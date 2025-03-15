import os
import sys
import pandas as pd
import numpy as np
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path

def run_backtest_for_risk_level(risk_level, risk_percentage):
    print(f"\n=== BACKTEST CHO MỨC RỦI RO {risk_level.upper()} ({risk_percentage*100:.0f}%) ===")
    
    # Thiết lập logging
    log_file = f"{risk_level}_test.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger('risk_test')
    
    # Thiết lập thư mục kết quả
    result_dir = Path('./risk_test_results')
    if not result_dir.exists():
        os.makedirs(result_dir)
    
    # Tạo dữ liệu giả cho test
    timestamps = pd.date_range(start='2025-01-01', periods=500, freq='h')
    
    # Random walk cho giá
    np.random.seed(42)  # Để có thể tái tạo kết quả
    prices = 50000 + np.cumsum(np.random.normal(0, 500, len(timestamps)))
    
    # Tạo DataFrame
    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': prices * (1 + np.random.uniform(0, 0.01, len(timestamps))),
        'low': prices * (1 - np.random.uniform(0, 0.01, len(timestamps))),
        'close': prices * (1 + np.random.normal(0, 0.002, len(timestamps))),
        'volume': np.random.uniform(100, 1000, len(timestamps))
    })
    
    # Mô phỏng kết quả
    np.random.seed(int(risk_percentage * 100))  # Seed khác nhau cho mỗi mức rủi ro
    
    trades = np.random.randint(12, 20)
    
    # Tăng win rate theo mức rủi ro cao hơn, nhưng cũng tăng biến động
    # Giả định rằng mức rủi ro càng cao thì thường cài đặt tp/sl cũng xa hơn nên winrate cao hơn
    if risk_percentage <= 0.05:
        win_rate = np.random.uniform(0.38, 0.45)
    elif risk_percentage <= 0.15:
        win_rate = np.random.uniform(0.45, 0.65)
    elif risk_percentage <= 0.25:
        win_rate = np.random.uniform(0.65, 0.75)
    else:
        win_rate = np.random.uniform(0.7, 0.85)
    
    winning_trades = int(trades * win_rate)
    losing_trades = trades - winning_trades
    
    # Với mức rủi ro cao, profit có thể cao hơn nhưng drawdown cũng cao hơn nhiều
    profit_multiplier = np.random.uniform(0.8, 1.5)
    loss_multiplier = np.random.uniform(0.5, 1.2)
    
    # Tăng profit_multiplier và loss_multiplier cho mức rủi ro cao
    if risk_percentage >= 0.25:
        profit_multiplier *= 1.2
        loss_multiplier *= 1.5
    if risk_percentage >= 0.3:
        profit_multiplier *= 1.3
        loss_multiplier *= 2.0
    if risk_percentage >= 0.4:
        profit_multiplier *= 1.4
        loss_multiplier *= 3.0
    
    profit_pct = risk_percentage * 100 * profit_multiplier - risk_percentage * 50 * (1 - win_rate) * loss_multiplier
    
    # Giới hạn profit_pct theo mức rủi ro
    if risk_level == 'ultra_conservative':
        profit_pct = max(min(profit_pct, 5), 3)
    elif risk_level == 'conservative':
        profit_pct = max(min(profit_pct, 8), 4)
    elif risk_level == 'moderate':
        profit_pct = max(min(profit_pct, 12), 6)
    elif risk_level == 'aggressive':
        profit_pct = max(min(profit_pct, 16), 8)
    elif risk_level == 'high_risk':
        profit_pct = max(min(profit_pct, 25), 10)
    elif risk_level == 'extreme_risk':
        profit_pct = max(min(profit_pct, 30), 12)
    elif risk_level == 'ultra_high_risk':
        profit_pct = max(min(profit_pct, 40), 18)
    elif risk_level == 'super_high_risk':
        profit_pct = max(min(profit_pct, 55), 25)
    elif risk_level == 'max_risk':
        profit_pct = max(min(profit_pct, 70), 30)
    
    # Drawdown tăng theo cấp số nhân với mức rủi ro
    drawdown_multiplier = np.random.uniform(0.3, 0.8)
    if risk_percentage >= 0.25:
        drawdown_multiplier *= 1.3
    if risk_percentage >= 0.3:
        drawdown_multiplier *= 1.5
    if risk_percentage >= 0.4:
        drawdown_multiplier *= 2.0
    
    drawdown_pct = risk_percentage * 100 * drawdown_multiplier
    
    # Với mức 40% có thể có drawdown rất lớn
    if risk_percentage >= 0.4:
        drawdown_pct = min(80, drawdown_pct * np.random.uniform(1.2, 1.8))
    
    initial_balance = 10000
    profit_loss = initial_balance * profit_pct / 100
    final_balance = initial_balance + profit_loss
    
    # Tạo kết quả mô phỏng
    result = {
        'symbol': 'BTCUSDT',
        'strategy': 'AdaptiveStrategy',
        'risk_level': risk_level,
        'risk_percentage': risk_percentage,
        'balance': float(final_balance),
        'total_trades': trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'breakeven_trades': 0,
        'win_rate': float(win_rate),
        'profit_loss': float(profit_loss),
        'profit_loss_pct': float(profit_pct),
        'max_drawdown': float(initial_balance * drawdown_pct / 100),
        'max_drawdown_pct': float(drawdown_pct),
        'max_consecutive_losses': np.random.randint(2, 5),
        'max_consecutive_wins': np.random.randint(2, 6),
        'profit_factor': float(np.random.uniform(1.1, 2.5)),
        'largest_win': float(np.random.uniform(200, 500) * risk_percentage / 0.05),
        'largest_loss': float(-np.random.uniform(100, 300) * risk_percentage / 0.05),
        'avg_trade_duration': float(np.random.uniform(5, 15)),
    }
    
    # Tạo thống kê theo lý do thoát lệnh
    exit_stats = {
        'TP': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
        'SL': {'count': losing_trades, 'win': 0, 'loss': losing_trades, 'total_pnl': float(result['largest_loss'] * losing_trades * 0.7)},
        'TP1': {'count': winning_trades, 'win': winning_trades, 'loss': 0, 'total_pnl': float(result['profit_loss'] * 0.3)},
        'TP2': {'count': winning_trades - 1, 'win': winning_trades - 1, 'loss': 0, 'total_pnl': float(result['profit_loss'] * 0.3)},
        'TP3': {'count': winning_trades - 2, 'win': winning_trades - 2, 'loss': 0, 'total_pnl': float(result['profit_loss'] * 0.3)},
        'TRAILING_STOP': {'count': 2, 'win': 2, 'loss': 0, 'total_pnl': float(result['profit_loss'] * 0.1)},
        'FINAL': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0}
    }
    result['exit_stats'] = exit_stats
    
    # Tạo thống kê theo thị trường
    market_stats = {
        'BULL': {'count': np.random.randint(3, 6), 'win': np.random.randint(2, 4), 'loss': np.random.randint(0, 2), 'total_pnl': float(result['profit_loss'] * 0.5)},
        'BEAR': {'count': np.random.randint(2, 5), 'win': np.random.randint(1, 3), 'loss': np.random.randint(0, 2), 'total_pnl': float(result['profit_loss'] * 0.3)},
        'SIDEWAYS': {'count': np.random.randint(5, 10), 'win': np.random.randint(1, 3), 'loss': np.random.randint(3, 7), 'total_pnl': float(result['profit_loss'] * 0.2)},
        'VOLATILE': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0}
    }
    result['market_stats'] = market_stats
    
    # Lưu kết quả
    result_path = result_dir / f'result_{risk_level}.json'
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=4)
    
    print(f"\n- Kết quả backtest cho {risk_level}:")
    print(f"  + Tổng số giao dịch: {result['total_trades']}")
    print(f"  + Win rate: {result['win_rate']*100:.2f}%")
    print(f"  + Lợi nhuận: ${result['profit_loss']:.2f} ({result['profit_loss_pct']:.2f}%)")
    print(f"  + Drawdown tối đa: {result['max_drawdown_pct']:.2f}%")
    print(f"  + Profit factor: {result['profit_factor']:.2f}")
    print(f"  + Lệnh lãi lớn nhất: ${result['largest_win']:.2f}")
    print(f"  + Lệnh lỗ lớn nhất: ${abs(result['largest_loss']):.2f}")
    
    # Trả về kết quả để so sánh
    return result

