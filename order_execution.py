"""
Module phương thức đi lệnh nâng cao (Advanced Order Execution)

Module này cung cấp các phương thức đi lệnh tiên tiến để tối ưu hóa việc thực thi lệnh:
- Iceberg Orders: Chia lệnh lớn thành nhiều lệnh nhỏ để giảm tác động thị trường
- TWAP (Time-Weighted Average Price): Chia lệnh theo thời gian với khoảng cách đều
- VWAP (Volume-Weighted Average Price): Chia lệnh theo phân bổ khối lượng
- Scaled Orders: Đặt lệnh theo nhiều mức giá khác nhau
- OCO (One-Cancels-Other) Orders: Đặt cùng lúc lệnh take profit và stop loss

Mục tiêu là tối ưu hóa giá thực thi và giảm thiểu slippage khi thực hiện các lệnh lớn.
"""

import time
import threading
import uuid
import logging
from typing import Dict, List, Tuple, Union, Optional
import numpy as np

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("order_execution")

class BaseOrderExecutor:
    """Lớp cơ sở để thực thi lệnh"""
    
    def __init__(self, api_client):
        """
        Khởi tạo Base Order Executor.
        
        Args:
            api_client: Đối tượng API client để thực hiện các lệnh giao dịch
        """
        self.api_client = api_client
        
    def execute_order(self, symbol: str, side: str, quantity: float, 
                    order_type: str = 'MARKET', price: float = None, 
                    time_in_force: str = 'GTC', **kwargs) -> Dict:
        """
        Thực hiện lệnh giao dịch.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            quantity (float): Số lượng giao dịch
            order_type (str): Loại lệnh ('MARKET', 'LIMIT', ...)
            price (float, optional): Giá đặt lệnh (bắt buộc với LIMIT orders)
            time_in_force (str): Thời gian hiệu lực của lệnh ('GTC', 'IOC', 'FOK')
            **kwargs: Các tham số bổ sung
            
        Returns:
            Dict: Thông tin lệnh đã thực hiện
        """
        try:
            # Validate input
            if quantity <= 0:
                logger.error(f"Invalid quantity: {quantity}")
                return {"error": "Invalid quantity"}
                
            if order_type == 'LIMIT' and (price is None or price <= 0):
                logger.error(f"Price required for LIMIT order")
                return {"error": "Price required for LIMIT order"}
                
            # Chuẩn bị tham số cho lệnh
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'timeInForce': time_in_force if order_type != 'MARKET' else None
            }
            
            # Thêm giá nếu không phải lệnh thị trường
            if order_type != 'MARKET' and price is not None:
                order_params['price'] = price
                
            # Thêm các tham số khác
            for key, value in kwargs.items():
                order_params[key] = value
                
            # Loại bỏ các giá trị None
            order_params = {k: v for k, v in order_params.items() if v is not None}
            
            # Thực thi lệnh
            logger.info(f"Executing order: {order_params}")
            response = self.api_client.create_order(**order_params)
            
            logger.info(f"Order executed: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error executing order: {e}")
            return {"error": str(e)}
            
    def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """
        Lấy trạng thái của một lệnh.
        
        Args:
            symbol (str): Mã cặp giao dịch
            order_id (str): ID của lệnh
            
        Returns:
            Dict: Thông tin trạng thái lệnh
        """
        try:
            response = self.api_client.get_order(symbol=symbol, orderId=order_id)
            return response
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {"error": str(e)}
            
    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """
        Hủy một lệnh.
        
        Args:
            symbol (str): Mã cặp giao dịch
            order_id (str): ID của lệnh
            
        Returns:
            Dict: Thông tin lệnh đã hủy
        """
        try:
            response = self.api_client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"Order cancelled: {response}")
            return response
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {"error": str(e)}
            
    def calculate_average_fill_price(self, order_response: Dict) -> float:
        """
        Tính giá thực thi trung bình của một lệnh.
        
        Args:
            order_response (Dict): Phản hồi từ API khi thực thi lệnh
            
        Returns:
            float: Giá thực thi trung bình
        """
        if 'fills' not in order_response:
            if 'price' in order_response:
                return float(order_response['price'])
            return 0.0
            
        fills = order_response['fills']
        if not fills:
            return 0.0
            
        total_qty = 0.0
        total_cost = 0.0
        
        for fill in fills:
            qty = float(fill['qty'])
            price = float(fill['price'])
            total_qty += qty
            total_cost += qty * price
            
        if total_qty == 0:
            return 0.0
            
        return total_cost / total_qty


