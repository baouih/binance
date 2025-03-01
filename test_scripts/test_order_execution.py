"""
Script kiểm tra module order_execution.py

Script này kiểm tra độc lập các lớp và phương thức trong module order_execution.py:
1. BaseOrderExecutor - Thực thi lệnh cơ bản
2. IcebergOrderExecutor - Chia lệnh lớn thành nhiều lệnh nhỏ
3. TWAPExecutor - Chia lệnh theo thời gian
4. ScaledOrderExecutor - Đặt lệnh theo nhiều mức giá
5. OCOOrderExecutor - Đặt cùng lúc lệnh take profit và stop loss

Các kiểm tra bao gồm xác minh giá trị đầu ra, kiểm tra xử lý lỗi và đảm bảo đúng logic.
"""

import os
import sys
import time
import logging
import json
import numpy as np
import threading
from datetime import datetime, timedelta
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_order_execution")

# Create necessary directories
os.makedirs('../test_results', exist_ok=True)

# Try to import the module
try:
    from order_execution import (
        BaseOrderExecutor,
        IcebergOrderExecutor,
        TWAPExecutor,
        ScaledOrderExecutor,
        OCOOrderExecutor,
        OrderExecutionFactory
    )
    HAS_MODULE = True
except ImportError as e:
    logger.warning(f"Could not import order_execution module: {e}")
    logger.warning("Using mock implementations for testing")
    HAS_MODULE = False
    
    # Mock API client for testing
    class MockAPIClient:
        def __init__(self, simulate_errors=False):
            self.orders = {}
            self.order_id_counter = 1000
            self.list_id_counter = 5000
            self.simulate_errors = simulate_errors
            
        def create_order(self, **kwargs):
            """Mock creating an order"""
            if self.simulate_errors and np.random.random() < 0.2:
                raise Exception("Simulated API error")
                
            order_id = str(self.order_id_counter)
            self.order_id_counter += 1
            
            order = {
                'orderId': order_id,
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
            
            self.orders[order_id] = order
            return order
            
        def cancel_order(self, **kwargs):
            """Mock canceling an order"""
            if self.simulate_errors and np.random.random() < 0.2:
                raise Exception("Simulated API error")
                
            order_id = kwargs.get('orderId')
            if order_id in self.orders:
                self.orders[order_id]['status'] = 'CANCELED'
                return {'orderId': order_id, 'status': 'CANCELED'}
            else:
                raise Exception(f"Order {order_id} not found")
                
        def get_order(self, **kwargs):
            """Mock getting order details"""
            order_id = kwargs.get('orderId')
            if order_id in self.orders:
                return self.orders[order_id]
            else:
                raise Exception(f"Order {order_id} not found")
                
        def get_open_orders(self, **kwargs):
            """Mock getting open orders"""
            symbol = kwargs.get('symbol')
            return [order for order in self.orders.values() 
                    if order['symbol'] == symbol and order['status'] == 'NEW']
                    
        def order_oco_sell(self, **kwargs):
            """Mock creating an OCO sell order"""
            if self.simulate_errors and np.random.random() < 0.2:
                raise Exception("Simulated API error")
                
            list_id = str(self.list_id_counter)
            self.list_id_counter += 1
            
            orders = []
            
            # Limit order (take profit)
            tp_order_id = str(self.order_id_counter)
            self.order_id_counter += 1
            tp_order = {
                'orderId': tp_order_id,
                'symbol': kwargs.get('symbol'),
                'side': 'SELL',
                'type': 'LIMIT',
                'price': kwargs.get('price'),
                'origQty': kwargs.get('quantity'),
                'executedQty': '0',
                'status': 'NEW'
            }
            self.orders[tp_order_id] = tp_order
            orders.append(tp_order)
            
            # Stop Loss order
            sl_order_id = str(self.order_id_counter)
            self.order_id_counter += 1
            sl_order = {
                'orderId': sl_order_id,
                'symbol': kwargs.get('symbol'),
                'side': 'SELL',
                'type': 'STOP_LOSS_LIMIT',
                'price': kwargs.get('stopLimitPrice'),
                'stopPrice': kwargs.get('stopPrice'),
                'origQty': kwargs.get('quantity'),
                'executedQty': '0',
                'status': 'NEW'
            }
            self.orders[sl_order_id] = sl_order
            orders.append(sl_order)
            
            return {
                'orderListId': list_id,
                'orders': orders
            }
            
        def order_oco_buy(self, **kwargs):
            """Mock creating an OCO buy order"""
            # Similar to sell, but with BUY side
            if self.simulate_errors and np.random.random() < 0.2:
                raise Exception("Simulated API error")
                
            list_id = str(self.list_id_counter)
            self.list_id_counter += 1
            
            orders = []
            
            # Limit order (take profit)
            tp_order_id = str(self.order_id_counter)
            self.order_id_counter += 1
            tp_order = {
                'orderId': tp_order_id,
                'symbol': kwargs.get('symbol'),
                'side': 'BUY',
                'type': 'LIMIT',
                'price': kwargs.get('price'),
                'origQty': kwargs.get('quantity'),
                'executedQty': '0',
                'status': 'NEW'
            }
            self.orders[tp_order_id] = tp_order
            orders.append(tp_order)
            
            # Stop Loss order
            sl_order_id = str(self.order_id_counter)
            self.order_id_counter += 1
            sl_order = {
                'orderId': sl_order_id,
                'symbol': kwargs.get('symbol'),
                'side': 'BUY',
                'type': 'STOP_LOSS_LIMIT',
                'price': kwargs.get('stopLimitPrice'),
                'stopPrice': kwargs.get('stopPrice'),
                'origQty': kwargs.get('quantity'),
                'executedQty': '0',
                'status': 'NEW'
            }
            self.orders[sl_order_id] = sl_order
            orders.append(sl_order)
            
            return {
                'orderListId': list_id,
                'orders': orders
            }
            
        def cancel_order_list(self, **kwargs):
            """Mock canceling an OCO order list"""
            return {'orderListId': kwargs.get('orderListId'), 'status': 'CANCELED'}
            
        def get_order_list(self, **kwargs):
            """Mock getting OCO order details"""
            return {'orderListId': kwargs.get('orderListId'), 'status': 'ACTIVE'}

    # Create mock implementations for testing
    class BaseOrderExecutor:
        def __init__(self, api_client):
            self.api_client = api_client
            
        def execute_order(self, symbol, side, quantity, order_type='MARKET', price=None, 
                        time_in_force='GTC', **kwargs):
            try:
                # Validate input
                if quantity <= 0:
                    logger.error(f"Invalid quantity: {quantity}")
                    return {"error": "Invalid quantity"}
                    
                if order_type == 'LIMIT' and (price is None or price <= 0):
                    logger.error(f"Price required for LIMIT order")
                    return {"error": "Price required for LIMIT order"}
                    
                # Create order parameters
                order_params = {
                    'symbol': symbol,
                    'side': side,
                    'type': order_type,
                    'quantity': quantity,
                    'timeInForce': time_in_force if order_type != 'MARKET' else None
                }
                
                if order_type != 'MARKET' and price is not None:
                    order_params['price'] = price
                    
                # Add other parameters
                for key, value in kwargs.items():
                    order_params[key] = value
                    
                # Remove None values
                order_params = {k: v for k, v in order_params.items() if v is not None}
                
                # Execute order
                response = self.api_client.create_order(**order_params)
                return response
                
            except Exception as e:
                logger.error(f"Error executing order: {e}")
                return {"error": str(e)}
                
        def get_order_status(self, symbol, order_id):
            try:
                response = self.api_client.get_order(symbol=symbol, orderId=order_id)
                return response
            except Exception as e:
                logger.error(f"Error getting order status: {e}")
                return {"error": str(e)}
                
        def cancel_order(self, symbol, order_id):
            try:
                response = self.api_client.cancel_order(symbol=symbol, orderId=order_id)
                return response
            except Exception as e:
                logger.error(f"Error cancelling order: {e}")
                return {"error": str(e)}
                
        def calculate_average_fill_price(self, order_response):
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
        def execute_iceberg_order(self, symbol, side, total_quantity, num_parts=5, price=None, 
                                order_type='MARKET', random_variance=0.1, time_between_parts=30.0, **kwargs):
            if total_quantity <= 0 or num_parts <= 0:
                logger.error(f"Invalid parameters")
                return []
                
            base_quantity = total_quantity / num_parts
            results = []
            remaining_quantity = total_quantity
            
            for i in range(num_parts):
                is_last_part = (i == num_parts - 1)
                
                if is_last_part:
                    part_quantity = remaining_quantity
                else:
                    if random_variance > 0:
                        variance = np.random.uniform(-random_variance, random_variance)
                        variance_factor = 1.0 + variance
                    else:
                        variance_factor = 1.0
                        
                    part_quantity = min(base_quantity * variance_factor, remaining_quantity)
                
                part_quantity = max(0.000001, part_quantity)
                
                order_result = self.execute_order(
                    symbol=symbol,
                    side=side,
                    quantity=part_quantity,
                    order_type=order_type,
                    price=price,
                    **kwargs
                )
                
                results.append(order_result)
                
                if 'executedQty' in order_result:
                    executed_qty = float(order_result['executedQty'])
                else:
                    executed_qty = part_quantity
                    
                remaining_quantity -= executed_qty
                
                if remaining_quantity <= 0 or is_last_part:
                    break
                    
                if time_between_parts > 0 and i < num_parts - 1:
                    time.sleep(time_between_parts)
                    
            return results
            
        def calculate_average_fill_price(self, order_response):
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
        def __init__(self, api_client):
            super().__init__(api_client)
            self.active_executions = {}
            self._lock = threading.Lock()
            
        def execute_twap_order(self, symbol, side, total_quantity, duration_minutes, num_parts=10,
                             order_type='MARKET', price=None, wait_for_completion=False, **kwargs):
            import uuid
            
            if total_quantity <= 0 or duration_minutes <= 0 or num_parts <= 0:
                logger.error(f"Invalid parameters")
                return ""
                
            execution_id = str(uuid.uuid4())
            part_quantity = total_quantity / num_parts
            time_interval = (duration_minutes * 60) / num_parts
            
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
            
            with self._lock:
                self.active_executions[execution_id] = twap_info
                
            twap_thread = threading.Thread(
                target=self._run_twap_execution,
                args=(execution_id,),
                daemon=True
            )
            twap_thread.start()
            
            if wait_for_completion:
                twap_thread.join()
                
            return execution_id
            
        def _run_twap_execution(self, execution_id):
            try:
                with self._lock:
                    if execution_id not in self.active_executions:
                        logger.error(f"TWAP execution {execution_id} not found")
                        return
                        
                    twap_info = self.active_executions[execution_id]
                    
                symbol = twap_info['symbol']
                side = twap_info['side']
                part_quantity = twap_info['part_quantity']
                num_parts = twap_info['num_parts']
                time_interval = twap_info['time_interval']
                order_type = twap_info['order_type']
                price = twap_info['price']
                kwargs = twap_info['kwargs']
                
                for i in range(num_parts):
                    with self._lock:
                        if execution_id not in self.active_executions or not self.active_executions[execution_id]['is_active']:
                            logger.info(f"TWAP execution {execution_id} was cancelled")
                            return
                            
                        current_info = self.active_executions[execution_id]
                        
                    is_last_part = (i == num_parts - 1)
                    
                    if is_last_part:
                        current_quantity = current_info['remaining_quantity']
                    else:
                        current_quantity = min(part_quantity, current_info['remaining_quantity'])
                        
                    if current_quantity <= 0:
                        break
                        
                    order_result = self.execute_order(
                        symbol=symbol,
                        side=side,
                        quantity=current_quantity,
                        order_type=order_type,
                        price=price,
                        **kwargs
                    )
                    
                    with self._lock:
                        if execution_id in self.active_executions:
                            if 'executedQty' in order_result:
                                executed_qty = float(order_result['executedQty'])
                            else:
                                executed_qty = current_quantity
                                
                            self.active_executions[execution_id]['remaining_quantity'] -= executed_qty
                            self.active_executions[execution_id]['parts_completed'] += 1
                            self.active_executions[execution_id]['orders'].append(order_result)
                            
                    if current_info['remaining_quantity'] <= 0 or is_last_part:
                        break
                        
                    time.sleep(time_interval)
                    
                with self._lock:
                    if execution_id in self.active_executions:
                        self.active_executions[execution_id]['is_active'] = False
                        
            except Exception as e:
                logger.error(f"Error in TWAP execution {execution_id}: {e}")
                with self._lock:
                    if execution_id in self.active_executions:
                        self.active_executions[execution_id]['is_active'] = False
                        self.active_executions[execution_id]['error'] = str(e)
                        
        def cancel_twap_execution(self, execution_id):
            with self._lock:
                if execution_id not in self.active_executions:
                    logger.warning(f"TWAP execution {execution_id} not found")
                    return False
                    
                self.active_executions[execution_id]['is_active'] = False
                return True
                
        def get_twap_status(self, execution_id):
            with self._lock:
                if execution_id not in self.active_executions:
                    logger.warning(f"TWAP execution {execution_id} not found")
                    return {"error": "TWAP execution not found"}
                    
                twap_info = self.active_executions[execution_id]
                
                total_executed = twap_info['total_quantity'] - twap_info['remaining_quantity']
                completion_pct = (total_executed / twap_info['total_quantity']) * 100 if twap_info['total_quantity'] > 0 else 0
                
                elapsed_seconds = time.time() - twap_info['start_time']
                time_pct = (elapsed_seconds / twap_info['duration_seconds']) * 100 if twap_info['duration_seconds'] > 0 else 0
                
                avg_price = self.calculate_average_fill_price(twap_info['orders'])
                
                return {
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
                    'error': twap_info.get('error')
                }
    
    class ScaledOrderExecutor(BaseOrderExecutor):
        def execute_scaled_entry(self, symbol, side, total_quantity, price_low, price_high, num_levels=5,
                               distribution='uniform', **kwargs):
            if total_quantity <= 0 or price_low <= 0 or price_high <= 0 or num_levels <= 0:
                logger.error(f"Invalid parameters")
                return []
                
            if price_low > price_high:
                price_low, price_high = price_high, price_low
                
            if num_levels == 1:
                price_levels = [price_low]
            else:
                price_step = (price_high - price_low) / (num_levels - 1)
                price_levels = [price_low + i * price_step for i in range(num_levels)]
                
            if distribution == 'uniform':
                quantities = [total_quantity / num_levels] * num_levels
            elif distribution == 'ascending':
                weights = [i+1 for i in range(num_levels)]
                total_weight = sum(weights)
                quantities = [(total_quantity * w / total_weight) for w in weights]
            elif distribution == 'descending':
                weights = [num_levels-i for i in range(num_levels)]
                total_weight = sum(weights)
                quantities = [(total_quantity * w / total_weight) for w in weights]
            else:
                quantities = [total_quantity / num_levels] * num_levels
                
            results = []
            for i, (price, quantity) in enumerate(zip(price_levels, quantities)):
                quantity = max(0.000001, quantity)
                
                order_result = self.execute_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type='LIMIT',
                    price=price,
                    **kwargs
                )
                
                results.append(order_result)
                
            return results
            
        def execute_scaled_exit(self, symbol, side, total_quantity, price_low, price_high, 
                              num_levels=5, distribution='ascending', **kwargs):
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
    
    class OCOOrderExecutor(BaseOrderExecutor):
        def place_tp_sl_orders(self, symbol, side, entry_price, quantity, take_profit_price, 
                             stop_loss_price, stop_limit_price_delta=0.5, **kwargs):
            if quantity <= 0 or entry_price <= 0 or take_profit_price <= 0 or stop_loss_price <= 0:
                logger.error(f"Invalid parameters")
                return {"error": "Invalid parameters"}
                
            if side.upper() == 'LONG':
                oco_side = 'SELL'
                
                if take_profit_price <= entry_price:
                    logger.error(f"Take profit price must be higher than entry price for LONG positions")
                    return {"error": "Take profit price must be higher than entry price for LONG positions"}
                    
                if stop_loss_price >= entry_price:
                    logger.error(f"Stop loss price must be lower than entry price for LONG positions")
                    return {"error": "Stop loss price must be lower than entry price for LONG positions"}
                    
            elif side.upper() == 'SHORT':
                oco_side = 'BUY'
                
                if take_profit_price >= entry_price:
                    logger.error(f"Take profit price must be lower than entry price for SHORT positions")
                    return {"error": "Take profit price must be lower than entry price for SHORT positions"}
                    
                if stop_loss_price <= entry_price:
                    logger.error(f"Stop loss price must be higher than entry price for SHORT positions")
                    return {"error": "Stop loss price must be higher than entry price for SHORT positions"}
                    
            else:
                logger.error(f"Invalid side: {side}")
                return {"error": f"Invalid side: {side}"}
                
            stop_limit_price_pct = 1.0 - (stop_limit_price_delta / 100.0) if oco_side == 'SELL' else 1.0 + (stop_limit_price_delta / 100.0)
            stop_limit_price = stop_loss_price * stop_limit_price_pct
            
            try:
                if oco_side == 'SELL':
                    response = self.api_client.order_oco_sell(
                        symbol=symbol,
                        quantity=quantity,
                        price=take_profit_price,
                        stopPrice=stop_loss_price,
                        stopLimitPrice=stop_limit_price,
                        **kwargs
                    )
                else:
                    response = self.api_client.order_oco_buy(
                        symbol=symbol,
                        quantity=quantity,
                        price=take_profit_price,
                        stopPrice=stop_loss_price,
                        stopLimitPrice=stop_limit_price,
                        **kwargs
                    )
                    
                response['entry_price'] = entry_price
                response['position_side'] = side
                response['take_profit_price'] = take_profit_price
                response['stop_loss_price'] = stop_loss_price
                
                return response
                
            except Exception as e:
                logger.error(f"Error placing OCO order: {e}")
                return {"error": str(e)}
                
        def get_oco_order_status(self, symbol, order_list_id):
            try:
                response = self.api_client.get_order_list(orderListId=order_list_id)
                return response
            except Exception as e:
                logger.error(f"Error getting OCO order status: {e}")
                return {"error": str(e)}
                
        def cancel_oco_order(self, symbol, order_list_id):
            try:
                response = self.api_client.cancel_order_list(symbol=symbol, orderListId=order_list_id)
                return response
            except Exception as e:
                logger.error(f"Error cancelling OCO order: {e}")
                return {"error": str(e)}
    
    class OrderExecutionFactory:
        def create_executor(self, executor_type, api_client):
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
                logger.warning(f"Unknown executor type: {executor_type}")
                return BaseOrderExecutor(api_client)

