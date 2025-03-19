#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tạo báo cáo đơn giản từ tệp nhật ký backtest
"""

import os
import re
from datetime import datetime
import argparse

def extract_key_metrics(log_file):
    """Trích xuất các chỉ số quan trọng từ tệp nhật ký"""
    
    try:
        with open(log_file, 'r') as f:
            content = f.read()
        
        # Trích xuất thông tin chính
        initial_balance_match = re.search(r"Số dư ban đầu: \$(\d+)", content)
        initial_balance = initial_balance_match.group(1) if initial_balance_match else "N/A"
        
        final_balance_match = re.search(r"Số dư cuối cùng: \$(\d+\.\d+)", content)
        final_balance = final_balance_match.group(1) if final_balance_match else "N/A"
        
        total_profit_match = re.search(r"Tổng lợi nhuận: \$(\d+\.\d+) \((\d+\.\d+)%\)", content)
        if total_profit_match:
            profit_amount = total_profit_match.group(1)
            profit_percent = total_profit_match.group(2)
        else:
            profit_amount = "N/A"
            profit_percent = "N/A"
        
        total_trades_match = re.search(r"Số lượng giao dịch: (\d+)", content)
        total_trades = total_trades_match.group(1) if total_trades_match else "N/A"
        
        win_loss_match = re.search(r"Giao dịch thắng/thua: (\d+)/(\d+)", content)
        if win_loss_match:
            winning_trades = win_loss_match.group(1)
            losing_trades = win_loss_match.group(2)
        else:
            winning_trades = "N/A"
            losing_trades = "N/A"
        
        win_rate_match = re.search(r"Tỷ lệ thắng: (\d+\.\d+)%", content)
        win_rate = win_rate_match.group(1) if win_rate_match else "N/A"
        
        # Tìm chi tiết giao dịch
        trade_details = []
        
        # Tìm tín hiệu giao dịch
        signal_pattern = r"Tín hiệu LONG cho ([A-Z-]+) tại (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}), giá \$(\d+\.\d+)"
        signals = re.finditer(signal_pattern, content)
        
        for signal in signals:
            symbol = signal.group(1)
            entry_date = signal.group(2)
            entry_price = signal.group(3)
            
            # Tìm kết quả của giao dịch
            result_pattern = r"Kết quả: (\w+) tại (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}), giá \$(\d+\.\d+)"
            result_match = re.search(result_pattern, content[signal.end():signal.end() + 1000])
            
            if result_match:
                exit_reason = result_match.group(1)
                exit_date = result_match.group(2)
                exit_price = result_match.group(3)
                
                # Tìm lợi nhuận
                profit_pattern = r"Lợi nhuận: \$(\d+\.\d+) \((\d+\.\d+)%\)"
                profit_match = re.search(profit_pattern, content[signal.end():signal.end() + 1000])
                
                if profit_match:
                    trade_profit = profit_match.group(1)
                    trade_profit_pct = profit_match.group(2)
                else:
                    trade_profit = "N/A"
                    trade_profit_pct = "N/A"
                
                trade_details.append({
                    "symbol": symbol,
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "exit_date": exit_date,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "profit": trade_profit,
                    "profit_pct": trade_profit_pct
                })
        
        return {
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "profit": profit_amount,
            "profit_pct": profit_percent,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "trades": trade_details
        }
    
    except Exception as e:
        print(f"Lỗi khi đọc tệp: {str(e)}")
        return None

def create_simple_report(metrics, output_dir='backtest_reports'):
    """Tạo báo cáo đơn giản từ các chỉ số"""
    
    if not metrics:
        print("Không có dữ liệu để tạo báo cáo")
        return
    
    # Tạo thư mục đầu ra nếu chưa tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Tạo tên tệp báo cáo
    report_file = os.path.join(output_dir, f'simple_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    
    with open(report_file, 'w') as f:
        f.write("=== BÁO CÁO BACKTEST ĐƠN GIẢN ===\n\n")
        f.write(f"Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("THỐNG KÊ TỔNG QUAN\n")
        f.write(f"Số dư ban đầu: ${metrics['initial_balance']}\n")
        f.write(f"Số dư cuối cùng: ${metrics['final_balance']}\n")
        f.write(f"Tổng lợi nhuận: ${metrics['profit']} ({metrics['profit_pct']}%)\n")
        f.write(f"Tổng số giao dịch: {metrics['total_trades']}\n")
        f.write(f"Giao dịch thắng: {metrics['winning_trades']}\n")
        f.write(f"Giao dịch thua: {metrics['losing_trades']}\n")
        f.write(f"Tỷ lệ thắng: {metrics['win_rate']}%\n\n")
        
        f.write("CHI TIẾT GIAO DỊCH\n")
        for i, trade in enumerate(metrics['trades'], 1):
            f.write(f"Giao dịch #{i}\n")
            f.write(f"  Symbol: {trade['symbol']}\n")
            f.write(f"  Mở lệnh: {trade['entry_date']} tại ${trade['entry_price']}\n")
            f.write(f"  Đóng lệnh: {trade['exit_date']} tại ${trade['exit_price']}\n")
            f.write(f"  Lý do đóng: {trade['exit_reason']}\n")
            f.write(f"  Lợi nhuận: ${trade['profit']} ({trade['profit_pct']}%)\n\n")
    
    print(f"Đã tạo báo cáo: {report_file}")
    return report_file

def main():
    parser = argparse.ArgumentParser(description='Tạo báo cáo backtest đơn giản')
    parser.add_argument('log_file', help='Đường dẫn đến tệp nhật ký backtest')
    parser.add_argument('--output-dir', default='backtest_reports', help='Thư mục đầu ra cho báo cáo')
    
    args = parser.parse_args()
    
    # Trích xuất các chỉ số
    metrics = extract_key_metrics(args.log_file)
    
    # Tạo báo cáo
    if metrics:
        create_simple_report(metrics, args.output_dir)

if __name__ == "__main__":
    main()