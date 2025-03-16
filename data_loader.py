#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tải dữ liệu lịch sử

Module này cung cấp các hàm để tải và xử lý dữ liệu lịch sử từ các nguồn khác nhau.
"""

import os
import json
import time
import logging
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime, timedelta
import requests
import ccxt

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('data_loader')

# Thư mục cache dữ liệu
DATA_CACHE_DIR = 'data/historical'

def load_historical_data(symbol: str, timeframe: str, start_date: str, end_date: str,
                         force_download: bool = False) -> Optional[pd.DataFrame]:
    """
    Tải dữ liệu lịch sử cho một cặp tiền và khung thời gian
    
    Args:
        symbol (str): Mã cặp tiền (VD: BTCUSDT)
        timeframe (str): Khung thời gian (VD: 1h, 4h, 1d)
        start_date (str): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str): Ngày kết thúc (YYYY-MM-DD)
        force_download (bool): Buộc tải lại dù có cache
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu lịch sử hoặc None nếu lỗi
    """
    # Kiểm tra cache
    if not force_download:
        cached_data = _load_from_cache(symbol, timeframe, start_date, end_date)
        if cached_data is not None:
            logger.info(f"Đã tải dữ liệu {symbol} {timeframe} từ cache")
            return cached_data
    
    # Tải từ API nếu không có cache hoặc force_download=True
    try:
        # Chuyển đổi start_date và end_date thành timestamp (ms)
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        
        df = None
        
        # Thử tải từ các nguồn khác nhau
        # 1. Thử tải từ file local trước
        df = _load_from_local_files(symbol, timeframe, start_date, end_date)
        
        # 2. Nếu không có file local, thử tải từ Binance
        if df is None or df.empty:
            df = _download_from_binance(symbol, timeframe, start_ts, end_ts)
            
        # 3. Nếu không tải được từ Binance, thử tải từ ccxt
        if df is None or df.empty:
            df = _download_from_ccxt(symbol, timeframe, start_ts, end_ts)
        
        # Nếu đã tải được dữ liệu, lưu vào cache
        if df is not None and not df.empty:
            _save_to_cache(df, symbol, timeframe, start_date, end_date)
            return df
        else:
            logger.warning(f"Không thể tải dữ liệu {symbol} {timeframe} từ bất kỳ nguồn nào")
            return None
            
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu {symbol} {timeframe}: {str(e)}")
        return None

def _load_from_cache(symbol: str, timeframe: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    Tải dữ liệu từ cache
    
    Args:
        symbol (str): Mã cặp tiền
        timeframe (str): Khung thời gian
        start_date (str): Ngày bắt đầu
        end_date (str): Ngày kết thúc
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu hoặc None nếu không có cache
    """
    cache_file = _get_cache_filename(symbol, timeframe, start_date, end_date)
    
    if os.path.exists(cache_file):
        try:
            df = pd.read_csv(cache_file)
            
            # Chuyển đổi cột thời gian thành index
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi đọc cache {cache_file}: {str(e)}")
    
    return None

def _save_to_cache(df: pd.DataFrame, symbol: str, timeframe: str, start_date: str, end_date: str) -> bool:
    """
    Lưu dữ liệu vào cache
    
    Args:
        df (pd.DataFrame): DataFrame cần lưu
        symbol (str): Mã cặp tiền
        timeframe (str): Khung thời gian
        start_date (str): Ngày bắt đầu
        end_date (str): Ngày kết thúc
        
    Returns:
        bool: True nếu lưu thành công, False nếu lỗi
    """
    # Tạo thư mục cache nếu chưa có
    os.makedirs(DATA_CACHE_DIR, exist_ok=True)
    
    cache_file = _get_cache_filename(symbol, timeframe, start_date, end_date)
    
    try:
        # Đảm bảo timestamp là cột bình thường (không phải index)
        df_to_save = df.copy()
        if df_to_save.index.name == 'timestamp':
            df_to_save.reset_index(inplace=True)
            
        # Lưu vào file CSV
        df_to_save.to_csv(cache_file, index=False)
        logger.info(f"Đã lưu dữ liệu vào cache: {cache_file}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu cache {cache_file}: {str(e)}")
        return False

