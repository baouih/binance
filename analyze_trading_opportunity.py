#!/usr/bin/env python3
"""
Script phân tích cơ hội giao dịch cụ thể cho một cặp tiền

Script này phân tích chi tiết một cặp tiền được chỉ định, đưa ra:
1. Phân tích tổng thể thị trường
2. Phân tích kỹ thuật chi tiết
3. Xác định điểm vào/ra lệnh cụ thể
4. Lý do đánh hoặc không đánh (nếu không đánh)
5. Tạo báo cáo phân tích và biểu đồ

Cách sử dụng:
    python analyze_trading_opportunity.py --symbol BTCUSDT --timeframe 1h
"""

import os
import sys
import json
import argparse
import logging
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any, Union
from market_analysis_system import MarketAnalysisSystem
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("trade_opportunity_analyzer")

class TradingOpportunityAnalyzer:
    """Phân tích cơ hội giao dịch cho một cặp tiền cụ thể"""
    
    def __init__(self):
        """Khởi tạo phân tích cơ hội giao dịch"""
        self.analyzer = MarketAnalysisSystem()
        # Đảm bảo thư mục tồn tại
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Tạo các thư mục cần thiết"""
        directories = [
            "reports/trade_analysis",
            "charts/trade_analysis"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Đã tạo thư mục: {directory}")
    
    def analyze_opportunity(self, symbol: str, timeframe: str = None, direction: str = None) -> Dict:
        """
        Phân tích chi tiết cơ hội giao dịch
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str, optional): Khung thời gian, mặc định là primary_timeframe
            direction (str, optional): Hướng giao dịch ('long', 'short', hoặc None)
            
        Returns:
            Dict: Kết quả phân tích
        """
        logger.info(f"Bắt đầu phân tích chi tiết cơ hội giao dịch cho {symbol}")
        
        # Phân tích thị trường toàn cầu
        global_market = self.analyzer.analyze_global_market()
        
        # Phân tích cặp tiền trên nhiều khung thời gian
        timeframes = self.analyzer.config["timeframes"]
        if timeframe is None:
            timeframe = self.analyzer.config["primary_timeframe"]
        
        # Đảm bảo timeframe được chỉ định nằm trong danh sách
        if timeframe not in timeframes:
            timeframes.append(timeframe)
        
        multi_timeframe_analysis = {}
        for tf in timeframes:
            multi_timeframe_analysis[tf] = self.analyzer.analyze_symbol(symbol, tf)
        
        # Phân tích chính trên timeframe được chỉ định
        primary_analysis = multi_timeframe_analysis[timeframe]
        
        # Kiểm tra điều kiện giao dịch
        can_trade, no_trade_reasons = self.analyzer.check_trading_conditions(symbol, timeframe, direction)
        
        # Tổng hợp kết quả
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "global_market": global_market,
            "primary_analysis": primary_analysis,
            "multi_timeframe_analysis": multi_timeframe_analysis,
            "can_trade": can_trade,
            "no_trade_reasons": no_trade_reasons,
            "trading_recommendation": self._generate_recommendation(primary_analysis, global_market, can_trade, no_trade_reasons)
        }
        
        # Tạo báo cáo và biểu đồ
        self._save_report(result)
        
        logger.info(f"Hoàn thành phân tích cơ hội giao dịch cho {symbol}")
        return result
    
    def _generate_recommendation(self, analysis: Dict, global_market: Dict, can_trade: bool, no_trade_reasons: List) -> Dict:
        """
        Tạo khuyến nghị giao dịch
        
        Args:
            analysis (Dict): Kết quả phân tích
            global_market (Dict): Phân tích thị trường toàn cầu
            can_trade (bool): Có thể giao dịch không
            no_trade_reasons (List): Lý do không giao dịch
            
        Returns:
            Dict: Khuyến nghị giao dịch
        """
        symbol = analysis["symbol"]
        current_price = analysis["price"]["current"]
        
        # Xác định hướng giao dịch
        direction = None
        if analysis["score"] >= 60:
            direction = "long"
        elif analysis["score"] <= 40:
            direction = "short"
        
        # Kết quả khuyến nghị
        recommendation = {
            "action": "no_trade",  # Mặc định: không giao dịch
            "direction": direction,
            "reasons": [],
            "entry_price": current_price,
            "entry_range": [],
            "stop_loss": None,
            "take_profit": None,
            "risk_reward_ratio": 0,
            "time_to_enter": "immediately",
            "notes": []
        }
        
        # Nếu không thể giao dịch, trả về lý do
        if not can_trade:
            recommendation["reasons"] = [reason["reason"] for reason in no_trade_reasons]
            return recommendation
        
        # Nếu không có hướng rõ ràng
        if direction is None:
            recommendation["reasons"].append(f"Không có tín hiệu giao dịch rõ ràng (điểm: {analysis['score']})")
            return recommendation
        
        # Hướng dẫn giao dịch cụ thể
        entry_exit = analysis["entry_exit_points"][direction]
        entry_points = entry_exit["entry_points"]
        take_profit_points = entry_exit["exit_points"]["take_profit"]
        stop_loss_points = entry_exit["exit_points"]["stop_loss"]
        
        if not entry_points or not take_profit_points or not stop_loss_points:
            recommendation["reasons"].append("Thiếu điểm vào hoặc điểm ra")
            return recommendation
        
        # Có thể giao dịch
        recommendation["action"] = "trade"
        recommendation["reasons"] = entry_exit["reasoning"]
        
        # Điểm vào
        recommendation["entry_price"] = entry_points[0]
        
        # Dải giá vào (buffer +/- 0.5%)
        price_buffer = entry_points[0] * 0.005
        recommendation["entry_range"] = [entry_points[0] - price_buffer, entry_points[0] + price_buffer]
        
        # Điểm ra
        recommendation["stop_loss"] = stop_loss_points[0]
        recommendation["take_profit"] = take_profit_points[0]
        
        # Tính R:R
        if direction == "long":
            risk = entry_points[0] - stop_loss_points[0]
            reward = take_profit_points[0] - entry_points[0]
        else:  # short
            risk = stop_loss_points[0] - entry_points[0]
            reward = entry_points[0] - take_profit_points[0]
        
        if risk > 0:
            recommendation["risk_reward_ratio"] = reward / risk
        
        # Thêm ghi chú
        if global_market["market_regime"] == "high_volatility":
            recommendation["notes"].append("Thị trường biến động cao, hãy cẩn trọng và xem xét giảm kích thước vị thế")
        
        if direction == "long" and global_market["market_trend"] == "bearish":
            recommendation["notes"].append("Giao dịch trái xu hướng thị trường, hãy cẩn trọng")
        elif direction == "short" and global_market["market_trend"] == "bullish":
            recommendation["notes"].append("Giao dịch trái xu hướng thị trường, hãy cẩn trọng")
        
        # Gợi ý thời điểm vào lệnh
        if direction == "long" and current_price > entry_points[0]:
            recommendation["time_to_enter"] = "wait_for_pullback"
        elif direction == "short" and current_price < entry_points[0]:
            recommendation["time_to_enter"] = "wait_for_bounce"
        
        return recommendation
    
    def _save_report(self, analysis_result: Dict) -> str:
        """
        Lưu báo cáo phân tích
        
        Args:
            analysis_result (Dict): Kết quả phân tích
            
        Returns:
            str: Đường dẫn đến báo cáo
        """
        symbol = analysis_result["symbol"]
        timeframe = analysis_result["timeframe"]
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Tạo tên file
        report_filename = f"reports/trade_analysis/{symbol}_{timeframe}_{timestamp}.json"
        
        # Lưu file JSON
        try:
            with open(report_filename, 'w') as f:
                json.dump(analysis_result, f, indent=4)
            
            logger.info(f"Đã lưu báo cáo phân tích tại {report_filename}")
            return report_filename
        except Exception as e:
            logger.error(f"Lỗi khi lưu báo cáo phân tích: {str(e)}")
            return ""
    
    def print_analysis_summary(self, analysis_result: Dict) -> None:
        """
        In tóm tắt phân tích ra console
        
        Args:
            analysis_result (Dict): Kết quả phân tích
        """
        symbol = analysis_result["symbol"]
        timeframe = analysis_result["timeframe"]
        primary_analysis = analysis_result["primary_analysis"]
        global_market = analysis_result["global_market"]
        recommendation = analysis_result["trading_recommendation"]
        
        print("\n" + "="*80)
        print(f"PHÂN TÍCH CƠ HỘI GIAO DỊCH: {symbol} - {timeframe}")
        print("="*80)
        
        # Thông tin chung
        print(f"\nNgày: {analysis_result['timestamp']}")
        print(f"Giá hiện tại: {primary_analysis['price']['current']:.4f}")
        print(f"Điểm đánh giá: {primary_analysis['score']}/100")
        print(f"Khuyến nghị: {primary_analysis['recommendation'].upper()}")
        
        # Thông tin thị trường
        print("\n" + "-"*80)
        print("PHÂN TÍCH THỊ TRƯỜNG TOÀN CẦU")
        print("-"*80)
        print(f"Xu hướng thị trường: {global_market['market_trend'].upper()}")
        print(f"Chế độ thị trường: {global_market['market_regime'].upper()}")
        print(f"Giá Bitcoin: ${global_market['btc_price']:.2f}")
        
        # Phân tích đa khung thời gian
        print("\n" + "-"*80)
        print("PHÂN TÍCH ĐA KHUNG THỜI GIAN")
        print("-"*80)
        
        mtf_data = []
        for tf, analysis in analysis_result["multi_timeframe_analysis"].items():
            mtf_data.append([
                tf,
                analysis.get("score", 0),
                analysis.get("recommendation", "unknown").upper(),
                analysis.get("market_regime", "unknown")
            ])
        
        print(tabulate(mtf_data, headers=["Timeframe", "Điểm", "Khuyến nghị", "Chế độ thị trường"], tablefmt="grid"))
        
        # Các chỉ báo kỹ thuật
        print("\n" + "-"*80)
        print("CÁC CHỈ BÁO KỸ THUẬT")
        print("-"*80)
        
        # Moving Averages
        if "indicators" in primary_analysis and "moving_averages" in primary_analysis["indicators"]:
            ma_data = []
            for ma_name, ma_value in primary_analysis["indicators"]["moving_averages"].items():
                ma_data.append([ma_name, ma_value])
            
            if ma_data:
                print("\nMoving Averages:")
                print(tabulate(ma_data, headers=["Chỉ báo", "Giá trị"], tablefmt="grid"))
        
        # Oscillators
        if "indicators" in primary_analysis and "oscillators" in primary_analysis["indicators"]:
            oscil_data = []
            
            oscillators = primary_analysis["indicators"]["oscillators"]
            if "rsi" in oscillators:
                oscil_data.append(["RSI", oscillators["rsi"]])
            
            if "macd" in oscillators:
                macd = oscillators["macd"]
                oscil_data.append(["MACD", macd["macd"]])
                oscil_data.append(["MACD Signal", macd["signal"]])
                oscil_data.append(["MACD Histogram", macd["histogram"]])
            
            if "stochastic" in oscillators:
                stoch = oscillators["stochastic"]
                oscil_data.append(["Stoch %K", stoch["k"]])
                oscil_data.append(["Stoch %D", stoch["d"]])
            
            if oscil_data:
                print("\nOscillators:")
                print(tabulate(oscil_data, headers=["Chỉ báo", "Giá trị"], tablefmt="grid"))
        
        # Volatility Indicators
        if "indicators" in primary_analysis and "volatility" in primary_analysis["indicators"]:
            vol_data = []
            
            volatility = primary_analysis["indicators"]["volatility"]
            if "atr" in volatility:
                vol_data.append(["ATR", volatility["atr"]])
                vol_data.append(["ATR %", volatility.get("atr_percent", 0)])
            
            if "bollinger_bands" in volatility:
                bb = volatility["bollinger_bands"]
                vol_data.append(["BB Upper", bb["upper"]])
                vol_data.append(["BB Middle", bb["middle"]])
                vol_data.append(["BB Lower", bb["lower"]])
                vol_data.append(["BB Width", bb["width"]])
            
            if vol_data:
                print("\nVolatility Indicators:")
                print(tabulate(vol_data, headers=["Chỉ báo", "Giá trị"], tablefmt="grid"))
        
        # Support/Resistance
        if "support_resistance" in primary_analysis:
            sr = primary_analysis["support_resistance"]
            print("\nSupport/Resistance:")
            
            # Resistance Levels
            if "resistance_levels" in sr and sr["resistance_levels"]:
                resistance_levels = sorted(sr["resistance_levels"])[:3]  # Top 3 resistance levels
                print(f"Top Resistance Levels: {', '.join([f'{level:.4f}' for level in resistance_levels])}")
            
            # Support Levels
            if "support_levels" in sr and sr["support_levels"]:
                support_levels = sorted(sr["support_levels"], reverse=True)[:3]  # Top 3 support levels
                print(f"Top Support Levels: {', '.join([f'{level:.4f}' for level in support_levels])}")
        
        # Khuyến nghị giao dịch
        print("\n" + "-"*80)
        print("KHUYẾN NGHỊ GIAO DỊCH")
        print("-"*80)
        
        if recommendation["action"] == "trade":
            direction_text = "LONG" if recommendation["direction"] == "long" else "SHORT"
            print(f"Đề xuất: {direction_text}")
            print(f"Giá vào: {recommendation['entry_price']:.4f}")
            print(f"Dải giá vào: {recommendation['entry_range'][0]:.4f} - {recommendation['entry_range'][1]:.4f}")
            print(f"Stop Loss: {recommendation['stop_loss']:.4f}")
            print(f"Take Profit: {recommendation['take_profit']:.4f}")
            print(f"Tỷ lệ Risk:Reward: 1:{recommendation['risk_reward_ratio']:.2f}")
            print(f"Thời điểm vào lệnh: {recommendation['time_to_enter']}")
            
            print("\nLý do:")
            for i, reason in enumerate(recommendation["reasons"], 1):
                print(f"  {i}. {reason}")
            
            if recommendation["notes"]:
                print("\nLưu ý:")
                for i, note in enumerate(recommendation["notes"], 1):
                    print(f"  {i}. {note}")
        else:
            print("Đề xuất: KHÔNG GIAO DỊCH")
            print("\nLý do:")
            for i, reason in enumerate(recommendation["reasons"], 1):
                print(f"  {i}. {reason}")
        
        print("\n" + "="*80)
        print(f"Báo cáo chi tiết được lưu trong thư mục reports/trade_analysis/")
        print("="*80 + "\n")

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Phân tích cơ hội giao dịch chi tiết")
    parser.add_argument("--symbol", type=str, required=True, help="Mã cặp tiền (ví dụ: BTCUSDT)")
    parser.add_argument("--timeframe", type=str, default=None, help="Khung thời gian (ví dụ: 1h, 4h, 1d)")
    parser.add_argument("--direction", type=str, choices=["long", "short"], default=None, help="Hướng giao dịch")
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    print(f"\nĐang phân tích chi tiết {args.symbol} trên khung {args.timeframe or 'mặc định'}...")
    
    analyzer = TradingOpportunityAnalyzer()
    result = analyzer.analyze_opportunity(args.symbol, args.timeframe, args.direction)
    
    # In kết quả
    analyzer.print_analysis_summary(result)

if __name__ == "__main__":
    main()