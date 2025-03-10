#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tạo tín hiệu giao dịch
"""

import os
import logging
import json
import traceback
from datetime import datetime, timedelta

# Cấu hình logging
logger = logging.getLogger("signal_generator")

class SignalGenerator:
    """
    Lớp tạo tín hiệu giao dịch dựa trên các chiến lược khác nhau
    """
    
    def __init__(self, market_analyzer, config=None):
        """
        Khởi tạo với market analyzer và cấu hình
        
        :param market_analyzer: Đối tượng MarketAnalyzer
        :param config: Dict cấu hình
        """
        self.market_analyzer = market_analyzer
        self.config = config or {}
        self.last_signals = {}  # Lưu trữ tín hiệu gần đây
    
    def generate_signals(self, symbols=None, timeframes=None):
        """
        Tạo tín hiệu giao dịch cho các cặp tiền và khung thời gian
        
        :param symbols: List các cặp tiền, ví dụ ["BTCUSDT", "ETHUSDT"]
        :param timeframes: List các khung thời gian, ví dụ ["1h", "4h"]
        :return: List các tín hiệu giao dịch
        """
        if not symbols:
            symbols = self.config.get("symbols", ["BTCUSDT", "ETHUSDT"])
        
        if not timeframes:
            timeframes = self.config.get("timeframes", ["1h", "4h"])
        
        signals = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    # Phân tích kỹ thuật
                    analysis = self.market_analyzer.analyze_technical(symbol, timeframe)
                    
                    if analysis["status"] != "success":
                        logger.warning(f"Không thể phân tích {symbol} trên khung thời gian {timeframe}: {analysis.get('message', 'Unknown error')}")
                        continue
                    
                    # Tính signal_key để kiểm tra tín hiệu trùng lặp
                    signal_key = f"{symbol}_{timeframe}"
                    
                    # Tạo tín hiệu dựa trên kết quả phân tích
                    if analysis["overall_signal"] in ["Mua", "Bán"]:
                        # Kiểm tra xem đã có tín hiệu tương tự chưa
                        if signal_key in self.last_signals:
                            last_signal = self.last_signals[signal_key]
                            
                            # Nếu đã có tín hiệu tương tự trong vòng 6 giờ, bỏ qua
                            time_diff = datetime.now() - last_signal["timestamp"]
                            if time_diff < timedelta(hours=6) and last_signal["side"] == analysis["overall_signal"]:
                                logger.info(f"Bỏ qua tín hiệu trùng lặp cho {symbol} ({timeframe}): {analysis['overall_signal']}")
                                continue
                        
                        # Đánh giá độ tin cậy dựa trên strength
                        confidence = 50  # Mặc định
                        if analysis["strength"] == "Mạnh":
                            confidence = 75
                        elif analysis["strength"] == "Trung bình":
                            confidence = 60
                        elif analysis["strength"] == "Yếu":
                            confidence = 40
                        
                        # Tính toán giá vào, SL, TP
                        current_price = analysis["price"]
                        
                        # Tính toán SL/TP tùy thuộc vào tín hiệu
                        if analysis["overall_signal"] == "Mua":
                            side = "LONG"
                            # Tính SL, TP dựa trên BB
                            bb_indicator = next((ind for ind in analysis["indicators"] if ind["name"] == "Bollinger Bands"), None)
                            if bb_indicator:
                                # Trích xuất giá trị BB lower từ chuỗi
                                bb_values = bb_indicator["value"].split(", ")
                                bb_lower = float(bb_values[1].split(": ")[1]) if len(bb_values) > 1 else current_price * 0.97
                                
                                # Tính SL dựa trên BB lower hoặc % mặc định
                                stop_loss = min(bb_lower, current_price * 0.97)
                                
                                # Tính TP với tỷ lệ R:R = 1:2
                                sl_distance = current_price - stop_loss
                                take_profit = current_price + (sl_distance * 2)
                            else:
                                # Fallback nếu không có BB
                                stop_loss = current_price * 0.97
                                take_profit = current_price * 1.06
                        else:  # BÁN
                            side = "SHORT"
                            # Tính SL, TP dựa trên BB
                            bb_indicator = next((ind for ind in analysis["indicators"] if ind["name"] == "Bollinger Bands"), None)
                            if bb_indicator:
                                # Trích xuất giá trị BB upper từ chuỗi
                                bb_values = bb_indicator["value"].split(", ")
                                bb_upper = float(bb_values[0].split(": ")[1]) if len(bb_values) > 0 else current_price * 1.03
                                
                                # Tính SL dựa trên BB upper hoặc % mặc định
                                stop_loss = max(bb_upper, current_price * 1.03)
                                
                                # Tính TP với tỷ lệ R:R = 1:2
                                sl_distance = stop_loss - current_price
                                take_profit = current_price - (sl_distance * 2)
                            else:
                                # Fallback nếu không có BB
                                stop_loss = current_price * 1.03
                                take_profit = current_price * 0.94
                        
                        # Tạo tín hiệu
                        signal = {
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "side": side,
                            "entry_price": current_price,
                            "stop_loss": stop_loss,
                            "take_profit": take_profit,
                            "confidence": confidence,
                            "strategy": "Composite Strategy",
                            "timestamp": datetime.now(),
                            "indicators": analysis["indicators"]
                        }
                        
                        # Lưu tín hiệu vào last_signals
                        self.last_signals[signal_key] = {
                            "side": analysis["overall_signal"],
                            "timestamp": datetime.now()
                        }
                        
                        signals.append(signal)
                
                except Exception as e:
                    logger.error(f"Lỗi khi tạo tín hiệu cho {symbol} ({timeframe}): {str(e)}")
                    logger.error(traceback.format_exc())
        
        return signals
    
    def get_current_signals(self):
        """
        Lấy các tín hiệu hiện tại
        
        :return: List các tín hiệu giao dịch
        """
        symbols = self.config.get("symbols", ["BTCUSDT", "ETHUSDT"])
        timeframes = self.config.get("timeframes", ["1h", "4h"])
        
        return self.generate_signals(symbols, timeframes)
    
    def get_best_signal(self):
        """
        Lấy tín hiệu tốt nhất hiện tại
        
        :return: Dict tín hiệu giao dịch tốt nhất hoặc None
        """
        signals = self.get_current_signals()
        
        if not signals:
            return None
        
        # Sắp xếp tín hiệu theo độ tin cậy giảm dần
        signals.sort(key=lambda x: x["confidence"], reverse=True)
        
        return signals[0]
    
    def validate_signal(self, signal):
        """
        Kiểm tra tính hợp lệ của tín hiệu
        
        :param signal: Dict tín hiệu giao dịch
        :return: Tuple (is_valid, reason)
        """
        if not signal:
            return (False, "Tín hiệu không tồn tại")
        
        # Kiểm tra các thông tin bắt buộc
        required_fields = ["symbol", "side", "entry_price", "stop_loss", "take_profit"]
        for field in required_fields:
            if field not in signal:
                return (False, f"Thiếu trường {field}")
        
        # Kiểm tra giá trị hợp lý
        if signal["side"] not in ["LONG", "SHORT"]:
            return (False, f"Hướng giao dịch không hợp lệ: {signal['side']}")
        
        if signal["entry_price"] <= 0:
            return (False, f"Giá vào lệnh không hợp lệ: {signal['entry_price']}")
        
        if signal["stop_loss"] <= 0 or signal["take_profit"] <= 0:
            return (False, f"SL/TP không hợp lệ: SL={signal['stop_loss']}, TP={signal['take_profit']}")
        
        # Kiểm tra SL/TP
        if signal["side"] == "LONG":
            if signal["stop_loss"] >= signal["entry_price"]:
                return (False, f"SL phải nhỏ hơn giá vào với lệnh LONG: SL={signal['stop_loss']}, Entry={signal['entry_price']}")
            
            if signal["take_profit"] <= signal["entry_price"]:
                return (False, f"TP phải lớn hơn giá vào với lệnh LONG: TP={signal['take_profit']}, Entry={signal['entry_price']}")
        else:  # SHORT
            if signal["stop_loss"] <= signal["entry_price"]:
                return (False, f"SL phải lớn hơn giá vào với lệnh SHORT: SL={signal['stop_loss']}, Entry={signal['entry_price']}")
            
            if signal["take_profit"] >= signal["entry_price"]:
                return (False, f"TP phải nhỏ hơn giá vào với lệnh SHORT: TP={signal['take_profit']}, Entry={signal['entry_price']}")
        
        return (True, "Tín hiệu hợp lệ")

# Hàm để thử nghiệm module
def test_signal_generator():
    """Hàm kiểm tra chức năng của SignalGenerator"""
    # Cấu hình logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        from market_analyzer import MarketAnalyzer
        
        # Khởi tạo market analyzer
        market_analyzer = MarketAnalyzer(testnet=True)
        
        # Khởi tạo signal generator
        config = {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1h", "4h"]
        }
        signal_generator = SignalGenerator(market_analyzer, config)
        
        # Lấy tín hiệu
        signals = signal_generator.get_current_signals()
        
        print(f"Đã tìm thấy {len(signals)} tín hiệu")
        
        for i, signal in enumerate(signals):
            print(f"\nTín hiệu #{i+1}:")
            print(f"  - Cặp: {signal['symbol']}")
            print(f"  - Khung thời gian: {signal['timeframe']}")
            print(f"  - Hướng: {signal['side']}")
            print(f"  - Giá vào: {signal['entry_price']:.2f}")
            print(f"  - Stop Loss: {signal['stop_loss']:.2f}")
            print(f"  - Take Profit: {signal['take_profit']:.2f}")
            print(f"  - Độ tin cậy: {signal['confidence']}%")
            print(f"  - Chiến lược: {signal['strategy']}")
            print(f"  - Thời gian: {signal['timestamp']}")
            
            # Kiểm tra tính hợp lệ
            is_valid, reason = signal_generator.validate_signal(signal)
            print(f"  - Hợp lệ: {is_valid} ({reason})")
        
        # Lấy tín hiệu tốt nhất
        best_signal = signal_generator.get_best_signal()
        if best_signal:
            print("\nTín hiệu tốt nhất:")
            print(f"  - Cặp: {best_signal['symbol']}")
            print(f"  - Khung thời gian: {best_signal['timeframe']}")
            print(f"  - Hướng: {best_signal['side']}")
            print(f"  - Giá vào: {best_signal['entry_price']:.2f}")
            print(f"  - Độ tin cậy: {best_signal['confidence']}%")
        else:
            print("\nKhông tìm thấy tín hiệu tốt nhất")
    
    except Exception as e:
        print(f"Lỗi khi test SignalGenerator: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_signal_generator()