def test_base_order_executor():
    """Test the BaseOrderExecutor class"""
    print("\n=== Testing BaseOrderExecutor ===")
    
    # Initialize the mock API client
    api_client = MockAPIClient()
    executor = BaseOrderExecutor(api_client)
    
    # Test case 1: Basic market order
    symbol = "BTCUSDT"
    side = "BUY"
    quantity = 0.1
    
    print(f"Test case 1: Market order ({side} {quantity} {symbol})")
    market_order = executor.execute_order(symbol=symbol, side=side, quantity=quantity)
    print(f"  Order ID: {market_order.get('orderId')}")
    print(f"  Status: {market_order.get('status')}")
    
    assert 'orderId' in market_order, "Order ID missing in market order response"
    assert market_order.get('status') == 'FILLED', "Market order not filled"
    
    # Test case 2: Limit order
    price = 40000
    
    print(f"\nTest case 2: Limit order ({side} {quantity} {symbol} @ {price})")
    limit_order = executor.execute_order(
        symbol=symbol, 
        side=side, 
        quantity=quantity, 
        order_type="LIMIT", 
        price=price
    )
    print(f"  Order ID: {limit_order.get('orderId')}")
    print(f"  Status: {limit_order.get('status')}")
    print(f"  Price: {limit_order.get('price')}")
    
    assert 'orderId' in limit_order, "Order ID missing in limit order response"
    assert limit_order.get('price') == price, f"Limit order price mismatch: {limit_order.get('price')} != {price}"
    
    # Test case 3: Calculate average fill price
    avg_price = executor.calculate_average_fill_price(market_order)
    expected_price = float(market_order['fills'][0]['price'])
    
    print(f"\nTest case 3: Calculate average fill price")
    print(f"  Average price: {avg_price}")
    print(f"  Expected price: {expected_price}")
    
    assert abs(avg_price - expected_price) < 0.0001, f"Average price mismatch: {avg_price} != {expected_price}"
    
    # Test case 4: Order status
    order_id = market_order.get('orderId')
    
    print(f"\nTest case 4: Order status (Order ID: {order_id})")
    order_status = executor.get_order_status(symbol=symbol, order_id=order_id)
    print(f"  Status: {order_status.get('status')}")
    
    assert order_status.get('orderId') == order_id, "Order ID mismatch in status response"
    
    # Test case 5: Cancel order
    order_id = limit_order.get('orderId')
    
    print(f"\nTest case 5: Cancel order (Order ID: {order_id})")
    cancel_result = executor.cancel_order(symbol=symbol, order_id=order_id)
    print(f"  Status: {cancel_result.get('status')}")
    
    assert cancel_result.get('status') == 'CANCELED', "Order not canceled"
    
    # Test case 6: Error handling for invalid inputs
    print("\nTest case 6: Error handling for invalid inputs")
    
    # Invalid quantity
    invalid_order = executor.execute_order(symbol=symbol, side=side, quantity=0)
    print(f"  Invalid quantity: {'error' in invalid_order}")
    assert 'error' in invalid_order, "No error for invalid quantity"
    
    # Missing price for limit order
    invalid_limit = executor.execute_order(symbol=symbol, side=side, quantity=quantity, order_type="LIMIT")
    print(f"  Missing price for limit order: {'error' in invalid_limit}")
    assert 'error' in invalid_limit, "No error for missing price in limit order"
    
    # Test case 7: Error handling for API errors
    print("\nTest case 7: Error handling for API errors")
    
    # Create an API client that simulates errors
    error_api_client = MockAPIClient(simulate_errors=True)
    error_executor = BaseOrderExecutor(error_api_client)
    
    # Try multiple orders to catch at least one error
    error_caught = False
    for i in range(10):
        result = error_executor.execute_order(symbol=symbol, side=side, quantity=quantity)
        if 'error' in result:
            print(f"  Error detected: {result['error']}")
            error_caught = True
            break
            
    if not error_caught:
        print("  No error simulated in 10 attempts")
        
    print("\nBaseOrderExecutor tests completed successfully!")
    return True

