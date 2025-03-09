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
        # Tải cấu hình tài khoản
        try:
            with open('account_config.json', 'r') as file:
                config = json.load(file)
        except Exception as e:
            logger.error(f"Lỗi khi tải file cấu hình: {str(e)}")
            config = {}

        # Khởi tạo Binance API
        api = BinanceAPI(
            account_type=config.get('account_type', 'futures'),
            testnet=(config.get('api_mode', 'testnet') == 'testnet')
        )
        
        # Lấy thông tin số dư tài khoản
        account_balance = api.futures_account_balance()
        available_balance = 0
        
        for balance in account_balance:
            if balance.get('asset') == 'USDT':
                available_balance = float(balance.get('availableBalance', 0))
                break
        
        logger.info(f"Số dư tài khoản: {available_balance} USDT, Khả dụng: {available_balance} USDT")
        
        if available_balance < 100:
            logger.warning(f"Số dư khả dụng thấp: {available_balance} USDT, nên có ít nhất 100 USDT")
        
        # Thông tin vị thế thử nghiệm
        symbol = "BTCUSDT"
        side = "BUY"  # BUY = LONG, SELL = SHORT
        leverage = config.get('leverage', 5)
        risk_percent = 2.5  # % số dư tài khoản
        
        # Lấy giá hiện tại
        ticker = api.get_symbol_ticker(symbol)
        if not ticker or 'price' not in ticker:
            logger.error(f"Không thể lấy giá hiện tại của {symbol}")
            return False
        
        current_price = float(ticker['price'])
        logger.info(f"Giá hiện tại của {symbol}: {current_price} USDT")
        
        # Đặt đòn bẩy
        try:
            api.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"Đã đặt đòn bẩy {leverage}x cho {symbol}")
        except Exception as e:
            logger.warning(f"Lỗi khi đặt đòn bẩy: {str(e)}")
        
        # Tính toán số lượng dựa trên mức rủi ro
        risk_amount = available_balance * (risk_percent / 100)
        position_size_usd = risk_amount * leverage  # Giá trị giao dịch với đòn bẩy
        
        # Đảm bảo position_size_usd đáp ứng MIN_NOTIONAL = 100 USDT cho BTCUSDT
        min_notional = 100  # USDT - giá trị giao dịch tối thiểu cho BTCUSDT
        if position_size_usd < min_notional:
            logger.warning(f"Giá trị giao dịch {position_size_usd:.2f} USDT thấp hơn MIN_NOTIONAL ({min_notional} USDT), điều chỉnh lên mức tối thiểu")
            position_size_usd = min_notional
        
        quantity = position_size_usd / current_price  # Số lượng coin cần mua
        
        # Binance Futures BTCUSDT có lượng giao dịch tối thiểu là 0.001 BTC
        min_qty = 0.001
        
        # Đảm bảo số lượng ít nhất là 0.001 BTC
        quantity = max(min_qty, quantity)
        
        # Kiểm tra thông tin lô tối thiểu trong cấu hình
        min_trade_sizes = config.get('min_trade_sizes', {})
        symbol_min_trade_info = min_trade_sizes.get(symbol, {})
        
        if symbol_min_trade_info:
            logger.info(f"Sử dụng thông tin giao dịch tối thiểu từ cấu hình cho {symbol}")
            min_qty = float(symbol_min_trade_info.get('min_qty', 0.001))
            step_size = float(symbol_min_trade_info.get('step_size', 0.001))
            precision = int(symbol_min_trade_info.get('precision', 3))
            
            # Đảm bảo số lượng ít nhất là min_qty
            quantity = max(min_qty, quantity)
            
            # Làm tròn theo step_size
            quantity = round(quantity - (quantity % step_size), precision)
        else:
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
                        
                        # Xác định số chữ số thập phân
                        precision = 0
                        if '.' in str(step_size):
                            precision = len(str(step_size).split('.')[1])
                        
                        # Làm tròn số lượng theo stepSize
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