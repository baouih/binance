#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý rủi ro cho hệ thống giao dịch
Quản lý rủi ro và cấu hình các thông số rủi ro khác nhau
"""

import os
import json
import logging
from datetime import datetime

# Cấu hình logging
logger = logging.getLogger("risk_manager")

class RiskManager:
    """
    Lớp quản lý rủi ro, cung cấp các phương thức
    để quản lý rủi ro trong giao dịch
    """
    
    def __init__(self, position_manager, risk_config=None):
        """
        Khởi tạo với position manager và cấu hình rủi ro
        
        :param position_manager: Đối tượng PositionManager để quản lý vị thế
        :param risk_config: Dict cấu hình rủi ro, nếu None sẽ tải từ file mặc định
        """
        self.position_manager = position_manager
        self.risk_config = risk_config or self.load_default_risk_config()
    
    def load_default_risk_config(self):
        """
        Tải cấu hình rủi ro mặc định
        
        :return: Dict cấu hình rủi ro
        """
        try:
            # Cấu hình rủi ro mặc định là 10%
            config_path = "risk_configs/risk_level_10.json"
            
            if not os.path.exists(config_path):
                # Nếu không tìm thấy, trả về giá trị cứng
                return {
                    "position_size_percent": 1,
                    "stop_loss_percent": 1,
                    "take_profit_percent": 2,
                    "leverage": 1,
                    "max_open_positions": 2,
                    "max_daily_trades": 5,
                    "risk_multipliers": {
                        "stop_loss_multiplier": 1.0,
                        "take_profit_multiplier": 1.0
                    }
                }
            
            with open(config_path, "r") as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro mặc định: {str(e)}")
            # Trả về cấu hình cứng nếu có lỗi
            return {
                "position_size_percent": 1,
                "stop_loss_percent": 1,
                "take_profit_percent": 2,
                "leverage": 1,
                "max_open_positions": 2,
                "max_daily_trades": 5,
                "risk_multipliers": {
                    "stop_loss_multiplier": 1.0,
                    "take_profit_multiplier": 1.0
                }
            }
    
    def load_risk_config(self, risk_level):
        """
        Tải cấu hình rủi ro theo mức độ
        
        :param risk_level: Mức độ rủi ro (10, 15, 20, 30)
        :return: Dict cấu hình rủi ro
        """
        try:
            config_path = f"risk_configs/risk_level_{risk_level}.json"
            
            if not os.path.exists(config_path):
                logger.warning(f"Không tìm thấy cấu hình rủi ro cho mức {risk_level}. Sử dụng mức mặc định 10.")
                return self.load_default_risk_config()
            
            with open(config_path, "r") as f:
                return json.load(f)
        
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro {risk_level}: {str(e)}")
            return self.load_default_risk_config()
    
    def apply_risk_config(self, risk_level):
        """
        Áp dụng cấu hình rủi ro
        
        :param risk_level: Mức độ rủi ro (10, 15, 20, 30)
        :return: Boolean thành công/thất bại
        """
        try:
            # Tải cấu hình rủi ro
            risk_config = self.load_risk_config(risk_level)
            
            # Cập nhật cấu hình cho RiskManager
            self.risk_config = risk_config
            
            # Cập nhật cấu hình cho PositionManager
            if self.position_manager:
                self.position_manager.risk_config = risk_config
            
            logger.info(f"Đã áp dụng cấu hình rủi ro mức {risk_level}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng cấu hình rủi ro {risk_level}: {str(e)}")
            return False
    
    def create_custom_risk_level(self, name, config):
        """
        Tạo cấu hình rủi ro tùy chỉnh
        
        :param name: Tên cấu hình
        :param config: Dict cấu hình rủi ro
        :return: Boolean thành công/thất bại
        """
        try:
            config_path = f"risk_configs/risk_level_{name}.json"
            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
            
            logger.info(f"Đã tạo cấu hình rủi ro tùy chỉnh: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo cấu hình rủi ro tùy chỉnh {name}: {str(e)}")
            return False
    
    def calculate_position_size(self, account_balance, symbol=None):
        """
        Tính toán kích thước vị thế dựa trên số dư tài khoản và cấu hình rủi ro
        
        :param account_balance: Số dư tài khoản
        :param symbol: Cặp tiền (nếu cần tính riêng cho từng cặp)
        :return: Kích thước vị thế (USDT)
        """
        # Lấy % kích thước vị thế từ cấu hình
        position_size_percent = self.risk_config.get("position_size_percent", 1)
        
        # Tính kích thước vị thế
        position_size = account_balance * (position_size_percent / 100)
        
        return position_size
    
    def calculate_sl_tp(self, symbol, side, entry_price):
        """
        Tính toán Stop Loss và Take Profit dựa trên cấu hình rủi ro
        
        :param symbol: Cặp tiền
        :param side: Hướng vị thế ("LONG" hoặc "SHORT")
        :param entry_price: Giá vào lệnh
        :return: Tuple (stop_loss, take_profit)
        """
        # Lấy % SL/TP từ cấu hình
        sl_percent = self.risk_config.get("stop_loss_percent", 1) / 100
        tp_percent = self.risk_config.get("take_profit_percent", 2) / 100
        
        # Áp dụng các hệ số nhân (nếu có)
        risk_multipliers = self.risk_config.get("risk_multipliers", {})
        sl_multiplier = risk_multipliers.get("stop_loss_multiplier", 1.0)
        tp_multiplier = risk_multipliers.get("take_profit_multiplier", 1.0)
        
        sl_percent *= sl_multiplier
        tp_percent *= tp_multiplier
        
        # Tính SL/TP dựa trên hướng vị thế
        if side == "LONG":
            stop_loss = entry_price * (1 - sl_percent)
            take_profit = entry_price * (1 + tp_percent)
        else:  # SHORT
            stop_loss = entry_price * (1 + sl_percent)
            take_profit = entry_price * (1 - tp_percent)
        
        return (stop_loss, take_profit)
    
    def check_risk_limits(self):
        """
        Kiểm tra các giới hạn rủi ro
        
        :return: Dict kết quả kiểm tra
        """
        try:
            # Lấy tất cả vị thế đang mở
            positions = self.position_manager.get_all_positions()
            
            # Lấy giới hạn từ cấu hình
            max_positions = self.risk_config.get("max_open_positions", 5)
            
            # Kiểm tra số lượng vị thế
            num_positions = len(positions)
            positions_limit_reached = num_positions >= max_positions
            
            # Tính tổng % margin đang sử dụng
            total_margin_percent = sum(abs(pos.get("profit_percent", 0)) for pos in positions)
            
            return {
                "positions_count": num_positions,
                "max_positions": max_positions,
                "positions_limit_reached": positions_limit_reached,
                "total_margin_percent": total_margin_percent
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra giới hạn rủi ro: {str(e)}")
            return {
                "error": str(e),
                "positions_count": 0,
                "max_positions": self.risk_config.get("max_open_positions", 5),
                "positions_limit_reached": False,
                "total_margin_percent": 0
            }
    
    def validate_new_position(self, symbol, side, amount):
        """
        Kiểm tra xem có thể mở vị thế mới không
        
        :param symbol: Cặp tiền
        :param side: Hướng vị thế
        :param amount: Số lượng (USDT)
        :return: Tuple (is_valid, message)
        """
        try:
            # Kiểm tra giới hạn rủi ro
            risk_limits = self.check_risk_limits()
            
            # Nếu đã đạt giới hạn vị thế
            if risk_limits["positions_limit_reached"]:
                return (False, f"Đã đạt giới hạn số lượng vị thế tối đa ({risk_limits['max_positions']})")
            
            # Kiểm tra xem đã có vị thế cho cặp tiền này chưa
            positions = self.position_manager.get_all_positions()
            for position in positions:
                if position["symbol"] == symbol:
                    # Nếu đã có vị thế LONG và muốn mở thêm LONG, hoặc ngược lại
                    if position["side"] == side:
                        return (False, f"Đã có vị thế {side} cho {symbol}. Không thể mở thêm vị thế cùng hướng.")
            
            # Các kiểm tra khác nếu cần
            
            return (True, "Có thể mở vị thế mới")
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra vị thế mới: {str(e)}")
            return (False, f"Lỗi khi kiểm tra: {str(e)}")

# Hàm để thử nghiệm module
def test_risk_manager():
    """Hàm kiểm tra chức năng của RiskManager"""
    # Cấu hình logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        from position_manager import PositionManager
        
        # Khởi tạo position manager
        position_manager = PositionManager(testnet=True)
        
        # Khởi tạo risk manager
        risk_manager = RiskManager(position_manager)
        
        # Kiểm tra tải cấu hình
        print("=== Cấu hình rủi ro mặc định ===")
        default_config = risk_manager.load_default_risk_config()
        print(json.dumps(default_config, indent=2))
        
        # Kiểm tra tải cấu hình cho các mức rủi ro khác
        risk_levels = [10, 15, 20, 30]
        for level in risk_levels:
            print(f"\n=== Cấu hình rủi ro mức {level}% ===")
            config = risk_manager.load_risk_config(level)
            print(json.dumps(config, indent=2))
        
        # Kiểm tra tính toán kích thước vị thế
        account_balance = 1000  # USDT
        for level in risk_levels:
            risk_manager.apply_risk_config(level)
            position_size = risk_manager.calculate_position_size(account_balance)
            print(f"\nMức rủi ro {level}%:")
            print(f"  - Số dư tài khoản: {account_balance} USDT")
            print(f"  - Kích thước vị thế: {position_size:.2f} USDT")
            
            # Kiểm tra tính SL/TP
            symbol = "BTCUSDT"
            entry_price = 50000
            for side in ["LONG", "SHORT"]:
                sl, tp = risk_manager.calculate_sl_tp(symbol, side, entry_price)
                print(f"  - {side} - Entry: {entry_price}, SL: {sl:.2f}, TP: {tp:.2f}")
        
    except Exception as e:
        print(f"Lỗi khi test RiskManager: {str(e)}")

if __name__ == "__main__":
    test_risk_manager()