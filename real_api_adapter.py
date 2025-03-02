#!/usr/bin/env python3
"""
Real API Adapter - Truy cập và xử lý dữ liệu thực từ Binance API

Module này cung cấp các phương thức tích hợp với Binance API, 
đảm bảo rằng hệ thống luôn sử dụng dữ liệu thực thay vì dữ liệu demo.
"""

import os
import logging
import datetime
import time
import json
from typing import Dict, List, Optional, Union, Any, Tuple

try:
    from binance.client import Client
except ImportError:
    # Cài đặt python-binance nếu chưa có
    import subprocess
    subprocess.check_call(["pip", "install", "python-binance"])
    from binance.client import Client

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('real_api_adapter')

class RealAPIAdapter:
    """
    Lớp adapter kết nối với Binance API để lấy dữ liệu thực.
    Lớp này đảm bảo không sử dụng dữ liệu giả lập.
    """
    
    def __init__(self, testnet: bool = True):
        """
        Khởi tạo RealAPIAdapter
        
        Args:
            testnet (bool): Có sử dụng testnet hay không
        """
        self.api_key = os.environ.get('BINANCE_API_KEY', '')
        self.api_secret = os.environ.get('BINANCE_API_SECRET', '')
        self.testnet = testnet
        self.client = None
        self.initialize_client()
        
    def initialize_client(self) -> bool:
        """
        Khởi tạo Binance API client
        
        Returns:
            bool: True nếu khởi tạo thành công, False nếu không
        """
        try:
            # Che giấu API key trong log
            masked_key = f"{self.api_key[:5]}...{self.api_key[-5:] if len(self.api_key) > 10 else ''}"
            logger.info(f"Khởi tạo Binance API client với key: {masked_key}, testnet: {self.testnet}")
            
            # Import Binance client
            from binance.client import Client
            self.client = Client(self.api_key, self.api_secret, testnet=self.testnet)
            
            # Kiểm tra kết nối bằng cách lấy thông tin máy chủ
            server_time = self.client.get_server_time()
            if server_time:
                logger.info(f"Kết nối Binance API thành công. Server time: {server_time}")
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khởi tạo Binance API client: {e}")
            return False
    
    def get_market_data(self) -> Dict:
        """
        Lấy dữ liệu thị trường từ Binance API
        
        Returns:
            Dict: Dữ liệu thị trường
        """
        try:
            if not self.client:
                if not self.initialize_client():
                    raise Exception("Không thể khởi tạo Binance API client")
            
            # Danh sách các cặp tiền cần lấy dữ liệu
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
            
            # Chuẩn bị dữ liệu kết quả
            market_data = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_real_data': True
            }
            
            # Lấy giá hiện tại cho tất cả các cặp tiền
            tickers = self.client.get_all_tickers()
            
            # Lấy dữ liệu 24h cho tất cả các cặp tiền
            tickers_24h = self.client.get_ticker()
            
            # Xử lý dữ liệu giá và % thay đổi cho các cặp quan tâm
            for symbol in symbols:
                # Lấy giá hiện tại
                price = next((t['price'] for t in tickers if t['symbol'] == symbol), '0')
                
                # Lấy dữ liệu 24h
                ticker_24h = next((t for t in tickers_24h if t['symbol'] == symbol), {'priceChangePercent': '0'})
                
                # Symbol dạng lowercase cho mapping vào kết quả
                symbol_key = symbol.replace('USDT', '').lower()
                
                # Thêm vào kết quả
                market_data[f'{symbol_key}_price'] = float(price)
                market_data[f'{symbol_key}_change_24h'] = float(ticker_24h['priceChangePercent'])
            
            # Thêm thông tin sentiment và market regime (tạm thời để trống, sẽ được cập nhật từ module phân tích)
            market_data['sentiment'] = {
                'value': 50,  # Giá trị trung lập
                'state': 'info', 
                'change': 0.0,
                'trend': 'neutral'
            }
            
            market_data['market_regime'] = {}
            for symbol in symbols:
                symbol_key = symbol.replace('USDT', '')
                market_data['market_regime'][symbol] = 'Analyzing' # Đang phân tích
            
            return market_data
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu thị trường: {e}")
            raise
    
    def get_account_data(self) -> Dict:
        """
        Lấy dữ liệu tài khoản từ Binance API
        
        Returns:
            Dict: Dữ liệu tài khoản
        """
        try:
            if not self.client:
                if not self.initialize_client():
                    raise Exception("Không thể khởi tạo Binance API client")
            
            # Dành cho tài khoản Spot
            account_info = self.client.get_account()
            
            # Tính tổng tài sản
            total_balance = 0.0
            free_balance = 0.0
            positions = []
            
            # Xử lý thông tin tài khoản spot
            if 'balances' in account_info:
                for asset in account_info['balances']:
                    asset_free = float(asset['free'])
                    asset_locked = float(asset['locked'])
                    
                    # Chỉ tính những tài sản có giá trị
                    if asset_free > 0 or asset_locked > 0:
                        # Nếu là USDT, tính trực tiếp
                        if asset['asset'] == 'USDT':
                            asset_value = asset_free + asset_locked
                            free_balance += asset_free
                        else:
                            # Đối với các tài sản khác, cố gắng lấy giá để quy đổi sang USDT
                            try:
                                # Lấy giá hiện tại của tài sản này sang USDT
                                ticker_price = self.client.get_symbol_ticker(symbol=f"{asset['asset']}USDT")
                                asset_price = float(ticker_price['price'])
                                
                                # Tính giá trị quy đổi sang USDT
                                asset_value = (asset_free + asset_locked) * asset_price
                                free_balance += asset_free * asset_price
                                
                                # Nếu có tài sản khóa, coi như đang trong vị thế
                                if asset_locked > 0 and asset['asset'] != 'USDT':
                                    position_id = f"spot_{asset['asset']}"
                                    position = {
                                        "id": position_id,
                                        "symbol": f"{asset['asset']}USDT",
                                        "type": "SPOT",
                                        "entry_price": 0.0,  # Không có thông tin entry price trong spot
                                        "current_price": asset_price,
                                        "quantity": asset_locked,
                                        "pnl": 0.0,  # Không thể tính PnL chính xác cho spot
                                        "pnl_percent": 0.0,
                                        "leverage": 1,
                                        "stop_loss": 0.0,
                                        "take_profit": 0.0,
                                        "entry_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                                    }
                                    positions.append(position)
                            except Exception as e:
                                logger.warning(f"Lỗi khi tính giá trị tài sản {asset['asset']}: {e}")
                                asset_value = 0
                        
                        total_balance += asset_value
            
            # Format lại thông tin tài khoản để trả về
            account_data = {
                'balance': round(total_balance, 2),
                'equity': round(total_balance, 2),  # Trong spot, balance và equity giống nhau
                'free_balance': round(free_balance, 2),
                'margin': 0,  # Spot không có margin
                'leverage': 1,  # Spot không có leverage
                'positions': positions,
                'is_real_data': True
            }
            
            return account_data
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu tài khoản: {e}")
            raise

    def get_futures_account_data(self) -> Dict:
        """
        Lấy dữ liệu tài khoản futures từ Binance API
        
        Returns:
            Dict: Dữ liệu tài khoản futures
        """
        try:
            if not self.client:
                if not self.initialize_client():
                    raise Exception("Không thể khởi tạo Binance API client")
            
            # Lấy thông tin tài khoản futures
            futures_account = self.client.futures_account()
            
            # Tính tổng tài sản
            total_balance = float(futures_account.get('totalWalletBalance', 0))
            total_margin = float(futures_account.get('totalInitialMargin', 0))
            total_pnl = float(futures_account.get('totalUnrealizedProfit', 0))
            
            # Lấy danh sách vị thế
            positions = []
            for position in futures_account.get('positions', []):
                position_amt = float(position.get('positionAmt', 0))
                
                # Bỏ qua các vị thế không có lượng
                if position_amt == 0:
                    continue
                
                entry_price = float(position.get('entryPrice', 0))
                mark_price = float(position.get('markPrice', 0))
                symbol = position.get('symbol', '')
                leverage = int(position.get('leverage', 1))
                
                # Tính PnL
                if position_amt > 0:  # Long position
                    pnl = position_amt * (mark_price - entry_price)
                    position_type = 'LONG'
                else:  # Short position
                    pnl = -position_amt * (entry_price - mark_price)
                    position_type = 'SHORT'
                
                # Tính % PnL
                if entry_price > 0 and position_amt != 0:
                    pnl_percent = (pnl / (abs(position_amt) * entry_price)) * 100
                else:
                    pnl_percent = 0
                
                # Format lại vị thế
                pos = {
                    "id": f"futures_{symbol}",
                    "symbol": symbol,
                    "type": position_type,
                    "entry_price": entry_price,
                    "current_price": mark_price,
                    "quantity": abs(position_amt),
                    "pnl": round(pnl, 2),
                    "pnl_percent": round(pnl_percent, 2),
                    "leverage": leverage,
                    "stop_loss": 0.0,  # Không có thông tin này từ API
                    "take_profit": 0.0,  # Không có thông tin này từ API
                    "entry_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M')  # Không có thông tin chính xác
                }
                positions.append(pos)
            
            # Format lại thông tin tài khoản để trả về
            account_data = {
                'balance': round(total_balance, 2),
                'equity': round(total_balance + total_pnl, 2),
                'free_balance': round(total_balance - total_margin, 2),
                'margin': round(total_margin, 2),
                'leverage': int(futures_account.get('leverage', 1)),
                'positions': positions,
                'is_real_data': True
            }
            
            return account_data
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu tài khoản futures: {e}")
            raise

# Singleton instance
_adapter_instance = None

def get_adapter(testnet: bool = True) -> RealAPIAdapter:
    """
    Lấy instance của RealAPIAdapter (singleton pattern)
    
    Args:
        testnet (bool): Có sử dụng testnet hay không
        
    Returns:
        RealAPIAdapter: Instance của adapter
    """
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = RealAPIAdapter(testnet=testnet)
    return _adapter_instance

def get_market_data(testnet: bool = True) -> Dict:
    """
    Lấy dữ liệu thị trường từ Binance API
    
    Args:
        testnet (bool): Có sử dụng testnet hay không
        
    Returns:
        Dict: Dữ liệu thị trường
    """
    adapter = get_adapter(testnet)
    return adapter.get_market_data()

def get_account_data(testnet: bool = True, account_type: str = 'spot') -> Dict:
    """
    Lấy dữ liệu tài khoản từ Binance API
    
    Args:
        testnet (bool): Có sử dụng testnet hay không
        account_type (str): Loại tài khoản ('spot' hoặc 'futures')
        
    Returns:
        Dict: Dữ liệu tài khoản
    """
    adapter = get_adapter(testnet)
    if account_type.lower() == 'futures':
        return adapter.get_futures_account_data()
    else:
        return adapter.get_account_data()

# Test function
def main():
    """
    Hàm chính để test module
    """
    # Lấy dữ liệu thị trường
    try:
        market_data = get_market_data(testnet=True)
        print("Market data:", market_data)
    except Exception as e:
        print(f"Error getting market data: {e}")
    
    # Lấy dữ liệu tài khoản
    try:
        account_data = get_account_data(testnet=True)
        print("Account data:", account_data)
    except Exception as e:
        print(f"Error getting account data: {e}")

if __name__ == "__main__":
    main()