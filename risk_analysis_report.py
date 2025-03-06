#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo báo cáo phân tích rủi ro chi tiết với biểu đồ và tổng hợp kết quả

Script này đọc dữ liệu kết quả từ thử nghiệm đa mức rủi ro và tạo ra các
biểu đồ trực quan, bảng so sánh và khuyến nghị mức rủi ro tối ưu cho mỗi
cặp tiền và trên toàn bộ hệ thống.
"""

import os
import sys
import json
import logging
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from typing import Dict, List, Tuple
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('risk_analysis_report.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('risk_analysis_report')

# Đảm bảo các thư mục cần thiết tồn tại
os.makedirs("risk_analysis", exist_ok=True)
os.makedirs("risk_analysis/charts", exist_ok=True)
os.makedirs("backtest_summary", exist_ok=True)

# Định nghĩa các mức rủi ro
RISK_LEVELS = [0.5, 1.0, 1.5, 2.0, 3.0]

def load_summary_data(file_path: str = "backtest_summary/multi_risk_summary.json") -> Dict:
    """
    Tải dữ liệu tổng hợp từ file
    
    Args:
        file_path (str): Đường dẫn đến file dữ liệu
        
    Returns:
        Dict: Dữ liệu tổng hợp
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu tổng hợp từ {file_path}: {str(e)}")
        return {}

def create_risk_performance_charts(summary_data: Dict) -> None:
    """
    Tạo biểu đồ hiệu suất theo mức rủi ro
    
    Args:
        summary_data (Dict): Dữ liệu tổng hợp
    """
    if not summary_data or "symbols" not in summary_data:
        logger.warning("Không có dữ liệu để tạo biểu đồ")
        return
    
    optimal_risk = summary_data.get("risk_analysis", {}).get("optimal_risk_by_symbol", {})
    
    # Tạo biểu đồ cho từng cặp tiền
    for symbol, tf_data in summary_data["symbols"].items():
        logger.info(f"Tạo biểu đồ cho {symbol}...")
        
        for tf, risk_data in tf_data.items():
            # Chuẩn bị dữ liệu
            risks = []
            profits = []
            win_rates = []
            profit_factors = []
            
            for risk_str, metrics in risk_data.items():
                try:
                    risk = float(risk_str)
                    risks.append(risk)
                    profits.append(metrics.get("profit_pct", 0))
                    win_rates.append(metrics.get("win_rate", 0))
                    profit_factors.append(min(metrics.get("profit_factor", 0), 5))  # Giới hạn ở 5 để dễ nhìn
                except:
                    continue
            
            if not risks:
                continue
                
            # Sắp xếp theo mức rủi ro
            sorted_indices = np.argsort(risks)
            risks = [risks[i] for i in sorted_indices]
            profits = [profits[i] for i in sorted_indices]
            win_rates = [win_rates[i] for i in sorted_indices]
            profit_factors = [profit_factors[i] for i in sorted_indices]
            
            # Biểu đồ lợi nhuận theo mức rủi ro
            plt.figure(figsize=(12, 7))
            plt.plot(risks, profits, 'o-', linewidth=2, markersize=8)
            plt.axhline(y=0, color='r', linestyle='--', alpha=0.3)
            plt.title(f'{symbol} ({tf}) - Lợi nhuận (%) theo mức rủi ro')
            plt.xlabel('Mức rủi ro (%)')
            plt.ylabel('Lợi nhuận (%)')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.xticks(risks)
            
            # Đánh dấu mức rủi ro tối ưu nếu có
            optimal = optimal_risk.get(symbol)
            if optimal is not None:
                try:
                    optimal_index = risks.index(optimal)
                    plt.plot(optimal, profits[optimal_index], 'r*', markersize=15)
                    plt.annotate(f'Tối ưu: {optimal}%', 
                                xy=(optimal, profits[optimal_index]),
                                xytext=(5, 10), textcoords='offset points', fontsize=12)
                except:
                    pass
            
            plt.tight_layout()
            plt.savefig(f"risk_analysis/charts/{symbol}_{tf}_risk_profit.png")
            plt.close()
            
            # Biểu đồ Profit Factor và Win Rate
            fig, ax1 = plt.subplots(figsize=(12, 7))
            
            color = 'tab:blue'
            ax1.set_xlabel('Mức rủi ro (%)')
            ax1.set_ylabel('Profit Factor', color=color)
            ax1.plot(risks, profit_factors, 'o-', color=color, linewidth=2, markersize=8)
            ax1.tick_params(axis='y', labelcolor=color)
            ax1.set_xticks(risks)
            
            ax2 = ax1.twinx()
            color = 'tab:red'
            ax2.set_ylabel('Win Rate (%)', color=color)
            ax2.plot(risks, win_rates, 'o-', color=color, linewidth=2, markersize=8)
            ax2.tick_params(axis='y', labelcolor=color)
            
            plt.title(f'{symbol} ({tf}) - Profit Factor và Win Rate theo mức rủi ro')
            fig.tight_layout()
            plt.savefig(f"risk_analysis/charts/{symbol}_{tf}_pf_winrate.png")
            plt.close()

