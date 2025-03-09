"""
Module thực thi lệnh (Order Execution)

Module này cung cấp các chiến lược thực thi lệnh giao dịch khác nhau để tối ưu hóa
giá thực thi và giảm thiểu trượt giá (slippage) trong các điều kiện thị trường khác nhau.
"""

import time
import math
import logging
import random
from typing import Dict, List, Optional, Union, Any, Tuple
import threading
from datetime import datetime, timedelta
import traceback

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("order_execution")

class BaseOrderExecutor:
    """Lớp cơ sở cho tất cả các chiến lược thực thi lệnh"""
    
    def __init__(self, binance_api=None, symbol: str = None, side: str = None, 
              quantity: float = None, price: float = None):
        """
        Khởi tạo order executor
        
        Args:
            binance_api: Đối tượng BinanceAPI
            symbol (str, optional): Symbol giao dịch
            side (str, optional): Hướng giao dịch ('BUY' hoặc 'SELL')
            quantity (float, optional): Số lượng
            price (float, optional): Giá đặt lệnh
        """
        self.binance_api = binance_api
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.order_type = 'LIMIT'
        self.orders = []
        self.order_status = {}
        self.execution_details = {
            'start_time': None,
            'end_time': None,
            'filled_quantity': 0,
            'avg_price': 0,
            'total_cost': 0,
            'fees': 0,
            'orders': [],
            'slippage': 0,
            'execution_time': 0,
            'status': 'initialized'
        }
        
    def execute(self, **kwargs) -> Dict:
        """
        Thực thi lệnh
        
        Args:
            **kwargs: Tham số bổ sung
            
        Returns:
            Dict: Thông tin chi tiết về việc thực thi
        """
        # Đặt thời gian bắt đầu
        self.execution_details['start_time'] = datetime.now()
        
        # Cài đặt tham số nếu có
        self.symbol = kwargs.get('symbol', self.symbol)
        self.side = kwargs.get('side', self.side)
        self.quantity = kwargs.get('quantity', self.quantity)
        self.price = kwargs.get('price', self.price)
        
        # Kiểm tra tham số
        if not self._validate_params():
            self.execution_details['status'] = 'failed'
            self.execution_details['end_time'] = datetime.now()
            self.execution_details['execution_time'] = (self.execution_details['end_time'] - 
                                                     self.execution_details['start_time']).total_seconds()
            return self.execution_details
            
        try:
            # Thực thi lệnh (cần được ghi đè bởi lớp con)
            self._execute_strategy(**kwargs)
            
            # Cập nhật chi tiết thực thi
            self.execution_details['end_time'] = datetime.now()
            self.execution_details['execution_time'] = (self.execution_details['end_time'] - 
                                                    self.execution_details['start_time']).total_seconds()
            
            # Tính toán slippage nếu có giá tham chiếu
            if self.price and self.execution_details['avg_price'] > 0:
                if self.side == 'BUY':
                    self.execution_details['slippage'] = ((self.execution_details['avg_price'] - self.price) 
                                                       / self.price * 100)
                else:  # SELL
                    self.execution_details['slippage'] = ((self.price - self.execution_details['avg_price']) 
                                                       / self.price * 100)
            
            return self.execution_details
            
        except Exception as e:
            logger.error(f"Lỗi khi thực thi lệnh: {str(e)}")
            logger.error(traceback.format_exc())
            
            self.execution_details['status'] = 'error'
            self.execution_details['error'] = str(e)
            self.execution_details['end_time'] = datetime.now()
            self.execution_details['execution_time'] = (self.execution_details['end_time'] - 
                                                     self.execution_details['start_time']).total_seconds()
            
            return self.execution_details
    
    def _execute_strategy(self, **kwargs) -> None:
        """
        Chiến lược thực thi cụ thể (cần được ghi đè bởi lớp con)
        
        Args:
            **kwargs: Tham số bổ sung
        """
        raise NotImplementedError("Phương thức _execute_strategy phải được ghi đè")
    
    def _validate_params(self) -> bool:
        """
        Kiểm tra tham số
        
        Returns:
            bool: True nếu tham số hợp lệ, False nếu không
        """
        if not self.symbol:
            logger.error("Symbol không được cung cấp")
            return False
            
        if not self.side:
            logger.error("Side không được cung cấp")
            return False
            
        if not self.quantity or self.quantity <= 0:
            logger.error("Quantity không hợp lệ")
            return False
            
        return True
    
    def _update_execution_details(self, order_info: Dict) -> None:
        """
        Cập nhật chi tiết thực thi từ thông tin lệnh
        
        Args:
            order_info (Dict): Thông tin lệnh từ Binance API
        """
        # Thêm order vào danh sách
        self.orders.append(order_info)
        self.execution_details['orders'].append(order_info)
        
        # Cập nhật trạng thái
        order_id = order_info.get('orderId')
        if order_id:
            self.order_status[order_id] = order_info.get('status', 'NEW')
            
        # Tính toán số lượng đã khớp và giá trung bình
        filled_qty = float(order_info.get('executedQty', 0))
        avg_price = float(order_info.get('price', 0))
        
        # Nếu là lệnh thị trường, sử dụng giá trung bình
        if self.order_type == 'MARKET' and filled_qty > 0:
            avg_price = float(order_info.get('cummulativeQuoteQty', 0)) / filled_qty
            
        # Cập nhật chi tiết
        self.execution_details['filled_quantity'] += filled_qty
        
        # Tính toán giá trung bình mới
        if self.execution_details['filled_quantity'] > 0:
            old_cost = self.execution_details['avg_price'] * (self.execution_details['filled_quantity'] - filled_qty)
            new_cost = avg_price * filled_qty
            self.execution_details['avg_price'] = (old_cost + new_cost) / self.execution_details['filled_quantity']
            
        # Tính tổng chi phí
        self.execution_details['total_cost'] = self.execution_details['avg_price'] * self.execution_details['filled_quantity']
        
        # Cập nhật trạng thái thực thi
        if self.execution_details['filled_quantity'] >= self.quantity:
            self.execution_details['status'] = 'completed'
        elif self.execution_details['filled_quantity'] > 0:
            self.execution_details['status'] = 'partially_filled'
        else:
            self.execution_details['status'] = 'pending'
    
    def cancel_all_orders(self) -> bool:
        """
        Hủy tất cả các lệnh đang mở
        
        Returns:
            bool: True nếu hủy thành công, False nếu không
        """
        if not self.binance_api:
            logger.error("Không có kết nối Binance API")
            return False
            
        try:
            # Hủy tất cả các lệnh đang mở cho symbol
            result = self.binance_api.cancel_open_orders(symbol=self.symbol)
            
            # Cập nhật trạng thái
            for order_id in self.order_status:
                self.order_status[order_id] = 'CANCELED'
                
            self.execution_details['status'] = 'canceled'
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi hủy lệnh: {str(e)}")
            return False
    
    def get_execution_details(self) -> Dict:
        """
        Lấy chi tiết thực thi
        
        Returns:
            Dict: Chi tiết thực thi
        """
        return self.execution_details
    
    def get_order_status(self, order_id: str = None) -> Union[Dict, str]:
        """
        Lấy trạng thái lệnh
        
        Args:
            order_id (str, optional): ID của lệnh, nếu None sẽ trả về tất cả
            
        Returns:
            Union[Dict, str]: Trạng thái lệnh
        """
        if order_id:
            return self.order_status.get(order_id)
        return self.order_status

