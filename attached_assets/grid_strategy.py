"""
Grid trading strategy implementation with DCA support.
"""
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

from binance_api import BinanceAPI
from data_processor import DataProcessor
from config import (
    GRID_LEVELS,
    GRID_SPREAD,
    GRID_SIZE,
    GRID_REBALANCE_THRESHOLD,
    MIN_PROFIT_PER_GRID,
    DCA_LEVELS,
    DCA_PRICE_DEVIATION,
    DCA_VOLUME_SCALE
)

logger = logging.getLogger(__name__)

class GridStrategy:
    def __init__(self, binance_client: BinanceAPI, data_processor: DataProcessor):
        """Initialize grid trading strategy"""
        self.client = binance_client
        self.data_processor = data_processor
        self.grids = {}  # Store active grids per symbol

    def calculate_grid_levels(self, symbol: str, base_price: float) -> List[Dict]:
        """
        Calculate grid levels around the current price with DCA support
        Returns list of grid levels with buy/sell orders
        """
        try:
            logger.info(f"\n=== Calculating Grid Levels for {symbol} ===")
            logger.info(f"Base Price: {base_price}")

            # Calculate price range for grids
            grid_range = base_price * GRID_SPREAD
            min_price = base_price - grid_range/2
            max_price = base_price + grid_range/2

            # Generate grid price levels
            grid_step = grid_range / (GRID_LEVELS - 1)
            price_levels = np.linspace(min_price, max_price, GRID_LEVELS)

            grids = []
            for i, price in enumerate(price_levels):
                grid = {
                    'level': i,
                    'price': price,
                    'type': 'BUY' if price < base_price else 'SELL',
                    'quantity': GRID_SIZE / price,  # Convert USDT amount to asset quantity
                    'status': 'PENDING'
                }
                grids.append(grid)

                logger.info(f"\nGrid {i}:")
                logger.info(f"Price: {price:.2f}")
                logger.info(f"Type: {grid['type']}")
                logger.info(f"Quantity: {grid['quantity']:.6f}")

            return grids

        except Exception as e:
            logger.error(f"Error calculating grid levels: {e}")
            logger.exception("Detailed error traceback:")
            return []

    def initialize_grids(self, symbol: str) -> bool:
        """
        Initialize grid trading for a symbol with DCA support
        Returns True if grids were successfully created
        """
        try:
            # Get current market price
            current_price = self.client.get_symbol_price(symbol)
            if not current_price:
                logger.error("Failed to get current price")
                return False

            logger.info(f"\n=== Initializing Grids for {symbol} ===")
            logger.info(f"Current Price: {current_price}")

            # Calculate grid levels
            grids = self.calculate_grid_levels(symbol, current_price)
            if not grids:
                logger.error("Failed to calculate grid levels")
                return False

            # Place initial orders
            active_grids = []
            for grid in grids:
                # Place limit order
                order = self.client.create_order(
                    symbol=symbol,
                    side=grid['type'],
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=grid['quantity'],
                    price=grid['price']
                )

                if order:
                    grid['order_id'] = order.get('orderId')
                    grid['status'] = 'ACTIVE'
                    active_grids.append(grid)
                    logger.info(f"Placed {grid['type']} order at {grid['price']}")
                else:
                    logger.warning(f"Failed to place order for grid {grid['level']}")

            # Store active grids
            if active_grids:
                self.grids[symbol] = active_grids
                logger.info(f"Successfully initialized {len(active_grids)} grids")
                return True

            return False

        except Exception as e:
            logger.error(f"Error initializing grids: {e}")
            logger.exception("Detailed error traceback:")
            return False

    def rebalance_grids(self, symbol: str) -> bool:
        """
        Rebalance grid levels based on current price with DCA support
        Returns True if rebalancing was successful
        """
        try:
            if symbol not in self.grids:
                logger.warning(f"No active grids for {symbol}")
                return False

            current_price = self.client.get_symbol_price(symbol)
            if not current_price:
                logger.error("Failed to get current price")
                return False

            logger.info(f"\n=== Rebalancing Grids for {symbol} ===")
            logger.info(f"Current Price: {current_price}")

            # Check if rebalancing is needed
            grid_center = sum(g['price'] for g in self.grids[symbol]) / len(self.grids[symbol])
            price_deviation = abs(current_price - grid_center) / grid_center

            if price_deviation < GRID_REBALANCE_THRESHOLD:
                logger.info("Price deviation within threshold, no rebalancing needed")
                return True

            logger.info(f"Price deviation: {price_deviation:.2%}")
            logger.info("Rebalancing required")

            # Cancel existing orders
            for grid in self.grids[symbol]:
                if grid['status'] == 'ACTIVE':
                    if self.client.cancel_order(symbol, grid['order_id']):
                        logger.info(f"Cancelled order {grid['order_id']}")
                    else:
                        logger.warning(f"Failed to cancel order {grid['order_id']}")

            # Calculate new grid levels
            new_grids = self.calculate_grid_levels(symbol, current_price)
            if not new_grids:
                logger.error("Failed to calculate new grid levels")
                return False

            # Place new orders
            active_grids = []
            for grid in new_grids:
                # Add DCA scaling for buy orders
                if grid['type'] == 'BUY':
                    dca_quantity = self.calculate_dca_quantity(grid['quantity'], grid['level'])
                    grid['quantity'] = dca_quantity

                order = self.client.create_order(
                    symbol=symbol,
                    side=grid['type'],
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=grid['quantity'],
                    price=grid['price']
                )

                if order:
                    grid['order_id'] = order.get('orderId')
                    grid['status'] = 'ACTIVE'
                    active_grids.append(grid)
                    logger.info(f"Placed new {grid['type']} order at {grid['price']}")
                else:
                    logger.warning(f"Failed to place new order for grid {grid['level']}")

            # Update stored grids
            if active_grids:
                self.grids[symbol] = active_grids
                logger.info(f"Successfully rebalanced {len(active_grids)} grids")
                return True

            return False

        except Exception as e:
            logger.error(f"Error rebalancing grids: {e}")
            logger.exception("Detailed error traceback:")
            return False

    def calculate_dca_quantity(self, base_quantity: float, grid_level: int) -> float:
        """
        Calculate DCA quantity based on grid level
        Returns scaled quantity for DCA orders
        """
        try:
            # Only scale quantity for lower grid levels (buy orders)
            if grid_level >= len(DCA_LEVELS):
                return base_quantity

            # Calculate scale factor based on grid level
            scale_factor = DCA_VOLUME_SCALE ** DCA_LEVELS[grid_level]

            # Scale quantity
            scaled_quantity = base_quantity * scale_factor

            logger.info(f"\nDCA Quantity Calculation:")
            logger.info(f"Base Quantity: {base_quantity:.6f}")
            logger.info(f"Grid Level: {grid_level}")
            logger.info(f"Scale Factor: {scale_factor:.2f}")
            logger.info(f"Scaled Quantity: {scaled_quantity:.6f}")

            return scaled_quantity

        except Exception as e:
            logger.error(f"Error calculating DCA quantity: {e}")
            logger.exception("Detailed error traceback:")
            return base_quantity

    def handle_grid_execution(self, symbol: str, order_id: str) -> bool:
        """
        Handle executed grid orders and place new orders with DCA support
        Returns True if handled successfully
        """
        try:
            if symbol not in self.grids:
                logger.warning(f"No active grids for {symbol}")
                return False

            # Find executed grid
            executed_grid = None
            for grid in self.grids[symbol]:
                if grid['order_id'] == order_id:
                    executed_grid = grid
                    break

            if not executed_grid:
                logger.warning(f"Order {order_id} not found in active grids")
                return False

            logger.info(f"\n=== Handling Grid Execution for {symbol} ===")
            logger.info(f"Executed grid level: {executed_grid['level']}")
            logger.info(f"Executed price: {executed_grid['price']}")

            # Place opposite order
            new_type = 'SELL' if executed_grid['type'] == 'BUY' else 'BUY'
            new_price = executed_grid['price'] * (1 + MIN_PROFIT_PER_GRID if new_type == 'SELL' else 1 - MIN_PROFIT_PER_GRID)

            # Apply DCA scaling for new buy orders
            new_quantity = executed_grid['quantity']
            if new_type == 'BUY':
                new_quantity = self.calculate_dca_quantity(executed_grid['quantity'], executed_grid['level'])

            order = self.client.create_order(
                symbol=symbol,
                side=new_type,
                type='LIMIT',
                timeInForce='GTC',
                quantity=new_quantity,
                price=new_price
            )

            if order:
                executed_grid['type'] = new_type
                executed_grid['price'] = new_price
                executed_grid['quantity'] = new_quantity
                executed_grid['order_id'] = order.get('orderId')
                logger.info(f"Placed new {new_type} order at {new_price}")
                return True

            logger.warning("Failed to place new order after execution")
            return False

        except Exception as e:
            logger.error(f"Error handling grid execution: {e}")
            logger.exception("Detailed error traceback:")
            return False