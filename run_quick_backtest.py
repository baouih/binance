import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Sử dụng Agg backend
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quick_backtest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('quick_backtest')

class BinanceDataLoader:
    """
    Lớp giả định để tải dữ liệu từ Binance cho mục đích này
    """
    def load_historical_data(self, symbol, interval, start_date=None, end_date=None):
        """
        Tải dữ liệu từ file CSV cho mục đích kiểm thử nhanh
        """
        # Tìm kiếm file dữ liệu có sẵn
        data_dir = Path('./data')
        if not data_dir.exists():
            os.makedirs(data_dir)
        
        # Mẫu tên file: BTCUSDT_1h_2023-01-01_2023-03-31.csv
        # Tìm kiếm file phù hợp nhất
        symbol_files = list(data_dir.glob(f"{symbol}_{interval}_*.csv"))
        
        if not symbol_files:
            logger.warning(f"Không tìm thấy file dữ liệu cho {symbol} {interval}")
            print(f"Không có dữ liệu sẵn cho {symbol} {interval}. Vui lòng sử dụng 'BTCUSDT' và '1h'")
            
            # Tạo dữ liệu mẫu để test
            return self._generate_sample_data(symbol)
        
        # Lấy file mới nhất
        latest_file = max(symbol_files, key=lambda x: os.path.getctime(x))
        
        logger.info(f"Đang tải dữ liệu từ file: {latest_file}")
        
        try:
            # Đọc dữ liệu
            df = pd.read_csv(latest_file)
            
            # Chuyển timestamp thành datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            # Đổi tên cột cho phù hợp với yêu cầu
            if 'open' in df.columns and 'Open' not in df.columns:
                df = df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu: {str(e)}")
            return self._generate_sample_data(symbol)
    
    def _generate_sample_data(self, symbol, periods=500):
        """
        Tạo dữ liệu mẫu cho mục đích kiểm thử
        """
        logger.info(f"Tạo dữ liệu mẫu cho {symbol}")
        
        # Tạo timestamp
        end_date = datetime.now()
        start_date = end_date - timedelta(days=periods // 24)
        dates = pd.date_range(start=start_date, end=end_date, periods=periods)
        
        # Tạo giá theo random walk
        price = 50000 if 'BTC' in symbol else 2000  # Giá ban đầu
        
        np.random.seed(42)  # Để kết quả có thể tái tạo
        
        # Tạo giá với xu hướng nhất định
        returns = np.random.normal(0.0005, 0.005, periods)  # Trung bình tăng nhẹ
        
        # Tạo biến động cao hơn trong khoảng giữa
        mid_start = periods // 3
        mid_end = 2 * periods // 3
        returns[mid_start:mid_end] = np.random.normal(-0.001, 0.01, mid_end - mid_start)
        
        # Tạo xu hướng tăng ở cuối
        returns[mid_end:] = np.random.normal(0.001, 0.004, periods - mid_end)
        
        prices = [price]
        for r in returns:
            price *= (1 + r)
            prices.append(price)
        
        prices = prices[:-1]  # Bỏ phần tử cuối thừa
        
        # Tạo dữ liệu OHLCV
        df = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.001, periods)),
            'close': prices,
            'high': prices * (1 + np.random.uniform(0.001, 0.003, periods)),
            'low': prices * (1 - np.random.uniform(0.001, 0.003, periods)),
            'volume': np.random.uniform(100, 1000, periods) * (1 + np.abs(returns) * 10)
        }, index=dates)
        
        # Đổi tên cột thành chữ hoa
        df.columns = ['Open', 'Close', 'High', 'Low', 'Volume']
        
        # Đảm bảo High > Open, Close và Low < Open, Close
        for i in range(len(df)):
            df.loc[df.index[i], 'High'] = max(df.iloc[i]['High'], df.iloc[i]['Open'], df.iloc[i]['Close'])
            df.loc[df.index[i], 'Low'] = min(df.iloc[i]['Low'], df.iloc[i]['Open'], df.iloc[i]['Close'])
        
        return df

