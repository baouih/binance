#!/usr/bin/env python3
"""
Module phát hiện chế độ thị trường (Market Regime Detector)

Module này cung cấp công cụ phát hiện chế độ thị trường (trending, ranging, volatile)
dựa trên các chỉ số kỹ thuật và học máy để điều chỉnh chiến thuật giao dịch cho phù hợp.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_regime_detector")

class MarketRegimeDetector:
    """Lớp phát hiện chế độ thị trường và chuyển đổi chiến lược phù hợp"""
    
    def __init__(self):
        """Khởi tạo bộ phát hiện chế độ thị trường"""
        self.regimes = {
            'trending_up': 'Thị trường xu hướng tăng - dễ dàng xác định chiều hướng, thích hợp cho chiến lược theo xu hướng',
            'trending_down': 'Thị trường xu hướng giảm - dễ dàng xác định chiều hướng, thích hợp cho chiến lược theo xu hướng',
            'ranging': 'Thị trường dao động trong biên độ hẹp - khó xác định xu hướng rõ ràng, thích hợp cho chiến lược tích lũy/phân phối',
            'volatile': 'Thị trường biến động mạnh - biến động cao và không ổn định, nên thận trọng và sử dụng chiến lược quản lý rủi ro chặt chẽ'
        }
        
        self.current_regime = None
        self.regime_history = []
        self.last_update = datetime.now()
        
        logger.info("Khởi tạo MarketRegimeDetector")
    
    def detect_regime(self, df: pd.DataFrame, window: int = 20) -> str:
        """
        Phát hiện chế độ thị trường hiện tại
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            window (int): Kích thước cửa sổ để phân tích
            
        Returns:
            str: Chế độ thị trường hiện tại ('trending_up', 'trending_down', 'ranging', 'volatile')
        """
        try:
            # Đảm bảo có đủ dữ liệu
            if len(df) < window:
                logger.warning(f"Không đủ dữ liệu cho phát hiện chế độ thị trường (cần {window}, có {len(df)})")
                return "unknown"
            
            # Lấy dữ liệu trong cửa sổ
            df_window = df.tail(window).copy()
            
            # Tính các chỉ báo nếu chưa có
            if 'atr' not in df_window.columns:
                df_window['atr'] = self._calculate_atr(df_window)
            
            if 'adx' not in df_window.columns:
                df_window['adx'] = self._calculate_adx(df_window)
            
            # Tính thêm các chỉ số
            close_prices = df_window['close'].values
            
            # 1. Tính biến động (volatility)
            volatility = self._calculate_volatility(df_window)
            
            # 2. Tính sức mạnh xu hướng
            trend_strength = self._calculate_trend_strength(df_window)
            
            # 3. Tính hướng xu hướng (tăng hay giảm)
            trend_direction = self._calculate_trend_direction(df_window)
            
            # 4. Tính đặc điểm dao động (ranging)
            range_characteristic = self._calculate_range_characteristic(df_window)
            
            # Phân loại chế độ thị trường
            if volatility > 2.0:
                # Thị trường biến động cao
                regime = "volatile"
            elif trend_strength > 0.7:
                # Thị trường có xu hướng mạnh
                if trend_direction > 0:
                    regime = "trending_up"
                else:
                    regime = "trending_down"
            elif range_characteristic > 0.7:
                # Thị trường dao động trong biên độ
                regime = "ranging"
            else:
                # Thị trường không rõ ràng, coi như dao động
                regime = "ranging"
            
            # Lưu chế độ thị trường hiện tại
            self.current_regime = regime
            self.regime_history.append({
                'timestamp': datetime.now(),
                'regime': regime,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'trend_direction': trend_direction,
                'range_characteristic': range_characteristic
            })
            
            # Giới hạn lịch sử
            if len(self.regime_history) > 100:
                self.regime_history.pop(0)
            
            self.last_update = datetime.now()
            
            logger.info(f"Phát hiện chế độ thị trường: {regime} (volatility={volatility:.2f}, trend_strength={trend_strength:.2f})")
            
            return regime
            
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường: {e}")
            return "unknown"
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Tính Average True Range (ATR)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            period (int): Chu kỳ ATR
            
        Returns:
            pd.Series: ATR
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Tính True Range
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Tính ATR
        atr = tr.rolling(period).mean()
        
        return atr
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Tính Average Directional Index (ADX)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            period (int): Chu kỳ ADX
            
        Returns:
            pd.Series: ADX
        """
        # Đơn giản hóa bằng cách sử dụng chiều dài của các xu hướng
        close = df['close'].values
        up_trend = 0
        down_trend = 0
        
        for i in range(1, len(close)):
            if close[i] > close[i-1]:
                up_trend += 1
                down_trend = 0
            elif close[i] < close[i-1]:
                down_trend += 1
                up_trend = 0
        
        # Tính ADX giả đơn giản (0-100)
        max_trend = max(up_trend, down_trend)
        return pd.Series(min(max_trend * 5, 100), index=df.index)
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """
        Tính mức độ biến động của thị trường
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            
        Returns:
            float: Mức độ biến động (0-infinity)
        """
        # Sử dụng ATR/Giá * 100 để tính biến động
        if 'atr' in df.columns:
            atr = df['atr'].iloc[-1]
        else:
            atr = self._calculate_atr(df).iloc[-1]
        
        price = df['close'].iloc[-1]
        volatility = (atr / price) * 100
        
        # Tính thêm độ lệch chuẩn của phần trăm thay đổi
        pct_change = df['close'].pct_change().dropna()
        std_dev = pct_change.std() * 100
        
        # Kết hợp cả hai chỉ số
        return (volatility + std_dev) / 2
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """
        Tính sức mạnh xu hướng của thị trường
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            
        Returns:
            float: Sức mạnh xu hướng (0-1)
        """
        # Kiểm tra ADX
        if 'adx' in df.columns:
            adx = df['adx'].iloc[-1]
        else:
            adx = self._calculate_adx(df).iloc[-1]
        
        # Chuẩn hóa ADX về 0-1
        adx_normalized = min(adx / 100, 1)
        
        # Tính thêm độ dốc của đường EMA
        if 'ema21' in df.columns:
            ema = df['ema21'].values
        else:
            ema = df['close'].ewm(span=21).mean().values
        
        ema_slope = (ema[-1] - ema[0]) / ema[0]
        ema_slope_normalized = min(abs(ema_slope) * 10, 1)
        
        # Kết hợp cả hai chỉ số
        return (adx_normalized * 0.7) + (ema_slope_normalized * 0.3)
    
    def _calculate_trend_direction(self, df: pd.DataFrame) -> float:
        """
        Tính hướng xu hướng của thị trường
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            
        Returns:
            float: Hướng xu hướng (-1 đến 1)
        """
        # Sử dụng EMA để xác định xu hướng
        if 'ema21' in df.columns:
            ema = df['ema21'].values
        else:
            ema = df['close'].ewm(span=21).mean().values
        
        # Tính độ dốc của EMA
        ema_slope = (ema[-1] - ema[0]) / ema[0]
        
        # Chuẩn hóa về -1 đến 1
        return max(min(ema_slope * 10, 1), -1)
    
    def _calculate_range_characteristic(self, df: pd.DataFrame) -> float:
        """
        Tính đặc tính dao động của thị trường
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            
        Returns:
            float: Đặc tính dao động (0-1)
        """
        # Tính % biến động giá trong khoảng
        price_min = df['low'].min()
        price_max = df['high'].max()
        price_range = (price_max - price_min) / price_min
        
        # Tính số lần đổi chiều
        prices = df['close'].values
        direction_changes = 0
        
        for i in range(2, len(prices)):
            prev_direction = prices[i-1] - prices[i-2]
            curr_direction = prices[i] - prices[i-1]
            
            if (prev_direction > 0 and curr_direction < 0) or (prev_direction < 0 and curr_direction > 0):
                direction_changes += 1
        
        # Chuẩn hóa số lần đổi chiều
        max_changes = len(prices) - 2
        change_ratio = direction_changes / max_changes if max_changes > 0 else 0
        
        # Kết hợp các chỉ số: nhiều lần đổi chiều + biên độ dao động nhỏ = thị trường dao động
        if price_range < 0.05:  # Biên độ nhỏ hơn 5%
            range_score = (change_ratio * 0.7) + 0.3
        else:
            range_score = change_ratio * (0.1 / price_range) * 1.5
            
        return min(range_score, 1.0)
    
    def get_regime_description(self, regime: str = None) -> str:
        """
        Trả về mô tả về chế độ thị trường hiện tại
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            str: Mô tả về chế độ thị trường
        """
        if regime is None:
            regime = self.current_regime or "unknown"
        
        return self.regimes.get(regime, "Không xác định")
    
    def get_suitable_strategies(self, regime: str = None) -> Dict[str, float]:
        """
        Trả về các chiến lược phù hợp với chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            Dict[str, float]: Ánh xạ chiến lược -> trọng số
        """
        if regime is None:
            regime = self.current_regime or "ranging"
        
        strategies = {
            'trending_up': {
                'ema_cross_strategy': 0.4,
                'macd_strategy': 0.3,
                'breakout_strategy': 0.2,
                'ml_strategy': 0.1
            },
            'trending_down': {
                'ema_cross_strategy': 0.4,
                'macd_strategy': 0.3,
                'breakout_strategy': 0.2,
                'ml_strategy': 0.1
            },
            'ranging': {
                'rsi_strategy': 0.4,
                'bollinger_strategy': 0.4,
                'support_resistance_strategy': 0.1,
                'ml_strategy': 0.1
            },
            'volatile': {
                'bollinger_strategy': 0.4,
                'rsi_strategy': 0.3,
                'ml_strategy': 0.2,
                'support_resistance_strategy': 0.1
            },
            'unknown': {
                'combined_strategy': 0.5,
                'rsi_strategy': 0.2,
                'bollinger_strategy': 0.2,
                'ema_cross_strategy': 0.1
            }
        }
        
        return strategies.get(regime, strategies['unknown'])
    
    def get_optimal_parameters(self, regime: str = None) -> Dict[str, Dict[str, Any]]:
        """
        Trả về tham số tối ưu cho từng chiến lược dựa trên chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            Dict[str, Dict[str, Any]]: Ánh xạ chiến lược -> tham số
        """
        if regime is None:
            regime = self.current_regime or "ranging"
        
        parameters = {
            'trending_up': {
                'rsi_strategy': {
                    'rsi_period': 14,
                    'rsi_overbought': 75,  # Tăng ngưỡng overbought trong xu hướng tăng
                    'rsi_oversold': 30,
                    'use_ema_confirmation': True
                },
                'macd_strategy': {
                    'fast_period': 12,
                    'slow_period': 26,
                    'signal_period': 9,
                    'use_histogram': True
                },
                'ema_cross_strategy': {
                    'fast_ema': 8,  # Giảm chu kỳ EMA ngắn để tăng độ nhạy
                    'slow_ema': 21
                }
            },
            'trending_down': {
                'rsi_strategy': {
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 25,  # Giảm ngưỡng oversold trong xu hướng giảm
                    'use_ema_confirmation': True
                },
                'macd_strategy': {
                    'fast_period': 12,
                    'slow_period': 26,
                    'signal_period': 9,
                    'use_histogram': True
                },
                'ema_cross_strategy': {
                    'fast_ema': 8,
                    'slow_ema': 21
                }
            },
            'ranging': {
                'rsi_strategy': {
                    'rsi_period': 13,  # Giảm chu kỳ RSI để tăng độ nhạy
                    'rsi_overbought': 65,  # Giảm ngưỡng overbought để bắt dao động
                    'rsi_oversold': 35,  # Tăng ngưỡng oversold để bắt dao động
                    'use_ema_confirmation': False
                },
                'bollinger_strategy': {
                    'bb_period': 20,
                    'bb_std': 2.0,
                    'use_bb_squeeze': True
                }
            },
            'volatile': {
                'rsi_strategy': {
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30,
                    'use_ema_confirmation': True
                },
                'bollinger_strategy': {
                    'bb_period': 20,
                    'bb_std': 2.5,  # Tăng độ lệch chuẩn để giảm tín hiệu sai
                    'use_bb_squeeze': True
                }
            },
            'unknown': {
                'rsi_strategy': {
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30,
                    'use_ema_confirmation': True
                },
                'bollinger_strategy': {
                    'bb_period': 20,
                    'bb_std': 2.0,
                    'use_bb_squeeze': True
                },
                'ema_cross_strategy': {
                    'fast_ema': 9,
                    'slow_ema': 21
                }
            }
        }
        
        return parameters.get(regime, parameters['unknown'])
    
    def get_regime_history(self, days: int = 7) -> List[Dict]:
        """
        Lấy lịch sử chế độ thị trường
        
        Args:
            days (int): Số ngày cần lấy lịch sử
            
        Returns:
            List[Dict]: Lịch sử chế độ thị trường
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        return [record for record in self.regime_history if record['timestamp'] > cutoff_time]

def main():
    """Hàm chính để test MarketRegimeDetector"""
    import yfinance as yf
    
    # Tải dữ liệu BTC
    symbol = "BTC-USD"
    data = yf.download(symbol, period="2mo", interval="1d")
    
    # Khởi tạo Market Regime Detector
    detector = MarketRegimeDetector()
    
    # Phát hiện chế độ thị trường
    regime = detector.detect_regime(data)
    
    print(f"Chế độ thị trường hiện tại: {regime}")
    print(f"Mô tả: {detector.get_regime_description(regime)}")
    
    print("\nCác chiến lược phù hợp:")
    for strategy, weight in detector.get_suitable_strategies(regime).items():
        print(f"- {strategy}: {weight:.2f}")
    
    print("\nTham số tối ưu cho các chiến lược:")
    for strategy, params in detector.get_optimal_parameters(regime).items():
        print(f"\n{strategy}:")
        for param, value in params.items():
            print(f"  - {param}: {value}")

if __name__ == "__main__":
    main()