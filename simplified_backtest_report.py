#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tạo báo cáo đơn giản từ tệp nhật ký backtest
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import re
from datetime import datetime
import argparse

def extract_backtest_info(log_file):
    """Trích xuất thông tin backtest từ tệp nhật ký"""
    
    if not os.path.exists(log_file):
        raise FileNotFoundError(f"Không tìm thấy tệp {log_file}")
    
    # Đọc tệp nhật ký
    with open(log_file, 'r') as f:
        content = f.read()
    
    # Trích xuất thông tin chung
    initial_balance = re.search(r"Số dư ban đầu: \$(\d+)", content)
    initial_balance = float(initial_balance.group(1)) if initial_balance else 10000.0
    
    final_balance = re.search(r"Số dư cuối cùng: \$(\d+\.\d+)", content)
    final_balance = float(final_balance.group(1)) if final_balance else initial_balance
    
    total_trades = re.search(r"Số lượng giao dịch: (\d+)", content)
    total_trades = int(total_trades.group(1)) if total_trades else 0
    
    win_lose = re.search(r"Giao dịch thắng/thua: (\d+)/(\d+)", content)
    if win_lose:
        winning_trades = int(win_lose.group(1))
        losing_trades = int(win_lose.group(2))
    else:
        winning_trades = 0
        losing_trades = 0
    
    # Tìm tất cả các giao dịch
    trades = []
    
    # Tìm tín hiệu LONG
    long_signals = re.finditer(r"Tín hiệu LONG cho ([A-Z-]+) tại (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}), giá \$(\d+\.\d+)", content)
    
    for match in long_signals:
        symbol = match.group(1)
        entry_date = match.group(2)
        entry_price = float(match.group(3))
        
        # Tìm stop loss và take profit
        sl_tp_pattern = fr"Stop Loss: \$(\d+\.\d+), Take Profit: \$(\d+\.\d+)"
        sl_tp = re.search(sl_tp_pattern, content[match.end():match.end() + 200])
        
        if sl_tp:
            stop_loss = float(sl_tp.group(1))
            take_profit = float(sl_tp.group(2))
        else:
            stop_loss = None
            take_profit = None
        
        # Tìm kích thước vị thế
        position_pattern = fr"Kích thước vị thế: ([\d\.]+), Đòn bẩy: (\d+)x"
        position_match = re.search(position_pattern, content[match.end():match.end() + 200])
        
        if position_match:
            position_size = float(position_match.group(1))
            leverage = int(position_match.group(2))
        else:
            position_size = None
            leverage = None
        
        # Tìm kết quả
        result_pattern = fr"Kết quả: (\w+) tại (\d{{4}}-\d{{2}}-\d{{2}} \d{{2}}:\d{{2}}:\d{{2}}), giá \$(\d+\.\d+)"
        result_match = re.search(result_pattern, content[match.end():match.end() + 1000])
        
        if result_match:
            exit_reason = result_match.group(1)
            exit_date = result_match.group(2)
            exit_price = float(result_match.group(3))
        else:
            exit_reason = None
            exit_date = None
            exit_price = None
        
        # Tìm lợi nhuận
        profit_pattern = fr"Lợi nhuận: \$(\d+\.\d+) \(([\d\.]+)%\)"
        profit_match = re.search(profit_pattern, content[match.end():match.end() + 1000])
        
        if profit_match:
            profit = float(profit_match.group(1))
            profit_pct = float(profit_match.group(2))
        else:
            profit = None
            profit_pct = None
        
        # Thêm giao dịch vào danh sách
        trade = {
            'symbol': symbol,
            'type': 'LONG',
            'entry_date': entry_date,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'leverage': leverage,
            'exit_date': exit_date,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'profit': profit,
            'profit_pct': profit_pct
        }
        
        trades.append(trade)
    
    # Tạo kết quả
    result = {
        'trades': trades,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'initial_balance': initial_balance,
        'final_balance': final_balance,
        'profit': final_balance - initial_balance,
        'profit_pct': ((final_balance / initial_balance) - 1) * 100 if initial_balance > 0 else 0
    }
    
    return result

