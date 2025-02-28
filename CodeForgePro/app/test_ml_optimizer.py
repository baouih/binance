"""
Enhanced test script with market regime analysis testing
"""
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc
import matplotlib.pyplot as plt

from ml_optimizer import MLOptimizer
from data_processor import DataProcessor
from binance_api import BinanceAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_simulation.log')
    ]
)
logger = logging.getLogger(__name__)

def analyze_trading_performance(returns, positions, hedge_returns=None):
    """Analyze detailed trading performance including hedge positions"""
    try:
        returns = np.array(returns)
        positions = np.array(positions)

        # Include hedge returns if available
        if hedge_returns is not None:
            hedge_returns = np.array(hedge_returns)
            combined_returns = returns + hedge_returns
        else:
            combined_returns = returns

        # Calculate trade statistics
        position_changes = np.diff(positions)
        trades = position_changes != 0
        total_trades = np.sum(trades)

        # Adjust array sizes to match
        trade_returns = returns[1:][trades]  # Get returns for trades only
        winning_trades = np.sum(trade_returns > 0)
        losing_trades = np.sum(trade_returns < 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Calculate average wins and losses
        avg_win = np.mean(trade_returns[trade_returns > 0]) if len(trade_returns[trade_returns > 0]) > 0 else 0
        avg_loss = np.mean(trade_returns[trade_returns < 0]) if len(trade_returns[trade_returns < 0]) > 0 else 0
        profit_factor = -avg_win / avg_loss if avg_loss != 0 else float('inf')

        # Calculate hedged performance metrics if available
        if hedge_returns is not None:
            hedge_trades = hedge_returns != 0
            total_hedge_trades = np.sum(hedge_trades)
            hedge_win_rate = np.sum(hedge_returns > 0) / total_hedge_trades if total_hedge_trades > 0 else 0

            # Calculate correlation between main and hedge returns
            correlation = np.corrcoef(returns, hedge_returns)[0,1]

            hedge_metrics = {
                'total_hedge_trades': int(total_hedge_trades),
                'hedge_win_rate': float(hedge_win_rate),
                'hedge_correlation': float(correlation),
                'hedge_profit_factor': float(-np.mean(hedge_returns[hedge_returns > 0]) / 
                                              np.mean(hedge_returns[hedge_returns < 0]))
                                              if np.any(hedge_returns < 0) else float('inf')
            }
        else:
            hedge_metrics = {}

        # Calculate cumulative returns and drawdown
        cum_returns = (1 + combined_returns).cumprod() - 1
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = cum_returns - running_max

        # Performance metrics over different periods
        returns_series = pd.Series(combined_returns)
        daily_returns = returns_series.resample('D').sum() if isinstance(returns_series.index, pd.DatetimeIndex) else returns_series
        weekly_returns = returns_series.resample('W').sum() if isinstance(returns_series.index, pd.DatetimeIndex) else returns_series.rolling(5).sum()
        monthly_returns = returns_series.resample('M').sum() if isinstance(returns_series.index, pd.DatetimeIndex) else returns_series.rolling(21).sum()

        performance_metrics = {
            # Trade statistics
            'total_trades': int(total_trades),
            'winning_trades': int(winning_trades),
            'losing_trades': int(losing_trades),
            'win_rate': float(win_rate),
            'profit_factor': float(profit_factor),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'largest_win': float(np.max(trade_returns)) if len(trade_returns) > 0 else 0,
            'largest_loss': float(np.min(trade_returns)) if len(trade_returns) > 0 else 0,

            # Hedging metrics
            **hedge_metrics,

            # Daily performance
            'daily_win_rate': float((daily_returns > 0).mean()),
            'daily_return': float(daily_returns.mean()),
            'daily_volatility': float(daily_returns.std()),
            'daily_sharpe': float(daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0),

            # Weekly performance
            'weekly_win_rate': float((weekly_returns > 0).mean()),
            'weekly_return': float(weekly_returns.mean()),
            'weekly_volatility': float(weekly_returns.std()),
            'weekly_sharpe': float(weekly_returns.mean() / weekly_returns.std() if weekly_returns.std() > 0 else 0),

            # Monthly performance
            'monthly_win_rate': float((monthly_returns > 0).mean()),
            'monthly_return': float(monthly_returns.mean()),
            'monthly_volatility': float(monthly_returns.std()),
            'monthly_sharpe': float(monthly_returns.mean() / monthly_returns.std() if monthly_returns.std() > 0 else 0),

            # Risk metrics
            'max_drawdown': float(np.min(drawdown)) if len(drawdown) > 0 else 0,
            'avg_drawdown': float(np.mean(drawdown)) if len(drawdown) > 0 else 0,
            'drawdown_duration': int(np.sum(drawdown < 0)) if len(drawdown) > 0 else 0,
            'time_in_market': float(np.mean(positions != 0)),
            'win_loss_ratio': float(avg_win / -avg_loss) if avg_loss != 0 else float('inf'),

            # Time period
            'trading_days': len(returns),
            'annualized_return': float(np.prod(1 + combined_returns) ** (252/len(combined_returns)) - 1) if len(combined_returns) > 0 else 0,
            'annualized_volatility': float(np.std(combined_returns) * np.sqrt(252))
        }

        return performance_metrics

    except Exception as e:
        logger.error(f"Error analyzing performance: {e}")
        logger.exception("Detailed error traceback:")
        return None

def analyze_regime_performance(regime_performance):
    """Analyze detailed performance metrics for each market regime"""
    try:
        analysis = {}
        for regime, perf in regime_performance.items():
            trades = perf['trades']
            if not trades:
                continue

            # Calculate basic metrics
            total_trades = len(trades)
            wins = perf['wins']
            losses = perf['losses']
            win_rate = wins / total_trades if total_trades > 0 else 0

            # Calculate returns
            returns = [t['return'] for t in trades]
            avg_return = np.mean(returns)
            std_return = np.std(returns)

            # Calculate drawdown
            cum_returns = np.cumprod(1 + np.array(returns))
            peak = np.maximum.accumulate(cum_returns)
            drawdown = (cum_returns - peak) / peak
            max_drawdown = np.min(drawdown)

            # Calculate profit metrics
            winning_trades = [t for t in trades if t['return'] > 0]
            losing_trades = [t for t in trades if t['return'] < 0]
            avg_win = np.mean([t['return'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['return'] for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')

            # Store analysis
            analysis[regime] = {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_return': avg_return,
                'std_return': std_return,
                'sharpe_ratio': avg_return / std_return if std_return > 0 else 0,
                'max_drawdown': max_drawdown,
                'profit_factor': profit_factor,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'consistency': 1 - std_return / abs(avg_return) if avg_return != 0 else 0
            }

        return analysis

    except Exception as e:
        logger.error(f"Error analyzing regime performance: {e}")
        logger.exception("Detailed error traceback:")
        return None

def analyze_regime_transitions(regime_changes):
    """Analyze effectiveness of regime transitions"""
    try:
        if not regime_changes:
            return

        logger.info("\n=== Chi tiết chuyển đổi giai đoạn ===")
        for i, change in enumerate(regime_changes):
            duration_hours = change['duration'] * 4  # Assuming 4-hour intervals
            logger.info(f"\nChuyển đổi {i+1}:")
            logger.info(f"Từ: {change['from_regime']}")
            logger.info(f"Sang: {change['to_regime']}")
            logger.info(f"Thời gian duy trì: {duration_hours} giờ")
            logger.info(f"Thời điểm: {change['timestamp']}")

    except Exception as e:
        logger.error(f"Lỗi phân tích chuyển đổi giai đoạn: {e}")
        logger.exception("Chi tiết lỗi:")


async def test_ml_optimizer():
    """Test ML optimizer with comprehensive evaluation"""
    try:
        logger.info("=== Bắt đầu kiểm thử ML Optimizer ===")
        binance_client = BinanceAPI()
        binance_client.simulation_mode = True
        data_processor = DataProcessor(binance_client)
        ml_optimizer = MLOptimizer()

        # Get historical data with 10000 samples for training
        symbol = 'BTCUSDT'
        logger.info(f"Đang lấy dữ liệu huấn luyện cho {symbol}")
        df = data_processor.get_historical_data(symbol, '1d', limit=10000)

        if df is None or df.empty:
            logger.error("Không thể lấy dữ liệu lịch sử")
            return False

        # Train models
        logger.info("\nĐang huấn luyện mô hình ML...")
        success = ml_optimizer.train_model(df)
        if not success:
            logger.error("Không thể huấn luyện mô hình")
            return False

        # Get test data (200 samples)
        logger.info("\nĐang lấy dữ liệu kiểm thử...")
        test_data = data_processor.get_historical_data(symbol, '1d', limit=200)
        if test_data is not None:
            future_returns = test_data['close'].pct_change(periods=6).shift(-6)
            predictions = []
            positions = []
            signals = []
            hedge_returns = []  # Track hedge returns separately
            returns = [] # Initialize returns list
            cum_returns = [] # Initialize cumulative returns list
            cum_return = 0 # Initialize cumulative return

            # Track regime changes and strategy performance
            regime_changes = []
            regime_performance = {}
            current_regime = None
            regime_duration = 0

            # Generate predictions and log details
            logger.info("\n=== Bắt đầu mô phỏng giao dịch ===")
            for i in range(len(test_data) - 6):
                data_slice = test_data.iloc[max(0, i-50):i+1]

                # Calculate technical indicators
                logger.info(f"\n--- Phân tích chu kỳ {i+1} ---")
                data_slice = ml_optimizer.calculate_technical_indicators(data_slice)
                if data_slice is None:
                    logger.error("Không thể tính toán các chỉ báo kỹ thuật")
                    continue

                latest = data_slice.iloc[-1]

                # Detect market regime and track changes
                regime = ml_optimizer.regime_analyzer.detect_regime(data_slice)
                if regime != current_regime:
                    if current_regime:
                        regime_changes.append({
                            'from_regime': current_regime,
                            'to_regime': regime,
                            'duration': regime_duration,
                            'timestamp': pd.Timestamp.now()
                        })
                        logger.info(f"\nPhát hiện chuyển đổi giai đoạn: {current_regime} -> {regime}")
                        logger.info(f"Thời gian giai đoạn trước: {regime_duration} chu kỳ")

                    current_regime = regime
                    regime_duration = 0
                else:
                    regime_duration += 1

                # Initialize regime tracking if new
                if current_regime not in regime_performance:
                    regime_performance[current_regime] = {
                        'trades': [],
                        'wins': 0,
                        'losses': 0,
                        'duration': 0,
                        'transitions': 0
                    }

                # Generate prediction with regime-specific strategy
                logger.info("\n--- Phân tích tín hiệu ---")
                if i % 10 == 0:  # Every 10th period, force a strong signal for hedge testing
                    logger.info("Buộc tín hiệu mạnh để kiểm thử hedge...")
                    base_pred = ml_optimizer.predict_signal(data_slice)
                    pred = 0.9 if base_pred > 0.5 else 0.1  # Force very strong signal
                    logger.info(f"Dự đoán cơ bản: {base_pred:.4f}")
                    logger.info(f"Dự đoán ép: {pred:.4f}")
                else:
                    pred = ml_optimizer.predict_signal(data_slice)
                    logger.info(f"Dự đoán bình thường: {pred:.4f}")

                predictions.append(pred)

                # Simulate hedge returns
                hedge_return = 0
                if hasattr(ml_optimizer, 'hedge_positions'):
                    base_return = future_returns.iloc[i] if i < len(future_returns) else 0
                    hedge_return = -0.7 * base_return  # Stronger hedge effect
                    logger.info("\n--- Mô phỏng lợi nhuận Hedge ---")
                    logger.info(f"Lợi nhuận cơ bản: {base_return:.4%}")
                    logger.info(f"Lợi nhuận Hedge mô phỏng: {hedge_return:.4%}")
                hedge_returns.append(hedge_return)

                # Determine position based on prediction
                if pred > 0.75:  # Strong buy signal
                    positions.append(1)
                    signals.append('BUY')
                    logger.info("Quyết định: MUA MẠNH")
                elif pred < 0.25:  # Strong sell signal
                    positions.append(-1)
                    signals.append('SELL')
                    logger.info("Quyết định: BÁN MẠNH")
                else:
                    positions.append(0)
                    signals.append('HOLD')
                    logger.info("Quyết định: GIỮ")

                # Log active hedge positions
                if hasattr(ml_optimizer, 'hedge_positions'):
                    logger.info("\n--- Vị thế Hedge đang hoạt động ---")
                    if ml_optimizer.hedge_positions:
                        for pos in ml_optimizer.hedge_positions:
                            logger.info(f"Mã: {pos['symbol']}, Chiều: {pos['side']}, Khối lượng: {pos['size']:.2f}")
                    else:
                        logger.info("Không có vị thế Hedge đang hoạt động")

                # Simulate trading and track regime performance
                if len(future_returns) > i:
                    position = positions[i]
                    trade_return = position * future_returns.iloc[i]
                    returns.append(trade_return)
                    cum_return = (1 + cum_return) * (1 + trade_return) - 1
                    cum_returns.append(cum_return)

                    # Log trade details
                    if position != 0:
                        logger.info(f"\nGiao dịch {i+1}:")
                        logger.info(f"Tín hiệu: {signals[i]}")
                        logger.info(f"Vị thế: {position}")
                        logger.info(f"Lợi nhuận: {trade_return:.4%}")
                        logger.info(f"Lợi nhuận tích lũy: {cum_return:.4%}")

                        # Track performance by regime
                        trade_info = {
                            'return': trade_return,
                            'position': position,
                            'pnl': trade_return * position,
                            'cum_return': cum_return,
                            'signal_strength': abs(pred - 0.5) * 2,
                            'timestamp': pd.Timestamp.now()
                        }
                        regime_performance[current_regime]['trades'].append(trade_info)

                        if trade_return > 0:
                            regime_performance[current_regime]['wins'] += 1
                        else:
                            regime_performance[current_regime]['losses'] += 1

            # Add more test scenarios for regime switching
            logger.info("\n=== Kiểm thử các kịch bản cụ thể cho từng giai đoạn ===")

            # Simulate trending up scenario
            trend_up_data = test_data.copy()
            trend_up_data['close'] = trend_up_data['close'] * (1 + np.linspace(0, 0.2, len(trend_up_data)))
            trend_up_data['volume'] = trend_up_data['volume'] * 1.5  # Increased volume

            # Test prediction with trending up data
            trend_regime = ml_optimizer.regime_analyzer.detect_regime(trend_up_data)
            logger.info(f"\nKịch bản xu hướng tăng:")
            logger.info(f"Giai đoạn phát hiện: {trend_regime}")

            # Simulate volatile scenario
            volatile_data = test_data.copy()
            volatility = np.random.normal(0, 0.05, len(volatile_data))
            volatile_data['close'] = volatile_data['close'] * (1 + volatility)
            volatile_data['volume'] = volatile_data['volume'] * 2  # High volume

            # Test prediction with volatile data
            volatile_regime = ml_optimizer.regime_analyzer.detect_regime(volatile_data)
            logger.info(f"\nKịch bản biến động:")
            logger.info(f"Giai đoạn phát hiện: {volatile_regime}")

            # Simulate ranging scenario
            ranging_data = test_data.copy()
            range_pattern = np.sin(np.linspace(0, 4*np.pi, len(ranging_data))) * 0.05
            ranging_data['close'] = ranging_data['close'] * (1 + range_pattern)
            ranging_data['volume'] = ranging_data['volume'] * 0.8  # Lower volume

            # Test prediction with ranging data
            ranging_regime = ml_optimizer.regime_analyzer.detect_regime(ranging_data)
            logger.info(f"\nKịch bản dao động:")
            logger.info(f"Giai đoạn phát hiện: {ranging_regime}")


            # Analyze regime-specific performance
            regime_analysis = analyze_regime_performance(regime_performance)
            if regime_analysis:
                logger.info("\n=== Phân tích giai đoạn thị trường ===")
                for regime, metrics in regime_analysis.items():
                    logger.info(f"\nGiai đoạn: {regime}")
                    logger.info(f"Số lệnh: {metrics['total_trades']}")
                    logger.info(f"Tỷ lệ thắng: {metrics['win_rate']:.2%}")
                    logger.info(f"Lợi nhuận TB: {metrics['avg_return']:.2%}")
                    logger.info(f"Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
                    logger.info(f"Drawdown tối đa: {metrics['max_drawdown']:.2%}")
                    logger.info(f"Hệ số lợi nhuận: {metrics['profit_factor']:.2f}")
                    logger.info(f"Độ ổn định: {metrics['consistency']:.2f}")

            # Analyze regime transitions
            analyze_regime_transitions(regime_changes)

            # Log regime transitions
            if regime_changes:
                logger.info("\n=== Chuyển đổi giai đoạn ===")
                for change in regime_changes:
                    logger.info(f"\nTừ: {change['from_regime']}")
                    logger.info(f"Sang: {change['to_regime']}")
                    logger.info(f"Thời gian: {change['duration']} chu kỳ")
                    logger.info(f"Thời điểm: {change['timestamp']}")

            # Calculate overall performance metrics
            performance_metrics = analyze_trading_performance(returns, positions, hedge_returns)

            if performance_metrics:
                logger.info("\n=== Tổng kết hiệu suất chung ===")
                logger.info(f"Tổng số lệnh: {performance_metrics['total_trades']}")
                logger.info(f"Tỷ lệ thắng: {performance_metrics['win_rate']:.2%}")
                logger.info(f"Hệ số lợi nhuận: {performance_metrics['profit_factor']:.2f}")
                logger.info(f"Lợi nhuận TB khi thắng: {performance_metrics['avg_win']:.2%}")
                logger.info(f"Lợi nhuận TB khi thua: {performance_metrics['avg_loss']:.2%}")
                logger.info(f"Tỷ lệ thắng/thua: {performance_metrics['win_loss_ratio']:.2f}")
                logger.info(f"Drawdown tối đa: {performance_metrics['max_drawdown']:.2%}")
                logger.info(f"Lợi nhuận hàng năm: {performance_metrics['annualized_return']:.2%}")
                logger.info(f"Sharpe ratio hàng ngày: {performance_metrics['daily_sharpe']:.2f}")

                # Save summary to file
                logger.info("\nĐang lưu tóm tắt hiệu suất...")
                with open('trading_summary.log', 'w') as f:
                    f.write("=== Tóm tắt hiệu suất giao dịch ===\n\n")
                    # Overall metrics
                    f.write("Hiệu suất chung:\n")
                    for key, value in performance_metrics.items():
                        f.write(f"{key}: {value}\n")
                    f.write("\n")

                    # Regime-specific metrics
                    f.write("Hiệu suất theo giai đoạn thị trường:\n")
                    for regime, metrics in regime_analysis.items():
                        f.write(f"\n{regime}:\n")
                        for key, value in metrics.items():
                            f.write(f"  {key}: {value}\n")

                logger.info("Tóm tắt đã được lưu thành công")

            logger.info("\n=== Kiểm thử hoàn tất ===")
            return True

    except Exception as e:
        logger.error(f"Lỗi trong quá trình kiểm thử ML optimizer: {e}")
        logger.exception("Chi tiết lỗi:")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ml_optimizer())