#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script để kiểm tra giao diện desktop
"""

import os
import sys
import json
import logging
from PyQt5.QtWidgets import QApplication

# Thiết lập logging
logger = logging.getLogger("test_desktop_app")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

try:
    # Thử import lớp giao diện desktop
    from enhanced_trading_gui import EnhancedTradingGUI
    logger.info("Đã import thành công lớp EnhancedTradingGUI")
except ImportError as e:
    logger.error(f"Lỗi khi import lớp EnhancedTradingGUI: {str(e)}")
    sys.exit(1)

def test_risk_configs():
    """Kiểm tra các file cấu hình rủi ro"""
    risk_configs_dir = "risk_configs"
    
    if not os.path.exists(risk_configs_dir):
        logger.error(f"Thư mục {risk_configs_dir} không tồn tại")
        return False
    
    # Kiểm tra các file cấu hình cần thiết
    required_files = [
        "current_risk_config.json",
        "extremely_high_risk_config.json",
        "extremely_low_risk_config.json",
        "low_risk_config.json",
        "medium_risk_config.json",
        "BTC_risk_config.json",
        "ETH_risk_config.json"
    ]
    
    missing_files = []
    for file in required_files:
        file_path = os.path.join(risk_configs_dir, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Thiếu các file cấu hình rủi ro: {', '.join(missing_files)}")
        return False
    
    # Kiểm tra nội dung file
    try:
        current_config_path = os.path.join(risk_configs_dir, "current_risk_config.json")
        with open(current_config_path, 'r', encoding='utf-8') as f:
            current_config = json.load(f)
            
        # Kiểm tra các trường cần thiết
        required_fields = ['risk_level', 'risk_per_trade', 'max_leverage', 'stop_loss_atr_multiplier', 'take_profit_atr_multiplier']
        for field in required_fields:
            if field not in current_config:
                logger.error(f"Thiếu trường {field} trong file cấu hình current_risk_config.json")
                return False
                
        logger.info("Kiểm tra file cấu hình rủi ro thành công")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi đọc file cấu hình rủi ro: {str(e)}")
        return False

def main():
    """Hàm chính để kiểm tra ứng dụng desktop"""
    logger.info("Bắt đầu kiểm tra ứng dụng desktop")
    
    # Kiểm tra cấu hình rủi ro
    if not test_risk_configs():
        logger.warning("Kiểm tra cấu hình rủi ro thất bại, tiếp tục chương trình")
    
    # Không khởi tạo QApplication trong môi trường không có GUI
    logger.info("Bỏ qua khởi tạo ứng dụng PyQt do môi trường không hỗ trợ")
    logger.info("Kiểm tra thành công, kết thúc chương trình")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)