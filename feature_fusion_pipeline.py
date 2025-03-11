#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Feature Fusion Pipeline - Quy trình tổng hợp đặc trưng cho dự đoán thị trường
"""

import os
import json
import logging
import pickle
from enum import Enum
from typing import Dict, List, Tuple, Union, Optional, Any, Callable

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Thư viện xử lý dữ liệu và chia các mẫu huấn luyện
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
from sklearn.impute import SimpleImputer

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('feature_fusion')

# Constants
DEFAULT_FEATURE_GROUPS = [
    "price", "volume", "momentum", "volatility", "trend", "pattern", "support_resistance"
]

# Định nghĩa các loại thị trường
class MarketType(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    NEUTRAL = "neutral"

class FeatureFusionPipeline:
    """
    Pipeline tổng hợp và xử lý đặc trưng từ nhiều nguồn 
    và thuật toán khác nhau để chuẩn bị dữ liệu cho các mô hình ML
    """
    
    def __init__(
        self, 
        feature_groups: Optional[List[str]] = None,
        price_features: bool = True,
        volume_features: bool = True,
        trend_features: bool = True,
        volatility_features: bool = True,
        pattern_features: bool = True,
        orderflow_features: bool = False,
        use_ta_lib: bool = True,
        use_pca: bool = False,
        pca_components: int = 10,
        feature_selection: Optional[str] = None,
        n_features_to_select: int = 20,
        scaling_method: str = "standard",
        handle_missing: bool = True,
        cache_dir: str = 'data/cache'
    ):
        """
        Khởi tạo pipeline tổng hợp đặc trưng
        
        Args:
            feature_groups: Danh sách nhóm đặc trưng sử dụng
            price_features: Sử dụng đặc trưng giá
            volume_features: Sử dụng đặc trưng khối lượng
            trend_features: Sử dụng đặc trưng xu hướng
            volatility_features: Sử dụng đặc trưng biến động
            pattern_features: Sử dụng đặc trưng mẫu hình
            orderflow_features: Sử dụng đặc trưng dòng lệnh
            use_ta_lib: Sử dụng thư viện TA-Lib
            use_pca: Sử dụng PCA để giảm chiều dữ liệu
            pca_components: Số thành phần PCA
            feature_selection: Phương pháp chọn đặc trưng: 'mutual_info', 'f_regression', None
            n_features_to_select: Số đặc trưng để chọn
            scaling_method: Phương pháp chuẩn hóa: 'standard', 'minmax', 'robust'
            handle_missing: Xử lý giá trị bị thiếu
            cache_dir: Thư mục lưu cache
        """
        # Thiết lập các nhóm đặc trưng
        self.feature_groups = feature_groups if feature_groups else DEFAULT_FEATURE_GROUPS
        
        # Cài đặt tùy chọn đặc trưng
        self.price_features = price_features
        self.volume_features = volume_features
        self.trend_features = trend_features
        self.volatility_features = volatility_features
        self.pattern_features = pattern_features
        self.orderflow_features = orderflow_features
        
        # Cài đặt kỹ thuật
        self.use_ta_lib = use_ta_lib
        self.use_pca = use_pca
        self.pca_components = pca_components
        self.feature_selection = feature_selection
        self.n_features_to_select = n_features_to_select
        self.scaling_method = scaling_method
        self.handle_missing = handle_missing
        
        # Thư mục cache
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Đường dẫn model
        self.model_path = os.path.join(cache_dir, 'feature_fusion_model.pkl')
        
        # Khởi tạo các biến pipeline
        self.scaler = None
        self.pca_model = None
        self.feature_selector = None
        self.pipeline = None
        self.selected_features = []
        self.feature_importance = {}
        
        # Danh sách đặc trưng cơ bản và nâng cao
        self.basic_features = []
        self.advanced_features = []
        self.technical_features = []
        
        # Khởi tạo pipeline
        self._initialize_pipeline()
        
        logger.info(f"Đã khởi tạo FeatureFusionPipeline với {len(self.feature_groups)} nhóm đặc trưng")
    
    def _initialize_pipeline(self) -> None:
        """
        Khởi tạo pipeline chuyển đổi đặc trưng
        """
        steps = []
        
        # Xử lý dữ liệu thiếu
        if self.handle_missing:
            steps.append(('imputer', SimpleImputer(strategy='mean')))
        
        # Chuẩn hóa đặc trưng
        if self.scaling_method == 'standard':
            self.scaler = StandardScaler()
        elif self.scaling_method == 'minmax':
            self.scaler = MinMaxScaler()
        elif self.scaling_method == 'robust':
            self.scaler = RobustScaler()
        else:
            self.scaler = StandardScaler()
        
        steps.append(('scaler', self.scaler))
        
        # Chọn đặc trưng
        if self.feature_selection == 'mutual_info':
            self.feature_selector = SelectKBest(
                mutual_info_regression, k=self.n_features_to_select
            )
            steps.append(('feature_selection', self.feature_selector))
        elif self.feature_selection == 'f_regression':
            self.feature_selector = SelectKBest(
                f_regression, k=self.n_features_to_select
            )
            steps.append(('feature_selection', self.feature_selector))
        
        # Giảm chiều với PCA
        if self.use_pca:
            self.pca_model = PCA(n_components=self.pca_components)
            steps.append(('pca', self.pca_model))
        
        # Tạo pipeline
        self.pipeline = Pipeline(steps)
    
    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo các đặc trưng từ dữ liệu chuỗi thời gian
        
        Args:
            df: DataFrame dữ liệu giá
        
        Returns:
            DataFrame chứa tất cả các đặc trưng
        """
        features_df = df.copy()
        
        # Kiểm tra các cột cần thiết
        required_columns = ['open', 'high', 'low', 'close']
        if not all(col in features_df.columns for col in required_columns):
            logger.warning(f"Thiếu các cột cần thiết: {required_columns}")
            # Tạo giả lập nếu thiếu
            if 'close' in features_df.columns:
                if 'open' not in features_df.columns:
                    features_df['open'] = features_df['close'].shift(1)
                if 'high' not in features_df.columns:
                    features_df['high'] = features_df['close'] * 1.01
                if 'low' not in features_df.columns:
                    features_df['low'] = features_df['close'] * 0.99
        
        # Thêm đặc trưng giá
        if self.price_features and 'price' in self.feature_groups:
            features_df = self._add_price_features(features_df)
        
        # Thêm đặc trưng khối lượng
        if self.volume_features and 'volume' in self.feature_groups and 'volume' in features_df.columns:
            features_df = self._add_volume_features(features_df)
        
        # Thêm đặc trưng xu hướng
        if self.trend_features and 'trend' in self.feature_groups:
            features_df = self._add_trend_features(features_df)
        
        # Thêm đặc trưng biến động
        if self.volatility_features and 'volatility' in self.feature_groups:
            features_df = self._add_volatility_features(features_df)
        
        # Thêm đặc trưng mẫu hình
        if self.pattern_features and 'pattern' in self.feature_groups:
            features_df = self._add_pattern_features(features_df)
        
        # Thêm đặc trưng hỗ trợ/kháng cự
        if 'support_resistance' in self.feature_groups:
            features_df = self._add_support_resistance_features(features_df)
        
        # Thêm đặc trưng dòng lệnh (orderflow)
        if self.orderflow_features and 'volume' in features_df.columns:
            features_df = self._add_orderflow_features(features_df)
        
        # Thêm đặc trưng với TALib
        if self.use_ta_lib:
            features_df = self._add_talib_features(features_df)
        
        # Xử lý giá trị bị thiếu và vô hạn
        features_df = self._handle_invalid_values(features_df)
        
        # Lọc các cột đặc trưng (loại bỏ các cột không phải đặc trưng)
        feature_cols = [col for col in features_df.columns if col not in 
                       ['open', 'high', 'low', 'close', 'volume', 'timestamp', 'date']]
        
        # Cập nhật danh sách đặc trưng
        self.basic_features = [col for col in feature_cols if not (col.startswith('ta_') or 
                                                                 col.startswith('pattern_') or 
                                                                 col.startswith('sr_'))]
        self.technical_features = [col for col in feature_cols if col.startswith('ta_')]
        self.advanced_features = [col for col in feature_cols if col.startswith('pattern_') or 
                                 col.startswith('sr_')]
        
        return features_df
    
    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các đặc trưng liên quan đến giá
        
        Args:
            df: DataFrame dữ liệu

        Returns:
            DataFrame với đặc trưng giá được thêm vào
        """
        # Kiểm tra các cột cần thiết
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            logger.warning("Thiếu các cột giá cần thiết")
            return df
        
        # Tạo DataFrame mới để thay đổi
        features_df = df.copy()
        
        # Log returns
        features_df['log_return'] = np.log(features_df['close'] / features_df['close'].shift(1))
        
        # Return percentage
        features_df['pct_change'] = features_df['close'].pct_change()
        
        # Moving Averages
        for window in [5, 10, 20, 50, 200]:
            features_df[f'ma_{window}'] = features_df['close'].rolling(window=window).mean()
            
            # Khoảng cách đến MA
            features_df[f'dist_to_ma_{window}'] = (features_df['close'] / features_df[f'ma_{window}'] - 1)
        
        # Biến động trong nến
        features_df['candle_range'] = (features_df['high'] - features_df['low']) / features_df['close']
        features_df['body_size'] = abs(features_df['open'] - features_df['close']) / features_df['close']
        features_df['upper_shadow'] = (features_df['high'] - features_df[['open', 'close']].max(axis=1)) / features_df['close']
        features_df['lower_shadow'] = (features_df[['open', 'close']].min(axis=1) - features_df['low']) / features_df['close']
        
        # Close Location Value
        features_df['clv'] = ((features_df['close'] - features_df['low']) - (features_df['high'] - features_df['close'])) / (features_df['high'] - features_df['low'])
        
        # High/Low/Close 1, 3, 5 days ago
        for i in [1, 3, 5]:
            features_df[f'close_{i}d_ago'] = features_df['close'].shift(i)
            features_df[f'high_{i}d_ago'] = features_df['high'].shift(i)
            features_df[f'low_{i}d_ago'] = features_df['low'].shift(i)
            
            # Percentage changes for periods
            features_df[f'pct_change_{i}d'] = features_df['close'].pct_change(periods=i)
        
        return features_df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các đặc trưng liên quan đến khối lượng
        
        Args:
            df: DataFrame dữ liệu

        Returns:
            DataFrame với đặc trưng khối lượng được thêm vào
        """
        if 'volume' not in df.columns:
            logger.warning("Thiếu cột volume, không thể thêm đặc trưng khối lượng")
            return df
        
        features_df = df.copy()
        
        # Volume Moving Averages
        for window in [5, 10, 20, 50]:
            features_df[f'volume_ma_{window}'] = features_df['volume'].rolling(window=window).mean()
            
            # Relative volume
            features_df[f'relative_volume_{window}'] = features_df['volume'] / features_df[f'volume_ma_{window}']
        
        # Volume Rate of Change
        features_df['volume_roc_1'] = features_df['volume'].pct_change(periods=1)
        features_df['volume_roc_5'] = features_df['volume'].pct_change(periods=5)
        
        # On-balance Volume (OBV)
        features_df['obv'] = 0
        features_df.loc[1:, 'obv'] = np.where(
            features_df['close'] > features_df['close'].shift(1),
            features_df['volume'],
            np.where(
                features_df['close'] < features_df['close'].shift(1),
                -features_df['volume'],
                0
            )
        ).cumsum()
        
        # Chaikin Money Flow (CMF)
        period = 20
        mf_volume = ((features_df['close'] - features_df['low']) - (features_df['high'] - features_df['close'])) / (features_df['high'] - features_df['low']) * features_df['volume']
        features_df['cmf'] = mf_volume.rolling(window=period).sum() / features_df['volume'].rolling(window=period).sum()
        
        # Price-Volume Trend
        features_df['pvt'] = (features_df['close'].pct_change() * features_df['volume']).cumsum()
        
        # VWAP
        features_df['vwap'] = (features_df['close'] * features_df['volume']).cumsum() / features_df['volume'].cumsum()
        
        # Volume Oscillator
        features_df['volume_oscillator'] = (
            features_df['volume_ma_5'] - features_df['volume_ma_20']
        ) / features_df['volume_ma_20']
        
        return features_df
    
    def _add_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các đặc trưng xu hướng
        
        Args:
            df: DataFrame dữ liệu

        Returns:
            DataFrame với đặc trưng xu hướng được thêm vào
        """
        features_df = df.copy()
        
        # ADX (Average Directional Index) - Mô phỏng
        # Thật ra nên dùng TALib cho chính xác
        window = 14
        
        # Tính toán TR (True Range)
        features_df['tr'] = np.maximum(
            features_df['high'] - features_df['low'],
            np.maximum(
                abs(features_df['high'] - features_df['close'].shift(1)),
                abs(features_df['low'] - features_df['close'].shift(1))
            )
        )
        
        # Tính toán +DM và -DM
        features_df['plus_dm'] = np.where(
            (features_df['high'] - features_df['high'].shift(1)) > (features_df['low'].shift(1) - features_df['low']),
            np.maximum(features_df['high'] - features_df['high'].shift(1), 0),
            0
        )
        features_df['minus_dm'] = np.where(
            (features_df['low'].shift(1) - features_df['low']) > (features_df['high'] - features_df['high'].shift(1)),
            np.maximum(features_df['low'].shift(1) - features_df['low'], 0),
            0
        )
        
        # Tính toán ATR, +DI và -DI
        features_df['atr'] = features_df['tr'].rolling(window=window).mean()
        features_df['plus_di'] = 100 * (features_df['plus_dm'].rolling(window=window).mean() / features_df['atr'])
        features_df['minus_di'] = 100 * (features_df['minus_dm'].rolling(window=window).mean() / features_df['atr'])
        
        # Tính toán DX và ADX
        features_df['dx'] = 100 * abs(features_df['plus_di'] - features_df['minus_di']) / (features_df['plus_di'] + features_df['minus_di'])
        features_df['adx'] = features_df['dx'].rolling(window=window).mean()
        
        # Trend Strength Indicator
        features_df['trend_strength'] = abs(features_df['plus_di'] - features_df['minus_di'])
        
        # Linear Regression Slope
        def rolling_slope(y):
            x = np.arange(len(y))
            return np.polyfit(x, y, 1)[0]
        
        for window in [10, 20, 50]:
            features_df[f'slope_{window}'] = features_df['close'].rolling(window=window).apply(
                rolling_slope, raw=True
            )
        
        # Supertrend (mô phỏng đơn giản)
        atr_multiplier = 3.0
        features_df['upper_band'] = ((features_df['high'] + features_df['low']) / 2) + (atr_multiplier * features_df['atr'])
        features_df['lower_band'] = ((features_df['high'] + features_df['low']) / 2) - (atr_multiplier * features_df['atr'])
        
        # Phân loại xu hướng từ band
        for i in range(1, len(features_df)):
            if features_df.iloc[i]['close'] <= features_df.iloc[i]['upper_band']:
                features_df.loc[features_df.index[i], 'supertrend'] = features_df.iloc[i]['upper_band']
            else:
                features_df.loc[features_df.index[i], 'supertrend'] = features_df.iloc[i]['lower_band']
                
        features_df['supertrend_direction'] = np.where(features_df['close'] > features_df['supertrend'], 1, -1)
        
        # Thêm MACD simplified
        ema12 = features_df['close'].ewm(span=12, adjust=False).mean()
        ema26 = features_df['close'].ewm(span=26, adjust=False).mean()
        features_df['macd'] = ema12 - ema26
        features_df['macd_signal'] = features_df['macd'].ewm(span=9, adjust=False).mean()
        features_df['macd_hist'] = features_df['macd'] - features_df['macd_signal']
        
        # Thêm đặc trưng Ichimoku (đơn giản hóa)
        high_9 = features_df['high'].rolling(window=9).max()
        low_9 = features_df['low'].rolling(window=9).min()
        features_df['tenkan_sen'] = (high_9 + low_9) / 2
        
        high_26 = features_df['high'].rolling(window=26).max()
        low_26 = features_df['low'].rolling(window=26).min()
        features_df['kijun_sen'] = (high_26 + low_26) / 2
        
        features_df['senkou_span_a'] = ((features_df['tenkan_sen'] + features_df['kijun_sen']) / 2).shift(26)
        
        high_52 = features_df['high'].rolling(window=52).max()
        low_52 = features_df['low'].rolling(window=52).min()
        features_df['senkou_span_b'] = ((high_52 + low_52) / 2).shift(26)
        features_df['chikou_span'] = features_df['close'].shift(-26)
        
        return features_df
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các đặc trưng liên quan đến biến động
        
        Args:
            df: DataFrame dữ liệu

        Returns:
            DataFrame với đặc trưng biến động được thêm vào
        """
        features_df = df.copy()
        
        # ATR nếu chưa có từ _add_trend_features
        if 'atr' not in features_df.columns:
            window = 14
            # Tính toán TR (True Range)
            features_df['tr'] = np.maximum(
                features_df['high'] - features_df['low'],
                np.maximum(
                    abs(features_df['high'] - features_df['close'].shift(1)),
                    abs(features_df['low'] - features_df['close'].shift(1))
                )
            )
            features_df['atr'] = features_df['tr'].rolling(window=window).mean()
        
        # Normalized ATR (ATR / Close Price)
        features_df['normalized_atr'] = features_df['atr'] / features_df['close']
        
        # Biến động lịch sử
        for window in [5, 10, 20, 50]:
            # Standard Deviation
            features_df[f'close_std_{window}'] = features_df['close'].rolling(window=window).std()
            features_df[f'close_std_pct_{window}'] = features_df[f'close_std_{window}'] / features_df['close']
            
            # Parkinson's Volatility
            features_df[f'parkinsons_{window}'] = (1.0 / (4.0 * np.log(2.0))) * (
                np.log(features_df['high'] / features_df['low'])**2
            ).rolling(window=window).mean()
            
            # Historical Volatility (annualized)
            features_df[f'hist_vol_{window}'] = features_df['log_return'].rolling(window=window).std() * np.sqrt(252)
        
        # Bollinger Bands
        window = 20
        features_df['bb_middle'] = features_df['close'].rolling(window=window).mean()
        features_df['bb_std'] = features_df['close'].rolling(window=window).std()
        features_df['bb_upper'] = features_df['bb_middle'] + (2 * features_df['bb_std'])
        features_df['bb_lower'] = features_df['bb_middle'] - (2 * features_df['bb_std'])
        features_df['bb_width'] = (features_df['bb_upper'] - features_df['bb_lower']) / features_df['bb_middle']
        features_df['bb_pct'] = (features_df['close'] - features_df['bb_lower']) / (features_df['bb_upper'] - features_df['bb_lower'])
        
        # Donchian Channels
        for window in [20, 50]:
            features_df[f'donchian_high_{window}'] = features_df['high'].rolling(window=window).max()
            features_df[f'donchian_low_{window}'] = features_df['low'].rolling(window=window).min()
            features_df[f'donchian_mid_{window}'] = (features_df[f'donchian_high_{window}'] + features_df[f'donchian_low_{window}']) / 2
            features_df[f'donchian_width_{window}'] = (features_df[f'donchian_high_{window}'] - features_df[f'donchian_low_{window}']) / features_df[f'donchian_mid_{window}']
        
        # Ulcer Index - đo lường sự suy giảm từ điểm cao nhất
        window = 14
        features_df['price_max'] = features_df['close'].rolling(window=window).max()
        features_df['percentage_drawdown'] = (features_df['close'] / features_df['price_max'] - 1.0) * 100.0
        features_df['squared_drawdown'] = features_df['percentage_drawdown'] ** 2
        features_df['ulcer_index'] = np.sqrt(features_df['squared_drawdown'].rolling(window=window).mean())
        
        # Keltner Channels
        features_df['keltner_middle'] = features_df['close'].rolling(window=20).mean()
        features_df['keltner_upper'] = features_df['keltner_middle'] + (2 * features_df['atr'])
        features_df['keltner_lower'] = features_df['keltner_middle'] - (2 * features_df['atr'])
        features_df['keltner_width'] = (features_df['keltner_upper'] - features_df['keltner_lower']) / features_df['keltner_middle']
        
        # Squeeze Momentum 
        features_df['squeeze'] = np.where(
            (features_df['bb_lower'] > features_df['keltner_lower']) & 
            (features_df['bb_upper'] < features_df['keltner_upper']),
            1, 0
        )
        
        return features_df
    
    def _add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các đặc trưng mẫu hình
        
        Args:
            df: DataFrame dữ liệu

        Returns:
            DataFrame với đặc trưng mẫu hình được thêm vào
        """
        features_df = df.copy()
        
        # Mẫu hình nến đơn giản
        
        # Doji
        features_df['pattern_doji'] = np.where(
            abs(features_df['open'] - features_df['close']) <= 0.1 * (features_df['high'] - features_df['low']),
            1, 0
        )
        
        # Hammer
        features_df['pattern_hammer'] = np.where(
            (features_df['close'] > features_df['open']) &
            ((features_df['high'] - features_df['close']) < 0.1 * (features_df['high'] - features_df['low'])) &
            ((features_df['open'] - features_df['low']) > 0.6 * (features_df['high'] - features_df['low'])),
            1, 0
        )
        
        # Shooting Star
        features_df['pattern_shooting_star'] = np.where(
            (features_df['close'] < features_df['open']) &
            ((features_df['high'] - features_df['open']) > 0.6 * (features_df['high'] - features_df['low'])) &
            ((features_df['close'] - features_df['low']) < 0.1 * (features_df['high'] - features_df['low'])),
            1, 0
        )
        
        # Engulfing
        features_df['pattern_bullish_engulfing'] = np.where(
            (features_df['close'].shift(1) < features_df['open'].shift(1)) &
            (features_df['close'] > features_df['open']) &
            (features_df['close'] > features_df['open'].shift(1)) &
            (features_df['open'] < features_df['close'].shift(1)),
            1, 0
        )
        
        features_df['pattern_bearish_engulfing'] = np.where(
            (features_df['close'].shift(1) > features_df['open'].shift(1)) &
            (features_df['close'] < features_df['open']) &
            (features_df['close'] < features_df['open'].shift(1)) &
            (features_df['open'] > features_df['close'].shift(1)),
            1, 0
        )
        
        # Phá vỡ kênh giá
        # Trước tiên cần các mức MA
        if 'ma_20' not in features_df.columns:
            features_df['ma_20'] = features_df['close'].rolling(window=20).mean()
        if 'ma_50' not in features_df.columns:
            features_df['ma_50'] = features_df['close'].rolling(window=50).mean()
        
        # Breakout trên MA
        features_df['pattern_ma20_breakout_up'] = np.where(
            (features_df['close'].shift(1) < features_df['ma_20'].shift(1)) &
            (features_df['close'] > features_df['ma_20']),
            1, 0
        )
        
        features_df['pattern_ma20_breakout_down'] = np.where(
            (features_df['close'].shift(1) > features_df['ma_20'].shift(1)) &
            (features_df['close'] < features_df['ma_20']),
            1, 0
        )
        
        features_df['pattern_ma50_breakout_up'] = np.where(
            (features_df['close'].shift(1) < features_df['ma_50'].shift(1)) &
            (features_df['close'] > features_df['ma_50']),
            1, 0
        )
        
        features_df['pattern_ma50_breakout_down'] = np.where(
            (features_df['close'].shift(1) > features_df['ma_50'].shift(1)) &
            (features_df['close'] < features_df['ma_50']),
            1, 0
        )
        
        # Phá vỡ Bollinger Band
        if 'bb_upper' not in features_df.columns or 'bb_lower' not in features_df.columns:
            window = 20
            features_df['bb_middle'] = features_df['close'].rolling(window=window).mean()
            features_df['bb_std'] = features_df['close'].rolling(window=window).std()
            features_df['bb_upper'] = features_df['bb_middle'] + (2 * features_df['bb_std'])
            features_df['bb_lower'] = features_df['bb_middle'] - (2 * features_df['bb_std'])
        
        features_df['pattern_bb_breakout_up'] = np.where(
            (features_df['close'].shift(1) < features_df['bb_upper'].shift(1)) &
            (features_df['close'] > features_df['bb_upper']),
            1, 0
        )
        
        features_df['pattern_bb_breakout_down'] = np.where(
            (features_df['close'].shift(1) > features_df['bb_lower'].shift(1)) &
            (features_df['close'] < features_df['bb_lower']),
            1, 0
        )
        
        # Mức đảo chiều
        
        # Inside Bar
        features_df['pattern_inside_bar'] = np.where(
            (features_df['high'] < features_df['high'].shift(1)) &
            (features_df['low'] > features_df['low'].shift(1)),
            1, 0
        )
        
        # Outside Bar
        features_df['pattern_outside_bar'] = np.where(
            (features_df['high'] > features_df['high'].shift(1)) &
            (features_df['low'] < features_df['low'].shift(1)),
            1, 0
        )
        
        # Head and Shoulders - phát hiện đơn giản
        window = 10
        for i in range(window, len(features_df) - window):
            # Lấy cửa sổ dữ liệu
            window_data = features_df.iloc[i-window:i+window+1]
            
            # Tìm các điểm cực đại cục bộ
            peaks = []
            for j in range(1, len(window_data) - 1):
                if (window_data.iloc[j]['high'] > window_data.iloc[j-1]['high'] and 
                    window_data.iloc[j]['high'] > window_data.iloc[j+1]['high']):
                    peaks.append((j, window_data.iloc[j]['high']))
            
            # Nếu có ít nhất 3 đỉnh
            if len(peaks) >= 3:
                # Sắp xếp theo chiều cao
                peaks.sort(key=lambda x: x[1], reverse=True)
                head = peaks[0]
                
                # Tìm vai trái và phải
                left_shoulders = []
                right_shoulders = []
                
                for p in peaks[1:]:
                    if p[0] < head[0]:
                        left_shoulders.append(p)
                    else:
                        right_shoulders.append(p)
                
                # Nếu có ít nhất một vai trái và một vai phải
                if left_shoulders and right_shoulders:
                    left_shoulder = max(left_shoulders, key=lambda x: x[1])
                    right_shoulder = max(right_shoulders, key=lambda x: x[1])
                    
                    # Kiểm tra mẫu hình đầu và vai
                    if (left_shoulder[1] < head[1] and right_shoulder[1] < head[1] and
                        abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1] < 0.1):
                        features_df.loc[features_df.index[i], 'pattern_head_shoulders'] = 1
        
        # Điền giá trị NaN
        if 'pattern_head_shoulders' in features_df.columns:
            features_df['pattern_head_shoulders'].fillna(0, inplace=True)
        else:
            features_df['pattern_head_shoulders'] = 0
        
        return features_df
    
    def _add_support_resistance_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các đặc trưng hỗ trợ/kháng cự dựa trên phân tích Fibonacci và các mức quan trọng khác
        
        Args:
            df: DataFrame dữ liệu

        Returns:
            DataFrame với đặc trưng hỗ trợ/kháng cự được thêm vào
        """
        features_df = df.copy()
        
        # Pivot Points
        features_df['sr_pp'] = (features_df['high'].shift(1) + features_df['low'].shift(1) + features_df['close'].shift(1)) / 3
        features_df['sr_r1'] = 2 * features_df['sr_pp'] - features_df['low'].shift(1)
        features_df['sr_s1'] = 2 * features_df['sr_pp'] - features_df['high'].shift(1)
        features_df['sr_r2'] = features_df['sr_pp'] + (features_df['high'].shift(1) - features_df['low'].shift(1))
        features_df['sr_s2'] = features_df['sr_pp'] - (features_df['high'].shift(1) - features_df['low'].shift(1))
        
        # Fibonacci Retracement Levels - đơn giản hóa
        lookback = 20
        
        for i in range(lookback, len(features_df)):
            window = features_df.iloc[i-lookback:i]
            high_point = window['high'].max()
            low_point = window['low'].min()
            price_range = high_point - low_point
            
            # Các mức Fibonacci Retracement
            fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
            
            # Xu hướng tăng (low to high)
            if features_df.iloc[i-1]['close'] > features_df.iloc[i-lookback]['close']:
                for level in fib_levels:
                    retracement = high_point - price_range * level
                    features_df.loc[features_df.index[i], f'sr_fib_up_{int(level*1000)}'] = retracement
            # Xu hướng giảm (high to low)
            else:
                for level in fib_levels:
                    retracement = low_point + price_range * level
                    features_df.loc[features_df.index[i], f'sr_fib_down_{int(level*1000)}'] = retracement
        
        # Điền giá trị NaN
        for col in features_df.columns:
            if col.startswith('sr_fib_'):
                features_df[col].fillna(method='ffill', inplace=True)
        
        # Khoảng cách từ giá đến các mức hỗ trợ/kháng cự
        for col in features_df.columns:
            if col.startswith('sr_'):
                features_df[f'{col}_dist'] = (features_df['close'] - features_df[col]) / features_df['close']
        
        # Đánh dấu khi giá gần mức hỗ trợ/kháng cự
        threshold = 0.01  # 1% từ mức hỗ trợ/kháng cự
        
        for col in features_df.columns:
            if col.startswith('sr_') and not col.endswith('_dist'):
                features_df[f'{col}_near'] = np.where(
                    abs(features_df['close'] - features_df[col]) / features_df['close'] < threshold,
                    1, 0
                )
        
        return features_df
    
    def _add_orderflow_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các đặc trưng phân tích dòng lệnh (order flow)
        
        Args:
            df: DataFrame dữ liệu

        Returns:
            DataFrame với đặc trưng dòng lệnh được thêm vào
        """
        if 'volume' not in df.columns:
            logger.warning("Thiếu cột volume, không thể thêm đặc trưng orderflow")
            return df
        
        features_df = df.copy()
        
        # Buying/Selling Volume - đơn giản hóa
        features_df['buying_volume'] = np.where(
            features_df['close'] > features_df['open'],
            features_df['volume'],
            0
        )
        
        features_df['selling_volume'] = np.where(
            features_df['close'] < features_df['open'],
            features_df['volume'],
            0
        )
        
        # Buying/Selling Volume Ratio
        features_df['buy_sell_volume_ratio'] = np.where(
            features_df['selling_volume'] > 0,
            features_df['buying_volume'] / features_df['selling_volume'],
            features_df['buying_volume']
        )
        
        # Cumulative Delta
        features_df['volume_delta'] = features_df['buying_volume'] - features_df['selling_volume']
        features_df['cumulative_delta'] = features_df['volume_delta'].cumsum()
        
        # Calculating relative strength of delta
        for window in [5, 10, 20]:
            features_df[f'delta_ma_{window}'] = features_df['volume_delta'].rolling(window=window).mean()
            features_df[f'delta_std_{window}'] = features_df['volume_delta'].rolling(window=window).std()
            features_df[f'delta_z_score_{window}'] = (features_df['volume_delta'] - features_df[f'delta_ma_{window}']) / features_df[f'delta_std_{window}']
        
        # Large Orders Detection (using volume spikes as proxy)
        for window in [10, 20]:
            features_df[f'volume_z_score_{window}'] = (
                features_df['volume'] - features_df['volume'].rolling(window=window).mean()
            ) / features_df['volume'].rolling(window=window).std()
            
            features_df[f'large_buy_orders_{window}'] = np.where(
                (features_df[f'volume_z_score_{window}'] > 2) & (features_df['close'] > features_df['open']),
                1, 0
            )
            
            features_df[f'large_sell_orders_{window}'] = np.where(
                (features_df[f'volume_z_score_{window}'] > 2) & (features_df['close'] < features_df['open']),
                1, 0
            )
        
        # Filling NaNs
        features_df['buy_sell_volume_ratio'].replace([np.inf, -np.inf], np.nan, inplace=True)
        numeric_cols = features_df.select_dtypes(include=['float64', 'int64']).columns
        features_df[numeric_cols] = features_df[numeric_cols].fillna(0)
        
        return features_df
    
    def _add_talib_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các đặc trưng từ thư viện TA-Lib
        
        Args:
            df: DataFrame dữ liệu

        Returns:
            DataFrame với đặc trưng TA-Lib được thêm vào
        """
        features_df = df.copy()
        
        try:
            import talib
            
            # Price indicators
            if all(col in features_df.columns for col in ['open', 'high', 'low', 'close']):
                # Oscillators
                features_df['ta_rsi'] = talib.RSI(features_df['close'].values, timeperiod=14)
                features_df['ta_rsi_5'] = talib.RSI(features_df['close'].values, timeperiod=5)
                features_df['ta_rsi_21'] = talib.RSI(features_df['close'].values, timeperiod=21)
                
                # Stochastic
                features_df['ta_slowk'], features_df['ta_slowd'] = talib.STOCH(
                    features_df['high'].values, 
                    features_df['low'].values, 
                    features_df['close'].values
                )
                
                # MACD
                features_df['ta_macd'], features_df['ta_macdsignal'], features_df['ta_macdhist'] = talib.MACD(
                    features_df['close'].values
                )
                
                # Bollinger Bands
                features_df['ta_upperband'], features_df['ta_middleband'], features_df['ta_lowerband'] = talib.BBANDS(
                    features_df['close'].values
                )
                
                # ATR
                features_df['ta_atr'] = talib.ATR(
                    features_df['high'].values,
                    features_df['low'].values,
                    features_df['close'].values
                )
                
                # CCI
                features_df['ta_cci'] = talib.CCI(
                    features_df['high'].values,
                    features_df['low'].values,
                    features_df['close'].values
                )
                
                # ADX
                features_df['ta_adx'] = talib.ADX(
                    features_df['high'].values,
                    features_df['low'].values,
                    features_df['close'].values
                )
                
                # OBV
                if 'volume' in features_df.columns:
                    features_df['ta_obv'] = talib.OBV(
                        features_df['close'].values,
                        features_df['volume'].values
                    )
                
                # Moving Averages
                for period in [10, 20, 50, 200]:
                    features_df[f'ta_sma_{period}'] = talib.SMA(features_df['close'].values, timeperiod=period)
                    features_df[f'ta_ema_{period}'] = talib.EMA(features_df['close'].values, timeperiod=period)
                
                # Pattern Recognition
                # Hammer
                features_df['ta_hammer'] = talib.CDLHAMMER(
                    features_df['open'].values,
                    features_df['high'].values,
                    features_df['low'].values,
                    features_df['close'].values
                )
                
                # Engulfing
                features_df['ta_engulfing'] = talib.CDLENGULFING(
                    features_df['open'].values,
                    features_df['high'].values,
                    features_df['low'].values,
                    features_df['close'].values
                )
                
                # Morning Star
                features_df['ta_morningstar'] = talib.CDLMORNINGSTAR(
                    features_df['open'].values,
                    features_df['high'].values,
                    features_df['low'].values,
                    features_df['close'].values
                )
                
                # Evening Star
                features_df['ta_eveningstar'] = talib.CDLEVENINGSTAR(
                    features_df['open'].values,
                    features_df['high'].values,
                    features_df['low'].values,
                    features_df['close'].values
                )
                
                # Shooting Star
                features_df['ta_shootingstar'] = talib.CDLSHOOTINGSTAR(
                    features_df['open'].values,
                    features_df['high'].values,
                    features_df['low'].values,
                    features_df['close'].values
                )
                
                # Doji
                features_df['ta_doji'] = talib.CDLDOJI(
                    features_df['open'].values,
                    features_df['high'].values,
                    features_df['low'].values,
                    features_df['close'].values
                )
                
                # Normalize pattern signals to 0-1
                pattern_cols = [col for col in features_df.columns if col.startswith('ta_') and 'star' in col or 'doji' in col or 'hammer' in col or 'engulfing' in col]
                for col in pattern_cols:
                    features_df[col] = np.where(features_df[col] > 0, 1, np.where(features_df[col] < 0, -1, 0))
        
        except ImportError:
            logger.warning("Thư viện TA-Lib không có sẵn, bỏ qua các đặc trưng TA-Lib")
        except Exception as e:
            logger.error(f"Lỗi khi thêm đặc trưng TA-Lib: {str(e)}")
        
        return features_df
    
    def _handle_invalid_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Xử lý các giá trị không hợp lệ (NaN, inf)
        
        Args:
            df: DataFrame dữ liệu
            
        Returns:
            DataFrame đã được làm sạch
        """
        # Tạo DataFrame mới để xử lý
        cleaned_df = df.copy()
        
        # Thay thế inf bằng NaN
        cleaned_df.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        # Lấy danh sách các cột có dữ liệu số
        numeric_cols = cleaned_df.select_dtypes(include=['float64', 'int64']).columns
        
        # Thêm các cột bị NaN vào danh sách đặc biệt
        nan_cols = [col for col in numeric_cols if cleaned_df[col].isna().any()]
        if nan_cols:
            logger.warning(f"Có {len(nan_cols)} cột chứa giá trị NaN")
        
        # Điền các giá trị NaN với phương pháp phù hợp
        if self.handle_missing:
            # Với đặc trưng thông thường, dùng forward fill, rồi backward fill
            cleaned_df[numeric_cols] = cleaned_df[numeric_cols].fillna(method='ffill')
            cleaned_df[numeric_cols] = cleaned_df[numeric_cols].fillna(method='bfill')
            
            # Sau cùng, điền các giá trị còn lại với 0
            cleaned_df[numeric_cols] = cleaned_df[numeric_cols].fillna(0)
        
        return cleaned_df
    
    def fit_transform(self, features_df: pd.DataFrame, target_col: Optional[str] = None) -> np.ndarray:
        """
        Áp dụng pipeline và chuyển đổi đặc trưng
        
        Args:
            features_df: DataFrame chứa đặc trưng
            target_col: Tên cột mục tiêu (nếu có) để phân tích quan hệ
            
        Returns:
            Mảng features đã được chuyển đổi
        """
        # Kiểm tra nếu features_df là DataFrame
        if not isinstance(features_df, pd.DataFrame):
            logger.error("features_df phải là pandas DataFrame")
            return np.array([])
        
        # Tạo X từ các đặc trưng
        feature_cols = [col for col in features_df.columns if col not in 
                       ['open', 'high', 'low', 'close', 'volume', 'timestamp', 'date', target_col]]
        
        if not feature_cols:
            logger.error("Không tìm thấy cột đặc trưng hợp lệ")
            return np.array([])
        
        X = features_df[feature_cols].values
        
        # Nếu có target_col, phân tích đặc trưng quan trọng
        if target_col and target_col in features_df.columns and self.feature_selection:
            y = features_df[target_col].values
            # Fit và transform
            X_transformed = self.pipeline.fit_transform(X, y)
            
            # Lưu danh sách đặc trưng được chọn
            if hasattr(self.feature_selector, 'get_support'):
                selected_indices = self.feature_selector.get_support()
                self.selected_features = [feature_cols[i] for i in range(len(feature_cols)) if selected_indices[i]]
                
                # Lưu điểm quan trọng của đặc trưng
                if hasattr(self.feature_selector, 'scores_'):
                    for feature, score in zip(feature_cols, self.feature_selector.scores_):
                        self.feature_importance[feature] = score
        else:
            # Chỉ transform
            X_transformed = self.pipeline.fit_transform(X)
            self.selected_features = feature_cols
        
        return X_transformed
    
    def transform(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        Chuyển đổi đặc trưng sử dụng pipeline đã fit trước đó
        
        Args:
            features_df: DataFrame chứa đặc trưng
            
        Returns:
            Mảng features đã được chuyển đổi
        """
        # Kiểm tra nếu pipeline đã được fit
        if not hasattr(self.pipeline, 'transform'):
            logger.error("Pipeline chưa được fit, sử dụng fit_transform trước")
            return np.array([])
        
        # Tạo X từ các đặc trưng
        feature_cols = [col for col in features_df.columns if col not in 
                       ['open', 'high', 'low', 'close', 'volume', 'timestamp', 'date']]
        
        # Nếu đã chọn features, chỉ dùng những features đó
        if self.selected_features:
            # Lấy giao của selected_features và feature_cols hiện có
            use_features = list(set(self.selected_features).intersection(set(feature_cols)))
            if not use_features:
                logger.warning("Không có đặc trưng nào khớp với selected_features, sử dụng tất cả feature_cols")
                use_features = feature_cols
        else:
            use_features = feature_cols
        
        X = features_df[use_features].values
        
        # Transform dữ liệu
        X_transformed = self.pipeline.transform(X)
        
        return X_transformed
    
    def analyze_feature_importance(self, features_df: pd.DataFrame, target_col: str) -> Dict[str, float]:
        """
        Phân tích mức độ quan trọng của các đặc trưng với mục tiêu
        
        Args:
            features_df: DataFrame chứa đặc trưng
            target_col: Tên cột mục tiêu
            
        Returns:
            Dict chứa điểm quan trọng của đặc trưng
        """
        if target_col not in features_df.columns:
            logger.error(f"Cột mục tiêu {target_col} không tồn tại trong DataFrame")
            return {}
        
        # Tạo X và y
        feature_cols = [col for col in features_df.columns if col not in 
                       ['open', 'high', 'low', 'close', 'volume', 'timestamp', 'date', target_col]]
        
        X = features_df[feature_cols].values
        y = features_df[target_col].values
        
        try:
            from sklearn.feature_selection import mutual_info_regression
            
            # Tính điểm mutual information
            scores = mutual_info_regression(X, y)
            
            # Chuẩn hóa điểm
            max_score = max(scores) if scores.max() > 0 else 1
            normalized_scores = scores / max_score
            
            # Tạo dict kết quả
            importance_dict = {feature: score for feature, score in zip(feature_cols, normalized_scores)}
            
            # Sắp xếp theo điểm giảm dần
            sorted_importance = {k: v for k, v in sorted(importance_dict.items(), key=lambda item: item[1], reverse=True)}
            
            return sorted_importance
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích feature importance: {str(e)}")
            return {}
    
    def save(self, filepath: Optional[str] = None) -> str:
        """
        Lưu pipeline đã huấn luyện
        
        Args:
            filepath: Đường dẫn file để lưu, None sẽ dùng đường dẫn mặc định
            
        Returns:
            Đường dẫn file đã lưu
        """
        if filepath is None:
            filepath = self.model_path
        
        try:
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Tạo dict dữ liệu để lưu
            data = {
                'pipeline': self.pipeline,
                'feature_groups': self.feature_groups,
                'selected_features': self.selected_features,
                'feature_importance': self.feature_importance,
                'basic_features': self.basic_features,
                'advanced_features': self.advanced_features,
                'technical_features': self.technical_features,
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'price_features': self.price_features,
                    'volume_features': self.volume_features,
                    'trend_features': self.trend_features,
                    'volatility_features': self.volatility_features,
                    'pattern_features': self.pattern_features,
                    'orderflow_features': self.orderflow_features,
                    'use_ta_lib': self.use_ta_lib,
                    'use_pca': self.use_pca,
                    'pca_components': self.pca_components,
                    'feature_selection': self.feature_selection,
                    'n_features_to_select': self.n_features_to_select,
                    'scaling_method': self.scaling_method
                }
            }
            
            # Lưu bằng pickle
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
                
            logger.info(f"Đã lưu pipeline tại {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu pipeline: {str(e)}")
            return ""
    
    def load(self, filepath: Optional[str] = None) -> bool:
        """
        Tải pipeline đã huấn luyện
        
        Args:
            filepath: Đường dẫn file để tải, None sẽ dùng đường dẫn mặc định
            
        Returns:
            True nếu tải thành công, False nếu thất bại
        """
        if filepath is None:
            filepath = self.model_path
        
        if not os.path.exists(filepath):
            logger.error(f"File không tồn tại: {filepath}")
            return False
        
        try:
            # Tải dữ liệu
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            # Khôi phục pipeline
            self.pipeline = data['pipeline']
            
            # Khôi phục thuộc tính
            self.feature_groups = data['feature_groups']
            self.selected_features = data['selected_features']
            self.feature_importance = data['feature_importance']
            self.basic_features = data['basic_features']
            self.advanced_features = data['advanced_features']
            self.technical_features = data['technical_features']
            
            # Khôi phục metadata
            metadata = data['metadata']
            self.price_features = metadata['price_features']
            self.volume_features = metadata['volume_features']
            self.trend_features = metadata['trend_features']
            self.volatility_features = metadata['volatility_features']
            self.pattern_features = metadata['pattern_features']
            self.orderflow_features = metadata['orderflow_features']
            self.use_ta_lib = metadata['use_ta_lib']
            self.use_pca = metadata['use_pca']
            self.pca_components = metadata['pca_components']
            self.feature_selection = metadata['feature_selection']
            self.n_features_to_select = metadata['n_features_to_select']
            self.scaling_method = metadata['scaling_method']
            
            logger.info(f"Đã tải pipeline từ {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tải pipeline: {str(e)}")
            return False
    
    def detect_market_type(self, features_df: pd.DataFrame) -> MarketType:
        """
        Phát hiện loại thị trường từ đặc trưng
        
        Args:
            features_df: DataFrame chứa đặc trưng
            
        Returns:
            Loại thị trường (MarketType)
        """
        # Lấy phần dữ liệu gần đây nhất
        recent_data = features_df.iloc[-20:].copy() if len(features_df) > 20 else features_df.copy()
        
        # Tính các đặc trưng chính cho phát hiện
        
        # 1. Trend Detection
        if 'adx' in recent_data.columns:
            adx = recent_data['adx'].iloc[-1]
        elif 'ta_adx' in recent_data.columns:
            adx = recent_data['ta_adx'].iloc[-1]
        else:
            # Tính adx nếu chưa có
            if 'plus_di' in recent_data.columns and 'minus_di' in recent_data.columns:
                dx = abs(recent_data['plus_di'] - recent_data['minus_di']) / (recent_data['plus_di'] + recent_data['minus_di']) * 100
                adx = dx.rolling(window=14).mean().iloc[-1]
            else:
                adx = 0
        
        # 2. Volatility Detection
        if 'normalized_atr' in recent_data.columns:
            volatility = recent_data['normalized_atr'].iloc[-1]
        elif 'atr' in recent_data.columns and 'close' in recent_data.columns:
            volatility = recent_data['atr'].iloc[-1] / recent_data['close'].iloc[-1]
        else:
            # Tính volatility nếu chưa có
            if 'close' in recent_data.columns:
                volatility = recent_data['close'].pct_change().std()
            else:
                volatility = 0
        
        # 3. Trend Direction
        if 'close' in recent_data.columns and len(recent_data) > 5:
            short_ma = recent_data['close'].rolling(window=5).mean().iloc[-1]
            long_ma = recent_data['close'].rolling(window=20).mean().iloc[-1]
            trend_direction = 1 if short_ma > long_ma else -1
        else:
            trend_direction = 0
        
        # 4. Range Detection
        if 'bb_width' in recent_data.columns:
            bb_width = recent_data['bb_width'].iloc[-1]
            is_ranging = bb_width < 0.03  # Threshold for ranging
        else:
            is_ranging = False
        
        # 5. Recent price volatility
        if 'close' in recent_data.columns and len(recent_data) > 5:
            recent_volatility = recent_data['close'].pct_change().abs().mean()
            is_volatile = recent_volatility > 0.01  # Threshold for volatile
        else:
            is_volatile = False
        
        # Logic phân loại thị trường
        if adx > 25:  # Strong trend
            if trend_direction > 0:
                return MarketType.TRENDING_UP
            else:
                return MarketType.TRENDING_DOWN
        elif is_volatile:
            return MarketType.VOLATILE
        elif is_ranging:
            return MarketType.RANGING
        else:
            return MarketType.NEUTRAL