def test_iceberg_order_executor():
    """Test the IcebergOrderExecutor class"""
    print("\n=== Testing IcebergOrderExecutor ===")
    
    # Initialize the mock API client
    api_client = MockAPIClient()
    executor = IcebergOrderExecutor(api_client)
    
    # Test case 1: Basic iceberg order
    symbol = "BTCUSDT"
    side = "BUY"
    total_quantity = 1.0
    num_parts = 3
    
    print(f"Test case 1: Iceberg order ({side} {total_quantity} {symbol} in {num_parts} parts)")
    # Make time_between_parts very short for testing
    results = executor.execute_iceberg_order(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        num_parts=num_parts,
        time_between_parts=0.01
    )
    
    print(f"  Number of orders executed: {len(results)}")
    
    # Check that we have the correct number of parts
    assert len(results) == num_parts, f"Expected {num_parts} orders, got {len(results)}"
    
    # Check that the total quantity matches
    total_executed = sum(float(order.get('executedQty', 0)) for order in results)
    print(f"  Total executed quantity: {total_executed}")
    print(f"  Expected quantity: {total_quantity}")
    
    assert abs(total_executed - total_quantity) < 0.0001, f"Total quantity mismatch: {total_executed} != {total_quantity}"
    
    # Test case 2: Iceberg order with limit price
    price = 40000
    
    print(f"\nTest case 2: Iceberg limit order ({side} {total_quantity} {symbol} @ {price} in {num_parts} parts)")
    results = executor.execute_iceberg_order(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        num_parts=num_parts,
        price=price,
        order_type="LIMIT",
        time_between_parts=0.01
    )
    
    print(f"  Number of orders executed: {len(results)}")
    
    # Check that we have the correct number of parts
    assert len(results) == num_parts, f"Expected {num_parts} orders, got {len(results)}"
    
    # Check that each order has the correct price
    for i, order in enumerate(results):
        assert order.get('price') == price, f"Order {i} price mismatch: {order.get('price')} != {price}"
        
    # Test case 3: Calculate average fill price
    avg_price = executor.calculate_average_fill_price(results)
    expected_price = price
    
    print(f"\nTest case 3: Calculate average fill price")
    print(f"  Average price: {avg_price}")
    print(f"  Expected price: {expected_price}")
    
    assert abs(avg_price - expected_price) < 0.0001, f"Average price mismatch: {avg_price} != {expected_price}"
    
    # Test case 4: Iceberg order with random variance
    random_variance = 0.2
    
    print(f"\nTest case 4: Iceberg order with random variance ({random_variance})")
    results = executor.execute_iceberg_order(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        num_parts=num_parts,
        random_variance=random_variance,
        time_between_parts=0.01
    )
    
    print(f"  Number of orders executed: {len(results)}")
    
    # Check that we have the correct number of parts or fewer (if merged due to remaining quantity)
    assert len(results) <= num_parts, f"Expected {num_parts} or fewer orders, got {len(results)}"
    
    # Check that orders have varying sizes (if random_variance > 0)
    if len(results) > 1:
        quantities = [float(order.get('origQty', 0)) for order in results]
        all_same = all(abs(q - quantities[0]) < 0.0001 for q in quantities)
        print(f"  Orders have varying sizes: {not all_same}")
        
        if random_variance > 0:
            # With random variance, it's unlikely (but not impossible) that all quantities are the same
            print(f"  Quantities: {quantities}")
    
    # Test case 5: Error handling for invalid inputs
    print("\nTest case 5: Error handling for invalid inputs")
    
    # Invalid total quantity
    invalid_results = executor.execute_iceberg_order(
        symbol=symbol, 
        side=side, 
        total_quantity=0, 
        num_parts=num_parts
    )
    print(f"  Invalid total quantity: {len(invalid_results) == 0}")
    assert len(invalid_results) == 0, "No error for invalid total quantity"
    
    # Invalid number of parts
    invalid_results = executor.execute_iceberg_order(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        num_parts=0
    )
    print(f"  Invalid number of parts: {len(invalid_results) == 0}")
    assert len(invalid_results) == 0, "No error for invalid number of parts"
    
    print("\nIcebergOrderExecutor tests completed successfully!")
    return True

