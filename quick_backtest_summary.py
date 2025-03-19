import pandas as pd
import numpy as np
import os
import argparse
import json
import logging
from datetime import datetime, timedelta
import yfinance as yf

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('quick_backtest')

# Tắt matplotlib backend để tránh lỗi Qt
import matplotlib
matplotlib.use('Agg')

class SimplifiedBacktester:
    def __init__(self, symbols, timeframe, period, initial_balance=10000):
        self.symbols = symbols
        self.timeframe = timeframe
        self.period = period
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.results = {}
        self.summary = {}
        
        # Load risk config
        self.load_risk_config()
        
    def load_risk_config(self):
        try:
            with open('account_risk_config.json', 'r') as f:
                self.risk_config = json.load(f)
            logger.info(f"Đã tải cấu hình rủi ro từ account_risk_config.json")
            
            # Sử dụng mức risk mặc định là "low"
            self.risk_level = "low"
            self.risk_params = self.risk_config["risk_levels"][self.risk_level]
            
            logger.info(f"Sử dụng mức rủi ro: {self.risk_level}")
            logger.info(f"Các tham số rủi ro: Rủi ro/Giao dịch: {self.risk_params['risk_per_trade']}%, Đòn bẩy: {self.risk_params['max_leverage']}x")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro: {e}")
            # Giá trị mặc định
            self.risk_params = {
                "risk_per_trade": 3.0,
                "max_leverage": 3,
                "max_open_positions": 5
            }
    
    def fetch_data(self, symbol, period):
        logger.info(f"Đang tải dữ liệu cho {symbol}, khung thời gian {self.timeframe}, khoảng thời gian {period}")
        try:
            data = yf.download(symbol, period=period, interval=self.timeframe)
            if isinstance(data.index, pd.MultiIndex):
                logger.info(f"Dữ liệu có cấu trúc MultiIndex, đang xử lý...")
                # Xử lý MultiIndex nếu cần
                data = data.reset_index(level=0, drop=True)
            
            logger.info(f"Đã tải {len(data)} dòng dữ liệu cho {symbol}")
            return data
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu {symbol}: {e}")
            return None
    
    def detect_rsi_divergence(self, data):
        """Phát hiện phân kỳ RSI đơn giản"""
        # Tính RSI
        delta = data['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Phát hiện phân kỳ đơn giản
        signals = []
        
        for i in range(30, len(data)):
            window = data.iloc[i-30:i]
            window_rsi = rsi.iloc[i-30:i]
            
            if len(window) < 30:
                continue
                
            # Cách tiếp cận đơn giản hơn để phát hiện tín hiệu
            # Thay vì tìm đáy cụ thể, chúng ta sẽ tìm điểm RSI dưới 30 và giá tăng
            # Đây là một cách tiếp cận đơn giản cho mục đích demo
            
            if len(window_rsi) > 14:
                if window_rsi.iloc[-1] < 30 and window_rsi.iloc[-1] > window_rsi.iloc[-2] and window['Close'].iloc[-1] > window['Close'].iloc[-2]:
                    signals.append({
                        'date': data.index[i],
                        'type': 'bullish',
                        'price': data['Close'].iloc[i],
                        'confidence': 0.9
                    })
                    logger.info(f"Phát hiện tín hiệu RSI oversold rebound tại {data.index[i]}, giá {data['Close'].iloc[i]}")
        
        return signals
    
    def detect_sideways_market(self, data):
        """Phát hiện thị trường sideway đơn giản dựa trên biến động giá"""
        # Tính mức độ biến động bằng ATR
        high_low = data['High'] - data['Low']
        high_close = abs(data['High'] - data['Close'].shift())
        low_close = abs(data['Low'] - data['Close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(14).mean()
        
        # Tính phần trăm biến động
        volatility = atr / data['Close'] * 100
        
        # Thị trường đi ngang có biến động nhỏ
        recent_volatility = volatility.iloc[-20:].mean()
        
        if recent_volatility < 1.5:
            return True, recent_volatility
        else:
            return False, recent_volatility
    
    def calculate_position_size(self, entry_price, stop_loss, signal_type):
        """Tính kích thước vị thế dựa trên rủi ro"""
        risk_amount = self.balance * (self.risk_params['risk_per_trade'] / 100)
        risk_per_share = abs(entry_price - stop_loss)
        position_size = risk_amount / risk_per_share
        
        # Áp dụng đòn bẩy
        leverage = self.risk_params['max_leverage']
        position_size = position_size * leverage
        
        return position_size, leverage
    
    def run_backtest(self, symbol):
        logger.info(f"Bắt đầu backtest cho {symbol}")
        
        # Lấy dữ liệu
        data = self.fetch_data(symbol, self.period)
        if data is None or len(data) < 30:
            logger.error(f"Không đủ dữ liệu để backtest {symbol}")
            return None
        
        # Phát hiện tín hiệu
        signals = self.detect_rsi_divergence(data)
        
        if not signals:
            logger.info(f"Không phát hiện tín hiệu giao dịch cho {symbol}")
            return None
        
        # Kiểm tra thị trường đi ngang
        is_sideways, volatility = self.detect_sideways_market(data)
        market_condition = "đi ngang" if is_sideways else "có xu hướng"
        logger.info(f"Thị trường {symbol} đang {market_condition}, biến động: {volatility:.2f}%")
        
        # Chạy backtest với tín hiệu đã phát hiện
        trades = []
        open_position = None
        
        for signal in signals:
            if signal['type'] == 'bullish' and open_position is None:
                # Tìm vị trí trong data
                idx = data.index.get_indexer([signal['date']], method='nearest')[0]
                if idx >= len(data) - 1:
                    continue
                
                # Giá vào lệnh
                entry_price = data['Close'].iloc[idx]
                
                # Tính stop loss và take profit
                atr = data['High'].iloc[idx-14:idx].max() - data['Low'].iloc[idx-14:idx].min()
                stop_loss = entry_price - atr * self.risk_config['atr_settings']['atr_multiplier'][self.risk_level]
                take_profit = entry_price + atr * self.risk_config['atr_settings']['take_profit_atr_multiplier'][self.risk_level]
                
                # Tính kích thước vị thế
                position_size, leverage = self.calculate_position_size(entry_price, stop_loss, 'buy')
                
                # Mở vị thế
                open_position = {
                    'symbol': symbol,
                    'entry_date': signal['date'],
                    'entry_price': entry_price,
                    'direction': 'buy',
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': position_size,
                    'leverage': leverage
                }
                
                logger.info(f"Mở vị thế BUY cho {symbol} tại {signal['date']}, giá {entry_price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
            
            # Đóng vị thế theo tín hiệu (không triển khai trong ví dụ này)
        
        # Kiểm tra kết quả các vị thế đã mở
        if open_position:
            entry_idx = data.index.get_indexer([open_position['entry_date']], method='nearest')[0]
            
            # Nếu còn vị thế mở, chạy ngày tiếp theo
            for i in range(entry_idx + 1, len(data)):
                current_price = data['Close'].iloc[i]
                
                # Kiểm tra stop loss
                if open_position['direction'] == 'buy' and current_price <= open_position['stop_loss']:
                    profit = (open_position['stop_loss'] - open_position['entry_price']) * open_position['position_size']
                    trades.append({
                        'symbol': symbol,
                        'entry_date': open_position['entry_date'],
                        'exit_date': data.index[i],
                        'entry_price': open_position['entry_price'],
                        'exit_price': open_position['stop_loss'],
                        'direction': 'buy',
                        'profit': profit,
                        'profit_pct': (open_position['stop_loss'] / open_position['entry_price'] - 1) * 100 * open_position['leverage'],
                        'exit_reason': 'stop_loss'
                    })
                    
                    stop_loss_price = open_position['stop_loss']
                    self.balance += profit
                    open_position = None
                    logger.info(f"Chạm stop loss {symbol} tại {data.index[i]}, giá {stop_loss_price:.2f}, lợi nhuận: ${profit:.2f}")
                    break
                
                # Kiểm tra take profit
                elif open_position['direction'] == 'buy' and current_price >= open_position['take_profit']:
                    profit = (open_position['take_profit'] - open_position['entry_price']) * open_position['position_size']
                    trades.append({
                        'symbol': symbol,
                        'entry_date': open_position['entry_date'],
                        'exit_date': data.index[i],
                        'entry_price': open_position['entry_price'],
                        'exit_price': open_position['take_profit'],
                        'direction': 'buy',
                        'profit': profit,
                        'profit_pct': (open_position['take_profit'] / open_position['entry_price'] - 1) * 100 * open_position['leverage'],
                        'exit_reason': 'take_profit'
                    })
                    
                    take_profit_price = open_position['take_profit']
                    self.balance += profit
                    open_position = None
                    logger.info(f"Chạm take profit {symbol} tại {data.index[i]}, giá {take_profit_price:.2f}, lợi nhuận: ${profit:.2f}")
                    break
            
            # Nếu kết thúc backtest mà vẫn còn vị thế mở
            if open_position:
                last_price = data['Close'].iloc[-1]
                profit = (last_price - open_position['entry_price']) * open_position['position_size']
                trades.append({
                    'symbol': symbol,
                    'entry_date': open_position['entry_date'],
                    'exit_date': data.index[-1],
                    'entry_price': open_position['entry_price'],
                    'exit_price': last_price,
                    'direction': 'buy',
                    'profit': profit,
                    'profit_pct': (last_price / open_position['entry_price'] - 1) * 100 * open_position['leverage'],
                    'exit_reason': 'end_of_test'
                })
                
                self.balance += profit
                logger.info(f"Kết thúc backtest với vị thế mở {symbol}, giá đóng {last_price:.2f}, lợi nhuận: ${profit:.2f}")
        
        return {
            'symbol': symbol,
            'trades': trades,
            'final_balance': self.balance,
            'profit': self.balance - self.initial_balance,
            'profit_pct': (self.balance / self.initial_balance - 1) * 100
        }
    
    def run_all(self):
        """Chạy backtest cho tất cả các symbols"""
        all_results = {}
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        total_profit = 0
        
        logger.info(f"=== BẮT ĐẦU BACKTEST CHO {len(self.symbols)} SYMBOLS ===")
        logger.info(f"Số dư ban đầu: ${self.initial_balance}")
        logger.info(f"Khung thời gian: {self.timeframe}")
        logger.info(f"Khoảng thời gian: {self.period}")
        logger.info(f"Mức rủi ro: {self.risk_level}")
        
        for symbol in self.symbols:
            result = self.run_backtest(symbol)
            if result and result['trades']:
                all_results[symbol] = result
                
                # Thống kê
                for trade in result['trades']:
                    total_trades += 1
                    if trade['profit'] > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
                    total_profit += trade['profit']
        
        # Tạo báo cáo tóm tắt
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        self.summary = {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_profit': self.balance - self.initial_balance,
            'total_profit_pct': (self.balance / self.initial_balance - 1) * 100,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'symbols_tested': len(self.symbols),
            'symbols_traded': len(all_results)
        }
        
        self.results = all_results
        return self.summary
    
    def print_summary(self):
        """In tóm tắt kết quả backtest"""
        logger.info(f"\n=== TÓM TẮT KẾT QUẢ BACKTEST ===")
        logger.info(f"Số symbols đã test: {self.summary['symbols_tested']}")
        logger.info(f"Số symbols có giao dịch: {self.summary['symbols_traded']}")
        logger.info(f"Tổng số giao dịch: {self.summary['total_trades']}")
        logger.info(f"Giao dịch thắng/thua: {self.summary['winning_trades']}/{self.summary['losing_trades']}")
        logger.info(f"Tỷ lệ thắng: {self.summary['win_rate']:.2f}%")
        logger.info(f"Số dư ban đầu: ${self.summary['initial_balance']:.2f}")
        logger.info(f"Số dư cuối cùng: ${self.summary['final_balance']:.2f}")
        logger.info(f"Tổng lợi nhuận: ${self.summary['total_profit']:.2f} ({self.summary['total_profit_pct']:.2f}%)")
        
        # In chi tiết từng symbol
        if self.results:
            logger.info(f"\n=== CHI TIẾT TỪNG SYMBOL ===")
            for symbol, result in self.results.items():
                if result['trades']:
                    profit = sum(trade['profit'] for trade in result['trades'])
                    num_trades = len(result['trades'])
                    win_trades = sum(1 for trade in result['trades'] if trade['profit'] > 0)
                    symbol_win_rate = (win_trades / num_trades) * 100 if num_trades > 0 else 0
                    
                    logger.info(f"{symbol}: {num_trades} giao dịch, Thắng: {win_trades}, Tỷ lệ: {symbol_win_rate:.2f}%, Lợi nhuận: ${profit:.2f}")

def main():
    parser = argparse.ArgumentParser(description='Công cụ backtest tóm tắt nhanh')
    parser.add_argument('--symbols', nargs='+', default=['BTC-USD', 'ETH-USD', 'SOL-USD'],
                        help='Danh sách các symbols cần test (e.g., BTC-USD ETH-USD)')
    parser.add_argument('--period', default='3mo', help='Khoảng thời gian (e.g., 1mo, 3mo, 6mo)')
    parser.add_argument('--timeframe', default='1d', help='Khung thời gian (e.g., 1d, 4h, 1h)')
    parser.add_argument('--balance', type=float, default=10000, help='Số dư ban đầu')
    
    args = parser.parse_args()
    
    # Khởi tạo và chạy backtest
    backtester = SimplifiedBacktester(
        symbols=args.symbols,
        timeframe=args.timeframe,
        period=args.period,
        initial_balance=args.balance
    )
    
    backtester.run_all()
    backtester.print_summary()

if __name__ == "__main__":
    main()