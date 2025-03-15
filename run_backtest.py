import os
import sys
import pandas as pd
import numpy as np
import datetime
import json
import logging
from pathlib import Path

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('backtest_system')

print('=== BẮT ĐẦU QUÁ TRÌNH BACKTEST TOÀN DIỆN ===')
print('1. Kiểm tra dữ liệu đầu vào')

# Lấy danh sách dữ liệu lịch sử có sẵn
data_dir = Path('./backtest_data')
if not data_dir.exists():
    os.makedirs(data_dir, exist_ok=True)
    print('- Đã tạo thư mục backtest_data')

# Kiểm tra xem đã có dữ liệu chưa
data_files = list(data_dir.glob('*.csv'))
if len(data_files) == 0:
    print('- Chưa có dữ liệu sẵn có, vui lòng tải dữ liệu trước')
    sys.exit(1)
else:
    print(f'- Đã tìm thấy {len(data_files)} file dữ liệu:')
    for file in data_files:
        print(f'  + {file.name}')

print('\n2. Tải mô-đun backtest')

# Định nghĩa các class cần thiết
class BacktestEngine:
    def __init__(self, data, initial_balance=10000, leverage=5):
        self.data = data
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.leverage = leverage
        self.positions = []
        self.current_position = None
        self.trades_history = []
        self.equity_curve = []
        
        # Thống kê
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.breakeven_trades = 0
        self.max_drawdown = 0
        self.max_drawdown_pct = 0
        self.peak_balance = initial_balance
        
        # Các cài đặt mặc định
        self.risk_per_trade = 0.02  # 2% của balance
        self.sl_pct = 0.015  # 1.5% SL
        self.tp_pct = 0.03  # 3% TP
        self.enable_trailing_stop = True
        self.trailing_trigger = 0.02  # Kích hoạt trailing khi lời 2%
        self.trailing_step = 0.005  # Di chuyển 0.5% mỗi bước
        
        logger.info(f'Khởi tạo Backtest Engine với balance={initial_balance}, leverage={leverage}')
    
    def run(self, strategy):
        logger.info(f'Bắt đầu chạy backtest với strategy={strategy.__class__.__name__}')
        self.equity_curve = [self.balance]
        
        for i in range(1, len(self.data)):
            # Cập nhật vị thế hiện tại nếu có
            if self.current_position:
                self._update_position(i)
            
            # Kiểm tra tín hiệu
            if not self.current_position:  # Chỉ mở vị thế mới nếu không có vị thế hiện tại
                signal = strategy.generate_signal(self.data, i)
                if signal in ['LONG', 'SHORT']:
                    self._open_position(signal, i)
            
            # Cập nhật equity curve
            self.equity_curve.append(self.calculate_equity(i))
        
        # Đóng vị thế cuối cùng nếu còn
        if self.current_position:
            self._close_position(self.data.iloc[-1]['close'], 'FINAL')
        
        # Tính toán thống kê
        self._calculate_statistics()
        
        logger.info('Hoàn thành backtest')
        return {
            'balance': self.balance,
            'equity_curve': self.equity_curve,
            'trades_history': self.trades_history,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'breakeven_trades': self.breakeven_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            'profit_loss': self.balance - self.initial_balance,
            'profit_loss_pct': (self.balance - self.initial_balance) / self.initial_balance * 100,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct
        }
    
    def _open_position(self, signal, index):
        entry_price = self.data.iloc[index]['close']
        
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
            'entry_time': self.data.iloc[index]['timestamp'],
            'size': position_size,
            'sl_price': sl_price,
            'initial_sl_price': sl_price,
            'tp_price': tp_price,
            'exit_price': None,
            'exit_time': None,
            'pnl': 0,
            'pnl_pct': 0,
            'status': 'OPEN',
            'highest_price': entry_price,
            'lowest_price': entry_price,
            'trailing_active': False,
            'trailing_stop': None
        }
        
        logger.info(f'Mở vị thế {signal} tại {entry_price} với size={position_size:.6f}, SL={sl_price:.2f}, TP={tp_price:.2f}')
    
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
                    logger.info(f'Đã kích hoạt Trailing Stop tại {current_price:.2f} với stop={self.current_position["trailing_stop"]:.2f}')
            else:  # SHORT
                profit_pct = (self.current_position['entry_price'] - current_price) / self.current_position['entry_price'] * 100
                if profit_pct >= self.trailing_trigger * 100:
                    # Kích hoạt trailing stop
                    self.current_position['trailing_active'] = True
                    self.current_position['trailing_stop'] = current_price * (1 + self.trailing_step)
                    logger.info(f'Đã kích hoạt Trailing Stop tại {current_price:.2f} với stop={self.current_position["trailing_stop"]:.2f}')
        
        # Cập nhật trailing stop nếu đã kích hoạt
        if self.current_position['trailing_active']:
            if self.current_position['type'] == 'LONG':
                new_trailing_stop = current_price * (1 - self.trailing_step)
                if new_trailing_stop > self.current_position['trailing_stop']:
                    self.current_position['trailing_stop'] = new_trailing_stop
                    logger.info(f'Cập nhật Trailing Stop lên {self.current_position["trailing_stop"]:.2f}')
            else:  # SHORT
                new_trailing_stop = current_price * (1 + self.trailing_step)
                if new_trailing_stop < self.current_position['trailing_stop']:
                    self.current_position['trailing_stop'] = new_trailing_stop
                    logger.info(f'Cập nhật Trailing Stop xuống {self.current_position["trailing_stop"]:.2f}')
            
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
        self.current_position['exit_time'] = self.data.iloc[self.data.shape[0]-1]['timestamp'] if reason == 'FINAL' else self.data.iloc[-1]['timestamp']
        self.current_position['pnl'] = pnl
        self.current_position['pnl_pct'] = pnl_pct
        self.current_position['status'] = 'CLOSED'
        self.current_position['exit_reason'] = reason
        
        # Thêm vào lịch sử
        self.trades_history.append(self.current_position.copy())
        
        # Cập nhật thống kê
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        elif pnl < 0:
            self.losing_trades += 1
        else:
            self.breakeven_trades += 1
        
        # Reset current position
        self.current_position = None
        
        logger.info(f'Đóng vị thế tại {exit_price:.2f} với lý do {reason}, PnL={pnl:.2f} ({pnl_pct:.2f}%), Balance={self.balance:.2f}')
    
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
        # Các thống kê đã được cập nhật trong quá trình
        pass

