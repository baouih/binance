#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module tải và lưu trữ dữ liệu lịch sử từ Binance cho ML
"""

import os
import sys
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
from typing import Dict, List, Optional, Union, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_downloader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('data_downloader')

# Thêm thư mục gốc vào sys.path để import các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app.binance_api import BinanceAPI
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")
    # Sử dụng một bản sao của BinanceAPI nếu cần thiết
    from binance.client import Client
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    import time
    import json
    import os
    
    class BinanceAPI:
        """
        Phiên bản đơn giản của BinanceAPI để tải dữ liệu
        """
        
        def __init__(self, simulation_mode=False):
            """
            Khởi tạo API với các tham số mặc định
            """
            try:
                # Tìm các biến môi trường
                api_key = os.environ.get('BINANCE_API_KEY', '')
                api_secret = os.environ.get('BINANCE_API_SECRET', '')
                testnet = os.environ.get('BINANCE_TESTNET', 'True').lower() == 'true'
                
                # Khởi tạo client
                self.client = Client(api_key, api_secret, testnet=testnet)
                logger.info(f"Đã khởi tạo Binance API client, testnet={testnet}")
                
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo BinanceAPI: {str(e)}")
        
        def get_historical_klines(self, symbol, interval, start_str, end_str=None):
            """
            Lấy dữ liệu lịch sử từ Binance API
            """
            try:
                klines = self.client.get_historical_klines(
                    symbol, interval, start_str, end_str
                )
                
                return klines
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu lịch sử: {str(e)}")
                return []
        
        def process_historical_klines(self, klines):
            """
            Xử lý dữ liệu nến lịch sử
            """
            processed_data = []
            
            for kline in klines:
                processed_kline = {
                    'open_time': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'close_time': kline[6],
                    'quote_asset_volume': float(kline[7]),
                    'number_of_trades': int(kline[8]),
                    'taker_buy_base_asset_volume': float(kline[9]),
                    'taker_buy_quote_asset_volume': float(kline[10])
                }
                processed_data.append(processed_kline)
            
            # Chuyển đổi thành DataFrame
            if processed_data:
                df = pd.DataFrame(processed_data)
                df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
                df.set_index('datetime', inplace=True)
                return df
            else:
                return pd.DataFrame()

class DataDownloader:
    """
    Lớp tải và lưu trữ dữ liệu lịch sử từ Binance
    """
    
    def __init__(self, use_testnet=True):
        """
        Khởi tạo downloader
        
        Args:
            use_testnet: Sử dụng testnet hay không
        """
        try:
            # Thử sử dụng BinanceAPI nếu có
            from app.binance_api import BinanceAPI
            self.api = BinanceAPI(simulation_mode=False)
            logger.info("Sử dụng BinanceAPI từ app")
            
            # Khởi tạo client Binance trực tiếp
            import os
            from binance.client import Client
            
            # Tìm các biến môi trường
            api_key = os.environ.get('BINANCE_API_KEY', '')
            api_secret = os.environ.get('BINANCE_API_SECRET', '')
            
            if use_testnet:
                api_key = os.environ.get('BINANCE_TESTNET_API_KEY', '')
                api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET', '')
            
            self.client = Client(api_key, api_secret, testnet=use_testnet)
            logger.info(f"Đã khởi tạo Binance Client, testnet={use_testnet}")
            
        except ImportError:
            # Khởi tạo client Binance trực tiếp
            import os
            from binance.client import Client
            
            # Tìm các biến môi trường
            api_key = os.environ.get('BINANCE_API_KEY', '')
            api_secret = os.environ.get('BINANCE_API_SECRET', '')
            
            if use_testnet:
                api_key = os.environ.get('BINANCE_TESTNET_API_KEY', '')
                api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET', '')
            
            self.client = Client(api_key, api_secret, testnet=use_testnet)
            logger.info(f"Đã khởi tạo Binance Client, testnet={use_testnet}")
            
        self.data_dir = "real_data"
        
        # Tạo thư mục lưu trữ nếu chưa tồn tại
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Danh sách khung thời gian được hỗ trợ
        self.supported_intervals = {
            "1m": {"binance": "1m", "minutes": 1},
            "5m": {"binance": "5m", "minutes": 5},
            "15m": {"binance": "15m", "minutes": 15},
            "30m": {"binance": "30m", "minutes": 30},
            "1h": {"binance": "1h", "minutes": 60},
            "2h": {"binance": "2h", "minutes": 120},
            "4h": {"binance": "4h", "minutes": 240},
            "6h": {"binance": "6h", "minutes": 360},
            "8h": {"binance": "8h", "minutes": 480},
            "12h": {"binance": "12h", "minutes": 720},
            "1d": {"binance": "1d", "minutes": 1440},
            "3d": {"binance": "3d", "minutes": 4320},
            "1w": {"binance": "1w", "minutes": 10080},
            "1M": {"binance": "1M", "minutes": 43200}
        }
        
        logger.info(f"Khởi tạo DataDownloader, testnet={use_testnet}")
    
    def download_historical_data(self, symbol: str, interval: str, 
                               lookback_days: int = 90,
                               end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        Tải dữ liệu lịch sử từ Binance
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            lookback_days: Số ngày lịch sử
            end_date: Ngày kết thúc (mặc định: hiện tại)
            
        Returns:
            DataFrame chứa dữ liệu lịch sử hoặc None nếu thất bại
        """
        try:
            # Kiểm tra khung thời gian
            if interval not in self.supported_intervals:
                logger.error(f"Khung thời gian không hợp lệ: {interval}")
                return None
            
            # Chuẩn bị tham số
            if end_date is None:
                end_date = datetime.now()
                
            start_date = end_date - timedelta(days=lookback_days)
            
            # Chuyển đổi định dạng timestamp cho Binance
            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
            # Chuyển đổi định dạng ngày (cho log)
            start_str = start_date.strftime("%d %b, %Y")
            end_str = end_date.strftime("%d %b, %Y")
            
            logger.info(f"Tải dữ liệu lịch sử cho {symbol} {interval} từ {start_str} đến {end_str}")
            
            # Tải dữ liệu sử dụng Binance Client
            binance_interval = self.supported_intervals[interval]["binance"]
            
            # Sử dụng client binance để tải dữ liệu
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=binance_interval,
                startTime=start_timestamp,
                endTime=end_timestamp,
                limit=1000
            )
            
            if not klines:
                logger.error(f"Không thể tải dữ liệu cho {symbol} {interval}")
                return None
            
            # Xử lý dữ liệu sang DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # Đặt timestamp làm index
            df.set_index('timestamp', inplace=True)
            
            # Sắp xếp dữ liệu theo thời gian tăng dần
            df.sort_index(inplace=True)
            
            if df.empty:
                logger.error(f"Dữ liệu trống cho {symbol} {interval}")
                return None
            
            logger.info(f"Đã tải {len(df)} nến cho {symbol} {interval}")
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu lịch sử: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def save_historical_data(self, df: pd.DataFrame, symbol: str, interval: str) -> str:
        """
        Lưu dữ liệu lịch sử vào file
        
        Args:
            df: DataFrame chứa dữ liệu
            symbol: Mã tiền
            interval: Khung thời gian
            
        Returns:
            Đường dẫn đến file đã lưu hoặc chuỗi rỗng nếu thất bại
        """
        try:
            if df is None or df.empty:
                logger.error(f"Không có dữ liệu để lưu cho {symbol} {interval}")
                return ""
            
            # Chuẩn bị tên file
            filename = f"{symbol}_{interval}_historical_data.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            # Lưu dữ liệu
            df.to_csv(filepath)
            
            logger.info(f"Đã lưu dữ liệu lịch sử {symbol} {interval} vào {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu lịch sử: {str(e)}")
            return ""
    
    def load_historical_data(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """
        Tải dữ liệu lịch sử từ file
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            
        Returns:
            DataFrame chứa dữ liệu lịch sử hoặc None nếu thất bại
        """
        try:
            # Chuẩn bị tên file
            filename = f"{symbol}_{interval}_historical_data.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            # Kiểm tra file tồn tại
            if not os.path.exists(filepath):
                logger.error(f"Không tìm thấy file dữ liệu {filepath}")
                return None
            
            # Tải dữ liệu
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            
            if df.empty:
                logger.error(f"Dữ liệu trống trong file {filepath}")
                return None
            
            logger.info(f"Đã tải {len(df)} nến từ {filepath}")
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu lịch sử từ file: {str(e)}")
            return None
    
    def get_historical_data(self, symbol: str, interval: str, 
                         lookback_days: int = 90,
                         force_download: bool = False) -> Optional[pd.DataFrame]:
        """
        Lấy dữ liệu lịch sử (từ file nếu có, nếu không thì tải mới)
        
        Args:
            symbol: Mã tiền
            interval: Khung thời gian
            lookback_days: Số ngày lịch sử
            force_download: Bắt buộc tải lại dữ liệu
            
        Returns:
            DataFrame chứa dữ liệu lịch sử hoặc None nếu thất bại
        """
        # Chuẩn bị tên file
        filename = f"{symbol}_{interval}_historical_data.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        # Kiểm tra xem có nên tải lại dữ liệu không
        should_download = force_download or not os.path.exists(filepath)
        
        if not should_download:
            # Kiểm tra thời gian cập nhật của file
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            now = datetime.now()
            
            # Nếu file quá cũ, tải lại
            if (now - file_time).total_seconds() > 86400:  # 24 giờ
                should_download = True
        
        if should_download:
            # Tải và lưu dữ liệu mới
            df = self.download_historical_data(symbol, interval, lookback_days)
            if df is not None:
                self.save_historical_data(df, symbol, interval)
                return df
            else:
                # Nếu tải thất bại nhưng file tồn tại, sử dụng file
                if os.path.exists(filepath):
                    logger.warning(f"Tải dữ liệu thất bại, sử dụng dữ liệu từ file {filepath}")
                    return self.load_historical_data(symbol, interval)
                else:
                    return None
        else:
            # Sử dụng dữ liệu từ file
            return self.load_historical_data(symbol, interval)
    
    def download_all_data(self, symbols: List[str], intervals: List[str], 
                       lookback_days: int = 90) -> Dict[str, Dict[str, str]]:
        """
        Tải dữ liệu cho nhiều coin và khung thời gian
        
        Args:
            symbols: Danh sách coin
            intervals: Danh sách khung thời gian
            lookback_days: Số ngày lịch sử
            
        Returns:
            Dict chứa kết quả tải dữ liệu
        """
        results = {}
        
        for symbol in symbols:
            symbol_results = {}
            
            for interval in intervals:
                try:
                    logger.info(f"Tải dữ liệu cho {symbol} {interval}")
                    
                    df = self.download_historical_data(symbol, interval, lookback_days)
                    
                    if df is not None:
                        filepath = self.save_historical_data(df, symbol, interval)
                        symbol_results[interval] = filepath
                    else:
                        symbol_results[interval] = ""
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tải dữ liệu cho {symbol} {interval}: {str(e)}")
                    symbol_results[interval] = "error"
            
            results[symbol] = symbol_results
        
        return results

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Tải dữ liệu lịch sử từ Binance')
    parser.add_argument('--symbols', type=str, nargs='+', 
                      default=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"],
                      help='Danh sách coin (mặc định: BTC, ETH, BNB, SOL, ADA)')
    parser.add_argument('--intervals', type=str, nargs='+', 
                      default=["1h", "4h"],
                      help='Danh sách khung thời gian (mặc định: 1h, 4h)')
    parser.add_argument('--lookback', type=int, default=90, 
                      help='Số ngày lịch sử (mặc định: 90)')
    parser.add_argument('--force', action='store_true', 
                      help='Bắt buộc tải lại dữ liệu (mặc định: False)')
    
    args = parser.parse_args()
    
    downloader = DataDownloader()
    
    if args.force:
        results = downloader.download_all_data(args.symbols, args.intervals, args.lookback)
    else:
        results = {}
        for symbol in args.symbols:
            symbol_results = {}
            
            for interval in args.intervals:
                df = downloader.get_historical_data(
                    symbol, interval, args.lookback, args.force
                )
                
                if df is not None:
                    filepath = os.path.join(
                        downloader.data_dir, 
                        f"{symbol}_{interval}_historical_data.csv"
                    )
                    symbol_results[interval] = filepath
                else:
                    symbol_results[interval] = ""
            
            results[symbol] = symbol_results
    
    # In kết quả
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()