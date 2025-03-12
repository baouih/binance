#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Activate Market Analyzer
-----------------------
Script để kích hoạt hệ thống phân tích thị trường và gửi thông báo qua Telegram
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime, timedelta
import traceback
try:
    import schedule
except ImportError:
    print("Không thể import module 'schedule'. Đang cài đặt...")
    os.system("pip install schedule")
    import schedule

from market_analysis_system import MarketAnalysisSystem
from telegram_notifier import TelegramNotifier
from enhanced_binance_api import EnhancedBinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('market_analyzer.log')
    ]
)

logger = logging.getLogger("market_analyzer")

class MarketAnalyzerActivator:
    """
    Lớp kích hoạt hệ thống phân tích thị trường
    """
    
    def __init__(self, config_path: str = "configs/market_analysis_config.json"):
        """
        Khởi tạo activator
        
        Args:
            config_path: Đường dẫn tới file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Khởi tạo các thành phần
        self.analyzer = MarketAnalysisSystem(config_path=config_path)
        self.notifier = TelegramNotifier()
        self.api = EnhancedBinanceAPI(testnet=self.config.get('testnet', True))
        
        # Trạng thái
        self.running = False
        self.last_analysis_time = None
        self.last_notification_time = None
        
        logger.info("Đã khởi tạo Market Analyzer Activator")
    
    def _load_config(self):
        """
        Tải cấu hình từ file
        
        Returns:
            dict: Cấu hình
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {e}")
        
        logger.warning("Không tìm thấy file cấu hình. Sử dụng cấu hình mặc định")
        return {
            "testnet": True,
            "symbols_to_analyze": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            "analysis_interval": 1800,  # 30 phút
            "notification_settings": {
                "send_market_summary": True,
                "send_trading_signals": True,
                "signal_confidence_threshold": 70,
                "notification_interval": 7200,  # 2 giờ
                "quiet_hours": [0, 5]  # 0h - 5h
            }
        }
    
    def run_market_analysis(self):
        """
        Chạy phân tích thị trường
        """
        try:
            logger.info("Bắt đầu phân tích thị trường...")
            
            # Phân tích tổng quan thị trường
            market_analysis = self.analyzer.analyze_market()
            
            if not market_analysis:
                logger.warning("Không thể phân tích thị trường")
                return
            
            logger.info(f"Đã phân tích thị trường: BTC = ${market_analysis.get('btc_price', 0):,.2f}")
            
            # Phân tích cơ hội giao dịch
            symbols = self.config.get('symbols_to_analyze', ["BTCUSDT", "ETHUSDT", "BNBUSDT"])
            opportunities = self.analyzer.scan_opportunities(symbols)
            
            logger.info(f"Đã tìm thấy {len(opportunities)} cơ hội giao dịch")
            
            # Tạo báo cáo
            market_report = self.analyzer.generate_market_report()
            
            # Gửi thông báo
            self._send_notifications(market_analysis, opportunities, market_report)
            
            # Cập nhật thời gian
            self.last_analysis_time = datetime.now()
            
            logger.info("Đã hoàn thành phân tích thị trường")
            
            return market_analysis, opportunities, market_report
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường: {e}")
            logger.debug(traceback.format_exc())
            return None, None, None
    
    def _should_send_notification(self):
        """
        Kiểm tra xem có nên gửi thông báo không
        
        Returns:
            bool: True nếu nên gửi thông báo
        """
        # Kiểm tra thời gian yên lặng
        current_hour = datetime.now().hour
        quiet_hours = self.config.get('notification_settings', {}).get('quiet_hours', [0, 5])
        
        if len(quiet_hours) >= 2 and quiet_hours[0] <= current_hour < quiet_hours[1]:
            logger.info(f"Đang trong thời gian yên lặng ({quiet_hours[0]}h - {quiet_hours[1]}h). Không gửi thông báo")
            return False
        
        # Kiểm tra khoảng thời gian thông báo
        if self.last_notification_time:
            notification_interval = self.config.get('notification_settings', {}).get('notification_interval', 7200)
            time_since_last = (datetime.now() - self.last_notification_time).total_seconds()
            
            if time_since_last < notification_interval:
                logger.info(f"Chưa đến thời gian gửi thông báo (cần {notification_interval}s, đã qua {time_since_last:.0f}s)")
                return False
        
        return True
    
    def _send_notifications(self, market_analysis, opportunities, market_report):
        """
        Gửi thông báo phân tích thị trường
        
        Args:
            market_analysis: Kết quả phân tích thị trường
            opportunities: Cơ hội giao dịch
            market_report: Báo cáo thị trường
        """
        if not self._should_send_notification():
            return
        
        notification_settings = self.config.get('notification_settings', {})
        send_market_summary = notification_settings.get('send_market_summary', True)
        send_trading_signals = notification_settings.get('send_trading_signals', True)
        signal_confidence_threshold = notification_settings.get('signal_confidence_threshold', 70)
        
        # Gửi tổng quan thị trường
        if send_market_summary and market_analysis:
            logger.info("Gửi thông báo tổng quan thị trường...")
            self.notifier.send_market_analysis(market_analysis)
        
        # Gửi tín hiệu giao dịch
        if send_trading_signals and opportunities:
            # Lọc các cơ hội có độ tin cậy cao
            high_confidence_ops = [op for op in opportunities if op.get('confidence', 0) >= signal_confidence_threshold]
            
            if high_confidence_ops:
                logger.info(f"Gửi thông báo {len(high_confidence_ops)} tín hiệu giao dịch độ tin cậy cao...")
                
                # Gửi tối đa 3 tín hiệu
                for op in high_confidence_ops[:3]:
                    self.notifier.send_signal_alert(op)
                    time.sleep(1)  # Tránh gửi quá nhanh
        
        self.last_notification_time = datetime.now()
        logger.info("Đã gửi tất cả thông báo")
    
    def start(self):
        """
        Bắt đầu chạy hệ thống phân tích theo lịch
        """
        if self.running:
            logger.warning("Hệ thống phân tích đã đang chạy")
            return
        
        self.running = True
        
        # Chạy phân tích ngay lập tức khi khởi động
        self.run_market_analysis()
        
        # Thiết lập lịch chạy định kỳ
        analysis_interval = self.config.get('analysis_interval', 1800)  # Mặc định 30 phút
        minutes = analysis_interval // 60
        
        if minutes < 1:
            minutes = 1
        
        schedule.every(minutes).minutes.do(self.run_market_analysis)
        logger.info(f"Đã thiết lập lịch chạy phân tích thị trường mỗi {minutes} phút")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Đã nhận lệnh dừng từ người dùng")
            self.running = False
        except Exception as e:
            logger.error(f"Lỗi khi chạy hệ thống phân tích: {e}")
            logger.debug(traceback.format_exc())
            self.running = False
    
    def stop(self):
        """
        Dừng hệ thống phân tích
        """
        self.running = False
        logger.info("Đã dừng hệ thống phân tích thị trường")

