#!/usr/bin/env python3
"""
Hệ thống tích hợp nâng cao cho quản lý rủi ro và trailing stop

Module này cung cấp một lớp tích hợp nâng cao giữa các hệ thống quản lý rủi ro,
trailing stop, đồng bộ dữ liệu Binance, quản lý cache, và thông báo,
giải quyết các vấn đề trong hệ thống hiện tại và cải thiện quy trình giao dịch.
"""

import os
import json
import time
import logging
import datetime
import random
from typing import Dict, List, Tuple, Optional, Union, Any

# Import các module cơ bản
from binance_api import BinanceAPI
from leverage_risk_manager import LeverageRiskManager

# Import các module cải tiến
from binance_synchronizer import BinanceSynchronizer
from data_cache import DataCache, ObservableDataCache
from advanced_trailing_stop import AdvancedTrailingStop
from enhanced_notification import EnhancedNotification, TelegramNotifier

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("enhanced_integrated_system")

class EnhancedIntegratedSystem:
    """Lớp tích hợp nâng cao các hệ thống giao dịch"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                config_path: str = 'account_config.json',
                risk_config_path: str = 'risk_config.json',
                positions_file: str = 'active_positions.json',
                notification_config: str = None,
                cache_dir: str = 'cache'):
        """
        Khởi tạo hệ thống tích hợp nâng cao
        
        Args:
            api_key (str, optional): API Key Binance
            api_secret (str, optional): API Secret Binance
            config_path (str): Đường dẫn đến file cấu hình tài khoản
            risk_config_path (str): Đường dẫn đến file cấu hình rủi ro
            positions_file (str): Đường dẫn file lưu vị thế active
            notification_config (str, optional): Đường dẫn file cấu hình thông báo
            cache_dir (str): Thư mục lưu cache dữ liệu
        """
        self.config_path = config_path
        self.risk_config_path = risk_config_path
        self.positions_file = positions_file
        
        # Tải cấu hình tài khoản
        self.account_config = self._load_config(config_path)
        self.risk_config = self._load_config(risk_config_path)
        
        # Khởi tạo Binance API
        self.api = BinanceAPI(api_key, api_secret)
        
        # Khởi tạo DataCache
        self.data_cache = ObservableDataCache(cache_dir=cache_dir)
        
        # Khởi tạo BinanceSynchronizer
        self.synchronizer = BinanceSynchronizer(
            self.api, positions_file=positions_file, max_retries=3
        )
        
        # Khởi tạo hệ thống quản lý rủi ro
        self.risk_manager = LeverageRiskManager(self.api, config_path=risk_config_path)
        
        # Khởi tạo AdvancedTrailingStop
        ts_type = self.risk_config.get('trailing_stop', {}).get('type', 'percentage')
        ts_config = self.risk_config.get('trailing_stop', {}).get('config', {})
        
        self.trailing_stop = AdvancedTrailingStop(
            strategy_type=ts_type,
            data_cache=self.data_cache,
            config=ts_config
        )
        
        # Khởi tạo hệ thống thông báo
        self.notification = EnhancedNotification(config_path=notification_config)
        
        # Đăng ký observer cho dữ liệu giá
        self._register_price_observers()
        
        # Số lần cập nhật kể từ lần đồng bộ cuối cùng
        self.update_count = 0
        # Tần suất đồng bộ (mỗi X lần cập nhật)
        self.sync_frequency = 5
        
        # Thông tin thời gian khởi động
        self.start_time = datetime.datetime.now()
        
        # Thông báo khởi động
        self._send_startup_notification()
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Không tìm thấy file cấu hình: {config_path}")
                return {}
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình từ {config_path}: {str(e)}")
            return {}
    
    def _register_price_observers(self) -> None:
        """Đăng ký observer cho dữ liệu giá để tự động cập nhật trailing stop"""
        
        def on_price_change(category, key, data):
            """Callback khi giá thay đổi"""
            if category == 'market_data' and key.endswith('_price'):
                # Lấy symbol từ key (giả sử key có dạng 'BTCUSDT_price')
                symbol = key.split('_')[0]
                self._update_position_trailing_stop(symbol, data)
        
        # Đăng ký observer cho tất cả cặp tiền đang theo dõi
        symbols = self._get_tracked_symbols()
        for symbol in symbols:
            self.data_cache.register_observer('market_data', f'{symbol}_price', on_price_change)
    
    def _get_tracked_symbols(self) -> List[str]:
        """
        Lấy danh sách các symbol đang theo dõi
        
        Returns:
            List[str]: Danh sách symbols
        """
        # Lấy danh sách symbol từ các vị thế đang mở
        positions = self.synchronizer.active_positions
        symbols = list(positions.keys())
        
        # Thêm các symbol từ cấu hình nếu có
        config_symbols = self.account_config.get('symbols', [])
        for symbol in config_symbols:
            if symbol not in symbols:
                symbols.append(symbol)
        
        return symbols
    
    def _send_startup_notification(self) -> None:
        """Gửi thông báo khởi động hệ thống"""
        try:
            version = "1.0.0"  # Thay đổi theo phiên bản thực tế
            mode = self.account_config.get('api_mode', 'testnet')
            account_type = self.account_config.get('account_type', 'futures')
            
            # Lấy số dư tài khoản
            balance = 0
            try:
                if account_type == 'futures':
                    account_info = self.api.get_futures_account()
                    # Lấy số dư USDT
                    for asset in account_info.get('assets', []):
                        if asset.get('asset') == 'USDT':
                            balance = float(asset.get('walletBalance', 0))
                            break
                else:
                    # Spot account
                    account_info = self.api.get_account()
                    # Lấy số dư USDT
                    for balance_info in account_info.get('balances', []):
                        if balance_info.get('asset') == 'USDT':
                            balance = float(balance_info.get('free', 0))
                            break
            except Exception as e:
                logger.warning(f"Không thể lấy số dư tài khoản: {str(e)}")
            
            # Gửi thông báo
            self.notification.send_system_start_notification(
                version=version,
                mode=mode,
                account=account_type,
                balance=balance
            )
            logger.info("Đã gửi thông báo khởi động hệ thống")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo khởi động: {str(e)}")
    
    def synchronize_with_binance(self) -> Dict:
        """
        Đồng bộ hóa dữ liệu với Binance (vị thế, SL/TP)
        
        Returns:
            Dict: Kết quả đồng bộ hóa
        """
        try:
            # Đồng bộ đầy đủ
            sync_result = self.synchronizer.full_sync_with_binance()
            
            # Đặt lại bộ đếm
            self.update_count = 0
            
            # Ghi log kết quả
            if sync_result['success']:
                logger.info(f"Đồng bộ với Binance thành công: {sync_result['positions_synced']} vị thế, "
                         f"{sync_result['stop_loss_synced']} SL, {sync_result['take_profit_synced']} TP")
            else:
                logger.warning(f"Đồng bộ với Binance không thành công: {', '.join(sync_result['errors'])}")
            
            return sync_result
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ với Binance: {str(e)}")
            return {
                "success": False,
                "errors": [str(e)],
                "positions_synced": 0,
                "stop_loss_synced": 0,
                "take_profit_synced": 0
            }
    
    def update_market_data(self) -> Dict:
        """
        Cập nhật dữ liệu thị trường (giá, chỉ báo)
        
        Returns:
            Dict: Dữ liệu thị trường đã cập nhật
        """
        try:
            # Lấy danh sách symbol cần cập nhật
            symbols = self._get_tracked_symbols()
            
            # Lấy giá hiện tại
            all_tickers = self.api.get_price_ticker()
            price_dict = {ticker['symbol']: float(ticker['price']) for ticker in all_tickers}
            
            # Lưu vào cache
            for symbol, price in price_dict.items():
                if symbol in symbols:
                    self.data_cache.set('market_data', f'{symbol}_price', price)
            
            # Chỉ trả về giá của các symbol đang theo dõi
            result = {symbol: price_dict.get(symbol) for symbol in symbols if symbol in price_dict}
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {str(e)}")
            return {}
    
    def _update_position_trailing_stop(self, symbol: str, current_price: float) -> Dict:
        """
        Cập nhật trailing stop cho một vị thế
        
        Args:
            symbol (str): Symbol của vị thế
            current_price (float): Giá hiện tại
            
        Returns:
            Dict: Kết quả cập nhật
        """
        try:
            # Kiểm tra xem có vị thế cho symbol này không
            if symbol not in self.synchronizer.active_positions:
                return {"success": False, "message": f"Không tìm thấy vị thế {symbol}"}
            
            # Lấy thông tin vị thế
            position = self.synchronizer.active_positions[symbol]
            
            # Khởi tạo vị thế với trailing stop nếu chưa
            if 'trailing_type' not in position:
                position = self.trailing_stop.initialize_position(position)
                self.synchronizer.active_positions[symbol] = position
            
            # Cập nhật giá hiện tại trong vị thế
            position['current_price'] = current_price
            
            # Cập nhật profit_percent
            side = position['side']
            entry_price = position['entry_price']
            leverage = position.get('leverage', 1)
            
            if side == "LONG":
                profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
            else:  # SHORT
                profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
            
            position['profit_percent'] = profit_percent
            
            # Cập nhật trailing stop
            position = self.trailing_stop.update_trailing_stop(position, current_price)
            
            # Kiểm tra điều kiện đóng vị thế
            should_close, reason = self.trailing_stop.check_stop_condition(position, current_price)
            
            # Thông báo nếu trailing stop mới được kích hoạt
            was_activated_before = position.get('notification_sent', False)
            is_activated_now = position.get('trailing_activated', False)
            
            if is_activated_now and not was_activated_before:
                self.notification.notify_trailing_stop(position)
                position['notification_sent'] = True
                logger.info(f"Trailing stop kích hoạt cho {symbol} tại {current_price}")
            
            # Nếu cần đóng vị thế
            if should_close:
                logger.info(f"Nên đóng vị thế {symbol} vì: {reason}")
                # Chi tiết xử lý đóng vị thế sẽ được thực hiện trong close_position()
                return {
                    "success": True,
                    "message": f"Nên đóng vị thế {symbol}",
                    "should_close": True,
                    "reason": reason
                }
            
            # Cập nhật vị thế
            self.synchronizer.active_positions[symbol] = position
            
            # Lưu dữ liệu
            self.synchronizer.save_local_positions()
            
            return {
                "success": True,
                "message": f"Đã cập nhật trailing stop cho {symbol}",
                "should_close": False
            }
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trailing stop cho {symbol}: {str(e)}")
            return {
                "success": False,
                "message": f"Lỗi: {str(e)}",
                "should_close": False
            }
    
    def close_position(self, symbol: str, reason: str = None) -> Dict:
        """
        Đóng một vị thế
        
        Args:
            symbol (str): Symbol của vị thế
            reason (str, optional): Lý do đóng vị thế
            
        Returns:
            Dict: Kết quả đóng vị thế
        """
        try:
            # Kiểm tra xem có vị thế cho symbol này không
            if symbol not in self.synchronizer.active_positions:
                return {"success": False, "message": f"Không tìm thấy vị thế {symbol}"}
            
            # Lấy thông tin vị thế
            position = self.synchronizer.active_positions[symbol]
            
            # Lấy giá hiện tại
            current_price = position.get('current_price')
            if not current_price:
                try:
                    ticker = self.api.get_symbol_ticker(symbol)
                    current_price = float(ticker['price'])
                except Exception as e:
                    logger.error(f"Không thể lấy giá hiện tại cho {symbol}: {str(e)}")
                    # Sử dụng giá cuối cùng đã biết
                    current_price = position.get('entry_price', 0)
            
            # Gọi API Binance để đóng vị thế
            close_result = self.synchronizer.close_position(symbol, reason)
            
            if close_result['success']:
                # Chuẩn bị dữ liệu thông báo
                side = position['side']
                entry_price = position['entry_price']
                quantity = position['quantity']
                leverage = position.get('leverage', 1)
                
                # Tính lợi nhuận
                if side == "LONG":
                    profit_loss = (current_price - entry_price) * quantity * leverage
                    profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
                else:  # SHORT
                    profit_loss = (entry_price - current_price) * quantity * leverage
                    profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
                
                # Dữ liệu cho thông báo
                notification_data = {
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry_price,
                    "exit_price": current_price,
                    "quantity": quantity,
                    "leverage": leverage,
                    "profit_loss": profit_loss,
                    "profit_percent": profit_percent,
                    "close_reason": reason or "Yêu cầu người dùng",
                    "exit_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Gửi thông báo
                self.notification.notify_position_closed(notification_data)
                
                logger.info(f"Đã đóng vị thế {symbol} thành công, P&L: {profit_loss:.2f} USD ({profit_percent:.2f}%)")
                return {
                    "success": True,
                    "message": f"Đã đóng vị thế {symbol}",
                    "profit_loss": profit_loss,
                    "profit_percent": profit_percent
                }
            else:
                logger.error(f"Lỗi khi đóng vị thế {symbol}: {close_result['message']}")
                return close_result
        except Exception as e:
            logger.error(f"Lỗi khi đóng vị thế {symbol}: {str(e)}")
            
            # Gửi thông báo lỗi
            self.notification.notify_error("CLOSE_POSITION_ERROR", f"Lỗi khi đóng vị thế {symbol}: {str(e)}")
            
            return {
                "success": False,
                "message": f"Lỗi: {str(e)}"
            }
    
    def check_positions(self) -> Dict:
        """
        Kiểm tra và hiển thị tất cả các vị thế đang mở
        
        Returns:
            Dict: Thông tin về các vị thế
        """
        result = {
            "positions": {},
            "count": 0,
            "total_value": 0,
            "total_unrealized_pnl": 0
        }
        
        positions = self.synchronizer.active_positions
        
        if not positions:
            logger.info("Không có vị thế đang mở")
            return result
        
        # Cập nhật dữ liệu thị trường
        self.update_market_data()
        
        # Lấy giá hiện tại
        all_tickers = self.api.get_price_ticker()
        price_dict = {ticker['symbol']: float(ticker['price']) for ticker in all_tickers}
        
        # Lấy thông tin về lệnh đang mở trên Binance để đối chiếu
        try:
            binance_orders = {}
            for symbol in positions.keys():
                open_orders = self.api.get_open_orders(symbol=symbol)
                if open_orders:
                    binance_orders[symbol] = open_orders
        except Exception as e:
            logger.error(f"Không thể lấy thông tin lệnh từ Binance: {str(e)}")
            binance_orders = {}
        
        total_value = 0
        total_unrealized_pnl = 0
        
        # Hiển thị thông tin từng vị thế
        logger.info("\n=== DANH SÁCH VỊ THẾ ĐANG MỞ ===")
        for symbol, position in positions.items():
            side = position["side"]
            entry_price = position["entry_price"]
            current_price = price_dict.get(symbol, position.get('current_price'))
            
            # Cập nhật giá hiện tại trong vị thế
            if current_price:
                position['current_price'] = current_price
            
            # Tính lợi nhuận nếu có giá hiện tại
            profit_str = ""
            unrealized_pnl = 0
            if current_price:
                quantity = position.get('quantity', 0)
                leverage = position.get('leverage', 1)
                
                if side == "LONG":
                    profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
                    unrealized_pnl = (current_price - entry_price) * quantity * leverage
                else:  # SHORT
                    profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
                    unrealized_pnl = (entry_price - current_price) * quantity * leverage
                
                position['profit_percent'] = profit_percent
                profit_str = f"Unrealized P&L: {unrealized_pnl:.2f} USD ({profit_percent:.2f}%)"
                
                # Cộng dồn vào tổng
                position_value = current_price * position.get('quantity', 0) * leverage
                total_value += position_value
                total_unrealized_pnl += unrealized_pnl
            
            # Kiểm tra trạng thái trailing stop
            trailing_activated = position.get("trailing_activated", False)
            trailing_status = "Đã kích hoạt" if trailing_activated else "Chưa kích hoạt"
            trailing_price = position.get("trailing_stop", None)
            
            # Hiển thị giá trailing stop dạng chuỗi
            if trailing_activated and trailing_price is not None:
                trailing_price_str = f"{trailing_price:.2f}"
            else:
                trailing_price_str = "N/A"
            
            # Kiểm tra trạng thái SL/TP trên Binance
            binance_sl = "Không"
            binance_tp = "Không"
            binance_sl_price = "N/A"
            binance_tp_price = "N/A"
            
            if symbol in binance_orders:
                for order in binance_orders[symbol]:
                    order_type = order.get('type', '')
                    stop_price = order.get('stopPrice', 'N/A')
                    
                    if order_type == "STOP_MARKET":
                        binance_sl = "Có"
                        binance_sl_price = stop_price
                    elif order_type == "TAKE_PROFIT_MARKET":
                        binance_tp = "Có"
                        binance_tp_price = stop_price
            
            # Hiển thị thông tin
            logger.info(f"Symbol: {symbol}")
            logger.info(f"  Hướng: {side}")
            logger.info(f"  Giá vào: {entry_price}")
            logger.info(f"  Giá hiện tại: {current_price}")
            logger.info(f"  Số lượng: {position['quantity']}")
            logger.info(f"  Đòn bẩy: {position['leverage']}x")
            logger.info(f"  Stop Loss: {position.get('stop_loss', 'N/A')}")
            logger.info(f"  Take Profit: {position.get('take_profit', 'N/A')}")
            logger.info(f"  Trailing Stop: {trailing_status} ({trailing_price_str})")
            logger.info(f"  SL trên Binance: {binance_sl} ({binance_sl_price})")
            logger.info(f"  TP trên Binance: {binance_tp} ({binance_tp_price})")
            logger.info(f"  Đồng bộ với Binance: {position.get('binance_sl_updated', False)}")
            logger.info(f"  {profit_str}\n")
            
            # Lưu vào kết quả
            result["positions"][symbol] = {
                "symbol": symbol,
                "side": side,
                "entry_price": entry_price,
                "current_price": current_price,
                "quantity": position.get('quantity', 0),
                "leverage": position.get('leverage', 1),
                "stop_loss": position.get('stop_loss', None),
                "take_profit": position.get('take_profit', None),
                "trailing_stop": trailing_price,
                "trailing_activated": trailing_activated,
                "profit_percent": position.get('profit_percent', 0),
                "unrealized_pnl": unrealized_pnl
            }
        
        result["count"] = len(positions)
        result["total_value"] = total_value
        result["total_unrealized_pnl"] = total_unrealized_pnl
        
        return result
    
    def check_and_handle_stops(self) -> Dict:
        """
        Kiểm tra và xử lý stop loss/trailing stop cho tất cả vị thế
        
        Returns:
            Dict: Kết quả xử lý
        """
        result = {
            "checked": 0,
            "processed": 0,
            "closed": 0,
            "errors": 0,
            "positions": {}
        }
        
        positions = self.synchronizer.active_positions
        
        if not positions:
            return result
        
        # Cập nhật dữ liệu thị trường
        market_data = self.update_market_data()
        
        # Xử lý từng vị thế
        positions_to_close = []
        for symbol, position in positions.items():
            result["checked"] += 1
            
            try:
                # Lấy giá hiện tại
                current_price = market_data.get(symbol)
                if not current_price:
                    continue
                
                # Cập nhật trailing stop
                update_result = self._update_position_trailing_stop(symbol, current_price)
                result["processed"] += 1
                
                # Nếu cần đóng vị thế
                if update_result.get("should_close", False):
                    positions_to_close.append((symbol, update_result.get("reason", "Trailing Stop")))
                
                # Lưu kết quả
                result["positions"][symbol] = update_result
            except Exception as e:
                logger.error(f"Lỗi khi xử lý vị thế {symbol}: {str(e)}")
                result["errors"] += 1
                result["positions"][symbol] = {
                    "success": False,
                    "message": f"Lỗi: {str(e)}"
                }
        
        # Đóng các vị thế cần đóng
        for symbol, reason in positions_to_close:
            try:
                close_result = self.close_position(symbol, reason)
                if close_result.get("success", False):
                    result["closed"] += 1
            except Exception as e:
                logger.error(f"Lỗi khi đóng vị thế {symbol}: {str(e)}")
                result["errors"] += 1
        
        return result
    
    def run_monitoring_service(self, interval: int = 60):
        """
        Chạy dịch vụ giám sát tích hợp
        
        Args:
            interval (int): Khoảng thời gian giữa các lần cập nhật (giây)
        """
        logger.info(f"Bắt đầu dịch vụ giám sát tích hợp với chu kỳ {interval} giây")
        
        try:
            import time
            
            # Đồng bộ với Binance khi bắt đầu
            logger.info("Đồng bộ với Binance khi bắt đầu...")
            self.synchronize_with_binance()
            
            running = True
            while running:
                try:
                    # Tăng bộ đếm cập nhật
                    self.update_count += 1
                    
                    # Cập nhật dữ liệu thị trường
                    self.update_market_data()
                    
                    # Kiểm tra và xử lý stop loss/trailing stop
                    check_result = self.check_and_handle_stops()
                    if check_result["closed"] > 0:
                        logger.info(f"Đã đóng {check_result['closed']} vị thế do đạt điều kiện stop")
                    
                    # Đồng bộ với Binance theo chu kỳ
                    if self.update_count >= self.sync_frequency:
                        logger.info(f"Đồng bộ định kỳ với Binance sau {self.update_count} lần cập nhật...")
                        self.synchronize_with_binance()
                    
                    # Chờ đến lần cập nhật tiếp theo
                    time.sleep(interval)
                except KeyboardInterrupt:
                    logger.info("Đã nhận tín hiệu thoát, đang dừng dịch vụ...")
                    running = False
                except Exception as e:
                    logger.error(f"Lỗi trong chu trình giám sát: {str(e)}")
                    
                    # Gửi thông báo lỗi
                    try:
                        self.notification.notify_error(
                            "MONITORING_ERROR", 
                            f"Lỗi trong chu trình giám sát: {str(e)}"
                        )
                    except:
                        pass
                    
                    # Chờ một khoảng thời gian ngắn trước khi thử lại
                    time.sleep(5)
        except Exception as e:
            logger.error(f"Lỗi nghiêm trọng trong dịch vụ giám sát: {str(e)}")
            
            # Gửi thông báo lỗi nghiêm trọng
            try:
                self.notification.notify_error(
                    "CRITICAL_ERROR", 
                    f"Lỗi nghiêm trọng trong dịch vụ giám sát: {str(e)}"
                )
            except:
                pass


def main():
    """Hàm chính để chạy hệ thống tích hợp nâng cao"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hệ thống tích hợp nâng cao")
    parser.add_argument("--mode", choices=["check", "service", "sync"], default="check",
                       help="Chế độ chạy (check: kiểm tra vị thế, service: chạy dịch vụ, sync: đồng bộ với Binance)")
    parser.add_argument("--interval", type=int, default=30,
                       help="Khoảng thời gian giữa các lần cập nhật (giây)")
    parser.add_argument("--symbol", type=str, default=None,
                       help="Symbol cụ thể để xử lý (tùy chọn)")
    args = parser.parse_args()
    
    # Khởi tạo hệ thống
    system = EnhancedIntegratedSystem()
    
    if args.mode == "check":
        # Kiểm tra vị thế
        system.check_positions()
    
    elif args.mode == "sync":
        # Đồng bộ với Binance
        print("Đồng bộ với Binance...")
        result = system.synchronize_with_binance()
        print(f"Kết quả đồng bộ: {result}")
        
        # Hiển thị vị thế sau khi đồng bộ
        print("\nVị thế sau khi đồng bộ:")
        system.check_positions()
    
    elif args.mode == "service":
        # Chạy dịch vụ giám sát
        system.run_monitoring_service(interval=args.interval)


if __name__ == "__main__":
    main()