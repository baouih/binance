#!/usr/bin/env python3
"""
Script backtest nâng cao với phát hiện chế độ thị trường và thích ứng chiến lược

Script này thực hiện backtest với khả năng:
1. Phát hiện chế độ thị trường (trending, ranging, volatile, quiet)
2. Tự động chọn chiến lược phù hợp với từng chế độ thị trường
3. Điều chỉnh tham số chiến lược dựa trên chế độ thị trường
4. Tự động điều chỉnh quản lý rủi ro dựa trên biến động thị trường
"""

import os
import json
import time
import logging
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('enhanced_backtest')

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)

class MarketRegimeDetector:
    """Lớp phát hiện chế độ thị trường"""
    
    def __init__(self, config_path: str = 'configs/strategy_market_config.json'):
        """
        Khởi tạo bộ phát hiện chế độ thị trường
        
        Args:
            config_path (str): Đường dẫn file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.current_regime = 'ranging'  # Mặc định
        
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình từ {self.config_path}: {str(e)}")
        
        logger.warning(f"Không tìm thấy file cấu hình {self.config_path}, sử dụng cấu hình mặc định")
        return {}
    
    def detect_regime(self, df: pd.DataFrame, window: int = 20) -> str:
        """
        Phát hiện chế độ thị trường hiện tại
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            window (int): Kích thước cửa sổ để phân tích
            
        Returns:
            str: Chế độ thị trường hiện tại ('trending', 'ranging', 'volatile', 'quiet')
        """
        if len(df) < window:
            logger.warning(f"Không đủ dữ liệu để phát hiện chế độ thị trường, cần ít nhất {window} nến")
            return 'ranging'  # Mặc định
        
        # Lấy dữ liệu gần nhất
        recent_data = df.iloc[-window:]
        
        # Tính các chỉ báo cần thiết nếu chưa có
        if 'atr' not in recent_data.columns:
            high_low = recent_data['high'] - recent_data['low']
            high_close = np.abs(recent_data['high'] - recent_data['close'].shift())
            low_close = np.abs(recent_data['low'] - recent_data['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            recent_data['atr'] = ranges.rolling(window=14).mean()
        
        if 'adx' not in recent_data.columns:
            # Tính toán ADX đơn giản
            plus_dm = np.maximum(recent_data['high'].diff(), 0)
            minus_dm = np.maximum(-recent_data['low'].diff(), 0)
            plus_di = 100 * (plus_dm.rolling(window=14).mean() / recent_data['atr'])
            minus_di = 100 * (minus_dm.rolling(window=14).mean() / recent_data['atr'])
            dx = 100 * np.abs((plus_di - minus_di) / (plus_di + minus_di))
            recent_data['adx'] = dx.rolling(window=14).mean()
        
        # Tính các metrics cho phát hiện chế độ thị trường
        avg_price = recent_data['close'].mean()
        volatility = recent_data['atr'].iloc[-1] / avg_price
        adx_value = recent_data['adx'].iloc[-1]
        price_range = (recent_data['high'].max() - recent_data['low'].min()) / avg_price
        
        # Tính xu hướng giá
        start_price = recent_data['close'].iloc[0]
        end_price = recent_data['close'].iloc[-1]
        price_change = abs(end_price - start_price) / start_price
        is_trend = price_change > 0.05  # Thay đổi > 5%
        trend_direction = 1 if end_price > start_price else -1
        
        # Logic phát hiện chế độ thị trường
        if adx_value > 25 and is_trend:
            regime = 'trending'
        elif volatility > 0.03:
            regime = 'volatile'
        elif price_range < 0.05 and adx_value < 15:
            regime = 'quiet'
        else:
            regime = 'ranging'
        
        self.current_regime = regime
        return regime
    
    def get_strategy_parameters(self, strategy_name: str) -> Dict:
        """
        Lấy tham số chiến lược dựa trên chế độ thị trường hiện tại
        
        Args:
            strategy_name (str): Tên chiến lược
            
        Returns:
            Dict: Tham số chiến lược
        """
        strategy_params = self.config.get('strategy_parameters', {}).get(strategy_name, {})
        regime_params = strategy_params.get(self.current_regime, {})
        
        if not regime_params:
            logger.warning(f"Không tìm thấy tham số cho chiến lược {strategy_name} ở chế độ {self.current_regime}")
            # Trả về tham số mặc định
            for regime in strategy_params:
                return strategy_params[regime]  # Lấy tham số của chế độ đầu tiên tìm thấy
        
        return regime_params
    
    def get_risk_adjustment(self) -> float:
        """
        Lấy hệ số điều chỉnh rủi ro dựa trên chế độ thị trường hiện tại
        
        Returns:
            float: Hệ số điều chỉnh rủi ro
        """
        risk_adj = self.config.get(self.current_regime, {}).get('risk_adjustment', 1.0)
        return risk_adj
    
    def get_suitable_strategies(self) -> Dict[str, float]:
        """
        Lấy danh sách chiến lược phù hợp với chế độ thị trường hiện tại
        
        Returns:
            Dict[str, float]: Chiến lược và trọng số tương ứng
        """
        strategies = self.config.get(self.current_regime, {}).get('strategies', {})
        
        if not strategies:
            logger.warning(f"Không tìm thấy chiến lược cho chế độ {self.current_regime}")
            # Trả về chiến lược mặc định
            return {'rsi': 0.5, 'macd': 0.5}
        
        return strategies

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
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Tính Bollinger Bands
    df['sma20'] = df['close'].rolling(window=20).mean()
    std_dev = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma20'] + (std_dev * 2)
    df['lower_band'] = df['sma20'] - (std_dev * 2)
    
    # Tính ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = ranges.rolling(window=14).mean()
    
    # Tính ADX (Simplified)
    plus_dm = np.maximum(df['high'].diff(), 0)
    minus_dm = np.maximum(-df['low'].diff(), 0)
    plus_di = 100 * (plus_dm.rolling(window=14).mean() / df['atr'])
    minus_di = 100 * (minus_dm.rolling(window=14).mean() / df['atr'])
    dx = 100 * np.abs((plus_di - minus_di) / (plus_di + minus_di))
    df['adx'] = dx.rolling(window=14).mean()
    
    return df

def generate_signal_for_regime(df: pd.DataFrame, regime: str, regime_detector: MarketRegimeDetector) -> pd.Series:
    """
    Tạo tín hiệu giao dịch dựa trên chế độ thị trường
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá và chỉ báo
        regime (str): Chế độ thị trường
        regime_detector (MarketRegimeDetector): Bộ phát hiện chế độ thị trường
        
    Returns:
        pd.Series: Tín hiệu giao dịch (1: mua, -1: bán, 0: không giao dịch)
    """
    signals = pd.Series(0, index=df.index)
    
    # Lấy danh sách chiến lược phù hợp với chế độ thị trường
    strategies = regime_detector.get_suitable_strategies()
    
    weighted_signals = pd.Series(0, index=df.index)
    total_weight = sum(strategies.values())
    
    for strategy_name, weight in strategies.items():
        if strategy_name == 'momentum' or strategy_name == 'rsi':
            params = regime_detector.get_strategy_parameters('momentum')
            rsi_period = params.get('rsi_period', 14)
            rsi_overbought = params.get('rsi_overbought', 70)
            rsi_oversold = params.get('rsi_oversold', 30)
            
            # Tạo tín hiệu RSI
            rsi_signals = pd.Series(0, index=df.index)
            rsi_signals[df['rsi'] < rsi_oversold] = 1
            rsi_signals[df['rsi'] > rsi_overbought] = -1
            
            # Phát hiện xu hướng RSI đảo chiều
            rsi_signals[(df['rsi'] > rsi_oversold) & (df['rsi'].shift() < rsi_oversold)] = 0  # Exit long
            rsi_signals[(df['rsi'] < rsi_overbought) & (df['rsi'].shift() > rsi_overbought)] = 0  # Exit short
            
            weighted_signals += rsi_signals * (weight / total_weight)
            
        elif strategy_name == 'trend_following' or strategy_name == 'ema_cross':
            params = regime_detector.get_strategy_parameters('trend_following')
            ema_fast = params.get('ema_fast', 12)
            ema_slow = params.get('ema_slow', 26)
            
            # Tính EMA nếu chưa có
            if f'ema{ema_fast}' not in df.columns:
                df[f'ema{ema_fast}'] = df['close'].ewm(span=ema_fast, adjust=False).mean()
            if f'ema{ema_slow}' not in df.columns:
                df[f'ema{ema_slow}'] = df['close'].ewm(span=ema_slow, adjust=False).mean()
            
            # Tạo tín hiệu EMA Cross
            ema_signals = pd.Series(0, index=df.index)
            ema_signals[df[f'ema{ema_fast}'] > df[f'ema{ema_slow}']] = 1
            ema_signals[df[f'ema{ema_fast}'] < df[f'ema{ema_slow}']] = -1
            
            # Phát hiện tín hiệu cross
            cross_signals = pd.Series(0, index=df.index)
            cross_signals[(df[f'ema{ema_fast}'] > df[f'ema{ema_slow}']) & 
                         (df[f'ema{ema_fast}'].shift() < df[f'ema{ema_slow}'].shift())] = 1
            cross_signals[(df[f'ema{ema_fast}'] < df[f'ema{ema_slow}']) & 
                         (df[f'ema{ema_fast}'].shift() > df[f'ema{ema_slow}'].shift())] = -1
            
            weighted_signals += (ema_signals * 0.5 + cross_signals * 0.5) * (weight / total_weight)
            
        elif strategy_name == 'mean_reversion' or strategy_name == 'bollinger':
            params = regime_detector.get_strategy_parameters('mean_reversion')
            bb_period = params.get('bb_period', 20)
            bb_std_dev = params.get('bb_std_dev', 2.0)
            
            # Tính Bollinger nếu chưa có hoặc với tham số khác
            if 'sma20' not in df.columns or bb_period != 20:
                df[f'sma{bb_period}'] = df['close'].rolling(window=bb_period).mean()
                std_dev = df['close'].rolling(window=bb_period).std()
                df[f'upper_band_{bb_period}'] = df[f'sma{bb_period}'] + (std_dev * bb_std_dev)
                df[f'lower_band_{bb_period}'] = df[f'sma{bb_period}'] - (std_dev * bb_std_dev)
            else:
                df[f'upper_band_{bb_period}'] = df['upper_band']
                df[f'lower_band_{bb_period}'] = df['lower_band']
                df[f'sma{bb_period}'] = df['sma20']
            
            # Tạo tín hiệu Bollinger Bands
            bb_signals = pd.Series(0, index=df.index)
            bb_signals[df['close'] < df[f'lower_band_{bb_period}']] = 1
            bb_signals[df['close'] > df[f'upper_band_{bb_period}']] = -1
            
            # Tín hiệu khi giá trở về trung bình
            reversion_signals = pd.Series(0, index=df.index)
            reversion_signals[(df['close'] > df[f'sma{bb_period}']) & 
                             (df['close'].shift() < df[f'sma{bb_period}'].shift())] = -1
            reversion_signals[(df['close'] < df[f'sma{bb_period}']) & 
                             (df['close'].shift() > df[f'sma{bb_period}'].shift())] = 1
            
            weighted_signals += (bb_signals * 0.7 + reversion_signals * 0.3) * (weight / total_weight)
            
        elif strategy_name == 'breakout':
            params = regime_detector.get_strategy_parameters('breakout')
            period = params.get('period', 20)
            atr_multiplier = params.get('atr_multiplier', 2.5)
            
            # Tính ATR
            if 'atr' not in df.columns:
                high_low = df['high'] - df['low']
                high_close = np.abs(df['high'] - df['close'].shift())
                low_close = np.abs(df['low'] - df['close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                df['atr'] = ranges.rolling(window=14).mean()
            
            # Tạo kênh giá
            df[f'high_{period}'] = df['high'].rolling(window=period).max()
            df[f'low_{period}'] = df['low'].rolling(window=period).min()
            
            # Tạo tín hiệu Breakout
            breakout_signals = pd.Series(0, index=df.index)
            breakout_threshold = df['atr'] * atr_multiplier
            
            # Breakout lên
            breakout_signals[(df['close'] > df[f'high_{period}'].shift()) & 
                           (df['close'] - df[f'high_{period}'].shift() > breakout_threshold)] = 1
            
            # Breakout xuống
            breakout_signals[(df['close'] < df[f'low_{period}'].shift()) & 
                           (df[f'low_{period}'].shift() - df['close'] > breakout_threshold)] = -1
            
            weighted_signals += breakout_signals * (weight / total_weight)
            
        elif strategy_name == 'volatility_based':
            params = regime_detector.get_strategy_parameters('volatility_based')
            atr_period = params.get('atr_period', 14)
            atr_multiplier = params.get('atr_multiplier', 1.5)
            
            # Tính ATR nếu chưa có
            if 'atr' not in df.columns:
                high_low = df['high'] - df['low']
                high_close = np.abs(df['high'] - df['close'].shift())
                low_close = np.abs(df['low'] - df['close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                df['atr'] = ranges.rolling(window=atr_period).mean()
            
            # Kênh ATR
            df['atr_upper'] = df['close'].shift() + df['atr'] * atr_multiplier
            df['atr_lower'] = df['close'].shift() - df['atr'] * atr_multiplier
            
            # Tín hiệu khi giá vượt kênh ATR
            atr_signals = pd.Series(0, index=df.index)
            atr_signals[df['close'] > df['atr_upper']] = 1  # Động lượng tăng
            atr_signals[df['close'] < df['atr_lower']] = -1  # Động lượng giảm
            
            weighted_signals += atr_signals * (weight / total_weight)
    
    # Làm tròn tín hiệu cuối cùng
    signals[weighted_signals > 0.2] = 1
    signals[weighted_signals < -0.2] = -1
    
    return signals

def load_data(symbol, interval, data_dir='test_data'):
    """
    Tải dữ liệu giá từ file CSV
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        data_dir (str): Thư mục dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu giá
    """
    file_path = os.path.join(data_dir, f"{symbol}_{interval}.csv")
    
    if not os.path.exists(file_path):
        logger.error(f"Không tìm thấy file dữ liệu {file_path}")
        return None
    
    df = pd.read_csv(file_path)
    
    # Chuyển đổi timestamp thành datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    
    return df

def run_adaptive_backtest(
    symbol='BTCUSDT', 
    interval='1h',
    initial_balance=10000.0, 
    leverage=3, 
    risk_percentage=1.0,
    stop_loss_pct=7.0,
    take_profit_pct=15.0,
    use_adaptive_risk=True,
    data_dir='test_data'):
    """
    Chạy backtest với chiến lược thích ứng
    
    Args:
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        risk_percentage (float): Phần trăm rủi ro
        stop_loss_pct (float): Phần trăm stop loss
        take_profit_pct (float): Phần trăm take profit
        use_adaptive_risk (bool): Sử dụng quản lý rủi ro thích ứng hay không
        data_dir (str): Thư mục dữ liệu
    """
    # Thiết lập thông số backtest
    logger.info("=== CHẠY BACKTEST THÍCH ỨNG ===")
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Số dư ban đầu: ${initial_balance}")
    logger.info(f"Đòn bẩy: {leverage}x")
    logger.info(f"Rủi ro: {risk_percentage}%")
    logger.info(f"Take Profit: {take_profit_pct}%")
    logger.info(f"Stop Loss: {stop_loss_pct}%")
    logger.info(f"Sử dụng rủi ro thích ứng: {use_adaptive_risk}")
    
    # Tải dữ liệu
    df = load_data(symbol, interval, data_dir)
    
    if df is None or len(df) < 100:
        logger.error("Không đủ dữ liệu để chạy backtest")
        return
    
    logger.info(f"Đã tải {len(df)} candles từ {df.index[0]} đến {df.index[-1]}")
    
    # Tính toán các chỉ báo
    df = calculate_indicators(df)
    
    # Khởi tạo bộ phát hiện chế độ thị trường
    regime_detector = MarketRegimeDetector()
    
    # Khởi tạo biến lưu trữ chế độ thị trường cho từng thời điểm
    df['market_regime'] = None
    
    # Phát hiện chế độ thị trường tại từng thời điểm (sử dụng cửa sổ trượt)
    window = 50
    for i in range(window, len(df)):
        df_window = df.iloc[i-window:i]
        regime = regime_detector.detect_regime(df_window)
        df.iloc[i, df.columns.get_loc('market_regime')] = regime
    
    # Tạo tín hiệu giao dịch dựa trên chế độ thị trường
    df['signal'] = 0
    
    # Bắt đầu từ vị trí có đủ dữ liệu chế độ thị trường
    for i in range(window, len(df)):
        if pd.notna(df.iloc[i]['market_regime']):
            regime = df.iloc[i]['market_regime']
            regime_detector.current_regime = regime
            df_window = df.iloc[i-window:i+1].copy()
            signals = generate_signal_for_regime(df_window, regime, regime_detector)
            df.iloc[i, df.columns.get_loc('signal')] = signals.iloc[-1]
    
    # Chạy backtest
    logger.info("Bắt đầu backtest...")
    
    # Danh sách để lưu trữ các giao dịch
    trades = []
    
    # Danh sách để lưu trữ giá trị vốn
    equity_curve = [initial_balance]
    dates = [df.index[0]]
    
    # Trạng thái giao dịch hiện tại
    current_position = None
    balance = initial_balance
    
    # Lưu lại các regime cho báo cáo
    regime_changes = []
    current_regime = None
    
    # Bỏ qua một số candlesticks đầu tiên để chờ các chỉ báo có đủ dữ liệu
    start_idx = window + 20
    
    for i in range(start_idx, len(df)):
        current_row = df.iloc[i]
        current_price = current_row['close']
        current_date = df.index[i]
        current_signal = current_row['signal']
        
        # Kiểm tra thay đổi chế độ thị trường
        detected_regime = current_row['market_regime']
        if detected_regime is not None and detected_regime != current_regime:
            current_regime = detected_regime
            regime_changes.append({
                'date': current_date,
                'regime': current_regime,
                'price': current_price
            })
            logger.info(f"Phát hiện chế độ thị trường mới tại {current_date}: {current_regime}")
        
        # Điều chỉnh rủi ro theo chế độ thị trường nếu được bật
        current_risk_percentage = risk_percentage
        if use_adaptive_risk and current_regime is not None:
            regime_detector.current_regime = current_regime
            risk_adjustment = regime_detector.get_risk_adjustment()
            current_risk_percentage = risk_percentage * risk_adjustment
        
        # Tính số tiền rủi ro
        risk_amount = balance * (current_risk_percentage / 100)
        
        # Mở vị thế mới nếu chưa có vị thế
        if current_position is None:
            if current_signal == 1:  # Tín hiệu mua
                # Tính toán số lượng
                order_qty = (risk_amount * leverage) / current_price
                entry_price = current_price
                entry_date = current_date
                
                # Tính toán stop loss và take profit
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
                take_profit_price = entry_price * (1 + take_profit_pct / 100)
                
                current_position = {
                    'side': 'BUY',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'market_regime': current_regime,
                    'risk_percentage': current_risk_percentage
                }
                
                logger.info(f"Mở vị thế MUA tại {entry_date}: ${entry_price:.2f}, Số lượng: {order_qty:.6f}, "
                          f"SL: ${stop_loss_price:.2f}, TP: ${take_profit_price:.2f}, Chế độ: {current_regime}")
                
            elif current_signal == -1:  # Tín hiệu bán
                # Tính toán số lượng
                order_qty = (risk_amount * leverage) / current_price
                entry_price = current_price
                entry_date = current_date
                
                # Tính toán stop loss và take profit
                stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
                take_profit_price = entry_price * (1 - take_profit_pct / 100)
                
                current_position = {
                    'side': 'SELL',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'market_regime': current_regime,
                    'risk_percentage': current_risk_percentage
                }
                
                logger.info(f"Mở vị thế BÁN tại {entry_date}: ${entry_price:.2f}, Số lượng: {order_qty:.6f}, "
                          f"SL: ${stop_loss_price:.2f}, TP: ${take_profit_price:.2f}, Chế độ: {current_regime}")
        
        # Kiểm tra đóng vị thế nếu đang có vị thế
        elif current_position is not None:
            exit_reason = None
            
            # Kiểm tra stop loss
            if current_position['side'] == 'BUY' and current_price <= current_position['stop_loss']:
                exit_reason = "Stop Loss"
            elif current_position['side'] == 'SELL' and current_price >= current_position['stop_loss']:
                exit_reason = "Stop Loss"
            
            # Kiểm tra take profit
            elif current_position['side'] == 'BUY' and current_price >= current_position['take_profit']:
                exit_reason = "Take Profit"
            elif current_position['side'] == 'SELL' and current_price <= current_position['take_profit']:
                exit_reason = "Take Profit"
            
            # Kiểm tra tín hiệu đảo chiều
            elif (current_position['side'] == 'BUY' and current_signal == -1) or \
                 (current_position['side'] == 'SELL' and current_signal == 1):
                exit_reason = "Reverse Signal"
            
            # Đóng vị thế nếu có lý do
            if exit_reason:
                exit_price = current_price
                exit_date = current_date
                
                # Tính PnL
                if current_position['side'] == 'BUY':
                    price_change_pct = (exit_price - current_position['entry_price']) / current_position['entry_price']
                else:  # SELL
                    price_change_pct = (current_position['entry_price'] - exit_price) / current_position['entry_price']
                
                # Áp dụng đòn bẩy cho PnL
                pnl_pct = price_change_pct * leverage * 100  # Phần trăm
                pnl_amount = (current_position['quantity'] * current_position['entry_price']) * price_change_pct * leverage
                
                # Cập nhật số dư
                new_balance = balance + pnl_amount
                
                logger.info(f"Đóng vị thế {current_position['side']} tại {exit_date}: ${exit_price:.2f}, "
                          f"PnL: {pnl_pct:.2f}%, ${pnl_amount:.2f}, Lý do: {exit_reason}")
                
                # Lưu thông tin giao dịch
                trade = {
                    'side': current_position['side'],
                    'entry_date': current_position['entry_date'],
                    'entry_price': current_position['entry_price'],
                    'exit_date': exit_date,
                    'exit_price': exit_price,
                    'quantity': current_position['quantity'],
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'balance_before': balance,
                    'balance_after': new_balance,
                    'exit_reason': exit_reason,
                    'market_regime': current_position['market_regime'],
                    'risk_percentage': current_position['risk_percentage']
                }
                
                trades.append(trade)
                
                # Cập nhật số dư và đường cong vốn
                balance = new_balance
                equity_curve.append(balance)
                dates.append(exit_date)
                
                # Reset vị thế
                current_position = None
        
        # Cập nhật đường cong vốn nếu không có giao dịch
        if i % 24 == 0 and len(equity_curve) > 0 and dates[-1] != current_date:
            equity_curve.append(balance)
            dates.append(current_date)
    
    # Tính toán các chỉ số hiệu suất
    if len(trades) > 0:
        win_trades = [t for t in trades if t['pnl_amount'] > 0]
        lose_trades = [t for t in trades if t['pnl_amount'] <= 0]
        
        win_rate = len(win_trades) / len(trades) * 100 if len(trades) > 0 else 0
        
        total_profit = sum(t['pnl_amount'] for t in win_trades) if len(win_trades) > 0 else 0
        total_loss = sum(t['pnl_amount'] for t in lose_trades) if len(lose_trades) > 0 else 0
        
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        
        avg_profit = total_profit / len(win_trades) if len(win_trades) > 0 else 0
        avg_loss = total_loss / len(lose_trades) if len(lose_trades) > 0 else 0
        
        # Tính drawdown
        peak = initial_balance
        drawdowns = []
        
        for trade in trades:
            if trade['balance_after'] > peak:
                peak = trade['balance_after']
            
            drawdown = (peak - trade['balance_after']) / peak * 100
            drawdowns.append(drawdown)
        
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Hiệu suất theo chế độ thị trường
        regime_performance = {}
        
        for trade in trades:
            regime = trade['market_regime']
            if regime not in regime_performance:
                regime_performance[regime] = {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'profit': 0,
                    'loss': 0
                }
            
            regime_performance[regime]['trades'] += 1
            
            if trade['pnl_amount'] > 0:
                regime_performance[regime]['wins'] += 1
                regime_performance[regime]['profit'] += trade['pnl_amount']
            else:
                regime_performance[regime]['losses'] += 1
                regime_performance[regime]['loss'] += trade['pnl_amount']
        
        # Tính chỉ số theo chế độ thị trường
        for regime in regime_performance:
            stats = regime_performance[regime]
            stats['win_rate'] = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
            stats['profit_factor'] = abs(stats['profit'] / stats['loss']) if stats['loss'] != 0 else float('inf')
            stats['avg_profit'] = stats['profit'] / stats['wins'] if stats['wins'] > 0 else 0
            stats['avg_loss'] = stats['loss'] / stats['losses'] if stats['losses'] > 0 else 0
            stats['net_pnl'] = stats['profit'] + stats['loss']
            stats['net_pnl_pct'] = stats['net_pnl'] / initial_balance * 100
        
        # Hiển thị kết quả
        logger.info("\n=== KẾT QUẢ BACKTEST ===")
        logger.info(f"Số giao dịch: {len(trades)}")
        logger.info(f"Giao dịch thắng/thua: {len(win_trades)}/{len(lose_trades)}")
        logger.info(f"Win rate: {win_rate:.2f}%")
        logger.info(f"Profit factor: {profit_factor:.2f}")
        logger.info(f"Lợi nhuận trung bình: ${avg_profit:.2f}")
        logger.info(f"Thua lỗ trung bình: ${avg_loss:.2f}")
        logger.info(f"Drawdown tối đa: {max_drawdown:.2f}%")
        logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
        logger.info(f"Số dư cuối cùng: ${balance:.2f}")
        logger.info(f"Lợi nhuận: ${balance - initial_balance:.2f} ({(balance - initial_balance) / initial_balance * 100:.2f}%)")
        
        # Hiển thị hiệu suất theo chế độ thị trường
        logger.info("\n=== HIỆU SUẤT THEO CHẾ ĐỘ THỊ TRƯỜNG ===")
        for regime, stats in regime_performance.items():
            logger.info(f"Chế độ: {regime}")
            logger.info(f"  Số giao dịch: {stats['trades']}")
            logger.info(f"  Win rate: {stats['win_rate']:.2f}%")
            logger.info(f"  Profit factor: {stats['profit_factor']:.2f}")
            logger.info(f"  PnL: ${stats['net_pnl']:.2f} ({stats['net_pnl_pct']:.2f}%)")
        
        # Vẽ đường cong vốn
        plt.figure(figsize=(10, 6))
        plt.plot(dates, equity_curve)
        plt.title(f"Đường cong vốn - ADAPTIVE ({symbol} {interval})")
        plt.xlabel("Thời gian")
        plt.ylabel("Vốn ($)")
        plt.grid(True)
        
        # Đánh dấu chuyển đổi chế độ thị trường
        for change in regime_changes:
            plt.axvline(x=change['date'], color='r', linestyle='--', alpha=0.5)
            plt.text(change['date'], min(equity_curve) * 1.05, change['regime'], rotation=90)
        
        # Lưu đồ thị
        equity_chart_path = f"backtest_charts/{symbol}_{interval}_adaptive_equity.png"
        plt.savefig(equity_chart_path)
        logger.info(f"Đã lưu đồ thị đường cong vốn vào '{equity_chart_path}'")
        
        # Lưu lịch sử giao dịch
        trades_df = pd.DataFrame(trades)
        trades_csv_path = f"backtest_results/{symbol}_{interval}_adaptive_trades.csv"
        trades_df.to_csv(trades_csv_path, index=False)
        logger.info(f"Đã lưu lịch sử giao dịch vào '{trades_csv_path}'")
        
        # Lưu kết quả backtest
        results = {
            'symbol': symbol,
            'interval': interval,
            'initial_balance': initial_balance,
            'final_balance': balance,
            'profit': balance - initial_balance,
            'profit_percentage': (balance - initial_balance) / initial_balance * 100,
            'total_trades': len(trades),
            'win_trades': len(win_trades),
            'lose_trades': len(lose_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'strategy': 'adaptive',
            'leverage': leverage,
            'risk_percentage': risk_percentage,
            'use_adaptive_risk': use_adaptive_risk,
            'regime_performance': regime_performance,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        results_json_path = f"backtest_results/{symbol}_{interval}_adaptive_results.json"
        with open(results_json_path, 'w') as f:
            json.dump(results, f, indent=4)
        logger.info(f"Đã lưu kết quả backtest vào '{results_json_path}'")
        
        # Vẽ đồ thị tín hiệu
        plt.figure(figsize=(12, 8))
        
        # Vẽ biểu đồ giá và các chỉ báo
        ax1 = plt.subplot(211)
        ax1.plot(df.index, df['close'], label='Giá đóng cửa')
        ax1.plot(df.index, df['sma20'], label='SMA 20', alpha=0.7)
        ax1.plot(df.index, df['upper_band'], 'r--', label='Upper Band', alpha=0.5)
        ax1.plot(df.index, df['lower_band'], 'g--', label='Lower Band', alpha=0.5)
        
        # Đánh dấu tín hiệu mua/bán
        for i in range(start_idx, len(df)):
            if df.iloc[i]['signal'] == 1:
                ax1.scatter(df.index[i], df.iloc[i]['close'], marker='^', color='g')
            elif df.iloc[i]['signal'] == -1:
                ax1.scatter(df.index[i], df.iloc[i]['close'], marker='v', color='r')
        
        # Đánh dấu chuyển đổi chế độ thị trường
        for change in regime_changes:
            ax1.axvline(x=change['date'], color='r', linestyle='--', alpha=0.5)
            ax1.text(change['date'], min(df['close']) * 0.95, change['regime'], rotation=90)
        
        # Các giao dịch đã thực hiện
        for trade in trades:
            if trade['side'] == 'BUY':
                ax1.scatter(trade['entry_date'], trade['entry_price'], marker='^', color='g', s=100)
                ax1.scatter(trade['exit_date'], trade['exit_price'], marker='o', color='g' if trade['pnl_amount'] > 0 else 'r', s=100)
                ax1.plot([trade['entry_date'], trade['exit_date']], [trade['entry_price'], trade['exit_price']], 'g-' if trade['pnl_amount'] > 0 else 'r-')
            else:  # SELL
                ax1.scatter(trade['entry_date'], trade['entry_price'], marker='v', color='r', s=100)
                ax1.scatter(trade['exit_date'], trade['exit_price'], marker='o', color='g' if trade['pnl_amount'] > 0 else 'r', s=100)
                ax1.plot([trade['entry_date'], trade['exit_date']], [trade['entry_price'], trade['exit_price']], 'g-' if trade['pnl_amount'] > 0 else 'r-')
        
        ax1.set_title(f'Tín hiệu giao dịch - ADAPTIVE ({symbol} {interval})')
        ax1.legend()
        ax1.grid(True)
        
        # Vẽ chỉ báo RSI
        ax2 = plt.subplot(212, sharex=ax1)
        ax2.plot(df.index, df['rsi'], 'purple')
        ax2.axhline(y=70, color='r', linestyle='--')
        ax2.axhline(y=30, color='g', linestyle='--')
        ax2.axhline(y=50, color='gray', linestyle='--')
        ax2.set_title('RSI (14)')
        ax2.set_ylim(0, 100)
        ax2.grid(True)
        
        # Giới hạn phạm vi thời gian hiển thị
        ax1.set_xlim(df.index[start_idx], df.index[-1])
        
        plt.tight_layout()
        signals_chart_path = f"backtest_charts/{symbol}_{interval}_adaptive_signals.png"
        plt.savefig(signals_chart_path)
        logger.info(f"Đã lưu đồ thị tín hiệu vào '{signals_chart_path}'")
        
        plt.close('all')
    else:
        logger.warning("Không có giao dịch nào được thực hiện trong quá trình backtest")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Backtest thích ứng với phát hiện chế độ thị trường')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã cặp giao dịch')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu')
    parser.add_argument('--leverage', type=int, default=3, help='Đòn bẩy')
    parser.add_argument('--risk', type=float, default=1.0, help='Phần trăm rủi ro')
    parser.add_argument('--stop_loss', type=float, default=7.0, help='Phần trăm stop loss')
    parser.add_argument('--take_profit', type=float, default=15.0, help='Phần trăm take profit')
    parser.add_argument('--adaptive_risk', action='store_true', help='Sử dụng quản lý rủi ro thích ứng')
    parser.add_argument('--data_dir', type=str, default='test_data', help='Thư mục dữ liệu')
    
    args = parser.parse_args()
    
    run_adaptive_backtest(
        symbol=args.symbol,
        interval=args.interval,
        initial_balance=args.balance,
        leverage=args.leverage,
        risk_percentage=args.risk,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit,
        use_adaptive_risk=args.adaptive_risk,
        data_dir=args.data_dir
    )

if __name__ == "__main__":
    main()