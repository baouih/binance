import os
import sys
import pandas as pd
import numpy as np
import datetime
import json
import logging
import matplotlib.pyplot as plt
from pathlib import Path
import time

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest_detailed.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('backtest_detailed')

print('=== BẮT ĐẦU QUÁ TRÌNH BACKTEST CHI TIẾT & PHÂN TÍCH THUẬT TOÁN ===')

# Tạo thư mục cho báo cáo
report_dirs = [
    './backtest_reports',
    './backtest_charts'
]

for dir_path in report_dirs:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        print(f'- Đã tạo thư mục {dir_path}')

# Kiểm tra dữ liệu đầu vào
data_dir = Path('./backtest_data')
btc_file = data_dir / 'BTCUSDT_1h.csv'
eth_file = data_dir / 'ETHUSDT_1h.csv'

if not btc_file.exists() or not eth_file.exists():
    print('Lỗi: Không tìm thấy file dữ liệu BTC hoặc ETH')
    sys.exit(1)

print(f'- Đang tải dữ liệu từ {btc_file} và {eth_file}')
btc_data = pd.read_csv(btc_file)
eth_data = pd.read_csv(eth_file)

print(f'- Đã tải dữ liệu BTC với {len(btc_data)} dòng từ {btc_data["timestamp"].min()} đến {btc_data["timestamp"].max()}')
print(f'- Đã tải dữ liệu ETH với {len(eth_data)} dòng từ {eth_data["timestamp"].min()} đến {eth_data["timestamp"].max()}')

