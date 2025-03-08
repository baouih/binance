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
logger = logging.getLogger('test_order_v2')

def main():
    # Khởi tạo Binance API
    api = BinanceAPI()
    
    # Lấy balance tài khoản
    balance = api.futures_account_balance()
    usdt_balance = None
    
    # Tìm balance của USDT
    for asset in balance:
        if asset['asset'] == 'USDT':
            usdt_balance = float(asset['balance'])
            break
    
    if usdt_balance is None:
        logger.error("Không tìm thấy balance USDT trong tài khoản!")
        return
    
    logger.info(f"Số dư tài khoản hiện tại: {usdt_balance} USDT")
    
    # Cấu hình giao dịch
    symbol = "SOLUSDT"
    leverage = 5  # 5x leverage
    risk_percent = 2.5  # % số dư để giao dịch
    stop_loss_percent = 5.0  # % giảm giá để dừng lỗ
    take_profit_percent = 7.5  # % tăng giá để chốt lời
    
    # Lấy giá hiện tại
    ticker = api.futures_ticker_price(symbol=symbol)
    if isinstance(ticker, list):
        for item in ticker:
            if item['symbol'] == symbol:
                current_price = float(item['price'])
                break
        else:
            current_price = None
    else:
        current_price = float(ticker['price'])
    
    if current_price is None:
        logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
        return
    
    logger.info(f"Giá hiện tại của {symbol}: {current_price} USDT")
    
    # Thiết lập đòn bẩy
    try:
        leverage_response = api.futures_change_leverage(symbol=symbol, leverage=leverage)
        logger.info(f"Đã thiết lập đòn bẩy {leverage}x cho {symbol}")
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập đòn bẩy: {str(e)}")
        return
    
    # Tính toán kích thước vị thế dựa trên risk_percent
    position_value = usdt_balance * (risk_percent / 100)
    position_size = position_value / current_price
    
    # Tính toán stop loss và take profit
    stop_loss_price = round(current_price * (1 - stop_loss_percent / 100), 2)
    take_profit_price = round(current_price * (1 + take_profit_percent / 100), 2)
    
    # Sử dụng AdaptiveStopLossManager để tính toán stop loss
    try:
        adaptive_sl_manager = AdaptiveStopLossManager()
        optimal_sl_percent = adaptive_sl_manager.calculate_optimal_stop_loss(symbol=symbol, strategy_name="futures_test")
        if optimal_sl_percent:
            stop_loss_percent = optimal_sl_percent
            logger.info(f"Sử dụng Adaptive Stop Loss: {stop_loss_percent}%")
            stop_loss_price = round(current_price * (1 - stop_loss_percent / 100), 2)
    except Exception as e:
        logger.warning(f"Không thể tính Adaptive Stop Loss, sử dụng mặc định: {str(e)}")
    
    # Hiển thị thông tin giao dịch
    logger.info("Thông số giao dịch:")
    logger.info(f"- Symbol: {symbol}")
    logger.info(f"- Đòn bẩy: {leverage}x")
    logger.info(f"- Kích thước vị thế: {position_size:.3f} {symbol.replace('USDT', '')} (≈ {position_value:.3f} USDT)")
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
        # Lấy các phương thức của API cho việc debug
        methods = [method for method in dir(api) if callable(getattr(api, method)) and not method.startswith('_')]
        logger.info(f"Các phương thức: {', '.join(methods)}")
        
        # Lấy thông tin exchange_info
        exchange_info = api.futures_exchange_info()
        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
        
        if symbol_info:
            # Lấy precision cho quantity
            qty_precision = int(symbol_info.get('quantityPrecision', 3))
            # Làm tròn chính xác theo precision
            from math import floor
            position_size = floor(position_size * 10**qty_precision) / 10**qty_precision
            position_size_str = f"{position_size:.{qty_precision}f}"
            logger.info(f"Kích thước vị thế sau khi làm tròn: {position_size_str} {symbol.replace('USDT', '')}")
        else:
            # Mặc định làm tròn xuống 3 chữ số thập phân
            position_size = floor(position_size * 1000) / 1000
            position_size_str = f"{position_size:.3f}"
        
        # Thử test_order trước
        try:
            test_params = {
                "symbol": symbol,
                "side": "BUY",
                "type": "MARKET",
                "quantity": position_size_str
            }
            logger.info(f"Tham số test_order: {test_params}")
            test_result = api.futures_create_order(
                symbol=symbol,
                side="BUY",
                type="MARKET",
                quantity=position_size_str,
                newOrderRespType="ACK",
                test=True
            )
            logger.info(f"Test order thành công: {test_result}")
        except Exception as test_e:
            logger.warning(f"Test order không thành công: {str(test_e)}")
            # Thử test với cách gọi khác
            try:
                logger.info("Thử phương thức test_order với tham số tương tự...")
                test_result = api.test_order(
                    symbol=symbol,
                    side="BUY",
                    type="MARKET",
                    quantity=position_size_str
                )
                logger.info(f"Test order thành công với phương thức thay thế: {test_result}")
            except Exception as alt_test_e:
                logger.warning(f"Test order phương thức thay thế cũng thất bại: {str(alt_test_e)}")
        
        # Đặt lệnh thực tế
        order_params = {
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET",
            "quantity": position_size_str
        }
        
        logger.info(f"Đặt lệnh với tham số: {order_params}")
        order = api.futures_create_order(**order_params)
        logger.info(f"Đã đặt lệnh MARKET BUY thành công: {json.dumps(order, indent=2)}")
        
        # Chờ để đảm bảo lệnh đã được xử lý
        import time
        time.sleep(2)
        
        # Lấy thông tin vị thế để xác nhận
        position = api.futures_get_position(symbol=symbol)
        logger.info(f"Thông tin vị thế sau khi đặt lệnh: {json.dumps(position, indent=2)}")
        
        # Đặt Stop Loss
        sl_params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "STOP_MARKET",
            "stopPrice": str(stop_loss_price),
            "closePosition": "true"
        }
        
        logger.info(f"Đặt lệnh Stop Loss với tham số: {sl_params}")
        stop_order = api.futures_create_order(**sl_params)
        logger.info(f"Đã đặt lệnh Stop Loss thành công: {json.dumps(stop_order, indent=2)}")
        
        # Đặt Take Profit
        tp_params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": str(take_profit_price),
            "closePosition": "true"
        }
        
        logger.info(f"Đặt lệnh Take Profit với tham số: {tp_params}")
        take_profit_order = api.futures_create_order(**tp_params)
        logger.info(f"Đã đặt lệnh Take Profit thành công: {json.dumps(take_profit_order, indent=2)}")
        
        # Cập nhật file active_positions.json
        try:
            with open('active_positions.json', 'r') as f:
                active_positions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            active_positions = {}
        
        # Thêm vị thế mới
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        active_positions[symbol] = {
            "entry_price": current_price,
            "position_size": position_size,
            "stop_loss": stop_loss_price,
            "take_profit": take_profit_price,
            "entry_time": timestamp,
            "order_id": order.get("orderId", "Unknown"),
            "sl_order_id": stop_order.get("orderId", "Unknown"),
            "tp_order_id": take_profit_order.get("orderId", "Unknown"),
            "status": "ACTIVE"
        }
        
        # Lưu lại thông tin
        with open('active_positions.json', 'w') as f:
            json.dump(active_positions, f, indent=4)
        
        logger.info(f"Đã cập nhật vị thế vào active_positions.json: {symbol}")
        
    except Exception as e:
        logger.error(f"Lỗi khi đặt lệnh: {str(e)}")
        # In ra traceback đầy đủ để debug
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()