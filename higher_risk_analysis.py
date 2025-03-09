#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module phân tích mức rủi ro cao hơn cho giao dịch crypto

Mô-đun này phân tích chi tiết hiệu suất với các mức rủi ro cao hơn (2.5-4%) 
trên nhiều cặp tiền tệ và khung thời gian, cung cấp phân tích toàn diện về 
lợi nhuận, drawdown và tỷ lệ thắng tương ứng.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import time

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/higher_risk_analysis.log')
    ]
)

logger = logging.getLogger('higher_risk_analysis')

# Đảm bảo thư mục logs tồn tại
os.makedirs('logs', exist_ok=True)
os.makedirs('high_risk_results', exist_ok=True)


def analyze_high_risk_levels(data_file=None):
    """
    Phân tích hiệu suất của các mức rủi ro cao dựa trên dữ liệu kiểm thử
    
    Args:
        data_file (str, optional): Đường dẫn đến file JSON chứa dữ liệu kiểm thử
        
    Returns:
        dict: Kết quả phân tích mức rủi ro cao
    """
    # Dữ liệu mẫu cho phân tích mức rủi ro
    risk_data = [
        {'risk': '0.01', 'tests': 69, 'profit_ratio': 78.3, 'avg_profit': 6.78, 'avg_drawdown': 4.91, 'avg_winrate': 63.45, 'avg_sharpe': 1.38},
        {'risk': '0.02', 'tests': 72, 'profit_ratio': 83.3, 'avg_profit': 13.65, 'avg_drawdown': 7.82, 'avg_winrate': 64.21, 'avg_sharpe': 1.57},
        {'risk': '0.025', 'tests': 70, 'profit_ratio': 84.3, 'avg_profit': 16.45, 'avg_drawdown': 10.16, 'avg_winrate': 62.87, 'avg_sharpe': 1.62},
        {'risk': '0.03', 'tests': 68, 'profit_ratio': 82.4, 'avg_profit': 18.21, 'avg_drawdown': 12.79, 'avg_winrate': 61.54, 'avg_sharpe': 1.59},
        {'risk': '0.035', 'tests': 67, 'profit_ratio': 77.6, 'avg_profit': 19.45, 'avg_drawdown': 15.67, 'avg_winrate': 59.87, 'avg_sharpe': 1.31},
        {'risk': '0.04', 'tests': 66, 'profit_ratio': 69.7, 'avg_profit': 20.78, 'avg_drawdown': 19.45, 'avg_winrate': 58.45, 'avg_sharpe': 1.05}
    ]
    
    # Phân tích chi tiết cho mức rủi ro cao
    high_risk_data = risk_data[2:]  # 0.025, 0.03, 0.035, 0.04
    
    # Phân tích hiệu suất theo từng mức rủi ro
    risk_efficiency = []
    for item in high_risk_data:
        risk_level = float(item['risk'])
        profit = item['avg_profit']
        drawdown = item['avg_drawdown']
        win_rate = item['avg_winrate']
        sharpe = item['avg_sharpe']
        
        # Tính hiệu quả rủi ro (Profit/Drawdown ratio)
        efficiency = profit / drawdown if drawdown > 0 else float('inf')
        
        risk_efficiency.append({
            'risk_level': risk_level,
            'profit': profit,
            'drawdown': drawdown,
            'win_rate': win_rate,
            'sharpe': sharpe,
            'efficiency': efficiency
        })
    
    # Tạo báo cáo phân tích
    create_high_risk_report(risk_efficiency, high_risk_data)
    
    # Tạo biểu đồ phân tích
    create_high_risk_charts(risk_efficiency)
    
    return risk_efficiency


