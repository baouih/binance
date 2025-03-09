#!/usr/bin/env python3
"""
Demo đơn giản về bot giao dịch với vốn nhỏ (100 USD) và đòn bẩy cao (x10-x20)

Script này sẽ mô phỏng các giao dịch với một chuỗi giá mẫu để minh họa
cách bot hoạt động với tài khoản vốn nhỏ.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("micro_bot_demo")

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("demo_results", exist_ok=True)

class MicroTradingDemo:
    """Demo về giao dịch với vốn nhỏ và đòn bẩy cao"""
    
    def __init__(self, initial_balance=100.0, max_leverage=20, risk_percent=2.0):
        """
        Khởi tạo demo
        
        Args:
            initial_balance (float): Số dư ban đầu (USD)
            max_leverage (int): Đòn bẩy tối đa
            risk_percent (float): Rủi ro trên mỗi giao dịch (%)
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.max_leverage = max_leverage
        self.risk_percent = risk_percent
        
        # Lịch sử số dư
        self.balance_history = []
        
        # Lịch sử giao dịch
        self.trades = []
        
        logger.info(f"Khởi tạo Demo: Balance=${initial_balance}, MaxLeverage=x{max_leverage}, Risk={risk_percent}%")
    
    def create_price_series(self, days=30, price_points_per_day=24) -> pd.DataFrame:
        """
        Tạo chuỗi giá mẫu
        
        Args:
            days (int): Số ngày dữ liệu
            price_points_per_day (int): Số điểm giá mỗi ngày
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu giá mẫu
        """
        total_points = days * price_points_per_day
        
        # Thời gian bắt đầu
        start_time = datetime.now() - timedelta(days=days)
        
        # Tạo dữ liệu thời gian
        time_interval = timedelta(days=days) / total_points
        timestamps = [start_time + i * time_interval for i in range(total_points)]
        
        # Tạo giá mẫu với các xu hướng và biến động khác nhau
        initial_price = 35000.0
        prices = [initial_price]
        
        # Các giai đoạn thị trường
        # 1. Giai đoạn đi ngang (30%)
        # 2. Giai đoạn tăng (30%)
        # 3. Giai đoạn biến động cao (20%)
        # 4. Giai đoạn giảm (20%)
        
        segment_sizes = [
            int(total_points * 0.3),  # Đi ngang
            int(total_points * 0.3),  # Tăng
            int(total_points * 0.2),  # Biến động cao
            int(total_points * 0.2)   # Giảm
        ]
        
        # Đảm bảo tổng đúng bằng total_points
        extra_points = total_points - sum(segment_sizes)
        segment_sizes[0] += extra_points
        
        # Volatility và trend cho từng giai đoạn
        segment_params = [
            {'volatility': 0.002, 'trend': 0.0001},  # Đi ngang
            {'volatility': 0.003, 'trend': 0.0025},  # Tăng
            {'volatility': 0.008, 'trend': 0.0000},  # Biến động cao
            {'volatility': 0.004, 'trend': -0.0020}  # Giảm
        ]
        
        # Tạo giá cho từng giai đoạn
        current_price = initial_price
        all_prices = []
        
        for i, segment_size in enumerate(segment_sizes):
            volatility = segment_params[i]['volatility']
            trend = segment_params[i]['trend']
            
            segment_prices = [current_price]
            for j in range(1, segment_size):
                # Tạo giá với xu hướng và biến động ngẫu nhiên
                rnd = np.random.randn()
                change = trend + volatility * rnd
                price = segment_prices[-1] * (1 + change)
                segment_prices.append(price)
            
            all_prices.extend(segment_prices)
            current_price = segment_prices[-1]
        
        # Tạo dữ liệu OHLCV
        df = pd.DataFrame()
        df['timestamp'] = timestamps
        df['close'] = all_prices
        
        # Tạo open, high, low từ close
        df['open'] = df['close'].shift(1).fillna(df['close'])
        df['high'] = df.apply(lambda row: max(row['open'], row['close']) * (1 + np.random.uniform(0, 0.003)), axis=1)
        df['low'] = df.apply(lambda row: min(row['open'], row['close']) * (1 - np.random.uniform(0, 0.003)), axis=1)
        
        # Tạo volume
        df['volume'] = np.random.uniform(10, 100, total_points) * np.abs(df['close'] - df['open']) / df['open'] * 1000
        
        # Reset index
        df = df.reset_index(drop=True)
        
        logger.info(f"Đã tạo chuỗi giá mẫu với {total_points} điểm giá")
        
        return df
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các chỉ báo kỹ thuật cần thiết
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã thêm
        """
        # RSI
        window_length = 14
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window_length).mean()
        avg_loss = loss.rolling(window=window_length).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        
        # Bollinger Bands
        df['sma20'] = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma20'] + 2 * std20
        df['bb_lower'] = df['sma20'] - 2 * std20
        
        # Loại bỏ hàng NaN
        df.dropna(inplace=True)
        
        return df
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, leverage: int) -> Tuple[float, Dict]:
        """
        Tính toán kích thước vị thế tối ưu cho tài khoản nhỏ
        
        Args:
            entry_price (float): Giá dự kiến vào lệnh
            stop_loss (float): Giá dự kiến stop loss
            leverage (int): Đòn bẩy dự kiến sử dụng
            
        Returns:
            Tuple[float, Dict]: (Kích thước vị thế, Chi tiết)
        """
        # Tính khoảng cách % từ entry đến stop loss
        if entry_price > stop_loss:  # Long position
            stop_distance_percent = (entry_price - stop_loss) / entry_price * 100
            side = "buy"
        else:  # Short position
            stop_distance_percent = (stop_loss - entry_price) / entry_price * 100
            side = "sell"
        
        # Tính số tiền rủi ro
        risk_amount = self.current_balance * (self.risk_percent / 100)
        
        # Tính kích thước vị thế (USD)
        position_size_usd = (risk_amount / stop_distance_percent) * 100 * leverage
        
        # Số lượng Bitcoin
        quantity = position_size_usd / entry_price
        
        # Kiểm tra điểm thanh lý (liquidation)
        if side == "buy":
            liquidation_price = entry_price * (1 - (1 / leverage) + 0.004)  # 0.4% duy trì margin
            liquidation_distance = (entry_price - liquidation_price) / entry_price * 100
        else:  # sell
            liquidation_price = entry_price * (1 + (1 / leverage) - 0.004)
            liquidation_distance = (liquidation_price - entry_price) / entry_price * 100
            
        # Kiểm tra xem stop loss có quá gần điểm thanh lý
        min_distance_to_liquidation = 25.0  # 25% buffer
        if liquidation_distance * (1 - min_distance_to_liquidation/100) > stop_distance_percent:
            # Stop loss quá gần điểm thanh lý, điều chỉnh lại kích thước vị thế
            adjustment_factor = stop_distance_percent / (liquidation_distance * (1 - min_distance_to_liquidation/100))
            position_size_usd *= adjustment_factor
            quantity = position_size_usd / entry_price
            
            logger.info(f"Điều chỉnh kích thước vị thế do stop loss quá gần điểm thanh lý: "
                       f"${position_size_usd:.2f}, quantity={quantity:.8f}")
        
        # Giới hạn kích thước vị thế tối đa 80% số dư tài khoản
        max_size = self.current_balance * 0.8 * leverage
        if position_size_usd > max_size:
            position_size_usd = max_size
            quantity = position_size_usd / entry_price
            
            logger.info(f"Giới hạn kích thước vị thế tối đa: ${position_size_usd:.2f}, quantity={quantity:.8f}")
        
        details = {
            'side': side,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'leverage': leverage,
            'risk_amount': risk_amount,
            'risk_percent': self.risk_percent,
            'position_size_usd': position_size_usd,
            'quantity': quantity,
            'margin_used': position_size_usd / leverage,
            'stop_distance_percent': stop_distance_percent,
            'liquidation_price': liquidation_price,
            'liquidation_distance_percent': liquidation_distance
        }
        
        return position_size_usd, details
    
    def generate_scalping_signal(self, df: pd.DataFrame, idx: int, volatility_threshold: float = 1.5) -> Dict:
        """
        Tạo tín hiệu giao dịch scalping
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            idx (int): Chỉ số hàng hiện tại
            volatility_threshold (float): Ngưỡng biến động tối thiểu
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        signal = {'signal': 'neutral'}
        
        # Lấy giá và chỉ báo hiện tại
        current_price = df['close'].iloc[idx]
        current_rsi = df['rsi'].iloc[idx]
        prev_rsi = df['rsi'].iloc[idx-1] if idx > 0 else 50
        
        current_macd = df['macd'].iloc[idx]
        current_macd_signal = df['macd_signal'].iloc[idx]
        
        # Tính biến động
        atr = df['atr'].iloc[idx]
        volatility = (atr / current_price) * 100
        
        # Chỉ giao dịch khi biến động đủ lớn
        if volatility < volatility_threshold:
            return signal
        
        # Tính leverage dựa trên biến động
        if volatility < 2.0:
            leverage = min(20, self.max_leverage)
        elif volatility < 4.0:
            leverage = min(12, self.max_leverage)
        elif volatility < 6.0:
            leverage = min(8, self.max_leverage)
        else:
            leverage = min(5, self.max_leverage)
        
        # Tín hiệu mua
        if current_rsi < 30 and prev_rsi < current_rsi and current_macd > current_macd_signal:
            signal['signal'] = 'buy'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price * (1 - 0.01)  # 1% stop loss
            signal['take_profit'] = current_price * (1 + 0.02)  # 2% take profit
            signal['leverage'] = leverage
            
        # Tín hiệu bán
        elif current_rsi > 70 and prev_rsi > current_rsi and current_macd < current_macd_signal:
            signal['signal'] = 'sell'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price * (1 + 0.01)  # 1% stop loss
            signal['take_profit'] = current_price * (1 - 0.02)  # 2% take profit
            signal['leverage'] = leverage
        
        # Tính kích thước vị thế nếu có tín hiệu
        if signal['signal'] != 'neutral':
            position_size, details = self.calculate_position_size(
                entry_price=signal['entry_price'],
                stop_loss=signal['stop_loss'],
                leverage=signal['leverage']
            )
            
            signal.update(details)
        
        return signal
    
    def generate_trend_signal(self, df: pd.DataFrame, idx: int) -> Dict:
        """
        Tạo tín hiệu giao dịch theo xu hướng
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            idx (int): Chỉ số hàng hiện tại
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        signal = {'signal': 'neutral'}
        
        # Lấy giá và chỉ báo hiện tại
        current_price = df['close'].iloc[idx]
        current_macd = df['macd'].iloc[idx]
        current_macd_signal = df['macd_signal'].iloc[idx]
        
        prev_macd = df['macd'].iloc[idx-1] if idx > 0 else 0
        prev_macd_signal = df['macd_signal'].iloc[idx-1] if idx > 0 else 0
        
        # Tính biến động
        atr = df['atr'].iloc[idx]
        volatility = (atr / current_price) * 100
        
        # Tính leverage dựa trên biến động
        if volatility < 2.0:
            leverage = min(16, self.max_leverage)
        elif volatility < 4.0:
            leverage = min(10, self.max_leverage)
        else:
            leverage = min(6, self.max_leverage)
        
        # Tín hiệu mua (MACD cắt lên)
        if (prev_macd < prev_macd_signal and current_macd > current_macd_signal) or \
           (current_macd > current_macd_signal and current_macd > prev_macd):
            signal['signal'] = 'buy'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price * (1 - 0.015)  # 1.5% stop loss
            signal['take_profit'] = current_price * (1 + 0.03)  # 3% take profit
            signal['leverage'] = leverage
            
        # Tín hiệu bán (MACD cắt xuống)
        elif (prev_macd > prev_macd_signal and current_macd < current_macd_signal) or \
             (current_macd < current_macd_signal and current_macd < prev_macd):
            signal['signal'] = 'sell'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price * (1 + 0.015)  # 1.5% stop loss
            signal['take_profit'] = current_price * (1 - 0.03)  # 3% take profit
            signal['leverage'] = leverage
        
        # Tính kích thước vị thế nếu có tín hiệu
        if signal['signal'] != 'neutral':
            position_size, details = self.calculate_position_size(
                entry_price=signal['entry_price'],
                stop_loss=signal['stop_loss'],
                leverage=signal['leverage']
            )
            
            signal.update(details)
        
        return signal
    
    def run_demo(self, strategy='scalping', days=30):
        """
        Chạy demo giao dịch
        
        Args:
            strategy (str): Chiến lược giao dịch ('scalping' hoặc 'trend')
            days (int): Số ngày mô phỏng
        """
        logger.info(f"Bắt đầu demo với chiến lược {strategy}, vốn ${self.initial_balance}")
        
        # Tạo dữ liệu giá mẫu
        df = self.create_price_series(days=days)
        
        # Thêm các chỉ báo
        df = self.add_indicators(df)
        
        # Biến theo dõi trạng thái
        current_position = None
        trade_id = 0
        
        # Lưu số dư ban đầu
        self.balance_history.append({
            'timestamp': df['timestamp'].iloc[0],
            'balance': self.current_balance
        })
        
        # Chạy mô phỏng
        for idx in range(len(df)):
            current_time = df['timestamp'].iloc[idx]
            current_price = df['close'].iloc[idx]
            
            # Cập nhật vị thế nếu đang có
            if current_position:
                # Kiểm tra điều kiện đóng vị thế
                close_position = False
                close_reason = ""
                
                if current_position['side'] == 'buy':
                    # Kiểm tra stop loss
                    if current_price <= current_position['stop_loss']:
                        close_position = True
                        close_reason = "stop_loss"
                    # Kiểm tra take profit
                    elif current_price >= current_position['take_profit']:
                        close_position = True
                        close_reason = "take_profit"
                else:  # 'sell'
                    # Kiểm tra stop loss
                    if current_price >= current_position['stop_loss']:
                        close_position = True
                        close_reason = "stop_loss"
                    # Kiểm tra take profit
                    elif current_price <= current_position['take_profit']:
                        close_position = True
                        close_reason = "take_profit"
                
                # Đóng vị thế nếu cần
                if close_position:
                    # Tính P&L
                    if current_position['side'] == 'buy':
                        pnl = (current_price - current_position['entry_price']) * current_position['quantity']
                        pnl_percent = (current_price - current_position['entry_price']) / current_position['entry_price'] * 100 * current_position['leverage']
                    else:  # 'sell'
                        pnl = (current_position['entry_price'] - current_price) * current_position['quantity']
                        pnl_percent = (current_position['entry_price'] - current_price) / current_position['entry_price'] * 100 * current_position['leverage']
                    
                    # Cập nhật số dư
                    self.current_balance += pnl
                    
                    # Thêm thông tin giao dịch
                    trade_info = {
                        'trade_id': trade_id,
                        'side': current_position['side'],
                        'entry_time': current_position['entry_time'],
                        'entry_price': current_position['entry_price'],
                        'exit_time': current_time,
                        'exit_price': current_price,
                        'leverage': current_position['leverage'],
                        'quantity': current_position['quantity'],
                        'position_size': current_position['position_size_usd'],
                        'stop_loss': current_position['stop_loss'],
                        'take_profit': current_position['take_profit'],
                        'pnl': pnl,
                        'pnl_percent': pnl_percent,
                        'exit_reason': close_reason
                    }
                    
                    self.trades.append(trade_info)
                    
                    # Lưu số dư mới
                    self.balance_history.append({
                        'timestamp': current_time,
                        'balance': self.current_balance
                    })
                    
                    logger.info(f"Giao dịch #{trade_id} đã đóng: {current_position['side'].upper()}, "
                              f"Entry=${current_position['entry_price']:.2f}, Exit=${current_price:.2f}, "
                              f"P&L=${pnl:.2f} ({pnl_percent:+.2f}%), Balance=${self.current_balance:.2f}")
                    
                    # Reset vị thế
                    current_position = None
                    trade_id += 1
            
            # Nếu không có vị thế mở, tạo tín hiệu mới
            if not current_position:
                # Tạo tín hiệu theo chiến lược
                if strategy == 'scalping':
                    signal = self.generate_scalping_signal(df, idx)
                else:  # 'trend'
                    signal = self.generate_trend_signal(df, idx)
                
                # Nếu có tín hiệu, mở vị thế mới
                if signal['signal'] != 'neutral':
                    # Thêm thông tin thời gian
                    signal['entry_time'] = current_time
                    
                    # Ghi nhận vị thế mới
                    current_position = signal
                    
                    logger.info(f"Giao dịch #{trade_id} đã mở: {signal['side'].upper()}, "
                              f"Entry=${signal['entry_price']:.2f}, Stop=${signal['stop_loss']:.2f}, "
                              f"TP=${signal['take_profit']:.2f}, Leverage=x{signal['leverage']}, "
                              f"Size=${signal['position_size_usd']:.2f}, Quantity={signal['quantity']:.8f}")
        
        # Đóng vị thế cuối cùng nếu còn
        if current_position:
            # Lấy giá cuối cùng
            final_price = df['close'].iloc[-1]
            
            # Tính P&L
            if current_position['side'] == 'buy':
                pnl = (final_price - current_position['entry_price']) * current_position['quantity']
                pnl_percent = (final_price - current_position['entry_price']) / current_position['entry_price'] * 100 * current_position['leverage']
            else:  # 'sell'
                pnl = (current_position['entry_price'] - final_price) * current_position['quantity']
                pnl_percent = (current_position['entry_price'] - final_price) / current_position['entry_price'] * 100 * current_position['leverage']
            
            # Cập nhật số dư
            self.current_balance += pnl
            
            # Thêm thông tin giao dịch
            trade_info = {
                'trade_id': trade_id,
                'side': current_position['side'],
                'entry_time': current_position['entry_time'],
                'entry_price': current_position['entry_price'],
                'exit_time': df['timestamp'].iloc[-1],
                'exit_price': final_price,
                'leverage': current_position['leverage'],
                'quantity': current_position['quantity'],
                'position_size': current_position['position_size_usd'],
                'stop_loss': current_position['stop_loss'],
                'take_profit': current_position['take_profit'],
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'exit_reason': 'end_of_demo'
            }
            
            self.trades.append(trade_info)
            
            # Lưu số dư cuối cùng
            self.balance_history.append({
                'timestamp': df['timestamp'].iloc[-1],
                'balance': self.current_balance
            })
            
            logger.info(f"Giao dịch cuối #{trade_id} đã đóng: {current_position['side'].upper()}, "
                      f"Entry=${current_position['entry_price']:.2f}, Exit=${final_price:.2f}, "
                      f"P&L=${pnl:.2f} ({pnl_percent:+.2f}%), Balance=${self.current_balance:.2f}")
        
        # Tính các chỉ số hiệu suất
        results = self._calculate_performance()
        
        # Vẽ biểu đồ
        self._plot_results(df, strategy)
        
        return results
    
    def _calculate_performance(self) -> Dict:
        """
        Tính toán các chỉ số hiệu suất
        
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        if not self.trades:
            return {
                'status': 'No trades executed',
                'initial_balance': self.initial_balance,
                'final_balance': self.current_balance
            }
        
        # Số giao dịch
        total_trades = len(self.trades)
        profitable_trades = len([t for t in self.trades if t['pnl'] > 0])
        losing_trades = total_trades - profitable_trades
        
        # Tỷ lệ thắng
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        # Lợi nhuận / thua lỗ
        total_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        total_loss = abs(sum(t['pnl'] for t in self.trades if t['pnl'] <= 0))
        net_profit = total_profit - total_loss
        
        # Profit factor
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Lợi nhuận trung bình
        avg_profit = total_profit / profitable_trades if profitable_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # ROI
        roi = (self.current_balance - self.initial_balance) / self.initial_balance * 100
        
        # Drawdown
        balances = [entry['balance'] for entry in self.balance_history]
        max_balance = balances[0]
        drawdowns = []
        
        for balance in balances:
            if balance > max_balance:
                max_balance = balance
            drawdown = (max_balance - balance) / max_balance * 100
            drawdowns.append(drawdown)
            
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Kết quả
        results = {
            'initial_balance': self.initial_balance,
            'final_balance': self.current_balance,
            'net_profit': net_profit,
            'roi': roi,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown
        }
        
        return results
    
    def _plot_results(self, df: pd.DataFrame, strategy: str):
        """
        Vẽ biểu đồ kết quả giao dịch
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            strategy (str): Chiến lược giao dịch
        """
        # Vẽ biểu đồ chính
        plt.figure(figsize=(15, 12))
        
        # Subplot 1: Giá và các giao dịch
        plt.subplot(3, 1, 1)
        plt.plot(df['timestamp'], df['close'], label='Close Price')
        
        # Vẽ các điểm entry/exit
        for trade in self.trades:
            entry_time = trade['entry_time']
            exit_time = trade['exit_time']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            
            if trade['side'] == 'buy':
                plt.scatter(entry_time, entry_price, marker='^', color='g', s=100)
                if trade['pnl'] > 0:
                    plt.scatter(exit_time, exit_price, marker='o', color='g', s=100)
                else:
                    plt.scatter(exit_time, exit_price, marker='o', color='r', s=100)
            else:  # 'sell'
                plt.scatter(entry_time, entry_price, marker='v', color='r', s=100)
                if trade['pnl'] > 0:
                    plt.scatter(exit_time, exit_price, marker='o', color='g', s=100)
                else:
                    plt.scatter(exit_time, exit_price, marker='o', color='r', s=100)
        
        plt.title(f'Price Chart with Trades - {strategy.capitalize()} Strategy')
        plt.ylabel('Price ($)')
        plt.grid(True, alpha=0.3)
        
        # Subplot 2: Equity curve
        plt.subplot(3, 1, 2)
        balances = [entry['balance'] for entry in self.balance_history]
        timestamps = [entry['timestamp'] for entry in self.balance_history]
        
        plt.plot(timestamps, balances, label='Account Balance')
        plt.axhline(y=self.initial_balance, color='r', linestyle='--', label=f'Initial Balance (${self.initial_balance})')
        
        plt.title('Equity Curve')
        plt.ylabel('Balance ($)')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Subplot 3: Drawdown
        plt.subplot(3, 1, 3)
        
        max_balance = balances[0]
        drawdowns = []
        
        for balance in balances:
            if balance > max_balance:
                max_balance = balance
            drawdown = (max_balance - balance) / max_balance * 100
            drawdowns.append(drawdown)
        
        plt.fill_between(timestamps, drawdowns, color='red', alpha=0.3)
        plt.title('Drawdown (%)')
        plt.ylabel('Drawdown (%)')
        plt.grid(True, alpha=0.3)
        
        # Tạo tiêu đề chung
        plt.suptitle(f'Demo Results: ${self.initial_balance} Initial Balance, {strategy.capitalize()} Strategy', fontsize=16)
        
        # Chỉnh định dạng và lưu
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(f"demo_results/micro_demo_{strategy}.png")
        
        logger.info(f"Đã lưu biểu đồ kết quả vào demo_results/micro_demo_{strategy}.png")

