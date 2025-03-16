#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Adaptive Risk Manager

Module này cung cấp các công cụ quản lý rủi ro thích ứng dựa trên ATR (Average True Range)
và tình trạng thị trường hiện tại để đặt các mức stop loss và take profit động.
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Union, Optional, Tuple

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('adaptive_risk_manager')

# Hằng số thị trường
MARKET_REGIME_STRONG_BULLISH = "strong_bullish"
MARKET_REGIME_BULLISH = "bullish"
MARKET_REGIME_NEUTRAL = "neutral"
MARKET_REGIME_BEARISH = "bearish"
MARKET_REGIME_STRONG_BEARISH = "strong_bearish"

# Các thông số ATR theo chế độ thị trường
ATR_MULTIPLIERS = {
    # (Stop Loss, Take Profit)
    MARKET_REGIME_STRONG_BULLISH: (2.0, 3.5),
    MARKET_REGIME_BULLISH: (2.5, 3.0),
    MARKET_REGIME_NEUTRAL: (2.0, 2.5),
    MARKET_REGIME_BEARISH: (2.5, 3.0),
    MARKET_REGIME_STRONG_BEARISH: (2.0, 3.5)
}

# Các thông số ATR theo chế độ thị trường với rủi ro cao (25-30%)
HIGH_RISK_ATR_MULTIPLIERS = {
    # (Stop Loss, Take Profit)
    MARKET_REGIME_STRONG_BULLISH: (1.8, 4.0),
    MARKET_REGIME_BULLISH: (2.0, 3.5),
    MARKET_REGIME_NEUTRAL: (1.8, 3.0),
    MARKET_REGIME_BEARISH: (2.0, 3.5),
    MARKET_REGIME_STRONG_BEARISH: (1.8, 4.0)
}

