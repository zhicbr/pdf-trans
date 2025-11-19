# stats_manager.py
import os
import json
import time
from datetime import datetime

class StatsManager:
    def __init__(self, output_dir):
        self.start_time = time.time()
        self.error_log_dir = os.path.join(output_dir, 'error_logs')
        self.summary_dir = os.path.join(output_dir, 'summaries')
        os.makedirs(self.error_log_dir, exist_ok=True)
        os.makedirs(self.summary_dir, exist_ok=True)

        self.stats = {
            "total_papers": 0,
            "model_usage": {
                "gemini-2.5-pro": {"success": 0, "failure": 0},
                "gemini-2.5-flash": {"success": 0, "failure": 0},
                "qwen-vl-max": {"success": 0, "failure": 0},
                "Qwen/QVQ-72B-Preview": {"success": 0, "failure": 0}
            }
        }
        self.page_times = []
        self.paper_times = []

    def log_api_call(self, model_name, success, duration, request_details=None, response_details=None):
        """记录一次API调用及其结果"""
        if model_name not in self.stats["model_usage"]:
            # 以防万一有未预设的模型名称
            self.stats["model_usage"][model_name] = {"success": 0, "failure": 0}

        if success:
            self.stats["model_usage"][model_name]["success"] += 1
        else:
            self.stats["model_usage"][model_name]["failure"] += 1
            self._log_detailed_error(model_name, duration, request_details, response_details)

    def _log_detailed_error(self, model_name, duration, request_details, response_details):
        """将详细的错误信息写入文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = os.path.join(self.error_log_dir, f"error_{model_name.replace('/', '_')}_{timestamp}.log")

        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Model: {model_name}\n")
            f.write(f"Duration: {duration:.2f}s\n")
            f.write("\n" + "="*20 + " REQUEST " + "="*20 + "\n")
            f.write(json.dumps(request_details, indent=2, ensure_ascii=False))
            f.write("\n\n" + "="*20 + " RESPONSE / ERROR " + "="*20 + "\n")
            f.write(str(response_details))
            f.write("\n")

    def record_page_time(self, duration):
        self.page_times.append(duration)

    def record_paper_time(self, duration):
        self.paper_times.append(duration)
        self.stats["total_papers"] += 1

    def generate_summary(self):
        """生成包含所有统计数据的字典"""
        end_time = time.time()
        total_duration = end_time - self.start_time
        total_pages = len(self.page_times)

        summary = {
            "execution_summary": {
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "total_duration_seconds": total_duration,
                "translated_papers": self.stats["total_papers"],
                "translated_pages": total_pages,
                "avg_time_per_paper_seconds": sum(self.paper_times) / len(self.paper_times) if self.paper_times else 0,
                "avg_time_per_page_seconds": sum(self.page_times) / total_pages if total_pages else 0,
            },
            "model_usage_stats": self.stats["model_usage"]
        }
        return summary

    def save_summary(self):
        """将总结报告保存为JSON文件"""
        summary_data = self.generate_summary()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file_path = os.path.join(self.summary_dir, f"summary_{timestamp}.json")
        with open(summary_file_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=4, ensure_ascii=False)
        return summary_file_path

    def get_summary_string(self):
        """生成用于在终端打印的总结字符串"""
        summary_data = self.generate_summary()
        exec_summary = summary_data["execution_summary"]
        model_stats = summary_data["model_usage_stats"]

        total_duration_str = time.strftime("%H:%M:%S", time.gmtime(exec_summary["total_duration_seconds"]))
        
        lines = [
            "\n" + "="*60,
            " " * 22 + "执行摘要",
            "="*60,
            f"  论文翻译总数: {exec_summary['translated_papers']} 篇",
            f"  页面翻译总数: {exec_summary['translated_pages']} 页",
            f"  总耗时: {total_duration_str}",
            f"  平均每篇论文耗时: {exec_summary['avg_time_per_paper_seconds']:.2f} 秒",
            f"  平均每页翻译耗时: {exec_summary['avg_time_per_page_seconds']:.2f} 秒",
            "-"*60,
            " " * 22 + "模型使用统计",
            "-"*60,
        ]

        for model, usage in model_stats.items():
            total = usage['success'] + usage['failure']
            if total > 0:
                lines.append(f"  模型: {model}")
                lines.append(f"    - 总调用: {total} 次")
                lines.append(f"    - 成功: {usage['success']} 次")
                lines.append(f"    - 失败: {usage['failure']} 次")
        
        lines.append("="*60)
        return "\n".join(lines)
