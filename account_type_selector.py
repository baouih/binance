#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import argparse
from tabulate import tabulate
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("account_selector")

class AccountTypeSelector:
    """
    Công cụ để lựa chọn cấu hình phù hợp nhất cho tài khoản dựa trên số dư và các tiêu chí đặt trước
    """
    
    def __init__(self):
        self.api = BinanceAPI(testnet=True)
        self.account_config = self.load_config('account_config.json')
        self.small_account_configs = self.account_config.get('small_account_configs', {})
        
    def load_config(self, filename):
        """Tải cấu hình từ file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Không thể tải cấu hình từ {filename}: {str(e)}")
            return {}
    
    def get_account_balance(self):
        """Lấy số dư tài khoản"""
        try:
            account_balance = self.api.futures_account_balance()
            available_balance = 0
            
            for balance in account_balance:
                if balance.get('asset') == 'USDT':
                    available_balance = float(balance.get('availableBalance', 0))
                    break
                    
            logger.info(f"Số dư khả dụng: {available_balance} USDT")
            return available_balance
        except Exception as e:
            logger.error(f"Không thể lấy số dư tài khoản: {str(e)}")
            return 0
    
    def select_account_config(self, balance=None):
        """Chọn cấu hình phù hợp dựa trên số dư"""
        if balance is None:
            balance = self.get_account_balance()
            
        if balance <= 0:
            logger.error("Không thể xác định số dư tài khoản")
            return None
            
        # Chuyển đổi các key từ string thành float để so sánh
        sizes = [float(size) for size in self.small_account_configs.keys()]
        sizes.sort()
        
        selected_size = None
        for size in sizes:
            if balance >= size:
                selected_size = size
            else:
                break
                
        if selected_size is None and sizes:
            # Nếu số dư nhỏ hơn tất cả các mức, chọn mức nhỏ nhất
            selected_size = sizes[0]
            
        if selected_size:
            config = self.small_account_configs.get(str(int(selected_size)), {})
            logger.info(f"Đã chọn cấu hình cho tài khoản ${int(selected_size)}")
            return config, selected_size
        else:
            logger.error("Không tìm thấy cấu hình phù hợp")
            return None, 0
            
    def display_config_comparison(self):
        """Hiển thị so sánh các cấu hình tài khoản"""
        logger.info("\n" + "="*80)
        logger.info("SO SÁNH CẤU HÌNH TÀI KHOẢN NHỎ")
        logger.info("="*80)
        
        configs = []
        
        for size, config in self.small_account_configs.items():
            configs.append({
                'Account Size': f"${size}",
                'Leverage': f"{config.get('leverage')}x",
                'Risk %': f"{config.get('risk_percentage')}%",
                'Max Positions': config.get('max_positions'),
                'Pairs Count': len(config.get('suitable_pairs', [])),
                'Min Position': f"${config.get('min_position_size', 0)}",
                'Trailing Stop': "Yes" if config.get('enable_trailing_stop', False) else "No",
                'Stop Loss': f"{config.get('default_stop_percentage', 0)}%",
                'Take Profit': f"{config.get('default_take_profit_percentage', 0)}%"
            })
            
        logger.info("\n" + tabulate(configs, headers='keys', tablefmt='grid'))
        
    def show_recommended_config(self, manual_balance=None):
        """Hiển thị cấu hình được đề xuất dựa trên số dư"""
        balance = manual_balance if manual_balance is not None else self.get_account_balance()
        
        if balance <= 0:
            logger.error("Không thể xác định số dư tài khoản")
            return None, 0
            
        config, selected_size = self.select_account_config(balance)
        
        if not config or config is None:
            return None, 0
            
        logger.info("\n" + "="*80)
        logger.info(f"CẤU HÌNH ĐỀ XUẤT CHO TÀI KHOẢN (${balance:.2f})")
        logger.info("="*80)
        
        # Hiển thị thông tin tổng quan
        logger.info(f"Cấu hình được chọn: ${int(selected_size)}")
        logger.info(f"Đòn bẩy: {config.get('leverage')}x")
        logger.info(f"Mức rủi ro: {config.get('risk_percentage')}%")
        logger.info(f"Số vị thế tối đa: {config.get('max_positions')}")
        logger.info(f"Vị thế tối thiểu: ${config.get('min_position_size', 0)}")
        
        # Hiển thị thông tin chi tiết về lệnh
        logger.info("\nCác loại lệnh hỗ trợ:")
        for order_type in config.get('order_types', []):
            logger.info(f"- {order_type}")
            
        # Hiển thị thông tin về stoploss và take profit
        logger.info(f"\nStop Loss mặc định: {config.get('default_stop_percentage', 0)}%")
        logger.info(f"Take Profit mặc định: {config.get('default_take_profit_percentage', 0)}%")
        logger.info(f"Trailing Stop: {'Bật' if config.get('enable_trailing_stop', False) else 'Tắt'}")
        
        # Hiển thị danh sách các cặp tiền phù hợp
        suitable_pairs = config.get('suitable_pairs', [])
        
        if suitable_pairs:
            logger.info(f"\nCác cặp tiền phù hợp ({len(suitable_pairs)}):")
            
            # Chia thành các hàng để hiển thị đẹp hơn
            pairs_rows = []
            current_row = []
            
            for i, pair in enumerate(suitable_pairs):
                current_row.append(pair)
                
                if len(current_row) == 5 or i == len(suitable_pairs) - 1:
                    pairs_rows.append(current_row)
                    current_row = []
                    
            for row in pairs_rows:
                logger.info("  ".join(row))
                
        # Hiển thị giá trị giao dịch tối đa
        max_trade_value = (balance * config.get('risk_percentage', 1) / 100) * config.get('leverage', 1)
        logger.info(f"\nGiá trị giao dịch tối đa: ${max_trade_value:.2f}")
        logger.info(f"BTC hiện tại: ${config.get('min_btc_value', 0)}")
        
        logger.info("\n" + "="*80)
        
    def run(self, manual_balance=None, compare=False):
        """Chạy công cụ lựa chọn tài khoản"""
        # Hiển thị so sánh nếu được yêu cầu
        if compare:
            self.display_config_comparison()
            
        # Hiển thị cấu hình đề xuất
        self.show_recommended_config(manual_balance)

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Công cụ lựa chọn cấu hình tài khoản')
    parser.add_argument('--balance', type=float, help='Số dư tài khoản (nếu không cung cấp, sẽ lấy từ API)')
    parser.add_argument('--compare', action='store_true', help='Hiển thị so sánh tất cả cấu hình')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    selector = AccountTypeSelector()
    selector.run(manual_balance=args.balance, compare=args.compare)