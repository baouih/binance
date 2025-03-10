#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Risk Level Manager - Quản lý các mức độ rủi ro khác nhau
"""

import os
import json
import logging
import argparse
import shutil
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('risk_manager')

class RiskLevelManager:
    """
    Lớp quản lý các mức độ rủi ro khác nhau
    """
    
    # Các mức rủi ro mặc định được hỗ trợ
    SUPPORTED_RISK_LEVELS = ["10", "15", "20", "30"]
    
    # Thư mục chứa cấu hình rủi ro
    RISK_CONFIG_DIR = "risk_configs"
    
    def __init__(self):
        """Khởi tạo"""
        # Đảm bảo thư mục cấu hình tồn tại
        os.makedirs(self.RISK_CONFIG_DIR, exist_ok=True)
        
        # Load các cấu hình rủi ro hiện có
        self.risk_configs = self._load_risk_configs()
    
    def _load_risk_configs(self):
        """Tải tất cả cấu hình rủi ro hiện có"""
        risk_configs = {}
        
        # Tìm tất cả file cấu hình
        config_files = list(Path(self.RISK_CONFIG_DIR).glob("risk_level_*.json"))
        
        for config_file in config_files:
            # Lấy mức rủi ro từ tên file
            risk_level = config_file.stem.split("_")[-1]
            
            try:
                # Đọc file cấu hình
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # Lưu vào dictionary
                risk_configs[risk_level] = config
                
            except Exception as e:
                logger.error(f"Lỗi khi đọc file cấu hình {config_file}: {str(e)}")
        
        return risk_configs
    
    def create_default_configs(self, force=False):
        """Tạo các file cấu hình mặc định cho các mức rủi ro được hỗ trợ"""
        for risk_level in self.SUPPORTED_RISK_LEVELS:
            self.create_risk_config(risk_level, force=force)
    
    def create_risk_config(self, risk_level, force=False):
        """
        Tạo file cấu hình cho một mức rủi ro cụ thể
        
        Args:
            risk_level (str): Mức độ rủi ro
            force (bool): Ghi đè nếu file đã tồn tại
        """
        if risk_level not in self.SUPPORTED_RISK_LEVELS:
            logger.warning(f"Mức rủi ro {risk_level} không được hỗ trợ")
        
        # Tạo tên file
        filename = f"{self.RISK_CONFIG_DIR}/risk_level_{risk_level}.json"
        
        # Kiểm tra file đã tồn tại chưa
        if os.path.exists(filename) and not force:
            logger.info(f"File cấu hình {filename} đã tồn tại, bỏ qua")
            return
        
        # Tạo cấu hình mặc định
        risk_level_float = float(risk_level) / 100.0
        config = {
            "risk_level": int(risk_level),
            "max_open_positions": 3,
            "max_daily_trades": 8,
            "position_size_percent": risk_level_float,
            "max_risk_per_trade": risk_level_float,
            "stop_loss_percent": 2.0,
            "take_profit_percent": 4.0,
            "max_leverage": 10,
            "default_leverage": 5,
            "use_trailing_stop": True,
            "trailing_stop_activation": 1.5,
            "trailing_stop_distance": 1.0,
            "enable_martingale": False,
            "martingale_factor": 1.5,
            "max_martingale_steps": 2,
            "risk_adjustment_factor": 1.0,
            "volatility_adjustment": True,
            "max_daily_drawdown_percent": float(risk_level) * 2,
            "max_total_drawdown_percent": float(risk_level) * 3,
            "capital_preservation_ratio": 0.5,
            "trade_filters": {
                "min_volume_24h": 10000000,
                "min_price_change_24h": 1.0,
                "max_price_change_24h": 15.0,
                "min_price": 0.00000100
            },
            "entry_confirmation": {
                "required_signals": 2,
                "min_signal_strength": 0.6,
                "use_volume_confirmation": True,
                "use_trend_confirmation": True
            },
            "exit_strategy": {
                "use_dynamic_take_profit": True,
                "partial_take_profits": [
                    {"percent": 30, "price_target": 2.0},
                    {"percent": 30, "price_target": 3.0},
                    {"percent": 40, "price_target": 4.0}
                ],
                "use_dynamic_stop_loss": True,
                "max_trade_duration_hours": 48
            },
            "time_filters": {
                "enabled": False,
                "trading_hours": {
                    "start": "00:00",
                    "end": "23:59"
                },
                "avoid_high_volatility_times": True
            }
        }
        
        # Thay đổi các tham số dựa trên mức rủi ro
        if risk_level == "10":
            # Cấu hình cho mức rủi ro thấp (10%)
            config["max_open_positions"] = 2
            config["max_daily_trades"] = 5
            config["stop_loss_percent"] = 1.5
            config["take_profit_percent"] = 3.0
            config["max_leverage"] = 5
            config["default_leverage"] = 3
            config["trade_filters"]["min_volume_24h"] = 20000000
            config["exit_strategy"]["partial_take_profits"] = [
                {"percent": 50, "price_target": 1.5},
                {"percent": 50, "price_target": 3.0}
            ]
            
        elif risk_level == "15":
            # Cấu hình cho mức rủi ro trung bình thấp (15%)
            config["max_open_positions"] = 3
            config["max_daily_trades"] = 6
            config["stop_loss_percent"] = 2.0
            config["take_profit_percent"] = 3.5
            config["max_leverage"] = 7
            config["default_leverage"] = 4
            
        elif risk_level == "20":
            # Cấu hình cho mức rủi ro trung bình (20%)
            # Giữ nguyên cấu hình mặc định
            pass
            
        elif risk_level == "30":
            # Cấu hình cho mức rủi ro cao (30%)
            config["max_open_positions"] = 4
            config["max_daily_trades"] = 10
            config["stop_loss_percent"] = 3.0
            config["take_profit_percent"] = 6.0
            config["max_leverage"] = 15
            config["default_leverage"] = 7
            config["trailing_stop_activation"] = 2.0
            config["trailing_stop_distance"] = 1.5
            config["enable_martingale"] = True
            config["max_martingale_steps"] = 3
            config["trade_filters"]["min_volume_24h"] = 5000000
            config["trade_filters"]["max_price_change_24h"] = 25.0
            config["entry_confirmation"]["required_signals"] = 1
            config["entry_confirmation"]["min_signal_strength"] = 0.5
            config["exit_strategy"]["partial_take_profits"] = [
                {"percent": 20, "price_target": 2.0},
                {"percent": 30, "price_target": 4.0},
                {"percent": 50, "price_target": 6.0}
            ]
        
        # Lưu cấu hình
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"Đã tạo file cấu hình {filename}")
        
        # Cập nhật lại dictionary cấu hình
        self.risk_configs[risk_level] = config
    
    def get_risk_config(self, risk_level):
        """
        Lấy cấu hình cho một mức rủi ro cụ thể
        
        Args:
            risk_level (str): Mức độ rủi ro
            
        Returns:
            dict: Cấu hình rủi ro
        """
        # Kiểm tra risk_level có hợp lệ không
        if risk_level not in self.SUPPORTED_RISK_LEVELS:
            logger.warning(f"Mức rủi ro {risk_level} không được hỗ trợ, sử dụng mức mặc định 10")
            risk_level = "10"
        
        # Lấy từ cache nếu có
        if risk_level in self.risk_configs:
            return self.risk_configs[risk_level]
        
        # Tạo file cấu hình nếu chưa có
        self.create_risk_config(risk_level)
        
        # Trả về cấu hình
        return self.risk_configs[risk_level]
    
    def set_active_risk_level(self, risk_level):
        """
        Thiết lập mức rủi ro hiện tại
        
        Args:
            risk_level (str): Mức độ rủi ro
        """
        # Kiểm tra risk_level có hợp lệ không
        if risk_level not in self.SUPPORTED_RISK_LEVELS:
            logger.warning(f"Mức rủi ro {risk_level} không được hỗ trợ, sử dụng mức mặc định 10")
            risk_level = "10"
        
        # Lấy cấu hình
        config = self.get_risk_config(risk_level)
        
        # Cập nhật file account_config.json nếu có
        if os.path.exists("account_config.json"):
            try:
                with open("account_config.json", "r", encoding="utf-8") as f:
                    account_config = json.load(f)
                
                # Cập nhật risk_level
                account_config["risk_level"] = int(risk_level)
                
                # Lưu lại
                with open("account_config.json", "w", encoding="utf-8") as f:
                    json.dump(account_config, f, indent=4)
                
                logger.info(f"Đã cập nhật mức rủi ro {risk_level} trong account_config.json")
                
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật account_config.json: {str(e)}")
        
        # Tạo file active_risk_level.txt
        with open("active_risk_level.txt", "w", encoding="utf-8") as f:
            f.write(risk_level)
        
        logger.info(f"Đã thiết lập mức rủi ro hiện tại: {risk_level}")
    
    def get_active_risk_level(self):
        """
        Lấy mức rủi ro hiện tại
        
        Returns:
            str: Mức độ rủi ro hiện tại
        """
        # Kiểm tra file active_risk_level.txt
        if os.path.exists("active_risk_level.txt"):
            try:
                with open("active_risk_level.txt", "r", encoding="utf-8") as f:
                    risk_level = f.read().strip()
                
                if risk_level in self.SUPPORTED_RISK_LEVELS:
                    return risk_level
                
            except Exception as e:
                logger.error(f"Lỗi khi đọc active_risk_level.txt: {str(e)}")
        
        # Kiểm tra trong account_config.json
        if os.path.exists("account_config.json"):
            try:
                with open("account_config.json", "r", encoding="utf-8") as f:
                    account_config = json.load(f)
                
                risk_level = str(account_config.get("risk_level", 10))
                
                if risk_level in self.SUPPORTED_RISK_LEVELS:
                    return risk_level
                
            except Exception as e:
                logger.error(f"Lỗi khi đọc account_config.json: {str(e)}")
        
        # Mặc định là 10
        return "10"
    
    def export_risk_configs(self, output_dir="exported_risk_configs"):
        """
        Xuất tất cả cấu hình rủi ro ra một thư mục khác
        
        Args:
            output_dir (str): Thư mục đích
        """
        # Tạo thư mục đích
        os.makedirs(output_dir, exist_ok=True)
        
        # Tạo cấu hình mặc định nếu chưa có
        self.create_default_configs()
        
        # Sao chép các file cấu hình
        for risk_level in self.SUPPORTED_RISK_LEVELS:
            src_file = f"{self.RISK_CONFIG_DIR}/risk_level_{risk_level}.json"
            dst_file = f"{output_dir}/risk_level_{risk_level}.json"
            
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
                logger.info(f"Đã xuất {src_file} -> {dst_file}")
    
    def import_risk_configs(self, input_dir="imported_risk_configs"):
        """
        Nhập cấu hình rủi ro từ một thư mục khác
        
        Args:
            input_dir (str): Thư mục nguồn
        """
        # Kiểm tra thư mục nguồn
        if not os.path.exists(input_dir):
            logger.error(f"Thư mục {input_dir} không tồn tại")
            return
        
        # Nhập các file cấu hình
        for risk_level in self.SUPPORTED_RISK_LEVELS:
            src_file = f"{input_dir}/risk_level_{risk_level}.json"
            dst_file = f"{self.RISK_CONFIG_DIR}/risk_level_{risk_level}.json"
            
            if os.path.exists(src_file):
                # Sao chép file
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)
                logger.info(f"Đã nhập {src_file} -> {dst_file}")
                
                # Tải lại cấu hình
                try:
                    with open(dst_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    
                    self.risk_configs[risk_level] = config
                    
                except Exception as e:
                    logger.error(f"Lỗi khi đọc file cấu hình {dst_file}: {str(e)}")
    
    def show_risk_configs(self):
        """Hiển thị tất cả cấu hình rủi ro hiện có"""
        # Tạo cấu hình mặc định nếu chưa có
        self.create_default_configs()
        
        print("===== CẤU HÌNH RỦI RO =====")
        
        for risk_level in sorted(self.SUPPORTED_RISK_LEVELS):
            config = self.get_risk_config(risk_level)
            active = " (ĐANG DÙNG)" if risk_level == self.get_active_risk_level() else ""
            
            print(f"\n--- MỨC RỦI RO {risk_level}%{active} ---")
            print(f"Số vị thế tối đa: {config['max_open_positions']}")
            print(f"Số giao dịch tối đa mỗi ngày: {config['max_daily_trades']}")
            print(f"Phần trăm vốn mỗi giao dịch: {config['position_size_percent'] * 100:.1f}%")
            print(f"Rủi ro tối đa mỗi giao dịch: {config['max_risk_per_trade'] * 100:.1f}%")
            print(f"Phần trăm stoploss: {config['stop_loss_percent']:.1f}%")
            print(f"Phần trăm takeprofit: {config['take_profit_percent']:.1f}%")
            print(f"Đòn bẩy tối đa: {config['max_leverage']}x")
            print(f"Đòn bẩy mặc định: {config['default_leverage']}x")
            print(f"Sử dụng trailing stop: {'Có' if config['use_trailing_stop'] else 'Không'}")
            print(f"Sử dụng martingale: {'Có' if config.get('enable_martingale', False) else 'Không'}")
            
            # Thêm thông tin về chiến lược exit nếu có
            if "exit_strategy" in config:
                print("\nChiến lược thoát:")
                print(f"  Take profit động: {'Có' if config['exit_strategy'].get('use_dynamic_take_profit', False) else 'Không'}")
                print(f"  Stop loss động: {'Có' if config['exit_strategy'].get('use_dynamic_stop_loss', False) else 'Không'}")
                
                # Thông tin về partial take profits
                if "partial_take_profits" in config["exit_strategy"]:
                    print("  Take profit từng phần:")
                    for i, tp in enumerate(config["exit_strategy"]["partial_take_profits"]):
                        print(f"    - {tp['percent']}% tại mục tiêu {tp['price_target']}%")
                        
    def apply_risk_config(self, risk_level=None):
        """
        Áp dụng cấu hình rủi ro cho bot
        
        Args:
            risk_level (str): Mức độ rủi ro, nếu None sẽ dùng mức đang hoạt động
            
        Returns:
            dict: Cấu hình rủi ro được áp dụng
        """
        # Lấy mức rủi ro hiện tại nếu không được chỉ định
        if risk_level is None:
            risk_level = self.get_active_risk_level()
        
        # Lấy cấu hình rủi ro
        config = self.get_risk_config(risk_level)
        
        # Thiết lập mức rủi ro hiện tại
        self.set_active_risk_level(risk_level)
        
        # Trả về cấu hình đã áp dụng
        return config

def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(description="Risk Level Manager - Quản lý các mức độ rủi ro")
    parser.add_argument("--create-default", action="store_true", help="Tạo tất cả các file cấu hình mặc định")
    parser.add_argument("--force", action="store_true", help="Ghi đè các file cấu hình đã tồn tại")
    parser.add_argument("--set-active", type=str, help="Thiết lập mức rủi ro hiện tại (10, 15, 20, 30)")
    parser.add_argument("--show", action="store_true", help="Hiển thị tất cả cấu hình rủi ro")
    parser.add_argument("--export", type=str, help="Xuất cấu hình rủi ro ra thư mục")
    parser.add_argument("--import", dest="import_dir", type=str, help="Nhập cấu hình rủi ro từ thư mục")
    
    args = parser.parse_args()
    
    # Khởi tạo risk manager
    risk_manager = RiskLevelManager()
    
    # Xử lý các tùy chọn
    if args.create_default:
        risk_manager.create_default_configs(force=args.force)
        print("Đã tạo tất cả các file cấu hình mặc định")
    
    if args.set_active:
        risk_manager.set_active_risk_level(args.set_active)
        print(f"Đã thiết lập mức rủi ro hiện tại: {args.set_active}%")
    
    if args.export:
        risk_manager.export_risk_configs(args.export)
        print(f"Đã xuất cấu hình rủi ro ra thư mục: {args.export}")
    
    if args.import_dir:
        risk_manager.import_risk_configs(args.import_dir)
        print(f"Đã nhập cấu hình rủi ro từ thư mục: {args.import_dir}")
    
    if args.show or not (args.create_default or args.set_active or args.export or args.import_dir):
        # Mặc định hiển thị cấu hình nếu không có tùy chọn nào khác
        risk_manager.show_risk_configs()

if __name__ == "__main__":
    main()