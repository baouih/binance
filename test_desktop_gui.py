#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script kiểm tra giao diện desktop PyQt5 
"""

import sys
import os
import logging

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("desktop_gui_test.log")
    ]
)

logger = logging.getLogger(__name__)

try:
    from PyQt5.QtWidgets import QApplication
    from enhanced_trading_gui import EnhancedTradingGUI
    
    # Tạo ứng dụng QT
    app = QApplication(sys.argv)
    
    # Tạo cửa sổ chính
    logger.info("Khởi tạo giao diện EnhancedTradingGUI...")
    window = EnhancedTradingGUI()
    
    # Hiển thị cửa sổ
    logger.info("Hiển thị giao diện...")
    window.show()
    
    # Chạy ứng dụng
    logger.info("Chạy ứng dụng QT...")
    sys.exit(app.exec_())
    
except Exception as e:
    logger.exception(f"Lỗi khởi chạy giao diện: {str(e)}")
    print(f"Lỗi: {str(e)}")