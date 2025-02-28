import logging
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('strategy')

class Strategy:
    """Base strategy class that all strategies should inherit from."""
    
    def __init__(self, name="BaseStrategy"):
        self.name = name
        self.description = {
            "vi": "Chiến lược cơ sở",
            "en": "Base strategy class"
        }
        
    def generate_signal(self, dataframe):
        """
        Generate trading signals.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        # To be implemented by subclasses
        return 0  # Literal type is important - subclasses must handle type correctly
        
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": "Base strategy class"
        }

class RSIStrategy(Strategy):
    """RSI-based trading strategy."""
    
    def __init__(self, overbought=70, oversold=30):
        """
        Initialize RSI strategy.
        
        Args:
            overbought (float): Overbought threshold
            oversold (float): Oversold threshold
        """
        super().__init__(name="RSI Strategy")
        self.overbought = overbought
        self.oversold = oversold
        
    def generate_signal(self, dataframe):
        """
        Generate trading signals based on RSI.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        # Check if dataframe is valid and contains RSI
        if dataframe is None or dataframe.empty or 'RSI' not in dataframe.columns:
            return 0
            
        # Get the latest RSI value
        latest_rsi = dataframe['RSI'].iloc[-1]
        
        # Generate signals
        if latest_rsi > self.overbought:
            return -1  # Sell signal
        elif latest_rsi < self.oversold:
            return 1  # Buy signal
        else:
            return 0  # Hold
            
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": "Generates signals based on RSI values",
            "parameters": {
                "overbought": self.overbought,
                "oversold": self.oversold
            }
        }

class MACDStrategy(Strategy):
    """MACD-based trading strategy."""
    
    def __init__(self):
        """Initialize MACD strategy."""
        super().__init__(name="MACD Strategy")
        
    def generate_signal(self, dataframe):
        """
        Generate trading signals based on MACD.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        # Check if dataframe is valid and contains MACD
        if dataframe is None or dataframe.empty or 'MACD' not in dataframe.columns or 'MACD_Signal' not in dataframe.columns:
            return 0
            
        # Get the latest MACD and signal values
        macd = dataframe['MACD'].iloc[-2:]
        signal = dataframe['MACD_Signal'].iloc[-2:]
        
        # Check for crossovers
        if macd.iloc[0] < signal.iloc[0] and macd.iloc[1] > signal.iloc[1]:
            return 1  # Bullish crossover (MACD crosses above signal)
        elif macd.iloc[0] > signal.iloc[0] and macd.iloc[1] < signal.iloc[1]:
            return -1  # Bearish crossover (MACD crosses below signal)
        else:
            return 0  # No crossover
            
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": "Generates signals based on MACD crossovers",
            "parameters": {}
        }

class EMACrossStrategy(Strategy):
    """EMA crossover strategy."""
    
    def __init__(self, short_period=9, long_period=21):
        """
        Initialize EMA cross strategy.
        
        Args:
            short_period (int): Short EMA period
            long_period (int): Long EMA period
        """
        super().__init__(name="EMA Cross Strategy")
        self.short_period = short_period
        self.long_period = long_period
        
    def generate_signal(self, dataframe):
        """
        Generate trading signals based on EMA crossovers.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        # Check if dataframe is valid and contains required EMAs
        short_ema = f'EMA_{self.short_period}'
        long_ema = f'EMA_{self.long_period}'
        
        if dataframe is None or dataframe.empty or short_ema not in dataframe.columns or long_ema not in dataframe.columns:
            return 0
            
        # Get the latest EMA values
        short_values = dataframe[short_ema].iloc[-2:]
        long_values = dataframe[long_ema].iloc[-2:]
        
        # Check for crossovers
        if short_values.iloc[0] < long_values.iloc[0] and short_values.iloc[1] > long_values.iloc[1]:
            return 1  # Bullish crossover
        elif short_values.iloc[0] > long_values.iloc[0] and short_values.iloc[1] < long_values.iloc[1]:
            return -1  # Bearish crossover
        else:
            return 0  # No crossover
            
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": f"Generates signals based on EMA ({self.short_period}/{self.long_period}) crossovers",
            "parameters": {
                "short_period": self.short_period,
                "long_period": self.long_period
            }
        }

