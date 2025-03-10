#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ứng dụng desktop cho hệ thống giao dịch crypto
Hỗ trợ đầy đủ chức năng quản lý, thông báo, vào lệnh, mô hình bot,
vị thế, cài đặt, Telegram và các chức năng kiểm tra
"""

import sys
import os
import logging
from datetime import datetime
import traceback

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("desktop_app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("desktop_app")

try:
    from PyQt5.QtWidgets import QApplication
    from enhanced_trading_gui import EnhancedTradingGUI
except ImportError as e:
    logger.error(f"Lỗi khi import các module cần thiết: {str(e)}")
    logger.error("Đảm bảo đã cài đặt PyQt5 và các thư viện khác")
    sys.exit(1)

def exception_hook(exctype, value, tb):
    """
    Bắt và ghi log các exception không được xử lý
    """
    logger.error("Unhandled exception:", exc_info=(exctype, value, tb))
    logger.error("".join(traceback.format_exception(exctype, value, tb)))
    sys.__excepthook__(exctype, value, tb)

def main():
    """
    Hàm chính để chạy ứng dụng desktop
    """
    # Đặt exception hook để bắt tất cả các lỗi không được xử lý
    sys.excepthook = exception_hook
    
    logger.info("Khởi động ứng dụng giao dịch desktop")
    
    # Kiểm tra thông tin API
    for key in ["BINANCE_TESTNET_API_KEY", "BINANCE_TESTNET_API_SECRET"]:
        if not os.environ.get(key):
            logger.warning(f"Thiếu biến môi trường {key}")
    
    # Kiểm tra thông tin Telegram
    for key in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
        if not os.environ.get(key):
            logger.warning(f"Thiếu biến môi trường {key}")
    
    # Khởi tạo ứng dụng PyQt
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Sử dụng style Fusion cho giao diện đồng nhất
    
    # Khởi tạo cửa sổ chính
    window = EnhancedTradingGUI()
    
    # Hiển thị cửa sổ
    window.show()
    
    # Chạy vòng lặp sự kiện
    return app.exec_()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {str(e)}")
        logger.error(traceback.format_exc())