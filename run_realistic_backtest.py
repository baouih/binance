#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BACKTEST THỰC TẾ CHO HỆ THỐNG GIAO DỊCH TỰ ĐỘNG
------------------------------------------------
- Mô phỏng chính xác cách bot sẽ hoạt động trong thực tế
- Bot tự động phân tích thị trường và chọn chiến lược phù hợp
- Tích hợp tất cả các thành phần (phân tích, quản lý rủi ro, đa chiến lược)
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('realistic_backtest.log')
    ]
)

logger = logging.getLogger('realistic_backtest')

class MarketAnalyzer:
    """
    Phân tích trạng thái thị trường và các tín hiệu kỹ thuật
    """
    
    def __init__(self, price_data, analysis_window=50):
        """
        Khởi tạo analyzer
        
        Args:
            price_data (pd.DataFrame): Dữ liệu giá đã tải
            analysis_window (int): Số nến để phân tích
        """
        self.data = price_data
        self.window = analysis_window
        
        # Chuẩn hoá tên cột - chuyển đổi từ chữ thường sang chữ hoa đầu tiên
        column_mapping = {}
        for col in self.data.columns:
            if col in ['open', 'high', 'low', 'close', 'volume']:
                column_mapping[col] = col.capitalize()
        
        if column_mapping:
            self.data = self.data.rename(columns=column_mapping)
        
        # Tính toán các chỉ báo cơ bản
        self._calculate_indicators()
        
        logger.info("Đã khởi tạo Market Analyzer")
    
    def _calculate_indicators(self):
        """
        Tính toán các chỉ báo kỹ thuật trên toàn bộ dữ liệu
        """
        df = self.data
        
        # 1. Tính Moving Averages
        df['sma20'] = df['Close'].rolling(window=20).mean()
        df['sma50'] = df['Close'].rolling(window=50).mean()
        df['sma100'] = df['Close'].rolling(window=100).mean()
        df['ema9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # 2. Tính RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. Tính MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 4. Tính Bollinger Bands
        df['std20'] = df['Close'].rolling(window=20).std()
        df['upper_band'] = df['sma20'] + (df['std20'] * 2)
        df['lower_band'] = df['sma20'] - (df['std20'] * 2)
        
        # 5. Tính ATR
        tr1 = df['High'] - df['Low']
        tr2 = abs(df['High'] - df['Close'].shift())
        tr3 = abs(df['Low'] - df['Close'].shift())
        df['tr'] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # 6. Tính Stochastic
        df['lowest_14'] = df['Low'].rolling(window=14).min()
        df['highest_14'] = df['High'].rolling(window=14).max()
        df['%K'] = (df['Close'] - df['lowest_14']) / (df['highest_14'] - df['lowest_14']) * 100
        df['%D'] = df['%K'].rolling(window=3).mean()
        
        # 7. Trend Strength
        df['trend_angle'] = np.degrees(np.arctan(df['sma20'].diff(20) / 20))
        df['adx'] = self._calculate_adx(df)
        
        # 8. Volatility ratio
        df['volatility_ratio'] = df['atr'] / df['Close'] * 100
        
        # 9. Volume metrics
        df['volume_sma20'] = df['Volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma20']
        
        logger.info(f"Đã tính toán {len(df.columns) - 5} chỉ báo kỹ thuật")
    
    def _calculate_adx(self, df, period=14):
        """
        Tính chỉ báo ADX (Average Directional Index)
        """
        # Chuẩn bị
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # +DM và -DM
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        # Lọc +DM và -DM
        plus_dm = plus_dm.mask((plus_dm < 0) | (plus_dm < minus_dm.abs()), 0)
        minus_dm = minus_dm.mask((minus_dm > 0) | (minus_dm.abs() < plus_dm), 0)
        minus_dm = minus_dm.abs()
        
        # Tính TR
        tr = pd.DataFrame({
            'tr1': high - low,
            'tr2': (high - close.shift(1)).abs(),
            'tr3': (low - close.shift(1)).abs()
        }).max(axis=1)
        
        # Tính toán +DI và -DI
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        # Tính DX và ADX
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        adx = dx.rolling(period).mean()
        
        return adx
    
    def detect_market_condition(self, current_idx=None):
        """
        Phát hiện điều kiện thị trường hiện tại
        
        Args:
            current_idx (int): Vị trí hiện tại trong dữ liệu, mặc định là vị trí cuối cùng
            
        Returns:
            str: Trạng thái thị trường ("BULL", "BEAR", "SIDEWAYS", "VOLATILE")
        """
        if current_idx is None:
            current_idx = len(self.data) - 1
        
        if current_idx < self.window:
            return "NEUTRAL"  # Không đủ dữ liệu để phân tích
        
        # Lấy dữ liệu trong cửa sổ phân tích
        window_data = self.data.iloc[current_idx - self.window:current_idx + 1]
        
        # Tính % thay đổi giá
        price_change = (window_data['Close'].iloc[-1] - window_data['Close'].iloc[0]) / window_data['Close'].iloc[0] * 100
        
        # Đo lường biến động
        volatility = window_data['volatility_ratio'].iloc[-1]
        
        # Phát hiện xu hướng (trend)
        trend_strength = abs(window_data['trend_angle'].iloc[-1])
        adx_value = window_data['adx'].iloc[-1]
        
        # Kiểm tra nếu thị trường có biến động lớn
        if volatility > 3.0:
            return "VOLATILE"
        
        # Kiểm tra xu hướng tăng/giảm dựa trên giá, góc và ADX
        if price_change > 5 and trend_strength > 3 and adx_value > 25:
            return "BULL"
        elif price_change < -5 and trend_strength > 3 and adx_value > 25:
            return "BEAR"
        
        # Mặc định là thị trường đi ngang nếu không thỏa điều kiện khác
        return "SIDEWAYS"
    
    def get_indicators_snapshot(self, current_idx=None):
        """
        Lấy snapshot các chỉ báo tại vị trí hiện tại
        
        Args:
            current_idx (int): Vị trí trong dữ liệu
            
        Returns:
            dict: Thông tin chỉ báo
        """
        if current_idx is None:
            current_idx = len(self.data) - 1
        
        if current_idx >= len(self.data) or current_idx < 0:
            logger.error(f"Index {current_idx} nằm ngoài phạm vi dữ liệu (0-{len(self.data)-1})")
            return {}
        
        row = self.data.iloc[current_idx]
        
        return {
            'price': row['Close'],
            'rsi': row['rsi'] if 'rsi' in row else None,
            'macd': row['macd'] if 'macd' in row else None,
            'macd_signal': row['macd_signal'] if 'macd_signal' in row else None,
            'atr': row['atr'] if 'atr' in row else None,
            'bollinger_width': (row['upper_band'] - row['lower_band']) / row['sma20'] * 100 if 'upper_band' in row else None,
            'is_above_sma50': row['Close'] > row['sma50'] if 'sma50' in row else None,
            'volume_ratio': row['volume_ratio'] if 'volume_ratio' in row else None,
            'adx': row['adx'] if 'adx' in row else None,
            'timestamp': self.data.index[current_idx] if isinstance(self.data.index, pd.DatetimeIndex) else None
        }

class AdaptiveRiskManager:
    """
    Quản lý rủi ro thích ứng theo điều kiện thị trường
    """
    
    def __init__(self):
        """
        Khởi tạo bộ quản lý rủi ro
        """
        # Ánh xạ điều kiện thị trường tới mức rủi ro tối ưu
        self.market_to_risk = {
            "BULL": 0.15,     # Thị trường tăng: mức rủi ro vừa phải
            "BEAR": 0.10,     # Thị trường giảm: mức rủi ro thấp
            "SIDEWAYS": 0.10, # Thị trường đi ngang: mức rủi ro thấp (tối ưu cho sideways strategy)
            "VOLATILE": 0.05,  # Thị trường biến động: mức rủi ro rất thấp
            "NEUTRAL": 0.10    # Chế độ mặc định: mức rủi ro thấp
        }
        
        # Phân bổ vốn tối đa cho mỗi mức rủi ro (% tài khoản)
        self.risk_allocation = {
            0.05: 0.10,  # 10% vốn cho ultra_conservative (5%)
            0.10: 0.30,  # 30% vốn cho conservative (10%) 
            0.15: 0.30,  # 30% vốn cho moderate (15%)
            0.20: 0.20,  # 20% vốn cho aggressive (20%)
            0.25: 0.10   # 10% vốn cho high_risk (25%)
        }
        
        # Giới hạn số vị thế đồng thời
        self.max_positions = {
            0.05: 3,   # Tối đa 3 vị thế đồng thời với rủi ro 5%
            0.10: 5,   # Tối đa 5 vị thế đồng thời với rủi ro 10%
            0.15: 4,   # Tối đa 4 vị thế đồng thời với rủi ro 15%
            0.20: 2,   # Tối đa 2 vị thế đồng thời với rủi ro 20%
            0.25: 1    # Tối đa 1 vị thế đồng thời với rủi ro 25%
        }
        
        # Ngưỡng bảo vệ tài khoản
        self.account_protection = {
            'max_drawdown': 0.25,  # Đóng bớt vị thế nếu drawdown vượt quá 25%
            'max_risk_exposure': 0.40,  # Tổng mức rủi ro tối đa là 40% vốn
            'max_positions_total': 10  # Tổng số vị thế tối đa
        }
        
        logger.info("Đã khởi tạo Adaptive Risk Manager")
    
    def get_optimal_risk(self, market_condition, indicators=None):
        """
        Lấy mức rủi ro tối ưu dựa trên điều kiện thị trường và chỉ báo
        
        Args:
            market_condition (str): Điều kiện thị trường
            indicators (dict): Các chỉ báo kỹ thuật
            
        Returns:
            float: Mức rủi ro tối ưu (0.05 - 0.25)
        """
        # Lấy mức rủi ro cơ bản dựa trên điều kiện thị trường
        base_risk = self.market_to_risk.get(market_condition, 0.10)
        
        # Điều chỉnh mức rủi ro dựa trên chỉ báo nếu có
        if indicators:
            # Thêm logic điều chỉnh tại đây nếu cần
            # Ví dụ: giảm rủi ro nếu RSI quá cao hoặc quá thấp
            rsi = indicators.get('rsi')
            if rsi and (rsi > 75 or rsi < 25):
                base_risk = max(0.05, base_risk * 0.8)  # Giảm 20% rủi ro
            
            # Giảm rủi ro nếu biến động cao (bollinger band rộng)
            bollinger_width = indicators.get('bollinger_width')
            if bollinger_width and bollinger_width > 6.0:
                base_risk = max(0.05, base_risk * 0.8)
        
        logger.debug(f"Mức rủi ro tối ưu cho thị trường {market_condition}: {base_risk}")
        return base_risk
    
    def calculate_position_size(self, risk_level, entry_price, stop_loss, account_balance):
        """
        Tính kích thước vị thế dựa trên mức rủi ro và khoảng stop loss
        
        Args:
            risk_level (float): Mức rủi ro (0.05 - 0.25)
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            account_balance (float): Số dư tài khoản
            
        Returns:
            float: Kích thước vị thế (đơn vị)
        """
        # Tính % thua lỗ nếu dừng tại stop loss
        stop_loss_pct = abs(entry_price - stop_loss) / entry_price
        
        # Tính số tiền tối đa có thể rủi ro
        max_risk_amount = account_balance * risk_level
        
        # Tính kích thước vị thế (đơn vị)
        position_size = max_risk_amount / (entry_price * stop_loss_pct)
        
        # Tính giá trị vị thế
        position_value = position_size * entry_price
        
        # Giới hạn theo phân bổ vốn cho mức rủi ro này
        max_allocation = account_balance * self.risk_allocation[risk_level]
        if position_value > max_allocation:
            position_size = max_allocation / entry_price
        
        return position_size
    
    def should_open_position(self, risk_level, active_positions, account_balance, account_equity):
        """
        Quyết định có nên mở vị thế mới không
        
        Args:
            risk_level (float): Mức rủi ro dự định
            active_positions (list): Danh sách vị thế đang mở
            account_balance (float): Số dư tài khoản
            account_equity (float): Tổng tài sản
            
        Returns:
            bool: True nếu nên mở vị thế, False nếu không
        """
        # Đếm số vị thế đang mở cho mức rủi ro này
        positions_at_risk = sum(1 for p in active_positions if p.get('risk_level') == risk_level)
        
        # Tính tổng phơi nhiễm rủi ro hiện tại
        total_risk_exposure = 0
        for p in active_positions:
            if 'risk_level' in p and 'value' in p:
                total_risk_exposure += p['risk_level'] * p['value']
            elif 'risk_level' in p and 'position_value' in p:
                total_risk_exposure += p['risk_level'] * p['position_value']
        
        total_risk_exposure = total_risk_exposure / account_balance if account_balance > 0 else 0
        
        # Tính drawdown hiện tại
        drawdown = (account_balance - account_equity) / account_balance if account_balance > 0 else 0
        
        # Kiểm tra các điều kiện
        max_positions_reached = positions_at_risk >= self.max_positions[risk_level]
        risk_exposure_too_high = total_risk_exposure >= self.account_protection['max_risk_exposure']
        drawdown_too_high = drawdown >= self.account_protection['max_drawdown']
        total_positions_too_high = len(active_positions) >= self.account_protection['max_positions_total']
        
        # Quyết định
        should_open = not (max_positions_reached or risk_exposure_too_high or drawdown_too_high or total_positions_too_high)
        
        if not should_open:
            reason = "không rõ"
            if max_positions_reached:
                reason = f"đã đạt giới hạn vị thế cho mức rủi ro {risk_level}"
            elif risk_exposure_too_high:
                reason = f"tổng phơi nhiễm rủi ro quá cao ({total_risk_exposure:.2f})"
            elif drawdown_too_high:
                reason = f"drawdown quá lớn ({drawdown:.2f})"
            elif total_positions_too_high:
                reason = f"tổng số vị thế quá nhiều ({len(active_positions)})"
            
            logger.debug(f"Không mở vị thế mới (risk={risk_level}): {reason}")
        
        return should_open
    
    def should_reduce_risk(self, active_positions, account_balance, account_equity):
        """
        Kiểm tra xem có nên giảm rủi ro không (đóng các vị thế có rủi ro cao)
        
        Args:
            active_positions (list): Danh sách vị thế đang mở
            account_balance (float): Số dư tài khoản
            account_equity (float): Tổng tài sản
            
        Returns:
            list: Danh sách vị thế nên đóng
        """
        # Tính drawdown hiện tại
        drawdown = (account_balance - account_equity) / account_balance if account_balance > 0 else 0
        
        positions_to_close = []
        
        # Nếu drawdown quá cao, bắt đầu đóng vị thế có rủi ro cao nhất
        if drawdown > self.account_protection['max_drawdown'] * 0.8:  # 80% ngưỡng bảo vệ
            # Sắp xếp vị thế theo mức rủi ro giảm dần
            # Sử dụng get() để tránh KeyError nếu position không có risk_level
            sorted_positions = sorted(active_positions, key=lambda p: p.get('risk_level', 0.05), reverse=True)
            
            # Đóng từng vị thế có rủi ro cao nhất cho đến khi đạt mức an toàn
            for pos in sorted_positions:
                positions_to_close.append(pos)
                
                # Tính lại drawdown nếu đóng các vị thế này
                new_equity = account_equity
                for p in positions_to_close:
                    # Ước tính P/L nếu đóng vị thế
                    new_equity += p.get('unrealized_pnl', 0)
                
                new_drawdown = (account_balance - new_equity) / account_balance if account_balance > 0 else 0
                
                # Nếu drawdown đã giảm xuống mức an toàn thì dừng
                if new_drawdown < self.account_protection['max_drawdown'] * 0.6:  # 60% ngưỡng bảo vệ
                    break
        
        if positions_to_close:
            logger.info(f"Cần giảm rủi ro: đóng {len(positions_to_close)} vị thế có rủi ro cao")
        
        return positions_to_close

class StrategySelector:
    """
    Bộ chọn chiến lược dựa trên điều kiện thị trường
    """
    
    def __init__(self):
        """
        Khởi tạo bộ chọn chiến lược
        """
        # Ánh xạ điều kiện thị trường tới chiến lược phù hợp
        self.market_to_strategy = {
            "BULL": "trend_following",
            "BEAR": "counter_trend",
            "SIDEWAYS": "sideways",
            "VOLATILE": "range_trading",
            "NEUTRAL": "sideways"  # Mặc định dùng sideways cho trường hợp trung tính
        }
        
        logger.info("Đã khởi tạo Strategy Selector")
    
    def select_strategy(self, market_condition, indicators=None):
        """
        Chọn chiến lược phù hợp nhất với điều kiện thị trường
        
        Args:
            market_condition (str): Điều kiện thị trường
            indicators (dict): Các chỉ báo kỹ thuật
            
        Returns:
            str: Tên chiến lược phù hợp
        """
        base_strategy = self.market_to_strategy.get(market_condition, "sideways")
        
        # Điều chỉnh dựa trên chỉ báo nếu cần
        if indicators:
            # Ví dụ: nếu thị trường BULL nhưng RSI > 75, chuyển từ trend_following sang range_trading
            if base_strategy == "trend_following" and indicators.get('rsi', 0) > 75:
                base_strategy = "range_trading"
            
            # Ví dụ: nếu thị trường SIDEWAYS nhưng ADX > 30, chuyển từ sideways sang counter_trend
            if base_strategy == "sideways" and indicators.get('adx', 0) > 30:
                base_strategy = "counter_trend"
        
        logger.debug(f"Chiến lược được chọn cho thị trường {market_condition}: {base_strategy}")
        return base_strategy

class SignalGenerator:
    """
    Tạo tín hiệu giao dịch dựa trên chiến lược được chọn
    """
    
    def __init__(self, data):
        """
        Khởi tạo bộ tạo tín hiệu
        
        Args:
            data (pd.DataFrame): Dữ liệu giá đã tính toán các chỉ báo
        """
        self.data = data
        logger.info("Đã khởi tạo Signal Generator")
    
    def generate_trend_following_signal(self, current_idx, risk_level):
        """
        Tạo tín hiệu theo xu hướng (trend following)
        
        Args:
            current_idx (int): Vị trí hiện tại trong dữ liệu
            risk_level (float): Mức rủi ro
            
        Returns:
            dict: Tín hiệu giao dịch hoặc None
        """
        if current_idx < 2:
            return None
        
        row = self.data.iloc[current_idx]
        prev_row = self.data.iloc[current_idx - 1]
        
        # Tín hiệu mua (LONG)
        long_signal = False
        long_reason = []
        
        # Điều kiện 1: Giá vượt lên trên SMA50
        if prev_row['Close'] <= prev_row['sma50'] and row['Close'] > row['sma50']:
            long_signal = True
            long_reason.append(f"Giá vượt lên trên SMA50 ({row['Close']:.2f} > {row['sma50']:.2f})")
        
        # Điều kiện 2: MACD cắt lên đường tín hiệu khi MACD < 0
        if prev_row['macd'] < prev_row['macd_signal'] and row['macd'] >= row['macd_signal'] and row['macd'] < 0:
            long_signal = True
            long_reason.append(f"MACD cắt lên đường tín hiệu ({row['macd']:.6f} >= {row['macd_signal']:.6f})")
        
        # Điều kiện 3: RSI tăng từ vùng quá bán
        if prev_row['rsi'] < 30 and row['rsi'] >= 30:
            long_signal = True
            long_reason.append(f"RSI tăng từ vùng quá bán ({row['rsi']:.2f})")
        
        # Tạo tín hiệu LONG nếu thỏa điều kiện
        if long_signal:
            # Tính SL và TP
            sl_factor = self._get_sl_factor(risk_level)
            tp_factor = self._get_tp_factor(risk_level)
            
            stop_loss = row['Close'] - (row['atr'] * sl_factor)
            take_profit = row['Close'] + (row['atr'] * tp_factor)
            
            return {
                'type': 'LONG',
                'price': row['Close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': long_reason,
                'strategy': 'trend_following'
            }
        
        # Tín hiệu bán (SHORT)
        short_signal = False
        short_reason = []
        
        # Điều kiện 1: Giá phá xuống dưới SMA50
        if prev_row['Close'] >= prev_row['sma50'] and row['Close'] < row['sma50']:
            short_signal = True
            short_reason.append(f"Giá phá xuống dưới SMA50 ({row['Close']:.2f} < {row['sma50']:.2f})")
        
        # Điều kiện 2: MACD cắt xuống đường tín hiệu khi MACD > 0
        if prev_row['macd'] > prev_row['macd_signal'] and row['macd'] <= row['macd_signal'] and row['macd'] > 0:
            short_signal = True
            short_reason.append(f"MACD cắt xuống đường tín hiệu ({row['macd']:.6f} <= {row['macd_signal']:.6f})")
        
        # Điều kiện 3: RSI giảm từ vùng quá mua
        if prev_row['rsi'] > 70 and row['rsi'] <= 70:
            short_signal = True
            short_reason.append(f"RSI giảm từ vùng quá mua ({row['rsi']:.2f})")
        
        # Tạo tín hiệu SHORT nếu thỏa điều kiện
        if short_signal:
            sl_factor = self._get_sl_factor(risk_level)
            tp_factor = self._get_tp_factor(risk_level)
            
            stop_loss = row['Close'] + (row['atr'] * sl_factor)
            take_profit = row['Close'] - (row['atr'] * tp_factor)
            
            return {
                'type': 'SHORT',
                'price': row['Close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': short_reason,
                'strategy': 'trend_following'
            }
        
        return None
    
    def generate_counter_trend_signal(self, current_idx, risk_level):
        """
        Tạo tín hiệu đảo chiều xu hướng (counter trend)
        
        Args:
            current_idx (int): Vị trí hiện tại trong dữ liệu
            risk_level (float): Mức rủi ro
            
        Returns:
            dict: Tín hiệu giao dịch hoặc None
        """
        if current_idx < 2:
            return None
        
        row = self.data.iloc[current_idx]
        prev_row = self.data.iloc[current_idx - 1]
        
        # Tín hiệu mua (LONG) - Chống xu hướng giảm
        long_signal = False
        long_reason = []
        
        # Điều kiện 1: RSI quá bán
        if row['rsi'] < 25:
            long_signal = True
            long_reason.append(f"RSI trong vùng quá bán sâu ({row['rsi']:.2f})")
        
        # Điều kiện 2: Giá chạm Bollinger Band dưới
        if row['Close'] <= row['lower_band']:
            long_signal = True
            long_reason.append(f"Giá chạm Bollinger Band dưới ({row['Close']:.2f} <= {row['lower_band']:.2f})")
        
        # Điều kiện 3: Stoch %K chạm đáy và bắt đầu đi lên
        if row['%K'] < 20 and row['%K'] > prev_row['%K']:
            long_signal = True
            long_reason.append(f"Stochastic %K trong vùng quá bán và đi lên ({row['%K']:.2f})")
        
        # Tạo tín hiệu LONG nếu thỏa điều kiện
        if long_signal:
            # Counter trend cần stop loss chặt hơn
            sl_factor = self._get_sl_factor(risk_level) * 0.7  # Chặt hơn 30%
            tp_factor = self._get_tp_factor(risk_level) * 0.8  # Thận trọng hơn 20%
            
            stop_loss = row['Close'] - (row['atr'] * sl_factor)
            take_profit = row['Close'] + (row['atr'] * tp_factor)
            
            return {
                'type': 'LONG',
                'price': row['Close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': long_reason,
                'strategy': 'counter_trend'
            }
        
        # Tín hiệu bán (SHORT) - Chống xu hướng tăng
        short_signal = False
        short_reason = []
        
        # Điều kiện 1: RSI quá mua
        if row['rsi'] > 75:
            short_signal = True
            short_reason.append(f"RSI trong vùng quá mua sâu ({row['rsi']:.2f})")
        
        # Điều kiện 2: Giá chạm Bollinger Band trên
        if row['Close'] >= row['upper_band']:
            short_signal = True
            short_reason.append(f"Giá chạm Bollinger Band trên ({row['Close']:.2f} >= {row['upper_band']:.2f})")
        
        # Điều kiện 3: Stoch %K chạm đỉnh và bắt đầu đi xuống
        if row['%K'] > 80 and row['%K'] < prev_row['%K']:
            short_signal = True
            short_reason.append(f"Stochastic %K trong vùng quá mua và đi xuống ({row['%K']:.2f})")
        
        # Tạo tín hiệu SHORT nếu thỏa điều kiện
        if short_signal:
            sl_factor = self._get_sl_factor(risk_level) * 0.7
            tp_factor = self._get_tp_factor(risk_level) * 0.8
            
            stop_loss = row['Close'] + (row['atr'] * sl_factor)
            take_profit = row['Close'] - (row['atr'] * tp_factor)
            
            return {
                'type': 'SHORT',
                'price': row['Close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': short_reason,
                'strategy': 'counter_trend'
            }
        
        return None
    
    def generate_sideways_signal(self, current_idx, risk_level):
        """
        Tạo tín hiệu cho thị trường đi ngang (sideways)
        
        Args:
            current_idx (int): Vị trí hiện tại trong dữ liệu
            risk_level (float): Mức rủi ro
            
        Returns:
            dict: Tín hiệu giao dịch hoặc None
        """
        if current_idx < 20:
            return None
        
        # Kiểm tra xem thị trường có thực sự đi ngang không
        window_data = self.data.iloc[current_idx - 20:current_idx + 1]
        highest = window_data['High'].max()
        lowest = window_data['Low'].min()
        
        # % chênh lệch giữa cao nhất và thấp nhất
        range_pct = (highest - lowest) / lowest
        if range_pct > 0.05:  # Nếu biên độ > 5%, không phải thị trường đi ngang
            return None
        
        row = self.data.iloc[current_idx]
        
        # Tín hiệu mua (LONG) - Khi giá gần chạm đáy kênh
        if row['Close'] < row['lower_band'] + (row['atr'] * 0.5):
            # Chiến lược sideways sử dụng Bollinger bands hẹp hơn và ATR
            sl_factor = 1.0  # Stop loss gần hơn
            tp_factor = 1.5  # Take profit cũng gần hơn
            
            stop_loss = row['Close'] - (row['atr'] * sl_factor)
            take_profit = row['Close'] + (row['atr'] * tp_factor)
            
            return {
                'type': 'LONG',
                'price': row['Close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': [f"Giá gần chạm đáy kênh Bollinger ({row['Close']:.2f} < {row['lower_band'] + (row['atr'] * 0.5):.2f})"],
                'strategy': 'sideways'
            }
        
        # Tín hiệu bán (SHORT) - Khi giá gần chạm đỉnh kênh
        if row['Close'] > row['upper_band'] - (row['atr'] * 0.5):
            sl_factor = 1.0
            tp_factor = 1.5
            
            stop_loss = row['Close'] + (row['atr'] * sl_factor)
            take_profit = row['Close'] - (row['atr'] * tp_factor)
            
            return {
                'type': 'SHORT',
                'price': row['Close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': [f"Giá gần chạm đỉnh kênh Bollinger ({row['Close']:.2f} > {row['upper_band'] - (row['atr'] * 0.5):.2f})"],
                'strategy': 'sideways'
            }
        
        return None
    
    def generate_range_trading_signal(self, current_idx, risk_level):
        """
        Tạo tín hiệu cho thị trường biến động mạnh (range trading)
        
        Args:
            current_idx (int): Vị trí hiện tại trong dữ liệu
            risk_level (float): Mức rủi ro
            
        Returns:
            dict: Tín hiệu giao dịch hoặc None
        """
        if current_idx < 5:
            return None
        
        row = self.data.iloc[current_idx]
        
        # Thị trường biến động mạnh, chỉ giao dịch khi có xác nhận mạnh
        # Tín hiệu mua (LONG)
        if row['rsi'] < 20 and row['Close'] < row['lower_band'] * 0.98:
            # Range trading cần stop loss xa hơn để tránh bị đá
            sl_factor = self._get_sl_factor(risk_level) * 1.5  # Xa hơn 50%
            tp_factor = self._get_tp_factor(risk_level) * 0.7  # Gần hơn 30%
            
            stop_loss = row['Close'] - (row['atr'] * sl_factor)
            take_profit = row['Close'] + (row['atr'] * tp_factor)
            
            return {
                'type': 'LONG',
                'price': row['Close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': [
                    f"RSI trong vùng quá bán rất sâu ({row['rsi']:.2f})",
                    f"Giá dưới Bollinger Band dưới ({row['Close']:.2f} < {row['lower_band']:.2f})"
                ],
                'strategy': 'range_trading'
            }
        
        # Tín hiệu bán (SHORT)
        if row['rsi'] > 80 and row['Close'] > row['upper_band'] * 1.02:
            sl_factor = self._get_sl_factor(risk_level) * 1.5
            tp_factor = self._get_tp_factor(risk_level) * 0.7
            
            stop_loss = row['Close'] + (row['atr'] * sl_factor)
            take_profit = row['Close'] - (row['atr'] * tp_factor)
            
            return {
                'type': 'SHORT',
                'price': row['Close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': [
                    f"RSI trong vùng quá mua rất sâu ({row['rsi']:.2f})",
                    f"Giá trên Bollinger Band trên ({row['Close']:.2f} > {row['upper_band']:.2f})"
                ],
                'strategy': 'range_trading'
            }
        
        return None
    
    def generate_signal(self, strategy, current_idx, risk_level):
        """
        Tạo tín hiệu giao dịch dựa trên chiến lược đã chọn
        
        Args:
            strategy (str): Chiến lược đã chọn
            current_idx (int): Vị trí hiện tại trong dữ liệu
            risk_level (float): Mức rủi ro
            
        Returns:
            dict: Tín hiệu giao dịch hoặc None
        """
        if strategy == "trend_following":
            return self.generate_trend_following_signal(current_idx, risk_level)
        elif strategy == "counter_trend":
            return self.generate_counter_trend_signal(current_idx, risk_level)
        elif strategy == "sideways":
            return self.generate_sideways_signal(current_idx, risk_level)
        elif strategy == "range_trading":
            return self.generate_range_trading_signal(current_idx, risk_level)
        else:
            logger.warning(f"Chiến lược không được hỗ trợ: {strategy}")
            return None
    
    def _get_sl_factor(self, risk_level):
        """
        Lấy hệ số stop loss dựa trên mức rủi ro
        
        Args:
            risk_level (float): Mức rủi ro
            
        Returns:
            float: Hệ số stop loss
        """
        if risk_level <= 0.10:  # Rủi ro thấp
            return 2.0  # Stop loss xa hơn
        elif risk_level <= 0.15:  # Rủi ro trung bình
            return 1.5
        elif risk_level <= 0.20:  # Rủi ro cao
            return 1.0  # Stop loss gần hơn
        else:  # Rủi ro rất cao (> 0.20)
            return 0.8
    
    def _get_tp_factor(self, risk_level):
        """
        Lấy hệ số take profit dựa trên mức rủi ro
        
        Args:
            risk_level (float): Mức rủi ro
            
        Returns:
            float: Hệ số take profit
        """
        if risk_level <= 0.10:  # Rủi ro thấp
            return 1.5  # Take profit gần hơn
        elif risk_level <= 0.15:  # Rủi ro trung bình
            return 2.0
        elif risk_level <= 0.20:  # Rủi ro cao
            return 2.5  # Take profit xa hơn
        else:  # Rủi ro rất cao (> 0.20)
            return 3.0

class TradingSimulator:
    """
    Mô phỏng giao dịch dựa trên tín hiệu
    """
    
    def __init__(self, data, initial_balance=10000.0):
        """
        Khởi tạo bộ mô phỏng giao dịch
        
        Args:
            data (pd.DataFrame): Dữ liệu giá
            initial_balance (float): Số dư ban đầu
        """
        self.data = data
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions = []
        self.closed_positions = []
        self.equity_curve = [initial_balance]
        
        # Thống kê
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'long_trades': 0,
            'short_trades': 0,
            'max_drawdown': 0.0,
            'max_drawdown_pct': 0.0,
            'peak_balance': initial_balance,
            'final_balance': initial_balance,
            'total_profit': 0.0,
            'total_profit_pct': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'average_profit': 0.0,
            'average_loss': 0.0,
            'strategy_stats': {}
        }
        
        logger.info(f"Đã khởi tạo Trading Simulator với số dư {initial_balance:.2f}")
    
    def open_position(self, idx, signal, risk_level):
        """
        Mở vị thế mới
        
        Args:
            idx (int): Vị trí trong dữ liệu
            signal (dict): Tín hiệu giao dịch
            risk_level (float): Mức rủi ro
        """
        current_price = signal['price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        position_type = signal['type']
        strategy = signal['strategy']
        
        # Tính kích thước vị thế dựa trên rủi ro
        risk_amount = self.balance * risk_level
        stop_loss_pct = abs(current_price - stop_loss) / current_price
        position_size = risk_amount / (current_price * stop_loss_pct)
        position_value = position_size * current_price
        
        # Tạo vị thế mới
        position = {
            'entry_idx': idx,
            'entry_date': self.data.index[idx] if isinstance(self.data.index, pd.DatetimeIndex) else idx,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'type': position_type,
            'size': position_size,
            'value': position_value,
            'risk_level': risk_level,
            'strategy': strategy,
            'reason': signal['reason']
        }
        
        # Thêm vào danh sách vị thế đang mở
        self.positions.append(position)
        
        logger.debug(f"Mở vị thế {position_type} tại {current_price:.2f} (SL: {stop_loss:.2f}, TP: {take_profit:.2f}, Size: {position_size:.6f}, Risk: {risk_level})")
    
    def update_positions(self, idx):
        """
        Cập nhật và kiểm tra các vị thế đang mở
        
        Args:
            idx (int): Vị trí hiện tại trong dữ liệu
        """
        if idx >= len(self.data):
            return
        
        current_row = self.data.iloc[idx]
        current_price = current_row['Close']
        low_price = current_row['Low']
        high_price = current_row['High']
        
        # Tính toán tổng giá trị tài sản
        self.equity = self.balance
        
        # Cập nhật và kiểm tra từng vị thế
        i = 0
        while i < len(self.positions):
            position = self.positions[i]
            
            # Tính lợi nhuận chưa thực hiện
            unrealized_pnl = 0
            if position['type'] == 'LONG':
                unrealized_pnl = (current_price - position['entry_price']) * position['size']
            else:  # SHORT
                unrealized_pnl = (position['entry_price'] - current_price) * position['size']
            
            position['unrealized_pnl'] = unrealized_pnl
            position['unrealized_pnl_pct'] = unrealized_pnl / (position['value']) * 100
            
            # Cập nhật tổng tài sản
            self.equity += unrealized_pnl
            
            # Kiểm tra điều kiện đóng vị thế
            close_position = False
            exit_price = current_price
            exit_reason = "Unknown"
            
            # Kiểm tra stop loss
            if position['type'] == 'LONG' and low_price <= position['stop_loss']:
                close_position = True
                exit_price = position['stop_loss']
                exit_reason = "Stop Loss"
            elif position['type'] == 'SHORT' and high_price >= position['stop_loss']:
                close_position = True
                exit_price = position['stop_loss']
                exit_reason = "Stop Loss"
            
            # Kiểm tra take profit
            elif position['type'] == 'LONG' and high_price >= position['take_profit']:
                close_position = True
                exit_price = position['take_profit']
                exit_reason = "Take Profit"
            elif position['type'] == 'SHORT' and low_price <= position['take_profit']:
                close_position = True
                exit_price = position['take_profit']
                exit_reason = "Take Profit"
            
            # Đóng vị thế nếu cần
            if close_position:
                # Tính PnL thực tế
                if position['type'] == 'LONG':
                    realized_pnl = (exit_price - position['entry_price']) * position['size']
                else:  # SHORT
                    realized_pnl = (position['entry_price'] - exit_price) * position['size']
                
                realized_pnl_pct = realized_pnl / position['value'] * 100
                
                # Cập nhật số dư
                self.balance += realized_pnl
                
                # Thêm thông tin đóng vị thế
                position['exit_idx'] = idx
                position['exit_date'] = self.data.index[idx] if isinstance(self.data.index, pd.DatetimeIndex) else idx
                position['exit_price'] = exit_price
                position['realized_pnl'] = realized_pnl
                position['realized_pnl_pct'] = realized_pnl_pct
                position['exit_reason'] = exit_reason
                
                # Chuyển vị thế vào danh sách đã đóng
                self.closed_positions.append(position)
                self.positions.pop(i)
                
                # Cập nhật thống kê
                self.stats['total_trades'] += 1
                
                if realized_pnl > 0:
                    self.stats['winning_trades'] += 1
                elif realized_pnl < 0:
                    self.stats['losing_trades'] += 1
                else:
                    self.stats['break_even_trades'] += 1
                
                if position['type'] == 'LONG':
                    self.stats['long_trades'] += 1
                else:
                    self.stats['short_trades'] += 1
                
                # Cập nhật thống kê theo chiến lược
                strategy = position['strategy']
                if strategy not in self.stats['strategy_stats']:
                    self.stats['strategy_stats'][strategy] = {
                        'total': 0,
                        'win': 0,
                        'loss': 0,
                        'profit': 0.0,
                        'win_rate': 0.0
                    }
                
                self.stats['strategy_stats'][strategy]['total'] += 1
                if realized_pnl > 0:
                    self.stats['strategy_stats'][strategy]['win'] += 1
                    self.stats['strategy_stats'][strategy]['profit'] += realized_pnl
                else:
                    self.stats['strategy_stats'][strategy]['loss'] += 1
                    self.stats['strategy_stats'][strategy]['profit'] += realized_pnl
                
                # Cập nhật win_rate
                strat_stats = self.stats['strategy_stats'][strategy]
                strat_stats['win_rate'] = strat_stats['win'] / strat_stats['total'] * 100 if strat_stats['total'] > 0 else 0
                
                logger.debug(f"Đóng vị thế {position['type']} tại {exit_price:.2f}, P/L: {realized_pnl:.2f} ({realized_pnl_pct:.2f}%), Lý do: {exit_reason}")
            else:
                i += 1
        
        # Cập nhật đường equity
        self.equity_curve.append(self.equity)
        
        # Cập nhật peak và drawdown
        if self.equity > self.stats['peak_balance']:
            self.stats['peak_balance'] = self.equity
        
        current_drawdown = self.stats['peak_balance'] - self.equity
        current_drawdown_pct = current_drawdown / self.stats['peak_balance'] * 100 if self.stats['peak_balance'] > 0 else 0
        
        if current_drawdown > self.stats['max_drawdown']:
            self.stats['max_drawdown'] = current_drawdown
            self.stats['max_drawdown_pct'] = current_drawdown_pct
    
    def get_active_positions_at_risk_level(self, risk_level):
        """
        Lấy danh sách vị thế đang mở tại mức rủi ro nhất định
        
        Args:
            risk_level (float): Mức rủi ro
            
        Returns:
            list: Danh sách vị thế
        """
        return [p for p in self.positions if p['risk_level'] == risk_level]
    
    def calculate_final_stats(self):
        """
        Tính toán thống kê cuối cùng
        
        Returns:
            dict: Thống kê giao dịch
        """
        # Cập nhật thống kê chung
        self.stats['final_balance'] = self.balance
        self.stats['total_profit'] = self.balance - self.initial_balance
        self.stats['total_profit_pct'] = (self.balance - self.initial_balance) / self.initial_balance * 100 if self.initial_balance > 0 else 0
        
        # Tính win rate
        if self.stats['total_trades'] > 0:
            self.stats['win_rate'] = self.stats['winning_trades'] / self.stats['total_trades'] * 100
        
        # Tính profit factor
        if self.closed_positions:
            total_gain = sum(p['realized_pnl'] for p in self.closed_positions if p.get('realized_pnl', 0) > 0)
            total_loss = sum(abs(p['realized_pnl']) for p in self.closed_positions if p.get('realized_pnl', 0) < 0)
            self.stats['profit_factor'] = total_gain / total_loss if total_loss > 0 else float('inf')
        
        # Tính trung bình lợi nhuận/thua lỗ
        winning_trades = [p['realized_pnl'] for p in self.closed_positions if p.get('realized_pnl', 0) > 0]
        losing_trades = [p['realized_pnl'] for p in self.closed_positions if p.get('realized_pnl', 0) < 0]
        
        self.stats['average_profit'] = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        self.stats['average_loss'] = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        
        return self.stats
    
    def get_full_equity_curve(self):
        """
        Lấy đường equity đầy đủ
        
        Returns:
            list: Đường equity
        """
        return self.equity_curve
    
    def reset(self):
        """
        Reset bộ mô phỏng về trạng thái ban đầu
        """
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.positions = []
        self.closed_positions = []
        self.equity_curve = [self.initial_balance]
        
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'long_trades': 0,
            'short_trades': 0,
            'max_drawdown': 0.0,
            'max_drawdown_pct': 0.0,
            'peak_balance': self.initial_balance,
            'final_balance': self.initial_balance,
            'total_profit': 0.0,
            'total_profit_pct': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'average_profit': 0.0,
            'average_loss': 0.0,
            'strategy_stats': {}
        }
        
        logger.info("Đã reset Trading Simulator")

class RealisticBacktest:
    """
    Chạy backtest thực tế cho hệ thống giao dịch tự động
    """
    
    def __init__(self, symbol="BTCUSDT", timeframe="1h", test_period=90, initial_balance=10000.0):
        """
        Khởi tạo backtest
        
        Args:
            symbol (str): Cặp tiền
            timeframe (str): Khung thời gian
            test_period (int): Số ngày backtest
            initial_balance (float): Số dư ban đầu
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.test_period = test_period
        self.initial_balance = initial_balance
        
        # Khởi tạo các thành phần
        self.data = None
        self.market_analyzer = None
        self.risk_manager = AdaptiveRiskManager()
        self.strategy_selector = StrategySelector()
        self.signal_generator = None
        self.simulator = None
        
        # Đường dẫn lưu kết quả
        self.result_dir = Path("realistic_backtest_results")
        if not self.result_dir.exists():
            os.makedirs(self.result_dir)
        
        # Lưu nhật ký giao dịch và phân tích thị trường
        self.market_analysis_log = []
        self.strategy_selection_log = []
        self.signal_log = []
        self.trade_log = []
        
        logger.info(f"Đã khởi tạo Realistic Backtest cho {symbol} {timeframe} ({test_period} ngày)")
    
    def load_data(self):
        """
        Tải dữ liệu giá
        
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        # Đường dẫn file dữ liệu
        file_path = f"data/{self.symbol}_{self.timeframe}_backtest.csv"
        
        if not os.path.exists(file_path):
            # Thử lại với file dữ liệu thay thế
            file_path = f"data/{self.symbol}_{self.timeframe}.csv"
            if not os.path.exists(file_path):
                logger.error(f"Không tìm thấy file dữ liệu: {file_path}")
                return False
        
        try:
            # Tải dữ liệu
            df = pd.read_csv(file_path)
            
            # Chắc chắn chúng ta có các cột cần thiết
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Thiếu các cột cần thiết trong dữ liệu: {missing_cols}")
                return False
            
            # Sử dụng cột timestamp nếu có
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            # Kiểm tra và lọc dữ liệu trong khoảng thời gian test
            if isinstance(df.index, pd.DatetimeIndex):
                end_date = df.index.max()
                start_date = end_date - pd.Timedelta(days=self.test_period)
                df = df.loc[start_date:end_date]
            
            # Đảm bảo tên cột được chuẩn hóa
            column_mapping = {}
            for col in df.columns:
                if col in ['open', 'high', 'low', 'close', 'volume']:
                    column_mapping[col] = col.capitalize()
            
            if column_mapping:
                df = df.rename(columns=column_mapping)
            
            # Đảm bảo không có giá trị NaN
            df = df.dropna()
            
            # Lưu dữ liệu
            self.data = df
            
            # Khởi tạo các thành phần với dữ liệu đã tải
            self.market_analyzer = MarketAnalyzer(self.data)
            self.signal_generator = SignalGenerator(self.data)
            self.simulator = TradingSimulator(self.data, self.initial_balance)
            
            logger.info(f"Đã tải {len(df)} nến dữ liệu cho {self.symbol} {self.timeframe}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu: {str(e)}")
            return False
    
    def run_backtest(self, start_idx=None, end_idx=None):
        """
        Chạy backtest
        
        Args:
            start_idx (int): Vị trí bắt đầu backtest
            end_idx (int): Vị trí kết thúc backtest
            
        Returns:
            dict: Kết quả backtest
        """
        if self.data is None:
            logger.error("Chưa tải dữ liệu. Hãy gọi load_data() trước.")
            return None
        
        # Xác định vị trí bắt đầu và kết thúc
        if start_idx is None:
            # Đảm bảo đủ dữ liệu cho các chỉ báo (tối thiểu 20 nến)
            start_idx = min(20, len(self.data) // 3)
        
        if end_idx is None:
            # Giới hạn số lượng nến để tránh quá tải
            max_candles = 300
            if len(self.data) - start_idx > max_candles:
                end_idx = start_idx + max_candles
            else:
                end_idx = len(self.data) - 1
        
        logger.info(f"Bắt đầu backtest từ idx {start_idx} đến {end_idx} (tổng {end_idx - start_idx + 1} nến)")
        
        # Thiết lập bộ mô phỏng
        self.simulator.reset()
        
        # Điều kiện thị trường hiện tại và mức rủi ro tối ưu
        current_market_condition = None
        current_optimal_risk = 0.10  # Giá trị mặc định
        current_strategy = None
        
        # Vòng lặp chính của backtest
        for i in range(start_idx, end_idx + 1):
            # 1. Cập nhật các vị thế đang mở
            self.simulator.update_positions(i)
            
            # 2. Phân tích thị trường (mỗi 24 nến - giả sử 1 ngày)
            if i % 24 == 0 or current_market_condition is None:
                current_market_condition = self.market_analyzer.detect_market_condition(i)
                current_indicators = self.market_analyzer.get_indicators_snapshot(i)
                
                # Lưu vào nhật ký phân tích
                self.market_analysis_log.append({
                    'idx': i,
                    'date': self.data.index[i] if isinstance(self.data.index, pd.DatetimeIndex) else i,
                    'price': self.data.iloc[i]['Close'],
                    'market_condition': current_market_condition,
                    'indicators': current_indicators
                })
                
                # 3. Lấy mức rủi ro tối ưu và chiến lược phù hợp
                current_optimal_risk = self.risk_manager.get_optimal_risk(current_market_condition, current_indicators)
                current_strategy = self.strategy_selector.select_strategy(current_market_condition, current_indicators)
                
                # Lưu vào nhật ký chiến lược
                self.strategy_selection_log.append({
                    'idx': i,
                    'date': self.data.index[i] if isinstance(self.data.index, pd.DatetimeIndex) else i,
                    'market_condition': current_market_condition,
                    'optimal_risk': current_optimal_risk,
                    'selected_strategy': current_strategy
                })
                
                logger.debug(f"Phân tích thị trường tại {i}: {current_market_condition}, Risk: {current_optimal_risk}, Strategy: {current_strategy}")
            
            # 4. Sinh tín hiệu dựa trên chiến lược đã chọn
            signal = self.signal_generator.generate_signal(current_strategy, i, current_optimal_risk)
            
            # Lưu tín hiệu vào nhật ký nếu có
            if signal:
                self.signal_log.append({
                    'idx': i,
                    'date': self.data.index[i] if isinstance(self.data.index, pd.DatetimeIndex) else i,
                    'price': self.data.iloc[i]['Close'],
                    'strategy': current_strategy,
                    'signal': signal
                })
                
                # 5. Kiểm tra xem có nên mở vị thế không
                active_positions = self.simulator.positions
                account_balance = self.simulator.balance
                account_equity = self.simulator.equity
                
                should_open = self.risk_manager.should_open_position(
                    current_optimal_risk, 
                    active_positions, 
                    account_balance, 
                    account_equity
                )
                
                # 6. Mở vị thế nếu điều kiện thỏa mãn
                if should_open:
                    self.simulator.open_position(i, signal, current_optimal_risk)
                    
                    # Lưu vào nhật ký giao dịch
                    self.trade_log.append({
                        'idx': i,
                        'date': self.data.index[i] if isinstance(self.data.index, pd.DatetimeIndex) else i,
                        'action': 'OPEN',
                        'type': signal['type'],
                        'price': signal['price'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit'],
                        'strategy': current_strategy,
                        'risk_level': current_optimal_risk,
                        'reason': signal['reason']
                    })
            
            # 7. Kiểm tra xem có nên giảm rủi ro không
            positions_to_close = self.risk_manager.should_reduce_risk(
                self.simulator.positions, 
                self.simulator.balance, 
                self.simulator.equity
            )
            
            # 8. Đóng các vị thế nếu cần giảm rủi ro
            for pos in positions_to_close:
                # Đánh dấu vị thế để đóng trong vòng lặp tiếp theo
                pos['force_close'] = True
                
                # Lưu vào nhật ký giao dịch
                self.trade_log.append({
                    'idx': i,
                    'date': self.data.index[i] if isinstance(self.data.index, pd.DatetimeIndex) else i,
                    'action': 'FORCE_CLOSE',
                    'type': pos['type'],
                    'price': self.data.iloc[i]['Close'],
                    'strategy': pos['strategy'],
                    'risk_level': pos['risk_level'],
                    'reason': 'Risk reduction'
                })
        
        # Tính toán thống kê cuối cùng
        final_stats = self.simulator.calculate_final_stats()
        
        logger.info(f"Kết thúc backtest: P/L: {final_stats['total_profit_pct']:.2f}%, Win Rate: {final_stats['win_rate']:.2f}%, Trades: {final_stats['total_trades']}")
        
        # Thống kê theo chiến lược
        for strategy, stats in final_stats['strategy_stats'].items():
            logger.info(f"Chiến lược {strategy}: Win Rate: {stats['win_rate']:.2f}%, Trades: {stats['total']}, P/L: {stats['profit']:.2f}")
        
        return final_stats
    
    def calculate_market_condition_stats(self):
        """
        Tính toán thống kê về điều kiện thị trường
        
        Returns:
            dict: Thống kê điều kiện thị trường
        """
        if not self.market_analysis_log:
            return {}
        
        market_conditions = {}
        for entry in self.market_analysis_log:
            condition = entry['market_condition']
            if condition not in market_conditions:
                market_conditions[condition] = 0
            market_conditions[condition] += 1
        
        # Tính phần trăm
        total = len(self.market_analysis_log)
        for condition in market_conditions:
            market_conditions[condition] = {
                'count': market_conditions[condition],
                'percentage': market_conditions[condition] / total * 100
            }
        
        return market_conditions
    
    def calculate_strategy_performance(self):
        """
        Tính toán hiệu suất của từng chiến lược
        
        Returns:
            dict: Hiệu suất của từng chiến lược
        """
        if not self.simulator or not self.simulator.closed_positions:
            return {}
        
        strategy_performance = {}
        for pos in self.simulator.closed_positions:
            strategy = pos['strategy']
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0.0,
                    'win_rate': 0.0,
                    'avg_profit': 0.0,
                    'avg_loss': 0.0,
                    'max_profit': 0.0,
                    'max_loss': 0.0
                }
            
            realized_pnl = pos.get('realized_pnl', 0)
            strategy_performance[strategy]['total_trades'] += 1
            strategy_performance[strategy]['total_profit'] += realized_pnl
            
            if realized_pnl > 0:
                strategy_performance[strategy]['winning_trades'] += 1
                strategy_performance[strategy]['max_profit'] = max(strategy_performance[strategy]['max_profit'], realized_pnl)
            elif realized_pnl < 0:
                strategy_performance[strategy]['losing_trades'] += 1
                strategy_performance[strategy]['max_loss'] = min(strategy_performance[strategy]['max_loss'], realized_pnl)
        
        # Tính thống kê bổ sung
        for strategy, stats in strategy_performance.items():
            if stats['total_trades'] > 0:
                stats['win_rate'] = stats['winning_trades'] / stats['total_trades'] * 100
            
            winning_trades = [p.get('realized_pnl', 0) for p in self.simulator.closed_positions if p['strategy'] == strategy and p.get('realized_pnl', 0) > 0]
            losing_trades = [p.get('realized_pnl', 0) for p in self.simulator.closed_positions if p['strategy'] == strategy and p.get('realized_pnl', 0) < 0]
            
            stats['avg_profit'] = sum(winning_trades) / len(winning_trades) if winning_trades else 0
            stats['avg_loss'] = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        
        return strategy_performance
    
    def plot_equity_curve(self):
        """
        Vẽ đường equity
        
        Returns:
            str: Đường dẫn đến file hình ảnh
        """
        if not self.simulator:
            return None
        
        equity_curve = self.simulator.get_full_equity_curve()
        
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve)
        plt.title(f'Đường Equity - {self.symbol} {self.timeframe} ({self.test_period} ngày)')
        plt.xlabel('Candle Index')
        plt.ylabel('Balance')
        plt.grid(True)
        
        # Vẽ line ở initial_balance
        plt.axhline(y=self.initial_balance, color='r', linestyle='--')
        
        # Lưu hình ảnh
        output_path = self.result_dir / f"{self.symbol}_{self.timeframe}_equity_curve.png"
        plt.savefig(output_path)
        plt.close()
        
        return output_path
    
    def plot_market_conditions(self):
        """
        Vẽ biểu đồ điều kiện thị trường
        
        Returns:
            str: Đường dẫn đến file hình ảnh
        """
        if not self.market_analysis_log:
            return None
        
        market_conditions = self.calculate_market_condition_stats()
        
        conditions = list(market_conditions.keys())
        percentages = [market_conditions[c]['percentage'] for c in conditions]
        
        plt.figure(figsize=(10, 6))
        plt.bar(conditions, percentages)
        plt.title(f'Phân Bố Điều Kiện Thị Trường - {self.symbol} {self.timeframe} ({self.test_period} ngày)')
        plt.xlabel('Điều Kiện Thị Trường')
        plt.ylabel('Phần Trăm (%)')
        plt.grid(axis='y')
        
        # Thêm giá trị lên đầu các cột
        for i, v in enumerate(percentages):
            plt.text(i, v + 0.5, f"{v:.1f}%", ha='center')
        
        # Lưu hình ảnh
        output_path = self.result_dir / f"{self.symbol}_{self.timeframe}_market_conditions.png"
        plt.savefig(output_path)
        plt.close()
        
        return output_path
    
    def plot_strategy_performance(self):
        """
        Vẽ biểu đồ hiệu suất của các chiến lược
        
        Returns:
            str: Đường dẫn đến file hình ảnh
        """
        strategy_performance = self.calculate_strategy_performance()
        
        if not strategy_performance:
            return None
        
        strategies = list(strategy_performance.keys())
        win_rates = [strategy_performance[s]['win_rate'] for s in strategies]
        profits = [strategy_performance[s]['total_profit'] for s in strategies]
        
        # Tạo figure với 2 subplot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
        
        # Subplot 1: Win Rate
        bars1 = ax1.bar(strategies, win_rates)
        ax1.set_title(f'Tỷ Lệ Thắng Theo Chiến Lược - {self.symbol} {self.timeframe}')
        ax1.set_xlabel('Chiến Lược')
        ax1.set_ylabel('Win Rate (%)')
        ax1.grid(axis='y')
        
        # Thêm giá trị lên đầu các cột
        for i, v in enumerate(win_rates):
            ax1.text(i, v + 1, f"{v:.1f}%", ha='center')
        
        # Subplot 2: Total Profit
        bars2 = ax2.bar(strategies, profits)
        ax2.set_title(f'Tổng Lợi Nhuận Theo Chiến Lược - {self.symbol} {self.timeframe}')
        ax2.set_xlabel('Chiến Lược')
        ax2.set_ylabel('Lợi Nhuận')
        ax2.grid(axis='y')
        
        # Thêm giá trị lên đầu các cột
        for i, v in enumerate(profits):
            ax2.text(i, v + (0.01 * max(profits) if max(profits) > 0 else -0.01 * min(profits)), 
                    f"{v:.2f}", ha='center')
        
        plt.tight_layout()
        
        # Lưu hình ảnh
        output_path = self.result_dir / f"{self.symbol}_{self.timeframe}_strategy_performance.png"
        plt.savefig(output_path)
        plt.close()
        
        return output_path
    
    def save_results(self):
        """
        Lưu tất cả kết quả backtest
        
        Returns:
            dict: Đường dẫn đến các file kết quả
        """
        if not self.simulator:
            return {}
        
        # Tạo thư mục kết quả nếu chưa tồn tại
        if not self.result_dir.exists():
            os.makedirs(self.result_dir)
        
        # 1. Lưu thống kê tổng thể
        stats = self.simulator.stats
        stats_path = self.result_dir / f"{self.symbol}_{self.timeframe}_stats.json"
        
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=4, default=str)
        
        # 2. Lưu danh sách vị thế đã đóng
        positions_df = pd.DataFrame(self.simulator.closed_positions)
        positions_path = self.result_dir / f"{self.symbol}_{self.timeframe}_positions.csv"
        
        if not positions_df.empty:
            positions_df.to_csv(positions_path, index=False)
        
        # 3. Lưu nhật ký phân tích thị trường
        market_analysis_df = pd.DataFrame(self.market_analysis_log)
        market_analysis_path = self.result_dir / f"{self.symbol}_{self.timeframe}_market_analysis.csv"
        
        if not market_analysis_df.empty:
            # Cần xử lý cột indicators mà nó là dictionary
            if 'indicators' in market_analysis_df.columns:
                market_analysis_df = market_analysis_df.drop(columns=['indicators'])
            
            market_analysis_df.to_csv(market_analysis_path, index=False)
        
        # 4. Lưu nhật ký chiến lược
        strategy_df = pd.DataFrame(self.strategy_selection_log)
        strategy_path = self.result_dir / f"{self.symbol}_{self.timeframe}_strategy_selection.csv"
        
        if not strategy_df.empty:
            strategy_df.to_csv(strategy_path, index=False)
        
        # 5. Lưu nhật ký tín hiệu
        signal_df = pd.DataFrame([{
            'idx': s['idx'],
            'date': s['date'],
            'price': s['price'],
            'strategy': s['strategy'],
            'signal_type': s['signal']['type'],
            'stop_loss': s['signal']['stop_loss'],
            'take_profit': s['signal']['take_profit']
        } for s in self.signal_log])
        
        signal_path = self.result_dir / f"{self.symbol}_{self.timeframe}_signals.csv"
        
        if not signal_df.empty:
            signal_df.to_csv(signal_path, index=False)
        
        # 6. Lưu nhật ký giao dịch
        trade_df = pd.DataFrame(self.trade_log)
        trade_path = self.result_dir / f"{self.symbol}_{self.timeframe}_trades.csv"
        
        if not trade_df.empty:
            trade_df.to_csv(trade_path, index=False)
        
        # 7. Vẽ đồ thị
        equity_curve_path = self.plot_equity_curve()
        market_conditions_path = self.plot_market_conditions()
        strategy_performance_path = self.plot_strategy_performance()
        
        # 8. Tạo báo cáo HTML
        report_content = self.generate_html_report(stats)
        report_path = self.result_dir / f"{self.symbol}_{self.timeframe}_report.html"
        
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        logger.info(f"Đã lưu tất cả kết quả trong thư mục {self.result_dir}")
        
        return {
            'stats': stats_path,
            'positions': positions_path,
            'market_analysis': market_analysis_path,
            'strategy_selection': strategy_path,
            'signals': signal_path,
            'trades': trade_path,
            'equity_curve': equity_curve_path,
            'market_conditions': market_conditions_path,
            'strategy_performance': strategy_performance_path,
            'report': report_path
        }
    
    def generate_html_report(self, stats):
        """
        Tạo báo cáo HTML
        
        Args:
            stats (dict): Thống kê backtest
            
        Returns:
            str: Nội dung HTML
        """
        # Tính thống kê điều kiện thị trường
        market_conditions = self.calculate_market_condition_stats()
        
        # Tính hiệu suất chiến lược
        strategy_performance = self.calculate_strategy_performance()
        
        # Tạo HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Báo Cáo Backtest - {self.symbol} {self.timeframe}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; }}
                th {{ background-color: #f2f2f2; text-align: left; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .good {{ color: green; }}
                .bad {{ color: red; }}
                .section {{ margin-bottom: 30px; }}
                .summary {{ display: flex; flex-wrap: wrap; }}
                .summary-item {{ width: 200px; margin: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .summary-value {{ font-size: 24px; margin: 10px 0; }}
                img {{ max-width: 100%; height: auto; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>Báo Cáo Backtest Thực Tế</h1>
            <div class="section">
                <h2>Thông Tin Chung</h2>
                <p>
                    <strong>Cặp Tiền:</strong> {self.symbol}<br>
                    <strong>Timeframe:</strong> {self.timeframe}<br>
                    <strong>Thời Gian Backtest:</strong> {self.test_period} ngày<br>
                    <strong>Số Dư Ban Đầu:</strong> {self.initial_balance:,.2f}<br>
                    <strong>Số Dư Cuối Cùng:</strong> {stats['final_balance']:,.2f}<br>
                </p>
            </div>
            
            <div class="section">
                <h2>Tóm Tắt Hiệu Suất</h2>
                <div class="summary">
                    <div class="summary-item">
                        <div>Lợi Nhuận</div>
                        <div class="summary-value {'good' if stats['total_profit'] > 0 else 'bad'}">{stats['total_profit_pct']:.2f}%</div>
                    </div>
                    <div class="summary-item">
                        <div>Tỷ Lệ Thắng</div>
                        <div class="summary-value">{stats['win_rate']:.2f}%</div>
                    </div>
                    <div class="summary-item">
                        <div>Số Giao Dịch</div>
                        <div class="summary-value">{stats['total_trades']}</div>
                    </div>
                    <div class="summary-item">
                        <div>Drawdown Tối Đa</div>
                        <div class="summary-value bad">{stats['max_drawdown_pct']:.2f}%</div>
                    </div>
                    <div class="summary-item">
                        <div>Profit Factor</div>
                        <div class="summary-value">{stats['profit_factor']:.2f}</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>Phân Bố Điều Kiện Thị Trường</h2>
                <table>
                    <tr>
                        <th>Điều Kiện</th>
                        <th>Số Lần Xuất Hiện</th>
                        <th>Phần Trăm</th>
                    </tr>
        """
        
        for condition, data in market_conditions.items():
            html += f"""
                    <tr>
                        <td>{condition}</td>
                        <td>{data['count']}</td>
                        <td>{data['percentage']:.2f}%</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Hiệu Suất Theo Chiến Lược</h2>
                <table>
                    <tr>
                        <th>Chiến Lược</th>
                        <th>Số Giao Dịch</th>
                        <th>Tỷ Lệ Thắng</th>
                        <th>Lợi Nhuận</th>
                        <th>Lợi Nhuận TB</th>
                        <th>Thua Lỗ TB</th>
                    </tr>
        """
        
        for strategy, data in strategy_performance.items():
            profit_class = 'good' if data['total_profit'] > 0 else 'bad'
            html += f"""
                    <tr>
                        <td>{strategy}</td>
                        <td>{data['total_trades']}</td>
                        <td>{data['win_rate']:.2f}%</td>
                        <td class="{profit_class}">{data['total_profit']:.2f}</td>
                        <td class="good">{data['avg_profit']:.2f}</td>
                        <td class="bad">{data['avg_loss']:.2f}</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Hình Ảnh</h2>
                <h3>Đường Equity</h3>
                <img src="SYMBOL_TIMEFRAME_equity_curve.png" alt="Equity Curve">
                
                <h3>Phân Bố Điều Kiện Thị Trường</h3>
                <img src="SYMBOL_TIMEFRAME_market_conditions.png" alt="Market Conditions">
                
                <h3>Hiệu Suất Theo Chiến Lược</h3>
                <img src="SYMBOL_TIMEFRAME_strategy_performance.png" alt="Strategy Performance">
            </div>
        </body>
        </html>
        """
        
        # Thay thế placeholder
        html = html.replace("SYMBOL_TIMEFRAME", f"{self.symbol}_{self.timeframe}")
        
        return html

def main():
    """
    Hàm chính - Chạy backtest trên nhiều cặp tiền và mức vốn
    """
    logger.info("=== BẮT ĐẦU BACKTEST THỰC TẾ ===")
    
    # Danh sách cặp tiền 
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT"]
    timeframe = "1h"
    test_period = 30  # Test 30 ngày
    
    # Các mức vốn để test
    account_balances = [300, 600]
    
    # Lưu kết quả tổng hợp
    combined_results = {
        'by_symbol': {},
        'by_balance': {},
        'by_strategy': {},
        'by_risk': {},
        'overall': {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'profit_pct': 0,
            'max_drawdown': 0,
        }
    }
    
    for initial_balance in account_balances:
        combined_results['by_balance'][initial_balance] = {
            'total_trades': 0,
            'winning_trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'profit_pct': 0,
        }
        
        for symbol in symbols:
            logger.info(f"Chạy backtest cho {symbol} với tài khoản ${initial_balance}")
            
            # Tạo instance backtest
            backtest = RealisticBacktest(symbol, timeframe, test_period, initial_balance)
            
            # Tải dữ liệu
            if not backtest.load_data():
                logger.error(f"Không thể tải dữ liệu cho {symbol}. Bỏ qua.")
                continue
            
            # Chạy backtest
            stats = backtest.run_backtest()
            
            # Lưu kết quả
            backtest.save_results()
            
            # Thêm kết quả vào bảng tổng hợp
            if stats:
                # Lưu theo symbol
                combined_results['by_symbol'][symbol] = {
                    'total_trades': stats['total_trades'],
                    'winning_trades': stats['winning_trades'],
                    'win_rate': stats['win_rate'],
                    'total_profit': stats['total_profit'],
                    'profit_pct': stats['total_profit_pct'],
                    'max_drawdown': stats['max_drawdown_pct'],
                }
                
                # Cập nhật tổng theo balance
                combined_results['by_balance'][initial_balance]['total_trades'] += stats['total_trades']
                combined_results['by_balance'][initial_balance]['winning_trades'] += stats['winning_trades']
                combined_results['by_balance'][initial_balance]['total_profit'] += stats['total_profit']
                
                # Cập nhật theo chiến lược
                for strategy, strategy_stats in stats['strategy_stats'].items():
                    if strategy not in combined_results['by_strategy']:
                        combined_results['by_strategy'][strategy] = {
                            'total_trades': 0,
                            'winning_trades': 0,
                            'win_rate': 0,
                            'total_profit': 0,
                        }
                    
                    combined_results['by_strategy'][strategy]['total_trades'] += strategy_stats['total']
                    combined_results['by_strategy'][strategy]['winning_trades'] += strategy_stats['win']
                    combined_results['by_strategy'][strategy]['total_profit'] += strategy_stats['profit']
                
                # Cập nhật tổng thể
                combined_results['overall']['total_trades'] += stats['total_trades']
                combined_results['overall']['winning_trades'] += stats['winning_trades']
                combined_results['overall']['total_profit'] += stats['total_profit']
                combined_results['overall']['max_drawdown'] = max(combined_results['overall']['max_drawdown'], stats['max_drawdown_pct'])
    
    # Tính tỷ lệ thắng tổng thể và các chỉ số tổng hợp khác
    if combined_results['overall']['total_trades'] > 0:
        combined_results['overall']['win_rate'] = combined_results['overall']['winning_trades'] / combined_results['overall']['total_trades'] * 100
        combined_results['overall']['profit_pct'] = combined_results['overall']['total_profit'] / (len(account_balances) * len(symbols) * account_balances[0]) * 100
    
    for balance in account_balances:
        if combined_results['by_balance'][balance]['total_trades'] > 0:
            combined_results['by_balance'][balance]['win_rate'] = combined_results['by_balance'][balance]['winning_trades'] / combined_results['by_balance'][balance]['total_trades'] * 100
            combined_results['by_balance'][balance]['profit_pct'] = combined_results['by_balance'][balance]['total_profit'] / (len(symbols) * balance) * 100
    
    for strategy in combined_results['by_strategy']:
        if combined_results['by_strategy'][strategy]['total_trades'] > 0:
            combined_results['by_strategy'][strategy]['win_rate'] = combined_results['by_strategy'][strategy]['winning_trades'] / combined_results['by_strategy'][strategy]['total_trades'] * 100
    
    # Lưu kết quả tổng hợp vào file
    with open('realistic_backtest_results/combined_results.json', 'w') as f:
        json.dump(combined_results, f, indent=4, default=str)
    
    # Tạo báo cáo tổng hợp dạng text
    with open('realistic_backtest_results/summary_report.txt', 'w') as f:
        f.write("=== BÁO CÁO TỔNG HỢP BACKTEST ===\n\n")
        
        f.write(f"Tổng số giao dịch: {combined_results['overall']['total_trades']}\n")
        f.write(f"Số giao dịch thắng: {combined_results['overall']['winning_trades']}\n")
        f.write(f"Tỷ lệ thắng: {combined_results['overall']['win_rate']:.2f}%\n")
        f.write(f"Tổng lợi nhuận: ${combined_results['overall']['total_profit']:.2f}\n")
        f.write(f"Tỷ lệ lợi nhuận trung bình: {combined_results['overall']['profit_pct']:.2f}%\n")
        f.write(f"Drawdown tối đa: {combined_results['overall']['max_drawdown']:.2f}%\n\n")
        
        f.write("=== KẾT QUẢ THEO COIN ===\n\n")
        for symbol, stats in combined_results['by_symbol'].items():
            f.write(f"{symbol}: {stats['total_trades']} giao dịch, Win rate: {stats['win_rate']:.2f}%, P/L: {stats['profit_pct']:.2f}%, Drawdown: {stats['max_drawdown']:.2f}%\n")
        
        f.write("\n=== KẾT QUẢ THEO KÍCH THƯỚC TÀI KHOẢN ===\n\n")
        for balance, stats in combined_results['by_balance'].items():
            f.write(f"${balance}: {stats['total_trades']} giao dịch, Win rate: {stats['win_rate']:.2f}%, P/L: {stats['profit_pct']:.2f}%\n")
        
        f.write("\n=== KẾT QUẢ THEO CHIẾN LƯỢC ===\n\n")
        for strategy, stats in combined_results['by_strategy'].items():
            f.write(f"{strategy}: {stats['total_trades']} giao dịch, Win rate: {stats['win_rate']:.2f}%, P/L: ${stats['total_profit']:.2f}\n")
    
    logger.info("=== KẾT THÚC BACKTEST THỰC TẾ ===")
    logger.info(f"Xem báo cáo chi tiết trong realistic_backtest_results/summary_report.txt")

if __name__ == "__main__":
    main()