import os
import fitz  # PyMuPDF

# ==================================================
# ||                配置区域                     ||
# ||         在此处修改您的设置                   ||
# ==================================================

# 1. 输入PDF文件的路径
# 请将 'sample.pdf' 替换为您的PDF文件路径
# 例如: 'C:/Users/YourUser/Documents/my_document.pdf'
INPUT_PDF_PATH = 'D:\paper\Class Integration Test order\强化学习Q-learing  Integration test order generation based on reinforcement learning considering class importance\Integration test order generationbasedonreinforcementlearning.pdf'

# 2. 输出图片的保存目录
# 程序会自动根据PDF文件名创建一个子目录来存放图片
# 例如, 如果输入是 'mydoc.pdf', 图片会保存在 'output/mydoc/'
OUTPUT_DIR = 'output'

# 3. 生成图片的格式
# 支持的格式包括 'png', 'jpg', 'jpeg', 'bmp', 'tiff' 等
IMAGE_FORMAT = 'png'

# 4. 生成图片的DPI（分辨率）
# DPI越高，图片越清晰，文件也越大。300 DPI 是印刷质量。
IMAGE_DPI = 300

# ==================================================
# ||                脚本核心逻辑                  ||
# ||         通常无需修改以下内容               ||
# ==================================================

def convert_pdf_to_images(input_path, output_dir, img_format='png', dpi=300):
    """
    将PDF的每一页转换为图片。

    :param input_path: 原始PDF文件的路径。
    :param output_dir: 图片的保存目录。
    :param img_format: 图片格式 (例如 'png', 'jpg')。
    :param dpi: 图片分辨率。
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            print(f"错误：找不到输入文件 '{input_path}'")
            print("请确保 'INPUT_PDF_PATH' 配置正确，并且文件存在。")
            return

        # 打开PDF文件
        doc = fitz.open(input_path)

        # 根据PDF文件名创建输出子目录
        pdf_filename = os.path.basename(input_path)
        pdf_name_without_ext = os.path.splitext(pdf_filename)[0]
        image_output_dir = os.path.join(output_dir, pdf_name_without_ext)

        if not os.path.exists(image_output_dir):
            os.makedirs(image_output_dir)
            print(f"创建图片保存目录：'{image_output_dir}'")

        print(f"开始转换 '{pdf_filename}'...")

        # 遍历每一页
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # 设置缩放矩阵以获得所需的DPI
            zoom = dpi / 72  # 默认DPI是72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # 定义输出图片的文件名
            output_image_path = os.path.join(image_output_dir, f"page_{page_num + 1}.{img_format}")

            # 保存图片
            pix.save(output_image_path)
            print(f"  - 已保存页面 {page_num + 1} 为 '{output_image_path}'")

        doc.close()
        print(f"\n成功！所有页面已转换为图片并保存在 '{image_output_dir}' 目录中。")

    except Exception as e:
        print(f"处理PDF时发生错误：{e}")
        print("请检查PDF文件是否已损坏或与PyMuPDF库不兼容。")

if __name__ == '__main__':
    # 执行PDF到图片的转换功能
    convert_pdf_to_images(INPUT_PDF_PATH, OUTPUT_DIR, IMAGE_FORMAT, IMAGE_DPI)
