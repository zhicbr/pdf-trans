# ai_handler.py
import requests
import json
import time
import traceback
from openai import OpenAI
import config
from utils import Logger, image_to_base64, get_mime_type

# 全局变量记录是否曾经成功连接过网络
HAS_CONNECTED_ONCE = False


class AIHandler:
    def __init__(self):
        # 初始化阿里云客户端
        self.aliyun_client = OpenAI(
            api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_API_URL
        )
        # 初始化硅基流动客户端
        self.qwen_client = OpenAI(
            api_key=config.QWEN_API_KEY,
            base_url=config.QWEN_API_URL
        )
        self.current_model_type = "gemini"  # 'gemini', 'aliyun', or 'siliconflow'

    def check_google_connection(self):
        """检查谷歌连接"""
        try:
            requests.get(config.GOOGLE_TEST_URL, timeout=5)
            global HAS_CONNECTED_ONCE
            HAS_CONNECTED_ONCE = True
            return True
        except:
            return False

    def _call_gemini(self, model_name, prompt, image_path):
        """调用 Gemini API"""
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?key={config.GOOGLE_API_KEY}&alt=sse"
        headers = {'Content-Type': 'application/json'}

        b64_img = image_to_base64(image_path)
        mime_type = get_mime_type(image_path)

        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": config.SYSTEM_PROMPT + "\n\n" + prompt},
                    {"inline_data": {"mime_type": mime_type, "data": b64_img}}
                ]
            }],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        }

        response = requests.post(api_url, headers=headers, data=json.dumps(payload), stream=True, timeout=60)
        response.raise_for_status()

        full_text = ""
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    try:
                        data = json.loads(decoded[6:])
                        if "candidates" in data:
                            chunk = data["candidates"][0]["content"]["parts"][0]["text"]
                            full_text += chunk
                    except:
                        pass
        return full_text

    def _call_aliyun_qwen(self, prompt, image_path):
        """调用阿里云 Qwen API"""
        b64_img = image_to_base64(image_path)
        response = self.aliyun_client.chat.completions.create(
            model=config.MODEL_ALIYUN_QWEN,
            messages=[
                {"role": "system", "content": config.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=4000
        )
        return response.choices[0].message.content

    def _call_qwen(self, prompt, image_path):
        """调用硅基流动 Qwen API"""
        b64_img = image_to_base64(image_path)
        response = self.qwen_client.chat.completions.create(
            model=config.MODEL_QWEN,
            messages=[
                {"role": "system", "content": config.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=4000
        )
        return response.choices[0].message.content

    def translate_page(self, image_path, prompt):
        """统一的翻译入口，处理重试和降级"""
        global HAS_CONNECTED_ONCE

        # 如果已锁定备用模型，直接使用
        if self.current_model_type == "aliyun":
            return self._translate_with_retry(self._call_aliyun_qwen, "Aliyun Qwen", image_path, prompt)
        if self.current_model_type == "siliconflow":
            return self._translate_with_retry(self._call_qwen, "SiliconFlow Qwen", image_path, prompt)

        # === 尝试 Gemini 流程 ===
        # 1. 网络检查 (仅针对 Gemini)
        if not self.check_google_connection():
            Logger.warning("无法连接到 Google 服务。", indent=3)
            if HAS_CONNECTED_ONCE:
                self._wait_for_connection() # 曾连上过，无限等
            else:
                if not self._retry_connection_limited(): # 从未连上，有限重试
                    Logger.warning("Google 连接失败，将尝试备用方案...", indent=3)
                    return self._fallback_to_alternatives(image_path, prompt) # 直接进入备用流程
        
        # 2. 尝试 Gemini
        try:
            Logger.api_log(f"尝试使用 Gemini ({config.MODEL_GEMINI_PRO})...", indent=3)
            return self._call_gemini(config.MODEL_GEMINI_PRO, prompt, image_path)
        except Exception as e:
            Logger.error(f"Gemini Pro 错误: {str(e)}", indent=3)
            try:
                Logger.api_log(f"尝试备用模型 Gemini ({config.MODEL_GEMINI_FLASH})...", indent=3)
                return self._call_gemini(config.MODEL_GEMINI_FLASH, prompt, image_path)
            except Exception as e2:
                Logger.error(f"Gemini Flash 错误: {str(e2)}", indent=3)
                Logger.warning("所有 Gemini 模型均调用失败。", indent=3)
                # Gemini 彻底失败，进入备用流程
                return self._fallback_to_alternatives(image_path, prompt)

    def _fallback_to_alternatives(self, image_path, prompt):
        """备用模型降级流程: Aliyun -> SiliconFlow"""
        # 1. 尝试 Aliyun
        try:
            Logger.warning("切换至第一备用方案: Aliyun Qwen...", indent=3)
            result = self._translate_with_retry(self._call_aliyun_qwen, "Aliyun Qwen", image_path, prompt)
            self.current_model_type = "aliyun" # 锁定 Aliyun
            Logger.info("已锁定使用 Aliyun Qwen 进行后续翻译。", indent=3)
            return result
        except Exception as e:
            Logger.error(f"Aliyun Qwen 错误: {e}", indent=3)

            # 2. 尝试 SiliconFlow
            try:
                Logger.warning("切换至第二备用方案: SiliconFlow Qwen...", indent=3)
                result = self._translate_with_retry(self._call_qwen, "SiliconFlow Qwen", image_path, prompt)
                self.current_model_type = "siliconflow" # 锁定 SiliconFlow
                Logger.info("已锁定使用 SiliconFlow Qwen 进行后续翻译。", indent=3)
                return result
            except Exception as e2:
                Logger.critical(f"所有备用方案均失败: {e2}", indent=3)
                raise e2 # 抛出最终异常

    def _wait_for_connection(self):
        """无限等待网络恢复"""
        attempt = 1
        while not self.check_google_connection():
            Logger.warning(f"网络连接超时。由于程序之前已成功连接, 将持续重试。 (第 {attempt} 次)", indent=3)
            time.sleep(10 if attempt < 10 else 30)
            attempt += 1
        Logger.success("网络连接已恢复！", indent=3)

    def _retry_connection_limited(self):
        """有限次数重试连接，成功返回True，失败返回False"""
        for i in range(config.INITIAL_RETRY_LIMIT):
            Logger.retry_log(
                f"{config.RETRY_DELAY} 秒后进行第 {i + 1} 次重试... (剩余 {config.INITIAL_RETRY_LIMIT - i - 1} 次)",
                indent=3)
            time.sleep(config.RETRY_DELAY)
            if self.check_google_connection():
                return True
        return False

    def _translate_with_retry(self, func, model_label, image_path, prompt):
        """通用的 API 调用重试逻辑"""
        retry_count = 0
        max_retries = 5

        while retry_count < max_retries:
            try:
                Logger.api_log(f"正在连接 {model_label}...", indent=3)
                res = func(prompt, image_path)
                if res:
                    Logger.success(f"{model_label} API 调用成功。", indent=3)
                    return res
            except Exception as e:
                Logger.error(f"{model_label} 连接失败: {e}", indent=3)
                retry_count += 1
                if retry_count < max_retries:
                    Logger.retry_log(f"{config.RETRY_DELAY} 秒后进行第 {retry_count} 次重试...", indent=3)
                    time.sleep(config.RETRY_DELAY)

        Logger.critical(f"所有重试均失败 ({model_label})。", indent=3)
        raise Exception(f"{model_label} Failed")