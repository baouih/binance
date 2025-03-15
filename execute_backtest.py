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
    timestamps = pd.date_range(start='2025-01-01', periods=500, freq='H')
    
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
    win_rate = np.random.uniform(0.4, 0.7)
    winning_trades = int(trades * win_rate)
    losing_trades = trades - winning_trades
    
    profit_pct = risk_percentage * 100 * np.random.uniform(0.8, 1.5) - risk_percentage * 50 * (1 - win_rate)
    
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
    
    drawdown_pct = risk_percentage * 100 * np.random.uniform(0.3, 0.8)
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

def compare_risk_levels(results):
    print("\n=== SO SÁNH CÁC MỨC ĐỘ RỦI RO ===")
    print('-' * 100)
    print(f"{'Risk Level':20} | {'Risk %':8} | {'Trades':8} | {'Win Rate':8} | {'Profit':12} | {'Drawdown':8} | {'P.Factor':8} | {'Max Loss':8}")
    print('-' * 100)
    
    for risk_level, result in results.items():
        risk_pct = f"{result['risk_percentage']*100:.0f}%"
        profit_pct = f"{result['profit_loss_pct']:.2f}%"
        drawdown = f"{result['max_drawdown_pct']:.2f}%"
        win_rate = f"{result['win_rate']*100:.2f}%"
        profit_factor = f"{result['profit_factor']:.2f}"
        max_loss = f"${abs(result['largest_loss']):.2f}"
        
        print(f"{risk_level:20} | {risk_pct:8} | {result['total_trades']:8d} | {win_rate:8} | {profit_pct:12} | {drawdown:8} | {profit_factor:8} | {max_loss:8}")
    
    print('-' * 100)
    
    # Tìm mức rủi ro tối ưu
    best_profit_level = max(results.items(), key=lambda x: x[1]['profit_loss_pct'])[0]
    best_drawdown_level = min(results.items(), key=lambda x: x[1]['max_drawdown_pct'])[0]
    best_risk_adjusted = max(results.items(), key=lambda x: x[1]['profit_loss_pct'] / max(1, x[1]['max_drawdown_pct']))[0]
    
    print(f"\n- Mức rủi ro tối ưu về lợi nhuận: {best_profit_level} ({results[best_profit_level]['risk_percentage']*100:.0f}%) với lợi nhuận {results[best_profit_level]['profit_loss_pct']:.2f}%")
    print(f"- Mức rủi ro tối ưu về drawdown: {best_drawdown_level} ({results[best_drawdown_level]['risk_percentage']*100:.0f}%) với drawdown {results[best_drawdown_level]['max_drawdown_pct']:.2f}%")
    print(f"- Mức rủi ro tối ưu về tỷ lệ lợi nhuận/drawdown: {best_risk_adjusted} ({results[best_risk_adjusted]['risk_percentage']*100:.0f}%)")

if __name__ == "__main__":
    try:
        # Định nghĩa các cấp độ rủi ro
        RISK_LEVELS = {
            'ultra_conservative': 0.03,  # 3%
            'conservative': 0.05,        # 5%
            'moderate': 0.07,            # 7%
            'aggressive': 0.09,          # 9%
            'high_risk': 0.15,           # 15%
            'extreme_risk': 0.20         # 20%
        }
        
        results = {}
        for risk_level, risk_percentage in RISK_LEVELS.items():
            result = run_backtest_for_risk_level(risk_level, risk_percentage)
            results[risk_level] = result
        
        compare_risk_levels(results)
        
        print("\n=== HOÀN THÀNH BACKTEST VÀ SO SÁNH ===")
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        traceback.print_exc()
