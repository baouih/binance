#!/usr/bin/env python3
"""
Tích hợp hồ sơ rủi ro vào Bot giao dịch

Module này tích hợp hệ thống quản lý rủi ro vào bot giao dịch, cho phép
dễ dàng chuyển đổi giữa các hồ sơ rủi ro và tự động cập nhật số dư từ Binance.
"""

import os
import logging
import argparse
import json
from typing import Dict, Any, Optional

from risk_config_manager import RiskConfigManager
from binance_balance_checker import BinanceBalanceChecker

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("risk_profile_integration")

def update_bot_settings(risk_config: Dict) -> bool:
    """
    Cập nhật cài đặt bot dựa trên hồ sơ rủi ro
    
    Args:
        risk_config (Dict): Cấu hình rủi ro
        
    Returns:
        bool: True nếu cập nhật thành công
    """
    # Lấy cài đặt rủi ro hiệu lực
    risk_settings = risk_config.get("custom_settings")
    
    if not risk_settings:
        profile_name = risk_config.get("risk_profile", "medium")
        from risk_config_manager import RISK_PROFILES
        risk_settings = RISK_PROFILES.get(profile_name)
    
    # Thêm thông tin về vốn ban đầu
    risk_settings["initial_balance"] = risk_config.get("initial_balance", 100.0)
    
    try:
        # Cập nhật các file cấu hình liên quan
        bot_configs = {
            "config.json": _update_main_config,
            "live_trading_config.json": _update_live_trading_config,
        }
        
        for config_file, update_func in bot_configs.items():
            if os.path.exists(config_file):
                update_func(config_file, risk_settings)
                logger.info(f"Đã cập nhật cấu hình {config_file}")
            
        return True
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cài đặt bot: {e}")
        return False

def _update_main_config(config_path: str, risk_settings: Dict) -> None:
    """
    Cập nhật file cấu hình chính
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        risk_settings (Dict): Cài đặt rủi ro
    """
    try:
        # Đọc cấu hình hiện tại
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Cập nhật cài đặt rủi ro
        config['risk_management'] = {
            'initial_balance': risk_settings.get('initial_balance', 100.0),
            'max_account_risk': risk_settings.get('max_account_risk', 25.0),
            'risk_per_trade': risk_settings.get('risk_per_trade', 2.5),
            'max_leverage': risk_settings.get('max_leverage', 15),
            'optimal_leverage': risk_settings.get('optimal_leverage', 12),
            'min_distance_to_liquidation': risk_settings.get('min_distance_to_liquidation', 30.0),
            'max_positions': risk_settings.get('max_positions', 2),
            'max_margin_usage': risk_settings.get('max_margin_usage', 60.0),
            'use_trailing_stop': risk_settings.get('use_trailing_stop', True),
            'min_risk_reward': risk_settings.get('min_risk_reward', 1.5)
        }
        
        # Cập nhật stop loss và take profit
        strategy = risk_settings.get('strategy', 'trend')
        config['stop_loss_percent'] = risk_settings.get('stop_loss_percent', {}).get(strategy, 1.5)
        config['take_profit_percent'] = risk_settings.get('take_profit_percent', {}).get(strategy, 2.5)
        
        # Lưu cấu hình
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
            
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật {config_path}: {e}")
        raise

def _update_live_trading_config(config_path: str, risk_settings: Dict) -> None:
    """
    Cập nhật file cấu hình giao dịch thực
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        risk_settings (Dict): Cài đặt rủi ro
    """
    try:
        # Đọc cấu hình hiện tại
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Cập nhật cài đặt rủi ro
        config['risk_management'] = {
            'initial_balance': risk_settings.get('initial_balance', 100.0),
            'max_risk_percent': risk_settings.get('max_account_risk', 25.0) / 100,
            'risk_per_trade_percent': risk_settings.get('risk_per_trade', 2.5) / 100,
            'leverage': risk_settings.get('optimal_leverage', 12),
            'min_distance_to_liquidation': risk_settings.get('min_distance_to_liquidation', 30.0) / 100,
            'max_positions': risk_settings.get('max_positions', 2),
            'max_margin_usage': risk_settings.get('max_margin_usage', 60.0) / 100
        }
        
        # Cập nhật stop loss và take profit
        strategy = risk_settings.get('strategy', 'trend')
        stop_loss = risk_settings.get('stop_loss_percent', {}).get(strategy, 1.5) / 100
        take_profit = risk_settings.get('take_profit_percent', {}).get(strategy, 2.5) / 100
        
        config['position_settings'] = {
            'stop_loss_percent': stop_loss,
            'take_profit_percent': take_profit,
            'use_trailing_stop': risk_settings.get('use_trailing_stop', True),
            'trailing_stop_activation': 0.5,  # Kích hoạt khi đạt 50% take profit
            'trailing_stop_distance': 0.3     # Khoảng cách trailing 30% biến động
        }
        
        # Lưu cấu hình
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
            
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật {config_path}: {e}")
        raise