def run_once():
    """
    Chạy phân tích một lần
    """
    activator = MarketAnalyzerActivator()
    market_analysis, opportunities, market_report = activator.run_market_analysis()
    
    if market_analysis:
        print("\n=== TỔNG QUAN THỊ TRƯỜNG ===")
        print(f"Giá BTC: ${market_analysis.get('btc_price', 0):,.2f}")
        print(f"Thay đổi 24h: {market_analysis.get('btc_price_change_24h', 0):+.2f}%")
        print(f"Trạng thái thị trường: {market_analysis.get('market_status', 'UNKNOWN')}")
        
        if 'market_regime' in market_analysis:
            regime = market_analysis['market_regime']
            print(f"Chế độ thị trường: {regime.get('primary', 'RANGE_BOUND')}")
            print(f"Biến động: {regime.get('volatility', 'NORMAL')}")
    
    if opportunities:
        print("\n=== CƠ HỘI GIAO DỊCH ===")
        for i, op in enumerate(opportunities[:5], 1):
            symbol = op.get('symbol', 'UNKNOWN')
            action = op.get('action', 'UNKNOWN')
            confidence = op.get('confidence', 0)
            price = op.get('current_price', 0)
            target = op.get('target_price', 0)
            
            target_pct = ((target - price) / price * 100) if price > 0 and target > 0 else 0
            
            print(f"{i}. {symbol}: {action} (Độ tin cậy: {confidence}%)")
            print(f"   Giá hiện tại: ${price:,.2f}")
            print(f"   Giá mục tiêu: ${target:,.2f} ({target_pct:+.2f}%)")
            print("")

def main():
    parser = argparse.ArgumentParser(description="Kích hoạt hệ thống phân tích thị trường")
    parser.add_argument('--once', action='store_true', help='Chạy phân tích một lần và hiển thị kết quả')
    parser.add_argument('--config', type=str, default='configs/market_analysis_config.json', help='Đường dẫn tới file cấu hình')
    
    args = parser.parse_args()
    
    if args.once:
        run_once()
    else:
        activator = MarketAnalyzerActivator(config_path=args.config)
        activator.start()

if __name__ == "__main__":
    main()