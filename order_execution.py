"""
Module thực thi lệnh (Order Execution)

Module này cung cấp các phương pháp thực thi lệnh khác nhau, từ đơn giản đến nâng cao,
giúp tối ưu hóa quá trình thực thi và giảm thiểu ảnh hưởng đến thị trường.
"""

import logging
import time
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Union, Callable

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("order_execution")

class BaseOrderExecutor:
    """Lớp cơ sở cho thực thi lệnh"""
    
    def __init__(self, api_client):
        """
        Khởi tạo order executor cơ bản
        
        Args:
            api_client (object): Đối tượng API client
        """
        self.api_client = api_client
        self.name = "Base Order Executor"
        
    def execute_order(self, symbol, side, quantity, order_type='MARKET', price=None, 
                    time_in_force='GTC', **kwargs):
        """
        Thực thi lệnh giao dịch
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            side (str): Bên giao dịch (BUY/SELL)
            quantity (float): Số lượng
            order_type (str): Loại lệnh (MARKET/LIMIT/...)
            price (float, optional): Giá đặt lệnh
            time_in_force (str): Hiệu lực thời gian của lệnh
            **kwargs: Tham số bổ sung
            
        Returns:
            Dict: Thông tin lệnh đã thực thi
        """
        try:
            # Kiểm tra đầu vào
            if quantity <= 0:
                logger.error(f"Số lượng không hợp lệ: {quantity}")
                return {"error": "Số lượng không hợp lệ"}
                
            if order_type == 'LIMIT' and (price is None or price <= 0):
                logger.error(f"Giá LIMIT không hợp lệ: {price}")
                return {"error": "Giá LIMIT không hợp lệ"}
                
            # Tạo tham số lệnh
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'timeInForce': time_in_force if order_type != 'MARKET' else None
            }
            
            if order_type != 'MARKET' and price is not None:
                order_params['price'] = price
                
            # Thêm các tham số khác
            for key, value in kwargs.items():
                order_params[key] = value
                
            # Loại bỏ tham số None
            order_params = {k: v for k, v in order_params.items() if v is not None}
            
            # Thực thi lệnh
            response = self.api_client.create_order(**order_params)
            logger.info(f"Lệnh thực thi: {symbol} {side} {quantity} giá {price or 'MARKET'}")
            return response
            
        except Exception as e:
            logger.error(f"Lỗi khi thực thi lệnh: {e}")
            return {"error": str(e)}
            
    def calculate_average_fill_price(self, order_response):
        """
        Tính giá trung bình thực hiện lệnh
        
        Args:
            order_response (Dict): Thông tin lệnh
            
        Returns:
            float: Giá trung bình
        """
        if not order_response:
            return 0.0
        
        # Xử lý trường hợp nếu order_response là một object đơn lẻ
        if isinstance(order_response, dict):
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
        
        # Nếu order_response là một list
        total_qty = 0.0
        total_cost = 0.0
        
        for order in order_response:
            if 'fills' in order and order['fills']:
                for fill in order['fills']:
                    qty = float(fill['qty'])
                    price = float(fill['price'])
                    total_qty += qty
                    total_cost += qty * price
            
            elif 'executedQty' in order and 'price' in order and float(order['executedQty']) > 0:
                qty = float(order['executedQty'])
                price = float(order['price'])
                total_qty += qty
                total_cost += qty * price
        
        if total_qty == 0:
            return 0.0
            
        return total_cost / total_qty
        
