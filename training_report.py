#!/usr/bin/env python3
"""
Báo cáo tiến trình huấn luyện mô hình học máy

Module này tạo báo cáo chi tiết về việc huấn luyện mô hình học máy, 
bao gồm các thông số kỹ thuật, kết quả huấn luyện và đánh giá mô hình.
"""

import os
import json
import logging
import time
from datetime import datetime
import glob
import re
from typing import Dict, List, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("training_report")

# Import telegram notifier
from telegram_notify import telegram_notifier

class TrainingReporter:
    """Lớp tạo báo cáo huấn luyện mô hình"""
    
    def __init__(self, log_folder="./logs", model_folder="./models", report_folder="./reports"):
        """
        Khởi tạo Training Reporter.
        
        Args:
            log_folder (str): Thư mục chứa log huấn luyện
            model_folder (str): Thư mục chứa mô hình đã huấn luyện
            report_folder (str): Thư mục lưu báo cáo
        """
        self.log_folder = log_folder
        self.model_folder = model_folder
        self.report_folder = report_folder
        
        # Tạo thư mục nếu chưa tồn tại
        for folder in [log_folder, model_folder, report_folder]:
            os.makedirs(folder, exist_ok=True)
    
    def parse_training_logs(self, log_file=None) -> Dict:
        """
        Đọc và phân tích log huấn luyện.
        
        Args:
            log_file (str, optional): Đường dẫn đến file log, nếu None thì tìm file log mới nhất
            
        Returns:
            Dict: Thông tin huấn luyện được trích xuất
        """
        # Tìm file log mới nhất nếu không chỉ định
        if log_file is None:
            training_logs = glob.glob(os.path.join(self.log_folder, "training_*.log"))
            if not training_logs:
                logger.warning("Không tìm thấy file log huấn luyện")
                return {}
            
            log_file = max(training_logs, key=os.path.getmtime)
        
        logger.info(f"Đang phân tích log huấn luyện: {log_file}")
        
        # Mẫu dữ liệu để thu thập
        training_data = {
            "timestamp": datetime.now().isoformat(),
            "symbols": [],
            "models": [],
            "performance": {},
            "duration": 0,
            "status": "unknown"
        }
        
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
                # Trích xuất thông tin cơ bản
                symbols = re.findall(r"Đã thu thập dữ liệu cho (\w+)", content)
                if symbols:
                    training_data["symbols"] = list(set(symbols))
                
                # Trích xuất thông tin mô hình
                models = re.findall(r"Đã đào tạo (\w+): Accuracy=([\d\.]+), F1=([\d\.]+), Thời gian=([\d\.]+)s", content)
                if models:
                    training_data["models"] = [{
                        "name": model[0],
                        "accuracy": float(model[1]),
                        "f1_score": float(model[2]),
                        "training_time": float(model[3])
                    } for model in models]
                
                # Tính thời gian huấn luyện
                start_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - INFO - Bắt đầu huấn luyện", content)
                end_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - INFO - Hoàn thành huấn luyện", content)
                
                if start_match and end_match:
                    start_time = datetime.strptime(start_match.group(1), "%Y-%m-%d %H:%M:%S")
                    end_time = datetime.strptime(end_match.group(1), "%Y-%m-%d %H:%M:%S")
                    
                    duration = (end_time - start_time).total_seconds()
                    training_data["duration"] = duration
                    training_data["status"] = "completed"
                elif start_match:
                    training_data["status"] = "in_progress"
            
            return training_data
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích log huấn luyện: {e}")
            return training_data
    
    def get_model_info(self) -> Dict:
        """
        Lấy thông tin về các mô hình đã huấn luyện.
        
        Returns:
            Dict: Thông tin về các mô hình
        """
        model_info = {
            "count": 0,
            "last_updated": None,
            "symbols": [],
            "size_mb": 0,
            "models": []
        }
        
        try:
            # Tìm tất cả các file mô hình
            model_files = glob.glob(os.path.join(self.model_folder, "*.joblib"))
            
            if not model_files:
                return model_info
            
            model_info["count"] = len(model_files)
            
            # Tìm file mới nhất
            newest_file = max(model_files, key=os.path.getmtime)
            model_info["last_updated"] = datetime.fromtimestamp(os.path.getmtime(newest_file)).isoformat()
            
            # Tính kích thước tổng
            total_size = sum(os.path.getsize(f) for f in model_files)
            model_info["size_mb"] = total_size / (1024 * 1024)  # Chuyển sang MB
            
            # Trích xuất thông tin từng mô hình
            for model_file in model_files:
                file_name = os.path.basename(model_file)
                # Mẫu tên: symbol_timeframe_modeltype_regime.joblib
                parts = os.path.splitext(file_name)[0].split('_')
                
                if len(parts) >= 2:
                    symbol = parts[0]
                    if symbol not in model_info["symbols"]:
                        model_info["symbols"].append(symbol)
                    
                    model_info["models"].append({
                        "name": file_name,
                        "symbol": symbol,
                        "timeframe": parts[1] if len(parts) > 1 else "unknown",
                        "type": parts[2] if len(parts) > 2 else "unknown",
                        "regime": parts[3] if len(parts) > 3 else "all",
                        "size_mb": os.path.getsize(model_file) / (1024 * 1024),
                        "last_modified": datetime.fromtimestamp(os.path.getmtime(model_file)).isoformat()
                    })
            
            return model_info
        
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin mô hình: {e}")
            return model_info
    
    def generate_training_report(self) -> Dict:
        """
        Tạo báo cáo huấn luyện đầy đủ.
        
        Returns:
            Dict: Báo cáo huấn luyện
        """
        logger.info("Đang tạo báo cáo huấn luyện")
        
        # Thu thập thông tin
        training_log = self.parse_training_logs()
        model_info = self.get_model_info()
        
        # Tạo báo cáo
        report = {
            "timestamp": datetime.now().isoformat(),
            "training": training_log,
            "models": model_info,
            "summary": {
                "status": training_log.get("status", "unknown"),
                "models_count": model_info.get("count", 0),
                "avg_accuracy": 0,
                "active_symbols": model_info.get("symbols", []),
                "last_training": training_log.get("timestamp")
            }
        }
        
        # Tính accuracy trung bình
        models = training_log.get("models", [])
        if models:
            avg_accuracy = sum(model.get("accuracy", 0) for model in models) / len(models)
            report["summary"]["avg_accuracy"] = avg_accuracy
        
        return report
    
    def save_report(self, report: Dict, file_name=None) -> str:
        """
        Lưu báo cáo vào file.
        
        Args:
            report (Dict): Báo cáo để lưu
            file_name (str, optional): Tên file báo cáo, nếu None thì tạo tên tự động
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"training_report_{timestamp}.json"
        
        file_path = os.path.join(self.report_folder, file_name)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Đã lưu báo cáo huấn luyện vào: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu báo cáo: {e}")
            return ""
    
    def send_telegram_notification(self, report: Dict) -> bool:
        """
        Gửi báo cáo huấn luyện qua Telegram.
        
        Args:
            report (Dict): Báo cáo huấn luyện
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not telegram_notifier.enabled:
            logger.warning("Telegram notifier không được kích hoạt")
            return False
        
        try:
            # Trích xuất dữ liệu từ báo cáo
            summary = report.get("summary", {})
            training = report.get("training", {})
            models = report.get("models", {})
            
            # Định dạng tin nhắn
            message = f"<b>🧠 BÁO CÁO HUẤN LUYỆN MÔ HÌNH</b>\n\n"
            
            # Trạng thái
            status = summary.get("status", "unknown")
            if status == "completed":
                message += f"<b>Trạng thái:</b> ✅ Hoàn thành\n"
            elif status == "in_progress":
                message += f"<b>Trạng thái:</b> ⏳ Đang huấn luyện\n"
            else:
                message += f"<b>Trạng thái:</b> ❓ Không xác định\n"
            
            # Thông tin tổng quan
            message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"<b>Số mô hình:</b> {summary.get('models_count', 0)}\n"
            message += f"<b>Độ chính xác TB:</b> {summary.get('avg_accuracy', 0):.2%}\n"
            
            # Cặp tiền được huấn luyện
            symbols = summary.get("active_symbols", [])
            if symbols:
                message += f"<b>Cặp tiền:</b> {', '.join(symbols)}\n\n"
            
            # Chi tiết mô hình
            model_list = training.get("models", [])
            if model_list:
                message += f"<b>CHI TIẾT MÔ HÌNH:</b>\n"
                for model in model_list:
                    name = model.get("name", "")
                    acc = model.get("accuracy", 0)
                    f1 = model.get("f1_score", 0)
                    time = model.get("training_time", 0)
                    
                    # Biểu tượng dựa vào độ chính xác
                    if acc >= 0.9:
                        emoji = "🟢"
                    elif acc >= 0.8:
                        emoji = "🟡"
                    else:
                        emoji = "🔴"
                    
                    message += f"{emoji} <b>{name}</b>: Acc={acc:.2%}, F1={f1:.2%}, Time={time:.1f}s\n"
            
            # Gửi tin nhắn
            return telegram_notifier.send_message(message)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo huấn luyện qua Telegram: {e}")
            return False

def main():
    """Hàm chính để tạo báo cáo huấn luyện"""
    # Tạo thư mục logs và models nếu chưa tồn tại
    os.makedirs("logs", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    reporter = TrainingReporter()
    report = reporter.generate_training_report()
    
    # Lưu báo cáo
    reporter.save_report(report)
    
    # Gửi thông báo qua Telegram
    reporter.send_telegram_notification(report)
    
    print("Báo cáo huấn luyện đã được tạo và gửi đi")

if __name__ == "__main__":
    main()