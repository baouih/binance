import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .config import (
    METRICS_WINDOW,
    PROFIT_FACTOR_MIN,
    SHARPE_RATIO_MIN,
    MAX_DRAWDOWN_THRESHOLD
)

logger = logging.getLogger(__name__)

class PerformanceTracker:
    def __init__(self):
        self.trades = []
        self.daily_stats = {}
        self.metrics = {}
        
    def add_trade(self, trade: Dict):
        """Add a new trade to tracking"""
        try:
            trade['timestamp'] = datetime.now()
            self.trades.append(trade)
            self._update_daily_stats(trade)
            logger.info(f"Added trade: {trade}")
        except Exception as e:
            logger.error(f"Error adding trade: {e}")

    def _update_daily_stats(self, trade: Dict):
        """Update daily trading statistics"""
        try:
            date = trade['timestamp'].date()
            if date not in self.daily_stats:
                self.daily_stats[date] = {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'profit': 0,
                    'max_drawdown': 0
                }
            
            stats = self.daily_stats[date]
            stats['trades'] += 1
            
            if trade.get('pnl', 0) > 0:
                stats['wins'] += 1
                stats['profit'] += trade['pnl']
            else:
                stats['losses'] += 1
                stats['profit'] -= abs(trade.get('pnl', 0))
                
            # Update max drawdown
            if stats['profit'] < stats['max_drawdown']:
                stats['max_drawdown'] = stats['profit']
                
        except Exception as e:
            logger.error(f"Error updating daily stats: {e}")

    def calculate_metrics(self, window_days: int = METRICS_WINDOW) -> Dict:
        """Calculate comprehensive performance metrics"""
        try:
            if not self.trades:
                return {}

            # Convert trades to DataFrame for analysis
            df = pd.DataFrame(self.trades)
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            
            # Filter for window period
            start_date = datetime.now().date() - timedelta(days=window_days)
            df = df[df['date'] >= start_date]
            
            if df.empty:
                return {}

            # Calculate basic metrics
            total_trades = len(df)
            winning_trades = len(df[df['pnl'] > 0])
            losing_trades = len(df[df['pnl'] < 0])
            
            metrics = {
                'total_trades': total_trades,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'profit_factor': abs(df[df['pnl'] > 0]['pnl'].sum() / df[df['pnl'] < 0]['pnl'].sum()) if df[df['pnl'] < 0]['pnl'].sum() != 0 else float('inf'),
                'avg_win': df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0,
                'avg_loss': df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0,
                'largest_win': df['pnl'].max(),
                'largest_loss': df['pnl'].min(),
                'avg_trade_duration': (df['exit_time'] - df['entry_time']).mean().total_seconds() / 3600  # in hours
            }
            
            # Calculate advanced metrics
            returns = df.groupby('date')['pnl'].sum()
            metrics.update({
                'sharpe_ratio': self._calculate_sharpe_ratio(returns),
                'sortino_ratio': self._calculate_sortino_ratio(returns),
                'max_drawdown': self._calculate_max_drawdown(returns),
                'win_streak': self._calculate_max_streak(df['pnl'] > 0),
                'lose_streak': self._calculate_max_streak(df['pnl'] < 0)
            })
            
            # Store metrics
            self.metrics = metrics
            
            # Log detailed metrics
            logger.info("=== Performance Metrics ===")
            for key, value in metrics.items():
                if isinstance(value, float):
                    logger.info(f"{key}: {value:.2f}")
                else:
                    logger.info(f"{key}: {value}")
            logger.info("=========================")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {}

    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio"""
        try:
            if returns.empty:
                return 0
            return (returns.mean() * 252) / (returns.std() * np.sqrt(252))
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0

    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio"""
        try:
            if returns.empty:
                return 0
            negative_returns = returns[returns < 0]
            if negative_returns.empty:
                return float('inf')
            return (returns.mean() * 252) / (negative_returns.std() * np.sqrt(252))
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        try:
            if returns.empty:
                return 0
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdowns = (cumulative - rolling_max) / rolling_max
            return abs(drawdowns.min())
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0

    def _calculate_max_streak(self, condition: pd.Series) -> int:
        """Calculate maximum streak of True values"""
        try:
            streak = 0
            max_streak = 0
            for value in condition:
                if value:
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            return max_streak
        except Exception as e:
            logger.error(f"Error calculating max streak: {e}")
            return 0

    def generate_report(self) -> str:
        """Generate a detailed performance report"""
        try:
            if not self.metrics:
                self.calculate_metrics()
                
            report = [
                "=== Trading Performance Report ===",
                f"Period: Last {METRICS_WINDOW} days",
                f"Total Trades: {self.metrics.get('total_trades', 0)}",
                f"Win Rate: {self.metrics.get('win_rate', 0):.2%}",
                f"Profit Factor: {self.metrics.get('profit_factor', 0):.2f}",
                f"Sharpe Ratio: {self.metrics.get('sharpe_ratio', 0):.2f}",
                f"Max Drawdown: {self.metrics.get('max_drawdown', 0):.2%}",
                f"Average Win: {self.metrics.get('avg_win', 0):.2%}",
                f"Average Loss: {self.metrics.get('avg_loss', 0):.2%}",
                f"Longest Win Streak: {self.metrics.get('win_streak', 0)}",
                f"Longest Lose Streak: {self.metrics.get('lose_streak', 0)}",
                f"Average Trade Duration: {self.metrics.get('avg_trade_duration', 0):.1f} hours",
                "==============================="
            ]
            
            # Add daily breakdown
            report.extend([
                "\nDaily Performance:",
                "----------------"
            ])
            
            for date, stats in sorted(self.daily_stats.items(), reverse=True):
                report.append(
                    f"{date}: {stats['trades']} trades, "
                    f"W/L: {stats['wins']}/{stats['losses']}, "
                    f"P/L: {stats['profit']:.2%}, "
                    f"Max DD: {stats['max_drawdown']:.2%}"
                )
                
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return "Error generating performance report"

    def validate_performance(self) -> bool:
        """Validate if performance meets minimum criteria"""
        try:
            if not self.metrics:
                self.calculate_metrics()
                
            if self.metrics.get('profit_factor', 0) < PROFIT_FACTOR_MIN:
                logger.warning(f"Profit factor {self.metrics['profit_factor']:.2f} below minimum {PROFIT_FACTOR_MIN}")
                return False
                
            if self.metrics.get('sharpe_ratio', 0) < SHARPE_RATIO_MIN:
                logger.warning(f"Sharpe ratio {self.metrics['sharpe_ratio']:.2f} below minimum {SHARPE_RATIO_MIN}")
                return False
                
            if self.metrics.get('max_drawdown', 0) > MAX_DRAWDOWN_THRESHOLD:
                logger.warning(f"Max drawdown {self.metrics['max_drawdown']:.2%} exceeds threshold {MAX_DRAWDOWN_THRESHOLD}%")
                return False
                
            logger.info("Performance validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error validating performance: {e}")
            return False
