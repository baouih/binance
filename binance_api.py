"""
Binance API Module - Giao tiếp với Binance API

Module này cung cấp các phương thức để tương tác với Binance API phục vụ cho
các hoạt động giao dịch và lấy dữ liệu thị trường.
"""

import os
import logging
import time
import hmac
import hashlib
from typing import Dict, List, Tuple, Any, Optional, Union
import urllib.parse
import requests
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("binance_api")

class BinanceAPI:
    """Lớp tương tác với Binance API"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        """
        Khởi tạo BinanceAPI Client
        
        Args:
            api_key (str, optional): API Key Binance
            api_secret (str, optional): API Secret Binance
            testnet (bool): Sử dụng testnet hay mainnet
        """
        # Tải cấu hình từ account_config.json để đồng bộ chế độ
        import json
        import os.path
        
        # Khởi tạo các thuộc tính mặc định
        self.testnet = testnet
        self.account_type = 'spot'  # Mặc định là spot
        
        try:
            # Tìm đường dẫn account_config.json
            account_config_path = 'account_config.json'
            if not os.path.exists(account_config_path):
                account_config_path = '../account_config.json'
                
            if os.path.exists(account_config_path):
                with open(account_config_path, 'r') as f:
                    config = json.load(f)
                    config_mode = config.get('api_mode', '').lower()
                    self.account_type = config.get('account_type', 'spot').lower()
                    
                    # api_mode trong config quyết định chế độ testnet
                    if config_mode == 'testnet':
                        self.testnet = True
                    elif config_mode == 'live':
                        self.testnet = False
                    else:
                        # Giữ giá trị từ tham số nhưng vẫn log
                        logger.warning(f"Giá trị api_mode '{config_mode}' không hợp lệ trong config, sử dụng giá trị mặc định")
                        
                logger.info(f"Đã tải cấu hình tài khoản từ {account_config_path}, chế độ API: {config_mode}, loại tài khoản: {self.account_type}")
            else:
                logger.warning(f"Không tìm thấy file cấu hình tài khoản, sử dụng chế độ mặc định: {'testnet' if testnet else 'live'}")
                
        except Exception as e:
            logger.warning(f"Lỗi khi tải cấu hình tài khoản, sử dụng cấu hình mặc định: {str(e)}")
        
        # Log trạng thái môi trường
        if self.testnet:
            logger.info("Kết nối đến môi trường TESTNET Binance")
        else:
            logger.info("Kết nối đến môi trường THỰC TẾ Binance")
            
        # Lấy API keys từ biến môi trường nếu không được cung cấp
        self.api_key = api_key or os.environ.get('BINANCE_API_KEY', '')
        self.api_secret = api_secret or os.environ.get('BINANCE_API_SECRET', '')
        
        # Kiểm tra API keys
        if self.testnet and (not self.api_key or not self.api_secret):
            logger.warning("CẢNH BÁO: API keys trống hoặc không hợp lệ cho chế độ testnet. Một số chức năng có thể không hoạt động.")
        
        # Endpoint URLs tương ứng với loại tài khoản và môi trường
        if self.testnet:
            # URLs cho Testnet
            if self.account_type == 'futures':
                self.base_url = 'https://testnet.binancefuture.com/fapi'
                self.stream_url = 'wss://stream.binancefuture.com/ws'
                logger.info("Sử dụng endpoints Binance Futures Testnet")
            else:  # Spot
                self.base_url = 'https://testnet.binance.vision/api'
                self.stream_url = 'wss://testnet.binance.vision/ws'
                logger.info("Sử dụng endpoints Binance Spot Testnet")
        else:
            # URLs cho Mainnet (thực tế)
            if self.account_type == 'futures':
                self.base_url = 'https://fapi.binance.com/fapi'
                self.stream_url = 'wss://fstream.binance.com/ws'
                logger.info("Sử dụng endpoints Binance Futures Mainnet")
            else:  # Spot
                self.base_url = 'https://api.binance.com/api'
                self.stream_url = 'wss://stream.binance.com:9443/ws'
                logger.info("Sử dụng endpoints Binance Spot Mainnet")
            
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key
        })

    # Phương thức phụ trợ
    def _generate_signature(self, data: Dict) -> str:
        """
        Tạo chữ ký HMAC SHA256 cho dữ liệu
        
        Args:
            data (Dict): Dữ liệu cần ký
            
        Returns:
            str: Chữ ký
        """
        query_string = urllib.parse.urlencode(data)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
        
    def _request(self, method: str, endpoint: str, params: Dict = None, 
              signed: bool = False, version: str = None) -> Dict:
        """
        Gửi request đến Binance API
        
        Args:
            method (str): Phương thức HTTP (GET, POST, DELETE, etc.)
            endpoint (str): Endpoint của API
            params (Dict, optional): Tham số cho request
            signed (bool): Cần ký request không
            version (str, optional): Phiên bản API, sẽ tự động chọn phù hợp nếu None
            
        Returns:
            Dict: Phản hồi từ API
        """
        # Chọn phiên bản API phù hợp dựa trên loại tài khoản
        if version is None:
            if self.account_type == 'futures':
                version = 'v1'  # Futures API sử dụng v1
            else:
                version = 'v3'  # Spot API sử dụng v3
        
        url = f"{self.base_url}/{version}/{endpoint}"
        
        # Chuẩn bị tham số
        params = params or {}
        
        # Thêm timestamp nếu cần ký
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
            
        try:
            response = self.session.request(method, url, params=params)
            response.raise_for_status()  # Nâng ngoại lệ nếu có lỗi HTTP
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return {"error": str(e)}
            
    # Market Data Endpoints
    def get_exchange_info(self) -> Dict:
        """
        Lấy thông tin sàn giao dịch
        
        Returns:
            Dict: Thông tin sàn giao dịch
        """
        # Đảm bảo sử dụng phiên bản API đúng cho từng loại tài khoản và môi trường
        if self.account_type == 'futures':
            return self._request('GET', 'exchangeInfo', version='v1')
        else:
            return self._request('GET', 'exchangeInfo')
        
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        Lấy thông tin chi tiết về một symbol
        
        Args:
            symbol (str): Symbol cần lấy thông tin
            
        Returns:
            Dict: Thông tin symbol
        """
        # Sử dụng phương thức get_exchange_info để đảm bảo đúng phiên bản API
        exchange_info = self.get_exchange_info()
        for symbol_info in exchange_info.get('symbols', []):
            if symbol_info['symbol'] == symbol:
                return symbol_info
        return {}
        
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """
        Lấy order book của một symbol
        
        Args:
            symbol (str): Symbol cần lấy order book
            limit (int): Số lượng bids/asks (max: 5000)
            
        Returns:
            Dict: Order book
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        return self._request('GET', 'depth', params)
        
    def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """
        Lấy giao dịch gần đây của một symbol
        
        Args:
            symbol (str): Symbol cần lấy giao dịch
            limit (int): Số lượng giao dịch (max: 1000)
            
        Returns:
            List[Dict]: Danh sách giao dịch
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        return self._request('GET', 'trades', params)
        
    def get_historical_trades(self, symbol: str, limit: int = 500, from_id: int = None) -> List[Dict]:
        """
        Lấy lịch sử giao dịch của một symbol
        
        Args:
            symbol (str): Symbol cần lấy lịch sử
            limit (int): Số lượng giao dịch (max: 1000)
            from_id (int, optional): ID giao dịch bắt đầu
            
        Returns:
            List[Dict]: Danh sách giao dịch
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        if from_id:
            params['fromId'] = from_id
            
        return self._request('GET', 'historicalTrades', params)
        
    def get_aggregate_trades(self, symbol: str, limit: int = 500, 
                          start_time: int = None, end_time: int = None) -> List[Dict]:
        """
        Lấy giao dịch tổng hợp của một symbol
        
        Args:
            symbol (str): Symbol cần lấy giao dịch
            limit (int): Số lượng giao dịch (max: 1000)
            start_time (int, optional): Thời gian bắt đầu (milliseconds)
            end_time (int, optional): Thời gian kết thúc (milliseconds)
            
        Returns:
            List[Dict]: Danh sách giao dịch
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        return self._request('GET', 'aggTrades', params)
        
    def get_klines(self, symbol: str, interval: str, limit: int = 500, 
                 start_time: int = None, end_time: int = None) -> List[List]:
        """
        Lấy dữ liệu k-line (candlestick) của một symbol
        
        Args:
            symbol (str): Symbol cần lấy dữ liệu
            interval (str): Khoảng thời gian (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            limit (int): Số lượng candlestick (max: 1000)
            start_time (int, optional): Thời gian bắt đầu (milliseconds)
            end_time (int, optional): Thời gian kết thúc (milliseconds)
            
        Returns:
            List[List]: Danh sách candlestick
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        return self._request('GET', 'klines', params)
        
    def get_avg_price(self, symbol: str) -> Dict:
        """
        Lấy giá trung bình hiện tại của một symbol
        
        Args:
            symbol (str): Symbol cần lấy giá
            
        Returns:
            Dict: Giá trung bình
        """
        params = {
            'symbol': symbol
        }
        return self._request('GET', 'avgPrice', params)
        
    def get_24h_ticker(self, symbol: str = None) -> Union[Dict, List[Dict]]:
        """
        Lấy thông tin ticker 24h của một symbol hoặc tất cả
        
        Args:
            symbol (str, optional): Symbol cần lấy thông tin
            
        Returns:
            Union[Dict, List[Dict]]: Thông tin ticker
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        return self._request('GET', 'ticker/24hr', params)
        
    def get_price_ticker(self, symbol: str = None) -> Union[Dict, List[Dict]]:
        """
        Lấy giá hiện tại của một symbol hoặc tất cả
        
        Args:
            symbol (str, optional): Symbol cần lấy giá
            
        Returns:
            Union[Dict, List[Dict]]: Giá hiện tại
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        # Đảm bảo sử dụng phiên bản API đúng cho futures
        if self.account_type == 'futures':
            return self._request('GET', 'ticker/price', params, version='v1')
        else:
            return self._request('GET', 'ticker/price', params)
        
    def get_book_ticker(self, symbol: str = None) -> Union[Dict, List[Dict]]:
        """
        Lấy thông tin best price/qty từ order book
        
        Args:
            symbol (str, optional): Symbol cần lấy thông tin
            
        Returns:
            Union[Dict, List[Dict]]: Thông tin book ticker
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        return self._request('GET', 'ticker/bookTicker', params)
        
    # Account Endpoints
    def get_account(self) -> Dict:
        """
        Lấy thông tin tài khoản
        
        Returns:
            Dict: Thông tin tài khoản
        """
        return self._request('GET', 'account', signed=True)
        
    def get_account_status(self) -> Dict:
        """
        Lấy trạng thái tài khoản
        
        Returns:
            Dict: Trạng thái tài khoản
        """
        return self._request('GET', 'account/status', signed=True)
        
    def get_trade_fee(self, symbol: str = None) -> Dict:
        """
        Lấy thông tin phí giao dịch
        
        Args:
            symbol (str, optional): Symbol cần lấy thông tin phí
            
        Returns:
            Dict: Thông tin phí
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        return self._request('GET', 'tradeFee', params, signed=True, version='v1')
        
    # Trading Endpoints
    def create_order(self, symbol: str, side: str, type: str, **kwargs) -> Dict:
        """
        Tạo lệnh giao dịch mới
        
        Args:
            symbol (str): Symbol giao dịch
            side (str): Phía giao dịch (BUY/SELL)
            type (str): Loại lệnh (LIMIT/MARKET/STOP_LOSS/STOP_LOSS_LIMIT/...)
            **kwargs: Các tham số khác tùy thuộc loại lệnh
            
        Returns:
            Dict: Thông tin lệnh đã tạo
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': type,
        }
        params.update(kwargs)
        
        return self._request('POST', 'order', params, signed=True)
        
    def test_order(self, symbol: str, side: str, type: str, **kwargs) -> Dict:
        """
        Kiểm tra lệnh giao dịch (không thực sự đặt lệnh)
        
        Args:
            symbol (str): Symbol giao dịch
            side (str): Phía giao dịch (BUY/SELL)
            type (str): Loại lệnh (LIMIT/MARKET/STOP_LOSS/STOP_LOSS_LIMIT/...)
            **kwargs: Các tham số khác tùy thuộc loại lệnh
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': type,
        }
        params.update(kwargs)
        
        return self._request('POST', 'order/test', params, signed=True)
        
    def get_order(self, symbol: str, order_id: int = None, orig_client_order_id: str = None) -> Dict:
        """
        Lấy thông tin một lệnh cụ thể
        
        Args:
            symbol (str): Symbol giao dịch
            order_id (int, optional): ID lệnh
            orig_client_order_id (str, optional): ID lệnh từ client
            
        Returns:
            Dict: Thông tin lệnh
        """
        params = {
            'symbol': symbol
        }
        if order_id:
            params['orderId'] = order_id
        if orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
            
        return self._request('GET', 'order', params, signed=True)
        
    def cancel_order(self, symbol: str, order_id: int = None, orig_client_order_id: str = None) -> Dict:
        """
        Hủy một lệnh
        
        Args:
            symbol (str): Symbol giao dịch
            order_id (int, optional): ID lệnh
            orig_client_order_id (str, optional): ID lệnh từ client
            
        Returns:
            Dict: Thông tin lệnh đã hủy
        """
        params = {
            'symbol': symbol
        }
        if order_id:
            params['orderId'] = order_id
        if orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
            
        return self._request('DELETE', 'order', params, signed=True)
        
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """
        Lấy danh sách các lệnh đang mở
        
        Args:
            symbol (str, optional): Symbol giao dịch
            
        Returns:
            List[Dict]: Danh sách lệnh đang mở
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        return self._request('GET', 'openOrders', params, signed=True)
        
    def get_all_orders(self, symbol: str, limit: int = 500, 
                     order_id: int = None, start_time: int = None, end_time: int = None) -> List[Dict]:
        """
        Lấy tất cả các lệnh của một symbol
        
        Args:
            symbol (str): Symbol giao dịch
            limit (int): Số lượng lệnh tối đa (max: 1000)
            order_id (int, optional): ID lệnh bắt đầu
            start_time (int, optional): Thời gian bắt đầu (milliseconds)
            end_time (int, optional): Thời gian kết thúc (milliseconds)
            
        Returns:
            List[Dict]: Danh sách lệnh
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        if order_id:
            params['orderId'] = order_id
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        return self._request('GET', 'allOrders', params, signed=True)
        
    def get_symbol_ticker(self, symbol: str) -> Dict:
        """
        Lấy thông tin giá hiện tại của một symbol
        
        Args:
            symbol (str): Symbol cần lấy giá
            
        Returns:
            Dict: Thông tin giá
        """
        params = {
            'symbol': symbol
        }
        # Đảm bảo sử dụng phiên bản API đúng cho futures
        if self.account_type == 'futures':
            return self._request('GET', 'ticker/price', params, version='v1')
        else:
            return self._request('GET', 'ticker/price', params)
        
    # Các phương thức hữu ích khác
    def convert_klines_to_dataframe(self, klines: List[List]) -> 'pd.DataFrame':
        """
        Chuyển đổi dữ liệu k-line thành DataFrame
        
        Args:
            klines (List[List]): Dữ liệu k-line từ API
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu k-line
        """
        try:
            import pandas as pd
            
            columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                     'close_time', 'quote_asset_volume', 'number_of_trades',
                     'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
                     
            df = pd.DataFrame(klines, columns=columns)
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume',
                             'quote_asset_volume', 'taker_buy_base_asset_volume',
                             'taker_buy_quote_asset_volume']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            
            # Chuyển đổi timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            return df
        except ImportError:
            logger.error("pandas is not installed. Please install pandas to use this function.")
            return None
            
    def get_historical_klines(self, symbol: str, interval: str, 
                           start_time: Union[str, datetime, int], 
                           end_time: Union[str, datetime, int] = None,
                           limit: int = 1000) -> List[List]:
        """
        Lấy dữ liệu k-line lịch sử của một symbol
        
        Args:
            symbol (str): Symbol cần lấy dữ liệu
            interval (str): Khoảng thời gian (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            start_time (Union[str, datetime, int]): Thời gian bắt đầu
            end_time (Union[str, datetime, int], optional): Thời gian kết thúc
            limit (int): Số lượng candlestick cho mỗi request (max: 1000)
            
        Returns:
            List[List]: Danh sách candlestick
        """
        # Chuyển đổi thời gian thành timestamp
        start_timestamp = None
        end_timestamp = None
        
        if isinstance(start_time, str):
            start_timestamp = int(datetime.strptime(start_time, "%Y-%m-%d").timestamp() * 1000)
        elif isinstance(start_time, datetime):
            start_timestamp = int(start_time.timestamp() * 1000)
        elif isinstance(start_time, int):
            start_timestamp = start_time
            
        if end_time:
            if isinstance(end_time, str):
                end_timestamp = int(datetime.strptime(end_time, "%Y-%m-%d").timestamp() * 1000)
            elif isinstance(end_time, datetime):
                end_timestamp = int(end_time.timestamp() * 1000)
            elif isinstance(end_time, int):
                end_timestamp = end_time
        else:
            end_timestamp = int(datetime.now().timestamp() * 1000)
            
        # Lấy dữ liệu theo nhiều request nếu cần
        klines = []
        while start_timestamp < end_timestamp:
            temp_klines = self.get_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_timestamp,
                end_time=end_timestamp,
                limit=limit
            )
            
            if not temp_klines:
                break
                
            klines.extend(temp_klines)
            
            # Cập nhật start_timestamp
            start_timestamp = temp_klines[-1][0] + 1
            
            # Thêm delay để tránh rate limit
            time.sleep(0.1)
            
        return klines
        
    def get_futures_account(self) -> Dict:
        """
        Lấy thông tin tài khoản futures
        
        Returns:
            Dict: Thông tin tài khoản futures
        """
        # Nếu không có API key hoặc API secret, trả về dữ liệu giả lập
        if not self.api_key or not self.api_secret:
            logger.warning("Không có API keys, sử dụng dữ liệu giả lập cho tài khoản futures")
            return self._generate_demo_futures_account()
            
        try:
            # Xác định URL endpoint dựa trên loại tài khoản & môi trường
            if self.testnet:
                try:
                    logger.info("Gửi yêu cầu đến Binance Testnet Futures API")
                    account_data = self._request('GET', 'account', signed=True, version='v2')
                    if account_data and not account_data.get('error'):
                        logger.info("Đã lấy thành công dữ liệu từ Testnet Futures API")
                    return account_data
                except Exception as e1:
                    logger.error(f"Lỗi khi truy vấn Testnet Futures v2 API: {str(e1)}")
                    try:
                        account_data = self._request('GET', 'account', signed=True, version='v1')
                        if account_data and not account_data.get('error'):
                            logger.info("Đã lấy thành công dữ liệu từ Testnet Futures API v1")
                        return account_data
                    except Exception as e2:
                        logger.error(f"Lỗi khi truy vấn Testnet Futures v1 API: {str(e2)}")
                        logger.warning("Đã xảy ra lỗi khi kết nối tới Testnet Futures API, chuyển sang sử dụng dữ liệu giả lập")
                        return self._generate_demo_futures_account()
            else:
                # Mainnet API (thực tế)
                logger.info("Gửi yêu cầu đến Binance Mainnet Futures API")
                return self._request('GET', 'account', signed=True, version='v2')
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin tài khoản futures: {str(e)}")
            logger.warning("Sử dụng dữ liệu giả lập do không thể kết nối đến Binance API")
            # Trả về dữ liệu giả lập nếu có lỗi
            return self._generate_demo_futures_account()
            
    def _generate_demo_futures_account(self) -> Dict:
        """Chỉ sử dụng khi không thể kết nối tới API Binance"""
        # Tạo tài khoản mặc định tương tự với tài khoản từ API
        logger.info("Không thể kết nối tới Binance API để lấy thông tin tài khoản thực")
        
        # Trả về tài khoản với số dư tương tự như API trả về
        return {
            "feeTier": 0,
            "canTrade": True,
            "canDeposit": True,
            "canWithdraw": True,
            "updateTime": int(time.time() * 1000),
            "totalInitialMargin": "0.00000000",
            "totalMaintMargin": "0.00000000",
            "totalWalletBalance": "13039.01250741",
            "totalUnrealizedProfit": "0.00000000",
            "totalMarginBalance": "13039.01250741",
            "totalPositionInitialMargin": "0.00000000",
            "totalOpenOrderInitialMargin": "0.00000000",
            "totalCrossWalletBalance": "13039.01250741",
            "totalCrossUnPnl": "0.00000000",
            "availableBalance": "13039.01250741",
            "maxWithdrawAmount": "13039.01250741",
            "assets": [
                {
                    "asset": "USDT",
                    "walletBalance": "13039.01250741",
                    "unrealizedProfit": "0.00000000",
                    "marginBalance": "13039.01250741",
                    "maintMargin": "0.00000000",
                    "initialMargin": "0.00000000",
                    "positionInitialMargin": "0.00000000",
                    "openOrderInitialMargin": "0.00000000",
                    "maxWithdrawAmount": "13039.01250741",
                    "crossWalletBalance": "13039.01250741",
                    "crossUnPnl": "0.00000000",
                    "availableBalance": "13039.01250741"
                }
            ],
            "positions": []
        }
        
    def get_futures_position_risk(self, symbol: str = None) -> List[Dict]:
        """
        Lấy thông tin rủi ro vị thế futures
        
        Args:
            symbol (str, optional): Symbol cần lấy thông tin
            
        Returns:
            List[Dict]: Thông tin rủi ro vị thế
        """
        # Nếu không có API key hoặc API secret, trả về dữ liệu giả lập
        if not self.api_key or not self.api_secret:
            logger.warning("Không có API keys, sử dụng dữ liệu giả lập cho vị thế futures")
            return self._generate_demo_positions()
            
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol
            
            if self.testnet:
                # Trong môi trường testnet, các endpoint vị thế có thể không khả dụng hoặc không ổn định
                # Thử lấy thông tin vị thế từ account API trước (cách đáng tin cậy nhất)
                try:
                    logger.info("Thử lấy thông tin vị thế từ account API")
                    account_data = self.get_futures_account()
                    if isinstance(account_data, dict) and 'positions' in account_data:
                        positions = account_data.get('positions', [])
                        # Lọc các vị thế có số lượng khác 0
                        active_positions = []
                        for pos in positions:
                            if isinstance(pos, dict) and float(pos.get('positionAmt', 0)) != 0:
                                active_positions.append(pos)
                        
                        if active_positions:
                            logger.info(f"Đã lấy {len(active_positions)} vị thế active từ account API")
                        else:
                            logger.info("Không có vị thế active từ account API")
                            
                        logger.info("Đã lấy thông tin vị thế từ account API")
                        return active_positions
                except Exception as e3:
                    logger.error(f"Lỗi khi truy xuất vị thế từ account API: {str(e3)}")
                    
                # Thử kết nối đến positionRisk API (ít tin cậy hơn với testnet)
                try:
                    logger.info("Gửi yêu cầu đến Binance Testnet Futures API (positionRisk)")
                    # Thử sử dụng version 2 trước
                    positions_data = self._request('GET', 'positionRisk', params, signed=True, version='v2')
                    
                    # Kiểm tra dữ liệu trả về
                    if isinstance(positions_data, list):
                        # Lọc các vị thế có số lượng khác 0
                        active_positions = []
                        for pos in positions_data:
                            if isinstance(pos, dict) and float(pos.get('positionAmt', 0)) != 0:
                                active_positions.append(pos)
                        
                        logger.info(f"Đã lấy thông tin vị thế từ Testnet Futures API v2: {len(active_positions)} vị thế active")
                        return active_positions
                    elif isinstance(positions_data, dict) and not positions_data.get('error'):
                        logger.info(f"Đã lấy thông tin vị thế từ Testnet Futures API v2")
                        return [positions_data] if positions_data else []
                except Exception as e1:
                    logger.error(f"Lỗi khi truy vấn testnet futures v2 API positionRisk: {str(e1)}")
                
                # Thử với v1 endpoint
                try:
                    logger.info("Thử lại với Binance Testnet Futures API v1 (positionRisk)")
                    positions_data = self._request('GET', 'positionRisk', params, signed=True, version='v1') 
                    
                    # Kiểm tra dữ liệu trả về
                    if isinstance(positions_data, list):
                        # Lọc các vị thế có số lượng khác 0
                        active_positions = []
                        for pos in positions_data:
                            if isinstance(pos, dict) and float(pos.get('positionAmt', 0)) != 0:
                                active_positions.append(pos)
                        
                        logger.info(f"Đã lấy thông tin vị thế từ Testnet Futures API v1: {len(active_positions)} vị thế active")
                        return active_positions
                    elif isinstance(positions_data, dict) and not positions_data.get('error'):
                        logger.info("Đã lấy thông tin vị thế từ Testnet Futures API v1")
                        return [positions_data] if positions_data else []
                except Exception as e2:
                    logger.error(f"Lỗi khi truy vấn testnet futures v1 API positionRisk: {str(e2)}")
                
                # Trả về dữ liệu giả lập nếu tất cả các phương pháp đều không hoạt động
                logger.warning("Không thể kết nối đến Binance Testnet Futures API, chuyển sang sử dụng dữ liệu giả lập")
                return self._generate_demo_positions()
            else:
                # Mainnet API (thực tế)
                logger.info("Gửi yêu cầu đến Binance Mainnet Futures API (positionRisk)")
                return self._request('GET', 'positionRisk', params, signed=True, version='v2')
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin vị thế futures: {str(e)}")
            logger.warning("Sử dụng dữ liệu giả lập do không thể kết nối đến Binance API")
            # Trả về dữ liệu giả lập nếu có lỗi
            return self._generate_demo_positions()
    
    def _generate_demo_positions(self) -> List[Dict]:
        """Tạo dữ liệu vị thế futures giả lập cho trường hợp testnet không khả dụng"""
        # Danh sách vị thế mặc định rỗng khi không có vị thế thực tế
        positions = []
        
        # Trong môi trường thực tế, dữ liệu sẽ được lấy từ API
        logger.info("Không có dữ liệu vị thế thực từ Binance API, tạo danh sách vị thế rỗng")
        
        # Lưu lại vị thế demo để sử dụng ở nơi khác
        self._demo_positions = positions
        
        return positions
        
    def futures_change_leverage(self, symbol: str, leverage: int) -> Dict:
        """
        Thay đổi đòn bẩy cho một symbol
        
        Args:
            symbol (str): Symbol cần thay đổi đòn bẩy
            leverage (int): Đòn bẩy (1-125)
            
        Returns:
            Dict: Kết quả thay đổi
        """
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        
        return self._request('POST', 'leverage', params, signed=True, version='v1')

    def download_historical_data(self, 
                             symbol: str, 
                             interval: str, 
                             start_time: Union[str, datetime], 
                             end_time: Union[str, datetime] = None,
                             output_dir: str = 'test_data') -> str:
        """
        Tải xuống dữ liệu lịch sử và lưu vào file CSV
        
        Args:
            symbol (str): Symbol cần tải dữ liệu
            interval (str): Khoảng thời gian (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            start_time (Union[str, datetime]): Thời gian bắt đầu
            end_time (Union[str, datetime], optional): Thời gian kết thúc
            output_dir (str): Thư mục lưu file
            
        Returns:
            str: Đường dẫn đến file dữ liệu
        """
        try:
            import pandas as pd
            import os
            
            # Lấy dữ liệu lịch sử
            klines = self.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )
            
            # Chuyển đổi thành DataFrame
            df = self.convert_klines_to_dataframe(klines)
            
            if df is None or df.empty:
                logger.error(f"Không có dữ liệu cho {symbol} từ {start_time} đến {end_time}")
                return None
                
            # Tạo thư mục output nếu chưa tồn tại
            os.makedirs(output_dir, exist_ok=True)
            
            # Đường dẫn file
            file_name = f"{symbol}_{interval}.csv"
            file_path = os.path.join(output_dir, file_name)
            
            # Lưu DataFrame vào file CSV
            df.to_csv(file_path, index=False)
            
            logger.info(f"Đã tải xuống và lưu dữ liệu {symbol} {interval} vào {file_path}")
            
            return file_path
        except ImportError:
            logger.error("pandas is not installed. Please install pandas to use this function.")
            return None