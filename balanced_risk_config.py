#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script điều chỉnh cấu hình rủi ro để cân bằng giữa lợi nhuận và an toàn

Script này sẽ tạo cấu hình rủi ro tối ưu dựa trên kết quả phân tích hiệu suất
từ các mức rủi ro khác nhau, nhưng giảm rủi ro mặc định xuống.
"""

import os
import json
import logging
import sys
import argparse
from datetime import datetime
from typing import Dict, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('balanced_risk_config.log')
    ]
)

logger = logging.getLogger('balanced_risk_config')

# Dựa trên kết quả phân tích multi-coin, các thông số hiệu suất tối ưu
OPTIMIZED_RESULTS = {
    "1d": {
        "win_rate": 60.55,
        "profit_factor": 7.53,
        "risk_adjusted_return": 8.21,
        "recommended_risk": 15.0  # Mức rủi ro khuyến nghị cho khung thời gian này
    },
    "4h": {
        "win_rate": 53.33,
        "profit_factor": 6.75,
        "risk_adjusted_return": 6.91,
        "recommended_risk": 15.0
    },
    "1h": {
        "win_rate": 49.53,
        "profit_factor": 5.62,
        "risk_adjusted_return": 5.69,
        "recommended_risk": 20.0
    },
    "15m": {
        "win_rate": 48.5,
        "profit_factor": 4.8,
        "risk_adjusted_return": 4.9,
        "recommended_risk": 20.0
    }
}

# Mức rủi ro tối ưu cho từng kích thước tài khoản, từ kết quả phân tích
OPTIMAL_RISK_BY_ACCOUNT_SIZE = {
    "small": {  # $100-$200
        "1d": 10.0,
        "4h": 10.0,
        "1h": 10.0,
        "15m": 10.0
    },
    "medium": {  # $200-$500
        "1d": 15.0,
        "4h": 15.0,
        "1h": 15.0,
        "15m": 10.0
    },
    "large": {  # $500-$1000
        "1d": 15.0,
        "4h": 20.0,
        "1h": 20.0,
        "15m": 15.0
    },
    "xlarge": {  # >$1000
        "1d": 20.0,
        "4h": 20.0,
        "1h": 30.0,
        "15m": 20.0
    }
}

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

def get_balanced_risk_config(account_balance: float, timeframe: str, safety_factor: float = 0.8) -> Dict:
    """
    Tạo cấu hình rủi ro cân bằng dựa trên kích thước tài khoản và khung thời gian

    Args:
        account_balance (float): Số dư tài khoản (USD)
        timeframe (str): Khung thời gian giao dịch
        safety_factor (float): Hệ số an toàn để giảm mức rủi ro (0.8 = 80% mức rủi ro tối ưu)

    Returns:
        Dict: Cấu hình rủi ro cân bằng
    """
    # Phân loại tài khoản
    account_type = classify_account_size(account_balance)
    
    # Lấy mức rủi ro tối ưu cho tài khoản và khung thời gian
    if timeframe in OPTIMAL_RISK_BY_ACCOUNT_SIZE[account_type]:
        optimal_risk = OPTIMAL_RISK_BY_ACCOUNT_SIZE[account_type][timeframe]
    else:
        # Mặc định sử dụng khung thời gian an toàn nhất
        optimal_risk = OPTIMAL_RISK_BY_ACCOUNT_SIZE[account_type]["1d"]
        logger.warning(f"Không tìm thấy khung thời gian {timeframe}, sử dụng khung thời gian 1d")
    
    # Áp dụng hệ số an toàn
    balanced_risk = optimal_risk * safety_factor
    
    # Tính các tham số liên quan
    max_position_size = min(0.3, balanced_risk / 100 * 3)  # Tối đa 30% tài khoản
    risk_per_trade = account_balance * (balanced_risk / 100)
    
    # Thiết lập số lượng vị thế tối đa
    if account_type == "small":
        max_positions = 2
    elif account_type == "medium":
        max_positions = 3
    elif account_type == "large":
        max_positions = 5
    else:  # xlarge
        max_positions = 8
    
    # Thiết lập stop loss và take profit dựa trên thông số hiệu suất
    if timeframe in OPTIMIZED_RESULTS:
        # Tính SL/TP tối ưu theo tỷ lệ thắng và profit factor
        win_rate = OPTIMIZED_RESULTS[timeframe]["win_rate"] / 100
        profit_factor = OPTIMIZED_RESULTS[timeframe]["profit_factor"]
        
        # TP = SL * profit_factor * (win_rate / (1 - win_rate))
        base_sl = balanced_risk * 0.4  # 40% của mức rủi ro
        tp_sl_ratio = profit_factor * (win_rate / (1 - win_rate))
        base_tp = base_sl * tp_sl_ratio
        
        # Giới hạn trong khoảng hợp lý
        stop_loss_pct = min(max(base_sl, 2.0), 15.0)
        take_profit_pct = min(max(base_tp, stop_loss_pct * 2), 45.0)
    else:
        # Mặc định
        stop_loss_pct = balanced_risk * 0.4
        take_profit_pct = balanced_risk * 1.2
    
    # Tạo cấu hình cân bằng
    config = {
        "account": {
            "balance": account_balance,
            "type": account_type,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "risk_management": {
            "original_optimal_risk": optimal_risk,
            "safety_factor": safety_factor,
            "risk_level": balanced_risk,
            "max_position_size": max_position_size,
            "max_open_positions": max_positions,
            "max_daily_trades": max_positions * 2,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "risk_per_trade": risk_per_trade
        },
        "trading_preferences": {
            "timeframe": timeframe,
            "preferred_coins": get_recommended_coins(account_type),
            "preferred_timeframes": get_recommended_timeframes(account_type),
            "leverage": get_recommended_leverage(account_type, balanced_risk)
        },
        "position_sizing": {
            "max_position_amount": account_balance * max_position_size,
            "min_position_amount": max(10, account_balance * 0.05)
        },
        "performance_metrics": {
            "expected_win_rate": OPTIMIZED_RESULTS.get(timeframe, {}).get("win_rate", 50),
            "expected_profit_factor": OPTIMIZED_RESULTS.get(timeframe, {}).get("profit_factor", 2),
            "expected_risk_adjusted_return": OPTIMIZED_RESULTS.get(timeframe, {}).get("risk_adjusted_return", 3)
        }
    }
    
    return config

def get_recommended_coins(account_type: str) -> list:
    """
    Lấy danh sách coin được khuyến nghị dựa trên loại tài khoản

    Args:
        account_type (str): Loại tài khoản

    Returns:
        list: Danh sách coin khuyến nghị
    """
    base_coins = ["BTCUSDT", "ETHUSDT"]
    
    if account_type == "small":
        return base_coins
    elif account_type == "medium":
        return base_coins + ["BNBUSDT", "SOLUSDT"]
    elif account_type == "large":
        return base_coins + ["BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
    else:  # xlarge
        return base_coins + ["BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT"]

def get_recommended_timeframes(account_type: str) -> list:
    """
    Lấy danh sách khung thời gian được khuyến nghị dựa trên loại tài khoản

    Args:
        account_type (str): Loại tài khoản

    Returns:
        list: Danh sách khung thời gian khuyến nghị
    """
    if account_type == "small":
        return ["1d", "4h"]
    elif account_type == "medium":
        return ["1d", "4h", "1h"]
    elif account_type == "large":
        return ["4h", "1h", "15m"]
    else:  # xlarge
        return ["1h", "15m", "5m"]

def get_recommended_leverage(account_type: str, risk_level: float) -> int:
    """
    Lấy đòn bẩy được khuyến nghị dựa trên loại tài khoản và mức rủi ro

    Args:
        account_type (str): Loại tài khoản
        risk_level (float): Mức rủi ro

    Returns:
        int: Đòn bẩy khuyến nghị
    """
    # Đòn bẩy cơ bản theo loại tài khoản
    base_leverage = {
        "small": 2,
        "medium": 3,
        "large": 5,
        "xlarge": 5
    }.get(account_type, 2)
    
    # Điều chỉnh theo mức rủi ro
    if risk_level < 10:
        return max(1, base_leverage - 1)
    elif risk_level > 20:
        return base_leverage + 1
    else:
        return base_leverage

def create_balanced_config(account_balance: float, timeframe: str, output_file: str,
                         safety_factor: float = 0.8, apply_immediately: bool = False):
    """
    Tạo và lưu file cấu hình rủi ro cân bằng

    Args:
        account_balance (float): Số dư tài khoản (USD)
        timeframe (str): Khung thời gian giao dịch
        output_file (str): Đường dẫn file cấu hình
        safety_factor (float): Hệ số an toàn (0.8 = 80% mức rủi ro tối ưu)
        apply_immediately (bool): Áp dụng ngay làm cấu hình chính
    """
    # Tạo cấu hình
    config = get_balanced_risk_config(account_balance, timeframe, safety_factor)
    
    # Lưu cấu hình
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Đã tạo cấu hình cân bằng tại {output_file}")
    logger.info(f"Mức rủi ro ban đầu: {config['risk_management']['original_optimal_risk']}%")
    logger.info(f"Mức rủi ro cân bằng: {config['risk_management']['risk_level']}%")
    logger.info(f"Số tiền rủi ro tối đa mỗi giao dịch: ${config['risk_management']['risk_per_trade']:.2f}")
    
    # Áp dụng làm cấu hình chính nếu được yêu cầu
    if apply_immediately:
        try:
            with open('account_config.json', 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Đã áp dụng cấu hình mới làm cấu hình chính (account_config.json)")
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng cấu hình mới: {str(e)}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Tạo cấu hình rủi ro cân bằng')
    parser.add_argument('--balance', type=float, required=True, help='Số dư tài khoản (USD)')
    parser.add_argument('--timeframe', type=str, default='1d', choices=['1d', '4h', '1h', '15m', '5m'], 
                        help='Khung thời gian giao dịch')
    parser.add_argument('--output', type=str, default='balanced_risk_config.json', help='File cấu hình đầu ra')
    parser.add_argument('--safety', type=float, default=0.8, help='Hệ số an toàn (0.8 = 80% mức rủi ro tối ưu)')
    parser.add_argument('--apply', action='store_true', help='Áp dụng ngay làm cấu hình chính')
    args = parser.parse_args()
    
    # Kiểm tra số dư tài khoản hợp lệ
    if args.balance <= 0:
        logger.error("Số dư tài khoản phải lớn hơn 0")
        sys.exit(1)
    
    # Kiểm tra hệ số an toàn hợp lệ
    if args.safety <= 0 or args.safety > 1:
        logger.error("Hệ số an toàn phải nằm trong khoảng (0, 1]")
        sys.exit(1)
    
    # Tạo file cấu hình
    create_balanced_config(args.balance, args.timeframe, args.output, args.safety, args.apply)
    
    # Hiển thị thông tin
    print(f"\n===== Cấu hình rủi ro cân bằng cho tài khoản ${args.balance} =====")
    with open(args.output, 'r') as f:
        config = json.load(f)
        
        account_type = config['account']['type']
        original_risk = config['risk_management']['original_optimal_risk']
        balanced_risk = config['risk_management']['risk_level']
        risk_per_trade = config['risk_management']['risk_per_trade']
        max_positions = config['risk_management']['max_open_positions']
        stop_loss = config['risk_management']['stop_loss_pct']
        take_profit = config['risk_management']['take_profit_pct']
        preferred_coins = config['trading_preferences']['preferred_coins']
        
        print(f"Loại tài khoản: {account_type}")
        print(f"Khung thời gian: {args.timeframe}")
        print(f"Mức rủi ro tối ưu ban đầu: {original_risk}%")
        print(f"Mức rủi ro cân bằng (sau áp dụng hệ số {args.safety}): {balanced_risk:.2f}%")
        print(f"Rủi ro tối đa mỗi giao dịch: ${risk_per_trade:.2f}")
        print(f"Số vị thế mở tối đa: {max_positions}")
        print(f"Stop Loss: {stop_loss:.2f}% / Take Profit: {take_profit:.2f}%")
        print(f"Các coin được khuyến nghị: {', '.join(preferred_coins[:3])}...")
        
        if args.apply:
            print("\nCấu hình này đã được áp dụng làm cấu hình chính (account_config.json)")
        else:
            print(f"\nCấu hình chi tiết được lưu tại: {args.output}")
    
    print("\nLưu ý: Cấu hình này giảm mức rủi ro tối ưu xuống để đảm bảo an toàn và bền vững trong dài hạn.")

if __name__ == "__main__":
    main()