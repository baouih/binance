#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Binance API
------------------
Module cung cấp lớp truy cập đến Binance API với các tính năng mở rộng,
hỗ trợ cho cả Spot và Futures, đồng thời tương thích với testnet.
"""

import os
import json
import time
import logging
import hashlib
import hmac
import urllib.parse
import requests
from typing import Dict, List, Union, Optional, Any
from datetime import datetime, timedelta

# Thử import Binance Client
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException, BinanceRequestException
    BINANCE_PYTHON_IMPORTED = True
except ImportError:
    BINANCE_PYTHON_IMPORTED = False

# Thiết lập logging
logger = logging.getLogger("enhanced_binance_api")

class EnhancedBinanceAPI:
    """
    Lớp cung cấp các chức năng để tương tác với Binance API
    Hỗ trợ cả Spot và Futures với khả năng sử dụng testnet
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = False):
        """
        Khởi tạo Binance API client
        
        Args:
            api_key: API key (nếu None, sẽ lấy từ biến môi trường BINANCE_API_KEY hoặc BINANCE_TESTNET_API_KEY)
            api_secret: API secret (nếu None, sẽ lấy từ biến môi trường BINANCE_API_SECRET hoặc BINANCE_TESTNET_API_SECRET)
            testnet: True nếu sử dụng testnet, False nếu sử dụng mainnet
        """
        self.testnet = testnet
        self.client = None
        self.spot_client = None
        self.futures_client = None
        
        # Các URL base cho các API
        self.spot_api_url = "https://api.binance.com"
        self.futures_api_url = "https://fapi.binance.com"
        self.spot_testnet_url = "https://testnet.binance.vision"
        self.futures_testnet_url = "https://testnet.binancefuture.com"
        
        # Tải các API key và secret
        api_key, api_secret = self._load_api_credentials(api_key, api_secret)
        
        # Khởi tạo client
        self._init_client(api_key, api_secret)
    
    def _load_api_credentials(self, api_key: Optional[str], api_secret: Optional[str]) -> tuple:
        """
        Tải API key và secret từ biến môi trường hoặc file config
        
        Args:
            api_key: API key từ tham số
            api_secret: API secret từ tham số
            
        Returns:
            tuple: (api_key, api_secret)
        """
        # Nếu đã cung cấp key và secret từ tham số, sử dụng chúng
        if api_key and api_secret:
            return api_key, api_secret
        
        # Thử đọc từ biến môi trường
        if self.testnet:
            env_api_key = os.environ.get('BINANCE_TESTNET_API_KEY')
            env_api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET')
        else:
            env_api_key = os.environ.get('BINANCE_API_KEY')
            env_api_secret = os.environ.get('BINANCE_API_SECRET')
        
        if env_api_key and env_api_secret:
            logger.info("Đã tìm thấy API key và secret trong biến môi trường")
            return env_api_key, env_api_secret
        
        # Thử đọc từ file account_config.json
        config_files = ['account_config.json', 'config.json', 'configs/account_config.json']
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    if self.testnet:
                        config_api_key = config.get('binance_testnet_api_key') or config.get('testnet_api_key')
                        config_api_secret = config.get('binance_testnet_api_secret') or config.get('testnet_api_secret')
                    else:
                        config_api_key = config.get('binance_api_key') or config.get('api_key')
                        config_api_secret = config.get('binance_api_secret') or config.get('api_secret')
                    
                    if config_api_key and config_api_secret:
                        logger.info(f"Đã tìm thấy API key và secret trong file {config_file}")
                        return config_api_key, config_api_secret
                
                except Exception as e:
                    logger.warning(f"Lỗi khi đọc file {config_file}: {e}")
        
        # Nếu không tìm thấy, trả về None và sử dụng API public
        logger.warning("Không tìm thấy API key và secret. Sử dụng API public.")
        return None, None
    
    def _init_client(self, api_key: Optional[str], api_secret: Optional[str]):
        """
        Khởi tạo client
        
        Args:
            api_key: API key
            api_secret: API secret
        """
        try:
            # Sử dụng python-binance nếu đã import thành công
            if BINANCE_PYTHON_IMPORTED:
                if self.testnet:
                    self.client = Client(
                        api_key=api_key,
                        api_secret=api_secret,
                        testnet=True
                    )
                    
                    self.spot_client = Client(
                        api_key=api_key,
                        api_secret=api_secret,
                        testnet=True
                    )
                    
                    self.futures_client = Client(
                        api_key=api_key,
                        api_secret=api_secret,
                        testnet=True
                    )
                    
                    logger.info("Đã khởi tạo Binance TestNet Client")
                else:
                    self.client = Client(
                        api_key=api_key,
                        api_secret=api_secret
                    )
                    
                    self.spot_client = Client(
                        api_key=api_key,
                        api_secret=api_secret
                    )
                    
                    self.futures_client = Client(
                        api_key=api_key,
                        api_secret=api_secret
                    )
                    
                    logger.info("Đã khởi tạo Binance MainNet Client")
            else:
                # Nếu không import được python-binance, sử dụng requests trực tiếp
                logger.warning("Không tìm thấy module python-binance. Sử dụng requests trực tiếp.")
                self.api_key = api_key
                self.api_secret = api_secret
        
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"Lỗi khi khởi tạo Binance Client: {e}")
        except Exception as e:
            logger.error(f"Lỗi không xác định khi khởi tạo Binance Client: {e}")
    
    def test_connection(self) -> bool:
        """
        Kiểm tra kết nối đến Binance API
        
        Returns:
            bool: True nếu kết nối thành công, False nếu không
        """
        try:
            if self.client:
                # Sử dụng python-binance nếu đã import thành công
                if self.testnet:
                    # Kiểm tra kết nối futures testnet
                    self.client.futures_ping()
                    logger.info("Kết nối đến Binance Futures TestNet thành công")
                else:
                    # Kiểm tra kết nối spot mainnet
                    self.client.ping()
                    logger.info("Kết nối đến Binance Spot MainNet thành công")
                
                # Lấy thời gian server
                server_time = self.client.get_server_time()
                server_time_dt = datetime.fromtimestamp(server_time['serverTime'] / 1000)
                logger.info(f"Thời gian máy chủ Binance: {server_time_dt}")
                
                return True
            else:
                # Sử dụng requests trực tiếp
                if self.testnet:
                    url = f"{self.futures_testnet_url}/fapi/v1/ping"
                else:
                    url = f"{self.spot_api_url}/api/v3/ping"
                
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    logger.info("Kết nối đến Binance API thành công")
                    return True
                else:
                    logger.error(f"Kết nối đến Binance API thất bại: {response.text}")
                    return False
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra kết nối đến Binance API: {e}")
            return False
    
    def _get_account_info(self) -> Dict:
        """
        Lấy thông tin tài khoản
        
        Returns:
            Dict: Thông tin tài khoản
        """
        try:
            if self.client:
                if self.testnet:
                    return self.client.futures_account()
                else:
                    return self.client.get_account()
            else:
                # TODO: Implement using requests
                if self.testnet:
                    url = f"{self.futures_testnet_url}/fapi/v2/account"
                else:
                    url = f"{self.spot_api_url}/api/v3/account"
                
                # Thêm mã xác thực nếu có
                if self.api_key and self.api_secret:
                    timestamp = int(time.time() * 1000)
                    params = {
                        'timestamp': timestamp
                    }
                    
                    query_string = urllib.parse.urlencode(params)
                    signature = hmac.new(
                        self.api_secret.encode('utf-8'),
                        query_string.encode('utf-8'),
                        hashlib.sha256
                    ).hexdigest()
                    
                    params['signature'] = signature
                    
                    headers = {
                        'X-MBX-APIKEY': self.api_key
                    }
                    
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        logger.error(f"Lỗi khi lấy thông tin tài khoản: {response.text}")
                        return {}
                else:
                    logger.warning("Không có API key và secret để lấy thông tin tài khoản")
                    return {}
        
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin tài khoản: {e}")
            return {}
    
    def get_account_balance(self) -> Dict[str, float]:
        """
        Lấy số dư tài khoản
        
        Returns:
            Dict[str, float]: Số dư tài khoản
        """
        try:
            if self.testnet:
                # Lấy số dư của tài khoản futures testnet
                account_info = self._get_account_info()
                
                if 'assets' in account_info:
                    balances = {}
                    for asset in account_info['assets']:
                        symbol = asset.get('asset', '')
                        balance = float(asset.get('walletBalance', 0))
                        if balance > 0:
                            balances[symbol] = balance
                    
                    return balances
                else:
                    logger.warning("Không tìm thấy thông tin số dư tài khoản futures")
                    return {}
            else:
                # Lấy số dư của tài khoản spot mainnet
                account_info = self._get_account_info()
                
                if 'balances' in account_info:
                    balances = {}
                    for balance in account_info['balances']:
                        symbol = balance.get('asset', '')
                        free = float(balance.get('free', 0))
                        locked = float(balance.get('locked', 0))
                        total = free + locked
                        if total > 0:
                            balances[symbol] = total
                    
                    return balances
                else:
                    logger.warning("Không tìm thấy thông tin số dư tài khoản spot")
                    return {}
        
        except Exception as e:
            logger.error(f"Lỗi khi lấy số dư tài khoản: {e}")
            return {}
    
    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """
        Lấy giá hiện tại của một symbol
        
        Args:
            symbol: Symbol cần lấy giá (ví dụ: BTCUSDT)
            
        Returns:
            Optional[float]: Giá hiện tại hoặc None nếu không lấy được
        """
        try:
            if self.client:
                if self.testnet:
                    # Sử dụng futures API cho testnet
                    ticker = self.client.futures_symbol_ticker(symbol=symbol)
                    if 'price' in ticker:
                        return float(ticker['price'])
                else:
                    # Sử dụng spot API cho mainnet
                    ticker = self.client.get_symbol_ticker(symbol=symbol)
                    if 'price' in ticker:
                        return float(ticker['price'])
            else:
                # Sử dụng requests trực tiếp
                if self.testnet:
                    url = f"{self.futures_testnet_url}/fapi/v1/ticker/price"
                else:
                    url = f"{self.spot_api_url}/api/v3/ticker/price"
                
                params = {
                    'symbol': symbol
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'price' in data:
                        return float(data['price'])
            
            logger.warning(f"Không lấy được giá của {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá của {symbol}: {e}")
            return None
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500, start_time: int = None, end_time: int = None) -> Optional[List]:
        """
        Lấy dữ liệu K-lines (biểu đồ nến)
        
        Args:
            symbol: Symbol cần lấy dữ liệu (ví dụ: BTCUSDT)
            interval: Khoảng thời gian (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            limit: Số lượng nến cần lấy (tối đa 1000)
            start_time: Thời gian bắt đầu (milliseconds)
            end_time: Thời gian kết thúc (milliseconds)
            
        Returns:
            Optional[List]: Dữ liệu K-lines hoặc None nếu không lấy được
        """
        try:
            if self.client:
                if self.testnet:
                    # Sử dụng futures API cho testnet
                    klines = self.client.futures_klines(
                        symbol=symbol,
                        interval=interval,
                        limit=limit,
                        startTime=start_time,
                        endTime=end_time
                    )
                    return klines
                else:
                    # Sử dụng spot API cho mainnet
                    klines = self.client.get_klines(
                        symbol=symbol,
                        interval=interval,
                        limit=limit,
                        startTime=start_time,
                        endTime=end_time
                    )
                    return klines
            else:
                # Sử dụng requests trực tiếp
                if self.testnet:
                    url = f"{self.futures_testnet_url}/fapi/v1/klines"
                else:
                    url = f"{self.spot_api_url}/api/v3/klines"
                
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
                
                if start_time:
                    params['startTime'] = start_time
                
                if end_time:
                    params['endTime'] = end_time
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    return response.json()
            
            logger.warning(f"Không lấy được dữ liệu K-lines cho {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu K-lines cho {symbol}: {e}")
            return None
    
    def get_24h_ticker(self, symbol: str = None) -> Union[Dict, List[Dict], None]:
        """
        Lấy thông tin ticker 24h
        
        Args:
            symbol: Symbol cần lấy thông tin (ví dụ: BTCUSDT), nếu None sẽ lấy tất cả
            
        Returns:
            Union[Dict, List[Dict], None]: Thông tin ticker 24h hoặc None nếu không lấy được
        """
        try:
            if self.client:
                if self.testnet:
                    # Sử dụng futures API cho testnet
                    if symbol:
                        ticker = self.client.futures_ticker(symbol=symbol)
                        return ticker
                    else:
                        tickers = self.client.futures_ticker()
                        return tickers
                else:
                    # Sử dụng spot API cho mainnet
                    if symbol:
                        ticker = self.client.get_ticker(symbol=symbol)
                        return ticker
                    else:
                        tickers = self.client.get_ticker()
                        return tickers
            else:
                # Sử dụng requests trực tiếp
                if self.testnet:
                    url = f"{self.futures_testnet_url}/fapi/v1/ticker/24hr"
                else:
                    url = f"{self.spot_api_url}/api/v3/ticker/24hr"
                
                params = {}
                if symbol:
                    params['symbol'] = symbol
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    return response.json()
            
            logger.warning(f"Không lấy được thông tin ticker 24h cho {symbol if symbol else 'tất cả'}")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin ticker 24h: {e}")
            return None
    
    def get_exchange_info(self, symbol: str = None) -> Dict:
        """
        Lấy thông tin của sàn
        
        Args:
            symbol: Symbol cần lấy thông tin (ví dụ: BTCUSDT), nếu None sẽ lấy tất cả
            
        Returns:
            Dict: Thông tin của sàn
        """
        try:
            if self.client:
                if self.testnet:
                    # Sử dụng futures API cho testnet
                    if symbol:
                        exchange_info = self.client.futures_exchange_info()
                        # Lọc thông tin cho symbol cụ thể
                        for s in exchange_info.get('symbols', []):
                            if s.get('symbol') == symbol:
                                return s
                        return {}
                    else:
                        return self.client.futures_exchange_info()
                else:
                    # Sử dụng spot API cho mainnet
                    if symbol:
                        exchange_info = self.client.get_exchange_info()
                        # Lọc thông tin cho symbol cụ thể
                        for s in exchange_info.get('symbols', []):
                            if s.get('symbol') == symbol:
                                return s
                        return {}
                    else:
                        return self.client.get_exchange_info()
            else:
                # Sử dụng requests trực tiếp
                if self.testnet:
                    url = f"{self.futures_testnet_url}/fapi/v1/exchangeInfo"
                else:
                    url = f"{self.spot_api_url}/api/v3/exchangeInfo"
                
                params = {}
                if symbol:
                    params['symbol'] = symbol
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if symbol:
                        # Lọc thông tin cho symbol cụ thể
                        for s in data.get('symbols', []):
                            if s.get('symbol') == symbol:
                                return s
                        return {}
                    else:
                        return data
            
            logger.warning(f"Không lấy được thông tin sàn cho {symbol if symbol else 'tất cả'}")
            return {}
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin sàn: {e}")
            return {}
    
    def get_ticker(self, symbol: str = None) -> Union[Dict, List[Dict], None]:
        """
        Lấy thông tin ticker hiện tại (giá hiện tại)
        
        Args:
            symbol: Symbol cần lấy thông tin (ví dụ: BTCUSDT), nếu None sẽ lấy tất cả
            
        Returns:
            Union[Dict, List[Dict], None]: Thông tin ticker hoặc None nếu không lấy được
        """
        try:
            if self.client:
                if self.testnet:
                    # Sử dụng futures API cho testnet
                    if symbol:
                        return self.client.futures_ticker(symbol=symbol)
                    else:
                        return self.client.futures_ticker()
                else:
                    # Sử dụng spot API cho mainnet
                    if symbol:
                        return self.client.get_ticker(symbol=symbol)
                    else:
                        return self.client.get_ticker()
            else:
                # Sử dụng requests trực tiếp
                if self.testnet:
                    url = f"{self.futures_testnet_url}/fapi/v1/ticker/price"
                else:
                    url = f"{self.spot_api_url}/api/v3/ticker/price"
                
                params = {}
                if symbol:
                    params['symbol'] = symbol
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    return response.json()
            
            logger.warning(f"Không lấy được thông tin ticker cho {symbol if symbol else 'tất cả'}")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin ticker: {e}")
            return None
    
    def get_market_overview(self) -> List[Dict]:
        """
        Lấy tổng quan thị trường (danh sách các cặp tiền, giá, khối lượng, biến động...)
        
        Returns:
            List[Dict]: Danh sách thông tin các cặp tiền
        """
        try:
            # Lấy thông tin ticker 24h cho tất cả các cặp tiền
            if self.testnet:
                tickers = self.get_24h_ticker()
            else:
                tickers = self.get_24h_ticker()
            
            if not tickers:
                logger.warning("Không lấy được thông tin ticker 24h")
                return []
            
            # Chuyển đổi dữ liệu
            market_overview = []
            for ticker in tickers:
                if isinstance(ticker, dict):
                    symbol = ticker.get('symbol', '')
                    
                    # Chỉ lấy các cặp tiền USDT
                    if symbol.endswith('USDT'):
                        price_change_percent = float(ticker.get('priceChangePercent', 0))
                        
                        market_data = {
                            'symbol': symbol,
                            'price': float(ticker.get('lastPrice', 0)),
                            'price_change_24h': price_change_percent,
                            'volume_24h': float(ticker.get('quoteVolume', 0)),
                            'high_24h': float(ticker.get('highPrice', 0)),
                            'low_24h': float(ticker.get('lowPrice', 0))
                        }
                        
                        market_overview.append(market_data)
            
            # Sắp xếp theo khối lượng giảm dần
            market_overview.sort(key=lambda x: x['volume_24h'], reverse=True)
            
            return market_overview
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy tổng quan thị trường: {e}")
            return []

