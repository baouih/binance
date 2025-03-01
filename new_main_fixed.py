#!/usr/bin/env python3
"""
Main entry point for the Crypto Trading Bot CLI - Command Line Version
"""

import os
import sys
import json
import logging
import argparse
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
        display_positions, get_recent_trades, display_performance_metrics
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
    
    warnings = []
    if not api_key or not api_secret:
        logger.warning("BINANCE_API_KEY hoặc BINANCE_API_SECRET không được cấu hình")
        warnings.append("CẢNH BÁO: API keys Binance chưa được cấu hình!")
        
    # Kiểm tra tập tin cấu hình
    if not os.path.exists('multi_coin_config.json'):
        logger.warning("File cấu hình multi_coin_config.json không tồn tại")
        warnings.append("CẢNH BÁO: File cấu hình multi_coin_config.json không tồn tại!")
    
    return warnings

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

def parse_command_line_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='BinanceTrader Bot CLI')
    
    # Thêm các tùy chọn dòng lệnh
    parser.add_argument('--status', '-s', action='store_true', help='Hiển thị trạng thái bot')
    parser.add_argument('--positions', '-p', action='store_true', help='Hiển thị vị thế hiện tại')
    parser.add_argument('--trades', '-t', action='store_true', help='Hiển thị giao dịch gần đây')
    parser.add_argument('--logs', '-l', type=int, metavar='N', nargs='?', const=20, help='Hiển thị N dòng log gần đây')
    parser.add_argument('--start', action='store_true', help='Khởi động bot')
    parser.add_argument('--stop', action='store_true', help='Dừng bot')
    parser.add_argument('--restart', action='store_true', help='Khởi động lại bot')
    parser.add_argument('--monitor', '-m', type=int, metavar='INTERVAL', nargs='?', const=5, help='Giám sát bot theo thời gian thực')
    
    return parser.parse_args()

def print_welcome_message():
    """In thông báo chào mừng"""
    print("\n" + "=" * 60)
    print("BINANCE FUTURES TRADING BOT - CLI MODE".center(60))
    print("=" * 60)
    print("\nPhiên bản: 1.0.0 (CLI Only)")
    print("Mode: Production\n")

def handle_command_line_args(args):
    """Xử lý tham số dòng lệnh"""
    if args.status:
        status = get_bot_status()
        print(format_status(status))
    
    if args.positions:
        positions = get_open_positions()
        display_positions(positions)
    
    if args.trades:
        trades = get_recent_trades()
        display_positions(trades, "Giao dịch gần đây")
    
    if args.logs is not None:
        view_logs(args.logs)
    
    if args.start:
        start_bot()
    
    if args.stop:
        stop_bot()
    
    if args.restart:
        restart_bot()
    
    if args.monitor is not None:
        display_real_time_monitor(args.monitor)

def main():
    """Hàm chính"""
    print_welcome_message()
    
    # Kiểm tra môi trường
    warnings = check_environment()
    for warning in warnings:
        print(warning)
    
    # Kiểm tra trạng thái bot
    status = check_bot_status()
    print(format_status(status))
    print()
    
    # Phân tích tham số dòng lệnh
    args = parse_command_line_arguments()
    
    # Nếu có tham số dòng lệnh, xử lý chúng
    if len(sys.argv) > 1:
        handle_command_line_args(args)
    else:
        # Nếu không có tham số, khởi chạy menu tương tác
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