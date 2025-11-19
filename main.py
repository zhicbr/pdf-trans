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


def pre_flight_checks():
    """执行程序启动前的环境检查"""
    Logger.separator('-', 50)
    print("执行启动前环境检查...")
    checks_passed = True

    # 1. 检查 Google API Key
    api_key = config.GOOGLE_API_KEY
    if not api_key or api_key == "你的_GOOGLE_API_KEY":
        Logger.error("检查失败: Google API Key 未配置。")
        print("请在系统中设置 GOOGLE_API_KEY 环境变量，或者直接在 config.py 文件中修改。")
        checks_passed = False
    else:
        Logger.success("检查通过: Google API Key 已配置。")

    # 2. 检查网络连接
    try:
        response = requests.get(config.GOOGLE_TEST_URL, timeout=10)
        if response.status_code == 200:
            Logger.success("检查通过: 网络连接正常，可以访问 Google 服务。")
        else:
            Logger.error(f"检查失败: 无法访问 Google 服务，状态码: {response.status_code}")
            checks_passed = False
    except requests.exceptions.RequestException as e:
        Logger.error(f"检查失败: 网络连接异常，无法连接到 {config.GOOGLE_TEST_URL}")
        print(f"错误详情: {e}")
        checks_passed = False

    Logger.separator('-', 50)
    return checks_passed


def main():
    Logger.separator('=', 50)
    print("[START] AI 论文翻译程序启动")
    Logger.separator('=', 50)

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
    ai_handler = AIHandler()

    # 3. 循环处理每一篇论文
    for idx, pdf_file in enumerate(pdf_files):
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
        except Exception as e:
            Logger.error(f"处理 PDF 失败，跳过此论文。错误: {e}", indent=2)
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

            except Exception as e:
                Logger.critical(f"页面 {current_page_num} 翻译彻底失败: {e}", indent=3)
                # 插入占位符，避免整体失败
                error_placeholder = f"\n\n> [ERROR] 第 {current_page_num} 页翻译失败，请检查日志。\n\n"
                translated_texts.append(error_placeholder)
                save_progress(paper_output_dir, {"translated_texts": translated_texts})
                # 这里选择继续下一页，而不是终止程序

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

    print()
    Logger.separator('=', 50)
    print("[END] 所有任务已完成, 程序正常退出。")
    Logger.separator('=', 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[STOP] 用户强制终止程序。")
    except Exception as e:
        print(f"\n\n[CRITICAL] 程序发生未捕获异常: {e}")
        traceback.print_exc()