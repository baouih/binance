#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý rủi ro
"""

import os
import json
import time
import math
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union, Any

# Thiết lập logging
logger = logging.getLogger("risk_manager")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class RiskManager:
    """
    Lớp quản lý rủi ro giao dịch
    """
    def __init__(self, position_manager, risk_config=None):
        """
        Khởi tạo quản lý rủi ro
        
        :param position_manager: Đối tượng PositionManager
        :param risk_config: Cấu hình rủi ro
        """
        self.position_manager = position_manager
        self.risk_config = risk_config or {}
        
        # Cấu hình mặc định
        self.default_risk_config = {
            "risk_percentage": 0.01,  # 1% rủi ro trên mỗi giao dịch
            "max_positions": 5,  # Số lượng vị thế tối đa
            "leverage": 5,  # Đòn bẩy mặc định
            "position_size_percentage": 0.1,  # 10% số dư cho mỗi vị thế
            "partial_take_profit": {
                "enabled": False,
                "levels": [
                    {"percentage": 30, "profit_percentage": 2},
                    {"percentage": 30, "profit_percentage": 5},
                    {"percentage": 40, "profit_percentage": 10}
                ]
            },
            "stop_loss_percentage": 0.015,  # 1.5% Stop Loss
            "take_profit_percentage": 0.03,  # 3% Take Profit
            "trailing_stop": {
                "enabled": True,
                "activation_percentage": 2,
                "trailing_percentage": 1.5
            },
            "trading_hours_restriction": {
                "enabled": False,
                "trading_hours": ["09:00-12:00", "14:00-21:00"]
            }
        }
        
        # Áp dụng cấu hình mặc định nếu không có cấu hình
        for key, value in self.default_risk_config.items():
            if key not in self.risk_config:
                self.risk_config[key] = value
    
    def calculate_position_size(self, account_balance: float, symbol: str = "BTCUSDT") -> float:
        """
        Tính toán kích thước vị thế dựa trên cấu hình rủi ro
        
        :param account_balance: Số dư tài khoản
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :return: Kích thước vị thế
        """
        # Lấy cấu hình
        position_size_percentage = self.risk_config.get("position_size_percentage", 0.1)
        
        # Tính toán kích thước vị thế
        position_size_usd = account_balance * position_size_percentage
        
        try:
            # Lấy giá hiện tại
            if self.position_manager and self.position_manager.client:
                ticker = self.position_manager.client.futures_symbol_ticker(symbol=symbol)
                current_price = float(ticker["price"])
                
                # Tính toán kích thước vị thế
                position_size = position_size_usd / current_price
                
                # Làm tròn kích thước vị thế
                if "BTC" in symbol:
                    position_size = round(position_size, 3)  # 3 chữ số thập phân cho BTC
                elif "ETH" in symbol:
                    position_size = round(position_size, 3)  # 3 chữ số thập phân cho ETH
                else:
                    position_size = round(position_size, 2)  # 2 chữ số thập phân cho các cặp khác
                
                return position_size
            else:
                logger.error("Không thể lấy giá hiện tại, sử dụng giá trị mặc định")
                return 0.01  # Giá trị mặc định nhỏ
        except Exception as e:
            logger.error(f"Lỗi khi tính toán kích thước vị thế: {str(e)}")
            return 0.01  # Giá trị mặc định nhỏ
    
    def calculate_sl_tp(self, symbol: str, side: str, entry_price: float) -> Dict[str, float]:
        """
        Tính toán giá Stop Loss và Take Profit dựa trên cấu hình rủi ro
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param side: Hướng giao dịch (LONG hoặc SHORT)
        :param entry_price: Giá vào lệnh
        :return: Dict với SL và TP
        """
        # Lấy cấu hình
        sl_percentage = self.risk_config.get("stop_loss_percentage", 0.015)
        tp_percentage = self.risk_config.get("take_profit_percentage", 0.03)
        
        # Tính toán SL và TP
        if side == "LONG":
            stop_loss = entry_price * (1 - sl_percentage)
            take_profit = entry_price * (1 + tp_percentage)
        else:  # SHORT
            stop_loss = entry_price * (1 + sl_percentage)
            take_profit = entry_price * (1 - tp_percentage)
        
        # Làm tròn giá trị
        stop_loss = round(stop_loss, 2)
        take_profit = round(take_profit, 2)
        
        return {"stop_loss": stop_loss, "take_profit": take_profit}
    
    def check_risk_limits(self) -> Dict[str, Any]:
        """
        Kiểm tra các giới hạn rủi ro
        
        :return: Dict với thông tin giới hạn rủi ro
        """
        # Lấy các vị thế hiện tại
        positions = self.position_manager.get_all_positions() if self.position_manager else []
        
        # Số lượng vị thế tối đa
        max_positions = self.risk_config.get("max_positions", 5)
        positions_count = len(positions)
        positions_limit_reached = positions_count >= max_positions
        
        # Tính tổng rủi ro
        total_risk = 0
        for position in positions:
            # Tính rủi ro cho mỗi vị thế (giả sử rủi ro = số dư * position_size_percentage)
            position_risk = self.risk_config.get("position_size_percentage", 0.1)
            total_risk += position_risk
        
        # Giới hạn rủi ro tổng thể
        max_risk = 0.5  # 50% rủi ro tổng thể tối đa
        risk_limit_reached = total_risk >= max_risk
        
        # Kiểm tra giờ giao dịch
        trading_hours_restriction = self.risk_config.get("trading_hours_restriction", {"enabled": False})
        outside_trading_hours = False
        
        if trading_hours_restriction.get("enabled", False):
            # Lấy danh sách giờ giao dịch
            trading_hours = trading_hours_restriction.get("trading_hours", ["09:00-12:00", "14:00-21:00"])
            
            # Kiểm tra xem có trong giờ giao dịch không
            current_time = datetime.now().time()
            in_trading_hours = False
            
            for time_range in trading_hours:
                # Phân tích giờ giao dịch
                start_time_str, end_time_str = time_range.split("-")
                start_hour, start_minute = map(int, start_time_str.split(":"))
                end_hour, end_minute = map(int, end_time_str.split(":"))
                
                start_time = datetime.strptime(f"{start_hour}:{start_minute}", "%H:%M").time()
                end_time = datetime.strptime(f"{end_hour}:{end_minute}", "%H:%M").time()
                
                # Kiểm tra xem thời gian hiện tại có trong khoảng giờ giao dịch không
                if start_time <= current_time <= end_time:
                    in_trading_hours = True
                    break
            
            outside_trading_hours = not in_trading_hours
        
        return {
            "positions_count": positions_count,
            "max_positions": max_positions,
            "positions_limit_reached": positions_limit_reached,
            "total_risk": total_risk,
            "max_risk": max_risk,
            "risk_limit_reached": risk_limit_reached,
            "outside_trading_hours": outside_trading_hours
        }
    
    def validate_new_position(self, symbol: str, side: str, amount: float) -> Tuple[bool, str]:
        """
        Kiểm tra tính hợp lệ của một vị thế mới
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param side: Hướng giao dịch (LONG hoặc SHORT)
        :param amount: Kích thước vị thế
        :return: Tuple (is_valid, reason)
        """
        # Kiểm tra các giới hạn rủi ro
        risk_limits = self.check_risk_limits()
        
        # Kiểm tra số lượng vị thế
        if risk_limits["positions_limit_reached"]:
            return (False, f"Đã đạt giới hạn số lượng vị thế ({risk_limits['positions_count']}/{risk_limits['max_positions']})")
        
        # Kiểm tra giới hạn rủi ro tổng thể
        if risk_limits["risk_limit_reached"]:
            return (False, f"Đã đạt giới hạn rủi ro tổng thể ({risk_limits['total_risk']:.2f}/{risk_limits['max_risk']:.2f})")
        
        # Kiểm tra giờ giao dịch
        if risk_limits["outside_trading_hours"]:
            return (False, "Ngoài giờ giao dịch được cấu hình")
        
        # Kiểm tra vị thế đã tồn tại
        positions = self.position_manager.get_all_positions() if self.position_manager else []
        for position in positions:
            if position["symbol"] == symbol:
                return (False, f"Đã có vị thế {position['side']} trên {symbol}")
        
        # Kiểm tra kích thước vị thế
        if amount <= 0:
            return (False, "Kích thước vị thế phải lớn hơn 0")
        
        # Kiểm tra cặp được hỗ trợ
        supported_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT"]
        if symbol not in supported_symbols:
            return (False, f"Cặp {symbol} không được hỗ trợ")
        
        # Kiểm tra hướng giao dịch
        if side not in ["LONG", "SHORT"]:
            return (False, f"Hướng giao dịch {side} không hợp lệ")
        
        return (True, "Vị thế hợp lệ")
    
    def validate_sl_tp(self, symbol: str, side: str, entry_price: float, stop_loss: float, take_profit: float) -> Tuple[bool, str]:
        """
        Kiểm tra tính hợp lệ của Stop Loss và Take Profit
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param side: Hướng giao dịch (LONG hoặc SHORT)
        :param entry_price: Giá vào lệnh
        :param stop_loss: Giá Stop Loss
        :param take_profit: Giá Take Profit
        :return: Tuple (is_valid, reason)
        """
        # Kiểm tra giá trị hợp lệ
        if stop_loss <= 0 or take_profit <= 0:
            return (False, "Giá Stop Loss và Take Profit phải lớn hơn 0")
        
        # Kiểm tra SL và TP dựa trên hướng giao dịch
        if side == "LONG":
            if stop_loss >= entry_price:
                return (False, f"Stop Loss ({stop_loss}) phải nhỏ hơn giá vào ({entry_price}) đối với lệnh LONG")
            
            if take_profit <= entry_price:
                return (False, f"Take Profit ({take_profit}) phải lớn hơn giá vào ({entry_price}) đối với lệnh LONG")
        else:  # SHORT
            if stop_loss <= entry_price:
                return (False, f"Stop Loss ({stop_loss}) phải lớn hơn giá vào ({entry_price}) đối với lệnh SHORT")
            
            if take_profit >= entry_price:
                return (False, f"Take Profit ({take_profit}) phải nhỏ hơn giá vào ({entry_price}) đối với lệnh SHORT")
        
        # Kiểm tra tỷ lệ rủi ro/phần thưởng
        if side == "LONG":
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # SHORT
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        if risk_reward_ratio < 1.5:
            return (False, f"Tỷ lệ rủi ro/phần thưởng ({risk_reward_ratio:.2f}) quá thấp, tối thiểu là 1.5")
        
        return (True, "Stop Loss và Take Profit hợp lệ")
    
    def manage_trailing_stops(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Quản lý Trailing Stop cho các vị thế
        
        :param positions: Danh sách các vị thế
        :return: Danh sách các cập nhật Trailing Stop
        """
        # Kiểm tra xem Trailing Stop có được bật không
        trailing_stop_config = self.risk_config.get("trailing_stop", {"enabled": True})
        
        if not trailing_stop_config.get("enabled", True):
            return []
        
        # Lấy thông số Trailing Stop
        activation_percentage = trailing_stop_config.get("activation_percentage", 2)
        trailing_percentage = trailing_stop_config.get("trailing_percentage", 1.5)
        
        updates = []
        
        for position in positions:
            # Lấy thông tin vị thế
            symbol = position["symbol"]
            side = position["side"]
            entry_price = position["entry_price"]
            current_price = position["mark_price"]
            stop_loss = position.get("stop_loss")
            
            # Kiểm tra xem có cần áp dụng Trailing Stop không
            if stop_loss is None:
                continue
            
            # Tính toán lợi nhuận hiện tại
            if side == "LONG":
                profit_percentage = (current_price / entry_price - 1) * 100
                
                # Kiểm tra xem lợi nhuận có đủ để kích hoạt Trailing Stop không
                if profit_percentage >= activation_percentage:
                    # Tính toán Stop Loss mới
                    new_stop_loss = current_price * (1 - trailing_percentage / 100)
                    
                    # Chỉ cập nhật nếu Stop Loss mới cao hơn Stop Loss hiện tại
                    if new_stop_loss > stop_loss:
                        updates.append({
                            "symbol": symbol,
                            "side": side,
                            "old_stop_loss": stop_loss,
                            "new_stop_loss": new_stop_loss,
                            "profit_percentage": profit_percentage
                        })
            else:  # SHORT
                profit_percentage = (1 - current_price / entry_price) * 100
                
                # Kiểm tra xem lợi nhuận có đủ để kích hoạt Trailing Stop không
                if profit_percentage >= activation_percentage:
                    # Tính toán Stop Loss mới
                    new_stop_loss = current_price * (1 + trailing_percentage / 100)
                    
                    # Chỉ cập nhật nếu Stop Loss mới thấp hơn Stop Loss hiện tại
                    if new_stop_loss < stop_loss:
                        updates.append({
                            "symbol": symbol,
                            "side": side,
                            "old_stop_loss": stop_loss,
                            "new_stop_loss": new_stop_loss,
                            "profit_percentage": profit_percentage
                        })
        
        return updates
    
    def get_partial_tp_levels(self, symbol: str, side: str, entry_price: float) -> List[Dict[str, Any]]:
        """
        Lấy các mức chốt lời một phần
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param side: Hướng giao dịch (LONG hoặc SHORT)
        :param entry_price: Giá vào lệnh
        :return: Danh sách các mức chốt lời một phần
        """
        # Kiểm tra xem chốt lời một phần có được bật không
        partial_tp_config = self.risk_config.get("partial_take_profit", {"enabled": False})
        
        if not partial_tp_config.get("enabled", False):
            return []
        
        # Lấy các mức chốt lời
        levels = partial_tp_config.get("levels", [])
        
        # Tính toán giá chốt lời cho mỗi mức
        partial_tp_levels = []
        
        for level in levels:
            percentage = level.get("percentage", 0)
            profit_percentage = level.get("profit_percentage", 0)
            
            # Tính toán giá chốt lời
            if side == "LONG":
                price = entry_price * (1 + profit_percentage / 100)
            else:  # SHORT
                price = entry_price * (1 - profit_percentage / 100)
            
            partial_tp_levels.append({
                "symbol": symbol,
                "side": side,
                "percentage": percentage,
                "profit_percentage": profit_percentage,
                "price": price
            })
        
        return partial_tp_levels
    
    def get_risk_level_name(self) -> str:
        """
        Lấy tên mức độ rủi ro
        
        :return: Tên mức độ rủi ro
        """
        risk_percentage = self.risk_config.get("risk_percentage", 0.01)
        
        if risk_percentage <= 0.01:
            return "Thấp"
        elif risk_percentage <= 0.02:
            return "Trung bình thấp"
        elif risk_percentage <= 0.03:
            return "Trung bình"
        elif risk_percentage <= 0.05:
            return "Trung bình cao"
        else:
            return "Cao"
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """
        Lấy tóm tắt cấu hình rủi ro
        
        :return: Dict với tóm tắt cấu hình rủi ro
        """
        return {
            "risk_level": self.get_risk_level_name(),
            "risk_percentage": self.risk_config.get("risk_percentage", 0.01) * 100,
            "max_positions": self.risk_config.get("max_positions", 5),
            "leverage": self.risk_config.get("leverage", 5),
            "position_size_percentage": self.risk_config.get("position_size_percentage", 0.1) * 100,
            "stop_loss_percentage": self.risk_config.get("stop_loss_percentage", 0.015) * 100,
            "take_profit_percentage": self.risk_config.get("take_profit_percentage", 0.03) * 100,
            "trailing_stop_enabled": self.risk_config.get("trailing_stop", {}).get("enabled", True),
            "partial_tp_enabled": self.risk_config.get("partial_take_profit", {}).get("enabled", False),
            "trading_hours_restriction": self.risk_config.get("trading_hours_restriction", {}).get("enabled", False)
        }

