#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
from enhanced_trading_gui import EnhancedTradingGUI
from PyQt5.QtWidgets import QApplication

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_gui.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("EnhancedGUILauncher")

def check_environment_variables():
    """Kiểm tra biến môi trường bắt buộc"""
    required_vars = [
        "BINANCE_TESTNET_API_KEY",
        "BINANCE_TESTNET_API_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"Thiếu các biến môi trường: {', '.join(missing_vars)}")
        return False
    
    return True

def main():
    """Hàm chính để chạy ứng dụng"""
    logger.info("Đang khởi động giao diện giao dịch nâng cao...")
    
    # Kiểm tra biến môi trường
    check_environment_variables()
    
    # Khởi tạo ứng dụng
    app = QApplication(sys.argv)
    
    # Khởi tạo giao diện
    window = EnhancedTradingGUI()
    window.show()
    
    # Chạy ứng dụng
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()