class BacktestEngine:
    def __init__(self, data, symbol, initial_balance=10000, leverage=5):
        self.data = data.copy()
        self.symbol = symbol
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.leverage = leverage
        self.positions = []
        self.current_position = None
        self.trades_history = []
        self.equity_curve = []
        self.drawdown_curve = []
        
        # Thống kê
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.breakeven_trades = 0
        self.max_drawdown = 0
        self.max_drawdown_pct = 0
        self.peak_balance = initial_balance
        self.max_consecutive_losses = 0
        self.current_consecutive_losses = 0
        self.max_consecutive_wins = 0
        self.current_consecutive_wins = 0
        self.profit_factor = 0
        self.total_profit = 0
        self.total_loss = 0
        self.largest_win = 0
        self.largest_loss = 0
        
        # Thống kê theo loại thoát lệnh
        self.exit_stats = {
            'TP': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'SL': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'TRAILING_STOP': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'FINAL': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0}
        }
        
        # Các cài đặt mặc định
        self.risk_per_trade = 0.02  # 2% của balance
        self.sl_pct = 0.015  # 1.5% SL
        self.tp_pct = 0.03  # 3% TP
        self.enable_trailing_stop = True
        self.trailing_trigger = 0.02  # Kích hoạt trailing khi lời 2%
        self.trailing_step = 0.005  # Di chuyển 0.5% mỗi bước
        
        # Để lưu tín hiệu từ strategy
        self.signal_history = []
        
        # Thời gian các lệnh
        self.trade_durations = []
        
        logger.info(f'Khởi tạo Backtest Engine cho {symbol} với balance={initial_balance}, leverage={leverage}')
    
    def run(self, strategy, debug_level=0):
        logger.info(f'Bắt đầu chạy backtest cho {self.symbol} với strategy={strategy.__class__.__name__}')
        self.equity_curve = [self.balance]
        self.drawdown_curve = [0]
        self.strategy_name = strategy.__class__.__name__
        
        # Chuẩn bị strategy
        strategy.prepare(self.data) if hasattr(strategy, 'prepare') else None
        
        start_time = time.time()
        
        for i in range(1, len(self.data)):
            # Lưu thông tin ngày hiện tại để debug
            current_date = self.data.iloc[i]['timestamp']
            current_price = self.data.iloc[i]['close']
            
            # Mỗi 100 candle, ghi log tiến độ
            if i % 100 == 0 and debug_level > 0:
                logger.info(f'Đang xử lý candle {i}/{len(self.data)}, ngày {current_date}, giá {current_price:.2f}')
            
            # Cập nhật vị thế hiện tại nếu có
            if self.current_position:
                self._update_position(i)
            
            # Lấy tín hiệu từ strategy
            signal, signal_data = strategy.generate_signal(self.data, i)
            
            # Lưu tín hiệu
            self.signal_history.append({
                'timestamp': current_date,
                'price': current_price,
                'signal': signal,
                'signal_data': signal_data
            })
            
            # Kiểm tra tín hiệu để mở vị thế
            if not self.current_position and signal in ['LONG', 'SHORT']:
                self._open_position(signal, i)
            
            # Cập nhật equity curve và drawdown
            current_equity = self.calculate_equity(i)
            self.equity_curve.append(current_equity)
            
            # Tính drawdown
            peak_equity = max(self.equity_curve)
            current_drawdown = (peak_equity - current_equity) / peak_equity * 100 if peak_equity > 0 else 0
            self.drawdown_curve.append(current_drawdown)
        
        # Đóng vị thế cuối cùng nếu còn
        if self.current_position:
            self._close_position(self.data.iloc[-1]['close'], 'FINAL')
        
        # Tính toán thống kê
        self._calculate_statistics()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        logger.info(f'Hoàn thành backtest cho {self.symbol} trong {elapsed_time:.2f} giây')
        
        return {
            'symbol': self.symbol,
            'strategy': self.strategy_name,
            'balance': self.balance,
            'equity_curve': self.equity_curve,
            'drawdown_curve': self.drawdown_curve,
            'trades_history': self.trades_history,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'breakeven_trades': self.breakeven_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            'profit_loss': self.balance - self.initial_balance,
            'profit_loss_pct': (self.balance - self.initial_balance) / self.initial_balance * 100,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'max_consecutive_losses': self.max_consecutive_losses,
            'max_consecutive_wins': self.max_consecutive_wins,
            'profit_factor': self.profit_factor,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'avg_trade_duration': sum(self.trade_durations) / len(self.trade_durations) if self.trade_durations else 0,
            'exit_stats': self.exit_stats,
            'signal_history': self.signal_history
        }
    
    def _open_position(self, signal, index):
        entry_price = self.data.iloc[index]['close']
        entry_time = self.data.iloc[index]['timestamp']
        
        # Tính size dựa trên risk
        risk_amount = self.balance * self.risk_per_trade
        position_size = risk_amount / (entry_price * self.sl_pct / self.leverage)
        
        # Giới hạn position size để không vượt quá 10% tài khoản
        max_position_size = (self.balance * 0.1 * self.leverage) / entry_price
        position_size = min(position_size, max_position_size)
        
        # Tính SL/TP
        if signal == 'LONG':
            sl_price = entry_price * (1 - self.sl_pct)
            tp_price = entry_price * (1 + self.tp_pct)
        else:  # SHORT
            sl_price = entry_price * (1 + self.sl_pct)
            tp_price = entry_price * (1 - self.tp_pct)
        
        # Tạo vị thế
        self.current_position = {
            'type': signal,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'entry_index': index,
            'size': position_size,
            'sl_price': sl_price,
            'initial_sl_price': sl_price,
            'tp_price': tp_price,
            'exit_price': None,
            'exit_time': None,
            'exit_index': None,
            'pnl': 0,
            'pnl_pct': 0,
            'status': 'OPEN',
            'highest_price': entry_price,
            'lowest_price': entry_price,
            'trailing_active': False,
            'trailing_stop': None
        }
        
        logger.info(f'Mở vị thế {signal} {self.symbol} tại {entry_price} với size={position_size:.6f}, SL={sl_price:.2f}, TP={tp_price:.2f}')
    
    def _update_position(self, index):
        if not self.current_position:
            return
        
        current_price = self.data.iloc[index]['close']
        high_price = self.data.iloc[index]['high']
        low_price = self.data.iloc[index]['low']
        
        # Cập nhật giá cao/thấp nhất
        if self.current_position['type'] == 'LONG':
            self.current_position['highest_price'] = max(self.current_position['highest_price'], high_price)
            self.current_position['lowest_price'] = min(self.current_position['lowest_price'], low_price)
        else:  # SHORT
            self.current_position['highest_price'] = max(self.current_position['highest_price'], high_price)
            self.current_position['lowest_price'] = min(self.current_position['lowest_price'], low_price)
        
        # Kiểm tra trailing stop
        if self.enable_trailing_stop:
            self._check_trailing_stop(current_price)
        
        # Kiểm tra SL/TP
        if self._check_stop_loss(low_price, high_price) or self._check_take_profit(low_price, high_price):
            # Vị thế đã được đóng trong _check_stop_loss hoặc _check_take_profit
            return
        
        # Tính PnL hiện tại
        if self.current_position['type'] == 'LONG':
            unrealized_pnl = (current_price - self.current_position['entry_price']) * self.current_position['size']
            unrealized_pnl_pct = (current_price - self.current_position['entry_price']) / self.current_position['entry_price'] * 100
        else:  # SHORT
            unrealized_pnl = (self.current_position['entry_price'] - current_price) * self.current_position['size']
            unrealized_pnl_pct = (self.current_position['entry_price'] - current_price) / self.current_position['entry_price'] * 100
        
        self.current_position['pnl'] = unrealized_pnl
        self.current_position['pnl_pct'] = unrealized_pnl_pct
    
    def _check_trailing_stop(self, current_price):
        if not self.current_position or not self.enable_trailing_stop:
            return False
        
        # Kiểm tra điều kiện kích hoạt trailing stop
        if not self.current_position['trailing_active']:
            if self.current_position['type'] == 'LONG':
                profit_pct = (current_price - self.current_position['entry_price']) / self.current_position['entry_price'] * 100
                if profit_pct >= self.trailing_trigger * 100:
                    # Kích hoạt trailing stop
                    self.current_position['trailing_active'] = True
                    self.current_position['trailing_stop'] = current_price * (1 - self.trailing_step)
                    logger.info(f'Đã kích hoạt Trailing Stop cho {self.symbol} tại {current_price:.2f} với stop={self.current_position["trailing_stop"]:.2f}')
            else:  # SHORT
                profit_pct = (self.current_position['entry_price'] - current_price) / self.current_position['entry_price'] * 100
                if profit_pct >= self.trailing_trigger * 100:
                    # Kích hoạt trailing stop
                    self.current_position['trailing_active'] = True
                    self.current_position['trailing_stop'] = current_price * (1 + self.trailing_step)
                    logger.info(f'Đã kích hoạt Trailing Stop cho {self.symbol} tại {current_price:.2f} với stop={self.current_position["trailing_stop"]:.2f}')
        
        # Cập nhật trailing stop nếu đã kích hoạt
        if self.current_position['trailing_active']:
            if self.current_position['type'] == 'LONG':
                new_trailing_stop = current_price * (1 - self.trailing_step)
                if new_trailing_stop > self.current_position['trailing_stop']:
                    self.current_position['trailing_stop'] = new_trailing_stop
                    logger.info(f'Cập nhật Trailing Stop {self.symbol} lên {self.current_position["trailing_stop"]:.2f}')
            else:  # SHORT
                new_trailing_stop = current_price * (1 + self.trailing_step)
                if new_trailing_stop < self.current_position['trailing_stop']:
                    self.current_position['trailing_stop'] = new_trailing_stop
                    logger.info(f'Cập nhật Trailing Stop {self.symbol} xuống {self.current_position["trailing_stop"]:.2f}')
            
            # Kiểm tra xem giá có chạm trailing stop không
            if self.current_position['type'] == 'LONG' and current_price <= self.current_position['trailing_stop']:
                self._close_position(current_price, 'TRAILING_STOP')
                return True
            elif self.current_position['type'] == 'SHORT' and current_price >= self.current_position['trailing_stop']:
                self._close_position(current_price, 'TRAILING_STOP')
                return True
        
        return False
    
    def _check_stop_loss(self, low_price, high_price):
        if not self.current_position:
            return False
        
        if self.current_position['type'] == 'LONG':
            if low_price <= self.current_position['sl_price']:
                # Kích hoạt SL ở giá SL
                self._close_position(self.current_position['sl_price'], 'SL')
                return True
        else:  # SHORT
            if high_price >= self.current_position['sl_price']:
                # Kích hoạt SL ở giá SL
                self._close_position(self.current_position['sl_price'], 'SL')
                return True
        
        return False
    
    def _check_take_profit(self, low_price, high_price):
        if not self.current_position:
            return False
        
        # Kiểm tra trailing stop trước
        if self.current_position['trailing_active']:
            return False
        
        if self.current_position['type'] == 'LONG':
            if high_price >= self.current_position['tp_price']:
                # Kích hoạt TP ở giá TP
                self._close_position(self.current_position['tp_price'], 'TP')
                return True
        else:  # SHORT
            if low_price <= self.current_position['tp_price']:
                # Kích hoạt TP ở giá TP
                self._close_position(self.current_position['tp_price'], 'TP')
                return True
        
        return False
    
    def _close_position(self, exit_price, reason):
        if not self.current_position:
            return
        
        # Tính PnL
        if self.current_position['type'] == 'LONG':
            pnl = (exit_price - self.current_position['entry_price']) * self.current_position['size']
            pnl_pct = (exit_price - self.current_position['entry_price']) / self.current_position['entry_price'] * 100
        else:  # SHORT
            pnl = (self.current_position['entry_price'] - exit_price) * self.current_position['size']
            pnl_pct = (self.current_position['entry_price'] - exit_price) / self.current_position['entry_price'] * 100
        
        # Cập nhật balance
        self.balance += pnl
        
        # Cập nhật thông tin vị thế
        self.current_position['exit_price'] = exit_price
        exit_time = self.data.iloc[-1]['timestamp'] if reason == 'FINAL' else self.data.iloc[min(len(self.data) - 1, self.current_position['entry_index'] + 1)]['timestamp']
        self.current_position['exit_time'] = exit_time
        self.current_position['exit_index'] = min(len(self.data) - 1, self.current_position['entry_index'] + 1)
        self.current_position['pnl'] = pnl
        self.current_position['pnl_pct'] = pnl_pct
        self.current_position['status'] = 'CLOSED'
        self.current_position['exit_reason'] = reason
        
        # Tính thời gian giao dịch (số candle)
        trade_duration = self.current_position['exit_index'] - self.current_position['entry_index']
        self.trade_durations.append(trade_duration)
        
        # Cập nhật thống kê theo reason
        if reason not in self.exit_stats:
            self.exit_stats[reason] = {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0}
        
        self.exit_stats[reason]['count'] += 1
        if pnl > 0:
            self.exit_stats[reason]['win'] += 1
        else:
            self.exit_stats[reason]['loss'] += 1
        
        self.exit_stats[reason]['total_pnl'] += pnl
        
        # Thêm vào lịch sử
        self.trades_history.append(self.current_position.copy())
        
        # Cập nhật thống kê
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
            self.total_profit += pnl
            self.largest_win = max(self.largest_win, pnl)
            
            # Cập nhật consecutive wins
            self.current_consecutive_wins += 1
            self.current_consecutive_losses = 0
            self.max_consecutive_wins = max(self.max_consecutive_wins, self.current_consecutive_wins)
        elif pnl < 0:
            self.losing_trades += 1
            self.total_loss -= pnl  # Lưu ý: total_loss lưu giá trị dương
            self.largest_loss = min(self.largest_loss, pnl)
            
            # Cập nhật consecutive losses
            self.current_consecutive_losses += 1
            self.current_consecutive_wins = 0
            self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_consecutive_losses)
        else:
            self.breakeven_trades += 1
        
        # Reset current position
        self.current_position = None
        
        logger.info(f'Đóng vị thế {self.symbol} tại {exit_price:.2f} với lý do {reason}, PnL={pnl:.2f} ({pnl_pct:.2f}%), Balance={self.balance:.2f}')
    
    def calculate_equity(self, index):
        equity = self.balance
        
        if self.current_position:
            current_price = self.data.iloc[index]['close']
            if self.current_position['type'] == 'LONG':
                equity += (current_price - self.current_position['entry_price']) * self.current_position['size']
            else:  # SHORT
                equity += (self.current_position['entry_price'] - current_price) * self.current_position['size']
        
        # Cập nhật max drawdown
        if equity > self.peak_balance:
            self.peak_balance = equity
        else:
            drawdown = self.peak_balance - equity
            drawdown_pct = drawdown / self.peak_balance * 100
            if drawdown_pct > self.max_drawdown_pct:
                self.max_drawdown = drawdown
                self.max_drawdown_pct = drawdown_pct
        
        return equity
    
    def _calculate_statistics(self):
        # Tính profit factor
        if self.total_loss > 0:
            self.profit_factor = self.total_profit / self.total_loss
        else:
            self.profit_factor = float('inf') if self.total_profit > 0 else 0
        
        # Phần lớn các thống kê đã được cập nhật trong quá trình

    def plot_equity_curve(self, save_path=None):
        """Vẽ đồ thị equity curve"""
        plt.figure(figsize=(12, 8))
        
        # Chuyển timestamps sang định dạng datetime
        timestamps = pd.to_datetime(self.data['timestamp'])
        
        # Tiểu đồ thị Equity
        plt.subplot(2, 1, 1)
        plt.plot(timestamps[:len(self.equity_curve)], self.equity_curve, label='Equity', color='blue')
        plt.title(f'Equity Curve - {self.symbol} - {self.strategy_name}')
        plt.grid(True)
        plt.legend()
        
        # Tiểu đồ thị Drawdown
        plt.subplot(2, 1, 2)
        plt.plot(timestamps[:len(self.drawdown_curve)], self.drawdown_curve, label='Drawdown (%)', color='red')
        plt.title(f'Drawdown - Max: {self.max_drawdown_pct:.2f}%')
        plt.grid(True)
        plt.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f'Đã lưu biểu đồ equity curve tại {save_path}')
        
        plt.close()
    
    def plot_trade_distribution(self, save_path=None):
        """Vẽ phân phối lợi nhuận các lệnh"""
        if not self.trades_history:
            logger.warning('Không có lệnh để vẽ phân phối lợi nhuận')
            return
        
        plt.figure(figsize=(12, 8))
        
        # Phân loại PnL theo loại
        long_pnl = [trade['pnl'] for trade in self.trades_history if trade['type'] == 'LONG']
        short_pnl = [trade['pnl'] for trade in self.trades_history if trade['type'] == 'SHORT']
        
        # Tiểu đồ thị phân phối tất cả lệnh
        plt.subplot(2, 1, 1)
        all_pnl = [trade['pnl'] for trade in self.trades_history]
        plt.hist(all_pnl, bins=20, alpha=0.7, label=f'All Trades (n={len(all_pnl)})')
        plt.axvline(x=0, color='r', linestyle='--')
        plt.grid(True)
        plt.title(f'PnL Distribution - {self.symbol} - {self.strategy_name}')
        plt.legend()
        
        # Tiểu đồ thị phân loại theo LONG/SHORT
        plt.subplot(2, 1, 2)
        if long_pnl:
            plt.hist(long_pnl, bins=15, alpha=0.7, label=f'LONG (n={len(long_pnl)})', color='green')
        if short_pnl:
            plt.hist(short_pnl, bins=15, alpha=0.7, label=f'SHORT (n={len(short_pnl)})', color='red')
        plt.axvline(x=0, color='r', linestyle='--')
        plt.grid(True)
        plt.title('PnL by Direction')
        plt.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f'Đã lưu biểu đồ phân phối lợi nhuận tại {save_path}')
        
        plt.close()

