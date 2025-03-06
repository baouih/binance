#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy thử nghiệm thực tế 3 tháng trên tất cả các cặp tiền

Script này tự động chạy backtest cho tất cả các cặp tiền trong tài khoản
với dữ liệu 3 tháng gần nhất và tổng hợp kết quả.
"""

import os
import sys
import json
import time
import logging
import argparse
import datetime
from typing import Dict, List
import subprocess
import pandas as pd
import matplotlib.pyplot as plt

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('3month_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('3month_test')

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)
os.makedirs("backtest_summary", exist_ok=True)

def load_account_config() -> Dict:
    """
    Tải cấu hình tài khoản
    
    Returns:
        Dict: Cấu hình tài khoản
    """
    try:
        with open('account_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải account_config.json: {str(e)}")
        return {}

def run_backtest_for_symbol(symbol: str, interval: str = '1h', adaptive_risk: bool = True) -> Dict:
    """
    Chạy backtest cho một cặp tiền
    
    Args:
        symbol (str): Mã cặp tiền
        interval (str): Khung thời gian
        adaptive_risk (bool): Sử dụng rủi ro thích ứng hay không
        
    Returns:
        Dict: Kết quả backtest
    """
    logger.info(f"Chạy backtest cho {symbol} {interval}...")
    
    try:
        # Tạo lệnh chạy backtest
        cmd = ["python", "enhanced_backtest.py", "--symbol", symbol, "--interval", interval]
        if adaptive_risk:
            cmd.append("--adaptive_risk")
            
        # Chạy lệnh và lấy output
        subprocess.run(cmd, check=True)
        
        # Đọc kết quả từ file
        result_file = f"backtest_results/{symbol}_{interval}_adaptive_results.json"
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                return json.load(f)
        else:
            logger.error(f"Không tìm thấy file kết quả: {result_file}")
            return {}
            
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest cho {symbol}: {str(e)}")
        return {}

def generate_summary_report(results: Dict[str, Dict]) -> Dict:
    """
    Tạo báo cáo tổng hợp từ kết quả backtest
    
    Args:
        results (Dict[str, Dict]): Kết quả backtest theo cặp tiền
        
    Returns:
        Dict: Báo cáo tổng hợp
    """
    if not results:
        return {}
        
    summary = {
        "total_symbols": len(results),
        "profitable_symbols": 0,
        "avg_win_rate": 0,
        "avg_profit_factor": 0,
        "total_trades": 0,
        "win_trades": 0,
        "lose_trades": 0,
        "overall_win_rate": 0,
        "avg_profit_pct": 0,
        "max_profit_pct": 0,
        "min_profit_pct": 0,
        "best_symbol": "",
        "worst_symbol": "",
        "symbols_performance": {},
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Tính toán các chỉ số tổng hợp
    max_profit = -float('inf')
    min_profit = float('inf')
    total_profit_pct = 0
    total_win_rate = 0
    total_profit_factor = 0
    
    for symbol, result in results.items():
        if not result:
            continue
            
        profit_pct = result.get("profit_percentage", 0)
        win_rate = result.get("win_rate", 0)
        profit_factor = result.get("profit_factor", 0)
        
        summary["symbols_performance"][symbol] = {
            "profit_pct": profit_pct,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": result.get("total_trades", 0),
            "avg_profit": result.get("avg_profit", 0),
            "avg_loss": result.get("avg_loss", 0)
        }
        
        summary["total_trades"] += result.get("total_trades", 0)
        summary["win_trades"] += result.get("win_trades", 0)
        summary["lose_trades"] += result.get("lose_trades", 0)
        
        total_profit_pct += profit_pct
        total_win_rate += win_rate
        total_profit_factor += profit_factor
        
        if profit_pct > 0:
            summary["profitable_symbols"] += 1
            
        if profit_pct > max_profit:
            max_profit = profit_pct
            summary["best_symbol"] = symbol
            
        if profit_pct < min_profit:
            min_profit = profit_pct
            summary["worst_symbol"] = symbol
    
    # Tính trung bình
    count = len(results)
    if count > 0:
        summary["avg_profit_pct"] = total_profit_pct / count
        summary["avg_win_rate"] = total_win_rate / count
        summary["avg_profit_factor"] = total_profit_factor / count
        
    if summary["total_trades"] > 0:
        summary["overall_win_rate"] = (summary["win_trades"] / summary["total_trades"]) * 100
        
    summary["max_profit_pct"] = max_profit if max_profit != -float('inf') else 0
    summary["min_profit_pct"] = min_profit if min_profit != float('inf') else 0
    
    return summary

def create_summary_charts(summary: Dict, results: Dict[str, Dict]):
    """
    Tạo biểu đồ tổng hợp
    
    Args:
        summary (Dict): Báo cáo tổng hợp
        results (Dict[str, Dict]): Kết quả backtest theo cặp tiền
    """
    if not summary or not results:
        return
        
    # Biểu đồ so sánh lợi nhuận theo cặp tiền
    symbols = []
    profits = []
    colors = []
    
    for symbol, data in summary.get("symbols_performance", {}).items():
        symbols.append(symbol.replace("USDT", ""))
        profit = data.get("profit_pct", 0)
        profits.append(profit)
        colors.append('green' if profit >= 0 else 'red')
    
    plt.figure(figsize=(14, 8))
    plt.bar(symbols, profits, color=colors)
    plt.title('Lợi nhuận (%) theo cặp tiền - 3 tháng')
    plt.xlabel('Cặp tiền')
    plt.ylabel('Lợi nhuận (%)')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("backtest_summary/profit_by_symbol.png")
    
    # Biểu đồ so sánh win rate
    symbols = []
    win_rates = []
    
    for symbol, data in summary.get("symbols_performance", {}).items():
        symbols.append(symbol.replace("USDT", ""))
        win_rates.append(data.get("win_rate", 0))
    
    plt.figure(figsize=(14, 8))
    plt.bar(symbols, win_rates, color='blue')
    plt.title('Win Rate (%) theo cặp tiền - 3 tháng')
    plt.xlabel('Cặp tiền')
    plt.ylabel('Win Rate (%)')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("backtest_summary/win_rate_by_symbol.png")
    
    # Biểu đồ so sánh profit factor
    symbols = []
    profit_factors = []
    
    for symbol, data in summary.get("symbols_performance", {}).items():
        symbols.append(symbol.replace("USDT", ""))
        pf = data.get("profit_factor", 0)
        # Giới hạn PF để biểu đồ dễ nhìn
        if pf > 10:
            pf = 10
        profit_factors.append(pf)
    
    plt.figure(figsize=(14, 8))
    plt.bar(symbols, profit_factors, color='purple')
    plt.title('Profit Factor theo cặp tiền - 3 tháng')
    plt.xlabel('Cặp tiền')
    plt.ylabel('Profit Factor')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("backtest_summary/profit_factor_by_symbol.png")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Chạy thử nghiệm thực tế 3 tháng')
    parser.add_argument('--interval', default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--symbols', nargs='+', help='Danh sách các cặp tiền (mặc định: tất cả)')
    parser.add_argument('--no-adaptive', action='store_true', help='Không sử dụng rủi ro thích ứng')
    args = parser.parse_args()
    
    # Tải cấu hình
    config = load_account_config()
    all_symbols = config.get('symbols', [])
    
    # Xác định danh sách cặp tiền
    symbols_to_test = args.symbols if args.symbols else all_symbols
    
    logger.info(f"=== BẮT ĐẦU THỬ NGHIỆM THỰC TẾ 3 THÁNG ===")
    logger.info(f"Tổng số cặp tiền: {len(symbols_to_test)}")
    logger.info(f"Khung thời gian: {args.interval}")
    logger.info(f"Sử dụng rủi ro thích ứng: {not args.no_adaptive}")
    
    # Chạy backtest cho từng cặp tiền
    results = {}
    
    for symbol in symbols_to_test:
        result = run_backtest_for_symbol(
            symbol=symbol,
            interval=args.interval,
            adaptive_risk=not args.no_adaptive
        )
        
        if result:
            results[symbol] = result
            logger.info(f"{symbol}: Lợi nhuận {result.get('profit_percentage', 0):.2f}%, " +
                      f"Win rate {result.get('win_rate', 0):.2f}%, " +
                      f"Profit factor {result.get('profit_factor', 0):.2f}")
        else:
            logger.warning(f"{symbol}: Không có kết quả")
    
    # Tạo báo cáo tổng hợp
    summary = generate_summary_report(results)
    
    # Lưu báo cáo tổng hợp
    if summary:
        with open(f"backtest_summary/3month_summary_{args.interval}.json", 'w') as f:
            json.dump(summary, f, indent=4)
            
        logger.info(f"=== KẾT QUẢ TỔM TẮT ===")
        logger.info(f"Tổng số cặp tiền: {summary['total_symbols']}")
        logger.info(f"Số cặp tiền có lãi: {summary['profitable_symbols']}")
        logger.info(f"Tỷ lệ thắng trung bình: {summary['avg_win_rate']:.2f}%")
        logger.info(f"Profit factor trung bình: {summary['avg_profit_factor']:.2f}")
        logger.info(f"Lợi nhuận trung bình: {summary['avg_profit_pct']:.2f}%")
        logger.info(f"Cặp tiền tốt nhất: {summary['best_symbol']} ({summary['max_profit_pct']:.2f}%)")
        logger.info(f"Cặp tiền kém nhất: {summary['worst_symbol']} ({summary['min_profit_pct']:.2f}%)")
        
        # Tạo biểu đồ
        create_summary_charts(summary, results)
        
        logger.info(f"Đã lưu báo cáo tổng hợp và biểu đồ trong thư mục backtest_summary/")
    
    logger.info(f"=== KẾT THÚC THỬ NGHIỆM ===")

if __name__ == "__main__":
    main()