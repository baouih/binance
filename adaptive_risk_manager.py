#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('adaptive_risk_manager')

class AdaptiveRiskManager:
    """
    Quản lý rủi ro tự động thích ứng dựa trên ATR và volatility
    """
    def __init__(self, config_path: str = 'account_risk_config.json'):
        """
        Khởi tạo quản lý rủi ro thích ứng
        
        Args:
            config_path (str): Đường dẫn tới file cấu hình rủi ro
        """
        self.config_path = config_path
        self.config = self.load_config()
        self.active_risk_level = self.config.get('active_risk_level', 'medium')
        logger.info(f"Khởi tạo Adaptive Risk Manager với mức rủi ro: {self.active_risk_level}")
        
        # Cache dữ liệu ATR để tối ưu hiệu suất
        self.atr_cache = {}
        self.volatility_cache = {}
        self.last_cache_clear = datetime.now()
    
    def load_config(self) -> Dict:
        """
        Tải cấu hình rủi ro từ file JSON
        
        Returns:
            Dict: Cấu hình rủi ro
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Đã tải cấu hình rủi ro từ {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro: {str(e)}")
            # Cấu hình mặc định nếu không thể đọc file
            return {
                "active_risk_level": "medium",
                "risk_levels": {
                    "medium": {
                        "risk_percentage": 20.0,
                        "max_open_positions": 6,
                        "base_stop_loss_pct": 3.0,
                        "base_take_profit_pct": 9.0,
                        "risk_per_trade": 3.33,
                        "base_position_size_pct": 3.33
                    }
                }
            }
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình rủi ro vào file JSON
        
        Returns:
            bool: True nếu lưu thành công, False nếu có lỗi
        """
        try:
            self.config["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Đã lưu cấu hình rủi ro vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình rủi ro: {str(e)}")
            return False
    
    def set_risk_level(self, risk_level: str) -> bool:
        """
        Thiết lập mức độ rủi ro
        
        Args:
            risk_level (str): Mức độ rủi ro mới ('very_low', 'low', 'medium', 'high', 'very_high')
            
        Returns:
            bool: True nếu thiết lập thành công, False nếu thất bại
        """
        valid_levels = ['very_low', 'low', 'medium', 'high', 'very_high']
        if risk_level not in valid_levels:
            logger.error(f"Mức rủi ro không hợp lệ: {risk_level}. Phải là một trong: {valid_levels}")
            return False
        
        if risk_level not in self.config.get('risk_levels', {}):
            logger.error(f"Không tìm thấy cấu hình cho mức rủi ro: {risk_level}")
            return False
        
        self.active_risk_level = risk_level
        self.config['active_risk_level'] = risk_level
        self.save_config()
        logger.info(f"Đã thiết lập mức rủi ro: {risk_level}")
        return True
    
    def get_current_risk_config(self) -> Dict:
        """
        Lấy cấu hình rủi ro hiện tại
        
        Returns:
            Dict: Cấu hình rủi ro hiện tại
        """
        risk_levels = self.config.get('risk_levels', {})
        return risk_levels.get(self.active_risk_level, {})
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Tính ATR (Average True Range) từ dữ liệu giá
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá (phải có 'high', 'low', 'close')
            period (int): Chu kỳ ATR
            
        Returns:
            float: Giá trị ATR
        """
        try:
            # Đảm bảo đủ dữ liệu
            if len(df) < period + 1:
                logger.warning(f"Không đủ dữ liệu để tính ATR (cần ít nhất {period + 1} nến, hiện có {len(df)} nến)")
                return None
            
            # Tính True Range
            df = df.copy()
            df['tr0'] = df['high'] - df['low']
            df['tr1'] = abs(df['high'] - df['close'].shift())
            df['tr2'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
            
            # Tính ATR
            df['atr'] = df['tr'].rolling(window=period).mean()
            
            # Lấy giá trị ATR gần nhất
            atr_value = df['atr'].iloc[-1]
            
            return atr_value
        except Exception as e:
            logger.error(f"Lỗi khi tính ATR: {str(e)}")
            return None
    
    def calculate_volatility_percentage(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Tính phần trăm biến động (ATR/price)
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            period (int): Chu kỳ tính ATR
            
        Returns:
            float: Phần trăm biến động
        """
        try:
            atr = self.calculate_atr(df, period)
            if atr is None:
                return None
                
            current_price = df['close'].iloc[-1]
            volatility = (atr / current_price) * 100
            
            return volatility
        except Exception as e:
            logger.error(f"Lỗi khi tính volatility: {str(e)}")
            return None
    
    def get_volatility_level(self, volatility: float) -> str:
        """
        Xác định mức độ biến động
        
        Args:
            volatility (float): Phần trăm biến động
            
        Returns:
            str: Mức độ biến động ('very_low', 'low', 'medium', 'high', 'extreme')
        """
        vol_settings = self.config.get('volatility_adjustment', {})
        thresholds = {
            'low': vol_settings.get('low_volatility_threshold', 1.5),
            'medium': vol_settings.get('medium_volatility_threshold', 3.0),
            'high': vol_settings.get('high_volatility_threshold', 5.0),
            'extreme': vol_settings.get('extreme_volatility_threshold', 7.0)
        }
        
        if volatility < thresholds['low']:
            return 'very_low'
        elif volatility < thresholds['medium']:
            return 'low'
        elif volatility < thresholds['high']:
            return 'medium'
        elif volatility < thresholds['extreme']:
            return 'high'
        else:
            return 'extreme'
    
    def get_position_size_adjustment(self, volatility_level: str) -> float:
        """
        Lấy hệ số điều chỉnh kích thước vị thế dựa trên mức độ biến động
        
        Args:
            volatility_level (str): Mức độ biến động
            
        Returns:
            float: Hệ số điều chỉnh kích thước vị thế
        """
        vol_settings = self.config.get('volatility_adjustment', {})
        adjustments = vol_settings.get('position_size_adjustments', {})
        
        # Lấy hệ số điều chỉnh dựa trên mức biến động
        adjustment_key = f"{volatility_level}_volatility"
        default_values = {
            'very_low_volatility': 1.2,
            'low_volatility': 1.1,
            'medium_volatility': 1.0,
            'high_volatility': 0.7,
            'extreme_volatility': 0.5
        }
        
        return adjustments.get(adjustment_key, default_values.get(adjustment_key, 1.0))
    
    def get_stop_loss_adjustment(self, volatility_level: str) -> float:
        """
        Lấy hệ số điều chỉnh stop loss dựa trên mức độ biến động
        
        Args:
            volatility_level (str): Mức độ biến động
            
        Returns:
            float: Hệ số điều chỉnh stop loss
        """
        vol_settings = self.config.get('volatility_adjustment', {})
        adjustments = vol_settings.get('stop_loss_adjustments', {})
        
        # Lấy hệ số điều chỉnh dựa trên mức biến động
        adjustment_key = f"{volatility_level}_volatility"
        default_values = {
            'very_low_volatility': 0.9,
            'low_volatility': 1.0,
            'medium_volatility': 1.1,
            'high_volatility': 1.3,
            'extreme_volatility': 1.5
        }
        
        return adjustments.get(adjustment_key, default_values.get(adjustment_key, 1.0))
    
    def get_leverage_adjustment(self, volatility_level: str) -> float:
        """
        Lấy hệ số điều chỉnh đòn bẩy dựa trên mức độ biến động
        
        Args:
            volatility_level (str): Mức độ biến động
            
        Returns:
            float: Hệ số điều chỉnh đòn bẩy
        """
        vol_settings = self.config.get('volatility_adjustment', {})
        adjustments = vol_settings.get('leverage_adjustments', {})
        
        # Lấy hệ số điều chỉnh dựa trên mức biến động
        adjustment_key = f"{volatility_level}_volatility"
        default_values = {
            'very_low_volatility': 1.2,
            'low_volatility': 1.1,
            'medium_volatility': 1.0,
            'high_volatility': 0.7,
            'extreme_volatility': 0.5
        }
        
        return adjustments.get(adjustment_key, default_values.get(adjustment_key, 1.0))
    
    def calculate_atr_based_stop_loss(self, df: pd.DataFrame, side: str) -> float:
        """
        Tính stop loss dựa trên ATR
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            side (str): 'BUY' hoặc 'SELL'
            
        Returns:
            float: Giá trị stop loss
        """
        try:
            # Tính ATR
            atr_period = self.config.get('atr_settings', {}).get('atr_period', 14)
            atr = self.calculate_atr(df, atr_period)
            if atr is None:
                logger.warning("Không thể tính ATR, sử dụng stop loss cơ sở")
                base_sl_pct = self.get_current_risk_config().get('base_stop_loss_pct', 3.0)
                current_price = df['close'].iloc[-1]
                return self._apply_percentage_to_price(current_price, base_sl_pct, side)
            
            # Lấy hệ số ATR cho stop loss
            atr_multiplier = self.config.get('atr_settings', {}).get('atr_multiplier', {}).get(
                self.active_risk_level, 2.0)
            
            # Tính volatility và điều chỉnh stop loss
            volatility = self.calculate_volatility_percentage(df, atr_period)
            volatility_level = self.get_volatility_level(volatility)
            sl_adjustment = self.get_stop_loss_adjustment(volatility_level)
            
            # Tính khoảng cách stop loss
            adjusted_atr_multiplier = atr_multiplier * sl_adjustment
            sl_distance = atr * adjusted_atr_multiplier
            
            # Giới hạn stop loss (min/max)
            current_price = df['close'].iloc[-1]
            min_sl_pct = self.config.get('atr_settings', {}).get('min_atr_stop_loss_pct', {}).get(
                self.active_risk_level, 1.0)
            max_sl_pct = self.config.get('atr_settings', {}).get('max_atr_stop_loss_pct', {}).get(
                self.active_risk_level, 5.0)
            
            min_sl_distance = current_price * (min_sl_pct / 100)
            max_sl_distance = current_price * (max_sl_pct / 100)
            
            # Đảm bảo khoảng cách stop loss nằm trong giới hạn
            sl_distance = max(min_sl_distance, min(sl_distance, max_sl_distance))
            
            # Tính giá stop loss
            if side.upper() == 'BUY':
                stop_loss = current_price - sl_distance
            else:  # SELL
                stop_loss = current_price + sl_distance
            
            logger.info(f"Đã tính stop loss dựa trên ATR: {stop_loss:.2f} (ATR: {atr:.2f}, "
                       f"Volatility: {volatility:.2f}%, Level: {volatility_level}, "
                       f"Adjustment: {sl_adjustment:.2f}x)")
            
            return stop_loss
        except Exception as e:
            logger.error(f"Lỗi khi tính stop loss dựa trên ATR: {str(e)}")
            # Fallback về SL cơ sở
            base_sl_pct = self.get_current_risk_config().get('base_stop_loss_pct', 3.0)
            current_price = df['close'].iloc[-1]
            return self._apply_percentage_to_price(current_price, base_sl_pct, side)
    
    def calculate_atr_based_take_profit(self, df: pd.DataFrame, side: str) -> float:
        """
        Tính take profit dựa trên ATR
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            side (str): 'BUY' hoặc 'SELL'
            
        Returns:
            float: Giá trị take profit
        """
        try:
            # Tính ATR
            atr_period = self.config.get('atr_settings', {}).get('atr_period', 14)
            atr = self.calculate_atr(df, atr_period)
            if atr is None:
                logger.warning("Không thể tính ATR, sử dụng take profit cơ sở")
                base_tp_pct = self.get_current_risk_config().get('base_take_profit_pct', 9.0)
                current_price = df['close'].iloc[-1]
                return self._apply_percentage_to_price(current_price, base_tp_pct, side, is_tp=True)
            
            # Lấy hệ số ATR cho take profit
            tp_atr_multiplier = self.config.get('atr_settings', {}).get('take_profit_atr_multiplier', {}).get(
                self.active_risk_level, 6.0)
            
            # Tính khoảng cách take profit
            tp_distance = atr * tp_atr_multiplier
            
            # Tính giá take profit
            current_price = df['close'].iloc[-1]
            if side.upper() == 'BUY':
                take_profit = current_price + tp_distance
            else:  # SELL
                take_profit = current_price - tp_distance
            
            logger.info(f"Đã tính take profit dựa trên ATR: {take_profit:.2f} (ATR: {atr:.2f}, "
                       f"Multiplier: {tp_atr_multiplier:.2f}x)")
            
            return take_profit
        except Exception as e:
            logger.error(f"Lỗi khi tính take profit dựa trên ATR: {str(e)}")
            # Fallback về TP cơ sở
            base_tp_pct = self.get_current_risk_config().get('base_take_profit_pct', 9.0)
            current_price = df['close'].iloc[-1]
            return self._apply_percentage_to_price(current_price, base_tp_pct, side, is_tp=True)
    
    def _apply_percentage_to_price(self, price: float, percentage: float, side: str, is_tp: bool = False) -> float:
        """
        Áp dụng phần trăm vào giá để tính stop loss hoặc take profit
        
        Args:
            price (float): Giá hiện tại
            percentage (float): Phần trăm
            side (str): 'BUY' hoặc 'SELL'
            is_tp (bool): True nếu là take profit, False nếu là stop loss
            
        Returns:
            float: Giá đã áp dụng phần trăm
        """
        factor = percentage / 100
        
        if side.upper() == 'BUY':
            if is_tp:
                return price * (1 + factor)
            else:
                return price * (1 - factor)
        else:  # SELL
            if is_tp:
                return price * (1 - factor)
            else:
                return price * (1 + factor)
    
    def calculate_position_size(self, df: pd.DataFrame, symbol: str) -> float:
        """
        Tính kích thước vị thế thích ứng dựa trên biến động
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            symbol (str): Mã cặp giao dịch
            
        Returns:
            float: Kích thước vị thế
        """
        try:
            # Lấy kích thước vị thế cơ sở
            base_position_size_pct = self.get_current_risk_config().get('base_position_size_pct', 3.33)
            
            # Tính volatility và lấy hệ số điều chỉnh
            volatility = self.calculate_volatility_percentage(df)
            if volatility is None:
                logger.warning("Không thể tính volatility, sử dụng kích thước vị thế cơ sở")
                return base_position_size_pct
            
            volatility_level = self.get_volatility_level(volatility)
            position_size_adjustment = self.get_position_size_adjustment(volatility_level)
            
            # Tính kích thước vị thế đã điều chỉnh
            adjusted_position_size_pct = base_position_size_pct * position_size_adjustment
            
            logger.info(f"Đã tính kích thước vị thế thích ứng cho {symbol}: {adjusted_position_size_pct:.2f}% "
                       f"(Cơ sở: {base_position_size_pct:.2f}%, Volatility: {volatility:.2f}%, "
                       f"Level: {volatility_level}, Adjustment: {position_size_adjustment:.2f}x)")
            
            return adjusted_position_size_pct
        except Exception as e:
            logger.error(f"Lỗi khi tính kích thước vị thế: {str(e)}")
            # Fallback về kích thước cơ sở
            return self.get_current_risk_config().get('base_position_size_pct', 3.33)
    
    def calculate_adaptive_leverage(self, df: pd.DataFrame, symbol: str) -> int:
        """
        Tính đòn bẩy thích ứng dựa trên biến động
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            symbol (str): Mã cặp giao dịch
            
        Returns:
            int: Giá trị đòn bẩy
        """
        try:
            # Lấy đòn bẩy cơ sở
            max_leverage = self.get_current_risk_config().get('max_leverage', 3)
            
            # Kiểm tra xem tính năng auto leverage có được bật không
            if not self.config.get('trading_preferences', {}).get('auto_leverage_adjustment', True):
                return max_leverage
            
            # Tính volatility và lấy hệ số điều chỉnh
            volatility = self.calculate_volatility_percentage(df)
            if volatility is None:
                logger.warning("Không thể tính volatility, sử dụng đòn bẩy cơ sở")
                return max_leverage
            
            volatility_level = self.get_volatility_level(volatility)
            leverage_adjustment = self.get_leverage_adjustment(volatility_level)
            
            # Tính đòn bẩy đã điều chỉnh và làm tròn
            adjusted_leverage = round(max_leverage * leverage_adjustment)
            
            # Đảm bảo đòn bẩy tối thiểu là 1
            adjusted_leverage = max(1, adjusted_leverage)
            
            logger.info(f"Đã tính đòn bẩy thích ứng cho {symbol}: {adjusted_leverage}x "
                       f"(Cơ sở: {max_leverage}x, Volatility: {volatility:.2f}%, "
                       f"Level: {volatility_level}, Adjustment: {leverage_adjustment:.2f}x)")
            
            return adjusted_leverage
        except Exception as e:
            logger.error(f"Lỗi khi tính đòn bẩy thích ứng: {str(e)}")
            # Fallback về leverage cơ sở
            return self.get_current_risk_config().get('max_leverage', 3)
    
    def should_enter_trade_time_filter(self) -> bool:
        """
        Kiểm tra bộ lọc thời gian - có nên vào lệnh tại thời điểm hiện tại không
        
        Returns:
            bool: True nếu nên vào lệnh, False nếu không
        """
        # Kiểm tra xem tính năng time filter có được bật không
        if not self.config.get('time_filter', {}).get('enabled', True):
            return True
            
        now = datetime.now()
        day_of_week = now.strftime('%A').lower()
        hour = now.hour
        
        # Kiểm tra có phải thời điểm biến động cao cần tránh không
        if self.config.get('time_filter', {}).get('avoid_high_volatility_times', True):
            high_volatility_periods = self.config.get('time_filter', {}).get('high_volatility_periods', [])
            
            for period in high_volatility_periods:
                period_day = period.get('day', 'all').lower()
                period_hours = period.get('hours', [])
                
                if (period_day == 'all' or period_day == day_of_week) and hour in period_hours:
                    logger.info(f"Tránh vào lệnh vào thời điểm biến động cao: {day_of_week} {hour}:00")
                    return False
        
        # Kiểm tra có phải thời điểm giao dịch ưu tiên không
        preferred_times = self.config.get('time_filter', {}).get('preferred_trading_times', [])
        if preferred_times:
            for time_slot in preferred_times:
                time_day = time_slot.get('day', 'all').lower()
                time_hours = time_slot.get('hours', [])
                
                if (time_day == 'all' or time_day == day_of_week) and hour in time_hours:
                    return True
            
            # Nếu có preferred_times nhưng không nằm trong đó
            logger.info(f"Thời điểm hiện tại không phải là thời gian giao dịch ưu tiên: {day_of_week} {hour}:00")
            return False
        
        # Mặc định cho phép giao dịch nếu không có quy tắc nào ảnh hưởng
        return True
    
    def get_trade_parameters(self, df: pd.DataFrame, symbol: str, side: str) -> Dict:
        """
        Tính toán tất cả các tham số giao dịch
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            symbol (str): Mã cặp giao dịch
            side (str): 'BUY' hoặc 'SELL'
            
        Returns:
            Dict: Các tham số giao dịch đã tính toán
        """
        # Làm mới cache ATR nếu đã quá 1 giờ
        if (datetime.now() - self.last_cache_clear).seconds > 3600:
            self.atr_cache = {}
            self.volatility_cache = {}
            self.last_cache_clear = datetime.now()
        
        # Tính toán các tham số
        position_size_pct = self.calculate_position_size(df, symbol)
        leverage = self.calculate_adaptive_leverage(df, symbol)
        stop_loss = self.calculate_atr_based_stop_loss(df, side)
        take_profit = self.calculate_atr_based_take_profit(df, side)
        
        # Kiểm tra bộ lọc thời gian
        time_filter_passed = self.should_enter_trade_time_filter()
        
        # Định dạng tham số
        current_price = df['close'].iloc[-1]
        entry_price = current_price  # Có thể thay bằng limit order nếu cần
        
        # Tính giá trị ATR để tham khảo
        atr_period = self.config.get('atr_settings', {}).get('atr_period', 14)
        atr = self.calculate_atr(df, atr_period)
        volatility = self.calculate_volatility_percentage(df, atr_period)
        volatility_level = self.get_volatility_level(volatility) if volatility is not None else 'unknown'
        
        # Tính SL/TP bằng % so với giá vào
        if side.upper() == 'BUY':
            sl_percentage = ((entry_price - stop_loss) / entry_price) * 100
            tp_percentage = ((take_profit - entry_price) / entry_price) * 100
        else:  # SELL
            sl_percentage = ((stop_loss - entry_price) / entry_price) * 100
            tp_percentage = ((entry_price - take_profit) / entry_price) * 100
        
        # Số vị thế tối đa
        max_positions = self.get_current_risk_config().get('max_open_positions', 6)
        
        parameters = {
            'symbol': symbol,
            'side': side.upper(),
            'entry_price': entry_price,
            'position_size_percentage': position_size_pct,
            'leverage': leverage,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'stop_loss_percentage': sl_percentage,
            'take_profit_percentage': tp_percentage,
            'risk_level': self.active_risk_level,
            'max_positions': max_positions,
            'time_filter_passed': time_filter_passed,
            'atr': atr,
            'volatility_percentage': volatility,
            'volatility_level': volatility_level,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Thêm thông tin về trailing stop nếu được bật
        adaptive_sl = self.config.get('adaptive_stop_loss', {})
        if adaptive_sl.get('enabled', True):
            parameters['use_trailing_stop'] = adaptive_sl.get('use_trailing_stop', True)
            parameters['trailing_activation_threshold'] = adaptive_sl.get('activation_threshold', 1.0)
            
            if atr is not None:
                # Tính khoảng cách trailing dựa trên ATR
                trailing_distance_multiplier = adaptive_sl.get('trailing_distance', {}).get(
                    self.active_risk_level, 1.0)
                parameters['trailing_distance'] = atr * trailing_distance_multiplier
                
                # Thêm thông tin về partial take profit
                if adaptive_sl.get('partial_take_profit', {}).get('enabled', True):
                    parameters['use_partial_tp'] = True
                    partial_tp_levels = []
                    
                    for level in adaptive_sl.get('partial_take_profit', {}).get('levels', []):
                        target_multiplier = level.get('target', 1.5)
                        percentage = level.get('percentage', 30)
                        
                        if side.upper() == 'BUY':
                            target_price = entry_price + (atr * target_multiplier)
                        else:  # SELL
                            target_price = entry_price - (atr * target_multiplier)
                        
                        partial_tp_levels.append({
                            'target_price': target_price,
                            'percentage': percentage,
                            'atr_multiplier': target_multiplier
                        })
                    
                    parameters['partial_take_profit_levels'] = partial_tp_levels
        
        return parameters

# Sử dụng lớp AdaptiveRiskManager
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Quản lý rủi ro thích ứng')
    parser.add_argument('--set-risk-level', type=str, choices=['very_low', 'low', 'medium', 'high', 'very_high'],
                        help='Thiết lập mức độ rủi ro')
    parser.add_argument('--set-atr-multiplier', type=float,
                        help='Thiết lập hệ số ATR cho stop loss')
    parser.add_argument('--set-atr-period', type=int,
                        help='Thiết lập chu kỳ ATR')
    parser.add_argument('--toggle-adaptive-sl', type=bool,
                        help='Bật/tắt stop loss thích ứng')
    
    args = parser.parse_args()
    
    risk_manager = AdaptiveRiskManager()
    
    if args.set_risk_level:
        risk_manager.set_risk_level(args.set_risk_level)
        print(f"Đã thiết lập mức độ rủi ro: {args.set_risk_level}")
    
    if args.set_atr_multiplier:
        risk_level = risk_manager.active_risk_level
        risk_manager.config['atr_settings']['atr_multiplier'][risk_level] = args.set_atr_multiplier
        risk_manager.save_config()
        print(f"Đã thiết lập hệ số ATR cho stop loss: {args.set_atr_multiplier}")
    
    if args.set_atr_period:
        risk_manager.config['atr_settings']['atr_period'] = args.set_atr_period
        risk_manager.save_config()
        print(f"Đã thiết lập chu kỳ ATR: {args.set_atr_period}")
    
    if args.toggle_adaptive_sl is not None:
        risk_manager.config['adaptive_stop_loss']['enabled'] = args.toggle_adaptive_sl
        risk_manager.save_config()
        print(f"Đã {'bật' if args.toggle_adaptive_sl else 'tắt'} stop loss thích ứng")
    
    print("Quản lý rủi ro thích ứng đã khởi tạo thành công!")