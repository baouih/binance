#!/usr/bin/env python3
"""
Script kiểm thử bot giao dịch Bitcoin với vốn nhỏ (100 USD) và đòn bẩy cao

Script này thực hiện kiểm thử tất cả các chiến lược micro trading trên
dữ liệu lịch sử để đánh giá hiệu suất với tài khoản vốn nhỏ.
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Import các module đã tạo
from micro_position_sizing import MicroPositionSizer
from micro_trading_strategy import MicroTradingStrategy
from leverage_risk_manager import LeverageRiskManager

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("micro_bot_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("micro_bot_test")

# Tạo thư mục cho kết quả
os.makedirs("micro_test_results", exist_ok=True)
os.makedirs("micro_test_charts", exist_ok=True)

class MicroBotTester:
    """Lớp kiểm thử bot giao dịch với vốn nhỏ và đòn bẩy cao"""
    
    def __init__(self, 
                initial_balance: float = 100.0,
                max_leverage: int = 20,
                risk_per_trade: float = 2.0,
                data_dir: str = 'test_data'):
        """
        Khởi tạo bộ kiểm thử bot
        
        Args:
            initial_balance (float): Số dư ban đầu (USD)
            max_leverage (int): Đòn bẩy tối đa
            risk_per_trade (float): Rủi ro trên mỗi giao dịch (%)
            data_dir (str): Thư mục chứa dữ liệu kiểm thử
        """
        self.initial_balance = initial_balance
        self.max_leverage = max_leverage
        self.risk_per_trade = risk_per_trade
        self.data_dir = data_dir
        
        # Danh sách chiến lược để kiểm thử
        self.strategies = ['scalping', 'breakout', 'reversal', 'trend']
        
        # Kết quả kiểm thử
        self.test_results = {}
        
        logger.info(f"Khởi tạo MicroBotTester: Balance=${initial_balance}, "
                   f"MaxLeverage=x{max_leverage}, Risk={risk_per_trade}%")
    
    def load_test_data(self, symbol: str = 'BTCUSDT', interval: str = '1h') -> pd.DataFrame:
        """
        Tải dữ liệu kiểm thử
        
        Args:
            symbol (str): Mã cặp giao dịch
            interval (str): Khung thời gian
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu giá
        """
        # Tìm file dữ liệu phù hợp
        file_pattern = f"{symbol}_{interval}"
        data_files = [f for f in os.listdir(self.data_dir) if file_pattern in f and f.endswith('.csv')]
        
        if not data_files:
            logger.error(f"Không tìm thấy dữ liệu cho {symbol}_{interval}")
            # Tạo dữ liệu giả nếu không tìm thấy file
            return self._generate_mock_data(symbol, interval)
        
        # Sử dụng file đầu tiên tìm thấy
        data_file = os.path.join(self.data_dir, data_files[0])
        logger.info(f"Tải dữ liệu từ {data_file}")
        
        try:
            # Đọc dữ liệu từ CSV
            df = pd.read_csv(data_file)
            
            # Chuyển đổi cột thời gian sang datetime nếu cần
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif 'open_time' in df.columns:
                df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
            
            # Chuẩn hóa tên cột
            if 'close' not in df.columns and 'Close' in df.columns:
                df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 
                                 'Close': 'close', 'Volume': 'volume'}, inplace=True)
                
            # Thêm chỉ báo nếu cần
            df = self._add_indicators(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu: {e}")
            return self._generate_mock_data(symbol, interval)
    
    def _generate_mock_data(self, symbol: str, interval: str) -> pd.DataFrame:
        """
        Tạo dữ liệu mẫu khi không có dữ liệu thực
        
        Args:
            symbol (str): Mã cặp giao dịch
            interval (str): Khung thời gian
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu giá mẫu
        """
        logger.warning(f"Tạo dữ liệu mẫu cho {symbol}_{interval}")
        
        # Tạo 1000 nến giá với xu hướng ngẫu nhiên
        num_candles = 1000
        
        # Thời gian bắt đầu (365 ngày trước)
        start_time = datetime.now() - timedelta(days=365)
        
        # Tạo dữ liệu thời gian dựa trên interval
        if interval == '1h':
            timestamps = [start_time + timedelta(hours=i) for i in range(num_candles)]
        elif interval == '15m':
            timestamps = [start_time + timedelta(minutes=15*i) for i in range(num_candles)]
        elif interval == '1d':
            timestamps = [start_time + timedelta(days=i) for i in range(num_candles)]
        else:
            timestamps = [start_time + timedelta(hours=i) for i in range(num_candles)]
        
        # Tạo giá mẫu
        initial_price = 35000.0
        volatility = 0.01
        trend = 0.001
        
        prices = [initial_price]
        for i in range(1, num_candles):
            # Tạo giá với xu hướng và biến động ngẫu nhiên
            rnd = np.random.randn()
            change = trend + volatility * rnd
            
            # Thêm một số xu hướng thị trường để kiểm thử
            if i % 200 < 100:  # Giai đoạn uptrend
                change += 0.002
            else:  # Giai đoạn downtrend
                change -= 0.001
                
            # Thêm một số biến động cao ở giữa để kiểm thử
            if 400 < i < 600:
                change *= 2
            
            price = prices[-1] * (1 + change)
            prices.append(price)
        
        # Tạo dữ liệu OHLCV
        df = pd.DataFrame()
        df['timestamp'] = timestamps
        df['open'] = prices
        
        # Tạo high, low từ giá mở cửa
        df['high'] = df['open'] * (1 + np.random.uniform(0, 0.01, num_candles))
        df['low'] = df['open'] * (1 - np.random.uniform(0, 0.01, num_candles))
        df['close'] = df['open'] * (1 + np.random.normal(0, 0.005, num_candles))
        
        # Đảm bảo high >= open, close và low <= open, close
        for i in range(num_candles):
            df.loc[i, 'high'] = max(df.loc[i, 'high'], df.loc[i, 'open'], df.loc[i, 'close'])
            df.loc[i, 'low'] = min(df.loc[i, 'low'], df.loc[i, 'open'], df.loc[i, 'close'])
        
        # Tạo volume
        df['volume'] = np.random.uniform(100, 500, num_candles) * np.abs(df['close'] - df['open']) / df['open']
        
        # Lưu dữ liệu mẫu
        mock_file = os.path.join(self.data_dir, f"{symbol}_{interval}_mock.csv")
        df.to_csv(mock_file, index=False)
        logger.info(f"Đã lưu dữ liệu mẫu vào {mock_file}")
        
        # Thêm các chỉ báo
        df = self._add_indicators(df)
        
        return df
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các chỉ báo kỹ thuật cần thiết vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã thêm
        """
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain_14 = gain.rolling(window=14).mean()
        avg_loss_14 = loss.rolling(window=14).mean()
        rs_14 = avg_gain_14 / avg_loss_14
        df['rsi'] = 100 - (100 / (1 + rs_14))
        
        avg_gain_7 = gain.rolling(window=7).mean()
        avg_loss_7 = loss.rolling(window=7).mean()
        rs_7 = avg_gain_7 / avg_loss_7
        df['rsi_7'] = 100 - (100 / (1 + rs_7))
        
        # EMA
        for period in [9, 21, 50, 200]:
            df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['sma20'] = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma20'] + 2 * std20
        df['bb_lower'] = df['sma20'] - 2 * std20
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        
        # Stochastic
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        
        # Loại bỏ các hàng NaN
        df.dropna(inplace=True)
        
        return df
    
    def test_strategy(self, 
                     strategy_type: str,
                     data: pd.DataFrame,
                     symbol: str = 'BTCUSDT') -> Dict:
        """
        Kiểm thử một chiến lược cụ thể
        
        Args:
            strategy_type (str): Loại chiến lược ('scalping', 'breakout', 'reversal', 'trend')
            data (pd.DataFrame): Dữ liệu kiểm thử
            symbol (str): Mã cặp giao dịch
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        logger.info(f"Bắt đầu kiểm thử chiến lược {strategy_type} với ${self.initial_balance}")
        
        # Khởi tạo các thành phần bot
        position_sizer = MicroPositionSizer(
            initial_balance=self.initial_balance,
            max_leverage=self.max_leverage,
            max_risk_per_trade_percent=self.risk_per_trade,
            adaptive_sizing=True
        )
        
        strategy = MicroTradingStrategy(
            initial_balance=self.initial_balance,
            max_leverage=self.max_leverage,
            risk_per_trade=self.risk_per_trade,
            strategy_type=strategy_type
        )
        
        risk_manager = LeverageRiskManager(
            initial_balance=self.initial_balance,
            max_leverage=self.max_leverage,
            max_positions=3,
            max_risk_per_trade=self.risk_per_trade,
            max_account_risk=15.0,
            min_distance_to_liquidation=20.0
        )
        
        # Kết quả kiểm thử
        results = {
            'strategy': strategy_type,
            'symbol': symbol,
            'initial_balance': self.initial_balance,
            'max_leverage': self.max_leverage,
            'risk_per_trade': self.risk_per_trade,
            'trades': [],
            'balance_history': [],
            'equity_history': []
        }
        
        # Lưu số dư ban đầu vào lịch sử
        results['balance_history'].append({
            'timestamp': data['timestamp'].iloc[50].strftime('%Y-%m-%d %H:%M:%S'),
            'balance': self.initial_balance
        })
        
        results['equity_history'].append({
            'timestamp': data['timestamp'].iloc[50].strftime('%Y-%m-%d %H:%M:%S'),
            'equity': self.initial_balance
        })
        
        # Biến theo dõi trạng thái
        current_balance = self.initial_balance
        current_position = None
        open_positions = {}  # ID vị thế -> thông tin vị thế
        trade_id = 0
        
        # Chạy mô phỏng trên toàn bộ dữ liệu
        for i in range(50, len(data)):
            # Lấy dữ liệu hiện tại
            curr_data = data.iloc[:i+1]
            current_time = curr_data['timestamp'].iloc[-1]
            current_price = curr_data['close'].iloc[-1]
            
            # Cập nhật equity cho vị thế đang mở
            if open_positions:
                equity = current_balance
                for pos_id, pos in open_positions.items():
                    # Tính P&L hiện tại
                    if pos['side'] == 'buy':
                        unrealized_pnl = (current_price - pos['entry_price']) * pos['quantity']
                    else:  # 'sell'
                        unrealized_pnl = (pos['entry_price'] - current_price) * pos['quantity']
                        
                    equity += unrealized_pnl
                    
                # Thêm vào lịch sử
                results['equity_history'].append({
                    'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'equity': equity
                })
            
            # Cập nhật các vị thế đang mở
            positions_to_close = []
            for pos_id, pos in open_positions.items():
                # Kiểm tra điều kiện đóng vị thế
                if pos['side'] == 'buy':
                    # Kiểm tra stop loss
                    if current_price <= pos['stop_loss']:
                        positions_to_close.append((pos_id, current_price, 'stop_loss'))
                    # Kiểm tra take profit
                    elif current_price >= pos['take_profit']:
                        positions_to_close.append((pos_id, current_price, 'take_profit'))
                else:  # 'sell'
                    # Kiểm tra stop loss
                    if current_price >= pos['stop_loss']:
                        positions_to_close.append((pos_id, current_price, 'stop_loss'))
                    # Kiểm tra take profit
                    elif current_price <= pos['take_profit']:
                        positions_to_close.append((pos_id, current_price, 'take_profit'))
            
            # Đóng vị thế nếu cần
            for pos_id, exit_price, reason in positions_to_close:
                pos = open_positions[pos_id]
                
                # Tính P&L
                if pos['side'] == 'buy':
                    pnl = (exit_price - pos['entry_price']) * pos['quantity']
                    pnl_percent = (exit_price - pos['entry_price']) / pos['entry_price'] * 100 * pos['leverage']
                else:  # 'sell'
                    pnl = (pos['entry_price'] - exit_price) * pos['quantity']
                    pnl_percent = (pos['entry_price'] - exit_price) / pos['entry_price'] * 100 * pos['leverage']
                
                # Cập nhật số dư
                current_balance += pnl
                
                # Thêm thông tin giao dịch
                trade_info = {
                    'trade_id': pos_id,
                    'side': pos['side'],
                    'entry_time': pos['entry_time'],
                    'entry_price': pos['entry_price'],
                    'exit_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'exit_price': exit_price,
                    'leverage': pos['leverage'],
                    'quantity': pos['quantity'],
                    'position_size': pos['position_size'],
                    'stop_loss': pos['stop_loss'],
                    'take_profit': pos['take_profit'],
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'exit_reason': reason
                }
                
                results['trades'].append(trade_info)
                
                # Lưu số dư mới vào lịch sử
                results['balance_history'].append({
                    'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'balance': current_balance
                })
                
                # Đóng vị thế trong risk manager
                success, closed_pos = risk_manager.close_position(
                    position_id=pos_id,
                    exit_price=exit_price,
                    exit_reason=reason
                )
                
                # Xóa khỏi danh sách vị thế mở
                del open_positions[pos_id]
                
                logger.info(f"Đóng vị thế #{pos_id}, P&L=${pnl:.2f} ({pnl_percent:+.2f}%), "
                           f"Balance=${current_balance:.2f}, Reason: {reason}")
            
            # Cập nhật số dư trong các thành phần
            risk_manager.update_balance(current_balance)
            position_sizer.update_balance(current_balance)
            
            # Tạo tín hiệu
            signal = strategy.generate_signal(curr_data)
            
            # Kiểm tra số vị thế đang mở
            if len(open_positions) >= 3:
                continue  # Đã đạt giới hạn vị thế
                
            # Nếu có tín hiệu mới
            if signal['signal'] in ['buy', 'sell']:
                # Tính toán kích thước vị thế
                signal = strategy.calculate_position_size(signal)
                
                # Xác thực giao dịch qua risk manager
                entry_price = signal['entry_price']
                stop_loss = signal['stop_loss']
                take_profit = signal['take_profit']
                leverage = signal['effective_leverage']
                side = signal['signal']
                
                is_valid, validation = risk_manager.validate_trade(
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    leverage=leverage,
                    side=side
                )
                
                if is_valid:
                    # Mở vị thế mới
                    success, position = risk_manager.add_position(
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        leverage=leverage,
                        side=side,
                        position_size=signal['position_size_usd']
                    )
                    
                    if success:
                        # Thêm vị thế vào danh sách theo dõi
                        position['entry_time'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
                        position['position_size'] = signal['position_size_usd']
                        position['quantity'] = signal['quantity']
                        open_positions[position['position_id']] = position
                        
                        logger.info(f"Mở vị thế {side.upper()} #{position['position_id']}: "
                                  f"Price=${entry_price:.2f}, Size=${signal['position_size_usd']:.2f}, "
                                  f"Leverage=x{leverage}, Balance=${current_balance:.2f}")
        
        # Đóng tất cả vị thế còn lại ở cuối kiểm thử
        final_price = data['close'].iloc[-1]
        
        for pos_id, pos in list(open_positions.items()):
            # Tính P&L
            if pos['side'] == 'buy':
                pnl = (final_price - pos['entry_price']) * pos['quantity']
                pnl_percent = (final_price - pos['entry_price']) / pos['entry_price'] * 100 * pos['leverage']
            else:  # 'sell'
                pnl = (pos['entry_price'] - final_price) * pos['quantity']
                pnl_percent = (pos['entry_price'] - final_price) / pos['entry_price'] * 100 * pos['leverage']
            
            # Cập nhật số dư
            current_balance += pnl
            
            # Thêm thông tin giao dịch
            trade_info = {
                'trade_id': pos_id,
                'side': pos['side'],
                'entry_time': pos['entry_time'],
                'entry_price': pos['entry_price'],
                'exit_time': data['timestamp'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S'),
                'exit_price': final_price,
                'leverage': pos['leverage'],
                'quantity': pos['quantity'],
                'position_size': pos['position_size'],
                'stop_loss': pos['stop_loss'],
                'take_profit': pos['take_profit'],
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'exit_reason': 'end_of_test'
            }
            
            results['trades'].append(trade_info)
            
            logger.info(f"Đóng vị thế #{pos_id} (kết thúc kiểm thử), P&L=${pnl:.2f} "
                       f"({pnl_percent:+.2f}%), Balance=${current_balance:.2f}")
        
        # Cập nhật số dư cuối cùng
        results['final_balance'] = current_balance
        results['profit_loss'] = current_balance - self.initial_balance
        results['profit_loss_percent'] = (results['profit_loss'] / self.initial_balance) * 100
        
        # Tính các chỉ số hiệu suất
        if results['trades']:
            results['total_trades'] = len(results['trades'])
            results['winning_trades'] = len([t for t in results['trades'] if t['pnl'] > 0])
            results['losing_trades'] = results['total_trades'] - results['winning_trades']
            
            results['win_rate'] = results['winning_trades'] / results['total_trades']
            
            # Profit factor
            total_profit = sum(t['pnl'] for t in results['trades'] if t['pnl'] > 0)
            total_loss = abs(sum(t['pnl'] for t in results['trades'] if t['pnl'] <= 0))
            
            if total_loss > 0:
                results['profit_factor'] = total_profit / total_loss
            else:
                results['profit_factor'] = float('inf') if total_profit > 0 else 0
            
            # Trong giao dịch với đòn bẩy cao, drawdown là rất quan trọng
            # Tính drawdown từ lịch sử equity
            equity_values = [entry['equity'] for entry in results['equity_history']]
            peak = equity_values[0]
            drawdowns = []
            
            for equity in equity_values:
                if equity > peak:
                    peak = equity
                drawdown_pct = (peak - equity) / peak * 100
                drawdowns.append(drawdown_pct)
                
            results['max_drawdown'] = max(drawdowns)
            
            # Avg profit/loss
            if results['winning_trades'] > 0:
                results['avg_profit'] = sum(t['pnl'] for t in results['trades'] if t['pnl'] > 0) / results['winning_trades']
            else:
                results['avg_profit'] = 0
                
            if results['losing_trades'] > 0:
                results['avg_loss'] = sum(t['pnl'] for t in results['trades'] if t['pnl'] <= 0) / results['losing_trades']
            else:
                results['avg_loss'] = 0
        else:
            results['total_trades'] = 0
            results['winning_trades'] = 0
            results['losing_trades'] = 0
            results['win_rate'] = 0
            results['profit_factor'] = 0
            results['max_drawdown'] = 0
            results['avg_profit'] = 0
            results['avg_loss'] = 0
        
        logger.info(f"Kết thúc kiểm thử {strategy_type}: Balance=${current_balance:.2f}, "
                   f"P&L=${results['profit_loss']:.2f} ({results['profit_loss_percent']:+.2f}%), "
                   f"Trades={results['total_trades']}, Win={results['win_rate']:.2%}")
        
        return results
    
    def run_all_tests(self, symbol: str = 'BTCUSDT', interval: str = '1h') -> Dict:
        """
        Chạy kiểm thử với tất cả các chiến lược
        
        Args:
            symbol (str): Mã cặp giao dịch
            interval (str): Khung thời gian
            
        Returns:
            Dict: Kết quả kiểm thử
        """
        logger.info(f"Bắt đầu kiểm thử toàn diện: {symbol}_{interval}, Vốn=${self.initial_balance}")
        
        # Tải dữ liệu
        data = self.load_test_data(symbol, interval)
        
        # Chạy từng chiến lược
        results = {}
        for strategy_type in self.strategies:
            result = self.test_strategy(strategy_type, data, symbol)
            results[strategy_type] = result
            
            # Lưu kết quả riêng lẻ
            self._save_result(result, f"{symbol}_{interval}_{strategy_type}_micro")
            
            # Vẽ biểu đồ
            self._plot_equity_curve(result, f"{symbol}_{interval}_{strategy_type}_micro")
        
        # Tạo báo cáo tổng hợp
        summary = self._create_summary(results)
        
        # Vẽ biểu đồ so sánh
        self._plot_comparison(results, f"{symbol}_{interval}_micro_comparison")
        
        # Lưu kết quả tổng hợp
        with open(f"micro_test_results/{symbol}_{interval}_micro_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"Đã lưu kết quả tổng hợp vào micro_test_results/{symbol}_{interval}_micro_summary.json")
        
        return summary
    
    def _save_result(self, result: Dict, filename: str) -> None:
        """
        Lưu kết quả kiểm thử
        
        Args:
            result (Dict): Kết quả kiểm thử
            filename (str): Tên file
        """
        with open(f"micro_test_results/{filename}.json", 'w') as f:
            json.dump(result, f, indent=2)
            
        logger.info(f"Đã lưu kết quả kiểm thử vào micro_test_results/{filename}.json")
    
    def _plot_equity_curve(self, result: Dict, filename: str) -> None:
        """
        Vẽ biểu đồ equity curve
        
        Args:
            result (Dict): Kết quả kiểm thử
            filename (str): Tên file
        """
        try:
            # Tạo biểu đồ
            plt.figure(figsize=(12, 6))
            
            # Lấy dữ liệu
            if 'equity_history' in result and result['equity_history']:
                timestamps = [entry['timestamp'] for entry in result['equity_history']]
                equity = [entry['equity'] for entry in result['equity_history']]
                
                # Chuyển đổi timestamp sang datetime
                dates = [datetime.strptime(ts, '%Y-%m-%d %H:%M:%S') for ts in timestamps]
                
                # Vẽ đường equity
                plt.plot(dates, equity, label='Equity')
                
                # Vẽ đường số dư ban đầu
                plt.axhline(y=result['initial_balance'], color='r', linestyle='--', 
                          label=f'Initial Balance (${result["initial_balance"]})')
                
                # Vẽ các giao dịch
                for trade in result['trades']:
                    entry_time = datetime.strptime(trade['entry_time'], '%Y-%m-%d %H:%M:%S')
                    exit_time = datetime.strptime(trade['exit_time'], '%Y-%m-%d %H:%M:%S')
                    
                    # Tìm equity tại thời điểm entry và exit
                    entry_idx = 0
                    exit_idx = len(dates) - 1
                    
                    for i, date in enumerate(dates):
                        if date >= entry_time:
                            entry_idx = i
                            break
                            
                    for i in range(len(dates) - 1, -1, -1):
                        if dates[i] <= exit_time:
                            exit_idx = i
                            break
                    
                    entry_equity = equity[entry_idx]
                    exit_equity = equity[exit_idx]
                    
                    # Vẽ marker cho entry và exit
                    if trade['pnl'] > 0:
                        color = 'g'  # Giao dịch thắng
                    else:
                        color = 'r'  # Giao dịch thua
                        
                    plt.scatter(entry_time, entry_equity, color=color, marker='^', alpha=0.7)
                    plt.scatter(exit_time, exit_equity, color=color, marker='v', alpha=0.7)
                
                # Thêm thông tin hiệu suất
                title = (f"Equity Curve: {result['strategy']} Strategy on {result['symbol']}\n"
                       f"Balance: ${result['final_balance']:.2f} ({result['profit_loss_percent']:+.2f}%), "
                       f"Trades: {result['total_trades']}, Win Rate: {result['win_rate']:.2%}")
                
                plt.title(title)
                plt.xlabel('Time')
                plt.ylabel('Equity ($)')
                plt.grid(True, alpha=0.3)
                plt.legend()
                
                # Định dạng trục x
                plt.gcf().autofmt_xdate()
                
                # Lưu biểu đồ
                plt.tight_layout()
                plt.savefig(f"micro_test_charts/{filename}_equity.png")
                plt.close()
                
                logger.info(f"Đã lưu biểu đồ equity curve vào micro_test_charts/{filename}_equity.png")
            else:
                logger.warning(f"Không có dữ liệu equity cho {filename}")
                
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ equity curve: {e}")
    
    def _plot_comparison(self, results: Dict, filename: str) -> None:
        """
        Vẽ biểu đồ so sánh các chiến lược
        
        Args:
            results (Dict): Kết quả kiểm thử
            filename (str): Tên file
        """
        try:
            # Tạo biểu đồ
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # Dữ liệu so sánh
            strategies = list(results.keys())
            profit_pcts = [results[s]['profit_loss_percent'] for s in strategies]
            win_rates = [results[s]['win_rate'] * 100 for s in strategies]
            profit_factors = [min(results[s]['profit_factor'], 5) for s in strategies]  # Giới hạn ở 5 để dễ nhìn
            max_drawdowns = [results[s]['max_drawdown'] for s in strategies]
            
            # 1. Biểu đồ lợi nhuận
            bars = axes[0, 0].bar(strategies, profit_pcts)
            
            # Thêm màu cho các thanh
            for i, bar in enumerate(bars):
                if profit_pcts[i] >= 0:
                    bar.set_color('g')
                else:
                    bar.set_color('r')
                    
            axes[0, 0].set_title('Profit/Loss (%)')
            axes[0, 0].set_ylabel('Profit/Loss (%)')
            axes[0, 0].axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            # Thêm giá trị trên các thanh
            for i, v in enumerate(profit_pcts):
                axes[0, 0].text(i, v + (1 if v >= 0 else -3), f"{v:.2f}%", ha='center')
            
            # 2. Biểu đồ win rate
            bars = axes[0, 1].bar(strategies, win_rates)
            axes[0, 1].set_title('Win Rate (%)')
            axes[0, 1].set_ylabel('Win Rate (%)')
            
            # Thêm giá trị trên các thanh
            for i, v in enumerate(win_rates):
                axes[0, 1].text(i, v + 1, f"{v:.1f}%", ha='center')
            
            # 3. Biểu đồ profit factor
            bars = axes[1, 0].bar(strategies, profit_factors)
            axes[1, 0].set_title('Profit Factor (capped at 5)')
            axes[1, 0].set_ylabel('Profit Factor')
            
            # Thêm giá trị trên các thanh
            for i, v in enumerate(profit_factors):
                real_v = results[strategies[i]]['profit_factor']
                if real_v >= 5:
                    display_v = f"{real_v:.2f}"
                else:
                    display_v = f"{real_v:.2f}"
                axes[1, 0].text(i, v + 0.1, display_v, ha='center')
            
            # 4. Biểu đồ drawdown
            bars = axes[1, 1].bar(strategies, max_drawdowns)
            axes[1, 1].set_title('Maximum Drawdown (%)')
            axes[1, 1].set_ylabel('Drawdown (%)')
            
            # Thêm giá trị trên các thanh
            for i, v in enumerate(max_drawdowns):
                axes[1, 1].text(i, v + 0.5, f"{v:.2f}%", ha='center')
            
            # Thêm tiêu đề chung
            symbol = next(iter(results.values()))['symbol']
            plt.suptitle(f"Strategy Comparison for {symbol} with ${self.initial_balance} Initial Balance\n"
                       f"Max Leverage: x{self.max_leverage}, Risk Per Trade: {self.risk_per_trade}%",
                       fontsize=16)
            
            # Định dạng và lưu
            plt.tight_layout(rect=[0, 0, 1, 0.95])
            plt.savefig(f"micro_test_charts/{filename}.png")
            plt.close()
            
            logger.info(f"Đã lưu biểu đồ so sánh vào micro_test_charts/{filename}.png")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ so sánh: {e}")
    
    def _create_summary(self, results: Dict) -> Dict:
        """
        Tạo báo cáo tổng hợp
        
        Args:
            results (Dict): Kết quả kiểm thử
            
        Returns:
            Dict: Báo cáo tổng hợp
        """
        summary = {
            'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'initial_balance': self.initial_balance,
            'max_leverage': self.max_leverage,
            'risk_per_trade': self.risk_per_trade,
            'strategies_tested': list(results.keys()),
            'performance_metrics': {},
            'best_strategy': None,
            'recommendations': []
        }
        
        # Hiệu suất của từng chiến lược
        for strategy, result in results.items():
            summary['performance_metrics'][strategy] = {
                'final_balance': result['final_balance'],
                'profit_loss': result['profit_loss'],
                'profit_loss_percent': result['profit_loss_percent'],
                'total_trades': result['total_trades'],
                'win_rate': result['win_rate'],
                'profit_factor': result['profit_factor'],
                'max_drawdown': result['max_drawdown'],
                'avg_profit': result.get('avg_profit', 0),
                'avg_loss': result.get('avg_loss', 0)
            }
        
        # Tìm chiến lược tốt nhất
        best_strategy = max(results.keys(), key=lambda s: results[s]['profit_loss_percent'])
        summary['best_strategy'] = {
            'name': best_strategy,
            'profit_percent': results[best_strategy]['profit_loss_percent'],
            'win_rate': results[best_strategy]['win_rate'],
            'profit_factor': results[best_strategy]['profit_factor'],
            'max_drawdown': results[best_strategy]['max_drawdown']
        }
        
        # Thêm khuyến nghị
        if summary['best_strategy']['profit_percent'] > 0:
            summary['recommendations'].append(
                f"Chiến lược {best_strategy} cho hiệu suất tốt nhất với lợi nhuận {summary['best_strategy']['profit_percent']:.2f}%")
            
            # Thêm khuyến nghị về drawdown
            if summary['best_strategy']['max_drawdown'] > 50:
                summary['recommendations'].append(
                    "Cảnh báo: Drawdown rất cao. Nên giảm kích thước vị thế hoặc sử dụng đòn bẩy thấp hơn.")
            
            if summary['best_strategy']['win_rate'] < 0.4:
                summary['recommendations'].append(
                    "Cảnh báo: Win rate thấp. Điều này có thể dẫn đến các chuỗi thua lỗ dài.")
        else:
            summary['recommendations'].append(
                "Cảnh báo: Không có chiến lược nào có lợi nhuận dương. Nên điều chỉnh tham số và thử lại.")
        
        return summary

def main():
    """Hàm chính để chạy kiểm thử"""
    # Khởi tạo bộ kiểm thử với vốn 100 USD
    tester = MicroBotTester(
        initial_balance=100.0,
        max_leverage=20,
        risk_per_trade=2.0
    )
    
    # Chạy kiểm thử
    summary = tester.run_all_tests(symbol='BTCUSDT', interval='1h')
    
    # In kết quả tóm tắt
    print("\n===== KẾT QUẢ KIỂM THỬ BOT GIAO DỊCH VỐN NHỎ =====")
    print(f"Vốn ban đầu: ${summary['initial_balance']}")
    print(f"Đòn bẩy tối đa: x{summary['max_leverage']}")
    print(f"Rủi ro mỗi giao dịch: {summary['risk_per_trade']}%")
    print(f"Các chiến lược đã kiểm thử: {', '.join(summary['strategies_tested'])}")
    
    print("\nHiệu suất các chiến lược:")
    for strategy, metrics in summary['performance_metrics'].items():
        print(f"  {strategy}: {metrics['profit_loss_percent']:+.2f}%, Win Rate: {metrics['win_rate']:.2%}, "
             f"Profit Factor: {metrics['profit_factor']:.2f}, Drawdown: {metrics['max_drawdown']:.2f}%")
    
    print(f"\nChiến lược tốt nhất: {summary['best_strategy']['name']}")
    print(f"  Lợi nhuận: {summary['best_strategy']['profit_percent']:+.2f}%")
    print(f"  Win Rate: {summary['best_strategy']['win_rate']:.2%}")
    print(f"  Profit Factor: {summary['best_strategy']['profit_factor']:.2f}")
    print(f"  Drawdown tối đa: {summary['best_strategy']['max_drawdown']:.2f}%")
    
    print("\nKhuyến nghị:")
    for rec in summary['recommendations']:
        print(f"- {rec}")
    
    print("\nĐã lưu kết quả chi tiết và biểu đồ vào thư mục: micro_test_results và micro_test_charts")

if __name__ == "__main__":
    main()