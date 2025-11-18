import os
from PyPDF2 import PdfReader, PdfWriter

# ==================================================
# ||                配置区域                     ||
# ||         在此处修改您的设置                   ||
# ==================================================

# 1. 输入PDF文件的路径
# 请将 'sample.pdf' 替换为您的PDF文件路径
INPUT_PDF_PATH = 'D:\paper\Class Integration Test order\强化学习Q-learing  Integration test order generation based on reinforcement learning considering class importance\Integration test order generationbasedonreinforcementlearning.pdf'

# 2. 输出PDF文件的保存目录
OUTPUT_DIR = 'output'

# 3. 输出PDF文件的名称
OUTPUT_FILENAME = 'sliced_document.pdf'

# 4. 切割的起始&结束页码
START_PAGE = 1
END_PAGE = 5


# ==================================================
# ||                脚本核心逻辑                  ||
# ||         通常无需修改以下内容               ||
# ==================================================

def slice_pdf(input_path, output_path, start, end):
    """
    切割PDF文件从指定的起始页到结束页。

    :param input_path: 原始PDF文件的路径。
    :param output_path: 切割后PDF的保存路径。
    :param start: 起始页码（从1开始）。
    :param end: 结束页码（包含此页）。
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            print(f"错误：找不到输入文件 '{input_path}'")
            print("请确保 'INPUT_PDF_PATH' 配置正确，并且文件存在。")
            return

        # 创建PdfReader对象
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        num_pages = len(reader.pages)

        # 验证页码范围
        if start < 1 or end > num_pages or start > end:
            print(f"错误：无效的页码范围。该PDF共有 {num_pages} 页。")
            print(f"您设置的范围是从 {start} 到 {end}。请确保起始页不小于1，结束页不大于总页数，并且起始页不大于结束页。")
            return

        # PyPDF2的页码是从0开始的，所以需要将用户的输入（从1开始）转换为0索引
        start_index = start - 1
        end_index = end - 1

        # 遍历指定范围的页面并添加到writer中
        for i in range(start_index, end_index + 1):
            writer.add_page(reader.pages[i])

        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"创建输出目录：'{output_dir}'")

        # 写入到新的PDF文件
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        print(f"成功！PDF已切割并保存为 '{output_path}'")
        print(f"共切割了 {end - start + 1} 页（从第 {start} 页到第 {end} 页）。")

    except Exception as e:
        print(f"处理PDF时发生错误：{e}")
        print("请检查PDF文件是否已损坏或被密码保护。")

if __name__ == '__main__':
    # 拼接完整的输出路径
    full_output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    
    # 执行切割功能
    slice_pdf(INPUT_PDF_PATH, full_output_path, START_PAGE, END_PAGE)
