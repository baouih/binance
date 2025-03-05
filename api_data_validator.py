#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module kiểm tra và xác thực dữ liệu API (API Data Validator)

Module này cung cấp các công cụ để kiểm tra tính hợp lệ của dữ liệu từ API trước khi sử dụng,
đồng thời triển khai các cơ chế retry khi API gặp lỗi để đảm bảo độ tin cậy.
"""

import time
import json
import logging
import datetime
import traceback
from typing import Dict, List, Tuple, Any, Optional, Union, Callable
from functools import wraps

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('api_data_validator')

class APIDataValidator:
    """Lớp kiểm tra và xác thực dữ liệu API"""
    
    def __init__(self, max_retries: int = 3, retry_delay: int = 2, 
                validate_schema: bool = True, log_level: str = 'INFO'):
        """
        Khởi tạo API Data Validator
        
        Args:
            max_retries (int): Số lần thử lại tối đa khi gặp lỗi API
            retry_delay (int): Thời gian chờ giữa các lần thử lại (giây)
            validate_schema (bool): Có kiểm tra schema của dữ liệu hay không
            log_level (str): Mức độ logging ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.validate_schema = validate_schema
        
        # Thiết lập log level
        log_levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        logger.setLevel(log_levels.get(log_level, logging.INFO))
        
        # Schema chuẩn cho các API response
        self.schemas = {
            # Schema cho dữ liệu giá từ Binance
            'klines': {
                'type': 'list',
                'required_fields': ['open_time', 'open', 'high', 'low', 'close', 'volume']
            },
            # Schema cho thông tin vị thế
            'position': {
                'type': 'dict',
                'required_fields': ['symbol', 'positionAmt', 'entryPrice', 'markPrice', 'unRealizedProfit', 'liquidationPrice', 'leverage', 'marginType']
            },
            # Schema cho order book
            'order_book': {
                'type': 'dict',
                'required_fields': ['lastUpdateId', 'bids', 'asks']
            },
            # Schema cho lệnh giao dịch
            'order': {
                'type': 'dict',
                'required_fields': ['orderId', 'symbol', 'status', 'clientOrderId', 'price', 'origQty', 'executedQty', 'type', 'side']
            },
            # Schema cho thông tin tài khoản
            'account': {
                'type': 'dict',
                'required_fields': ['totalWalletBalance', 'totalUnrealizedProfit', 'totalMarginBalance', 'availableBalance', 'positions']
            }
        }
        
        # Thêm schema tùy chỉnh
        self.custom_schemas = {}
    
    def add_custom_schema(self, schema_name: str, schema_def: Dict) -> None:
        """
        Thêm schema tùy chỉnh
        
        Args:
            schema_name (str): Tên schema
            schema_def (Dict): Định nghĩa schema
        """
        self.custom_schemas[schema_name] = schema_def
        logger.debug(f"Đã thêm schema tùy chỉnh: {schema_name}")
    
    def with_retry(self, func: Callable) -> Callable:
        """
        Decorator để thêm cơ chế retry cho hàm
        
        Args:
            func (Callable): Hàm cần thêm retry
            
        Returns:
            Callable: Hàm đã được wrap với cơ chế retry
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(self.max_retries):
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Lỗi khi thực thi {func.__name__} (lần thử {attempt+1}/{self.max_retries}): {str(e)}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
            
            # Nếu tất cả các lần thử đều thất bại
            logger.error(f"Đã thử {self.max_retries} lần nhưng đều thất bại: {str(last_exception)}")
            raise last_exception
        
        return wrapper
    
    def validate_data(self, data: Any, schema_name: str, raise_exception: bool = False) -> Tuple[bool, List[str]]:
        """
        Kiểm tra tính hợp lệ của dữ liệu dựa trên schema
        
        Args:
            data (Any): Dữ liệu cần kiểm tra
            schema_name (str): Tên schema sử dụng để kiểm tra
            raise_exception (bool): Có raise exception khi dữ liệu không hợp lệ hay không
            
        Returns:
            Tuple[bool, List[str]]: (Dữ liệu có hợp lệ không, Danh sách lỗi)
        """
        errors = []
        
        # Lấy schema
        schema = self.schemas.get(schema_name)
        if not schema and schema_name in self.custom_schemas:
            schema = self.custom_schemas.get(schema_name)
        
        if not schema:
            msg = f"Không tìm thấy schema '{schema_name}'"
            errors.append(msg)
            if raise_exception:
                raise ValueError(msg)
            return False, errors
        
        # Kiểm tra kiểu dữ liệu
        expected_type = schema['type']
        if expected_type == 'list' and not isinstance(data, list):
            msg = f"Dữ liệu phải là danh sách, nhưng nhận được {type(data).__name__}"
            errors.append(msg)
            if raise_exception:
                raise TypeError(msg)
            return False, errors
        
        if expected_type == 'dict' and not isinstance(data, dict):
            msg = f"Dữ liệu phải là từ điển, nhưng nhận được {type(data).__name__}"
            errors.append(msg)
            if raise_exception:
                raise TypeError(msg)
            return False, errors
        
        # Kiểm tra các trường bắt buộc
        required_fields = schema.get('required_fields', [])
        
        if expected_type == 'dict':
            # Kiểm tra từng trường bắt buộc
            for field in required_fields:
                if field not in data:
                    msg = f"Thiếu trường bắt buộc '{field}'"
                    errors.append(msg)
        
        elif expected_type == 'list' and len(data) > 0:
            # Nếu là danh sách, kiểm tra phần tử đầu tiên
            if isinstance(data[0], dict):
                for field in required_fields:
                    if field not in data[0]:
                        msg = f"Thiếu trường bắt buộc '{field}' trong phần tử của danh sách"
                        errors.append(msg)
        
        # Kiểm tra các ràng buộc khác
        constraints = schema.get('constraints', {})
        for field, constraint in constraints.items():
            if expected_type == 'dict' and field in data:
                # Kiểm tra giá trị
                if 'min' in constraint and data[field] < constraint['min']:
                    msg = f"Trường '{field}' nhỏ hơn giá trị tối thiểu {constraint['min']}"
                    errors.append(msg)
                
                if 'max' in constraint and data[field] > constraint['max']:
                    msg = f"Trường '{field}' lớn hơn giá trị tối đa {constraint['max']}"
                    errors.append(msg)
                
                if 'enum' in constraint and data[field] not in constraint['enum']:
                    msg = f"Trường '{field}' phải là một trong {constraint['enum']}"
                    errors.append(msg)
        
        # Xử lý kết quả
        is_valid = len(errors) == 0
        
        if not is_valid:
            log_msg = f"Dữ liệu không hợp lệ cho schema '{schema_name}': {'; '.join(errors)}"
            logger.warning(log_msg)
            
            if raise_exception:
                raise ValueError(log_msg)
        
        return is_valid, errors
    
    def clean_and_transform_data(self, data: Any, schema_name: str) -> Any:
        """
        Làm sạch và chuyển đổi dữ liệu theo schema
        
        Args:
            data (Any): Dữ liệu cần xử lý
            schema_name (str): Tên schema sử dụng
            
        Returns:
            Any: Dữ liệu đã được làm sạch và chuyển đổi
        """
        # Lấy schema
        schema = self.schemas.get(schema_name)
        if not schema and schema_name in self.custom_schemas:
            schema = self.custom_schemas.get(schema_name)
        
        if not schema:
            logger.warning(f"Không tìm thấy schema '{schema_name}', không thể xử lý dữ liệu")
            return data
        
        # Kiểm tra kiểu dữ liệu
        expected_type = schema['type']
        
        # Xử lý cho từ điển
        if expected_type == 'dict' and isinstance(data, dict):
            # Tạo một copy của dữ liệu gốc
            cleaned_data = {}
            
            # Các trường cần giữ lại
            fields_to_keep = schema.get('required_fields', []) + schema.get('optional_fields', [])
            
            # Chỉ giữ lại các trường cần thiết
            for field in fields_to_keep:
                if field in data:
                    cleaned_data[field] = data[field]
            
            # Áp dụng các phép biến đổi
            transformations = schema.get('transformations', {})
            for field, transform in transformations.items():
                if field in cleaned_data:
                    if transform == 'to_float':
                        try:
                            cleaned_data[field] = float(cleaned_data[field])
                        except (ValueError, TypeError):
                            logger.warning(f"Không thể chuyển đổi trường '{field}' sang float")
                    
                    elif transform == 'to_int':
                        try:
                            cleaned_data[field] = int(float(cleaned_data[field]))
                        except (ValueError, TypeError):
                            logger.warning(f"Không thể chuyển đổi trường '{field}' sang int")
                    
                    elif transform == 'to_bool':
                        if isinstance(cleaned_data[field], str):
                            cleaned_data[field] = cleaned_data[field].lower() in ('true', '1', 'yes')
                        else:
                            cleaned_data[field] = bool(cleaned_data[field])
            
            return cleaned_data
        
        # Xử lý cho danh sách
        elif expected_type == 'list' and isinstance(data, list):
            # Xử lý từng phần tử
            cleaned_data = []
            
            for item in data:
                if isinstance(item, dict):
                    # Áp dụng tương tự như với từ điển
                    cleaned_item = {}
                    fields_to_keep = schema.get('required_fields', []) + schema.get('optional_fields', [])
                    
                    for field in fields_to_keep:
                        if field in item:
                            cleaned_item[field] = item[field]
                    
                    cleaned_data.append(cleaned_item)
                else:
                    cleaned_data.append(item)
            
            return cleaned_data
        
        # Trả về dữ liệu gốc nếu không thể xử lý
        return data
    
    def validate_binance_position_data(self, position_data: Dict) -> Tuple[bool, List[str]]:
        """
        Kiểm tra tính hợp lệ của dữ liệu vị thế từ Binance
        
        Args:
            position_data (Dict): Dữ liệu vị thế từ Binance
            
        Returns:
            Tuple[bool, List[str]]: (Dữ liệu có hợp lệ không, Danh sách lỗi)
        """
        errors = []
        
        # Kiểm tra các trường bắt buộc
        required_fields = [
            'symbol', 'positionAmt', 'entryPrice', 'markPrice', 
            'unRealizedProfit', 'marginType', 'leverage'
        ]
        
        for field in required_fields:
            if field not in position_data:
                errors.append(f"Thiếu trường bắt buộc '{field}'")
        
        # Kiểm tra và chuyển đổi kiểu dữ liệu
        if 'positionAmt' in position_data:
            try:
                position_amt = float(position_data['positionAmt'])
            except (ValueError, TypeError):
                errors.append("Trường 'positionAmt' không phải là số hợp lệ")
        
        if 'entryPrice' in position_data:
            try:
                entry_price = float(position_data['entryPrice'])
            except (ValueError, TypeError):
                errors.append("Trường 'entryPrice' không phải là số hợp lệ")
        
        if 'markPrice' in position_data:
            try:
                mark_price = float(position_data['markPrice'])
            except (ValueError, TypeError):
                errors.append("Trường 'markPrice' không phải là số hợp lệ")
        
        if 'leverage' in position_data:
            try:
                leverage = int(float(position_data['leverage']))
                if leverage <= 0:
                    errors.append("Trường 'leverage' phải lớn hơn 0")
            except (ValueError, TypeError):
                errors.append("Trường 'leverage' không phải là số hợp lệ")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Dữ liệu vị thế không hợp lệ: {'; '.join(errors)}")
        
        return is_valid, errors
    
    def validate_binance_order_data(self, order_data: Dict) -> Tuple[bool, List[str]]:
        """
        Kiểm tra tính hợp lệ của dữ liệu lệnh từ Binance
        
        Args:
            order_data (Dict): Dữ liệu lệnh từ Binance
            
        Returns:
            Tuple[bool, List[str]]: (Dữ liệu có hợp lệ không, Danh sách lỗi)
        """
        errors = []
        
        # Kiểm tra các trường bắt buộc
        required_fields = [
            'orderId', 'symbol', 'status', 'type', 'side', 
            'price', 'origQty', 'executedQty'
        ]
        
        for field in required_fields:
            if field not in order_data:
                errors.append(f"Thiếu trường bắt buộc '{field}'")
        
        # Kiểm tra status hợp lệ
        valid_statuses = ['NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']
        if 'status' in order_data and order_data['status'] not in valid_statuses:
            errors.append(f"Trạng thái '{order_data['status']}' không hợp lệ, phải là một trong {valid_statuses}")
        
        # Kiểm tra side hợp lệ
        valid_sides = ['BUY', 'SELL']
        if 'side' in order_data and order_data['side'] not in valid_sides:
            errors.append(f"Side '{order_data['side']}' không hợp lệ, phải là một trong {valid_sides}")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Dữ liệu lệnh không hợp lệ: {'; '.join(errors)}")
        
        return is_valid, errors
    
    def validate_binance_klines_data(self, klines_data: List) -> Tuple[bool, List[str]]:
        """
        Kiểm tra tính hợp lệ của dữ liệu k-lines từ Binance
        
        Args:
            klines_data (List): Dữ liệu k-lines từ Binance
            
        Returns:
            Tuple[bool, List[str]]: (Dữ liệu có hợp lệ không, Danh sách lỗi)
        """
        errors = []
        
        # Kiểm tra kiểu dữ liệu
        if not isinstance(klines_data, list):
            errors.append(f"Dữ liệu klines phải là danh sách, nhận được {type(klines_data).__name__}")
            return False, errors
        
        # Kiểm tra danh sách rỗng
        if len(klines_data) == 0:
            errors.append("Danh sách klines trống")
            return False, errors
        
        # Kiểm tra cấu trúc từng candlestick
        for i, candle in enumerate(klines_data):
            if not isinstance(candle, list):
                errors.append(f"Candlestick ở vị trí {i} phải là danh sách, nhận được {type(candle).__name__}")
                continue
            
            # Binance klines API trả về danh sách 12 phần tử
            if len(candle) < 12:
                errors.append(f"Candlestick ở vị trí {i} thiếu dữ liệu, cần ít nhất 12 phần tử")
                continue
            
            # Kiểm tra các giá trị quan trọng
            try:
                open_time = int(candle[0])
                open_price = float(candle[1])
                high_price = float(candle[2])
                low_price = float(candle[3])
                close_price = float(candle[4])
                volume = float(candle[5])
                
                # Kiểm tra tính hợp lệ của giá
                if low_price > high_price:
                    errors.append(f"Candlestick ở vị trí {i} có giá thấp nhất ({low_price}) > giá cao nhất ({high_price})")
                
                if low_price > open_price or low_price > close_price:
                    errors.append(f"Candlestick ở vị trí {i} có giá thấp nhất ({low_price}) > giá mở/đóng cửa")
                
                if high_price < open_price or high_price < close_price:
                    errors.append(f"Candlestick ở vị trí {i} có giá cao nhất ({high_price}) < giá mở/đóng cửa")
                
                # Kiểm tra volume hợp lệ
                if volume < 0:
                    errors.append(f"Candlestick ở vị trí {i} có volume âm ({volume})")
            
            except (ValueError, TypeError) as e:
                errors.append(f"Lỗi khi kiểm tra candlestick ở vị trí {i}: {str(e)}")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            if len(errors) > 5:
                # Nếu có quá nhiều lỗi, chỉ hiển thị 5 lỗi đầu tiên
                logger.warning(f"Dữ liệu klines không hợp lệ: {'; '.join(errors[:5])} và {len(errors) - 5} lỗi khác")
            else:
                logger.warning(f"Dữ liệu klines không hợp lệ: {'; '.join(errors)}")
        
        return is_valid, errors
    
    def transform_binance_klines(self, klines_data: List) -> List[Dict]:
        """
        Chuyển đổi dữ liệu k-lines từ Binance sang định dạng dễ sử dụng
        
        Args:
            klines_data (List): Dữ liệu k-lines từ Binance
            
        Returns:
            List[Dict]: Dữ liệu sau khi chuyển đổi
        """
        # Kiểm tra dữ liệu hợp lệ
        is_valid, errors = self.validate_binance_klines_data(klines_data)
        if not is_valid:
            logger.warning(f"Chuyển đổi dữ liệu klines không hợp lệ: {errors}")
            return []
        
        # Chuyển đổi sang dạng dict
        result = []
        for candle in klines_data:
            transformed_candle = {
                'open_time': int(candle[0]),
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5]),
                'close_time': int(candle[6]),
                'quote_volume': float(candle[7]),
                'trades_count': int(candle[8]),
                'taker_buy_base_volume': float(candle[9]),
                'taker_buy_quote_volume': float(candle[10])
            }
            
            # Thêm timestamp dạng datetime
            transformed_candle['timestamp'] = datetime.datetime.fromtimestamp(transformed_candle['open_time'] / 1000)
            
            result.append(transformed_candle)
        
        return result
    
    def transform_binance_position(self, position_data: Dict) -> Dict:
        """
        Chuyển đổi dữ liệu vị thế từ Binance sang định dạng dễ sử dụng
        
        Args:
            position_data (Dict): Dữ liệu vị thế từ Binance
            
        Returns:
            Dict: Dữ liệu sau khi chuyển đổi
        """
        # Kiểm tra dữ liệu hợp lệ
        is_valid, errors = self.validate_binance_position_data(position_data)
        if not is_valid:
            logger.warning(f"Chuyển đổi dữ liệu vị thế không hợp lệ: {errors}")
            return {}
        
        # Chuyển đổi sang định dạng sử dụng trong hệ thống
        position_amt = float(position_data['positionAmt'])
        side = 'LONG' if position_amt > 0 else 'SHORT' if position_amt < 0 else 'NONE'
        
        transformed_data = {
            'symbol': position_data['symbol'],
            'side': side,
            'entry_price': float(position_data['entryPrice']),
            'mark_price': float(position_data['markPrice']),
            'quantity': abs(position_amt),
            'unrealized_pnl': float(position_data['unRealizedProfit']),
            'leverage': int(float(position_data['leverage'])),
            'margin_type': position_data['marginType'],
            'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Thêm các trường tùy chọn nếu có
        if 'liquidationPrice' in position_data:
            transformed_data['liquidation_price'] = float(position_data['liquidationPrice'])
        
        if 'isolatedWallet' in position_data:
            transformed_data['isolated_margin'] = float(position_data['isolatedWallet'])
        
        if 'isolatedMargin' in position_data:
            transformed_data['isolated_margin'] = float(position_data['isolatedMargin'])
        
        return transformed_data


def retry(max_retries=3, retry_delay=2):
    """
    Decorator để thêm cơ chế retry cho bất kỳ hàm nào
    
    Args:
        max_retries (int): Số lần thử lại tối đa
        retry_delay (int): Thời gian chờ giữa các lần thử lại (giây)
    
    Returns:
        Callable: Decorator
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Lỗi khi thực thi {func.__name__} (lần thử {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
            
            # Nếu tất cả các lần thử đều thất bại
            logger.error(f"Đã thử {max_retries} lần nhưng đều thất bại: {str(last_exception)}")
            raise last_exception
        
        return wrapper
    
    return decorator


def main():
    """Hàm chính để test APIDataValidator"""
    
    print("=== Testing APIDataValidator ===\n")
    
    # Tạo một đối tượng validator
    validator = APIDataValidator(max_retries=3, retry_delay=1)
    
    # Test dữ liệu đúng và sai
    # Dữ liệu k-lines đúng
    klines_data_valid = [
        [1625097600000, "35000.0", "36000.0", "34500.0", "35500.0", "1000.0", 1625184000000, "35500000.0", 5000, "600.0", "21000000.0", "0"],
        [1625184000000, "35500.0", "37000.0", "35000.0", "36800.0", "1200.0", 1625270400000, "43200000.0", 6000, "700.0", "25200000.0", "0"]
    ]
    
    # Dữ liệu k-lines sai
    klines_data_invalid = [
        [1625097600000, "35000.0", "34000.0", "34500.0", "35500.0", "1000.0", 1625184000000, "35500000.0", 5000, "600.0", "21000000.0", "0"],
        [1625184000000, "35500.0", "37000.0", "35000.0", "36800.0", "-1200.0", 1625270400000, "43200000.0", 6000, "700.0", "25200000.0", "0"]
    ]
    
    # Dữ liệu position đúng
    position_data_valid = {
        "symbol": "BTCUSDT",
        "positionAmt": "0.002",
        "entryPrice": "35000.0",
        "markPrice": "36000.0",
        "unRealizedProfit": "2.0",
        "liquidationPrice": "30000.0",
        "leverage": "10",
        "marginType": "isolated",
        "isolatedMargin": "7.0"
    }
    
    # Dữ liệu position sai
    position_data_invalid = {
        "symbol": "BTCUSDT",
        "positionAmt": "invalid",
        "entryPrice": "35000.0",
        "markPrice": "36000.0",
        "unRealizedProfit": "2.0",
        "marginType": "isolated"
    }
    
    # Kiểm tra dữ liệu k-lines
    print("Kiểm tra dữ liệu k-lines hợp lệ:")
    is_valid, errors = validator.validate_binance_klines_data(klines_data_valid)
    print(f"Hợp lệ: {is_valid}")
    if not is_valid:
        print(f"Lỗi: {errors}")
    
    print("\nKiểm tra dữ liệu k-lines không hợp lệ:")
    is_valid, errors = validator.validate_binance_klines_data(klines_data_invalid)
    print(f"Hợp lệ: {is_valid}")
    if not is_valid:
        print(f"Lỗi: {errors}")
    
    # Kiểm tra dữ liệu position
    print("\nKiểm tra dữ liệu position hợp lệ:")
    is_valid, errors = validator.validate_binance_position_data(position_data_valid)
    print(f"Hợp lệ: {is_valid}")
    if not is_valid:
        print(f"Lỗi: {errors}")
    
    print("\nKiểm tra dữ liệu position không hợp lệ:")
    is_valid, errors = validator.validate_binance_position_data(position_data_invalid)
    print(f"Hợp lệ: {is_valid}")
    if not is_valid:
        print(f"Lỗi: {errors}")
    
    # Chuyển đổi dữ liệu
    print("\nChuyển đổi dữ liệu k-lines:")
    transformed_klines = validator.transform_binance_klines(klines_data_valid)
    print(f"Số lượng k-lines sau chuyển đổi: {len(transformed_klines)}")
    if transformed_klines:
        print(f"Mẫu dữ liệu đã chuyển đổi: {transformed_klines[0]}")
    
    print("\nChuyển đổi dữ liệu position:")
    transformed_position = validator.transform_binance_position(position_data_valid)
    print(f"Dữ liệu position đã chuyển đổi: {transformed_position}")


if __name__ == "__main__":
    main()