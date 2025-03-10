#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module chạy ứng dụng desktop giao dịch
"""

import os
import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from enhanced_trading_gui import EnhancedTradingGUI

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

def main():
    """Hàm chính để chạy ứng dụng desktop"""
    try:
        logger.info("Khởi động ứng dụng desktop trading")
        
        # Tạo ứng dụng Qt
        app = QApplication(sys.argv)
        app.setStyle('Fusion')  # Sử dụng style Fusion cho giao diện hiện đại
        
        # Thiết lập icon và thông tin ứng dụng
        app.setApplicationName("Trading Bot GUI")
        app.setWindowIcon(QIcon("static/icons/app_icon.png"))
        
        # Tạo cửa sổ chính
        main_window = EnhancedTradingGUI()
        main_window.show()
        
        # Chạy vòng lặp sự kiện
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Lỗi khi khởi động ứng dụng: {str(e)}", exc_info=True)
        print(f"Lỗi: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()