#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module quản lý tích hợp ML vào hệ thống giao dịch
Tự động xử lý việc tải mô hình, tạo tín hiệu ML và tích hợp vào bot giao dịch
"""

import os
import sys
import logging
import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ml_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ml_integration_manager')

# Thêm thư mục gốc vào sys.path để import các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from app.market_regime_detector import MarketRegimeDetector
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")

class MLIntegrationManager:
    """
    Lớp quản lý tích hợp ML vào hệ thống giao dịch
    """
    
    def __init__(self, config_path: str = "ml_pipeline_results/ml_deployment_config.json", data_dir: str = "real_data"):
        """
        Khởi tạo MLIntegrationManager
        
        Args:
            config_path: Đường dẫn đến file cấu hình triển khai
            data_dir: Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)
        """
        self.config_path = config_path
        self.data_dir = data_dir
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Khởi tạo API và bộ xử lý dữ liệu
        self.api = BinanceAPI(testnet=False)
        self.data_processor = DataProcessor(self.api, data_dir=self.data_dir)
        
        # Khởi tạo Market Regime Detector
        self.regime_detector = MarketRegimeDetector()
        
        # Thư mục lưu trữ
        self.models_dir = "ml_models"
        self.signals_dir = "ml_signals"
        os.makedirs(self.signals_dir, exist_ok=True)
        
        # Từ điển lưu trữ mô hình đã tải
        self.loaded_models = {}
        
        logger.info(f"Khởi tạo MLIntegrationManager với cấu hình từ {config_path}, thư mục dữ liệu: {data_dir}")
        
        # Tải các mô hình
        self._load_all_models()
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình triển khai
        
        Returns:
            Dict chứa cấu hình
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            else:
                logger.warning(f"Không tìm thấy file cấu hình {self.config_path}")
                # Trả về cấu hình mặc định
                return {
                    "timestamp": datetime.now().isoformat(),
                    "qualified_models": {},
                    "trading_configs": {},
                    "ml_integration_enabled": False,
                    "thresholds": {
                        "profit_pct": 20.0,
                        "win_rate": 60.0
                    }
                }
                
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            return {}
    
    def _load_all_models(self):
        """Tải tất cả các mô hình được cấu hình"""
        if not self.config or "trading_configs" not in self.config:
            logger.warning("Không có cấu hình trading để tải mô hình")
            return
            
        logger.info("Tải các mô hình ML...")
        
        for key, config in self.config["trading_configs"].items():
            if "model_name" in config:
                model_name = config["model_name"]
                
                logger.info(f"Tải mô hình {model_name}")
                
                model, scaler, features = self._load_model(model_name)
                
                if model is not None:
                    self.loaded_models[key] = {
                        "model": model,
                        "scaler": scaler,
                        "features": features,
                        "config": config
                    }
                    logger.info(f"Đã tải mô hình {model_name} cho {key}")
                else:
                    logger.error(f"Không thể tải mô hình {model_name} cho {key}")
        
        logger.info(f"Đã tải {len(self.loaded_models)} mô hình")
    
    def _load_model(self, model_name: str) -> Tuple:
        """
        Tải mô hình ML từ file
        
        Args:
            model_name: Tên mô hình (không bao gồm phần mở rộng)
            
        Returns:
            Tuple (model, scaler, features)
        """
        try:
            # Đường dẫn đến các file
            model_path = os.path.join(self.models_dir, f"{model_name}_model.joblib")
            scaler_path = os.path.join(self.models_dir, f"{model_name}_scaler.joblib")
            features_path = os.path.join(self.models_dir, f"{model_name}_features.json")
            
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
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Chuẩn bị các đặc trưng cho dự đoán
        
        Args:
            df: DataFrame với dữ liệu giá và chỉ báo
            
        Returns:
            DataFrame với các đặc trưng
        """
        try:
            # Sao chép DataFrame để tránh thay đổi dữ liệu gốc
            df_features = df.copy()
            
            # Thêm các chỉ báo kỹ thuật nếu chưa có
            # RSI
            if 'rsi' not in df_features.columns:
                delta = df_features['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()
                rs = avg_gain / avg_loss
                df_features['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            if 'sma_20' not in df_features.columns:
                df_features['sma_20'] = df_features['close'].rolling(window=20).mean()
                df_features['std_20'] = df_features['close'].rolling(window=20).std()
                df_features['upper_band'] = df_features['sma_20'] + (df_features['std_20'] * 2)
                df_features['lower_band'] = df_features['sma_20'] - (df_features['std_20'] * 2)
                df_features['bb_width'] = (df_features['upper_band'] - df_features['lower_band']) / df_features['sma_20']
                df_features['bb_position'] = (df_features['close'] - df_features['lower_band']) / (df_features['upper_band'] - df_features['lower_band'])
            
            # MACD
            if 'macd' not in df_features.columns:
                ema_12 = df_features['close'].ewm(span=12, adjust=False).mean()
                ema_26 = df_features['close'].ewm(span=26, adjust=False).mean()
                df_features['macd'] = ema_12 - ema_26
                df_features['macd_signal'] = df_features['macd'].ewm(span=9, adjust=False).mean()
                df_features['macd_histogram'] = df_features['macd'] - df_features['macd_signal']
            
            # Stochastic
            if 'stoch_k' not in df_features.columns:
                low_14 = df_features['low'].rolling(window=14).min()
                high_14 = df_features['high'].rolling(window=14).max()
                df_features['stoch_k'] = 100 * ((df_features['close'] - low_14) / (high_14 - low_14))
                df_features['stoch_d'] = df_features['stoch_k'].rolling(window=3).mean()
            
            # Phân tích giá
            if 'price_change' not in df_features.columns:
                df_features['price_change'] = df_features['close'].pct_change()
                df_features['price_change_abs'] = df_features['price_change'].abs()
                df_features['price_volatility'] = df_features['price_change'].rolling(window=14).std()
            
            # Phân tích khối lượng
            if 'volume_change' not in df_features.columns:
                df_features['volume_change'] = df_features['volume'].pct_change()
                df_features['volume_ma'] = df_features['volume'].rolling(window=20).mean()
                df_features['volume_ratio'] = df_features['volume'] / df_features['volume_ma']
            
            # Thêm lag features
            lags = [1, 2, 3, 5, 7, 14, 21]
            for lag in lags:
                lag_col = f'close_lag_{lag}'
                if lag_col not in df_features.columns:
                    df_features[lag_col] = df_features['close'].shift(lag)
                    df_features[f'price_change_lag_{lag}'] = df_features['price_change'].shift(lag)
                    df_features[f'volume_change_lag_{lag}'] = df_features['volume_change'].shift(lag)
            
            # Thêm biến thời gian
            if 'hour' not in df_features.columns:
                df_features['hour'] = pd.to_datetime(df_features.index).hour
                df_features['day_of_week'] = pd.to_datetime(df_features.index).dayofweek
            
            # Phát hiện chế độ thị trường
            if 'market_regime' not in df_features.columns:
                regimes = []
                for i in range(len(df_features)):
                    window_start = max(0, i - 30)
                    if i < 30:
                        regimes.append('neutral')
                    else:
                        temp_df = df_features.iloc[window_start:i+1].copy()
                        regime = self.regime_detector.detect_regime(temp_df)
                        regimes.append(regime)
                
                df_features['market_regime'] = regimes
                
                # One-hot encoding cho market regime
                for regime in ['uptrend', 'downtrend', 'ranging', 'volatile']:
                    df_features[f'regime_{regime}'] = (df_features['market_regime'] == regime).astype(int)
            
            # Loại bỏ các giá trị NaN
            df_features = df_features.replace([np.inf, -np.inf], np.nan)
            df_features = df_features.fillna(0)
            
            return df_features
            
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị đặc trưng: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return df
    
    def generate_ml_signal(self, symbol: str, interval: str, lookback_days: int = 30) -> Dict:
        """
        Tạo tín hiệu ML cho một cặp tiền và khung thời gian
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            lookback_days: Số ngày lịch sử
            
        Returns:
            Dict chứa tín hiệu ML
        """
        key = f"{symbol}_{interval}"
        
        # Kiểm tra xem có mô hình cho cặp tiền và khung thời gian này không
        if key not in self.loaded_models:
            logger.warning(f"Không có mô hình cho {key}")
            return {"symbol": symbol, "interval": interval, "signal": 0, "ml_enabled": False}
        
        try:
            # Lấy thông tin mô hình
            model_info = self.loaded_models[key]
            model = model_info["model"]
            scaler = model_info["scaler"]
            features = model_info["features"]
            config = model_info["config"]
            
            # Tải dữ liệu lịch sử
            df = self.data_processor.get_historical_data(symbol, interval, lookback_days=lookback_days)
            
            if df is None or len(df) < 30:
                logger.error(f"Không đủ dữ liệu cho {symbol} {interval}")
                return {"symbol": symbol, "interval": interval, "signal": 0, "ml_enabled": False}
            
            # Chuẩn bị đặc trưng
            df_features = self.prepare_features(df)
            
            # Lọc các đặc trưng cần thiết
            available_features = [f for f in features if f in df_features.columns]
            
            if len(available_features) < len(features):
                missing = set(features) - set(available_features)
                logger.warning(f"Thiếu {len(missing)} đặc trưng: {missing}")
            
            X = df_features[available_features].iloc[-1:].copy()
            
            # Chuẩn hóa đặc trưng
            X_scaled = scaler.transform(X)
            
            # Dự đoán
            prediction = model.predict(X_scaled)[0]
            
            # Lấy xác suất nếu có
            probability = 0.5
            if hasattr(model, 'predict_proba'):
                try:
                    probas = model.predict_proba(X_scaled)[0]
                    # Lấy xác suất cao nhất
                    probability = np.max(probas)
                except:
                    pass
            
            # Áp dụng chế độ thị trường
            market_regime = df_features['market_regime'].iloc[-1]
            
            # Tạo tín hiệu
            signal = {
                "symbol": symbol,
                "interval": interval,
                "timestamp": datetime.now().isoformat(),
                "price": float(df['close'].iloc[-1]),
                "model_name": config["model_name"],
                "ml_signal": int(prediction),
                "ml_probability": float(probability),
                "market_regime": market_regime,
                "ml_enabled": True,
                "use_integration": config.get("use_integration", True),
                "risk_pct": config.get("risk_pct", 10),
                "leverage": config.get("leverage", 20)
            }
            
            # Lưu tín hiệu
            signal_filename = os.path.join(
                self.signals_dir,
                f"{symbol}_{interval}_ml_signal.json"
            )
            
            with open(signal_filename, 'w') as f:
                json.dump(signal, f, indent=2)
                
            logger.info(f"Đã tạo tín hiệu ML cho {symbol} {interval}: {prediction} (prob: {probability:.4f})")
            
            return signal
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu ML cho {symbol} {interval}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"symbol": symbol, "interval": interval, "signal": 0, "ml_enabled": False}
    
    def generate_high_risk_signal(self, symbol: str, interval: str, lookback_days: int = 30) -> Dict:
        """
        Tạo tín hiệu chiến lược rủi ro cao
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            lookback_days: Số ngày lịch sử
            
        Returns:
            Dict chứa tín hiệu rủi ro cao
        """
        try:
            # Tải dữ liệu lịch sử
            df = self.data_processor.get_historical_data(symbol, interval, lookback_days=lookback_days)
            
            if df is None or len(df) < 30:
                logger.error(f"Không đủ dữ liệu cho {symbol} {interval}")
                return {"symbol": symbol, "interval": interval, "signal": 0, "high_risk_enabled": False}
            
            # Chuẩn bị đặc trưng
            df_features = self.prepare_features(df)
            
            # Lấy các giá trị cuối cùng
            last_row = df_features.iloc[-1]
            
            # Các điều kiện mua mạnh
            buy_conditions = (
                (last_row['rsi'] < 25) and  # RSI quá bán mạnh
                (last_row['close'] < last_row['lower_band']) and  # Giá dưới dải dưới
                (last_row['volume_ratio'] > 1.5)  # Khối lượng tăng
            )
            
            # Các điều kiện bán mạnh
            sell_conditions = (
                (last_row['rsi'] > 75) and  # RSI quá mua mạnh
                (last_row['close'] > last_row['upper_band']) and  # Giá trên dải trên
                (last_row['volume_ratio'] > 1.5)  # Khối lượng tăng
            )
            
            # Đặt tín hiệu
            high_risk_signal = 0
            if buy_conditions:
                high_risk_signal = 1
            elif sell_conditions:
                high_risk_signal = -1
            
            # Tạo tín hiệu
            signal = {
                "symbol": symbol,
                "interval": interval,
                "timestamp": datetime.now().isoformat(),
                "price": float(df['close'].iloc[-1]),
                "high_risk_signal": high_risk_signal,
                "rsi": float(last_row['rsi']),
                "bb_position": float(last_row['bb_position']),
                "volume_ratio": float(last_row['volume_ratio']),
                "market_regime": last_row['market_regime'],
                "high_risk_enabled": True
            }
            
            # Lưu tín hiệu
            signal_filename = os.path.join(
                self.signals_dir,
                f"{symbol}_{interval}_high_risk_signal.json"
            )
            
            with open(signal_filename, 'w') as f:
                json.dump(signal, f, indent=2)
                
            logger.info(f"Đã tạo tín hiệu rủi ro cao cho {symbol} {interval}: {high_risk_signal}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu rủi ro cao cho {symbol} {interval}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"symbol": symbol, "interval": interval, "signal": 0, "high_risk_enabled": False}
    
    def generate_integrated_signal(self, symbol: str, interval: str) -> Dict:
        """
        Tạo tín hiệu tích hợp ML và chiến lược rủi ro cao
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            
        Returns:
            Dict chứa tín hiệu tích hợp
        """
        # Kiểm tra xem ML có được bật không
        if not self.config.get("ml_integration_enabled", False):
            logger.info(f"Tích hợp ML đã bị tắt theo cấu hình")
            return {"symbol": symbol, "interval": interval, "signal": 0, "integration_enabled": False}
        
        # Tạo tín hiệu ML
        ml_signal_result = self.generate_ml_signal(symbol, interval)
        
        # Tạo tín hiệu rủi ro cao
        high_risk_signal_result = self.generate_high_risk_signal(symbol, interval)
        
        # Tích hợp tín hiệu
        ml_signal = ml_signal_result.get("ml_signal", 0)
        high_risk_signal = high_risk_signal_result.get("high_risk_signal", 0)
        
        # Chỉ mua khi cả hai đều đồng ý
        if ml_signal == 1 and high_risk_signal == 1:
            integrated_signal = 1
        # Chỉ bán khi cả hai đều đồng ý
        elif ml_signal == -1 and high_risk_signal == -1:
            integrated_signal = -1
        # Nếu không đồng thuận, không có tín hiệu
        else:
            integrated_signal = 0
        
        # Tạo tín hiệu
        key = f"{symbol}_{interval}"
        config = self.loaded_models.get(key, {}).get("config", {})
        
        signal = {
            "symbol": symbol,
            "interval": interval,
            "timestamp": datetime.now().isoformat(),
            "price": ml_signal_result.get("price", 0),
            "ml_signal": ml_signal,
            "high_risk_signal": high_risk_signal,
            "integrated_signal": integrated_signal,
            "market_regime": ml_signal_result.get("market_regime", "unknown"),
            "ml_probability": ml_signal_result.get("ml_probability", 0),
            "integration_enabled": True,
            "risk_pct": config.get("risk_pct", 10),
            "leverage": config.get("leverage", 20)
        }
        
        # Lưu tín hiệu
        signal_filename = os.path.join(
            self.signals_dir,
            f"{symbol}_{interval}_integrated_signal.json"
        )
        
        with open(signal_filename, 'w') as f:
            json.dump(signal, f, indent=2)
            
        logger.info(f"Đã tạo tín hiệu tích hợp cho {symbol} {interval}: {integrated_signal}")
        
        return signal
    
    def generate_all_signals(self) -> Dict:
        """
        Tạo tín hiệu cho tất cả các cặp tiền được cấu hình
        
        Returns:
            Dict chứa tất cả các tín hiệu
        """
        all_signals = {}
        
        # Lấy danh sách cặp tiền và khung thời gian từ cấu hình
        if not self.config or "trading_configs" not in self.config:
            logger.warning("Không có cấu hình trading để tạo tín hiệu")
            return all_signals
        
        for key, config in self.config["trading_configs"].items():
            if "symbol" in config and "interval" in config:
                symbol = config["symbol"]
                interval = config["interval"]
                
                # Tạo tín hiệu tích hợp
                signal = self.generate_integrated_signal(symbol, interval)
                
                all_signals[key] = signal
        
        # Lưu tất cả tín hiệu
        all_signals_filename = os.path.join(
            self.signals_dir,
            f"all_ml_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(all_signals_filename, 'w') as f:
            json.dump(all_signals, f, indent=2)
            
        logger.info(f"Đã tạo tín hiệu cho {len(all_signals)} cặp tiền")
        
        return all_signals
    
    def update_system_with_ml_signals(self) -> Dict:
        """
        Cập nhật hệ thống giao dịch với tín hiệu ML
        
        Returns:
            Dict chứa thông tin cập nhật
        """
        # Tạo tín hiệu cho tất cả các cặp tiền
        all_signals = self.generate_all_signals()
        
        # Tạo file tích hợp cho hệ thống giao dịch
        integration_filename = os.path.join(
            ".",  # Thư mục gốc
            "ml_integration_signals.json"
        )
        
        # Chuyển đổi dạng tín hiệu thành dạng phù hợp với hệ thống giao dịch
        system_signals = {
            "timestamp": datetime.now().isoformat(),
            "signals": {},
            "ml_integration_enabled": self.config.get("ml_integration_enabled", False)
        }
        
        for key, signal in all_signals.items():
            symbol = signal["symbol"]
            
            system_signals["signals"][symbol] = {
                "ml_signal": signal.get("integrated_signal", 0),
                "probability": signal.get("ml_probability", 0),
                "market_regime": signal.get("market_regime", "unknown"),
                "risk_pct": signal.get("risk_pct", 10),
                "leverage": signal.get("leverage", 20),
                "timestamp": signal.get("timestamp", datetime.now().isoformat())
            }
        
        # Lưu tín hiệu tích hợp
        with open(integration_filename, 'w') as f:
            json.dump(system_signals, f, indent=2)
            
        logger.info(f"Đã cập nhật hệ thống với tín hiệu ML: {integration_filename}")
        
        return system_signals
    
    def run_continuous_update(self, interval_minutes: int = 60):
        """
        Chạy cập nhật liên tục theo khoảng thời gian
        
        Args:
            interval_minutes: Khoảng thời gian cập nhật (phút)
        """
        logger.info(f"Bắt đầu cập nhật liên tục với khoảng thời gian {interval_minutes} phút")
        
        try:
            while True:
                # Cập nhật hệ thống với tín hiệu ML
                self.update_system_with_ml_signals()
                
                # Chờ đến lần cập nhật tiếp theo
                logger.info(f"Chờ {interval_minutes} phút đến lần cập nhật tiếp theo...")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("Đã dừng cập nhật liên tục")
        except Exception as e:
            logger.error(f"Lỗi khi chạy cập nhật liên tục: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

def main():
    """Hàm chính"""
    import argparse
    
    # Thiết lập parser dòng lệnh
    parser = argparse.ArgumentParser(description='Quản lý tích hợp ML vào hệ thống giao dịch')
    parser.add_argument('--config', type=str, 
                      help='Đường dẫn đến file cấu hình triển khai')
    parser.add_argument('--interval', type=int, default=60, 
                      help='Khoảng thời gian cập nhật (phút) (mặc định: 60)')
    parser.add_argument('--symbol', type=str, 
                      help='Mã tiền (chỉ tạo tín hiệu cho một cặp tiền)')
    parser.add_argument('--timeframe', type=str, 
                      help='Khung thời gian (chỉ tạo tín hiệu cho một khung thời gian)')
    parser.add_argument('--mode', type=str, choices=['once', 'continuous'], default='once', 
                      help='Chế độ chạy (mặc định: once)')
    parser.add_argument('--data-dir', type=str, default='real_data',
                      help='Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)')
    
    args = parser.parse_args()
    
    # Khởi tạo manager
    config_path = args.config if args.config else "ml_pipeline_results/ml_deployment_config.json"
    manager = MLIntegrationManager(config_path=config_path, data_dir=args.data_dir)
    
    # Chọn chế độ chạy
    if args.symbol and args.timeframe:
        # Chỉ tạo tín hiệu cho một cặp tiền
        logger.info(f"Tạo tín hiệu cho {args.symbol} {args.timeframe}")
        signal = manager.generate_integrated_signal(args.symbol, args.timeframe)
        print(json.dumps(signal, indent=2))
    elif args.mode == 'continuous':
        # Chạy cập nhật liên tục
        manager.run_continuous_update(interval_minutes=args.interval)
    else:
        # Chạy một lần
        logger.info("Cập nhật hệ thống với tín hiệu ML (một lần)")
        signals = manager.update_system_with_ml_signals()
        print(json.dumps(signals, indent=2))
    
    logger.info("Hoàn tất")

if __name__ == "__main__":
    main()