#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý vị thế giao dịch cho hệ thống giao dịch
Tương tác với Binance API để quản lý vị thế, đặt lệnh, và theo dõi
"""

import os
import logging
import time
import json
import traceback
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.enums import *

# Cấu hình logging
logger = logging.getLogger("position_manager")

class PositionManager:
    """
    Lớp quản lý vị thế, tương tác với Binance API
    để mở, đóng và quản lý vị thế giao dịch
    """
    
    def __init__(self, api_key=None, api_secret=None, testnet=True, risk_config=None):
        """
        Khởi tạo với thông tin API
        
        :param api_key: Binance API key
        :param api_secret: Binance API secret
        :param testnet: Sử dụng testnet (True) hoặc mainnet (False)
        :param risk_config: Cấu hình quản lý rủi ro
        """
        self.api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY")
        self.api_secret = api_secret or os.environ.get("BINANCE_TESTNET_API_SECRET")
        self.testnet = testnet
        self.client = None
        self.risk_config = risk_config or {}
        self.connect()
    
    def connect(self):
        """Kết nối tới Binance API"""
        try:
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet
            )
            # Kiểm tra kết nối
            self.client.ping()
            logger.info("✅ Kết nối Binance API thành công")
            return True
        except BinanceAPIException as e:
            logger.error(f"❌ Lỗi kết nối Binance API: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Lỗi không xác định khi kết nối Binance API: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def is_connected(self):
        """Kiểm tra xem API có kết nối không"""
        if not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def reconnect(self):
        """Kết nối lại nếu mất kết nối"""
        logger.info("Đang kết nối lại với Binance API...")
        return self.connect()
    
    def get_all_positions(self):
        """
        Lấy tất cả vị thế đang mở
        
        :return: List các vị thế đang mở
        """
        if not self.is_connected() and not self.reconnect():
            logger.error("Không thể kết nối tới Binance API")
            return []
        
        try:
            # Lấy thông tin tài khoản futures
            account = self.client.futures_account()
            
            # Lọc các vị thế có số lượng khác 0
            positions = []
            for position in account['positions']:
                position_amt = float(position['positionAmt'])
                if position_amt != 0:
                    symbol = position['symbol']
                    entry_price = float(position['entryPrice'])
                    mark_price = float(position['markPrice'])
                    unrealized_pnl = float(position['unrealizedProfit'])
                    leverage = int(position['leverage'])
                    
                    # Xác định hướng vị thế
                    side = "LONG" if position_amt > 0 else "SHORT"
                    
                    # Tính % lợi nhuận
                    if entry_price == 0:
                        profit_percent = 0
                    else:
                        if side == "LONG":
                            profit_percent = ((mark_price - entry_price) / entry_price) * 100 * leverage
                        else:
                            profit_percent = ((entry_price - mark_price) / entry_price) * 100 * leverage
                    
                    # Lấy thông tin SL/TP nếu có
                    open_orders = self.client.futures_get_open_orders(symbol=symbol)
                    stop_loss = None
                    take_profit = None
                    
                    for order in open_orders:
                        order_type = order['type']
                        order_side = order['side']
                        
                        # SL cho vị thế LONG là SELL STOP, cho SHORT là BUY STOP
                        is_sl = (side == "LONG" and order_side == "SELL" and order_type == "STOP_MARKET") or \
                                (side == "SHORT" and order_side == "BUY" and order_type == "STOP_MARKET")
                        
                        # TP cho vị thế LONG là SELL LIMIT, cho SHORT là BUY LIMIT
                        is_tp = (side == "LONG" and order_side == "SELL" and order_type == "LIMIT") or \
                                (side == "SHORT" and order_side == "BUY" and order_type == "LIMIT")
                        
                        if is_sl:
                            stop_loss = float(order['stopPrice'])
                        elif is_tp:
                            take_profit = float(order['price'])
                    
                    position_info = {
                        "symbol": symbol,
                        "side": side,
                        "entry_price": entry_price,
                        "mark_price": mark_price,
                        "amount": abs(position_amt),
                        "leverage": leverage,
                        "unrealized_pnl": unrealized_pnl,
                        "profit_percent": profit_percent,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit
                    }
                    
                    positions.append(position_info)
            
            return positions
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API khi lấy vị thế: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy vị thế: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def open_position(self, symbol, side, amount, leverage=None, stop_loss=None, take_profit=None):
        """
        Mở vị thế mới
        
        :param symbol: Cặp tiền, ví dụ BTCUSDT
        :param side: Hướng vị thế ("LONG" hoặc "SHORT")
        :param amount: Số lượng (đơn vị là USDT nếu dùng QUANTITY_TYPE="USDT")
        :param leverage: Đòn bẩy (nếu None, sẽ dùng leverage từ risk_config)
        :param stop_loss: Mức stop loss (giá)
        :param take_profit: Mức take profit (giá)
        :return: Dict thông tin vị thế hoặc lỗi
        """
        if not self.is_connected() and not self.reconnect():
            logger.error("Không thể kết nối tới Binance API")
            return {"status": "error", "message": "Không thể kết nối tới Binance API"}
        
        try:
            # Kiểm tra số lượng vị thế đang mở
            current_positions = self.get_all_positions()
            max_positions = self.risk_config.get("max_open_positions", 5)
            
            if len(current_positions) >= max_positions:
                logger.warning(f"Đã đạt giới hạn vị thế tối đa ({max_positions})")
                return {"status": "error", "message": f"Đã đạt giới hạn vị thế tối đa ({max_positions})"}
            
            # Đặt leverage
            lev = leverage or self.risk_config.get("leverage", 1)
            self.client.futures_change_leverage(symbol=symbol, leverage=lev)
            
            # Lấy thông tin giá hiện tại
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Tính số lượng dựa trên USDT amount
            # Trong thực tế, cần kiểm tra precision và quantity_step_size từ exchange info
            precision = 3  # Tạm thời cứng, trong thực tế cần lấy từ exchange info
            if side == "LONG":
                binance_side = "BUY"
            else:  # SHORT
                binance_side = "SELL"
            
            # Tính toán số lượng base coin dựa trên số tiền USDT
            quantity = amount / current_price
            quantity = round(quantity, precision)
            
            # Đặt lệnh thị trường để mở vị thế
            order = self.client.futures_create_order(
                symbol=symbol,
                side=binance_side,
                type="MARKET",
                quantity=quantity
            )
            
            logger.info(f"Đã mở vị thế {side} trên {symbol} với số lượng {quantity} ({amount} USDT)")
            
            # Nếu có SL, đặt lệnh SL
            if stop_loss:
                sl_side = "SELL" if side == "LONG" else "BUY"
                sl_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=sl_side,
                    type="STOP_MARKET",
                    quantity=quantity,
                    stopPrice=stop_loss,
                    reduceOnly=True
                )
                logger.info(f"Đã đặt Stop Loss tại {stop_loss} cho vị thế {side} trên {symbol}")
            
            # Nếu có TP, đặt lệnh TP
            if take_profit:
                tp_side = "SELL" if side == "LONG" else "BUY"
                tp_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=tp_side,
                    type="LIMIT",
                    timeInForce="GTC",
                    quantity=quantity,
                    price=take_profit,
                    reduceOnly=True
                )
                logger.info(f"Đã đặt Take Profit tại {take_profit} cho vị thế {side} trên {symbol}")
            
            return {
                "status": "success",
                "order": order,
                "position": {
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "quantity": quantity,
                    "leverage": lev,
                    "entry_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit
                }
            }
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API khi mở vị thế: {str(e)}")
            return {"status": "error", "message": f"Lỗi Binance API: {str(e)}"}
        except Exception as e:
            logger.error(f"Lỗi không xác định khi mở vị thế: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}
    
    def close_position(self, symbol, side):
        """
        Đóng vị thế
        
        :param symbol: Cặp tiền, ví dụ BTCUSDT
        :param side: Hướng vị thế ("LONG" hoặc "SHORT")
        :return: Dict kết quả đóng vị thế
        """
        if not self.is_connected() and not self.reconnect():
            logger.error("Không thể kết nối tới Binance API")
            return {"status": "error", "message": "Không thể kết nối tới Binance API"}
        
        try:
            # Lấy thông tin vị thế
            positions = self.get_all_positions()
            position = None
            
            for pos in positions:
                if pos["symbol"] == symbol and pos["side"] == side:
                    position = pos
                    break
            
            if not position:
                logger.warning(f"Không tìm thấy vị thế {side} trên {symbol}")
                return {"status": "error", "message": f"Không tìm thấy vị thế {side} trên {symbol}"}
            
            # Đặt lệnh market để đóng vị thế
            close_side = "SELL" if side == "LONG" else "BUY"
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=close_side,
                type="MARKET",
                quantity=position["amount"],
                reduceOnly=True
            )
            
            # Hủy tất cả các lệnh SL/TP đang chờ
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            
            logger.info(f"Đã đóng vị thế {side} trên {symbol}")
            
            return {
                "status": "success",
                "order": order,
                "message": f"Đã đóng vị thế {side} trên {symbol}"
            }
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API khi đóng vị thế: {str(e)}")
            return {"status": "error", "message": f"Lỗi Binance API: {str(e)}"}
        except Exception as e:
            logger.error(f"Lỗi không xác định khi đóng vị thế: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}
    
    def close_all_positions(self):
        """
        Đóng tất cả vị thế đang mở
        
        :return: Dict kết quả đóng vị thế
        """
        if not self.is_connected() and not self.reconnect():
            logger.error("Không thể kết nối tới Binance API")
            return {"status": "error", "message": "Không thể kết nối tới Binance API"}
        
        try:
            # Lấy tất cả vị thế đang mở
            positions = self.get_all_positions()
            
            if not positions:
                logger.info("Không có vị thế nào đang mở")
                return {"status": "success", "message": "Không có vị thế nào đang mở"}
            
            results = []
            
            # Đóng từng vị thế
            for position in positions:
                symbol = position["symbol"]
                side = position["side"]
                
                # Đóng vị thế
                result = self.close_position(symbol, side)
                results.append(result)
            
            return {
                "status": "success",
                "results": results,
                "message": f"Đã đóng {len(results)} vị thế"
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi đóng tất cả vị thế: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}
    
    def update_sl_tp(self, symbol, side, stop_loss=None, take_profit=None):
        """
        Cập nhật Stop Loss và Take Profit cho vị thế
        
        :param symbol: Cặp tiền, ví dụ BTCUSDT
        :param side: Hướng vị thế ("LONG" hoặc "SHORT")
        :param stop_loss: Mức stop loss mới (giá)
        :param take_profit: Mức take profit mới (giá)
        :return: Dict kết quả cập nhật
        """
        if not self.is_connected() and not self.reconnect():
            logger.error("Không thể kết nối tới Binance API")
            return {"status": "error", "message": "Không thể kết nối tới Binance API"}
        
        try:
            # Lấy thông tin vị thế
            positions = self.get_all_positions()
            position = None
            
            for pos in positions:
                if pos["symbol"] == symbol and pos["side"] == side:
                    position = pos
                    break
            
            if not position:
                logger.warning(f"Không tìm thấy vị thế {side} trên {symbol}")
                return {"status": "error", "message": f"Không tìm thấy vị thế {side} trên {symbol}"}
            
            # Hủy các lệnh SL/TP hiện tại
            open_orders = self.client.futures_get_open_orders(symbol=symbol)
            
            for order in open_orders:
                order_type = order['type']
                if order_type in ["STOP_MARKET", "LIMIT"]:
                    self.client.futures_cancel_order(
                        symbol=symbol,
                        orderId=order['orderId']
                    )
            
            results = {"status": "success", "message": "Đã cập nhật SL/TP"}
            
            # Đặt SL mới nếu có
            if stop_loss is not None:
                sl_side = "SELL" if side == "LONG" else "BUY"
                sl_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=sl_side,
                    type="STOP_MARKET",
                    quantity=position["amount"],
                    stopPrice=stop_loss,
                    reduceOnly=True
                )
                results["stop_loss"] = stop_loss
                logger.info(f"Đã cập nhật Stop Loss tại {stop_loss} cho vị thế {side} trên {symbol}")
            
            # Đặt TP mới nếu có
            if take_profit is not None:
                tp_side = "SELL" if side == "LONG" else "BUY"
                tp_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=tp_side,
                    type="LIMIT",
                    timeInForce="GTC",
                    quantity=position["amount"],
                    price=take_profit,
                    reduceOnly=True
                )
                results["take_profit"] = take_profit
                logger.info(f"Đã cập nhật Take Profit tại {take_profit} cho vị thế {side} trên {symbol}")
            
            return results
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi Binance API khi cập nhật SL/TP: {str(e)}")
            return {"status": "error", "message": f"Lỗi Binance API: {str(e)}"}
        except Exception as e:
            logger.error(f"Lỗi không xác định khi cập nhật SL/TP: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}

# Hàm để thử nghiệm module
def test_position_manager():
    """Hàm kiểm tra chức năng của PositionManager"""
    # Cấu hình logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Load risk config
    try:
        with open("risk_configs/risk_level_10.json", "r") as f:
            risk_config = json.load(f)
    except:
        risk_config = {
            "position_size_percent": 1,
            "stop_loss_percent": 1,
            "take_profit_percent": 2,
            "leverage": 1,
            "max_open_positions": 2
        }
    
    print("Đang kiểm tra PositionManager...")
    position_manager = PositionManager(testnet=True, risk_config=risk_config)
    
    if not position_manager.is_connected():
        print("❌ Không thể kết nối tới Binance API")
        return
    
    print("✅ Đã kết nối tới Binance API")
    
    # Kiểm tra vị thế hiện tại
    positions = position_manager.get_all_positions()
    print(f"Số vị thế đang mở: {len(positions)}")
    for pos in positions:
        print(f"  - {pos['symbol']} {pos['side']}: Entry: {pos['entry_price']}, Mark: {pos['mark_price']}, P/L: {pos['profit_percent']:.2f}%")
    
    # Test mở vị thế (có thể bỏ comment để test)
    """
    symbol = "BTCUSDT"
    side = "LONG"
    amount = 10  # USDT
    
    # Tính SL/TP
    ticker = position_manager.client.futures_symbol_ticker(symbol=symbol)
    current_price = float(ticker['price'])
    
    sl_percent = risk_config["stop_loss_percent"] / 100
    tp_percent = risk_config["take_profit_percent"] / 100
    
    if side == "LONG":
        stop_loss = current_price * (1 - sl_percent)
        take_profit = current_price * (1 + tp_percent)
    else:
        stop_loss = current_price * (1 + sl_percent)
        take_profit = current_price * (1 - tp_percent)
    
    # Mở vị thế
    result = position_manager.open_position(
        symbol=symbol,
        side=side,
        amount=amount,
        stop_loss=stop_loss,
        take_profit=take_profit
    )
    
    if result["status"] == "success":
        print(f"✅ Đã mở vị thế {side} trên {symbol}")
        print(f"  - Entry: {result['position']['entry_price']}")
        print(f"  - SL: {result['position']['stop_loss']}")
        print(f"  - TP: {result['position']['take_profit']}")
    else:
        print(f"❌ Lỗi khi mở vị thế: {result.get('message', 'Unknown error')}")
    """

if __name__ == "__main__":
    test_position_manager()