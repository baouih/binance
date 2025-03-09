#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script khởi động hệ thống phân tích thị trường nâng cao

Script này khởi động các module nâng cao để phân tích tất cả các cặp tiền 
và gửi thông báo Telegram theo định kỳ với đầy đủ thông tin.
"""

import os
import sys
import time
import json
import argparse
import logging
import threading
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_market_analyzer.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("enhanced_market_analyzer")

# Import các module cần thiết
try:
    from enhanced_market_updater import EnhancedMarketUpdater
    from enhanced_binance_api import EnhancedBinanceAPI
    from enhanced_telegram_notifications import EnhancedTelegramNotifications
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đã tạo và cài đặt đúng các module cần thiết")
    sys.exit(1)

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Khởi động hệ thống phân tích thị trường nâng cao')
    
    parser.add_argument('--update-interval', type=int, default=10,
                        help='Khoảng thời gian cập nhật thị trường (phút)')
    
    parser.add_argument('--notification-interval', type=int, default=15,
                        help='Khoảng thời gian gửi thông báo (phút)')
    
    parser.add_argument('--testnet', action='store_true', default=True,
                        help='Sử dụng Binance Testnet')
    
    parser.add_argument('--auto-fallback', action='store_true', default=True,
                        help='Tự động chuyển sang API chính khi cần')
    
    parser.add_argument('--config', type=str, default='account_config.json',
                        help='Đường dẫn tới file cấu hình')
    
    return parser.parse_args()

def save_pid():
    """Lưu PID vào file để có thể dừng tiến trình sau này"""
    pid = os.getpid()
    
    with open('enhanced_market_analyzer.pid', 'w') as f:
        f.write(str(pid))
    
    logger.info(f"Đã lưu PID {pid} vào enhanced_market_analyzer.pid")

def save_uptime_info():
    """Lưu thông tin về thời gian bắt đầu hệ thống"""
    uptime_data = {
        'start_time': datetime.now().timestamp(),
        'start_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('system_uptime.json', 'w') as f:
        json.dump(uptime_data, f, indent=4)
    
    logger.info(f"Đã lưu thông tin uptime vào system_uptime.json")

def main():
    """Hàm chính"""
    try:
        # Phân tích tham số dòng lệnh
        args = parse_arguments()
        
        # Lưu PID
        save_pid()
        
        # Lưu thông tin uptime
        save_uptime_info()
        
        logger.info("Khởi động hệ thống phân tích thị trường nâng cao")
        
        # Khởi tạo EnhancedBinanceAPI
        binance_api = EnhancedBinanceAPI(
            config_path=args.config,
            testnet=args.testnet,
            auto_fallback=args.auto_fallback
        )
        
        # Khởi tạo EnhancedTelegramNotifications
        telegram = EnhancedTelegramNotifications()
        
        # Khởi tạo EnhancedMarketUpdater
        market_updater = EnhancedMarketUpdater(
            config_path=args.config,
            update_interval=args.update_interval,
            notification_interval=args.notification_interval
        )
        
        # Khởi động lịch trình thông báo
        telegram.start_scheduled_notifications()
        
        # Khởi động lịch trình cập nhật thị trường
        market_updater.run_scheduled_updates()
        
        # Gửi thông báo hệ thống đã khởi động
        telegram.telegram.send_notification('info', 
            "<b>🚀 HỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG ĐÃ KHỞI ĐỘNG</b>\n\n"
            f"⏱️ Cập nhật thị trường: mỗi {args.update_interval} phút\n"
            f"📢 Gửi thông báo: mỗi {args.notification_interval} phút\n"
            f"🔄 Tự động chuyển API: {'Bật' if args.auto_fallback else 'Tắt'}\n\n"
            f"<i>Thời gian khởi động: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        
        # Cập nhật ngay lần đầu
        market_updater.update_all_markets()
        
        # Gửi thông báo trạng thái hệ thống
        telegram.send_system_status()
        
        # Giữ cho tiến trình chạy
        logger.info("Hệ thống đang chạy, nhấn Ctrl+C để dừng")
        
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng từ người dùng")
        
        # Dừng các lịch trình
        telegram.stop_scheduled_notifications()
        market_updater.stop_scheduled_updates()
        
        # Gửi thông báo hệ thống đã dừng
        telegram.telegram.send_notification('warning', 
            "<b>⚠️ HỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG ĐÃ DỪNG</b>\n\n"
            f"<i>Thời gian dừng: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        
        logger.info("Hệ thống đã dừng thành công")
        return 0
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())