class IcebergOrderExecutor(BaseOrderExecutor):
    """Lớp thực thi lệnh iceberg (chia lệnh lớn thành nhiều lệnh nhỏ)"""
    
    def __init__(self, api_client):
        """
        Khởi tạo iceberg order executor
        
        Args:
            api_client (object): Đối tượng API client
        """
        super().__init__(api_client)
        self.name = "Iceberg Order Executor"
        
    def execute_iceberg_order(self, symbol, side, total_quantity, num_parts=5, price=None, 
                            order_type='MARKET', random_variance=0.1, time_between_parts=30.0, **kwargs):
        """
        Thực thi lệnh iceberg (chia thành nhiều phần)
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            side (str): Bên giao dịch (BUY/SELL)
            total_quantity (float): Tổng số lượng
            num_parts (int): Số lượng phần chia
            price (float, optional): Giá đặt lệnh
            order_type (str): Loại lệnh (MARKET/LIMIT/...)
            random_variance (float): Biến động ngẫu nhiên cho kích thước mỗi phần (0-1)
            time_between_parts (float): Thời gian giữa các phần (giây)
            **kwargs: Tham số bổ sung
            
        Returns:
            List[Dict]: Danh sách các lệnh đã thực thi
        """
        if total_quantity <= 0 or num_parts <= 0:
            logger.error(f"Tham số không hợp lệ")
            return []
            
        # Kích thước cơ bản mỗi phần
        base_quantity = total_quantity / num_parts
        results = []
        remaining_quantity = total_quantity
        
        for i in range(num_parts):
            is_last_part = (i == num_parts - 1)
            
            if is_last_part:
                # Phần cuối cùng sẽ lấy toàn bộ số lượng còn lại
                part_quantity = remaining_quantity
            else:
                # Các phần khác sẽ có biến động ngẫu nhiên nếu có
                if random_variance > 0:
                    variance = random.uniform(-random_variance, random_variance)
                    variance_factor = 1.0 + variance
                else:
                    variance_factor = 1.0
                    
                part_quantity = min(base_quantity * variance_factor, remaining_quantity)
            
            # Đảm bảo số lượng hợp lệ
            part_quantity = max(0.000001, part_quantity)
            
            # Thực thi phần lệnh
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
            
            # Kiểm tra nếu đã hết số lượng
            if remaining_quantity <= 0 or is_last_part:
                break
                
            # Đợi giữa các phần
            if time_between_parts > 0 and i < num_parts - 1:
                time.sleep(time_between_parts)
                
        return results
        
    def calculate_average_fill_price(self, order_response):
        """
        Tính giá trung bình thực hiện cho nhiều lệnh
        
        Args:
            order_response (List[Dict]): Danh sách các lệnh
            
        Returns:
            float: Giá trung bình
        """
        if not order_response:
            return 0.0
            
        # Xử lý trường hợp nếu order_response là một object đơn lẻ
        if isinstance(order_response, dict):
            # Nếu order_response là một dict không phải list, chuyển nó thành list để xử lý
            orders = [order_response]
        else:
            # Nếu đã là list thì giữ nguyên
            orders = order_response
            
        total_qty = 0.0
        total_cost = 0.0
        
        for order in orders:
            if 'fills' in order and order['fills']:
                for fill in order['fills']:
                    qty = float(fill['qty'])
                    price = float(fill['price'])
                    total_qty += qty
                    total_cost += qty * price
            
            elif 'executedQty' in order and 'price' in order and float(order['executedQty']) > 0:
                qty = float(order['executedQty'])
                price = float(order['price'])
                total_qty += qty
                total_cost += qty * price
                
        if total_qty == 0:
            return 0.0
            
        return total_cost / total_qty
        
