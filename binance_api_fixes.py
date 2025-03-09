#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cải tiến cho Binance API để khắc phục các vấn đề tạo lệnh

1. Xử lý đúng chế độ hedge mode (dual position side)
2. Loại bỏ tham số reduceOnly khi đã chỉ định positionSide
3. Đảm bảo giá trị lệnh đáp ứng yêu cầu tối thiểu (100 USDT)
4. Xử lý lỗi định dạng tham số của API
"""

import sys
import json
import logging
import time
import os
import hmac
import hashlib
import urllib.parse
import requests
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime, timedelta

# Thiết lập logging
logger = logging.getLogger("binance_api_fixes")

class APIFixer:
    """
    Lớp bổ sung chức năng vào BinanceAPI để xử lý các vấn đề đặc biệt
    
    Các chức năng bao gồm:
    1. Kiểm tra hedge mode của tài khoản
    2. Tạo lệnh với position side phù hợp
    3. Đảm bảo giá trị lệnh đáp ứng yêu cầu tối thiểu
    """
    
    @staticmethod
    def check_hedge_mode(api, check_only=True):
        """
        Kiểm tra và cập nhật trạng thái hedge mode của tài khoản
        
        Args:
            api: Instance của BinanceAPI
            check_only (bool): Chỉ kiểm tra, không đổi trạng thái
            
        Returns:
            bool: True nếu tài khoản đang ở chế độ hedge mode
        """
        if api.account_type != 'futures':
            logger.warning("Chế độ hedge mode chỉ áp dụng cho tài khoản futures")
            return False
            
        try:
            # Lấy cài đặt hiện tại
            response = api._request('GET', 'positionSide/dual', {}, signed=True, version='v1')
            
            if not response or 'dualSidePosition' not in response:
                logger.error(f"Không lấy được thông tin position side: {response}")
                return False
                
            is_hedge_mode = response.get('dualSidePosition', False)
            logger.info(f"Tài khoản đang ở chế độ hedge mode: {is_hedge_mode}")
            
            # Lưu vào instance để sử dụng sau này
            api.hedge_mode = is_hedge_mode
            
            # Thay đổi chế độ nếu cần và được yêu cầu
            if not check_only and not is_hedge_mode:
                logger.info("Đang chuyển sang chế độ hedge mode...")
                change_response = api._request('POST', 'positionSide/dual', 
                                          {'dualSidePosition': 'true'}, 
                                          signed=True, version='v1')
                logger.info(f"Kết quả thay đổi: {change_response}")
                api.hedge_mode = True
                return True
                
            return is_hedge_mode
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra hedge mode: {str(e)}")
            return False
    
    @staticmethod
    def calculate_min_quantity(api, symbol, usd_value=100):
        """
        Tính toán số lượng tối thiểu để đáp ứng yêu cầu giá trị của Binance
        
        Args:
            api: Instance của BinanceAPI
            symbol (str): Symbol cần giao dịch
            usd_value (float): Giá trị USD tối thiểu cần đạt được
            
        Returns:
            float: Số lượng đã làm tròn theo precision của symbol
        """
        try:
            # Lấy giá hiện tại
            ticker = api.get_ticker_price(symbol)
            if not ticker or 'price' not in ticker:
                logger.error(f"Không lấy được giá của {symbol}")
                return None
                
            price = float(ticker['price'])
            
            # Lấy thông tin của symbol
            exchange_info = api._get_exchange_info_for_symbol(symbol)
            if not exchange_info:
                logger.error(f"Không lấy được thông tin của {symbol}")
                return None
                
            # Xác định số thập phân chính xác
            qty_precision = exchange_info.get('quantityPrecision', 3)
            
            # Tính toán số lượng cần thiết để đạt giá trị USD nhất định
            quantity = usd_value / price
            quantity = round(quantity, qty_precision)
            
            # Kiểm tra lại giá trị
            order_value = quantity * price
            
            if order_value < usd_value:
                # Nếu giá trị vẫn chưa đủ, điều chỉnh lên 1 bước nhỏ nhất
                step_size = float('0.' + '0' * (qty_precision - 1) + '1')
                quantity += step_size
                quantity = round(quantity, qty_precision)
                order_value = quantity * price
                
            logger.info(f"Số lượng {symbol}: {quantity} (giá: {price}, giá trị: {order_value} USD)")
            return quantity
        except Exception as e:
            logger.error(f"Lỗi khi tính toán số lượng: {str(e)}")
            return None
    
    @staticmethod
    def create_order_with_position_side(api, symbol, side, order_type, quantity=None, price=None, 
                                        stop_price=None, usd_value=None, position_side=None, 
                                        reduce_only=False, **kwargs):
        """
        Tạo lệnh với xử lý đặc biệt cho hedge mode và notional value
        
        Args:
            api: Instance của BinanceAPI
            symbol (str): Symbol giao dịch
            side (str): Phía giao dịch (BUY/SELL)
            order_type (str): Loại lệnh (LIMIT/MARKET/STOP/TAKE_PROFIT/...)
            quantity (float): Số lượng giao dịch
            price (float): Giá đặt lệnh
            stop_price (float): Giá kích hoạt cho lệnh có điều kiện
            usd_value (float): Giá trị USD tối thiểu (thay thế cho quantity nếu được cung cấp)
            position_side (str): Vị thế (LONG/SHORT)
            reduce_only (bool): Chỉ đóng vị thế
            **kwargs: Các tham số khác
            
        Returns:
            Dict: Kết quả API
        """
        # Kiểm tra hedge mode và đặt mode mặc định nếu cần
        if not hasattr(api, 'hedge_mode'):
            api.hedge_mode = APIFixer.check_hedge_mode(api)
        
        # Ưu tiên dùng giá trị USD để tính số lượng nếu được cung cấp
        if usd_value and not quantity:
            quantity = APIFixer.calculate_min_quantity(api, symbol, usd_value)
            
        if not quantity:
            return {'error': "Không thể xác định số lượng giao dịch"}
        
        # Chuẩn bị tham số
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity
        }
        
        # Thêm các tham số tùy chọn
        if price and order_type != 'MARKET':
            params['price'] = price
            
        if stop_price and order_type in ['STOP', 'STOP_MARKET', 'TAKE_PROFIT', 'TAKE_PROFIT_MARKET']:
            params['stopPrice'] = stop_price
        
        # Xử lý đặc biệt cho hedge mode
        if api.hedge_mode and position_side:
            # Trong hedge mode với position side được chỉ định
            if position_side in ['LONG', 'SHORT']:
                params['positionSide'] = position_side
                # Không thêm reduceOnly khi đã chỉ định positionSide
            elif position_side == 'BOTH':
                params['positionSide'] = 'BOTH'
                if reduce_only:
                    params['reduceOnly'] = 'true'
        else:
            # Chế độ one-way hoặc không chỉ định position side
            if reduce_only:
                params['reduceOnly'] = 'true'
        
        # Thêm các tham số bổ sung
        for key, value in kwargs.items():
            params[key] = value
            
        logger.info(f"Tạo lệnh {order_type} cho {symbol}: {json.dumps(params, indent=2)}")
        
        # Thử gọi API
        result = api._request('POST', 'order', params, signed=True, version='v1')
        
        # Nếu gặp lỗi position side, tự động thử lại với LONG
        if isinstance(result, dict) and result.get('code') == -4061:
            logger.warning("Lỗi position side không khớp, thử lại với LONG")
            params['positionSide'] = 'LONG'
            result = api._request('POST', 'order', params, signed=True, version='v1')
            
        return result
    
    @staticmethod
    def set_stop_loss_take_profit(api, symbol, position_side, is_open_order=False, entry_price=None,
                                 stop_loss_price=None, take_profit_price=None, 
                                 order_quantity=None, usd_value=None):
        """
        Tự động đặt Stop Loss và Take Profit cho vị thế
        
        Args:
            api: Instance của BinanceAPI
            symbol (str): Symbol giao dịch
            position_side (str): LONG, SHORT hoặc BOTH
            is_open_order (bool): True nếu đang mở lệnh mới
            entry_price (float): Giá mở vị thế
            stop_loss_price (float): Giá stop loss
            take_profit_price (float): Giá take profit
            order_quantity (float): Số lượng lệnh
            usd_value (float): Giá trị USD dùng để tính số lượng nếu không cung cấp order_quantity
            
        Returns:
            Dict: Kết quả với các lệnh đã tạo
        """
        if not hasattr(api, 'hedge_mode'):
            api.hedge_mode = APIFixer.check_hedge_mode(api)
        
        # Xác định phương hướng của vị thế
        if not position_side and api.hedge_mode:
            position_side = 'LONG'  # Mặc định LONG nếu không chỉ định trong hedge mode
        
        # Xác định số lượng lệnh TP/SL
        if not order_quantity and usd_value:
            order_quantity = APIFixer.calculate_min_quantity(api, symbol, usd_value)
            
        if not order_quantity:
            # Thử lấy từ vị thế hiện tại
            positions = api.get_position_risk()
            for pos in positions:
                if pos['symbol'] == symbol:
                    if (not position_side) or (position_side == 'BOTH') or (pos['positionSide'] == position_side):
                        order_quantity = abs(float(pos['positionAmt']))
                        break
        
        if not order_quantity:
            return {'error': "Không thể xác định số lượng cho TP/SL"}
            
        # Xác định side dựa vào position_side
        if position_side == 'LONG':
            side = 'SELL'
        elif position_side == 'SHORT':
            side = 'BUY'
        else:
            # Với BOTH, cần xác định dựa trên vị thế hiện tại
            positions = api.get_position_risk()
            for pos in positions:
                if pos['symbol'] == symbol:
                    pos_amt = float(pos['positionAmt'])
                    side = 'SELL' if pos_amt > 0 else 'BUY'
                    break
            else:
                return {'error': "Không thể xác định side cho TP/SL"}
        
        # Tạo lệnh
        results = {}
        
        # Take Profit
        if take_profit_price:
            tp_result = APIFixer.create_order_with_position_side(
                api=api,
                symbol=symbol,
                side=side,
                order_type='TAKE_PROFIT_MARKET',
                quantity=order_quantity,
                stop_price=take_profit_price,
                position_side=position_side,
                working_type='MARK_PRICE'
            )
            results['take_profit'] = tp_result
            
        # Stop Loss
        if stop_loss_price:
            sl_result = APIFixer.create_order_with_position_side(
                api=api,
                symbol=symbol,
                side=side,
                order_type='STOP_MARKET',
                quantity=order_quantity,
                stop_price=stop_loss_price,
                position_side=position_side,
                working_type='MARK_PRICE'
            )
            results['stop_loss'] = sl_result
            
        return results

def apply_fixes_to_api(api):
    """
    Áp dụng các bản vá lỗi vào instance BinanceAPI hiện có
    
    Args:
        api: Instance của BinanceAPI
    """
    # Thêm các thuộc tính mới
    api.hedge_mode = False
    
    # Kiểm tra hedge mode
    APIFixer.check_hedge_mode(api)
    
    # Thêm các phương thức mới
    api.create_order_with_position_side = lambda *args, **kwargs: APIFixer.create_order_with_position_side(api, *args, **kwargs)
    api.set_stop_loss_take_profit = lambda *args, **kwargs: APIFixer.set_stop_loss_take_profit(api, *args, **kwargs)
    api.calculate_min_quantity = lambda *args, **kwargs: APIFixer.calculate_min_quantity(api, *args, **kwargs)
    
    # Ghi log
    logger.info("Đã áp dụng các bản vá lỗi vào BinanceAPI")
    
    return api

# Module test
if __name__ == "__main__":
    from binance_api import BinanceAPI
    
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Tạo instance API
    api = BinanceAPI()
    
    # Áp dụng bản vá
    api = apply_fixes_to_api(api)
    
    # Kiểm tra hedge mode
    print(f"Tài khoản ở chế độ hedge mode: {api.hedge_mode}")
    
    # Thử tạo lệnh
    symbol = "BTCUSDT"
    order = api.create_order_with_position_side(
        symbol=symbol,
        side="BUY",
        order_type="MARKET",
        usd_value=200,
        position_side="LONG"
    )
    
    print(f"Kết quả tạo lệnh: {json.dumps(order, indent=2)}")
    
    # Thử đặt TP/SL
    if not order.get('error'):
        ticker = api.get_ticker_price(symbol)
        if ticker and 'price' in ticker:
            price = float(ticker['price'])
            
            tp_sl = api.set_stop_loss_take_profit(
                symbol=symbol,
                position_side="LONG",
                entry_price=price,
                stop_loss_price=price * 0.97,  # -3%
                take_profit_price=price * 1.05,  # +5%
                usd_value=100  # 50% vị thế
            )
            
            print(f"Kết quả đặt TP/SL: {json.dumps(tp_sl, indent=2)}")