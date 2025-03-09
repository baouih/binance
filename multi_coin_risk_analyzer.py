#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script phân tích hiệu suất của các mức rủi ro khác nhau trên nhiều đồng coin

Script này kiểm tra hiệu suất của các mức rủi ro khác nhau (10%, 15%, 20%, 30%)
trên các đồng coin thanh khoản cao như BTC, ETH, BNB, SOL...
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Tuple, Any
import logging
import argparse

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multi_coin_risk_analysis.log')
    ]
)

logger = logging.getLogger('multi_coin_risk_analyzer')

# Danh sách coin thanh khoản cao
HIGH_LIQUIDITY_COINS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 
    'ADAUSDT', 'DOGEUSDT', 'XRPUSDT', 'AVAXUSDT'
]

# Các mức rủi ro cần kiểm tra
RISK_LEVELS = [10.0, 15.0, 20.0, 30.0]

# Các khung thời gian cần kiểm tra
TIMEFRAMES = ['1h', '4h', '1d']

def load_backtest_results(symbol: str, timeframe: str, risk_level: float) -> Dict:
    """
    Tải kết quả backtest từ file

    Args:
        symbol (str): Ký hiệu cặp tiền (ví dụ: BTCUSDT)
        timeframe (str): Khung thời gian (ví dụ: 1h, 4h, 1d)
        risk_level (float): Mức rủi ro (ví dụ: 10.0, 15.0)

    Returns:
        Dict: Dữ liệu kết quả hoặc None nếu không tìm thấy
    """
    # Thử nhiều định dạng tên file khác nhau
    potential_files = [
        f"backtest_results/{symbol}_{timeframe}_risk{int(risk_level)}_results.json",
        f"backtest_results/{symbol}_{timeframe}_risk{int(risk_level)}.json",
        f"backtest_results/{symbol}_{timeframe}_risk_{risk_level}_results.json"
    ]
    
    # Thêm định dạng với dấu chấm (ví dụ risk0.5)
    if risk_level < 10:
        risk_str = str(risk_level).replace('.', '_')
        potential_files.append(f"backtest_results/{symbol}_{timeframe}_risk{risk_str}_results.json")
    
    # Kiểm tra từng file
    for file_path in potential_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Đã tải kết quả từ {file_path}")
                return data
            except Exception as e:
                logger.error(f"Lỗi khi đọc file {file_path}: {str(e)}")
    
    logger.warning(f"Không tìm thấy kết quả cho {symbol} {timeframe} với mức rủi ro {risk_level}%")
    return None

def analyze_all_coins(coins: List[str] = None, 
                      timeframes: List[str] = None,
                      risk_levels: List[float] = None) -> Dict:
    """
    Phân tích hiệu suất của các mức rủi ro trên nhiều coin

    Args:
        coins (List[str], optional): Danh sách coin cần phân tích
        timeframes (List[str], optional): Danh sách khung thời gian
        risk_levels (List[float], optional): Danh sách mức rủi ro

    Returns:
        Dict: Kết quả phân tích
    """
    # Sử dụng giá trị mặc định nếu không được cung cấp
    if coins is None:
        coins = HIGH_LIQUIDITY_COINS
    if timeframes is None:
        timeframes = TIMEFRAMES
    if risk_levels is None:
        risk_levels = RISK_LEVELS
    
    # Cấu trúc kết quả
    results = {
        "summary": {},
        "details": {},
        "best_performers": {},
        "risk_performance": {}
    }
    
    # Phân tích từng coin
    for symbol in coins:
        symbol_results = {}
        
        # Phân tích từng khung thời gian
        for timeframe in timeframes:
            timeframe_results = {}
            valid_results_count = 0
            
            # Phân tích từng mức rủi ro
            for risk in risk_levels:
                # Tải kết quả backtest
                backtest_data = load_backtest_results(symbol, timeframe, risk)
                
                if backtest_data:
                    valid_results_count += 1
                    
                    # Trích xuất các chỉ số quan trọng
                    win_rate = backtest_data.get('win_rate', 0)
                    profit_pct = backtest_data.get('profit_pct', 0)
                    max_drawdown = backtest_data.get('max_drawdown_pct', 0)
                    profit_factor = backtest_data.get('profit_factor', 0)
                    total_trades = backtest_data.get('total_trades', 0)
                    
                    # Lưu kết quả
                    timeframe_results[str(risk)] = {
                        'win_rate': win_rate,
                        'profit_pct': profit_pct,
                        'max_drawdown': max_drawdown,
                        'profit_factor': profit_factor,
                        'total_trades': total_trades,
                        'risk_adjusted_return': profit_pct / max_drawdown if max_drawdown > 0 else 0
                    }
            
            # Chỉ lưu kết quả nếu có ít nhất một mức rủi ro hợp lệ
            if valid_results_count > 0:
                symbol_results[timeframe] = timeframe_results
        
        # Lưu kết quả cho từng đồng coin
        if symbol_results:
            results["details"][symbol] = symbol_results
    
    # Tính toán các chỉ số tổng hợp
    if results["details"]:
        results["summary"] = calculate_summary_metrics(results["details"])
        results["best_performers"] = find_best_performers(results["details"])
        results["risk_performance"] = analyze_risk_performance(results["details"])
    
    return results

