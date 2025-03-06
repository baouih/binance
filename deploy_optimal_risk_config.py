#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script triển khai cấu hình rủi ro tối ưu vào môi trường giao dịch thực tế

Script này triển khai cấu hình rủi ro tối ưu vào môi trường giao dịch thực tế,
không làm ảnh hưởng đến các test đang chạy. Script cũng tạo các file backup 
để có thể khôi phục cấu hình nếu cần.
"""

import os
import json
import shutil
import logging
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("deploy_optimal_risk")

# Đường dẫn các file cấu hình
CONFIG_PATHS = {
    'strategy': 'configs/strategy_market_config.json',
    'signal_filter': 'risk_analysis/signal_filter_config.json',
    'risk_reward': 'risk_analysis/risk_reward_config.json'
}

# Thư mục backup
BACKUP_DIR = 'backups/configs'

def ensure_backup_dir():
    """Đảm bảo thư mục backup tồn tại"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    logger.info(f"Đã tạo thư mục backup: {BACKUP_DIR}")

def create_backup(config_path: str) -> str:
    """
    Tạo bản backup của file cấu hình
    
    Args:
        config_path (str): Đường dẫn file cấu hình
        
    Returns:
        str: Đường dẫn đến file backup
    """
    if not os.path.exists(config_path):
        logger.error(f"File cấu hình không tồn tại: {config_path}")
        return ""
    
    # Tạo tên file backup với timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(config_path)
    backup_path = os.path.join(BACKUP_DIR, f"{filename}.{timestamp}.bak")
    
    # Tạo backup
    try:
        shutil.copy2(config_path, backup_path)
        logger.info(f"Đã tạo backup tại: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Lỗi khi tạo backup {config_path}: {e}")
        return ""

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
            config = json.load(f)
        return config
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
        logger.info(f"Đã lưu cấu hình vào {config_path}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình vào {config_path}: {e}")
        return False

def update_strategy_config() -> bool:
    """
    Cập nhật cấu hình chiến lược với các giá trị tối ưu
    
    Returns:
        bool: True nếu cập nhật thành công, False nếu lỗi
    """
    strategy_path = CONFIG_PATHS['strategy']
    
    # Tạo backup
    backup = create_backup(strategy_path)
    if not backup:
        return False
    
    # Tải cấu hình hiện tại
    config = load_json_config(strategy_path)
    if not config:
        return False
    
    # Cập nhật cấu hình
    risk_adjustments = {
        'trending': 1.5,    # Tăng 50% rủi ro trong thị trường xu hướng 
        'ranging': 0.7,     # Giảm 30% rủi ro trong thị trường dao động
        'volatile': 0.5,    # Giảm 50% rủi ro trong thị trường biến động
        'quiet': 1.2        # Tăng 20% rủi ro trong thị trường yên tĩnh
    }
    
    # Cập nhật risk_adjustment cho từng chế độ thị trường
    for regime, value in risk_adjustments.items():
        if regime in config:
            config[regime]['risk_adjustment'] = value
            logger.info(f"Cập nhật risk_adjustment cho {regime}: {value}")
    
    # Cập nhật bộ lọc tín hiệu
    try:
        signal_filter_config = load_json_config(CONFIG_PATHS['signal_filter'])
        if signal_filter_config and 'signal_filter' in signal_filter_config:
            for regime, filters in signal_filter_config['signal_filter'].items():
                if regime in config:
                    if 'signal_filter' not in config[regime]:
                        config[regime]['signal_filter'] = {}
                    config[regime]['signal_filter'].update(filters)
                    logger.info(f"Cập nhật signal_filter cho {regime}: {filters}")
    except Exception as e:
        logger.warning(f"Lỗi khi cập nhật bộ lọc tín hiệu: {e}")
    
    # Cập nhật tỷ lệ TP/SL
    try:
        risk_reward_config = load_json_config(CONFIG_PATHS['risk_reward'])
        if risk_reward_config and 'risk_reward_ratios' in risk_reward_config:
            for regime, ratios in risk_reward_config['risk_reward_ratios'].items():
                if regime in config:
                    if 'risk_reward' not in config[regime]:
                        config[regime]['risk_reward'] = {}
                    config[regime]['risk_reward'].update(ratios)
                    logger.info(f"Cập nhật risk_reward cho {regime}: {ratios}")
    except Exception as e:
        logger.warning(f"Lỗi khi cập nhật tỷ lệ TP/SL: {e}")
    
    # Lưu cấu hình đã cập nhật
    return save_json_config(config, strategy_path)