class MarketOrderExecutor(BaseOrderExecutor):
    """Thực thi lệnh thị trường (Market Order)"""
    
    def __init__(self, binance_api=None, symbol: str = None, side: str = None, 
              quantity: float = None, price: float = None):
        """
        Khởi tạo Market Order Executor
        
        Args:
            binance_api: Đối tượng BinanceAPI
            symbol (str, optional): Symbol giao dịch
            side (str, optional): Hướng giao dịch ('BUY' hoặc 'SELL')
            quantity (float, optional): Số lượng
            price (float, optional): Giá tham chiếu (không sử dụng trong lệnh thị trường)
        """
        super().__init__(binance_api, symbol, side, quantity, price)
        self.order_type = 'MARKET'
    
    def _execute_strategy(self, **kwargs) -> None:
        """
        Thực thi lệnh thị trường
        
        Args:
            **kwargs: Tham số bổ sung
        """
        if not self.binance_api:
            raise ValueError("Không có kết nối Binance API")
            
        # Đặt lệnh thị trường
        order_params = {
            'symbol': self.symbol,
            'side': self.side,
            'type': 'MARKET',
            'quantity': self.quantity
        }
        
        # Thêm các tham số bổ sung
        for key, value in kwargs.items():
            if key not in order_params:
                order_params[key] = value
                
        # Chỉ thêm tham số mới từ kwargs
        order_params.update({k: v for k, v in kwargs.items() if k not in order_params})
                
        # Đặt lệnh
        order_info = self.binance_api.create_order(**order_params)
        
        # Cập nhật chi tiết thực thi
        self._update_execution_details(order_info)
        
        # Lệnh thị trường thường hoàn thành ngay lập tức, nên kiểm tra lại nếu cần
        if self.execution_details['status'] == 'pending':
            time.sleep(1)  # Đợi 1 giây
            
            # Kiểm tra lại trạng thái lệnh
            try:
                updated_order = self.binance_api.get_order(
                    symbol=self.symbol,
                    order_id=order_info.get('orderId')
                )
                self._update_execution_details(updated_order)
            except Exception as e:
                logger.warning(f"Không thể cập nhật trạng thái lệnh: {str(e)}")

