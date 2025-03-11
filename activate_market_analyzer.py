#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Activate Market Analyzer
-----------------------
Script khởi động hệ thống phân tích thị trường tự động với cảnh báo qua Telegram
"""

import os
import sys
import json
import time
import logging
import argparse
import threading
from datetime import datetime
import schedule

from market_analysis_system import MarketAnalysisSystem
from enhanced_telegram_notifications import EnhancedTelegramNotifications

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("market_analyzer.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("activate_market_analyzer")

class MarketAnalyzerActivator:
    """
    Kích hoạt hệ thống phân tích thị trường tự động
    """
    
    def __init__(self, 
                 config_path: str = "configs/market_analysis_config.json",
                 notification_interval: int = 60,
                 run_immediately: bool = True):
        """
        Khởi tạo activator
        
        Args:
            config_path: Đường dẫn đến file cấu hình
            notification_interval: Khoảng thời gian giữa các thông báo (phút)
            run_immediately: Chạy phân tích ngay lập tức sau khi khởi tạo
        """
        self.config_path = config_path
        self.notification_interval = notification_interval
        self.analyzer = MarketAnalysisSystem(config_path)
        self.notifier = EnhancedTelegramNotifications(config_path, notification_interval)
        
        # Chạy phân tích ngay lập tức nếu được yêu cầu
        if run_immediately:
            self.run_analysis()
        
        # Bắt đầu lịch trình thông báo
        self.start_schedule()
    
    def run_analysis(self):
        """Chạy phân tích thị trường và lưu kết quả"""
        try:
            logger.info("Bắt đầu phân tích thị trường...")
            start_time = time.time()
            
            # Lấy cấu hình phân tích
            symbols = self.analyzer.config.get('symbols_to_analyze', ["BTCUSDT", "ETHUSDT"])
            
            # Phân tích thị trường tổng thể
            market_data = self.analyzer.analyze_market()
            
            # Lưu kết quả phân tích thị trường
            with open('market_overview.json', 'w') as f:
                json.dump(market_data, f, indent=4)
            
            logger.info(f"Đã hoàn thành phân tích thị trường tổng thể")
            
            # Phân tích từng symbol
            all_analysis = {}
            primary_tf = self.analyzer.config.get('primary_timeframe', "1h")
            
            for symbol in symbols:
                logger.info(f"Đang phân tích {symbol}...")
                analysis = self.analyzer.analyze_symbol(symbol, primary_tf)
                all_analysis[symbol] = analysis
                
                # Lưu kết quả phân tích cho từng symbol
                with open(f'market_analysis_{symbol.lower()}.json', 'w') as f:
                    json.dump(analysis, f, indent=4)
            
            # Lưu tất cả kết quả phân tích
            with open('market_analysis.json', 'w') as f:
                json.dump(all_analysis, f, indent=4)
            
            # Tạo đề xuất giao dịch
            recommendations = self.analyzer.generate_trading_recommendations(symbols)
            
            # Lưu đề xuất giao dịch
            with open('all_recommendations.json', 'w') as f:
                json.dump(recommendations, f, indent=4)
            
            # Tạo báo cáo thị trường
            market_report = self.analyzer.generate_market_report()
            
            # Lưu báo cáo thị trường
            with open('market_report.json', 'w') as f:
                json.dump(market_report, f, indent=4)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Đã hoàn thành phân tích tất cả ({elapsed_time:.2f} giây)")
            
            return all_analysis, recommendations, market_report
            
        except Exception as e:
            logger.error(f"Lỗi khi chạy phân tích thị trường: {e}")
            return None, None, None
    
    def start_schedule(self):
        """Bắt đầu lịch trình phân tích và thông báo"""
        try:
            # Lấy khoảng thời gian phân tích từ cấu hình
            analysis_interval = self.analyzer.config.get('analysis_interval', 1800)  # Mặc định 30 phút
            analysis_interval_minutes = max(1, analysis_interval // 60)  # Chuyển đổi giây sang phút
            
            logger.info(f"Thiết lập phân tích thị trường mỗi {analysis_interval_minutes} phút")
            
            # Lịch trình phân tích
            schedule.every(analysis_interval_minutes).minutes.do(self.run_and_notify)
            
            # Bắt đầu thông báo Telegram
            self.notifier.start_scheduled_notifications()
            
            # Bắt đầu thread để chạy lịch trình
            self.scheduler_thread = threading.Thread(target=self._run_schedule, daemon=True)
            self.scheduler_thread.start()
            
            logger.info("Đã bắt đầu lịch trình phân tích thị trường")
            
            # Gửi thông báo khởi động
            self.send_startup_notification()
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi bắt đầu lịch trình: {e}")
            return False
    
    def _run_schedule(self):
        """Hàm chạy lịch trình trong thread riêng"""
        logger.info("Thread lịch trình phân tích đã bắt đầu")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except Exception as e:
            logger.error(f"Lỗi trong thread lịch trình: {e}")
        
        logger.info("Thread lịch trình phân tích đã kết thúc")
    
    def run_and_notify(self):
        """Chạy phân tích và gửi thông báo"""
        analysis, recommendations, market_report = self.run_analysis()
        
        if analysis and recommendations:
            # Gửi thông báo thị trường
            self.notifier.send_market_update()
            
            # Tìm các tín hiệu mạnh để gửi cảnh báo
            for symbol, data in analysis.items():
                summary = data.get('summary', {})
                signal = summary.get('overall_signal', 'NEUTRAL')
                confidence = summary.get('confidence', 0)
                
                if signal != 'NEUTRAL' and confidence >= 70:
                    # Tạo dữ liệu tín hiệu
                    signal_data = {
                        'symbol': symbol,
                        'signal': signal,
                        'confidence': confidence,
                        'price': data.get('current_price', 0),
                        'description': summary.get('description', ''),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Thêm thông tin giá mục tiêu và stop loss
                    price_prediction = summary.get('price_prediction', {})
                    if signal in ['STRONG_BUY', 'BUY']:
                        signal_data['target_price'] = price_prediction.get('resistance', 0)
                        signal_data['stop_loss'] = price_prediction.get('support', 0)
                    elif signal in ['STRONG_SELL', 'SELL']:
                        signal_data['target_price'] = price_prediction.get('support', 0)
                        signal_data['stop_loss'] = price_prediction.get('resistance', 0)
                    
                    # Gửi cảnh báo tín hiệu
                    self.notifier.send_signal_alert(symbol, signal_data)
            
            # Gửi đề xuất giao dịch tốt nhất nếu có
            top_opportunities = recommendations.get('top_opportunities', [])
            if top_opportunities:
                for opportunity in top_opportunities[:1]:  # Chỉ lấy cơ hội tốt nhất
                    symbol = opportunity.get('symbol', '')
                    
                    # Chỉ gửi thông báo nếu có tín hiệu mạnh
                    if opportunity.get('action') in ['BUY', 'SELL'] and opportunity.get('confidence', 0) >= 75:
                        # Tạo dữ liệu trade
                        trade_data = {
                            'symbol': symbol,
                            'side': 'BUY' if opportunity.get('action') == 'BUY' else 'SELL',
                            'entry_price': opportunity.get('current_price', 0),
                            'quantity': 0.1,  # Giá trị mẫu
                            'take_profit': opportunity.get('target_price', 0),
                            'stop_loss': opportunity.get('stop_loss', 0),
                            'reason': opportunity.get('description', ''),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        # Gửi thông báo giao dịch
                        self.notifier.send_trade_notification(trade_data)
    
    def send_startup_notification(self):
        """Gửi thông báo khởi động hệ thống"""
        message = "<b>🚀 HỆ THỐNG PHÂN TÍCH THỊ TRƯỜNG ĐÃ KHỞI ĐỘNG</b>\n\n"
        
        # Thêm thông tin cấu hình
        symbols = self.analyzer.config.get('symbols_to_analyze', [])
        timeframes = self.analyzer.config.get('timeframes', [])
        
        message += f"<b>Đang theo dõi:</b> {', '.join(symbols)}\n"
        message += f"<b>Khung thời gian:</b> {', '.join(timeframes)}\n"
        message += f"<b>Khung thời gian chính:</b> {self.analyzer.config.get('primary_timeframe', '1h')}\n"
        
        # Thêm thông tin lịch trình
        analysis_interval = self.analyzer.config.get('analysis_interval', 1800)
        analysis_interval_minutes = max(1, analysis_interval // 60)
        
        message += f"\n<b>Lịch trình:</b>\n"
        message += f"• Phân tích thị trường: Mỗi {analysis_interval_minutes} phút\n"
        message += f"• Thông báo thị trường: Mỗi {self.notification_interval} phút\n"
        
        # Thêm thông tin về độ tin cậy tối thiểu
        min_confidence = self.notifier.config.get('min_signal_confidence', 70)
        message += f"\n<b>Cấu hình thông báo:</b>\n"
        message += f"• Độ tin cậy tối thiểu: {min_confidence}%\n"
        
        # Thêm thông tin về giờ yên tĩnh
        quiet_hours = self.notifier.config.get('quiet_hours', {})
        if quiet_hours.get('enabled', False):
            start_hour = quiet_hours.get('start_hour', 0)
            end_hour = quiet_hours.get('end_hour', 7)
            message += f"• Giờ yên tĩnh: {start_hour}:00 - {end_hour}:00\n"
        
        # Thêm thời gian
        message += f"\n⏱ <i>Khởi động lúc: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        
        # Gửi thông báo
        self.notifier.telegram.send_notification("info", message)

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Kích hoạt hệ thống phân tích thị trường tự động')
    parser.add_argument('--config', type=str, default="configs/market_analysis_config.json", help='Đường dẫn đến file cấu hình')
    parser.add_argument('--interval', type=int, default=60, help='Khoảng thời gian giữa các thông báo (phút)')
    parser.add_argument('--no-immediate', action='store_false', dest='run_immediately', help='Không chạy phân tích ngay lập tức')
    
    args = parser.parse_args()
    
    activator = MarketAnalyzerActivator(
        config_path=args.config,
        notification_interval=args.interval,
        run_immediately=args.run_immediately
    )
    
    try:
        # Giữ thread chính chạy
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Đã nhận tín hiệu thoát. Dừng hệ thống...")
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {e}")
    
    logger.info("Hệ thống phân tích thị trường đã dừng")

if __name__ == "__main__":
    main()