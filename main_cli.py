#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot CLI - Simplified CLI version

This version replaces the previous web-based interface with a CLI-only
implementation for improved stability and reduced resource consumption.
"""

import os
import sys
import json
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

# Import CLI controller
try:
    from cli_controller import (
        interactive_menu, get_bot_status, format_status,
        start_bot, stop_bot, restart_bot, view_logs,
        display_real_time_monitor, get_open_positions, 
        display_positions, get_recent_trades, display_performance_metrics,
        main as cli_main
    )
    logger.info("CLI Controller đã được import thành công")
except ImportError as e:
    logger.error(f"Lỗi khi import CLI Controller: {e}")
    print(f"Lỗi: Không thể import CLI Controller - {e}")
    sys.exit(1)

def check_environment():
    """Kiểm tra môi trường và cấu hình"""
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

def check_bot_status():
    """Kiểm tra trạng thái bot"""
    try:
        status = get_bot_status()
        if status["status"] == "running":
            logger.info(f"Bot đang chạy với PID: {status.get('pid', 'N/A')}")
        else:
            logger.info("Bot không chạy")
            
        return status
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái bot: {e}")
        return {"status": "unknown", "error": str(e)}

def load_trading_state():
    """Tải trạng thái giao dịch từ file"""
    try:
        if os.path.exists("trading_state.json"):
            with open("trading_state.json", "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi đọc trạng thái giao dịch: {e}")
    return None

def print_welcome_message():
    """In thông báo chào mừng"""
    print("\n" + "=" * 60)
    print("BINANCE FUTURES TRADING BOT - CLI MODE".center(60))
    print("=" * 60)
    print("\nPhiên bản: 1.0.0 (CLI Only)")
    print("Mode: Production\n")

def main():
    """Hàm chính"""
    print_welcome_message()
    
    # Kiểm tra môi trường
    check_environment()
    
    # Kiểm tra trạng thái bot
    status = check_bot_status()
    print(format_status(status))
    print()
    
    # Nếu có tham số dòng lệnh, chuyển cho CLI controller xử lý
    if len(sys.argv) > 1:
        cli_main()
    else:
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