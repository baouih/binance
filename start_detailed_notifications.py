#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script khởi động hệ thống thông báo chi tiết

Script này kết hợp các module đã tạo để khởi động hệ thống thông báo chi tiết
và theo dõi giao dịch trên Binance.
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("start_detailed_notifications.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("start_detailed_notifications")

# Import module cần thiết
try:
    from integrate_detailed_notifications import IntegratedNotificationSystem
    from telegram_notifier import TelegramNotifier
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đã tạo các module cần thiết")
    sys.exit(1)

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Khởi động hệ thống thông báo chi tiết')
    
    parser.add_argument('--config', type=str, default='account_config.json',
                        help='Đường dẫn tới file cấu hình')
    
    parser.add_argument('--notify-interval', type=int, default=15,
                        help='Khoảng thời gian gửi thông báo định kỳ (phút)')
    
    parser.add_argument('--daemonize', action='store_true',
                        help='Chạy như daemon trong nền')
    
    return parser.parse_args()

def save_pid():
    """Lưu PID vào file để có thể dừng tiến trình sau này"""
    pid = os.getpid()
    
    with open('detailed_notifications.pid', 'w') as f:
        f.write(str(pid))
    
    logger.info(f"Đã lưu PID {pid} vào detailed_notifications.pid")

def update_config(config_path: str, notification_interval: int):
    """
    Cập nhật cấu hình với khoảng thời gian thông báo
    
    Args:
        config_path (str): Đường dẫn tới file cấu hình
        notification_interval (int): Khoảng thời gian gửi thông báo (phút)
    """
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Cập nhật khoảng thời gian thông báo
            config['notification_interval'] = notification_interval
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Đã cập nhật cấu hình với khoảng thời gian thông báo {notification_interval} phút")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình: {e}")

def main():
    """Hàm chính"""
    try:
        # Phân tích tham số dòng lệnh
        args = parse_arguments()
        
        # Lưu PID
        save_pid()
        
        # Cập nhật cấu hình
        update_config(args.config, args.notify_interval)
        
        # Thông báo khởi động
        telegram = TelegramNotifier()
        telegram.send_notification('info', 
            f"<b>🚀 KHỞI ĐỘNG HỆ THỐNG THÔNG BÁO CHI TIẾT</b>\n\n"
            f"⚙️ Thông báo chi tiết cách {args.notify_interval} phút\n"
            f"📊 Theo dõi vào lệnh, ra lệnh, lãi/lỗ\n"
            f"💰 Thống kê giao dịch tự động\n\n"
            f"<i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        
        logger.info("Khởi động hệ thống thông báo chi tiết")
        
        # Khởi tạo hệ thống
        system = IntegratedNotificationSystem(config_path=args.config)
        
        # Bắt đầu theo dõi
        system.start_monitoring()
        
        # Nếu chạy daemon, không block
        if args.daemonize:
            logger.info("Chạy như daemon, exit")
            return 0
        
        # Giữ cho tiến trình chạy
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng từ người dùng")
            system.stop_monitoring()
        
        logger.info("Hệ thống thông báo chi tiết đã dừng")
        return 0
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())