class LimitOrderExecutor(BaseOrderExecutor):
    """Thực thi lệnh giới hạn (Limit Order)"""
    
    def __init__(self, binance_api=None, symbol: str = None, side: str = None, 
              quantity: float = None, price: float = None, 
              time_in_force: str = 'GTC', post_only: bool = False):
        """
        Khởi tạo Limit Order Executor
        
        Args:
            binance_api: Đối tượng BinanceAPI
            symbol (str, optional): Symbol giao dịch
            side (str, optional): Hướng giao dịch ('BUY' hoặc 'SELL')
            quantity (float, optional): Số lượng
            price (float, optional): Giá đặt lệnh
            time_in_force (str): Thời gian hiệu lực (GTC, IOC, FOK)
            post_only (bool): Chỉ để lệnh vào orderbook, không khớp ngay
        """
        super().__init__(binance_api, symbol, side, quantity, price)
        self.order_type = 'LIMIT'
        self.time_in_force = time_in_force
        self.post_only = post_only
    
    def _execute_strategy(self, **kwargs) -> None:
        """
        Thực thi lệnh giới hạn
        
        Args:
            **kwargs: Tham số bổ sung
        """
        if not self.binance_api:
            raise ValueError("Không có kết nối Binance API")
            
        if not self.price or self.price <= 0:
            raise ValueError("Giá không hợp lệ cho lệnh giới hạn")
            
        # Đặt lệnh giới hạn
        order_params = {
            'symbol': self.symbol,
            'side': self.side,
            'type': 'LIMIT',
            'timeInForce': self.time_in_force,
            'quantity': self.quantity,
            'price': self.price
        }
        
        # Thêm tham số post-only nếu cần
        if self.post_only:
            # Binance sử dụng 'LIMIT_MAKER' cho post-only
            order_params['type'] = 'LIMIT_MAKER'
            # Xóa timeInForce vì LIMIT_MAKER không cần
            order_params.pop('timeInForce', None)
            
        # Thêm các tham số bổ sung
        order_params.update({k: v for k, v in kwargs.items() if k not in order_params})
            
        # Đặt lệnh
        order_info = self.binance_api.create_order(**order_params)
        
        # Cập nhật chi tiết thực thi
        self._update_execution_details(order_info)
        
        # Với lệnh giới hạn, theo dõi trạng thái
        self._monitor_order_status(order_info.get('orderId'), kwargs.get('timeout', 60))
    
    def _monitor_order_status(self, order_id: str, timeout: int = 60) -> None:
        """
        Theo dõi trạng thái lệnh
        
        Args:
            order_id (str): ID của lệnh
            timeout (int): Thời gian chờ tối đa (giây)
        """
        if not order_id:
            return
            
        start_time = time.time()
        
        # Theo dõi trạng thái cho đến khi hết thời gian hoặc lệnh hoàn thành
        while time.time() - start_time < timeout:
            try:
                # Kiểm tra trạng thái lệnh
                order_info = self.binance_api.get_order(
                    symbol=self.symbol,
                    order_id=order_id
                )
                
                # Cập nhật chi tiết
                self._update_execution_details(order_info)
                
                # Nếu lệnh đã hoàn thành, thoát
                if order_info.get('status') in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                    break
                    
                # Đợi một chút trước khi kiểm tra lại
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Lỗi khi kiểm tra trạng thái lệnh: {str(e)}")
                break

