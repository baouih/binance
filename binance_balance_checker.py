#!/usr/bin/env python3
"""
Module kiểm tra số dư tài khoản Binance

Module này tự động kiểm tra số dư tài khoản Binance Futures thực tế và cập nhật
vào cấu hình bot để đảm bảo tính chính xác trong tính toán quản lý rủi ro.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, Tuple
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("binance_balance_checker")

class BinanceBalanceChecker:
    """Kiểm tra số dư tài khoản Binance Futures"""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Khởi tạo trình kiểm tra số dư tài khoản Binance
        
        Args:
            api_key (str, optional): API Key của Binance
            api_secret (str, optional): API Secret của Binance
        """
        self.api_key = api_key or os.environ.get('BINANCE_API_KEY')
        self.api_secret = api_secret or os.environ.get('BINANCE_API_SECRET')
        self.client = None
        
        if not self.api_key or not self.api_secret:
            logger.warning("API Key hoặc API Secret không được cung cấp. Sẽ sử dụng chế độ mô phỏng.")
        else:
            try:
                self.client = Client(self.api_key, self.api_secret)
                logger.info("Đã kết nối tới Binance API.")
            except Exception as e:
                logger.error(f"Lỗi khi kết nối tới Binance API: {e}")
                self.client = None
    
    def get_spot_balance(self, asset: str = 'USDT') -> Tuple[float, bool]:
        """
        Lấy số dư tài khoản Spot cho một đồng cụ thể
        
        Args:
            asset (str): Mã đồng cần kiểm tra (mặc định là USDT)
            
        Returns:
            Tuple[float, bool]: (Số dư, Thành công hay không)
        """
        if not self.client:
            logger.warning("Không thể kết nối Binance API. Sử dụng số dư mô phỏng.")
            return 100.0, False
            
        try:
            account_info = self.client.get_account()
            
            for balance in account_info['balances']:
                if balance['asset'] == asset:
                    free_balance = float(balance['free'])
                    logger.info(f"Số dư Spot {asset}: {free_balance}")
                    return free_balance, True
            
            logger.warning(f"Không tìm thấy số dư cho {asset}")
            return 0.0, True
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API: {e}")
            return 0.0, False
        except Exception as e:
            logger.error(f"Lỗi khi lấy số dư Spot: {e}")
            return 0.0, False
    
    def get_futures_balance(self, asset: str = 'USDT') -> Tuple[float, bool]:
        """
        Lấy số dư tài khoản Futures cho một đồng cụ thể
        
        Args:
            asset (str): Mã đồng cần kiểm tra (mặc định là USDT)
            
        Returns:
            Tuple[float, bool]: (Số dư, Thành công hay không)
        """
        if not self.client:
            logger.warning("Không thể kết nối Binance API. Sử dụng số dư mô phỏng.")
            return 100.0, False
            
        try:
            # Lấy số dư futures
            futures_account = self.client.futures_account_balance()
            
            for balance in futures_account:
                if balance['asset'] == asset:
                    available_balance = float(balance['withdrawAvailable'])  # Số dư có thể sử dụng
                    logger.info(f"Số dư Futures {asset}: {available_balance}")
                    return available_balance, True
            
            logger.warning(f"Không tìm thấy số dư Futures cho {asset}")
            return 0.0, True
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API: {e}")
            return 0.0, False
        except Exception as e:
            logger.error(f"Lỗi khi lấy số dư Futures: {e}")
            return 0.0, False
            
    def get_futures_positions(self) -> Tuple[Dict, bool]:
        """
        Lấy thông tin vị thế Futures đang mở
        
        Returns:
            Tuple[Dict, bool]: (Thông tin vị thế, Thành công hay không)
        """
        if not self.client:
            logger.warning("Không thể kết nối Binance API. Không thể lấy thông tin vị thế.")
            return {}, False
            
        try:
            # Lấy thông tin vị thế
            positions = self.client.futures_position_information()
            
            # Lọc các vị thế đang mở (positionAmt != 0)
            open_positions = {}
            for position in positions:
                symbol = position['symbol']
                position_amt = float(position['positionAmt'])
                
                if position_amt != 0:
                    entry_price = float(position['entryPrice'])
                    leverage = int(position['leverage'])
                    unrealized_pnl = float(position['unRealizedProfit'])
                    margin_type = position['marginType']  # isolated hoặc cross
                    
                    open_positions[symbol] = {
                        'symbol': symbol,
                        'position_amount': position_amt,
                        'entry_price': entry_price,
                        'leverage': leverage,
                        'unrealized_pnl': unrealized_pnl,
                        'margin_type': margin_type,
                        'position_side': 'LONG' if position_amt > 0 else 'SHORT'
                    }
            
            if open_positions:
                logger.info(f"Đang có {len(open_positions)} vị thế mở: {list(open_positions.keys())}")
            else:
                logger.info("Không có vị thế nào đang mở.")
                
            return open_positions, True
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API: {e}")
            return {}, False
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin vị thế: {e}")
            return {}, False
            
    def get_futures_leverage_bracket(self, symbol: str = 'BTCUSDT') -> Tuple[Dict, bool]:
        """
        Lấy thông tin giới hạn đòn bẩy cho một symbol
        
        Args:
            symbol (str): Mã cặp giao dịch (mặc định là BTCUSDT)
            
        Returns:
            Tuple[Dict, bool]: (Thông tin giới hạn đòn bẩy, Thành công hay không)
        """
        if not self.client:
            logger.warning("Không thể kết nối Binance API. Sử dụng giới hạn đòn bẩy mặc định.")
            return {'maxLeverage': 20}, False
            
        try:
            # Lấy thông tin giới hạn đòn bẩy
            leverage_brackets = self.client.futures_leverage_bracket(symbol=symbol)
            
            # Xử lý phản hồi
            if isinstance(leverage_brackets, list) and len(leverage_brackets) > 0:
                bracket_info = leverage_brackets[0]['brackets']
                max_leverage = bracket_info[0]['initialLeverage']
                
                logger.info(f"Đòn bẩy tối đa cho {symbol}: x{max_leverage}")
                
                return {'maxLeverage': max_leverage, 'brackets': bracket_info}, True
            else:
                logger.warning(f"Không tìm thấy thông tin giới hạn đòn bẩy cho {symbol}")
                return {'maxLeverage': 20}, True  # Giá trị mặc định
                
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API: {e}")
            return {'maxLeverage': 20}, False
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin giới hạn đòn bẩy: {e}")
            return {'maxLeverage': 20}, False
            
    def auto_update_risk_config(self, config_path: str, asset: str = 'USDT', account_type: str = 'futures') -> bool:
        """
        Tự động cập nhật cấu hình rủi ro dựa trên số dư thực tế
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình rủi ro
            asset (str): Mã đồng cần kiểm tra (mặc định là USDT)
            account_type (str): Loại tài khoản ('spot' hoặc 'futures')
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        # Lấy số dư
        if account_type.lower() == 'spot':
            balance, success = self.get_spot_balance(asset)
        else:  # futures
            balance, success = self.get_futures_balance(asset)
            
        if not success:
            logger.warning("Không thể lấy số dư thực tế. Cấu hình sẽ không được cập nhật.")
            return False
            
        # Kiểm tra và cập nhật cấu hình
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                # Cập nhật số dư ban đầu
                old_balance = config.get('initial_balance', 0)
                config['initial_balance'] = balance
                config['last_updated'] = self._get_current_timestamp()
                config['auto_updated'] = True
                
                # Lưu cấu hình
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=4)
                    
                logger.info(f"Đã cập nhật số dư từ ${old_balance:.2f} thành ${balance:.2f}")
                return True
            else:
                logger.warning(f"Không tìm thấy file cấu hình: {config_path}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cấu hình: {e}")
            return False
            
    def _get_current_timestamp(self) -> str:
        """
        Lấy thời gian hiện tại dạng chuỗi
        
        Returns:
            str: Thời gian hiện tại dạng chuỗi
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    """Hàm chính để test BinanceBalanceChecker"""
    checker = BinanceBalanceChecker()
    
    print("Kiểm tra số dư tài khoản Binance:")
    
    # Kiểm tra số dư Spot
    spot_balance, spot_success = checker.get_spot_balance()
    print(f"Số dư Spot USDT: {'${:.2f}'.format(spot_balance) if spot_success else 'Không thể kiểm tra'}")
    
    # Kiểm tra số dư Futures
    futures_balance, futures_success = checker.get_futures_balance()
    print(f"Số dư Futures USDT: {'${:.2f}'.format(futures_balance) if futures_success else 'Không thể kiểm tra'}")
    
    # Kiểm tra vị thế đang mở
    positions, positions_success = checker.get_futures_positions()
    if positions_success and positions:
        print("Vị thế đang mở:")
        for symbol, position in positions.items():
            print(f"  {symbol}: {position['position_amount']} @ ${position['entry_price']:.2f}, Leverage: x{position['leverage']}")
    else:
        print("Không có vị thế nào đang mở hoặc không thể kiểm tra.")
        
    # Kiểm tra giới hạn đòn bẩy
    leverage_info, leverage_success = checker.get_futures_leverage_bracket()
    print(f"Đòn bẩy tối đa cho BTCUSDT: {'x' + str(leverage_info['maxLeverage']) if leverage_success else 'Không thể kiểm tra'}")
    
    # Tự động cập nhật cấu hình rủi ro
    config_path = "configs/risk_config.json"
    if checker.auto_update_risk_config(config_path):
        print(f"Đã cập nhật cấu hình rủi ro tại {config_path}")
    else:
        print("Không thể cập nhật cấu hình rủi ro.")

if __name__ == "__main__":
    main()