class AdaptiveRiskManager:
    """
    Quản lý rủi ro thích ứng dựa trên biến động thị trường
    """
    
    def __init__(self, default_sl_pct: float = 0.02, default_tp_pct: float = 0.05, 
                atr_periods: int = 14, volatility_lookback: int = 30):
        """
        Khởi tạo AdaptiveRiskManager
        
        Args:
            default_sl_pct: Phần trăm stop loss mặc định khi không có ATR
            default_tp_pct: Phần trăm take profit mặc định khi không có ATR
            atr_periods: Số nến để tính ATR
            volatility_lookback: Số nến để xác định volatility hiện tại
        """
        self.default_sl_pct = default_sl_pct
        self.default_tp_pct = default_tp_pct
        self.atr_periods = atr_periods
        self.volatility_lookback = volatility_lookback
        
    def calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán chỉ báo ATR cho DataFrame
        
        Args:
            df: DataFrame với dữ liệu giá ('high', 'low', 'close')
            
        Returns:
            DataFrame với thêm cột 'atr'
        """
        # Tạo bản sao của DataFrame
        result_df = df.copy()
        
        # Tính True Range
        result_df['tr1'] = abs(result_df['high'] - result_df['low'])
        result_df['tr2'] = abs(result_df['high'] - result_df['close'].shift())
        result_df['tr3'] = abs(result_df['low'] - result_df['close'].shift())
        result_df['tr'] = result_df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Tính ATR
        result_df['atr'] = result_df['tr'].rolling(window=self.atr_periods).mean()
        
        # Loại bỏ các cột tạm thời
        result_df = result_df.drop(['tr1', 'tr2', 'tr3', 'tr'], axis=1)
        
        return result_df
    
    def calculate_volatility_ratio(self, df: pd.DataFrame) -> float:
        """
        Tính tỷ lệ biến động hiện tại so với lịch sử
        
        Args:
            df: DataFrame với dữ liệu giá có ATR
            
        Returns:
            Tỷ lệ biến động (>1 = biến động cao, <1 = biến động thấp)
        """
        # Lấy ATR hiện tại
        current_atr = df['atr'].iloc[-1]
        
        # Lấy ATR trung bình trong quá khứ
        past_atr = df['atr'].iloc[-self.volatility_lookback:-1].mean()
        
        # Tính tỷ lệ
        if past_atr > 0:
            volatility_ratio = current_atr / past_atr
        else:
            volatility_ratio = 1.0
            
        return volatility_ratio
    
    def get_market_based_multipliers(self, market_regime: str, custom_multiplier: float = None,
                                 risk_level: float = 15.0) -> Tuple[float, float]:
        """
        Lấy bội số ATR dựa trên chế độ thị trường và mức độ rủi ro
        
        Args:
            market_regime: Chế độ thị trường hiện tại
            custom_multiplier: Bội số tùy chỉnh (nếu được cung cấp)
            risk_level: Mức độ rủi ro (phần trăm)
            
        Returns:
            Tuple (sl_multiplier, tp_multiplier)
        """
        # Nếu có custom_multiplier, sử dụng nó
        if custom_multiplier is not None:
            return (custom_multiplier, custom_multiplier)
        
        # Sử dụng bội số dựa trên mức độ rủi ro
        if risk_level >= 25.0:
            # Sử dụng bội số HIGH_RISK cho rủi ro cao (25-30%)
            if market_regime in HIGH_RISK_ATR_MULTIPLIERS:
                return HIGH_RISK_ATR_MULTIPLIERS[market_regime]
            # Mặc định cho rủi ro cao
            return (1.8, 3.5)
        else:
            # Sử dụng bội số mặc định cho rủi ro thông thường
            if market_regime in ATR_MULTIPLIERS:
                return ATR_MULTIPLIERS[market_regime]
            # Mặc định cho rủi ro thông thường
            return (2.0, 2.5)
    
    def adjust_for_volatility(self, multiplier: float, volatility_ratio: float) -> float:
        """
        Điều chỉnh bội số ATR dựa trên tỷ lệ biến động
        
        Args:
            multiplier: Bội số ATR ban đầu
            volatility_ratio: Tỷ lệ biến động
            
        Returns:
            Bội số ATR đã điều chỉnh
        """
        # Thị trường biến động cao -> giảm bội số để tránh stop loss quá xa
        if volatility_ratio > 1.5:
            return multiplier * 0.8
        # Thị trường biến động thấp -> tăng bội số để tránh dừng lỗ quá gần
        elif volatility_ratio < 0.7:
            return multiplier * 1.2
        # Biến động bình thường
        else:
            return multiplier
    
    def calculate_adaptive_stoploss(self, df: pd.DataFrame, position_type: str, 
                                   entry_price: float, market_regime: str = "neutral",
                                   custom_multiplier: float = None, risk_level: float = 15.0) -> float:
        """
        Tính toán mức stop loss thích ứng dựa trên ATR
        
        Args:
            df: DataFrame với dữ liệu giá (phải có cột 'atr')
            position_type: Loại vị thế ('long' hoặc 'short')
            entry_price: Giá entry
            market_regime: Chế độ thị trường hiện tại
            custom_multiplier: Bội số tùy chỉnh
            risk_level: Mức độ rủi ro (phần trăm, mặc định 15%)
            
        Returns:
            Giá stop loss
        """
        # Kiểm tra xem có dữ liệu ATR không
        if 'atr' not in df.columns or df['atr'].iloc[-1] is None or np.isnan(df['atr'].iloc[-1]):
            # Điều chỉnh sl_pct theo mức rủi ro
            adjusted_sl_pct = self.default_sl_pct
            if risk_level >= 25.0:
                adjusted_sl_pct = self.default_sl_pct * 0.9  # Gần hơn cho rủi ro cao
            
            # Sử dụng % đã điều chỉnh
            if position_type.lower() == 'long':
                return entry_price * (1 - adjusted_sl_pct)
            else:
                return entry_price * (1 + adjusted_sl_pct)
        
        # Lấy ATR hiện tại
        current_atr = df['atr'].iloc[-1]
        
        # Tính tỷ lệ biến động
        volatility_ratio = self.calculate_volatility_ratio(df)
        
        # Lấy bội số theo chế độ thị trường và mức rủi ro
        sl_multiplier, _ = self.get_market_based_multipliers(market_regime, custom_multiplier, risk_level)
        
        # Điều chỉnh bội số theo biến động
        adjusted_multiplier = self.adjust_for_volatility(sl_multiplier, volatility_ratio)
        
        # Tính stop loss
        if position_type.lower() == 'long':
            stop_loss = entry_price - (current_atr * adjusted_multiplier)
        else:  # short
            stop_loss = entry_price + (current_atr * adjusted_multiplier)
            
        return stop_loss
    
    def calculate_adaptive_takeprofit(self, df: pd.DataFrame, position_type: str, 
                                     entry_price: float, market_regime: str = "neutral",
                                     custom_multiplier: float = None, risk_level: float = 15.0) -> float:
        """
        Tính toán mức take profit thích ứng dựa trên ATR
        
        Args:
            df: DataFrame với dữ liệu giá (phải có cột 'atr')
            position_type: Loại vị thế ('long' hoặc 'short')
            entry_price: Giá entry
            market_regime: Chế độ thị trường hiện tại
            custom_multiplier: Bội số tùy chỉnh
            risk_level: Mức độ rủi ro (phần trăm, mặc định 15%)
            
        Returns:
            Giá take profit
        """
        # Kiểm tra xem có dữ liệu ATR không
        if 'atr' not in df.columns or df['atr'].iloc[-1] is None or np.isnan(df['atr'].iloc[-1]):
            # Điều chỉnh tp_pct theo mức rủi ro
            adjusted_tp_pct = self.default_tp_pct
            if risk_level >= 25.0:
                adjusted_tp_pct = self.default_tp_pct * 1.3  # Xa hơn cho rủi ro cao
            
            # Sử dụng % đã điều chỉnh
            if position_type.lower() == 'long':
                return entry_price * (1 + adjusted_tp_pct)
            else:
                return entry_price * (1 - adjusted_tp_pct)
        
        # Lấy ATR hiện tại
        current_atr = df['atr'].iloc[-1]
        
        # Tính tỷ lệ biến động
        volatility_ratio = self.calculate_volatility_ratio(df)
        
        # Lấy bội số theo chế độ thị trường và mức rủi ro
        _, tp_multiplier = self.get_market_based_multipliers(market_regime, custom_multiplier, risk_level)
        
        # Điều chỉnh bội số theo biến động
        adjusted_multiplier = self.adjust_for_volatility(tp_multiplier, volatility_ratio)
        
        # Tính take profit
        if position_type.lower() == 'long':
            take_profit = entry_price + (current_atr * adjusted_multiplier)
        else:  # short
            take_profit = entry_price - (current_atr * adjusted_multiplier)
            
        return take_profit
    
    def calculate_risk_reward_ratio(self, entry_price: float, stop_loss: float, 
                                   take_profit: float, position_type: str) -> float:
        """
        Tính tỷ lệ risk/reward
        
        Args:
            entry_price: Giá entry
            stop_loss: Giá stop loss
            take_profit: Giá take profit
            position_type: Loại vị thế ('long' hoặc 'short')
            
        Returns:
            Tỷ lệ R/R (tỷ lệ reward/risk)
        """
        if position_type.lower() == 'long':
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # short
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
            
        # Tránh chia cho 0
        if risk <= 0:
            return 0
            
        return reward / risk
    
    def is_risk_acceptable(self, risk_reward_ratio: float, min_rr: float = 1.5) -> bool:
        """
        Kiểm tra xem tỷ lệ R/R có chấp nhận được không
        
        Args:
            risk_reward_ratio: Tỷ lệ R/R
            min_rr: Tỷ lệ R/R tối thiểu
            
        Returns:
            Boolean cho biết R/R có được chấp nhận không
        """
        return risk_reward_ratio >= min_rr
    
    def optimize_position_size(self, account_balance: float, entry_price: float, 
                             stop_loss: float, risk_pct: float, position_type: str,
                             leverage: float = 1.0) -> Dict[str, float]:
        """
        Tối ưu kích thước vị thế dựa trên quản lý rủi ro
        
        Args:
            account_balance: Số dư tài khoản
            entry_price: Giá entry
            stop_loss: Giá stop loss
            risk_pct: Phần trăm rủi ro (ví dụ: 0.02 cho 2%)
            position_type: Loại vị thế ('long' hoặc 'short')
            leverage: Đòn bẩy
            
        Returns:
            Dict với thông tin về kích thước vị thế và rủi ro
        """
        # Tính khoảng cách % đến stop loss
        if position_type.lower() == 'long':
            stop_distance_pct = (entry_price - stop_loss) / entry_price
        else:  # short
            stop_distance_pct = (stop_loss - entry_price) / entry_price
            
        # Số tiền tối đa có thể để mất
        max_risk_amount = account_balance * risk_pct
        
        # Kích thước vị thế tối đa (không có đòn bẩy)
        max_position_size_no_leverage = max_risk_amount / stop_distance_pct
        
        # Kích thước vị thế với đòn bẩy
        max_position_size = max_position_size_no_leverage * leverage
        
        # Giá trị danh nghĩa của vị thế
        position_value = max_position_size
        
        # Số lượng đơn vị
        position_units = position_value / entry_price
        
        return {
            'max_position_size': max_position_size,
            'position_units': position_units,
            'risk_amount': max_risk_amount,
            'stop_distance_pct': stop_distance_pct,
            'leverage_used': leverage
        }

# Hàm tiện ích để thêm ATR vào DataFrame
def add_atr_to_dataframe(df: pd.DataFrame, atr_periods: int = 14) -> pd.DataFrame:
    """
    Thêm chỉ báo ATR vào DataFrame
    
    Args:
        df: DataFrame với dữ liệu giá
        atr_periods: Số nến để tính ATR
        
    Returns:
        DataFrame với thêm cột ATR
    """
    risk_manager = AdaptiveRiskManager(atr_periods=atr_periods)
    result_df = risk_manager.calculate_atr(df)
    return result_df