#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script thiết lập cấu hình rủi ro tối ưu

Script này cập nhật cấu hình chiến lược thích ứng dựa trên kết quả phân tích hiệu suất
theo mức rủi ro và chế độ thị trường. Script tự động cập nhật:
- Điều chỉnh rủi ro theo từng chế độ thị trường
- Bộ lọc tín hiệu theo chế độ thị trường
- Tỷ lệ take profit/stop loss theo chế độ thị trường
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, List, Tuple

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("risk_setup")

# Đường dẫn mặc định
STRATEGY_CONFIG_PATH = 'configs/strategy_market_config.json'
SIGNAL_FILTER_CONFIG_PATH = 'risk_analysis/signal_filter_config.json'
RISK_REWARD_CONFIG_PATH = 'risk_analysis/risk_reward_config.json'

def load_json_config(config_path: str) -> Dict:
    """
    Tải cấu hình từ file JSON
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        
    Returns:
        Dict: Cấu hình đã tải
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình từ {config_path}: {e}")
        return {}

def save_json_config(config: Dict, config_path: str) -> bool:
    """
    Lưu cấu hình vào file JSON
    
    Args:
        config (Dict): Cấu hình cần lưu
        config_path (str): Đường dẫn đến file cấu hình
        
    Returns:
        bool: True nếu lưu thành công, False nếu lỗi
    """
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình vào {config_path}: {e}")
        return False

def update_risk_adjustment(config: Dict, risk_values: Dict[str, float]) -> Dict:
    """
    Cập nhật điều chỉnh rủi ro theo chế độ thị trường
    
    Args:
        config (Dict): Cấu hình hiện tại
        risk_values (Dict[str, float]): Giá trị điều chỉnh cho từng chế độ
        
    Returns:
        Dict: Cấu hình đã cập nhật
    """
    for regime, value in risk_values.items():
        if regime in config:
            config[regime]['risk_adjustment'] = value
            logger.info(f"Đã cập nhật risk_adjustment cho {regime}: {value}")
    return config

def update_signal_filters(strategy_config: Dict, signal_filter_config: Dict) -> Dict:
    """
    Cập nhật bộ lọc tín hiệu cho từng chế độ thị trường
    
    Args:
        strategy_config (Dict): Cấu hình chiến lược hiện tại
        signal_filter_config (Dict): Cấu hình bộ lọc tín hiệu
        
    Returns:
        Dict: Cấu hình đã cập nhật
    """
    if 'signal_filter' in signal_filter_config:
        for regime, filters in signal_filter_config['signal_filter'].items():
            if regime in strategy_config:
                if 'signal_filter' not in strategy_config[regime]:
                    strategy_config[regime]['signal_filter'] = {}
                strategy_config[regime]['signal_filter'].update(filters)
                logger.info(f"Đã cập nhật signal_filter cho {regime}: {filters}")
    return strategy_config

def update_risk_reward_ratios(strategy_config: Dict, risk_reward_config: Dict) -> Dict:
    """
    Cập nhật tỷ lệ take profit/stop loss cho từng chế độ thị trường
    
    Args:
        strategy_config (Dict): Cấu hình chiến lược hiện tại
        risk_reward_config (Dict): Cấu hình tỷ lệ risk/reward
        
    Returns:
        Dict: Cấu hình đã cập nhật
    """
    if 'risk_reward_ratios' in risk_reward_config:
        for regime, ratios in risk_reward_config['risk_reward_ratios'].items():
            if regime in strategy_config:
                if 'risk_reward' not in strategy_config[regime]:
                    strategy_config[regime]['risk_reward'] = {}
                strategy_config[regime]['risk_reward'].update(ratios)
                logger.info(f"Đã cập nhật risk_reward cho {regime}: {ratios}")
    return strategy_config

def create_backup(file_path: str) -> bool:
    """
    Tạo bản backup của file cấu hình
    
    Args:
        file_path (str): Đường dẫn đến file cần backup
        
    Returns:
        bool: True nếu backup thành công, False nếu lỗi
    """
    try:
        backup_path = f"{file_path}.bak"
        if os.path.exists(file_path):
            import shutil
            shutil.copy2(file_path, backup_path)
            logger.info(f"Đã tạo backup tại: {backup_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Lỗi khi tạo backup {file_path}: {e}")
        return False

def update_config_values(base_config_path: str = STRATEGY_CONFIG_PATH,
                        signal_filter_path: str = SIGNAL_FILTER_CONFIG_PATH,
                        risk_reward_path: str = RISK_REWARD_CONFIG_PATH) -> bool:
    """
    Cập nhật các giá trị cấu hình từ các file nguồn
    
    Args:
        base_config_path (str): Đường dẫn đến file cấu hình chiến lược
        signal_filter_path (str): Đường dẫn đến file cấu hình bộ lọc tín hiệu
        risk_reward_path (str): Đường dẫn đến file cấu hình tỷ lệ risk/reward
        
    Returns:
        bool: True nếu cập nhật thành công, False nếu lỗi
    """
    try:
        # Tạo backup
        create_backup(base_config_path)
        
        # Tải các cấu hình
        strategy_config = load_json_config(base_config_path)
        signal_filter_config = load_json_config(signal_filter_path)
        risk_reward_config = load_json_config(risk_reward_path)
        
        if not strategy_config:
            logger.error(f"Không thể tải cấu hình từ {base_config_path}")
            return False
            
        # Lấy giá trị điều chỉnh rủi ro từ config hoặc dùng giá trị mặc định
        risk_values = {
            'trending': 1.5,  # Tăng 50% rủi ro trong thị trường xu hướng mạnh
            'ranging': 0.7,   # Giảm 30% rủi ro trong thị trường dao động
            'volatile': 0.5,  # Giảm 50% rủi ro trong thị trường biến động mạnh
            'quiet': 1.2      # Tăng 20% rủi ro trong thị trường yên tĩnh
        }
        
        # Cập nhật từng phần
        strategy_config = update_risk_adjustment(strategy_config, risk_values)
        strategy_config = update_signal_filters(strategy_config, signal_filter_config)
        strategy_config = update_risk_reward_ratios(strategy_config, risk_reward_config)
        
        # Lưu cấu hình đã cập nhật
        if save_json_config(strategy_config, base_config_path):
            logger.info(f"Đã cập nhật thành công cấu hình tại {base_config_path}")
            return True
        else:
            logger.error(f"Không thể lưu cấu hình vào {base_config_path}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình: {e}")
        return False

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Cập nhật cấu hình rủi ro tối ưu')
    parser.add_argument('--config', type=str, default=STRATEGY_CONFIG_PATH, 
                      help='Đường dẫn đến file cấu hình chiến lược')
    parser.add_argument('--signal-filter', type=str, default=SIGNAL_FILTER_CONFIG_PATH,
                      help='Đường dẫn đến file cấu hình bộ lọc tín hiệu')
    parser.add_argument('--risk-reward', type=str, default=RISK_REWARD_CONFIG_PATH,
                      help='Đường dẫn đến file cấu hình tỷ lệ risk/reward')
    args = parser.parse_args()
    
    success = update_config_values(args.config, args.signal_filter, args.risk_reward)
    
    if success:
        logger.info("Cập nhật cấu hình rủi ro tối ưu thành công!")
        sys.exit(0)
    else:
        logger.error("Cập nhật cấu hình rủi ro tối ưu thất bại!")
        sys.exit(1)

if __name__ == "__main__":
    main()