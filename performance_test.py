#!/usr/bin/env python3
"""
Công cụ kiểm tra hiệu suất các chiến lược giao dịch
Chạy mô phỏng backtest và live test với nhiều chiến lược khác nhau
"""
import os
import logging
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import argparse
import matplotlib.pyplot as plt
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('performance_test')

# Import các module từ ứng dụng
from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.strategy import (RSIStrategy, MACDStrategy, EMACrossStrategy, 
                         BBandsStrategy, CombinedStrategy, StrategyFactory)
from app.trading_bot import TradingBot
from app.storage import Storage

class PerformanceTester:
    def __init__(self, symbols=None, test_mode=True):
        """
        Khởi tạo công cụ test hiệu suất
        
        Args:
            symbols (list): Danh sách cặp giao dịch cần test
            test_mode (bool): Chế độ test (True) hoặc thực tế (False)
        """
        self.test_mode = test_mode
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT']
        self.intervals = ['1h', '4h', '1d']
        self.binance_api = BinanceAPI(simulation_mode=True)  # Luôn dùng simulation để test
        self.data_processor = DataProcessor(self.binance_api, simulation_mode=True)
        self.storage = Storage()
        
        # Danh sách các chiến lược cần test
        self.strategies = {
            'RSI': RSIStrategy(overbought=70, oversold=30),
            'MACD': MACDStrategy(),
            'EMA Cross': EMACrossStrategy(short_period=9, long_period=21),
            'Bollinger Bands': BBandsStrategy(),
            'Combined (RSI+MACD)': CombinedStrategy([
                RSIStrategy(overbought=70, oversold=30),
                MACDStrategy()
            ], weights=[0.5, 0.5])
        }
        
        # Kết quả test
        self.results = {
            'backtest': {},
            'livetest': {}
        }
    
    def run_all_tests(self):
        """Chạy tất cả các bài test"""
        logger.info("=== BẮT ĐẦU TEST HIỆU SUẤT CHIẾN LƯỢC GIAO DỊCH ===")
        
        # 1. Chạy backtest cho tất cả các chiến lược, cặp và khung thời gian
        logger.info("1. BACKTEST TẤT CẢ CHIẾN LƯỢC")
        self.run_all_backtests()
        
        # 2. Chạy live test nếu không ở chế độ test
        if not self.test_mode:
            logger.info("2. LIVETEST TẤT CẢ CHIẾN LƯỢC")
            self.run_live_test()
        
        # 3. Phân tích kết quả và tìm chiến lược tốt nhất
        logger.info("3. PHÂN TÍCH KẾT QUẢ")
        self.analyze_results()
        
        # 4. Tạo báo cáo hiệu suất
        logger.info("4. TẠO BÁO CÁO HIỆU SUẤT")
        self.generate_report()
    
    def run_all_backtests(self):
        """Chạy backtest cho tất cả các cấu hình"""
        for symbol in self.symbols:
            for interval in self.intervals:
                for strategy_name, strategy in self.strategies.items():
                    logger.info(f"Backtest: {symbol} - {interval} - {strategy_name}")
                    
                    # Tạo bot giao dịch cho backtest
                    bot = TradingBot(
                        binance_api=self.binance_api,
                        data_processor=self.data_processor,
                        strategy=strategy,
                        symbol=symbol,
                        interval=interval,
                        test_mode=True,
                        leverage=1,
                        max_positions=1,
                        risk_percentage=1.0
                    )
                    
                    # Lấy dữ liệu lịch sử để backtest
                    lookback_days = 90 if interval == '1h' else 365
                    df = self.data_processor.get_historical_data(
                        symbol=symbol,
                        interval=interval,
                        lookback_days=lookback_days
                    )
                    
                    if df is None or df.empty:
                        logger.warning(f"Không có dữ liệu cho {symbol} - {interval}")
                        continue
                    
                    # Chạy backtest
                    results, metrics = bot.backtest(df, initial_balance=10000)
                    
                    # Lưu kết quả
                    key = f"{symbol}_{interval}_{strategy_name}"
                    self.results['backtest'][key] = {
                        'symbol': symbol,
                        'interval': interval,
                        'strategy': strategy_name,
                        'metrics': metrics,
                        'trades': results.get('trades', []),
                        'equity_curve': results.get('equity_curve', [])
                    }
                    
                    logger.info(f"Kết quả backtest cho {key}: Win rate = {metrics.get('win_rate', 0):.2%}, "
                                f"Lợi nhuận = {metrics.get('profit_pct', 0):.2%}, "
                                f"Sharpe = {metrics.get('sharpe_ratio', 0):.2f}")
    
    def run_live_test(self, duration_hours=24):
        """
        Chạy live test cho các chiến lược tốt nhất
        
        Args:
            duration_hours (int): Thời gian chạy test (giờ)
        """
        # Lọc 3 chiến lược tốt nhất từ kết quả backtest
        best_strategies = self.get_best_strategies(top_n=3)
        
        for config in best_strategies:
            symbol = config['symbol']
            interval = config['interval']
            strategy_name = config['strategy']
            strategy = self.strategies[strategy_name]
            
            logger.info(f"Live test: {symbol} - {interval} - {strategy_name}")
            
            # Tạo bot với các thông số đã chọn
            bot = TradingBot(
                binance_api=self.binance_api,
                data_processor=self.data_processor,
                strategy=strategy,
                symbol=symbol,
                interval=interval,
                test_mode=True,  # Vẫn dùng test mode để không thực hiện giao dịch thật
                leverage=1,
                max_positions=1,
                risk_percentage=1.0
            )
            
            # Chạy bot trong một khoảng thời gian ngắn
            bot.start(check_interval=60)  # Kiểm tra mỗi 60 giây
            
            # Lưu thời điểm bắt đầu
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=duration_hours)
            
            logger.info(f"Bot đang chạy từ {start_time} đến {end_time}")
            
            try:
                # Giả lập chạy trong thời gian thực
                sleep_time = min(3600, duration_hours * 3600)  # Tối đa 1 giờ cho test
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                logger.info("Đã dừng test bằng tay")
            finally:
                # Dừng bot
                bot.stop()
                
                # Lấy và lưu metrics
                metrics = bot.get_current_metrics()
                trades = bot.trade_history
                
                key = f"{symbol}_{interval}_{strategy_name}"
                self.results['livetest'][key] = {
                    'symbol': symbol,
                    'interval': interval,
                    'strategy': strategy_name,
                    'metrics': metrics,
                    'trades': trades,
                    'start_time': start_time,
                    'end_time': datetime.now()
                }
                
                logger.info(f"Kết quả live test cho {key}: Win rate = {metrics.get('win_rate', 0):.2%}, "
                           f"Lợi nhuận = {metrics.get('profit_pct', 0):.2%}")
    
    def get_best_strategies(self, top_n=3):
        """
        Lấy n chiến lược tốt nhất dựa trên kết quả backtest
        
        Args:
            top_n (int): Số lượng chiến lược cần lấy
            
        Returns:
            list: Danh sách các chiến lược tốt nhất
        """
        # Tạo danh sách các chiến lược và sắp xếp theo lợi nhuận
        strategies = []
        
        for key, result in self.results['backtest'].items():
            metrics = result['metrics']
            
            # Chỉ xem xét các chiến lược có ít nhất 10 giao dịch
            if metrics.get('total_trades', 0) < 10:
                continue
            
            # Tính điểm dựa trên lợi nhuận, win rate và Sharpe ratio
            profit = metrics.get('profit_pct', 0)
            win_rate = metrics.get('win_rate', 0)
            sharpe = metrics.get('sharpe_ratio', 0)
            
            # Công thức tính điểm
            score = profit * 0.5 + win_rate * 0.3 + sharpe * 0.2
            
            strategies.append({
                'symbol': result['symbol'],
                'interval': result['interval'],
                'strategy': result['strategy'],
                'profit': profit,
                'win_rate': win_rate,
                'sharpe': sharpe,
                'score': score
            })
        
        # Sắp xếp theo điểm số
        strategies.sort(key=lambda x: x['score'], reverse=True)
        
        return strategies[:top_n]
    
    def analyze_results(self):
        """Phân tích kết quả và đưa ra các khuyến nghị"""
        logger.info("=== PHÂN TÍCH KẾT QUẢ ===")
        
        # 1. Phân tích backtest
        backtest_summary = []
        
        for key, result in self.results['backtest'].items():
            metrics = result['metrics']
            backtest_summary.append({
                'Symbol': result['symbol'],
                'Interval': result['interval'],
                'Strategy': result['strategy'],
                'Win Rate': f"{metrics.get('win_rate', 0):.2%}",
                'Profit': f"{metrics.get('profit_pct', 0):.2%}",
                'Trades': metrics.get('total_trades', 0),
                'Sharpe': f"{metrics.get('sharpe_ratio', 0):.2f}",
                'Max DD': f"{metrics.get('max_drawdown', 0):.2%}"
            })
        
        # Sắp xếp theo lợi nhuận
        backtest_summary.sort(key=lambda x: float(x['Profit'].replace('%', '')) / 100, reverse=True)
        
        print("\n=== KẾT QUẢ BACKTEST ===")
        print(tabulate(backtest_summary, headers="keys", tablefmt="grid"))
        
        # 2. Phân tích và khuyến nghị
        best_strategies = self.get_best_strategies(top_n=3)
        
        print("\n=== 3 CHIẾN LƯỢC TỐT NHẤT ===")
        for i, strategy in enumerate(best_strategies, 1):
            print(f"{i}. {strategy['symbol']} - {strategy['interval']} - {strategy['strategy']}")
            print(f"   Lợi nhuận: {strategy['profit']:.2%}, Win Rate: {strategy['win_rate']:.2%}, Sharpe: {strategy['sharpe']:.2f}")
            print()
    
    def generate_report(self):
        """Tạo báo cáo hiệu suất với đồ thị"""
        # Lấy chiến lược tốt nhất
        best_strategies = self.get_best_strategies(top_n=1)
        if not best_strategies:
            logger.warning("Không có đủ dữ liệu để tạo báo cáo")
            return
        
        best = best_strategies[0]
        key = f"{best['symbol']}_{best['interval']}_{best['strategy']}"
        result = self.results['backtest'].get(key)
        
        if not result:
            logger.warning(f"Không tìm thấy kết quả cho {key}")
            return
        
        # Tạo đồ thị equity curve
        equity_curve = result.get('equity_curve', [])
        if equity_curve:
            plt.figure(figsize=(12, 6))
            plt.plot(equity_curve)
            plt.title(f"Equity Curve: {best['symbol']} - {best['interval']} - {best['strategy']}")
            plt.xlabel('Giao dịch')
            plt.ylabel('Tài sản ($)')
            plt.grid(True)
            plt.savefig('equity_curve.png')
            plt.close()
            
            logger.info(f"Đã lưu đồ thị equity curve vào equity_curve.png")
        
        # Tạo file báo cáo
        with open('trading_report.txt', 'w') as f:
            f.write("=== BÁO CÁO HIỆU SUẤT GIAO DỊCH ===\n\n")
            f.write(f"Thời gian: {datetime.now()}\n\n")
            
            f.write("=== CHIẾN LƯỢC TỐT NHẤT ===\n")
            f.write(f"Symbol: {best['symbol']}\n")
            f.write(f"Interval: {best['interval']}\n")
            f.write(f"Strategy: {best['strategy']}\n")
            f.write(f"Profit: {best['profit']:.2%}\n")
            f.write(f"Win Rate: {best['win_rate']:.2%}\n")
            f.write(f"Sharpe Ratio: {best['sharpe']:.2f}\n\n")
            
            f.write("=== THÔNG TIN GIAO DỊCH ===\n")
            trades = result.get('trades', [])
            f.write(f"Tổng số giao dịch: {len(trades)}\n")
            
            winning_trades = [t for t in trades if t.get('pnl_pct', 0) > 0]
            losing_trades = [t for t in trades if t.get('pnl_pct', 0) <= 0]
            
            f.write(f"Số giao dịch thắng: {len(winning_trades)}\n")
            f.write(f"Số giao dịch thua: {len(losing_trades)}\n")
            
            if winning_trades:
                avg_win = sum(t.get('pnl_pct', 0) for t in winning_trades) / len(winning_trades)
                f.write(f"Lợi nhuận trung bình giao dịch thắng: {avg_win:.2%}\n")
            
            if losing_trades:
                avg_loss = sum(t.get('pnl_pct', 0) for t in losing_trades) / len(losing_trades)
                f.write(f"Thua lỗ trung bình giao dịch thua: {avg_loss:.2%}\n")
            
            f.write("\n=== KẾT LUẬN ===\n")
            f.write(f"Chiến lược {best['strategy']} trên {best['symbol']} với khung thời gian {best['interval']} "
                   f"cho hiệu suất tốt nhất trong quá trình backtest.\n")
        
        logger.info(f"Đã lưu báo cáo vào trading_report.txt")

def main():
    parser = argparse.ArgumentParser(description='Công cụ kiểm tra hiệu suất giao dịch')
    parser.add_argument('--live', action='store_true', help='Chạy live test (mặc định: chỉ backtest)')
    parser.add_argument('--symbols', type=str, nargs='+', default=None, help='Danh sách các cặp giao dịch cần test')
    
    args = parser.parse_args()
    
    tester = PerformanceTester(symbols=args.symbols, test_mode=not args.live)
    tester.run_all_tests()

if __name__ == "__main__":
    main()