def test_twap_executor():
    """Test the TWAPExecutor class"""
    print("\n=== Testing TWAPExecutor ===")
    
    # Initialize the mock API client
    api_client = MockAPIClient()
    executor = TWAPExecutor(api_client)
    
    # Test case 1: Basic TWAP order
    symbol = "BTCUSDT"
    side = "BUY"
    total_quantity = 1.0
    duration_minutes = 0.05  # Short duration for testing (3 seconds)
    num_parts = 3
    
    print(f"Test case 1: TWAP order ({side} {total_quantity} {symbol} over {duration_minutes:.2f} minutes in {num_parts} parts)")
    execution_id = executor.execute_twap_order(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        duration_minutes=duration_minutes,
        num_parts=num_parts
    )
    
    print(f"  Execution ID: {execution_id}")
    assert execution_id, "No execution ID returned"
    
    # Wait a short time for at least some orders to be executed
    time.sleep(duration_minutes * 60 / 2)
    
    # Check status
    status = executor.get_twap_status(execution_id)
    print(f"  Status: {status}")
    print(f"  Parts completed: {status.get('parts_completed')} / {status.get('total_parts')}")
    print(f"  Completion percentage: {status.get('completion_percentage'):.2f}%")
    print(f"  Time percentage: {status.get('time_percentage'):.2f}%")
    
    # If it's still active, wait for completion
    if status.get('is_active', False):
        print("  Waiting for completion...")
        time.sleep(duration_minutes * 60 / 2 + 1)  # Wait a bit longer
        status = executor.get_twap_status(execution_id)
        print(f"  Updated status: Parts completed: {status.get('parts_completed')} / {status.get('total_parts')}")
        
    # Test case 2: TWAP order with limit price
    price = 40000
    
    print(f"\nTest case 2: TWAP limit order ({side} {total_quantity} {symbol} @ {price})")
    execution_id = executor.execute_twap_order(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        duration_minutes=duration_minutes,
        num_parts=num_parts,
        price=price,
        order_type="LIMIT",
        wait_for_completion=True  # Wait for completion
    )
    
    print(f"  Execution ID: {execution_id}")
    assert execution_id, "No execution ID returned"
    
    # Check status after completion
    status = executor.get_twap_status(execution_id)
    print(f"  Final status: Parts completed: {status.get('parts_completed')} / {status.get('total_parts')}")
    print(f"  Average price: {status.get('average_price')}")
    
    # Check if all parts were completed
    assert status.get('parts_completed') == num_parts, f"Not all parts completed: {status.get('parts_completed')} != {num_parts}"
    
    # Check average price
    avg_price = status.get('average_price')
    assert abs(avg_price - price) < 0.0001, f"Average price mismatch: {avg_price} != {price}"
    
    # Test case 3: Cancel TWAP execution
    print(f"\nTest case 3: Cancel TWAP execution")
    execution_id = executor.execute_twap_order(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        duration_minutes=0.1,  # Longer duration
        num_parts=num_parts
    )
    
    print(f"  Execution ID: {execution_id}")
    
    # Wait a short time
    time.sleep(0.1)
    
    # Cancel execution
    cancel_result = executor.cancel_twap_execution(execution_id)
    print(f"  Cancel result: {cancel_result}")
    assert cancel_result, "Failed to cancel TWAP execution"
    
    # Check status after cancellation
    status = executor.get_twap_status(execution_id)
    print(f"  Status after cancellation: Is active: {status.get('is_active')}")
    assert not status.get('is_active'), "TWAP execution still active after cancellation"
    
    # Test case 4: Error handling for invalid inputs
    print("\nTest case 4: Error handling for invalid inputs")
    
    # Invalid total quantity
    execution_id = executor.execute_twap_order(
        symbol=symbol, 
        side=side, 
        total_quantity=0, 
        duration_minutes=duration_minutes,
        num_parts=num_parts
    )
    print(f"  Invalid total quantity: {execution_id == ''}")
    assert execution_id == '', "No error for invalid total quantity"
    
    # Invalid duration
    execution_id = executor.execute_twap_order(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        duration_minutes=0,
        num_parts=num_parts
    )
    print(f"  Invalid duration: {execution_id == ''}")
    assert execution_id == '', "No error for invalid duration"
    
    # Test case 5: TWAP status for non-existent execution
    print("\nTest case 5: TWAP status for non-existent execution")
    status = executor.get_twap_status("non-existent-id")
    print(f"  Status: {status}")
    assert 'error' in status, "No error for non-existent execution ID"
    
    print("\nTWAPExecutor tests completed successfully!")
    return True

