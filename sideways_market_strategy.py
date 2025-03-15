import os
import sys
import json
import numpy as np
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path

# Tạo các hàm thay thế cho talib
def SMA(data, timeperiod):
    return pd.Series(data).rolling(window=timeperiod).mean().values

def EMA(data, timeperiod):
    return pd.Series(data).ewm(span=timeperiod, adjust=False).mean().values

def STDDEV(data, timeperiod):
    return pd.Series(data).rolling(window=timeperiod).std().values

def RSI(data, timeperiod):
    delta = pd.Series(data).diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=timeperiod-1, adjust=False).mean()
    ema_down = down.ewm(com=timeperiod-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs)).values

def ATR(high, low, close, timeperiod):
    high_s = pd.Series(high)
    low_s = pd.Series(low)
    close_s = pd.Series(close)
    
    tr1 = high_s - low_s
    tr2 = abs(high_s - close_s.shift())
    tr3 = abs(low_s - close_s.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=timeperiod).mean()
    return atr.values

def STOCH(high, low, close, fastk_period, slowk_period, slowk_matype, slowd_period, slowd_matype):
    high_s = pd.Series(high)
    low_s = pd.Series(low)
    close_s = pd.Series(close)
    
    lowest_low = low_s.rolling(window=fastk_period).min()
    highest_high = high_s.rolling(window=fastk_period).max()
    
    fastk = 100 * ((close_s - lowest_low) / (highest_high - lowest_low))
    slowk = fastk.rolling(window=slowk_period).mean()
    slowd = slowk.rolling(window=slowd_period).mean()
    
    return slowk.values, slowd.values

def CCI(high, low, close, timeperiod):
    high_s = pd.Series(high)
    low_s = pd.Series(low)
    close_s = pd.Series(close)
    
    tp = (high_s + low_s + close_s) / 3
    tp_ma = tp.rolling(window=timeperiod).mean()
    tp_md = tp.rolling(window=timeperiod).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
    
    # Avoid division by zero
    cci = (tp - tp_ma) / (0.015 * tp_md)
    cci = cci.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    return cci.values

def WILLR(high, low, close, timeperiod):
    high_s = pd.Series(high)
    low_s = pd.Series(low)
    close_s = pd.Series(close)
    
    highest_high = high_s.rolling(window=timeperiod).max()
    lowest_low = low_s.rolling(window=timeperiod).min()
    
    willr = -100 * ((highest_high - close_s) / (highest_high - lowest_low))
    return willr.values

def MOM(data, timeperiod):
    return pd.Series(data).diff(timeperiod).values

def OBV(close, volume):
    close_s = pd.Series(close)
    volume_s = pd.Series(volume)
    
    obv = pd.Series(0, index=close_s.index)
    
    for i in range(1, len(close_s)):
        if close_s.iloc[i] > close_s.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + volume_s.iloc[i]
        elif close_s.iloc[i] < close_s.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - volume_s.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv.values

# Tạo namespace để mô phỏng talib
class ta:
    SMA = SMA
    EMA = EMA
    STDDEV = STDDEV
    RSI = RSI
    ATR = ATR
    STOCH = STOCH
    CCI = CCI
    WILLR = WILLR
    MOM = MOM
    OBV = OBV

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sideways_market_strategy.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('sideways_market_strategy')