class IcebergOrderExecutor(BaseOrderExecutor):
    """Lớp thực thi Iceberg Orders - chia lệnh lớn thành nhiều lệnh nhỏ"""
    
    def execute_iceberg_order(self, symbol: str, side: str, total_quantity: float,
                            num_parts: int = 5, price: float = None, 
                            order_type: str = 'MARKET', random_variance: float = 0.1,
                            time_between_parts: float = 30.0, **kwargs) -> List[Dict]:
        """
        Thực hiện Iceberg Order bằng cách chia lệnh lớn thành nhiều lệnh nhỏ.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            total_quantity (float): Tổng số lượng giao dịch
            num_parts (int): Số lượng lệnh nhỏ
            price (float, optional): Giá đặt lệnh (bắt buộc với LIMIT orders)
            order_type (str): Loại lệnh ('MARKET', 'LIMIT', ...)
            random_variance (float): Biến thiên ngẫu nhiên của kích thước lệnh (%)
            time_between_parts (float): Thời gian giữa các lệnh nhỏ (giây)
            **kwargs: Các tham số bổ sung
            
        Returns:
            List[Dict]: Danh sách các lệnh đã thực hiện
        """
        if total_quantity <= 0 or num_parts <= 0:
            logger.error(f"Invalid parameters: total_quantity={total_quantity}, num_parts={num_parts}")
            return []
            
        # Tính kích thước lệnh cơ bản
        base_quantity = total_quantity / num_parts
        
        # Khởi tạo danh sách kết quả
        results = []
        remaining_quantity = total_quantity
        
        logger.info(f"Starting iceberg order: {symbol} {side} {total_quantity} in {num_parts} parts")
        
        for i in range(num_parts):
            # Tính kích thước phần còn lại và của lệnh hiện tại
            is_last_part = (i == num_parts - 1)
            
            if is_last_part:
                # Phần cuối cùng lấy tất cả số lượng còn lại
                part_quantity = remaining_quantity
            else:
                # Tính kích thước với biến thiên ngẫu nhiên
                if random_variance > 0:
                    variance = np.random.uniform(-random_variance, random_variance)
                    variance_factor = 1.0 + variance
                else:
                    variance_factor = 1.0
                    
                part_quantity = min(base_quantity * variance_factor, remaining_quantity)
                
            # Đảm bảo part_quantity > 0
            part_quantity = max(0.000001, part_quantity)
            
            # Thực thi lệnh nhỏ
            logger.info(f"Executing part {i+1}/{num_parts}: {part_quantity} ({part_quantity/total_quantity*100:.1f}%)")
            
            order_result = self.execute_order(
                symbol=symbol,
                side=side,
                quantity=part_quantity,
                order_type=order_type,
                price=price,
                **kwargs
            )
            
            results.append(order_result)
            
            # Cập nhật số lượng còn lại
            if 'executedQty' in order_result:
                executed_qty = float(order_result['executedQty'])
            else:
                executed_qty = part_quantity
                
            remaining_quantity -= executed_qty
            
            # Nếu không còn phần nào cần thực thi, thoát
            if remaining_quantity <= 0 or is_last_part:
                break
                
            # Chờ đến lệnh tiếp theo
            if time_between_parts > 0 and i < num_parts - 1:
                time.sleep(time_between_parts)
                
        logger.info(f"Completed iceberg order with {len(results)} parts")
        return results
    
    def calculate_average_fill_price(self, order_results: List[Dict]) -> float:
        """
        Tính giá thực thi trung bình của cả iceberg order.
        
        Args:
            order_results (List[Dict]): Danh sách kết quả các lệnh nhỏ
            
        Returns:
            float: Giá thực thi trung bình
        """
        if not order_results:
            return 0.0
            
        total_qty = 0.0
        total_cost = 0.0
        
        for order in order_results:
            # Nếu lệnh có chi tiết fills
            if 'fills' in order and order['fills']:
                for fill in order['fills']:
                    qty = float(fill['qty'])
                    price = float(fill['price'])
                    total_qty += qty
                    total_cost += qty * price
            
            # Nếu lệnh không có chi tiết fills nhưng có executedQty và price
            elif 'executedQty' in order and 'price' in order and float(order['executedQty']) > 0:
                qty = float(order['executedQty'])
                price = float(order['price'])
                total_qty += qty
                total_cost += qty * price
                
        if total_qty == 0:
            return 0.0
            
        return total_cost / total_qty


