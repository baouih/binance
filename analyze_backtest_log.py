#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phân tích kết quả backtest từ tệp nhật ký
"""

import os
import json
import re
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse

def parse_backtest_log(log_file):
    """Phân tích tệp nhật ký backtest và trả về kết quả dưới dạng dict"""
    
    if not os.path.exists(log_file):
        raise FileNotFoundError(f"Không tìm thấy tệp {log_file}")
    
    # Đọc tệp nhật ký
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    # Khởi tạo biến
    trades = []
    current_symbol = None
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    initial_balance = 10000
    final_balance = 10000
    
    # Phân tích từng dòng để trích xuất thông tin
    for line in lines:
        line = line.strip()
        
        # Bỏ qua dòng trống
        if not line:
            continue
        
        # Bỏ qua đầu ra của yfinance
        if "YF.download()" in line:
            continue
            
        # Bỏ qua cảnh báo pandas
        if "FutureWarning" in line:
            continue
        
        # Xử lý thông báo
        message = line
        
        # Nếu là định dạng log chuẩn, trích xuất phần thông báo
        if ' - INFO - ' in line:
            message = line.split(' - INFO - ', 1)[1]
        
        # Tách cấp độ và thông báo
        if ':' in level_message:
            level, message = level_message.split(':', 1)
        else:
            message = level_message
        
        # Chuẩn bị message để phân tích
        message = message.strip()
        
        # Tìm tham số ban đầu
        if "Số dư ban đầu: $" in message:
            amount = message.split('$')[1].strip()
            initial_balance = float(amount)
            
        # Xác định symbol hiện tại
        if "Bắt đầu backtest" in message:
            current_symbol = message.split()[-1]
            
        # Tìm tín hiệu giao dịch
        if "Tín hiệu LONG cho" in message:
            parts = message.split()
            symbol = parts[3]
            date = parts[5] + " " + parts[6]
            price = float(parts[8].replace('$', ''))
            
            # Thêm giao dịch mới
            trades.append({
                'symbol': symbol,
                'type': 'LONG',
                'entry_date': date,
                'entry_price': price
            })
            
        # Tìm thông tin stop loss / take profit
        if "Stop Loss:" in message:
            if trades:
                parts = message.split()
                sl_price = float(parts[2].replace('$', ''))
                tp_price = float(parts[5].replace('$', ''))
                trades[-1]['stop_loss'] = sl_price
                trades[-1]['take_profit'] = tp_price
                
        # Tìm kích thước vị thế
        if "Kích thước vị thế:" in message:
            if trades:
                parts = message.split()
                position_size = float(parts[3].replace(',', '.'))
                leverage = int(parts[6].replace('x', ''))
                trades[-1]['position_size'] = position_size
                trades[-1]['leverage'] = leverage
        
        # Tìm kết quả giao dịch
        if "Kết quả:" in message and "tại" in message:
            if trades:
                parts = message.split()
                exit_reason = parts[1].replace(':', '')
                date = parts[3] + " " + parts[4]
                price = float(parts[6].replace('$', ''))
                
                # Cập nhật thông tin đóng lệnh
                trades[-1]['exit_date'] = date
                trades[-1]['exit_price'] = price
                trades[-1]['exit_reason'] = exit_reason
        
        # Tìm lợi nhuận giao dịch
        if "Lợi nhuận:" in message and "(" in message:
            if trades and 'exit_price' in trades[-1]:
                parts = message.split()
                profit = float(parts[1].replace('$', ''))
                profit_pct = float(parts[2].replace('(', '').replace('%)', ''))
                
                # Cập nhật thông tin lợi nhuận
                trades[-1]['profit'] = profit
                trades[-1]['profit_pct'] = profit_pct
        
        # Tìm số giao dịch, tỉ lệ thắng thua và số dư cuối
        if "Số lượng giao dịch:" in message:
            total_trades = int(message.split(":")[-1].strip())
            
        if "Giao dịch thắng/thua:" in message:
            parts = message.split(":")[-1].strip().split("/")
            winning_trades = int(parts[0])
            losing_trades = int(parts[1])
            
        if "Số dư cuối cùng:" in message:
            final_balance = float(message.split("$")[-1].strip())
            
        if "Tổng lợi nhuận:" in message:
            # Đã có final_balance, không cần xử lý
            pass
    
    # Tính các giá trị nếu chúng không được tìm thấy trong log
    if total_trades == 0:
        total_trades = len(trades)
    
    if winning_trades == 0 and losing_trades == 0:
        winning_trades = sum(1 for trade in trades if trade.get('profit', 0) > 0)
        losing_trades = sum(1 for trade in trades if trade.get('profit', 0) <= 0)
    
    # Tổng hợp kết quả
    result = {
        'trades': trades,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'initial_balance': initial_balance,
        'final_balance': final_balance,
        'profit': final_balance - initial_balance,
        'profit_pct': ((final_balance / initial_balance) - 1) * 100
    }
    
    return result

def generate_report(result, output_dir='backtest_reports'):
    """Tạo báo cáo backtest"""
    
    # Tạo thư mục đầu ra nếu chưa tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Tạo tên tệp dựa trên thời gian
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(output_dir, f'backtest_report_{timestamp}.txt')
    json_file = os.path.join(output_dir, f'backtest_data_{timestamp}.json')
    
    # Lưu dữ liệu dưới dạng JSON
    with open(json_file, 'w') as f:
        json.dump(result, f, indent=4, default=str)
    
    # Tạo báo cáo văn bản
    with open(report_file, 'w') as f:
        f.write("=== BÁO CÁO KẾT QUẢ BACKTEST ===\n\n")
        f.write(f"Ngày tạo báo cáo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("THỐNG KÊ TỔNG QUAN\n")
        f.write(f"Số dư ban đầu: ${result['initial_balance']:.2f}\n")
        f.write(f"Số dư cuối cùng: ${result['final_balance']:.2f}\n")
        f.write(f"Lợi nhuận: ${result['profit']:.2f} ({result['profit_pct']:.2f}%)\n")
        f.write(f"Tổng số giao dịch: {result['total_trades']}\n")
        f.write(f"Số giao dịch thắng: {result['winning_trades']}\n")
        f.write(f"Số giao dịch thua: {result['losing_trades']}\n")
        
        win_rate = result['winning_trades'] / result['total_trades'] * 100 if result['total_trades'] > 0 else 0
        f.write(f"Tỷ lệ thắng: {win_rate:.2f}%\n\n")
        
        f.write("CHI TIẾT GIAO DỊCH\n")
        for i, trade in enumerate(result['trades'], 1):
            f.write(f"Giao dịch #{i}\n")
            f.write(f"  Symbol: {trade['symbol']}\n")
            f.write(f"  Loại: {trade['type']}\n")
            f.write(f"  Mở lệnh: {trade['entry_date']} tại ${trade['entry_price']:.2f}\n")
            
            if 'stop_loss' in trade and 'take_profit' in trade:
                f.write(f"  Stop Loss: ${trade['stop_loss']:.2f}\n")
                f.write(f"  Take Profit: ${trade['take_profit']:.2f}\n")
            
            if 'position_size' in trade and 'leverage' in trade:
                f.write(f"  Kích thước vị thế: {trade['position_size']:.4f}, Đòn bẩy: {trade['leverage']}x\n")
            
            if 'exit_date' in trade and 'exit_price' in trade:
                f.write(f"  Đóng lệnh: {trade['exit_date']} tại ${trade['exit_price']:.2f}\n")
                f.write(f"  Lý do đóng: {trade['exit_reason']}\n")
            
            if 'profit' in trade and 'profit_pct' in trade:
                f.write(f"  Lợi nhuận: ${trade['profit']:.2f} ({trade['profit_pct']:.2f}%)\n")
            
            f.write("\n")
    
    # Tạo biểu đồ nếu có giao dịch
    if result['trades']:
        chart_file = os.path.join(output_dir, f'backtest_chart_{timestamp}.png')
        
        # Chuẩn bị dữ liệu cho biểu đồ
        trades_data = []
        
        for trade in result['trades']:
            if 'profit' in trade and 'profit_pct' in trade:
                trades_data.append({
                    'symbol': trade['symbol'],
                    'profit': trade['profit'],
                    'profit_pct': trade['profit_pct']
                })
        
        if trades_data:
            df = pd.DataFrame(trades_data)
            
            # Tạo biểu đồ
            plt.figure(figsize=(15, 8))
            
            # Biểu đồ lợi nhuận theo giao dịch
            plt.subplot(2, 2, 1)
            bars = plt.bar(range(1, len(df) + 1), df['profit_pct'], color=['green' if x > 0 else 'red' for x in df['profit_pct']])
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.title('Lợi nhuận theo giao dịch (%)')
            plt.xlabel('Giao dịch #')
            plt.ylabel('Lợi nhuận (%)')
            
            # Biểu đồ lợi nhuận theo symbol
            plt.subplot(2, 2, 2)
            symbol_profit = df.groupby('symbol')['profit_pct'].sum()
            colors = ['green' if x > 0 else 'red' for x in symbol_profit]
            symbol_profit.plot(kind='bar', color=colors)
            plt.title('Lợi nhuận theo Symbol (%)')
            plt.xlabel('Symbol')
            plt.ylabel('Lợi nhuận (%)')
            
            # Biểu đồ tỉ lệ thắng/thua
            plt.subplot(2, 2, 3)
            plt.pie([result['winning_trades'], result['losing_trades']], 
                   labels=['Thắng', 'Thua'],
                   colors=['green', 'red'],
                   autopct='%1.1f%%',
                   startangle=90)
            plt.axis('equal')
            plt.title('Tỉ lệ thắng/thua')
            
            # Biểu đồ số dư
            plt.subplot(2, 2, 4)
            
            # Tạo dữ liệu tăng trưởng
            balance = result['initial_balance']
            balances = [balance]
            
            for trade in result['trades']:
                if 'profit' in trade:
                    balance += trade['profit']
                    balances.append(balance)
            
            plt.plot(range(len(balances)), balances, marker='o', linestyle='-', color='blue')
            plt.title('Tăng trưởng số dư')
            plt.xlabel('Giao dịch #')
            plt.ylabel('Số dư ($)')
            
            plt.tight_layout()
            plt.savefig(chart_file)
            
            print(f"Đã tạo biểu đồ: {chart_file}")
    
    print(f"Đã tạo báo cáo: {report_file}")
    return report_file

def main():
    parser = argparse.ArgumentParser(description='Phân tích tệp nhật ký backtest')
    parser.add_argument('log_file', type=str, help='Đường dẫn đến tệp nhật ký backtest')
    parser.add_argument('--output-dir', type=str, default='backtest_reports', help='Thư mục lưu báo cáo')
    
    args = parser.parse_args()
    
    # Phân tích tệp nhật ký
    result = parse_backtest_log(args.log_file)
    
    # Tạo báo cáo
    generate_report(result, args.output_dir)

if __name__ == "__main__":
    main()