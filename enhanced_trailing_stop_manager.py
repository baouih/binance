#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module quản lý trailing stop nâng cao

Mô-đun này cung cấp lớp EnhancedTrailingStopManager với các chức năng
trailing stop thích ứng dựa theo trạng thái thị trường và biến động giá.
"""

import os
import logging
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime, timedelta
import time
import threading

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/trailing_stop.log')
    ]
)

logger = logging.getLogger('trailing_stop')

class EnhancedTrailingStopManager:
    """
    Lớp quản lý trailing stop thông minh với khả năng thích ứng theo trạng thái thị trường
    """
    
    def __init__(self, config_path: str = 'configs/trailing_stop_config.json', api_client=None):
        """
        Khởi tạo manager
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            api_client: Client API để thực hiện các thao tác thị trường
        """
        self.config = self._load_config(config_path)
        self.api_client = api_client
        
        # Các tham số cấu hình
        self.activation_threshold = self.config.get('activation_threshold', 0.5)  # % lợi nhuận để kích hoạt
        self.trail_percentages = self.config.get('trail_percentages', {
            'default': 0.3,
            'trending': 0.2,
            'volatile': 0.5,
            'low_volatility': 0.15
        })
        self.min_profit_protection = self.config.get('min_profit_protection', 0.2)  # % tối thiểu bảo vệ
        self.volatility_measure_window = self.config.get('volatility_measure_window', 14)
        self.atr_multiplier = self.config.get('atr_multiplier', 2.0)
        self.partial_exit_levels = self.config.get('partial_exit_levels', [])
        
        # Trạng thái và dữ liệu theo dõi
        self.active_stops = {}  # key: symbol_order_id, value: stop_data
        self.market_regimes = {}  # key: symbol, value: regime_data
        self.last_prices = {}  # key: symbol, value: last_price
        self.price_history = {}  # key: symbol, value: list of prices
        
        # Lock để đồng bộ hóa trong môi trường đa luồng
        self.lock = threading.Lock()
        
        # Tạo thư mục logs nếu chưa tồn tại
        os.makedirs('logs', exist_ok=True)
        
        logger.info("Đã khởi tạo EnhancedTrailingStopManager")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file JSON
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                # Cấu hình mặc định nếu không tìm thấy file
                default_config = {
                    "activation_threshold": 0.5,
                    "trail_percentages": {
                        "default": 0.3,
                        "trending": 0.2,
                        "volatile": 0.5,
                        "low_volatility": 0.15
                    },
                    "min_profit_protection": 0.2,
                    "volatility_measure_window": 14,
                    "atr_multiplier": 2.0,
                    "partial_exit_levels": [
                        {"profit_percentage": 1.0, "exit_percentage": 0.25},
                        {"profit_percentage": 2.0, "exit_percentage": 0.25},
                        {"profit_percentage": 3.0, "exit_percentage": 0.25}
                    ],
                    "profit_based_trail": [
                        {"profit_threshold": 1.0, "trail_percentage": 0.4},
                        {"profit_threshold": 2.0, "trail_percentage": 0.3},
                        {"profit_threshold": 5.0, "trail_percentage": 0.2}
                    ]
                }
                
                # Tạo thư mục configs nếu chưa tồn tại
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                
                # Lưu cấu hình mặc định
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                
                logger.info(f"Đã tạo file cấu hình mặc định tại {config_path}")
                return default_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            return {}
    
    def register_position(self, symbol: str, order_id: str, entry_price: float, 
                          position_size: float, direction: str = 'long',
                          stop_loss_price: Optional[float] = None,
                          take_profit_price: Optional[float] = None) -> str:
        """
        Đăng ký vị thế để theo dõi trailing stop
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            order_id (str): ID của lệnh/vị thế
            entry_price (float): Giá vào lệnh
            position_size (float): Kích thước vị thế
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            stop_loss_price (float, optional): Giá stop loss ban đầu
            take_profit_price (float, optional): Giá take profit ban đầu
            
        Returns:
            str: ID theo dõi trailing stop
        """
        with self.lock:
            # Tạo ID theo dõi
            tracking_id = f"{symbol}_{order_id}"
            
            # Thu thập dữ liệu thị trường hiện tại nếu cần
            if symbol not in self.market_regimes:
                self._update_market_regime(symbol)
            
            # Khởi tạo theo dõi vị thế
            self.active_stops[tracking_id] = {
                'symbol': symbol,
                'order_id': order_id,
                'entry_price': entry_price,
                'position_size': position_size,
                'current_position_size': position_size,  # Cho partial exits
                'direction': direction,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'trailing_stop_price': None,
                'trailing_active': False,
                'highest_price': entry_price if direction == 'long' else None,
                'lowest_price': entry_price if direction == 'short' else None,
                'profit_percentage': 0.0,
                'current_market_regime': self.market_regimes.get(symbol, {}).get('regime', 'unknown'),
                'partial_exits': [],
                'timestamp': datetime.now().isoformat(),
                'stop_type': 'fixed',  # 'fixed', 'trailing', 'dynamic'
                'atr_value': self.market_regimes.get(symbol, {}).get('atr', 0)
            }
            
            logger.info(f"Đã đăng ký vị thế {tracking_id}: {direction} {position_size} {symbol} tại {entry_price}")
            return tracking_id
    
    def update_price(self, symbol: str, current_price: float, timestamp: Optional[datetime] = None) -> None:
        """
        Cập nhật giá mới và xử lý trailing stop
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            current_price (float): Giá hiện tại
            timestamp (datetime, optional): Thời gian của giá
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        with self.lock:
            # Cập nhật giá mới nhất
            self.last_prices[symbol] = current_price
            
            # Lưu vào lịch sử giá
            if symbol not in self.price_history:
                self.price_history[symbol] = []
                
            self.price_history[symbol].append({
                'price': current_price,
                'timestamp': timestamp.isoformat()
            })
            
            # Giới hạn kích thước lịch sử giá
            max_history = self.volatility_measure_window * 10
            if len(self.price_history[symbol]) > max_history:
                self.price_history[symbol] = self.price_history[symbol][-max_history:]
            
            # Kiểm tra và cập nhật tất cả trạng thái trailing stop
            positions_to_close = []
            for tracking_id, stop_data in self.active_stops.items():
                if stop_data['symbol'] == symbol:
                    triggered, action_type = self._process_trailing_stop(tracking_id, current_price, timestamp)
                    if triggered:
                        positions_to_close.append((tracking_id, action_type))
            
            # Xử lý các vị thế cần đóng
            for tracking_id, action_type in positions_to_close:
                self._execute_stop(tracking_id, action_type)
    
    def _process_trailing_stop(self, tracking_id: str, current_price: float, 
                              timestamp: datetime) -> Tuple[bool, str]:
        """
        Xử lý trailing stop cho một vị thế cụ thể
        
        Args:
            tracking_id (str): ID theo dõi
            current_price (float): Giá hiện tại
            timestamp (datetime): Thời gian hiện tại
            
        Returns:
            Tuple[bool, str]: (Đã kích hoạt, Loại hành động)
        """
        stop_data = self.active_stops[tracking_id]
        symbol = stop_data['symbol']
        direction = stop_data['direction']
        entry_price = stop_data['entry_price']
        
        # Tính % lợi nhuận hiện tại
        if direction == 'long':
            profit_percentage = (current_price - entry_price) / entry_price * 100
            # Cập nhật giá cao nhất
            if stop_data['highest_price'] is None or current_price > stop_data['highest_price']:
                stop_data['highest_price'] = current_price
        else:  # short
            profit_percentage = (entry_price - current_price) / entry_price * 100
            # Cập nhật giá thấp nhất
            if stop_data['lowest_price'] is None or current_price < stop_data['lowest_price']:
                stop_data['lowest_price'] = current_price
        
        # Cập nhật % lợi nhuận
        stop_data['profit_percentage'] = profit_percentage
        
        # Nếu chưa kích hoạt trailing stop, kiểm tra ngưỡng kích hoạt
        if not stop_data['trailing_active']:
            if profit_percentage >= self.activation_threshold:
                # Kích hoạt trailing stop
                trail_percentage = self._get_trail_percentage(symbol, profit_percentage)
                
                if direction == 'long':
                    trail_amount = current_price * (trail_percentage / 100)
                    stop_price = current_price - trail_amount
                    
                    # Đảm bảo stop mới cao hơn stop cũ nếu có
                    if stop_data['stop_loss_price'] is not None:
                        stop_price = max(stop_price, stop_data['stop_loss_price'])
                        
                else:  # short
                    trail_amount = current_price * (trail_percentage / 100)
                    stop_price = current_price + trail_amount
                    
                    # Đảm bảo stop mới thấp hơn stop cũ nếu có
                    if stop_data['stop_loss_price'] is not None:
                        stop_price = min(stop_price, stop_data['stop_loss_price'])
                
                # Cập nhật thông tin trailing stop
                stop_data['trailing_stop_price'] = stop_price
                stop_data['trailing_active'] = True
                stop_data['stop_type'] = 'trailing'
                
                logger.info(f"Kích hoạt trailing stop cho {tracking_id}: Giá: {current_price}, Stop: {stop_price}, Trail: {trail_percentage}%")
                
                # Tùy chọn: cập nhật ở sàn nếu có API client
                self._update_stop_loss_order(tracking_id, stop_price)
        else:
            # Trailing stop đã kích hoạt, cập nhật nếu cần
            if direction == 'long' and current_price > stop_data['highest_price']:
                # Giá mới cao hơn, di chuyển trailing stop
                trail_percentage = self._get_trail_percentage(symbol, profit_percentage)
                trail_amount = current_price * (trail_percentage / 100)
                new_stop_price = current_price - trail_amount
                
                # Chỉ cập nhật nếu stop mới cao hơn stop cũ
                if new_stop_price > stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop_price
                    stop_data['highest_price'] = current_price
                    
                    logger.info(f"Cập nhật trailing stop cho {tracking_id}: Giá: {current_price}, Stop mới: {new_stop_price}")
                    
                    # Tùy chọn: cập nhật ở sàn nếu có API client
                    self._update_stop_loss_order(tracking_id, new_stop_price)
            
            elif direction == 'short' and current_price < stop_data['lowest_price']:
                # Giá mới thấp hơn, di chuyển trailing stop
                trail_percentage = self._get_trail_percentage(symbol, profit_percentage)
                trail_amount = current_price * (trail_percentage / 100)
                new_stop_price = current_price + trail_amount
                
                # Chỉ cập nhật nếu stop mới thấp hơn stop cũ
                if new_stop_price < stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop_price
                    stop_data['lowest_price'] = current_price
                    
                    logger.info(f"Cập nhật trailing stop cho {tracking_id}: Giá: {current_price}, Stop mới: {new_stop_price}")
                    
                    # Tùy chọn: cập nhật ở sàn nếu có API client
                    self._update_stop_loss_order(tracking_id, new_stop_price)
        
        # Kiểm tra trạng thái thị trường và thay đổi chiến lược nếu cần
        self._adapt_to_market_conditions(tracking_id, current_price)
        
        # Kiểm tra kích hoạt partial exit
        partial_exit_triggered = self._check_partial_exit(tracking_id, profit_percentage)
        if partial_exit_triggered:
            return True, "partial_exit"
        
        # Kiểm tra kích hoạt stop loss
        if stop_data['trailing_active'] and (
            (direction == 'long' and current_price <= stop_data['trailing_stop_price']) or
            (direction == 'short' and current_price >= stop_data['trailing_stop_price'])
        ):
            logger.info(f"Trailing stop kích hoạt cho {tracking_id} tại giá {current_price}")
            return True, "trailing_stop"
        
        # Kiểm tra kích hoạt stop loss cố định
        if not stop_data['trailing_active'] and stop_data['stop_loss_price'] is not None and (
            (direction == 'long' and current_price <= stop_data['stop_loss_price']) or
            (direction == 'short' and current_price >= stop_data['stop_loss_price'])
        ):
            logger.info(f"Stop loss cố định kích hoạt cho {tracking_id} tại giá {current_price}")
            return True, "stop_loss"
        
        # Kiểm tra kích hoạt take profit
        if stop_data['take_profit_price'] is not None and (
            (direction == 'long' and current_price >= stop_data['take_profit_price']) or
            (direction == 'short' and current_price <= stop_data['take_profit_price'])
        ):
            logger.info(f"Take profit kích hoạt cho {tracking_id} tại giá {current_price}")
            return True, "take_profit"
        
        return False, ""
    
    def _get_trail_percentage(self, symbol: str, profit_percentage: float) -> float:
        """
        Lấy phần trăm trailing dựa trên trạng thái thị trường và lợi nhuận
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            profit_percentage (float): Phần trăm lợi nhuận hiện tại
            
        Returns:
            float: Phần trăm trailing
        """
        # Kiểm tra điều chỉnh theo lợi nhuận
        profit_based_trail = self.config.get('profit_based_trail', [])
        if profit_based_trail:
            # Sắp xếp ngưỡng lợi nhuận giảm dần
            sorted_thresholds = sorted(profit_based_trail, key=lambda x: x.get('profit_threshold', 0), reverse=True)
            
            # Tìm ngưỡng phù hợp đầu tiên
            for threshold in sorted_thresholds:
                if profit_percentage >= threshold.get('profit_threshold', 0):
                    return threshold.get('trail_percentage', self.trail_percentages.get('default', 0.3))
        
        # Nếu không có điều chỉnh theo lợi nhuận, sử dụng theo regime
        regime = self.market_regimes.get(symbol, {}).get('regime', 'unknown')
        
        if regime == 'trending':
            return self.trail_percentages.get('trending', 0.2)
        elif regime == 'volatile':
            return self.trail_percentages.get('volatile', 0.5)
        elif regime == 'low_volatility':
            return self.trail_percentages.get('low_volatility', 0.15)
        else:
            return self.trail_percentages.get('default', 0.3)
    
    def _update_market_regime(self, symbol: str) -> None:
        """
        Cập nhật phân loại trạng thái thị trường
        
        Args:
            symbol (str): Ký hiệu tiền tệ
        """
        # Nếu không có đủ dữ liệu, thử lấy từ API
        if symbol not in self.price_history or len(self.price_history[symbol]) < self.volatility_measure_window:
            if self.api_client:
                try:
                    # Lấy dữ liệu lịch sử
                    historical_data = self._get_historical_data(symbol)
                    
                    # Cập nhật price_history
                    if historical_data and len(historical_data) > 0:
                        self.price_history[symbol] = historical_data
                except Exception as e:
                    logger.error(f"Lỗi khi lấy dữ liệu lịch sử: {str(e)}")
        
        # Nếu vẫn không đủ dữ liệu, trả về unknown
        if symbol not in self.price_history or len(self.price_history[symbol]) < self.volatility_measure_window:
            self.market_regimes[symbol] = {
                'regime': 'unknown',
                'volatility': 0,
                'atr': 0,
                'trend_strength': 0,
                'updated_at': datetime.now().isoformat()
            }
            return
        
        # Tính toán các chỉ số
        recent_prices = [entry['price'] for entry in self.price_history[symbol][-self.volatility_measure_window:]]
        prices_array = np.array(recent_prices)
        
        # Tính ATR
        highs = prices_array
        lows = prices_array
        closes = prices_array[:-1]
        
        tr1 = np.abs(highs[1:] - lows[1:])
        tr2 = np.abs(highs[1:] - closes)
        tr3 = np.abs(lows[1:] - closes)
        
        tr = np.vstack([tr1, tr2, tr3]).max(axis=0)
        atr = np.mean(tr)
        
        # Tính volatility
        volatility = np.std(prices_array) / np.mean(prices_array) * 100
        
        # Tính trend strength
        ma_short = np.mean(prices_array[-5:])
        ma_long = np.mean(prices_array)
        trend_strength = abs(ma_short - ma_long) / ma_long * 100
        
        # Xác định regime
        regime = 'unknown'
        if volatility < 0.5:
            regime = 'low_volatility'
        elif volatility > 2.0:
            regime = 'volatile'
        elif trend_strength > 1.0:
            regime = 'trending'
        else:
            regime = 'normal'
        
        # Cập nhật market_regimes
        self.market_regimes[symbol] = {
            'regime': regime,
            'volatility': volatility,
            'atr': atr,
            'trend_strength': trend_strength,
            'updated_at': datetime.now().isoformat()
        }
        
        logger.debug(f"Cập nhật regime {symbol}: {regime} (Volatility: {volatility:.2f}%, Trend: {trend_strength:.2f}%, ATR: {atr:.4f})")
    
    def _get_historical_data(self, symbol: str) -> List[Dict]:
        """
        Lấy dữ liệu lịch sử từ API
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            
        Returns:
            List[Dict]: Danh sách dữ liệu lịch sử
        """
        if not self.api_client:
            return []
        
        try:
            # Lấy dữ liệu từ API client (phụ thuộc vào API đang sử dụng)
            # Ví dụ với Binance API:
            klines = self.api_client.get_klines(
                symbol=symbol, 
                interval='1h',
                limit=self.volatility_measure_window * 2
            )
            
            # Chuyển đổi sang định dạng price_history
            result = []
            for kline in klines:
                close_price = float(kline[4])  # Giá đóng cửa là index 4 trong kline Binance
                timestamp = datetime.fromtimestamp(kline[0] / 1000)  # Timestamp là index 0 và tính bằng ms
                
                result.append({
                    'price': close_price,
                    'timestamp': timestamp.isoformat()
                })
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu lịch sử từ API: {str(e)}")
            return []
    
    def _adapt_to_market_conditions(self, tracking_id: str, current_price: float) -> None:
        """
        Điều chỉnh chiến lược dựa trên điều kiện thị trường
        
        Args:
            tracking_id (str): ID theo dõi
            current_price (float): Giá hiện tại
        """
        if tracking_id not in self.active_stops:
            return
            
        stop_data = self.active_stops[tracking_id]
        symbol = stop_data['symbol']
        
        # Cập nhật regime nếu cần
        if symbol not in self.market_regimes or \
           datetime.fromisoformat(self.market_regimes[symbol]['updated_at']) < datetime.now() - timedelta(hours=1):
            self._update_market_regime(symbol)
        
        # Lấy regime hiện tại
        current_regime = self.market_regimes.get(symbol, {}).get('regime', 'unknown')
        
        # Nếu regime thay đổi, cập nhật chiến lược
        if current_regime != stop_data['current_market_regime'] and stop_data['trailing_active']:
            stop_data['current_market_regime'] = current_regime
            
            # Tính lại trailing stop với % mới
            direction = stop_data['direction']
            profit_percentage = stop_data['profit_percentage']
            trail_percentage = self._get_trail_percentage(symbol, profit_percentage)
            
            if direction == 'long':
                trail_amount = current_price * (trail_percentage / 100)
                new_stop_price = current_price - trail_amount
                
                # Chỉ cập nhật nếu stop mới cao hơn stop cũ
                if new_stop_price > stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop_price
                    logger.info(f"Cập nhật trailing stop theo regime mới ({current_regime}) cho {tracking_id}: {new_stop_price}")
                    self._update_stop_loss_order(tracking_id, new_stop_price)
            else:  # short
                trail_amount = current_price * (trail_percentage / 100)
                new_stop_price = current_price + trail_amount
                
                # Chỉ cập nhật nếu stop mới thấp hơn stop cũ
                if new_stop_price < stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop_price
                    logger.info(f"Cập nhật trailing stop theo regime mới ({current_regime}) cho {tracking_id}: {new_stop_price}")
                    self._update_stop_loss_order(tracking_id, new_stop_price)
    
    def _check_partial_exit(self, tracking_id: str, profit_percentage: float) -> bool:
        """
        Kiểm tra và thực hiện partial exit dựa trên mức lợi nhuận
        
        Args:
            tracking_id (str): ID theo dõi
            profit_percentage (float): Phần trăm lợi nhuận hiện tại
            
        Returns:
            bool: True nếu đã thực hiện partial exit
        """
        # Nếu không có partial_exit_levels, không cần kiểm tra
        if not self.partial_exit_levels:
            return False
            
        stop_data = self.active_stops[tracking_id]
        
        # Kiểm tra từng level
        for level in self.partial_exit_levels:
            profit_threshold = level.get('profit_percentage', 0)
            exit_percentage = level.get('exit_percentage', 0)
            
            # Nếu profit đạt ngưỡng và chưa exit ở level này
            if profit_percentage >= profit_threshold and \
               profit_threshold not in [exit['profit_threshold'] for exit in stop_data['partial_exits']]:
                
                # Tính số lượng cần exit
                exit_size = stop_data['position_size'] * exit_percentage
                
                # Thêm vào danh sách partial exits
                stop_data['partial_exits'].append({
                    'profit_threshold': profit_threshold,
                    'exit_percentage': exit_percentage,
                    'exit_size': exit_size,
                    'remaining_size': stop_data['current_position_size'] - exit_size,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Cập nhật position size hiện tại
                stop_data['current_position_size'] -= exit_size
                
                logger.info(f"Thực hiện partial exit cho {tracking_id} tại mức lợi nhuận {profit_threshold}%: {exit_size} ({exit_percentage*100}%)")
                
                # Thực hiện lệnh exit nếu có API client
                self._execute_partial_exit(tracking_id, exit_size)
                
                return True
        
        return False
    
    def _execute_partial_exit(self, tracking_id: str, exit_size: float) -> bool:
        """
        Thực hiện lệnh partial exit
        
        Args:
            tracking_id (str): ID theo dõi
            exit_size (float): Kích thước cần exit
            
        Returns:
            bool: True nếu thành công
        """
        if not self.api_client:
            logger.warning(f"Không có API client để thực hiện partial exit cho {tracking_id}")
            return False
            
        try:
            stop_data = self.active_stops[tracking_id]
            symbol = stop_data['symbol']
            direction = stop_data['direction']
            
            # Đặt lệnh market để exit
            side = 'SELL' if direction == 'long' else 'BUY'
            result = self.api_client.create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=exit_size
            )
            
            logger.info(f"Đã đặt lệnh partial exit cho {tracking_id}: {result}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện partial exit cho {tracking_id}: {str(e)}")
            return False
    
    def _update_stop_loss_order(self, tracking_id: str, new_stop_price: float) -> bool:
        """
        Cập nhật lệnh stop loss trên sàn
        
        Args:
            tracking_id (str): ID theo dõi
            new_stop_price (float): Giá stop loss mới
            
        Returns:
            bool: True nếu thành công
        """
        if not self.api_client:
            return False
            
        try:
            stop_data = self.active_stops[tracking_id]
            symbol = stop_data['symbol']
            direction = stop_data['direction']
            order_id = stop_data['order_id']
            
            # Hủy lệnh stop loss cũ nếu có
            # [Lưu ý: Cách thực hiện phụ thuộc vào API]
            
            # Đặt lệnh stop loss mới
            side = 'SELL' if direction == 'long' else 'BUY'
            result = self.api_client.create_order(
                symbol=symbol,
                side=side,
                type='STOP_MARKET',
                stopPrice=new_stop_price,
                closePosition='true'
            )
            
            logger.info(f"Đã cập nhật stop loss cho {tracking_id} tại {new_stop_price}: {result}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật stop loss cho {tracking_id}: {str(e)}")
            return False
    
    def _execute_stop(self, tracking_id: str, action_type: str) -> bool:
        """
        Thực hiện đóng vị thế khi stop loss kích hoạt
        
        Args:
            tracking_id (str): ID theo dõi
            action_type (str): Loại hành động kích hoạt
            
        Returns:
            bool: True nếu thành công
        """
        if tracking_id not in self.active_stops:
            logger.warning(f"Không tìm thấy vị thế {tracking_id} để đóng")
            return False
            
        stop_data = self.active_stops[tracking_id]
        
        # Kiểm tra xem có API client để đóng lệnh không
        if self.api_client and action_type != "partial_exit" and stop_data['current_position_size'] > 0:
            try:
                symbol = stop_data['symbol']
                direction = stop_data['direction']
                
                # Đặt lệnh market để đóng vị thế
                side = 'SELL' if direction == 'long' else 'BUY'
                result = self.api_client.create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=stop_data['current_position_size']
                )
                
                logger.info(f"Đã đóng vị thế {tracking_id} do {action_type}: {result}")
            except Exception as e:
                logger.error(f"Lỗi khi đóng vị thế {tracking_id}: {str(e)}")
        
        # Nếu là partial exit, không xóa khỏi active_stops
        if action_type == "partial_exit":
            return True
            
        # Lưu thông tin vị thế đã đóng
        stop_data['close_type'] = action_type
        stop_data['close_time'] = datetime.now().isoformat()
        stop_data['final_profit_percentage'] = stop_data['profit_percentage']
        
        # Lưu vào lịch sử và xóa khỏi active_stops
        self._save_closed_position(tracking_id, stop_data)
        
        # Xóa khỏi active_stops
        del self.active_stops[tracking_id]
        
        return True
    
    def _save_closed_position(self, tracking_id: str, position_data: Dict) -> None:
        """
        Lưu thông tin vị thế đã đóng vào lịch sử
        
        Args:
            tracking_id (str): ID theo dõi
            position_data (Dict): Dữ liệu vị thế
        """
        # Đảm bảo thư mục tồn tại
        os.makedirs('logs/closed_positions', exist_ok=True)
        
        # Tạo tên file
        symbol = position_data['symbol']
        close_time = datetime.fromisoformat(position_data['close_time']).strftime('%Y%m%d_%H%M%S')
        file_name = f"position_{symbol}_{close_time}.json"
        file_path = os.path.join('logs/closed_positions', file_name)
        
        # Lưu vào file
        try:
            with open(file_path, 'w') as f:
                json.dump(position_data, f, indent=4)
                
            logger.info(f"Đã lưu thông tin vị thế đóng {tracking_id} vào {file_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu thông tin vị thế đóng {tracking_id}: {str(e)}")
    
    def get_active_positions(self) -> Dict[str, Dict]:
        """
        Lấy danh sách các vị thế đang theo dõi
        
        Returns:
            Dict[str, Dict]: Danh sách vị thế
        """
        with self.lock:
            return {k: v.copy() for k, v in self.active_stops.items()}
    
    def get_position_info(self, tracking_id: str) -> Optional[Dict]:
        """
        Lấy thông tin vị thế cụ thể
        
        Args:
            tracking_id (str): ID theo dõi
            
        Returns:
            Optional[Dict]: Thông tin vị thế hoặc None nếu không tìm thấy
        """
        with self.lock:
            return self.active_stops.get(tracking_id, {}).copy()
    
    def update_stop_loss(self, tracking_id: str, new_stop_price: float) -> bool:
        """
        Cập nhật giá stop loss thủ công
        
        Args:
            tracking_id (str): ID theo dõi
            new_stop_price (float): Giá stop loss mới
            
        Returns:
            bool: True nếu thành công
        """
        with self.lock:
            if tracking_id not in self.active_stops:
                logger.warning(f"Không tìm thấy vị thế {tracking_id} để cập nhật stop loss")
                return False
                
            stop_data = self.active_stops[tracking_id]
            direction = stop_data['direction']
            current_price = self.last_prices.get(stop_data['symbol'], 0)
            
            # Kiểm tra giá stop loss hợp lệ
            if direction == 'long' and new_stop_price >= current_price:
                logger.warning(f"Stop loss mới ({new_stop_price}) phải thấp hơn giá hiện tại ({current_price}) cho lệnh long")
                return False
            elif direction == 'short' and new_stop_price <= current_price:
                logger.warning(f"Stop loss mới ({new_stop_price}) phải cao hơn giá hiện tại ({current_price}) cho lệnh short")
                return False
            
            # Cập nhật giá stop loss
            stop_data['stop_loss_price'] = new_stop_price
            
            # Nếu trailing stop đã kích hoạt, cập nhật trailing stop price nếu cần
            if stop_data['trailing_active']:
                if direction == 'long' and new_stop_price > stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop_price
                elif direction == 'short' and new_stop_price < stop_data['trailing_stop_price']:
                    stop_data['trailing_stop_price'] = new_stop_price
            
            # Cập nhật trên sàn nếu có API client
            self._update_stop_loss_order(tracking_id, new_stop_price)
            
            logger.info(f"Đã cập nhật stop loss cho {tracking_id} thành {new_stop_price}")
            return True
    
    def manual_close_position(self, tracking_id: str, reason: str = "manual") -> bool:
        """
        Đóng vị thế thủ công
        
        Args:
            tracking_id (str): ID theo dõi
            reason (str): Lý do đóng
            
        Returns:
            bool: True nếu thành công
        """
        with self.lock:
            return self._execute_stop(tracking_id, reason)
    
    def set_config_parameter(self, param_name: str, value: Any) -> bool:
        """
        Cập nhật tham số cấu hình
        
        Args:
            param_name (str): Tên tham số
            value (Any): Giá trị mới
            
        Returns:
            bool: True nếu thành công
        """
        try:
            with self.lock:
                # Cập nhật tham số
                if param_name in self.config:
                    self.config[param_name] = value
                    
                    # Cập nhật các biến instance tương ứng
                    if param_name == 'activation_threshold':
                        self.activation_threshold = value
                    elif param_name == 'trail_percentages':
                        self.trail_percentages = value
                    elif param_name == 'min_profit_protection':
                        self.min_profit_protection = value
                    elif param_name == 'volatility_measure_window':
                        self.volatility_measure_window = value
                    elif param_name == 'atr_multiplier':
                        self.atr_multiplier = value
                    elif param_name == 'partial_exit_levels':
                        self.partial_exit_levels = value
                    
                    # Lưu cấu hình mới
                    config_path = 'configs/trailing_stop_config.json'
                    os.makedirs(os.path.dirname(config_path), exist_ok=True)
                    
                    with open(config_path, 'w') as f:
                        json.dump(self.config, f, indent=4)
                    
                    logger.info(f"Đã cập nhật tham số {param_name} thành {value}")
                    return True
                else:
                    logger.warning(f"Không tìm thấy tham số {param_name} trong cấu hình")
                    return False
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật tham số {param_name}: {str(e)}")
            return False
    
    def get_performance_stats(self) -> Dict:
        """
        Lấy thống kê hiệu suất của trailing stop
        
        Returns:
            Dict: Thống kê hiệu suất
        """
        # Thư mục chứa các vị thế đã đóng
        closed_positions_dir = 'logs/closed_positions'
        
        if not os.path.exists(closed_positions_dir):
            return {
                'total_positions': 0,
                'successful_trails': 0,
                'profit_saved': 0,
                'avg_trail_percentage': 0,
                'positions_by_regime': {},
                'positions_by_symbol': {}
            }
        
        # Lấy danh sách file trong thư mục
        position_files = [f for f in os.listdir(closed_positions_dir) if f.endswith('.json')]
        
        # Thống kê
        stats = {
            'total_positions': 0,
            'successful_trails': 0,
            'profit_saved': 0,
            'avg_trail_percentage': 0,
            'positions_by_regime': {},
            'positions_by_symbol': {},
            'positions_by_close_type': {}
        }
        
        trail_percentages = []
        
        # Đọc từng file
        for file_name in position_files:
            file_path = os.path.join(closed_positions_dir, file_name)
            
            try:
                with open(file_path, 'r') as f:
                    position_data = json.load(f)
                
                # Tăng tổng số vị thế
                stats['total_positions'] += 1
                
                # Lấy thông tin
                symbol = position_data.get('symbol', 'unknown')
                regime = position_data.get('current_market_regime', 'unknown')
                close_type = position_data.get('close_type', 'unknown')
                
                # Cập nhật thống kê theo symbol
                if symbol not in stats['positions_by_symbol']:
                    stats['positions_by_symbol'][symbol] = {
                        'count': 0,
                        'successful_trails': 0,
                        'avg_profit': 0
                    }
                
                stats['positions_by_symbol'][symbol]['count'] += 1
                
                # Cập nhật thống kê theo regime
                if regime not in stats['positions_by_regime']:
                    stats['positions_by_regime'][regime] = {
                        'count': 0,
                        'successful_trails': 0,
                        'avg_profit': 0
                    }
                
                stats['positions_by_regime'][regime]['count'] += 1
                
                # Cập nhật thống kê theo close_type
                if close_type not in stats['positions_by_close_type']:
                    stats['positions_by_close_type'][close_type] = 0
                
                stats['positions_by_close_type'][close_type] += 1
                
                # Kiểm tra trailing stop thành công
                if position_data.get('trailing_active', False) and close_type == 'trailing_stop':
                    stats['successful_trails'] += 1
                    stats['positions_by_regime'][regime]['successful_trails'] += 1
                    stats['positions_by_symbol'][symbol]['successful_trails'] += 1
                    
                    # Tính profit saved
                    direction = position_data.get('direction', 'long')
                    highest_price = position_data.get('highest_price', 0)
                    lowest_price = position_data.get('lowest_price', 0)
                    entry_price = position_data.get('entry_price', 0)
                    stop_price = position_data.get('trailing_stop_price', 0)
                    
                    if direction == 'long' and highest_price and entry_price:
                        max_profit = (highest_price - entry_price) / entry_price * 100
                        actual_profit = (stop_price - entry_price) / entry_price * 100
                        profit_saved = max_profit - actual_profit
                        stats['profit_saved'] += profit_saved
                    elif direction == 'short' and lowest_price and entry_price:
                        max_profit = (entry_price - lowest_price) / entry_price * 100
                        actual_profit = (entry_price - stop_price) / entry_price * 100
                        profit_saved = max_profit - actual_profit
                        stats['profit_saved'] += profit_saved
                
                # Thu thập trail percentages
                trail_percentages.append(
                    self.trail_percentages.get(
                        regime, 
                        self.trail_percentages.get('default', 0.3)
                    )
                )
                
                # Cập nhật avg_profit
                if position_data.get('final_profit_percentage') is not None:
                    profit = position_data['final_profit_percentage']
                    
                    # Symbol
                    current_avg = stats['positions_by_symbol'][symbol]['avg_profit']
                    current_count = stats['positions_by_symbol'][symbol]['count']
                    stats['positions_by_symbol'][symbol]['avg_profit'] = \
                        (current_avg * (current_count - 1) + profit) / current_count
                    
                    # Regime
                    current_avg = stats['positions_by_regime'][regime]['avg_profit']
                    current_count = stats['positions_by_regime'][regime]['count']
                    stats['positions_by_regime'][regime]['avg_profit'] = \
                        (current_avg * (current_count - 1) + profit) / current_count
                
            except Exception as e:
                logger.error(f"Lỗi khi đọc file {file_path}: {str(e)}")
        
        # Tính trung bình trail percentage
        if trail_percentages:
            stats['avg_trail_percentage'] = sum(trail_percentages) / len(trail_percentages)
        
        return stats

