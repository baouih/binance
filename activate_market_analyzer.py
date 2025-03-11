#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kích hoạt hệ thống phân tích thị trường và thông báo
Script này:
1. Khởi tạo và kích hoạt EnhancedMarketUpdater
2. Thiết lập thông báo chi tiết qua Telegram
3. Bắt đầu phân tích coin theo cấu hình
4. Chạy trong chế độ nền với lịch trình thông báo tự động
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("market_analyzer_activation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("market_analyzer")

# Import các module cần thiết
try:
    from enhanced_market_updater import EnhancedMarketUpdater
    from enhanced_binance_api import EnhancedBinanceAPI
    from enhanced_telegram_notifications import EnhancedTelegramNotifications
    from telegram_notifier import TelegramNotifier
    from detailed_trade_notifications import DetailedTradeNotifications
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đã tạo và cài đặt đúng các module cần thiết")
    sys.exit(1)

def save_pid():
    """Lưu PID vào file để có thể dừng tiến trình sau này"""
    pid = os.getpid()
    
    with open('market_analyzer.pid', 'w') as f:
        f.write(str(pid))
    
    logger.info(f"Đã lưu PID {pid} vào market_analyzer.pid")

def main():
    """Hàm chính khởi động hệ thống phân tích thị trường"""
    try:
        logger.info("Bắt đầu kích hoạt hệ thống phân tích thị trường")
        
        # Lưu PID
        save_pid()
        
        # Thông báo bắt đầu
        telegram = TelegramNotifier()
        telegram.send_notification(
            "info",
            "<b>🚀 BẮT ĐẦU KÍCH HOẠT HỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG</b>\n\n"
            "Đang khởi tạo các module...\n"
            f"Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        )
        
        # Khởi tạo Binance API
        binance_api = EnhancedBinanceAPI(
            config_path='account_config.json',
            testnet=True,
            auto_fallback=True
        )
        logger.info("Đã khởi tạo Binance API")
        
        # Khởi tạo thông báo Telegram nâng cao
        telegram_notifications = EnhancedTelegramNotifications(
            notification_interval=30  # 30 phút/lần thông báo
        )
        logger.info("Đã khởi tạo thông báo Telegram nâng cao")
        
        # Khởi tạo thông báo giao dịch chi tiết
        detailed_notifications = DetailedTradeNotifications()
        logger.info("Đã khởi tạo thông báo giao dịch chi tiết")
        
        # Khởi tạo Market Updater
        market_updater = EnhancedMarketUpdater(
            config_path='account_config.json',
            update_interval=15,  # 15 phút/lần cập nhật
            notification_interval=30  # 30 phút/lần thông báo
        )
        logger.info("Đã khởi tạo Enhanced Market Updater")
        
        # Khởi động lịch trình thông báo
        telegram_notifications.start_scheduled_notifications()
        logger.info("Đã khởi động lịch trình thông báo")
        
        # Khởi động lịch trình cập nhật thị trường
        market_updater.run_scheduled_updates()
        logger.info("Đã khởi động lịch trình cập nhật thị trường")
        
        # Thông báo hệ thống đã khởi động
        telegram.send_notification(
            "success",
            "<b>✅ HỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG ĐÃ ĐƯỢC KÍCH HOẠT</b>\n\n"
            "📊 <b>Thông tin chi tiết:</b>\n"
            f"• Cập nhật thị trường: mỗi 15 phút\n"
            f"• Thông báo phân tích: mỗi 30 phút\n"
            f"• Chế độ testnet: Bật\n"
            f"• Các coin theo dõi: {len(market_updater.symbols)}\n\n"
            f"<i>Thời gian kích hoạt: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        
        # Cập nhật thị trường ngay lập tức
        logger.info("Bắt đầu phân tích thị trường lần đầu")
        market_updater.update_all_markets()
        logger.info("Đã hoàn thành phân tích thị trường lần đầu")
        
        # Gửi thông báo phân tích thị trường ngay lập tức
        telegram_notifications.send_market_update()
        
        logger.info("Hệ thống phân tích thị trường đang chạy trong nền")
        
        # Giữ cho tiến trình chạy
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng từ người dùng")
        
        # Dừng các lịch trình khi kết thúc
        telegram_notifications.stop_scheduled_notifications()
        market_updater.stop_scheduled_updates()
        
        # Thông báo hệ thống đã dừng
        telegram.send_notification(
            "warning",
            "<b>⚠️ HỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG ĐÃ DỪNG</b>\n\n"
            f"<i>Thời gian dừng: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        
        logger.info("Hệ thống phân tích thị trường đã dừng thành công")
        return 0
        
    except Exception as e:
        logger.error(f"Lỗi không mong đợi khi khởi động hệ thống: {e}")
        
        # Thông báo lỗi qua Telegram
        try:
            telegram = TelegramNotifier()
            telegram.send_notification(
                "error",
                "<b>❌ LỖI KHI KHỞI ĐỘNG HỆ THỐNG PHÂN TÍCH</b>\n\n"
                f"Thông báo lỗi: {str(e)}\n\n"
                f"<i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            )
        except:
            pass  # Bỏ qua nếu không thể gửi thông báo
            
        return 1

if __name__ == "__main__":
    sys.exit(main())