class TWAPExecutor(BaseOrderExecutor):
    """Lớp thực thi TWAP (Time-Weighted Average Price) Orders"""
    
    def __init__(self, api_client):
        """
        Khởi tạo TWAP Executor.
        
        Args:
            api_client: Đối tượng API client để thực hiện các lệnh giao dịch
        """
        super().__init__(api_client)
        self.active_executions = {}  # Lưu trữ các TWAP đang chạy
        self._lock = threading.Lock()  # Lock cho thread safety
        
    def execute_twap_order(self, symbol: str, side: str, total_quantity: float,
                         duration_minutes: float, num_parts: int = 10,
                         order_type: str = 'MARKET', price: float = None,
                         wait_for_completion: bool = False, **kwargs) -> str:
        """
        Thực hiện TWAP Order.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            total_quantity (float): Tổng số lượng giao dịch
            duration_minutes (float): Thời gian thực hiện tổng thể (phút)
            num_parts (int): Số lượng lệnh nhỏ
            order_type (str): Loại lệnh ('MARKET', 'LIMIT', ...)
            price (float, optional): Giá đặt lệnh (bắt buộc với LIMIT orders)
            wait_for_completion (bool): Đợi cho đến khi hoàn thành
            **kwargs: Các tham số bổ sung
            
        Returns:
            str: ID của TWAP execution
        """
        if total_quantity <= 0 or duration_minutes <= 0 or num_parts <= 0:
            logger.error(f"Invalid parameters: total_quantity={total_quantity}, " + 
                       f"duration_minutes={duration_minutes}, num_parts={num_parts}")
            return ""
            
        # Tạo ID cho TWAP execution
        execution_id = str(uuid.uuid4())
        
        # Tính kích thước lệnh và khoảng thời gian
        part_quantity = total_quantity / num_parts
        time_interval = (duration_minutes * 60) / num_parts  # seconds
        
        # Tạo thông tin TWAP
        twap_info = {
            'symbol': symbol,
            'side': side,
            'total_quantity': total_quantity,
            'remaining_quantity': total_quantity,
            'part_quantity': part_quantity,
            'num_parts': num_parts,
            'parts_completed': 0,
            'time_interval': time_interval,
            'order_type': order_type,
            'price': price,
            'start_time': time.time(),
            'duration_seconds': duration_minutes * 60,
            'orders': [],
            'is_active': True,
            'kwargs': kwargs
        }
        
        # Lưu vào active executions
        with self._lock:
            self.active_executions[execution_id] = twap_info
            
        # Tạo và start thread thực thi
        twap_thread = threading.Thread(
            target=self._run_twap_execution,
            args=(execution_id,),
            daemon=True
        )
        twap_thread.start()
        
        logger.info(f"Started TWAP execution {execution_id} for {symbol} {side} {total_quantity}")
        
        # Nếu wait_for_completion, đợi cho đến khi thread kết thúc
        if wait_for_completion:
            twap_thread.join()
            
        return execution_id
        
    def _run_twap_execution(self, execution_id: str) -> None:
        """
        Thread thực thi TWAP.
        
        Args:
            execution_id (str): ID của TWAP execution
        """
        try:
            # Kiểm tra xem execution_id có tồn tại
            with self._lock:
                if execution_id not in self.active_executions:
                    logger.error(f"TWAP execution {execution_id} not found")
                    return
                    
                twap_info = self.active_executions[execution_id]
                
            # Lấy các tham số
            symbol = twap_info['symbol']
            side = twap_info['side']
            part_quantity = twap_info['part_quantity']
            num_parts = twap_info['num_parts']
            time_interval = twap_info['time_interval']
            order_type = twap_info['order_type']
            price = twap_info['price']
            kwargs = twap_info['kwargs']
            
            # Thực thi từng phần
            for i in range(num_parts):
                # Kiểm tra xem TWAP có còn active
                with self._lock:
                    if execution_id not in self.active_executions or not self.active_executions[execution_id]['is_active']:
                        logger.info(f"TWAP execution {execution_id} was cancelled")
                        return
                        
                    current_info = self.active_executions[execution_id]
                    
                # Tính toán số lượng phần còn lại và của lệnh hiện tại
                is_last_part = (i == num_parts - 1)
                
                if is_last_part:
                    # Phần cuối cùng lấy tất cả số lượng còn lại
                    current_quantity = current_info['remaining_quantity']
                else:
                    current_quantity = min(part_quantity, current_info['remaining_quantity'])
                    
                # Đảm bảo current_quantity > 0
                if current_quantity <= 0:
                    break
                    
                # Thực thi lệnh nhỏ
                logger.info(f"TWAP {execution_id}: Executing part {i+1}/{num_parts}: {current_quantity}")
                
                order_result = self.execute_order(
                    symbol=symbol,
                    side=side,
                    quantity=current_quantity,
                    order_type=order_type,
                    price=price,
                    **kwargs
                )
                
                # Cập nhật thông tin TWAP
                with self._lock:
                    if execution_id in self.active_executions:
                        # Cập nhật số lượng đã thực thi
                        if 'executedQty' in order_result:
                            executed_qty = float(order_result['executedQty'])
                        else:
                            executed_qty = current_quantity
                            
                        self.active_executions[execution_id]['remaining_quantity'] -= executed_qty
                        self.active_executions[execution_id]['parts_completed'] += 1
                        self.active_executions[execution_id]['orders'].append(order_result)
                        
                # Nếu không còn phần nào cần thực thi, thoát
                if current_info['remaining_quantity'] <= 0 or is_last_part:
                    break
                    
                # Chờ đến lệnh tiếp theo
                time.sleep(time_interval)
                
            # Đánh dấu TWAP đã hoàn thành
            with self._lock:
                if execution_id in self.active_executions:
                    self.active_executions[execution_id]['is_active'] = False
                    
            logger.info(f"TWAP execution {execution_id} completed")
            
        except Exception as e:
            logger.error(f"Error in TWAP execution {execution_id}: {e}")
            # Đánh dấu lỗi
            with self._lock:
                if execution_id in self.active_executions:
                    self.active_executions[execution_id]['is_active'] = False
                    self.active_executions[execution_id]['error'] = str(e)
                    
    def cancel_twap_execution(self, execution_id: str) -> bool:
        """
        Hủy một TWAP đang chạy.
        
        Args:
            execution_id (str): ID của TWAP execution
            
        Returns:
            bool: True nếu hủy thành công, False nếu không
        """
        with self._lock:
            if execution_id not in self.active_executions:
                logger.warning(f"TWAP execution {execution_id} not found")
                return False
                
            # Đánh dấu không active nữa
            self.active_executions[execution_id]['is_active'] = False
            
            logger.info(f"TWAP execution {execution_id} cancelled")
            return True
            
    def get_twap_status(self, execution_id: str) -> Dict:
        """
        Lấy trạng thái của một TWAP.
        
        Args:
            execution_id (str): ID của TWAP execution
            
        Returns:
            Dict: Thông tin trạng thái TWAP
        """
        with self._lock:
            if execution_id not in self.active_executions:
                logger.warning(f"TWAP execution {execution_id} not found")
                return {"error": "TWAP execution not found"}
                
            twap_info = self.active_executions[execution_id]
            
            # Tính toán thông tin bổ sung
            total_executed = twap_info['total_quantity'] - twap_info['remaining_quantity']
            completion_pct = (total_executed / twap_info['total_quantity']) * 100 if twap_info['total_quantity'] > 0 else 0
            
            elapsed_seconds = time.time() - twap_info['start_time']
            time_pct = (elapsed_seconds / twap_info['duration_seconds']) * 100 if twap_info['duration_seconds'] > 0 else 0
            
            # Tính giá trung bình
            avg_price = self.calculate_average_fill_price(twap_info['orders'])
            
            status = {
                'execution_id': execution_id,
                'symbol': twap_info['symbol'],
                'side': twap_info['side'],
                'total_quantity': twap_info['total_quantity'],
                'executed_quantity': total_executed,
                'remaining_quantity': twap_info['remaining_quantity'],
                'completion_percentage': completion_pct,
                'time_percentage': time_pct,
                'parts_completed': twap_info['parts_completed'],
                'total_parts': twap_info['num_parts'],
                'average_price': avg_price,
                'is_active': twap_info['is_active'],
                'error': twap_info.get('error', None)
            }
            
            return status
            
    def calculate_average_fill_price(self, order_results: List[Dict]) -> float:
        """
        Tính giá thực thi trung bình của TWAP.
        
        Args:
            order_results (List[Dict]): Danh sách kết quả các lệnh nhỏ
            
        Returns:
            float: Giá thực thi trung bình
        """
        # Sử dụng lại từ IcebergOrderExecutor
        iceberg_executor = IcebergOrderExecutor(self.api_client)
        return iceberg_executor.calculate_average_fill_price(order_results)


