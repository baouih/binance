#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý vị thế
"""

import os
import json
import time
import math
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union, Any

# Thiết lập logging
logger = logging.getLogger("position_manager")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

try:
    # Sử dụng python-binance cho việc gọi API
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    from binance.enums import *
    
    # Ghi log nếu import thành công
    logger.info("Đã import các thư viện cần thiết")
except ImportError as e:
    logger.error(f"Lỗi khi import thư viện: {str(e)}")

class PositionManager:
    """
    Lớp quản lý vị thế giao dịch sử dụng API Binance
    """
    def __init__(self, testnet=True, risk_config=None):
        """
        Khởi tạo quản lý vị thế
        
        :param testnet: Sử dụng testnet hay không
        :param risk_config: Cấu hình rủi ro
        """
        self.testnet = testnet
        self.client = None
        self.initialized = False
        self.risk_config = risk_config or {}
        
        # Khởi tạo API client
        self.initialize_client()
    
    def initialize_client(self):
        """Khởi tạo client API"""
        try:
            # Lấy khóa API từ biến môi trường
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
            
            if not api_key or not api_secret:
                logger.warning("API key hoặc API secret không được cung cấp")
                return
            
            # Khởi tạo client
            self.client = Client(api_key, api_secret, testnet=self.testnet)
            
            # Test kết nối
            self.client.get_account()
            
            self.initialized = True
            logger.info("Đã khởi tạo Binance API client thành công")
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo client: {str(e)}")
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách tất cả các vị thế đang mở
        
        :return: List các vị thế đang mở
        """
        if not self.initialized:
            logger.error("API client chưa được khởi tạo")
            return []
        
        try:
            # Lấy thông tin tài khoản futures
            account_info = self.client.futures_account()
            
            # Lấy thông tin vị thế
            positions = []
            
            for position in account_info["positions"]:
                # Chỉ lấy các vị thế có số lượng khác 0
                if float(position["positionAmt"]) != 0:
                    # Tính toán lợi nhuận
                    entry_price = float(position["entryPrice"])
                    mark_price = float(position["markPrice"])
                    position_amt = float(position["positionAmt"])
                    
                    # Xác định hướng (LONG/SHORT)
                    side = "LONG" if position_amt > 0 else "SHORT"
                    
                    # Tính lợi nhuận theo %
                    if side == "LONG":
                        profit_percent = (mark_price / entry_price - 1) * 100
                    else:  # SHORT
                        profit_percent = (1 - mark_price / entry_price) * 100
                    
                    # Lấy SL và TP nếu có
                    sl_tp = self.get_sltp_for_position(position["symbol"])
                    
                    position_data = {
                        "symbol": position["symbol"],
                        "side": side,
                        "size": abs(position_amt),
                        "entry_price": entry_price,
                        "mark_price": mark_price,
                        "unrealized_pnl": float(position["unrealizedProfit"]),
                        "profit_percent": profit_percent,
                        "leverage": float(position["leverage"]),
                        "stop_loss": sl_tp.get("stop_loss"),
                        "take_profit": sl_tp.get("take_profit")
                    }
                    
                    positions.append(position_data)
            
            return positions
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách vị thế: {str(e)}")
            return []
    
    def get_sltp_for_position(self, symbol: str) -> Dict[str, float]:
        """
        Lấy Stop Loss và Take Profit cho một vị thế
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :return: Dict với SL và TP
        """
        if not self.initialized:
            logger.error("API client chưa được khởi tạo")
            return {"stop_loss": None, "take_profit": None}
        
        try:
            # Lấy danh sách lệnh đang mở
            open_orders = self.client.futures_get_open_orders(symbol=symbol)
            
            # Tìm SL và TP
            stop_loss = None
            take_profit = None
            
            for order in open_orders:
                # Kiểm tra xem đây có phải là SL hoặc TP không
                if order["type"] == "STOP_MARKET" or order["type"] == "STOP":
                    stop_loss = float(order["stopPrice"])
                elif order["type"] == "TAKE_PROFIT_MARKET" or order["type"] == "TAKE_PROFIT":
                    take_profit = float(order["stopPrice"])
            
            return {"stop_loss": stop_loss, "take_profit": take_profit}
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance khi lấy SL/TP cho {symbol}: {str(e)}")
            return {"stop_loss": None, "take_profit": None}
        except Exception as e:
            logger.error(f"Lỗi khi lấy SL/TP cho {symbol}: {str(e)}")
            return {"stop_loss": None, "take_profit": None}
    
    def open_position(self, symbol: str, side: str, amount: float, stop_loss: float = None, take_profit: float = None, leverage: int = None) -> Dict[str, Any]:
        """
        Mở một vị thế mới
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param side: Hướng giao dịch (LONG hoặc SHORT)
        :param amount: Số lượng
        :param stop_loss: Giá Stop Loss (tùy chọn)
        :param take_profit: Giá Take Profit (tùy chọn)
        :param leverage: Đòn bẩy (tùy chọn)
        :return: Dict kết quả
        """
        if not self.initialized:
            return {"status": "error", "message": "API client chưa được khởi tạo"}
        
        try:
            # Thiết lập đòn bẩy nếu được cung cấp
            if leverage is not None:
                self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
                logger.info(f"Đã thiết lập đòn bẩy cho {symbol}: {leverage}x")
            
            # Lấy giá hiện tại
            symbol_price = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(symbol_price["price"])
            
            # Xác định hướng giao dịch
            if side == "LONG":
                binance_side = SIDE_BUY
                opposite_side = SIDE_SELL
                sl_side = SIDE_SELL
                tp_side = SIDE_SELL
            else:  # SHORT
                binance_side = SIDE_SELL
                opposite_side = SIDE_BUY
                sl_side = SIDE_BUY
                tp_side = SIDE_BUY
            
            # Đặt lệnh thị trường
            order = self.client.futures_create_order(
                symbol=symbol,
                side=binance_side,
                type=ORDER_TYPE_MARKET,
                quantity=amount
            )
            
            logger.info(f"Đã đặt lệnh {side} cho {symbol} với số lượng {amount}")
            
            # Đặt Stop Loss nếu có
            if stop_loss is not None:
                sl_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=sl_side,
                    type=ORDER_TYPE_STOP_MARKET,
                    stopPrice=stop_loss,
                    closePosition=True
                )
                
                logger.info(f"Đã đặt Stop Loss cho {symbol} {side} tại giá {stop_loss}")
            
            # Đặt Take Profit nếu có
            if take_profit is not None:
                tp_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=tp_side,
                    type=ORDER_TYPE_TAKE_PROFIT_MARKET,
                    stopPrice=take_profit,
                    closePosition=True
                )
                
                logger.info(f"Đã đặt Take Profit cho {symbol} {side} tại giá {take_profit}")
            
            return {
                "status": "success",
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "leverage": leverage,
                "order_id": order["orderId"]
            }
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Lỗi khi mở vị thế: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Đóng một vị thế
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :return: Dict kết quả
        """
        if not self.initialized:
            return {"status": "error", "message": "API client chưa được khởi tạo"}
        
        try:
            # Lấy thông tin vị thế
            positions = self.get_all_positions()
            position = next((p for p in positions if p["symbol"] == symbol), None)
            
            if not position:
                return {"status": "error", "message": f"Không tìm thấy vị thế cho {symbol}"}
            
            # Đóng các lệnh đang mở trước
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            
            # Xác định hướng đóng
            close_side = "SELL" if position["side"] == "LONG" else "BUY"
            
            # Đặt lệnh đóng
            order = self.client.futures_create_order(
                symbol=symbol,
                side=close_side,
                type=ORDER_TYPE_MARKET,
                quantity=position["size"],
                reduceOnly=True
            )
            
            logger.info(f"Đã đóng vị thế {position['side']} trên {symbol}")
            
            return {
                "status": "success",
                "symbol": symbol,
                "side": position["side"],
                "amount": position["size"],
                "close_price": position["mark_price"],
                "profit": position["unrealized_pnl"],
                "profit_percent": position["profit_percent"],
                "order_id": order["orderId"]
            }
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Lỗi khi đóng vị thế: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def update_sl_tp(self, symbol: str, side: str = None, stop_loss: float = None, take_profit: float = None) -> Dict[str, Any]:
        """
        Cập nhật Stop Loss và Take Profit cho một vị thế
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param side: Hướng giao dịch (LONG hoặc SHORT), nếu không có sẽ tự động xác định
        :param stop_loss: Giá Stop Loss mới (tùy chọn)
        :param take_profit: Giá Take Profit mới (tùy chọn)
        :return: Dict kết quả
        """
        if not self.initialized:
            return {"status": "error", "message": "API client chưa được khởi tạo"}
        
        if stop_loss is None and take_profit is None:
            return {"status": "error", "message": "Phải cung cấp ít nhất một trong hai giá trị Stop Loss hoặc Take Profit"}
        
        try:
            # Lấy thông tin vị thế nếu không có side
            if side is None:
                positions = self.get_all_positions()
                position = next((p for p in positions if p["symbol"] == symbol), None)
                
                if not position:
                    return {"status": "error", "message": f"Không tìm thấy vị thế cho {symbol}"}
                
                side = position["side"]
            
            # Xác định hướng giao dịch
            if side == "LONG":
                sl_side = SIDE_SELL
                tp_side = SIDE_SELL
            else:  # SHORT
                sl_side = SIDE_BUY
                tp_side = SIDE_BUY
            
            # Lấy danh sách lệnh đang mở
            open_orders = self.client.futures_get_open_orders(symbol=symbol)
            
            # Hủy các lệnh SL/TP hiện tại
            for order in open_orders:
                if order["type"] in ["STOP_MARKET", "STOP", "TAKE_PROFIT_MARKET", "TAKE_PROFIT"]:
                    self.client.futures_cancel_order(
                        symbol=symbol,
                        orderId=order["orderId"]
                    )
            
            # Đặt Stop Loss mới nếu có
            if stop_loss is not None:
                sl_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=sl_side,
                    type=ORDER_TYPE_STOP_MARKET,
                    stopPrice=stop_loss,
                    closePosition=True
                )
                
                logger.info(f"Đã cập nhật Stop Loss cho {symbol} {side} tại giá {stop_loss}")
            
            # Đặt Take Profit mới nếu có
            if take_profit is not None:
                tp_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=tp_side,
                    type=ORDER_TYPE_TAKE_PROFIT_MARKET,
                    stopPrice=take_profit,
                    closePosition=True
                )
                
                logger.info(f"Đã cập nhật Take Profit cho {symbol} {side} tại giá {take_profit}")
            
            return {
                "status": "success",
                "symbol": symbol,
                "side": side,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật SL/TP: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def get_position_history(self, symbol: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử giao dịch
        
        :param symbol: Cặp giao dịch (tùy chọn)
        :param limit: Số lượng giao dịch tối đa
        :return: List các giao dịch
        """
        if not self.initialized:
            logger.error("API client chưa được khởi tạo")
            return []
        
        try:
            # Lấy lịch sử giao dịch
            trades = self.client.futures_account_trades(symbol=symbol, limit=limit) if symbol else self.client.futures_account_trades(limit=limit)
            
            # Chuyển đổi dữ liệu
            history = []
            
            for trade in trades:
                history.append({
                    "symbol": trade["symbol"],
                    "side": "LONG" if trade["side"] == "BUY" else "SHORT",
                    "price": float(trade["price"]),
                    "quantity": float(trade["qty"]),
                    "commission": float(trade["commission"]),
                    "realized_pnl": float(trade["realizedPnl"]),
                    "time": datetime.fromtimestamp(trade["time"] / 1000).strftime("%Y-%m-%d %H:%M:%S")
                })
            
            return history
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Lỗi khi lấy lịch sử giao dịch: {str(e)}")
            return []
    
    def get_account_balance(self) -> Dict[str, Any]:
        """
        Lấy số dư tài khoản
        
        :return: Dict với số dư tài khoản
        """
        if not self.initialized:
            return {"status": "error", "message": "API client chưa được khởi tạo"}
        
        try:
            # Lấy thông tin tài khoản futures
            account_info = self.client.futures_account()
            
            # Tạo dữ liệu trả về
            balance_data = {
                "total_balance": float(account_info["totalWalletBalance"]),
                "unrealized_pnl": float(account_info["totalUnrealizedProfit"]),
                "margin_balance": float(account_info["totalMarginBalance"]),
                "available_balance": float(account_info["availableBalance"]),
                "position_initial_margin": float(account_info["totalPositionInitialMargin"]),
                "open_order_initial_margin": float(account_info["totalOpenOrderInitialMargin"]),
                "max_withdraw_amount": float(account_info["maxWithdrawAmount"])
            }
            
            return {"status": "success", "balance": balance_data}
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Lỗi khi lấy số dư tài khoản: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def partial_close_position(self, symbol: str, percentage: float) -> Dict[str, Any]:
        """
        Đóng một phần vị thế
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param percentage: Phần trăm vị thế cần đóng (0-100)
        :return: Dict kết quả
        """
        if not self.initialized:
            return {"status": "error", "message": "API client chưa được khởi tạo"}
        
        if percentage <= 0 or percentage > 100:
            return {"status": "error", "message": "Phần trăm phải nằm trong khoảng (0, 100]"}
        
        try:
            # Lấy thông tin vị thế
            positions = self.get_all_positions()
            position = next((p for p in positions if p["symbol"] == symbol), None)
            
            if not position:
                return {"status": "error", "message": f"Không tìm thấy vị thế cho {symbol}"}
            
            # Tính toán số lượng cần đóng
            close_amount = position["size"] * percentage / 100
            
            # Làm tròn số lượng
            precision = 8  # Mặc định, có thể thay đổi tùy theo cặp
            close_amount = math.floor(close_amount * 10**precision) / 10**precision
            
            # Xác định hướng đóng
            close_side = "SELL" if position["side"] == "LONG" else "BUY"
            
            # Đặt lệnh đóng một phần
            order = self.client.futures_create_order(
                symbol=symbol,
                side=close_side,
                type=ORDER_TYPE_MARKET,
                quantity=close_amount,
                reduceOnly=True
            )
            
            logger.info(f"Đã đóng {percentage}% vị thế {position['side']} trên {symbol}")
            
            return {
                "status": "success",
                "symbol": symbol,
                "side": position["side"],
                "close_amount": close_amount,
                "percentage": percentage,
                "close_price": position["mark_price"],
                "order_id": order["orderId"]
            }
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Lỗi khi đóng một phần vị thế: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}

# Hàm kiểm tra kết nối
def test_position_manager():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Đang kiểm tra PositionManager...")
    
    # Tạo instance
    manager = PositionManager(testnet=True)
    
    # Kiểm tra kết nối
    logger.info("Đang lấy danh sách vị thế...")
    positions = manager.get_all_positions()
    logger.info(f"Số lượng vị thế đang mở: {len(positions)}")
    
    for position in positions:
        logger.info(f"Vị thế: {position['symbol']} {position['side']} - Size: {position['size']} - PnL: {position['unrealized_pnl']:.2f} ({position['profit_percent']:.2f}%)")
    
    # Lấy số dư tài khoản
    logger.info("Đang lấy số dư tài khoản...")
    balance = manager.get_account_balance()
    if balance["status"] == "success":
        logger.info(f"Số dư: {balance['balance']['total_balance']} USDT")
        logger.info(f"Unrealized PnL: {balance['balance']['unrealized_pnl']} USDT")
        logger.info(f"Số dư khả dụng: {balance['balance']['available_balance']} USDT")
    else:
        logger.error(f"Lỗi: {balance.get('message', 'Không rõ lỗi')}")

if __name__ == "__main__":
    test_position_manager()