# Định nghĩa các chiến lược

class SimpleStrategy:
    def __init__(self, fast_period=10, slow_period=20):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signals = []
        self.last_signal = None
        
        logger.info(f'Khởi tạo SimpleStrategy với fast_period={fast_period}, slow_period={slow_period}')
    
    def prepare(self, data):
        """Chuẩn bị dữ liệu trước khi bắt đầu backtest"""
        # Tính các chỉ báo trước
        data['fast_ma'] = data['close'].rolling(self.fast_period).mean()
        data['slow_ma'] = data['close'].rolling(self.slow_period).mean()
        
        # Tính RSI
        delta = data['close'].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rs = ema_up / ema_down
        data['rsi'] = 100 - (100 / (1 + rs))
        
        logger.info(f'Đã tính xong các chỉ báo cho SimpleStrategy')
    
    def generate_signal(self, data, index):
        if index < self.slow_period:
            return None, {}
        
        # Lấy giá trị đã được tính sẵn
        current_fast = data['fast_ma'].iloc[index]
        current_slow = data['slow_ma'].iloc[index]
        prev_fast = data['fast_ma'].iloc[index-1]
        prev_slow = data['slow_ma'].iloc[index-1]
        
        current_rsi = data['rsi'].iloc[index]
        current_close = data['close'].iloc[index]
        
        signal = None
        signal_data = {
            'fast_ma': current_fast,
            'slow_ma': current_slow,
            'rsi': current_rsi,
            'close': current_close
        }
        
        # Logic tín hiệu
        if prev_fast <= prev_slow and current_fast > current_slow:
            if current_rsi < 70:  # Không mua khi RSI quá cao
                signal = 'LONG'
        elif prev_fast >= prev_slow and current_fast < current_slow:
            if current_rsi > 30:  # Không bán khi RSI quá thấp
                signal = 'SHORT'
        
        if signal:
            self.last_signal = signal
        
        return signal, signal_data

