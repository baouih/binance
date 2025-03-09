#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module Đánh Giá Chất Lượng Tín Hiệu Nâng Cao (Enhanced Signal Quality)

Module này cung cấp công cụ đánh giá chất lượng tín hiệu giao dịch, sử dụng
nhiều chỉ báo kỹ thuật, phân tích đa khung thời gian, và tương quan với BTC
để đưa ra điểm số và mức độ tin cậy của tín hiệu.
"""

import logging
import json
import time
import datetime
import os
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('signal_quality')


class EnhancedSignalQuality:
    """Lớp đánh giá chất lượng tín hiệu giao dịch nâng cao"""
    
    def __init__(self, binance_api = None, config_path: str = 'configs/signal_quality_config.json'):
        """
        Khởi tạo Enhanced Signal Quality
        
        Args:
            binance_api: Đối tượng BinanceAPI để lấy dữ liệu
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config = self._load_config(config_path)
        self.binance_api = binance_api
        self.cached_data = {}
        self.evaluation_history = {}
        
        # Đảm bảo thư mục data tồn tại
        os.makedirs('data', exist_ok=True)
        
        # Tải lịch sử đánh giá nếu có
        self._load_evaluation_history()
        logger.info("Đã khởi tạo Enhanced Signal Quality")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file hoặc sử dụng cấu hình mặc định
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        default_config = {
            'indicator_weights': {
                'trend_strength': 0.25,     # Độ mạnh xu hướng
                'momentum': 0.20,           # Động lượng (RSI, MACD)
                'volume_confirmation': 0.15, # Xác nhận khối lượng
                'price_patterns': 0.15,      # Mẫu hình giá
                'support_resistance': 0.10,  # Hỗ trợ/kháng cự
                'btc_alignment': 0.15       # Tương đồng với xu hướng BTC
            },
            'multi_timeframe_weights': {
                '1m': 0.05,
                '5m': 0.10,
                '15m': 0.15,
                '1h': 0.25,
                '4h': 0.25,
                '1d': 0.20
            },
            'signal_quality_thresholds': {
                'excellent': 80,
                'good': 65,
                'moderate': 50,
                'weak': 35
            },
            'rsi_parameters': {
                'period': 14,
                'overbought': 70,
                'oversold': 30
            },
            'macd_parameters': {
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9
            },
            'adx_parameters': {
                'period': 14,
                'strong_trend': 25
            },
            'bollinger_parameters': {
                'period': 20,
                'std_dev': 2.0
            },
            'volume_parameters': {
                'period': 20,
                'significant_increase': 1.5
            },
            'price_pattern_scores': {
                'double_bottom': 85,
                'double_top': 85,
                'head_shoulders': 80,
                'inv_head_shoulders': 80,
                'ascending_triangle': 75,
                'descending_triangle': 75,
                'bull_flag': 70,
                'bear_flag': 70,
                'cup_handle': 70,
                'channel_breakout': 65
            },
            'btc_correlation_thresholds': {
                'high': 0.7,    # Tương quan cao
                'medium': 0.4,  # Tương quan trung bình
                'low': 0.2      # Tương quan thấp
            },
            'cache_timeout': 300  # Thời gian cache dữ liệu (giây)
        }
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {config_path}")
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Không thể tải cấu hình từ {config_path}, sử dụng cấu hình mặc định")
            return default_config
    
    def evaluate_signal_quality(self, symbol: str, timeframe: str = '1h') -> Tuple[float, Dict]:
        """
        Đánh giá chất lượng tín hiệu giao dịch
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            Tuple[float, Dict]: (Điểm chất lượng tổng hợp, Chi tiết đánh giá)
        """
        if not self.binance_api:
            logger.error("Không có BinanceAPI, không thể đánh giá tín hiệu")
            return 0, {"error": "No BinanceAPI instance provided"}
        
        # Lấy dữ liệu
        data = self._get_data_for_evaluation(symbol, timeframe)
        if not data:
            logger.error(f"Không thể lấy dữ liệu cho {symbol} {timeframe}")
            return 0, {"error": "Failed to get data"}
        
        # Đánh giá các thành phần
        trend_strength_score = self._evaluate_trend_strength(data, symbol, timeframe)
        momentum_score = self._evaluate_momentum(data, symbol, timeframe)
        volume_score = self._evaluate_volume_confirmation(data, symbol, timeframe)
        pattern_score = self._evaluate_price_patterns(data, symbol, timeframe)
        sr_score = self._evaluate_support_resistance(data, symbol, timeframe)
        btc_alignment_score = self._evaluate_btc_alignment(data, symbol, timeframe)
        
        # Tính tổng hợp với trọng số
        weights = self.config.get('indicator_weights', {})
        total_score = (
            weights.get('trend_strength', 0.25) * trend_strength_score +
            weights.get('momentum', 0.20) * momentum_score +
            weights.get('volume_confirmation', 0.15) * volume_score +
            weights.get('price_patterns', 0.15) * pattern_score +
            weights.get('support_resistance', 0.10) * sr_score +
            weights.get('btc_alignment', 0.15) * btc_alignment_score
        )
        
        # Đánh giá đa khung thời gian nếu được yêu cầu
        multi_tf_score = self._evaluate_multi_timeframe(symbol, timeframe)
        if multi_tf_score > 0:
            # Kết hợp với tỷ lệ 70% điểm hiện tại, 30% đánh giá đa khung thời gian
            total_score = 0.7 * total_score + 0.3 * multi_tf_score
        
        # Xác định hướng tín hiệu
        signal_direction = self._determine_signal_direction(data, symbol, timeframe)
        
        # Xác định cường độ tín hiệu
        signal_strength = self._determine_signal_strength(total_score)
        
        # Lưu kết quả đánh giá
        evaluation_result = {
            'score': total_score,
            'signal_direction': signal_direction,
            'signal_strength': signal_strength,
            'component_scores': {
                'trend_strength': trend_strength_score,
                'momentum': momentum_score,
                'volume_confirmation': volume_score,
                'price_patterns': pattern_score,
                'support_resistance': sr_score,
                'btc_alignment': btc_alignment_score,
                'multi_timeframe': multi_tf_score
            },
            'timestamp': int(time.time()),
            'symbol': symbol,
            'timeframe': timeframe,
            'btc_correlation': self._calculate_btc_correlation(data, timeframe)
        }
        
        # Lưu lịch sử đánh giá
        self._save_evaluation(symbol, timeframe, evaluation_result)
        
        return total_score, evaluation_result
    
    def _get_data_for_evaluation(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Lấy dữ liệu cần thiết cho đánh giá
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            Optional[pd.DataFrame]: DataFrame chứa dữ liệu, hoặc None nếu không lấy được
        """
        cache_key = f"{symbol}_{timeframe}"
        cache_timeout = self.config.get('cache_timeout', 300)
        
        # Kiểm tra cache
        if cache_key in self.cached_data:
            cache_time, df = self.cached_data[cache_key]
            if time.time() - cache_time < cache_timeout:
                logger.debug(f"Sử dụng dữ liệu cache cho {symbol} {timeframe}")
                return df
        
        try:
            # Lấy dữ liệu từ API
            limit = 100  # Số lượng candle cần lấy
            if self.binance_api is None:
                logger.error("Đối tượng binance_api không được khởi tạo")
                return None
            klines = self.binance_api.get_klines(symbol=symbol, interval=timeframe, limit=limit)
            
            # Chuyển đổi thành DataFrame
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                            'close_time', 'quote_asset_volume', 'number_of_trades', 
                                            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume', 
                             'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            # Thêm các chỉ báo cần thiết
            df = self._add_indicators(df)
            
            # Cache dữ liệu
            self.cached_data[cache_key] = (time.time(), df)
            
            return df
        
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu cho {symbol} {timeframe}: {str(e)}")
            return None
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các chỉ báo kỹ thuật vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã thêm
        """
        # Thêm SMA và EMA
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # Thêm RSI
        rsi_period = self.config.get('rsi_parameters', {}).get('period', 14)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=rsi_period).mean()
        avg_loss = loss.rolling(window=rsi_period).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Thêm MACD
        macd_params = self.config.get('macd_parameters', {})
        fast_period = macd_params.get('fast_period', 12)
        slow_period = macd_params.get('slow_period', 26)
        signal_period = macd_params.get('signal_period', 9)
        
        df['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Thêm Bollinger Bands
        bb_params = self.config.get('bollinger_parameters', {})
        bb_period = bb_params.get('period', 20)
        bb_std = bb_params.get('std_dev', 2.0)
        
        df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
        df['bb_std'] = df['close'].rolling(window=bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * bb_std)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * bb_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Thêm ATR
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = true_range.rolling(window=14).mean()
        
        # Thêm Volume SMA
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        # Thêm ADX
        adx_period = self.config.get('adx_parameters', {}).get('period', 14)
        
        # Tính True Range
        df['tr1'] = abs(df['high'] - df['low'])
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Tính Directional Movement
        df['up_move'] = df['high'] - df['high'].shift()
        df['down_move'] = df['low'].shift() - df['low']
        
        df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
        df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
        
        # Tính Directional Indicators
        df['plus_di'] = 100 * (df['plus_dm'].rolling(window=adx_period).mean() / df['tr'].rolling(window=adx_period).mean())
        df['minus_di'] = 100 * (df['minus_dm'].rolling(window=adx_period).mean() / df['tr'].rolling(window=adx_period).mean())
        
        # Tính Directional Index
        df['dx'] = 100 * (abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']))
        
        # Tính ADX
        df['adx'] = df['dx'].rolling(window=adx_period).mean()
        
        return df
    
    def _evaluate_trend_strength(self, df: pd.DataFrame, symbol: str, timeframe: str) -> float:
        """
        Đánh giá độ mạnh xu hướng
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            float: Điểm đánh giá (0-100)
        """
        try:
            # Lấy giá trị ADX
            adx = df['adx'].iloc[-1]
            strong_trend = self.config.get('adx_parameters', {}).get('strong_trend', 25)
            
            # Kiểm tra xu hướng với EMA
            ema_20 = df['ema_20'].iloc[-1]
            ema_50 = df['ema_50'].iloc[-1]
            ema_trend = 0
            
            if ema_20 > ema_50:
                # Xu hướng tăng
                ema_trend = (ema_20 / ema_50 - 1) * 100
            else:
                # Xu hướng giảm
                ema_trend = (1 - ema_20 / ema_50) * 100
            
            # Điểm ADX - Mạnh khi ADX > 25, rất mạnh khi ADX > 50
            adx_score = min(100, adx * 2) if adx > strong_trend else (adx / strong_trend) * 50
            
            # Điểm EMA - Mạnh khi chênh lệch lớn
            ema_score = min(100, ema_trend * 10)
            
            # Điểm BB Width - Xu hướng mạnh khi BB mở rộng
            bb_width = df['bb_width'].iloc[-1]
            bb_width_avg = df['bb_width'].rolling(window=20).mean().iloc[-1]
            bb_width_score = 100 if bb_width > bb_width_avg * 1.5 else (bb_width / bb_width_avg) * 75
            
            # Điểm tổng hợp
            trend_score = 0.5 * adx_score + 0.3 * ema_score + 0.2 * bb_width_score
            
            return trend_score
        
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá độ mạnh xu hướng cho {symbol} {timeframe}: {str(e)}")
            return 50  # Điểm trung bình
    
    def _evaluate_momentum(self, df: pd.DataFrame, symbol: str, timeframe: str) -> float:
        """
        Đánh giá động lượng (momentum)
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            float: Điểm đánh giá (0-100)
        """
        try:
            # Lấy giá trị RSI
            rsi = df['rsi'].iloc[-1]
            rsi_params = self.config.get('rsi_parameters', {})
            overbought = rsi_params.get('overbought', 70)
            oversold = rsi_params.get('oversold', 30)
            
            # Lấy giá trị MACD
            macd = df['macd'].iloc[-1]
            macd_signal = df['macd_signal'].iloc[-1]
            macd_hist = df['macd_hist'].iloc[-1]
            macd_hist_prev = df['macd_hist'].iloc[-2]
            
            # Điểm RSI
            rsi_score = 0
            if rsi > overbought:
                # Quá mua
                rsi_score = 80 - (rsi - overbought)
            elif rsi < oversold:
                # Quá bán
                rsi_score = 80 + (oversold - rsi)
            else:
                # Trung tính, điểm cao khi gần quá mua/quá bán
                rsi_score = 50 + min(abs(rsi - 50), 20)
            
            # Điểm MACD
            macd_score = 0
            
            # MACD trên Signal Line
            if macd > macd_signal:
                base_score = 60
                # MACD Histogram đang tăng
                if macd_hist > macd_hist_prev:
                    base_score += 20
                macd_score = base_score + min(abs(macd), 20)
            else:
                base_score = 40
                # MACD Histogram đang giảm
                if macd_hist < macd_hist_prev:
                    base_score -= 20
                macd_score = base_score - min(abs(macd), 20)
            
            # Điểm tổng hợp
            momentum_score = 0.5 * rsi_score + 0.5 * macd_score
            
            return momentum_score
        
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá động lượng cho {symbol} {timeframe}: {str(e)}")
            return 50  # Điểm trung bình
    
    def _evaluate_volume_confirmation(self, df: pd.DataFrame, symbol: str, timeframe: str) -> float:
        """
        Đánh giá xác nhận khối lượng
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            float: Điểm đánh giá (0-100)
        """
        try:
            # Lấy khối lượng gần đây
            volume = df['volume'].iloc[-1]
            volume_sma = df['volume_sma_20'].iloc[-1]
            volume_ratio = df['volume_ratio'].iloc[-1]
            
            # Lấy giá gần đây
            close = df['close'].iloc[-1]
            close_prev = df['close'].iloc[-2]
            price_change = (close - close_prev) / close_prev
            
            # Lấy tham số
            vol_params = self.config.get('volume_parameters', {})
            significant_increase = vol_params.get('significant_increase', 1.5)
            
            # Tính điểm khối lượng
            volume_score = 0
            
            # Khối lượng cao hơn trung bình
            if volume_ratio > 1:
                base_score = 50 + (volume_ratio - 1) * 25
                base_score = min(base_score, 90)
                
                # Khối lượng tăng mạnh
                if volume_ratio > significant_increase:
                    base_score += 10
                
                # Xác nhận xu hướng giá
                if (price_change > 0 and close > df['ema_20'].iloc[-1]) or (price_change < 0 and close < df['ema_20'].iloc[-1]):
                    base_score += 10
                
                volume_score = base_score
            else:
                # Khối lượng thấp hơn trung bình
                volume_score = 50 - (1 - volume_ratio) * 25
            
            # Điều chỉnh điểm theo sự đồng thuận giữa khối lượng và giá
            if (price_change > 0.01 and volume_ratio > 1.3) or (price_change < -0.01 and volume_ratio > 1.3):
                volume_score = min(volume_score + 10, 100)
            
            # Điều chỉnh điểm nếu khối lượng quá thấp
            if volume_ratio < 0.5:
                volume_score = max(volume_score - 20, 0)
            
            return volume_score
        
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá xác nhận khối lượng cho {symbol} {timeframe}: {str(e)}")
            return 50  # Điểm trung bình
    
    def _evaluate_price_patterns(self, df: pd.DataFrame, symbol: str, timeframe: str) -> float:
        """
        Đánh giá mẫu hình giá
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            float: Điểm đánh giá (0-100)
        """
        try:
            # Dữ liệu gần đây
            closes = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            
            pattern_scores = self.config.get('price_pattern_scores', {})
            detected_patterns = []
            
            # Kiểm tra gần Bollinger Bands
            bb_upper = df['bb_upper'].iloc[-1]
            bb_lower = df['bb_lower'].iloc[-1]
            close = df['close'].iloc[-1]
            
            if close > bb_upper * 0.98:
                detected_patterns.append(('bollinger_upper_touch', 60))
            elif close < bb_lower * 1.02:
                detected_patterns.append(('bollinger_lower_touch', 60))
            
            # Kiểm tra nến Doji
            body_size = abs(df['close'].iloc[-1] - df['open'].iloc[-1])
            candle_size = df['high'].iloc[-1] - df['low'].iloc[-1]
            
            if body_size < candle_size * 0.1:
                detected_patterns.append(('doji', 70))
            
            # Kiểm tra nến Hammer/Inverted Hammer
            if df['low'].iloc[-1] < df['close'].iloc[-1] < df['open'].iloc[-1]:
                # Hammer (lower shadow at least 2x body)
                lower_shadow = df['open'].iloc[-1] - df['low'].iloc[-1]
                if lower_shadow > body_size * 2:
                    detected_patterns.append(('hammer', 75))
            elif df['high'].iloc[-1] > df['open'].iloc[-1] > df['close'].iloc[-1]:
                # Inverted Hammer (upper shadow at least 2x body)
                upper_shadow = df['high'].iloc[-1] - df['open'].iloc[-1]
                if upper_shadow > body_size * 2:
                    detected_patterns.append(('inverted_hammer', 75))
            
            # Kiểm tra giao cắt EMA
            ema_20 = df['ema_20'].iloc[-1]
            ema_50 = df['ema_50'].iloc[-1]
            ema_20_prev = df['ema_20'].iloc[-2]
            ema_50_prev = df['ema_50'].iloc[-2]
            
            if ema_20_prev < ema_50_prev and ema_20 > ema_50:
                detected_patterns.append(('ema_golden_cross', 80))
            elif ema_20_prev > ema_50_prev and ema_20 < ema_50:
                detected_patterns.append(('ema_death_cross', 80))
            
            # Nếu không phát hiện mẫu hình, trả về điểm trung bình
            if not detected_patterns:
                return 50
            
            # Tính điểm trung bình từ các mẫu hình đã phát hiện
            pattern_score = sum(score for _, score in detected_patterns) / len(detected_patterns)
            
            return pattern_score
        
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá mẫu hình giá cho {symbol} {timeframe}: {str(e)}")
            return 50  # Điểm trung bình
    
    def _evaluate_support_resistance(self, df: pd.DataFrame, symbol: str, timeframe: str) -> float:
        """
        Đánh giá hỗ trợ/kháng cự
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            float: Điểm đánh giá (0-100)
        """
        try:
            # Tìm các mức hỗ trợ/kháng cự
            close = df['close'].iloc[-1]
            
            # Phương pháp đơn giản: tìm các đỉnh, đáy cục bộ
            highs = df['high'].values
            lows = df['low'].values
            
            # Tìm các đỉnh cục bộ
            resistance_levels = []
            for i in range(3, len(highs) - 3):
                if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i-3] and \
                   highs[i] > highs[i+1] and highs[i] > highs[i+2] and highs[i] > highs[i+3]:
                    resistance_levels.append(highs[i])
            
            # Tìm các đáy cục bộ
            support_levels = []
            for i in range(3, len(lows) - 3):
                if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i-3] and \
                   lows[i] < lows[i+1] and lows[i] < lows[i+2] and lows[i] < lows[i+3]:
                    support_levels.append(lows[i])
            
            # Thêm BB Bands làm mức hỗ trợ/kháng cự động
            resistance_levels.append(df['bb_upper'].iloc[-1])
            support_levels.append(df['bb_lower'].iloc[-1])
            
            # Tính khoảng cách đến mức hỗ trợ/kháng cự gần nhất
            min_distance_resistance = float('inf')
            min_distance_support = float('inf')
            
            for level in resistance_levels:
                if level > close:
                    distance = (level - close) / close
                    min_distance_resistance = min(min_distance_resistance, distance)
            
            for level in support_levels:
                if level < close:
                    distance = (close - level) / close
                    min_distance_support = min(min_distance_support, distance)
            
            # Tính điểm dựa trên khoảng cách đến mức hỗ trợ/kháng cự
            sr_score = 50
            
            # Gần mức hỗ trợ
            if min_distance_support < 0.01:
                sr_score = 80
            elif min_distance_support < 0.03:
                sr_score = 70
            
            # Gần mức kháng cự
            if min_distance_resistance < 0.01:
                sr_score = 80
            elif min_distance_resistance < 0.03:
                sr_score = 70
            
            # Nếu giá đang ở giữa hỗ trợ và kháng cự
            if min_distance_support < 0.05 and min_distance_resistance < 0.05:
                sr_score = 60
            
            return sr_score
        
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá hỗ trợ/kháng cự cho {symbol} {timeframe}: {str(e)}")
            return 50  # Điểm trung bình
    
    def _evaluate_btc_alignment(self, df: pd.DataFrame, symbol: str, timeframe: str) -> float:
        """
        Đánh giá sự phù hợp với xu hướng BTC
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            float: Điểm đánh giá (0-100)
        """
        try:
            # Nếu đây là BTC, điểm là 100
            if symbol == 'BTCUSDT':
                return 100
            
            # Lấy dữ liệu BTC
            btc_df = self._get_data_for_evaluation('BTCUSDT', timeframe)
            if btc_df is None:
                return 50
            
            # Tính tương quan
            correlation = self._calculate_btc_correlation(df, timeframe, btc_df)
            
            # Lấy các chỉ số của BTC và cặp tiền
            btc_trend = 1 if btc_df['ema_20'].iloc[-1] > btc_df['ema_50'].iloc[-1] else -1
            coin_trend = 1 if df['ema_20'].iloc[-1] > df['ema_50'].iloc[-1] else -1
            
            # Tính điểm căn chỉnh
            alignment_score = 50
            
            # Tương quan cao và cùng xu hướng
            if correlation > 0.7 and btc_trend == coin_trend:
                alignment_score = 80 + correlation * 20
            # Tương quan cao nhưng khác xu hướng
            elif correlation > 0.7 and btc_trend != coin_trend:
                alignment_score = 30
            # Tương quan trung bình và cùng xu hướng
            elif correlation > 0.4 and btc_trend == coin_trend:
                alignment_score = 60 + correlation * 20
            # Tương quan trung bình nhưng khác xu hướng
            elif correlation > 0.4 and btc_trend != coin_trend:
                alignment_score = 40
            # Tương quan thấp
            else:
                alignment_score = 50
            
            return min(alignment_score, 100)
        
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá sự phù hợp với BTC cho {symbol} {timeframe}: {str(e)}")
            return 50  # Điểm trung bình
    
    def _calculate_btc_correlation(self, df: pd.DataFrame, timeframe: str, btc_df: pd.DataFrame = None) -> float:
        """
        Tính hệ số tương quan với BTC
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu cặp tiền
            timeframe (str): Khung thời gian
            btc_df (pd.DataFrame, optional): DataFrame dữ liệu BTC
            
        Returns:
            float: Hệ số tương quan (-1 đến 1)
        """
        try:
            # Nếu không có dữ liệu BTC, lấy từ API
            if btc_df is None:
                btc_df = self._get_data_for_evaluation('BTCUSDT', timeframe)
                if btc_df is None:
                    return 0
            
            # Tính lợi nhuận %
            df_returns = df['close'].pct_change().dropna()
            btc_returns = btc_df['close'].pct_change().dropna()
            
            # Đảm bảo cùng độ dài
            min_len = min(len(df_returns), len(btc_returns))
            df_returns = df_returns[-min_len:]
            btc_returns = btc_returns[-min_len:]
            
            # Tính hệ số tương quan
            correlation = df_returns.corr(btc_returns)
            return correlation
        
        except Exception as e:
            logger.error(f"Lỗi khi tính hệ số tương quan với BTC: {str(e)}")
            return 0
    
    def _evaluate_multi_timeframe(self, symbol: str, base_timeframe: str) -> float:
        """
        Đánh giá đa khung thời gian
        
        Args:
            symbol (str): Mã cặp tiền
            base_timeframe (str): Khung thời gian cơ sở
            
        Returns:
            float: Điểm đánh giá (0-100)
        """
        try:
            # Xác định các khung thời gian cần kiểm tra
            all_timeframes = list(self.config.get('multi_timeframe_weights', {}).keys())
            
            # Nếu không có đủ khung thời gian, trả về -1 (không đánh giá)
            if len(all_timeframes) < 2:
                return -1
            
            # Lọc ra các khung thời gian cao hơn
            higher_timeframes = []
            tf_order = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']
            
            base_index = tf_order.index(base_timeframe) if base_timeframe in tf_order else -1
            if base_index == -1 or base_index >= len(tf_order) - 1:
                return -1
            
            for tf in all_timeframes:
                if tf in tf_order and tf_order.index(tf) > base_index:
                    higher_timeframes.append(tf)
            
            if not higher_timeframes:
                return -1
            
            # Đánh giá tín hiệu trên các khung thời gian cao hơn
            signals = {}
            for tf in higher_timeframes:
                tf_data = self._get_data_for_evaluation(symbol, tf)
                if tf_data is not None:
                    tf_signal = self._determine_signal_direction(tf_data, symbol, tf)
                    signals[tf] = tf_signal
            
            # Nếu không có đủ dữ liệu, trả về -1
            if not signals:
                return -1
            
            # Lấy tín hiệu ở khung thời gian cơ sở
            base_data = self._get_data_for_evaluation(symbol, base_timeframe)
            if base_data is None:
                return -1
            
            base_signal = self._determine_signal_direction(base_data, symbol, base_timeframe)
            
            # Tính điểm phù hợp
            agreement_score = 0
            total_weight = 0
            
            for tf, signal in signals.items():
                weight = self.config.get('multi_timeframe_weights', {}).get(tf, 0.1)
                if signal == base_signal:
                    agreement_score += 100 * weight
                elif signal == 'NEUTRAL' or base_signal == 'NEUTRAL':
                    agreement_score += 50 * weight
                else:
                    agreement_score += 0 * weight
                
                total_weight += weight
            
            if total_weight == 0:
                return -1
            
            return agreement_score / total_weight
        
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá đa khung thời gian cho {symbol}: {str(e)}")
            return -1
    
    def _determine_signal_direction(self, df: pd.DataFrame, symbol: str, timeframe: str) -> str:
        """
        Xác định hướng tín hiệu giao dịch
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            str: Hướng tín hiệu ('LONG', 'SHORT', 'NEUTRAL')
        """
        try:
            # Lấy giá trị chỉ báo
            ema_20 = df['ema_20'].iloc[-1]
            ema_50 = df['ema_50'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            macd = df['macd'].iloc[-1]
            macd_signal = df['macd_signal'].iloc[-1]
            close = df['close'].iloc[-1]
            adx = df['adx'].iloc[-1]
            
            # Đếm số tín hiệu cho mỗi hướng
            long_signals = 0
            short_signals = 0
            
            # EMA Cross
            if ema_20 > ema_50:
                long_signals += 1
            else:
                short_signals += 1
            
            # RSI
            if rsi > 50:
                long_signals += 1
            else:
                short_signals += 1
            
            # MACD
            if macd > macd_signal:
                long_signals += 1
            else:
                short_signals += 1
            
            # Giá vs EMA
            if close > ema_20:
                long_signals += 1
            else:
                short_signals += 1
            
            # ADX - xác định xu hướng rõ ràng
            has_trend = adx > self.config.get('adx_parameters', {}).get('strong_trend', 25)
            
            # Quyết định hướng tín hiệu
            if long_signals > short_signals and (has_trend or long_signals >= 3):
                return 'LONG'
            elif short_signals > long_signals and (has_trend or short_signals >= 3):
                return 'SHORT'
            else:
                return 'NEUTRAL'
            
        except Exception as e:
            logger.error(f"Lỗi khi xác định hướng tín hiệu cho {symbol} {timeframe}: {str(e)}")
            return 'NEUTRAL'
    
    def _determine_signal_strength(self, total_score: float) -> str:
        """
        Xác định cường độ tín hiệu dựa trên điểm tổng hợp
        
        Args:
            total_score (float): Điểm tổng hợp
            
        Returns:
            str: Cường độ tín hiệu ('STRONG', 'MODERATE', 'WEAK', 'VERY_WEAK')
        """
        thresholds = self.config.get('signal_quality_thresholds', {})
        
        if total_score >= thresholds.get('excellent', 80):
            return 'STRONG'
        elif total_score >= thresholds.get('good', 65):
            return 'MODERATE'
        elif total_score >= thresholds.get('moderate', 50):
            return 'WEAK'
        else:
            return 'VERY_WEAK'
    
    def _save_evaluation(self, symbol: str, timeframe: str, result: Dict) -> None:
        """
        Lưu kết quả đánh giá vào lịch sử
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            result (Dict): Kết quả đánh giá
        """
        key = f"{symbol}_{timeframe}"
        
        if key not in self.evaluation_history:
            self.evaluation_history[key] = []
        
        # Giới hạn lịch sử lưu trữ (giữ 100 bản ghi gần nhất)
        if len(self.evaluation_history[key]) >= 100:
            self.evaluation_history[key].pop(0)
        
        self.evaluation_history[key].append(result)
        
        # Lưu lịch sử định kỳ
        self._save_evaluation_history()
    
    def _save_evaluation_history(self) -> None:
        """Lưu lịch sử đánh giá vào file"""
        try:
            with open('data/signal_quality_history.json', 'w') as f:
                json.dump(self.evaluation_history, f)
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử đánh giá: {str(e)}")
    
    def _load_evaluation_history(self) -> None:
        """Tải lịch sử đánh giá từ file"""
        try:
            with open('data/signal_quality_history.json', 'r') as f:
                self.evaluation_history = json.load(f)
            logger.info("Đã tải lịch sử đánh giá tín hiệu")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Không tìm thấy hoặc không thể tải lịch sử đánh giá tín hiệu")
            self.evaluation_history = {}
    
    def get_signal_quality_trend(self, symbol: str, timeframe: str, lookback: int = 10) -> Dict:
        """
        Lấy xu hướng chất lượng tín hiệu trong khoảng thời gian gần đây
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            lookback (int): Số kết quả đánh giá gần nhất để phân tích
            
        Returns:
            Dict: Kết quả phân tích xu hướng
        """
        key = f"{symbol}_{timeframe}"
        
        if key not in self.evaluation_history or not self.evaluation_history[key]:
            return {
                'trend': 'unknown',
                'stability': 0,
                'current_score': 0,
                'average_score': 0,
                'direction_changes': 0,
                'strength_changes': 0
            }
        
        history = self.evaluation_history[key]
        
        # Lấy các kết quả gần nhất
        recent_evaluations = history[-lookback:] if len(history) >= lookback else history
        
        # Tính các chỉ số
        scores = [eval_result['score'] for eval_result in recent_evaluations]
        directions = [eval_result['signal_direction'] for eval_result in recent_evaluations]
        strengths = [eval_result['signal_strength'] for eval_result in recent_evaluations]
        
        current_score = scores[-1] if scores else 0
        average_score = sum(scores) / len(scores) if scores else 0
        
        # Đếm số lần thay đổi hướng
        direction_changes = sum(1 for i in range(1, len(directions)) if directions[i] != directions[i-1])
        
        # Đếm số lần thay đổi cường độ
        strength_changes = sum(1 for i in range(1, len(strengths)) if strengths[i] != strengths[i-1])
        
        # Xác định xu hướng điểm
        if len(scores) >= 3:
            first_half = scores[:len(scores)//2]
            second_half = scores[len(scores)//2:]
            
            first_half_avg = sum(first_half) / len(first_half)
            second_half_avg = sum(second_half) / len(second_half)
            
            if second_half_avg > first_half_avg + 5:
                trend = 'improving'
            elif second_half_avg < first_half_avg - 5:
                trend = 'deteriorating'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient data'
        
        # Tính độ ổn định
        if scores:
            stability = 100 - (np.std(scores) / average_score * 100 if average_score > 0 else 0)
        else:
            stability = 0
        
        return {
            'trend': trend,
            'stability': stability,
            'current_score': current_score,
            'average_score': average_score,
            'direction_changes': direction_changes,
            'strength_changes': strength_changes,
            'data_points': len(recent_evaluations)
        }
    
    def get_best_quality_symbols(self, symbols: List[str] = None, timeframe: str = '1h') -> List[Dict]:
        """
        Lấy danh sách các cặp tiền có chất lượng tín hiệu tốt nhất
        
        Args:
            symbols (List[str], optional): Danh sách các cặp tiền cần kiểm tra
            timeframe (str): Khung thời gian
            
        Returns:
            List[Dict]: Danh sách các cặp tiền được xếp hạng theo chất lượng tín hiệu
        """
        # Nếu không có danh sách symbols, sử dụng danh sách cặp tiền đã lưu trong lịch sử
        if symbols is None:
            symbols = []
            for key in self.evaluation_history.keys():
                if key.endswith(f"_{timeframe}"):
                    symbol = key.split('_')[0]
                    symbols.append(symbol)
            
            # Nếu vẫn không có symbols, trả về danh sách rỗng
            if not symbols:
                return []
        
        # Đánh giá tất cả các cặp tiền
        results = []
        for symbol in symbols:
            # Kiểm tra xem đã có kết quả mới nhất trong lịch sử chưa
            key = f"{symbol}_{timeframe}"
            if key in self.evaluation_history and self.evaluation_history[key]:
                latest_evaluation = self.evaluation_history[key][-1]
                
                # Kiểm tra xem kết quả có quá cũ không (>30 phút)
                if time.time() - latest_evaluation.get('timestamp', 0) < 1800:
                    score = latest_evaluation.get('score', 0)
                    direction = latest_evaluation.get('signal_direction', 'NEUTRAL')
                    strength = latest_evaluation.get('signal_strength', 'WEAK')
                else:
                    # Nếu kết quả quá cũ, đánh giá lại
                    try:
                        score, latest_evaluation = self.evaluate_signal_quality(symbol, timeframe)
                        if not isinstance(latest_evaluation, dict):
                            logger.error(f"Đánh giá signal quality cho {symbol} không trả về đúng định dạng")
                            continue
                        direction = latest_evaluation.get('signal_direction', 'NEUTRAL')
                        strength = latest_evaluation.get('signal_strength', 'WEAK')
                    except Exception as e:
                        logger.error(f"Lỗi khi đánh giá signal quality cho {symbol}: {str(e)}")
                        continue
            else:
                # Nếu chưa có kết quả, đánh giá mới
                try:
                    score, latest_evaluation = self.evaluate_signal_quality(symbol, timeframe)
                    if not isinstance(latest_evaluation, dict):
                        logger.error(f"Đánh giá signal quality cho {symbol} không trả về đúng định dạng")
                        continue
                    direction = latest_evaluation.get('signal_direction', 'NEUTRAL')
                    strength = latest_evaluation.get('signal_strength', 'WEAK')
                except Exception as e:
                    logger.error(f"Lỗi khi đánh giá signal quality cho {symbol}: {str(e)}")
                    continue
            
            results.append({
                'symbol': symbol,
                'score': score,
                'direction': direction,
                'strength': strength,
                'btc_correlation': latest_evaluation.get('btc_correlation', 0)
            })
        
        # Sắp xếp theo điểm giảm dần
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results


def main():
    """Hàm chính để test signal quality"""
    from binance_api import BinanceAPI
    
    # Khởi tạo API
    binance_api = BinanceAPI()
    
    # Khởi tạo Signal Quality
    signal_quality = EnhancedSignalQuality(binance_api=binance_api)
    
    # Test với một số cặp tiền
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    timeframe = '1h'
    
    for symbol in symbols:
        score, details = signal_quality.evaluate_signal_quality(symbol, timeframe)
        print(f"{symbol}: Score = {score:.2f}, Direction = {details['signal_direction']}, Strength = {details['signal_strength']}")
        
        # In chi tiết
        print(f"  - Trend Strength: {details['component_scores']['trend_strength']:.2f}")
        print(f"  - Momentum: {details['component_scores']['momentum']:.2f}")
        print(f"  - Volume Confirmation: {details['component_scores']['volume_confirmation']:.2f}")
        print(f"  - BTC Correlation: {details['btc_correlation']:.2f}")
        print()
    
    # Test multi-timeframe
    print("Multi-timeframe analysis:")
    multi_tf_score = signal_quality._evaluate_multi_timeframe('BTCUSDT', '1h')
    print(f"Multi-timeframe score: {multi_tf_score:.2f}")
    
    # Test get best quality symbols
    best_symbols = signal_quality.get_best_quality_symbols(symbols, timeframe)
    print("\nBest quality symbols:")
    for result in best_symbols:
        print(f"{result['symbol']}: Score = {result['score']:.2f}, Direction = {result['direction']}")


if __name__ == "__main__":
    main()