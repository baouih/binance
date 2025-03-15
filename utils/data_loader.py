import os
import logging
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Xử lý import Binance API một cách an toàn
try:
    from binance.spot import Spot
    from binance.cm_futures import CMFutures
    from binance.um_futures import UMFutures
    binance_api_available = True
except ImportError:
    binance_api_available = False
    print("Thông báo: binance-futures-connector chưa được cài đặt hoặc không khả dụng. Sẽ sử dụng dữ liệu từ file cục bộ.")
from pathlib import Path

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Lớp tải dữ liệu lịch sử giao dịch từ Binance hoặc từ tệp cục bộ
    """
    
    def __init__(self, data_dir='./data'):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            os.makedirs(self.data_dir)
        
        # Thiết lập API keys từ environment variables 
        self.api_key = os.environ.get('BINANCE_API_KEY')
        self.api_secret = os.environ.get('BINANCE_API_SECRET')
    
    def load_historical_data(self, symbol, interval, start_str=None, end_str=None, limit=1000, testnet=False, use_cached=True):
        """
        Tải dữ liệu lịch sử từ Binance hoặc từ cache
        
        Args:
            symbol (str): Cặp tiền, ví dụ 'BTCUSDT'
            interval (str): Khung thời gian, ví dụ '1h', '4h', '1d'
            start_str (str, optional): Thời gian bắt đầu, ví dụ '2023-01-01'
            end_str (str, optional): Thời gian kết thúc, ví dụ '2023-12-31'
            limit (int, optional): Số lượng nến tối đa
            testnet (bool, optional): Sử dụng testnet hay không
            use_cached (bool, optional): Sử dụng dữ liệu cache nếu có
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu lịch sử
        """
        # Kiểm tra xem có dữ liệu cache phù hợp không
        cache_file = self._get_cache_path(symbol, interval, start_str, end_str)
        
        if use_cached and cache_file.exists():
            logger.info(f"Đang tải dữ liệu từ cache: {cache_file}")
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        # Nếu không có cache hoặc không sử dụng cache, tải từ Binance
        try:
            # Chuyển đổi chuỗi thời gian thành timestamp (ms)
            start_time = int(datetime.strptime(start_str, '%Y-%m-%d').timestamp() * 1000) if start_str else None
            end_time = int(datetime.strptime(end_str, '%Y-%m-%d').timestamp() * 1000) if end_str else None
            
            # Kết nối đến Binance API
            if testnet:
                client = UMFutures(key=self.api_key, secret=self.api_secret, base_url="https://testnet.binancefuture.com")
            else:
                client = UMFutures(key=self.api_key, secret=self.api_secret)
            
            logger.info(f"Đang tải dữ liệu {symbol} {interval} từ Binance")
            
            # Tải dữ liệu
            klines = client.klines(
                symbol=symbol,
                interval=interval,
                startTime=start_time,
                endTime=end_time,
                limit=limit
            )
            
            # Chuyển đổi thành DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Chuyển đổi cột giá trị thành kiểu số
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            
            # Lưu vào cache
            self._save_to_cache(df, symbol, interval, start_str, end_str)
            
            logger.info(f"Đã tải {len(df)} nến cho {symbol} {interval}")
            return df
        
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu từ Binance: {str(e)}")
            
            # Nếu lỗi và có dữ liệu mẫu, thử tải dữ liệu mẫu
            sample_data = self._load_sample_data(symbol, interval)
            if sample_data is not None:
                logger.info(f"Sử dụng dữ liệu mẫu cho {symbol} {interval}")
                return sample_data
            
            return None
    
    def _get_cache_path(self, symbol, interval, start_str, end_str):
        """
        Tạo đường dẫn file cache dựa vào thông tin dữ liệu
        """
        start_str = start_str or 'earliest'
        end_str = end_str or 'latest'
        return self.data_dir / f"{symbol}_{interval}_{start_str}_{end_str}.csv"
    
    def _save_to_cache(self, df, symbol, interval, start_str, end_str):
        """
        Lưu DataFrame vào file cache
        """
        cache_file = self._get_cache_path(symbol, interval, start_str, end_str)
        df.to_csv(cache_file)
        logger.info(f"Đã lưu dữ liệu vào cache: {cache_file}")
    
    def _load_sample_data(self, symbol, interval):
        """
        Tạo dữ liệu mẫu để kiểm thử (chỉ sử dụng khi không tải được dữ liệu thật)
        """
        # Báo cáo lập tức và thoát - chúng ta không sử dụng dữ liệu mẫu
        logger.error("Không thể tải dữ liệu thực và không sử dụng dữ liệu mẫu.")
        return None
    
    def generate_test_data(self, symbol, interval='1h', days=90, volatility=0.02, trend=0.001):
        """
        Tạo dữ liệu giả lập cho việc kiểm thử và phát triển
        (Chỉ nên dùng khi không có dữ liệu thật)
        
        Args:
            symbol (str): Cặp tiền
            interval (str): Khung thời gian
            days (int): Số ngày dữ liệu
            volatility (float): Độ biến động
            trend (float): Xu hướng trung bình (dương là xu hướng tăng)
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu giả lập
        """
        # Báo cáo lập tức và thoát - chúng ta không sử dụng dữ liệu giả lập
        logger.error("Không được phép tạo dữ liệu giả lập trong môi trường sản xuất.")
        return None