#!/usr/bin/env python3
"""
Script triển khai Trailing Stop Thông Minh cho các vị thế đang mở

Script này tích hợp chức năng trailing stop nâng cao để bảo vệ lợi nhuận,
tự động điều chỉnh dựa trên biến động thị trường và điều kiện của từng cặp tiền,
có thể chạy như service độc lập để theo dõi vị thế.
"""

import os
import sys
import json
import time
import logging
import argparse
import datetime
import pandas as pd
from typing import Dict, List, Tuple
from binance_api import BinanceAPI
from leverage_risk_manager import LeverageRiskManager

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("position_trailing_stop")

# Đường dẫn cấu hình
CONFIG_PATH = 'account_config.json'
POSITIONS_FILE = 'active_positions.json'

class PositionTrailingStop:
    """Lớp quản lý trailing stop các vị thế đang mở"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, 
               config_path: str = CONFIG_PATH, 
               positions_file: str = POSITIONS_FILE):
        """
        Khởi tạo quản lý trailing stop
        
        Args:
            api_key (str, optional): API Key Binance
            api_secret (str, optional): API Secret Binance
            config_path (str): Đường dẫn đến file cấu hình
            positions_file (str): Đường dẫn file lưu vị thế active
        """
        self.config_path = config_path
        self.positions_file = positions_file
        
        # Khởi tạo Binance API
        self.api = BinanceAPI(api_key, api_secret)
        
        # Khởi tạo Quản lý rủi ro
        self.risk_manager = LeverageRiskManager(self.api)
        
        # Dữ liệu vị thế
        self.active_positions = {}
        self.load_active_positions()
        
        # Cập nhật vị thế hiện tại từ Binance
        self.update_positions_from_exchange()
    
    def load_active_positions(self) -> Dict:
        """
        Tải danh sách vị thế đang theo dõi từ file
        
        Returns:
            Dict: Danh sách vị thế đang theo dõi
        """
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r') as f:
                    self.active_positions = json.load(f)
                logger.info(f"Đã tải {len(self.active_positions)} vị thế từ {self.positions_file}")
            else:
                logger.info(f"Không tìm thấy file {self.positions_file}, tạo mới")
                self.active_positions = {}
                self.save_active_positions()
            
            return self.active_positions
        except Exception as e:
            logger.error(f"Lỗi khi tải danh sách vị thế: {str(e)}")
            self.active_positions = {}
            return self.active_positions
    
    def save_active_positions(self) -> bool:
        """
        Lưu danh sách vị thế đang theo dõi vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.active_positions, f, indent=4)
            logger.info(f"Đã lưu {len(self.active_positions)} vị thế vào {self.positions_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu danh sách vị thế: {str(e)}")
            return False
    
    def update_positions_from_exchange(self) -> Dict:
        """
        Cập nhật danh sách vị thế từ sàn giao dịch
        
        Returns:
            Dict: Danh sách vị thế đã cập nhật
        """
        try:
            # Lấy danh sách vị thế từ Binance
            positions = self.api.get_futures_position_risk()
            
            # Lọc ra các vị thế đang mở (positionAmt != 0)
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            
            for pos in open_positions:
                symbol = pos['symbol']
                side = "LONG" if float(pos['positionAmt']) > 0 else "SHORT"
                entry_price = float(pos['entryPrice'])
                quantity = abs(float(pos['positionAmt']))
                leverage = int(float(pos['leverage']))
                
                # Kiểm tra xem vị thế đã tồn tại trong danh sách chưa
                if symbol not in self.active_positions:
                    # Nếu chưa tồn tại, thêm mới
                    logger.info(f"Phát hiện vị thế mới từ sàn: {symbol} {side}")
                    
                    # Tính giá stop loss và take profit tự động dựa trên biến động thị trường
                    # Trong trường hợp này, giả định một giá trị mặc định
                    # Thực tế cần tính toán dựa trên dữ liệu giá và biến động
                    stop_loss = None
                    take_profit = None
                    
                    # Load dữ liệu giá để tính volatility (đơn giản hóa ví dụ này)
                    try:
                        # Lấy dữ liệu biến động của cặp tiền
                        klines = self.api.get_klines(symbol=symbol, interval='1h', limit=50)
                        if klines:
                            df = self.api.convert_klines_to_dataframe(klines)
                            # Cập nhật thông tin biến động
                            self.risk_manager.update_volatility_metrics(symbol, df)
                            
                            # Tính stop loss dựa trên thông tin biến động
                            stop_loss = self.risk_manager.calculate_dynamic_stop_loss(
                                symbol=symbol, 
                                entry_price=entry_price, 
                                side=side
                            )
                            
                            # Tính take profit dựa trên thông tin biến động và stop loss
                            take_profit = self.risk_manager.calculate_dynamic_take_profit(
                                symbol=symbol,
                                entry_price=entry_price,
                                side=side,
                                stop_loss_price=stop_loss
                            )
                    except Exception as e:
                        logger.warning(f"Không thể tính toán stop loss/take profit tự động: {str(e)}")
                        # Nếu có lỗi, sử dụng giá trị mặc định
                        if side == "LONG":
                            stop_loss = entry_price * 0.95  # -5%
                            take_profit = entry_price * 1.1  # +10%
                        else:  # SHORT
                            stop_loss = entry_price * 1.05  # +5%
                            take_profit = entry_price * 0.9  # -10%
                    
                    # Thêm vị thế vào danh sách theo dõi
                    self.active_positions[symbol] = {
                        "symbol": symbol,
                        "side": side,
                        "entry_price": entry_price,
                        "quantity": quantity,
                        "leverage": leverage,
                        "stop_loss": stop_loss if stop_loss else entry_price * 0.95 if side == "LONG" else entry_price * 1.05,
                        "take_profit": take_profit if take_profit else entry_price * 1.1 if side == "LONG" else entry_price * 0.9,
                        "trailing_activated": False,
                        "entry_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "highest_price": entry_price if side == "LONG" else None,
                        "lowest_price": entry_price if side == "SHORT" else None,
                        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Đăng ký vị thế vào risk manager cho việc theo dõi
                    sl = stop_loss if stop_loss else entry_price * 0.95 if side == "LONG" else entry_price * 1.05
                    tp = take_profit if take_profit else entry_price * 1.1 if side == "LONG" else entry_price * 0.9
                    
                    self.risk_manager.track_open_position(
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        quantity=quantity,
                        leverage=leverage,
                        stop_loss=sl,
                        take_profit=tp
                    )
                else:
                    # Nếu đã tồn tại, chỉ cập nhật thông tin quantity và leverage nếu có thay đổi
                    if (quantity != self.active_positions[symbol]["quantity"] or 
                        leverage != self.active_positions[symbol]["leverage"]):
                        logger.info(f"Cập nhật thông tin vị thế: {symbol} {side}")
                        self.active_positions[symbol]["quantity"] = quantity
                        self.active_positions[symbol]["leverage"] = leverage
                        self.active_positions[symbol]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Lưu danh sách vị thế đã cập nhật
            self.save_active_positions()
            
            return self.active_positions
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật vị thế từ sàn: {str(e)}")
            return self.active_positions
    
    def update_all_trailing_stops(self) -> List[Dict]:
        """
        Cập nhật trailing stop cho tất cả vị thế
        
        Returns:
            List[Dict]: Danh sách kết quả cập nhật
        """
        results = []
        symbols_to_remove = []
        
        try:
            # Tải thông báo Telegram (nếu chưa có, tự động tải từ file cấu hình)
            try:
                from telegram_notifier import TelegramNotifier
                telegram = TelegramNotifier()
            except Exception as e:
                logger.warning(f"Không thể tải TelegramNotifier: {str(e)}")
                telegram = None
            
            # Lấy giá hiện tại của tất cả các symbols
            all_tickers = self.api.get_price_ticker()
            price_dict = {ticker['symbol']: float(ticker['price']) for ticker in all_tickers}
            
            for symbol, position in self.active_positions.items():
                if symbol in price_dict:
                    current_price = price_dict[symbol]
                    side = position["side"]
                    entry_price = position["entry_price"]
                    leverage = position["leverage"]
                    
                    # Cập nhật trailing stop cho vị thế này
                    update_result = self.risk_manager.update_position_with_trailing_stop(symbol, current_price)
                    
                    # Tính toán lợi nhuận hiện tại
                    if side == "LONG":
                        profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
                    else:  # SHORT
                        profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
                    
                    # Nếu trailing stop mới được kích hoạt, gửi thông báo
                    if update_result.get("trailing_activated", False) and not position.get("trailing_activated", False):
                        logger.info(f"Trailing stop kích hoạt cho {symbol} {side} tại {update_result.get('trailing_stop')}")
                        
                        # Gửi thông báo Telegram nếu có
                        if telegram:
                            try:
                                notification_data = {
                                    "symbol": symbol,
                                    "side": side,
                                    "entry_price": entry_price,
                                    "current_price": current_price,
                                    "trailing_stop": update_result.get("trailing_stop"),
                                    "profit_percent": profit_percent
                                }
                                telegram.send_trailing_stop_notification(notification_data)
                                logger.info(f"Đã gửi thông báo trailing stop qua Telegram cho {symbol}")
                            except Exception as te:
                                logger.error(f"Lỗi gửi thông báo Telegram: {str(te)}")
                    
                    # Nếu vị thế đã đóng, thêm vào danh sách để xóa sau
                    if update_result.get("position_closed", False):
                        symbols_to_remove.append(symbol)
                        close_reason = update_result.get('close_reason', 'unknown')
                        logger.info(f"Vị thế {symbol} đã đóng do {close_reason}")
                        
                        # Gửi thông báo Telegram nếu có
                        if telegram:
                            try:
                                # Tính toán lợi nhuận
                                if side == "LONG":
                                    profit_loss = (current_price - entry_price) * position["quantity"] * leverage
                                else:  # SHORT
                                    profit_loss = (entry_price - current_price) * position["quantity"] * leverage
                                
                                notification_data = {
                                    "symbol": symbol,
                                    "side": side,
                                    "entry_price": entry_price,
                                    "exit_price": current_price,
                                    "profit_loss": profit_loss,
                                    "profit_percent": profit_percent,
                                    "close_reason": close_reason
                                }
                                telegram.send_position_close_notification(notification_data)
                                logger.info(f"Đã gửi thông báo đóng vị thế qua Telegram cho {symbol}")
                            except Exception as te:
                                logger.error(f"Lỗi gửi thông báo Telegram: {str(te)}")
                        
                        # TODO: Thực hiện đóng lệnh thực tế tại đây
                        # Trong ví dụ này, chúng ta chỉ giả định ghi nhận việc đóng vị thế
                        # Trong thực tế, bạn cần gọi API để đóng vị thế
                    
                    # Cập nhật thông tin vị thế
                    self.active_positions[symbol].update({
                        "current_price": current_price,
                        "trailing_activated": update_result.get("trailing_activated", False),
                        "trailing_stop": update_result.get("trailing_stop", None),
                        "profit_percent": profit_percent,
                        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Thêm kết quả vào danh sách
                    results.append(update_result)
                else:
                    logger.warning(f"Không tìm thấy giá hiện tại cho {symbol}")
            
            # Xóa các vị thế đã đóng
            for symbol in symbols_to_remove:
                del self.active_positions[symbol]
                logger.info(f"Đã xóa vị thế {symbol} khỏi danh sách theo dõi")
            
            # Lưu danh sách vị thế đã cập nhật
            self.save_active_positions()
            
            return results
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trailing stop: {str(e)}")
            return results
    
    def run_monitoring_service(self, interval: int = 60):
        """
        Chạy dịch vụ giám sát các vị thế 
        
        Args:
            interval (int): Khoảng thời gian giữa các lần cập nhật (giây)
        """
        logger.info(f"Bắt đầu dịch vụ giám sát trailing stop với chu kỳ {interval} giây")
        try:
            while True:
                # Cập nhật danh sách vị thế từ sàn
                self.update_positions_from_exchange()
                
                # Nếu có vị thế đang mở, cập nhật trailing stop
                if self.active_positions:
                    logger.info(f"Đang theo dõi {len(self.active_positions)} vị thế")
                    results = self.update_all_trailing_stops()
                    
                    # In thông tin trailing stop
                    for result in results:
                        symbol = result.get("symbol")
                        side = result.get("side")
                        current_price = result.get("current_price")
                        trailing_activated = result.get("trailing_activated", False)
                        trailing_stop = result.get("trailing_stop")
                        
                        if trailing_activated:
                            logger.info(f"{symbol} {side}: Giá hiện tại: {current_price}, Trailing Stop: {trailing_stop}")
                        else:
                            logger.info(f"{symbol} {side}: Giá hiện tại: {current_price}, Trailing Stop chưa kích hoạt")
                else:
                    logger.info("Không có vị thế nào đang mở")
                
                # Đợi một khoảng thời gian trước khi cập nhật lại
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Dịch vụ giám sát đã dừng theo yêu cầu người dùng")
        except Exception as e:
            logger.error(f"Lỗi trong dịch vụ giám sát: {str(e)}")
    
    def manual_check(self):
        """Kiểm tra thủ công và hiển thị thông tin vị thế"""
        try:
            # Cập nhật danh sách vị thế từ sàn
            self.update_positions_from_exchange()
            
            # Lấy giá hiện tại của tất cả các symbols
            all_tickers = self.api.get_price_ticker()
            price_dict = {ticker['symbol']: float(ticker['price']) for ticker in all_tickers}
            
            print("\n=== DANH SÁCH VỊ THẾ ĐANG MỞ ===")
            if not self.active_positions:
                print("Không có vị thế nào đang mở")
                return
            
            for symbol, position in self.active_positions.items():
                side = position["side"]
                entry_price = position["entry_price"]
                quantity = position["quantity"]
                leverage = position["leverage"]
                stop_loss = position.get("stop_loss", "N/A")
                take_profit = position.get("take_profit", "N/A")
                trailing_activated = position.get("trailing_activated", False)
                trailing_stop = position.get("trailing_stop", "N/A")
                
                current_price = price_dict.get(symbol, "N/A")
                if current_price != "N/A":
                    if side == "LONG":
                        pnl_percent = (current_price - entry_price) / entry_price * 100 * leverage
                    else:  # SHORT
                        pnl_percent = (entry_price - current_price) / entry_price * 100 * leverage
                else:
                    pnl_percent = "N/A"
                
                print(f"Symbol: {symbol}")
                print(f"  Hướng: {side}")
                print(f"  Giá vào: {entry_price}")
                print(f"  Giá hiện tại: {current_price}")
                print(f"  Số lượng: {quantity}")
                print(f"  Đòn bẩy: {leverage}x")
                print(f"  Stop Loss: {stop_loss}")
                print(f"  Take Profit: {take_profit}")
                print(f"  Trailing Stop: {'Đã kích hoạt' if trailing_activated else 'Chưa kích hoạt'}")
                if trailing_activated:
                    print(f"  Trailing Stop Level: {trailing_stop}")
                
                if pnl_percent != "N/A":
                    print(f"  Unrealized P/L: {pnl_percent:.2f}%")
                else:
                    print(f"  Unrealized P/L: N/A")
                print("")
        except Exception as e:
            print(f"Lỗi khi kiểm tra thủ công: {str(e)}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Quản lý Trailing Stop cho các vị thế đang mở')
    parser.add_argument('--mode', type=str, choices=['service', 'check'], default='check',
                      help='Chế độ hoạt động (service: chạy như dịch vụ, check: kiểm tra thủ công)')
    parser.add_argument('--interval', type=int, default=60,
                      help='Khoảng thời gian giữa các lần cập nhật (giây)')
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    # Khởi tạo quản lý trailing stop
    trailing_stop_manager = PositionTrailingStop()
    
    if args.mode == 'service':
        # Chạy như dịch vụ
        trailing_stop_manager.run_monitoring_service(args.interval)
    else:
        # Kiểm tra thủ công
        trailing_stop_manager.manual_check()

if __name__ == "__main__":
    main()