#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script cập nhật cấu hình rủi ro trước khi khởi động hệ thống giao dịch
Tự động điều chỉnh cấu hình dựa trên lịch sử và hiệu suất gần đây

Tác giả: AdvancedTradingBot
Ngày: 9/3/2025
"""

import os
import sys
import json
import logging
import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('risk_config_update.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('risk_config')

class RiskConfigUpdater:
    """Lớp quản lý cập nhật cấu hình rủi ro"""
    
    def __init__(self):
        """Khởi tạo trình cập nhật cấu hình"""
        self.logger = logging.getLogger('risk_config')
        self.account_config_path = 'account_config.json'
        self.strategy_config_path = 'configs/strategy_market_config.json'
        
        # Tải cấu hình
        with open(self.account_config_path, 'r') as f:
            self.account_config = json.load(f)
            
        with open(self.strategy_config_path, 'r') as f:
            self.strategy_config = json.load(f)
        
        self.logger.info("Đã khởi tạo RiskConfigUpdater")
        
    def update_account_config(self, risk_level='high'):
        """Cập nhật cấu hình tài khoản dựa trên mức độ rủi ro"""
        if risk_level == 'extreme':
            # Cấu hình rủi ro cực cao (20-50%)
            self.account_config['risk_per_trade'] = 20.0
            self.account_config['leverage'] = 25
            self.account_config['max_open_positions'] = 5
            self.account_config['capital_allocation']['BTC'] = 0.2
            self.account_config['capital_allocation']['ETH'] = 0.1
            self.account_config['capital_allocation']['others'] = 0.7
            
        elif risk_level == 'very_high':
            # Cấu hình rủi ro rất cao (15-20%)
            self.account_config['risk_per_trade'] = 15.0
            self.account_config['leverage'] = 20
            self.account_config['max_open_positions'] = 7
            self.account_config['capital_allocation']['BTC'] = 0.25
            self.account_config['capital_allocation']['ETH'] = 0.15
            self.account_config['capital_allocation']['others'] = 0.6
            
        elif risk_level == 'high':
            # Cấu hình rủi ro cao (10-15%)
            self.account_config['risk_per_trade'] = 10.0
            self.account_config['leverage'] = 20
            self.account_config['max_open_positions'] = 10
            self.account_config['capital_allocation']['BTC'] = 0.3
            self.account_config['capital_allocation']['ETH'] = 0.2
            self.account_config['capital_allocation']['others'] = 0.5
            
        elif risk_level == 'moderate':
            # Cấu hình rủi ro trung bình (5-10%)
            self.account_config['risk_per_trade'] = 7.0
            self.account_config['leverage'] = 15
            self.account_config['max_open_positions'] = 12
            self.account_config['capital_allocation']['BTC'] = 0.35
            self.account_config['capital_allocation']['ETH'] = 0.25
            self.account_config['capital_allocation']['others'] = 0.4
            
        elif risk_level == 'low':
            # Cấu hình rủi ro thấp (1-5%)
            self.account_config['risk_per_trade'] = 3.0
            self.account_config['leverage'] = 10
            self.account_config['max_open_positions'] = 15
            self.account_config['capital_allocation']['BTC'] = 0.4
            self.account_config['capital_allocation']['ETH'] = 0.3
            self.account_config['capital_allocation']['others'] = 0.3
            
        # Cập nhật thời gian chỉnh sửa
        self.account_config['last_updated'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # Ghi cấu hình mới
        with open(self.account_config_path, 'w') as f:
            json.dump(self.account_config, f, indent=4)
            
        self.logger.info(f"Đã cập nhật cấu hình tài khoản với mức độ rủi ro: {risk_level}")
        
    def update_strategy_config(self, aggressive_level='high'):
        """Cập nhật cấu hình chiến lược dựa trên mức độ tấn công"""
        # Cập nhật tham số chiến lược dựa trên mức độ tấn công
        if aggressive_level == 'extreme':
            # Cập nhật các thông số chiến lược cho mức độ tấn công cực cao
            for strategy_name, params in self.strategy_config['strategy_parameters'].items():
                if 'stop_loss_percent' in params:
                    # Giảm stop loss để tăng khả năng chịu rủi ro
                    params['stop_loss_percent'] = params['stop_loss_percent'] * 1.5
                    
                if 'take_profit_percent' in params:
                    # Tăng take profit để có lợi nhuận cao hơn
                    params['take_profit_percent'] = params['take_profit_percent'] * 1.5
            
            # Điều chỉnh hệ số rủi ro trong các chế độ thị trường
            for regime_name, regime_data in self.strategy_config['market_regimes'].items():
                if 'risk_adjustment' in regime_data:
                    regime_data['risk_adjustment'] = min(2.0, regime_data['risk_adjustment'] * 1.5)
                
                if 'position_sizing' in regime_data:
                    regime_data['position_sizing'] = 'aggressive'
        
        elif aggressive_level == 'high':
            # Cập nhật các thông số chiến lược cho mức độ tấn công cao
            for strategy_name, params in self.strategy_config['strategy_parameters'].items():
                if 'stop_loss_percent' in params:
                    params['stop_loss_percent'] = params['stop_loss_percent'] * 1.25
                    
                if 'take_profit_percent' in params:
                    params['take_profit_percent'] = params['take_profit_percent'] * 1.25
            
            # Điều chỉnh hệ số rủi ro trong các chế độ thị trường
            for regime_name, regime_data in self.strategy_config['market_regimes'].items():
                if 'risk_adjustment' in regime_data:
                    regime_data['risk_adjustment'] = min(1.8, regime_data['risk_adjustment'] * 1.25)
                
                if 'position_sizing' in regime_data:
                    regime_data['position_sizing'] = 'aggressive'
        
        elif aggressive_level == 'moderate':
            # Giữ nguyên các thông số mặc định
            pass
        
        elif aggressive_level == 'low':
            # Cập nhật các thông số chiến lược cho mức độ tấn công thấp
            for strategy_name, params in self.strategy_config['strategy_parameters'].items():
                if 'stop_loss_percent' in params:
                    params['stop_loss_percent'] = params['stop_loss_percent'] * 0.8
                    
                if 'take_profit_percent' in params:
                    params['take_profit_percent'] = params['take_profit_percent'] * 0.8
            
            # Điều chỉnh hệ số rủi ro trong các chế độ thị trường
            for regime_name, regime_data in self.strategy_config['market_regimes'].items():
                if 'risk_adjustment' in regime_data:
                    regime_data['risk_adjustment'] = regime_data['risk_adjustment'] * 0.8
                
                if 'position_sizing' in regime_data:
                    regime_data['position_sizing'] = 'reduced'
                  
        # Ghi cấu hình mới
        with open(self.strategy_config_path, 'w') as f:
            json.dump(self.strategy_config, f, indent=4)
            
        self.logger.info(f"Đã cập nhật cấu hình chiến lược với mức độ tấn công: {aggressive_level}")
    
    def update_combined_risk(self, risk_level='high', aggressive_level='high'):
        """Cập nhật cả cấu hình tài khoản và chiến lược"""
        self.update_account_config(risk_level)
        self.update_strategy_config(aggressive_level)
        
        self.logger.info(f"Đã hoàn thành cập nhật cấu hình rủi ro kết hợp: {risk_level} + {aggressive_level}")
        return True

def main():
    """Hàm chính để cập nhật cấu hình"""
    risk_level = 'high'  # 'low', 'moderate', 'high', 'very_high', 'extreme'
    aggressive_level = 'high'  # 'low', 'moderate', 'high', 'extreme'
    
    # Kiểm tra nếu có tham số dòng lệnh
    if len(sys.argv) > 1:
        risk_level = sys.argv[1]
    
    if len(sys.argv) > 2:
        aggressive_level = sys.argv[2]
    
    logger.info(f"Cập nhật cấu hình rủi ro với mức độ: {risk_level}, mức độ tấn công: {aggressive_level}")
    
    # Khởi tạo và thực hiện cập nhật
    updater = RiskConfigUpdater()
    result = updater.update_combined_risk(risk_level, aggressive_level)
    
    if result:
        logger.info("Cập nhật cấu hình rủi ro thành công!")
        return 0
    else:
        logger.error("Cập nhật cấu hình rủi ro thất bại!")
        return 1

if __name__ == "__main__":
    sys.exit(main())