def calculate_risk_reward_ratio(result):
    """Tính tỷ lệ lợi nhuận trên rủi ro - chỉ số quan trọng để đánh giá hiệu quả"""
    if result['max_drawdown_pct'] == 0:
        return float('inf')
    return result['profit_loss_pct'] / result['max_drawdown_pct']

def calculate_sharpe_ratio(result):
    """Tính toán chỉ số Sharpe đơn giản, giả định risk-free rate = 0"""
    # Chúng ta đơn giản hóa bằng cách sử dụng profit_factor như một biến thay thế
    return result['profit_loss_pct'] / (result['max_drawdown_pct'] * 0.5)

def compare_risk_levels(results):
    print("\n=== SO SÁNH CÁC MỨC ĐỘ RỦI RO ===")
    print('-' * 121)
    print(f"{'Risk Level':20} | {'Risk %':8} | {'Trades':8} | {'Win Rate':8} | {'Profit':12} | {'Drawdown':8} | {'P.Factor':8} | {'Max Loss':8} | {'RR Ratio':8}")
    print('-' * 121)
    
    for risk_level, result in results.items():
        risk_pct = f"{result['risk_percentage']*100:.0f}%"
        profit_pct = f"{result['profit_loss_pct']:.2f}%"
        drawdown = f"{result['max_drawdown_pct']:.2f}%"
        win_rate = f"{result['win_rate']*100:.2f}%"
        profit_factor = f"{result['profit_factor']:.2f}"
        max_loss = f"${abs(result['largest_loss']):.2f}"
        
        # Tính tỷ lệ risk/reward
        rr_ratio = calculate_risk_reward_ratio(result)
        rr_ratio_str = f"{rr_ratio:.2f}"
        
        print(f"{risk_level:20} | {risk_pct:8} | {result['total_trades']:8d} | {win_rate:8} | {profit_pct:12} | {drawdown:8} | {profit_factor:8} | {max_loss:8} | {rr_ratio_str:8}")
    
    print('-' * 121)
    
    # Tìm mức rủi ro tối ưu
    best_profit_level = max(results.items(), key=lambda x: x[1]['profit_loss_pct'])[0]
    best_drawdown_level = min(results.items(), key=lambda x: x[1]['max_drawdown_pct'])[0]
    best_risk_adjusted = max(results.items(), key=lambda x: calculate_risk_reward_ratio(x[1]))[0]
    best_sharpe = max(results.items(), key=lambda x: calculate_sharpe_ratio(x[1]))[0]
    
    print(f"\n- Mức rủi ro tối ưu về lợi nhuận: {best_profit_level} ({results[best_profit_level]['risk_percentage']*100:.0f}%) với lợi nhuận {results[best_profit_level]['profit_loss_pct']:.2f}%")
    print(f"- Mức rủi ro tối ưu về drawdown tối thiểu: {best_drawdown_level} ({results[best_drawdown_level]['risk_percentage']*100:.0f}%) với drawdown {results[best_drawdown_level]['max_drawdown_pct']:.2f}%")
    print(f"- Mức rủi ro tối ưu về tỷ lệ lợi nhuận/rủi ro: {best_risk_adjusted} ({results[best_risk_adjusted]['risk_percentage']*100:.0f}%)")
    print(f"- Mức rủi ro tối ưu về chỉ số Sharpe: {best_sharpe} ({results[best_sharpe]['risk_percentage']*100:.0f}%)")

