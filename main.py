# main.py
import os
import sys
import time
import config
import traceback
import requests  # 添加导入
from utils import Logger, ensure_directories, extract_last_sentences, save_progress, load_progress
from pdf_processor import convert_pdf_to_images
from ai_handler import AIHandler
from stats_manager import StatsManager # 导入 StatsManager


def pre_flight_checks():
    """执行程序启动前的环境检查"""
    Logger.separator('-', 50)
    print("执行启动前环境检查...")
    
    # 检查 API Keys
    google_key_ok = config.GOOGLE_API_KEY and config.GOOGLE_API_KEY != "你的_GOOGLE_API_KEY"
    aliyun_key_ok = config.DASHSCOPE_API_KEY and config.DASHSCOPE_API_KEY != "你的_DASHSCOPE_API_KEY"
    siliconflow_key_ok = config.QWEN_API_KEY and config.QWEN_API_KEY != "你的_QWEN_API_KEY"

    if not google_key_ok and not aliyun_key_ok and not siliconflow_key_ok:
        Logger.error("检查失败: 所有 API Key (Google, Aliyun, SiliconFlow) 均未配置。")
        print("请至少在系统中设置一个有效的 API 密钥环境变量（如 GOOGLE_API_KEY），或在 config.py 中修改。")
        Logger.separator('-', 50)
        return False

    # 详细报告每个key的状态
    if google_key_ok:
        Logger.success("检查通过: Google API Key 已配置。")
    else:
        Logger.warning("注意: Google API Key 未配置，将依赖备用模型。")

    if aliyun_key_ok:
        Logger.success("检查通过: Aliyun DashScope API Key 已配置。")
    else:
        Logger.warning("注意: Aliyun API Key 未配置，第一备用模型将不可用。")

    if siliconflow_key_ok:
        Logger.success("检查通过: SiliconFlow API Key 已配置。")
    else:
        Logger.warning("注意: SiliconFlow API Key 未配置，第二备用模型将不可用。")

    # 如果配置了Google Key，则检查网络
    if google_key_ok:
        Logger.info("正在检查 Google 网络连通性...")
        try:
            response = requests.get(config.GOOGLE_TEST_URL, timeout=10)
            if response.status_code == 200:
                Logger.success("检查通过: 网络连接正常，可以访问 Google 服务。")
            else:
                Logger.warning(f"网络警告: 无法访问 Google 服务 (状态码: {response.status_code})，将依赖备用模型。")
        except requests.exceptions.RequestException:
            Logger.warning(f"网络警告: 无法连接到 {config.GOOGLE_TEST_URL}，将依赖备用模型。")
    
    Logger.separator('-', 50)
    return True