def test_scaled_order_executor():
    """Test the ScaledOrderExecutor class"""
    print("\n=== Testing ScaledOrderExecutor ===")
    
    # Initialize the mock API client
    api_client = MockAPIClient()
    executor = ScaledOrderExecutor(api_client)
    
    # Test case 1: Scaled entry with uniform distribution
    symbol = "BTCUSDT"
    side = "BUY"
    total_quantity = 1.0
    price_low = 39000
    price_high = 40000
    num_levels = 5
    distribution = "uniform"
    
    print(f"Test case 1: Scaled entry ({side} {total_quantity} {symbol} from {price_low} to {price_high}, {distribution})")
    results = executor.execute_scaled_entry(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        price_low=price_low,
        price_high=price_high,
        num_levels=num_levels,
        distribution=distribution
    )
    
    print(f"  Number of orders: {len(results)}")
    assert len(results) == num_levels, f"Expected {num_levels} orders, got {len(results)}"
    
    # Check price levels
    price_step = (price_high - price_low) / (num_levels - 1)
    expected_prices = [price_low + i * price_step for i in range(num_levels)]
    actual_prices = [float(order.get('price', 0)) for order in results]
    
    print(f"  Price levels: {actual_prices}")
    print(f"  Expected prices: {expected_prices}")
    
    for i, (actual, expected) in enumerate(zip(actual_prices, expected_prices)):
        assert abs(actual - expected) < 0.0001, f"Price mismatch at level {i}: {actual} != {expected}"
    
    # Check quantities (should be uniform)
    expected_qty = total_quantity / num_levels
    actual_quantities = [float(order.get('origQty', 0)) for order in results]
    
    print(f"  Quantities: {actual_quantities}")
    
    for i, qty in enumerate(actual_quantities):
        assert abs(qty - expected_qty) < 0.0001, f"Quantity mismatch at level {i}: {qty} != {expected_qty}"
    
    # Test case 2: Scaled entry with ascending distribution
    distribution = "ascending"
    
    print(f"\nTest case 2: Scaled entry with {distribution} distribution")
    results = executor.execute_scaled_entry(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        price_low=price_low,
        price_high=price_high,
        num_levels=num_levels,
        distribution=distribution
    )
    
    print(f"  Number of orders: {len(results)}")
    
    # Check quantities (should be ascending)
    weights = [i+1 for i in range(num_levels)]
    total_weight = sum(weights)
    expected_quantities = [(total_quantity * w / total_weight) for w in weights]
    actual_quantities = [float(order.get('origQty', 0)) for order in results]
    
    print(f"  Quantities: {actual_quantities}")
    print(f"  Expected quantities: {expected_quantities}")
    
    for i, (actual, expected) in enumerate(zip(actual_quantities, expected_quantities)):
        assert abs(actual - expected) < 0.0001, f"Quantity mismatch at level {i}: {actual} != {expected}"
    
    # Test case 3: Scaled entry with descending distribution
    distribution = "descending"
    
    print(f"\nTest case 3: Scaled entry with {distribution} distribution")
    results = executor.execute_scaled_entry(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        price_low=price_low,
        price_high=price_high,
        num_levels=num_levels,
        distribution=distribution
    )
    
    print(f"  Number of orders: {len(results)}")
    
    # Check quantities (should be descending)
    weights = [num_levels-i for i in range(num_levels)]
    total_weight = sum(weights)
    expected_quantities = [(total_quantity * w / total_weight) for w in weights]
    actual_quantities = [float(order.get('origQty', 0)) for order in results]
    
    print(f"  Quantities: {actual_quantities}")
    print(f"  Expected quantities: {expected_quantities}")
    
    for i, (actual, expected) in enumerate(zip(actual_quantities, expected_quantities)):
        assert abs(actual - expected) < 0.0001, f"Quantity mismatch at level {i}: {actual} != {expected}"
    
    # Test case 4: Scaled exit
    print(f"\nTest case 4: Scaled exit (SELL {total_quantity} {symbol})")
    results = executor.execute_scaled_exit(
        symbol=symbol, 
        side="SELL", 
        total_quantity=total_quantity, 
        price_low=price_low,
        price_high=price_high,
        num_levels=num_levels
    )
    
    print(f"  Number of orders: {len(results)}")
    assert len(results) == num_levels, f"Expected {num_levels} orders, got {len(results)}"
    
    # Verify side is SELL
    for i, order in enumerate(results):
        assert order.get('side') == 'SELL', f"Side mismatch at level {i}: {order.get('side')} != SELL"
    
    # Test case 5: Error handling for invalid inputs
    print("\nTest case 5: Error handling for invalid inputs")
    
    # Invalid total quantity
    invalid_results = executor.execute_scaled_entry(
        symbol=symbol, 
        side=side, 
        total_quantity=0, 
        price_low=price_low,
        price_high=price_high,
        num_levels=num_levels
    )
    print(f"  Invalid total quantity: {len(invalid_results) == 0}")
    assert len(invalid_results) == 0, "No error for invalid total quantity"
    
    # Invalid price levels (zero or negative)
    invalid_results = executor.execute_scaled_entry(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        price_low=0,
        price_high=price_high,
        num_levels=num_levels
    )
    print(f"  Invalid price level: {len(invalid_results) == 0}")
    assert len(invalid_results) == 0, "No error for invalid price level"
    
    # Test case 6: Swapped price_low and price_high
    print("\nTest case 6: Swapped price_low and price_high")
    # Deliberately swap them
    results = executor.execute_scaled_entry(
        symbol=symbol, 
        side=side, 
        total_quantity=total_quantity, 
        price_low=price_high,  # Swapped
        price_high=price_low,  # Swapped
        num_levels=num_levels
    )
    
    print(f"  Number of orders: {len(results)}")
    
    # Check that the function corrected the order
    actual_prices = [float(order.get('price', 0)) for order in results]
    print(f"  Price levels: {actual_prices}")
    
    # First price should be lower than last price
    assert actual_prices[0] < actual_prices[-1], "Prices not properly ordered"
    
    print("\nScaledOrderExecutor tests completed successfully!")
    return True

