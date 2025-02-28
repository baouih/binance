import os
import logging
import random
import time
import hmac
import hashlib
from urllib.parse import urlencode
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('binance_api')

class BinanceAPI:
    def __init__(self, api_key=None, api_secret=None, testnet=True, simulation_mode=False):
        """
        Initialize the Binance API client.
        
        Args:
            api_key (str): Binance API key
            api_secret (str): Binance API secret
            testnet (bool): Whether to use testnet (default: True)
            simulation_mode (bool): Whether to use simulation mode (no actual API calls)
        """
        self.api_key = api_key or os.getenv('BINANCE_API_KEY', '')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET', '')
        
        # Kiểm tra cấu hình testnet từ biến môi trường nếu có
        env_testnet = os.getenv('BINANCE_TESTNET')
        if env_testnet is not None:
            self.testnet = env_testnet.lower() == 'true'
        else:
            self.testnet = testnet
            
        self.simulation_mode = simulation_mode
        
        # Kiểm tra keys
        if self.api_key and self.api_secret:
            logger.info("Khóa API Binance đã được cấu hình")
        else:
            logger.warning("Khóa API Binance chưa được cấu hình! Sẽ sử dụng chế độ mô phỏng.")
            self.simulation_mode = True
        
        if self.simulation_mode:
            logger.info("Initializing BinanceAPI in simulation mode")
            self.client = None
        else:
            logger.info("Initializing BinanceAPI in live mode")
            try:
                # Initialize with REST client directly
                self.base_url = 'https://testnet.binancefuture.com' if testnet else 'https://fapi.binance.com'
                # Test connection
                self.test_connection()
                logger.info(f"BinanceAPI initialized with client: {self.client is not None}")
            except Exception as e:
                logger.error(f"Error initializing Binance client: {str(e)}")
                self.client = None
                
    def test_connection(self):
        """Test API connection"""
        if self.simulation_mode:
            self.client = True
            return True
            
        try:
            url = f"{self.base_url}/fapi/v1/ping"
            response = requests.get(url)
            response.raise_for_status()
            self.client = True
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            self.client = None
            return False
    
    def _get_signature(self, params):
        """Generate a signature for a request"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_headers(self):
        """Get request headers"""
        return {
            'X-MBX-APIKEY': self.api_key
        }
    
    def get_server_time(self):
        """Get server time"""
        if self.simulation_mode:
            return int(time.time() * 1000)
            
        try:
            url = f"{self.base_url}/fapi/v1/time"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()['serverTime']
        except Exception as e:
            logger.error(f"Error getting server time: {str(e)}")
            return int(time.time() * 1000)
            
    def get_exchange_info(self):
        """Get exchange information"""
        if self.simulation_mode:
            return {
                'symbols': [
                    {
                        'symbol': 'BTCUSDT',
                        'baseAsset': 'BTC',
                        'quoteAsset': 'USDT',
                        'filters': [
                            {
                                'filterType': 'LOT_SIZE',
                                'minQty': '0.00100000',
                                'maxQty': '1000.00000000',
                                'stepSize': '0.00100000'
                            },
                            {
                                'filterType': 'PRICE_FILTER',
                                'minPrice': '0.01000000',
                                'maxPrice': '1000000.00000000',
                                'tickSize': '0.01000000'
                            }
                        ]
                    }
                ]
            }
            
        try:
            url = f"{self.base_url}/fapi/v1/exchangeInfo"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting exchange info: {str(e)}")
            return {'symbols': []}
    
    def get_klines(self, symbol, interval='1h', limit=500, start_time=None, end_time=None):
        """
        Get historical klines (candlesticks)
        
        Args:
            symbol (str): The trading pair
            interval (str): Interval of klines (1m, 5m, 15m, 1h, etc.)
            limit (int): Number of klines to return
            start_time (int): Start time in milliseconds
            end_time (int): End time in milliseconds
            
        Returns:
            pandas.DataFrame: DataFrame with klines data
        """
        if self.simulation_mode:
            return self._generate_mock_klines(symbol, interval, limit)
        
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
                
            url = f"{self.base_url}/fapi/v1/klines"
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            klines = response.json()
            df = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume',
                                              'close_time', 'quote_volume', 'trades_count',
                                              'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignored'])
            
            # Convert numeric columns
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume',
                           'taker_buy_base_volume', 'taker_buy_quote_volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
            
            # Convert timestamps to datetime
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting klines: {str(e)}")
            # Return empty dataframe with proper columns
            return pd.DataFrame(columns=['open_time', 'open', 'high', 'low', 'close', 'volume',
                                        'close_time', 'quote_volume', 'trades_count',
                                        'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignored'])
    
    def _generate_mock_klines(self, symbol, interval, limit):
        """Generate mock klines for simulation"""
        logger.info(f"SIMULATION: Generated {limit} samples of synthetic data for {symbol}")
        
        # Set seed for reproducibility
        np.random.seed(42)
        
        # Current time
        end_time = datetime.now()
        
        # Calculate time delta based on interval
        if interval.endswith('m'):
            minutes = int(interval[:-1])
            delta = timedelta(minutes=minutes)
        elif interval.endswith('h'):
            hours = int(interval[:-1])
            delta = timedelta(hours=hours)
        elif interval.endswith('d'):
            days = int(interval[:-1])
            delta = timedelta(days=days)
        else:
            delta = timedelta(hours=1)  # Default to 1h
            
        # Generate timestamps
        timestamps = [end_time - delta * i for i in range(limit)]
        timestamps.reverse()  # Oldest first
        
        # Get current market price from CoinGecko or use a safe default
        current_price = 81500  # Fallback price
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
            if response.status_code == 200:
                data = response.json()
                if 'bitcoin' in data and 'usd' in data['bitcoin']:
                    current_price = data['bitcoin']['usd']
        except Exception as e:
            logger.warning(f"Failed to get current price from CoinGecko: {e}")
        
        # Base price and volatility based on symbol and current price
        if symbol == 'BTCUSDT':
            base_price = current_price  # Use current price
            volatility = 0.005  # Daily volatility
        elif symbol == 'ETHUSDT':
            # Typically ETH is about 5-7% of BTC price
            base_price = current_price * 0.06  
            volatility = 0.007
        else:
            base_price = 100
            volatility = 0.01
            
        # Generate price series with random walk
        close_prices = [base_price]
        for i in range(1, limit):
            # Random price change with momentum
            momentum = 0.2  # Autocorrelation factor
            change = np.random.normal(0, volatility) + momentum * (close_prices[-1] / close_prices[0] - 1)
            new_price = close_prices[-1] * (1 + change)
            close_prices.append(new_price)
            
        # Create other price components
        high_prices = [price * (1 + abs(np.random.normal(0, volatility))) for price in close_prices]
        low_prices = [price * (1 - abs(np.random.normal(0, volatility))) for price in close_prices]
        open_prices = [low + (high - low) * np.random.random() for low, high in zip(low_prices, high_prices)]
        
        # Create volumes with some correlation to price changes
        volumes = []
        for i in range(limit):
            if i > 0:
                price_change = abs(close_prices[i] - close_prices[i-1]) / close_prices[i-1]
                volume_factor = 1 + price_change * 10  # Higher volume on larger price moves
            else:
                volume_factor = 1
                
            base_volume = base_price * 500  # Base volume proportional to price
            volumes.append(base_volume * volume_factor * np.random.lognormal(0, 0.5))
            
        # Create quote volumes (volume * price)
        quote_volumes = [v * p for v, p in zip(volumes, close_prices)]
        
        # Create taker buy volumes (some portion of total volume)
        taker_buy_ratios = [0.4 + np.random.random() * 0.2 for _ in range(limit)]  # 40-60% taker buy ratio
        taker_buy_base_volumes = [v * r for v, r in zip(volumes, taker_buy_ratios)]
        taker_buy_quote_volumes = [v * p for v, p in zip(taker_buy_base_volumes, close_prices)]
        
        # Create DataFrame
        df = pd.DataFrame({
            'open_time': timestamps,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes,
            'close_time': [t + delta for t in timestamps],
            'quote_volume': quote_volumes,
            'trades_count': [int(v / 10) if np.isfinite(v) else 0 for v in volumes],  # Rough approximation
            'taker_buy_base_volume': taker_buy_base_volumes,
            'taker_buy_quote_volume': taker_buy_quote_volumes,
            'ignored': [0] * limit
        })
        
        # Log some info about the generated data
        logger.info(f"Date range: {df['open_time'].min()} to {df['open_time'].max()}")
        logger.info(f"Price range: {df['close'].min():.2f} to {df['close'].max():.2f}")
        
        return df
        
    def get_account_info(self):
        """Get account information"""
        if self.simulation_mode:
            # In simulation mode, don't show any active positions
            return {
                'totalWalletBalance': '50000.00',
                'totalUnrealizedProfit': '0.00',
                'totalMarginBalance': '50000.00',
                'availableBalance': '50000.00',
                'positions': []
            }
        
        try:
            timestamp = self.get_server_time()
            params = {
                'timestamp': timestamp
            }
            signature = self._get_signature(params)
            params['signature'] = signature
            
            url = f"{self.base_url}/fapi/v2/account"
            response = requests.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            logger.info(f"Đã lấy được thông tin tài khoản Binance thành công")
            return response.json()
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {}
            
    def get_open_orders(self, symbol=None):
        """Get all open orders on a symbol or all symbols"""
        if self.simulation_mode:
            # Return empty list in simulation mode to not display any mock orders
            return []
            
        try:
            timestamp = self.get_server_time()
            params = {
                'timestamp': timestamp
            }
            
            if symbol:
                params['symbol'] = symbol
                
            signature = self._get_signature(params)
            params['signature'] = signature
            
            url = f"{self.base_url}/fapi/v1/openOrders"
            response = requests.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            logger.info(f"Đã lấy được thông tin lệnh đang mở thành công: {len(response.json())} lệnh")
            return response.json()
        except Exception as e:
            logger.error(f"Error getting open orders: {str(e)}")
            return []
            
    def get_positions(self):
        """Get current positions (extracted from account info)"""
        try:
            account_info = self.get_account_info()
            if 'positions' in account_info:
                # Filter out positions with zero amount
                active_positions = [p for p in account_info['positions'] if float(p.get('positionAmt', 0)) != 0]
                logger.info(f"Đã lấy được thông tin vị thế đang mở: {len(active_positions)} vị thế")
                return active_positions
            return []
        except Exception as e:
            logger.error(f"Error extracting positions: {str(e)}")
            return []

    def get_income_history(self, symbol=None, income_type=None, limit=100):
        """Get income history (realized PnL, funding fees, etc.)"""
        if self.simulation_mode:
            return [
                {
                    "symbol": "BTCUSDT",
                    "incomeType": "REALIZED_PNL",
                    "income": "0.00000000",
                    "asset": "USDT",
                    "time": int(time.time() * 1000) - 86400000,
                    "info": "FUNDING_FEE",
                    "tranId": 9243,
                    "tradeId": ""
                }
            ]
            
        try:
            timestamp = self.get_server_time()
            params = {
                'timestamp': timestamp,
                'limit': limit
            }
            
            if symbol:
                params['symbol'] = symbol
            if income_type:
                params['incomeType'] = income_type
                
            signature = self._get_signature(params)
            params['signature'] = signature
            
            url = f"{self.base_url}/fapi/v1/income"
            response = requests.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            logger.info(f"Đã lấy được thông tin lịch sử thu nhập: {len(response.json())} bản ghi")
            return response.json()
        except Exception as e:
            logger.error(f"Error getting income history: {str(e)}")
            return []
    
    def get_order_book(self, symbol, limit=20):
        """Get order book"""
        if self.simulation_mode:
            # Generate mock order book
            last_price = 65000 if symbol == 'BTCUSDT' else 3500
            spread = last_price * 0.0005  # 0.05% spread
            
            asks = []
            for i in range(limit):
                price = last_price + spread + i * (spread / 2)
                quantity = 1 / (i + 1) * random.uniform(0.1, 2)
                asks.append([price, quantity])
                
            bids = []
            for i in range(limit):
                price = last_price - spread - i * (spread / 2)
                quantity = 1 / (i + 1) * random.uniform(0.1, 2)
                bids.append([price, quantity])
                
            return {
                'lastUpdateId': int(time.time() * 1000),
                'bids': bids,
                'asks': asks
            }
            
        try:
            params = {
                'symbol': symbol,
                'limit': limit
            }
            
            url = f"{self.base_url}/fapi/v1/depth"
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting order book: {str(e)}")
            return {'bids': [], 'asks': []}
            
    def create_order(self, symbol, side, order_type, quantity=None, price=None, 
                     time_in_force='GTC', reduce_only=False, close_position=False,
                     stop_price=None, working_type='CONTRACT_PRICE', position_side='BOTH',
                     new_client_order_id=None):
        """
        Create a new order
        
        Args:
            symbol (str): The trading pair
            side (str): BUY or SELL
            order_type (str): LIMIT, MARKET, STOP, TAKE_PROFIT, etc.
            quantity (float): Order quantity
            price (float): Order price
            time_in_force (str): GTC, IOC, FOK
            reduce_only (bool): Reduce only flag
            close_position (bool): Close position flag
            stop_price (float): Stop price for STOP orders
            working_type (str): CONTRACT_PRICE or MARK_PRICE
            position_side (str): BOTH, LONG, or SHORT
            new_client_order_id (str): Client order ID
            
        Returns:
            dict: Order information
        """
        if self.simulation_mode:
            # Generate mock order response
            order_id = int(time.time() * 1000000)
            client_order_id = new_client_order_id or f"simulated_{order_id}"
            
            # Determine execution price based on order type
            if order_type == 'MARKET':
                exec_price = self._get_simulated_execution_price(symbol, side)
            else:
                exec_price = price
                
            return {
                'orderId': order_id,
                'symbol': symbol,
                'status': 'NEW',
                'clientOrderId': client_order_id,
                'price': str(price if price else '0'),
                'avgPrice': '0.00',
                'origQty': str(quantity),
                'executedQty': '0',
                'cumQuote': '0',
                'timeInForce': time_in_force,
                'type': order_type,
                'reduceOnly': reduce_only,
                'closePosition': close_position,
                'side': side,
                'positionSide': position_side,
                'stopPrice': str(stop_price if stop_price else '0'),
                'workingType': working_type,
                'priceProtect': False,
                'origType': order_type,
                'updateTime': int(time.time() * 1000)
            }
            
        try:
            timestamp = self.get_server_time()
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'timestamp': timestamp
            }
            
            if quantity:
                params['quantity'] = quantity
                
            if price and order_type != 'MARKET':
                params['price'] = price
                
            if time_in_force and order_type != 'MARKET':
                params['timeInForce'] = time_in_force
                
            if reduce_only:
                params['reduceOnly'] = 'true'
                
            if close_position:
                params['closePosition'] = 'true'
                
            if stop_price:
                params['stopPrice'] = stop_price
                
            if working_type:
                params['workingType'] = working_type
                
            if position_side:
                params['positionSide'] = position_side
                
            if new_client_order_id:
                params['newClientOrderId'] = new_client_order_id
                
            signature = self._get_signature(params)
            params['signature'] = signature
            
            url = f"{self.base_url}/fapi/v1/order"
            response = requests.post(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return {}
            
    def _get_simulated_execution_price(self, symbol, side):
        """Get simulated execution price for market orders"""
        # Get the current market price (mid price from order book)
        order_book = self.get_order_book(symbol)
        if not order_book['asks'] or not order_book['bids']:
            return 65000.0  # Default fallback price
            
        best_ask = float(order_book['asks'][0][0])
        best_bid = float(order_book['bids'][0][0])
        mid_price = (best_ask + best_bid) / 2
        
        # Add some slippage based on side
        slippage = mid_price * 0.001  # 0.1% slippage
        if side == 'BUY':
            return mid_price + slippage
        else:  # SELL
            return mid_price - slippage