class SimpleStrategy:
    def __init__(self, fast_period=10, slow_period=20):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signals = []
        self.last_signal = None
        
        logger.info(f'Khởi tạo SimpleStrategy với fast_period={fast_period}, slow_period={slow_period}')
    
    def generate_signal(self, data, index):
        if index < self.slow_period:
            return None
        
        # Tính MA
        fast_ma = data['close'].rolling(self.fast_period).mean()
        slow_ma = data['close'].rolling(self.slow_period).mean()
        
        # Tính RSI
        delta = data['close'].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rs = ema_up / ema_down
        rsi = 100 - (100 / (1 + rs))
        
        # Logic tín hiệu
        current_fast = fast_ma.iloc[index]
        current_slow = slow_ma.iloc[index]
        prev_fast = fast_ma.iloc[index-1]
        prev_slow = slow_ma.iloc[index-1]
        
        current_rsi = rsi.iloc[index]
        
        # Tín hiệu giao cắt MA + điều kiện RSI
        if prev_fast <= prev_slow and current_fast > current_slow:
            if current_rsi < 70:  # Không mua khi RSI quá cao
                self.last_signal = 'LONG'
                return 'LONG'
        elif prev_fast >= prev_slow and current_fast < current_slow:
            if current_rsi > 30:  # Không bán khi RSI quá thấp
                self.last_signal = 'SHORT'
                return 'SHORT'
        
        return None

class AdaptiveStrategy:
    def __init__(self, fast_period=10, medium_period=20, slow_period=50):
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period
        self.signals = []
        self.last_signal = None
        self.market_regime = 'NEUTRAL'
        
        logger.info(f'Khởi tạo AdaptiveStrategy với periods={fast_period}/{medium_period}/{slow_period}')
    
    def detect_market_regime(self, data, index):
        if index < self.slow_period + 20:
            return 'NEUTRAL'
        
        # Tính các MA
        slow_ma = data['close'].rolling(self.slow_period).mean()
        
        # Tính stdev trong 20 candle
        volatility = data['close'].rolling(20).std() / data['close'].rolling(20).mean() * 100
        
        # Xác định xu hướng
        current_close = data['close'].iloc[index]
        current_slow_ma = slow_ma.iloc[index]
        
        current_volatility = volatility.iloc[index]
        
        # Đánh giá xu hướng
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
            if current_volatility > 2:
                return 'CHOPPY'
            else:
                return 'NEUTRAL'
    
    def generate_signal(self, data, index):
        if index < self.slow_period + 20:
            return None
        
        # Cập nhật market regime
        self.market_regime = self.detect_market_regime(data, index)
        
        # Tính MA
        fast_ma = data['close'].rolling(self.fast_period).mean()
        medium_ma = data['close'].rolling(self.medium_period).mean()
        slow_ma = data['close'].rolling(self.slow_period).mean()
        
        # Tính RSI
        delta = data['close'].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rs = ema_up / ema_down
        rsi = 100 - (100 / (1 + rs))
        
        # Logic tín hiệu thích ứng theo market regime
        current_close = data['close'].iloc[index]
        current_fast = fast_ma.iloc[index]
        current_medium = medium_ma.iloc[index]
        current_slow = slow_ma.iloc[index]
        
        prev_fast = fast_ma.iloc[index-1]
        prev_medium = medium_ma.iloc[index-1]
        
        current_rsi = rsi.iloc[index]
        
        signal = None
        
        # Chiến lược phụ thuộc vào market regime
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
        
        return signal

