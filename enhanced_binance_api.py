#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module API Binance tăng cường

Module này cải thiện kết nối với Binance bằng cách:
1. Tự động chuyển đổi giữa API Testnet và API chính khi cần lấy dữ liệu lịch sử
2. Hỗ trợ tự động thử lại khi API không phản hồi hoặc bị lỗi
3. Ghi log chi tiết về quá trình lấy dữ liệu
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_binance_api.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("enhanced_binance_api")

# Import module Binance API gốc
try:
    from binance_api import BinanceAPI
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đang chạy từ thư mục gốc của dự án")
    sys.exit(1)

class EnhancedBinanceAPI:
    """Lớp API Binance tăng cường với khả năng tự động điều chỉnh giữa Testnet và API chính"""
    
    # Các URL cơ sở
    TESTNET_FUTURES_BASE_URL = "https://testnet.binancefuture.com"
    MAINNET_FUTURES_BASE_URL = "https://fapi.binance.com"
    
    # Các URL cơ sở của thị trường spot
    TESTNET_SPOT_BASE_URL = "https://testnet.binance.vision"
    MAINNET_SPOT_BASE_URL = "https://api.binance.com"
    
    def __init__(self, config_path: str = 'account_config.json', 
                 testnet: bool = True, 
                 auto_fallback: bool = True):
        """
        Khởi tạo enhanced Binance API
        
        Args:
            config_path (str): Đường dẫn tới file cấu hình
            testnet (bool): Có sử dụng Testnet không
            auto_fallback (bool): Tự động chuyển sang API chính khi API Testnet thất bại
        """
        self.config_path = config_path
        self.testnet = testnet
        self.auto_fallback = auto_fallback
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Khởi tạo Binance API gốc
        self.binance_api = BinanceAPI()
        
        # Thiết lập API key từ file cấu hình
        self.api_key = self.config.get('api_key', '')
        self.api_secret = self.config.get('api_secret', '')
        
        # Đường dẫn URL
        self._set_base_urls()
        
        # Lượt thử API và số lần thử lại
        self.retry_count = 3
        self.retry_delay_seconds = 2
        
        logger.info(f"Đã khởi tạo Enhanced Binance API (testnet={testnet}, auto_fallback={auto_fallback})")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            # Cấu hình mặc định
            return {
                "api_key": "",
                "api_secret": "",
                "api_mode": "testnet"
            }
    
    def _set_base_urls(self) -> None:
        """Thiết lập các URL cơ sở dựa trên chế độ testnet"""
        if self.testnet:
            self.futures_base_url = self.TESTNET_FUTURES_BASE_URL
            self.spot_base_url = self.TESTNET_SPOT_BASE_URL
            logger.info("Sử dụng URLs Binance Testnet")
        else:
            self.futures_base_url = self.MAINNET_FUTURES_BASE_URL
            self.spot_base_url = self.MAINNET_SPOT_BASE_URL
            logger.info("Sử dụng URLs Binance Mainnet")
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     params: Dict = None, 
                     data: Dict = None, 
                     headers: Dict = None,
                     use_mainnet: bool = False) -> Dict:
        """
        Thực hiện yêu cầu HTTP tới API Binance
        
        Args:
            method (str): Phương thức HTTP (GET, POST, DELETE)
            endpoint (str): Endpoint API
            params (Dict, optional): Tham số query string
            data (Dict, optional): Dữ liệu gửi trong body
            headers (Dict, optional): Headers
            use_mainnet (bool): Sử dụng API chính thay vì API testnet
            
        Returns:
            Dict: Dữ liệu từ API
        """
        # Xác định base URL
        base_url = self.MAINNET_FUTURES_BASE_URL if use_mainnet else self.futures_base_url
        
        # Tạo URL đầy đủ
        url = f"{base_url}{endpoint}"
        
        # Headers mặc định
        if not headers:
            headers = {}
        
        # Thêm API key vào header nếu có
        if self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key
        
        # Số lần thử lại
        retries = 0
        last_error = None
        
        while retries < self.retry_count:
            try:
                if method == 'GET':
                    response = requests.get(url, params=params, headers=headers)
                elif method == 'POST':
                    response = requests.post(url, params=params, data=data, headers=headers)
                elif method == 'DELETE':
                    response = requests.delete(url, params=params, headers=headers)
                else:
                    logger.error(f"Phương thức không được hỗ trợ: {method}")
                    return {'error': f"Phương thức không được hỗ trợ: {method}"}
                
                # Kiểm tra mã trạng thái HTTP
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"{response.status_code} {response.reason} for url: {url}"
                    logger.error(f"API request error: {error_msg}")
                    
                    # Nếu API testnet lỗi và có auto_fallback, thử dùng API chính cho đọc dữ liệu
                    if self.auto_fallback and self.testnet and not use_mainnet and method == 'GET':
                        logger.info(f"Thử sử dụng Binance Mainnet API cho {endpoint}")
                        return self._make_request(method, endpoint, params, data, headers, use_mainnet=True)
                    
                    # Lưu lỗi và thử lại
                    last_error = error_msg
                    retries += 1
                    time.sleep(self.retry_delay_seconds)
            except Exception as e:
                logger.error(f"Lỗi khi gửi yêu cầu: {str(e)}")
                last_error = str(e)
                retries += 1
                time.sleep(self.retry_delay_seconds)
        
        # Nếu tất cả các lần thử đều thất bại
        logger.error(f"Đã thử lại {self.retry_count} lần nhưng vẫn thất bại: {last_error}")
        return {'error': last_error}
    
    def get_klines(self, 
                  symbol: str, 
                  interval: str, 
                  limit: int = 1000, 
                  start_time: int = None,
                  end_time: int = None) -> List:
        """
        Lấy dữ liệu K-lines (nến) từ Binance
        
        Args:
            symbol (str): Symbol cặp giao dịch
            interval (str): Khoảng thời gian (1m, 5m, 15m, 1h, 4h, 1d)
            limit (int): Số lượng nến tối đa
            start_time (int, optional): Thời gian bắt đầu (timestamp)
            end_time (int, optional): Thời gian kết thúc (timestamp)
            
        Returns:
            List: Danh sách các nến
        """
        endpoint = "/fapi/v1/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
            
        if end_time:
            params['endTime'] = end_time
        
        logger.info(f"Lấy dữ liệu K-lines cho {symbol} (interval={interval}, limit={limit})")
        
        # Gọi API
        response = self._make_request('GET', endpoint, params=params)
        
        # Kiểm tra lỗi
        if 'error' in response:
            logger.error(f"Lỗi khi lấy K-lines: {response['error']}")
            return []
        
        # Kiểm tra xem có phải list không
        if not isinstance(response, list):
            logger.error(f"Định dạng phản hồi không đúng: {response}")
            return []
        
        logger.info(f"Đã lấy {len(response)} K-lines cho {symbol} (interval={interval})")
        return response
    
    def get_historical_data(self, 
                           symbol: str, 
                           interval: str, 
                           days_back: int = 30) -> List:
        """
        Lấy dữ liệu lịch sử theo số ngày
        
        Args:
            symbol (str): Symbol cặp giao dịch
            interval (str): Khoảng thời gian (1m, 5m, 15m, 1h, 4h, 1d)
            days_back (int): Số ngày dữ liệu lấy ngược về quá khứ
            
        Returns:
            List: Danh sách các nến
        """
        # Tính timestamp
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
        
        # Tính toán số lượng nến tối đa dựa trên khoảng thời gian
        max_candles = self._calculate_max_candles(interval, days_back)
        
        logger.info(f"Lấy dữ liệu lịch sử {days_back} ngày cho {symbol} (interval={interval})")
        
        # Lấy dữ liệu
        klines = self.get_klines(
            symbol=symbol,
            interval=interval,
            limit=max_candles,
            start_time=start_time,
            end_time=end_time
        )
        
        return klines
    
    def _calculate_max_candles(self, interval: str, days: int) -> int:
        """
        Tính toán số lượng nến tối đa dựa trên khoảng thời gian và số ngày
        
        Args:
            interval (str): Khoảng thời gian (1m, 5m, 15m, 1h, 4h, 1d)
            days (int): Số ngày
            
        Returns:
            int: Số lượng nến tối đa
        """
        minutes_in_day = 24 * 60
        
        # Chuyển đổi khoảng thời gian thành phút
        if interval == '1m':
            interval_minutes = 1
        elif interval == '5m':
            interval_minutes = 5
        elif interval == '15m':
            interval_minutes = 15
        elif interval == '1h':
            interval_minutes = 60
        elif interval == '4h':
            interval_minutes = 240
        elif interval == '1d':
            interval_minutes = 1440
        else:
            logger.warning(f"Khoảng thời gian không được hỗ trợ: {interval}, sử dụng 1h")
            interval_minutes = 60
        
        # Tính toán số lượng nến
        return int(days * minutes_in_day / interval_minutes)
    
    def get_ticker_price(self, symbol: str) -> float:
        """
        Lấy giá hiện tại của một cặp giao dịch
        
        Args:
            symbol (str): Symbol cặp giao dịch
            
        Returns:
            float: Giá hiện tại
        """
        endpoint = "/fapi/v1/ticker/price"
        params = {'symbol': symbol}
        
        logger.info(f"Lấy giá hiện tại cho {symbol}")
        
        # Gọi API
        response = self._make_request('GET', endpoint, params=params)
        
        # Kiểm tra lỗi
        if 'error' in response:
            logger.error(f"Lỗi khi lấy giá hiện tại: {response['error']}")
            return 0.0
        
        # Trả về giá
        if 'price' in response:
            price = float(response['price'])
            logger.info(f"Giá hiện tại của {symbol}: {price}")
            return price
        else:
            logger.error(f"Không tìm thấy giá trong phản hồi: {response}")
            return 0.0
    
    def get_all_tickers(self) -> Dict[str, float]:
        """
        Lấy giá hiện tại của tất cả các cặp giao dịch
        
        Returns:
            Dict[str, float]: Dictionary với key là symbol và value là giá
        """
        endpoint = "/fapi/v1/ticker/price"
        
        logger.info("Lấy giá hiện tại cho tất cả các cặp giao dịch")
        
        # Gọi API
        response = self._make_request('GET', endpoint)
        
        # Kiểm tra lỗi
        if 'error' in response:
            logger.error(f"Lỗi khi lấy tất cả giá: {response['error']}")
            return {}
        
        # Kiểm tra xem có phải list không
        if not isinstance(response, list):
            logger.error(f"Định dạng phản hồi không đúng: {response}")
            return {}
        
        # Chuyển đổi thành dictionary
        tickers = {}
        for item in response:
            if 'symbol' in item and 'price' in item:
                tickers[item['symbol']] = float(item['price'])
        
        logger.info(f"Đã lấy giá cho {len(tickers)} cặp giao dịch")
        return tickers
    
    def get_open_positions(self) -> List[Dict]:
        """
        Lấy danh sách các vị thế đang mở
        
        Returns:
            List[Dict]: Danh sách các vị thế mở
        """
        # Sử dụng API gốc vì cần ký request
        logger.info("Lấy danh sách vị thế đang mở")
        
        # Delegate to original BinanceAPI
        try:
            positions = self.binance_api.get_positions()
            logger.info(f"Đã lấy {len(positions)} vị thế đang mở")
            return positions
        except Exception as e:
            logger.error(f"Lỗi khi lấy vị thế: {str(e)}")
            return []
    
    def get_account_balance(self) -> Dict:
        """
        Lấy thông tin số dư tài khoản
        
        Returns:
            Dict: Thông tin số dư
        """
        # Sử dụng API gốc vì cần ký request
        logger.info("Lấy thông tin số dư tài khoản")
        
        # Delegate to original BinanceAPI
        try:
            balance = self.binance_api.get_account_balance()
            logger.info(f"Đã lấy thông tin số dư tài khoản")
            return balance
        except Exception as e:
            logger.error(f"Lỗi khi lấy số dư tài khoản: {str(e)}")
            return {}


# Hàm chính để kiểm thử
def main():
    """Hàm kiểm thử Enhanced Binance API"""
    try:
        # Khởi tạo Enhanced Binance API
        api = EnhancedBinanceAPI(testnet=True, auto_fallback=True)
        
        # Lấy giá hiện tại
        btc_price = api.get_ticker_price("BTCUSDT")
        print(f"Giá Bitcoin hiện tại: {btc_price}")
        
        # Lấy dữ liệu lịch sử
        btc_history = api.get_historical_data("BTCUSDT", "1h", days_back=7)
        print(f"Số lượng nến Bitcoin (1h, 7 ngày): {len(btc_history)}")
        
        # Lấy tất cả giá
        all_tickers = api.get_all_tickers()
        print(f"Số lượng cặp giao dịch: {len(all_tickers)}")
        
        # Lấy danh sách vị thế mở
        positions = api.get_open_positions()
        print(f"Số lượng vị thế mở: {len(positions)}")
        
        # Lấy thông tin số dư
        balance = api.get_account_balance()
        print(f"Số dư tài khoản: {balance}")
        
        return 0
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())