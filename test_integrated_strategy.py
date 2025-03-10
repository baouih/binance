#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Script cho Chiến lược Tích hợp Mới

Script này chạy backtest sử dụng chiến lược tích hợp mới với các tính năng:
- RSI phân loại 3 mức
- Fibonacci retracement
- ATR-based stop loss
- Market regime detection

Sử dụng: python test_integrated_strategy.py --symbol BTCUSDT --interval 1h --lookback 90
"""

import os
import sys
import argparse
import logging
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("integrated_strategy_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('test_integrated_strategy')

from ml_strategy_tester import MLStrategyTester

def main():
    """
    Hàm chính
    """
    # Thiết lập parser dòng lệnh
    parser = argparse.ArgumentParser(description='Test chiến lược tích hợp mới')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã tiền (mặc định: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--lookback', type=int, default=90, help='Số ngày lịch sử (mặc định: 90)')
    parser.add_argument('--risk', type=float, default=5, help='Phần trăm rủi ro mỗi lệnh (mặc định: 5%)')
    parser.add_argument('--leverage', type=float, default=1, help='Đòn bẩy (mặc định: 1x)')
    parser.add_argument('--simulation', action='store_true', help='Chế độ mô phỏng (mặc định: False)')
    parser.add_argument('--data-dir', type=str, help='Thư mục chứa dữ liệu lịch sử')
    parser.add_argument('--model', type=str, default='BTCUSDT_1h_3m_target3d', help='Tên mô hình ML')
    
    args = parser.parse_args()
    
    # In các tham số
    logger.info(f"===== Tham số Test =====")
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Interval: {args.interval}")
    logger.info(f"Lookback days: {args.lookback}")
    logger.info(f"Risk %: {args.risk}")
    logger.info(f"Leverage: {args.leverage}")
    logger.info(f"ML Model: {args.model}")
    logger.info(f"Simulation mode: {args.simulation}")
    logger.info(f"Data directory: {args.data_dir if args.data_dir else 'Using API'}")
    
    # Khởi tạo tester
    tester = MLStrategyTester(simulation_mode=args.simulation, data_dir=args.data_dir)
    
    # Chạy backtest chiến lược tích hợp
    result = tester.integrate_ml_with_high_risk(
        symbol=args.symbol,
        interval=args.interval,
        best_ml_model=args.model,
        lookback_days=args.lookback,
        risk_pct=args.risk,
        leverage=args.leverage
    )
    
    # In kết quả
    if isinstance(result, dict) and 'error' not in result:
        logger.info(f"===== Kết quả Test =====")
        
        # In thông tin cơ bản
        logger.info(f"Symbol: {args.symbol}, Interval: {args.interval}, Lookback: {args.lookback} days")
        
        # In bảng xếp hạng
        logger.info(f"Xếp hạng chiến lược:")
        for rank_item in result['ranking']:
            logger.info(f"  {rank_item['rank']}. {rank_item['strategy']}: {rank_item['profit_pct']:.2f}% (Win rate: {rank_item['win_rate']:.2f}%, Trades: {rank_item['trades']})")
        
        # In chi tiết chiến lược tích hợp
        integrated_result = result['detailed_results']['integrated']
        logger.info(f"\nChi tiết chiến lược tích hợp:")
        logger.info(f"  Lợi nhuận: {integrated_result['profit_pct']:.2f}%")
        logger.info(f"  Max drawdown: {integrated_result['max_drawdown']:.2f}%")
        logger.info(f"  Số giao dịch: {integrated_result['stats']['total_trades']}")
        logger.info(f"  Win rate: {integrated_result['stats']['win_rate']:.2f}%")
        logger.info(f"  Profit factor: {integrated_result['stats']['profit_factor']:.2f}")
        logger.info(f"  Avg win: {integrated_result['stats']['avg_win_pct']:.2f}%")
        logger.info(f"  Avg loss: {integrated_result['stats']['avg_loss_pct']:.2f}%")
        logger.info(f"  Sharpe ratio: {integrated_result['stats']['sharpe_ratio']:.2f}")
        
        # Path to charts
        charts_dir = os.path.join('ml_test_charts', f"{args.symbol}_{args.interval}")
        logger.info(f"\nBiểu đồ đã được lưu tại thư mục: {charts_dir}")
        
        return result
    else:
        error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
        logger.error(f"Lỗi khi chạy backtest: {error_msg}")
        return None

if __name__ == "__main__":
    main()