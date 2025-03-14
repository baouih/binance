#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module để quản lý cache giá của các cặp tiền, đặc biệt hữu ích cho testnet.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)

class PriceCache:
    """
    Lớp quản lý cache giá của các cặp tiền.
    - Lưu giá mới nhất vào bộ nhớ và file
    - Cung cấp giá dự phòng khi API không trả về kết quả
    - Hỗ trợ tự động cập nhật theo thời gian
    """
    
    def __init__(self, cache_file: str = 'symbol_prices_cache.json', max_age_seconds: int = 3600):
        """
        Khởi tạo PriceCache.
        
        Args:
            cache_file (str): Đường dẫn đến file cache
            max_age_seconds (int): Thời gian tối đa (giây) một giá được coi là hợp lệ
        """
        self.cache_file = cache_file
        self.max_age_seconds = max_age_seconds
        self.prices = {}
        self.last_update_time = {}
        
        # Thiết lập giá mặc định cho một số cặp phổ biến (chỉ sử dụng khi không có nguồn khác)
        self.default_prices = {
            "BTCUSDT": 81932.3, "ETHUSDT": 1895.32, "BNBUSDT": 596.111, 
            "SOLUSDT": 135.3, "ADAUSDT": 0.55, "DOGEUSDT": 0.19,
            "LTCUSDT": 86.0, "DOTUSDT": 8.7, "XRPUSDT": 0.56,
            "AVAXUSDT": 37.6, "LINKUSDT": 14.067, "ATOMUSDT": 10.4,
            "MATICUSDT": 0.95, "UNIUSDT": 8.5, "FILUSDT": 7.02,
            "AAVEUSDT": 100.2, "ICPUSDT": 12.8, "ETCUSDT": 26.3
        }
        
        # Tải cache từ file nếu có
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Tải dữ liệu cache từ file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.prices = data.get('prices', {})
                    self.last_update_time = data.get('last_update_time', {})
                    logger.info(f"Đã tải cache giá cho {len(self.prices)} symbols từ {self.cache_file}")
        except Exception as e:
            logger.error(f"Lỗi khi tải cache: {str(e)}")
            # Sử dụng giá mặc định nếu không tải được cache
            self.prices = self.default_prices.copy()
            self.last_update_time = {symbol: int(time.time()) for symbol in self.prices}
    
    def save_cache(self) -> None:
        """Lưu dữ liệu cache vào file."""
        try:
            data = {
                'prices': self.prices,
                'last_update_time': self.last_update_time,
                'saved_at': int(time.time())
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Đã lưu cache giá cho {len(self.prices)} symbols vào {self.cache_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cache: {str(e)}")
    
    def update_price(self, symbol: str, price: float) -> None:
        """
        Cập nhật giá mới cho một cặp tiền.
        
        Args:
            symbol (str): Symbol cần cập nhật
            price (float): Giá mới
        """
        self.prices[symbol] = price
        self.last_update_time[symbol] = int(time.time())
        
        # Tự động lưu cache sau khi cập nhật
        self.save_cache()
    
    def update_prices(self, price_data: Dict[str, float]) -> None:
        """
        Cập nhật giá cho nhiều cặp tiền.
        
        Args:
            price_data (Dict[str, float]): Dict với key là symbol và value là giá
        """
        for symbol, price in price_data.items():
            self.prices[symbol] = price
            self.last_update_time[symbol] = int(time.time())
        
        # Tự động lưu cache sau khi cập nhật
        self.save_cache()
    
    def get_price(self, symbol: str, fallback_to_default: bool = True) -> Optional[float]:
        """
        Lấy giá cho một cặp tiền.
        
        Args:
            symbol (str): Symbol cần lấy giá
            fallback_to_default (bool): Có sử dụng giá mặc định nếu không có cache không
            
        Returns:
            Optional[float]: Giá của symbol hoặc None nếu không có
        """
        # Kiểm tra giá trong cache
        if symbol in self.prices:
            # Kiểm tra thời gian cache
            now = int(time.time())
            if now - self.last_update_time.get(symbol, 0) <= self.max_age_seconds:
                return self.prices[symbol]
            else:
                logger.warning(f"Giá của {symbol} quá cũ: {now - self.last_update_time.get(symbol, 0)} giây")
        
        # Sử dụng giá mặc định nếu được yêu cầu
        if fallback_to_default and symbol in self.default_prices:
            logger.warning(f"Sử dụng giá mặc định cho {symbol}: {self.default_prices[symbol]}")
            return self.default_prices[symbol]
        
        return None
    
    def is_price_fresh(self, symbol: str) -> bool:
        """
        Kiểm tra xem giá cache có còn mới không.
        
        Args:
            symbol (str): Symbol cần kiểm tra
            
        Returns:
            bool: True nếu giá còn mới, False nếu không có hoặc quá cũ
        """
        if symbol not in self.prices or symbol not in self.last_update_time:
            return False
            
        now = int(time.time())
        return now - self.last_update_time[symbol] <= self.max_age_seconds
    
    def get_all_prices(self) -> Dict[str, float]:
        """
        Lấy tất cả giá hiện có trong cache.
        
        Returns:
            Dict[str, float]: Dict với key là symbol và value là giá
        """
        return self.prices.copy()
    
    def get_fresh_prices(self) -> Dict[str, float]:
        """
        Lấy tất cả giá còn mới trong cache.
        
        Returns:
            Dict[str, float]: Dict với key là symbol và value là giá
        """
        now = int(time.time())
        fresh_prices = {}
        
        for symbol, price in self.prices.items():
            if now - self.last_update_time.get(symbol, 0) <= self.max_age_seconds:
                fresh_prices[symbol] = price
                
        return fresh_prices
        
    def clear_cache(self) -> None:
        """Xóa toàn bộ cache."""
        self.prices = {}
        self.last_update_time = {}
        self.save_cache()
        logger.info("Đã xóa toàn bộ cache giá")

# Tạo instance mặc định để sử dụng trong toàn bộ ứng dụng
price_cache = PriceCache()

def update_price(symbol: str, price: float) -> None:
    """
    Cập nhật giá cho một cặp tiền trong cache toàn cục.
    
    Args:
        symbol (str): Symbol cần cập nhật
        price (float): Giá mới
    """
    price_cache.update_price(symbol, price)

def get_price(symbol: str, fallback_to_default: bool = True) -> Optional[float]:
    """
    Lấy giá cho một cặp tiền từ cache toàn cục.
    
    Args:
        symbol (str): Symbol cần lấy giá
        fallback_to_default (bool): Có sử dụng giá mặc định không
        
    Returns:
        Optional[float]: Giá của symbol hoặc None
    """
    price = price_cache.get_price(symbol, fallback_to_default)
    if price:
        logger.info(f"Lấy giá {symbol} từ cache: {price}")
    else:
        logger.warning(f"Không tìm thấy giá cho {symbol} trong cache")
    return price

def update_prices(price_data: Dict[str, float]) -> None:
    """
    Cập nhật giá cho nhiều cặp tiền trong cache toàn cục.
    
    Args:
        price_data (Dict[str, float]): Dict với key là symbol và value là giá
    """
    price_cache.update_prices(price_data)

def get_all_prices() -> Dict[str, float]:
    """
    Lấy tất cả giá từ cache toàn cục.
    
    Returns:
        Dict[str, float]: Dict với key là symbol và value là giá
    """
    return price_cache.get_all_prices()

# Tiện ích cho quy trình fetching giá
def update_prices_from_api(api, symbols: List[str]) -> Dict[str, float]:
    """
    Cập nhật giá từ API cho nhiều symbols.
    
    Args:
        api: Instance của BinanceAPI
        symbols (List[str]): Danh sách các symbols cần lấy giá
        
    Returns:
        Dict[str, float]: Dict với key là symbol và value là giá đã cập nhật
    """
    updated_prices = {}
    
    for symbol in symbols:
        try:
            # Lấy giá từ API
            ticker_data = api.futures_ticker_price(symbol)
            
            if isinstance(ticker_data, dict) and 'price' in ticker_data:
                price = float(ticker_data['price'])
                update_price(symbol, price)
                updated_prices[symbol] = price
                logger.info(f"Đã cập nhật giá {symbol}: {price}")
            else:
                logger.warning(f"Không lấy được giá {symbol} từ API")
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá {symbol}: {str(e)}")
    
    return updated_prices

if __name__ == "__main__":
    # Test module
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Tạo dữ liệu test
    test_prices = {
        "BTCUSDT": 86000.0,
        "ETHUSDT": 2170.5,
        "BNBUSDT": 595.75
    }
    
    # Cập nhật giá
    update_prices(test_prices)
    
    # Lấy giá
    btc_price = get_price("BTCUSDT")
    eth_price = get_price("ETHUSDT")
    sol_price = get_price("SOLUSDT")  # Không có trong test_prices
    
    logger.info(f"Giá BTCUSDT: {btc_price}")
    logger.info(f"Giá ETHUSDT: {eth_price}")
    logger.info(f"Giá SOLUSDT: {sol_price}")
    
    # Lấy tất cả giá
    all_prices = get_all_prices()
    logger.info(f"Tất cả giá: {all_prices}")