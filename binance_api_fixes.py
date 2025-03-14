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
    def calculate_min_quantity(api, symbol, usd_value=None):
        """
        Tính toán số lượng tối thiểu để đáp ứng yêu cầu giá trị của Binance
        
        Args:
            api: Instance của BinanceAPI
            symbol (str): Symbol cần giao dịch
            usd_value (float): Giá trị USD tối thiểu cần đạt được (nếu None, sẽ dùng giá trị tối thiểu của symbol)
            
        Returns:
            float: Số lượng đã làm tròn theo precision của symbol
        """
        try:
            # Import module cache giá
            from prices_cache import get_price, update_price
            import json
            import os
            
            # Đọc cấu hình min_value cho từng đồng coin
            min_values = {}
            try:
                if os.path.exists('symbol_min_values.json'):
                    with open('symbol_min_values.json', 'r') as f:
                        min_values = json.load(f)
                    logger.info(f"Đã tải cấu hình min_value cho {len(min_values)} symbols")
            except Exception as ex:
                logger.error(f"Lỗi khi tải cấu hình min_value: {str(ex)}")
            
            # Nếu không có usd_value, dùng giá trị tối thiểu của symbol
            if usd_value is None:
                if symbol in min_values:
                    usd_value = min_values[symbol].get('min_notional', 5.0)
                    logger.info(f"Sử dụng min_notional={usd_value} cho {symbol}")
                elif 'default' in min_values:
                    usd_value = min_values['default'].get('min_notional', 5.0)
                    logger.info(f"Sử dụng min_notional mặc định={usd_value} cho {symbol}")
                else:
                    usd_value = 5.0
                    logger.info(f"Sử dụng min_notional cố định={usd_value} cho {symbol}")
            
            # Lấy min_quantity từ cấu hình
            min_quantity = 0.001  # Giá trị mặc định
            if symbol in min_values:
                min_quantity = min_values[symbol].get('min_quantity', 0.001)
            elif 'default' in min_values:
                min_quantity = min_values['default'].get('min_quantity', 0.001)
                
            # Thử lấy giá từ API
            ticker_data = None
            try:
                ticker_data = api.futures_ticker_price(symbol)
            except Exception as ex:
                logger.warning(f"Lỗi khi lấy giá từ API: {str(ex)}")
                
            if isinstance(ticker_data, dict) and 'price' in ticker_data:
                price = float(ticker_data['price'])
                # Cập nhật cache
                update_price(symbol, price)
            else:
                # Fallback: sử dụng giá từ cache
                price = get_price(symbol, fallback_to_default=True)
                if price:
                    logger.warning(f"Sử dụng giá cache cho {symbol}: {price}")
                else:
                    logger.warning(f"Symbol {symbol} không được hỗ trợ hoặc không có giá")
                    return None
                
            if not price:
                logger.error(f"Không lấy được giá của {symbol}")
                return None
            
            # Lấy thông tin của symbol
            exchange_info = None
            try:
                # Lấy thông tin exchange
                exchange_info_data = api._request('GET', 'exchangeInfo', {}, version='v1')
                if isinstance(exchange_info_data, dict) and 'symbols' in exchange_info_data:
                    for item in exchange_info_data['symbols']:
                        if item.get('symbol') == symbol:
                            exchange_info = item
                            break
            except Exception as ex:
                logger.error(f"Lỗi khi lấy exchange info: {str(ex)}")
            
            if not exchange_info:
                # Sử dụng giá trị mặc định nếu không lấy được thông tin chính xác
                qty_precision = 3
                logger.warning(f"Không lấy được thông tin của {symbol}, sử dụng precision mặc định: {qty_precision}")
            else:
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
                
            # Kiểm tra và đảm bảo số lượng tối thiểu (từ min_values)
            min_quantity = 0.001  # Giá trị mặc định
            if symbol in min_values:
                min_quantity = min_values[symbol].get('min_quantity', 0.001)
            elif 'default' in min_values:
                min_quantity = min_values['default'].get('min_quantity', 0.001)
                
            # Sử dụng giá trị lớn hơn giữa min_quantity và quantity đã tính
            if quantity < min_quantity:
                logger.info(f"Điều chỉnh số lượng {quantity} lên min_quantity={min_quantity}")
                quantity = min_quantity
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
        
        # Xử lý đặc biệt cho hedge mode và one-way mode
        # Quan trọng: Không kết hợp closePosition=true với positionSide
        if 'closePosition' in kwargs and kwargs['closePosition'] == 'true':
            # Nếu đã chỉ định closePosition, xóa position_side để tránh lỗi
            logger.warning("Không thể kết hợp closePosition với positionSide, sẽ ưu tiên closePosition")
            position_side = None
            
        if api.hedge_mode:
            # Trong chế độ hedge mode
            if position_side in ['LONG', 'SHORT']:
                # Thêm positionSide nhưng KHÔNG thêm reduceOnly - đây là vấn đề quan trọng
                params['positionSide'] = position_side
                if 'reduceOnly' in params:
                    logger.warning("Đã xóa tham số reduceOnly khi sử dụng positionSide")
                    del params['reduceOnly']
            elif position_side == 'BOTH' and reduce_only:
                # Trường hợp BOTH chỉ dùng trong one-way mode
                params['positionSide'] = 'BOTH'
                params['reduceOnly'] = 'true'
            elif reduce_only:
                # Trong hedge mode nhưng không chỉ định position_side
                logger.warning("Trong hedge mode nhưng không chỉ định position_side cho reduceOnly")
                # Mặc định dùng LONG cho SL/TP nếu không chỉ định
                params['positionSide'] = 'LONG'  
        else:
            # Chế độ one-way (không có positionSide)
            if reduce_only:
                params['reduceOnly'] = 'true'
                # Xác nhận không sử dụng positionSide trong one-way mode
                if position_side:
                    logger.warning(f"Bỏ qua tham số position_side={position_side} trong chế độ one-way")
        
        # Thêm các tham số bổ sung
        for key, value in kwargs.items():
            # Bỏ qua closePosition khi đã chỉ định positionSide
            if key == 'closePosition' and 'positionSide' in params:
                logger.warning(f"Bỏ qua tham số {key}={value} khi đã sử dụng positionSide")
                continue
            params[key] = value
            
        logger.info(f"Tạo lệnh {order_type} cho {symbol}: {json.dumps(params, indent=2)}")
        
        # Thử gọi API
        result = api._request('POST', 'order', params, signed=True, version='v1')
        
        # Xử lý các lỗi thường gặp
        if isinstance(result, dict) and 'code' in result:
            error_code = result.get('code')
            
            # Lỗi position side không khớp
            if error_code == -4061:
                logger.warning("Lỗi position side không khớp, thử lại với LONG")
                params['positionSide'] = 'LONG'
                result = api._request('POST', 'order', params, signed=True, version='v1')
            # Lỗi về reduceOnly và positionSide
            elif error_code == -4013 and 'positionSide' in params and 'reduceOnly' in params:
                logger.warning("Lỗi kết hợp reduceOnly với positionSide, thử lại sau khi xóa reduceOnly")
                del params['reduceOnly']
                result = api._request('POST', 'order', params, signed=True, version='v1')
            # Thêm các xử lý lỗi khác nếu cần
            
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
        
        # Ghi log chế độ tài khoản
        logger.info(f"Đang đặt SL/TP cho tài khoản {'' if api.hedge_mode else 'không '}ở chế độ hedge mode")
        
        # Xác định phương hướng của vị thế
        if not position_side and api.hedge_mode:
            position_side = 'LONG'  # Mặc định LONG nếu không chỉ định trong hedge mode
            logger.info(f"Không chỉ định position_side, sử dụng mặc định: {position_side}")
        
        # Xác định số lượng lệnh TP/SL
        if not order_quantity and usd_value:
            order_quantity = APIFixer.calculate_min_quantity(api, symbol, usd_value)
            logger.info(f"Tính toán số lượng từ giá trị USD {usd_value}: {order_quantity}")
            
        if not order_quantity:
            # Thử lấy từ vị thế hiện tại
            try:
                positions = api.get_futures_position_risk()
                found_position = False
                
                for pos in positions:
                    if pos['symbol'] == symbol:
                        # Kiểm tra position_side nếu ở chế độ hedge
                        if api.hedge_mode:
                            if position_side and pos['positionSide'] == position_side:
                                order_quantity = abs(float(pos['positionAmt']))
                                logger.info(f"Đã xác định số lượng từ vị thế {symbol} ({position_side}): {order_quantity}")
                                found_position = True
                                break
                        else:
                            # Trong chế độ one-way, không cần kiểm tra positionSide
                            order_quantity = abs(float(pos['positionAmt']))
                            logger.info(f"Đã xác định số lượng từ vị thế {symbol} (one-way): {order_quantity}")
                            found_position = True
                            break
                
                if not found_position:
                    logger.warning(f"Không tìm thấy vị thế {symbol} phù hợp")
            except Exception as e:
                logger.error(f"Lỗi khi truy vấn vị thế: {str(e)}")
        
        if not order_quantity:
            return {'error': "Không thể xác định số lượng cho TP/SL"}
            
        # Xác định side dựa vào position_side và loại vị thế
        side = None
        
        if api.hedge_mode:
            # Trong chế độ hedge mode, side phụ thuộc vào position_side
            if position_side == 'LONG':
                side = 'SELL'  # Đóng vị thế LONG bằng SELL
            elif position_side == 'SHORT':
                side = 'BUY'   # Đóng vị thế SHORT bằng BUY
            else:
                logger.error(f"Position side không hợp lệ trong hedge mode: {position_side}")
                return {'error': f"Position side không hợp lệ: {position_side}"}
        else:
            # Trong chế độ one-way, cần xác định side dựa trên giá trị vị thế
            try:
                positions = api.get_futures_position_risk()
                for pos in positions:
                    if pos['symbol'] == symbol:
                        pos_amt = float(pos['positionAmt'])
                        side = 'SELL' if pos_amt > 0 else 'BUY'
                        logger.info(f"Đã xác định side cho one-way mode: {side} (positionAmt={pos_amt})")
                        break
                else:
                    return {'error': "Không tìm thấy vị thế để đặt SL/TP"}
            except Exception as e:
                logger.error(f"Lỗi khi xác định side cho SL/TP: {str(e)}")
                return {'error': f"Lỗi khi xác định side: {str(e)}"}
        
        if not side:
            return {'error': "Không thể xác định side cho TP/SL"}
        
        # Chuẩn bị các tham số cho SL/TP dựa vào loại tài khoản
        tp_params = {
            'api': api,
            'symbol': symbol,
            'side': side,
            'order_type': 'TAKE_PROFIT_MARKET',
            'quantity': order_quantity,
            'stop_price': take_profit_price,
            'working_type': 'MARK_PRICE'
        }
        
        sl_params = {
            'api': api,
            'symbol': symbol,
            'side': side,
            'order_type': 'STOP_MARKET',
            'quantity': order_quantity,
            'stop_price': stop_loss_price,
            'working_type': 'MARK_PRICE'
        }
        
        # Thêm tham số đặc biệt dựa vào chế độ tài khoản
        if api.hedge_mode:
            # Trong hedge mode, thêm position_side
            tp_params['position_side'] = position_side
            sl_params['position_side'] = position_side
            logger.info(f"Thêm position_side={position_side} cho lệnh SL/TP trong hedge mode")
        else:
            # Trong one-way mode, thêm reduceOnly=True
            tp_params['reduce_only'] = True
            sl_params['reduce_only'] = True
            logger.info("Thêm reduceOnly=True cho lệnh SL/TP trong one-way mode")
        
        # Tạo lệnh
        results = {}
        
        # Take Profit
        if take_profit_price:
            logger.info(f"Đặt Take Profit cho {symbol} tại giá {take_profit_price}")
            tp_result = APIFixer.create_order_with_position_side(**tp_params)
            results['take_profit'] = tp_result
            
            if 'orderId' in tp_result:
                logger.info(f"Đặt TP thành công, orderId: {tp_result['orderId']}")
            else:
                logger.error(f"Lỗi khi đặt TP: {tp_result}")
            
        # Stop Loss
        if stop_loss_price:
            logger.info(f"Đặt Stop Loss cho {symbol} tại giá {stop_loss_price}")
            sl_result = APIFixer.create_order_with_position_side(**sl_params)
            results['stop_loss'] = sl_result
            
            if 'orderId' in sl_result:
                logger.info(f"Đặt SL thành công, orderId: {sl_result['orderId']}")
            else:
                logger.error(f"Lỗi khi đặt SL: {sl_result}")
            
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
        # Thử lấy giá hiện tại từ API
        try:
            ticker_data = api.futures_ticker_price(symbol)
            price = None
            
            if isinstance(ticker_data, dict) and 'price' in ticker_data:
                price = float(ticker_data['price'])
                logger.info(f"Đã lấy được giá {symbol} từ API: {price}")
            else:
                # Sử dụng giá từ cache trong trường hợp không lấy được từ API
                from prices_cache import get_price as get_cached_price
                price = get_cached_price(symbol)
                logger.warning(f"Không lấy được giá {symbol} từ API, sử dụng giá cache: {price}")
        except Exception as e:
            # Trong trường hợp lỗi API, sử dụng giá dự phòng từ module prices_cache
            from prices_cache import get_price as get_cached_price
            price = get_cached_price(symbol)
            logger.error(f"Lỗi khi lấy giá {symbol}: {str(e)}, sử dụng giá dự phòng: {price}")
        
        if price:
            tp_sl = api.set_stop_loss_take_profit(
                symbol=symbol,
                position_side="LONG",
                entry_price=price,
                stop_loss_price=price * 0.97,  # -3%
                take_profit_price=price * 1.05,  # +5%
                usd_value=100  # 50% vị thế
            )
        else:
            tp_sl = {"error": f"Không thể lấy giá cho {symbol}"}
            logger.error(f"Không thể đặt TP/SL vì không có giá cho {symbol}")
            
            print(f"Kết quả đặt TP/SL: {json.dumps(tp_sl, indent=2)}")