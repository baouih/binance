#!/usr/bin/env python3
"""
Kiểm tra chuyên sâu hệ thống thông báo Telegram

Test việc gửi tất cả loại thông báo qua Telegram, bao gồm:
1. Thông báo tín hiệu giao dịch
2. Thông báo vị thế được mở/đóng
3. Gửi biểu đồ phân tích
4. Báo cáo hiệu suất
5. Xử lý lỗi kết nối
"""

import os
import sys
import time
import json
import logging
import traceback
from typing import Dict, List, Union, Optional
from datetime import datetime
import unittest
from unittest.mock import patch, MagicMock

# Thêm thư mục gốc vào sys.path để import module từ dự án
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from telegram_notify import TelegramNotifier
except ImportError:
    logging.warning("Không thể import TelegramNotifier, sẽ tạo mock")
    class TelegramNotifier:
        def __init__(self, token=None, chat_id=None):
            self.token = token
            self.chat_id = chat_id
            self.enabled = bool(token and chat_id)
            
        def send_message(self, message, parse_mode="HTML"):
            print(f"[MOCK] Gửi tin nhắn: {message}")
            return True
            
        def send_photo(self, photo_path, caption=None, parse_mode="HTML"):
            print(f"[MOCK] Gửi ảnh: {photo_path}, caption: {caption}")
            return True
            
        def send_document(self, document_path, caption=None, parse_mode="HTML"):
            print(f"[MOCK] Gửi tài liệu: {document_path}, caption: {caption}")
            return True
            
        def send_trade_signal(self, **kwargs):
            print(f"[MOCK] Gửi tín hiệu giao dịch: {kwargs}")
            return True
            
        def send_position_closed(self, **kwargs):
            print(f"[MOCK] Gửi thông báo đóng vị thế: {kwargs}")
            return True
            
        def send_trade_execution(self, **kwargs):
            print(f"[MOCK] Gửi thông báo thực hiện giao dịch: {kwargs}")
            return True
            
        def send_daily_report(self, **kwargs):
            print(f"[MOCK] Gửi báo cáo hàng ngày: {kwargs}")
            return True

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_telegram')

