# utils.py
import os
import sys
import time
import json
import base64
import mimetypes


class Logger:
    @staticmethod
    def separator(char='-', length=50):
        print(char * length)

    @staticmethod
    def info(msg, indent=0):
        prefix = "  " * indent
        print(f"{prefix}[INFO]     {msg}")

    @staticmethod
    def success(msg, indent=0):
        prefix = "  " * indent
        print(f"{prefix}[SUCCESS]  {msg}")

    @staticmethod
    def warning(msg, indent=0):
        prefix = "  " * indent
        print(f"{prefix}[WARNING]  {msg}")

    @staticmethod
    def error(msg, indent=0):
        prefix = "  " * indent
        print(f"{prefix}[ERROR]    {msg}")

    @staticmethod
    def api_log(msg, indent=0):
        prefix = "  " * indent
        print(f"{prefix}[API]      {msg}")

    @staticmethod
    def retry_log(msg, indent=0):
        prefix = "  " * indent
        print(f"{prefix}[RETRY]    {msg}")

    @staticmethod
    def critical(msg, indent=0):
        prefix = "  " * indent
        print(f"{prefix}[CRITICAL] {msg}")


def ensure_directories(paths):
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)


def image_to_base64(image_path):
    """将图片文件转换为 Base64 编码的字符串"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        Logger.error(f"读取图片失败: {e}")
        return None


def get_mime_type(image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    return mime_type or "application/octet-stream"


def extract_last_sentences(text, num_sentences=2):
    """简单的提取最后两句话的逻辑"""
    if not text:
        return ""
    # 简单通过句号、问号、感叹号分割，实际情况可能更复杂，这里做简化处理
    # 移除多余空行
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return ""

    full_text = " ".join(lines)
    # 简单的按句号分割（注意：这只是一个近似处理，针对学术论文通常足够）
    sentences = full_text.replace('。', '.').split('.')
    # 过滤空句
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) < num_sentences:
        return ".".join(sentences) + "."

    return ".".join(sentences[-num_sentences:]) + "."


def save_progress(folder_path, data):
    """保存翻译进度到JSON文件"""
    file_path = os.path.join(folder_path, "progress.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_progress(folder_path):
    """加载翻译进度"""
    file_path = os.path.join(folder_path, "progress.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None