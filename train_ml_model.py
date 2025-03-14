#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mô đun huấn luyện mô hình ML cho dự đoán thị trường

Tác giả: BinanceTrader Bot
"""

import os
import sys
import time
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from joblib import dump, load
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ml_training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ml_training')

# Các hằng số
MODEL_DIR = './ml_models'
DATA_DIR = './data'
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "BNBUSDT"]
TIMEFRAMES = ["1h", "4h", "1d"]
MODELS = ["random_forest", "gradient_boost", "svm"]

class MLTrainer:
    """Lớp huấn luyện mô hình ML"""
    
    def __init__(self):
        """Khởi tạo MLTrainer"""
        # Tạo thư mục mô hình nếu chưa tồn tại
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR)
        
        # Tải cấu hình huấn luyện
        self.config = self.load_config()
    
    def load_config(self):
        """Tải cấu hình huấn luyện từ file"""
        try:
            if os.path.exists('advanced_ml_config.json'):
                with open('advanced_ml_config.json', 'r') as f:
                    return json.load(f)
            else:
                # Cấu hình mặc định
                config = {
                    "test_size": 0.2,
                    "random_state": 42,
                    "feature_engineering": {
                        "use_technical_indicators": True,
                        "use_price_patterns": True,
                        "use_volatility_features": True,
                        "use_volume_features": True
                    },
                    "hyperparameters": {
                        "random_forest": {
                            "n_estimators": 100,
                            "max_depth": 10,
                            "min_samples_split": 2,
                            "min_samples_leaf": 1
                        },
                        "gradient_boost": {
                            "n_estimators": 100,
                            "learning_rate": 0.1,
                            "max_depth": 3
                        },
                        "svm": {
                            "C": 1.0,
                            "kernel": "rbf",
                            "gamma": "scale"
                        }
                    },
                    "training": {
                        "use_cross_validation": True,
                        "cv_folds": 5,
                        "hyperparameter_tuning": False
                    }
                }
                # Lưu cấu hình mặc định
                with open('advanced_ml_config.json', 'w') as f:
                    json.dump(config, f, indent=4)
                return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            return {}
    
    def load_data(self, symbol, timeframe):
        """Tải dữ liệu cho cặp tiền và khung thời gian"""
        try:
            # Đường dẫn đến file dữ liệu
            file_path = os.path.join(DATA_DIR, f"{symbol}_{timeframe}.csv")
            
            if not os.path.exists(file_path):
                logger.warning(f"Không tìm thấy dữ liệu cho {symbol} {timeframe}")
                return None
            
            # Đọc dữ liệu từ file CSV
            data = pd.read_csv(file_path)
            
            # Chuyển đổi cột thời gian (nếu có)
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                data.set_index('timestamp', inplace=True)
            
            logger.info(f"Đã tải dữ liệu {symbol} {timeframe}: {len(data)} mẫu")
            return data
        
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu {symbol} {timeframe}: {str(e)}")
            return None
    
    def prepare_features(self, data):
        """Chuẩn bị đặc trưng từ dữ liệu"""
        try:
            if data is None or len(data) < 100:
                logger.warning("Không đủ dữ liệu để chuẩn bị đặc trưng")
                return None, None
            
            # Tạo bản sao để tránh cảnh báo SettingWithCopyWarning
            df = data.copy()
            
            # Tính toán các đặc trưng kỹ thuật
            feature_config = self.config.get("feature_engineering", {})
            
            features = []
            
            # Đặc trưng cơ bản từ giá
            df['return_1d'] = df['close'].pct_change(1)
            df['return_3d'] = df['close'].pct_change(3)
            df['return_5d'] = df['close'].pct_change(5)
            
            features.extend(['return_1d', 'return_3d', 'return_5d'])
            
            # Đặc trưng từ chỉ báo kỹ thuật
            if feature_config.get("use_technical_indicators", True):
                # SMA - Simple Moving Average
                df['sma_7'] = df['close'].rolling(window=7).mean()
                df['sma_14'] = df['close'].rolling(window=14).mean()
                df['sma_30'] = df['close'].rolling(window=30).mean()
                
                # Khoảng cách từ giá đến SMA
                df['close_sma_7_ratio'] = df['close'] / df['sma_7']
                df['close_sma_14_ratio'] = df['close'] / df['sma_14']
                df['close_sma_30_ratio'] = df['close'] / df['sma_30']
                
                # EMA - Exponential Moving Average
                df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
                df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
                
                # MACD
                df['macd'] = df['ema_12'] - df['ema_26']
                df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
                df['macd_hist'] = df['macd'] - df['macd_signal']
                
                # RSI
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()
                rs = avg_gain / avg_loss
                df['rsi_14'] = 100 - (100 / (1 + rs))
                
                features.extend([
                    'close_sma_7_ratio', 'close_sma_14_ratio', 'close_sma_30_ratio',
                    'macd', 'macd_signal', 'macd_hist', 'rsi_14'
                ])
            
            # Đặc trưng từ mẫu hình giá
            if feature_config.get("use_price_patterns", True):
                # Mẫu hình Candlestick
                df['body_size'] = abs(df['open'] - df['close']) / df['close']
                df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
                df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
                
                # Nhận diện mẫu hình nến Doji
                df['is_doji'] = df['body_size'] < 0.001
                
                features.extend(['body_size', 'upper_shadow', 'lower_shadow', 'is_doji'])
            
            # Đặc trưng từ biến động
            if feature_config.get("use_volatility_features", True):
                # Biến động: (high-low)/close
                df['volatility'] = (df['high'] - df['low']) / df['close']
                
                # Biến động di động
                df['volatility_7d'] = df['volatility'].rolling(window=7).mean()
                df['volatility_14d'] = df['volatility'].rolling(window=14).mean()
                
                # ATR - Average True Range (Chỉ báo biến động)
                tr1 = df['high'] - df['low']
                tr2 = abs(df['high'] - df['close'].shift(1))
                tr3 = abs(df['low'] - df['close'].shift(1))
                df['true_range'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                df['atr_14'] = df['true_range'].rolling(window=14).mean()
                
                features.extend(['volatility', 'volatility_7d', 'volatility_14d', 'atr_14'])
            
            # Đặc trưng từ khối lượng
            if feature_config.get("use_volume_features", True) and 'volume' in df.columns:
                # Khối lượng đã chuẩn hóa
                df['volume_norm'] = df['volume'] / df['volume'].rolling(window=20).mean()
                
                # OBV - On Balance Volume
                df['obv'] = np.where(
                    df['close'] > df['close'].shift(1),
                    df['volume'],
                    np.where(
                        df['close'] < df['close'].shift(1),
                        -df['volume'],
                        0
                    )
                ).cumsum()
                
                features.extend(['volume_norm', 'obv'])
            
            # Chuẩn bị nhãn: Dự đoán xu hướng giá trong tương lai
            # 1: tăng, 0: giảm, khi so sánh giá sau 3 phiên với giá hiện tại
            df['target'] = (df['close'].shift(-3) > df['close']).astype(int)
            
            # Loại bỏ các hàng có giá trị NaN
            df.dropna(inplace=True)
            
            # Tách đặc trưng và nhãn
            X = df[features]
            y = df['target']
            
            logger.info(f"Đã chuẩn bị {len(features)} đặc trưng từ {len(X)} mẫu")
            
            return X, y
        
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị đặc trưng: {str(e)}")
            return None, None
    
    def train_model(self, X, y, model_type="random_forest", symbol="BTCUSDT", timeframe="1h"):
        """Huấn luyện mô hình ML"""
        try:
            if X is None or y is None or len(X) == 0 or len(y) == 0:
                logger.warning("Không có dữ liệu để huấn luyện")
                return None
            
            logger.info(f"Bắt đầu huấn luyện mô hình {model_type} cho {symbol} {timeframe}")
            
            # Tách dữ liệu thành tập huấn luyện và tập kiểm tra
            test_size = self.config.get("test_size", 0.2)
            random_state = self.config.get("random_state", 42)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, shuffle=False
            )
            
            # Chuẩn hóa dữ liệu
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Tạo và huấn luyện mô hình dựa trên loại
            hp = self.config.get("hyperparameters", {}).get(model_type, {})
            
            if model_type == "random_forest":
                model = RandomForestClassifier(
                    n_estimators=hp.get("n_estimators", 100),
                    max_depth=hp.get("max_depth", 10),
                    min_samples_split=hp.get("min_samples_split", 2),
                    min_samples_leaf=hp.get("min_samples_leaf", 1),
                    random_state=random_state
                )
            elif model_type == "gradient_boost":
                model = GradientBoostingClassifier(
                    n_estimators=hp.get("n_estimators", 100),
                    learning_rate=hp.get("learning_rate", 0.1),
                    max_depth=hp.get("max_depth", 3),
                    random_state=random_state
                )
            elif model_type == "svm":
                model = SVC(
                    C=hp.get("C", 1.0),
                    kernel=hp.get("kernel", "rbf"),
                    gamma=hp.get("gamma", "scale"),
                    probability=True,
                    random_state=random_state
                )
            else:
                logger.error(f"Loại mô hình không hợp lệ: {model_type}")
                return None
            
            # Huấn luyện mô hình
            training_config = self.config.get("training", {})
            use_cv = training_config.get("use_cross_validation", True)
            
            if use_cv:
                # Sử dụng Cross-Validation
                cv_folds = training_config.get("cv_folds", 5)
                cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=cv_folds)
                logger.info(f"Cross-validation scores: {cv_scores}")
                logger.info(f"Cross-validation mean accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
            
            # Huấn luyện mô hình trên toàn bộ tập huấn luyện
            model.fit(X_train_scaled, y_train)
            
            # Đánh giá mô hình trên tập kiểm tra
            y_pred = model.predict(X_test_scaled)
            
            # Tính toán các chỉ số đánh giá
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            logger.info(f"Kết quả đánh giá mô hình {model_type} cho {symbol} {timeframe}:")
            logger.info(f"- Accuracy: {accuracy:.4f}")
            logger.info(f"- Precision: {precision:.4f}")
            logger.info(f"- Recall: {recall:.4f}")
            logger.info(f"- F1 score: {f1:.4f}")
            
            # Lưu mô hình và scaler
            model_filename = f"{symbol}_{timeframe}_{model_type}_model.joblib"
            scaler_filename = f"{symbol}_{timeframe}_{model_type}_scaler.joblib"
            
            model_path = os.path.join(MODEL_DIR, model_filename)
            scaler_path = os.path.join(MODEL_DIR, scaler_filename)
            
            dump(model, model_path)
            dump(scaler, scaler_path)
            
            logger.info(f"Đã lưu mô hình tại {model_path}")
            
            # Lưu thông tin đánh giá
            metrics = {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "samples_count": len(X),
                "features_count": len(X.columns),
                "test_size": test_size
            }
            
            metrics_filename = f"{symbol}_{timeframe}_{model_type}_metrics.json"
            metrics_path = os.path.join(MODEL_DIR, metrics_filename)
            
            with open(metrics_path, 'w') as f:
                json.dump(metrics, f, indent=4)
            
            return {
                "model": model,
                "scaler": scaler,
                "metrics": metrics,
                "features": list(X.columns)
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi huấn luyện mô hình {model_type} cho {symbol} {timeframe}: {str(e)}")
            return None
    
    def train_all_models(self):
        """Huấn luyện tất cả các mô hình cho các cặp tiền và khung thời gian"""
        start_time = time.time()
        logger.info("Bắt đầu huấn luyện tất cả các mô hình...")
        
        results = {}
        
        for symbol in SYMBOLS:
            results[symbol] = {}
            
            for timeframe in TIMEFRAMES:
                results[symbol][timeframe] = {}
                
                # Tải và chuẩn bị dữ liệu
                data = self.load_data(symbol, timeframe)
                X, y = self.prepare_features(data)
                
                if X is None or y is None:
                    logger.warning(f"Bỏ qua {symbol} {timeframe} do không có dữ liệu")
                    continue
                
                # Huấn luyện các loại mô hình khác nhau
                for model_type in MODELS:
                    logger.info(f"Đang huấn luyện {model_type} cho {symbol} {timeframe}...")
                    model_result = self.train_model(X, y, model_type, symbol, timeframe)
                    
                    if model_result:
                        results[symbol][timeframe][model_type] = model_result.get("metrics", {})
        
        # Tổng kết kết quả
        total_models = sum(
            sum(len(tf_results) for tf_results in sym_results.values())
            for sym_results in results.values()
        )
        
        duration = time.time() - start_time
        logger.info(f"Đã hoàn thành huấn luyện {total_models} mô hình trong {duration:.2f} giây")
        
        # Lưu báo cáo tổng hợp
        report = {
            "training_time": duration,
            "total_models": total_models,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        }
        
        with open(os.path.join(MODEL_DIR, "training_report.json"), 'w') as f:
            json.dump(report, f, indent=4)
        
        return report

def main():
    """Hàm chính"""
    logger.info("Bắt đầu quá trình huấn luyện mô hình ML...")
    
    # Tạo thư mục data nếu chưa tồn tại
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logger.info(f"Đã tạo thư mục {DATA_DIR}")
    
    # Tạo trainer và huấn luyện các mô hình
    trainer = MLTrainer()
    
    # Kiểm tra xem có tham số dòng lệnh không
    if len(sys.argv) > 1:
        # Huấn luyện cho cặp tiền và khung thời gian cụ thể
        if len(sys.argv) >= 4:
            symbol = sys.argv[1]
            timeframe = sys.argv[2]
            model_type = sys.argv[3]
            
            logger.info(f"Huấn luyện mô hình theo yêu cầu: {symbol} {timeframe} {model_type}")
            
            data = trainer.load_data(symbol, timeframe)
            X, y = trainer.prepare_features(data)
            
            if X is not None and y is not None:
                trainer.train_model(X, y, model_type, symbol, timeframe)
            else:
                logger.error("Không có dữ liệu để huấn luyện")
        else:
            logger.error("Cú pháp không hợp lệ. Sử dụng: python train_ml_model.py SYMBOL TIMEFRAME MODEL_TYPE")
    else:
        # Huấn luyện tất cả các mô hình
        trainer.train_all_models()
    
    logger.info("Hoàn thành quá trình huấn luyện mô hình ML")

if __name__ == "__main__":
    main()