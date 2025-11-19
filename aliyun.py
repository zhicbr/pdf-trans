import base64
import os
from openai import OpenAI

# --------------------- 可修改区域 ---------------------------------
IMAGE_PATH = r"E:\PyCharm\PDF-Processor\PixPin_2025-11-18_20-41-02.png"        # 输入图片路径
PROMPT = "请详细描述这张图的内容。"  # 输入提示词
MODEL_NAME = "qwen-vl-max-2025-08-13"       # 可切换模型qwen3-vl-plus-2025-09-23，qwen3-vl-plus，qwen-vl-max-2025-08-13，qvq-max-2025-05-15，qvq-plus，qvq-plus-latest，qvq-plus-2025-05-15
# -------------------------------------------------------------------

# 环境变量读取密钥
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("请在 PyCharm 的环境变量中设置 DASHSCOPE_API_KEY")

# 初始化客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 读取并编码图片
with open(IMAGE_PATH, "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode("utf-8")

# 调用模型
response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{img_base64}"
                }
            ]
        }
    ]
)

# 安全输出
print("\n=== 模型返回的描述 ===\n")
print(response.choices[0].message.content)
