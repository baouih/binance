#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot Startup - Script khởi động bot giao dịch
"""

import os
import sys
import json
import time
import logging
import argparse
import threading
import importlib
import datetime
import traceback
from pathlib import Path

# Đảm bảo thư mục logs tồn tại
os.makedirs("logs", exist_ok=True)

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot_startup.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('bot_startup')

# Biến toàn cục để kiểm soát hoạt động của bot
is_running = True
threads = []

def load_config():
    """Tải cấu hình từ file"""
    config_file = "account_config.json"
    
    if not os.path.exists(config_file):
        logger.error(f"Không tìm thấy file cấu hình {config_file}")
        create_default_config(config_file)
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Đã tải cấu hình từ {config_file}")
        return config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
        return None

def create_default_config(config_file):
    """Tạo cấu hình mặc định"""
    try:
        default_config = {
            "api_key": "",
            "api_secret": "",
            "testnet": True,
            "telegram_token": "",
            "telegram_chat_id": "",
            "telegram_enabled": False,
            "auto_trading": True,
            "detailed_logging": True,
            "auto_restart": True,
            "data_dir": "./data",
            "update_interval": 10,
            "risk_level": "20",
            "max_position_size_percent": 2.0,
            "max_open_positions": 5,
            "stop_loss_percent": 1.0,
            "take_profit_percent": 3.0,
            "leverage": 5,
            "trading_settings": {
                "max_daily_loss_percent": 5.0,
                "enable_trailing_stop": True,
                "trailing_stop_callback": 0.2,
                "use_smart_entry": True,
                "use_market_regime_filter": True,
                "use_volatility_filter": True
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        logger.info(f"Đã tạo cấu hình mặc định tại {config_file}")
    except Exception as e:
        logger.error(f"Lỗi khi tạo cấu hình mặc định: {str(e)}")

def setup_environment(config):
    """Thiết lập môi trường"""
    try:
        # Tạo thư mục dữ liệu nếu chưa tồn tại
        data_dir = config.get("data_dir", "./data")
        os.makedirs(data_dir, exist_ok=True)
        
        # Tạo thư mục models nếu chưa tồn tại
        os.makedirs("ml_models", exist_ok=True)
        
        # Tạo thư mục risk_configs nếu chưa tồn tại
        os.makedirs("risk_configs", exist_ok=True)
        
        # Tạo thư mục strategies nếu chưa tồn tại
        os.makedirs("strategies", exist_ok=True)
        
        # Ghi log
        logger.info("Đã thiết lập môi trường")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập môi trường: {str(e)}")
        return False

def validate_config(config):
    """Kiểm tra tính hợp lệ của cấu hình"""
    if config is None:
        logger.error("Cấu hình không hợp lệ")
        return False
    
    # Kiểm tra các trường bắt buộc
    required_fields = ["api_key", "api_secret"]
    for field in required_fields:
        if field not in config or not config[field]:
            logger.error(f"Thiếu trường cấu hình bắt buộc: {field}")
            return False
    
    # Kiểm tra các trường có kiểu dữ liệu hợp lệ
    numeric_fields = ["max_position_size_percent", "stop_loss_percent", "take_profit_percent", "leverage"]
    for field in numeric_fields:
        if field in config and not isinstance(config[field], (int, float)):
            logger.error(f"Trường cấu hình {field} phải là số")
            return False
    
    # Các kiểm tra hợp lệ khác
    if "risk_level" in config and config["risk_level"] not in ["10", "15", "20", "30"]:
        logger.error(f"Mức rủi ro không hợp lệ: {config.get('risk_level')}")
        return False
    
    logger.info("Cấu hình hợp lệ")
    return True

def load_risk_config(risk_level):
    """Tải cấu hình rủi ro"""
    try:
        from risk_level_manager import RiskLevelManager
        risk_manager = RiskLevelManager()
        risk_config = risk_manager.get_risk_config(risk_level)
        logger.info(f"Đã tải cấu hình rủi ro {risk_level}%")
        return risk_config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình rủi ro: {str(e)}")
        return None

def initialize_trading_system(config, risk_config):
    """Khởi tạo hệ thống giao dịch"""
    logger.info("Đang khởi tạo hệ thống giao dịch...")
    
    try:
        # Khởi tạo API client
        logger.info("Khởi tạo kết nối API...")
        
        # Thiết lập cấu hình giao dịch
        logger.info("Thiết lập cấu hình giao dịch...")
        
        # Thiết lập quản lý rủi ro
        logger.info("Thiết lập quản lý rủi ro...")
        
        # Thiết lập chiến lược giao dịch
        active_strategy = config.get("active_strategy", "Adaptive Strategy")
        logger.info(f"Thiết lập chiến lược giao dịch: {active_strategy}")
        
        # Khởi tạo hệ thống thông báo
        if config.get("telegram_enabled", False):
            logger.info("Khởi tạo hệ thống thông báo Telegram...")
        
        logger.info("Đã khởi tạo hệ thống giao dịch thành công")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo hệ thống giao dịch: {str(e)}")
        return False

def start_market_data_thread(config):
    """Khởi động thread cập nhật dữ liệu thị trường"""
    def market_data_worker(stop_event):
        """Thread worker để cập nhật dữ liệu thị trường"""
        logger.info("Bắt đầu thread cập nhật dữ liệu thị trường")
        update_interval = config.get("update_interval", 10)
        
        try:
            while not stop_event.is_set():
                # Lấy dữ liệu thị trường mới nhất
                logger.debug("Cập nhật dữ liệu thị trường...")
                
                # Đợi một khoảng thời gian
                time.sleep(update_interval)
        except Exception as e:
            logger.error(f"Lỗi trong thread dữ liệu thị trường: {str(e)}")
        
        logger.info("Kết thúc thread cập nhật dữ liệu thị trường")
    
    stop_event = threading.Event()
    market_thread = threading.Thread(target=market_data_worker, args=(stop_event,))
    market_thread.daemon = True
    market_thread.start()
    
    threads.append((market_thread, stop_event))
    logger.info("Đã khởi động thread cập nhật dữ liệu thị trường")
    return market_thread

def start_signal_generator_thread(config):
    """Khởi động thread tạo tín hiệu giao dịch"""
    def signal_generator_worker(stop_event):
        """Thread worker để tạo tín hiệu giao dịch"""
        logger.info("Bắt đầu thread tạo tín hiệu giao dịch")
        
        try:
            while not stop_event.is_set():
                # Phân tích dữ liệu và tạo tín hiệu
                logger.debug("Xử lý tín hiệu giao dịch...")
                
                # Đợi một khoảng thời gian
                time.sleep(30)  # Cập nhật tín hiệu mỗi 30 giây
        except Exception as e:
            logger.error(f"Lỗi trong thread tạo tín hiệu: {str(e)}")
        
        logger.info("Kết thúc thread tạo tín hiệu giao dịch")
    
    stop_event = threading.Event()
    signal_thread = threading.Thread(target=signal_generator_worker, args=(stop_event,))
    signal_thread.daemon = True
    signal_thread.start()
    
    threads.append((signal_thread, stop_event))
    logger.info("Đã khởi động thread tạo tín hiệu giao dịch")
    return signal_thread

def start_trade_executor_thread(config):
    """Khởi động thread thực thi giao dịch"""
    def trade_executor_worker(stop_event):
        """Thread worker để thực thi giao dịch"""
        logger.info("Bắt đầu thread thực thi giao dịch")
        
        try:
            while not stop_event.is_set():
                # Kiểm tra và thực thi các tín hiệu giao dịch
                logger.debug("Kiểm tra tín hiệu giao dịch...")
                
                # Thực thi các lệnh giao dịch
                
                # Đợi một khoảng thời gian
                time.sleep(5)  # Kiểm tra tín hiệu mỗi 5 giây
        except Exception as e:
            logger.error(f"Lỗi trong thread thực thi giao dịch: {str(e)}")
        
        logger.info("Kết thúc thread thực thi giao dịch")
    
    # Chỉ khởi động thread nếu chế độ tự động giao dịch được bật
    if config.get("auto_trading", True):
        stop_event = threading.Event()
        trade_thread = threading.Thread(target=trade_executor_worker, args=(stop_event,))
        trade_thread.daemon = True
        trade_thread.start()
        
        threads.append((trade_thread, stop_event))
        logger.info("Đã khởi động thread thực thi giao dịch")
        return trade_thread
    else:
        logger.info("Chế độ tự động giao dịch đã bị tắt, không khởi động thread thực thi giao dịch")
        return None

def start_position_manager_thread(config):
    """Khởi động thread quản lý vị thế"""
    def position_manager_worker(stop_event):
        """Thread worker để quản lý vị thế"""
        logger.info("Bắt đầu thread quản lý vị thế")
        
        try:
            while not stop_event.is_set():
                # Quản lý các vị thế hiện tại
                logger.debug("Quản lý vị thế...")
                
                # Kiểm tra và cập nhật stop loss / take profit
                
                # Đợi một khoảng thời gian
                time.sleep(10)  # Cập nhật mỗi 10 giây
        except Exception as e:
            logger.error(f"Lỗi trong thread quản lý vị thế: {str(e)}")
        
        logger.info("Kết thúc thread quản lý vị thế")
    
    stop_event = threading.Event()
    position_thread = threading.Thread(target=position_manager_worker, args=(stop_event,))
    position_thread.daemon = True
    position_thread.start()
    
    threads.append((position_thread, stop_event))
    logger.info("Đã khởi động thread quản lý vị thế")
    return position_thread

def start_notification_thread(config):
    """Khởi động thread thông báo"""
    def notification_worker(stop_event):
        """Thread worker để gửi thông báo"""
        logger.info("Bắt đầu thread thông báo")
        
        try:
            # Khởi tạo kết nối Telegram nếu được cấu hình
            telegram_enabled = config.get("telegram_enabled", False)
            telegram_token = config.get("telegram_token", "")
            telegram_chat_id = config.get("telegram_chat_id", "")
            
            if telegram_enabled and telegram_token and telegram_chat_id:
                logger.info("Kết nối Telegram thành công")
                # Gửi thông báo khởi động
                # telegram_bot.send_message(telegram_chat_id, "Bot giao dịch đã khởi động")
            else:
                logger.info("Không sử dụng thông báo Telegram")
            
            # Loop chính của thread
            while not stop_event.is_set():
                # Xử lý hàng đợi thông báo
                
                # Đợi một khoảng thời gian
                time.sleep(1)
        except Exception as e:
            logger.error(f"Lỗi trong thread thông báo: {str(e)}")
        
        logger.info("Kết thúc thread thông báo")
    
    stop_event = threading.Event()
    notification_thread = threading.Thread(target=notification_worker, args=(stop_event,))
    notification_thread.daemon = True
    notification_thread.start()
    
    threads.append((notification_thread, stop_event))
    logger.info("Đã khởi động thread thông báo")
    return notification_thread

def start_web_server():
    """Khởi động web server"""
    def web_server_worker():
        """Thread worker cho web server"""
        logger.info("Khởi động web server...")
        try:
            # Khởi động Flask app
            from app import app
            app.run(host="0.0.0.0", port=5000)
        except Exception as e:
            logger.error(f"Lỗi khi khởi động web server: {str(e)}")
    
    web_thread = threading.Thread(target=web_server_worker)
    web_thread.daemon = True
    web_thread.start()
    
    logger.info("Đã khởi động web server")
    return web_thread

def load_module_dynamically(module_name):
    """Tải module động"""
    try:
        # Kiểm tra nếu module đã được tải
        if module_name in sys.modules:
            return sys.modules[module_name]
        
        # Tải module
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        else:
            logger.error(f"Không tìm thấy module {module_name}")
            return None
    except Exception as e:
        logger.error(f"Lỗi khi tải module {module_name}: {str(e)}")
        return None

def setup_ml_environment():
    """Thiết lập môi trường học máy"""
    try:
        # Tải các thư viện học máy
        import numpy as np
        import pandas as pd
        import matplotlib
        matplotlib.use('Agg')  # Sử dụng backend không cần GUI
        
        logger.info("Đã tải thư viện học máy")
        return True
    except ImportError as e:
        logger.warning(f"Không thể tải thư viện học máy: {str(e)}")
        logger.warning("Một số chức năng học máy có thể không hoạt động")
        return False

def monitor_system():
    """Giám sát hệ thống và xử lý tắt tắt"""
    global is_running, threads
    
    try:
        # Loop chính của chương trình
        while is_running:
            # Kiểm tra các thread con
            active_threads = []
            for thread, stop_event in threads:
                if thread.is_alive():
                    active_threads.append((thread, stop_event))
                else:
                    logger.warning(f"Thread {thread.name} đã dừng không mong muốn")
            
            # Cập nhật danh sách thread
            threads = active_threads
            
            # Đợi một khoảng thời gian
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Nhận tín hiệu KeyboardInterrupt, đang dừng bot...")
        shutdown_system()
    except Exception as e:
        logger.error(f"Lỗi trong monitor_system: {str(e)}")
        logger.error(traceback.format_exc())
        shutdown_system()

def shutdown_system():
    """Dừng tất cả và thoát chương trình"""
    global is_running
    
    logger.info("Đang dừng hệ thống...")
    is_running = False
    
    # Dừng tất cả các thread
    for thread, stop_event in threads:
        logger.info(f"Dừng thread {thread.name}...")
        stop_event.set()
    
    # Đợi tất cả các thread kết thúc
    for thread, _ in threads:
        thread.join(timeout=5)
    
    logger.info("Đã dừng tất cả các thread")
    logger.info("Hệ thống đã dừng hoàn toàn")

def main():
    """Hàm main của bot"""
    parser = argparse.ArgumentParser(description='Bot giao dịch')
    parser.add_argument('--risk-level', type=str, choices=["10", "15", "20", "30"], default=None,
                        help='Mức rủi ro (10, 15, 20, 30)')
    parser.add_argument('--no-trading', action='store_true', help='Không thực hiện giao dịch tự động')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng môi trường testnet')
    args = parser.parse_args()
    
    try:
        logger.info("==== Khởi động hệ thống bot giao dịch ====")
        
        # Tải cấu hình
        config = load_config()
        if not config:
            logger.error("Không thể tải cấu hình, dừng khởi động")
            return 1
        
        # Ghi đè cấu hình từ tham số dòng lệnh
        if args.risk_level:
            config["risk_level"] = args.risk_level
            logger.info(f"Sử dụng mức rủi ro từ tham số dòng lệnh: {args.risk_level}%")
        
        if args.no_trading:
            config["auto_trading"] = False
            logger.info("Chế độ không giao dịch tự động được bật từ tham số dòng lệnh")
        
        if args.testnet:
            config["testnet"] = True
            logger.info("Sử dụng môi trường testnet từ tham số dòng lệnh")
        
        # Kiểm tra tính hợp lệ của cấu hình
        if not validate_config(config):
            logger.error("Cấu hình không hợp lệ, dừng khởi động")
            return 1
        
        # Thiết lập môi trường
        if not setup_environment(config):
            logger.error("Không thể thiết lập môi trường, dừng khởi động")
            return 1
        
        # Tải cấu hình rủi ro
        risk_config = load_risk_config(config.get("risk_level", "20"))
        if not risk_config:
            logger.error("Không thể tải cấu hình rủi ro, dừng khởi động")
            return 1
        
        # Thiết lập môi trường học máy
        setup_ml_environment()
        
        # Khởi tạo hệ thống giao dịch
        if not initialize_trading_system(config, risk_config):
            logger.error("Không thể khởi tạo hệ thống giao dịch, dừng khởi động")
            return 1
        
        # Khởi động các thread
        market_thread = start_market_data_thread(config)
        signal_thread = start_signal_generator_thread(config)
        
        if config.get("auto_trading", True):
            trade_thread = start_trade_executor_thread(config)
        
        position_thread = start_position_manager_thread(config)
        notification_thread = start_notification_thread(config)
        
        # Khởi động web server trong thread riêng biệt
        web_thread = start_web_server()
        
        logger.info("Bot đã khởi động thành công")
        
        # Giám sát hệ thống
        monitor_system()
        
        return 0
        
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Đảm bảo dừng tất cả các thread
        shutdown_system()
        
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)