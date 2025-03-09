#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kiểm thử nhanh tích hợp sideway optimization và trailing stop
Kiểm tra sự ổn định của hệ thống trong các tình huống thị trường khác nhau
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import time
import random
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/quick_test.log')
    ]
)

logger = logging.getLogger('quick_test')

# Đảm bảo các thư mục cần thiết tồn tại
os.makedirs('logs', exist_ok=True)
os.makedirs('quick_test_results', exist_ok=True)

class MockSidewaysMarketOptimizer:
    """
    Giả lập SidewaysMarketOptimizer cho mục đích kiểm thử
    """
    
    def __init__(self):
        self.sideways_score = 0.0
        self.is_sideways = False
    
    def detect_sideways_market(self, df):
        """Phát hiện thị trường sideway"""
        # Tính toán chỉ số để phát hiện thị trường sideway
        # Ở đây chỉ tính toán đơn giản dựa trên biến động giá
        
        # Tính Bollinger Bands width
        window = 20
        if len(df) < window:
            self.sideways_score = 0.0
            self.is_sideways = False
            return False
            
        df['sma'] = df['close'].rolling(window=window).mean()
        df['std'] = df['close'].rolling(window=window).std()
        df['upper_band'] = df['sma'] + 2 * df['std']
        df['lower_band'] = df['sma'] - 2 * df['std']
        df['bb_width'] = (df['upper_band'] - df['lower_band']) / df['sma']
        
        # Tính ATR và so sánh với giá trung bình
        def tr(row):
            return max(
                row['high'] - row['low'],
                abs(row['high'] - row['close_prev']),
                abs(row['low'] - row['close_prev'])
            )
            
        df['close_prev'] = df['close'].shift(1)
        df['tr'] = df.apply(tr, axis=1)
        df['atr'] = df['tr'].rolling(window=window).mean()
        df['atr_ratio'] = df['atr'] / df['close']
        
        # Tính slope của SMA để phát hiện xu hướng
        df['sma_prev'] = df['sma'].shift(window)
        df['sma_slope'] = (df['sma'] - df['sma_prev']) / (window * df['sma_prev'])
        
        # Lấy giá trị gần đây để tính toán
        recent_bb_width = df['bb_width'].dropna().iloc[-5:].mean()
        recent_atr_ratio = df['atr_ratio'].dropna().iloc[-5:].mean()
        recent_sma_slope = abs(df['sma_slope'].dropna().iloc[-5:].mean())
        
        # Tính điểm sideway dựa trên 3 chỉ số
        bb_score = 1 - min(recent_bb_width / 0.03, 1)  # Thấp hơn 3% được coi là tốt
        atr_score = 1 - min(recent_atr_ratio / 0.01, 1)  # Thấp hơn 1% được coi là tốt
        slope_score = 1 - min(recent_sma_slope / 0.001, 1)  # Thấp hơn 0.1% mỗi kỳ là tốt
        
        self.sideways_score = (bb_score * 0.4) + (atr_score * 0.4) + (slope_score * 0.2)
        self.is_sideways = self.sideways_score > 0.7
        
        return self.is_sideways
    
    def adjust_strategy_for_sideways(self, original_position_size=1.0):
        """Điều chỉnh chiến lược cho thị trường sideway"""
        if not hasattr(self, 'is_sideways'):
            return {
                'position_size': original_position_size,
                'use_mean_reversion': False
            }
        
        if self.is_sideways:
            # Nếu là thị trường sideway, giảm kích thước lệnh và sử dụng mean reversion
            position_size = original_position_size * (0.5 + 0.1 * (1 - self.sideways_score))
            return {
                'position_size': position_size,
                'use_mean_reversion': True
            }
        else:
            return {
                'position_size': original_position_size,
                'use_mean_reversion': False
            }
    
    def optimize_takeprofit_stoploss(self, df):
        """Tối ưu hóa take profit và stop loss cho thị trường hiện tại"""
        if not hasattr(self, 'is_sideways'):
            return {
                'tp_adjustment': 1.0,
                'sl_adjustment': 1.0
            }
        
        if self.is_sideways:
            # Trong thị trường sideway:
            # - Mục tiêu take profit gần hơn
            # - Stop loss rộng hơn để tránh bị stopped out bởi noise
            tp_adjustment = 0.7  # Giảm 30% take profit
            sl_adjustment = 1.5  # Tăng 50% stop loss
        else:
            # Trong thị trường có xu hướng, sử dụng cài đặt bình thường
            tp_adjustment = 1.0
            sl_adjustment = 1.0
        
        return {
            'tp_adjustment': tp_adjustment,
            'sl_adjustment': sl_adjustment
        }
    
    def generate_mean_reversion_signals(self, df):
        """Tạo tín hiệu mean reversion cho thị trường sideway"""
        # Tính các chỉ báo cho mean reversion
        window = 20
        
        # Tính Bollinger Bands
        df['sma'] = df['close'].rolling(window=window).mean()
        df['std'] = df['close'].rolling(window=window).std()
        df['upper_band'] = df['sma'] + 2 * df['std']
        df['lower_band'] = df['sma'] - 2 * df['std']
        
        # Tính %B (phần trăm giá trong Bollinger Bands)
        df['percent_b'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
        
        # Tính RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Tạo tín hiệu mua/bán
        df['buy_signal'] = (df['percent_b'] < 0.2) & (df['rsi'] < 30)  # Mua khi giá thấp và quá bán
        df['sell_signal'] = (df['percent_b'] > 0.8) & (df['rsi'] > 70)  # Bán khi giá cao và quá mua
        
        return df
    
    def predict_breakout_direction(self, df):
        """Dự đoán hướng breakout từ thị trường sideway"""
        # Đánh giá chiều hướng volume và chênh lệch giá
        
        # Tính trung bình volume
        avg_volume = df['volume'].iloc[-20:].mean()
        recent_volume = df['volume'].iloc[-5:].mean()
        
        # Tính chênh lệch giá đóng cửa so với SMA
        if 'sma' not in df.columns:
            df['sma'] = df['close'].rolling(window=20).mean()
        
        price_distance = (df['close'].iloc[-1] - df['sma'].iloc[-1]) / df['sma'].iloc[-1]
        
        # Dựa trên volume và chênh lệch giá
        if recent_volume > avg_volume * 1.2:  # Volume tăng 20%
            if price_distance > 0.005:
                return "upward"
            elif price_distance < -0.005:
                return "downward"
        
        return "uncertain"
    
    def visualize_sideways_detection(self, df, symbol, custom_path=None):
        """Tạo biểu đồ phân tích thị trường sideway"""
        # Tạo mẫu visualize đơn giản
        
        # Đảm bảo các chỉ báo được tính toán
        if 'sma' not in df.columns:
            df['sma'] = df['close'].rolling(window=20).mean()
        if 'upper_band' not in df.columns:
            df['std'] = df['close'].rolling(window=20).std()
            df['upper_band'] = df['sma'] + 2 * df['std']
            df['lower_band'] = df['sma'] - 2 * df['std']
        
        # Tạo biểu đồ
        plt.figure(figsize=(12, 8))
        
        # Vẽ giá và các band
        plt.subplot(2, 1, 1)
        plt.plot(df.index[-50:], df['close'].iloc[-50:], label='Giá đóng cửa')
        plt.plot(df.index[-50:], df['sma'].iloc[-50:], label='SMA20', linestyle='--')
        plt.plot(df.index[-50:], df['upper_band'].iloc[-50:], label='Upper BB', linestyle=':')
        plt.plot(df.index[-50:], df['lower_band'].iloc[-50:], label='Lower BB', linestyle=':')
        plt.title(f'Phân tích thị trường {symbol} - Sideways Score: {self.sideways_score:.2f}')
        plt.legend()
        
        # Vẽ volume
        plt.subplot(2, 1, 2)
        plt.bar(df.index[-50:], df['volume'].iloc[-50:], alpha=0.5)
        plt.title('Volume')
        
        # Lưu biểu đồ
        if custom_path:
            os.makedirs(custom_path, exist_ok=True)
            filename = f"{custom_path}/{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        else:
            os.makedirs('charts', exist_ok=True)
            filename = f"charts/{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        
        return filename


class MockTrailingStopManager:
    """
    Giả lập EnhancedTrailingStopManager cho mục đích kiểm thử
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        self.active_stops = {}
        self.last_prices = {}
        self.price_history = {}
        self.market_regimes = {}
        
        # Cài đặt trailing stop
        self.default_activation_percent = 1.0  # Kích hoạt trailing stop khi đạt 1% lợi nhuận
        self.default_trailing_percent = 0.5    # Trailing stop theo sau 0.5% từ giá cao nhất
        self.min_profit_protection = 0.3       # Bảo vệ ít nhất 0.3% lợi nhuận khi đã trailing
        
        # Theo dõi hiệu suất
        self.performance_stats = {
            'successful_trails': 0,
            'profit_saved': 0.0
        }
    
    def register_position(self, symbol, order_id, entry_price, position_size, direction='long', 
                         stop_loss_price=None, take_profit_price=None):
        """Đăng ký vị thế để theo dõi trailing stop"""
        # Tạo ID theo dõi duy nhất
        tracking_id = f"{symbol}_{order_id}_{int(time.time())}"
        
        # Tính stop loss mặc định nếu không được cung cấp
        if stop_loss_price is None:
            if direction == 'long':
                stop_loss_price = entry_price * 0.95  # -5% cho long
            else:
                stop_loss_price = entry_price * 1.05  # +5% cho short
        
        # Lưu thông tin vị thế
        self.active_stops[tracking_id] = {
            'symbol': symbol,
            'order_id': order_id,
            'entry_price': entry_price,
            'position_size': position_size,
            'direction': direction,
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'current_price': entry_price,
            'highest_price': entry_price if direction == 'long' else float('inf'),
            'lowest_price': entry_price if direction == 'short' else 0,
            'trailing_active': False,
            'trailing_stop_price': stop_loss_price,
            'start_time': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat()
        }
        
        # Cập nhật giá ban đầu
        self.last_prices[symbol] = entry_price
        
        logger.info(f"Đã đăng ký vị thế {tracking_id} - {direction} {symbol} tại {entry_price}")
        return tracking_id
    
    def update_price(self, symbol, current_price, timestamp=None):
        """Cập nhật giá và xử lý trailing stop"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Cập nhật giá mới nhất
        self.last_prices[symbol] = current_price
        
        # Lưu vào lịch sử giá
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            
        self.price_history[symbol].append({
            'price': current_price,
            'timestamp': timestamp.isoformat()
        })
        
        # Giới hạn kích thước lịch sử giá
        max_history = 1000
        if len(self.price_history[symbol]) > max_history:
            self.price_history[symbol] = self.price_history[symbol][-max_history:]
        
        # Kiểm tra và cập nhật trạng thái trailing stop cho từng vị thế
        positions_to_close = []
        
        for tracking_id, stop_data in list(self.active_stops.items()):
            if stop_data['symbol'] == symbol:
                # Cập nhật giá hiện tại
                stop_data['current_price'] = current_price
                stop_data['last_update'] = timestamp.isoformat()
                
                # Kiểm tra và cập nhật trailing stop
                triggered, action_type = self._process_trailing_stop(tracking_id, current_price, timestamp)
                if triggered:
                    positions_to_close.append((tracking_id, action_type))
        
        # Đóng các vị thế đã kích hoạt
        for tracking_id, action_type in positions_to_close:
            self._execute_stop(tracking_id, action_type)
    
    def _process_trailing_stop(self, tracking_id, current_price, timestamp):
        """
        Xử lý trailing stop cho một vị thế
        
        Returns:
            tuple: (triggered, action_type)
            - triggered: True nếu stop được kích hoạt
            - action_type: 'stop_loss', 'take_profit', hoặc 'trailing_stop'
        """
        stop_data = self.active_stops[tracking_id]
        direction = stop_data['direction']
        entry_price = stop_data['entry_price']
        
        # Cập nhật giá cao nhất/thấp nhất
        if direction == 'long' and current_price > stop_data['highest_price']:
            stop_data['highest_price'] = current_price
        elif direction == 'short' and current_price < stop_data['lowest_price']:
            stop_data['lowest_price'] = current_price
        
        # Tính lợi nhuận hiện tại (%)
        if direction == 'long':
            current_profit_pct = (current_price - entry_price) / entry_price * 100
            highest_profit_pct = (stop_data['highest_price'] - entry_price) / entry_price * 100
        else:
            current_profit_pct = (entry_price - current_price) / entry_price * 100
            highest_profit_pct = (entry_price - stop_data['lowest_price']) / entry_price * 100
        
        # Kiểm tra take profit
        if stop_data['take_profit_price'] is not None:
            if (direction == 'long' and current_price >= stop_data['take_profit_price']) or \
               (direction == 'short' and current_price <= stop_data['take_profit_price']):
                return True, 'take_profit'
        
        # Kiểm tra stop loss
        if (direction == 'long' and current_price <= stop_data['stop_loss_price']) or \
           (direction == 'short' and current_price >= stop_data['stop_loss_price']):
            return True, 'stop_loss'
        
        # Kiểm tra kích hoạt trailing stop
        if not stop_data['trailing_active']:
            if current_profit_pct >= self.default_activation_percent:
                stop_data['trailing_active'] = True
                
                # Thiết lập giá trailing stop ban đầu
                if direction == 'long':
                    new_stop = current_price * (1 - self.default_trailing_percent / 100)
                    if new_stop > stop_data['stop_loss_price']:
                        stop_data['trailing_stop_price'] = new_stop
                else:
                    new_stop = current_price * (1 + self.default_trailing_percent / 100)
                    if new_stop < stop_data['stop_loss_price']:
                        stop_data['trailing_stop_price'] = new_stop
                
                logger.info(f"Đã kích hoạt trailing stop cho {tracking_id} tại {stop_data['trailing_stop_price']:.2f}")
        
        # Cập nhật trailing stop nếu đã kích hoạt
        elif stop_data['trailing_active']:
            if direction == 'long':
                # Tính toán trailing stop mới
                new_stop = stop_data['highest_price'] * (1 - self.default_trailing_percent / 100)
                
                # Đảm bảo luôn bảo vệ lợi nhuận tối thiểu
                min_stop = entry_price * (1 + self.min_profit_protection / 100)
                new_stop = max(new_stop, min_stop)
                
                # Chỉ cập nhật nếu stop mới cao hơn stop hiện tại
                if new_stop > stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop
                    logger.debug(f"Đã cập nhật trailing stop cho {tracking_id} lên {new_stop:.2f}")
                
                # Kiểm tra kích hoạt trailing stop
                if current_price <= stop_data['trailing_stop_price']:
                    # Tính lợi nhuận được bảo toàn
                    saved_profit = highest_profit_pct - current_profit_pct
                    self.performance_stats['profit_saved'] += saved_profit
                    self.performance_stats['successful_trails'] += 1
                    
                    logger.info(f"Kích hoạt trailing stop: {tracking_id} - Bảo toàn {saved_profit:.2f}% lợi nhuận")
                    return True, 'trailing_stop'
            else:
                # Short position
                new_stop = stop_data['lowest_price'] * (1 + self.default_trailing_percent / 100)
                
                # Đảm bảo luôn bảo vệ lợi nhuận tối thiểu
                min_stop = entry_price * (1 - self.min_profit_protection / 100)
                new_stop = min(new_stop, min_stop)
                
                # Chỉ cập nhật nếu stop mới thấp hơn stop hiện tại
                if new_stop < stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop
                    logger.debug(f"Đã cập nhật trailing stop cho {tracking_id} xuống {new_stop:.2f}")
                
                # Kiểm tra kích hoạt trailing stop
                if current_price >= stop_data['trailing_stop_price']:
                    # Tính lợi nhuận được bảo toàn
                    saved_profit = highest_profit_pct - current_profit_pct
                    self.performance_stats['profit_saved'] += saved_profit
                    self.performance_stats['successful_trails'] += 1
                    
                    logger.info(f"Kích hoạt trailing stop: {tracking_id} - Bảo toàn {saved_profit:.2f}% lợi nhuận")
                    return True, 'trailing_stop'
        
        return False, None
    
    def _execute_stop(self, tracking_id, action_type):
        """Thực hiện đóng vị thế"""
        if tracking_id not in self.active_stops:
            return
        
        stop_data = self.active_stops[tracking_id]
        current_price = stop_data['current_price']
        entry_price = stop_data['entry_price']
        direction = stop_data['direction']
        
        # Tính lợi nhuận
        if direction == 'long':
            profit_pct = (current_price - entry_price) / entry_price * 100
        else:
            profit_pct = (entry_price - current_price) / entry_price * 100
        
        # Ghi log
        logger.info(f"Đóng vị thế {tracking_id} qua {action_type}: {profit_pct:.2f}% lợi nhuận")
        
        # Thực hiện đóng vị thế thông qua API nếu có
        if self.api_client:
            try:
                # Giả định: hàm close_position của api_client
                # self.api_client.close_position(symbol=stop_data['symbol'], ...)
                pass
            except Exception as e:
                logger.error(f"Không thể đóng vị thế {tracking_id} qua API: {str(e)}")
        
        # Đánh dấu thời gian đóng
        stop_data['close_time'] = datetime.now().isoformat()
        stop_data['close_price'] = current_price
        stop_data['close_action'] = action_type
        stop_data['profit_percent'] = profit_pct
        
        # Xóa khỏi active_stops
        self.active_stops.pop(tracking_id)
    
    def manual_close_position(self, tracking_id, reason="manual"):
        """Đóng vị thế thủ công"""
        if tracking_id not in self.active_stops:
            logger.warning(f"Không tìm thấy vị thế {tracking_id} để đóng thủ công")
            return False
        
        stop_data = self.active_stops[tracking_id]
        
        # Lưu lý do đóng
        stop_data['close_reason'] = reason
        
        # Thực hiện đóng
        self._execute_stop(tracking_id, f"manual_{reason}")
        return True
    
    def get_position_info(self, tracking_id):
        """Lấy thông tin vị thế"""
        return self.active_stops.get(tracking_id)
    
    def get_active_positions(self):
        """Lấy danh sách vị thế đang hoạt động"""
        return list(self.active_stops.keys())
    
    def get_performance_stats(self):
        """Lấy thống kê hiệu suất"""
        return self.performance_stats


def generate_market_data(scenario="normal", n_samples=500):
    """
    Tạo dữ liệu thị trường mô phỏng cho các kịch bản khác nhau
    
    Args:
        scenario (str): Loại kịch bản thị trường
            'normal': Thị trường thông thường
            'flash_crash': Sụp đổ nhanh chóng
            'price_spike': Tăng giá mạnh đột ngột
            'sideways': Thị trường sideway
            'high_volatility': Biến động cao
        n_samples (int): Số lượng mẫu dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLC
    """
    # Tạo dữ liệu cơ sở
    dates = pd.date_range(start='2023-01-01', periods=n_samples, freq='1H')
    
    if scenario == "flash_crash":
        # Mô phỏng sụp đổ nhanh chóng (-20% trong vài giờ)
        base_price = 50000
        prices = np.ones(n_samples) * base_price
        
        # Thời điểm sụp đổ
        crash_start = int(n_samples * 0.7)
        crash_duration = 5
        
        for i in range(crash_duration):
            crash_idx = crash_start + i
            prices[crash_idx:] = prices[crash_idx-1] * 0.92  # Giảm 8% mỗi giờ
        
    elif scenario == "price_spike":
        # Mô phỏng đợt tăng giá đột ngột (+30% trong vài giờ)
        base_price = 50000
        prices = np.ones(n_samples) * base_price
        
        # Thời điểm tăng giá
        spike_start = int(n_samples * 0.6)
        spike_duration = 3
        
        for i in range(spike_duration):
            spike_idx = spike_start + i
            prices[spike_idx:] = prices[spike_idx-1] * 1.1  # Tăng 10% mỗi giờ
        
    elif scenario == "sideways":
        # Thị trường sideway (biến động < 1%)
        base_price = 50000
        volatility = 0.002  # 0.2%
        
        # Tạo dao động nhỏ quanh giá trung bình
        random_moves = np.random.normal(0, volatility, n_samples)
        prices = base_price * (1 + np.cumsum(random_moves))
        
        # Giới hạn biến động trong khoảng hẹp
        prices = np.clip(prices, base_price * 0.98, base_price * 1.02)
        
    elif scenario == "high_volatility":
        # Biến động cao, dao động mạnh trong cả hai chiều
        base_price = 50000
        volatility = 0.025  # 2.5%
        
        # Tạo chuyển động ngẫu nhiên với biến động cao
        random_moves = np.random.normal(0, volatility, n_samples)
        prices = base_price * (1 + np.cumsum(random_moves))
        
        # Thêm các đỉnh và đáy cực đoan
        for i in range(5):
            spike_idx = random.randint(20, n_samples-20)
            spike_direction = random.choice([-1, 1])
            spike_size = random.uniform(0.05, 0.15)  # 5% đến 15%
            
            prices[spike_idx] = prices[spike_idx-1] * (1 + spike_direction * spike_size)
            # Điều chỉnh các giá sau spike
            adjustment = np.linspace(spike_direction * spike_size, 0, 10)
            for j in range(1, 10):
                if spike_idx + j < n_samples:
                    prices[spike_idx + j] = prices[spike_idx-1] * (1 + adjustment[j])
    
    else:  # normal
        # Thị trường thông thường với xu hướng nhẹ
        base_price = 50000
        trend = np.linspace(0, 0.1, n_samples)  # Xu hướng tăng 10%
        noise = np.random.normal(0, 0.01, n_samples)  # Nhiễu 1%
        prices = base_price * (1 + trend + noise)
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'open': prices * 0.998,
        'high': prices * 1.004,
        'low': prices * 0.996,
        'close': prices,
        'volume': np.random.randint(100, 10000, n_samples)
    }, index=dates)
    
    # Điều chỉnh high/low để hợp lý
    for i in range(1, len(df)):
        df.loc[df.index[i], 'open'] = df.loc[df.index[i-1], 'close']
        df.loc[df.index[i], 'high'] = max(df.loc[df.index[i], 'open'], df.loc[df.index[i], 'close']) * (1 + random.uniform(0.001, 0.006))
        df.loc[df.index[i], 'low'] = min(df.loc[df.index[i], 'open'], df.loc[df.index[i], 'close']) * (1 - random.uniform(0.001, 0.006))
    
    # Điều chỉnh volume dựa trên biến động giá
    price_changes = np.abs(df['close'].pct_change().fillna(0))
    volume_factor = 1 + price_changes * 10
    df['volume'] = (df['volume'] * volume_factor).astype(int)
    
    return df


