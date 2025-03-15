import os
import sys
import pandas as pd
import numpy as np
import json
import logging
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('conservative_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('risk_test')

print('=== BẮT ĐẦU BACKTEST CHO MỨC RỦI RO CONSERVATIVE (5%) ===')

# Thiết lập thư mục dữ liệu và kết quả
data_dir = Path('./backtest_data')
result_dir = Path('./risk_test_results')
chart_dir = Path('./risk_test_charts')

# Tạo thư mục nếu chưa tồn tại
for dir_path in [result_dir, chart_dir]:
    if not dir_path.exists():
        os.makedirs(dir_path)
        print(f'- Đã tạo thư mục {dir_path}')

# Kiểm tra dữ liệu
print("\n1. KIỂM TRA DỮ LIỆU")

# Tìm tất cả các file dữ liệu
data_files = list(data_dir.glob('*.csv'))
if not data_files:
    print("Không tìm thấy dữ liệu. Vui lòng đảm bảo có dữ liệu trong thư mục ./backtest_data")
    sys.exit(1)

# Hiển thị danh sách file dữ liệu
print(f"Tìm thấy {len(data_files)} file dữ liệu:")
for file in data_files:
    print(f"- {file.name}")

# Chọn file dữ liệu
btc_files = [f for f in data_files if 'BTC' in f.name.upper()]
eth_files = [f for f in data_files if 'ETH' in f.name.upper()]

if not btc_files:
    print("Không tìm thấy dữ liệu BTC.")
    sys.exit(1)

# Đọc dữ liệu
try:
    btc_file = btc_files[0]
    print(f"\nĐang đọc dữ liệu từ {btc_file.name}...")
    data = pd.read_csv(btc_file)
    print(f"Đã đọc {len(data)} dòng dữ liệu từ {data['timestamp'].min()} đến {data['timestamp'].max()}")
    
    # Kiểm tra cột cần thiết
    required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in data.columns]
    
    if missing_columns:
        print(f"Thiếu các cột: {', '.join(missing_columns)}")
        sys.exit(1)
    
    # Chuyển đổi timestamp sang datetime nếu cần
    if not pd.api.types.is_datetime64_dtype(data['timestamp']):
        data['timestamp'] = pd.to_datetime(data['timestamp'])
    
    print(f"Khoảng thời gian dữ liệu: {(data['timestamp'].max() - data['timestamp'].min()).days} ngày")
    
except Exception as e:
    print(f"Lỗi khi đọc dữ liệu: {str(e)}")
    sys.exit(1)