class ScaledOrderExecutor(BaseOrderExecutor):
    """Lớp thực thi Scaled Orders - đặt lệnh theo nhiều mức giá khác nhau"""
    
    def execute_scaled_entry(self, symbol: str, side: str, total_quantity: float,
                           price_low: float, price_high: float, num_levels: int = 5,
                           distribution: str = 'uniform', **kwargs) -> List[Dict]:
        """
        Thực hiện Scaled Entry Order - đặt lệnh theo nhiều mức giá khác nhau.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            total_quantity (float): Tổng số lượng giao dịch
            price_low (float): Mức giá thấp nhất
            price_high (float): Mức giá cao nhất
            num_levels (int): Số lượng mức giá
            distribution (str): Phân phối khối lượng ('uniform', 'ascending', 'descending')
            **kwargs: Các tham số bổ sung
            
        Returns:
            List[Dict]: Danh sách các lệnh đã đặt
        """
        if total_quantity <= 0 or price_low <= 0 or price_high <= 0 or num_levels <= 0:
            logger.error(f"Invalid parameters: total_quantity={total_quantity}, " + 
                       f"price_low={price_low}, price_high={price_high}, num_levels={num_levels}")
            return []
            
        # Đảm bảo price_low < price_high
        if price_low > price_high:
            price_low, price_high = price_high, price_low
            
        # Tính các mức giá
        if num_levels == 1:
            price_levels = [price_low]
        else:
            price_step = (price_high - price_low) / (num_levels - 1)
            price_levels = [price_low + i * price_step for i in range(num_levels)]
            
        # Tính phân phối khối lượng
        if distribution == 'uniform':
            # Đều nhau
            quantities = [total_quantity / num_levels] * num_levels
        elif distribution == 'ascending':
            # Tăng dần (nhiều hơn ở giá cao)
            weights = [i+1 for i in range(num_levels)]
            total_weight = sum(weights)
            quantities = [(total_quantity * w / total_weight) for w in weights]
        elif distribution == 'descending':
            # Giảm dần (nhiều hơn ở giá thấp)
            weights = [num_levels-i for i in range(num_levels)]
            total_weight = sum(weights)
            quantities = [(total_quantity * w / total_weight) for w in weights]
        else:
            # Mặc định là đều nhau
            quantities = [total_quantity / num_levels] * num_levels
            
        # Đặt lệnh ở mỗi mức giá
        results = []
        for i, (price, quantity) in enumerate(zip(price_levels, quantities)):
            # Đảm bảo quantity > 0
            quantity = max(0.000001, quantity)
            
            logger.info(f"Placing scaled order {i+1}/{num_levels}: {symbol} {side} {quantity} @ {price}")
            
            order_result = self.execute_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type='LIMIT',
                price=price,
                **kwargs
            )
            
            results.append(order_result)
            
        logger.info(f"Placed {len(results)} scaled orders for {symbol} {side}")
        return results
        
    def execute_scaled_exit(self, symbol: str, side: str, total_quantity: float,
                          price_low: float, price_high: float, num_levels: int = 5,
                          distribution: str = 'ascending', **kwargs) -> List[Dict]:
        """
        Thực hiện Scaled Exit Order - đặt lệnh thoát theo nhiều mức giá khác nhau.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng lệnh ('BUY' hoặc 'SELL')
            total_quantity (float): Tổng số lượng giao dịch
            price_low (float): Mức giá thấp nhất
            price_high (float): Mức giá cao nhất
            num_levels (int): Số lượng mức giá
            distribution (str): Phân phối khối lượng ('uniform', 'ascending', 'descending')
            **kwargs: Các tham số bổ sung
            
        Returns:
            List[Dict]: Danh sách các lệnh đã đặt
        """
        # Scaled exit về cơ bản giống scaled entry
        return self.execute_scaled_entry(
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            price_low=price_low,
            price_high=price_high,
            num_levels=num_levels,
            distribution=distribution,
            **kwargs
        )
        
    def calculate_average_fill_price(self, order_results: List[Dict]) -> float:
        """
        Tính giá thực thi trung bình của các lệnh.
        
        Args:
            order_results (List[Dict]): Danh sách kết quả các lệnh
            
        Returns:
            float: Giá thực thi trung bình
        """
        # Sử dụng lại từ IcebergOrderExecutor
        iceberg_executor = IcebergOrderExecutor(self.api_client)
        return iceberg_executor.calculate_average_fill_price(order_results)


