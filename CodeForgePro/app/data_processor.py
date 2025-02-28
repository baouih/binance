import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Optional
from binance_api import BinanceAPI
from config import *

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self, binance_client: BinanceAPI):
        """Initialize the data processor with Binance client"""
        self.client = binance_client
        self.simulation_mode = binance_client.simulation_mode
        if LOG_TO_FILE:
            file_handler = logging.FileHandler(LOG_FILE)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(file_handler)
        logger.info(f"DataProcessor initialized in {'simulation' if self.simulation_mode else 'live'} mode")

    def get_historical_klines(self, symbol: str, interval: str, limit: int = 100):
        """Get historical kline/candlestick data"""
        try:
            if self.simulation_mode:
                # Generate synthetic data for simulation mode
                # Calculate proper timedelta based on interval
                interval_map = {
                    '1d': timedelta(days=1),
                    '1h': timedelta(hours=1),
                    '15m': timedelta(minutes=15),
                    '5m': timedelta(minutes=5),
                    '1m': timedelta(minutes=1)
                }
                delta = interval_map.get(interval, timedelta(days=1))

                # Generate dates working backwards from now
                end_date = datetime.now()
                start_date = end_date - (delta * limit)
                dates = pd.date_range(start=start_date, end=end_date, periods=limit)

                # Set base price according to symbol
                if symbol == 'BTCUSDT':
                    base_price = 85000
                elif symbol == 'ETHUSDT':
                    base_price = 2500
                else:
                    base_price = 100

                # Generate more dynamic price movements with increased volatility
                time = np.linspace(0, 10, limit)

                # Multiple volatility components
                trend = np.sin(time) * base_price * 0.15  # Main trend
                volatility = np.sin(time * 3) * base_price * 0.08  # Medium cycle
                micro_volatility = np.sin(time * 8) * base_price * 0.05  # Short cycle
                noise = np.random.normal(0, base_price * 0.03, limit)  # Random noise

                # Combine all components
                prices = base_price + trend + volatility + micro_volatility + noise

                # More realistic high/low prices
                high_prices = prices * (1 + np.random.uniform(0.005, 0.05, limit))
                low_prices = prices * (1 - np.random.uniform(0.005, 0.05, limit))

                # Generate realistic volume patterns
                price_changes = np.diff(prices, prepend=prices[0])
                trend_factor = np.abs(trend / base_price)
                volume_base = np.abs(price_changes) * base_price * 25
                volume = volume_base * (1 + trend_factor * 8) * (1 + np.random.normal(0, 0.8, limit))
                volume = np.maximum(volume, 0)  # Ensure positive volume

                # Scale volume based on volatility
                relative_vol = (high_prices - low_prices) / prices
                volume = volume * (1 + relative_vol * 5)
                volume = volume * (1 + np.abs(price_changes/prices) * 6)

                df = pd.DataFrame({
                    'timestamp': dates,
                    'open': prices,
                    'high': high_prices,
                    'low': low_prices,
                    'close': prices,
                    'volume': volume,
                    'close_time': dates + delta,
                    'quote_volume': volume * prices,
                    'trades': np.random.randint(100, 2000, limit),
                    'buy_base_volume': volume * 0.6,
                    'buy_quote_volume': volume * prices * 0.6,
                    'ignore': [0] * limit
                })

                logger.info(f"SIMULATION: Generated {len(df)} samples of synthetic data for {symbol}")
                logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
                logger.info(f"Price range: {df['close'].min():.2f} to {df['close'].max():.2f}")

                return df

            if not self.client:
                logger.error("Binance client not initialized")
                return None

            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            if not klines:
                logger.warning(f"No data received for {symbol}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'close_time', 'quote_volume', 'trades',
                'buy_base_volume', 'buy_quote_volume', 'ignore'
            ])

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Convert price columns to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            return df
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None

    def get_historical_data(self, symbol: str, interval: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Get historical data - alias for get_historical_klines with indicator calculation"""
        try:
            # Get klines data
            df = self.get_historical_klines(symbol, interval, limit)
            if df is None or len(df) < limit * 0.9:  # Allow for some missing data but require at least 90%
                logger.warning(f"Insufficient historical data: got {len(df) if df is not None else 0} samples, expected {limit}")
                # Switch to simulation mode if we don't have enough data
                if not self.simulation_mode:
                    logger.info("Switching to simulation mode to generate synthetic data")
                    self.simulation_mode = True
                    df = self.get_historical_klines(symbol, interval, limit)

            # Calculate indicators if we have data
            if df is not None and not df.empty:
                df = self.calculate_indicators(df)
                logger.info(f"Processed {len(df)} samples with indicators")
                return df

            logger.error("Failed to get historical data")
            return None

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            logger.exception("Detailed error traceback:")
            return None

    def calculate_ema_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate EMA crossover signals"""
        # Fast and slow EMAs
        df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # EMA Crossover signals
        df['EMA_Cross_9_21'] = np.where(df['EMA_9'] > df['EMA_21'], 1, -1)
        df['EMA_Cross_21_50'] = np.where(df['EMA_21'] > df['EMA_50'], 1, -1)
        df['EMA_Cross_50_200'] = np.where(df['EMA_50'] > df['EMA_200'], 1, -1)

        # Trend strength based on EMA alignment
        df['EMA_Trend_Strength'] = (df['EMA_Cross_9_21'] + df['EMA_Cross_21_50'] + df['EMA_Cross_50_200']) / 3

        return df

    def analyze_volume_profile(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhanced volume profile analysis"""
        # Volume moving averages
        df['Volume_SMA_5'] = df['volume'].rolling(window=5).mean()
        df['Volume_SMA_20'] = df['volume'].rolling(window=20).mean()

        # Volume momentum
        df['Volume_ROC'] = df['volume'].pct_change(5)  # 5-period Rate of Change

        # Volume trend strength
        df['Volume_Trend'] = df['Volume_SMA_5'] / df['Volume_SMA_20']

        # Price-volume relationship
        df['Price_Volume_Impact'] = df['Price_Change'] * (df['volume'] / df['Volume_SMA_20'])

        # Accumulation/Distribution
        df['ADL'] = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low']) * df['volume']
        df['ADL'] = df['ADL'].cumsum()

        # On-Balance Volume (OBV)
        df['OBV'] = np.where(df['close'] > df['close'].shift(1), df['volume'], 
                            np.where(df['close'] < df['close'].shift(1), -df['volume'], 0)).cumsum()

        return df

    def calculate_indicators(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Calculate technical indicators"""
        if df is None or df.empty:
            logger.error("Empty DataFrame provided for indicator calculation")
            return None

        try:
            # Handle missing data
            df = df.ffill().bfill()

            # Moving averages
            df['SMA_20'] = df['close'].rolling(window=SMA_SHORT_PERIOD, min_periods=1).mean()
            df['SMA_50'] = df['close'].rolling(window=SMA_LONG_PERIOD, min_periods=1).mean()
            df['EMA_20'] = df['close'].ewm(span=SMA_SHORT_PERIOD, adjust=False).mean()

            # RSI with dynamic components
            df['Price_Change'] = df['close'].diff()
            df['Gain'] = df['Price_Change'].apply(lambda x: x if x > 0 else 0)
            df['Loss'] = df['Price_Change'].apply(lambda x: -x if x < 0 else 0)

            # Average gains and losses
            avg_gain = df['Gain'].rolling(window=RSI_PERIOD).mean()
            avg_loss = df['Loss'].rolling(window=RSI_PERIOD).mean()

            # RSI calculation
            rs = avg_gain / avg_loss
            df['RSI'] = 100 - (100 / (1 + rs))
            df['RSI'] = df['RSI'].fillna(50)  # Initialize with neutral value
            df['RSI'] = df['RSI'].clip(0, 100)  # Ensure RSI stays within bounds

            # Bollinger Bands
            df['BB_middle'] = df['close'].rolling(window=BOLLINGER_PERIOD, min_periods=1).mean()
            bb_std = df['close'].rolling(window=BOLLINGER_PERIOD, min_periods=1).std()
            df['BB_upper'] = df['BB_middle'] + (BOLLINGER_STD_DEV * bb_std)
            df['BB_lower'] = df['BB_middle'] - (BOLLINGER_STD_DEV * bb_std)

            # MACD
            exp1 = df['close'].ewm(span=MACD_FAST, adjust=False).mean()
            exp2 = df['close'].ewm(span=MACD_SLOW, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_Signal'] = df['MACD'].ewm(span=MACD_SIGNAL, adjust=False).mean()
            df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

            # Volume indicators
            df['Volume_MA'] = df['volume'].rolling(window=VOLUME_MA_PERIOD, min_periods=1).mean()
            df['Volume_Ratio'] = df['volume'] / df['Volume_MA']
            df['Volume_Ratio'] = df['Volume_Ratio'].replace([np.inf, -np.inf], 1.0)

            # Price-volume correlation
            df['Price_Volume_Corr'] = df['close'].pct_change().rolling(
                window=20, min_periods=5
            ).corr(df['volume'].pct_change())

            # New indicators
            df['ADX'] = self.calculate_adx(df)
            df['Trend_Strength'] = self.calculate_trend_strength(df)

            # Add EMA crossover signals
            df = self.calculate_ema_signals(df)

            # Add enhanced volume analysis
            df = self.analyze_volume_profile(df)

            # Log validation with trend information
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            trend = "Uptrend" if latest['close'] > latest['SMA_20'] > latest['SMA_50'] else \
                   "Downtrend" if latest['close'] < latest['SMA_20'] < latest['SMA_50'] else \
                   "Sideways"

            rsi_trend = "Overbought" if latest['RSI'] > 70 else \
                       "Oversold" if latest['RSI'] < 30 else \
                       "Neutral"

            logger.info("\n=== Latest Market Analysis ===")
            logger.info(f"Price: {latest['close']:.2f} ({(latest['close']/prev['close']-1)*100:.2f}% change)")
            logger.info(f"Trend: {trend}")
            logger.info(f"RSI: {latest['RSI']:.2f} ({rsi_trend})")
            logger.info(f"MACD: {latest['MACD']:.2f} (Signal: {latest['MACD_Signal']:.2f})")
            logger.info(f"Volume: {latest['Volume_Ratio']:.2f}x average")
            logger.info("===========================")

            return df
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            logger.exception("Detailed error traceback:")
            return None

    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX)"""
        try:
            # Calculate True Range
            df['TR'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )

            # Calculate Directional Movement
            df['DM_plus'] = np.where(
                (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                np.maximum(df['high'] - df['high'].shift(1), 0),
                0
            )

            df['DM_minus'] = np.where(
                (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                np.maximum(df['low'].shift(1) - df['low'], 0),
                0
            )

            # Calculate smoothed averages
            df['TR_avg'] = df['TR'].rolling(window=period).mean()
            df['DM_plus_avg'] = df['DM_plus'].rolling(window=period).mean()
            df['DM_minus_avg'] = df['DM_minus'].rolling(window=period).mean()

            # Calculate Directional Indicators
            df['DI_plus'] = 100 * (df['DM_plus_avg'] / df['TR_avg'])
            df['DI_minus'] = 100 * (df['DM_minus_avg'] / df['TR_avg'])

            # Calculate Directional Index
            df['DX'] = 100 * abs(df['DI_plus'] - df['DI_minus']) / (df['DI_plus'] + df['DI_minus'])

            # Calculate ADX
            adx = df['DX'].rolling(window=period).mean()

            return adx.fillna(0)
        except Exception as e:
            logger.error(f"Error calculating ADX: {e}")
            return pd.Series(0, index=df.index)

    def calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """Calculate custom trend strength indicator"""
        try:
            # Price momentum
            momentum = df['close'].pct_change(periods=5)

            # Moving average alignment
            ma_alignment = (df['SMA_20'] > df['SMA_50']).astype(int) * 2 - 1

            # Price position relative to moving averages
            price_vs_ma = ((df['close'] - df['SMA_20']) / df['SMA_20']) * 100

            # Combine indicators
            trend_strength = (
                momentum * 0.3 +  # 30% weight to momentum
                ma_alignment * 0.3 +  # 30% weight to MA alignment
                price_vs_ma * 0.4  # 40% weight to price position
            )

            return trend_strength.fillna(0)
        except Exception as e:
            logger.error(f"Error calculating trend strength: {e}")
            return pd.Series(0, index=df.index)

    def get_current_indicators(self, symbol: str, interval: str = '1h'):
        """Get current technical indicators for a symbol"""
        df = self.get_historical_klines(symbol, interval)
        if df is not None:
            return self.calculate_indicators(df)
        return None

    def backtest_strategy(self, symbol: str, start_date: str, end_date: str = None):
        """Perform backtesting of the trading strategy"""
        try:
            # Get historical data
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')

            # Calculate indicators and generate signals
            df = self.get_historical_klines(symbol, '1h', 1000)  # Get more data for accurate backtesting
            if df is None:
                return None

            df = self.calculate_indicators(df)

            # Initialize performance metrics
            df['Position'] = 0  # 1 for long, -1 for short, 0 for neutral
            df['Returns'] = 0.0

            # Calculate signals and positions
            # This will be implemented based on your trading strategy

            # Calculate performance metrics
            total_trades = len(df[df['Position'] != df['Position'].shift(1)]) // 2
            winning_trades = len(df[df['Returns'] > 0])
            losing_trades = len(df[df['Returns'] < 0])

            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            avg_win = df[df['Returns'] > 0]['Returns'].mean() if winning_trades > 0 else 0
            avg_loss = df[df['Returns'] < 0]['Returns'].mean() if losing_trades > 0 else 0

            # Calculate drawdown
            cumulative_returns = (1 + df['Returns']).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdown.min()

            # Log results
            logger.info(f"Backtesting Results for {symbol}:")
            logger.info(f"Total Trades: {total_trades}")
            logger.info(f"Win Rate: {win_rate:.2%}")
            logger.info(f"Average Win: {avg_win:.2%}")
            logger.info(f"Average Loss: {avg_loss:.2%}")
            logger.info(f"Maximum Drawdown: {max_drawdown:.2%}")

            return {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'max_drawdown': max_drawdown
            }
        except Exception as e:
            logger.error(f"Error in backtesting: {e}")
            return None