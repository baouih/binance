#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script chạy ứng dụng desktop
"""

import os
import sys
import logging
import threading
import io

# Sửa lỗi mã hóa tiếng Việt
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("desktop_app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("desktop_app")

# Import giao diện đồ họa nâng cao
try:
    from enhanced_trading_gui import EnhancedTradingGUI
    from auto_update_client import AutoUpdater
except ImportError as e:
    logger.error(f"Lỗi khi import module: {str(e)}")
    sys.exit(1)

def check_updates():
    """Kiểm tra cập nhật"""
    try:
        updater = AutoUpdater()
        
        # Kiểm tra cập nhật
        has_update, new_version, update_info = updater.check_for_updates()
        
        if has_update:
            logger.info(f"Phát hiện bản cập nhật mới: {new_version}")
            
            # Thông báo về bản cập nhật mới
            changes = update_info.get("changes", [])
            if changes:
                logger.info("Các thay đổi trong bản cập nhật mới:")
                for change in changes:
                    logger.info(f"- {change}")
            
            # Tải xuống và cài đặt bản cập nhật
            if updater.download_update(new_version):
                logger.info(f"Đã tải xuống bản cập nhật {new_version}")
                
                # Cài đặt bản cập nhật
                updater.install_update(new_version)
            else:
                logger.error("Không thể tải xuống bản cập nhật")
        else:
            logger.info("Không có bản cập nhật mới")
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra cập nhật: {str(e)}")

def main():
    """Hàm chính"""
    try:
        # Thiết lập các biến môi trường nếu cần
        if "BINANCE_TESTNET_API_KEY" not in os.environ:
            # Thử tải từ file .env
            if os.path.exists(".env"):
                from dotenv import load_dotenv
                load_dotenv()
                logger.info("Đã tải biến môi trường từ file .env")
        
        # Kiểm tra cập nhật trong luồng riêng
        update_thread = threading.Thread(target=check_updates)
        update_thread.daemon = True
        update_thread.start()
        
        # Khởi tạo ứng dụng
        app = QApplication(sys.argv)
        app.setApplicationName("Bot Giao Dịch Crypto")
        
        # Thiết lập icon cho ứng dụng
        icon_path = "static/icons/app_icon.png"
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        
        # Khởi tạo cửa sổ chính
        window = EnhancedTradingGUI()
        window.show()
        
        # Chạy ứng dụng
        sys.exit(app.exec_())
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy ứng dụng: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()