#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quản lý đa vị thế (Multi-Position Manager)

Module này cung cấp các công cụ để quản lý nhiều vị thế đồng thời, 
tự động phân bổ vốn dựa trên hiệu suất quá khứ và kiểm soát rủi ro tổng thể.
"""

import os
import json
import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('multi_position_manager')

class MultiPositionManager:
    """
    Quản lý nhiều vị thế đồng thời với phân bổ vốn động và kiểm soát rủi ro
    """
    
    def __init__(self, config_path: str = 'configs/high_risk_multi_position_config.json'):
        """
        Khởi tạo quản lý đa vị thế
        
        Args:
            config_path (str): Đường dẫn tới file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Dữ liệu vị thế hiện tại
        self.active_positions = {}
        self.position_history = []
        
        # Hiệu suất theo coin/timeframe
        self.performance_data = {}
        
        # Phân bổ vốn hiện tại
        self.current_allocation = {}
        
        # Giới hạn mở vị thế
        self.position_limits = self.config.get('risk_config', {}).get('position_limits', {})
        self.max_positions = self.position_limits.get('max_positions', 10)
        self.max_positions_per_coin = self.position_limits.get('max_positions_per_coin', 3)
        
        # Mức kiểm soát drawdown
        self.drawdown_levels = self.config.get('risk_config', {}).get('max_drawdown', {})
        self.drawdown_warning = self.drawdown_levels.get('warning', 25.0)
        self.drawdown_reduce = self.drawdown_levels.get('reduce_size', 30.0)
        self.drawdown_stop = self.drawdown_levels.get('stop_trading', 35.0)
        
        # Thời gian quan trọng
        self.trading_windows = self.config.get('trading_windows', {})
        
        # Tải dữ liệu vị thế hiện tại nếu có
        self._load_active_positions()
        
        # Tính toán phân bổ vốn ban đầu
        self._calculate_initial_allocation()
        
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        default_config = {
            "risk_config": {
                "risk_levels": {
                    "default": 25.0,
                    "high": 30.0,
                    "medium": 20.0,
                    "low": 15.0
                },
                "max_drawdown": {
                    "warning": 25.0,
                    "reduce_size": 30.0,
                    "stop_trading": 35.0
                },
                "position_limits": {
                    "max_positions": 10,
                    "max_positions_per_coin": 3,
                    "max_correlated_positions": 5
                }
            },
            "capital_allocation": {
                "btc": 0.4,
                "eth": 0.3,
                "tier1_alts": 0.2,
                "opportunity": 0.1,
                "tier1_coins": ["SOL", "BNB", "LINK"],
                "tier2_coins": ["DOT", "ADA", "AVAX", "MATIC"]
            },
            "timeframe_allocation": {
                "1d": 0.4,
                "4h": 0.4,
                "1h": 0.2
            }
        }
        
        # Kiểm tra file cấu hình tồn tại
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình từ {self.config_path}: {e}")
                return default_config
        else:
            # Tạo file cấu hình mặc định
            try:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"Đã tạo cấu hình mặc định tại {self.config_path}")
            except Exception as e:
                logger.error(f"Lỗi khi tạo cấu hình mặc định: {e}")
            
            return default_config
            
    def _load_active_positions(self):
        """
        Tải thông tin vị thế đang mở từ file lưu trữ
        """
        try:
            if os.path.exists('active_positions.json'):
                with open('active_positions.json', 'r') as f:
                    self.active_positions = json.load(f)
                logger.info(f"Đã tải {len(self.active_positions)} vị thế đang mở từ active_positions.json")
        except Exception as e:
            logger.error(f"Lỗi khi tải vị thế đang mở: {e}")
            self.active_positions = {}
    
    def _save_active_positions(self):
        """
        Lưu thông tin vị thế đang mở ra file
        """
        try:
            with open('active_positions.json', 'w') as f:
                json.dump(self.active_positions, f, indent=4)
            logger.info(f"Đã lưu {len(self.active_positions)} vị thế đang mở vào active_positions.json")
        except Exception as e:
            logger.error(f"Lỗi khi lưu vị thế đang mở: {e}")
    
    def _calculate_initial_allocation(self):
        """
        Tính toán phân bổ vốn ban đầu theo cấu hình
        """
        capital_allocation = self.config.get('capital_allocation', {})
        
        # Phân bổ theo loại coin
        self.current_allocation = {
            'by_coin': {
                'BTC': capital_allocation.get('btc', 0.4),
                'ETH': capital_allocation.get('eth', 0.3)
            },
            'by_timeframe': self.config.get('timeframe_allocation', {
                '1d': 0.4,
                '4h': 0.4,
                '1h': 0.2
            })
        }
        
        # Phân bổ cho các altcoin tier 1
        tier1_coins = capital_allocation.get('tier1_coins', [])
        tier1_allocation = capital_allocation.get('tier1_alts', 0.2)
        
        if tier1_coins:
            per_coin_allocation = tier1_allocation / len(tier1_coins)
            for coin in tier1_coins:
                self.current_allocation['by_coin'][coin] = per_coin_allocation
        
        # Dự phòng cơ hội
        self.current_allocation['opportunity'] = capital_allocation.get('opportunity', 0.1)
        
        logger.info(f"Đã tính toán phân bổ vốn ban đầu: {self.current_allocation}")
        
    def update_performance_data(self, performance_history: Dict):
        """
        Cập nhật dữ liệu hiệu suất theo coin/timeframe
        
        Args:
            performance_history (Dict): Lịch sử hiệu suất theo coin/timeframe
        """
        self.performance_data = performance_history
        self._adjust_allocation_by_performance()
        
    def _adjust_allocation_by_performance(self):
        """
        Điều chỉnh phân bổ vốn theo hiệu suất gần đây
        """
        if not self.performance_data:
            logger.info("Không có dữ liệu hiệu suất để điều chỉnh phân bổ vốn")
            return
        
        # Kiểm tra cài đặt điều chỉnh động
        dynamic_config = self.config.get('risk_management', {}).get('dynamic_sizing', {})
        if not dynamic_config.get('enabled', True):
            logger.info("Tính năng điều chỉnh phân bổ vốn động đã bị tắt")
            return
        
        # Lấy các tham số từ cấu hình
        lookback = dynamic_config.get('performance_lookback', 20)
        adjustment_factor = dynamic_config.get('adjustment_factor', 0.2)
        
        # Tính hiệu suất trung bình
        avg_performance = {}
        for coin, data in self.performance_data.items():
            if 'profit_pct' in data:
                avg_performance[coin] = data['profit_pct']
        
        if not avg_performance:
            return
        
        # Tính hiệu suất trung bình của tất cả các coin
        all_coin_avg = sum(avg_performance.values()) / len(avg_performance)
        
        # Điều chỉnh phân bổ vốn theo hiệu suất
        new_allocation = {}
        for coin, perf in avg_performance.items():
            if coin in self.current_allocation['by_coin']:
                # Điều chỉnh phân bổ dựa trên hiệu suất tương đối
                relative_perf = perf / all_coin_avg if all_coin_avg > 0 else 1.0
                adjustment = (relative_perf - 1.0) * adjustment_factor
                
                # Giới hạn điều chỉnh
                adjustment = max(min(adjustment, 0.1), -0.1)
                
                # Phân bổ mới
                new_allocation[coin] = self.current_allocation['by_coin'][coin] * (1.0 + adjustment)
        
        # Chuẩn hóa phân bổ để tổng = 1.0 (trừ phần opportunity)
        opportunity = self.current_allocation.get('opportunity', 0.1)
        total_allocation = sum(new_allocation.values())
        
        for coin in new_allocation:
            new_allocation[coin] = new_allocation[coin] / total_allocation * (1.0 - opportunity)
        
        # Cập nhật phân bổ
        self.current_allocation['by_coin'] = new_allocation
        self.current_allocation['opportunity'] = opportunity
        
        logger.info(f"Đã điều chỉnh phân bổ vốn theo hiệu suất: {self.current_allocation}")
    
    def get_optimal_trade_size(self, symbol: str, timeframe: str, 
                              account_balance: float, risk_pct: float) -> float:
        """
        Tính toán kích thước giao dịch tối ưu dựa trên phân bổ vốn và mức rủi ro
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            account_balance (float): Số dư tài khoản
            risk_pct (float): Phần trăm rủi ro
            
        Returns:
            float: Kích thước giao dịch tối ưu (dollar value)
        """
        # Kiểm tra xem có vượt quá giới hạn vị thế không
        if not self.can_open_new_position(symbol):
            return 0.0
        
        # Kiểm tra trạng thái drawdown
        current_drawdown = self.calculate_current_drawdown()
        if current_drawdown >= self.drawdown_stop:
            logger.warning(f"Không mở vị thế mới do drawdown ({current_drawdown}%) vượt quá ngưỡng dừng ({self.drawdown_stop}%)")
            return 0.0
        elif current_drawdown >= self.drawdown_reduce:
            # Giảm kích thước vị thế khi drawdown cao
            risk_pct = risk_pct * 0.5
            logger.warning(f"Giảm 50% kích thước vị thế do drawdown cao ({current_drawdown}%)")
        
        # Lấy phân bổ vốn cho coin và timeframe
        coin = symbol.replace("USDT", "")
        coin_allocation = self.current_allocation.get('by_coin', {}).get(coin, 0.05)  # mặc định 5%
        timeframe_allocation = self.current_allocation.get('by_timeframe', {}).get(timeframe, 0.33)  # mặc định 33%
        
        # Kiểm tra có phải thời gian ưu tiên không
        time_boost = self._check_priority_trading_window(timeframe)
        
        # Tính toán kích thước giao dịch
        allocated_balance = account_balance * coin_allocation * timeframe_allocation
        position_size = allocated_balance * (risk_pct / 100)
        
        # Áp dụng boost nếu trong thời gian ưu tiên
        if time_boost > 1.0:
            position_size = position_size * time_boost
            logger.info(f"Áp dụng boost {time_boost}x cho giao dịch trong thời gian ưu tiên")
        
        return position_size
    
    def _check_priority_trading_window(self, timeframe: str) -> float:
        """
        Kiểm tra xem hiện tại có phải là thời gian giao dịch ưu tiên không
        
        Args:
            timeframe (str): Khung thời gian giao dịch
            
        Returns:
            float: Hệ số boost (>1.0 nếu là thời gian ưu tiên, 1.0 nếu không phải)
        """
        # Kiểm tra tính năng có được bật không
        boost_config = self.config.get('market_hours_boost', {})
        if not boost_config.get('enabled', False):
            return 1.0
        
        boost_factor = boost_config.get('boost_factor', 1.25)
        
        # Lấy thời gian hiện tại
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        # Kiểm tra các cửa sổ thời gian giao dịch
        for window_name, window in self.trading_windows.items():
            start_hour = window.get('start_hour', 0)
            start_minute = window.get('start_minute', 0)
            end_hour = window.get('end_hour', 0)
            end_minute = window.get('end_minute', 0)
            priority = window.get('priority', 'medium')
            
            # Kiểm tra xem thời gian hiện tại có nằm trong cửa sổ không
            is_in_window = False
            
            # Nếu cùng ngày
            if start_hour < end_hour or (start_hour == end_hour and start_minute < end_minute):
                is_in_window = (current_hour > start_hour or (current_hour == start_hour and current_minute >= start_minute)) and \
                              (current_hour < end_hour or (current_hour == end_hour and current_minute <= end_minute))
            else:  # Xuyên ngày (qua 00:00)
                is_in_window = (current_hour > start_hour or (current_hour == start_hour and current_minute >= start_minute)) or \
                              (current_hour < end_hour or (current_hour == end_hour and current_minute <= end_minute))
            
            if is_in_window:
                # Áp dụng boost theo độ ưu tiên
                if priority == 'high':
                    return boost_factor
                elif priority == 'medium':
                    return boost_factor * 0.8
                else:  # low
                    return boost_factor * 0.6
        
        return 1.0
    
    def can_open_new_position(self, symbol: str) -> bool:
        """
        Kiểm tra xem có thể mở vị thế mới cho cặp tiền này không
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            bool: True nếu có thể mở vị thế mới, False nếu không
        """
        # Kiểm tra tổng số vị thế đang mở
        total_positions = len(self.active_positions)
        if total_positions >= self.max_positions:
            logger.warning(f"Đã đạt giới hạn tổng số vị thế ({self.max_positions})")
            return False
        
        # Đếm số vị thế hiện tại của cặp tiền này
        symbol_positions = sum(1 for pos in self.active_positions.values() if pos.get('symbol') == symbol)
        if symbol_positions >= self.max_positions_per_coin:
            logger.warning(f"Đã đạt giới hạn vị thế cho {symbol} ({self.max_positions_per_coin})")
            return False
        
        # Kiểm tra tương quan và vị thế đối trọng
        # TODO: Implement correlation check
        
        return True
    
    def calculate_current_drawdown(self) -> float:
        """
        Tính toán drawdown hiện tại dựa trên các vị thế đang mở
        
        Returns:
            float: Drawdown hiện tại (phần trăm)
        """
        # Tạm thời giả định drawdown = 0
        # TODO: Calculate actual drawdown from account data
        return 0.0
    
    def register_position(self, position_data: Dict) -> None:
        """
        Đăng ký một vị thế mới vào hệ thống
        
        Args:
            position_data (Dict): Thông tin vị thế
        """
        # Tạo ID vị thế nếu chưa có
        if 'position_id' not in position_data:
            position_id = f"{position_data.get('symbol')}_{int(time.time())}"
            position_data['position_id'] = position_id
        else:
            position_id = position_data['position_id']
        
        # Thêm thời gian vào
        if 'open_time' not in position_data:
            position_data['open_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Đăng ký vị thế
        self.active_positions[position_id] = position_data
        
        # Lưu thông tin vị thế
        self._save_active_positions()
        
        logger.info(f"Đã đăng ký vị thế mới: {position_id} - {position_data.get('symbol')} {position_data.get('direction')} {position_data.get('size')}")
    
    def close_position(self, position_id: str, close_data: Dict) -> None:
        """
        Đóng một vị thế và cập nhật lịch sử
        
        Args:
            position_id (str): ID vị thế cần đóng
            close_data (Dict): Thông tin đóng vị thế (giá, P/L, thời gian)
        """
        if position_id not in self.active_positions:
            logger.warning(f"Không tìm thấy vị thế {position_id} để đóng")
            return
        
        # Lấy thông tin vị thế
        position = self.active_positions[position_id]
        
        # Cập nhật thông tin đóng
        position.update(close_data)
        
        # Thêm thời gian đóng nếu chưa có
        if 'close_time' not in position:
            position['close_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Thêm vào lịch sử
        self.position_history.append(position)
        
        # Xóa khỏi danh sách vị thế đang mở
        del self.active_positions[position_id]
        
        # Lưu thông tin vị thế
        self._save_active_positions()
        
        # Lưu lịch sử giao dịch
        self._save_position_history()
        
        logger.info(f"Đã đóng vị thế: {position_id} - {position.get('symbol')} {position.get('direction')} với P/L: {close_data.get('pnl', 'N/A')}")
    
    def _save_position_history(self):
        """
        Lưu lịch sử giao dịch ra file
        """
        try:
            with open('position_history.json', 'w') as f:
                json.dump(self.position_history, f, indent=4)
            logger.info(f"Đã lưu {len(self.position_history)} giao dịch vào position_history.json")
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử giao dịch: {e}")
    
    def get_trailing_stop_parameters(self, symbol: str, entry_price: float, 
                                    current_price: float, direction: str) -> Dict:
        """
        Tính toán tham số trailing stop tối ưu dựa trên cấu hình và diễn biến giá
        
        Args:
            symbol (str): Mã cặp tiền
            entry_price (float): Giá entry
            current_price (float): Giá hiện tại
            direction (str): Hướng vị thế (long/short)
            
        Returns:
            Dict: Các tham số trailing stop
        """
        # Lấy cấu hình trailing stop
        trail_config = self.config.get('risk_management', {}).get('trailing_stop', {})
        activation = trail_config.get('activation_threshold', 2.5)  # Phần trăm
        step = trail_config.get('step_percent', 0.5)
        acceleration = trail_config.get('acceleration_factor', 0.02)
        max_factor = trail_config.get('maximum_factor', 0.2)
        
        # Tính profit hiện tại
        if direction.lower() == 'long':
            current_profit_pct = (current_price - entry_price) / entry_price * 100
        else:  # short
            current_profit_pct = (entry_price - current_price) / entry_price * 100
        
        # Kiểm tra đã đạt ngưỡng kích hoạt chưa
        if current_profit_pct < activation:
            return {
                'should_activate': False,
                'activation_threshold': activation,
                'current_profit_pct': current_profit_pct,
                'step_percent': step
            }
        
        # Tính số bước profit đã đạt được
        steps_achieved = int((current_profit_pct - activation) / step) + 1
        
        # Tính trailing_stop_distance với hệ số tăng tốc
        acceleration_factor = min(steps_achieved * acceleration, max_factor)
        trailing_distance = step * (1.0 - acceleration_factor)
        
        # Tính giá trailing stop
        if direction.lower() == 'long':
            trailing_stop_price = current_price * (1.0 - trailing_distance / 100)
        else:  # short
            trailing_stop_price = current_price * (1.0 + trailing_distance / 100)
        
        return {
            'should_activate': True,
            'activation_threshold': activation,
            'current_profit_pct': current_profit_pct,
            'steps_achieved': steps_achieved,
            'acceleration_factor': acceleration_factor,
            'trailing_distance': trailing_distance,
            'trailing_stop_price': trailing_stop_price
        }
    
    def update_trailing_stops(self, current_prices: Dict) -> List[str]:
        """
        Cập nhật trailing stop cho tất cả các vị thế đang mở
        
        Args:
            current_prices (Dict): Giá hiện tại của các cặp tiền
            
        Returns:
            List[str]: Danh sách ID vị thế cần đóng do hit trailing stop
        """
        positions_to_close = []
        
        for position_id, position in self.active_positions.items():
            symbol = position.get('symbol')
            direction = position.get('direction')
            entry_price = position.get('entry_price')
            
            # Bỏ qua nếu thiếu thông tin
            if not all([symbol, direction, entry_price]):
                continue
            
            # Kiểm tra giá hiện tại
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            
            # Kiểm tra trailing stop hiện tại
            has_trailing = position.get('has_trailing_stop', False)
            current_trailing_price = position.get('trailing_stop_price')
            
            # Tính toán tham số trailing stop mới
            trail_params = self.get_trailing_stop_parameters(
                symbol, entry_price, current_price, direction
            )
            
            # Nếu chưa có trailing stop và đạt ngưỡng kích hoạt
            if not has_trailing and trail_params.get('should_activate', False):
                position['has_trailing_stop'] = True
                position['trailing_stop_price'] = trail_params.get('trailing_stop_price')
                position['trailing_activation_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                logger.info(f"Kích hoạt trailing stop cho {position_id} tại {position['trailing_stop_price']}")
            
            # Nếu đã có trailing stop, kiểm tra xem có cần cập nhật không
            elif has_trailing and trail_params.get('should_activate', False):
                new_trail_price = trail_params.get('trailing_stop_price')
                
                # Chỉ cập nhật nếu trailing stop mới có lợi hơn
                if direction.lower() == 'long' and new_trail_price > current_trailing_price:
                    position['trailing_stop_price'] = new_trail_price
                    logger.info(f"Cập nhật trailing stop cho {position_id} lên {new_trail_price}")
                elif direction.lower() == 'short' and new_trail_price < current_trailing_price:
                    position['trailing_stop_price'] = new_trail_price
                    logger.info(f"Cập nhật trailing stop cho {position_id} xuống {new_trail_price}")
            
            # Kiểm tra xem đã hit trailing stop chưa
            if has_trailing:
                if (direction.lower() == 'long' and current_price <= position['trailing_stop_price']) or \
                   (direction.lower() == 'short' and current_price >= position['trailing_stop_price']):
                    # Thêm vào danh sách cần đóng
                    positions_to_close.append(position_id)
                    logger.info(f"Vị thế {position_id} hit trailing stop tại {current_price}")
        
        # Lưu lại các thay đổi
        self._save_active_positions()
        
        return positions_to_close