# Định nghĩa class AdaptiveStrategy
class AdaptiveStrategy:
    def __init__(self, fast_period=10, medium_period=20, slow_period=50):
        self.fast_period = fast_period
        self.medium_period = medium_period
        self.slow_period = slow_period
        self.signals = []
        self.last_signal = None
        self.market_regime = 'NEUTRAL'
        
        # Thêm các tham số mới
        self.atr_period = 14
        self.rsi_period = 14
        self.bb_period = 20
        self.bb_std = 2
        
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
        ema_up = up.ewm(com=self.rsi_period-1, adjust=False).mean()
        ema_down = down.ewm(com=self.rsi_period-1, adjust=False).mean()
        rs = ema_up / ema_down
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Tính ATR
        high_low = data['high'] - data['low']
        high_close = (data['high'] - data['close'].shift()).abs()
        low_close = (data['low'] - data['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(self.atr_period).mean()
        
        # Tính Bollinger Bands
        data['bb_middle'] = data['close'].rolling(self.bb_period).mean()
        data['bb_std'] = data['close'].rolling(self.bb_period).std()
        data['bb_upper'] = data['bb_middle'] + (data['bb_std'] * self.bb_std)
        data['bb_lower'] = data['bb_middle'] - (data['bb_std'] * self.bb_std)
        
        # Tính các chỉ báo trends
        data['ema50'] = data['close'].rolling(50).mean()
        data['ema100'] = data['close'].rolling(100).mean()
        data['ema200'] = data['close'].rolling(200).mean()
        
        # Tính Volatility
        data['volatility'] = data['close'].rolling(20).std() / data['close'].rolling(20).mean() * 100
        
        logger.info(f'Đã tính xong các chỉ báo cho AdaptiveStrategy')
    
    def detect_market_regime(self, data, index):
        if index < self.slow_period + 20:
            return 'NEUTRAL'
        
        # Lấy dữ liệu hiện tại
        current_close = data['close'].iloc[index]
        current_ema50 = data['ema50'].iloc[index]
        current_ema100 = data['ema100'].iloc[index]
        current_ema200 = data['ema200'].iloc[index]
        current_volatility = data['volatility'].iloc[index]
        current_bb_upper = data['bb_upper'].iloc[index]
        current_bb_lower = data['bb_lower'].iloc[index]
        
        # Xác định xu hướng dài hạn
        long_term_trend = 'NEUTRAL'
        if current_close > current_ema200 and current_ema50 > current_ema200:
            long_term_trend = 'BULL'
        elif current_close < current_ema200 and current_ema50 < current_ema200:
            long_term_trend = 'BEAR'
        
        # Xác định biến động
        volatility_state = 'NORMAL'
        if current_volatility > 3:
            volatility_state = 'HIGH'
        elif current_volatility < 1.5:
            volatility_state = 'LOW'
        
        # Kiểm tra trạng thái quá mua/quá bán
        if current_close > current_bb_upper:
            overbought_oversold = 'OVERBOUGHT'
        elif current_close < current_bb_lower:
            overbought_oversold = 'OVERSOLD'
        else:
            overbought_oversold = 'NORMAL'
        
        # Quyết định regime
        if long_term_trend == 'BULL':
            if volatility_state == 'HIGH':
                return 'VOLATILE_BULL'
            elif overbought_oversold == 'OVERBOUGHT':
                return 'OVERBOUGHT'
            else:
                return 'BULL'
        elif long_term_trend == 'BEAR':
            if volatility_state == 'HIGH':
                return 'VOLATILE_BEAR'
            elif overbought_oversold == 'OVERSOLD':
                return 'OVERSOLD'
            else:
                return 'BEAR'
        else:  # NEUTRAL
            if volatility_state == 'HIGH':
                return 'CHOPPY'
            elif volatility_state == 'LOW':
                return 'RANGING'
            else:
                return 'SIDEWAYS'
    
    def generate_signal(self, data, index):
        if index < self.slow_period + 20:
            return None, {}
        
        # Cập nhật market regime
        self.market_regime = self.detect_market_regime(data, index)
        
        # Lấy dữ liệu
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
            'market_regime': self.market_regime,
            'atr': data['atr'].iloc[index]
        }
        
        signal = None
        
        # Chiến lược thích ứng theo market regime
        if self.market_regime in ['BULL', 'VOLATILE_BULL', 'OVERBOUGHT']:
            # Thị trường tăng - ưu tiên LONG
            if prev_fast <= prev_medium and current_fast > current_medium:
                if current_rsi < 75:  # Không quá mua
                    signal = 'LONG'
            # SHORT chỉ khi có tín hiệu mạnh và RSI cao
            elif prev_fast >= prev_medium and current_fast < current_medium:
                if current_rsi > 75 and self.market_regime == 'OVERBOUGHT':
                    signal = 'SHORT'
        
        elif self.market_regime in ['BEAR', 'VOLATILE_BEAR', 'OVERSOLD']:
            # Thị trường giảm - ưu tiên SHORT
            if prev_fast >= prev_medium and current_fast < current_medium:
                if current_rsi > 25:  # Không quá bán
                    signal = 'SHORT'
            # LONG chỉ khi có tín hiệu mạnh và RSI thấp
            elif prev_fast <= prev_medium and current_fast > current_medium:
                if current_rsi < 25 and self.market_regime == 'OVERSOLD':
                    signal = 'LONG'
        
        else:  # SIDEWAYS, CHOPPY, RANGING, NEUTRAL
            # Thị trường dao động - dùng chiến lược phản xu hướng
            if self.market_regime == 'CHOPPY':
                # Trong thị trường hỗn loạn, hạn chế giao dịch
                if current_rsi < 30:
                    signal = 'LONG'
                elif current_rsi > 70:
                    signal = 'SHORT'
            else:
                # Thị trường đi ngang - theo giao cắt MA
                if prev_fast <= prev_medium and current_fast > current_medium:
                    if current_rsi < 65:
                        signal = 'LONG'
                elif prev_fast >= prev_medium and current_fast < current_medium:
                    if current_rsi > 35:
                        signal = 'SHORT'
        
        if signal:
            self.last_signal = signal
        
        return signal, signal_data

# Định nghĩa BacktestEngine với hỗ trợ nhiều cấp độ rủi ro
class BacktestEngine:
    def __init__(self, data, symbol, initial_balance=10000, leverage=5, risk_percentage=0.05):
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
        
        # Thống kê theo exit reason
        self.exit_stats = {
            'TP': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'SL': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'TP1': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'TP2': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'TP3': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'TRAILING_STOP': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'FINAL': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0}
        }
        
        # Thống kê theo thị trường
        self.market_stats = {
            'BULL': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'BEAR': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'SIDEWAYS': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0},
            'VOLATILE': {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0}
        }
        
        # Cấu hình rủi ro - mức Conservative (5%)
        self.risk_level = 'conservative'
        self.risk_percentage = risk_percentage
        logger.info(f'Sử dụng mức rủi ro: {self.risk_level} ({self.risk_percentage*100}%)')
        
        # Các cài đặt SL/TP
        self.base_sl_pct = 0.015  # 1.5% SL cơ bản
        self.base_tp_pct = self.base_sl_pct * 2  # 3% TP cơ bản (RR = 1:2)
        self.enable_trailing_stop = True
        self.trailing_trigger = 0.015  # Kích hoạt trailing khi lời 1.5%
        self.trailing_step = 0.003  # Di chuyển 0.3% mỗi bước
        
        # Thêm cơ chế đóng lệnh từng phần
        self.enable_partial_tp = True
        self.tp_levels = [0.4, 0.8, 1.0, 1.5]  # % của mục tiêu TP
        self.tp_percentages = [0.25, 0.25, 0.25, 0.25]  # % của vị thế đóng ở mỗi mức
        
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
        
        start_time = datetime.now()
        
        for i in range(1, len(self.data)):
            # Lưu thông tin ngày hiện tại để debug
            current_date = self.data.iloc[i]['timestamp']
            current_price = self.data.iloc[i]['close']
            
            # Mỗi 100 candle, ghi log tiến độ
            if i % 500 == 0 and debug_level > 0:
                progress = i / len(self.data) * 100
                time_elapsed = datetime.now() - start_time
                estimated_total = time_elapsed / (i / len(self.data))
                remaining = estimated_total - time_elapsed
                logger.info(f'Đang xử lý candle {i}/{len(self.data)} ({progress:.1f}%), '
                           f'ngày {current_date}, giá {current_price:.2f}. '
                           f'Thời gian còn lại: {remaining}')
            
            # Cập nhật vị thế hiện tại nếu có
            if self.current_position is not None:
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
            if self.current_position is None and signal in ['LONG', 'SHORT']:
                self._open_position(signal, i, signal_data)
            
            # Cập nhật equity curve và drawdown
            current_equity = self.calculate_equity(i)
            self.equity_curve.append(current_equity)
            
            # Tính drawdown
            peak_equity = max(self.equity_curve)
            current_drawdown = (peak_equity - current_equity) / peak_equity * 100 if peak_equity > 0 else 0
            self.drawdown_curve.append(current_drawdown)
        
        # Đóng vị thế cuối cùng nếu còn
        if self.current_position is not None:
            self._close_position(self.data.iloc[-1]['close'], 'FINAL', 1.0)
        
        # Tính toán thống kê
        self._calculate_statistics()
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        
        logger.info(f'Hoàn thành backtest cho {self.symbol} trong {elapsed_time}')
        
        return {
            'symbol': self.symbol,
            'strategy': self.strategy_name,
            'risk_level': self.risk_level,
            'risk_percentage': self.risk_percentage,
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
            'market_stats': self.market_stats
        }
    
    def _open_position(self, signal, index, signal_data=None):
        entry_price = self.data.iloc[index]['close']
        entry_time = self.data.iloc[index]['timestamp']
        
        # Lấy thông tin thị trường từ signal_data
        market_regime = signal_data.get('market_regime', 'NEUTRAL') if signal_data else 'NEUTRAL'
        
        # Điều chỉnh SL/TP theo thị trường
        sl_pct = self.base_sl_pct
        tp_pct = self.base_tp_pct
        
        if market_regime in ['VOLATILE_BULL', 'VOLATILE_BEAR', 'CHOPPY']:
            sl_pct *= 1.3  # Tăng SL trong thị trường biến động
            tp_pct *= 1.2  # Tăng TP nhưng ít hơn SL
        elif market_regime in ['SIDEWAYS', 'RANGING']:
            sl_pct *= 0.8  # Giảm SL trong thị trường ít biến động
            tp_pct *= 0.7  # Giảm TP nhiều hơn SL
        
        # Tính risk amount dựa trên mức rủi ro hiện tại
        risk_amount = self.balance * self.risk_percentage
        
        # Tính kích thước vị thế dựa trên risk
        position_size = risk_amount / (entry_price * sl_pct / self.leverage)
        
        # Giới hạn position size tối đa 20% tài khoản
        max_position_size = (self.balance * 0.2 * self.leverage) / entry_price
        position_size = min(position_size, max_position_size)
        
        # Tính SL/TP
        if signal == 'LONG':
            sl_price = entry_price * (1 - sl_pct)
            tp_price = entry_price * (1 + tp_pct)
            
            # Tính các mức TP từng phần
            tp1 = entry_price * (1 + tp_pct * self.tp_levels[0])
            tp2 = entry_price * (1 + tp_pct * self.tp_levels[1])
            tp3 = entry_price * (1 + tp_pct * self.tp_levels[2])
            tp4 = entry_price * (1 + tp_pct * self.tp_levels[3])
        else:  # SHORT
            sl_price = entry_price * (1 + sl_pct)
            tp_price = entry_price * (1 - tp_pct)
            
            # Tính các mức TP từng phần
            tp1 = entry_price * (1 - tp_pct * self.tp_levels[0])
            tp2 = entry_price * (1 - tp_pct * self.tp_levels[1])
            tp3 = entry_price * (1 - tp_pct * self.tp_levels[2])
            tp4 = entry_price * (1 - tp_pct * self.tp_levels[3])
        
        # Tạo vị thế
        self.current_position = {
            'type': signal,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'entry_index': index,
            'size': position_size,
            'remaining_size': position_size,  # Kích thước còn lại sau các lần TP từng phần
            'sl_price': sl_price,
            'initial_sl_price': sl_price,
            'tp_price': tp_price,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'tp4': tp4,
            'tp1_triggered': False,
            'tp2_triggered': False,
            'tp3_triggered': False,
            'exit_price': None,
            'exit_time': None,
            'exit_index': None,
            'pnl': 0,
            'pnl_pct': 0,
            'status': 'OPEN',
            'highest_price': entry_price,
            'lowest_price': entry_price,
            'trailing_active': False,
            'trailing_stop': None,
            'market_regime': market_regime
        }
        
        logger.info(f'Mở vị thế {signal} {self.symbol} tại {entry_price} với size={position_size:.6f}, '
                   f'SL={sl_price:.2f}, TP={tp_price:.2f}, Market={market_regime}')
        
        # Cập nhật thống kê theo thị trường
        market_group = market_regime.split('_')[0] if '_' in market_regime else market_regime
        if market_group in ['BULL', 'OVERBOUGHT']:
            self.market_stats['BULL']['count'] += 1
        elif market_group in ['BEAR', 'OVERSOLD']:
            self.market_stats['BEAR']['count'] += 1
        elif market_group in ['SIDEWAYS', 'RANGING', 'NEUTRAL']:
            self.market_stats['SIDEWAYS']['count'] += 1
        elif market_group in ['VOLATILE', 'CHOPPY']:
            self.market_stats['VOLATILE']['count'] += 1
    
    def _update_position(self, index):
        if self.current_position is None:
            return
        
        current_price = self.data.iloc[index]['close']
        high_price = self.data.iloc[index]['high']
        low_price = self.data.iloc[index]['low']
        
        # Cập nhật giá cao/thấp nhất
        if self.current_position['type'] == 'LONG':
            self.current_position['highest_price'] = max(self.current_position['highest_price'], high_price)
            self.current_position['lowest_price'] = min(self.current_position['lowest_price'], low_price)
            
            # Kiểm tra các mức TP từng phần
            if self.enable_partial_tp:
                # TP1
                if not self.current_position['tp1_triggered'] and high_price >= self.current_position['tp1']:
                    self._partial_take_profit(self.current_position['tp1'], 'TP1', self.tp_percentages[0])
                    self.current_position['tp1_triggered'] = True
                
                # TP2
                if not self.current_position['tp2_triggered'] and self.current_position['tp1_triggered'] and high_price >= self.current_position['tp2']:
                    self._partial_take_profit(self.current_position['tp2'], 'TP2', self.tp_percentages[1] / (1 - self.tp_percentages[0]))
                    self.current_position['tp2_triggered'] = True
                
                # TP3
                if not self.current_position['tp3_triggered'] and self.current_position['tp2_triggered'] and high_price >= self.current_position['tp3']:
                    self._partial_take_profit(self.current_position['tp3'], 'TP3', self.tp_percentages[2] / (1 - self.tp_percentages[0] - self.tp_percentages[1]))
                    self.current_position['tp3_triggered'] = True
        else:  # SHORT
            self.current_position['highest_price'] = max(self.current_position['highest_price'], high_price)
            self.current_position['lowest_price'] = min(self.current_position['lowest_price'], low_price)
            
            # Kiểm tra các mức TP từng phần
            if self.enable_partial_tp:
                # TP1
                if not self.current_position['tp1_triggered'] and low_price <= self.current_position['tp1']:
                    self._partial_take_profit(self.current_position['tp1'], 'TP1', self.tp_percentages[0])
                    self.current_position['tp1_triggered'] = True
                
                # TP2
                if not self.current_position['tp2_triggered'] and self.current_position['tp1_triggered'] and low_price <= self.current_position['tp2']:
                    self._partial_take_profit(self.current_position['tp2'], 'TP2', self.tp_percentages[1] / (1 - self.tp_percentages[0]))
                    self.current_position['tp2_triggered'] = True
                
                # TP3
                if not self.current_position['tp3_triggered'] and self.current_position['tp2_triggered'] and low_price <= self.current_position['tp3']:
                    self._partial_take_profit(self.current_position['tp3'], 'TP3', self.tp_percentages[2] / (1 - self.tp_percentages[0] - self.tp_percentages[1]))
                    self.current_position['tp3_triggered'] = True
        
        # Kiểm tra trailing stop
        if self.enable_trailing_stop and self.current_position['tp3_triggered']:
            self._check_trailing_stop(current_price)
        
        # Kiểm tra SL
        if self._check_stop_loss(low_price, high_price):
            # Vị thế đã được đóng trong _check_stop_loss
            return
        
        # Tính PnL hiện tại
        if self.current_position is not None:
            if self.current_position['type'] == 'LONG':
                unrealized_pnl = (current_price - self.current_position['entry_price']) * self.current_position['remaining_size']
                unrealized_pnl_pct = (current_price - self.current_position['entry_price']) / self.current_position['entry_price'] * 100
            else:  # SHORT
                unrealized_pnl = (self.current_position['entry_price'] - current_price) * self.current_position['remaining_size']
                unrealized_pnl_pct = (self.current_position['entry_price'] - current_price) / self.current_position['entry_price'] * 100
            
            self.current_position['pnl'] = unrealized_pnl
            self.current_position['pnl_pct'] = unrealized_pnl_pct
    
    def _partial_take_profit(self, price, reason, percentage):
        """Thực hiện chốt lời một phần vị thế"""
        if self.current_position is None:
            return
        
        # Tính kích thước phần muốn đóng
        close_size = self.current_position['remaining_size'] * percentage
        
        # Tính PnL cho phần đóng
        if self.current_position['type'] == 'LONG':
            pnl = (price - self.current_position['entry_price']) * close_size
            pnl_pct = (price - self.current_position['entry_price']) / self.current_position['entry_price'] * 100
        else:  # SHORT
            pnl = (self.current_position['entry_price'] - price) * close_size
            pnl_pct = (self.current_position['entry_price'] - price) / self.current_position['entry_price'] * 100
        
        # Cập nhật balance
        self.balance += pnl
        
        # Cập nhật kích thước còn lại
        original_size = self.current_position['remaining_size']
        self.current_position['remaining_size'] -= close_size
        
        # Ghi log
        logger.info(f"Chốt lời {percentage*100:.0f}% vị thế {self.current_position['type']} {self.symbol} tại {price:.2f} "
                   f"với lý do {reason}, PnL={pnl:.2f} ({pnl_pct:.2f}%), Balance={self.balance:.2f}, "
                   f"Còn lại: {self.current_position['remaining_size']/original_size*100:.0f}%")
        
        # Cập nhật thống kê
        self.exit_stats[reason]['count'] += 1
        if pnl > 0:
            self.exit_stats[reason]['win'] += 1
        else:
            self.exit_stats[reason]['loss'] += 1
        self.exit_stats[reason]['total_pnl'] += pnl
        
        # Ghi nhận lệnh chốt lời từng phần vào lịch sử
        partial_trade = {
            'type': self.current_position['type'],
            'entry_price': self.current_position['entry_price'],
            'entry_time': self.current_position['entry_time'],
            'exit_price': price,
            'exit_time': self.data.iloc[min(len(self.data) - 1, self.current_position['entry_index'] + 1)]['timestamp'],
            'size': close_size,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'exit_reason': reason,
            'market_regime': self.current_position['market_regime'],
            'is_partial': True
        }
        
        self.trades_history.append(partial_trade)
    
    def _check_trailing_stop(self, current_price):
        if self.current_position is None or not self.enable_trailing_stop:
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
                self._close_position(current_price, 'TRAILING_STOP', 1.0)
                return True
            elif self.current_position['type'] == 'SHORT' and current_price >= self.current_position['trailing_stop']:
                self._close_position(current_price, 'TRAILING_STOP', 1.0)
                return True
        
        return False
    
    def _check_stop_loss(self, low_price, high_price):
        if self.current_position is None:
            return False
        
        if self.current_position['type'] == 'LONG':
            if low_price <= self.current_position['sl_price']:
                # Kích hoạt SL ở giá SL
                self._close_position(self.current_position['sl_price'], 'SL', 1.0)
                return True
        else:  # SHORT
            if high_price >= self.current_position['sl_price']:
                # Kích hoạt SL ở giá SL
                self._close_position(self.current_position['sl_price'], 'SL', 1.0)
                return True
        
        return False
    
    def _close_position(self, exit_price, reason, percentage=1.0):
        if self.current_position is None:
            return
        
        # Kích thước phần muốn đóng
        close_size = self.current_position['remaining_size'] * percentage
        
        # Tính PnL
        if self.current_position['type'] == 'LONG':
            pnl = (exit_price - self.current_position['entry_price']) * close_size
            pnl_pct = (exit_price - self.current_position['entry_price']) / self.current_position['entry_price'] * 100
        else:  # SHORT
            pnl = (self.current_position['entry_price'] - exit_price) * close_size
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
        self.current_position['remaining_size'] = 0  # Đã đóng hết
        
        # Tính thời gian giao dịch (số candle)
        trade_duration = self.current_position['exit_index'] - self.current_position['entry_index']
        self.trade_durations.append(trade_duration)
        
        # Thêm vào lịch sử
        trade_record = self.current_position.copy()
        trade_record['size'] = close_size  # Ghi nhận kích thước thực tế đóng
        self.trades_history.append(trade_record)
        
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
            
            # Cập nhật thống kê theo thị trường
            market_regime = self.current_position['market_regime']
            market_group = market_regime.split('_')[0] if '_' in market_regime else market_regime
            if market_group in ['BULL', 'OVERBOUGHT']:
                self.market_stats['BULL']['win'] += 1
                self.market_stats['BULL']['total_pnl'] += pnl
            elif market_group in ['BEAR', 'OVERSOLD']:
                self.market_stats['BEAR']['win'] += 1
                self.market_stats['BEAR']['total_pnl'] += pnl
            elif market_group in ['SIDEWAYS', 'RANGING', 'NEUTRAL']:
                self.market_stats['SIDEWAYS']['win'] += 1
                self.market_stats['SIDEWAYS']['total_pnl'] += pnl
            elif market_group in ['VOLATILE', 'CHOPPY']:
                self.market_stats['VOLATILE']['win'] += 1
                self.market_stats['VOLATILE']['total_pnl'] += pnl
        elif pnl < 0:
            self.losing_trades += 1
            self.total_loss -= pnl  # Lưu ý: total_loss lưu giá trị dương
            self.largest_loss = min(self.largest_loss, pnl)
            
            # Cập nhật consecutive losses
            self.current_consecutive_losses += 1
            self.current_consecutive_wins = 0
            self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_consecutive_losses)
            
            # Cập nhật thống kê theo thị trường
            market_regime = self.current_position['market_regime']
            market_group = market_regime.split('_')[0] if '_' in market_regime else market_regime
            if market_group in ['BULL', 'OVERBOUGHT']:
                self.market_stats['BULL']['loss'] += 1
                self.market_stats['BULL']['total_pnl'] += pnl
            elif market_group in ['BEAR', 'OVERSOLD']:
                self.market_stats['BEAR']['loss'] += 1
                self.market_stats['BEAR']['total_pnl'] += pnl
            elif market_group in ['SIDEWAYS', 'RANGING', 'NEUTRAL']:
                self.market_stats['SIDEWAYS']['loss'] += 1
                self.market_stats['SIDEWAYS']['total_pnl'] += pnl
            elif market_group in ['VOLATILE', 'CHOPPY']:
                self.market_stats['VOLATILE']['loss'] += 1
                self.market_stats['VOLATILE']['total_pnl'] += pnl
        else:
            self.breakeven_trades += 1
        
        # Cập nhật thống kê theo reason
        if reason not in self.exit_stats:
            self.exit_stats[reason] = {'count': 0, 'win': 0, 'loss': 0, 'total_pnl': 0}
        
        self.exit_stats[reason]['count'] += 1
        if pnl > 0:
            self.exit_stats[reason]['win'] += 1
        else:
            self.exit_stats[reason]['loss'] += 1
        self.exit_stats[reason]['total_pnl'] += pnl
        
        # Reset current position
        pos = self.current_position
        self.current_position = None
        
        logger.info(f'Đóng vị thế {self.symbol} tại {exit_price:.2f} với lý do {reason}, PnL={pnl:.2f} ({pnl_pct:.2f}%), Balance={self.balance:.2f}')
        
        return pos
    
    def calculate_equity(self, index):
        equity = self.balance
        
        if self.current_position is not None:
            current_price = self.data.iloc[index]['close']
            if self.current_position['type'] == 'LONG':
                equity += (current_price - self.current_position['entry_price']) * self.current_position['remaining_size']
            else:  # SHORT
                equity += (self.current_position['entry_price'] - current_price) * self.current_position['remaining_size']
        
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
        plt.title(f'Equity Curve - {self.symbol} - {self.strategy_name} - Risk {self.risk_level} ({self.risk_percentage*100:.0f}%)')
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
        long_pnl = [trade['pnl'] for trade in self.trades_history if trade['type'] == 'LONG' and not trade.get('is_partial', False)]
        short_pnl = [trade['pnl'] for trade in self.trades_history if trade['type'] == 'SHORT' and not trade.get('is_partial', False)]
        
        # Tiểu đồ thị phân phối tất cả lệnh
        plt.subplot(2, 1, 1)
        all_pnl = [trade['pnl'] for trade in self.trades_history if not trade.get('is_partial', False)]
        plt.hist(all_pnl, bins=20, alpha=0.7, label=f'All Trades (n={len(all_pnl)})')
        plt.axvline(x=0, color='r', linestyle='--')
        plt.grid(True)
        plt.title(f'PnL Distribution - {self.symbol} - {self.strategy_name} - Risk {self.risk_level}')
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

