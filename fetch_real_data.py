#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tải dữ liệu thực tế từ Binance

Mô tả:
    Script này tải dữ liệu giá từ Binance API cho một hoặc nhiều cặp tiền và khung thời gian.
    Dữ liệu được lưu dưới dạng file CSV để sử dụng trong backtest hoặc phân tích.

Cách sử dụng:
    python fetch_real_data.py --symbol BTCUSDT --interval 1h --start_date 2023-01-01 --end_date 2023-12-31
    
    Tham số:
        --symbol: Mã cặp tiền (mặc định: BTCUSDT). Có thể dùng nhiều lần.
        --interval: Khung thời gian (mặc định: 1h). Có thể dùng nhiều lần.
        --start_date: Ngày bắt đầu lấy dữ liệu (mặc định: 6 tháng trước).
        --end_date: Ngày kết thúc lấy dữ liệu (mặc định: ngày hiện tại).
        --output_dir: Thư mục lưu dữ liệu (mặc định: test_data).
        --retry: Số lần thử lại nếu gặp lỗi (mặc định: 3).
        --no_progress: Không hiển thị thanh tiến trình.
"""

import os
import json
import time
import logging
import argparse
import pandas as pd
from datetime import datetime, timedelta
from binance.client import Client
from dotenv import load_dotenv
from tqdm import tqdm
import sys

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fetch_real_data.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('fetch_real_data')

# Tải biến môi trường
load_dotenv()
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Sử dụng API keys trong account config nếu có
try:
    with open('account_config.json', 'r') as f:
        account_config = json.load(f)
        if not API_KEY and account_config.get('api_key'):
            API_KEY = account_config.get('api_key')
        if not API_SECRET and account_config.get('api_secret'):
            API_SECRET = account_config.get('api_secret')
except (FileNotFoundError, json.JSONDecodeError):
    pass

def get_binance_client():
    """Tạo và trả về một client Binance"""
    try:
        client = Client(API_KEY, API_SECRET)
        # Kiểm tra kết nối
        server_time = client.get_server_time()
        logger.info(f"Đã kết nối đến Binance. Server time: {datetime.fromtimestamp(server_time['serverTime']/1000)}")
        return client
    except Exception as e:
        logger.error(f"Lỗi kết nối đến Binance: {str(e)}")
        return None

def get_historical_klines(client, symbol, interval, start_str, end_str=None):
    """Lấy dữ liệu lịch sử từ Binance"""
    try:
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_str,
            end_str=end_str
        )
        return klines
    except Exception as e:
        logger.error(f"Lỗi lấy dữ liệu lịch sử cho {symbol} {interval}: {str(e)}")
        return []

def klines_to_dataframe(klines):
    """Chuyển đổi dữ liệu klines sang DataFrame"""
    columns = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ]
    df = pd.DataFrame(klines, columns=columns)
    
    # Chuyển đổi kiểu dữ liệu
    numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                      'quote_asset_volume', 'number_of_trades',
                      'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
    
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col])
    
    # Chuyển đổi timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    return df

def save_to_csv(df, symbol, interval, output_dir='data'):
    """Lưu DataFrame vào file CSV"""
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = f"{output_dir}/{symbol}_{interval}.csv"
    df.to_csv(file_path, index=False)
    logger.info(f"Đã lưu {len(df)} dòng dữ liệu vào {file_path}")
    return file_path

def get_binance_client_with_retry(max_retries=3, delay=5):
    """Tạo client Binance với thử lại nếu thất bại"""
    for attempt in range(max_retries):
        client = get_binance_client()
        if client:
            return client
        
        logger.warning(f"Thử lại kết nối lần {attempt+1}/{max_retries} sau {delay} giây...")
        time.sleep(delay)
    
    logger.error(f"Đã thử kết nối {max_retries} lần nhưng thất bại")
    return None

def fetch_data_with_retry(client, symbol, interval, start_str, end_str=None, max_retries=3):
    """Lấy dữ liệu với cơ chế thử lại nếu thất bại"""
    for attempt in range(max_retries):
        try:
            klines = get_historical_klines(
                client=client,
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_str
            )
            
            if klines:
                return klines
            
            logger.warning(f"Thử lại lấy dữ liệu {symbol} {interval} lần {attempt+1}/{max_retries}...")
            time.sleep(2)  # Tránh rate limit
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu {symbol} {interval} lần {attempt+1}: {str(e)}")
            time.sleep(5)  # Nghỉ lâu hơn nếu có lỗi
    
    return []

def fetch_single_pair(client, symbol, interval, start_date, end_date, output_dir, retry_count=3, show_progress=True):
    """Lấy dữ liệu cho một cặp tiền và khung thời gian cụ thể"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Đang lấy dữ liệu {symbol} {interval} từ {start_date} đến {end_date}...")
    
    klines = fetch_data_with_retry(
        client=client,
        symbol=symbol,
        interval=interval,
        start_str=start_date,
        end_str=end_date,
        max_retries=retry_count
    )
    
    if not klines:
        logger.error(f"Không thể lấy dữ liệu cho {symbol} {interval}")
        return None, 0
    
    df = klines_to_dataframe(klines)
    file_path = save_to_csv(df, symbol, interval, output_dir)
    
    result = {
        "file_path": file_path,
        "candles": len(df),
        "start_date": df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
        "end_date": df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return result, len(df)

def parse_args():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Tải dữ liệu giá từ Binance')
    
    # Cách đây 6 tháng
    default_start = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    
    parser.add_argument('--symbol', action='append', default=None, 
                        help='Mã cặp tiền (mặc định: BTCUSDT)')
    parser.add_argument('--interval', action='append', default=None,
                        help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--start_date', type=str, default=default_start,
                        help=f'Ngày bắt đầu lấy dữ liệu (mặc định: {default_start})')
    parser.add_argument('--end_date', type=str, default=datetime.now().strftime('%Y-%m-%d'),
                        help='Ngày kết thúc lấy dữ liệu (mặc định: ngày hiện tại)')
    parser.add_argument('--output_dir', type=str, default='test_data',
                        help='Thư mục lưu dữ liệu (mặc định: test_data)')
    parser.add_argument('--retry', type=int, default=3,
                        help='Số lần thử lại nếu gặp lỗi (mặc định: 3)')
    parser.add_argument('--no_progress', action='store_true',
                        help='Không hiển thị thanh tiến trình')
    parser.add_argument('--all', action='store_true',
                        help='Tải dữ liệu cho tất cả các cặp tiền thông dụng')
    
    args = parser.parse_args()
    
    # Thiết lập giá trị mặc định
    if args.symbol is None or (len(args.symbol) == 0 and not args.all):
        args.symbol = ['BTCUSDT']
    
    if args.interval is None or len(args.interval) == 0:
        args.interval = ['1h']
    
    # Nếu có cờ --all, sử dụng danh sách mở rộng
    if args.all:
        args.symbol = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
            'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'LINKUSDT'
        ]
    
    return args

