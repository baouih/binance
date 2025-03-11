#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Telegram Notifications
------------------------------
Module này cung cấp các tính năng thông báo nâng cao qua Telegram
với hỗ trợ cho các loại thông báo khác nhau về thị trường tiền điện tử
"""

import os
import json
import time
import logging
import threading
import schedule
from typing import Dict, List, Union, Optional, Any
from datetime import datetime, timedelta

from telegram_notifier import TelegramNotifier

# Thiết lập logging
logger = logging.getLogger("enhanced_telegram_notifications")

class EnhancedTelegramNotifications:
    """
    Cung cấp thông báo Telegram nâng cao cho hệ thống giao dịch tiền điện tử
    Hỗ trợ các loại thông báo:
    - Cập nhật thị trường định kỳ
    - Cảnh báo tín hiệu kỹ thuật
    - Phân tích thị trường
    - Thông báo giao dịch chi tiết
    """
    
    def __init__(self, config_path: str = None, notification_interval: int = 60):
        """
        Khởi tạo Enhanced Telegram Notifications
        
        Args:
            config_path: Đường dẫn đến file cấu hình (nếu None, sử dụng mặc định)
            notification_interval: Khoảng thời gian giữa các thông báo (phút)
        """
        self.config_path = config_path
        self.notification_interval = notification_interval
        self.telegram = TelegramNotifier()
        self.scheduled_task = None
        self.running = False
        self.config = self._load_config()
        
        # Thư mục lưu kết quả phân tích
        self.market_analysis_file = "market_analysis.json"
        self.recommendations_file = "all_recommendations.json"
        
        # Thông tin thông báo cuối cùng
        self.last_notification_time = {
            "market_update": None,
            "signal_alert": {},
            "trade_notification": {}
        }
        
        # Thiết lập cấu hình từ file
        self.update_from_config()
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình đã tải
        """
        config = {
            "enabled": True,
            "notification_interval": self.notification_interval,
            "min_signal_confidence": 70,
            "only_significant_changes": True,
            "signal_cooldown": 240,  # Phút
            "include_charts": True,
            "telegram_enabled": True,
            "notification_types": {
                "market_updates": True,
                "signal_alerts": True,
                "trade_notifications": True,
                "performance_reports": True
            },
            "quiet_hours": {
                "enabled": False,
                "start_hour": 0,
                "end_hour": 7
            }
        }
        
        # Đọc cấu hình từ file
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Cập nhật cấu hình từ file
                for key, value in loaded_config.items():
                    if key in config:
                        config[key] = value
                
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {e}")
        
        return config
    
    def update_from_config(self):
        """Cập nhật thông số từ cấu hình"""
        self.enabled = self.config.get("enabled", True)
        self.notification_interval = self.config.get("notification_interval", 60)
        self.telegram.enabled = self.config.get("telegram_enabled", True) and self.telegram.enabled
    
    def start_scheduled_notifications(self):
        """Bắt đầu lịch trình thông báo"""
        if not self.running:
            self.running = True
            
            # Thiết lập lịch trình thông báo thị trường
            minutes = self.notification_interval
            logger.info(f"Thiết lập thông báo thị trường mỗi {minutes} phút")
            
            # Sử dụng schedule
            schedule.every(minutes).minutes.do(self.send_market_update)
            
            # Bắt đầu thread để chạy lịch trình
            self.scheduled_task = threading.Thread(target=self._run_schedule, daemon=True)
            self.scheduled_task.start()
            
            logger.info("Đã bắt đầu lịch trình thông báo")
            return True
        
        logger.warning("Lịch trình thông báo đã được bắt đầu trước đó")
        return False
    
    def _run_schedule(self):
        """Hàm chạy lịch trình trong thread riêng"""
        logger.info("Thread lịch trình thông báo đã bắt đầu")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except Exception as e:
            logger.error(f"Lỗi trong thread lịch trình thông báo: {e}")
        
        logger.info("Thread lịch trình thông báo đã kết thúc")
    
    def stop_scheduled_notifications(self):
        """Dừng lịch trình thông báo"""
        if self.running:
            self.running = False
            
            # Xóa tất cả các lịch trình
            schedule.clear()
            
            # Chờ thread kết thúc nếu còn chạy
            if self.scheduled_task and self.scheduled_task.is_alive():
                self.scheduled_task.join(timeout=5)
            
            logger.info("Đã dừng lịch trình thông báo")
            return True
        
        logger.warning("Lịch trình thông báo chưa được bắt đầu")
        return False
    
    def _is_quiet_hours(self) -> bool:
        """
        Kiểm tra xem có đang trong giờ yên tĩnh không
        
        Returns:
            bool: True nếu đang trong giờ yên tĩnh, False nếu không
        """
        quiet_hours = self.config.get("quiet_hours", {})
        enabled = quiet_hours.get("enabled", False)
        
        if not enabled:
            return False
        
        start_hour = quiet_hours.get("start_hour", 0)
        end_hour = quiet_hours.get("end_hour", 7)
        
        current_hour = datetime.now().hour
        
        if start_hour <= end_hour:
            return start_hour <= current_hour < end_hour
        else:  # Qua nửa đêm
            return current_hour >= start_hour or current_hour < end_hour
    
    def _can_send_notification(self, notification_type: str, key: str = None) -> bool:
        """
        Kiểm tra xem có thể gửi thông báo hay không
        
        Args:
            notification_type: Loại thông báo
            key: Khóa phụ cho loại thông báo
            
        Returns:
            bool: True nếu có thể gửi, False nếu không
        """
        if not self.enabled or not self.telegram.enabled:
            return False
        
        # Kiểm tra giờ yên tĩnh
        if self._is_quiet_hours():
            logger.info("Đang trong giờ yên tĩnh, không gửi thông báo")
            return False
        
        # Kiểm tra cấu hình cho loại thông báo
        notification_types = self.config.get("notification_types", {})
        if not notification_types.get(notification_type, True):
            logger.info(f"Loại thông báo {notification_type} bị tắt trong cấu hình")
            return False
        
        # Kiểm tra thời gian cooldown
        last_time = None
        cooldown = 0
        
        if notification_type == "market_updates":
            last_time = self.last_notification_time["market_update"]
            cooldown = self.notification_interval
        elif notification_type == "signal_alerts" and key:
            last_time = self.last_notification_time["signal_alert"].get(key)
            cooldown = self.config.get("signal_cooldown", 240)
        elif notification_type == "trade_notifications" and key:
            last_time = self.last_notification_time["trade_notification"].get(key)
            cooldown = 60  # 1 giờ cooldown cho thông báo giao dịch
        
        if last_time:
            time_diff = (datetime.now() - last_time).total_seconds() / 60  # Phút
            if time_diff < cooldown:
                logger.info(f"Thông báo {notification_type} cho {key} vẫn trong thời gian cooldown ({cooldown - time_diff:.1f} phút còn lại)")
                return False
        
        return True
    
    def send_market_update(self) -> bool:
        """
        Gửi cập nhật thị trường
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self._can_send_notification("market_updates"):
            return False
        
        try:
            # Tìm file phân tích thị trường
            if not os.path.exists(self.market_analysis_file):
                logger.warning(f"Không tìm thấy file phân tích thị trường: {self.market_analysis_file}")
                return False
            
            # Đọc dữ liệu phân tích
            with open(self.market_analysis_file, 'r') as f:
                market_analysis = json.load(f)
            
            # Kiểm tra xem có đề xuất không
            recommendations = []
            if os.path.exists(self.recommendations_file):
                try:
                    with open(self.recommendations_file, 'r') as f:
                        recommendations_data = json.load(f)
                        recommendations = recommendations_data.get("recommendations", [])
                except:
                    pass
            
            # Tạo thông báo
            # Nếu phân tích thị trường ở dạng danh sách các cặp tiền
            if isinstance(market_analysis, dict) and "timestamp" in market_analysis:
                # Đây là loại market report
                success = self.telegram.send_market_analysis(market_analysis)
            elif isinstance(market_analysis, dict) and all(isinstance(key, str) and key.endswith("USDT") for key in market_analysis.keys()):
                # Đây là loại phân tích danh sách các cặp tiền
                # Chọn ra top 3 cặp tiền quan trọng
                important_coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
                report_data = {}
                
                for coin in important_coins:
                    if coin in market_analysis:
                        report_data[coin] = market_analysis[coin]
                
                # Tạo thông báo market overview
                overview_message = "<b>📊 TỔNG QUAN THỊ TRƯỜNG</b>\n\n"
                
                # Thêm thông tin BTC
                if "BTCUSDT" in report_data:
                    btc_data = report_data["BTCUSDT"]
                    btc_price = btc_data.get("current_price", 0)
                    btc_signal = btc_data.get("summary", {}).get("overall_signal", "NEUTRAL")
                    
                    signal_emoji = "⚪"
                    if btc_signal in ["STRONG_BUY", "BUY"]:
                        signal_emoji = "🟢"
                    elif btc_signal in ["STRONG_SELL", "SELL"]:
                        signal_emoji = "🔴"
                    
                    overview_message += f"<b>Bitcoin:</b> ${btc_price:,.2f} {signal_emoji}\n"
                
                # Thêm thông tin tín hiệu cho các coin
                overview_message += "\n<b>Tín hiệu giao dịch:</b>\n"
                
                for coin, data in report_data.items():
                    summary = data.get("summary", {})
                    signal = summary.get("overall_signal", "NEUTRAL")
                    confidence = summary.get("confidence", 0)
                    
                    signal_emoji = "⚪"
                    if signal in ["STRONG_BUY", "BUY"]:
                        signal_emoji = "🟢"
                    elif signal in ["STRONG_SELL", "SELL"]:
                        signal_emoji = "🔴"
                    
                    coin_name = coin.replace("USDT", "")
                    overview_message += f"{signal_emoji} {coin_name}: {signal} ({confidence}%)\n"
                
                # Thêm đề xuất giao dịch tốt nhất
                if recommendations:
                    overview_message += "\n<b>Cơ hội giao dịch hàng đầu:</b>\n"
                    
                    top_recommendations = sorted(
                        [r for r in recommendations if r.get("action") != "WATCH"],
                        key=lambda x: x.get("confidence", 0),
                        reverse=True
                    )[:3]  # Top 3
                    
                    for rec in top_recommendations:
                        symbol = rec.get("symbol", "").replace("USDT", "")
                        action = rec.get("action", "")
                        confidence = rec.get("confidence", 0)
                        
                        action_emoji = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "⚪"
                        
                        overview_message += f"{action_emoji} {symbol}: {action} ({confidence}%)\n"
                
                # Thêm thời gian
                overview_message += f"\n⏱ <i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
                
                success = self.telegram.send_notification("info", overview_message)
            else:
                logger.warning("Không thể xác định định dạng dữ liệu phân tích thị trường")
                return False
            
            # Cập nhật thời gian thông báo cuối cùng
            if success:
                self.last_notification_time["market_update"] = datetime.now()
                logger.info("Đã gửi cập nhật thị trường thành công")
            
            return success
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi cập nhật thị trường: {e}")
            return False
    
    def send_signal_alert(self, symbol: str, signal_data: Dict) -> bool:
        """
        Gửi cảnh báo tín hiệu giao dịch
        
        Args:
            symbol: Symbol cần gửi cảnh báo
            signal_data: Dữ liệu tín hiệu
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self._can_send_notification("signal_alerts", symbol):
            return False
        
        # Kiểm tra độ tin cậy tối thiểu
        min_confidence = self.config.get("min_signal_confidence", 70)
        confidence = signal_data.get("confidence", 0)
        
        if confidence < min_confidence:
            logger.info(f"Bỏ qua tín hiệu {symbol} do độ tin cậy quá thấp ({confidence}% < {min_confidence}%)")
            return False
        
        try:
            success = self.telegram.send_signal_alert(signal_data)
            
            # Cập nhật thời gian thông báo cuối cùng
            if success:
                self.last_notification_time["signal_alert"][symbol] = datetime.now()
                logger.info(f"Đã gửi cảnh báo tín hiệu {symbol} thành công")
            
            return success
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi cảnh báo tín hiệu {symbol}: {e}")
            return False
    
    def send_trade_notification(self, trade_data: Dict) -> bool:
        """
        Gửi thông báo giao dịch
        
        Args:
            trade_data: Dữ liệu giao dịch
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        symbol = trade_data.get("symbol", "UNKNOWN")
        
        if not self._can_send_notification("trade_notifications", symbol):
            return False
        
        try:
            success = self.telegram.send_trade_notification(trade_data)
            
            # Cập nhật thời gian thông báo cuối cùng
            if success:
                self.last_notification_time["trade_notification"][symbol] = datetime.now()
                logger.info(f"Đã gửi thông báo giao dịch {symbol} thành công")
            
            return success
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo giao dịch {symbol}: {e}")
            return False
    
    def send_enhanced_market_report(self) -> bool:
        """
        Gửi báo cáo thị trường tăng cường với biểu đồ và phân tích chuyên sâu
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self._can_send_notification("market_updates"):
            return False
        
        try:
            # Tìm báo cáo thị trường nếu có
            market_report_files = [
                "market_report.json",
                "market_analysis_report.json",
                "market_overview.json"
            ]
            
            market_report = None
            for file_path in market_report_files:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            market_report = json.load(f)
                        break
                    except:
                        pass
            
            if not market_report:
                logger.warning("Không tìm thấy báo cáo thị trường để gửi")
                return False
            
            # Tạo thông báo
            message = "<b>📊 BÁO CÁO TĂNG CƯỜNG THỊ TRƯỜNG</b>\n\n"
            
            # Thêm thông tin tổng quan
            if "market_summary" in market_report:
                summary = market_report["market_summary"]
                message += "<b>Tổng quan thị trường:</b>\n"
                message += f"• Trạng thái: {summary.get('status', 'UNKNOWN')}\n"
                message += f"• Chế độ: {summary.get('regime', 'UNKNOWN')}\n"
                message += f"• Biến động: {summary.get('volatility', 'UNKNOWN')}\n"
                message += f"• Giá Bitcoin: ${summary.get('bitcoin_price', 0):,.2f}\n"
                message += f"• Thay đổi BTC: {summary.get('bitcoin_change', 0):+.2f}%\n\n"
            
            # Thêm thông tin các cặp tiền
            if "top_symbols" in market_report:
                message += "<b>Tín hiệu giao dịch chính:</b>\n"
                
                for symbol, data in market_report["top_symbols"].items():
                    coin_name = symbol.replace("USDT", "")
                    signal = data.get('signal', 'NEUTRAL')
                    momentum = data.get('momentum', 'NEUTRAL')
                    
                    signal_emoji = "⚪"
                    if signal in ["STRONG_BUY", "BUY"]:
                        signal_emoji = "🟢"
                    elif signal in ["STRONG_SELL", "SELL"]:
                        signal_emoji = "🔴"
                    
                    message += f"{signal_emoji} {coin_name}: {signal} ({momentum})\n"
                
                message += "\n"
            
            # Thêm cơ hội giao dịch
            if "trading_opportunities" in market_report and market_report["trading_opportunities"]:
                message += "<b>Cơ hội giao dịch hàng đầu:</b>\n"
                
                for opportunity in market_report["trading_opportunities"][:3]:
                    symbol = opportunity.get("symbol", "").replace("USDT", "")
                    signal = opportunity.get("signal", "NEUTRAL")
                    confidence = opportunity.get("confidence", 0)
                    price = opportunity.get("price", 0)
                    
                    signal_emoji = "⚪"
                    if signal in ["STRONG_BUY", "BUY"]:
                        signal_emoji = "🟢"
                    elif signal in ["STRONG_SELL", "SELL"]:
                        signal_emoji = "🔴"
                    
                    message += f"{signal_emoji} {symbol}: {signal} ({confidence}%) @ ${price:,.2f}\n"
                
                message += "\n"
            
            # Thêm nhận xét về thị trường
            if "market_outlook" in market_report:
                outlook = market_report["market_outlook"]
                message += f"<b>Nhận xét:</b>\n{outlook}\n\n"
            
            # Thêm thời gian
            message += f"⏱ <i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi biểu đồ cùng với thông báo nếu có
            if self.config.get("include_charts", True):
                chart_files = [
                    "charts/market_overview.png",
                    "charts/bitcoin_analysis.png",
                    "charts/market_correlation.png"
                ]
                
                for chart_file in chart_files:
                    if os.path.exists(chart_file):
                        self.telegram.send_photo(chart_file, f"Biểu đồ thị trường - {datetime.now().strftime('%d/%m/%Y')}")
            
            # Gửi thông báo văn bản
            success = self.telegram.send_notification("info", message)
            
            # Cập nhật thời gian thông báo cuối cùng
            if success:
                self.last_notification_time["market_update"] = datetime.now()
                logger.info("Đã gửi báo cáo thị trường tăng cường thành công")
            
            return success
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo thị trường tăng cường: {e}")
            return False
    
    def send_multi_symbol_analysis(self, symbols: List[str] = None) -> bool:
        """
        Gửi phân tích đa symbol
        
        Args:
            symbols: Danh sách các symbols cần phân tích (nếu None, sử dụng tất cả)
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self._can_send_notification("market_updates"):
            return False
        
        try:
            # Nếu không chỉ định symbols, tìm tất cả các file phân tích
            if not symbols:
                analysis_files = []
                
                # Tìm tất cả các file phân tích
                for file in os.listdir():
                    if file.startswith("market_analysis_") and file.endswith(".json"):
                        symbol = file.replace("market_analysis_", "").replace(".json", "").upper()
                        analysis_files.append((symbol, file))
                
                if not analysis_files:
                    logger.warning("Không tìm thấy file phân tích nào")
                    return False
                
                # Chỉ lấy tối đa 5 symbols
                analysis_files = analysis_files[:5]
                symbols = [symbol for symbol, _ in analysis_files]
            
            # Thu thập dữ liệu phân tích cho từng symbol
            analysis_data = {}
            
            for symbol in symbols:
                file_path = f"market_analysis_{symbol.lower()}.json"
                
                if not os.path.exists(file_path):
                    logger.warning(f"Không tìm thấy file phân tích cho {symbol}: {file_path}")
                    continue
                
                try:
                    with open(file_path, 'r') as f:
                        symbol_data = json.load(f)
                    
                    analysis_data[symbol] = symbol_data
                except Exception as e:
                    logger.error(f"Lỗi khi đọc dữ liệu phân tích cho {symbol}: {e}")
            
            if not analysis_data:
                logger.warning("Không có dữ liệu phân tích nào để gửi")
                return False
            
            # Tạo thông báo
            message = "<b>📊 PHÂN TÍCH ĐA COIN</b>\n\n"
            
            # Thêm thông tin cho từng symbol
            for symbol, data in analysis_data.items():
                symbol_name = symbol.replace("USDT", "")
                current_price = data.get("current_price", 0)
                summary = data.get("summary", {})
                
                signal = summary.get("overall_signal", "NEUTRAL")
                confidence = summary.get("confidence", 0)
                
                signal_emoji = "⚪"
                if signal in ["STRONG_BUY", "BUY"]:
                    signal_emoji = "🟢"
                elif signal in ["STRONG_SELL", "SELL"]:
                    signal_emoji = "🔴"
                
                message += f"{signal_emoji} <b>{symbol_name} (${current_price:,.2f}):</b>\n"
                message += f"• Tín hiệu: {signal}\n"
                message += f"• Độ tin cậy: {confidence}%\n"
                
                # Thêm thông tin hỗ trợ/kháng cự
                price_prediction = summary.get("price_prediction", {})
                support = price_prediction.get("support", 0)
                resistance = price_prediction.get("resistance", 0)
                
                if support and resistance:
                    message += f"• Hỗ trợ: ${support:,.2f}\n"
                    message += f"• Kháng cự: ${resistance:,.2f}\n"
                
                # Thêm mô tả
                if "description" in summary:
                    short_desc = summary["description"].split(".")[0] + "."
                    message += f"• {short_desc}\n"
                
                message += "\n"
            
            # Thêm thời gian
            message += f"⏱ <i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            # Gửi thông báo
            success = self.telegram.send_notification("info", message)
            
            # Cập nhật thời gian thông báo cuối cùng
            if success:
                self.last_notification_time["market_update"] = datetime.now()
                logger.info(f"Đã gửi phân tích đa symbol ({', '.join(symbols)}) thành công")
            
            return success
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi phân tích đa symbol: {e}")
            return False


if __name__ == "__main__":
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test EnhancedTelegramNotifications
    notifications = EnhancedTelegramNotifications(notification_interval=30)
    
    # Gửi thông báo thị trường
    notifications.send_market_update()
    
    # Kiểm tra nếu có báo cáo thị trường nâng cao
    notifications.send_enhanced_market_report()
    
    print("Đã gửi các thông báo test")