# Tiến hành backtest
print('\n3. Thực hiện backtest')

try:
    # Sử dụng dữ liệu có sẵn
    test_file = data_dir / 'BTCUSDT_1h.csv'
    
    if not test_file.exists():
        print(f'- Không tìm thấy file {test_file}')
        sys.exit(1)
    
    print(f'- Đang tải dữ liệu từ {test_file}')
    data = pd.read_csv(test_file)
    print(f'- Đã tải dữ liệu với {len(data)} dòng từ {data["timestamp"].min()} đến {data["timestamp"].max()}')
    
    # Chạy backtest với các chiến lược khác nhau
    strategies = [
        ('SimpleStrategy', SimpleStrategy(fast_period=10, slow_period=20)),
        ('AdaptiveStrategy', AdaptiveStrategy(fast_period=10, medium_period=20, slow_period=50))
    ]
    
    results = {}
    
    for name, strategy in strategies:
        print(f'- Chạy backtest với {name}')
        engine = BacktestEngine(data, initial_balance=10000, leverage=5)
        
        # Thiết lập các thông số
        engine.risk_per_trade = 0.02  # 2% của balance
        engine.sl_pct = 0.015  # 1.5% SL
        engine.tp_pct = 0.03  # 3% TP
        engine.enable_trailing_stop = True
        engine.trailing_trigger = 0.02  # Kích hoạt trailing khi lời 2%
        engine.trailing_step = 0.005  # Di chuyển 0.5% mỗi bước
        
        # Chạy backtest
        result = engine.run(strategy)
        results[name] = result
        
        # Hiển thị kết quả
        print(f'  + Tổng số giao dịch: {result["total_trades"]}')
        print(f'  + Giao dịch thắng: {result["winning_trades"]} ({result["win_rate"]*100:.2f}%)')
        print(f'  + Giao dịch thua: {result["losing_trades"]}')
        print(f'  + Lợi nhuận: ${result["profit_loss"]:.2f} ({result["profit_loss_pct"]:.2f}%)')
        print(f'  + Drawdown tối đa: ${result["max_drawdown"]:.2f} ({result["max_drawdown_pct"]:.2f}%)')
    
    # So sánh các chiến lược
    print('\n4. So sánh các chiến lược')
    
    print('-' * 80)
    print(f'{"Chiến lược":20} | {"Tổng GD":8} | {"Thắng":8} | {"Win Rate":8} | {"Lợi nhuận":12} | {"Drawdown":10}')
    print('-' * 80)
    
    for name, result in results.items():
        profit = f'${result["profit_loss"]:.2f}'
        profit_pct = f'{result["profit_loss_pct"]:.2f}%'
        drawdown = f'{result["max_drawdown_pct"]:.2f}%'
        win_rate = f'{result["win_rate"]*100:.2f}%'
        
        print(f'{name:20} | {result["total_trades"]:8d} | {result["winning_trades"]:8d} | {win_rate:8} | {profit:12} | {drawdown:10}')
    
    print('-' * 80)
    
    # Tìm ra chiến lược tốt nhất
    best_strategy = max(results.items(), key=lambda x: x[1]['profit_loss_pct'])
    print(f'\n- Chiến lược hiệu quả nhất: {best_strategy[0]} với lợi nhuận {best_strategy[1]["profit_loss_pct"]:.2f}%')
    
    # Phân tích lỗi và vấn đề
    print('\n5. Phân tích lỗi và vấn đề')
    
    # Tìm các giao dịch thua lỗ lớn
    worst_trades = []
    for name, result in results.items():
        trades = result['trades_history']
        
        # Sắp xếp theo PnL tăng dần (thua lỗ nhiều nhất lên đầu)
        sorted_trades = sorted(trades, key=lambda x: x['pnl'])
        
        # Lấy 3 giao dịch thua lỗ lớn nhất
        worst = sorted_trades[:3] if len(sorted_trades) >= 3 else sorted_trades
        
        for trade in worst:
            worst_trades.append({
                'strategy': name,
                'type': trade['type'],
                'entry_time': trade['entry_time'],
                'exit_time': trade['exit_time'],
                'entry_price': trade['entry_price'],
                'exit_price': trade['exit_price'],
                'pnl': trade['pnl'],
                'pnl_pct': trade['pnl_pct'],
                'exit_reason': trade.get('exit_reason', 'Unknown')
            })
    
    # Hiển thị các giao dịch thua lỗ lớn nhất
    if worst_trades:
        print('- Các giao dịch thua lỗ lớn nhất:')
        worst_trades = sorted(worst_trades, key=lambda x: x['pnl'])[:5]
        
        for i, trade in enumerate(worst_trades):
            print(f'  {i+1}. {trade["strategy"]} - {trade["type"]} từ {trade["entry_time"]} đến {trade["exit_time"]}')
            print(f'     Vào: {trade["entry_price"]:.2f}, Ra: {trade["exit_price"]:.2f}, PnL: ${trade["pnl"]:.2f} ({trade["pnl_pct"]:.2f}%)')
            print(f'     Lý do thoát: {trade["exit_reason"]}')
    
    # Kiểm tra thống kê giao dịch theo exit_reason
    print('\n- Thống kê giao dịch theo lý do thoát:')
    
    for name, result in results.items():
        trades = result['trades_history']
        exit_reasons = {}
        
        for trade in trades:
            reason = trade.get('exit_reason', 'Unknown')
            if reason not in exit_reasons:
                exit_reasons[reason] = {'count': 0, 'win': 0, 'lose': 0, 'total_pnl': 0}
            
            exit_reasons[reason]['count'] += 1
            if trade['pnl'] > 0:
                exit_reasons[reason]['win'] += 1
            else:
                exit_reasons[reason]['lose'] += 1
            
            exit_reasons[reason]['total_pnl'] += trade['pnl']
        
        print(f'  {name}:')
        for reason, stats in exit_reasons.items():
            win_rate = stats['win'] / stats['count'] * 100 if stats['count'] > 0 else 0
            avg_pnl = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0
            
            print(f'    {reason}: {stats["count"]} lệnh, Win rate: {win_rate:.2f}%, Avg PnL: ${avg_pnl:.2f}')
    
    # Kết luận tổng quan
    print('\n6. Kết luận và đề xuất')
    
    # Tìm chiến lược có win rate cao nhất
    best_win_rate = max(results.items(), key=lambda x: x[1]['win_rate'])
    
    # Tìm chiến lược có drawdown thấp nhất
    min_drawdown = min(results.items(), key=lambda x: x[1]['max_drawdown_pct'])
    
    print(f'- Chiến lược có win rate cao nhất: {best_win_rate[0]} ({best_win_rate[1]["win_rate"]*100:.2f}%)')
    print(f'- Chiến lược có drawdown thấp nhất: {min_drawdown[0]} ({min_drawdown[1]["max_drawdown_pct"]:.2f}%)')
    print(f'- Chiến lược có lợi nhuận cao nhất: {best_strategy[0]} ({best_strategy[1]["profit_loss_pct"]:.2f}%)')
    
    print('\n- Đề xuất:')
    recommendations = []
    
    # So sánh SimpleStrategy và AdaptiveStrategy
    if 'SimpleStrategy' in results and 'AdaptiveStrategy' in results:
        simple = results['SimpleStrategy']
        adaptive = results['AdaptiveStrategy']
        
        if adaptive['profit_loss_pct'] > simple['profit_loss_pct']:
            recommendations.append('Sử dụng AdaptiveStrategy thay vì SimpleStrategy vì có lợi nhuận cao hơn')
        else:
            if simple['win_rate'] > adaptive['win_rate']:
                recommendations.append('SimpleStrategy có win rate cao hơn nhưng lợi nhuận thấp hơn, có thể tối ưu thêm')
        
        if adaptive['max_drawdown_pct'] < simple['max_drawdown_pct']:
            recommendations.append('AdaptiveStrategy có drawdown thấp hơn, rủi ro thấp hơn')
    
    # Đề xuất chung
    recommendations.append('Nên thêm bộ lọc xu hướng dài hạn để tránh giao dịch trong thị trường sideway')
    recommendations.append('Tối ưu các thông số trailing stop để cải thiện lợi nhuận')
    recommendations.append('Nên có chiến lược riêng cho từng chế độ thị trường để tối đa hiệu suất')
    
    for i, rec in enumerate(recommendations):
        print(f'  {i+1}. {rec}')
    
    print('\n=== KẾT THÚC BACKTEST ===')

except Exception as e:
    print(f'Lỗi khi thực hiện backtest: {str(e)}')
