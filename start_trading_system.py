#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Start Trading System
------------------
Script khởi động và điều khiển hệ thống giao dịch, cung cấp giao diện CLI để quản lý các dịch vụ.
"""

import os
import sys
import time
import json
import argparse
import logging
from datetime import datetime
import subprocess

from telegram_notifier import TelegramNotifier
from service_guardian import ServiceGuardian

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_system.log')
    ]
)

logger = logging.getLogger("trading_system")

def create_default_configs():
    """
    Tạo các file cấu hình mặc định nếu chưa tồn tại
    """
    # Tạo thư mục configs nếu chưa tồn tại
    os.makedirs("configs", exist_ok=True)
    
    # Tạo cấu hình market_analysis_config.json nếu chưa tồn tại
    market_analysis_config_path = "configs/market_analysis_config.json"
    if not os.path.exists(market_analysis_config_path):
        market_analysis_config = {
            "testnet": True,
            "primary_timeframe": "1h",
            "timeframes": ["5m", "15m", "1h", "4h", "1d"],
            "symbols_to_analyze": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"],
            "analysis_interval": 1800,
            "notification_settings": {
                "send_market_summary": True,
                "send_trading_signals": True,
                "signal_confidence_threshold": 70,
                "notification_interval": 7200,
                "quiet_hours": [0, 5]
            },
            "indicators": {
                "sma": [20, 50, 100, 200],
                "ema": [9, 21, 55, 100],
                "rsi": 14,
                "macd": {"fast": 12, "slow": 26, "signal": 9},
                "bollinger": {"window": 20, "std": 2},
                "atr": 14,
                "stoch": {"k": 14, "d": 3, "smooth": 3},
                "volume_sma": 20
            },
            "market_regime": {
                "volatility_threshold": 2.5,
                "trend_strength_threshold": 3.0,
                "volume_surge_threshold": 2.0
            },
            "data_window": 200,
            "system_settings": {
                "debug_mode": True,
                "cache_data": True,
                "cache_expiry": 300,
                "log_level": "INFO",
                "save_analysis_files": True
            }
        }
        
        with open(market_analysis_config_path, 'w') as f:
            json.dump(market_analysis_config, f, indent=4)
        
        logger.info(f"Đã tạo file cấu hình mặc định: {market_analysis_config_path}")
    
    # Tạo cấu hình service_config.json nếu chưa tồn tại
    service_config_path = "configs/service_config.json"
    if not os.path.exists(service_config_path):
        service_config = {
            "services": {
                "market_analyzer": {
                    "enabled": True,
                    "command": "python activate_market_analyzer.py --once",
                    "description": "Hệ thống phân tích thị trường và tín hiệu giao dịch",
                    "autostart": True,
                    "auto_restart": True,
                    "check_interval": 60,
                    "restart_delay": 10,
                    "max_restart_attempts": 5,
                    "health_check": {
                        "type": "file",
                        "path": "market_analyzer.log",
                        "max_age": 600
                    },
                    "dependencies": []
                },
                "auto_sltp_manager": {
                    "enabled": False,  # Tắt mặc định do chưa cần thiết
                    "command": "python auto_sltp_manager.py",
                    "description": "Quản lý tự động Stop Loss và Take Profit",
                    "autostart": False,
                    "auto_restart": True,
                    "check_interval": 60,
                    "restart_delay": 10,
                    "max_restart_attempts": 5,
                    "health_check": {
                        "type": "file",
                        "path": "auto_sltp_manager.log",
                        "max_age": 600
                    },
                    "dependencies": []
                }
            },
            "system": {
                "check_interval": 30,
                "status_report_interval": 3600,
                "enable_notifications": True,
                "log_level": "INFO"
            }
        }
        
        with open(service_config_path, 'w') as f:
            json.dump(service_config, f, indent=4)
        
        logger.info(f"Đã tạo file cấu hình mặc định: {service_config_path}")

def init_system():
    """
    Khởi tạo hệ thống
    """
    logger.info("Đang khởi tạo hệ thống giao dịch...")
    
    # Tạo các file cấu hình mặc định
    create_default_configs()
    
    # Gửi thông báo khởi động
    notifier = TelegramNotifier()
    
    try:
        message = "<b>🚀 KHỞI ĐỘNG HỆ THỐNG GIAO DỊCH</b>\n\n"
        message += "<b>Thông tin hệ thống:</b>\n"
        message += f"- Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
        message += f"- Môi trường: Testnet\n"
        message += f"- Phiên bản: 1.0.0\n\n"
        message += "Hệ thống đang được khởi tạo. Một báo cáo trạng thái sẽ được gửi sau khi khởi động hoàn tất."
        
        success = notifier.send_message(message)
        if success:
            logger.info("Đã gửi thông báo khởi động hệ thống")
        else:
            logger.warning("Không thể gửi thông báo khởi động hệ thống")
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo khởi động: {e}")
    
    logger.info("Hệ thống đã được khởi tạo")

def start_market_analyzer():
    """
    Khởi động hệ thống phân tích thị trường
    """
    logger.info("Đang khởi động hệ thống phân tích thị trường...")
    
    try:
        # Khởi động trực tiếp một lần
        result = subprocess.run(
            ["python", "activate_market_analyzer.py", "--once"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False
        )
        
        if result.returncode == 0:
            logger.info("Đã khởi động hệ thống phân tích thị trường")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            return True
        else:
            logger.error(f"Lỗi khi khởi động hệ thống phân tích thị trường: mã thoát {result.returncode}")
            print(f"Lỗi: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi động hệ thống phân tích thị trường: {e}")
        return False

def start_service_guardian():
    """
    Khởi động Service Guardian để quản lý các dịch vụ
    """
    logger.info("Đang khởi động Service Guardian...")
    
    try:
        guardian = ServiceGuardian()
        guardian.start()
        return True
    except KeyboardInterrupt:
        logger.info("Đã nhận lệnh dừng từ người dùng")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi động Service Guardian: {e}")
        return False

def main():
    """
    Hàm chính
    """
    parser = argparse.ArgumentParser(description="Khởi động và quản lý hệ thống giao dịch")
    
    # Thiết lập các tùy chọn
    parser.add_argument('--init', action='store_true', help='Khởi tạo hệ thống (tạo cấu hình mặc định)')
    parser.add_argument('--market-analysis', action='store_true', help='Chạy phân tích thị trường một lần')
    parser.add_argument('--service-guardian', action='store_true', help='Khởi động Service Guardian để quản lý các dịch vụ')
    parser.add_argument('--all', action='store_true', help='Khởi động tất cả các dịch vụ')
    
    args = parser.parse_args()
    
    # Nếu không có tùy chọn nào được chỉ định, hiển thị trợ giúp
    if not (args.init or args.market_analysis or args.service_guardian or args.all):
        parser.print_help()
        return
    
    # Khởi tạo hệ thống nếu được yêu cầu
    if args.init or args.all:
        init_system()
    
    # Chạy phân tích thị trường một lần nếu được yêu cầu
    if args.market_analysis or args.all:
        start_market_analyzer()
    
    # Khởi động Service Guardian nếu được yêu cầu
    if args.service_guardian or args.all:
        start_service_guardian()

if __name__ == "__main__":
    main()