def run_multiple_demos():
    """Chạy nhiều demo với các cấu hình khác nhau"""
    strategies = ['scalping', 'trend']
    results = {}
    
    for strategy in strategies:
        # Khởi tạo demo
        demo = MicroTradingDemo(initial_balance=100.0, max_leverage=20, risk_percent=2.0)
        
        # Chạy demo
        result = demo.run_demo(strategy=strategy, days=30)
        
        # Lưu kết quả
        results[strategy] = result
    
    # So sánh kết quả
    print("\n===== KẾT QUẢ DEMO BOT GIAO DỊCH VỐN NHỎ =====")
    print(f"Vốn ban đầu: $100.00")
    print(f"Đòn bẩy tối đa: x20")
    print(f"Rủi ro mỗi giao dịch: 2.0%")
    
    print("\nHiệu suất các chiến lược:")
    for strategy, result in results.items():
        print(f"\n  {strategy.upper()}:")
        print(f"    Số dư cuối: ${result['final_balance']:.2f}")
        print(f"    ROI: {result['roi']:+.2f}%")
        print(f"    Số giao dịch: {result['total_trades']}")
        print(f"    Win rate: {result['win_rate']:.2%}")
        print(f"    Profit factor: {result['profit_factor']:.2f}")
        print(f"    Drawdown tối đa: {result['max_drawdown']:.2f}%")
    
    # Khuyến nghị
    best_strategy = max(results.keys(), key=lambda s: results[s]['roi'])
    print(f"\nChiến lược tốt nhất: {best_strategy.upper()}")
    print(f"  ROI: {results[best_strategy]['roi']:+.2f}%")
    
    print("\nKhuyến nghị:")
    if results[best_strategy]['roi'] > 0:
        print(f"  - Nên sử dụng chiến lược {best_strategy} với vốn $100")
        
        if results[best_strategy]['max_drawdown'] > 30:
            print("  - Cảnh báo: Drawdown khá cao, nên giảm đòn bẩy hoặc rủi ro mỗi giao dịch")
            
        if results[best_strategy]['win_rate'] < 0.4:
            print("  - Cảnh báo: Win rate thấp, cân nhắc thêm bộ lọc cho tín hiệu")
    else:
        print("  - Cảnh báo: Không có chiến lược nào có lợi nhuận dương")
    
    print("\nĐã lưu biểu đồ kết quả vào thư mục: demo_results")

if __name__ == "__main__":
    run_multiple_demos()