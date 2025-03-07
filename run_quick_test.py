#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script để chạy backtest nhanh với khối lượng dữ liệu nhỏ hơn để kiểm thử
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, List, Any
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('quick_test.log')
    ]
)
logger = logging.getLogger('quick_test')

# Các mức rủi ro cần kiểm thử
RISK_LEVELS = [2.0, 2.5, 3.0, 4.0, 5.0]

def run_backtest(symbol: str, interval: str, risk_level: float, period_days: int = 14) -> Dict[str, Any]:
    """
    Chạy backtest với mức rủi ro cụ thể và khối lượng dữ liệu giảm
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        risk_level (float): Mức rủi ro (%)
        period_days (int): Số ngày dữ liệu muốn backtest (mặc định 14 ngày)
        
    Returns:
        Dict[str, Any]: Kết quả backtest
    """
    try:
        # Định dạng mức rủi ro cho tên file
        risk_str = str(risk_level).replace('.', '_')
        
        # Tính ngày bắt đầu và kết thúc
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        logger.info(f"Chạy backtest cho {symbol} với mức rủi ro {risk_level}% trên dữ liệu {period_days} ngày")
        logger.info(f"Khoảng thời gian: {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}")
        
        # Tạo thư mục backtest_results nếu chưa tồn tại
        os.makedirs('backtest_results', exist_ok=True)
        
        # Tên file kết quả
        result_file = f"backtest_results/{symbol}_{interval}_risk{risk_str}_quick_results.json"
        
        # Mô phỏng chạy backtest với dữ liệu giả lập
        time.sleep(2)  # Giả lập thời gian xử lý
        
        # Tạo dữ liệu giả về kết quả backtest
        win_rate = 50 + risk_level * 5 + (hash(symbol) % 10)  # Giả lập tỉ lệ thắng dựa trên mức rủi ro và cặp tiền
        profit = risk_level * 10 + (hash(symbol) % 20)  # Giả lập lợi nhuận dựa trên mức rủi ro và cặp tiền
        max_drawdown = risk_level * 3 + 5  # Giả lập drawdown
        sharpe_ratio = 1 + (risk_level / 3) + (hash(symbol) % 5) / 10  # Giả lập tỉ số sharpe
        
        # Lưu kết quả backtest vào file
        result_data = {
            'symbol': symbol,
            'interval': interval,
            'risk_level': risk_level,
            'period_days': period_days,
            'win_rate': win_rate,
            'profit_percentage': profit,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': int(30 + risk_level * 10),
            'test_period': f"{start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=4)
            
        logger.info(f"Đã lưu kết quả backtest vào {result_file}")
        
        return result_data
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest cho {symbol} với mức rủi ro {risk_level}%: {e}")
        return {}

def generate_comparison_chart(symbol: str, interval: str, results: Dict[float, Dict[str, Any]]) -> str:
    """
    Tạo biểu đồ so sánh hiệu suất các mức rủi ro
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        results (Dict[float, Dict[str, Any]]): Kết quả backtest các mức rủi ro
        
    Returns:
        str: Đường dẫn đến file biểu đồ
    """
    if not results:
        logger.error("Không có dữ liệu để tạo biểu đồ so sánh")
        return ""
    
    # Thiết lập biểu đồ
    plt.figure(figsize=(14, 10))
    
    # Chuẩn bị dữ liệu
    risk_levels = [2.0, 2.5, 3.0, 4.0, 5.0]
    profits = []
    win_rates = []
    drawdowns = []
    sharpe_ratios = []
    
    for risk, result in results.items():
        if not result:
            continue
        
        risk_levels.append(risk)
        profits.append(result.get('profit_percentage', 0))
        win_rates.append(result.get('win_rate', 0))
        drawdowns.append(result.get('max_drawdown', 0))
        sharpe_ratios.append(result.get('sharpe_ratio', 0))
    
    # Vẽ biểu đồ lợi nhuận
    plt.subplot(2, 2, 1)
    plt.bar(risk_levels, profits, color='green')
    plt.title(f'Lợi nhuận theo mức rủi ro - {symbol} {interval}')
    plt.xlabel('Mức rủi ro (%)')
    plt.ylabel('Lợi nhuận (%)')
    plt.grid(True, alpha=0.3)
    
    # Vẽ biểu đồ win rate
    plt.subplot(2, 2, 2)
    plt.bar(risk_levels, win_rates, color='blue')
    plt.title(f'Win Rate theo mức rủi ro - {symbol} {interval}')
    plt.xlabel('Mức rủi ro (%)')
    plt.ylabel('Win Rate (%)')
    plt.grid(True, alpha=0.3)
    
    # Vẽ biểu đồ drawdown
    plt.subplot(2, 2, 3)
    plt.bar(risk_levels, drawdowns, color='red')
    plt.title(f'Drawdown theo mức rủi ro - {symbol} {interval}')
    plt.xlabel('Mức rủi ro (%)')
    plt.ylabel('Max Drawdown (%)')
    plt.grid(True, alpha=0.3)
    
    # Vẽ biểu đồ Sharpe ratio
    plt.subplot(2, 2, 4)
    plt.bar(risk_levels, sharpe_ratios, color='purple')
    plt.title(f'Sharpe Ratio theo mức rủi ro - {symbol} {interval}')
    plt.xlabel('Mức rủi ro (%)')
    plt.ylabel('Sharpe Ratio')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Tạo thư mục risk_analysis nếu chưa tồn tại
    os.makedirs('risk_analysis', exist_ok=True)
    
    # Lưu biểu đồ
    chart_file = f"risk_analysis/{symbol}_{interval}_quick_risk_comparison.png"
    plt.savefig(chart_file)
    logger.info(f"Đã lưu biểu đồ so sánh vào {chart_file}")
    
    return chart_file

def create_summary_report(symbol: str, interval: str, results: Dict[float, Dict[str, Any]]) -> str:
    """
    Tạo báo cáo tổng hợp so sánh các mức rủi ro
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        results (Dict[float, Dict[str, Any]]): Kết quả backtest các mức rủi ro
        
    Returns:
        str: Đường dẫn đến file báo cáo
    """
    if not results:
        logger.error("Không có dữ liệu để tạo báo cáo tổng hợp")
        return ""
    
    # Tạo thư mục risk_analysis nếu chưa tồn tại
    os.makedirs('risk_analysis', exist_ok=True)
    
    # Tạo báo cáo tổng hợp
    report_file = f"risk_analysis/{symbol}_{interval}_quick_risk_summary.md"
    
    # Tìm mức rủi ro tối ưu dựa trên lợi nhuận và drawdown
    optimal_risk = 0
    best_profit = -float('inf')
    best_sharpe = -float('inf')
    lowest_drawdown = float('inf')
    lowest_drawdown_risk = 0
    best_sharpe_risk = 0
    
    for risk, result in results.items():
        if not result:
            continue
            
        profit = result.get('profit_percentage', 0)
        drawdown = result.get('max_drawdown', 0)
        sharpe = result.get('sharpe_ratio', 0)
        
        # So sánh để tìm mức rủi ro tối ưu
        if profit > best_profit:
            best_profit = profit
            optimal_risk = risk
            
        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_sharpe_risk = risk
            
        if drawdown < lowest_drawdown:
            lowest_drawdown = drawdown
            lowest_drawdown_risk = risk
    
    with open(report_file, 'w') as f:
        f.write(f"# Báo cáo phân tích rủi ro nhanh cho {symbol} {interval}\n\n")
        f.write(f"*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        f.write("## Tổng quan\n\n")
        f.write(f"- **Cặp giao dịch:** {symbol}\n")
        f.write(f"- **Khung thời gian:** {interval}\n")
        f.write(f"- **Dữ liệu:** 14 ngày gần nhất\n")
        f.write(f"- **Số mức rủi ro được kiểm thử:** {len(results)}\n\n")
        
        f.write("## So sánh hiệu suất các mức rủi ro\n\n")
        f.write("| Mức rủi ro | Lợi nhuận (%) | Win Rate (%) | Drawdown (%) | Sharpe Ratio | Số lệnh | Trade/Ngày |\n")
        f.write("|------------|--------------|--------------|--------------|--------------|---------|------------|\n")
        
        for risk in sorted(results.keys()):
            result = results[risk]
            if not result:
                continue
                
            profit = result.get('profit_percentage', 0)
            win_rate = result.get('win_rate', 0)
            drawdown = result.get('max_drawdown', 0)
            sharpe = result.get('sharpe_ratio', 0)
            total_trades = result.get('total_trades', 0)
            trades_per_day = total_trades / 14  # 14 ngày
            
            f.write(f"| {risk}% | {profit:.2f} | {win_rate:.2f} | {drawdown:.2f} | {sharpe:.2f} | {total_trades} | {trades_per_day:.2f} |\n")
        
        f.write("\n## Kết luận phân tích\n\n")
        
        f.write("### Mức rủi ro tối ưu\n\n")
        if optimal_risk > 0:
            result = results[optimal_risk]
            f.write(f"- **Mức rủi ro lợi nhuận tốt nhất:** {optimal_risk}%\n")
            f.write(f"  - Lợi nhuận: {result.get('profit_percentage', 0):.2f}%\n")
            f.write(f"  - Win Rate: {result.get('win_rate', 0):.2f}%\n")
            f.write(f"  - Drawdown: {result.get('max_drawdown', 0):.2f}%\n")
            f.write(f"  - Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}\n\n")
        
        if best_sharpe_risk > 0:
            result = results[best_sharpe_risk]
            f.write(f"- **Mức rủi ro Sharpe tốt nhất:** {best_sharpe_risk}%\n")
            f.write(f"  - Lợi nhuận: {result.get('profit_percentage', 0):.2f}%\n")
            f.write(f"  - Win Rate: {result.get('win_rate', 0):.2f}%\n")
            f.write(f"  - Drawdown: {result.get('max_drawdown', 0):.2f}%\n")
            f.write(f"  - Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}\n\n")
        
        if lowest_drawdown_risk > 0:
            result = results[lowest_drawdown_risk]
            f.write(f"- **Mức rủi ro Drawdown thấp nhất:** {lowest_drawdown_risk}%\n")
            f.write(f"  - Lợi nhuận: {result.get('profit_percentage', 0):.2f}%\n")
            f.write(f"  - Win Rate: {result.get('win_rate', 0):.2f}%\n")
            f.write(f"  - Drawdown: {result.get('max_drawdown', 0):.2f}%\n")
            f.write(f"  - Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}\n\n")
        
        f.write("### Khuyến nghị\n\n")
        
        # Tạo khuyến nghị dựa trên phân tích
        if optimal_risk == lowest_drawdown_risk:
            f.write(f"✅ **Khuyến nghị sử dụng mức rủi ro {optimal_risk}%** - đây là mức tối ưu cả về lợi nhuận và giảm thiểu drawdown.\n\n")
        elif best_sharpe_risk == optimal_risk:
            f.write(f"✅ **Khuyến nghị sử dụng mức rủi ro {optimal_risk}%** - đây là mức tối ưu cả về lợi nhuận và hiệu suất điều chỉnh theo rủi ro (Sharpe Ratio).\n\n")
        else:
            # Khuyến nghị mức cân bằng
            f.write(f"✅ **Khuyến nghị sử dụng mức rủi ro {best_sharpe_risk}%** - đây là mức cân bằng tốt nhất giữa lợi nhuận và rủi ro.\n\n")
            
        f.write("### Ghi chú\n\n")
        f.write("Lưu ý: Đây là dữ liệu mô phỏng nhanh trên tập dữ liệu nhỏ (14 ngày), ")
        f.write("kết quả có thể khác biệt so với backtest trên dữ liệu lớn hơn.\n\n")
        
        f.write("![So sánh hiệu suất các mức rủi ro](./" + os.path.basename(generate_comparison_chart(symbol, interval, results)) + ")\n")
    
    logger.info(f"Đã tạo báo cáo tổng hợp tại {report_file}")
    return report_file

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Chạy backtest nhanh với dữ liệu giả lập để kiểm thử hệ thống')
    parser.add_argument('--symbol', type=str, required=True, help='Mã cặp giao dịch (VD: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (VD: 1h, 4h)')
    args = parser.parse_args()
    
    symbol = args.symbol
    interval = args.interval
    
    logger.info(f"=== BẮT ĐẦU CHẠY KIỂM THỬ NHANH CHO {symbol} ===")
    
    # Chạy backtest cho từng mức rủi ro
    results = {}
    for risk in RISK_LEVELS:
        logger.info(f"Chạy backtest với mức rủi ro {risk}%")
        result = run_backtest(symbol, interval, risk)
        results[risk] = result
        
        # Tạm dừng giữa các lần chạy để giả lập thời gian xử lý
        time.sleep(0.5)
    
    # Tạo báo cáo tổng hợp
    report_file = create_summary_report(symbol, interval, results)
    if report_file:
        logger.info(f"Xem báo cáo tổng hợp tại: {report_file}")
    
    logger.info(f"=== ĐÃ HOÀN THÀNH KIỂM THỬ NHANH CHO {symbol} ===")

if __name__ == "__main__":
    main()