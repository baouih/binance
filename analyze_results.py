import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Đường dẫn đến thư mục kết quả
result_dir = Path('./risk_test_results')
if not result_dir.exists():
    print('Thư mục kết quả không tồn tại!')
    exit(1)

# Đọc kết quả đã có
results = {}
for file in result_dir.glob('result_*.json'):
    try:
        with open(file, 'r') as f:
            result = json.load(f)
            risk_level = file.stem.split('_')[1]
            results[risk_level] = result
    except Exception as e:
        print(f'Lỗi khi đọc file {file}: {str(e)}')

# Khởi chạy các mức rủi ro còn lại
print('\n=== PHÂN TÍCH KẾT QUẢ ĐÃ THU THẬP ===')
print('-' * 100)
print(f"{'Risk Level':20} | {'Risk %':8} | {'Trades':8} | {'Win Rate':8} | {'Profit':12} | {'Drawdown':8} | {'P.Factor':8} | {'Max Loss':8}")
print('-' * 100)

RISK_LEVELS = {
    'ultra_conservative': 0.03,  # 3%
    'conservative': 0.05,        # 5%
    'moderate': 0.07,            # 7%
    'aggressive': 0.09,          # 9%
    'high_risk': 0.15,           # 15%
    'extreme_risk': 0.20         # 20%
}

for risk_level, result in results.items():
    risk_pct = f"{RISK_LEVELS[risk_level]*100:.0f}%"
    profit = f"${result['profit_loss']:.2f}"
    profit_pct = f"{result['profit_loss_pct']:.2f}%"
    drawdown = f"{result['max_drawdown_pct']:.2f}%"
    win_rate = f"{result['win_rate']*100:.2f}%"
    profit_factor = f"{result['profit_factor']:.2f}"
    max_loss = f"${abs(result['largest_loss']):.2f}"
    
    print(f"{risk_level:20} | {risk_pct:8} | {result['total_trades']:8d} | {win_rate:8} | {profit_pct:12} | {drawdown:8} | {profit_factor:8} | {max_loss:8}")

print('\n=== THỐNG KÊ CHI TIẾT MỨC RỦI RO 3% ===')
if 'ultra_conservative' in results:
    result = results['ultra_conservative']
    
    print(f"\n- Tổng số lệnh: {result['total_trades']}")
    print(f"- Lệnh thắng: {result['winning_trades']}")
    print(f"- Lệnh thua: {result['losing_trades']}")
    print(f"- Tỷ lệ thắng: {result['win_rate']*100:.2f}%")
    print(f"- Lợi nhuận: ${result['profit_loss']:.2f} ({result['profit_loss_pct']:.2f}%)")
    print(f"- Drawdown tối đa: {result['max_drawdown_pct']:.2f}%")
    print(f"- Chuỗi thua dài nhất: {result['max_consecutive_losses']}")
    print(f"- Lệnh lãi lớn nhất: ${result['largest_win']:.2f}")
    print(f"- Lệnh lỗ lớn nhất: ${abs(result['largest_loss']):.2f}")
    
    print(f"\n- Thống kê theo lý do thoát lệnh:")
    for reason, stats in result['exit_stats'].items():
        if stats['count'] > 0:
            win_rate = stats['win'] / stats['count'] * 100
            avg_pnl = stats['total_pnl'] / stats['count']
            print(f"  + {reason}: {stats['count']} lệnh, Win rate: {win_rate:.2f}%, PnL trung bình: ${avg_pnl:.2f}")
    
    print(f"\n- Thống kê theo loại thị trường:")
    for market, stats in result['market_stats'].items():
        total_trades = stats['win'] + stats['loss']
        if total_trades > 0:
            win_rate = stats['win'] / total_trades * 100
            avg_pnl = stats['total_pnl'] / total_trades
            print(f"  + {market}: {total_trades} lệnh, Win rate: {win_rate:.2f}%, PnL trung bình: ${avg_pnl:.2f}")
            
    print(f"\n- Phân tích Partial TP vs SL:")
    total_tp_pnl = 0
    total_tp_count = 0
    for key in ['TP1', 'TP2', 'TP3', 'TRAILING_STOP']:
        if key in result['exit_stats']:
            total_tp_pnl += result['exit_stats'][key]['total_pnl']
            total_tp_count += result['exit_stats'][key]['count']
    
    sl_pnl = result['exit_stats']['SL']['total_pnl'] if 'SL' in result['exit_stats'] else 0
    sl_count = result['exit_stats']['SL']['count'] if 'SL' in result['exit_stats'] else 0
    
    if total_tp_count > 0 and sl_count > 0:
        print(f"  + Partial TP: {total_tp_count} lần chốt lời, tổng lãi ${total_tp_pnl:.2f}, trung bình ${total_tp_pnl/total_tp_count:.2f}/lần")
        print(f"  + SL: {sl_count} lần dừng lỗ, tổng lỗ ${abs(sl_pnl):.2f}, trung bình ${abs(sl_pnl)/sl_count:.2f}/lần")
        print(f"  + Tỷ lệ bù đắp: Partial TP đã bù đắp {(total_tp_pnl/abs(sl_pnl))*100:.2f}% tổng lỗ từ SL")
else:
    print('Chưa có kết quả cho mức rủi ro 3%')

print('\n=== ĐỀ XUẤT CÁC BƯỚC TIẾP THEO ===')
print('1. Tiếp tục chạy backtest với các mức rủi ro cao hơn: 5%, 7%, 9%, 15%, 20%')
print('2. So sánh hiệu suất các mức rủi ro để tìm điểm cân bằng tối ưu')
print('3. Phân tích chi tiết lệnh lãi/lỗ lớn nhất ở từng mức rủi ro')
print('4. Tối ưu hóa chiến lược dựa trên kết quả ban đầu')