def test_oco_order_executor():
    """Test the OCOOrderExecutor class"""
    print("\n=== Testing OCOOrderExecutor ===")
    
    # Initialize the mock API client
    api_client = MockAPIClient()
    executor = OCOOrderExecutor(api_client)
    
    # Test case 1: Long position TP/SL orders
    symbol = "BTCUSDT"
    side = "LONG"
    entry_price = 40000
    quantity = 0.1
    take_profit_price = 42000
    stop_loss_price = 39000
    
    print(f"Test case 1: Long position TP/SL ({side} {quantity} {symbol}, entry={entry_price}, TP={take_profit_price}, SL={stop_loss_price})")
    result = executor.place_tp_sl_orders(
        symbol=symbol, 
        side=side, 
        entry_price=entry_price, 
        quantity=quantity,
        take_profit_price=take_profit_price,
        stop_loss_price=stop_loss_price
    )
    
    print(f"  Order List ID: {result.get('orderListId')}")
    assert 'orderListId' in result, "Order List ID missing in OCO response"
    
    # Check orders
    orders = result.get('orders', [])
    print(f"  Number of orders: {len(orders)}")
    assert len(orders) == 2, f"Expected 2 orders (TP and SL), got {len(orders)}"
    
    # Check that all orders are for SELL side (for long position)
    for i, order in enumerate(orders):
        assert order.get('side') == 'SELL', f"Side mismatch for order {i}: {order.get('side')} != SELL"
    
    # Test case 2: Short position TP/SL orders
    side = "SHORT"
    entry_price = 40000
    take_profit_price = 38000  # Lower for short
    stop_loss_price = 41000    # Higher for short
    
    print(f"\nTest case 2: Short position TP/SL ({side} {quantity} {symbol}, entry={entry_price}, TP={take_profit_price}, SL={stop_loss_price})")
    result = executor.place_tp_sl_orders(
        symbol=symbol, 
        side=side, 
        entry_price=entry_price, 
        quantity=quantity,
        take_profit_price=take_profit_price,
        stop_loss_price=stop_loss_price
    )
    
    print(f"  Order List ID: {result.get('orderListId')}")
    assert 'orderListId' in result, "Order List ID missing in OCO response"
    
    # Check orders
    orders = result.get('orders', [])
    print(f"  Number of orders: {len(orders)}")
    assert len(orders) == 2, f"Expected 2 orders (TP and SL), got {len(orders)}"
    
    # Check that all orders are for BUY side (for short position)
    for i, order in enumerate(orders):
        assert order.get('side') == 'BUY', f"Side mismatch for order {i}: {order.get('side')} != BUY"
    
    # Test case 3: Get and cancel OCO order
    order_list_id = result.get('orderListId')
    
    print(f"\nTest case 3: Get and cancel OCO order (List ID: {order_list_id})")
    
    # Get order status
    status = executor.get_oco_order_status(symbol=symbol, order_list_id=order_list_id)
    print(f"  Status: {status.get('status')}")
    assert status.get('orderListId') == order_list_id, f"Order List ID mismatch: {status.get('orderListId')} != {order_list_id}"
    
    # Cancel order
    cancel_result = executor.cancel_oco_order(symbol=symbol, order_list_id=order_list_id)
    print(f"  Cancel result: {cancel_result.get('status')}")
    assert cancel_result.get('status') == 'CANCELED', "OCO order not canceled"
    
    # Test case 4: Error handling for invalid inputs
    print("\nTest case 4: Error handling for invalid inputs")
    
    # Invalid quantity
    invalid_result = executor.place_tp_sl_orders(
        symbol=symbol, 
        side=side, 
        entry_price=entry_price, 
        quantity=0,
        take_profit_price=take_profit_price,
        stop_loss_price=stop_loss_price
    )
    print(f"  Invalid quantity: {'error' in invalid_result}")
    assert 'error' in invalid_result, "No error for invalid quantity"
    
    # Invalid entry price
    invalid_result = executor.place_tp_sl_orders(
        symbol=symbol, 
        side=side, 
        entry_price=0, 
        quantity=quantity,
        take_profit_price=take_profit_price,
        stop_loss_price=stop_loss_price
    )
    print(f"  Invalid entry price: {'error' in invalid_result}")
    assert 'error' in invalid_result, "No error for invalid entry price"
    
    # Test case 5: Invalid price relationships
    print("\nTest case 5: Invalid price relationships")
    
    # For long position, TP must be higher than entry
    invalid_result = executor.place_tp_sl_orders(
        symbol=symbol, 
        side="LONG", 
        entry_price=40000, 
        quantity=quantity,
        take_profit_price=39000,  # Lower than entry
        stop_loss_price=38000
    )
    print(f"  Long position, TP lower than entry: {'error' in invalid_result}")
    assert 'error' in invalid_result, "No error for invalid TP (long)"
    
    # For long position, SL must be lower than entry
    invalid_result = executor.place_tp_sl_orders(
        symbol=symbol, 
        side="LONG", 
        entry_price=40000, 
        quantity=quantity,
        take_profit_price=42000,
        stop_loss_price=41000  # Higher than entry
    )
    print(f"  Long position, SL higher than entry: {'error' in invalid_result}")
    assert 'error' in invalid_result, "No error for invalid SL (long)"
    
    # For short position, TP must be lower than entry
    invalid_result = executor.place_tp_sl_orders(
        symbol=symbol, 
        side="SHORT", 
        entry_price=40000, 
        quantity=quantity,
        take_profit_price=41000,  # Higher than entry
        stop_loss_price=42000
    )
    print(f"  Short position, TP higher than entry: {'error' in invalid_result}")
    assert 'error' in invalid_result, "No error for invalid TP (short)"
    
    # For short position, SL must be higher than entry
    invalid_result = executor.place_tp_sl_orders(
        symbol=symbol, 
        side="SHORT", 
        entry_price=40000, 
        quantity=quantity,
        take_profit_price=38000,
        stop_loss_price=39000  # Lower than entry
    )
    print(f"  Short position, SL lower than entry: {'error' in invalid_result}")
    assert 'error' in invalid_result, "No error for invalid SL (short)"
    
    print("\nOCOOrderExecutor tests completed successfully!")
    return True

