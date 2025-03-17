#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module tải dữ liệu lịch sử đồng loạt cho tất cả các coin từ cấu hình
"""

import os
import sys
import time
import json
import logging
import subprocess
import datetime
import argparse
from typing import List, Dict, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_all_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('data_downloader_all')

def load_config(config_path='comprehensive_backtest_config.json'):
    """Tải tập tin cấu hình"""
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
            logger.info(f"Đã tải cấu hình từ {config_path}")
            return config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {e}")
        sys.exit(1)

def download_data_for_symbol(symbol, timeframe, start_date, end_date, use_testnet=False):
    """Tải dữ liệu cho một symbol và timeframe cụ thể"""
    try:
        cmd = [
            "python", "download_historical_data.py",
            symbol, timeframe,
            "--start", start_date,
            "--end", end_date
        ]
        
        if use_testnet:
            cmd.append("--testnet")
        
        logger.info(f"Thực thi: {' '.join(cmd)}")
        
        # Chạy script download_historical_data.py
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Tải thành công dữ liệu cho {symbol} ({timeframe})")
            return True
        else:
            logger.error(f"Lỗi khi tải dữ liệu cho {symbol} ({timeframe}): {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy lệnh tải dữ liệu cho {symbol} ({timeframe}): {str(e)}")
        return False

def parse_arguments():
    """Xử lý tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Tải dữ liệu lịch sử Binance cho nhiều coin")
    parser.add_argument("--config", help="Đường dẫn đến tập tin cấu hình", default="comprehensive_backtest_config.json")
    parser.add_argument("--start", help="Ngày bắt đầu (YYYY-MM-DD)", default="2024-02-01")
    parser.add_argument("--end", help="Ngày kết thúc (YYYY-MM-DD)", default="2024-03-15")
    parser.add_argument("--testnet", help="Sử dụng testnet", action="store_true")
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    # Xử lý tham số
    args = parse_arguments()
    
    # Tải cấu hình
    config = load_config(args.config)
    
    # Lấy danh sách symbols và timeframes
    symbols = config.get('symbols', [])
    timeframes = config.get('timeframes', [])
    
    if not symbols:
        logger.error("Không tìm thấy danh sách symbols trong cấu hình. Dừng.")
        return 1
    
    if not timeframes:
        logger.error("Không tìm thấy danh sách timeframes trong cấu hình. Dừng.")
        return 1
    
    logger.info(f"Chuẩn bị tải dữ liệu cho {len(symbols)} symbols và {len(timeframes)} timeframes")
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Timeframes: {', '.join(timeframes)}")
    logger.info(f"Khoảng thời gian: {args.start} đến {args.end}")
    
    # Tạo thư mục data nếu chưa tồn tại
    os.makedirs("data", exist_ok=True)
    
    # Biến đếm
    total_tasks = len(symbols) * len(timeframes)
    successful_tasks = 0
    failed_tasks = 0
    
    # Lặp qua tất cả symbols và timeframes để tải dữ liệu
    for symbol in symbols:
        for timeframe in timeframes:
            logger.info(f"Đang tải dữ liệu cho {symbol} ({timeframe})...")
            
            # Tải dữ liệu
            success = download_data_for_symbol(
                symbol=symbol,
                timeframe=timeframe,
                start_date=args.start,
                end_date=args.end,
                use_testnet=args.testnet
            )
            
            if success:
                successful_tasks += 1
            else:
                failed_tasks += 1
            
            # Tiến độ
            progress = (successful_tasks + failed_tasks) / total_tasks * 100
            logger.info(f"Tiến độ: {progress:.1f}% ({successful_tasks + failed_tasks}/{total_tasks})")
            
            # Chờ 1 giây để tránh rate limit
            time.sleep(1)
    
    # Tổng kết
    logger.info("=== KẾT QUẢ TẢI DỮ LIỆU ===")
    logger.info(f"Tổng số tasks: {total_tasks}")
    logger.info(f"Thành công: {successful_tasks}")
    logger.info(f"Thất bại: {failed_tasks}")
    logger.info(f"Tỷ lệ thành công: {successful_tasks / total_tasks * 100:.1f}%")
    
    return 0 if failed_tasks == 0 else 1

if __name__ == "__main__":
    sys.exit(main())