# Hàm kiểm tra
def test_risk_manager():
    from position_manager import PositionManager
    
    # Thiết lập logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Cấu hình rủi ro
    risk_config = {
        "risk_percentage": 0.02,  # 2% rủi ro trên mỗi giao dịch
        "max_positions": 4,  # Số lượng vị thế tối đa
        "leverage": 10,  # Đòn bẩy mặc định
        "position_size_percentage": 0.15,  # 15% số dư cho mỗi vị thế
        "partial_take_profit": {
            "enabled": True,
            "levels": [
                {"percentage": 30, "profit_percentage": 2},
                {"percentage": 30, "profit_percentage": 5},
                {"percentage": 40, "profit_percentage": 10}
            ]
        },
        "stop_loss_percentage": 0.02,  # 2% Stop Loss
        "take_profit_percentage": 0.05,  # 5% Take Profit
        "trailing_stop": {
            "enabled": True,
            "activation_percentage": 2,
            "trailing_percentage": 1.5
        },
        "trading_hours_restriction": {
            "enabled": True,
            "trading_hours": ["00:00-23:59"]  # Giao dịch cả ngày
        }
    }
    
    # Tạo đối tượng PositionManager và RiskManager
    position_manager = PositionManager(testnet=True)
    risk_manager = RiskManager(position_manager, risk_config)
    
    # Hiển thị thông tin cấu hình rủi ro
    risk_summary = risk_manager.get_risk_summary()
    
    print("=== Cấu hình Rủi ro ===")
    print(f"Mức độ rủi ro: {risk_summary['risk_level']}")
    print(f"Rủi ro mỗi giao dịch: {risk_summary['risk_percentage']:.1f}%")
    print(f"Số lượng vị thế tối đa: {risk_summary['max_positions']}")
    print(f"Đòn bẩy mặc định: {risk_summary['leverage']}x")
    print(f"Phần trăm số dư cho mỗi vị thế: {risk_summary['position_size_percentage']:.1f}%")
    print(f"Stop Loss: {risk_summary['stop_loss_percentage']:.1f}%")
    print(f"Take Profit: {risk_summary['take_profit_percentage']:.1f}%")
    print(f"Trailing Stop: {'Bật' if risk_summary['trailing_stop_enabled'] else 'Tắt'}")
    print(f"Chốt lời một phần: {'Bật' if risk_summary['partial_tp_enabled'] else 'Tắt'}")
    print(f"Giới hạn giờ giao dịch: {'Bật' if risk_summary['trading_hours_restriction'] else 'Tắt'}")
    
    # Kiểm tra tính toán kích thước vị thế
    account_balance = 1000  # USD
    symbol = "BTCUSDT"
    position_size = risk_manager.calculate_position_size(account_balance, symbol)
    
    print("\n=== Tính toán Kích thước Vị thế ===")
    print(f"Số dư tài khoản: {account_balance} USD")
    print(f"Cặp giao dịch: {symbol}")
    print(f"Kích thước vị thế: {position_size}")
    
    # Kiểm tra tính toán SL và TP
    entry_price = 50000  # USD
    side = "LONG"
    sl_tp = risk_manager.calculate_sl_tp(symbol, side, entry_price)
    
    print("\n=== Tính toán Stop Loss và Take Profit ===")
    print(f"Cặp giao dịch: {symbol}")
    print(f"Hướng giao dịch: {side}")
    print(f"Giá vào lệnh: {entry_price} USD")
    print(f"Stop Loss: {sl_tp['stop_loss']} USD")
    print(f"Take Profit: {sl_tp['take_profit']} USD")
    
    # Kiểm tra các mức chốt lời một phần
    partial_tp_levels = risk_manager.get_partial_tp_levels(symbol, side, entry_price)
    
    print("\n=== Các mức Chốt lời một phần ===")
    for level in partial_tp_levels:
        print(f"Phần trăm: {level['percentage']}%, Lợi nhuận: {level['profit_percentage']}%, Giá: {level['price']} USD")
    
    # Kiểm tra giới hạn rủi ro
    risk_limits = risk_manager.check_risk_limits()
    
    print("\n=== Kiểm tra Giới hạn Rủi ro ===")
    print(f"Số lượng vị thế: {risk_limits['positions_count']}/{risk_limits['max_positions']}")
    print(f"Đạt giới hạn vị thế: {'Có' if risk_limits['positions_limit_reached'] else 'Không'}")
    print(f"Rủi ro tổng thể: {risk_limits['total_risk']:.2f}/{risk_limits['max_risk']:.2f}")
    print(f"Đạt giới hạn rủi ro: {'Có' if risk_limits['risk_limit_reached'] else 'Không'}")
    print(f"Ngoài giờ giao dịch: {'Có' if risk_limits['outside_trading_hours'] else 'Không'}")

if __name__ == "__main__":
    test_risk_manager()