#!/usr/bin/env python3
"""
Script phân tích chi tiết lý do không đánh một crypto cụ thể

Script này cung cấp phân tích chi tiết về lý do không giao dịch một cặp tiền,
giúp người dùng hiểu tại sao hệ thống không khuyến nghị giao dịch mặc dù
đã được phân tích kỹ thuật. Script này cũng gợi ý các điều kiện cần thiết
để thực hiện giao dịch trong tương lai.

Cách sử dụng:
    python analyze_no_trade_reasons.py --symbol BTCUSDT --timeframe 1h
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
logger = logging.getLogger("no_trade_reasons_analyzer")

class NoTradeReasonsAnalyzer:
    """Phân tích chi tiết lý do không giao dịch"""
    
    def __init__(self):
        """Khởi tạo phân tích"""
        self.analyzer = MarketAnalysisSystem()
        # Đảm bảo thư mục tồn tại
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Tạo các thư mục cần thiết"""
        directories = [
            "reports/no_trade_analysis",
            "charts/no_trade_analysis"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Đã tạo thư mục: {directory}")
    
    def analyze_both_directions(self, symbol: str, timeframe: str = None) -> Dict:
        """
        Phân tích lý do không giao dịch cho cả hai hướng
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str, optional): Khung thời gian
            
        Returns:
            Dict: Kết quả phân tích
        """
        if timeframe is None:
            timeframe = self.analyzer.config["primary_timeframe"]
        
        logger.info(f"Phân tích lý do không giao dịch cho {symbol} trên khung {timeframe}")
        
        # Phân tích chi tiết
        long_result = self.analyze_no_trade_reasons(symbol, timeframe, "long")
        short_result = self.analyze_no_trade_reasons(symbol, timeframe, "short")
        
        # Tổng hợp kết quả
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "long_analysis": long_result,
            "short_analysis": short_result,
            "suggestion": self._generate_suggestion(long_result, short_result)
        }
        
        # Lưu báo cáo
        self._save_report(result)
        
        logger.info(f"Hoàn thành phân tích lý do không giao dịch cho {symbol}")
        return result
    
    def analyze_no_trade_reasons(self, symbol: str, timeframe: str = None, direction: str = "long") -> Dict:
        """
        Phân tích chi tiết lý do không giao dịch
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str, optional): Khung thời gian
            direction (str): Hướng giao dịch ('long' hoặc 'short')
            
        Returns:
            Dict: Kết quả phân tích
        """
        if timeframe is None:
            timeframe = self.analyzer.config["primary_timeframe"]
        
        logger.info(f"Phân tích lý do không giao dịch {direction.upper()} cho {symbol}")
        
        # Phân tích cặp tiền
        analysis = self.analyzer.analyze_symbol(symbol, timeframe)
        
        # Kiểm tra điều kiện giao dịch
        can_trade, no_trade_reasons = self.analyzer.check_trading_conditions(symbol, timeframe, direction)
        
        # Phân tích thị trường toàn cầu
        global_market = self.analyzer.analyze_global_market()
        
        # Kiểm tra lịch sử lý do không giao dịch
        historical_reasons = self._get_historical_reasons(symbol, timeframe, direction)
        
        # Lấy điểm cặp tiền
        entry_exit = analysis.get("entry_exit_points", {})
        direction_score = entry_exit.get("score", {}).get(direction, 0)
        
        # Xác định ngưỡng thông số cho giao dịch
        thresholds = {
            "rsi": {
                "long": {"min": None, "max": 30},  # RSI < 30 cho long
                "short": {"min": 70, "max": None}  # RSI > 70 cho short
            },
            "volatility": {
                "min": 1.0,  # Biến động tối thiểu 1%
                "max": 5.0   # Biến động tối đa 5%
            }
        }
        
        # Tìm các thông số hiện tại
        current_stats = {}
        
        # RSI
        if "indicators" in analysis and "oscillators" in analysis["indicators"] and "rsi" in analysis["indicators"]["oscillators"]:
            current_stats["rsi"] = analysis["indicators"]["oscillators"]["rsi"]
        
        # Biến động
        current_stats["volatility"] = analysis.get("volatility", 0)
        
        # MACD
        if "indicators" in analysis and "oscillators" in analysis["indicators"] and "macd" in analysis["indicators"]["oscillators"]:
            macd = analysis["indicators"]["oscillators"]["macd"]
            current_stats["macd"] = macd["macd"]
            current_stats["macd_signal"] = macd["signal"]
            current_stats["macd_histogram"] = macd["histogram"]
        
        # Bollinger Bands
        if "indicators" in analysis and "volatility" in analysis["indicators"] and "bollinger_bands" in analysis["indicators"]["volatility"]:
            bb = analysis["indicators"]["volatility"]["bollinger_bands"]
            current_stats["bb_width"] = bb["width"]
            current_stats["bb_upper"] = bb["upper"]
            current_stats["bb_middle"] = bb["middle"]
            current_stats["bb_lower"] = bb["lower"]
        
        # Tổng hợp kết quả
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "can_trade": can_trade,
            "score": direction_score,
            "current_price": analysis["price"]["current"],
            "no_trade_reasons": no_trade_reasons,
            "historical_reasons": historical_reasons,
            "current_stats": current_stats,
            "thresholds": thresholds,
            "global_market": global_market,
            "required_conditions": self._generate_required_conditions(direction, analysis, no_trade_reasons, thresholds, current_stats)
        }
        
        logger.info(f"Phát hiện {len(no_trade_reasons)} lý do không giao dịch {direction} cho {symbol}")
        return result
    
    def _get_historical_reasons(self, symbol: str, timeframe: str, direction: str) -> List[Dict]:
        """
        Lấy lịch sử lý do không giao dịch
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            direction (str): Hướng giao dịch
            
        Returns:
            List[Dict]: Lịch sử lý do không giao dịch
        """
        try:
            historical_reasons = []
            
            for entry in self.analyzer.no_trade_reasons:
                if entry.get("symbol") == symbol and entry.get("timeframe") == timeframe:
                    # Lọc lý do theo hướng nếu có
                    if direction == "long":
                        # Lọc lý do liên quan đến long
                        reasons = [r for r in entry.get("reasons", []) if "long" in r.get("reason", "").lower()]
                        if reasons:
                            historical_reasons.append({
                                "timestamp": entry.get("timestamp"),
                                "price": entry.get("price"),
                                "reasons": reasons
                            })
                    elif direction == "short":
                        # Lọc lý do liên quan đến short
                        reasons = [r for r in entry.get("reasons", []) if "short" in r.get("reason", "").lower()]
                        if reasons:
                            historical_reasons.append({
                                "timestamp": entry.get("timestamp"),
                                "price": entry.get("price"),
                                "reasons": reasons
                            })
                    else:
                        # Nếu không xác định hướng, lấy tất cả
                        historical_reasons.append({
                            "timestamp": entry.get("timestamp"),
                            "price": entry.get("price"),
                            "reasons": entry.get("reasons", [])
                        })
            
            # Giới hạn 10 bản ghi gần nhất
            return historical_reasons[-10:] if len(historical_reasons) > 10 else historical_reasons
        except Exception as e:
            logger.error(f"Lỗi khi lấy lịch sử lý do không giao dịch: {str(e)}")
            return []
    
    def _generate_required_conditions(self, direction: str, analysis: Dict, no_trade_reasons: List[Dict], thresholds: Dict, current_stats: Dict) -> List[Dict]:
        """
        Tạo danh sách các điều kiện cần thiết để giao dịch
        
        Args:
            direction (str): Hướng giao dịch
            analysis (Dict): Kết quả phân tích
            no_trade_reasons (List[Dict]): Danh sách lý do không giao dịch
            thresholds (Dict): Ngưỡng thông số
            current_stats (Dict): Thông số hiện tại
            
        Returns:
            List[Dict]: Danh sách điều kiện cần thiết
        """
        required_conditions = []
        
        # Xem xét các lý do không giao dịch
        for reason in no_trade_reasons:
            reason_text = reason.get("reason", "")
            category = reason.get("category", "")
            
            # Điểm số quá thấp
            if "điểm" in reason_text.lower() and "thấp" in reason_text.lower():
                required_conditions.append({
                    "condition": f"Tăng điểm {direction} (hiện tại: {analysis['entry_exit_points']['score'][direction]})",
                    "description": f"Cần đạt ít nhất 60 điểm để xem xét giao dịch",
                    "target_value": "≥ 60",
                    "current_value": str(analysis['entry_exit_points']['score'][direction])
                })
            
            # Thiếu điểm vào
            if "không có điểm vào" in reason_text.lower():
                required_conditions.append({
                    "condition": "Xác định điểm vào rõ ràng",
                    "description": f"Cần có điểm vào rõ ràng dựa trên các mức hỗ trợ/kháng cự hoặc tín hiệu kỹ thuật",
                    "target_value": "Có điểm vào cụ thể",
                    "current_value": "Không có"
                })
            
            # Thiếu điểm ra
            if "thiếu điểm take profit" in reason_text.lower() or "thiếu điểm stop loss" in reason_text.lower():
                required_conditions.append({
                    "condition": "Xác định điểm TP/SL rõ ràng",
                    "description": f"Cần có điểm Take Profit và Stop Loss rõ ràng",
                    "target_value": "Có TP/SL cụ thể",
                    "current_value": "Không đủ"
                })
            
            # Chế độ thị trường không phù hợp
            if category == "market_conditions":
                if direction == "long" and "không nên mua" in reason_text.lower():
                    required_conditions.append({
                        "condition": "Chờ thị trường chuyển xu hướng tăng",
                        "description": f"Thị trường hiện đang {analysis.get('market_regime', 'unknown')}, không phù hợp cho LONG",
                        "target_value": "trending_up, ranging",
                        "current_value": analysis.get('market_regime', 'unknown')
                    })
                elif direction == "short" and "không nên bán" in reason_text.lower():
                    required_conditions.append({
                        "condition": "Chờ thị trường chuyển xu hướng giảm",
                        "description": f"Thị trường hiện đang {analysis.get('market_regime', 'unknown')}, không phù hợp cho SHORT",
                        "target_value": "trending_down, ranging",
                        "current_value": analysis.get('market_regime', 'unknown')
                    })
            
            # Biến động quá cao
            if category == "volatility" and "biến động quá cao" in reason_text.lower():
                if "volatility" in current_stats:
                    required_conditions.append({
                        "condition": "Chờ biến động thị trường giảm",
                        "description": f"Biến động hiện tại quá cao ({current_stats['volatility']:.2f}%)",
                        "target_value": f"< {thresholds['volatility']['max']}%",
                        "current_value": f"{current_stats['volatility']:.2f}%"
                    })
        
        # Kiểm tra RSI
        if "rsi" in current_stats:
            rsi_value = current_stats["rsi"]
            
            if direction == "long" and thresholds["rsi"]["long"]["max"] is not None and rsi_value > thresholds["rsi"]["long"]["max"]:
                required_conditions.append({
                    "condition": "Chờ RSI giảm",
                    "description": f"RSI hiện tại ({rsi_value:.2f}) cao hơn ngưỡng cho LONG",
                    "target_value": f"< {thresholds['rsi']['long']['max']}",
                    "current_value": f"{rsi_value:.2f}"
                })
            elif direction == "short" and thresholds["rsi"]["short"]["min"] is not None and rsi_value < thresholds["rsi"]["short"]["min"]:
                required_conditions.append({
                    "condition": "Chờ RSI tăng",
                    "description": f"RSI hiện tại ({rsi_value:.2f}) thấp hơn ngưỡng cho SHORT",
                    "target_value": f"> {thresholds['rsi']['short']['min']}",
                    "current_value": f"{rsi_value:.2f}"
                })
        
        # Kiểm tra MACD
        if "macd" in current_stats and "macd_signal" in current_stats:
            macd_value = current_stats["macd"]
            signal_value = current_stats["macd_signal"]
            
            if direction == "long" and macd_value < signal_value:
                required_conditions.append({
                    "condition": "Chờ MACD cắt lên trên đường tín hiệu",
                    "description": f"MACD ({macd_value:.6f}) đang dưới đường tín hiệu ({signal_value:.6f})",
                    "target_value": "MACD > Signal",
                    "current_value": f"MACD = {macd_value:.6f}, Signal = {signal_value:.6f}"
                })
            elif direction == "short" and macd_value > signal_value:
                required_conditions.append({
                    "condition": "Chờ MACD cắt xuống dưới đường tín hiệu",
                    "description": f"MACD ({macd_value:.6f}) đang trên đường tín hiệu ({signal_value:.6f})",
                    "target_value": "MACD < Signal",
                    "current_value": f"MACD = {macd_value:.6f}, Signal = {signal_value:.6f}"
                })
        
        # Kiểm tra Bollinger Bands
        if all(key in current_stats for key in ["bb_lower", "bb_upper", "bb_middle"]):
            price = analysis["price"]["current"]
            
            if direction == "long" and price > current_stats["bb_lower"]:
                required_conditions.append({
                    "condition": "Chờ giá chạm hoặc phá dưới Band dưới",
                    "description": f"Giá hiện tại ({price:.4f}) cao hơn Band dưới ({current_stats['bb_lower']:.4f})",
                    "target_value": f"Giá ≤ {current_stats['bb_lower']:.4f}",
                    "current_value": f"{price:.4f}"
                })
            elif direction == "short" and price < current_stats["bb_upper"]:
                required_conditions.append({
                    "condition": "Chờ giá chạm hoặc phá trên Band trên",
                    "description": f"Giá hiện tại ({price:.4f}) thấp hơn Band trên ({current_stats['bb_upper']:.4f})",
                    "target_value": f"Giá ≥ {current_stats['bb_upper']:.4f}",
                    "current_value": f"{price:.4f}"
                })
        
        return required_conditions
    
    def _generate_suggestion(self, long_result: Dict, short_result: Dict) -> Dict:
        """
        Tạo gợi ý tổng thể dựa trên phân tích
        
        Args:
            long_result (Dict): Kết quả phân tích LONG
            short_result (Dict): Kết quả phân tích SHORT
            
        Returns:
            Dict: Gợi ý tổng thể
        """
        symbol = long_result["symbol"]
        long_score = long_result["score"]
        short_score = short_result["score"]
        long_reasons = long_result["no_trade_reasons"]
        short_reasons = short_result["no_trade_reasons"]
        market_regime = long_result["global_market"]["market_regime"]
        
        # Xác định xu hướng tốt hơn
        better_direction = "long" if long_score > short_score else "short"
        potential_exists = long_score >= 40 or short_score >= 40
        
        # Tạo gợi ý
        suggestion = {
            "primary_direction": better_direction,
            "potential_exists": potential_exists,
            "waiting_preferred": len(long_reasons) > 0 and len(short_reasons) > 0,
            "suggested_action": "wait",
            "market_regime": market_regime,
            "next_steps": [],
            "estimated_wait_time": "unknown"
        }
        
        # Xác định hành động gợi ý
        if not potential_exists:
            suggestion["suggested_action"] = "skip"
            suggestion["next_steps"].append(f"Bỏ qua {symbol} vì không có tiềm năng giao dịch đủ mạnh")
        elif long_score >= 60 and len(long_reasons) == 0:
            suggestion["suggested_action"] = "long"
            suggestion["next_steps"].append(f"Xem xét vào lệnh LONG cho {symbol}")
        elif short_score >= 60 and len(short_reasons) == 0:
            suggestion["suggested_action"] = "short"
            suggestion["next_steps"].append(f"Xem xét vào lệnh SHORT cho {symbol}")
        else:
            suggestion["suggested_action"] = "wait"
            if better_direction == "long":
                for condition in long_result["required_conditions"]:
                    suggestion["next_steps"].append(condition["condition"])
            else:
                for condition in short_result["required_conditions"]:
                    suggestion["next_steps"].append(condition["condition"])
        
        # Ước tính thời gian chờ đợi
        if suggestion["suggested_action"] == "wait":
            if "high_volatility" in market_regime:
                suggestion["estimated_wait_time"] = "short (1-3 giờ)"
            elif "trending" in market_regime:
                suggestion["estimated_wait_time"] = "medium (4-12 giờ)"
            elif "ranging" in market_regime:
                suggestion["estimated_wait_time"] = "long (12-24 giờ)"
            else:
                suggestion["estimated_wait_time"] = "unknown"
        
        return suggestion
    
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
        report_filename = f"reports/no_trade_analysis/{symbol}_{timeframe}_{timestamp}.json"
        
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
        long_analysis = analysis_result["long_analysis"]
        short_analysis = analysis_result["short_analysis"]
        suggestion = analysis_result["suggestion"]
        
        long_score = long_analysis["score"]
        short_score = short_analysis["score"]
        long_reasons = long_analysis["no_trade_reasons"]
        short_reasons = short_analysis["no_trade_reasons"]
        
        print("\n" + "="*80)
        print(f"PHÂN TÍCH LÝ DO KHÔNG GIAO DỊCH: {symbol} - {timeframe}")
        print("="*80)
        
        print(f"\nNgày: {analysis_result['timestamp']}")
        print(f"Giá hiện tại: {long_analysis['current_price']}")
        print(f"Chế độ thị trường: {long_analysis['global_market']['market_regime']}")
        
        # Tóm tắt điểm
        print("\n" + "-"*80)
        print("TÓM TẮT ĐIỂM PHÂN TÍCH")
        print("-"*80)
        print(f"Điểm LONG: {long_score}/100 {'(Đủ để giao dịch)' if long_score >= 60 else '(Chưa đủ để giao dịch)'}")
        print(f"Điểm SHORT: {short_score}/100 {'(Đủ để giao dịch)' if short_score >= 60 else '(Chưa đủ để giao dịch)'}")
        
        # Lý do không giao dịch LONG
        print("\n" + "-"*80)
        print("LÝ DO KHÔNG GIAO DỊCH LONG")
        print("-"*80)
        
        if not long_reasons:
            print("Không có lý do chặn giao dịch LONG! Đây có thể là cơ hội giao dịch tốt.")
        else:
            for i, reason in enumerate(long_reasons, 1):
                importance = reason.get("importance", "medium")
                importance_icon = "❗❗❗" if importance == "high" else "❗❗" if importance == "medium" else "❗"
                print(f"{i}. {importance_icon} {reason.get('reason')} (Mức độ quan trọng: {importance})")
        
        # Lý do không giao dịch SHORT
        print("\n" + "-"*80)
        print("LÝ DO KHÔNG GIAO DỊCH SHORT")
        print("-"*80)
        
        if not short_reasons:
            print("Không có lý do chặn giao dịch SHORT! Đây có thể là cơ hội giao dịch tốt.")
        else:
            for i, reason in enumerate(short_reasons, 1):
                importance = reason.get("importance", "medium")
                importance_icon = "❗❗❗" if importance == "high" else "❗❗" if importance == "medium" else "❗"
                print(f"{i}. {importance_icon} {reason.get('reason')} (Mức độ quan trọng: {importance})")
        
        # Các điều kiện cần thiết để giao dịch LONG
        print("\n" + "-"*80)
        print("ĐIỀU KIỆN CẦN THIẾT ĐỂ GIAO DỊCH LONG")
        print("-"*80)
        
        if not long_analysis["required_conditions"]:
            print("Không có điều kiện bổ sung - Có thể giao dịch LONG ngay!")
        else:
            required_data = []
            for condition in long_analysis["required_conditions"]:
                required_data.append([
                    condition["condition"],
                    condition["target_value"],
                    condition["current_value"]
                ])
            
            print(tabulate(required_data, headers=["Điều kiện cần đạt", "Giá trị mục tiêu", "Giá trị hiện tại"], tablefmt="grid"))
        
        # Các điều kiện cần thiết để giao dịch SHORT
        print("\n" + "-"*80)
        print("ĐIỀU KIỆN CẦN THIẾT ĐỂ GIAO DỊCH SHORT")
        print("-"*80)
        
        if not short_analysis["required_conditions"]:
            print("Không có điều kiện bổ sung - Có thể giao dịch SHORT ngay!")
        else:
            required_data = []
            for condition in short_analysis["required_conditions"]:
                required_data.append([
                    condition["condition"],
                    condition["target_value"],
                    condition["current_value"]
                ])
            
            print(tabulate(required_data, headers=["Điều kiện cần đạt", "Giá trị mục tiêu", "Giá trị hiện tại"], tablefmt="grid"))
        
        # Các thông số hiện tại
        print("\n" + "-"*80)
        print("CÁC THÔNG SỐ KỸ THUẬT HIỆN TẠI")
        print("-"*80)
        
        stats_data = []
        for key, value in long_analysis["current_stats"].items():
            if isinstance(value, float):
                stats_data.append([key, f"{value:.4f}"])
            else:
                stats_data.append([key, value])
        
        print(tabulate(stats_data, headers=["Chỉ báo", "Giá trị"], tablefmt="grid"))
        
        # Gợi ý tổng thể
        print("\n" + "-"*80)
        print("GỢI Ý TỔNG THỂ")
        print("-"*80)
        
        action_text = ""
        if suggestion["suggested_action"] == "long":
            action_text = "VÀO LỆNH LONG"
        elif suggestion["suggested_action"] == "short":
            action_text = "VÀO LỆNH SHORT"
        elif suggestion["suggested_action"] == "wait":
            action_text = "CHỜ ĐỢI"
        else:
            action_text = "BỎ QUA"
        
        print(f"Gợi ý: {action_text}")
        print(f"Hướng tiềm năng tốt hơn: {suggestion['primary_direction'].upper()}")
        print(f"Có tiềm năng giao dịch: {'Có' if suggestion['potential_exists'] else 'Không'}")
        print(f"Ước tính thời gian chờ: {suggestion['estimated_wait_time']}")
        
        print("\nCác bước tiếp theo:")
        for i, step in enumerate(suggestion["next_steps"], 1):
            print(f"{i}. {step}")
        
        # Lịch sử phân tích
        if long_analysis["historical_reasons"] or short_analysis["historical_reasons"]:
            print("\n" + "-"*80)
            print("LỊCH SỬ PHÂN TÍCH GẦN ĐÂY")
            print("-"*80)
            
            # LONG
            if long_analysis["historical_reasons"]:
                print("\nLịch sử phân tích LONG:")
                history_data = []
                for entry in long_analysis["historical_reasons"]:
                    reasons_text = "; ".join([r.get("reason", "") for r in entry.get("reasons", [])])
                    if len(reasons_text) > 50:
                        reasons_text = reasons_text[:47] + "..."
                    
                    history_data.append([
                        entry.get("timestamp", ""),
                        entry.get("price", ""),
                        reasons_text
                    ])
                
                print(tabulate(history_data, headers=["Thời gian", "Giá", "Lý do"], tablefmt="grid"))
            
            # SHORT
            if short_analysis["historical_reasons"]:
                print("\nLịch sử phân tích SHORT:")
                history_data = []
                for entry in short_analysis["historical_reasons"]:
                    reasons_text = "; ".join([r.get("reason", "") for r in entry.get("reasons", [])])
                    if len(reasons_text) > 50:
                        reasons_text = reasons_text[:47] + "..."
                    
                    history_data.append([
                        entry.get("timestamp", ""),
                        entry.get("price", ""),
                        reasons_text
                    ])
                
                print(tabulate(history_data, headers=["Thời gian", "Giá", "Lý do"], tablefmt="grid"))
        
        print("\n" + "="*80)
        print(f"Báo cáo chi tiết được lưu trong thư mục reports/no_trade_analysis/")
        print("="*80 + "\n")

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Phân tích lý do không giao dịch")
    parser.add_argument("--symbol", type=str, required=True, help="Mã cặp tiền (ví dụ: BTCUSDT)")
    parser.add_argument("--timeframe", type=str, default=None, help="Khung thời gian (ví dụ: 1h, 4h, 1d)")
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    print(f"\nĐang phân tích lý do không giao dịch cho {args.symbol} trên khung {args.timeframe or 'mặc định'}...")
    
    analyzer = NoTradeReasonsAnalyzer()
    result = analyzer.analyze_both_directions(args.symbol, args.timeframe)
    
    # In kết quả
    analyzer.print_analysis_summary(result)

if __name__ == "__main__":
    main()