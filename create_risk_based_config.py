#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo file cấu hình tự động dựa trên quy mô tài khoản

Script này tạo file cấu hình giao dịch phù hợp với các mức rủi ro
được khuyến nghị cho từng quy mô tài khoản khác nhau.
"""

import os
import json
import argparse
import logging
from typing import Dict, Any
from datetime import datetime
import sys

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('risk_config_generator.log')
    ]
)

logger = logging.getLogger('risk_config_generator')

# Các mức rủi ro được khuyến nghị theo quy mô tài khoản
ACCOUNT_SIZE_RECOMMENDATIONS = {
    "small": {  # $100-$200
        "risk_level": 10.0,
        "max_position_size": 0.3,  # Tối đa 30% tài khoản cho 1 vị thế 
        "max_open_positions": 3,
        "max_daily_trades": 5,
        "stop_loss_pct": 5.0,
        "take_profit_pct": 15.0,
        "preferred_coins": ["BTCUSDT", "ETHUSDT"],
        "preferred_timeframes": ["1d", "4h"],
        "leverage": 2
    },
    "medium": {  # $200-$500
        "risk_level": 15.0,
        "max_position_size": 0.35,  # Tối đa 35% tài khoản cho 1 vị thế
        "max_open_positions": 4,
        "max_daily_trades": 8,
        "stop_loss_pct": 6.0,
        "take_profit_pct": 18.0,
        "preferred_coins": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
        "preferred_timeframes": ["4h", "1h"],
        "leverage": 3
    },
    "large": {  # $500-$1000
        "risk_level": 20.0,
        "max_position_size": 0.4,  # Tối đa 40% tài khoản cho 1 vị thế
        "max_open_positions": 5,
        "max_daily_trades": 10,
        "stop_loss_pct": 8.0,
        "take_profit_pct": 24.0,
        "preferred_coins": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"],
        "preferred_timeframes": ["1h", "15m"],
        "leverage": 5
    },
    "xlarge": {  # >$1000
        "risk_level": 30.0,
        "max_position_size": 0.3,  # Tối đa 30% tài khoản cho 1 vị thế (phân tán rủi ro)
        "max_open_positions": 8,
        "max_daily_trades": 15,
        "stop_loss_pct": 10.0,
        "take_profit_pct": 30.0,
        "preferred_coins": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT"],
        "preferred_timeframes": ["1h", "15m", "5m"],
        "leverage": 5
    }
}

# Phân loại quy mô tài khoản dựa trên số tiền
def classify_account_size(account_balance: float) -> str:
    """
    Phân loại quy mô tài khoản dựa trên số dư

    Args:
        account_balance (float): Số dư tài khoản (USD)

    Returns:
        str: Loại tài khoản (small, medium, large, xlarge)
    """
    if account_balance <= 200:
        return "small"
    elif account_balance <= 500:
        return "medium"
    elif account_balance <= 1000:
        return "large"
    else:
        return "xlarge"

def get_config_for_account_size(account_balance: float, custom_params: Dict = None) -> Dict:
    """
    Lấy cấu hình phù hợp với quy mô tài khoản

    Args:
        account_balance (float): Số dư tài khoản (USD)
        custom_params (Dict, optional): Các tham số tùy chỉnh

    Returns:
        Dict: Cấu hình giao dịch
    """
    # Phân loại quy mô tài khoản
    account_type = classify_account_size(account_balance)
    logger.info(f"Tài khoản {account_balance}$ được phân loại là: {account_type}")
    
    # Lấy cấu hình khuyến nghị
    config = ACCOUNT_SIZE_RECOMMENDATIONS[account_type].copy()
    
    # Thêm số dư tài khoản vào cấu hình
    config["account_balance"] = account_balance
    
    # Thêm ngày tạo
    config["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    config["account_type"] = account_type
    
    # Ghi đè các tham số tùy chỉnh nếu có
    if custom_params:
        for key, value in custom_params.items():
            config[key] = value
    
    # Tính toán một số giá trị dựa trên số dư
    config["max_position_amount"] = account_balance * config["max_position_size"]
    config["min_position_amount"] = max(10, account_balance * 0.05)  # Tối thiểu $10 hoặc 5% tài khoản
    
    # Tính toán số lượng giao dịch đồng thời tối đa dựa trên rủi ro
    risk_per_trade = account_balance * (config["risk_level"] / 100)
    config["risk_per_trade"] = risk_per_trade
    
    return config

def create_account_config(account_balance: float, output_file: str, custom_params: Dict = None):
    """
    Tạo và lưu file cấu hình tài khoản

    Args:
        account_balance (float): Số dư tài khoản (USD)
        output_file (str): Đường dẫn file cấu hình
        custom_params (Dict, optional): Các tham số tùy chỉnh
    """
    # Lấy cấu hình
    config = get_config_for_account_size(account_balance, custom_params)
    
    # Tạo file cấu hình cơ bản
    basic_config = {
        "account": {
            "balance": account_balance,
            "type": config["account_type"],
            "created_at": config["created_at"]
        },
        "risk_management": {
            "risk_level": config["risk_level"],
            "max_position_size": config["max_position_size"],
            "max_open_positions": config["max_open_positions"],
            "max_daily_trades": config["max_daily_trades"],
            "stop_loss_pct": config["stop_loss_pct"],
            "take_profit_pct": config["take_profit_pct"],
            "risk_per_trade": config["risk_per_trade"]
        },
        "trading_preferences": {
            "preferred_coins": config["preferred_coins"],
            "preferred_timeframes": config["preferred_timeframes"],
            "leverage": config["leverage"]
        },
        "position_sizing": {
            "max_position_amount": config["max_position_amount"],
            "min_position_amount": config["min_position_amount"]
        }
    }
    
    # Lưu cấu hình
    with open(output_file, 'w') as f:
        json.dump(basic_config, f, indent=2)
    
    logger.info(f"Đã tạo file cấu hình tại {output_file}")
    logger.info(f"Mức rủi ro được đề xuất: {config['risk_level']}%")
    logger.info(f"Số tiền rủi ro tối đa mỗi giao dịch: ${config['risk_per_trade']:.2f}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Tạo file cấu hình dựa trên quy mô tài khoản')
    parser.add_argument('--balance', type=float, required=True, help='Số dư tài khoản (USD)')
    parser.add_argument('--output', type=str, default='account_risk_config.json', help='File cấu hình đầu ra')
    parser.add_argument('--risk_level', type=float, help='Ghi đè mức rủi ro (%)')
    parser.add_argument('--max_position_size', type=float, help='Ghi đè kích thước vị thế tối đa (tỷ lệ, ví dụ: 0.3 cho 30%)')
    parser.add_argument('--leverage', type=int, help='Ghi đè đòn bẩy')
    args = parser.parse_args()
    
    # Kiểm tra số dư tài khoản hợp lệ
    if args.balance <= 0:
        logger.error("Số dư tài khoản phải lớn hơn 0")
        sys.exit(1)
    
    # Tham số tùy chỉnh
    custom_params = {}
    if args.risk_level is not None:
        custom_params["risk_level"] = args.risk_level
    if args.max_position_size is not None:
        custom_params["max_position_size"] = args.max_position_size
    if args.leverage is not None:
        custom_params["leverage"] = args.leverage
    
    # Tạo file cấu hình
    create_account_config(args.balance, args.output, custom_params)
    
    print(f"\n===== Cấu hình tài khoản ${args.balance} =====")
    with open(args.output, 'r') as f:
        config = json.load(f)
        account_type = config['account']['type']
        risk_level = config['risk_management']['risk_level']
        risk_per_trade = config['risk_management']['risk_per_trade']
        max_positions = config['risk_management']['max_open_positions']
        preferred_coins = config['trading_preferences']['preferred_coins']
        
        print(f"Loại tài khoản: {account_type}")
        print(f"Mức rủi ro: {risk_level}%")
        print(f"Rủi ro tối đa mỗi giao dịch: ${risk_per_trade:.2f}")
        print(f"Số vị thế mở tối đa: {max_positions}")
        print(f"Các coin được khuyến nghị: {', '.join(preferred_coins[:3])}...")
        print(f"Cấu hình chi tiết được lưu tại: {args.output}")
    
    print("\nLưu ý: Cấu hình này chỉ là khuyến nghị dựa trên nghiên cứu. Vui lòng điều chỉnh phù hợp với chiến lược và mức chịu rủi ro cá nhân của bạn.")

if __name__ == "__main__":
    main()