def calculate_summary_metrics(detailed_results: Dict) -> Dict:
    """
    Tính toán các chỉ số tổng hợp từ kết quả chi tiết

    Args:
        detailed_results (Dict): Kết quả chi tiết theo từng coin

    Returns:
        Dict: Các chỉ số tổng hợp
    """
    summary = {
        "total_coins": len(detailed_results),
        "risk_levels": {},
        "timeframes": {}
    }
    
    # Khởi tạo cấu trúc dữ liệu cho mỗi mức rủi ro
    for risk in RISK_LEVELS:
        summary["risk_levels"][str(risk)] = {
            "avg_win_rate": 0,
            "avg_profit_pct": 0,
            "avg_max_drawdown": 0,
            "avg_profit_factor": 0,
            "avg_risk_adjusted_return": 0,
            "num_samples": 0
        }
    
    # Khởi tạo cấu trúc dữ liệu cho mỗi khung thời gian
    for tf in TIMEFRAMES:
        summary["timeframes"][tf] = {
            "avg_win_rate": 0,
            "avg_profit_pct": 0,
            "avg_max_drawdown": 0,
            "avg_profit_factor": 0,
            "avg_risk_adjusted_return": 0,
            "num_samples": 0
        }
    
    # Tính tổng và đếm số lượng để tính trung bình
    for symbol, symbol_data in detailed_results.items():
        for timeframe, timeframe_data in symbol_data.items():
            for risk, risk_data in timeframe_data.items():
                # Cập nhật thống kê theo mức rủi ro
                risk_summary = summary["risk_levels"].get(risk, {})
                if risk_summary:
                    risk_summary["avg_win_rate"] += risk_data.get("win_rate", 0)
                    risk_summary["avg_profit_pct"] += risk_data.get("profit_pct", 0)
                    risk_summary["avg_max_drawdown"] += risk_data.get("max_drawdown", 0)
                    risk_summary["avg_profit_factor"] += risk_data.get("profit_factor", 0)
                    risk_summary["avg_risk_adjusted_return"] += risk_data.get("risk_adjusted_return", 0)
                    risk_summary["num_samples"] += 1
                
                # Cập nhật thống kê theo khung thời gian
                tf_summary = summary["timeframes"].get(timeframe, {})
                if tf_summary:
                    tf_summary["avg_win_rate"] += risk_data.get("win_rate", 0)
                    tf_summary["avg_profit_pct"] += risk_data.get("profit_pct", 0)
                    tf_summary["avg_max_drawdown"] += risk_data.get("max_drawdown", 0)
                    tf_summary["avg_profit_factor"] += risk_data.get("profit_factor", 0)
                    tf_summary["avg_risk_adjusted_return"] += risk_data.get("risk_adjusted_return", 0)
                    tf_summary["num_samples"] += 1
    
    # Tính giá trị trung bình
    for risk, risk_summary in summary["risk_levels"].items():
        if risk_summary["num_samples"] > 0:
            for key in ["avg_win_rate", "avg_profit_pct", "avg_max_drawdown", 
                        "avg_profit_factor", "avg_risk_adjusted_return"]:
                risk_summary[key] /= risk_summary["num_samples"]
    
    for tf, tf_summary in summary["timeframes"].items():
        if tf_summary["num_samples"] > 0:
            for key in ["avg_win_rate", "avg_profit_pct", "avg_max_drawdown", 
                        "avg_profit_factor", "avg_risk_adjusted_return"]:
                tf_summary[key] /= tf_summary["num_samples"]
    
    return summary

