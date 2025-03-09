#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module chọn chiến lược thích ứng (Adaptive Strategy Selector)

Module này tự động chọn chiến lược giao dịch phù hợp dựa trên chế độ thị trường,
đồng thời tối ưu hóa quá trình tính toán chỉ báo bằng cách sử dụng bộ nhớ cache.
"""

import os
import json
import time
import logging
import datetime
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Union
from data_cache import DataCache

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('adaptive_strategy_selector')

class AdaptiveStrategySelector:
    """Lớp chọn chiến lược thích ứng theo chế độ thị trường"""
    
    def __init__(self, data_cache: DataCache = None, config_path: str = 'configs/strategy_market_config.json'):
        """
        Khởi tạo bộ chọn chiến lược
        
        Args:
            data_cache (DataCache, optional): Cache dữ liệu
            config_path (str): Đường dẫn file cấu hình
        """
        self.data_cache = data_cache if data_cache else DataCache()
        self.config_path = config_path
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Chế độ thị trường hiện tại và lịch sử
        self.current_regime = 'unknown'
        self.regime_history = []
        
        # Chiến lược được chọn theo chế độ thị trường
        self.selected_strategies = {}
        
        # Chỉ số được tính toán
        self.calculated_indicators = {}
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình
        """
        default_config = {
            'market_regimes': {
                'trending': {
                    'description': 'Thị trường có xu hướng rõ ràng (lên hoặc xuống)',
                    'detection': {
                        'adx_min': 25,
                        'volatility_max': 0.03
                    },
                    'strategies': {
                        'trend_following': 0.7,
                        'momentum': 0.2,
                        'breakout': 0.1
                    },
                    'risk_adjustment': 1.0,
                    'position_sizing': 'normal'
                },
                'ranging': {
                    'description': 'Thị trường đi ngang trong biên độ nhất định',
                    'detection': {
                        'adx_max': 20,
                        'volatility_max': 0.02,
                        'bb_width_max': 0.05
                    },
                    'strategies': {
                        'mean_reversion': 0.6,
                        'range_trading': 0.3,
                        'support_resistance': 0.1
                    },
                    'risk_adjustment': 0.8,
                    'position_sizing': 'reduced'
                },
                'volatile': {
                    'description': 'Thị trường biến động mạnh, không có xu hướng rõ ràng',
                    'detection': {
                        'volatility_min': 0.03,
                        'bb_width_min': 0.05
                    },
                    'strategies': {
                        'breakout': 0.4,
                        'volatility_based': 0.4,
                        'momentum': 0.2
                    },
                    'risk_adjustment': 0.6,
                    'position_sizing': 'reduced'
                },
                'quiet': {
                    'description': 'Thị trường ít biến động, thanh khoản thấp',
                    'detection': {
                        'volatility_max': 0.01,
                        'adx_max': 15,
                        'volume_percentile_max': 30
                    },
                    'strategies': {
                        'idle': 0.7,
                        'range_trading': 0.2,
                        'mean_reversion': 0.1
                    },
                    'risk_adjustment': 0.5,
                    'position_sizing': 'minimal'
                }
            },
            'strategy_parameters': {
                'trend_following': {
                    'ema_fast': 20,
                    'ema_slow': 50,
                    'stop_loss_percent': 2.0,
                    'take_profit_percent': 4.0
                },
                'momentum': {
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30,
                    'stop_loss_percent': 2.5,
                    'take_profit_percent': 3.5
                },
                'breakout': {
                    'atr_period': 14,
                    'atr_multiplier': 3.0,
                    'stop_loss_atr_multiplier': 2.0,
                    'take_profit_atr_multiplier': 4.0
                },
                'mean_reversion': {
                    'bb_period': 20,
                    'bb_std_dev': 2.0,
                    'stop_loss_percent': 1.5,
                    'take_profit_percent': 2.0
                },
                'range_trading': {
                    'lookback_period': 20,
                    'range_percent': 80,
                    'stop_loss_percent': 1.0,
                    'take_profit_percent': 1.5
                },
                'support_resistance': {
                    'lookback_period': 50,
                    'min_touches': 2,
                    'price_buffer': 0.005,
                    'stop_loss_percent': 1.2,
                    'take_profit_percent': 1.8
                },
                'volatility_based': {
                    'atr_period': 14,
                    'bollinger_period': 20,
                    'bollinger_std_dev': 2.0,
                    'stop_loss_atr_multiplier': 1.5,
                    'take_profit_atr_multiplier': 3.0
                },
                'idle': {
                    'min_volatility': 0.02,
                    'min_volume': 1000000
                }
            },
            'indicator_cache_duration': {
                'trend': 3600,  # 1 hour
                'oscillator': 1800,  # 30 minutes
                'volatility': 3600,  # 1 hour
                'volume': 7200   # 2 hours
            }
        }
        
        # Kiểm tra file cấu hình tồn tại
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình từ {self.config_path}: {str(e)}")
        
        # Tạo file cấu hình mặc định nếu không tồn tại
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            logger.info(f"Đã tạo cấu hình mặc định tại {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo cấu hình mặc định: {str(e)}")
        
        return default_config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
            return False
    
    def get_market_regime(self, symbol: str, timeframe: str = '1h', force_recalculate: bool = False) -> str:
        """
        Xác định chế độ thị trường hiện tại
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            force_recalculate (bool): Có tính lại các chỉ báo không
            
        Returns:
            str: Chế độ thị trường ('trending', 'ranging', 'volatile', 'quiet')
        """
        # Kiểm tra cache
        cache_key = f"{symbol}_{timeframe}_market_regime"
        cached_regime = self.data_cache.get('market_analysis', cache_key)
        
        if cached_regime and not force_recalculate:
            cached_time = self.data_cache.get_timestamp('market_analysis', cache_key)
            if cached_time:
                # Kiểm tra thời gian cache, nếu mới hơn 15 phút thì sử dụng
                cache_age = time.time() - cached_time
                if cache_age < 900:  # 15 minutes
                    self.current_regime = cached_regime
                    return cached_regime
        
        # Tính toán các chỉ báo cần thiết
        indicators = self._calculate_regime_indicators(symbol, timeframe, force_recalculate)
        
        # Xác định chế độ thị trường dựa trên các chỉ báo
        regime = self._detect_market_regime(indicators)
        
        # Lưu vào cache
        self.data_cache.set('market_analysis', cache_key, regime)
        
        # Cập nhật lịch sử
        self.regime_history.append({
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'symbol': symbol,
            'timeframe': timeframe,
            'regime': regime,
            'indicators': indicators
        })
        
        # Giới hạn lịch sử
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]
        
        # Cập nhật chế độ hiện tại
        self.current_regime = regime
        
        return regime
    
    def _calculate_regime_indicators(self, symbol: str, timeframe: str, force_recalculate: bool = False) -> Dict:
        """
        Tính toán các chỉ báo cần thiết để xác định chế độ thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            force_recalculate (bool): Có tính lại các chỉ báo không
            
        Returns:
            Dict: Các chỉ báo đã tính
        """
        indicators = {}
        
        # Tính toán ADX (Average Directional Index) - chỉ báo xu hướng
        adx = self._get_cached_indicator(symbol, timeframe, 'adx', force_recalculate)
        indicators['adx'] = adx
        
        # Tính toán volatility (ATR/Price)
        volatility = self._get_cached_indicator(symbol, timeframe, 'volatility', force_recalculate)
        indicators['volatility'] = volatility
        
        # Tính toán Bollinger Bands width
        bb_width = self._get_cached_indicator(symbol, timeframe, 'bb_width', force_recalculate)
        indicators['bb_width'] = bb_width
        
        # Tính toán volume percentile
        volume_percentile = self._get_cached_indicator(symbol, timeframe, 'volume_percentile', force_recalculate)
        indicators['volume_percentile'] = volume_percentile
        
        # Tính toán RSI
        rsi = self._get_cached_indicator(symbol, timeframe, 'rsi', force_recalculate)
        indicators['rsi'] = rsi
        
        # Tính toán MACD
        macd = self._get_cached_indicator(symbol, timeframe, 'macd', force_recalculate)
        indicators['macd'] = macd
        
        # Lưu các chỉ báo đã tính
        self.calculated_indicators[f"{symbol}_{timeframe}"] = indicators
        
        return indicators
    
    def _get_cached_indicator(self, symbol: str, timeframe: str, indicator: str, force_recalculate: bool = False) -> float:
        """
        Lấy chỉ báo từ cache hoặc tính toán nếu cần
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            indicator (str): Tên chỉ báo
            force_recalculate (bool): Có tính lại không
            
        Returns:
            float: Giá trị chỉ báo
        """
        cache_key = f"{symbol}_{timeframe}_{indicator}"
        
        # Nếu không cần tính lại, kiểm tra cache
        if not force_recalculate:
            # Lấy từ cache
            cached_value = self.data_cache.get('indicators', cache_key)
            if cached_value is not None:
                # Kiểm tra thời gian cache
                cache_time = self.data_cache.get_timestamp('indicators', cache_key)
                if cache_time:
                    indicator_type = 'trend'
                    if indicator in ['rsi', 'stoch', 'cci']:
                        indicator_type = 'oscillator'
                    elif indicator in ['atr', 'volatility', 'bb_width']:
                        indicator_type = 'volatility'
                    elif indicator in ['volume', 'volume_percentile']:
                        indicator_type = 'volume'
                    
                    # Lấy thời gian hết hạn
                    expiry_time = self.config.get('indicator_cache_duration', {}).get(indicator_type, 3600)
                    
                    # Nếu chưa hết hạn, trả về giá trị cache
                    if time.time() - cache_time < expiry_time:
                        return cached_value
        
        # Tính toán chỉ báo
        value = None
        
        if indicator == 'adx':
            value = self._calculate_adx(symbol, timeframe)
        elif indicator == 'volatility':
            value = self._calculate_volatility(symbol, timeframe)
        elif indicator == 'bb_width':
            value = self._calculate_bb_width(symbol, timeframe)
        elif indicator == 'volume_percentile':
            value = self._calculate_volume_percentile(symbol, timeframe)
        elif indicator == 'rsi':
            value = self._calculate_rsi(symbol, timeframe)
        elif indicator == 'macd':
            value = self._calculate_macd(symbol, timeframe)
        
        # Lưu vào cache
        if value is not None:
            self.data_cache.set('indicators', cache_key, value)
        
        return value
    
    def _calculate_adx(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """
        Tính toán ADX (Average Directional Index)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            period (int): Số chu kỳ
            
        Returns:
            float: Giá trị ADX
        """
        # Thực tế, nên lấy dữ liệu từ cache hoặc tính toán chi tiết
        # Trong demo này, trả về giá trị giả lập
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < period:
                # Nếu không có dữ liệu, trả về giá trị ngẫu nhiên
                import random
                return random.uniform(10, 40)
            
            # Thực tế, nên tính toán ADX từ dữ liệu giá
            # Đây là tính toán giả lập dựa trên xu hướng dữ liệu
            closes = [float(candle[4]) for candle in price_data[-period-10:]]
            
            # Tính xu hướng đơn giản
            trend = 0
            for i in range(1, len(closes)):
                trend += 1 if closes[i] > closes[i-1] else -1
            
            # Tính ADX giả lập
            trend_strength = abs(trend) / len(closes)
            adx = trend_strength * 50  # Scale to 0-50
            
            return adx
        except Exception as e:
            logger.error(f"Lỗi khi tính ADX cho {symbol} {timeframe}: {str(e)}")
            return 20.0  # Giá trị mặc định
    
    def _calculate_volatility(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """
        Tính toán volatility (ATR/Price)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            period (int): Số chu kỳ
            
        Returns:
            float: Giá trị volatility
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < period:
                # Nếu không có dữ liệu, trả về giá trị ngẫu nhiên
                import random
                return random.uniform(0.01, 0.04)
            
            # Tính volatility
            close_prices = [float(candle[4]) for candle in price_data[-period:]]
            high_prices = [float(candle[2]) for candle in price_data[-period:]]
            low_prices = [float(candle[3]) for candle in price_data[-period:]]
            
            # Tính true range
            tr_values = []
            for i in range(1, len(close_prices)):
                tr1 = high_prices[i] - low_prices[i]
                tr2 = abs(high_prices[i] - close_prices[i-1])
                tr3 = abs(low_prices[i] - close_prices[i-1])
                tr_values.append(max(tr1, tr2, tr3))
            
            # Tính ATR
            atr = sum(tr_values) / len(tr_values) if tr_values else 0
            
            # Tính volatility (ATR/giá đóng cửa)
            volatility = atr / close_prices[-1] if close_prices[-1] > 0 else 0
            
            return volatility
        except Exception as e:
            logger.error(f"Lỗi khi tính volatility cho {symbol} {timeframe}: {str(e)}")
            return 0.02  # Giá trị mặc định
    
    def _calculate_bb_width(self, symbol: str, timeframe: str, period: int = 20, std_dev: float = 2.0) -> float:
        """
        Tính toán Bollinger Bands width
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            period (int): Số chu kỳ
            std_dev (float): Số lần độ lệch chuẩn
            
        Returns:
            float: Giá trị BB width
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < period:
                # Nếu không có dữ liệu, trả về giá trị ngẫu nhiên
                import random
                return random.uniform(0.02, 0.08)
            
            # Tính BB width
            close_prices = [float(candle[4]) for candle in price_data[-period:]]
            
            # Tính SMA
            sma = sum(close_prices) / len(close_prices)
            
            # Tính độ lệch chuẩn
            variance = sum((x - sma) ** 2 for x in close_prices) / len(close_prices)
            std = variance ** 0.5
            
            # Tính BB width
            upper_band = sma + std_dev * std
            lower_band = sma - std_dev * std
            
            bb_width = (upper_band - lower_band) / sma
            
            return bb_width
        except Exception as e:
            logger.error(f"Lỗi khi tính BB width cho {symbol} {timeframe}: {str(e)}")
            return 0.04  # Giá trị mặc định
    
    def _calculate_volume_percentile(self, symbol: str, timeframe: str, lookback: int = 30) -> float:
        """
        Tính toán volume percentile
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            lookback (int): Số chu kỳ nhìn lại
            
        Returns:
            float: Giá trị volume percentile (0-100)
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < lookback:
                # Nếu không có dữ liệu, trả về giá trị ngẫu nhiên
                import random
                return random.uniform(20, 80)
            
            # Lấy dữ liệu volume
            volumes = [float(candle[5]) for candle in price_data[-lookback-1:]]
            
            # Tính volume hiện tại
            current_volume = volumes[-1]
            
            # Tính percentile
            volumes_sorted = sorted(volumes[:-1])
            
            # Tìm vị trí của volume hiện tại
            position = 0
            for i, vol in enumerate(volumes_sorted):
                if current_volume > vol:
                    position = i + 1
            
            # Tính percentile
            percentile = (position / len(volumes_sorted)) * 100
            
            return percentile
        except Exception as e:
            logger.error(f"Lỗi khi tính volume percentile cho {symbol} {timeframe}: {str(e)}")
            return 50.0  # Giá trị mặc định
    
    def _calculate_rsi(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """
        Tính toán RSI (Relative Strength Index)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            period (int): Số chu kỳ
            
        Returns:
            float: Giá trị RSI
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < period + 1:
                # Nếu không có dữ liệu, trả về giá trị ngẫu nhiên
                import random
                return random.uniform(30, 70)
            
            # Tính RSI
            close_prices = [float(candle[4]) for candle in price_data[-(period+1):]]
            
            # Tính price changes
            price_changes = [close_prices[i] - close_prices[i-1] for i in range(1, len(close_prices))]
            
            # Tính gains và losses
            gains = [change if change > 0 else 0 for change in price_changes]
            losses = [abs(change) if change < 0 else 0 for change in price_changes]
            
            # Tính average gains và losses
            avg_gain = sum(gains) / len(gains)
            avg_loss = sum(losses) / len(losses)
            
            # Tính RS và RSI
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            return rsi
        except Exception as e:
            logger.error(f"Lỗi khi tính RSI cho {symbol} {timeframe}: {str(e)}")
            return 50.0  # Giá trị mặc định
    
    def _calculate_macd(self, symbol: str, timeframe: str, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict:
        """
        Tính toán MACD (Moving Average Convergence Divergence)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            fast_period (int): Số chu kỳ EMA nhanh
            slow_period (int): Số chu kỳ EMA chậm
            signal_period (int): Số chu kỳ EMA tín hiệu
            
        Returns:
            Dict: Giá trị MACD
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < slow_period + signal_period:
                # Nếu không có dữ liệu, trả về giá trị ngẫu nhiên
                import random
                return {
                    'macd': random.uniform(-20, 20),
                    'signal': random.uniform(-20, 20),
                    'histogram': random.uniform(-10, 10)
                }
            
            # Tính MACD
            close_prices = [float(candle[4]) for candle in price_data]
            
            # Tính EMA nhanh và chậm
            def calculate_ema(prices, period):
                multiplier = 2 / (period + 1)
                ema = [prices[0]]
                for i in range(1, len(prices)):
                    ema.append((prices[i] - ema[i-1]) * multiplier + ema[i-1])
                return ema
            
            # Tính EMA
            ema_fast = calculate_ema(close_prices, fast_period)[-1]
            ema_slow = calculate_ema(close_prices, slow_period)[-1]
            
            # Tính MACD Line
            macd_line = ema_fast - ema_slow
            
            # Tính Signal Line (giả lập)
            signal_line = macd_line * 0.9  # Giả lập
            
            # Tính Histogram
            histogram = macd_line - signal_line
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
        except Exception as e:
            logger.error(f"Lỗi khi tính MACD cho {symbol} {timeframe}: {str(e)}")
            return {
                'macd': 0.0,
                'signal': 0.0,
                'histogram': 0.0
            }  # Giá trị mặc định
    
    def _detect_market_regime(self, indicators: Dict) -> str:
        """
        Xác định chế độ thị trường dựa trên các chỉ báo
        
        Args:
            indicators (Dict): Các chỉ báo đã tính
            
        Returns:
            str: Chế độ thị trường ('trending', 'ranging', 'volatile', 'quiet')
        """
        # Lấy các ngưỡng từ cấu hình
        market_regimes = self.config.get('market_regimes', {})
        
        # Tính điểm cho từng chế độ
        regime_scores = {
            'trending': 0,
            'ranging': 0,
            'volatile': 0,
            'quiet': 0
        }
        
        # Kiểm tra điều kiện trending
        trending_conditions = market_regimes.get('trending', {}).get('detection', {})
        if indicators.get('adx', 0) >= trending_conditions.get('adx_min', 25) and \
           indicators.get('volatility', 0) <= trending_conditions.get('volatility_max', 0.03):
            regime_scores['trending'] += 1
        
        # Kiểm tra điều kiện ranging
        ranging_conditions = market_regimes.get('ranging', {}).get('detection', {})
        if indicators.get('adx', 0) <= ranging_conditions.get('adx_max', 20) and \
           indicators.get('volatility', 0) <= ranging_conditions.get('volatility_max', 0.02) and \
           indicators.get('bb_width', 0) <= ranging_conditions.get('bb_width_max', 0.05):
            regime_scores['ranging'] += 1
        
        # Kiểm tra điều kiện volatile
        volatile_conditions = market_regimes.get('volatile', {}).get('detection', {})
        if indicators.get('volatility', 0) >= volatile_conditions.get('volatility_min', 0.03) and \
           indicators.get('bb_width', 0) >= volatile_conditions.get('bb_width_min', 0.05):
            regime_scores['volatile'] += 1
        
        # Kiểm tra điều kiện quiet
        quiet_conditions = market_regimes.get('quiet', {}).get('detection', {})
        if indicators.get('volatility', 0) <= quiet_conditions.get('volatility_max', 0.01) and \
           indicators.get('adx', 0) <= quiet_conditions.get('adx_max', 15) and \
           indicators.get('volume_percentile', 0) <= quiet_conditions.get('volume_percentile_max', 30):
            regime_scores['quiet'] += 1
        
        # Chọn chế độ có điểm cao nhất
        max_score = 0
        selected_regime = 'ranging'  # Mặc định
        
        for regime, score in regime_scores.items():
            if score > max_score:
                max_score = score
                selected_regime = regime
        
        # Nếu không có chế độ nào phù hợp, xem xét theo MACD và RSI
        if max_score == 0:
            macd = indicators.get('macd', {})
            rsi = indicators.get('rsi', 50)
            
            if isinstance(macd, dict) and macd.get('histogram', 0) > 0 and rsi > 50:
                selected_regime = 'trending'  # Uptrend
            elif isinstance(macd, dict) and macd.get('histogram', 0) < 0 and rsi < 50:
                selected_regime = 'trending'  # Downtrend
            elif 40 <= rsi <= 60:
                selected_regime = 'ranging'
            elif indicators.get('volatility', 0) > 0.02:
                selected_regime = 'volatile'
            else:
                selected_regime = 'quiet'
        
        return selected_regime
    
    def get_strategies_for_regime(self, regime: str = None) -> Dict[str, float]:
        """
        Lấy danh sách chiến lược phù hợp với chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            Dict[str, float]: Ánh xạ tên chiến lược -> trọng số
        """
        if regime is None:
            regime = self.current_regime
        
        # Lấy danh sách chiến lược từ cấu hình
        market_regimes = self.config.get('market_regimes', {})
        regime_config = market_regimes.get(regime, {})
        
        strategies = regime_config.get('strategies', {})
        
        # Nếu không có chiến lược nào, trả về chiến lược mặc định
        if not strategies:
            return {
                'trend_following': 0.3,
                'momentum': 0.3,
                'mean_reversion': 0.2,
                'breakout': 0.2
            }
        
        return strategies
    
    def get_strategy_parameters(self, strategy_name: str, regime: str = None) -> Dict:
        """
        Lấy tham số cho chiến lược
        
        Args:
            strategy_name (str): Tên chiến lược
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            Dict: Tham số chiến lược
        """
        if regime is None:
            regime = self.current_regime
        
        # Lấy tham số từ cấu hình
        strategy_parameters = self.config.get('strategy_parameters', {})
        base_params = strategy_parameters.get(strategy_name, {})
        
        # Lấy tham số tùy chỉnh theo chế độ thị trường nếu có
        market_regimes = self.config.get('market_regimes', {})
        regime_config = market_regimes.get(regime, {})
        custom_params = regime_config.get('strategy_parameters', {}).get(strategy_name, {})
        
        # Kết hợp tham số
        result = base_params.copy()
        result.update(custom_params)
        
        return result
    
    def get_risk_adjustment(self, regime: str = None) -> float:
        """
        Lấy hệ số điều chỉnh rủi ro theo chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            float: Hệ số điều chỉnh rủi ro
        """
        if regime is None:
            regime = self.current_regime
        
        # Lấy hệ số từ cấu hình
        market_regimes = self.config.get('market_regimes', {})
        regime_config = market_regimes.get(regime, {})
        
        risk_adjustment = regime_config.get('risk_adjustment', 1.0)
        
        return risk_adjustment
    
    def get_position_sizing_method(self, regime: str = None) -> str:
        """
        Lấy phương pháp tính kích thước vị thế theo chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            str: Phương pháp tính kích thước vị thế
        """
        if regime is None:
            regime = self.current_regime
        
        # Lấy phương pháp từ cấu hình
        market_regimes = self.config.get('market_regimes', {})
        regime_config = market_regimes.get(regime, {})
        
        position_sizing = regime_config.get('position_sizing', 'normal')
        
        return position_sizing
    
    def get_trading_decision(self, symbol: str, timeframe: str, risk_percentage: float = 1.0) -> Dict:
        """
        Đưa ra quyết định giao dịch dựa trên chế độ thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            risk_percentage (float): Phần trăm rủi ro cơ sở
            
        Returns:
            Dict: Quyết định giao dịch
        """
        # Xác định chế độ thị trường
        regime = self.get_market_regime(symbol, timeframe)
        
        # Lấy danh sách chiến lược
        strategies = self.get_strategies_for_regime(regime)
        
        # Lấy hệ số điều chỉnh rủi ro
        risk_adjustment = self.get_risk_adjustment(regime)
        
        # Điều chỉnh risk_percentage
        adjusted_risk = risk_percentage * risk_adjustment
        
        # Lấy phương pháp tính kích thước vị thế
        position_sizing = self.get_position_sizing_method(regime)
        
        # Tạo quyết định giao dịch
        decision = {
            'symbol': symbol,
            'timeframe': timeframe,
            'market_regime': regime,
            'strategies': strategies,
            'risk_percentage': adjusted_risk,
            'position_sizing': position_sizing,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Tính tín hiệu từ các chiến lược
        signals = self._calculate_strategy_signals(symbol, timeframe, strategies)
        decision['signals'] = signals
        
        # Tính toán tín hiệu tổng hợp
        composite_signal = self._calculate_composite_signal(signals, strategies)
        decision['composite_signal'] = composite_signal
        
        # Tính toán stop loss và take profit
        stop_loss, take_profit = self._calculate_sl_tp(symbol, timeframe, composite_signal, regime)
        decision['stop_loss'] = stop_loss
        decision['take_profit'] = take_profit
        
        return decision
    
    def _calculate_strategy_signals(self, symbol: str, timeframe: str, strategies: Dict[str, float]) -> Dict[str, Dict]:
        """
        Tính toán tín hiệu từ các chiến lược
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            strategies (Dict[str, float]): Ánh xạ tên chiến lược -> trọng số
            
        Returns:
            Dict[str, Dict]: Tín hiệu từ các chiến lược
        """
        signals = {}
        
        # Lấy dữ liệu giá
        price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
        
        # Nếu không có dữ liệu, trả về tín hiệu trung tính
        if price_data is None or not isinstance(price_data, list) or len(price_data) < 50:
            return {strategy: {'signal': 'NEUTRAL', 'strength': 0} for strategy in strategies}
        
        # Lấy giá hiện tại
        current_price = float(price_data[-1][4]) if len(price_data) > 0 else 0
        
        # Tính toán tín hiệu cho từng chiến lược
        for strategy_name in strategies:
            signal = 'NEUTRAL'
            strength = 0
            
            # Lấy tham số chiến lược
            params = self.get_strategy_parameters(strategy_name)
            
            # Tính toán tín hiệu
            if strategy_name == 'trend_following':
                signal, strength = self._trend_following_signal(symbol, timeframe, params)
            elif strategy_name == 'momentum':
                signal, strength = self._momentum_signal(symbol, timeframe, params)
            elif strategy_name == 'breakout':
                signal, strength = self._breakout_signal(symbol, timeframe, params)
            elif strategy_name == 'mean_reversion':
                signal, strength = self._mean_reversion_signal(symbol, timeframe, params)
            elif strategy_name == 'range_trading':
                signal, strength = self._range_trading_signal(symbol, timeframe, params)
            elif strategy_name == 'support_resistance':
                signal, strength = self._support_resistance_signal(symbol, timeframe, params)
            elif strategy_name == 'volatility_based':
                signal, strength = self._volatility_based_signal(symbol, timeframe, params)
            else:
                # Chiến lược không hỗ trợ
                signal = 'NEUTRAL'
                strength = 0
            
            signals[strategy_name] = {
                'signal': signal,
                'strength': strength,
                'current_price': current_price
            }
        
        return signals
    
    def _trend_following_signal(self, symbol: str, timeframe: str, params: Dict) -> Tuple[str, float]:
        """
        Tính toán tín hiệu theo xu hướng
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            params (Dict): Tham số chiến lược
            
        Returns:
            Tuple[str, float]: (tín hiệu, độ mạnh)
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < 50:
                return 'NEUTRAL', 0
            
            # Lấy tham số
            ema_fast = params.get('ema_fast', 20)
            ema_slow = params.get('ema_slow', 50)
            
            # Lấy giá đóng cửa
            close_prices = [float(candle[4]) for candle in price_data]
            
            # Tính EMA nhanh và chậm
            def calculate_ema(prices, period):
                multiplier = 2 / (period + 1)
                ema = [prices[0]]
                for i in range(1, len(prices)):
                    ema.append((prices[i] - ema[i-1]) * multiplier + ema[i-1])
                return ema
            
            ema_fast_values = calculate_ema(close_prices, ema_fast)
            ema_slow_values = calculate_ema(close_prices, ema_slow)
            
            # Lấy các giá trị EMA hiện tại
            current_ema_fast = ema_fast_values[-1]
            current_ema_slow = ema_slow_values[-1]
            
            # Lấy giá trị EMA trước đó
            prev_ema_fast = ema_fast_values[-2] if len(ema_fast_values) > 1 else current_ema_fast
            prev_ema_slow = ema_slow_values[-2] if len(ema_slow_values) > 1 else current_ema_slow
            
            # Xác định tín hiệu
            if current_ema_fast > current_ema_slow:
                # Uptrend
                if prev_ema_fast <= prev_ema_slow:
                    # Crossover - tín hiệu mạnh
                    signal = 'BUY'
                    strength = 1.0
                else:
                    # Tiếp tục uptrend
                    signal = 'BUY'
                    strength = 0.7
            elif current_ema_fast < current_ema_slow:
                # Downtrend
                if prev_ema_fast >= prev_ema_slow:
                    # Crossover - tín hiệu mạnh
                    signal = 'SELL'
                    strength = 1.0
                else:
                    # Tiếp tục downtrend
                    signal = 'SELL'
                    strength = 0.7
            else:
                # Không có xu hướng rõ ràng
                signal = 'NEUTRAL'
                strength = 0.0
            
            return signal, strength
        except Exception as e:
            logger.error(f"Lỗi khi tính tín hiệu trend_following cho {symbol} {timeframe}: {str(e)}")
            return 'NEUTRAL', 0
    
    def _momentum_signal(self, symbol: str, timeframe: str, params: Dict) -> Tuple[str, float]:
        """
        Tính toán tín hiệu theo động lượng (momentum)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            params (Dict): Tham số chiến lược
            
        Returns:
            Tuple[str, float]: (tín hiệu, độ mạnh)
        """
        try:
            # Lấy dữ liệu RSI
            rsi = self._get_cached_indicator(symbol, timeframe, 'rsi')
            
            # Lấy tham số
            rsi_overbought = params.get('rsi_overbought', 70)
            rsi_oversold = params.get('rsi_oversold', 30)
            
            # Xác định tín hiệu
            if rsi >= rsi_overbought:
                signal = 'SELL'
                strength = min(1.0, (rsi - rsi_overbought) / 10)  # Càng vượt ngưỡng nhiều, tín hiệu càng mạnh
            elif rsi <= rsi_oversold:
                signal = 'BUY'
                strength = min(1.0, (rsi_oversold - rsi) / 10)
            else:
                # Trong vùng trung tính
                if rsi > 50:
                    signal = 'BUY'
                    strength = (rsi - 50) / (rsi_overbought - 50) * 0.5
                elif rsi < 50:
                    signal = 'SELL'
                    strength = (50 - rsi) / (50 - rsi_oversold) * 0.5
                else:
                    signal = 'NEUTRAL'
                    strength = 0.0
            
            return signal, strength
        except Exception as e:
            logger.error(f"Lỗi khi tính tín hiệu momentum cho {symbol} {timeframe}: {str(e)}")
            return 'NEUTRAL', 0
    
    def _breakout_signal(self, symbol: str, timeframe: str, params: Dict) -> Tuple[str, float]:
        """
        Tính toán tín hiệu theo breakout
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            params (Dict): Tham số chiến lược
            
        Returns:
            Tuple[str, float]: (tín hiệu, độ mạnh)
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < 30:
                return 'NEUTRAL', 0
            
            # Lấy tham số
            atr_period = params.get('atr_period', 14)
            atr_multiplier = params.get('atr_multiplier', 3.0)
            
            # Lấy giá đóng cửa
            close_prices = [float(candle[4]) for candle in price_data]
            high_prices = [float(candle[2]) for candle in price_data]
            low_prices = [float(candle[3]) for candle in price_data]
            
            # Tính ATR
            atr = self._get_cached_indicator(symbol, timeframe, 'atr')
            
            # Tính resistance và support
            lookback = 20
            resistance = max(high_prices[-lookback:-1])
            support = min(low_prices[-lookback:-1])
            
            # Lấy giá hiện tại
            current_price = close_prices[-1]
            
            # Xác định tín hiệu
            if current_price > resistance:
                # Breakout lên
                breakout_strength = (current_price - resistance) / (atr * atr_multiplier)
                signal = 'BUY'
                strength = min(1.0, breakout_strength)
            elif current_price < support:
                # Breakout xuống
                breakout_strength = (support - current_price) / (atr * atr_multiplier)
                signal = 'SELL'
                strength = min(1.0, breakout_strength)
            else:
                # Chưa có breakout
                signal = 'NEUTRAL'
                strength = 0.0
            
            return signal, strength
        except Exception as e:
            logger.error(f"Lỗi khi tính tín hiệu breakout cho {symbol} {timeframe}: {str(e)}")
            return 'NEUTRAL', 0
    
    def _mean_reversion_signal(self, symbol: str, timeframe: str, params: Dict) -> Tuple[str, float]:
        """
        Tính toán tín hiệu theo quay về trung bình (mean reversion)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            params (Dict): Tham số chiến lược
            
        Returns:
            Tuple[str, float]: (tín hiệu, độ mạnh)
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < 30:
                return 'NEUTRAL', 0
            
            # Lấy tham số
            bb_period = params.get('bb_period', 20)
            bb_std_dev = params.get('bb_std_dev', 2.0)
            
            # Lấy giá đóng cửa
            close_prices = [float(candle[4]) for candle in price_data]
            
            # Tính SMA
            sma = sum(close_prices[-bb_period:]) / bb_period
            
            # Tính độ lệch chuẩn
            variance = sum((x - sma) ** 2 for x in close_prices[-bb_period:]) / bb_period
            std = variance ** 0.5
            
            # Tính Bollinger Bands
            upper_band = sma + bb_std_dev * std
            lower_band = sma - bb_std_dev * std
            
            # Lấy giá hiện tại
            current_price = close_prices[-1]
            
            # Tính khoảng cách tới bands
            upper_distance = upper_band - current_price
            lower_distance = current_price - lower_band
            
            # Xác định tín hiệu
            if current_price > upper_band:
                # Giá vượt ngưỡng trên - tín hiệu bán
                signal = 'SELL'
                strength = min(1.0, (current_price - upper_band) / std)
            elif current_price < lower_band:
                # Giá vượt ngưỡng dưới - tín hiệu mua
                signal = 'BUY'
                strength = min(1.0, (lower_band - current_price) / std)
            else:
                # Giá trong dải - tín hiệu trung tính
                middle_band = (upper_band + lower_band) / 2
                if current_price > middle_band:
                    # Phần trên dải - tín hiệu bán yếu
                    signal = 'SELL'
                    strength = (current_price - middle_band) / (upper_band - middle_band) * 0.5
                elif current_price < middle_band:
                    # Phần dưới dải - tín hiệu mua yếu
                    signal = 'BUY'
                    strength = (middle_band - current_price) / (middle_band - lower_band) * 0.5
                else:
                    signal = 'NEUTRAL'
                    strength = 0.0
            
            return signal, strength
        except Exception as e:
            logger.error(f"Lỗi khi tính tín hiệu mean_reversion cho {symbol} {timeframe}: {str(e)}")
            return 'NEUTRAL', 0
    
    def _range_trading_signal(self, symbol: str, timeframe: str, params: Dict) -> Tuple[str, float]:
        """
        Tính toán tín hiệu theo giao dịch trong range
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            params (Dict): Tham số chiến lược
            
        Returns:
            Tuple[str, float]: (tín hiệu, độ mạnh)
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < 30:
                return 'NEUTRAL', 0
            
            # Lấy tham số
            lookback_period = params.get('lookback_period', 20)
            range_percent = params.get('range_percent', 80)
            
            # Lấy giá đóng cửa
            close_prices = [float(candle[4]) for candle in price_data]
            high_prices = [float(candle[2]) for candle in price_data]
            low_prices = [float(candle[3]) for candle in price_data]
            
            # Tính range
            high = max(high_prices[-lookback_period:])
            low = min(low_prices[-lookback_period:])
            
            # Lấy giá hiện tại
            current_price = close_prices[-1]
            
            # Tính vị trí tương đối trong range
            range_size = high - low
            if range_size == 0:
                return 'NEUTRAL', 0
            
            relative_position = (current_price - low) / range_size * 100
            
            # Xác định tín hiệu
            if relative_position >= range_percent:
                # Gần mức cao - tín hiệu bán
                signal = 'SELL'
                strength = min(1.0, (relative_position - range_percent) / (100 - range_percent))
            elif relative_position <= 100 - range_percent:
                # Gần mức thấp - tín hiệu mua
                signal = 'BUY'
                strength = min(1.0, (100 - range_percent - relative_position) / (100 - range_percent))
            else:
                # Trong khoảng giữa - tín hiệu trung tính
                signal = 'NEUTRAL'
                strength = 0.0
            
            return signal, strength
        except Exception as e:
            logger.error(f"Lỗi khi tính tín hiệu range_trading cho {symbol} {timeframe}: {str(e)}")
            return 'NEUTRAL', 0
    
    def _support_resistance_signal(self, symbol: str, timeframe: str, params: Dict) -> Tuple[str, float]:
        """
        Tính toán tín hiệu theo hỗ trợ/kháng cự (support/resistance)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            params (Dict): Tham số chiến lược
            
        Returns:
            Tuple[str, float]: (tín hiệu, độ mạnh)
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < 50:
                return 'NEUTRAL', 0
            
            # Lấy tham số
            lookback_period = params.get('lookback_period', 50)
            min_touches = params.get('min_touches', 2)
            price_buffer = params.get('price_buffer', 0.005)
            
            # Lấy giá đóng cửa
            close_prices = [float(candle[4]) for candle in price_data]
            high_prices = [float(candle[2]) for candle in price_data]
            low_prices = [float(candle[3]) for candle in price_data]
            
            # Lấy giá hiện tại
            current_price = close_prices[-1]
            
            # Tìm các mức hỗ trợ/kháng cự (đơn giản hóa)
            supports = []
            resistances = []
            
            # Phát hiện đỉnh và đáy cục bộ
            for i in range(2, min(lookback_period, len(price_data) - 2)):
                if high_prices[-i] > high_prices[-i-1] and high_prices[-i] > high_prices[-i-2] and \
                   high_prices[-i] > high_prices[-i+1] and high_prices[-i] > high_prices[-i+2]:
                    # Đỉnh cục bộ
                    resistances.append(high_prices[-i])
                
                if low_prices[-i] < low_prices[-i-1] and low_prices[-i] < low_prices[-i-2] and \
                   low_prices[-i] < low_prices[-i+1] and low_prices[-i] < low_prices[-i+2]:
                    # Đáy cục bộ
                    supports.append(low_prices[-i])
            
            # Nhóm các mức hỗ trợ/kháng cự gần nhau
            if supports or resistances:
                # Nhóm các mức hỗ trợ gần nhau
                grouped_supports = []
                for s in sorted(supports):
                    found_group = False
                    for i, group in enumerate(grouped_supports):
                        if abs(s - group) / group < price_buffer:
                            # Gộp vào nhóm
                            grouped_supports[i] = (group + s) / 2
                            found_group = True
                            break
                    if not found_group:
                        grouped_supports.append(s)
                
                # Nhóm các mức kháng cự gần nhau
                grouped_resistances = []
                for r in sorted(resistances):
                    found_group = False
                    for i, group in enumerate(grouped_resistances):
                        if abs(r - group) / group < price_buffer:
                            # Gộp vào nhóm
                            grouped_resistances[i] = (group + r) / 2
                            found_group = True
                            break
                    if not found_group:
                        grouped_resistances.append(r)
                
                # Tìm mức hỗ trợ/kháng cự gần nhất
                closest_support = None
                closest_resistance = None
                
                for s in grouped_supports:
                    if s < current_price and (closest_support is None or s > closest_support):
                        closest_support = s
                
                for r in grouped_resistances:
                    if r > current_price and (closest_resistance is None or r < closest_resistance):
                        closest_resistance = r
                
                # Tính khoảng cách tới mức hỗ trợ/kháng cự gần nhất
                support_distance = (current_price - closest_support) / current_price if closest_support else float('inf')
                resistance_distance = (closest_resistance - current_price) / current_price if closest_resistance else float('inf')
                
                # Xác định tín hiệu
                if support_distance < resistance_distance and support_distance < 0.01:
                    # Gần mức hỗ trợ - tín hiệu mua
                    signal = 'BUY'
                    strength = min(1.0, 1 - support_distance / 0.01)
                elif resistance_distance < support_distance and resistance_distance < 0.01:
                    # Gần mức kháng cự - tín hiệu bán
                    signal = 'SELL'
                    strength = min(1.0, 1 - resistance_distance / 0.01)
                else:
                    # Không gần mức hỗ trợ/kháng cự nào
                    signal = 'NEUTRAL'
                    strength = 0.0
            else:
                # Không tìm thấy mức hỗ trợ/kháng cự
                signal = 'NEUTRAL'
                strength = 0.0
            
            return signal, strength
        except Exception as e:
            logger.error(f"Lỗi khi tính tín hiệu support_resistance cho {symbol} {timeframe}: {str(e)}")
            return 'NEUTRAL', 0
    
    def _volatility_based_signal(self, symbol: str, timeframe: str, params: Dict) -> Tuple[str, float]:
        """
        Tính toán tín hiệu dựa trên biến động (volatility)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            params (Dict): Tham số chiến lược
            
        Returns:
            Tuple[str, float]: (tín hiệu, độ mạnh)
        """
        try:
            # Lấy dữ liệu giá
            price_data = self.data_cache.get('market_data', f"{symbol}_{timeframe}_data")
            
            if price_data is None or not isinstance(price_data, list) or len(price_data) < 30:
                return 'NEUTRAL', 0
            
            # Lấy tham số
            atr_period = params.get('atr_period', 14)
            bollinger_period = params.get('bollinger_period', 20)
            bollinger_std_dev = params.get('bollinger_std_dev', 2.0)
            
            # Lấy giá đóng cửa
            close_prices = [float(candle[4]) for candle in price_data]
            
            # Lấy ATR và BB width
            atr = self._get_cached_indicator(symbol, timeframe, 'atr')
            bb_width = self._get_cached_indicator(symbol, timeframe, 'bb_width')
            
            # Lấy tín hiệu từ RSI và MACD
            rsi = self._get_cached_indicator(symbol, timeframe, 'rsi')
            macd = self._get_cached_indicator(symbol, timeframe, 'macd')
            
            # Lấy giá hiện tại
            current_price = close_prices[-1]
            
            # Xác định tín hiệu
            if bb_width > 0.05:  # Biến động cao
                if isinstance(macd, dict) and macd.get('histogram', 0) > 0 and rsi > 50:
                    # Xu hướng tăng mạnh
                    signal = 'BUY'
                    strength = min(1.0, bb_width / 0.1)
                elif isinstance(macd, dict) and macd.get('histogram', 0) < 0 and rsi < 50:
                    # Xu hướng giảm mạnh
                    signal = 'SELL'
                    strength = min(1.0, bb_width / 0.1)
                else:
                    # Chưa có xu hướng rõ ràng
                    signal = 'NEUTRAL'
                    strength = 0.0
            else:  # Biến động thấp - chuẩn bị breakout
                if rsi > 60 and rsi < 70:
                    # Tích lũy hướng lên
                    signal = 'BUY'
                    strength = 0.5
                elif rsi < 40 and rsi > 30:
                    # Tích lũy hướng xuống
                    signal = 'SELL'
                    strength = 0.5
                else:
                    # Chưa có tín hiệu
                    signal = 'NEUTRAL'
                    strength = 0.0
            
            return signal, strength
        except Exception as e:
            logger.error(f"Lỗi khi tính tín hiệu volatility_based cho {symbol} {timeframe}: {str(e)}")
            return 'NEUTRAL', 0
    
    def _calculate_composite_signal(self, signals: Dict[str, Dict], strategy_weights: Dict[str, float]) -> Dict:
        """
        Tính toán tín hiệu tổng hợp từ các chiến lược
        
        Args:
            signals (Dict[str, Dict]): Tín hiệu từ các chiến lược
            strategy_weights (Dict[str, float]): Trọng số các chiến lược
            
        Returns:
            Dict: Tín hiệu tổng hợp
        """
        # Tính tổng trọng số
        total_weight = sum(strategy_weights.values())
        if total_weight == 0:
            total_weight = 1.0
        
        # Chuẩn hóa trọng số
        normalized_weights = {k: v / total_weight for k, v in strategy_weights.items()}
        
        # Tính điểm tổng hợp
        buy_score = 0.0
        sell_score = 0.0
        
        for strategy, signal_info in signals.items():
            weight = normalized_weights.get(strategy, 0.0)
            signal = signal_info.get('signal', 'NEUTRAL')
            strength = signal_info.get('strength', 0.0)
            
            if signal == 'BUY':
                buy_score += weight * strength
            elif signal == 'SELL':
                sell_score += weight * strength
        
        # Xác định tín hiệu tổng hợp
        if buy_score > sell_score:
            signal = 'BUY'
            strength = buy_score
        elif sell_score > buy_score:
            signal = 'SELL'
            strength = sell_score
        else:
            signal = 'NEUTRAL'
            strength = 0.0
        
        # Lấy giá hiện tại
        current_price = next(iter(signals.values())).get('current_price', 0) if signals else 0
        
        return {
            'signal': signal,
            'strength': strength,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'current_price': current_price
        }
    
    def _calculate_sl_tp(self, symbol: str, timeframe: str, signal: Dict, regime: str) -> Tuple[float, float]:
        """
        Tính toán stop loss và take profit
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            signal (Dict): Tín hiệu giao dịch
            regime (str): Chế độ thị trường
            
        Returns:
            Tuple[float, float]: (stop loss, take profit)
        """
        # Lấy thông tin từ tín hiệu
        signal_type = signal.get('signal', 'NEUTRAL')
        current_price = signal.get('current_price', 0)
        
        if signal_type == 'NEUTRAL' or current_price == 0:
            return None, None
        
        # Lấy ATR
        atr = self._get_cached_indicator(symbol, timeframe, 'atr')
        if atr is None or atr == 0:
            atr = current_price * 0.01  # Mặc định 1% giá hiện tại
        
        # Điều chỉnh theo chế độ thị trường
        market_regimes = self.config.get('market_regimes', {})
        regime_config = market_regimes.get(regime, {})
        
        # Lấy hệ số điều chỉnh rủi ro
        risk_adjustment = regime_config.get('risk_adjustment', 1.0)
        
        # Mặc định
        sl_percent = 2.0
        tp_percent = 3.0
        
        # Tính SL/TP dựa trên chế độ thị trường
        if regime == 'trending':
            # Xu hướng - SL rộng hơn, TP xa hơn
            sl_atr_multiplier = 3.0
            tp_atr_multiplier = 6.0
        elif regime == 'ranging':
            # Dao động - SL và TP gần hơn
            sl_atr_multiplier = 2.0
            tp_atr_multiplier = 3.0
        elif regime == 'volatile':
            # Biến động mạnh - SL rộng hơn
            sl_atr_multiplier = 4.0
            tp_atr_multiplier = 6.0
        elif regime == 'quiet':
            # Ít biến động - SL và TP gần hơn
            sl_atr_multiplier = 1.5
            tp_atr_multiplier = 2.5
        else:
            # Mặc định
            sl_atr_multiplier = 2.5
            tp_atr_multiplier = 4.0
        
        # Điều chỉnh theo risk_adjustment
        sl_atr_multiplier *= risk_adjustment
        tp_atr_multiplier *= risk_adjustment
        
        # Tính SL/TP
        if signal_type == 'BUY':
            stop_loss = current_price - atr * sl_atr_multiplier
            take_profit = current_price + atr * tp_atr_multiplier
        else:  # SELL
            stop_loss = current_price + atr * sl_atr_multiplier
            take_profit = current_price - atr * tp_atr_multiplier
        
        return stop_loss, take_profit
    
    def update_config_for_regime(self, regime: str, strategies: Dict[str, float], risk_adjustment: float = None, 
                             position_sizing: str = None) -> bool:
        """
        Cập nhật cấu hình cho một chế độ thị trường
        
        Args:
            regime (str): Chế độ thị trường
            strategies (Dict[str, float]): Ánh xạ tên chiến lược -> trọng số
            risk_adjustment (float, optional): Hệ số điều chỉnh rủi ro
            position_sizing (str, optional): Phương pháp tính kích thước vị thế
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            # Kiểm tra chế độ tồn tại
            if regime not in self.config.get('market_regimes', {}):
                logger.error(f"Chế độ thị trường không tồn tại: {regime}")
                return False
            
            # Cập nhật chiến lược
            if strategies:
                self.config['market_regimes'][regime]['strategies'] = strategies
            
            # Cập nhật hệ số điều chỉnh rủi ro
            if risk_adjustment is not None:
                self.config['market_regimes'][regime]['risk_adjustment'] = risk_adjustment
            
            # Cập nhật phương pháp tính kích thước vị thế
            if position_sizing:
                self.config['market_regimes'][regime]['position_sizing'] = position_sizing
            
            # Lưu cấu hình
            return self.save_config()
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cấu hình cho chế độ {regime}: {str(e)}")
            return False


def main():
    """Hàm chính để test AdaptiveStrategySelector"""
    
    print("=== Testing AdaptiveStrategySelector ===\n")
    
    # Khởi tạo DataCache và AdaptiveStrategySelector
    data_cache = DataCache()
    selector = AdaptiveStrategySelector(data_cache)
    
    # Lưu dữ liệu giá giả lập vào cache
    symbol = "BTCUSDT"
    timeframe = "1h"
    
    # Tạo dữ liệu giá ngẫu nhiên
    import random
    from datetime import datetime, timedelta
    
    price = 60000
    time_start = datetime.now() - timedelta(days=10)
    
    price_data = []
    for i in range(200):
        candle_time = time_start + timedelta(hours=i)
        candle_time_ms = int(candle_time.timestamp() * 1000)
        
        # Tạo biến động giá ngẫu nhiên
        price_change = random.normalvariate(0, 1) * price * 0.01  # ~1% biến động
        price += price_change
        
        # Tạo giá cao, thấp ngẫu nhiên
        high = price + abs(random.normalvariate(0, 1)) * price * 0.005
        low = price - abs(random.normalvariate(0, 1)) * price * 0.005
        
        # Tạo volume ngẫu nhiên
        volume = random.normalvariate(1000, 200)
        
        # Thêm vào dữ liệu
        candle = [
            candle_time_ms,  # Thời gian mở
            str(price - price_change),  # Giá mở
            str(high),  # Giá cao
            str(low),  # Giá thấp
            str(price),  # Giá đóng
            str(volume),  # Volume
            candle_time_ms + 3600000,  # Thời gian đóng
            str(volume * price),  # Quote volume
            100,  # Số giao dịch
            str(volume * 0.6),  # Taker buy base volume
            str(volume * 0.6 * price),  # Taker buy quote volume
            "0"  # Ignore
        ]
        
        price_data.append(candle)
    
    # Lưu vào cache
    data_cache.set('market_data', f"{symbol}_{timeframe}_data", price_data)
    
    # Test xác định chế độ thị trường
    print("Xác định chế độ thị trường:")
    regime = selector.get_market_regime(symbol, timeframe)
    print(f"Chế độ thị trường của {symbol} {timeframe}: {regime}")
    
    # Test lấy chiến lược theo chế độ thị trường
    print("\nCác chiến lược phù hợp với chế độ thị trường:")
    strategies = selector.get_strategies_for_regime(regime)
    for strategy, weight in strategies.items():
        print(f"- {strategy}: {weight:.2f}")
    
    # Test lấy tham số chiến lược
    print("\nTham số cho chiến lược trend_following:")
    params = selector.get_strategy_parameters('trend_following', regime)
    for key, value in params.items():
        print(f"- {key}: {value}")
    
    # Test lấy hệ số điều chỉnh rủi ro
    print("\nHệ số điều chỉnh rủi ro:")
    risk_adjustment = selector.get_risk_adjustment(regime)
    print(f"- Risk adjustment cho {regime}: {risk_adjustment:.2f}")
    
    # Test lấy quyết định giao dịch
    print("\nQuyết định giao dịch:")
    decision = selector.get_trading_decision(symbol, timeframe, risk_percentage=1.0)
    print(f"- Chế độ thị trường: {decision['market_regime']}")
    print(f"- Tín hiệu tổng hợp: {decision['composite_signal']['signal']} "
          f"(mạnh: {decision['composite_signal']['strength']:.2f})")
    print(f"- Risk %: {decision['risk_percentage']:.2f}%")
    print(f"- Stop loss: {decision['stop_loss']:.2f}")
    print(f"- Take profit: {decision['take_profit']:.2f}")
    
    # Test các tín hiệu chiến lược riêng biệt
    print("\nTín hiệu từ các chiến lược:")
    for strategy, signal in decision['signals'].items():
        print(f"- {strategy}: {signal['signal']} (mạnh: {signal['strength']:.2f})")


if __name__ == "__main__":
    main()