def main():
    Logger.separator('=', 50)
    print("[START] AI 论文翻译程序启动")
    Logger.separator('=', 50)

    stats_manager = StatsManager(config.OUTPUT_DIR) # 实例化 StatsManager

    try:
        # 0. 执行启动前检查
        if not pre_flight_checks():
            print("\n环境检查未通过，程序已终止。请根据提示修复问题后重试。")
            sys.exit(1)

        # 1. 初始化目录
        ensure_directories([config.DATA_DIR, config.OUTPUT_DIR, config.TRANS_DIR])

        # 2. 扫描论文
        Logger.info('扫描 "Data" 文件夹...')
        pdf_files = [f for f in os.listdir(config.DATA_DIR) if f.lower().endswith('.pdf')]

        if not pdf_files:
            Logger.warning("Data 文件夹下没有找到 PDF 文件。")
            return

        Logger.info(f"发现 {len(pdf_files)} 篇待翻译论文: {pdf_files}")

        # 初始化 AI 处理器
        ai_handler = AIHandler(stats_manager) # 传递 stats_manager 实例

        # 3. 循环处理每一篇论文
        for idx, pdf_file in enumerate(pdf_files):
            paper_start_time = time.time() # 记录论文开始时间
            print()
            Logger.separator()
            Logger.info(f"开始处理论文 ({idx + 1}/{len(pdf_files)}): {pdf_file}")
            Logger.separator()

            pdf_path = os.path.join(config.DATA_DIR, pdf_file)
            pdf_name_no_ext = os.path.splitext(pdf_file)[0]
            paper_output_dir = os.path.join(config.OUTPUT_DIR, pdf_name_no_ext)

            # --- 步骤 1: 切分 PDF ---
            Logger.info("步骤 1/3: 切分 PDF 为图片", indent=1)
            try:
                image_paths = convert_pdf_to_images(pdf_path, config.OUTPUT_DIR)
                Logger.info(f"PDF 切分结果: image_paths 包含 {len(image_paths)} 张图片。", indent=2) # Debug log
            except Exception as e:
                Logger.error(f"处理 PDF 失败，跳过此论文。错误: {e}", indent=2)
                Logger.info("PDF 切分异常捕获，跳过当前论文。", indent=2) # Debug log
                continue

            # --- 步骤 2: 逐页翻译 (支持断点续传) ---
            Logger.info("步骤 2/3: 逐页翻译", indent=1)

            # 加载进度
            progress_data = load_progress(paper_output_dir)
            translated_texts = []
            start_page_idx = 0

            if progress_data:
                translated_texts = progress_data.get("translated_texts", [])
                start_page_idx = len(translated_texts)
                if start_page_idx > 0:
                    Logger.info(f"检测到上次翻译进度，从第 {start_page_idx + 1} 页继续。", indent=2)

                # 如果已经全部翻译完
                if start_page_idx >= len(image_paths):
                    Logger.success("该论文所有页面已翻译，直接合并。", indent=2)

            # 开始翻译循环
            for i in range(start_page_idx, len(image_paths)):
                page_start_time = time.time() # 记录页面开始时间
                img_path = image_paths[i]
                current_page_num = i + 1
                Logger.info(f"翻译第 {current_page_num}/{len(image_paths)} 页...", indent=2)

                # 构建提示词上下文
                context_instruction = ""
                if i > 0 and translated_texts:
                    prev_text = translated_texts[-1]
                    last_sentences = extract_last_sentences(prev_text)
                    if last_sentences:
                        context_instruction = config.CONTEXT_INSTRUCTION.format(prev_context=last_sentences)
                        Logger.api_log("附加前一页的最后两句话作为上下文。", indent=3)

                prompt = config.USER_PROMPT_TEMPLATE.format(
                    page_num=current_page_num,
                    context_instruction=context_instruction
                )

                try:
                    # 调用 AI
                    page_content = ai_handler.translate_page(img_path, prompt)

                    # 记录结果
                    translated_texts.append(page_content)

                    # 实时保存进度
                    save_progress(paper_output_dir, {"translated_texts": translated_texts})
                    page_end_time = time.time() # 记录页面结束时间
                    stats_manager.record_page_time(page_end_time - page_start_time) # 记录页面耗时

                except Exception as e:
                    Logger.critical(f"页面 {current_page_num} 翻译彻底失败: {e}", indent=3)
                    # 插入占位符，避免整体失败
                    error_placeholder = f"\n\n> [ERROR] 第 {current_page_num} 页翻译失败，请检查日志。\n\n"
                    translated_texts.append(error_placeholder)
                    save_progress(paper_output_dir, {"translated_texts": translated_texts})
                    # 这里选择继续下一页，而不是终止程序
                    page_end_time = time.time() # 记录页面结束时间
                    stats_manager.record_page_time(page_end_time - page_start_time) # 记录页面耗时 (即使失败也记录)


            # --- 步骤 3: 合并结果 ---
            Logger.info("步骤 3/3: 合并翻译结果", indent=1)
            Logger.info("开始合并所有页面翻译内容...", indent=2)

            final_markdown_path = os.path.join(config.TRANS_DIR, f"翻译-{pdf_name_no_ext}.md")

            try:
                with open(final_markdown_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {pdf_name_no_ext}\n\n")
                    for page_idx, text in enumerate(translated_texts):
                        f.write(f"\n\n--- Page {page_idx + 1} ---\n\n")
                        f.write(text)

                Logger.success(f"合并完成, '{os.path.basename(final_markdown_path)}' 已保存至 'Trans' 文件夹。", indent=2)
                Logger.success(f"论文 \"{pdf_file}\" 处理完成。", indent=0)

            except Exception as e:
                Logger.error(f"文件写入失败: {e}", indent=2)
            
            paper_end_time = time.time() # 记录论文结束时间
            stats_manager.record_paper_time(paper_end_time - paper_start_time) # 记录论文耗时
    finally:
        print()
        Logger.separator('=', 50)
        print("[END] 所有任务已完成, 程序正常退出。")
        Logger.separator('=', 50)
        
        # 打印并保存总结报告
        print(stats_manager.get_summary_string())
        summary_file_path = stats_manager.save_summary()
        Logger.info(f"详细执行总结已保存至: {summary_file_path}")

if __name__ == "__main__":
    main()