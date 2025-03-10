#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot Startup - Khởi động và quản lý bot giao dịch
"""

import os
import sys
import time
import signal
import logging
import argparse
import traceback
import threading
import json
import datetime
from pathlib import Path

# Thiết lập logging
os.makedirs("logs", exist_ok=True)
log_file = f"logs/bot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('bot_startup')

# Biến trạng thái toàn cục
running = True
bot_process = None
status_file = "bot_status.json"

class BotManager:
    """
    Lớp quản lý bot giao dịch
    """
    def __init__(self, 
                risk_level=None, 
                test_mode=False, 
                enable_telegram=False,
                symbols=None, 
                config_file=None,
                auto_recovery=True):
        """
        Khởi tạo
        
        Args:
            risk_level (str): Mức độ rủi ro (10, 15, 20, 30)
            test_mode (bool): Chế độ test
            enable_telegram (bool): Kích hoạt thông báo Telegram
            symbols (list): Danh sách cặp tiền
            config_file (str): File cấu hình
            auto_recovery (bool): Tự động khôi phục vị thế
        """
        self.risk_level = risk_level
        self.test_mode = test_mode
        self.enable_telegram = enable_telegram
        self.symbols = symbols
        self.config_file = config_file
        self.auto_recovery = auto_recovery
        
        # Trạng thái
        self.start_time = datetime.datetime.now()
        self.error_count = 0
        self.restart_count = 0
        self.is_running = False
        self.last_error = None
        
        # Khởi tạo thư mục logs
        os.makedirs("logs", exist_ok=True)
        
        # Kiểm tra các thư mục và file cần thiết
        self._check_required_files()
        
        # Khởi tạo file trạng thái
        self._init_status_file()
        
        # Đặt handler xử lý tín hiệu
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _check_required_files(self):
        """Kiểm tra các thư mục và file cần thiết"""
        # Các thư mục cần thiết
        required_dirs = [
            "logs", "risk_configs", "data", "backups",
            "templates", "static", "models"
        ]
        
        # Tạo thư mục nếu chưa tồn tại
        for directory in required_dirs:
            os.makedirs(directory, exist_ok=True)
        
        # Kiểm tra file cấu hình rủi ro
        if self.risk_level:
            risk_config_path = f"risk_configs/risk_level_{self.risk_level}.json"
            if not os.path.exists(risk_config_path):
                logger.warning(f"File cấu hình rủi ro không tồn tại: {risk_config_path}")
                logger.warning("Đang tạo file cấu hình rủi ro mặc định...")
                self._create_default_risk_config(risk_config_path)
        
        # Kiểm tra file cấu hình tài khoản
        if not os.path.exists("account_config.json"):
            if os.path.exists("account_config.json.example"):
                logger.warning("File cấu hình tài khoản không tồn tại, sao chép từ file mẫu...")
                import shutil
                shutil.copy("account_config.json.example", "account_config.json")
            else:
                logger.warning("File cấu hình tài khoản không tồn tại, đang tạo file mặc định...")
                self._create_default_account_config()
    
    def _create_default_risk_config(self, path):
        """Tạo file cấu hình rủi ro mặc định"""
        risk_level = int(self.risk_level) if self.risk_level else 10
        
        # Cấu hình mặc định
        config = {
            "risk_level": risk_level,
            "max_open_positions": 3,
            "max_daily_trades": 10,
            "position_size_percent": risk_level / 100,
            "max_risk_per_trade": risk_level / 100,
            "stop_loss_percent": 2.0,
            "take_profit_percent": 4.0,
            "max_leverage": 5,
            "default_leverage": 3,
            "use_trailing_stop": True,
            "trailing_stop_activation": 1.5,
            "trailing_stop_distance": 1.0,
            "enable_martingale": False,
            "martingale_factor": 1.5,
            "max_martingale_steps": 3
        }
        
        # Lưu file
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"Đã tạo file cấu hình rủi ro mặc định: {path}")
    
    def _create_default_account_config(self):
        """Tạo file cấu hình tài khoản mặc định"""
        config = {
            "api_key": "YOUR_API_KEY",
            "api_secret": "YOUR_API_SECRET",
            "testnet": True,
            "exchange": "binance",
            "base_currency": "USDT",
            "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            "risk_level": 10,
            "enable_notifications": False,
            "telegram_token": "",
            "telegram_chat_id": "",
            "session_hours": 24,
            "auto_restart": True
        }
        
        # Lưu file
        with open("account_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        
        logger.info("Đã tạo file cấu hình tài khoản mặc định")
    
    def _init_status_file(self):
        """Khởi tạo file trạng thái"""
        status = {
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "initializing",
            "risk_level": self.risk_level,
            "test_mode": self.test_mode,
            "error_count": 0,
            "restart_count": 0,
            "last_error": None,
            "running_time": "0m",
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu file
        with open(status_file, "w") as f:
            json.dump(status, f, indent=4)
    
    def _update_status(self, status="running", error=None):
        """Cập nhật file trạng thái"""
        if os.path.exists(status_file):
            try:
                with open(status_file, "r") as f:
                    current_status = json.load(f)
            except:
                current_status = {}
        else:
            current_status = {}
        
        # Cập nhật trạng thái
        current_status["status"] = status
        current_status["risk_level"] = self.risk_level
        current_status["test_mode"] = self.test_mode
        current_status["error_count"] = self.error_count
        current_status["restart_count"] = self.restart_count
        
        if error:
            current_status["last_error"] = str(error)
            self.last_error = str(error)
        
        # Tính thời gian chạy
        running_time = datetime.datetime.now() - self.start_time
        hours, remainder = divmod(running_time.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours >= 24:
            days, hours = divmod(hours, 24)
            current_status["running_time"] = f"{int(days)}d {int(hours)}h {int(minutes)}m"
        elif hours >= 1:
            current_status["running_time"] = f"{int(hours)}h {int(minutes)}m"
        else:
            current_status["running_time"] = f"{int(minutes)}m"
        
        current_status["last_update"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Lưu file
        with open(status_file, "w") as f:
            json.dump(current_status, f, indent=4)
    
    def _signal_handler(self, sig, frame):
        """Xử lý tín hiệu"""
        logger.info(f"Đã nhận tín hiệu {sig}, dừng bot...")
        self.stop()
        sys.exit(0)
    
    def _import_bot_module(self):
        """Import module bot chính"""
        try:
            # Kiểm tra file bot_gui.py
            if os.path.exists("bot_gui.py"):
                import bot_gui
                return bot_gui
            # Kiểm tra file main_bot.py
            elif os.path.exists("main_bot.py"):
                import main_bot
                return main_bot
            # Kiểm tra file trading_bot.py
            elif os.path.exists("trading_bot.py"):
                import trading_bot
                return trading_bot
            else:
                logger.error("Không tìm thấy file bot chính (bot_gui.py, main_bot.py, trading_bot.py)")
                return None
        except Exception as e:
            logger.error(f"Lỗi khi import module bot: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def start(self):
        """Khởi động bot"""
        logger.info("Khởi động bot...")
        
        # Cập nhật trạng thái
        self._update_status("starting")
        
        try:
            # Kiểm tra biến môi trường cho API
            self._check_api_environment()
            
            # Tải module bot
            bot_module = self._import_bot_module()
            if not bot_module:
                raise Exception("Không thể tải module bot")
            
            # Khởi động bot
            self._start_bot_process(bot_module)
            
            # Chạy vòng lặp giám sát
            self._monitor_loop()
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động bot: {str(e)}")
            logger.error(traceback.format_exc())
            self.error_count += 1
            self._update_status("error", error=str(e))
            return False
        
        return True
    
    def _check_api_environment(self):
        """Kiểm tra biến môi trường API"""
        # Nếu đang chạy trên testnet, cần key testnet
        if "BINANCE_TESTNET_API_KEY" in os.environ and "BINANCE_TESTNET_API_SECRET" in os.environ:
            logger.info("Tìm thấy thông tin API Binance Testnet trong biến môi trường")
            # Đảm bảo file cấu hình đã được cập nhật
            self._update_account_config_with_env()
        else:
            # Kiểm tra file cấu hình
            if os.path.exists("account_config.json"):
                with open("account_config.json", "r") as f:
                    config = json.load(f)
                
                # Kiểm tra thông tin API
                if config.get("api_key") == "YOUR_API_KEY" or config.get("api_secret") == "YOUR_API_SECRET":
                    logger.warning("Thông tin API chưa được cấu hình trong file account_config.json")
                    if self.test_mode:
                        logger.info("Đang ở chế độ test, bỏ qua kiểm tra API")
                    else:
                        logger.warning("Vui lòng cập nhật thông tin API trong file account_config.json")
    
    def _update_account_config_with_env(self):
        """Cập nhật file cấu hình với biến môi trường"""
        # Chỉ cập nhật nếu file tồn tại
        if os.path.exists("account_config.json"):
            try:
                with open("account_config.json", "r") as f:
                    config = json.load(f)
                
                # Cập nhật từ biến môi trường
                if "BINANCE_TESTNET_API_KEY" in os.environ:
                    config["api_key"] = os.environ.get("BINANCE_TESTNET_API_KEY")
                
                if "BINANCE_TESTNET_API_SECRET" in os.environ:
                    config["api_secret"] = os.environ.get("BINANCE_TESTNET_API_SECRET")
                
                config["testnet"] = True
                
                # Cập nhật Telegram nếu có
                if "TELEGRAM_BOT_TOKEN" in os.environ:
                    config["telegram_token"] = os.environ.get("TELEGRAM_BOT_TOKEN")
                    config["enable_notifications"] = True
                
                if "TELEGRAM_CHAT_ID" in os.environ:
                    config["telegram_chat_id"] = os.environ.get("TELEGRAM_CHAT_ID")
                
                # Lưu lại file
                with open("account_config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4)
                
                logger.info("Đã cập nhật thông tin API từ biến môi trường")
                
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật file cấu hình từ biến môi trường: {str(e)}")
    
    def _start_bot_process(self, bot_module):
        """Khởi động tiến trình bot"""
        # Khởi động bot từ module đã import
        try:
            # Kiểm tra nếu module có hàm start
            if hasattr(bot_module, "start"):
                logger.info("Khởi động bot với hàm start()...")
                
                # Chuẩn bị tham số
                kwargs = {
                    "test_mode": self.test_mode
                }
                
                if self.risk_level:
                    kwargs["risk_level"] = self.risk_level
                
                if self.enable_telegram:
                    kwargs["enable_telegram"] = True
                
                if self.symbols:
                    kwargs["symbols"] = self.symbols
                
                if self.config_file:
                    kwargs["config_file"] = self.config_file
                
                # Khởi động trong thread riêng
                bot_thread = threading.Thread(
                    target=bot_module.start,
                    kwargs=kwargs
                )
                bot_thread.daemon = True
                bot_thread.start()
                
            # Nếu có lớp Bot, khởi tạo và khởi động
            elif hasattr(bot_module, "Bot"):
                logger.info("Khởi động bot bằng lớp Bot...")
                
                # Chuẩn bị tham số
                kwargs = {
                    "test_mode": self.test_mode
                }
                
                if self.risk_level:
                    kwargs["risk_level"] = self.risk_level
                
                if self.enable_telegram:
                    kwargs["enable_telegram"] = True
                
                if self.symbols:
                    kwargs["symbols"] = self.symbols
                
                if self.config_file:
                    kwargs["config_file"] = self.config_file
                
                # Khởi tạo đối tượng Bot
                bot = bot_module.Bot(**kwargs)
                
                # Khởi động trong thread riêng
                bot_thread = threading.Thread(
                    target=bot.start
                )
                bot_thread.daemon = True
                bot_thread.start()
                
            # Nếu có hàm main
            elif hasattr(bot_module, "main"):
                logger.info("Khởi động bot với hàm main()...")
                
                # Chuẩn bị tham số
                args = []
                
                if self.risk_level:
                    args.append(f"--risk-level={self.risk_level}")
                
                if self.test_mode:
                    args.append("--test-mode")
                
                if self.enable_telegram:
                    args.append("--enable-telegram")
                
                if self.symbols:
                    args.append(f"--symbols={','.join(self.symbols)}")
                
                if self.config_file:
                    args.append(f"--config={self.config_file}")
                
                # Khởi động trong thread riêng
                bot_thread = threading.Thread(
                    target=bot_module.main
                    # args=(args,)  # Bỏ dòng này để sửa lỗi
                )
                bot_thread.daemon = True
                bot_thread.start()
                
            # Nếu không tìm thấy các cách khởi động trên
            else:
                logger.error("Không tìm thấy hàm start(), lớp Bot, hoặc hàm main() trong module bot")
                raise Exception("Không thể khởi động bot, thiếu các phương thức khởi động")
            
            logger.info("Bot đã được khởi động")
            self.is_running = True
            self._update_status("running")
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động bot: {str(e)}")
            logger.error(traceback.format_exc())
            self.error_count += 1
            self._update_status("error", error=str(e))
            raise
    
    def _monitor_loop(self):
        """Vòng lặp giám sát bot"""
        logger.info("Bắt đầu giám sát bot...")
        
        check_interval = 30  # 30 giây
        last_check_time = time.time()
        
        try:
            while self.is_running and running:
                # Kiểm tra trạng thái bot
                current_time = time.time()
                if current_time - last_check_time >= check_interval:
                    # Cập nhật thời gian kiểm tra
                    last_check_time = current_time
                    
                    # Kiểm tra bot có đang chạy không
                    if not self._check_bot_status():
                        logger.warning("Bot không phản hồi hoặc đã dừng")
                        self.error_count += 1
                        self._update_status("error", error="Bot không phản hồi")
                        
                        # Thử khởi động lại
                        if self.auto_recovery:
                            logger.info("Đang khởi động lại bot...")
                            self.restart()
                    else:
                        # Cập nhật trạng thái
                        self._update_status("running")
                
                # Ngủ
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Lỗi trong vòng lặp giám sát: {str(e)}")
            logger.error(traceback.format_exc())
            self.error_count += 1
            self._update_status("error", error=str(e))
    
    def _check_bot_status(self):
        """Kiểm tra trạng thái của bot"""
        # Kiểm tra file heartbeat nếu có
        heartbeat_file = "bot_heartbeat.json"
        if os.path.exists(heartbeat_file):
            try:
                with open(heartbeat_file, "r") as f:
                    heartbeat = json.load(f)
                
                # Kiểm tra thời gian cập nhật
                last_update = datetime.datetime.strptime(heartbeat["last_update"], "%Y-%m-%d %H:%M:%S")
                now = datetime.datetime.now()
                
                # Nếu cập nhật trong 2 phút
                if (now - last_update).total_seconds() < 120:
                    return True
                else:
                    logger.warning(f"Bot heartbeat đã cũ: {(now - last_update).total_seconds():.1f} giây")
                    return False
                
            except Exception as e:
                logger.error(f"Lỗi khi đọc file heartbeat: {str(e)}")
        
        # Nếu không có file heartbeat, kiểm tra các dấu hiệu khác
        # TODO: Bổ sung thêm các phương pháp kiểm tra khác
        
        # Trong chế độ test, coi như bot đang chạy
        if self.test_mode:
            return True
        
        # Mặc định trả về True nếu không có phương pháp kiểm tra nào
        return True
    
    def restart(self):
        """Khởi động lại bot"""
        logger.info("Khởi động lại bot...")
        
        # Dừng bot hiện tại
        self.stop(restart=True)
        
        # Tăng số lần khởi động lại
        self.restart_count += 1
        
        # Cập nhật trạng thái
        self._update_status("restarting")
        
        # Chờ một chút
        time.sleep(2)
        
        # Khởi động lại
        return self.start()
    
    def stop(self, restart=False):
        """Dừng bot"""
        if not restart:
            logger.info("Dừng bot...")
        
        # Đánh dấu dừng
        self.is_running = False
        
        # Tạo file stop signal
        with open("bot_stop_signal", "w") as f:
            f.write("stop")
        
        # Cập nhật trạng thái
        if not restart:
            self._update_status("stopped")
        
        # Chờ bot dừng
        time.sleep(3)
        
        # Xóa file stop signal
        if os.path.exists("bot_stop_signal"):
            os.remove("bot_stop_signal")

def main():
    """Hàm main"""
    # Phân tích tham số dòng lệnh
    parser = argparse.ArgumentParser(description="Khởi động bot giao dịch")
    parser.add_argument("--risk-level", type=str, help="Mức độ rủi ro (10, 15, 20, 30)")
    parser.add_argument("--test-mode", action="store_true", help="Chạy ở chế độ test")
    parser.add_argument("--enable-telegram", action="store_true", help="Kích hoạt thông báo Telegram")
    parser.add_argument("--symbols", type=str, help="Danh sách cặp tiền (phân cách bằng dấu phẩy)")
    parser.add_argument("--config", type=str, help="File cấu hình")
    parser.add_argument("--no-recovery", action="store_true", help="Không tự động khôi phục")
    
    # Parse args
    args = parser.parse_args()
    
    # Khởi tạo biến trạng thái toàn cục
    global running
    running = True
    
    # Xử lý tham số symbols
    symbols = None
    if args.symbols:
        symbols = args.symbols.split(",")
    
    # Khởi tạo Bot Manager
    manager = BotManager(
        risk_level=args.risk_level,
        test_mode=args.test_mode,
        enable_telegram=args.enable_telegram,
        symbols=symbols,
        config_file=args.config,
        auto_recovery=not args.no_recovery
    )
    
    # Lưu vào biến toàn cục
    global bot_process
    bot_process = manager
    
    # Khởi động bot
    try:
        success = manager.start()
        if not success:
            sys.exit(1)
        
        # Chờ tín hiệu dừng
        while running:
            time.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("Đã nhận tín hiệu dừng từ bàn phím")
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        # Dừng bot
        manager.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())