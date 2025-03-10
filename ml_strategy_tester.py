#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Công cụ kiểm thử chiến lược ML và đánh giá hiệu suất
So sánh với các chiến lược truyền thống và chiến lược rủi ro cao
"""

import os
import sys
import logging
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import joblib
import json
from typing import Dict, List, Tuple, Optional, Any
import glob
import time

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ml_testing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ml_strategy_tester')

# Thêm thư mục gốc vào sys.path để import các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from app.simple_feature_engineering import SimpleFeatureEngineering
    from app.market_regime_detector import MarketRegimeDetector
    from app.advanced_ml_optimizer import AdvancedMLOptimizer
    from fibonacci_helper import FibonacciAnalyzer, add_fibonacci_signals
    from adaptive_risk_manager import AdaptiveRiskManager, add_atr_to_dataframe
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")

class MLStrategyTester:
    """
    Lớp kiểm thử chiến lược ML và so sánh với các chiến lược khác
    """
    
    def __init__(self, simulation_mode=True, data_dir=None):
        """
        Khởi tạo tester
        
        Args:
            simulation_mode: Sử dụng chế độ mô phỏng hay không
            data_dir: Thư mục chứa dữ liệu lịch sử, nếu None sẽ lấy qua API
        """
        self.simulation_mode = simulation_mode
        self.data_dir = data_dir
        
        # Khởi tạo API và bộ xử lý dữ liệu
        self.api = BinanceAPI(simulation_mode=simulation_mode)
        self.data_processor = DataProcessor(self.api, simulation_mode=simulation_mode)
        
        # Khởi tạo Market Regime Detector
        self.regime_detector = MarketRegimeDetector()
        
        # Khởi tạo ML Optimizer
        self.ml_optimizer = AdvancedMLOptimizer()
        
        # Các thư mục lưu trữ
        self.models_dir = "ml_models"
        self.test_results_dir = "ml_test_results"
        self.test_charts_dir = "ml_test_charts"
        
        # Tạo thư mục nếu chưa tồn tại
        for dir_path in [self.test_results_dir, self.test_charts_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Danh sách coin và khung thời gian mặc định
        self.default_coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
        self.default_timeframes = ["1h", "4h"]
        
        # Các chiến lược truyền thống
        self.traditional_strategies = {
            "rsi": self._apply_rsi_strategy,
            "macd": self._apply_macd_strategy,
            "bollinger": self._apply_bollinger_strategy,
            "combined": self._apply_combined_strategy
        }
        
        # Tỷ lệ dữ liệu dành cho tập test
        self.test_ratio = 0.3
        
        logger.info(f"Khởi tạo MLStrategyTester, chế độ mô phỏng: {simulation_mode}")
        
    def load_model(self, model_name: str, source_dir: str = None) -> Tuple:
        """
        Tải mô hình ML từ file
        
        Args:
            model_name: Tên mô hình (không bao gồm phần mở rộng)
            source_dir: Thư mục chứa mô hình (mặc định: self.models_dir)
            
        Returns:
            Tuple (model, scaler, features)
        """
        if source_dir is None:
            source_dir = self.models_dir
            
        try:
            # Xử lý tên file - cắt bỏ "_random_forest" nếu có
            base_name = model_name.replace("_random_forest", "")
            
            # Đường dẫn đến các file
            model_path = os.path.join(source_dir, f"{base_name}_model.joblib")
            scaler_path = os.path.join(source_dir, f"{base_name}_scaler.joblib")
            features_path = os.path.join(source_dir, f"{base_name}_features.json")
            
            # Kiểm tra tất cả các file tồn tại
            if not all(os.path.exists(p) for p in [model_path, scaler_path, features_path]):
                missing = [p for p in [model_path, scaler_path, features_path] if not os.path.exists(p)]
                logger.error(f"Không tìm thấy các file cần thiết: {missing}")
                return None, None, None
            
            # Tải mô hình và scaler
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            
            # Tải danh sách đặc trưng
            with open(features_path, 'r') as f:
                features = json.load(f)
            
            logger.info(f"Đã tải mô hình {model_name} thành công")
            
            return model, scaler, features
            
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình {model_name}: {str(e)}")
            return None, None, None
            
    def prepare_data_for_backtesting(self, symbol: str, interval: str, 
                                  lookback_days: int = 60) -> pd.DataFrame:
        """
        Chuẩn bị dữ liệu cho backtesting
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            lookback_days: Số ngày lịch sử
            
        Returns:
            DataFrame chứa dữ liệu đã xử lý
        """
        try:
            logger.info(f"Chuẩn bị dữ liệu cho backtesting {symbol} {interval}")
            
            # Nếu data_dir được cung cấp, đọc từ file
            if self.data_dir:
                # Thử các định dạng file khác nhau
                file_patterns = [
                    f"{symbol}_{interval}.csv",
                    f"{symbol}_{interval}_historical_data.csv",
                    f"{symbol}_{interval}_sample.csv"
                ]
                
                found_file = False
                for pattern in file_patterns:
                    file_path = os.path.join(self.data_dir, pattern)
                    if os.path.exists(file_path):
                        logger.info(f"Đọc dữ liệu từ file {file_path}")
                        df = pd.read_csv(file_path)
                        found_file = True
                        break
                        
                if not found_file:
                    logger.warning(f"Không tìm thấy file dữ liệu {self.data_dir}/{symbol}_{interval}*.csv")
                    return None
                
                # Đảm bảo định dạng cột thời gian đúng
                if 'datetime' in df.columns:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df.set_index('datetime', inplace=True)
                elif 'timestamp' in df.columns:
                    df['datetime'] = pd.to_datetime(df['timestamp'])
                    df.set_index('datetime', inplace=True)
                elif 'open_time' in df.columns:
                    df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
                    df.set_index('datetime', inplace=True)
                    
                # Chỉ lấy số ngày dữ liệu cần thiết nếu có quá nhiều
                if lookback_days > 0 and isinstance(df.index, pd.DatetimeIndex):
                    end_date = df.index.max()
                    start_date = end_date - pd.Timedelta(days=lookback_days)
                    df = df[df.index >= start_date]
            else:
                # Tải dữ liệu lịch sử qua API
                df = self.data_processor.get_historical_data(symbol, interval, lookback_days=lookback_days)
            
            if df is None or len(df) < 30:
                logger.error(f"Không đủ dữ liệu cho {symbol} {interval}")
                return None
                
            logger.info(f"Đã tải {len(df)} nến cho {symbol} {interval}")
            
            # Thêm các chỉ báo kỹ thuật
            # RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['std_20'] = df['close'].rolling(window=20).std()
            df['upper_band'] = df['sma_20'] + (df['std_20'] * 2)
            df['lower_band'] = df['sma_20'] - (df['std_20'] * 2)
            df['bb_width'] = (df['upper_band'] - df['lower_band']) / df['sma_20']
            df['bb_position'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
            
            # MACD
            ema_12 = df['close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Stochastic
            low_14 = df['low'].rolling(window=14).min()
            high_14 = df['high'].rolling(window=14).max()
            df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
            df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
            
            # ADX (Average Directional Index)
            tr1 = df['high'] - df['low']
            tr2 = abs(df['high'] - df['close'].shift(1))
            tr3 = abs(df['low'] - df['close'].shift(1))
            tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
            df['atr'] = tr.rolling(window=14).mean()
            
            # Phân tích giá
            df['price_change'] = df['close'].pct_change()
            df['price_change_abs'] = df['price_change'].abs()
            df['price_volatility'] = df['price_change'].rolling(window=14).std()
            
            # Phân tích khối lượng
            df['volume_change'] = df['volume'].pct_change()
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # Thêm lag features
            lags = [1, 2, 3, 5, 7, 14, 21]
            for lag in lags:
                df[f'close_lag_{lag}'] = df['close'].shift(lag)
                df[f'price_change_lag_{lag}'] = df['price_change'].shift(lag)
                df[f'volume_change_lag_{lag}'] = df['volume_change'].shift(lag)
            
            # Thêm biến thời gian
            df['hour'] = pd.to_datetime(df.index).hour
            df['day_of_week'] = pd.to_datetime(df.index).dayofweek
            
            # Thêm chế độ thị trường
            regimes = []
            for i in range(len(df)):
                # Cần ít nhất 30 nến để phân loại chế độ
                window_start = max(0, i - 30)
                if i < 30:
                    regimes.append('neutral')
                else:
                    temp_df = df.iloc[window_start:i+1].copy()
                    regime = self.regime_detector.detect_regime(temp_df)
                    regimes.append(regime)
            
            df['market_regime'] = regimes
            
            # Loại bỏ các giá trị NaN
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.dropna()
            
            logger.info(f"Đã chuẩn bị dữ liệu cho backtesting với {len(df.columns)} đặc trưng")
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị dữ liệu cho backtesting: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _apply_rsi_strategy(self, df: pd.DataFrame, overbought: int = 70, 
                          oversold: int = 30) -> pd.DataFrame:
        """
        Áp dụng chiến lược RSI
        
        Args:
            df: DataFrame với các chỉ báo
            overbought: Ngưỡng quá mua
            oversold: Ngưỡng quá bán
            
        Returns:
            DataFrame với tín hiệu
        """
        df_strategy = df.copy()
        
        # Khởi tạo cột tín hiệu
        df_strategy['signal'] = 0
        
        # Tín hiệu mua: RSI < oversold
        df_strategy.loc[df_strategy['rsi'] < oversold, 'signal'] = 1
        
        # Tín hiệu bán: RSI > overbought
        df_strategy.loc[df_strategy['rsi'] > overbought, 'signal'] = -1
        
        return df_strategy
    
    def _apply_macd_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Áp dụng chiến lược MACD
        
        Args:
            df: DataFrame với các chỉ báo
            
        Returns:
            DataFrame với tín hiệu
        """
        df_strategy = df.copy()
        
        # Khởi tạo cột tín hiệu
        df_strategy['signal'] = 0
        
        # Tín hiệu mua: MACD vượt lên trên Signal Line
        df_strategy.loc[(df_strategy['macd'] > df_strategy['macd_signal']) & 
                         (df_strategy['macd'].shift(1) <= df_strategy['macd_signal'].shift(1)), 'signal'] = 1
        
        # Tín hiệu bán: MACD giảm xuống dưới Signal Line
        df_strategy.loc[(df_strategy['macd'] < df_strategy['macd_signal']) & 
                         (df_strategy['macd'].shift(1) >= df_strategy['macd_signal'].shift(1)), 'signal'] = -1
        
        return df_strategy
    
    def _apply_bollinger_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Áp dụng chiến lược Bollinger Bands
        
        Args:
            df: DataFrame với các chỉ báo
            
        Returns:
            DataFrame với tín hiệu
        """
        df_strategy = df.copy()
        
        # Khởi tạo cột tín hiệu
        df_strategy['signal'] = 0
        
        # Tín hiệu mua: Giá chạm dải dưới
        df_strategy.loc[df_strategy['close'] < df_strategy['lower_band'], 'signal'] = 1
        
        # Tín hiệu bán: Giá chạm dải trên
        df_strategy.loc[df_strategy['close'] > df_strategy['upper_band'], 'signal'] = -1
        
        return df_strategy
    
    def _apply_combined_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Áp dụng chiến lược kết hợp (RSI + MACD + Bollinger Bands)
        
        Args:
            df: DataFrame với các chỉ báo
            
        Returns:
            DataFrame với tín hiệu
        """
        # Áp dụng từng chiến lược
        df_rsi = self._apply_rsi_strategy(df)
        df_macd = self._apply_macd_strategy(df)
        df_bollinger = self._apply_bollinger_strategy(df)
        
        # Kết hợp tín hiệu
        df_combined = df.copy()
        df_combined['signal'] = 0
        
        # Tín hiệu mua: ít nhất 2 trong 3 chiến lược đều cho tín hiệu mua
        buy_count = (df_rsi['signal'] == 1).astype(int) + \
                   (df_macd['signal'] == 1).astype(int) + \
                   (df_bollinger['signal'] == 1).astype(int)
        
        df_combined.loc[buy_count >= 2, 'signal'] = 1
        
        # Tín hiệu bán: ít nhất 2 trong 3 chiến lược đều cho tín hiệu bán
        sell_count = (df_rsi['signal'] == -1).astype(int) + \
                    (df_macd['signal'] == -1).astype(int) + \
                    (df_bollinger['signal'] == -1).astype(int)
        
        df_combined.loc[sell_count >= 2, 'signal'] = -1
        
        return df_combined
    
    def _apply_ml_strategy(self, df: pd.DataFrame, model, scaler, features) -> pd.DataFrame:
        """
        Áp dụng chiến lược ML
        
        Args:
            df: DataFrame với các chỉ báo
            model: Mô hình ML đã huấn luyện
            scaler: Scaler đã fit
            features: Danh sách đặc trưng sử dụng
            
        Returns:
            DataFrame với tín hiệu
        """
        try:
            df_strategy = df.copy()
            
            # Khởi tạo cột tín hiệu
            df_strategy['signal'] = 0
            
            # Trích xuất danh sách tính năng từ đối tượng features
            if isinstance(features, dict) and 'features' in features:
                feature_list = features['features']
            else:
                feature_list = features

            # Sử dụng MLFeatureCalculator để tính toán các tính năng còn thiếu
            try:
                from ml_feature_calculator import MLFeatureCalculator
                
                # Tạo bộ tính toán tính năng với danh sách tính năng của mô hình
                feature_calculator = MLFeatureCalculator(features_list=feature_list)
                
                # Tính toán tất cả các tính năng cần thiết
                df = feature_calculator.calculate_live_features(df)
                
                logger.info(f"Đã tính toán {len(feature_list)} tính năng cần thiết cho mô hình")
            except Exception as e:
                logger.error(f"Lỗi khi sử dụng MLFeatureCalculator: {str(e)}")
                logger.warning("Quay lại phương pháp tính tính năng cũ")
                
                # Thêm các tính năng còn thiếu trong DataFrame
                required_features = set(feature_list)
                existing_features = set(df.columns)
                
                # Lọc các đặc trưng có sẵn
                available_features = [f for f in feature_list if f in df.columns]
                
                if len(available_features) < len(feature_list):
                    missing_features = required_features - existing_features
                    logger.warning(f"Thiếu {len(missing_features)} đặc trưng: {missing_features}")
                    
                    # Thêm một số tính năng cơ bản nếu thiếu
                    for feature in missing_features:
                        if feature == 'sma5':
                            df['sma5'] = df['close'].rolling(window=5).mean()
                        elif feature == 'sma10':
                            df['sma10'] = df['close'].rolling(window=10).mean()
                        elif feature == 'sma20':
                            df['sma20'] = df['close'].rolling(window=20).mean()
                        elif feature == 'sma50':
                            df['sma50'] = df['close'].rolling(window=50).mean()
                        elif feature == 'sma100':
                            df['sma100'] = df['close'].rolling(window=100).mean()
                        elif feature == 'ema5':
                            df['ema5'] = df['close'].ewm(span=5, adjust=False).mean()
                        elif feature == 'ema10':
                            df['ema10'] = df['close'].ewm(span=10, adjust=False).mean()
                        elif feature == 'ema20':
                            df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
                        elif feature == 'ema50':
                            df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
                        elif feature == 'price_sma20_ratio' and 'sma20' in df.columns:
                            df['price_sma20_ratio'] = df['close'] / df['sma20']
                        elif feature == 'price_sma50_ratio' and 'sma50' in df.columns:
                            df['price_sma50_ratio'] = df['close'] / df['sma50']
                        elif feature == 'volume_sma5':
                            df['volume_sma5'] = df['volume'].rolling(window=5).mean()
                        elif feature == 'volume_ratio' and 'volume_sma5' in df.columns:
                            df['volume_ratio'] = df['volume'] / df['volume_sma5']
                        elif feature == 'volatility':
                            df['volatility'] = df['close'].pct_change().rolling(window=20).std()
                        elif feature == 'daily_return':
                            df['daily_return'] = df['close'].pct_change(24)
                        elif feature == 'weekly_return':
                            df['weekly_return'] = df['close'].pct_change(24*7)
            
            # Cập nhật lại danh sách tính năng có sẵn
            available_features = [f for f in feature_list if f in df.columns]
            
            if len(available_features) == 0:
                logger.error("Không có tính năng nào khớp, không thể tiếp tục")
                return df_strategy
            
            # Đọc dữ liệu chỉ với các tính năng có sẵn
            X = df[available_features]
            
            # Loại bỏ các dòng NaN
            X = X.dropna()
            if len(X) == 0:
                logger.error("Sau khi loại bỏ NaN, không còn dữ liệu nào")
                return df_strategy
                
            # Chuẩn hóa đặc trưng
            try:
                X_scaled = scaler.transform(X)
            except Exception as e:
                logger.error(f"Lỗi khi chuẩn hóa dữ liệu: {e}")
                return df_strategy
            
            # Dự đoán
            predictions = model.predict(X_scaled)
            
            # Áp dụng chiến lược quyết định mạnh hơn
            df_strategy['raw_prediction'] = predictions
            df_strategy['signal'] = predictions  # Sử dụng dự đoán nguyên gốc làm tín hiệu mặc định
            
            # Nếu mô hình hỗ trợ predict_proba, sử dụng xác suất để quyết định mạnh hơn
            if hasattr(model, 'predict_proba'):
                try:
                    probas = model.predict_proba(X_scaled)
                    # Lưu xác suất cho từng lớp
                    for i, class_label in enumerate(model.classes_):
                        col_name = f'prob_{class_label}'
                        df_strategy[col_name] = probas[:, i]
                    
                    # Ngưỡng tin cậy để quyết định giao dịch
                    confidence_threshold = 0.40  # Giảm ngưỡng tin cậy xuống 40%
                    
                    # Chỉ đặt tín hiệu khi xác suất vượt ngưỡng
                    # Đã đặt ngưỡng tin cậy ở trên (confidence_threshold = 0.40)
                    
                    # Đặt tín hiệu mua khi dự đoán là 1 và xác suất cao
                    if 'prob_1' in df_strategy.columns:
                        # Kết hợp xác suất với các chỉ báo kỹ thuật
                        if 'rsi' in df_strategy.columns:
                            # RSI boost - 3 mức dựa trên mức độ quá bán
                            # Mức 1: < 40 - giảm 20%
                            # Mức 2: < 30 - giảm 30%
                            # Mức 3: < 20 - giảm 40%
                            rsi_confidence_boost = 0.0
                            rsi_oversold_level3 = df_strategy['rsi'] < 20
                            rsi_oversold_level2 = df_strategy['rsi'] < 30 
                            rsi_oversold_level1 = df_strategy['rsi'] < 40
                            
                            # Mặc định RSI boost là 0, áp dụng mức cao nhất nếu thỏa mãn
                            rsi_boost_mask = rsi_oversold_level1.copy()  # Mặc định mức 1
                            rsi_confidence_boost = 0.20  # Giảm 20% ngưỡng khi RSI < 40
                            
                            # Mức 2: giảm 30% nếu RSI < 30
                            mask_level2 = rsi_oversold_level2
                            if mask_level2.any():
                                rsi_boost_mask = mask_level2
                                rsi_confidence_boost = 0.30
                            
                            # Mức 3: giảm 40% nếu RSI < 20
                            mask_level3 = rsi_oversold_level3
                            if mask_level3.any():
                                rsi_boost_mask = mask_level3
                                rsi_confidence_boost = 0.40
                            
                            # Ghi log các trường hợp RSI boost
                            rsi_values = df_strategy.loc[rsi_boost_mask, 'rsi']
                            if not rsi_values.empty:
                                min_rsi = rsi_values.min()
                                max_rsi = rsi_values.max()
                                logger.info(f"Áp dụng RSI boost cho long: {rsi_confidence_boost:.2f}, RSI min={min_rsi:.2f}, max={max_rsi:.2f}")
                            
                            # Sử dụng mask để xác định điều kiện quá bán
                            rsi_oversold = rsi_boost_mask
                            
                            # Mua khi dự đoán = 1 và (xác suất > ngưỡng hoặc RSI quá bán và xác suất > ngưỡng thấp hơn)
                            buy_signals = (predictions == 1) & (
                                (df_strategy['prob_1'] > confidence_threshold) | 
                                (rsi_oversold & (df_strategy['prob_1'] > (confidence_threshold - rsi_confidence_boost)))
                            )
                        else:
                            # Nếu không có RSI, chỉ dùng xác suất
                            buy_signals = (predictions == 1) & (df_strategy['prob_1'] > confidence_threshold)
                        
                        df_strategy.loc[buy_signals, 'signal'] = 1
                    
                    # Đặt tín hiệu bán khi dự đoán là 0 và xác suất cao
                    if 'prob_0' in df_strategy.columns:
                        # Kết hợp xác suất với các chỉ báo kỹ thuật
                        if 'rsi' in df_strategy.columns:
                            # RSI boost - 3 mức dựa trên mức độ quá mua
                            # Mức 1: > 60 - giảm 20%
                            # Mức 2: > 70 - giảm 30%
                            # Mức 3: > 80 - giảm 40%
                            rsi_confidence_boost = 0.0
                            rsi_overbought_level3 = df_strategy['rsi'] > 80
                            rsi_overbought_level2 = df_strategy['rsi'] > 70 
                            rsi_overbought_level1 = df_strategy['rsi'] > 60
                            
                            # Mặc định RSI boost là 0, áp dụng mức cao nhất nếu thỏa mãn
                            rsi_boost_mask = rsi_overbought_level1.copy()  # Mặc định mức 1
                            rsi_confidence_boost = 0.20  # Giảm 20% ngưỡng khi RSI > 60
                            
                            # Mức 2: giảm 30% nếu RSI > 70
                            mask_level2 = rsi_overbought_level2
                            if mask_level2.any():
                                rsi_boost_mask = mask_level2
                                rsi_confidence_boost = 0.30
                            
                            # Mức 3: giảm 40% nếu RSI > 80
                            mask_level3 = rsi_overbought_level3
                            if mask_level3.any():
                                rsi_boost_mask = mask_level3
                                rsi_confidence_boost = 0.40
                            
                            # Ghi log các trường hợp RSI boost
                            rsi_values = df_strategy.loc[rsi_boost_mask, 'rsi']
                            if not rsi_values.empty:
                                min_rsi = rsi_values.min()
                                max_rsi = rsi_values.max()
                                logger.info(f"Áp dụng RSI boost cho short: {rsi_confidence_boost:.2f}, RSI min={min_rsi:.2f}, max={max_rsi:.2f}")
                            
                            # Sử dụng mask để xác định điều kiện quá mua
                            rsi_overbought = rsi_boost_mask
                            
                            # Bán khi dự đoán = 0 và (xác suất > ngưỡng hoặc RSI quá mua và xác suất > ngưỡng thấp hơn)
                            sell_signals = (predictions == 0) & (
                                (df_strategy['prob_0'] > confidence_threshold) | 
                                (rsi_overbought & (df_strategy['prob_0'] > (confidence_threshold - rsi_confidence_boost)))
                            )
                        else:
                            # Nếu không có RSI, chỉ dùng xác suất
                            sell_signals = (predictions == 0) & (df_strategy['prob_0'] > confidence_threshold)
                        
                        df_strategy.loc[sell_signals, 'signal'] = -1
                        
                    logger.info(f"Áp dụng ngưỡng tin cậy {confidence_threshold} cho tín hiệu")
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý xác suất dự đoán: {str(e)}")
                    # Nếu không thể xử lý xác suất, sử dụng dự đoán nguyên gốc
                    df_strategy['signal'] = predictions
            else:
                # Nếu mô hình không hỗ trợ predict_proba, áp dụng logic khác
                logger.info("Mô hình không hỗ trợ predict_proba, sử dụng tín hiệu dự đoán trực tiếp")
                df_strategy['signal'] = predictions
            
            return df_strategy
            
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng chiến lược ML: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return df.assign(signal=0)  # Trả về DataFrame với tín hiệu 0 (không có tín hiệu)
    
    def _apply_high_risk_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Áp dụng chiến lược rủi ro cao
        Kết hợp RSI, Bollinger và biến động giá với các ngưỡng quyết liệt hơn
        
        Args:
            df: DataFrame với các chỉ báo
            
        Returns:
            DataFrame với tín hiệu
        """
        df_strategy = df.copy()
        
        # Khởi tạo cột tín hiệu
        df_strategy['signal'] = 0
        
        # Các điều kiện mua mạnh
        buy_conditions = (
            (df_strategy['rsi'] < 25) &  # RSI quá bán mạnh
            (df_strategy['close'] < df_strategy['lower_band']) &  # Giá dưới dải dưới
            (df_strategy['volume_ratio'] > 1.5)  # Khối lượng tăng
        )
        
        # Các điều kiện bán mạnh
        sell_conditions = (
            (df_strategy['rsi'] > 75) &  # RSI quá mua mạnh
            (df_strategy['close'] > df_strategy['upper_band']) &  # Giá trên dải trên
            (df_strategy['volume_ratio'] > 1.5)  # Khối lượng tăng
        )
        
        # Đặt tín hiệu
        df_strategy.loc[buy_conditions, 'signal'] = 1
        df_strategy.loc[sell_conditions, 'signal'] = -1
        
        return df_strategy
    
    def backtest_strategy(self, df: pd.DataFrame, strategy_func, initial_balance: float = 10000,
                       risk_pct: float = 5, leverage: float = 1, plot: bool = True,
                       plot_filename: str = None) -> Dict:
        """
        Thực hiện backtest cho một chiến lược
        
        Args:
            df: DataFrame với dữ liệu giá và chỉ báo
            strategy_func: Hàm áp dụng chiến lược (trả về DataFrame với cột 'signal')
            initial_balance: Số dư ban đầu
            risk_pct: Phần trăm rủi ro mỗi lệnh
            leverage: Đòn bẩy
            plot: Vẽ biểu đồ hay không
            plot_filename: Tên file để lưu biểu đồ
            
        Returns:
            Dict chứa kết quả backtest
        """
        try:
            start_time = time.time()
            
            # Áp dụng chiến lược để lấy tín hiệu
            if callable(strategy_func):
                df_strategy = strategy_func(df)
            else:
                df_strategy = df.copy()
                # Fix lỗi 'predictions' không được định nghĩa trong backtest_strategy
                if 'predictions' in locals():
                    df_strategy['signal'] = predictions
                else:
                    df_strategy['signal'] = 0  # Sử dụng 0 làm giá trị mặc định nếu không có predictions
            
            # Khởi tạo các biến theo dõi
            balance = float(initial_balance)
            position = 0.0
            entry_price = 0.0
            position_type = None  # 'long' hoặc 'short'
            position_start_index = 0
            
            trades = []
            balance_history = [balance]
            equity_history = [balance]
            
            # Tính toán kích thước vị thế dựa trên rủi ro
            risk_factor = risk_pct / 100.0
            position_size_pct = risk_factor * leverage
            
            # Khởi tạo helper cho quản lý risk nếu dùng trong chiến lược tích hợp mới
            risk_manager = None
            if 'atr' in df_strategy.columns:
                risk_manager = AdaptiveRiskManager()
            
            # Thiết lập stop loss và take profit mặc định
            default_stop_loss_pct = 0.05  # 5%
            default_take_profit_pct = 0.1  # 10%
            
            # Vòng lặp qua từng nến
            for i in range(1, len(df_strategy)):
                # Cập nhật giá hiện tại
                current_price = float(df_strategy['close'].iloc[i])
                current_signal = df_strategy['signal'].iloc[i]
                
                # Tính toán equity (số dư + giá trị vị thế)
                if position != 0 and position_type == 'long':
                    equity = balance + position * (current_price - entry_price)
                elif position != 0 and position_type == 'short':
                    equity = balance + position * (entry_price - current_price)
                else:
                    equity = balance
                
                equity_history.append(equity)
                
                # Nếu đang có vị thế, kiểm tra điều kiện đóng vị thế
                if position != 0:
                    # Tính toán P/L hiện tại
                    if position_type == 'long':
                        pnl_pct = (current_price / entry_price - 1) * 100
                        
                        # Sử dụng ATR nếu có, ngược lại dùng % cố định
                        if risk_manager is not None and 'atr' in df_strategy.columns and 'market_regime' in df_strategy.columns:
                            # Lấy chế độ thị trường hiện tại
                            market_regime = df_strategy['market_regime'].iloc[i]
                            
                            # Tính SL/TP thích ứng dựa trên ATR
                            stop_loss_price = risk_manager.calculate_adaptive_stoploss(
                                df_strategy.iloc[i-5:i+1], 'long', entry_price, market_regime, 2.0)
                            
                            take_profit_price = risk_manager.calculate_adaptive_takeprofit(
                                df_strategy.iloc[i-5:i+1], 'long', entry_price, market_regime, 2.5)
                        else:
                            # Dùng % cố định khi không có ATR
                            stop_loss_price = entry_price * (1 - default_stop_loss_pct)
                            take_profit_price = entry_price * (1 + default_take_profit_pct)
                        
                        # Kiểm tra stop loss
                        if current_price <= stop_loss_price:
                            # Đóng vị thế với stop loss
                            pnl = position * (current_price - entry_price)
                            balance += pnl
                            
                            trades.append({
                                'type': 'long',
                                'entry_idx': position_start_index,
                                'exit_idx': i,
                                'entry_price': entry_price,
                                'exit_price': current_price,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'exit_reason': 'stop_loss',
                                'balance': balance
                            })
                            
                            position = 0
                            position_type = None
                            
                        # Kiểm tra take profit
                        elif current_price >= take_profit_price:
                            # Đóng vị thế với take profit
                            pnl = position * (current_price - entry_price)
                            balance += pnl
                            
                            trades.append({
                                'type': 'long',
                                'entry_idx': position_start_index,
                                'exit_idx': i,
                                'entry_price': entry_price,
                                'exit_price': current_price,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'exit_reason': 'take_profit',
                                'balance': balance
                            })
                            
                            position = 0
                            position_type = None
                            
                        # Kiểm tra tín hiệu đảo chiều
                        elif current_signal == -1:
                            # Đóng vị thế long và mở vị thế short
                            pnl = position * (current_price - entry_price)
                            balance += pnl
                            
                            trades.append({
                                'type': 'long',
                                'entry_idx': position_start_index,
                                'exit_idx': i,
                                'entry_price': entry_price,
                                'exit_price': current_price,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'exit_reason': 'signal_reverse',
                                'balance': balance
                            })
                            
                            # Mở vị thế short mới
                            position_size_usd = balance * position_size_pct
                            position = position_size_usd / current_price
                            position = -position  # Đảo dấu cho vị thế short
                            entry_price = current_price
                            position_type = 'short'
                            position_start_index = i
                    
                    elif position_type == 'short':
                        pnl_pct = (entry_price / current_price - 1) * 100
                        
                        # Sử dụng ATR nếu có, ngược lại dùng % cố định
                        if risk_manager is not None and 'atr' in df_strategy.columns and 'market_regime' in df_strategy.columns:
                            # Lấy chế độ thị trường hiện tại
                            market_regime = df_strategy['market_regime'].iloc[i]
                            
                            # Tính SL/TP thích ứng dựa trên ATR
                            stop_loss_price = risk_manager.calculate_adaptive_stoploss(
                                df_strategy.iloc[i-5:i+1], 'short', entry_price, market_regime, 2.0)
                            
                            take_profit_price = risk_manager.calculate_adaptive_takeprofit(
                                df_strategy.iloc[i-5:i+1], 'short', entry_price, market_regime, 2.5)
                        else:
                            # Dùng % cố định khi không có ATR
                            stop_loss_price = entry_price * (1 + default_stop_loss_pct)
                            take_profit_price = entry_price * (1 - default_take_profit_pct)
                        
                        # Kiểm tra stop loss
                        if current_price >= stop_loss_price:
                            # Đóng vị thế với stop loss
                            pnl = -position * (current_price - entry_price)
                            balance += pnl
                            
                            trades.append({
                                'type': 'short',
                                'entry_idx': position_start_index,
                                'exit_idx': i,
                                'entry_price': entry_price,
                                'exit_price': current_price,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'exit_reason': 'stop_loss',
                                'balance': balance
                            })
                            
                            position = 0
                            position_type = None
                            
                        # Kiểm tra take profit
                        elif current_price <= take_profit_price:
                            # Đóng vị thế với take profit
                            pnl = -position * (current_price - entry_price)
                            balance += pnl
                            
                            trades.append({
                                'type': 'short',
                                'entry_idx': position_start_index,
                                'exit_idx': i,
                                'entry_price': entry_price,
                                'exit_price': current_price,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'exit_reason': 'take_profit',
                                'balance': balance
                            })
                            
                            position = 0
                            position_type = None
                            
                        # Kiểm tra tín hiệu đảo chiều
                        elif current_signal == 1:
                            # Đóng vị thế short và mở vị thế long
                            pnl = -position * (current_price - entry_price)
                            balance += pnl
                            
                            trades.append({
                                'type': 'short',
                                'entry_idx': position_start_index,
                                'exit_idx': i,
                                'entry_price': entry_price,
                                'exit_price': current_price,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'exit_reason': 'signal_reverse',
                                'balance': balance
                            })
                            
                            # Mở vị thế long mới
                            position_size_usd = balance * position_size_pct
                            position = position_size_usd / current_price
                            entry_price = current_price
                            position_type = 'long'
                            position_start_index = i
                
                # Nếu không có vị thế, kiểm tra tín hiệu mở vị thế mới
                elif position == 0:
                    if current_signal == 1:  # Tín hiệu mua
                        position_size_usd = balance * position_size_pct
                        position = position_size_usd / current_price
                        entry_price = current_price
                        position_type = 'long'
                        position_start_index = i
                        
                    elif current_signal == -1:  # Tín hiệu bán
                        position_size_usd = balance * position_size_pct
                        position = -position_size_usd / current_price  # Đảo dấu cho vị thế short
                        entry_price = current_price
                        position_type = 'short'
                        position_start_index = i
                
                # Cập nhật lịch sử số dư
                balance_history.append(balance)
            
            # Đóng vị thế cuối cùng nếu còn
            if position != 0:
                current_price = float(df_strategy['close'].iloc[-1])
                
                if position_type == 'long':
                    pnl = position * (current_price - entry_price)
                    pnl_pct = (current_price / entry_price - 1) * 100
                else:  # short
                    pnl = -position * (current_price - entry_price)
                    pnl_pct = (entry_price / current_price - 1) * 100
                
                balance += pnl
                
                trades.append({
                    'type': position_type,
                    'entry_idx': position_start_index,
                    'exit_idx': len(df_strategy) - 1,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'exit_reason': 'end_of_data',
                    'balance': balance
                })
            
            # Tính các số liệu hiệu suất
            final_balance = balance
            profit_loss = final_balance - initial_balance
            profit_pct = (final_balance / initial_balance - 1) * 100
            
            # Tính drawdown
            peak = initial_balance
            drawdown = 0
            max_drawdown = 0
            
            for bal in balance_history:
                if bal > peak:
                    peak = bal
                
                dd = (peak - bal) / peak * 100 if peak > 0 else 0
                drawdown = dd
                
                if dd > max_drawdown:
                    max_drawdown = dd
            
            # Tính win rate và profit factor
            if len(trades) > 0:
                win_trades = [t for t in trades if t['pnl'] > 0]
                win_rate = len(win_trades) / len(trades) * 100
                
                total_win = sum(t['pnl'] for t in win_trades) if win_trades else 0
                
                lose_trades = [t for t in trades if t['pnl'] <= 0]
                total_loss = sum(abs(t['pnl']) for t in lose_trades) if lose_trades else 0
                
                profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
                
                avg_win = total_win / len(win_trades) if win_trades else 0
                avg_loss = total_loss / len(lose_trades) if lose_trades else 0
                
                avg_win_pct = sum(t['pnl_pct'] for t in win_trades) / len(win_trades) if win_trades else 0
                avg_loss_pct = sum(abs(t['pnl_pct']) for t in lose_trades) / len(lose_trades) if lose_trades else 0
                
                # Tính Sharpe Ratio
                returns = np.diff(np.array(equity_history)) / np.array(equity_history)[:-1]
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
                
                # Tạo bảng tổng hợp các chỉ số
                stats = {
                    'total_trades': len(trades),
                    'win_trades': len(win_trades),
                    'lose_trades': len(lose_trades),
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'avg_win_pct': avg_win_pct,
                    'avg_loss_pct': avg_loss_pct,
                    'largest_win': max([t['pnl'] for t in win_trades]) if win_trades else 0,
                    'largest_loss': min([t['pnl'] for t in lose_trades]) if lose_trades else 0,
                    'largest_win_pct': max([t['pnl_pct'] for t in win_trades]) if win_trades else 0,
                    'largest_loss_pct': min([t['pnl_pct'] for t in lose_trades]) if lose_trades else 0,
                    'sharpe_ratio': sharpe_ratio
                }
            else:
                stats = {
                    'total_trades': 0,
                    'win_trades': 0,
                    'lose_trades': 0,
                    'win_rate': 0,
                    'profit_factor': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'avg_win_pct': 0,
                    'avg_loss_pct': 0,
                    'largest_win': 0,
                    'largest_loss': 0,
                    'largest_win_pct': 0,
                    'largest_loss_pct': 0,
                    'sharpe_ratio': 0
                }
            
            # Vẽ biểu đồ nếu cần
            if plot:
                self._plot_backtest_results(df_strategy, trades, balance_history, equity_history, 
                                         profit_pct, max_drawdown, stats, plot_filename)
            
            # Tạo kết quả
            results = {
                'initial_balance': initial_balance,
                'final_balance': final_balance,
                'profit_loss': profit_loss,
                'profit_pct': profit_pct,
                'max_drawdown': max_drawdown,
                'trades': trades,
                'stats': stats,
                'execution_time': time.time() - start_time
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện backtest: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'initial_balance': initial_balance,
                'final_balance': initial_balance,
                'profit_loss': 0,
                'profit_pct': 0,
                'max_drawdown': 0,
                'trades': [],
                'stats': {},
                'error': str(e)
            }
    
    def _plot_backtest_results(self, df: pd.DataFrame, trades: List[Dict], 
                            balance_history: List[float], equity_history: List[float],
                            profit_pct: float, max_drawdown: float, stats: Dict,
                            filename: str = None):
        """
        Vẽ biểu đồ kết quả backtest
        
        Args:
            df: DataFrame với dữ liệu giá và tín hiệu
            trades: Danh sách giao dịch
            balance_history: Lịch sử số dư
            equity_history: Lịch sử giá trị tài khoản
            profit_pct: Phần trăm lợi nhuận
            max_drawdown: Drawdown tối đa
            stats: Thống kê hiệu suất
            filename: Tên file để lưu biểu đồ
        """
        try:
            # Tạo figure với 3 subplot
            fig = plt.figure(figsize=(15, 12))
            
            # Subplot 1: Giá và tín hiệu
            ax1 = plt.subplot2grid((3, 1), (0, 0), rowspan=2)
            
            # Vẽ giá
            ax1.plot(df.index, df['close'], label='Giá đóng cửa')
            
            # Thêm Bollinger Bands nếu có
            if 'upper_band' in df.columns and 'lower_band' in df.columns:
                ax1.plot(df.index, df['upper_band'], 'r--', alpha=0.3)
                ax1.plot(df.index, df['lower_band'], 'g--', alpha=0.3)
            
            # Vẽ các điểm vào lệnh và thoát lệnh
            for trade in trades:
                entry_idx = trade['entry_idx']
                exit_idx = trade['exit_idx']
                
                entry_date = df.index[entry_idx]
                exit_date = df.index[exit_idx]
                
                entry_price = trade['entry_price']
                exit_price = trade['exit_price']
                
                if trade['type'] == 'long':
                    marker_color = 'green' if trade['pnl'] > 0 else 'red'
                    # Điểm vào lệnh
                    ax1.scatter(entry_date, entry_price, marker='^', color='blue', s=100)
                    # Điểm thoát lệnh
                    ax1.scatter(exit_date, exit_price, marker='v', color=marker_color, s=100)
                    # Đường nối
                    ax1.plot([entry_date, exit_date], [entry_price, exit_price], 
                            color=marker_color, linestyle='--', alpha=0.5)
                else:  # short
                    marker_color = 'green' if trade['pnl'] > 0 else 'red'
                    # Điểm vào lệnh
                    ax1.scatter(entry_date, entry_price, marker='v', color='blue', s=100)
                    # Điểm thoát lệnh
                    ax1.scatter(exit_date, exit_price, marker='^', color=marker_color, s=100)
                    # Đường nối
                    ax1.plot([entry_date, exit_date], [entry_price, exit_price], 
                            color=marker_color, linestyle='--', alpha=0.5)
            
            # Chú thích
            ax1.set_title('Backtest Results')
            ax1.set_ylabel('Giá')
            ax1.grid(True)
            ax1.legend()
            
            # Subplot 2: Số dư và Equity
            ax2 = plt.subplot2grid((3, 1), (2, 0))
            
            # Vẽ số dư và equity
            ax2.plot(df.index[:len(balance_history)], balance_history, label='Số dư')
            ax2.plot(df.index[:len(equity_history)], equity_history, label='Equity', alpha=0.7)
            
            ax2.set_ylabel('Số dư/Equity')
            ax2.grid(True)
            ax2.legend()
            
            # Thêm thông tin tổng quan
            textstr = '\n'.join((
                f'Lợi nhuận: {profit_pct:.2f}%',
                f'Drawdown tối đa: {max_drawdown:.2f}%',
                f'Số lệnh: {stats["total_trades"]}',
                f'Win rate: {stats["win_rate"]:.2f}%',
                f'Profit factor: {stats["profit_factor"]:.2f}',
                f'Sharpe ratio: {stats["sharpe_ratio"]:.2f}'
            ))
            
            # Đặt text box
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax1.text(0.02, 0.03, textstr, transform=ax1.transAxes, fontsize=10,
                    verticalalignment='bottom', bbox=props)
            
            plt.tight_layout()
            
            # Lưu biểu đồ nếu có tên file
            if filename:
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                logger.info(f"Đã lưu biểu đồ tại {filename}")
            
            plt.close()
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ: {str(e)}")
    
    def compare_strategies(self, symbol: str, interval: str, lookback_days: int = 60,
                        ml_model_name: str = None, risk_pct: float = 5, 
                        leverage: float = 1) -> Dict:
        """
        So sánh hiệu suất của các chiến lược khác nhau
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            lookback_days: Số ngày lịch sử
            ml_model_name: Tên mô hình ML (nếu None, không dùng ML)
            risk_pct: Phần trăm rủi ro mỗi lệnh
            leverage: Đòn bẩy
            
        Returns:
            Dict chứa kết quả so sánh
        """
        try:
            logger.info(f"So sánh các chiến lược cho {symbol} {interval}")
            
            # Chuẩn bị dữ liệu
            df = self.prepare_data_for_backtesting(symbol, interval, lookback_days)
            
            if df is None:
                logger.error(f"Không thể chuẩn bị dữ liệu cho {symbol} {interval}")
                return {"error": "No data available"}
            
            # Tạo danh sách chiến lược cần so sánh
            strategies = {
                "rsi": self._apply_rsi_strategy,
                "macd": self._apply_macd_strategy,
                "bollinger": self._apply_bollinger_strategy,
                "combined": self._apply_combined_strategy,
                "high_risk": self._apply_high_risk_strategy
            }
            
            # Thêm chiến lược ML nếu cung cấp tên mô hình
            if ml_model_name:
                # Tải mô hình
                model, scaler, features = self.load_model(ml_model_name)
                
                if model is not None:
                    # Tạo hàm áp dụng chiến lược ML
                    ml_strategy_func = lambda df: self._apply_ml_strategy(df, model, scaler, features)
                    strategies["ml"] = ml_strategy_func
                    logger.info(f"Đã thêm chiến lược ML sử dụng mô hình {ml_model_name}")
                else:
                    logger.warning(f"Không thể tải mô hình {ml_model_name}")
            
            # Chạy backtest cho từng chiến lược
            results = {}
            initial_balance = 10000  # Số dư ban đầu đồng nhất
            
            for strategy_name, strategy_func in strategies.items():
                logger.info(f"Backtest chiến lược {strategy_name}")
                
                # Đặt tên file cho biểu đồ
                plot_filename = os.path.join(
                    self.test_charts_dir, 
                    f"{symbol}_{interval}_{strategy_name}_backtest.png"
                )
                
                # Chạy backtest
                strategy_result = self.backtest_strategy(
                    df=df,
                    strategy_func=strategy_func,
                    initial_balance=initial_balance,
                    risk_pct=risk_pct,
                    leverage=leverage,
                    plot=True,
                    plot_filename=plot_filename
                )
                
                # Lưu kết quả
                results[strategy_name] = strategy_result
                
                logger.info(f"Chiến lược {strategy_name}: PnL={strategy_result['profit_pct']:.2f}%, "
                          f"Trades={strategy_result['stats']['total_trades']}, "
                          f"Win Rate={strategy_result['stats']['win_rate']:.2f}%")
            
            # Đánh giá hiệu suất tương đối
            performance_ranking = sorted(
                results.items(), 
                key=lambda x: x[1]['profit_pct'], 
                reverse=True
            )
            
            # Tạo báo cáo so sánh
            comparison = {
                'symbol': symbol,
                'interval': interval,
                'lookback_days': lookback_days,
                'risk_pct': risk_pct,
                'leverage': leverage,
                'ml_model': ml_model_name,
                'ranking': [],
                'detailed_results': results
            }
            
            # Thêm thông tin xếp hạng
            for i, (strategy, result) in enumerate(performance_ranking):
                comparison['ranking'].append({
                    'rank': i + 1,
                    'strategy': strategy,
                    'profit_pct': result['profit_pct'],
                    'max_drawdown': result['max_drawdown'],
                    'win_rate': result['stats']['win_rate'],
                    'profit_factor': result['stats']['profit_factor'],
                    'trades': result['stats']['total_trades'],
                    'sharpe_ratio': result['stats']['sharpe_ratio']
                })
            
            # Lưu kết quả
            result_filename = os.path.join(
                self.test_results_dir,
                f"{symbol}_{interval}_strategy_comparison.json"
            )
            
            with open(result_filename, 'w') as f:
                json.dump(comparison, f, indent=2)
                
            logger.info(f"Đã lưu kết quả so sánh tại {result_filename}")
            
            # Vẽ biểu đồ so sánh
            self._plot_strategy_comparison(comparison)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Lỗi khi so sánh các chiến lược: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def _plot_strategy_comparison(self, comparison: Dict):
        """
        Vẽ biểu đồ so sánh các chiến lược
        
        Args:
            comparison: Dict chứa kết quả so sánh
        """
        try:
            symbol = comparison['symbol']
            interval = comparison['interval']
            
            # Trích xuất dữ liệu
            strategies = [item['strategy'] for item in comparison['ranking']]
            profits = [item['profit_pct'] for item in comparison['ranking']]
            drawdowns = [item['max_drawdown'] for item in comparison['ranking']]
            win_rates = [item['win_rate'] for item in comparison['ranking']]
            trades = [item['trades'] for item in comparison['ranking']]
            
            # Tạo các biểu đồ
            
            # 1. Biểu đồ lợi nhuận
            plt.figure(figsize=(12, 6))
            colors = ['green' if p > 0 else 'red' for p in profits]
            plt.bar(strategies, profits, color=colors)
            plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
            plt.title(f'Lợi nhuận theo Chiến lược - {symbol} {interval}')
            plt.ylabel('Lợi nhuận (%)')
            plt.xticks(rotation=45)
            
            # Thêm nhãn giá trị
            for i, p in enumerate(profits):
                plt.text(i, p + (1 if p >= 0 else -3), f"{p:.2f}%", ha='center')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.test_charts_dir, f"{symbol}_{interval}_profit_comparison.png"), dpi=300)
            plt.close()
            
            # 2. Biểu đồ drawdown
            plt.figure(figsize=(12, 6))
            plt.bar(strategies, drawdowns, color='red')
            plt.title(f'Drawdown tối đa theo Chiến lược - {symbol} {interval}')
            plt.ylabel('Drawdown (%)')
            plt.xticks(rotation=45)
            
            # Thêm nhãn giá trị
            for i, d in enumerate(drawdowns):
                plt.text(i, d + 0.5, f"{d:.2f}%", ha='center')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.test_charts_dir, f"{symbol}_{interval}_drawdown_comparison.png"), dpi=300)
            plt.close()
            
            # 3. Biểu đồ win rate và số lệnh
            fig, ax1 = plt.subplots(figsize=(12, 6))
            
            # Win rate (trục y trái)
            x = np.arange(len(strategies))
            ax1.bar(x - 0.2, win_rates, width=0.4, color='blue', label='Win Rate')
            ax1.set_ylabel('Win Rate (%)', color='blue')
            ax1.tick_params(axis='y', labelcolor='blue')
            
            # Số lệnh (trục y phải)
            ax2 = ax1.twinx()
            ax2.bar(x + 0.2, trades, width=0.4, color='orange', label='Số lệnh')
            ax2.set_ylabel('Số lệnh', color='orange')
            ax2.tick_params(axis='y', labelcolor='orange')
            
            # Nhãn trục x
            plt.xticks(x, strategies, rotation=45)
            plt.title(f'Win Rate và Số lệnh theo Chiến lược - {symbol} {interval}')
            
            # Thêm legend
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.test_charts_dir, f"{symbol}_{interval}_winrate_trades_comparison.png"), dpi=300)
            plt.close()
            
            # 4. Biểu đồ tổng hợp các chỉ số
            # Lấy các chỉ số quan trọng cho mỗi chiến lược
            metrics = ['profit_pct', 'win_rate', 'profit_factor', 'sharpe_ratio']
            metric_labels = ['Lợi nhuận (%)', 'Win Rate (%)', 'Profit Factor', 'Sharpe Ratio']
            
            # Chuẩn hóa dữ liệu để có thể so sánh
            normalized_data = []
            
            for metric in metrics:
                if metric == 'profit_pct':
                    values = [item[metric] for item in comparison['ranking']]
                elif metric in ['win_rate', 'sharpe_ratio']:
                    values = [item[metric] for item in comparison['ranking']]
                else:  # profit_factor
                    values = [min(item[metric], 5) for item in comparison['ranking']]  # Giới hạn Profit Factor
                
                # Chuẩn hóa (nếu có giá trị âm, dùng phép biến đổi khác)
                min_val = min(values)
                max_val = max(values)
                
                if min_val < 0:
                    # Có giá trị âm, dùng phép biến đổi khác
                    abs_max = max(abs(min_val), abs(max_val))
                    norm_values = [v / abs_max * 0.5 + 0.5 for v in values]
                else:
                    # Toàn giá trị dương
                    if max_val == min_val:
                        norm_values = [0.5 for _ in values]
                    else:
                        norm_values = [(v - min_val) / (max_val - min_val) for v in values]
                
                normalized_data.append(norm_values)
            
            # Tạo radar chart
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, polar=True)
            
            # Số lượng biến
            N = len(metrics)
            
            # Góc cho mỗi trục
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]  # Đóng vòng tròn
            
            # Vẽ cho từng chiến lược
            for i, strategy in enumerate(strategies):
                values = [normalized_data[j][i] for j in range(N)]
                values += values[:1]  # Đóng vòng tròn
                
                ax.plot(angles, values, linewidth=2, linestyle='solid', label=strategy)
                ax.fill(angles, values, alpha=0.1)
            
            # Thiết lập các trục
            plt.xticks(angles[:-1], metric_labels)
            
            # Thêm legend
            plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
            
            plt.title(f'So sánh hiệu suất chiến lược - {symbol} {interval}')
            plt.tight_layout()
            
            plt.savefig(os.path.join(self.test_charts_dir, f"{symbol}_{interval}_radar_comparison.png"), dpi=300)
            plt.close()
            
            logger.info(f"Đã tạo các biểu đồ so sánh cho {symbol} {interval}")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ so sánh: {str(e)}")
    
    def compare_multiple_ml_models(self, symbol: str, interval: str, lookback_days: int = 60,
                                risk_pct: float = 5, leverage: float = 1) -> Dict:
        """
        So sánh hiệu suất của nhiều mô hình ML khác nhau
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            lookback_days: Số ngày lịch sử
            risk_pct: Phần trăm rủi ro mỗi lệnh
            leverage: Đòn bẩy
            
        Returns:
            Dict chứa kết quả so sánh
        """
        try:
            logger.info(f"So sánh các mô hình ML cho {symbol} {interval}")
            
            # Tìm tất cả các mô hình phù hợp với symbol và interval
            model_files = glob.glob(os.path.join(self.models_dir, f"{symbol}_{interval}_*_model.joblib"))
            
            if not model_files:
                logger.warning(f"Không tìm thấy mô hình nào cho {symbol} {interval}")
                return {"error": "No models found"}
            
            # Trích xuất tên mô hình (bỏ đuôi "_model.joblib")
            model_names = [os.path.basename(f).replace("_model.joblib", "") for f in model_files]
            
            logger.info(f"Tìm thấy {len(model_names)} mô hình: {model_names}")
            
            # Chuẩn bị dữ liệu
            df = self.prepare_data_for_backtesting(symbol, interval, lookback_days)
            
            if df is None:
                logger.error(f"Không thể chuẩn bị dữ liệu cho {symbol} {interval}")
                return {"error": "No data available"}
            
            # Chạy backtest cho từng mô hình
            results = {}
            initial_balance = 10000  # Số dư ban đầu đồng nhất
            
            for model_name in model_names:
                logger.info(f"Backtest mô hình {model_name}")
                
                # Tải mô hình
                model, scaler, features = self.load_model(model_name)
                
                if model is None:
                    logger.warning(f"Không thể tải mô hình {model_name}")
                    continue
                
                # Tạo hàm áp dụng chiến lược ML
                ml_strategy_func = lambda df: self._apply_ml_strategy(df, model, scaler, features)
                
                # Đặt tên file cho biểu đồ
                plot_filename = os.path.join(
                    self.test_charts_dir, 
                    f"{model_name}_backtest.png"
                )
                
                # Chạy backtest
                strategy_result = self.backtest_strategy(
                    df=df,
                    strategy_func=ml_strategy_func,
                    initial_balance=initial_balance,
                    risk_pct=risk_pct,
                    leverage=leverage,
                    plot=True,
                    plot_filename=plot_filename
                )
                
                # Lưu kết quả
                results[model_name] = strategy_result
                
                logger.info(f"Mô hình {model_name}: PnL={strategy_result['profit_pct']:.2f}%, "
                          f"Trades={strategy_result['stats']['total_trades']}, "
                          f"Win Rate={strategy_result['stats']['win_rate']:.2f}%")
            
            # Thêm chiến lược rủi ro cao để so sánh
            high_risk_result = self.backtest_strategy(
                df=df,
                strategy_func=self._apply_high_risk_strategy,
                initial_balance=initial_balance,
                risk_pct=risk_pct,
                leverage=leverage,
                plot=True,
                plot_filename=os.path.join(self.test_charts_dir, f"{symbol}_{interval}_high_risk_backtest.png")
            )
            
            results["high_risk"] = high_risk_result
            
            # Đánh giá hiệu suất tương đối
            performance_ranking = sorted(
                results.items(), 
                key=lambda x: x[1]['profit_pct'], 
                reverse=True
            )
            
            # Tạo báo cáo so sánh
            comparison = {
                'symbol': symbol,
                'interval': interval,
                'lookback_days': lookback_days,
                'risk_pct': risk_pct,
                'leverage': leverage,
                'ranking': [],
                'detailed_results': results
            }
            
            # Thêm thông tin xếp hạng
            for i, (model, result) in enumerate(performance_ranking):
                comparison['ranking'].append({
                    'rank': i + 1,
                    'model': model,
                    'profit_pct': result['profit_pct'],
                    'max_drawdown': result['max_drawdown'],
                    'win_rate': result['stats']['win_rate'],
                    'profit_factor': result['stats']['profit_factor'],
                    'trades': result['stats']['total_trades'],
                    'sharpe_ratio': result['stats']['sharpe_ratio']
                })
            
            # Lưu kết quả
            result_filename = os.path.join(
                self.test_results_dir,
                f"{symbol}_{interval}_ml_model_comparison.json"
            )
            
            with open(result_filename, 'w') as f:
                json.dump(comparison, f, indent=2)
                
            logger.info(f"Đã lưu kết quả so sánh tại {result_filename}")
            
            # Vẽ biểu đồ so sánh
            self._plot_ml_model_comparison(comparison)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Lỗi khi so sánh các mô hình ML: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def _plot_ml_model_comparison(self, comparison: Dict):
        """
        Vẽ biểu đồ so sánh các mô hình ML
        
        Args:
            comparison: Dict chứa kết quả so sánh
        """
        try:
            symbol = comparison['symbol']
            interval = comparison['interval']
            
            # Trích xuất dữ liệu
            models = [item['model'] for item in comparison['ranking']]
            profits = [item['profit_pct'] for item in comparison['ranking']]
            drawdowns = [item['max_drawdown'] for item in comparison['ranking']]
            win_rates = [item['win_rate'] for item in comparison['ranking']]
            trades = [item['trades'] for item in comparison['ranking']]
            
            # Tạo nhãn ngắn gọn cho mô hình
            short_labels = []
            for model in models:
                if model == "high_risk":
                    short_labels.append("High Risk")
                else:
                    # Phân tích tên mô hình
                    parts = model.split('_')
                    # Tìm phần target và period
                    target = "?"
                    period = "?"
                    for part in parts:
                        if part.startswith("target"):
                            target = part.replace("target", "") + "d"
                        if part.endswith("m") or part.endswith("d"):
                            if not part.startswith("target"):
                                period = part
                    
                    short_labels.append(f"{period}-{target}")
            
            # 1. Biểu đồ lợi nhuận
            plt.figure(figsize=(12, 6))
            colors = ['green' if p > 0 else 'red' for p in profits]
            plt.bar(short_labels, profits, color=colors)
            plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
            plt.title(f'Lợi nhuận theo Mô hình - {symbol} {interval}')
            plt.ylabel('Lợi nhuận (%)')
            plt.xticks(rotation=45)
            
            # Thêm nhãn giá trị
            for i, p in enumerate(profits):
                plt.text(i, p + (1 if p >= 0 else -3), f"{p:.2f}%", ha='center')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.test_charts_dir, f"{symbol}_{interval}_ml_profit_comparison.png"), dpi=300)
            plt.close()
            
            # 2. Biểu đồ drawdown
            plt.figure(figsize=(12, 6))
            plt.bar(short_labels, drawdowns, color='red')
            plt.title(f'Drawdown tối đa theo Mô hình - {symbol} {interval}')
            plt.ylabel('Drawdown (%)')
            plt.xticks(rotation=45)
            
            # Thêm nhãn giá trị
            for i, d in enumerate(drawdowns):
                plt.text(i, d + 0.5, f"{d:.2f}%", ha='center')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.test_charts_dir, f"{symbol}_{interval}_ml_drawdown_comparison.png"), dpi=300)
            plt.close()
            
            # 3. Biểu đồ win rate và số lệnh
            fig, ax1 = plt.subplots(figsize=(12, 6))
            
            # Win rate (trục y trái)
            x = np.arange(len(short_labels))
            ax1.bar(x - 0.2, win_rates, width=0.4, color='blue', label='Win Rate')
            ax1.set_ylabel('Win Rate (%)', color='blue')
            ax1.tick_params(axis='y', labelcolor='blue')
            
            # Số lệnh (trục y phải)
            ax2 = ax1.twinx()
            ax2.bar(x + 0.2, trades, width=0.4, color='orange', label='Số lệnh')
            ax2.set_ylabel('Số lệnh', color='orange')
            ax2.tick_params(axis='y', labelcolor='orange')
            
            # Nhãn trục x
            plt.xticks(x, short_labels, rotation=45)
            plt.title(f'Win Rate và Số lệnh theo Mô hình - {symbol} {interval}')
            
            # Thêm legend
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.test_charts_dir, f"{symbol}_{interval}_ml_winrate_trades_comparison.png"), dpi=300)
            plt.close()
            
            logger.info(f"Đã tạo các biểu đồ so sánh mô hình ML cho {symbol} {interval}")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ so sánh mô hình ML: {str(e)}")
    
    def integrate_ml_with_high_risk(self, symbol: str, interval: str, 
                                 best_ml_model: str, lookback_days: int = 60,
                                 risk_pct: float = 10, leverage: float = 20) -> Dict:
        """
        Tích hợp mô hình ML với chiến lược rủi ro cao
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            best_ml_model: Tên mô hình ML tốt nhất
            lookback_days: Số ngày lịch sử
            risk_pct: Phần trăm rủi ro mỗi lệnh
            leverage: Đòn bẩy
            
        Returns:
            Dict chứa kết quả so sánh
        """
        try:
            logger.info(f"Tích hợp ML với chiến lược rủi ro cao cho {symbol} {interval}")
            
            # Tải mô hình ML tốt nhất
            model, scaler, features = self.load_model(best_ml_model)
            
            if model is None:
                logger.error(f"Không thể tải mô hình {best_ml_model}")
                return {"error": "Could not load ML model"}
            
            # Chuẩn bị dữ liệu
            df = self.prepare_data_for_backtesting(symbol, interval, lookback_days)
            
            if df is None:
                logger.error(f"Không thể chuẩn bị dữ liệu cho {symbol} {interval}")
                return {"error": "No data available"}
            
            # Tạo các hàm chiến lược
            ml_strategy_func = lambda df: self._apply_ml_strategy(df, model, scaler, features)
            high_risk_func = self._apply_high_risk_strategy
            
            # Khởi tạo các công cụ mới
            fib_analyzer = FibonacciAnalyzer(window_size=20, lookback=100)
            risk_manager = AdaptiveRiskManager(default_sl_pct=0.02, default_tp_pct=0.05, atr_periods=14)
            
            # Tích hợp ML với chiến lược rủi ro cao, RSI Boost, Fibonacci và ATR
            def integrated_strategy(df):
                # Áp dụng cả hai chiến lược
                df_ml = ml_strategy_func(df)
                df_high_risk = high_risk_func(df)
                
                # Tạo DataFrame kết quả
                df_integrated = df.copy()
                df_integrated['signal'] = 0
                
                # Thêm các chỉ báo mới
                # 1. Thêm ATR và các mức stop loss/take profit thích ứng
                df_integrated = add_atr_to_dataframe(df_integrated, atr_periods=14)
                
                # 2. Thêm phân tích Fibonacci
                df_integrated = add_fibonacci_signals(df_integrated, window_size=20, lookback=100)
                
                # Cải tiến 1: Tạo thêm tín hiệu mua/bán từ RSI với 3 mức độ
                strong_rsi_buy = (df['rsi'] < 20)  # RSI dưới 20: tín hiệu mua mạnh
                medium_rsi_buy = (df['rsi'] >= 20) & (df['rsi'] < 30)  # RSI 20-30: tín hiệu mua trung bình
                weak_rsi_buy = (df['rsi'] >= 30) & (df['rsi'] < 40)  # RSI 30-40: tín hiệu mua yếu
                
                strong_rsi_sell = (df['rsi'] > 80)  # RSI trên 80: tín hiệu bán mạnh
                medium_rsi_sell = (df['rsi'] <= 80) & (df['rsi'] > 70)  # RSI 70-80: tín hiệu bán trung bình
                weak_rsi_sell = (df['rsi'] <= 70) & (df['rsi'] > 60)  # RSI 60-70: tín hiệu bán yếu
                
                # Cải tiến 2: Phân loại chi tiết cho các chế độ thị trường
                market_regime = df['market_regime']
                trending_up = (market_regime == 'trending_up')
                trending_down = (market_regime == 'trending_down')
                ranging = (market_regime == 'ranging')
                volatile = (market_regime == 'volatile')
                neutral = (market_regime == 'neutral')
                
                # Cải tiến 3: Điều chỉnh tín hiệu ML dựa trên chế độ thị trường
                # Trong chế độ trending_up: Ưu tiên tín hiệu mua, bỏ qua một số tín hiệu bán
                # Trong chế độ trending_down: Ưu tiên tín hiệu bán, bỏ qua một số tín hiệu mua
                # Trong chế độ ranging: Ưu tiên tín hiệu đảo chiều khi giá đến vùng hỗ trợ/kháng cự
                # Trong chế độ volatile: Tăng ngưỡng xác nhận, tìm điểm đột phá
                
                # Cải tiến 4: Tích hợp Fibonacci vào quá trình ra quyết định
                # Lấy tín hiệu Fibonacci và các mức hỗ trợ/kháng cự
                fib_signals = df_integrated['fib_signal'].copy()
                fib_supports = df_integrated['fib_support'].fillna(0).copy()
                fib_resistances = df_integrated['fib_resistance'].fillna(0).copy()
                
                # Thêm tín hiệu giao dịch dựa trên tín hiệu Fibonacci
                fib_strong_buy_signal = (fib_signals == 1) & (df_integrated['trend'] > 0)
                
                fib_medium_buy_signal = (fib_supports > 0) & (df_integrated['close'] <= fib_supports * 1.01) & (df_integrated['trend'] > 0)
                
                fib_strong_sell_signal = (fib_signals == -1) & (df_integrated['trend'] < 0) 
                
                fib_medium_sell_signal = (fib_resistances > 0) & (df_integrated['close'] >= fib_resistances * 0.99) & (df_integrated['trend'] < 0)
                
                # Cải tiến 5: Tích hợp ATR cho quản lý rủi ro thích ứng
                # Lưu trữ các tham số ATR cho điều chỉnh stop loss/take profit sau này
                atr_values = df_integrated['atr'].copy()
                
                # Lấy tham số thích ứng theo chế độ thị trường
                risk_params = {}
                for i in range(len(df_integrated)):
                    regime = df_integrated['market_regime'].iloc[i]
                    # Lấy bội số ATR dựa trên chế độ thị trường
                    sl_multiplier, tp_multiplier = risk_manager.get_market_based_multipliers(regime)
                    risk_params[i] = {'sl_multiplier': sl_multiplier, 'tp_multiplier': tp_multiplier}
                
                # Điều kiện mua cho từng chế độ thị trường - tích hợp thêm Fibonacci
                trending_up_buy = trending_up & (
                    ((df_ml['signal'] == 1) & (fib_strong_buy_signal | fib_medium_buy_signal)) |  # ML tín hiệu mua + Fib hỗ trợ
                    ((df_high_risk['signal'] == 1) & fib_strong_buy_signal) |  # High Risk tín hiệu mua + Fib hỗ trợ mạnh
                    ((medium_rsi_buy | strong_rsi_buy) & fib_strong_buy_signal)  # RSI quá bán + Fib hỗ trợ mạnh
                )
                
                trending_down_buy = trending_down & (
                    ((df_ml['signal'] == 1) & strong_rsi_buy & fib_strong_buy_signal) |  # ML tín hiệu mua + RSI cực thấp + Fib hỗ trợ mạnh
                    ((df_high_risk['signal'] == 1) & strong_rsi_buy & fib_strong_buy_signal)  # High Risk tín hiệu mua + RSI cực thấp + Fib hỗ trợ mạnh
                )
                
                ranging_buy = ranging & (
                    ((df_ml['signal'] == 1) & (medium_rsi_buy | strong_rsi_buy) & fib_medium_buy_signal) |  # ML tín hiệu mua + RSI thấp + Fib hỗ trợ trung bình
                    ((df_high_risk['signal'] == 1) & (medium_rsi_buy | strong_rsi_buy) & fib_medium_buy_signal) |  # High Risk tín hiệu mua + RSI thấp + Fib hỗ trợ
                    (strong_rsi_buy & fib_strong_buy_signal)  # RSI cực thấp + Fib hỗ trợ mạnh
                )
                
                volatile_buy = volatile & (
                    ((df_ml['signal'] == 1) & (df_high_risk['signal'] == 1) & strong_rsi_buy & fib_strong_buy_signal) |  # Cả ML và High Risk đều có tín hiệu + RSI cực thấp + Fib hỗ trợ mạnh
                    ((df_ml['signal'] == 1) & strong_rsi_buy & fib_strong_buy_signal)  # ML tín hiệu mua + RSI cực thấp + Fib hỗ trợ mạnh
                )
                
                neutral_buy = neutral & (
                    ((df_ml['signal'] == 1) & medium_rsi_buy & (fib_strong_buy_signal | fib_medium_buy_signal)) |  # ML tín hiệu mua + RSI trung bình + Fib hỗ trợ
                    ((df_high_risk['signal'] == 1) & strong_rsi_buy & fib_strong_buy_signal)  # High Risk tín hiệu mua + RSI cực thấp + Fib hỗ trợ mạnh
                )
                
                # Điều kiện bán cho từng chế độ thị trường - tích hợp thêm Fibonacci
                trending_up_sell = trending_up & (
                    ((df_ml['signal'] == -1) & strong_rsi_sell & fib_strong_sell_signal) |  # ML tín hiệu bán + RSI cực cao + Fib kháng cự mạnh
                    ((df_high_risk['signal'] == -1) & strong_rsi_sell & fib_medium_sell_signal)  # High Risk tín hiệu bán + RSI cực cao + Fib kháng cự
                )
                
                trending_down_sell = trending_down & (
                    ((df_ml['signal'] == -1) & (fib_strong_sell_signal | fib_medium_sell_signal)) |  # ML tín hiệu bán + Fib kháng cự
                    ((df_high_risk['signal'] == -1) & fib_strong_sell_signal) |  # High Risk tín hiệu bán + Fib kháng cự mạnh
                    ((medium_rsi_sell | strong_rsi_sell) & fib_strong_sell_signal)  # RSI quá mua + Fib kháng cự mạnh
                )
                
                ranging_sell = ranging & (
                    ((df_ml['signal'] == -1) & (medium_rsi_sell | strong_rsi_sell) & fib_medium_sell_signal) |  # ML tín hiệu bán + RSI cao + Fib kháng cự trung bình
                    ((df_high_risk['signal'] == -1) & (medium_rsi_sell | strong_rsi_sell) & fib_medium_sell_signal) |  # High Risk tín hiệu bán + RSI cao + Fib kháng cự
                    (strong_rsi_sell & fib_strong_sell_signal)  # RSI cực cao + Fib kháng cự mạnh
                )
                
                volatile_sell = volatile & (
                    ((df_ml['signal'] == -1) & (df_high_risk['signal'] == -1) & strong_rsi_sell & fib_strong_sell_signal) |  # Cả ML và High Risk đều có tín hiệu + RSI cực cao + Fib kháng cự mạnh
                    ((df_ml['signal'] == -1) & strong_rsi_sell & fib_strong_sell_signal)  # ML tín hiệu bán + RSI cực cao + Fib kháng cự mạnh
                )
                
                neutral_sell = neutral & (
                    ((df_ml['signal'] == -1) & medium_rsi_sell & (fib_strong_sell_signal | fib_medium_sell_signal)) |  # ML tín hiệu bán + RSI cao-trung bình + Fib kháng cự
                    ((df_high_risk['signal'] == -1) & strong_rsi_sell & fib_strong_sell_signal)  # High Risk tín hiệu bán + RSI cực cao + Fib kháng cự mạnh
                )
                
                # Kết hợp tất cả các điều kiện mua/bán
                buy_condition = (
                    trending_up_buy | trending_down_buy | ranging_buy | volatile_buy | neutral_buy
                )
                
                sell_condition = (
                    trending_up_sell | trending_down_sell | ranging_sell | volatile_sell | neutral_sell
                )
                
                # Đặt tín hiệu
                df_integrated.loc[buy_condition, 'signal'] = 1
                df_integrated.loc[sell_condition, 'signal'] = -1
                
                return df_integrated
            
            # Chạy backtest cho từng chiến lược và chiến lược tích hợp
            results = {}
            initial_balance = 10000  # Số dư ban đầu đồng nhất
            
            # Backtest chiến lược ML
            ml_result = self.backtest_strategy(
                df=df,
                strategy_func=ml_strategy_func,
                initial_balance=initial_balance,
                risk_pct=risk_pct,
                leverage=leverage,
                plot=True,
                plot_filename=os.path.join(self.test_charts_dir, f"{symbol}_{interval}_ml_only_backtest.png")
            )
            
            results["ml_only"] = ml_result
            
            # Backtest chiến lược rủi ro cao
            high_risk_result = self.backtest_strategy(
                df=df,
                strategy_func=high_risk_func,
                initial_balance=initial_balance,
                risk_pct=risk_pct,
                leverage=leverage,
                plot=True,
                plot_filename=os.path.join(self.test_charts_dir, f"{symbol}_{interval}_high_risk_only_backtest.png")
            )
            
            results["high_risk_only"] = high_risk_result
            
            # Backtest chiến lược tích hợp
            integrated_result = self.backtest_strategy(
                df=df,
                strategy_func=integrated_strategy,
                initial_balance=initial_balance,
                risk_pct=risk_pct,
                leverage=leverage,
                plot=True,
                plot_filename=os.path.join(self.test_charts_dir, f"{symbol}_{interval}_integrated_backtest.png")
            )
            
            results["integrated"] = integrated_result
            
            # Đánh giá hiệu suất tương đối
            performance_ranking = sorted(
                results.items(), 
                key=lambda x: x[1]['profit_pct'], 
                reverse=True
            )
            
            # Tạo báo cáo so sánh
            comparison = {
                'symbol': symbol,
                'interval': interval,
                'lookback_days': lookback_days,
                'risk_pct': risk_pct,
                'leverage': leverage,
                'ml_model': best_ml_model,
                'ranking': [],
                'detailed_results': results
            }
            
            # Thêm thông tin xếp hạng
            for i, (strategy, result) in enumerate(performance_ranking):
                comparison['ranking'].append({
                    'rank': i + 1,
                    'strategy': strategy,
                    'profit_pct': result['profit_pct'],
                    'max_drawdown': result['max_drawdown'],
                    'win_rate': result['stats']['win_rate'],
                    'profit_factor': result['stats']['profit_factor'],
                    'trades': result['stats']['total_trades']
                })
            
            # Lưu kết quả
            result_filename = os.path.join(
                self.test_results_dir,
                f"{symbol}_{interval}_integration_test.json"
            )
            
            with open(result_filename, 'w') as f:
                json.dump(comparison, f, indent=2)
                
            logger.info(f"Đã lưu kết quả tích hợp tại {result_filename}")
            
            # Vẽ biểu đồ so sánh
            self._plot_integration_comparison(comparison)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Lỗi khi tích hợp ML với chiến lược rủi ro cao: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def _plot_integration_comparison(self, comparison: Dict):
        """
        Vẽ biểu đồ so sánh tích hợp
        
        Args:
            comparison: Dict chứa kết quả so sánh
        """
        try:
            symbol = comparison['symbol']
            interval = comparison['interval']
            
            # Trích xuất dữ liệu
            strategies = [item['strategy'] for item in comparison['ranking']]
            profits = [item['profit_pct'] for item in comparison['ranking']]
            drawdowns = [item['max_drawdown'] for item in comparison['ranking']]
            win_rates = [item['win_rate'] for item in comparison['ranking']]
            trades = [item['trades'] for item in comparison['ranking']]
            
            # Tạo nhãn thân thiện
            strategy_labels = {
                'ml_only': 'Chỉ ML',
                'high_risk_only': 'Chỉ Rủi ro cao',
                'integrated': 'ML + Rủi ro cao'
            }
            
            friendly_labels = [strategy_labels.get(s, s) for s in strategies]
            
            # 1. Biểu đồ lợi nhuận và drawdown
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
            
            # Biểu đồ lợi nhuận
            colors = ['green' if p > 0 else 'red' for p in profits]
            ax1.bar(friendly_labels, profits, color=colors)
            ax1.axhline(y=0, color='k', linestyle='--', alpha=0.3)
            ax1.set_title(f'Lợi nhuận theo Chiến lược - {symbol} {interval}')
            ax1.set_ylabel('Lợi nhuận (%)')
            
            # Thêm nhãn giá trị
            for i, p in enumerate(profits):
                ax1.text(i, p + (1 if p >= 0 else -3), f"{p:.2f}%", ha='center')
            
            # Biểu đồ drawdown
            ax2.bar(friendly_labels, drawdowns, color='red')
            ax2.set_title(f'Drawdown tối đa theo Chiến lược')
            ax2.set_ylabel('Drawdown (%)')
            
            # Thêm nhãn giá trị
            for i, d in enumerate(drawdowns):
                ax2.text(i, d + 0.5, f"{d:.2f}%", ha='center')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.test_charts_dir, f"{symbol}_{interval}_integration_profit_dd.png"), dpi=300)
            plt.close()
            
            # 2. Biểu đồ win rate và số lệnh
            fig, ax1 = plt.subplots(figsize=(10, 6))
            
            # Win rate (trục y trái)
            x = np.arange(len(friendly_labels))
            ax1.bar(x - 0.2, win_rates, width=0.4, color='blue', label='Win Rate')
            ax1.set_ylabel('Win Rate (%)', color='blue')
            ax1.tick_params(axis='y', labelcolor='blue')
            
            # Số lệnh (trục y phải)
            ax2 = ax1.twinx()
            ax2.bar(x + 0.2, trades, width=0.4, color='orange', label='Số lệnh')
            ax2.set_ylabel('Số lệnh', color='orange')
            ax2.tick_params(axis='y', labelcolor='orange')
            
            # Nhãn trục x
            plt.xticks(x, friendly_labels)
            plt.title(f'Win Rate và Số lệnh theo Chiến lược - {symbol} {interval}')
            
            # Thêm legend
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.test_charts_dir, f"{symbol}_{interval}_integration_winrate_trades.png"), dpi=300)
            plt.close()
            
            logger.info(f"Đã tạo các biểu đồ so sánh tích hợp cho {symbol} {interval}")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ so sánh tích hợp: {str(e)}")

def main():
    """Hàm chính"""
    # Thiết lập parser dòng lệnh
    parser = argparse.ArgumentParser(description='Kiểm thử chiến lược ML và so sánh với chiến lược khác')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã tiền (mặc định: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--lookback', type=int, default=60, help='Số ngày lịch sử (mặc định: 60)')
    parser.add_argument('--risk', type=float, default=5, help='Phần trăm rủi ro mỗi lệnh (mặc định: 5)')
    parser.add_argument('--leverage', type=float, default=1, help='Đòn bẩy (mặc định: 1)')
    parser.add_argument('--ml-model', type=str, help='Tên mô hình ML')
    parser.add_argument('--mode', type=str, choices=['compare', 'ml-compare', 'integrate'], default='compare',
                      help='Chế độ kiểm thử (mặc định: compare)')
    parser.add_argument('--simulation', action='store_true', help='Chế độ mô phỏng (mặc định: False)')
    parser.add_argument('--data-dir', type=str, help='Thư mục chứa dữ liệu lịch sử (mặc định: None)')
    
    args = parser.parse_args()
    
    # Khởi tạo tester
    tester = MLStrategyTester(simulation_mode=args.simulation, data_dir=args.data_dir)
    
    # Chọn chế độ kiểm thử
    if args.mode == 'compare':
        logger.info(f"So sánh các chiến lược cho {args.symbol} {args.interval}")
        result = tester.compare_strategies(
            symbol=args.symbol,
            interval=args.interval,
            lookback_days=args.lookback,
            ml_model_name=args.ml_model,
            risk_pct=args.risk,
            leverage=args.leverage
        )
    elif args.mode == 'ml-compare':
        logger.info(f"So sánh các mô hình ML cho {args.symbol} {args.interval}")
        result = tester.compare_multiple_ml_models(
            symbol=args.symbol,
            interval=args.interval,
            lookback_days=args.lookback,
            risk_pct=args.risk,
            leverage=args.leverage
        )
    elif args.mode == 'integrate':
        if not args.ml_model:
            logger.error("Phải cung cấp tên mô hình ML cho chế độ integrate")
            sys.exit(1)
            
        logger.info(f"Tích hợp ML với chiến lược rủi ro cao cho {args.symbol} {args.interval}")
        result = tester.integrate_ml_with_high_risk(
            symbol=args.symbol,
            interval=args.interval,
            best_ml_model=args.ml_model,
            lookback_days=args.lookback,
            risk_pct=args.risk,
            leverage=args.leverage
        )
    
    logger.info(f"Đã hoàn tất kiểm thử {args.mode} cho {args.symbol} {args.interval}")
    
    return result

if __name__ == "__main__":
    main()