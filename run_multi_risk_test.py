#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy thử nghiệm 3 tháng với 5 mức rủi ro khác nhau cho tất cả cặp tiền

Script này tự động chạy backtest cho tất cả các cặp tiền trong tài khoản
với 5 mức rủi ro khác nhau và tổng hợp kết quả để xác định mức tối ưu.
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
import numpy as np

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_risk_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('multi_risk_test')

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)
os.makedirs("backtest_summary", exist_ok=True)
os.makedirs("risk_analysis", exist_ok=True)

# Định nghĩa 5 mức rủi ro khác nhau (% vốn trên mỗi giao dịch)
RISK_LEVELS = [0.5, 1.0, 1.5, 2.0, 3.0]

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

def run_backtest_for_symbol(symbol: str, interval: str = '1h', risk: float = 1.0, adaptive_risk: bool = True) -> Dict:
    """
    Chạy backtest cho một cặp tiền với mức rủi ro cụ thể
    
    Args:
        symbol (str): Mã cặp tiền
        interval (str): Khung thời gian
        risk (float): Mức rủi ro (% vốn)
        adaptive_risk (bool): Sử dụng rủi ro thích ứng hay không
        
    Returns:
        Dict: Kết quả backtest
    """
    logger.info(f"Chạy backtest cho {symbol} {interval} với mức rủi ro {risk}%...")
    
    try:
        # Tạo tên file kết quả
        risk_str = str(risk).replace('.', '_')
        result_file = f"backtest_results/{symbol}_{interval}_risk{risk_str}_results.json"
        
        # Tạo lệnh chạy backtest
        cmd = [
            "python", "enhanced_backtest.py", 
            "--symbol", symbol, 
            "--interval", interval,
            "--risk", str(risk)
        ]
        
        if adaptive_risk:
            cmd.append("--adaptive_risk")
            
        # Chạy lệnh và lấy output
        subprocess.run(cmd, check=True)
        
        # Đọc kết quả từ file
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Không tìm thấy file kết quả {result_file}, kiểm tra file adaptive_results.json")
            # Kiểm tra file mặc định
            default_file = f"backtest_results/{symbol}_{interval}_adaptive_results.json"
            if os.path.exists(default_file):
                with open(default_file, 'r') as f:
                    result = json.load(f)
                    # Sao chép file với tên mới
                    with open(result_file, 'w') as f2:
                        json.dump(result, f2, indent=4)
                    return result
                
        logger.error(f"Không tìm thấy file kết quả nào cho {symbol} với rủi ro {risk}%")
        return {}
            
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest cho {symbol} với rủi ro {risk}%: {str(e)}")
        return {}