# Tiến hành backtest
print("\n2. TIẾN HÀNH BACKTEST CHO MỨC RỦI RO CONSERVATIVE (5%)")

try:
    # Khởi tạo engine với mức rủi ro Conservative (5%)
    engine = BacktestEngine(data, 'BTCUSDT', initial_balance=10000, leverage=5, risk_percentage=0.05)
    
    # Khởi tạo strategy
    strategy = AdaptiveStrategy(fast_period=10, medium_period=20, slow_period=50)
    
    # Chạy backtest
    result = engine.run(strategy, debug_level=1)
    
    # Lưu kết quả
    result_path = result_dir / 'result_conservative.json'
    with open(result_path, 'w') as f:
        # Chỉ lưu các dữ liệu không phải danh sách lớn
        save_result = {
            k: v for k, v in result.items() 
            if k not in ['equity_curve', 'drawdown_curve', 'trades_history', 'signal_history']
        }
        json.dump(save_result, f, indent=4, default=str)
    
    # Vẽ và lưu biểu đồ
    engine.plot_equity_curve(chart_dir / 'equity_conservative.png')
    engine.plot_trade_distribution(chart_dir / 'distribution_conservative.png')
    
    # Hiển thị kết quả
    print(f"\n3. KẾT QUẢ BACKTEST:")
    print(f"  + Tổng số giao dịch: {result['total_trades']}")
    print(f"  + Win rate: {result['win_rate']*100:.2f}%")
    print(f"  + Lợi nhuận: ${result['profit_loss']:.2f} ({result['profit_loss_pct']:.2f}%)")
    print(f"  + Drawdown tối đa: {result['max_drawdown_pct']:.2f}%")
    print(f"  + Profit factor: {result['profit_factor']:.2f}")
    print(f"  + Consecutive losses: {result['max_consecutive_losses']}")
    
    # Hiển thị các lệnh lãi/lỗ lớn nhất
    print(f"  + Lệnh lãi lớn nhất: ${result['largest_win']:.2f}")
    print(f"  + Lệnh lỗ lớn nhất: ${result['largest_loss']:.2f}")
    
    # Phân tích lệnh lãi/lỗ
    print("\n4. PHÂN TÍCH CÁC LỆNH GIAO DỊCH")
    
    # Phân loại
    winning_trades = [t for t in engine.trades_history if t['pnl'] > 0 and not t.get('is_partial', False)]
    losing_trades = [t for t in engine.trades_history if t['pnl'] < 0 and not t.get('is_partial', False)]
    partial_trades = [t for t in engine.trades_history if t.get('is_partial', False)]
    
    # Sắp xếp theo PnL
    top_winners = sorted(winning_trades, key=lambda x: x['pnl'], reverse=True)[:5]
    top_losers = sorted(losing_trades, key=lambda x: x['pnl'])[:5]
    
    # Hiển thị top winners
    print(f"\n- Top 5 lệnh lãi lớn nhất:")
    for i, trade in enumerate(top_winners):
        print(f"  {i+1}. {trade['type']} vào ngày {trade['entry_time']}, ra ngày {trade['exit_time']}")
        print(f"     Vào giá: ${trade['entry_price']:.2f}, ra giá: ${trade['exit_price']:.2f}")
        print(f"     PnL: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%), Lý do thoát: {trade['exit_reason']}")
        print(f"     Chế độ thị trường: {trade['market_regime']}")
    
    # Hiển thị top losers
    print(f"\n- Top 5 lệnh lỗ lớn nhất:")
    for i, trade in enumerate(top_losers):
        print(f"  {i+1}. {trade['type']} vào ngày {trade['entry_time']}, ra ngày {trade['exit_time']}")
        print(f"     Vào giá: ${trade['entry_price']:.2f}, ra giá: ${trade['exit_price']:.2f}")
        print(f"     PnL: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%), Lý do thoát: {trade['exit_reason']}")
        print(f"     Chế độ thị trường: {trade['market_regime']}")
    
    # Phân tích theo loại exit
    print("\n- Phân tích theo lý do thoát lệnh:")
    exit_reasons = engine.exit_stats
    
    for reason, stats in exit_reasons.items():
        if stats['count'] > 0:
            win_rate = stats['win'] / stats['count'] * 100
            avg_pnl = stats['total_pnl'] / stats['count']
            print(f"  + {reason}: {stats['count']} lệnh, Win rate: {win_rate:.2f}%, PnL trung bình: ${avg_pnl:.2f}")
    
    # Phân tích theo thị trường
    print("\n- Phân tích theo loại thị trường:")
    market_stats = engine.market_stats
    
    for market, stats in market_stats.items():
        total_trades = stats['win'] + stats['loss']
        if total_trades > 0:
            win_rate = stats['win'] / total_trades * 100
            avg_pnl = stats['total_pnl'] / total_trades
            print(f"  + {market}: {total_trades} lệnh, Win rate: {win_rate:.2f}%, PnL trung bình: ${avg_pnl:.2f}")
    
    # Phân tích Partial TP vs SL
    print(f"\n- Phân tích Partial TP vs SL:")
    total_tp_pnl = 0
    total_tp_count = 0
    for key in ['TP1', 'TP2', 'TP3', 'TRAILING_STOP']:
        if key in result['exit_stats']:
            total_tp_pnl += result['exit_stats'][key]['total_pnl']
            total_tp_count += result['exit_stats'][key]['count']
    
    sl_pnl = result['exit_stats']['SL']['total_pnl'] if 'SL' in result['exit_stats'] else 0
    sl_count = result['exit_stats']['SL']['count'] if 'SL' in result['exit_stats'] else 0
    
    if total_tp_count > 0 and sl_count > 0:
        print(f"  + Partial TP: {total_tp_count} lần chốt lời, tổng lãi ${total_tp_pnl:.2f}, trung bình ${total_tp_pnl/total_tp_count:.2f}/lần")
        print(f"  + SL: {sl_count} lần dừng lỗ, tổng lỗ ${abs(sl_pnl):.2f}, trung bình ${abs(sl_pnl)/sl_count:.2f}/lần")
        print(f"  + Tỷ lệ bù đắp: Partial TP đã bù đắp {(total_tp_pnl/abs(sl_pnl))*100:.2f}% tổng lỗ từ SL")
    
    print("\n=== HOÀN THÀNH BACKTEST ===")
    
except Exception as e:
    print(f"Lỗi khi chạy backtest: {str(e)}")
    logger.error(f"Lỗi khi chạy backtest: {str(e)}")