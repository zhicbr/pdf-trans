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
        self.qwen_client = OpenAI(
            api_key=config.QWEN_API_KEY,
            base_url=config.QWEN_API_URL
        )
        self.current_model_type = "gemini"  # 'gemini' or 'qwen'

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

    def _call_qwen(self, prompt, image_path):
        """调用 Qwen API"""
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

        # 尝试顺序：Gemini Pro -> Gemini Flash -> Qwen
        # 如果当前已经降级到 Qwen，则直接使用 Qwen

        if self.current_model_type == "qwen":
            return self._translate_with_retry(self._call_qwen, "Qwen", image_path, prompt)

        # === 尝试 Gemini 流程 ===

        # 1. 网络检查
        if not self.check_google_connection():
            Logger.warning("无法连接到 Google 服务。", indent=3)
            if HAS_CONNECTED_ONCE:
                # 曾经连接成功过，无限重试
                self._wait_for_connection()
            else:
                # 从未成功过，重试几次后切换到 Qwen
                if not self._retry_connection_limited():
                    Logger.warning("Google 连接失败次数过多，切换至最终备用方案: Qwen...", indent=3)
                    self.current_model_type = "qwen"
                    return self._translate_with_retry(self._call_qwen, "Qwen", image_path, prompt)

        # 2. Gemini Pro
        try:
            Logger.api_log(f"尝试使用 Gemini ({config.MODEL_GEMINI_PRO})...", indent=3)
            return self._call_gemini(config.MODEL_GEMINI_PRO, prompt, image_path)
        except Exception as e:
            Logger.error(f"Gemini Pro 错误: {str(e)}", indent=3)

            # 3. Gemini Flash (Pro 失败后)
            try:
                Logger.api_log(f"尝试备用模型 Gemini ({config.MODEL_GEMINI_FLASH})...", indent=3)
                return self._call_gemini(config.MODEL_GEMINI_FLASH, prompt, image_path)
            except Exception as e2:
                Logger.error(f"Gemini Flash 错误: {str(e2)}", indent=3)
                Logger.warning("所有 Gemini 模型均调用失败。", indent=3)

                # 4. 切换到 Qwen
                Logger.warning("切换至最终备用方案: Qwen...", indent=3)
                self.current_model_type = "qwen"
                return self._translate_with_retry(self._call_qwen, "Qwen", image_path, prompt)

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
        """通用的 API 调用重试逻辑 (针对 Qwen 或 已经确定使用 Gemini 但偶发错误的情况)"""
        retry_count = 0
        max_retries = 5

        while retry_count < max_retries:
            try:
                Logger.api_log(f"正在连接 {model_label}...", indent=3)
                res = None
                if model_label == "Qwen":
                    res = func(prompt, image_path)
                else:  # 理论上不应该走到这，因为Gemini有专门流程，但这作为通用保险
                    pass

                if res:
                    Logger.success(f"{model_label} API 调用成功。", indent=3)
                    return res
            except Exception as e:
                Logger.error(f"{model_label} 连接失败: {e}", indent=3)
                retry_count += 1
                Logger.retry_log(f"{config.RETRY_DELAY} 秒后进行第 {retry_count} 次重试...", indent=3)
                time.sleep(config.RETRY_DELAY)

        Logger.critical(f"所有重试均失败 ({model_label})。", indent=3)
        raise Exception(f"{model_label} Failed")