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
        Generate trading signals based on RSI with additional trend and volume filters.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        # Check if dataframe is valid and contains required columns
        required_columns = ['RSI', 'volume']
        if dataframe is None or dataframe.empty or not all(col in dataframe.columns for col in required_columns):
            return 0
            
        # Get the latest data
        latest_rsi = dataframe['RSI'].iloc[-1]
        
        # Get price and moving averages to determine trend if available
        has_trend_info = all(col in dataframe.columns for col in ['close', 'EMA_50', 'EMA_200'])
        has_prev_data = len(dataframe) > 1
        
        # If previous data is available, get previous RSI
        prev_rsi = dataframe['RSI'].iloc[-2] if has_prev_data else latest_rsi
        
        # Check trend
        trend = "neutral"
        if has_trend_info:
            latest_close = dataframe['close'].iloc[-1]
            latest_ema50 = dataframe['EMA_50'].iloc[-1]
            latest_ema200 = dataframe['EMA_200'].iloc[-1]
            
            if latest_ema50 > latest_ema200 and latest_close > latest_ema50:
                trend = "uptrend"
            elif latest_ema50 < latest_ema200 and latest_close < latest_ema50:
                trend = "downtrend"
                
        # Check volume
        high_volume = False
        if 'volume' in dataframe.columns:
            latest_volume = dataframe['volume'].iloc[-1]
            avg_volume = dataframe['volume'].rolling(window=20).mean().iloc[-1] if len(dataframe) >= 20 else latest_volume
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1.0
            high_volume = volume_ratio > 1.2  # Volume is at least 20% above average
            
        # Generate signals with filters
        if latest_rsi < self.oversold:
            # Buy signals - stronger in uptrends with high volume or RSI turning up
            if (trend == "uptrend" and high_volume) or (has_prev_data and latest_rsi > prev_rsi):
                return 1  # Strong buy signal
            elif trend != "downtrend":  # Avoid buying in downtrends
                return 1  # Normal buy signal
                
        elif latest_rsi > self.overbought:
            # Sell signals - stronger in downtrends with high volume or RSI turning down
            if (trend == "downtrend" and high_volume) or (has_prev_data and latest_rsi < prev_rsi):
                return -1  # Strong sell signal
            elif trend != "uptrend":  # Avoid selling in uptrends  
                return -1  # Normal sell signal
                
        return 0  # Hold signal
            
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": {
                "en": "Enhanced RSI strategy with trend and volume filters",
                "vi": "Chiến lược RSI nâng cao với bộ lọc xu hướng và khối lượng"
            },
            "parameters": {
                "overbought": self.overbought,
                "oversold": self.oversold,
                "features": "Trend detection, volume confirmation, RSI reversal detection"
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
    """Machine learning-based trading strategy with market regime awareness."""
    
    def __init__(self, ml_optimizer, market_regime_detector=None, probability_threshold=0.65):
        """
        Initialize ML strategy with market regime awareness.
        
        Args:
            ml_optimizer (MLOptimizer): Trained ML model
            market_regime_detector (MarketRegimeDetector, optional): Detector for market regimes
            probability_threshold (float): Threshold for trading signals
        """
        super().__init__(name="ML Strategy")
        self.ml_optimizer = ml_optimizer
        self.market_regime_detector = market_regime_detector
        self.probability_threshold = probability_threshold
        self.current_regime = "neutral"
        self.regime_thresholds = {
            "trending_up": 0.55,      # Hạ ngưỡng trong thị trường xu hướng tăng để dễ vào lệnh hơn
            "trending_down": 0.55,    # Hạ ngưỡng trong thị trường xu hướng giảm
            "volatile": 0.75,         # Tăng ngưỡng trong thị trường biến động để tránh nhiễu
            "ranging": 0.70,          # Tăng ngưỡng trong thị trường sideway
            "breakout": 0.60,         # Ngưỡng trung bình trong thị trường breakout
            "neutral": 0.65           # Ngưỡng mặc định
        }
        self.regime_signals = []   # Lưu lịch sử tín hiệu theo từng chế độ thị trường
        
    def generate_signal(self, dataframe):
        """
        Generate trading signals based on ML predictions with market regime adaptation.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        # Check if dataframe is valid
        if dataframe is None or dataframe.empty:
            return 0
            
        # Phát hiện chế độ thị trường nếu có
        if self.market_regime_detector:
            try:
                self.current_regime = self.market_regime_detector.detect_regime(dataframe)
                logger.info(f"ML Strategy - Current market regime: {self.current_regime}")
            except Exception as e:
                logger.error(f"Error detecting market regime: {str(e)}")
        
        # Điều chỉnh ngưỡng xác suất theo chế độ thị trường hiện tại
        adjusted_threshold = self.regime_thresholds.get(self.current_regime, self.probability_threshold)
            
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
        
        # Sử dụng mô hình ML phù hợp nhất với chế độ thị trường hiện tại
        model_name = 'ensemble'  # Mặc định dùng ensemble
        if self.current_regime == 'trending_up' or self.current_regime == 'trending_down':
            model_name = 'gradient_boosting'
        elif self.current_regime == 'volatile':
            model_name = 'random_forest'
        elif self.current_regime == 'ranging':
            model_name = 'svm'
        
        # Thử dùng mô hình regime nếu có
        if hasattr(self.ml_optimizer, 'regime_models') and self.current_regime in self.ml_optimizer.regime_models:
            model_name = 'regime'
        
        # Make prediction
        try:
            prediction, probability = self.ml_optimizer.predict(latest_data, model_name=model_name)
            
            if prediction is None or len(prediction) == 0:
                return 0
                
            pred_value = prediction[0]  # Get the prediction for the latest data point
            prob_value = probability[0] if isinstance(probability, np.ndarray) else probability  # Get the probability
            
            # Ghi nhận tín hiệu theo chế độ thị trường
            self.regime_signals.append({
                'regime': self.current_regime,
                'signal': pred_value,
                'probability': prob_value,
                'threshold': adjusted_threshold,
                'timestamp': pd.Timestamp.now()
            })
            
            # Giữ tối đa 100 tín hiệu gần nhất
            if len(self.regime_signals) > 100:
                self.regime_signals = self.regime_signals[-100:]
            
            # Log thông tin tín hiệu
            logger.info(f"ML Signal: {pred_value} with probability {prob_value:.4f} " +
                      f"(threshold: {adjusted_threshold}) in {self.current_regime} regime")
            
            # Chỉ tạo tín hiệu nếu xác suất đủ cao
            if prob_value < adjusted_threshold:
                return 0
                
            return pred_value
        except Exception as e:
            logger.error(f"Error generating ML signal: {str(e)}")
            return 0
    
    def get_performance_by_regime(self):
        """
        Get performance statistics by market regime.
        
        Returns:
            dict: Performance metrics by regime
        """
        stats = {}
        
        # Nếu không có dữ liệu, trả về dict rỗng
        if not self.regime_signals:
            return stats
            
        # Nhóm tín hiệu theo từng chế độ
        for regime in set([s['regime'] for s in self.regime_signals]):
            regime_data = [s for s in self.regime_signals if s['regime'] == regime]
            
            # Tính toán các thống kê
            signal_count = len(regime_data)
            avg_probability = sum(s['probability'] for s in regime_data) / signal_count if signal_count > 0 else 0
            buy_signals = sum(1 for s in regime_data if s['signal'] == 1)
            sell_signals = sum(1 for s in regime_data if s['signal'] == -1)
            hold_signals = sum(1 for s in regime_data if s['signal'] == 0)
            
            stats[regime] = {
                'count': signal_count,
                'avg_probability': avg_probability,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'hold_signals': hold_signals,
                'buy_ratio': buy_signals / signal_count if signal_count > 0 else 0,
                'sell_ratio': sell_signals / signal_count if signal_count > 0 else 0
            }
            
        return stats
            
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        # Get performance statistics
        regime_stats = self.get_performance_by_regime()
        
        return {
            "name": self.name,
            "description": {
                "en": "Trading signals based on machine learning models with market regime awareness",
                "vi": "Tín hiệu giao dịch dựa trên mô hình học máy thích ứng với chế độ thị trường"
            },
            "parameters": {
                "probability_threshold": self.probability_threshold,
                "current_regime": self.current_regime,
                "regime_thresholds": self.regime_thresholds
            },
            "performance": regime_stats
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
        Generate trading signals by combining multiple strategies with improved conflict resolution.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        if not self.strategies or dataframe is None or dataframe.empty:
            return 0
            
        # Get signals from all strategies with debug logging
        signals = []
        strategy_signals = {}
        
        for i, strategy in enumerate(self.strategies):
            signal = strategy.generate_signal(dataframe)
            strategy_name = strategy.name
            strategy_signals[strategy_name] = signal
            signals.append(signal)
            
            # Log the signal from each strategy for debugging
            logger.debug(f"Strategy '{strategy_name}' signal: {signal}")
            
        # Check for market conditions
        market_trend = "neutral"
        if all(col in dataframe.columns for col in ['close', 'EMA_50', 'EMA_200']):
            latest_close = dataframe['close'].iloc[-1]
            latest_ema50 = dataframe['EMA_50'].iloc[-1]
            latest_ema200 = dataframe['EMA_200'].iloc[-1]
            
            if latest_ema50 > latest_ema200 and latest_close > latest_ema50:
                market_trend = "uptrend"
            elif latest_ema50 < latest_ema200 and latest_close < latest_ema50:
                market_trend = "downtrend"
                
        # Calculate consensus signal with market trend consideration
        weighted_signal = sum(s * w for s, w in zip(signals, self.weights))
        
        # Improved signal threshold logic with market trend consideration
        if market_trend == "uptrend":
            # In uptrend, we're more lenient with buy signals and stricter with sell signals
            if weighted_signal > 0.2:  # Lower threshold for buy signals in uptrend
                return 1
            elif weighted_signal < -0.4:  # Higher threshold for sell signals in uptrend
                return -1
        elif market_trend == "downtrend":
            # In downtrend, we're more lenient with sell signals and stricter with buy signals
            if weighted_signal > 0.4:  # Higher threshold for buy signals in downtrend
                return 1
            elif weighted_signal < -0.2:  # Lower threshold for sell signals in downtrend
                return -1
        else:
            # In neutral trend, use standard thresholds
            if weighted_signal > 0.3:
                return 1
            elif weighted_signal < -0.3:
                return -1
                
        return 0  # Hold signal when there's no strong consensus
            
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": {
                "en": "Enhanced combined strategy with trend-adaptive signal thresholds",
                "vi": "Chiến lược kết hợp nâng cao với ngưỡng tín hiệu thích ứng theo xu hướng"
            },
            "parameters": {
                "strategies": [s.name for s in self.strategies],
                "weights": self.weights,
                "features": "Market trend detection, adaptive signal thresholds, consensus weighting"
            }
        }

class AutoStrategy(Strategy):
    """
    Auto Strategy that adapts to market conditions by selecting the most appropriate strategy.
    """
    
    def __init__(self, market_regime_detector=None, ml_optimizer=None):
        """
        Initialize auto strategy with market regime detector.
        
        Args:
            market_regime_detector: MarketRegimeDetector instance for detecting market regime
            ml_optimizer: MLOptimizer instance for ML predictions
        """
        super().__init__(name="Auto Strategy")
        self.market_regime_detector = market_regime_detector
        self.ml_optimizer = ml_optimizer
        self.current_regime = "neutral"
        self.strategy_map = {}
        self.strategy_performance = {}
        self._initialize_strategies()
        
    def _initialize_strategies(self):
        """Initialize strategies for different market regimes."""
        # Initialize strategies for different regimes
        self.strategy_map = {
            "trending_up": EMACrossStrategy(9, 21),  # EMA Cross good for trending up markets
            "trending_down": EMACrossStrategy(12, 26),  # Different parameters for trending down
            "volatile": BBandsStrategy(2.5),  # BBands good for volatile markets with wider bands
            "ranging": RSIStrategy(75, 25),  # RSI good for ranging markets with adjusted thresholds
            "breakout": BBandsStrategy(2.0),  # BBands with narrower bands for breakouts
            "neutral": CombinedStrategy([
                RSIStrategy(70, 30),
                MACDStrategy(),
                EMACrossStrategy(9, 21)
            ], [0.4, 0.3, 0.3])
        }
        
        # Initialize ML strategy if optimizer is available
        if self.ml_optimizer:
            ml_strategy = MLStrategy(self.ml_optimizer, self.market_regime_detector, 0.65)
            # Add ML strategy to all regimes
            for regime in self.strategy_map:
                if isinstance(self.strategy_map[regime], CombinedStrategy):
                    # Add ML to combined strategies
                    strategies = self.strategy_map[regime].strategies + [ml_strategy]
                    weights = self.strategy_map[regime].weights + [0.4]  # Add weight for ML
                    # Normalize weights
                    total = sum(weights)
                    weights = [w / total for w in weights]
                    self.strategy_map[regime] = CombinedStrategy(strategies, weights)
                else:
                    # Replace single strategies with combined (original + ML)
                    strategies = [self.strategy_map[regime], ml_strategy]
                    self.strategy_map[regime] = CombinedStrategy(strategies, [0.6, 0.4])
        
        # Initialize performance tracking
        for regime in self.strategy_map:
            self.strategy_performance[regime] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'pnl': 0.0
            }
    
    def generate_signal(self, dataframe):
        """
        Generate signals by automatically selecting strategy based on market regime.
        
        Args:
            dataframe (pandas.DataFrame): DataFrame with price and indicator data
            
        Returns:
            int: Signal (-1 for sell, 0 for hold, 1 for buy)
        """
        if dataframe is None or dataframe.empty:
            return 0
            
        # Detect current market regime if detector is available
        if self.market_regime_detector:
            try:
                self.current_regime = self.market_regime_detector.detect_regime(dataframe)
                logger.info(f"Auto Strategy - Current market regime: {self.current_regime}")
            except Exception as e:
                logger.error(f"Error detecting market regime: {str(e)}")
                # Default to neutral if detection fails
                self.current_regime = "neutral"
        
        # Get strategy for current regime
        strategy = self.strategy_map.get(self.current_regime, self.strategy_map["neutral"])
        
        # Get signal from selected strategy
        signal = strategy.generate_signal(dataframe)
        
        # Log the selected strategy and signal
        logger.info(f"Auto Strategy using {strategy.name} for {self.current_regime} regime. Signal: {signal}")
        
        return signal
    
    def update_performance(self, regime, win, pnl):
        """
        Update performance metrics for a regime.
        
        Args:
            regime (str): Market regime
            win (bool): Whether the trade was profitable
            pnl (float): Profit and loss
        """
        if regime in self.strategy_performance:
            self.strategy_performance[regime]['trades'] += 1
            if win:
                self.strategy_performance[regime]['wins'] += 1
            else:
                self.strategy_performance[regime]['losses'] += 1
            
            self.strategy_performance[regime]['pnl'] += pnl
            
            # Update win rate
            total_trades = self.strategy_performance[regime]['trades']
            wins = self.strategy_performance[regime]['wins']
            self.strategy_performance[regime]['win_rate'] = wins / total_trades if total_trades > 0 else 0.0
    
    def get_strategy_info(self):
        """
        Get strategy information.
        
        Returns:
            dict: Strategy information
        """
        return {
            "name": self.name,
            "description": {
                "en": "Adaptive strategy that automatically selects the best approach based on market regime",
                "vi": "Chiến lược thích ứng tự động chọn phương pháp tốt nhất dựa trên chế độ thị trường"
            },
            "parameters": {
                "current_regime": self.current_regime,
                "active_strategy": self.strategy_map.get(self.current_regime, self.strategy_map["neutral"]).name,
            },
            "performance": self.strategy_performance
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
            market_regime_detector = kwargs.get('market_regime_detector')
            probability_threshold = kwargs.get('probability_threshold', 0.65)
            return MLStrategy(ml_optimizer, market_regime_detector, probability_threshold)
        elif strategy_type.lower() == 'combined':
            strategies = kwargs.get('strategies', [])
            weights = kwargs.get('weights')
            return CombinedStrategy(strategies, weights)
        elif strategy_type.lower() == 'auto':
            # Auto strategy selects the best strategy based on market conditions
            market_regime_detector = kwargs.get('market_regime_detector')
            ml_optimizer = kwargs.get('ml_optimizer')
            
            # Tạo đối tượng AutoStrategy với detector và optimizer
            return AutoStrategy(market_regime_detector, ml_optimizer)
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
