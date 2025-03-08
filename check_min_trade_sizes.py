#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
from decimal import Decimal, ROUND_UP

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('min_trade_sizes')

def setup_logging_handler():
    """Thiết lập logging handler để ghi ra file và console."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return handler

def load_account_config():
    """Tải cấu hình tài khoản từ file JSON."""
    try:
        with open('account_config.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Lỗi khi tải file cấu hình tài khoản: {str(e)}")
        return None

def save_account_config(config_data):
    """Lưu cấu hình tài khoản vào file JSON."""
    try:
        with open('account_config.json', 'w') as file:
            json.dump(config_data, file, indent=4)
        logger.info("Đã lưu cấu hình tài khoản vào file account_config.json")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu file cấu hình tài khoản: {str(e)}")
        return False

def check_min_trade_sizes():
    """Kiểm tra kích thước giao dịch tối thiểu cho tất cả các cặp tiền tệ."""
    # Tải cấu hình tài khoản
    config = load_account_config()
    if not config:
        logger.error("Không thể tiếp tục do lỗi tải cấu hình tài khoản.")
        return False
    
    # Tạo kết nối API Binance
    api = BinanceAPI(
        account_type=config.get('account_type', 'futures'),
        api_mode=config.get('api_mode', 'testnet')
    )
    
    # Lấy danh sách các cặp tiền tệ mà chúng ta đang theo dõi
    symbols = config.get('symbols', [])
    if not symbols:
        logger.error("Không tìm thấy danh sách các cặp tiền tệ trong cấu hình.")
        return False
    
    # Lấy số dư tài khoản
    account_balance = api.futures_account_balance()
    available_balance = 0
    
    for balance in account_balance:
        if balance.get('asset') == 'USDT':
            available_balance = float(balance.get('availableBalance', 0))
            break
    
    if available_balance <= 0:
        logger.error(f"Số dư khả dụng không hợp lệ: {available_balance} USDT")
        return False
    
    logger.info(f"Số dư khả dụng: {available_balance} USDT")
    
    # Lấy thông tin chi tiết về exchange
    exchange_info = api.get_exchange_info()
    
    # Danh sách để lưu thông tin về kích thước giao dịch tối thiểu và giới hạn rủi ro
    min_trade_info = []
    risk_levels = [1.0, 2.5, 5.0, 10.0]  # Các mức rủi ro (%)
    leverage = config.get('leverage', 5)
    
    # Kiểm tra từng cặp tiền tệ
    for symbol in symbols:
        # Lấy giá hiện tại
        ticker = api.get_symbol_ticker(symbol)
        if not ticker or 'price' not in ticker:
            logger.warning(f"Không thể lấy giá hiện tại của {symbol}")
            continue
        
        current_price = float(ticker['price'])
        
        # Tìm thông tin của symbol
        symbol_info = None
        for info in exchange_info.get('symbols', []):
            if info['symbol'] == symbol:
                symbol_info = info
                break
        
        if not symbol_info:
            logger.warning(f"Không tìm thấy thông tin cho {symbol}")
            continue
        
        # Lấy thông tin về lọc size cho symbol này
        min_qty = 0
        step_size = 0
        precision = 0
        
        for filter_item in symbol_info.get('filters', []):
            if filter_item['filterType'] == 'LOT_SIZE':
                min_qty = float(filter_item['minQty'])
                step_size = float(filter_item['stepSize'])
                
                # Xác định số chữ số thập phân
                if '.' in str(step_size):
                    precision = len(str(step_size).split('.')[1])
                break
        
        # Tính toán giá trị giao dịch tối thiểu (USD)
        min_trade_value = min_qty * current_price
        
        # Tính toán số lượng tối thiểu cho mỗi mức rủi ro với đòn bẩy hiện tại
        risk_quantities = {}
        min_notional_met = {}
        
        for risk in risk_levels:
            # Giá trị danh nghĩa có thể giao dịch dựa trên mức rủi ro
            risk_value = (available_balance * risk / 100) * leverage
            
            # Số lượng tương ứng với mức rủi ro
            qty = risk_value / current_price
            
            # Làm tròn theo step_size
            rounded_qty = max(min_qty, round(qty - (qty % step_size), precision))
            
            # Kiểm tra xem có đạt được yêu cầu tối thiểu không
            meets_min = rounded_qty >= min_qty
            risk_quantities[risk] = rounded_qty
            min_notional_met[risk] = meets_min
        
        # Thêm vào danh sách kết quả
        min_trade_info.append({
            'symbol': symbol,
            'current_price': current_price,
            'min_qty': min_qty,
            'min_notional': min_trade_value,
            'step_size': step_size,
            'precision': precision,
            'risk_quantities': risk_quantities,
            'min_notional_met': min_notional_met
        })
    
    # Hiển thị kết quả
    logger.info(f"{'=' * 80}")
    logger.info(f"THÔNG TIN GIAO DỊCH TỐI THIỂU CHO {len(min_trade_info)} CẶP TIỀN TỆ")
    logger.info(f"{'=' * 80}")
    logger.info(f"{'Symbol':<10} {'Giá hiện tại':<15} {'Min Qty':<10} {'Min Notional':<15} {'Step Size':<10}")
    logger.info(f"{'-' * 80}")
    
    for info in min_trade_info:
        logger.info(f"{info['symbol']:<10} {info['current_price']:<15.8f} {info['min_qty']:<10.8f} {info['min_notional']:<15.2f} {info['step_size']:<10.8f}")
    
    logger.info(f"{'=' * 80}")
    logger.info(f"PHÂN TÍCH MỨC ĐỘ RỦI RO VỚI ĐÒN BẨY {leverage}x")
    logger.info(f"{'=' * 80}")
    
    # Hiển thị thông tin chi tiết về các mức rủi ro
    headers = ['Symbol']
    for risk in risk_levels:
        headers.append(f"{risk}% Qty")
        headers.append(f"Valid?")
    
    logger.info(" | ".join([f"{h:<12}" for h in headers]))
    logger.info(f"{'-' * 120}")
    
    for info in min_trade_info:
        row = [info['symbol']]
        for risk in risk_levels:
            qty = info['risk_quantities'][risk]
            valid = info['min_notional_met'][risk]
            row.append(f"{qty:.8f}")
            row.append("✓" if valid else "✗")
        
        logger.info(" | ".join([f"{cell:<12}" for cell in row]))
    
    # Tạo cấu hình giao dịch tối thiểu mới
    min_trade_sizes = {}
    for info in min_trade_info:
        min_trade_sizes[info['symbol']] = {
            'min_qty': info['min_qty'],
            'step_size': info['step_size'],
            'precision': info['precision']
        }
    
    # Cập nhật cấu hình tài khoản
    config['min_trade_sizes'] = min_trade_sizes
    if save_account_config(config):
        logger.info("Đã cập nhật thành công thông tin về kích thước giao dịch tối thiểu vào cấu hình tài khoản.")
    
    return True

if __name__ == "__main__":
    logger.info("Bắt đầu kiểm tra kích thước giao dịch tối thiểu cho tất cả các cặp tiền tệ...")
    check_min_trade_sizes()