class IcebergOrderExecutor(BaseOrderExecutor):
    """Thực thi lệnh băng sơn (Iceberg Order)"""
    
    def __init__(self, binance_api=None, symbol: str = None, side: str = None, 
              quantity: float = None, price: float = None, 
              iceberg_parts: int = 5, price_variance: float = 0.0,
              time_in_force: str = 'GTC'):
        """
        Khởi tạo Iceberg Order Executor
        
        Args:
            binance_api: Đối tượng BinanceAPI
            symbol (str, optional): Symbol giao dịch
            side (str, optional): Hướng giao dịch ('BUY' hoặc 'SELL')
            quantity (float, optional): Tổng số lượng
            price (float, optional): Giá cơ sở
            iceberg_parts (int): Số phần chia lệnh
            price_variance (float): Phần trăm biến động giá giữa các phần
            time_in_force (str): Thời gian hiệu lực (GTC, IOC, FOK)
        """
        super().__init__(binance_api, symbol, side, quantity, price)
        self.order_type = 'LIMIT'  # Iceberg sử dụng các lệnh LIMIT
        self.iceberg_parts = max(1, iceberg_parts)
        self.price_variance = price_variance
        self.time_in_force = time_in_force
        self.active_orders = []
    
    def _execute_strategy(self, **kwargs) -> None:
        """
        Thực thi chiến lược băng sơn
        
        Args:
            **kwargs: Tham số bổ sung
        """
        if not self.binance_api:
            raise ValueError("Không có kết nối Binance API")
            
        if not self.price or self.price <= 0:
            raise ValueError("Giá không hợp lệ cho lệnh băng sơn")
            
        # Tính toán kích thước cho mỗi phần
        part_size = self.quantity / self.iceberg_parts
        
        # Làm tròn part_size theo quy tắc của sàn
        try:
            symbol_info = self.binance_api.get_symbol_info(self.symbol)
            lot_size_filter = next((f for f in symbol_info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'), None)
            
            if lot_size_filter:
                step_size = float(lot_size_filter.get('stepSize', 0.00000001))
                part_size = math.floor(part_size / step_size) * step_size
        except Exception as e:
            logger.warning(f"Không thể lấy thông tin symbol để làm tròn kích thước: {str(e)}")
            
        # Đặt các lệnh riêng lẻ
        remaining_qty = self.quantity
        orders_placed = 0
        
        for i in range(self.iceberg_parts):
            # Nếu đã đặt đủ số lượng, dừng lại
            if remaining_qty <= 0:
                break
                
            # Tính toán số lượng cho phần này
            this_part_size = min(part_size, remaining_qty)
            
            # Tính giá cho phần này
            variance_factor = self.price_variance / 100 * (i - (self.iceberg_parts - 1) / 2)
            this_price = self.price * (1 + variance_factor)
            
            # Làm tròn giá theo quy tắc của sàn
            try:
                price_filter = next((f for f in symbol_info.get('filters', []) if f.get('filterType') == 'PRICE_FILTER'), None)
                
                if price_filter:
                    tick_size = float(price_filter.get('tickSize', 0.00000001))
                    this_price = math.floor(this_price / tick_size) * tick_size
            except Exception:
                pass
                
            # Đặt lệnh
            try:
                order_params = {
                    'symbol': self.symbol,
                    'side': self.side,
                    'type': 'LIMIT',
                    'timeInForce': self.time_in_force,
                    'quantity': this_part_size,
                    'price': this_price
                }
                
                # Thêm các tham số bổ sung
                for key, value in kwargs.items():
                    if key not in order_params:
                        order_params[key] = value
                        
                # Đặt lệnh
                order_info = self.binance_api.create_order(**order_params)
                
                # Cập nhật chi tiết
                self._update_execution_details(order_info)
                
                # Thêm vào danh sách lệnh đang hoạt động
                self.active_orders.append(order_info.get('orderId'))
                
                # Cập nhật số lượng còn lại
                remaining_qty -= this_part_size
                orders_placed += 1
                
                # Đợi một chút để tránh rate limit
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh phần {i+1}: {str(e)}")
                continue
                
        logger.info(f"Đã đặt {orders_placed}/{self.iceberg_parts} lệnh băng sơn")
        
        # Theo dõi các lệnh đã đặt
        self._monitor_iceberg_orders(kwargs.get('timeout', 300))
    
    def _monitor_iceberg_orders(self, timeout: int = 300) -> None:
        """
        Theo dõi các lệnh băng sơn
        
        Args:
            timeout (int): Thời gian chờ tối đa (giây)
        """
        if not self.active_orders:
            return
            
        start_time = time.time()
        
        # Theo dõi trạng thái cho đến khi hết thời gian hoặc tất cả lệnh hoàn thành
        while time.time() - start_time < timeout and self.active_orders:
            # Tạo bản sao để tránh thay đổi trong vòng lặp
            orders_to_check = self.active_orders.copy()
            
            for order_id in orders_to_check:
                try:
                    # Kiểm tra trạng thái lệnh
                    order_info = self.binance_api.get_order(
                        symbol=self.symbol,
                        order_id=order_id
                    )
                    
                    # Cập nhật chi tiết
                    self._update_execution_details(order_info)
                    
                    # Nếu lệnh đã hoàn thành, xóa khỏi danh sách đang theo dõi
                    if order_info.get('status') in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                        self.active_orders.remove(order_id)
                        
                except Exception as e:
                    logger.warning(f"Lỗi khi kiểm tra trạng thái lệnh {order_id}: {str(e)}")
                    # Khả năng là lệnh không còn tồn tại
                    self.active_orders.remove(order_id)
                    
            # Đợi một chút trước khi kiểm tra lại
            time.sleep(3)
            
        # Cập nhật trạng thái cuối cùng
        if not self.active_orders and self.execution_details['filled_quantity'] >= self.quantity:
            self.execution_details['status'] = 'completed'
        elif not self.active_orders:
            self.execution_details['status'] = 'partially_filled'
        else:
            self.execution_details['status'] = 'timeout'

class TWAPExecutor(BaseOrderExecutor):
    """Thực thi lệnh theo thuật toán TWAP (Time-Weighted Average Price)"""
    
    def __init__(self, binance_api=None, symbol: str = None, side: str = None, 
              quantity: float = None, price: float = None, 
              duration: int = 3600, intervals: int = 12,
              price_variance: float = 0.1, use_market_orders: bool = False):
        """
        Khởi tạo TWAP Executor
        
        Args:
            binance_api: Đối tượng BinanceAPI
            symbol (str, optional): Symbol giao dịch
            side (str, optional): Hướng giao dịch ('BUY' hoặc 'SELL')
            quantity (float, optional): Tổng số lượng
            price (float, optional): Giá tham chiếu
            duration (int): Tổng thời gian thực thi (giây)
            intervals (int): Số lần đặt lệnh
            price_variance (float): Phần trăm biến động giá cho phép
            use_market_orders (bool): Sử dụng lệnh thị trường thay vì lệnh giới hạn
        """
        super().__init__(binance_api, symbol, side, quantity, price)
        self.duration = duration
        self.intervals = max(1, intervals)
        self.price_variance = price_variance
        self.use_market_orders = use_market_orders
        self.active_orders = []
        self.stop_event = threading.Event()
    
    def _execute_strategy(self, **kwargs) -> None:
        """
        Thực thi chiến lược TWAP
        
        Args:
            **kwargs: Tham số bổ sung
        """
        if not self.binance_api:
            raise ValueError("Không có kết nối Binance API")
            
        # Tính toán thời gian cho mỗi interval
        interval_seconds = self.duration / self.intervals
        
        # Tính toán kích thước cho mỗi lệnh
        order_quantity = self.quantity / self.intervals
        
        # Làm tròn order_quantity theo quy tắc của sàn
        try:
            symbol_info = self.binance_api.get_symbol_info(self.symbol)
            lot_size_filter = next((f for f in symbol_info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'), None)
            
            if lot_size_filter:
                step_size = float(lot_size_filter.get('stepSize', 0.00000001))
                order_quantity = math.floor(order_quantity / step_size) * step_size
        except Exception as e:
            logger.warning(f"Không thể lấy thông tin symbol để làm tròn kích thước: {str(e)}")
            
        # Tính giá hiện tại nếu không có giá tham chiếu
        if not self.price or self.price <= 0:
            try:
                ticker = self.binance_api.get_symbol_ticker(symbol=self.symbol)
                self.price = float(ticker.get('price', 0))
            except Exception as e:
                logger.error(f"Không thể lấy giá hiện tại: {str(e)}")
                raise ValueError("Không có giá tham chiếu và không thể lấy giá hiện tại")
                
        # Kết quả của thuật toán
        total_filled = 0
        orders_executed = 0
        
        # Khởi chạy TWAP
        start_time = time.time()
        next_execution_time = start_time
        
        logger.info(f"Bắt đầu TWAP: {self.intervals} lệnh trong {self.duration} giây")
        
        for i in range(self.intervals):
            # Nếu đã nhận lệnh hủy, dừng lại
            if self.stop_event.is_set():
                logger.info("TWAP nhận lệnh hủy, dừng lại")
                break
                
            # Tính toán số lượng còn lại
            remaining_qty = self.quantity - total_filled
            
            # Nếu đã thực thi đủ, dừng lại
            if remaining_qty <= 0:
                logger.info("TWAP đã thực thi đủ số lượng")
                break
                
            # Tính toán số lượng cho lệnh này
            this_qty = min(order_quantity, remaining_qty)
            
            # Đợi đến thời điểm thực thi
            current_time = time.time()
            if current_time < next_execution_time:
                wait_time = next_execution_time - current_time
                time.sleep(wait_time)
                
            # Cập nhật giá nếu cần
            if not self.use_market_orders:
                try:
                    ticker = self.binance_api.get_symbol_ticker(symbol=self.symbol)
                    current_price = float(ticker.get('price', 0))
                    
                    # Tính giá cho lệnh này với biến động ngẫu nhiên
                    price_variance = random.uniform(-self.price_variance, self.price_variance) / 100
                    this_price = current_price * (1 + price_variance)
                    
                    # Làm tròn giá
                    try:
                        price_filter = next((f for f in symbol_info.get('filters', []) if f.get('filterType') == 'PRICE_FILTER'), None)
                        
                        if price_filter:
                            tick_size = float(price_filter.get('tickSize', 0.00000001))
                            this_price = math.floor(this_price / tick_size) * tick_size
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(f"Không thể cập nhật giá: {str(e)}")
                    this_price = self.price
            
            # Đặt lệnh
            try:
                if self.use_market_orders:
                    order_params = {
                        'symbol': self.symbol,
                        'side': self.side,
                        'type': 'MARKET',
                        'quantity': this_qty
                    }
                else:
                    order_params = {
                        'symbol': self.symbol,
                        'side': self.side,
                        'type': 'LIMIT',
                        'timeInForce': 'GTC',
                        'quantity': this_qty,
                        'price': this_price
                    }
                    
                # Thêm các tham số bổ sung
                for key, value in kwargs.items():
                    if key not in order_params:
                        order_params[key] = value
                        
                # Đặt lệnh
                order_info = self.binance_api.create_order(**order_params)
                
                # Cập nhật chi tiết
                self._update_execution_details(order_info)
                
                # Với lệnh giới hạn, thêm vào danh sách đang theo dõi
                if not self.use_market_orders:
                    self.active_orders.append(order_info.get('orderId'))
                    
                # Cập nhật số lượng đã thực thi
                total_filled += float(order_info.get('executedQty', 0))
                orders_executed += 1
                
                logger.info(f"TWAP lệnh {i+1}/{self.intervals}: {this_qty} @ {this_price if not self.use_market_orders else 'MARKET'}")
                
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh TWAP {i+1}: {str(e)}")
                
            # Cập nhật thời điểm thực thi tiếp theo
            next_execution_time = start_time + (i + 1) * interval_seconds
            
        # Chờ các lệnh giới hạn hoàn thành
        if not self.use_market_orders and self.active_orders:
            self._monitor_twap_orders(kwargs.get('timeout', 300))
            
        # Cập nhật kết quả cuối cùng
        end_time = time.time()
        self.execution_details['status'] = 'completed' if total_filled >= self.quantity else 'partially_filled'
        
        logger.info(f"TWAP kết thúc: {orders_executed}/{self.intervals} lệnh, {total_filled}/{self.quantity} khớp")
    
    def _monitor_twap_orders(self, timeout: int = 300) -> None:
        """
        Theo dõi các lệnh TWAP
        
        Args:
            timeout (int): Thời gian chờ tối đa (giây)
        """
        if not self.active_orders:
            return
            
        start_time = time.time()
        
        # Theo dõi trạng thái cho đến khi hết thời gian hoặc tất cả lệnh hoàn thành
        while time.time() - start_time < timeout and self.active_orders:
            # Tạo bản sao để tránh thay đổi trong vòng lặp
            orders_to_check = self.active_orders.copy()
            
            for order_id in orders_to_check:
                try:
                    # Kiểm tra trạng thái lệnh
                    order_info = self.binance_api.get_order(
                        symbol=self.symbol,
                        order_id=order_id
                    )
                    
                    # Cập nhật chi tiết
                    self._update_execution_details(order_info)
                    
                    # Nếu lệnh đã hoàn thành, xóa khỏi danh sách đang theo dõi
                    if order_info.get('status') in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                        self.active_orders.remove(order_id)
                        
                except Exception as e:
                    logger.warning(f"Lỗi khi kiểm tra trạng thái lệnh {order_id}: {str(e)}")
                    # Khả năng là lệnh không còn tồn tại
                    if order_id in self.active_orders:
                        self.active_orders.remove(order_id)
                    
            # Đợi một chút trước khi kiểm tra lại
            time.sleep(5)
    
    def stop(self) -> None:
        """Dừng chiến lược TWAP đang chạy"""
        self.stop_event.set()
        
        # Hủy các lệnh đang chờ
        if self.active_orders:
            for order_id in self.active_orders:
                try:
                    self.binance_api.cancel_order(
                        symbol=self.symbol,
                        order_id=order_id
                    )
                except Exception as e:
                    logger.warning(f"Không thể hủy lệnh {order_id}: {str(e)}")
                    
            self.active_orders = []

class ScaledOrderExecutor(BaseOrderExecutor):
    """Thực thi lệnh theo thuật toán Scaled Order (đặt nhiều lệnh ở các mức giá khác nhau)"""
    
    def __init__(self, binance_api=None, symbol: str = None, side: str = None, 
              quantity: float = None, price: float = None, 
              scale_levels: int = 5, price_range_pct: float = 2.0,
              distribution: str = 'linear'):
        """
        Khởi tạo Scaled Order Executor
        
        Args:
            binance_api: Đối tượng BinanceAPI
            symbol (str, optional): Symbol giao dịch
            side (str, optional): Hướng giao dịch ('BUY' hoặc 'SELL')
            quantity (float, optional): Tổng số lượng
            price (float, optional): Giá trung tâm
            scale_levels (int): Số lượng mức giá
            price_range_pct (float): Phần trăm biên độ giá (từ thấp nhất đến cao nhất)
            distribution (str): Cách phân bổ ('linear', 'geometric', 'uniform')
        """
        super().__init__(binance_api, symbol, side, quantity, price)
        self.scale_levels = max(2, scale_levels)
        self.price_range_pct = price_range_pct
        self.distribution = distribution
        self.active_orders = []
    
    def _execute_strategy(self, **kwargs) -> None:
        """
        Thực thi chiến lược Scaled Order
        
        Args:
            **kwargs: Tham số bổ sung
        """
        if not self.binance_api:
            raise ValueError("Không có kết nối Binance API")
            
        # Tính giá hiện tại nếu không có giá trung tâm
        if not self.price or self.price <= 0:
            try:
                ticker = self.binance_api.get_symbol_ticker(symbol=self.symbol)
                self.price = float(ticker.get('price', 0))
            except Exception as e:
                logger.error(f"Không thể lấy giá hiện tại: {str(e)}")
                raise ValueError("Không có giá trung tâm và không thể lấy giá hiện tại")
                
        # Tính toán khoảng giá
        price_range = self.price * self.price_range_pct / 100
        
        if self.side == 'BUY':
            # Đối với lệnh mua, đặt từ thấp đến cao
            min_price = self.price - price_range
            max_price = self.price
        else:  # SELL
            # Đối với lệnh bán, đặt từ cao đến thấp
            min_price = self.price
            max_price = self.price + price_range
            
        # Tạo các mức giá dựa trên phân bổ đã chọn
        price_levels = []
        
        if self.distribution == 'linear':
            # Phân bổ tuyến tính
            for i in range(self.scale_levels):
                price_levels.append(min_price + (max_price - min_price) * i / (self.scale_levels - 1))
                
        elif self.distribution == 'geometric':
            # Phân bổ hình học (tỷ lệ tăng/giảm đều)
            ratio = (max_price / min_price) ** (1 / (self.scale_levels - 1))
            for i in range(self.scale_levels):
                price_levels.append(min_price * (ratio ** i))
                
        else:  # uniform
            # Phân bổ đều
            for i in range(self.scale_levels):
                price_levels.append(min_price + (max_price - min_price) * i / (self.scale_levels - 1))
                
        # Nếu là lệnh bán, đảo ngược mảng để đặt từ cao xuống thấp
        if self.side == 'SELL':
            price_levels.reverse()
            
        # Phân bổ số lượng vào các mức giá
        quantity_levels = []
        
        if self.distribution == 'linear':
            # Phân bổ số lượng tuyến tính (nhiều hơn ở gần giá hiện tại)
            total_weight = sum(range(1, self.scale_levels + 1))
            for i in range(self.scale_levels):
                weight = (i + 1) / total_weight
                quantity_levels.append(self.quantity * weight)
                
        elif self.distribution == 'geometric':
            # Phân bổ số lượng hình học
            weights = [2 ** i for i in range(self.scale_levels)]
            total_weight = sum(weights)
            for i in range(self.scale_levels):
                quantity_levels.append(self.quantity * weights[i] / total_weight)
                
        else:  # uniform
            # Phân bổ số lượng đều
            for i in range(self.scale_levels):
                quantity_levels.append(self.quantity / self.scale_levels)
                
        # Đặt các lệnh
        symbol_info = None
        try:
            symbol_info = self.binance_api.get_symbol_info(self.symbol)
        except Exception as e:
            logger.warning(f"Không thể lấy thông tin symbol: {str(e)}")
            
        # Làm tròn giá và số lượng
        rounded_price_levels = []
        rounded_quantity_levels = []
        
        for price in price_levels:
            # Làm tròn giá
            if symbol_info:
                try:
                    price_filter = next((f for f in symbol_info.get('filters', []) if f.get('filterType') == 'PRICE_FILTER'), None)
                    
                    if price_filter:
                        tick_size = float(price_filter.get('tickSize', 0.00000001))
                        price = math.floor(price / tick_size) * tick_size
                except Exception:
                    pass
                    
            rounded_price_levels.append(price)
            
        for qty in quantity_levels:
            # Làm tròn số lượng
            if symbol_info:
                try:
                    lot_size_filter = next((f for f in symbol_info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'), None)
                    
                    if lot_size_filter:
                        step_size = float(lot_size_filter.get('stepSize', 0.00000001))
                        qty = math.floor(qty / step_size) * step_size
                except Exception:
                    pass
                    
            rounded_quantity_levels.append(qty)
            
        # Đặt các lệnh
        orders_executed = 0
        
        for i in range(self.scale_levels):
            try:
                order_params = {
                    'symbol': self.symbol,
                    'side': self.side,
                    'type': 'LIMIT',
                    'timeInForce': 'GTC',
                    'quantity': rounded_quantity_levels[i],
                    'price': rounded_price_levels[i]
                }
                
                # Thêm các tham số bổ sung
                for key, value in kwargs.items():
                    if key not in order_params:
                        order_params[key] = value
                        
                # Đặt lệnh
                order_info = self.binance_api.create_order(**order_params)
                
                # Cập nhật chi tiết
                self._update_execution_details(order_info)
                
                # Thêm vào danh sách đang theo dõi
                self.active_orders.append(order_info.get('orderId'))
                
                orders_executed += 1
                
                logger.info(f"Scaled Order {i+1}/{self.scale_levels}: {rounded_quantity_levels[i]} @ {rounded_price_levels[i]}")
                
                # Đợi một chút để tránh rate limit
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Lỗi khi đặt lệnh Scaled Order {i+1}: {str(e)}")
                
        logger.info(f"Đã đặt {orders_executed}/{self.scale_levels} lệnh Scaled Order")
        
        # Theo dõi các lệnh
        self._monitor_scaled_orders(kwargs.get('timeout', 600))
    
    def _monitor_scaled_orders(self, timeout: int = 600) -> None:
        """
        Theo dõi các lệnh Scaled Order
        
        Args:
            timeout (int): Thời gian chờ tối đa (giây)
        """
        if not self.active_orders:
            return
            
        start_time = time.time()
        
        # Theo dõi trạng thái cho đến khi hết thời gian hoặc tất cả lệnh hoàn thành
        while time.time() - start_time < timeout and self.active_orders:
            # Tạo bản sao để tránh thay đổi trong vòng lặp
            orders_to_check = self.active_orders.copy()
            
            for order_id in orders_to_check:
                try:
                    # Kiểm tra trạng thái lệnh
                    order_info = self.binance_api.get_order(
                        symbol=self.symbol,
                        order_id=order_id
                    )
                    
                    # Cập nhật chi tiết
                    self._update_execution_details(order_info)
                    
                    # Nếu lệnh đã hoàn thành, xóa khỏi danh sách đang theo dõi
                    if order_info.get('status') in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                        self.active_orders.remove(order_id)
                        
                except Exception as e:
                    logger.warning(f"Lỗi khi kiểm tra trạng thái lệnh {order_id}: {str(e)}")
                    # Khả năng là lệnh không còn tồn tại
                    if order_id in self.active_orders:
                        self.active_orders.remove(order_id)
                    
            # Đợi một chút trước khi kiểm tra lại
            time.sleep(5)
            
        # Cập nhật trạng thái cuối cùng
        if not self.active_orders and self.execution_details['filled_quantity'] >= self.quantity:
            self.execution_details['status'] = 'completed'
        elif not self.active_orders:
            self.execution_details['status'] = 'partially_filled'
        else:
            self.execution_details['status'] = 'timeout'
            
    def cancel_all(self) -> None:
        """Hủy tất cả các lệnh Scaled Order đang chờ"""
        if not self.active_orders:
            return
            
        for order_id in self.active_orders:
            try:
                self.binance_api.cancel_order(
                    symbol=self.symbol,
                    order_id=order_id
                )
            except Exception as e:
                logger.warning(f"Không thể hủy lệnh {order_id}: {str(e)}")
                
        self.active_orders = []
        self.execution_details['status'] = 'canceled'

class OCOOrderExecutor(BaseOrderExecutor):
    """Thực thi lệnh OCO (One-Cancels-the-Other)"""
    
    def __init__(self, binance_api=None, symbol: str = None, side: str = None, 
              quantity: float = None, price: float = None, 
              stop_price: float = None, stop_limit_price: float = None):
        """
        Khởi tạo OCO Order Executor
        
        Args:
            binance_api: Đối tượng BinanceAPI
            symbol (str, optional): Symbol giao dịch
            side (str, optional): Hướng giao dịch ('BUY' hoặc 'SELL')
            quantity (float, optional): Số lượng
            price (float, optional): Giá limit
            stop_price (float, optional): Giá stop
            stop_limit_price (float, optional): Giá stop limit
        """
        super().__init__(binance_api, symbol, side, quantity, price)
        self.order_type = 'OCO'
        self.stop_price = stop_price
        self.stop_limit_price = stop_limit_price or stop_price
    
    def _execute_strategy(self, **kwargs) -> None:
        """
        Thực thi lệnh OCO
        
        Args:
            **kwargs: Tham số bổ sung
        """
        if not self.binance_api:
            raise ValueError("Không có kết nối Binance API")
            
        if not self.price or self.price <= 0:
            raise ValueError("Giá limit không hợp lệ")
            
        if not self.stop_price or self.stop_price <= 0:
            raise ValueError("Giá stop không hợp lệ")
            
        # Đặt lệnh OCO
        try:
            order_params = {
                'symbol': self.symbol,
                'side': self.side,
                'quantity': self.quantity,
                'price': self.price,
                'stopPrice': self.stop_price,
                'stopLimitPrice': self.stop_limit_price,
                'stopLimitTimeInForce': 'GTC'
            }
            
            # Thêm các tham số bổ sung
            for key, value in kwargs.items():
                if key not in order_params:
                    order_params[key] = value
                    
            # Đặt lệnh OCO
            order_info = self.binance_api.create_oco_order(**order_params)
            
            # Cập nhật chi tiết
            self._update_execution_details_oco(order_info)
            
            logger.info(f"Đã đặt lệnh OCO: {self.quantity} @ limit: {self.price}, stop: {self.stop_price}")
            
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh OCO: {str(e)}")
            self.execution_details['status'] = 'error'
            self.execution_details['error'] = str(e)
    
    def _update_execution_details_oco(self, order_info: Dict) -> None:
        """
        Cập nhật chi tiết thực thi từ thông tin lệnh OCO
        
        Args:
            order_info (Dict): Thông tin lệnh OCO từ Binance API
        """
        # OCO trả về danh sách các lệnh (limit và stop_limit)
        self.orders = order_info.get('orderReports', [])
        
        # Thêm vào danh sách orders
        self.execution_details['orders'].extend(self.orders)
        
        # Cập nhật trạng thái
        for order in self.orders:
            order_id = order.get('orderId')
            if order_id:
                self.order_status[order_id] = order.get('status', 'NEW')
                
        # Tính toán số lượng đã khớp và giá trung bình
        filled_qty = sum([float(order.get('executedQty', 0)) for order in self.orders])
        
        # Tính giá trung bình nếu có lệnh đã khớp
        if filled_qty > 0:
            total_value = sum([float(order.get('executedQty', 0)) * float(order.get('price', 0)) for order in self.orders])
            avg_price = total_value / filled_qty
        else:
            avg_price = 0
            
        # Cập nhật chi tiết
        self.execution_details['filled_quantity'] = filled_qty
        self.execution_details['avg_price'] = avg_price
        self.execution_details['total_cost'] = avg_price * filled_qty
        
        # Cập nhật trạng thái thực thi
        if filled_qty >= self.quantity:
            self.execution_details['status'] = 'completed'
        elif filled_qty > 0:
            self.execution_details['status'] = 'partially_filled'
        else:
            self.execution_details['status'] = 'pending'

class OrderExecutionFactory:
    """Factory tạo các đối tượng OrderExecutor"""
    
    @staticmethod
    def create_executor(execution_type: str, binance_api=None, **kwargs) -> BaseOrderExecutor:
        """
        Tạo đối tượng OrderExecutor
        
        Args:
            execution_type (str): Loại executor
            binance_api: Đối tượng BinanceAPI
            **kwargs: Tham số cho executor
            
        Returns:
            BaseOrderExecutor: Đối tượng OrderExecutor
        """
        if execution_type.lower() == 'market':
            return MarketOrderExecutor(binance_api, **kwargs)
            
        elif execution_type.lower() == 'limit':
            return LimitOrderExecutor(binance_api, **kwargs)
            
        elif execution_type.lower() == 'iceberg':
            return IcebergOrderExecutor(binance_api, **kwargs)
            
        elif execution_type.lower() == 'twap':
            return TWAPExecutor(binance_api, **kwargs)
            
        elif execution_type.lower() == 'scaled':
            return ScaledOrderExecutor(binance_api, **kwargs)
            
        elif execution_type.lower() == 'oco':
            return OCOOrderExecutor(binance_api, **kwargs)
            
        else:
            # Mặc định sử dụng lệnh thị trường
            logger.warning(f"Không hỗ trợ loại executor: {execution_type}, sử dụng MarketOrderExecutor")
            return MarketOrderExecutor(binance_api, **kwargs)
    
    @staticmethod
    def get_available_executors() -> Dict[str, str]:
        """
        Lấy danh sách các loại executor có sẵn
        
        Returns:
            Dict[str, str]: Ánh xạ loại executor -> mô tả
        """
        return {
            'market': 'Market Order - Khớp ngay lập tức theo giá thị trường',
            'limit': 'Limit Order - Đặt lệnh ở mức giá cụ thể',
            'iceberg': 'Iceberg Order - Chia nhỏ lệnh lớn thành nhiều lệnh nhỏ hơn',
            'twap': 'Time-Weighted Average Price - Thực thi theo thời gian',
            'scaled': 'Scaled Order - Đặt nhiều lệnh ở các mức giá khác nhau',
            'oco': 'One-Cancels-the-Other - Đặt lệnh limit và stop cùng lúc'
        }
    
    @staticmethod
    def recommend_executor(symbol: str, side: str, quantity: float, market_data: Dict = None) -> str:
        """
        Đề xuất loại executor phù hợp dựa trên điều kiện thị trường
        
        Args:
            symbol (str): Symbol giao dịch
            side (str): Hướng giao dịch ('BUY' hoặc 'SELL')
            quantity (float): Số lượng
            market_data (Dict, optional): Dữ liệu thị trường
            
        Returns:
            str: Loại executor được đề xuất
        """
        # Phân tích dữ liệu thị trường
        volume = market_data.get('volume', 0) if market_data else 0
        volatility = market_data.get('volatility', 0) if market_data else 0
        spread = market_data.get('spread', 0) if market_data else 0
        
        # Logic đề xuất
        if volume > 0 and quantity / volume > 0.1:
            # Lệnh lớn so với khối lượng thị trường
            if volatility > 0.05:  # Biến động cao
                return 'twap'  # Chia theo thời gian
            else:
                return 'iceberg'  # Chia thành nhiều lệnh
                
        elif volatility > 0.03:  # Biến động trung bình
            if spread > 0.01:  # Spread lớn
                return 'scaled'  # Đặt nhiều mức giá
            else:
                return 'limit'  # Lệnh giới hạn đơn giản
                
        else:  # Biến động thấp, thị trường bình thường
            return 'market'  # Lệnh thị trường đơn giản

def main():
    """Hàm chính để demo"""
    logging.basicConfig(level=logging.INFO)
    
    # Khởi tạo đối tượng OrderExecutor
    executor = OrderExecutionFactory.create_executor(
        execution_type='market',
        symbol='BTCUSDT',
        side='BUY',
        quantity=0.001,
        price=30000
    )
    
    # Xem danh sách các loại executor có sẵn
    executors = OrderExecutionFactory.get_available_executors()
    print("Các loại executor có sẵn:")
    for key, value in executors.items():
        print(f"- {key}: {value}")
    
if __name__ == "__main__":
    main()