def run_quick_test():
    """
    Chạy kiểm thử nhanh cho các module giả lập
    """
    print("\n===== KIỂM TRA NHANH MODULE TÍCH HỢP =====")
    
    # Khởi tạo các module
    sideways_optimizer = MockSidewaysMarketOptimizer()
    trailing_manager = MockTrailingStopManager()
    
    # Thiết lập kịch bản kiểm thử
    scenarios = ["normal", "flash_crash", "price_spike", "sideways", "high_volatility"]
    
    # Kết quả tổng hợp
    results = {}
    
    for scenario in scenarios:
        print(f"\n----- Kiểm tra kịch bản: {scenario} -----")
        
        # Tạo dữ liệu thị trường
        market_data = generate_market_data(scenario)
        
        # Phát hiện thị trường sideway
        is_sideway = sideways_optimizer.detect_sideways_market(market_data)
        
        print(f"Phát hiện thị trường: {'SIDEWAY' if is_sideway else 'TRENDING'}")
        print(f"Sideways score: {sideways_optimizer.sideways_score:.2f}")
        
        # Lấy các điều chỉnh chiến lược
        strategy_adjustments = sideways_optimizer.adjust_strategy_for_sideways()
        tp_sl_adjustments = sideways_optimizer.optimize_takeprofit_stoploss(market_data)
        
        print(f"Kích thước vị thế: {strategy_adjustments['position_size']}")
        print(f"Sử dụng mean reversion: {strategy_adjustments['use_mean_reversion']}")
        print(f"Điều chỉnh TP: {tp_sl_adjustments['tp_adjustment']:.2f}x")
        print(f"Điều chỉnh SL: {tp_sl_adjustments['sl_adjustment']:.2f}x")
        
        # Tạo biểu đồ phân tích
        chart_path = sideways_optimizer.visualize_sideways_detection(
            market_data, f"TEST_{scenario}", custom_path='quick_test_results'
        )
        print(f"Đã tạo biểu đồ phân tích: {chart_path}")
        
        # Mô phỏng giao dịch
        print("\nMô phỏng giao dịch...")
        
        # Đặt lệnh và trailing stop
        entry_price = market_data['close'].iloc[-100]
        
        # Tính toán stop loss và take profit
        sl_percent = 0.05 * tp_sl_adjustments['sl_adjustment']
        tp_percent = 0.15 * tp_sl_adjustments['tp_adjustment']
        
        stop_loss = entry_price * (1 - sl_percent)
        take_profit = entry_price * (1 + tp_percent)
        
        # Đăng ký vị thế
        order_id = f"test_{scenario}_{int(time.time())}"
        position_size = strategy_adjustments['position_size']
        
        tracking_id = trailing_manager.register_position(
            symbol=f"TEST_{scenario}",
            order_id=order_id,
            entry_price=entry_price,
            position_size=position_size,
            direction="long",
            stop_loss_price=stop_loss,
            take_profit_price=take_profit
        )
        
        print(f"Đã mở vị thế: {tracking_id}")
        print(f"Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
        
        # Mô phỏng cập nhật giá trong tương lai
        future_prices = market_data['close'].iloc[-100:].values
        
        print("\nCập nhật giá...")
        position_closed = False
        
        for i, price in enumerate(future_prices):
            # Cập nhật giá
            trailing_manager.update_price(f"TEST_{scenario}", price)
            
            # Kiểm tra nếu vị thế đã đóng
            if tracking_id not in trailing_manager.get_active_positions():
                position_closed = True
                position_info = None
                for p in list(trailing_manager.active_stops.values()) + [p for p in trailing_manager.active_stops.values()]:
                    if p.get('order_id') == order_id:
                        position_info = p
                        break
                
                if position_info:
                    print(f"Vị thế đã đóng sau {i+1} update:")
                    print(f"Giá đóng: {position_info.get('close_price', 'N/A')}")
                    print(f"Hành động: {position_info.get('close_action', 'N/A')}")
                    print(f"Lợi nhuận: {position_info.get('profit_percent', 'N/A'):.2f}%")
                else:
                    print(f"Vị thế đã đóng sau {i+1} update")
                
                break
        
        if not position_closed:
            position_info = trailing_manager.get_position_info(tracking_id)
            if position_info:
                current_price = position_info['current_price']
                entry_price = position_info['entry_price']
                profit_pct = (current_price - entry_price) / entry_price * 100
                
                print(f"Vị thế vẫn mở sau tất cả updates:")
                print(f"Giá hiện tại: {current_price:.2f}")
                print(f"Trailing active: {position_info['trailing_active']}")
                if position_info['trailing_active']:
                    print(f"Trailing stop price: {position_info['trailing_stop_price']:.2f}")
                print(f"Lợi nhuận hiện tại: {profit_pct:.2f}%")
        
        # Lưu kết quả
        results[scenario] = {
            'is_sideway': is_sideway,
            'sideways_score': sideways_optimizer.sideways_score,
            'position_size': strategy_adjustments['position_size'],
            'use_mean_reversion': strategy_adjustments['use_mean_reversion'],
            'tp_adjustment': tp_sl_adjustments['tp_adjustment'],
            'sl_adjustment': tp_sl_adjustments['sl_adjustment'],
            'position_closed': position_closed,
            'chart_path': chart_path
        }
        
        if position_closed and position_info:
            results[scenario]['close_action'] = position_info.get('close_action', 'unknown')
            results[scenario]['profit_percent'] = position_info.get('profit_percent', 0)
    
    # Tổng kết
    print("\n===== TỔNG KẾT KIỂM TRA NHANH =====")
    
    for scenario, result in results.items():
        print(f"\n{scenario}:")
        print(f"  - Phát hiện sideway: {'Có' if result['is_sideway'] else 'Không'} (Score: {result['sideways_score']:.2f})")
        print(f"  - Điều chỉnh chiến lược: Vị thế x{result['position_size']:.2f}, Mean reversion: {'Có' if result['use_mean_reversion'] else 'Không'}")
        print(f"  - Điều chỉnh TP/SL: TP x{result['tp_adjustment']:.2f}, SL x{result['sl_adjustment']:.2f}")
        
        if result['position_closed']:
            print(f"  - Kết quả giao dịch: Đóng qua {result.get('close_action', 'unknown')}, Lợi nhuận: {result.get('profit_percent', 0):.2f}%")
        else:
            print(f"  - Kết quả giao dịch: Vị thế vẫn mở")
    
    # Lưu kết quả vào file
    result_file = 'quick_test_results/summary.json'
    with open(result_file, 'w') as f:
        json.dump(results, f, indent=4)
    
    print(f"\nĐã lưu kết quả chi tiết vào {result_file}")
    print("\nHoàn thành kiểm tra nhanh!")

if __name__ == "__main__":
    # Chạy kiểm thử nhanh
    run_quick_test()