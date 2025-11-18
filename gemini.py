import requests
import base64
import json
import os
import sys
import mimetypes
from PIL import Image

# --- 1. 配置区域：请在此处修改你的信息 ---

# 请替换为你的 Google AI Studio API Key
# 获取地址: https://aistudio.google.com/app/apikey
API_KEY = os.getenv("GOOGLE_API_KEY")

# 要分析的图片文件的路径
IMAGE_PATH = r"E:\PyCharm\PDF-Processor\PixPin_2025-11-18_20-41-02.png"

# 你想对图片提出的问题或指令
PROMPT = "这张图里有什么？详细描述一下。"

# --- 已更新 ---
# 使用当前最新的 Gemini 2.5 Pro 模型
# 参考来源: https://ai.google.dev/gemini-api/docs/models/gemini
MODEL_NAME = "gemini-2.5-flash"
#MODEL_NAME = "gemini-2.5-pro"
#两个模型都可以使用

# --- 2. 脚本核心逻辑：通常无需修改以下内容 ---

def check_google_connection():
    """检查是否能连接到谷歌官网"""
    try:
        response = requests.get("https://www.google.com", timeout=10)
        if response.status_code == 200:
            print("网络连接正常：可以访问谷歌官网")
            return True
        else:
            print(f"无法访问谷歌官网，状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"无法连接到谷歌官网: {e}")
        return False

def get_image_mime_type(image_path):
    """根据文件扩展名猜测 MIME 类型"""
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        return "application/octet-stream"
    return mime_type


def image_to_base64(image_path):
    """将图片文件转换为 Base64 编码的字符串"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"错误：无法读取或编码图片文件 '{image_path}'。错误信息: {e}")
        sys.exit(1)


def main():
    """主执行函数"""

    # --- 安全性检查和配置 ---
    if API_KEY == "YOUR_API_KEY_HERE":
        print("错误：请在脚本顶部设置你的 API_KEY。")
        sys.exit(1)

    if not os.path.exists(IMAGE_PATH):
        print(f"错误：图片文件未找到，请检查路径：'{IMAGE_PATH}'")
        sys.exit(1)

    try:
        Image.open(IMAGE_PATH).verify()
    except Exception as e:
        print(f"无法打开或验证图片文件。请确保它是一个有效的图片格式。错误信息: {e}")
        sys.exit(1)

    # --- 检查网络连接 ---
    if not check_google_connection():
        print("错误：无法连接到谷歌服务，请检查您的网络连接。")
        sys.exit(1)

    # --- 构造 API 请求 ---
    print("正在准备 API 请求...")

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:streamGenerateContent?key={API_KEY}&alt=sse"

    headers = {
        'Content-Type': 'application/json'
    }

    base64_image = image_to_base64(IMAGE_PATH)
    image_mime_type = get_image_mime_type(IMAGE_PATH)

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": PROMPT},
                    {
                        "inline_data": {
                            "mime_type": image_mime_type,
                            "data": base64_image
                        }
                    }
                ]
            }
        ],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    }

    # --- 发送请求并处理流式响应 ---
    try:
        print(f"\n正在向 Gemini 模型 ({MODEL_NAME}) 发送请求，请稍候...")
        response = requests.post(
            api_url,
            headers=headers,
            data=json.dumps(payload),
            stream=True,
            timeout=180
        )

        response.raise_for_status()

        print("\n--- Gemini 的回复 ---\n")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    try:
                        json_str = decoded_line[6:]
                        data = json.loads(json_str)
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        print(text, end='', flush=True)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass
        print()

    except requests.exceptions.RequestException as e:
        print(f"\n错误：网络请求失败。请检查您的网络连接、API Key 和模型名称。")
        # 尝试解析错误响应体以获取更具体的信息
        try:
            error_details = response.json()
            print(f"API 返回的错误信息: {error_details.get('error', {}).get('message', '无详细信息')}")
        except:
            print(f"原始响应内容: {response.text}")
    except Exception as e:
        print(f"\n发生未知错误: {e}")


if __name__ == "__main__":
    main()