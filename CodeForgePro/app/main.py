import logging
import os
import sys
from datetime import datetime, timedelta
import time

# Add app directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from config import (
    TRADING_SYMBOLS,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_FILE,
    LOG_TO_FILE,
    SIMULATION_MODE,
    SIMULATE_SIGNALS,
    BACKTEST_PERIOD
)
from binance_api import BinanceAPI
from data_processor import DataProcessor
from trading_strategy import TradingStrategy
from backtesting import Backtester
from grid_strategy import GridStrategy

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Add file handler if enabled
if LOG_TO_FILE:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)

def main():
    try:
        # Initialize components
        binance_client = BinanceAPI()
        data_processor = DataProcessor(binance_client)
        trading_strategy = TradingStrategy(binance_client, data_processor)
        grid_strategy = GridStrategy(binance_client, data_processor)  # Added grid strategy
        backtester = Backtester(data_processor, trading_strategy)

        logger.info("\n=== Auto Trading System Initialized ===")
        logger.info(f"Mode: {'Simulation' if SIMULATION_MODE else 'Live'}")
        logger.info(f"Forced Signals: {SIMULATE_SIGNALS if SIMULATION_MODE else 'None'}")
        logger.info(f"Trading Symbols: {TRADING_SYMBOLS}")
        logger.info("Strategies: Regular, Grid Trading")  # Added strategy info
        logger.info("=====================================")

        # Run backtesting first
        start_date = datetime.now() - timedelta(days=BACKTEST_PERIOD)  # Use config value
        for symbol in TRADING_SYMBOLS:
            logger.info(f"\n=== Starting Backtest for {symbol} ===")
            logger.info(f"Period: {start_date} to {datetime.now()}")

            metrics = backtester.run_backtest(symbol, start_date)

            if not metrics:
                logger.error(f"Failed to get backtest metrics for {symbol}")
                continue

            # Log detailed backtest metrics
            logger.info("\nDetailed Backtest Metrics:")
            for key, value in metrics.items():
                if isinstance(value, float):
                    logger.info(f"{key}: {value:.4f}")
                else:
                    logger.info(f"{key}: {value}")

            if not backtester.validate_strategy():
                logger.warning(f"Strategy validation failed for {symbol}, skipping live trading")
                logger.warning("Please check logs above for failing criteria")
                continue

            logger.info(f"Strategy validation passed for {symbol}, proceeding with live trading")

        while True:
            try:
                # Get account balance at the start of each cycle
                balance = binance_client.get_account_balance()
                if balance:
                    logger.info(f"\nCurrent USDT balance: {balance['free'].get('USDT', 0)}")

                for symbol in TRADING_SYMBOLS:
                    try:
                        logger.info(f"\n=== Processing {symbol} ===")
                        logger.info(f"Time: {datetime.now()}")

                        # Get current price and log it
                        current_price = binance_client.get_symbol_price(symbol)
                        if current_price:
                            logger.info(f"Current {symbol} price: {current_price}")

                        # Execute regular trading strategy
                        logger.info("\nAnalyzing market conditions for regular strategy...")
                        if trading_strategy.execute_signals(symbol):
                            logger.info(f"Regular trade executed for {symbol}")
                            logger.info("Check detailed signal analysis above")
                        else:
                            logger.info(f"No actionable signals for {symbol}")

                        # Execute grid trading strategy
                        logger.info("\nChecking grid trading conditions...")
                        if not grid_strategy.grids.get(symbol):
                            logger.info(f"Initializing grid trading for {symbol}")
                            if grid_strategy.initialize_grids(symbol):
                                logger.info("Grid trading initialized successfully")
                            else:
                                logger.warning("Failed to initialize grid trading")
                        else:
                            logger.info("Checking grid rebalancing...")
                            if grid_strategy.rebalance_grids(symbol):
                                logger.info("Grid rebalancing completed")
                            else:
                                logger.info("No rebalancing needed")

                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                        logger.exception("Detailed error traceback:")
                        continue

                # Sleep for 5 minutes before next iteration
                logger.info("\nWaiting for next iteration...")
                time.sleep(300)

            except Exception as e:
                logger.error(f"Error in trading cycle: {e}")
                logger.exception("Detailed error traceback:")
                time.sleep(60)
                continue

    except Exception as e:
        logger.error(f"Critical error in main loop: {e}")
        logger.exception("Detailed error traceback:")
        raise

if __name__ == "__main__":
    main()