"""
Module chiến lược giao dịch cho tài khoản nhỏ (Micro Trading Strategy)

Module này cung cấp các chiến lược giao dịch được tối ưu hóa cho tài khoản có vốn nhỏ
(100-200 USD) kết hợp với đòn bẩy cao (x10-x20) trên thị trường Futures.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# Import các module khác của hệ thống
from micro_position_sizing import MicroPositionSizer

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("micro_trading_strategy")

class MicroTradingStrategy:
    """Chiến lược giao dịch tối ưu cho tài khoản nhỏ"""
    
    def __init__(self, 
                 initial_balance: float = 100.0,
                 max_leverage: int = 20,
                 risk_per_trade: float = 2.0,
                 strategy_type: str = 'scalping',
                 stop_type: str = 'ATR',
                 take_profit_ratio: float = 2.0):
        """
        Khởi tạo chiến lược giao dịch cho tài khoản nhỏ
        
        Args:
            initial_balance (float): Số dư ban đầu (USD)
            max_leverage (int): Đòn bẩy tối đa cho phép
            risk_per_trade (float): % rủi ro cho mỗi giao dịch
            strategy_type (str): Loại chiến lược ('scalping', 'breakout', 'reversal', 'trend')
            stop_type (str): Loại stop loss ('ATR', 'percent', 'support_resistance')
            take_profit_ratio (float): Tỷ lệ take profit / stop loss
        """
        self.initial_balance = initial_balance
        self.max_leverage = max_leverage
        self.risk_per_trade = risk_per_trade
        self.strategy_type = strategy_type
        self.stop_type = stop_type
        self.take_profit_ratio = take_profit_ratio
        
        # Khởi tạo position sizer
        self.position_sizer = MicroPositionSizer(
            initial_balance=initial_balance,
            max_leverage=max_leverage,
            max_risk_per_trade_percent=risk_per_trade,
            adaptive_sizing=True
        )
        
        # Thiết lập các tham số theo loại chiến lược
        self._configure_strategy()
        
        logger.info(f"Khởi tạo MicroTradingStrategy: {strategy_type}, "
                   f"Balance=${initial_balance}, MaxLeverage=x{max_leverage}, "
                   f"Risk={risk_per_trade}%")
    
    def _configure_strategy(self):
        """Cấu hình các tham số dựa trên loại chiến lược"""
        if self.strategy_type == 'scalping':
            # Cho tài khoản nhỏ: scalping với đòn bẩy cao, nhiều giao dịch nhỏ
            self.params = {
                'ATR_period': 14,
                'ATR_multiplier': 1.0,  # Stop loss nhỏ hơn cho scalping
                'RSI_period': 7,        # RSI ngắn hơn cho scalping
                'RSI_overbought': 75,   # Ngưỡng overbought cao hơn
                'RSI_oversold': 25,     # Ngưỡng oversold thấp hơn
                'EMA_short': 9,
                'EMA_long': 21,
                'min_volume': 1.5,      # Yêu cầu volume lớn hơn trung bình
                'volatility_filter': 1.2,  # Scalping hiệu quả trong biến động cao
                'min_risk_reward': 1.5  # Tỷ lệ risk/reward tối thiểu
            }
            
        elif self.strategy_type == 'breakout':
            # Chiến lược breakout cho tài khoản nhỏ với đòn bẩy cao
            self.params = {
                'ATR_period': 14,
                'ATR_multiplier': 1.5,
                'lookback_period': 24,  # Số giờ để xác định kháng cự/hỗ trợ
                'confirmation_candles': 1,  # Số nến xác nhận breakout
                'volume_surge': 2.0,    # Yêu cầu surge volume khi breakout
                'max_retracement': 0.3, # % retracement tối đa sau breakout
                'min_consolidation_period': 12,  # Số giờ tối thiểu cho giai đoạn tích lũy
                'min_risk_reward': 2.0  # Tỷ lệ risk/reward tối thiểu
            }
            
        elif self.strategy_type == 'reversal':
            # Chiến lược đảo chiều cho tài khoản nhỏ
            self.params = {
                'ATR_period': 14,
                'ATR_multiplier': 2.0,  # Stop loss lớn hơn cho reversal
                'RSI_period': 14,
                'RSI_extreme': 15,      # Tìm kiếm các mức RSI cực đoan hơn
                'lookback_period': 48,  # Xem xét thời gian dài hơn
                'confirmation_candles': 2,  # Số nến xác nhận đảo chiều
                'min_price_move': 3.0,  # % chuyển động giá tối thiểu
                'oversold_threshold': 20,
                'overbought_threshold': 80,
                'min_risk_reward': 1.8  # Tỷ lệ risk/reward tối thiểu
            }
            
        elif self.strategy_type == 'trend':
            # Chiến lược theo xu hướng cho tài khoản nhỏ
            self.params = {
                'ATR_period': 14,
                'ATR_multiplier': 2.5,  # Stop loss lớn hơn cho trend following
                'EMA_short': 21,
                'EMA_long': 55,
                'MACD_fast': 12,
                'MACD_slow': 26,
                'MACD_signal': 9,
                'min_trend_strength': 25,  # Độ mạnh xu hướng tối thiểu theo ADX
                'trailing_stop': True,  # Sử dụng trailing stop
                'trail_percent': 1.5,   # % cho trailing stop
                'min_risk_reward': 2.5  # Tỷ lệ risk/reward tối thiểu
            }
        else:
            # Chiến lược mặc định cân bằng
            self.params = {
                'ATR_period': 14,
                'ATR_multiplier': 1.5,
                'RSI_period': 14,
                'EMA_short': 9,
                'EMA_long': 21,
                'min_risk_reward': 2.0
            }
        
        logger.info(f"Đã cấu hình tham số cho chiến lược {self.strategy_type}")
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """
        Tạo tín hiệu giao dịch từ dữ liệu giá
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và các chỉ báo kỹ thuật
            
        Returns:
            Dict: Tín hiệu giao dịch (nếu có)
        """
        if len(df) < 50:  # Cần ít nhất 50 nến
            return {'signal': 'neutral'}
        
        # Đảm bảo có các chỉ báo cần thiết
        self._ensure_indicators(df)
        
        # Phát hiện chế độ thị trường cho điều chỉnh leverage
        market_regime = self._detect_market_regime(df)
        
        # Tính volatility cho điều chỉnh leverage
        current_volatility = self._calculate_volatility(df)
        
        # Lấy gợi ý đòn bẩy tối ưu
        optimal_leverage = self.position_sizer.get_optimal_leverage(current_volatility, market_regime)
        
        # Gọi phương thức tạo tín hiệu dựa trên loại chiến lược
        if self.strategy_type == 'scalping':
            signal = self._generate_scalping_signal(df, optimal_leverage, current_volatility)
        elif self.strategy_type == 'breakout':
            signal = self._generate_breakout_signal(df, optimal_leverage, current_volatility)
        elif self.strategy_type == 'reversal':
            signal = self._generate_reversal_signal(df, optimal_leverage, current_volatility)
        elif self.strategy_type == 'trend':
            signal = self._generate_trend_signal(df, optimal_leverage, current_volatility)
        else:
            signal = {'signal': 'neutral'}
        
        # Thêm thông tin thị trường
        signal['market_regime'] = market_regime
        signal['market_volatility'] = current_volatility
        signal['optimal_leverage'] = optimal_leverage
        
        # Log tín hiệu
        if signal['signal'] != 'neutral':
            logger.info(f"Tín hiệu {self.strategy_type}: {signal['signal'].upper()}, "
                       f"Entry={signal.get('entry_price', 0):.2f}, "
                       f"Stop={signal.get('stop_loss', 0):.2f}, "
                       f"TP={signal.get('take_profit', 0):.2f}, "
                       f"Leverage=x{optimal_leverage}")
        
        return signal
    
    def _ensure_indicators(self, df: pd.DataFrame) -> None:
        """
        Đảm bảo DataFrame có tất cả các chỉ báo cần thiết
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
        """
        # Thêm các chỉ báo nếu chưa có
        # ATR - dùng cho stop loss
        if 'atr' not in df.columns:
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['atr'] = tr.rolling(window=self.params['ATR_period']).mean()
        
        # RSI
        if 'rsi' not in df.columns and ('RSI_period' in self.params):
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=self.params['RSI_period']).mean()
            avg_loss = loss.rolling(window=self.params['RSI_period']).mean()
            
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMA
        if 'EMA_short' in self.params and f"ema{self.params['EMA_short']}" not in df.columns:
            df[f"ema{self.params['EMA_short']}"] = df['close'].ewm(span=self.params['EMA_short'], adjust=False).mean()
            
        if 'EMA_long' in self.params and f"ema{self.params['EMA_long']}" not in df.columns:
            df[f"ema{self.params['EMA_long']}"] = df['close'].ewm(span=self.params['EMA_long'], adjust=False).mean()
        
        # MACD
        if 'MACD_fast' in self.params and 'macd' not in df.columns:
            fast = df['close'].ewm(span=self.params['MACD_fast'], adjust=False).mean()
            slow = df['close'].ewm(span=self.params['MACD_slow'], adjust=False).mean()
            df['macd'] = fast - slow
            df['macd_signal'] = df['macd'].ewm(span=self.params['MACD_signal'], adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """
        Tính toán độ biến động hiện tại của thị trường
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
            
        Returns:
            float: Độ biến động dưới dạng % thay đổi giá
        """
        # Sử dụng ATR làm % của giá hiện tại
        if 'atr' in df.columns:
            current_atr = df['atr'].iloc[-1]
            current_price = df['close'].iloc[-1]
            volatility = (current_atr / current_price) * 100
        else:
            # Tính độ biến động từ % thay đổi giá
            returns = df['close'].pct_change().dropna()
            volatility = returns.std() * 100 * np.sqrt(24)  # Quy đổi theo ngày (24 giờ)
            
        return volatility
    
    def _detect_market_regime(self, df: pd.DataFrame) -> str:
        """
        Phát hiện chế độ thị trường hiện tại
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
            
        Returns:
            str: Chế độ thị trường ('trending', 'ranging', 'volatile', 'quiet')
        """
        # Tính độ biến động
        volatility = self._calculate_volatility(df)
        
        # Kiểm tra xu hướng
        if 'ema9' in df.columns and 'ema21' in df.columns:
            ema_short = df['ema9'].iloc[-1]
            ema_long = df['ema21'].iloc[-1]
            ema_diff = abs((ema_short - ema_long) / ema_long) * 100
            
            # Tính momentum
            close_prices = df['close'].iloc[-20:]
            momentum = (close_prices.iloc[-1] - close_prices.iloc[0]) / close_prices.iloc[0] * 100
            
            # Phát hiện chế độ thị trường
            if ema_diff > 1.0 and abs(momentum) > 5.0:  # Xu hướng rõ ràng
                return 'trending'
            elif volatility > 3.0:  # Biến động cao
                return 'volatile'
            elif volatility < 1.0:  # Biến động thấp
                return 'quiet'
            else:  # Mặc định: thị trường đi ngang
                return 'ranging'
        else:
            # Phương pháp phát hiện dự phòng
            if volatility > 3.0:
                return 'volatile'
            elif volatility < 1.0:
                return 'quiet'
            else:
                return 'ranging'
    
    def _calculate_stop_loss(self, df: pd.DataFrame, signal: str) -> float:
        """
        Tính toán mức stop loss dựa trên loại stop đã cấu hình
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
            signal (str): Tín hiệu giao dịch ('buy' hoặc 'sell')
            
        Returns:
            float: Mức stop loss
        """
        current_price = df['close'].iloc[-1]
        
        if self.stop_type == 'ATR':
            # Sử dụng ATR cho stop loss
            atr = df['atr'].iloc[-1]
            if signal == 'buy':
                return current_price - atr * self.params['ATR_multiplier']
            else:  # 'sell'
                return current_price + atr * self.params['ATR_multiplier']
                
        elif self.stop_type == 'percent':
            # Sử dụng % cố định
            stop_percent = 1.0  # Mặc định 1%
            if signal == 'buy':
                return current_price * (1 - stop_percent / 100)
            else:  # 'sell'
                return current_price * (1 + stop_percent / 100)
                
        elif self.stop_type == 'support_resistance':
            # Tìm mức support/resistance gần nhất
            if signal == 'buy':
                # Tìm mức hỗ trợ gần nhất
                recent_lows = df['low'].iloc[-20:].nsmallest(3)
                support_level = recent_lows.mean()
                return min(support_level, current_price - df['atr'].iloc[-1])
            else:  # 'sell'
                # Tìm mức kháng cự gần nhất
                recent_highs = df['high'].iloc[-20:].nlargest(3)
                resistance_level = recent_highs.mean()
                return max(resistance_level, current_price + df['atr'].iloc[-1])
        else:
            # Mặc định dùng ATR
            atr = df['atr'].iloc[-1]
            if signal == 'buy':
                return current_price - atr * 1.5
            else:  # 'sell'
                return current_price + atr * 1.5
    
    def _calculate_take_profit(self, entry_price: float, stop_loss: float, signal: str) -> float:
        """
        Tính toán mức take profit dựa trên tỷ lệ risk/reward
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            signal (str): Tín hiệu giao dịch ('buy' hoặc 'sell')
            
        Returns:
            float: Mức take profit
        """
        if signal == 'buy':
            risk = entry_price - stop_loss
            return entry_price + (risk * self.take_profit_ratio)
        else:  # 'sell'
            risk = stop_loss - entry_price
            return entry_price - (risk * self.take_profit_ratio)
    
    def _generate_scalping_signal(self, df: pd.DataFrame, leverage: int, volatility: float) -> Dict:
        """
        Tạo tín hiệu scalping cho tài khoản nhỏ
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
            leverage (int): Đòn bẩy đề xuất
            volatility (float): Độ biến động hiện tại
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        signal = {'signal': 'neutral'}
        
        # Lấy giá hiện tại và các chỉ báo
        current_price = df['close'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]
        
        # Lấy giá EMA
        ema_short = df[f"ema{self.params['EMA_short']}"].iloc[-1]
        ema_long = df[f"ema{self.params['EMA_long']}"].iloc[-1]
        
        # Dấu hiệu xu hướng từ EMA
        trend_direction = 'up' if ema_short > ema_long else 'down'
        
        # Filter 1: Kiểm tra xem biến động có đủ cho scalping không
        if volatility < self.params['volatility_filter']:
            return signal
        
        # Tín hiệu mua: RSI quá bán + EMA ngắn > EMA dài
        if (current_rsi < self.params['RSI_oversold'] and 
            trend_direction == 'up' and 
            df['volume'].iloc[-1] > df['volume'].rolling(20).mean().iloc[-1] * self.params['min_volume']):
            
            signal['signal'] = 'buy'
            signal['entry_price'] = current_price
            signal['stop_loss'] = self._calculate_stop_loss(df, 'buy')
            signal['take_profit'] = self._calculate_take_profit(current_price, signal['stop_loss'], 'buy')
            signal['leverage'] = leverage
            
            # Kiểm tra tỷ lệ risk/reward
            rr_ratio = self.position_sizer.calculate_risk_reward_ratio(
                current_price, signal['stop_loss'], signal['take_profit'])
                
            if rr_ratio < self.params['min_risk_reward']:
                signal['signal'] = 'neutral'  # Không đủ tỷ lệ risk/reward
            
        # Tín hiệu bán: RSI quá mua + EMA ngắn < EMA dài
        elif (current_rsi > self.params['RSI_overbought'] and 
              trend_direction == 'down' and 
              df['volume'].iloc[-1] > df['volume'].rolling(20).mean().iloc[-1] * self.params['min_volume']):
            
            signal['signal'] = 'sell'
            signal['entry_price'] = current_price
            signal['stop_loss'] = self._calculate_stop_loss(df, 'sell')
            signal['take_profit'] = self._calculate_take_profit(current_price, signal['stop_loss'], 'sell')
            signal['leverage'] = leverage
            
            # Kiểm tra tỷ lệ risk/reward
            rr_ratio = self.position_sizer.calculate_risk_reward_ratio(
                current_price, signal['stop_loss'], signal['take_profit'])
                
            if rr_ratio < self.params['min_risk_reward']:
                signal['signal'] = 'neutral'  # Không đủ tỷ lệ risk/reward
        
        return signal
    
    def _generate_breakout_signal(self, df: pd.DataFrame, leverage: int, volatility: float) -> Dict:
        """
        Tạo tín hiệu breakout cho tài khoản nhỏ
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
            leverage (int): Đòn bẩy đề xuất
            volatility (float): Độ biến động hiện tại
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        signal = {'signal': 'neutral'}
        
        # Tìm mức cao/thấp trong giai đoạn tích lũy
        lookback = self.params['lookback_period']
        if len(df) < lookback + 10:
            return signal
            
        # Xác định mức kháng cự/hỗ trợ
        recent_range = df.iloc[-lookback:-1]
        resistance = recent_range['high'].max()
        support = recent_range['low'].min()
        
        # Tính range trung bình của giai đoạn tích lũy
        avg_range = (recent_range['high'] - recent_range['low']).mean()
        
        # Lấy giá hiện tại và giá trước đó
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        # Xác nhận tích lũy (range nhỏ)
        consolidation_verified = avg_range < df['atr'].iloc[-1] * 1.5
        
        # Xác nhận khối lượng tăng
        volume_surge = df['volume'].iloc[-1] > df['volume'].rolling(lookback).mean().iloc[-1] * self.params['volume_surge']
        
        # Kiểm tra breakout hướng lên
        if (consolidation_verified and 
            current_high > resistance and 
            current_price > resistance and 
            volume_surge):
            
            # Breakout hướng lên
            signal['signal'] = 'buy'
            signal['entry_price'] = current_price
            # Stop loss ngay dưới mức support hoặc theo ATR, tùy thuộc vào cái nào gần hơn
            stop_by_support = support - df['atr'].iloc[-1] * 0.5
            stop_by_atr = self._calculate_stop_loss(df, 'buy')
            signal['stop_loss'] = max(stop_by_support, stop_by_atr)  # Chọn stop loss cao hơn (gần entry hơn)
            signal['take_profit'] = self._calculate_take_profit(current_price, signal['stop_loss'], 'buy')
            signal['leverage'] = leverage
            
            # Kiểm tra tỷ lệ risk/reward
            rr_ratio = self.position_sizer.calculate_risk_reward_ratio(
                current_price, signal['stop_loss'], signal['take_profit'])
                
            if rr_ratio < self.params['min_risk_reward']:
                signal['signal'] = 'neutral'  # Không đủ tỷ lệ risk/reward
            
        # Kiểm tra breakout hướng xuống
        elif (consolidation_verified and 
              current_low < support and 
              current_price < support and 
              volume_surge):
            
            # Breakout hướng xuống
            signal['signal'] = 'sell'
            signal['entry_price'] = current_price
            # Stop loss ngay trên mức resistance hoặc theo ATR, tùy thuộc vào cái nào gần hơn
            stop_by_resistance = resistance + df['atr'].iloc[-1] * 0.5
            stop_by_atr = self._calculate_stop_loss(df, 'sell')
            signal['stop_loss'] = min(stop_by_resistance, stop_by_atr)  # Chọn stop loss thấp hơn (gần entry hơn)
            signal['take_profit'] = self._calculate_take_profit(current_price, signal['stop_loss'], 'sell')
            signal['leverage'] = leverage
            
            # Kiểm tra tỷ lệ risk/reward
            rr_ratio = self.position_sizer.calculate_risk_reward_ratio(
                current_price, signal['stop_loss'], signal['take_profit'])
                
            if rr_ratio < self.params['min_risk_reward']:
                signal['signal'] = 'neutral'  # Không đủ tỷ lệ risk/reward
        
        return signal
    
    def _generate_reversal_signal(self, df: pd.DataFrame, leverage: int, volatility: float) -> Dict:
        """
        Tạo tín hiệu đảo chiều cho tài khoản nhỏ
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
            leverage (int): Đòn bẩy đề xuất
            volatility (float): Độ biến động hiện tại
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        signal = {'signal': 'neutral'}
        
        # Chuẩn bị dữ liệu
        current_price = df['close'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]
        prev_rsi = df['rsi'].iloc[-2]
        
        # Xác định xu hướng trước đó
        recent_prices = df['close'].iloc[-self.params['lookback_period']:]
        price_change = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0] * 100
        prior_trend = 'up' if price_change > 0 else 'down'
        
        # Xác định mức cực trị
        recent_high = df['high'].iloc[-self.params['lookback_period']:].max()
        recent_low = df['low'].iloc[-self.params['lookback_period']:].min()
        
        # Dấu hiệu đảo chiều xu hướng
        reversal_up = (
            prior_trend == 'down' and 
            current_rsi < self.params['oversold_threshold'] and 
            current_rsi > prev_rsi and  # RSI đang quay đầu
            df['close'].iloc[-1] > df['close'].iloc[-2] and  # Giá đang tăng
            df['volume'].iloc[-1] > df['volume'].rolling(5).mean().iloc[-1]  # Volume tăng
        )
        
        reversal_down = (
            prior_trend == 'up' and 
            current_rsi > self.params['overbought_threshold'] and 
            current_rsi < prev_rsi and  # RSI đang quay đầu
            df['close'].iloc[-1] < df['close'].iloc[-2] and  # Giá đang giảm
            df['volume'].iloc[-1] > df['volume'].rolling(5).mean().iloc[-1]  # Volume tăng
        )
        
        # Tín hiệu đảo chiều hướng lên
        if reversal_up:
            signal['signal'] = 'buy'
            signal['entry_price'] = current_price
            signal['stop_loss'] = max(recent_low * 0.995, self._calculate_stop_loss(df, 'buy'))
            signal['take_profit'] = self._calculate_take_profit(current_price, signal['stop_loss'], 'buy')
            signal['leverage'] = max(2, leverage - 5)  # Giảm leverage cho giao dịch đảo chiều
            
            # Kiểm tra tỷ lệ risk/reward
            rr_ratio = self.position_sizer.calculate_risk_reward_ratio(
                current_price, signal['stop_loss'], signal['take_profit'])
                
            if rr_ratio < self.params['min_risk_reward']:
                signal['signal'] = 'neutral'  # Không đủ tỷ lệ risk/reward
            
        # Tín hiệu đảo chiều hướng xuống
        elif reversal_down:
            signal['signal'] = 'sell'
            signal['entry_price'] = current_price
            signal['stop_loss'] = min(recent_high * 1.005, self._calculate_stop_loss(df, 'sell'))
            signal['take_profit'] = self._calculate_take_profit(current_price, signal['stop_loss'], 'sell')
            signal['leverage'] = max(2, leverage - 5)  # Giảm leverage cho giao dịch đảo chiều
            
            # Kiểm tra tỷ lệ risk/reward
            rr_ratio = self.position_sizer.calculate_risk_reward_ratio(
                current_price, signal['stop_loss'], signal['take_profit'])
                
            if rr_ratio < self.params['min_risk_reward']:
                signal['signal'] = 'neutral'  # Không đủ tỷ lệ risk/reward
        
        return signal
    
    def _generate_trend_signal(self, df: pd.DataFrame, leverage: int, volatility: float) -> Dict:
        """
        Tạo tín hiệu theo xu hướng cho tài khoản nhỏ
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu giá
            leverage (int): Đòn bẩy đề xuất
            volatility (float): Độ biến động hiện tại
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        signal = {'signal': 'neutral'}
        
        # Chuẩn bị dữ liệu
        current_price = df['close'].iloc[-1]
        
        # Kiểm tra dấu hiệu MACD và EMA
        macd = df['macd'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_hist = df['macd_hist'].iloc[-1]
        prev_macd_hist = df['macd_hist'].iloc[-2]
        
        ema_short = df[f"ema{self.params['EMA_short']}"].iloc[-1]
        ema_long = df[f"ema{self.params['EMA_long']}"].iloc[-1]
        
        # Xác định xu hướng
        trend_up = ema_short > ema_long
        trend_down = ema_short < ema_long
        
        # Tín hiệu mua: EMA ngắn > EMA dài và MACD > Signal
        if (trend_up and 
            macd > macd_signal and 
            macd_hist > 0 and 
            macd_hist > prev_macd_hist):  # Histogram đang tăng
            
            signal['signal'] = 'buy'
            signal['entry_price'] = current_price
            signal['stop_loss'] = self._calculate_stop_loss(df, 'buy')
            signal['take_profit'] = self._calculate_take_profit(current_price, signal['stop_loss'], 'buy')
            signal['leverage'] = leverage
            
            # Kiểm tra tỷ lệ risk/reward
            rr_ratio = self.position_sizer.calculate_risk_reward_ratio(
                current_price, signal['stop_loss'], signal['take_profit'])
                
            if rr_ratio < self.params['min_risk_reward']:
                signal['signal'] = 'neutral'  # Không đủ tỷ lệ risk/reward
            
        # Tín hiệu bán: EMA ngắn < EMA dài và MACD < Signal
        elif (trend_down and 
              macd < macd_signal and 
              macd_hist < 0 and 
              macd_hist < prev_macd_hist):  # Histogram đang giảm
            
            signal['signal'] = 'sell'
            signal['entry_price'] = current_price
            signal['stop_loss'] = self._calculate_stop_loss(df, 'sell')
            signal['take_profit'] = self._calculate_take_profit(current_price, signal['stop_loss'], 'sell')
            signal['leverage'] = leverage
            
            # Kiểm tra tỷ lệ risk/reward
            rr_ratio = self.position_sizer.calculate_risk_reward_ratio(
                current_price, signal['stop_loss'], signal['take_profit'])
                
            if rr_ratio < self.params['min_risk_reward']:
                signal['signal'] = 'neutral'  # Không đủ tỷ lệ risk/reward
        
        return signal
    
    def calculate_position_size(self, signal: Dict) -> Dict:
        """
        Tính toán kích thước vị thế cho tín hiệu giao dịch
        
        Args:
            signal (Dict): Tín hiệu giao dịch
            
        Returns:
            Dict: Tín hiệu với kích thước vị thế
        """
        if signal['signal'] in ['buy', 'sell']:
            # Điều chỉnh stop loss cho tài khoản nhỏ
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            leverage = signal['leverage']
            market_volatility = signal.get('market_volatility')
            
            # Tính kích thước vị thế
            position_size, details = self.position_sizer.calculate_position_size(
                entry_price=entry_price,
                stop_loss_price=stop_loss,
                leverage=leverage,
                market_volatility=market_volatility
            )
            
            # Đảm bảo kích thước vị thế phù hợp với tài khoản nhỏ
            adjusted_size = self.position_sizer.adjust_position_for_small_account(
                position_size_usd=position_size,
                entry_price=entry_price
            )
            
            # Cập nhật thông tin vào tín hiệu
            signal['position_size_usd'] = adjusted_size
            signal['quantity'] = adjusted_size / entry_price
            signal['margin_used'] = adjusted_size / leverage
            signal['effective_leverage'] = leverage
            signal['risk_amount'] = details['risk_amount']
            signal['risk_percent'] = details['risk_percent']
            signal['liquidation_price'] = details['liquidation_price_estimate']
            
        return signal
    
    def execute_trade(self, signal: Dict) -> bool:
        """
        Thực hiện giao dịch dựa trên tín hiệu
        
        Args:
            signal (Dict): Tín hiệu giao dịch với kích thước vị thế
            
        Returns:
            bool: True nếu giao dịch được thực hiện, False nếu không
        """
        if signal['signal'] not in ['buy', 'sell']:
            return False
            
        try:
            # Mở vị thế mới
            position_id = self.position_sizer.add_position(signal)
            
            logger.info(f"Đã mở vị thế: {signal['signal'].upper()}, "
                       f"Size=${signal['position_size_usd']:.2f}, "
                       f"Entry={signal['entry_price']:.2f}, "
                       f"Stop={signal['stop_loss']:.2f}, "
                       f"TP={signal['take_profit']:.2f}, "
                       f"Leverage=x{signal['effective_leverage']}")
                       
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện giao dịch: {e}")
            return False