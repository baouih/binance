#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module để kiểm tra và xác thực tính đáng tin cậy của giá từ API Binance.
"""

import os
import json
import time
import logging
import requests
from typing import Dict, Any, Optional, List, Union, Tuple

# Import module cache giá
from prices_cache import price_cache, update_price, get_price

logger = logging.getLogger(__name__)

class PriceValidator:
    """
    Lớp xác thực tính đáng tin cậy của giá crypto.
    Giúp đảm bảo dữ liệu giá từ API sử dụng để tạo lệnh là đáng tin cậy.
    """
    
    def __init__(self, max_price_age_seconds: int = 60, max_deviation_percent: float = 5.0):
        """
        Khởi tạo PriceValidator.
        
        Args:
            max_price_age_seconds (int): Thời gian tối đa (giây) giá được coi là mới
            max_deviation_percent (float): Độ chênh lệch tối đa (%) giữa các nguồn
        """
        self.max_price_age = max_price_age_seconds
        self.max_deviation = max_deviation_percent / 100.0
        self.unreliable_symbols = set()
        self.last_check_time = {}
        self.trading_enabled = True
        
    def get_binance_spot_price(self, symbol: str) -> Optional[float]:
        """
        Lấy giá từ Binance Spot API (nguồn thứ 2).
        
        Args:
            symbol (str): Symbol cần lấy giá
            
        Returns:
            Optional[float]: Giá hoặc None nếu không lấy được
        """
        try:
            # Binance Spot API
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'price' in data:
                    return float(data['price'])
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá Binance Spot cho {symbol}: {str(e)}")
        
        return None
        
    def get_other_exchange_price(self, symbol: str) -> Optional[float]:
        """
        Lấy giá từ sàn khác (nguồn thứ 3).
        Ví dụ: OKX, Bybit, hoặc CoinGecko/CoinMarketCap API.
        
        Args:
            symbol (str): Symbol cần lấy giá
            
        Returns:
            Optional[float]: Giá hoặc None nếu không lấy được
        """
        # Đối với một số cặp phổ biến, chúng ta có thể sử dụng CoinGecko API
        if symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
            try:
                coin_id_map = {
                    "BTCUSDT": "bitcoin",
                    "ETHUSDT": "ethereum",
                    "BNBUSDT": "binancecoin"
                }
                
                coin_id = coin_id_map.get(symbol)
                if not coin_id:
                    return None
                    
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if coin_id in data and 'usd' in data[coin_id]:
                        return float(data[coin_id]['usd'])
            except Exception as e:
                logger.error(f"Lỗi khi lấy giá CoinGecko cho {symbol}: {str(e)}")
        
        return None
    
    def get_price_from_multiple_sources(self, symbol: str, api: Any = None) -> Dict[str, Optional[float]]:
        """
        Lấy giá từ nhiều nguồn khác nhau.
        
        Args:
            symbol (str): Symbol cần lấy giá
            api: Instance của BinanceAPI nếu có
            
        Returns:
            Dict[str, Optional[float]]: Dict với key là nguồn và value là giá
        """
        prices = {
            'futures_api': None,
            'spot_api': None,
            'other_exchange': None,
            'cache': get_price(symbol, fallback_to_default=False)
        }
        
        # Nguồn 1: Binance Futures API
        if api:
            try:
                ticker_data = api.futures_ticker_price(symbol)
                if isinstance(ticker_data, dict) and 'price' in ticker_data:
                    prices['futures_api'] = float(ticker_data['price'])
            except Exception as e:
                logger.error(f"Lỗi khi lấy giá Futures API cho {symbol}: {str(e)}")
        
        # Nguồn 2: Binance Spot API
        prices['spot_api'] = self.get_binance_spot_price(symbol)
        
        # Nguồn 3: Exchange khác hoặc data provider
        prices['other_exchange'] = self.get_other_exchange_price(symbol)
        
        return prices
    
    def calculate_deviation(self, price1: float, price2: float) -> float:
        """
        Tính toán độ chênh lệch giữa hai giá.
        
        Args:
            price1 (float): Giá thứ nhất
            price2 (float): Giá thứ hai
            
        Returns:
            float: Độ chênh lệch phần trăm
        """
        return abs(price1 - price2) / price1
    
    def is_price_reliable(self, symbol: str, price: float, reference_prices: Dict[str, Optional[float]] = None) -> bool:
        """
        Kiểm tra xem giá có đáng tin cậy không dựa trên nhiều tiêu chí.
        
        Args:
            symbol (str): Symbol cần kiểm tra
            price (float): Giá cần kiểm tra
            reference_prices (Dict[str, Optional[float]]): Giá từ các nguồn khác nếu đã có
            
        Returns:
            bool: True nếu giá đáng tin cậy, False nếu không
        """
        # Kiểm tra giá âm hoặc bằng 0
        if price <= 0:
            logger.warning(f"Giá không hợp lệ cho {symbol}: {price} <= 0")
            return False
        
        # Lấy giá từ các nguồn khác nếu chưa có
        if not reference_prices:
            reference_prices = {
                'spot_api': self.get_binance_spot_price(symbol),
                'other_exchange': self.get_other_exchange_price(symbol),
                'cache': get_price(symbol, fallback_to_default=False)
            }
        
        # Đếm số nguồn có giá
        valid_sources = 0
        for source, ref_price in reference_prices.items():
            if ref_price and ref_price > 0:
                valid_sources += 1
                
                # Kiểm tra độ chênh lệch
                deviation = self.calculate_deviation(price, ref_price)
                if deviation > self.max_deviation:
                    logger.warning(f"Độ chênh lệch giá {symbol} quá cao so với nguồn {source}: {deviation*100:.2f}% > {self.max_deviation*100:.2f}%")
                    return False
        
        # Nếu có ít nhất một nguồn khác xác nhận giá
        return valid_sources > 0
    
    def get_verified_price(self, symbol: str, api: Any = None) -> Tuple[Optional[float], bool]:
        """
        Lấy giá đã được xác thực từ nhiều nguồn.
        
        Args:
            symbol (str): Symbol cần lấy giá
            api: Instance của BinanceAPI nếu có
            
        Returns:
            Tuple[Optional[float], bool]: (Giá đã được xác thực hoặc None, True nếu đáng tin cậy)
        """
        # Lấy giá từ nhiều nguồn
        prices = self.get_price_from_multiple_sources(symbol, api)
        
        # Ghi log tất cả giá từ các nguồn
        log_msg = f"Giá {symbol} từ các nguồn: "
        log_msg += f"Futures={prices['futures_api']}, "
        log_msg += f"Spot={prices['spot_api']}, "
        log_msg += f"Other={prices['other_exchange']}, "
        log_msg += f"Cache={prices['cache']}"
        logger.info(log_msg)
        
        # Ưu tiên sử dụng giá từ Futures API nếu có
        if prices['futures_api']:
            primary_price = prices['futures_api']
            is_reliable = self.is_price_reliable(symbol, primary_price, prices)
            
            if is_reliable:
                # Cập nhật cache nếu giá đáng tin cậy
                update_price(symbol, primary_price)
                return primary_price, True
        
        # Nếu không có giá từ Futures API hoặc không đáng tin cậy,
        # thử với giá từ Spot API
        if prices['spot_api']:
            spot_price = prices['spot_api']
            is_reliable = self.is_price_reliable(symbol, spot_price, prices)
            
            if is_reliable:
                update_price(symbol, spot_price)
                return spot_price, True
        
        # Nếu vẫn không có giá đáng tin cậy, sử dụng giá từ cache
        cache_price = prices['cache']
        if cache_price:
            logger.warning(f"Sử dụng giá cache cho {symbol}: {cache_price} (không có giá đáng tin cậy từ API)")
            return cache_price, False
        
        # Không có giá
        logger.error(f"Không thể lấy giá cho {symbol} từ bất kỳ nguồn nào")
        return None, False
    
    def update_trading_status(self, max_unreliable_symbols: int = 3) -> bool:
        """
        Cập nhật trạng thái giao dịch dựa trên số symbols không đáng tin cậy.
        
        Args:
            max_unreliable_symbols (int): Số lượng tối đa symbols không đáng tin cậy được chấp nhận
            
        Returns:
            bool: True nếu giao dịch được phép, False nếu không
        """
        if len(self.unreliable_symbols) >= max_unreliable_symbols:
            if self.trading_enabled:
                logger.critical(f"Đã tạm dừng giao dịch: {len(self.unreliable_symbols)} symbols không đáng tin cậy")
                self.trading_enabled = False
        else:
            if not self.trading_enabled:
                logger.info(f"Đã kích hoạt lại giao dịch: Chỉ có {len(self.unreliable_symbols)} symbols không đáng tin cậy")
                self.trading_enabled = True
                
        return self.trading_enabled

    def mark_symbol_reliability(self, symbol: str, is_reliable: bool) -> None:
        """
        Đánh dấu độ tin cậy của một symbol.
        
        Args:
            symbol (str): Symbol cần đánh dấu
            is_reliable (bool): True nếu đáng tin cậy, False nếu không
        """
        self.last_check_time[symbol] = int(time.time())
        
        if is_reliable:
            if symbol in self.unreliable_symbols:
                self.unreliable_symbols.remove(symbol)
                logger.info(f"Symbol {symbol} đã trở lại trạng thái đáng tin cậy")
        else:
            self.unreliable_symbols.add(symbol)
            logger.warning(f"Symbol {symbol} đã được đánh dấu là không đáng tin cậy")
            
        self.update_trading_status()
    
    def safe_create_order(self, api, symbol: str, side: str, order_type: str, 
                         quantity: float = None, price: float = None, 
                         stop_price: float = None, usd_value: float = None, 
                         position_side: str = None, **kwargs) -> Dict[str, Any]:
        """
        Tạo lệnh với cơ chế bảo vệ giá.
        
        Args:
            api: Instance của BinanceAPI
            symbol (str): Symbol giao dịch
            side (str): Phía giao dịch (BUY/SELL)
            order_type (str): Loại lệnh
            quantity (float): Số lượng
            price (float): Giá (với lệnh limit)
            stop_price (float): Giá kích hoạt (với lệnh stop)
            usd_value (float): Giá trị USD
            position_side (str): Vị thế (LONG/SHORT)
            **kwargs: Tham số khác
            
        Returns:
            Dict[str, Any]: Kết quả API hoặc lỗi
        """
        # Không cần kiểm tra giá với lệnh MARKET (sẽ dùng giá thị trường thực tế)
        if order_type == "MARKET":
            # Chỉ cần tính toán số lượng dựa trên USD value nếu cần
            if not quantity and usd_value:
                verified_price, is_reliable = self.get_verified_price(symbol, api)
                
                if not verified_price:
                    return {
                        "error": f"Không thể tạo lệnh {side} {symbol}: Không có giá đáng tin cậy để tính số lượng"
                    }
                
                # Tính số lượng
                if hasattr(api, 'calculate_min_quantity'):
                    quantity = api.calculate_min_quantity(symbol, usd_value)
                else:
                    # Fallback nếu không có hàm calculate_min_quantity
                    quantity = usd_value / verified_price
                    # Làm tròn xuống 3 chữ số thập phân
                    quantity = round(quantity, 3)
                
                if not quantity:
                    return {
                        "error": f"Không thể tạo lệnh {side} {symbol}: Không thể tính số lượng"
                    }
                    
            # Tạo lệnh market
            return api.create_order_with_position_side(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                position_side=position_side,
                **kwargs
            )
        
        # Đối với lệnh limit và có stop_price, cần kiểm tra giá
        # Đây là các lệnh TP/SL, OCO, và lệnh limit bình thường
        else:
            # Với lệnh stop hoặc take profit, kiểm tra giá thực tế
            if order_type in ['STOP', 'STOP_MARKET', 'TAKE_PROFIT', 'TAKE_PROFIT_MARKET', 'LIMIT']:
                if not price and not stop_price:
                    return {
                        "error": f"Không thể tạo lệnh {order_type} {side} {symbol}: Không có giá/stop_price"
                    }
                
                # Lấy giá hiện tại để xác minh
                current_price, is_reliable = self.get_verified_price(symbol, api)
                
                if not current_price:
                    return {
                        "error": f"Không thể tạo lệnh {order_type} {side} {symbol}: Không có giá hiện tại để xác minh"
                    }
                
                # Kiểm tra giá stop có hợp lý không
                if stop_price:
                    # Đối với lệnh stop buy, giá kích hoạt phải cao hơn giá hiện tại
                    if side == 'BUY' and order_type in ['STOP', 'STOP_MARKET']:
                        if stop_price <= current_price:
                            logger.warning(f"Điều chỉnh stop_price cho lệnh {order_type} {side} {symbol}: {stop_price} -> {current_price * 1.01}")
                            stop_price = current_price * 1.01  # Điều chỉnh lên 1%
                    
                    # Đối với lệnh stop sell, giá kích hoạt phải thấp hơn giá hiện tại
                    elif side == 'SELL' and order_type in ['STOP', 'STOP_MARKET']:
                        if stop_price >= current_price:
                            logger.warning(f"Điều chỉnh stop_price cho lệnh {order_type} {side} {symbol}: {stop_price} -> {current_price * 0.99}")
                            stop_price = current_price * 0.99  # Điều chỉnh xuống 1%
                
                # Kiểm tra giá limit có hợp lý không
                if price and order_type == 'LIMIT':
                    # Đối với lệnh buy limit, giá đặt phải thấp hơn giá hiện tại
                    if side == 'BUY' and price >= current_price:
                        logger.warning(f"Điều chỉnh price cho lệnh {order_type} {side} {symbol}: {price} -> {current_price * 0.99}")
                        price = current_price * 0.99  # Điều chỉnh xuống 1%
                    
                    # Đối với lệnh sell limit, giá đặt phải cao hơn giá hiện tại
                    elif side == 'SELL' and price <= current_price:
                        logger.warning(f"Điều chỉnh price cho lệnh {order_type} {side} {symbol}: {price} -> {current_price * 1.01}")
                        price = current_price * 1.01  # Điều chỉnh lên 1%
                
                # Tính số lượng nếu cần
                if not quantity and usd_value:
                    if hasattr(api, 'calculate_min_quantity'):
                        quantity = api.calculate_min_quantity(symbol, usd_value)
                    else:
                        quantity = usd_value / current_price
                        quantity = round(quantity, 3)
                
                if not quantity:
                    return {
                        "error": f"Không thể tạo lệnh {order_type} {side} {symbol}: Không thể tính số lượng"
                    }
            
            # Tạo lệnh với thông số đã kiểm tra
            params = {
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "quantity": quantity,
                "position_side": position_side
            }
            
            if price:
                params["price"] = price
                
            if stop_price:
                params["stop_price"] = stop_price
                
            # Thêm các tham số bổ sung
            for key, value in kwargs.items():
                params[key] = value
                
            # Ghi log
            logger.info(f"Tạo lệnh {order_type} {side} {symbol} với thông số đã xác minh: {params}")
                
            return api.create_order_with_position_side(**params)

# Tạo instance mặc định để sử dụng trong toàn bộ ứng dụng
price_validator = PriceValidator()

def get_verified_price(symbol: str, api: Any = None) -> Tuple[Optional[float], bool]:
    """
    Lấy giá đã được xác thực từ nhiều nguồn.
    
    Args:
        symbol (str): Symbol cần lấy giá
        api: Instance của BinanceAPI nếu có
        
    Returns:
        Tuple[Optional[float], bool]: (Giá đã được xác thực, True nếu đáng tin cậy)
    """
    return price_validator.get_verified_price(symbol, api)

def safe_create_order(api, symbol: str, side: str, order_type: str, **kwargs) -> Dict[str, Any]:
    """
    Tạo lệnh với cơ chế bảo vệ giá.
    
    Args:
        api: Instance của BinanceAPI
        symbol (str): Symbol giao dịch
        side (str): Phía giao dịch (BUY/SELL)
        order_type (str): Loại lệnh
        **kwargs: Tham số khác
        
    Returns:
        Dict[str, Any]: Kết quả API hoặc lỗi
    """
    return price_validator.safe_create_order(api, symbol, side, order_type, **kwargs)

def is_trading_enabled() -> bool:
    """
    Kiểm tra xem giao dịch có được phép không.
    
    Returns:
        bool: True nếu giao dịch được phép, False nếu không
    """
    return price_validator.trading_enabled

if __name__ == "__main__":
    # Test module
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test với một số symbol
    for symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
        price, is_reliable = get_verified_price(symbol)
        if price:
            logger.info(f"Giá {symbol}: {price} (đáng tin cậy: {is_reliable})")
        else:
            logger.warning(f"Không thể lấy giá cho {symbol}")