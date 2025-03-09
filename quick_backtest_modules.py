"""
Script backtest nhanh để kiểm tra các module trading

Script này thực hiện backtest nhanh sử dụng dữ liệu Binance thực tế để kiểm tra
các module position_sizing, order_execution, và risk_manager. Mục tiêu chính
là phát hiện lỗi trong môi trường gần với sản phẩm thực tế.
"""

import os
import sys
import json
import logging
import traceback
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backtest_module_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("quick_backtest")

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)

# Mock API client để mô phỏng Binance API
class MockBinanceAPI:
    def __init__(self, load_historical_data=True):
        """
        Mô phỏng Binance API để backtest
        
        Args:
            load_historical_data (bool): Tải dữ liệu lịch sử từ file nếu True
        """
        self.order_id_counter = 1000
        self.open_orders = {}
        self.trade_history = []
        
        # Tải dữ liệu lịch sử
        self.historical_data = {}
        if load_historical_data:
            self._load_historical_data()
    
    def _load_historical_data(self):
        """Tải dữ liệu lịch sử từ file hoặc tạo dữ liệu mẫu nếu không có"""
        try:
            # Thử tải dữ liệu từ file
            if os.path.exists("data/BTCUSDT_1h.csv"):
                df = pd.read_csv("data/BTCUSDT_1h.csv")
                self.historical_data["BTCUSDT"] = df
                logger.info(f"Đã tải dữ liệu BTCUSDT từ file, {len(df)} mẫu")
            else:
                # Tạo dữ liệu mẫu nếu không có file
                logger.info("Không tìm thấy file dữ liệu. Tạo dữ liệu mẫu...")
                self.historical_data["BTCUSDT"] = self._generate_sample_data("BTCUSDT")
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu lịch sử: {e}")
            self.historical_data["BTCUSDT"] = self._generate_sample_data("BTCUSDT")
    
    def _generate_sample_data(self, symbol, days=90, interval='1h'):
        """
        Tạo dữ liệu mẫu cho backtest
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            days (int): Số ngày dữ liệu
            interval (str): Khung thời gian
            
        Returns:
            pd.DataFrame: DataFrame với dữ liệu OHLCV
        """
        logger.info(f"Tạo dữ liệu mẫu {symbol} cho {days} ngày")
        
        # Tham số gốc
        start_price = 40000  # Giá BTC khởi đầu
        volatility = 0.02    # Biến động giá theo phần trăm
        trend = 0.001        # Xu hướng tăng/giảm mỗi kỳ
        volume_base = 1000   # Khối lượng cơ bản
        
        # Tạo chuỗi thời gian
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Tạo các mốc thời gian
        if interval == '1h':
            periods = days * 24
            freq = 'H'
        elif interval == '15m':
            periods = days * 24 * 4
            freq = '15min'
        elif interval == '1d':
            periods = days
            freq = 'D'
        else:
            periods = days * 24
            freq = 'H'
        
        date_range = pd.date_range(start=start_date, end=end_date, periods=periods)
        
        # Tạo giá chuỗi giá
        np.random.seed(42)  # Để tái tạo kết quả
        
        # Tạo chuỗi ngẫu nhiên có tương quan
        returns = np.random.normal(trend, volatility, periods)
        
        # Thêm một số yếu tố thực tế
        # Giai đoạn tăng mạnh
        bull_period_start = int(periods * 0.2)
        bull_period_end = int(periods * 0.4)
        returns[bull_period_start:bull_period_end] += 0.003
        
        # Giai đoạn giảm mạnh
        bear_period_start = int(periods * 0.6)
        bear_period_end = int(periods * 0.7)
        returns[bear_period_start:bear_period_end] -= 0.004
        
        # Chuyển đổi thành giá
        prices = start_price * (1 + np.cumsum(returns))
        
        # Tạo giá OHLC từ close price
        high = prices * (1 + np.random.uniform(0, 0.01, periods))
        low = prices * (1 - np.random.uniform(0, 0.01, periods))
        open_prices = prices * (1 + np.random.uniform(-0.005, 0.005, periods))
        
        # Tạo khối lượng với đặc tính thực tế
        volume = np.random.normal(volume_base, volume_base * 0.2, periods)
        # Khối lượng cao hơn trong giai đoạn biến động
        volume[bull_period_start:bull_period_end] *= 1.5
        volume[bear_period_start:bear_period_end] *= 1.7
        volume = np.abs(volume)
        
        # Tạo DataFrame
        df = pd.DataFrame({
            'timestamp': date_range,
            'open': open_prices,
            'high': high,
            'low': low,
            'close': prices,
            'volume': volume
        })
        
        # Thêm vài chỉ báo cơ bản
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # Tính RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Lưu file
        os.makedirs("data", exist_ok=True)
        df.to_csv(f"data/{symbol}_{interval}.csv", index=False)
        logger.info(f"Đã lưu dữ liệu mẫu vào data/{symbol}_{interval}.csv")
        
        return df
        
    def get_historical_klines(self, symbol, interval, start_str, end_str=None):
        """
        Lấy dữ liệu lịch sử cho backtest
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            interval (str): Khung thời gian ('1h', '15m', '1d',...)
            start_str (str): Thời gian bắt đầu
            end_str (str): Thời gian kết thúc
            
        Returns:
            List[List]: Dữ liệu OHLCV
        """
        if symbol not in self.historical_data:
            self.historical_data[symbol] = self._generate_sample_data(symbol)
            
        df = self.historical_data[symbol].copy()
        
        # Chuyển đổi timestamp thành datetime
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Chuyển đổi start_str và end_str thành datetime
            start_date = pd.to_datetime(start_str)
            
            if end_str:
                end_date = pd.to_datetime(end_str)
            else:
                end_date = pd.to_datetime(datetime.now())
                
            # Lọc dữ liệu theo khoảng thời gian
            df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
            
            # Chuyển đổi thành định dạng Binance API trả về
            result = df.apply(lambda row: [
                int(row['timestamp'].timestamp() * 1000),  # Open time
                str(row['open']),                         # Open
                str(row['high']),                         # High
                str(row['low']),                          # Low
                str(row['close']),                        # Close
                str(row['volume']),                       # Volume
                int(row['timestamp'].timestamp() * 1000 + 3600000),  # Close time
                "0",                                      # Quote asset volume
                0,                                        # Number of trades
                "0",                                      # Taker buy base asset volume
                "0",                                      # Taker buy quote asset volume
                "0"                                       # Ignore
            ], axis=1).tolist()
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu lịch sử: {e}")
            return []
    
    def create_order(self, symbol, side, type, quantity, price=None, **kwargs):
        """Tạo lệnh mới"""
        order_id = str(self.order_id_counter)
        self.order_id_counter += 1
        
        # Giá mặc định cho lệnh market
        current_price = self._get_current_price(symbol)
        if price is None and type.upper() == 'MARKET':
            price = current_price
            
        # Tính phí
        fee = quantity * float(price) * 0.001  # Phí 0.1%
        
        order = {
            'orderId': order_id,
            'symbol': symbol,
            'side': side,
            'type': type,
            'price': price,
            'origQty': str(quantity),
            'executedQty': str(quantity),  # Giả định lệnh được thực thi hoàn toàn
            'status': 'FILLED',
            'timeInForce': kwargs.get('timeInForce', 'GTC'),
            'time': int(datetime.now().timestamp() * 1000),
            'updateTime': int(datetime.now().timestamp() * 1000),
            'fills': [
                {
                    'price': str(price),
                    'qty': str(quantity),
                    'commission': str(fee),
                    'commissionAsset': 'USDT'
                }
            ]
        }
        
        # Thêm vào lịch sử giao dịch
        trade_record = {
            'orderId': order_id,
            'symbol': symbol,
            'side': side,
            'price': price,
            'quantity': quantity,
            'fee': fee,
            'time': datetime.now().isoformat()
        }
        self.trade_history.append(trade_record)
        
        return order
    
    def _get_current_price(self, symbol):
        """Lấy giá hiện tại từ dữ liệu lịch sử"""
        if symbol in self.historical_data:
            return float(self.historical_data[symbol].iloc[-1]['close'])
        return 40000.0  # Giá mặc định
    
    def get_account(self):
        """Lấy thông tin tài khoản"""
        return {
            'balances': [
                {'asset': 'USDT', 'free': '10000.0', 'locked': '0.0'},
                {'asset': 'BTC', 'free': '0.5', 'locked': '0.0'},
                {'asset': 'ETH', 'free': '5.0', 'locked': '0.0'}
            ]
        }