# Hàm chạy demo nếu chạy trực tiếp
if __name__ == "__main__":
    class MockAPIClient:
        def create_order(self, **kwargs):
            print(f"Mock API: Tạo lệnh với tham số {kwargs}")
            return {"orderId": "123456", "status": "SUCCESS", **kwargs}
            
        def get_klines(self, **kwargs):
            # Tạo dữ liệu giả
            import random
            import time
            
            now = time.time() * 1000  # ms
            klines = []
            
            base_price = 50000  # Giá cơ sở
            
            for i in range(kwargs.get('limit', 100)):
                # [timestamp, open, high, low, close, volume, ...]
                timestamp = now - (kwargs.get('limit', 100) - i) * 60 * 60 * 1000  # 1h interval
                close = base_price + random.uniform(-1000, 1000)
                klines.append([
                    timestamp,
                    close - random.uniform(-100, 100),  # open
                    close + random.uniform(0, 200),  # high
                    close - random.uniform(0, 200),  # low
                    close,  # close
                    random.uniform(100, 1000)  # volume
                ])
            
            return klines
    
    # Tạo mock API client
    mock_api = MockAPIClient()
    
    # Khởi tạo trailing stop manager
    manager = EnhancedTrailingStopManager(api_client=mock_api)
    
    # Demo với BTCUSDT
    print("\n=== Demo với BTCUSDT ===")
    
    # Đăng ký vị thế
    tracking_id = manager.register_position(
        symbol="BTCUSDT",
        order_id="12345",
        entry_price=50000,
        position_size=0.1,
        direction="long",
        stop_loss_price=49000
    )
    
    print(f"Đã đăng ký vị thế BTCUSDT với ID: {tracking_id}")
    
    # Cập nhật giá để thử trailing stop
    print("\nCập nhật giá tăng dần...")
    
    for i in range(10):
        price = 50000 + (i+1) * 200  # Tăng 200 mỗi lần
        print(f"Cập nhật giá BTCUSDT: {price}")
        manager.update_price("BTCUSDT", price)
        
        # Lấy thông tin vị thế
        position = manager.get_position_info(tracking_id)
        print(f"  - Profit: {position['profit_percentage']:.2f}%")
        print(f"  - Trailing active: {position['trailing_active']}")
        if position['trailing_active']:
            print(f"  - Trailing stop: {position['trailing_stop_price']}")
        print()
    
    # Cập nhật giá giảm để kích hoạt trailing stop
    print("\nCập nhật giá giảm để kích hoạt trailing stop...")
    
    # Lấy trailing stop price hiện tại
    position = manager.get_position_info(tracking_id)
    if position and position['trailing_active']:
        trailing_price = position['trailing_stop_price']
        
        # Cập nhật giá sát trailing stop
        price = trailing_price + 50
        print(f"Cập nhật giá BTCUSDT: {price}")
        manager.update_price("BTCUSDT", price)
        
        # Kích hoạt trailing stop
        price = trailing_price - 10
        print(f"Cập nhật giá BTCUSDT: {price} (dưới trailing stop {trailing_price})")
        manager.update_price("BTCUSDT", price)
    
    # Kiểm tra active positions
    active_positions = manager.get_active_positions()
    print(f"\nVị thế hiện tại: {len(active_positions)}")
    
    # Lấy thống kê hiệu suất
    stats = manager.get_performance_stats()
    print("\nThống kê hiệu suất:")
    print(f"Tổng số vị thế: {stats['total_positions']}")
    print(f"Trailing stop thành công: {stats['successful_trails']}")
    print(f"Profit saved: {stats['profit_saved']:.2f}%")
    
    print("\nHoàn thành demo EnhancedTrailingStopManager!")