def update_base_risk_config() -> bool:
    """
    Cập nhật cấu hình rủi ro cơ bản
    
    Returns:
        bool: True nếu cập nhật thành công, False nếu lỗi
    """
    config_path = 'configs/risk_config.json'
    
    # Kiểm tra file cấu hình
    if not os.path.exists(config_path):
        # Tạo cấu hình mới
        risk_config = {
            'base_risk_percentage': 1.0,
            'min_risk_percentage': 0.5,
            'max_risk_percentage': 1.5,
            'use_adaptive_risk': True,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return save_json_config(risk_config, config_path)
    
    # Tạo backup
    backup = create_backup(config_path)
    if not backup:
        return False
    
    # Tải cấu hình hiện tại
    config = load_json_config(config_path)
    if not config:
        return False
    
    # Cập nhật cấu hình
    config['base_risk_percentage'] = 1.0
    config['min_risk_percentage'] = 0.5
    config['max_risk_percentage'] = 1.5
    config['use_adaptive_risk'] = True
    config['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Lưu cấu hình
    return save_json_config(config, config_path)

def create_deployment_summary() -> bool:
    """
    Tạo báo cáo tóm tắt việc triển khai
    
    Returns:
        bool: True nếu tạo thành công, False nếu lỗi
    """
    try:
        summary = f"""# Báo Cáo Triển Khai Cấu Hình Rủi Ro Tối Ưu
        
## Thời gian triển khai
- Ngày triển khai: {datetime.now().strftime("%Y-%m-%d")}
- Giờ triển khai: {datetime.now().strftime("%H:%M:%S")}

## Các cấu hình đã triển khai

### 1. Điều chỉnh rủi ro theo chế độ thị trường
- Thị trường xu hướng (Trending): 1.5x (tăng 50%) 
- Thị trường dao động (Ranging): 0.7x (giảm 30%)
- Thị trường biến động (Volatile): 0.5x (giảm 50%)
- Thị trường yên tĩnh (Quiet): 1.2x (tăng 20%)

### 2. Bộ lọc tín hiệu theo chế độ thị trường
- Thị trường xu hướng (Trending): min_strength=70, min_confirmation=2
- Thị trường dao động (Ranging): min_strength=85, min_confirmation=3
- Thị trường biến động (Volatile): min_strength=90, min_confirmation=3
- Thị trường yên tĩnh (Quiet): min_strength=75, min_confirmation=2

### 3. Tỷ lệ TP/SL theo chế độ thị trường
- Thị trường xu hướng (Trending): TP=2.5, SL=1.0
- Thị trường dao động (Ranging): TP=1.8, SL=1.0
- Thị trường biến động (Volatile): TP=3.0, SL=1.0
- Thị trường yên tĩnh (Quiet): TP=2.2, SL=1.0

### 4. Cấu hình rủi ro cơ sở
- Mức rủi ro cơ sở: 1.0%
- Mức rủi ro tối thiểu: 0.5%
- Mức rủi ro tối đa: 1.5%
- Rủi ro thích ứng: Bật

## Các file đã cập nhật
- configs/strategy_market_config.json
- configs/risk_config.json

## Files backup
"""
        
        # Thêm danh sách các file backup
        backup_files = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.bak')]
        for backup_file in backup_files:
            backup_path = os.path.join(BACKUP_DIR, backup_file)
            summary += f"- {backup_path}\n"
        
        # Lưu báo cáo
        report_path = 'risk_analysis/deployment_summary.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        logger.info(f"Đã tạo báo cáo triển khai tại {report_path}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo triển khai: {e}")
        return False

def main():
    """Hàm chính chạy quá trình triển khai"""
    parser = argparse.ArgumentParser(description='Triển khai cấu hình rủi ro tối ưu vào môi trường giao dịch thực tế')
    parser.add_argument('--confirm', action='store_true', help='Xác nhận triển khai')
    args = parser.parse_args()
    
    if not args.confirm:
        logger.warning("Bạn cần sử dụng tham số --confirm để xác nhận triển khai")
        return
    
    # Đảm bảo thư mục backup tồn tại
    ensure_backup_dir()
    
    # Cập nhật cấu hình
    success_strategy = update_strategy_config()
    success_risk = update_base_risk_config()
    
    # Tạo báo cáo triển khai
    if success_strategy and success_risk:
        create_deployment_summary()
        logger.info("Triển khai cấu hình rủi ro tối ưu thành công!")
    else:
        logger.error("Triển khai cấu hình rủi ro tối ưu thất bại!")

if __name__ == "__main__":
    main()