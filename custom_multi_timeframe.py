"""
Module phân tích đa khung thời gian (Multi-timeframe Analysis)

Module này cung cấp các công cụ để phân tích thị trường trên nhiều khung thời gian
khác nhau và tổng hợp kết quả để có tín hiệu giao dịch chính xác hơn.
"""

import os
import json
import time
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from binance_api import BinanceAPI
from data_processor import DataProcessor

# Thiết lập logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('multi_timeframe')

class MultiTimeframeAnalyzer:
    """
    Lớp phân tích đa khung thời gian, kết hợp tín hiệu từ nhiều khung 
    thời gian khác nhau để tăng độ tin cậy của tín hiệu giao dịch.
    """
    
    # Các khung thời gian mặc định để phân tích
    DEFAULT_TIMEFRAMES = ['15m', '1h', '4h', '1d']
    
    # Trọng số mặc định cho mỗi khung thời gian (càng dài càng quan trọng)
    DEFAULT_WEIGHTS = {
        '1m': 0.05,
        '3m': 0.07,
        '5m': 0.10,
        '15m': 0.15,
        '30m': 0.18,
        '1h': 0.25,
        '2h': 0.28,
        '4h': 0.30,
        '6h': 0.35,
        '12h': 0.40,
        '1d': 0.45,
        '3d': 0.50,
        '1w': 0.60
    }
    
    def __init__(self, binance_api: BinanceAPI = None, data_processor: DataProcessor = None, 
                timeframes: List[str] = None):
        """
        Khởi tạo phân tích đa khung thời gian
        
        Args:
            binance_api (BinanceAPI, optional): Đối tượng BinanceAPI
            data_processor (DataProcessor, optional): Đối tượng DataProcessor
            timeframes (List[str], optional): Danh sách các khung thời gian cần phân tích
        """
        self.binance_api = binance_api if binance_api else BinanceAPI()
        self.data_processor = data_processor if data_processor else DataProcessor(self.binance_api)
        self.timeframes = timeframes if timeframes else self.DEFAULT_TIMEFRAMES
        self.signals_cache = {}
        
        logger.info(f"Khởi tạo Bộ phân tích đa khung thời gian với các khung: {self.timeframes}")
    
    def analyze_timeframe(self, symbol: str, timeframe: str, lookback_days: int = 30) -> Dict:
        """
        Phân tích một khung thời gian cụ thể
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            lookback_days (int): Số ngày dữ liệu phân tích
            
        Returns:
            Dict: Kết quả phân tích cho khung thời gian
        """
        try:
            # Lấy dữ liệu
            df = self.data_processor.get_historical_data(symbol, timeframe, lookback_days)
            
            if df is None or df.empty:
                logger.warning(f"Không có dữ liệu cho {symbol} trên khung {timeframe}")
                return {
                    "timeframe": timeframe,
                    "trend": 0,
                    "strength": 0,
                    "signal": 0
                }
            
            # Phân tích xu hướng
            ema_short = df['close'].ewm(span=9, adjust=False).mean().iloc[-1]
            ema_medium = df['close'].ewm(span=21, adjust=False).mean().iloc[-1]
            ema_long = df['close'].ewm(span=55, adjust=False).mean().iloc[-1]
            current_close = df['close'].iloc[-1]
            
            # Xác định xu hướng (2: rất tăng, 1: tăng, 0: đi ngang, -1: giảm, -2: rất giảm)
            trend = 0
            if current_close > ema_short > ema_medium > ema_long:
                trend = 2  # Rất tăng
            elif current_close > ema_medium > ema_long:
                trend = 1  # Tăng
            elif current_close < ema_short < ema_medium < ema_long:
                trend = -2  # Rất giảm
            elif current_close < ema_medium < ema_long:
                trend = -1  # Giảm
            
            # Phân tích RSI
            rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50
            
            # Phân tích MACD
            macd_val = df['macd'].iloc[-1] if 'macd' in df.columns else 0
            macd_signal = df['macd_signal'].iloc[-1] if 'macd_signal' in df.columns else 0
            macd_hist = macd_val - macd_signal
            
            # Tính độ mạnh của tín hiệu (0-100)
            strength = 0
            if trend > 0:  # Xu hướng tăng
                strength = min(100, max(0, (rsi - 30) * 1.5))
                if macd_hist > 0:
                    strength += 20
                if macd_hist > macd_hist_prev:
                    strength += 10
            elif trend < 0:  # Xu hướng giảm
                strength = min(100, max(0, (70 - rsi) * 1.5))
                if macd_hist < 0:
                    strength += 20
                if macd_hist < macd_hist_prev:
                    strength += 10
            
            # Chuẩn hóa strength về khoảng 0-100
            strength = max(0, min(100, strength))
            
            # Xác định tín hiệu (-1: bán, 0: không có, 1: mua)
            signal = 0
            if trend >= 1 and rsi < 70 and macd_hist > 0:
                signal = 1
            elif trend <= -1 and rsi > 30 and macd_hist < 0:
                signal = -1
            
            return {
                "timeframe": timeframe,
                "trend": trend,
                "strength": strength,
                "signal": signal,
                "rsi": rsi,
                "macd": macd_val,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
                "ema_short": ema_short,
                "ema_medium": ema_medium,
                "ema_long": ema_long,
                "close": current_close,
                "weight": self.DEFAULT_WEIGHTS.get(timeframe, 0.2)
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích {symbol} trên khung {timeframe}: {str(e)}")
            return {
                "timeframe": timeframe,
                "trend": 0,
                "strength": 0,
                "signal": 0,
                "error": str(e)
            }
    
    def consolidate_signals(self, symbol: str, lookback_days: int = 30) -> Dict:
        """
        Tổng hợp tín hiệu từ tất cả các khung thời gian
        
        Args:
            symbol (str): Mã cặp giao dịch
            lookback_days (int): Số ngày dữ liệu phân tích
            
        Returns:
            Dict: Tín hiệu tổng hợp
        """
        # Kiểm tra cache
        cache_key = f"{symbol}_{lookback_days}"
        cache_time = self.signals_cache.get(cache_key, {}).get('timestamp', 0)
        current_time = time.time()
        
        # Nếu cache hợp lệ (dưới 5 phút)
        if current_time - cache_time < 300:
            return self.signals_cache.get(cache_key, {}).get('data', {})
        
        try:
            # Phân tích từng khung thời gian
            timeframe_results = {}
            trend_analysis = {}
            rsi_analysis = {}
            macd_analysis = {}
            
            for tf in self.timeframes:
                result = self.analyze_timeframe(symbol, tf, lookback_days)
                timeframe_results[tf] = result
                
                # Lưu kết quả phân tích xu hướng
                if 'trend' in result:
                    trend_analysis[tf] = {
                        'trend': result['trend'],
                        'ema_short': result.get('ema_short', 0),
                        'ema_medium': result.get('ema_medium', 0),
                        'ema_long': result.get('ema_long', 0),
                        'close': result.get('close', 0),
                        'weight': result.get('weight', self.DEFAULT_WEIGHTS.get(tf, 0.2))
                    }
                
                # Lưu kết quả phân tích RSI
                if 'rsi' in result:
                    rsi_analysis[tf] = {
                        'rsi': result['rsi'],
                        'weight': result.get('weight', self.DEFAULT_WEIGHTS.get(tf, 0.2))
                    }
                
                # Lưu kết quả phân tích MACD
                if 'macd' in result and 'macd_signal' in result:
                    macd_analysis[tf] = {
                        'macd': result['macd'],
                        'macd_signal': result['macd_signal'],
                        'macd_hist': result.get('macd_hist', 0),
                        'weight': result.get('weight', self.DEFAULT_WEIGHTS.get(tf, 0.2))
                    }
            
            # Tính tín hiệu tổng hợp
            weighted_signal = 0
            total_weight = 0
            confidence = 0
            
            for tf, result in timeframe_results.items():
                weight = result.get('weight', self.DEFAULT_WEIGHTS.get(tf, 0.2))
                signal = result.get('signal', 0)
                strength = result.get('strength', 0)
                
                weighted_signal += signal * weight
                total_weight += weight
                
                if signal != 0:
                    confidence += (strength / 100) * weight
            
            if total_weight > 0:
                weighted_signal /= total_weight
                confidence = (confidence / total_weight) * 100
            
            # Chuẩn hóa weighted_signal tới [-1, 0, 1]
            signal = 0
            raw_signal = weighted_signal
            if weighted_signal > 0.3:
                signal = 1
            elif weighted_signal < -0.3:
                signal = -1
            
            # Xác định mô tả tín hiệu
            signal_description = "TRUNG LẬP"
            position_size_factor = 0.5
            
            if signal == 1:
                if raw_signal > 0.7:
                    signal_description = "MUA mạnh"
                    position_size_factor = 1.0
                else:
                    signal_description = "MUA nhẹ"
                    position_size_factor = 0.7
            elif signal == -1:
                if raw_signal < -0.7:
                    signal_description = "BÁN mạnh"
                    position_size_factor = 1.0
                else:
                    signal_description = "BÁN nhẹ"
                    position_size_factor = 0.7
            
            # Tính độ biến động
            volatility = self._calculate_volatility(symbol)
            
            # Tạo kết quả tổng hợp
            consolidated_result = {
                "symbol": symbol,
                "signal": signal,
                "confidence": confidence,
                "position_size_factor": position_size_factor,
                "raw_signal": raw_signal,
                "signal_description": signal_description,
                "rsi_analysis": rsi_analysis,
                "trend_analysis": trend_analysis,
                "macd_analysis": macd_analysis,
                "volatility": volatility,
                "summary": f"{signal_description} với độ tin cậy {confidence:.1f}% (Hệ số vị thế: {position_size_factor:.2f})"
            }
            
            # Lưu vào cache
            self.signals_cache[cache_key] = {
                'timestamp': current_time,
                'data': consolidated_result
            }
            
            return consolidated_result
            
        except Exception as e:
            logger.error(f"Lỗi khi tổng hợp tín hiệu cho {symbol}: {str(e)}")
            return {
                "symbol": symbol,
                "signal": 0,
                "confidence": 0,
                "error": str(e)
            }
    
    def _calculate_volatility(self, symbol: str, timeframe: str = '1d', lookback_days: int = 14) -> float:
        """
        Tính toán độ biến động của một cặp giao dịch
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            lookback_days (int): Số ngày phân tích
            
        Returns:
            float: Giá trị biến động (phần trăm)
        """
        try:
            df = self.data_processor.get_historical_data(symbol, timeframe, lookback_days)
            
            if df is None or df.empty:
                return 0
            
            # Tính độ biến động bằng ATR/Giá trung bình
            if 'atr' in df.columns:
                atr = df['atr'].iloc[-1]
                avg_price = df['close'].mean()
                volatility = (atr / avg_price) * 100
            else:
                # Tính độ biến động theo phương sai chuẩn hóa
                returns = df['close'].pct_change().dropna()
                volatility = returns.std() * 100
            
            return volatility
            
        except Exception as e:
            logger.error(f"Lỗi khi tính độ biến động cho {symbol}: {str(e)}")
            return 0
    
    def get_optimal_entry_points(self, symbol: str, lookback_days: int = 30, 
                              lookforward_days: int = 5) -> Dict:
        """
        Xác định các điểm vào lệnh tối ưu
        
        Args:
            symbol (str): Mã cặp giao dịch
            lookback_days (int): Số ngày phân tích dữ liệu lịch sử
            lookforward_days (int): Số ngày dự báo
            
        Returns:
            Dict: Điểm vào lệnh tối ưu
        """
        try:
            # Lấy dữ liệu từ khung 1h để có độ chi tiết tốt
            df_1h = self.data_processor.get_historical_data(symbol, '1h', lookback_days)
            
            if df_1h is None or df_1h.empty:
                return {"entry_points": []}
            
            # Lấy tín hiệu tổng hợp
            signals = self.consolidate_signals(symbol, lookback_days)
            
            # Lấy giá hiện tại
            current_price = df_1h['close'].iloc[-1]
            
            # Xác định các điểm vào lệnh mua dựa trên phân tích Fibonacci
            entry_points = []
            
            # Tìm đỉnh cao nhất và đáy thấp nhất gần đây
            high = df_1h['high'].max()
            low = df_1h['low'].min()
            
            # Các mức Fibonacci Retracement
            fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786, 0.886]
            
            # Nếu xu hướng tăng, xác định các điểm mua ở mức hỗ trợ
            if signals.get('signal', 0) >= 0:
                for level in fib_levels:
                    fib_price = high - (high - low) * level
                    if fib_price < current_price:
                        # Giá ở mức hỗ trợ
                        distance_pct = (current_price - fib_price) / current_price * 100
                        entry_points.append({
                            "price": fib_price,
                            "type": "buy",
                            "strength": 100,
                            "distance_pct": distance_pct
                        })
            
            # Nếu xu hướng giảm, xác định các điểm bán ở mức kháng cự
            if signals.get('signal', 0) <= 0:
                for level in fib_levels:
                    fib_price = low + (high - low) * level
                    if fib_price > current_price:
                        # Giá ở mức kháng cự
                        distance_pct = (fib_price - current_price) / current_price * 100
                        entry_points.append({
                            "price": fib_price,
                            "type": "sell",
                            "strength": 100,
                            "distance_pct": distance_pct
                        })
            
            # Thêm các điểm vào lệnh dựa trên mức hỗ trợ/kháng cự gần đây
            sr_levels = self._find_support_resistance_levels(df_1h)
            
            for level in sr_levels:
                level_price = level['price']
                level_type = level['type']
                level_strength = level['strength']
                
                if level_type == 'support' and level_price < current_price:
                    distance_pct = (current_price - level_price) / current_price * 100
                    entry_points.append({
                        "price": level_price,
                        "type": "buy",
                        "strength": level_strength,
                        "distance_pct": distance_pct
                    })
                elif level_type == 'resistance' and level_price > current_price:
                    distance_pct = (level_price - current_price) / current_price * 100
                    entry_points.append({
                        "price": level_price,
                        "type": "sell",
                        "strength": level_strength,
                        "distance_pct": distance_pct
                    })
            
            # Sắp xếp các điểm vào lệnh theo khoảng cách
            entry_points = sorted(entry_points, key=lambda x: x['distance_pct'])
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "entry_points": entry_points
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi xác định điểm vào lệnh cho {symbol}: {str(e)}")
            return {"entry_points": []}
    
    def _find_support_resistance_levels(self, df: pd.DataFrame, window: int = 10, 
                                     threshold: float = 0.01) -> List[Dict]:
        """
        Tìm các mức hỗ trợ/kháng cự từ dữ liệu lịch sử
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            window (int): Cửa sổ để xác định đỉnh/đáy
            threshold (float): Ngưỡng để xác định mức hỗ trợ/kháng cự (phần trăm)
            
        Returns:
            List[Dict]: Danh sách các mức hỗ trợ/kháng cự
        """
        try:
            levels = []
            
            # Tìm các đỉnh cục bộ
            for i in range(window, len(df) - window):
                if df['high'].iloc[i] > max(df['high'].iloc[i-window:i]) and \
                   df['high'].iloc[i] > max(df['high'].iloc[i+1:i+window+1]):
                    price = df['high'].iloc[i]
                    
                    # Đếm số lần giá chạm mức này
                    touches = 0
                    for j in range(len(df)):
                        if abs(df['high'].iloc[j] - price) / price < threshold:
                            touches += 1
                    
                    strength = min(100, touches * 20)
                    
                    levels.append({
                        "price": price,
                        "type": "resistance",
                        "strength": strength
                    })
            
            # Tìm các đáy cục bộ
            for i in range(window, len(df) - window):
                if df['low'].iloc[i] < min(df['low'].iloc[i-window:i]) and \
                   df['low'].iloc[i] < min(df['low'].iloc[i+1:i+window+1]):
                    price = df['low'].iloc[i]
                    
                    # Đếm số lần giá chạm mức này
                    touches = 0
                    for j in range(len(df)):
                        if abs(df['low'].iloc[j] - price) / price < threshold:
                            touches += 1
                    
                    strength = min(100, touches * 20)
                    
                    levels.append({
                        "price": price,
                        "type": "support",
                        "strength": strength
                    })
            
            return levels
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm mức hỗ trợ/kháng cự: {str(e)}")
            return []