#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo chương trình thử nghiệm Trailing Stop nâng cao

Script này cho phép người dùng thử nghiệm các chiến lược trailing stop khác nhau
với dữ liệu giả lập, giúp hiểu rõ hơn cách thức hoạt động của từng chiến lược.
"""

import os
import time
import json
import logging
import datetime
import random
from typing import Dict, List, Any

from advanced_trailing_stop import (
    AdvancedTrailingStop,
    PercentageTrailingStop,
    AbsoluteTrailingStop,
    ATRTrailingStop,
    ParabolicSARTrailingStop,
    StepTrailingStop
)

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('demo_trailing_stop')

class DemoDataCache:
    """Lớp cache dữ liệu đơn giản cho demo"""
    
    def __init__(self):
        self.data = {}
    
    def set(self, category: str, key: str, value: Any) -> None:
        """Lưu dữ liệu vào cache"""
        if category not in self.data:
            self.data[category] = {}
        self.data[category][key] = value
    
    def get(self, category: str, key: str, default: Any = None) -> Any:
        """Lấy dữ liệu từ cache"""
        return self.data.get(category, {}).get(key, default)

class MarketSimulator:
    """Lớp mô phỏng thị trường với nhiều mô hình biến động giá khác nhau"""
    
    def __init__(self, symbol: str, start_price: float):
        """
        Khởi tạo mô phỏng thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            start_price (float): Giá ban đầu
        """
        self.symbol = symbol
        self.current_price = start_price
        self.prices = [start_price]
        self.time = datetime.datetime.now()
        
        # Tạo cache dữ liệu
        self.data_cache = DemoDataCache()
        
        # Các tham số cho mô hình biến động
        self.trend = 0.0  # -1.0 (giảm mạnh) đến 1.0 (tăng mạnh)
        self.volatility = 0.005  # 0.001 (ít biến động) đến 0.05 (biến động mạnh)
        self.random_factor = 0.3  # 0.1 (ít ngẫu nhiên) đến 0.9 (nhiều ngẫu nhiên)
    
    def set_market_conditions(self, trend: float, volatility: float, random_factor: float) -> None:
        """
        Đặt điều kiện thị trường
        
        Args:
            trend (float): Xu hướng từ -1.0 đến 1.0
            volatility (float): Biến động từ 0.001 đến 0.05
            random_factor (float): Độ ngẫu nhiên từ 0.1 đến 0.9
        """
        self.trend = max(-1.0, min(1.0, trend))
        self.volatility = max(0.001, min(0.05, volatility))
        self.random_factor = max(0.1, min(0.9, random_factor))
    
    def update_price(self) -> float:
        """
        Cập nhật giá theo mô hình biến động
        
        Returns:
            float: Giá mới
        """
        # Tính toán các thành phần biến động
        trend_component = self.trend * self.volatility * self.current_price
        random_component = (random.random() * 2 - 1) * self.volatility * self.current_price * self.random_factor
        
        # Cập nhật giá
        price_change = trend_component + random_component
        self.current_price += price_change
        
        # Đảm bảo giá không âm
        self.current_price = max(0.01, self.current_price)
        
        # Lưu giá vào lịch sử
        self.prices.append(self.current_price)
        
        # Cập nhật thời gian
        self.time += datetime.timedelta(minutes=1)
        
        # Lưu vào cache
        self.data_cache.set('market_data', f'{self.symbol}_price', self.current_price)
        
        # Tính ATR và lưu vào cache
        if len(self.prices) >= 14:
            tr_values = []
            for i in range(1, 14):
                high = max(self.prices[-i], self.prices[-i-1])
                low = min(self.prices[-i], self.prices[-i-1])
                tr = high - low
                tr_values.append(tr)
            
            atr = sum(tr_values) / len(tr_values)
            self.data_cache.set('indicators', f'{self.symbol}_1h_atr_14', atr)
        
        return self.current_price

class DemoTrailingStop:
    """Lớp demo các chiến lược trailing stop"""
    
    def __init__(self):
        """Khởi tạo demo"""
        # Tạo cache dữ liệu
        self.data_cache = DemoDataCache()
        
        # Các vị thế demo
        self.positions = {}
        
        # Các chiến lược trailing stop
        self.strategies = {
            "percentage": AdvancedTrailingStop("percentage", self.data_cache, {
                "activation_percent": 1.0,
                "callback_percent": 0.5
            }),
            "absolute": AdvancedTrailingStop("absolute", self.data_cache, {
                "activation_amount": 50.0,
                "callback_amount": 20.0
            }),
            "atr": AdvancedTrailingStop("atr", self.data_cache, {
                "atr_multiplier": 2.0,
                "atr_period": 14
            }),
            "psar": AdvancedTrailingStop("psar", self.data_cache, {
                "acceleration_factor": 0.02,
                "acceleration_max": 0.2
            }),
            "step": AdvancedTrailingStop("step", self.data_cache, {
                "profit_steps": [1.0, 2.0, 3.0, 5.0],
                "callback_steps": [0.5, 0.8, 1.0, 1.5]
            })
        }
        
        # Mô phỏng thị trường
        self.market = MarketSimulator("BTCUSDT", 60000)
    
    def create_test_position(self, symbol: str, side: str, entry_price: float,
                           quantity: float, leverage: int, strategy: str) -> Dict:
        """
        Tạo một vị thế test
        
        Args:
            symbol (str): Mã cặp tiền
            side (str): Hướng giao dịch (LONG/SHORT)
            entry_price (float): Giá vào lệnh
            quantity (float): Số lượng
            leverage (int): Đòn bẩy
            strategy (str): Loại chiến lược trailing stop
            
        Returns:
            Dict: Vị thế đã tạo
        """
        position = {
            'id': f"{symbol}_{side}_{int(time.time())}",
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'quantity': quantity,
            'leverage': leverage,
            'entry_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Khởi tạo với chiến lược trailing stop
        if strategy in self.strategies:
            ts = self.strategies[strategy]
            position = ts.initialize_position(position)
            self.positions[position['id']] = position
            return position
        else:
            logger.error(f"Chiến lược không hợp lệ: {strategy}")
            return None
    
    def update_positions(self, current_price: float) -> Dict:
        """
        Cập nhật tất cả các vị thế với giá hiện tại
        
        Args:
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Kết quả cập nhật
        """
        result = {
            "updated": 0,
            "closed": 0,
            "active": len(self.positions)
        }
        
        # Cập nhật từng vị thế
        positions_to_close = []
        for position_id, position in self.positions.items():
            # Lấy chiến lược tương ứng
            strategy_type = position.get('trailing_type', 'percentage')
            ts = self.strategies.get(strategy_type, self.strategies['percentage'])
            
            # Cập nhật trailing stop
            position = ts.update_trailing_stop(position, current_price)
            self.positions[position_id] = position
            result["updated"] += 1
            
            # Kiểm tra điều kiện đóng vị thế
            should_close, reason = ts.check_stop_condition(position, current_price)
            if should_close:
                positions_to_close.append((position_id, reason))
        
        # Đóng các vị thế cần đóng
        for position_id, reason in positions_to_close:
            position = self.positions[position_id]
            
            # Tính lợi nhuận
            profit_amount, profit_percent = self._calculate_profit(position, current_price)
            
            # Hiển thị thông tin đóng vị thế
            logger.info(f"Đóng vị thế {position['symbol']} {position['side']} tại {current_price:.2f}")
            logger.info(f"Lợi nhuận: {profit_amount:.2f} USD ({profit_percent:.2f}%)")
            logger.info(f"Lý do: {reason}")
            
            # Xóa khỏi danh sách
            del self.positions[position_id]
            result["closed"] += 1
            result["active"] = len(self.positions)
        
        return result
    
    def _calculate_profit(self, position: Dict, current_price: float) -> tuple:
        """
        Tính lợi nhuận của vị thế
        
        Args:
            position (Dict): Vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            tuple: (Lợi nhuận tuyệt đối, Lợi nhuận phần trăm)
        """
        entry_price = position['entry_price']
        quantity = position['quantity']
        leverage = position['leverage']
        side = position['side']
        
        if side == 'LONG':
            profit_amount = (current_price - entry_price) * quantity * leverage
            profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
        else:  # SHORT
            profit_amount = (entry_price - current_price) * quantity * leverage
            profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
        
        return profit_amount, profit_percent
    
    def print_position_status(self, position_id: str, current_price: float) -> None:
        """
        In trạng thái của vị thế
        
        Args:
            position_id (str): ID của vị thế
            current_price (float): Giá hiện tại
        """
        position = self.positions.get(position_id)
        if not position:
            logger.error(f"Không tìm thấy vị thế {position_id}")
            return
        
        # Tính lợi nhuận
        profit_amount, profit_percent = self._calculate_profit(position, current_price)
        
        # Thông tin trailing stop
        ts_activated = position.get('trailing_activated', False)
        ts_price = position.get('trailing_stop')
        ts_type = position.get('trailing_type', 'percentage')
        
        # In thông tin
        print(f"\n=== Trạng thái vị thế {position['symbol']} {position['side']} ===")
        print(f"Giá vào: {position['entry_price']:.2f}")
        print(f"Giá hiện tại: {current_price:.2f}")
        print(f"P&L: {profit_amount:.2f} USD ({profit_percent:.2f}%)")
        print(f"Trailing Stop: {'Đã kích hoạt' if ts_activated else 'Chưa kích hoạt'}")
        if ts_price is not None:
            print(f"Giá Trailing Stop: {ts_price:.2f}")
        print(f"Loại Trailing Stop: {ts_type}")
        
        # Thông tin thêm tùy theo loại trailing stop
        if ts_type == 'percentage':
            print(f"Kích hoạt: {position.get('trailing_activation_percent', 1.0)}%, "
                f"Callback: {position.get('trailing_callback_percent', 0.5)}%")
        elif ts_type == 'absolute':
            print(f"Kích hoạt: {position.get('trailing_activation_amount', 50.0)} USD, "
                f"Callback: {position.get('trailing_callback_amount', 20.0)} USD")
        elif ts_type == 'atr':
            print(f"Hệ số ATR: {position.get('trailing_atr_multiplier', 2.0)}, "
                f"ATR: {position.get('atr_value', 0):.2f}")
        elif ts_type == 'psar':
            print(f"PSAR: {position.get('psar_value', 0):.2f}, "
                f"AF: {position.get('psar_af', 0.02):.3f}")
        elif ts_type == 'step':
            current_step = position.get('trailing_current_step', 0)
            print(f"Bước hiện tại: {current_step}, "
                f"Profit Steps: {position.get('trailing_profit_steps', [])}, "
                f"Callback Steps: {position.get('trailing_callback_steps', [])}")
    
    def run_simulation(self, num_steps: int = 100, interval: float = 0.1,
                     market_trend: float = 0.2, market_volatility: float = 0.01,
                     positions_to_create: List[Dict] = None) -> None:
        """
        Chạy mô phỏng với các vị thế và thị trường
        
        Args:
            num_steps (int): Số bước mô phỏng
            interval (float): Thời gian giữa các bước (giây)
            market_trend (float): Xu hướng thị trường
            market_volatility (float): Biến động thị trường
            positions_to_create (List[Dict]): Các vị thế cần tạo
        """
        # Đặt điều kiện thị trường
        self.market.set_market_conditions(market_trend, market_volatility, 0.3)
        
        # Tạo các vị thế ban đầu
        if positions_to_create:
            for pos_info in positions_to_create:
                self.create_test_position(**pos_info)
        
        # Nếu không có vị thế nào, tạo mặc định
        if not self.positions:
            self.create_test_position(
                symbol="BTCUSDT",
                side="LONG",
                entry_price=self.market.current_price,
                quantity=0.1,
                leverage=10,
                strategy="percentage"
            )
        
        print(f"\n=== Bắt đầu mô phỏng với {len(self.positions)} vị thế ===")
        print(f"Xu hướng: {market_trend:.2f}, Biến động: {market_volatility:.4f}")
        print(f"Giá ban đầu: {self.market.current_price:.2f}")
        
        # Chạy mô phỏng
        for step in range(num_steps):
            # Cập nhật giá
            current_price = self.market.update_price()
            
            # Cập nhật các vị thế
            result = self.update_positions(current_price)
            
            # Hiển thị định kỳ
            if step % 10 == 0 or result["closed"] > 0:
                print(f"\nBước {step+1}/{num_steps}, Giá: {current_price:.2f}")
                print(f"Vị thế active: {result['active']}, Đã đóng: {result['closed']}")
                
                # Hiển thị từng vị thế
                for position_id in list(self.positions.keys()):
                    self.print_position_status(position_id, current_price)
            
            # Dừng nếu không còn vị thế nào
            if not self.positions:
                print("\nTất cả vị thế đã đóng, kết thúc mô phỏng")
                break
            
            # Dừng giữa các bước
            time.sleep(interval)
        
        print("\n=== Kết thúc mô phỏng ===")
        print(f"Giá cuối: {self.market.current_price:.2f}")
        print(f"Vị thế còn lại: {len(self.positions)}")


def main():
    """Hàm chính để chạy demo"""
    print("\n=== DEMO TRAILING STOP NÂNG CAO ===\n")
    
    # Tạo đối tượng demo
    demo = DemoTrailingStop()
    
    # Chuẩn bị một số vị thế để demo
    positions_to_create = [
        {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_price": 60000,
            "quantity": 0.1,
            "leverage": 10,
            "strategy": "percentage"
        },
        {
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "entry_price": 3000,
            "quantity": 1.0,
            "leverage": 5,
            "strategy": "atr"
        },
        {
            "symbol": "BNBUSDT",
            "side": "LONG",
            "entry_price": 600,
            "quantity": 0.5,
            "leverage": 10,
            "strategy": "step"
        },
        {
            "symbol": "SOLUSDT",
            "side": "SHORT",
            "entry_price": 150,
            "quantity": 2.0,
            "leverage": 3,
            "strategy": "psar"
        }
    ]
    
    # Chạy mô phỏng với thị trường tăng (+0.3)
    print("\n>>> KỊCH BẢN THỊ TRƯỜNG TĂNG:")
    demo.run_simulation(
        num_steps=100,
        interval=0.05,
        market_trend=0.3,
        market_volatility=0.01,
        positions_to_create=positions_to_create
    )
    
    # Đợi người dùng xem kết quả
    input("\nNhấn Enter để tiếp tục với kịch bản thị trường giảm...")
    
    # Tạo đối tượng demo mới cho thị trường giảm
    demo = DemoTrailingStop()
    
    # Chạy mô phỏng với thị trường giảm (-0.3)
    print("\n>>> KỊCH BẢN THỊ TRƯỜNG GIẢM:")
    demo.run_simulation(
        num_steps=100,
        interval=0.05,
        market_trend=-0.3,
        market_volatility=0.01,
        positions_to_create=positions_to_create
    )
    
    # Đợi người dùng xem kết quả
    input("\nNhấn Enter để tiếp tục với kịch bản thị trường biến động lớn...")
    
    # Tạo đối tượng demo mới cho thị trường biến động
    demo = DemoTrailingStop()
    
    # Chạy mô phỏng với thị trường biến động lớn
    print("\n>>> KỊCH BẢN THỊ TRƯỜNG BIẾN ĐỘNG LỚN:")
    demo.run_simulation(
        num_steps=100,
        interval=0.05,
        market_trend=0.0,
        market_volatility=0.03,
        positions_to_create=positions_to_create
    )
    
    print("\nCảm ơn bạn đã dùng thử tính năng Trailing Stop nâng cao!")


if __name__ == "__main__":
    main()