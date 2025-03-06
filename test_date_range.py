#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script thử nghiệm tính năng lọc phạm vi ngày tháng trong backtesting

Script này thực hiện backtest với các khoảng thời gian khác nhau 
để minh họa tính năng mới của hệ thống backtesting với phạm vi ngày tùy chỉnh.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from enhanced_backtest import run_adaptive_backtest

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('date_range_test.log')
    ]
)

logger = logging.getLogger('date_range_test')

def run_period_tests(symbol='BTCUSDT', interval='1h'):
    """
    Chạy các bài test với nhiều khoảng thời gian khác nhau
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
    """
    logger.info(f"=== BẮT ĐẦU KIỂM TRA TÍNH NĂNG LỌC PHẠM VI NGÀY THÁNG ===")
    logger.info(f"Symbol: {symbol}, Interval: {interval}")
    
    # Các khoảng thời gian kiểm thử - dựa trên dữ liệu thực tế có sẵn (tháng 2/2024)
    test_periods = [
        {
            'name': 'Tuần đầu tháng 2/2024',
            'start_date': '2024-02-01',
            'end_date': '2024-02-07'
        },
        {
            'name': 'Tuần thứ hai tháng 2/2024',
            'start_date': '2024-02-08',
            'end_date': '2024-02-14'
        },
        {
            'name': 'Tuần thứ ba tháng 2/2024',
            'start_date': '2024-02-15',
            'end_date': '2024-02-21'
        },
        {
            'name': 'Tuần cuối tháng 2/2024',
            'start_date': '2024-02-22',
            'end_date': '2024-02-28'
        }
    ]
    
    # Chạy test cho từng khoảng thời gian
    for period in test_periods:
        logger.info(f"\n========== TEST: {period['name']} ==========")
        logger.info(f"Phạm vi thời gian: {period['start_date']} đến {period['end_date']}")
        
        # Chạy backtest với khoảng thời gian này
        run_adaptive_backtest(
            symbol=symbol,
            interval=interval,
            initial_balance=10000.0,
            leverage=3,
            risk_percentage=1.0,
            stop_loss_pct=7.0,
            take_profit_pct=15.0,
            use_adaptive_risk=True,
            data_dir='test_data',
            start_date=period['start_date'],
            end_date=period['end_date']
        )
        
        logger.info(f"========== KẾT THÚC TEST: {period['name']} ==========\n")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Kiểm thử tính năng lọc phạm vi ngày tháng')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã cặp giao dịch')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian')
    
    args = parser.parse_args()
    
    run_period_tests(
        symbol=args.symbol,
        interval=args.interval
    )

if __name__ == "__main__":
    main()