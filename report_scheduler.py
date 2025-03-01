#!/usr/bin/env python3
"""
Lập lịch tự động cho các báo cáo

Module này tự động lập lịch và gửi các loại báo cáo khác nhau qua email và Telegram
theo lịch được cấu hình sẵn.
"""

import os
import json
import logging
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("report_scheduler")

# Import các module khác
try:
    from telegram_notify import telegram_notifier
except ImportError:
    logger.warning("Không thể import telegram_notifier")
    telegram_notifier = None

try:
    from email_report import EmailReporter
except ImportError:
    logger.warning("Không thể import EmailReporter")
    EmailReporter = None

try:
    from signal_report import SignalReporter
except ImportError:
    logger.warning("Không thể import SignalReporter")
    SignalReporter = None

try:
    from training_report import TrainingReporter
except ImportError:
    logger.warning("Không thể import TrainingReporter")
    TrainingReporter = None

try:
    from daily_report import main as generate_daily_report
except ImportError:
    logger.warning("Không thể import daily_report.main")
    generate_daily_report = None

try:
    from market_report import MarketReporter
except ImportError:
    logger.warning("Không thể import MarketReporter")
    MarketReporter = None

class ReportScheduler:
    """Lớp lập lịch và gửi báo cáo tự động"""
    
    def __init__(self, config_file="report_config.json"):
        """
        Khởi tạo Report Scheduler.
        
        Args:
            config_file (str): Đường dẫn đến file cấu hình
        """
        self.config_file = config_file
        self.config = self._load_config()
        
        # Khởi tạo các đối tượng báo cáo
        self.email_reporter = EmailReporter() if EmailReporter else None
        self.signal_reporter = SignalReporter() if SignalReporter else None
        self.training_reporter = TrainingReporter() if TrainingReporter else None
        self.market_reporter = MarketReporter() if MarketReporter else None
        
        # Các thư mục cần thiết
        self._create_directories()
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file.
        
        Returns:
            Dict: Cấu hình báo cáo
        """
        default_config = {
            "email": {
                "enabled": True,
                "recipients": ["user@example.com"],
                "schedules": {
                    "daily_report": "18:00",
                    "signal_report": "08:00,16:00",
                    "market_report": "09:00",
                    "training_report": "after_training"
                }
            },
            "telegram": {
                "enabled": True,
                "schedules": {
                    "daily_report": "18:00",
                    "signal_report": "08:00,12:00,16:00,20:00",
                    "market_report": "09:00,21:00",
                    "training_report": "after_training"
                }
            },
            "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT"]
        }
        
        # Kiểm tra file cấu hình
        if not os.path.exists(self.config_file):
            logger.info(f"Không tìm thấy file cấu hình {self.config_file}, tạo cấu hình mặc định")
            self._save_config(default_config)
            return default_config
        
        # Tải cấu hình
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            return default_config
    
    def _save_config(self, config: Dict) -> bool:
        """
        Lưu cấu hình vào file.
        
        Args:
            config (Dict): Cấu hình báo cáo
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Đã lưu cấu hình vào {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
            return False
    
    def _create_directories(self) -> None:
        """Tạo các thư mục cần thiết"""
        dirs = ["data", "reports", "reports/charts", "logs", "models"]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def _parse_time_schedule(self, time_str: str) -> List[tuple]:
        """
        Phân tích chuỗi thời gian lập lịch.
        
        Args:
            time_str (str): Chuỗi thời gian (vd: "08:00,16:00")
            
        Returns:
            List[tuple]: Danh sách các tuple (giờ, phút)
        """
        time_list = []
        
        if not time_str or time_str == "after_training":
            return time_list
        
        try:
            time_parts = time_str.split(",")
            for part in time_parts:
                hour, minute = part.strip().split(":")
                time_list.append((int(hour), int(minute)))
            
            return time_list
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thời gian lập lịch '{time_str}': {e}")
            return time_list
    
    def setup_schedules(self) -> None:
        """Thiết lập lịch trình gửi báo cáo"""
        # Lấy cấu hình
        email_config = self.config.get("email", {})
        telegram_config = self.config.get("telegram", {})
        
        symbols = self.config.get("symbols", ["BTCUSDT", "ETHUSDT"])
        
        # Lập lịch cho email
        if email_config.get("enabled", False) and self.email_reporter and self.email_reporter.enabled:
            recipients = email_config.get("recipients", [])
            if not recipients:
                logger.warning("Không có người nhận email được cấu hình")
            else:
                schedules = email_config.get("schedules", {})
                
                # Báo cáo hàng ngày
                if "daily_report" in schedules and generate_daily_report:
                    times = self._parse_time_schedule(schedules["daily_report"])
                    for hour, minute in times:
                        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                            self.send_daily_report_email, recipients=recipients
                        )
                        logger.info(f"Đã lập lịch gửi báo cáo hàng ngày qua email lúc {hour:02d}:{minute:02d}")
                
                # Báo cáo tín hiệu
                if "signal_report" in schedules and self.signal_reporter:
                    times = self._parse_time_schedule(schedules["signal_report"])
                    for hour, minute in times:
                        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                            self.send_signal_report_email, recipients=recipients
                        )
                        logger.info(f"Đã lập lịch gửi báo cáo tín hiệu qua email lúc {hour:02d}:{minute:02d}")
                
                # Báo cáo thị trường
                if "market_report" in schedules and self.market_reporter:
                    times = self._parse_time_schedule(schedules["market_report"])
                    for hour, minute in times:
                        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                            self.send_market_report_email, recipients=recipients, symbols=symbols
                        )
                        logger.info(f"Đã lập lịch gửi báo cáo thị trường qua email lúc {hour:02d}:{minute:02d}")
        
        # Lập lịch cho Telegram
        if telegram_config.get("enabled", False) and telegram_notifier and telegram_notifier.enabled:
            schedules = telegram_config.get("schedules", {})
            
            # Báo cáo hàng ngày
            if "daily_report" in schedules and telegram_notifier and generate_daily_report:
                times = self._parse_time_schedule(schedules["daily_report"])
                for hour, minute in times:
                    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                        self.send_daily_report_telegram
                    )
                    logger.info(f"Đã lập lịch gửi báo cáo hàng ngày qua Telegram lúc {hour:02d}:{minute:02d}")
            
            # Báo cáo tín hiệu
            if "signal_report" in schedules and self.signal_reporter:
                times = self._parse_time_schedule(schedules["signal_report"])
                for hour, minute in times:
                    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                        self.send_signal_report_telegram
                    )
                    logger.info(f"Đã lập lịch gửi báo cáo tín hiệu qua Telegram lúc {hour:02d}:{minute:02d}")
            
            # Báo cáo thị trường
            if "market_report" in schedules and self.market_reporter:
                times = self._parse_time_schedule(schedules["market_report"])
                for hour, minute in times:
                    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                        self.send_market_report_telegram, symbols=symbols
                    )
                    logger.info(f"Đã lập lịch gửi báo cáo thị trường qua Telegram lúc {hour:02d}:{minute:02d}")
        
        # Báo cáo huấn luyện mô hình sẽ được gửi khi có sự kiện huấn luyện
    
    def send_daily_report_email(self, recipients: List[str]) -> bool:
        """
        Gửi báo cáo hàng ngày qua email.
        
        Args:
            recipients (List[str]): Danh sách người nhận
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        logger.info("Đang gửi báo cáo hàng ngày qua email")
        
        try:
            # Tạo báo cáo hàng ngày
            if generate_daily_report:
                generate_daily_report()
            
            # Gửi báo cáo qua email
            for recipient in recipients:
                self.email_reporter.send_daily_report(recipient)
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo hàng ngày qua email: {e}")
            return False
    
    def send_daily_report_telegram(self) -> bool:
        """
        Gửi báo cáo hàng ngày qua Telegram.
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        logger.info("Đang gửi báo cáo hàng ngày qua Telegram")
        
        try:
            # Tạo báo cáo hàng ngày
            if generate_daily_report:
                generate_daily_report()
            
            # Tải trạng thái giao dịch
            try:
                with open("trading_state.json", "r") as f:
                    state = json.load(f)
                
                # Tạo dữ liệu hiệu suất
                balance = state.get("balance", 0)
                positions = state.get("positions", [])
                trade_history = state.get("trade_history", [])
                
                # Tính hiệu suất
                winning_trades = sum(1 for trade in trade_history if trade.get("pnl", 0) > 0)
                total_trades = len(trade_history)
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                # Tạo dữ liệu báo cáo
                performance_data = {
                    "current_balance": balance,
                    "daily_pnl": sum(trade.get("pnl", 0) for trade in trade_history if 
                                    datetime.fromisoformat(trade.get("exit_time", datetime.now().isoformat())).date() == datetime.now().date()),
                    "daily_trades": sum(1 for trade in trade_history if 
                                      datetime.fromisoformat(trade.get("exit_time", datetime.now().isoformat())).date() == datetime.now().date()),
                    "win_rate": win_rate / 100,
                    "open_positions": positions
                }
                
                # Gửi báo cáo qua Telegram
                return telegram_notifier.send_daily_report(performance_data)
            
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu giao dịch: {e}")
                return telegram_notifier.send_message("<b>📊 BÁO CÁO HÀNG NGÀY</b>\n\nKhông thể tải dữ liệu giao dịch để tạo báo cáo.")
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo hàng ngày qua Telegram: {e}")
            return False
    
    def send_signal_report_email(self, recipients: List[str]) -> bool:
        """
        Gửi báo cáo tín hiệu qua email.
        
        Args:
            recipients (List[str]): Danh sách người nhận
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        logger.info("Đang gửi báo cáo tín hiệu qua email")
        
        try:
            # Tạo báo cáo tín hiệu
            report = self.signal_reporter.generate_signal_report()
            
            if not report:
                logger.warning("Không thể tạo báo cáo tín hiệu")
                return False
            
            # Lưu báo cáo
            self.signal_reporter.save_report(report)
            
            # Gửi báo cáo qua email
            for recipient in recipients:
                self.email_reporter.send_signal_report(recipient)
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo tín hiệu qua email: {e}")
            return False
    
    def send_signal_report_telegram(self) -> bool:
        """
        Gửi báo cáo tín hiệu qua Telegram.
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        logger.info("Đang gửi báo cáo tín hiệu qua Telegram")
        
        try:
            # Tạo báo cáo tín hiệu
            report = self.signal_reporter.generate_signal_report()
            
            if not report:
                logger.warning("Không thể tạo báo cáo tín hiệu")
                return False
            
            # Lưu báo cáo
            self.signal_reporter.save_report(report)
            
            # Gửi báo cáo qua Telegram
            return self.signal_reporter.send_telegram_notification(report)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo tín hiệu qua Telegram: {e}")
            return False
    
    def send_market_report_email(self, recipients: List[str], symbols: List[str]) -> bool:
        """
        Gửi báo cáo thị trường qua email.
        
        Args:
            recipients (List[str]): Danh sách người nhận
            symbols (List[str]): Danh sách các cặp giao dịch
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        logger.info("Đang gửi báo cáo thị trường qua email")
        
        try:
            # Tạo báo cáo thị trường cho mỗi cặp
            for symbol in symbols:
                # Tạo báo cáo
                report = self.market_reporter.generate_market_report(symbol)
                
                if not report:
                    logger.warning(f"Không thể tạo báo cáo thị trường cho {symbol}")
                    continue
                
                # Lưu báo cáo
                report_path = self.market_reporter.save_report(report)
                
                if not report_path:
                    logger.warning(f"Không thể lưu báo cáo thị trường cho {symbol}")
                    continue
                
                # Tạo báo cáo văn bản
                text_report = self.market_reporter.generate_text_report(report)
                
                # Lưu báo cáo văn bản
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                text_report_path = os.path.join("reports", f"market_report_{symbol}_{timestamp}.txt")
                
                with open(text_report_path, "w", encoding="utf-8") as f:
                    f.write(text_report)
                
                # Gửi báo cáo qua email
                for recipient in recipients:
                    # Thu thập các file đính kèm (biểu đồ)
                    attachments = []
                    for tf, chart_path in report.get("charts", {}).items():
                        if os.path.exists(chart_path):
                            attachments.append(chart_path)
                    
                    # Tạo email
                    subject = f"Báo cáo thị trường: {symbol} - {datetime.now().strftime('%d/%m/%Y')}"
                    self.email_reporter.send_email(
                        subject=subject,
                        to_email=recipient,
                        text_content=text_report,
                        attachments=attachments
                    )
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo thị trường qua email: {e}")
            return False
    
    def send_market_report_telegram(self, symbols: List[str]) -> bool:
        """
        Gửi báo cáo thị trường qua Telegram.
        
        Args:
            symbols (List[str]): Danh sách các cặp giao dịch
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        logger.info("Đang gửi báo cáo thị trường qua Telegram")
        
        try:
            # Tạo báo cáo thị trường cho mỗi cặp
            for symbol in symbols:
                # Tạo báo cáo
                report = self.market_reporter.generate_market_report(symbol)
                
                if not report:
                    logger.warning(f"Không thể tạo báo cáo thị trường cho {symbol}")
                    continue
                
                # Lưu báo cáo
                self.market_reporter.save_report(report)
                
                # Gửi báo cáo qua Telegram
                self.market_reporter.send_telegram_notification(report)
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo thị trường qua Telegram: {e}")
            return False
    
    def send_training_report(self) -> bool:
        """
        Gửi báo cáo huấn luyện mô hình.
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        logger.info("Đang gửi báo cáo huấn luyện mô hình")
        
        try:
            # Tạo báo cáo huấn luyện
            report = self.training_reporter.generate_training_report()
            
            if not report:
                logger.warning("Không thể tạo báo cáo huấn luyện")
                return False
            
            # Lưu báo cáo
            self.training_reporter.save_report(report)
            
            # Gửi báo cáo qua Telegram
            self.training_reporter.send_telegram_notification(report)
            
            # Gửi báo cáo qua email
            email_config = self.config.get("email", {})
            if email_config.get("enabled", False) and self.email_reporter and self.email_reporter.enabled:
                recipients = email_config.get("recipients", [])
                for recipient in recipients:
                    # TODO: Tạo phương thức gửi báo cáo huấn luyện qua email
                    pass
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo huấn luyện: {e}")
            return False
    
    def run(self) -> None:
        """Chạy lập lịch báo cáo"""
        # Thiết lập lịch trình
        self.setup_schedules()
        
        logger.info("Bắt đầu chạy lập lịch báo cáo")
        
        try:
            # Vòng lặp vô hạn
            while True:
                # Chạy các tác vụ đến hạn
                schedule.run_pending()
                
                # Ngủ 1 phút
                time.sleep(60)
        
        except KeyboardInterrupt:
            logger.info("Đã dừng lập lịch báo cáo")

def main():
    """Hàm chính"""
    # Tạo lập lịch báo cáo
    scheduler = ReportScheduler()
    
    # Chạy lập lịch
    scheduler.run()

if __name__ == "__main__":
    main()