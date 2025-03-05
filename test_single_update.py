#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kiểm thử cập nhật đơn cặp tiền

Script này kiểm tra chức năng cập nhật phân tích thị trường của một cặp tiền cụ thể.
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("single_update_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("single_update_test")

# Import các module cần thiết
try:
    from market_data_updater import MarketDataUpdater
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {e}")
    sys.exit(1)

def test_single_update(symbol: str, timeframe: str = '1h'):
    """
    Kiểm tra cập nhật một cặp tiền cụ thể
    
    Args:
        symbol (str): Mã cặp tiền
        timeframe (str): Khung thời gian
    """
    logger.info(f"Bắt đầu kiểm tra cập nhật {symbol} ({timeframe})")
    
    try:
        # Khởi tạo MarketDataUpdater
        updater = MarketDataUpdater()
        
        # Thời gian bắt đầu
        start_time = time.time()
        
        # Cập nhật dữ liệu thị trường
        success = updater.update_symbol(symbol, timeframe)
        
        # Thời gian kết thúc
        end_time = time.time()
        duration = end_time - start_time
        
        if success:
            logger.info(f"Cập nhật {symbol} thành công ({duration:.2f}s)")
            
            # Kiểm tra file kết quả có tồn tại không
            recommendation_file = f"recommendation_{symbol.lower()}.json"
            analysis_file = f"market_analysis_{symbol.lower()}.json"
            
            if os.path.exists(recommendation_file):
                file_time = datetime.fromtimestamp(os.path.getmtime(recommendation_file))
                logger.info(f"File khuyến nghị {recommendation_file} được cập nhật lúc {file_time}")
            else:
                logger.warning(f"Không tìm thấy file khuyến nghị {recommendation_file}")
            
            if os.path.exists(analysis_file):
                file_time = datetime.fromtimestamp(os.path.getmtime(analysis_file))
                logger.info(f"File phân tích {analysis_file} được cập nhật lúc {file_time}")
            else:
                logger.warning(f"Không tìm thấy file phân tích {analysis_file}")
                
            return True
        else:
            logger.error(f"Cập nhật {symbol} thất bại ({duration:.2f}s)")
            return False
            
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật {symbol}: {e}")
        return False

def main():
    """Hàm chính"""
    # Phân tích tham số dòng lệnh
    parser = argparse.ArgumentParser(description='Kiểm tra cập nhật đơn cặp tiền')
    parser.add_argument('symbol', type=str, help='Mã cặp tiền (ví dụ: BTCUSDT)')
    parser.add_argument('--timeframe', type=str, default='1h', help='Khung thời gian (mặc định: 1h)')
    args = parser.parse_args()
    
    # Chuẩn hóa symbol và timeframe
    symbol = args.symbol.upper()
    timeframe = args.timeframe.lower()
    
    logger.info(f"Kiểm tra cập nhật {symbol} ({timeframe})")
    
    # Chạy kiểm tra
    result = test_single_update(symbol, timeframe)
    
    # Kết quả
    if result:
        logger.info(f"Kiểm tra cập nhật {symbol} ({timeframe}) thành công")
        return 0
    else:
        logger.error(f"Kiểm tra cập nhật {symbol} ({timeframe}) thất bại")
        return 1

if __name__ == "__main__":
    sys.exit(main())