def create_optimal_risk_distribution_chart(summary_data: Dict) -> None:
    """
    Tạo biểu đồ phân phối mức rủi ro tối ưu
    
    Args:
        summary_data (Dict): Dữ liệu tổng hợp
    """
    if not summary_data or "risk_analysis" not in summary_data:
        return
        
    risk_distribution = summary_data["risk_analysis"].get("risk_distribution", {})
    
    if not risk_distribution:
        return
    
    # Chuẩn bị dữ liệu
    risks = []
    counts = []
    
    for risk_str, count in risk_distribution.items():
        try:
            risks.append(float(risk_str))
            counts.append(count)
        except:
            continue
    
    if not risks:
        return
        
    # Sắp xếp theo mức rủi ro
    sorted_indices = np.argsort(risks)
    risks = [risks[i] for i in sorted_indices]
    counts = [counts[i] for i in sorted_indices]
    
    # Tạo biểu đồ
    plt.figure(figsize=(12, 7))
    bars = plt.bar(risks, counts, color='skyblue', width=0.4)
    
    # Thêm nhãn trên mỗi cột
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.0f}', ha='center', va='bottom')
    
    plt.title('Phân phối mức rủi ro tối ưu', fontsize=16)
    plt.xlabel('Mức rủi ro (%)', fontsize=14)
    plt.ylabel('Số lượng cặp tiền', fontsize=14)
    plt.xticks(risks, [f"{risk}%" for risk in risks], fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("risk_analysis/charts/optimal_risk_distribution.png")
    plt.close()

def create_best_performers_chart(summary_data: Dict) -> None:
    """
    Tạo biểu đồ các cặp tiền có hiệu suất tốt nhất
    
    Args:
        summary_data (Dict): Dữ liệu tổng hợp
    """
    if not summary_data or "risk_analysis" not in summary_data:
        return
        
    best_performers = summary_data["risk_analysis"].get("best_performers", [])
    
    if not best_performers:
        return
    
    # Lấy top 10
    top_performers = best_performers[:10]
    
    # Chuẩn bị dữ liệu
    symbols = [f"{p['symbol'].replace('USDT', '')}" for p in top_performers]
    profits = [p["profit_pct"] for p in top_performers]
    tf_risk = [f"{p['timeframe']}/{p['risk']}%" for p in top_performers]
    colors = ['green' if p > 0 else 'red' for p in profits]
    
    # Tạo biểu đồ
    plt.figure(figsize=(14, 8))
    bars = plt.bar(range(len(symbols)), profits, color=colors)
    
    # Thêm nhãn trên mỗi cột
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., 
                height + 0.1 if height >= 0 else height - 0.6,
                f'{profits[i]:.2f}%\n{tf_risk[i]}', 
                ha='center', va='bottom' if height >= 0 else 'top',
                color='black' if height >= 0 else 'white',
                fontsize=10)
    
    plt.title('Top 10 cặp tiền có hiệu suất tốt nhất', fontsize=16)
    plt.xlabel('Cặp tiền', fontsize=14)
    plt.ylabel('Lợi nhuận (%)', fontsize=14)
    plt.xticks(range(len(symbols)), symbols, fontsize=12, rotation=45)
    plt.yticks(fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("risk_analysis/charts/best_performers.png")
    plt.close()

def create_risk_profit_heatmap(summary_data: Dict) -> None:
    """
    Tạo heat map lợi nhuận theo mức rủi ro và cặp tiền
    
    Args:
        summary_data (Dict): Dữ liệu tổng hợp
    """
    if not summary_data or "symbols" not in summary_data:
        return
    
    # Chọn khung thời gian (ưu tiên 1h nếu có)
    tf_priority = ['1h', '4h']
    selected_tf = None
    
    for symbol_data in summary_data["symbols"].values():
        for tf in tf_priority:
            if tf in symbol_data:
                selected_tf = tf
                break
        if selected_tf:
            break
    
    if not selected_tf:
        timeframes = set()
        for symbol_data in summary_data["symbols"].values():
            timeframes.update(symbol_data.keys())
        if timeframes:
            selected_tf = list(timeframes)[0]
        else:
            return
    
    logger.info(f"Tạo heat map cho khung thời gian {selected_tf}...")
    
    # Chuẩn bị dữ liệu
    symbols = []
    
    for symbol, symbol_data in summary_data["symbols"].items():
        if selected_tf in symbol_data:
            symbols.append(symbol)
    
    if not symbols:
        return
        
    # Tạo ma trận dữ liệu
    risk_profit_data = np.zeros((len(RISK_LEVELS), len(symbols)))
    
    for i, risk in enumerate(RISK_LEVELS):
        for j, symbol in enumerate(symbols):
            risk_str = str(risk)
            tf_data = summary_data["symbols"][symbol].get(selected_tf, {})
            
            if risk_str in tf_data:
                risk_profit_data[i, j] = tf_data[risk_str].get("profit_pct", 0)
    
    # Tạo short names cho cặp tiền
    symbols_short = [symbol.replace("USDT", "") for symbol in symbols]
    
    # Tạo heat map
    plt.figure(figsize=(18, 10))
    ax = plt.gca()
    
    # Tạo màu tùy chỉnh: đỏ cho âm, xanh lá cho dương
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'RedGreen', ['#d13c4b', '#ffffff', '#1e8449'])
    bounds = np.linspace(-10, 10, 21)  # Giới hạn từ -10% đến 10%
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    
    im = plt.imshow(risk_profit_data, cmap=cmap, norm=norm, aspect='auto', interpolation='nearest')
    plt.colorbar(im, label='Lợi nhuận (%)')
    
    # Thêm giá trị lên từng ô
    for i in range(len(RISK_LEVELS)):
        for j in range(len(symbols_short)):
            value = risk_profit_data[i, j]
            text_color = "black" if -2.5 < value < 2.5 else "white"
            text = plt.text(j, i, f"{value:.1f}",
                           ha="center", va="center", 
                           color=text_color, fontsize=10)
    
    plt.title(f'Heat Map: Lợi nhuận (%) theo mức rủi ro và cặp tiền ({selected_tf})', fontsize=16)
    plt.ylabel('Mức rủi ro (%)', fontsize=14)
    plt.xlabel('Cặp tiền', fontsize=14)
    plt.yticks(range(len(RISK_LEVELS)), [f"{risk}%" for risk in RISK_LEVELS], fontsize=12)
    plt.xticks(range(len(symbols_short)), symbols_short, fontsize=12, rotation=45)
    
    # Đặt đường kẻ grid cho bảng
    ax.set_xticks(np.arange(-0.5, len(symbols_short), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(RISK_LEVELS), 1), minor=True)
    ax.grid(which='minor', color='black', linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    plt.savefig(f"risk_analysis/charts/risk_profit_heatmap_{selected_tf}.png")
    plt.close()

def calculate_risk_correlations(summary_data: Dict) -> Dict:
    """
    Tính tương quan giữa mức rủi ro và lợi nhuận
    
    Args:
        summary_data (Dict): Dữ liệu tổng hợp
        
    Returns:
        Dict: Tương quan theo cặp tiền
    """
    if not summary_data or "symbols" not in summary_data:
        return {}
    
    correlations = {}
    
    for symbol, tf_data in summary_data["symbols"].items():
        symbol_correlations = {}
        
        for tf, risk_data in tf_data.items():
            risks = []
            profits = []
            
            for risk_str, metrics in risk_data.items():
                try:
                    risk = float(risk_str)
                    profit = metrics.get("profit_pct", 0)
                    
                    risks.append(risk)
                    profits.append(profit)
                except:
                    continue
            
            if len(risks) > 1:
                # Tính tương quan
                try:
                    correlation = np.corrcoef(risks, profits)[0, 1]
                    symbol_correlations[tf] = correlation
                except:
                    pass
        
        if symbol_correlations:
            correlations[symbol] = symbol_correlations
    
    return correlations

def generate_risk_recommendations(summary_data: Dict, correlations: Dict) -> Dict:
    """
    Tạo khuyến nghị mức rủi ro tối ưu
    
    Args:
        summary_data (Dict): Dữ liệu tổng hợp
        correlations (Dict): Tương quan mức rủi ro vs lợi nhuận
        
    Returns:
        Dict: Khuyến nghị
    """
    if not summary_data or "risk_analysis" not in summary_data:
        return {}
    
    optimal_risks = summary_data["risk_analysis"].get("optimal_risk_by_symbol", {})
    
    recommendations = {
        "global": {
            "optimal_risk": 0,
            "description": "",
            "rationale": ""
        },
        "by_symbol": {}
    }
    
    # Tính mức rủi ro trung bình tối ưu
    if optimal_risks:
        avg_risk = sum(optimal_risks.values()) / len(optimal_risks)
        recommendations["global"]["optimal_risk"] = avg_risk
        
        # Phân loại xu hướng rủi ro
        positive_corr = 0
        negative_corr = 0
        neutral_corr = 0
        
        for symbol, tf_corrs in correlations.items():
            for tf, corr in tf_corrs.items():
                if corr > 0.5:
                    positive_corr += 1
                elif corr < -0.5:
                    negative_corr += 1
                else:
                    neutral_corr += 1
        
        if positive_corr > negative_corr and positive_corr > neutral_corr:
            trend = "tăng rủi ro tăng lợi nhuận"
            recommendations["global"]["description"] = f"Xu hướng tổng thể: {trend}. Nên sử dụng mức rủi ro {max(RISK_LEVELS):.1f}%"
            recommendations["global"]["rationale"] = "Phần lớn các cặp tiền có lợi nhuận tăng khi tăng mức rủi ro"
        elif negative_corr > positive_corr and negative_corr > neutral_corr:
            trend = "tăng rủi ro giảm lợi nhuận"
            recommendations["global"]["description"] = f"Xu hướng tổng thể: {trend}. Nên sử dụng mức rủi ro {min(RISK_LEVELS):.1f}%"
            recommendations["global"]["rationale"] = "Phần lớn các cặp tiền có lợi nhuận giảm khi tăng mức rủi ro"
        else:
            trend = "không rõ ràng"
            recommendations["global"]["description"] = f"Xu hướng tổng thể: {trend}. Nên sử dụng mức rủi ro trung bình {avg_risk:.1f}%"
            recommendations["global"]["rationale"] = "Mức rủi ro tối ưu phụ thuộc vào từng cặp tiền cụ thể"
    
    # Tạo khuyến nghị cho từng cặp tiền
    for symbol, tf_corrs in correlations.items():
        if symbol not in optimal_risks:
            continue
            
        optimal_risk = optimal_risks[symbol]
        avg_corr = sum(tf_corrs.values()) / len(tf_corrs)
        
        recommendation = {
            "optimal_risk": optimal_risk,
            "correlation": avg_corr,
            "description": ""
        }
        
        if avg_corr > 0.7:
            recommendation["description"] = f"Tương quan mạnh dương ({avg_corr:.2f}): Có thể tăng rủi ro để tăng lợi nhuận"
        elif avg_corr < -0.7:
            recommendation["description"] = f"Tương quan mạnh âm ({avg_corr:.2f}): Nên giảm rủi ro để tăng lợi nhuận"
        elif avg_corr > 0.3:
            recommendation["description"] = f"Tương quan dương nhẹ ({avg_corr:.2f}): Mức rủi ro {optimal_risk}% là phù hợp"
        elif avg_corr < -0.3:
            recommendation["description"] = f"Tương quan âm nhẹ ({avg_corr:.2f}): Mức rủi ro {optimal_risk}% là phù hợp"
        else:
            recommendation["description"] = f"Tương quan yếu ({avg_corr:.2f}): Mức rủi ro {optimal_risk}% là tối ưu"
        
        recommendations["by_symbol"][symbol] = recommendation
    
    return recommendations

def generate_html_report(summary_data: Dict, correlations: Dict, recommendations: Dict) -> str:
    """
    Tạo báo cáo HTML
    
    Args:
        summary_data (Dict): Dữ liệu tổng hợp
        correlations (Dict): Tương quan mức rủi ro vs lợi nhuận
        recommendations (Dict): Khuyến nghị
        
    Returns:
        str: Nội dung HTML
    """
    # CSS style cho báo cáo
    css = """
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
        h2 { color: #3498db; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
        h3 { color: #2980b9; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: center; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        tr:hover { background-color: #f5f5f5; }
        .positive { color: green; }
        .negative { color: red; }
        .neutral { color: orange; }
        .summary-box { background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; }
        .chart-container { text-align: center; margin: 30px 0; }
        .chart-container img { max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }
        .recommendation { background-color: #e8f4fd; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; }
    </style>
    """
    
    # Tạo phần header
    header = f"""
    <h1>Báo Cáo Phân Tích Rủi Ro Đa Mức</h1>
    <p style="text-align: center;">Phân tích hiệu suất giao dịch từ thử nghiệm 3 tháng với 5 mức rủi ro khác nhau</p>
    <p style="text-align: center;"><em>Thời gian tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
    """
    
    # Tạo phần tổng quan
    overview = """
    <h2>Tổng Quan</h2>
    """
    
    if summary_data:
        total_symbols = summary_data.get("total_symbols", 0)
        total_timeframes = summary_data.get("total_timeframes", 0)
        total_risk_levels = summary_data.get("total_risk_levels", 0)
        
        overview += f"""
        <div class="summary-box">
            <p><strong>Tổng số cặp tiền:</strong> {total_symbols}</p>
            <p><strong>Số khung thời gian:</strong> {total_timeframes}</p>
            <p><strong>Số mức rủi ro:</strong> {total_risk_levels}</p>
        </div>
        """
    
    # Thêm biểu đồ phân phối mức rủi ro tối ưu
    overview += """
    <h3>Phân Phối Mức Rủi Ro Tối Ưu</h3>
    <div class="chart-container">
        <img src="charts/optimal_risk_distribution.png" alt="Phân phối mức rủi ro tối ưu">
    </div>
    """
    
    # Thêm biểu đồ top performers
    overview += """
    <h3>Top 10 Cặp Tiền Có Hiệu Suất Tốt Nhất</h3>
    <div class="chart-container">
        <img src="charts/best_performers.png" alt="Top 10 cặp tiền có hiệu suất tốt nhất">
    </div>
    """
    
    # Thêm heat map
    overview += """
    <h3>Heat Map: Lợi Nhuận Theo Mức Rủi Ro</h3>
    <div class="chart-container">
        <img src="charts/risk_profit_heatmap_1h.png" alt="Heat map lợi nhuận theo mức rủi ro và cặp tiền">
    </div>
    """
    
    # Tạo phần khuyến nghị
    recommendation_section = """
    <h2>Khuyến Nghị Mức Rủi Ro</h2>
    """
    
    if recommendations and "global" in recommendations:
        global_rec = recommendations["global"]
        
        recommendation_section += f"""
        <div class="recommendation">
            <h3>Khuyến Nghị Tổng Thể</h3>
            <p><strong>Mức rủi ro tối ưu:</strong> {global_rec["optimal_risk"]:.2f}%</p>
            <p><strong>Mô tả:</strong> {global_rec["description"]}</p>
            <p><strong>Lý do:</strong> {global_rec["rationale"]}</p>
        </div>
        """
    
    # Tạo bảng khuyến nghị theo cặp tiền
    if recommendations and "by_symbol" in recommendations:
        symbol_recs = recommendations["by_symbol"]
        
        if symbol_recs:
            recommendation_section += """
            <h3>Khuyến Nghị Theo Cặp Tiền</h3>
            <table>
                <tr>
                    <th>Cặp Tiền</th>
                    <th>Mức Rủi Ro Tối Ưu</th>
                    <th>Tương Quan</th>
                    <th>Mô Tả</th>
                </tr>
            """
            
            for symbol, rec in symbol_recs.items():
                corr = rec.get("correlation", 0)
                corr_class = "positive" if corr > 0.3 else "negative" if corr < -0.3 else "neutral"
                
                recommendation_section += f"""
                <tr>
                    <td>{symbol}</td>
                    <td>{rec["optimal_risk"]}%</td>
                    <td class="{corr_class}">{corr:.2f}</td>
                    <td>{rec["description"]}</td>
                </tr>
                """
            
            recommendation_section += """
            </table>
            """
    
    # Tạo phần chi tiết
    detail_section = """
    <h2>Chi Tiết Theo Cặp Tiền</h2>
    """
    
    if summary_data and "symbols" in summary_data:
        for symbol in summary_data["symbols"]:
            detail_section += f"""
            <h3>{symbol}</h3>
            <div class="chart-container">
                <img src="charts/{symbol}_1h_risk_profit.png" alt="{symbol} lợi nhuận theo mức rủi ro">
            </div>
            <div class="chart-container">
                <img src="charts/{symbol}_1h_pf_winrate.png" alt="{symbol} profit factor và win rate">
            </div>
            """
    
    # Tạo phần kết luận
    conclusion = """
    <h2>Kết Luận</h2>
    <p>Dựa trên kết quả phân tích các mức rủi ro khác nhau trên tất cả các cặp tiền, có thể rút ra một số kết luận sau:</p>
    <ol>
        <li>Mức rủi ro tối ưu khác nhau giữa các cặp tiền và phụ thuộc vào đặc tính của mỗi thị trường.</li>
        <li>Một số cặp tiền có xu hướng lợi nhuận tăng khi tăng rủi ro, trong khi các cặp khác có xu hướng ngược lại.</li>
        <li>Việc điều chỉnh mức rủi ro phù hợp cho từng cặp tiền có thể cải thiện đáng kể hiệu suất tổng thể của hệ thống.</li>
        <li>Mỗi mức rủi ro có những ưu và nhược điểm khác nhau, cần cân nhắc kỹ dựa trên mục tiêu đầu tư và khẩu vị rủi ro.</li>
    </ol>
    """
    
    # Kết hợp các phần
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Báo Cáo Phân Tích Rủi Ro Đa Mức</title>
        {css}
    </head>
    <body>
        {header}
        {overview}
        {recommendation_section}
        {detail_section}
        {conclusion}
    </body>
    </html>
    """
    
    return html_content

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Tạo báo cáo phân tích rủi ro')
    parser.add_argument('--input', default='backtest_summary/multi_risk_summary.json', help='File dữ liệu đầu vào')
    parser.add_argument('--output', default='risk_analysis/risk_analysis_report.html', help='File báo cáo đầu ra')
    args = parser.parse_args()
    
    # Tải dữ liệu
    summary_data = load_summary_data(args.input)
    
    if not summary_data:
        logger.error("Không thể tải dữ liệu tổng hợp, kết thúc")
        return
    
    logger.info("Tạo biểu đồ phân tích rủi ro...")
    
    # Tạo các biểu đồ
    create_risk_performance_charts(summary_data)
    create_optimal_risk_distribution_chart(summary_data)
    create_best_performers_chart(summary_data)
    create_risk_profit_heatmap(summary_data)
    
    # Tính tương quan
    correlations = calculate_risk_correlations(summary_data)
    
    # Tạo khuyến nghị
    recommendations = generate_risk_recommendations(summary_data, correlations)
    
    # Tạo báo cáo HTML
    html_content = generate_html_report(summary_data, correlations, recommendations)
    
    # Lưu báo cáo
    with open(args.output, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Đã lưu báo cáo HTML: {args.output}")
    
    # Lưu khuyến nghị dưới dạng JSON
    with open("risk_analysis/risk_recommendations.json", 'w') as f:
        json.dump(recommendations, f, indent=4)
    
    logger.info("Đã lưu khuyến nghị: risk_analysis/risk_recommendations.json")

if __name__ == "__main__":
    main()