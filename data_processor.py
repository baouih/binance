#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data Processor - Xử lý và chuẩn bị dữ liệu cho ML trong giao dịch tiền điện tử
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union, Optional, Any

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('data_processor')

class DataProcessor:
    """
    Lớp xử lý dữ liệu cho ML trong giao dịch tiền điện tử
    """
    
    def __init__(
        self,
        api: Any = None,
        data_dir: str = 'data',
        cache_dir: str = 'data/cache',
        use_cache: bool = True,
        cache_expiry: int = 3600
    ):
        """
        Khởi tạo DataProcessor
        
        Args:
            api: API client (như Binance API)
            data_dir: Thư mục dữ liệu
            cache_dir: Thư mục cache
            use_cache: Sử dụng cache hay không
            cache_expiry: Thời gian hết hạn cache (giây)
        """
        self.api = api
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.cache_expiry = cache_expiry
        
        # Tạo thư mục dữ liệu nếu chưa tồn tại
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        logger.info(f"Đã khởi tạo DataProcessor, sử dụng cache dir: {cache_dir}")
    
    def get_historical_data(
        self,
        symbol: str,
        interval: str,
        limit: int = 1000,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        use_cache: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu lịch sử
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            limit: Số lượng nến tối đa
            start_time: Thời gian bắt đầu
            end_time: Thời gian kết thúc
            use_cache: Sử dụng cache hay không, None sẽ sử dụng giá trị mặc định
        
        Returns:
            DataFrame chứa dữ liệu lịch sử
        """
        if use_cache is None:
            use_cache = self.use_cache
        
        # Tạo tên file cache
        cache_filename = f"{symbol}_{interval}_{limit}"
        if start_time:
            cache_filename += f"_{start_time.strftime('%Y%m%d')}"
        if end_time:
            cache_filename += f"_{end_time.strftime('%Y%m%d')}"
        cache_filename += ".csv"
        
        cache_path = os.path.join(self.cache_dir, cache_filename)
        
        # Kiểm tra cache
        if use_cache and os.path.exists(cache_path):
            cache_time = os.path.getmtime(cache_path)
            if datetime.now().timestamp() - cache_time < self.cache_expiry:
                try:
                    df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                    logger.info(f"Đã tải dữ liệu từ cache: {cache_path}")
                    return df
                except Exception as e:
                    logger.error(f"Lỗi khi tải dữ liệu từ cache: {str(e)}")
        
        # Lấy dữ liệu mới
        if self.api is None:
            # Nếu không có API, tạo dữ liệu mẫu
            logger.warning("Không có API, tạo dữ liệu mẫu")
            df = self._generate_sample_data(symbol, interval, limit)
        else:
            try:
                # Lấy dữ liệu từ API
                klines = self.api.get_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # Chuyển đổi thành DataFrame
                df = pd.DataFrame(
                    klines,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                             'close_time', 'quote_asset_volume', 'trades_count',
                             'taker_buy_base', 'taker_buy_quote', 'ignore']
                )
                
                # Xử lý dữ liệu
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Chuyển đổi kiểu dữ liệu
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col])
                
                logger.info(f"Đã lấy {len(df)} dòng dữ liệu cho {symbol} {interval}")
                
                # Lưu vào cache
                if use_cache:
                    df.to_csv(cache_path)
                    logger.info(f"Đã lưu dữ liệu vào cache: {cache_path}")
            
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu từ API: {str(e)}")
                # Tạo dữ liệu mẫu trong trường hợp lỗi
                df = self._generate_sample_data(symbol, interval, limit)
        
        return df
    
    def _generate_sample_data(
        self,
        symbol: str,
        interval: str,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Tạo dữ liệu mẫu cho kiểm thử
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            limit: Số lượng nến
        
        Returns:
            DataFrame chứa dữ liệu mẫu
        """
        # Tạo index thời gian
        end_time = datetime.now()
        
        if interval == '1m':
            delta = timedelta(minutes=1)
        elif interval == '5m':
            delta = timedelta(minutes=5)
        elif interval == '15m':
            delta = timedelta(minutes=15)
        elif interval == '30m':
            delta = timedelta(minutes=30)
        elif interval == '1h':
            delta = timedelta(hours=1)
        elif interval == '4h':
            delta = timedelta(hours=4)
        elif interval == '1d':
            delta = timedelta(days=1)
        else:
            delta = timedelta(hours=1)  # Default
        
        # Tạo timestamps
        timestamps = [end_time - i * delta for i in range(limit)]
        timestamps.reverse()
        
        # Tạo giá
        if symbol.startswith('BTC'):
            base_price = 60000
            volatility = 2000
        elif symbol.startswith('ETH'):
            base_price = 3000
            volatility = 100
        else:
            base_price = 100
            volatility = 5
        
        # Tạo dữ liệu giả với xu hướng
        trend = np.linspace(-0.1, 0.1, limit)  # -10% to +10%
        noise = np.random.normal(0, 0.01, limit)  # 1% noise
        
        returns = trend + noise
        cum_returns = np.cumprod(1 + returns)
        
        close_prices = base_price * cum_returns
        
        # Tính các giá khác
        daily_volatility = volatility * 0.01  # 1% của volatility
        
        open_prices = close_prices * (1 + np.random.normal(0, daily_volatility, limit))
        high_prices = np.maximum(open_prices, close_prices) * (1 + abs(np.random.normal(0, daily_volatility, limit)))
        low_prices = np.minimum(open_prices, close_prices) * (1 - abs(np.random.normal(0, daily_volatility, limit)))
        
        # Tạo volume
        base_volume = 1000
        volume = base_volume * (1 + np.random.lognormal(0, 1, limit))
        
        # Tạo DataFrame
        df = pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume
        }, index=timestamps)
        
        logger.warning(f"Đã tạo dữ liệu mẫu cho {symbol} {interval} ({limit} nến)")
        
        return df
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm các chỉ báo kỹ thuật vào DataFrame
        
        Args:
            df: DataFrame chứa dữ liệu giá
        
        Returns:
            DataFrame đã thêm chỉ báo kỹ thuật
        """
        # Tạo bản sao để tránh thay đổi DataFrame gốc
        df_copy = df.copy()
        
        try:
            # SMA - Simple Moving Average
            for period in [9, 20, 50, 200]:
                df_copy[f'sma_{period}'] = df_copy['close'].rolling(period).mean()
            
            # EMA - Exponential Moving Average
            for period in [9, 12, 26, 50, 200]:
                df_copy[f'ema_{period}'] = df_copy['close'].ewm(span=period, adjust=False).mean()
            
            # Bollinger Bands
            df_copy['bb_middle'] = df_copy['close'].rolling(20).mean()
            df_copy['bb_std'] = df_copy['close'].rolling(20).std()
            df_copy['bb_upper'] = df_copy['bb_middle'] + 2 * df_copy['bb_std']
            df_copy['bb_lower'] = df_copy['bb_middle'] - 2 * df_copy['bb_std']
            df_copy['bb_width'] = (df_copy['bb_upper'] - df_copy['bb_lower']) / df_copy['bb_middle']
            
            # RSI - Relative Strength Index
            delta = df_copy['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()
            
            rs = avg_gain / avg_loss.replace(0, 0.001)  # Tránh chia cho 0
            df_copy['rsi_14'] = 100 - (100 / (1 + rs))
            
            # MACD - Moving Average Convergence Divergence
            df_copy['ema_12'] = df_copy['close'].ewm(span=12, adjust=False).mean()
            df_copy['ema_26'] = df_copy['close'].ewm(span=26, adjust=False).mean()
            df_copy['macd'] = df_copy['ema_12'] - df_copy['ema_26']
            df_copy['macd_signal'] = df_copy['macd'].ewm(span=9, adjust=False).mean()
            df_copy['macd_hist'] = df_copy['macd'] - df_copy['macd_signal']
            
            # Stochastic Oscillator
            n = 14
            df_copy['stoch_k'] = 100 * (df_copy['close'] - df_copy['low'].rolling(n).min()) / \
                            (df_copy['high'].rolling(n).max() - df_copy['low'].rolling(n).min())
            df_copy['stoch_d'] = df_copy['stoch_k'].rolling(3).mean()
            
            # ADX - Average Directional Index
            tr1 = df_copy['high'] - df_copy['low']
            tr2 = abs(df_copy['high'] - df_copy['close'].shift())
            tr3 = abs(df_copy['low'] - df_copy['close'].shift())
            
            tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
            atr = tr.rolling(14).mean()
            
            plus_dm = df_copy['high'].diff()
            minus_dm = df_copy['low'].diff()
            plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm), 0)
            minus_dm = minus_dm.where((minus_dm > 0) & (minus_dm > plus_dm), 0)
            
            plus_di = 100 * plus_dm.rolling(14).mean() / atr
            minus_di = 100 * minus_dm.rolling(14).mean() / atr
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            df_copy['adx'] = dx.rolling(14).mean()
            
            # Đặc trưng giá và khối lượng
            df_copy['returns'] = df_copy['close'].pct_change()
            df_copy['log_returns'] = np.log(df_copy['close'] / df_copy['close'].shift(1))
            df_copy['volatility'] = df_copy['returns'].rolling(20).std()
            
            df_copy['volume_delta'] = df_copy['volume'].diff()
            df_copy['volume_sma'] = df_copy['volume'].rolling(20).mean()
            df_copy['volume_ratio'] = df_copy['volume'] / df_copy['volume_sma']
            
            logger.info(f"Đã thêm {len(df_copy.columns) - len(df.columns)} chỉ báo kỹ thuật")
        
        except Exception as e:
            logger.error(f"Lỗi khi thêm chỉ báo kỹ thuật: {str(e)}")
        
        return df_copy
    
    def split_train_test(
        self, 
        df: pd.DataFrame, 
        test_size: float = 0.2
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Chia dữ liệu thành tập huấn luyện và kiểm thử
        
        Args:
            df: DataFrame chứa dữ liệu
            test_size: Tỷ lệ dữ liệu kiểm thử
        
        Returns:
            Tuple (train_df, test_df)
        """
        train_size = int(len(df) * (1 - test_size))
        train_df = df.iloc[:train_size]
        test_df = df.iloc[train_size:]
        
        logger.info(f"Đã chia dữ liệu: train={len(train_df)}, test={len(test_df)}")
        
        return train_df, test_df
    
    def normalize_data(
        self, 
        df: pd.DataFrame, 
        columns: List[str] = None,
        method: str = 'minmax'
    ) -> pd.DataFrame:
        """
        Chuẩn hóa dữ liệu
        
        Args:
            df: DataFrame chứa dữ liệu
            columns: Danh sách cột cần chuẩn hóa, None sẽ chuẩn hóa tất cả các cột số
            method: Phương pháp chuẩn hóa ('minmax', 'zscore', 'robust')
        
        Returns:
            DataFrame đã chuẩn hóa
        """
        # Tạo bản sao để tránh thay đổi DataFrame gốc
        df_copy = df.copy()
        
        # Nếu không chỉ định cột, lấy tất cả các cột số
        if columns is None:
            columns = df.select_dtypes(include=['number']).columns.tolist()
        
        # Chuẩn hóa từng cột
        for col in columns:
            if col not in df.columns:
                continue
            
            if method == 'minmax':
                # Min-Max Scaling
                min_val = df[col].min()
                max_val = df[col].max()
                
                if max_val > min_val:
                    df_copy[col] = (df[col] - min_val) / (max_val - min_val)
                else:
                    df_copy[col] = 0.5  # Giá trị mặc định nếu min = max
            
            elif method == 'zscore':
                # Z-score Normalization
                mean = df[col].mean()
                std = df[col].std()
                
                if std > 0:
                    df_copy[col] = (df[col] - mean) / std
                else:
                    df_copy[col] = 0  # Giá trị mặc định nếu std = 0
            
            elif method == 'robust':
                # Robust Scaling
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                
                if iqr > 0:
                    df_copy[col] = (df[col] - q1) / iqr
                else:
                    df_copy[col] = 0.5  # Giá trị mặc định nếu iqr = 0
        
        logger.info(f"Đã chuẩn hóa {len(columns)} cột bằng phương pháp {method}")
        
        return df_copy
    
    def export_data(
        self, 
        df: pd.DataFrame, 
        filename: str, 
        format: str = 'csv'
    ) -> str:
        """
        Xuất dữ liệu ra file
        
        Args:
            df: DataFrame chứa dữ liệu
            filename: Tên file
            format: Định dạng file ('csv', 'json', 'xlsx')
        
        Returns:
            Đường dẫn file đã lưu
        """
        # Tạo đường dẫn đầy đủ
        filepath = os.path.join(self.data_dir, filename)
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        try:
            if format == 'csv':
                df.to_csv(filepath)
            elif format == 'json':
                df.to_json(filepath)
            elif format == 'xlsx':
                df.to_excel(filepath)
            else:
                raise ValueError(f"Định dạng không hỗ trợ: {format}")
            
            logger.info(f"Đã xuất dữ liệu ra file: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Lỗi khi xuất dữ liệu: {str(e)}")
            return ""

if __name__ == "__main__":
    # Demo
    processor = DataProcessor()
    
    # Tạo dữ liệu mẫu
    df = processor._generate_sample_data("BTCUSDT", "1h", 100)
    print(f"Dữ liệu gốc: {df.shape}")
    
    # Thêm chỉ báo kỹ thuật
    df_with_indicators = processor.add_technical_indicators(df)
    print(f"Dữ liệu với chỉ báo: {df_with_indicators.shape}")
    
    # Chia dữ liệu
    train_df, test_df = processor.split_train_test(df_with_indicators)
    print(f"Tập huấn luyện: {train_df.shape}")
    print(f"Tập kiểm thử: {test_df.shape}")
    
    # Chuẩn hóa dữ liệu
    normalized_df = processor.normalize_data(train_df)
    print(f"Dữ liệu chuẩn hóa: {normalized_df.shape}")