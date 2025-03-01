"""
Module tạo chiến lược (Strategy Factory)

Module này cung cấp các lớp và hàm để tạo ra các đối tượng chiến lược giao dịch
theo mẫu thiết kế Factory Pattern. Mỗi chiến lược được tạo ra từ factory đều
tuân theo cùng một giao diện (interface), giúp code dễ mở rộng và bảo trì hơn.
"""

import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Union
import traceback

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("strategy_factory")

class BaseStrategy:
    """Lớp cơ sở cho tất cả các chiến lược"""
    
    def __init__(self, name: str, parameters: Dict = None):
        """
        Khởi tạo chiến lược
        
        Args:
            name (str): Tên chiến lược
            parameters (Dict, optional): Tham số chiến lược
        """
        self.name = name
        self.parameters = parameters or {}
        self.last_signal = 0
        self.last_position = None
        self.position_count = 0
        self.win_count = 0
        self.loss_count = 0
        
    def generate_signal(self, data: Union[pd.DataFrame, Dict], **kwargs) -> Union[int, Dict]:
        """
        Tạo tín hiệu giao dịch từ dữ liệu
        
        Args:
            data (pd.DataFrame | Dict): Dữ liệu thị trường
            **kwargs: Các tham số bổ sung
            
        Returns:
            int | Dict: Tín hiệu giao dịch (1: mua, -1: bán, 0: không giao dịch)
                        hoặc Dict chứa thông tin chi tiết về tín hiệu
        """
        raise NotImplementedError("Phương thức generate_signal phải được ghi đè")
    
    def update_parameters(self, parameters: Dict) -> bool:
        """
        Cập nhật tham số chiến lược
        
        Args:
            parameters (Dict): Tham số mới
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        if parameters is None:
            return False
            
        self.parameters.update(parameters)
        return True
    
    def get_name(self) -> str:
        """
        Lấy tên chiến lược
        
        Returns:
            str: Tên chiến lược
        """
        return self.name
    
    def get_parameters(self) -> Dict:
        """
        Lấy tham số hiện tại của chiến lược
        
        Returns:
            Dict: Tham số hiện tại
        """
        return self.parameters
    
    def update_performance(self, is_win: bool) -> None:
        """
        Cập nhật thông tin hiệu suất
        
        Args:
            is_win (bool): Giao dịch thắng hay thua
        """
        self.position_count += 1
        if is_win:
            self.win_count += 1
        else:
            self.loss_count += 1
    
    def get_performance(self) -> Dict:
        """
        Lấy thông tin hiệu suất
        
        Returns:
            Dict: Thông tin hiệu suất
        """
        win_rate = self.win_count / self.position_count if self.position_count > 0 else 0
        return {
            'position_count': self.position_count,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': win_rate
        }
    
    def adapt_to_market_regime(self, regime: str) -> None:
        """
        Điều chỉnh tham số theo chế độ thị trường
        
        Args:
            regime (str): Chế độ thị trường
        """
        # Phương thức này có thể được ghi đè bởi các lớp con
        pass

class RSIStrategy(BaseStrategy):
    """Chiến lược giao dịch dựa trên RSI"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược RSI
        
        Args:
            parameters (Dict, optional): Tham số chiến lược
        """
        default_params = {
            'period': 14,
            'overbought': 70,
            'oversold': 30,
            'use_divergence': False,
            'exit_threshold': 50
        }
        
        # Cập nhật tham số mặc định với tham số đã cho
        if parameters:
            default_params.update(parameters)
            
        super().__init__('RSI Strategy', default_params)
    
    def generate_signal(self, data: Union[pd.DataFrame, Dict], **kwargs) -> Union[int, Dict]:
        """
        Tạo tín hiệu giao dịch từ dữ liệu
        
        Args:
            data (pd.DataFrame | Dict): Dữ liệu thị trường
            **kwargs: Các tham số bổ sung
            
        Returns:
            int | Dict: Tín hiệu giao dịch
        """
        try:
            # Xử lý khi data là Dict (đa khung thời gian)
            if isinstance(data, dict):
                df = data.get('primary', None)
                if df is None and len(data) > 0:
                    # Lấy DataFrame đầu tiên trong dict
                    df = next(iter(data.values()))
            else:
                df = data
                
            if df is None or len(df) < self.parameters['period']:
                return 0
                
            # Đảm bảo có cột RSI
            if 'rsi' not in df.columns:
                # Tính RSI nếu chưa có
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                
                avg_gain = gain.rolling(window=self.parameters['period']).mean()
                avg_loss = loss.rolling(window=self.parameters['period']).mean()
                
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
                df['rsi'] = rsi
            
            # Lấy giá trị RSI gần nhất
            current_rsi = df['rsi'].iloc[-1]
            previous_rsi = df['rsi'].iloc[-2] if len(df) > 1 else None
            
            signal = 0
            strength = 0
            reason = ""
            
            # Chiến lược RSI cơ bản
            if current_rsi < self.parameters['oversold']:
                signal = 1
                strength = (self.parameters['oversold'] - current_rsi) / self.parameters['oversold']
                reason = f"RSI quá bán ({current_rsi:.2f} < {self.parameters['oversold']})"
                
            elif current_rsi > self.parameters['overbought']:
                signal = -1
                strength = (current_rsi - self.parameters['overbought']) / (100 - self.parameters['overbought'])
                reason = f"RSI quá mua ({current_rsi:.2f} > {self.parameters['overbought']})"
            
            # Tín hiệu thoát
            elif (self.last_signal == 1 and current_rsi > self.parameters['exit_threshold']) or \
                 (self.last_signal == -1 and current_rsi < self.parameters['exit_threshold']):
                signal = 0
                strength = 0.5
                reason = f"RSI đạt ngưỡng thoát ({current_rsi:.2f})"
            
            # Phát hiện phân kỳ nếu được kích hoạt
            if self.parameters['use_divergence'] and previous_rsi is not None and len(df) > 5:
                # Phân kỳ dương (Bullish Divergence)
                if (df['close'].iloc[-1] < df['close'].iloc[-2]) and (current_rsi > previous_rsi) and current_rsi < 40:
                    signal = 1
                    strength = 0.8
                    reason = "Phân kỳ dương (Bullish Divergence)"
                
                # Phân kỳ âm (Bearish Divergence)
                elif (df['close'].iloc[-1] > df['close'].iloc[-2]) and (current_rsi < previous_rsi) and current_rsi > 60:
                    signal = -1
                    strength = 0.8
                    reason = "Phân kỳ âm (Bearish Divergence)"
            
            # Cập nhật tín hiệu gần nhất
            self.last_signal = signal
            
            # Trả về kết quả chi tiết
            result = {
                'signal': signal,
                'strength': min(1.0, max(0.0, strength)),
                'reason': reason,
                'value': current_rsi,
                'parameters': self.parameters
            }
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu RSI: {str(e)}")
            return 0
    
    def adapt_to_market_regime(self, regime: str) -> None:
        """Điều chỉnh tham số theo chế độ thị trường"""
        if regime == 'trending_up':
            self.parameters['overbought'] = 80
            self.parameters['oversold'] = 40
            self.parameters['exit_threshold'] = 60
        elif regime == 'trending_down':
            self.parameters['overbought'] = 60
            self.parameters['oversold'] = 20
            self.parameters['exit_threshold'] = 40
        elif regime == 'ranging':
            self.parameters['overbought'] = 70
            self.parameters['oversold'] = 30
            self.parameters['exit_threshold'] = 50
        elif regime == 'volatile':
            self.parameters['overbought'] = 75
            self.parameters['oversold'] = 25
            self.parameters['exit_threshold'] = 50
            self.parameters['use_divergence'] = True
        elif regime == 'quiet':
            self.parameters['overbought'] = 65
            self.parameters['oversold'] = 35
            self.parameters['exit_threshold'] = 50

class MACDStrategy(BaseStrategy):
    """Chiến lược giao dịch dựa trên MACD"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược MACD
        
        Args:
            parameters (Dict, optional): Tham số chiến lược
        """
        default_params = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'hist_threshold': 0,
            'signal_cross_only': False
        }
        
        # Cập nhật tham số mặc định với tham số đã cho
        if parameters:
            default_params.update(parameters)
            
        super().__init__('MACD Strategy', default_params)
    
    def generate_signal(self, data: Union[pd.DataFrame, Dict], **kwargs) -> Union[int, Dict]:
        """
        Tạo tín hiệu giao dịch từ dữ liệu
        
        Args:
            data (pd.DataFrame | Dict): Dữ liệu thị trường
            **kwargs: Các tham số bổ sung
            
        Returns:
            int | Dict: Tín hiệu giao dịch
        """
        try:
            # Xử lý khi data là Dict (đa khung thời gian)
            if isinstance(data, dict):
                df = data.get('primary', None)
                if df is None and len(data) > 0:
                    # Lấy DataFrame đầu tiên trong dict
                    df = next(iter(data.values()))
            else:
                df = data
                
            min_period = max(self.parameters['fast_period'], self.parameters['slow_period'], self.parameters['signal_period'])
            if df is None or len(df) < min_period:
                return 0
                
            # Đảm bảo có các cột MACD
            if 'macd' not in df.columns or 'macd_signal' not in df.columns or 'macd_hist' not in df.columns:
                # Tính MACD nếu chưa có
                ema_fast = df['close'].ewm(span=self.parameters['fast_period'], adjust=False).mean()
                ema_slow = df['close'].ewm(span=self.parameters['slow_period'], adjust=False).mean()
                
                macd_line = ema_fast - ema_slow
                signal_line = macd_line.ewm(span=self.parameters['signal_period'], adjust=False).mean()
                histogram = macd_line - signal_line
                
                df['macd'] = macd_line
                df['macd_signal'] = signal_line
                df['macd_hist'] = histogram
            
            # Lấy giá trị MACD gần nhất
            current_macd = df['macd'].iloc[-1]
            current_signal = df['macd_signal'].iloc[-1]
            current_hist = df['macd_hist'].iloc[-1]
            
            previous_macd = df['macd'].iloc[-2] if len(df) > 1 else None
            previous_signal = df['macd_signal'].iloc[-2] if len(df) > 1 else None
            previous_hist = df['macd_hist'].iloc[-2] if len(df) > 1 else None
            
            signal = 0
            strength = 0
            reason = ""
            
            # Tín hiệu giao nhau của MACD và Signal Line
            if self.parameters['signal_cross_only']:
                if previous_macd is not None and previous_signal is not None:
                    # Giao cắt từ dưới lên (bullish)
                    if (current_macd > current_signal) and (previous_macd <= previous_signal):
                        signal = 1
                        strength = min(1.0, abs(current_macd - current_signal) * 10)
                        reason = "MACD cắt lên Signal Line"
                    
                    # Giao cắt từ trên xuống (bearish)
                    elif (current_macd < current_signal) and (previous_macd >= previous_signal):
                        signal = -1
                        strength = min(1.0, abs(current_macd - current_signal) * 10)
                        reason = "MACD cắt xuống Signal Line"
            else:
                # Dựa vào histogram (MACD - Signal)
                if previous_hist is not None:
                    # Từ âm sang dương (bullish)
                    if (current_hist > self.parameters['hist_threshold']) and (previous_hist <= self.parameters['hist_threshold']):
                        signal = 1
                        strength = min(1.0, abs(current_hist) * 5)
                        reason = "MACD Histogram chuyển từ âm sang dương"
                    
                    # Từ dương sang âm (bearish)
                    elif (current_hist < self.parameters['hist_threshold']) and (previous_hist >= self.parameters['hist_threshold']):
                        signal = -1
                        strength = min(1.0, abs(current_hist) * 5)
                        reason = "MACD Histogram chuyển từ dương sang âm"
                    
                    # Histogram tăng mạnh
                    elif (current_hist > 0) and (current_hist > previous_hist * 1.5) and (current_hist > 0.001 * df['close'].iloc[-1]):
                        signal = 1
                        strength = 0.7
                        reason = "MACD Histogram tăng mạnh"
                    
                    # Histogram giảm mạnh
                    elif (current_hist < 0) and (current_hist < previous_hist * 1.5) and (abs(current_hist) > 0.001 * df['close'].iloc[-1]):
                        signal = -1
                        strength = 0.7
                        reason = "MACD Histogram giảm mạnh"
            
            # Cập nhật tín hiệu gần nhất
            self.last_signal = signal
            
            # Trả về kết quả chi tiết
            result = {
                'signal': signal,
                'strength': min(1.0, max(0.0, strength)),
                'reason': reason,
                'value': {
                    'macd': current_macd,
                    'signal': current_signal,
                    'histogram': current_hist
                },
                'parameters': self.parameters
            }
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu MACD: {str(e)}")
            return 0
    
    def adapt_to_market_regime(self, regime: str) -> None:
        """Điều chỉnh tham số theo chế độ thị trường"""
        if regime == 'trending_up' or regime == 'trending_down':
            self.parameters['fast_period'] = 8
            self.parameters['slow_period'] = 21
            self.parameters['signal_period'] = 9
            self.parameters['signal_cross_only'] = True
        elif regime == 'ranging':
            self.parameters['fast_period'] = 12
            self.parameters['slow_period'] = 26
            self.parameters['signal_period'] = 9
            self.parameters['signal_cross_only'] = False
        elif regime == 'volatile':
            self.parameters['fast_period'] = 6
            self.parameters['slow_period'] = 13
            self.parameters['signal_period'] = 4
            self.parameters['hist_threshold'] = 0.0005
        elif regime == 'quiet':
            self.parameters['fast_period'] = 16
            self.parameters['slow_period'] = 32
            self.parameters['signal_period'] = 12
            self.parameters['hist_threshold'] = 0

class EMACrossStrategy(BaseStrategy):
    """Chiến lược giao dịch dựa trên giao cắt EMA"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược EMA Cross
        
        Args:
            parameters (Dict, optional): Tham số chiến lược
        """
        default_params = {
            'fast_period': 9,
            'slow_period': 21,
            'confirmation_period': 1,
            'use_slope': True
        }
        
        # Cập nhật tham số mặc định với tham số đã cho
        if parameters:
            default_params.update(parameters)
            
        super().__init__('EMA Cross Strategy', default_params)
    
    def generate_signal(self, data: Union[pd.DataFrame, Dict], **kwargs) -> Union[int, Dict]:
        """
        Tạo tín hiệu giao dịch từ dữ liệu
        
        Args:
            data (pd.DataFrame | Dict): Dữ liệu thị trường
            **kwargs: Các tham số bổ sung
            
        Returns:
            int | Dict: Tín hiệu giao dịch
        """
        try:
            # Xử lý khi data là Dict (đa khung thời gian)
            if isinstance(data, dict):
                df = data.get('primary', None)
                if df is None and len(data) > 0:
                    # Lấy DataFrame đầu tiên trong dict
                    df = next(iter(data.values()))
            else:
                df = data
                
            if df is None or len(df) < self.parameters['slow_period'] + self.parameters['confirmation_period']:
                return 0
                
            # Tính EMA nếu chưa có
            fast_col = f"ema_{self.parameters['fast_period']}"
            slow_col = f"ema_{self.parameters['slow_period']}"
            
            if fast_col not in df.columns:
                df[fast_col] = df['close'].ewm(span=self.parameters['fast_period'], adjust=False).mean()
                
            if slow_col not in df.columns:
                df[slow_col] = df['close'].ewm(span=self.parameters['slow_period'], adjust=False).mean()
            
            # Lấy giá trị EMA hiện tại và trước đó
            current_fast_ema = df[fast_col].iloc[-1]
            current_slow_ema = df[slow_col].iloc[-1]
            
            prev_fast_ema = df[fast_col].iloc[-2] if len(df) > 1 else None
            prev_slow_ema = df[slow_col].iloc[-2] if len(df) > 1 else None
            
            signal = 0
            strength = 0
            reason = ""
            
            # Đảm bảo có đủ dữ liệu để phát hiện giao cắt
            if prev_fast_ema is not None and prev_slow_ema is not None:
                # Giao cắt từ dưới lên (bullish)
                if (current_fast_ema > current_slow_ema) and (prev_fast_ema <= prev_slow_ema):
                    signal = 1
                    strength = 0.8
                    reason = f"EMA{self.parameters['fast_period']} cắt lên EMA{self.parameters['slow_period']}"
                
                # Giao cắt từ trên xuống (bearish)
                elif (current_fast_ema < current_slow_ema) and (prev_fast_ema >= prev_slow_ema):
                    signal = -1
                    strength = 0.8
                    reason = f"EMA{self.parameters['fast_period']} cắt xuống EMA{self.parameters['slow_period']}"
                
                # Kiểm tra xác nhận tín hiệu qua số ngày confirmation_period
                if self.parameters['confirmation_period'] > 1 and (signal == 1 or signal == -1):
                    confirmed = True
                    for i in range(2, self.parameters['confirmation_period'] + 1):
                        if i >= len(df):
                            confirmed = False
                            break
                            
                        if signal == 1:
                            # Kiểm tra xác nhận xu hướng tăng
                            if df[fast_col].iloc[-i] <= df[slow_col].iloc[-i]:
                                confirmed = False
                                break
                        else:
                            # Kiểm tra xác nhận xu hướng giảm
                            if df[fast_col].iloc[-i] >= df[slow_col].iloc[-i]:
                                confirmed = False
                                break
                    
                    if not confirmed:
                        signal = 0
                        reason = "Tín hiệu không được xác nhận qua đủ số ngày"
                
                # Kiểm tra độ dốc (slope) nếu được kích hoạt
                if self.parameters['use_slope'] and signal != 0:
                    # Tính độ dốc của EMA chậm
                    slow_ema_slope = (current_slow_ema - df[slow_col].iloc[-5]) / 5 if len(df) >= 5 else 0
                    slope_pct = slow_ema_slope / current_slow_ema * 100
                    
                    if signal == 1 and slope_pct <= 0:
                        signal = 0
                        reason = f"EMA{self.parameters['slow_period']} không tăng (độ dốc = {slope_pct:.2f}%)"
                    elif signal == -1 and slope_pct >= 0:
                        signal = 0
                        reason = f"EMA{self.parameters['slow_period']} không giảm (độ dốc = {slope_pct:.2f}%)"
            
            # Cập nhật tín hiệu gần nhất
            self.last_signal = signal
            
            # Trả về kết quả chi tiết
            result = {
                'signal': signal,
                'strength': min(1.0, max(0.0, strength)),
                'reason': reason,
                'value': {
                    'fast_ema': current_fast_ema,
                    'slow_ema': current_slow_ema
                },
                'parameters': self.parameters
            }
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu EMA Cross: {str(e)}")
            return 0
    
    def adapt_to_market_regime(self, regime: str) -> None:
        """Điều chỉnh tham số theo chế độ thị trường"""
        if regime == 'trending_up' or regime == 'trending_down':
            self.parameters['fast_period'] = 9
            self.parameters['slow_period'] = 21
            self.parameters['confirmation_period'] = 1
            self.parameters['use_slope'] = True
        elif regime == 'ranging':
            self.parameters['fast_period'] = 5
            self.parameters['slow_period'] = 15
            self.parameters['confirmation_period'] = 2
            self.parameters['use_slope'] = False
        elif regime == 'volatile':
            self.parameters['fast_period'] = 5
            self.parameters['slow_period'] = 13
            self.parameters['confirmation_period'] = 2
            self.parameters['use_slope'] = True
        elif regime == 'quiet':
            self.parameters['fast_period'] = 9
            self.parameters['slow_period'] = 30
            self.parameters['confirmation_period'] = 1
            self.parameters['use_slope'] = False

class BollingerBandsStrategy(BaseStrategy):
    """Chiến lược giao dịch dựa trên Bollinger Bands"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược Bollinger Bands
        
        Args:
            parameters (Dict, optional): Tham số chiến lược
        """
        default_params = {
            'period': 20,
            'std_dev': 2.0,
            'use_mean_reversion': True,
            'use_trend_confirmation': False,
            'squeeze_threshold': 0.1
        }
        
        # Cập nhật tham số mặc định với tham số đã cho
        if parameters:
            default_params.update(parameters)
            
        super().__init__('Bollinger Bands Strategy', default_params)
    
    def generate_signal(self, data: Union[pd.DataFrame, Dict], **kwargs) -> Union[int, Dict]:
        """
        Tạo tín hiệu giao dịch từ dữ liệu
        
        Args:
            data (pd.DataFrame | Dict): Dữ liệu thị trường
            **kwargs: Các tham số bổ sung
            
        Returns:
            int | Dict: Tín hiệu giao dịch
        """
        try:
            # Xử lý khi data là Dict (đa khung thời gian)
            if isinstance(data, dict):
                df = data.get('primary', None)
                if df is None and len(data) > 0:
                    # Lấy DataFrame đầu tiên trong dict
                    df = next(iter(data.values()))
            else:
                df = data
                
            if df is None or len(df) < self.parameters['period']:
                return 0
                
            # Đảm bảo có các cột Bollinger Bands
            if 'bb_middle' not in df.columns or 'bb_upper' not in df.columns or 'bb_lower' not in df.columns:
                # Tính Bollinger Bands nếu chưa có
                sma = df['close'].rolling(window=self.parameters['period']).mean()
                rolling_std = df['close'].rolling(window=self.parameters['period']).std()
                
                upper_band = sma + (rolling_std * self.parameters['std_dev'])
                lower_band = sma - (rolling_std * self.parameters['std_dev'])
                
                df['bb_middle'] = sma
                df['bb_upper'] = upper_band
                df['bb_lower'] = lower_band
                df['bb_width'] = (upper_band - lower_band) / sma
            
            # Lấy giá trị hiện tại
            current_close = df['close'].iloc[-1]
            current_middle = df['bb_middle'].iloc[-1]
            current_upper = df['bb_upper'].iloc[-1]
            current_lower = df['bb_lower'].iloc[-1]
            current_width = df['bb_width'].iloc[-1] if 'bb_width' in df.columns else (current_upper - current_lower) / current_middle
            
            # Lấy giá trị trước đó để tính toán xu hướng
            prev_close = df['close'].iloc[-2] if len(df) > 1 else None
            prev_middle = df['bb_middle'].iloc[-2] if len(df) > 1 else None
            prev_width = df['bb_width'].iloc[-2] if 'bb_width' in df.columns and len(df) > 1 else None
            
            signal = 0
            strength = 0
            reason = ""
            
            # Kịch bản 1: Mean Reversion (Quay về giá trị trung bình)
            if self.parameters['use_mean_reversion']:
                # Tín hiệu mua khi giá chạm hoặc phá vỡ band dưới
                if current_close <= current_lower:
                    signal = 1
                    strength = min(1.0, (current_lower - current_close) / current_lower * 10)
                    reason = "Giá chạm/phá vỡ dải dưới Bollinger (oversold)"
                
                # Tín hiệu bán khi giá chạm hoặc phá vỡ band trên
                elif current_close >= current_upper:
                    signal = -1
                    strength = min(1.0, (current_close - current_upper) / current_upper * 10)
                    reason = "Giá chạm/phá vỡ dải trên Bollinger (overbought)"
            
            # Kịch bản 2: Bollinger Squeeze (Sự co hẹp của dải Bollinger)
            if prev_width is not None and signal == 0:
                # Phát hiện Bollinger Squeeze
                if current_width < self.parameters['squeeze_threshold'] and current_width < prev_width:
                    # Chờ breakout
                    if current_close > current_middle and current_close > prev_close:
                        signal = 1
                        strength = 0.7
                        reason = "Bollinger Squeeze và breakout lên"
                    elif current_close < current_middle and current_close < prev_close:
                        signal = -1
                        strength = 0.7
                        reason = "Bollinger Squeeze và breakout xuống"
            
            # Kịch bản 3: Xác nhận xu hướng (nếu được kích hoạt)
            if self.parameters['use_trend_confirmation'] and prev_middle is not None and signal == 0:
                # Xu hướng tăng: giá và SMA đều tăng
                if current_close > prev_close and current_middle > prev_middle:
                    # Nếu giá ở gần dải trên, xác nhận xu hướng tăng mạnh
                    upper_distance = (current_upper - current_close) / current_close
                    if upper_distance < 0.01:  # Trong vòng 1% của dải trên
                        signal = 1
                        strength = 0.6
                        reason = "Giá gần dải trên trong xu hướng tăng mạnh"
                
                # Xu hướng giảm: giá và SMA đều giảm
                elif current_close < prev_close and current_middle < prev_middle:
                    # Nếu giá ở gần dải dưới, xác nhận xu hướng giảm mạnh
                    lower_distance = (current_close - current_lower) / current_close
                    if lower_distance < 0.01:  # Trong vòng 1% của dải dưới
                        signal = -1
                        strength = 0.6
                        reason = "Giá gần dải dưới trong xu hướng giảm mạnh"
            
            # Cập nhật tín hiệu gần nhất
            self.last_signal = signal
            
            # Trả về kết quả chi tiết
            result = {
                'signal': signal,
                'strength': min(1.0, max(0.0, strength)),
                'reason': reason,
                'value': {
                    'middle': current_middle,
                    'upper': current_upper,
                    'lower': current_lower,
                    'width': current_width
                },
                'parameters': self.parameters
            }
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu Bollinger Bands: {str(e)}")
            return 0
    
    def adapt_to_market_regime(self, regime: str) -> None:
        """Điều chỉnh tham số theo chế độ thị trường"""
        if regime == 'trending_up' or regime == 'trending_down':
            self.parameters['period'] = 20
            self.parameters['std_dev'] = 2.5
            self.parameters['use_mean_reversion'] = False
            self.parameters['use_trend_confirmation'] = True
        elif regime == 'ranging':
            self.parameters['period'] = 20
            self.parameters['std_dev'] = 2.0
            self.parameters['use_mean_reversion'] = True
            self.parameters['use_trend_confirmation'] = False
        elif regime == 'volatile':
            self.parameters['period'] = 20
            self.parameters['std_dev'] = 3.0
            self.parameters['squeeze_threshold'] = 0.15
            self.parameters['use_mean_reversion'] = True
        elif regime == 'quiet':
            self.parameters['period'] = 20
            self.parameters['std_dev'] = 1.8
            self.parameters['squeeze_threshold'] = 0.05
            self.parameters['use_mean_reversion'] = True

class CompositeStrategy(BaseStrategy):
    """Chiến lược giao dịch kết hợp nhiều chiến lược lại với nhau"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược tổng hợp
        
        Args:
            parameters (Dict, optional): Tham số chiến lược
        """
        default_params = {
            'strategies': ['rsi', 'macd', 'bbands', 'ema_cross'],
            'weights': {'rsi': 0.3, 'macd': 0.3, 'bbands': 0.2, 'ema_cross': 0.2},
            'threshold': 0.6,
            'use_veto': True
        }
        
        # Cập nhật tham số mặc định với tham số đã cho
        if parameters:
            default_params.update(parameters)
            
        super().__init__('Composite Strategy', default_params)
        
        # Khởi tạo các chiến lược thành phần
        self.strategies = {}
        self._init_strategies()
    
    def _init_strategies(self):
        """Khởi tạo các chiến lược thành phần"""
        for strategy_name in self.parameters['strategies']:
            try:
                if strategy_name.lower() == 'rsi':
                    self.strategies['rsi'] = RSIStrategy()
                elif strategy_name.lower() == 'macd':
                    self.strategies['macd'] = MACDStrategy()
                elif strategy_name.lower() == 'ema_cross':
                    self.strategies['ema_cross'] = EMACrossStrategy()
                elif strategy_name.lower() == 'bbands':
                    self.strategies['bbands'] = BollingerBandsStrategy()
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo chiến lược {strategy_name}: {str(e)}")
    
    def update_parameters(self, parameters: Dict) -> bool:
        """
        Cập nhật tham số chiến lược
        
        Args:
            parameters (Dict): Tham số mới
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        if parameters is None:
            return False
            
        # Cập nhật tham số chính
        super().update_parameters(parameters)
        
        # Khởi tạo lại các chiến lược thành phần nếu danh sách thay đổi
        if 'strategies' in parameters:
            self.strategies = {}
            self._init_strategies()
            
        # Cập nhật tham số cho các chiến lược thành phần
        for strategy_name, strategy_params in parameters.items():
            if strategy_name in self.strategies and isinstance(strategy_params, dict):
                self.strategies[strategy_name].update_parameters(strategy_params)
                
        return True
    
    def generate_signal(self, data: Union[pd.DataFrame, Dict], **kwargs) -> Union[int, Dict]:
        """
        Tạo tín hiệu giao dịch từ dữ liệu
        
        Args:
            data (pd.DataFrame | Dict): Dữ liệu thị trường
            **kwargs: Các tham số bổ sung
            
        Returns:
            int | Dict: Tín hiệu giao dịch
        """
        try:
            # Lấy tín hiệu từ từng chiến lược thành phần
            strategy_signals = {}
            veto_count = 0
            
            for name, strategy in self.strategies.items():
                try:
                    # Lấy tín hiệu từ chiến lược
                    signal_result = strategy.generate_signal(data, **kwargs)
                    
                    if isinstance(signal_result, dict):
                        signal = signal_result.get('signal', 0)
                        strength = signal_result.get('strength', 0.5)
                        reason = signal_result.get('reason', '')
                    else:
                        signal = signal_result
                        strength = 0.5
                        reason = ''
                    
                    strategy_signals[name] = {
                        'signal': signal,
                        'strength': strength,
                        'reason': reason
                    }
                    
                    # Đếm số chiến lược có tín hiệu ngược với xu hướng chung
                    if self.parameters['use_veto'] and len(strategy_signals) > 1:
                        other_signals = [s['signal'] for n, s in strategy_signals.items() if n != name]
                        if len(other_signals) > 0:
                            avg_other_signal = sum(other_signals) / len(other_signals)
                            if signal * avg_other_signal < 0:  # Tín hiệu ngược
                                veto_count += 1
                
                except Exception as e:
                    logger.error(f"Lỗi khi lấy tín hiệu từ chiến lược {name}: {str(e)}")
            
            # Tính toán tín hiệu tổng hợp
            weighted_sum = 0
            total_weight = 0
            
            for name, result in strategy_signals.items():
                weight = self.parameters['weights'].get(name, 1.0)
                weighted_sum += result['signal'] * result['strength'] * weight
                total_weight += weight
            
            if total_weight > 0:
                composite_score = weighted_sum / total_weight
            else:
                composite_score = 0
            
            # Xác định tín hiệu dựa trên ngưỡng
            signal = 0
            if composite_score >= self.parameters['threshold']:
                signal = 1
            elif composite_score <= -self.parameters['threshold']:
                signal = -1
            
            # Kiểm tra veto: nếu có bất kỳ chiến lược nào phủ quyết, hủy tín hiệu
            if self.parameters['use_veto'] and veto_count >= len(self.strategies) // 2:
                signal = 0
                composite_score = 0
            
            # Cập nhật tín hiệu gần nhất
            self.last_signal = signal
            
            # Tạo lý do chi tiết
            reasons = []
            for name, result in strategy_signals.items():
                if result['signal'] != 0:
                    direction = "MUA" if result['signal'] > 0 else "BÁN"
                    reasons.append(f"{name.upper()}: {direction} - {result['reason']}")
            
            reason_str = "\n".join(reasons)
            
            # Trả về kết quả chi tiết
            result = {
                'signal': signal,
                'strength': min(1.0, max(0.0, abs(composite_score))),
                'reason': f"Tín hiệu tổng hợp ({composite_score:.2f}):\n{reason_str}",
                'value': composite_score,
                'strategy_signals': strategy_signals,
                'parameters': self.parameters
            }
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu tổng hợp: {str(e)}")
            logger.error(traceback.format_exc())
            return 0
    
    def adapt_to_market_regime(self, regime: str) -> None:
        """Điều chỉnh tham số theo chế độ thị trường"""
        # Điều chỉnh trọng số dựa trên chế độ thị trường
        if regime == 'trending_up' or regime == 'trending_down':
            self.parameters['weights'] = {
                'rsi': 0.2, 
                'macd': 0.3, 
                'bbands': 0.1, 
                'ema_cross': 0.4
            }
            self.parameters['threshold'] = 0.5
        elif regime == 'ranging':
            self.parameters['weights'] = {
                'rsi': 0.4, 
                'macd': 0.2, 
                'bbands': 0.3, 
                'ema_cross': 0.1
            }
            self.parameters['threshold'] = 0.6
        elif regime == 'volatile':
            self.parameters['weights'] = {
                'rsi': 0.3, 
                'macd': 0.2, 
                'bbands': 0.3, 
                'ema_cross': 0.2
            }
            self.parameters['threshold'] = 0.7
            self.parameters['use_veto'] = True
        elif regime == 'quiet':
            self.parameters['weights'] = {
                'rsi': 0.25, 
                'macd': 0.25, 
                'bbands': 0.25, 
                'ema_cross': 0.25
            }
            self.parameters['threshold'] = 0.5
            self.parameters['use_veto'] = False
        
        # Điều chỉnh các chiến lược thành phần
        for strategy in self.strategies.values():
            strategy.adapt_to_market_regime(regime)