# Tạo một hàm trợ giúp để lấy giá tài sản
def get_asset_price(symbol: str = "BTCUSDT", testnet: bool = False) -> float:
    """
    Hàm trợ giúp để lấy giá của một tài sản
    
    Args:
        symbol: Symbol cần lấy giá (ví dụ: BTCUSDT)
        testnet: True nếu sử dụng testnet, False nếu sử dụng mainnet
        
    Returns:
        float: Giá hiện tại hoặc 0 nếu không lấy được
    """
    api = EnhancedBinanceAPI(testnet=testnet)
    price = api.get_symbol_price(symbol)
    return price if price else 0

# Tạo một hàm trợ giúp để lấy số dư tài khoản
def get_account_balance(testnet: bool = False) -> Dict[str, float]:
    """
    Hàm trợ giúp để lấy số dư tài khoản
    
    Args:
        testnet: True nếu sử dụng testnet, False nếu sử dụng mainnet
        
    Returns:
        Dict[str, float]: Số dư tài khoản
    """
    api = EnhancedBinanceAPI(testnet=testnet)
    return api.get_account_balance()

# Chạy test nếu file được thực thi trực tiếp
if __name__ == "__main__":
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Kiểm tra kết nối
    api = EnhancedBinanceAPI(testnet=True)
    
    if api.test_connection():
        print("Kết nối đến Binance API thành công!")
        
        # Lấy giá BTC/USDT
        btc_price = api.get_symbol_price("BTCUSDT")
        print(f"Giá BTC/USDT: ${btc_price:,.2f}")
        
        # Lấy số dư tài khoản
        balance = api.get_account_balance()
        for symbol, amount in balance.items():
            print(f"Số dư {symbol}: {amount:,.8f}")
    else:
        print("Kết nối đến Binance API thất bại!")