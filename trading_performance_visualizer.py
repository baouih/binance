#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo biểu đồ so sánh hiệu suất đa mức rủi ro

Script này tạo các biểu đồ so sánh hiệu suất giữa các mức rủi ro khác nhau
sử dụng dữ liệu từ các file kết quả backtest.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.ticker import FuncFormatter
import seaborn as sns
from typing import Dict, List, Any

# Đảm bảo thư mục đầu ra tồn tại
os.makedirs("risk_analysis", exist_ok=True)

# Thiết lập style cho biểu đồ
sns.set(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

def percent_formatter(x, pos):
    """Format số dạng phần trăm"""
    return f'{x:.1f}%'

def load_backtest_results(symbol: str = 'BTCUSDT', interval: str = '1h') -> Dict[float, Dict]:
    """
    Tải kết quả backtest cho các mức rủi ro khác nhau
    
    Args:
        symbol (str): Mã cặp tiền
        interval (str): Khung thời gian
        
    Returns:
        Dict[float, Dict]: Ánh xạ mức rủi ro -> kết quả backtest
    """
    results = {}
    backtest_dir = 'backtest_results'
    
    # Tìm các file kết quả với mức rủi ro khác nhau
    for filename in os.listdir(backtest_dir):
        if filename.startswith(f"{symbol}_{interval}_risk"):
            try:
                parts = filename.split('_')
                risk_str = parts[2][4:].replace('_', '.')
                risk = float(risk_str)
                
                file_path = os.path.join(backtest_dir, filename)
                with open(file_path, 'r') as f:
                    results[risk] = json.load(f)
            except Exception as e:
                print(f"Lỗi khi tải file {filename}: {str(e)}")
                
    # Thử tìm file kết quả với rủi ro 0.5%
    risk05_file = os.path.join(backtest_dir, f"{symbol}_{interval}_risk0_5_results.json")
    if os.path.exists(risk05_file):
        try:
            with open(risk05_file, 'r') as f:
                results[0.5] = json.load(f)
        except Exception as e:
            print(f"Lỗi khi tải risk0_5_results.json: {str(e)}")
    
    # Thêm adaptive_results nếu có (mức rủi ro 1.5%)
    adaptive_file = os.path.join(backtest_dir, f"{symbol}_{interval}_adaptive_results.json")
    if os.path.exists(adaptive_file):
        try:
            with open(adaptive_file, 'r') as f:
                adaptive_data = json.load(f)
                risk_value = adaptive_data.get('risk_percentage', 1.5)
                if risk_value not in results:
                    results[risk_value] = adaptive_data
        except Exception as e:
            print(f"Lỗi khi tải adaptive_results: {str(e)}")
    
    return results

def create_performance_comparison_chart(results: Dict[float, Dict], output_path: str = 'risk_analysis/performance_comparison.png'):
    """
    Tạo biểu đồ so sánh hiệu suất của các mức rủi ro
    
    Args:
        results (Dict[float, Dict]): Kết quả backtest theo mức rủi ro
        output_path (str): Đường dẫn file đầu ra
    """
    if not results:
        print("Không có dữ liệu để tạo biểu đồ")
        return
    
    # Chuẩn bị dữ liệu
    risks = []
    profits = []
    win_rates = []
    profit_factors = []
    max_drawdowns = []
    avg_profits = []
    
    for risk, result in sorted(results.items()):
        risks.append(risk)
        profits.append(result.get('profit_percentage', 0) * 100)  # Convert to %
        win_rates.append(result.get('win_rate', 0))
        pf = result.get('profit_factor', 0)
        profit_factors.append(min(pf, 10) if pf != float('inf') else 10)  # Cap at 10 for visualization
        max_drawdowns.append(result.get('max_drawdown', 0) * 100)  # Convert to %
        avg_profits.append(result.get('avg_profit', 0))
    
    # Tạo dataframe
    df = pd.DataFrame({
        'Risk (%)': risks,
        'Profit (%)': profits,
        'Win Rate (%)': win_rates,
        'Profit Factor': profit_factors,
        'Max Drawdown (%)': max_drawdowns,
        'Avg Profit Per Trade': avg_profits
    })
    
    # Tạo biểu đồ
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    plt.subplots_adjust(hspace=0.3, wspace=0.3)
    
    # Biểu đồ 1: Lợi nhuận
    ax1 = axes[0, 0]
    bars1 = ax1.bar(df['Risk (%)'], df['Profit (%)'], color='skyblue')
    ax1.set_title('Lợi nhuận theo Mức Rủi ro', fontweight='bold')
    ax1.set_xlabel('Mức Rủi ro (%)')
    ax1.set_ylabel('Lợi nhuận (%)')
    ax1.yaxis.set_major_formatter(FuncFormatter(percent_formatter))
    
    # Thêm giá trị trên thanh
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{height:.2f}%', ha='center', va='bottom')
    
    # Biểu đồ 2: Win Rate
    ax2 = axes[0, 1]
    bars2 = ax2.bar(df['Risk (%)'], df['Win Rate (%)'], color='lightgreen')
    ax2.set_title('Tỷ lệ Thắng theo Mức Rủi ro', fontweight='bold')
    ax2.set_xlabel('Mức Rủi ro (%)')
    ax2.set_ylabel('Tỷ lệ Thắng (%)')
    ax2.set_ylim(0, 110)  # Để có không gian cho giá trị trên thanh
    ax2.yaxis.set_major_formatter(FuncFormatter(percent_formatter))
    
    # Thêm giá trị trên thanh
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.1f}%', ha='center', va='bottom')
    
    # Biểu đồ 3: Profit Factor & Max Drawdown
    ax3 = axes[1, 0]
    ax3_2 = ax3.twinx()
    
    bars3 = ax3.bar(df['Risk (%)'], df['Profit Factor'], color='orange', alpha=0.7, label='Profit Factor')
    bars3_2 = ax3_2.bar(df['Risk (%)'], df['Max Drawdown (%)'], color='red', alpha=0.5, width=0.4, label='Max Drawdown')
    
    ax3.set_title('Profit Factor & Max Drawdown theo Mức Rủi ro', fontweight='bold')
    ax3.set_xlabel('Mức Rủi ro (%)')
    ax3.set_ylabel('Profit Factor')
    ax3_2.set_ylabel('Max Drawdown (%)')
    ax3.set_ylim(0, max(df['Profit Factor']) * 1.2)
    ax3_2.set_ylim(0, max(max(df['Max Drawdown (%)']), 0.5) * 1.5)
    ax3_2.yaxis.set_major_formatter(FuncFormatter(percent_formatter))
    
    # Thêm giá trị trên thanh
    for bar in bars3:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.1f}', ha='center', va='bottom')
    
    # Thêm legend
    lines, labels = ax3.get_legend_handles_labels()
    lines2, labels2 = ax3_2.get_legend_handles_labels()
    ax3.legend(lines + lines2, labels + labels2, loc='upper right')
    
    # Biểu đồ 4: Lợi nhuận trung bình mỗi giao dịch
    ax4 = axes[1, 1]
    bars4 = ax4.bar(df['Risk (%)'], df['Avg Profit Per Trade'], color='purple')
    ax4.set_title('Lợi nhuận TB mỗi Giao dịch theo Mức Rủi ro', fontweight='bold')
    ax4.set_xlabel('Mức Rủi ro (%)')
    ax4.set_ylabel('Lợi nhuận TB (USDT)')
    
    # Thêm giá trị trên thanh
    for bar in bars4:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.2f}', ha='center', va='bottom')
    
    # Tiêu đề chính
    plt.suptitle(f'So sánh Hiệu suất Theo Mức Rủi ro - BTCUSDT 1h', fontsize=16, fontweight='bold')
    
    # Lưu biểu đồ
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Đã lưu biểu đồ so sánh hiệu suất tại {output_path}")
    plt.close()