def find_best_performers(detailed_results: Dict) -> Dict:
    """
    Tìm các cặp coin/khung thời gian/mức rủi ro có hiệu suất tốt nhất

    Args:
        detailed_results (Dict): Kết quả chi tiết theo từng coin

    Returns:
        Dict: Các hiệu suất tốt nhất
    """
    best_performers = {
        "by_profit": [],
        "by_win_rate": [],
        "by_risk_adjusted": [],
        "by_profit_factor": [],
        "best_combination": []
    }
    
    all_results = []
    
    # Thu thập tất cả kết quả
    for symbol, symbol_data in detailed_results.items():
        for timeframe, timeframe_data in symbol_data.items():
            for risk, risk_data in timeframe_data.items():
                entry = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "risk": float(risk),
                    "win_rate": risk_data.get("win_rate", 0),
                    "profit_pct": risk_data.get("profit_pct", 0),
                    "max_drawdown": risk_data.get("max_drawdown", 0),
                    "profit_factor": risk_data.get("profit_factor", 0),
                    "risk_adjusted_return": risk_data.get("risk_adjusted_return", 0),
                    "total_trades": risk_data.get("total_trades", 0)
                }
                all_results.append(entry)
    
    # Sắp xếp theo lợi nhuận
    by_profit = sorted(all_results, key=lambda x: x["profit_pct"], reverse=True)
    best_performers["by_profit"] = by_profit[:10]  # Top 10
    
    # Sắp xếp theo tỷ lệ thắng
    by_win_rate = sorted(all_results, key=lambda x: x["win_rate"], reverse=True)
    best_performers["by_win_rate"] = by_win_rate[:10]  # Top 10
    
    # Sắp xếp theo hiệu suất điều chỉnh theo rủi ro
    by_risk_adjusted = sorted(all_results, key=lambda x: x["risk_adjusted_return"], reverse=True)
    best_performers["by_risk_adjusted"] = by_risk_adjusted[:10]  # Top 10
    
    # Sắp xếp theo profit factor
    by_profit_factor = sorted(all_results, key=lambda x: x["profit_factor"], reverse=True)
    best_performers["by_profit_factor"] = by_profit_factor[:10]  # Top 10
    
    # Tìm kết hợp tốt nhất (điểm đánh giá tổng hợp)
    for entry in all_results:
        # Mức độ cân bằng là đánh giá tổng hợp
        balance_score = (
            0.3 * entry["profit_pct"] / 100 +  # 30% trọng số cho lợi nhuận
            0.2 * entry["win_rate"] / 100 +    # 20% trọng số cho tỷ lệ thắng
            0.25 * entry["risk_adjusted_return"] / 5 +  # 25% cho hiệu suất điều chỉnh theo rủi ro
            0.25 * entry["profit_factor"] / 3   # 25% cho profit factor
        )
        entry["balance_score"] = balance_score
    
    # Sắp xếp theo điểm tổng hợp
    best_combinations = sorted(all_results, key=lambda x: x["balance_score"], reverse=True)
    best_performers["best_combination"] = best_combinations[:10]  # Top 10
    
    return best_performers

def analyze_risk_performance(detailed_results: Dict) -> Dict:
    """
    Phân tích hiệu suất theo mức rủi ro

    Args:
        detailed_results (Dict): Kết quả chi tiết theo từng coin

    Returns:
        Dict: Phân tích hiệu suất theo rủi ro
    """
    risk_performance = {}
    
    # Khởi tạo cấu trúc dữ liệu cho mỗi mức rủi ro
    for risk in RISK_LEVELS:
        risk_performance[str(risk)] = {
            "coins": {},
            "win_rate_range": [100, 0],  # [min, max]
            "profit_range": [float('inf'), float('-inf')],  # [min, max]
            "drawdown_range": [float('inf'), float('-inf')],  # [min, max]
            "best_coin": "",
            "worst_coin": ""
        }
    
    # Thu thập thông tin hiệu suất theo từng mức rủi ro
    for symbol, symbol_data in detailed_results.items():
        for timeframe, timeframe_data in symbol_data.items():
            for risk, risk_data in timeframe_data.items():
                if risk not in risk_performance:
                    continue
                
                # Lưu thông tin hiệu suất cho từng coin
                if symbol not in risk_performance[risk]["coins"]:
                    risk_performance[risk]["coins"][symbol] = []
                
                risk_performance[risk]["coins"][symbol].append({
                    "timeframe": timeframe,
                    "win_rate": risk_data.get("win_rate", 0),
                    "profit_pct": risk_data.get("profit_pct", 0),
                    "max_drawdown": risk_data.get("max_drawdown", 0),
                    "profit_factor": risk_data.get("profit_factor", 0),
                    "risk_adjusted_return": risk_data.get("risk_adjusted_return", 0)
                })
                
                # Cập nhật phạm vi win rate
                win_rate = risk_data.get("win_rate", 0)
                risk_performance[risk]["win_rate_range"][0] = min(risk_performance[risk]["win_rate_range"][0], win_rate)
                risk_performance[risk]["win_rate_range"][1] = max(risk_performance[risk]["win_rate_range"][1], win_rate)
                
                # Cập nhật phạm vi lợi nhuận
                profit = risk_data.get("profit_pct", 0)
                if profit < risk_performance[risk]["profit_range"][0]:
                    risk_performance[risk]["profit_range"][0] = profit
                    risk_performance[risk]["worst_coin"] = f"{symbol} ({timeframe})"
                if profit > risk_performance[risk]["profit_range"][1]:
                    risk_performance[risk]["profit_range"][1] = profit
                    risk_performance[risk]["best_coin"] = f"{symbol} ({timeframe})"
                
                # Cập nhật phạm vi drawdown
                drawdown = risk_data.get("max_drawdown", 0)
                risk_performance[risk]["drawdown_range"][0] = min(risk_performance[risk]["drawdown_range"][0], drawdown)
                risk_performance[risk]["drawdown_range"][1] = max(risk_performance[risk]["drawdown_range"][1], drawdown)
    
    return risk_performance

