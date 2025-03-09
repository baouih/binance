#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Huấn luyện nâng cao các mô hình ML cho giao dịch tiền điện tử
Hỗ trợ nhiều coin, nhiều khung thời gian và nhiều thuật toán
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
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split, GridSearchCV, TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from typing import Dict, List, Tuple, Optional, Any
import json
import glob
import time

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ml_training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('enhanced_ml_trainer')

# Thêm thư mục gốc vào sys.path để import các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from app.simple_feature_engineering import SimpleFeatureEngineering
    from app.market_regime_detector import MarketRegimeDetector
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")
    logger.info("Sử dụng triển khai đơn giản hóa")

class EnhancedMLTrainer:
    """
    Lớp huấn luyện ML nâng cao cho giao dịch tiền điện tử
    Hỗ trợ nhiều mô hình, nhiều coin, và nhiều khung thời gian
    """

    def __init__(self, simulation_mode=True, data_dir=None):
        """
        Khởi tạo trainer với các tham số mặc định
        
        Args:
            simulation_mode: Sử dụng chế độ mô phỏng hay không
            data_dir: Thư mục chứa dữ liệu lịch sử, nếu None sẽ lấy qua API
        """
        self.simulation_mode = simulation_mode
        self.data_dir = data_dir
        
        # Khởi tạo API và bộ xử lý dữ liệu
        self.api = BinanceAPI(simulation_mode=simulation_mode)
        self.data_processor = DataProcessor(self.api, simulation_mode=simulation_mode)
        
        # Các thư mục lưu trữ
        self.models_dir = "ml_models"
        self.features_dir = os.path.join(self.models_dir, "features")
        self.trained_dir = os.path.join(self.models_dir, "trained")
        self.charts_dir = "ml_charts"
        self.results_dir = "ml_results"
        
        # Tạo thư mục nếu chưa tồn tại
        for dir_path in [self.models_dir, self.features_dir, self.trained_dir, 
                        self.charts_dir, self.results_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Danh sách coin và khung thời gian mặc định
        self.default_coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
        self.default_timeframes = ["1h", "4h"]
        
        # Các thuật toán ML sử dụng
        self.algorithms = {
            "random_forest": RandomForestClassifier,
            "gradient_boosting": GradientBoostingClassifier,
            "svm": SVC
        }
        
        # Cấu hình thuật toán
        self.algorithm_configs = {
            "random_forest": {
                "n_estimators": 100,
                "max_depth": 10,
                "min_samples_split": 10,
                "random_state": 42,
                "class_weight": "balanced",
                "n_jobs": -1
            },
            "gradient_boosting": {
                "n_estimators": 100,
                "learning_rate": 0.1,
                "max_depth": 5,
                "random_state": 42,
                "subsample": 0.8
            },
            "svm": {
                "C": 1.0,
                "kernel": "rbf",
                "probability": True,
                "random_state": 42,
                "class_weight": "balanced"
            }
        }
        
        # Cấu hình tối ưu siêu tham số
        self.hyperparameter_grids = {
            "random_forest": {
                "n_estimators": [50, 100, 200],
                "max_depth": [5, 10, 15, None],
                "min_samples_split": [5, 10, 15]
            },
            "gradient_boosting": {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.1, 0.2],
                "max_depth": [3, 5, 7]
            },
            "svm": {
                "C": [0.1, 1.0, 10.0],
                "kernel": ["linear", "rbf"],
                "gamma": ["scale", "auto", 0.1]
            }
        }
        
        # Phân loại chế độ thị trường
        self.market_regimes = ["uptrend", "downtrend", "ranging", "volatile"]
        
        logger.info(f"Khởi tạo EnhancedMLTrainer, chế độ mô phỏng: {simulation_mode}")
    
    def download_historical_data(self, symbol: str, interval: str, 
                               lookback_days: int = 90) -> Optional[pd.DataFrame]:
        """
        Tải dữ liệu lịch sử từ Binance API hoặc từ file
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            lookback_days: Số ngày lịch sử cần lấy
            
        Returns:
            DataFrame chứa dữ liệu lịch sử
        """
        try:
            logger.info(f"Tải dữ liệu lịch sử cho {symbol}, khung thời gian {interval}, {lookback_days} ngày")
            
            # Nếu data_dir được cung cấp, đọc từ file
            if self.data_dir:
                file_path = os.path.join(self.data_dir, f"{symbol}_{interval}.csv")
                if os.path.exists(file_path):
                    logger.info(f"Đọc dữ liệu từ file {file_path}")
                    df = pd.read_csv(file_path)
                    
                    # Đảm bảo định dạng cột thời gian đúng
                    if 'datetime' in df.columns:
                        df['datetime'] = pd.to_datetime(df['datetime'])
                    elif 'open_time' in df.columns:
                        df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
                        
                    # Sắp xếp theo thời gian
                    if 'datetime' in df.columns:
                        df = df.sort_values('datetime')
                        
                    # Chỉ lấy số ngày dữ liệu cần thiết nếu có quá nhiều
                    if lookback_days > 0 and 'datetime' in df.columns:
                        end_date = df['datetime'].max()
                        start_date = end_date - pd.Timedelta(days=lookback_days)
                        df = df[df['datetime'] >= start_date]
                else:
                    logger.warning(f"Không tìm thấy file dữ liệu {file_path}")
                    return None
            else:
                # Sử dụng data_processor để lấy dữ liệu qua API
                df = self.data_processor.get_historical_data(symbol, interval, lookback_days=lookback_days)
            
            if df is None or len(df) < 30:  # Yêu cầu ít nhất 30 nến
                logger.warning(f"Không đủ dữ liệu cho {symbol} {interval}")
                return None
            
            logger.info(f"Đã tải {len(df)} nến cho {symbol} {interval}")
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu lịch sử: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def prepare_features(self, df: pd.DataFrame, add_regime: bool = True) -> pd.DataFrame:
        """
        Chuẩn bị các đặc trưng cho mô hình ML
        
        Args:
            df: DataFrame dữ liệu gốc
            add_regime: Thêm phân loại chế độ thị trường
            
        Returns:
            DataFrame với các đặc trưng đã tính toán
        """
        try:
            # Sao chép DataFrame để tránh thay đổi dữ liệu gốc
            df_features = df.copy()
            
            # Thêm các chỉ báo kỹ thuật
            # RSI
            delta = df_features['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df_features['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df_features['sma_20'] = df_features['close'].rolling(window=20).mean()
            df_features['std_20'] = df_features['close'].rolling(window=20).std()
            df_features['upper_band'] = df_features['sma_20'] + (df_features['std_20'] * 2)
            df_features['lower_band'] = df_features['sma_20'] - (df_features['std_20'] * 2)
            df_features['bb_width'] = (df_features['upper_band'] - df_features['lower_band']) / df_features['sma_20']
            df_features['bb_position'] = (df_features['close'] - df_features['lower_band']) / (df_features['upper_band'] - df_features['lower_band'])
            
            # MACD
            ema_12 = df_features['close'].ewm(span=12, adjust=False).mean()
            ema_26 = df_features['close'].ewm(span=26, adjust=False).mean()
            df_features['macd'] = ema_12 - ema_26
            df_features['macd_signal'] = df_features['macd'].ewm(span=9, adjust=False).mean()
            df_features['macd_histogram'] = df_features['macd'] - df_features['macd_signal']
            
            # Stochastic
            low_14 = df_features['low'].rolling(window=14).min()
            high_14 = df_features['high'].rolling(window=14).max()
            df_features['stoch_k'] = 100 * ((df_features['close'] - low_14) / (high_14 - low_14))
            df_features['stoch_d'] = df_features['stoch_k'].rolling(window=3).mean()
            
            # ADX (Average Directional Index)
            tr1 = df_features['high'] - df_features['low']
            tr2 = abs(df_features['high'] - df_features['close'].shift(1))
            tr3 = abs(df_features['low'] - df_features['close'].shift(1))
            tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
            df_features['atr'] = tr.rolling(window=14).mean()
            
            # Phân tích giá
            df_features['price_change'] = df_features['close'].pct_change()
            df_features['price_change_abs'] = df_features['price_change'].abs()
            df_features['price_volatility'] = df_features['price_change'].rolling(window=14).std()
            
            # Phân tích khối lượng
            df_features['volume_change'] = df_features['volume'].pct_change()
            df_features['volume_ma'] = df_features['volume'].rolling(window=20).mean()
            df_features['volume_ratio'] = df_features['volume'] / df_features['volume_ma']
            
            # Thêm lag features
            lags = [1, 2, 3, 5, 7, 14, 21]
            for lag in lags:
                df_features[f'close_lag_{lag}'] = df_features['close'].shift(lag)
                df_features[f'price_change_lag_{lag}'] = df_features['price_change'].shift(lag)
                df_features[f'volume_change_lag_{lag}'] = df_features['volume_change'].shift(lag)
            
            # Thêm biến thời gian
            df_features['hour'] = pd.to_datetime(df_features.index).hour
            df_features['day_of_week'] = pd.to_datetime(df_features.index).dayofweek
            
            # Thêm biến chế độ thị trường
            if add_regime:
                try:
                    # Sử dụng market regime detector nếu có
                    regime_detector = MarketRegimeDetector()
                    regimes = []
                    
                    for i in range(len(df_features)):
                        temp_df = df_features.iloc[:i+1].copy()
                        if i < 30:  # Cần ít nhất 30 nến cho phân loại chế độ
                            regimes.append('neutral')
                        else:
                            regime = regime_detector.detect_regime(temp_df.iloc[-30:])
                            regimes.append(regime)
                    
                    df_features['market_regime'] = regimes
                    
                    # One-hot encoding cho market regime
                    for regime in self.market_regimes:
                        df_features[f'regime_{regime}'] = (df_features['market_regime'] == regime).astype(int)
                    
                except Exception as e:
                    logger.warning(f"Không thể thêm market regime: {str(e)}")
            
            # Xử lý giá trị NaN
            df_features = df_features.replace([np.inf, -np.inf], np.nan)
            df_features = df_features.dropna()
            
            logger.info(f"Đã chuẩn bị {len(df_features.columns)} đặc trưng cho mô hình")
            
            return df_features
            
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị đặc trưng: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return df
    
    def generate_target(self, df: pd.DataFrame, target_days: int = 1,
                      threshold_pct: float = 1.0) -> pd.DataFrame:
        """
        Tạo biến mục tiêu cho mô hình ML
        
        Args:
            df: DataFrame với các đặc trưng
            target_days: Số ngày dự đoán tương lai
            threshold_pct: Ngưỡng phần trăm thay đổi để coi là tín hiệu
            
        Returns:
            DataFrame với biến mục tiêu đã thêm
        """
        try:
            df_with_target = df.copy()
            
            # Tính toán giá close tương lai
            df_with_target['future_close'] = df_with_target['close'].shift(-target_days)
            
            # Tính toán phần trăm thay đổi
            df_with_target['future_change_pct'] = (df_with_target['future_close'] / df_with_target['close'] - 1) * 100
            
            # Phân loại tín hiệu
            conditions = [
                (df_with_target['future_change_pct'] > threshold_pct),  # Tăng mạnh
                (df_with_target['future_change_pct'] < -threshold_pct), # Giảm mạnh
                (abs(df_with_target['future_change_pct']) <= threshold_pct) # Đi ngang
            ]
            choices = [1, -1, 0]  # 1 = mua, -1 = bán, 0 = giữ nguyên
            
            df_with_target['target'] = np.select(conditions, choices, default=0)
            
            # Loại bỏ các hàng không có giá trị mục tiêu
            df_with_target = df_with_target.dropna(subset=['future_change_pct', 'target'])
            
            # Thống kê phân phối mục tiêu
            target_distribution = df_with_target['target'].value_counts(normalize=True) * 100
            logger.info(f"Phân phối mục tiêu (threshold={threshold_pct}%):")
            for target, pct in target_distribution.items():
                label = "Mua" if target == 1 else "Bán" if target == -1 else "Giữ nguyên"
                logger.info(f"  {label}: {pct:.2f}%")
            
            return df_with_target
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biến mục tiêu: {str(e)}")
            return df
    
    def prepare_train_test_data(self, df: pd.DataFrame, test_size: float = 0.2,
                             time_series_split: bool = True) -> Tuple:
        """
        Chuẩn bị dữ liệu huấn luyện và kiểm thử
        
        Args:
            df: DataFrame với đặc trưng và mục tiêu
            test_size: Tỷ lệ dữ liệu dành cho tập test
            time_series_split: Sử dụng phân chia chuỗi thời gian
            
        Returns:
            Tuple (X_train, X_test, y_train, y_test, scaler)
        """
        try:
            # Loại bỏ các cột không sử dụng làm đặc trưng
            feature_cols = df.columns.tolist()
            cols_to_drop = ['future_close', 'future_change_pct', 'target', 'market_regime',
                           'open_time', 'close_time', 'datetime', 'date', 'time', 'timestamp']
            
            for col in cols_to_drop:
                if col in feature_cols:
                    feature_cols.remove(col)
            
            # Tạo dữ liệu đặc trưng và mục tiêu
            X = df[feature_cols]
            y = df['target']
            
            # Chuẩn hóa đặc trưng
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Phân chia dữ liệu
            if time_series_split:
                # Sử dụng phân chia chuỗi thời gian
                split_idx = int(len(X) * (1 - test_size))
                X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
                y_train, y_test = y[:split_idx], y[split_idx:]
            else:
                # Phân chia ngẫu nhiên
                X_train, X_test, y_train, y_test = train_test_split(
                    X_scaled, y, test_size=test_size, random_state=42, stratify=y
                )
            
            logger.info(f"Đã phân chia dữ liệu: {X_train.shape[0]} mẫu huấn luyện, {X_test.shape[0]} mẫu kiểm thử")
            logger.info(f"Phân phối mục tiêu (train): 1={sum(y_train==1)}, -1={sum(y_train==-1)}, 0={sum(y_train==0)}")
            logger.info(f"Phân phối mục tiêu (test): 1={sum(y_test==1)}, -1={sum(y_test==-1)}, 0={sum(y_test==0)}")
            
            return X_train, X_test, y_train, y_test, scaler, feature_cols
            
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị dữ liệu huấn luyện/kiểm thử: {str(e)}")
            return None, None, None, None, None, None
    
    def train_model(self, X_train, y_train, algorithm: str = "random_forest",
                 optimize_hyperparams: bool = False) -> Any:
        """
        Huấn luyện mô hình ML
        
        Args:
            X_train: Dữ liệu đặc trưng huấn luyện
            y_train: Dữ liệu mục tiêu huấn luyện
            algorithm: Thuật toán sử dụng
            optimize_hyperparams: Tối ưu siêu tham số
            
        Returns:
            Mô hình đã huấn luyện
        """
        try:
            start_time = time.time()
            logger.info(f"Bắt đầu huấn luyện mô hình {algorithm}")
            
            if algorithm not in self.algorithms:
                logger.error(f"Không hỗ trợ thuật toán {algorithm}")
                return None
            
            # Tạo mô hình với cấu hình mặc định
            model_class = self.algorithms[algorithm]
            model_config = self.algorithm_configs[algorithm]
            
            if optimize_hyperparams:
                # Tối ưu siêu tham số bằng Grid Search
                logger.info(f"Thực hiện tối ưu siêu tham số cho {algorithm}")
                
                param_grid = self.hyperparameter_grids[algorithm]
                
                if algorithm == "svm" and X_train.shape[0] > 10000:
                    # Giảm kích thước dữ liệu cho SVM nếu quá lớn
                    logger.info("Giảm kích thước dữ liệu cho SVM")
                    sample_idx = np.random.choice(X_train.shape[0], 10000, replace=False)
                    X_sample = X_train[sample_idx]
                    y_sample = y_train.iloc[sample_idx] if hasattr(y_train, 'iloc') else y_train[sample_idx]
                else:
                    X_sample = X_train
                    y_sample = y_train
                
                # Phân chia chuỗi thời gian cho CV
                tscv = TimeSeriesSplit(n_splits=5)
                
                # Grid Search
                grid_search = GridSearchCV(
                    model_class(**model_config),
                    param_grid,
                    cv=tscv,
                    scoring='f1_weighted',
                    n_jobs=-1 if algorithm != "svm" else 1,
                    verbose=1
                )
                
                grid_search.fit(X_sample, y_sample)
                
                # Lấy tham số tốt nhất
                best_params = grid_search.best_params_
                logger.info(f"Tham số tốt nhất cho {algorithm}: {best_params}")
                
                # Cập nhật cấu hình
                model_config.update(best_params)
                
                # Huấn luyện lại với toàn bộ dữ liệu
                model = model_class(**model_config)
            else:
                # Huấn luyện với cấu hình mặc định
                model = model_class(**model_config)
            
            # Huấn luyện mô hình
            model.fit(X_train, y_train)
            
            training_time = time.time() - start_time
            logger.info(f"Đã huấn luyện xong mô hình {algorithm} sau {training_time:.2f} giây")
            
            return model
            
        except Exception as e:
            logger.error(f"Lỗi khi huấn luyện mô hình: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def evaluate_model(self, model, X_test, y_test, X_train=None, y_train=None) -> Dict:
        """
        Đánh giá hiệu suất mô hình
        
        Args:
            model: Mô hình đã huấn luyện
            X_test: Dữ liệu đặc trưng kiểm thử
            y_test: Dữ liệu mục tiêu kiểm thử
            X_train: Dữ liệu đặc trưng huấn luyện (tùy chọn)
            y_train: Dữ liệu mục tiêu huấn luyện (tùy chọn)
            
        Returns:
            Dict chứa các số liệu hiệu suất
        """
        try:
            # Dự đoán
            y_pred = model.predict(X_test)
            
            # Tính các số liệu
            acc = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            
            # Tạo ma trận nhầm lẫn
            cm = confusion_matrix(y_test, y_pred)
            
            # Tính hiệu suất trên tập huấn luyện nếu có
            if X_train is not None and y_train is not None:
                y_train_pred = model.predict(X_train)
                train_acc = accuracy_score(y_train, y_train_pred)
                train_f1 = f1_score(y_train, y_train_pred, average='weighted', zero_division=0)
            else:
                train_acc = None
                train_f1 = None
            
            # Tính tỷ lệ dự đoán từng lớp
            pred_distribution = np.bincount(y_pred.astype(int) + 1, minlength=3) / len(y_pred)
            pred_distribution = {
                "buy": float(pred_distribution[2]),    # +1 -> index 2
                "hold": float(pred_distribution[1]),   # 0 -> index 1
                "sell": float(pred_distribution[0])    # -1 -> index 0
            }
            
            # Kết quả
            results = {
                "accuracy": float(acc),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "confusion_matrix": cm.tolist(),
                "prediction_distribution": pred_distribution
            }
            
            if train_acc is not None:
                results["train_accuracy"] = float(train_acc)
                results["train_f1"] = float(train_f1)
                results["overfitting"] = float(train_acc - acc)
            
            logger.info(f"Kết quả đánh giá: Accuracy={acc:.4f}, F1={f1:.4f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá mô hình: {str(e)}")
            return {}
    
    def plot_evaluation_results(self, y_test, y_pred, model_name, results):
        """
        Vẽ các biểu đồ đánh giá
        
        Args:
            y_test: Dữ liệu mục tiêu thực tế
            y_pred: Dữ liệu dự đoán
            model_name: Tên mô hình
            results: Kết quả đánh giá
        """
        try:
            # Tạo biểu đồ ma trận nhầm lẫn
            plt.figure(figsize=(10, 8))
            cm = results["confusion_matrix"]
            labels = ["Bán", "Giữ", "Mua"]  # -1, 0, 1
            
            cm_display = np.zeros((3, 3))
            for i in range(len(cm)):
                for j in range(len(cm[i])):
                    actual_idx = i - 1 + 1  # Convert -1,0,1 to 0,1,2
                    pred_idx = j - 1 + 1
                    if 0 <= actual_idx < 3 and 0 <= pred_idx < 3:
                        cm_display[actual_idx][pred_idx] = cm[i][j]
            
            plt.imshow(cm_display, interpolation='nearest', cmap=plt.cm.Blues)
            plt.title(f'Ma trận nhầm lẫn - {model_name}')
            plt.colorbar()
            tick_marks = np.arange(len(labels))
            plt.xticks(tick_marks, labels, rotation=45)
            plt.yticks(tick_marks, labels)
            
            # Thêm nhãn giá trị
            fmt = 'd'
            thresh = cm_display.max() / 2.
            for i in range(cm_display.shape[0]):
                for j in range(cm_display.shape[1]):
                    plt.text(j, i, format(int(cm_display[i, j]), fmt),
                            ha="center", va="center",
                            color="white" if cm_display[i, j] > thresh else "black")
            
            plt.ylabel('Thực tế')
            plt.xlabel('Dự đoán')
            plt.tight_layout()
            
            # Lưu biểu đồ
            cm_filename = os.path.join(self.charts_dir, f"{model_name}_confusion_matrix.png")
            plt.savefig(cm_filename, dpi=300)
            
            # Tạo biểu đồ dự đoán
            plt.figure(figsize=(14, 7))
            
            # Chuyển đổi -1,0,1 thành các màu
            colors = np.array(['red', 'gray', 'green'])
            y_test_colors = np.array([colors[y+1] for y in y_test])
            y_pred_colors = np.array([colors[y+1] for y in y_pred])
            
            plt.subplot(2, 1, 1)
            plt.scatter(range(len(y_test)), y_test, marker='o', s=30, c=y_test_colors, alpha=0.7)
            plt.title(f'Giá trị thực tế vs Dự đoán - {model_name}')
            plt.ylabel('Thực tế')
            plt.yticks([-1, 0, 1], ['Bán', 'Giữ', 'Mua'])
            
            plt.subplot(2, 1, 2)
            plt.scatter(range(len(y_pred)), y_pred, marker='x', s=30, c=y_pred_colors, alpha=0.7)
            plt.ylabel('Dự đoán')
            plt.yticks([-1, 0, 1], ['Bán', 'Giữ', 'Mua'])
            plt.xlabel('Mẫu')
            
            plt.tight_layout()
            
            # Lưu biểu đồ
            pred_filename = os.path.join(self.charts_dir, f"{model_name}_predictions.png")
            plt.savefig(pred_filename, dpi=300)
            
            # Đóng tất cả
            plt.close('all')
            
            logger.info(f"Đã lưu biểu đồ đánh giá: {cm_filename}, {pred_filename}")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ đánh giá: {str(e)}")
    
    def save_model(self, model, scaler, feature_cols, model_name, results):
        """
        Lưu mô hình và metadata
        
        Args:
            model: Mô hình đã huấn luyện
            scaler: Scaler đã fit
            feature_cols: Danh sách cột đặc trưng
            model_name: Tên mô hình
            results: Kết quả đánh giá
            
        Returns:
            bool: Thành công hay không
        """
        try:
            # Lưu mô hình
            model_path = os.path.join(self.models_dir, f"{model_name}_model.joblib")
            joblib.dump(model, model_path)
            
            # Lưu scaler
            scaler_path = os.path.join(self.models_dir, f"{model_name}_scaler.joblib")
            joblib.dump(scaler, scaler_path)
            
            # Lưu danh sách đặc trưng
            features_path = os.path.join(self.models_dir, f"{model_name}_features.json")
            with open(features_path, 'w') as f:
                json.dump(feature_cols, f, indent=2)
            
            # Lưu kết quả đánh giá
            results_path = os.path.join(self.results_dir, f"{model_name}_performance.json")
            
            # Thêm metadata
            results["model_name"] = model_name
            results["saved_time"] = datetime.now().isoformat()
            results["feature_count"] = len(feature_cols)
            
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Đã lưu mô hình và metadata: {model_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu mô hình: {str(e)}")
            return False
    
    def train_for_symbol(self, symbol: str, interval: str, 
                      lookback_days: int = 90, 
                      target_days: int = 1,
                      threshold_pct: float = 1.0,
                      algorithms: List[str] = None,
                      optimize_hyperparams: bool = False) -> Dict:
        """
        Huấn luyện mô hình cho một cặp tiền cụ thể
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            lookback_days: Số ngày lịch sử cần lấy
            target_days: Số ngày dự đoán tương lai
            threshold_pct: Ngưỡng phần trăm thay đổi
            algorithms: Danh sách thuật toán cần huấn luyện
            optimize_hyperparams: Tối ưu siêu tham số
            
        Returns:
            Dict chứa kết quả huấn luyện
        """
        try:
            period_label = f"{lookback_days//30}m" if lookback_days >= 30 else f"{lookback_days}d"
            logger.info(f"=== Huấn luyện mô hình cho {symbol} {interval} (dữ liệu {period_label}, mục tiêu {target_days}d) ===")
            
            # Thiết lập danh sách thuật toán
            if algorithms is None:
                algorithms = list(self.algorithms.keys())
            
            # Tải dữ liệu lịch sử
            df = self.download_historical_data(symbol, interval, lookback_days)
            
            if df is None or len(df) < 50:
                logger.error(f"Không đủ dữ liệu cho {symbol} {interval}")
                return {"success": False, "message": "Không đủ dữ liệu"}
            
            # Chuẩn bị đặc trưng
            df_features = self.prepare_features(df)
            
            # Tạo biến mục tiêu
            df_with_target = self.generate_target(df_features, target_days, threshold_pct)
            
            # Kiểm tra số lượng dữ liệu sau khi xử lý
            if len(df_with_target) < 50:
                logger.error(f"Không đủ dữ liệu sau khi tạo đặc trưng và mục tiêu: {len(df_with_target)} mẫu")
                return {"success": False, "message": "Không đủ dữ liệu sau khi xử lý"}
            
            # Chuẩn bị dữ liệu huấn luyện và kiểm thử
            X_train, X_test, y_train, y_test, scaler, feature_cols = self.prepare_train_test_data(
                df_with_target, test_size=0.2, time_series_split=True
            )
            
            if X_train is None:
                logger.error("Lỗi khi chuẩn bị dữ liệu huấn luyện/kiểm thử")
                return {"success": False, "message": "Lỗi khi chuẩn bị dữ liệu"}
            
            results = {}
            best_model = None
            best_algorithm = None
            best_f1 = -1
            
            # Huấn luyện từng thuật toán
            for algo in algorithms:
                try:
                    logger.info(f"Huấn luyện {algo} cho {symbol} {interval}")
                    
                    # Tên mô hình
                    model_name = f"{symbol}_{interval}_{period_label}_target{target_days}d_{algo}"
                    
                    # Huấn luyện mô hình
                    model = self.train_model(
                        X_train, y_train, algorithm=algo, 
                        optimize_hyperparams=optimize_hyperparams
                    )
                    
                    if model is None:
                        logger.warning(f"Không thể huấn luyện mô hình {algo}")
                        continue
                    
                    # Dự đoán
                    y_pred = model.predict(X_test)
                    
                    # Đánh giá mô hình
                    eval_results = self.evaluate_model(
                        model, X_test, y_test, X_train, y_train
                    )
                    
                    # Vẽ biểu đồ đánh giá
                    self.plot_evaluation_results(y_test, y_pred, model_name, eval_results)
                    
                    # Lưu mô hình
                    save_result = self.save_model(
                        model, scaler, feature_cols, model_name, eval_results
                    )
                    
                    # Lưu kết quả
                    results[algo] = {
                        "model_name": model_name,
                        "accuracy": eval_results.get("accuracy", 0),
                        "f1": eval_results.get("f1", 0),
                        "save_status": save_result
                    }
                    
                    # Kiểm tra nếu là mô hình tốt nhất
                    current_f1 = eval_results.get("f1", 0)
                    if current_f1 > best_f1:
                        best_f1 = current_f1
                        best_algorithm = algo
                        best_model = {
                            "model_name": model_name,
                            "algorithm": algo,
                            "accuracy": eval_results.get("accuracy", 0),
                            "precision": eval_results.get("precision", 0),
                            "recall": eval_results.get("recall", 0),
                            "f1": current_f1
                        }
                    
                except Exception as e:
                    logger.error(f"Lỗi khi huấn luyện thuật toán {algo}: {str(e)}")
                    results[algo] = {"error": str(e)}
            
            # Kết quả tổng hợp
            summary = {
                "success": True,
                "symbol": symbol,
                "interval": interval,
                "period": period_label,
                "target_days": target_days,
                "threshold_pct": threshold_pct,
                "data_points": len(df),
                "training_samples": X_train.shape[0],
                "testing_samples": X_test.shape[0],
                "feature_count": len(feature_cols),
                "algorithms": results,
                "best_model": best_model
            }
            
            # Lưu kết quả tổng hợp
            summary_path = os.path.join(
                self.results_dir, 
                f"{symbol}_{interval}_{period_label}_target{target_days}d_summary.json"
            )
            
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"=== Đã hoàn thành huấn luyện cho {symbol} {interval} ===")
            logger.info(f"Thuật toán tốt nhất: {best_algorithm} với F1-score: {best_f1:.4f}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Lỗi khi huấn luyện mô hình cho {symbol} {interval}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "message": str(e)}
    
    def train_multiple_models(self, symbols: List[str] = None, 
                           intervals: List[str] = None,
                           lookback_periods: List[int] = None,
                           target_days_list: List[int] = None,
                           threshold_pct: float = 1.0,
                           algorithms: List[str] = None,
                           optimize_hyperparams: bool = False) -> Dict:
        """
        Huấn luyện nhiều mô hình cho nhiều cặp tiền và khung thời gian
        
        Args:
            symbols: Danh sách cặp tiền
            intervals: Danh sách khung thời gian
            lookback_periods: Danh sách khoảng thời gian lịch sử (ngày)
            target_days_list: Danh sách khoảng thời gian mục tiêu (ngày)
            threshold_pct: Ngưỡng phần trăm thay đổi
            algorithms: Danh sách thuật toán cần huấn luyện
            optimize_hyperparams: Tối ưu siêu tham số
            
        Returns:
            Dict chứa kết quả huấn luyện
        """
        # Thiết lập các giá trị mặc định
        if symbols is None:
            symbols = self.default_coins
        
        if intervals is None:
            intervals = self.default_timeframes
        
        if lookback_periods is None:
            lookback_periods = [30, 90]  # 1 tháng và 3 tháng
        
        if target_days_list is None:
            target_days_list = [1, 3]  # 1 ngày và 3 ngày
        
        if algorithms is None:
            algorithms = list(self.algorithms.keys())
        
        # Tạo danh sách tổ hợp cần huấn luyện
        training_tasks = []
        for symbol in symbols:
            for interval in intervals:
                for lookback_days in lookback_periods:
                    for target_days in target_days_list:
                        training_tasks.append({
                            "symbol": symbol,
                            "interval": interval,
                            "lookback_days": lookback_days,
                            "target_days": target_days
                        })
        
        logger.info(f"=== Bắt đầu huấn luyện {len(training_tasks)} mô hình ===")
        
        # Kết quả tổng hợp
        all_results = {
            "tasks_total": len(training_tasks),
            "tasks_completed": 0,
            "tasks_failed": 0,
            "started_at": datetime.now().isoformat(),
            "results": {}
        }
        
        # Huấn luyện từng mô hình
        for i, task in enumerate(training_tasks):
            try:
                symbol = task["symbol"]
                interval = task["interval"]
                lookback_days = task["lookback_days"]
                target_days = task["target_days"]
                
                logger.info(f"Nhiệm vụ {i+1}/{len(training_tasks)}: {symbol} {interval} ({lookback_days} ngày, mục tiêu {target_days}d)")
                
                # Tạo khóa cho kết quả
                period_label = f"{lookback_days//30}m" if lookback_days >= 30 else f"{lookback_days}d"
                result_key = f"{symbol}_{interval}_{period_label}_target{target_days}d"
                
                # Huấn luyện mô hình
                result = self.train_for_symbol(
                    symbol, interval, lookback_days, target_days,
                    threshold_pct, algorithms, optimize_hyperparams
                )
                
                # Lưu kết quả
                all_results["results"][result_key] = result
                
                # Cập nhật số liệu
                if result.get("success", False):
                    all_results["tasks_completed"] += 1
                else:
                    all_results["tasks_failed"] += 1
                
            except Exception as e:
                logger.error(f"Lỗi khi thực hiện nhiệm vụ {i+1}: {str(e)}")
                all_results["tasks_failed"] += 1
        
        # Cập nhật thời gian kết thúc
        all_results["completed_at"] = datetime.now().isoformat()
        all_results["total_time"] = (datetime.now() - datetime.fromisoformat(all_results["started_at"])).total_seconds()
        
        # Lưu kết quả tổng hợp
        all_results_path = os.path.join(self.results_dir, "all_models_training_results.json")
        with open(all_results_path, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        logger.info(f"=== Đã hoàn thành huấn luyện {all_results['tasks_completed']}/{len(training_tasks)} mô hình ===")
        logger.info(f"Thời gian tổng cộng: {all_results['total_time']:.2f} giây")
        logger.info(f"Kết quả đã được lưu tại: {all_results_path}")
        
        return all_results
    
    def generate_training_summary(self):
        """
        Tạo báo cáo tổng hợp về việc huấn luyện mô hình
        """
        try:
            # Tìm tất cả các tệp kết quả
            performance_files = glob.glob(os.path.join(self.results_dir, "*_performance.json"))
            
            if not performance_files:
                logger.warning("Không tìm thấy kết quả đánh giá mô hình")
                return False
            
            # Thu thập thông tin
            models_info = []
            
            for perf_file in performance_files:
                try:
                    with open(perf_file, 'r') as f:
                        perf_data = json.load(f)
                    
                    model_name = os.path.basename(perf_file).replace("_performance.json", "")
                    
                    # Phân tích tên mô hình
                    name_parts = model_name.split("_")
                    symbol = name_parts[0]
                    interval = name_parts[1]
                    
                    # Tìm period và target
                    period = None
                    target_days = None
                    algorithm = None
                    
                    for part in name_parts:
                        if part.endswith("m") or part.endswith("d"):
                            if not part.startswith("target"):
                                period = part
                        if part.startswith("target") and part.endswith("d"):
                            target_days = int(part.replace("target", "").replace("d", ""))
                        if part in self.algorithms:
                            algorithm = part
                    
                    models_info.append({
                        "model_name": model_name,
                        "symbol": symbol,
                        "interval": interval,
                        "period": period,
                        "target_days": target_days,
                        "algorithm": algorithm,
                        "accuracy": perf_data.get("accuracy", 0),
                        "precision": perf_data.get("precision", 0),
                        "recall": perf_data.get("recall", 0),
                        "f1": perf_data.get("f1", 0),
                        "confusion_matrix": perf_data.get("confusion_matrix", [])
                    })
                    
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý tệp {perf_file}: {str(e)}")
            
            # Sắp xếp theo F1 score
            models_info.sort(key=lambda x: x.get("f1", 0), reverse=True)
            
            # Tính toán thống kê
            symbols = set(model["symbol"] for model in models_info)
            intervals = set(model["interval"] for model in models_info)
            periods = set(model["period"] for model in models_info if model["period"])
            target_days_set = set(model["target_days"] for model in models_info if model["target_days"])
            
            # Tìm mô hình tốt nhất cho mỗi số liệu
            best_accuracy = max(models_info, key=lambda x: x.get("accuracy", 0))
            best_precision = max(models_info, key=lambda x: x.get("precision", 0))
            best_recall = max(models_info, key=lambda x: x.get("recall", 0))
            best_f1 = max(models_info, key=lambda x: x.get("f1", 0))
            
            # Tính hiệu suất trung bình cho từng symbol
            performance_by_symbol = {}
            for symbol in symbols:
                symbol_models = [m for m in models_info if m["symbol"] == symbol]
                if symbol_models:
                    performance_by_symbol[symbol] = {
                        "accuracy": sum(m.get("accuracy", 0) for m in symbol_models) / len(symbol_models),
                        "precision": sum(m.get("precision", 0) for m in symbol_models) / len(symbol_models),
                        "recall": sum(m.get("recall", 0) for m in symbol_models) / len(symbol_models),
                        "f1": sum(m.get("f1", 0) for m in symbol_models) / len(symbol_models),
                        "n_models": len(symbol_models)
                    }
            
            # Tính hiệu suất trung bình cho từng period
            performance_by_period = {}
            for period in periods:
                period_models = [m for m in models_info if m["period"] == period]
                if period_models:
                    performance_by_period[period] = {
                        "accuracy": sum(m.get("accuracy", 0) for m in period_models) / len(period_models),
                        "precision": sum(m.get("precision", 0) for m in period_models) / len(period_models),
                        "recall": sum(m.get("recall", 0) for m in period_models) / len(period_models),
                        "f1": sum(m.get("f1", 0) for m in period_models) / len(period_models),
                        "n_models": len(period_models)
                    }
            
            # Tính hiệu suất trung bình cho từng target
            performance_by_target = {}
            for target in target_days_set:
                target_models = [m for m in models_info if m["target_days"] == target]
                if target_models:
                    performance_by_target[str(target)] = {
                        "accuracy": sum(m.get("accuracy", 0) for m in target_models) / len(target_models),
                        "precision": sum(m.get("precision", 0) for m in target_models) / len(target_models),
                        "recall": sum(m.get("recall", 0) for m in target_models) / len(target_models),
                        "f1": sum(m.get("f1", 0) for m in target_models) / len(target_models),
                        "n_models": len(target_models)
                    }
            
            # Tạo báo cáo tổng hợp
            summary = {
                "timestamp": datetime.now().isoformat(),
                "total_models": len(models_info),
                "coins": list(symbols),
                "timeframes": list(intervals),
                "periods": list(periods),
                "target_days": list(map(int, target_days_set)),
                "performance_by_coin": performance_by_symbol,
                "performance_by_period": performance_by_period,
                "performance_by_target": performance_by_target,
                "best_models": {
                    "accuracy": {
                        "model": best_accuracy["model_name"],
                        "value": best_accuracy.get("accuracy", 0)
                    },
                    "precision": {
                        "model": best_precision["model_name"],
                        "value": best_precision.get("precision", 0)
                    },
                    "recall": {
                        "model": best_recall["model_name"],
                        "value": best_recall.get("recall", 0)
                    },
                    "f1": {
                        "model": best_f1["model_name"],
                        "value": best_f1.get("f1", 0)
                    }
                }
            }
            
            # Lưu báo cáo
            summary_path = os.path.join(self.results_dir, "ml_summary_report.json")
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Đã tạo báo cáo tổng hợp với {len(models_info)} mô hình")
            logger.info(f"Mô hình F1 tốt nhất: {best_f1['model_name']} ({best_f1.get('f1', 0):.4f})")
            
            # Tạo biểu đồ hiệu suất
            self._plot_summary_charts(summary)
            
            # Tạo báo cáo HTML
            self._generate_html_report(summary, models_info)
            
            return summary
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _plot_summary_charts(self, summary):
        """
        Vẽ các biểu đồ tổng hợp
        
        Args:
            summary: Dict chứa thông tin tổng hợp
        """
        try:
            # Biểu đồ hiệu suất theo coin
            plt.figure(figsize=(12, 6))
            
            coins = list(summary["performance_by_coin"].keys())
            if not coins:
                logger.warning("Không có thông tin hiệu suất theo coin")
                return
                
            metrics = ['accuracy', 'precision', 'recall', 'f1']
            
            x = np.arange(len(coins))
            width = 0.2
            
            for i, metric in enumerate(metrics):
                values = [summary["performance_by_coin"][coin][metric] for coin in coins]
                plt.bar(x + i*width, values, width, label=metric.capitalize())
            
            plt.xlabel('Coins')
            plt.ylabel('Score')
            plt.title('Hiệu suất theo Coin')
            plt.xticks(x + width * 1.5, coins)
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Lưu biểu đồ
            plt.savefig(os.path.join(self.charts_dir, 'performance_by_coin.png'), dpi=300, bbox_inches='tight')
            plt.close()
            
            # Biểu đồ hiệu suất theo khoảng thời gian huấn luyện
            if summary["performance_by_period"]:
                plt.figure(figsize=(12, 6))
                
                periods = list(summary["performance_by_period"].keys())
                
                x = np.arange(len(periods))
                width = 0.2
                
                for i, metric in enumerate(metrics):
                    values = [summary["performance_by_period"][period][metric] for period in periods]
                    plt.bar(x + i*width, values, width, label=metric.capitalize())
                
                plt.xlabel('Khoảng thời gian huấn luyện')
                plt.ylabel('Score')
                plt.title('Hiệu suất theo khoảng thời gian dữ liệu')
                plt.xticks(x + width * 1.5, periods)
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                plt.savefig(os.path.join(self.charts_dir, 'performance_by_period.png'), dpi=300, bbox_inches='tight')
                plt.close()
            
            # Biểu đồ hiệu suất theo mục tiêu dự đoán
            if summary["performance_by_target"]:
                plt.figure(figsize=(12, 6))
                
                targets = list(summary["performance_by_target"].keys())
                
                x = np.arange(len(targets))
                width = 0.2
                
                for i, metric in enumerate(metrics):
                    values = [summary["performance_by_target"][target][metric] for target in targets]
                    plt.bar(x + i*width, values, width, label=metric.capitalize())
                
                plt.xlabel('Mục tiêu dự đoán (ngày)')
                plt.ylabel('Score')
                plt.title('Hiệu suất theo mục tiêu dự đoán')
                plt.xticks(x + width * 1.5, targets)
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                plt.savefig(os.path.join(self.charts_dir, 'performance_by_target.png'), dpi=300, bbox_inches='tight')
                plt.close()
            
            # Biểu đồ mô hình tốt nhất
            plt.figure(figsize=(12, 6))
            
            best_metrics = list(summary["best_models"].keys())
            best_values = [summary["best_models"][metric]["value"] for metric in best_metrics]
            
            plt.bar(best_metrics, best_values, color='skyblue')
            plt.ylim(0, 1)
            plt.xlabel('Metric')
            plt.ylabel('Score')
            plt.title('Mô hình tốt nhất theo metric')
            
            # Thêm nhãn
            for i, v in enumerate(best_values):
                model_name = summary["best_models"][best_metrics[i]]["model"]
                plt.text(i, v + 0.02, f"{v:.3f}\n{model_name}", ha='center', fontsize=9)
            
            plt.savefig(os.path.join(self.charts_dir, 'best_models.png'), dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info("Đã tạo các biểu đồ tổng hợp hiệu suất")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ tổng hợp: {str(e)}")
    
    def _generate_html_report(self, summary, models_info):
        """
        Tạo báo cáo HTML
        
        Args:
            summary: Dict chứa thông tin tổng hợp
            models_info: Danh sách thông tin chi tiết về các mô hình
        """
        try:
            # Tạo nội dung HTML
            html = '''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Báo Cáo Huấn Luyện ML</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 0;
                        padding: 20px;
                        color: #333;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                    }
                    h1, h2, h3 {
                        color: #2c3e50;
                    }
                    .summary {
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 20px;
                    }
                    th, td {
                        padding: 12px 15px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }
                    th {
                        background-color: #4CAF50;
                        color: white;
                    }
                    tr:hover {
                        background-color: #f5f5f5;
                    }
                    .tab-content {
                        display: none;
                        padding: 20px;
                        border: 1px solid #ddd;
                        border-radius: 0 0 5px 5px;
                    }
                    .tabs {
                        display: flex;
                        border-bottom: 1px solid #ddd;
                    }
                    .tab {
                        padding: 10px 15px;
                        cursor: pointer;
                        background-color: #f1f1f1;
                        border: 1px solid #ddd;
                        border-bottom: none;
                        border-radius: 5px 5px 0 0;
                        margin-right: 5px;
                    }
                    .tab:hover {
                        background-color: #ddd;
                    }
                    .active-tab {
                        background-color: white;
                        border-bottom: 1px solid white;
                    }
                    .chart-container {
                        margin: 20px 0;
                    }
                    .metric {
                        font-weight: bold;
                        color: #2980b9;
                    }
                    .highlight {
                        background-color: #fff3cd;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Báo Cáo Huấn Luyện Mô Hình ML</h1>
                    <div class="summary">
                        <h2>Tóm Tắt</h2>
                        <p>Thời gian: {timestamp}</p>
                        <p>Tổng số mô hình: {total_models}</p>
                        <p>Coins: {coins}</p>
                        <p>Khung thời gian: {timeframes}</p>
                        <p>Khoảng thời gian huấn luyện: {periods}</p>
                        <p>Mục tiêu dự đoán (ngày): {target_days}</p>
                    </div>
                    
                    <h2>Hiệu Suất Tốt Nhất</h2>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Mô hình</th>
                            <th>Giá trị</th>
                        </tr>
            '''.format(
                timestamp=summary['timestamp'],
                total_models=summary['total_models'],
                coins=', '.join(summary['coins']),
                timeframes=', '.join(summary['timeframes']),
                periods=', '.join(summary['periods']),
                target_days=', '.join(map(str, summary['target_days']))
            )
            
            # Thêm thông tin về mô hình tốt nhất
            for metric, data in summary["best_models"].items():
                html += '''
                        <tr>
                            <td>{metric}</td>
                            <td>{model}</td>
                            <td>{value:.4f}</td>
                        </tr>
                '''.format(metric=metric.upper(), model=data["model"], value=data["value"])
            
            html += '''
                    </table>
                    
                    <h2>Hiệu Suất Theo Phân Loại</h2>
                    
                    <div class="tabs">
                        <div class="tab active-tab" onclick="openTab('coinTab')">Theo Coin</div>
                        <div class="tab" onclick="openTab('periodTab')">Theo Khoảng Thời Gian</div>
                        <div class="tab" onclick="openTab('targetTab')">Theo Mục Tiêu</div>
                        <div class="tab" onclick="openTab('allModels')">Tất cả mô hình</div>
                    </div>
                    
                    <div id="coinTab" class="tab-content" style="display: block;">
                        <h2>Theo Coin</h2>
                        <div class="chart-container">
                            <img src="../ml_charts/performance_by_coin.png" alt="Hiệu suất theo coin" style="max-width: 100%;">
                        </div>
                        <table>
                            <tr>
                                <th>Coin</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Số mô hình</th>
                            </tr>
            '''
            
            # Thêm thông tin hiệu suất theo coin
            for coin, data in summary["performance_by_coin"].items():
                html += '''
                            <tr>
                                <td>{coin}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>{n_models}</td>
                            </tr>
                '''.format(
                    coin=coin,
                    accuracy=data["accuracy"],
                    precision=data["precision"],
                    recall=data["recall"],
                    f1=data["f1"],
                    n_models=data["n_models"]
                )
            
            html += '''
                        </table>
                    </div>
                    
                    <div id="periodTab" class="tab-content">
                        <h2>Theo Khoảng Thời Gian</h2>
                        <div class="chart-container">
                            <img src="../ml_charts/performance_by_period.png" alt="Hiệu suất theo khoảng thời gian" style="max-width: 100%;">
                        </div>
                        <table>
                            <tr>
                                <th>Khoảng thời gian</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Số mô hình</th>
                            </tr>
            '''
            
            # Thêm thông tin hiệu suất theo khoảng thời gian
            for period, data in summary["performance_by_period"].items():
                html += '''
                            <tr>
                                <td>{period}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>{n_models}</td>
                            </tr>
                '''.format(
                    period=period,
                    accuracy=data["accuracy"],
                    precision=data["precision"],
                    recall=data["recall"],
                    f1=data["f1"],
                    n_models=data["n_models"]
                )
            
            html += '''
                        </table>
                    </div>
                    
                    <div id="targetTab" class="tab-content">
                        <h2>Theo Mục Tiêu Dự Đoán</h2>
                        <div class="chart-container">
                            <img src="../ml_charts/performance_by_target.png" alt="Hiệu suất theo mục tiêu" style="max-width: 100%;">
                        </div>
                        <table>
                            <tr>
                                <th>Mục tiêu (ngày)</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Số mô hình</th>
                            </tr>
            '''
            
            # Thêm thông tin hiệu suất theo mục tiêu
            for target, data in summary["performance_by_target"].items():
                html += '''
                            <tr>
                                <td>{target}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>{n_models}</td>
                            </tr>
                '''.format(
                    target=target,
                    accuracy=data["accuracy"],
                    precision=data["precision"],
                    recall=data["recall"],
                    f1=data["f1"],
                    n_models=data["n_models"]
                )
            
            html += '''
                        </table>
                    </div>
                    
                    <div id="allModels" class="tab-content">
                        <h2>Tất cả mô hình</h2>
                        <table>
                            <tr>
                                <th>Mô hình</th>
                                <th>Coin</th>
                                <th>Timeframe</th>
                                <th>Khoảng thời gian</th>
                                <th>Mục tiêu (ngày)</th>
                                <th>Thuật toán</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Biểu đồ</th>
                            </tr>
            '''
            
            # Thêm thông tin về tất cả các mô hình
            for model in models_info:
                html += '''
                            <tr>
                                <td>{model_name}</td>
                                <td>{symbol}</td>
                                <td>{interval}</td>
                                <td>{period}</td>
                                <td>{target_days}</td>
                                <td>{algorithm}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>
                                    <a href="../ml_charts/{model_name}_confusion_matrix.png" target="_blank">Ma trận nhầm lẫn</a><br>
                                    <a href="../ml_charts/{model_name}_predictions.png" target="_blank">Dự đoán</a>
                                </td>
                            </tr>
                '''.format(
                    model_name=model["model_name"],
                    symbol=model["symbol"],
                    interval=model["interval"],
                    period=model["period"] if model["period"] else "-",
                    target_days=model["target_days"] if model["target_days"] else "-",
                    algorithm=model["algorithm"] if model["algorithm"] else "-",
                    accuracy=model["accuracy"],
                    precision=model["precision"],
                    recall=model["recall"],
                    f1=model["f1"]
                )
            
            html += '''
                        </table>
                    </div>
                    
                    <script>
                        function openTab(tabName) {
                            // Ẩn tất cả các tab content
                            var tabContents = document.getElementsByClassName("tab-content");
                            for (var i = 0; i < tabContents.length; i++) {
                                tabContents[i].style.display = "none";
                            }
                            
                            // Loại bỏ class active-tab khỏi tất cả các tab
                            var tabs = document.getElementsByClassName("tab");
                            for (var i = 0; i < tabs.length; i++) {
                                tabs[i].className = tabs[i].className.replace(" active-tab", "");
                            }
                            
                            // Hiển thị tab hiện tại và thêm class active-tab
                            document.getElementById(tabName).style.display = "block";
                            event.currentTarget.className += " active-tab";
                        }
                    </script>
                </div>
            </body>
            </html>
            '''
            
            # Lưu báo cáo HTML
            html_path = os.path.join(self.results_dir, "ml_summary_report.html")
            with open(html_path, 'w') as f:
                f.write(html)
                
            logger.info(f"Đã tạo báo cáo HTML: {html_path}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo HTML: {str(e)}")

def main():
    """Hàm chính"""
    # Thiết lập parser dòng lệnh
    parser = argparse.ArgumentParser(description='Huấn luyện nâng cao mô hình ML cho giao dịch tiền điện tử')
    parser.add_argument('--symbols', type=str, nargs='+', help='Danh sách cặp tiền (mặc định: BTC, ETH)')
    parser.add_argument('--intervals', type=str, nargs='+', help='Danh sách khung thời gian (mặc định: 1h, 4h)')
    parser.add_argument('--lookback', type=int, nargs='+', help='Khoảng thời gian lịch sử (ngày) (mặc định: 30, 90)')
    parser.add_argument('--target', type=int, nargs='+', help='Khoảng thời gian mục tiêu (ngày) (mặc định: 1, 3)')
    parser.add_argument('--threshold', type=float, default=1.0, help='Ngưỡng phần trăm thay đổi (mặc định: 1.0)')
    parser.add_argument('--algorithms', type=str, nargs='+', help='Danh sách thuật toán (mặc định: tất cả)')
    parser.add_argument('--optimize', action='store_true', help='Tối ưu siêu tham số (mặc định: False)')
    parser.add_argument('--simulation', action='store_true', help='Chế độ mô phỏng (mặc định: False)')
    parser.add_argument('--report-only', action='store_true', help='Chỉ tạo báo cáo tổng hợp (mặc định: False)')
    
    args = parser.parse_args()
    
    # Khởi tạo trainer
    trainer = EnhancedMLTrainer(simulation_mode=args.simulation)
    
    # Chỉ tạo báo cáo tổng hợp
    if args.report_only:
        logger.info("Tạo báo cáo tổng hợp cho các mô hình đã huấn luyện")
        trainer.generate_training_summary()
        sys.exit(0)
    
    # Thiết lập các tham số
    symbols = args.symbols
    intervals = args.intervals
    lookback_periods = args.lookback
    target_days_list = args.target
    threshold_pct = args.threshold
    algorithms = args.algorithms
    optimize_hyperparams = args.optimize
    
    # Huấn luyện các mô hình
    result = trainer.train_multiple_models(
        symbols=symbols,
        intervals=intervals,
        lookback_periods=lookback_periods,
        target_days_list=target_days_list,
        threshold_pct=threshold_pct,
        algorithms=algorithms,
        optimize_hyperparams=optimize_hyperparams
    )
    
    # Tạo báo cáo tổng hợp
    trainer.generate_training_summary()
    
    return result

if __name__ == "__main__":
    main()