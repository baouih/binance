#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import logging
import threading
from typing import Dict, List, Any
from datetime import datetime

from market_analyzer import MarketAnalyzer
from position_manager import PositionManager
from risk_manager import RiskManager
from advanced_telegram_notifier import TelegramNotifier

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_scanner")

class MarketScanner:
    """
    Lớp quét thị trường để tìm kiếm các cơ hội giao dịch
    """
    def __init__(self, testnet=True):
        """
        Khởi tạo Market Scanner
        
        :param testnet: Sử dụng testnet hay không
        """
        self.testnet = testnet
        self.active = False
        self.scan_thread = None
        self.scan_interval = 300  # Quét mỗi 5 phút
        self.pairs_to_scan = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT", 
            "ADAUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT",
            "MATICUSDT", "LINKUSDT", "UNIUSDT", "ATOMUSDT", "VETUSDT"
        ]
        self.timeframes = ["15m", "1h", "4h"]  # Các khung thời gian cần quét
        self.min_score_threshold = 65  # Điểm số tối thiểu để gửi thông báo
        
        try:
            # Khởi tạo các đối tượng phân tích
            self.market_analyzer = MarketAnalyzer(testnet=testnet)
            self.position_manager = PositionManager(testnet=testnet)
            
            # Tải cấu hình từ file nếu có
            self.load_config()
            
            logger.info(f"Đã khởi tạo MarketScanner với {len(self.pairs_to_scan)} cặp và {len(self.timeframes)} khung thời gian")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo MarketScanner: {str(e)}", exc_info=True)
    
    def load_config(self):
        """Tải cấu hình từ file"""
        config_path = "configs/market_scanner_config.json"
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Cập nhật cấu hình
                self.pairs_to_scan = config.get("pairs_to_scan", self.pairs_to_scan)
                self.timeframes = config.get("timeframes", self.timeframes)
                self.scan_interval = config.get("scan_interval", self.scan_interval)
                self.min_score_threshold = config.get("min_score_threshold", self.min_score_threshold)
                
                logger.info(f"Đã tải cấu hình từ {config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}", exc_info=True)
    
    def save_config(self):
        """Lưu cấu hình vào file"""
        config_path = "configs/market_scanner_config.json"
        try:
            # Tạo thư mục configs nếu chưa tồn tại
            os.makedirs("configs", exist_ok=True)
            
            config = {
                "pairs_to_scan": self.pairs_to_scan,
                "timeframes": self.timeframes,
                "scan_interval": self.scan_interval,
                "min_score_threshold": self.min_score_threshold
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình vào {config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}", exc_info=True)
    
    def start_scanning(self):
        """Bắt đầu quét thị trường"""
        if self.scan_thread and self.scan_thread.is_alive():
            logger.warning("Đã có một luồng quét đang chạy")
            return False
        
        self.active = True
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        
        logger.info("Đã bắt đầu quét thị trường")
        return True
    
    def stop_scanning(self):
        """Dừng quét thị trường"""
        self.active = False
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=1.0)
        
        logger.info("Đã dừng quét thị trường")
        return True
    
    def _scan_loop(self):
        """Vòng lặp quét thị trường"""
        while self.active:
            try:
                logger.info("Bắt đầu quét thị trường...")
                scan_results = self.scan_market()
                
                # Xử lý kết quả quét
                self._process_scan_results(scan_results)
                
                # Lưu kết quả quét
                self._save_scan_results(scan_results)
                
                logger.info(f"Hoàn thành quét thị trường, sẽ quét lại sau {self.scan_interval} giây")
            except Exception as e:
                logger.error(f"Lỗi trong quá trình quét thị trường: {str(e)}", exc_info=True)
            
            # Chờ đến lần quét tiếp theo
            for _ in range(self.scan_interval):
                if not self.active:
                    break
                time.sleep(1)
    
    def scan_market(self) -> List[Dict[str, Any]]:
        """
        Quét thị trường cho tất cả các cặp và khung thời gian
        
        :return: Danh sách kết quả phân tích
        """
        results = []
        
        # Lặp qua từng cặp giao dịch
        for symbol in self.pairs_to_scan:
            for interval in self.timeframes:
                try:
                    # Phân tích kỹ thuật
                    analysis = self.market_analyzer.analyze_technical(symbol, interval)
                    
                    if analysis.get("status") == "success":
                        # Thêm thông tin thời gian
                        analysis["timestamp"] = datetime.now().isoformat()
                        analysis["symbol"] = symbol
                        analysis["interval"] = interval
                        
                        # Nếu tín hiệu đủ mạnh, thêm vào kết quả
                        score = analysis.get("score", 0)
                        if score >= self.min_score_threshold:
                            results.append(analysis)
                            logger.info(f"Đã tìm thấy tín hiệu mạnh cho {symbol} ({interval}): {analysis.get('overall_signal', 'N/A')} - Điểm số: {score}")
                    
                    # Đợi một chút để tránh vượt quá giới hạn API
                    time.sleep(0.5)
                
                except Exception as e:
                    logger.error(f"Lỗi khi phân tích {symbol} ({interval}): {str(e)}", exc_info=True)
        
        return results
    
    def _process_scan_results(self, results: List[Dict[str, Any]]):
        """
        Xử lý kết quả quét thị trường
        
        :param results: Danh sách kết quả phân tích
        """
        if not results:
            logger.info("Không tìm thấy cơ hội giao dịch nào")
            return
        
        # Sắp xếp kết quả theo điểm số
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Gửi thông báo về những cơ hội tốt nhất
        self._send_opportunity_notifications(results[:5])  # Top 5 cơ hội
    
    def _send_opportunity_notifications(self, opportunities: List[Dict[str, Any]]):
        """
        Gửi thông báo về các cơ hội giao dịch
        
        :param opportunities: Danh sách cơ hội giao dịch
        """
        if not opportunities:
            return
        
        # Tạo nội dung thông báo
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"🔍 PHÁT HIỆN CƠ HỘI GIAO DỊCH ({now})\n\n"
        
        for i, opportunity in enumerate(opportunities, 1):
            symbol = opportunity.get("symbol", "N/A")
            interval = opportunity.get("interval", "N/A")
            signal = opportunity.get("overall_signal", "N/A")
            score = opportunity.get("score", 0)
            price = opportunity.get("price", 0)
            
            # Xác định emoji dựa trên tín hiệu
            emoji = "🟢" if signal == "Mua" else "🔴" if signal == "Bán" else "⚪"
            
            message += f"{emoji} {i}. {symbol} ({interval})\n"
            message += f"   • Tín hiệu: {signal}\n"
            message += f"   • Độ tin cậy: {score:.0f}%\n"
            message += f"   • Giá hiện tại: {price:.2f} USDT\n"
            
            # Thêm thông tin về hỗ trợ/kháng cự
            support_resistance = opportunity.get("support_resistance", [])
            supports = [sr.get("value", 0) for sr in support_resistance if sr.get("type", "").lower() == "support"]
            resistances = [sr.get("value", 0) for sr in support_resistance if sr.get("type", "").lower() == "resistance"]
            
            if supports:
                message += f"   • Hỗ trợ: {min(supports):.2f}\n"
            
            if resistances:
                message += f"   • Kháng cự: {max(resistances):.2f}\n"
            
            message += "\n"
        
        # Gửi thông báo qua Telegram
        try:
            telegram = TelegramNotifier()
            telegram.send_message(message)
            logger.info(f"Đã gửi thông báo về {len(opportunities)} cơ hội giao dịch")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo: {str(e)}", exc_info=True)
    
    def _save_scan_results(self, results: List[Dict[str, Any]]):
        """
        Lưu kết quả quét thị trường
        
        :param results: Danh sách kết quả phân tích
        """
        if not results:
            return
        
        try:
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs("signal_analysis", exist_ok=True)
            
            # Tên file dựa trên thời gian
            filename = f"signal_analysis/market_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Lưu kết quả vào file
            with open(filename, 'w') as f:
                json.dump(results, f, indent=4)
            
            logger.info(f"Đã lưu kết quả quét thị trường vào {filename}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả quét: {str(e)}", exc_info=True)
    
    def get_latest_opportunities(self, max_count=10) -> List[Dict[str, Any]]:
        """
        Lấy các cơ hội giao dịch mới nhất
        
        :param max_count: Số lượng cơ hội tối đa
        :return: Danh sách cơ hội giao dịch
        """
        opportunities = []
        
        try:
            # Tìm file kết quả quét mới nhất
            signal_dir = "signal_analysis"
            if not os.path.exists(signal_dir):
                return []
            
            files = [os.path.join(signal_dir, f) for f in os.listdir(signal_dir) 
                    if f.startswith("market_scan_") and f.endswith(".json")]
            
            if not files:
                return []
            
            # Sắp xếp theo thời gian sửa đổi
            latest_file = max(files, key=os.path.getmtime)
            
            # Đọc file
            with open(latest_file, 'r') as f:
                opportunities = json.load(f)
            
            # Giới hạn số lượng kết quả
            opportunities = opportunities[:max_count]
            
            logger.info(f"Đã tải {len(opportunities)} cơ hội giao dịch từ {latest_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lấy cơ hội giao dịch mới nhất: {str(e)}", exc_info=True)
        
        return opportunities


# Singleton instance
_scanner_instance = None

def get_scanner(testnet=True):
    """Lấy singleton instance của MarketScanner"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = MarketScanner(testnet=testnet)
    return _scanner_instance


if __name__ == "__main__":
    # Test chương trình
    scanner = MarketScanner(testnet=True)
    scanner.start_scanning()
    
    try:
        # Để chương trình chạy trong 1 giờ
        time.sleep(3600)
    except KeyboardInterrupt:
        print("Dừng chương trình...")
    finally:
        scanner.stop_scanning()