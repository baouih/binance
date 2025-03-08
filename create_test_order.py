#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
from datetime import datetime
from binance_api import BinanceAPI
from adaptive_stop_loss_manager import AdaptiveStopLossManager

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_order')

def main():
    # Khởi tạo Binance API
    api = BinanceAPI()
    
    # Kiểm tra số dư tài khoản
    account_info = api.get_futures_account()
    balance = float(account_info.get('totalWalletBalance', 0))
    logger.info(f"Số dư tài khoản hiện tại: {balance} USDT")
    
    # Kiểm tra giá hiện tại
    symbol = "SOLUSDT"  # Sử dụng SOL là coin test
    ticker_data = api.futures_ticker_price(symbol)
    
    # Xử lý ticker data dựa trên kiểu dữ liệu trả về
    if isinstance(ticker_data, list):
        # Tìm ticker cho symbol cụ thể
        for ticker in ticker_data:
            if ticker.get('symbol') == symbol:
                current_price = float(ticker.get('price', 0))
                break
        else:
            logger.error(f"Không tìm thấy thông tin giá cho {symbol}")
            return
    else:
        # Nếu là dict, truy cập trực tiếp
        current_price = float(ticker_data.get('price', 0))
    logger.info(f"Giá hiện tại của {symbol}: {current_price} USDT")
    
    # Thiết lập đòn bẩy
    leverage = 5  # Đòn bẩy 5x
    api.futures_change_leverage(symbol=symbol, leverage=leverage)
    logger.info(f"Đã thiết lập đòn bẩy {leverage}x cho {symbol}")
    
    # Tính toán số lượng dựa trên rủi ro và số dư
    risk_amount = balance * 0.01  # Rủi ro 1% số dư
    position_size = round((risk_amount * leverage) / current_price, 4)
    
    # Làm tròn về số lượng nhỏ hơn để đảm bảo an toàn
    position_size = round(position_size * 0.5, 3)  # Giảm 50% kích thước vị thế để test
    
    # Tính toán stop loss và take profit
    stop_loss_manager = AdaptiveStopLossManager()
    sl_tp_info = stop_loss_manager.calculate_optimal_stop_loss(
        symbol, 
        'BUY', 
        current_price,
        'rsi_reversal'
    )
    
    stop_loss_percent = sl_tp_info['stop_loss']['percent']
    take_profit_percent = sl_tp_info['take_profit']['percent']
    
    stop_loss_price = round(current_price * (1 - stop_loss_percent/100), 2)
    take_profit_price = round(current_price * (1 + take_profit_percent/100), 2)
    
    logger.info(f"Thông số giao dịch:")
    logger.info(f"- Symbol: {symbol}")
    logger.info(f"- Đòn bẩy: {leverage}x")
    logger.info(f"- Kích thước vị thế: {position_size} SOL (≈ {position_size * current_price} USDT)")
    logger.info(f"- Giá hiện tại: {current_price} USDT")
    logger.info(f"- Stop Loss: {stop_loss_price} USDT ({stop_loss_percent}%)")
    logger.info(f"- Take Profit: {take_profit_price} USDT ({take_profit_percent}%)")
    
    # Trong môi trường thực, bot sẽ tự động đặt lệnh không cần xác nhận
    # Chỉ giữ lại đoạn xác nhận này cho chế độ kiểm thử
    if os.environ.get('BOT_MODE') == 'TEST':
        confirm = input("Xác nhận đặt lệnh BUY MARKET? (y/n): ")
        if confirm.lower() != 'y':
            logger.info("Hủy đặt lệnh.")
            return
    else:
        # Tự động xác nhận trong chế độ thực
        logger.info("Bot đang chạy ở chế độ tự động, tiến hành đặt lệnh...")
    
    # Đặt lệnh MARKET
    try:
        # Lấy tất cả phương thức của đối tượng api
        logger.info("Kiểm tra các phương thức có sẵn trong API:")
        methods = [method for method in dir(api) if callable(getattr(api, method)) and not method.startswith('_')]
        logger.info(f"Các phương thức: {', '.join(methods)}")
        
        # Kiểm tra trực tiếp phương thức futures_create_order
        if hasattr(api, 'futures_create_order'):
            # Quan trọng: làm tròn quantity theo precision của Binance
            # Đối với SOLUSDT, thường là 3 chữ số thập phân
            from math import floor
            
            # Lấy thông tin precision từ API nếu có
            try:
                exchange_info = api.futures_exchange_info()
                symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
                if symbol_info:
                    qty_precision = symbol_info.get('quantityPrecision', 3)
                    # Làm tròn chính xác theo precision
                    position_size = floor(position_size * 10**qty_precision) / 10**qty_precision
            except Exception as e:
                logger.warning(f"Không thể lấy thông tin precision, sử dụng mặc định: {str(e)}")
                # Mặc định làm tròn xuống 3 chữ số thập phân nếu không lấy được thông tin
                position_size = floor(position_size * 1000) / 1000
            
            logger.info(f"Kích thước vị thế sau khi làm tròn: {position_size} {symbol}")
            
            # Thiết lập các tham số khi gửi lệnh cho Binance Futures
            # Tham khảo: https://binance-docs.github.io/apidocs/futures/en/#new-order-trade
            
            # Đối với MARKET order, cần xác định chính xác cách nhập số lượng
            # Futures API yêu cầu tham số 'quantity' được định dạng chính xác
            order_params = {
                "symbol": symbol,
                "side": 'BUY',
                "type": 'MARKET',
                "quantity": str(position_size),  # Đổi thành chuỗi để tránh lỗi định dạng số
                "reduceOnly": False,             # Không giảm vị thế
                "newOrderRespType": "RESULT"     # Yêu cầu phản hồi đầy đủ
            }
            
            # Log các tham số để kiểm tra
            logger.info(f"Thử đặt lệnh với tham số: {order_params}")
            
            # Thử đặt lệnh test trước
            try:
                test_result = api.test_order(
                    symbol=symbol,
                    side='BUY',
                    type='MARKET',
                    quantity=str(position_size)
                )
                logger.info(f"Kết quả test order: {test_result}")
            except Exception as test_e:
                logger.warning(f"Test order không thành công: {str(test_e)}")
            
            # Đặt lệnh thực tế
            order = api.futures_create_order(**order_params)
            logger.info(f"Đã đặt lệnh MARKET BUY thành công: {json.dumps(order, indent=2)}")
            
            # Đặt Stop Loss
            # Binance Futures yêu cầu:
            # - stopPrice phải là chuỗi hoặc số
            # - closePosition phải là 'true' (chuỗi) khi đóng toàn bộ vị thế
            stop_loss_params = {
                "symbol": symbol,
                "side": 'SELL',
                "type": 'STOP_MARKET',
                "stopPrice": str(stop_loss_price),
                "closePosition": 'true'  # Phải là chuỗi 'true', không phải boolean True
            }
            
            logger.info(f"Thử đặt lệnh Stop Loss với tham số: {stop_loss_params}")
            stop_order = api.futures_create_order(**stop_loss_params)
            logger.info(f"Đã đặt lệnh Stop Loss thành công: {json.dumps(stop_order, indent=2)}")
            
            # Đặt Take Profit
            take_profit_params = {
                "symbol": symbol,
                "side": 'SELL',
                "type": 'TAKE_PROFIT_MARKET',
                "stopPrice": str(take_profit_price),
                "closePosition": 'true'  # Phải là chuỗi 'true', không phải boolean True
            }
            
            logger.info(f"Thử đặt lệnh Take Profit với tham số: {take_profit_params}")
            take_profit_order = api.futures_create_order(**take_profit_params)
            logger.info(f"Đã đặt lệnh Take Profit thành công: {json.dumps(take_profit_order, indent=2)}")
        else:
            logger.error("Phương thức futures_create_order không tồn tại!")
        
    except Exception as e:
        logger.error(f"Lỗi khi đặt lệnh: {str(e)}")

if __name__ == "__main__":
    main()