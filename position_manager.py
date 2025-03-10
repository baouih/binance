#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý vị thế giao dịch
"""

import os
import json
import time
import logging
import datetime
import traceback
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Union, Tuple, Any, Optional

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("position_manager")

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    from binance.enums import (
        SIDE_BUY, SIDE_SELL, 
        ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT,
        ORDER_TYPE_STOP_MARKET, ORDER_TYPE_TAKE_PROFIT_MARKET
    )
    logger.info("Đã import thành công thư viện Binance")
except ImportError as e:
    # Tạo lớp giả khi không import được
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        
        def futures_account_balance(self, **kwargs):
            return []
            
        def futures_position_information(self, **kwargs):
            return []
            
        def futures_get_open_orders(self, **kwargs):
            return []
            
        def futures_create_order(self, **kwargs):
            return {}
            
        def futures_cancel_order(self, **kwargs):
            return {}
    
    class BinanceAPIException(Exception):
        pass
    
    # Tạo enums giả
    SIDE_BUY = "BUY"
    SIDE_SELL = "SELL"
    ORDER_TYPE_MARKET = "MARKET"
    ORDER_TYPE_LIMIT = "LIMIT"
    ORDER_TYPE_STOP_MARKET = "STOP_MARKET"
    ORDER_TYPE_TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    logger.error(f"Lỗi khi import thư viện Binance: {str(e)}")
    # Các hằng số đã được định nghĩa ở trên

class PositionManager:
    """Quản lý vị thế giao dịch"""
    
    def __init__(self, testnet: bool = True):
        """
        Khởi tạo Position Manager
        
        :param testnet: Sử dụng testnet hay không
        """
        self.testnet = testnet
        self.client = self._create_client()
        
        logger.info("Đã khởi tạo Position Manager")
    
    def _create_client(self):
        """
        Tạo client Binance
        
        :return: Đối tượng Client
        """
        try:
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
            
            if not api_key or not api_secret:
                logger.error("Thiếu API Key hoặc API Secret")
                return None
            
            client = Client(api_key, api_secret, testnet=self.testnet)
            
            # Kiểm tra kết nối
            client.ping()
            
            logger.info("Đã kết nối thành công với Binance API")
            return client
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi kết nối với Binance API: {str(e)}")
            return None
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi tạo client: {str(e)}", exc_info=True)
            return None
    
    def get_account_balance(self) -> Dict[str, Any]:
        """
        Lấy thông tin số dư tài khoản
        
        :return: Dict với thông tin số dư
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return {"status": "error", "message": "Chưa kết nối với Binance API"}
            
            # Lấy thông tin tài khoản
            account = self.client.futures_account()
            
            # Tính toán tổng số dư và số dư khả dụng
            total_balance = float(account.get("totalWalletBalance", 0))
            unrealized_pnl = float(account.get("totalUnrealizedProfit", 0))
            position_initial_margin = float(account.get("totalPositionInitialMargin", 0))
            open_order_initial_margin = float(account.get("totalOpenOrderInitialMargin", 0))
            available_balance = total_balance - position_initial_margin - open_order_initial_margin
            max_withdraw_amount = float(account.get("maxWithdrawAmount", 0))
            
            # Kết quả
            result = {
                "status": "success",
                "balance": {
                    "total_balance": total_balance,
                    "available_balance": available_balance,
                    "unrealized_pnl": unrealized_pnl,
                    "position_initial_margin": position_initial_margin,
                    "open_order_initial_margin": open_order_initial_margin,
                    "max_withdraw_amount": max_withdraw_amount
                }
            }
            
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy thông tin số dư: {str(e)}")
            return {"status": "error", "message": str(e)}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy thông tin số dư: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def get_sl_tp(self, symbol: str) -> Dict[str, float]:
        """
        Lấy thông tin Stop Loss và Take Profit cho vị thế
        
        :param symbol: Cặp giao dịch
        :return: Dict với Stop Loss và Take Profit
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return {"stop_loss": None, "take_profit": None}
            
            # Lấy danh sách lệnh mở
            open_orders = self.client.futures_get_open_orders(symbol=symbol)
            
            stop_loss = None
            take_profit = None
            
            # Tìm lệnh Stop Loss và Take Profit
            for order in open_orders:
                order_type = order.get("type")
                
                if order_type == "STOP_MARKET":
                    stop_loss = float(order.get("stopPrice", 0))
                elif order_type == "TAKE_PROFIT_MARKET":
                    take_profit = float(order.get("stopPrice", 0))
            
            return {"stop_loss": stop_loss, "take_profit": take_profit}
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy thông tin SL/TP: {str(e)}")
            return {"stop_loss": None, "take_profit": None}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy thông tin SL/TP: {str(e)}", exc_info=True)
            return {"stop_loss": None, "take_profit": None}
    
    def open_position(self, symbol: str, side: str, amount: float,
                     stop_loss: float = None, take_profit: float = None,
                     leverage: int = 5) -> Dict[str, Any]:
        """
        Mở vị thế mới
        
        :param symbol: Cặp giao dịch
        :param side: Hướng giao dịch (LONG/SHORT)
        :param amount: Kích thước vị thế
        :param stop_loss: Giá Stop Loss (tùy chọn)
        :param take_profit: Giá Take Profit (tùy chọn)
        :param leverage: Đòn bẩy
        :return: Dict với kết quả
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return {"status": "error", "message": "Chưa kết nối với Binance API"}
            
            # Thiết lập đòn bẩy
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            # Lấy giá hiện tại
            symbol_ticker = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(symbol_ticker["price"])
            
            # Xác định hướng giao dịch
            if side == "LONG":
                binance_side = SIDE_BUY
                sl_side = SIDE_SELL
                tp_side = SIDE_SELL
            elif side == "SHORT":
                binance_side = SIDE_SELL
                sl_side = SIDE_BUY
                tp_side = SIDE_BUY
            else:
                return {"status": "error", "message": f"Hướng giao dịch không hợp lệ: {side}"}
            
            # Đặt lệnh mở vị thế
            order = self.client.futures_create_order(
                symbol=symbol,
                side=binance_side,
                type=ORDER_TYPE_MARKET,
                quantity=amount
            )
            
            # Nếu có Stop Loss, đặt lệnh Stop Loss
            if stop_loss:
                sl_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=sl_side,
                    type=ORDER_TYPE_STOP_MARKET,
                    stopPrice=stop_loss,
                    closePosition=True,
                    timeInForce="GTE_GTC"
                )
            
            # Nếu có Take Profit, đặt lệnh Take Profit
            if take_profit:
                tp_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=tp_side,
                    type=ORDER_TYPE_TAKE_PROFIT_MARKET,
                    stopPrice=take_profit,
                    closePosition=True,
                    timeInForce="GTE_GTC"
                )
            
            # Kết quả
            result = {
                "status": "success",
                "message": f"Đã mở vị thế {side} trên {symbol}",
                "order": order,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "entry_price": current_price
            }
            
            logger.info(f"Đã mở vị thế {side} trên {symbol} với giá {current_price}")
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi mở vị thế: {str(e)}")
            return {"status": "error", "message": str(e)}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi mở vị thế: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Đóng vị thế
        
        :param symbol: Cặp giao dịch
        :return: Dict với kết quả
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return {"status": "error", "message": "Chưa kết nối với Binance API"}
            
            # Hủy tất cả các lệnh mở
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            
            # Lấy thông tin vị thế
            position_info = self.get_position_info(symbol)
            
            # Đặt lệnh đóng vị thế
            order = self.client.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL if position_info["side"] == "LONG" else SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=abs(position_info["size"]),
                reduceOnly=True
            )
            
            # Kết quả
            result = {
                "status": "success",
                "message": f"Đã đóng vị thế trên {symbol}",
                "order": order,
                "profit": position_info["unrealized_pnl"],
                "profit_percent": position_info["profit_percent"]
            }
            
            logger.info(f"Đã đóng vị thế trên {symbol} với lợi nhuận {position_info['unrealized_pnl']:.2f} USDT")
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi đóng vị thế: {str(e)}")
            return {"status": "error", "message": str(e)}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi đóng vị thế: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def update_sl_tp(self, symbol: str, position_id: str = None,
                    stop_loss: float = None, take_profit: float = None) -> Dict[str, Any]:
        """
        Cập nhật Stop Loss và Take Profit
        
        :param symbol: Cặp giao dịch
        :param position_id: ID vị thế (tùy chọn)
        :param stop_loss: Giá Stop Loss mới (tùy chọn)
        :param take_profit: Giá Take Profit mới (tùy chọn)
        :return: Dict với kết quả
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return {"status": "error", "message": "Chưa kết nối với Binance API"}
            
            # Lấy thông tin vị thế
            position_info = self.get_position_info(symbol)
            
            if position_info["size"] == 0:
                return {"status": "error", "message": f"Không có vị thế mở trên {symbol}"}
            
            # Xác định hướng giao dịch
            side = position_info["side"]
            if side == "LONG":
                sl_side = SIDE_SELL
                tp_side = SIDE_SELL
            else:  # SHORT
                sl_side = SIDE_BUY
                tp_side = SIDE_BUY
            
            # Hủy các lệnh SL/TP hiện tại
            open_orders = self.client.futures_get_open_orders(symbol=symbol)
            
            for order in open_orders:
                order_type = order.get("type")
                if order_type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]:
                    self.client.futures_cancel_order(
                        symbol=symbol,
                        orderId=order.get("orderId")
                    )
            
            # Đặt lệnh Stop Loss mới nếu có
            if stop_loss is not None:
                sl_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=sl_side,
                    type=ORDER_TYPE_STOP_MARKET,
                    stopPrice=stop_loss,
                    closePosition=True,
                    timeInForce="GTE_GTC"
                )
            
            # Đặt lệnh Take Profit mới nếu có
            if take_profit is not None:
                tp_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=tp_side,
                    type=ORDER_TYPE_TAKE_PROFIT_MARKET,
                    stopPrice=take_profit,
                    closePosition=True,
                    timeInForce="GTE_GTC"
                )
            
            # Kết quả
            result = {
                "status": "success",
                "message": f"Đã cập nhật SL/TP cho {symbol}",
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
            
            logger.info(f"Đã cập nhật SL/TP cho {symbol}")
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi cập nhật SL/TP: {str(e)}")
            return {"status": "error", "message": str(e)}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi cập nhật SL/TP: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def get_position_history(self, symbol: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử giao dịch
        
        :param symbol: Cặp giao dịch (tùy chọn)
        :param limit: Số lượng giao dịch tối đa
        :return: List các giao dịch
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return []
            
            # Lấy lịch sử giao dịch
            if symbol:
                trades = self.client.futures_account_trades(symbol=symbol, limit=limit)
            else:
                trades = self.client.futures_account_trades(limit=limit)
            
            # Chuyển đổi dữ liệu
            result = []
            for trade in trades:
                # Chuyển đổi thời gian
                trade_time = datetime.datetime.fromtimestamp(trade.get("time", 0) / 1000)
                trade_time_str = trade_time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Thêm vào kết quả
                result.append({
                    "symbol": trade.get("symbol", ""),
                    "side": "LONG" if trade.get("side") == "BUY" else "SHORT",
                    "price": float(trade.get("price", 0)),
                    "quantity": float(trade.get("qty", 0)),
                    "commission": float(trade.get("commission", 0)),
                    "realized_pnl": float(trade.get("realizedPnl", 0)),
                    "time": trade_time_str
                })
            
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy lịch sử giao dịch: {str(e)}")
            return []
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy lịch sử giao dịch: {str(e)}", exc_info=True)
            return []
    
    def get_position_info(self, symbol: str) -> Dict[str, Any]:
        """
        Lấy thông tin vị thế
        
        :param symbol: Cặp giao dịch
        :return: Dict với thông tin vị thế
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return {"symbol": symbol, "side": "", "size": 0, "entry_price": 0, "mark_price": 0, "unrealized_pnl": 0, "profit_percent": 0}
            
            # Lấy thông tin tài khoản
            account = self.client.futures_account()
            
            # Tìm vị thế
            position = None
            for pos in account.get("positions", []):
                if pos.get("symbol") == symbol:
                    position = pos
                    break
            
            if not position:
                return {"symbol": symbol, "side": "", "size": 0, "entry_price": 0, "mark_price": 0, "unrealized_pnl": 0, "profit_percent": 0}
            
            # Tính toán thông tin vị thế
            size = float(position.get("positionAmt", 0))
            entry_price = float(position.get("entryPrice", 0))
            mark_price = float(position.get("markPrice", 0))
            unrealized_pnl = float(position.get("unrealizedProfit", 0))
            
            # Xác định hướng giao dịch
            side = ""
            if size > 0:
                side = "LONG"
            elif size < 0:
                side = "SHORT"
                size = abs(size)  # Lấy giá trị tuyệt đối
            
            # Tính toán phần trăm lợi nhuận
            profit_percent = 0
            if entry_price > 0 and size > 0:
                if side == "LONG":
                    profit_percent = (mark_price - entry_price) / entry_price * 100
                else:  # SHORT
                    profit_percent = (entry_price - mark_price) / entry_price * 100
            
            # Lấy thông tin SL/TP
            sl_tp = self.get_sl_tp(symbol)
            
            # Kết quả
            result = {
                "symbol": symbol,
                "side": side,
                "size": size,
                "entry_price": entry_price,
                "mark_price": mark_price,
                "unrealized_pnl": unrealized_pnl,
                "profit_percent": profit_percent,
                "stop_loss": sl_tp.get("stop_loss"),
                "take_profit": sl_tp.get("take_profit")
            }
            
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy thông tin vị thế: {str(e)}")
            return {"symbol": symbol, "side": "", "size": 0, "entry_price": 0, "mark_price": 0, "unrealized_pnl": 0, "profit_percent": 0}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy thông tin vị thế: {str(e)}", exc_info=True)
            return {"symbol": symbol, "side": "", "size": 0, "entry_price": 0, "mark_price": 0, "unrealized_pnl": 0, "profit_percent": 0}
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        Lấy tất cả các vị thế đang mở
        
        :return: List các vị thế
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return []
            
            # Lấy thông tin tài khoản
            account = self.client.futures_account()
            
            # Tìm tất cả các vị thế có số lượng khác 0
            positions = []
            for pos in account.get("positions", []):
                symbol = pos.get("symbol")
                size = float(pos.get("positionAmt", 0))
                
                if size != 0:
                    # Lấy thông tin chi tiết vị thế
                    position_info = self.get_position_info(symbol)
                    positions.append(position_info)
            
            return positions
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy tất cả các vị thế: {str(e)}")
            return []
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy tất cả các vị thế: {str(e)}", exc_info=True)
            return []