class AdaptiveStrategy:
    def __init__(self, fast_period=10, medium_period=20, slow_period=50):
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period
        self.signals = []
        self.last_signal = None
        self.market_regime = 'NEUTRAL'
        
        self.vwap_period = 20  # VWAP 20 candle
        self.bb_period = 20     # Bollinger Bands 20 candle
        self.bb_std = 2        # 2 độ lệch chuẩn
        
        logger.info(f'Khởi tạo AdaptiveStrategy với periods={fast_period}/{medium_period}/{slow_period}')
    
    def prepare(self, data):
        """Chuẩn bị dữ liệu trước khi bắt đầu backtest"""
        # Tính các MA
        data['fast_ma'] = data['close'].rolling(self.fast_period).mean()
        data['medium_ma'] = data['close'].rolling(self.medium_period).mean()
        data['slow_ma'] = data['close'].rolling(self.slow_period).mean()
        
        # Tính RSI
        delta = data['close'].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rs = ema_up / ema_down
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Tính VWAP
        data['vwap'] = (data['close'] * data['volume']).rolling(window=self.vwap_period).sum() / data['volume'].rolling(window=self.vwap_period).sum()
        
        # Tính Bollinger Bands
        data['sma'] = data['close'].rolling(window=self.bb_period).mean()
        data['std'] = data['close'].rolling(window=self.bb_period).std()
        data['upper_bb'] = data['sma'] + (data['std'] * self.bb_std)
        data['lower_bb'] = data['sma'] - (data['std'] * self.bb_std)
        
        # Tính Volatility
        data['volatility'] = data['close'].rolling(20).std() / data['close'].rolling(20).mean() * 100
        
        logger.info(f'Đã tính xong các chỉ báo cho AdaptiveStrategy')
    
    def detect_market_regime(self, data, index):
        if index < self.slow_period + 20:
            return 'NEUTRAL'
        
        # Lấy giá trị đã được tính sẵn
        current_close = data['close'].iloc[index]
        current_slow_ma = data['slow_ma'].iloc[index]
        current_volatility = data['volatility'].iloc[index]
        
        # Kiểm tra vị trí giá so với BB
        upper_bb = data['upper_bb'].iloc[index]
        lower_bb = data['lower_bb'].iloc[index]
        
        # Đánh giá xu hướng dựa trên MA và Volatility
        if current_close > current_slow_ma * 1.05:
            if current_volatility < 2.5:
                return 'STRONG_BULL'
            else:
                return 'VOLATILE_BULL'
        elif current_close > current_slow_ma * 1.01:
            return 'WEAK_BULL'
        elif current_close < current_slow_ma * 0.95:
            if current_volatility < 2.5:
                return 'STRONG_BEAR'
            else:
                return 'VOLATILE_BEAR'
        elif current_close < current_slow_ma * 0.99:
            return 'WEAK_BEAR'
        else:
            # Đánh giá dao động dựa trên BB
            if current_close > upper_bb:
                return 'OVERBOUGHT'
            elif current_close < lower_bb:
                return 'OVERSOLD'
            elif current_volatility > 2:
                return 'CHOPPY'
            else:
                return 'NEUTRAL'
    
    def generate_signal(self, data, index):
        if index < self.slow_period + 20:
            return None, {}
        
        # Cập nhật market regime
        self.market_regime = self.detect_market_regime(data, index)
        
        # Lấy giá trị đã được tính sẵn
        current_close = data['close'].iloc[index]
        current_fast = data['fast_ma'].iloc[index]
        current_medium = data['medium_ma'].iloc[index]
        current_slow = data['slow_ma'].iloc[index]
        current_rsi = data['rsi'].iloc[index]
        
        prev_fast = data['fast_ma'].iloc[index-1]
        prev_medium = data['medium_ma'].iloc[index-1]
        
        # Tạo dữ liệu signal
        signal_data = {
            'fast_ma': current_fast,
            'medium_ma': current_medium,
            'slow_ma': current_slow,
            'rsi': current_rsi,
            'close': current_close,
            'market_regime': self.market_regime
        }
        
        signal = None
        
        # Chiến lược thích ứng theo market regime
        if self.market_regime in ['STRONG_BULL', 'VOLATILE_BULL', 'WEAK_BULL']:
            # Xu hướng tăng - ưu tiên LONG
            if prev_fast <= prev_medium and current_fast > current_medium:
                if current_rsi < 75:  # Thận trọng hơn trong thị trường tăng
                    signal = 'LONG'
            # SHORT chỉ khi có tín hiệu mạnh và RSI cao
            elif prev_fast >= prev_medium and current_fast < current_medium:
                if current_rsi > 75 and self.market_regime == 'VOLATILE_BULL':
                    signal = 'SHORT'
        
        elif self.market_regime in ['STRONG_BEAR', 'VOLATILE_BEAR', 'WEAK_BEAR']:
            # Xu hướng giảm - ưu tiên SHORT
            if prev_fast >= prev_medium and current_fast < current_medium:
                if current_rsi > 25:  # Thận trọng hơn trong thị trường giảm
                    signal = 'SHORT'
            # LONG chỉ khi có tín hiệu mạnh và RSI thấp
            elif prev_fast <= prev_medium and current_fast > current_medium:
                if current_rsi < 25 and self.market_regime == 'VOLATILE_BEAR':
                    signal = 'LONG'
        
        elif self.market_regime in ['OVERBOUGHT', 'OVERSOLD']:
            # Trong vùng quá mua/quá bán, áp dụng chiến lược phản xu hướng
            if self.market_regime == 'OVERBOUGHT' and current_rsi > 70:
                signal = 'SHORT'
            elif self.market_regime == 'OVERSOLD' and current_rsi < 30:
                signal = 'LONG'
        
        else:  # NEUTRAL hoặc CHOPPY
            # Trong thị trường dao động, áp dụng chiến lược phản xu hướng
            if self.market_regime == 'CHOPPY':
                if current_rsi < 30:
                    signal = 'LONG'
                elif current_rsi > 70:
                    signal = 'SHORT'
            else:
                # Trong thị trường trung tính, áp dụng chiến lược theo xu hướng nhưng thận trọng
                if prev_fast <= prev_medium and current_fast > current_medium:
                    if current_rsi < 65:
                        signal = 'LONG'
                elif prev_fast >= prev_medium and current_fast < current_medium:
                    if current_rsi > 35:
                        signal = 'SHORT'
        
        if signal:
            self.last_signal = signal
        
        return signal, signal_data

