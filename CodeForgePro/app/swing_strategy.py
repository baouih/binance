import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from .binance_api import BinanceAPI
from .config import (
    SWING_MIN_RANGE_PCT,
    SWING_ENTRY_DEVIATION,
    SWING_CONFIRMATION_PERIODS,
    SWING_PROFIT_TARGET,
    SWING_MAX_HOLDING_TIME,
    TAKE_PROFIT_LEVELS,
    STOP_LOSS_PCT
)

logger = logging.getLogger(__name__)

class SwingStrategy:
    def __init__(self, binance_client: BinanceAPI):
        self.client = binance_client
        self.active_ranges = {}  # Track active trading ranges per symbol

    def identify_range(self, df: pd.DataFrame) -> Optional[Dict]:
        """Identify potential trading range using price action and volume"""
        try:
            # Calculate local highs and lows with more sophisticated analysis
            window = 20  # Look at last 20 candles
            data = df.tail(window)

            # Use volume-weighted price levels
            volume_weighted_price = (data['close'] * data['volume']).sum() / data['volume'].sum()

            # Find resistance and support using volume profile
            price_volume = pd.DataFrame({
                'price': data['close'],
                'volume': data['volume']
            }).groupby('price').sum()

            # Find high-volume price levels
            high_volume_levels = price_volume.nlargest(3, 'volume').index.tolist()

            # Calculate dynamic support and resistance
            resistance = max(high_volume_levels)
            support = min(high_volume_levels)

            # Calculate range percentage
            range_pct = ((resistance - support) / support) * 100

            if range_pct >= SWING_MIN_RANGE_PCT:
                current_price = df['close'].iloc[-1]

                # Check if price is near support or resistance
                support_distance = abs((current_price - support) / support * 100)
                resistance_distance = abs((current_price - resistance) / resistance * 100)

                # Check range stability
                range_stability = self.check_range_stability(df, support, resistance)

                range_info = {
                    'support': support,
                    'resistance': resistance,
                    'range_pct': range_pct,
                    'near_support': support_distance <= SWING_ENTRY_DEVIATION,
                    'near_resistance': resistance_distance <= SWING_ENTRY_DEVIATION,
                    'stability': range_stability,
                    'volume_profile': high_volume_levels
                }

                logger.info(f"Range Analysis:")
                logger.info(f"Support: {support:.2f}")
                logger.info(f"Resistance: {resistance:.2f}")
                logger.info(f"Range %: {range_pct:.2f}")
                logger.info(f"Support Distance: {support_distance:.2f}%")
                logger.info(f"Resistance Distance: {resistance_distance:.2f}%")
                logger.info(f"Range Stability: {range_stability:.2f}")

                return range_info

            return None

        except Exception as e:
            logger.error(f"Error identifying range: {e}")
            return None

    def check_range_stability(self, df: pd.DataFrame, support: float, resistance: float) -> float:
        """Check how stable the trading range is"""
        try:
            # Calculate how often price respects support/resistance levels
            lookback = min(len(df), SWING_CONFIRMATION_PERIODS)
            data = df.tail(lookback)

            support_tests = 0
            resistance_tests = 0
            support_breaks = 0
            resistance_breaks = 0

            for _, row in data.iterrows():
                if row['low'] <= support * 1.01:  # Within 1% of support
                    support_tests += 1
                    if row['close'] < support * 0.99:  # Break below support
                        support_breaks += 1

                if row['high'] >= resistance * 0.99:  # Within 1% of resistance
                    resistance_tests += 1
                    if row['close'] > resistance * 1.01:  # Break above resistance
                        resistance_breaks += 1

            # Calculate stability score (0-1)
            total_tests = support_tests + resistance_tests
            total_breaks = support_breaks + resistance_breaks

            if total_tests == 0:
                return 0

            stability = 1 - (total_breaks / total_tests)
            return stability

        except Exception as e:
            logger.error(f"Error checking range stability: {e}")
            return 0

    def get_entry_points(self, df: pd.DataFrame) -> Optional[Dict]:
        """Get optimal entry points for swing trading"""
        range_info = self.identify_range(df)
        if not range_info or range_info['stability'] < 0.7:  # Require high stability
            return None

        try:
            current_price = df['close'].iloc[-1]

            # Calculate multiple take-profit levels
            mid_range = (range_info['resistance'] + range_info['support']) / 2

            entry_points = None
            if range_info['near_support']:
                # Buy setup near support
                entry_points = {
                    'side': 'BUY',
                    'entry': current_price,
                    'stop_loss': range_info['support'] * (1 - STOP_LOSS_PCT/100),
                    'take_profits': [
                        mid_range * (1 + tp/100) for tp in TAKE_PROFIT_LEVELS
                    ]
                }

            elif range_info['near_resistance']:
                # Sell setup near resistance
                entry_points = {
                    'side': 'SELL',
                    'entry': current_price,
                    'stop_loss': range_info['resistance'] * (1 + STOP_LOSS_PCT/100),
                    'take_profits': [
                        mid_range * (1 - tp/100) for tp in TAKE_PROFIT_LEVELS
                    ]
                }

            if entry_points:
                logger.info(f"Swing Entry Points:")
                logger.info(f"Side: {entry_points['side']}")
                logger.info(f"Entry: {entry_points['entry']:.2f}")
                logger.info(f"Stop Loss: {entry_points['stop_loss']:.2f}")
                logger.info(f"Take Profits: {[f'{tp:.2f}' for tp in entry_points['take_profits']]}")

            return entry_points

        except Exception as e:
            logger.error(f"Error calculating entry points: {e}")
            return None

    def execute_swing_trade(self, symbol: str, df: pd.DataFrame) -> bool:
        """Execute swing trade if conditions are met"""
        try:
            entry_points = self.get_entry_points(df)
            if not entry_points:
                return False

            # Calculate position size based on range size
            quantity = self.client.calculate_trade_quantity(symbol)
            if quantity <= 0:
                return False

            # Split quantity for multiple entries
            entry_levels = 3  # Number of entry orders
            quantity_per_order = quantity / entry_levels

            # Place multiple orders near entry point with different take profits
            success = self.client.manage_swing_trade(
                symbol=symbol,
                support_price=entry_points['stop_loss'],
                resistance_price=max(entry_points['take_profits']),
                quantity=quantity_per_order
            )

            if success:
                logger.info(f"Successfully placed swing trade orders for {symbol}")
                # Track this range
                self.active_ranges[symbol] = {
                    'side': entry_points['side'],
                    'entry': entry_points['entry'],
                    'stop_loss': entry_points['stop_loss'],
                    'take_profits': entry_points['take_profits']
                }
                return True

            return False

        except Exception as e:
            logger.error(f"Error executing swing trade: {e}")
            return False

    def manage_active_trades(self, symbol: str) -> None:
        """Manage active swing trades - adjust stops and take profits"""
        try:
            if symbol not in self.active_ranges:
                return

            current_price = self.client.get_symbol_price(symbol)
            if not current_price:
                return

            trade = self.active_ranges[symbol]

            # Move stop loss to break even if price reaches first take profit
            if trade['side'] == 'BUY':
                if current_price >= trade['take_profits'][0]:
                    new_stop = trade['entry']
                    logger.info(f"Moving stop loss to break even at {new_stop:.2f}")
                    # Update stop loss orders here
            else:
                if current_price <= trade['take_profits'][0]:
                    new_stop = trade['entry']
                    logger.info(f"Moving stop loss to break even at {new_stop:.2f}")
                    # Update stop loss orders here

        except Exception as e:
            logger.error(f"Error managing active trades: {e}")