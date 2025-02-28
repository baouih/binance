import os
import sys
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add app directory to path for importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.ml_optimizer import MLOptimizer
from app.strategy import StrategyFactory, MLStrategy
from app.trading_bot import TradingBot

def test_ml_model_training():
    """Test training ML models with synthetic data"""
    # Initialize components with simulation mode
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    ml_optimizer = MLOptimizer()
    
    logger.info("Fetching historical data for BTCUSDT")
    df = data_processor.get_historical_data(
        symbol="BTCUSDT",
        interval="1h",
        lookback_days=30
    )
    
    # Prepare features for ML
    X, y = data_processor.prepare_features_for_ml(df)
    
    logger.info("\nTraining ML models...")
    ml_optimizer.train_models(X, y)
    
    # Test predictions
    logger.info("\nTesting predictions on recent data...")
    test_df = data_processor.get_historical_data(
        symbol="BTCUSDT",
        interval="1h",
        lookback_days=7
    )
    
    # Apply the model to generate predictions
    recent_data = test_df.tail(10)
    
    # Print analysis for a few periods
    for i in range(1, 10):
        period_data = test_df.iloc[:50+i]
        logger.info(f"\nAnalyzing period {i}:")
        logger.info(f"Close price: {period_data['close'].iloc[-1]}")
        
        # Print some key indicators
        if 'SMA_Ratio' in period_data.columns:
            logger.info(f"SMA_Ratio: {period_data['SMA_Ratio'].iloc[-1]}")
        else:
            logger.info(f"SMA_Ratio: N/A")
            
        if 'RSI' in period_data.columns:
            logger.info(f"RSI: {period_data['RSI'].iloc[-1]}")
            
        if 'MACD' in period_data.columns and 'MACD_Signal' in period_data.columns:
            macd_diff = period_data['MACD'].iloc[-1] - period_data['MACD_Signal'].iloc[-1]
            logger.info(f"MACD Diff: {macd_diff:.4f}")
            
        if 'Volume_Ratio' in period_data.columns:
            logger.info(f"Volume Ratio: {period_data['Volume_Ratio'].iloc[-1]}")
        
        # Get prediction
        features = period_data[ml_optimizer.features] if ml_optimizer.features else None
        if features is not None:
            prediction, probability = ml_optimizer.predict(features)
            logger.info(f"Signal probability: {probability[0]:.4f}")
            
            # Determine trading signal
            if prediction is not None:
                signal = prediction[0]
                if signal == 1:
                    decision = "BUY"
                elif signal == -1:
                    decision = "SELL"
                else:
                    decision = "HOLD"
                logger.info(f"Decision: {decision}")
            else:
                logger.info("No prediction available")
        else:
            logger.info("No features available for prediction")