class BacktestDataProcessor:
    """Xử lý dữ liệu cho backtest"""
    
    def __init__(self, binance_api):
        self.binance_api = binance_api
        self.data_cache = {}
    
    def get_historical_data(self, symbol, interval, lookback_days=30, include_indicators=True):
        """
        Lấy dữ liệu lịch sử và thêm các chỉ báo
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            interval (str): Khung thời gian
            lookback_days (int): Số ngày dữ liệu lịch sử
            include_indicators (bool): Thêm các chỉ báo kỹ thuật
            
        Returns:
            pd.DataFrame: DataFrame với dữ liệu OHLCV và chỉ báo
        """
        # Tạo khóa cache
        cache_key = f"{symbol}_{interval}_{lookback_days}"
        
        # Kiểm tra cache
        if cache_key in self.data_cache:
            return self.data_cache[cache_key].copy()
        
        # Tính thời gian bắt đầu
        end_time = datetime.now()
        start_time = end_time - timedelta(days=lookback_days)
        
        # Format thời gian cho API Binance
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Lấy dữ liệu từ API
        try:
            klines = self.binance_api.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_str
            )
            
            if not klines:
                logger.error(f"Không có dữ liệu cho {symbol} từ {start_str} đến {end_str}")
                return pd.DataFrame()
                
            # Chuyển đổi thành DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_base', 'taker_quote', 'ignored'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            if include_indicators:
                # Thêm các chỉ báo kỹ thuật
                df = self._add_indicators(df)
            
            # Lưu vào cache
            self.data_cache[cache_key] = df.copy()
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu lịch sử: {e}")
            return pd.DataFrame()
    
    def _add_indicators(self, df):
        """
        Thêm các chỉ báo kỹ thuật vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLCV
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo
        """
        try:
            # Thêm SMA
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # Thêm EMA
            df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
            
            # RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + 2 * bb_std
            df['bb_lower'] = df['bb_middle'] - 2 * bb_std
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
            
            # Thêm chỉ báo biến động
            df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            
            # Thêm động lượng
            df['momentum'] = df['close'] / df['close'].shift(10) - 1
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi thêm chỉ báo: {e}")
            return df

# Mô phỏng các module cốt lõi cho backtest
# Các lớp này sẽ được sử dụng để mô phỏng các module thực tế

# 1. Module Position Sizing
class BasePositionSizer:
    """Lớp cơ sở cho position sizing"""
    
    def __init__(self, account_balance, max_risk_pct=2.0, leverage=1, min_position_size=0.0):
        self.account_balance = account_balance
        self.max_risk_pct = max_risk_pct
        self.leverage = leverage
        self.min_position_size = min_position_size
        self.name = "Base Position Sizer"
        
    def calculate_position_size(self, entry_price, stop_loss_price, **kwargs):
        """
        Tính toán kích thước vị thế dựa trên quản lý rủi ro
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (Kích thước vị thế, phần trăm rủi ro)
        """
        if entry_price <= 0:
            raise ValueError("Giá vào lệnh phải lớn hơn 0")
            
        if stop_loss_price <= 0:
            raise ValueError("Giá dừng lỗ phải lớn hơn 0")
            
        if entry_price == stop_loss_price:
            raise ValueError("Giá vào lệnh và giá dừng lỗ không được bằng nhau")
            
        # Tính toán phần trăm rủi ro trên mỗi đơn vị
        risk_per_unit = abs(entry_price - stop_loss_price) / entry_price
        
        # Số tiền rủi ro tối đa
        risk_amount = self.account_balance * (self.max_risk_pct / 100)
        
        # Kích thước vị thế
        position_size = risk_amount / (entry_price * risk_per_unit)
        position_size *= self.leverage
        
        return max(self.min_position_size, position_size), self.max_risk_pct
        
    def update_account_balance(self, new_balance):
        """Cập nhật số dư tài khoản"""
        self.account_balance = max(0.0, new_balance)
        
class DynamicPositionSizer(BasePositionSizer):
    """Lớp position sizing động dựa trên biến động và độ tin cậy"""
    
    def __init__(self, account_balance, max_risk_pct=2.0, leverage=1,
               volatility_factor=1.0, confidence_factor=1.0, min_position_size=0.0):
        super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
        self.volatility_factor = volatility_factor
        self.confidence_factor = confidence_factor
        self.name = "Dynamic Position Sizer"
        
    def calculate_position_size(self, entry_price, stop_loss_price, 
                              volatility=None, signal_confidence=None, **kwargs):
        """
        Tính toán kích thước vị thế có điều chỉnh theo biến động và độ tin cậy
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            volatility (float, optional): Độ biến động thị trường (0-1)
            signal_confidence (float, optional): Độ tin cậy của tín hiệu (0-1)
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (Kích thước vị thế, phần trăm rủi ro)
        """
        base_size, base_risk = super().calculate_position_size(entry_price, stop_loss_price)
        
        # Điều chỉnh dựa trên biến động và độ tin cậy
        volatility_multiplier = 1.0
        confidence_multiplier = 1.0
        
        if volatility is not None:
            volatility = max(0.0, min(1.0, volatility))
            volatility_multiplier = 1.0 / (1.0 + volatility * self.volatility_factor)
            
        if signal_confidence is not None:
            signal_confidence = max(0.0, min(1.0, signal_confidence))
            confidence_multiplier = signal_confidence * self.confidence_factor
            
        # Tính kích thước cuối cùng
        adjusted_size = base_size * volatility_multiplier * confidence_multiplier
        
        return max(self.min_position_size, adjusted_size), base_risk
        
class KellyCriterionSizer(BasePositionSizer):
    """Lớp position sizing dựa trên công thức Kelly Criterion"""
    
    def __init__(self, account_balance, win_rate=0.5, avg_win_loss_ratio=1.0, 
               max_risk_pct=5.0, kelly_fraction=1.0, leverage=1, min_position_size=0.0):
        super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
        self.win_rate = win_rate
        self.avg_win_loss_ratio = avg_win_loss_ratio
        self.kelly_fraction = kelly_fraction
        self.name = "Kelly Criterion Sizer"
        
    def calculate_position_size(self, entry_price, stop_loss_price, take_profit_price=None, **kwargs):
        """
        Tính toán kích thước vị thế dựa trên công thức Kelly
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            take_profit_price (float, optional): Giá chốt lời
            **kwargs: Tham số bổ sung
            
        Returns:
            Tuple[float, float]: (Kích thước vị thế, phần trăm rủi ro)
        """
        # Tính toán tỷ lệ thắng/thua dựa trên giá nếu có
        if take_profit_price is not None:
            if entry_price > stop_loss_price:  # Long
                win_amount = take_profit_price - entry_price
                loss_amount = entry_price - stop_loss_price
            else:  # Short
                win_amount = entry_price - take_profit_price
                loss_amount = stop_loss_price - entry_price
                
            current_rr_ratio = win_amount / loss_amount if loss_amount > 0 else self.avg_win_loss_ratio
        else:
            current_rr_ratio = self.avg_win_loss_ratio
            
        # Áp dụng công thức Kelly
        # f* = (p*r - q)/r where p = win rate, q = 1-p, r = win/loss ratio
        kelly_pct = (self.win_rate * current_rr_ratio - (1 - self.win_rate)) / current_rr_ratio
        
        # Áp dụng hệ số Kelly (thường là 0.5 hoặc 0.25 của Kelly đầy đủ)
        kelly_pct = max(0, kelly_pct * self.kelly_fraction)
        
        # Giới hạn theo max_risk_pct
        kelly_pct = min(kelly_pct, self.max_risk_pct / 100)
        
        # Tính kích thước vị thế
        position_value = self.account_balance * kelly_pct
        position_size = position_value / entry_price * self.leverage
        
        return max(self.min_position_size, position_size), kelly_pct * 100

