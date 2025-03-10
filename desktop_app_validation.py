#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Công cụ kiểm tra và xác thực ứng dụng desktop
"""

import os
import sys
import time
import json
import logging
import traceback
from typing import Dict, List, Any, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("desktop_validation.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("desktop_validation")

# Import các module
try:
    from dotenv import load_dotenv
    from market_analyzer import MarketAnalyzer
    from position_manager import PositionManager
    from risk_manager import RiskManager
    from auto_update_client import AutoUpdater
    
    logger.info("Đã import thành công các module")
except ImportError as e:
    logger.error(f"Lỗi khi import module: {str(e)}")
    sys.exit(1)

class DesktopAppValidator:
    """Công cụ kiểm tra tính năng của ứng dụng desktop"""
    
    def __init__(self):
        """Khởi tạo validator"""
        # Tải biến môi trường
        load_dotenv()
        
        # Biến để theo dõi kết quả kiểm tra
        self.validation_results = {
            "api_connection": False,
            "market_data": False,
            "position_management": False,
            "risk_management": False,
            "technical_analysis": False,
            "auto_update": False,
            "telegram_integration": False
        }
        
        # Khởi tạo các đối tượng
        self.market_analyzer = None
        self.position_manager = None
        self.risk_manager = None
        self.auto_updater = None
        
        logger.info("Đã khởi tạo Desktop App Validator")
    
    def initialize_components(self):
        """Khởi tạo các thành phần cần thiết"""
        try:
            # Kiểm tra thông tin API
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
            
            if not api_key or not api_secret:
                logger.error("Thiếu API Key hoặc API Secret")
                return False
            
            # Khởi tạo các đối tượng
            self.market_analyzer = MarketAnalyzer(testnet=True)
            self.position_manager = PositionManager(testnet=True)
            self.risk_manager = RiskManager(self.position_manager)
            self.auto_updater = AutoUpdater()
            
            logger.info("Đã khởi tạo các thành phần")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo các thành phần: {str(e)}", exc_info=True)
            return False
    
    def validate_api_connection(self):
        """Kiểm tra kết nối API"""
        try:
            logger.info("Kiểm tra kết nối API...")
            
            if not self.market_analyzer or not self.market_analyzer.client:
                logger.error("Chưa khởi tạo MarketAnalyzer hoặc thiếu client")
                return False
            
            # Ping API để kiểm tra kết nối
            self.market_analyzer.client.ping()
            
            # Lấy thông tin máy chủ
            server_time = self.market_analyzer.client.get_server_time()
            logger.info(f"Server time: {server_time}")
            
            self.validation_results["api_connection"] = True
            logger.info("✅ Kết nối API thành công")
            return True
        
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra kết nối API: {str(e)}", exc_info=True)
            return False
    
    def validate_market_data(self):
        """Kiểm tra lấy dữ liệu thị trường"""
        try:
            logger.info("Kiểm tra lấy dữ liệu thị trường...")
            
            # Lấy tổng quan thị trường
            market_overview = self.market_analyzer.get_market_overview()
            
            if market_overview.get("status") != "success":
                logger.error(f"Lỗi khi lấy tổng quan thị trường: {market_overview.get('message', 'Lỗi không xác định')}")
                return False
            
            # Kiểm tra dữ liệu
            market_data = market_overview.get("data", [])
            
            if not market_data:
                logger.error("Không có dữ liệu thị trường")
                return False
            
            # Hiển thị một số dữ liệu mẫu
            logger.info(f"Số lượng cặp giao dịch: {len(market_data)}")
            
            for i, data in enumerate(market_data[:3]):
                logger.info(f"Dữ liệu {i+1}: {data.get('symbol')} - Giá: {data.get('price')} - Thay đổi 24h: {data.get('change_24h')}%")
            
            # Kiểm tra dữ liệu lịch sử
            btc_data = self.market_analyzer.get_historical_data("BTCUSDT", "1h", 10)
            
            if btc_data.empty:
                logger.error("Không có dữ liệu lịch sử cho BTCUSDT")
                return False
            
            logger.info(f"Số dòng dữ liệu lịch sử: {len(btc_data)}")
            
            self.validation_results["market_data"] = True
            logger.info("✅ Lấy dữ liệu thị trường thành công")
            return True
        
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra dữ liệu thị trường: {str(e)}", exc_info=True)
            return False
    
    def validate_position_management(self):
        """Kiểm tra quản lý vị thế"""
        try:
            logger.info("Kiểm tra chức năng quản lý vị thế...")
            
            # Lấy số dư tài khoản
            account_info = self.position_manager.get_account_balance()
            
            if account_info.get("status") != "success":
                logger.error(f"Lỗi khi lấy số dư tài khoản: {account_info.get('message', 'Lỗi không xác định')}")
                return False
            
            balance = account_info.get("balance", {})
            
            logger.info(f"Số dư tài khoản: {balance.get('total_balance')} USDT")
            logger.info(f"Số dư khả dụng: {balance.get('available_balance')} USDT")
            
            # Kiểm tra danh sách vị thế
            positions = self.position_manager.get_all_positions()
            
            logger.info(f"Số lượng vị thế đang mở: {len(positions)}")
            
            # Thử mở một vị thế test
            test_symbol = "BNBUSDT"
            test_side = "SHORT"
            test_amount = 0.01
            
            # Đặt đòn bẩy
            try:
                self.position_manager.client.futures_change_leverage(symbol=test_symbol, leverage=5)
                logger.info(f"Đã thiết lập đòn bẩy: 5x")
            except Exception as e:
                logger.warning(f"Không thể thiết lập đòn bẩy: {str(e)}")
            
            # Lấy giá hiện tại
            symbol_ticker = self.position_manager.client.futures_symbol_ticker(symbol=test_symbol)
            current_price = float(symbol_ticker["price"])
            
            # Tính SL/TP
            sl_tp = self.risk_manager.calculate_sl_tp(test_symbol, test_side, current_price)
            
            # Hiển thị thông tin giao dịch test
            logger.info(f"Thông tin giao dịch test: {test_symbol} {test_side}")
            logger.info(f"Giá hiện tại: {current_price}")
            logger.info(f"Stop Loss: {sl_tp.get('stop_loss')}")
            logger.info(f"Take Profit: {sl_tp.get('take_profit')}")
            
            # Mở vị thế - CHỈ SỬ DỤNG KHI CẦN TEST THỰC TẾ
            # result = self.position_manager.open_position(
            #     test_symbol, test_side, test_amount,
            #     sl_tp.get("stop_loss"), sl_tp.get("take_profit"), 5
            # )
            
            # if result.get("status") == "success":
            #     logger.info(f"Đã mở vị thế test: {test_symbol} {test_side} tại giá {current_price}")
            #     
            #     # Đóng vị thế test ngay lập tức
            #     close_result = self.position_manager.close_position(test_symbol)
            #     
            #     if close_result.get("status") == "success":
            #         logger.info(f"Đã đóng vị thế test: {test_symbol}")
            #     else:
            #         logger.error(f"Lỗi khi đóng vị thế test: {close_result.get('message', 'Lỗi không xác định')}")
            # else:
            #     logger.error(f"Lỗi khi mở vị thế test: {result.get('message', 'Lỗi không xác định')}")
            
            # Kiểm tra thành công nếu không có lỗi
            self.validation_results["position_management"] = True
            logger.info("✅ Kiểm tra quản lý vị thế thành công")
            return True
        
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra quản lý vị thế: {str(e)}", exc_info=True)
            return False
    
    def validate_risk_management(self):
        """Kiểm tra quản lý rủi ro"""
        try:
            logger.info("Kiểm tra chức năng quản lý rủi ro...")
            
            # Tính toán kích thước vị thế
            account_balance = 1000.0  # Giả sử số dư tài khoản là 1000 USDT
            test_symbol = "BTCUSDT"
            
            position_size = self.risk_manager.calculate_position_size(account_balance, test_symbol)
            
            logger.info(f"Kích thước vị thế được tính toán: {position_size} {test_symbol.replace('USDT', '')}")
            
            # Kiểm tra tính hợp lệ của vị thế
            is_valid, reason = self.risk_manager.validate_new_position(test_symbol, "LONG", position_size)
            
            logger.info(f"Vị thế hợp lệ: {is_valid}, Lý do: {reason}")
            
            # Kiểm tra exposure
            risk_exposure = self.risk_manager.check_risk_exposure()
            
            logger.info(f"Mức độ rủi ro hiện tại: {risk_exposure.get('risk_level')}")
            logger.info(f"Số lượng vị thế: {risk_exposure.get('position_count')}/{risk_exposure.get('max_positions')}")
            
            self.validation_results["risk_management"] = True
            logger.info("✅ Kiểm tra quản lý rủi ro thành công")
            return True
        
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra quản lý rủi ro: {str(e)}", exc_info=True)
            return False
    
    def validate_technical_analysis(self):
        """Kiểm tra phân tích kỹ thuật"""
        try:
            logger.info("Kiểm tra chức năng phân tích kỹ thuật...")
            
            # Phân tích kỹ thuật cho BTC
            btc_analysis = self.market_analyzer.analyze_technical("BTCUSDT", "1h")
            
            if btc_analysis.get("status") != "success":
                logger.error(f"Lỗi khi phân tích kỹ thuật: {btc_analysis.get('message', 'Lỗi không xác định')}")
                return False
            
            # Hiển thị kết quả phân tích
            logger.info(f"Tín hiệu tổng hợp: {btc_analysis.get('overall_signal')}")
            logger.info(f"Độ mạnh: {btc_analysis.get('strength')}")
            logger.info(f"Xu hướng ngắn hạn: {btc_analysis.get('short_term_trend')}")
            logger.info(f"Xu hướng trung hạn: {btc_analysis.get('mid_term_trend')}")
            logger.info(f"Xu hướng dài hạn: {btc_analysis.get('long_term_trend')}")
            
            # Kiểm tra các chỉ báo
            indicators = btc_analysis.get("indicators", [])
            
            for indicator in indicators:
                logger.info(f"Chỉ báo {indicator.get('name')}: {indicator.get('value')} - Tín hiệu: {indicator.get('signal')}")
            
            # Quét cơ hội giao dịch
            opportunities = self.market_analyzer.scan_trading_opportunities()
            
            if opportunities.get("status") == "success":
                logger.info(f"Số lượng cơ hội giao dịch: {opportunities.get('count')}")
                
                for i, opportunity in enumerate(opportunities.get("opportunities", [])[:3]):
                    logger.info(f"Cơ hội {i+1}: {opportunity.get('symbol')} {opportunity.get('signal')} - {opportunity.get('reason')}")
            else:
                logger.warning(f"Không thể quét cơ hội giao dịch: {opportunities.get('message', 'Lỗi không xác định')}")
            
            self.validation_results["technical_analysis"] = True
            logger.info("✅ Kiểm tra phân tích kỹ thuật thành công")
            return True
        
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra phân tích kỹ thuật: {str(e)}", exc_info=True)
            return False
    
    def validate_auto_update(self):
        """Kiểm tra chức năng cập nhật tự động"""
        try:
            logger.info("Kiểm tra chức năng cập nhật tự động...")
            
            # Kiểm tra phiên bản hiện tại
            current_version = self.auto_updater.get_current_version()
            
            logger.info(f"Phiên bản hiện tại: {current_version}")
            
            # Kiểm tra cập nhật
            has_update, new_version, update_info = self.auto_updater.check_for_updates()
            
            if has_update:
                logger.info(f"Phát hiện phiên bản mới: {new_version}")
                logger.info(f"Thông tin cập nhật: {update_info}")
            else:
                logger.info("Không có bản cập nhật mới")
            
            self.validation_results["auto_update"] = True
            logger.info("✅ Kiểm tra cập nhật tự động thành công")
            return True
        
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra cập nhật tự động: {str(e)}", exc_info=True)
            return False
    
    def validate_telegram_integration(self):
        """Kiểm tra tích hợp Telegram"""
        try:
            logger.info("Kiểm tra tích hợp Telegram...")
            
            # Kiểm tra thông tin Telegram
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            
            if not telegram_token or not telegram_chat_id:
                logger.warning("Thiếu thông tin Telegram, bỏ qua kiểm tra")
                return False
            
            # Thử gửi tin nhắn test
            import requests
            
            message = f"📱 Kiểm tra tin nhắn Telegram từ ứng dụng desktop - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            response = requests.get(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                params={"chat_id": telegram_chat_id, "text": message}
            )
            
            if response.status_code == 200:
                self.validation_results["telegram_integration"] = True
                logger.info("✅ Kiểm tra tích hợp Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi tin nhắn Telegram: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra tích hợp Telegram: {str(e)}", exc_info=True)
            return False
    
    def validate_all(self):
        """Kiểm tra tất cả chức năng"""
        logger.info("===== BẮT ĐẦU KIỂM TRA TOÀN DIỆN =====")
        
        # Khởi tạo các thành phần
        if not self.initialize_components():
            logger.error("❌ Không thể khởi tạo các thành phần, dừng kiểm tra")
            return False
        
        # Kiểm tra từng chức năng
        self.validate_api_connection()
        self.validate_market_data()
        self.validate_position_management()
        self.validate_risk_management()
        self.validate_technical_analysis()
        self.validate_auto_update()
        self.validate_telegram_integration()
        
        # Hiển thị kết quả kiểm tra
        logger.info("===== KẾT QUẢ KIỂM TRA =====")
        for name, result in self.validation_results.items():
            status = "✅ THÀNH CÔNG" if result else "❌ THẤT BẠI"
            logger.info(f"{name}: {status}")
        
        # Kiểm tra thành công nếu tất cả các thành phần chính đều hoạt động
        success = (
            self.validation_results["api_connection"] and
            self.validation_results["market_data"] and
            self.validation_results["position_management"] and
            self.validation_results["risk_management"] and
            self.validation_results["technical_analysis"]
        )
        
        if success:
            logger.info("✅✅✅ KIỂM TRA TOÀN DIỆN THÀNH CÔNG ✅✅✅")
        else:
            logger.error("❌❌❌ KIỂM TRA TOÀN DIỆN THẤT BẠI ❌❌❌")
        
        return success

if __name__ == "__main__":
    validator = DesktopAppValidator()
    validator.validate_all()