class TWAPExecutor(BaseOrderExecutor):
    """
    Lớp thực thi lệnh TWAP (Time Weighted Average Price)
    
    Chia lệnh giao dịch thành các phần đều nhau và thực thi trong một khoảng thời gian xác định
    """
    
    def __init__(self, api_client):
        """
        Khởi tạo TWAP executor
        
        Args:
            api_client (object): Đối tượng API client
        """
        super().__init__(api_client)
        self.name = "TWAP Executor"
        
    def execute_twap_order(self, symbol, side, total_quantity, duration_minutes, num_slices, 
                         order_type='LIMIT', price_offset_pct=0.05, **kwargs):
        """
        Thực thi lệnh TWAP (Time Weighted Average Price)
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            side (str): Bên giao dịch (BUY/SELL)
            total_quantity (float): Tổng số lượng
            duration_minutes (int): Thời gian thực thi (phút)
            num_slices (int): Số lượng phần chia
            order_type (str): Loại lệnh (MARKET/LIMIT/...)
            price_offset_pct (float): Phần trăm chênh lệch giá so với thị trường
            **kwargs: Tham số bổ sung
            
        Returns:
            Dict: Kết quả thực thi
        """
        if total_quantity <= 0 or duration_minutes <= 0 or num_slices <= 0:
            logger.error(f"Tham số không hợp lệ")
            return {"error": "Tham số không hợp lệ"}
            
        # Tính toán các tham số
        slice_quantity = total_quantity / num_slices
        time_per_slice = (duration_minutes * 60) / num_slices
        
        results = []
        remaining_quantity = total_quantity
        start_time = datetime.now()
        
        for i in range(num_slices):
            # Tính thời gian bắt đầu của phần hiện tại
            slice_start_time = start_time + timedelta(seconds=i * time_per_slice)
            
            # Đợi đến thời gian bắt đầu của phần hiện tại
            wait_seconds = (slice_start_time - datetime.now()).total_seconds()
            if wait_seconds > 0:
                time.sleep(wait_seconds)
                
            # Nếu là phần cuối cùng, sử dụng toàn bộ số lượng còn lại
            if i == num_slices - 1:
                current_slice_qty = remaining_quantity
            else:
                current_slice_qty = slice_quantity
                
            # Lấy giá thị trường hiện tại nếu cần
            current_price = None
            limit_price = None  # Khởi tạo limit_price trước khi sử dụng
            
            if order_type == 'LIMIT':
                try:
                    # Lấy giá thị trường hiện tại
                    ticker = self.api_client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                    
                    # Điều chỉnh giá theo offset
                    if side == 'BUY':
                        # Nếu mua, đặt giá cao hơn một chút để đảm bảo thực thi
                        limit_price = current_price * (1 + price_offset_pct / 100)
                    else:
                        # Nếu bán, đặt giá thấp hơn một chút để đảm bảo thực thi
                        limit_price = current_price * (1 - price_offset_pct / 100)
                except Exception as e:
                    logger.error(f"Lỗi khi lấy giá hiện tại: {e}")
                    limit_price = None
                    
            # Thực thi lệnh
            order_result = self.execute_order(
                symbol=symbol,
                side=side,
                quantity=current_slice_qty,
                order_type=order_type,
                price=limit_price if order_type == 'LIMIT' else None,
                **kwargs
            )
            
            results.append(order_result)
            
            # Cập nhật số lượng còn lại
            if 'executedQty' in order_result:
                executed_qty = float(order_result['executedQty'])
                remaining_quantity -= executed_qty
                
        # Tổng hợp kết quả
        summary = {
            'symbol': symbol,
            'side': side,
            'total_quantity': total_quantity,
            'executed_quantity': total_quantity - remaining_quantity,
            'num_slices': num_slices,
            'duration_minutes': duration_minutes,
            'orders': results,
            'average_price': self.calculate_average_fill_price(results)
        }
        
        return summary
        
    def calculate_average_fill_price(self, order_response):
        """
        Tính giá trung bình thực hiện cho nhiều lệnh
        
        Args:
            order_response (List[Dict]): Danh sách các lệnh
            
        Returns:
            float: Giá trung bình
        """
        if not order_response:
            return 0.0
            
        # Xử lý trường hợp nếu order_response là một object đơn lẻ
        if isinstance(order_response, dict):
            # Nếu order_response là một dict không phải list, chuyển nó thành list để xử lý
            orders = [order_response]
        else:
            # Nếu đã là list thì giữ nguyên
            orders = order_response
        
        total_qty = 0.0
        total_cost = 0.0
        
        for order in orders:
            if 'fills' in order and order['fills']:
                for fill in order['fills']:
                    qty = float(fill['qty'])
                    price = float(fill['price'])
                    total_qty += qty
                    total_cost += qty * price
            
            elif 'executedQty' in order and 'price' in order and float(order['executedQty']) > 0:
                qty = float(order['executedQty'])
                price = float(order['price'])
                total_qty += qty
                total_cost += qty * price
                
        if total_qty == 0:
            return 0.0
            
        return total_cost / total_qty
        
