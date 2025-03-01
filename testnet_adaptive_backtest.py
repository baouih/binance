#!/usr/bin/env python3
"""
Script chạy backtest với chiến lược thích ứng trên dữ liệu thực từ Binance Testnet

Script này thực hiện:
1. Kết nối với Binance Testnet API để lấy dữ liệu thực
2. Xử lý dữ liệu và tính toán các chỉ báo kỹ thuật
3. Chạy backtest với chiến lược thích ứng đa chỉ báo
4. Tạo báo cáo và biểu đồ chi tiết
"""

import os
import json
import time
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import requests
import hmac
import hashlib
import dotenv
from urllib.parse import urlencode
import concurrent.futures
from adaptive_strategy_backtester import MarketRegimeDetector, StrategiesManager, RiskManager

# Tải biến môi trường
dotenv.load_dotenv()

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('testnet_backtest')

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)

class BinanceTestnetAPI:
    """Lớp kết nối với Binance Testnet API"""
    
    def __init__(self):
        """Khởi tạo kết nối với Binance Testnet"""
        self.base_url = "https://testnet.binancefuture.com"
        self.api_key = os.environ.get("BINANCE_API_KEY")
        self.api_secret = os.environ.get("BINANCE_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            logger.warning("API key hoặc API secret không được cấu hình")
        
        self.headers = {
            'X-MBX-APIKEY': self.api_key
        }
    
    def _get_signature(self, params: Dict) -> str:
        """
        Tạo chữ ký cho yêu cầu API
        
        Args:
            params (Dict): Các tham số yêu cầu
            
        Returns:
            str: Chữ ký HMAC SHA256
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def get_server_time(self) -> int:
        """
        Lấy thời gian máy chủ Binance
        
        Returns:
            int: Thời gian máy chủ (miliseconds)
        """
        path = '/fapi/v1/time'
        url = self.base_url + path
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()['serverTime']
        except Exception as e:
            logger.error(f"Lỗi khi lấy thời gian máy chủ: {e}")
            # Sử dụng thời gian local nếu không thể lấy được thời gian máy chủ
            return int(time.time() * 1000)
    
    def get_exchange_info(self) -> Dict:
        """
        Lấy thông tin về các cặp giao dịch từ Binance
        
        Returns:
            Dict: Thông tin về các cặp giao dịch
        """
        path = '/fapi/v1/exchangeInfo'
        url = self.base_url + path
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin exchange: {e}")
            return {}
    
    def get_historical_klines(self, symbol: str, interval: str, 
                            start_time: Optional[int] = None, 
                            end_time: Optional[int] = None, 
                            limit: int = 500) -> List[List]:
        """
        Lấy dữ liệu candlestick lịch sử từ Binance
        
        Args:
            symbol (str): Mã cặp giao dịch
            interval (str): Khung thời gian (1m, 5m, 15m, 1h, 4h, 1d, ...)
            start_time (int, optional): Thời điểm bắt đầu (miliseconds)
            end_time (int, optional): Thời điểm kết thúc (miliseconds)
            limit (int): Số lượng candlestick tối đa (tối đa 1000)
            
        Returns:
            List[List]: Danh sách các candlestick
        """
        path = '/fapi/v1/klines'
        url = self.base_url + path
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu candlestick: {e}")
            return []
    
    def get_historical_data(self, symbol: str, interval: str, days: int = 30) -> pd.DataFrame:
        """
        Lấy dữ liệu lịch sử cho một khoảng thời gian
        
        Args:
            symbol (str): Mã cặp giao dịch
            interval (str): Khung thời gian
            days (int): Số ngày dữ liệu cần lấy
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu lịch sử
        """
        # Tính thời điểm bắt đầu (days ngày trước)
        end_time = int(time.time() * 1000)
        start_time = end_time - (days * 24 * 60 * 60 * 1000)
        
        # Số candlestick tối đa trong một yêu cầu
        limit = 1000
        
        # Danh sách để lưu dữ liệu
        all_klines = []
        
        # Lấy dữ liệu theo từng phần
        current_start_time = start_time
        
        while current_start_time < end_time:
            # Lấy dữ liệu
            klines = self.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_time=current_start_time,
                end_time=end_time,
                limit=limit
            )
            
            if not klines:
                break
            
            # Thêm vào danh sách
            all_klines.extend(klines)
            
            # Cập nhật thời điểm bắt đầu cho yêu cầu tiếp theo
            current_start_time = klines[-1][0] + 1
            
            # Tránh gửi quá nhiều yêu cầu trong một khoảng thời gian ngắn
            time.sleep(0.5)
        
        # Chuyển đổi thành DataFrame
        if not all_klines:
            logger.error(f"Không thể lấy dữ liệu lịch sử cho {symbol}")
            return pd.DataFrame()
        
        # Tạo DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Chuyển đổi kiểu dữ liệu
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        for col in ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume',
                   'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']:
            df[col] = df[col].astype(float)
        
        df['number_of_trades'] = df['number_of_trades'].astype(int)
        
        # Đặt timestamp làm index
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"Đã lấy {len(df)} candlesticks cho {symbol} ({interval}) từ {df.index[0]} đến {df.index[-1]}")
        
        return df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tính toán các chỉ báo kỹ thuật
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo đã tính
    """
    # Tính RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Tính MACD
    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal']
    
    # Tính Bollinger Bands
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['stddev'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma20'] + (df['stddev'] * 2)
    df['lower_band'] = df['sma20'] - (df['stddev'] * 2)
    
    # Tính EMA
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # Tính ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    df['atr'] = true_range.rolling(14).mean()
    
    # Tính ADX
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff() * -1
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = np.maximum(
        df['high'] - df['low'],
        np.abs(df['high'] - df['close'].shift(1)),
        np.abs(df['low'] - df['close'].shift(1))
    )
    
    atr = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
    df['di_plus'] = plus_di
    df['di_minus'] = minus_di
    
    dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di))
    df['adx'] = dx.rolling(14).mean()
    
    return df