def start_bot_with_risk_profile(risk_profile: str, update_balance: bool = True) -> bool:
    """
    Khởi động bot với hồ sơ rủi ro đã chọn
    
    Args:
        risk_profile (str): Tên hồ sơ rủi ro ('very_low', 'low', 'medium', 'high', 'very_high')
        update_balance (bool): Tự động cập nhật số dư từ Binance
        
    Returns:
        bool: True nếu khởi động thành công
    """
    try:
        # Khởi tạo trình quản lý cấu hình
        risk_manager = RiskConfigManager()
        
        # Đặt hồ sơ rủi ro
        if risk_profile:
            logger.info(f"Đặt hồ sơ rủi ro: {risk_profile}")
            if not risk_manager.set_risk_profile(risk_profile):
                logger.error(f"Lỗi khi đặt hồ sơ rủi ro: {risk_profile}")
                return False
        
        # Cập nhật số dư từ Binance
        if update_balance:
            logger.info("Đang cập nhật số dư từ tài khoản Binance...")
            if not risk_manager.auto_update_balance_from_binance():
                logger.warning("Không thể cập nhật số dư từ Binance. Sử dụng số dư hiện tại.")
        
        # Lấy cấu hình hiện tại
        risk_config = risk_manager.get_current_config()
        
        # Cập nhật cài đặt bot
        if not update_bot_settings(risk_config):
            logger.error("Lỗi khi cập nhật cài đặt bot.")
            return False
            
        logger.info("Đã cập nhật cài đặt bot thành công!")
        logger.info(f"Số dư ban đầu: ${risk_config.get('initial_balance', 100.0):.2f}")
        
        # Đoạn code khởi động bot thực tế sẽ ở đây
        # ...
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi khởi động bot: {e}")
        return False

def main():
    """Hàm chính để tích hợp và khởi động bot"""
    parser = argparse.ArgumentParser(description="Tích hợp hồ sơ rủi ro vào Bot giao dịch")
    
    parser.add_argument('--risk-profile', type=str, choices=['very_low', 'low', 'medium', 'high', 'very_high'],
                        help="Hồ sơ rủi ro (very_low, low, medium, high, very_high)")
    
    parser.add_argument('--update-balance', action='store_true', default=True,
                        help="Tự động cập nhật số dư từ Binance (mặc định: True)")
    
    parser.add_argument('--no-update-balance', action='store_false', dest='update_balance',
                        help="Không tự động cập nhật số dư từ Binance")
    
    args = parser.parse_args()
    
    # Nếu không có hồ sơ rủi ro, hiển thị menu
    if not args.risk_profile:
        risk_manager = RiskConfigManager()
        current_config = risk_manager.get_current_config()
        current_profile = current_config.get("risk_profile", "medium")
        
        print("===== KHỞI ĐỘNG BOT VỚI HỒ SƠ RỦI RO =====")
        print()
        print(f"Hồ sơ rủi ro hiện tại: {current_profile}")
        print()
        
        print("Các hồ sơ rủi ro có sẵn:")
        print("1. very_low - Rủi ro rất thấp (5-10%)")
        print("2. low - Rủi ro thấp (10-15%)")
        print("3. medium - Rủi ro vừa phải (20-30%)")
        print("4. high - Rủi ro cao (30-50%)")
        print("5. very_high - Rủi ro rất cao (50-70%)")
        print()
        
        choice = input("Chọn hồ sơ rủi ro (1-5, Enter để giữ nguyên): ")
        
        profiles = {
            "1": "very_low",
            "2": "low",
            "3": "medium",
            "4": "high",
            "5": "very_high"
        }
        
        if choice and choice in profiles:
            args.risk_profile = profiles[choice]
        else:
            args.risk_profile = current_profile
            
        update_balance = input("Cập nhật số dư từ tài khoản Binance? (y/n, mặc định: y): ").lower()
        args.update_balance = update_balance != "n"
    
    # Khởi động bot với hồ sơ rủi ro
    if start_bot_with_risk_profile(args.risk_profile, args.update_balance):
        print("Bot đã được khởi động thành công!")
    else:
        print("Lỗi khi khởi động bot.")

if __name__ == "__main__":
    main()