#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module xử lý dữ liệu thị trường (Data Processor)

Module này cung cấp các công cụ để lấy, xử lý và chuẩn bị dữ liệu thị trường
từ các nguồn khác nhau (Binance API, dữ liệu lịch sử, v.v.).
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union

from binance_api import BinanceAPI

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataProcessor:
    """Lớp xử lý dữ liệu thị trường"""
    
    def __init__(self, binance_api: BinanceAPI = None, cache_dir: str = 'data/cache'):
        """
        Khởi tạo bộ xử lý dữ liệu
        
        Args:
            binance_api (BinanceAPI, optional): Đối tượng BinanceAPI để kết nối với Binance
            cache_dir (str): Thư mục lưu cache dữ liệu
        """
        self.cache_dir = cache_dir
        self.binance_api = binance_api if binance_api else BinanceAPI()
        self.data_cache = {}
        
        # Đảm bảo thư mục cache tồn tại
        os.makedirs(self.cache_dir, exist_ok=True)
        
        logger.info(f"Đã khởi tạo DataProcessor, sử dụng cache dir: {self.cache_dir}")
    
    def get_market_data(self, symbol: str, interval: str, limit: int = 100, 
                      use_cache: bool = True, cache_ttl: int = 300) -> pd.DataFrame:
        """
        Lấy dữ liệu thị trường cho một cặp tiền tệ và khung thời gian
        
        Args:
            symbol (str): Mã cặp giao dịch (ví dụ: 'BTCUSDT')
            interval (str): Khung thời gian (ví dụ: '1h', '4h', '1d')
            limit (int): Số lượng candlestick cần lấy
            use_cache (bool): Có sử dụng cache không
            cache_ttl (int): Thời gian cache hợp lệ (giây)
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu thị trường và các indicator
        """
        # Tạo cache key
        cache_key = f"{symbol}_{interval}_{limit}"
        
        # Kiểm tra cache
        if use_cache and cache_key in self.data_cache:
            cache_data = self.data_cache[cache_key]
            cache_time = cache_data.get('timestamp', 0)
            current_time = datetime.now().timestamp()
            
            # Nếu cache còn hợp lệ
            if current_time - cache_time < cache_ttl:
                logger.info(f"Lấy dữ liệu {symbol} {interval} từ cache")
                return cache_data.get('data', pd.DataFrame())
        
        try:
            # Lấy dữ liệu mới từ API
            klines = self.binance_api.get_klines(symbol, interval, limit=limit)
            
            if not klines or len(klines) == 0:
                logger.warning(f"Không thể lấy dữ liệu cho {symbol} {interval}")
                return pd.DataFrame()
            
            # Chuyển đổi thành DataFrame
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                              'close_time', 'quote_asset_volume', 'number_of_trades', 
                                              'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Loại bỏ các cột không cần thiết
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            # Thêm các indicator cơ bản
            df = self.add_basic_indicators(df)
            
            # Lưu vào cache
            self.data_cache[cache_key] = {
                'data': df,
                'timestamp': datetime.now().timestamp()
            }
            
            logger.info(f"Đã lấy và xử lý {len(df)} candlesticks cho {symbol} {interval}")
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu thị trường: {str(e)}")
            return pd.DataFrame()
    
    def add_basic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các chỉ báo kỹ thuật cơ bản vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã thêm
        """
        if len(df) == 0:
            return df
        
        # Tính RSI
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        
        # Tính MACD
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Tính Bollinger Bands
        period = 20
        df['sma'] = df['close'].rolling(window=period).mean()
        df['std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['sma'] + (df['std'] * 2)
        df['bb_lower'] = df['sma'] - (df['std'] * 2)
        
        # Tính EMA ngắn và dài
        df['ema_short'] = df['close'].ewm(span=10, adjust=False).mean()
        df['ema_long'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # Tính ATR
        df['tr1'] = abs(df['high'] - df['low'])
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # Tính ADX
        df = self._calculate_adx(df, 14)
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Tính RSI (Relative Strength Index)
        
        Args:
            prices (pd.Series): Chuỗi giá
            period (int): Chu kỳ RSI
            
        Returns:
            pd.Series: Chuỗi RSI
        """
        # Tính biến động giá
        deltas = prices.diff()
        
        # Tạo chuỗi gain và loss
        gain = deltas.copy()
        loss = deltas.copy()
        gain[gain < 0] = 0
        loss[loss > 0] = 0
        loss = -loss  # Chuyển đổi thành giá trị dương
        
        # Tính giá trị trung bình
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Tính RS và RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Tính ADX (Average Directional Index)
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            period (int): Chu kỳ ADX
            
        Returns:
            pd.DataFrame: DataFrame với ADX đã tính
        """
        # Tính +DM và -DM
        df['prev_high'] = df['high'].shift(1)
        df['prev_low'] = df['low'].shift(1)
        df['dm_plus'] = np.where((df['high'] - df['prev_high']) > (df['prev_low'] - df['low']),
                                np.maximum(df['high'] - df['prev_high'], 0),
                                0)
        df['dm_minus'] = np.where((df['prev_low'] - df['low']) > (df['high'] - df['prev_high']),
                                np.maximum(df['prev_low'] - df['low'], 0),
                                0)
        
        # Tính +DI và -DI
        df['di_plus'] = 100 * (df['dm_plus'].rolling(window=period).mean() / df['atr'])
        df['di_minus'] = 100 * (df['dm_minus'].rolling(window=period).mean() / df['atr'])
        
        # Tính DX
        df['dx'] = 100 * abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus'])
        
        # Tính ADX
        df['adx'] = df['dx'].rolling(window=period).mean()
        
        return df
    
    def get_historical_data(self, symbol: str, interval: str, lookback_days: int = 30) -> pd.DataFrame:
        """
        Lấy dữ liệu lịch sử cho một cặp tiền tệ trong khoảng thời gian xác định
        
        Args:
            symbol (str): Mã cặp giao dịch (ví dụ: 'BTCUSDT')
            interval (str): Khung thời gian (ví dụ: '1h', '4h', '1d')
            lookback_days (int): Số ngày lấy dữ liệu lịch sử
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu lịch sử
        """
        try:
            # Tính số lượng candlestick cần lấy
            intervals_per_day = {
                '1m': 24 * 60,
                '3m': 24 * 20,
                '5m': 24 * 12,
                '15m': 24 * 4,
                '30m': 24 * 2,
                '1h': 24,
                '2h': 12,
                '4h': 6,
                '6h': 4,
                '8h': 3,
                '12h': 2,
                '1d': 1,
                '3d': 1/3,
                '1w': 1/7,
                '1M': 1/30
            }
            
            if interval not in intervals_per_day:
                interval = '1h'  # Mặc định nếu interval không hợp lệ
            
            # Số candlestick cần lấy
            limit = min(1000, int(lookback_days * intervals_per_day.get(interval, 24)))
            
            # Lấy dữ liệu từ API
            df = self.get_market_data(symbol, interval, limit=limit, use_cache=True)
            
            if df is None or (hasattr(df, 'empty') and df.empty):
                logger.warning(f"Không có dữ liệu lịch sử cho {symbol} với khung thời gian {interval}")
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu lịch sử: {str(e)}")
            return pd.DataFrame()
            
    def download_historical_data(self, symbol: str, interval: str, start_time: datetime = None, 
                              end_time: datetime = None, save_to_file: bool = False) -> pd.DataFrame:
        """
        Tải xuống dữ liệu lịch sử đầy đủ cho một cặp tiền tệ
        
        Args:
            symbol (str): Mã cặp giao dịch (ví dụ: 'BTCUSDT')
            interval (str): Khung thời gian (ví dụ: '1h', '4h', '1d')
            start_time (datetime, optional): Thời gian bắt đầu, mặc định là 30 ngày trước
            end_time (datetime, optional): Thời gian kết thúc, mặc định là hiện tại
            save_to_file (bool): Có lưu dữ liệu vào file không
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu lịch sử
        """
        try:
            if start_time is None:
                start_time = datetime.now() - timedelta(days=30)
            if end_time is None:
                end_time = datetime.now()
            
            start_timestamp = int(start_time.timestamp() * 1000)
            end_timestamp = int(end_time.timestamp() * 1000)
            
            logger.info(f"Đang tải dữ liệu lịch sử cho {symbol} {interval} từ {start_time} đến {end_time}")
            
            # Khởi tạo DataFrame rỗng để chứa dữ liệu lịch sử
            all_klines = []
            
            # Binance giới hạn 1000 candlestick mỗi request, nên chúng ta cần lặp
            current_start = start_timestamp
            while current_start < end_timestamp:
                try:
                    # Lấy dữ liệu từ API
                    klines = self.binance_api.get_historical_klines(
                        symbol=symbol,
                        interval=interval,
                        start_str=current_start,
                        end_str=end_timestamp,
                        limit=1000
                    )
                    
                    if not klines or len(klines) == 0:
                        break
                    
                    all_klines.extend(klines)
                    
                    # Cập nhật thời gian bắt đầu cho lần lấy tiếp theo
                    current_start = int(klines[-1][0]) + 1
                    
                    logger.info(f"Đã tải {len(klines)} candlesticks. Tiến độ: {(current_start - start_timestamp) / (end_timestamp - start_timestamp) * 100:.2f}%")
                    
                    # Chờ một chút để tránh rate limit
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tải dữ liệu lịch sử cho {symbol} {interval}: {str(e)}")
                    # Chờ lâu hơn nếu có lỗi
                    time.sleep(2)
                    continue
            
            # Chuyển đổi thành DataFrame
            if not all_klines:
                logger.warning(f"Không có dữ liệu lịch sử cho {symbol} {interval}")
                return pd.DataFrame()
            
            df = pd.DataFrame(all_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                                  'close_time', 'quote_asset_volume', 'number_of_trades', 
                                                  'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Loại bỏ các cột không cần thiết
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            # Thêm các indicator cơ bản
            df = self.add_basic_indicators(df)
            
            logger.info(f"Đã tải và xử lý {len(df)} candlesticks cho {symbol} {interval}")
            
            # Lưu vào file nếu cần
            if save_to_file:
                os.makedirs(f"{self.cache_dir}/historical", exist_ok=True)
                file_path = f"{self.cache_dir}/historical/{symbol}_{interval}_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.csv"
                df.to_csv(file_path, index=False)
                logger.info(f"Đã lưu dữ liệu lịch sử vào file {file_path}")
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải xuống dữ liệu lịch sử: {str(e)}")
            return pd.DataFrame()
    
    def get_market_summary(self, symbol: str) -> Dict:
        """
        Lấy tóm tắt thị trường cho một cặp tiền tệ
        
        Args:
            symbol (str): Mã cặp giao dịch (ví dụ: 'BTCUSDT')
            
        Returns:
            Dict: Tóm tắt thị trường
        """
        try:
            # Lấy giá hiện tại
            ticker = self.binance_api.get_symbol_ticker(symbol)
            price = float(ticker['price']) if isinstance(ticker, dict) and 'price' in ticker else 0.0
            
            # Lấy thông tin biến động 24h
            ticker_24h = self.binance_api.get_24h_ticker(symbol)
            
            # Lấy dữ liệu 1h gần nhất
            df_1h = self.get_market_data(symbol, '1h', limit=24)
            
            # Lấy dữ liệu 4h gần nhất
            df_4h = self.get_market_data(symbol, '4h', limit=24)
            
            # Lấy dữ liệu 1d gần nhất
            df_1d = self.get_market_data(symbol, '1d', limit=30)
            
            # Tính toán các chỉ số biến động
            volatility_24h = float(ticker_24h.get('priceChangePercent', 0)) if isinstance(ticker_24h, dict) else 0.0
            
            # Tính toán volume trung bình
            volume_1h = df_1h['volume'].mean() if not df_1h.empty else 0
            volume_4h = df_4h['volume'].mean() if not df_4h.empty else 0
            volume_1d = df_1d['volume'].mean() if not df_1d.empty else 0
            
            # Tổng hợp các chỉ báo kỹ thuật
            indicators = {}
            
            # Lấy các chỉ báo từ khung 1h
            if not df_1h.empty and len(df_1h) > 0:
                latest = df_1h.iloc[-1]
                indicators['1h'] = {
                    'rsi': float(latest['rsi']) if 'rsi' in latest else 0,
                    'macd': float(latest['macd']) if 'macd' in latest else 0,
                    'macd_signal': float(latest['macd_signal']) if 'macd_signal' in latest else 0,
                    'bb_upper': float(latest['bb_upper']) if 'bb_upper' in latest else 0,
                    'bb_lower': float(latest['bb_lower']) if 'bb_lower' in latest else 0,
                    'ema_short': float(latest['ema_short']) if 'ema_short' in latest else 0,
                    'ema_long': float(latest['ema_long']) if 'ema_long' in latest else 0,
                    'adx': float(latest['adx']) if 'adx' in latest else 0
                }
            
            # Lấy các chỉ báo từ khung 4h
            if not df_4h.empty and len(df_4h) > 0:
                latest = df_4h.iloc[-1]
                indicators['4h'] = {
                    'rsi': float(latest['rsi']) if 'rsi' in latest else 0,
                    'macd': float(latest['macd']) if 'macd' in latest else 0,
                    'macd_signal': float(latest['macd_signal']) if 'macd_signal' in latest else 0,
                    'bb_upper': float(latest['bb_upper']) if 'bb_upper' in latest else 0,
                    'bb_lower': float(latest['bb_lower']) if 'bb_lower' in latest else 0,
                    'ema_short': float(latest['ema_short']) if 'ema_short' in latest else 0,
                    'ema_long': float(latest['ema_long']) if 'ema_long' in latest else 0,
                    'adx': float(latest['adx']) if 'adx' in latest else 0
                }
            
            # Lấy các chỉ báo từ khung 1d
            if not df_1d.empty and len(df_1d) > 0:
                latest = df_1d.iloc[-1]
                indicators['1d'] = {
                    'rsi': float(latest['rsi']) if 'rsi' in latest else 0,
                    'macd': float(latest['macd']) if 'macd' in latest else 0,
                    'macd_signal': float(latest['macd_signal']) if 'macd_signal' in latest else 0,
                    'bb_upper': float(latest['bb_upper']) if 'bb_upper' in latest else 0,
                    'bb_lower': float(latest['bb_lower']) if 'bb_lower' in latest else 0,
                    'ema_short': float(latest['ema_short']) if 'ema_short' in latest else 0,
                    'ema_long': float(latest['ema_long']) if 'ema_long' in latest else 0,
                    'adx': float(latest['adx']) if 'adx' in latest else 0
                }
            
            # Tạo tóm tắt thị trường
            market_summary = {
                'symbol': symbol,
                'price': price,
                'change_24h': volatility_24h,
                'volume': {
                    '1h': volume_1h,
                    '4h': volume_4h,
                    '1d': volume_1d
                },
                'indicators': indicators,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return market_summary
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy tóm tắt thị trường: {str(e)}")
            return {
                'symbol': symbol,
                'error': str(e),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

def main():
    """Hàm chính để test DataProcessor"""
    data_processor = DataProcessor()
    
    # Lấy dữ liệu BTC 1h
    df = data_processor.get_market_data('BTCUSDT', '1h', limit=24)
    
    # In thông tin
    print(f"Đã lấy {len(df)} candlesticks")
    print("\nThông tin DataFrame:")
    print(df.info())
    
    print("\nSample data:")
    print(df.head())
    
    # Lấy tóm tắt thị trường
    summary = data_processor.get_market_summary('BTCUSDT')
    
    print("\nMarket Summary:")
    print(f"Symbol: {summary['symbol']}")
    print(f"Price: {summary['price']}")
    print(f"24h Change: {summary['change_24h']}%")
    
    print("\nIndicators (1h):")
    if '1h' in summary['indicators']:
        indicators = summary['indicators']['1h']
        print(f"RSI: {indicators['rsi']:.2f}")
        print(f"MACD: {indicators['macd']:.4f}")
        print(f"ADX: {indicators['adx']:.2f}")

if __name__ == "__main__":
    main()