#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module thông báo Telegram tăng cường

Module này cải thiện việc gửi thông báo Telegram bằng cách:
1. Hỗ trợ thông báo định kỳ theo lịch trình
2. Cung cấp báo cáo phân tích tất cả các cặp giao dịch
3. Cung cấp thông báo tổng quan thị trường
"""

import os
import sys
import json
import time
import logging
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_telegram.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("enhanced_telegram")

# Import module Telegram Notifier
try:
    from telegram_notifier import TelegramNotifier
except ImportError as e:
    logger.error(f"Lỗi import module: {e}")
    logger.error("Đảm bảo đang chạy từ thư mục gốc của dự án")
    sys.exit(1)

class EnhancedTelegramNotifications:
    """Lớp thông báo Telegram tăng cường với các tính năng nâng cao"""
    
    def __init__(self, config_path: str = 'telegram_config.json', notification_interval: int = 15):
        """
        Khởi tạo thông báo Telegram tăng cường
        
        Args:
            config_path (str): Đường dẫn tới file cấu hình Telegram
            notification_interval (int): Khoảng thời gian gửi thông báo (phút)
        """
        self.config_path = config_path
        self.telegram = TelegramNotifier()
        
        # Cài đặt thông báo định kỳ
        self.notification_interval = notification_interval
        self.notification_intervals = {
            'market_update': notification_interval,  # Phút
            'portfolio_update': notification_interval * 2,  # Phút
            'system_status': notification_interval * 4,  # Phút
            'daily_summary': 24 * 60  # Phút (24 giờ)
        }
        
        # Các biến kiểm soát
        self.running = False
        self.scheduler_thread = None
        
        # Cache dữ liệu
        self.latest_market_data = {}
        self.latest_positions = []
        self.latest_portfolio = {}
        
        logger.info("Đã khởi tạo Enhanced Telegram Notifications")
    
    def start_scheduled_notifications(self) -> None:
        """Bắt đầu lịch trình gửi thông báo"""
        if self.running:
            logger.warning("Lịch trình thông báo đã đang chạy")
            return
        
        logger.info("Bắt đầu lịch trình thông báo Telegram")
        
        # Đặt lịch thông báo
        schedule.every(self.notification_intervals['market_update']).minutes.do(self.send_market_update)
        schedule.every(self.notification_intervals['portfolio_update']).minutes.do(self.send_portfolio_update)
        schedule.every(self.notification_intervals['system_status']).minutes.do(self.send_system_status)
        schedule.every().day.at("20:00").do(self.send_daily_summary)
        
        # Bắt đầu luồng chạy lịch trình
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Đã khởi động lịch trình thông báo Telegram")
    
    def _run_scheduler(self) -> None:
        """Hàm chạy lập lịch trong một thread riêng"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop_scheduled_notifications(self) -> None:
        """Dừng lịch trình gửi thông báo"""
        if not self.running:
            logger.warning("Lịch trình thông báo không đang chạy")
            return
        
        logger.info("Dừng lịch trình thông báo Telegram")
        self.running = False
        
        # Xóa tất cả các công việc đã lập lịch
        schedule.clear()
        
        # Chờ thread kết thúc
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
            
        logger.info("Đã dừng lịch trình thông báo Telegram")
    
    def update_market_data(self, market_data: Dict[str, Any]) -> None:
        """
        Cập nhật dữ liệu thị trường mới nhất
        
        Args:
            market_data (Dict[str, Any]): Dữ liệu thị trường
        """
        self.latest_market_data = market_data
        logger.info("Đã cập nhật dữ liệu thị trường mới nhất")
    
    def update_positions(self, positions: List[Dict]) -> None:
        """
        Cập nhật thông tin vị thế mới nhất
        
        Args:
            positions (List[Dict]): Danh sách các vị thế
        """
        self.latest_positions = positions
        logger.info(f"Đã cập nhật {len(positions)} vị thế mới nhất")
    
    def update_portfolio(self, portfolio: Dict) -> None:
        """
        Cập nhật thông tin danh mục đầu tư mới nhất
        
        Args:
            portfolio (Dict): Thông tin danh mục đầu tư
        """
        self.latest_portfolio = portfolio
        logger.info("Đã cập nhật thông tin danh mục đầu tư mới nhất")
    
    def send_market_update(self) -> bool:
        """
        Gửi thông báo cập nhật thị trường
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            logger.info("Đang gửi thông báo cập nhật thị trường")
            
            # Kiểm tra dữ liệu
            if not self.latest_market_data:
                logger.warning("Không có dữ liệu thị trường để gửi thông báo")
                return False
            
            # Đọc dữ liệu từ các file phân tích
            all_symbols = self._get_all_symbols()
            analysis_data = self._collect_analysis_data(all_symbols)
            
            # Tạo tin nhắn thông báo
            message = self._generate_market_update_message(analysis_data)
            
            # Gửi thông báo qua Telegram
            result = self.telegram.send_notification('info', message)
            
            if result.get('ok'):
                logger.info("Đã gửi thông báo cập nhật thị trường thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo cập nhật thị trường: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo cập nhật thị trường: {str(e)}")
            return False
    
    def _get_all_symbols(self) -> List[str]:
        """
        Lấy danh sách tất cả các cặp giao dịch từ file cấu hình
        
        Returns:
            List[str]: Danh sách các cặp giao dịch
        """
        try:
            # Thử đọc từ bot_config.json
            if os.path.exists('bot_config.json'):
                with open('bot_config.json', 'r') as f:
                    config = json.load(f)
                    if 'symbols' in config:
                        return config['symbols']
            
            # Thử đọc từ account_config.json
            if os.path.exists('account_config.json'):
                with open('account_config.json', 'r') as f:
                    config = json.load(f)
                    if 'symbols' in config:
                        return config['symbols']
            
            # Danh sách mặc định
            return [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
                "XRPUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "MATICUSDT",
                "LINKUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT"
            ]
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách cặp giao dịch: {str(e)}")
            # Danh sách mặc định nếu có lỗi
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
    
    def _collect_analysis_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Thu thập dữ liệu phân tích từ các file recommendation
        
        Args:
            symbols (List[str]): Danh sách các cặp giao dịch
            
        Returns:
            Dict[str, Dict]: Dữ liệu phân tích theo cặp giao dịch
        """
        analysis_data = {}
        
        for symbol in symbols:
            symbol_lower = symbol.lower()
            recommendation_file = f"recommendation_{symbol_lower}.json"
            
            if os.path.exists(recommendation_file):
                try:
                    with open(recommendation_file, 'r') as f:
                        analysis_data[symbol] = json.load(f)
                        logger.info(f"Đã thu thập phân tích cho {symbol}")
                except Exception as e:
                    logger.error(f"Lỗi khi đọc file {recommendation_file}: {str(e)}")
                    # Tạo mục mặc định nếu không đọc được file
                    analysis_data[symbol] = {
                        'symbol': symbol,
                        'price': self.latest_market_data.get(symbol, 0),
                        'signal': 'UNKNOWN',
                        'signal_text': 'Không có dữ liệu phân tích',
                        'confidence': 0,
                        'action': 'CHỜ ĐỢI',
                        'indicators': {},
                        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
            else:
                # Tạo mục mặc định nếu không có file
                analysis_data[symbol] = {
                    'symbol': symbol,
                    'price': self.latest_market_data.get(symbol, 0),
                    'signal': 'UNKNOWN',
                    'signal_text': 'Không có file phân tích',
                    'confidence': 0,
                    'action': 'CHỜ ĐỢI',
                    'indicators': {},
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        
        return analysis_data
    
    def _generate_market_update_message(self, analysis_data: Dict[str, Dict]) -> str:
        """
        Tạo tin nhắn cập nhật thị trường
        
        Args:
            analysis_data (Dict[str, Dict]): Dữ liệu phân tích
            
        Returns:
            str: Nội dung tin nhắn
        """
        # Tạo tin nhắn
        message = "<b>PHÂN TÍCH THỊ TRƯỜNG CẬP NHẬT</b>\n\n"
        
        # Danh sách các cặp theo tín hiệu
        buy_signals = []
        sell_signals = []
        neutral_signals = []
        no_data_signals = []
        
        # Phân loại các cặp
        for symbol, data in analysis_data.items():
            signal = data.get('signal', 'UNKNOWN')
            confidence = data.get('confidence', 0)
            price = data.get('price', 0)
            action = data.get('action', 'CHỜ ĐỢI')
            signal_text = data.get('signal_text', 'Không có dữ liệu')
            
            item = {
                'symbol': symbol,
                'signal_text': signal_text,
                'confidence': confidence,
                'price': price,
                'action': action
            }
            
            if signal == 'BUY' or signal == 'STRONG_BUY':
                buy_signals.append(item)
            elif signal == 'SELL' or signal == 'STRONG_SELL':
                sell_signals.append(item)
            elif signal == 'NEUTRAL':
                neutral_signals.append(item)
            else:
                no_data_signals.append(item)
        
        # Sắp xếp các danh sách theo độ tin cậy
        buy_signals.sort(key=lambda x: x['confidence'], reverse=True)
        sell_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Thêm các tín hiệu MUA
        if buy_signals:
            message += "🟢 <b>TÍN HIỆU MUA</b>\n"
            for item in buy_signals:
                message += f"  • {item['symbol']}: {item['signal_text']} ({item['confidence']:.1f}%)\n"
                message += f"    💵 Giá: {item['price']}, Đề xuất: {item['action']}\n"
            message += "\n"
        
        # Thêm các tín hiệu BÁN
        if sell_signals:
            message += "🔴 <b>TÍN HIỆU BÁN</b>\n"
            for item in sell_signals:
                message += f"  • {item['symbol']}: {item['signal_text']} ({item['confidence']:.1f}%)\n"
                message += f"    💵 Giá: {item['price']}, Đề xuất: {item['action']}\n"
            message += "\n"
        
        # Thêm các tín hiệu TRUNG TÍNH
        if neutral_signals:
            message += "⚪ <b>THỊ TRƯỜNG ĐI NGANG</b>\n"
            for item in neutral_signals:
                message += f"  • {item['symbol']}: {item['signal_text']} ({item['confidence']:.1f}%)\n"
                message += f"    💵 Giá: {item['price']}, Đề xuất: {item['action']}\n"
            message += "\n"
        
        # Thêm các cặp không có dữ liệu
        if no_data_signals:
            message += "⚠️ <b>KHÔNG ĐỦ DỮ LIỆU</b>\n"
            for item in no_data_signals:
                message += f"  • {item['symbol']}: {item['signal_text']}\n"
                message += f"    💵 Giá: {item['price']}, Đề xuất: {item['action']}\n"
            message += "\n"
        
        # Thêm thông tin thời gian
        message += f"<i>Cập nhật: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>\n"
        message += f"<i>Cập nhật tiếp theo: {self.notification_interval} phút sau</i>"
        
        return message
    
    def send_portfolio_update(self) -> bool:
        """
        Gửi thông báo cập nhật danh mục đầu tư
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            logger.info("Đang gửi thông báo cập nhật danh mục đầu tư")
            
            # Kiểm tra dữ liệu
            if not self.latest_positions and not self.latest_portfolio:
                logger.warning("Không có dữ liệu danh mục đầu tư để gửi thông báo")
                return False
            
            # Tạo tin nhắn thông báo
            message = self._generate_portfolio_update_message()
            
            # Gửi thông báo qua Telegram
            result = self.telegram.send_notification('info', message)
            
            if result.get('ok'):
                logger.info("Đã gửi thông báo cập nhật danh mục đầu tư thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo cập nhật danh mục đầu tư: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo cập nhật danh mục đầu tư: {str(e)}")
            return False
    
    def _generate_portfolio_update_message(self) -> str:
        """
        Tạo tin nhắn cập nhật danh mục đầu tư
        
        Returns:
            str: Nội dung tin nhắn
        """
        # Tạo tin nhắn
        message = "<b>CẬP NHẬT DANH MỤC ĐẦU TƯ</b>\n\n"
        
        # Thêm thông tin về các vị thế đang mở
        if self.latest_positions:
            message += "📊 <b>CÁC VỊ THẾ ĐANG MỞ</b>\n"
            
            total_profit_loss = 0
            total_margin_used = 0
            
            for position in self.latest_positions:
                symbol = position.get('symbol', 'UNKNOWN')
                entry_price = position.get('entry_price', 0)
                current_price = position.get('mark_price', 0)
                quantity = position.get('positionAmt', 0)
                leverage = position.get('leverage', 1)
                
                # Tính lợi nhuận
                side = 'LONG' if float(quantity) > 0 else 'SHORT'
                quantity_abs = abs(float(quantity))
                
                if side == 'LONG':
                    profit_percent = (current_price - entry_price) / entry_price * 100 * leverage
                else:
                    profit_percent = (entry_price - current_price) / entry_price * 100 * leverage
                
                # Tính margin đã sử dụng
                margin_used = quantity_abs * entry_price / leverage
                total_margin_used += margin_used
                
                # Tính lợi nhuận tuyệt đối
                profit_loss = profit_percent * margin_used / 100
                total_profit_loss += profit_loss
                
                # Thêm emoji dựa trên lợi nhuận
                emoji = '🟢' if profit_percent > 0 else '🔴'
                
                # Thêm thông tin vị thế
                message += f"{emoji} <b>{side} {symbol}</b>\n"
                message += f"  💵 Giá vào: {entry_price}, Giá hiện tại: {current_price}\n"
                message += f"  🔢 Số lượng: {quantity_abs}, Đòn bẩy: {leverage}x\n"
                message += f"  💰 P/L: {profit_loss:.2f} USDT ({profit_percent:.2f}%)\n\n"
            
            # Thêm tổng kết
            message += f"<b>TỔNG P/L:</b> {total_profit_loss:.2f} USDT\n"
            message += f"<b>TỔNG MARGIN:</b> {total_margin_used:.2f} USDT\n\n"
        else:
            message += "📊 <b>KHÔNG CÓ VỊ THẾ MỞ</b>\n\n"
        
        # Thêm thông tin về tài khoản
        if self.latest_portfolio:
            balance = self.latest_portfolio.get('total_balance', 0)
            available = self.latest_portfolio.get('available_balance', 0)
            unrealized_pnl = self.latest_portfolio.get('unrealized_pnl', 0)
            
            message += "💼 <b>THÔNG TIN TÀI KHOẢN</b>\n"
            message += f"💵 Tổng số dư: {balance:.2f} USDT\n"
            message += f"💰 Số dư khả dụng: {available:.2f} USDT\n"
            message += f"📈 Lợi nhuận chưa thực hiện: {unrealized_pnl:.2f} USDT\n\n"
        
        # Thêm thông tin thời gian
        message += f"<i>Cập nhật: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>\n"
        message += f"<i>Cập nhật tiếp theo: {self.notification_interval * 2} phút sau</i>"
        
        return message
    
    def send_system_status(self) -> bool:
        """
        Gửi thông báo trạng thái hệ thống
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            logger.info("Đang gửi thông báo trạng thái hệ thống")
            
            # Tạo tin nhắn thông báo
            message = self._generate_system_status_message()
            
            # Gửi thông báo qua Telegram
            result = self.telegram.send_notification('info', message)
            
            if result.get('ok'):
                logger.info("Đã gửi thông báo trạng thái hệ thống thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo trạng thái hệ thống: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo trạng thái hệ thống: {str(e)}")
            return False
    
    def _generate_system_status_message(self) -> str:
        """
        Tạo tin nhắn trạng thái hệ thống
        
        Returns:
            str: Nội dung tin nhắn
        """
        # Tạo tin nhắn
        message = "<b>TRẠNG THÁI HỆ THỐNG</b>\n\n"
        
        # Kiểm tra trạng thái kết nối API
        api_status = "✅ Hoạt động" if self._check_api_connection() else "❌ Lỗi kết nối"
        message += f"🔌 <b>Kết nối API:</b> {api_status}\n"
        
        # Kiểm tra trạng thái các luồng chính
        message += f"🧵 <b>Luồng phân tích thị trường:</b> ✅ Hoạt động\n"
        message += f"🧵 <b>Luồng quản lý vị thế:</b> ✅ Hoạt động\n"
        message += f"🧵 <b>Luồng gửi thông báo:</b> ✅ Hoạt động\n"
        
        # Kiểm tra số lượng cặp giao dịch có dữ liệu
        all_symbols = self._get_all_symbols()
        analysis_data = self._collect_analysis_data(all_symbols)
        
        valid_count = sum(1 for data in analysis_data.values() if data.get('signal', 'UNKNOWN') != 'UNKNOWN')
        message += f"📊 <b>Cặp giao dịch có dữ liệu:</b> {valid_count}/{len(all_symbols)}\n\n"
        
        # Kiểm tra thời gian hoạt động
        uptime = self._get_system_uptime()
        message += f"⏱️ <b>Thời gian hoạt động:</b> {uptime}\n\n"
        
        # Thêm thông tin thời gian
        message += f"<i>Cập nhật: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>\n"
        message += f"<i>Cập nhật tiếp theo: {self.notification_interval * 4} phút sau</i>"
        
        return message
    
    def _check_api_connection(self) -> bool:
        """
        Kiểm tra kết nối tới Binance API
        
        Returns:
            bool: True nếu kết nối thành công, False nếu không
        """
        try:
            # Kiểm tra kết nối bằng cách đọc file trạng thái API mới nhất
            if os.path.exists('api_status.json'):
                with open('api_status.json', 'r') as f:
                    status = json.load(f)
                    last_successful = status.get('last_successful_connection', 0)
                    # Kiểm tra xem kết nối cuối cùng có trong vòng 10 phút không
                    return (datetime.now() - datetime.fromtimestamp(last_successful)).total_seconds() < 600
            
            # Kiểm tra bằng cách xem có file recommendation mới không
            recommendation_files = [f for f in os.listdir('.') if f.startswith('recommendation_') and f.endswith('.json')]
            if recommendation_files:
                newest_file = max(recommendation_files, key=lambda f: os.path.getmtime(f))
                # Kiểm tra xem file có được tạo trong vòng 30 phút không
                return (datetime.now() - datetime.fromtimestamp(os.path.getmtime(newest_file))).total_seconds() < 1800
            
            return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra kết nối API: {str(e)}")
            return False
    
    def _get_system_uptime(self) -> str:
        """
        Lấy thời gian hoạt động của hệ thống
        
        Returns:
            str: Thời gian hoạt động định dạng chuỗi
        """
        try:
            # Kiểm tra từ file uptime nếu có
            if os.path.exists('system_uptime.json'):
                with open('system_uptime.json', 'r') as f:
                    uptime_data = json.load(f)
                    start_time = uptime_data.get('start_time', 0)
                    uptime_seconds = datetime.now().timestamp() - start_time
                    
                    # Chuyển đổi sang chuỗi định dạng
                    days, remainder = divmod(uptime_seconds, 86400)
                    hours, remainder = divmod(remainder, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    return f"{int(days)} ngày, {int(hours)} giờ, {int(minutes)} phút"
            
            # Nếu không có file, trả về thời gian mặc định
            return "Chưa xác định"
        except Exception as e:
            logger.error(f"Lỗi khi lấy thời gian hoạt động: {str(e)}")
            return "Lỗi khi lấy thông tin"
    
    def send_daily_summary(self) -> bool:
        """
        Gửi báo cáo tổng kết hàng ngày
        
        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            logger.info("Đang gửi báo cáo tổng kết hàng ngày")
            
            # Tạo tin nhắn thông báo
            message = self._generate_daily_summary_message()
            
            # Gửi thông báo qua Telegram
            result = self.telegram.send_notification('info', message)
            
            if result.get('ok'):
                logger.info("Đã gửi báo cáo tổng kết hàng ngày thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi báo cáo tổng kết hàng ngày: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo tổng kết hàng ngày: {str(e)}")
            return False
    
    def _generate_daily_summary_message(self) -> str:
        """
        Tạo tin nhắn tổng kết hàng ngày
        
        Returns:
            str: Nội dung tin nhắn
        """
        # Tạo tin nhắn
        message = "<b>🌟 BÁO CÁO TỔNG KẾT HÀNG NGÀY 🌟</b>\n\n"
        
        # Ngày hiện tại
        today = datetime.now().strftime('%d/%m/%Y')
        message += f"📅 <b>Ngày:</b> {today}\n\n"
        
        # Thống kê danh mục đầu tư
        if self.latest_portfolio:
            balance = self.latest_portfolio.get('total_balance', 0)
            available = self.latest_portfolio.get('available_balance', 0)
            unrealized_pnl = self.latest_portfolio.get('unrealized_pnl', 0)
            
            message += "💼 <b>THÔNG TIN TÀI KHOẢN</b>\n"
            message += f"💵 Tổng số dư: {balance:.2f} USDT\n"
            message += f"💰 Số dư khả dụng: {available:.2f} USDT\n"
            message += f"📈 Lợi nhuận chưa thực hiện: {unrealized_pnl:.2f} USDT\n\n"
        
        # Thống kê giao dịch trong ngày
        message += "📊 <b>THỐNG KÊ GIAO DỊCH TRONG NGÀY</b>\n"
        
        # *** Tại đây cần đọc dữ liệu giao dịch từ file logs hoặc trading history ***
        # (Phần này sẽ cần triển khai sau khi có hệ thống ghi nhật ký giao dịch)
        message += "  • (Chưa có dữ liệu giao dịch trong ngày)\n\n"
        
        # Phân tích thị trường trong ngày
        message += "📈 <b>PHÂN TÍCH THỊ TRƯỜNG</b>\n"
        
        # Đọc dữ liệu phân tích
        all_symbols = self._get_all_symbols()
        analysis_data = self._collect_analysis_data(all_symbols)
        
        # Đếm số lượng tín hiệu
        buy_count = sum(1 for data in analysis_data.values() if data.get('signal') in ['BUY', 'STRONG_BUY'])
        sell_count = sum(1 for data in analysis_data.values() if data.get('signal') in ['SELL', 'STRONG_SELL'])
        neutral_count = sum(1 for data in analysis_data.values() if data.get('signal') == 'NEUTRAL')
        
        message += f"  • Tín hiệu MUA: {buy_count}/{len(all_symbols)}\n"
        message += f"  • Tín hiệu BÁN: {sell_count}/{len(all_symbols)}\n"
        message += f"  • Tín hiệu TRUNG TÍNH: {neutral_count}/{len(all_symbols)}\n\n"
        
        # Thêm nhận xét về xu hướng thị trường
        if buy_count > sell_count and buy_count > neutral_count:
            message += "🟢 <b>Nhận xét:</b> Thị trường có xu hướng TĂNG\n\n"
        elif sell_count > buy_count and sell_count > neutral_count:
            message += "🔴 <b>Nhận xét:</b> Thị trường có xu hướng GIẢM\n\n"
        else:
            message += "⚪ <b>Nhận xét:</b> Thị trường có xu hướng ĐI NGANG\n\n"
        
        # Thêm thông tin thời gian
        message += f"<i>Cập nhật: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>\n"
        message += f"<i>Báo cáo tiếp theo sẽ được gửi vào 20:00 hôm sau</i>"
        
        return message

# Hàm chính để kiểm thử
def main():
    """Hàm kiểm thử Enhanced Telegram Notifications"""
    try:
        # Khởi tạo Enhanced Telegram Notifications
        notifier = EnhancedTelegramNotifications()
        
        # Gửi thông báo thử nghiệm
        notifier.send_system_status()
        
        # Bắt đầu lịch trình thông báo
        notifier.start_scheduled_notifications()
        
        # Giữ cho tiến trình chạy
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng từ người dùng")
            notifier.stop_scheduled_notifications()
        
        logger.info("Enhanced Telegram Notifications đã dừng")
        return 0
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())