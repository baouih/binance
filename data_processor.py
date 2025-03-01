"""
Module xử lý dữ liệu (Data Processor)

Module này cung cấp các công cụ để xử lý dữ liệu thị trường, tính toán các chỉ báo kỹ thuật
và chuẩn hóa dữ liệu để sử dụng trong các chiến lược giao dịch.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional, Union
import traceback

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("data_processor")

class DataProcessor:
    """Lớp xử lý dữ liệu thị trường"""
    
    def __init__(self, binance_api=None, simulation_mode=False):
        """
        Khởi tạo data processor
        
        Args:
            binance_api: Đối tượng BinanceAPI
            simulation_mode (bool): Chế độ mô phỏng
        """
        self.binance_api = binance_api
        self.simulation_mode = simulation_mode
        self.common_indicators = [
            'rsi', 'macd', 'bbands', 'ema', 'atr', 'stoch', 'obv', 'adx'
        ]
        
    def download_historical_data(self, symbol: str, interval: str, 
                              start_time: str = None, end_time: str = None,
                              limit: int = 1000, save_to_file: bool = True,
                              output_dir: str = 'data') -> pd.DataFrame:
        """
        Tải dữ liệu lịch sử từ Binance
        
        Args:
            symbol (str): Mã cặp giao dịch
            interval (str): Khung thời gian
            start_time (str, optional): Thời gian bắt đầu (YYYY-MM-DD)
            end_time (str, optional): Thời gian kết thúc (YYYY-MM-DD)
            limit (int): Số lượng candlestick tối đa
            save_to_file (bool): Có lưu vào file hay không
            output_dir (str): Thư mục lưu file
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu lịch sử
        """
        if self.binance_api is None:
            logger.error("Không có kết nối Binance API, không thể tải dữ liệu")
            return None
            
        try:
            # Sử dụng phương thức download_historical_data của BinanceAPI
            file_path = self.binance_api.download_historical_data(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                output_dir=output_dir
            )
            
            if file_path is None:
                logger.error(f"Không thể tải dữ liệu cho {symbol} {interval}")
                return None
                
            # Đọc file CSV
            df = pd.read_csv(file_path)
            
            # Đảm bảo timestamp là datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            logger.info(f"Đã tải dữ liệu {symbol} {interval}: {len(df)} candles từ {df['timestamp'].min()} đến {df['timestamp'].max()}")
            
            # Thêm các chỉ báo kỹ thuật
            df = self.add_indicators(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu lịch sử: {str(e)}")
            logger.error(traceback.format_exc())
            return None
            
    def add_indicators(self, df: pd.DataFrame, indicators: List[str] = None) -> pd.DataFrame:
        """
        Thêm các chỉ báo kỹ thuật vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            indicators (List[str], optional): Danh sách chỉ báo cần thêm
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã thêm
        """
        if indicators is None:
            indicators = self.common_indicators
            
        try:
            # Đảm bảo có đủ dữ liệu OHLCV
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Thiếu các cột dữ liệu: {missing_columns}")
                return df
            
            # Tạo bản sao để tránh ảnh hưởng đến dữ liệu gốc
            result_df = df.copy()
            
            # Thêm từng chỉ báo
            for indicator in indicators:
                try:
                    if indicator.lower() == 'rsi':
                        result_df = self._add_rsi(result_df)
                    elif indicator.lower() == 'macd':
                        result_df = self._add_macd(result_df)
                    elif indicator.lower() == 'bbands':
                        result_df = self._add_bollinger_bands(result_df)
                    elif indicator.lower() == 'ema':
                        result_df = self._add_ema(result_df)
                    elif indicator.lower() == 'atr':
                        result_df = self._add_atr(result_df)
                    elif indicator.lower() == 'stoch':
                        result_df = self._add_stochastic(result_df)
                    elif indicator.lower() == 'obv':
                        result_df = self._add_obv(result_df)
                    elif indicator.lower() == 'adx':
                        result_df = self._add_adx(result_df)
                except Exception as e:
                    logger.error(f"Lỗi khi thêm chỉ báo {indicator}: {str(e)}")
                    
            return result_df
            
        except Exception as e:
            logger.error(f"Lỗi khi thêm các chỉ báo: {str(e)}")
            logger.error(traceback.format_exc())
            return df
            
    def _add_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Thêm chỉ báo RSI"""
        try:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            df['rsi'] = rsi
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính RSI: {str(e)}")
            return df
            
    def _add_macd(self, df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
        """Thêm chỉ báo MACD"""
        try:
            ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
            ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            histogram = macd_line - signal_line
            
            df['macd'] = macd_line
            df['macd_signal'] = signal_line
            df['macd_hist'] = histogram
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính MACD: {str(e)}")
            return df
            
    def _add_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """Thêm chỉ báo Bollinger Bands"""
        try:
            sma = df['close'].rolling(window=period).mean()
            rolling_std = df['close'].rolling(window=period).std()
            
            upper_band = sma + (rolling_std * std_dev)
            lower_band = sma - (rolling_std * std_dev)
            
            df['bb_middle'] = sma
            df['bb_upper'] = upper_band
            df['bb_lower'] = lower_band
            df['bb_width'] = (upper_band - lower_band) / sma
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính Bollinger Bands: {str(e)}")
            return df
            
    def _add_ema(self, df: pd.DataFrame, periods: List[int] = [9, 21, 50, 200]) -> pd.DataFrame:
        """Thêm các đường EMA"""
        try:
            for period in periods:
                df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính EMA: {str(e)}")
            return df
            
    def _add_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Thêm chỉ báo ATR"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            
            df['atr'] = true_range.rolling(period).mean()
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính ATR: {str(e)}")
            return df
            
    def _add_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
        """Thêm chỉ báo Stochastic"""
        try:
            low_min = df['low'].rolling(window=k_period).min()
            high_max = df['high'].rolling(window=k_period).max()
            
            k = 100 * ((df['close'] - low_min) / (high_max - low_min))
            d = k.rolling(window=d_period).mean()
            
            df['stoch_k'] = k
            df['stoch_d'] = d
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính Stochastic: {str(e)}")
            return df
            
    def _add_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Thêm chỉ báo On-Balance Volume"""
        try:
            df['obv'] = np.where(df['close'] > df['close'].shift(1), df['volume'], 
                               np.where(df['close'] < df['close'].shift(1), -df['volume'], 0)).cumsum()
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính OBV: {str(e)}")
            return df
            
    def _add_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Thêm chỉ báo ADX"""
        try:
            plus_dm = df['high'].diff()
            minus_dm = df['low'].diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm > 0] = 0
            
            tr1 = df['high'] - df['low']
            tr2 = np.abs(df['high'] - df['close'].shift(1))
            tr3 = np.abs(df['low'] - df['close'].shift(1))
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / 
                          true_range.ewm(alpha=1/period, adjust=False).mean())
            minus_di = abs(100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / 
                          true_range.ewm(alpha=1/period, adjust=False).mean()))
            
            dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
            adx = dx.ewm(alpha=1/period, adjust=False).mean()
            
            df['adx'] = adx
            df['plus_di'] = plus_di
            df['minus_di'] = minus_di
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính ADX: {str(e)}")
            return df
            
    def normalize_data(self, df: pd.DataFrame, columns: List[str] = None) -> pd.DataFrame:
        """
        Chuẩn hóa dữ liệu trong DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame cần chuẩn hóa
            columns (List[str], optional): Danh sách cột cần chuẩn hóa
            
        Returns:
            pd.DataFrame: DataFrame đã chuẩn hóa
        """
        try:
            if columns is None:
                columns = [col for col in df.columns if col not in ['timestamp', 'date', 'time']]
                
            result_df = df.copy()
            
            for col in columns:
                if col in result_df.columns:
                    col_min = result_df[col].min()
                    col_max = result_df[col].max()
                    
                    if col_max > col_min:
                        result_df[f"{col}_norm"] = (result_df[col] - col_min) / (col_max - col_min)
                        
            return result_df
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn hóa dữ liệu: {str(e)}")
            return df
            
    def prepare_ml_data(self, df: pd.DataFrame, target_column: str, 
                      feature_columns: List[str] = None, 
                      shift_periods: int = 1) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Chuẩn bị dữ liệu cho mô hình học máy
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            target_column (str): Tên cột mục tiêu
            feature_columns (List[str], optional): Danh sách cột đặc trưng
            shift_periods (int): Số kỳ dịch chuyển cho mục tiêu
            
        Returns:
            Tuple[pd.DataFrame, pd.Series]: (X_features, y_target)
        """
        try:
            if feature_columns is None:
                # Sử dụng tất cả các cột số trừ timestamp và target
                feature_columns = [col for col in df.columns if col != 'timestamp' and col != target_column 
                                 and pd.api.types.is_numeric_dtype(df[col])]
                
            # Tạo mục tiêu dự đoán (giá sẽ tăng hay giảm sau shift_periods)
            if shift_periods > 0:
                target = df[target_column].shift(-shift_periods)
            else:
                target = df[target_column]
                
            # Lấy dữ liệu đặc trưng
            features = df[feature_columns].copy()
            
            # Loại bỏ các hàng có giá trị NaN
            features = features.dropna()
            target = target.iloc[:len(features)]
            
            return features, target
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị dữ liệu ML: {str(e)}")
            return None, None
            
    def find_correlation(self, df: pd.DataFrame, target_column: str, 
                       min_correlation: float = 0.3) -> Dict[str, float]:
        """
        Tìm tương quan giữa các cột và cột mục tiêu
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            target_column (str): Tên cột mục tiêu
            min_correlation (float): Ngưỡng tương quan tối thiểu
            
        Returns:
            Dict[str, float]: Ánh xạ tên cột -> giá trị tương quan
        """
        try:
            if target_column not in df.columns:
                logger.error(f"Cột mục tiêu {target_column} không tồn tại trong DataFrame")
                return {}
                
            # Tính ma trận tương quan
            correlation = df.corr()[target_column]
            
            # Lọc các cột có tương quan >= min_correlation
            strong_correlations = correlation[abs(correlation) >= min_correlation]
            
            # Chuyển thành từ điển
            result = strong_correlations.to_dict()
            
            # Loại bỏ tương quan với chính nó
            if target_column in result:
                del result[target_column]
                
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tìm tương quan: {str(e)}")
            return {}
            
    def create_market_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo các đặc trưng để phát hiện chế độ thị trường
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            
        Returns:
            pd.DataFrame: DataFrame với các đặc trưng mới
        """
        try:
            result_df = df.copy()
            
            # Thêm ADX nếu chưa có
            if 'adx' not in result_df.columns:
                result_df = self._add_adx(result_df)
                
            # Thêm ATR nếu chưa có
            if 'atr' not in result_df.columns:
                result_df = self._add_atr(result_df)
                
            # Thêm Bollinger Bands nếu chưa có
            if 'bb_width' not in result_df.columns:
                result_df = self._add_bollinger_bands(result_df)
                
            # Biến động (volatility)
            result_df['volatility'] = result_df['atr'] / result_df['close'] * 100
            
            # Độ mạnh xu hướng (trend strength)
            result_df['trend_strength'] = result_df['adx'] / 100.0
            
            # Tỷ lệ khối lượng giao dịch (volume ratio)
            result_df['volume_ratio'] = result_df['volume'] / result_df['volume'].rolling(window=20).mean()
            
            # Độ rộng kênh giá (price channel width)
            result_df['channel_width'] = (result_df['high'].rolling(window=20).max() - 
                                       result_df['low'].rolling(window=20).min()) / result_df['close'] * 100
            
            # Hệ số Hurst (phát hiện tính ngẫu nhiên)
            result_df['log_returns'] = np.log(result_df['close'] / result_df['close'].shift(1))
            
            # Returns dispersion (phân tán lợi nhuận)
            result_df['returns_dispersion'] = result_df['log_returns'].rolling(window=20).std()
            
            # Phân loại chế độ thị trường dựa trên các chỉ số
            conditions = [
                # Xu hướng tăng mạnh
                (result_df['adx'] > 25) & (result_df['plus_di'] > result_df['minus_di']),
                # Xu hướng giảm mạnh
                (result_df['adx'] > 25) & (result_df['plus_di'] < result_df['minus_di']),
                # Dao động (ranging)
                (result_df['adx'] <= 25) & (result_df['bb_width'] < result_df['bb_width'].rolling(window=50).mean()),
                # Biến động cao (volatile)
                (result_df['volatility'] > result_df['volatility'].rolling(window=50).mean() * 1.5)
            ]
            
            choices = ['uptrend', 'downtrend', 'ranging', 'volatile']
            result_df['market_regime'] = np.select(conditions, choices, default='neutral')
            
            return result_df
        except Exception as e:
            logger.error(f"Lỗi khi tạo đặc trưng chế độ thị trường: {str(e)}")
            return df
            
    def merge_multi_timeframe_data(self, dataframes: Dict[str, pd.DataFrame], 
                                primary_timeframe: str) -> pd.DataFrame:
        """
        Kết hợp dữ liệu từ nhiều khung thời gian
        
        Args:
            dataframes (Dict[str, pd.DataFrame]): Ánh xạ timeframe -> DataFrame
            primary_timeframe (str): Khung thời gian chính
            
        Returns:
            pd.DataFrame: DataFrame kết hợp
        """
        try:
            if primary_timeframe not in dataframes:
                logger.error(f"Khung thời gian chính {primary_timeframe} không có trong dữ liệu")
                return None
                
            # Lấy DataFrame chính
            primary_df = dataframes[primary_timeframe].copy()
            
            # Đảm bảo timestamp là index
            if 'timestamp' in primary_df.columns:
                primary_df.set_index('timestamp', inplace=True)
                
            # Với mỗi khung thời gian khác
            for timeframe, df in dataframes.items():
                if timeframe == primary_timeframe:
                    continue
                    
                # Đảm bảo timestamp là index
                timeframe_df = df.copy()
                if 'timestamp' in timeframe_df.columns:
                    timeframe_df.set_index('timestamp', inplace=True)
                    
                # Lấy các cột cần thêm vào
                for col in timeframe_df.columns:
                    if col in ['open', 'high', 'low', 'close', 'volume']:
                        continue  # Bỏ qua các cột OHLCV
                    
                    # Thêm tiền tố khung thời gian
                    new_col = f"{timeframe}_{col}"
                    
                    # Ghép DataFrame theo index timestamp
                    primary_df = primary_df.join(timeframe_df[col].rename(new_col), how='left')
                    
                    # Điền các giá trị NaN bằng forward fill
                    primary_df[new_col] = primary_df[new_col].fillna(method='ffill')
                    
            # Reset index nếu cần
            primary_df.reset_index(inplace=True)
            
            return primary_df
        except Exception as e:
            logger.error(f"Lỗi khi kết hợp dữ liệu đa khung thời gian: {str(e)}")
            return dataframes[primary_timeframe]
            
    def simulate_real_time_data(self, df: pd.DataFrame, batch_size: int = 1) -> pd.DataFrame:
        """
        Mô phỏng dữ liệu thời gian thực bằng cách chia nhỏ DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu đầy đủ
            batch_size (int): Số lượng candle trong mỗi batch
            
        Returns:
            pd.DataFrame: DataFrame batch hiện tại
        """
        if not hasattr(self, 'current_index'):
            self.current_index = 0
            
        if self.current_index >= len(df):
            # Kết thúc dữ liệu
            return None
            
        # Lấy batch hiện tại
        batch = df.iloc[:self.current_index + batch_size].copy()
        
        # Tăng chỉ số cho lần sau
        self.current_index += batch_size
        
        return batch
        
    def reset_simulation(self):
        """Reset chỉ số mô phỏng"""
        self.current_index = 0