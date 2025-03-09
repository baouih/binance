#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script giao diện dòng lệnh để chạy backtest

Script này cung cấp giao diện dòng lệnh để chạy backtest với các tùy chọn khác nhau:
- Chọn cặp tiền và khung thời gian
- Thiết lập phạm vi backtest
- Cấu hình quản lý vốn và rủi ro
- Bật/tắt các tính năng như trailing stop, chỉ báo tổng hợp
"""

import os
import sys
import json
import time
import logging
import argparse
import datetime
from typing import Dict, List, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('run_backtest')

# Kiểm tra và import các module cần thiết
try:
    from comprehensive_backtest import ComprehensiveBacktest, create_sample_data
except ImportError as e:
    logger.error(f"Không thể import các module cần thiết: {str(e)}")
    logger.error("Hãy đảm bảo rằng các module này đã được cài đặt.")
    sys.exit(1)

def run_backtest(args):
    """
    Chạy backtest với các tham số từ dòng lệnh
    
    Args:
        args: Tham số từ argparse
    """
    # Chuẩn bị cấu hình
    config = {
        "symbols": args.symbols,
        "timeframes": args.timeframes,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "initial_balance": args.initial_balance,
        "max_open_positions": args.max_positions,
        "commission_rate": args.commission / 100,  # Chuyển từ phần trăm sang phần nghìn
        "slippage": args.slippage / 100,  # Chuyển từ phần trăm sang phần nghìn
        "trailing_stop": {
            "enabled": args.trailing_stop,
            "strategy_type": args.ts_strategy,
            "activation_percent": args.ts_activation,
            "callback_percent": args.ts_callback
        },
        "risk_management": {
            "base_risk_percentage": args.risk_percentage,
            "max_risk_per_trade": args.max_risk_per_trade,
            "dynamic_risk_adjustment": args.dynamic_risk,
            "max_risk_per_day": args.max_risk_per_day
        },
        "position_sizing": {
            "method": args.position_sizing,
            "fixed_usd_amount": args.fixed_usd,
            "fixed_pct_balance": args.fixed_pct
        }
    }
    
    # Tạo thư mục cấu hình
    os.makedirs('configs', exist_ok=True)
    
    # Lưu cấu hình
    config_path = args.config if args.config else 'configs/backtest_config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    logger.info(f"Đã lưu cấu hình backtest tại {config_path}")
    
    # Kiểm tra dữ liệu
    if args.create_sample_data or not os.path.exists('backtest_data') or len(os.listdir('backtest_data')) == 0:
        logger.info("Tạo dữ liệu mẫu cho backtest")
        create_sample_data()
    
    # Chạy backtest
    backtest = ComprehensiveBacktest(config_path)
    
    # Đo thời gian chạy
    start_time = time.time()
    logger.info("Bắt đầu chạy backtest")
    
    # Chạy backtest
    results = backtest.run_backtest()
    
    # Thời gian chạy
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Thời gian chạy backtest: {duration:.2f} giây")
    
    # Tạo báo cáo HTML
    if args.html_report:
        html_report = backtest.create_html_report(results)
        logger.info(f"Đã tạo báo cáo HTML tại {html_report}")

def parse_args():
    """
    Phân tích tham số dòng lệnh
    
    Returns:
        argparse.Namespace: Các tham số dòng lệnh
    """
    parser = argparse.ArgumentParser(description='Chạy backtest cho hệ thống giao dịch')
    
    # Nhóm cấu hình cơ bản
    basic_group = parser.add_argument_group('Cấu hình cơ bản')
    basic_group.add_argument('--symbols', type=str, nargs='+', default=['BTCUSDT'], help='Danh sách các cặp tiền')
    basic_group.add_argument('--timeframes', type=str, nargs='+', default=['1h'], help='Danh sách các khung thời gian')
    basic_group.add_argument('--start-date', type=str, default='2023-01-01', help='Ngày bắt đầu (YYYY-MM-DD)')
    basic_group.add_argument('--end-date', type=str, default='2023-12-31', help='Ngày kết thúc (YYYY-MM-DD)')
    basic_group.add_argument('--initial-balance', type=float, default=10000, help='Số dư ban đầu')
    basic_group.add_argument('--max-positions', type=int, default=5, help='Số lượng vị thế tối đa')
    basic_group.add_argument('--commission', type=float, default=0.04, help='Phí giao dịch (phần trăm)')
    basic_group.add_argument('--slippage', type=float, default=0.01, help='Slippage (phần trăm)')
    
    # Nhóm quản lý vốn và rủi ro
    risk_group = parser.add_argument_group('Quản lý vốn và rủi ro')
    risk_group.add_argument('--risk-percentage', type=float, default=1.0, help='Phần trăm rủi ro cơ sở (phần trăm)')
    risk_group.add_argument('--max-risk-per-trade', type=float, default=2.0, help='Phần trăm rủi ro tối đa cho một giao dịch (phần trăm)')
    risk_group.add_argument('--max-risk-per-day', type=float, default=5.0, help='Phần trăm rủi ro tối đa cho một ngày (phần trăm)')
    risk_group.add_argument('--dynamic-risk', action='store_true', help='Bật điều chỉnh rủi ro động')
    
    # Nhóm position sizing
    sizing_group = parser.add_argument_group('Position Sizing')
    sizing_group.add_argument('--position-sizing', type=str, choices=['risk_based', 'fixed_usd', 'fixed_pct'], default='risk_based',
                           help='Phương pháp tính kích thước vị thế')
    sizing_group.add_argument('--fixed-usd', type=float, default=100, help='Số tiền cố định cho fixed_usd (USD)')
    sizing_group.add_argument('--fixed-pct', type=float, default=5.0, help='Phần trăm cố định cho fixed_pct (phần trăm)')
    
    # Nhóm trailing stop
    ts_group = parser.add_argument_group('Trailing Stop')
    ts_group.add_argument('--trailing-stop', action='store_true', help='Bật trailing stop')
    ts_group.add_argument('--ts-strategy', type=str, choices=['percentage', 'absolute', 'atr', 'psar', 'step'], default='percentage',
                       help='Chiến lược trailing stop')
    ts_group.add_argument('--ts-activation', type=float, default=0.5, help='Phần trăm kích hoạt trailing stop (phần trăm)')
    ts_group.add_argument('--ts-callback', type=float, default=0.2, help='Phần trăm callback trailing stop (phần trăm)')
    
    # Nhóm khác
    misc_group = parser.add_argument_group('Khác')
    misc_group.add_argument('--config', type=str, help='Đường dẫn đến file cấu hình')
    misc_group.add_argument('--html-report', action='store_true', help='Tạo báo cáo HTML')
    misc_group.add_argument('--create-sample-data', action='store_true', help='Tạo dữ liệu mẫu cho backtest')
    
    return parser.parse_args()

def main():
    """Hàm chính để chạy backtest từ dòng lệnh"""
    args = parse_args()
    run_backtest(args)

if __name__ == "__main__":
    main()