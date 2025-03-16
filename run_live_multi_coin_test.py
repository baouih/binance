#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy thử nghiệm thực tế với nhiều coin thanh khoản cao
Sử dụng chiến lược Single Direction tối ưu dựa trên khung thời gian
"""

import os
import json
import time
import logging
import argparse
import datetime
from typing import Dict, List, Any

# Import các module cần thiết
from binance_api import BinanceAPI
from signal_processor import SignalProcessor
from adaptive_risk_manager import AdaptiveRiskManager
from position_manager import PositionManager
from market_analyzer import MarketAnalyzer
from improved_win_rate import ImprovedWinRateAdapter
from optimal_entry_timing import OptimalEntryTiming
from data_validator import DataValidator

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("live_test_multi_coin.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('LiveTest')

class LiveMultiCoinTest:
    """
    Lớp thực hiện thử nghiệm thực tế với nhiều coin
    """
    
    def __init__(self, initial_balance=10000, test_days=30):
        """
        Khởi tạo môi trường thử nghiệm
        
        Args:
            initial_balance: Số dư ban đầu (USDT)
            test_days: Số ngày thử nghiệm
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.test_days = test_days
        self.test_start_time = datetime.datetime.now()
        self.test_end_time = self.test_start_time + datetime.timedelta(days=test_days)
        
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
        
        # Thiết lập các module cần thiết
        self._setup_modules()
        
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
        
        # Số dư tối đa và tối thiểu
        self.max_balance = initial_balance
        self.min_balance = initial_balance
        
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
        
        logger.info(f"Đã khởi tạo LiveMultiCoinTest với số dư ban đầu {initial_balance} USDT, thời gian thử nghiệm {test_days} ngày")
    
    def _setup_modules(self):
        """
        Thiết lập các module cần thiết
        """
        try:
            # Kết nối đến Binance API
            self.api = BinanceAPI(is_testnet=True)
            logger.info("Đã kết nối thành công đến Binance Testnet API")
            
            # Khởi tạo các module
            self.risk_manager = AdaptiveRiskManager()
            self.position_manager = PositionManager(self.api)
            self.market_analyzer = MarketAnalyzer()
            self.signal_processor = SignalProcessor()
            self.win_rate_adapter = ImprovedWinRateAdapter()
            self.entry_timing = OptimalEntryTiming()
            self.data_validator = DataValidator()
            
            # Kiểm tra số dư hiện tại
            account_info = self.api.get_account_information()
            available_balance = float(account_info.get('availableBalance', 0))
            logger.info(f"Số dư khả dụng trên tài khoản Testnet: {available_balance} USDT")
            
            # Kiểm tra vị thế hiện tại
            positions = self.api.get_positions()
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            logger.info(f"Số vị thế đang mở: {len(open_positions)}")
            
            # In thông tin vị thế đang mở
            for pos in open_positions:
                symbol = pos['symbol']
                size = float(pos['positionAmt'])
                entry_price = float(pos['entryPrice'])
                mark_price = float(pos['markPrice'])
                pnl = float(pos['unRealizedProfit'])
                logger.info(f"Vị thế đang mở: {symbol}, Size: {size}, Entry: {entry_price}, Mark: {mark_price}, PnL: {pnl}")
        
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập các module: {str(e)}")
            raise
    
    def is_optimal_trading_time(self, symbol, current_time=None):
        """
        Kiểm tra xem thời điểm hiện tại có phải là thời điểm giao dịch tối ưu không
        
        Args:
            symbol: Cặp tiền cần kiểm tra
            current_time: Thời gian hiện tại (nếu không cung cấp, sử dụng thời gian hệ thống)
            
        Returns:
            dict: Thông tin về phiên giao dịch tối ưu hoặc None nếu không phải
        """
        if current_time is None:
            current_time = datetime.datetime.now()
        
        # Lấy giờ và phút hiện tại
        current_time_str = current_time.strftime("%H:%M")
        
        for session in self.optimal_sessions:
            # Kiểm tra xem thời gian hiện tại có nằm trong phiên không
            if session["start_time"] <= current_time_str <= session["end_time"]:
                # Kiểm tra xem symbol có phù hợp với phiên không
                # Trong trường hợp này, chúng ta giả định tất cả các coin đều phù hợp
                return {
                    "session": session["name"],
                    "direction": session["direction"],
                    "win_rate": session["win_rate"]
                }
        
        return None
    
    def execute_trades(self):
        """
        Thực hiện các giao dịch dựa trên thời gian tối ưu
        """
        logger.info("Bắt đầu thực hiện giao dịch thử nghiệm...")
        
        # Xác định số tiền cho mỗi giao dịch (3% vốn)
        trade_amount = self.current_balance * 0.03
        
        # Lấy thời gian hiện tại
        current_time = datetime.datetime.now()
        
        # Kiểm tra từng coin
        for symbol in self.coins:
            try:
                # Kiểm tra xem thời điểm hiện tại có phải là thời điểm giao dịch tối ưu không
                optimal_time = self.is_optimal_trading_time(symbol, current_time)
                
                if optimal_time:
                    logger.info(f"Thời điểm giao dịch tối ưu cho {symbol}: {optimal_time['session']} ({optimal_time['direction']})")
                    
                    # Kiểm tra xem đã có vị thế nào cho coin này chưa
                    current_positions = self.position_manager.get_positions_for_symbol(symbol)
                    
                    if current_positions:
                        logger.info(f"Đã có vị thế cho {symbol}, bỏ qua")
                        continue
                    
                    # Xác định hướng giao dịch
                    direction = optimal_time["direction"]
                    
                    # Nếu hướng là BOTH, chọn ngẫu nhiên hoặc dựa vào phân tích thị trường
                    if direction == "BOTH":
                        # Phân tích thị trường để xác định hướng
                        market_analysis = self.market_analyzer.analyze_market(symbol)
                        trend = market_analysis.get("trend", "NEUTRAL")
                        
                        if trend == "BULLISH":
                            direction = "LONG"
                        elif trend == "BEARISH":
                            direction = "SHORT"
                        else:
                            # Nếu không có xu hướng rõ ràng, bỏ qua
                            logger.info(f"Không có xu hướng rõ ràng cho {symbol}, bỏ qua")
                            continue
                    
                    # Lấy giá hiện tại
                    ticker = self.api.get_symbol_ticker(symbol)
                    current_price = float(ticker["price"])
                    
                    # Tính toán khối lượng giao dịch
                    leverage = 20  # Đòn bẩy 20x
                    quantity = trade_amount * leverage / current_price
                    
                    # Làm tròn số lượng
                    symbol_info = self.api.get_symbol_info(symbol)
                    precision = symbol_info.get("quantityPrecision", 3)
                    quantity = round(quantity, precision)
                    
                    # Kiểm tra khối lượng tối thiểu
                    min_qty = float(symbol_info.get("filters", [{}])[1].get("minQty", 0))
                    if quantity < min_qty:
                        logger.warning(f"Khối lượng {quantity} nhỏ hơn khối lượng tối thiểu {min_qty} cho {symbol}, điều chỉnh")
                        quantity = min_qty
                    
                    # Tính toán SL/TP dựa trên phiên giao dịch
                    sl_percent = 1.5  # Mặc định 1.5%
                    tp_percent = 4.5  # Mặc định 4.5%
                    
                    # Điều chỉnh SL/TP dựa trên phiên và hướng
                    if optimal_time["session"] == "London Open" and direction == "SHORT":
                        sl_percent = 1.2
                        tp_percent = 3.6
                    elif optimal_time["session"] == "New York Open" and direction == "SHORT":
                        sl_percent = 1.3
                        tp_percent = 3.9
                    elif optimal_time["session"] == "Daily Candle Close" and direction == "LONG":
                        sl_percent = 1.4
                        tp_percent = 4.2
                    
                    # Tính giá SL/TP
                    if direction == "LONG":
                        sl_price = current_price * (1 - sl_percent/100)
                        tp_price = current_price * (1 + tp_percent/100)
                    else:  # SHORT
                        sl_price = current_price * (1 + sl_percent/100)
                        tp_price = current_price * (1 - tp_percent/100)
                    
                    # Mở vị thế
                    logger.info(f"Mở vị thế {direction} cho {symbol} tại giá {current_price}, SL: {sl_price}, TP: {tp_price}, Số lượng: {quantity}")
                    
                    try:
                        order = self.position_manager.open_position(
                            symbol=symbol,
                            direction="LONG" if direction == "LONG" else "SHORT",
                            quantity=quantity,
                            leverage=leverage,
                            stop_loss=sl_price,
                            take_profit=tp_price
                        )
                        
                        # Ghi lại thông tin giao dịch
                        trade_info = {
                            "symbol": symbol,
                            "direction": direction,
                            "entry_price": current_price,
                            "quantity": quantity,
                            "leverage": leverage,
                            "sl_price": sl_price,
                            "tp_price": tp_price,
                            "entry_time": current_time.isoformat(),
                            "session": optimal_time["session"],
                            "order_id": order.get("orderId", "unknown")
                        }
                        
                        self.trades.append(trade_info)
                        
                        # Cập nhật thống kê
                        self.stats["total_trades"] += 1
                        self.stats["by_symbol"][symbol]["total_trades"] += 1
                        self.stats["by_session"][optimal_time["session"]]["total_trades"] += 1
                        
                        logger.info(f"Đã mở vị thế thành công: {json.dumps(trade_info)}")
                        
                    except Exception as e:
                        logger.error(f"Lỗi khi mở vị thế cho {symbol}: {str(e)}")
                
                else:
                    logger.debug(f"Không phải thời điểm giao dịch tối ưu cho {symbol}")
            
            except Exception as e:
                logger.error(f"Lỗi khi xử lý coin {symbol}: {str(e)}")
    
    def check_positions(self):
        """
        Kiểm tra các vị thế đang mở
        """
        logger.info("Kiểm tra các vị thế đang mở...")
        
        try:
            # Lấy tất cả vị thế đang mở
            positions = self.position_manager.get_all_positions()
            closed_positions = []
            
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
                    logger.info(f"Vị thế {symbol}: Entry: {entry_price}, Mark: {mark_price}, PnL: {unrealized_profit}")
                    
                    # Kiểm tra xem vị thế đã đạt TP hoặc SL chưa
                    direction = trade_info["direction"]
                    sl_price = trade_info["sl_price"]
                    tp_price = trade_info["tp_price"]
                    
                    is_tp_hit = (direction == "LONG" and mark_price >= tp_price) or (direction == "SHORT" and mark_price <= tp_price)
                    is_sl_hit = (direction == "LONG" and mark_price <= sl_price) or (direction == "SHORT" and mark_price >= sl_price)
                    
                    if is_tp_hit:
                        logger.info(f"Vị thế {symbol} đã đạt TP tại giá {mark_price}")
                        
                        # Đóng vị thế
                        self.position_manager.close_position(symbol)
                        
                        # Cập nhật thông tin giao dịch
                        trade_info["exit_price"] = mark_price
                        trade_info["exit_time"] = datetime.datetime.now().isoformat()
                        trade_info["pnl"] = unrealized_profit
                        trade_info["status"] = "TP_HIT"
                        trade_info["is_win"] = True
                        
                        # Cập nhật thống kê
                        self.stats["win_trades"] += 1
                        self.stats["by_symbol"][symbol]["win_trades"] += 1
                        self.stats["by_session"][trade_info["session"]]["win_trades"] += 1
                        
                        closed_positions.append(trade_info)
                    
                    elif is_sl_hit:
                        logger.info(f"Vị thế {symbol} đã đạt SL tại giá {mark_price}")
                        
                        # Đóng vị thế
                        self.position_manager.close_position(symbol)
                        
                        # Cập nhật thông tin giao dịch
                        trade_info["exit_price"] = mark_price
                        trade_info["exit_time"] = datetime.datetime.now().isoformat()
                        trade_info["pnl"] = unrealized_profit
                        trade_info["status"] = "SL_HIT"
                        trade_info["is_win"] = False
                        
                        # Cập nhật thống kê
                        self.stats["loss_trades"] += 1
                        self.stats["by_symbol"][symbol]["loss_trades"] += 1
                        self.stats["by_session"][trade_info["session"]]["loss_trades"] += 1
                        
                        closed_positions.append(trade_info)
            
            # Cập nhật số dư
            account_info = self.api.get_account_information()
            self.current_balance = float(account_info.get('totalWalletBalance', self.current_balance))
            
            # Cập nhật drawdown
            if self.current_balance > self.max_balance:
                self.max_balance = self.current_balance
            
            if self.current_balance < self.min_balance:
                self.min_balance = self.current_balance
            
            drawdown = (self.max_balance - self.min_balance) / self.max_balance * 100
            
            if drawdown > self.stats["max_drawdown"]:
                self.stats["max_drawdown"] = drawdown
            
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
            
            # Cập nhật thống kê theo phiên
            for session in self.optimal_sessions:
                session_name = session["name"]
                stats = self.stats["by_session"][session_name]
                if stats["total_trades"] > 0:
                    stats["win_rate"] = stats["win_trades"] / stats["total_trades"] * 100
            
            return closed_positions
        
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
        report += f"Thời gian bắt đầu: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Thời gian kết thúc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Số dư ban đầu: {self.initial_balance:.2f} USDT\n"
        report += f"Số dư hiện tại: {self.current_balance:.2f} USDT\n"
        report += f"Lợi nhuận: {self.stats['profit_loss']:.2f} USDT ({self.stats['profit_loss_percent']:.2f}%)\n"
        report += f"Số giao dịch: {self.stats['total_trades']}\n"
        report += f"Thắng/Thua: {self.stats['win_trades']}/{self.stats['loss_trades']}\n"
        report += f"Tỷ lệ thắng: {self.stats['win_rate']:.2f}%\n"
        report += f"Drawdown tối đa: {self.stats['max_drawdown']:.2f}%\n\n"
        
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
                report += f"PnL: {trade['pnl']:.2f}, Status: {trade['status']}\n"
            else:
                report += f"Entry: {trade['entry_price']:.2f}, Status: OPEN\n"
        
        report += "\n"
        
        # Kết luận
        report += "KẾT LUẬN:\n"
        report += "--------\n"
        
        if self.stats["profit_loss"] > 0:
            report += f"Chiến lược sinh lời với lợi nhuận {self.stats['profit_loss_percent']:.2f}%\n"
        else:
            report += f"Chiến lược thua lỗ với tổn thất {abs(self.stats['profit_loss_percent']):.2f}%\n"
        
        # Tìm phiên hiệu quả nhất
        best_session = None
        best_win_rate = 0
        
        for session_name, stats in self.stats["by_session"].items():
            if stats["total_trades"] > 0 and stats["win_rate"] > best_win_rate:
                best_win_rate = stats["win_rate"]
                best_session = session_name
        
        if best_session:
            report += f"Phiên giao dịch hiệu quả nhất: {best_session} với tỷ lệ thắng {best_win_rate:.2f}%\n"
        
        # Tìm coin hiệu quả nhất
        best_coin = None
        best_win_rate = 0
        
        for symbol, stats in self.stats["by_symbol"].items():
            if stats["total_trades"] > 0 and stats["win_rate"] > best_win_rate:
                best_win_rate = stats["win_rate"]
                best_coin = symbol
        
        if best_coin:
            report += f"Coin hiệu quả nhất: {best_coin} với tỷ lệ thắng {best_win_rate:.2f}%\n"
        
        return report
    
    def save_report(self, report_text):
        """
        Lưu báo cáo vào file
        
        Args:
            report_text: Nội dung báo cáo
        """
        report_file = f"live_test_multi_coin_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        
        logger.info(f"Đã lưu báo cáo vào file {report_file}")
    
    def run(self, run_time_hours=24):
        """
        Chạy thử nghiệm
        
        Args:
            run_time_hours: Số giờ chạy thử nghiệm
        """
        try:
            logger.info(f"Bắt đầu chạy thử nghiệm trong {run_time_hours} giờ...")
            
            end_time = datetime.datetime.now() + datetime.timedelta(hours=run_time_hours)
            
            while datetime.datetime.now() < end_time:
                # Thực hiện giao dịch
                self.execute_trades()
                
                # Kiểm tra vị thế
                closed_positions = self.check_positions()
                
                # In thông tin vị thế đã đóng
                for pos in closed_positions:
                    logger.info(f"Vị thế đã đóng: {pos['symbol']} {pos['direction']}, "
                              f"Entry: {pos['entry_price']:.2f}, Exit: {pos['exit_price']:.2f}, "
                              f"PnL: {pos['pnl']:.2f}, Status: {pos['status']}")
                
                # Tạo và lưu báo cáo tạm thời
                if self.stats["total_trades"] > 0:
                    report = self.generate_report()
                    self.save_report(report)
                    logger.info("\n" + report)
                
                # Đợi một thời gian trước khi kiểm tra lại
                logger.info(f"Đợi 60 giây trước khi kiểm tra lại...")
                time.sleep(60)
            
            # Tạo báo cáo cuối cùng
            final_report = self.generate_report()
            self.save_report(final_report)
            
            logger.info("Đã hoàn thành thử nghiệm!")
            logger.info("\n" + final_report)
            
            return final_report
        
        except KeyboardInterrupt:
            logger.info("Đã dừng thử nghiệm bởi người dùng!")
            
            # Tạo báo cáo khi dừng
            report = self.generate_report()
            self.save_report(report)
            
            logger.info("\n" + report)
            
            return report
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy thử nghiệm: {str(e)}")
            
            # Tạo báo cáo khi lỗi
            report = self.generate_report()
            self.save_report(report)
            
            return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy thử nghiệm thực tế với nhiều coin")
    parser.add_argument("--balance", type=float, default=10000, help="Số dư ban đầu (USDT)")
    parser.add_argument("--days", type=int, default=30, help="Số ngày thử nghiệm")
    parser.add_argument("--hours", type=int, default=24, help="Số giờ chạy thử nghiệm")
    args = parser.parse_args()
    
    test = LiveMultiCoinTest(initial_balance=args.balance, test_days=args.days)
    test.run(run_time_hours=args.hours)