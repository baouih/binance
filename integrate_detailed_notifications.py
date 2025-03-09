#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tích hợp thông báo chi tiết vào hệ thống giao dịch hiện tại

Script này kết nối mô-đun thông báo chi tiết với hệ thống giao dịch để gửi
thông báo đầy đủ về các hoạt động giao dịch qua Telegram.
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("integrate_detailed_notifications.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("integrate_detailed_notifications")

# Import các module cần thiết
try:
    from detailed_trade_notifications import DetailedTradeNotifications
    from enhanced_binance_api import EnhancedBinanceAPI
    from telegram_notifier import TelegramNotifier
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đã tạo các module cần thiết")
    sys.exit(1)

class IntegratedNotificationSystem:
    """Lớp tích hợp hệ thống thông báo chi tiết với hệ thống giao dịch"""
    
    def __init__(self, config_path: str = 'account_config.json'):
        """
        Khởi tạo hệ thống thông báo tích hợp
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Khởi tạo các thành phần
        self.binance_api = EnhancedBinanceAPI(config_path=config_path)
        self.notifier = DetailedTradeNotifications()
        self.telegram = TelegramNotifier()
        
        # Các biến kiểm soát
        self.running = False
        self.update_thread = None
        
        # Theo dõi các vị thế
        self.current_positions = []
        self.previous_positions = []
        
        logger.info("Đã khởi tạo hệ thống thông báo tích hợp")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            # Cấu hình mặc định
            return {
                "api_mode": "testnet",
                "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
                "notification_interval": 15
            }
    
    def start_monitoring(self) -> None:
        """Bắt đầu theo dõi vị thế và gửi thông báo"""
        if self.running:
            logger.warning("Hệ thống theo dõi đã đang chạy")
            return
        
        logger.info("Bắt đầu theo dõi vị thế và gửi thông báo")
        
        # Bắt đầu thread theo dõi
        self.running = True
        self.update_thread = threading.Thread(target=self._monitor_positions)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # Thông báo khởi động
        self.telegram.send_notification('info', 
            "<b>🚀 HỆ THỐNG THÔNG BÁO CHI TIẾT ĐÃ KHỞI ĐỘNG</b>\n\n"
            f"📊 Đang theo dõi các cặp: {', '.join(self.config.get('symbols', ['BTCUSDT']))}\n"
            f"⏱️ Cập nhật mỗi: {self.config.get('notification_interval', 15)} phút\n\n"
            f"<i>Thời gian khởi động: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        
        logger.info("Đã khởi động hệ thống theo dõi và thông báo")
    
    def stop_monitoring(self) -> None:
        """Dừng theo dõi vị thế và gửi thông báo"""
        if not self.running:
            logger.warning("Hệ thống theo dõi không đang chạy")
            return
        
        logger.info("Dừng theo dõi vị thế và gửi thông báo")
        self.running = False
        
        # Chờ thread kết thúc
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        
        # Thông báo dừng
        self.telegram.send_notification('warning', 
            "<b>⚠️ HỆ THỐNG THÔNG BÁO CHI TIẾT ĐÃ DỪNG</b>\n\n"
            f"<i>Thời gian dừng: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        )
        
        logger.info("Đã dừng hệ thống theo dõi và thông báo")
    
    def _monitor_positions(self) -> None:
        """Hàm theo dõi vị thế trong một thread riêng"""
        logger.info("Bắt đầu thread theo dõi vị thế")
        
        # Lấy khoảng thời gian cập nhật từ cấu hình
        update_interval = self.config.get('notification_interval', 15) * 60  # Đổi sang giây
        
        # Cập nhật ban đầu
        try:
            self._check_position_changes()
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật ban đầu: {e}")
        
        # Gửi thông báo tóm tắt tài khoản
        try:
            self._update_account_summary()
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo tóm tắt tài khoản: {e}")
        
        next_account_update = time.time() + update_interval
        next_daily_stats = time.time() + 24 * 60 * 60  # Mỗi 24 giờ
        
        # Vòng lặp chính
        while self.running:
            try:
                # Kiểm tra thay đổi vị thế
                self._check_position_changes()
                
                # Kiểm tra nếu đến thời gian cập nhật tài khoản
                current_time = time.time()
                if current_time >= next_account_update:
                    self._update_account_summary()
                    next_account_update = current_time + update_interval
                
                # Kiểm tra nếu đến thời gian gửi thống kê hàng ngày
                if current_time >= next_daily_stats:
                    self.notifier.send_daily_stats()
                    next_daily_stats = current_time + 24 * 60 * 60
                
                # Chờ một khoảng thời gian trước khi kiểm tra lại
                time.sleep(30)  # Kiểm tra mỗi 30 giây
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp theo dõi: {e}")
                time.sleep(60)  # Chờ lâu hơn nếu có lỗi
        
        logger.info("Đã kết thúc thread theo dõi vị thế")
    
    def _check_position_changes(self) -> None:
        """Kiểm tra thay đổi vị thế và gửi thông báo"""
        try:
            # Lưu vị thế hiện tại vào previous
            self.previous_positions = self.current_positions.copy()
            
            # Lấy vị thế mới
            self.current_positions = self.binance_api.get_open_positions()
            
            logger.info(f"Đã lấy {len(self.current_positions)} vị thế mở")
            
            # Không có dữ liệu trước đó để so sánh
            if not self.previous_positions:
                return
            
            # Tìm các vị thế mới
            new_positions = []
            for current in self.current_positions:
                is_new = True
                for prev in self.previous_positions:
                    if (current.get('symbol') == prev.get('symbol') and 
                        current.get('positionSide') == prev.get('positionSide')):
                        is_new = False
                        break
                
                if is_new:
                    new_positions.append(current)
            
            # Tìm các vị thế đã đóng
            closed_positions = []
            for prev in self.previous_positions:
                is_closed = True
                for current in self.current_positions:
                    if (prev.get('symbol') == current.get('symbol') and 
                        prev.get('positionSide') == current.get('positionSide')):
                        is_closed = False
                        break
                
                if is_closed:
                    closed_positions.append(prev)
            
            # Gửi thông báo cho các vị thế mới
            for position in new_positions:
                self._notify_new_position(position)
            
            # Gửi thông báo cho các vị thế đã đóng
            for position in closed_positions:
                self._notify_closed_position(position)
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra thay đổi vị thế: {e}")
    
    def _notify_new_position(self, position: Dict) -> None:
        """
        Gửi thông báo cho vị thế mới
        
        Args:
            position (Dict): Thông tin vị thế mới
        """
        try:
            # Lấy thông tin từ vị thế
            symbol = position.get('symbol', 'UNKNOWN')
            side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
            entry_price = float(position.get('entryPrice', 0))
            quantity = abs(float(position.get('positionAmt', 0)))
            leverage = int(position.get('leverage', 1))
            margin = quantity * entry_price / leverage
            
            # Tìm TP và SL nếu có
            tp = 0
            sl = 0
            
            # Đọc dữ liệu phân tích cho lý do vào lệnh
            entry_reason = "Tín hiệu kỹ thuật hợp lệ"
            indicator_values = {}
            
            # Thử đọc từ file recommendation
            recommendation_file = f"recommendation_{symbol.lower()}.json"
            if os.path.exists(recommendation_file):
                try:
                    with open(recommendation_file, 'r') as f:
                        recommendation = json.load(f)
                        
                        # Lấy lý do từ recommendation
                        signal_text = recommendation.get('signal_text', '')
                        if signal_text:
                            entry_reason = signal_text
                        
                        # Lấy giá trị chỉ báo
                        indicators = recommendation.get('indicators', {})
                        if indicators:
                            for key, value in indicators.items():
                                indicator_values[key] = value
                except Exception as e:
                    logger.error(f"Lỗi khi đọc file recommendation: {e}")
            
            # Tạo dữ liệu vào lệnh
            entry_data = {
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'quantity': quantity,
                'leverage': leverage,
                'take_profit': tp,
                'stop_loss': sl,
                'margin_amount': margin,
                'entry_time': datetime.now().isoformat(),
                'entry_reason': entry_reason,
                'indicator_values': indicator_values
            }
            
            # Gửi thông báo
            self.notifier.notify_entry(entry_data)
            
            logger.info(f"Đã gửi thông báo vào lệnh cho {symbol}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo vị thế mới: {e}")
    
    def _notify_closed_position(self, position: Dict) -> None:
        """
        Gửi thông báo cho vị thế đã đóng
        
        Args:
            position (Dict): Thông tin vị thế đã đóng
        """
        try:
            # Lấy thông tin từ vị thế
            symbol = position.get('symbol', 'UNKNOWN')
            side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
            entry_price = float(position.get('entryPrice', 0))
            quantity = abs(float(position.get('positionAmt', 0)))
            
            # Lấy giá hiện tại
            current_price = self._get_current_price(symbol)
            
            # Tính lợi nhuận
            if side == 'LONG':
                profit_percent = (current_price - entry_price) / entry_price * 100 * int(position.get('leverage', 1))
            else:
                profit_percent = (entry_price - current_price) / entry_price * 100 * int(position.get('leverage', 1))
            
            # Tính lợi nhuận tuyệt đối
            margin = quantity * entry_price / int(position.get('leverage', 1))
            profit_amount = profit_percent * margin / 100
            
            # Đọc dữ liệu phân tích cho lý do đóng lệnh
            exit_reason = "Tín hiệu kỹ thuật đảo chiều" if profit_amount > 0 else "Đạt ngưỡng stop loss để bảo vệ vốn"
            
            # Thử đọc từ file recommendation
            recommendation_file = f"recommendation_{symbol.lower()}.json"
            if os.path.exists(recommendation_file):
                try:
                    with open(recommendation_file, 'r') as f:
                        recommendation = json.load(f)
                        
                        # Lấy lý do từ recommendation
                        signal_text = recommendation.get('signal_text', '')
                        if signal_text:
                            if ((side == 'LONG' and 'BÁN' in signal_text) or 
                                (side == 'SHORT' and 'MUA' in signal_text)):
                                exit_reason = f"Tín hiệu đảo chiều: {signal_text}"
                except Exception as e:
                    logger.error(f"Lỗi khi đọc file recommendation: {e}")
            
            # Tạo dữ liệu thoát lệnh
            exit_data = {
                'symbol': symbol,
                'side': side,
                'exit_price': current_price,
                'quantity': quantity,
                'exit_time': datetime.now().isoformat(),
                'exit_reason': exit_reason,
                'profit_amount': profit_amount,
                'profit_percent': profit_percent
            }
            
            # Gửi thông báo
            self.notifier.notify_exit(exit_data)
            
            logger.info(f"Đã gửi thông báo thoát lệnh cho {symbol}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo vị thế đóng: {e}")
    
    def _get_current_price(self, symbol: str) -> float:
        """
        Lấy giá hiện tại của một cặp giao dịch
        
        Args:
            symbol (str): Symbol cặp giao dịch
            
        Returns:
            float: Giá hiện tại
        """
        try:
            price = self.binance_api.get_ticker_price(symbol)
            return price
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá hiện tại của {symbol}: {e}")
            return 0.0
    
    def _update_account_summary(self) -> None:
        """Cập nhật và gửi thông báo tóm tắt tài khoản"""
        try:
            # Lấy thông tin tài khoản
            account_balance = self.binance_api.get_account_balance()
            
            if not account_balance:
                logger.warning("Không lấy được thông tin số dư tài khoản")
                return
            
            # Tính tổng số dư và số dư khả dụng
            total_balance = account_balance.get('totalWalletBalance', 0)
            available_balance = account_balance.get('availableBalance', 0)
            
            # Tính tổng margin và lợi nhuận
            positions = self.binance_api.get_open_positions()
            unrealized_pnl = sum(float(p.get('unrealizedProfit', 0)) for p in positions)
            
            # Tạo dữ liệu tài khoản
            account_data = {
                'total_balance': float(total_balance),
                'available_balance': float(available_balance),
                'margin_balance': float(total_balance),
                'unrealized_pnl': unrealized_pnl,
                'positions': positions
            }
            
            # Gửi thông báo
            self.notifier.notify_account_summary(account_data)
            
            logger.info(f"Đã gửi thông báo tóm tắt tài khoản")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật tóm tắt tài khoản: {e}")

def main():
    """Hàm chính"""
    try:
        logger.info("Khởi động hệ thống thông báo tích hợp")
        
        # Khởi tạo hệ thống
        system = IntegratedNotificationSystem()
        
        # Bắt đầu theo dõi
        system.start_monitoring()
        
        # Giữ cho tiến trình chạy
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng từ người dùng")
            system.stop_monitoring()
        
        logger.info("Hệ thống thông báo tích hợp đã dừng")
        return 0
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())