def create_regime_performance_chart(results: Dict[float, Dict], output_path: str = 'risk_analysis/regime_performance.png'):
    """
    Tạo biểu đồ so sánh hiệu suất theo chế độ thị trường
    
    Args:
        results (Dict[float, Dict]): Kết quả backtest theo mức rủi ro
        output_path (str): Đường dẫn file đầu ra
    """
    if not results:
        print("Không có dữ liệu để tạo biểu đồ")
        return
    
    # Tìm tất cả các chế độ thị trường có trong kết quả
    all_regimes = set()
    for result in results.values():
        if 'regime_performance' in result:
            all_regimes.update(result['regime_performance'].keys())
    
    if not all_regimes:
        print("Không tìm thấy dữ liệu về chế độ thị trường")
        return
    
    # Chuẩn bị dữ liệu
    df_data = []
    
    for risk, result in sorted(results.items()):
        if 'regime_performance' not in result:
            continue
            
        for regime, perf in result['regime_performance'].items():
            df_data.append({
                'Risk': f"{risk}%",
                'Market Regime': regime.capitalize(),
                'Win Rate (%)': perf.get('win_rate', 0),
                'Profit (%)': perf.get('net_pnl_pct', 0) * 100,  # Convert to %
                'Trades': perf.get('trades', 0)
            })
    
    df = pd.DataFrame(df_data)
    
    # Tạo biểu đồ
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    
    # Biểu đồ 1: Win Rate theo chế độ thị trường và mức rủi ro
    sns.barplot(x='Market Regime', y='Win Rate (%)', hue='Risk', data=df, ax=axes[0])
    axes[0].set_title('Tỷ lệ Thắng theo Chế độ Thị trường', fontweight='bold')
    axes[0].set_ylim(0, 110)
    axes[0].yaxis.set_major_formatter(FuncFormatter(percent_formatter))
    
    # Biểu đồ 2: Lợi nhuận theo chế độ thị trường và mức rủi ro
    sns.barplot(x='Market Regime', y='Profit (%)', hue='Risk', data=df, ax=axes[1])
    axes[1].set_title('Lợi nhuận (%) theo Chế độ Thị trường', fontweight='bold')
    axes[1].yaxis.set_major_formatter(FuncFormatter(percent_formatter))
    
    # Tiêu đề chính
    plt.suptitle(f'So sánh Hiệu suất Theo Chế độ Thị trường - BTCUSDT 1h', fontsize=16, fontweight='bold')
    
    # Lưu biểu đồ
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Đã lưu biểu đồ chế độ thị trường tại {output_path}")
    plt.close()

