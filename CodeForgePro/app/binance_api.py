"""
Binance API client with simulation mode support
"""
import logging
import numpy as np
from typing import Dict, List, Optional
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException
from decimal import Decimal
from config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    BINANCE_TESTNET,
    SIMULATION_MODE,
    MIN_TRADE_AMOUNTS,
    DCA_LEVELS,
    DCA_DISTRIBUTION,
    DCA_PRICE_DEVIATION,
    TAKE_PROFIT_LEVELS,
    TAKE_PROFIT_DISTRIBUTION
)

logger = logging.getLogger(__name__)

class BinanceAPI:
    def __init__(self):
        """Initialize the API client with proper simulation handling"""
        self.simulation_mode = SIMULATION_MODE
        logger.info(f"Initializing BinanceAPI in {'simulation' if self.simulation_mode else 'live'} mode")

        # Only create real client if not in simulation mode
        self.client = None
        if not self.simulation_mode:
            try:
                self.client = Client(
                    BINANCE_API_KEY,
                    BINANCE_API_SECRET,
                    testnet=BINANCE_TESTNET
                )
            except Exception as e:
                logger.error(f"Failed to initialize Binance client: {e}")
                self.simulation_mode = True  # Fallback to simulation mode
                self.client = None

        # Initialize simulation state
        self.simulated_balance = 10000.0  # Initial simulated USDT balance
        self.simulated_prices = {
            'BTCUSDT': 85000.0,
            'ETHUSDT': 2500.0,
            'DEFAULT': 100.0
        }
        self.active_trades = {}
        self.dca_orders = {}
        self.tp_orders = {}

        logger.info(f"BinanceAPI initialized with client: {self.client is not None}")

    def get_account_balance(self) -> Dict:
        """Get account balance for all assets"""
        try:
            if self.simulation_mode:
                return {
                    'free': {'USDT': self.simulated_balance},
                    'locked': {'USDT': 0.0}
                }

            balance = self.client.get_account()
            if not balance:
                return {'free': {'USDT': 0.0}, 'locked': {'USDT': 0.0}}
            return balance

        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return {'free': {'USDT': 0.0}, 'locked': {'USDT': 0.0}}

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            if self.simulation_mode or self.client is None:
                return self.simulated_prices.get(symbol, self.simulated_prices['DEFAULT'])

            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return self.simulated_prices.get(symbol, self.simulated_prices['DEFAULT'])

    def create_order(self, symbol: str, side: str, type: str, timeInForce: str = None,
                    quantity: float = None, price: float = None, stopPrice: float = None) -> Dict:
        """Create an order with the Binance API or simulate order in test mode"""
        try:
            # Always create simulated orders in simulation mode or when client is None
            if self.simulation_mode or self.client is None:
                order_id = f"SIM_{int(time.time() * 1000)}"
                current_price = price or self.get_symbol_price(symbol)

                # Create simulated order response
                order = {
                    'orderId': order_id,
                    'symbol': symbol,
                    'side': side,
                    'type': type,
                    'timeInForce': timeInForce,
                    'quantity': quantity,
                    'price': current_price,
                    'stopPrice': stopPrice,
                    'status': 'FILLED',
                    'fills': [{'price': current_price}]
                }

                # Track order and update balance
                order_value = quantity * current_price
                if side == 'BUY':
                    self.simulated_balance -= order_value
                else:
                    self.simulated_balance += order_value

                # Store order in appropriate collection
                if type == 'LIMIT':
                    self.dca_orders[order_id] = order
                elif type == 'TAKE_PROFIT_LIMIT':
                    self.tp_orders[order_id] = order
                else:
                    self.active_trades[order_id] = order

                logger.info(f"SIMULATION: Created order: {order}")
                return order

            # Only attempt real API calls in live mode with valid client
            params = {
                'symbol': symbol,
                'side': side,
                'type': type,
                'quantity': quantity
            }

            if timeInForce:
                params['timeInForce'] = timeInForce
            if price:
                params['price'] = price
            if stopPrice:
                params['stopPrice'] = stopPrice

            return self.client.create_order(**params)

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            if self.simulation_mode:
                return None
            self.simulation_mode = True  # Switch to simulation mode on error
            return self.create_order(symbol, side, type, timeInForce, quantity, price, stopPrice)

    def verify_order_execution(self, order_id: str, symbol: str) -> bool:
        """Verify that an order was executed correctly"""
        if self.simulation_mode or self.client is None:
            # In simulation mode, check if order exists in any of our collections
            return (order_id in self.active_trades or
                    order_id in self.dca_orders or
                    order_id in self.tp_orders)

        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return order['status'] == 'FILLED'

        except Exception as e:
            logger.error(f"Error verifying order {order_id}: {e}")
            return False

    def place_dca_orders(self, symbol: str, side: str, total_quantity: float, base_price: float) -> List[Dict]:
        """Place multiple DCA orders at different price levels"""
        orders = []

        try:
            # Calculate min quantity for this symbol
            min_trade_amount = MIN_TRADE_AMOUNTS.get(symbol, MIN_TRADE_AMOUNTS['DEFAULT'])
            min_quantity = min_trade_amount / base_price

            logger.info(f"\n=== DCA Order Placement for {symbol} ===")
            logger.info(f"Total quantity: {total_quantity:.6f}")
            logger.info(f"Base price: {base_price:.2f}")
            logger.info(f"Min quantity per order: {min_quantity:.6f}")

            # Place orders at each DCA level
            for level, (tp_percentage, size_percentage) in enumerate(zip(DCA_LEVELS, DCA_DISTRIBUTION), 1):
                # Calculate quantity for this level
                quantity = total_quantity * size_percentage

                # Ensure minimum quantity
                if quantity < min_quantity:
                    quantity = min_quantity

                # Calculate price for this level
                price_adjustment = 1 - (level * DCA_PRICE_DEVIATION) if side == 'BUY' else 1 + (level * DCA_PRICE_DEVIATION)
                target_price = base_price * price_adjustment

                logger.info(f"DCA Level {level}:")
                logger.info(f"Quantity: {quantity:.6f}")
                logger.info(f"Target price: {target_price:.2f}")

                order = self.create_order(
                    symbol=symbol,
                    side=side,
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=quantity,
                    price=target_price
                )

                if order:
                    orders.append(order)
                    logger.info(f"DCA order {level} placed successfully")
                else:
                    logger.warning(f"Failed to place DCA order {level}")

            logger.info(f"\n=== DCA Order Summary ===")
            logger.info(f"Total orders placed: {len(orders)}")
            logger.info("=======================")

            return orders

        except Exception as e:
            logger.error(f"Error in DCA order placement: {e}")
            return []

    def place_scaled_take_profit_orders(self, symbol: str, entry_price: float, quantity: float, side: str) -> List[Dict]:
        """Place multiple take-profit orders at different price levels"""
        orders = []

        try:
            for level, (tp_percentage, size_percentage) in enumerate(zip(TAKE_PROFIT_LEVELS, TAKE_PROFIT_DISTRIBUTION), 1):
                quantity_for_level = quantity * size_percentage

                # Calculate take profit price
                tp_price = entry_price * (1 + tp_percentage/100) if side == 'BUY' else entry_price * (1 - tp_percentage/100)

                if self.simulation_mode:
                    simulated_order = {
                        'orderId': f'SIM_TP_{level}',
                        'symbol': symbol,
                        'side': 'SELL' if side == 'BUY' else 'BUY',
                        'type': 'TAKE_PROFIT_LIMIT',
                        'quantity': quantity_for_level,
                        'price': tp_price
                    }
                    orders.append(simulated_order)
                    self.tp_orders[simulated_order['orderId']] = simulated_order
                    logger.info(f"SIMULATION: Take-profit {level} placed - Price: {tp_price:.2f}, Quantity: {quantity_for_level:.6f}")
                    continue

                try:
                    order = self.create_order(
                        symbol=symbol,
                        side='SELL' if side == 'BUY' else 'BUY',
                        type='TAKE_PROFIT_LIMIT',
                        timeInForce='GTC',
                        quantity=quantity_for_level,
                        price=tp_price,
                        stopPrice=tp_price
                    )

                    if order:
                        orders.append(order)
                        self.tp_orders[order['orderId']] = order
                        logger.info(f"Take-profit {level} placed - Price: {tp_price:.2f}, Quantity: {quantity_for_level:.6f}")
                    else:
                        logger.error(f"Failed to place take-profit order {level}")

                except Exception as e:
                    logger.error(f"Error placing take-profit order {level}: {e}")
                    continue

            return orders

        except Exception as e:
            logger.error(f"Error in take-profit order placement: {e}")
            return []

    def manage_swing_trade(self, symbol: str, support_price: float, resistance_price: float, quantity: float) -> bool:
        """Manage swing trading between support and resistance levels"""
        try:
            current_price = self.get_symbol_price(symbol)
            if not current_price:
                return False

            # Calculate position near support/resistance
            support_distance = (current_price - support_price) / support_price * 100
            resistance_distance = (resistance_price - current_price) / current_price * 100

            logger.info(f"Swing Analysis - Support Distance: {support_distance:.2f}%, Resistance Distance: {resistance_distance:.2f}%")

            orders = []
            if support_distance <= 1.0:  # Within 1% of support
                # Place buy order with take profit at mid-range
                mid_price = (resistance_price + support_price) / 2
                buy_order = self.place_order(
                    symbol=symbol,
                    side='BUY',
                    quantity=quantity,
                    take_profit=(mid_price/current_price - 1) * 100
                )
                if buy_order:
                    orders.append(buy_order)
                    logger.info(f"Swing buy order placed near support at {current_price}")

            elif resistance_distance <= 1.0:  # Within 1% of resistance
                # Place sell order with take profit at mid-range
                mid_price = (resistance_price + support_price) / 2
                sell_order = self.place_order(
                    symbol=symbol,
                    side='SELL',
                    quantity=quantity,
                    take_profit=(1 - mid_price/current_price) * 100
                )
                if sell_order:
                    orders.append(sell_order)
                    logger.info(f"Swing sell order placed near resistance at {current_price}")

            return len(orders) > 0

        except Exception as e:
            logger.error(f"Error managing swing trade: {e}")
            return False
    
    def get_historical_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Get historical klines/candlestick data"""
        try:
            if self.simulation_mode:
                logger.info(f"SIMULATION: Generating synthetic klines for {symbol}")
                now = int(time.time() * 1000)  # current timestamp in milliseconds
                klines = []

                # Generate more realistic price trend with higher volatility
                base_price = self.simulated_prices.get(symbol, self.simulated_prices['DEFAULT'])
                trend = np.random.choice(['up', 'down', 'sideways'])
                trend_strength = np.random.uniform(0.002, 0.005)  # Increased trend strength

                current_price = base_price

                # Ensure we generate exactly 'limit' number of samples
                for i in range(limit):
                    timestamp = now - ((limit - i) * 3600000)  # 1 hour intervals

                    # Add trend bias
                    if trend == 'up':
                        bias = trend_strength
                    elif trend == 'down':
                        bias = -trend_strength
                    else:
                        bias = np.random.normal(0, trend_strength)  # Random walk for sideways

                    # Add some randomness to prices with increased volatility
                    daily_return = np.random.normal(bias, 0.03)  # Increased from 0.02 to 0.03
                    current_price *= (1 + daily_return)

                    # Calculate OHLC with more volatile relationships
                    open_price = current_price * (1 + np.random.normal(0, 0.002))
                    high_price = max(open_price * (1 + abs(np.random.normal(0, 0.008))),
                                   current_price * (1 + abs(np.random.normal(0, 0.008))))
                    low_price = min(open_price * (1 - abs(np.random.normal(0, 0.008))),
                                  current_price * (1 - abs(np.random.normal(0, 0.008))))
                    close_price = current_price

                    # Generate realistic volume with stronger price-volume correlation
                    base_volume = abs(np.random.normal(1000, 500))  # Increased volume variation
                    volume = base_volume * (1 + abs(daily_return) * 15)  # Stronger volume reaction

                    kline = [
                        timestamp,                    # Open time
                        str(open_price),             # Open
                        str(high_price),             # High
                        str(low_price),              # Low
                        str(close_price),            # Close
                        str(volume),                 # Volume
                        timestamp + 3600000,         # Close time
                        str(volume * close_price),   # Quote asset volume
                        100,                         # Number of trades
                        str(volume * 0.6),           # Taker buy base asset volume
                        str(volume * close_price * 0.6),  # Taker buy quote asset volume
                        "0"                          # Ignore
                    ]
                    klines.append(kline)

                    # Change trend more frequently
                    if i % 15 == 0:  # Changed from 20 to 15 periods
                        trend = np.random.choice(['up', 'down', 'sideways'])
                        trend_strength = np.random.uniform(0.002, 0.005)

                logger.info(f"Generated {len(klines)} klines in simulation mode")
                logger.info(f"Time range: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(klines[0][0]/1000))} "
                          f"to {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(klines[-1][0]/1000))}")
                return klines

            if not self.client:
                logger.error("Binance client not initialized")
                return []

            # Get historical klines from Binance API
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            return klines if klines else []

        except Exception as e:
            logger.error(f"Error fetching historical klines: {e}")
            return []