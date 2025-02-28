"""
Công cụ tạo tính năng đơn giản cho mô hình học máy trong giao dịch.

Module này cung cấp các hàm để tạo ra các tính năng từ dữ liệu giá 
mà không sử dụng thư viện ngoài như talib.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime

# Cấu hình logging
logger = logging.getLogger('simple_feature_engineering')

class SimpleFeatureEngineering:
    """
    Lớp cung cấp các phương thức tạo tính năng đơn giản cho mô hình học máy.
    """
    
    def __init__(self):
        """
        Khởi tạo với cài đặt mặc định.
        """
        pass
        
    def add_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm tất cả các tính năng vào DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame gốc với dữ liệu OHLCV
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng bổ sung
        """
        # Kiểm tra dữ liệu
        if df is None or df.empty:
            logger.error("DataFrame trống hoặc None")
            return df
            
        # Tạo bản sao để tránh thay đổi DataFrame gốc
        df_features = df.copy()
        
        # Đảm bảo có các cột cần thiết
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df_features.columns]
        
        if missing_columns:
            logger.error(f"Thiếu các cột cần thiết trong dữ liệu: {missing_columns}")
            return df
        
        try:
            # Thêm các tính năng cơ bản
            df_features = self.add_basic_features(df_features)
            
            # Thêm các tính năng biến động
            df_features = self.add_volatility_features(df_features)
            
            # Thêm các tính năng khối lượng
            df_features = self.add_volume_features(df_features)
            
            # Thêm các tính năng về xu hướng
            df_features = self.add_trend_features(df_features)
            
            # Đảm bảo không có dữ liệu NaN
            df_features = self.handle_missing_values(df_features)
            
            return df_features
            
        except Exception as e:
            logger.error(f"Lỗi khi thêm tính năng: {str(e)}")
            return df
    
    def add_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng cơ bản.
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng cơ bản
        """
        df_result = df.copy()
        
        # Các tính năng về trung bình động (MAs)
        for period in [5, 10, 20, 50, 100, 200]:
            # Đơn giản hoá: chỉ tính SMA, không dùng EMA
            df_result[f'SMA_{period}'] = df_result['close'].rolling(window=period).mean()
        
        # Bollinger Bands - tính thủ công
        df_result['BB_middle'] = df_result['close'].rolling(window=20).mean()
        df_result['BB_std'] = df_result['close'].rolling(window=20).std()
        df_result['BB_upper'] = df_result['BB_middle'] + 2 * df_result['BB_std']
        df_result['BB_lower'] = df_result['BB_middle'] - 2 * df_result['BB_std']
        
        # Độ rộng của dải Bollinger Bands
        df_result['BB_Width'] = (df_result['BB_upper'] - df_result['BB_lower']) / df_result['BB_middle']
        
        # Phần trăm B - vị trí của giá trong dải Bollinger
        df_result['BB_B'] = (df_result['close'] - df_result['BB_lower']) / (df_result['BB_upper'] - df_result['BB_lower'])
        
        # RSI tính thủ công
        delta = df_result['close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        # RSI calculation
        rs = avg_gain / avg_loss.replace(0, 1e-10)  # Tránh chia cho 0
        df_result['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD tính thủ công
        df_result['EMA_12'] = df_result['close'].ewm(span=12, adjust=False).mean()
        df_result['EMA_26'] = df_result['close'].ewm(span=26, adjust=False).mean()
        df_result['MACD'] = df_result['EMA_12'] - df_result['EMA_26']
        df_result['MACD_Signal'] = df_result['MACD'].ewm(span=9, adjust=False).mean()
        df_result['MACD_Hist'] = df_result['MACD'] - df_result['MACD_Signal']
        
        # ATR - Average True Range (tính thủ công)
        high_low = df_result['high'] - df_result['low']
        high_close = (df_result['high'] - df_result['close'].shift()).abs()
        low_close = (df_result['low'] - df_result['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df_result['ATR'] = tr.rolling(window=14).mean()
        
        # Price percent change
        df_result['Price_Pct_Change_1'] = df_result['close'].pct_change(1) * 100
        df_result['Price_Pct_Change_5'] = df_result['close'].pct_change(5) * 100
        
        return df_result
    
    def add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng về biến động.
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng về biến động
        """
        df_result = df.copy()
        
        # Phần trăm thay đổi so với phiên trước
        df_result['Price_Change'] = df_result['close'].pct_change()
        
        # Biến động giá theo nhiều khung thời gian
        for period in [5, 10, 20, 50]:
            # Độ lệch chuẩn của giá
            df_result[f'Price_Std_{period}'] = df_result['close'].rolling(period).std() / df_result['close']
            
            # Biên độ dao động của giá (High-Low)
            df_result[f'Price_Range_{period}'] = (
                df_result['high'].rolling(period).max() - df_result['low'].rolling(period).min()
            ) / df_result['close']
        
        # Biến động của biến động (std của returns)
        df_result['Returns_Volatility'] = df_result['Price_Change'].rolling(20).std()
        
        # Biến động tương đối so với thị trường
        df_result['Rel_Volatility'] = df_result['Returns_Volatility'] / df_result['Returns_Volatility'].mean()
        
        # Hệ số biến thiên (CV) - chuẩn hóa biến động theo giá
        df_result['CV'] = df_result['Returns_Volatility'] / df_result['close'].rolling(20).mean()
        
        # Chỉ số biến động tiêu chuẩn
        df_result['Price_Volatility'] = df_result['close'].rolling(20).std() / df_result['close']
        
        # Biến động điều chỉnh theo khối lượng
        df_result['Vol_Adj_Range'] = (df_result['high'] - df_result['low']) * df_result['volume']
        
        return df_result
    
    def add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng liên quan đến khối lượng.
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng khối lượng
        """
        df_result = df.copy()
        
        # Khối lượng tương đối
        df_result['Volume_Ratio'] = df_result['volume'] / df_result['volume'].rolling(20).mean()
        
        # Tốc độ thay đổi khối lượng
        df_result['Volume_ROC'] = df_result['volume'].pct_change(5)  # 5-period rate of change
        
        # Xu hướng khối lượng
        df_result['Volume_Trend'] = df_result['Volume_ROC'].rolling(window=5).mean()
        df_result['Volume_Trend'] = df_result['Volume_Trend'].clip(-1, 1)  # Clip to range -1 to 1
        
        # Khối lượng điều chỉnh theo giá
        df_result['Price_Volume_Impact'] = df_result['Price_Change'] * df_result['Volume_Ratio']
        
        # OBV - On Balance Volume (tính thủ công)
        df_result['OBV'] = (np.sign(df_result['close'].diff()) * df_result['volume']).fillna(0).cumsum()
        
        # Chaikin A/D Line (tính thủ công)
        mf_multiplier = ((df_result['close'] - df_result['low']) - (df_result['high'] - df_result['close'])) / (df_result['high'] - df_result['low'])
        mf_multiplier = mf_multiplier.replace([np.inf, -np.inf], 0)
        df_result['ADL'] = (mf_multiplier * df_result['volume']).cumsum()
        
        # Khối lượng khác thường
        df_result['Volume_Surprise'] = (df_result['volume'] - df_result['volume'].rolling(20).mean()) / df_result['volume'].rolling(20).std()
        
        # Xác nhận khối lượng
        df_result['Up_Volume'] = np.where(df_result['close'] > df_result['close'].shift(1), df_result['volume'], 0)
        df_result['Down_Volume'] = np.where(df_result['close'] < df_result['close'].shift(1), df_result['volume'], 0)
        
        # Tỷ lệ khối lượng tăng/giảm
        df_result['Up_Down_Ratio'] = df_result['Up_Volume'].rolling(10).sum() / df_result['Down_Volume'].rolling(10).sum().replace(0, 1)
        
        return df_result
    
    def add_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng về xu hướng.
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng xu hướng
        """
        df_result = df.copy()
        
        # Calculate EMA crossovers (9 and 21)
        df_result['EMA_9'] = df_result['close'].ewm(span=9, adjust=False).mean()
        df_result['EMA_21'] = df_result['close'].ewm(span=21, adjust=False).mean()
        df_result['EMA_50'] = df_result['close'].ewm(span=50, adjust=False).mean()
        df_result['EMA_200'] = df_result['close'].ewm(span=200, adjust=False).mean()
        
        # Crossover signals (1 for bullish, -1 for bearish, 0 for no crossover)
        df_result['EMA_Cross_9_21'] = np.where(df_result['EMA_9'] > df_result['EMA_21'], 1, -1)
        df_result['EMA_Cross_21_50'] = np.where(df_result['EMA_21'] > df_result['EMA_50'], 1, -1)
        df_result['EMA_Cross_50_200'] = np.where(df_result['EMA_50'] > df_result['EMA_200'], 1, -1)
        
        # Trends based on EMAs crossing
        for short_p, long_p in [(5, 20), (9, 21), (20, 50), (50, 200)]:
            # Tính EMA nếu chưa có
            if f'EMA_{short_p}' not in df_result.columns:
                df_result[f'EMA_{short_p}'] = df_result['close'].ewm(span=short_p, adjust=False).mean()
            if f'EMA_{long_p}' not in df_result.columns:
                df_result[f'EMA_{long_p}'] = df_result['close'].ewm(span=long_p, adjust=False).mean()
                
            short_col = f'EMA_{short_p}'
            long_col = f'EMA_{long_p}'
            
            # Create a trend indicator (1 for uptrend, -1 for downtrend, 0 for neutral)
            df_result[f'EMA_{short_p}_{long_p}_Cross'] = np.where(
                df_result[short_col] > df_result[long_col], 1, 
                np.where(df_result[short_col] < df_result[long_col], -1, 0)
            )
            
            # Measure trend strength based on the percentage difference
            df_result[f'EMA_{short_p}_{long_p}_Strength'] = (
                (df_result[short_col] - df_result[long_col]) / df_result[long_col]
            )
        
        # Tạo tính năng "EMA_Trend_Strength" dựa trên tất cả các cặp EMA
        df_result['EMA_Trend_Strength'] = (
            df_result['EMA_5_20_Strength'] + 
            df_result['EMA_9_21_Strength'] + 
            df_result['EMA_20_50_Strength'] + 
            df_result['EMA_50_200_Strength']
        ) / 4.0
        
        # ADX (Average Directional Index) cho độ mạnh xu hướng - phiên bản đơn giản
        # Sử dụng độ lệch giữa các đường trung bình động làm đại diện cho ADX
        df_result['ADX_Proxy'] = abs(df_result['EMA_Trend_Strength']) * 100  # scale to 0-100 range
        df_result['ADX'] = df_result['ADX_Proxy'].rolling(window=14).mean()  # smooth it out
        
        # Trend direction (-1 for downtrend, 1 for uptrend)
        df_result['Trend_Direction'] = np.where(df_result['EMA_Trend_Strength'] > 0, 1, -1)
        
        # Trend Strength: combining EMA trend strength
        df_result['Trend_Strength'] = df_result['EMA_Trend_Strength'] * df_result['Trend_Direction']
        
        return df_result
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Xử lý các giá trị thiếu trong DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame cần xử lý
            
        Returns:
            pd.DataFrame: DataFrame đã xử lý các giá trị thiếu
        """
        # Tạo bản sao để tránh thay đổi dataframe gốc
        df_result = df.copy()
        
        # Điền các giá trị NA bằng phương pháp ffill rồi đến bfill
        df_result = df_result.ffill().bfill()
        
        # Thay thế các giá trị vô cùng bằng NaN, sau đó điền bằng 0
        df_result = df_result.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # Kiểm tra xem còn giá trị NaN nào không
        na_cols = df_result.columns[df_result.isna().any()].tolist()
        if na_cols:
            logger.warning(f"Vẫn còn các cột có giá trị NaN: {na_cols}")
            # Lấp đầy các giá trị NA còn lại bằng 0
            df_result = df_result.fillna(0)
        
        return df_result