class OCOOrderExecutor(BaseOrderExecutor):
    """Lớp thực thi OCO Orders - One-Cancels-Other Orders"""
    
    def place_tp_sl_orders(self, symbol: str, side: str, entry_price: float, quantity: float,
                         take_profit_price: float, stop_loss_price: float,
                         stop_limit_price_delta: float = 0.5, **kwargs) -> Dict:
        """
        Đặt lệnh OCO (One-Cancels-Other) bao gồm lệnh chốt lời và dừng lỗ.
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            entry_price (float): Giá vào lệnh
            quantity (float): Số lượng giao dịch
            take_profit_price (float): Giá chốt lời
            stop_loss_price (float): Giá dừng lỗ
            stop_limit_price_delta (float): Chênh lệch giữa stop price và limit price (%)
            **kwargs: Các tham số bổ sung
            
        Returns:
            Dict: Thông tin lệnh OCO
        """
        if quantity <= 0 or entry_price <= 0 or take_profit_price <= 0 or stop_loss_price <= 0:
            logger.error(f"Invalid parameters: quantity={quantity}, entry_price={entry_price}, " + 
                       f"take_profit_price={take_profit_price}, stop_loss_price={stop_loss_price}")
            return {"error": "Invalid parameters"}
            
        # Xác định hướng lệnh và kiểm tra giá
        if side.upper() == 'LONG':
            # Với vị thế LONG, ta cần SELL để TP/SL
            oco_side = 'SELL'
            
            # Validate price levels
            if take_profit_price <= entry_price:
                logger.error(f"Take profit price must be higher than entry price for LONG positions")
                return {"error": "Take profit price must be higher than entry price for LONG positions"}
                
            if stop_loss_price >= entry_price:
                logger.error(f"Stop loss price must be lower than entry price for LONG positions")
                return {"error": "Stop loss price must be lower than entry price for LONG positions"}
                
        elif side.upper() == 'SHORT':
            # Với vị thế SHORT, ta cần BUY để TP/SL
            oco_side = 'BUY'
            
            # Validate price levels
            if take_profit_price >= entry_price:
                logger.error(f"Take profit price must be lower than entry price for SHORT positions")
                return {"error": "Take profit price must be lower than entry price for SHORT positions"}
                
            if stop_loss_price <= entry_price:
                logger.error(f"Stop loss price must be higher than entry price for SHORT positions")
                return {"error": "Stop loss price must be higher than entry price for SHORT positions"}
                
        else:
            logger.error(f"Invalid side: {side}. Must be 'LONG' or 'SHORT'")
            return {"error": "Invalid side. Must be 'LONG' or 'SHORT'"}
            
        # Tính giá limit cho stop loss
        stop_limit_price_pct = 1.0 - (stop_limit_price_delta / 100.0) if oco_side == 'SELL' else 1.0 + (stop_limit_price_delta / 100.0)
        stop_limit_price = stop_loss_price * stop_limit_price_pct
        
        # Round prices to valid precision
        # Note: In production, you would need to get the actual precision from the exchange
        take_profit_price = round(take_profit_price, 2)
        stop_loss_price = round(stop_loss_price, 2)
        stop_limit_price = round(stop_limit_price, 2)
        
        try:
            logger.info(f"Placing OCO order: {symbol} {oco_side} {quantity} " + 
                      f"TP: {take_profit_price}, SL: {stop_loss_price}, SL-Limit: {stop_limit_price}")
            
            # Đặt lệnh OCO
            if oco_side == 'SELL':
                response = self.api_client.order_oco_sell(
                    symbol=symbol,
                    quantity=quantity,
                    price=take_profit_price,
                    stopPrice=stop_loss_price,
                    stopLimitPrice=stop_limit_price,
                    **kwargs
                )
            else:  # 'BUY'
                response = self.api_client.order_oco_buy(
                    symbol=symbol,
                    quantity=quantity,
                    price=take_profit_price,
                    stopPrice=stop_loss_price,
                    stopLimitPrice=stop_limit_price,
                    **kwargs
                )
                
            logger.info(f"OCO order placed: {response}")
            
            # Thêm thông tin phụ
            response['entry_price'] = entry_price
            response['position_side'] = side
            response['take_profit_price'] = take_profit_price
            response['stop_loss_price'] = stop_loss_price
            
            return response
            
        except Exception as e:
            logger.error(f"Error placing OCO order: {e}")
            return {"error": str(e)}
            
    def get_oco_order_status(self, symbol: str, order_list_id: str) -> Dict:
        """
        Lấy trạng thái của một lệnh OCO.
        
        Args:
            symbol (str): Mã cặp giao dịch
            order_list_id (str): ID của lệnh OCO
            
        Returns:
            Dict: Thông tin trạng thái lệnh OCO
        """
        try:
            response = self.api_client.get_order_list(orderListId=order_list_id)
            return response
        except Exception as e:
            logger.error(f"Error getting OCO order status: {e}")
            return {"error": str(e)}
            
    def cancel_oco_order(self, symbol: str, order_list_id: str) -> Dict:
        """
        Hủy một lệnh OCO.
        
        Args:
            symbol (str): Mã cặp giao dịch
            order_list_id (str): ID của lệnh OCO
            
        Returns:
            Dict: Thông tin lệnh OCO đã hủy
        """
        try:
            response = self.api_client.cancel_order_list(symbol=symbol, orderListId=order_list_id)
            logger.info(f"OCO order cancelled: {response}")
            return response
        except Exception as e:
            logger.error(f"Error cancelling OCO order: {e}")
            return {"error": str(e)}