class BBandsStrategy(Strategy):
    """Bollinger Bands trading strategy."""
    
    def __init__(self, deviation_multiplier=2.0):
        """
        Initialize Bollinger Bands strategy.
        
        Args:
            deviation_multiplier (float): Multiplier for standard deviation
        """
        super().__init__(name="Bollinger Bands Strategy")
        self.deviation_multiplier = deviation_multiplier
        
    def generate_signal(self, dataframe):
        """
        Generate trading signals based on Bollinger Bands.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        # Check if dataframe is valid and contains required bands
        if dataframe is None or dataframe.empty or 'BB_upper' not in dataframe.columns or 'BB_lower' not in dataframe.columns:
            return 0
            
        # Get the latest values
        close = dataframe['close'].iloc[-1]
        upper = dataframe['BB_upper'].iloc[-1]
        lower = dataframe['BB_lower'].iloc[-1]
        
        # Generate signals
        if close > upper:
            return -1  # Overbought, sell signal
        elif close < lower:
            return 1  # Oversold, buy signal
        else:
            return 0  # Inside bands, no signal
            
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": "Generates signals based on price crossing Bollinger Bands",
            "parameters": {
                "deviation_multiplier": self.deviation_multiplier
            }
        }

class MLStrategy(Strategy):
    """Machine learning-based trading strategy."""
    
    def __init__(self, ml_optimizer, probability_threshold=0.65):
        """
        Initialize ML strategy.
        
        Args:
            ml_optimizer (MLOptimizer): Trained ML model
            probability_threshold (float): Threshold for trading signals
        """
        super().__init__(name="ML Strategy")
        self.ml_optimizer = ml_optimizer
        self.probability_threshold = probability_threshold
        
    def generate_signal(self, dataframe):
        """
        Generate trading signals based on ML predictions.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        # Check if dataframe is valid
        if dataframe is None or dataframe.empty:
            return 0
            
        # Prepare features
        features = [
            'RSI', 'MACD', 'MACD_Signal', 'EMA_Trend_Strength', 
            'Trend_Strength', 'Volume_Ratio', 'Price_Volume_Impact',
            'Price_Momentum', 'Price_Volatility', 'BB_Width',
            'SMA_Ratio', 'ADX'
        ]
        
        # Check if all features are present
        missing_features = [f for f in features if f not in dataframe.columns]
        if missing_features:
            logger.warning(f"Missing features for ML strategy: {missing_features}")
            return 0
            
        # Get the latest data
        latest_data = dataframe.iloc[-1:][features]
        
        # Make prediction
        prediction, probability = self.ml_optimizer.predict(latest_data)
        
        if prediction is None:
            return 0
            
        # Only generate signals if the probability is above threshold
        if probability > self.probability_threshold:
            return prediction[0]
        else:
            return 0
            
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": "Generates signals based on machine learning predictions",
            "parameters": {
                "probability_threshold": self.probability_threshold
            }
        }