# 2. Module Order Execution
class BaseOrderExecutor:
    """Lớp cơ sở cho thực thi lệnh"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.name = "Base Order Executor"
        
    def execute_order(self, symbol, side, quantity, order_type='MARKET', price=None, 
                    time_in_force='GTC', **kwargs):
        """
        Thực thi lệnh giao dịch
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            side (str): Bên giao dịch (BUY/SELL)
            quantity (float): Số lượng
            order_type (str): Loại lệnh (MARKET/LIMIT/...)
            price (float, optional): Giá đặt lệnh
            time_in_force (str): Hiệu lực thời gian của lệnh
            **kwargs: Tham số bổ sung
            
        Returns:
            Dict: Thông tin lệnh đã thực thi
        """
        try:
            # Kiểm tra đầu vào
            if quantity <= 0:
                logger.error(f"Số lượng không hợp lệ: {quantity}")
                return {"error": "Số lượng không hợp lệ"}
                
            if order_type == 'LIMIT' and (price is None or price <= 0):
                logger.error(f"Giá LIMIT không hợp lệ: {price}")
                return {"error": "Giá LIMIT không hợp lệ"}
                
            # Tạo tham số lệnh
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'timeInForce': time_in_force if order_type != 'MARKET' else None
            }
            
            if order_type != 'MARKET' and price is not None:
                order_params['price'] = price
                
            # Thêm các tham số khác
            for key, value in kwargs.items():
                order_params[key] = value
                
            # Loại bỏ tham số None
            order_params = {k: v for k, v in order_params.items() if v is not None}
            
            # Thực thi lệnh
            response = self.api_client.create_order(**order_params)
            logger.info(f"Lệnh thực thi: {symbol} {side} {quantity} giá {price or 'MARKET'}")
            return response
            
        except Exception as e:
            logger.error(f"Lỗi khi thực thi lệnh: {e}")
            return {"error": str(e)}
            
    def calculate_average_fill_price(self, order_response):
        """
        Tính giá trung bình thực hiện lệnh
        
        Args:
            order_response (Dict): Thông tin lệnh
            
        Returns:
            float: Giá trung bình
        """
        if 'fills' not in order_response:
            if 'price' in order_response:
                return float(order_response['price'])
            return 0.0
            
        fills = order_response['fills']
        if not fills:
            return 0.0
            
        total_qty = 0.0
        total_cost = 0.0
        
        for fill in fills:
            qty = float(fill['qty'])
            price = float(fill['price'])
            total_qty += qty
            total_cost += qty * price
            
        if total_qty == 0:
            return 0.0
            
        return total_cost / total_qty
        
class IcebergOrderExecutor(BaseOrderExecutor):
    """Lớp thực thi lệnh iceberg (chia lệnh lớn thành nhiều lệnh nhỏ)"""
    
    def __init__(self, api_client):
        super().__init__(api_client)
        self.name = "Iceberg Order Executor"
        
    def execute_iceberg_order(self, symbol, side, total_quantity, num_parts=5, price=None, 
                            order_type='MARKET', random_variance=0.1, time_between_parts=30.0, **kwargs):
        """
        Thực thi lệnh iceberg (chia thành nhiều phần)
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            side (str): Bên giao dịch (BUY/SELL)
            total_quantity (float): Tổng số lượng
            num_parts (int): Số lượng phần chia
            price (float, optional): Giá đặt lệnh
            order_type (str): Loại lệnh (MARKET/LIMIT/...)
            random_variance (float): Biến động ngẫu nhiên cho kích thước mỗi phần (0-1)
            time_between_parts (float): Thời gian giữa các phần (giây)
            **kwargs: Tham số bổ sung
            
        Returns:
            List[Dict]: Danh sách các lệnh đã thực thi
        """
        if total_quantity <= 0 or num_parts <= 0:
            logger.error(f"Tham số không hợp lệ")
            return []
            
        # Kích thước cơ bản mỗi phần
        base_quantity = total_quantity / num_parts
        results = []
        remaining_quantity = total_quantity
        
        for i in range(num_parts):
            is_last_part = (i == num_parts - 1)
            
            if is_last_part:
                # Phần cuối cùng sẽ lấy toàn bộ số lượng còn lại
                part_quantity = remaining_quantity
            else:
                # Các phần khác sẽ có biến động ngẫu nhiên nếu có
                if random_variance > 0:
                    variance = np.random.uniform(-random_variance, random_variance)
                    variance_factor = 1.0 + variance
                else:
                    variance_factor = 1.0
                    
                part_quantity = min(base_quantity * variance_factor, remaining_quantity)
            
            # Đảm bảo số lượng hợp lệ
            part_quantity = max(0.000001, part_quantity)
            
            # Thực thi phần lệnh
            order_result = self.execute_order(
                symbol=symbol,
                side=side,
                quantity=part_quantity,
                order_type=order_type,
                price=price,
                **kwargs
            )
            
            results.append(order_result)
            
            # Cập nhật số lượng còn lại
            if 'executedQty' in order_result:
                executed_qty = float(order_result['executedQty'])
            else:
                executed_qty = part_quantity
                
            remaining_quantity -= executed_qty
            
            # Kiểm tra nếu đã hết số lượng
            if remaining_quantity <= 0 or is_last_part:
                break
                
            # Đợi giữa các phần
            if time_between_parts > 0 and i < num_parts - 1:
                # Sử dụng module time đã import
                time.sleep(time_between_parts)
                
        return results
        
    def calculate_average_fill_price(self, order_response):
        """
        Tính giá trung bình thực hiện cho nhiều lệnh
        
        Args:
            order_response (List[Dict]): Danh sách các lệnh
            
        Returns:
            float: Giá trung bình
        """
        if not order_response:
            return 0.0
            
        # Xử lý trường hợp nếu order_response là một object đơn lẻ
        if isinstance(order_response, dict):
            # Nếu order_response là một dict không phải list, chuyển nó thành list để xử lý
            orders = [order_response]
        else:
            # Nếu đã là list thì giữ nguyên
            orders = order_response
            
        total_qty = 0.0
        total_cost = 0.0
        
        for order in orders:
            if 'fills' in order and order['fills']:
                for fill in order['fills']:
                    qty = float(fill['qty'])
                    price = float(fill['price'])
                    total_qty += qty
                    total_cost += qty * price
            
            elif 'executedQty' in order and 'price' in order and float(order['executedQty']) > 0:
                qty = float(order['executedQty'])
                price = float(order['price'])
                total_qty += qty
                total_cost += qty * price
                
        if total_qty == 0:
            return 0.0
            
        return total_cost / total_qty

# 3. Module Risk Management
class RiskManager:
    """Lớp quản lý rủi ro cơ bản"""
    
    def __init__(self, account_balance, max_risk_per_trade=2.0, max_daily_risk=5.0,
               max_weekly_risk=10.0, max_open_trades=5):
        self.account_balance = account_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_risk = max_daily_risk
        self.max_weekly_risk = max_weekly_risk
        self.max_open_trades = max_open_trades
        
        self.daily_risk_used = 0.0
        self.weekly_risk_used = 0.0
        self.active_trades = {}
        self.closed_trades = []
        self.name = "Base Risk Manager"
        
    def check_trade_risk(self, symbol, risk_amount, entry_price, stop_loss_price, **kwargs):
        """
        Kiểm tra rủi ro của một giao dịch mới
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            risk_amount (float): Số tiền rủi ro
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            **kwargs: Tham số bổ sung
            
        Returns:
            Dict: Kết quả kiểm tra rủi ro
        """
        risk_percentage = (risk_amount / self.account_balance) * 100
        
        # Kiểm tra giới hạn rủi ro mỗi giao dịch
        if risk_percentage > self.max_risk_per_trade:
            return {
                'allowed': False,
                'reason': f'Vượt quá rủi ro tối đa mỗi giao dịch ({risk_percentage:.2f}% > {self.max_risk_per_trade:.2f}%)'
            }
            
        # Kiểm tra giới hạn rủi ro hàng ngày
        if self.daily_risk_used + risk_percentage > self.max_daily_risk:
            return {
                'allowed': False,
                'reason': f'Vượt quá rủi ro tối đa hàng ngày ({self.daily_risk_used + risk_percentage:.2f}% > {self.max_daily_risk:.2f}%)'
            }
            
        # Kiểm tra giới hạn rủi ro hàng tuần
        if self.weekly_risk_used + risk_percentage > self.max_weekly_risk:
            return {
                'allowed': False,
                'reason': f'Vượt quá rủi ro tối đa hàng tuần ({self.weekly_risk_used + risk_percentage:.2f}% > {self.max_weekly_risk:.2f}%)'
            }
            
        # Kiểm tra số lượng giao dịch mở
        if len(self.active_trades) >= self.max_open_trades:
            return {
                'allowed': False,
                'reason': f'Vượt quá số giao dịch mở tối đa ({len(self.active_trades)} >= {self.max_open_trades})'
            }
            
        return {
            'allowed': True,
            'reason': 'Giao dịch đáp ứng yêu cầu rủi ro'
        }
        
    def register_trade(self, trade_info):
        """
        Đăng ký một giao dịch mới
        
        Args:
            trade_info (Dict): Thông tin giao dịch
            
        Returns:
            str: ID của giao dịch
        """
        trade_id = trade_info.get('trade_id') or f"trade_{int(time.time())}"
        trade_info['timestamp'] = datetime.now()
        
        self.active_trades[trade_id] = trade_info
        self.daily_risk_used += trade_info.get('risk_percentage', 0)
        self.weekly_risk_used += trade_info.get('risk_percentage', 0)
        
        logger.info(f"Đăng ký giao dịch {trade_id}: {trade_info.get('symbol')} {trade_info.get('side')}")
        return trade_id
        
    def close_trade(self, trade_id, exit_price, pnl, exit_reason=None, timestamp=None):
        """
        Đóng một giao dịch
        
        Args:
            trade_id (str): ID của giao dịch
            exit_price (float): Giá thoát lệnh
            pnl (float): Lãi/lỗ của giao dịch
            exit_reason (str, optional): Lý do thoát lệnh
            timestamp (datetime, optional): Thời gian thoát lệnh
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if trade_id not in self.active_trades:
            logger.warning(f"Giao dịch {trade_id} không tồn tại")
            return False
            
        trade = self.active_trades[trade_id].copy()
        trade['exit_price'] = exit_price
        trade['pnl'] = pnl
        trade['exit_time'] = timestamp or datetime.now()
        trade['exit_reason'] = exit_reason or "unknown"
        
        # Đánh dấu thắng/thua
        trade['result'] = 'win' if pnl > 0 else 'loss'
        
        # Thêm vào lịch sử giao dịch
        self.closed_trades.append(trade)
        
        # Xóa khỏi giao dịch đang mở
        del self.active_trades[trade_id]
        
        # Cập nhật số dư tài khoản và rủi ro
        self.account_balance += pnl
        
        logger.info(f"Đóng giao dịch {trade_id} với P&L: {pnl:.2f}")
        return True
        
    def get_active_trades(self):
        """Lấy danh sách các giao dịch đang mở"""
        return self.active_trades
        
    def get_closed_trades(self, limit=None):
        """Lấy danh sách các giao dịch đã đóng"""
        if limit:
            return self.closed_trades[-limit:]
        return self.closed_trades
        
    def get_performance_metrics(self):
        """
        Tính toán các chỉ số hiệu suất giao dịch
        
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        if not self.closed_trades:
            return {
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'avg_trade': 0,
                'total_trades': 0,
                'total_pnl': 0,
                'current_balance': self.account_balance
            }
            
        # Tổng số giao dịch
        total_trades = len(self.closed_trades)
        
        # Số giao dịch thắng
        winning_trades = [t for t in self.closed_trades if t.get('result') == 'win']
        losing_trades = [t for t in self.closed_trades if t.get('result') == 'loss']
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        # Win rate
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # Tổng lợi nhuận
        total_profit = sum(t.get('pnl', 0) for t in winning_trades)
        total_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
        total_pnl = total_profit - total_loss
        
        # Profit factor
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Thắng/thua trung bình
        avg_win = total_profit / win_count if win_count > 0 else 0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0
        avg_trade = total_pnl / total_trades if total_trades > 0 else 0
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_trade': avg_trade,
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'current_balance': self.account_balance
        }

# Lớp backtest tích hợp các module
class ModuleBacktester:
    """Backtest các module riêng lẻ và tích hợp"""
    
    def __init__(self, binance_api=None, initial_balance=10000.0, test_name=None):
        """
        Khởi tạo backtester
        
        Args:
            binance_api (Any, optional): API client Binance
            initial_balance (float): Số dư ban đầu
            test_name (str, optional): Tên backtest
        """
        self.binance_api = binance_api or MockBinanceAPI()
        self.data_processor = BacktestDataProcessor(self.binance_api)
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.start_time = datetime.now()
        self.test_name = test_name or f"Backtest_{self.start_time.strftime('%Y%m%d_%H%M%S')}"
        
        # Danh sách các module có thể sử dụng
        self.position_sizers = [
            BasePositionSizer(initial_balance),
            DynamicPositionSizer(initial_balance),
            KellyCriterionSizer(initial_balance, win_rate=0.6, avg_win_loss_ratio=2.0)
        ]
        
        self.order_executors = [
            BaseOrderExecutor(self.binance_api),
            IcebergOrderExecutor(self.binance_api)
        ]
        
        self.risk_manager = RiskManager(initial_balance)
        
        # Lưu lịch sử backtest
        self.trades = []
        self.equity_curve = []
        self.metrics = {}
        
    def backtest_position_sizing(self, symbol='BTCUSDT', interval='1h', days=30):
        """
        Backtest module position sizing
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            interval (str): Khung thời gian
            days (int): Số ngày dữ liệu
            
        Returns:
            Dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest position sizing cho {symbol} trên khung {interval}")
        
        # Lấy dữ liệu lịch sử
        df = self.data_processor.get_historical_data(
            symbol=symbol, 
            interval=interval, 
            lookback_days=days
        )
        
        if df.empty:
            logger.error("Không thể lấy dữ liệu lịch sử")
            return {"error": "Không thể lấy dữ liệu lịch sử"}
            
        # Thông số test
        test_scenarios = [
            # Format: entry_price, stop_loss_price, take_profit_price, volatility, signal_confidence
            (40000, 39000, 42000, 0.1, 0.9),  # Biến động thấp, tin cậy cao
            (40000, 39000, 42000, 0.5, 0.5),  # Biến động trung bình, tin cậy trung bình
            (40000, 39000, 42000, 0.8, 0.3),  # Biến động cao, tin cậy thấp
        ]
        
        results = []
        
        for sizer in self.position_sizers:
            sizer_results = []
            
            for i, (entry, stop, take, vol, conf) in enumerate(test_scenarios):
                try:
                    size, risk = sizer.calculate_position_size(
                        entry_price=entry,
                        stop_loss_price=stop,
                        take_profit_price=take,
                        volatility=vol,
                        signal_confidence=conf
                    )
                    
                    risk_amount = self.initial_balance * (risk / 100)
                    max_loss = size * abs(entry - stop)
                    
                    sizer_results.append({
                        'scenario': i + 1,
                        'entry_price': entry,
                        'stop_loss': stop,
                        'take_profit': take,
                        'volatility': vol,
                        'confidence': conf,
                        'position_size': size,
                        'risk_percentage': risk,
                        'risk_amount': risk_amount,
                        'max_loss': max_loss
                    })
                    
                except Exception as e:
                    logger.error(f"Lỗi với {sizer.name} ở scenario {i+1}: {e}")
                    sizer_results.append({
                        'scenario': i + 1,
                        'error': str(e)
                    })
                    
            results.append({
                'sizer_name': sizer.name,
                'scenarios': sizer_results
            })
            
        # Lưu kết quả
        output_file = f"backtest_results/position_sizing_{symbol}_{interval}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
            
        logger.info(f"Kết quả backtest position sizing lưu tại {output_file}")
        
        return {
            'status': 'success',
            'results': results,
            'output_file': output_file
        }
        
    def backtest_order_execution(self, symbol='BTCUSDT', interval='1h', days=30):
        """
        Backtest module order execution
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            interval (str): Khung thời gian
            days (int): Số ngày dữ liệu
            
        Returns:
            Dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest order execution cho {symbol} trên khung {interval}")
        
        # Lấy dữ liệu lịch sử
        df = self.data_processor.get_historical_data(
            symbol=symbol, 
            interval=interval, 
            lookback_days=days
        )
        
        if df.empty:
            logger.error("Không thể lấy dữ liệu lịch sử")
            return {"error": "Không thể lấy dữ liệu lịch sử"}
            
        # Thông số test
        test_orders = [
            # Format: side, total_quantity, num_parts, order_type, price
            ('BUY', 0.1, 1, 'MARKET', None),  # Market order đơn giản
            ('BUY', 0.5, 5, 'LIMIT', 40000),  # Limit order chia 5 phần
            ('SELL', 0.2, 2, 'MARKET', None), # Sell market order chia 2 phần
            ('SELL', 0.3, 3, 'LIMIT', 42000), # Sell limit order chia 3 phần
        ]
        
        results = []
        
        for executor in self.order_executors:
            executor_results = []
            
            for i, (side, qty, parts, order_type, price) in enumerate(test_orders):
                try:
                    # Với Base Executor chỉ thực hiện đơn giản
                    if executor.name == "Base Order Executor":
                        response = executor.execute_order(
                            symbol=symbol,
                            side=side,
                            quantity=qty,
                            order_type=order_type,
                            price=price
                        )
                        
                        fill_price = executor.calculate_average_fill_price(response)
                        
                        executor_results.append({
                            'order_id': i + 1,
                            'response': response,
                            'average_price': fill_price,
                            'parts': 1
                        })
                        
                    # Với Iceberg Executor thực hiện chia nhỏ
                    elif executor.name == "Iceberg Order Executor":
                        responses = executor.execute_iceberg_order(
                            symbol=symbol,
                            side=side,
                            total_quantity=qty,
                            num_parts=parts,
                            order_type=order_type,
                            price=price,
                            random_variance=0.1,
                            time_between_parts=0  # Không chờ trong backtest
                        )
                        
                        fill_price = executor.calculate_average_fill_price(responses)
                        
                        executor_results.append({
                            'order_id': i + 1,
                            'num_parts': len(responses),
                            'average_price': fill_price,
                            'parts': parts,
                            'total_quantity': qty
                        })
                        
                except Exception as e:
                    logger.error(f"Lỗi với {executor.name} ở order {i+1}: {e}")
                    executor_results.append({
                        'order_id': i + 1,
                        'error': str(e)
                    })
                    
            results.append({
                'executor_name': executor.name,
                'orders': executor_results
            })
            
        # Lưu kết quả
        output_file = f"backtest_results/order_execution_{symbol}_{interval}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
            
        logger.info(f"Kết quả backtest order execution lưu tại {output_file}")
        
        return {
            'status': 'success',
            'results': results,
            'output_file': output_file
        }
        
    def backtest_risk_management(self, symbol='BTCUSDT', interval='1h', days=30):
        """
        Backtest module risk management
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            interval (str): Khung thời gian
            days (int): Số ngày dữ liệu
            
        Returns:
            Dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest risk management cho {symbol} trên khung {interval}")
        
        # Lấy dữ liệu lịch sử
        df = self.data_processor.get_historical_data(
            symbol=symbol, 
            interval=interval, 
            lookback_days=days
        )
        
        if df.empty:
            logger.error("Không thể lấy dữ liệu lịch sử")
            return {"error": "Không thể lấy dữ liệu lịch sử"}
            
        # Reset risk manager
        self.risk_manager = RiskManager(self.initial_balance)
        
        # Danh sách các giao dịch test
        test_trades = [
            # [symbol, side, entry_price, stop_loss, take_profit, quantity, risk_pct]
            [symbol, 'LONG', 40000, 39000, 42000, 0.1, 2.0],  # Trong giới hạn rủi ro
            [symbol, 'LONG', 40000, 39000, 42000, 0.5, 5.0],  # Ngoài giới hạn rủi ro 
            [symbol, 'SHORT', 42000, 43000, 40000, 0.2, 2.5], # Trong giới hạn rủi ro
            [symbol, 'SHORT', 42000, 43000, 40000, 1.0, 6.0], # Ngoài giới hạn rủi ro
        ]
        
        results = []
        active_trade_ids = []
        
        # 1. Kiểm tra quản lý rủi ro
        for i, trade in enumerate(test_trades):
            symbol, side, entry, stop, take, qty, risk_pct = trade
            
            risk_amount = self.initial_balance * (risk_pct / 100)
            
            # Kiểm tra rủi ro
            check_result = self.risk_manager.check_trade_risk(
                symbol=symbol,
                risk_amount=risk_amount,
                entry_price=entry,
                stop_loss_price=stop
            )
            
            # Khởi tạo trade_id với None
            trade_id = None
            
            # Tạo giao dịch nếu được chấp nhận
            if check_result['allowed']:
                trade_info = {
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry,
                    'stop_loss_price': stop,
                    'take_profit_price': take,
                    'quantity': qty,
                    'risk_amount': risk_amount,
                    'risk_percentage': risk_pct
                }
                
                trade_id = self.risk_manager.register_trade(trade_info)
                active_trade_ids.append(trade_id)
            
            results.append({
                'trade_id': i + 1,
                'trade_info': {
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry,
                    'stop_loss_price': stop,
                    'take_profit_price': take,
                    'quantity': qty,
                    'risk_pct': risk_pct
                },
                'risk_check': check_result,
                'accepted': check_result['allowed'],
                'registered_id': trade_id
            })
            
        # 2. Đóng một số giao dịch đã mở
        closed_results = []
        
        for i, trade_id in enumerate(active_trade_ids):
            # Lấy thông tin giao dịch
            trade = self.risk_manager.active_trades.get(trade_id)
            
            if not trade:
                continue
                
            # Mô phỏng lãi/lỗ
            if i % 2 == 0:  # Giao dịch chẵn thắng
                if trade['side'] == 'LONG':
                    exit_price = trade['take_profit_price']
                    pnl = trade['quantity'] * (exit_price - trade['entry_price'])
                else:
                    exit_price = trade['take_profit_price']
                    pnl = trade['quantity'] * (trade['entry_price'] - exit_price)
                exit_reason = "take_profit"
            else:  # Giao dịch lẻ thua
                if trade['side'] == 'LONG':
                    exit_price = trade['stop_loss_price']
                    pnl = trade['quantity'] * (exit_price - trade['entry_price'])
                else:
                    exit_price = trade['stop_loss_price']
                    pnl = trade['quantity'] * (trade['entry_price'] - exit_price)
                exit_reason = "stop_loss"
                
            # Đóng giao dịch
            close_result = self.risk_manager.close_trade(
                trade_id=trade_id,
                exit_price=exit_price,
                pnl=pnl,
                exit_reason=exit_reason
            )
            
            closed_results.append({
                'trade_id': trade_id,
                'exit_price': exit_price,
                'pnl': pnl,
                'exit_reason': exit_reason,
                'close_success': close_result
            })
            
        # 3. Lấy các chỉ số hiệu suất
        performance = self.risk_manager.get_performance_metrics()
        
        # Lưu kết quả tổng hợp
        final_results = {
            'risk_checks': results,
            'closed_trades': closed_results,
            'active_trades': list(self.risk_manager.active_trades.values()),
            'performance': performance
        }
        
        # Lưu kết quả
        output_file = f"backtest_results/risk_management_{symbol}_{interval}.json"
        with open(output_file, 'w') as f:
            json.dump(final_results, f, indent=4)
            
        logger.info(f"Kết quả backtest risk management lưu tại {output_file}")
        
        return {
            'status': 'success',
            'results': final_results,
            'output_file': output_file
        }
        
    def backtest_integrated_modules(self, symbol='BTCUSDT', interval='1h', days=30, strategy='simple_ma_cross'):
        """
        Backtest tích hợp các module với chiến lược đơn giản
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            interval (str): Khung thời gian
            days (int): Số ngày dữ liệu
            strategy (str): Chiến lược sử dụng
            
        Returns:
            Dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest tích hợp cho {symbol} trên khung {interval} với chiến lược {strategy}")
        
        # Lấy dữ liệu lịch sử
        df = self.data_processor.get_historical_data(
            symbol=symbol, 
            interval=interval, 
            lookback_days=days
        )
        
        if df.empty:
            logger.error("Không thể lấy dữ liệu lịch sử")
            return {"error": "Không thể lấy dữ liệu lịch sử"}
            
        # Chuẩn bị các module
        position_sizer = self.position_sizers[1]  # Sử dụng DynamicPositionSizer
        order_executor = self.order_executors[1]  # Sử dụng IcebergOrderExecutor
        risk_manager = RiskManager(self.initial_balance)
        
        # Chuẩn bị khởi tạo
        trades = []
        equity_curve = [self.initial_balance]
        current_position = None
        balance = self.initial_balance
        
        # Thực hiện giao dịch theo chiến lược
        for i in range(20, len(df)):
            current_time = df.iloc[i]['timestamp']
            price = df.iloc[i]['close']
            
            # Cập nhật đường equity
            if current_position:
                # Cập nhật giá trị vị thế
                if current_position['side'] == 'LONG':
                    unrealized_pnl = current_position['quantity'] * (price - current_position['entry_price'])
                else:
                    unrealized_pnl = current_position['quantity'] * (current_position['entry_price'] - price)
                current_equity = balance + unrealized_pnl
            else:
                current_equity = balance
                
            equity_curve.append(current_equity)
            
            # Kiểm tra tín hiệu vào lệnh
            if strategy == 'simple_ma_cross':
                # MA Cross Strategy: Long khi MA ngắn cắt lên MA dài, Short khi ngược lại
                sma20 = df.iloc[i]['sma_20']
                sma50 = df.iloc[i]['sma_50']
                prev_sma20 = df.iloc[i-1]['sma_20']
                prev_sma50 = df.iloc[i-1]['sma_50']
                
                # Tín hiệu Long (sma20 cắt lên sma50)
                long_signal = prev_sma20 < prev_sma50 and sma20 > sma50
                
                # Tín hiệu Short (sma20 cắt xuống sma50)
                short_signal = prev_sma20 > prev_sma50 and sma20 < sma50
                
                # Nếu đang có vị thế, kiểm tra đóng
                if current_position:
                    # Đóng Long khi có tín hiệu Short
                    if current_position['side'] == 'LONG' and short_signal:
                        # Tính PnL
                        pnl = current_position['quantity'] * (price - current_position['entry_price'])
                        
                        # Đóng vị thế
                        risk_manager.close_trade(
                            trade_id=current_position['trade_id'],
                            exit_price=price,
                            pnl=pnl,
                            exit_reason="signal_reversal"
                        )
                        
                        # Cập nhật balance
                        balance += pnl
                        position_sizer.update_account_balance(balance)
                        
                        # Lưu giao dịch
                        trades.append({
                            'entry_time': current_position['entry_time'],
                            'exit_time': current_time,
                            'symbol': symbol,
                            'side': current_position['side'],
                            'entry_price': current_position['entry_price'],
                            'exit_price': price,
                            'quantity': current_position['quantity'],
                            'pnl': pnl,
                            'exit_reason': "signal_reversal"
                        })
                        
                        current_position = None
                        
                    # Đóng Short khi có tín hiệu Long
                    elif current_position['side'] == 'SHORT' and long_signal:
                        # Tính PnL
                        pnl = current_position['quantity'] * (current_position['entry_price'] - price)
                        
                        # Đóng vị thế
                        risk_manager.close_trade(
                            trade_id=current_position['trade_id'],
                            exit_price=price,
                            pnl=pnl,
                            exit_reason="signal_reversal"
                        )
                        
                        # Cập nhật balance
                        balance += pnl
                        position_sizer.update_account_balance(balance)
                        
                        # Lưu giao dịch
                        trades.append({
                            'entry_time': current_position['entry_time'],
                            'exit_time': current_time,
                            'symbol': symbol,
                            'side': current_position['side'],
                            'entry_price': current_position['entry_price'],
                            'exit_price': price,
                            'quantity': current_position['quantity'],
                            'pnl': pnl,
                            'exit_reason': "signal_reversal"
                        })
                        
                        current_position = None
                
                # Chưa có vị thế, kiểm tra vào lệnh mới
                elif not current_position:
                    # Vào Long khi có tín hiệu Long
                    if long_signal:
                        # Tính stop loss và take profit
                        atr = df.iloc[i]['atr']
                        stop_loss = price - 2 * atr
                        take_profit = price + 3 * atr  # Risk:Reward = 1:1.5
                        
                        # Tính kích thước vị thế
                        volatility = df.iloc[i]['volatility']
                        rsi = df.iloc[i]['rsi']
                        signal_confidence = 0.7 if abs(sma20 - sma50) > atr else 0.5
                        
                        size, risk_pct = position_sizer.calculate_position_size(
                            entry_price=price,
                            stop_loss_price=stop_loss,
                            take_profit_price=take_profit,
                            volatility=volatility,
                            signal_confidence=signal_confidence
                        )
                        
                        # Kiểm tra rủi ro
                        risk_amount = balance * (risk_pct / 100)
                        check = risk_manager.check_trade_risk(
                            symbol=symbol,
                            risk_amount=risk_amount,
                            entry_price=price,
                            stop_loss_price=stop_loss
                        )
                        
                        if check['allowed']:
                            # Thực thi lệnh (2 phần để giảm ảnh hưởng giá)
                            try:
                                order_responses = order_executor.execute_iceberg_order(
                                    symbol=symbol,
                                    side='BUY',
                                    total_quantity=size,
                                    num_parts=2,
                                    price=price,  # Sử dụng limit để mô phỏng chính xác hơn
                                    time_between_parts=0  # Không chờ trong backtest
                                )
                                
                                avg_price = order_executor.calculate_average_fill_price(order_responses)
                                
                                # Đăng ký giao dịch
                                trade_info = {
                                    'symbol': symbol,
                                    'side': 'LONG',
                                    'entry_price': avg_price or price,
                                    'stop_loss_price': stop_loss,
                                    'take_profit_price': take_profit,
                                    'quantity': size,
                                    'risk_amount': risk_amount,
                                    'risk_percentage': risk_pct,
                                    'entry_time': current_time
                                }
                                
                                trade_id = risk_manager.register_trade(trade_info)
                                trade_info['trade_id'] = trade_id
                                
                                # Lưu vị thế hiện tại
                                current_position = trade_info
                                
                            except Exception as e:
                                logger.error(f"Lỗi khi vào lệnh Long: {e}")
                    
                    # Vào Short khi có tín hiệu Short
                    elif short_signal:
                        # Tính stop loss và take profit
                        atr = df.iloc[i]['atr']
                        stop_loss = price + 2 * atr
                        take_profit = price - 3 * atr  # Risk:Reward = 1:1.5
                        
                        # Tính kích thước vị thế
                        volatility = df.iloc[i]['volatility']
                        rsi = df.iloc[i]['rsi']
                        signal_confidence = 0.7 if abs(sma20 - sma50) > atr else 0.5
                        
                        size, risk_pct = position_sizer.calculate_position_size(
                            entry_price=price,
                            stop_loss_price=stop_loss,
                            take_profit_price=take_profit,
                            volatility=volatility,
                            signal_confidence=signal_confidence
                        )
                        
                        # Kiểm tra rủi ro
                        risk_amount = balance * (risk_pct / 100)
                        check = risk_manager.check_trade_risk(
                            symbol=symbol,
                            risk_amount=risk_amount,
                            entry_price=price,
                            stop_loss_price=stop_loss
                        )
                        
                        if check['allowed']:
                            # Thực thi lệnh (2 phần để giảm ảnh hưởng giá)
                            try:
                                order_responses = order_executor.execute_iceberg_order(
                                    symbol=symbol,
                                    side='SELL',
                                    total_quantity=size,
                                    num_parts=2,
                                    price=price,  # Sử dụng limit để mô phỏng chính xác hơn
                                    time_between_parts=0  # Không chờ trong backtest
                                )
                                
                                avg_price = order_executor.calculate_average_fill_price(order_responses)
                                
                                # Đăng ký giao dịch
                                trade_info = {
                                    'symbol': symbol,
                                    'side': 'SHORT',
                                    'entry_price': avg_price or price,
                                    'stop_loss_price': stop_loss,
                                    'take_profit_price': take_profit,
                                    'quantity': size,
                                    'risk_amount': risk_amount,
                                    'risk_percentage': risk_pct,
                                    'entry_time': current_time
                                }
                                
                                trade_id = risk_manager.register_trade(trade_info)
                                trade_info['trade_id'] = trade_id
                                
                                # Lưu vị thế hiện tại
                                current_position = trade_info
                                
                            except Exception as e:
                                logger.error(f"Lỗi khi vào lệnh Short: {e}")
            
            # Kiểm tra stop loss/take profit nếu đang có vị thế
            if current_position:
                if current_position['side'] == 'LONG':
                    # Kiểm tra stop loss
                    if price <= current_position['stop_loss_price']:
                        # Tính PnL
                        pnl = current_position['quantity'] * (current_position['stop_loss_price'] - current_position['entry_price'])
                        
                        # Đóng vị thế
                        risk_manager.close_trade(
                            trade_id=current_position['trade_id'],
                            exit_price=current_position['stop_loss_price'],
                            pnl=pnl,
                            exit_reason="stop_loss"
                        )
                        
                        # Cập nhật balance
                        balance += pnl
                        position_sizer.update_account_balance(balance)
                        
                        # Lưu giao dịch
                        trades.append({
                            'entry_time': current_position['entry_time'],
                            'exit_time': current_time,
                            'symbol': symbol,
                            'side': current_position['side'],
                            'entry_price': current_position['entry_price'],
                            'exit_price': current_position['stop_loss_price'],
                            'quantity': current_position['quantity'],
                            'pnl': pnl,
                            'exit_reason': "stop_loss"
                        })
                        
                        current_position = None
                        
                    # Kiểm tra take profit
                    elif price >= current_position['take_profit_price']:
                        # Tính PnL
                        pnl = current_position['quantity'] * (current_position['take_profit_price'] - current_position['entry_price'])
                        
                        # Đóng vị thế
                        risk_manager.close_trade(
                            trade_id=current_position['trade_id'],
                            exit_price=current_position['take_profit_price'],
                            pnl=pnl,
                            exit_reason="take_profit"
                        )
                        
                        # Cập nhật balance
                        balance += pnl
                        position_sizer.update_account_balance(balance)
                        
                        # Lưu giao dịch
                        trades.append({
                            'entry_time': current_position['entry_time'],
                            'exit_time': current_time,
                            'symbol': symbol,
                            'side': current_position['side'],
                            'entry_price': current_position['entry_price'],
                            'exit_price': current_position['take_profit_price'],
                            'quantity': current_position['quantity'],
                            'pnl': pnl,
                            'exit_reason': "take_profit"
                        })
                        
                        current_position = None
                
                elif current_position['side'] == 'SHORT':
                    # Kiểm tra stop loss
                    if price >= current_position['stop_loss_price']:
                        # Tính PnL
                        pnl = current_position['quantity'] * (current_position['entry_price'] - current_position['stop_loss_price'])
                        
                        # Đóng vị thế
                        risk_manager.close_trade(
                            trade_id=current_position['trade_id'],
                            exit_price=current_position['stop_loss_price'],
                            pnl=pnl,
                            exit_reason="stop_loss"
                        )
                        
                        # Cập nhật balance
                        balance += pnl
                        position_sizer.update_account_balance(balance)
                        
                        # Lưu giao dịch
                        trades.append({
                            'entry_time': current_position['entry_time'],
                            'exit_time': current_time,
                            'symbol': symbol,
                            'side': current_position['side'],
                            'entry_price': current_position['entry_price'],
                            'exit_price': current_position['stop_loss_price'],
                            'quantity': current_position['quantity'],
                            'pnl': pnl,
                            'exit_reason': "stop_loss"
                        })
                        
                        current_position = None
                        
                    # Kiểm tra take profit
                    elif price <= current_position['take_profit_price']:
                        # Tính PnL
                        pnl = current_position['quantity'] * (current_position['entry_price'] - current_position['take_profit_price'])
                        
                        # Đóng vị thế
                        risk_manager.close_trade(
                            trade_id=current_position['trade_id'],
                            exit_price=current_position['take_profit_price'],
                            pnl=pnl,
                            exit_reason="take_profit"
                        )
                        
                        # Cập nhật balance
                        balance += pnl
                        position_sizer.update_account_balance(balance)
                        
                        # Lưu giao dịch
                        trades.append({
                            'entry_time': current_position['entry_time'],
                            'exit_time': current_time,
                            'symbol': symbol,
                            'side': current_position['side'],
                            'entry_price': current_position['entry_price'],
                            'exit_price': current_position['take_profit_price'],
                            'quantity': current_position['quantity'],
                            'pnl': pnl,
                            'exit_reason': "take_profit"
                        })
                        
                        current_position = None
        
        # Đóng vị thế đang mở nếu còn
        if current_position:
            # Lấy giá cuối cùng từ dataframe để đóng vị thế
            last_price = df.iloc[-1]['close']
            
            # Tính PnL
            if current_position['side'] == 'LONG':
                pnl = current_position['quantity'] * (last_price - current_position['entry_price'])
            else:
                pnl = current_position['quantity'] * (current_position['entry_price'] - last_price)
                
            # Đóng vị thế
            risk_manager.close_trade(
                trade_id=current_position['trade_id'],
                exit_price=last_price,
                pnl=pnl,
                exit_reason="end_of_backtest"
            )
            
            # Lưu giao dịch
            trades.append({
                'entry_time': current_position['entry_time'],
                'exit_time': df.iloc[-1]['timestamp'],
                'symbol': symbol,
                'side': current_position['side'],
                'entry_price': current_position['entry_price'],
                'exit_price': last_price,
                'quantity': current_position['quantity'],
                'pnl': pnl,
                'exit_reason': "end_of_backtest"
            })
            
            # Cập nhật balance
            balance += pnl
        
        # Tính toán các chỉ số hiệu suất
        final_balance = balance
        total_pnl = final_balance - self.initial_balance
        pnl_percentage = (total_pnl / self.initial_balance) * 100
        
        # Đếm số giao dịch thắng/thua
        win_trades = [t for t in trades if t['pnl'] > 0]
        lose_trades = [t for t in trades if t['pnl'] <= 0]
        win_count = len(win_trades)
        lose_count = len(lose_trades)
        total_trades = len(trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # Tính profit factor
        total_profit = sum(t['pnl'] for t in win_trades)
        total_loss = abs(sum(t['pnl'] for t in lose_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Tính drawdown
        max_balance = self.initial_balance
        max_drawdown = 0
        drawdown_pct = 0
        
        for eq in equity_curve:
            if eq > max_balance:
                max_balance = eq
            dd = max_balance - eq
            dd_pct = (dd / max_balance) * 100
            if dd_pct > drawdown_pct:
                drawdown_pct = dd_pct
                max_drawdown = dd
                
        # Lưu kết quả
        backtest_results = {
            'symbol': symbol,
            'interval': interval,
            'strategy': strategy,
            'start_date': df.iloc[0]['timestamp'].strftime('%Y-%m-%d'),
            'end_date': df.iloc[-1]['timestamp'].strftime('%Y-%m-%d'),
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_pnl': total_pnl,
            'pnl_percentage': pnl_percentage,
            'total_trades': total_trades,
            'win_count': win_count,
            'lose_count': lose_count,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': drawdown_pct,
            'modules_used': [
                position_sizer.name,
                order_executor.name,
                risk_manager.name
            ],
            'trades': trades
        }
        
        # Lưu equity curve
        np.save(f"backtest_results/equity_curve_{symbol}_{interval}.npy", np.array(equity_curve))
        
        # Vẽ đồ thị
        self._plot_backtest_results(
            df=df, 
            equity_curve=equity_curve, 
            trades=trades, 
            results=backtest_results,
            symbol=symbol,
            interval=interval
        )
        
        # Lưu kết quả
        output_file = f"backtest_results/integrated_backtest_{symbol}_{interval}.json"
        with open(output_file, 'w') as f:
            # Chuyển datetime thành string
            trades_serializable = []
            for t in trades:
                t_copy = t.copy()
                if 'entry_time' in t_copy and isinstance(t_copy['entry_time'], pd.Timestamp):
                    t_copy['entry_time'] = t_copy['entry_time'].strftime('%Y-%m-%d %H:%M:%S')
                if 'exit_time' in t_copy and isinstance(t_copy['exit_time'], pd.Timestamp):
                    t_copy['exit_time'] = t_copy['exit_time'].strftime('%Y-%m-%d %H:%M:%S')
                trades_serializable.append(t_copy)
                
            backtest_results['trades'] = trades_serializable
            json.dump(backtest_results, f, indent=4)
            
        logger.info(f"Kết quả backtest tích hợp lưu tại {output_file}")
        
        return {
            'status': 'success',
            'results': backtest_results,
            'output_file': output_file
        }
        
    def _plot_backtest_results(self, df, equity_curve, trades, results, symbol, interval):
        """Vẽ biểu đồ kết quả backtest"""
        plt.figure(figsize=(15, 10))
        
        # 1. Vẽ biểu đồ giá
        plt.subplot(2, 1, 1)
        plt.plot(df['timestamp'], df['close'], label='Close Price')
        plt.plot(df['timestamp'], df['sma_20'], label='SMA20')
        plt.plot(df['timestamp'], df['sma_50'], label='SMA50')
        
        # Vẽ các điểm vào lệnh/ra lệnh
        for trade in trades:
            entry_time = trade['entry_time']
            exit_time = trade['exit_time']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            
            if trade['side'] == 'LONG':
                plt.scatter(entry_time, entry_price, color='green', marker='^', s=100)
                plt.scatter(exit_time, exit_price, color='red', marker='v', s=100)
            else:
                plt.scatter(entry_time, entry_price, color='red', marker='v', s=100)
                plt.scatter(exit_time, exit_price, color='green', marker='^', s=100)
                
        plt.title(f'Backtest Results for {symbol} ({interval})')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        
        # 2. Vẽ biểu đồ equity
        plt.subplot(2, 1, 2)
        plt.plot(df['timestamp'][:len(equity_curve)], equity_curve, label='Equity Curve')
        plt.title(f'Equity Curve - Win Rate: {results["win_rate"]:.2%}, PnL: {results["total_pnl"]:.2f} ({results["pnl_percentage"]:.2f}%)')
        plt.ylabel('Equity')
        plt.grid(True)
        plt.legend()
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(f"backtest_results/backtest_chart_{symbol}_{interval}.png")
        plt.close()
        
    def run_all_tests(self):
        """Chạy tất cả các bài test"""
        results = {}
        
        # 1. Backtest position sizing
        logger.info("1. Bắt đầu backtest position sizing")
        results['position_sizing'] = self.backtest_position_sizing()
        
        # 2. Backtest order execution
        logger.info("2. Bắt đầu backtest order execution")
        results['order_execution'] = self.backtest_order_execution()
        
        # 3. Backtest risk management
        logger.info("3. Bắt đầu backtest risk management")
        results['risk_management'] = self.backtest_risk_management()
        
        # 4. Backtest tích hợp
        logger.info("4. Bắt đầu backtest tích hợp")
        results['integrated'] = self.backtest_integrated_modules()
        
        # Lưu tất cả kết quả
        with open(f"backtest_results/all_tests_summary.json", 'w') as f:
            json.dump(results, f, indent=4)
            
        logger.info("Hoàn thành tất cả các bài test")
        return results

def main():
    """Hàm chính"""
    # Đảm bảo thư mục kết quả tồn tại
    os.makedirs("backtest_results", exist_ok=True)
    
    logger.info("Bắt đầu backtest modules...")
    
    try:
        # Tạo backtester
        backtester = ModuleBacktester(initial_balance=10000.0)
        
        # Chạy backtest tích hợp
        results = backtester.backtest_integrated_modules(
            symbol='BTCUSDT',
            interval='1h',
            days=60,
            strategy='simple_ma_cross'
        )
        
        logger.info(f"Kết quả backtest: {results.get('status', 'unknown')}")
        
        # Chạy các test module riêng lẻ nếu muốn
        run_all = input("Bạn có muốn chạy tất cả các bài test không? (y/n): ")
        if run_all.lower() == 'y':
            all_results = backtester.run_all_tests()
            logger.info("Đã hoàn thành tất cả các bài test")
        
    except Exception as e:
        logger.error(f"Lỗi trong quá trình backtest: {e}")
        logger.error(traceback.format_exc())
        
    logger.info("Backtest hoàn tất")

if __name__ == "__main__":
    main()