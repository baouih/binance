#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Module kết nối price_validator với hệ thống giao dịch chính
'''

import logging
import importlib
import inspect
import sys
from typing import Dict, Any, Optional, List, Tuple, Union

logger = logging.getLogger(__name__)

class PriceValidationIntegrator:
    '''
    Lớp tích hợp hệ thống xác thực giá vào hệ thống giao dịch chính.
    Được thiết kế để có thể hoạt động kể cả khi các module xác thực giá không tồn tại.
    '''
    
    def __init__(self):
        self.price_validator_available = False
        self.price_monitor_available = False
        self.price_cache_available = False
        
        # Thử import các module
        try:
            import price_validator
            self.price_validator = price_validator
            self.price_validator_available = True
            logger.info("Đã tìm thấy và tích hợp price_validator")
        except ImportError:
            logger.warning("Không tìm thấy module price_validator, sẽ sử dụng chức năng mặc định")
            self.price_validator = None
        
        try:
            import price_monitor
            self.price_monitor = price_monitor
            self.price_monitor_available = True
            self.monitor_instance = None
            logger.info("Đã tìm thấy và tích hợp price_monitor")
        except ImportError:
            logger.warning("Không tìm thấy module price_monitor, sẽ không giám sát giá")
            self.price_monitor = None
        
        try:
            import prices_cache
            self.prices_cache = prices_cache
            self.price_cache_available = True
            logger.info("Đã tìm thấy và tích hợp prices_cache")
        except ImportError:
            logger.warning("Không tìm thấy module prices_cache, sẽ không cache giá")
            self.prices_cache = None
    
    def get_price(self, symbol: str, api=None) -> Tuple[float, bool]:
        '''
        Lấy giá đã được xác thực.
        
        Args:
            symbol (str): Symbol cần lấy giá
            api: Instance của BinanceAPI
            
        Returns:
            Tuple[float, bool]: (Giá, True nếu đáng tin cậy)
        '''
        if self.price_validator_available:
            try:
                return self.price_validator.get_verified_price(symbol, api)
            except Exception as e:
                logger.error(f"Lỗi khi lấy giá đã xác thực: {str(e)}")
        
        # Fallback: Lấy giá trực tiếp từ API
        if api:
            try:
                ticker_data = api.futures_ticker_price(symbol)
                if isinstance(ticker_data, dict) and 'price' in ticker_data:
                    price = float(ticker_data['price'])
                    return price, True
            except Exception as e:
                logger.error(f"Lỗi khi lấy giá từ API: {str(e)}")
        
        # Không lấy được giá
        logger.warning(f"Không thể lấy giá cho {symbol}")
        return None, False
    
    def cache_price(self, symbol: str, price: float) -> None:
        '''
        Lưu giá vào cache.
        
        Args:
            symbol (str): Symbol cần lưu
            price (float): Giá cần lưu
        '''
        if self.price_cache_available:
            try:
                self.prices_cache.update_price(symbol, price)
            except Exception as e:
                logger.error(f"Lỗi khi cache giá: {str(e)}")
    
    def get_cached_price(self, symbol: str) -> Optional[float]:
        '''
        Lấy giá từ cache.
        
        Args:
            symbol (str): Symbol cần lấy giá
            
        Returns:
            Optional[float]: Giá từ cache hoặc None
        '''
        if self.price_cache_available:
            try:
                return self.prices_cache.get_price(symbol)
            except Exception as e:
                logger.error(f"Lỗi khi lấy giá từ cache: {str(e)}")
        
        return None
    
    def safe_create_order(self, api, symbol: str, side: str, order_type: str, **kwargs) -> Dict[str, Any]:
        '''
        Tạo lệnh an toàn với xác thực giá.
        
        Args:
            api: Instance của BinanceAPI
            symbol (str): Symbol giao dịch
            side (str): Phía giao dịch (BUY/SELL)
            order_type (str): Loại lệnh
            **kwargs: Tham số khác
            
        Returns:
            Dict[str, Any]: Kết quả API hoặc lỗi
        '''
        if self.price_validator_available:
            try:
                return self.price_validator.safe_create_order(api, symbol, side, order_type, **kwargs)
            except Exception as e:
                logger.error(f"Lỗi khi tạo lệnh an toàn: {str(e)}")
        
        # Fallback: Sử dụng phương thức gốc
        if hasattr(api, 'create_order_with_position_side'):
            return api.create_order_with_position_side(
                symbol=symbol,
                side=side,
                order_type=order_type,
                **kwargs
            )
        else:
            return api.create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                **kwargs
            )
    
    def is_trading_enabled(self) -> bool:
        '''
        Kiểm tra xem giao dịch có được phép không.
        
        Returns:
            bool: True nếu giao dịch được phép, False nếu không
        '''
        if self.price_validator_available:
            try:
                return self.price_validator.is_trading_enabled()
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra trạng thái giao dịch: {str(e)}")
        
        # Mặc định là được phép
        return True
    
    def start_price_monitor(self, api=None) -> None:
        '''
        Khởi động monitor giám sát giá.
        
        Args:
            api: Instance của BinanceAPI
        '''
        if self.price_monitor_available and not self.monitor_instance:
            try:
                self.monitor_instance = self.price_monitor.start_price_monitor(api)
                logger.info("Đã khởi động price_monitor")
            except Exception as e:
                logger.error(f"Lỗi khi khởi động price_monitor: {str(e)}")
    
    def stop_price_monitor(self) -> None:
        '''Dừng monitor giám sát giá.'''
        if self.monitor_instance:
            try:
                self.monitor_instance.stop()
                self.monitor_instance = None
                logger.info("Đã dừng price_monitor")
            except Exception as e:
                logger.error(f"Lỗi khi dừng price_monitor: {str(e)}")

# Tạo instance mặc định sẵn sàng để sử dụng
price_integrator = PriceValidationIntegrator()

# Các hàm tiện ích để dễ dàng sử dụng
def get_verified_price(symbol: str, api=None) -> Tuple[float, bool]:
    '''Lấy giá đã được xác thực từ nhiều nguồn.'''
    return price_integrator.get_price(symbol, api)

def safe_create_order(api, symbol: str, side: str, order_type: str, **kwargs) -> Dict[str, Any]:
    '''Tạo lệnh với cơ chế bảo vệ giá.'''
    return price_integrator.safe_create_order(api, symbol, side, order_type, **kwargs)

def is_trading_enabled() -> bool:
    '''Kiểm tra xem giao dịch có được phép không.'''
    return price_integrator.is_trading_enabled()

def cache_price(symbol: str, price: float) -> None:
    '''Lưu giá vào cache.'''
    price_integrator.cache_price(symbol, price)

def get_cached_price(symbol: str) -> Optional[float]:
    '''Lấy giá từ cache.'''
    return price_integrator.get_cached_price(symbol)

def start_price_monitor(api=None) -> None:
    '''Khởi động monitor giám sát giá.'''
    price_integrator.start_price_monitor(api)

def stop_price_monitor() -> None:
    '''Dừng monitor giám sát giá.'''
    price_integrator.stop_price_monitor()

if __name__ == "__main__":
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test module
    logger.info("Kiểm tra module price_integration")
    logger.info(f"price_validator có sẵn: {price_integrator.price_validator_available}")
    logger.info(f"price_monitor có sẵn: {price_integrator.price_monitor_available}")
    logger.info(f"prices_cache có sẵn: {price_integrator.price_cache_available}")
    
    # Test các chức năng cơ bản
    try:
        from binance_api import BinanceAPI
        api = BinanceAPI()
        
        # Danh sách các cặp tiền cần kiểm tra
        symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
            "DOGEUSDT", "LTCUSDT", "DOTUSDT", "XRPUSDT", "AVAXUSDT",
            "LINKUSDT", "MATICUSDT", "UNIUSDT"
        ]
        
        logger.info("=== Kiểm tra giá tất cả các cặp tiền ===")
        for symbol in symbols:
            try:
                price, is_reliable = get_verified_price(symbol, api)
                logger.info(f"Giá xác thực {symbol}: {price}, Đáng tin cậy: {is_reliable}")
                # Cache lại giá nếu tin cậy
                if is_reliable and price:
                    cache_price(symbol, price)
            except Exception as ex:
                logger.error(f"Lỗi khi kiểm tra {symbol}: {str(ex)}")
        
        logger.info("=== Khởi động price_monitor ===")
        start_price_monitor(api)
        
        import time
        logger.info("Đợi 5 giây để price_monitor hoạt động...")
        time.sleep(5)
        
        logger.info("=== Dừng price_monitor ===")
        stop_price_monitor()
    except Exception as e:
        logger.error(f"Lỗi khi test: {str(e)}")