class SidewaysMarketStrategy:
    """
    Chiến lược chuyên biệt cho thị trường đi ngang (Sideways Market)
    Tối ưu hóa để nâng cao tỷ lệ thắng trong điều kiện thị trường không có xu hướng rõ ràng
    """
    
    def __init__(self, config_file=None):
        # Thiết lập mặc định
        self.default_config = {
            'range_detection': {
                'atr_period': 14,                # Giai đoạn tính ATR
                'atr_multiplier': 2.5,           # Hệ số nhân ATR để xác định biên độ
                'range_period': 24,              # Số giờ/nến để xác định thị trường đi ngang
                'max_range_percent': 5.0,        # Biên độ dao động tối đa (%) để coi là đi ngang
                'trend_slope_threshold': 0.05    # Độ dốc tối đa của đường xu hướng
            },
            'oscillator_settings': {
                'rsi_period': 14,                # Giai đoạn tính RSI
                'rsi_overbought': 70,            # Ngưỡng quá mua RSI
                'rsi_oversold': 30,              # Ngưỡng quá bán RSI
                'stoch_k_period': 14,            # Giai đoạn tính Stochastic %K
                'stoch_d_period': 3,             # Giai đoạn tính Stochastic %D
                'stoch_overbought': 80,          # Ngưỡng quá mua Stochastic
                'stoch_oversold': 20,            # Ngưỡng quá bán Stochastic
                'cci_period': 20,                # Giai đoạn tính CCI
                'cci_overbought': 100,           # Ngưỡng quá mua CCI
                'cci_oversold': -100             # Ngưỡng quá bán CCI
            },
            'bollinger_bands': {
                'bb_period': 20,                 # Giai đoạn tính Bollinger Bands
                'bb_std': 2.0,                   # Số độ lệch chuẩn
                'bb_squeeze_threshold': 0.5,     # Ngưỡng nhận diện BB Squeeze (% của ATR)
                'keltner_atr_period': 20,        # Giai đoạn tính Keltner Channel ATR
                'keltner_atr_multiplier': 2.0,   # Hệ số nhân ATR cho Keltner Channel
                'keltner_ema_period': 20         # Giai đoạn tính Keltner Channel EMA
            },
            'volume_analysis': {
                'volume_ma_period': 20,          # Giai đoạn tính khối lượng trung bình
                'volume_threshold': 1.5,         # Hệ số nhân khối lượng đột biến
                'obv_ma_period': 20,             # Giai đoạn tính OBV MA
                'vwap_period': 24                # Giai đoạn tính VWAP (1 ngày)
            },
            'signal_confirmation': {
                'min_oscillator_agreement': 2,   # Số tối thiểu chỉ báo dao động cần đồng thuận
                'min_confirmation_signals': 3,    # Số tối thiểu tín hiệu xác nhận để mở lệnh
                'exit_after_bars': 10,           # Thoát lệnh sau số nến nếu không đạt TP
                'use_trailing_stop': True,       # Sử dụng trailing stop
                'trail_after_profit': 0.5,       # Bắt đầu trailing sau khi đạt % lợi nhuận (của TP)
                'trail_distance': 0.2            # Khoảng cách trailing (% của ATR)
            },
            'position_sizing': {
                'default_risk': 0.15,             # Mặc định rủi ro 15% (cho thị trường đi ngang)
                'sl_atr_multiplier': 1.2,         # Hệ số nhân ATR để đặt SL
                'tp_sl_ratio': 1.5,               # Tỷ lệ TP:SL
                'partial_tp': [0.4, 0.7, 1.0],    # Các mức TP từng phần (% của mục tiêu)
                'tp_size': [0.3, 0.3, 0.4]        # Tỷ lệ đóng lệnh ở mỗi mức TP
            },
            'advanced_features': {
                'use_market_profile': True,       # Sử dụng Market Profile
                'use_order_flow': False,          # Sử dụng Order Flow (nếu có dữ liệu)
                'use_divergence': True,           # Tìm kiếm phân kỳ
                'use_support_resistance': True,   # Sử dụng hỗ trợ/kháng cự
                'filter_by_time': True,           # Lọc theo thời gian
                'avoid_news_events': True         # Tránh các sự kiện tin tức
            }
        }
        
        # Đọc cấu hình từ file nếu có
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {config_file}")
        else:
            self.config = self.default_config
            if config_file:
                logger.warning(f"Không tìm thấy file {config_file}, sử dụng cấu hình mặc định")
                
                # Lưu cấu hình mặc định nếu chưa có file
                os.makedirs(os.path.dirname(os.path.abspath(config_file)), exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(self.default_config, f, indent=4)
                logger.info(f"Đã lưu cấu hình mặc định vào {config_file}")
        
        # Các biến phân tích
        self.is_sideways_market = False
        self.range_high = None
        self.range_low = None
        self.range_mid = None
        self.volume_baseline = None
        self.last_signals = []
        
        logger.info(f"Khởi tạo SidewaysMarketStrategy")
    
    def detect_sideways_market(self, data):
        """
        Phát hiện thị trường đi ngang dựa trên biên độ dao động và các chỉ báo khác
        
        Parameters:
        - data: DataFrame với cột OHLCV
        
        Returns:
        - Boolean: True nếu đang trong thị trường đi ngang
        """
        # Các thiết lập
        atr_period = self.config['range_detection']['atr_period']
        atr_multiplier = self.config['range_detection']['atr_multiplier']
        range_period = self.config['range_detection']['range_period']
        max_range_percent = self.config['range_detection']['max_range_percent']
        trend_slope_threshold = self.config['range_detection']['trend_slope_threshold']
        
        # Đảm bảo đủ dữ liệu
        if len(data) < range_period + atr_period:
            logger.warning(f"Không đủ dữ liệu để xác định thị trường đi ngang")
            return False
        
        # Lấy dữ liệu gần đây
        recent_data = data.iloc[-range_period:].copy()
        
        # Tính ATR
        atr = ta.ATR(data['high'].values, data['low'].values, data['close'].values, timeperiod=atr_period)
        recent_atr = atr[-range_period:]
        
        # Tính biên độ dao động
        highest_high = recent_data['high'].max()
        lowest_low = recent_data['low'].min()
        mid_price = (highest_high + lowest_low) / 2
        
        # Tính biên độ dưới dạng phần trăm
        range_percent = (highest_high - lowest_low) / mid_price * 100
        
        # Kiểm tra độ dốc của đường xu hướng
        x = np.arange(len(recent_data))
        y = recent_data['close'].values
        slope, _ = np.polyfit(x, y, 1)
        normalized_slope = slope / mid_price * 100  # Chuẩn hóa độ dốc thành %
        
        # Kiểm tra volatility (độ biến động giá)
        avg_atr_percent = np.mean(recent_atr) / mid_price * 100
        
        # Điều kiện xác định thị trường đi ngang:
        # 1. Biên độ dao động nhỏ hơn ngưỡng cấu hình
        # 2. Độ dốc xu hướng gần bằng 0
        # 3. ATR trung bình nhỏ
        is_sideways = (range_percent < max_range_percent and 
                       abs(normalized_slope) < trend_slope_threshold)
        
        # Lưu lại các giá trị để sử dụng sau này
        if is_sideways:
            self.range_high = highest_high
            self.range_low = lowest_low
            self.range_mid = mid_price
            
            # Tính các mức quan trọng
            self.range_quarter_1 = lowest_low + (highest_high - lowest_low) * 0.25
            self.range_quarter_3 = lowest_low + (highest_high - lowest_low) * 0.75
            
            logger.info(f"Xác định thị trường đi ngang: Range={range_percent:.2f}%, Slope={normalized_slope:.4f}%")
            logger.info(f"Biên độ: High={highest_high:.2f}, Low={lowest_low:.2f}, Mid={mid_price:.2f}")
        else:
            logger.info(f"Không phải thị trường đi ngang: Range={range_percent:.2f}%, Slope={normalized_slope:.4f}%")
        
        self.is_sideways_market = is_sideways
        return is_sideways
    
    def calculate_indicators(self, data):
        """
        Tính toán các chỉ báo cần thiết cho chiến lược đi ngang
        
        Parameters:
        - data: DataFrame với cột OHLCV
        
        Returns:
        - DataFrame với các chỉ báo đã tính
        """
        df = data.copy()
        
        # Thiết lập từ cấu hình
        config_osc = self.config['oscillator_settings']
        config_bb = self.config['bollinger_bands']
        config_vol = self.config['volume_analysis']
        
        # 1. Tính Bollinger Bands
        bb_period = config_bb['bb_period']
        bb_std = config_bb['bb_std']
        df['bb_middle'] = ta.SMA(df['close'].values, timeperiod=bb_period)
        df['bb_upper'] = df['bb_middle'] + bb_std * ta.STDDEV(df['close'].values, timeperiod=bb_period)
        df['bb_lower'] = df['bb_middle'] - bb_std * ta.STDDEV(df['close'].values, timeperiod=bb_period)
        
        # 2. Tính Keltner Channels
        keltner_atr_period = config_bb['keltner_atr_period']
        keltner_ema_period = config_bb['keltner_ema_period']
        keltner_multiplier = config_bb['keltner_atr_multiplier']
        
        df['keltner_middle'] = ta.EMA(df['close'].values, timeperiod=keltner_ema_period)
        df['atr'] = ta.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=keltner_atr_period)
        df['keltner_upper'] = df['keltner_middle'] + df['atr'] * keltner_multiplier
        df['keltner_lower'] = df['keltner_middle'] - df['atr'] * keltner_multiplier
        
        # 3. Tính chỉ báo dao động
        # RSI
        rsi_period = config_osc['rsi_period']
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=rsi_period)
        
        # Stochastic
        stoch_k_period = config_osc['stoch_k_period']
        stoch_d_period = config_osc['stoch_d_period']
        df['stoch_k'], df['stoch_d'] = ta.STOCH(df['high'].values, df['low'].values, df['close'].values, 
                                                fastk_period=stoch_k_period, slowk_period=3, slowk_matype=0, 
                                                slowd_period=stoch_d_period, slowd_matype=0)
        
        # CCI
        cci_period = config_osc['cci_period']
        df['cci'] = ta.CCI(df['high'].values, df['low'].values, df['close'].values, timeperiod=cci_period)
        
        # 4. Các chỉ báo khối lượng
        # Khối lượng trung bình
        volume_ma_period = config_vol['volume_ma_period']
        df['volume_ma'] = ta.SMA(df['volume'].values, timeperiod=volume_ma_period)
        
        # On-Balance Volume (OBV)
        df['obv'] = ta.OBV(df['close'].values, df['volume'].values)
        df['obv_ma'] = ta.SMA(df['obv'].values, timeperiod=config_vol['obv_ma_period'])
        
        # 5. Chỉ báo BB Squeeze
        # BB Squeeze xảy ra khi BB nằm trong Keltner Channel
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['keltner_width'] = (df['keltner_upper'] - df['keltner_lower']) / df['keltner_middle']
        df['is_squeeze'] = df['bb_width'] < df['keltner_width'] * config_bb['bb_squeeze_threshold']
        
        # 6. Các chỉ báo tìm điểm đảo chiều
        # Momentum
        df['momentum'] = ta.MOM(df['close'].values, timeperiod=10)
        
        # Williams %R
        df['willr'] = ta.WILLR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        
        # Tính distance từ giá hiện tại đến các dải BB (phần trăm)
        df['bb_pos'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Fisher Transform của RSI (giúp phát hiện đảo chiều sớm hơn)
        # Chuyển RSI từ [0, 100] sang [-1, 1]
        df['rsi_scaled'] = df['rsi'].apply(lambda x: 0 if pd.isna(x) else (x / 100 * 2 - 1))
        
        # Tính Fisher Transform (cận logarithm)
        df['fisher_rsi'] = df['rsi_scaled'].apply(
            lambda x: 0 if abs(x) >= 0.999 or pd.isna(x) else 0.5 * np.log((1 + x) / (1 - x))
        )
        
        # Các điểm giao cắt và chỉ báo đảo chiều
        df['rsi_cross_50'] = np.where((df['rsi'].shift(1) < 50) & (df['rsi'] >= 50), 1, 
                                    np.where((df['rsi'].shift(1) > 50) & (df['rsi'] <= 50), -1, 0))
        
        df['stoch_cross'] = np.where((df['stoch_k'].shift(1) < df['stoch_d'].shift(1)) & 
                                    (df['stoch_k'] >= df['stoch_d']), 1,
                                    np.where((df['stoch_k'].shift(1) > df['stoch_d'].shift(1)) & 
                                           (df['stoch_k'] <= df['stoch_d']), -1, 0))
        
        # Điểm giao cắt giá với BB Middle
        df['price_cross_bb_mid'] = np.where((df['close'].shift(1) < df['bb_middle'].shift(1)) & 
                                           (df['close'] >= df['bb_middle']), 1,
                                           np.where((df['close'].shift(1) > df['bb_middle'].shift(1)) & 
                                                  (df['close'] <= df['bb_middle']), -1, 0))
        
        # Đối với thị trường đi ngang, xác định vị trí trong range
        if self.is_sideways_market and self.range_high is not None and self.range_low is not None:
            # Tính vị trí trong range từ 0-100%
            df['range_position'] = ((df['close'] - self.range_low) / 
                                   (self.range_high - self.range_low) * 100)
            
            # Xác định nếu giá ở gần giới hạn range (20% gần biên)
            df['near_range_top'] = df['range_position'] > 80
            df['near_range_bottom'] = df['range_position'] < 20
            df['in_range_middle'] = (df['range_position'] >= 40) & (df['range_position'] <= 60)
        
        return df
    
    def generate_sideways_signals(self, data, indicators):
        """
        Sinh tín hiệu giao dịch cho thị trường đi ngang
        
        Parameters:
        - data: DataFrame gốc
        - indicators: DataFrame với các chỉ báo đã tính
        
        Returns:
        - Tuple of (signal, signal_data)
          signal: 'LONG', 'SHORT', hoặc None
          signal_data: Dictionary với thông tin chi tiết về tín hiệu
        """
        # Nếu không phải thị trường đi ngang, trả về None
        if not self.is_sideways_market:
            return None, {'description': 'Không phải thị trường đi ngang'}
        
        # Thiết lập từ cấu hình
        config_osc = self.config['oscillator_settings']
        config_signal = self.config['signal_confirmation']
        
        # Lấy hàng cuối cùng của indicators
        last_candle = indicators.iloc[-1]
        prev_candle = indicators.iloc[-2] if len(indicators) > 1 else None
        
        # Khởi tạo danh sách tín hiệu và điểm
        signals = []
        signal_points = {'long': 0, 'short': 0}
        
        # Tạo dictionary để lưu thông tin tín hiệu
        signal_data = {
            'timestamp': data.iloc[-1]['timestamp'] if 'timestamp' in data.columns else None,
            'price': last_candle['close'],
            'indicators': {},
            'signals': {},
            'confirmation_count': {'long': 0, 'short': 0},
            'range_data': {
                'high': self.range_high,
                'low': self.range_low,
                'mid': self.range_mid,
                'position': last_candle.get('range_position', None)
            }
        }
        
        # Ghi nhận thông tin chỉ báo
        signal_data['indicators'] = {
            'rsi': last_candle['rsi'],
            'stoch_k': last_candle['stoch_k'],
            'stoch_d': last_candle['stoch_d'],
            'cci': last_candle['cci'],
            'bb_pos': last_candle['bb_pos'],
            'is_squeeze': last_candle['is_squeeze']
        }
        
        # 1. Tín hiệu từ RSI
        rsi = last_candle['rsi']
        rsi_overbought = config_osc['rsi_overbought']
        rsi_oversold = config_osc['rsi_oversold']
        
        # RSI phản ứng mạnh ở các vùng cực trị trong thị trường đi ngang
        if rsi < rsi_oversold:
            signals.append('RSI oversold')
            signal_points['long'] += 2
            signal_data['signals']['rsi'] = 'oversold'
        elif rsi > rsi_overbought:
            signals.append('RSI overbought')
            signal_points['short'] += 2
            signal_data['signals']['rsi'] = 'overbought'
        
        # RSI divergence - Phân kỳ (một trong những tín hiệu mạnh nhất cho thị trường đi ngang)
        if prev_candle is not None:
            # Tìm phân kỳ dương
            if last_candle['close'] < prev_candle['close'] and last_candle['rsi'] > prev_candle['rsi']:
                signals.append('RSI bullish divergence')
                signal_points['long'] += 3
                signal_data['signals']['rsi_divergence'] = 'bullish'
            
            # Tìm phân kỳ âm
            elif last_candle['close'] > prev_candle['close'] and last_candle['rsi'] < prev_candle['rsi']:
                signals.append('RSI bearish divergence')
                signal_points['short'] += 3
                signal_data['signals']['rsi_divergence'] = 'bearish'
        
        # 2. Tín hiệu từ Stochastic
        stoch_k = last_candle['stoch_k']
        stoch_d = last_candle['stoch_d']
        stoch_overbought = config_osc['stoch_overbought']
        stoch_oversold = config_osc['stoch_oversold']
        
        if stoch_k < stoch_oversold and stoch_d < stoch_oversold:
            signals.append('Stochastic oversold')
            signal_points['long'] += 1
            signal_data['signals']['stochastic'] = 'oversold'
        elif stoch_k > stoch_overbought and stoch_d > stoch_overbought:
            signals.append('Stochastic overbought')
            signal_points['short'] += 1
            signal_data['signals']['stochastic'] = 'overbought'
        
        # Stochastic cross - Rất quan trọng trong thị trường đi ngang
        if last_candle['stoch_cross'] == 1 and stoch_k < 50:
            signals.append('Stochastic bullish cross')
            signal_points['long'] += 2
            signal_data['signals']['stoch_cross'] = 'bullish'
        elif last_candle['stoch_cross'] == -1 and stoch_k > 50:
            signals.append('Stochastic bearish cross')
            signal_points['short'] += 2
            signal_data['signals']['stoch_cross'] = 'bearish'
        
        # 3. Tín hiệu từ CCI
        cci = last_candle['cci']
        cci_overbought = config_osc['cci_overbought']
        cci_oversold = config_osc['cci_oversold']
        
        if cci < cci_oversold:
            signals.append('CCI oversold')
            signal_points['long'] += 1
            signal_data['signals']['cci'] = 'oversold'
        elif cci > cci_overbought:
            signals.append('CCI overbought')
            signal_points['short'] += 1
            signal_data['signals']['cci'] = 'overbought'
        
        # 4. Tín hiệu từ Bollinger Bands
        bb_pos = last_candle['bb_pos']
        
        # Trong thị trường đi ngang, tỷ lệ bounce back từ các dải BB rất cao
        if bb_pos < 0.05:  # Rất gần hoặc dưới BB dưới
            signals.append('Price near lower BB')
            signal_points['long'] += 2
            signal_data['signals']['bb_position'] = 'near_lower'
        elif bb_pos > 0.95:  # Rất gần hoặc trên BB trên
            signals.append('Price near upper BB')
            signal_points['short'] += 2
            signal_data['signals']['bb_position'] = 'near_upper'
        
        # 5. Tín hiệu từ vị trí trong range
        if 'range_position' in last_candle:
            range_pos = last_candle['range_position']
            
            if range_pos < 20:  # Gần đáy range
                signals.append('Price near range bottom')
                signal_points['long'] += 3
                signal_data['signals']['range_position'] = 'near_bottom'
            elif range_pos > 80:  # Gần đỉnh range
                signals.append('Price near range top')
                signal_points['short'] += 3
                signal_data['signals']['range_position'] = 'near_top'
        
        # 6. Tín hiệu từ BB Squeeze
        if last_candle['is_squeeze']:
            signals.append('BB Squeeze detected')
            # Squeeze thường dẫn đến bùng nổ, nhưng không biết hướng
            # Cần kết hợp với các tín hiệu khác
            signal_data['signals']['bb_squeeze'] = True
            
            # Trong squeeze, ta xem xét momentum
            if last_candle['momentum'] > 0:
                signal_points['long'] += 1
            elif last_candle['momentum'] < 0:
                signal_points['short'] += 1
        
        # 7. Tín hiệu từ khối lượng
        if 'volume' in last_candle and 'volume_ma' in last_candle:
            volume_threshold = self.config['volume_analysis']['volume_threshold']
            
            if last_candle['volume'] > last_candle['volume_ma'] * volume_threshold:
                signals.append('Volume spike')
                signal_data['signals']['volume'] = 'spike'
                
                # Xem xét khối lượng kết hợp với giá
                if last_candle['close'] > last_candle['open']:
                    signal_points['long'] += 1
                else:
                    signal_points['short'] += 1
        
        # 8. Tín hiệu từ Fisher Transform RSI
        if 'fisher_rsi' in last_candle:
            fisher_rsi = last_candle['fisher_rsi']
            
            if fisher_rsi < -2.0:  # Quá bán mạnh
                signals.append('Fisher RSI extremely oversold')
                signal_points['long'] += 2
                signal_data['signals']['fisher_rsi'] = 'extremely_oversold'
            elif fisher_rsi > 2.0:  # Quá mua mạnh
                signals.append('Fisher RSI extremely overbought')
                signal_points['short'] += 2
                signal_data['signals']['fisher_rsi'] = 'extremely_overbought'
        
        # Đếm số tín hiệu xác nhận
        signal_data['confirmation_count']['long'] = signal_points['long']
        signal_data['confirmation_count']['short'] = signal_points['short']
        
        # Sinh tín hiệu dựa trên điểm và ngưỡng xác nhận
        min_confirmation = config_signal['min_confirmation_signals']
        
        signal = None
        
        if signal_points['long'] >= min_confirmation and signal_points['long'] > signal_points['short']:
            signal = 'LONG'
        elif signal_points['short'] >= min_confirmation and signal_points['short'] > signal_points['long']:
            signal = 'SHORT'
        
        # Thêm mô tả tín hiệu
        if signal:
            signal_data['decision'] = signal
            signal_data['confidence'] = max(signal_points['long'], signal_points['short'])
            signal_data['description'] = f"{signal} signal in sideways market with {len(signals)} confirmations: {', '.join(signals)}"
            logger.info(f"Tín hiệu {signal} cho thị trường đi ngang: {signal_data['description']}")
        else:
            signal_data['decision'] = 'NEUTRAL'
            signal_data['description'] = f"No clear signal in sideways market. Long points: {signal_points['long']}, Short points: {signal_points['short']}"
            logger.info(f"Không có tín hiệu rõ ràng cho thị trường đi ngang: {signal_data['description']}")
        
        # Lưu tín hiệu gần nhất
        self.last_signals.append(signal_data)
        if len(self.last_signals) > 10:
            self.last_signals.pop(0)
        
        return signal, signal_data
    
    def calculate_entry_exit_levels(self, entry_price, signal, atr_value=None):
        """
        Tính toán các mức vào lệnh, dừng lỗ, và chốt lời cho thị trường đi ngang
        
        Parameters:
        - entry_price: Giá vào lệnh
        - signal: 'LONG' hoặc 'SHORT'
        - atr_value: Giá trị ATR, nếu None sẽ sử dụng % cố định
        
        Returns:
        - Dictionary với các mức SL, TP1, TP2, TP3
        """
        config_position = self.config['position_sizing']
        sl_atr_multiplier = config_position['sl_atr_multiplier'] 
        tp_sl_ratio = config_position['tp_sl_ratio']
        partial_tp = config_position['partial_tp']
        
        # Nếu không có ATR, sử dụng % mặc định
        if atr_value is None or atr_value <= 0:
            # Trong thị trường đi ngang, dùng SL nhỏ hơn
            sl_percent = 0.01  # 1%
        else:
            # Tính SL dựa trên ATR
            sl_percent = (atr_value * sl_atr_multiplier) / entry_price
        
        # Tính TP dựa trên tỷ lệ TP:SL
        tp_percent = sl_percent * tp_sl_ratio
        
        # Tính các mức
        if signal == 'LONG':
            sl_price = entry_price * (1 - sl_percent)
            tp1 = entry_price * (1 + tp_percent * partial_tp[0])
            tp2 = entry_price * (1 + tp_percent * partial_tp[1])
            tp3 = entry_price * (1 + tp_percent * partial_tp[2])
            
            # Nếu đã tính range, kiểm tra và điều chỉnh
            if self.is_sideways_market and self.range_high and self.range_low:
                # Đảm bảo TP3 không vượt quá high của range
                if tp3 > self.range_high:
                    # Điều chỉnh TP xuống
                    tp3 = self.range_high
                    # Điều chỉnh TP1 và TP2 theo tỷ lệ
                    tp1 = entry_price + (tp3 - entry_price) * partial_tp[0] / partial_tp[2]
                    tp2 = entry_price + (tp3 - entry_price) * partial_tp[1] / partial_tp[2]
        else:  # SHORT
            sl_price = entry_price * (1 + sl_percent)
            tp1 = entry_price * (1 - tp_percent * partial_tp[0])
            tp2 = entry_price * (1 - tp_percent * partial_tp[1])
            tp3 = entry_price * (1 - tp_percent * partial_tp[2])
            
            # Nếu đã tính range, kiểm tra và điều chỉnh
            if self.is_sideways_market and self.range_high and self.range_low:
                # Đảm bảo TP3 không thấp hơn low của range
                if tp3 < self.range_low:
                    # Điều chỉnh TP lên
                    tp3 = self.range_low
                    # Điều chỉnh TP1 và TP2 theo tỷ lệ
                    tp1 = entry_price - (entry_price - tp3) * partial_tp[0] / partial_tp[2]
                    tp2 = entry_price - (entry_price - tp3) * partial_tp[1] / partial_tp[2]
        
        return {
            'entry': entry_price,
            'sl': sl_price,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'sl_percent': sl_percent * 100,  # Chuyển sang %
            'tp_percent': tp_percent * 100,  # Chuyển sang %
            'risk_reward': tp_sl_ratio
        }
    
    def optimize_entry_timing(self, data, signal, indicators, max_wait_candles=5):
        """
        Tối ưu hóa thời điểm vào lệnh để tăng tỷ lệ thắng
        
        Parameters:
        - data: DataFrame gốc
        - signal: 'LONG' hoặc 'SHORT'
        - indicators: DataFrame với các chỉ báo đã tính
        - max_wait_candles: Số nến tối đa chờ đợi
        
        Returns:
        - Dictionary với thông tin vào lệnh tối ưu
        """
        # Nếu không phải thị trường đi ngang hoặc không có tín hiệu, trả về None
        if not self.is_sideways_market or not signal:
            return None
        
        last_candle = indicators.iloc[-1]
        current_price = last_candle['close']
        
        # Khởi tạo thông tin vào lệnh
        entry_info = {
            'entry_type': 'immediate',  # immediate, limit, wait
            'entry_price': current_price,
            'reason': 'Default immediate entry',
            'wait_for': None,
            'limit_price': None
        }
        
        # Kiểm tra vị trí trong range
        if 'range_position' in last_candle:
            range_pos = last_candle['range_position']
            
            if signal == 'LONG':
                if range_pos > 40:
                    # Đang ở giữa hoặc gần cao hơn trong range, tốt hơn nên đợi pullback
                    entry_info['entry_type'] = 'limit'
                    entry_info['limit_price'] = min(current_price * 0.995, self.range_quarter_1)
                    entry_info['reason'] = f"Waiting for pullback before LONG (current range position: {range_pos:.1f}%)"
                elif range_pos < 20:
                    # Đã gần đáy range, vào lệnh ngay là tốt
                    entry_info['entry_type'] = 'immediate'
                    entry_info['reason'] = f"Immediate LONG near range bottom (range position: {range_pos:.1f}%)"
            else:  # SHORT
                if range_pos < 60:
                    # Đang ở giữa hoặc gần thấp hơn trong range, tốt hơn nên đợi pullback
                    entry_info['entry_type'] = 'limit'
                    entry_info['limit_price'] = max(current_price * 1.005, self.range_quarter_3)
                    entry_info['reason'] = f"Waiting for pullback before SHORT (current range position: {range_pos:.1f}%)"
                elif range_pos > 80:
                    # Đã gần đỉnh range, vào lệnh ngay là tốt
                    entry_info['entry_type'] = 'immediate'
                    entry_info['reason'] = f"Immediate SHORT near range top (range position: {range_pos:.1f}%)"
        
        # Kiểm tra vị trí so với BB
        bb_pos = last_candle['bb_pos']
        
        if signal == 'LONG':
            if bb_pos > 0.6:
                # Đang gần BB trên, khi muốn LONG tốt hơn nên đợi
                entry_info['entry_type'] = 'wait'
                entry_info['wait_for'] = 'bb_middle_touch'
                entry_info['reason'] = f"Wait for price to reach BB middle before LONG (BB position: {bb_pos:.2f})"
        else:  # SHORT
            if bb_pos < 0.4:
                # Đang gần BB dưới, khi muốn SHORT tốt hơn nên đợi
                entry_info['entry_type'] = 'wait'
                entry_info['wait_for'] = 'bb_middle_touch'
                entry_info['reason'] = f"Wait for price to reach BB middle before SHORT (BB position: {bb_pos:.2f})"
        
        # Kiểm tra BB Squeeze
        if last_candle['is_squeeze'] and entry_info['entry_type'] == 'immediate':
            # Trong BB Squeeze, tốt hơn nên đợi breakout
            entry_info['entry_type'] = 'wait'
            entry_info['wait_for'] = 'squeeze_breakout'
            entry_info['reason'] = f"BB Squeeze detected - wait for breakout before {signal}"
        
        # Kiểm tra khối lượng
        if 'volume' in last_candle and 'volume_ma' in last_candle:
            volume_ratio = last_candle['volume'] / last_candle['volume_ma']
            
            if volume_ratio < 0.7 and entry_info['entry_type'] == 'immediate':
                # Khối lượng thấp, tín hiệu kém tin cậy
                entry_info['entry_type'] = 'wait'
                entry_info['wait_for'] = 'volume_confirmation'
                entry_info['reason'] = f"Low volume detected (ratio: {volume_ratio:.2f}) - wait for confirmation"
        
        logger.info(f"Tối ưu vào lệnh: {entry_info['entry_type']} với lý do: {entry_info['reason']}")
        return entry_info
    
    def adaptive_sl_tp_management(self, position, current_price, indicator_data):
        """
        Quản lý SL/TP thích ứng cho thị trường đi ngang
        
        Parameters:
        - position: Dictionary chứa thông tin vị thế
        - current_price: Giá hiện tại
        - indicator_data: Dictionary chứa dữ liệu chỉ báo hiện tại
        
        Returns:
        - Dictionary với hành động được đề xuất
        """
        # Khởi tạo kết quả
        result = {
            'action': 'hold',  # hold, move_sl, close_partial, close_full
            'reason': 'No condition met',
            'new_sl': position.get('sl', None),
            'close_percentage': 0
        }
        
        # Chiến lược đặc biệt cho thị trường đi ngang:
        # 1. Chốt lời sớm và thường xuyên
        # 2. Trailing stop sau khi đạt một mức lợi nhuận nhất định
        # 3. Đặc biệt chú ý đến các mức hỗ trợ/kháng cự trong range
        
        position_type = position.get('type', 'LONG')
        entry_price = position.get('entry_price', current_price)
        sl_price = position.get('sl', None)
        
        # Tính toán % lợi nhuận hiện tại
        if position_type == 'LONG':
            current_profit_pct = (current_price - entry_price) / entry_price * 100
        else:  # SHORT
            current_profit_pct = (entry_price - current_price) / entry_price * 100
        
        # Các thiết lập
        config_signal = self.config['signal_confirmation']
        trail_after_profit = config_signal['trail_after_profit']
        trail_distance = config_signal['trail_distance']
        exit_after_bars = config_signal['exit_after_bars']
        
        # Kiểm tra trailing stop
        if config_signal['use_trailing_stop'] and current_profit_pct >= trail_after_profit:
            # Đã đạt ngưỡng kích hoạt trailing stop
            
            # Tính giá trị trailing stop mới
            if position_type == 'LONG':
                # Đối với LONG, trailing stop luôn tăng
                new_trail_sl = current_price * (1 - trail_distance / 100)
                # Chỉ di chuyển SL nếu giá mới cao hơn SL hiện tại
                if sl_price is None or new_trail_sl > sl_price:
                    result['action'] = 'move_sl'
                    result['new_sl'] = new_trail_sl
                    result['reason'] = f"Trailing stop updated: profit {current_profit_pct:.2f}% > threshold {trail_after_profit}%"
            else:  # SHORT
                # Đối với SHORT, trailing stop luôn giảm
                new_trail_sl = current_price * (1 + trail_distance / 100)
                # Chỉ di chuyển SL nếu giá mới thấp hơn SL hiện tại
                if sl_price is None or new_trail_sl < sl_price:
                    result['action'] = 'move_sl'
                    result['new_sl'] = new_trail_sl
                    result['reason'] = f"Trailing stop updated: profit {current_profit_pct:.2f}% > threshold {trail_after_profit}%"
        
        # Kiểm tra chốt lời từng phần dựa trên TP
        tp1 = position.get('tp1', None)
        tp2 = position.get('tp2', None)
        tp3 = position.get('tp3', None)
        
        # Lấy thông tin TP đã kích hoạt
        tp1_triggered = position.get('tp1_triggered', False)
        tp2_triggered = position.get('tp2_triggered', False)
        tp3_triggered = position.get('tp3_triggered', False)
        
        # Kiểm tra TP1
        if not tp1_triggered and tp1 is not None:
            if (position_type == 'LONG' and current_price >= tp1) or \
               (position_type == 'SHORT' and current_price <= tp1):
                result['action'] = 'close_partial'
                result['close_percentage'] = 0.3  # 30% của vị thế
                result['reason'] = f"TP1 triggered at {tp1:.2f}"
                return result
        
        # Kiểm tra TP2
        if not tp2_triggered and tp1_triggered and tp2 is not None:
            if (position_type == 'LONG' and current_price >= tp2) or \
               (position_type == 'SHORT' and current_price <= tp2):
                result['action'] = 'close_partial'
                result['close_percentage'] = 0.3  # 30% của vị thế
                result['reason'] = f"TP2 triggered at {tp2:.2f}"
                return result
        
        # Kiểm tra TP3
        if not tp3_triggered and tp2_triggered and tp3 is not None:
            if (position_type == 'LONG' and current_price >= tp3) or \
               (position_type == 'SHORT' and current_price <= tp3):
                result['action'] = 'close_partial'
                result['close_percentage'] = 0.4  # 40% còn lại của vị thế
                result['reason'] = f"TP3 triggered at {tp3:.2f}"
                return result
        
        # Kiểm tra đảo chiều trong range
        if self.is_sideways_market and 'range_position' in indicator_data:
            range_pos = indicator_data['range_position']
            
            # Chiến lược đóng khi đạt đỉnh/đáy range
            if position_type == 'LONG' and range_pos > 80:
                result['action'] = 'close_full'
                result['reason'] = f"Close LONG near range top (position: {range_pos:.1f}%)"
                return result
            elif position_type == 'SHORT' and range_pos < 20:
                result['action'] = 'close_full'
                result['reason'] = f"Close SHORT near range bottom (position: {range_pos:.1f}%)"
                return result
        
        # Kiểm tra đảo chiều theo chỉ báo
        if 'rsi' in indicator_data and 'stoch_k' in indicator_data:
            rsi = indicator_data['rsi']
            stoch_k = indicator_data['stoch_k']
            
            # Kiểm tra tín hiệu đảo chiều
            if position_type == 'LONG':
                if rsi > 70 and stoch_k > 80:
                    # Dấu hiệu quá mua trong thị trường đi ngang = tín hiệu mạnh để đóng
                    result['action'] = 'close_partial'
                    result['close_percentage'] = 0.5
                    result['reason'] = f"Overbought signals detected: RSI={rsi:.1f}, Stochastic=%K={stoch_k:.1f}"
                    return result
            else:  # SHORT
                if rsi < 30 and stoch_k < 20:
                    # Dấu hiệu quá bán trong thị trường đi ngang = tín hiệu mạnh để đóng
                    result['action'] = 'close_partial'
                    result['close_percentage'] = 0.5
                    result['reason'] = f"Oversold signals detected: RSI={rsi:.1f}, Stochastic=%K={stoch_k:.1f}"
                    return result
        
        # Kiểm tra thời gian trong lệnh
        bars_in_trade = position.get('bars_in_trade', 0)
        if bars_in_trade > exit_after_bars:
            # Đã quá số nến quy định mà chưa đạt TP
            if current_profit_pct > 0:
                # Đang lời, đóng hết
                result['action'] = 'close_full'
                result['reason'] = f"Trade duration exceeded {exit_after_bars} bars with profit {current_profit_pct:.2f}%"
                return result
            elif current_profit_pct > -0.5:
                # Tương đối hòa vốn, đóng hết
                result['action'] = 'close_full'
                result['reason'] = f"Trade duration exceeded {exit_after_bars} bars with small loss {current_profit_pct:.2f}%"
                return result
        
        return result
    
    def calculate_position_size(self, account_balance, entry_price, sl_price, risk_percentage=None):
        """
        Tính toán kích thước vị thế dựa trên quản lý rủi ro
        
        Parameters:
        - account_balance: Số dư tài khoản
        - entry_price: Giá vào lệnh
        - sl_price: Giá dừng lỗ
        - risk_percentage: % rủi ro, nếu None sẽ sử dụng mặc định
        
        Returns:
        - Kích thước vị thế
        """
        if risk_percentage is None:
            risk_percentage = self.config['position_sizing']['default_risk']
        
        # Chuyển % thành tỷ lệ
        risk_ratio = risk_percentage / 100
        
        # Tính số tiền rủi ro
        risk_amount = account_balance * risk_ratio
        
        # Tính khoảng cách từ entry đến SL
        if entry_price > sl_price:  # LONG
            sl_distance_percent = (entry_price - sl_price) / entry_price
        else:  # SHORT
            sl_distance_percent = (sl_price - entry_price) / entry_price
        
        # Đảm bảo sl_distance_percent không quá nhỏ
        sl_distance_percent = max(sl_distance_percent, 0.005)  # Tối thiểu 0.5%
        
        # Tính kích thước vị thế
        position_size = risk_amount / (entry_price * sl_distance_percent)
        
        logger.info(f"Tính position size: balance=${account_balance:.2f}, risk={risk_percentage:.2f}%, "
                   f"entry={entry_price:.2f}, SL={sl_price:.2f}, size={position_size:.6f}")
        
        return position_size
    
    def evaluate_strategy_performance(self, trades_history):
        """
        Đánh giá hiệu suất của chiến lược trong thị trường đi ngang
        
        Parameters:
        - trades_history: List các dictionary chứa thông tin lệnh
        
        Returns:
        - Dictionary với các chỉ số hiệu suất
        """
        if not trades_history:
            return {"error": "No trades to evaluate"}
        
        # Lọc các lệnh trong thị trường đi ngang
        sideways_trades = [trade for trade in trades_history if trade.get('market_type') == 'sideways']
        
        if not sideways_trades:
            return {"error": "No sideways market trades to evaluate"}
        
        # Tính các chỉ số
        total_trades = len(sideways_trades)
        winning_trades = len([t for t in sideways_trades if t.get('pnl', 0) > 0])
        losing_trades = len([t for t in sideways_trades if t.get('pnl', 0) < 0])
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        # Tính tổng lợi nhuận và lỗ
        total_profit = sum([t.get('pnl', 0) for t in sideways_trades if t.get('pnl', 0) > 0])
        total_loss = sum([abs(t.get('pnl', 0)) for t in sideways_trades if t.get('pnl', 0) < 0])
        
        # Tính profit factor
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Tính expectancy
        expectancy = (win_rate/100 * (total_profit/winning_trades if winning_trades > 0 else 0) - 
                     (1-win_rate/100) * (total_loss/losing_trades if losing_trades > 0 else 0))
        
        # Phân tích theo loại tín hiệu
        signal_performance = {}
        for trade in sideways_trades:
            signals = trade.get('signals', [])
            for signal in signals:
                if signal not in signal_performance:
                    signal_performance[signal] = {'count': 0, 'wins': 0, 'total_pnl': 0}
                
                signal_performance[signal]['count'] += 1
                if trade.get('pnl', 0) > 0:
                    signal_performance[signal]['wins'] += 1
                signal_performance[signal]['total_pnl'] += trade.get('pnl', 0)
        
        # Tính tỷ lệ thắng cho từng loại tín hiệu
        for signal, stats in signal_performance.items():
            if stats['count'] > 0:
                stats['win_rate'] = stats['wins'] / stats['count'] * 100
                stats['avg_pnl'] = stats['total_pnl'] / stats['count']
        
        # Sắp xếp các tín hiệu theo hiệu suất
        top_signals = sorted(signal_performance.items(), 
                            key=lambda x: x[1]['win_rate'], 
                            reverse=True)
        
        # Kết quả
        performance = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'top_signals': top_signals[:5] if len(top_signals) >= 5 else top_signals,
            'worst_signals': top_signals[-5:] if len(top_signals) >= 5 else []
        }
        
        return performance
    
    def save_state(self, file_path='sideways_strategy_state.json'):
        """Lưu trạng thái chiến lược hiện tại"""
        state = {
            'config': self.config,
            'is_sideways_market': self.is_sideways_market,
            'range_high': self.range_high,
            'range_low': self.range_low,
            'range_mid': self.range_mid,
            'last_signals': self.last_signals,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(file_path, 'w') as f:
            json.dump(state, f, indent=4, default=str)
        
        logger.info(f"Đã lưu trạng thái chiến lược vào {file_path}")
    
    def load_state(self, file_path='sideways_strategy_state.json'):
        """Tải trạng thái chiến lược từ file"""
        if not os.path.exists(file_path):
            logger.warning(f"Không tìm thấy file {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            self.config = state.get('config', self.config)
            self.is_sideways_market = state.get('is_sideways_market', False)
            self.range_high = state.get('range_high', None)
            self.range_low = state.get('range_low', None)
            self.range_mid = state.get('range_mid', None)
            self.last_signals = state.get('last_signals', [])
            
            logger.info(f"Đã tải trạng thái chiến lược từ {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tải trạng thái: {str(e)}")
            return False

# Hàm test
def test_sideways_strategy():
    """Hàm kiểm tra chức năng của SidewaysMarketStrategy"""
    # Tạo dữ liệu giả để test
    date_range = pd.date_range(start='2025-01-01', periods=100, freq='1h')
    
    # Tạo DataFrame
    np.random.seed(42)  # Để tái tạo kết quả
    close_prices = 50000 + np.cumsum(np.random.normal(0, 100, len(date_range)))
    
    # Tạo biến động trong range
    for i in range(20, 80):
        if close_prices[i] > 51000:
            close_prices[i] = 51000 - np.random.normal(0, 50)
        elif close_prices[i] < 49000:
            close_prices[i] = 49000 + np.random.normal(0, 50)
    
    data = pd.DataFrame({
        'timestamp': date_range,
        'open': close_prices + np.random.normal(0, 30, len(date_range)),
        'high': close_prices + np.random.normal(50, 30, len(date_range)),
        'low': close_prices + np.random.normal(-50, 30, len(date_range)),
        'close': close_prices,
        'volume': np.random.randint(100, 1000, len(date_range))
    })
    
    # Đảm bảo high > open, close và low < open, close
    for i in range(len(data)):
        data.loc[i, 'high'] = max(data.loc[i, 'high'], data.loc[i, 'open'], data.loc[i, 'close'])
        data.loc[i, 'low'] = min(data.loc[i, 'low'], data.loc[i, 'open'], data.loc[i, 'close'])
    
    # Khởi tạo chiến lược
    strategy = SidewaysMarketStrategy()
    
    print("\n=== TEST SIDEWAYS MARKET STRATEGY ===")
    
    # 1. Kiểm tra phát hiện thị trường đi ngang
    is_sideways = strategy.detect_sideways_market(data)
    print(f"Thị trường đi ngang: {is_sideways}")
    print(f"Range: High={strategy.range_high:.2f}, Low={strategy.range_low:.2f}, Mid={strategy.range_mid:.2f}")
    
    # 2. Tính toán các chỉ báo
    indicators = strategy.calculate_indicators(data)
    print(f"Đã tính {len(indicators.columns)} chỉ báo")
    
    # 3. Tạo tín hiệu
    signal, signal_data = strategy.generate_sideways_signals(data, indicators)
    print(f"Tín hiệu được tạo: {signal}")
    print(f"Chi tiết tín hiệu: {signal_data.get('description', 'N/A')}")
    
    # 4. Tính toán entry/exit levels
    if signal:
        entry_price = data.iloc[-1]['close']
        atr_value = indicators.iloc[-1]['atr']
        levels = strategy.calculate_entry_exit_levels(entry_price, signal, atr_value)
        
        print(f"\nMức vào/ra lệnh:")
        print(f"Entry: {levels['entry']:.2f}")
        print(f"SL: {levels['sl']:.2f} ({levels['sl_percent']:.2f}%)")
        print(f"TP1: {levels['tp1']:.2f}")
        print(f"TP2: {levels['tp2']:.2f}")
        print(f"TP3: {levels['tp3']:.2f}")
        print(f"Risk/Reward: {levels['risk_reward']:.2f}")
        
        # 5. Tối ưu thời điểm vào lệnh
        entry_info = strategy.optimize_entry_timing(data, signal, indicators)
        print(f"\nTối ưu vào lệnh:")
        print(f"Loại: {entry_info['entry_type']}")
        print(f"Lý do: {entry_info['reason']}")
        if entry_info['entry_type'] == 'limit':
            print(f"Limit giá: {entry_info['limit_price']:.2f}")
        
        # 6. Mô phỏng quản lý SL/TP
        position = {
            'type': signal,
            'entry_price': entry_price,
            'sl': levels['sl'],
            'tp1': levels['tp1'],
            'tp2': levels['tp2'],
            'tp3': levels['tp3'],
            'bars_in_trade': 5
        }
        
        # Giả định giá hiện tại là giữa entry và TP1
        if signal == 'LONG':
            current_price = entry_price + (levels['tp1'] - entry_price) * 0.5
        else:
            current_price = entry_price - (entry_price - levels['tp1']) * 0.5
        
        indicator_data = {
            'rsi': indicators.iloc[-1]['rsi'],
            'stoch_k': indicators.iloc[-1]['stoch_k'],
            'stoch_d': indicators.iloc[-1]['stoch_d'],
            'range_position': indicators.iloc[-1].get('range_position', 50)
        }
        
        action = strategy.adaptive_sl_tp_management(position, current_price, indicator_data)
        
        print(f"\nQuản lý SL/TP:")
        print(f"Hành động: {action['action']}")
        print(f"Lý do: {action['reason']}")
        if action['action'] == 'move_sl':
            print(f"SL mới: {action['new_sl']:.2f}")
        elif action['action'] in ['close_partial', 'close_full']:
            print(f"Đóng: {action['close_percentage']*100:.0f}% vị thế")
    
    print("\n=== HOÀN THÀNH KIỂM TRA ===")

if __name__ == "__main__":
    test_sideways_strategy()