def create_report(result, output_dir='backtest_reports'):
    """Tạo báo cáo từ kết quả đã trích xuất"""
    
    # Tạo thư mục đầu ra nếu chưa tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Tạo tên file báo cáo dựa trên thời gian hiện tại
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(output_dir, f'backtest_report_{timestamp}.txt')
    
    # Tạo báo cáo
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
            
            if trade['stop_loss'] and trade['take_profit']:
                f.write(f"  Stop Loss: ${trade['stop_loss']:.2f}\n")
                f.write(f"  Take Profit: ${trade['take_profit']:.2f}\n")
            
            if trade['position_size'] and trade['leverage']:
                f.write(f"  Kích thước vị thế: {trade['position_size']:.4f}, Đòn bẩy: {trade['leverage']}x\n")
            
            if trade['exit_date'] and trade['exit_price']:
                f.write(f"  Đóng lệnh: {trade['exit_date']} tại ${trade['exit_price']:.2f}\n")
                f.write(f"  Lý do đóng: {trade['exit_reason']}\n")
            
            if trade['profit'] and trade['profit_pct']:
                f.write(f"  Lợi nhuận: ${trade['profit']:.2f} ({trade['profit_pct']:.2f}%)\n")
            
            f.write("\n")
    
    # Tạo biểu đồ nếu có giao dịch
    if result['trades']:
        chart_file = os.path.join(output_dir, f'backtest_chart_{timestamp}.png')
        
        # Dữ liệu cho biểu đồ
        trades_df = pd.DataFrame([{
            'symbol': t['symbol'],
            'profit': t['profit'] if t['profit'] else 0,
            'profit_pct': t['profit_pct'] if t['profit_pct'] else 0
        } for t in result['trades']])
        
        if not trades_df.empty:
            plt.figure(figsize=(15, 10))
            
            # Biểu đồ lợi nhuận theo giao dịch
            plt.subplot(2, 2, 1)
            colors = ['green' if x > 0 else 'red' for x in trades_df['profit_pct']]
            plt.bar(range(1, len(trades_df) + 1), trades_df['profit_pct'], color=colors)
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.title('Lợi nhuận từng giao dịch (%)')
            plt.xlabel('Giao dịch #')
            plt.ylabel('Lợi nhuận (%)')
            
            # Biểu đồ tỉ lệ thắng/thua
            plt.subplot(2, 2, 2)
            plt.pie([result['winning_trades'], result['losing_trades']], 
                   labels=['Thắng', 'Thua'],
                   colors=['green', 'red'],
                   autopct='%1.1f%%',
                   startangle=90)
            plt.axis('equal')
            plt.title('Tỉ lệ thắng/thua')
            
            # Biểu đồ tăng trưởng tài khoản
            plt.subplot(2, 1, 2)
            balance = result['initial_balance']
            balances = [balance]
            
            for trade in result['trades']:
                if trade['profit']:
                    balance += trade['profit']
                    balances.append(balance)
            
            plt.plot(range(len(balances)), balances, marker='o', linestyle='-', color='blue')
            plt.title('Tăng trưởng số dư')
            plt.xlabel('Giao dịch #')
            plt.ylabel('Số dư ($)')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(chart_file)
            print(f"Đã tạo biểu đồ: {chart_file}")
    
    print(f"Đã tạo báo cáo: {report_file}")
    return report_file

def main():
    parser = argparse.ArgumentParser(description='Tạo báo cáo backtest đơn giản')
    parser.add_argument('log_file', help='Đường dẫn đến tệp nhật ký backtest')
    parser.add_argument('--output-dir', default='backtest_reports', help='Thư mục đầu ra cho báo cáo')
    
    args = parser.parse_args()
    
    try:
        # Trích xuất thông tin
        result = extract_backtest_info(args.log_file)
        
        # Tạo báo cáo
        create_report(result, args.output_dir)
    except Exception as e:
        print(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main()