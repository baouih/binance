#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy backtest trên nhiều khung thời gian (30m, 1h, 4h, 1d) 
và so sánh hiệu suất của hệ thống
"""

import os
import json
import logging
import pandas as pd
from pathlib import Path

from run_realistic_backtest import RealisticBacktest
from adaptive_risk_manager import AdaptiveRiskManager
from adaptive_strategy_selector import AdaptiveStrategySelector

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multi_timeframe_backtest.log')
    ]
)

logger = logging.getLogger('multi_timeframe_backtest')

def run_backtest_for_timeframe(symbol, timeframe, test_period, initial_balance):
    """
    Chạy backtest cho một khung thời gian cụ thể
    
    Args:
        symbol (str): Cặp tiền
        timeframe (str): Khung thời gian
        test_period (int): Số ngày test
        initial_balance (float): Số dư ban đầu
        
    Returns:
        dict: Kết quả backtest
    """
    logger.info(f"Chạy backtest cho {symbol} trên khung thời gian {timeframe}")
    
    # Khởi tạo các thành phần
    risk_manager = AdaptiveRiskManager()
    strategy_selector = AdaptiveStrategySelector()
    
    # Khởi tạo backtest
    try:
        # Khởi tạo đối tượng backtest với các tham số
        backtest = RealisticBacktest(symbol, timeframe, test_period, initial_balance)
        
        # Tải dữ liệu
        if not backtest.load_data():
            logger.error(f"Không tải được dữ liệu cho {symbol}_{timeframe}")
            raise Exception(f"Không tải được dữ liệu cho {symbol}_{timeframe}")
        
        # Chạy backtest
        results = backtest.run_backtest()
        
        # Xác định chiến lược chính dựa trên số lượng giao dịch
        primary_strategy = "unknown"
        max_trades = 0
        
        if 'strategy_stats' in results:
            for strategy, stats in results['strategy_stats'].items():
                if stats['total_trades'] > max_trades:
                    max_trades = stats['total_trades']
                    primary_strategy = strategy
        
        # Tạo báo cáo chi tiết
        backtest_report = {
            'symbol': symbol,
            'timeframe': timeframe,
            'period': test_period,
            'initial_balance': initial_balance,
            'final_balance': results['final_balance'],
            'profit_loss_pct': results['total_profit_pct'],  # Sử dụng đúng tên trường
            'win_rate': results['win_rate'],
            'total_trades': results['total_trades'],
            'winning_trades': results['winning_trades'],
            'losing_trades': results['losing_trades'],
            'strategy_stats': results['strategy_stats']
        }
        
        # Lưu báo cáo chi tiết
        report_path = f"backtest_reports/{symbol}_{timeframe}_{test_period}d.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(backtest_report, f, indent=2)
        
        logger.info(f"Đã lưu báo cáo chi tiết cho {symbol} {timeframe} tại {report_path}")
        
        # Tạo báo cáo tóm tắt
        summary = {
            'profit_loss_pct': results['total_profit_pct'],  # Sử dụng đúng tên trường
            'win_rate': results['win_rate'],
            'total_trades': results['total_trades'],
            'primary_strategy': primary_strategy
        }
        
        return summary
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest cho {symbol} {timeframe}: {str(e)}")
        return {
            'profit_loss_pct': 0,
            'win_rate': 0,
            'total_trades': 0,
            'primary_strategy': 'unknown'
        }

def main():
    """
    Hàm chính - Chạy backtest trên nhiều khung thời gian
    """
    logger.info("=== BẮT ĐẦU BACKTEST ĐA KHUNG THỜI GIAN ===")
    
    # Danh sách cặp tiền (chỉ test BTC vì chúng ta đã tạo dữ liệu cho BTC)
    symbols = ["BTCUSDT"]
    timeframes = ["30m", "1h", "4h", "1d"]
    
    # Điều chỉnh thời gian test dựa trên khung thời gian 
    # để có số lượng nến tương đương giữa các khung thời gian
    test_periods = {
        "30m": 10,  # 10 ngày với nến 30m
        "1h": 20,   # 20 ngày với nến 1h
        "4h": 40,   # 40 ngày với nến 4h
        "1d": 80    # 80 ngày với nến 1d
    }
    
    initial_balance = 10000  # Số dư ban đầu
    
    # Lưu kết quả tổng hợp
    combined_results = {
        'by_timeframe': {},
        'by_symbol': {},
        'by_strategy': {},
        'overall': {
            'timeframes': {},
            'best_timeframe': None,
            'best_pl': -float('inf')
        }
    }
    
    # Lặp qua từng cặp tiền
    for symbol in symbols:
        combined_results['by_symbol'][symbol] = {}
        
        # Lặp qua từng khung thời gian
        for timeframe in timeframes:
            # Lấy số ngày test phù hợp cho khung thời gian này
            test_period = test_periods[timeframe]
            
            # Chạy backtest
            results = run_backtest_for_timeframe(symbol, timeframe, test_period, initial_balance)
            
            # Lưu kết quả
            if timeframe not in combined_results['by_timeframe']:
                combined_results['by_timeframe'][timeframe] = {
                    'symbols': {},
                    'avg_profit_loss_pct': 0,
                    'avg_win_rate': 0,
                    'total_trades': 0
                }
            
            combined_results['by_timeframe'][timeframe]['symbols'][symbol] = results
            combined_results['by_symbol'][symbol][timeframe] = results
            
            # Cập nhật thông tin chiến lược
            strategy = results['primary_strategy']
            if strategy not in combined_results['by_strategy']:
                combined_results['by_strategy'][strategy] = {
                    'usage_count': 0,
                    'avg_profit_loss_pct': 0,
                    'avg_win_rate': 0,
                    'total_trades': 0
                }
            
            # Cập nhật thống kê chiến lược
            strat_data = combined_results['by_strategy'][strategy]
            strat_data['usage_count'] += 1
            strat_data['avg_profit_loss_pct'] = (strat_data['avg_profit_loss_pct'] * (strat_data['usage_count'] - 1) + results['profit_loss_pct']) / strat_data['usage_count']
            strat_data['avg_win_rate'] = (strat_data['avg_win_rate'] * (strat_data['usage_count'] - 1) + results['win_rate']) / strat_data['usage_count']
            strat_data['total_trades'] += results['total_trades']
            
            # Cập nhật thống kê cho khung thời gian
            tf_data = combined_results['by_timeframe'][timeframe]
            tf_data['avg_profit_loss_pct'] = sum([r['profit_loss_pct'] for r in tf_data['symbols'].values()]) / len(tf_data['symbols'])
            tf_data['avg_win_rate'] = sum([r['win_rate'] for r in tf_data['symbols'].values()]) / len(tf_data['symbols'])
            tf_data['total_trades'] = sum([r['total_trades'] for r in tf_data['symbols'].values()])
            
            # Kiểm tra xem khung thời gian này có hiệu suất tốt nhất không
            if results['profit_loss_pct'] > combined_results['overall']['best_pl']:
                combined_results['overall']['best_pl'] = results['profit_loss_pct']
                combined_results['overall']['best_timeframe'] = timeframe
    
    # Tính toán thống kê tổng hợp cho mỗi khung thời gian
    for timeframe in timeframes:
        tf_data = combined_results['by_timeframe'][timeframe]
        combined_results['overall']['timeframes'][timeframe] = {
            'avg_profit_loss_pct': tf_data['avg_profit_loss_pct'],
            'avg_win_rate': tf_data['avg_win_rate'],
            'total_trades': tf_data['total_trades']
        }
    
    # Lưu tổng kết
    summary_path = "backtest_summary/multi_timeframe_summary.json"
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump(combined_results, f, indent=2)
    
    logger.info(f"Đã lưu tổng kết vào {summary_path}")
    
    # In kết quả
    logger.info("=== KẾT QUẢ BACKTEST ĐA KHUNG THỜI GIAN ===")
    logger.info(f"Khung thời gian tốt nhất: {combined_results['overall']['best_timeframe']} với P/L: {combined_results['overall']['best_pl']:.2f}%")
    
    for timeframe in timeframes:
        tf_data = combined_results['overall']['timeframes'][timeframe]
        logger.info(f"- {timeframe}: P/L: {tf_data['avg_profit_loss_pct']:.2f}%, WR: {tf_data['avg_win_rate']:.2f}%, Giao dịch: {tf_data['total_trades']}")

if __name__ == "__main__":
    main()