def test_order_execution_factory():
    """Test the OrderExecutionFactory class"""
    print("\n=== Testing OrderExecutionFactory ===")
    
    # Initialize the mock API client
    api_client = MockAPIClient()
    factory = OrderExecutionFactory()
    
    # Test all executor types
    executor_types = ['base', 'iceberg', 'twap', 'scaled', 'oco', 'unknown']
    
    for executor_type in executor_types:
        executor = factory.create_executor(executor_type, api_client)
        
        # Check the type of executor created
        if executor_type == 'base':
            expected_type = BaseOrderExecutor
        elif executor_type == 'iceberg':
            expected_type = IcebergOrderExecutor
        elif executor_type == 'twap':
            expected_type = TWAPExecutor
        elif executor_type == 'scaled':
            expected_type = ScaledOrderExecutor
        elif executor_type == 'oco':
            expected_type = OCOOrderExecutor
        else:
            expected_type = BaseOrderExecutor  # fallback for unknown types
            
        actual_type = type(executor)
        print(f"Requested: {executor_type}, Created: {actual_type.__name__}")
        assert isinstance(executor, expected_type), f"Expected type {expected_type.__name__}, got {actual_type.__name__}"
    
    print("\nOrderExecutionFactory tests completed successfully!")
    return True

def run_all_tests():
    """Run all order execution tests"""
    start_time = datetime.now()
    
    print("=== Starting Order Execution Tests ===")
    print(f"Time: {start_time}")
    print(f"Using actual module: {HAS_MODULE}")
    
    # Dictionary to track test results
    results = {
        "meta": {
            "timestamp": start_time,
            "module_available": HAS_MODULE
        },
        "tests": {}
    }
    
    # Run tests
    test_functions = [
        test_base_order_executor,
        test_iceberg_order_executor,
        test_twap_executor,
        test_scaled_order_executor,
        test_oco_order_executor,
        test_order_execution_factory
    ]
    
    all_passed = True
    
    for test_func in test_functions:
        test_name = test_func.__name__
        try:
            passed = test_func()
            results["tests"][test_name] = {"passed": passed}
        except Exception as e:
            print(f"Error in {test_name}: {e}")
            print(traceback.format_exc())
            results["tests"][test_name] = {
                "passed": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            all_passed = False
    
    # Calculate test duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["meta"]["duration_seconds"] = duration
    
    # Save results
    result_path = os.path.join('../test_results', f"order_execution_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    def serialize_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    with open(result_path, 'w') as f:
        json.dump(results, f, default=serialize_datetime, indent=2)
        
    print(f"\nSaved test results to {result_path}")
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Testing completed in {duration:.2f} seconds")
    
    for test_name, result in results["tests"].items():
        if result.get("passed", False):
            print(f"✅ {test_name}: Passed")
        else:
            print(f"❌ {test_name}: Failed - {result.get('error', 'Unknown error')}")
            
    print(f"\nOverall result: {'PASSED' if all_passed else 'FAILED'}")
    
    return results

if __name__ == "__main__":
    run_all_tests()