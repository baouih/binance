import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.simple_feature_engineering import SimpleFeatureEngineering
from app.market_regime_detector import MarketRegimeDetector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('data_processor')

class DataProcessor:
    def __init__(self, binance_api, simulation_mode=False):
        """
        Initialize the DataProcessor.
        
        Args:
            binance_api: BinanceAPI instance
            simulation_mode (bool): Whether to use simulation mode
        """
        self.binance_api = binance_api
        self.simulation_mode = simulation_mode
        self.feature_engineering = SimpleFeatureEngineering()  # Sử dụng phiên bản đơn giản không cần talib
        self.market_regime_detector = MarketRegimeDetector()
        self.current_regime = "neutral"
        logger.info(f"DataProcessor initialized in {'simulation' if simulation_mode else 'live'} mode with ML features")
        
    def get_historical_data(self, symbol, interval='1h', lookback_days=30, start_time=None, end_time=None):
        """
        Get historical data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            interval (str): Kline interval
            lookback_days (int): Number of days to look back
            start_time (int): Start time in milliseconds
            end_time (int): End time in milliseconds
            
        Returns:
            pandas.DataFrame: DataFrame with historical data and indicators
        """
        # Calculate start and end times if not provided
        if not start_time:
            start_time = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
        if not end_time:
            end_time = int(datetime.now().timestamp() * 1000)
            
        # Get klines data
        df = self.binance_api.get_klines(
            symbol=symbol,
            interval=interval,
            limit=1000,
            start_time=start_time,
            end_time=end_time
        )
        
        if df.empty:
            logger.warning(f"No data retrieved for {symbol}")
            return df
            
        # Add indicators
        df = self.add_indicators(df)
        
        # Thêm các tính năng ML nâng cao nếu có đủ dữ liệu
        if len(df) >= 50:
            try:
                # Phát hiện chế độ thị trường
                self.current_regime = self.market_regime_detector.detect_regime(df)
                logger.info(f"Detected market regime: {self.current_regime}")
                
                # Thêm tính năng nâng cao cho ML
                df = self.feature_engineering.add_all_features(df)
            except Exception as e:
                logger.error(f"Error adding ML features: {str(e)}")
        
        # Log some analytics
        self._log_market_analysis(df)
        
        logger.info(f"Processed {len(df)} samples with indicators")
        return df
        
    def add_indicators(self, df):
        """
        Add technical indicators to the dataframe.
        
        Args:
            df (pandas.DataFrame): DataFrame with price data
            
        Returns:
            pandas.DataFrame: DataFrame with added indicators
        """
        if df.empty:
            return df
            
        # Make a copy to avoid SettingWithCopyWarning
        df = df.copy()
        
        # Calculate moving averages
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        # RSI calculation
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands
        df['BB_middle'] = df['SMA_20']
        df['BB_std'] = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + 2 * df['BB_std']
        df['BB_lower'] = df['BB_middle'] - 2 * df['BB_std']
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=14).mean()
        
        # Volume indicators
        df['Volume_MA'] = df['volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['volume'] / df['Volume_MA']
        
        # Price momentum
        df['Price_Change'] = df['close'].pct_change()
        
        # Calculate EMA crossovers (9 and 21)
        df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # Crossover signals (1 for bullish, -1 for bearish, 0 for no crossover)
        df['EMA_Cross_9_21'] = np.where(df['EMA_9'] > df['EMA_21'], 1, -1)
        df['EMA_Cross_21_50'] = np.where(df['EMA_21'] > df['EMA_50'], 1, -1)
        df['EMA_Cross_50_200'] = np.where(df['EMA_50'] > df['EMA_200'], 1, -1)
        
        # Overall EMA trend strength
        df['EMA_Trend_Strength'] = df['EMA_Cross_9_21'] + df['EMA_Cross_21_50'] + df['EMA_Cross_50_200']
        df['EMA_Trend_Strength'] = df['EMA_Trend_Strength'] / 3  # Normalize between -1 and 1
        
        # ADX (Average Directional Index) for trend strength
        # TR calculation was done above
        df['DM_plus'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                              np.maximum(df['high'] - df['high'].shift(1), 0), 0)
        df['DM_minus'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                               np.maximum(df['low'].shift(1) - df['low'], 0), 0)
        
        # Smoothed values (using Wilder's smoothing)
        n = 14  # Period
        df['TR_avg'] = tr.ewm(alpha=1/n, min_periods=n).mean()
        df['DM_plus_avg'] = df['DM_plus'].ewm(alpha=1/n, min_periods=n).mean()
        df['DM_minus_avg'] = df['DM_minus'].ewm(alpha=1/n, min_periods=n).mean()
        
        # DI calculations
        df['DI_plus'] = 100 * df['DM_plus_avg'] / df['TR_avg']
        df['DI_minus'] = 100 * df['DM_minus_avg'] / df['TR_avg']
        
        # DX and ADX
        df['DX'] = 100 * (df['DI_plus'] - df['DI_minus']).abs() / (df['DI_plus'] + df['DI_minus'])
        df['ADX'] = df['DX'].ewm(alpha=1/n, min_periods=n).mean()
        
        # Trend direction (-1 for downtrend, 1 for uptrend, multiplied by ADX for strength)
        df['Trend_Direction'] = np.where(df['DI_plus'] > df['DI_minus'], 1, -1)
        df['Trend_Strength'] = df['Trend_Direction'] * df['ADX'] / 100
        
        # Calculate additional volume indicators
        df['Volume_SMA_5'] = df['volume'].rolling(window=5).mean()
        df['Volume_SMA_20'] = df['volume'].rolling(window=20).mean()
        df['Volume_ROC'] = df['volume'].pct_change(5)  # 5-period rate of change
        
        # Volume trend (-1 to 1 normalized)
        df['Volume_Trend'] = df['Volume_ROC'].rolling(window=5).mean()
        df['Volume_Trend'] = df['Volume_Trend'].clip(-1, 1)  # Clip to range -1 to 1
        
        # Price-volume relationship (positive when price and volume move together)
        df['Price_Volume_Impact'] = df['Price_Change'] * df['Volume_Ratio']
        
        # Money Flow Index components
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        # Calculate ADL (Accumulation/Distribution Line)
        mf_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
        mf_multiplier = mf_multiplier.replace([np.inf, -np.inf], 0)
        df['ADL'] = (mf_multiplier * df['volume']).cumsum()
        
        # OBV (On-Balance Volume)
        df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        
        # Ratio of SMAs
        df['SMA_Ratio'] = df['SMA_20'] / df['SMA_50']
        
        # Bollinger Band width (volatility indicator)
        df['BB_Width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
        
        # Price momentum over different periods
        df['Price_Momentum'] = df['close'].pct_change(5)
        
        # Price volatility (standard deviation of returns)
        df['Price_Volatility'] = df['Price_Change'].rolling(window=20).std()
        
        return df
        
    def _log_market_analysis(self, df):
        """Log market analysis based on the latest data"""
        if df.empty or len(df) < 2:
            return
            
        # Get the latest row
        latest = df.iloc[-1]
        
        # Determine the trend
        trend = "Sideways"
        if latest['EMA_Trend_Strength'] > 0.5:
            trend = "Strong Uptrend"
        elif latest['EMA_Trend_Strength'] > 0:
            trend = "Uptrend"
        elif latest['EMA_Trend_Strength'] < -0.5:
            trend = "Strong Downtrend"
        elif latest['EMA_Trend_Strength'] < 0:
            trend = "Downtrend"
            
        # RSI interpretation
        rsi_status = "Neutral"
        if latest['RSI'] > 70:
            rsi_status = "Overbought"
        elif latest['RSI'] < 30:
            rsi_status = "Oversold"
            
        # Price change percentage
        price_change_pct = latest['Price_Change'] * 100 if 'Price_Change' in latest else 0
        
        # Giới hạn giá trị để tránh lỗi hiển thị
        def safe_value(val, default=0):
            """Trả về giá trị an toàn, tránh NaN và inf"""
            if pd.isna(val) or np.isinf(val):
                return default
            return val
            
        # Áp dụng safe_value cho tất cả các giá trị
        close_price = safe_value(latest['close'])
        price_change = safe_value(price_change_pct)
        rsi_value = safe_value(latest['RSI'])
        macd_value = safe_value(latest['MACD'])
        macd_signal = safe_value(latest['MACD_Signal'])
        volume_ratio = safe_value(latest['Volume_Ratio'])
            
        # Log the analysis
        logger.info("\n=== Latest Market Analysis ===")
        logger.info(f"Price: {close_price:.2f} ({price_change:.2f}% change)")
        logger.info(f"Trend: {trend}")
        logger.info(f"RSI: {rsi_value:.2f} ({rsi_status})")
        logger.info(f"MACD: {macd_value:.2f} (Signal: {macd_signal:.2f})")
        logger.info(f"Volume: {volume_ratio:.2f}x average")
        logger.info("===========================")
        
    def prepare_features_for_ml(self, df):
        """
        Prepare features for machine learning.
        
        Args:
            df (pandas.DataFrame): DataFrame with indicators
            
        Returns:
            tuple: (X, y) features and labels
        """
        if df.empty or len(df) < 50:  # Need at least 50 rows for meaningful prediction
            return None, None
            
        # Make a copy to avoid SettingWithCopyWarning
        df = df.copy()
        
        # Create target variable (1 for price increase, -1 for decrease, 0 for sideways)
        # Look 5 periods ahead
        lookahead = 5
        future_returns = df['close'].pct_change(lookahead).shift(-lookahead)
        threshold = 0.01  # 1% threshold for significant move
        
        df['target'] = np.where(future_returns > threshold, 1, 
                            np.where(future_returns < -threshold, -1, 0))
        
        # Select features
        features = [
            'RSI', 'MACD', 'MACD_Signal', 'EMA_Trend_Strength', 
            'Trend_Strength', 'Volume_Ratio', 'Price_Volume_Impact',
            'Price_Momentum', 'Price_Volatility', 'BB_Width',
            'SMA_Ratio', 'ADX'
        ]
        
        # Drop NaN values
        df_clean = df.dropna(subset=features + ['target'])
        
        if df_clean.empty:
            return None, None
            
        X = df_clean[features]
        y = df_clean['target']
        
        return X, y