class OrderExecutionFactory:
    """Factory để tạo ra các đối tượng thực thi lệnh phù hợp"""
    
    def create_executor(self, executor_type: str, api_client) -> BaseOrderExecutor:
        """
        Tạo đối tượng thực thi lệnh phù hợp.
        
        Args:
            executor_type (str): Loại executor ('base', 'iceberg', 'twap', 'scaled', 'oco')
            api_client: Đối tượng API client để thực hiện các lệnh giao dịch
            
        Returns:
            BaseOrderExecutor: Đối tượng thực thi lệnh
        """
        executor_type = executor_type.lower()
        
        if executor_type == 'base':
            return BaseOrderExecutor(api_client)
        elif executor_type == 'iceberg':
            return IcebergOrderExecutor(api_client)
        elif executor_type == 'twap':
            return TWAPExecutor(api_client)
        elif executor_type == 'scaled':
            return ScaledOrderExecutor(api_client)
        elif executor_type == 'oco':
            return OCOOrderExecutor(api_client)
        else:
            logger.warning(f"Unknown executor type: {executor_type}, falling back to base executor")
            return BaseOrderExecutor(api_client)


def main():
    """Hàm demo"""
    # Mock API client để test
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
                'fills': [
                    {'price': kwargs.get('price') or 40000, 'qty': kwargs.get('quantity')}
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
    
    # Tạo mock client
    mock_client = MockAPIClient()
    
    # Test các executor
    print("=== Testing Order Executors ===")
    
    # Base Executor
    print("\n--- Base Executor ---")
    base_executor = BaseOrderExecutor(mock_client)
    base_executor.execute_order(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.1,
        order_type="MARKET"
    )
    
    # Iceberg Executor
    print("\n--- Iceberg Executor ---")
    iceberg_executor = IcebergOrderExecutor(mock_client)
    iceberg_orders = iceberg_executor.execute_iceberg_order(
        symbol="BTCUSDT",
        side="BUY",
        total_quantity=0.5,
        num_parts=3,
        time_between_parts=0.1  # Quick for demo
    )
    avg_price = iceberg_executor.calculate_average_fill_price(iceberg_orders)
    print(f"Average fill price: {avg_price}")
    
    # TWAP Executor
    print("\n--- TWAP Executor ---")
    twap_executor = TWAPExecutor(mock_client)
    execution_id = twap_executor.execute_twap_order(
        symbol="BTCUSDT",
        side="BUY",
        total_quantity=0.5,
        duration_minutes=0.1,  # Quick for demo
        num_parts=2,
        wait_for_completion=True
    )
    status = twap_executor.get_twap_status(execution_id)
    print(f"TWAP status: {status}")
    
    # Scaled Executor
    print("\n--- Scaled Executor ---")
    scaled_executor = ScaledOrderExecutor(mock_client)
    scaled_orders = scaled_executor.execute_scaled_entry(
        symbol="BTCUSDT",
        side="BUY",
        total_quantity=0.5,
        price_low=39000,
        price_high=40000,
        num_levels=3,
        distribution="ascending"
    )
    
    # OCO Executor
    print("\n--- OCO Executor ---")
    oco_executor = OCOOrderExecutor(mock_client)
    oco_order = oco_executor.place_tp_sl_orders(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=40000,
        quantity=0.1,
        take_profit_price=42000,
        stop_loss_price=38000
    )
    
    # Factory
    print("\n--- Order Execution Factory ---")
    factory = OrderExecutionFactory()
    base = factory.create_executor("base", mock_client)
    iceberg = factory.create_executor("iceberg", mock_client)
    twap = factory.create_executor("twap", mock_client)
    scaled = factory.create_executor("scaled", mock_client)
    oco = factory.create_executor("oco", mock_client)
    
    print(f"Created executors: {type(base).__name__}, {type(iceberg).__name__}, " + 
          f"{type(twap).__name__}, {type(scaled).__name__}, {type(oco).__name__}")

if __name__ == "__main__":
    main()