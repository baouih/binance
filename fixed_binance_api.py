"""
Phiên bản đơn giản hóa của Binance API để tránh các vấn đề đệ quy
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

import requests

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fixed_binance_api')

# Các URL API
BINANCE_API_URL = "https://api.binance.com"
BINANCE_FUTURES_API_URL = "https://fapi.binance.com"
BINANCE_FUTURES_TESTNET_API_URL = "https://testnet.binancefuture.com"

class FixedBinanceAPI:
    """
    Phiên bản đơn giản hóa của Binance API để tránh các vấn đề đệ quy
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, 
                 testnet: bool = True, account_type: str = 'futures'):
        """
        Khởi tạo API client
        
        Args:
            api_key (str, optional): Khóa API Binance
            api_secret (str, optional): Bí mật API Binance
            testnet (bool): Sử dụng testnet (mặc định là True)
            account_type (str): Loại tài khoản ('futures' hoặc 'spot')
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.account_type = account_type
        
        if testnet:
            logger.info("Kết nối đến môi trường TESTNET Binance")
            # Sử dụng URL testnet cho Futures
            self.base_url = BINANCE_FUTURES_TESTNET_API_URL
            logger.info("Sử dụng endpoints Binance Futures Testnet")
        elif account_type == 'futures':
            self.base_url = BINANCE_FUTURES_API_URL
            logger.info("Sử dụng endpoints Binance Futures")
        else:
            self.base_url = BINANCE_API_URL
            logger.info("Sử dụng endpoints Binance Spot")

        # Tải cấu hình tài khoản từ file nếu có
        self._load_account_config()
        
    def _load_account_config(self) -> None:
        """Tải cấu hình tài khoản từ file"""
        try:
            config_path = 'account_config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                # Cập nhật từ cấu hình
                if 'api_mode' in config:
                    self.testnet = config['api_mode'] == 'testnet'
                    
                if 'account_type' in config:
                    self.account_type = config['account_type']
                    
                # Cập nhật URL dựa trên cấu hình
                if self.testnet:
                    self.base_url = BINANCE_FUTURES_TESTNET_API_URL
                elif self.account_type == 'futures':
                    self.base_url = BINANCE_FUTURES_API_URL
                else:
                    self.base_url = BINANCE_API_URL
                    
                if 'api_key' in config and config['api_key']:
                    self.api_key = config['api_key']
                
                if 'api_secret' in config and config['api_secret']:
                    self.api_secret = config['api_secret']
                    
                logger.info(f"Đã tải cấu hình tài khoản từ {config_path}, chế độ API: {config.get('api_mode', 'unknown')}, loại tài khoản: {config.get('account_type', 'unknown')}")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình tài khoản: {str(e)}")
        
    def _send_request(self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = False) -> Any:
        """
        Gửi request đến Binance API
        
        Args:
            method (str): Phương thức HTTP ('GET', 'POST', 'DELETE', ...)
            endpoint (str): Endpoint API
            params (Dict, optional): Tham số request
            signed (bool): Yêu cầu có chữ ký hay không
            
        Returns:
            Any: Dữ liệu trả về từ API
        """
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key
            
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, params=params, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, params=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Phương thức không hỗ trợ: {method}")
                
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Lỗi khi gửi request đến Binance API: {str(e)}")
            return None
            
    def get_exchange_info(self) -> Dict:
        """
        Lấy thông tin trao đổi từ Binance
        
        Returns:
            Dict: Thông tin trao đổi
        """
        if self.account_type == 'futures':
            endpoint = '/fapi/v1/exchangeInfo'
        else:
            endpoint = '/api/v3/exchangeInfo'
            
        return self._send_request('GET', endpoint)
        
    def get_account_balance(self) -> List[Dict]:
        """
        Lấy số dư tài khoản
        
        Returns:
            List[Dict]: Danh sách số dư
        """
        if self.account_type == 'futures':
            endpoint = '/fapi/v2/balance'
        else:
            endpoint = '/api/v3/account'
            
        result = self._send_request('GET', endpoint, signed=True)
        if result:
            if self.account_type == 'futures':
                return result
            else:
                return result.get('balances', [])
        return []
        
    def get_symbol_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Lấy thông tin ticker cho một cặp
        
        Args:
            symbol (str): Mã cặp (VD: BTCUSDT)
            
        Returns:
            Optional[Dict]: Thông tin ticker hoặc None nếu có lỗi
        """
        if self.account_type == 'futures':
            endpoint = '/fapi/v1/ticker/price'
        else:
            endpoint = '/api/v3/ticker/price'
            
        params = {'symbol': symbol}
        return self._send_request('GET', endpoint, params)
        
    def get_futures_account_info(self) -> Dict:
        """
        Lấy thông tin tài khoản futures
        
        Returns:
            Dict: Thông tin tài khoản futures
        """
        endpoint = '/fapi/v2/account'
        return self._send_request('GET', endpoint, signed=True)
        
    def get_open_positions(self) -> List[Dict]:
        """
        Lấy danh sách vị thế đang mở
        
        Returns:
            List[Dict]: Danh sách vị thế đang mở
        """
        if self.account_type != 'futures':
            logger.warning("get_open_positions chỉ khả dụng cho tài khoản futures")
            return []
            
        account_info = self.get_futures_account_info()
        if not account_info:
            return []
            
        # Lọc các vị thế có amount != 0
        positions = account_info.get('positions', [])
        return [position for position in positions if float(position.get('positionAmt', 0)) != 0]
        
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Lấy danh sách lệnh đang mở
        
        Args:
            symbol (str, optional): Mã cặp (VD: BTCUSDT)
            
        Returns:
            List[Dict]: Danh sách lệnh đang mở
        """
        if self.account_type == 'futures':
            endpoint = '/fapi/v1/openOrders'
        else:
            endpoint = '/api/v3/openOrders'
            
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        result = self._send_request('GET', endpoint, params, signed=True)
        if result:
            return result
        return []
        
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List[List]:
        """
        Lấy dữ liệu K-lines (candlestick)
        
        Args:
            symbol (str): Mã cặp (VD: BTCUSDT)
            interval (str): Khoảng thời gian ('1m', '5m', '15m', '1h', '4h', '1d', ...)
            limit (int): Số lượng K-lines tối đa (mặc định 500)
            
        Returns:
            List[List]: Danh sách K-lines
        """
        if self.account_type == 'futures':
            endpoint = '/fapi/v1/klines'
        else:
            endpoint = '/api/v3/klines'
            
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        result = self._send_request('GET', endpoint, params)
        if result:
            return result
        return []

    def futures_create_order(self, symbol: str, side: str, order_type: str, 
                           quantity: Optional[float] = None, price: Optional[float] = None,
                           stop_price: Optional[float] = None, close_position: bool = False) -> Dict:
        """
        Tạo lệnh trên tài khoản futures
        
        Args:
            symbol (str): Mã cặp (VD: BTCUSDT)
            side (str): Phía ('BUY' hoặc 'SELL')
            order_type (str): Loại lệnh ('LIMIT', 'MARKET', 'STOP', 'TAKE_PROFIT', ...)
            quantity (float, optional): Số lượng
            price (float, optional): Giá (cho lệnh LIMIT)
            stop_price (float, optional): Giá dừng (cho lệnh STOP, TAKE_PROFIT)
            close_position (bool): Đóng vị thế (chỉ cho futures)
            
        Returns:
            Dict: Thông tin lệnh đã tạo
        """
        if self.account_type != 'futures':
            logger.warning("futures_create_order chỉ khả dụng cho tài khoản futures")
            return {}
            
        endpoint = '/fapi/v1/order'
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type
        }
        
        if quantity:
            params['quantity'] = quantity
            
        if price:
            params['price'] = price
            
        if stop_price:
            params['stopPrice'] = stop_price
            
        if close_position:
            params['closePosition'] = 'true'
            
        return self._send_request('POST', endpoint, params, signed=True)
        
    def futures_cancel_order(self, symbol: str, order_id: Optional[int] = None) -> Dict:
        """
        Hủy lệnh trên tài khoản futures
        
        Args:
            symbol (str): Mã cặp (VD: BTCUSDT)
            order_id (int, optional): ID lệnh
            
        Returns:
            Dict: Thông tin lệnh đã hủy
        """
        if self.account_type != 'futures':
            logger.warning("futures_cancel_order chỉ khả dụng cho tài khoản futures")
            return {}
            
        endpoint = '/fapi/v1/order'
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
            
        return self._send_request('DELETE', endpoint, params, signed=True)
        
    def futures_cancel_all_orders(self, symbol: str) -> Dict:
        """
        Hủy tất cả lệnh trên tài khoản futures
        
        Args:
            symbol (str): Mã cặp (VD: BTCUSDT)
            
        Returns:
            Dict: Kết quả hủy lệnh
        """
        if self.account_type != 'futures':
            logger.warning("futures_cancel_all_orders chỉ khả dụng cho tài khoản futures")
            return {}
            
        endpoint = '/fapi/v1/allOpenOrders'
        params = {'symbol': symbol}
        
        return self._send_request('DELETE', endpoint, params, signed=True)
        
    def futures_change_leverage(self, symbol: str, leverage: int) -> Dict:
        """
        Thay đổi đòn bẩy trên tài khoản futures
        
        Args:
            symbol (str): Mã cặp (VD: BTCUSDT)
            leverage (int): Giá trị đòn bẩy (1-125)
            
        Returns:
            Dict: Kết quả thay đổi đòn bẩy
        """
        if self.account_type != 'futures':
            logger.warning("futures_change_leverage chỉ khả dụng cho tài khoản futures")
            return {}
            
        endpoint = '/fapi/v1/leverage'
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        
        return self._send_request('POST', endpoint, params, signed=True)
        
    def get_futures_position_information(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Lấy thông tin vị thế futures
        
        Args:
            symbol (str, optional): Mã cặp (VD: BTCUSDT)
            
        Returns:
            List[Dict]: Thông tin vị thế
        """
        if self.account_type != 'futures':
            logger.warning("get_futures_position_information chỉ khả dụng cho tài khoản futures")
            return []
            
        endpoint = '/fapi/v2/positionRisk'
        params = {}
        
        if symbol:
            params['symbol'] = symbol
            
        result = self._send_request('GET', endpoint, params, signed=True)
        if result:
            return result
        return []
        
    def get_futures_account_balance(self) -> List[Dict]:
        """
        Lấy số dư tài khoản futures
        
        Returns:
            List[Dict]: Danh sách số dư
        """
        if self.account_type != 'futures':
            logger.warning("get_futures_account_balance chỉ khả dụng cho tài khoản futures")
            return []
            
        endpoint = '/fapi/v2/balance'
        result = self._send_request('GET', endpoint, signed=True)
        if result:
            return result
        return []

    def futures_set_stop_loss(self, symbol: str, side: str, stop_price: float, quantity: float) -> Dict:
        """
        Đặt stop loss trên tài khoản futures
        
        Args:
            symbol (str): Mã cặp (VD: BTCUSDT)
            side (str): Phía ('BUY' hoặc 'SELL')
            stop_price (float): Giá dừng
            quantity (float): Số lượng
            
        Returns:
            Dict: Thông tin lệnh stop loss
        """
        return self.futures_create_order(
            symbol=symbol,
            side=side,
            order_type='STOP_MARKET',
            quantity=quantity,
            stop_price=stop_price
        )
        
    def futures_set_take_profit(self, symbol: str, side: str, stop_price: float, quantity: float) -> Dict:
        """
        Đặt take profit trên tài khoản futures
        
        Args:
            symbol (str): Mã cặp (VD: BTCUSDT)
            side (str): Phía ('BUY' hoặc 'SELL')
            stop_price (float): Giá dừng
            quantity (float): Số lượng
            
        Returns:
            Dict: Thông tin lệnh take profit
        """
        return self.futures_create_order(
            symbol=symbol,
            side=side,
            order_type='TAKE_PROFIT_MARKET',
            quantity=quantity,
            stop_price=stop_price
        )
        
    def get_usdt_balance(self) -> float:
        """
        Lấy số dư USDT
        
        Returns:
            float: Số dư USDT
        """
        if self.account_type == 'futures':
            balances = self.get_futures_account_balance()
            for balance in balances:
                if balance.get('asset') == 'USDT':
                    return float(balance.get('balance', 0))
        else:
            balances = self.get_account_balance()
            for balance in balances:
                if balance.get('asset') == 'USDT':
                    return float(balance.get('free', 0))
        return 0.0
        
    def check_connection(self) -> bool:
        """
        Kiểm tra kết nối đến Binance API
        
        Returns:
            bool: True nếu kết nối thành công, False nếu thất bại
        """
        try:
            if self._send_request('GET', '/fapi/v1/ping'):
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra kết nối: {str(e)}")
            return False