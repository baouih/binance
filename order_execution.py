"""
Module phương thức đi lệnh nâng cao (Advanced Order Execution)

Module này cung cấp các phương thức đi lệnh nâng cao để tối ưu hóa việc vào lệnh/ra lệnh:
- Iceberg Orders: Chia nhỏ lệnh lớn để giảm ảnh hưởng thị trường
- TWAP/VWAP: Thực thi lệnh theo thời gian/khối lượng trung bình có trọng số
- Scaled Orders: Vào/ra lệnh theo nhiều mức giá để tối ưu giá trung bình
- OCO Orders: Kết hợp TP/SL trong một lệnh

Các chiến lược này giúp giảm slippage và cải thiện giá trung bình vào lệnh/ra lệnh.
"""

import logging
import time
import threading
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Callable
import datetime as dt

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("order_execution")

class BaseOrderExecutor:
    """Lớp cơ sở cho tất cả các chiến lược thực thi lệnh"""
    
    def __init__(self, api_client, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Khởi tạo order executor.
        
        Args:
            api_client: Đối tượng API client (Binance)
            max_retries (int): Số lần thử lại tối đa khi gặp lỗi
            retry_delay (float): Thời gian chờ giữa các lần thử lại (giây)
        """
        self.api_client = api_client
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def execute_order(self, symbol: str, side: str, quantity: float, 
                    order_type: str = 'MARKET', price: float = None, 
                    time_in_force: str = 'GTC', **kwargs) -> Dict:
        """
        Thực thi lệnh với cơ chế thử lại.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            quantity (float): Số lượng
            order_type (str): Loại lệnh ('MARKET', 'LIMIT', 'STOP_LOSS', etc.)
            price (float, optional): Giá đặt lệnh (bắt buộc cho lệnh limit)
            time_in_force (str): Thời gian hiệu lực của lệnh ('GTC', 'IOC', 'FOK')
            **kwargs: Các tham số bổ sung
            
        Returns:
            Dict: Thông tin về lệnh đã thực thi
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                # Thực thi lệnh
                if order_type == 'MARKET':
                    response = self.api_client.create_order(
                        symbol=symbol,
                        side=side,
                        type=order_type,
                        quantity=quantity,
                        **kwargs
                    )
                elif order_type == 'LIMIT':
                    if price is None:
                        raise ValueError("Price must be specified for LIMIT orders")
                    response = self.api_client.create_order(
                        symbol=symbol,
                        side=side,
                        type=order_type,
                        quantity=quantity,
                        price=price,
                        timeInForce=time_in_force,
                        **kwargs
                    )
                else:
                    # Xử lý các loại lệnh khác
                    response = self.api_client.create_order(
                        symbol=symbol,
                        side=side,
                        type=order_type,
                        quantity=quantity,
                        price=price if price else None,
                        timeInForce=time_in_force if price else None,
                        **kwargs
                    )
                
                logger.info(f"Order executed: {symbol} {side} {quantity} @ {price if price else 'MARKET'}")
                return response
                
            except Exception as e:
                logger.warning(f"Error executing order (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to execute order after {self.max_retries} attempts: {e}")
                    raise
    
    def cancel_order(self, symbol: str, order_id: str = None, 
                   client_order_id: str = None) -> Dict:
        """
        Hủy lệnh.
        
        Args:
            symbol (str): Mã cặp giao dịch
            order_id (str, optional): ID lệnh
            client_order_id (str, optional): Client order ID
            
        Returns:
            Dict: Thông tin về lệnh đã hủy
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                params = {'symbol': symbol}
                if order_id:
                    params['orderId'] = order_id
                if client_order_id:
                    params['origClientOrderId'] = client_order_id
                    
                response = self.api_client.cancel_order(**params)
                logger.info(f"Order cancelled: {symbol} {order_id or client_order_id}")
                return response
                
            except Exception as e:
                logger.warning(f"Error cancelling order (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to cancel order after {self.max_retries} attempts: {e}")
                    raise
    
    def get_order_status(self, symbol: str, order_id: str = None, 
                       client_order_id: str = None) -> Dict:
        """
        Lấy trạng thái của lệnh.
        
        Args:
            symbol (str): Mã cặp giao dịch
            order_id (str, optional): ID lệnh
            client_order_id (str, optional): Client order ID
            
        Returns:
            Dict: Thông tin về trạng thái lệnh
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                params = {'symbol': symbol}
                if order_id:
                    params['orderId'] = order_id
                if client_order_id:
                    params['origClientOrderId'] = client_order_id
                    
                response = self.api_client.get_order(**params)
                return response
                
            except Exception as e:
                logger.warning(f"Error getting order status (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to get order status after {self.max_retries} attempts: {e}")
                    raise


class IcebergOrderExecutor(BaseOrderExecutor):
    """Chiến lược thực thi lệnh Iceberg chia nhỏ lệnh lớn thành nhiều phần"""
    
    def __init__(self, api_client, max_retries: int = 3, retry_delay: float = 1.0,
                random_variation: bool = True, variation_pct: float = 0.05):
        """
        Khởi tạo Iceberg Order Executor.
        
        Args:
            api_client: Đối tượng API client (Binance)
            max_retries (int): Số lần thử lại tối đa khi gặp lỗi
            retry_delay (float): Thời gian chờ giữa các lần thử lại (giây)
            random_variation (bool): Sử dụng biến đổi ngẫu nhiên cho kích thước các phần
            variation_pct (float): Phần trăm biến đổi tối đa
        """
        super().__init__(api_client, max_retries, retry_delay)
        self.random_variation = random_variation
        self.variation_pct = variation_pct
        
    def execute_iceberg_order(self, symbol: str, side: str, total_quantity: float,
                            num_parts: int = 5, price: float = None,
                            time_between_parts: float = 2.0,
                            order_type: str = 'MARKET') -> List[Dict]:
        """
        Thực thi lệnh Iceberg bằng cách chia nhỏ thành nhiều phần.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            total_quantity (float): Tổng số lượng
            num_parts (int): Số phần muốn chia
            price (float, optional): Giá đặt lệnh (cho lệnh limit)
            time_between_parts (float): Thời gian chờ giữa các phần (giây)
            order_type (str): Loại lệnh ('MARKET' hoặc 'LIMIT')
            
        Returns:
            List[Dict]: Danh sách các lệnh đã thực thi
        """
        if num_parts <= 0:
            raise ValueError("num_parts must be a positive integer")
            
        # Tính lượng cho mỗi phần
        base_quantity_per_part = total_quantity / num_parts
        
        # Kiểm tra các ràng buộc về số lượng (lot sizes)
        # Tùy thuộc vào yêu cầu của sàn, có thể cần làm tròn số lượng
        
        orders = []
        remaining_quantity = total_quantity
        
        for i in range(num_parts):
            # Tính số lượng cho phần này
            if i == num_parts - 1:
                # Phần cuối cùng lấy toàn bộ số còn lại để đảm bảo tổng đúng
                part_quantity = remaining_quantity
            else:
                # Thêm biến đổi ngẫu nhiên nếu được bật
                if self.random_variation:
                    # Biến đổi trong khoảng ±variation_pct
                    variation = np.random.uniform(-self.variation_pct, self.variation_pct)
                    part_quantity = base_quantity_per_part * (1 + variation)
                    
                    # Đảm bảo không vượt quá số lượng còn lại
                    part_quantity = min(part_quantity, remaining_quantity)
                else:
                    part_quantity = base_quantity_per_part
            
            # Làm tròn số lượng phù hợp với yêu cầu của sàn
            # Tùy thuộc vào symbol, có thể cần cập nhật cách làm tròn
            part_quantity = round(part_quantity, 6)  # Đủ cho hầu hết các coin
            
            logger.info(f"Iceberg part {i+1}/{num_parts}: {symbol} {side} {part_quantity} " +
                       f"({part_quantity/total_quantity*100:.1f}% of total)")
            
            # Thực thi lệnh cho phần này
            order = self.execute_order(
                symbol=symbol,
                side=side,
                quantity=part_quantity,
                order_type=order_type,
                price=price if order_type == 'LIMIT' else None
            )
            
            orders.append(order)
            remaining_quantity -= part_quantity
            
            # Chờ giữa các phần (trừ phần cuối cùng)
            if i < num_parts - 1:
                # Thêm biến đổi ngẫu nhiên cho thời gian nếu cần
                if self.random_variation:
                    wait_time = time_between_parts * np.random.uniform(0.8, 1.2)
                else:
                    wait_time = time_between_parts
                    
                time.sleep(wait_time)
                
        logger.info(f"Completed Iceberg order execution: {symbol} {side} {total_quantity}")
        return orders


class TWAPExecutor(BaseOrderExecutor):
    """Chiến lược thực thi lệnh TWAP (Time-Weighted Average Price)"""
    
    def __init__(self, api_client, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Khởi tạo TWAP Executor.
        
        Args:
            api_client: Đối tượng API client (Binance)
            max_retries (int): Số lần thử lại tối đa khi gặp lỗi
            retry_delay (float): Thời gian chờ giữa các lần thử lại (giây)
        """
        super().__init__(api_client, max_retries, retry_delay)
        self.active_executions = {}  # Theo dõi các lệnh TWAP đang chạy
        
    def execute_twap_order(self, symbol: str, side: str, total_quantity: float,
                         duration_minutes: float = 30.0, num_parts: int = 10,
                         order_type: str = 'MARKET', price: float = None, 
                         cancel_on_error: bool = True) -> str:
        """
        Khởi chạy lệnh TWAP trong thread riêng biệt.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            total_quantity (float): Tổng số lượng
            duration_minutes (float): Tổng thời gian thực thi (phút)
            num_parts (int): Số phần muốn chia
            order_type (str): Loại lệnh ('MARKET' hoặc 'LIMIT')
            price (float, optional): Giá đặt lệnh (cho lệnh limit)
            cancel_on_error (bool): Hủy các lệnh còn lại nếu có lỗi
            
        Returns:
            str: ID thực thi TWAP
        """
        # Tạo execution ID
        execution_id = f"TWAP_{symbol}_{side}_{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Lưu thông tin thực thi
        self.active_executions[execution_id] = {
            'status': 'starting',
            'symbol': symbol,
            'side': side,
            'total_quantity': total_quantity,
            'executed_quantity': 0,
            'remaining_quantity': total_quantity,
            'orders': [],
            'start_time': dt.datetime.now(),
            'end_time': dt.datetime.now() + dt.timedelta(minutes=duration_minutes),
            'errors': [],
            'is_cancelled': False
        }
        
        # Khởi chạy thread thực thi
        thread = threading.Thread(
            target=self._execute_twap_thread,
            args=(
                execution_id,
                symbol,
                side,
                total_quantity,
                duration_minutes,
                num_parts,
                order_type,
                price,
                cancel_on_error
            )
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started TWAP execution {execution_id}: {symbol} {side} {total_quantity} " +
                   f"over {duration_minutes} minutes in {num_parts} parts")
        
        return execution_id
        
    def _execute_twap_thread(self, execution_id: str, symbol: str, side: str, 
                          total_quantity: float, duration_minutes: float, 
                          num_parts: int, order_type: str, price: float,
                          cancel_on_error: bool) -> None:
        """
        Thread thực thi TWAP.
        
        Args:
            execution_id (str): ID thực thi
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            total_quantity (float): Tổng số lượng
            duration_minutes (float): Tổng thời gian thực thi (phút)
            num_parts (int): Số phần muốn chia
            order_type (str): Loại lệnh
            price (float): Giá đặt lệnh
            cancel_on_error (bool): Hủy các lệnh còn lại nếu có lỗi
        """
        try:
            # Cập nhật trạng thái
            self.active_executions[execution_id]['status'] = 'running'
            
            # Tính thời gian giữa các phần
            interval_seconds = (duration_minutes * 60) / num_parts
            
            # Tính số lượng cho mỗi phần
            quantity_per_part = total_quantity / num_parts
            
            # Biến theo dõi
            executed_quantity = 0
            remaining_quantity = total_quantity
            
            # Thực thi từng phần
            for i in range(num_parts):
                # Kiểm tra nếu lệnh đã bị hủy
                if self.active_executions[execution_id]['is_cancelled']:
                    logger.info(f"TWAP execution {execution_id} was cancelled")
                    break
                    
                start_time = time.time()
                
                # Tính số lượng cho phần này
                if i == num_parts - 1:
                    # Phần cuối cùng lấy toàn bộ số còn lại
                    part_quantity = remaining_quantity
                else:
                    part_quantity = quantity_per_part
                
                # Làm tròn số lượng phù hợp với yêu cầu của sàn
                part_quantity = round(part_quantity, 6)
                
                # Thực thi lệnh cho phần này
                try:
                    order = self.execute_order(
                        symbol=symbol,
                        side=side,
                        quantity=part_quantity,
                        order_type=order_type,
                        price=price if order_type == 'LIMIT' else None
                    )
                    
                    # Cập nhật thông tin
                    executed_quantity += float(order.get('executedQty', 0))
                    remaining_quantity -= float(order.get('executedQty', 0))
                    
                    # Lưu lệnh
                    self.active_executions[execution_id]['orders'].append(order)
                    self.active_executions[execution_id]['executed_quantity'] = executed_quantity
                    self.active_executions[execution_id]['remaining_quantity'] = remaining_quantity
                    
                    logger.info(f"TWAP part {i+1}/{num_parts}: {symbol} {side} {part_quantity} executed")
                
                except Exception as e:
                    error_msg = f"Error executing TWAP part {i+1}/{num_parts}: {e}"
                    logger.error(error_msg)
                    self.active_executions[execution_id]['errors'].append(error_msg)
                    
                    if cancel_on_error:
                        self.active_executions[execution_id]['is_cancelled'] = True
                        break
                
                # Tính thời gian chờ cho phần tiếp theo (nếu không phải phần cuối)
                if i < num_parts - 1:
                    elapsed = time.time() - start_time
                    wait_time = max(0, interval_seconds - elapsed)
                    time.sleep(wait_time)
            
            # Cập nhật trạng thái kết thúc
            if self.active_executions[execution_id]['is_cancelled']:
                self.active_executions[execution_id]['status'] = 'cancelled'
            else:
                self.active_executions[execution_id]['status'] = 'completed'
                
            logger.info(f"TWAP execution {execution_id} {self.active_executions[execution_id]['status']}: " +
                       f"{executed_quantity}/{total_quantity} executed")
        
        except Exception as e:
            error_msg = f"Unexpected error in TWAP execution {execution_id}: {e}"
            logger.error(error_msg)
            self.active_executions[execution_id]['errors'].append(error_msg)
            self.active_executions[execution_id]['status'] = 'failed'
    
    def cancel_twap_execution(self, execution_id: str) -> bool:
        """
        Hủy thực thi TWAP đang chạy.
        
        Args:
            execution_id (str): ID thực thi TWAP
            
        Returns:
            bool: True nếu hủy thành công, False nếu không
        """
        if execution_id not in self.active_executions:
            logger.warning(f"TWAP execution {execution_id} not found")
            return False
            
        if self.active_executions[execution_id]['status'] in ['completed', 'failed', 'cancelled']:
            logger.warning(f"TWAP execution {execution_id} already {self.active_executions[execution_id]['status']}")
            return False
            
        # Đánh dấu là đã hủy
        self.active_executions[execution_id]['is_cancelled'] = True
        self.active_executions[execution_id]['status'] = 'cancelling'
        
        logger.info(f"Cancelling TWAP execution {execution_id}")
        return True
    
    def get_twap_status(self, execution_id: str) -> Dict:
        """
        Lấy trạng thái của thực thi TWAP.
        
        Args:
            execution_id (str): ID thực thi TWAP
            
        Returns:
            Dict: Thông tin về trạng thái thực thi
        """
        if execution_id not in self.active_executions:
            logger.warning(f"TWAP execution {execution_id} not found")
            return {'status': 'not_found', 'execution_id': execution_id}
            
        # Tính toán thông tin thêm
        execution = self.active_executions[execution_id].copy()
        
        # Tính thời gian đã trôi qua
        elapsed_time = (dt.datetime.now() - execution['start_time']).total_seconds() / 60
        total_time = (execution['end_time'] - execution['start_time']).total_seconds() / 60
        
        # Tính tiến độ
        if total_time > 0:
            time_progress = min(100, elapsed_time / total_time * 100)
        else:
            time_progress = 100
            
        # Tính tiến độ thực thi
        if execution['total_quantity'] > 0:
            execution_progress = execution['executed_quantity'] / execution['total_quantity'] * 100
        else:
            execution_progress = 0
            
        # Thêm thông tin vào kết quả
        execution['time_progress'] = time_progress
        execution['execution_progress'] = execution_progress
        execution['elapsed_minutes'] = elapsed_time
        execution['total_minutes'] = total_time
        
        return execution


class ScaledOrderExecutor(BaseOrderExecutor):
    """Chiến lược thực thi lệnh theo nhiều mức giá"""
    
    def __init__(self, api_client, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Khởi tạo Scaled Order Executor.
        
        Args:
            api_client: Đối tượng API client (Binance)
            max_retries (int): Số lần thử lại tối đa khi gặp lỗi
            retry_delay (float): Thời gian chờ giữa các lần thử lại (giây)
        """
        super().__init__(api_client, max_retries, retry_delay)
        
    def execute_scaled_entry(self, symbol: str, side: str, total_quantity: float,
                          price_low: float, price_high: float, num_levels: int = 5,
                          distribution: str = 'linear') -> List[Dict]:
        """
        Thực thi lệnh vào theo nhiều mức giá.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            total_quantity (float): Tổng số lượng
            price_low (float): Mức giá thấp nhất
            price_high (float): Mức giá cao nhất
            num_levels (int): Số mức giá
            distribution (str): Phân phối số lượng ('linear', 'geometric', 'equal')
            
        Returns:
            List[Dict]: Danh sách các lệnh đã đặt
        """
        if num_levels <= 0:
            raise ValueError("num_levels must be a positive integer")
            
        if price_low >= price_high:
            raise ValueError("price_low must be less than price_high")
            
        # Tính các mức giá
        if num_levels == 1:
            prices = [price_low]
        else:
            prices = np.linspace(price_low, price_high, num_levels)
            
        # Tính phân phối số lượng
        if distribution == 'equal':
            # Phân phối đều
            quantities = [total_quantity / num_levels] * num_levels
        elif distribution == 'geometric':
            # Phân phối theo cấp số nhân (tỷ trọng giảm dần hoặc tăng dần)
            if side == 'BUY':
                # Đối với lệnh mua, tỷ trọng lớn hơn ở giá thấp
                weights = np.geomspace(2, 1, num_levels)
            else:
                # Đối với lệnh bán, tỷ trọng lớn hơn ở giá cao
                weights = np.geomspace(1, 2, num_levels)
                
            # Chuẩn hóa
            weights = weights / np.sum(weights)
            quantities = [total_quantity * w for w in weights]
        else:
            # Phân phối tuyến tính (mặc định)
            if side == 'BUY':
                # Đối với lệnh mua, tỷ trọng lớn hơn ở giá thấp
                weights = np.linspace(1.5, 0.5, num_levels)
            else:
                # Đối với lệnh bán, tỷ trọng lớn hơn ở giá cao
                weights = np.linspace(0.5, 1.5, num_levels)
                
            # Chuẩn hóa
            weights = weights / np.sum(weights)
            quantities = [total_quantity * w for w in weights]
            
        # Đặt lệnh
        orders = []
        
        for i, (price, quantity) in enumerate(zip(prices, quantities)):
            # Làm tròn số lượng và giá
            rounded_quantity = round(quantity, 6)
            rounded_price = round(price, 8)
            
            logger.info(f"Scaled order {i+1}/{num_levels}: {symbol} {side} {rounded_quantity} @ {rounded_price}")
            
            try:
                order = self.execute_order(
                    symbol=symbol,
                    side=side,
                    quantity=rounded_quantity,
                    order_type='LIMIT',
                    price=rounded_price,
                    time_in_force='GTC'
                )
                
                orders.append(order)
                
            except Exception as e:
                logger.error(f"Error placing scaled order at level {i+1}: {e}")
                # Tiếp tục với các lệnh còn lại
                
        logger.info(f"Placed {len(orders)}/{num_levels} scaled orders for {symbol} {side} {total_quantity}")
        return orders
    
    def execute_scaled_exit(self, symbol: str, side: str, total_quantity: float,
                          price_low: float, price_high: float, num_levels: int = 5,
                          distribution: str = 'linear') -> List[Dict]:
        """
        Thực thi lệnh ra theo nhiều mức giá.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            total_quantity (float): Tổng số lượng
            price_low (float): Mức giá thấp nhất
            price_high (float): Mức giá cao nhất
            num_levels (int): Số mức giá
            distribution (str): Phân phối số lượng ('linear', 'geometric', 'equal')
            
        Returns:
            List[Dict]: Danh sách các lệnh đã đặt
        """
        # Đối với lệnh thoát, chúng ta đảo ngược phân phối
        reverse_side = 'SELL' if side == 'BUY' else 'BUY'
        
        return self.execute_scaled_entry(
            symbol=symbol,
            side=reverse_side,
            total_quantity=total_quantity,
            price_low=price_low,
            price_high=price_high,
            num_levels=num_levels,
            distribution=distribution
        )
    
    def cancel_all_scaled_orders(self, symbol: str) -> List[Dict]:
        """
        Hủy tất cả các lệnh đang mở của một cặp tiền.
        
        Args:
            symbol (str): Mã cặp giao dịch
            
        Returns:
            List[Dict]: Danh sách các lệnh đã hủy
        """
        try:
            # Lấy tất cả các lệnh đang mở
            open_orders = self.api_client.get_open_orders(symbol=symbol)
            cancelled_orders = []
            
            for order in open_orders:
                try:
                    cancelled = self.cancel_order(
                        symbol=symbol,
                        order_id=order['orderId']
                    )
                    
                    cancelled_orders.append(cancelled)
                    
                except Exception as e:
                    logger.error(f"Error cancelling order {order['orderId']}: {e}")
                    
            logger.info(f"Cancelled {len(cancelled_orders)}/{len(open_orders)} open orders for {symbol}")
            return cancelled_orders
            
        except Exception as e:
            logger.error(f"Error getting open orders for {symbol}: {e}")
            return []
    
    def calculate_average_fill_price(self, orders: List[Dict]) -> float:
        """
        Tính giá trung bình của các lệnh đã được thực hiện.
        
        Args:
            orders (List[Dict]): Danh sách các lệnh
            
        Returns:
            float: Giá trung bình
        """
        total_value = 0
        total_quantity = 0
        
        for order in orders:
            # Chỉ tính các lệnh đã được thực hiện hoàn toàn hoặc một phần
            executed_qty = float(order.get('executedQty', 0))
            if executed_qty > 0:
                # Lấy giá trung bình từ fills nếu có
                if 'fills' in order and order['fills']:
                    order_value = sum(float(fill['price']) * float(fill['qty']) for fill in order['fills'])
                else:
                    # Nếu không có fills, sử dụng giá lệnh
                    order_value = executed_qty * float(order.get('price', 0))
                    
                total_value += order_value
                total_quantity += executed_qty
        
        if total_quantity > 0:
            return total_value / total_quantity
        else:
            return 0


class OCOOrderExecutor(BaseOrderExecutor):
    """Chiến lược thực thi lệnh OCO (One-Cancels-Other)"""
    
    def __init__(self, api_client, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Khởi tạo OCO Order Executor.
        
        Args:
            api_client: Đối tượng API client (Binance)
            max_retries (int): Số lần thử lại tối đa khi gặp lỗi
            retry_delay (float): Thời gian chờ giữa các lần thử lại (giây)
        """
        super().__init__(api_client, max_retries, retry_delay)
        
    def place_oco_order(self, symbol: str, side: str, quantity: float, 
                      price: float, stop_price: float, stop_limit_price: float = None,
                      stop_limit_time_in_force: str = 'GTC') -> Dict:
        """
        Đặt lệnh OCO (One-Cancels-Other).
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            quantity (float): Số lượng
            price (float): Giá limit (take profit)
            stop_price (float): Giá stop loss (kích hoạt)
            stop_limit_price (float, optional): Giá stop limit, mặc định = stop_price
            stop_limit_time_in_force (str): Thời gian hiệu lực của lệnh stop limit
            
        Returns:
            Dict: Thông tin về lệnh OCO
        """
        if stop_limit_price is None:
            stop_limit_price = stop_price
            
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.api_client.order_oco_sell(
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    stopPrice=stop_price,
                    stopLimitPrice=stop_limit_price,
                    stopLimitTimeInForce=stop_limit_time_in_force
                ) if side.upper() == 'SELL' else self.api_client.order_oco_buy(
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    stopPrice=stop_price,
                    stopLimitPrice=stop_limit_price,
                    stopLimitTimeInForce=stop_limit_time_in_force
                )
                
                logger.info(f"Placed OCO order: {symbol} {side} {quantity} " +
                           f"TP:{price} SL:{stop_price}")
                return response
                
            except Exception as e:
                logger.warning(f"Error placing OCO order (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to place OCO order after {self.max_retries} attempts: {e}")
                    raise
    
    def cancel_oco_order(self, symbol: str, order_list_id: str) -> Dict:
        """
        Hủy lệnh OCO.
        
        Args:
            symbol (str): Mã cặp giao dịch
            order_list_id (str): ID của danh sách lệnh OCO
            
        Returns:
            Dict: Thông tin về lệnh OCO đã hủy
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.api_client.cancel_order_list(
                    symbol=symbol,
                    orderListId=order_list_id
                )
                
                logger.info(f"Cancelled OCO order: {symbol} {order_list_id}")
                return response
                
            except Exception as e:
                logger.warning(f"Error cancelling OCO order (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to cancel OCO order after {self.max_retries} attempts: {e}")
                    raise
    
    def get_oco_order_status(self, order_list_id: str) -> Dict:
        """
        Lấy trạng thái của lệnh OCO.
        
        Args:
            order_list_id (str): ID của danh sách lệnh OCO
            
        Returns:
            Dict: Thông tin về trạng thái lệnh OCO
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.api_client.get_order_list(
                    orderListId=order_list_id
                )
                
                return response
                
            except Exception as e:
                logger.warning(f"Error getting OCO order status (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to get OCO order status after {self.max_retries} attempts: {e}")
                    raise
    
    def place_tp_sl_orders(self, symbol: str, side: str, entry_price: float, 
                         quantity: float, take_profit_price: float, stop_loss_price: float,
                         use_oco: bool = True) -> Dict:
        """
        Đặt lệnh take profit và stop loss (có thể là OCO hoặc riêng biệt).
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            entry_price (float): Giá vào lệnh
            quantity (float): Số lượng
            take_profit_price (float): Giá chốt lời
            stop_loss_price (float): Giá cắt lỗ
            use_oco (bool): Sử dụng lệnh OCO hay đặt riêng biệt
            
        Returns:
            Dict: Thông tin về lệnh
        """
        # Xác định hướng lệnh đóng vị thế
        close_side = 'SELL' if side.upper() == 'LONG' else 'BUY'
        
        # Kiểm tra các giá trị
        if side.upper() == 'LONG':
            if not (take_profit_price > entry_price > stop_loss_price):
                raise ValueError(f"For LONG positions, TP ({take_profit_price}) > Entry ({entry_price}) > SL ({stop_loss_price}) must be true")
        else:  # SHORT
            if not (take_profit_price < entry_price < stop_loss_price):
                raise ValueError(f"For SHORT positions, TP ({take_profit_price}) < Entry ({entry_price}) < SL ({stop_loss_price}) must be true")
        
        if use_oco:
            # Đặt lệnh OCO
            return self.place_oco_order(
                symbol=symbol,
                side=close_side,
                quantity=quantity,
                price=take_profit_price,
                stop_price=stop_loss_price
            )
        else:
            # Đặt các lệnh riêng biệt
            orders = {}
            
            # Đặt lệnh take profit
            try:
                tp_order = self.execute_order(
                    symbol=symbol,
                    side=close_side,
                    quantity=quantity,
                    order_type='LIMIT',
                    price=take_profit_price,
                    time_in_force='GTC'
                )
                orders['take_profit'] = tp_order
                
            except Exception as e:
                logger.error(f"Error placing take profit order: {e}")
                orders['take_profit_error'] = str(e)
            
            # Đặt lệnh stop loss
            try:
                sl_order = self.execute_order(
                    symbol=symbol,
                    side=close_side,
                    quantity=quantity,
                    order_type='STOP_LOSS_LIMIT',
                    price=stop_loss_price,
                    stop_price=stop_loss_price,
                    time_in_force='GTC'
                )
                orders['stop_loss'] = sl_order
                
            except Exception as e:
                logger.error(f"Error placing stop loss order: {e}")
                orders['stop_loss_error'] = str(e)
                
                # Nếu TP đã đặt thành công nhưng SL thất bại, hủy TP
                if 'take_profit' in orders and 'stop_loss' not in orders:
                    try:
                        self.cancel_order(
                            symbol=symbol,
                            order_id=orders['take_profit']['orderId']
                        )
                        orders['take_profit_cancelled'] = True
                        
                    except Exception as cancel_error:
                        logger.error(f"Error cancelling take profit order: {cancel_error}")
                        orders['take_profit_cancel_error'] = str(cancel_error)
            
            return orders


class OrderExecutionFactory:
    """Factory để tạo các đối tượng executor phù hợp"""
    
    @staticmethod
    def create_executor(executor_type: str, api_client, **kwargs) -> BaseOrderExecutor:
        """
        Tạo order executor theo loại.
        
        Args:
            executor_type (str): Loại executor ('base', 'iceberg', 'twap', 'scaled', 'oco')
            api_client: Đối tượng API client (Binance)
            **kwargs: Các tham số bổ sung
            
        Returns:
            BaseOrderExecutor: Đối tượng order executor
        """
        if executor_type.lower() == 'iceberg':
            return IcebergOrderExecutor(api_client, **kwargs)
        elif executor_type.lower() == 'twap':
            return TWAPExecutor(api_client, **kwargs)
        elif executor_type.lower() == 'scaled':
            return ScaledOrderExecutor(api_client, **kwargs)
        elif executor_type.lower() == 'oco':
            return OCOOrderExecutor(api_client, **kwargs)
        else:  # 'base' hoặc mặc định
            return BaseOrderExecutor(api_client, **kwargs)


def main():
    """Hàm chính để test module"""
    # Đây chỉ là ví dụ, thực tế cần kết nối với API client thực tế
    
    # Giả lập API client đơn giản
    class MockAPIClient:
        def create_order(self, **kwargs):
            print(f"MOCK: Creating order with params: {kwargs}")
            return {
                'orderId': '12345',
                'symbol': kwargs.get('symbol'),
                'side': kwargs.get('side'),
                'type': kwargs.get('type'),
                'price': kwargs.get('price'),
                'origQty': kwargs.get('quantity'),
                'executedQty': kwargs.get('quantity'),
                'status': 'FILLED',
                'timeInForce': kwargs.get('timeInForce', 'GTC'),
                'fills': [
                    {'price': kwargs.get('price'), 'qty': kwargs.get('quantity')}
                ]
            }
            
        def cancel_order(self, **kwargs):
            print(f"MOCK: Cancelling order with params: {kwargs}")
            return {'orderId': kwargs.get('orderId'), 'status': 'CANCELED'}
            
        def get_order(self, **kwargs):
            print(f"MOCK: Getting order with params: {kwargs}")
            return {'orderId': kwargs.get('orderId'), 'status': 'FILLED'}
            
        def get_open_orders(self, **kwargs):
            print(f"MOCK: Getting open orders with params: {kwargs}")
            return [
                {'orderId': '12345', 'symbol': kwargs.get('symbol'), 'price': '40000', 'origQty': '0.1', 'executedQty': '0.05'},
                {'orderId': '12346', 'symbol': kwargs.get('symbol'), 'price': '41000', 'origQty': '0.1', 'executedQty': '0'}
            ]
            
        def order_oco_sell(self, **kwargs):
            print(f"MOCK: Creating OCO SELL order with params: {kwargs}")
            return {
                'orderListId': '12347',
                'orders': [
                    {'orderId': '12348', 'type': 'LIMIT', 'price': kwargs.get('price')},
                    {'orderId': '12349', 'type': 'STOP_LOSS_LIMIT', 'price': kwargs.get('stopLimitPrice')}
                ]
            }
            
        def order_oco_buy(self, **kwargs):
            print(f"MOCK: Creating OCO BUY order with params: {kwargs}")
            return {
                'orderListId': '12350',
                'orders': [
                    {'orderId': '12351', 'type': 'LIMIT', 'price': kwargs.get('price')},
                    {'orderId': '12352', 'type': 'STOP_LOSS_LIMIT', 'price': kwargs.get('stopLimitPrice')}
                ]
            }
            
        def cancel_order_list(self, **kwargs):
            print(f"MOCK: Cancelling OCO order with params: {kwargs}")
            return {'orderListId': kwargs.get('orderListId'), 'status': 'CANCELED'}
            
        def get_order_list(self, **kwargs):
            print(f"MOCK: Getting OCO order with params: {kwargs}")
            return {'orderListId': kwargs.get('orderListId'), 'status': 'ACTIVE'}
    
    # Tạo mock API client
    mock_client = MockAPIClient()
    
    # Test các executor
    print("\n=== Testing Iceberg Order Executor ===")
    iceberg_executor = IcebergOrderExecutor(mock_client)
    iceberg_executor.execute_iceberg_order(
        symbol="BTCUSDT",
        side="BUY",
        total_quantity=0.5,
        num_parts=3,
        price=40000,
        time_between_parts=0.1  # ngắn cho mục đích test
    )
    
    print("\n=== Testing TWAP Executor ===")
    twap_executor = TWAPExecutor(mock_client)
    execution_id = twap_executor.execute_twap_order(
        symbol="BTCUSDT",
        side="BUY",
        total_quantity=0.5,
        duration_minutes=0.1,  # ngắn cho mục đích test
        num_parts=2
    )
    # Đợi một chút cho TWAP chạy
    time.sleep(0.2)
    print(f"TWAP status: {twap_executor.get_twap_status(execution_id)}")
    
    print("\n=== Testing Scaled Order Executor ===")
    scaled_executor = ScaledOrderExecutor(mock_client)
    scaled_orders = scaled_executor.execute_scaled_entry(
        symbol="BTCUSDT",
        side="BUY",
        total_quantity=0.5,
        price_low=39000,
        price_high=40000,
        num_levels=3
    )
    print(f"Average fill price: {scaled_executor.calculate_average_fill_price(scaled_orders)}")
    
    print("\n=== Testing OCO Order Executor ===")
    oco_executor = OCOOrderExecutor(mock_client)
    oco_order = oco_executor.place_tp_sl_orders(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=40000,
        quantity=0.1,
        take_profit_price=42000,
        stop_loss_price=38000
    )
    print(f"OCO order: {oco_order}")
    
    print("\n=== Testing Order Execution Factory ===")
    factory = OrderExecutionFactory()
    custom_executor = factory.create_executor("iceberg", mock_client, random_variation=True)
    print(f"Created executor: {type(custom_executor).__name__}")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()