def plot_risk_comparison(results: Dict, output_file: str = "risk_analysis/multi_coin_risk_comparison.png"):
    """
    Vẽ biểu đồ so sánh hiệu suất các mức rủi ro trên nhiều coin

    Args:
        results (Dict): Kết quả phân tích
        output_file (str): Đường dẫn lưu biểu đồ
    """
    # Tạo thư mục nếu chưa tồn tại
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Khởi tạo figure
    plt.figure(figsize=(16, 12))
    
    # Dữ liệu để vẽ
    risk_levels = []
    avg_profit = []
    avg_drawdown = []
    avg_win_rate = []
    avg_risk_adjusted = []
    
    # Thu thập dữ liệu từ kết quả
    for risk, risk_data in results["summary"]["risk_levels"].items():
        risk_levels.append(float(risk))
        avg_profit.append(risk_data["avg_profit_pct"])
        avg_drawdown.append(risk_data["avg_max_drawdown"])
        avg_win_rate.append(risk_data["avg_win_rate"])
        avg_risk_adjusted.append(risk_data["avg_risk_adjusted_return"])
    
    # Sắp xếp theo mức rủi ro tăng dần
    sorted_indices = np.argsort(risk_levels)
    risk_levels = [risk_levels[i] for i in sorted_indices]
    avg_profit = [avg_profit[i] for i in sorted_indices]
    avg_drawdown = [avg_drawdown[i] for i in sorted_indices]
    avg_win_rate = [avg_win_rate[i] for i in sorted_indices]
    avg_risk_adjusted = [avg_risk_adjusted[i] for i in sorted_indices]
    
    # Tạo 4 biểu đồ con
    plt.subplot(2, 2, 1)
    plt.plot(risk_levels, avg_profit, 'o-', linewidth=2, markersize=8)
    plt.title('Lợi nhuận trung bình theo mức rủi ro', fontsize=14)
    plt.xlabel('Mức rủi ro (%)', fontsize=12)
    plt.ylabel('Lợi nhuận (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    plt.subplot(2, 2, 2)
    plt.plot(risk_levels, avg_drawdown, 'o-', linewidth=2, markersize=8, color='red')
    plt.title('Drawdown trung bình theo mức rủi ro', fontsize=14)
    plt.xlabel('Mức rủi ro (%)', fontsize=12)
    plt.ylabel('Drawdown (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    plt.subplot(2, 2, 3)
    plt.plot(risk_levels, avg_win_rate, 'o-', linewidth=2, markersize=8, color='green')
    plt.title('Tỷ lệ thắng trung bình theo mức rủi ro', fontsize=14)
    plt.xlabel('Mức rủi ro (%)', fontsize=12)
    plt.ylabel('Tỷ lệ thắng (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    plt.subplot(2, 2, 4)
    plt.plot(risk_levels, avg_risk_adjusted, 'o-', linewidth=2, markersize=8, color='purple')
    plt.title('Hiệu suất điều chỉnh rủi ro', fontsize=14)
    plt.xlabel('Mức rủi ro (%)', fontsize=12)
    plt.ylabel('Lợi nhuận/Drawdown', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    
    logger.info(f"Đã lưu biểu đồ so sánh rủi ro tại {output_file}")

def save_results(results: Dict, output_file: str = "multi_coin_risk_analysis.json"):
    """
    Lưu kết quả phân tích vào file

    Args:
        results (Dict): Kết quả phân tích
        output_file (str): Đường dẫn lưu file
    """
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
    logger.info(f"Đã lưu kết quả phân tích tại {output_file}")

def generate_markdown_report(results: Dict, output_file: str = "risk_analysis/multi_coin_risk_report.md"):
    """
    Tạo báo cáo dạng markdown từ kết quả phân tích

    Args:
        results (Dict): Kết quả phân tích
        output_file (str): Đường dẫn lưu báo cáo
    """
    # Tạo thư mục nếu chưa tồn tại
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Khởi tạo nội dung báo cáo
    report = f"""# Báo Cáo Phân Tích Hiệu Suất Theo Mức Rủi Ro
    
*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Tổng Quan

Báo cáo này phân tích hiệu suất của các mức rủi ro khác nhau (10%, 15%, 20%, 30%) trên {results['summary']['total_coins']} đồng coin thanh khoản cao.

## So Sánh Các Mức Rủi Ro

| Mức Rủi Ro | Win Rate | Lợi Nhuận | Drawdown | Profit Factor | Hiệu Suất Điều Chỉnh Rủi Ro |
|------------|----------|-----------|----------|---------------|------------------------------|
"""
    
    # Thêm dữ liệu cho bảng so sánh
    for risk, risk_data in sorted(results["summary"]["risk_levels"].items(), key=lambda x: float(x[0])):
        if risk_data["num_samples"] > 0:
            report += f"| {risk}% | {risk_data['avg_win_rate']:.2f}% | {risk_data['avg_profit_pct']:.2f}% | {risk_data['avg_max_drawdown']:.2f}% | {risk_data['avg_profit_factor']:.2f} | {risk_data['avg_risk_adjusted_return']:.2f} |\n"
    
    # Thêm phần so sánh khung thời gian
    report += """
## So Sánh Các Khung Thời Gian

| Khung Thời Gian | Win Rate | Lợi Nhuận | Drawdown | Profit Factor | Hiệu Suất Điều Chỉnh Rủi Ro |
|-----------------|----------|-----------|----------|---------------|------------------------------|
"""
    
    # Thêm dữ liệu cho bảng khung thời gian
    for tf, tf_data in results["summary"]["timeframes"].items():
        if tf_data["num_samples"] > 0:
            report += f"| {tf} | {tf_data['avg_win_rate']:.2f}% | {tf_data['avg_profit_pct']:.2f}% | {tf_data['avg_max_drawdown']:.2f}% | {tf_data['avg_profit_factor']:.2f} | {tf_data['avg_risk_adjusted_return']:.2f} |\n"
    
    # Thêm phần hiệu suất tốt nhất
    report += """
## Top 5 Kết Hợp Tốt Nhất (Cân Bằng)

| Coin | Khung Thời Gian | Mức Rủi Ro | Win Rate | Lợi Nhuận | Drawdown | Profit Factor | Điểm Tổng Hợp |
|------|-----------------|------------|----------|-----------|----------|---------------|---------------|
"""
    
    # Thêm dữ liệu top 5 kết hợp tốt nhất
    for i, entry in enumerate(results["best_performers"]["best_combination"][:5]):
        report += f"| {entry['symbol']} | {entry['timeframe']} | {entry['risk']}% | {entry['win_rate']:.2f}% | {entry['profit_pct']:.2f}% | {entry['max_drawdown']:.2f}% | {entry['profit_factor']:.2f} | {entry['balance_score']:.3f} |\n"
    
    # Thêm phần phân tích cho từng mức rủi ro
    report += """
## Phân Tích Chi Tiết Theo Mức Rủi Ro

"""
    
    for risk, risk_data in sorted(results["risk_performance"].items(), key=lambda x: float(x[0])):
        report += f"""### Mức Rủi Ro {risk}%

- **Phạm vi Win Rate:** {risk_data['win_rate_range'][0]:.2f}% - {risk_data['win_rate_range'][1]:.2f}%
- **Phạm vi Lợi Nhuận:** {risk_data['profit_range'][0]:.2f}% - {risk_data['profit_range'][1]:.2f}%
- **Phạm vi Drawdown:** {risk_data['drawdown_range'][0]:.2f}% - {risk_data['drawdown_range'][1]:.2f}%
- **Coin hiệu suất tốt nhất:** {risk_data['best_coin']}
- **Coin hiệu suất kém nhất:** {risk_data['worst_coin']}

"""
    
    # Thêm phần kết luận và đề xuất
    report += """
## Kết Luận và Đề Xuất

Dựa trên phân tích dữ liệu từ nhiều cặp tiền và khung thời gian khác nhau, chúng tôi đưa ra các khuyến nghị sau:

"""
    
    # Tìm mức rủi ro có hiệu suất điều chỉnh rủi ro cao nhất
    best_risk_adj = 0
    best_risk = None
    for risk, risk_data in results["summary"]["risk_levels"].items():
        if risk_data["avg_risk_adjusted_return"] > best_risk_adj:
            best_risk_adj = risk_data["avg_risk_adjusted_return"]
            best_risk = risk
    
    # Tìm mức rủi ro có lợi nhuận cao nhất
    best_profit = 0
    best_profit_risk = None
    for risk, risk_data in results["summary"]["risk_levels"].items():
        if risk_data["avg_profit_pct"] > best_profit:
            best_profit = risk_data["avg_profit_pct"]
            best_profit_risk = risk
    
    # Thêm đề xuất
    report += f"""1. **Mức rủi ro tối ưu cho cân bằng:** {best_risk}% - cung cấp hiệu suất điều chỉnh rủi ro cao nhất trong các mức rủi ro được kiểm tra, với tỷ số lợi nhuận/drawdown là {best_risk_adj:.2f}.

2. **Mức rủi ro cho lợi nhuận tối đa:** {best_profit_risk}% - tạo ra lợi nhuận trung bình cao nhất là {best_profit:.2f}%, nhưng cũng có mức độ biến động cao hơn.

3. **Khuyến nghị theo quy mô tài khoản:**
   - **Tài khoản $100-$200:** Mức rủi ro 10-15%
   - **Tài khoản $200-$500:** Mức rủi ro 15-20%
   - **Tài khoản $500-$1000:** Mức rủi ro 20-30% (tùy theo khả năng chịu đựng rủi ro)
   - **Tài khoản >$1000:** Có thể cân nhắc mức rủi ro 30% với một phần tài khoản

4. **Khuyến nghị về khung thời gian:**
   - Khung thời gian {max(results["summary"]["timeframes"].items(), key=lambda x: x[1]["avg_risk_adjusted_return"])[0]} cho hiệu suất điều chỉnh rủi ro tốt nhất
   - Khung thời gian {max(results["summary"]["timeframes"].items(), key=lambda x: x[1]["avg_profit_pct"])[0]} cho lợi nhuận tổng thể tốt nhất

5. **Top 3 coin hiệu quả nhất:**
"""
    
    # Thêm top 3 coin hiệu quả nhất
    top_coins = {}
    for entry in results["best_performers"]["best_combination"]:
        symbol = entry["symbol"]
        if symbol not in top_coins:
            top_coins[symbol] = entry["balance_score"]
    
    # Sắp xếp và lấy top 3
    top_3_coins = sorted(top_coins.items(), key=lambda x: x[1], reverse=True)[:3]
    for i, (coin, score) in enumerate(top_3_coins):
        report += f"   - {coin}: Điểm hiệu suất tổng hợp {score:.3f}\n"
    
    # Lưu báo cáo
    with open(output_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Đã tạo báo cáo markdown tại {output_file}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Phân tích hiệu suất của các mức rủi ro trên nhiều coin')
    parser.add_argument('--coins', nargs='+', help='Danh sách coin cần phân tích')
    parser.add_argument('--timeframes', nargs='+', help='Danh sách khung thời gian')
    parser.add_argument('--risk_levels', nargs='+', type=float, help='Danh sách mức rủi ro')
    args = parser.parse_args()
    
    logger.info("Bắt đầu phân tích hiệu suất đa coin theo mức rủi ro")
    
    # Phân tích tất cả coin
    results = analyze_all_coins(
        coins=args.coins,
        timeframes=args.timeframes,
        risk_levels=args.risk_levels
    )
    
    # Lưu kết quả phân tích
    save_results(results)
    
    # Tạo biểu đồ so sánh
    plot_risk_comparison(results)
    
    # Tạo báo cáo markdown
    generate_markdown_report(results)
    
    logger.info("Đã hoàn thành phân tích hiệu suất đa coin theo mức rủi ro")

if __name__ == "__main__":
    main()