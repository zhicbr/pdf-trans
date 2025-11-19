# pdf_processor.py
import os
import fitz  # PyMuPDF
from utils import Logger


def convert_pdf_to_images(pdf_path, output_root_dir, dpi=300):
    """
    将PDF转换为图片，保存到 output_root_dir/PDF文件名/ 目录下
    返回: 图片路径列表 (按页码排序)
    """
    try:
        pdf_filename = os.path.basename(pdf_path)
        pdf_name_no_ext = os.path.splitext(pdf_filename)[0]
        save_dir = os.path.join(output_root_dir, pdf_name_no_ext)

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # 检查是否已经存在图片，如果存在且数量合理，可能跳过（这里为了保险起见，简单检查是否有文件）
        existing_files = [f for f in os.listdir(save_dir) if f.endswith('.png')]
        if existing_files:
            # 尝试按页码排序返回
            # 假设文件名格式 page_X.png
            try:
                existing_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
                Logger.info(f"检测到 '{save_dir}' 下已有 {len(existing_files)} 张图片，跳过转换。", indent=2)
                return [os.path.join(save_dir, f) for f in existing_files]
            except:
                pass  # 文件名格式不对，重新转换

        Logger.info("开始切分...", indent=2)
        doc = fitz.open(pdf_path)
        image_paths = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            img_filename = f"page_{page_num + 1}.png"
            img_path = os.path.join(save_dir, img_filename)
            pix.save(img_path)
            image_paths.append(img_path)

        doc.close()
        Logger.success(f"切分完成, 共 {len(image_paths)} 页图片已保存至 '{save_dir}'", indent=2)
        return image_paths

    except Exception as e:
        Logger.error(f"PDF 切分失败: {e}", indent=2)
        raise e