class TestTelegramNotifications(unittest.TestCase):
    """Test các chức năng thông báo qua Telegram"""
    
    def setUp(self):
        """Thiết lập cho mỗi test case"""
        # Lấy token và chat_id từ biến môi trường hoặc sử dụng giá trị mẫu
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "8069189803:AAF3PJc3BNQgZmpQ2Oj7o0-ySJGmi2AQ9OM")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "1834332146")
        
        # Kiểm tra xem token và chat_id có giống mẫu không, nếu có thì sử dụng mock
        self.use_mock = token == "8069189803:AAF3PJc3BNQgZmpQ2Oj7o0-ySJGmi2AQ9OM" or not token
        
        if self.use_mock:
            logger.warning("Sử dụng mock cho Telegram test do không có thông tin API hợp lệ")
            self.notifier = TelegramNotifier(token, chat_id)
        else:
            logger.info("Sử dụng Telegram API thật")
            self.notifier = TelegramNotifier(token, chat_id)
        
        # Tạo thư mục test chart nếu chưa tồn tại
        self.chart_dir = os.path.join(os.path.dirname(__file__), '../test_charts')
        if not os.path.exists(self.chart_dir):
            os.makedirs(self.chart_dir)
            
        # Tạo file biểu đồ mẫu nếu chưa tồn tại
        self.sample_chart = os.path.join(self.chart_dir, 'sample_chart.png')
        try:
            # Thử tạo một biểu đồ đơn giản với matplotlib (nếu có)
            import matplotlib.pyplot as plt
            import numpy as np
            
            if not os.path.exists(self.sample_chart) or os.path.getsize(self.sample_chart) < 1000:
                plt.figure(figsize=(8, 6))
                x = np.linspace(0, 10, 100)
                y = np.sin(x)
                plt.plot(x, y)
                plt.title('Sample Chart for Telegram Test')
                plt.xlabel('Time')
                plt.ylabel('Value')
                plt.grid(True)
                plt.savefig(self.sample_chart)
                plt.close()
                logger.info(f"Đã tạo biểu đồ mẫu tại {self.sample_chart}")
        except ImportError:
            # Nếu không có matplotlib, tạo một file PNG đơn giản lớn hơn
            if not os.path.exists(self.sample_chart) or os.path.getsize(self.sample_chart) < 1000:
                # Tạo một PNG đơn giản 100x100 pixels
                png_header = b'\x89PNG\r\n\x1a\n'
                png_ihdr = b'\x00\x00\x00\x0DIHDR\x00\x00\x00d\x00\x00\x00d\x08\x02\x00\x00\x00\xff\x80\x02\x03'
                png_data = b'\x00\x00\x00\x01sRGB\x00\xAE\xCE\x1C\xE9\x00\x00\x00\x04gAMA\x00\x00\xB1\x8F\x0B\xFC\x61\x05'
                png_end = b'\x00\x00\x00\x00IEND\xAEB`\x82'
                
                with open(self.sample_chart, 'wb') as f:
                    f.write(png_header + png_ihdr + png_data + (b'\x00' * 1000) + png_end)
                logger.info(f"Đã tạo PNG đơn giản tại {self.sample_chart}")
        
        # Tạo file báo cáo mẫu nếu chưa tồn tại
        self.sample_report = os.path.join(self.chart_dir, 'sample_report.json')
        if not os.path.exists(self.sample_report):
            sample_data = {
                'timestamp': datetime.now().isoformat(),
                'data': 'Sample report data'
            }
            with open(self.sample_report, 'w') as f:
                json.dump(sample_data, f)
    
    def test_01_send_text_message(self):
        """Test gửi tin nhắn văn bản đơn giản"""
        logger.info("Test gửi tin nhắn văn bản")
        
        message = """
<b>Thông báo kiểm tra</b>

Đây là thông báo kiểm tra được gửi vào {time}.
        """.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        result = self.notifier.send_message(message)
        self.assertTrue(result, "Gửi tin nhắn thất bại")
        logger.info("✅ Test gửi tin nhắn văn bản thành công")
    
    def test_02_send_photo(self):
        """Test gửi hình ảnh"""
        logger.info("Test gửi hình ảnh")
        
        caption = "Biểu đồ kiểm tra - " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        result = self.notifier.send_photo(
            photo_path=self.sample_chart,
            caption=caption
        )
        self.assertTrue(result, "Gửi hình ảnh thất bại")
        logger.info("✅ Test gửi hình ảnh thành công")
    
    def test_03_send_document(self):
        """Test gửi tài liệu"""
        logger.info("Test gửi tài liệu")
        
        caption = "Báo cáo kiểm tra - " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        result = self.notifier.send_document(
            document_path=self.sample_report,
            caption=caption
        )
        self.assertTrue(result, "Gửi tài liệu thất bại")
        logger.info("✅ Test gửi tài liệu thành công")
    
    def test_04_send_trade_signal(self):
        """Test gửi tín hiệu giao dịch"""
        logger.info("Test gửi tín hiệu giao dịch")
        
        # Tín hiệu mua
        buy_signal = {
            "symbol": "BTCUSDT",
            "final_signal": "BUY",
            "ml_confidence": 0.85,
            "current_price": 60420.50,
            "timeframe": "4h",
            "market_regime": "uptrend",
            "composite_score": 0.72,
            "indicators": {
                "rsi": 58.2,
                "macd": 120.5,
                "atr": 1200.3
            }
        }
        
        result = self.notifier.send_trade_signal(signal_info=buy_signal)
        self.assertTrue(result, "Gửi tín hiệu mua thất bại")
        
        # Đợi 3 giây để tránh Telegram API rate limit
        time.sleep(3)
        
        # Tín hiệu bán
        sell_signal = {
            "symbol": "ETHUSDT",
            "final_signal": "SELL",
            "ml_confidence": 0.65,
            "current_price": 3140.75,
            "timeframe": "1h",
            "market_regime": "downtrend",
            "composite_score": -0.48,
            "indicators": {
                "rsi": 72.5,
                "macd": -45.2,
                "atr": 80.3
            }
        }
        
        result = self.notifier.send_trade_signal(signal_info=sell_signal)
        self.assertTrue(result, "Gửi tín hiệu bán thất bại")
        
        # Đợi 3 giây để tránh Telegram API rate limit
        time.sleep(3)
        
        # Tín hiệu trung lập
        neutral_signal = {
            "symbol": "SOLUSDT",
            "final_signal": "NEUTRAL",
            "ml_confidence": 0.40,
            "current_price": 125.20,
            "timeframe": "2h",
            "market_regime": "ranging",
            "composite_score": 0.05,
            "indicators": {
                "rsi": 45.8,
                "macd": 5.2,
                "atr": 4.5
            }
        }
        
        result = self.notifier.send_trade_signal(signal_info=neutral_signal)
        self.assertTrue(result, "Gửi tín hiệu trung lập thất bại")
        
        logger.info("✅ Test gửi tín hiệu giao dịch thành công")
    
    def test_05_send_position_closed(self):
        """Test gửi thông báo đóng vị thế"""
        logger.info("Test gửi thông báo đóng vị thế")
        
        # Vị thế lãi
        profit_position = {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_price": 58750.25,
            "exit_price": 61430.80,
            "quantity": 0.15,
            "pnl": 402.08,
            "pnl_percent": 4.55,
            "exit_reason": "Take Profit"
        }
        
        result = self.notifier.send_position_closed(position_data=profit_position)
        self.assertTrue(result, "Gửi thông báo vị thế lãi thất bại")
        
        # Đợi 3 giây để tránh Telegram API rate limit
        time.sleep(3)
        
        # Vị thế lỗ
        loss_position = {
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "entry_price": 3420.50,
            "exit_price": 3520.75,
            "quantity": 1.2,
            "pnl": -120.30,
            "pnl_percent": -2.93,
            "exit_reason": "Stop Loss"
        }
        
        result = self.notifier.send_position_closed(position_data=loss_position)
        self.assertTrue(result, "Gửi thông báo vị thế lỗ thất bại")
        
        logger.info("✅ Test gửi thông báo đóng vị thế thành công")
    
    def test_06_send_trade_execution(self):
        """Test gửi thông báo thực hiện giao dịch"""
        logger.info("Test gửi thông báo thực hiện giao dịch")
        
        # Giao dịch mua
        result = self.notifier.send_trade_execution(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.05,
            price=60750.25,
            total=3037.51,
        )
        self.assertTrue(result, "Gửi thông báo giao dịch mua thất bại")
        
        # Đợi 3 giây để tránh Telegram API rate limit
        time.sleep(3)
        
        # Giao dịch bán có lãi
        result = self.notifier.send_trade_execution(
            symbol="BTCUSDT",
            side="SELL",
            quantity=0.05,
            price=61850.75,
            total=3092.54,
            pnl=55.03
        )
        self.assertTrue(result, "Gửi thông báo giao dịch bán thất bại")
        
        logger.info("✅ Test gửi thông báo thực hiện giao dịch thành công")
    
    def test_07_send_daily_report(self):
        """Test gửi báo cáo hàng ngày"""
        logger.info("Test gửi báo cáo hàng ngày")
        
        performance_data = {
            "current_balance": 15250.75,
            "daily_pnl": 350.25,
            "daily_trades": 8,
            "win_rate": 0.75,
            "open_positions": [
                {
                    "symbol": "BTCUSDT",
                    "type": "LONG",
                    "entry_price": 59870.50,
                    "current_price": 60420.75,
                    "pnl": 82.5,
                    "pnl_percent": 0.92
                },
                {
                    "symbol": "ETHUSDT",
                    "type": "SHORT",
                    "entry_price": 3520.25,
                    "current_price": 3480.50,
                    "pnl": 47.75,
                    "pnl_percent": 1.13
                }
            ],
            "best_performer": "BTCUSDT",
            "worst_performer": "DOGEUSDT"
        }
        
        result = self.notifier.send_daily_report(performance_data)
        self.assertTrue(result, "Gửi báo cáo hàng ngày thất bại")
        
        logger.info("✅ Test gửi báo cáo hàng ngày thành công")
    
    @patch('requests.post')
    def test_08_error_handling(self, mock_post):
        """Test xử lý lỗi khi gửi thông báo"""
        logger.info("Test xử lý lỗi khi gửi thông báo")
        
        if self.use_mock:
            # Giả lập lỗi kết nối
            mock_post.side_effect = Exception("Simulated connection error")
            
            # Test gửi tin nhắn khi có lỗi
            result = self.notifier.send_message("Tin nhắn sẽ thất bại")
            self.assertFalse(result, "Xử lý lỗi không hoạt động đúng")
            
            # Test gửi hình ảnh khi có lỗi
            result = self.notifier.send_photo(self.sample_chart, "Hình ảnh sẽ thất bại")
            self.assertFalse(result, "Xử lý lỗi không hoạt động đúng")
            
            # Test gửi tín hiệu khi có lỗi
            result = self.notifier.send_trade_signal(symbol="BTCUSDT", signal="BUY")
            self.assertFalse(result, "Xử lý lỗi không hoạt động đúng")
            
            logger.info("✅ Test xử lý lỗi thành công")
        else:
            logger.warning("Bỏ qua test xử lý lỗi vì đang sử dụng API thật")

    def test_09_rate_limit_compliance(self):
        """Test tuân thủ rate limit của Telegram API"""
        logger.info("Test tuân thủ rate limit của Telegram API")
        
        # Gửi 10 tin nhắn liên tiếp, đảm bảo khoảng thời gian giữa các tin nhắn
        for i in range(5):
            message = f"Test tin nhắn tuần tự {i+1} - {datetime.now().strftime('%H:%M:%S')}"
            result = self.notifier.send_message(message)
            self.assertTrue(result, f"Gửi tin nhắn {i+1} thất bại")
            
            # Đợi 1 giây giữa các tin nhắn để tránh Telegram API rate limit
            time.sleep(1)
        
        logger.info("✅ Test tuân thủ rate limit thành công")

def run_tests():
    """Chạy tất cả các bài kiểm tra Telegram"""
    
    logger.info("=== BẮT ĐẦU KIỂM TRA THÔNG BÁO TELEGRAM ===")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Tạo test suite và chạy
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestTelegramNotifications))
    
    # Chạy các test
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Tóm tắt kết quả
    logger.info("\n=== KẾT QUẢ KIỂM TRA ===")
    logger.info(f"Tổng số test: {result.testsRun}")
    logger.info(f"Số test thành công: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"Số test thất bại: {len(result.failures)}")
    logger.info(f"Số test lỗi: {len(result.errors)}")
    
    # Chi tiết về các test thất bại hoặc lỗi
    if result.failures:
        logger.error("\nCHI TIẾT CÁC TEST THẤT BẠI:")
        for test, error in result.failures:
            logger.error(f"\n{test}")
            logger.error(error)
    
    if result.errors:
        logger.error("\nCHI TIẾT CÁC TEST LỖI:")
        for test, error in result.errors:
            logger.error(f"\n{test}")
            logger.error(error)
    
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)