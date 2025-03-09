#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tối ưu hóa chiến lược cho tài khoản trung bình ($300-$600)

Script này tạo cấu hình giao dịch tối ưu cho tài khoản $300-$600,
tập trung vào việc tối đa hóa số lượng giao dịch và lựa chọn khung
thời gian có tỷ lệ thắng cao nhất.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any
import random

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('medium_account.log')
    ]
)

logger = logging.getLogger('medium_account_optimizer')

# Dữ liệu về khung thời gian và tỷ lệ thắng (từ phân tích trước đó)
TIMEFRAME_WIN_RATES = {
    "1d": 54.72,
    "4h": 52.72,
    "1h": 50.72,
    "15m": 49.50,  # Ước tính
    "5m": 47.50    # Ước tính
}

# Top coin theo hiệu suất (từ phân tích trước đó)
TOP_COINS = [
    {"symbol": "BTCUSDT", "win_rate": 59.50, "best_timeframe": "1d", "volatility": 0.8},
    {"symbol": "ETHUSDT", "win_rate": 57.50, "best_timeframe": "1d", "volatility": 0.9},
    {"symbol": "BNBUSDT", "win_rate": 53.50, "best_timeframe": "4h", "volatility": 1.0},
    {"symbol": "SOLUSDT", "win_rate": 54.50, "best_timeframe": "1d", "volatility": 1.2},
    {"symbol": "LINKUSDT", "win_rate": 53.50, "best_timeframe": "1d", "volatility": 1.1},
    {"symbol": "LTCUSDT", "win_rate": 51.50, "best_timeframe": "1d", "volatility": 0.9},
    {"symbol": "ATOMUSDT", "win_rate": 50.50, "best_timeframe": "4h", "volatility": 1.3},
    {"symbol": "AVAXUSDT", "win_rate": 51.50, "best_timeframe": "4h", "volatility": 1.3}
]

# Mức rủi ro theo quy mô tài khoản (từ phân tích trước đó)
ACCOUNT_SIZE_RISK = {
    "small": {  # $100-$200
        "risk_level": 10.0,
        "max_position_size": 0.3,
        "max_positions": 3
    },
    "medium": {  # $200-$500
        "risk_level": 15.0,
        "max_position_size": 0.35,
        "max_positions": 4
    },
    "large": {  # $500-$1000
        "risk_level": 20.0,
        "max_position_size": 0.4,
        "max_positions": 5
    },
    "xlarge": {  # >$1000
        "risk_level": 30.0,
        "max_position_size": 0.3,
        "max_positions": 8
    }
}