if __name__ == "__main__":
    # Demo
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Tạo dữ liệu mẫu
    days = 100
    date_range = [datetime.now() - timedelta(days=i) for i in range(days)]
    date_range.reverse()
    
    # Tạo biến động giá ngẫu nhiên
    close_prices = [100]
    for i in range(1, days):
        # Mô phỏng xu hướng với một số biến động
        close_prices.append(close_prices[-1] * (1 + np.random.normal(0.001, 0.02)))
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'date': date_range,
        'open': [price * (1 - 0.005 + np.random.random() * 0.01) for price in close_prices],
        'high': [price * (1 + 0.005 + np.random.random() * 0.01) for price in close_prices],
        'low': [price * (1 - 0.005 - np.random.random() * 0.01) for price in close_prices],
        'close': close_prices,
        'volume': [np.random.randint(100000, 1000000) for _ in range(days)]
    })
    
    # Thiết lập index
    df.set_index('date', inplace=True)
    
    # Tạo pipeline
    pipeline = FeatureFusionPipeline(
        feature_groups=["price", "volume", "trend", "volatility", "pattern"],
        price_features=True,
        volume_features=True,
        trend_features=True,
        volatility_features=True,
        pattern_features=True,
        use_ta_lib=False,  # Set False nếu không có talib
        use_pca=True,
        pca_components=10,
        feature_selection="mutual_info",
        n_features_to_select=20
    )
    
    # Thêm đặc trưng
    features_df = pipeline.generate_features(df)
    
    # In thông tin về đặc trưng được tạo
    print(f"Số lượng đặc trưng: {len(features_df.columns) - 5}")  # Trừ các cột OHLCV
    print(f"Các đặc trưng cơ bản: {len(pipeline.basic_features)}")
    print(f"Các đặc trưng kỹ thuật: {len(pipeline.technical_features)}")
    print(f"Các đặc trưng nâng cao: {len(pipeline.advanced_features)}")
    
    # Tạo biến mục tiêu là giá đóng cửa cho mục đích demo
    features_df['target'] = features_df['close'].shift(-1) / features_df['close'] - 1
    
    # Loại bỏ NaN
    features_df = features_df.dropna()
    
    # Fit và transform
    X_transformed = pipeline.fit_transform(features_df, 'target')
    
    # In thông tin về đặc trưng được chọn
    print(f"\nĐặc trưng được chọn ({len(pipeline.selected_features)}):")
    for feature in pipeline.selected_features[:10]:  # Chỉ in 10 đặc trưng đầu tiên
        print(f"- {feature}")
    
    # Phân tích thị trường
    market_type = pipeline.detect_market_type(features_df)
    print(f"\nLoại thị trường hiện tại: {market_type}")
    
    # Lưu pipeline
    pipeline.save()
    print("Đã lưu pipeline thành công")