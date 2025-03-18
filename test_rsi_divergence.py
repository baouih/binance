#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test RSI Divergence Detector

Script này thực hiện kiểm thử bộ phát hiện RSI Divergence trên dữ liệu thị trường thật.
"""

import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import yfinance as yf
import argparse

# Import các module đã phát triển
from rsi_divergence_detector import RSIDivergenceDetector
from sideways_market_optimizer import SidewaysMarketOptimizer

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_rsi_divergence.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('test_rsi_divergence')

def load_data(symbol, period='3mo', interval='1d'):
    """
    Tải dữ liệu thị trường
    
    Args:
        symbol (str): Ký hiệu tiền tệ
        period (str): Khoảng thời gian
        interval (str): Khung thời gian
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLC
    """
    try:
        logger.info(f"Đang tải dữ liệu {symbol} ({interval}, {period})")
        df = yf.download(symbol, period=period, interval=interval)
        
        # Kiểm tra xem df có phải là DataFrame không
        if not isinstance(df, pd.DataFrame):
            logger.error(f"yfinance không trả về DataFrame: {type(df)}")
            return pd.DataFrame()
            
        # Kiểm tra xem DataFrame có dữ liệu không
        if df.empty:
            logger.warning(f"Không có dữ liệu cho {symbol}")
            return pd.DataFrame()
            
        # In ra thông tin về DataFrame để debug
        logger.info(f"Các cột trong DataFrame: {list(df.columns)}")
        logger.info(f"Các dòng đầu tiên: \n{df.head(2)}")
        
        # Kiểm tra xem các cột cần thiết có tồn tại không
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Thiếu các cột cần thiết: {missing_columns}")
            
        # Chuẩn hóa tên cột
        column_map = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        }
        
        # Đổi tên cột
        df = df.rename(columns=column_map)
        
        logger.info(f"Các cột sau khi đổi tên: {list(df.columns)}")
        logger.info(f"Đã tải {len(df)} dòng dữ liệu cho {symbol}")
        return df
    
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu: {str(e)}")
        return pd.DataFrame()

def test_rsi_divergence_detector(symbol, period='3mo', interval='1d', rsi_period=14, window_size=30):
    """
    Kiểm thử RSI Divergence Detector độc lập
    
    Args:
        symbol (str): Ký hiệu tiền tệ
        period (str): Khoảng thời gian
        interval (str): Khung thời gian
        rsi_period (int): Chu kỳ RSI
        window_size (int): Cửa sổ dữ liệu để tìm kiếm phân kỳ
    """
    # Tạo thư mục đầu ra
    os.makedirs('charts', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    
    # Tải dữ liệu
    df = load_data(symbol, period, interval)
    
    if df.empty:
        logger.error("Không thể tiếp tục do thiếu dữ liệu")
        return
    
    # Khởi tạo RSI Divergence Detector
    detector = RSIDivergenceDetector(rsi_period=rsi_period, window_size=window_size)
    
    # Phát hiện phân kỳ
    bullish_result = detector.detect_divergence(df, is_bullish=True)
    bearish_result = detector.detect_divergence(df, is_bullish=False)
    
    # Lấy tín hiệu giao dịch
    signal = detector.get_trading_signal(df)
    
    # In kết quả
    print("\n=== Kết Quả Phát Hiện RSI Divergence ===")
    print(f"Symbol: {symbol}")
    print(f"Khung thời gian: {interval}")
    print(f"Khoảng thời gian: {period}")
    
    print("\n-- Phân kỳ tăng (Bullish) --")
    print(f"Phát hiện: {bullish_result['detected']}")
    if bullish_result['detected']:
        print(f"Độ tin cậy: {bullish_result['confidence']:.2f}")
        print(f"Bắt đầu: {bullish_result['divergence_start'].strftime('%Y-%m-%d')}")
        print(f"Kết thúc: {bullish_result['divergence_end'].strftime('%Y-%m-%d')}")
        
        # Trực quan hóa
        chart_path = detector.visualize_divergence(df, bullish_result, symbol)
        print(f"Biểu đồ: {chart_path}")
    
    print("\n-- Phân kỳ giảm (Bearish) --")
    print(f"Phát hiện: {bearish_result['detected']}")
    if bearish_result['detected']:
        print(f"Độ tin cậy: {bearish_result['confidence']:.2f}")
        print(f"Bắt đầu: {bearish_result['divergence_start'].strftime('%Y-%m-%d')}")
        print(f"Kết thúc: {bearish_result['divergence_end'].strftime('%Y-%m-%d')}")
        
        # Trực quan hóa
        chart_path = detector.visualize_divergence(df, bearish_result, symbol)
        print(f"Biểu đồ: {chart_path}")
    
    print("\n-- Tín hiệu giao dịch --")
    print(f"Tín hiệu: {signal['signal']}")
    print(f"Độ tin cậy: {signal['confidence']:.2f}")
    
    # Lưu kết quả
    result = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': symbol,
        'interval': interval,
        'period': period,
        'rsi_period': rsi_period,
        'window_size': window_size,
        'bullish_detected': bullish_result['detected'],
        'bullish_confidence': bullish_result['confidence'],
        'bearish_detected': bearish_result['detected'],
        'bearish_confidence': bearish_result['confidence'],
        'trading_signal': signal['signal'],
        'signal_confidence': signal['confidence']
    }
    
    return result

def test_integrated_analysis(symbol, period='3mo', interval='1d', config_path='configs/sideways_config.json'):
    """
    Kiểm thử phân tích tích hợp với Sideways Market Optimizer
    
    Args:
        symbol (str): Ký hiệu tiền tệ
        period (str): Khoảng thời gian
        interval (str): Khung thời gian
        config_path (str): Đường dẫn đến file cấu hình
    """
    # Tải dữ liệu
    df = load_data(symbol, period, interval)
    
    if df.empty:
        logger.error("Không thể tiếp tục do thiếu dữ liệu")
        return
    
    # Khởi tạo Sideways Market Optimizer
    optimizer = SidewaysMarketOptimizer(config_path)
    
    # Phân tích thị trường đầy đủ
    analysis = optimizer.analyze_market_with_divergence(df, symbol)
    
    # In kết quả
    print("\n=== Kết Quả Phân Tích Tích Hợp ===")
    print(f"Symbol: {symbol}")
    print(f"Khung thời gian: {interval}")
    print(f"Khoảng thời gian: {period}")
    
    print(f"\nThị trường đi ngang: {analysis['is_sideways_market']} (Score: {analysis['sideways_score']:.2f})")
    
    if 'divergence' in analysis:
        print("\n-- Phát hiện Divergence (Tích hợp) --")
        print(f"Bullish: {analysis['divergence']['bullish']['detected']} (Conf: {analysis['divergence']['bullish']['confidence']:.2f})")
        print(f"Bearish: {analysis['divergence']['bearish']['detected']} (Conf: {analysis['divergence']['bearish']['confidence']:.2f})")
        print(f"Tín hiệu: {analysis['divergence']['signal']} (Conf: {analysis['divergence']['signal_confidence']:.2f})")
        
        # Biểu đồ
        if analysis['divergence'].get('chart_path'):
            print(f"Biểu đồ phân kỳ: {analysis['divergence']['chart_path']}")
    
    print("\n-- Chiến lược --")
    print(f"Kích thước vị thế: {analysis['position_sizing']['adjusted']:.2f}x (Giảm {analysis['position_sizing']['reduction_pct']:.1f}%)")
    print(f"Chiến lược: {'Mean Reversion' if analysis['strategy']['use_mean_reversion'] else 'Trend Following'}")
    print(f"Dự đoán breakout: {analysis['strategy']['breakout_prediction']}")
    print(f"Tỷ lệ TP/SL: {analysis['strategy']['tp_sl_ratio']:.1f}:1")
    
    if 'price_targets' in analysis:
        print("\n-- Mục tiêu giá --")
        print(f"Giá hiện tại: ${analysis['price_targets']['current_price']:.2f}")
        print(f"Hướng: {analysis['price_targets']['direction']}")
        print(f"Take Profit: ${analysis['price_targets']['tp_price']:.2f} ({analysis['price_targets']['tp_distance_pct']:.1f}%)")
        print(f"Stop Loss: ${analysis['price_targets']['sl_price']:.2f} ({analysis['price_targets']['sl_distance_pct']:.1f}%)")
    
    # Biểu đồ phát hiện thị trường đi ngang
    if 'chart_path' in analysis:
        print(f"\nBiểu đồ phát hiện thị trường đi ngang: {analysis['chart_path']}")
    
    # Tạo báo cáo chi tiết
    report = optimizer.generate_market_report(df, symbol)
    
    return report

def main():
    """
    Hàm main cho script
    """
    parser = argparse.ArgumentParser(description='Test RSI Divergence Detector')
    parser.add_argument('--symbol', type=str, default='BTC-USD', help='Symbol to analyze (e.g., BTC-USD)')
    parser.add_argument('--period', type=str, default='3mo', help='Period (e.g., 1mo, 3mo, 6mo)')
    parser.add_argument('--interval', type=str, default='1d', help='Interval (e.g., 1d, 4h, 1h)')
    parser.add_argument('--rsi_period', type=int, default=14, help='RSI period')
    parser.add_argument('--window_size', type=int, default=30, help='Window size for divergence detection')
    parser.add_argument('--test_integrated', action='store_true', help='Test integrated analysis with Sideways Market Optimizer')
    
    args = parser.parse_args()
    
    # Tạo thư mục logs nếu chưa có
    os.makedirs('logs', exist_ok=True)
    
    try:
        # Test RSI Divergence Detector độc lập
        logger.info("Bắt đầu kiểm thử RSI Divergence Detector")
        divergence_result = test_rsi_divergence_detector(
            args.symbol, args.period, args.interval, args.rsi_period, args.window_size
        )
        
        # Test phân tích tích hợp
        if args.test_integrated:
            logger.info("Bắt đầu kiểm thử phân tích tích hợp")
            integrated_result = test_integrated_analysis(
                args.symbol, args.period, args.interval
            )
            
            if integrated_result:
                logger.info(f"Đã tạo báo cáo tích hợp tại {integrated_result.get('report_path', 'unknown')}")
        
        logger.info("Kiểm thử hoàn tất")
        
    except Exception as e:
        logger.error(f"Lỗi trong quá trình kiểm thử: {str(e)}")
        print(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main()