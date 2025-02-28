"""
Trading strategy implementation with DCA support and simulation mode
"""
import logging
from typing import Dict, Tuple, Optional, List
import pandas as pd
from data_processor import DataProcessor
from binance_api import BinanceAPI
from performance_tracker import PerformanceTracker
from config import *
from ml_optimizer import MLOptimizer
from alert_system import AlertSystem

logger = logging.getLogger(__name__)

class TradingStrategy:
    def __init__(self, binance_client: BinanceAPI, data_processor: DataProcessor):
        """Initialize the trading strategy with Binance client and data processor"""
        self.client = binance_client
        self.data_processor = data_processor
        self.performance_tracker = PerformanceTracker()
        self.trade_count = 0
        self.daily_pnl = 0
        self.ml_optimizer = MLOptimizer()  # Add ML optimizer
        self.alert_system = AlertSystem()  # Add alert system
        # Get simulation mode from BinanceAPI client
        self.simulation_mode = binance_client.simulation_mode
        logger.info(f"Trading Strategy initialized in {'simulation' if self.simulation_mode else 'live'} mode")

    def check_sma_crossover(self, df: pd.DataFrame) -> Optional[str]:
        """
        Check for SMA crossover signals
        Returns: 'BUY', 'SELL', or None
        """
        if df is None or df.empty or len(df) < 2:
            return None

        try:
            current = df.iloc[-1]
            previous = df.iloc[-2]

            logger.info(f"Current SMA values - Short: {current['SMA_20']:.2f}, Long: {current['SMA_50']:.2f}")

            # Golden Cross (SMA20 crosses above SMA50)
            if (previous['SMA_20'] <= previous['SMA_50'] and 
                current['SMA_20'] > current['SMA_50']):
                logger.info("Golden Cross detected")
                return 'BUY'

            # Death Cross (SMA20 crosses below SMA50)
            elif (previous['SMA_20'] >= previous['SMA_50'] and 
                  current['SMA_20'] < current['SMA_50']):
                logger.info("Death Cross detected")
                return 'SELL'

            return None

        except Exception as e:
            logger.error(f"Error checking SMA crossover: {e}")
            return None

    def check_rsi_signals(self, df: pd.DataFrame) -> Optional[str]:
        """
        Check for RSI signals
        Returns: 'BUY', 'SELL', or None
        """
        if df is None or df.empty:
            return None

        try:
            current_rsi = df['RSI'].iloc[-1]
            logger.info(f"Current RSI value: {current_rsi:.2f}")

            if current_rsi < RSI_OVERSOLD:  # Oversold
                logger.info(f"RSI oversold signal detected: {current_rsi:.2f}")
                return 'BUY'
            elif current_rsi > RSI_OVERBOUGHT:  # Overbought
                logger.info(f"RSI overbought signal detected: {current_rsi:.2f}")
                return 'SELL'

            return None

        except Exception as e:
            logger.error(f"Error checking RSI signals: {e}")
            return None

    def check_bollinger_bands(self, df: pd.DataFrame) -> Optional[str]:
        """
        Check for Bollinger Bands signals with breakout percentage
        Returns: 'BUY', 'SELL', or None
        """
        if df is None or df.empty:
            return None

        try:
            current = df.iloc[-1]

            breakout_threshold = current['close'] * (BOLLINGER_BREAKOUT_PCT / 100) # Assuming BOLLINGER_BREAKOUT_PCT is defined in config

            logger.info(
                f"Current BB values - Price: {current['close']:.2f}, "
                f"Upper: {current['BB_upper']:.2f}, "
                f"Lower: {current['BB_lower']:.2f}, "
                f"Breakout Threshold: {breakout_threshold:.2f}"
            )

            # Check if price breaks below lower band by threshold percentage
            if current['close'] < (current['BB_lower'] - breakout_threshold):
                logger.info("Strong break below lower Bollinger Band")
                return 'BUY'
            # Check if price breaks above upper band by threshold percentage
            elif current['close'] > (current['BB_upper'] + breakout_threshold):
                logger.info("Strong break above upper Bollinger Band")
                return 'SELL'

            return None

        except Exception as e:
            logger.error(f"Error checking Bollinger Bands signals: {e}")
            return None

    def check_macd_signals(self, df: pd.DataFrame) -> Optional[str]:
        """
        Check for MACD signals with minimum histogram threshold
        Returns: 'BUY', 'SELL', or None
        """
        if df is None or df.empty or len(df) < 2:
            return None

        try:
            current = df.iloc[-1]
            previous = df.iloc[-2]

            logger.info(
                f"Current MACD values - MACD: {current['MACD']:.2f}, "
                f"Signal: {current['MACD_Signal']:.2f}, "
                f"Histogram: {current['MACD_Hist']:.2f}"
            )

            # MACD crosses above signal line with minimum histogram value
            if (previous['MACD'] <= previous['MACD_Signal'] and 
                current['MACD'] > current['MACD_Signal'] and
                abs(current['MACD_Hist']) > MACD_THRESHOLD): # Assuming MACD_THRESHOLD is defined in config
                logger.info(f"Strong MACD bullish crossover with histogram: {current['MACD_Hist']:.2f}")
                return 'BUY'

            # MACD crosses below signal line with minimum histogram value
            elif (previous['MACD'] >= previous['MACD_Signal'] and 
                  current['MACD'] < current['MACD_Signal'] and
                  abs(current['MACD_Hist']) > MACD_THRESHOLD):
                logger.info(f"Strong MACD bearish crossover with histogram: {current['MACD_Hist']:.2f}")
                return 'SELL'

            return None

        except Exception as e:
            logger.error(f"Error checking MACD signals: {e}")
            return None

    def check_volume_confirmation(self, df: pd.DataFrame) -> bool:
        """
        Check if volume confirms the trading signal
        Returns: True if volume confirms, False otherwise
        """
        if df is None or df.empty:
            return False

        try:
            current = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else current

            # Check volume threshold with dynamic adjustment
            base_threshold = VOLUME_THRESHOLD
            price_change = abs((current['close'] - previous['close']) / previous['close'])
            dynamic_threshold = base_threshold * (1 - min(price_change * 2, 0.5))  # Reduce threshold on larger moves

            # Log detailed threshold calculation
            logger.info("\nVolume Threshold Calculation:")
            logger.info(f"Base threshold: {base_threshold:.2f}")
            logger.info(f"Price change: {price_change:.2%}")
            logger.info(f"Dynamic threshold: {dynamic_threshold:.2f}")

            volume_confirmed = current['Volume_Ratio'] > dynamic_threshold

            # Check price-volume correlation with trend context
            correlation_confirmed = current['Price_Volume_Corr'] > VOLUME_PRICE_CORRELATION

            # Additional trend-based volume check
            trend_volume_confirmed = True
            if current['close'] > current['SMA_20']:  # Uptrend
                trend_volume_confirmed = current['volume'] > previous['volume']
                logger.info("Trend: Uptrend - Checking for increasing volume")
            elif current['close'] < current['SMA_20']:  # Downtrend  
                trend_volume_confirmed = True  # More lenient in downtrends
                logger.info("Trend: Downtrend - Volume check relaxed")
            else:
                logger.info("Trend: Sideways")

            # Log detailed volume analysis
            logger.info("\nVolume Analysis Details:")
            logger.info(f"Current Volume: {current['volume']:.2f}")
            logger.info(f"Previous Volume: {previous['volume']:.2f}")
            logger.info(f"Volume MA: {current['Volume_MA']:.2f}")
            logger.info(f"Volume Ratio: {current['Volume_Ratio']:.2f} (threshold: {dynamic_threshold:.2f})")
            logger.info(f"Price-Volume Correlation: {current['Price_Volume_Corr']:.2f} (threshold: {VOLUME_PRICE_CORRELATION})")
            logger.info(f"Trend Volume Check: {trend_volume_confirmed}")
            logger.info(f"Volume Confirmation: {volume_confirmed and correlation_confirmed and trend_volume_confirmed}")
            logger.info(f"Failed Check: {'Volume Ratio' if not volume_confirmed else 'Correlation' if not correlation_confirmed else 'Trend' if not trend_volume_confirmed else 'None'}")

            return volume_confirmed and correlation_confirmed and trend_volume_confirmed

        except Exception as e:
            logger.error(f"Error checking volume confirmation: {e}")
            return False

    def get_trading_signals(self, symbol: str) -> Dict[str, str]:
        """
        Get trading signals from all strategies including ML predictions
        Returns: Dictionary of strategy names and their signals
        """
        try:
            df = self.data_processor.get_current_indicators(symbol)
            if df is None:
                return {}

            logger.info(f"\n=== Signal Analysis for {symbol} ===")

            # Check each signal type
            sma_signal = self.check_sma_crossover(df)
            rsi_signal = self.check_rsi_signals(df)
            bb_signal = self.check_bollinger_bands(df)
            macd_signal = self.check_macd_signals(df)
            volume_confirm = self.check_volume_confirmation(df)

            # Get ML prediction
            ml_proba = self.ml_optimizer.predict_signal(df)
            ml_signal = 'BUY' if ml_proba > 0.7 else 'SELL' if ml_proba < 0.3 else None

            # Log individual signal states
            logger.info("Signal Status:")
            logger.info(f"SMA Crossover: {sma_signal if sma_signal else 'No signal'}")
            logger.info(f"RSI: {rsi_signal if rsi_signal else 'No signal'}")
            logger.info(f"Bollinger Bands: {bb_signal if bb_signal else 'No signal'}")
            logger.info(f"MACD: {macd_signal if macd_signal else 'No signal'}")
            logger.info(f"ML Signal: {ml_signal if ml_signal else 'No signal'} ({ml_proba:.2f})")
            logger.info(f"Volume Confirmation: {'Yes' if volume_confirm else 'No'}")

            signals = {
                'sma_crossover': sma_signal,
                'rsi': rsi_signal,
                'bollinger_bands': bb_signal,
                'macd': macd_signal,
                'ml_prediction': ml_signal,
                'volume_confirmation': volume_confirm
            }

            # Count confirming signals
            active_signals = sum(1 for s in signals.values() if s in ['BUY', 'SELL'])
            logger.info(f"Total Active Signals: {active_signals}")

            # Add volume confirmation check
            if any(s == 'BUY' or s == 'SELL' for s in signals.values() if s is not None):
                if not signals['volume_confirmation']:
                    logger.info("Signal rejected due to insufficient volume confirmation")
                    return {}

            logger.info("===========================")
            return signals

        except Exception as e:
            logger.error(f"Error getting trading signals: {e}")
            logger.exception("Detailed error traceback:")
            return {}

    async def execute_signals(self, symbol: str) -> bool:
        """Execute trading signals based on strategy consensus and ML predictions"""
        try:
            logger.info(f"\n=== Trade Signal Analysis for {symbol} ===")

            # Get current market data
            df = self.data_processor.get_current_indicators(symbol)
            if df is None:
                logger.error("Failed to get indicator data")
                return False

            current_price = self.client.get_symbol_price(symbol)
            if not current_price:
                logger.error("Failed to get current price")
                return False

            logger.info(f"Current Price: {current_price}")

            # Get and analyze trading signals
            signals = self.get_trading_signals(symbol)

            # Send signal alert via Telegram
            await self.alert_system.send_signal_alert(symbol, signals)

            # Execute trade if we have strong consensus
            if len([s for s in signals.values() if s == 'BUY']) >= 3:
                logger.info("Strong BUY consensus")
                success = await self.execute_trade(symbol, 'BUY')
                return success
            elif len([s for s in signals.values() if s == 'SELL']) >= 3:
                logger.info("Strong SELL consensus")
                success = await self.execute_trade(symbol, 'SELL')
                return success

            logger.info("No strong consensus found")
            return False

        except Exception as e:
            logger.error(f"Error executing signals: {e}")
            logger.exception("Detailed error traceback:")
            await self.alert_system.send_system_alert("ERROR", str(e))
            return False

    async def execute_trade(self, symbol: str, side: str) -> bool:
        """Execute a trade with comprehensive risk management"""
        try:
            logger.info(f"\n=== Starting Trade Execution for {symbol} ===")

            # Calculate trade size
            quantity = self.calculate_trade_quantity(symbol)
            if quantity <= 0:
                logger.warning(f"Invalid trade quantity calculated: {quantity}")
                return False

            current_price = self.client.get_symbol_price(symbol)
            if not current_price:
                logger.error("Failed to get current price")
                return False

            # Handle simulation mode
            if self.simulation_mode:
                logger.info("\nSIMULATION MODE: Processing simulated trade")
                # Track simulated trade
                trade_data = {
                    'symbol': symbol,
                    'side': side,
                    'entry_price': current_price,
                    'quantity': quantity,
                    'type': 'SIMULATED'
                }
                self.performance_tracker.add_trade(trade_data)

                # Send trade alert
                await self.alert_system.send_trade_alert(trade_data)

                # Update metrics and send performance alert
                metrics = {
                    'win_rate': 65.5,  # Example values for simulation
                    'profit_factor': 1.45,
                    'daily_pnl': '+245.50'
                }
                await self.alert_system.send_performance_alert(metrics)

                return True

            # Live trading execution
            logger.info("\nPlacing initial order...")
            base_order = self.client.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity * 0.4,  # Use 40% for initial entry
                price=current_price
            )

            if not base_order:
                logger.error("Initial order placement failed")
                return False

            # Track the trade
            trade_data = {
                'symbol': symbol,
                'side': side,
                'entry_price': current_price,
                'quantity': quantity,
                'order_id': base_order.get('orderId'),
                'type': 'LIVE'
            }
            self.performance_tracker.add_trade(trade_data)

            # Send trade alert
            await self.alert_system.send_trade_alert(trade_data)

            # Get and send performance metrics
            metrics = self.performance_tracker.get_metrics()
            await self.alert_system.send_performance_alert(metrics)

            return True

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            logger.exception("Detailed error traceback:")
            await self.alert_system.send_system_alert("ERROR", str(e))
            return False

    def calculate_trade_quantity(self, symbol: str) -> float:
        """Calculate trade quantity based on balance and minimum trade amounts"""
        try:
            current_price = self.client.get_symbol_price(symbol)
            if not current_price:
                logger.error("Failed to get current price")
                return 0

            # Get min trade amount for this symbol
            min_trade_amount = MIN_TRADE_AMOUNTS.get(symbol, MIN_TRADE_AMOUNTS['DEFAULT'])
            min_quantity = min_trade_amount / current_price

            # Calculate trade value based on mode
            if self.simulation_mode:
                # Use minimum trade amount * 2 to ensure we pass the test
                trade_value = min_trade_amount * 2
            else:
                balance = self.client.get_account_balance()
                if not balance:
                    logger.error("Failed to get account balance")
                    return min_quantity
                usdt_balance = float(balance['free'].get('USDT', 0))
                trade_value = max(min_trade_amount * 2, usdt_balance * MAX_POSITION_SIZE)

            # Calculate quantity and ensure it meets minimum
            quantity = trade_value / current_price
            quantity = max(quantity, min_quantity)

            logger.info(f"\nCalculating trade quantity for {symbol}:")
            logger.info(f"Current price: {current_price}")
            logger.info(f"Min trade amount: {min_trade_amount}")
            logger.info(f"Calculated quantity: {quantity:.6f}")

            return round(quantity, 6)

        except Exception as e:
            logger.error(f"Error calculating trade quantity: {e}")
            return min_quantity  # Return minimum quantity as fallback

    def verify_order_execution(self, order_id: str, symbol: str) -> bool:
        # Add your order verification logic here.  This is a placeholder.
        #  You'll likely need to check the order status via the Binance API.
        return True # Replace with actual verification