def create_trade_metrics_chart(results: Dict[float, Dict], output_path: str = 'risk_analysis/trade_metrics.png'):
    """
    Tạo biểu đồ so sánh các chỉ số giao dịch
    
    Args:
        results (Dict[float, Dict]): Kết quả backtest theo mức rủi ro
        output_path (str): Đường dẫn file đầu ra
    """
    if not results:
        print("Không có dữ liệu để tạo biểu đồ")
        return
    
    # Chuẩn bị dữ liệu
    df_data = []
    
    for risk, result in sorted(results.items()):
        df_data.append({
            'Risk (%)': risk,
            'Total Trades': result.get('total_trades', 0),
            'Win Trades': result.get('win_trades', 0),
            'Lose Trades': result.get('lose_trades', 0)
        })
    
    df = pd.DataFrame(df_data)
    
    # Tạo dataframe dạng long form cho stacked bar chart
    df_long = pd.DataFrame({
        'Risk (%)': df['Risk (%)'].repeat(2),
        'Trade Type': ['Win'] * len(df) + ['Lose'] * len(df),
        'Count': list(df['Win Trades']) + list(df['Lose Trades'])
    })
    
    # Tạo biểu đồ
    plt.figure(figsize=(12, 8))
    
    # Tạo stacked bar chart
    sns.barplot(x='Risk (%)', y='Count', hue='Trade Type', data=df_long, palette=['forestgreen', 'crimson'])
    
    # Thêm tổng số giao dịch trên mỗi thanh
    for i, risk in enumerate(df['Risk (%)']):
        total = df.loc[i, 'Total Trades']
        plt.text(i, total + 0.5, f'Total: {total}', ha='center', fontweight='bold')
    
    plt.title('Phân tích Giao dịch Thắng/Thua theo Mức Rủi ro - BTCUSDT 1h', fontsize=16, fontweight='bold')
    plt.xlabel('Mức Rủi ro (%)')
    plt.ylabel('Số lượng Giao dịch')
    plt.legend(title='Loại Giao dịch')
    
    # Lưu biểu đồ
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Đã lưu biểu đồ chỉ số giao dịch tại {output_path}")
    plt.close()

def generate_all_charts(symbol: str = 'BTCUSDT', interval: str = '1h'):
    """
    Tạo tất cả các biểu đồ phân tích
    
    Args:
        symbol (str): Mã cặp tiền
        interval (str): Khung thời gian
    """
    results = load_backtest_results(symbol, interval)
    
    if not results:
        print(f"Không tìm thấy kết quả backtest cho {symbol} {interval}")
        return
    
    print(f"Đã tìm thấy {len(results)} mức rủi ro: {list(results.keys())}")
    
    create_performance_comparison_chart(results)
    create_regime_performance_chart(results)
    create_trade_metrics_chart(results)
    
    print("Đã tạo xong tất cả biểu đồ!")

if __name__ == "__main__":
    generate_all_charts()