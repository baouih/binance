#!/usr/bin/env python3
"""
Bộ điều khiển cấu hình rủi ro cho bot giao dịch

Module này cung cấp giao diện CLI để thiết lập thông số rủi ro và vốn ban đầu cho bot giao dịch.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List
from tabulate import tabulate

# Import RiskConfigManager từ module quản lý cấu hình
from risk_config_manager import RiskConfigManager, RISK_PROFILES

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("risk_config_controller")

class RiskConfigController:
    """Bộ điều khiển cấu hình rủi ro cho bot giao dịch"""
    
    def __init__(self):
        """Khởi tạo bộ điều khiển cấu hình rủi ro"""
        self.config_manager = RiskConfigManager()
    
    def main_menu(self):
        """Hiển thị menu chính và xử lý lựa chọn"""
        while True:
            self._clear_screen()
            print("=============================================")
            print("=== THIẾT LẬP RỦI RO BOT GIAO DỊCH BITCOIN ===")
            print("=============================================")
            print()
            print("Cấu hình hiện tại:")
            config = self.config_manager.get_current_config()
            effective_settings = self.config_manager.get_effective_risk_settings()
            
            print(f"  Vốn ban đầu: ${config.get('initial_balance', 100.0):.2f}")
            
            if config.get("custom_settings"):
                risk_profile = "Tùy chỉnh"
            else:
                profile_name = config.get("risk_profile", "medium")
                risk_profile = RISK_PROFILES[profile_name]["name"]
                
            print(f"  Hồ sơ rủi ro: {risk_profile}")
            print(f"  Chiến lược: {config.get('strategy', 'trend').capitalize()}")
            print(f"  Rủi ro tối đa: {effective_settings.get('max_account_risk', 25.0):.1f}%")
            print(f"  Rủi ro mỗi giao dịch: {effective_settings.get('risk_per_trade', 2.5):.1f}%")
            print(f"  Đòn bẩy tối ưu: x{effective_settings.get('optimal_leverage', 12)}")
            print()
            
            print("MENU CHÍNH:")
            print("1. Xem thông tin chi tiết cấu hình hiện tại")
            print("2. Đặt vốn ban đầu")
            print("3. Chọn hồ sơ rủi ro")
            print("4. Cài đặt rủi ro tùy chỉnh")
            print("5. Chọn chiến lược giao dịch")
            print("6. Mô phỏng giao dịch")
            print("7. Lưu cấu hình")
            print("8. Đặt lại cấu hình mặc định")
            print("0. Thoát")
            print()
            
            choice = input("Nhập lựa chọn của bạn (0-8): ")
            
            if choice == "0":
                print("Thoát khỏi chương trình.")
                break
            elif choice == "1":
                self._view_current_config()
            elif choice == "2":
                self._set_initial_balance()
            elif choice == "3":
                self._select_risk_profile()
            elif choice == "4":
                self._set_custom_settings()
            elif choice == "5":
                self._select_strategy()
            elif choice == "6":
                self._simulate_trade()
            elif choice == "7":
                print("Cấu hình đã được lưu tự động.")
                input("Nhấn Enter để tiếp tục...")
            elif choice == "8":
                self._reset_config()
            else:
                print("Lựa chọn không hợp lệ. Vui lòng chọn lại.")
                input("Nhấn Enter để tiếp tục...")
    
    def _clear_screen(self):
        """Xóa màn hình"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _view_current_config(self):
        """Xem thông tin chi tiết cấu hình hiện tại"""
        self._clear_screen()
        print("========================================")
        print("=== CHI TIẾT CẤU HÌNH RỦI RO HIỆN TẠI ===")
        print("========================================")
        print()
        
        summary = self.config_manager.get_current_summary()
        print(summary)
        
        input("Nhấn Enter để quay lại menu chính...")
    
    def _set_initial_balance(self):
        """Đặt vốn ban đầu"""
        self._clear_screen()
        print("==========================")
        print("=== ĐẶT VỐN BAN ĐẦU ===")
        print("==========================")
        print()
        
        current_balance = self.config_manager.get_current_config().get("initial_balance", 100.0)
        is_auto_detected = self.config_manager.get_current_config().get("balance_auto_detected", False)
        
        print(f"Vốn ban đầu hiện tại: ${current_balance:.2f}")
        if is_auto_detected:
            print("(Đã được phát hiện tự động từ tài khoản Binance)")
        print()
        
        print("1. Tự động kiểm tra số dư từ tài khoản Binance Futures")
        print("2. Tự động kiểm tra số dư từ tài khoản Binance Spot")
        print("3. Nhập thủ công số dư ban đầu")
        print("0. Quay lại")
        print()
        
        choice = input("Nhập lựa chọn của bạn (0-3): ")
        
        if choice == "0":
            return
        elif choice == "1":
            print("\nĐang kiểm tra số dư tài khoản Binance Futures...")
            if self.config_manager.auto_update_balance_from_binance(account_type='futures'):
                print("Đã cập nhật số dư từ tài khoản Binance Futures.")
            else:
                print("Không thể cập nhật số dư từ tài khoản Binance Futures.")
                print("Vui lòng kiểm tra kết nối và cài đặt API key.")
        elif choice == "2":
            print("\nĐang kiểm tra số dư tài khoản Binance Spot...")
            if self.config_manager.auto_update_balance_from_binance(account_type='spot'):
                print("Đã cập nhật số dư từ tài khoản Binance Spot.")
            else:
                print("Không thể cập nhật số dư từ tài khoản Binance Spot.")
                print("Vui lòng kiểm tra kết nối và cài đặt API key.")
        elif choice == "3":
            while True:
                try:
                    new_balance = float(input("\nNhập vốn ban đầu mới (USD): "))
                    if new_balance <= 0:
                        print("Vốn ban đầu phải lớn hơn 0.")
                        continue
                        
                    break
                except ValueError:
                    print("Vui lòng nhập một số hợp lệ.")
            
            if self.config_manager.set_initial_balance(new_balance):
                print(f"Đã đặt vốn ban đầu: ${new_balance:.2f}")
            else:
                print("Lỗi khi đặt vốn ban đầu.")
        else:
            print("Lựa chọn không hợp lệ.")
        
        input("Nhấn Enter để quay lại menu chính...")
    
    def _select_risk_profile(self):
        """Chọn hồ sơ rủi ro"""
        while True:
            self._clear_screen()
            print("============================")
            print("=== CHỌN HỒ SƠ RỦI RO ===")
            print("============================")
            print()
            
            current_profile = self.config_manager.get_current_config().get("risk_profile", "medium")
            print(f"Hồ sơ rủi ro hiện tại: {RISK_PROFILES[current_profile]['name']}")
            print()
            
            print("Các hồ sơ rủi ro có sẵn:")
            for i, (profile_name, profile) in enumerate(RISK_PROFILES.items(), 1):
                print(f"{i}. {profile['name']}")
                print(f"   {profile['description']}")
                print()
            
            print("0. Quay lại")
            print()
            
            choice = input("Nhập lựa chọn của bạn (0-5): ")
            
            if choice == "0":
                break
                
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(RISK_PROFILES):
                    profile_name = list(RISK_PROFILES.keys())[choice_idx]
                    
                    # Hiển thị thông tin chi tiết
                    self._clear_screen()
                    print(f"=== CHI TIẾT HỒ SƠ: {RISK_PROFILES[profile_name]['name']} ===")
                    print()
                    print(self.config_manager.get_profile_summary(profile_name))
                    print()
                    
                    confirm = input(f"Xác nhận chọn hồ sơ '{RISK_PROFILES[profile_name]['name']}' (y/n)? ").lower()
                    if confirm == 'y':
                        if self.config_manager.set_risk_profile(profile_name):
                            print(f"Đã chọn hồ sơ rủi ro: {RISK_PROFILES[profile_name]['name']}")
                            input("Nhấn Enter để quay lại menu chính...")
                            break
                        else:
                            print("Lỗi khi đặt hồ sơ rủi ro.")
                    else:
                        print("Đã hủy lựa chọn.")
                        
                    input("Nhấn Enter để tiếp tục...")
                else:
                    print("Lựa chọn không hợp lệ.")
                    input("Nhấn Enter để tiếp tục...")
            except ValueError:
                print("Vui lòng nhập một số hợp lệ.")
                input("Nhấn Enter để tiếp tục...")
    
    def _set_custom_settings(self):
        """Cài đặt rủi ro tùy chỉnh"""
        self._clear_screen()
        print("===============================")
        print("=== CÀI ĐẶT RỦI RO TÙY CHỈNH ===")
        print("===============================")
        print()
        
        # Hiện thị cài đặt hiện tại làm tham khảo
        settings = self.config_manager.get_effective_risk_settings()
        print("Cài đặt hiện tại:")
        print(f"  Rủi ro tối đa tài khoản: {settings.get('max_account_risk', 25.0):.1f}%")
        print(f"  Rủi ro mỗi giao dịch: {settings.get('risk_per_trade', 2.5):.1f}%")
        print(f"  Đòn bẩy tối đa: x{settings.get('max_leverage', 15)}")
        print(f"  Đòn bẩy tối ưu: x{settings.get('optimal_leverage', 12)}")
        print(f"  Khoảng cách thanh lý: {settings.get('min_distance_to_liquidation', 30.0):.1f}%")
        print()
        
        # Thu thập cài đặt mới
        custom_settings = {}
        
        print("Nhập giá trị mới (Enter để giữ nguyên giá trị hiện tại):")
        
        # Rủi ro tối đa tài khoản
        while True:
            max_account_risk = input(f"Rủi ro tối đa tài khoản (%, hiện tại: {settings.get('max_account_risk', 25.0):.1f}): ")
            if not max_account_risk:
                max_account_risk = settings.get('max_account_risk', 25.0)
                break
                
            try:
                max_account_risk = float(max_account_risk)
                if max_account_risk <= 0 or max_account_risk > 100:
                    print("Rủi ro tối đa phải trong khoảng (0, 100]%.")
                    continue
                    
                break
            except ValueError:
                print("Vui lòng nhập một số hợp lệ.")
        
        custom_settings['max_account_risk'] = max_account_risk
        
        # Rủi ro mỗi giao dịch
        while True:
            risk_per_trade = input(f"Rủi ro mỗi giao dịch (%, hiện tại: {settings.get('risk_per_trade', 2.5):.1f}): ")
            if not risk_per_trade:
                risk_per_trade = settings.get('risk_per_trade', 2.5)
                break
                
            try:
                risk_per_trade = float(risk_per_trade)
                if risk_per_trade <= 0 or risk_per_trade > 20:
                    print("Rủi ro mỗi giao dịch phải trong khoảng (0, 20]%.")
                    continue
                    
                break
            except ValueError:
                print("Vui lòng nhập một số hợp lệ.")
        
        custom_settings['risk_per_trade'] = risk_per_trade
        
        # Đòn bẩy tối đa
        while True:
            max_leverage = input(f"Đòn bẩy tối đa (hiện tại: x{settings.get('max_leverage', 15)}): ")
            if not max_leverage:
                max_leverage = settings.get('max_leverage', 15)
                break
                
            try:
                max_leverage = int(max_leverage)
                if max_leverage <= 0 or max_leverage > 100:
                    print("Đòn bẩy tối đa phải trong khoảng (0, 100].")
                    continue
                    
                break
            except ValueError:
                print("Vui lòng nhập một số nguyên hợp lệ.")
        
        custom_settings['max_leverage'] = max_leverage
        
        # Đòn bẩy tối ưu
        while True:
            optimal_leverage = input(f"Đòn bẩy tối ưu (hiện tại: x{settings.get('optimal_leverage', 12)}): ")
            if not optimal_leverage:
                optimal_leverage = settings.get('optimal_leverage', 12)
                break
                
            try:
                optimal_leverage = int(optimal_leverage)
                if optimal_leverage <= 0 or optimal_leverage > max_leverage:
                    print(f"Đòn bẩy tối ưu phải trong khoảng (0, {max_leverage}].")
                    continue
                    
                break
            except ValueError:
                print("Vui lòng nhập một số nguyên hợp lệ.")
        
        custom_settings['optimal_leverage'] = optimal_leverage
        
        # Khoảng cách thanh lý
        while True:
            min_distance = input(f"Khoảng cách thanh lý (%, hiện tại: {settings.get('min_distance_to_liquidation', 30.0):.1f}): ")
            if not min_distance:
                min_distance = settings.get('min_distance_to_liquidation', 30.0)
                break
                
            try:
                min_distance = float(min_distance)
                if min_distance <= 0 or min_distance > 100:
                    print("Khoảng cách thanh lý phải trong khoảng (0, 100]%.")
                    continue
                    
                break
            except ValueError:
                print("Vui lòng nhập một số hợp lệ.")
        
        custom_settings['min_distance_to_liquidation'] = min_distance
        
        # Các thông số khác
        custom_settings['max_positions'] = settings.get('max_positions', 2)
        custom_settings['max_margin_usage'] = settings.get('max_margin_usage', 60.0)
        custom_settings['use_trailing_stop'] = settings.get('use_trailing_stop', True)
        custom_settings['min_risk_reward'] = settings.get('min_risk_reward', 1.5)
        custom_settings['stop_loss_percent'] = settings.get('stop_loss_percent', {'scalping': 1.0, 'trend': 1.5})
        custom_settings['take_profit_percent'] = settings.get('take_profit_percent', {'scalping': 1.8, 'trend': 2.5})
        
        print()
        print("Xác nhận cài đặt tùy chỉnh:")
        print(f"  Rủi ro tối đa tài khoản: {custom_settings['max_account_risk']:.1f}%")
        print(f"  Rủi ro mỗi giao dịch: {custom_settings['risk_per_trade']:.1f}%")
        print(f"  Đòn bẩy tối đa: x{custom_settings['max_leverage']}")
        print(f"  Đòn bẩy tối ưu: x{custom_settings['optimal_leverage']}")
        print(f"  Khoảng cách thanh lý: {custom_settings['min_distance_to_liquidation']:.1f}%")
        print()
        
        confirm = input("Xác nhận cài đặt tùy chỉnh (y/n)? ").lower()
        if confirm == 'y':
            if self.config_manager.set_custom_settings(custom_settings):
                print("Đã lưu cài đặt rủi ro tùy chỉnh.")
            else:
                print("Lỗi khi lưu cài đặt tùy chỉnh.")
        else:
            print("Đã hủy cài đặt tùy chỉnh.")
            
        input("Nhấn Enter để quay lại menu chính...")
    
    def _select_strategy(self):
        """Chọn chiến lược giao dịch"""
        self._clear_screen()
        print("===============================")
        print("=== CHỌN CHIẾN LƯỢC GIAO DỊCH ===")
        print("===============================")
        print()
        
        current_strategy = self.config_manager.get_current_config().get("strategy", "trend")
        print(f"Chiến lược hiện tại: {current_strategy.capitalize()}")
        print()
        
        print("Các chiến lược có sẵn:")
        print("1. Scalping - Giao dịch nhanh trong thời gian ngắn, lợi nhuận nhỏ nhưng thường xuyên")
        print("2. Trend - Theo xu hướng thị trường, thời gian nắm giữ lâu hơn, lợi nhuận lớn hơn")
        print("3. Combined - Kết hợp cả hai chiến lược trên, tối ưu cho nhiều điều kiện thị trường")
        print()
        print("0. Quay lại")
        print()
        
        choice = input("Nhập lựa chọn của bạn (0-3): ")
        
        strategies = {
            "1": "scalping",
            "2": "trend",
            "3": "combined"
        }
        
        if choice == "0":
            return
        elif choice in strategies:
            strategy = strategies[choice]
            if self.config_manager.set_strategy(strategy):
                print(f"Đã chọn chiến lược: {strategy.capitalize()}")
            else:
                print("Lỗi khi đặt chiến lược.")
        else:
            print("Lựa chọn không hợp lệ.")
            
        input("Nhấn Enter để quay lại menu chính...")
    
    def _simulate_trade(self):
        """Mô phỏng giao dịch"""
        self._clear_screen()
        print("==========================")
        print("=== MÔ PHỎNG GIAO DỊCH ===")
        print("==========================")
        print()
        
        # Lấy vốn ban đầu
        initial_balance = self.config_manager.get_current_config().get("initial_balance", 100.0)
        print(f"Vốn ban đầu: ${initial_balance:.2f}")
        print()
        
        # Nhập thông tin giá
        try:
            entry_price = float(input("Nhập giá Bitcoin hiện tại (USD): "))
            if entry_price <= 0:
                print("Giá phải lớn hơn 0.")
                input("Nhấn Enter để quay lại menu chính...")
                return
                
            # Nhập phần trăm stop loss
            while True:
                stop_loss_percent = input("Nhập % stop loss (khoảng cách từ giá vào đến stop loss): ")
                try:
                    stop_loss_percent = float(stop_loss_percent)
                    if stop_loss_percent <= 0 or stop_loss_percent > 10:
                        print("% stop loss phải trong khoảng (0, 10]%.")
                        continue
                        
                    break
                except ValueError:
                    print("Vui lòng nhập một số hợp lệ.")
            
            # Hỏi hướng giao dịch
            direction = input("Chọn hướng giao dịch (1: Long/BUY, 2: Short/SELL): ")
            if direction not in ["1", "2"]:
                print("Lựa chọn không hợp lệ.")
                input("Nhấn Enter để quay lại menu chính...")
                return
                
            # Tính stop loss
            if direction == "1":  # Long/BUY
                stop_loss = entry_price * (1 - stop_loss_percent / 100)
                side = "buy"
            else:  # Short/SELL
                stop_loss = entry_price * (1 + stop_loss_percent / 100)
                side = "sell"
                
            # Chọn chiến lược
            strategy = self.config_manager.get_current_config().get("strategy", "trend")
            
            # Tính toán kích thước vị thế
            position_info = self.config_manager.calculate_position_size(entry_price, stop_loss, strategy)
            
            # Hiển thị thông tin giao dịch
            self._clear_screen()
            print("============================")
            print("=== THÔNG TIN GIAO DỊCH DEMO ===")
            print("============================")
            print()
            
            print(f"Vốn ban đầu: ${initial_balance:.2f}")
            print(f"Chiến lược: {strategy.capitalize()}")
            print(f"Hướng giao dịch: {side.upper()}")
            print()
            
            print(f"Giá vào lệnh: ${entry_price:.2f}")
            print(f"Stop Loss: ${position_info['stop_loss']:.2f} ({position_info['stop_distance_percent']:.2f}%)")
            print(f"Take Profit: ${position_info['take_profit']:.2f}")
            print(f"Đòn bẩy: x{position_info['leverage']}")
            print()
            
            print(f"Kích thước vị thế: ${position_info['position_size_usd']:.2f}")
            print(f"Số lượng Bitcoin: {position_info['quantity']:.8f} BTC")
            print(f"Margin sử dụng: ${position_info['position_size_usd']/position_info['leverage']:.2f}")
            print()
            
            print(f"Rủi ro: ${position_info['risk_amount']:.2f} ({position_info['risk_percent']:.2f}% của vốn)")
            print(f"Tỷ lệ R:R: 1:{position_info['risk_reward_ratio']:.2f}")
            print(f"Điểm thanh lý: ${position_info['liquidation_price']:.2f} ({position_info['liquidation_distance_percent']:.2f}%)")
            print()
            
            # Mô phỏng các kịch bản
            print("Mô phỏng các kịch bản:")
            scenarios = []
            
            if side == "buy":
                # Stop Loss Hit
                scenarios.append({
                    'name': 'Stop Loss hit',
                    'price': position_info['stop_loss'],
                    'pnl': -position_info['risk_amount'],
                    'pnl_pct': -position_info['risk_percent']
                })
                
                # Take Profit Hit
                scenarios.append({
                    'name': 'Take Profit hit',
                    'price': position_info['take_profit'],
                    'pnl': position_info['risk_amount'] * position_info['risk_reward_ratio'],
                    'pnl_pct': position_info['risk_percent'] * position_info['risk_reward_ratio']
                })
                
                # Price up 1%
                scenarios.append({
                    'name': 'Giá tăng 1%',
                    'price': entry_price * 1.01,
                    'pnl': position_info['quantity'] * (entry_price * 0.01),
                    'pnl_pct': 1.0 * position_info['leverage']
                })
                
                # Price down 1%
                scenarios.append({
                    'name': 'Giá giảm 1%',
                    'price': entry_price * 0.99,
                    'pnl': position_info['quantity'] * (entry_price * -0.01),
                    'pnl_pct': -1.0 * position_info['leverage']
                })
            else:  # sell
                # Stop Loss Hit
                scenarios.append({
                    'name': 'Stop Loss hit',
                    'price': position_info['stop_loss'],
                    'pnl': -position_info['risk_amount'],
                    'pnl_pct': -position_info['risk_percent']
                })
                
                # Take Profit Hit
                scenarios.append({
                    'name': 'Take Profit hit',
                    'price': position_info['take_profit'],
                    'pnl': position_info['risk_amount'] * position_info['risk_reward_ratio'],
                    'pnl_pct': position_info['risk_percent'] * position_info['risk_reward_ratio']
                })
                
                # Price up 1%
                scenarios.append({
                    'name': 'Giá tăng 1%',
                    'price': entry_price * 1.01,
                    'pnl': position_info['quantity'] * (entry_price * -0.01),
                    'pnl_pct': -1.0 * position_info['leverage']
                })
                
                # Price down 1%
                scenarios.append({
                    'name': 'Giá giảm 1%',
                    'price': entry_price * 0.99,
                    'pnl': position_info['quantity'] * (entry_price * 0.01),
                    'pnl_pct': 1.0 * position_info['leverage']
                })
            
            # Hiển thị bảng kịch bản
            table_data = []
            for scenario in scenarios:
                table_data.append([
                    scenario['name'],
                    f"${scenario['price']:.2f}",
                    f"${scenario['pnl']:.2f}",
                    f"{scenario['pnl_pct']:+.2f}%",
                    f"${initial_balance + scenario['pnl']:.2f}"
                ])
                
            headers = ["Kịch bản", "Giá", "P&L", "P&L %", "Số dư mới"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
        except ValueError:
            print("Vui lòng nhập các giá trị số hợp lệ.")
            
        input("Nhấn Enter để quay lại menu chính...")
    
    def _reset_config(self):
        """Đặt lại cấu hình mặc định"""
        self._clear_screen()
        print("==============================")
        print("=== ĐẶT LẠI CẤU HÌNH MẶC ĐỊNH ===")
        print("==============================")
        print()
        
        confirm = input("Bạn có chắc chắn muốn đặt lại cấu hình về mặc định (y/n)? ").lower()
        if confirm == 'y':
            if self.config_manager.reset_to_default():
                print("Đã đặt lại cấu hình về mặc định.")
            else:
                print("Lỗi khi đặt lại cấu hình.")
        else:
            print("Đã hủy thao tác.")
            
        input("Nhấn Enter để quay lại menu chính...")

def main():
    """Hàm chính để chạy bộ điều khiển cấu hình rủi ro"""
    controller = RiskConfigController()
    controller.main_menu()

if __name__ == "__main__":
    main()