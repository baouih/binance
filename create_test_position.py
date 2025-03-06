#!/usr/bin/env python3
"""
Script tạo vị thế thử nghiệm để kiểm tra hệ thống trailing stop
"""

import json
import logging
import datetime
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("create_test_position")

def create_test_position():
    """
    Tạo vị thế thử nghiệm trên Binance Futures Testnet
    """
    try:
        # Khởi tạo Binance API
        api = BinanceAPI()
        
        # Kiểm tra kết nối và số dư
        account_info = api.get_futures_account()
        if not account_info:
            logger.error("Không thể kết nối đến tài khoản Binance Futures")
            return False
        
        balance = float(account_info.get('totalWalletBalance', 0))
        available_balance = float(account_info.get('availableBalance', 0))
        
        logger.info(f"Số dư tài khoản: {balance} USDT, Khả dụng: {available_balance} USDT")
        
        if available_balance < 100:
            logger.warning(f"Số dư khả dụng thấp: {available_balance} USDT, nên có ít nhất 100 USDT")
        
        # Thông tin vị thế thử nghiệm
        symbol = "BTCUSDT"
        side = "BUY"  # BUY = LONG, SELL = SHORT
        leverage = 10
        position_size_usd = 50  # USD
        
        # Lấy giá hiện tại
        ticker = api.get_symbol_ticker(symbol)
        if not ticker or 'price' not in ticker:
            logger.error(f"Không thể lấy giá hiện tại của {symbol}")
            return False
        
        current_price = float(ticker['price'])
        logger.info(f"Giá hiện tại của {symbol}: {current_price} USDT")
        
        # Đặt đòn bẩy
        try:
            api.set_futures_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"Đã đặt đòn bẩy {leverage}x cho {symbol}")
        except Exception as e:
            logger.warning(f"Lỗi khi đặt đòn bẩy: {str(e)}")
        
        # Tính toán số lượng
        quantity = position_size_usd / current_price
        
        # Làm tròn số lượng theo quy tắc của sàn
        exchange_info = api.get_exchange_info()
        symbol_info = None
        
        for info in exchange_info.get('symbols', []):
            if info['symbol'] == symbol:
                symbol_info = info
                break
        
        if symbol_info:
            for filter_item in symbol_info.get('filters', []):
                if filter_item['filterType'] == 'LOT_SIZE':
                    min_qty = float(filter_item['minQty'])
                    max_qty = float(filter_item['maxQty'])
                    step_size = float(filter_item['stepSize'])
                    
                    # Làm tròn số lượng theo stepSize
                    precision = 0
                    if '.' in str(step_size):
                        precision = len(str(step_size).split('.')[1])
                    quantity = round(quantity - (quantity % step_size), precision)
                    
                    # Đảm bảo nằm trong giới hạn
                    quantity = max(min_qty, min(quantity, max_qty))
                    break
        
        logger.info(f"Số lượng đã làm tròn: {quantity} {symbol}")
        
        # Tạo lệnh thị trường
        try:
            order = api.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=quantity,
                reduceOnly=False
            )
            
            logger.info(f"Đã tạo lệnh mua thị trường: {json.dumps(order, indent=2)}")
            
            # Đặt stop loss và take profit
            entry_price = current_price
            
            if side == "BUY":
                stop_loss_price = entry_price * 0.95  # 5% dưới giá vào
                take_profit_price = entry_price * 1.10  # 10% trên giá vào
            else:
                stop_loss_price = entry_price * 1.05  # 5% trên giá vào
                take_profit_price = entry_price * 0.90  # 10% dưới giá vào
            
            # Đặt stop loss
            sl_order = api.futures_create_order(
                symbol=symbol,
                side="SELL" if side == "BUY" else "BUY",
                type="STOP_MARKET",
                stopPrice=stop_loss_price,
                closePosition=True,
                reduceOnly=True
            )
            
            logger.info(f"Đã đặt stop loss tại {stop_loss_price}: {json.dumps(sl_order, indent=2)}")
            
            # Đặt take profit
            tp_order = api.futures_create_order(
                symbol=symbol,
                side="SELL" if side == "BUY" else "BUY",
                type="TAKE_PROFIT_MARKET",
                stopPrice=take_profit_price,
                closePosition=True,
                reduceOnly=True
            )
            
            logger.info(f"Đã đặt take profit tại {take_profit_price}: {json.dumps(tp_order, indent=2)}")
            
            logger.info("Vị thế đã được tạo thành công!")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo lệnh: {str(e)}")
            return False
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo vị thế thử nghiệm: {str(e)}")
        return False

if __name__ == "__main__":
    print("Đang tạo vị thế thử nghiệm để kiểm tra hệ thống trailing stop...")
    create_test_position()