class AutoStrategy(BaseStrategy):
    """Chiến lược tự động chọn các chiến lược con phù hợp với điều kiện thị trường"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược tự động
        
        Args:
            parameters (Dict, optional): Tham số chiến lược
        """
        default_params = {
            'auto_detect_regime': True,
            'use_all_strategies': True,
            'lookback_period': 50,
            'confidence_threshold': 0.6
        }
        
        # Cập nhật tham số mặc định với tham số đã cho
        if parameters:
            default_params.update(parameters)
            
        super().__init__('Auto Strategy', default_params)
        
        # Khởi tạo các chiến lược con
        self.strategies = {
            'rsi': RSIStrategy(),
            'macd': MACDStrategy(),
            'ema_cross': EMACrossStrategy(),
            'bbands': BollingerBandsStrategy(),
            'composite': CompositeStrategy()
        }
        
        # Trạng thái hiện tại
        self.current_regime = 'unknown'
        self.current_strategy = 'composite'
        self.regime_history = []
    
    def _detect_market_regime(self, df: pd.DataFrame) -> str:
        """
        Phát hiện chế độ thị trường
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            str: Chế độ thị trường ('trending_up', 'trending_down', 'ranging', 'volatile', 'quiet')
        """
        try:
            # Đảm bảo đủ dữ liệu
            if len(df) < self.parameters['lookback_period']:
                return 'unknown'
                
            # Tính các chỉ báo cần thiết nếu chưa có
            if 'atr' not in df.columns:
                # Tính ATR
                high_low = df['high'] - df['low']
                high_close = np.abs(df['high'] - df['close'].shift())
                low_close = np.abs(df['low'] - df['close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = np.max(ranges, axis=1)
                df['atr'] = true_range.rolling(window=14).mean()
            
            if 'adx' not in df.columns:
                # Tính ADX (Sử dụng giá trị cố định để đơn giản hóa)
                df['adx'] = 0
                df['plus_di'] = 0
                df['minus_di'] = 0
            
            # Lấy dữ liệu trong lookback_period
            recent_df = df.iloc[-self.parameters['lookback_period']:]
            
            # Phát hiện trend (xu hướng)
            close_prices = recent_df['close']
            first_half = close_prices.iloc[:len(close_prices)//2]
            second_half = close_prices.iloc[len(close_prices)//2:]
            is_uptrend = second_half.mean() > first_half.mean()
            
            # Tính % biến động
            volatility = recent_df['atr'].mean() / recent_df['close'].mean() * 100
            
            # Tính độ rộng giá
            price_range = (recent_df['high'].max() - recent_df['low'].min()) / recent_df['close'].mean() * 100
            
            # Kiểm tra ADX (nếu có)
            adx_value = recent_df['adx'].iloc[-1] if 'adx' in recent_df.columns else 0
            plus_di = recent_df['plus_di'].iloc[-1] if 'plus_di' in recent_df.columns else 0
            minus_di = recent_df['minus_di'].iloc[-1] if 'minus_di' in recent_df.columns else 0
            
            # Kiểm tra tính chất dao động (ranging)
            is_ranging = np.std(close_prices.pct_change()) < 0.01  # 1% std dev
            
            # Xác định chế độ thị trường
            if adx_value > 25:
                # Thị trường có xu hướng mạnh
                if plus_di > minus_di and is_uptrend:
                    regime = 'trending_up'
                else:
                    regime = 'trending_down'
            elif volatility > 2.0:  # Biến động lớn
                regime = 'volatile'
            elif is_ranging and price_range < 5.0:  # Biên độ nhỏ
                regime = 'quiet'
            else:
                regime = 'ranging'
            
            # Cập nhật lịch sử
            self.regime_history.append(regime)
            if len(self.regime_history) > 10:
                self.regime_history.pop(0)
            
            # Lấy chế độ phổ biến nhất trong lịch sử gần đây
            from collections import Counter
            regime_counter = Counter(self.regime_history)
            self.current_regime = regime_counter.most_common(1)[0][0]
            
            return self.current_regime
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
            return 'unknown'
    
    def _select_best_strategy(self, regime: str) -> str:
        """
        Chọn chiến lược tốt nhất cho chế độ thị trường
        
        Args:
            regime (str): Chế độ thị trường
            
        Returns:
            str: Tên chiến lược tốt nhất
        """
        strategy_map = {
            'trending_up': 'ema_cross',
            'trending_down': 'ema_cross',
            'ranging': 'rsi',
            'volatile': 'bbands',
            'quiet': 'macd',
            'unknown': 'composite'
        }
        
        return strategy_map.get(regime, 'composite')
    
    def generate_signal(self, data: Union[pd.DataFrame, Dict], **kwargs) -> Union[int, Dict]:
        """
        Tạo tín hiệu giao dịch từ dữ liệu
        
        Args:
            data (pd.DataFrame | Dict): Dữ liệu thị trường
            **kwargs: Các tham số bổ sung
            
        Returns:
            int | Dict: Tín hiệu giao dịch
        """
        try:
            # Xử lý khi data là Dict (đa khung thời gian)
            if isinstance(data, dict):
                df = data.get('primary', None)
                if df is None and len(data) > 0:
                    # Lấy DataFrame đầu tiên trong dict
                    df = next(iter(data.values()))
            else:
                df = data
                
            if df is None or len(df) < 20:  # Yêu cầu tối thiểu 20 điểm dữ liệu
                return 0
            
            # Phát hiện chế độ thị trường mới nếu được kích hoạt
            regime = kwargs.get('market_regime', None)
            if regime is None and self.parameters['auto_detect_regime']:
                regime = self._detect_market_regime(df)
            
            if regime is not None and regime != 'unknown':
                self.current_regime = regime
                # Chọn chiến lược tốt nhất nếu không sử dụng tất cả
                if not self.parameters['use_all_strategies']:
                    self.current_strategy = self._select_best_strategy(regime)
                # Điều chỉnh tham số cho tất cả các chiến lược theo chế độ
                for strategy in self.strategies.values():
                    strategy.adapt_to_market_regime(regime)
            
            # Nếu sử dụng tất cả chiến lược, áp dụng chiến lược tổng hợp
            if self.parameters['use_all_strategies']:
                self.current_strategy = 'composite'
            
            # Lấy tín hiệu từ chiến lược hiện tại
            selected_strategy = self.strategies.get(self.current_strategy, self.strategies['composite'])
            signal_result = selected_strategy.generate_signal(data, **kwargs)
            
            # Thêm thông tin về chế độ thị trường và chiến lược đã chọn
            if isinstance(signal_result, dict):
                signal_result['regime'] = self.current_regime
                signal_result['selected_strategy'] = self.current_strategy
                
                # Thêm mô tả về chiến lược và chế độ
                reason = signal_result.get('reason', '')
                strategy_description = f"Chiến lược: {self.current_strategy}"
                regime_description = f"Chế độ thị trường: {self.current_regime}"
                signal_result['reason'] = f"{regime_description}\n{strategy_description}\n{reason}"
            
            return signal_result
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu tự động: {str(e)}")
            logger.error(traceback.format_exc())
            return 0

class StrategyFactory:
    """Lớp factory để tạo các đối tượng chiến lược"""
    
    @staticmethod
    def create_strategy(strategy_type: str, parameters: Dict = None, use_ml: bool = False) -> BaseStrategy:
        """
        Tạo đối tượng chiến lược mới
        
        Args:
            strategy_type (str): Loại chiến lược
            parameters (Dict, optional): Tham số chiến lược
            use_ml (bool): Có sử dụng học máy không
            
        Returns:
            BaseStrategy: Đối tượng chiến lược
        """
        try:
            # Chuẩn hóa tên chiến lược
            strategy_type = strategy_type.lower()
            
            if strategy_type == 'rsi':
                return RSIStrategy(parameters)
            elif strategy_type == 'macd':
                return MACDStrategy(parameters)
            elif strategy_type == 'ema_cross' or strategy_type == 'ema':
                return EMACrossStrategy(parameters)
            elif strategy_type == 'bbands' or strategy_type == 'bollinger':
                return BollingerBandsStrategy(parameters)
            elif strategy_type == 'composite' or strategy_type == 'combined':
                return CompositeStrategy(parameters)
            elif strategy_type == 'auto':
                return AutoStrategy(parameters)
            else:
                logger.warning(f"Loại chiến lược không hỗ trợ: {strategy_type}. Sử dụng chiến lược tự động thay thế.")
                return AutoStrategy(parameters)
        except Exception as e:
            logger.error(f"Lỗi khi tạo chiến lược {strategy_type}: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    @staticmethod
    def list_available_strategies() -> Dict[str, str]:
        """
        Liệt kê các chiến lược có sẵn
        
        Returns:
            Dict[str, str]: Danh sách các chiến lược có sẵn với mô tả
        """
        return {
            'rsi': 'Relative Strength Index - Sử dụng trong thị trường dao động (ranging)',
            'macd': 'Moving Average Convergence Divergence - Sử dụng trong thị trường xu hướng',
            'ema_cross': 'EMA Crossover - Sử dụng trong thị trường xu hướng mạnh',
            'bbands': 'Bollinger Bands - Sử dụng trong thị trường dao động và đột phá',
            'composite': 'Kết hợp nhiều chiến lược thành một tín hiệu tổng hợp',
            'auto': 'Tự động chọn chiến lược tốt nhất dựa trên điều kiện thị trường'
        }
    
    @staticmethod
    def get_default_parameters(strategy_type: str) -> Dict:
        """
        Lấy tham số mặc định cho một loại chiến lược
        
        Args:
            strategy_type (str): Loại chiến lược
            
        Returns:
            Dict: Tham số mặc định
        """
        strategy_type = strategy_type.lower()
        
        if strategy_type == 'rsi':
            return {
                'period': 14,
                'overbought': 70,
                'oversold': 30,
                'use_divergence': False,
                'exit_threshold': 50
            }
        elif strategy_type == 'macd':
            return {
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9,
                'hist_threshold': 0,
                'signal_cross_only': False
            }
        elif strategy_type == 'ema_cross' or strategy_type == 'ema':
            return {
                'fast_period': 9,
                'slow_period': 21,
                'confirmation_period': 1,
                'use_slope': True
            }
        elif strategy_type == 'bbands' or strategy_type == 'bollinger':
            return {
                'period': 20,
                'std_dev': 2.0,
                'use_mean_reversion': True,
                'use_trend_confirmation': False,
                'squeeze_threshold': 0.1
            }
        elif strategy_type == 'composite' or strategy_type == 'combined':
            return {
                'strategies': ['rsi', 'macd', 'bbands', 'ema_cross'],
                'weights': {'rsi': 0.3, 'macd': 0.3, 'bbands': 0.2, 'ema_cross': 0.2},
                'threshold': 0.6,
                'use_veto': True
            }
        elif strategy_type == 'auto':
            return {
                'auto_detect_regime': True,
                'use_all_strategies': True,
                'lookback_period': 50,
                'confidence_threshold': 0.6
            }
        else:
            return {}

def main():
    """Hàm chính để demo"""
    logging.basicConfig(level=logging.INFO)
    
    # Tạo dữ liệu mẫu
    np.random.seed(42)
    n = 100
    close = np.cumsum(np.random.normal(0, 1, n)) + 100
    high = close + np.random.normal(0, 1, n)
    low = close - np.random.normal(0, 1, n)
    volume = np.random.normal(1000, 200, n)
    
    df = pd.DataFrame({
        'open': close,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    
    # Tính RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Tạo các chiến lược
    rsi_strategy = StrategyFactory.create_strategy('rsi')
    macd_strategy = StrategyFactory.create_strategy('macd')
    composite_strategy = StrategyFactory.create_strategy('composite')
    
    # Lấy tín hiệu
    rsi_signal = rsi_strategy.generate_signal(df)
    macd_signal = macd_strategy.generate_signal(df)
    composite_signal = composite_strategy.generate_signal(df)
    
    print("RSI Signal:", rsi_signal)
    print("MACD Signal:", macd_signal)
    print("Composite Signal:", composite_signal)
    
if __name__ == "__main__":
    main()