# Tham số tối ưu cho tài khoản $300-$600
MEDIUM_ACCOUNT_OPTIMIZED = {
    "risk_level": 18.0,  # 18% rủi ro (giữa medium và large)
    "max_position_size": 0.35,  # Tối đa 35% tài khoản cho 1 vị thế
    "max_positions": 5,  # Tối đa 5 vị thế cùng lúc
    "max_daily_trades": 10,  # Tối đa 10 giao dịch mỗi ngày
    "recommended_timeframes": ["1d", "4h"],  # Khung thời gian khuyến nghị
    "stop_loss_pct": 7.0,  # 7% stop loss
    "take_profit_pct": 21.0,  # 21% take profit (tỷ lệ 1:3)
    "position_sizing_strategy": "Kelly",  # Chiến lược phân bổ vốn
    "order_types": ["limit", "market"],  # Loại lệnh sử dụng
    "portfolio_allocation": {
        "high_win_rate": 0.6,  # 60% vốn cho coin có win rate cao
        "medium_win_rate": 0.3,  # 30% vốn cho coin có win rate trung bình
        "speculative": 0.1  # 10% vốn cho coin có tiềm năng cao nhưng rủi ro lớn
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

def optimize_timeframes(account_balance: float) -> Dict[str, float]:
    """
    Tối ưu hóa phân bổ cho từng khung thời gian dựa trên quy mô tài khoản

    Args:
        account_balance (float): Số dư tài khoản (USD)

    Returns:
        Dict[str, float]: Tỷ lệ phân bổ cho từng khung thời gian
    """
    account_type = classify_account_size(account_balance)
    
    # Phân bổ khung thời gian theo loại tài khoản
    if account_type == "small":
        # Tài khoản nhỏ: tập trung vào khung thời gian dài, ít giao dịch
        return {
            "1d": 0.7,  # 70% tài khoản cho khung 1d
            "4h": 0.3,  # 30% tài khoản cho khung 4h
            "1h": 0.0,
            "15m": 0.0,
            "5m": 0.0
        }
    elif account_type == "medium":
        # Tài khoản trung bình: chủ yếu là 4h và 1d, một ít 1h
        return {
            "1d": 0.4,  # 40% tài khoản cho khung 1d
            "4h": 0.4,  # 40% tài khoản cho khung 4h
            "1h": 0.2,  # 20% tài khoản cho khung 1h
            "15m": 0.0,
            "5m": 0.0
        }
    elif account_type == "large":
        # Tài khoản lớn: đa dạng khung thời gian
        return {
            "1d": 0.3,
            "4h": 0.3,
            "1h": 0.3,
            "15m": 0.1,
            "5m": 0.0
        }
    else:  # xlarge
        # Tài khoản rất lớn: đa dạng tất cả các khung thời gian
        return {
            "1d": 0.2,
            "4h": 0.3,
            "1h": 0.3,
            "15m": 0.15,
            "5m": 0.05
        }

def optimize_coins(account_balance: float) -> List[Dict]:
    """
    Tối ưu hóa lựa chọn coin dựa trên quy mô tài khoản

    Args:
        account_balance (float): Số dư tài khoản (USD)

    Returns:
        List[Dict]: Danh sách coin được khuyến nghị
    """
    account_type = classify_account_size(account_balance)
    
    # Sắp xếp coin theo tỷ lệ thắng
    coins_by_win_rate = sorted(TOP_COINS, key=lambda x: x["win_rate"], reverse=True)
    
    # Lấy số lượng coin phù hợp với quy mô tài khoản
    if account_type == "small":
        selected_coins = coins_by_win_rate[:3]  # 3 coin tốt nhất
    elif account_type == "medium":
        selected_coins = coins_by_win_rate[:5]  # 5 coin tốt nhất
    elif account_type == "large":
        selected_coins = coins_by_win_rate[:7]  # 7 coin tốt nhất
    else:  # xlarge
        selected_coins = coins_by_win_rate  # Tất cả coin
    
    return selected_coins

def calculate_optimal_trade_size(account_balance: float, risk_level: float, 
                               win_rate: float, reward_risk_ratio: float) -> float:
    """
    Tính toán kích thước giao dịch tối ưu sử dụng công thức Kelly

    Args:
        account_balance (float): Số dư tài khoản (USD)
        risk_level (float): Mức rủi ro phần trăm
        win_rate (float): Tỷ lệ thắng (%)
        reward_risk_ratio (float): Tỷ lệ TP:SL

    Returns:
        float: Kích thước giao dịch tối ưu (USD)
    """
    # Chuyển đổi phần trăm sang thập phân
    win_rate = win_rate / 100.0
    
    # Tính toán phần trăm Kelly
    kelly_pct = win_rate - ((1 - win_rate) / reward_risk_ratio)
    
    # Giới hạn kết quả
    kelly_pct = max(0.01, min(kelly_pct, 0.5))  # Giới hạn từ 1% đến 50%
    
    # Áp dụng mức rủi ro
    adjusted_kelly = kelly_pct * (risk_level / 100.0) * 2  # Điều chỉnh theo mức rủi ro
    
    # Tính toán kích thước giao dịch
    trade_size = account_balance * adjusted_kelly
    
    return trade_size

def generate_trading_plan(account_balance: float) -> Dict:
    """
    Tạo kế hoạch giao dịch tối ưu cho tài khoản

    Args:
        account_balance (float): Số dư tài khoản (USD)

    Returns:
        Dict: Kế hoạch giao dịch
    """
    # Phân loại quy mô tài khoản
    account_type = classify_account_size(account_balance)
    
    # Lấy thông số cơ bản cho loại tài khoản
    base_params = ACCOUNT_SIZE_RISK[account_type].copy()
    
    # Điều chỉnh thông số cho tài khoản $300-$600
    if 300 <= account_balance <= 600:
        base_params.update(MEDIUM_ACCOUNT_OPTIMIZED)
    
    # Tối ưu hóa khung thời gian
    timeframe_allocation = optimize_timeframes(account_balance)
    
    # Tối ưu hóa lựa chọn coin
    recommended_coins = optimize_coins(account_balance)
    
    # Tính toán TP:SL ratio
    tp_sl_ratio = base_params.get("take_profit_pct", 21.0) / base_params.get("stop_loss_pct", 7.0)
    
    # Tính toán kích thước giao dịch cho từng coin
    trading_sizes = {}
    for coin in recommended_coins:
        symbol = coin["symbol"]
        win_rate = coin["win_rate"]
        optimal_size = calculate_optimal_trade_size(
            account_balance, 
            base_params["risk_level"], 
            win_rate, 
            tp_sl_ratio
        )
        trading_sizes[symbol] = optimal_size
    
    # Tạo kế hoạch giao dịch
    trading_plan = {
        "account": {
            "balance": account_balance,
            "type": account_type,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "risk_management": {
            "risk_level": base_params["risk_level"],
            "max_position_size": base_params["max_position_size"],
            "max_positions": base_params.get("max_positions", 4),
            "stop_loss_pct": base_params.get("stop_loss_pct", 7.0),
            "take_profit_pct": base_params.get("take_profit_pct", 21.0),
            "reward_risk_ratio": tp_sl_ratio
        },
        "timeframe_allocation": timeframe_allocation,
        "recommended_coins": [coin["symbol"] for coin in recommended_coins],
        "trading_sizes": trading_sizes,
        "trading_rules": {
            "max_daily_trades": base_params.get("max_daily_trades", 8),
            "minimum_win_rate_threshold": 52.0,  # Chỉ giao dịch nếu win rate dự đoán > 52%
            "maximum_concurrent_trades": min(base_params.get("max_positions", 4), len(recommended_coins)),
            "maximum_correlated_trades": 2  # Tối đa 2 giao dịch cùng xu hướng
        },
        "optimization_notes": [
            "Tối ưu hóa cho tài khoản $300-$600",
            "Tập trung vào khung thời gian có win rate cao (1d, 4h)",
            "Ưu tiên coin có tỷ lệ thắng cao",
            "Sử dụng công thức Kelly để tính kích thước giao dịch tối ưu",
            "Phân bổ vốn theo tỷ lệ thắng của từng khung thời gian"
        ]
    }
    
    return trading_plan

def generate_markdown_report(trading_plan: Dict, output_file: str = "medium_account_trading_plan.md"):
    """
    Tạo báo cáo markdown từ kế hoạch giao dịch

    Args:
        trading_plan (Dict): Kế hoạch giao dịch
        output_file (str): File đầu ra cho báo cáo
    """
    # Tạo nội dung báo cáo
    report = f"""# Kế Hoạch Giao Dịch Tối Ưu Cho Tài Khoản ${trading_plan['account']['balance']}

*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Tổng Quan

Đây là kế hoạch giao dịch được tối ưu hóa cho tài khoản ${trading_plan['account']['balance']}, tập trung vào việc tối đa hóa số lượng giao dịch thắng và lựa chọn khung thời gian có tỷ lệ thắng cao nhất.

## Quản Lý Rủi Ro

| Thông Số | Giá Trị |
|----------|---------|
| Mức rủi ro | {trading_plan['risk_management']['risk_level']}% |
| Kích thước vị thế tối đa | {trading_plan['risk_management']['max_position_size'] * 100}% tài khoản |
| Số vị thế tối đa | {trading_plan['risk_management']['max_positions']} |
| Stop Loss | {trading_plan['risk_management']['stop_loss_pct']}% |
| Take Profit | {trading_plan['risk_management']['take_profit_pct']}% |
| Tỷ lệ TP:SL | {trading_plan['risk_management']['reward_risk_ratio']:.2f} |

## Phân Bổ Khung Thời Gian

| Khung Thời Gian | Phân Bổ | Win Rate (%) |
|-----------------|---------|--------------|
"""
    
    # Thêm dữ liệu phân bổ khung thời gian
    for tf, allocation in trading_plan["timeframe_allocation"].items():
        if allocation > 0:
            report += f"| {tf} | {allocation*100:.0f}% | {TIMEFRAME_WIN_RATES.get(tf, 50):.2f}% |\n"
    
    # Thêm phần coin được khuyến nghị
    report += """
## Coin Được Khuyến Nghị

| Coin | Kích Thước Giao Dịch | Win Rate (%) | Khung Thời Gian Tốt Nhất |
|------|----------------------|--------------|---------------------------|
"""
    
    # Thêm dữ liệu coin
    for coin in TOP_COINS:
        if coin["symbol"] in trading_plan["recommended_coins"]:
            report += f"| {coin['symbol']} | ${trading_plan['trading_sizes'][coin['symbol']]:.2f} | {coin['win_rate']:.2f}% | {coin['best_timeframe']} |\n"
    
    # Thêm phần quy tắc giao dịch
    report += """
## Quy Tắc Giao Dịch

| Quy Tắc | Giá Trị |
|---------|---------|
"""
    
    # Thêm dữ liệu quy tắc
    for rule, value in trading_plan["trading_rules"].items():
        rule_text = rule.replace("_", " ").title()
        report += f"| {rule_text} | {value} |\n"
    
    # Thêm phần ghi chú và khuyến nghị
    report += """
## Ghi Chú và Khuyến Nghị

"""
    
    # Thêm các ghi chú
    for i, note in enumerate(trading_plan["optimization_notes"], 1):
        report += f"{i}. {note}\n"
    
    # Thêm khuyến nghị cụ thể cho tài khoản $300-$600
    report += """
## Khuyến Nghị Cụ Thể Cho Tài Khoản $300-$600

1. **Tập trung vào khung thời gian 1d và 4h**: Những khung thời gian này có tỷ lệ thắng cao nhất và ít đòi hỏi thời gian theo dõi.
2. **Chỉ giao dịch 5 coin tốt nhất**: Tập trung vào BTC, ETH và các altcoin có tỷ lệ thắng cao nhất.
3. **Tuân thủ nghiêm ngặt quy tắc quản lý vốn**: Không vượt quá số vị thế tối đa và kích thước vị thế tối đa.
4. **Sử dụng lệnh Limit thay vì Market**: Để có giá tốt hơn và tránh trượt giá.
5. **Đặt cảnh báo giá thay vì theo dõi liên tục**: Thiết lập cảnh báo giá để không phải theo dõi thị trường liên tục.
6. **Ưu tiên giao dịch theo xu hướng**: Chỉ giao dịch theo xu hướng chính của thị trường.
7. **Duy trì ít nhất 20% tiền mặt**: Luôn duy trì ít nhất 20% tài khoản dưới dạng tiền mặt để có thể tận dụng cơ hội mới.

## Kết Luận

Kế hoạch giao dịch này được thiết kế đặc biệt cho tài khoản ${trading_plan['account']['balance']}, tập trung vào việc tối đa hóa tỷ lệ thắng và kiểm soát rủi ro. Bằng cách tuân thủ các khuyến nghị trên, bạn có thể cải thiện hiệu suất giao dịch và đạt được mục tiêu tăng trưởng tài khoản bền vững.
"""
    
    # Lưu báo cáo
    with open(output_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Đã tạo báo cáo markdown tại {output_file}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Tạo kế hoạch giao dịch tối ưu cho tài khoản $300-$600')
    parser.add_argument('--balance', type=float, default=450.0, help='Số dư tài khoản (USD)')
    parser.add_argument('--output', type=str, default='medium_account_config.json', help='File cấu hình đầu ra')
    parser.add_argument('--report', type=str, default='medium_account_trading_plan.md', help='File báo cáo đầu ra')
    args = parser.parse_args()
    
    # Kiểm tra số dư tài khoản hợp lệ
    if args.balance <= 0:
        logger.error("Số dư tài khoản phải lớn hơn 0")
        sys.exit(1)
    
    # Tạo kế hoạch giao dịch
    trading_plan = generate_trading_plan(args.balance)
    
    # Lưu kế hoạch giao dịch
    with open(args.output, 'w') as f:
        json.dump(trading_plan, f, indent=2)
    
    logger.info(f"Đã lưu kế hoạch giao dịch vào {args.output}")
    
    # Tạo báo cáo markdown
    generate_markdown_report(trading_plan, args.report)
    
    # Hiển thị thông tin
    print(f"\n===== Kế hoạch giao dịch tối ưu cho tài khoản ${args.balance} =====")
    print(f"Mức rủi ro: {trading_plan['risk_management']['risk_level']}%")
    print(f"Stop Loss: {trading_plan['risk_management']['stop_loss_pct']}%")
    print(f"Take Profit: {trading_plan['risk_management']['take_profit_pct']}%")
    print(f"Tỷ lệ TP:SL: {trading_plan['risk_management']['reward_risk_ratio']:.2f}")
    print(f"Số vị thế tối đa: {trading_plan['risk_management']['max_positions']}")
    print("\nKhung thời gian được khuyến nghị:")
    for tf, allocation in trading_plan["timeframe_allocation"].items():
        if allocation > 0:
            print(f"- {tf}: {allocation*100:.0f}% (Win rate: {TIMEFRAME_WIN_RATES.get(tf, 50):.2f}%)")
    
    print("\nTop coin được khuyến nghị:")
    for i, symbol in enumerate(trading_plan["recommended_coins"][:5], 1):
        coin_data = next((c for c in TOP_COINS if c["symbol"] == symbol), None)
        if coin_data:
            print(f"{i}. {symbol} - Win rate: {coin_data['win_rate']}% - Khung thời gian tốt nhất: {coin_data['best_timeframe']}")
    
    print(f"\nCấu hình chi tiết được lưu tại: {args.output}")
    print(f"Báo cáo chi tiết được lưu tại: {args.report}")

if __name__ == "__main__":
    main()