def main():
    """Hàm chính"""
    # Phân tích tham số dòng lệnh
    args = parse_args()
    
    symbols = args.symbol
    intervals = args.interval
    start_date = args.start_date
    end_date = args.end_date
    output_dir = args.output_dir
    retry_count = args.retry
    show_progress = not args.no_progress
    
    logger.info(f"Chuẩn bị tải dữ liệu cho {len(symbols)} cặp tiền và {len(intervals)} khung thời gian")
    logger.info(f"- Symbols: {', '.join(symbols)}")
    logger.info(f"- Intervals: {', '.join(intervals)}")
    logger.info(f"- Khoảng thời gian: {start_date} đến {end_date}")
    logger.info(f"- Thư mục lưu: {output_dir}")
    
    # Tạo thư mục đầu ra nếu chưa tồn tại
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Lấy client Binance
    client = get_binance_client_with_retry(max_retries=retry_count)
    if not client:
        logger.error("Không thể tạo client Binance. Thoát chương trình.")
        return
    
    # Chuẩn bị kết quả
    results = {
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "symbols": {},
        "params": {
            "start_date": start_date,
            "end_date": end_date,
            "symbols": symbols,
            "intervals": intervals
        },
        "total_files": 0,
        "total_candles": 0
    }
    
    # Tính toán tổng số cặp cần tải
    total_pairs = len(symbols) * len(intervals)
    
    if show_progress:
        progress_bar = tqdm(total=total_pairs, desc="Tải dữ liệu", unit="pair")
    
    # Lấy dữ liệu cho từng cặp tiền và khung thời gian
    for symbol in symbols:
        results["symbols"][symbol] = {}
        
        for interval in intervals:
            try:
                result, candles = fetch_single_pair(
                    client=client,
                    symbol=symbol,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir,
                    retry_count=retry_count,
                    show_progress=False  # Đã có thanh tiến độ tổng thể
                )
                
                if result:
                    results["symbols"][symbol][interval] = result
                    results["total_files"] += 1
                    results["total_candles"] += candles
                    
                    if show_progress:
                        progress_bar.set_postfix(symbol=symbol, interval=interval, candles=candles)
                else:
                    results["symbols"][symbol][interval] = {
                        "file_path": None,
                        "candles": 0,
                        "error": "Failed to retrieve data"
                    }
            except Exception as e:
                logger.error(f"Lỗi không xác định khi xử lý {symbol} {interval}: {str(e)}")
                results["symbols"][symbol][interval] = {
                    "file_path": None,
                    "candles": 0,
                    "error": str(e)
                }
            
            if show_progress:
                progress_bar.update(1)
            
            # Tránh rate limit
            time.sleep(0.5)
    
    if show_progress:
        progress_bar.close()
    
    # Lưu báo cáo kết quả
    report_path = f"{output_dir}/fetch_results.json"
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Hiển thị tóm tắt
    logger.info(f"Hoàn tất! Đã tải {results['total_files']}/{total_pairs} file với tổng cộng {results['total_candles']} nến.")
    logger.info(f"Báo cáo chi tiết được lưu tại {report_path}")
    
    # Kiểm tra nếu có lỗi
    failed_pairs = total_pairs - results['total_files']
    if failed_pairs > 0:
        logger.warning(f"Có {failed_pairs} cặp dữ liệu không thể tải thành công. Xem chi tiết trong báo cáo.")
    
    return results

if __name__ == "__main__":
    main()