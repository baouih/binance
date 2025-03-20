#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug cho adaptive backtest
"""

import pandas as pd
import numpy as np
import yfinance as yf
import logging
from sideways_market_detector import SidewaysMarketDetector

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('debug_backtest')

def main():
    """Hàm chính"""
    # Tải dữ liệu
    symbol = 'BTC-USD'
    period = '1mo'
    timeframe = '1d'
    
    logger.info(f"Tải dữ liệu {symbol} trong {period} với khung thời gian {timeframe}")
    data = yf.download(symbol, period=period, interval=timeframe)
    logger.info(f"Đã tải {len(data)} dòng dữ liệu")
    
    # Khởi tạo bộ phát hiện sideways market
    logger.info("Khởi tạo SidewaysMarketDetector")
    detector = SidewaysMarketDetector()
    
    try:
        # Tính các chỉ báo
        logger.info("Tính toán chỉ báo...")
        indicators_data = detector.calculate_indicators(data)
        logger.info("Chỉ báo đã được tính toán thành công")
        
        # In ra các cột trong dữ liệu
        logger.info(f"Các cột trong dữ liệu: {indicators_data.columns.tolist()}")
        
        # Kiểm tra cột atr_volatility
        logger.info(f"Loại dữ liệu của atr_volatility: {indicators_data['atr_volatility'].dtype}")
        logger.info(f"Mẫu dữ liệu atr_volatility: {indicators_data['atr_volatility'].head()}")
        
        # Thực hiện phát hiện thị trường đi ngang
        logger.info("Phát hiện thị trường đi ngang...")
        processed_data, sideways_periods = detector.detect_sideways_market(data)
        logger.info(f"Đã phát hiện {len(sideways_periods)} giai đoạn thị trường đi ngang")
        
        logger.info("Hoàn thành debug!")
    
    except Exception as e:
        logger.error(f"Lỗi trong quá trình debug: {e}")
        # Import traceback để in chi tiết lỗi
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()