def _get_cache_filename(symbol: str, timeframe: str, start_date: str, end_date: str) -> str:
    """
    Tạo tên file cache
    
    Args:
        symbol (str): Mã cặp tiền
        timeframe (str): Khung thời gian
        start_date (str): Ngày bắt đầu
        end_date (str): Ngày kết thúc
        
    Returns:
        str: Đường dẫn đến file cache
    """
    # Chuẩn hóa tên
    symbol = symbol.replace('/', '_')
    
    # Tạo tên file
    filename = f"{symbol}_{timeframe}_{start_date}_{end_date}.csv"
    
    return os.path.join(DATA_CACHE_DIR, filename)

def _load_from_local_files(symbol: str, timeframe: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    Tải dữ liệu từ các file local
    
    Args:
        symbol (str): Mã cặp tiền
        timeframe (str): Khung thời gian
        start_date (str): Ngày bắt đầu
        end_date (str): Ngày kết thúc
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu hoặc None nếu không có file
    """
    # Các thư mục có thể chứa dữ liệu
    data_dirs = [
        'backtest_data',
        'data',
        'real_data',
        f"data/{timeframe}",
        f"data/{symbol}"
    ]
    
    # Các tên file có thể có
    possible_filenames = [
        f"{symbol}_{timeframe}.csv",
        f"{symbol}.csv",
        f"{symbol}_{timeframe}_data.csv",
        f"{timeframe}/{symbol}.csv",
        f"{symbol}/{timeframe}.csv"
    ]
    
    # Tìm file
    for data_dir in data_dirs:
        if not os.path.exists(data_dir):
            continue
            
        for filename in possible_filenames:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath)
                    
                    # Chuyển đổi cột thời gian
                    time_columns = ['timestamp', 'time', 'date', 'datetime', 'open_time']
                    for col in time_columns:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col])
                            df.set_index(col, inplace=True)
                            break
                    
                    # Kiểm tra xem có đủ cột dữ liệu cần thiết không
                    required_columns = ['open', 'high', 'low', 'close']
                    if all(col in df.columns for col in required_columns):
                        # Lọc theo ngày
                        if df.index.name:
                            df = df[(df.index >= start_date) & (df.index <= end_date)]
                            
                            if not df.empty:
                                logger.info(f"Đã tải dữ liệu {symbol} {timeframe} từ file local: {filepath}")
                                return df
                except Exception as e:
                    logger.error(f"Lỗi khi đọc file {filepath}: {str(e)}")
    
    return None

def _download_from_binance(symbol: str, timeframe: str, start_ts: int, end_ts: int) -> Optional[pd.DataFrame]:
    """
    Tải dữ liệu từ Binance API
    
    Args:
        symbol (str): Mã cặp tiền
        timeframe (str): Khung thời gian
        start_ts (int): Timestamp bắt đầu (ms)
        end_ts (int): Timestamp kết thúc (ms)
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu hoặc None nếu lỗi
    """
    # Ánh xạ khung thời gian về định dạng của Binance
    timeframe_mapping = {
        '1m': '1m',
        '3m': '3m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '1h',
        '2h': '2h',
        '4h': '4h',
        '6h': '6h',
        '8h': '8h',
        '12h': '12h',
        '1d': '1d',
        '3d': '3d',
        '1w': '1w',
        '1M': '1M'
    }
    
    binance_tf = timeframe_mapping.get(timeframe, timeframe)
    
    try:
        # Binance API giới hạn 1000 nến mỗi lần gọi
        # Nên cần chia thành nhiều request nếu khoảng thời gian lớn
        
        # Tính khoảng thời gian của mỗi nến
        timeframe_ms = {
            '1m': 60 * 1000,
            '3m': 3 * 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '30m': 30 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '2h': 2 * 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '6h': 6 * 60 * 60 * 1000,
            '8h': 8 * 60 * 60 * 1000,
            '12h': 12 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
            '3d': 3 * 24 * 60 * 60 * 1000,
            '1w': 7 * 24 * 60 * 60 * 1000,
            '1M': 30 * 24 * 60 * 60 * 1000
        }
        
        # Số nến tối đa trong khoảng thời gian
        max_candles = 1000
        candle_interval = timeframe_ms.get(binance_tf, 60 * 60 * 1000)  # Mặc định 1h
        
        # Tính số request cần thiết
        time_span = end_ts - start_ts
        num_candles = time_span // candle_interval
        num_requests = (num_candles + max_candles - 1) // max_candles  # Làm tròn lên
        
        all_data = []
        
        # Nếu cần nhiều request
        if num_requests > 1:
            current_start = start_ts
            for i in range(num_requests):
                current_end = min(current_start + max_candles * candle_interval, end_ts)
                
                # Gọi API Binance
                url = f"https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': symbol,
                    'interval': binance_tf,
                    'startTime': current_start,
                    'endTime': current_end,
                    'limit': max_candles
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if isinstance(data, list):
                    all_data.extend(data)
                
                # Cập nhật start time cho lần tiếp theo
                current_start = current_end
                
                # Đợi để tránh rate limit
                time.sleep(0.5)
        else:
            # Chỉ cần 1 request
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': binance_tf,
                'startTime': start_ts,
                'endTime': end_ts,
                'limit': max_candles
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if isinstance(data, list):
                all_data = data
        
        # Kiểm tra dữ liệu trả về
        if not all_data:
            logger.warning(f"Không có dữ liệu từ Binance cho {symbol} {timeframe}")
            return None
        
        # Chuyển đổi dữ liệu thành DataFrame
        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                         'close_time', 'quote_volume', 'count', 
                                         'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'])
        
        # Chuyển đổi kiểu dữ liệu
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_volume', 
                          'taker_buy_volume', 'taker_buy_quote_volume']
        
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col])
        
        # Chuyển đổi timestamp thành datetime và làm index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"Đã tải {len(df)} nến dữ liệu {symbol} {timeframe} từ Binance")
        return df
    
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu từ Binance {symbol} {timeframe}: {str(e)}")
        return None

def _download_from_ccxt(symbol: str, timeframe: str, start_ts: int, end_ts: int) -> Optional[pd.DataFrame]:
    """
    Tải dữ liệu từ ccxt
    
    Args:
        symbol (str): Mã cặp tiền
        timeframe (str): Khung thời gian
        start_ts (int): Timestamp bắt đầu (ms)
        end_ts (int): Timestamp kết thúc (ms)
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu hoặc None nếu lỗi
    """
    try:
        # Tạo exchange object
        exchange = ccxt.binance({
            'enableRateLimit': True,  # Bật rate limit để tránh bị khóa
        })
        
        # Chuyển đổi timeframe
        ccxt_timeframe = timeframe.replace('m', 'm').replace('h', 'h').replace('d', 'd').replace('w', 'w').replace('M', 'M')
        
        # Chia thành nhiều request để tránh vượt quá giới hạn
        all_candles = []
        
        # ccxt lấy timestamp ở đơn vị ms
        current_start = start_ts
        
        while current_start < end_ts:
            # Lấy OHLCV
            candles = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=ccxt_timeframe,
                since=current_start,
                limit=1000  # Số nến tối đa
            )
            
            if not candles:
                break
                
            all_candles.extend(candles)
            
            # Cập nhật thời gian bắt đầu là thời gian của nến cuối cùng + 1ms
            current_start = candles[-1][0] + 1
            
            # Đợi để tránh rate limit
            time.sleep(0.5)
        
        # Nếu không có dữ liệu
        if not all_candles:
            logger.warning(f"Không có dữ liệu từ ccxt cho {symbol} {timeframe}")
            return None
        
        # Chuyển đổi thành DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Chuyển đổi timestamp thành datetime và làm index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Lọc theo thời gian
        df = df[(df.index >= pd.to_datetime(start_ts, unit='ms')) & 
               (df.index <= pd.to_datetime(end_ts, unit='ms'))]
        
        logger.info(f"Đã tải {len(df)} nến dữ liệu {symbol} {timeframe} từ ccxt")
        return df
    
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu từ ccxt {symbol} {timeframe}: {str(e)}")
        return None

def download_multiple_symbols(symbols: List[str], timeframes: List[str], 
                              start_date: str, end_date: str, force_download: bool = False) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Tải dữ liệu cho nhiều cặp tiền và khung thời gian
    
    Args:
        symbols (List[str]): Danh sách mã cặp tiền
        timeframes (List[str]): Danh sách khung thời gian
        start_date (str): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str): Ngày kết thúc (YYYY-MM-DD)
        force_download (bool): Buộc tải lại dù có cache
        
    Returns:
        Dict[str, Dict[str, pd.DataFrame]]: Dictionary với dữ liệu dạng {symbol: {timeframe: DataFrame}}
    """
    result = {}
    
    for symbol in symbols:
        result[symbol] = {}
        
        for timeframe in timeframes:
            df = load_historical_data(symbol, timeframe, start_date, end_date, force_download)
            
            if df is not None and not df.empty:
                result[symbol][timeframe] = df
            else:
                logger.warning(f"Không thể tải dữ liệu cho {symbol} {timeframe}")
    
    return result

# Hàm tiện ích để tính các chỉ báo phổ biến
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thêm các chỉ báo kỹ thuật vào DataFrame
    
    Args:
        df (pd.DataFrame): DataFrame gốc với dữ liệu OHLCV
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo đã được thêm vào
    """
    result_df = df.copy()
    
    # Kiểm tra các cột cần thiết
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in result_df.columns for col in required_columns):
        logger.error("DataFrame không có đủ các cột cần thiết (OHLCV)")
        return df
    
    # --- Các chỉ báo xu hướng ---
    
    # 1. SMA (Simple Moving Average)
    result_df['sma_20'] = result_df['close'].rolling(window=20).mean()
    result_df['sma_50'] = result_df['close'].rolling(window=50).mean()
    result_df['sma_200'] = result_df['close'].rolling(window=200).mean()
    
    # 2. EMA (Exponential Moving Average)
    result_df['ema_20'] = result_df['close'].ewm(span=20, adjust=False).mean()
    result_df['ema_50'] = result_df['close'].ewm(span=50, adjust=False).mean()
    result_df['ema_200'] = result_df['close'].ewm(span=200, adjust=False).mean()
    
    # --- Các chỉ báo dao động ---
    
    # 3. RSI (Relative Strength Index)
    delta = result_df['close'].diff()
    gain = delta.copy()
    loss = delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    loss = abs(loss)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    result_df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # --- Các chỉ báo biến động ---
    
    # 4. ATR (Average True Range)
    tr1 = result_df['high'] - result_df['low']
    tr2 = abs(result_df['high'] - result_df['close'].shift())
    tr3 = abs(result_df['low'] - result_df['close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    result_df['atr_14'] = tr.rolling(window=14).mean()
    
    # 5. Bollinger Bands
    result_df['bb_middle'] = result_df['close'].rolling(window=20).mean()
    result_df['bb_std'] = result_df['close'].rolling(window=20).std()
    result_df['bb_upper'] = result_df['bb_middle'] + 2 * result_df['bb_std']
    result_df['bb_lower'] = result_df['bb_middle'] - 2 * result_df['bb_std']
    
    # 6. MACD
    result_df['macd_line'] = result_df['close'].ewm(span=12, adjust=False).mean() - \
                          result_df['close'].ewm(span=26, adjust=False).mean()
    result_df['macd_signal'] = result_df['macd_line'].ewm(span=9, adjust=False).mean()
    result_df['macd_histogram'] = result_df['macd_line'] - result_df['macd_signal']
    
    return result_df