def test_backtest():
    """Test backtesting functionality with ML strategy"""
    # Initialize components with simulation mode
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    ml_optimizer = MLOptimizer()
    
    # Get historical data
    df = data_processor.get_historical_data(
        symbol="BTCUSDT",
        interval="1h",
        lookback_days=30
    )
    
    # Prepare features for ML
    X, y = data_processor.prepare_features_for_ml(df)
    
    # Train ML models
    ml_optimizer.train_models(X, y)
    
    # Create ML strategy
    ml_strategy = StrategyFactory.create_strategy("ml", ml_optimizer=ml_optimizer, probability_threshold=0.6)
    
    # Create trading bot
    bot = TradingBot(
        binance_api=binance_api,
        data_processor=data_processor,
        strategy=ml_strategy,
        symbol="BTCUSDT",
        interval="1h",
        test_mode=True
    )
    
    # Run backtest
    logger.info("\nRunning backtest with ML strategy...")
    results, metrics, trades = bot.backtest(df, initial_balance=10000.0)
    
    # Display results
    logger.info("\nBacktest Results:")
    logger.info(f"Total Trades: {metrics['total_trades']}")
    logger.info(f"Winning Trades: {metrics['winning_trades']}")
    logger.info(f"Losing Trades: {metrics['losing_trades']}")
    logger.info(f"Win Rate: {metrics['win_rate']:.2%}")
    logger.info(f"Profit Factor: {metrics['profit_factor']:.2f}")
    logger.info(f"Total Profit: {metrics['profit_pct']:.2%}")
    logger.info(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
    
    # Plot equity curve
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(results.index, results['equity'])
        plt.title('Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Equity')
        plt.grid(True)
        plt.tight_layout()
        
        # Save the plot to a file
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        plt.savefig(os.path.join(output_dir, 'equity_curve.png'))
        logger.info(f"Equity curve saved to {os.path.join(output_dir, 'equity_curve.png')}")
        
    except Exception as e:
        logger.error(f"Error plotting equity curve: {str(e)}")

def test_strategy_combination():
    """Test combining multiple strategies"""
    # Initialize components with simulation mode
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Get historical data
    df = data_processor.get_historical_data(
        symbol="BTCUSDT",
        interval="1h",
        lookback_days=30
    )
    
    # Create individual strategies
    rsi_strategy = StrategyFactory.create_strategy("rsi", overbought=70, oversold=30)
    macd_strategy = StrategyFactory.create_strategy("macd")
    ema_strategy = StrategyFactory.create_strategy("ema_cross", short_period=9, long_period=21)
    
    # Create combined strategy
    combined_strategy = StrategyFactory.create_strategy(
        "combined",
        strategies=[rsi_strategy, macd_strategy, ema_strategy],
        weights=[0.4, 0.3, 0.3]
    )
    
    # Create trading bot with combined strategy
    bot = TradingBot(
        binance_api=binance_api,
        data_processor=data_processor,
        strategy=combined_strategy,
        symbol="BTCUSDT",
        interval="1h",
        test_mode=True
    )
    
    # Run backtest
    logger.info("\nRunning backtest with combined strategy...")
    results, metrics, trades = bot.backtest(df, initial_balance=10000.0)
    
    # Display results
    logger.info("\nCombined Strategy Backtest Results:")
    logger.info(f"Total Trades: {metrics['total_trades']}")
    logger.info(f"Winning Trades: {metrics['winning_trades']}")
    logger.info(f"Losing Trades: {metrics['losing_trades']}")
    logger.info(f"Win Rate: {metrics['win_rate']:.2%}")
    logger.info(f"Profit Factor: {metrics['profit_factor']:.2f}")
    logger.info(f"Total Profit: {metrics['profit_pct']:.2%}")

def test_all_strategies_comparison():
    """Compare performance of all available strategies"""
    # Initialize components with simulation mode
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    ml_optimizer = MLOptimizer()
    
    # Get historical data
    df = data_processor.get_historical_data(
        symbol="BTCUSDT",
        interval="1h",
        lookback_days=30
    )
    
    # Prepare features for ML
    X, y = data_processor.prepare_features_for_ml(df)
    
    # Train ML models
    ml_optimizer.train_models(X, y)
    
    # List of strategies to test
    strategies = [
        {"name": "RSI", "strategy": StrategyFactory.create_strategy("rsi")},
        {"name": "MACD", "strategy": StrategyFactory.create_strategy("macd")},
        {"name": "EMA Cross", "strategy": StrategyFactory.create_strategy("ema_cross")},
        {"name": "Bollinger Bands", "strategy": StrategyFactory.create_strategy("bbands")},
        {"name": "ML Strategy", "strategy": StrategyFactory.create_strategy("ml", ml_optimizer=ml_optimizer)}
    ]
    
    # Results storage
    results_summary = []
    
    # Test each strategy
    for strategy_info in strategies:
        logger.info(f"\nTesting {strategy_info['name']} strategy...")
        
        # Create trading bot
        bot = TradingBot(
            binance_api=binance_api,
            data_processor=data_processor,
            strategy=strategy_info["strategy"],
            symbol="BTCUSDT",
            interval="1h",
            test_mode=True
        )
        
        # Run backtest
        _, metrics, _ = bot.backtest(df, initial_balance=10000.0)
        
        # Store results
        results_summary.append({
            "Strategy": strategy_info["name"],
            "Total Trades": metrics["total_trades"],
            "Win Rate": metrics["win_rate"],
            "Profit %": metrics["profit_pct"],
            "Max Drawdown": metrics["max_drawdown"]
        })
    
    # Display results comparison
    logger.info("\nStrategy Performance Comparison:")
    results_df = pd.DataFrame(results_summary)
    logger.info("\n" + str(results_df))
    
    # Format percentages
    results_df["Win Rate"] = results_df["Win Rate"].apply(lambda x: f"{x:.2%}")
    results_df["Profit %"] = results_df["Profit %"].apply(lambda x: f"{x:.2%}")
    results_df["Max Drawdown"] = results_df["Max Drawdown"].apply(lambda x: f"{x:.2%}")
    
    # Save results to file
    try:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        results_file = os.path.join(output_dir, 'strategy_comparison.csv')
        results_df.to_csv(results_file, index=False)
        logger.info(f"Strategy comparison saved to {results_file}")
    except Exception as e:
        logger.error(f"Error saving strategy comparison: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting ML Optimizer tests")
    
    # Run tests
    test_ml_model_training()
    test_backtest()
    test_strategy_combination()
    test_all_strategies_comparison()
    
    logger.info("All tests completed")
