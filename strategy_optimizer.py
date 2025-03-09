#!/usr/bin/env python3
"""
Công cụ tối ưu hóa chiến lược giao dịch tự động
Sử dụng Grid Search để tìm các tham số tối ưu cho mỗi chiến lược
"""
import os
import logging
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import argparse
import json
import itertools
from tabulate import tabulate
import matplotlib.pyplot as plt

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('strategy_optimizer')

# Import các module từ ứng dụng
from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.strategy import (RSIStrategy, MACDStrategy, EMACrossStrategy, 
                         BBandsStrategy, CombinedStrategy)
from app.trading_bot import TradingBot
from app.storage import Storage

class StrategyOptimizer:
    def __init__(self, symbol='BTCUSDT', interval='1h', lookback_days=90):
        """
        Khởi tạo công cụ tối ưu hóa chiến lược
        
        Args:
            symbol (str): Cặp giao dịch cần tối ưu hóa
            interval (str): Khung thời gian
            lookback_days (int): Số ngày dữ liệu lịch sử
        """
        self.symbol = symbol
        self.interval = interval
        self.lookback_days = lookback_days
        
        # Khởi tạo API và Data Processor
        self.binance_api = BinanceAPI(simulation_mode=True)
        self.data_processor = DataProcessor(self.binance_api, simulation_mode=True)
        
        # Lấy dữ liệu lịch sử
        self.historical_data = self.data_processor.get_historical_data(
            symbol=self.symbol,
            interval=self.interval,
            lookback_days=self.lookback_days
        )
        
        if self.historical_data is None or self.historical_data.empty:
            logger.error(f"Không thể lấy dữ liệu cho {symbol} với {interval}")
            self.historical_data = None
        else:
            logger.info(f"Đã lấy {len(self.historical_data)} mẫu dữ liệu cho {symbol} với {interval}")
            
        # Định nghĩa không gian tham số tối ưu hóa cho mỗi chiến lược
        self.param_spaces = {
            'RSI': {
                'overbought': [65, 70, 75, 80],
                'oversold': [20, 25, 30, 35]
            },
            'MACD': {
                'fast_period': [8, 12, 16],
                'slow_period': [21, 26, 30],
                'signal_period': [7, 9, 11]
            },
            'EMA_Cross': {
                'short_period': [5, 9, 13, 17],
                'long_period': [21, 34, 50, 100]
            },
            'Bollinger_Bands': {
                'window': [14, 20, 26],
                'num_std_dev': [1.5, 2.0, 2.5, 3.0]
            }
        }
        
        # Kết quả tối ưu hóa
        self.optimization_results = {}
        
    def optimize_all_strategies(self):
        """Tối ưu hóa tất cả các chiến lược"""
        if self.historical_data is None:
            logger.error("Không có dữ liệu để tối ưu hóa")
            return
        
        logger.info("=== BẮT ĐẦU TỐI ƯU HÓA CHIẾN LƯỢC ===")
        
        # Tối ưu RSI
        logger.info("1. TỐI ƯU HÓA CHIẾN LƯỢC RSI")
        self.optimize_rsi()
        
        # Tối ưu MACD
        logger.info("2. TỐI ƯU HÓA CHIẾN LƯỢC MACD")
        self.optimize_macd()
        
        # Tối ưu EMA Crossover
        logger.info("3. TỐI ƯU HÓA CHIẾN LƯỢC EMA CROSSOVER")
        self.optimize_ema_cross()
        
        # Tối ưu Bollinger Bands
        logger.info("4. TỐI ƯU HÓA CHIẾN LƯỢC BOLLINGER BANDS")
        self.optimize_bbands()
        
        # Tối ưu Combined Strategy
        logger.info("5. TỐI ƯU HÓA CHIẾN LƯỢC KẾT HỢP")
        self.optimize_combined()
        
        # Tạo báo cáo
        self.generate_report()
    
    def optimize_rsi(self):
        """Tối ưu hóa chiến lược RSI"""
        param_grid = list(itertools.product(
            self.param_spaces['RSI']['overbought'],
            self.param_spaces['RSI']['oversold']
        ))
        
        results = []
        
        for overbought, oversold in param_grid:
            # Đảm bảo overbought > oversold
            if overbought <= oversold:
                continue
                
            strategy = RSIStrategy(overbought=overbought, oversold=oversold)
            
            bot = TradingBot(
                binance_api=self.binance_api,
                data_processor=self.data_processor,
                strategy=strategy,
                symbol=self.symbol,
                interval=self.interval,
                test_mode=True
            )
            
            # Chạy backtest
            backtest_results, metrics = bot.backtest(self.historical_data, initial_balance=10000)
            
            # Lưu kết quả
            results.append({
                'overbought': overbought,
                'oversold': oversold,
                'profit': metrics.get('profit_pct', 0),
                'win_rate': metrics.get('win_rate', 0),
                'trade_count': metrics.get('total_trades', 0),
                'metrics': metrics
            })
            
            logger.info(f"RSI (overbought={overbought}, oversold={oversold}): "
                       f"Profit={metrics.get('profit_pct', 0):.2%}, Win Rate={metrics.get('win_rate', 0):.2%}, "
                       f"Trades={metrics.get('total_trades', 0)}")
        
        # Sắp xếp theo lợi nhuận
        results.sort(key=lambda x: x['profit'], reverse=True)
        
        # Lưu kết quả tối ưu
        if results:
            best = results[0]
            self.optimization_results['RSI'] = {
                'best_params': {
                    'overbought': best['overbought'],
                    'oversold': best['oversold']
                },
                'performance': {
                    'profit': best['profit'],
                    'win_rate': best['win_rate'],
                    'trade_count': best['trade_count']
                },
                'all_results': results
            }
            
            logger.info(f"RSI tối ưu: overbought={best['overbought']}, oversold={best['oversold']}, "
                       f"Profit={best['profit']:.2%}, Win Rate={best['win_rate']:.2%}")
    
    def optimize_macd(self):
        """Tối ưu hóa chiến lược MACD"""
        param_grid = list(itertools.product(
            self.param_spaces['MACD']['fast_period'],
            self.param_spaces['MACD']['slow_period'],
            self.param_spaces['MACD']['signal_period']
        ))
        
        results = []
        
        for fast_period, slow_period, signal_period in param_grid:
            # Đảm bảo fast_period < slow_period
            if fast_period >= slow_period:
                continue
                
            # MACD không cần tham số, sử dụng tham số mặc định
            strategy = MACDStrategy()
            
            bot = TradingBot(
                binance_api=self.binance_api,
                data_processor=self.data_processor,
                strategy=strategy,
                symbol=self.symbol,
                interval=self.interval,
                test_mode=True
            )
            
            # Chạy backtest
            backtest_results, metrics = bot.backtest(self.historical_data, initial_balance=10000)
            
            # Lưu kết quả
            results.append({
                'fast_period': fast_period,
                'slow_period': slow_period,
                'signal_period': signal_period,
                'profit': metrics.get('profit_pct', 0),
                'win_rate': metrics.get('win_rate', 0),
                'trade_count': metrics.get('total_trades', 0),
                'metrics': metrics
            })
            
            logger.info(f"MACD (fast={fast_period}, slow={slow_period}, signal={signal_period}): "
                       f"Profit={metrics.get('profit_pct', 0):.2%}, Win Rate={metrics.get('win_rate', 0):.2%}, "
                       f"Trades={metrics.get('total_trades', 0)}")
        
        # Sắp xếp theo lợi nhuận
        results.sort(key=lambda x: x['profit'], reverse=True)
        
        # Lưu kết quả tối ưu
        if results:
            best = results[0]
            self.optimization_results['MACD'] = {
                'best_params': {
                    'fast_period': best['fast_period'],
                    'slow_period': best['slow_period'],
                    'signal_period': best['signal_period']
                },
                'performance': {
                    'profit': best['profit'],
                    'win_rate': best['win_rate'],
                    'trade_count': best['trade_count']
                },
                'all_results': results
            }
            
            logger.info(f"MACD tối ưu: fast={best['fast_period']}, slow={best['slow_period']}, signal={best['signal_period']}, "
                       f"Profit={best['profit']:.2%}, Win Rate={best['win_rate']:.2%}")
    
    def optimize_ema_cross(self):
        """Tối ưu hóa chiến lược EMA Crossover"""
        param_grid = list(itertools.product(
            self.param_spaces['EMA_Cross']['short_period'],
            self.param_spaces['EMA_Cross']['long_period']
        ))
        
        results = []
        
        for short_period, long_period in param_grid:
            # Đảm bảo short_period < long_period
            if short_period >= long_period:
                continue
                
            strategy = EMACrossStrategy(short_period=short_period, long_period=long_period)
            
            bot = TradingBot(
                binance_api=self.binance_api,
                data_processor=self.data_processor,
                strategy=strategy,
                symbol=self.symbol,
                interval=self.interval,
                test_mode=True
            )
            
            # Chạy backtest
            backtest_results, metrics = bot.backtest(self.historical_data, initial_balance=10000)
            
            # Lưu kết quả
            results.append({
                'short_period': short_period,
                'long_period': long_period,
                'profit': metrics.get('profit_pct', 0),
                'win_rate': metrics.get('win_rate', 0),
                'trade_count': metrics.get('total_trades', 0),
                'metrics': metrics
            })
            
            logger.info(f"EMA Cross (short={short_period}, long={long_period}): "
                       f"Profit={metrics.get('profit_pct', 0):.2%}, Win Rate={metrics.get('win_rate', 0):.2%}, "
                       f"Trades={metrics.get('total_trades', 0)}")
        
        # Sắp xếp theo lợi nhuận
        results.sort(key=lambda x: x['profit'], reverse=True)
        
        # Lưu kết quả tối ưu
        if results:
            best = results[0]
            self.optimization_results['EMA_Cross'] = {
                'best_params': {
                    'short_period': best['short_period'],
                    'long_period': best['long_period']
                },
                'performance': {
                    'profit': best['profit'],
                    'win_rate': best['win_rate'],
                    'trade_count': best['trade_count']
                },
                'all_results': results
            }
            
            logger.info(f"EMA Cross tối ưu: short={best['short_period']}, long={best['long_period']}, "
                       f"Profit={best['profit']:.2%}, Win Rate={best['win_rate']:.2%}")
    
    def optimize_bbands(self):
        """Tối ưu hóa chiến lược Bollinger Bands"""
        param_grid = list(itertools.product(
            self.param_spaces['Bollinger_Bands']['window'],
            self.param_spaces['Bollinger_Bands']['num_std_dev']
        ))
        
        results = []
        
        for window, num_std_dev in param_grid:
            strategy = BBandsStrategy(deviation_multiplier=num_std_dev)
            
            bot = TradingBot(
                binance_api=self.binance_api,
                data_processor=self.data_processor,
                strategy=strategy,
                symbol=self.symbol,
                interval=self.interval,
                test_mode=True
            )
            
            # Chạy backtest
            backtest_results, metrics = bot.backtest(self.historical_data, initial_balance=10000)
            
            # Lưu kết quả
            results.append({
                'window': window,
                'num_std_dev': num_std_dev,
                'profit': metrics.get('profit_pct', 0),
                'win_rate': metrics.get('win_rate', 0),
                'trade_count': metrics.get('total_trades', 0),
                'metrics': metrics
            })
            
            logger.info(f"Bollinger Bands (window={window}, std_dev={num_std_dev}): "
                       f"Profit={metrics.get('profit_pct', 0):.2%}, Win Rate={metrics.get('win_rate', 0):.2%}, "
                       f"Trades={metrics.get('total_trades', 0)}")
        
        # Sắp xếp theo lợi nhuận
        results.sort(key=lambda x: x['profit'], reverse=True)
        
        # Lưu kết quả tối ưu
        if results:
            best = results[0]
            self.optimization_results['Bollinger_Bands'] = {
                'best_params': {
                    'window': best['window'],
                    'num_std_dev': best['num_std_dev']
                },
                'performance': {
                    'profit': best['profit'],
                    'win_rate': best['win_rate'],
                    'trade_count': best['trade_count']
                },
                'all_results': results
            }
            
            logger.info(f"Bollinger Bands tối ưu: window={best['window']}, std_dev={best['num_std_dev']}, "
                       f"Profit={best['profit']:.2%}, Win Rate={best['win_rate']:.2%}")
    
    def optimize_combined(self):
        """Tối ưu hóa chiến lược kết hợp các phương pháp tốt nhất"""
        # Kiểm tra nếu chưa có kết quả tối ưu hóa cho các chiến lược riêng lẻ
        strategies_to_combine = []
        weights_options = [0.2, 0.3, 0.5]
        
        if 'RSI' in self.optimization_results:
            best_rsi = self.optimization_results['RSI']['best_params']
            strategies_to_combine.append(RSIStrategy(
                overbought=best_rsi['overbought'],
                oversold=best_rsi['oversold']
            ))
        
        if 'MACD' in self.optimization_results:
            best_macd = self.optimization_results.get('MACD', {}).get('best_params', {})
            strategies_to_combine.append(MACDStrategy())
        
        if 'EMA_Cross' in self.optimization_results:
            best_ema = self.optimization_results['EMA_Cross']['best_params']
            strategies_to_combine.append(EMACrossStrategy(
                short_period=best_ema['short_period'],
                long_period=best_ema['long_period']
            ))
        
        if 'Bollinger_Bands' in self.optimization_results:
            best_bbands = self.optimization_results['Bollinger_Bands']['best_params']
            strategies_to_combine.append(BBandsStrategy(
                deviation_multiplier=best_bbands['num_std_dev']
            ))
        
        # Nếu không có đủ chiến lược để kết hợp
        if len(strategies_to_combine) < 2:
            logger.warning("Không đủ chiến lược tối ưu để kết hợp")
            return
        
        # Tạo tất cả các tổ hợp trọng số có tổng = 1
        num_strategies = len(strategies_to_combine)
        
        # Thử nhiều cách kết hợp khác nhau
        results = []
        
        # Thử các kết hợp của 2 chiến lược
        for i in range(num_strategies):
            for j in range(i+1, num_strategies):
                for weight_i in weights_options:
                    weight_j = 1 - weight_i
                    
                    # Tạo chiến lược kết hợp
                    combined_strategy = CombinedStrategy(
                        strategies=[strategies_to_combine[i], strategies_to_combine[j]],
                        weights=[weight_i, weight_j]
                    )
                    
                    bot = TradingBot(
                        binance_api=self.binance_api,
                        data_processor=self.data_processor,
                        strategy=combined_strategy,
                        symbol=self.symbol,
                        interval=self.interval,
                        test_mode=True
                    )
                    
                    # Chạy backtest
                    backtest_results, metrics = bot.backtest(self.historical_data, initial_balance=10000)
                    
                    # Lưu kết quả
                    results.append({
                        'strategies': [type(strategies_to_combine[i]).__name__, type(strategies_to_combine[j]).__name__],
                        'weights': [weight_i, weight_j],
                        'profit': metrics.get('profit_pct', 0),
                        'win_rate': metrics.get('win_rate', 0),
                        'trade_count': metrics.get('total_trades', 0),
                        'metrics': metrics
                    })
                    
                    logger.info(f"Combined ({type(strategies_to_combine[i]).__name__}={weight_i:.1f}, "
                               f"{type(strategies_to_combine[j]).__name__}={weight_j:.1f}): "
                               f"Profit={metrics.get('profit_pct', 0):.2%}, Win Rate={metrics.get('win_rate', 0):.2%}")
        
        # Sắp xếp theo lợi nhuận
        results.sort(key=lambda x: x['profit'], reverse=True)
        
        # Lưu kết quả tối ưu
        if results:
            best = results[0]
            self.optimization_results['Combined'] = {
                'best_params': {
                    'strategies': best['strategies'],
                    'weights': best['weights']
                },
                'performance': {
                    'profit': best['profit'],
                    'win_rate': best['win_rate'],
                    'trade_count': best['trade_count']
                },
                'all_results': results
            }
            
            logger.info(f"Combined tối ưu: {best['strategies'][0]}={best['weights'][0]:.1f}, "
                       f"{best['strategies'][1]}={best['weights'][1]:.1f}, "
                       f"Profit={best['profit']:.2%}, Win Rate={best['win_rate']:.2%}")
    
    def generate_report(self):
        """Tạo báo cáo tối ưu hóa"""
        # Lưu kết quả tối ưu hóa vào file JSON
        with open(f'strategy_optimization_{self.symbol}_{self.interval}.json', 'w') as f:
            # Xử lý kết quả để có thể serialize
            serializable_results = {}
            for strategy, results in self.optimization_results.items():
                serializable_results[strategy] = {
                    'best_params': results['best_params'],
                    'performance': results['performance'],
                    'all_results': []
                }
                
                for result in results.get('all_results', []):
                    if 'metrics' in result:
                        del result['metrics']
                    serializable_results[strategy]['all_results'].append(result)
            
            json.dump(serializable_results, f, indent=2)
        
        # In bảng tóm tắt
        summary_table = []
        for strategy, results in self.optimization_results.items():
            perf = results['performance']
            params = results['best_params']
            
            params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
            
            summary_table.append({
                'Strategy': strategy,
                'Parameters': params_str,
                'Profit': f"{perf['profit']:.2%}",
                'Win Rate': f"{perf['win_rate']:.2%}",
                'Trades': perf['trade_count']
            })
        
        print("\n=== BẢNG TÓM TẮT KẾT QUẢ TỐI ƯU HÓA ===")
        print(tabulate(summary_table, headers="keys", tablefmt="grid"))
        
        # Tạo biểu đồ so sánh hiệu suất
        plt.figure(figsize=(12, 6))
        
        strategies = []
        profits = []
        win_rates = []
        
        for strategy, results in self.optimization_results.items():
            strategies.append(strategy)
            profits.append(results['performance']['profit'] * 100)  # Chuyển thành phần trăm
            win_rates.append(results['performance']['win_rate'] * 100)  # Chuyển thành phần trăm
        
        x = np.arange(len(strategies))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(12, 6))
        rects1 = ax.bar(x - width/2, profits, width, label='Lợi nhuận (%)')
        rects2 = ax.bar(x + width/2, win_rates, width, label='Tỷ lệ thắng (%)')
        
        ax.set_title('So sánh hiệu suất các chiến lược tối ưu')
        ax.set_xticks(x)
        ax.set_xticklabels(strategies)
        ax.legend()
        
        # Thêm nhãn giá trị lên các cột
        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.1f}%',
                            xy=(rect.get_x() + rect.get_width()/2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom')
        
        autolabel(rects1)
        autolabel(rects2)
        
        fig.tight_layout()
        plt.savefig(f'strategy_optimization_{self.symbol}_{self.interval}.png')
        
        logger.info(f"Đã lưu báo cáo tối ưu hóa vào strategy_optimization_{self.symbol}_{self.interval}.json")
        logger.info(f"Đã lưu biểu đồ so sánh vào strategy_optimization_{self.symbol}_{self.interval}.png")

def main():
    parser = argparse.ArgumentParser(description='Công cụ tối ưu hóa chiến lược giao dịch')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp giao dịch cần tối ưu hóa')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)')
    parser.add_argument('--lookback', type=int, default=90, help='Số ngày dữ liệu lịch sử')
    
    args = parser.parse_args()
    
    optimizer = StrategyOptimizer(
        symbol=args.symbol,
        interval=args.interval,
        lookback_days=args.lookback
    )
    
    optimizer.optimize_all_strategies()

if __name__ == "__main__":
    main()