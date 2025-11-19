# config.py
import os

# ================= 配置区域 =================

# 1. API Keys (请替换或使用环境变量)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "你的_GOOGLE_API_KEY")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "你的_DASHSCOPE_API_KEY") # 阿里云 DashScope Key
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "你的_QWEN_API_KEY") # 硅基流动或其他兼容OpenAI的Key

# 2. 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'Data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
TRANS_DIR = os.path.join(BASE_DIR, 'Trans')

# 3. 模型配置
# Gemini
MODEL_GEMINI_PRO = "gemini-2.5-pro" # 优先
MODEL_GEMINI_FLASH = "gemini-2.5-flash" # 备用
# Aliyun
MODEL_ALIYUN_QWEN = "qwen-vl-max" # 阿里云第一备用
DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1" # 阿里云地址
# SiliconFlow
MODEL_QWEN = "Qwen/QVQ-72B-Preview" # 最终备用
QWEN_API_URL = "https://api.siliconflow.cn/v1" # 硅基流动地址


# 4. 网络与重试配置
GOOGLE_TEST_URL = "https://www.google.com"
INITIAL_RETRY_LIMIT = 5  # 首次运行失败重试次数
NETWORK_TIMEOUT = 30     # 请求超时时间(秒)
RETRY_DELAY = 5          # 重试等待基数(秒)

# ================= 提示词模板 =================

# 系统提示词
SYSTEM_PROMPT = """你是一个专业的学术论文翻译助手。你的任务是将计算机科学领域的英文论文图片翻译成流畅、准确的中文 Markdown 格式。
请遵循以下规则：
1. **翻译风格**：符合中文学术语言习惯，准确严谨。
2. **排版处理**：
   - 单栏排版：从上到下翻译。
   - 双栏排版：先左栏后右栏。
3. **特殊元素处理**：
   - **图片**：使用 `【FigX - 图片标题】\n图片描述：...` 格式。
   - **表格**：使用 `【TableX - 表格标题】\n表格描述：一个包含n列的表格，分别是...` 格式。
   - **公式**：
     - 行间公式（独立一行）：使用 `$$` 包裹，例如 `$$\nE = mc^2\n$$`。
     - 行内公式（文本中）：使用 `$$` 包裹，例如 `$$a+b=c$$`。
     - **重要**：保留所有公式标号，使用 `\\quad (标号)`，例如 `$$ y = ax + b \\quad (1) $$`。
4. **内容拼接**：如果提供了“上一页的上下文”，请务必将本页开头的内容与上下文衔接通顺，不要重复翻译上下文，只翻译本页内容。
"""

# 用户提示词模板
USER_PROMPT_TEMPLATE = """
这是论文的第 {page_num} 页。
{context_instruction}
请详细分析并翻译这张图片里的内容。
"""

CONTEXT_INSTRUCTION = """
【注意】：上一页的最后两句话是：
“{prev_context}”
请根据这两句话的语境，确保本页开始的翻译内容与其语义连贯。
"""