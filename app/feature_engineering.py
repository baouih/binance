"""
Công cụ tạo tính năng nâng cao cho mô hình học máy trong giao dịch.

Module này cung cấp các hàm để tạo ra nhiều tính năng kỹ thuật phức tạp từ dữ liệu giá.
Các tính năng này được thiết kế để tăng cường khả năng dự đoán của mô hình học máy.
"""

import logging
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime
# Thay thế thư viện talib bằng cách triển khai trực tiếp các hàm tính toán chỉ báo kỹ thuật
# import talib

# Cấu hình logging
logger = logging.getLogger('feature_engineering')

class FeatureEngineering:
    """
    Lớp cung cấp các phương thức tạo tính năng nâng cao cho mô hình học máy.
    """
    
    def __init__(self, use_all_features=False):
        """
        Khởi tạo với cài đặt sử dụng tất cả các tính năng hay chỉ dùng các tính năng cốt lõi.
        
        Args:
            use_all_features (bool): Nếu True, sẽ tạo tất cả các tính năng có thể (nặng về tính toán)
        """
        self.use_all_features = use_all_features
        
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
            
            # Thêm các tính năng động lực
            df_features = self.add_momentum_features(df_features)
            
            # Thêm các tính năng về mẫu hình giá
            df_features = self.add_pattern_features(df_features)
            
            # Thêm các tính năng theo thời gian
            df_features = self.add_temporal_features(df_features)
            
            # Thêm các tính năng về sự hỗ trợ/kháng cự
            df_features = self.add_support_resistance_features(df_features)
            
            # Nếu cần tất cả các tính năng, thêm các tính năng nâng cao (nặng về tính toán)
            if self.use_all_features:
                # Thêm các tính năng tùy chỉnh nâng cao
                df_features = self.add_advanced_features(df_features)
                
                # Thêm các tính năng chu kỳ
                df_features = self.add_cycle_features(df_features)
                
                # Thêm các tính năng thống kê
                df_features = self.add_statistical_features(df_features)
            
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
            df_result[f'SMA_{period}'] = talib.SMA(df_result['close'].values, timeperiod=period)
            df_result[f'EMA_{period}'] = talib.EMA(df_result['close'].values, timeperiod=period)
            
        # Bollinger Bands
        df_result['BB_upper'], df_result['BB_middle'], df_result['BB_lower'] = talib.BBANDS(
            df_result['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )
        
        # Độ rộng của dải Bollinger Bands
        df_result['BB_Width'] = (df_result['BB_upper'] - df_result['BB_lower']) / df_result['BB_middle']
        
        # Phần trăm B - vị trí của giá trong dải Bollinger
        df_result['BB_B'] = (df_result['close'] - df_result['BB_lower']) / (df_result['BB_upper'] - df_result['BB_lower'])
        
        # RSI
        df_result['RSI'] = talib.RSI(df_result['close'].values, timeperiod=14)
        
        # MACD
        df_result['MACD'], df_result['MACD_Signal'], df_result['MACD_Hist'] = talib.MACD(
            df_result['close'].values, fastperiod=12, slowperiod=26, signalperiod=9
        )
        
        # ATR - Average True Range
        df_result['ATR'] = talib.ATR(
            df_result['high'].values, df_result['low'].values, df_result['close'].values, 
            timeperiod=14
        )
        
        # ADX - Average Directional Index
        df_result['ADX'] = talib.ADX(
            df_result['high'].values, df_result['low'].values, df_result['close'].values, 
            timeperiod=14
        )
        
        # Parabolic SAR
        df_result['SAR'] = talib.SAR(
            df_result['high'].values, df_result['low'].values, 
            acceleration=0.02, maximum=0.2
        )
        
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
        
        # CHOP - chỉ báo Choppiness Index (thị trường lình xình hay có xu hướng)
        period = 14
        atr1 = talib.MAX(df_result['high'].rolling(period).max(), df_result['close'].shift(period))
        atr2 = talib.MIN(df_result['low'].rolling(period).min(), df_result['close'].shift(period))
        df_result['CHOP'] = 100 * np.log10(
            df_result['ATR'].rolling(period).sum() / (atr1 - atr2)
        ) / np.log10(period)
        
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
        
        # OBV - On Balance Volume
        df_result['OBV'] = (np.sign(df_result['close'].diff()) * df_result['volume']).fillna(0).cumsum()
        
        # Chaikin A/D Line
        mf_multiplier = ((df_result['close'] - df_result['low']) - (df_result['high'] - df_result['close'])) / (df_result['high'] - df_result['low'])
        mf_multiplier = mf_multiplier.replace([np.inf, -np.inf], 0)
        df_result['ADL'] = (mf_multiplier * df_result['volume']).cumsum()
        
        # Chaikin Oscillator
        df_result['Chaikin_Osc'] = talib.EMA(df_result['ADL'].values, timeperiod=3) - talib.EMA(df_result['ADL'].values, timeperiod=10)
        
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
        
        # Trends based on EMAs crossing
        for short_p, long_p in [(5, 20), (9, 21), (20, 50), (50, 200)]:
            short_col = f'EMA_{short_p}'
            long_col = f'EMA_{long_p}'
            
            if short_col in df_result.columns and long_col in df_result.columns:
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
        
        # Supertrend indicator
        atr_multiplier = 3.0
        hl2 = (df_result['high'] + df_result['low']) / 2
        
        # Upper band = hl2 + (multiplier * ATR)
        df_result['ST_Upper'] = hl2 + (atr_multiplier * df_result['ATR'])
        
        # Lower band = hl2 - (multiplier * ATR)
        df_result['ST_Lower'] = hl2 - (atr_multiplier * df_result['ATR'])
        
        # Initialize Supertrend
        df_result['ST'] = 0.0
        df_result['ST_Direction'] = 0  # 1 for uptrend, -1 for downtrend
        
        # Calculate Supertrend with vectorized operations when possible
        for i in range(1, len(df_result)):
            if (df_result['close'].iloc[i-1] <= df_result['ST_Upper'].iloc[i-1]):
                df_result.loc[df_result.index[i], 'ST_Upper'] = min(
                    df_result['ST_Upper'].iloc[i],
                    df_result['ST_Upper'].iloc[i-1]
                )
            else:
                df_result.loc[df_result.index[i], 'ST_Upper'] = df_result['ST_Upper'].iloc[i]
                
            if (df_result['close'].iloc[i-1] >= df_result['ST_Lower'].iloc[i-1]):
                df_result.loc[df_result.index[i], 'ST_Lower'] = max(
                    df_result['ST_Lower'].iloc[i],
                    df_result['ST_Lower'].iloc[i-1]
                )
            else:
                df_result.loc[df_result.index[i], 'ST_Lower'] = df_result['ST_Lower'].iloc[i]
                
        # Set the trend direction
        df_result['ST_Direction'] = np.where(
            df_result['close'] > df_result['ST_Upper'].shift(1), 1,
            np.where(df_result['close'] < df_result['ST_Lower'].shift(1), -1,
                    df_result['ST_Direction'].shift(1))
        )
        
        # Fill first value with 0
        df_result.loc[df_result.index[0], 'ST_Direction'] = 0
        
        # Supertrend value
        df_result['ST'] = np.where(
            df_result['ST_Direction'] == 1,
            df_result['ST_Lower'],
            df_result['ST_Upper']
        )
        
        # Độ mạnh của xu hướng từ SuperTrend
        df_result['ST_Strength'] = abs(df_result['close'] - df_result['ST']) / df_result['close']
        
        # ADX, DI+, DI- từ TA-Lib
        df_result['DI_Plus'] = talib.PLUS_DI(df_result['high'].values, df_result['low'].values, df_result['close'].values, timeperiod=14)
        df_result['DI_Minus'] = talib.MINUS_DI(df_result['high'].values, df_result['low'].values, df_result['close'].values, timeperiod=14)
        
        # Trend Strength: Tổng hợp từ nhiều chỉ báo xu hướng
        df_result['Trend_Strength'] = (
            df_result['EMA_Trend_Strength'] * 0.4 +
            df_result['ST_Direction'] * df_result['ST_Strength'] * 0.3 +
            (df_result['DI_Plus'] - df_result['DI_Minus']) / (df_result['DI_Plus'] + df_result['DI_Minus']) * 0.3
        )
        
        return df_result
    
    def add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng về động lực (momentum).
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng động lực
        """
        df_result = df.copy()
        
        # Rate of Change
        for period in [5, 10, 20, 60]:
            df_result[f'ROC_{period}'] = talib.ROC(df_result['close'].values, timeperiod=period)
        
        # Momentum
        df_result['Momentum'] = df_result['close'] - df_result['close'].shift(10)
        
        # Chỉ số Stochastic
        df_result['Stoch_K'], df_result['Stoch_D'] = talib.STOCH(
            df_result['high'].values, df_result['low'].values, df_result['close'].values,
            fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0
        )
        
        # CCI - Commodity Channel Index
        df_result['CCI'] = talib.CCI(
            df_result['high'].values, df_result['low'].values, df_result['close'].values,
            timeperiod=20
        )
        
        # Williams %R
        df_result['Williams_R'] = talib.WILLR(
            df_result['high'].values, df_result['low'].values, df_result['close'].values,
            timeperiod=14
        )
        
        # Tổng hợp Momentum
        df_result['Momentum_Summary'] = (
            df_result['ROC_10'] * 0.2 +
            df_result['Stoch_K'] / 100 * 0.3 +
            df_result['RSI'] / 100 * 0.3 +
            df_result['CCI'] / 200 * 0.2
        )
        
        # Momentum Oscillator từ hai EMA khác nhau
        df_result['Momentum_Osc'] = (df_result['EMA_5'] - df_result['EMA_20']) / df_result['EMA_20'] * 100
        
        # Thuộc tính momentum chính
        df_result['Price_Momentum'] = df_result['ROC_10']
        
        return df_result
    
    def add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng về mẫu hình giá (price patterns).
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng về mẫu hình giá
        """
        df_result = df.copy()
        
        # Hammer pattern 
        df_result['Hammer'] = talib.CDLHAMMER(
            df_result['open'].values, df_result['high'].values,
            df_result['low'].values, df_result['close'].values
        )
        
        # Engulfing pattern
        df_result['Engulfing'] = talib.CDLENGULFING(
            df_result['open'].values, df_result['high'].values,
            df_result['low'].values, df_result['close'].values
        )
        
        # Doji pattern
        df_result['Doji'] = talib.CDLDOJI(
            df_result['open'].values, df_result['high'].values,
            df_result['low'].values, df_result['close'].values
        )
        
        # Evening star
        df_result['EveningStar'] = talib.CDLEVENINGSTAR(
            df_result['open'].values, df_result['high'].values,
            df_result['low'].values, df_result['close'].values
        )
        
        # Morning star
        df_result['MorningStar'] = talib.CDLMORNINGSTAR(
            df_result['open'].values, df_result['high'].values,
            df_result['low'].values, df_result['close'].values
        )
        
        # Harami pattern
        df_result['Harami'] = talib.CDLHARAMI(
            df_result['open'].values, df_result['high'].values,
            df_result['low'].values, df_result['close'].values
        )
        
        # Pattern strength indicator (tổng hợp từ các mẫu hình)
        df_result['Pattern_Strength'] = (
            df_result['Hammer'] + 
            df_result['Engulfing'] + 
            df_result['Doji'] * 0.5 + 
            df_result['EveningStar'] * 2 + 
            df_result['MorningStar'] * 2 +
            df_result['Harami']
        ) / 100  # Normalize
        
        return df_result
    
    def add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng về thời gian.
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng thời gian
        """
        df_result = df.copy()
        
        # Kiểm tra xem index có phải là datetime không
        if df_result.index.dtype == 'datetime64[ns]':
            # Thêm các tính năng thời gian
            df_result['Hour'] = df_result.index.hour
            df_result['Day'] = df_result.index.day
            df_result['Week'] = df_result.index.isocalendar().week
            df_result['Month'] = df_result.index.month
            df_result['Year'] = df_result.index.year
            df_result['DayOfWeek'] = df_result.index.dayofweek
            
            # Tính năng theo mùa
            df_result['Quarter'] = df_result.index.quarter
            
            # Sin và Cos của giờ trong ngày (chu kỳ)
            df_result['Hour_Sin'] = np.sin(2 * np.pi * df_result['Hour'] / 24)
            df_result['Hour_Cos'] = np.cos(2 * np.pi * df_result['Hour'] / 24)
            
            # Sin và Cos của ngày trong tuần
            df_result['DayOfWeek_Sin'] = np.sin(2 * np.pi * df_result['DayOfWeek'] / 7)
            df_result['DayOfWeek_Cos'] = np.cos(2 * np.pi * df_result['DayOfWeek'] / 7)
            
            # Sin và Cos của tháng trong năm
            df_result['Month_Sin'] = np.sin(2 * np.pi * df_result['Month'] / 12)
            df_result['Month_Cos'] = np.cos(2 * np.pi * df_result['Month'] / 12)
        
        return df_result
    
    def add_support_resistance_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng về các mức hỗ trợ/kháng cự.
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng về hỗ trợ/kháng cự
        """
        df_result = df.copy()
        
        # Tính mức hỗ trợ và kháng cự đơn giản dựa trên dữ liệu N phiên gần nhất
        window = 20
        
        if len(df_result) >= window:
            # Rolling windows cho mức cao/thấp
            for i in range(window, len(df_result)):
                # Lấy dữ liệu trong cửa sổ
                high_window = df_result['high'].iloc[i-window:i]
                low_window = df_result['low'].iloc[i-window:i]
                
                # Tìm các đỉnh và đáy cục bộ
                # (Một điểm được coi là đỉnh cục bộ nếu nó cao hơn 2 điểm kề trước và sau)
                highs = []
                lows = []
                
                # Tìm đỉnh
                for j in range(2, len(high_window) - 2):
                    if (high_window.iloc[j] > high_window.iloc[j-1] and 
                        high_window.iloc[j] > high_window.iloc[j-2] and
                        high_window.iloc[j] > high_window.iloc[j+1] and
                        high_window.iloc[j] > high_window.iloc[j+2]):
                        highs.append(high_window.iloc[j])
                
                # Tìm đáy
                for j in range(2, len(low_window) - 2):
                    if (low_window.iloc[j] < low_window.iloc[j-1] and 
                        low_window.iloc[j] < low_window.iloc[j-2] and
                        low_window.iloc[j] < low_window.iloc[j+1] and
                        low_window.iloc[j] < low_window.iloc[j+2]):
                        lows.append(low_window.iloc[j])
                
                # Xác định mức kháng cự (mức thấp nhất trong các đỉnh cao hơn giá hiện tại)
                resistance = float('inf')
                current_price = df_result['close'].iloc[i]
                
                for high in highs:
                    if high > current_price and high < resistance:
                        resistance = high
                
                # Xác định mức hỗ trợ (mức cao nhất trong các đáy thấp hơn giá hiện tại)
                support = 0
                
                for low in lows:
                    if low < current_price and low > support:
                        support = low
                
                # Thêm vào DataFrame
                if resistance != float('inf'):
                    df_result.loc[df_result.index[i], 'Resistance'] = resistance
                else:
                    df_result.loc[df_result.index[i], 'Resistance'] = df_result['high'].iloc[i-window:i].max()
                    
                if support != 0:
                    df_result.loc[df_result.index[i], 'Support'] = support
                else:
                    df_result.loc[df_result.index[i], 'Support'] = df_result['low'].iloc[i-window:i].min()
        
        # Tính khoảng cách đến hỗ trợ/kháng cự
        if 'Support' in df_result.columns and 'Resistance' in df_result.columns:
            df_result['Support_Distance'] = (df_result['close'] - df_result['Support']) / df_result['close']
            df_result['Resistance_Distance'] = (df_result['Resistance'] - df_result['close']) / df_result['close']
            
            # Tỷ lệ khoảng cách (0-1) - càng gần 0.5 càng ở giữa, càng gần 0 hoặc 1 càng gần S/R
            df_result['SR_Ratio'] = df_result['Support_Distance'] / (df_result['Support_Distance'] + df_result['Resistance_Distance'])
            
            # Giá gần mức hỗ trợ hay kháng cự hơn?
            df_result['Near_Support'] = df_result['Support_Distance'] < df_result['Resistance_Distance']
            df_result['Near_Resistance'] = df_result['Support_Distance'] >= df_result['Resistance_Distance']
                
        return df_result
    
    def add_advanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng nâng cao.
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng nâng cao
        """
        df_result = df.copy()
        
        # Chỉ số sức mạnh tương đối (vị thế hiện tại so với mức cao và thấp)
        high_max = df_result['high'].rolling(window=50).max()
        low_min = df_result['low'].rolling(window=50).min()
        
        # Chuẩn hóa đến biên độ 0-100
        df_result['Strength_Index'] = 100 * (df_result['close'] - low_min) / (high_max - low_min)
        
        # Z-score của giá
        df_result['Price_ZScore'] = (df_result['close'] - df_result['close'].rolling(20).mean()) / df_result['close'].rolling(20).std()
        
        # Điểm quay đầu (Pivot Points)
        pivot = (df_result['high'] + df_result['low'] + df_result['close']) / 3
        s1 = 2 * pivot - df_result['high']
        r1 = 2 * pivot - df_result['low']
        
        df_result['PP_Pivot'] = pivot
        df_result['PP_S1'] = s1
        df_result['PP_R1'] = r1
        
        # Giá nằm giữa mức Pivot nào?
        df_result['Between_Pivot_S1'] = (df_result['close'] < df_result['PP_Pivot']) & (df_result['close'] > df_result['PP_S1'])
        df_result['Between_Pivot_R1'] = (df_result['close'] > df_result['PP_Pivot']) & (df_result['close'] < df_result['PP_R1'])
        
        # Chỉ số khớp lệnh tích lũy
        df_result['CMF'] = talib.ADOSC(
            df_result['high'].values, df_result['low'].values, 
            df_result['close'].values, df_result['volume'].values,
            fastperiod=3, slowperiod=10
        )
        
        # Tỷ lệ Higher Highs và Lower Lows (đếm số lần giá tạo đỉnh cao hơn hoặc đáy thấp hơn)
        window = 5
        
        df_result['Higher_High'] = np.zeros(len(df_result))
        df_result['Lower_Low'] = np.zeros(len(df_result))
        
        for i in range(window, len(df_result)):
            # Higher High: Giá cao nhất hiện tại > giá cao nhất trong window trước
            if df_result['high'].iloc[i] > df_result['high'].iloc[i-window:i].max():
                df_result.loc[df_result.index[i], 'Higher_High'] = 1
            
            # Lower Low: Giá thấp nhất hiện tại < giá thấp nhất trong window trước
            if df_result['low'].iloc[i] < df_result['low'].iloc[i-window:i].min():
                df_result.loc[df_result.index[i], 'Lower_Low'] = 1
        
        # Hichimoku Cloud
        tenkan_period = 9
        kijun_period = 26
        senkou_period = 52
        
        # Tenkan-sen (Conversion Line): (Giá cao nhất + Giá thấp nhất) / 2 trong 9 phiên
        df_result['Tenkan_Sen'] = (
            df_result['high'].rolling(window=tenkan_period).max() + 
            df_result['low'].rolling(window=tenkan_period).min()
        ) / 2
        
        # Kijun-sen (Base Line): (Giá cao nhất + Giá thấp nhất) / 2 trong 26 phiên
        df_result['Kijun_Sen'] = (
            df_result['high'].rolling(window=kijun_period).max() + 
            df_result['low'].rolling(window=kijun_period).min()
        ) / 2
        
        # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2
        df_result['Senkou_Span_A'] = (df_result['Tenkan_Sen'] + df_result['Kijun_Sen']) / 2
        
        # Senkou Span B (Leading Span B): (Giá cao nhất + Giá thấp nhất) / 2 trong 52 phiên
        df_result['Senkou_Span_B'] = (
            df_result['high'].rolling(window=senkou_period).max() + 
            df_result['low'].rolling(window=senkou_period).min()
        ) / 2
        
        # Vị trí của giá trong mây Hichimoku
        df_result['Above_Cloud'] = df_result['close'] > df_result['Senkou_Span_A']
        df_result['Below_Cloud'] = df_result['close'] < df_result['Senkou_Span_B']
        df_result['In_Cloud'] = ~(df_result['Above_Cloud'] | df_result['Below_Cloud'])
        
        # Tính năng tổng hợp dựa trên nhiều chỉ báo khác nhau
        df_result['Technical_Score'] = (
            (df_result['RSI'] / 100) * 0.15 +  # RSI
            (df_result['EMA_Trend_Strength']) * 0.2 +  # EMA Trend
            df_result['Price_Momentum'] * 0.15 +  # Momentum
            df_result['Volume_Ratio'] * 0.1 +  # Volume
            df_result['Pattern_Strength'] * 0.15 +  # Patterns
            (df_result['Strength_Index'] / 100) * 0.15 +  # Position Strength
            df_result['ADX'] / 100 * 0.1  # Trend Strength
        )
        
        return df_result
    
    def add_cycle_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng về chu kỳ thị trường.
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng chu kỳ
        """
        df_result = df.copy()
        
        # HT_DCPERIOD estimates the dominant cycle period
        if len(df_result) >= 20:
            df_result['HT_DCPERIOD'] = talib.HT_DCPERIOD(df_result['close'].values)
            
            # HT_DCPHASE - cycle phase
            df_result['HT_DCPHASE'] = talib.HT_DCPHASE(df_result['close'].values)
            
            # HT_PHASOR - in-phase and quadrature components
            in_phase, quadrature = talib.HT_PHASOR(df_result['close'].values)
            df_result['HT_PHASOR_INPHASE'] = in_phase
            df_result['HT_PHASOR_QUADRATURE'] = quadrature
            
            # HT_SINE - sine wave and leading sine wave
            sine, leadsine = talib.HT_SINE(df_result['close'].values)
            df_result['HT_SINE'] = sine
            df_result['HT_LEADSINE'] = leadsine
            
            # Calculate sin and cos of the phase for cyclical representation
            df_result['Phase_Sin'] = np.sin(df_result['HT_DCPHASE'] * np.pi / 180)
            df_result['Phase_Cos'] = np.cos(df_result['HT_DCPHASE'] * np.pi / 180)
        
        return df_result
    
    def add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các tính năng thống kê.
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            
        Returns:
            pd.DataFrame: DataFrame với các tính năng thống kê
        """
        df_result = df.copy()
        
        # Skewness (độ lệch) và Kurtosis (độ nhọn) của giá
        df_result['Return_Skew'] = df_result['Price_Change'].rolling(window=20).apply(
            lambda x: stats.skew(x) if len(x) >= 5 else 0
        )
        
        df_result['Return_Kurt'] = df_result['Price_Change'].rolling(window=20).apply(
            lambda x: stats.kurtosis(x) if len(x) >= 5 else 0
        )
        
        # Rolling Sharpe Ratio
        risk_free_rate = 0  # Giả định lãi suất phi rủi ro là 0
        mean_return = df_result['Price_Change'].rolling(window=20).mean()
        std_return = df_result['Price_Change'].rolling(window=20).std()
        df_result['Sharpe_Ratio'] = (mean_return - risk_free_rate) / std_return.replace(0, np.nan)
        
        # Calmar Ratio: mean return / max drawdown
        # Tính drawdown
        roll_max = df_result['close'].rolling(window=20, min_periods=1).max()
        drawdown = (df_result['close'] / roll_max - 1.0)
        max_drawdown = drawdown.rolling(window=20, min_periods=1).min()
        df_result['Max_Drawdown'] = max_drawdown
        
        # Calmar Ratio
        df_result['Calmar_Ratio'] = mean_return / abs(max_drawdown).replace(0, np.nan)
        
        # Phân phối xác suất cho returns
        for percentile in [10, 25, 50, 75, 90]:
            df_result[f'Return_P{percentile}'] = df_result['Price_Change'].rolling(window=20).apply(
                lambda x: np.percentile(x, percentile) if len(x) >= 5 else 0
            )
        
        # Value at Risk (VaR) - 95% confidence
        df_result['VaR_95'] = df_result['Price_Change'].rolling(window=20).quantile(0.05)
        
        # Expected Shortfall (ES) - 95% confidence
        def calculate_es(returns, confidence_level=0.05):
            if len(returns) < 5:
                return 0
            var = np.percentile(returns, confidence_level * 100)
            return returns[returns <= var].mean() if any(returns <= var) else var
            
        df_result['ES_95'] = df_result['Price_Change'].rolling(window=20).apply(
            lambda x: calculate_es(x) if len(x) >= 5 else 0
        )
        
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
        
        # Điền các giá trị NA bằng phương pháp bfill và ffill
        df_result = df_result.fillna(method='ffill').fillna(method='bfill')
        
        # Thay thế các giá trị vô cùng bằng NaN, sau đó điền bằng 0
        df_result = df_result.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # Kiểm tra xem còn giá trị NaN nào không
        na_cols = df_result.columns[df_result.isna().any()].tolist()
        if na_cols:
            logger.warning(f"Vẫn còn các cột có giá trị NaN: {na_cols}")
            # Lấp đầy các giá trị NA còn lại bằng 0
            df_result = df_result.fillna(0)
        
        return df_result