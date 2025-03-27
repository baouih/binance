#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Backtest đơn giản sử dụng dữ liệu thực từ Binance trong 3 tháng
Tập trung vào các cặp tiền chính
"""

import os
import sys
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback

# Thiết lập logging
log_file = f'backtest_simplified_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('simplified_backtest')

try:
    # Import các module cần thiết
    from adaptive_strategy_backtest import run_adaptive_backtest, save_report
    from sideways_market_detector import SidewaysMarketDetector
except ImportError as e:
    logger.error(f"Không thể import module cần thiết: {e}")
    sys.exit(1)

def run_simplified_test():
    """Chạy backtest đơn giản với ít symbol và thời gian ngắn hơn"""
    
    # Danh sách các symbol mạnh nhất
    symbols = ['BTC-USD', 'ETH-USD', 'BNB-USD']
    
    # Thiết lập test
    period = '3mo'
    timeframe = '1d'
    initial_balance = 10000.0
    use_binance = True
    
    logger.info(f"Bắt đầu backtest đơn giản với {len(symbols)} symbols trong {period}")
    
    results = {}
    all_trades = []
    total_trades_count = 0
    winning_trades_count = 0
    losing_trades_count = 0
    
    for symbol in symbols:
        logger.info(f"Test symbol {symbol} với {period} dữ liệu trên khung {timeframe}")
        
        try:
            # Chạy backtest cho symbol này với chiến lược thích ứng
            report = run_adaptive_backtest(
                symbols=[symbol],
                period=period,
                timeframe=timeframe,
                initial_balance=initial_balance,
                use_binance_data=use_binance
            )
            
            # Phân tích kết quả
            symbol_trades = len(report.get('all_trades', []))
            symbol_win_rate = report.get('win_rate', 0)
            symbol_profit = report.get('total_profit', 0)
            symbol_profit_pct = report.get('total_profit_pct', 0)
            
            # Cập nhật thống kê tổng thể
            total_trades_count += report.get('total_trades', 0)
            winning_trades_count += report.get('winning_trades', 0)
            losing_trades_count += report.get('losing_trades', 0)
            
            # Thêm vào all_trades
            all_trades.extend(report.get('all_trades', []))
            
            # Lưu kết quả
            results[symbol] = {
                'trades': symbol_trades,
                'win_rate': symbol_win_rate,
                'profit': symbol_profit,
                'profit_pct': symbol_profit_pct,
                'ma_signals': report.get('symbol_results', {}).get(symbol, {}).get('ma_signals', 0),
                'sideways_signals': report.get('symbol_results', {}).get(symbol, {}).get('sideways_signals', 0)
            }
            
            logger.info(f"Kết quả {symbol}: {symbol_trades} giao dịch, Win rate: {symbol_win_rate:.2f}%, Profit: {symbol_profit_pct:.2f}%")
            
        except Exception as e:
            logger.error(f"Lỗi khi backtest {symbol}: {e}")
            logger.error(traceback.format_exc())
            results[symbol] = {'error': str(e)}
    
    # Tính toán thống kê tổng thể
    total_win_rate = (winning_trades_count / total_trades_count * 100) if total_trades_count > 0 else 0
    
    # Phân tích hiệu suất chiến lược
    ma_signals_count = sum(result.get('ma_signals', 0) for result in results.values() if isinstance(result, dict) and 'ma_signals' in result)
    sideways_signals_count = sum(result.get('sideways_signals', 0) for result in results.values() if isinstance(result, dict) and 'sideways_signals' in result)
    
    # Phân tích trades theo loại tín hiệu
    ma_trades = [t for t in all_trades if 'crossover' in t.get('signal_source', '')]
    sideways_trades = [t for t in all_trades if t.get('sideways_period', False)]
    
    ma_win_count = sum(1 for t in ma_trades if t.get('profit', 0) > 0)
    sideways_win_count = sum(1 for t in sideways_trades if t.get('profit', 0) > 0)
    
    ma_win_rate = (ma_win_count / len(ma_trades) * 100) if len(ma_trades) > 0 else 0
    sideways_win_rate = (sideways_win_count / len(sideways_trades) * 100) if len(sideways_trades) > 0 else 0
    
    # Tạo báo cáo tổng hợp
    summary = {
        'test_time': datetime.now().isoformat(),
        'symbols': symbols,
        'period': period,
        'timeframe': timeframe,
        'total_trades': total_trades_count,
        'winning_trades': winning_trades_count,
        'losing_trades': losing_trades_count,
        'win_rate': total_win_rate,
        'strategy_performance': {
            'ma_crossover': {
                'signals': ma_signals_count,
                'trades': len(ma_trades),
                'wins': ma_win_count,
                'win_rate': ma_win_rate
            },
            'sideways_market': {
                'signals': sideways_signals_count,
                'trades': len(sideways_trades),
                'wins': sideways_win_count,
                'win_rate': sideways_win_rate
            }
        },
        'symbol_results': results
    }
    
    # Lưu báo cáo tổng hợp
    with open(f'backtest_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(summary, f, indent=4, default=str)
    
    # In báo cáo tóm tắt
    logger.info("\n=== BÁO CÁO TÓM TẮT ===")
    logger.info(f"Tổng số giao dịch: {total_trades_count}")
    logger.info(f"Giao dịch thắng/thua: {winning_trades_count}/{losing_trades_count}")
    logger.info(f"Tỷ lệ thắng tổng thể: {total_win_rate:.2f}%")
    logger.info("\nHiệu suất theo chiến lược:")
    logger.info(f"- MA Crossover: {ma_win_count}/{len(ma_trades)} thắng ({ma_win_rate:.2f}%)")
    logger.info(f"- Sideways Market: {sideways_win_count}/{len(sideways_trades)} thắng ({sideways_win_rate:.2f}%)")
    logger.info("\nHiệu suất theo symbol:")
    
    for symbol, result in results.items():
        if 'error' in result:
            logger.info(f"- {symbol}: LỖI - {result['error']}")
        else:
            logger.info(f"- {symbol}: {result['trades']} giao dịch, Win rate: {result['win_rate']:.2f}%, Profit: {result['profit_pct']:.2f}%")
    
    # Phân tích rủi ro
    logger.info("\n=== PHÂN TÍCH RỦI RO ===")
    
    # 1. Kiểm tra drawdown
    if all_trades:
        # Sắp xếp giao dịch theo thứ tự thời gian
        sorted_trades = sorted(all_trades, key=lambda x: x.get('entry_date', datetime.min))
        
        # Tính equity curve
        equity = [initial_balance]
        max_equity = initial_balance
        max_drawdown = 0
        max_drawdown_pct = 0
        
        for trade in sorted_trades:
            profit = trade.get('profit', 0)
            equity.append(equity[-1] + profit)
            
            if equity[-1] > max_equity:
                max_equity = equity[-1]
            else:
                drawdown = max_equity - equity[-1]
                drawdown_pct = (drawdown / max_equity) * 100
                if drawdown_pct > max_drawdown_pct:
                    max_drawdown = drawdown
                    max_drawdown_pct = drawdown_pct
        
        logger.info(f"Max Drawdown: ${max_drawdown:.2f} ({max_drawdown_pct:.2f}%)")
    
    # 2. Kiểm tra consecutive losses (chuỗi thua liên tiếp)
    if all_trades:
        sorted_trades = sorted(all_trades, key=lambda x: x.get('entry_date', datetime.min))
        
        max_consecutive_losses = 0
        current_consecutive_losses = 0
        
        for trade in sorted_trades:
            if trade.get('profit', 0) < 0:
                current_consecutive_losses += 1
                if current_consecutive_losses > max_consecutive_losses:
                    max_consecutive_losses = current_consecutive_losses
            else:
                current_consecutive_losses = 0
        
        logger.info(f"Chuỗi thua dài nhất: {max_consecutive_losses} giao dịch")
    
    # 3. Phân tích hiệu suất theo biến động thị trường
    high_volatility_trades = [t for t in all_trades if t.get('volatility', 'normal') == 'high']
    low_volatility_trades = [t for t in all_trades if t.get('volatility', 'normal') == 'low']
    
    high_vol_win_count = sum(1 for t in high_volatility_trades if t.get('profit', 0) > 0)
    low_vol_win_count = sum(1 for t in low_volatility_trades if t.get('profit', 0) > 0)
    
    high_vol_win_rate = (high_vol_win_count / len(high_volatility_trades) * 100) if len(high_volatility_trades) > 0 else 0
    low_vol_win_rate = (low_vol_win_count / len(low_volatility_trades) * 100) if len(low_volatility_trades) > 0 else 0
    
    logger.info(f"Win rate trong biến động cao: {high_vol_win_rate:.2f}%")
    logger.info(f"Win rate trong biến động thấp: {low_vol_win_rate:.2f}%")
    
    # Kết luận và đề xuất
    logger.info("\n=== KẾT LUẬN VÀ ĐỀ XUẤT ===")
    
    if total_win_rate > 50:
        logger.info("Chiến lược hoạt động tốt với tỷ lệ thắng > 50%")
    else:
        logger.info("Chiến lược cần cải thiện với tỷ lệ thắng < 50%")
    
    if sideways_win_rate > ma_win_rate:
        logger.info("Chiến lược Sideways Market Detection hoạt động tốt hơn MA Crossover")
    else:
        logger.info("Chiến lược MA Crossover hoạt động tốt hơn Sideways Market Detection")
    
    if max_drawdown_pct > 20:
        logger.info("Cảnh báo: Drawdown cao (>20%), cần cải thiện quản lý rủi ro")
    
    if max_consecutive_losses > 5:
        logger.info("Cảnh báo: Nhiều giao dịch thua liên tiếp, kiểm tra lại bộ lọc tín hiệu")
    
    # Đề xuất cải thiện
    logger.info("\nĐề xuất cải thiện:")
    logger.info("1. Thêm bộ lọc tín hiệu giả theo xu hướng thị trường tổng thể")
    logger.info("2. Tối ưu hóa tham số ATR cho Stop Loss trong biến động cao")
    logger.info("3. Cải thiện chiến lược chốt lời từng phần dựa trên biến động thị trường")
    logger.info("4. Thêm bộ lọc khối lượng giao dịch cho các tín hiệu")
    logger.info("5. Kiểm tra sức khỏe API và xử lý lỗi kết nối")
    
    return summary

if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"Bắt đầu backtest đơn giản lúc: {start_time}")
    
    try:
        summary = run_simplified_test()
        logger.info(f"Đã hoàn thành backtest đơn giản")
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest đơn giản: {e}")
        logger.error(traceback.format_exc())
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Kết thúc backtest đơn giản lúc: {end_time}")
    logger.info(f"Tổng thời gian thực hiện: {duration}")
