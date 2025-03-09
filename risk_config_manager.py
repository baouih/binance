#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quản lý cấu hình rủi ro cho hệ thống giao dịch
Hỗ trợ các mức rủi ro: 2.0%, 2.5%, 3.0%, 4.0%, 5.0%
"""

import os
import json
import logging

class RiskConfigManager:
    """Quản lý cấu hình rủi ro cho hệ thống"""
    
    @staticmethod
    def load_risk_config(symbol):
        """Tải cấu hình rủi ro cho một cặp giao dịch"""
        config_path = f"configs/risk_config_{symbol.lower()}.json"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Lỗi khi tải cấu hình rủi ro từ {config_path}: {str(e)}")
        
        # Trả về cấu hình mặc định
        return {
            "risk_percentage": 0.02,  # 2% vốn cho mỗi giao dịch
            "max_active_positions": 3,
            "max_daily_trades": 10,
            "max_daily_loss": 5,  # 5% tổng vốn
            "stop_trading_on_drawdown": 10  # 10% drawdown
        }
        
    @staticmethod
    def generate_risk_config(symbol, risk_percentage=0.02):
        """Tạo cấu hình rủi ro với mức rủi ro tùy chỉnh"""
        # Cấu hình cơ bản
        config = {
            "risk_percentage": risk_percentage,
            "max_active_positions": 3,
            "max_daily_trades": 10,
            "max_daily_loss": risk_percentage * 5,  # 5 lần mức rủi ro
            "stop_trading_on_drawdown": risk_percentage * 10  # 10 lần mức rủi ro
        }
        
        # Điều chỉnh các tham số khác dựa trên mức rủi ro
        if risk_percentage <= 0.01:  # Rủi ro thấp (1% hoặc ít hơn)
            config["max_active_positions"] = 2
            config["max_daily_trades"] = 8
        elif risk_percentage <= 0.02:  # Rủi ro trung bình thấp (2% hoặc ít hơn)
            config["max_active_positions"] = 3
            config["max_daily_trades"] = 10
        elif risk_percentage <= 0.03:  # Rủi ro trung bình (3% hoặc ít hơn)
            config["max_active_positions"] = 4
            config["max_daily_trades"] = 12
        elif risk_percentage <= 0.04:  # Rủi ro trung bình cao (4% hoặc ít hơn)
            config["max_active_positions"] = 5
            config["max_daily_trades"] = 15
        else:  # Rủi ro cao (trên 4%)
            config["max_active_positions"] = 6
            config["max_daily_trades"] = 20
        
        return config
    
    @staticmethod
    def save_risk_config(symbol, config):
        """Lưu cấu hình rủi ro cho một cặp giao dịch"""
        config_dir = "configs"
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        config_path = f"{config_dir}/risk_config_{symbol.lower()}.json"
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logging.info(f"Đã lưu cấu hình rủi ro cho {symbol} tại {config_path}")
            return True
        except Exception as e:
            logging.error(f"Lỗi khi lưu cấu hình rủi ro tại {config_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_risk_levels():
        """Trả về danh sách các mức rủi ro được hỗ trợ"""
        return [2.0, 2.5, 3.0, 4.0, 5.0]
    
    @staticmethod
    def validate_risk_level(risk_level):
        """Kiểm tra mức rủi ro có hợp lệ không"""
        supported_levels = RiskConfigManager.get_risk_levels()
        
        if risk_level not in supported_levels:
            closest = min(supported_levels, key=lambda x: abs(x - risk_level))
            logging.warning(f"Mức rủi ro {risk_level}% không được hỗ trợ, sử dụng mức gần nhất {closest}%")
            return closest
        
        return risk_level
    
    @staticmethod
    def estimate_capital_required(symbol, risk_level, avg_position_size=None):
        """Ước tính vốn cần thiết dựa trên mức rủi ro"""
        if avg_position_size is None:
            # Ước tính giá trị vị thế trung bình dựa trên dữ liệu thị trường
            if symbol.startswith('BTC'):
                avg_position_size = 1000  # USD
            elif symbol.startswith('ETH'):
                avg_position_size = 500  # USD
            else:
                avg_position_size = 300  # USD
        
        # Ước tính vốn cần thiết: giá trị vị thế / % rủi ro
        capital = avg_position_size / (risk_level / 100)
        
        return capital