def run_testnet_backtest(
    symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'],
    interval='1h',
    days=30,
    initial_balance=10000.0, 
    leverage=5, 
    risk_percentage=1.0,
    use_trailing_stop=True):
    """
    Chạy backtest với dữ liệu từ Binance Testnet
    
    Args:
        symbols (List[str]): Danh sách các cặp giao dịch
        interval (str): Khung thời gian
        days (int): Số ngày dữ liệu
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        risk_percentage (float): Phần trăm rủi ro
        use_trailing_stop (bool): Sử dụng trailing stop hay không
    """
    logger.info(f"=== CHẠY BACKTEST TESTNET ===")
    logger.info(f"Cặp giao dịch: {', '.join(symbols)}")
    logger.info(f"Khung thời gian: {interval}")
    logger.info(f"Số ngày dữ liệu: {days}")
    logger.info(f"Số dư ban đầu: ${initial_balance}")
    logger.info(f"Đòn bẩy: {leverage}x")
    logger.info(f"Rủi ro: {risk_percentage}%")
    logger.info(f"Trailing Stop: {'Bật' if use_trailing_stop else 'Tắt'}")
    
    # Khởi tạo Binance Testnet API
    binance_api = BinanceTestnetAPI()
    
    # Danh sách để lưu kết quả
    all_results = {}
    
    # Chạy backtest cho từng cặp tiền
    for symbol in symbols:
        logger.info(f"\n=== Bắt đầu backtest cho {symbol} ===")
        
        # Lấy dữ liệu từ Binance Testnet
        df = binance_api.get_historical_data(symbol, interval, days)
        
        if df.empty:
            logger.error(f"Không có dữ liệu cho {symbol}")
            continue
        
        # Tính toán các chỉ báo
        df = calculate_indicators(df)
        
        # Khởi tạo các thành phần
        market_regime_detector = MarketRegimeDetector()
        strategies_manager = StrategiesManager(market_regime_detector)
        risk_manager = RiskManager(initial_balance, risk_percentage)
        
        # Danh sách để lưu trữ giá trị vốn
        equity_curve = [initial_balance]
        dates = [df.index[0]]
        regime_history = []
        
        # Khởi tạo các biến theo dõi
        current_position = None
        position_id = None
        
        # Chạy backtest
        logger.info(f"Bắt đầu backtest cho {symbol}...")
        
        # Bỏ qua một số candlesticks đầu tiên để chờ các chỉ báo có đủ dữ liệu
        start_idx = 100
        
        # Thêm cột tín hiệu để theo dõi
        df['signal'] = 0
        df['regime'] = 'unknown'
        
        for i in range(start_idx, len(df)):
            # Dữ liệu đến candlestick hiện tại
            data_so_far = df.iloc[:i+1]
            current_row = data_so_far.iloc[-1]
            current_date = data_so_far.index[-1]
            current_price = current_row['close']
            
            # Phát hiện chế độ thị trường
            regime = market_regime_detector.detect_regime(data_so_far)
            df.loc[current_date, 'regime'] = regime
            regime_history.append(regime)
            
            # Tạo tín hiệu giao dịch
            signals = strategies_manager.generate_combined_signals(data_so_far)
            current_signal = signals[-1]
            df.loc[current_date, 'signal'] = current_signal
            
            # Kiểm tra vị thế
            if current_position is None:
                # Chưa có vị thế, kiểm tra tín hiệu để mở vị thế mới
                if current_signal == 1:  # Tín hiệu mua
                    # Tính toán stop loss
                    atr_value = current_row['atr']
                    stop_loss_price = current_price - (atr_value * 2)
                    
                    # Tính toán kích thước vị thế
                    quantity, sizing_info = risk_manager.calculate_position_size(
                        current_price, stop_loss_price, leverage, regime)
                    
                    # Tính toán take profit
                    take_profit_price = risk_manager.calculate_dynamic_take_profit(
                        current_price, stop_loss_price, 'BUY', atr_value, regime)
                    
                    # Mở vị thế
                    position_id = risk_manager.open_position(
                        'BUY', current_price, quantity, leverage, 
                        stop_loss_price, take_profit_price, 
                        use_trailing_stop, 0.5, 0.2, current_date)
                    
                    current_position = 'BUY'
                    
                    logger.info(f"Mở vị thế MUA tại {current_date}: ${current_price:.2f}, "
                              f"Số lượng: {quantity:.6f}, SL: ${stop_loss_price:.2f}, "
                              f"TP: ${take_profit_price:.2f}, Chế độ: {regime}")
                    
                elif current_signal == -1:  # Tín hiệu bán
                    # Tính toán stop loss
                    atr_value = current_row['atr']
                    stop_loss_price = current_price + (atr_value * 2)
                    
                    # Tính toán kích thước vị thế
                    quantity, sizing_info = risk_manager.calculate_position_size(
                        current_price, stop_loss_price, leverage, regime)
                    
                    # Tính toán take profit
                    take_profit_price = risk_manager.calculate_dynamic_take_profit(
                        current_price, stop_loss_price, 'SELL', atr_value, regime)
                    
                    # Mở vị thế
                    position_id = risk_manager.open_position(
                        'SELL', current_price, quantity, leverage, 
                        stop_loss_price, take_profit_price, 
                        use_trailing_stop, 0.5, 0.2, current_date)
                    
                    current_position = 'SELL'
                    
                    logger.info(f"Mở vị thế BÁN tại {current_date}: ${current_price:.2f}, "
                              f"Số lượng: {quantity:.6f}, SL: ${stop_loss_price:.2f}, "
                              f"TP: ${take_profit_price:.2f}, Chế độ: {regime}")
            else:
                # Đã có vị thế, kiểm tra tín hiệu đóng hoặc đảo chiều
                if ((current_position == 'BUY' and current_signal == -1) or 
                    (current_position == 'SELL' and current_signal == 1)):
                    
                    # Đóng vị thế hiện tại do đảo chiều
                    closed_position = risk_manager.close_position(
                        position_id, current_price, current_date, 'Reverse Signal')
                    
                    # Log kết quả
                    logger.info(f"Đóng vị thế {closed_position['side']} tại {current_date}: "
                              f"${current_price:.2f}, PnL: {closed_position['pnl_pct']:.2f}%, "
                              f"${closed_position['pnl']:.2f}, Lý do: Đảo chiều")
                    
                    # Reset vị thế
                    current_position = None
                    position_id = None
                    
                    # Mở vị thế mới với tín hiệu mới
                    if current_signal == 1:  # Tín hiệu mua
                        # Tính toán stop loss
                        atr_value = current_row['atr']
                        stop_loss_price = current_price - (atr_value * 2)
                        
                        # Tính toán kích thước vị thế
                        quantity, sizing_info = risk_manager.calculate_position_size(
                            current_price, stop_loss_price, leverage, regime)
                        
                        # Tính toán take profit
                        take_profit_price = risk_manager.calculate_dynamic_take_profit(
                            current_price, stop_loss_price, 'BUY', atr_value, regime)
                        
                        # Mở vị thế
                        position_id = risk_manager.open_position(
                            'BUY', current_price, quantity, leverage, 
                            stop_loss_price, take_profit_price, 
                            use_trailing_stop, 0.5, 0.2, current_date)
                        
                        current_position = 'BUY'
                        
                        logger.info(f"Mở vị thế MUA tại {current_date}: ${current_price:.2f}, "
                                  f"Số lượng: {quantity:.6f}, SL: ${stop_loss_price:.2f}, "
                                  f"TP: ${take_profit_price:.2f}, Chế độ: {regime}")
                        
                    elif current_signal == -1:  # Tín hiệu bán
                        # Tính toán stop loss
                        atr_value = current_row['atr']
                        stop_loss_price = current_price + (atr_value * 2)
                        
                        # Tính toán kích thước vị thế
                        quantity, sizing_info = risk_manager.calculate_position_size(
                            current_price, stop_loss_price, leverage, regime)
                        
                        # Tính toán take profit
                        take_profit_price = risk_manager.calculate_dynamic_take_profit(
                            current_price, stop_loss_price, 'SELL', atr_value, regime)
                        
                        # Mở vị thế
                        position_id = risk_manager.open_position(
                            'SELL', current_price, quantity, leverage, 
                            stop_loss_price, take_profit_price, 
                            use_trailing_stop, 0.5, 0.2, current_date)
                        
                        current_position = 'SELL'
                        
                        logger.info(f"Mở vị thế BÁN tại {current_date}: ${current_price:.2f}, "
                                  f"Số lượng: {quantity:.6f}, SL: ${stop_loss_price:.2f}, "
                                  f"TP: ${take_profit_price:.2f}, Chế độ: {regime}")
                else:
                    # Cập nhật vị thế
                    price_dict = {position_id: current_price}
                    closed_positions = risk_manager.update_positions(price_dict, current_date)
                    
                    # Kiểm tra xem vị thế có bị đóng không
                    if closed_positions:
                        closed_position = closed_positions[0]
                        logger.info(f"Đóng vị thế {closed_position['side']} tại {current_date}: "
                                  f"${current_price:.2f}, PnL: {closed_position['pnl_pct']:.2f}%, "
                                  f"${closed_position['pnl']:.2f}, Lý do: {closed_position['exit_reason']}")
                        
                        # Reset vị thế
                        current_position = None
                        position_id = None
            
            # Cập nhật đường cong vốn
            if i % 24 == 0 or i == len(df) - 1:  # Cập nhật hàng ngày hoặc ở candle cuối cùng
                equity_curve.append(risk_manager.current_balance)
                dates.append(current_date)
        
        # Đóng vị thế cuối cùng nếu còn
        if current_position is not None:
            final_price = df['close'].iloc[-1]
            final_date = df.index[-1]
            
            closed_position = risk_manager.close_position(
                position_id, final_price, final_date, 'End of Backtest')
            
            logger.info(f"Đóng vị thế cuối cùng {closed_position['side']} tại {final_date}: "
                      f"${final_price:.2f}, PnL: {closed_position['pnl_pct']:.2f}%, "
                      f"${closed_position['pnl']:.2f}, Lý do: Kết thúc backtest")
        
        # Tính toán hiệu suất
        performance = risk_manager.get_performance_metrics()
        
        # Hiển thị kết quả
        logger.info(f"\n=== KẾT QUẢ BACKTEST CHO {symbol} ===")
        logger.info(f"Số giao dịch: {performance['total_trades']}")
        logger.info(f"Giao dịch thắng/thua: {performance['winning_trades']}/{performance['losing_trades']}")
        logger.info(f"Win rate: {performance['win_rate']:.2f}%")
        logger.info(f"Profit factor: {performance['profit_factor']:.2f}")
        logger.info(f"Lợi nhuận trung bình: ${performance['avg_profit']:.2f}")
        logger.info(f"Thua lỗ trung bình: ${performance['avg_loss']:.2f}")
        logger.info(f"Drawdown tối đa: {performance['max_drawdown']:.2f}%")
        logger.info(f"Số dư ban đầu: ${performance['initial_balance']:.2f}")
        logger.info(f"Số dư cuối cùng: ${performance['current_balance']:.2f}")
        logger.info(f"Lợi nhuận: ${performance['profit_amount']:.2f} ({performance['profit_percent']:.2f}%)")
        
        # Phân phối chế độ thị trường
        regime_counts = {}
        for r in regime_history:
            regime_counts[r] = regime_counts.get(r, 0) + 1
        
        total_regimes = len(regime_history)
        logger.info(f"\n=== PHÂN PHỐI CHẾ ĐỘ THỊ TRƯỜNG CHO {symbol} ===")
        for regime, count in regime_counts.items():
            logger.info(f"{regime}: {count} candles ({count/total_regimes*100:.2f}%)")
        
        # Vẽ đồ thị đường cong vốn
        plt.figure(figsize=(12, 6))
        plt.plot(dates, equity_curve)
        plt.title(f'Đường cong vốn - {symbol} {interval}')
        plt.xlabel('Thời gian')
        plt.ylabel('Vốn ($)')
        plt.grid(True)
        
        chart_path = f'backtest_charts/testnet_{symbol}_{interval}_equity.png'
        plt.savefig(chart_path)
        logger.info(f"Đã lưu đồ thị đường cong vốn vào '{chart_path}'")
        
        # Vẽ đồ thị phân phối chế độ thị trường
        plt.figure(figsize=(10, 5))
        plt.bar(regime_counts.keys(), regime_counts.values())
        plt.title(f'Phân phối chế độ thị trường - {symbol} {interval}')
        plt.xlabel('Chế độ')
        plt.ylabel('Số lượng candles')
        plt.grid(True, axis='y')
        
        regime_chart_path = f'backtest_charts/testnet_{symbol}_{interval}_regime.png'
        plt.savefig(regime_chart_path)
        logger.info(f"Đã lưu đồ thị phân phối chế độ thị trường vào '{regime_chart_path}'")
        
        # Vẽ đồ thị giá và tín hiệu
        plt.figure(figsize=(14, 10))
        
        # Đồ thị giá và chế độ thị trường
        plt.subplot(3, 1, 1)
        plt.plot(df.index[start_idx:], df['close'].iloc[start_idx:], label='Giá đóng cửa')
        plt.plot(df.index[start_idx:], df['sma20'].iloc[start_idx:], 'b--', label='SMA 20')
        plt.plot(df.index[start_idx:], df['upper_band'].iloc[start_idx:], 'r--', label='Upper Band')
        plt.plot(df.index[start_idx:], df['lower_band'].iloc[start_idx:], 'g--', label='Lower Band')
        
        # Đánh dấu các khu vực theo chế độ thị trường
        regimes = df['regime'].iloc[start_idx:]
        for regime in ['trending', 'ranging', 'volatile', 'quiet', 'mixed']:
            mask = regimes == regime
            if mask.any():
                plt.scatter(df.index[start_idx:][mask], df['close'].iloc[start_idx:][mask], 
                          marker='.', alpha=0.5, label=f'Chế độ: {regime}')
        
        plt.title(f'Giá và chế độ thị trường - {symbol} {interval}')
        plt.ylabel('Giá ($)')
        plt.grid(True)
        plt.legend()
        
        # Đồ thị tín hiệu giao dịch
        plt.subplot(3, 1, 2)
        
        # Tìm tín hiệu mua và bán
        buy_signals = df['signal'].iloc[start_idx:] == 1
        sell_signals = df['signal'].iloc[start_idx:] == -1
        
        plt.plot(df.index[start_idx:], df['close'].iloc[start_idx:], alpha=0.3)
        plt.scatter(df.index[start_idx:][buy_signals], df['close'].iloc[start_idx:][buy_signals], 
                  color='green', marker='^', s=100, label='Mua')
        plt.scatter(df.index[start_idx:][sell_signals], df['close'].iloc[start_idx:][sell_signals], 
                  color='red', marker='v', s=100, label='Bán')
        
        # Vẽ các vị thế
        for position in risk_manager.closed_positions:
            if position['side'] == 'BUY':
                # Tạo arrow từ điểm vào đến điểm ra
                plt.plot([position['entry_time'], position['exit_time']], 
                       [position['entry_price'], position['exit_price']], 
                       'g-', alpha=0.5)
                
                # Đánh dấu điểm vào và ra
                plt.scatter(position['entry_time'], position['entry_price'], 
                          color='green', marker='o', s=50)
                
                # Màu điểm ra phụ thuộc vào lợi nhuận
                exit_color = 'green' if position['pnl'] > 0 else 'red'
                plt.scatter(position['exit_time'], position['exit_price'], 
                          color=exit_color, marker='x', s=50)
            else:  # SELL
                # Tạo arrow từ điểm vào đến điểm ra
                plt.plot([position['entry_time'], position['exit_time']], 
                       [position['entry_price'], position['exit_price']], 
                       'r-', alpha=0.5)
                
                # Đánh dấu điểm vào và ra
                plt.scatter(position['entry_time'], position['entry_price'], 
                          color='red', marker='o', s=50)
                
                # Màu điểm ra phụ thuộc vào lợi nhuận
                exit_color = 'green' if position['pnl'] > 0 else 'red'
                plt.scatter(position['exit_time'], position['exit_price'], 
                          color=exit_color, marker='x', s=50)
        
        plt.title('Tín hiệu giao dịch và vị thế')
        plt.ylabel('Giá ($)')
        plt.grid(True)
        plt.legend()
        
        # Đồ thị chỉ báo
        plt.subplot(3, 1, 3)
        plt.plot(df.index[start_idx:], df['rsi'].iloc[start_idx:], label='RSI')
        plt.axhline(y=70, color='r', linestyle='-', alpha=0.3)
        plt.axhline(y=30, color='g', linestyle='-', alpha=0.3)
        plt.axhline(y=50, color='gray', linestyle='--', alpha=0.3)
        
        plt.title('RSI (14)')
        plt.ylabel('RSI')
        plt.grid(True)
        plt.legend()
        
        plt.tight_layout()
        
        signals_chart_path = f'backtest_charts/testnet_{symbol}_{interval}_signals.png'
        plt.savefig(signals_chart_path)
        logger.info(f"Đã lưu đồ thị tín hiệu vào '{signals_chart_path}'")
        
        # Lưu giao dịch
        trades_df = pd.DataFrame([position for position in risk_manager.closed_positions])
        trades_file = f'backtest_results/testnet_{symbol}_{interval}_trades.csv'
        
        if not trades_df.empty:
            trades_df.to_csv(trades_file, index=False)
            logger.info(f"Đã lưu lịch sử giao dịch vào '{trades_file}'")
        
        # Lưu kết quả
        results = {
            'symbol': symbol,
            'interval': interval,
            'strategy': 'adaptive',
            'initial_balance': initial_balance,
            'final_balance': risk_manager.current_balance,
            'profit': risk_manager.current_balance - initial_balance,
            'profit_percent': (risk_manager.current_balance - initial_balance) / initial_balance * 100,
            'num_trades': performance['total_trades'],
            'winning_trades': performance['winning_trades'],
            'losing_trades': performance['losing_trades'],
            'win_rate': performance['win_rate'],
            'profit_factor': performance['profit_factor'],
            'max_drawdown': performance['max_drawdown'],
            'leverage': leverage,
            'risk_percentage': risk_percentage,
            'use_trailing_stop': use_trailing_stop,
            'regime_distribution': regime_counts
        }
        
        results_file = f'backtest_results/testnet_{symbol}_{interval}_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Đã lưu kết quả backtest vào '{results_file}'")
        
        # Thêm vào kết quả tổng hợp
        all_results[symbol] = results
    
    # Tạo báo cáo tóm tắt kết quả
    summary = {
        'backtest_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'interval': interval,
        'days': days,
        'initial_balance': initial_balance,
        'leverage': leverage,
        'risk_percentage': risk_percentage,
        'use_trailing_stop': use_trailing_stop,
        'symbols': {}
    }
    
    total_profit_percent = 0.0
    total_trades = 0
    total_winning_trades = 0
    total_losing_trades = 0
    
    for symbol, result in all_results.items():
        summary['symbols'][symbol] = {
            'profit_percent': result['profit_percent'],
            'win_rate': result['win_rate'],
            'num_trades': result['num_trades'],
            'profit_factor': result['profit_factor'],
            'max_drawdown': result['max_drawdown']
        }
        
        total_profit_percent += result['profit_percent']
        total_trades += result['num_trades']
        total_winning_trades += result['winning_trades']
        total_losing_trades += result['losing_trades']
    
    if all_results:
        average_profit = total_profit_percent / len(all_results)
        average_win_rate = (total_winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        summary['average_profit_percent'] = average_profit
        summary['average_win_rate'] = average_win_rate
        summary['total_trades'] = total_trades
        
        summary_file = f'backtest_results/testnet_summary_{interval}.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"\n=== TÓM TẮT KẾT QUẢ BACKTEST ===")
        logger.info(f"Số cặp giao dịch: {len(all_results)}")
        logger.info(f"Tổng số giao dịch: {total_trades}")
        logger.info(f"Lợi nhuận trung bình: {average_profit:.2f}%")
        logger.info(f"Win rate trung bình: {average_win_rate:.2f}%")
        
        # Tạo biểu đồ so sánh lợi nhuận
        plt.figure(figsize=(12, 6))
        symbols = list(all_results.keys())
        profits = [all_results[s]['profit_percent'] for s in symbols]
        win_rates = [all_results[s]['win_rate'] for s in symbols]
        
        bars = plt.bar(symbols, profits, alpha=0.7)
        
        # Đánh dấu màu dựa trên lợi nhuận
        for i, bar in enumerate(bars):
            if profits[i] > 0:
                bar.set_color('green')
            else:
                bar.set_color('red')
            
            # Thêm nhãn win rate
            plt.text(i, profits[i] + np.sign(profits[i]) * 2, 
                   f"WR: {win_rates[i]:.1f}%", 
                   ha='center', va='bottom')
        
        plt.axhline(y=0, color='gray', linestyle='-')
        plt.title('So sánh lợi nhuận giữa các cặp tiền')
        plt.xlabel('Cặp giao dịch')
        plt.ylabel('Lợi nhuận (%)')
        plt.grid(True, axis='y')
        
        comparison_chart_path = f'backtest_charts/testnet_comparison_{interval}.png'
        plt.savefig(comparison_chart_path)
        logger.info(f"Đã lưu biểu đồ so sánh vào '{comparison_chart_path}'")
    
    return all_results

def check_binance_api_keys():
    """
    Kiểm tra xem API keys của Binance đã được cấu hình chưa
    
    Returns:
        bool: True nếu API keys đã được cấu hình, False nếu chưa
    """
    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("BINANCE_API_KEY và BINANCE_API_SECRET chưa được cấu hình trong file .env")
        return False
    
    # Kiểm tra kết nối với Binance Testnet
    binance_api = BinanceTestnetAPI()
    try:
        server_time = binance_api.get_server_time()
        if server_time > 0:
            logger.info("Kết nối với Binance Testnet thành công")
            return True
        else:
            logger.error("Không thể kết nối với Binance Testnet")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi kết nối với Binance Testnet: {e}")
        return False

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Công cụ backtest với dữ liệu Binance Testnet')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT',
                       help='Danh sách các cặp giao dịch, phân tách bằng dấu phẩy (mặc định: BTCUSDT,ETHUSDT)')
    parser.add_argument('--interval', type=str, default='1h', 
                       help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--days', type=int, default=30, 
                       help='Số ngày dữ liệu (mặc định: 30)')
    parser.add_argument('--balance', type=float, default=10000.0, 
                       help='Số dư ban đầu (mặc định: $10,000)')
    parser.add_argument('--leverage', type=int, default=5, 
                       help='Đòn bẩy (mặc định: 5x)')
    parser.add_argument('--risk', type=float, default=1.0, 
                       help='Phần trăm rủi ro (mặc định: 1%%)')
    parser.add_argument('--trailing_stop', action='store_true', 
                       help='Sử dụng trailing stop (mặc định: True)')
    
    args = parser.parse_args()
    
    # Kiểm tra API keys
    if not check_binance_api_keys():
        logger.error("Vui lòng cấu hình BINANCE_API_KEY và BINANCE_API_SECRET trong file .env")
        return
    
    # Chuyển đổi danh sách cặp giao dịch
    symbols = args.symbols.split(',')
    
    # Chạy backtest
    run_testnet_backtest(
        symbols=symbols,
        interval=args.interval,
        days=args.days,
        initial_balance=args.balance,
        leverage=args.leverage,
        risk_percentage=args.risk,
        use_trailing_stop=args.trailing_stop
    )

if __name__ == "__main__":
    main()