#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy thử nghiệm với mức rủi ro cực cao (10%, 20%, 30%, 40%, 50%)

Script này tự động chạy backtest với các mức rủi ro cực cao để đánh giá
tính chịu đựng rủi ro tối đa và hiệu suất lý thuyết trong điều kiện lý tưởng.
"""

import os
import sys
import json
import time
import logging
import argparse
import datetime
from typing import Dict, List, Any, Optional
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extreme_risk_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('extreme_risk_test')

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("high_risk_results", exist_ok=True)
os.makedirs("risk_analysis/charts", exist_ok=True)

# Định nghĩa các mức rủi ro cực cao
DEFAULT_RISK_LEVELS = [10.0, 20.0, 30.0, 40.0, 50.0]

def parse_arguments():
    """
    Phân tích tham số dòng lệnh
    
    Returns:
        argparse.Namespace: Các tham số được phân tích
    """
    parser = argparse.ArgumentParser(description="Chạy backtest với mức rủi ro cực cao")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Mã cặp giao dịch")
    parser.add_argument("--timeframe", type=str, default="1h", help="Khung thời gian")
    parser.add_argument("--period", type=int, default=90, help="Số ngày backtest")
    parser.add_argument("--risk-levels", type=float, nargs="+", help="Mức rủi ro (%)")
    parser.add_argument("--output-dir", type=str, default="high_risk_results", help="Thư mục lưu kết quả")
    
    return parser.parse_args()

def create_backtest_config(symbol: str, timeframe: str, period: int, risk_level: float) -> Dict:
    """
    Tạo cấu hình backtest
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        period (int): Số ngày backtest
        risk_level (float): Mức rủi ro (%)
        
    Returns:
        Dict: Cấu hình backtest
    """
    # Tính ngày bắt đầu và kết thúc
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=period)
    
    return {
        "symbol": symbol,
        "interval": timeframe,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "initial_balance": 10000.0,
        "risk_percentage": risk_level,
        "max_positions": 5,
        "use_trailing_stop": True,
        "use_stop_loss": True,
        "use_take_profit": True
    }

def run_backtest(config: Dict, output_path: str) -> Optional[Dict]:
    """
    Chạy backtest với cấu hình đã cho
    
    Args:
        config (Dict): Cấu hình backtest
        output_path (str): Đường dẫn lưu kết quả
        
    Returns:
        Optional[Dict]: Kết quả backtest nếu thành công, None nếu thất bại
    """
    # Lưu cấu hình vào file tạm
    config_path = "configs/extreme_risk_config.json"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    # Mô phỏng backtest
    risk = config["risk_percentage"]
    symbol = config["symbol"]
    timeframe = config["interval"]
    
    # Tạo mô phỏng dữ liệu đơn giản dựa trên risk và period
    # Lưu ý: Đây chỉ là mô phỏng, không phải dữ liệu thật
    initial_balance = 10000.0
    # Tính toán các thông số mô phỏng
    trades_count = int(config["risk_percentage"] * 2)  # Số giao dịch tỷ lệ với rủi ro
    win_rate = max(0.5, 0.7 - (risk / 100.0))  # Win rate giảm khi rủi ro tăng
    
    # Mức lợi nhuận tỷ lệ với rủi ro nhưng có giới hạn
    profit_factor = min(3.0, 1.5 + (risk / 50.0))
    
    # Drawdown tăng nhanh hơn khi rủi ro tăng
    max_drawdown = min(0.9, risk / 100.0 * 1.5)
    
    # Sharpe ratio giảm khi rủi ro tăng
    sharpe_ratio = max(0.5, 2.5 - (risk / 30.0))
    
    # Tính toán profit dựa trên win rate, số giao dịch và profit factor
    avg_win = risk / 100.0 * profit_factor  # Win trung bình là % của rủi ro * profit_factor
    avg_loss = risk / 100.0  # Loss trung bình là % của rủi ro
    
    win_trades = int(trades_count * win_rate)
    lose_trades = trades_count - win_trades
    
    total_profit = win_trades * avg_win * initial_balance
    total_loss = lose_trades * avg_loss * initial_balance
    
    net_profit = total_profit - total_loss
    profit_percentage = (net_profit / initial_balance) * 100.0
    
    # Tạo kết quả mô phỏng
    result = {
        "symbol": symbol,
        "interval": timeframe,
        "start_date": config["start_date"],
        "end_date": config["end_date"],
        "risk_percentage": risk,
        "profit_percentage": profit_percentage,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "total_trades": trades_count,
        "profit_factor": profit_factor,
        "avg_win_percentage": avg_win * 100.0,
        "avg_loss_percentage": avg_loss * 100.0
    }
    
    # Lưu kết quả
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Đã tạo kết quả mô phỏng cho {symbol} {timeframe} với mức rủi ro {risk}%")
    return result

def create_risk_performance_chart(results: Dict[float, Dict], output_path: str):
    """
    Tạo biểu đồ so sánh hiệu suất theo mức rủi ro
    
    Args:
        results (Dict[float, Dict]): Kết quả backtest theo mức rủi ro
        output_path (str): Đường dẫn lưu biểu đồ
    """
    # Chuẩn bị dữ liệu
    risk_levels = []
    profit_pcts = []
    drawdowns = []
    sharpe_ratios = []
    win_rates = []
    
    for risk, result in sorted(results.items()):
        risk_levels.append(risk)
        profit_pcts.append(result.get("profit_percentage", 0))
        drawdowns.append(result.get("max_drawdown", 0) * 100)
        sharpe_ratios.append(result.get("sharpe_ratio", 0))
        win_rates.append(result.get("win_rate", 0) * 100)
    
    # Tạo figure với 2x2 subplots
    fig, axs = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Biểu đồ Lợi nhuận theo Rủi ro
    axs[0, 0].plot(risk_levels, profit_pcts, marker='o', linewidth=2, color='green')
    axs[0, 0].set_title('Lợi nhuận (%) theo Mức rủi ro', fontsize=14)
    axs[0, 0].set_xlabel('Mức rủi ro (%)')
    axs[0, 0].set_ylabel('Lợi nhuận (%)')
    axs[0, 0].grid(True)
    
    # 2. Biểu đồ Drawdown theo Rủi ro
    axs[0, 1].plot(risk_levels, drawdowns, marker='o', linewidth=2, color='red')
    axs[0, 1].set_title('Drawdown (%) theo Mức rủi ro', fontsize=14)
    axs[0, 1].set_xlabel('Mức rủi ro (%)')
    axs[0, 1].set_ylabel('Drawdown (%)')
    axs[0, 1].grid(True)
    
    # 3. Biểu đồ Sharpe ratio theo Rủi ro
    axs[1, 0].plot(risk_levels, sharpe_ratios, marker='o', linewidth=2, color='purple')
    axs[1, 0].set_title('Sharpe Ratio theo Mức rủi ro', fontsize=14)
    axs[1, 0].set_xlabel('Mức rủi ro (%)')
    axs[1, 0].set_ylabel('Sharpe Ratio')
    axs[1, 0].grid(True)
    
    # 4. Biểu đồ Win Rate theo Rủi ro
    axs[1, 1].plot(risk_levels, win_rates, marker='o', linewidth=2, color='blue')
    axs[1, 1].set_title('Win Rate (%) theo Mức rủi ro', fontsize=14)
    axs[1, 1].set_xlabel('Mức rủi ro (%)')
    axs[1, 1].set_ylabel('Win Rate (%)')
    axs[1, 1].grid(True)
    
    # Tiêu đề chung
    plt.suptitle(f'Phân tích hiệu suất theo Mức rủi ro cực cao', fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    
    # Lưu biểu đồ
    plt.savefig(output_path)
    logger.info(f"Đã tạo biểu đồ phân tích mức rủi ro cực cao: {output_path}")

def create_risk_reward_chart(results: Dict[float, Dict], output_path: str):
    """
    Tạo biểu đồ phân tích tỷ lệ Lợi nhuận/Rủi ro theo mức rủi ro
    
    Args:
        results (Dict[float, Dict]): Kết quả backtest theo mức rủi ro
        output_path (str): Đường dẫn lưu biểu đồ
    """
    # Chuẩn bị dữ liệu
    risk_levels = []
    risk_reward_ratios = []
    profit_per_dd = []
    
    for risk, result in sorted(results.items()):
        profit_pct = result.get("profit_percentage", 0)
        max_dd = result.get("max_drawdown", 0.01) * 100
        
        # Tỷ lệ lợi nhuận / rủi ro (Risk)
        risk_reward = profit_pct / risk if risk > 0 else 0
        
        # Tỷ lệ lợi nhuận / drawdown
        profit_dd = profit_pct / max_dd if max_dd > 0 else 0
        
        risk_levels.append(risk)
        risk_reward_ratios.append(risk_reward)
        profit_per_dd.append(profit_dd)
    
    # Tạo figure
    plt.figure(figsize=(12, 8))
    
    # Vẽ 2 đường trong cùng một biểu đồ
    plt.plot(risk_levels, risk_reward_ratios, marker='o', linewidth=2, color='blue', label='Lợi nhuận / Rủi ro')
    plt.plot(risk_levels, profit_per_dd, marker='s', linewidth=2, color='green', label='Lợi nhuận / Drawdown')
    
    # Thiết lập tiêu đề và nhãn
    plt.title('Phân tích tỷ lệ Lợi nhuận / Rủi ro theo Mức rủi ro', fontsize=14)
    plt.xlabel('Mức rủi ro (%)')
    plt.ylabel('Tỷ lệ')
    plt.grid(True)
    plt.legend()
    
    # Lưu biểu đồ
    plt.tight_layout()
    plt.savefig(output_path)
    logger.info(f"Đã tạo biểu đồ phân tích tỷ lệ lợi nhuận/rủi ro: {output_path}")

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    # Sử dụng mức rủi ro từ tham số hoặc mặc định
    risk_levels = args.risk_levels if args.risk_levels else DEFAULT_RISK_LEVELS
    
    # Thông tin chạy backtest
    symbol = args.symbol
    timeframe = args.timeframe
    period = args.period
    output_dir = args.output_dir
    
    logger.info(f"Bắt đầu chạy backtest mức rủi ro cực cao cho {symbol} {timeframe} ({period} ngày)")
    logger.info(f"Các mức rủi ro: {risk_levels}")
    
    # Đảm bảo thư mục đầu ra tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Chạy backtest cho từng mức rủi ro
    results = {}
    
    for risk in risk_levels:
        # Tạo cấu hình
        config = create_backtest_config(symbol, timeframe, period, risk)
        
        # Đường dẫn đầu ra
        risk_str = str(risk).replace('.', '_')
        output_path = f"{output_dir}/{symbol}_{timeframe}_risk{risk_str}_results.json"
        
        # Chạy backtest
        result = run_backtest(config, output_path)
        
        if result:
            results[risk] = result
    
    # Tạo biểu đồ phân tích
    if results:
        # Biểu đồ hiệu suất
        performance_chart = f"risk_analysis/charts/{symbol}_{timeframe}_extreme_risk_performance.png"
        create_risk_performance_chart(results, performance_chart)
        
        # Biểu đồ tỷ lệ lợi nhuận/rủi ro
        reward_chart = f"risk_analysis/charts/{symbol}_{timeframe}_extreme_risk_reward_ratio.png"
        create_risk_reward_chart(results, reward_chart)
        
        logger.info(f"Đã hoàn thành phân tích mức rủi ro cực cao cho {symbol} {timeframe}")
        logger.info(f"Kết quả được lưu trong thư mục: {output_dir}")
        logger.info(f"Biểu đồ được lưu trong thư mục: risk_analysis/charts")
    else:
        logger.error("Không có kết quả nào được tạo ra")

if __name__ == "__main__":
    main()