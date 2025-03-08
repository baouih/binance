#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("account_risk_calculator")

def calculate_risk_levels():
    """Tính toán các mức rủi ro phù hợp cho tài khoản nhỏ (100-300 USD)."""
    try:
        # Khởi tạo API
        api = BinanceAPI(testnet=True)
        
        # Lấy thông tin số dư tài khoản
        account_balance = api.futures_account_balance()
        available_balance = 0
        
        for balance in account_balance:
            if balance.get('asset') == 'USDT':
                available_balance = float(balance.get('availableBalance', 0))
                break
        
        logger.info(f"Số dư khả dụng: {available_balance} USDT")
        
        # Định nghĩa các mức vốn tài khoản mẫu để tính toán
        sample_account_sizes = [100, 200, 300, 500, 1000, 3000, 5000, 10000]
        
        # Lấy giá hiện tại của BTC
        ticker = api.get_symbol_ticker("BTCUSDT")
        btc_price = float(ticker['price']) if ticker and 'price' in ticker else 85000
        logger.info(f"Giá hiện tại của BTC: {btc_price} USDT")
        
        # Định nghĩa các mức đòn bẩy
        leverage_levels = [1, 2, 3, 5, 10, 20]
        
        # Yêu cầu giao dịch tối thiểu
        min_notional = 100  # USDT
        min_qty = 0.001  # BTC
        
        # Tính toán các mức rủi ro cho mỗi kích thước tài khoản
        logger.info("\n" + "="*80)
        logger.info("PHÂN TÍCH MỨC RỦI RO CHO TÀI KHOẢN NHỎ")
        logger.info("="*80)
        
        # Hiển thị header
        header = "| {:^10} | {:^10} | {:^15} | {:^15} | {:^15} | {:^10} |".format(
            "Số dư (USD)", "Đòn bẩy", "Rủi ro (%)", "Giá trị (USD)", "Số lượng BTC", "Khả thi?"
        )
        logger.info("-"*92)
        logger.info(header)
        logger.info("-"*92)
        
        result_data = []
        
        for account_size in sample_account_sizes:
            risk_percentages = []
            
            # Tính risk_range thông minh dựa vào kích thước tài khoản
            if account_size <= 100:
                risk_percentages = [5, 10, 15, 20, 25, 30]
            elif account_size <= 300:
                risk_percentages = [3, 5, 7, 10, 15, 20]
            elif account_size <= 1000:
                risk_percentages = [1, 2, 3, 5, 7, 10]
            else:
                risk_percentages = [0.5, 1, 2, 3, 5, 7]
            
            for leverage in leverage_levels:
                for risk_percentage in risk_percentages:
                    # Tính giá trị USD dựa vào rủi ro và đòn bẩy
                    position_value = (account_size * risk_percentage / 100) * leverage
                    
                    # Tính lượng BTC
                    btc_amount = position_value / btc_price
                    
                    # Kiểm tra xem có đáp ứng yêu cầu tối thiểu không
                    is_valid = (position_value >= min_notional) and (btc_amount >= min_qty)
                    
                    # Lưu dữ liệu
                    result_data.append({
                        'account_size': account_size,
                        'leverage': leverage,
                        'risk_percentage': risk_percentage,
                        'position_value': position_value,
                        'btc_amount': btc_amount,
                        'is_valid': is_valid
                    })
                    
                    # Hiển thị kết quả
                    row = "| {:^10} | {:^10} | {:^15.2f} | {:^15.2f} | {:^15.6f} | {:^10} |".format(
                        account_size, leverage, risk_percentage, position_value, btc_amount, 
                        "✓" if is_valid else "✗"
                    )
                    logger.info(row)
        
        # Lọc và hiển thị các mức phù hợp cho tài khoản nhỏ (100-300 USD)
        logger.info("\n" + "="*80)
        logger.info("CÁC MỨC PHÙ HỢP CHO TÀI KHOẢN 100-300 USD")
        logger.info("="*80)
        
        small_accounts = [100, 200, 300]
        for account_size in small_accounts:
            logger.info(f"\nTài khoản {account_size} USD:")
            logger.info("-"*60)
            
            valid_configs = [r for r in result_data if r['account_size'] == account_size and r['is_valid']]
            
            # Sắp xếp theo đòn bẩy và % rủi ro để hiển thị
            valid_configs.sort(key=lambda x: (x['leverage'], x['risk_percentage']))
            
            if valid_configs:
                for config in valid_configs:
                    logger.info(f"- Đòn bẩy: {config['leverage']}x, Rủi ro: {config['risk_percentage']}%, "
                             f"Giá trị: {config['position_value']:.2f} USD, BTC: {config['btc_amount']:.6f}")
            else:
                logger.info("Không có cấu hình phù hợp cho kích thước tài khoản này.")
        
        # Tạo các cấu hình đề xuất để cập nhật vào account_config.json
        logger.info("\n" + "="*80)
        logger.info("CẤU HÌNH ĐỀ XUẤT CHO account_config.json")
        logger.info("="*80)
        
        # Đề xuất cấu hình cho từng kích thước tài khoản
        config_suggestions = {}
        
        for account_size in sample_account_sizes:
            valid_configs = [r for r in result_data if r['account_size'] == account_size and r['is_valid']]
            
            if valid_configs:
                # Chọn cấu hình cân bằng (đòn bẩy medium, rủi ro medium)
                valid_configs.sort(key=lambda x: (x['leverage'], x['risk_percentage']))
                middle_index = len(valid_configs) // 2
                suggested_config = valid_configs[middle_index]
                
                config_suggestions[str(account_size)] = {
                    'leverage': suggested_config['leverage'],
                    'risk_percentage': suggested_config['risk_percentage'],
                    'max_positions': 3 if account_size >= 500 else (2 if account_size >= 200 else 1)
                }
        
        # Hiển thị cấu hình đề xuất dưới dạng JSON
        logger.info(json.dumps(config_suggestions, indent=2))
        
        # Lưu cấu hình đề xuất vào file
        with open('risk_configs.json', 'w') as f:
            json.dump(config_suggestions, f, indent=2)
        logger.info("\nĐã lưu cấu hình đề xuất vào file risk_configs.json")
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi tính toán mức rủi ro: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Bắt đầu tính toán các mức rủi ro cho tài khoản nhỏ...")
    calculate_risk_levels()