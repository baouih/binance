#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scheduler tự động cho điểm vào lệnh tối ưu

Module này lên lịch thực thi các chiến lược giao dịch dựa trên thời gian tối ưu,
giúp tự động hóa quá trình vào lệnh theo các khung thời gian cụ thể.
"""

import os
import sys
import json
import time
import logging
import argparse
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import schedule

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('optimized_entry_scheduler.log')
    ]
)

logger = logging.getLogger('optimized_entry_scheduler')

# Thử import các module khác
try:
    from time_optimized_strategy import TimeOptimizedStrategy
except ImportError:
    logger.error("Không thể import module TimeOptimizedStrategy. Hãy đảm bảo tệp time_optimized_strategy.py tồn tại")
    sys.exit(1)

try:
    from telegram_notifier import TelegramNotifier
except ImportError:
    # Giả lập TelegramNotifier nếu không import được
    class TelegramNotifier:
        def __init__(self, token=None, chat_id=None, config_path=None):
            self.enabled = False
            self.token = token
            self.chat_id = chat_id
        
        def send_message(self, message, parse_mode=None):
            logger.info(f"[TELEGRAM] {message}")
            return True

class OptimizedEntryScheduler:
    """
    Scheduler tự động cho điểm vào lệnh tối ưu
    """
    
    def __init__(
        self, 
        config_path: str = "configs/entry_scheduler_config.json",
        strategy_config_path: str = "configs/time_optimized_strategy_config.json",
        telegram_config_path: str = "telegram_config.json"
    ):
        """
        Khởi tạo scheduler

        Args:
            config_path (str, optional): Đường dẫn đến file cấu hình scheduler. Defaults to "configs/entry_scheduler_config.json".
            strategy_config_path (str, optional): Đường dẫn đến file cấu hình chiến lược. Defaults to "configs/time_optimized_strategy_config.json".
            telegram_config_path (str, optional): Đường dẫn đến file cấu hình Telegram. Defaults to "telegram_config.json".
        """
        self.config_path = config_path
        self.strategy_config_path = strategy_config_path
        self.telegram_config_path = telegram_config_path
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Khởi tạo chiến lược tối ưu
        self.strategy = TimeOptimizedStrategy(strategy_config_path)
        
        # Khởi tạo Telegram Notifier
        self.telegram = TelegramNotifier(config_path=telegram_config_path)
        
        # Biến theo dõi trạng thái
        self.is_running = False
        self.scheduler_thread = None
        self.scheduled_jobs = {}
        
        # Cấu hình lịch trình
        self.schedule_configs = self.config.get("schedule_configs", [
            {
                "name": "London Open",
                "time": "14:55",
                "days": [0, 1, 2, 3, 4],  # Thứ 2 - Thứ 6
                "enabled": True,
                "message": "Chuẩn bị phiên London Open (15:00-17:00), ưu tiên tìm lệnh SHORT"
            },
            {
                "name": "New York Open",
                "time": "20:25",
                "days": [0, 1, 2, 3, 4],  # Thứ 2 - Thứ 6
                "enabled": True,
                "message": "Chuẩn bị phiên New York Open (20:30-22:30), ưu tiên tìm lệnh SHORT"
            },
            {
                "name": "Daily Candle Close",
                "time": "06:25",
                "days": [0, 1, 2, 3, 4],  # Thứ 2 - Thứ 6
                "enabled": True,
                "message": "Chuẩn bị phiên Daily Candle Close (06:30-07:30), xem xét lệnh LONG có điều kiện"
            },
            {
                "name": "Major News Events",
                "time": "21:25",
                "days": [1, 3],  # Thứ 3, Thứ 5 (ngày công bố tin tức quan trọng)
                "enabled": True,
                "message": "Chuẩn bị phiên Major News Events (21:30-22:00), ưu tiên tìm lệnh SHORT"
            },
            {
                "name": "Daily Summary",
                "time": "22:00",
                "days": [0, 1, 2, 3, 4, 5, 6],  # Tất cả các ngày
                "enabled": True,
                "message": "Tổng kết ngày giao dịch"
            },
            {
                "name": "Weekend Alert",
                "time": "18:00",
                "days": [4],  # Thứ 6
                "enabled": True,
                "message": "Cảnh báo giao dịch cuối tuần: Khối lượng thấp, hạn chế số lệnh còn 2 lệnh/ngày"
            }
        ])
        
        logger.info(f"Đã khởi tạo OptimizedEntryScheduler với {len(self.schedule_configs)} lịch trình")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file

        Returns:
            Dict: Cấu hình
        """
        config = {}
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
            else:
                logger.warning(f"Không tìm thấy file cấu hình {self.config_path}, sử dụng cấu hình mặc định")
                # Tạo cấu hình mặc định
                config = self._create_default_config()
                # Lưu cấu hình mặc định
                self._save_config(config)
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            config = self._create_default_config()
        
        return config
    
    def _create_default_config(self) -> Dict:
        """
        Tạo cấu hình mặc định

        Returns:
            Dict: Cấu hình mặc định
        """
        default_config = {
            "enabled": True,
            "notification": {
                "enabled": True,
                "session_reminder": True,
                "daily_summary": True
            },
            "schedule_configs": [
                {
                    "name": "London Open",
                    "time": "14:55",
                    "days": [0, 1, 2, 3, 4],  # Thứ 2 - Thứ 6
                    "enabled": True,
                    "message": "Chuẩn bị phiên London Open (15:00-17:00), ưu tiên tìm lệnh SHORT"
                },
                {
                    "name": "New York Open",
                    "time": "20:25",
                    "days": [0, 1, 2, 3, 4],  # Thứ 2 - Thứ 6
                    "enabled": True,
                    "message": "Chuẩn bị phiên New York Open (20:30-22:30), ưu tiên tìm lệnh SHORT"
                },
                {
                    "name": "Daily Candle Close",
                    "time": "06:25",
                    "days": [0, 1, 2, 3, 4],  # Thứ 2 - Thứ 6
                    "enabled": True,
                    "message": "Chuẩn bị phiên Daily Candle Close (06:30-07:30), xem xét lệnh LONG có điều kiện"
                },
                {
                    "name": "Major News Events",
                    "time": "21:25",
                    "days": [1, 3],  # Thứ 3, Thứ 5 (ngày công bố tin tức quan trọng)
                    "enabled": True,
                    "message": "Chuẩn bị phiên Major News Events (21:30-22:00), ưu tiên tìm lệnh SHORT"
                },
                {
                    "name": "Daily Summary",
                    "time": "22:00",
                    "days": [0, 1, 2, 3, 4, 5, 6],  # Tất cả các ngày
                    "enabled": True,
                    "message": "Tổng kết ngày giao dịch"
                },
                {
                    "name": "Weekend Alert",
                    "time": "18:00",
                    "days": [4],  # Thứ 6
                    "enabled": True,
                    "message": "Cảnh báo giao dịch cuối tuần: Khối lượng thấp, hạn chế số lệnh còn 2 lệnh/ngày"
                }
            ],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return default_config
    
    def _save_config(self, config: Dict = None):
        """
        Lưu cấu hình vào file

        Args:
            config (Dict, optional): Cấu hình cần lưu. Defaults to None.
        """
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
    
    def handle_scheduled_event(self, schedule_name: str) -> None:
        """
        Xử lý sự kiện theo lịch trình

        Args:
            schedule_name (str): Tên lịch trình
        """
        now = datetime.now()
        weekday = now.weekday()
        
        # Tìm cấu hình lịch trình
        schedule_config = None
        for config in self.schedule_configs:
            if config["name"] == schedule_name:
                schedule_config = config
                break
        
        if not schedule_config:
            logger.error(f"Không tìm thấy cấu hình lịch trình {schedule_name}")
            return
        
        # Kiểm tra xem ngày hiện tại có trong danh sách ngày của lịch trình không
        if weekday not in schedule_config.get("days", []):
            logger.info(f"Lịch trình {schedule_name} không chạy vào ngày {weekday}")
            return
        
        # Kiểm tra xem lịch trình có được bật không
        if not schedule_config.get("enabled", True):
            logger.info(f"Lịch trình {schedule_name} đã bị tắt")
            return
        
        # Kiểm tra xem thông báo có được bật không
        if not self.config.get("notification", {}).get("enabled", True):
            logger.info(f"Thông báo đã bị tắt, không gửi thông báo cho lịch trình {schedule_name}")
            return
        
        # Xử lý các lịch trình cụ thể
        if schedule_name == "Daily Summary":
            self.send_daily_summary()
        elif schedule_name == "Weekend Alert":
            self.send_weekend_alert()
        else:
            # Gửi thông báo nhắc nhở về phiên giao dịch
            self.send_session_reminder(schedule_config)
    
    def send_session_reminder(self, schedule_config: Dict) -> None:
        """
        Gửi thông báo nhắc nhở về phiên giao dịch

        Args:
            schedule_config (Dict): Cấu hình lịch trình
        """
        if not self.config.get("notification", {}).get("session_reminder", True):
            return
        
        message = f"🔔 *NHẮC NHỞ PHIÊN GIAO DỊCH* 🔔\n\n"
        message += f"⏰ *{schedule_config['name']}*\n\n"
        
        # Thông điệp chính
        message += f"{schedule_config.get('message', '')}\n\n"
        
        # Thêm thông tin từ chiến lược tối ưu
        optimal_times = self.strategy.get_all_optimal_times()
        for time_info in optimal_times:
            if time_info["name"] == schedule_config["name"]:
                message += f"🕒 Thời gian: {time_info['start_time']} - {time_info['end_time']}\n"
                message += f"📈 Tỷ lệ thắng: {time_info['win_rate']:.1f}%\n"
                message += f"🧭 Hướng khuyến nghị: {time_info['direction'].upper()}\n"
                
                if time_info["symbols"]:
                    message += f"🪙 Coin khuyến nghị: {', '.join(time_info['symbols'])}\n"
                
                break
        
        # Thêm thông tin về điều kiện vào lệnh tối ưu
        message += "\n⚠️ *Điều kiện vào lệnh*:\n"
        if schedule_config["name"] == "London Open" or schedule_config["name"] == "New York Open":
            message += "• RSI > 65 (1h)\n"
            message += "• MACD Histogram âm hoặc vừa cắt xuống\n"
            message += "• Giá cách EMA21 > 1%\n"
            message += "• Khối lượng giao dịch tăng (> 1.2x trung bình)\n"
        elif schedule_config["name"] == "Daily Candle Close":
            message += "• RSI < 40 (1h)\n"
            message += "• MACD Histogram dương hoặc vừa cắt lên\n"
            message += "• Giá cách EMA21 < -1%\n"
            message += "• Khối lượng giao dịch tăng (> 1.2x trung bình)\n"
        
        # Thêm thông tin về ngày trong tuần
        now = datetime.now()
        weekday = now.weekday()
        weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
        max_trades = self.strategy.max_trades_by_weekday.get(str(weekday), self.strategy.max_trades_by_weekday.get(weekday, 3))
        
        message += f"\n📅 Hôm nay ({weekday_names[weekday]}): tối đa {max_trades} lệnh"
        
        # Gửi thông báo
        self.telegram.send_message(message, parse_mode="Markdown")
        
        logger.info(f"Đã gửi nhắc nhở phiên {schedule_config['name']}")
    
    def send_daily_summary(self) -> None:
        """
        Gửi tóm tắt hàng ngày
        """
        if not self.config.get("notification", {}).get("daily_summary", True):
            return
        
        # Lấy tóm tắt về chiến lược giao dịch
        summary = self.strategy.get_trading_summary()
        
        # Tạo thông báo
        message = f"📊 *TÓM TẮT GIAO DỊCH HÀNG NGÀY* 📊\n\n"
        
        # Thông tin về ngày
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
        tomorrow_weekday_name = weekday_names[tomorrow.weekday()]
        
        message += f"📅 *Ngày*: {now.strftime('%d/%m/%Y')} ({weekday_names[now.weekday()]})\n"
        message += f"⏰ *Múi giờ*: UTC+{self.strategy.timezone_offset}\n\n"
        
        # Thông tin về giao dịch hôm nay
        message += f"📈 *Giao dịch hôm nay*: {summary.get('trades_today_count', 0)}/{summary.get('max_trades_today', 5)}\n\n"
        
        # Thông tin về ngày mai
        tomorrow_weekday = tomorrow.weekday()
        max_trades_tomorrow = self.strategy.max_trades_by_weekday.get(str(tomorrow_weekday), self.strategy.max_trades_by_weekday.get(tomorrow_weekday, 3))
        
        message += f"🔍 *Ngày mai ({tomorrow_weekday_name})*: tối đa {max_trades_tomorrow} lệnh\n\n"
        
        # Lấy các phiên giao dịch cho ngày mai
        tomorrow_sessions = []
        for config in self.schedule_configs:
            if tomorrow_weekday in config.get("days", []) and config.get("enabled", True) and config["name"] != "Daily Summary":
                # Tìm thông tin thời gian từ chiến lược tối ưu
                for time_info in summary.get("top_times", []):
                    if time_info["name"] == config["name"]:
                        tomorrow_sessions.append({
                            "name": config["name"],
                            "time": config.get("time", ""),
                            "direction": time_info.get("direction", "both"),
                            "win_rate": time_info.get("win_rate", 0)
                        })
                        break
        
        # Sắp xếp theo tỷ lệ thắng giảm dần
        tomorrow_sessions.sort(key=lambda x: x.get("win_rate", 0), reverse=True)
        
        # Thêm thông tin về các phiên giao dịch ngày mai
        if tomorrow_sessions:
            message += "🕒 *Các phiên giao dịch ngày mai*:\n"
            for i, session in enumerate(tomorrow_sessions, 1):
                message += f"{i}. {session['name']} - {session.get('time', '')} - {session.get('direction', 'both').upper()} ({session.get('win_rate', 0):.1f}%)\n"
        
        # Thêm lời khuyên
        message += "\n💡 *Lời khuyên*:\n"
        message += "• Chỉ vào lệnh khi có tín hiệu rõ ràng\n"
        message += "• Tuân thủ quản lý vốn và số lệnh tối đa\n"
        message += "• Đặt SL/TP ngay khi vào lệnh\n"
        
        # Gửi thông báo
        self.telegram.send_message(message, parse_mode="Markdown")
        
        logger.info("Đã gửi tóm tắt hàng ngày")
    
    def send_weekend_alert(self) -> None:
        """
        Gửi cảnh báo cuối tuần
        """
        message = f"⚠️ *CẢNH BÁO GIAO DỊCH CUỐI TUẦN* ⚠️\n\n"
        message += "Sắp bước vào cuối tuần, thị trường thường có khối lượng thấp và biến động khó đoán.\n\n"
        
        message += "🚫 *Hạn chế*:\n"
        message += "• Giảm số lệnh tối đa xuống 2 lệnh/ngày\n"
        message += "• Giảm kích thước vị thế xuống 50%\n"
        message += "• Tránh giao dịch khi có biến động bất thường\n\n"
        
        message += "✅ *Khuyến nghị*:\n"
        message += "• Ưu tiên bảo toàn vốn hơn tìm kiếm lợi nhuận\n"
        message += "• Chỉ vào lệnh khi có tín hiệu cực kỳ rõ ràng\n"
        message += "• Nghỉ ngơi, xem lại các giao dịch trong tuần\n"
        
        # Gửi thông báo
        self.telegram.send_message(message, parse_mode="Markdown")
        
        logger.info("Đã gửi cảnh báo cuối tuần")
    
    def schedule_all_jobs(self) -> None:
        """
        Lên lịch cho tất cả các công việc
        """
        # Xóa tất cả các job hiện tại
        schedule.clear()
        self.scheduled_jobs.clear()
        
        # Lên lịch cho từng công việc
        for config in self.schedule_configs:
            if not config.get("enabled", True):
                continue
            
            time_str = config.get("time", "00:00")
            job = schedule.every().day.at(time_str).do(self.handle_scheduled_event, config["name"])
            
            self.scheduled_jobs[config["name"]] = {
                "job": job,
                "time": time_str,
                "days": config.get("days", []),
                "enabled": config.get("enabled", True)
            }
            
            logger.info(f"Đã lên lịch cho {config['name']} lúc {time_str}")
    
    def start(self) -> None:
        """
        Bắt đầu scheduler
        """
        if self.is_running:
            logger.warning("Scheduler đã đang chạy")
            return
        
        self.is_running = True
        
        # Lên lịch cho tất cả các công việc
        self.schedule_all_jobs()
        
        # Gửi thông báo khởi động
        startup_message = f"🚀 *ENTRY SCHEDULER ĐÃ KHỞI ĐỘNG* 🚀\n\n"
        startup_message += f"⏰ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        startup_message += "📋 *Các lịch trình*:\n"
        for config in self.schedule_configs:
            if config.get("enabled", True):
                days_str = ", ".join([["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"][d] for d in config.get("days", [])])
                startup_message += f"• {config['name']} - {config.get('time', '')} ({days_str})\n"
        
        self.telegram.send_message(startup_message, parse_mode="Markdown")
        
        # Chạy scheduler trong thread riêng
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Đã bắt đầu scheduler")
    
    def _run_scheduler(self) -> None:
        """
        Chạy scheduler trong thread
        """
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self) -> None:
        """
        Dừng scheduler
        """
        if not self.is_running:
            logger.warning("Scheduler chưa được khởi động")
            return
        
        self.is_running = False
        
        # Gửi thông báo dừng
        stop_message = f"🛑 *ENTRY SCHEDULER ĐÃ DỪNG* 🛑\n\n"
        stop_message += f"⏰ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        self.telegram.send_message(stop_message, parse_mode="Markdown")
        
        logger.info("Đã dừng scheduler")
    
    def get_next_scheduled_events(self, count: int = 5) -> List[Dict]:
        """
        Lấy danh sách các sự kiện sắp tới

        Args:
            count (int, optional): Số lượng sự kiện tối đa. Defaults to 5.

        Returns:
            List[Dict]: Danh sách các sự kiện sắp tới
        """
        now = datetime.now()
        today_weekday = now.weekday()
        
        upcoming_events = []
        
        # Duyệt qua 7 ngày tới
        for day_offset in range(7):
            future_date = now + timedelta(days=day_offset)
            future_weekday = (today_weekday + day_offset) % 7
            
            # Kiểm tra từng công việc
            for config in self.schedule_configs:
                if not config.get("enabled", True):
                    continue
                
                # Kiểm tra xem ngày này có trong lịch trình không
                if future_weekday not in config.get("days", []):
                    continue
                
                # Lấy thời gian của sự kiện
                time_parts = config.get("time", "00:00").split(":")
                event_time = future_date.replace(
                    hour=int(time_parts[0]),
                    minute=int(time_parts[1]),
                    second=0,
                    microsecond=0
                )
                
                # Nếu là ngày hôm nay và thời gian đã qua, bỏ qua
                if day_offset == 0 and event_time < now:
                    continue
                
                # Thêm vào danh sách
                upcoming_events.append({
                    "name": config["name"],
                    "time": event_time,
                    "days_from_now": day_offset,
                    "message": config.get("message", "")
                })
        
        # Sắp xếp theo thời gian
        upcoming_events.sort(key=lambda x: x["time"])
        
        # Giới hạn số lượng
        return upcoming_events[:count]
    
    def print_upcoming_events(self) -> None:
        """
        In ra các sự kiện sắp tới
        """
        upcoming_events = self.get_next_scheduled_events()
        
        print("\n===== CÁC SỰ KIỆN SẮP TỚI =====")
        
        for i, event in enumerate(upcoming_events, 1):
            event_time = event["time"]
            days_from_now = event["days_from_now"]
            
            if days_from_now == 0:
                day_str = "Hôm nay"
            elif days_from_now == 1:
                day_str = "Ngày mai"
            else:
                weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
                day_str = f"{weekday_names[event_time.weekday()]} ({days_from_now} ngày nữa)"
            
            print(f"{i}. {event['name']} - {event_time.strftime('%H:%M')} {day_str}")
            print(f"   {event['message']}")
            print()