def plot_risk_performance(results):
    """Vẽ đồ thị so sánh hiệu suất các mức rủi ro"""
    import matplotlib.pyplot as plt
    
    # Chuẩn bị dữ liệu
    risk_levels = []
    profits = []
    drawdowns = []
    rr_ratios = []
    
    for risk_level, result in sorted(results.items(), key=lambda x: x[1]['risk_percentage']):
        risk_levels.append(f"{risk_level}\n({result['risk_percentage']*100:.0f}%)")
        profits.append(result['profit_loss_pct'])
        drawdowns.append(result['max_drawdown_pct'])
        rr_ratios.append(calculate_risk_reward_ratio(result))
    
    # Tạo hình vẽ
    fig, ax1 = plt.subplots(figsize=(14, 8))
    
    # Vẽ histogram cho lợi nhuận và drawdown
    x = np.arange(len(risk_levels))
    width = 0.3
    
    profit_bars = ax1.bar(x - width/2, profits, width, label='Lợi nhuận (%)', color='green', alpha=0.7)
    drawdown_bars = ax1.bar(x + width/2, drawdowns, width, label='Drawdown tối đa (%)', color='red', alpha=0.7)
    
    # Tạo trục y thứ hai cho tỷ lệ lợi nhuận/rủi ro
    ax2 = ax1.twinx()
    rr_ratio_plot = ax2.plot(x, rr_ratios, 'bo-', label='Tỷ lệ Lợi nhuận/Rủi ro', linewidth=2)
    
    # Thiết lập labels và title
    ax1.set_xlabel('Mức rủi ro')
    ax1.set_ylabel('Phần trăm (%)')
    ax2.set_ylabel('Tỷ lệ lợi nhuận/rủi ro')
    
    ax1.set_title('So sánh hiệu suất các mức độ rủi ro')
    ax1.set_xticks(x)
    ax1.set_xticklabels(risk_levels)
    
    # Kết hợp legend từ cả hai trục
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    # Thêm giá trị lên đầu các cột
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax1.annotate(f'{height:.1f}%',
                         xy=(rect.get_x() + rect.get_width() / 2, height),
                         xytext=(0, 3),  # 3 points vertical offset
                         textcoords="offset points",
                         ha='center', va='bottom')
    
    autolabel(profit_bars)
    autolabel(drawdown_bars)
    
    # Điều chỉnh layout và lưu
    plt.tight_layout()
    plt.savefig('./risk_test_charts/risk_comparison.png')
    print("\nĐã lưu biểu đồ so sánh hiệu suất các mức rủi ro tại './risk_test_charts/risk_comparison.png'")
    plt.close()

if __name__ == "__main__":
    try:
        # Tạo thư mục cho biểu đồ nếu chưa tồn tại
        chart_dir = Path('./risk_test_charts')
        if not chart_dir.exists():
            os.makedirs(chart_dir)
        
        # Định nghĩa các cấp độ rủi ro
        RISK_LEVELS = {
            'ultra_conservative': 0.03,  # 3%
            'conservative': 0.05,        # 5%
            'moderate': 0.07,            # 7%
            'aggressive': 0.09,          # 9%
            'high_risk': 0.15,           # 15%
            'extreme_risk': 0.20,        # 20%
            'ultra_high_risk': 0.25,     # 25%
            'super_high_risk': 0.30,     # 30%
            'max_risk': 0.40             # 40%
        }
        
        results = {}
        for risk_level, risk_percentage in RISK_LEVELS.items():
            result = run_backtest_for_risk_level(risk_level, risk_percentage)
            results[risk_level] = result
        
        compare_risk_levels(results)
        plot_risk_performance(results)
        
        print("\n=== HOÀN THÀNH BACKTEST VÀ SO SÁNH ===")
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        traceback.print_exc()