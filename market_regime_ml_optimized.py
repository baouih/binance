#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hệ thống giao dịch thích ứng theo chế độ thị trường với ML

Module này xây dựng một hệ thống giao dịch thích ứng theo chế độ thị trường,
sử dụng học máy để phát hiện chế độ và tối ưu hóa chiến lược phù hợp.
Việc này giúp nâng cao tỷ lệ thắng bằng cách chỉ giao dịch trong các điều kiện
thị trường phù hợp và với chiến lược được tối ưu hóa cho từng chế độ.
"""

import os
import sys
import logging
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union, Optional
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from joblib import dump, load

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('market_regime_ml.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Các hằng số
REGIME_TYPES = ['trending_up', 'trending_down', 'ranging', 'volatile', 'quiet']
ML_MODEL_DIR = 'ml_models'
DATA_DIR = 'real_data'
RESULT_DIR = 'backtest_results'
CHART_DIR = 'backtest_charts'

os.makedirs(ML_MODEL_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

class MarketRegimeDetector:
    """
    Phát hiện chế độ thị trường hiện tại dựa vào học máy
    """
    
    def __init__(self, use_ml: bool = True, model_path: str = None):
        """
        Khởi tạo bộ phát hiện chế độ thị trường
        
        Args:
            use_ml (bool): Sử dụng học máy hay phương pháp rule-based
            model_path (str): Đường dẫn đến file mô hình (nếu dùng ML)
        """
        self.use_ml = use_ml
        self.model_path = model_path
        self.model = None
        self.scaler = None
        
        # Tải mô hình nếu đã chỉ định đường dẫn
        if use_ml and model_path and os.path.exists(model_path):
            try:
                self.model = load(model_path)
                self.scaler = load(model_path.replace('.joblib', '_scaler.joblib'))
                logger.info(f"Đã tải mô hình phát hiện chế độ thị trường từ: {model_path}")
            except Exception as e:
                logger.error(f"Lỗi khi tải mô hình: {e}")
                self.use_ml = False
    
    def extract_features(self, df: pd.DataFrame, window: int = 20) -> np.ndarray:
        """
        Trích xuất đặc trưng cho mô hình ML
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            window (int): Kích thước cửa sổ để tính đặc trưng
            
        Returns:
            np.ndarray: Vector đặc trưng
        """
        if len(df) < window + 10:  # Cần đủ dữ liệu
            return None
            
        # Lấy dữ liệu trong cửa sổ
        recent_data = df.iloc[-window:].copy()
        
        # Tính toán các đặc trưng
        features = []
        
        # 1. Biến động (volatility)
        price_volatility = recent_data['close'].pct_change().std() * 100
        features.append(price_volatility)
        
        if 'atr' in recent_data.columns:
            avg_atr = recent_data['atr'].mean()
            relative_atr = avg_atr / recent_data['close'].mean() * 100
            features.append(relative_atr)
        
        # 2. Xu hướng (trend)
        if 'ema_9' in recent_data.columns and 'ema_21' in recent_data.columns:
            # Độ dốc EMA
            ema_9_slope = (recent_data['ema_9'].iloc[-1] / recent_data['ema_9'].iloc[0] - 1) * 100
            ema_21_slope = (recent_data['ema_21'].iloc[-1] / recent_data['ema_21'].iloc[0] - 1) * 100
            features.append(ema_9_slope)
            features.append(ema_21_slope)
            
            # Khoảng cách giữa các EMA
            ema_diff = (recent_data['ema_9'] - recent_data['ema_21']).mean() / recent_data['close'].mean() * 100
            features.append(ema_diff)
        
        # 3. Dao động (oscillation)
        if 'rsi' in recent_data.columns:
            rsi_mean = recent_data['rsi'].mean()
            rsi_std = recent_data['rsi'].std()
            rsi_min = recent_data['rsi'].min()
            rsi_max = recent_data['rsi'].max()
            rsi_range = rsi_max - rsi_min
            features.extend([rsi_mean, rsi_std, rsi_range])
        
        # 4. Khối lượng (volume)
        if 'volume' in recent_data.columns:
            vol_mean = recent_data['volume'].mean()
            vol_std = recent_data['volume'].std() / vol_mean if vol_mean > 0 else 0
            vol_trend = (recent_data['volume'].iloc[-5:].mean() / recent_data['volume'].iloc[:5].mean() - 1) * 100
            features.extend([vol_std, vol_trend])
        
        # 5. Bollinger Bands
        if 'bb_upper' in recent_data.columns and 'bb_lower' in recent_data.columns:
            bb_width = (recent_data['bb_upper'] - recent_data['bb_lower']).mean() / recent_data['close'].mean() * 100
            price_position_in_bb = ((recent_data['close'] - recent_data['bb_lower']) / 
                                  (recent_data['bb_upper'] - recent_data['bb_lower'])).mean() * 100
            features.extend([bb_width, price_position_in_bb])
        
        # 6. ADX (Chỉ báo sức mạnh xu hướng)
        if 'adx' in recent_data.columns:
            adx_mean = recent_data['adx'].mean()
            adx_trend = recent_data['adx'].iloc[-1] - recent_data['adx'].iloc[0]
            features.extend([adx_mean, adx_trend])
        
        # 7. Tỷ lệ nến tăng/giảm
        price_changes = recent_data['close'] - recent_data['open']
        bullish_candles = (price_changes > 0).sum() / len(recent_data) * 100
        features.append(bullish_candles)
        
        # 8. Khoảng dao động giá (high-low)
        price_range = (recent_data['high'] - recent_data['low']).mean() / recent_data['close'].mean() * 100
        features.append(price_range)
        
        # 9. Tỷ lệ nến với thân lớn
        candle_body = abs(recent_data['close'] - recent_data['open'])
        large_body_ratio = (candle_body > candle_body.mean()).sum() / len(recent_data) * 100
        features.append(large_body_ratio)
        
        # 10. Chỉ số tương quan với trendline
        try:
            close_prices = recent_data['close'].values
            x = np.arange(len(close_prices))
            z = np.polyfit(x, close_prices, 1)
            trend_line = np.poly1d(z)
            trend_values = trend_line(x)
            
            # Độ dốc của đường xu hướng
            slope = z[0] / close_prices.mean() * 100
            features.append(slope)
            
            # Độ lệch so với đường xu hướng
            deviation = np.mean(np.abs(close_prices - trend_values)) / close_prices.mean() * 100
            features.append(deviation)
            
            # R-squared (độ khớp với đường xu hướng)
            mean_price = np.mean(close_prices)
            ss_total = np.sum((close_prices - mean_price) ** 2)
            ss_residual = np.sum((close_prices - trend_values) ** 2)
            r_squared = 1 - (ss_residual / ss_total) if ss_total > 0 else 0
            features.append(r_squared * 100)  # Chuyển thành %
        except:
            # Nếu không tính được, thêm giá trị 0
            features.extend([0, 0, 0])
        
        return np.array(features).reshape(1, -1)
    
    def detect_regime_rule_based(self, df: pd.DataFrame, window: int = 20) -> str:
        """
        Phát hiện chế độ thị trường bằng phương pháp rule-based
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            window (int): Kích thước cửa sổ để phân tích
            
        Returns:
            str: Chế độ thị trường ('trending_up', 'trending_down', 'ranging', 'volatile', 'quiet')
        """
        if len(df) < window:
            return "unknown"
            
        # Lấy dữ liệu trong cửa sổ
        recent_data = df.iloc[-window:].copy()
        
        # 1. Tính biến động
        volatility = recent_data['close'].pct_change().std() * 100
        
        # 2. Tính xu hướng
        price_start = recent_data['close'].iloc[0]
        price_end = recent_data['close'].iloc[-1]
        price_change = (price_end / price_start - 1) * 100
        
        # 3. Kiểm tra sự hiện diện của ADX
        has_strong_trend = False
        if 'adx' in recent_data.columns:
            adx_values = recent_data['adx'].iloc[-5:].mean()  # Lấy trung bình 5 giá trị gần nhất
            has_strong_trend = adx_values > 25
        
        # 4. Kiểm tra dao động sideways
        is_ranging = False
        if 'bb_upper' in recent_data.columns and 'bb_lower' in recent_data.columns:
            bb_width = (recent_data['bb_upper'] - recent_data['bb_lower']).mean() / recent_data['close'].mean() * 100
            is_ranging = bb_width < 4  # Dải Bollinger Bands hẹp
        
        # 5. Kiểm tra khối lượng
        low_volume = False
        if 'volume' in recent_data.columns and 'volume_sma20' in recent_data.columns:
            volume_ratio = recent_data['volume'].mean() / recent_data['volume_sma20'].mean()
            low_volume = volume_ratio < 0.8
        
        # Phân loại chế độ thị trường dựa trên các chỉ số
        if volatility > 4:
            regime = "volatile"
        elif abs(price_change) > 3 and has_strong_trend:
            regime = "trending_up" if price_change > 0 else "trending_down"
        elif is_ranging:
            regime = "ranging"
        elif low_volume and volatility < 1.5:
            regime = "quiet"
        else:
            # Mặc định: phân loại dựa trên biến động và xu hướng giá
            if abs(price_change) > 2:
                regime = "trending_up" if price_change > 0 else "trending_down"
            elif volatility < 1.5:
                regime = "quiet"
            else:
                regime = "ranging"
        
        return regime
    
    def detect_regime(self, df: pd.DataFrame, window: int = 20) -> str:
        """
        Phát hiện chế độ thị trường
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            window (int): Kích thước cửa sổ để phân tích
            
        Returns:
            str: Chế độ thị trường ('trending_up', 'trending_down', 'ranging', 'volatile', 'quiet')
        """
        if not self.use_ml or self.model is None:
            return self.detect_regime_rule_based(df, window)
        
        try:
            # Trích xuất đặc trưng
            features = self.extract_features(df, window)
            if features is None:
                return self.detect_regime_rule_based(df, window)
            
            # Chuẩn hóa đặc trưng
            if self.scaler is not None:
                features = self.scaler.transform(features)
            
            # Dự đoán chế độ thị trường
            regime_idx = self.model.predict(features)[0]
            return REGIME_TYPES[regime_idx]
        except Exception as e:
            logger.error(f"Lỗi khi dự đoán chế độ thị trường: {e}")
            return self.detect_regime_rule_based(df, window)
    
    def train(self, training_data: List[Dict], save_path: str = None) -> float:
        """
        Huấn luyện mô hình phát hiện chế độ thị trường
        
        Args:
            training_data (List[Dict]): Dữ liệu huấn luyện
                Mỗi phần tử là một dict với format:
                    {
                      'features': np.ndarray,  # Vector đặc trưng
                      'regime': str            # Chế độ thị trường thực tế 
                    }
            save_path (str): Đường dẫn để lưu mô hình
            
        Returns:
            float: Độ chính xác của mô hình
        """
        if not training_data:
            logger.error("Không có dữ liệu huấn luyện")
            return 0.0
        
        # Chuẩn bị dữ liệu
        X = np.vstack([item['features'] for item in training_data])
        y = np.array([REGIME_TYPES.index(item['regime']) for item in training_data])
        
        # Chia tập huấn luyện và kiểm thử
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Chuẩn hóa dữ liệu
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        
        # Huấn luyện mô hình
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Đánh giá mô hình
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Đã huấn luyện mô hình phát hiện chế độ thị trường với độ chính xác: {accuracy:.4f}")
        
        # Lưu mô hình nếu cần
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            dump(model, save_path)
            dump(scaler, save_path.replace('.joblib', '_scaler.joblib'))
            logger.info(f"Đã lưu mô hình tại: {save_path}")
        
        # Cập nhật mô hình hiện tại
        self.model = model
        self.scaler = scaler
        self.use_ml = True
        
        return accuracy
    
    def prepare_training_data(self, data_files: List[str], window: int = 20) -> List[Dict]:
        """
        Chuẩn bị dữ liệu huấn luyện từ các file dữ liệu giá
        
        Args:
            data_files (List[str]): Danh sách đường dẫn đến các file dữ liệu
            window (int): Kích thước cửa sổ để phân tích
            
        Returns:
            List[Dict]: Dữ liệu huấn luyện
        """
        training_data = []
        
        for file_path in data_files:
            try:
                # Tải dữ liệu
                df = pd.read_csv(file_path)
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                
                # Thêm các chỉ báo kỹ thuật
                df_with_indicators = self.add_indicators(df)
                
                # Chuẩn bị dữ liệu huấn luyện
                for i in range(window, len(df_with_indicators) - window, window // 2):  # Lấy mẫu với bước nhảy window/2
                    subset = df_with_indicators.iloc[i-window:i]
                    next_subset = df_with_indicators.iloc[i:i+window]
                    
                    # Nhãn chế độ thị trường dựa trên hành vi giá trong khoảng tiếp theo
                    regime = self.detect_regime_rule_based(next_subset, window)
                    
                    # Trích xuất đặc trưng
                    features = self.extract_features(subset, window)
                    if features is not None:
                        training_data.append({
                            'features': features[0],  # Loại bỏ chiều batch
                            'regime': regime
                        })
            except Exception as e:
                logger.error(f"Lỗi khi chuẩn bị dữ liệu từ {file_path}: {e}")
        
        logger.info(f"Đã chuẩn bị {len(training_data)} mẫu dữ liệu huấn luyện")
        return training_data
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các chỉ báo kỹ thuật vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã thêm
        """
        # Tạo bản sao để tránh warning
        result = df.copy()
        
        # RSI (14 periods)
        delta = result['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        result['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = result['close'].ewm(span=12, adjust=False).mean()
        ema26 = result['close'].ewm(span=26, adjust=False).mean()
        result['macd'] = ema12 - ema26
        result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
        result['macd_hist'] = result['macd'] - result['macd_signal']
        
        # Bollinger Bands
        result['sma20'] = result['close'].rolling(window=20).mean()
        result['bb_middle'] = result['sma20']
        result['bb_std'] = result['close'].rolling(window=20).std()
        result['bb_upper'] = result['bb_middle'] + (result['bb_std'] * 2)
        result['bb_lower'] = result['bb_middle'] - (result['bb_std'] * 2)
        
        # EMAs
        for period in [9, 21, 50, 200]:
            result[f'ema_{period}'] = result['close'].ewm(span=period, adjust=False).mean()
        
        # ATR
        high_low = result['high'] - result['low']
        high_close = (result['high'] - result['close'].shift()).abs()
        low_close = (result['low'] - result['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        result['atr'] = true_range.rolling(window=14).mean()
        
        # Stochastic Oscillator
        period = 14
        result['lowest_low'] = result['low'].rolling(window=period).min()
        result['highest_high'] = result['high'].rolling(window=period).max()
        result['stoch_k'] = 100 * ((result['close'] - result['lowest_low']) / 
                                  (result['highest_high'] - result['lowest_low']))
        result['stoch_d'] = result['stoch_k'].rolling(window=3).mean()
        
        # ADX
        plus_dm = result['high'].diff()
        minus_dm = result['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = abs(minus_dm)
        
        tr = true_range
        plus_di = 100 * (plus_dm.rolling(window=14).mean() / tr.rolling(window=14).mean())
        minus_di = 100 * (minus_dm.rolling(window=14).mean() / tr.rolling(window=14).mean())
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        result['adx'] = dx.rolling(window=14).mean()
        result['plus_di'] = plus_di
        result['minus_di'] = minus_di
        
        # Volume Metrics
        if 'volume' in result.columns:
            result['volume_sma20'] = result['volume'].rolling(window=20).mean()
            result['volume_ratio'] = result['volume'] / result['volume_sma20']
        
        # Loại bỏ missing values
        result.dropna(inplace=True)
        
        return result

class StrategySelector:
    """
    Lựa chọn và tối ưu hóa chiến lược phù hợp với từng chế độ thị trường
    """
    
    def __init__(self):
        """Khởi tạo bộ chọn chiến lược"""
        # Danh sách các chiến lược theo chế độ thị trường
        self.strategies_by_regime = {
            'trending_up': {
                'macd': {'weight': 0.4, 'active': True},
                'ema_cross': {'weight': 0.4, 'active': True},
                'adx': {'weight': 0.2, 'active': True},
            },
            'trending_down': {
                'macd': {'weight': 0.3, 'active': True},
                'ema_cross': {'weight': 0.3, 'active': True},
                'bbands': {'weight': 0.2, 'active': True},
                'adx': {'weight': 0.2, 'active': True},
            },
            'ranging': {
                'rsi': {'weight': 0.4, 'active': True},
                'bbands': {'weight': 0.4, 'active': True},
                'stochastic': {'weight': 0.2, 'active': True},
            },
            'volatile': {
                'bbands': {'weight': 0.5, 'active': True},
                'atr': {'weight': 0.5, 'active': True},
            },
            'quiet': {
                'bbands': {'weight': 0.5, 'active': True},
                'rsi': {'weight': 0.3, 'active': True},
                'stochastic': {'weight': 0.2, 'active': True},
            }
        }
        
        # Tham số tối ưu cho từng chiến lược và chế độ thị trường
        self.optimal_params = {
            'trending_up': {
                'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9, 'use_histogram': True},
                'ema_cross': {'fast_ema': 9, 'slow_ema': 21, 'use_confirmation': True},
                'adx': {'adx_period': 14, 'adx_threshold': 25, 'use_di_cross': True},
            },
            'trending_down': {
                'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9, 'use_histogram': True},
                'ema_cross': {'fast_ema': 9, 'slow_ema': 21, 'use_confirmation': True},
                'bbands': {'bb_period': 20, 'bb_std': 2.0, 'use_bb_squeeze': False},
                'adx': {'adx_period': 14, 'adx_threshold': 25, 'use_di_cross': True},
            },
            'ranging': {
                'rsi': {'overbought': 70, 'oversold': 30, 'use_trend_filter': False},
                'bbands': {'bb_period': 20, 'bb_std': 2.0, 'use_bb_squeeze': True},
                'stochastic': {'k_period': 14, 'd_period': 3, 'overbought': 80, 'oversold': 20},
            },
            'volatile': {
                'bbands': {'bb_period': 20, 'bb_std': 2.5, 'use_bb_squeeze': False},
                'atr': {'atr_period': 14, 'atr_multiplier': 1.5, 'use_atr_stops': True},
            },
            'quiet': {
                'bbands': {'bb_period': 20, 'bb_std': 1.0, 'use_bb_squeeze': True},
                'rsi': {'overbought': 55, 'oversold': 45, 'use_trend_filter': False},
                'stochastic': {'k_period': 14, 'd_period': 3, 'overbought': 65, 'oversold': 35},
                'atr': {'atr_period': 14, 'atr_multiplier': 0.7, 'use_atr_stops': True},
            }
        }
        
        # Tham số quản lý vốn theo chế độ thị trường
        self.risk_params = {
            'trending_up': {
                'risk_percentage': 1.0,
                'take_profit_pct': 3.0,
                'stop_loss_pct': 1.5,
                'trailing_stop': True,
                'trailing_activation': 0.5,
                'max_trades': 3
            },
            'trending_down': {
                'risk_percentage': 1.0,
                'take_profit_pct': 3.0,
                'stop_loss_pct': 1.5,
                'trailing_stop': True,
                'trailing_activation': 0.5,
                'max_trades': 3
            },
            'ranging': {
                'risk_percentage': 0.8,
                'take_profit_pct': 2.0,
                'stop_loss_pct': 1.0,
                'trailing_stop': False,
                'trailing_activation': 0.0,
                'max_trades': 2
            },
            'volatile': {
                'risk_percentage': 0.5,
                'take_profit_pct': 4.0,
                'stop_loss_pct': 2.0,
                'trailing_stop': True,
                'trailing_activation': 0.3,
                'max_trades': 1
            },
            'quiet': {
                'risk_percentage': 0.6,
                'take_profit_pct': 1.2,
                'stop_loss_pct': 0.6,
                'trailing_stop': True,
                'trailing_activation': 0.4,
                'max_trades': 1
            }
        }
    
    def get_strategies_for_regime(self, regime: str) -> Dict:
        """
        Lấy danh sách các chiến lược phù hợp cho chế độ thị trường
        
        Args:
            regime (str): Chế độ thị trường
            
        Returns:
            Dict: {strategy_name: weight} for active strategies
        """
        if regime not in self.strategies_by_regime:
            regime = 'ranging'  # Mặc định
        
        # Lấy các chiến lược đang hoạt động
        active_strategies = {}
        for strat_name, strat_info in self.strategies_by_regime[regime].items():
            if strat_info['active']:
                active_strategies[strat_name] = strat_info['weight']
        
        return active_strategies
    
    def get_optimal_params(self, regime: str, strategy_name: str) -> Dict:
        """
        Lấy tham số tối ưu cho chiến lược cụ thể trong chế độ thị trường
        
        Args:
            regime (str): Chế độ thị trường
            strategy_name (str): Tên chiến lược
            
        Returns:
            Dict: Tham số tối ưu
        """
        if regime not in self.optimal_params or strategy_name not in self.optimal_params[regime]:
            # Trả về tham số mặc định nếu không tìm thấy
            return {}
        
        return self.optimal_params[regime][strategy_name]
    
    def get_risk_params(self, regime: str) -> Dict:
        """
        Lấy tham số quản lý vốn cho chế độ thị trường
        
        Args:
            regime (str): Chế độ thị trường
            
        Returns:
            Dict: Tham số quản lý vốn
        """
        if regime not in self.risk_params:
            regime = 'ranging'  # Mặc định
        
        return self.risk_params[regime]
    
    def optimize_params(self, regime: str, strategy_name: str, 
                      training_data: pd.DataFrame, metric: str = 'roi') -> Dict:
        """
        Tối ưu hóa tham số cho chiến lược cụ thể trong chế độ thị trường
        
        Args:
            regime (str): Chế độ thị trường
            strategy_name (str): Tên chiến lược
            training_data (pd.DataFrame): Dữ liệu huấn luyện
            metric (str): Chỉ số để tối ưu hóa ('roi', 'win_rate', 'sharpe')
            
        Returns:
            Dict: Tham số tối ưu
        """
        # TODO: Implement grid search hoặc Bayesian optimization
        # Hiện tại, sử dụng tham số đã được định nghĩa trước
        return self.get_optimal_params(regime, strategy_name)
    
    def update_strategy_performance(self, regime: str, strategy_name: str, 
                                  performance: Dict) -> None:
        """
        Cập nhật hiệu suất của chiến lược trong chế độ thị trường cụ thể
        
        Args:
            regime (str): Chế độ thị trường
            strategy_name (str): Tên chiến lược
            performance (Dict): Hiệu suất 
                (ví dụ: {'win_rate': 0.6, 'roi': 5.2, 'sharpe': 1.5})
        """
        # TODO: Implement performance tracking và adaptive adjustment
        pass
    
    def save_config(self, file_path: str = 'strategy_selector_config.json') -> None:
        """
        Lưu cấu hình bộ chọn chiến lược
        
        Args:
            file_path (str): Đường dẫn file lưu cấu hình
        """
        config = {
            'strategies_by_regime': self.strategies_by_regime,
            'optimal_params': self.optimal_params,
            'risk_params': self.risk_params
        }
        
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=4)
            
        logger.info(f"Đã lưu cấu hình bộ chọn chiến lược tại: {file_path}")
    
    def load_config(self, file_path: str = 'strategy_selector_config.json') -> bool:
        """
        Tải cấu hình bộ chọn chiến lược
        
        Args:
            file_path (str): Đường dẫn file cấu hình
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        if not os.path.exists(file_path):
            logger.error(f"Không tìm thấy file cấu hình: {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            
            self.strategies_by_regime = config.get('strategies_by_regime', self.strategies_by_regime)
            self.optimal_params = config.get('optimal_params', self.optimal_params)
            self.risk_params = config.get('risk_params', self.risk_params)
            
            logger.info(f"Đã tải cấu hình bộ chọn chiến lược từ: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            return False

class Strategy:
    """
    Lớp cơ sở cho các chiến lược giao dịch
    """
    
    def __init__(self, name: str, params: Dict = None):
        """
        Khởi tạo chiến lược
        
        Args:
            name (str): Tên chiến lược
            params (Dict): Tham số của chiến lược
        """
        self.name = name
        self.params = params or {}
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu giao dịch từ dữ liệu
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            
        Returns:
            int: 1 (mua), -1 (bán), 0 (giữ nguyên)
        """
        # Triển khai trong lớp con
        return 0

class RSIStrategy(Strategy):
    """Chiến lược dựa trên RSI"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'overbought': 70,
            'oversold': 30,
            'use_trend_filter': True,
            'trend_ema': 50
        }
        merged_params = {**default_params, **(params or {})}
        super().__init__("RSI", merged_params)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        # Kiểm tra dữ liệu
        if 'rsi' not in df.columns or len(df) < 2:
            return 0
        
        # Lấy thông số từ tham số
        overbought = self.params.get('overbought', 70)
        oversold = self.params.get('oversold', 30)
        use_trend_filter = self.params.get('use_trend_filter', True)
        trend_ema = self.params.get('trend_ema', 50)
        
        # Lấy giá trị RSI
        current_rsi = df['rsi'].iloc[-1]
        previous_rsi = df['rsi'].iloc[-2]
        
        # Kiểm tra xu hướng nếu được yêu cầu
        trend_ok = True
        if use_trend_filter:
            ema_col = f'ema_{trend_ema}'
            if ema_col in df.columns:
                current_price = df['close'].iloc[-1]
                current_ema = df[ema_col].iloc[-1]
                trend_ok = current_price > current_ema  # Xu hướng tăng
        
        # Tạo tín hiệu
        signal = 0
        
        # Xác định nếu đang ở trong thị trường yên tĩnh (quiet market)
        is_quiet_market = False
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
            # Tính dải Bollinger Band tương đối
            bb_width = (df['bb_upper'].iloc[-1] - df['bb_lower'].iloc[-1]) / df['bb_middle'].iloc[-1]
            
            # So sánh với ngưỡng hẹp để xác định thị trường yên tĩnh
            if bb_width < 0.03:  # 3% width là khá hẹp, thị trường yên tĩnh
                is_quiet_market = True
        
        # Bổ sung logic đặc biệt cho thị trường yên tĩnh
        if is_quiet_market:
            # Trong thị trường yên tĩnh, sử dụng ngưỡng RSI gần trung tâm hơn
            if current_rsi < oversold + 10 and previous_rsi < current_rsi and current_rsi > previous_rsi + 1.5:
                # Tín hiệu mua khi RSI dưới ngưỡng oversold+10 và đang tăng
                signal = 1
            elif current_rsi > overbought - 10 and previous_rsi > current_rsi and previous_rsi > current_rsi + 1.5:
                # Tín hiệu bán khi RSI trên ngưỡng overbought-10 và đang giảm
                signal = -1
        else:
            # Logic thông thường cho các thị trường khác
            if current_rsi < oversold and previous_rsi < current_rsi:
                # Tín hiệu mua khi RSI dưới ngưỡng oversold và đang tăng
                if trend_ok or not use_trend_filter:
                    signal = 1
            elif current_rsi > overbought and previous_rsi > current_rsi:
                # Tín hiệu bán khi RSI trên ngưỡng overbought và đang giảm
                if not trend_ok or not use_trend_filter:
                    signal = -1
        
        return signal

class MACDStrategy(Strategy):
    """Chiến lược dựa trên MACD"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'use_histogram': True
        }
        merged_params = {**default_params, **(params or {})}
        super().__init__("MACD", merged_params)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        # Kiểm tra dữ liệu
        if 'macd' not in df.columns or 'macd_signal' not in df.columns or len(df) < 2:
            return 0
        
        # Lấy giá trị MACD
        current_macd = df['macd'].iloc[-1]
        previous_macd = df['macd'].iloc[-2]
        current_signal = df['macd_signal'].iloc[-1]
        previous_signal = df['macd_signal'].iloc[-2]
        
        if 'macd_hist' in df.columns:
            current_hist = df['macd_hist'].iloc[-1]
            previous_hist = df['macd_hist'].iloc[-2]
        else:
            current_hist = current_macd - current_signal
            previous_hist = previous_macd - previous_signal
        
        # Lấy thông số từ tham số
        use_histogram = self.params.get('use_histogram', True)
        
        # Tạo tín hiệu
        signal = 0
        
        # Tín hiệu cắt nhau
        if previous_macd < previous_signal and current_macd > current_signal:
            # MACD cắt lên trên signal line -> mua
            signal = 1
        elif previous_macd > previous_signal and current_macd < current_signal:
            # MACD cắt xuống dưới signal line -> bán
            signal = -1
        
        # Bổ sung tín hiệu từ histogram nếu cần
        if use_histogram and signal == 0:
            if current_hist > 0 and previous_hist < current_hist:
                # Histogram dương và đang tăng -> xu hướng tăng
                signal = 1
            elif current_hist < 0 and previous_hist > current_hist:
                # Histogram âm và đang giảm -> xu hướng giảm
                signal = -1
        
        return signal

class BollingerBandsStrategy(Strategy):
    """Chiến lược dựa trên Bollinger Bands"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'bb_period': 20,
            'bb_std': 2.0,
            'use_bb_squeeze': True
        }
        merged_params = {**default_params, **(params or {})}
        super().__init__("BollingerBands", merged_params)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        # Kiểm tra dữ liệu
        if 'bb_lower' not in df.columns or 'bb_upper' not in df.columns or len(df) < 2:
            return 0
        
        # Lấy giá trị
        current_price = df['close'].iloc[-1]
        previous_price = df['close'].iloc[-2]
        current_lower = df['bb_lower'].iloc[-1]
        current_upper = df['bb_upper'].iloc[-1]
        current_middle = df['bb_middle'].iloc[-1] if 'bb_middle' in df.columns else None
        
        # Lấy thông số từ tham số
        use_bb_squeeze = self.params.get('use_bb_squeeze', True)
        bb_std = self.params.get('bb_std', 2.0)
        
        # Tạo tín hiệu
        signal = 0
        
        # Xác định nếu đang ở trong thị trường yên tĩnh (quiet market)
        is_quiet_market = False
        if current_middle is not None:
            # Tính dải Bollinger Band tương đối
            bb_width = (current_upper - current_lower) / current_middle
            
            # So sánh với ngưỡng hẹp để xác định thị trường yên tĩnh
            if bb_width < 0.03:  # 3% width là khá hẹp, thị trường yên tĩnh
                is_quiet_market = True
        
        # Kiểm tra squeeze
        bb_width = None
        if use_bb_squeeze and current_middle is not None:
            bb_width = (current_upper - current_lower) / current_middle
            previous_width = ((df['bb_upper'].iloc[-3] - df['bb_lower'].iloc[-3]) / 
                            df['bb_middle'].iloc[-3]) if len(df) > 2 else bb_width
            
            # Phát hiện squeeze và breakout
            squeeze_breakout = bb_width > previous_width * 1.2  # Dải BB bung ra 20%
            if squeeze_breakout:
                # Xác định hướng breakout
                if current_price > previous_price and current_price > current_middle:
                    signal = 1  # Bung ra hướng lên
                elif current_price < previous_price and current_price < current_middle:
                    signal = -1  # Bung ra hướng xuống
        
        # Logic đặc biệt cho thị trường yên tĩnh
        if is_quiet_market and signal == 0:
            # Trong thị trường yên tĩnh, sử dụng phương pháp "Mean Reversion"
            # với ngưỡng gần hơn để trả giá nhanh
            mean_reversion_threshold = 0.7  # Phần trăm của khoảng cách từ giữa đến biên
            
            # Tính khoảng cách tương đối đến giá trung bình
            upper_distance = (current_upper - current_middle) * mean_reversion_threshold
            lower_distance = (current_middle - current_lower) * mean_reversion_threshold
            
            # Tín hiệu dựa trên sự trở về giá trị trung bình với ngưỡng thấp hơn
            if current_price >= current_middle + upper_distance:
                # Giá quá cao so với trung bình trong thị trường yên tĩnh
                signal = -1  # Tín hiệu bán để hưởng lợi từ sự đảo chiều
            elif current_price <= current_middle - lower_distance:
                # Giá quá thấp so với trung bình trong thị trường yên tĩnh
                signal = 1   # Tín hiệu mua để hưởng lợi từ sự đảo chiều
                
            # Thêm tín hiệu "touch và bounce" trong thị trường yên tĩnh
            if signal == 0:
                # Kiểm tra sự phản hồi từ biên
                if previous_price <= current_lower * 1.002 and current_price > previous_price:
                    # Giá chạm dải dưới và bắt đầu tăng
                    signal = 1  # Mua khi có dấu hiệu phản hồi
                elif previous_price >= current_upper * 0.998 and current_price < previous_price:
                    # Giá chạm dải trên và bắt đầu giảm
                    signal = -1  # Bán khi có dấu hiệu phản hồi
        else:
            # Tín hiệu cơ bản của Bollinger Bands cho các thị trường khác
            if signal == 0:
                # Phản ứng khi giá chạm dải
                if current_price <= current_lower and previous_price >= current_lower:
                    signal = 1  # Phản ứng mua ở dải dưới
                elif current_price >= current_upper and previous_price <= current_upper:
                    signal = -1  # Phản ứng bán ở dải trên
                
                # Nếu giá vượt quá dải rõ rệt
                bb_overshoot_threshold = 0.005  # 0.5% vượt qua dải
                if current_price < current_lower * (1 - bb_overshoot_threshold):
                    signal = 1  # Quá bán
                elif current_price > current_upper * (1 + bb_overshoot_threshold):
                    signal = -1  # Quá mua
        
        return signal

class EMACrossStrategy(Strategy):
    """Chiến lược dựa trên EMA Cross"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'fast_ema': 9,
            'slow_ema': 21,
            'use_confirmation': True,
            'confirmation_periods': 2
        }
        merged_params = {**default_params, **(params or {})}
        super().__init__("EMACross", merged_params)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        # Lấy thông số từ tham số
        fast_ema = self.params.get('fast_ema', 9)
        slow_ema = self.params.get('slow_ema', 21)
        use_confirmation = self.params.get('use_confirmation', True)
        confirmation_periods = self.params.get('confirmation_periods', 2)
        
        # Kiểm tra dữ liệu
        fast_col = f'ema_{fast_ema}'
        slow_col = f'ema_{slow_ema}'
        
        if fast_col not in df.columns or slow_col not in df.columns or len(df) < 2:
            return 0
        
        # Lấy giá trị EMA
        current_fast = df[fast_col].iloc[-1]
        current_slow = df[slow_col].iloc[-1]
        previous_fast = df[fast_col].iloc[-2]
        previous_slow = df[slow_col].iloc[-2]
        
        # Tạo tín hiệu
        signal = 0
        
        if not use_confirmation:
            # Tín hiệu đơn giản dựa trên cắt nhau
            if previous_fast < previous_slow and current_fast > current_slow:
                signal = 1  # EMA nhanh cắt lên EMA chậm -> mua
            elif previous_fast > previous_slow and current_fast < current_slow:
                signal = -1  # EMA nhanh cắt xuống EMA chậm -> bán
        else:
            # Sử dụng xác nhận qua nhiều nến
            confirmed = False
            
            if len(df) > confirmation_periods + 1:
                # Kiểm tra xác nhận cho tín hiệu mua
                if current_fast > current_slow:
                    # Tìm điểm cắt nhau gần đây
                    for i in range(1, min(confirmation_periods + 1, len(df) - 1)):
                        idx = -1 - i
                        if df[fast_col].iloc[idx] <= df[slow_col].iloc[idx]:
                            confirmed = True
                            break
                    
                    if confirmed:
                        signal = 1
                
                # Kiểm tra xác nhận cho tín hiệu bán
                elif current_fast < current_slow:
                    # Tìm điểm cắt nhau gần đây
                    for i in range(1, min(confirmation_periods + 1, len(df) - 1)):
                        idx = -1 - i
                        if df[fast_col].iloc[idx] >= df[slow_col].iloc[idx]:
                            confirmed = True
                            break
                    
                    if confirmed:
                        signal = -1
        
        return signal

class ADXStrategy(Strategy):
    """Chiến lược dựa trên ADX"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'adx_period': 14,
            'adx_threshold': 25,
            'use_di_cross': True
        }
        merged_params = {**default_params, **(params or {})}
        super().__init__("ADX", merged_params)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        # Kiểm tra dữ liệu
        if 'adx' not in df.columns or 'plus_di' not in df.columns or 'minus_di' not in df.columns or len(df) < 2:
            return 0
        
        # Lấy thông số từ tham số
        adx_threshold = self.params.get('adx_threshold', 25)
        use_di_cross = self.params.get('use_di_cross', True)
        
        # Lấy giá trị ADX
        current_adx = df['adx'].iloc[-1]
        current_plus_di = df['plus_di'].iloc[-1]
        current_minus_di = df['minus_di'].iloc[-1]
        previous_plus_di = df['plus_di'].iloc[-2]
        previous_minus_di = df['minus_di'].iloc[-2]
        
        # Tạo tín hiệu
        signal = 0
        
        # Kiểm tra sức mạnh xu hướng
        strong_trend = current_adx > adx_threshold
        
        if strong_trend:
            if use_di_cross:
                # Sử dụng tín hiệu cắt nhau DI+/DI-
                if previous_plus_di < previous_minus_di and current_plus_di > current_minus_di:
                    signal = 1  # DI+ cắt lên DI- -> mua
                elif previous_plus_di > previous_minus_di and current_plus_di < current_minus_di:
                    signal = -1  # DI+ cắt xuống DI- -> bán
            else:
                # Sử dụng so sánh DI+/DI-
                if current_plus_di > current_minus_di:
                    signal = 1  # DI+ > DI- -> xu hướng tăng
                else:
                    signal = -1  # DI+ < DI- -> xu hướng giảm
        
        return signal

class CompositeStrategy(Strategy):
    """Chiến lược kết hợp nhiều chiến lược khác"""
    
    def __init__(self, strategies: Dict[str, Dict] = None, params: Dict = None):
        """
        Khởi tạo chiến lược kết hợp
        
        Args:
            strategies (Dict[str, Dict]): Ánh xạ tên chiến lược -> {weight, params, active}
            params (Dict): Tham số của chiến lược kết hợp
        """
        super().__init__("Composite", params or {})
        self.strategies = {}
        self.strategy_weights = {}
        
        # Khởi tạo các chiến lược thành phần
        if strategies:
            for name, config in strategies.items():
                if config.get('active', True):
                    self.add_strategy(name, config.get('weight', 1.0), config.get('params', {}))
    
    def add_strategy(self, name: str, weight: float, params: Dict = None) -> None:
        """
        Thêm chiến lược thành phần
        
        Args:
            name (str): Tên chiến lược
            weight (float): Trọng số
            params (Dict): Tham số của chiến lược
        """
        # Khởi tạo chiến lược dựa trên tên
        strategy = None
        if name.lower() == 'rsi':
            strategy = RSIStrategy(params)
        elif name.lower() == 'macd':
            strategy = MACDStrategy(params)
        elif name.lower() == 'bbands':
            strategy = BollingerBandsStrategy(params)
        elif name.lower() == 'ema_cross':
            strategy = EMACrossStrategy(params)
        elif name.lower() == 'adx':
            strategy = ADXStrategy(params)
        
        # Thêm vào danh sách nếu khởi tạo thành công
        if strategy:
            self.strategies[name] = strategy
            self.strategy_weights[name] = weight
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu kết hợp từ các chiến lược thành phần
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            int: 1 (mua), -1 (bán), 0 (giữ nguyên)
        """
        if not self.strategies:
            return 0
        
        # Thu thập tín hiệu từ các chiến lược
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        for name, strategy in self.strategies.items():
            weight = self.strategy_weights.get(name, 1.0)
            signal = strategy.generate_signal(df)
            
            if signal > 0:
                buy_score += weight
            elif signal < 0:
                sell_score += weight
            
            total_weight += weight
        
        # Chuẩn hóa điểm số
        if total_weight > 0:
            buy_score /= total_weight
            sell_score /= total_weight
        
        # Tạo tín hiệu cuối cùng với ngưỡng tin cậy
        signal = 0
        confidence_threshold = self.params.get('confidence_threshold', 0.5)
        
        if buy_score > confidence_threshold and buy_score > sell_score:
            signal = 1
        elif sell_score > confidence_threshold and sell_score > buy_score:
            signal = -1
        
        return signal

class AdaptiveTrader:
    """
    Hệ thống giao dịch thích ứng theo chế độ thị trường
    """
    
    def __init__(self, regime_detector: MarketRegimeDetector = None, 
               strategy_selector: StrategySelector = None):
        """
        Khởi tạo hệ thống giao dịch thích ứng
        
        Args:
            regime_detector (MarketRegimeDetector): Bộ phát hiện chế độ thị trường
            strategy_selector (StrategySelector): Bộ chọn chiến lược
        """
        self.regime_detector = regime_detector or MarketRegimeDetector()
        self.strategy_selector = strategy_selector or StrategySelector()
        
        # Theo dõi trạng thái
        self.current_regime = None
        self.current_strategy = None
        self.active_trades = []
        
        # Theo dõi hiệu suất
        self.performance_history = []
    
    def process_data(self, df: pd.DataFrame, window: int = 20) -> Tuple[str, Dict, Dict]:
        """
        Xử lý dữ liệu, phát hiện chế độ thị trường và lựa chọn chiến lược
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            window (int): Kích thước cửa sổ để phân tích
            
        Returns:
            Tuple[str, Dict, Dict]: (regime, strategies, risk_params)
        """
        # Phát hiện chế độ thị trường
        if len(df) < window:
            logger.warning(f"Không đủ dữ liệu để phát hiện chế độ thị trường (cần ít nhất {window} nến)")
            regime = "unknown"
        else:
            regime = self.regime_detector.detect_regime(df, window)
        
        # Cập nhật chế độ hiện tại
        self.current_regime = regime
        
        # Lựa chọn chiến lược
        strategies = self.strategy_selector.get_strategies_for_regime(regime)
        
        # Lấy tham số quản lý vốn
        risk_params = self.strategy_selector.get_risk_params(regime)
        
        logger.info(f"Chế độ thị trường hiện tại: {regime}")
        logger.info(f"Chiến lược được chọn: {strategies}")
        
        return regime, strategies, risk_params
    
    def create_strategy(self, strategies: Dict[str, float], regime: str) -> CompositeStrategy:
        """
        Tạo chiến lược kết hợp từ danh sách chiến lược
        
        Args:
            strategies (Dict[str, float]): Ánh xạ tên chiến lược -> trọng số
            regime (str): Chế độ thị trường hiện tại
            
        Returns:
            CompositeStrategy: Chiến lược kết hợp
        """
        strategy_configs = {}
        
        for strat_name, weight in strategies.items():
            # Lấy tham số tối ưu cho chiến lược trong chế độ thị trường này
            params = self.strategy_selector.get_optimal_params(regime, strat_name)
            
            strategy_configs[strat_name] = {
                'weight': weight,
                'params': params,
                'active': True
            }
        
        # Tạo chiến lược kết hợp
        composite_params = {'confidence_threshold': 0.5}
        return CompositeStrategy(strategy_configs, composite_params)
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """
        Tạo tín hiệu giao dịch thích ứng với chế độ thị trường
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            Dict: Thông tin tín hiệu
        """
        # Thêm các chỉ báo kỹ thuật nếu chưa có
        if 'rsi' not in df.columns:
            df = self.regime_detector.add_indicators(df)
        
        # Phát hiện chế độ thị trường và lựa chọn chiến lược
        regime, strategies, risk_params = self.process_data(df)
        
        # Tạo chiến lược kết hợp
        self.current_strategy = self.create_strategy(strategies, regime)
        
        # Tạo tín hiệu
        signal_value = self.current_strategy.generate_signal(df)
        
        # Convert signal to action
        action = "HOLD"
        if signal_value > 0:
            action = "BUY"
        elif signal_value < 0:
            action = "SELL"
        
        signal = {
            'action': action,
            'regime': regime,
            'timestamp': df.index[-1] if isinstance(df.index[-1], datetime) else datetime.now(),
            'price': df['close'].iloc[-1],
            'strategies': strategies,
            'risk_params': risk_params
        }
        
        return signal
    
    def backtest(self, df: pd.DataFrame, initial_balance: float = 10000.0, 
               leverage: int = 5) -> Dict:
        """
        Chạy backtest với hệ thống giao dịch thích ứng
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            initial_balance (float): Số dư ban đầu
            leverage (int): Đòn bẩy
            
        Returns:
            Dict: Kết quả backtest
        """
        # Thêm các chỉ báo kỹ thuật
        if 'rsi' not in df.columns:
            df = self.regime_detector.add_indicators(df)
        
        # Khởi tạo biến theo dõi
        balance = initial_balance
        equity_curve = [initial_balance]
        dates = [df.index[0] if hasattr(df.index[0], 'strftime') else 0]
        trades = []
        current_position = None
        
        # Theo dõi chế độ thị trường
        regime_changes = []
        current_regime = None
        
        # Theo dõi chiến lược
        strategy_uses = {name: 0 for name in ['rsi', 'macd', 'bbands', 'ema_cross', 'adx']}
        
        # Bỏ qua một số nến đầu do cần dữ liệu để tính chỉ báo
        start_idx = 50  # Đủ cho hầu hết chỉ báo
        
        # Chạy backtest
        logger.info(f"Bắt đầu backtest với số dư {initial_balance}...")
        
        for i in range(start_idx, len(df)):
            current_data = df.iloc[:i+1].copy()
            current_date = current_data.index[-1]
            current_price = current_data['close'].iloc[-1]
            
            # Phát hiện chế độ thị trường
            regime, strategies, risk_params = self.process_data(current_data)
            
            # Ghi lại thay đổi chế độ thị trường
            if regime != current_regime:
                regime_changes.append({
                    'timestamp': current_date,
                    'price': current_price,
                    'old_regime': current_regime,
                    'new_regime': regime
                })
                current_regime = regime
            
            # Cập nhật số lần sử dụng chiến lược
            for strat_name in strategies.keys():
                strategy_uses[strat_name] = strategy_uses.get(strat_name, 0) + 1
            
            # Tạo chiến lược kết hợp
            strategy = self.create_strategy(strategies, regime)
            
            # Tạo tín hiệu
            signal = strategy.generate_signal(current_data)
            
            # Lấy tham số quản lý vốn
            risk_percentage = risk_params.get('risk_percentage', 1.0)
            take_profit_pct = risk_params.get('take_profit_pct', 3.0)
            stop_loss_pct = risk_params.get('stop_loss_pct', 1.5)
            trailing_stop = risk_params.get('trailing_stop', False)
            
            # Xử lý vị thế hiện tại
            if current_position:
                # Giả định giá cả có thể thay đổi trong một nến
                if 'high' in current_data.columns and 'low' in current_data.columns:
                    high_price = current_data['high'].iloc[-1]
                    low_price = current_data['low'].iloc[-1]
                else:
                    high_price = current_price * 1.005  # +0.5%
                    low_price = current_price * 0.995   # -0.5%
                
                close_position = False
                exit_reason = ""
                exit_price = current_price  # Giá đóng vị thế mặc định
                
                # Xử lý vị thế BUY
                if current_position['side'] == 'BUY':
                    # Kiểm tra stop loss
                    if low_price <= current_position['stop_loss']:
                        close_position = True
                        exit_reason = 'stop_loss'
                        exit_price = current_position['stop_loss']
                    
                    # Kiểm tra take profit
                    elif high_price >= current_position['take_profit'] and not current_position.get('trailing_active', False):
                        close_position = True
                        exit_reason = 'take_profit'
                        exit_price = current_position['take_profit']
                    
                    # Kiểm tra trailing stop
                    elif trailing_stop:
                        # Cập nhật giá cao nhất
                        if high_price > current_position.get('highest_price', current_position['entry_price']):
                            current_position['highest_price'] = high_price
                            
                            # Kích hoạt trailing stop
                            activation_pct = risk_params.get('trailing_activation', 0.5)
                            activation_threshold = current_position['entry_price'] * (1 + activation_pct / 100)
                            
                            if high_price >= activation_threshold and not current_position.get('trailing_active', False):
                                current_position['trailing_active'] = True
                            
                            # Cập nhật stop loss nếu đã kích hoạt trailing
                            if current_position.get('trailing_active', False):
                                # Đặt stop loss ở 50% của khoảng tăng từ giá ban đầu
                                new_stop = current_position['highest_price'] * 0.99  # 1% dưới giá cao nhất
                                if new_stop > current_position['stop_loss']:
                                    current_position['stop_loss'] = new_stop
                    
                    # Kiểm tra tín hiệu đảo chiều
                    if signal < 0:
                        close_position = True
                        exit_reason = 'signal_reverse'
                
                # Xử lý vị thế SELL
                else:
                    # Kiểm tra stop loss
                    if high_price >= current_position['stop_loss']:
                        close_position = True
                        exit_reason = 'stop_loss'
                        exit_price = current_position['stop_loss']
                    
                    # Kiểm tra take profit
                    elif low_price <= current_position['take_profit'] and not current_position.get('trailing_active', False):
                        close_position = True
                        exit_reason = 'take_profit'
                        exit_price = current_position['take_profit']
                    
                    # Kiểm tra trailing stop
                    elif trailing_stop:
                        # Cập nhật giá thấp nhất
                        if low_price < current_position.get('lowest_price', current_position['entry_price']):
                            current_position['lowest_price'] = low_price
                            
                            # Kích hoạt trailing stop
                            activation_pct = risk_params.get('trailing_activation', 0.5)
                            activation_threshold = current_position['entry_price'] * (1 - activation_pct / 100)
                            
                            if low_price <= activation_threshold and not current_position.get('trailing_active', False):
                                current_position['trailing_active'] = True
                            
                            # Cập nhật stop loss nếu đã kích hoạt trailing
                            if current_position.get('trailing_active', False):
                                # Đặt stop loss ở 50% của khoảng giảm từ giá ban đầu
                                new_stop = current_position['lowest_price'] * 1.01  # 1% trên giá thấp nhất
                                if new_stop < current_position['stop_loss']:
                                    current_position['stop_loss'] = new_stop
                    
                    # Kiểm tra tín hiệu đảo chiều
                    if signal > 0:
                        close_position = True
                        exit_reason = 'signal_reverse'
                
                # Đóng vị thế nếu cần
                if close_position:
                    # Tính lợi nhuận
                    if current_position['side'] == 'BUY':
                        pnl = (exit_price - current_position['entry_price']) * current_position['quantity'] * leverage
                    else:  # SELL
                        pnl = (current_position['entry_price'] - exit_price) * current_position['quantity'] * leverage
                    
                    # Cập nhật số dư
                    balance += pnl
                    
                    # Ghi lại giao dịch
                    trade_info = {
                        'entry_date': current_position['entry_date'],
                        'entry_price': current_position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': exit_price,
                        'side': current_position['side'],
                        'quantity': current_position['quantity'],
                        'pnl': pnl,
                        'roi': pnl / initial_balance * 100,
                        'exit_reason': exit_reason,
                        'regime': current_position['regime'],
                        'leverage': leverage
                    }
                    
                    trades.append(trade_info)
                    current_position = None
            
            # Mở vị thế mới nếu có tín hiệu và không có vị thế hiện tại
            if current_position is None and (signal == 1 or signal == -1):
                # Kiểm tra giới hạn giao dịch theo chế độ thị trường
                max_trades = risk_params.get('max_trades', 999)
                active_trades_in_regime = sum(1 for t in trades[-20:] if t['regime'] == regime and t['exit_date'] > dates[-10])
                
                if active_trades_in_regime < max_trades:
                    # Tính toán kích thước vị thế
                    risk_amount = balance * (risk_percentage / 100)
                    
                    # Mở vị thế mới
                    if signal == 1:  # BUY
                        # Tính stop loss và take profit
                        stop_loss_price = current_price * (1 - stop_loss_pct / 100)
                        take_profit_price = current_price * (1 + take_profit_pct / 100)
                        
                        # Tính số lượng
                        price_delta = current_price - stop_loss_price
                        quantity = risk_amount / (price_delta * leverage) if price_delta > 0 else 0
                        
                        if quantity > 0:
                            current_position = {
                                'side': 'BUY',
                                'entry_price': current_price,
                                'entry_date': current_date,
                                'quantity': quantity,
                                'stop_loss': stop_loss_price,
                                'take_profit': take_profit_price,
                                'regime': regime,
                                'highest_price': current_price,
                                'trailing_active': False
                            }
                    
                    elif signal == -1:  # SELL
                        # Tính stop loss và take profit
                        stop_loss_price = current_price * (1 + stop_loss_pct / 100)
                        take_profit_price = current_price * (1 - take_profit_pct / 100)
                        
                        # Tính số lượng
                        price_delta = stop_loss_price - current_price
                        quantity = risk_amount / (price_delta * leverage) if price_delta > 0 else 0
                        
                        if quantity > 0:
                            current_position = {
                                'side': 'SELL',
                                'entry_price': current_price,
                                'entry_date': current_date,
                                'quantity': quantity,
                                'stop_loss': stop_loss_price,
                                'take_profit': take_profit_price,
                                'regime': regime,
                                'lowest_price': current_price,
                                'trailing_active': False
                            }
            
            # Tính giá trị danh mục hiện tại
            current_equity = balance
            if current_position:
                # Tính lợi nhuận chưa thực hiện
                if current_position['side'] == 'BUY':
                    unrealized_pnl = (current_price - current_position['entry_price']) * current_position['quantity'] * leverage
                else:  # SELL
                    unrealized_pnl = (current_position['entry_price'] - current_price) * current_position['quantity'] * leverage
                
                current_equity += unrealized_pnl
            
            # Ghi lại giá trị danh mục
            equity_curve.append(current_equity)
            dates.append(current_date)
        
        # Đóng vị thế cuối cùng nếu còn
        if current_position:
            # Tính lợi nhuận
            if current_position['side'] == 'BUY':
                pnl = (current_price - current_position['entry_price']) * current_position['quantity'] * leverage
            else:  # SELL
                pnl = (current_position['entry_price'] - current_price) * current_position['quantity'] * leverage
            
            # Cập nhật số dư
            balance += pnl
            
            # Ghi lại giao dịch
            trade_info = {
                'entry_date': current_position['entry_date'],
                'entry_price': current_position['entry_price'],
                'exit_date': current_date,
                'exit_price': current_price,
                'side': current_position['side'],
                'quantity': current_position['quantity'],
                'pnl': pnl,
                'roi': pnl / initial_balance * 100,
                'exit_reason': 'end_of_test',
                'regime': current_position['regime'],
                'leverage': leverage
            }
            
            trades.append(trade_info)
        
        # Tính toán các chỉ số hiệu suất
        metrics = self._calculate_performance_metrics(trades, equity_curve, initial_balance)
        
        # Tính phân phối theo chế độ thị trường
        regime_distribution = {}
        for change in regime_changes:
            regime = change['new_regime']
            regime_distribution[regime] = regime_distribution.get(regime, 0) + 1
        
        # Tính tổng số
        total_regimes = sum(regime_distribution.values()) or 1  # Tránh chia cho 0
        regime_distribution = {k: v / total_regimes * 100 for k, v in regime_distribution.items()}
        
        # Tính hiệu suất theo chế độ thị trường
        regime_performance = {}
        for regime in set([t['regime'] for t in trades if 'regime' in t]):
            regime_trades = [t for t in trades if t.get('regime') == regime]
            if regime_trades:
                win_trades = sum(1 for t in regime_trades if t['pnl'] > 0)
                total_trades = len(regime_trades)
                win_rate = win_trades / total_trades if total_trades > 0 else 0
                
                total_pnl = sum(t['pnl'] for t in regime_trades)
                avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
                
                regime_performance[regime] = {
                    'win_rate': win_rate,
                    'total_trades': total_trades,
                    'total_pnl': total_pnl,
                    'avg_pnl': avg_pnl
                }
        
        # Tạo kết quả
        result = {
            'initial_balance': initial_balance,
            'final_balance': balance,
            'trades': trades,
            'metrics': metrics,
            'equity_curve': equity_curve,
            'dates': [d.strftime('%Y-%m-%d %H:%M:%S') if hasattr(d, 'strftime') else str(d) for d in dates],
            'regime_changes': regime_changes,
            'regime_distribution': regime_distribution,
            'regime_performance': regime_performance,
            'strategy_uses': strategy_uses
        }
        
        # Lưu và trả về kết quả
        self._save_backtest_results(result)
        
        return result
    
    def _calculate_performance_metrics(self, trades: List[Dict], equity_curve: List[float], 
                                     initial_balance: float) -> Dict:
        """
        Tính toán các chỉ số hiệu suất
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            equity_curve (List[float]): Đường cong vốn
            initial_balance (float): Số dư ban đầu
            
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'total_roi': 0
            }
        
        # Các chỉ số cơ bản
        total_trades = len(trades)
        profitable_trades = sum(1 for t in trades if t['pnl'] > 0)
        losing_trades = total_trades - profitable_trades
        
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        total_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        total_loss = sum(t['pnl'] for t in trades if t['pnl'] <= 0)
        
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        
        avg_profit = total_profit / profitable_trades if profitable_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # Tính drawdown
        peak = initial_balance
        drawdowns = []
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            drawdown_pct = (peak - equity) / peak * 100 if peak > 0 else 0
            drawdowns.append(drawdown_pct)
        
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Tính Sharpe Ratio (simplified annual)
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
        
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if returns else 1e-9
        
        sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Tính ROI tổng thể
        final_balance = equity_curve[-1]
        total_roi = (final_balance - initial_balance) / initial_balance * 100
        
        # Tạo kết quả
        metrics = {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_roi': total_roi
        }
        
        return metrics
    
    def _save_backtest_results(self, result: Dict, filename: str = None) -> str:
        """
        Lưu kết quả backtest
        
        Args:
            result (Dict): Kết quả backtest
            filename (str): Tên file (nếu None, sẽ tạo tự động)
            
        Returns:
            str: Đường dẫn đến file kết quả
        """
        # Tạo tên file nếu chưa có
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{RESULT_DIR}/adaptive_backtest_{timestamp}.json"
        else:
            filename = f"{RESULT_DIR}/{filename}"
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Tạo bản sao để xử lý dữ liệu không phải JSON
        serializable_result = {}
        
        # Xử lý từng phần tử để đảm bảo có thể serializable
        for key, value in result.items():
            if key == 'trades':
                serializable_result[key] = []
                for trade in value:
                    serializable_trade = {}
                    for trade_key, trade_value in trade.items():
                        # Xử lý datetime
                        if hasattr(trade_value, 'strftime'):
                            serializable_trade[trade_key] = trade_value.strftime('%Y-%m-%d %H:%M:%S')
                        # Xử lý numpy types
                        elif isinstance(trade_value, (np.integer, np.floating)):
                            serializable_trade[trade_key] = float(trade_value)
                        else:
                            serializable_trade[trade_key] = trade_value
                    serializable_result[key].append(serializable_trade)
            elif key == 'equity_curve':
                serializable_result[key] = [float(x) if isinstance(x, (np.integer, np.floating)) else x for x in value]
            elif key == 'dates':
                serializable_result[key] = [d.strftime('%Y-%m-%d %H:%M:%S') if hasattr(d, 'strftime') else str(d) for d in value]
            elif key == 'regime_changes':
                serializable_result[key] = []
                for change in value:
                    serializable_change = {}
                    for change_key, change_value in change.items():
                        if hasattr(change_value, 'strftime'):
                            serializable_change[change_key] = change_value.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(change_value, (np.integer, np.floating)):
                            serializable_change[change_key] = float(change_value)
                        else:
                            serializable_change[change_key] = change_value
                    serializable_result[key].append(serializable_change)
            elif key == 'regime_performance' or key == 'metrics' or key == 'regime_distribution':
                # Xử lý dictionaries nested
                serializable_result[key] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        serializable_result[key][sub_key] = {}
                        for sub_sub_key, sub_sub_value in sub_value.items():
                            if isinstance(sub_sub_value, (np.integer, np.floating)):
                                serializable_result[key][sub_key][sub_sub_key] = float(sub_sub_value)
                            else:
                                serializable_result[key][sub_key][sub_sub_key] = sub_sub_value
                    elif isinstance(sub_value, (np.integer, np.floating)):
                        serializable_result[key][sub_key] = float(sub_value)
                    else:
                        serializable_result[key][sub_key] = sub_value
            elif isinstance(value, (np.integer, np.floating)):
                # Xử lý numpy types
                serializable_result[key] = float(value)
            else:
                # Loại dữ liệu khác
                serializable_result[key] = value
        
        # Lưu file
        with open(filename, 'w') as f:
            json.dump(serializable_result, f, indent=4)
        
        logger.info(f"Đã lưu kết quả backtest tại: {filename}")
        
        # Lưu trades vào CSV
        if result['trades']:
            csv_file = filename.replace('.json', '_trades.csv')
            pd.DataFrame(result['trades']).to_csv(csv_file, index=False)
            logger.info(f"Đã lưu chi tiết giao dịch tại: {csv_file}")
        
        # Tạo biểu đồ
        self._create_backtest_charts(result, filename.replace('.json', ''))
        
        return filename
    
    def _create_backtest_charts(self, result: Dict, base_filename: str) -> None:
        """
        Tạo các biểu đồ từ kết quả backtest
        
        Args:
            result (Dict): Kết quả backtest
            base_filename (str): Tên file cơ sở cho biểu đồ
        """
        try:
            # 1. Biểu đồ đường cong vốn
            plt.figure(figsize=(12, 6))
            
            # Dùng indices thay vì datetime để tránh lỗi convert
            plt.plot(range(len(result['equity_curve'])), result['equity_curve'], label='Portfolio Value', color='blue')
            
            # Thêm điểm đánh dấu chế độ thị trường
            regime_colors = {
                'trending_up': 'green',
                'trending_down': 'red',
                'ranging': 'orange',
                'volatile': 'purple',
                'quiet': 'gray'
            }
            
            # Tạo đánh dấu cho các thay đổi chế độ
            for i, change in enumerate(result['regime_changes']):
                # Tìm chỉ số gần nhất
                # Do vấn đề với datetime, dùng chỉ số thay vì thời gian
                date_str = change['timestamp'] if isinstance(change['timestamp'], str) else str(change['timestamp'])
                idx = result['dates'].index(date_str) if date_str in result['dates'] else i * 20
                
                # Vẽ đường dọc cho mỗi thay đổi chế độ
                color = regime_colors.get(change['new_regime'], 'black')
                plt.axvline(x=idx, color=color, linestyle='--', alpha=0.5)
                
                # Thêm chú thích
                if idx < len(result['equity_curve']):
                    plt.text(idx, result['equity_curve'][idx] * 1.02, 
                           change['new_regime'], 
                           rotation=90, color=color, alpha=0.7)
            
            # Thêm chi tiết biểu đồ
            plt.title('Equity Curve with Market Regimes')
            plt.xlabel('Trading Periods')
            plt.ylabel('Portfolio Value')
            plt.grid(True, alpha=0.3)
            
            # Thêm chú thích về chế độ thị trường
            handles = [plt.Line2D([0], [0], color=color, linestyle='--', label=regime) 
                     for regime, color in regime_colors.items()]
            plt.legend(handles=handles, loc='upper left')
            
            # Xoay nhãn trục x
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Lưu biểu đồ
            equity_chart = f"{base_filename}_equity.png"
            plt.savefig(equity_chart)
            plt.close()
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ equity curve: {e}")
            # Tiếp tục để không dừng toàn bộ quá trình
        
        try:
            # 2. Biểu đồ hiệu suất theo chế độ thị trường
            plt.figure(figsize=(10, 6))
            
            # Vẽ biểu đồ win rate theo chế độ
            regimes = list(result['regime_performance'].keys())
            win_rates = [float(result['regime_performance'][r]['win_rate']) * 100 for r in regimes]
            trade_counts = [int(result['regime_performance'][r]['total_trades']) for r in regimes]
            
            # Tạo màu cho từng regime
            colors = [regime_colors.get(r, 'gray') for r in regimes]
            
            # Vẽ biểu đồ cột
            ax = plt.subplot(111)
            bars = ax.bar(regimes, win_rates, color=colors, alpha=0.7)
            
            # Thêm số lượng giao dịch
            for i, bar in enumerate(bars):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'n={trade_counts[i]}',
                       ha='center', va='bottom', rotation=0)
            
            # Thêm chi tiết
            plt.title('Win Rate by Market Regime')
            plt.xlabel('Market Regime')
            plt.ylabel('Win Rate (%)')
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            
            # Lưu biểu đồ
            regime_chart = f"{base_filename}_regimes.png"
            plt.savefig(regime_chart)
            plt.close()
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ win rate: {e}")
            
        try:
            # 3. Biểu đồ phân phối chế độ thị trường
            plt.figure(figsize=(8, 8))
            
            # Vẽ biểu đồ tròn
            regimes = list(result['regime_distribution'].keys())
            values = [float(v) for v in result['regime_distribution'].values()]
            
            # Tạo màu cho từng regime
            colors = [regime_colors.get(r, 'gray') for r in regimes]
            
            # Vẽ biểu đồ
            plt.pie(values, labels=regimes, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('Market Regime Distribution')
            plt.tight_layout()
            
            # Lưu biểu đồ
            distribution_chart = f"{base_filename}_distribution.png"
            plt.savefig(distribution_chart)
            plt.close()
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân phối: {e}")
        
        logger.info(f"Đã tạo các biểu đồ backtest tại: {base_filename}_*.png")

def load_data(file_path: str) -> pd.DataFrame:
    """
    Tải dữ liệu từ file CSV
    
    Args:
        file_path (str): Đường dẫn đến file dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu
    """
    try:
        df = pd.read_csv(file_path)
        
        # Chuyển đổi timestamp thành datetime nếu có
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        return df
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu từ {file_path}: {e}")
        return None

def find_data_files(data_dir: str = 'real_data', pattern: str = '*sample.csv') -> List[str]:
    """
    Tìm các file dữ liệu phù hợp với mẫu
    
    Args:
        data_dir (str): Thư mục chứa dữ liệu
        pattern (str): Mẫu tên file
        
    Returns:
        List[str]: Danh sách đường dẫn đến các file
    """
    import glob
    
    if not os.path.exists(data_dir):
        logger.error(f"Thư mục {data_dir} không tồn tại")
        return []
    
    # Tìm các file
    pattern_path = os.path.join(data_dir, pattern)
    files = glob.glob(pattern_path)
    
    return files

def train_regime_detector(data_files: List[str] = None) -> MarketRegimeDetector:
    """
    Huấn luyện bộ phát hiện chế độ thị trường
    
    Args:
        data_files (List[str]): Danh sách đường dẫn đến các file dữ liệu
        
    Returns:
        MarketRegimeDetector: Bộ phát hiện đã huấn luyện
    """
    # Tìm file dữ liệu nếu chưa chỉ định
    if data_files is None:
        data_files = find_data_files()
    
    if not data_files:
        logger.error("Không tìm thấy file dữ liệu nào")
        return MarketRegimeDetector(use_ml=False)
    
    # Khởi tạo bộ phát hiện
    detector = MarketRegimeDetector(use_ml=False)
    
    # Chuẩn bị dữ liệu huấn luyện
    training_data = detector.prepare_training_data(data_files)
    
    if len(training_data) < 100:
        logger.warning(f"Không đủ dữ liệu huấn luyện: {len(training_data)} mẫu")
        return detector
    
    # Huấn luyện mô hình
    model_path = os.path.join(ML_MODEL_DIR, 'regime_detector.joblib')
    detector.train(training_data, save_path=model_path)
    
    return detector

def main():
    """Hàm chính để demo hệ thống giao dịch thích ứng"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hệ thống giao dịch thích ứng theo chế độ thị trường với ML')
    parser.add_argument('--mode', choices=['train', 'backtest', 'both'], default='both',
                      help='Chế độ hoạt động: train (huấn luyện mô hình), backtest (chạy backtest), both (cả hai)')
    parser.add_argument('--symbol', type=str, default='BTCUSDT',
                      help='Cặp giao dịch (chỉ sử dụng trong chế độ backtest)')
    parser.add_argument('--interval', type=str, default='1h',
                      help='Khung thời gian (chỉ sử dụng trong chế độ backtest)')
    parser.add_argument('--balance', type=float, default=10000.0,
                      help='Số dư ban đầu (chỉ sử dụng trong chế độ backtest)')
    parser.add_argument('--leverage', type=int, default=5,
                      help='Đòn bẩy (chỉ sử dụng trong chế độ backtest)')
    parser.add_argument('--data-dir', type=str, default='real_data',
                      help='Thư mục chứa dữ liệu')
    
    args = parser.parse_args()
    
    # Tìm file dữ liệu
    data_files = find_data_files(args.data_dir)
    
    if not data_files:
        logger.error(f"Không tìm thấy file dữ liệu nào trong thư mục {args.data_dir}")
        return
    
    # Huấn luyện mô hình nếu cần
    if args.mode in ['train', 'both']:
        logger.info("Huấn luyện bộ phát hiện chế độ thị trường...")
        detector = train_regime_detector(data_files)
    else:
        # Tải mô hình từ file
        model_path = os.path.join(ML_MODEL_DIR, 'regime_detector.joblib')
        if os.path.exists(model_path):
            detector = MarketRegimeDetector(use_ml=True, model_path=model_path)
        else:
            logger.warning(f"Không tìm thấy mô hình tại {model_path}. Sử dụng phương pháp rule-based.")
            detector = MarketRegimeDetector(use_ml=False)
    
    # Chạy backtest nếu cần
    if args.mode in ['backtest', 'both']:
        # Tìm file dữ liệu phù hợp
        data_file = None
        for file_path in data_files:
            if args.symbol in file_path and args.interval in file_path:
                data_file = file_path
                break
        
        if data_file is None:
            logger.error(f"Không tìm thấy dữ liệu cho {args.symbol} {args.interval}")
            return
        
        # Tải dữ liệu
        df = load_data(data_file)
        if df is None:
            return
        
        # Khởi tạo hệ thống giao dịch
        strategy_selector = StrategySelector()
        trader = AdaptiveTrader(detector, strategy_selector)
        
        # Chạy backtest
        logger.info(f"Chạy backtest cho {args.symbol} {args.interval}...")
        result = trader.backtest(df, initial_balance=args.balance, leverage=args.leverage)
        
        # In kết quả
        logger.info(f"Kết quả backtest:")
        logger.info(f"Số dư ban đầu: ${args.balance:.2f}")
        logger.info(f"Số dư cuối: ${result['final_balance']:.2f}")
        logger.info(f"ROI: {result['metrics']['total_roi']:.2f}%")
        logger.info(f"Tổng số giao dịch: {result['metrics']['total_trades']}")
        logger.info(f"Tỷ lệ thắng: {result['metrics']['win_rate']:.2%}")
        logger.info(f"Drawdown tối đa: {result['metrics']['max_drawdown']:.2f}%")
        logger.info(f"Sharpe ratio: {result['metrics']['sharpe_ratio']:.2f}")
        
        # Hiệu suất theo chế độ thị trường
        logger.info("Hiệu suất theo chế độ thị trường:")
        for regime, perf in result['regime_performance'].items():
            logger.info(f"  {regime}: Win rate {perf['win_rate']:.2%}, {perf['total_trades']} giao dịch")
        
        # Phân phối chế độ thị trường
        logger.info("Phân phối chế độ thị trường:")
        for regime, pct in result['regime_distribution'].items():
            logger.info(f"  {regime}: {pct:.1f}%")

if __name__ == "__main__":
    main()