#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Market Analysis System
--------------------
Module cung cấp hệ thống phân tích thị trường tiên tiến,
tạo tín hiệu giao dịch và đề xuất dựa trên nhiều chỉ báo kỹ thuật và phân tích xu hướng.
"""

import os
import json
import time
import logging
import math
from typing import Dict, List, Union, Optional, Any, Tuple
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from enhanced_binance_api import EnhancedBinanceAPI

# Thiết lập logging
logger = logging.getLogger("market_analysis_system")

class MarketAnalysisSystem:
    """
    Hệ thống phân tích thị trường tiên tiến
    Cung cấp các phương thức để phân tích thị trường, xác định xu hướng,
    tính toán các chỉ báo kỹ thuật và sinh tín hiệu giao dịch
    """
    
    def __init__(self, config_path: str = "configs/market_analysis_config.json"):
        """
        Khởi tạo hệ thống phân tích thị trường
        
        Args:
            config_path: Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Khởi tạo Binance API
        use_testnet = self.config.get('testnet', True)
        self.api = EnhancedBinanceAPI(testnet=use_testnet)
        
        # Kiểm tra kết nối
        if not self.api.test_connection():
            logger.warning("Không thể kết nối tới Binance API. Một số chức năng có thể không hoạt động.")
        
        # Cache dữ liệu
        self.cache = {}
        self.cache_expiry = {}
        self.cache_enabled = self.config.get('system_settings', {}).get('cache_data', True)
        self.cache_ttl = self.config.get('system_settings', {}).get('cache_expiry', 300)  # 5 phút
        
        logger.info("Đã khởi tạo Market Analysis System")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        default_config = {
            "testnet": True,
            "primary_timeframe": "1h",
            "timeframes": ["5m", "15m", "1h", "4h", "1d"],
            "symbols_to_analyze": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            "analysis_interval": 1800,  # 30 phút
            "indicators": {
                "sma": [20, 50, 100, 200],
                "ema": [9, 21, 55, 100],
                "rsi": 14,
                "macd": {"fast": 12, "slow": 26, "signal": 9},
                "bollinger": {"window": 20, "std": 2},
                "atr": 14,
                "stoch": {"k": 14, "d": 3, "smooth": 3},
                "volume_sma": 20
            },
            "market_regime": {
                "volatility_threshold": 2.5,
                "trend_strength_threshold": 3.0,
                "volume_surge_threshold": 2.0
            },
            "data_window": 200,
            "system_settings": {
                "debug_mode": True,
                "cache_data": True,
                "cache_expiry": 300,
                "log_level": "INFO",
                "save_analysis_files": True
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {e}")
                logger.info("Sử dụng cấu hình mặc định")
        else:
            logger.warning(f"Không tìm thấy file cấu hình {self.config_path}. Sử dụng cấu hình mặc định.")
        
        return default_config
    
    def get_historical_data(self, symbol: str, timeframe: str, limit: int = None) -> Optional[pd.DataFrame]:
        """
        Lấy dữ liệu lịch sử
        
        Args:
            symbol: Symbol cần lấy dữ liệu (ví dụ: BTCUSDT)
            timeframe: Khoảng thời gian (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            limit: Số lượng nến cần lấy (mặc định lấy từ cấu hình data_window)
            
        Returns:
            Optional[pd.DataFrame]: DataFrame chứa dữ liệu lịch sử hoặc None nếu không lấy được
        """
        try:
            # Kiểm tra cache
            cache_key = f"{symbol}_{timeframe}"
            if self.cache_enabled and cache_key in self.cache:
                cache_time = self.cache_expiry.get(cache_key, 0)
                if time.time() - cache_time < self.cache_ttl:
                    logger.debug(f"Sử dụng dữ liệu cache cho {symbol} {timeframe}")
                    return self.cache[cache_key].copy()
            
            # Nếu không có limit, lấy từ cấu hình
            if limit is None:
                limit = self.config.get('data_window', 200)
            
            # Lấy dữ liệu K-lines từ API
            klines = self.api.get_klines(symbol=symbol, interval=timeframe, limit=limit)
            
            if not klines or len(klines) == 0:
                logger.warning(f"Không lấy được dữ liệu K-lines cho {symbol} {timeframe}")
                return None
            
            # Chuyển đổi dữ liệu sang DataFrame
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume',
                               'quote_asset_volume', 'number_of_trades',
                               'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            # Chuyển đổi thời gian
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            # Đặt index
            df.set_index('open_time', inplace=True)
            
            # Lưu vào cache
            if self.cache_enabled:
                self.cache[cache_key] = df.copy()
                self.cache_expiry[cache_key] = time.time()
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu lịch sử cho {symbol} {timeframe}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán các chỉ báo kỹ thuật
        
        Args:
            df: DataFrame chứa dữ liệu lịch sử
            
        Returns:
            pd.DataFrame: DataFrame đã thêm các chỉ báo
        """
        try:
            # Tạo bản sao để không ảnh hưởng đến dữ liệu gốc
            df = df.copy()
            
            # Lấy cấu hình chỉ báo
            indicators_config = self.config.get('indicators', {})
            
            # Tính toán SMA
            sma_periods = indicators_config.get('sma', [20, 50, 100, 200])
            for period in sma_periods:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            
            # Tính toán EMA
            ema_periods = indicators_config.get('ema', [9, 21, 55, 100])
            for period in ema_periods:
                df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
            
            # Tính toán RSI
            rsi_period = indicators_config.get('rsi', 14)
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=rsi_period).mean()
            avg_loss = loss.rolling(window=rsi_period).mean()
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Tính toán MACD
            macd_config = indicators_config.get('macd', {"fast": 12, "slow": 26, "signal": 9})
            fast_period = macd_config.get('fast', 12)
            slow_period = macd_config.get('slow', 26)
            signal_period = macd_config.get('signal', 9)
            
            df['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
            df['macd'] = df['ema_fast'] - df['ema_slow']
            df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Tính toán Bollinger Bands
            bb_config = indicators_config.get('bollinger', {"window": 20, "std": 2})
            bb_window = bb_config.get('window', 20)
            bb_std = bb_config.get('std', 2)
            
            df['bb_middle'] = df['close'].rolling(window=bb_window).mean()
            df['bb_std'] = df['close'].rolling(window=bb_window).std()
            df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * bb_std)
            df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * bb_std)
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            
            # Tính toán ATR
            atr_period = indicators_config.get('atr', 14)
            df['tr1'] = abs(df['high'] - df['low'])
            df['tr2'] = abs(df['high'] - df['close'].shift())
            df['tr3'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            df['atr'] = df['tr'].rolling(window=atr_period).mean()
            
            # Tính toán Stochastic
            stoch_config = indicators_config.get('stoch', {"k": 14, "d": 3, "smooth": 3})
            stoch_k = stoch_config.get('k', 14)
            stoch_d = stoch_config.get('d', 3)
            stoch_smooth = stoch_config.get('smooth', 3)
            
            df['stoch_k_raw'] = 100 * (df['close'] - df['low'].rolling(window=stoch_k).min()) / (
                df['high'].rolling(window=stoch_k).max() - df['low'].rolling(window=stoch_k).min()
            )
            df['stoch_k'] = df['stoch_k_raw'].rolling(window=stoch_smooth).mean()
            df['stoch_d'] = df['stoch_k'].rolling(window=stoch_d).mean()
            
            # Tính toán Volume SMA
            volume_sma_period = indicators_config.get('volume_sma', 20)
            df['volume_sma'] = df['volume'].rolling(window=volume_sma_period).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Tính toán thêm - Chaikin Money Flow
            period = 20
            mf_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
            mf_volume = mf_multiplier * df['volume']
            df['cmf'] = mf_volume.rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
            
            # Tính toán Ichimoku
            tenkan_period = 9
            kijun_period = 26
            senkou_span_b_period = 52
            
            df['tenkan_sen'] = (df['high'].rolling(window=tenkan_period).max() + df['low'].rolling(window=tenkan_period).min()) / 2
            df['kijun_sen'] = (df['high'].rolling(window=kijun_period).max() + df['low'].rolling(window=kijun_period).min()) / 2
            df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(kijun_period)
            df['senkou_span_b'] = ((df['high'].rolling(window=senkou_span_b_period).max() + df['low'].rolling(window=senkou_span_b_period).min()) / 2).shift(kijun_period)
            df['chikou_span'] = df['close'].shift(-kijun_period)
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tính toán chỉ báo: {e}")
            return df
    
    def identify_patterns(self, df: pd.DataFrame) -> Dict:
        """
        Xác định các mẫu nến (candlestick patterns)
        
        Args:
            df: DataFrame chứa dữ liệu lịch sử
            
        Returns:
            Dict: Dictionary chứa các mẫu nến đã phát hiện
        """
        try:
            patterns = {}
            
            # Tạo bản sao để đảm bảo dữ liệu không bị thay đổi
            df = df.copy()
            
            # Lấy 10 nến gần nhất để phân tích
            recent_candles = df.iloc[-10:].copy()
            
            # --- MẪU NẾN ĐƠN ---
            
            # Mẫu Doji
            recent_candles['body_size'] = abs(recent_candles['close'] - recent_candles['open'])
            recent_candles['shadow_size'] = recent_candles['high'] - recent_candles['low']
            doji = recent_candles[recent_candles['body_size'] < 0.1 * recent_candles['shadow_size']]
            
            if not doji.empty:
                last_doji = doji.iloc[-1]
                patterns['doji'] = {
                    'detected': True,
                    'index': doji.index[-1],
                    'strength': 'weak' if len(doji) == 1 else 'medium' if len(doji) == 2 else 'strong'
                }
            
            # Mẫu Hammer
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            body_size = abs(latest['close'] - latest['open'])
            lower_shadow = min(latest['close'], latest['open']) - latest['low']
            upper_shadow = latest['high'] - max(latest['close'], latest['open'])
            
            if (lower_shadow > 2 * body_size) and (upper_shadow < 0.1 * body_size) and (latest['close'] > latest['open']):
                patterns['hammer'] = {
                    'detected': True,
                    'index': df.index[-1],
                    'strength': 'strong' if prev['close'] < prev['open'] else 'medium'
                }
            
            # Mẫu Shooting Star
            if (upper_shadow > 2 * body_size) and (lower_shadow < 0.1 * body_size) and (latest['close'] < latest['open']):
                patterns['shooting_star'] = {
                    'detected': True,
                    'index': df.index[-1],
                    'strength': 'strong' if prev['close'] > prev['open'] else 'medium'
                }
            
            # --- MẪU NẾN KẾT HỢP ---
            
            # Mẫu Engulfing
            if len(df) >= 2:
                current = df.iloc[-1]
                previous = df.iloc[-2]
                
                current_body_size = abs(current['close'] - current['open'])
                previous_body_size = abs(previous['close'] - previous['open'])
                
                # Bullish Engulfing
                if (current['close'] > current['open']) and (previous['close'] < previous['open']):
                    if (current['open'] < previous['close']) and (current['close'] > previous['open']):
                        if current_body_size > previous_body_size:
                            patterns['bullish_engulfing'] = {
                                'detected': True,
                                'index': df.index[-1],
                                'strength': 'strong' if current_body_size > 1.5 * previous_body_size else 'medium'
                            }
                
                # Bearish Engulfing
                if (current['close'] < current['open']) and (previous['close'] > previous['open']):
                    if (current['open'] > previous['close']) and (current['close'] < previous['open']):
                        if current_body_size > previous_body_size:
                            patterns['bearish_engulfing'] = {
                                'detected': True,
                                'index': df.index[-1],
                                'strength': 'strong' if current_body_size > 1.5 * previous_body_size else 'medium'
                            }
            
            # Mẫu Morning Star
            if len(df) >= 3:
                first = df.iloc[-3]
                middle = df.iloc[-2]
                last = df.iloc[-1]
                
                first_body_size = abs(first['close'] - first['open'])
                middle_body_size = abs(middle['close'] - middle['open'])
                last_body_size = abs(last['close'] - last['open'])
                
                if (first['close'] < first['open']) and (last['close'] > last['open']):
                    if middle_body_size < 0.5 * first_body_size:
                        if (last['close'] > (first['open'] + first['close']) / 2):
                            patterns['morning_star'] = {
                                'detected': True,
                                'index': df.index[-1],
                                'strength': 'strong'
                            }
            
            # Mẫu Evening Star
            if len(df) >= 3:
                first = df.iloc[-3]
                middle = df.iloc[-2]
                last = df.iloc[-1]
                
                first_body_size = abs(first['close'] - first['open'])
                middle_body_size = abs(middle['close'] - middle['open'])
                last_body_size = abs(last['close'] - last['open'])
                
                if (first['close'] > first['open']) and (last['close'] < last['open']):
                    if middle_body_size < 0.5 * first_body_size:
                        if (last['close'] < (first['open'] + first['close']) / 2):
                            patterns['evening_star'] = {
                                'detected': True,
                                'index': df.index[-1],
                                'strength': 'strong'
                            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Lỗi khi xác định mẫu nến: {e}")
            return {}
    
    def analyze_trend(self, df: pd.DataFrame) -> Dict:
        """
        Phân tích xu hướng
        
        Args:
            df: DataFrame chứa dữ liệu lịch sử với các chỉ báo
            
        Returns:
            Dict: Kết quả phân tích xu hướng
        """
        try:
            result = {
                'primary_trend': 'NEUTRAL',
                'secondary_trend': 'NEUTRAL',
                'trend_strength': 0,
                'support_levels': [],
                'resistance_levels': [],
                'key_level': 0
            }
            
            # Lấy các giá trị gần nhất
            latest = df.iloc[-1]
            
            # Phân tích xu hướng dựa trên MA
            sma_short = latest.get('sma_50', latest.get('sma_20', 0))
            sma_long = latest.get('sma_200', latest.get('sma_100', 0))
            ema_short = latest.get('ema_21', latest.get('ema_9', 0))
            ema_long = latest.get('ema_100', latest.get('ema_55', 0))
            current_price = latest['close']
            
            # Kiểm tra xu hướng theo giá và MA
            price_above_short_ma = current_price > sma_short and current_price > ema_short
            price_below_short_ma = current_price < sma_short and current_price < ema_short
            short_ma_above_long_ma = sma_short > sma_long and ema_short > ema_long
            short_ma_below_long_ma = sma_short < sma_long and ema_short < ema_long
            
            # Xác định xu hướng
            if price_above_short_ma and short_ma_above_long_ma:
                result['primary_trend'] = 'UPTREND'
            elif price_below_short_ma and short_ma_below_long_ma:
                result['primary_trend'] = 'DOWNTREND'
            
            # Xác định xu hướng thứ cấp dựa trên MACD
            macd = latest.get('macd', 0)
            macd_signal = latest.get('macd_signal', 0)
            macd_histogram = latest.get('macd_histogram', 0)
            
            if macd > macd_signal and macd_histogram > 0:
                result['secondary_trend'] = 'UPTREND'
            elif macd < macd_signal and macd_histogram < 0:
                result['secondary_trend'] = 'DOWNTREND'
            
            # Đánh giá độ mạnh của xu hướng
            trend_strength = 0
            
            # 1. Độ mạnh từ giá và MA
            if result['primary_trend'] == 'UPTREND':
                price_ma_ratio = current_price / sma_long - 1
                trend_strength += min(5, price_ma_ratio * 100)  # Tối đa 5 điểm
            elif result['primary_trend'] == 'DOWNTREND':
                price_ma_ratio = 1 - current_price / sma_long
                trend_strength += min(5, price_ma_ratio * 100)  # Tối đa 5 điểm
            
            # 2. Độ mạnh từ MACD
            if result['secondary_trend'] == result['primary_trend']:
                trend_strength += 2  # Thêm 2 điểm nếu xu hướng chính và phụ khớp nhau
                
                # Điểm thêm từ độ lớn của MACD histogram
                macd_strength = min(3, abs(macd_histogram) / current_price * 1000)
                trend_strength += macd_strength
            
            # 3. Độ mạnh từ RSI
            rsi = latest.get('rsi', 50)
            if result['primary_trend'] == 'UPTREND' and rsi > 50:
                trend_strength += min(2, (rsi - 50) / 10)  # Tối đa 2 điểm cho RSI trên 50
            elif result['primary_trend'] == 'DOWNTREND' and rsi < 50:
                trend_strength += min(2, (50 - rsi) / 10)  # Tối đa 2 điểm cho RSI dưới 50
            
            result['trend_strength'] = round(trend_strength, 1)
            
            # Xác định mức hỗ trợ và kháng cự
            # 1. Sử dụng Swing High/Low
            swing_high = df['high'].rolling(window=5, center=True).max()
            swing_low = df['low'].rolling(window=5, center=True).min()
            
            resistance_levels = []
            support_levels = []
            
            for i in range(5, len(df) - 5):
                # Xác định Swing High
                if df['high'].iloc[i] == swing_high.iloc[i] and df['high'].iloc[i] > df['high'].iloc[i+1] and df['high'].iloc[i] > df['high'].iloc[i-1]:
                    resistance_levels.append(df['high'].iloc[i])
                
                # Xác định Swing Low
                if df['low'].iloc[i] == swing_low.iloc[i] and df['low'].iloc[i] < df['low'].iloc[i+1] and df['low'].iloc[i] < df['low'].iloc[i-1]:
                    support_levels.append(df['low'].iloc[i])
            
            # 2. Thêm mức MA làm hỗ trợ/kháng cự
            if result['primary_trend'] == 'UPTREND':
                support_levels.extend([sma_short, ema_short])
            elif result['primary_trend'] == 'DOWNTREND':
                resistance_levels.extend([sma_short, ema_short])
            
            # 3. Thêm mức Fibonacci
            high = df['high'].max()
            low = df['low'].min()
            fib_range = high - low
            
            if result['primary_trend'] == 'UPTREND':
                resistance_levels.extend([
                    low + fib_range * 0.618,
                    low + fib_range * 0.786,
                    low + fib_range * 1.0,
                    low + fib_range * 1.272
                ])
                support_levels.extend([
                    low + fib_range * 0.236,
                    low + fib_range * 0.382,
                    low + fib_range * 0.5
                ])
            else:
                resistance_levels.extend([
                    low + fib_range * 0.5,
                    low + fib_range * 0.618,
                    low + fib_range * 0.786,
                    low + fib_range * 1.0
                ])
                support_levels.extend([
                    low,
                    low + fib_range * 0.236,
                    low + fib_range * 0.382
                ])
            
            # Lọc và phân loại mức hỗ trợ/kháng cự
            current_price = latest['close']
            
            # Lọc mức hỗ trợ dưới giá hiện tại
            filtered_supports = list(filter(lambda x: x < current_price, support_levels))
            filtered_supports.sort(reverse=True)  # Sắp xếp giảm dần
            
            # Lọc mức kháng cự trên giá hiện tại
            filtered_resistance = list(filter(lambda x: x > current_price, resistance_levels))
            filtered_resistance.sort()  # Sắp xếp tăng dần
            
            # Lấy 3 mức gần nhất
            result['support_levels'] = filtered_supports[:3]
            result['resistance_levels'] = filtered_resistance[:3]
            
            # Xác định mức giá quan trọng nhất (key level)
            if result['primary_trend'] == 'UPTREND' and filtered_resistance:
                result['key_level'] = filtered_resistance[0]  # Mức kháng cự gần nhất
            elif result['primary_trend'] == 'DOWNTREND' and filtered_supports:
                result['key_level'] = filtered_supports[0]  # Mức hỗ trợ gần nhất
            else:
                result['key_level'] = current_price  # Mức giá hiện tại
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích xu hướng: {e}")
            return {
                'primary_trend': 'NEUTRAL',
                'secondary_trend': 'NEUTRAL',
                'trend_strength': 0,
                'support_levels': [],
                'resistance_levels': [],
                'key_level': 0
            }
    
    def analyze_volatility(self, df: pd.DataFrame) -> Dict:
        """
        Phân tích biến động
        
        Args:
            df: DataFrame chứa dữ liệu lịch sử với các chỉ báo
            
        Returns:
            Dict: Kết quả phân tích biến động
        """
        try:
            result = {
                'current_volatility': 0,
                'volatility_state': 'NORMAL',
                'volatility_change': 'STABLE',
                'atr': 0,
                'atr_percent': 0,
                'bollinger_width': 0,
                'volatility_score': 0
            }
            
            # Lấy giá trị gần nhất
            latest = df.iloc[-1]
            recent = df.iloc[-10:]
            
            # ATR và ATR %
            atr = latest.get('atr', 0)
            close_price = latest['close']
            atr_percent = (atr / close_price * 100) if close_price > 0 else 0
            
            result['atr'] = atr
            result['atr_percent'] = atr_percent
            
            # Bollinger Width
            bb_width = latest.get('bb_width', 0)
            result['bollinger_width'] = bb_width
            
            # Tính toán điểm biến động
            volatility_score = 0
            
            # 1. Đánh giá từ ATR%
            if atr_percent < 1.0:
                volatility_score += 1  # Biến động thấp
            elif atr_percent < 2.0:
                volatility_score += 2  # Biến động trung bình
            elif atr_percent < 3.5:
                volatility_score += 3  # Biến động cao
            else:
                volatility_score += 4  # Biến động rất cao
            
            # 2. Đánh giá từ Bollinger Width
            avg_bb_width = recent['bb_width'].mean()
            if bb_width < 0.5 * avg_bb_width:
                volatility_score += 0  # Biến động rất thấp
            elif bb_width < 0.8 * avg_bb_width:
                volatility_score += 1  # Biến động thấp
            elif bb_width < 1.2 * avg_bb_width:
                volatility_score += 2  # Biến động trung bình
            elif bb_width < 1.5 * avg_bb_width:
                volatility_score += 3  # Biến động cao
            else:
                volatility_score += 4  # Biến động rất cao
            
            # 3. Đánh giá từ Price Range
            recent_range = (recent['high'].max() - recent['low'].min()) / close_price * 100
            if recent_range < 2.0:
                volatility_score += 1  # Biến động thấp
            elif recent_range < 4.0:
                volatility_score += 2  # Biến động trung bình
            elif recent_range < 7.0:
                volatility_score += 3  # Biến động cao
            else:
                volatility_score += 4  # Biến động rất cao
            
            result['volatility_score'] = round(volatility_score / 3, 1)  # Điểm trung bình
            
            # Xác định trạng thái biến động
            if result['volatility_score'] < 1.5:
                result['volatility_state'] = 'LOW'
            elif result['volatility_score'] < 2.5:
                result['volatility_state'] = 'NORMAL'
            elif result['volatility_score'] < 3.5:
                result['volatility_state'] = 'HIGH'
            else:
                result['volatility_state'] = 'EXTREME'
            
            # Xác định sự thay đổi biến động
            if len(df) > 20:
                prev_bb_width = df['bb_width'].iloc[-20:-10].mean()
                curr_bb_width = df['bb_width'].iloc[-10:].mean()
                
                if curr_bb_width < 0.8 * prev_bb_width:
                    result['volatility_change'] = 'DECREASING'
                elif curr_bb_width > 1.2 * prev_bb_width:
                    result['volatility_change'] = 'INCREASING'
                else:
                    result['volatility_change'] = 'STABLE'
            
            result['current_volatility'] = atr_percent
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích biến động: {e}")
            return {
                'current_volatility': 0,
                'volatility_state': 'NORMAL',
                'volatility_change': 'STABLE',
                'atr': 0,
                'atr_percent': 0,
                'bollinger_width': 0,
                'volatility_score': 0
            }
    
    def analyze_momentum(self, df: pd.DataFrame) -> Dict:
        """
        Phân tích xung lượng
        
        Args:
            df: DataFrame chứa dữ liệu lịch sử với các chỉ báo
            
        Returns:
            Dict: Kết quả phân tích xung lượng
        """
        try:
            result = {
                'primary_momentum': 'NEUTRAL',
                'momentum_strength': 0,
                'momentum_change': 'STABLE',
                'rsi': 0,
                'macd': 0,
                'stochastic': 0,
                'momentum_score': 0
            }
            
            # Lấy giá trị gần nhất
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # Lấy các chỉ số xung lượng
            rsi = latest.get('rsi', 50)
            macd = latest.get('macd', 0)
            macd_signal = latest.get('macd_signal', 0)
            macd_histogram = latest.get('macd_histogram', 0)
            stoch_k = latest.get('stoch_k', 50)
            stoch_d = latest.get('stoch_d', 50)
            
            result['rsi'] = rsi
            result['macd'] = macd
            result['stochastic'] = stoch_k
            
            # Tính toán điểm xung lượng
            momentum_score = 0
            
            # 1. Đánh giá từ RSI
            if rsi > 70:
                momentum_score += 2  # Xung lượng tăng mạnh
            elif rsi > 60:
                momentum_score += 1  # Xung lượng tăng trung bình
            elif rsi < 30:
                momentum_score -= 2  # Xung lượng giảm mạnh
            elif rsi < 40:
                momentum_score -= 1  # Xung lượng giảm trung bình
            
            # 2. Đánh giá từ MACD
            if macd > macd_signal:
                momentum_score += 1  # Xung lượng tăng
                if macd > 0:
                    momentum_score += 0.5  # Xung lượng tăng mạnh hơn khi MACD > 0
            else:
                momentum_score -= 1  # Xung lượng giảm
                if macd < 0:
                    momentum_score -= 0.5  # Xung lượng giảm mạnh hơn khi MACD < 0
            
            # 3. Đánh giá từ Stochastic
            if stoch_k > stoch_d:
                momentum_score += 0.5  # Xung lượng tăng nhẹ
                if stoch_k > 80:
                    momentum_score += 0.5  # Xung lượng tăng mạnh khi ở vùng quá mua
            else:
                momentum_score -= 0.5  # Xung lượng giảm nhẹ
                if stoch_k < 20:
                    momentum_score -= 0.5  # Xung lượng giảm mạnh khi ở vùng quá bán
            
            # 4. Đánh giá từ thay đổi MACD Histogram
            prev_histogram = prev.get('macd_histogram', 0)
            if macd_histogram > prev_histogram:
                momentum_score += 0.5  # Xung lượng tăng
            else:
                momentum_score -= 0.5  # Xung lượng giảm
            
            # 5. Đánh giá từ CMF
            cmf = latest.get('cmf', 0)
            if cmf > 0.05:
                momentum_score += 0.5  # Xung lượng tăng với dòng tiền vào
            elif cmf < -0.05:
                momentum_score -= 0.5  # Xung lượng giảm với dòng tiền ra
            
            result['momentum_score'] = round(momentum_score, 1)
            
            # Xác định xung lượng chính
            if momentum_score >= 2.0:
                result['primary_momentum'] = 'STRONG_BULLISH'
            elif momentum_score >= 1.0:
                result['primary_momentum'] = 'BULLISH'
            elif momentum_score <= -2.0:
                result['primary_momentum'] = 'STRONG_BEARISH'
            elif momentum_score <= -1.0:
                result['primary_momentum'] = 'BEARISH'
            else:
                result['primary_momentum'] = 'NEUTRAL'
            
            # Xác định độ mạnh xung lượng
            result['momentum_strength'] = abs(momentum_score)
            
            # Xác định sự thay đổi xung lượng
            if len(df) > 5:
                prev_rsi = df['rsi'].iloc[-5:-1].mean()
                prev_macd = df['macd'].iloc[-5:-1].mean()
                
                if rsi > prev_rsi and macd > prev_macd:
                    result['momentum_change'] = 'INCREASING'
                elif rsi < prev_rsi and macd < prev_macd:
                    result['momentum_change'] = 'DECREASING'
                else:
                    result['momentum_change'] = 'STABLE'
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích xung lượng: {e}")
            return {
                'primary_momentum': 'NEUTRAL',
                'momentum_strength': 0,
                'momentum_change': 'STABLE',
                'rsi': 0,
                'macd': 0,
                'stochastic': 0,
                'momentum_score': 0
            }
    
    def analyze_volume(self, df: pd.DataFrame) -> Dict:
        """
        Phân tích khối lượng
        
        Args:
            df: DataFrame chứa dữ liệu lịch sử với các chỉ báo
            
        Returns:
            Dict: Kết quả phân tích khối lượng
        """
        try:
            result = {
                'volume_state': 'NORMAL',
                'volume_trend': 'NEUTRAL',
                'money_flow': 'NEUTRAL',
                'volume_avg': 0,
                'volume_change': 0,
                'volume_score': 0
            }
            
            # Lấy giá trị gần nhất
            latest = df.iloc[-1]
            recent_volume = df['volume'].iloc[-10:].mean()
            
            # Tính toán khối lượng trung bình và thay đổi
            volume_sma = latest.get('volume_sma', recent_volume)
            current_volume = latest['volume']
            volume_ratio = current_volume / volume_sma if volume_sma > 0 else 1
            volume_change = (current_volume - volume_sma) / volume_sma * 100 if volume_sma > 0 else 0
            
            result['volume_avg'] = volume_sma
            result['volume_change'] = volume_change
            
            # Tính toán điểm khối lượng
            volume_score = 0
            
            # 1. Đánh giá từ tỉ lệ khối lượng
            if volume_ratio > 2.0:
                volume_score += 3  # Khối lượng rất cao
            elif volume_ratio > 1.5:
                volume_score += 2  # Khối lượng cao
            elif volume_ratio > 1.2:
                volume_score += 1  # Khối lượng trên trung bình
            elif volume_ratio < 0.5:
                volume_score -= 2  # Khối lượng rất thấp
            elif volume_ratio < 0.8:
                volume_score -= 1  # Khối lượng thấp
            
            # 2. Đánh giá từ Chaikin Money Flow
            cmf = latest.get('cmf', 0)
            if cmf > 0.1:
                volume_score += 2  # Dòng tiền vào mạnh
            elif cmf > 0.05:
                volume_score += 1  # Dòng tiền vào
            elif cmf < -0.1:
                volume_score -= 2  # Dòng tiền ra mạnh
            elif cmf < -0.05:
                volume_score -= 1  # Dòng tiền ra
            
            # 3. Đánh giá từ xu hướng khối lượng
            volume_trend = np.polyfit(range(min(10, len(df))), df['volume'].iloc[-min(10, len(df)):].values, 1)[0]
            if volume_trend > 0:
                volume_score += 1  # Khối lượng tăng
            else:
                volume_score -= 0.5  # Khối lượng giảm
            
            # 4. Đánh giá từ sự phù hợp giữa khối lượng và giá
            price_change = (latest['close'] - latest['open']) / latest['open'] * 100 if latest['open'] > 0 else 0
            
            if price_change > 0 and volume_ratio > 1.2:
                volume_score += 1  # Khối lượng tăng kèm giá tăng
            elif price_change < 0 and volume_ratio > 1.2:
                volume_score -= 1  # Khối lượng tăng kèm giá giảm
            
            result['volume_score'] = round(volume_score, 1)
            
            # Xác định trạng thái khối lượng
            if volume_ratio > 1.5:
                result['volume_state'] = 'HIGH'
            elif volume_ratio > 1.2:
                result['volume_state'] = 'ABOVE_AVERAGE'
            elif volume_ratio < 0.8:
                result['volume_state'] = 'BELOW_AVERAGE'
            elif volume_ratio < 0.5:
                result['volume_state'] = 'LOW'
            else:
                result['volume_state'] = 'NORMAL'
            
            # Xác định xu hướng khối lượng
            recent_volumes = df['volume'].iloc[-5:].values
            if len(recent_volumes) >= 5:
                slope = np.polyfit(range(5), recent_volumes, 1)[0]
                if slope > 0:
                    result['volume_trend'] = 'INCREASING'
                elif slope < 0:
                    result['volume_trend'] = 'DECREASING'
                else:
                    result['volume_trend'] = 'NEUTRAL'
            
            # Xác định dòng tiền
            if cmf > 0.05:
                result['money_flow'] = 'INFLOW'
            elif cmf < -0.05:
                result['money_flow'] = 'OUTFLOW'
            else:
                result['money_flow'] = 'NEUTRAL'
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích khối lượng: {e}")
            return {
                'volume_state': 'NORMAL',
                'volume_trend': 'NEUTRAL',
                'money_flow': 'NEUTRAL',
                'volume_avg': 0,
                'volume_change': 0,
                'volume_score': 0
            }
    
    def _generate_summary(self, analysis_results: Dict, timeframes: List[str]) -> Dict:
        """
        Tạo tóm tắt từ các kết quả phân tích
        
        Args:
            analysis_results: Dictionary chứa kết quả phân tích cho các khung thời gian
            timeframes: Danh sách các khung thời gian đã phân tích
            
        Returns:
            Dict: Tóm tắt phân tích
        """
        try:
            summary = {
                'overall_signal': 'NEUTRAL',
                'confidence': 0,
                'description': '',
                'time_horizons': {
                    'short_term': 'NEUTRAL',
                    'medium_term': 'NEUTRAL',
                    'long_term': 'NEUTRAL'
                },
                'price_prediction': {
                    'support': 0,
                    'resistance': 0,
                    'target': 0
                }
            }
            
            # Xác định khung thời gian ngắn, trung và dài hạn
            short_term_tf = ['1m', '5m', '15m']
            medium_term_tf = ['30m', '1h', '4h']
            long_term_tf = ['1d', '1w']
            
            signal_scores = []
            confidence_scores = []
            
            # Phân tích cho từng khung thời gian
            for timeframe in timeframes:
                if timeframe not in analysis_results:
                    continue
                
                tf_analysis = analysis_results[timeframe]
                
                # 1. Tính toán điểm tín hiệu cho khung thời gian này
                signal_score = 0
                
                # Xu hướng
                trend_analysis = tf_analysis.get('trend_analysis', {})
                trend = trend_analysis.get('primary_trend', 'NEUTRAL')
                trend_strength = trend_analysis.get('trend_strength', 0)
                
                if trend == 'UPTREND':
                    signal_score += trend_strength / 2
                elif trend == 'DOWNTREND':
                    signal_score -= trend_strength / 2
                
                # Xung lượng
                momentum_analysis = tf_analysis.get('momentum_analysis', {})
                momentum = momentum_analysis.get('primary_momentum', 'NEUTRAL')
                momentum_strength = momentum_analysis.get('momentum_strength', 0)
                
                if momentum == 'STRONG_BULLISH':
                    signal_score += momentum_strength
                elif momentum == 'BULLISH':
                    signal_score += momentum_strength / 2
                elif momentum == 'STRONG_BEARISH':
                    signal_score -= momentum_strength
                elif momentum == 'BEARISH':
                    signal_score -= momentum_strength / 2
                
                # Khối lượng
                volume_analysis = tf_analysis.get('volume_analysis', {})
                volume_score = volume_analysis.get('volume_score', 0)
                money_flow = volume_analysis.get('money_flow', 'NEUTRAL')
                
                if money_flow == 'INFLOW':
                    signal_score += min(1, volume_score / 2)
                elif money_flow == 'OUTFLOW':
                    signal_score -= min(1, volume_score / 2)
                
                # Mẫu nến
                pattern_analysis = tf_analysis.get('pattern_analysis', {})
                
                for pattern, details in pattern_analysis.items():
                    if not isinstance(details, dict) or not details.get('detected', False):
                        continue
                    
                    strength = details.get('strength', 'medium')
                    strength_value = 0.5 if strength == 'weak' else 1.0 if strength == 'medium' else 1.5
                    
                    if pattern in ['hammer', 'morning_star', 'bullish_engulfing']:
                        signal_score += strength_value
                    elif pattern in ['shooting_star', 'evening_star', 'bearish_engulfing']:
                        signal_score -= strength_value
                
                # 2. Tính toán độ tin cậy
                confidence = min(95, 50 + 10 * min(4.5, abs(signal_score)))
                
                # Thêm vào danh sách để tính trung bình
                signal_scores.append((timeframe, signal_score))
                confidence_scores.append(confidence)
                
                # 3. Phân loại vào các khung thời gian
                if timeframe in short_term_tf:
                    summary['time_horizons']['short_term'] = self._signal_from_score(signal_score)
                elif timeframe in medium_term_tf:
                    summary['time_horizons']['medium_term'] = self._signal_from_score(signal_score)
                elif timeframe in long_term_tf:
                    summary['time_horizons']['long_term'] = self._signal_from_score(signal_score)
            
            # Tính toán tín hiệu tổng thể dựa trên trọng số
            if signal_scores:
                # Tính trọng số cho từng khung thời gian
                weighted_scores = []
                for tf, score in signal_scores:
                    weight = 1.0
                    if tf in short_term_tf:
                        weight = 0.7
                    elif tf in medium_term_tf:
                        weight = 1.0
                    elif tf in long_term_tf:
                        weight = 1.3
                    
                    weighted_scores.append(score * weight)
                
                # Tín hiệu tổng thể
                overall_score = sum(weighted_scores) / sum(weight for _, weight in zip(signal_scores, weighted_scores))
                summary['overall_signal'] = self._signal_from_score(overall_score)
                
                # Độ tin cậy trung bình
                summary['confidence'] = int(sum(confidence_scores) / len(confidence_scores))
            
            # Dự đoán giá
            current_prices = []
            supports = []
            resistances = []
            
            for timeframe in timeframes:
                if timeframe not in analysis_results:
                    continue
                
                tf_analysis = analysis_results[timeframe]
                trend_analysis = tf_analysis.get('trend_analysis', {})
                
                current_price = tf_analysis.get('current_price', 0)
                support_levels = trend_analysis.get('support_levels', [])
                resistance_levels = trend_analysis.get('resistance_levels', [])
                
                if current_price > 0:
                    current_prices.append(current_price)
                
                if support_levels:
                    supports.extend(support_levels)
                
                if resistance_levels:
                    resistances.extend(resistance_levels)
            
            # Lấy giá hiện tại
            current_price = current_prices[0] if current_prices else 0
            
            # Lọc và tính trung bình cho các mức hỗ trợ/kháng cự
            if supports:
                # Lấy mức hỗ trợ gần nhất
                close_supports = [s for s in supports if s < current_price]
                if close_supports:
                    summary['price_prediction']['support'] = max(close_supports)
            
            if resistances:
                # Lấy mức kháng cự gần nhất
                close_resistances = [r for r in resistances if r > current_price]
                if close_resistances:
                    summary['price_prediction']['resistance'] = min(close_resistances)
            
            # Tính mức giá mục tiêu dựa trên tín hiệu
            if summary['overall_signal'] in ['STRONG_BUY', 'BUY'] and summary['price_prediction']['resistance'] > 0:
                summary['price_prediction']['target'] = summary['price_prediction']['resistance']
            elif summary['overall_signal'] in ['STRONG_SELL', 'SELL'] and summary['price_prediction']['support'] > 0:
                summary['price_prediction']['target'] = summary['price_prediction']['support']
            else:
                # Giá mục tiêu mặc định
                if current_price > 0:
                    if summary['overall_signal'] == 'STRONG_BUY':
                        summary['price_prediction']['target'] = current_price * 1.05
                    elif summary['overall_signal'] == 'BUY':
                        summary['price_prediction']['target'] = current_price * 1.03
                    elif summary['overall_signal'] == 'STRONG_SELL':
                        summary['price_prediction']['target'] = current_price * 0.95
                    elif summary['overall_signal'] == 'SELL':
                        summary['price_prediction']['target'] = current_price * 0.97
                    else:
                        summary['price_prediction']['target'] = current_price
            
            # Tạo mô tả
            description = self._generate_analysis_description(summary, analysis_results, timeframes)
            summary['description'] = description
            
            return summary
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tóm tắt phân tích: {e}")
            return {
                'overall_signal': 'NEUTRAL',
                'confidence': 0,
                'description': 'Không thể tạo tóm tắt do lỗi phân tích',
                'time_horizons': {
                    'short_term': 'NEUTRAL',
                    'medium_term': 'NEUTRAL',
                    'long_term': 'NEUTRAL'
                },
                'price_prediction': {
                    'support': 0,
                    'resistance': 0,
                    'target': 0
                }
            }
    
    def _signal_from_score(self, score: float) -> str:
        """
        Chuyển đổi điểm tín hiệu thành chuỗi tín hiệu
        
        Args:
            score: Điểm tín hiệu
            
        Returns:
            str: Chuỗi tín hiệu
        """
        if score >= 3.0:
            return 'STRONG_BUY'
        elif score >= 1.0:
            return 'BUY'
        elif score <= -3.0:
            return 'STRONG_SELL'
        elif score <= -1.0:
            return 'SELL'
        else:
            return 'NEUTRAL'
    
    def _generate_analysis_description(self, summary: Dict, analysis_results: Dict, timeframes: List[str]) -> str:
        """
        Tạo mô tả phân tích chi tiết
        
        Args:
            summary: Tóm tắt phân tích
            analysis_results: Kết quả phân tích chi tiết
            timeframes: Danh sách khung thời gian
            
        Returns:
            str: Mô tả phân tích
        """
        try:
            description = ""
            
            # Lấy tín hiệu tổng thể
            overall_signal = summary.get('overall_signal', 'NEUTRAL')
            confidence = summary.get('confidence', 0)
            
            # Lấy tín hiệu theo khung thời gian
            short_term = summary.get('time_horizons', {}).get('short_term', 'NEUTRAL')
            medium_term = summary.get('time_horizons', {}).get('medium_term', 'NEUTRAL')
            long_term = summary.get('time_horizons', {}).get('long_term', 'NEUTRAL')
            
            # Lấy dự đoán giá
            current_price = 0
            for timeframe in timeframes:
                if timeframe in analysis_results:
                    current_price = analysis_results[timeframe].get('current_price', 0)
                    if current_price > 0:
                        break
            
            support = summary.get('price_prediction', {}).get('support', 0)
            resistance = summary.get('price_prediction', {}).get('resistance', 0)
            target = summary.get('price_prediction', {}).get('target', 0)
            
            # Tạo mô tả tóm tắt
            if overall_signal == 'STRONG_BUY':
                description = f"Tín hiệu MUA MẠNH với độ tin cậy {confidence}%. "
                description += "Các chỉ báo kỹ thuật cho thấy xu hướng tăng rất mạnh. "
            elif overall_signal == 'BUY':
                description = f"Tín hiệu MUA với độ tin cậy {confidence}%. "
                description += "Các chỉ báo kỹ thuật cho thấy xu hướng tăng. "
            elif overall_signal == 'STRONG_SELL':
                description = f"Tín hiệu BÁN MẠNH với độ tin cậy {confidence}%. "
                description += "Các chỉ báo kỹ thuật cho thấy xu hướng giảm rất mạnh. "
            elif overall_signal == 'SELL':
                description = f"Tín hiệu BÁN với độ tin cậy {confidence}%. "
                description += "Các chỉ báo kỹ thuật cho thấy xu hướng giảm. "
            else:
                description = "Tín hiệu TRUNG LẬP. Các chỉ báo kỹ thuật không cho thấy xu hướng rõ ràng. "
            
            # Thêm thông tin về khung thời gian
            time_horizons = []
            if short_term != 'NEUTRAL':
                direction = "tăng" if short_term in ['BUY', 'STRONG_BUY'] else "giảm"
                time_horizons.append(f"ngắn hạn ({direction})")
            
            if medium_term != 'NEUTRAL':
                direction = "tăng" if medium_term in ['BUY', 'STRONG_BUY'] else "giảm"
                time_horizons.append(f"trung hạn ({direction})")
            
            if long_term != 'NEUTRAL':
                direction = "tăng" if long_term in ['BUY', 'STRONG_BUY'] else "giảm"
                time_horizons.append(f"dài hạn ({direction})")
            
            if time_horizons:
                description += "Xu hướng " + ", ".join(time_horizons) + ". "
            
            # Thêm thông tin về mức giá
            if current_price > 0:
                # Hỗ trợ và kháng cự
                if support > 0:
                    support_pct = (support - current_price) / current_price * 100
                    description += f"Mức hỗ trợ gần nhất ở {support:.2f} ({support_pct:.2f}%). "
                
                if resistance > 0:
                    resist_pct = (resistance - current_price) / current_price * 100
                    description += f"Mức kháng cự gần nhất ở {resistance:.2f} ({resist_pct:.2f}%). "
                
                # Giá mục tiêu
                if target > 0 and overall_signal != 'NEUTRAL':
                    target_pct = (target - current_price) / current_price * 100
                    direction = "tăng" if target > current_price else "giảm"
                    description += f"Giá mục tiêu {target:.2f} ({direction} {abs(target_pct):.2f}%). "
            
            # Thêm chi tiết từ phân tích
            main_tf = self.config.get('primary_timeframe', '1h')
            if main_tf in analysis_results:
                tf_analysis = analysis_results[main_tf]
                
                # Biến động
                volatility = tf_analysis.get('volatility_analysis', {}).get('volatility_state', 'NORMAL')
                if volatility != 'NORMAL':
                    if volatility == 'LOW':
                        description += "Biến động thị trường thấp. "
                    elif volatility == 'HIGH':
                        description += "Biến động thị trường cao. "
                    elif volatility == 'EXTREME':
                        description += "Biến động thị trường cực kỳ cao. "
                
                # Khối lượng
                volume = tf_analysis.get('volume_analysis', {})
                vol_state = volume.get('volume_state', 'NORMAL')
                money_flow = volume.get('money_flow', 'NEUTRAL')
                
                if vol_state in ['HIGH', 'ABOVE_AVERAGE'] and money_flow != 'NEUTRAL':
                    if money_flow == 'INFLOW':
                        description += "Khối lượng cao với dòng tiền vào. "
                    else:
                        description += "Khối lượng cao với dòng tiền ra. "
                
                # Mẫu nến
                patterns = tf_analysis.get('pattern_analysis', {})
                detected_patterns = []
                
                for pattern, details in patterns.items():
                    if not isinstance(details, dict) or not details.get('detected', False):
                        continue
                    
                    pattern_name = pattern.replace('_', ' ').title()
                    detected_patterns.append(pattern_name)
                
                if detected_patterns:
                    description += f"Phát hiện mẫu nến: {', '.join(detected_patterns)}. "
            
            return description
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo mô tả phân tích: {e}")
            return "Không thể tạo mô tả phân tích do lỗi."
    
    def analyze_symbol(self, symbol: str, timeframe: str = None) -> Dict:
        """
        Phân tích một cặp tiền cụ thể
        
        Args:
            symbol: Symbol cần phân tích (ví dụ: BTCUSDT)
            timeframe: Khung thời gian cần phân tích
            
        Returns:
            Dict: Kết quả phân tích
        """
        try:
            # Nếu không chỉ định khung thời gian, sử dụng khung thời gian chính từ cấu hình
            if not timeframe:
                timeframe = self.config.get('primary_timeframe', '1h')
            
            # Lấy danh sách các khung thời gian để phân tích đa khung thời gian
            all_timeframes = [timeframe]  # Bắt đầu với khung thời gian chỉ định
            
            # Thêm các khung thời gian khác từ cấu hình
            config_timeframes = self.config.get('timeframes', [])
            for tf in config_timeframes:
                if tf != timeframe and tf not in all_timeframes:
                    all_timeframes.append(tf)
            
            # Giới hạn số lượng khung thời gian để tránh quá tải
            all_timeframes = all_timeframes[:3]
            
            # Lấy giá hiện tại
            current_price = self.api.get_symbol_price(symbol)
            
            if not current_price:
                logger.warning(f"Không lấy được giá hiện tại của {symbol}")
                current_price = 0
            
            # Kết quả phân tích theo khung thời gian
            analysis_results = {}
            
            for tf in all_timeframes:
                # Lấy dữ liệu lịch sử
                df = self.get_historical_data(symbol, tf)
                
                if df is None or len(df) < 50:
                    logger.warning(f"Không đủ dữ liệu lịch sử cho {symbol} {tf}")
                    continue
                
                # Tính toán các chỉ báo
                df = self.calculate_indicators(df)
                
                # Phân tích các khía cạnh khác nhau
                trend_analysis = self.analyze_trend(df)
                volatility_analysis = self.analyze_volatility(df)
                momentum_analysis = self.analyze_momentum(df)
                volume_analysis = self.analyze_volume(df)
                pattern_analysis = self.identify_patterns(df)
                
                # Gộp vào kết quả
                analysis_results[tf] = {
                    'current_price': current_price,
                    'trend_analysis': trend_analysis,
                    'volatility_analysis': volatility_analysis,
                    'momentum_analysis': momentum_analysis,
                    'volume_analysis': volume_analysis,
                    'pattern_analysis': pattern_analysis
                }
            
            # Tạo tóm tắt
            summary = self._generate_summary(analysis_results, all_timeframes)
            
            # Tạo kết quả cuối cùng
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'timeframe': timeframe,
                'timestamp': datetime.now().isoformat(),
                'summary': summary,
                'detailed_analysis': analysis_results
            }
            
            # Lưu kết quả phân tích nếu được cấu hình
            if self.config.get('system_settings', {}).get('save_analysis_files', True):
                try:
                    filename = f"market_analysis_{symbol.lower()}.json"
                    with open(filename, 'w') as f:
                        json.dump(result, f, indent=4)
                    logger.info(f"Đã lưu kết quả phân tích vào {filename}")
                except Exception as e:
                    logger.error(f"Lỗi khi lưu kết quả phân tích: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích symbol {symbol}: {e}")
            return {
                'symbol': symbol,
                'current_price': 0,
                'timeframe': timeframe,
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'overall_signal': 'NEUTRAL',
                    'confidence': 0,
                    'description': f"Không thể phân tích do lỗi: {e}",
                    'time_horizons': {
                        'short_term': 'NEUTRAL',
                        'medium_term': 'NEUTRAL',
                        'long_term': 'NEUTRAL'
                    },
                    'price_prediction': {
                        'support': 0,
                        'resistance': 0,
                        'target': 0
                    }
                },
                'detailed_analysis': {}
            }
    
    def analyze_market(self) -> Dict:
        """
        Phân tích thị trường tổng thể
        
        Returns:
            Dict: Kết quả phân tích thị trường
        """
        try:
            # Lấy tổng quan thị trường
            market_overview = self.api.get_market_overview()
            
            if not market_overview:
                logger.warning("Không lấy được tổng quan thị trường")
                return {}
            
            # Lấy giá và biến động của BTC (chỉ số chính của thị trường)
            btc_data = None
            for coin in market_overview:
                if coin.get('symbol') == 'BTCUSDT':
                    btc_data = coin
                    break
            
            btc_price = btc_data.get('price', 0) if btc_data else 0
            btc_change = btc_data.get('price_change_24h', 0) if btc_data else 0
            
            # Sắp xếp các coin theo thay đổi giá
            top_gainers = sorted(market_overview, key=lambda x: x.get('price_change_24h', 0), reverse=True)[:10]
            top_losers = sorted(market_overview, key=lambda x: x.get('price_change_24h', 0))[:10]
            
            # Xác định trạng thái thị trường
            market_status = "SIDEWAYS"
            if btc_change > 2.0:
                market_status = "BULLISH"
            elif btc_change > 5.0:
                market_status = "STRONG_BULLISH"
            elif btc_change < -2.0:
                market_status = "BEARISH"
            elif btc_change < -5.0:
                market_status = "STRONG_BEARISH"
            
            # Phân tích sâu hơn cho BTC
            btc_analysis = self.analyze_symbol('BTCUSDT')
            
            # Xác định chế độ thị trường
            regime = {}
            if btc_analysis and 'summary' in btc_analysis:
                # Trend
                primary_trend = btc_analysis['summary'].get('time_horizons', {}).get('medium_term', 'NEUTRAL')
                if primary_trend == 'STRONG_BUY':
                    regime['primary'] = 'BULLISH'
                elif primary_trend == 'BUY':
                    regime['primary'] = 'SLIGHTLY_BULLISH'
                elif primary_trend == 'STRONG_SELL':
                    regime['primary'] = 'BEARISH'
                elif primary_trend == 'SELL':
                    regime['primary'] = 'SLIGHTLY_BEARISH'
                else:
                    regime['primary'] = 'RANGE_BOUND'
                
                # Volatility
                detailed_analysis = btc_analysis.get('detailed_analysis', {})
                if '1h' in detailed_analysis:
                    volatility_state = detailed_analysis['1h'].get('volatility_analysis', {}).get('volatility_state', 'NORMAL')
                    regime['volatility'] = volatility_state
                else:
                    regime['volatility'] = 'NORMAL'
                
                # Mô tả
                regime['description'] = btc_analysis['summary'].get('description', '')
            
            # Kết quả phân tích thị trường
            market_analysis = {
                'timestamp': datetime.now().isoformat(),
                'market_status': market_status,
                'btc_price': btc_price,
                'btc_price_change_24h': btc_change,
                'top_gainers': top_gainers,
                'top_losers': top_losers,
                'market_regime': regime,
                'btc_analysis': btc_analysis.get('summary', {}) if btc_analysis else {}
            }
            
            # Tính toán một số chỉ số thị trường
            total_market_cap = sum(coin.get('price', 0) * coin.get('volume_24h', 0) / coin.get('price', 1) for coin in market_overview)
            btc_dominance = 0
            if total_market_cap > 0 and btc_data:
                btc_market_cap = btc_data.get('price', 0) * btc_data.get('volume_24h', 0) / btc_data.get('price', 1)
                btc_dominance = btc_market_cap / total_market_cap * 100
            
            market_analysis['total_market_cap'] = total_market_cap
            market_analysis['btc_dominance'] = btc_dominance
            
            # Lưu kết quả phân tích nếu được cấu hình
            if self.config.get('system_settings', {}).get('save_analysis_files', True):
                try:
                    filename = "market_overview.json"
                    with open(filename, 'w') as f:
                        json.dump(market_analysis, f, indent=4)
                    logger.info(f"Đã lưu kết quả phân tích thị trường vào {filename}")
                except Exception as e:
                    logger.error(f"Lỗi khi lưu kết quả phân tích thị trường: {e}")
            
            return market_analysis
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường: {e}")
            return {}
    
    def scan_opportunities(self, symbols: List[str] = None) -> List[Dict]:
        """
        Quét cơ hội giao dịch trên nhiều cặp tiền
        
        Args:
            symbols: Danh sách các cặp tiền cần quét, nếu None sẽ sử dụng danh sách từ cấu hình
            
        Returns:
            List[Dict]: Danh sách các cơ hội giao dịch
        """
        try:
            # Nếu không chỉ định danh sách cặp tiền, sử dụng từ cấu hình
            if not symbols:
                symbols = self.config.get('symbols_to_analyze', ["BTCUSDT", "ETHUSDT", "BNBUSDT"])
            
            # Khung thời gian chính
            primary_tf = self.config.get('primary_timeframe', '1h')
            
            opportunities = []
            
            # Duyệt qua từng cặp tiền
            for symbol in symbols:
                logger.info(f"Đang quét cơ hội cho {symbol}...")
                
                # Phân tích cặp tiền
                analysis = self.analyze_symbol(symbol, primary_tf)
                
                if not analysis:
                    continue
                
                # Lấy tín hiệu tổng thể
                summary = analysis.get('summary', {})
                signal = summary.get('overall_signal', 'NEUTRAL')
                confidence = summary.get('confidence', 0)
                description = summary.get('description', '')
                current_price = analysis.get('current_price', 0)
                
                # Lấy dự đoán giá
                price_prediction = summary.get('price_prediction', {})
                target_price = price_prediction.get('target', 0)
                support = price_prediction.get('support', 0)
                resistance = price_prediction.get('resistance', 0)
                
                # Kiểm tra nếu có tín hiệu rõ ràng (không phải NEUTRAL)
                if signal != 'NEUTRAL' and confidence >= 70:
                    # Xác định hành động giao dịch
                    action = "BUY" if signal in ['STRONG_BUY', 'BUY'] else "SELL"
                    
                    # Xác định giá vào lệnh và stop loss
                    entry_price = current_price
                    stop_loss = 0
                    
                    if action == "BUY":
                        stop_loss = support if support > 0 else current_price * 0.97
                    else:  # SELL
                        stop_loss = resistance if resistance > 0 else current_price * 1.03
                    
                    # Tính toán tỷ lệ risk/reward
                    risk = abs(entry_price - stop_loss) / entry_price
                    reward = abs(target_price - entry_price) / entry_price if target_price > 0 else 0
                    risk_reward_ratio = reward / risk if risk > 0 else 0
                    
                    # Chỉ thêm cơ hội nếu tỷ lệ risk/reward tốt
                    if risk_reward_ratio >= 1.5:
                        opportunity = {
                            'symbol': symbol,
                            'action': action,
                            'signal': signal,
                            'confidence': confidence,
                            'current_price': current_price,
                            'target_price': target_price,
                            'stop_loss': stop_loss,
                            'risk_reward_ratio': risk_reward_ratio,
                            'risk': risk * 100,  # Phần trăm
                            'potential_reward': reward * 100,  # Phần trăm
                            'timeframe': primary_tf,
                            'description': description
                        }
                        
                        opportunities.append(opportunity)
                
            # Sắp xếp các cơ hội theo độ tin cậy giảm dần
            opportunities.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Lỗi khi quét cơ hội giao dịch: {e}")
            return []
    
    def generate_trading_recommendations(self, symbols: List[str] = None) -> Dict:
        """
        Tạo đề xuất giao dịch
        
        Args:
            symbols: Danh sách các cặp tiền cần quét, nếu None sẽ sử dụng danh sách từ cấu hình
            
        Returns:
            Dict: Đề xuất giao dịch
        """
        try:
            # Quét cơ hội
            opportunities = self.scan_opportunities(symbols)
            
            # Phân loại đề xuất
            buy_signals = [op for op in opportunities if op.get('action') == 'BUY']
            sell_signals = [op for op in opportunities if op.get('action') == 'SELL']
            watch_signals = []
            
            # Xác định các cặp tiền cần theo dõi (gần có tín hiệu)
            if symbols:
                primary_tf = self.config.get('primary_timeframe', '1h')
                
                for symbol in symbols:
                    # Bỏ qua các cặp đã có trong các tín hiệu mua/bán
                    if any(op.get('symbol') == symbol for op in opportunities):
                        continue
                    
                    # Phân tích cặp tiền
                    analysis = self.analyze_symbol(symbol, primary_tf)
                    
                    if not analysis:
                        continue
                    
                    # Lấy tín hiệu tổng thể
                    summary = analysis.get('summary', {})
                    signal = summary.get('overall_signal', 'NEUTRAL')
                    confidence = summary.get('confidence', 0)
                    
                    # Nếu có tín hiệu gần với ngưỡng đáng kể
                    if signal != 'NEUTRAL' and 60 <= confidence < 70:
                        watch_signals.append({
                            'symbol': symbol,
                            'action': 'WATCH',
                            'current_signal': signal,
                            'confidence': confidence,
                            'current_price': analysis.get('current_price', 0),
                            'description': summary.get('description', ''),
                            'timeframe': primary_tf
                        })
            
            # Xếp hạng các tín hiệu theo độ tin cậy
            buy_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            sell_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            watch_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Tạo đề xuất
            recommendations = {
                'timestamp': datetime.now().isoformat(),
                'top_opportunities': opportunities[:5],  # Top 5 cơ hội
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'watch_signals': watch_signals,
                'recommendations': buy_signals + sell_signals + watch_signals
            }
            
            # Lưu đề xuất nếu được cấu hình
            if self.config.get('system_settings', {}).get('save_analysis_files', True):
                try:
                    filename = "all_recommendations.json"
                    with open(filename, 'w') as f:
                        json.dump(recommendations, f, indent=4)
                    logger.info(f"Đã lưu đề xuất giao dịch vào {filename}")
                except Exception as e:
                    logger.error(f"Lỗi khi lưu đề xuất giao dịch: {e}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo đề xuất giao dịch: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'top_opportunities': [],
                'buy_signals': [],
                'sell_signals': [],
                'watch_signals': [],
                'recommendations': []
            }
    
    def generate_market_report(self) -> Dict:
        """
        Tạo báo cáo thị trường tổng hợp
        
        Returns:
            Dict: Báo cáo thị trường
        """
        try:
            # Phân tích thị trường
            market_analysis = self.analyze_market()
            
            # Lấy các cặp tiền chính
            primary_symbols = self.config.get('symbols_to_analyze', ["BTCUSDT", "ETHUSDT", "BNBUSDT"])[:5]  # Chỉ lấy 5 cặp hàng đầu
            
            # Phân tích mỗi cặp tiền
            symbol_analysis = {}
            for symbol in primary_symbols:
                analysis = self.analyze_symbol(symbol)
                if analysis:
                    symbol_analysis[symbol] = {
                        'current_price': analysis.get('current_price', 0),
                        'signal': analysis.get('summary', {}).get('overall_signal', 'NEUTRAL'),
                        'confidence': analysis.get('summary', {}).get('confidence', 0),
                        'momentum': analysis.get('detailed_analysis', {}).get('1h', {}).get('momentum_analysis', {}).get('primary_momentum', 'NEUTRAL')
                    }
            
            # Tạo báo cáo
            market_report = {
                'timestamp': datetime.now().isoformat(),
                'market_summary': {
                    'status': market_analysis.get('market_status', 'SIDEWAYS'),
                    'regime': market_analysis.get('market_regime', {}).get('primary', 'RANGE_BOUND'),
                    'volatility': market_analysis.get('market_regime', {}).get('volatility', 'NORMAL'),
                    'bitcoin_price': market_analysis.get('btc_price', 0),
                    'bitcoin_change': market_analysis.get('btc_price_change_24h', 0),
                    'bitcoin_signal': market_analysis.get('btc_analysis', {}).get('overall_signal', 'NEUTRAL')
                },
                'top_symbols': symbol_analysis,
                'market_outlook': market_analysis.get('market_regime', {}).get('description', '')
            }
            
            # Quét cơ hội giao dịch
            opportunities = self.scan_opportunities(primary_symbols)
            market_report['trading_opportunities'] = opportunities
            
            # Lưu báo cáo nếu được cấu hình
            if self.config.get('system_settings', {}).get('save_analysis_files', True):
                try:
                    filename = "market_report.json"
                    with open(filename, 'w') as f:
                        json.dump(market_report, f, indent=4)
                    logger.info(f"Đã lưu báo cáo thị trường vào {filename}")
                except Exception as e:
                    logger.error(f"Lỗi khi lưu báo cáo thị trường: {e}")
            
            return market_report
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo thị trường: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'market_summary': {},
                'top_symbols': {},
                'market_outlook': f"Không thể tạo báo cáo do lỗi: {e}",
                'trading_opportunities': []
            }

# Test nếu chạy trực tiếp
if __name__ == "__main__":
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Khởi tạo hệ thống phân tích
    analyzer = MarketAnalysisSystem()
    
    # Phân tích BTC
    btc_analysis = analyzer.analyze_symbol("BTCUSDT")
    print(f"Tín hiệu BTC: {btc_analysis.get('summary', {}).get('overall_signal', 'NEUTRAL')}")
    print(f"Độ tin cậy: {btc_analysis.get('summary', {}).get('confidence', 0)}%")
    print(f"Mô tả: {btc_analysis.get('summary', {}).get('description', '')}")
    
    # Phân tích thị trường
    market_analysis = analyzer.analyze_market()
    print(f"Trạng thái thị trường: {market_analysis.get('market_status', 'UNKNOWN')}")
    print(f"Giá BTC: ${market_analysis.get('btc_price', 0):,.2f}")
    print(f"Thay đổi BTC 24h: {market_analysis.get('btc_price_change_24h', 0):+.2f}%")
    
    # Quét cơ hội giao dịch
    opportunities = analyzer.scan_opportunities()
    print(f"Tìm thấy {len(opportunities)} cơ hội giao dịch")
    for i, opportunity in enumerate(opportunities[:3], 1):  # Chỉ hiển thị 3 cơ hội hàng đầu
        print(f"{i}. {opportunity.get('symbol')} - {opportunity.get('action')} (Độ tin cậy: {opportunity.get('confidence')}%)")
        print(f"   Giá hiện tại: ${opportunity.get('current_price', 0):,.2f}")
        print(f"   Giá mục tiêu: ${opportunity.get('target_price', 0):,.2f}")
        print(f"   Stop Loss: ${opportunity.get('stop_loss', 0):,.2f}")
        print(f"   Tỷ lệ R/R: {opportunity.get('risk_reward_ratio', 0):.2f}")