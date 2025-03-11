#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module tính toán tính năng cho mô hình ML (ML Feature Calculator)

Module này cung cấp các hàm để tính toán 31 tính năng cần thiết cho huấn luyện 
và áp dụng mô hình máy học trong giao dịch tiền điện tử.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MLFeatureCalculator:
    """Lớp tính toán tính năng cho mô hình ML"""
    
    def __init__(self, features_list: List[str] = None):
        """
        Khởi tạo bộ tính toán tính năng ML
        
        Args:
            features_list (List[str], optional): Danh sách tính năng cần tính toán
        """
        if features_list is None:
            # 31 tính năng mặc định từ features.json
            self.features_list = [
                "open", "high", "low", "close", "volume",
                "sma5", "sma10", "sma20", "sma50", "sma100",
                "ema5", "ema10", "ema20", "ema50",
                "rsi", "macd", "macd_signal", "macd_hist",
                "bb_middle", "bb_upper", "bb_lower",
                "price_sma20_ratio", "price_sma50_ratio",
                "volatility", "daily_return", "weekly_return",
                "volume_sma5", "volume_ratio",
                "direction_1d", "direction_3d", "direction_5d"
            ]
        else:
            self.features_list = features_list
            
        logger.info(f"Đã khởi tạo MLFeatureCalculator với {len(self.features_list)} tính năng")
    
    def calculate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán tất cả các tính năng cho dữ liệu đầu vào
        
        Args:
            df (pd.DataFrame): DataFrame gốc chứa dữ liệu OHLCV
            
        Returns:
            pd.DataFrame: DataFrame với đầy đủ các tính năng đã tính toán
        """
        if df.empty:
            logger.warning("DataFrame đầu vào rỗng, không thể tính toán tính năng")
            return df
            
        # Đảm bảo df có các cột cần thiết
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"Thiếu cột dữ liệu, cần các cột: {required_columns}")
            return df
            
        # Tạo bản sao để tránh sửa đổi dữ liệu gốc
        df_features = df.copy()
        
        # Tính toán SMA (Simple Moving Average)
        if any(f in self.features_list for f in ["sma5", "sma10", "sma20", "sma50", "sma100"]):
            if "sma5" in self.features_list:
                df_features['sma5'] = df_features['close'].rolling(window=5).mean()
            if "sma10" in self.features_list:
                df_features['sma10'] = df_features['close'].rolling(window=10).mean()
            if "sma20" in self.features_list:
                df_features['sma20'] = df_features['close'].rolling(window=20).mean()
            if "sma50" in self.features_list:
                df_features['sma50'] = df_features['close'].rolling(window=50).mean()
            if "sma100" in self.features_list:
                df_features['sma100'] = df_features['close'].rolling(window=100).mean()
        
        # Tính toán EMA (Exponential Moving Average)
        if any(f in self.features_list for f in ["ema5", "ema10", "ema20", "ema50"]):
            if "ema5" in self.features_list:
                df_features['ema5'] = df_features['close'].ewm(span=5, adjust=False).mean()
            if "ema10" in self.features_list:
                df_features['ema10'] = df_features['close'].ewm(span=10, adjust=False).mean()
            if "ema20" in self.features_list:
                df_features['ema20'] = df_features['close'].ewm(span=20, adjust=False).mean()
            if "ema50" in self.features_list:
                df_features['ema50'] = df_features['close'].ewm(span=50, adjust=False).mean()
        
        # Tính toán RSI (Relative Strength Index)
        if "rsi" in self.features_list:
            df_features['rsi'] = self._calculate_rsi(df_features['close'], period=14)
        
        # Tính toán MACD (Moving Average Convergence Divergence)
        if any(f in self.features_list for f in ["macd", "macd_signal", "macd_hist"]):
            # Tính MACD
            ema_fast = df_features['close'].ewm(span=12, adjust=False).mean()
            ema_slow = df_features['close'].ewm(span=26, adjust=False).mean()
            df_features['macd'] = ema_fast - ema_slow
            df_features['macd_signal'] = df_features['macd'].ewm(span=9, adjust=False).mean()
            df_features['macd_hist'] = df_features['macd'] - df_features['macd_signal']
        
        # Tính toán Bollinger Bands
        if any(f in self.features_list for f in ["bb_middle", "bb_upper", "bb_lower"]):
            period = 20
            df_features['bb_middle'] = df_features['close'].rolling(window=period).mean()
            std_dev = df_features['close'].rolling(window=period).std()
            df_features['bb_upper'] = df_features['bb_middle'] + (std_dev * 2)
            df_features['bb_lower'] = df_features['bb_middle'] - (std_dev * 2)
            
            # Thêm độ rộng của Bollinger Bands
            df_features['bb_width'] = (df_features['bb_upper'] - df_features['bb_lower']) / df_features['bb_middle']
        
        # Tính toán các tỷ lệ giá/SMA
        if any(f in self.features_list for f in ["price_sma20_ratio", "price_sma50_ratio"]):
            if "price_sma20_ratio" in self.features_list and "sma20" in df_features.columns:
                df_features['price_sma20_ratio'] = df_features['close'] / df_features['sma20']
            if "price_sma50_ratio" in self.features_list and "sma50" in df_features.columns:
                df_features['price_sma50_ratio'] = df_features['close'] / df_features['sma50']
        
        # Tính toán các chỉ báo khối lượng
        if any(f in self.features_list for f in ["volume_sma5", "volume_ratio"]):
            if "volume_sma5" in self.features_list:
                df_features['volume_sma5'] = df_features['volume'].rolling(window=5).mean()
            if "volume_ratio" in self.features_list and "volume_sma5" in df_features.columns:
                df_features['volume_ratio'] = df_features['volume'] / df_features['volume_sma5']
        
        # Tính toán biến động và lợi nhuận
        if any(f in self.features_list for f in ["volatility", "daily_return", "weekly_return"]):
            if "volatility" in self.features_list:
                df_features['volatility'] = df_features['close'].pct_change().rolling(window=20).std()
            if "daily_return" in self.features_list:
                df_features['daily_return'] = df_features['close'].pct_change(1)
            if "weekly_return" in self.features_list:
                df_features['weekly_return'] = df_features['close'].pct_change(7)
        
        # Tính toán các chỉ báo hướng giá (direction indicators)
        # Đây là các tính năng dùng cho huấn luyện, cần dữ liệu trong tương lai
        if any(f in self.features_list for f in ["direction_1d", "direction_3d", "direction_5d"]):
            # Đối với khung thời gian 1h
            hours_in_day = 24
            
            if "direction_1d" in self.features_list:
                # Giá 1 ngày trong tương lai (shift -24 cho 1h candlesticks)
                future_1d = df_features['close'].shift(-hours_in_day)
                df_features['direction_1d'] = np.where(future_1d > df_features['close'], 1, 0)
                # Nếu có NaN (ở cuối dữ liệu), thay thế bằng giá trị dự đoán từ các chỉ báo
                if df_features['direction_1d'].isna().any():
                    # Dự đoán dựa trên RSI và xu hướng giá
                    if 'rsi' in df_features.columns and 'ema20' in df_features.columns:
                        bullish_pred = (df_features['rsi'] < 30) | (df_features['close'] > df_features['ema20'])
                        df_features.loc[df_features['direction_1d'].isna(), 'direction_1d'] = bullish_pred.astype(int)
                    else:
                        # Mặc định là 0 (không có xu hướng)
                        df_features.loc[df_features['direction_1d'].isna(), 'direction_1d'] = 0
            
            if "direction_3d" in self.features_list:
                # Giá 3 ngày trong tương lai
                future_3d = df_features['close'].shift(-hours_in_day * 3)
                df_features['direction_3d'] = np.where(future_3d > df_features['close'], 1, 0)
                # Xử lý NaN
                if df_features['direction_3d'].isna().any():
                    if 'rsi' in df_features.columns and 'ema50' in df_features.columns:
                        bullish_pred = (df_features['rsi'] < 30) | (df_features['close'] > df_features['ema50'])
                        df_features.loc[df_features['direction_3d'].isna(), 'direction_3d'] = bullish_pred.astype(int)
                    else:
                        df_features.loc[df_features['direction_3d'].isna(), 'direction_3d'] = 0
            
            if "direction_5d" in self.features_list:
                # Giá 5 ngày trong tương lai
                future_5d = df_features['close'].shift(-hours_in_day * 5)
                df_features['direction_5d'] = np.where(future_5d > df_features['close'], 1, 0)
                # Xử lý NaN
                if df_features['direction_5d'].isna().any():
                    if 'rsi' in df_features.columns and 'sma100' in df_features.columns:
                        bullish_pred = (df_features['rsi'] < 25) | (df_features['close'] > df_features['sma100'])
                        df_features.loc[df_features['direction_5d'].isna(), 'direction_5d'] = bullish_pred.astype(int)
                    else:
                        df_features.loc[df_features['direction_5d'].isna(), 'direction_5d'] = 0
        
        return df_features
    
    def calculate_live_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán các tính năng cho dữ liệu thời gian thực (không có direction indicators)
        
        Args:
            df (pd.DataFrame): DataFrame gốc chứa dữ liệu OHLCV
            
        Returns:
            pd.DataFrame: DataFrame với đầy đủ các tính năng đã tính toán
        """
        # Lọc các tính năng dự đoán tương lai ra khỏi danh sách
        live_features = [f for f in self.features_list if not f.startswith("direction_")]
        
        # Tạo bộ tính năng tạm thời với chỉ các tính năng trực tiếp
        temp_calculator = MLFeatureCalculator(features_list=live_features)
        
        # Tính toán các tính năng
        return temp_calculator.calculate_all_features(df)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Tính RSI (Relative Strength Index)
        
        Args:
            prices (pd.Series): Chuỗi giá
            period (int): Chu kỳ RSI
            
        Returns:
            pd.Series: Chuỗi RSI
        """
        # Tính biến động giá
        deltas = prices.diff()
        
        # Tạo chuỗi gain và loss
        gain = deltas.copy()
        loss = deltas.copy()
        gain[gain < 0] = 0
        loss[loss > 0] = 0
        loss = -loss  # Chuyển đổi thành giá trị dương
        
        # Tính giá trị trung bình
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Tính RS và RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def save_features_json(self, filename: str, info: Dict = None) -> None:
        """
        Lưu danh sách tính năng vào file JSON
        
        Args:
            filename (str): Tên file để lưu
            info (Dict, optional): Thông tin bổ sung về mô hình
        """
        features_dict = {
            "features": self.features_list,
            "creation_date": datetime.now().isoformat(),
            "info": info or {}
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(features_dict, f, indent=2)
            logger.info(f"Đã lưu danh sách tính năng vào {filename}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu danh sách tính năng: {str(e)}")
    
    @staticmethod
    def load_features_json(filename: str) -> Dict:
        """
        Đọc danh sách tính năng từ file JSON
        
        Args:
            filename (str): Tên file để đọc
            
        Returns:
            Dict: Dictionary chứa thông tin tính năng
        """
        try:
            with open(filename, 'r') as f:
                features_dict = json.load(f)
            logger.info(f"Đã đọc danh sách tính năng từ {filename}")
            return features_dict
        except Exception as e:
            logger.error(f"Lỗi khi đọc danh sách tính năng: {str(e)}")
            return {"features": [], "creation_date": "", "info": {}}
    
    @staticmethod
    def get_required_features_for_model(model_name: str) -> List[str]:
        """
        Lấy danh sách tính năng cần thiết cho một mô hình ML
        
        Args:
            model_name (str): Tên mô hình ML
            
        Returns:
            List[str]: Danh sách tính năng
        """
        # Thử đọc từ file features.json tương ứng
        features_file = f"{model_name}_features.json"
        if os.path.exists(features_file):
            features_dict = MLFeatureCalculator.load_features_json(features_file)
            return features_dict.get("features", [])
        
        # Nếu không tìm thấy file, trả về danh sách tính năng mặc định
        logger.warning(f"Không tìm thấy file {features_file}, sử dụng danh sách tính năng mặc định")
        return MLFeatureCalculator().features_list
    
    def align_features_with_model(self, df: pd.DataFrame, model_features: List[str]) -> pd.DataFrame:
        """
        Căn chỉnh tính năng trong DataFrame phù hợp với mô hình
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu
            model_features (List[str]): Danh sách tính năng mô hình yêu cầu
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng đã căn chỉnh
        """
        # Đảm bảo tất cả các tính năng cần thiết đều có trong df
        for feature in model_features:
            if feature not in df.columns:
                logger.warning(f"Tính năng {feature} không có trong DataFrame, thử tính toán...")
                
                # Đặt tạm thời tất cả các tính năng vào danh sách cần tính
                temp_calculator = MLFeatureCalculator(features_list=model_features)
                df = temp_calculator.calculate_all_features(df)
                break  # Tính toán tất cả cùng một lúc
        
        # Kiểm tra lại sau khi tính toán
        missing_features = [f for f in model_features if f not in df.columns]
        if missing_features:
            logger.error(f"Không thể tính toán các tính năng: {missing_features}")
        
        return df


# Hàm để test functionality
def test_feature_calculator():
    """Test MLFeatureCalculator với dữ liệu mẫu"""
    # Tạo dữ liệu mẫu
    dates = pd.date_range(start='2023-01-01', periods=200, freq='H')
    np.random.seed(42)
    data = {
        'timestamp': dates,
        'open': np.random.normal(100, 10, 200),
        'high': np.random.normal(105, 10, 200),
        'low': np.random.normal(95, 10, 200),
        'close': np.random.normal(100, 10, 200),
        'volume': np.random.normal(1000, 200, 200)
    }
    
    # Ensure high > low and high > open/close
    for i in range(len(data['high'])):
        data['high'][i] = max(data['high'][i], data['open'][i], data['close'][i], data['low'][i] + 1)
        data['low'][i] = min(data['low'][i], data['open'][i], data['close'][i])
    
    df = pd.DataFrame(data)
    
    # Tạo bộ tính toán tính năng
    calculator = MLFeatureCalculator()
    
    # Tính toán tất cả các tính năng
    df_features = calculator.calculate_all_features(df)
    
    # Hiển thị thông tin
    print(f"Số cột ban đầu: {len(df.columns)}")
    print(f"Số cột sau khi tính tính năng: {len(df_features.columns)}")
    print("\nDanh sách tính năng:")
    for col in df_features.columns:
        print(f"- {col}")
    
    # Kiểm tra các tính năng đã được tính toán
    for feature in calculator.features_list:
        if feature not in df_features.columns:
            print(f"THIẾU: {feature}")
    
    return df_features


if __name__ == "__main__":
    # Test tính năng khi chạy trực tiếp
    result_df = test_feature_calculator()
    print("\nĐã tính toán xong tất cả tính năng!")