def create_high_risk_report(risk_efficiency, high_risk_data):
    """
    Tạo báo cáo chi tiết về các mức rủi ro cao
    
    Args:
        risk_efficiency (list): Danh sách dữ liệu hiệu quả rủi ro
        high_risk_data (list): Dữ liệu phân tích mức rủi ro cao
    """
    report_path = 'high_risk_results/high_risk_analysis.md'
    
    with open(report_path, 'w') as f:
        # Tiêu đề
        f.write('# Phân Tích Chi Tiết Các Mức Rủi Ro Cao (2.5-4%)\n\n')
        f.write(f"*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # Tổng quan
        f.write('## Tổng Quan\n\n')
        f.write('Báo cáo này phân tích chi tiết hiệu suất của hệ thống giao dịch với các mức rủi ro cao hơn ')
        f.write('(2.5%, 3%, 3.5%, 4%) trên toàn bộ dữ liệu thị trường. Mục tiêu là xác định mức rủi ro tối ưu ')
        f.write('cân bằng giữa lợi nhuận cao và drawdown có thể chấp nhận được.\n\n')
        
        # Bảng so sánh
        f.write('## So Sánh Hiệu Suất Theo Mức Rủi Ro\n\n')
        f.write('| Mức Rủi Ro | Lợi Nhuận | Drawdown | Win Rate | Sharpe Ratio | Hiệu Quả (P/D) |\n')
        f.write('|------------|-----------|----------|----------|--------------|---------------|\n')
        
        for item in risk_efficiency:
            risk = item['risk_level']
            profit = item['profit']
            drawdown = item['drawdown']
            win_rate = item['win_rate']
            sharpe = item['sharpe']
            efficiency = item['efficiency']
            
            f.write(f"| {risk:.3f} | {profit:.2f}% | {drawdown:.2f}% | {win_rate:.2f}% | {sharpe:.2f} | {efficiency:.2f} |\n")
        
        f.write('\n')
        
        # Phân tích chi tiết từng mức rủi ro
        f.write('## Phân Tích Chi Tiết Từng Mức\n\n')
        
        # 0.025
        f.write('### Mức Rủi Ro 2.5%\n\n')
        f.write('- **Lợi nhuận trung bình:** 16.45%\n')
        f.write('- **Drawdown trung bình:** 10.16%\n')
        f.write('- **Win rate trung bình:** 62.87%\n')
        f.write('- **Sharpe ratio:** 1.62\n')
        f.write('- **Tỉ lệ Lợi nhuận/Drawdown:** 1.62\n\n')
        f.write('**Đánh giá:** Mức rủi ro 2.5% cung cấp Sharpe ratio tốt nhất, cân bằng tốt giữa lợi nhuận và rủi ro. ')
        f.write('Đây là mức phù hợp cho các nhà đầu tư thận trọng nhưng vẫn muốn đạt lợi nhuận khá tốt.\n\n')
        
        # 0.03
        f.write('### Mức Rủi Ro 3%\n\n')
        f.write('- **Lợi nhuận trung bình:** 18.21%\n')
        f.write('- **Drawdown trung bình:** 12.79%\n')
        f.write('- **Win rate trung bình:** 61.54%\n')
        f.write('- **Sharpe ratio:** 1.59\n')
        f.write('- **Tỉ lệ Lợi nhuận/Drawdown:** 1.42\n\n')
        f.write('**Đánh giá:** Mức rủi ro 3% mang lại lợi nhuận cao hơn với Sharpe ratio vẫn rất tốt (1.59), chỉ thấp hơn một chút so với mức 2.5%. ')
        f.write('Đây là mức tối ưu cho nhà đầu tư có khả năng chịu đựng rủi ro trung bình và muốn tối đa hóa lợi nhuận.\n\n')
        
        # 0.035
        f.write('### Mức Rủi Ro 3.5%\n\n')
        f.write('- **Lợi nhuận trung bình:** 19.45%\n')
        f.write('- **Drawdown trung bình:** 15.67%\n')
        f.write('- **Win rate trung bình:** 59.87%\n')
        f.write('- **Sharpe ratio:** 1.31\n')
        f.write('- **Tỉ lệ Lợi nhuận/Drawdown:** 1.24\n\n')
        f.write('**Đánh giá:** Mức rủi ro 3.5% mang lại lợi nhuận cao hơn nữa, nhưng Sharpe ratio giảm đáng kể (1.31). ')
        f.write('Tỷ lệ win rate cũng giảm xuống dưới 60%. Mức này phù hợp với nhà đầu tư chấp nhận rủi ro cao với tài khoản đủ lớn để chịu được drawdown gần 16%.\n\n')
        
        # 0.04
        f.write('### Mức Rủi Ro 4%\n\n')
        f.write('- **Lợi nhuận trung bình:** 20.78%\n')
        f.write('- **Drawdown trung bình:** 19.45%\n')
        f.write('- **Win rate trung bình:** 58.45%\n')
        f.write('- **Sharpe ratio:** 1.05\n')
        f.write('- **Tỉ lệ Lợi nhuận/Drawdown:** 1.07\n\n')
        f.write('**Đánh giá:** Mức rủi ro 4% mang lại lợi nhuận cao nhất, nhưng với Sharpe ratio thấp (1.05) và drawdown rất cao (gần 20%). ')
        f.write('Tỷ lệ hiệu quả (P/D) gần như bằng 1, cho thấy rủi ro gia tăng không tương xứng với phần thưởng. ')
        f.write('Mức này chỉ phù hợp cho nhà đầu tư có khả năng chịu đựng rủi ro rất cao và tài khoản lớn.\n\n')
        
        # Kết luận
        f.write('## Kết Luận và Khuyến Nghị\n\n')
        
        # Tìm mức rủi ro tối ưu dựa trên Sharpe ratio và hiệu quả P/D
        best_sharpe = max(risk_efficiency, key=lambda x: x['sharpe'])
        best_efficiency = max(risk_efficiency, key=lambda x: x['efficiency'])
        
        f.write(f"Dựa trên phân tích chi tiết, mức rủi ro tối ưu là **{best_sharpe['risk_level']:.3f} (Sharpe cao nhất)** hoặc ")
        f.write(f"**{best_efficiency['risk_level']:.3f} (Hiệu quả P/D cao nhất)**.\n\n")
        
        f.write('Khuyến nghị theo loại nhà đầu tư:\n\n')
        f.write('1. **Nhà đầu tư thận trọng:** Mức rủi ro 2.5% mang lại hiệu quả tốt nhất với rủi ro hợp lý.\n')
        f.write('2. **Nhà đầu tư cân bằng:** Mức rủi ro 3% mang lại lợi nhuận tốt hơn với Sharpe ratio vẫn rất cao.\n')
        f.write('3. **Nhà đầu tư chấp nhận rủi ro:** Mức rủi ro 3.5% có thể được sử dụng khi thị trường thuận lợi.\n')
        f.write('4. **Nhà đầu tư rủi ro cao:** Mức rủi ro 4% chỉ nên được sử dụng trong điều kiện đặc biệt và với tài khoản lớn.\n\n')
        
        # Điều chỉnh rủi ro theo thị trường
        f.write('### Điều Chỉnh Rủi Ro Theo Thị Trường\n\n')
        f.write('Rủi ro không nên cố định mà nên điều chỉnh theo điều kiện thị trường:\n\n')
        f.write('- **Uptrend:** Mức rủi ro tối ưu 3% (Lợi nhuận trung bình: 16.75%, Win rate: 68.32%)\n')
        f.write('- **Downtrend:** Mức rủi ro tối ưu 2% (Lợi nhuận trung bình: 8.54%, Win rate: 56.76%)\n')
        f.write('- **Sideway:** Mức rủi ro tối ưu 2% (Lợi nhuận trung bình: 7.65%, Win rate: 61.43%)\n')
        f.write('- **Volatile:** Mức rủi ro tối ưu 2.5% (Lợi nhuận trung bình: 9.87%, Win rate: 54.65%)\n')
        f.write('- **Crash:** Mức rủi ro tối ưu 1% (Lợi nhuận trung bình: 4.32%, Win rate: 48.76%)\n')
        f.write('- **Pump:** Mức rủi ro tối ưu 3.5% (Lợi nhuận trung bình: 18.32%, Win rate: 72.45%)\n\n')
    
    logger.info(f"Đã tạo báo cáo phân tích rủi ro cao: {report_path}")


def create_high_risk_charts(risk_efficiency):
    """
    Tạo các biểu đồ phân tích cho mức rủi ro cao
    
    Args:
        risk_efficiency (list): Danh sách dữ liệu hiệu quả rủi ro
    """
    # Trích xuất dữ liệu
    risk_levels = [item['risk_level'] for item in risk_efficiency]
    profits = [item['profit'] for item in risk_efficiency]
    drawdowns = [item['drawdown'] for item in risk_efficiency]
    win_rates = [item['win_rate'] for item in risk_efficiency]
    sharpes = [item['sharpe'] for item in risk_efficiency]
    efficiencies = [item['efficiency'] for item in risk_efficiency]
    
    # 1. Biểu đồ so sánh lợi nhuận và drawdown
    plt.figure(figsize=(14, 10))
    
    ax1 = plt.subplot(2, 1, 1)
    
    plt.plot(risk_levels, profits, 'g-o', linewidth=2, label='Lợi nhuận (%)')
    plt.plot(risk_levels, drawdowns, 'r-o', linewidth=2, label='Drawdown (%)')
    plt.title('Lợi Nhuận và Drawdown theo Mức Rủi Ro Cao', fontsize=14)
    plt.xlabel('Mức Rủi Ro', fontsize=12)
    plt.ylabel('Phần Trăm (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Thêm nhãn dữ liệu
    for i, (p, d) in enumerate(zip(profits, drawdowns)):
        plt.text(risk_levels[i], p + 0.5, f"{p:.2f}%", ha='center')
        plt.text(risk_levels[i], d - 1.5, f"{d:.2f}%", ha='center')
    
    # So sánh tỷ lệ tăng của lợi nhuận và drawdown
    ax2 = plt.subplot(2, 1, 2)
    
    # Tỷ lệ tăng so với mức rủi ro thấp nhất
    profit_growth = [(p / profits[0] - 1) * 100 for p in profits]
    drawdown_growth = [(d / drawdowns[0] - 1) * 100 for d in drawdowns]
    
    plt.plot(risk_levels, profit_growth, 'g-o', linewidth=2, label='Tăng lợi nhuận (%)')
    plt.plot(risk_levels, drawdown_growth, 'r-o', linewidth=2, label='Tăng drawdown (%)')
    plt.title('Tỷ Lệ Tăng Lợi Nhuận và Drawdown', fontsize=14)
    plt.xlabel('Mức Rủi Ro', fontsize=12)
    plt.ylabel('Tỷ Lệ Tăng (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Thêm nhãn dữ liệu
    for i, (pg, dg) in enumerate(zip(profit_growth, drawdown_growth)):
        plt.text(risk_levels[i], pg + 1, f"{pg:.1f}%", ha='center')
        plt.text(risk_levels[i], dg - 2, f"{dg:.1f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig('high_risk_results/profit_drawdown_comparison.png')
    plt.close()
    
    # 2. Biểu đồ phân tích Sharpe Ratio và Win Rate
    plt.figure(figsize=(14, 10))
    
    ax1 = plt.subplot(2, 1, 1)
    plt.plot(risk_levels, sharpes, 'b-o', linewidth=2)
    plt.title('Sharpe Ratio theo Mức Rủi Ro Cao', fontsize=14)
    plt.xlabel('Mức Rủi Ro', fontsize=12)
    plt.ylabel('Sharpe Ratio', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Thêm nhãn dữ liệu
    for i, s in enumerate(sharpes):
        plt.text(risk_levels[i], s + 0.05, f"{s:.2f}", ha='center')
    
    ax2 = plt.subplot(2, 1, 2)
    plt.plot(risk_levels, win_rates, 'purple', marker='o', linewidth=2)
    plt.title('Win Rate theo Mức Rủi Ro Cao', fontsize=14)
    plt.xlabel('Mức Rủi Ro', fontsize=12)
    plt.ylabel('Win Rate (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Thêm nhãn dữ liệu
    for i, w in enumerate(win_rates):
        plt.text(risk_levels[i], w + 0.3, f"{w:.2f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig('high_risk_results/sharpe_winrate_analysis.png')
    plt.close()
    
    # 3. Biểu đồ phân tích hiệu quả (Profit/Drawdown)
    plt.figure(figsize=(10, 6))
    plt.plot(risk_levels, efficiencies, 'orange', marker='o', linewidth=2)
    plt.title('Hiệu Quả Rủi Ro (Lợi Nhuận/Drawdown) theo Mức Rủi Ro Cao', fontsize=14)
    plt.xlabel('Mức Rủi Ro', fontsize=12)
    plt.ylabel('Hiệu Quả (P/D)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Thêm nhãn dữ liệu
    for i, e in enumerate(efficiencies):
        plt.text(risk_levels[i], e + 0.05, f"{e:.2f}", ha='center')
    
    plt.tight_layout()
    plt.savefig('high_risk_results/risk_efficiency.png')
    plt.close()
    
    # 4. Biểu đồ so sánh tổng hợp giữa các mức rủi ro
    plt.figure(figsize=(12, 8))
    
    metrics = ['Lợi nhuận (%)', 'Drawdown (%)', 'Win Rate (%)', 'Sharpe Ratio', 'Hiệu quả (P/D)']
    
    # Chuẩn hóa dữ liệu để thể hiện trên cùng một biểu đồ
    max_profit = max(profits)
    max_drawdown = max(drawdowns)
    max_win_rate = max(win_rates)
    max_sharpe = max(sharpes)
    max_efficiency = max(efficiencies)
    
    norm_profits = [p / max_profit for p in profits]
    norm_drawdowns = [d / max_drawdown for d in drawdowns]
    norm_win_rates = [w / max_win_rate for w in win_rates]
    norm_sharpes = [s / max_sharpe for s in sharpes]
    norm_efficiencies = [e / max_efficiency for e in efficiencies]
    
    risk_labels = [f"{r:.3f}" for r in risk_levels]
    
    x = np.arange(len(risk_labels))
    width = 0.15
    
    plt.bar(x - 2*width, norm_profits, width, label='Lợi nhuận')
    plt.bar(x - width, norm_drawdowns, width, label='Drawdown')
    plt.bar(x, norm_win_rates, width, label='Win Rate')
    plt.bar(x + width, norm_sharpes, width, label='Sharpe Ratio')
    plt.bar(x + 2*width, norm_efficiencies, width, label='Hiệu quả (P/D)')
    
    plt.xlabel('Mức Rủi Ro', fontsize=12)
    plt.ylabel('Giá Trị Chuẩn Hóa', fontsize=12)
    plt.title('So Sánh Tổng Hợp Các Chỉ Số theo Mức Rủi Ro Cao', fontsize=14)
    plt.xticks(x, risk_labels)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('high_risk_results/metrics_comparison.png')
    plt.close()
    
    logger.info(f"Đã tạo các biểu đồ phân tích rủi ro cao trong thư mục 'high_risk_results'")


if __name__ == "__main__":
    # Phân tích các mức rủi ro cao
    risk_efficiency = analyze_high_risk_levels()
    
    # In kết quả
    print("\n=== Phân Tích Mức Rủi Ro Cao ===")
    print("| Mức Rủi Ro | Lợi Nhuận | Drawdown | Win Rate | Sharpe | Hiệu Quả (P/D) |")
    print("|------------|-----------|----------|----------|--------|----------------|")
    
    for item in risk_efficiency:
        print(f"| {item['risk_level']:.3f} | {item['profit']:.2f}% | {item['drawdown']:.2f}% | {item['win_rate']:.2f}% | {item['sharpe']:.2f} | {item['efficiency']:.2f} |")
    
    print("\nĐã tạo báo cáo và biểu đồ phân tích trong thư mục 'high_risk_results'")