#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot CLI
"""

import os
import sys
import logging
import time
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('main')

# Import các module cần thiết
try:
    from cli_controller import (
        interactive_menu, get_bot_status, format_status,
        start_bot, stop_bot, restart_bot, view_logs,
        display_real_time_monitor, get_open_positions, 
        display_positions, get_recent_trades, display_performance_metrics
    )
    logger.info("CLI Controller đã được import thành công")
except ImportError as e:
    logger.error(f"Lỗi khi import CLI Controller: {e}")
    sys.exit(1)

def check_env():
    """Kiểm tra biến môi trường và tập tin cấu hình"""
    try:
        # Kiểm tra API keys
        api_key = os.environ.get('BINANCE_API_KEY')
        api_secret = os.environ.get('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            logger.warning("BINANCE_API_KEY hoặc BINANCE_API_SECRET không được cấu hình")
            print("CẢNH BÁO: API keys Binance chưa được cấu hình!")
            
        # Kiểm tra tập tin cấu hình
        if not os.path.exists('multi_coin_config.json'):
            logger.warning("File cấu hình multi_coin_config.json không tồn tại")
            print("CẢNH BÁO: File cấu hình multi_coin_config.json không tồn tại!")
            
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra môi trường: {e}")
        return False

def check_bot_running():
    """Kiểm tra xem bot có đang chạy không và cập nhật trạng thái nếu cần"""
    try:
        status = get_bot_status()
        if status["status"] == "running":
            logger.info("Bot đang chạy với PID: " + status.get("pid", "N/A"))
        else:
            logger.info("Bot không chạy")
            
        return status["status"] == "running"
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái bot: {e}")
        return False

def main():
    """Hàm chính của ứng dụng"""
    print("\n===== BinanceTrader Bot CLI =====\n")
    
    # Kiểm tra môi trường
    if not check_env():
        print("Có lỗi khi kiểm tra môi trường. Xem logs để biết thêm chi tiết.")
    
    # Kiểm tra xem bot có đang chạy hay không
    is_running = check_bot_running()
    
    # Hiển thị trạng thái hiện tại
    status = get_bot_status()
    print(format_status(status))
    print()
    
    # Khởi chạy menu tương tác
    try:
        interactive_menu()
    except KeyboardInterrupt:
        print("\nĐã thoát chương trình.")
    except Exception as e:
        logger.error(f"Lỗi không xác định: {e}")
        print(f"Đã xảy ra lỗi: {e}")
        print("Xem logs để biết thêm chi tiết.")

if __name__ == "__main__":
    main()