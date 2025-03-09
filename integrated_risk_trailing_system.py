#!/usr/bin/env python3
"""
Hệ thống tích hợp quản lý rủi ro và trailing stop

Module này tạo một lớp tích hợp giữa hệ thống quản lý rủi ro và trailing stop,
giải quyết vấn đề chồng chéo khi hai hệ thống hoạt động đồng thời và cải thiện
việc bảo vệ lợi nhuận cho các vị thế đang mở.
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Tuple, Optional, Union, Any
from binance_api import BinanceAPI
from leverage_risk_manager import LeverageRiskManager
from position_trailing_stop import PositionTrailingStop

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("integrated_risk_system")

class IntegratedRiskTrailingSystem:
    """Lớp tích hợp hệ thống quản lý rủi ro và trailing stop"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                config_path: str = 'account_config.json',
                risk_config_path: str = 'risk_config.json',
                positions_file: str = 'active_positions.json'):
        """
        Khởi tạo hệ thống tích hợp
        
        Args:
            api_key (str, optional): API Key Binance
            api_secret (str, optional): API Secret Binance
            config_path (str): Đường dẫn đến file cấu hình tài khoản
            risk_config_path (str): Đường dẫn đến file cấu hình rủi ro
            positions_file (str): Đường dẫn file lưu vị thế active
        """
        self.config_path = config_path
        self.risk_config_path = risk_config_path
        self.positions_file = positions_file
        
        # Khởi tạo Binance API (BinanceAPI chấp nhận None cho api_key và api_secret)
        self.api = BinanceAPI(api_key, api_secret)
        
        # Khởi tạo hệ thống quản lý rủi ro
        self.risk_manager = LeverageRiskManager(self.api, config_path=risk_config_path)
        
        # Khởi tạo hệ thống trailing stop (PositionTrailingStop chấp nhận None cho api_key và api_secret)
        self.trailing_system = PositionTrailingStop(api_key, api_secret, config_path, positions_file)
        
        # Tải cấu hình tích hợp
        self.load_integration_config()
    
    def load_integration_config(self) -> Dict:
        """
        Tải cấu hình tích hợp từ file
        
        Returns:
            Dict: Cấu hình tích hợp
        """
        try:
            with open(self.risk_config_path, 'r') as f:
                self.risk_config = json.load(f)
            
            # Đảm bảo các thiết lập tích hợp tồn tại
            if 'integration' not in self.risk_config:
                self.risk_config['integration'] = {
                    "sync_stop_loss": True,  # Đồng bộ stop loss giữa hai hệ thống
                    "override_strategy": "most_protective",  # Chiến lược ghi đè ('most_protective', 'trailing_priority', 'fixed_priority')
                    "notify_conflicts": True,  # Thông báo khi phát hiện xung đột
                    "auto_resolve_conflicts": True  # Tự động giải quyết xung đột
                }
                # Lưu cấu hình đã cập nhật
                with open(self.risk_config_path, 'w') as f:
                    json.dump(self.risk_config, f, indent=4)
                logger.info("Đã tạo cấu hình tích hợp mặc định")
            
            return self.risk_config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình tích hợp: {str(e)}")
            # Tạo cấu hình mặc định
            self.risk_config = {
                "integration": {
                    "sync_stop_loss": True,
                    "override_strategy": "most_protective",
                    "notify_conflicts": True,
                    "auto_resolve_conflicts": True
                }
            }
            return self.risk_config
    
    def update_positions_from_binance(self) -> Dict:
        """
        Cập nhật vị thế từ Binance
        
        Returns:
            Dict: Kết quả cập nhật
        """
        result = {"updated": 0, "new": 0, "errors": 0}
        
        try:
            # Lấy thông tin vị thế từ Binance
            binance_positions = self.api.futures_get_position()
            
            # Lọc các vị thế có số lượng > 0
            active_positions = [pos for pos in binance_positions if float(pos.get('positionAmt', 0)) != 0]
            
            if not active_positions:
                logger.info("Không tìm thấy vị thế active nào trên Binance")
                return result
            
            # Cập nhật vị thế trong hệ thống
            for pos in active_positions:
                try:
                    symbol = pos['symbol']
                    position_amt = float(pos['positionAmt'])
                    entry_price = float(pos['entryPrice'])
                    leverage = int(pos['leverage'])
                    
                    # Xác định hướng vị thế
                    side = "LONG" if position_amt > 0 else "SHORT"
                    quantity = abs(position_amt)
                    
                    # Kiểm tra xem vị thế đã tồn tại trong hệ thống chưa
                    if symbol in self.risk_manager.positions:
                        # Cập nhật vị thế hiện có
                        self.risk_manager.positions[symbol].update({
                            "side": side,
                            "entry_price": entry_price,
                            "quantity": quantity,
                            "leverage": leverage,
                            "current_price": float(pos['markPrice']),
                            "unrealized_profit": float(pos['unrealizedProfit'])
                        })
                        result["updated"] += 1
                        logger.info(f"Đã cập nhật vị thế {symbol} từ Binance")
                    else:
                        # Thêm vị thế mới
                        self.risk_manager.track_open_position(
                            symbol=symbol,
                            side=side,
                            entry_price=entry_price,
                            quantity=quantity,
                            leverage=leverage
                        )
                        result["new"] += 1
                        logger.info(f"Đã thêm vị thế mới {symbol} từ Binance")
                    
                except Exception as e:
                    result["errors"] += 1
                    position_symbol = symbol if 'symbol' in locals() else pos.get('symbol', 'unknown')
                    logger.error(f"Lỗi khi cập nhật vị thế {position_symbol} từ Binance: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy vị thế từ Binance: {str(e)}")
            result["errors"] += 1
            return result
            
    def set_binance_sl_tp_orders(self, symbol: str, side: str, stop_loss: float = None, take_profit: float = None) -> Dict:
        """
        Đặt lệnh SL/TP trực tiếp trên Binance
        
        Args:
            symbol (str): Mã cặp tiền
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            stop_loss (float, optional): Giá stop loss
            take_profit (float, optional): Giá take profit
            
        Returns:
            Dict: Kết quả đặt lệnh
        """
        result = {"success": False, "sl_order": None, "tp_order": None, "errors": []}
        
        try:
            # Hủy tất cả các lệnh SL/TP cũ nếu có
            self.api.futures_cancel_all_orders(symbol)
            
            # Đặt Stop Loss nếu có
            if stop_loss:
                try:
                    sl_result = self.api.futures_set_stop_loss(
                        symbol=symbol,
                        side=side,
                        stop_price=stop_loss,
                        close_position=True
                    )
                    
                    if "error" not in sl_result:
                        result["sl_order"] = sl_result
                        logger.info(f"Đã đặt Stop Loss cho {symbol} {side} tại mức {stop_loss}")
                    else:
                        result["errors"].append(f"Lỗi đặt SL: {sl_result.get('error')}")
                        logger.error(f"Lỗi khi đặt Stop Loss cho {symbol}: {sl_result}")
                        
                except Exception as e:
                    result["errors"].append(f"Lỗi đặt SL: {str(e)}")
                    logger.error(f"Lỗi khi đặt Stop Loss cho {symbol}: {str(e)}")
            
            # Đặt Take Profit nếu có
            if take_profit:
                try:
                    tp_result = self.api.futures_set_take_profit(
                        symbol=symbol,
                        side=side,
                        take_profit_price=take_profit,
                        close_position=True
                    )
                    
                    if "error" not in tp_result:
                        result["tp_order"] = tp_result
                        logger.info(f"Đã đặt Take Profit cho {symbol} {side} tại mức {take_profit}")
                    else:
                        result["errors"].append(f"Lỗi đặt TP: {tp_result.get('error')}")
                        logger.error(f"Lỗi khi đặt Take Profit cho {symbol}: {tp_result}")
                        
                except Exception as e:
                    result["errors"].append(f"Lỗi đặt TP: {str(e)}")
                    logger.error(f"Lỗi khi đặt Take Profit cho {symbol}: {str(e)}")
            
            # Kết quả tổng hợp
            if not result["errors"]:
                result["success"] = True
                
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh SL/TP trên Binance cho {symbol}: {str(e)}")
            result["errors"].append(str(e))
            return result
    
    def synchronize_with_binance(self) -> Dict:
        """
        Đồng bộ hóa thiết lập bảo vệ (SL/TP) với Binance cho tất cả vị thế
        
        Returns:
            Dict: Kết quả đồng bộ hóa
        """
        result = {"synchronized": 0, "errors": 0}
        
        try:
            # Cập nhật vị thế từ Binance trước khi đồng bộ
            self.update_positions_from_binance()
            
            # Đồng bộ dữ liệu giữa hệ thống quản lý rủi ro và trailing stop
            self.synchronize_stop_loss_settings()
            
            # Lấy danh sách vị thế từ hệ thống quản lý rủi ro
            positions = self.risk_manager.positions
            
            for symbol, position in positions.items():
                try:
                    side = position["side"]
                    stop_loss = position.get("stop_loss")
                    take_profit = position.get("take_profit")
                    trailing_activated = position.get("trailing_activated", False)
                    trailing_stop = position.get("trailing_stop")
                    
                    # Nếu trailing stop đã kích hoạt, sử dụng mức trailing stop
                    if trailing_activated and trailing_stop:
                        stop_loss = trailing_stop
                    
                    # Đặt lệnh SL/TP trên Binance
                    sl_tp_result = self.set_binance_sl_tp_orders(
                        symbol=symbol,
                        side=side,
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )
                    
                    if sl_tp_result["success"]:
                        # Đánh dấu đã đồng bộ với Binance
                        position["binance_sl_updated"] = True
                        result["synchronized"] += 1
                        logger.info(f"Đã đồng bộ SL/TP cho {symbol} với Binance")
                    else:
                        result["errors"] += 1
                        logger.error(f"Không thể đồng bộ SL/TP cho {symbol} với Binance: {sl_tp_result['errors']}")
                        
                except Exception as e:
                    result["errors"] += 1
                    logger.error(f"Lỗi khi đồng bộ SL/TP cho {symbol} với Binance: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ với Binance: {str(e)}")
            result["errors"] += 1
            return result
    
    def synchronize_stop_loss_settings(self) -> Dict:
        """
        Đồng bộ hóa thiết lập stop loss giữa hai hệ thống
        
        Returns:
            Dict: Kết quả đồng bộ hóa
        """
        result = {"synchronized": 0, "conflicts": 0, "errors": 0}
        
        try:
            # Lấy danh sách vị thế từ cả hai hệ thống
            risk_positions = self.risk_manager.positions
            trailing_positions = self.trailing_system.active_positions
            
            # Duyệt qua tất cả các vị thế
            all_symbols = set(list(risk_positions.keys()) + list(trailing_positions.keys()))
            
            for symbol in all_symbols:
                try:
                    # Kiểm tra vị thế tồn tại trong cả hai hệ thống
                    risk_pos = risk_positions.get(symbol)
                    trail_pos = trailing_positions.get(symbol)
                    
                    if risk_pos is None and trail_pos is None:
                        continue
                    
                    if risk_pos is None and trail_pos is not None:
                        # Vị thế chỉ tồn tại trong hệ thống trailing
                        # Thêm vị thế vào hệ thống quản lý rủi ro
                        self.risk_manager.track_open_position(
                            symbol=symbol,
                            side=trail_pos["side"],
                            entry_price=trail_pos["entry_price"],
                            quantity=trail_pos["quantity"],
                            leverage=trail_pos["leverage"],
                            stop_loss=trail_pos.get("stop_loss"),
                            take_profit=trail_pos.get("take_profit")
                        )
                        result["synchronized"] += 1
                        logger.info(f"Đã thêm vị thế {symbol} vào hệ thống quản lý rủi ro")
                        continue
                    
                    if risk_pos is not None and trail_pos is None:
                        # Vị thế chỉ tồn tại trong hệ thống quản lý rủi ro
                        # Thêm vị thế vào hệ thống trailing stop
                        self.trailing_system.active_positions[symbol] = {
                            "symbol": symbol,
                            "side": risk_pos["side"],
                            "entry_price": risk_pos["entry_price"],
                            "quantity": risk_pos["quantity"],
                            "leverage": risk_pos["leverage"],
                            "stop_loss": risk_pos.get("stop_loss"),
                            "take_profit": risk_pos.get("take_profit"),
                            "trailing_activated": False,
                            "entry_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "highest_price": risk_pos["entry_price"] if risk_pos["side"] == "LONG" else None,
                            "lowest_price": risk_pos["entry_price"] if risk_pos["side"] == "SHORT" else None,
                            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        self.trailing_system.save_active_positions()
                        result["synchronized"] += 1
                        logger.info(f"Đã thêm vị thế {symbol} vào hệ thống trailing stop")
                        continue
                    
                    # Vị thế tồn tại trong cả hai hệ thống, kiểm tra và giải quyết xung đột
                    conflict = False
                    
                    # Kiểm tra sự khác biệt về stop loss
                    risk_sl = risk_pos.get("stop_loss") if risk_pos else None
                    trail_sl = trail_pos.get("stop_loss") if trail_pos else None
                    trail_trailing_sl = trail_pos.get("trailing_stop") if trail_pos else None
                    
                    if risk_sl is not None and trail_sl is not None and abs(risk_sl - trail_sl) > 0.001:
                        conflict = True
                        logger.warning(f"Phát hiện xung đột stop loss cho {symbol}: risk={risk_sl}, trailing={trail_sl}")
                    
                    if conflict and self.risk_config["integration"]["auto_resolve_conflicts"]:
                        # Tự động giải quyết xung đột theo chiến lược đã cấu hình
                        strategy = self.risk_config["integration"]["override_strategy"]
                        
                        if strategy == "most_protective":
                            # Chọn stop loss bảo vệ tốt hơn (gần giá hiện tại hơn)
                            if risk_pos and risk_pos.get("side") == "LONG":
                                new_stop_loss = max(risk_sl or 0, trail_sl or 0, trail_trailing_sl or 0)
                            else:  # SHORT
                                if risk_sl and trail_sl:
                                    new_stop_loss = min(risk_sl, trail_sl)
                                elif risk_sl:
                                    new_stop_loss = risk_sl
                                else:
                                    new_stop_loss = trail_sl
                                    
                                if trail_trailing_sl:
                                    new_stop_loss = min(new_stop_loss, trail_trailing_sl) if new_stop_loss else trail_trailing_sl
                        
                        elif strategy == "trailing_priority":
                            # Ưu tiên stop loss từ hệ thống trailing
                            new_stop_loss = trail_trailing_sl or trail_sl
                        
                        elif strategy == "fixed_priority":
                            # Ưu tiên stop loss từ hệ thống quản lý rủi ro cố định
                            new_stop_loss = risk_sl
                        
                        else:
                            # Mặc định là most_protective
                            if risk_pos and risk_pos.get("side") == "LONG":
                                new_stop_loss = max(risk_sl or 0, trail_sl or 0, trail_trailing_sl or 0)
                            else:  # SHORT
                                if risk_sl and trail_sl:
                                    new_stop_loss = min(risk_sl, trail_sl)
                                elif risk_sl:
                                    new_stop_loss = risk_sl
                                else:
                                    new_stop_loss = trail_sl
                                    
                                if trail_trailing_sl:
                                    new_stop_loss = min(new_stop_loss, trail_trailing_sl) if new_stop_loss else trail_trailing_sl
                        
                        # Cập nhật stop loss trong cả hai hệ thống
                        if new_stop_loss and risk_pos and trail_pos:
                            risk_pos["stop_loss"] = new_stop_loss
                            trail_pos["stop_loss"] = new_stop_loss
                            result["synchronized"] += 1
                            logger.info(f"Đã đồng bộ stop loss cho {symbol} thành {new_stop_loss}")
                    
                    elif conflict:
                        result["conflicts"] += 1
                
                except Exception as e:
                    logger.error(f"Lỗi khi đồng bộ hóa cho {symbol}: {str(e)}")
                    result["errors"] += 1
            
            # Lưu lại thay đổi
            self.trailing_system.save_active_positions()
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ hóa stop loss: {str(e)}")
            result["errors"] += 1
            return result
    
    def update_all_positions(self) -> Dict:
        """
        Cập nhật tất cả các vị thế (bao gồm cả quản lý rủi ro và trailing stop)
        
        Returns:
            Dict: Kết quả cập nhật
        """
        result = {"positions_updated": 0, "trailing_updates": 0, "stop_loss_hit": 0, "take_profit_hit": 0}
        
        try:
            # Đồng bộ hóa thiết lập giữa hai hệ thống
            sync_result = self.synchronize_stop_loss_settings()
            
            # Lấy giá thị trường hiện tại
            all_tickers = self.api.get_price_ticker()
            price_dict = {ticker['symbol']: float(ticker['price']) for ticker in all_tickers}
            
            # Lấy danh sách vị thế từ hệ thống quản lý rủi ro (đã đồng bộ)
            positions = self.risk_manager.positions
            
            for symbol, position in positions.items():
                if symbol not in price_dict:
                    logger.warning(f"Không tìm thấy giá hiện tại cho {symbol}")
                    continue
                
                current_price = price_dict[symbol]
                
                # Kiểm tra trạng thái vị thế
                side = position["side"]
                entry_price = position["entry_price"]
                leverage = position["leverage"]
                stop_loss = position.get("stop_loss")
                take_profit = position.get("take_profit")
                
                # Tính lợi nhuận hiện tại
                if side == "LONG":
                    profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
                else:  # SHORT
                    profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
                
                # Kiểm tra các điều kiện đóng vị thế
                position_closed = False
                close_reason = None
                
                # 1. Kiểm tra stop loss cố định
                if stop_loss and ((side == "LONG" and current_price <= stop_loss) or
                                 (side == "SHORT" and current_price >= stop_loss)):
                    position_closed = True
                    close_reason = "stop_loss"
                    result["stop_loss_hit"] += 1
                
                # 2. Kiểm tra take profit
                if not position_closed and take_profit and ((side == "LONG" and current_price >= take_profit) or
                                                          (side == "SHORT" and current_price <= take_profit)):
                    position_closed = True
                    close_reason = "take_profit"
                    result["take_profit_hit"] += 1
                
                # 3. Cập nhật trailing stop và kiểm tra xem nó có bị kích hoạt không
                if not position_closed:
                    trailing_result = self.risk_manager.update_position_with_trailing_stop(symbol, current_price)
                    
                    # Kiểm tra nếu trailing stop đã được kích hoạt và cần cập nhật trên Binance
                    if trailing_result.get("trailing_activated", False) and not position.get("binance_sl_updated", False):
                        # Trailing stop đã được kích hoạt, cập nhật stop loss trên Binance
                        trailing_stop_price = position.get("trailing_stop")
                        if trailing_stop_price:
                            # Hủy tất cả các lệnh cũ (SL, TP) để tránh xung đột
                            self.api.futures_cancel_all_orders(symbol)
                            
                            # Đặt lệnh stop loss mới dựa trên trailing stop
                            sl_result = self.api.futures_set_stop_loss(
                                symbol=symbol,
                                side=side,
                                stop_price=trailing_stop_price,
                                close_position=True
                            )
                            
                            # Nếu còn take profit, đặt lại
                            if take_profit:
                                tp_result = self.api.futures_set_take_profit(
                                    symbol=symbol,
                                    side=side,
                                    take_profit_price=take_profit,
                                    close_position=True
                                )
                            
                            # Đánh dấu đã cập nhật SL trên Binance
                            position["binance_sl_updated"] = True
                            logger.info(f"Đã cập nhật trailing stop trên Binance cho {symbol} tại mức {trailing_stop_price}")
                            result["trailing_updates"] += 1
                    
                    if trailing_result.get("position_closed", False):
                        position_closed = True
                        close_reason = "trailing_stop"
                        result["trailing_updates"] += 1
                
                # Xử lý đóng vị thế nếu cần
                if position_closed:
                    logger.info(f"Vị thế {symbol} {side} đã đóng do {close_reason}. "
                               f"Entry: {entry_price}, Exit: {current_price}, P/L: {profit_percent:.2f}%")
                    
                    # Xóa vị thế khỏi cả hai hệ thống
                    del self.risk_manager.positions[symbol]
                    
                    if symbol in self.trailing_system.active_positions:
                        del self.trailing_system.active_positions[symbol]
                        self.trailing_system.save_active_positions()
                    
                    # Thực hiện đóng vị thế thực tế tại Binance
                    self.api.futures_close_position(symbol=symbol, side=side)
                    
                    # Gửi thông báo
                    self._send_position_close_notification(symbol, side, entry_price, current_price, 
                                                         profit_percent, close_reason or "unknown")
                else:
                    # Cập nhật thông tin vị thế
                    self.risk_manager.positions[symbol].update({
                        "current_price": current_price,
                        "profit_percent": profit_percent,
                        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Đảm bảo thông tin vị thế được đồng bộ với hệ thống trailing stop
                    if symbol in self.trailing_system.active_positions:
                        self.trailing_system.active_positions[symbol].update({
                            "current_price": current_price,
                            "profit_percent": profit_percent,
                            "stop_loss": self.risk_manager.positions[symbol].get("stop_loss"),
                            "trailing_stop": self.risk_manager.positions[symbol].get("trailing_stop"),
                            "trailing_activated": self.risk_manager.positions[symbol].get("trailing_activated", False),
                            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    
                    result["positions_updated"] += 1
            
            # Lưu lại thay đổi
            self.trailing_system.save_active_positions()
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật vị thế: {str(e)}")
            return result
    
    def _send_position_close_notification(self, symbol: str, side: str, entry_price: float, 
                                       exit_price: float, profit_percent: float, close_reason: str) -> bool:
        """
        Gửi thông báo khi đóng vị thế
        
        Args:
            symbol (str): Mã cặp giao dịch
            side (str): Hướng vị thế ('LONG' hoặc 'SHORT')
            entry_price (float): Giá vào lệnh
            exit_price (float): Giá thoát lệnh
            profit_percent (float): Phần trăm lợi nhuận
            close_reason (str): Lý do đóng vị thế
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        try:
            # Thử tải TelegramNotifier nếu có
            try:
                from telegram_notifier import TelegramNotifier
                telegram = TelegramNotifier()
                
                notification_data = {
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "profit_percent": profit_percent,
                    "close_reason": close_reason
                }
                
                telegram.send_position_close_notification(notification_data)
                logger.info(f"Đã gửi thông báo đóng vị thế qua Telegram cho {symbol}")
                return True
            
            except Exception as e:
                logger.warning(f"Không thể gửi thông báo Telegram: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo: {str(e)}")
            return False
    
    def run_monitoring_service(self, interval: int = 30):
        """
        Chạy dịch vụ giám sát tích hợp
        
        Args:
            interval (int): Khoảng thời gian giữa các lần cập nhật (giây)
        """
        logger.info(f"Bắt đầu dịch vụ giám sát tích hợp với chu kỳ {interval} giây")
        
        try:
            import time
            
            # Đếm chu kỳ cập nhật (đồng bộ với Binance mỗi 5 chu kỳ)
            cycle_count = 0
            binance_sync_frequency = 5  # Đồng bộ với Binance mỗi 5 chu kỳ
            
            running = True
            while running:
                try:
                    cycle_count += 1
                    
                    # Cập nhật vị thế từ sàn giao dịch
                    self.trailing_system.update_positions_from_exchange()
                    
                    # Cập nhật và đồng bộ hóa tất cả các vị thế
                    result = self.update_all_positions()
                    
                    if sum(result.values()) > 0:
                        logger.info(f"Kết quả cập nhật: {result}")
                    
                    # Định kỳ đồng bộ SL/TP với Binance (mỗi binance_sync_frequency chu kỳ)
                    if cycle_count % binance_sync_frequency == 0:
                        logger.info("Đồng bộ hóa theo lịch trình với Binance...")
                        binance_sync_result = self.synchronize_with_binance()
                        logger.info(f"Kết quả đồng bộ với Binance: {binance_sync_result}")
                    
                    # Chờ đến lần cập nhật tiếp theo
                    time.sleep(interval)
                
                except KeyboardInterrupt:
                    logger.info("Đã nhận tín hiệu dừng dịch vụ")
                    running = False
                
                except Exception as e:
                    logger.error(f"Lỗi trong chu kỳ cập nhật: {str(e)}")
                    time.sleep(interval)
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy dịch vụ giám sát: {str(e)}")
    
    def check_positions(self) -> None:
        """Hiển thị tất cả các vị thế đang mở"""
        positions = self.risk_manager.positions
        
        print("\n=== DANH SÁCH VỊ THẾ ĐANG MỞ ===")
        if not positions:
            print("Không có vị thế đang mở")
            return
        
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
        
        for symbol, position in positions.items():
            side = position["side"]
            entry_price = position["entry_price"]
            current_price = price_dict.get(symbol, None)
            
            # Tính lợi nhuận nếu có giá hiện tại
            profit_str = ""
            if current_price:
                if side == "LONG":
                    profit_percent = (current_price - entry_price) / entry_price * 100 * position["leverage"]
                else:  # SHORT
                    profit_percent = (entry_price - current_price) / entry_price * 100 * position["leverage"]
                profit_str = f"Unrealized P/L: {profit_percent:.2f}%"
            
            # Kiểm tra trạng thái trailing stop
            trailing_activated = position.get("trailing_activated", False)
            trailing_status = "Đã kích hoạt" if trailing_activated else "Chưa kích hoạt"
            trailing_price = position.get("trailing_stop", None)
            
            # Hiển thị giá trailing stop dạng chuỗi
            if trailing_activated and trailing_price is not None:
                trailing_price = f"{trailing_price:.2f}"
            else:
                trailing_price = "N/A"
            
            # Kiểm tra trạng thái SL/TP trên Binance
            binance_sl = "Không"
            binance_tp = "Không"
            binance_sl_price = "N/A"
            binance_tp_price = "N/A"
            
            if symbol in binance_orders:
                for order in binance_orders[symbol]:
                    order_type = order.get("type", "")
                    stop_price = order.get("stopPrice", "N/A")
                    
                    if order_type == "STOP_MARKET":
                        binance_sl = "Có"
                        binance_sl_price = stop_price
                    elif order_type == "TAKE_PROFIT_MARKET":
                        binance_tp = "Có"
                        binance_tp_price = stop_price
            
            print(f"Symbol: {symbol}")
            print(f"  Hướng: {side}")
            print(f"  Giá vào: {entry_price}")
            print(f"  Giá hiện tại: {current_price}")
            print(f"  Số lượng: {position['quantity']}")
            print(f"  Đòn bẩy: {position['leverage']}x")
            print(f"  Stop Loss: {position.get('stop_loss', 'N/A')}")
            print(f"  Take Profit: {position.get('take_profit', 'N/A')}")
            print(f"  Trailing Stop: {trailing_status} ({trailing_price})")
            print(f"  SL trên Binance: {binance_sl} ({binance_sl_price})")
            print(f"  TP trên Binance: {binance_tp} ({binance_tp_price})")
            print(f"  Đồng bộ với Binance: {position.get('binance_sl_updated', False)}")
            print(f"  {profit_str}\n")


def main():
    """Hàm chính để chạy hệ thống tích hợp"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hệ thống tích hợp quản lý rủi ro và trailing stop")
    parser.add_argument("--mode", choices=["check", "service", "sync"], default="check",
                       help="Chế độ chạy (check: kiểm tra vị thế, service: chạy dịch vụ, sync: đồng bộ với Binance)")
    parser.add_argument("--interval", type=int, default=30,
                       help="Khoảng thời gian giữa các lần cập nhật (giây)")
    args = parser.parse_args()
    
    system = IntegratedRiskTrailingSystem()
    
    if args.mode == "check":
        # Đồng bộ hóa vị thế trước khi hiển thị
        system.synchronize_stop_loss_settings()
        system.check_positions()
    
    elif args.mode == "sync":
        # Đồng bộ hóa vị thế và SL/TP với Binance
        print("Đồng bộ hóa SL/TP với Binance...")
        result = system.synchronize_with_binance()
        print(f"Kết quả đồng bộ: {result}")
        
        # Hiển thị vị thế sau khi đồng bộ
        print("\nVị thế sau khi đồng bộ:")
        system.check_positions()
    
    elif args.mode == "service":
        # Đồng bộ hóa vị thế và SL/TP với Binance khi bắt đầu
        print("Đồng bộ hóa SL/TP với Binance trước khi bắt đầu dịch vụ...")
        result = system.synchronize_with_binance()
        print(f"Kết quả đồng bộ: {result}")
        
        system.run_monitoring_service(interval=args.interval)


if __name__ == "__main__":
    main()