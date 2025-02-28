import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from data_processor import DataProcessor
from trading_strategy import TradingStrategy
from config import (
    BACKTEST_PERIOD,
    COMMISSION_RATE,
    SLIPPAGE,
    METRICS_WINDOW,
    PROFIT_FACTOR_MIN,
    SHARPE_RATIO_MIN,
    MAX_DRAWDOWN_THRESHOLD,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    MIN_WIN_RATE
)

logger = logging.getLogger(__name__)

class Backtester:
    def __init__(self, data_processor: DataProcessor, trading_strategy: TradingStrategy):
        self.data_processor = data_processor
        self.trading_strategy = trading_strategy
        self.trades = []
        self.metrics = {}

    def run_backtest(self, symbol: str, start_date: datetime) -> Dict:
        """Run backtest for a symbol from start_date"""
        try:
            logger.info(f"\n=== Starting Backtest for {symbol} ===")
            logger.info(f"From: {start_date}")

            # Get historical data
            df = self.data_processor.get_historical_klines(
                symbol=symbol,
                interval='1h',
                limit=BACKTEST_PERIOD * 24  # Convert days to hours
            )

            if df is None or df.empty:
                logger.error("No historical data available for backtesting")
                return {}

            # Initialize tracking variables
            position = 0  # 1 for long, -1 for short, 0 for no position
            entry_price = 0
            pnl = []
            equity_curve = [10000]  # Start with $10,000
            max_equity = 10000
            drawdowns = []

            # Process each candle
            logger.info("Processing historical data...")
            trade_count = 0
            winning_trades = 0
            total_profit = 0
            total_loss = 0

            for i in range(len(df)-1):
                current_data = df.iloc[:i+1]
                current_price = current_data['close'].iloc[-1]

                # Log progress every 24 hours
                if i % 24 == 0:
                    logger.info(f"\nProcessing day {i//24 + 1}")
                    logger.info(f"Current price: {current_price:.2f}")
                    logger.info(f"Current position: {position}")
                    if position != 0:
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        logger.info(f"Open P&L: {pnl_pct:.2f}%")

                signals = self.trading_strategy.get_trading_signals(symbol)
                if any(signals.values()):
                    logger.info(f"\nSignals detected at price {current_price}:")
                    for k, v in signals.items():
                        if v:
                            logger.info(f"{k}: {v}")

                # Check for position entry
                if position == 0:
                    entry_signal = None
                    if signals.get('sma_crossover') == 'BUY' or signals.get('rsi') == 'BUY':
                        entry_signal = 'BUY'
                        position = 1
                        entry_price = current_price * (1 + SLIPPAGE)
                    elif signals.get('sma_crossover') == 'SELL' or signals.get('rsi') == 'SELL':
                        entry_signal = 'SELL'
                        position = -1
                        entry_price = current_price * (1 - SLIPPAGE)

                    if entry_signal:
                        trade_count += 1
                        logger.info(f"\nTrade #{trade_count}:")
                        logger.info(f"Signal: {entry_signal}")
                        logger.info(f"Price: {entry_price:.2f}")
                        logger.info(f"Active signals: {signals}")
                        self.trades.append({
                            'type': 'ENTRY',
                            'side': entry_signal,
                            'price': entry_price,
                            'timestamp': current_data.index[-1]
                        })

                # Check for position exit
                elif position != 0:
                    # Calculate current P&L
                    current_pnl = (current_price - entry_price) / entry_price if position == 1 else (entry_price - current_price) / entry_price

                    # Apply commission
                    current_pnl -= COMMISSION_RATE

                    # Check stop loss and take profit
                    stop_loss_hit = current_pnl < -STOP_LOSS_PCT/100
                    take_profit_hit = current_pnl > TAKE_PROFIT_PCT/100

                    # Exit signals
                    exit_signal = (
                        stop_loss_hit or 
                        take_profit_hit or
                        (position == 1 and signals.get('sma_crossover') == 'SELL') or
                        (position == -1 and signals.get('sma_crossover') == 'BUY')
                    )

                    if exit_signal:
                        logger.info(f"\nTrade #{trade_count} Exit:")
                        logger.info(f"Price: {current_price:.2f}")
                        logger.info(f"P&L: {current_pnl:.2%}")
                        logger.info(f"Reason: {'Stop Loss' if stop_loss_hit else 'Take Profit' if take_profit_hit else 'Signal'}")

                        # Track trade performance
                        if current_pnl > 0:
                            winning_trades += 1
                            total_profit += current_pnl
                        else:
                            total_loss -= current_pnl

                        pnl.append(current_pnl)
                        new_equity = equity_curve[-1] * (1 + current_pnl)
                        equity_curve.append(new_equity)
                        max_equity = max(max_equity, new_equity)
                        drawdown = (max_equity - new_equity) / max_equity * 100
                        drawdowns.append(drawdown)

                        self.trades.append({
                            'type': 'EXIT',
                            'side': 'SELL' if position == 1 else 'BUY',
                            'price': current_price,
                            'timestamp': current_data.index[-1],
                            'pnl': current_pnl
                        })

                        position = 0
                        entry_price = 0

            # Calculate performance metrics
            self.metrics = self.calculate_metrics(pnl, equity_curve, drawdowns)

            # Log detailed results
            logger.info("\n=== Backtest Results ===")
            logger.info(f"Period: {start_date} to {df.index[-1]}")
            logger.info(f"Total Days: {len(df)//24}")
            logger.info(f"Total Trades: {trade_count}")

            # Trade distribution and performance
            logger.info("\nTrade Performance:")
            logger.info(f"Winning Trades: {winning_trades}")
            logger.info(f"Losing Trades: {trade_count - winning_trades}")
            if trade_count > 0:
                logger.info(f"Win Rate: {(winning_trades/trade_count)*100:.1f}%")
                logger.info(f"Average Win: {(total_profit/winning_trades)*100:.2f}%" if winning_trades > 0 else "N/A")
                logger.info(f"Average Loss: {(total_loss/(trade_count-winning_trades))*100:.2f}%" if trade_count > winning_trades else "N/A")

            # Validation criteria
            logger.info("\nValidation Criteria:")
            logger.info(f"Profit Factor: {self.metrics['profit_factor']:.2f} (min: {PROFIT_FACTOR_MIN})")
            logger.info(f"Sharpe Ratio: {self.metrics['sharpe_ratio']:.2f} (min: {SHARPE_RATIO_MIN})")
            logger.info(f"Max Drawdown: {self.metrics['max_drawdown']:.1f}% (max: {MAX_DRAWDOWN_THRESHOLD}%)")
            logger.info(f"Win Rate: {self.metrics['win_rate']*100:.1f}% (min: {MIN_WIN_RATE*100}%)")
            logger.info("=====================")

            return self.metrics

        except Exception as e:
            logger.error(f"Error during backtesting: {e}")
            logger.exception("Detailed error traceback:")
            return {}

    def calculate_metrics(self, pnl: List[float], equity: List[float], drawdowns: List[float]) -> Dict:
        """Calculate comprehensive trading metrics"""
        try:
            # Basic metrics
            total_trades = len(pnl)
            winning_trades = len([p for p in pnl if p > 0])
            losing_trades = len([p for p in pnl if p < 0])

            metrics = {
                'total_trades': total_trades,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'max_drawdown': max(drawdowns) if drawdowns else 0,
                'final_equity': equity[-1] if equity else 0
            }

            # Advanced metrics
            if pnl:
                # Profit Factor
                gross_profits = sum([p for p in pnl if p > 0])
                gross_losses = abs(sum([p for p in pnl if p < 0]))
                metrics['profit_factor'] = gross_profits / gross_losses if gross_losses > 0 else float('inf')

                # Risk-adjusted returns with NaN handling
                returns = pd.Series(pnl).fillna(0)  # Replace NaN with 0
                metrics['sharpe_ratio'] = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() != 0 else 0
                metrics['sortino_ratio'] = (returns.mean() * 252) / (returns[returns < 0].std() * np.sqrt(252)) if len(returns[returns < 0]) > 0 else 0

                # Average trade metrics
                metrics['avg_win'] = sum([p for p in pnl if p > 0]) / winning_trades if winning_trades > 0 else 0
                metrics['avg_loss'] = sum([p for p in pnl if p < 0]) / losing_trades if losing_trades > 0 else 0
                metrics['avg_trade'] = sum(pnl) / total_trades if total_trades > 0 else 0

            logger.info("\n=== Detailed Metrics ===")
            logger.info(f"Win Rate: {metrics['win_rate']:.2%}")
            logger.info(f"Average Win: {metrics['avg_win']:.2%}")
            logger.info(f"Average Loss: {metrics['avg_loss']:.2%}")
            logger.info(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            logger.info(f"Sortino Ratio: {metrics['sortino_ratio']:.2f}")
            logger.info("=====================")

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            logger.exception("Detailed error traceback:")
            return {}

    def validate_strategy(self) -> bool:
        """Validate if the strategy meets minimum performance criteria"""
        if not self.metrics:
            logger.warning("No metrics available for validation")
            return False

        try:
            logger.info("\n=== Strategy Validation ===")
            logger.info(f"Total Trades: {len(self.trades)//2}")  # Added total trades count

            # Check minimum profit factor
            profit_factor = self.metrics.get('profit_factor', 0)
            logger.info(f"Profit Factor: {profit_factor:.2f} (min: {PROFIT_FACTOR_MIN})")
            if profit_factor < PROFIT_FACTOR_MIN:
                logger.warning(f"Profit factor {profit_factor:.2f} below minimum {PROFIT_FACTOR_MIN}")
                return False

            # Check minimum Sharpe ratio
            sharpe_ratio = self.metrics.get('sharpe_ratio', 0)
            logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f} (min: {SHARPE_RATIO_MIN})")
            if sharpe_ratio < SHARPE_RATIO_MIN:
                logger.warning(f"Sharpe ratio {sharpe_ratio:.2f} below minimum {SHARPE_RATIO_MIN}")
                return False

            # Check maximum drawdown
            max_drawdown = self.metrics.get('max_drawdown', 0)
            logger.info(f"Max Drawdown: {max_drawdown:.2f}% (max: {MAX_DRAWDOWN_THRESHOLD}%)")
            if max_drawdown > MAX_DRAWDOWN_THRESHOLD:
                logger.warning(f"Max drawdown {max_drawdown:.2f}% exceeds threshold {MAX_DRAWDOWN_THRESHOLD}%")
                return False

            # Check minimum win rate using config value
            win_rate = self.metrics.get('win_rate', 0)
            logger.info(f"Win Rate: {win_rate:.2%} (min: {MIN_WIN_RATE*100}%)")
            if win_rate < MIN_WIN_RATE:
                logger.warning(f"Win rate {win_rate:.2%} below minimum {MIN_WIN_RATE*100}%")
                return False

            # Added more detailed metrics
            logger.info(f"Average Win: {self.metrics.get('avg_win', 0):.2%}")
            logger.info(f"Average Loss: {self.metrics.get('avg_loss', 0):.2%}")
            logger.info(f"Maximum Win Streak: {self.metrics.get('max_win_streak', 0)}")
            logger.info(f"Maximum Loss Streak: {self.metrics.get('max_lose_streak', 0)}")
            logger.info(f"Sortino Ratio: {self.metrics.get('sortino_ratio', 0):.2f}")

            logger.info("Strategy validation passed all criteria")
            logger.info("===========================")
            return True

        except Exception as e:
            logger.error(f"Error validating strategy: {e}")
            logger.exception("Detailed error traceback:")
            return False