def setup_environment():
    """
    Thiết lập môi trường làm việc
    """
    # Tạo thư mục configs nếu chưa tồn tại
    os.makedirs("configs", exist_ok=True)

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Lên lịch tự động cho điểm vào lệnh tối ưu')
    parser.add_argument('--config', type=str, default='configs/entry_scheduler_config.json', help='Đường dẫn đến file cấu hình')
    parser.add_argument('--strategy-config', type=str, default='configs/time_optimized_strategy_config.json', help='Đường dẫn đến file cấu hình chiến lược')
    parser.add_argument('--telegram-config', type=str, default='telegram_config.json', help='Đường dẫn đến file cấu hình Telegram')
    parser.add_argument('--reset', action='store_true', help='Reset cấu hình về mặc định')
    parser.add_argument('--list', action='store_true', help='Liệt kê các sự kiện sắp tới')
    args = parser.parse_args()
    
    # Thiết lập môi trường
    setup_environment()
    
    # Nếu yêu cầu reset cấu hình
    if args.reset and os.path.exists(args.config):
        os.remove(args.config)
        logger.info(f"Đã xóa file cấu hình {args.config}")
    
    # Khởi tạo scheduler
    scheduler = OptimizedEntryScheduler(
        config_path=args.config,
        strategy_config_path=args.strategy_config,
        telegram_config_path=args.telegram_config
    )
    
    # Nếu chỉ yêu cầu liệt kê các sự kiện sắp tới
    if args.list:
        scheduler.print_upcoming_events()
        return
    
    # Hiển thị thông tin
    print("\n===== SCHEDULER TỰ ĐỘNG CHO ĐIỂM VÀO LỆNH TỐI ƯU =====")
    print(f"Thời gian hiện tại: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\nCác lịch trình:")
    for config in scheduler.schedule_configs:
        status = "✓" if config.get("enabled", True) else "✗"
        days_str = ", ".join([["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"][d] for d in config.get("days", [])])
        print(f"- {status} {config['name']} - {config.get('time', '')} ({days_str})")
    
    # In ra các sự kiện sắp tới
    scheduler.print_upcoming_events()
    
    # Hiển thị hướng dẫn
    print("\nHướng dẫn:")
    print("- Nhấn Ctrl+C để dừng scheduler")
    
    # Bắt đầu scheduler
    try:
        scheduler.start()
        
        # Chờ kết thúc
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nĐang dừng scheduler...")
        scheduler.stop()
        print("Đã dừng scheduler!")
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {e}", exc_info=True)
        scheduler.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()