def analyze_risk_performance(symbol: str, results: Dict[float, Dict]) -> Dict:
    """
    Phân tích hiệu suất theo mức rủi ro cho một cặp tiền
    
    Args:
        symbol (str): Mã cặp tiền
        results (Dict[float, Dict]): Kết quả backtest theo mức rủi ro
        
    Returns:
        Dict: Phân tích hiệu suất
    """
    if not results:
        return {}
        
    analysis = {
        "symbol": symbol,
        "optimal_risk": 0,
        "max_profit_pct": -float('inf'),
        "max_profit_factor": -float('inf'),
        "max_win_rate": -float('inf'),
        "risk_profit_correlation": 0,
        "risk_to_performance": {},
        "recommendation": "",
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Chuẩn bị dữ liệu cho tính tương quan
    risk_levels = []
    profit_pcts = []
    profit_factors = []
    win_rates = []
    
    for risk, result in results.items():
        if not result:
            continue
            
        profit_pct = result.get("profit_percentage", 0)
        profit_factor = result.get("profit_factor", 0)
        win_rate = result.get("win_rate", 0)
        
        analysis["risk_to_performance"][str(risk)] = {
            "profit_pct": profit_pct,
            "profit_factor": profit_factor,
            "win_rate": win_rate,
            "total_trades": result.get("total_trades", 0),
            "drawdown": result.get("max_drawdown", 0)
        }
        
        # Kiểm tra nếu lợi nhuận tốt hơn mức tốt nhất hiện tại
        if profit_pct > analysis["max_profit_pct"]:
            analysis["max_profit_pct"] = profit_pct
            analysis["optimal_risk"] = risk
            
        # Cập nhật các chỉ số tối đa khác
        if profit_factor > analysis["max_profit_factor"]:
            analysis["max_profit_factor"] = profit_factor
            
        if win_rate > analysis["max_win_rate"]:
            analysis["max_win_rate"] = win_rate
            
        # Thêm dữ liệu cho tính tương quan
        risk_levels.append(risk)
        profit_pcts.append(profit_pct)
        profit_factors.append(profit_factor)
        win_rates.append(win_rate)
    
    # Tính tương quan giữa mức rủi ro và lợi nhuận
    if len(risk_levels) > 1:
        try:
            correlation = np.corrcoef(risk_levels, profit_pcts)[0, 1]
            analysis["risk_profit_correlation"] = correlation
            
            # Tạo khuyến nghị dựa trên tương quan và kết quả
            if correlation > 0.7:
                analysis["recommendation"] = "Có thể tăng mức rủi ro để cải thiện lợi nhuận"
            elif correlation < -0.7:
                analysis["recommendation"] = "Nên sử dụng mức rủi ro thấp để tối ưu hóa lợi nhuận"
            else:
                analysis["recommendation"] = f"Mức rủi ro tối ưu là {analysis['optimal_risk']}%"
        except:
            analysis["recommendation"] = f"Mức rủi ro tối ưu là {analysis['optimal_risk']}%"
    
    return analysis

def create_risk_analysis_charts(symbol: str, risk_analysis: Dict):
    """
    Tạo biểu đồ phân tích rủi ro cho một cặp tiền
    
    Args:
        symbol (str): Mã cặp tiền
        risk_analysis (Dict): Kết quả phân tích rủi ro
    """
    if not risk_analysis or "risk_to_performance" not in risk_analysis:
        return
        
    # Chuẩn bị dữ liệu
    risk_levels = []
    profit_pcts = []
    profit_factors = []
    win_rates = []
    
    for risk_str, perf in risk_analysis["risk_to_performance"].items():
        risk_levels.append(float(risk_str))
        profit_pcts.append(perf["profit_pct"])
        profit_factors.append(min(perf["profit_factor"], 5))  # Giới hạn ở 5 để biểu đồ dễ nhìn
        win_rates.append(perf["win_rate"])
    
    # Sắp xếp theo mức rủi ro
    sorted_indices = np.argsort(risk_levels)
    risk_levels = [risk_levels[i] for i in sorted_indices]
    profit_pcts = [profit_pcts[i] for i in sorted_indices]
    profit_factors = [profit_factors[i] for i in sorted_indices]
    win_rates = [win_rates[i] for i in sorted_indices]
    
    # Tạo biểu đồ so sánh lợi nhuận theo mức rủi ro
    plt.figure(figsize=(12, 7))
    plt.plot(risk_levels, profit_pcts, 'o-', linewidth=2, markersize=8)
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.3)
    plt.title(f'{symbol} - Lợi nhuận (%) theo mức rủi ro')
    plt.xlabel('Mức rủi ro (%)')
    plt.ylabel('Lợi nhuận (%)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(risk_levels)
    
    # Đánh dấu mức rủi ro tối ưu
    optimal_idx = risk_levels.index(risk_analysis["optimal_risk"])
    plt.plot(risk_analysis["optimal_risk"], profit_pcts[optimal_idx], 'r*', markersize=15)
    plt.annotate(f'Tối ưu: {risk_analysis["optimal_risk"]}%', 
                xy=(risk_analysis["optimal_risk"], profit_pcts[optimal_idx]),
                xytext=(5, 10), textcoords='offset points', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f"risk_analysis/{symbol}_risk_profit.png")
    
    # Tạo biểu đồ so sánh Profit Factor và Win Rate theo mức rủi ro
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    color = 'tab:blue'
    ax1.set_xlabel('Mức rủi ro (%)')
    ax1.set_ylabel('Profit Factor', color=color)
    ax1.plot(risk_levels, profit_factors, 'o-', color=color, linewidth=2, markersize=8)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_xticks(risk_levels)
    
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Win Rate (%)', color=color)
    ax2.plot(risk_levels, win_rates, 'o-', color=color, linewidth=2, markersize=8)
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title(f'{symbol} - Profit Factor và Win Rate theo mức rủi ro')
    fig.tight_layout()
    plt.savefig(f"risk_analysis/{symbol}_pf_winrate.png")

def generate_combined_risk_analysis(all_risk_analyses: Dict[str, Dict]) -> Dict:
    """
    Tạo phân tích rủi ro tổng hợp cho tất cả các cặp tiền
    
    Args:
        all_risk_analyses (Dict[str, Dict]): Phân tích rủi ro theo cặp tiền
        
    Returns:
        Dict: Phân tích tổng hợp
    """
    if not all_risk_analyses:
        return {}
        
    combined = {
        "total_symbols": len(all_risk_analyses),
        "optimal_risk_distribution": {},
        "avg_optimal_risk": 0,
        "risk_preference_by_symbol": {},
        "symbols_with_positive_risk_correlation": [],
        "symbols_with_negative_risk_correlation": [],
        "overall_recommendation": "",
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Tính phân phối mức rủi ro tối ưu
    total_optimal_risk = 0
    for symbol, analysis in all_risk_analyses.items():
        optimal_risk = analysis.get("optimal_risk", 0)
        optimal_risk_str = str(optimal_risk)
        
        # Cập nhật phân phối
        if optimal_risk_str not in combined["optimal_risk_distribution"]:
            combined["optimal_risk_distribution"][optimal_risk_str] = 0
        combined["optimal_risk_distribution"][optimal_risk_str] += 1
        
        # Cập nhật mức rủi ro tối ưu cho mỗi cặp tiền
        combined["risk_preference_by_symbol"][symbol] = optimal_risk
        
        # Tổng hợp tương quan
        correlation = analysis.get("risk_profit_correlation", 0)
        if correlation > 0.5:
            combined["symbols_with_positive_risk_correlation"].append(symbol)
        elif correlation < -0.5:
            combined["symbols_with_negative_risk_correlation"].append(symbol)
            
        total_optimal_risk += optimal_risk
    
    # Tính mức rủi ro trung bình
    if combined["total_symbols"] > 0:
        combined["avg_optimal_risk"] = total_optimal_risk / combined["total_symbols"]
    
    # Tạo khuyến nghị tổng thể
    if len(combined["symbols_with_positive_risk_correlation"]) > len(combined["symbols_with_negative_risk_correlation"]):
        combined["overall_recommendation"] = f"Có xu hướng tăng lợi nhuận khi tăng rủi ro. Xem xét sử dụng mức rủi ro {combined['avg_optimal_risk']:.1f}%"
    elif len(combined["symbols_with_negative_risk_correlation"]) > len(combined["symbols_with_positive_risk_correlation"]):
        combined["overall_recommendation"] = f"Có xu hướng giảm lợi nhuận khi tăng rủi ro. Nên sử dụng mức rủi ro thấp (0.5-1.0%)"
    else:
        combined["overall_recommendation"] = f"Không có xu hướng rõ ràng. Sử dụng mức rủi ro trung bình {combined['avg_optimal_risk']:.1f}%"
    
    return combined

def create_combined_risk_charts(combined_analysis: Dict, all_risk_analyses: Dict[str, Dict]):
    """
    Tạo biểu đồ phân tích rủi ro tổng hợp
    
    Args:
        combined_analysis (Dict): Phân tích tổng hợp
        all_risk_analyses (Dict[str, Dict]): Phân tích rủi ro theo cặp tiền
    """
    if not combined_analysis or not all_risk_analyses:
        return
        
    # Biểu đồ phân phối mức rủi ro tối ưu
    plt.figure(figsize=(12, 7))
    risk_levels = []
    counts = []
    
    for risk_str, count in combined_analysis["optimal_risk_distribution"].items():
        try:
            risk_levels.append(float(risk_str))
            counts.append(count)
        except:
            continue
    
    # Sắp xếp theo mức rủi ro
    sorted_indices = np.argsort(risk_levels)
    risk_levels = [risk_levels[i] for i in sorted_indices]
    counts = [counts[i] for i in sorted_indices]
    
    plt.bar(risk_levels, counts)
    plt.title('Phân phối mức rủi ro tối ưu')
    plt.xlabel('Mức rủi ro (%)')
    plt.ylabel('Số lượng cặp tiền')
    plt.xticks(risk_levels)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("risk_analysis/optimal_risk_distribution.png")
    
    # Biểu đồ so sánh lợi nhuận ở mức rủi ro tối ưu
    plt.figure(figsize=(14, 8))
    symbols = []
    profits = []
    colors = []
    
    for symbol, analysis in all_risk_analyses.items():
        if "risk_to_performance" not in analysis:
            continue
            
        optimal_risk = analysis.get("optimal_risk", 0)
        optimal_risk_str = str(optimal_risk)
        
        if optimal_risk_str in analysis["risk_to_performance"]:
            perf = analysis["risk_to_performance"][optimal_risk_str]
            profit = perf.get("profit_pct", 0)
            
            symbols.append(symbol.replace("USDT", ""))
            profits.append(profit)
            colors.append('green' if profit >= 0 else 'red')
    
    plt.bar(symbols, profits, color=colors)
    plt.title('Lợi nhuận (%) ở mức rủi ro tối ưu')
    plt.xlabel('Cặp tiền')
    plt.ylabel('Lợi nhuận (%)')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("risk_analysis/optimal_risk_profit.png")
    
    # Biểu đồ heat map so sánh mức rủi ro vs lợi nhuận cho tất cả các cặp tiền
    symbols_short = [symbol.replace("USDT", "") for symbol in all_risk_analyses.keys()]
    
    # Chuẩn bị dữ liệu cho heat map
    risk_profit_data = np.zeros((len(RISK_LEVELS), len(symbols_short)))
    
    for i, risk in enumerate(RISK_LEVELS):
        for j, symbol in enumerate(all_risk_analyses.keys()):
            analysis = all_risk_analyses[symbol]
            if "risk_to_performance" not in analysis:
                continue
                
            risk_str = str(risk)
            if risk_str in analysis["risk_to_performance"]:
                perf = analysis["risk_to_performance"][risk_str]
                profit = perf.get("profit_pct", 0)
                risk_profit_data[i, j] = profit
    
    # Tạo heat map
    plt.figure(figsize=(16, 8))
    plt.imshow(risk_profit_data, cmap='RdYlGn', aspect='auto', interpolation='nearest')
    plt.colorbar(label='Lợi nhuận (%)')
    
    # Thêm giá trị lên từng ô
    for i in range(len(RISK_LEVELS)):
        for j in range(len(symbols_short)):
            text = plt.text(j, i, f"{risk_profit_data[i, j]:.1f}",
                           ha="center", va="center", 
                           color="black" if -5 < risk_profit_data[i, j] < 5 else "white")
    
    plt.title('Heat Map: Lợi nhuận (%) theo mức rủi ro và cặp tiền')
    plt.ylabel('Mức rủi ro (%)')
    plt.xlabel('Cặp tiền')
    plt.yticks(range(len(RISK_LEVELS)), [f"{risk}%" for risk in RISK_LEVELS])
    plt.xticks(range(len(symbols_short)), symbols_short, rotation=45)
    plt.tight_layout()
    plt.savefig("risk_analysis/risk_profit_heatmap.png")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Chạy thử nghiệm 3 tháng với nhiều mức rủi ro')
    parser.add_argument('--interval', default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--symbols', nargs='+', help='Danh sách các cặp tiền (mặc định: tất cả)')
    parser.add_argument('--no-adaptive', action='store_true', help='Không sử dụng rủi ro thích ứng')
    args = parser.parse_args()
    
    # Tải cấu hình
    config = load_account_config()
    all_symbols = config.get('symbols', [])
    
    # Xác định danh sách cặp tiền
    symbols_to_test = args.symbols if args.symbols else all_symbols
    
    logger.info(f"=== BẮT ĐẦU THỬ NGHIỆM ĐA MỨC RỦI RO 3 THÁNG ===")
    logger.info(f"Tổng số cặp tiền: {len(symbols_to_test)}")
    logger.info(f"Khung thời gian: {args.interval}")
    logger.info(f"Các mức rủi ro: {RISK_LEVELS}")
    logger.info(f"Sử dụng rủi ro thích ứng: {not args.no_adaptive}")
    
    # Chạy backtest cho từng cặp tiền với mỗi mức rủi ro
    all_results = {}  # symbol -> risk_level -> results
    all_risk_analyses = {}  # symbol -> risk_analysis
    
    for symbol in symbols_to_test:
        symbol_results = {}
        
        for risk in RISK_LEVELS:
            result = run_backtest_for_symbol(
                symbol=symbol,
                interval=args.interval,
                risk=risk,
                adaptive_risk=not args.no_adaptive
            )
            
            if result:
                symbol_results[risk] = result
                logger.info(f"{symbol} (Rủi ro {risk}%): Lợi nhuận {result.get('profit_percentage', 0):.2f}%, " +
                          f"Win rate {result.get('win_rate', 0):.2f}%, " +
                          f"Profit factor {result.get('profit_factor', 0):.2f}")
        
        if symbol_results:
            all_results[symbol] = symbol_results
            
            # Phân tích rủi ro
            risk_analysis = analyze_risk_performance(symbol, symbol_results)
            all_risk_analyses[symbol] = risk_analysis
            
            if risk_analysis:
                logger.info(f"{symbol}: Mức rủi ro tối ưu là {risk_analysis.get('optimal_risk', 0)}%, " +
                          f"Lợi nhuận tối đa {risk_analysis.get('max_profit_pct', 0):.2f}%")
                
                # Tạo biểu đồ phân tích rủi ro
                create_risk_analysis_charts(symbol, risk_analysis)
    
    # Tạo phân tích tổng hợp
    combined_analysis = generate_combined_risk_analysis(all_risk_analyses)
    
    # Lưu phân tích tổng hợp
    if combined_analysis:
        with open("risk_analysis/combined_risk_analysis.json", 'w') as f:
            json.dump(combined_analysis, f, indent=4)
            
        logger.info(f"=== PHÂN TÍCH TỔNG HỢP ===")
        logger.info(f"Tổng số cặp tiền: {combined_analysis['total_symbols']}")
        logger.info(f"Mức rủi ro tối ưu trung bình: {combined_analysis['avg_optimal_risk']:.2f}%")
        logger.info(f"Số cặp có tương quan dương với rủi ro: {len(combined_analysis['symbols_with_positive_risk_correlation'])}")
        logger.info(f"Số cặp có tương quan âm với rủi ro: {len(combined_analysis['symbols_with_negative_risk_correlation'])}")
        logger.info(f"Khuyến nghị: {combined_analysis['overall_recommendation']}")
        
        # Tạo biểu đồ tổng hợp
        create_combined_risk_charts(combined_analysis, all_risk_analyses)
        
        logger.info(f"Đã lưu phân tích rủi ro và biểu đồ trong thư mục risk_analysis/")
    
    logger.info(f"=== KẾT THÚC THỬ NGHIỆM ===")

if __name__ == "__main__":
    main()