class ScaledOrderExecutor(BaseOrderExecutor):
    """
    Lớp thực thi lệnh theo tỷ lệ (Scaled Order)
    
    Đặt nhiều lệnh ở các mức giá khác nhau theo một phạm vi
    """
    
    def __init__(self, api_client):
        """
        Khởi tạo Scaled Order executor
        
        Args:
            api_client (object): Đối tượng API client
        """
        super().__init__(api_client)
        self.name = "Scaled Order Executor"
        
    def execute_scaled_order(self, symbol, side, total_quantity, price_low, price_high, 
                           num_orders, distribution='linear', **kwargs):
        """
        Thực thi lệnh theo tỷ lệ (đặt nhiều lệnh ở các mức giá khác nhau)
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            side (str): Bên giao dịch (BUY/SELL)
            total_quantity (float): Tổng số lượng
            price_low (float): Mức giá thấp nhất
            price_high (float): Mức giá cao nhất
            num_orders (int): Số lượng lệnh
            distribution (str): Phân phối số lượng ('linear', 'geometric', 'uniform')
            **kwargs: Tham số bổ sung
            
        Returns:
            Dict: Kết quả thực thi
        """
        if total_quantity <= 0 or num_orders <= 0 or price_low <= 0 or price_high <= 0:
            logger.error(f"Tham số không hợp lệ")
            return {"error": "Tham số không hợp lệ"}
            
        if price_low >= price_high:
            logger.error(f"Mức giá thấp phải nhỏ hơn mức giá cao")
            return {"error": "Mức giá thấp phải nhỏ hơn mức giá cao"}
            
        # Tính toán phân phối giá và số lượng
        prices = []
        quantities = []
        
        if distribution == 'uniform':
            # Phân phối đều
            for i in range(num_orders):
                prices.append(price_low + (price_high - price_low) * i / (num_orders - 1))
                quantities.append(total_quantity / num_orders)
                
        elif distribution == 'geometric':
            # Phân phối hình học (tỷ lệ số lượng giảm/tăng dần)
            ratios = []
            sum_ratio = 0
            
            # Tạo tỷ lệ hình học
            for i in range(num_orders):
                if side == 'BUY':
                    # Nếu mua, đặt nhiều ở giá thấp hơn
                    ratio = 1 + (num_orders - i - 1) * 0.2
                else:
                    # Nếu bán, đặt nhiều ở giá cao hơn
                    ratio = 1 + i * 0.2
                    
                ratios.append(ratio)
                sum_ratio += ratio
                
            # Tính giá và số lượng
            for i in range(num_orders):
                prices.append(price_low + (price_high - price_low) * i / (num_orders - 1))
                quantities.append(total_quantity * ratios[i] / sum_ratio)
                
        else:  # linear
            # Phân phối tuyến tính (số lượng thay đổi theo giá)
            if side == 'BUY':
                # Nếu mua, đặt nhiều ở giá thấp hơn
                for i in range(num_orders):
                    prices.append(price_low + (price_high - price_low) * i / (num_orders - 1))
                    weight = 1 + (num_orders - i - 1) * 0.5
                    quantities.append(weight)
            else:
                # Nếu bán, đặt nhiều ở giá cao hơn
                for i in range(num_orders):
                    prices.append(price_low + (price_high - price_low) * i / (num_orders - 1))
                    weight = 1 + i * 0.5
                    quantities.append(weight)
                    
            # Chuẩn hóa số lượng
            total_weight = sum(quantities)
            for i in range(num_orders):
                quantities[i] = total_quantity * quantities[i] / total_weight
                
        # Thực thi các lệnh
        results = []
        total_executed = 0.0
        
        for i in range(num_orders):
            order_result = self.execute_order(
                symbol=symbol,
                side=side,
                quantity=quantities[i],
                order_type='LIMIT',
                price=prices[i],
                **kwargs
            )
            
            results.append({
                'price': prices[i],
                'quantity': quantities[i],
                'order': order_result
            })
            
            if 'executedQty' in order_result:
                total_executed += float(order_result['executedQty'])
                
        # Tổng hợp kết quả
        summary = {
            'symbol': symbol,
            'side': side,
            'total_quantity': total_quantity,
            'executed_quantity': total_executed,
            'price_low': price_low,
            'price_high': price_high,
            'num_orders': num_orders,
            'distribution': distribution,
            'orders': results,
            'average_price': self.calculate_average_fill_price(results)
        }
        
        return summary
        
    def calculate_average_fill_price(self, order_response):
        """
        Tính giá trung bình thực hiện cho nhiều lệnh
        
        Args:
            order_response (List[Dict]): Danh sách các lệnh
            
        Returns:
            float: Giá trung bình
        """
        if not order_response or 'orders' not in order_response:
            # Kiểm tra nếu order_response là một Dict có thuộc tính 'orders'
            if isinstance(order_response, dict) and 'orders' in order_response:
                orders = order_response['orders']
            # Kiểm tra nếu order_response là một List
            elif isinstance(order_response, list):
                orders = order_response
            else:
                return 0.0
        else:
            orders = order_response['orders']
            
        total_qty = 0.0
        total_cost = 0.0
        
        for order_item in orders:
            # Nếu order_item là một Dict có 'order'
            if isinstance(order_item, dict) and 'order' in order_item:
                order = order_item['order']
            else:
                order = order_item
                
            if 'fills' in order and order['fills']:
                for fill in order['fills']:
                    qty = float(fill['qty'])
                    price = float(fill['price'])
                    total_qty += qty
                    total_cost += qty * price
            
            elif 'executedQty' in order and 'price' in order and float(order['executedQty']) > 0:
                qty = float(order['executedQty'])
                price = float(order['price'])
                total_qty += qty
                total_cost += qty * price
                
        if total_qty == 0:
            return 0.0
            
        return total_cost / total_qty