class MultiRiskStrategy:
    """
    Chiến lược giao dịch đa mức rủi ro với khả năng thích ứng theo điều kiện thị trường
    """
    
    def __init__(self, risk_level=0.15, lookback_period=14):
        """
        Khởi tạo chiến lược giao dịch
        
        Args:
            risk_level (float): Mức rủi ro (0.1-0.25)
            lookback_period (int): Số nến quá khứ để xem xét
        """
        self.risk_level = risk_level
        self.lookback_period = lookback_period
        logger.info(f"Khởi tạo MultiRiskStrategy với risk_level={risk_level}, lookback_period={lookback_period}")
    
    def calculate_indicators(self, data):
        """
        Tính toán các chỉ báo kỹ thuật
        
        Args:
            data (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã tính
        """
        # Kiểm tra dữ liệu đầu vào
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            # Thử chuyển đổi từ chữ thường sang chữ hoa
            lowercase_cols = ['open', 'high', 'low', 'close', 'volume']
            if all(col in data.columns for col in lowercase_cols):
                data = data.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
            else:
                logger.error(f"Thiếu các cột dữ liệu cần thiết. Yêu cầu: {required_columns}, Hiện có: {data.columns.tolist()}")
                return None
        
        # Copy dữ liệu để tránh ảnh hưởng đến dữ liệu gốc
        df = data.copy()
        
        # 1. Tính RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.lookback_period).mean()
        avg_loss = loss.rolling(window=self.lookback_period).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 2. Tính MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 3. Tính Bollinger Bands
        df['sma20'] = df['Close'].rolling(window=20).mean()
        df['std20'] = df['Close'].rolling(window=20).std()
        df['upper_band'] = df['sma20'] + (df['std20'] * 2)
        df['lower_band'] = df['sma20'] - (df['std20'] * 2)
        
        # 4. Tính ATR (Average True Range)
        tr1 = df['High'] - df['Low']
        tr2 = abs(df['High'] - df['Close'].shift())
        tr3 = abs(df['Low'] - df['Close'].shift())
        df['tr'] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # 5. Tính Stochastic Oscillator
        df['lowest_14'] = df['Low'].rolling(window=14).min()
        df['highest_14'] = df['High'].rolling(window=14).max()
        df['%K'] = (df['Close'] - df['lowest_14']) / (df['highest_14'] - df['lowest_14']) * 100
        df['%D'] = df['%K'].rolling(window=3).mean()
        
        # 6. Detect Market Condition
        df['market_condition'] = self._detect_market_condition(df)
        
        # Loại bỏ dữ liệu NaN
        return df.dropna()
    
    def _detect_market_condition(self, df):
        """
        Phát hiện điều kiện thị trường dựa trên dữ liệu giá
        
        Args:
            df (pd.DataFrame): DataFrame đã có các chỉ báo
            
        Returns:
            pd.Series: Series chứa điều kiện thị trường cho mỗi điểm dữ liệu
        """
        # Tạo mảng để lưu kết quả
        conditions = np.full(len(df), 'NEUTRAL', dtype=object)
        
        # Số nến để xác định xu hướng
        trend_period = min(50, len(df) // 2)
        
        # Tính phần trăm thay đổi giá trong giai đoạn xu hướng
        for i in range(trend_period, len(df)):
            # Tính % thay đổi từ đầu kỳ
            price_change = (df['Close'].iloc[i] - df['Close'].iloc[i - trend_period]) / df['Close'].iloc[i - trend_period] * 100
            
            # Biến động (dựa trên ATR so với giá)
            if 'atr' in df.columns and not pd.isna(df['atr'].iloc[i]):
                volatility = df['atr'].iloc[i] / df['Close'].iloc[i] * 100
            else:
                volatility = 0
            
            # Xác định điều kiện thị trường
            if price_change > 5:  # Tăng > 5%
                if volatility > 3:
                    conditions[i] = 'VOLATILE'
                else:
                    conditions[i] = 'BULL'
            elif price_change < -5:  # Giảm > 5%
                if volatility > 3:
                    conditions[i] = 'VOLATILE'
                else:
                    conditions[i] = 'BEAR'
            else:  # Đi ngang
                if volatility > 2:
                    conditions[i] = 'VOLATILE'
                else:
                    conditions[i] = 'SIDEWAYS'
        
        return pd.Series(conditions, index=df.index)
    
    def generate_signals(self, data):
        """
        Tạo tín hiệu giao dịch
        
        Args:
            data (pd.DataFrame): DataFrame đã có các chỉ báo
            
        Returns:
            dict: Dictionary chứa các tín hiệu giao dịch
        """
        signals = {}
        
        # Điều chỉnh tín hiệu dựa trên mức rủi ro
        for i in range(1, len(data)):
            # Xác định điều kiện thị trường
            market_condition = data['market_condition'].iloc[i]
            
            # Tín hiệu RSI
            rsi = data['rsi'].iloc[i]
            prev_rsi = data['rsi'].iloc[i-1]
            
            # Tín hiệu MACD
            macd = data['macd'].iloc[i]
            macd_signal = data['macd_signal'].iloc[i]
            prev_macd = data['macd'].iloc[i-1]
            prev_macd_signal = data['macd_signal'].iloc[i-1]
            
            # Tín hiệu Bollinger Bands
            close = data['Close'].iloc[i]
            upper_band = data['upper_band'].iloc[i]
            lower_band = data['lower_band'].iloc[i]
            
            # Tính SL và TP dựa trên ATR và mức rủi ro
            atr = data['atr'].iloc[i]
            
            # Điều chỉnh hệ số ATR dựa trên mức rủi ro
            sl_factor = 1.5  # Mặc định
            tp_factor = 2.0  # Mặc định
            
            if self.risk_level <= 0.10:  # Rủi ro thấp
                sl_factor = 2.0  # Stop loss xa hơn
                tp_factor = 1.5  # Take profit gần hơn
            elif self.risk_level <= 0.15:  # Rủi ro trung bình
                sl_factor = 1.5
                tp_factor = 2.0
            elif self.risk_level <= 0.20:  # Rủi ro cao
                sl_factor = 1.0  # Stop loss gần hơn
                tp_factor = 2.5  # Take profit xa hơn
            else:  # Rủi ro rất cao (> 0.20)
                sl_factor = 0.8
                tp_factor = 3.0
            
            # Tín hiệu mua (LONG)
            long_signal = False
            long_reason = []
            
            # RSI vượt lên từ vùng quá bán
            if prev_rsi < 30 and rsi >= 30:
                long_signal = True
                long_reason.append(f"RSI vượt lên từ vùng quá bán ({rsi:.2f})")
            
            # MACD cắt lên đường tín hiệu
            if prev_macd < prev_macd_signal and macd >= macd_signal and macd < 0:
                long_signal = True
                long_reason.append(f"MACD cắt lên đường tín hiệu (histogram: {macd - macd_signal:.6f})")
            
            # Giá chạm Bollinger Bands dưới
            if close <= lower_band:
                long_signal = True
                long_reason.append(f"Giá chạm Bollinger Band dưới ({close:.2f} <= {lower_band:.2f})")
            
            # Chỉ tạo tín hiệu nếu có điều kiện thoả mãn
            if long_signal:
                # Tính SL và TP
                stop_loss = close - (atr * sl_factor)
                take_profit = close + (atr * tp_factor)
                
                signals[i] = {
                    'index': i,
                    'timestamp': data.index[i],
                    'price': close,
                    'type': 'LONG',
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': long_reason,
                    'market_condition': market_condition
                }
            
            # Tín hiệu bán (SHORT)
            short_signal = False
            short_reason = []
            
            # RSI vượt xuống từ vùng quá mua
            if prev_rsi > 70 and rsi <= 70:
                short_signal = True
                short_reason.append(f"RSI vượt xuống từ vùng quá mua ({rsi:.2f})")
            
            # MACD cắt xuống đường tín hiệu
            if prev_macd > prev_macd_signal and macd <= macd_signal and macd > 0:
                short_signal = True
                short_reason.append(f"MACD cắt xuống đường tín hiệu (histogram: {macd - macd_signal:.6f})")
            
            # Giá chạm Bollinger Bands trên
            if close >= upper_band:
                short_signal = True
                short_reason.append(f"Giá chạm Bollinger Band trên ({close:.2f} >= {upper_band:.2f})")
            
            # Chỉ tạo tín hiệu nếu có điều kiện thoả mãn
            if short_signal:
                # Tính SL và TP
                stop_loss = close + (atr * sl_factor)
                take_profit = close - (atr * tp_factor)
                
                signals[i] = {
                    'index': i,
                    'timestamp': data.index[i],
                    'price': close,
                    'type': 'SHORT',
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': short_reason,
                    'market_condition': market_condition
                }
        
        logger.info(f"Đã tạo {len(signals)} tín hiệu giao dịch")
        return signals

class SidewaysMarketStrategy:
    """
    Chiến lược tối ưu cho thị trường đi ngang
    """
    
    def __init__(self, data, risk_level=0.15, window_size=20):
        """
        Khởi tạo chiến lược tối ưu cho thị trường đi ngang
        
        Args:
            data (pd.DataFrame): Dữ liệu giá
            risk_level (float): Mức độ rủi ro (0.1-0.25)
            window_size (int): Cửa sổ dữ liệu để phát hiện thị trường đi ngang
        """
        self.data = data
        self.risk_level = risk_level
        self.window_size = window_size
        logger.info(f"Khởi tạo SidewaysMarketStrategy với risk_level={risk_level}, window_size={window_size}")
    
    def is_sideways(self, price_data, threshold=0.05):
        """
        Kiểm tra xem dữ liệu giá có đang trong thị trường đi ngang hay không
        
        Args:
            price_data (pd.Series): Dữ liệu giá đóng cửa
            threshold (float): Ngưỡng % thay đổi tối đa để coi là thị trường đi ngang
            
        Returns:
            bool: True nếu là thị trường đi ngang, False nếu không
        """
        highest = price_data.max()
        lowest = price_data.min()
        
        # Tính % chênh lệch giữa giá cao nhất và thấp nhất
        range_pct = (highest - lowest) / lowest
        
        return range_pct < threshold
    
    def generate_signals(self):
        """
        Tạo tín hiệu giao dịch cho thị trường đi ngang
        
        Returns:
            dict: Dictionary chứa các tín hiệu giao dịch
        """
        if 'Close' not in self.data.columns and 'close' in self.data.columns:
            self.data = self.data.rename(columns={'close': 'Close'})
        
        if 'Close' not in self.data.columns:
            logger.error("Không tìm thấy cột 'Close' trong dữ liệu")
            return {}
        
        signals = {}
        
        # Tính bollinger bands cho thị trường đi ngang
        self.data['sma20'] = self.data['Close'].rolling(window=20).mean()
        self.data['std20'] = self.data['Close'].rolling(window=20).std()
        self.data['upper_band'] = self.data['sma20'] + (self.data['std20'] * 1.5)  # Hẹp hơn cho thị trường đi ngang
        self.data['lower_band'] = self.data['sma20'] - (self.data['std20'] * 1.5)
        
        # Tính chỉ báo RSI
        delta = self.data['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        self.data['rsi'] = 100 - (100 / (1 + rs))
        
        # Tính ATR
        if 'High' in self.data.columns and 'Low' in self.data.columns:
            tr1 = self.data['High'] - self.data['Low']
            tr2 = abs(self.data['High'] - self.data['Close'].shift())
            tr3 = abs(self.data['Low'] - self.data['Close'].shift())
            self.data['tr'] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
            self.data['atr'] = self.data['tr'].rolling(window=14).mean()
        
        # Loại bỏ dữ liệu NaN
        data = self.data.dropna()
        
        for i in range(self.window_size, len(data)):
            # Xem xét cửa sổ dữ liệu
            window = data['Close'].iloc[i-self.window_size:i]
            
            # Kiểm tra xem có phải thị trường đi ngang không
            if self.is_sideways(window):
                current_price = data['Close'].iloc[i]
                rsi = data['rsi'].iloc[i]
                upper_band = data['upper_band'].iloc[i]
                lower_band = data['lower_band'].iloc[i]
                
                # Tính ATR nếu có
                atr = data['atr'].iloc[i] if 'atr' in data.columns else current_price * 0.01
                
                # Điều chỉnh SL/TP dựa trên mức rủi ro
                if self.risk_level <= 0.10:
                    sl_factor = 1.0
                    tp_factor = 1.2
                elif self.risk_level <= 0.15:
                    sl_factor = 0.8
                    tp_factor = 1.5
                elif self.risk_level <= 0.20:
                    sl_factor = 0.7
                    tp_factor = 1.8
                else:
                    sl_factor = 0.5
                    tp_factor = 2.0
                
                # Tín hiệu LONG khi giá chạm lower band và RSI < 40
                if current_price <= lower_band and rsi < 40:
                    stop_loss = current_price - (atr * sl_factor)
                    take_profit = current_price + (atr * tp_factor)
                    
                    signals[i] = {
                        'index': i,
                        'timestamp': data.index[i],
                        'price': current_price,
                        'type': 'LONG',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'reason': ["Giá chạm Bollinger Band dưới trong thị trường đi ngang",
                                  f"RSI thấp ({rsi:.2f})"],
                        'market_condition': 'SIDEWAYS'
                    }
                
                # Tín hiệu SHORT khi giá chạm upper band và RSI > 60
                elif current_price >= upper_band and rsi > 60:
                    stop_loss = current_price + (atr * sl_factor)
                    take_profit = current_price - (atr * tp_factor)
                    
                    signals[i] = {
                        'index': i,
                        'timestamp': data.index[i],
                        'price': current_price,
                        'type': 'SHORT',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'reason': ["Giá chạm Bollinger Band trên trong thị trường đi ngang",
                                  f"RSI cao ({rsi:.2f})"],
                        'market_condition': 'SIDEWAYS'
                    }
        
        logger.info(f"Đã tạo {len(signals)} tín hiệu giao dịch cho thị trường đi ngang")
        return signals

class BacktestRunner:
    """
    Lớp thực hiện backtest các chiến lược khác nhau
    """
    
    def __init__(self, symbol='BTCUSDT', interval='1h', start_date=None, end_date=None):
        self.symbol = symbol
        self.interval = interval
        self.start_date = start_date
        self.end_date = end_date
        
        # Thư mục kết quả
        self.results_dir = Path('./quick_test_results')
        if not self.results_dir.exists():
            os.makedirs(self.results_dir)
        
        # Tải dữ liệu
        data_loader = BinanceDataLoader()
        self.data = data_loader.load_historical_data(symbol, interval, start_date, end_date)
        
        if self.data is None or len(self.data) < 100:
            logger.error(f"Không thể tải đủ dữ liệu cho {symbol} {interval}")
            raise ValueError(f"Không thể tải đủ dữ liệu cho {symbol} {interval}")
        
        logger.info(f"Đã tải {len(self.data)} nến cho {symbol} {interval}")
    
    def run_backtest(self, strategy, risk_level=0.15, initial_balance=10000):
        """
        Chạy backtest một chiến lược cụ thể
        
        Args:
            strategy (str): Loại chiến lược ('multi_risk', 'sideways', 'combined')
            risk_level (float): Mức rủi ro (0.1-0.25)
            initial_balance (float): Số dư ban đầu
            
        Returns:
            dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest chiến lược {strategy} với risk_level={risk_level}")
        
        # Tạo chiến lược và tín hiệu
        signals = {}
        
        if strategy == 'multi_risk':
            multi_strategy = MultiRiskStrategy(risk_level=risk_level)
            data_with_indicators = multi_strategy.calculate_indicators(self.data)
            signals = multi_strategy.generate_signals(data_with_indicators)
        
        elif strategy == 'sideways':
            sideways_strategy = SidewaysMarketStrategy(self.data, risk_level=risk_level)
            signals = sideways_strategy.generate_signals()
        
        elif strategy == 'combined':
            # Kết hợp tín hiệu từ cả hai chiến lược
            multi_strategy = MultiRiskStrategy(risk_level=risk_level)
            data_with_indicators = multi_strategy.calculate_indicators(self.data)
            multi_signals = multi_strategy.generate_signals(data_with_indicators)
            
            sideways_strategy = SidewaysMarketStrategy(self.data, risk_level=risk_level)
            sideways_signals = sideways_strategy.generate_signals()
            
            # Kết hợp tín hiệu, ưu tiên tín hiệu thị trường đi ngang
            signals = sideways_signals.copy()
            for i, signal in multi_signals.items():
                if i not in signals:
                    signals[i] = signal
        
        else:
            logger.error(f"Không hỗ trợ chiến lược: {strategy}")
            return None
        
        if not signals:
            logger.warning(f"Không có tín hiệu giao dịch cho chiến lược {strategy}")
            return None
        
        # Thực hiện backtest
        balance = initial_balance
        position = None
        trades = []
        equity_curve = [balance]
        
        for i in range(1, len(self.data)):
            current_price = self.data['Close'].iloc[i]
            
            # Xử lý vị thế đang mở
            if position is not None:
                # Kiểm tra điều kiện chốt lời
                if (position['type'] == 'LONG' and current_price >= position['take_profit']) or \
                   (position['type'] == 'SHORT' and current_price <= position['take_profit']):
                    # Tính lợi nhuận
                    if position['type'] == 'LONG':
                        profit = position['qty'] * (current_price - position['entry_price'])
                    else:
                        profit = position['qty'] * (position['entry_price'] - current_price)
                    
                    # Cập nhật số dư
                    balance += profit
                    
                    # Lưu thông tin giao dịch
                    trade = {
                        'entry_time': position['time'],
                        'exit_time': self.data.index[i],
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'qty': position['qty'],
                        'profit': profit,
                        'profit_pct': (profit / (position['entry_price'] * position['qty'])) * 100,
                        'exit_reason': 'take_profit',
                        'market_condition': position['market_condition'],
                        'strategy': position['strategy']
                    }
                    trades.append(trade)
                    
                    # Đóng vị thế
                    position = None
                
                # Kiểm tra điều kiện cắt lỗ
                elif (position['type'] == 'LONG' and current_price <= position['stop_loss']) or \
                     (position['type'] == 'SHORT' and current_price >= position['stop_loss']):
                    # Tính lỗ
                    if position['type'] == 'LONG':
                        loss = position['qty'] * (current_price - position['entry_price'])
                    else:
                        loss = position['qty'] * (position['entry_price'] - current_price)
                    
                    # Cập nhật số dư
                    balance += loss
                    
                    # Lưu thông tin giao dịch
                    trade = {
                        'entry_time': position['time'],
                        'exit_time': self.data.index[i],
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'qty': position['qty'],
                        'profit': loss,
                        'profit_pct': (loss / (position['entry_price'] * position['qty'])) * 100,
                        'exit_reason': 'stop_loss',
                        'market_condition': position['market_condition'],
                        'strategy': position['strategy']
                    }
                    trades.append(trade)
                    
                    # Đóng vị thế
                    position = None
            
            # Mở vị thế mới nếu có tín hiệu và không có vị thế đang mở
            if i in signals and position is None:
                signal = signals[i]
                
                # Tính kích thước vị thế dựa trên mức rủi ro
                risk_amount = balance * risk_level
                
                if signal['type'] == 'LONG':
                    sl_distance = signal['price'] - signal['stop_loss']
                else:
                    sl_distance = signal['stop_loss'] - signal['price']
                
                # Đảm bảo sl_distance > 0
                sl_distance = max(sl_distance, signal['price'] * 0.001)
                qty = risk_amount / sl_distance / signal['price']
                
                # Mở vị thế
                position = {
                    'time': signal['timestamp'],
                    'type': signal['type'],
                    'entry_price': signal['price'],
                    'qty': qty,
                    'stop_loss': signal['stop_loss'],
                    'take_profit': signal['take_profit'],
                    'market_condition': signal.get('market_condition', 'UNKNOWN'),
                    'strategy': strategy
                }
            
            # Cập nhật equity curve
            equity_curve.append(balance)
        
        # Đóng vị thế cuối cùng nếu còn
        if position is not None:
            # Đóng ở giá cuối cùng
            final_price = self.data['Close'].iloc[-1]
            
            # Tính lãi/lỗ
            if position['type'] == 'LONG':
                profit = position['qty'] * (final_price - position['entry_price'])
            else:
                profit = position['qty'] * (position['entry_price'] - final_price)
            
            # Cập nhật số dư
            balance += profit
            
            # Lưu thông tin giao dịch
            trade = {
                'entry_time': position['time'],
                'exit_time': self.data.index[-1],
                'type': position['type'],
                'entry_price': position['entry_price'],
                'exit_price': final_price,
                'qty': position['qty'],
                'profit': profit,
                'profit_pct': (profit / (position['entry_price'] * position['qty'])) * 100,
                'exit_reason': 'end_of_data',
                'market_condition': position['market_condition'],
                'strategy': position['strategy']
            }
            trades.append(trade)
            
            # Cập nhật equity curve
            equity_curve[-1] = balance
        
        # Tính các chỉ số hiệu suất
        profit_loss = balance - initial_balance
        profit_loss_pct = (profit_loss / initial_balance) * 100
        
        # Tính drawdown
        peak = initial_balance
        drawdowns = []
        max_drawdown = 0
        max_drawdown_pct = 0
        
        for bal in equity_curve:
            if bal > peak:
                peak = bal
            drawdown = peak - bal
            drawdown_pct = (drawdown / peak) * 100
            drawdowns.append(drawdown_pct)
            
            if drawdown_pct > max_drawdown_pct:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        # Tính win rate
        winning_trades = [t for t in trades if t['profit'] > 0]
        losing_trades = [t for t in trades if t['profit'] <= 0]
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        
        # Tính profit factor
        total_profit = sum([t['profit'] for t in winning_trades]) if winning_trades else 0
        total_loss = sum([abs(t['profit']) for t in losing_trades]) if losing_trades else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Phân tích theo điều kiện thị trường
        trades_by_market = {}
        for trade in trades:
            condition = trade['market_condition']
            if condition not in trades_by_market:
                trades_by_market[condition] = []
            trades_by_market[condition].append(trade)
        
        market_condition_performance = {}
        for condition, condition_trades in trades_by_market.items():
            winning = len([t for t in condition_trades if t['profit'] > 0])
            win_rate_by_market = winning / len(condition_trades) * 100 if condition_trades else 0
            avg_profit = sum([t['profit'] for t in condition_trades]) / len(condition_trades) if condition_trades else 0
            
            market_condition_performance[condition] = {
                'trades': len(condition_trades),
                'win_rate': win_rate_by_market,
                'avg_profit': avg_profit
            }
        
        # Đếm số lượng loại thị trường
        market_type_counts = {}
        if hasattr(self.data, 'market_condition'):
            for condition in self.data['market_condition']:
                if condition not in market_type_counts:
                    market_type_counts[condition] = 0
                market_type_counts[condition] += 1
        
        # Kết quả backtest
        backtest_result = {
            'strategy': strategy,
            'risk_level': risk_level,
            'initial_balance': initial_balance,
            'final_balance': balance,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'trades': trades,
            'equity_curve': equity_curve,
            'market_condition_performance': market_condition_performance,
            'market_type_counts': market_type_counts
        }
        
        logger.info(f"Kết quả backtest chiến lược {strategy} (risk={risk_level}): "
                   f"P/L: {profit_loss_pct:.2f}%, Win Rate: {win_rate:.2f}%, "
                   f"Trades: {len(trades)}, Max DD: {max_drawdown_pct:.2f}%")
        
        return backtest_result
    
    def plot_results(self, result, save_path=None):
        """
        Vẽ biểu đồ kết quả backtest
        
        Args:
            result (dict): Kết quả backtest
            save_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            None
        """
        # Tạo biểu đồ
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 18), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Plot giá và các điểm giao dịch
        ax1.plot(self.data.index, self.data['Close'], label='Close Price')
        
        for trade in result['trades']:
            entry_time = trade['entry_time']
            exit_time = trade['exit_time']
            
            if trade['type'] == 'LONG':
                ax1.plot([entry_time, exit_time], [trade['entry_price'], trade['exit_price']], 
                       'g-' if trade['profit'] > 0 else 'r-', alpha=0.5)
                ax1.plot(entry_time, trade['entry_price'], '^', color='g', markersize=6)
                ax1.plot(exit_time, trade['exit_price'], 'o', color='g' if trade['profit'] > 0 else 'r', markersize=6)
            else:  # SHORT
                ax1.plot([entry_time, exit_time], [trade['entry_price'], trade['exit_price']], 
                       'g-' if trade['profit'] > 0 else 'r-', alpha=0.5)
                ax1.plot(entry_time, trade['entry_price'], 'v', color='r', markersize=6)
                ax1.plot(exit_time, trade['exit_price'], 'o', color='g' if trade['profit'] > 0 else 'r', markersize=6)
        
        ax1.set_title(f"{self.symbol} {self.interval} - {result['strategy']} Strategy (Risk: {result['risk_level']*100:.0f}%)")
        ax1.set_ylabel('Price')
        ax1.grid(True)
        ax1.legend()
        
        # Plot Equity Curve
        equity_dates = pd.date_range(start=self.data.index[0], periods=len(result['equity_curve']), freq=self.data.index[1] - self.data.index[0])
        ax2.plot(equity_dates, result['equity_curve'], label='Equity Curve')
        ax2.set_ylabel('Balance')
        ax2.grid(True)
        ax2.legend()
        
        # Plot Drawdown
        drawdowns = []
        peak = result['equity_curve'][0]
        for balance in result['equity_curve']:
            if balance > peak:
                peak = balance
            drawdown_pct = (peak - balance) / peak * 100
            drawdowns.append(drawdown_pct)
        
        ax3.fill_between(equity_dates, drawdowns, color='red', alpha=0.3, label='Drawdown')
        ax3.set_ylabel('Drawdown (%)')
        ax3.set_xlabel('Date')
        ax3.grid(True)
        ax3.legend()
        
        # Thêm thông tin hiệu suất
        performance_text = (
            f"Initial Balance: ${result['initial_balance']:.2f}\n"
            f"Final Balance: ${result['final_balance']:.2f}\n"
            f"Profit/Loss: ${result['profit_loss']:.2f} ({result['profit_loss_pct']:.2f}%)\n"
            f"Max Drawdown: {result['max_drawdown_pct']:.2f}%\n"
            f"Total Trades: {result['total_trades']}\n"
            f"Win Rate: {result['win_rate']:.2f}%\n"
            f"Profit Factor: {result['profit_factor']:.2f}\n"
        )
        
        plt.figtext(0.01, 0.01, performance_text, ha='left', fontsize=10, 
                  bbox=dict(facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
            logger.info(f"Đã lưu biểu đồ tại {save_path}")
        
        plt.close()
    
    def run_multi_risk_test(self, risk_levels=[0.10, 0.15, 0.20, 0.25]):
        """
        Chạy test với nhiều mức rủi ro khác nhau
        
        Args:
            risk_levels (list): Danh sách các mức rủi ro cần test
            
        Returns:
            dict: Kết quả test
        """
        results = {}
        strategies = ['multi_risk', 'sideways', 'combined']
        
        for strategy in strategies:
            results[strategy] = {}
            
            for risk_level in risk_levels:
                backtest_result = self.run_backtest(strategy, risk_level)
                
                if backtest_result:
                    risk_key = f"{risk_level:.2f}"
                    results[strategy][risk_key] = backtest_result
                    
                    # Tạo đường dẫn lưu biểu đồ
                    chart_path = self.results_dir / f"{self.symbol}_{self.interval}_{strategy}_risk{int(risk_level*100)}.png"
                    self.plot_results(backtest_result, save_path=chart_path)
        
        # Lưu kết quả
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_path = self.results_dir / f"multi_risk_test_results_{timestamp}.json"
        
        # Xóa equity_curve và trade details trước khi lưu để giảm kích thước file
        results_to_save = {}
        for strategy, strategy_results in results.items():
            results_to_save[strategy] = {}
            for risk_key, risk_result in strategy_results.items():
                results_to_save[strategy][risk_key] = risk_result.copy()
                results_to_save[strategy][risk_key].pop('equity_curve', None)
                results_to_save[strategy][risk_key].pop('trades', None)
        
        with open(results_path, 'w') as f:
            json.dump(results_to_save, f, indent=4, default=str)
        
        logger.info(f"Đã lưu kết quả test tại {results_path}")
        
        # Tạo báo cáo tổng hợp
        self.create_summary_report(results)
        
        return results
    
    def create_summary_report(self, results):
        """
        Tạo báo cáo tổng hợp
        
        Args:
            results (dict): Kết quả test
            
        Returns:
            None
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.results_dir / f"multi_risk_test_summary_{timestamp}.md"
        
        with open(report_path, 'w') as f:
            f.write(f"# Báo Cáo Kiểm Thử Nhiều Mức Rủi Ro\n\n")
            
            f.write(f"## Thông Tin Kiểm Thử\n\n")
            f.write(f"- **Symbol:** {self.symbol}\n")
            f.write(f"- **Interval:** {self.interval}\n")
            f.write(f"- **Thời gian:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"## Kết Quả Tổng Hợp\n\n")
            
            # Tạo bảng tổng hợp
            strategies = list(results.keys())
            risk_levels = list(results[strategies[0]].keys())
            
            f.write("### So sánh lợi nhuận (%)\n\n")
            f.write("| Strategy | " + " | ".join([f"Risk {float(r)*100:.0f}%" for r in risk_levels]) + " |\n")
            f.write("|" + "-"*10 + "|" + "-"*15 * len(risk_levels) + "|\n")
            
            for strategy in strategies:
                row = f"| {strategy} |"
                for risk_level in risk_levels:
                    if risk_level in results[strategy]:
                        profit = results[strategy][risk_level]['profit_loss_pct']
                        row += f" {profit:.2f}% |"
                    else:
                        row += " N/A |"
                f.write(row + "\n")
            
            f.write("\n### So sánh tỷ lệ thắng (%)\n\n")
            f.write("| Strategy | " + " | ".join([f"Risk {float(r)*100:.0f}%" for r in risk_levels]) + " |\n")
            f.write("|" + "-"*10 + "|" + "-"*15 * len(risk_levels) + "|\n")
            
            for strategy in strategies:
                row = f"| {strategy} |"
                for risk_level in risk_levels:
                    if risk_level in results[strategy]:
                        win_rate = results[strategy][risk_level]['win_rate']
                        row += f" {win_rate:.2f}% |"
                    else:
                        row += " N/A |"
                f.write(row + "\n")
            
            f.write("\n### So sánh drawdown tối đa (%)\n\n")
            f.write("| Strategy | " + " | ".join([f"Risk {float(r)*100:.0f}%" for r in risk_levels]) + " |\n")
            f.write("|" + "-"*10 + "|" + "-"*15 * len(risk_levels) + "|\n")
            
            for strategy in strategies:
                row = f"| {strategy} |"
                for risk_level in risk_levels:
                    if risk_level in results[strategy]:
                        dd = results[strategy][risk_level]['max_drawdown_pct']
                        row += f" {dd:.2f}% |"
                    else:
                        row += " N/A |"
                f.write(row + "\n")
            
            # Hiệu suất theo điều kiện thị trường
            f.write("\n## Hiệu Suất Theo Điều Kiện Thị Trường\n\n")
            
            for strategy in strategies:
                f.write(f"\n### Chiến lược: {strategy}\n\n")
                
                for risk_level in risk_levels:
                    if risk_level in results[strategy]:
                        result = results[strategy][risk_level]
                        f.write(f"\n#### Risk {float(risk_level)*100:.0f}%\n\n")
                        
                        if 'market_condition_performance' in result:
                            f.write("| Market Condition | Trades | Win Rate | Avg Profit |\n")
                            f.write("|" + "-"*17 + "|" + "-"*8 + "|" + "-"*10 + "|" + "-"*12 + "|\n")
                            
                            for condition, stats in result['market_condition_performance'].items():
                                f.write(f"| {condition} | {stats['trades']} | {stats['win_rate']:.2f}% | ${stats['avg_profit']:.2f} |\n")
            
            # Nhận xét và kết luận
            f.write("\n## Nhận Xét và Kết Luận\n\n")
            
            # Tìm chiến lược và mức rủi ro tốt nhất
            best_profit_strategy = None
            best_profit_risk = None
            best_profit = -float('inf')
            
            best_win_rate_strategy = None
            best_win_rate_risk = None
            best_win_rate = -float('inf')
            
            best_rr_strategy = None
            best_rr_risk = None
            best_rr = -float('inf')
            
            for strategy in strategies:
                for risk_level in risk_levels:
                    if risk_level in results[strategy]:
                        result = results[strategy][risk_level]
                        
                        profit = result['profit_loss_pct']
                        if profit > best_profit:
                            best_profit = profit
                            best_profit_strategy = strategy
                            best_profit_risk = risk_level
                        
                        win_rate = result['win_rate']
                        if win_rate > best_win_rate:
                            best_win_rate = win_rate
                            best_win_rate_strategy = strategy
                            best_win_rate_risk = risk_level
                        
                        # Tính risk-reward ratio (profit/drawdown)
                        if result['max_drawdown_pct'] > 0:
                            rr = profit / result['max_drawdown_pct']
                            if rr > best_rr:
                                best_rr = rr
                                best_rr_strategy = strategy
                                best_rr_risk = risk_level
            
            f.write("### Những phát hiện chính\n\n")
            
            if best_profit_strategy:
                f.write(f"- **Lợi nhuận cao nhất:** {best_profit:.2f}% đạt được với chiến lược *{best_profit_strategy}* ở mức rủi ro *{float(best_profit_risk)*100:.0f}%*\n")
            
            if best_win_rate_strategy:
                f.write(f"- **Tỷ lệ thắng cao nhất:** {best_win_rate:.2f}% đạt được với chiến lược *{best_win_rate_strategy}* ở mức rủi ro *{float(best_win_rate_risk)*100:.0f}%*\n")
            
            if best_rr_strategy:
                f.write(f"- **Tỷ số lợi nhuận/rủi ro tốt nhất:** {best_rr:.2f} đạt được với chiến lược *{best_rr_strategy}* ở mức rủi ro *{float(best_rr_risk)*100:.0f}%*\n")
            
            f.write("\n### Đề xuất chiến lược\n\n")
            
            # Phân tích hiệu suất chiến lược combined so với các chiến lược riêng lẻ
            combined_better = True
            for risk_level in risk_levels:
                if (risk_level in results.get('combined', {}) and 
                    risk_level in results.get('multi_risk', {}) and 
                    risk_level in results.get('sideways', {})):
                    
                    combined_profit = results['combined'][risk_level]['profit_loss_pct']
                    multi_profit = results['multi_risk'][risk_level]['profit_loss_pct']
                    sideways_profit = results['sideways'][risk_level]['profit_loss_pct']
                    
                    if combined_profit < max(multi_profit, sideways_profit):
                        combined_better = False
                        break
            
            if combined_better:
                f.write("- **Chiến lược kết hợp** cho hiệu suất tốt hơn các chiến lược riêng lẻ, nên được sử dụng để tối ưu hóa kết quả giao dịch.\n")
            else:
                if best_profit_strategy:
                    f.write(f"- **Chiến lược {best_profit_strategy}** với mức rủi ro **{float(best_profit_risk)*100:.0f}%** cho hiệu suất lợi nhuận tốt nhất.\n")
                
                if best_rr_strategy and best_rr_strategy != best_profit_strategy:
                    f.write(f"- **Chiến lược {best_rr_strategy}** với mức rủi ro **{float(best_rr_risk)*100:.0f}%** cho tỷ lệ lợi nhuận/rủi ro tốt nhất, phù hợp với nhà đầu tư cẩn trọng.\n")
            
            # Nhận xét về mức rủi ro
            low_risk_results = {}
            high_risk_results = {}
            
            for strategy in strategies:
                for risk_level in risk_levels:
                    if risk_level in results[strategy]:
                        if float(risk_level) <= 0.15:  # Rủi ro thấp (10-15%)
                            if strategy not in low_risk_results:
                                low_risk_results[strategy] = []
                            low_risk_results[strategy].append((risk_level, results[strategy][risk_level]))
                        else:  # Rủi ro cao (20-25%)
                            if strategy not in high_risk_results:
                                high_risk_results[strategy] = []
                            high_risk_results[strategy].append((risk_level, results[strategy][risk_level]))
            
            # So sánh hiệu suất giữa rủi ro thấp và cao
            avg_low_profit = 0
            count_low = 0
            avg_high_profit = 0
            count_high = 0
            
            for strategy, results_list in low_risk_results.items():
                for _, result in results_list:
                    avg_low_profit += result['profit_loss_pct']
                    count_low += 1
            
            for strategy, results_list in high_risk_results.items():
                for _, result in results_list:
                    avg_high_profit += result['profit_loss_pct']
                    count_high += 1
            
            if count_low > 0:
                avg_low_profit /= count_low
            
            if count_high > 0:
                avg_high_profit /= count_high
            
            f.write("\n### Nhận xét về mức rủi ro\n\n")
            
            if count_low > 0 and count_high > 0:
                if avg_high_profit > avg_low_profit:
                    f.write(f"- Các mức rủi ro cao (20-25%) cho lợi nhuận trung bình ({avg_high_profit:.2f}%) tốt hơn so với các mức rủi ro thấp (10-15%, {avg_low_profit:.2f}%).\n")
                    f.write("- Tuy nhiên, các mức rủi ro cao cũng đi kèm với drawdown lớn hơn, phù hợp với nhà đầu tư chấp nhận biến động lớn.\n")
                else:
                    f.write(f"- Các mức rủi ro thấp (10-15%) cho lợi nhuận trung bình ({avg_low_profit:.2f}%) tốt hơn so với các mức rủi ro cao (20-25%, {avg_high_profit:.2f}%).\n")
                    f.write("- Điều này cho thấy một cách tiếp cận thận trọng có thể hiệu quả hơn trong điều kiện thị trường hiện tại.\n")
            
            # Hiệu suất của chiến lược thị trường đi ngang
            sideways_performance = {}
            for risk_level in risk_levels:
                if risk_level in results.get('sideways', {}):
                    result = results['sideways'][risk_level]
                    
                    if 'market_condition_performance' in result and 'SIDEWAYS' in result['market_condition_performance']:
                        sideways_stats = result['market_condition_performance']['SIDEWAYS']
                        sideways_performance[risk_level] = sideways_stats
            
            if sideways_performance:
                f.write("\n### Hiệu suất chiến lược thị trường đi ngang\n\n")
                
                best_sideways_risk = None
                best_sideways_win_rate = -float('inf')
                
                for risk_level, stats in sideways_performance.items():
                    if stats['win_rate'] > best_sideways_win_rate:
                        best_sideways_win_rate = stats['win_rate']
                        best_sideways_risk = risk_level
                
                if best_sideways_risk:
                    f.write(f"- Chiến lược thị trường đi ngang đạt hiệu suất tốt nhất với mức rủi ro **{float(best_sideways_risk)*100:.0f}%**, cho tỷ lệ thắng **{best_sideways_win_rate:.2f}%**.\n")
                    
                    if best_sideways_win_rate > 50:
                        f.write("- Điều này cho thấy chiến lược đã được tối ưu hóa tốt cho thị trường đi ngang.\n")
                    else:
                        f.write("- Mặc dù đã cải thiện, chiến lược thị trường đi ngang vẫn cần được tối ưu hóa thêm.\n")
            
            f.write("\n### Kết luận\n\n")
            
            # Tóm tắt kết luận dựa trên phân tích
            if best_profit_strategy and best_rr_strategy and best_win_rate_strategy:
                if best_profit_strategy == best_rr_strategy == best_win_rate_strategy:
                    f.write(f"- **Chiến lược {best_profit_strategy}** với mức rủi ro **{float(best_profit_risk)*100:.0f}%** cho hiệu suất tốt nhất trên tất cả các phương diện.\n")
                else:
                    f.write("- Các chiến lược khác nhau cho hiệu suất tốt trên các phương diện khác nhau:\n")
                    f.write(f"  * **Lợi nhuận cao nhất:** {best_profit_strategy} ({float(best_profit_risk)*100:.0f}%)\n")
                    f.write(f"  * **Tỷ lệ thắng cao nhất:** {best_win_rate_strategy} ({float(best_win_rate_risk)*100:.0f}%)\n")
                    f.write(f"  * **Tỷ lệ lợi nhuận/rủi ro tốt nhất:** {best_rr_strategy} ({float(best_rr_risk)*100:.0f}%)\n")
            
            # Đề xuất cuối cùng
            f.write("\n### Đề xuất cuối cùng\n\n")
            
            if best_rr_strategy:  # Ưu tiên RR ratio
                f.write(f"- **Ưu tiên sử dụng chiến lược {best_rr_strategy} với mức rủi ro {float(best_rr_risk)*100:.0f}%** để cân bằng tốt giữa lợi nhuận và rủi ro.\n")
            elif best_profit_strategy:
                f.write(f"- **Sử dụng chiến lược {best_profit_strategy} với mức rủi ro {float(best_profit_risk)*100:.0f}%** để tối đa hóa lợi nhuận.\n")
        
        logger.info(f"Đã tạo báo cáo tổng hợp tại {report_path}")

def run_quick_backtest():
    """
    Chạy backtest nhanh để kiểm tra hiệu suất các chiến lược
    """
    print("\n=== BẮT ĐẦU BACKTEST NHANH ===")
    
    # Các cặp tiền để test
    symbols = ['BTCUSDT']
    
    # Các khung thời gian để test
    intervals = ['1h']
    
    # Các mức rủi ro để test
    risk_levels = [0.10, 0.15, 0.20, 0.25]
    
    # Chạy backtest cho mỗi cặp tiền và khung thời gian
    for symbol in symbols:
        for interval in intervals:
            print(f"\nTesting {symbol} {interval}...")
            
            try:
                # Tạo backtest runner
                backtest_runner = BacktestRunner(symbol=symbol, interval=interval)
                
                # Chạy test với nhiều mức rủi ro
                results = backtest_runner.run_multi_risk_test(risk_levels=risk_levels)
                
                print(f"Completed testing {symbol} {interval}")
                
                # In kết quả tóm tắt
                print("\n=== TÓM TẮT KẾT QUẢ ===")
                
                for strategy in results:
                    print(f"\nStrategy: {strategy}")
                    
                    for risk_key, result in results[strategy].items():
                        print(f"  Risk {float(risk_key)*100:.0f}%: P/L: {result['profit_loss_pct']:.2f}%, "
                             f"Win Rate: {result['win_rate']:.2f}%, Trades: {result['total_trades']}")
            
            except Exception as e:
                print(f"Error testing {symbol} {interval}: {str(e)}")
    
    print("\n=== BACKTEST HOÀN THÀNH ===")
    print(f"Kết quả chi tiết và biểu đồ được lưu trong thư mục: ./quick_test_results")

if __name__ == "__main__":
    run_quick_backtest()