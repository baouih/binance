#!/usr/bin/env python3
"""
Script tích hợp và khởi động bot giao dịch với các cài đặt đã chọn

Script này tự động khởi động bot giao dịch với các cài đặt phù hợp từ
loại tài khoản, thuật toán giao dịch và hồ sơ rủi ro.
"""

import os
import sys
import logging
import argparse
import json
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_startup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("integration_script")

# Import các module đã tạo
try:
    from risk_config_manager import RiskConfigManager
    from account_type_selector import AccountTypeSelector
    from trading_algorithm_selector import TradingAlgorithmSelector
    from binance_balance_checker import BinanceBalanceChecker
except ImportError as e:
    logger.error(f"Lỗi khi import module: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

def load_configs() -> Dict[str, Any]:
    """
    Tải tất cả các cấu hình cần thiết
    
    Returns:
        Dict[str, Any]: Tất cả cấu hình đã tải
    """
    configs = {}
    
    try:
        # Tải cấu hình rủi ro
        risk_manager = RiskConfigManager()
        configs['risk'] = risk_manager.get_current_config()
        configs['risk_effective'] = risk_manager.get_effective_risk_settings()
        
        # Tải cấu hình loại tài khoản
        account_selector = AccountTypeSelector()
        configs['account'] = account_selector.get_current_config()
        configs['account_effective'] = account_selector.get_effective_settings()
        
        # Tải cấu hình thuật toán
        algorithm_selector = TradingAlgorithmSelector()
        configs['algorithm'] = algorithm_selector.get_current_config()
        
        logger.info("Đã tải tất cả cấu hình")
        
        return configs
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {e}")
        logger.error(traceback.format_exc())
        return {}

def update_balance_from_binance() -> bool:
    """
    Cập nhật số dư từ tài khoản Binance
    
    Returns:
        bool: True nếu cập nhật thành công
    """
    try:
        # Tải cấu hình loại tài khoản để xác định account_type
        account_selector = AccountTypeSelector()
        account_config = account_selector.get_current_config()
        account_type = account_config.get('account_type', 'futures')
        
        # Tải cấu hình rủi ro
        risk_manager = RiskConfigManager()
        
        # Cập nhật số dư
        success = risk_manager.auto_update_balance_from_binance(account_type=account_type)
        
        if success:
            new_balance = risk_manager.get_current_config().get('initial_balance', 0)
            logger.info(f"Đã cập nhật số dư từ tài khoản Binance: ${new_balance:.2f}")
        else:
            logger.warning("Không thể cập nhật số dư từ tài khoản Binance")
            
        return success
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật số dư từ Binance: {e}")
        logger.error(traceback.format_exc())
        return False

def update_main_config(configs: Dict[str, Any]) -> bool:
    """
    Cập nhật cấu hình chính của bot
    
    Args:
        configs (Dict[str, Any]): Các cấu hình đã tải
        
    Returns:
        bool: True nếu cập nhật thành công
    """
    try:
        # Tạo cấu hình tổng hợp
        main_config = {
            "account": {
                "type": configs['account'].get('account_type', 'futures'),
                "leverage": configs['account'].get('leverage', 10),
                "symbols": configs['account'].get('symbols', ["BTCUSDT"]),
                "timeframes": configs['account'].get('timeframes', ["1h"]),
            },
            "risk_management": {
                "initial_balance": configs['risk'].get('initial_balance', 100.0),
                "max_account_risk": configs['risk_effective'].get('max_account_risk', 25.0),
                "risk_per_trade": configs['risk_effective'].get('risk_per_trade', 2.5),
                "max_leverage": configs['risk_effective'].get('max_leverage', 15),
                "optimal_leverage": configs['risk_effective'].get('optimal_leverage', 12),
                "min_distance_to_liquidation": configs['risk_effective'].get('min_distance_to_liquidation', 30.0),
                "max_positions": configs['risk_effective'].get('max_positions', 2),
                "max_margin_usage": configs['risk_effective'].get('max_margin_usage', 60.0),
                "use_trailing_stop": configs['risk_effective'].get('use_trailing_stop', True),
                "min_risk_reward": configs['risk_effective'].get('min_risk_reward', 1.5)
            },
            "trading_algorithm": {
                "primary": configs['algorithm'].get('primary_algorithm', 'combined_strategy'),
                "backup": configs['algorithm'].get('backup_algorithm', 'ema_cross_strategy'),
                "enabled_algorithms": [algo for algo, config in configs['algorithm'].get('algorithms', {}).items() if config.get('enabled', False)]
            },
            "parameters": {},
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "config_version": "1.0"
        }
        
        # Thêm tham số từng thuật toán
        for algo, algo_config in configs['algorithm'].get('algorithms', {}).items():
            if algo_config.get('enabled', False):
                main_config['parameters'][algo] = algo_config.get('parameters', {})
        
        # Lưu cấu hình
        with open('config.json', 'w') as f:
            json.dump(main_config, f, indent=4)
            
        logger.info("Đã cập nhật cấu hình chính")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình chính: {e}")
        logger.error(traceback.format_exc())
        return False

def check_api_keys() -> bool:
    """
    Kiểm tra API keys cho Binance
    
    Returns:
        bool: True nếu đã có API keys
    """
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        logger.warning("Không tìm thấy API keys cho Binance")
        return False
        
    # Thử kết nối đến Binance API
    try:
        checker = BinanceBalanceChecker(api_key, api_secret)
        balance, success = checker.get_futures_balance()
        
        if success:
            logger.info(f"Kết nối thành công đến Binance API. Số dư: ${balance:.2f}")
            return True
        else:
            logger.warning("Kết nối đến Binance API thất bại")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra API keys: {e}")
        logger.error(traceback.format_exc())
        return False

def start_bot(auto_mode: bool = False) -> bool:
    """
    Khởi động bot giao dịch
    
    Args:
        auto_mode (bool): Chế độ tự động (không hỏi xác nhận)
        
    Returns:
        bool: True nếu khởi động thành công
    """
    try:
        # Tải tất cả cấu hình
        configs = load_configs()
        
        if not configs:
            logger.error("Không thể tải cấu hình")
            return False
            
        # Kiểm tra API keys
        if not check_api_keys():
            if not auto_mode:
                logger.warning("Cần cài đặt API keys cho Binance trước khi khởi động bot")
                set_keys = input("Bạn có muốn cài đặt API keys ngay bây giờ? (y/n): ")
                
                if set_keys.lower() == 'y':
                    api_key = input("Nhập Binance API Key: ")
                    api_secret = input("Nhập Binance API Secret: ")
                    
                    # Lưu vào biến môi trường
                    os.environ['BINANCE_API_KEY'] = api_key
                    os.environ['BINANCE_API_SECRET'] = api_secret
                    
                    # Lưu vào file .env
                    with open('.env', 'a') as f:
                        f.write(f"\nBINANCE_API_KEY={api_key}\n")
                        f.write(f"BINANCE_API_SECRET={api_secret}\n")
                        
                    logger.info("Đã lưu API keys")
                else:
                    logger.warning("Không thể khởi động bot mà không có API keys")
                    return False
            else:
                logger.error("Không thể khởi động bot trong chế độ tự động mà không có API keys")
                return False
                
        # Cập nhật số dư từ Binance
        logger.info("Cập nhật số dư từ Binance...")
        update_balance_from_binance()
        
        # Cập nhật cấu hình chính
        update_main_config(load_configs())  # Tải lại cấu hình sau khi cập nhật số dư
        
        # Hiển thị thông tin trước khi khởi động
        risk_manager = RiskConfigManager()
        account_selector = AccountTypeSelector()
        algorithm_selector = TradingAlgorithmSelector()
        
        account_type = account_selector.get_current_config().get('account_type', 'futures')
        account_name = account_selector.get_effective_settings().get('name', 'Futures')
        
        risk_profile = risk_manager.get_current_config().get('risk_profile', 'medium')
        if risk_manager.get_current_config().get('custom_settings'):
            risk_profile_name = "Tùy chỉnh"
        else:
            from risk_config_manager import RISK_PROFILES
            risk_profile_name = RISK_PROFILES[risk_profile]['name']
            
        algorithm = algorithm_selector.get_current_config().get('primary_algorithm', 'combined_strategy')
        algorithm_name = algorithm_selector.get_available_algorithms().get(algorithm, {}).get('name', algorithm)
        
        initial_balance = risk_manager.get_current_config().get('initial_balance', 100.0)
        
        logger.info(f"=== CẤU HÌNH BOT ===")
        logger.info(f"Loại tài khoản: {account_name}")
        logger.info(f"Hồ sơ rủi ro: {risk_profile_name}")
        logger.info(f"Thuật toán chính: {algorithm_name}")
        logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
        
        # Xác nhận khởi động
        if not auto_mode:
            confirm = input("Xác nhận khởi động bot với cấu hình trên? (y/n): ")
            
            if confirm.lower() != 'y':
                logger.info("Đã hủy khởi động bot")
                return False
                
        # Khởi động bot
        logger.info("Khởi động bot...")
        
        # TODO: Thêm code khởi động bot thực tế ở đây
        # Ví dụ: os.system("python trading_bot.py")
        
        logger.info("Đã khởi động bot thành công!")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi khởi động bot: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Hàm chính để tích hợp và khởi động bot"""
    parser = argparse.ArgumentParser(description='Tích hợp và khởi động bot giao dịch')
    
    parser.add_argument('--auto', action='store_true', help='Chế độ tự động (không hỏi xác nhận)')
    parser.add_argument('--risk-profile', type=str, choices=['very_low', 'low', 'medium', 'high', 'very_high'],
                       help='Hồ sơ rủi ro')
    parser.add_argument('--account-type', type=str, choices=['spot', 'futures'],
                       help='Loại tài khoản')
    parser.add_argument('--algorithm', type=str,
                       help='Thuật toán giao dịch')
    parser.add_argument('--update-balance', action='store_true',
                       help='Cập nhật số dư từ Binance')
    
    args = parser.parse_args()
    
    # Cập nhật cấu hình nếu được chỉ định
    if args.risk_profile or args.account_type or args.algorithm or args.update_balance:
        # Cập nhật hồ sơ rủi ro
        if args.risk_profile:
            try:
                risk_manager = RiskConfigManager()
                if risk_manager.set_risk_profile(args.risk_profile):
                    logger.info(f"Đã đặt hồ sơ rủi ro: {args.risk_profile}")
                else:
                    logger.error(f"Không thể đặt hồ sơ rủi ro: {args.risk_profile}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt hồ sơ rủi ro: {e}")
                
        # Cập nhật loại tài khoản
        if args.account_type:
            try:
                account_selector = AccountTypeSelector()
                if account_selector.set_account_type(args.account_type):
                    logger.info(f"Đã đặt loại tài khoản: {args.account_type}")
                else:
                    logger.error(f"Không thể đặt loại tài khoản: {args.account_type}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt loại tài khoản: {e}")
                
        # Cập nhật thuật toán giao dịch
        if args.algorithm:
            try:
                algorithm_selector = TradingAlgorithmSelector()
                if algorithm_selector.set_primary_algorithm(args.algorithm):
                    logger.info(f"Đã đặt thuật toán giao dịch: {args.algorithm}")
                else:
                    logger.error(f"Không thể đặt thuật toán giao dịch: {args.algorithm}")
            except Exception as e:
                logger.error(f"Lỗi khi đặt thuật toán giao dịch: {e}")
                
        # Cập nhật số dư từ Binance
        if args.update_balance:
            if update_balance_from_binance():
                logger.info("Đã cập nhật số dư từ Binance")
            else:
                logger.error("Không thể cập nhật số dư từ Binance")
    
    # Khởi động bot
    start_bot(args.auto)

if __name__ == "__main__":
    main()