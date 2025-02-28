#!/usr/bin/env python3
"""
Chạy bot giao dịch tự động với các cấu hình đã tối ưu
"""
import os
import logging
import json
import time
import signal
import argparse
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('trading_bot_runner')

# Import các module từ ứng dụng
from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.strategy import (RSIStrategy, MACDStrategy, EMACrossStrategy, 
                         BBandsStrategy, CombinedStrategy)
from app.trading_bot import TradingBot

class TradingBotRunner:
    def __init__(self, config_file=None, symbol='BTCUSDT', interval='1h', 
                 test_mode=True, leverage=1, risk_percentage=1.0,
                 use_optimized=True):
        """
        Khởi tạo runner cho bot giao dịch
        
        Args:
            config_file (str): Đường dẫn đến file cấu hình
            symbol (str): Cặp giao dịch
            interval (str): Khung thời gian
            test_mode (bool): Chạy ở chế độ test
            leverage (int): Đòn bẩy (1-50)
            risk_percentage (float): Phần trăm rủi ro (0.1-10.0)
            use_optimized (bool): Sử dụng chiến lược tối ưu từ file cấu hình
        """
        self.symbol = symbol
        self.interval = interval
        self.test_mode = test_mode
        self.leverage = leverage
        self.risk_percentage = risk_percentage
        self.use_optimized = use_optimized
        
        # Khởi tạo API và Data Processor
        simulation = True if test_mode else False
        self.binance_api = BinanceAPI(simulation_mode=simulation)
        self.data_processor = DataProcessor(self.binance_api, simulation_mode=simulation)
        
        # Khởi tạo bot giao dịch với chiến lược mặc định
        self.strategy = self._create_default_strategy()
        
        # Nếu sử dụng cấu hình tối ưu
        if use_optimized and config_file:
            self._load_optimized_strategy(config_file)
        
        # Khởi tạo bot giao dịch
        self.bot = TradingBot(
            binance_api=self.binance_api,
            data_processor=self.data_processor,
            strategy=self.strategy,
            symbol=self.symbol,
            interval=self.interval,
            test_mode=self.test_mode,
            leverage=self.leverage,
            max_positions=1,
            risk_percentage=self.risk_percentage
        )
        
        # Xử lý tín hiệu interrupt
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)
        
        logger.info("Đã khởi tạo bot giao dịch: "
                   f"Symbol={self.symbol}, Interval={self.interval}, "
                   f"Test Mode={self.test_mode}, Leverage={self.leverage}x, "
                   f"Risk={self.risk_percentage}%, Strategy={type(self.strategy).__name__}")
    
    def _create_default_strategy(self):
        """Tạo chiến lược mặc định"""
        # Chiến lược kết hợp
        return CombinedStrategy([
            RSIStrategy(overbought=70, oversold=30),
            MACDStrategy(),
            EMACrossStrategy(short_period=9, long_period=21)
        ], weights=[0.4, 0.3, 0.3])
    
    def _load_optimized_strategy(self, config_file):
        """
        Tải cấu hình chiến lược tối ưu từ file
        
        Args:
            config_file (str): Đường dẫn đến file cấu hình
        """
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Tìm kết quả của cặp giao dịch và khung thời gian phù hợp
            strategy_key = None
            for key in config.keys():
                if 'Combined' in key:
                    strategy_key = 'Combined'
                    break
            
            if not strategy_key:
                logger.warning("Không tìm thấy chiến lược kết hợp tối ưu trong file cấu hình")
                return
            
            # Lấy thông tin chiến lược tối ưu
            combined_config = config[strategy_key]
            best_params = combined_config.get('best_params', {})
            
            # Nếu có danh sách chiến lược kết hợp
            if 'strategies' in best_params and 'weights' in best_params:
                strategies_to_combine = []
                
                # Tạo các chiến lược con
                for strategy_name in best_params['strategies']:
                    if strategy_name == 'RSIStrategy':
                        rsi_params = config.get('RSI', {}).get('best_params', {})
                        strategies_to_combine.append(RSIStrategy(
                            overbought=rsi_params.get('overbought', 70),
                            oversold=rsi_params.get('oversold', 30)
                        ))
                    elif strategy_name == 'MACDStrategy':
                        strategies_to_combine.append(MACDStrategy())
                    elif strategy_name == 'EMACrossStrategy':
                        ema_params = config.get('EMA_Cross', {}).get('best_params', {})
                        strategies_to_combine.append(EMACrossStrategy(
                            short_period=ema_params.get('short_period', 9),
                            long_period=ema_params.get('long_period', 21)
                        ))
                    elif strategy_name == 'BBandsStrategy':
                        bb_params = config.get('Bollinger_Bands', {}).get('best_params', {})
                        strategies_to_combine.append(BBandsStrategy(
                            deviation_multiplier=bb_params.get('num_std_dev', 2.0)
                        ))
                
                # Tạo chiến lược kết hợp
                if len(strategies_to_combine) > 1:
                    self.strategy = CombinedStrategy(
                        strategies=strategies_to_combine,
                        weights=best_params['weights']
                    )
                    
                    logger.info(f"Đã tải chiến lược kết hợp tối ưu: {[type(s).__name__ for s in strategies_to_combine]}")
                    return
            
            # Nếu không tìm thấy cấu hình phù hợp, sử dụng chiến lược mặc định
            logger.warning("Không thể tạo chiến lược kết hợp tối ưu, sử dụng chiến lược mặc định")
            
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình tối ưu: {str(e)}")
    
    def _handle_exit(self, signum, frame):
        """Xử lý khi nhận tín hiệu thoát"""
        logger.info("Nhận tín hiệu thoát, đang dừng bot...")
        self.stop_bot()
        
    def start_bot(self, check_interval=60):
        """
        Bắt đầu chạy bot giao dịch
        
        Args:
            check_interval (int): Khoảng thời gian kiểm tra (giây)
        """
        logger.info(f"Bắt đầu chạy bot giao dịch với khoảng thời gian kiểm tra {check_interval}s")
        
        # Bắt đầu bot
        success = self.bot.start(check_interval=check_interval)
        
        if success:
            logger.info("Bot giao dịch đã bắt đầu chạy thành công")
            
            # Vòng lặp báo cáo trạng thái định kỳ
            try:
                while True:
                    time.sleep(600)  # Báo cáo mỗi 10 phút
                    self._report_status()
            except KeyboardInterrupt:
                logger.info("Nhận tín hiệu dừng từ bàn phím")
                self.stop_bot()
        else:
            logger.error("Không thể khởi động bot giao dịch")
    
    def stop_bot(self):
        """Dừng bot giao dịch"""
        if self.bot:
            self.bot.stop()
            logger.info("Đã dừng bot giao dịch")
            
            # Báo cáo kết quả cuối cùng
            self._final_report()
    
    def _report_status(self):
        """Báo cáo trạng thái hoạt động của bot"""
        if not self.bot:
            return
            
        # Lấy thông tin hiệu suất
        metrics = self.bot.get_current_metrics()
        positions = self.bot.positions
        
        # In báo cáo trạng thái
        logger.info("=== BÁO CÁO TRẠNG THÁI BOT ===")
        logger.info(f"Thời gian: {datetime.now()}")
        logger.info(f"Bot hoạt động: {self.bot.is_running}")
        logger.info(f"Tổng giao dịch: {metrics.get('total_trades', 0)}")
        logger.info(f"Thắng/Thua: {metrics.get('winning_trades', 0)}/{metrics.get('losing_trades', 0)}")
        logger.info(f"Win rate: {metrics.get('win_rate', 0):.2%}")
        logger.info(f"Lợi nhuận tích lũy: {metrics.get('profit_pct', 0):.2%}")
        
        if positions:
            logger.info("Vị thế đang mở:")
            position_data = []
            for pos in positions:
                if pos['status'] == 'OPEN':
                    position_data.append({
                        'Symbol': pos['symbol'],
                        'Side': pos['side'],
                        'Entry Price': pos['entry_price'],
                        'Current Price': pos['current_price'],
                        'P&L': f"{pos['current_pnl']:.2%}"
                    })
            
            if position_data:
                logger.info('\n' + tabulate(position_data, headers="keys", tablefmt="grid"))
    
    def _final_report(self):
        """Tạo báo cáo kết quả cuối cùng"""
        if not self.bot:
            return
            
        # Lấy thông tin hiệu suất
        metrics = self.bot.get_current_metrics()
        trades = self.bot.trade_history
        
        # In báo cáo kết quả
        logger.info("=== BÁO CÁO KẾT QUẢ CUỐI CÙNG ===")
        logger.info(f"Thời gian kết thúc: {datetime.now()}")
        logger.info(f"Tổng giao dịch: {metrics.get('total_trades', 0)}")
        logger.info(f"Thắng/Thua: {metrics.get('winning_trades', 0)}/{metrics.get('losing_trades', 0)}")
        logger.info(f"Win rate: {metrics.get('win_rate', 0):.2%}")
        logger.info(f"Lợi nhuận tích lũy: {metrics.get('profit_pct', 0):.2%}")
        
        if trades:
            logger.info("10 giao dịch gần nhất:")
            trades_data = []
            for trade in trades[-10:]:
                trades_data.append({
                    'Symbol': trade['symbol'],
                    'Side': trade['side'],
                    'Entry Price': trade['entry_price'],
                    'Exit Price': trade['exit_price'],
                    'P&L': f"{trade.get('final_pnl', 0):.2%}",
                    'Entry Time': trade['entry_time'].strftime('%Y-%m-%d %H:%M'),
                    'Exit Time': trade['exit_time'].strftime('%Y-%m-%d %H:%M') if trade['exit_time'] else 'N/A'
                })
            
            if trades_data:
                logger.info('\n' + tabulate(trades_data, headers="keys", tablefmt="grid"))
        
        # Lưu kết quả giao dịch vào file CSV cho phân tích
        if trades:
            try:
                df = pd.DataFrame(trades)
                df.to_csv(f'trade_results_{self.symbol}_{self.interval}_{datetime.now().strftime("%Y%m%d")}.csv', index=False)
                logger.info(f"Đã lưu kết quả giao dịch vào file CSV")
            except Exception as e:
                logger.error(f"Lỗi khi lưu kết quả giao dịch: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Bot giao dịch tự động')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp giao dịch')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian')
    parser.add_argument('--live', action='store_true', help='Chạy trong môi trường thực (mặc định: simulation)')
    parser.add_argument('--leverage', type=int, default=1, help='Đòn bẩy (1-50)')
    parser.add_argument('--risk', type=float, default=1.0, help='Phần trăm rủi ro (0.1-10.0)')
    parser.add_argument('--config', type=str, help='File cấu hình tối ưu')
    parser.add_argument('--check-interval', type=int, default=60, help='Khoảng thời gian kiểm tra (giây)')
    
    args = parser.parse_args()
    
    # Khởi tạo runner
    runner = TradingBotRunner(
        config_file=args.config,
        symbol=args.symbol,
        interval=args.interval,
        test_mode=not args.live,
        leverage=args.leverage,
        risk_percentage=args.risk,
        use_optimized=args.config is not None
    )
    
    # Bắt đầu chạy bot
    runner.start_bot(check_interval=args.check_interval)

if __name__ == "__main__":
    main()