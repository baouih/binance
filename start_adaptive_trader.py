#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script khởi động Adaptive Mode Trader - tự động chọn giữa Hedge Mode và Single Direction
"""

import os
import time
import json
import logging
import argparse

from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api
from adaptive_mode_trader import AdaptiveModeTrader

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('adaptive_trader.log')
    ]
)

logger = logging.getLogger('start_adaptive')

def main():
    """
    Hàm chính để khởi động Adaptive Mode Trader
    """
    # Parse arguments
    parser = argparse.ArgumentParser(description='Khởi động Adaptive Mode Trader')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT',
                        help='Danh sách các cặp tiền, phân cách bởi dấu phẩy')
    parser.add_argument('--mode', type=str, default='both',
                        choices=['hedge', 'single', 'both'],
                        help='Chế độ giao dịch ban đầu')
    parser.add_argument('--config', type=str, default='adaptive_trader_config.json',
                        help='Đường dẫn file cấu hình')
    
    args = parser.parse_args()
    
    # Chuyển đổi danh sách symbols
    symbols = args.symbols.split(',')
    
    # Khởi tạo Binance API
    try:
        # Kiểm tra tồn tại file .env
        if not os.path.exists('.env'):
            if os.path.exists('.env.example'):
                logger.warning("Không tìm thấy file .env, sao chép từ .env.example")
                import shutil
                shutil.copy('.env.example', '.env')
                
                # Yêu cầu nhập API key và secret
                print("\nChú ý: Bạn cần phải cấu hình API key và secret trong file .env")
                print("Vui lòng cập nhật file .env trước khi tiếp tục.\n")
                
                # Đợi 3 giây để người dùng có thể đọc thông báo
                time.sleep(3)
        
        # Khởi tạo API
        api = BinanceAPI()
        api = apply_fixes_to_api(api)
        
        # Kiểm tra kết nối
        if not api.ping():
            logger.error("Không thể kết nối đến Binance API")
            print("Lỗi: Không thể kết nối đến Binance API. Vui lòng kiểm tra mạng và API key.")
            return False
        
        logger.info(f"Kết nối thành công đến Binance API")
        
        # Kiểm tra môi trường testnet hay mainnet
        is_testnet = api.is_testnet
        logger.info(f"Đang sử dụng {'TESTNET' if is_testnet else 'MAINNET'}")
        
        # Hiển thị thông tin tài khoản
        try:
            account_info = api.get_futures_account_balance()
            balance = float(account_info[0]['balance']) if account_info else 0
            logger.info(f"Số dư tài khoản: {balance:.2f} USDT")
            print(f"Số dư tài khoản: {balance:.2f} USDT")
        except Exception as e:
            logger.error(f"Không thể lấy thông tin tài khoản: {e}")
            print(f"Lỗi: Không thể lấy thông tin tài khoản. {str(e)}")
        
        # Khởi tạo cấu hình
        if not os.path.exists(args.config):
            # Tạo cấu hình mặc định
            config = {
                'symbols': symbols,
                'max_concurrent_positions': 10,
                'max_positions_per_symbol': 2,
                'use_market_orders': True,
                'market_check_interval': 10,  # phút
                'position_check_interval': 5,  # phút
                'enable_telegram_notifications': True,
                'enable_auto_optimization': True,
                'optimization_interval': 24,  # giờ
                'account_risk_limit': 20.0,  # % tổng tài khoản có thể đặt cọc
                'fallback_mode': 'single',  # Chế độ dự phòng nếu lỗi phân tích
                'max_spread_percentage': 0.5,  # % chênh lệch giá mua/bán tối đa
                'min_volume_usd': 1000000.0  # Volume tối thiểu cho các cặp (USD)
            }
            
            # Lưu cấu hình
            with open(args.config, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Đã tạo file cấu hình mặc định {args.config}")
        
        # Khởi tạo trader
        trader = AdaptiveModeTrader(api, config_path=args.config)
        
        # Hiển thị thông tin
        print("\n===================== ADAPTIVE MODE TRADER =====================")
        print(f"Chế độ: {'TESTNET' if is_testnet else 'MAINNET'}")
        print(f"Số dư: {balance:.2f} USDT")
        print(f"Số cặp tiền: {len(symbols)}")
        print(f"Danh sách cặp tiền: {', '.join(symbols)}")
        print("================================================================\n")
        
        # Bắt đầu trader
        trader.start()
        logger.info("Đã khởi động Adaptive Mode Trader")
        
        # Hiển thị thông tin khi đang chạy
        print("Adaptive Mode Trader đang chạy...")
        print("Nhấn Ctrl+C để dừng")
        
        try:
            # Chạy vô hạn
            while True:
                time.sleep(60)
                
                # Tạo báo cáo trạng thái mỗi 30 phút
                if time.localtime().tm_min in [0, 30]:
                    report = trader.get_status_report()
                    
                    # Hiển thị thông tin ngắn gọn
                    if report and 'error' not in report:
                        account = report.get('account', {})
                        positions = report.get('positions', {})
                        performance = report.get('performance', {})
                        
                        print("\n----- Báo cáo trạng thái -----")
                        print(f"Thời gian: {report.get('timestamp', '')}")
                        print(f"Số dư: {account.get('balance', 0):.2f} USDT")
                        print(f"Unrealized PnL: {account.get('unrealized_pnl', 0):.2f} USDT")
                        print(f"Vị thế: {positions.get('total', 0)} (Hedge: {positions.get('hedge', 0)}, Single: {positions.get('single', 0)})")
                        print(f"Lợi nhuận: {performance.get('total_pnl', 0):.2f} USDT")
                        print(f"Tỷ lệ thắng: {performance.get('win_rate', 0)*100:.1f}%")
                        print("-----------------------------\n")
        
        except KeyboardInterrupt:
            # Dừng khi nhấn Ctrl+C
            trader.stop()
            logger.info("Đã dừng Adaptive Mode Trader")
            print("\nĐã dừng Adaptive Mode Trader")
        
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi khởi động Adaptive Mode Trader: {e}")
        print(f"Lỗi: {str(e)}")
        return False

if __name__ == "__main__":
    main()