class CombinedStrategy(Strategy):
    """Combined strategy that aggregates signals from multiple strategies."""
    
    def __init__(self, strategies, weights=None):
        """
        Initialize combined strategy.
        
        Args:
            strategies (list): List of strategy instances
            weights (list): List of weights for each strategy
        """
        super().__init__(name="Combined Strategy")
        self.strategies = strategies
        
        # If weights not provided, assign equal weights
        if weights is None:
            self.weights = [1.0 / len(strategies)] * len(strategies)
        else:
            # Normalize weights to sum to 1
            total = sum(weights)
            self.weights = [w / total for w in weights]
            
    def generate_signal(self, dataframe):
        """
        Generate trading signals by combining multiple strategies.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        if not self.strategies:
            return 0
            
        # Get signals from all strategies
        signals = []
        for strategy in self.strategies:
            signal = strategy.generate_signal(dataframe)
            signals.append(signal)
            
        # Combine signals using weights
        weighted_signal = sum(s * w for s, w in zip(signals, self.weights))
        
        # Threshold for decision
        if weighted_signal > 0.3:
            return 1
        elif weighted_signal < -0.3:
            return -1
        else:
            return 0
            
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": "Combines signals from multiple strategies",
            "parameters": {
                "strategies": [s.name for s in self.strategies],
                "weights": self.weights
            }
        }

class StrategyFactory:
    """Factory class to create strategy instances."""
    
    @staticmethod
    def create_strategy(strategy_type, **kwargs):
        """
        Create a strategy instance.
        
        Args:
            strategy_type (str): Type of strategy to create
            **kwargs: Strategy parameters
            
        Returns:
            Strategy: Strategy instance
        """
        if strategy_type.lower() == 'rsi':
            overbought = kwargs.get('overbought', 70)
            oversold = kwargs.get('oversold', 30)
            return RSIStrategy(overbought, oversold)
        elif strategy_type.lower() == 'macd':
            return MACDStrategy()
        elif strategy_type.lower() == 'ema_cross':
            short_period = kwargs.get('short_period', 9)
            long_period = kwargs.get('long_period', 21)
            return EMACrossStrategy(short_period, long_period)
        elif strategy_type.lower() == 'bbands':
            deviation_multiplier = kwargs.get('deviation_multiplier', 2.0)
            return BBandsStrategy(deviation_multiplier)
        elif strategy_type.lower() == 'ml':
            ml_optimizer = kwargs.get('ml_optimizer')
            probability_threshold = kwargs.get('probability_threshold', 0.65)
            return MLStrategy(ml_optimizer, probability_threshold)
        elif strategy_type.lower() == 'combined':
            strategies = kwargs.get('strategies', [])
            weights = kwargs.get('weights')
            return CombinedStrategy(strategies, weights)
        elif strategy_type.lower() == 'auto':
            # Auto strategy selects the best strategy based on market conditions
            market_regime = kwargs.get('market_regime', 'neutral')
            
            # Define strategy based on market regime
            if market_regime == 'trending_up':
                return EMACrossStrategy(9, 21)  # EMA Cross good for trending markets
            elif market_regime == 'trending_down':
                return EMACrossStrategy(9, 21)  # EMA Cross good for trending markets
            elif market_regime == 'volatile':
                return BBandsStrategy(2.5)  # BBands good for volatile markets
            elif market_regime == 'ranging':
                return RSIStrategy(75, 25)  # RSI good for ranging markets
            else:  # Default to combined strategy for neutral markets
                strategies = [
                    RSIStrategy(70, 30),
                    MACDStrategy(),
                    EMACrossStrategy(9, 21)
                ]
                weights = [0.4, 0.3, 0.3]
                return CombinedStrategy(strategies, weights, name="Auto Strategy")
        else:
            logger.warning(f"Unknown strategy type: {strategy_type}")
            return Strategy()
            
    @staticmethod
    def get_available_strategies():
        """
        Get list of available strategy types.
        
        Returns:
            list: Available strategy types with labels
        """
        return [
            {'id': 'rsi', 'name': 'RSI (Chỉ Báo Sức Mạnh Tương Đối)', 'description': 'Chiến lược dựa trên chỉ báo RSI để xác định vùng quá mua và quá bán.'},
            {'id': 'macd', 'name': 'MACD (Phân Kỳ Trung Bình Động)', 'description': 'Chiến lược dựa trên chỉ báo MACD để xác định xu hướng thị trường.'},
            {'id': 'ema_cross', 'name': 'EMA Cross (Cắt Nhau EMA)', 'description': 'Chiến lược dựa trên sự cắt nhau của đường EMA ngắn và dài hạn.'},
            {'id': 'bbands', 'name': 'Bollinger Bands (Dải Bollinger)', 'description': 'Chiến lược giao dịch dựa trên dải giá Bollinger phân tích biến động.'},
            {'id': 'ml', 'name': 'Machine Learning (Học Máy)', 'description': 'Chiến lược dựa trên mô hình học máy để dự đoán xu hướng giá.'},
            {'id': 'combined', 'name': 'Combined (Kết Hợp)', 'description': 'Chiến lược kết hợp nhiều chỉ báo để đưa ra tín hiệu giao dịch chính xác hơn.'},
            {'id': 'auto', 'name': 'Auto Strategy (Tự Động)', 'description': 'Tự động chọn chiến lược tốt nhất dựa trên điều kiện thị trường hiện tại.'}
        ]
