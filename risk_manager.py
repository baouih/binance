#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý rủi ro
"""

import os
import json
import logging
import datetime
import traceback
from typing import Dict, List, Union, Tuple, Any, Optional

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("risk_manager")

class RiskManager:
    """Quản lý rủi ro cho giao dịch"""
    
    def __init__(self, position_manager=None, risk_config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo Risk Manager
        
        :param position_manager: Đối tượng PositionManager
        :param risk_config: Cấu hình rủi ro
        """
        self.position_manager = position_manager
        self.risk_config = risk_config or self.load_default_config()
        
        logger.info("Đã khởi tạo Risk Manager")
    
    def load_default_config(self) -> Dict[str, Any]:
        """
        Tải cấu hình rủi ro mặc định
        
        :return: Dict với cấu hình rủi ro
        """
        try:
            config_file = "risk_configs/desktop_risk_config.json"
            
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình rủi ro từ {config_file}")
                return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro: {str(e)}", exc_info=True)
        
        # Trả về cấu hình mặc định nếu không thể tải từ file
        return {
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
    
    def calculate_position_size(self, account_balance: float, symbol: str) -> float:
        """
        Tính toán kích thước vị thế dựa trên rủi ro
        
        :param account_balance: Số dư tài khoản
        :param symbol: Cặp giao dịch
        :return: Kích thước vị thế
        """
        try:
            # Lấy phần trăm rủi ro và phần trăm số dư
            risk_percentage = self.risk_config.get("risk_percentage", 0.01)
            position_size_percentage = self.risk_config.get("position_size_percentage", 0.1)
            
            # Tính toán số tiền tối đa cho mỗi giao dịch
            max_position_value = account_balance * position_size_percentage
            
            # Lấy giá hiện tại
            current_price = 0
            if self.position_manager and self.position_manager.client:
                symbol_ticker = self.position_manager.client.futures_symbol_ticker(symbol=symbol)
                current_price = float(symbol_ticker["price"])
            
            if current_price <= 0:
                logger.error(f"Giá hiện tại không hợp lệ: {current_price}")
                return 0.001  # Giá trị nhỏ nhất để tránh lỗi
            
            # Tính toán kích thước vị thế
            position_size = max_position_value / current_price
            
            # Làm tròn kích thước vị thế
            if "BTC" in symbol:
                position_size = round(position_size, 3)  # 3 số thập phân cho BTC
            else:
                position_size = round(position_size, 2)  # 2 số thập phân cho các coin khác
            
            logger.info(f"Kích thước vị thế đã tính toán: {position_size} {symbol.replace('USDT', '')}")
            return position_size
        
        except Exception as e:
            logger.error(f"Lỗi khi tính toán kích thước vị thế: {str(e)}", exc_info=True)
            return 0.001  # Giá trị nhỏ nhất để tránh lỗi
    
    def calculate_sl_tp(self, symbol: str, side: str, entry_price: float) -> Dict[str, float]:
        """
        Tính toán Stop Loss và Take Profit
        
        :param symbol: Cặp giao dịch
        :param side: Hướng giao dịch (LONG/SHORT)
        :param entry_price: Giá vào lệnh
        :return: Dict với Stop Loss và Take Profit
        """
        try:
            # Lấy phần trăm Stop Loss và Take Profit
            sl_percentage = self.risk_config.get("stop_loss_percentage", 0.015)
            tp_percentage = self.risk_config.get("take_profit_percentage", 0.03)
            
            # Tính toán SL và TP dựa trên hướng
            if side == "LONG":
                stop_loss = round(entry_price * (1 - sl_percentage), 2)
                take_profit = round(entry_price * (1 + tp_percentage), 2)
            else:  # SHORT
                stop_loss = round(entry_price * (1 + sl_percentage), 2)
                take_profit = round(entry_price * (1 - tp_percentage), 2)
            
            logger.info(f"SL/TP đã tính toán cho {symbol} {side}: SL={stop_loss}, TP={take_profit}")
            return {"stop_loss": stop_loss, "take_profit": take_profit}
        
        except Exception as e:
            logger.error(f"Lỗi khi tính toán SL/TP: {str(e)}", exc_info=True)
            # Trả về giá trị mặc định để tránh lỗi
            return {"stop_loss": entry_price * 0.98, "take_profit": entry_price * 1.02}
    
    def validate_new_position(self, symbol: str, side: str, amount: float) -> Tuple[bool, str]:
        """
        Kiểm tra tính hợp lệ của vị thế mới
        
        :param symbol: Cặp giao dịch
        :param side: Hướng giao dịch (LONG/SHORT)
        :param amount: Kích thước vị thế
        :return: Tuple (hợp lệ, lý do)
        """
        try:
            # Kiểm tra số lượng vị thế tối đa
            max_positions = self.risk_config.get("max_positions", 5)
            
            if self.position_manager:
                positions = self.position_manager.get_all_positions()
                
                if len(positions) >= max_positions:
                    return False, f"Đã đạt số lượng vị thế tối đa ({max_positions})"
            
            # Kiểm tra giờ giao dịch
            trading_hours_restriction = self.risk_config.get("trading_hours_restriction", {})
            
            if trading_hours_restriction.get("enabled", False):
                current_time = datetime.datetime.now().time()
                trading_hours = trading_hours_restriction.get("trading_hours", [])
                
                in_trading_hour = False
                for time_range in trading_hours:
                    start_time_str, end_time_str = time_range.split("-")
                    start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
                    end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()
                    
                    if start_time <= current_time <= end_time:
                        in_trading_hour = True
                        break
                
                if not in_trading_hour:
                    return False, "Ngoài giờ giao dịch cho phép"
            
            # Kiểm tra vị thế đã tồn tại chưa
            if self.position_manager:
                positions = self.position_manager.get_all_positions()
                
                for position in positions:
                    if position.get("symbol") == symbol:
                        existing_side = position.get("side")
                        
                        if existing_side != side:
                            return False, f"Đã có vị thế {existing_side} trên {symbol}"
            
            # Kiểm tra kích thước vị thế
            if amount <= 0:
                return False, "Kích thước vị thế phải lớn hơn 0"
            
            # Nếu tất cả kiểm tra đều qua
            return True, "Vị thế hợp lệ"
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra tính hợp lệ của vị thế: {str(e)}", exc_info=True)
            return False, f"Lỗi: {str(e)}"
    
    def validate_sl_tp(self, symbol: str, side: str, entry_price: float, 
                        stop_loss: float, take_profit: float) -> Tuple[bool, str]:
        """
        Kiểm tra tính hợp lệ của Stop Loss và Take Profit
        
        :param symbol: Cặp giao dịch
        :param side: Hướng giao dịch (LONG/SHORT)
        :param entry_price: Giá vào lệnh
        :param stop_loss: Giá Stop Loss
        :param take_profit: Giá Take Profit
        :return: Tuple (hợp lệ, lý do)
        """
        try:
            if side == "LONG":
                # Đối với LONG, SL phải nhỏ hơn giá vào và TP phải lớn hơn giá vào
                if stop_loss >= entry_price:
                    return False, "Stop Loss phải nhỏ hơn giá vào với vị thế LONG"
                
                if take_profit <= entry_price:
                    return False, "Take Profit phải lớn hơn giá vào với vị thế LONG"
            else:  # SHORT
                # Đối với SHORT, SL phải lớn hơn giá vào và TP phải nhỏ hơn giá vào
                if stop_loss <= entry_price:
                    return False, "Stop Loss phải lớn hơn giá vào với vị thế SHORT"
                
                if take_profit >= entry_price:
                    return False, "Take Profit phải nhỏ hơn giá vào với vị thế SHORT"
            
            # Kiểm tra khoảng cách Stop Loss
            sl_percentage = abs(stop_loss - entry_price) / entry_price
            min_sl_percentage = 0.005  # 0.5% tối thiểu
            
            if sl_percentage < min_sl_percentage:
                return False, f"Stop Loss quá gần giá vào, tối thiểu {min_sl_percentage*100}%"
            
            # Kiểm tra khoảng cách Take Profit
            tp_percentage = abs(take_profit - entry_price) / entry_price
            min_tp_percentage = 0.01  # 1% tối thiểu
            
            if tp_percentage < min_tp_percentage:
                return False, f"Take Profit quá gần giá vào, tối thiểu {min_tp_percentage*100}%"
            
            # Nếu tất cả kiểm tra đều qua
            return True, "SL/TP hợp lệ"
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra tính hợp lệ của SL/TP: {str(e)}", exc_info=True)
            return False, f"Lỗi: {str(e)}"
    
    def apply_trailing_stop(self, symbol: str, side: str, entry_price: float, 
                           current_price: float, position_id: str = None) -> bool:
        """
        Áp dụng Trailing Stop
        
        :param symbol: Cặp giao dịch
        :param side: Hướng giao dịch (LONG/SHORT)
        :param entry_price: Giá vào lệnh
        :param current_price: Giá hiện tại
        :param position_id: ID vị thế (tùy chọn)
        :return: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra xem Trailing Stop có được bật không
            trailing_stop = self.risk_config.get("trailing_stop", {})
            
            if not trailing_stop.get("enabled", False):
                return False
            
            # Lấy các thông số Trailing Stop
            activation_percentage = trailing_stop.get("activation_percentage", 2) / 100
            trailing_percentage = trailing_stop.get("trailing_percentage", 1.5) / 100
            
            # Tính toán mức kích hoạt
            activation_price = 0
            if side == "LONG":
                activation_price = entry_price * (1 + activation_percentage)
                
                # Kiểm tra xem giá hiện tại có vượt qua mức kích hoạt không
                if current_price >= activation_price:
                    # Tính toán Stop Loss mới
                    new_stop_loss = current_price * (1 - trailing_percentage)
                    
                    # Cập nhật Stop Loss
                    if self.position_manager:
                        result = self.position_manager.update_sl_tp(symbol, position_id, new_stop_loss, None)
                        
                        if result.get("status") == "success":
                            logger.info(f"Đã cập nhật Trailing Stop cho {symbol} {side}: {new_stop_loss}")
                            return True
            else:  # SHORT
                activation_price = entry_price * (1 - activation_percentage)
                
                # Kiểm tra xem giá hiện tại có vượt qua mức kích hoạt không
                if current_price <= activation_price:
                    # Tính toán Stop Loss mới
                    new_stop_loss = current_price * (1 + trailing_percentage)
                    
                    # Cập nhật Stop Loss
                    if self.position_manager:
                        result = self.position_manager.update_sl_tp(symbol, position_id, new_stop_loss, None)
                        
                        if result.get("status") == "success":
                            logger.info(f"Đã cập nhật Trailing Stop cho {symbol} {side}: {new_stop_loss}")
                            return True
            
            return False
        
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng Trailing Stop: {str(e)}", exc_info=True)
            return False
    
    def check_risk_exposure(self) -> Dict[str, Any]:
        """
        Kiểm tra mức độ rủi ro hiện tại
        
        :return: Dict với thông tin rủi ro
        """
        try:
            # Khởi tạo kết quả
            result = {
                "total_risk": 0,
                "max_risk": self.risk_config.get("risk_percentage", 0.01) * 100,
                "position_count": 0,
                "max_positions": self.risk_config.get("max_positions", 5),
                "highest_risk_position": None,
                "risk_level": "Thấp"
            }
            
            # Lấy danh sách vị thế
            positions = []
            if self.position_manager:
                positions = self.position_manager.get_all_positions()
            
            result["position_count"] = len(positions)
            
            # Tính toán tổng rủi ro
            total_risk = 0
            highest_risk = 0
            highest_risk_position = None
            
            for position in positions:
                symbol = position.get("symbol", "")
                size = position.get("size", 0)
                entry_price = position.get("entry_price", 0)
                stop_loss = position.get("stop_loss", 0)
                
                # Bỏ qua nếu không có Stop Loss
                if stop_loss == 0:
                    continue
                
                # Tính toán rủi ro cho vị thế này
                risk_percentage = abs(entry_price - stop_loss) / entry_price
                position_risk = risk_percentage * size * entry_price
                
                # Cập nhật tổng rủi ro
                total_risk += position_risk
                
                # Kiểm tra xem có phải vị thế có rủi ro cao nhất không
                if position_risk > highest_risk:
                    highest_risk = position_risk
                    highest_risk_position = {
                        "symbol": symbol,
                        "risk": position_risk,
                        "risk_percentage": risk_percentage * 100
                    }
            
            result["total_risk"] = total_risk
            result["highest_risk_position"] = highest_risk_position
            
            # Xác định mức độ rủi ro
            if total_risk <= result["max_risk"] * 0.5:
                result["risk_level"] = "Thấp"
            elif total_risk <= result["max_risk"]:
                result["risk_level"] = "Trung bình"
            else:
                result["risk_level"] = "Cao"
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra mức độ rủi ro: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "risk_level": "Không xác định"
            }
    
    def save_config(self, config_file: str = "risk_configs/desktop_risk_config.json") -> bool:
        """
        Lưu cấu hình rủi ro
        
        :param config_file: Đường dẫn file cấu hình
        :return: True nếu thành công, False nếu thất bại
        """
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            # Lưu cấu hình
            with open(config_file, "w") as f:
                json.dump(self.risk_config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình rủi ro vào {config_file}")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình rủi ro: {str(e)}", exc_info=True)
            return False