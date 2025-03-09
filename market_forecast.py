"""
Module dự báo thị trường sử dụng học máy và phân tích kỹ thuật

Module này phân tích dữ liệu thị trường và dự báo xu hướng giá,
biến động và khuyến nghị giao dịch trong tương lai gần.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any, Optional, Union
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, mean_squared_error, r2_score
import joblib

# Thêm thư mục gốc vào đường dẫn
import sys
sys.path.append('.')

# Import các module cần thiết
from binance_api import BinanceAPI
from data_processor import DataProcessor
from market_regime_detector import MarketRegimeDetector

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('market_forecast.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("market_forecast")

class MarketForecast:
    """Lớp dự báo thị trường"""
    
    def __init__(self, models_dir: str = 'models', data_dir: str = 'forecast_data'):
        """
        Khởi tạo Market Forecast
        
        Args:
            models_dir (str): Thư mục lưu mô hình
            data_dir (str): Thư mục lưu dữ liệu
        """
        self.models_dir = models_dir
        self.data_dir = data_dir
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(models_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        
        # Khởi tạo các thành phần
        self.binance_api = self._init_binance_api()
        self.data_processor = DataProcessor(binance_api=self.binance_api)
        self.market_regime_detector = MarketRegimeDetector()
        
        # Khởi tạo mô hình
        self.models = {}
        self.scalers = {}
        
    def _init_binance_api(self) -> BinanceAPI:
        """
        Khởi tạo Binance API
        
        Returns:
            BinanceAPI: Đối tượng Binance API
        """
        try:
            # Lấy API key và secret từ biến môi trường
            api_key = os.environ.get('BINANCE_API_KEY')
            api_secret = os.environ.get('BINANCE_API_SECRET')
                
            return BinanceAPI(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True
            )
        except Exception as e:
            logger.error(f"Không thể khởi tạo Binance API: {str(e)}")
            return None
            
    def fetch_data(self, symbol: str, interval: str = '1h', 
                 days: int = 30) -> pd.DataFrame:
        """
        Tải dữ liệu từ Binance
        
        Args:
            symbol (str): Mã cặp giao dịch
            interval (str): Khung thời gian
            days (int): Số ngày dữ liệu
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu
        """
        try:
            # Tính thời gian bắt đầu và kết thúc
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # Tải dữ liệu
            df = self.data_processor.download_historical_data(
                symbol=symbol,
                interval=interval,
                start_time=start_time.strftime("%Y-%m-%d"),
                end_time=end_time.strftime("%Y-%m-%d"),
                output_dir=self.data_dir
            )
            
            if df is not None and not df.empty:
                logger.info(f"Đã tải dữ liệu {symbol}_{interval}: {len(df)} dòng")
                return df
            else:
                logger.warning(f"Không tải được dữ liệu {symbol}_{interval}")
                return None
                
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu {symbol}_{interval}: {str(e)}")
            return None
            
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Chuẩn bị các đặc trưng cho dự báo
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            
        Returns:
            pd.DataFrame: DataFrame với các đặc trưng đã tính
        """
        try:
            # Thêm các chỉ báo kỹ thuật
            df_with_indicators = self.data_processor.add_indicators(df)
            
            # Thêm các đặc trưng dự báo
            forecast_df = df_with_indicators.copy()
            
            # Thêm đặc trưng biến động giá
            forecast_df['price_change'] = forecast_df['close'].pct_change()
            forecast_df['price_change_1d'] = forecast_df['close'].pct_change(24)  # 1 day (assuming 1h data)
            forecast_df['price_change_1w'] = forecast_df['close'].pct_change(168)  # 1 week
            
            # Thêm đặc trưng biến động khối lượng
            forecast_df['volume_change'] = forecast_df['volume'].pct_change()
            forecast_df['volume_change_1d'] = forecast_df['volume'].pct_change(24)
            
            # Thêm đặc trưng xu hướng
            forecast_df['trend_1d'] = (forecast_df['close'] > forecast_df['close'].shift(24)).astype(int)
            forecast_df['trend_1w'] = (forecast_df['close'] > forecast_df['close'].shift(168)).astype(int)
            
            # Thêm đặc trưng giá so với trung bình động
            forecast_df['price_vs_ema9'] = forecast_df['close'] / forecast_df['ema9'] - 1
            forecast_df['price_vs_ema21'] = forecast_df['close'] / forecast_df['ema21'] - 1
            forecast_df['price_vs_ema50'] = forecast_df['close'] / forecast_df['ema50'] - 1
            
            # Đánh dấu chế độ thị trường
            regime = self.market_regime_detector.detect_regime(forecast_df)
            forecast_df['market_regime'] = regime
            
            # Thêm mục tiêu dự báo (price_change sau 1, 3, 7 ngày)
            forecast_df['target_price_1d'] = forecast_df['close'].pct_change(-24)  # Biến đổi giá 1 ngày sau
            forecast_df['target_price_3d'] = forecast_df['close'].pct_change(-72)  # Biến đổi giá 3 ngày sau
            forecast_df['target_price_7d'] = forecast_df['close'].pct_change(-168)  # Biến đổi giá 7 ngày sau
            
            # Thêm mục tiêu xu hướng (lên/xuống)
            forecast_df['target_trend_1d'] = (forecast_df['close'].shift(-24) > forecast_df['close']).astype(int)
            forecast_df['target_trend_3d'] = (forecast_df['close'].shift(-72) > forecast_df['close']).astype(int)
            forecast_df['target_trend_7d'] = (forecast_df['close'].shift(-168) > forecast_df['close']).astype(int)
            
            # Loại bỏ các dòng có giá trị NaN
            forecast_df = forecast_df.dropna()
            
            logger.info(f"Đã chuẩn bị đặc trưng dự báo: {len(forecast_df)} dòng")
            return forecast_df
            
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị đặc trưng: {str(e)}")
            return df
            
    def train_forecast_model(self, df: pd.DataFrame, 
                          forecast_period: str = '1d',
                          forecast_type: str = 'trend',
                          test_size: float = 0.2) -> bool:
        """
        Huấn luyện mô hình dự báo
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            forecast_period (str): Kỳ dự báo ('1d', '3d', '7d')
            forecast_type (str): Loại dự báo ('trend', 'price')
            test_size (float): Tỷ lệ dữ liệu test
            
        Returns:
            bool: True nếu huấn luyện thành công, False nếu không
        """
        try:
            # Kiểm tra dữ liệu
            if df is None or df.empty:
                logger.warning("Không có dữ liệu để huấn luyện")
                return False
                
            # Xác định cột mục tiêu
            target_col = f"target_{forecast_type}_{forecast_period}"
            
            if target_col not in df.columns:
                logger.warning(f"Không tìm thấy cột mục tiêu {target_col}")
                return False
                
            # Lấy các đặc trưng
            feature_cols = [
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'bb_upper', 'bb_middle', 'bb_lower',
                'ema9', 'ema21', 'ema50', 'ema200',
                'atr', 'stoch_k', 'stoch_d',
                'price_change', 'price_change_1d', 'price_change_1w',
                'volume_change', 'volume_change_1d',
                'price_vs_ema9', 'price_vs_ema21', 'price_vs_ema50'
            ]
            
            # Loại bỏ các cột không tồn tại
            feature_cols = [col for col in feature_cols if col in df.columns]
            
            # Chuẩn bị dữ liệu
            X = df[feature_cols].values
            y = df[target_col].values
            
            # Chia dữ liệu
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
            
            # Chuẩn hóa dữ liệu
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Lưu scaler
            model_key = f"{forecast_type}_{forecast_period}"
            self.scalers[model_key] = scaler
            
            # Huấn luyện mô hình
            if forecast_type == 'trend':
                # Phân loại xu hướng (lên/xuống)
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(X_train_scaled, y_train)
                
                # Đánh giá mô hình
                y_pred = model.predict(X_test_scaled)
                accuracy = accuracy_score(y_test, y_pred)
                
                logger.info(f"Mô hình dự báo xu hướng {forecast_period} - Accuracy: {accuracy:.4f}")
                
            else:
                # Dự báo giá (hồi quy)
                model = GradientBoostingRegressor(n_estimators=100, random_state=42)
                model.fit(X_train_scaled, y_train)
                
                # Đánh giá mô hình
                y_pred = model.predict(X_test_scaled)
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                logger.info(f"Mô hình dự báo giá {forecast_period} - MSE: {mse:.4f}, R²: {r2:.4f}")
            
            # Lưu mô hình
            self.models[model_key] = model
            
            # Lưu mô hình và scaler vào file
            model_path = os.path.join(self.models_dir, f"forecast_{model_key}_model.joblib")
            scaler_path = os.path.join(self.models_dir, f"forecast_{model_key}_scaler.joblib")
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            
            # Lưu thông tin đặc trưng
            feature_info = {
                'feature_columns': feature_cols,
                'forecast_type': forecast_type,
                'forecast_period': forecast_period
            }
            
            feature_path = os.path.join(self.models_dir, f"forecast_{model_key}_features.json")
            with open(feature_path, 'w') as f:
                json.dump(feature_info, f, indent=2)
            
            logger.info(f"Đã lưu mô hình dự báo {model_key}: {model_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi huấn luyện mô hình dự báo: {str(e)}")
            return False
            
    def load_forecast_models(self) -> bool:
        """
        Tải mô hình dự báo từ file
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            # Tìm tất cả các file mô hình dự báo
            model_files = [f for f in os.listdir(self.models_dir) if f.startswith('forecast_') and f.endswith('_model.joblib')]
            
            for model_file in model_files:
                try:
                    # Phân tích tên file để lấy thông tin
                    parts = model_file.replace('forecast_', '').replace('_model.joblib', '').split('_')
                    forecast_type = parts[0]
                    forecast_period = parts[1]
                    
                    # Tạo model key
                    model_key = f"{forecast_type}_{forecast_period}"
                    
                    # Kiểm tra xem file scaler và feature có tồn tại không
                    scaler_path = os.path.join(self.models_dir, f"forecast_{model_key}_scaler.joblib")
                    feature_path = os.path.join(self.models_dir, f"forecast_{model_key}_features.json")
                    
                    if not os.path.exists(scaler_path) or not os.path.exists(feature_path):
                        logger.warning(f"Thiếu file scaler hoặc feature cho mô hình {model_key}")
                        continue
                    
                    # Tải mô hình và scaler
                    model_path = os.path.join(self.models_dir, model_file)
                    self.models[model_key] = joblib.load(model_path)
                    self.scalers[model_key] = joblib.load(scaler_path)
                    
                    logger.info(f"Đã tải mô hình dự báo {model_key}: {model_path}")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tải mô hình {model_file}: {str(e)}")
            
            return len(self.models) > 0
            
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình dự báo: {str(e)}")
            return False
            
    def predict_forecast(self, df: pd.DataFrame, 
                      forecast_period: str = '1d',
                      forecast_type: str = 'trend') -> Dict:
        """
        Dự báo xu hướng hoặc giá
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            forecast_period (str): Kỳ dự báo ('1d', '3d', '7d')
            forecast_type (str): Loại dự báo ('trend', 'price')
            
        Returns:
            Dict: Kết quả dự báo
        """
        try:
            # Kiểm tra dữ liệu
            if df is None or df.empty:
                logger.warning("Không có dữ liệu để dự báo")
                return {}
                
            # Lấy dòng dữ liệu gần nhất
            latest_data = df.iloc[-1:].copy()
            
            # Tạo model key
            model_key = f"{forecast_type}_{forecast_period}"
            
            # Kiểm tra xem có mô hình không
            if model_key not in self.models:
                loaded = self.load_forecast_models()
                if not loaded or model_key not in self.models:
                    logger.warning(f"Không có mô hình dự báo {model_key}")
                    return {}
            
            # Lấy thông tin đặc trưng
            feature_path = os.path.join(self.models_dir, f"forecast_{model_key}_features.json")
            if not os.path.exists(feature_path):
                logger.warning(f"Không tìm thấy file thông tin đặc trưng: {feature_path}")
                return {}
                
            with open(feature_path, 'r') as f:
                feature_info = json.load(f)
                
            feature_cols = feature_info.get('feature_columns', [])
            
            # Kiểm tra các cột
            for col in feature_cols:
                if col not in latest_data.columns:
                    logger.warning(f"Thiếu cột {col} trong dữ liệu")
                    return {}
            
            # Lấy đặc trưng
            X = latest_data[feature_cols].values
            
            # Chuẩn hóa
            X_scaled = self.scalers[model_key].transform(X)
            
            # Dự báo
            model = self.models[model_key]
            
            if forecast_type == 'trend':
                # Dự báo xu hướng và xác suất
                prediction = model.predict(X_scaled)[0]
                probabilities = model.predict_proba(X_scaled)[0]
                
                result = {
                    'trend': 'up' if prediction == 1 else 'down',
                    'probability': float(probabilities[prediction]),
                    'forecast_period': forecast_period,
                    'timestamp': datetime.now().isoformat()
                }
                
            else:
                # Dự báo giá
                prediction = model.predict(X_scaled)[0]
                
                result = {
                    'price_change': float(prediction),
                    'forecast_period': forecast_period,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Tính giá dự báo
                current_price = latest_data['close'].values[0]
                forecast_price = current_price * (1 + prediction)
                result['current_price'] = float(current_price)
                result['forecast_price'] = float(forecast_price)
            
            logger.info(f"Đã dự báo {forecast_type} cho {forecast_period}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi dự báo {forecast_type} cho {forecast_period}: {str(e)}")
            return {}
            
    def prepare_all_forecasts(self, symbol: str, interval: str = '1h') -> Dict:
        """
        Chuẩn bị tất cả các dự báo cho một symbol
        
        Args:
            symbol (str): Mã cặp giao dịch
            interval (str): Khung thời gian
            
        Returns:
            Dict: Tất cả các dự báo
        """
        try:
            # Tải dữ liệu
            df = self.fetch_data(symbol, interval, days=60)
            
            if df is None or df.empty:
                logger.warning(f"Không có dữ liệu cho {symbol} {interval}")
                return {}
                
            # Chuẩn bị đặc trưng
            forecast_df = self.prepare_features(df)
            
            # Huấn luyện mô hình nếu chưa có
            if not self.models:
                for forecast_type in ['trend', 'price']:
                    for forecast_period in ['1d', '3d', '7d']:
                        self.train_forecast_model(
                            df=forecast_df,
                            forecast_type=forecast_type,
                            forecast_period=forecast_period
                        )
            
            # Dự báo
            forecasts = {
                'symbol': symbol,
                'interval': interval,
                'timestamp': datetime.now().isoformat(),
                'market_regime': self.market_regime_detector.detect_regime(forecast_df),
                'trend_forecasts': {},
                'price_forecasts': {}
            }
            
            # Dự báo xu hướng
            for period in ['1d', '3d', '7d']:
                forecast = self.predict_forecast(
                    df=forecast_df,
                    forecast_type='trend',
                    forecast_period=period
                )
                
                if forecast:
                    forecasts['trend_forecasts'][period] = forecast
            
            # Dự báo giá
            for period in ['1d', '3d', '7d']:
                forecast = self.predict_forecast(
                    df=forecast_df,
                    forecast_type='price',
                    forecast_period=period
                )
                
                if forecast:
                    forecasts['price_forecasts'][period] = forecast
            
            # Thêm thông tin giá hiện tại
            current_price = forecast_df['close'].iloc[-1]
            forecasts['current_price'] = float(current_price)
            
            # Thêm đề xuất giao dịch
            forecasts['trading_recommendation'] = self._generate_trading_recommendation(forecasts)
            
            # Lưu dự báo vào file
            output_path = os.path.join(self.data_dir, f"{symbol}_forecast.json")
            with open(output_path, 'w') as f:
                json.dump(forecasts, f, indent=2)
                
            logger.info(f"Đã lưu dự báo cho {symbol}: {output_path}")
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị dự báo cho {symbol}: {str(e)}")
            return {}
            
    def _generate_trading_recommendation(self, forecasts: Dict) -> Dict:
        """
        Tạo đề xuất giao dịch từ các dự báo
        
        Args:
            forecasts (Dict): Các dự báo
            
        Returns:
            Dict: Đề xuất giao dịch
        """
        try:
            recommendation = {
                'action': 'hold',  # Mặc định: giữ
                'confidence': 0.0,
                'reason': '',
                'entry_price': forecasts.get('current_price', 0),
                'stop_loss': 0.0,
                'take_profit': 0.0,
                'risk_reward_ratio': 0.0
            }
            
            # Lấy các dự báo
            trend_1d = forecasts.get('trend_forecasts', {}).get('1d', {})
            trend_3d = forecasts.get('trend_forecasts', {}).get('3d', {})
            trend_7d = forecasts.get('trend_forecasts', {}).get('7d', {})
            
            price_1d = forecasts.get('price_forecasts', {}).get('1d', {})
            price_3d = forecasts.get('price_forecasts', {}).get('3d', {})
            price_7d = forecasts.get('price_forecasts', {}).get('7d', {})
            
            market_regime = forecasts.get('market_regime', 'unknown')
            
            # Tính điểm dự báo
            buy_score = 0.0
            sell_score = 0.0
            count = 0
            
            # Đánh giá xu hướng
            if trend_1d:
                weight = 0.4
                if trend_1d.get('trend') == 'up':
                    buy_score += weight * trend_1d.get('probability', 0.5)
                else:
                    sell_score += weight * trend_1d.get('probability', 0.5)
                count += weight
                
            if trend_3d:
                weight = 0.3
                if trend_3d.get('trend') == 'up':
                    buy_score += weight * trend_3d.get('probability', 0.5)
                else:
                    sell_score += weight * trend_3d.get('probability', 0.5)
                count += weight
                
            if trend_7d:
                weight = 0.3
                if trend_7d.get('trend') == 'up':
                    buy_score += weight * trend_7d.get('probability', 0.5)
                else:
                    sell_score += weight * trend_7d.get('probability', 0.5)
                count += weight
            
            # Đánh giá mức thay đổi giá
            if price_1d and price_3d and price_7d:
                price_change_1d = price_1d.get('price_change', 0)
                price_change_3d = price_3d.get('price_change', 0)
                price_change_7d = price_7d.get('price_change', 0)
                
                # Tính trung bình có trọng số
                avg_price_change = (0.4 * price_change_1d + 0.3 * price_change_3d + 0.3 * price_change_7d)
                
                # Thêm vào điểm
                if avg_price_change > 0:
                    buy_score += 0.3 * min(1.0, abs(avg_price_change) * 10)  # Giới hạn ở 1.0
                else:
                    sell_score += 0.3 * min(1.0, abs(avg_price_change) * 10)
                    
                count += 0.3
            
            # Tính điểm cuối cùng
            if count > 0:
                buy_score = buy_score / count
                sell_score = sell_score / count
            
            # Quyết định hành động
            if buy_score > 0.6 and buy_score > sell_score:
                recommendation['action'] = 'buy'
                recommendation['confidence'] = buy_score
                recommendation['reason'] = f"Xu hướng tăng {buy_score:.2f}, Chế độ thị trường: {market_regime}"
                
                # Tính stop loss và take profit
                current_price = forecasts.get('current_price', 0)
                if current_price > 0:
                    # Stop loss: 2-3% tùy theo chế độ thị trường
                    stop_loss_pct = 0.03 if market_regime == 'volatile' else 0.02
                    recommendation['stop_loss'] = current_price * (1 - stop_loss_pct)
                    
                    # Take profit: 2-3 lần stop loss
                    take_profit_pct = stop_loss_pct * 2.5
                    recommendation['take_profit'] = current_price * (1 + take_profit_pct)
                    
                    # Risk-reward ratio
                    recommendation['risk_reward_ratio'] = take_profit_pct / stop_loss_pct
                
            elif sell_score > 0.6 and sell_score > buy_score:
                recommendation['action'] = 'sell'
                recommendation['confidence'] = sell_score
                recommendation['reason'] = f"Xu hướng giảm {sell_score:.2f}, Chế độ thị trường: {market_regime}"
                
                # Tính stop loss và take profit
                current_price = forecasts.get('current_price', 0)
                if current_price > 0:
                    # Stop loss: 2-3% tùy theo chế độ thị trường
                    stop_loss_pct = 0.03 if market_regime == 'volatile' else 0.02
                    recommendation['stop_loss'] = current_price * (1 + stop_loss_pct)
                    
                    # Take profit: 2-3 lần stop loss
                    take_profit_pct = stop_loss_pct * 2.5
                    recommendation['take_profit'] = current_price * (1 - take_profit_pct)
                    
                    # Risk-reward ratio
                    recommendation['risk_reward_ratio'] = take_profit_pct / stop_loss_pct
            else:
                recommendation['reason'] = f"Không đủ tín hiệu rõ ràng (Mua: {buy_score:.2f}, Bán: {sell_score:.2f})"
                
            return recommendation
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo đề xuất giao dịch: {str(e)}")
            return {'action': 'hold', 'reason': 'error'}
    
    def create_forecast_chart(self, symbol: str) -> str:
        """
        Tạo biểu đồ dự báo
        
        Args:
            symbol (str): Mã cặp giao dịch
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        try:
            # Kiểm tra file dự báo
            forecast_path = os.path.join(self.data_dir, f"{symbol}_forecast.json")
            if not os.path.exists(forecast_path):
                logger.warning(f"Không tìm thấy file dự báo: {forecast_path}")
                return None
                
            # Đọc dự báo
            with open(forecast_path, 'r') as f:
                forecasts = json.load(f)
                
            # Tải dữ liệu giá
            df = self.fetch_data(symbol, interval='1h', days=30)
            
            if df is None or df.empty:
                logger.warning(f"Không có dữ liệu cho {symbol}")
                return None
            
            # Lấy giá hiện tại và dự báo
            current_price = forecasts.get('current_price', 0)
            
            price_1d = forecasts.get('price_forecasts', {}).get('1d', {}).get('forecast_price', 0)
            price_3d = forecasts.get('price_forecasts', {}).get('3d', {}).get('forecast_price', 0)
            price_7d = forecasts.get('price_forecasts', {}).get('7d', {}).get('forecast_price', 0)
            
            # Tạo biểu đồ
            plt.figure(figsize=(12, 8))
            
            # Vẽ giá lịch sử
            plt.plot(df.index, df['close'], label='Giá đóng cửa', color='blue')
            
            # Vẽ giá dự báo
            last_date = df.index[-1]
            forecast_dates = [
                last_date + timedelta(days=1),
                last_date + timedelta(days=3),
                last_date + timedelta(days=7)
            ]
            
            forecast_prices = [price_1d, price_3d, price_7d]
            
            plt.plot(forecast_dates, forecast_prices, 'r--', label='Dự báo giá')
            plt.scatter(forecast_dates, forecast_prices, color='red', s=50)
            
            # Thêm chú thích
            for i, date in enumerate(forecast_dates):
                plt.annotate(f"{forecast_prices[i]:.2f}", 
                          (date, forecast_prices[i]),
                          textcoords="offset points",
                          xytext=(0, 10),
                          ha='center')
            
            # Thêm thông tin đề xuất
            recommendation = forecasts.get('trading_recommendation', {})
            action = recommendation.get('action', 'hold')
            confidence = recommendation.get('confidence', 0)
            
            action_color = 'green' if action == 'buy' else 'red' if action == 'sell' else 'gray'
            
            title = f"Dự báo giá {symbol} - Đề xuất: {action.upper()} (Độ tin cậy: {confidence:.2f})"
            plt.title(title)
            
            # Thêm stop loss và take profit nếu có
            if action != 'hold':
                stop_loss = recommendation.get('stop_loss', 0)
                take_profit = recommendation.get('take_profit', 0)
                
                if stop_loss > 0:
                    plt.axhline(y=stop_loss, color='red', linestyle='--', alpha=0.5, label='Stop Loss')
                    
                if take_profit > 0:
                    plt.axhline(y=take_profit, color='green', linestyle='--', alpha=0.5, label='Take Profit')
                    
            plt.xlabel('Ngày')
            plt.ylabel('Giá')
            plt.grid(True)
            plt.legend()
            
            # Lưu biểu đồ
            os.makedirs('forecast_charts', exist_ok=True)
            chart_path = f"forecast_charts/{symbol}_forecast.png"
            plt.savefig(chart_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ dự báo: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ dự báo cho {symbol}: {str(e)}")
            return None

def main():
    """Hàm chính để test module"""
    try:
        # Khởi tạo Market Forecast
        forecaster = MarketForecast()
        
        # Dự báo cho BTC
        print("Đang dự báo cho BTCUSDT...")
        btc_forecast = forecaster.prepare_all_forecasts('BTCUSDT', '1h')
        
        if btc_forecast:
            print("\nĐề xuất giao dịch BTC:")
            recommendation = btc_forecast.get('trading_recommendation', {})
            print(f"Hành động: {recommendation.get('action', 'hold').upper()}")
            print(f"Độ tin cậy: {recommendation.get('confidence', 0):.2f}")
            print(f"Lý do: {recommendation.get('reason', '')}")
            
            if recommendation.get('action') != 'hold':
                print(f"Giá vào lệnh: {recommendation.get('entry_price', 0):.2f}")
                print(f"Stop Loss: {recommendation.get('stop_loss', 0):.2f}")
                print(f"Take Profit: {recommendation.get('take_profit', 0):.2f}")
                print(f"Risk/Reward: {recommendation.get('risk_reward_ratio', 0):.2f}")
            
            # Tạo biểu đồ
            chart_path = forecaster.create_forecast_chart('BTCUSDT')
            if chart_path:
                print(f"\nBiểu đồ dự báo: {chart_path}")
        
        # Dự báo cho ETH
        print("\nĐang dự báo cho ETHUSDT...")
        eth_forecast = forecaster.prepare_all_forecasts('ETHUSDT', '1h')
        
        if eth_forecast:
            print("\nĐề xuất giao dịch ETH:")
            recommendation = eth_forecast.get('trading_recommendation', {})
            print(f"Hành động: {recommendation.get('action', 'hold').upper()}")
            print(f"Độ tin cậy: {recommendation.get('confidence', 0):.2f}")
            print(f"Lý do: {recommendation.get('reason', '')}")
            
            # Tạo biểu đồ
            chart_path = forecaster.create_forecast_chart('ETHUSDT')
            if chart_path:
                print(f"\nBiểu đồ dự báo: {chart_path}")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy Market Forecast: {str(e)}")

if __name__ == "__main__":
    main()