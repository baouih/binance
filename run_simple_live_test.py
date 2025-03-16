#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script đơn giản để chạy thử nghiệm trên dữ liệu thực với Binance Testnet
"""

import os
import time
import json
import logging
import datetime
from typing import Dict, List, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simple_live_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SimpleLiveTest')

class SimpleLiveTest:
    """
    Lớp thực hiện thử nghiệm đơn giản với chiến lược Single Direction
    trên các cặp tiền thanh khoản cao
    """
    
    def __init__(self, initial_balance=10000):
        """
        Khởi tạo thử nghiệm
        
        Args:
            initial_balance: Số dư ban đầu (USDT)
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        
        # Danh sách các coin thanh khoản cao
        self.coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT", "XRPUSDT"]
        
        # Thời gian giao dịch tối ưu từ backtest
        self.optimal_sessions = [
            {"name": "London Open", "start_time": "15:00", "end_time": "17:00", "direction": "SHORT", "win_rate": 95.0},
            {"name": "New York Open", "start_time": "20:30", "end_time": "22:30", "direction": "SHORT", "win_rate": 90.0},
            {"name": "Major News Events", "start_time": "21:30", "end_time": "22:00", "direction": "SHORT", "win_rate": 80.0},
            {"name": "Daily Candle Close", "start_time": "06:30", "end_time": "07:30", "direction": "LONG", "win_rate": 75.0},
            {"name": "London/NY Close", "start_time": "03:00", "end_time": "05:00", "direction": "BOTH", "win_rate": 70.0}
        ]
        
        # Kết nối đến Binance API
        self._setup_binance_api()
        
        # Danh sách các giao dịch
        self.trades = []
        
        # Thống kê
        self.stats = {
            "total_trades": 0,
            "win_trades": 0,
            "loss_trades": 0,
            "win_rate": 0,
            "profit_loss": 0,
            "profit_loss_percent": 0,
            "max_drawdown": 0,
            "by_symbol": {},
            "by_session": {}
        }
        
        # Khởi tạo thống kê cho từng coin và từng phiên
        for coin in self.coins:
            self.stats["by_symbol"][coin] = {
                "total_trades": 0,
                "win_trades": 0,
                "loss_trades": 0,
                "win_rate": 0,
                "profit_loss": 0,
                "profit_loss_percent": 0
            }
        
        for session in self.optimal_sessions:
            self.stats["by_session"][session["name"]] = {
                "total_trades": 0,
                "win_trades": 0,
                "loss_trades": 0,
                "win_rate": 0,
                "profit_loss": 0,
                "profit_loss_percent": 0
            }
        
        logger.info(f"Đã khởi tạo SimpleLiveTest với số dư ban đầu {initial_balance} USDT")
    
    def _setup_binance_api(self):
        """
        Thiết lập kết nối đến Binance API
        """
        try:
            # Import BinanceAPI từ module hiện có
            try:
                from binance_api import BinanceAPI
                self.api = BinanceAPI(testnet=True)
                logger.info("Đã sử dụng BinanceAPI từ module binance_api")
            except ImportError:
                # Nếu không có, sử dụng python-binance trực tiếp
                from binance.um_futures import UMFutures
                
                api_key = os.environ.get('BINANCE_API_KEY')
                api_secret = os.environ.get('BINANCE_API_SECRET')
                
                self.api = UMFutures(
                    key=api_key,
                    secret=api_secret,
                    base_url="https://testnet.binancefuture.com"
                )
                logger.info("Đã sử dụng UMFutures từ thư viện binance-futures-connector")
            
            # Kiểm tra kết nối
            if hasattr(self.api, 'ping'):
                self.api.ping()
            logger.info("Đã kết nối thành công đến Binance Testnet API")
            
            # Kiểm tra số dư tài khoản
            account_info = self._get_account_info()
            available_balance = float(account_info.get('availableBalance', 0))
            logger.info(f"Số dư khả dụng trên tài khoản Testnet: {available_balance} USDT")
            
        except Exception as e:
            logger.error(f"Lỗi khi kết nối đến Binance API: {str(e)}")
            raise
    
    def _get_account_info(self):
        """
        Lấy thông tin tài khoản
        
        Returns:
            Dict: Thông tin tài khoản
        """
        try:
            if hasattr(self.api, 'get_account_information'):
                return self.api.get_account_information()
            elif hasattr(self.api, 'account'):
                return self.api.account()
            else:
                logger.warning("Không thể lấy thông tin tài khoản, phương thức không được hỗ trợ")
                return {"availableBalance": self.initial_balance}
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin tài khoản: {str(e)}")
            return {"availableBalance": self.initial_balance}
    
    def _get_positions(self):
        """
        Lấy các vị thế đang mở
        
        Returns:
            List[Dict]: Danh sách các vị thế
        """
        try:
            if hasattr(self.api, 'get_positions'):
                return self.api.get_positions()
            elif hasattr(self.api, 'get_position_risk'):
                return self.api.get_position_risk()
            else:
                logger.warning("Không thể lấy vị thế, phương thức không được hỗ trợ")
                return []
        except Exception as e:
            logger.error(f"Lỗi khi lấy vị thế: {str(e)}")
            return []
    
    def _get_ticker(self, symbol):
        """
        Lấy giá hiện tại của một cặp tiền
        
        Args:
            symbol: Cặp tiền
            
        Returns:
            Dict: Thông tin giá
        """
        try:
            if hasattr(self.api, 'get_symbol_ticker'):
                return self.api.get_symbol_ticker(symbol)
            elif hasattr(self.api, 'ticker_price'):
                return self.api.ticker_price(symbol=symbol)
            else:
                logger.warning("Không thể lấy giá, phương thức không được hỗ trợ")
                return {"price": 0}
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá của {symbol}: {str(e)}")
            return {"price": 0}
    
    def _get_exchange_info(self):
        """
        Lấy thông tin thị trường
        
        Returns:
            Dict: Thông tin thị trường
        """
        try:
            if hasattr(self.api, 'get_exchange_info'):
                return self.api.get_exchange_info()
            elif hasattr(self.api, 'exchange_info'):
                return self.api.exchange_info()
            else:
                logger.warning("Không thể lấy thông tin thị trường, phương thức không được hỗ trợ")
                return {"symbols": []}
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin thị trường: {str(e)}")
            return {"symbols": []}
    
    def _open_position(self, symbol, direction, quantity, leverage=20, stop_loss=None, take_profit=None):
        """
        Mở vị thế
        
        Args:
            symbol: Cặp tiền
            direction: Hướng giao dịch (LONG hoặc SHORT)
            quantity: Số lượng
            leverage: Đòn bẩy
            stop_loss: Giá stop loss
            take_profit: Giá take profit
            
        Returns:
            Dict: Thông tin lệnh
        """
        try:
            # Đặt đòn bẩy
            if hasattr(self.api, 'change_leverage'):
                self.api.change_leverage(symbol=symbol, leverage=leverage)
            elif hasattr(self.api, 'change_initial_leverage'):
                self.api.change_initial_leverage(symbol=symbol, leverage=leverage)
            
            # Đặt lệnh
            side = "BUY" if direction == "LONG" else "SELL"
            
            if hasattr(self.api, 'new_order'):
                order = self.api.new_order(
                    symbol=symbol,
                    side=side,
                    ordertype="MARKET",
                    quantity=quantity
                )
            elif hasattr(self.api, 'new_market_order'):
                order = self.api.new_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity
                )
            else:
                logger.warning("Không thể đặt lệnh, phương thức không được hỗ trợ")
                return {"orderId": "simulated", "status": "FILLED", "price": 0}
            
            # Đặt stop loss và take profit nếu có
            if stop_loss and hasattr(self.api, 'new_order'):
                stop_side = "SELL" if direction == "LONG" else "BUY"
                self.api.new_order(
                    symbol=symbol,
                    side=stop_side,
                    ordertype="STOP_MARKET",
                    stopPrice=stop_loss,
                    closePosition=True
                )
            
            if take_profit and hasattr(self.api, 'new_order'):
                tp_side = "SELL" if direction == "LONG" else "BUY"
                self.api.new_order(
                    symbol=symbol,
                    side=tp_side,
                    ordertype="TAKE_PROFIT_MARKET",
                    stopPrice=take_profit,
                    closePosition=True
                )
            
            return order
            
        except Exception as e:
            logger.error(f"Lỗi khi mở vị thế {direction} cho {symbol}: {str(e)}")
            raise
    
    def _close_position(self, symbol):
        """
        Đóng vị thế
        
        Args:
            symbol: Cặp tiền
            
        Returns:
            Dict: Thông tin lệnh
        """
        try:
            # Lấy thông tin vị thế
            positions = self._get_positions()
            position = next((p for p in positions if p['symbol'] == symbol and float(p['positionAmt']) != 0), None)
            
            if not position:
                logger.warning(f"Không tìm thấy vị thế nào cho {symbol}")
                return None
            
            # Xác định hướng đóng vị thế
            position_amt = float(position['positionAmt'])
            side = "SELL" if position_amt > 0 else "BUY"
            quantity = abs(position_amt)
            
            # Đặt lệnh đóng vị thế
            if hasattr(self.api, 'new_order'):
                order = self.api.new_order(
                    symbol=symbol,
                    side=side,
                    ordertype="MARKET",
                    quantity=quantity,
                    reduceOnly=True
                )
            elif hasattr(self.api, 'new_market_order'):
                order = self.api.new_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    reduceOnly=True
                )
            else:
                logger.warning("Không thể đóng vị thế, phương thức không được hỗ trợ")
                return {"orderId": "simulated", "status": "FILLED", "price": 0}
            
            return order
            
        except Exception as e:
            logger.error(f"Lỗi khi đóng vị thế cho {symbol}: {str(e)}")
            raise
    
    def is_optimal_trading_time(self, current_time=None):
        """
        Kiểm tra xem thời điểm hiện tại có phải là thời điểm giao dịch tối ưu không
        
        Args:
            current_time: Thời gian hiện tại (nếu không cung cấp, sử dụng thời gian hệ thống)
            
        Returns:
            Dict: Thông tin về phiên giao dịch tối ưu hoặc None nếu không phải
        """
        if current_time is None:
            current_time = datetime.datetime.now()
        
        # Lấy giờ và phút hiện tại
        current_time_str = current_time.strftime("%H:%M")
        
        for session in self.optimal_sessions:
            # Kiểm tra xem thời gian hiện tại có nằm trong phiên không
            if session["start_time"] <= current_time_str <= session["end_time"]:
                return session
        
        return None
    
    def execute_trades(self):
        """
        Thực hiện các giao dịch dựa trên thời gian tối ưu
        """
        logger.info("Kiểm tra điều kiện giao dịch...")
        
        # Kiểm tra xem thời điểm hiện tại có phải là thời điểm giao dịch tối ưu không
        optimal_session = self.is_optimal_trading_time()
        
        if not optimal_session:
            logger.info("Không phải thời điểm giao dịch tối ưu, bỏ qua")
            return
        
        logger.info(f"Đang trong phiên giao dịch tối ưu: {optimal_session['name']} ({optimal_session['direction']})")
        
        # Lấy số dư tài khoản
        account_info = self._get_account_info()
        available_balance = float(account_info.get('availableBalance', self.current_balance))
        
        # Cập nhật số dư
        self.current_balance = available_balance
        
        # Xác định số tiền cho mỗi giao dịch (3% vốn)
        trade_amount = self.current_balance * 0.03
        
        # Hướng giao dịch từ phiên
        direction = optimal_session["direction"]
        
        # Kiểm tra các coin phù hợp với phiên
        for symbol in self.coins:
            try:
                # Kiểm tra xem đã có vị thế nào cho coin này chưa
                positions = self._get_positions()
                has_position = any(p['symbol'] == symbol and float(p['positionAmt']) != 0 for p in positions)
                
                if has_position:
                    logger.info(f"Đã có vị thế cho {symbol}, bỏ qua")
                    continue
                
                # Nếu hướng là BOTH, chọn LONG (đơn giản hóa)
                if direction == "BOTH":
                    trade_direction = "LONG"
                else:
                    trade_direction = direction
                
                # Lấy giá hiện tại
                ticker = self._get_ticker(symbol)
                current_price = float(ticker["price"])
                
                if current_price == 0:
                    logger.warning(f"Không thể lấy giá cho {symbol}, bỏ qua")
                    continue
                
                # Tính toán khối lượng giao dịch
                leverage = 20  # Đòn bẩy 20x
                quantity = trade_amount * leverage / current_price
                
                # Làm tròn số lượng (đơn giản hóa)
                quantity = round(quantity, 3)
                
                # Tính toán SL/TP dựa trên phiên giao dịch
                sl_percent = 1.5  # Mặc định 1.5%
                tp_percent = 4.5  # Mặc định 4.5%
                
                # Điều chỉnh SL/TP dựa trên phiên và hướng
                if optimal_session["name"] == "London Open" and trade_direction == "SHORT":
                    sl_percent = 1.2
                    tp_percent = 3.6
                elif optimal_session["name"] == "New York Open" and trade_direction == "SHORT":
                    sl_percent = 1.3
                    tp_percent = 3.9
                elif optimal_session["name"] == "Daily Candle Close" and trade_direction == "LONG":
                    sl_percent = 1.4
                    tp_percent = 4.2
                
                # Tính giá SL/TP
                if trade_direction == "LONG":
                    sl_price = current_price * (1 - sl_percent/100)
                    tp_price = current_price * (1 + tp_percent/100)
                else:  # SHORT
                    sl_price = current_price * (1 + sl_percent/100)
                    tp_price = current_price * (1 - tp_percent/100)
                
                # Mở vị thế
                logger.info(f"Mở vị thế {trade_direction} cho {symbol} tại giá {current_price}, SL: {sl_price}, TP: {tp_price}, Số lượng: {quantity}")
                
                try:
                    order = self._open_position(
                        symbol=symbol,
                        direction=trade_direction,
                        quantity=quantity,
                        leverage=leverage,
                        stop_loss=sl_price,
                        take_profit=tp_price
                    )
                    
                    # Ghi lại thông tin giao dịch
                    trade_info = {
                        "symbol": symbol,
                        "direction": trade_direction,
                        "entry_price": current_price,
                        "quantity": quantity,
                        "leverage": leverage,
                        "sl_price": sl_price,
                        "tp_price": tp_price,
                        "entry_time": datetime.datetime.now().isoformat(),
                        "session": optimal_session["name"],
                        "order_id": order.get("orderId", "unknown")
                    }
                    
                    self.trades.append(trade_info)
                    
                    # Cập nhật thống kê
                    self.stats["total_trades"] += 1
                    self.stats["by_symbol"][symbol]["total_trades"] += 1
                    self.stats["by_session"][optimal_session["name"]]["total_trades"] += 1
                    
                    logger.info(f"Đã mở vị thế thành công: {json.dumps(trade_info)}")
                    
                    # Chỉ mở 3 vị thế tối đa mỗi lần
                    if self.stats["total_trades"] >= 3:
                        logger.info("Đã đạt số lượng vị thế tối đa (3), dừng mở thêm vị thế")
                        break
                    
                except Exception as e:
                    logger.error(f"Lỗi khi mở vị thế cho {symbol}: {str(e)}")
            
            except Exception as e:
                logger.error(f"Lỗi khi xử lý coin {symbol}: {str(e)}")
    
    def check_positions(self):
        """
        Kiểm tra các vị thế đang mở
        """
        logger.info("Kiểm tra các vị thế đang mở...")
        
        try:
            # Lấy tất cả vị thế đang mở
            positions = self._get_positions()
            closed_trades = []
            
            # Kiểm tra từng vị thế
            for pos in positions:
                symbol = pos.get("symbol")
                position_amt = float(pos.get("positionAmt", 0))
                
                # Bỏ qua các vị thế không có
                if position_amt == 0:
                    continue
                
                entry_price = float(pos.get("entryPrice", 0))
                mark_price = float(pos.get("markPrice", 0))
                unrealized_profit = float(pos.get("unRealizedProfit", 0))
                
                # Tìm thông tin giao dịch tương ứng
                trade_info = next((t for t in self.trades if t["symbol"] == symbol and "exit_time" not in t), None)
                
                if trade_info:
                    direction = trade_info["direction"]
                    sl_price = trade_info["sl_price"]
                    tp_price = trade_info["tp_price"]
                    
                    # Tính lợi nhuận hiện tại
                    pnl_percent = 0
                    if direction == "LONG":
                        pnl_percent = (mark_price - entry_price) / entry_price * 100
                    else:  # SHORT
                        pnl_percent = (entry_price - mark_price) / entry_price * 100
                    
                    logger.info(f"Vị thế {symbol} {direction}: Entry: {entry_price}, Mark: {mark_price}, PnL: {unrealized_profit} ({pnl_percent:.2f}%)")
                    
                    # Kiểm tra xem vị thế đã đạt TP hoặc SL chưa
                    is_tp_hit = (direction == "LONG" and mark_price >= tp_price) or (direction == "SHORT" and mark_price <= tp_price)
                    is_sl_hit = (direction == "LONG" and mark_price <= sl_price) or (direction == "SHORT" and mark_price >= sl_price)
                    
                    # Mô phỏng TP/SL do không có dữ liệu thực tế
                    if is_tp_hit or is_sl_hit:
                        status = "TP_HIT" if is_tp_hit else "SL_HIT"
                        logger.info(f"Vị thế {symbol} đã đạt {status} tại giá {mark_price}")
                        
                        # Đóng vị thế
                        self._close_position(symbol)
                        
                        # Cập nhật thông tin giao dịch
                        trade_info["exit_price"] = mark_price
                        trade_info["exit_time"] = datetime.datetime.now().isoformat()
                        trade_info["pnl"] = unrealized_profit
                        trade_info["pnl_percent"] = pnl_percent
                        trade_info["status"] = status
                        trade_info["is_win"] = is_tp_hit
                        
                        # Cập nhật thống kê
                        if is_tp_hit:
                            self.stats["win_trades"] += 1
                            self.stats["by_symbol"][symbol]["win_trades"] += 1
                            self.stats["by_session"][trade_info["session"]]["win_trades"] += 1
                        else:
                            self.stats["loss_trades"] += 1
                            self.stats["by_symbol"][symbol]["loss_trades"] += 1
                            self.stats["by_session"][trade_info["session"]]["loss_trades"] += 1
                        
                        closed_trades.append(trade_info)
            
            # Cập nhật số dư
            account_info = self._get_account_info()
            self.current_balance = float(account_info.get('totalWalletBalance', self.current_balance))
            
            # Cập nhật thống kê lợi nhuận
            self.stats["profit_loss"] = self.current_balance - self.initial_balance
            self.stats["profit_loss_percent"] = (self.current_balance - self.initial_balance) / self.initial_balance * 100
            
            # Cập nhật win rate
            if self.stats["total_trades"] > 0:
                self.stats["win_rate"] = self.stats["win_trades"] / self.stats["total_trades"] * 100
            
            # Cập nhật thống kê theo coin
            for symbol in self.coins:
                stats = self.stats["by_symbol"][symbol]
                if stats["total_trades"] > 0:
                    stats["win_rate"] = stats["win_trades"] / stats["total_trades"] * 100
                    stats["profit_loss_percent"] = stats["win_rate"] / 100 * 100  # Ước tính đơn giản
            
            # Cập nhật thống kê theo phiên
            for session in self.optimal_sessions:
                session_name = session["name"]
                stats = self.stats["by_session"][session_name]
                if stats["total_trades"] > 0:
                    stats["win_rate"] = stats["win_trades"] / stats["total_trades"] * 100
                    stats["profit_loss_percent"] = stats["win_rate"] / 100 * 100  # Ước tính đơn giản
            
            return closed_trades
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra vị thế: {str(e)}")
            return []
    
    def generate_report(self):
        """
        Tạo báo cáo kết quả
        
        Returns:
            str: Báo cáo dạng text
        """
        report = "===== BÁO CÁO KIỂM THỬ LIVE MULTI-COIN =====\n\n"
        
        # Thông tin cơ bản
        report += f"Thời gian hiện tại: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Số dư ban đầu: {self.initial_balance:.2f} USDT\n"
        report += f"Số dư hiện tại: {self.current_balance:.2f} USDT\n"
        report += f"Lợi nhuận: {self.stats['profit_loss']:.2f} USDT ({self.stats['profit_loss_percent']:.2f}%)\n"
        report += f"Số giao dịch: {self.stats['total_trades']}\n"
        report += f"Thắng/Thua: {self.stats['win_trades']}/{self.stats['loss_trades']}\n"
        report += f"Tỷ lệ thắng: {self.stats['win_rate']:.2f}%\n\n"
        
        # Thống kê theo coin
        report += "THỐNG KÊ THEO COIN:\n"
        report += "-----------------\n"
        
        for symbol, stats in self.stats["by_symbol"].items():
            if stats["total_trades"] > 0:
                report += f"{symbol}: "
                report += f"Số GD: {stats['total_trades']}, "
                report += f"Thắng: {stats['win_trades']}, "
                report += f"Thua: {stats['loss_trades']}, "
                report += f"Win Rate: {stats['win_rate']:.2f}%\n"
        
        report += "\n"
        
        # Thống kê theo phiên
        report += "THỐNG KÊ THEO PHIÊN:\n"
        report += "-------------------\n"
        
        for session_name, stats in self.stats["by_session"].items():
            if stats["total_trades"] > 0:
                report += f"{session_name}: "
                report += f"Số GD: {stats['total_trades']}, "
                report += f"Thắng: {stats['win_trades']}, "
                report += f"Thua: {stats['loss_trades']}, "
                report += f"Win Rate: {stats['win_rate']:.2f}%\n"
        
        report += "\n"
        
        # Danh sách giao dịch
        report += "DANH SÁCH GIAO DỊCH:\n"
        report += "------------------\n"
        
        for i, trade in enumerate(self.trades):
            report += f"GD #{i+1}: {trade['symbol']} {trade['direction']} "
            
            if "exit_time" in trade:
                report += f"Entry: {trade['entry_price']:.2f}, Exit: {trade['exit_price']:.2f}, "
                report += f"PnL: {trade['pnl']:.2f} USDT ({trade.get('pnl_percent', 0):.2f}%), Status: {trade['status']}\n"
            else:
                report += f"Entry: {trade['entry_price']:.2f}, Status: OPEN\n"
        
        report += "\n"
        
        # Các phiên giao dịch tối ưu
        report += "PHIÊN GIAO DỊCH TỐI ƯU:\n"
        report += "---------------------\n"
        
        for session in self.optimal_sessions:
            report += f"{session['name']}: "
            report += f"{session['start_time']} - {session['end_time']}, "
            report += f"Hướng: {session['direction']}, "
            report += f"Win Rate (Backtest): {session['win_rate']:.2f}%\n"
        
        report += "\n"
        
        return report
    
    def run(self, run_time_minutes=60):
        """
        Chạy thử nghiệm
        
        Args:
            run_time_minutes: Số phút chạy thử nghiệm
        """
        try:
            logger.info(f"Bắt đầu chạy thử nghiệm trong {run_time_minutes} phút...")
            
            end_time = datetime.datetime.now() + datetime.timedelta(minutes=run_time_minutes)
            
            while datetime.datetime.now() < end_time:
                # Thực hiện giao dịch
                self.execute_trades()
                
                # Kiểm tra vị thế
                closed_trades = self.check_positions()
                
                # In thông tin vị thế đã đóng
                for trade in closed_trades:
                    logger.info(f"Vị thế đã đóng: {trade['symbol']} {trade['direction']}, "
                              f"Entry: {trade['entry_price']:.2f}, Exit: {trade['exit_price']:.2f}, "
                              f"PnL: {trade['pnl']:.2f}, Status: {trade['status']}")
                
                # Tạo báo cáo tạm thời
                report = self.generate_report()
                logger.info("\n" + report)
                
                # Lưu báo cáo
                with open(f"simple_live_test_report.txt", "w", encoding="utf-8") as f:
                    f.write(report)
                
                # Đợi một thời gian trước khi kiểm tra lại
                logger.info(f"Đợi 60 giây trước khi kiểm tra lại...")
                time.sleep(60)
            
            # Tạo báo cáo cuối cùng
            final_report = self.generate_report()
            
            with open(f"simple_live_test_final_report.txt", "w", encoding="utf-8") as f:
                f.write(final_report)
            
            logger.info("Đã hoàn thành thử nghiệm!")
            logger.info("\n" + final_report)
            
            return final_report
        
        except KeyboardInterrupt:
            logger.info("Đã dừng thử nghiệm bởi người dùng!")
            
            # Tạo báo cáo khi dừng
            report = self.generate_report()
            
            with open(f"simple_live_test_interrupt_report.txt", "w", encoding="utf-8") as f:
                f.write(report)
            
            logger.info("\n" + report)
            
            return report
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy thử nghiệm: {str(e)}")
            
            # Tạo báo cáo khi lỗi
            report = self.generate_report()
            
            with open(f"simple_live_test_error_report.txt", "w", encoding="utf-8") as f:
                f.write(report)
            
            return report

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Chạy thử nghiệm đơn giản với nhiều coin")
    parser.add_argument("--balance", type=float, default=10000, help="Số dư ban đầu (USDT)")
    parser.add_argument("--minutes", type=int, default=60, help="Số phút chạy thử nghiệm")
    args = parser.parse_args()
    
    test = SimpleLiveTest(initial_balance=args.balance)
    test.run(run_time_minutes=args.minutes)