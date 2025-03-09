#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SL/TP Telegram Integration
==========================
Tích hợp Auto SL/TP Manager với hệ thống thông báo Telegram.
Hệ thống này sẽ tự động thiết lập và cập nhật SL/TP cho các vị thế,
đồng thời gửi thông báo qua Telegram về trạng thái vị thế và việc cập nhật SL/TP.

Sử dụng:
    python sltp_telegram_integration.py --testnet --interval 60
"""

import os
import sys
import time
import logging
import traceback
from typing import Dict, Any, Optional

from auto_sltp_manager import AutoSLTPManager
from advanced_telegram_notifier import AdvancedTelegramNotifier

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sltp_telegram_integration")

class EnhancedAutoSLTPManager(AutoSLTPManager):
    """Auto SL/TP Manager tích hợp với Telegram"""
    
    def __init__(self, testnet: bool = False, 
                telegram_config_path: str = "configs/telegram_config.json"):
        """
        Khởi tạo EnhancedAutoSLTPManager
        
        Args:
            testnet: Sử dụng Binance Testnet
            telegram_config_path: Đường dẫn tới file cấu hình Telegram
        """
        # Khởi tạo lớp cha
        super().__init__(api_key="", api_secret="", testnet=testnet)
        
        # Khởi tạo Telegram notifier
        self.notifier = AdvancedTelegramNotifier(config_path=telegram_config_path)
        
        # Gửi thông báo khởi động
        self._send_startup_notification()
    
    def _send_startup_notification(self):
        """Gửi thông báo khởi động"""
        try:
            # Lấy thông tin tài khoản
            balance = 0
            try:
                # Thử lấy thông tin số dư từ API
                balance_data = self.api.futures_account_balance()
                for asset in balance_data:
                    if asset.get('asset') == 'USDT':
                        balance = float(asset.get('balance', 0))
                        break
            except Exception as inner_e:
                logger.error(f"Lỗi khi lấy số dư tài khoản: {str(inner_e)}")
                # Thử cách khác nếu phương thức trên lỗi
                try:
                    position_info = self.api.get_futures_position_risk()
                    balance = float(position_info[0].get('walletBalance', 0)) if position_info else 0
                except Exception as inner_e2:
                    logger.error(f"Không thể lấy số dư sau khi thử phương thức thay thế: {str(inner_e2)}")
            
            # Lấy số lượng vị thế đang mở
            positions = [p for p in self.active_positions.values() if abs(float(p.get('positionAmt', 0))) > 0]
            
            # Gửi thông báo
            self.notifier.notify_system_status(
                status='running',
                uptime=0,
                account_balance=balance,
                positions_count=len(positions),
                next_maintenance=None
            )
            
            logger.info(f"Đã gửi thông báo khởi động tới Telegram")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo khởi động: {str(e)}")
    
    def set_stop_loss(self, symbol: str, side: str, price: float, quantity: float) -> bool:
        """
        Thiết lập Stop Loss với thông báo Telegram
        
        Args:
            symbol (str): Symbol
            side (str): 'LONG' hoặc 'SHORT'
            price (float): Giá stop loss
            quantity (float): Số lượng
            
        Returns:
            bool: True nếu thành công
        """
        # Lưu giá SL cũ nếu có
        old_sl_price = 0
        if symbol in self.position_data:
            old_sl_price = self.position_data[symbol].get('sl_price', 0)
        
        # Gọi hàm cha để đặt SL
        result = super().set_stop_loss(symbol, side, price, quantity)
        
        # Thông báo nếu có thay đổi
        if result and old_sl_price > 0 and old_sl_price != price:
            try:
                self.notifier.notify_sltp_update(
                    symbol=symbol,
                    side=side,
                    old_sl=old_sl_price,
                    new_sl=price,
                    reason='trailing_stop'
                )
                logger.info(f"Đã gửi thông báo cập nhật SL cho {symbol} tới Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo SL: {str(e)}")
        
        return result
    
    def set_take_profit(self, symbol: str, side: str, price: float, quantity: float) -> bool:
        """
        Thiết lập Take Profit với thông báo Telegram
        
        Args:
            symbol (str): Symbol
            side (str): 'LONG' hoặc 'SHORT'
            price (float): Giá take profit
            quantity (float): Số lượng
            
        Returns:
            bool: True nếu thành công
        """
        # Lưu giá TP cũ nếu có
        old_tp_price = 0
        if symbol in self.position_data:
            old_tp_price = self.position_data[symbol].get('tp_price', 0)
        
        # Gọi hàm cha để đặt TP
        result = super().set_take_profit(symbol, side, price, quantity)
        
        # Thông báo nếu có thay đổi
        if result and old_tp_price > 0 and old_tp_price != price:
            try:
                self.notifier.notify_sltp_update(
                    symbol=symbol,
                    side=side,
                    old_tp=old_tp_price,
                    new_tp=price,
                    reason='manual'
                )
                logger.info(f"Đã gửi thông báo cập nhật TP cho {symbol} tới Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo TP: {str(e)}")
        
        return result
    
    def setup_initial_sltp(self, symbol: str, force: bool = False) -> bool:
        """
        Thiết lập SL/TP ban đầu với thông báo Telegram
        
        Args:
            symbol (str): Symbol cần thiết lập
            force (bool): Buộc thiết lập lại nếu đã có
            
        Returns:
            bool: True nếu thành công
        """
        # Lưu trạng thái trước khi thiết lập
        had_sl_tp = False
        if symbol in self.position_data:
            had_sl_tp = self.position_data[symbol].get('sl_price', 0) > 0 and self.position_data[symbol].get('tp_price', 0) > 0
        
        # Gọi hàm cha để thiết lập SL/TP
        result = super().setup_initial_sltp(symbol, force)
        
        # Thông báo nếu đã thiết lập mới
        if result and (force or not had_sl_tp) and symbol in self.position_data:
            try:
                # Lấy thông tin vị thế
                position = self.active_positions[symbol]
                side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
                entry_price = float(position.get('entryPrice', 0))
                
                # Lấy giá SL/TP mới
                sl_price = self.position_data[symbol].get('sl_price', 0)
                tp_price = self.position_data[symbol].get('tp_price', 0)
                
                if sl_price > 0 and tp_price > 0:
                    # Tính toán R:R
                    if side == 'LONG':
                        sl_dist = entry_price - sl_price
                        tp_dist = tp_price - entry_price
                    else:
                        sl_dist = sl_price - entry_price
                        tp_dist = entry_price - tp_price
                    
                    risk_reward = tp_dist / sl_dist if sl_dist > 0 else 0
                    
                    # Gửi thông báo
                    self.notifier.notify_trade_signal(
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        stop_loss=sl_price,
                        take_profit=tp_price,
                        risk_reward=risk_reward,
                        timeframe='1h',
                        strategy='Auto SL/TP'
                    )
                    logger.info(f"Đã gửi thông báo thiết lập SL/TP cho {symbol} tới Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo thiết lập SL/TP: {str(e)}")
        
        return result
    
    def update_trailing_stop(self, symbol: str) -> bool:
        """
        Cập nhật trailing stop với thông báo Telegram
        
        Args:
            symbol (str): Symbol cần cập nhật
            
        Returns:
            bool: True nếu có cập nhật
        """
        # Lưu giá SL cũ
        old_sl_price = 0
        if symbol in self.position_data:
            old_sl_price = self.position_data[symbol].get('sl_price', 0)
        
        # Gọi hàm cha để cập nhật trailing stop
        result = super().update_trailing_stop(symbol)
        
        # Thông báo nếu có cập nhật
        if result and symbol in self.position_data:
            try:
                # Lấy thông tin vị thế
                position = self.active_positions[symbol]
                side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
                
                # Lấy giá SL mới
                new_sl_price = self.position_data[symbol].get('sl_price', 0)
                
                if new_sl_price > 0 and new_sl_price != old_sl_price:
                    # Gửi thông báo
                    self.notifier.notify_sltp_update(
                        symbol=symbol,
                        side=side,
                        old_sl=old_sl_price,
                        new_sl=new_sl_price,
                        reason='trailing_stop'
                    )
                    logger.info(f"Đã gửi thông báo cập nhật trailing stop cho {symbol} tới Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo trailing stop: {str(e)}")
        
        return result
    
    def run_once(self, force_setup: bool = False) -> bool:
        """
        Chạy một lần kiểm tra và cập nhật SL/TP
        
        Args:
            force_setup (bool): Buộc thiết lập lại SL/TP
            
        Returns:
            bool: True nếu hoàn thành
        """
        # Gọi hàm cha để cập nhật SL/TP
        result = super().run_once(force_setup)
        
        # Tính toán số lượng vị thế và gửi cập nhật định kỳ
        try:
            now = time.time()
            last_position_update = getattr(self, 'last_position_update', 0)
            position_update_interval = 3600  # 1 giờ
            
            if now - last_position_update > position_update_interval and self.active_positions:
                # Lấy thông tin số dư và vị thế
                try:
                    # Lấy thông tin tài khoản
                    balance = 0
                    try:
                        # Thử lấy thông tin số dư từ API
                        balance_data = self.api.futures_account_balance()
                        for asset in balance_data:
                            if asset.get('asset') == 'USDT':
                                balance = float(asset.get('balance', 0))
                                break
                    except Exception as bal_error:
                        logger.error(f"Lỗi khi lấy số dư tài khoản: {str(bal_error)}")
                        # Thử cách khác nếu phương thức trên lỗi
                        try:
                            position_info = self.api.get_futures_position_risk()
                            balance = float(position_info[0].get('walletBalance', 0)) if position_info else 0
                        except Exception as pos_error:
                            logger.error(f"Không thể lấy số dư sau khi thử phương thức thay thế: {str(pos_error)}")
                    
                    # Tính toán tổng unrealized PnL từ các vị thế
                    unrealized_pnl = 0
                    for position in self.active_positions.values():
                        pos_pnl = float(position.get('unrealizedProfit', 0))
                        unrealized_pnl += pos_pnl
                    
                    # Gửi thông báo
                    self.notifier.notify_position_update(
                        positions=list(self.active_positions.values()),
                        account_balance=balance,
                        unrealized_pnl=unrealized_pnl
                    )
                except Exception as inner_e:
                    logger.error(f"Lỗi khi lấy thông tin tài khoản: {str(inner_e)}")
                    # Nếu không thể lấy thông tin tài khoản, vẫn gửi cập nhật vị thế
                    self.notifier.notify_position_update(
                        positions=list(self.active_positions.values()),
                        account_balance=0,
                        unrealized_pnl=0
                    )
                
                self.last_position_update = now
                logger.info(f"Đã gửi cập nhật vị thế định kỳ tới Telegram")
        except Exception as e:
            logger.error(f"Lỗi khi gửi cập nhật vị thế: {str(e)}")
        
        return result

def main():
    """Hàm chính"""
    import argparse
    import atexit
    import signal
    
    # Đường dẫn đến PID file
    pid_file = "sltp_telegram_integration.pid"
    
    # Hàm xử lý khi thoát
    def cleanup_pid_file():
        """Xóa file PID khi thoát"""
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
                logger.info(f"Đã xóa PID file: {pid_file}")
        except Exception as e:
            logger.error(f"Lỗi khi xóa PID file: {str(e)}")
    
    # Hàm xử lý khi nhận tín hiệu dừng
    def signal_handler(signum, frame):
        """Xử lý khi nhận tín hiệu dừng"""
        signal_name = signal.Signals(signum).name
        logger.info(f"Đã nhận tín hiệu {signal_name}, đang dừng tiến trình...")
        cleanup_pid_file()
        sys.exit(0)
    
    # Đăng ký hàm xử lý cho các tín hiệu
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Đăng ký hàm cleanup khi thoát
    atexit.register(cleanup_pid_file)
    
    # Ghi PID vào file
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"Đã ghi PID {os.getpid()} vào file {pid_file}")
    except Exception as e:
        logger.error(f"Lỗi khi ghi PID file: {str(e)}")
    
    # Phân tích tham số dòng lệnh
    parser = argparse.ArgumentParser(description='Enhanced Auto SL/TP Manager with Telegram Integration')
    parser.add_argument('--interval', type=int, default=60, help='Thời gian giữa các lần kiểm tra (giây)')
    parser.add_argument('--force', action='store_true', help='Buộc thiết lập lại SL/TP')
    parser.add_argument('--once', action='store_true', help='Chỉ chạy một lần')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng Binance Testnet')
    args = parser.parse_args()
    
    # Khởi tạo enhanced manager
    manager = EnhancedAutoSLTPManager(testnet=args.testnet)
    
    # Cập nhật tiêu đề tiến trình để dễ theo dõi (bỏ qua chức năng không cần thiết)
    # try:
    #     import setproctitle
    #     setproctitle.setproctitle("sltp_telegram_integration")
    # except ImportError:
    #     pass
    # Cập nhật trạng thái
    try:
        # Thử import setproctitle nếu có
        try:
            import setproctitle
            setproctitle.setproctitle("sltp_telegram_integration")
            logger.info("Đã cập nhật tên tiến trình thành 'sltp_telegram_integration'")
        except ImportError:
            logger.info("Không thể cập nhật tên tiến trình, bỏ qua")
    except Exception as e:
        logger.warning(f"Lỗi khi thiết lập tên tiến trình: {str(e)}")
    
    # Khởi tạo quản lý
    try:
        # Khởi tạo manager
        manager = EnhancedAutoSLTPManager(testnet=args.testnet)
        logger.info(f"Đã khởi tạo EnhancedAutoSLTPManager thành công, chế độ testnet={args.testnet}")
    except Exception as e:
        logger.critical(f"Không thể khởi tạo EnhancedAutoSLTPManager: {str(e)}")
        logger.critical(f"Chi tiết: {traceback.format_exc()}")
        sys.exit(1)
    
    # Không thoát ra dù gặp lỗi
    retry_count = 0
    max_retry_count = 10
    wait_time = 60
    
    while True:
        try:
            # Chạy
            if args.once:
                logger.info("Chạy một lần chế độ đơn lẻ")
                manager.run_once(force_setup=args.force)
                break  # Thoát vòng lặp nếu chế độ once
            else:
                logger.info(f"Chạy liên tục với interval={args.interval}s")
                manager.run(interval=args.interval, force_setup=args.force)
                # Không nên chạy tới đây vì hàm run() có vòng lặp vô hạn
                logger.warning("Hàm run() đã trả về dù có vòng lặp vô hạn, đây là bất thường. Khởi động lại...")
                
        except KeyboardInterrupt:
            logger.info("Đã nhận tín hiệu dừng từ bàn phím")
            break
            
        except Exception as e:
            retry_count += 1
            logger.critical(f"Lỗi nghiêm trọng trong tiến trình SL/TP Telegram lần thứ {retry_count}: {str(e)}")
            logger.critical(f"Chi tiết lỗi: {traceback.format_exc()}")
            
            if retry_count >= max_retry_count:
                logger.critical(f"Đã thử khởi động lại {retry_count} lần không thành công, đợi thời gian dài hơn")
                wait_time = 300  # Tăng thời gian chờ lên 5 phút
                retry_count = 0  # Reset lại đếm
            
            logger.info(f"Đợi {wait_time} giây trước khi thử khởi động lại...")
            time.sleep(wait_time)
            
            # Khởi tạo lại manager để tránh lỗi trạng thái
            try:
                del manager
                manager = EnhancedAutoSLTPManager(testnet=args.testnet)
                logger.info("Đã khởi tạo lại EnhancedAutoSLTPManager thành công")
            except Exception as init_error:
                logger.error(f"Không thể khởi tạo lại manager: {str(init_error)}")
    
    # Chỉ tới đây nếu đã nhận KeyboardInterrupt hoặc chế độ run_once
    logger.info("Tiến trình SL/TP Telegram kết thúc")

if __name__ == "__main__":
    main()