# Định nghĩa chiến lược kết hợp
class CombinedStrategy:
    def __init__(self, fast_period=10, medium_period=20, slow_period=50):
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period
        self.last_signal = None
        
        # Tạo cả hai chiến lược
        self.simple_strategy = SimpleStrategy(fast_period, medium_period)
        self.adaptive_strategy = AdaptiveStrategy(fast_period, medium_period, slow_period)
        
        logger.info(f'Khởi tạo CombinedStrategy với periods={fast_period}/{medium_period}/{slow_period}')
    
    def prepare(self, data):
        """Chuẩn bị dữ liệu cho cả hai chiến lược"""
        self.simple_strategy.prepare(data)
        self.adaptive_strategy.prepare(data)
    
    def generate_signal(self, data, index):
        if index < self.slow_period + 20:
            return None, {}
        
        # Lấy tín hiệu từ cả hai chiến lược
        simple_signal, simple_data = self.simple_strategy.generate_signal(data, index)
        adaptive_signal, adaptive_data = self.adaptive_strategy.generate_signal(data, index)
        
        # Logic kết hợp:
        # Nếu cả hai chiến lược đều đưa ra cùng tín hiệu, theo tín hiệu đó
        # Nếu chỉ một chiến lược đưa ra tín hiệu, kiểm tra điều kiện bổ sung
        # Nếu hai chiến lược mâu thuẫn, không đưa ra tín hiệu
        
        signal = None
        combined_data = {**simple_data, **adaptive_data, 'simple_signal': simple_signal, 'adaptive_signal': adaptive_signal}
        
        if simple_signal == adaptive_signal and simple_signal is not None:
            # Cả hai chiến lược đồng ý
            signal = simple_signal
            combined_data['signal_strength'] = 'STRONG'
        elif simple_signal is not None and adaptive_signal is None:
            # Chỉ có SimpleStrategy đưa ra tín hiệu
            # Kiểm tra thêm điều kiện để tăng độ tin cậy
            if (simple_signal == 'LONG' and combined_data['rsi'] < 60) or \
               (simple_signal == 'SHORT' and combined_data['rsi'] > 40):
                signal = simple_signal
                combined_data['signal_strength'] = 'MEDIUM'
        elif simple_signal is None and adaptive_signal is not None:
            # Chỉ có AdaptiveStrategy đưa ra tín hiệu
            # Kiểm tra thêm điều kiện
            current_regime = combined_data.get('market_regime', 'NEUTRAL')
            if (adaptive_signal == 'LONG' and current_regime not in ['STRONG_BEAR', 'VOLATILE_BEAR']) or \
               (adaptive_signal == 'SHORT' and current_regime not in ['STRONG_BULL', 'VOLATILE_BULL']):
                signal = adaptive_signal
                combined_data['signal_strength'] = 'MEDIUM'
        elif simple_signal != adaptive_signal and simple_signal is not None and adaptive_signal is not None:
            # Mâu thuẫn - không đưa ra tín hiệu
            combined_data['signal_conflict'] = True
        
        if signal:
            self.last_signal = signal
        
        return signal, combined_data

# Tiến hành backtest
print('\n3. TIẾN HÀNH BACKTEST CHI TIẾT')

