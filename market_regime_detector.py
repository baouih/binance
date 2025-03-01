"""
Module phát hiện chế độ thị trường (Market Regime Detector)

Module này cung cấp các công cụ để phát hiện chế độ thị trường hiện tại (trending, ranging,
volatile, etc.) và đưa ra các chiến lược phù hợp với từng chế độ.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional, Union
import os
import json
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("market_regime_detector")

class MarketRegimeDetector:
    """Lớp phát hiện chế độ thị trường và chuyển đổi chiến lược phù hợp"""
    
    def __init__(self, data_folder: str = 'data', models_folder: str = 'models'):
        """
        Khởi tạo Market Regime Detector.
        
        Args:
            data_folder (str): Thư mục lưu dữ liệu
            models_folder (str): Thư mục lưu các mô hình ML
        """
        self.data_folder = data_folder
        self.models_folder = models_folder
        
        self.regime_history = []
        self.current_regime = None
        self.regime_probabilities = {}
        
        # Đảm bảo các thư mục tồn tại
        os.makedirs(data_folder, exist_ok=True)
        os.makedirs(models_folder, exist_ok=True)
        
        # Thông tin về các chế độ thị trường
        self.regimes = {
            'trending_up': {
                'description': 'Xu hướng tăng mạnh',
                'indicators': ['adx > 25', 'plus_di > minus_di', 'ema_50 > ema_200']
            },
            'trending_down': {
                'description': 'Xu hướng giảm mạnh',
                'indicators': ['adx > 25', 'plus_di < minus_di', 'ema_50 < ema_200']
            },
            'ranging': {
                'description': 'Thị trường dao động trong biên độ',
                'indicators': ['adx < 20', 'bb_width < bb_width_mean']
            },
            'volatile': {
                'description': 'Biến động cao',
                'indicators': ['atr > atr_mean * 1.5', 'bb_width > bb_width_mean * 1.5']
            },
            'quiet': {
                'description': 'Biến động thấp',
                'indicators': ['atr < atr_mean * 0.5', 'bb_width < bb_width_mean * 0.5']
            }
        }
        
        # Ánh xạ chiến lược theo chế độ
        self.strategy_mapping = {
            'trending_up': ['ema_cross', 'macd', 'adx_trend'],
            'trending_down': ['ema_cross', 'macd', 'adx_trend'],
            'ranging': ['rsi', 'bbands', 'stochastic'],
            'volatile': ['atr_breakout', 'volatility_expansion'],
            'quiet': ['channel_breakout', 'accumulation']
        }
        
        # Tham số tối ưu theo chế độ
        self.optimal_parameters = {}
        
        # Tải dữ liệu từ file nếu có
        self.load_regime_data()
        
    def detect_regime(self, df: pd.DataFrame, window: int = 20) -> str:
        """
        Phát hiện chế độ thị trường hiện tại
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            window (int): Kích thước cửa sổ để phân tích
            
        Returns:
            str: Chế độ thị trường hiện tại ('trending_up', 'trending_down', 'ranging', 'volatile', 'quiet')
        """
        try:
            # Đảm bảo DataFrame có đủ dữ liệu
            if len(df) < window:
                logger.warning(f"Không đủ dữ liệu để phát hiện chế độ thị trường (cần {window}, có {len(df)})")
                return "unknown"
            
            # Tính toán các chỉ báo nếu chưa có
            df_with_indicators = df.copy()
            
            # Tính toán các giá trị trung bình cần thiết
            if 'atr' in df_with_indicators.columns:
                df_with_indicators['atr_mean'] = df_with_indicators['atr'].rolling(window=window).mean()
            else:
                # Tính ATR nếu chưa có
                high_low = df_with_indicators['high'] - df_with_indicators['low']
                high_close = np.abs(df_with_indicators['high'] - df_with_indicators['close'].shift())
                low_close = np.abs(df_with_indicators['low'] - df_with_indicators['close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = np.max(ranges, axis=1)
                df_with_indicators['atr'] = true_range.rolling(window).mean()
                df_with_indicators['atr_mean'] = df_with_indicators['atr'].rolling(window=window).mean()
            
            if 'bb_width' in df_with_indicators.columns:
                df_with_indicators['bb_width_mean'] = df_with_indicators['bb_width'].rolling(window=window).mean()
            else:
                # Tính Bollinger Bands width nếu chưa có
                sma = df_with_indicators['close'].rolling(window=window).mean()
                rolling_std = df_with_indicators['close'].rolling(window=window).std()
                upper_band = sma + (rolling_std * 2)
                lower_band = sma - (rolling_std * 2)
                df_with_indicators['bb_width'] = (upper_band - lower_band) / sma
                df_with_indicators['bb_width_mean'] = df_with_indicators['bb_width'].rolling(window=window).mean()
            
            if 'adx' not in df_with_indicators.columns:
                # Tính ADX nếu chưa có
                plus_dm = df_with_indicators['high'].diff()
                minus_dm = df_with_indicators['low'].diff()
                plus_dm[plus_dm < 0] = 0
                minus_dm[minus_dm > 0] = 0
                
                tr1 = df_with_indicators['high'] - df_with_indicators['low']
                tr2 = np.abs(df_with_indicators['high'] - df_with_indicators['close'].shift(1))
                tr3 = np.abs(df_with_indicators['low'] - df_with_indicators['close'].shift(1))
                true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                
                plus_di = 100 * (plus_dm.ewm(alpha=1/window, adjust=False).mean() / 
                              true_range.ewm(alpha=1/window, adjust=False).mean())
                minus_di = abs(100 * (minus_dm.ewm(alpha=1/window, adjust=False).mean() / 
                              true_range.ewm(alpha=1/window, adjust=False).mean()))
                
                dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
                adx = dx.ewm(alpha=1/window, adjust=False).mean()
                
                df_with_indicators['adx'] = adx
                df_with_indicators['plus_di'] = plus_di
                df_with_indicators['minus_di'] = minus_di
            
            if 'ema_50' not in df_with_indicators.columns:
                df_with_indicators['ema_50'] = df_with_indicators['close'].ewm(span=50, adjust=False).mean()
            
            if 'ema_200' not in df_with_indicators.columns:
                df_with_indicators['ema_200'] = df_with_indicators['close'].ewm(span=200, adjust=False).mean()
            
            # Lấy các giá trị mới nhất
            latest = df_with_indicators.iloc[-1]
            
            # Tính toán các xác suất cho từng chế độ thị trường
            regime_scores = {
                'trending_up': 0,
                'trending_down': 0,
                'ranging': 0,
                'volatile': 0,
                'quiet': 0
            }
            
            # Trending Up
            if latest['adx'] > 25 and latest['plus_di'] > latest['minus_di']:
                regime_scores['trending_up'] += 0.5
            if 'ema_50' in latest and 'ema_200' in latest and latest['ema_50'] > latest['ema_200']:
                regime_scores['trending_up'] += 0.3
            if df_with_indicators['close'].iloc[-window:].is_monotonic_increasing:
                regime_scores['trending_up'] += 0.2
                
            # Trending Down
            if latest['adx'] > 25 and latest['plus_di'] < latest['minus_di']:
                regime_scores['trending_down'] += 0.5
            if 'ema_50' in latest and 'ema_200' in latest and latest['ema_50'] < latest['ema_200']:
                regime_scores['trending_down'] += 0.3
            if df_with_indicators['close'].iloc[-window:].is_monotonic_decreasing:
                regime_scores['trending_down'] += 0.2
                
            # Ranging
            if latest['adx'] < 20:
                regime_scores['ranging'] += 0.4
            if latest['bb_width'] < latest['bb_width_mean']:
                regime_scores['ranging'] += 0.3
            # Kiểm tra nếu giá dao động trong khoảng hẹp
            price_range = (df_with_indicators['high'].iloc[-window:].max() - 
                         df_with_indicators['low'].iloc[-window:].min()) / latest['close']
            if price_range < 0.05:  # Biên độ 5%
                regime_scores['ranging'] += 0.3
                
            # Volatile
            if latest['atr'] > latest['atr_mean'] * 1.5:
                regime_scores['volatile'] += 0.5
            if latest['bb_width'] > latest['bb_width_mean'] * 1.5:
                regime_scores['volatile'] += 0.5
                
            # Quiet
            if latest['atr'] < latest['atr_mean'] * 0.5:
                regime_scores['quiet'] += 0.5
            if latest['bb_width'] < latest['bb_width_mean'] * 0.5:
                regime_scores['quiet'] += 0.5
            
            # Chuẩn hóa điểm số thành xác suất
            total_score = sum(regime_scores.values())
            if total_score > 0:
                self.regime_probabilities = {regime: score / total_score for regime, score in regime_scores.items()}
            else:
                self.regime_probabilities = {regime: 0.2 for regime in regime_scores}
            
            # Chọn chế độ có điểm cao nhất
            self.current_regime = max(regime_scores, key=regime_scores.get)
            
            # Thêm vào lịch sử
            self.regime_history.append({
                'timestamp': datetime.now().isoformat(),
                'regime': self.current_regime,
                'probabilities': self.regime_probabilities
            })
            
            # Nếu lịch sử quá dài, giữ lại 100 bản ghi gần nhất
            if len(self.regime_history) > 100:
                self.regime_history = self.regime_history[-100:]
            
            logger.info(f"Phát hiện chế độ thị trường: {self.current_regime}")
            return self.current_regime
            
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
            return "unknown"
    
    def get_regime_description(self, regime: str = None) -> str:
        """
        Trả về mô tả về chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            str: Mô tả về chế độ thị trường
        """
        if regime is None:
            regime = self.current_regime
            
        if regime in self.regimes:
            return self.regimes[regime]['description']
        
        return "Không có thông tin về chế độ thị trường này"
    
    def get_suitable_strategies(self, regime: str = None) -> Dict[str, float]:
        """
        Trả về các chiến lược phù hợp với chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            Dict[str, float]: Ánh xạ chiến lược -> trọng số
        """
        if regime is None:
            regime = self.current_regime
            
        if regime in self.strategy_mapping:
            strategies = self.strategy_mapping[regime]
            # Tạo trọng số bằng nhau cho mỗi chiến lược
            weight = 1.0 / len(strategies)
            return {strategy: weight for strategy in strategies}
        
        # Trả về tất cả các chiến lược với trọng số thấp nếu không biết chế độ
        all_strategies = set()
        for strategies in self.strategy_mapping.values():
            all_strategies.update(strategies)
        
        weight = 1.0 / len(all_strategies)
        return {strategy: weight for strategy in all_strategies}
    
    def get_optimal_parameters(self, regime: str = None) -> Dict[str, Dict[str, Any]]:
        """
        Trả về tham số tối ưu cho từng chiến lược dựa trên chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            Dict[str, Dict[str, Any]]: Ánh xạ chiến lược -> tham số
        """
        if regime is None:
            regime = self.current_regime
            
        if regime in self.optimal_parameters:
            return self.optimal_parameters[regime]
        
        # Trả về tham số mặc định nếu không có tham số tối ưu
        default_params = {
            'rsi': {'overbought': 70, 'oversold': 30, 'period': 14},
            'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
            'bbands': {'period': 20, 'std_dev': 2.0},
            'ema_cross': {'fast_period': 9, 'slow_period': 21},
            'adx_trend': {'adx_period': 14, 'threshold': 25},
            'stochastic': {'k_period': 14, 'd_period': 3, 'overbought': 80, 'oversold': 20},
            'atr_breakout': {'atr_period': 14, 'multiplier': 1.5},
            'volatility_expansion': {'lookback': 20, 'threshold': 1.5},
            'channel_breakout': {'period': 20, 'multiplier': 1.0},
            'accumulation': {'volume_period': 20, 'price_period': 10}
        }
        
        # Điều chỉnh tham số theo chế độ thị trường
        if regime == 'trending_up' or regime == 'trending_down':
            default_params['rsi']['overbought'] = 80 if regime == 'trending_up' else 60
            default_params['rsi']['oversold'] = 40 if regime == 'trending_up' else 20
            default_params['macd']['fast_period'] = 8
            default_params['bbands']['std_dev'] = 2.5
            
        elif regime == 'ranging':
            default_params['rsi']['overbought'] = 65
            default_params['rsi']['oversold'] = 35
            default_params['bbands']['std_dev'] = 1.8
            default_params['stochastic']['overbought'] = 75
            default_params['stochastic']['oversold'] = 25
            
        elif regime == 'volatile':
            default_params['atr_breakout']['multiplier'] = 2.0
            default_params['bbands']['std_dev'] = 3.0
            default_params['macd']['fast_period'] = 6
            default_params['macd']['slow_period'] = 13
            
        elif regime == 'quiet':
            default_params['atr_breakout']['multiplier'] = 1.0
            default_params['bbands']['std_dev'] = 1.5
            default_params['channel_breakout']['period'] = 10
            
        return default_params
    
    def register_strategy_for_regime(self, regime: str, strategy_name: str,
                                  parameters: Dict = None, expected_performance: Dict = None) -> bool:
        """
        Đăng ký một chiến lược cho một chế độ thị trường cụ thể
        
        Args:
            regime (str): Chế độ thị trường
            strategy_name (str): Tên chiến lược
            parameters (Dict, optional): Tham số chiến lược
            expected_performance (Dict, optional): Hiệu suất kỳ vọng
            
        Returns:
            bool: True nếu đăng ký thành công, False nếu không
        """
        try:
            # Kiểm tra chế độ thị trường
            if regime not in self.regimes:
                logger.error(f"Chế độ thị trường không hợp lệ: {regime}")
                return False
            
            # Thêm chiến lược vào danh sách ánh xạ
            if regime not in self.strategy_mapping:
                self.strategy_mapping[regime] = []
                
            if strategy_name not in self.strategy_mapping[regime]:
                self.strategy_mapping[regime].append(strategy_name)
            
            # Cập nhật tham số tối ưu
            if parameters is not None:
                if regime not in self.optimal_parameters:
                    self.optimal_parameters[regime] = {}
                
                self.optimal_parameters[regime][strategy_name] = parameters
            
            logger.info(f"Đã đăng ký chiến lược {strategy_name} cho chế độ {regime}")
            
            # Lưu dữ liệu
            self.save_regime_data()
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi đăng ký chiến lược: {str(e)}")
            return False
    
    def save_regime_data(self) -> bool:
        """
        Lưu dữ liệu chế độ thị trường vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            data = {
                'regimes': self.regimes,
                'strategy_mapping': self.strategy_mapping,
                'optimal_parameters': self.optimal_parameters,
                'regime_history': self.regime_history,
                'current_regime': self.current_regime,
                'regime_probabilities': self.regime_probabilities
            }
            
            file_path = os.path.join(self.data_folder, 'market_regimes.json')
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Đã lưu dữ liệu chế độ thị trường vào {file_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu chế độ thị trường: {str(e)}")
            return False
    
    def load_regime_data(self) -> bool:
        """
        Tải dữ liệu chế độ thị trường từ file
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            file_path = os.path.join(self.data_folder, 'market_regimes.json')
            
            if not os.path.exists(file_path):
                logger.info(f"Chưa có file dữ liệu {file_path}, sử dụng dữ liệu mặc định")
                return False
                
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            self.regimes = data.get('regimes', self.regimes)
            self.strategy_mapping = data.get('strategy_mapping', self.strategy_mapping)
            self.optimal_parameters = data.get('optimal_parameters', self.optimal_parameters)
            self.regime_history = data.get('regime_history', self.regime_history)
            self.current_regime = data.get('current_regime', self.current_regime)
            self.regime_probabilities = data.get('regime_probabilities', self.regime_probabilities)
            
            logger.info(f"Đã tải dữ liệu chế độ thị trường từ {file_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu chế độ thị trường: {str(e)}")
            return False