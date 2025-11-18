# -*- coding: utf-8 -*-
"""
使用 Qwen/Qwen3-VL-235B-A22B-Instruct 视觉模型分析图片内容
自动保存结果到 output 文件夹，并带详细出错捕获
依赖：
    pip install openai pillow
"""

# ====== 提示词配置 ======
PROMPT = """
图片是什么
"""

# ====== 基本配置 ======
API_KEY = "sk-eoenljxhvzwgthkkurejqyascniadoqxfrvmpzfcifpolkdc"  # ⚠️替换为你自己的密钥
API_URL = "https://api.siliconflow.cn/v1"
MODEL_NAME = "Qwen/QVQ-72B-Preview"

# ====== 输入图片路径 ======
IMAGE_PATH = r"E:\PyCharm\PDF-Processor\PixPin_2025-11-18_20-41-02.png"

DEFAULT_OUTPUT_DIR = "output"
# 模型参数，可根据需要调整
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 4000
# 是否在运行时打印提示词的前缀预览（仅用于调试）
SHOW_PROMPT_PREVIEW = True
# 如果希望在 Markdown 中插入图片预览（如果图片存在），设为 True
EMBED_IMAGE_IN_MD = True

import argparse
import base64
import os
import traceback
from openai import OpenAI
from openai import APIError, Timeout, AuthenticationError, APIConnectionError

client = OpenAI(base_url=API_URL, api_key=API_KEY)


def encode_image_to_base64(image_path: str) -> str:
    """读取图片并转为Base64编码"""
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"找不到文件：{image_path}")
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"图片读取或编码失败：{e}")


def analyze_image(image_path: str, prompt: str = PROMPT,
                  temperature: float = DEFAULT_TEMPERATURE,
                  max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """调用视觉模型分析图片"""
    try:
        image_base64 = encode_image_to_base64(image_path)
    except Exception as e:
        raise RuntimeError(f"图片加载失败：{e}")

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的视觉AI助手，擅长分析学术图片和图表。"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text",
                         "text": prompt
                         },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,  # 增加最大输出长度
        )

        if not response or not response.choices:
            raise ValueError("模型没有返回任何内容。")

        return response.choices[0].message.content

    except AuthenticationError:
        raise RuntimeError("❌ API 认证失败，请检查 API_KEY 是否正确。")
    except APIConnectionError:
        raise RuntimeError("❌ 无法连接到 API 服务器，请检查网络连接。")
    except Timeout:
        raise RuntimeError("⚠️ 请求超时，请重试或检查网络。")
    except APIError as e:
        raise RuntimeError(f"💥 模型接口返回错误：{e}")
    except Exception as e:
        raise RuntimeError(f"模型调用时出现未知错误：{e}")


def save_output(image_path: str, content: str, output_dir: str = DEFAULT_OUTPUT_DIR):
    """保存输出结果到指定的输出文件夹，格式为 Markdown (.md)。

    output_dir: 目标输出文件夹路径，如果不存在会自动创建。
    文件名使用原图片名（不含扩展名），扩展名为 .md。
    Markdown 文件会包含一个一级标题和模型的输出内容。
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.md")

        # 将结果写成 Markdown：标题 + 原图（如果存在） + 内容
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# {base_name}\n\n")

            # 如果图片路径存在则以绝对或相对路径插入图片引用
            try:
                if EMBED_IMAGE_IN_MD and os.path.exists(image_path):
                    # 使用绝对路径，这在本地查看时可以直接显示；如果需要相对路径可自行调整
                    img_path_for_md = image_path.replace('\\', '/')
                    f.write(f"![{base_name}]({img_path_for_md})\n\n")
            except Exception:
                # 忽略插图错误，继续写入文本内容
                pass

            f.write(content)

        print(f"✅ 结果已保存到: {output_path}")

    except Exception as e:
        raise RuntimeError(f"保存输出文件失败：{e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用视觉模型分析图片并保存为 Markdown")
    parser.add_argument("--image", "-i", dest="image_path", default=IMAGE_PATH,
                        help="要分析的图片路径，默认使用文件内的 IMAGE_PATH")
    parser.add_argument("--output-dir", "-o", dest="output_dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"输出目录（会自动创建），默认：{DEFAULT_OUTPUT_DIR}")
    args = parser.parse_args()

    print(f"🖼️ 正在分析图片：{args.image_path}")
    if SHOW_PROMPT_PREVIEW:
        print(f"📝 使用提示词：{PROMPT[:100]}...\n")  # 只显示前100个字符

    try:
        result = analyze_image(args.image_path,
                               temperature=DEFAULT_TEMPERATURE,
                               max_tokens=DEFAULT_MAX_TOKENS)
        save_output(args.image_path, result, args.output_dir)
        print("\n===== 模型输出内容 =====")
        print(result)
    except Exception as e:
        print("\n❌ 程序运行出错：")
        print("错误信息：", e)
        print("\n详细堆栈信息如下：\n")
        traceback.print_exc()