try:
    # Chuẩn bị các chiến lược để test
    strategies = [
        ('SimpleStrategy', SimpleStrategy(fast_period=10, slow_period=20)),
        ('AdaptiveStrategy', AdaptiveStrategy(fast_period=10, medium_period=20, slow_period=50)),
        ('CombinedStrategy', CombinedStrategy(fast_period=10, medium_period=20, slow_period=50))
    ]
    
    # Backtest cho cả BTC và ETH
    symbols = [
        ('BTCUSDT', btc_data),
        ('ETHUSDT', eth_data)
    ]
    
    all_results = {}
    
    # Chạy backtest cho từng cặp symbol và strategy
    for symbol_name, symbol_data in symbols:
        print(f'\n- Chạy backtest cho {symbol_name}:')
        symbol_results = {}
        
        for strategy_name, strategy in strategies:
            print(f'  + Đang chạy {strategy_name}...')
            
            # Khởi tạo backtest engine
            engine = BacktestEngine(symbol_data, symbol_name, initial_balance=10000, leverage=5)
            
            # Thiết lập các thông số
            engine.risk_per_trade = 0.02   # 2% của balance
            engine.sl_pct = 0.015          # 1.5% SL
            engine.tp_pct = 0.03           # 3% TP
            engine.enable_trailing_stop = True
            engine.trailing_trigger = 0.02  # Kích hoạt trailing khi lời 2%
            engine.trailing_step = 0.005    # Di chuyển 0.5% mỗi bước
            
            # Chạy backtest
            result = engine.run(strategy, debug_level=1)
            symbol_results[strategy_name] = result
            
            # Lưu biểu đồ
            engine.plot_equity_curve(f'./backtest_charts/{symbol_name}_{strategy_name}_equity.png')
            engine.plot_trade_distribution(f'./backtest_charts/{symbol_name}_{strategy_name}_trades.png')
            
            # Hiển thị kết quả tóm tắt
            print(f'  - Tổng số giao dịch: {result["total_trades"]}')
            print(f'  - Win rate: {result["win_rate"]*100:.2f}%')
            print(f'  - Lợi nhuận: ${result["profit_loss"]:.2f} ({result["profit_loss_pct"]:.2f}%)')
            print(f'  - Drawdown tối đa: {result["max_drawdown_pct"]:.2f}%')
            print(f'  - Profit factor: {result["profit_factor"]:.2f}')
        
        all_results[symbol_name] = symbol_results
    
    # So sánh các chiến lược
    print('\n4. SO SÁNH CÁC CHIẾN LƯỢC')
    
    # So sánh cho từng symbol
    for symbol_name, symbol_results in all_results.items():
        print(f'\n- Kết quả cho {symbol_name}:')
        print('-' * 80)
        print(f'{"Chiến lược":20} | {"Tổng GD":8} | {"Win Rate":8} | {"Lợi nhuận":12} | {"Drawdown":8} | {"P.Factor":8} | {"Consec.Loss":8}')
        print('-' * 80)
        
        for strategy_name, result in symbol_results.items():
            profit = f'${result["profit_loss"]:.2f}'
            profit_pct = f'{result["profit_loss_pct"]:.2f}%'
            drawdown = f'{result["max_drawdown_pct"]:.2f}%'
            win_rate = f'{result["win_rate"]*100:.2f}%'
            profit_factor = f'{result["profit_factor"]:.2f}'
            consecutive_losses = f'{result["max_consecutive_losses"]}'
            
            print(f'{strategy_name:20} | {result["total_trades"]:8d} | {win_rate:8} | {profit_pct:12} | {drawdown:8} | {profit_factor:8} | {consecutive_losses:8}')
        
        print('-' * 80)
    
    # Tìm chiến lược tốt nhất cho mỗi symbol
    best_strategies = {}
    for symbol_name, symbol_results in all_results.items():
        best_strategy = max(symbol_results.items(), key=lambda x: x[1]['profit_loss_pct'])
        best_strategies[symbol_name] = best_strategy[0]
    
    print('\n- Chiến lược hiệu quả nhất cho mỗi symbol:')
    for symbol_name, strategy_name in best_strategies.items():
        result = all_results[symbol_name][strategy_name]
        print(f'  + {symbol_name}: {strategy_name} với lợi nhuận {result["profit_loss_pct"]:.2f}% và win rate {result["win_rate"]*100:.2f}%')
    
    # Phân tích các giao dịch thua lỗ
    print('\n5. PHÂN TÍCH GIAO DỊCH THUA LỖ')
    
    for symbol_name, symbol_results in all_results.items():
        for strategy_name, result in symbol_results.items():
            losing_trades = [trade for trade in result['trades_history'] if trade['pnl'] < 0]
            if losing_trades:
                print(f'\n- {symbol_name} - {strategy_name} - Phân tích {len(losing_trades)} giao dịch thua lỗ:')
                
                # Phân loại theo lý do thoát
                exit_reason_counts = {}
                for trade in losing_trades:
                    reason = trade['exit_reason']
                    if reason not in exit_reason_counts:
                        exit_reason_counts[reason] = 0
                    exit_reason_counts[reason] += 1
                
                print('  + Phân loại theo lý do thoát:')
                for reason, count in exit_reason_counts.items():
                    print(f'    - {reason}: {count} lệnh ({count/len(losing_trades)*100:.1f}%)')
                
                # Phân tích market regime khi vào lệnh thua
                if strategy_name == 'AdaptiveStrategy' or strategy_name == 'CombinedStrategy':
                    regime_counts = {}
                    for i, trade in enumerate(losing_trades):
                        # Tìm signal data tương ứng với thời điểm vào lệnh
                        entry_time = trade['entry_time']
                        matching_signals = [s for s in result['signal_history'] if s['timestamp'] == entry_time]
                        
                        if matching_signals and 'market_regime' in matching_signals[0]['signal_data']:
                            regime = matching_signals[0]['signal_data']['market_regime']
                            if regime not in regime_counts:
                                regime_counts[regime] = 0
                            regime_counts[regime] += 1
                    
                    if regime_counts:
                        print('  + Phân loại theo market regime:')
                        for regime, count in regime_counts.items():
                            print(f'    - {regime}: {count} lệnh ({count/len(losing_trades)*100:.1f}%)')
    
    # Phân tích chồng chéo và mâu thuẫn giữa các chiến lược
    print('\n6. PHÂN TÍCH CHỒNG CHÉO VÀ MÂU THUẪN')
    
    for symbol_name, symbol_results in all_results.items():
        if 'SimpleStrategy' in symbol_results and 'AdaptiveStrategy' in symbol_results:
            print(f'\n- Phân tích chồng chéo cho {symbol_name}:')
            
            simple_result = symbol_results['SimpleStrategy']
            adaptive_result = symbol_results['AdaptiveStrategy']
            
            # Tạo dictionary ánh xạ timestamp -> signal cho mỗi chiến lược
            simple_signals = {s['timestamp']: s['signal'] for s in simple_result['signal_history']}
            adaptive_signals = {s['timestamp']: s['signal'] for s in adaptive_result['signal_history']}
            
            # Tìm các tín hiệu trùng nhau
            matching_signals = 0
            conflicting_signals = 0
            
            # Đếm số tín hiệu
            simple_signal_count = sum(1 for s in simple_signals.values() if s in ['LONG', 'SHORT'])
            adaptive_signal_count = sum(1 for s in adaptive_signals.values() if s in ['LONG', 'SHORT'])
            
            # Kiểm tra từng timestamp
            for timestamp, simple_signal in simple_signals.items():
                if simple_signal in ['LONG', 'SHORT'] and timestamp in adaptive_signals:
                    adaptive_signal = adaptive_signals[timestamp]
                    if adaptive_signal in ['LONG', 'SHORT']:
                        if simple_signal == adaptive_signal:
                            matching_signals += 1
                        else:
                            conflicting_signals += 1
            
            print(f'  + Tổng số tín hiệu SimpleStrategy: {simple_signal_count}')
            print(f'  + Tổng số tín hiệu AdaptiveStrategy: {adaptive_signal_count}')
            print(f'  + Số tín hiệu trùng khớp: {matching_signals}')
            print(f'  + Số tín hiệu mâu thuẫn: {conflicting_signals}')
            
            # Tính tỷ lệ
            if simple_signal_count > 0 and adaptive_signal_count > 0:
                overlap_rate = matching_signals / min(simple_signal_count, adaptive_signal_count) * 100
                conflict_rate = conflicting_signals / min(simple_signal_count, adaptive_signal_count) * 100
                print(f'  + Tỷ lệ trùng khớp: {overlap_rate:.2f}%')
                print(f'  + Tỷ lệ mâu thuẫn: {conflict_rate:.2f}%')
    
    # Phân tích hiệu quả CombinedStrategy
    print('\n7. PHÂN TÍCH HIỆU QUẢ COMBINEDSTRATEGY')
    
    for symbol_name, symbol_results in all_results.items():
        if 'CombinedStrategy' in symbol_results:
            combined_result = symbol_results['CombinedStrategy']
            
            print(f'\n- Phân tích CombinedStrategy cho {symbol_name}:')
            
            # Phân loại theo signal_strength và đếm số lệnh
            signal_strengths = {}
            for signal in combined_result['signal_history']:
                if signal['signal'] in ['LONG', 'SHORT'] and 'signal_data' in signal:
                    signal_data = signal['signal_data']
                    strength = signal_data.get('signal_strength', 'UNKNOWN')
                    
                    if strength not in signal_strengths:
                        signal_strengths[strength] = {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0}
                    
                    signal_strengths[strength]['count'] += 1
                    
                    # Tìm giao dịch tương ứng
                    for trade in combined_result['trades_history']:
                        if trade['entry_time'] == signal['timestamp']:
                            if trade['pnl'] > 0:
                                signal_strengths[strength]['win'] += 1
                            elif trade['pnl'] < 0:
                                signal_strengths[strength]['loss'] += 1
                            
                            signal_strengths[strength]['total_pnl'] += trade['pnl']
                            break
            
            # Hiển thị kết quả
            print('  + Phân loại theo độ mạnh tín hiệu:')
            for strength, stats in signal_strengths.items():
                if stats['count'] > 0:
                    win_rate = stats['win'] / stats['count'] * 100 if stats['count'] > 0 else 0
                    avg_pnl = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0
                    
                    print(f'    - {strength}: {stats["count"]} lệnh, Win rate: {win_rate:.2f}%, Avg PnL: ${avg_pnl:.2f}')
    
    # Kết luận tổng quan
    print('\n8. KẾT LUẬN VÀ ĐỀ XUẤT')
    
    # Tìm chiến lược tốt nhất tổng thể
    best_strategy_overall = None
    best_avg_profit = -float('inf')
    
    for strategy_name in strategies[0][0], strategies[1][0], strategies[2][0]:
        avg_profit = sum(all_results[symbol][strategy_name]['profit_loss_pct'] for symbol in all_results) / len(all_results)
        if avg_profit > best_avg_profit:
            best_avg_profit = avg_profit
            best_strategy_overall = strategy_name
    
    print(f'- Chiến lược hiệu quả nhất tổng thể: {best_strategy_overall} với lợi nhuận trung bình {best_avg_profit:.2f}%')
    
    # Vấn đề đã phát hiện
    print('\n- Vấn đề đã phát hiện:')
    
    # Kiểm tra vấn đề chồng chéo
    if 'conflict_rate' in locals() and conflict_rate > 20:
        print(f'  + Tỷ lệ mâu thuẫn giữa các chiến lược cao ({conflict_rate:.2f}%)')
    
    # Kiểm tra vấn đề consecutive losses
    max_consecutive_losses = 0
    for symbol_name, symbol_results in all_results.items():
        for strategy_name, result in symbol_results.items():
            max_consecutive_losses = max(max_consecutive_losses, result['max_consecutive_losses'])
    
    if max_consecutive_losses >= 5:
        print(f'  + Số lần thua liên tiếp cao ({max_consecutive_losses}), cần cải thiện quản lý rủi ro')
    
    # Kiểm tra profit factor
    min_profit_factor = float('inf')
    for symbol_name, symbol_results in all_results.items():
        for strategy_name, result in symbol_results.items():
            if result['profit_factor'] < min_profit_factor:
                min_profit_factor = result['profit_factor']
    
    if min_profit_factor < 1.5:
        print(f'  + Profit factor thấp ({min_profit_factor:.2f}), cần cải thiện tỷ lệ lời/lỗ')
    
    # Đề xuất
    print('\n- Đề xuất cải tiến:')
    recommendations = []
    
    # So sánh AdaptiveStrategy và SimpleStrategy
    if all(all_results[symbol]['AdaptiveStrategy']['profit_loss_pct'] > all_results[symbol]['SimpleStrategy']['profit_loss_pct'] for symbol in all_results):
        recommendations.append('Sử dụng AdaptiveStrategy thay vì SimpleStrategy vì có lợi nhuận cao hơn trên tất cả các cặp')
    
    # Kiểm tra hiệu quả của CombinedStrategy
    if best_strategy_overall == 'CombinedStrategy':
        recommendations.append('CombinedStrategy tỏ ra hiệu quả nhất, tiếp tục tối ưu logic kết hợp')
    elif 'signal_strengths' in locals() and 'STRONG' in signal_strengths and signal_strengths['STRONG']['count'] > 0:
        strong_win_rate = signal_strengths['STRONG']['win'] / signal_strengths['STRONG']['count'] * 100
        if strong_win_rate > 70:
            recommendations.append(f'Tín hiệu STRONG trong CombinedStrategy có win rate cao ({strong_win_rate:.2f}%), nên ưu tiên')
    
    # Đề xuất dựa trên market regime
    if 'regime_counts' in locals() and regime_counts:
        problematic_regimes = [regime for regime, count in regime_counts.items() if count >= 3]
        if problematic_regimes:
            recommendations.append(f'Tránh giao dịch trong các market regime: {", ".join(problematic_regimes)}')
    
    # Đề xuất dựa trên thời gian giao dịch
    avg_durations = {}
    for symbol_name, symbol_results in all_results.items():
        for strategy_name, result in symbol_results.items():
            if 'avg_trade_duration' in result:
                if strategy_name not in avg_durations:
                    avg_durations[strategy_name] = []
                avg_durations[strategy_name].append(result['avg_trade_duration'])
    
    for strategy_name, durations in avg_durations.items():
        avg_duration = sum(durations) / len(durations)
        if avg_duration < 5:
            recommendations.append(f'{strategy_name} có thời gian giao dịch trung bình ngắn ({avg_duration:.1f} candles), cần tối ưu trailing stop')
    
    # Đề xuất chung
    recommendations.append('Thêm bộ lọc xu hướng dài hạn (ví dụ: MA 100) để tránh giao dịch trong thị trường sideway')
    recommendations.append('Tối ưu các thông số trailing stop để cải thiện lợi nhuận')
    recommendations.append('Cần có cơ chế giảm kích thước vị thế sau các lần thua liên tiếp')
    
    for i, rec in enumerate(recommendations):
        print(f'  {i+1}. {rec}')
    
    # Xuất báo cáo tổng hợp
    print('\n9. TẠO BÁO CÁO TỔNG HỢP')
    
    report_path = './backtest_reports/detailed_backtest_report.json'
    try:
        # Chuyển đổi các kết quả thành định dạng có thể serialize
        serializable_results = {}
        for symbol_name, symbol_results in all_results.items():
            serializable_results[symbol_name] = {}
            for strategy_name, result in symbol_results.items():
                # Loại bỏ các mảng dài và không cần thiết
                serializable_result = {k: v for k, v in result.items() if k not in ['equity_curve', 'drawdown_curve', 'signal_history']}
                
                # Chỉ lưu một số giao dịch để giảm kích thước
                trades_sample = result['trades_history'][:10] if len(result['trades_history']) > 10 else result['trades_history']
                serializable_result['trades_sample'] = trades_sample
                
                serializable_results[symbol_name][strategy_name] = serializable_result
        
        # Lưu kết quả
        with open(report_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f'- Đã lưu báo cáo chi tiết tại {report_path}')
    except Exception as e:
        print(f'- Lỗi khi lưu báo cáo: {str(e)}')
    
    # Tạo báo cáo tóm tắt
    summary_path = './backtest_reports/backtest_summary.txt'
    try:
        with open(summary_path, 'w') as f:
            f.write('=== BÁO CÁO TÓM TẮT BACKTEST CHI TIẾT ===\n\n')
            
            f.write('1. KẾT QUẢ TỔNG QUAN\n')
            f.write('-' * 80 + '\n')
            f.write(f'{"Symbol":10} | {"Chiến lược":20} | {"Tổng GD":8} | {"Win Rate":8} | {"Lợi nhuận":12} | {"Drawdown":8}\n')
            f.write('-' * 80 + '\n')
            
            for symbol_name, symbol_results in all_results.items():
                for strategy_name, result in symbol_results.items():
                    profit_pct = f'{result["profit_loss_pct"]:.2f}%'
                    drawdown = f'{result["max_drawdown_pct"]:.2f}%'
                    win_rate = f'{result["win_rate"]*100:.2f}%'
                    
                    f.write(f'{symbol_name:10} | {strategy_name:20} | {result["total_trades"]:8d} | {win_rate:8} | {profit_pct:12} | {drawdown:8}\n')
            
            f.write('-' * 80 + '\n\n')
            
            f.write('2. CHIẾN LƯỢC HIỆU QUẢ NHẤT\n')
            for symbol_name, strategy_name in best_strategies.items():
                result = all_results[symbol_name][strategy_name]
                f.write(f'- {symbol_name}: {strategy_name} với lợi nhuận {result["profit_loss_pct"]:.2f}% và win rate {result["win_rate"]*100:.2f}%\n')
            
            f.write(f'- Tổng thể: {best_strategy_overall} với lợi nhuận trung bình {best_avg_profit:.2f}%\n\n')
            
            f.write('3. THỐNG KÊ THEO LOẠI THOÁT LỆNH\n')
            for symbol_name, symbol_results in all_results.items():
                f.write(f'- {symbol_name}:\n')
                for strategy_name, result in symbol_results.items():
                    f.write(f'  + {strategy_name}:\n')
                    for reason, stats in result['exit_stats'].items():
                        if stats['count'] > 0:
                            win_rate = stats['win'] / stats['count'] * 100
                            avg_pnl = stats['total_pnl'] / stats['count']
                            f.write(f'    - {reason}: {stats["count"]} lệnh, Win rate: {win_rate:.2f}%, Avg PnL: ${avg_pnl:.2f}\n')
            
            f.write('\n4. VẤN ĐỀ ĐÃ PHÁT HIỆN\n')
            if 'conflict_rate' in locals() and conflict_rate > 20:
                f.write(f'- Tỷ lệ mâu thuẫn giữa các chiến lược cao ({conflict_rate:.2f}%)\n')
            if max_consecutive_losses >= 5:
                f.write(f'- Số lần thua liên tiếp cao ({max_consecutive_losses}), cần cải thiện quản lý rủi ro\n')
            if min_profit_factor < 1.5:
                f.write(f'- Profit factor thấp ({min_profit_factor:.2f}), cần cải thiện tỷ lệ lời/lỗ\n')
            
            f.write('\n5. ĐỀ XUẤT CẢI TIẾN\n')
            for i, rec in enumerate(recommendations):
                f.write(f'{i+1}. {rec}\n')
        
        print(f'- Đã lưu báo cáo tóm tắt tại {summary_path}')
        
    except Exception as e:
        print(f'- Lỗi khi lưu báo cáo tóm tắt: {str(e)}')
    
    print('\n=== KẾT THÚC BACKTEST CHI TIẾT ===')

except Exception as e:
    print(f'Lỗi khi thực hiện backtest: {str(e)}')
    import traceback
    traceback.print_exc()
