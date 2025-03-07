#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script để cập nhật cấu hình rủi ro trong hệ thống
Thay đổi các mức rủi ro mặc định sang: 2.0%, 2.5%, 3.0%, 4.0%, 5.0%
"""

import os
import sys
import json
import logging
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("risk_config_updater")

# Danh sách mức rủi ro mới
NEW_RISK_LEVELS = [2.0, 2.5, 3.0, 4.0, 5.0]

def update_config_files():
    """
    Cập nhật mức rủi ro trong các tệp cấu hình
    """
    # 1. Cập nhật tệp cấu hình chính
    main_config_file = "bot_config.json"
    if os.path.exists(main_config_file):
        try:
            with open(main_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if 'risk_levels' in config:
                old_levels = config['risk_levels']
                config['risk_levels'] = NEW_RISK_LEVELS
                
                # Lưu cấu hình
                with open(main_config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                
                logger.info(f"Đã cập nhật mức rủi ro trong {main_config_file}: {old_levels} -> {NEW_RISK_LEVELS}")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật {main_config_file}: {str(e)}")
    
    # 2. Tìm và cập nhật các tệp Python có chứa mức rủi ro
    files_to_check = [
        "run_quick_test.py",
        "run_single_coin_risk_test.py",
        "risk_config_manager.py",
        "enhanced_backtest.py",
        "run_multi_risk_test.py"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            try:
                # Đọc nội dung tệp
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Tìm và thay thế mức rủi ro
                if "RISK_LEVELS" in content or "risk_levels" in content:
                    # Mẫu thay thế 1: RISK_LEVELS = [x, y, z]
                    old_pattern = "RISK_LEVELS = ["
                    if old_pattern in content:
                        # Tìm vị trí bắt đầu và kết thúc
                        start_idx = content.find(old_pattern)
                        if start_idx != -1:
                            end_idx = content.find("]", start_idx)
                            if end_idx != -1:
                                old_part = content[start_idx:end_idx+1]
                                new_part = f"RISK_LEVELS = {str(NEW_RISK_LEVELS)}"
                                content = content.replace(old_part, new_part)
                    
                    # Mẫu thay thế 2: risk_levels = [x, y, z]
                    old_pattern = "risk_levels = ["
                    if old_pattern in content:
                        # Tìm vị trí bắt đầu và kết thúc
                        start_idx = content.find(old_pattern)
                        if start_idx != -1:
                            end_idx = content.find("]", start_idx)
                            if end_idx != -1:
                                old_part = content[start_idx:end_idx+1]
                                new_part = f"risk_levels = {str(NEW_RISK_LEVELS)}"
                                content = content.replace(old_part, new_part)
                    
                    # Lưu nội dung cập nhật
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    logger.info(f"Đã cập nhật mức rủi ro trong {file_path}")
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật {file_path}: {str(e)}")
    
    # 3. Tạo bản sao lưu cấu hình cũ
    try:
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backup_file = f"{backup_dir}/risk_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_data = {
            "old_risk_levels": [0.5, 1.0, 1.5, 2.0, 3.0],
            "new_risk_levels": NEW_RISK_LEVELS,
            "updated_files": files_to_check,
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2)
        
        logger.info(f"Đã tạo bản sao lưu cấu hình rủi ro cũ tại {backup_file}")
    except Exception as e:
        logger.error(f"Lỗi khi tạo bản sao lưu: {str(e)}")

def main():
    logger.info("Bắt đầu cập nhật cấu hình rủi ro...")
    logger.info(f"Mức rủi ro mới: {NEW_RISK_LEVELS}")
    
    update_config_files()
    
    logger.info("Đã hoàn thành cập nhật cấu hình rủi ro")

if __name__ == "__main__":
    main()