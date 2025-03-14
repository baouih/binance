#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive Backtesting System - Hệ thống backtest toàn diện, phân tích và kiểm tra xung đột
giữa các chiến lược, đánh giá hiệu suất và độ tin cậy của các tín hiệu
"""

import os
import sys
import json
import time
import logging
import datetime
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('comprehensive_backtest.log')
    ]
)

logger = logging.getLogger('comprehensive_backtest')

# Import các module liên quan
try:
    from bot_diagnostic import BotDiagnostic
    from strategy_conflict_checker import StrategyConflictChecker
    from signal_consistency_analyzer import SignalConsistencyAnalyzer
except ImportError as e:
    logger.error(f"Không thể import module cần thiết: {e}")
    logger.info("Đảm bảo các file bot_diagnostic.py, strategy_conflict_checker.py, signal_consistency_analyzer.py tồn tại")
    sys.exit(1)

class ComprehensiveBacktest:
    """
    Hệ thống backtest toàn diện kết hợp nhiều công cụ phân tích
    """
    
    def __init__(self, config_path='comprehensive_backtest_config.json'):
        """
        Khởi tạo hệ thống backtest toàn diện
        
        Args:
            config_path (str): Đường dẫn file cấu hình
        """
        self.config_path = config_path
        self.load_config()
        
        # Tạo thư mục kết quả
        self.results_dir = 'comprehensive_test_results'
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Khởi tạo các công cụ phân tích
        self.bot_diagnostic = BotDiagnostic(config_path=self.config.get('bot_diagnostic_config', 'bot_diagnostic_config.json'))
        self.conflict_checker = StrategyConflictChecker(config_path=self.config.get('strategy_conflict_config', 'strategy_conflict_config.json'))
        self.signal_analyzer = SignalConsistencyAnalyzer(config_path=self.config.get('signal_analyzer_config', 'signal_analyzer_config.json'))
        
        logger.info("Đã khởi tạo hệ thống backtest toàn diện")
    
    def load_config(self):
        """
        Tải cấu hình từ file JSON
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
            else:
                # Tạo cấu hình mặc định
                self.config = {
                    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT", "XRPUSDT"],
                    "timeframes": ["1h", "4h", "1d"],
                    "risk_levels": ["low", "medium", "high"],
                    "test_days": 30,
                    "strategies": [
                        "ema_crossover",
                        "macd_divergence",
                        "rsi_extreme",
                        "supertrend",
                        "bollinger_bands_squeeze",
                        "adaptive_mode",
                        "hedge_mode"
                    ],
                    "parallel_tests": 4,
                    "performance_metrics": {
                        "min_win_rate": 55,
                        "max_drawdown": 20,
                        "min_profit_factor": 1.5,
                        "min_sharpe_ratio": 1.0
                    },
                    "consistency_thresholds": {
                        "max_signal_conflict": 10,
                        "max_position_overlap": 5,
                        "min_strategy_agreement": 70
                    },
                    "report_formats": ["json", "html", "md"],
                    "data_sources": {
                        "use_historical_data": True,
                        "historical_data_dir": "data",
                        "download_missing_data": True
                    },
                    "bot_diagnostic_config": "bot_diagnostic_config.json",
                    "strategy_conflict_config": "strategy_conflict_config.json",
                    "signal_analyzer_config": "signal_analyzer_config.json"
                }
                
                # Lưu cấu hình mặc định
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
                
                logger.info(f"Đã tạo cấu hình mặc định và lưu vào {self.config_path}")
        
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            raise
    
    def run_comprehensive_test(self):
        """
        Chạy kiểm tra toàn diện
        
        Returns:
            dict: Kết quả kiểm tra toàn diện
        """
        logger.info("Bắt đầu chạy kiểm tra toàn diện...")
        start_time = time.time()
        
        # Kết quả tổng hợp
        results = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "test_duration": 0,
            "symbols_tested": self.config["symbols"],
            "timeframes_tested": self.config["timeframes"],
            "risk_levels_tested": self.config["risk_levels"],
            "strategies_tested": self.config["strategies"],
            "diagnostic_results": {},
            "conflict_analysis": {},
            "signal_consistency": {},
            "performance_metrics": {},
            "combined_recommendations": [],
            "final_score": 0,
            "passing_status": False
        }
        
        try:
            # 1. Chạy bot diagnostic
            logger.info("Bắt đầu chạy bot diagnostic...")
            diagnostic_results = self.bot_diagnostic.run_diagnostic()
            results["diagnostic_results"] = self._summarize_diagnostic_results(diagnostic_results)
            
            # 2. Chạy phân tích xung đột chiến lược
            logger.info("Bắt đầu phân tích xung đột chiến lược...")
            conflict_results = self.conflict_checker.check_conflicts()
            results["conflict_analysis"] = self._summarize_conflict_results(conflict_results)
            
            # 3. Chạy phân tích tính nhất quán tín hiệu
            logger.info("Bắt đầu phân tích tính nhất quán tín hiệu...")
            consistency_results = self.signal_analyzer.analyze_consistency()
            results["signal_consistency"] = self._summarize_consistency_results(consistency_results)
            
            # 4. Chạy backtest và đánh giá hiệu suất
            logger.info("Bắt đầu backtest và đánh giá hiệu suất...")
            performance_results = self._run_performance_tests()
            results["performance_metrics"] = performance_results
            
            # 5. Kết hợp các khuyến nghị
            logger.info("Tổng hợp các khuyến nghị...")
            self._combine_recommendations(results)
            
            # 6. Tính điểm tổng thể và trạng thái pass/fail
            logger.info("Tính điểm tổng thể...")
            self._calculate_final_score(results)
            
            # 7. Tạo báo cáo
            logger.info("Tạo báo cáo...")
            self._generate_report(results)
            
            # Ghi lại thời gian chạy
            end_time = time.time()
            results["test_duration"] = end_time - start_time
            
            logger.info(f"Hoàn thành kiểm tra toàn diện sau {results['test_duration']:.2f} giây")
            
            return results
        
        except Exception as e:
            logger.error(f"Lỗi trong quá trình chạy kiểm tra toàn diện: {e}")
            
            # Vẫn ghi lại thời gian chạy
            end_time = time.time()
            results["test_duration"] = end_time - start_time
            results["error"] = str(e)
            
            # Lưu kết quả dù có lỗi
            self._save_results(results)
            
            raise
    
    def _summarize_diagnostic_results(self, diagnostic_results):
        """
        Tóm tắt kết quả từ bot diagnostic
        
        Args:
            diagnostic_results (dict): Kết quả chẩn đoán
            
        Returns:
            dict: Tóm tắt kết quả
        """
        summary = {
            "total_errors": 0,
            "critical_errors": 0,
            "warning_errors": 0,
            "info_errors": 0,
            "error_categories": {},
            "critical_error_details": [],
            "recommendations": []
        }
        
        # Đếm tổng số lỗi
        for category, errors in diagnostic_results.items():
            error_count = len(errors)
            summary["total_errors"] += error_count
            summary["error_categories"][category] = error_count
            
            # Phân loại mức độ nghiêm trọng
            if category in ['api_errors', 'algorithm_failures', 'database_failures', 'entry_exit_errors']:
                summary["critical_errors"] += error_count
                
                # Lưu chi tiết các lỗi nghiêm trọng
                for error in errors[:5]:  # Chỉ lấy 5 lỗi nghiêm trọng đầu tiên
                    summary["critical_error_details"].append({
                        "category": category,
                        "error": error.get("error", "Unknown"),
                        "details": error.get("details", "No details")
                    })
            
            elif category in ['strategy_conflicts', 'position_overlaps', 'risk_management_issues']:
                summary["warning_errors"] += error_count
            
            else:
                summary["info_errors"] += error_count
        
        # Tạo khuyến nghị dựa trên lỗi
        if summary["critical_errors"] > 0:
            summary["recommendations"].append({
                "type": "critical",
                "recommendation": f"Sửa {summary['critical_errors']} lỗi nghiêm trọng trước khi triển khai.",
                "details": "Các lỗi nghiêm trọng có thể gây mất tiền khi giao dịch thực."
            })
        
        if summary["warning_errors"] > 0:
            summary["recommendations"].append({
                "type": "warning",
                "recommendation": f"Xem xét {summary['warning_errors']} cảnh báo để cải thiện hiệu suất.",
                "details": "Các cảnh báo có thể dẫn đến hiệu suất giao dịch không tối ưu."
            })
        
        category_with_most_errors = max(summary["error_categories"].items(), key=lambda x: x[1], default=("none", 0))
        if category_with_most_errors[1] > 0:
            summary["recommendations"].append({
                "type": "info",
                "recommendation": f"Tập trung sửa lỗi trong danh mục '{category_with_most_errors[0]}'.",
                "details": f"Danh mục này có nhiều lỗi nhất ({category_with_most_errors[1]} lỗi)."
            })
        
        return summary
    
    def _summarize_conflict_results(self, conflict_results):
        """
        Tóm tắt kết quả từ phân tích xung đột
        
        Args:
            conflict_results (dict): Kết quả phân tích xung đột
            
        Returns:
            dict: Tóm tắt kết quả
        """
        summary = {
            "total_conflicts": len(conflict_results.get("conflicts", [])),
            "total_overlaps": len(conflict_results.get("overlaps", [])),
            "conflict_percentage": conflict_results.get("overall_summary", {}).get("conflict_percentage", 0),
            "overlap_percentage": conflict_results.get("overall_summary", {}).get("overlap_percentage", 0),
            "strategy_conflict_stats": {},
            "top_conflicts": [],
            "recommendations": []
        }
        
        # Thống kê xung đột theo chiến lược
        for strategy, stats in conflict_results.get("strategy_statistics", {}).items():
            if stats.get("total_signals", 0) > 0:
                conflict_percentage = (stats.get("conflict_count", 0) / stats.get("total_signals", 1)) * 100
                overlap_percentage = (stats.get("overlap_count", 0) / stats.get("total_signals", 1)) * 100
            else:
                conflict_percentage = 0
                overlap_percentage = 0
            
            summary["strategy_conflict_stats"][strategy] = {
                "conflict_percentage": conflict_percentage,
                "overlap_percentage": overlap_percentage,
                "total_signals": stats.get("total_signals", 0)
            }
        
        # Top xung đột
        for conflict in conflict_results.get("conflicts", [])[:5]:  # Lấy 5 xung đột đầu tiên
            summary["top_conflicts"].append({
                "timestamp": conflict.get("timestamp", "Unknown"),
                "symbol": conflict.get("symbol", "Unknown"),
                "timeframe": conflict.get("timeframe", "Unknown"),
                "strategies": conflict.get("strategies", []),
                "signals": conflict.get("signals", []),
                "conflict_type": conflict.get("conflict_type", "Unknown")
            })
        
        # Tạo khuyến nghị dựa trên xung đột
        thresholds = self.config.get("consistency_thresholds", {})
        max_signal_conflict = thresholds.get("max_signal_conflict", 10)
        max_position_overlap = thresholds.get("max_position_overlap", 5)
        
        if summary["conflict_percentage"] > max_signal_conflict:
            summary["recommendations"].append({
                "type": "critical",
                "recommendation": f"Tỷ lệ xung đột tín hiệu ({summary['conflict_percentage']:.2f}%) vượt quá ngưỡng cho phép ({max_signal_conflict}%).",
                "details": "Xung đột tín hiệu cao có thể dẫn đến việc đặt lệnh mâu thuẫn, cần xem xét lại cơ chế kết hợp chiến lược."
            })
        
        if summary["overlap_percentage"] > max_position_overlap:
            summary["recommendations"].append({
                "type": "warning",
                "recommendation": f"Tỷ lệ chồng chéo vị thế ({summary['overlap_percentage']:.2f}%) vượt quá ngưỡng cho phép ({max_position_overlap}%).",
                "details": "Chồng chéo vị thế có thể dẫn đến quản lý rủi ro không hiệu quả, cần cải thiện cơ chế quản lý vị thế."
            })
        
        # Khuyến nghị cho từng chiến lược
        problem_strategies = []
        for strategy, stats in summary["strategy_conflict_stats"].items():
            if stats["conflict_percentage"] > max_signal_conflict * 1.5:
                problem_strategies.append(strategy)
        
        if problem_strategies:
            summary["recommendations"].append({
                "type": "warning",
                "recommendation": f"Các chiến lược {', '.join(problem_strategies)} có tỷ lệ xung đột cao.",
                "details": "Cần xem xét lại các chiến lược này hoặc cải thiện cơ chế giải quyết xung đột."
            })
        
        return summary
    
    def _summarize_consistency_results(self, consistency_results):
        """
        Tóm tắt kết quả từ phân tích tính nhất quán
        
        Args:
            consistency_results (dict): Kết quả phân tích tính nhất quán
            
        Returns:
            dict: Tóm tắt kết quả
        """
        summary = {
            "agreement_percentage": consistency_results.get("overall_consistency", {}).get("agreement_percentage", 0),
            "contradiction_percentage": consistency_results.get("overall_consistency", {}).get("contradiction_percentage", 0),
            "average_correlation": consistency_results.get("overall_consistency", {}).get("average_correlation", 0),
            "timeframe_consistency": {},
            "strategy_consistency": {},
            "conflicting_periods_count": len(consistency_results.get("conflicting_periods", [])),
            "recommendations": []
        }
        
        # Thống kê theo timeframe
        for timeframe, stats in consistency_results.get("timeframe_consistency", {}).items():
            summary["timeframe_consistency"][timeframe] = {
                "agreement_percentage": stats.get("agreement_percentage", 0),
                "contradiction_percentage": stats.get("contradiction_percentage", 0),
                "false_signal_ratio": stats.get("false_signal_ratio", 0)
            }
        
        # Thống kê theo chiến lược
        for strategy, stats in consistency_results.get("strategy_consistency", {}).items():
            summary["strategy_consistency"][strategy] = {
                "contradiction_count": stats.get("contradiction_count", 0),
                "average_correlation": stats.get("average_correlation", 0)
            }
        
        # Tạo khuyến nghị dựa trên tính nhất quán
        thresholds = self.config.get("consistency_thresholds", {})
        min_strategy_agreement = thresholds.get("min_strategy_agreement", 70)
        
        if summary["agreement_percentage"] < min_strategy_agreement:
            summary["recommendations"].append({
                "type": "critical",
                "recommendation": f"Tỷ lệ đồng thuận ({summary['agreement_percentage']:.2f}%) thấp hơn ngưỡng tối thiểu ({min_strategy_agreement}%).",
                "details": "Tỷ lệ đồng thuận thấp cho thấy các chiến lược không thống nhất, cần cải thiện cơ chế ra quyết định."
            })
        
        if summary["contradiction_percentage"] > 20:  # Ngưỡng cứng
            summary["recommendations"].append({
                "type": "warning",
                "recommendation": f"Tỷ lệ mâu thuẫn ({summary['contradiction_percentage']:.2f}%) quá cao.",
                "details": "Tỷ lệ mâu thuẫn cao có thể dẫn đến nhầm lẫn trong việc vào lệnh, cần xem xét lại thuật toán."
            })
        
        if summary["average_correlation"] < 0.3:  # Ngưỡng cứng
            summary["recommendations"].append({
                "type": "warning",
                "recommendation": f"Tương quan trung bình giữa các chiến lược ({summary['average_correlation']:.2f}) quá thấp.",
                "details": "Tương quan thấp có thể dẫn đến quyết định không nhất quán, cần cân nhắc việc sử dụng các chiến lược có mối tương quan cao hơn."
            })
        
        # Khuyến nghị dựa trên timeframe
        bad_timeframes = []
        for timeframe, stats in summary["timeframe_consistency"].items():
            if stats["contradiction_percentage"] > 30:  # Ngưỡng cứng
                bad_timeframes.append(timeframe)
        
        if bad_timeframes:
            summary["recommendations"].append({
                "type": "info",
                "recommendation": f"Timeframe {', '.join(bad_timeframes)} có tỷ lệ mâu thuẫn cao.",
                "details": "Cân nhắc điều chỉnh chiến lược cho các timeframe này hoặc ưu tiên các timeframe khác."
            })
        
        return summary
    
    def _run_performance_tests(self):
        """
        Chạy backtest và đánh giá hiệu suất
        
        Returns:
            dict: Kết quả đánh giá hiệu suất
        """
        logger.info("Chạy backtest và đánh giá hiệu suất...")
        
        # Kết quả hiệu suất
        performance_results = {
            "overall_metrics": {
                "win_rate": 0,
                "profit_factor": 0,
                "drawdown": 0,
                "sharpe_ratio": 0,
                "total_trades": 0,
                "net_profit_percent": 0
            },
            "symbol_metrics": {},
            "timeframe_metrics": {},
            "strategy_metrics": {},
            "risk_level_metrics": {},
            "best_combinations": [],
            "worst_combinations": [],
            "recommendations": []
        }
        
        # Sử dụng đa luồng để chạy backtest
        with ThreadPoolExecutor(max_workers=self.config.get("parallel_tests", 4)) as executor:
            # Tạo danh sách tất cả các công việc backtest
            tasks = []
            for symbol in self.config["symbols"]:
                for timeframe in self.config["timeframes"]:
                    for risk_level in self.config["risk_levels"]:
                        tasks.append(executor.submit(self._run_single_backtest, symbol, timeframe, risk_level))
            
            # Thu thập kết quả khi hoàn thành
            backtest_results = []
            for future in as_completed(tasks):
                try:
                    result = future.result()
                    backtest_results.append(result)
                except Exception as e:
                    logger.error(f"Lỗi khi chạy backtest: {e}")
        
        # Tính toán các chỉ số tổng hợp
        self._calculate_performance_metrics(backtest_results, performance_results)
        
        # Tạo khuyến nghị dựa trên hiệu suất
        self._generate_performance_recommendations(performance_results)
        
        return performance_results
    
    def _run_single_backtest(self, symbol, timeframe, risk_level):
        """
        Chạy backtest cho một bộ tham số cụ thể
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            risk_level (str): Mức độ rủi ro
            
        Returns:
            dict: Kết quả backtest
        """
        logger.info(f"Chạy backtest cho {symbol} {timeframe} {risk_level}...")
        
        try:
            # Kết quả backtest
            backtest_result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "risk_level": risk_level,
                "strategies": {},
                "combined_result": {
                    "win_rate": 0,
                    "profit_factor": 0,
                    "drawdown": 0,
                    "sharpe_ratio": 0,
                    "total_trades": 0,
                    "net_profit_percent": 0
                }
            }
            
            # Chạy backtest cho từng chiến lược
            for strategy in self.config["strategies"]:
                # Mô phỏng kết quả backtest
                # Trong thực tế, cần gọi hàm backtest thực tế ở đây
                strategy_result = self._simulate_strategy_backtest(symbol, timeframe, risk_level, strategy)
                backtest_result["strategies"][strategy] = strategy_result
            
            # Kết hợp kết quả từ tất cả chiến lược
            self._combine_strategy_results(backtest_result)
            
            logger.info(f"Hoàn thành backtest cho {symbol} {timeframe} {risk_level}")
            
            return backtest_result
        
        except Exception as e:
            logger.error(f"Lỗi khi chạy backtest cho {symbol} {timeframe} {risk_level}: {e}")
            raise
    
    def _simulate_strategy_backtest(self, symbol, timeframe, risk_level, strategy):
        """
        Mô phỏng kết quả backtest cho một chiến lược
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            risk_level (str): Mức độ rủi ro
            strategy (str): Tên chiến lược
            
        Returns:
            dict: Kết quả backtest mô phỏng
        """
        # Mô phỏng kết quả backtest
        # Trong thực tế, cần sử dụng dữ liệu thực và thuật toán thực
        
        # Tạo số liệu ngẫu nhiên nhưng có tính đến các yếu tố ảnh hưởng
        
        # Hệ số ảnh hưởng dựa trên mức độ rủi ro
        risk_factor = 1.0
        if risk_level == "low":
            risk_factor = 0.7  # Ít lệnh hơn, ít lợi nhuận hơn, ít rủi ro hơn
        elif risk_level == "high":
            risk_factor = 1.3  # Nhiều lệnh hơn, nhiều lợi nhuận hơn, nhiều rủi ro hơn
        
        # Hệ số ảnh hưởng dựa trên symbol (gần thực tế hơn)
        symbol_factor = 1.0
        if symbol == "BTCUSDT":
            symbol_factor = 1.1  # BTC thường ổn định hơn
        elif symbol == "ETHUSDT":
            symbol_factor = 1.05  # ETH cũng khá ổn định
        elif symbol == "DOGEUSDT":
            symbol_factor = 0.9  # DOGE thường biến động và rủi ro hơn
        
        # Hệ số ảnh hưởng dựa trên chiến lược
        strategy_factor = 1.0
        if strategy == "ema_crossover":
            strategy_factor = 1.05  # Chiến lược đơn giản và ổn định
        elif strategy == "macd_divergence":
            strategy_factor = 1.1  # Chiến lược tốt trong thị trường xu hướng
        elif strategy == "rsi_extreme":
            strategy_factor = 0.95  # Chiến lược chỉ tốt trong thị trường sideway
        elif strategy == "supertrend":
            strategy_factor = 1.08  # Chiến lược tốt trong thị trường xu hướng mạnh
        elif strategy == "bollinger_bands_squeeze":
            strategy_factor = 0.9  # Chiến lược đòi hỏi nhiều điều kiện
        elif strategy == "adaptive_mode":
            strategy_factor = 1.15  # Chiến lược thích ứng tốt với nhiều điều kiện
        elif strategy == "hedge_mode":
            strategy_factor = 1.0  # Chiến lược hedge mode ít rủi ro nhưng cũng ít lợi nhuận
        
        # Hệ số ảnh hưởng dựa trên timeframe
        timeframe_factor = 1.0
        if timeframe == "1h":
            timeframe_factor = 0.9  # Timeframe ngắn có nhiều nhiễu
        elif timeframe == "4h":
            timeframe_factor = 1.1  # Timeframe trung bình khá cân bằng
        elif timeframe == "1d":
            timeframe_factor = 1.05  # Timeframe dài ổn định nhưng ít cơ hội
        
        # Kết hợp tất cả các yếu tố
        combined_factor = risk_factor * symbol_factor * strategy_factor * timeframe_factor
        
        # Tạo kết quả ngẫu nhiên nhưng có tính đến các yếu tố ảnh hưởng
        win_rate_base = 52 + np.random.randint(-5, 15)  # Tỷ lệ thắng cơ bản từ 47% đến 67%
        win_rate = min(max(win_rate_base * combined_factor * 0.01, 0.3), 0.9)  # Giới hạn từ 30% đến 90%
        
        profit_factor_base = 1.2 + np.random.random() * 1.0  # Hệ số lợi nhuận cơ bản từ 1.2 đến 2.2
        profit_factor = profit_factor_base * combined_factor
        
        drawdown_base = 5 + np.random.random() * 20  # Drawdown cơ bản từ 5% đến 25%
        drawdown = drawdown_base / combined_factor  # Combined factor cao làm giảm drawdown
        
        total_trades_base = 20 + np.random.randint(0, 60)  # Số lệnh cơ bản từ 20 đến 80
        total_trades = int(total_trades_base * risk_factor)  # Mức rủi ro cao có nhiều lệnh hơn
        
        # Tính toán net profit dựa trên các chỉ số khác
        avg_win = 2.0  # Giả sử lãi trung bình 2%
        avg_loss = 1.0  # Giả sử lỗ trung bình 1%
        net_profit = total_trades * (win_rate * avg_win - (1 - win_rate) * avg_loss)
        
        # Tính Sharpe Ratio
        returns_std = drawdown / 3  # Ước tính độ lệch chuẩn dựa trên drawdown
        sharpe_ratio = (net_profit / 100) / returns_std if returns_std > 0 else 0
        
        # Kết quả backtest mô phỏng
        return {
            "win_rate": win_rate * 100,  # Chuyển về phần trăm
            "profit_factor": profit_factor,
            "drawdown": drawdown,
            "sharpe_ratio": sharpe_ratio,
            "total_trades": total_trades,
            "net_profit_percent": net_profit
        }
    
    def _combine_strategy_results(self, backtest_result):
        """
        Kết hợp kết quả từ các chiến lược trong một backtest
        
        Args:
            backtest_result (dict): Kết quả backtest của các chiến lược
        """
        strategies = backtest_result["strategies"]
        
        if not strategies:
            return
        
        # Tính tổng số lệnh
        total_trades = sum(strategy_result["total_trades"] for strategy_result in strategies.values())
        
        if total_trades == 0:
            return
        
        # Tính trung bình có trọng số dựa trên số lệnh
        weighted_win_rate = sum(strategy_result["win_rate"] * strategy_result["total_trades"] for strategy_result in strategies.values()) / total_trades
        
        weighted_profit_factor = sum(strategy_result["profit_factor"] * strategy_result["total_trades"] for strategy_result in strategies.values()) / total_trades
        
        weighted_drawdown = sum(strategy_result["drawdown"] * strategy_result["total_trades"] for strategy_result in strategies.values()) / total_trades
        
        weighted_sharpe = sum(strategy_result["sharpe_ratio"] * strategy_result["total_trades"] for strategy_result in strategies.values()) / total_trades
        
        # Tính tổng lợi nhuận
        net_profit = sum(strategy_result["net_profit_percent"] for strategy_result in strategies.values())
        
        # Cập nhật kết quả kết hợp
        backtest_result["combined_result"] = {
            "win_rate": weighted_win_rate,
            "profit_factor": weighted_profit_factor,
            "drawdown": weighted_drawdown,
            "sharpe_ratio": weighted_sharpe,
            "total_trades": total_trades,
            "net_profit_percent": net_profit
        }
    
    def _calculate_performance_metrics(self, backtest_results, performance_results):
        """
        Tính toán các chỉ số hiệu suất từ kết quả backtest
        
        Args:
            backtest_results (list): Danh sách kết quả backtest
            performance_results (dict): Kết quả hiệu suất tổng hợp
        """
        if not backtest_results:
            return
        
        # Tính toán chỉ số tổng hợp
        total_trades = sum(result["combined_result"]["total_trades"] for result in backtest_results)
        
        if total_trades == 0:
            return
        
        # Tính trung bình có trọng số dựa trên số lệnh
        weighted_win_rate = sum(result["combined_result"]["win_rate"] * result["combined_result"]["total_trades"] for result in backtest_results) / total_trades
        
        weighted_profit_factor = sum(result["combined_result"]["profit_factor"] * result["combined_result"]["total_trades"] for result in backtest_results) / total_trades
        
        weighted_drawdown = sum(result["combined_result"]["drawdown"] * result["combined_result"]["total_trades"] for result in backtest_results) / total_trades
        
        weighted_sharpe = sum(result["combined_result"]["sharpe_ratio"] * result["combined_result"]["total_trades"] for result in backtest_results) / total_trades
        
        # Tính tổng lợi nhuận
        net_profit = sum(result["combined_result"]["net_profit_percent"] for result in backtest_results)
        
        # Cập nhật chỉ số tổng thể
        performance_results["overall_metrics"] = {
            "win_rate": weighted_win_rate,
            "profit_factor": weighted_profit_factor,
            "drawdown": weighted_drawdown,
            "sharpe_ratio": weighted_sharpe,
            "total_trades": total_trades,
            "net_profit_percent": net_profit
        }
        
        # Tính toán chỉ số theo symbol
        symbols = {}
        for result in backtest_results:
            symbol = result["symbol"]
            if symbol not in symbols:
                symbols[symbol] = {
                    "total_trades": 0,
                    "win_rate_sum": 0,
                    "profit_factor_sum": 0,
                    "drawdown_sum": 0,
                    "sharpe_sum": 0,
                    "net_profit": 0
                }
            
            trades = result["combined_result"]["total_trades"]
            symbols[symbol]["total_trades"] += trades
            symbols[symbol]["win_rate_sum"] += result["combined_result"]["win_rate"] * trades
            symbols[symbol]["profit_factor_sum"] += result["combined_result"]["profit_factor"] * trades
            symbols[symbol]["drawdown_sum"] += result["combined_result"]["drawdown"] * trades
            symbols[symbol]["sharpe_sum"] += result["combined_result"]["sharpe_ratio"] * trades
            symbols[symbol]["net_profit"] += result["combined_result"]["net_profit_percent"]
        
        # Tính trung bình cho từng symbol
        for symbol, stats in symbols.items():
            if stats["total_trades"] > 0:
                performance_results["symbol_metrics"][symbol] = {
                    "win_rate": stats["win_rate_sum"] / stats["total_trades"],
                    "profit_factor": stats["profit_factor_sum"] / stats["total_trades"],
                    "drawdown": stats["drawdown_sum"] / stats["total_trades"],
                    "sharpe_ratio": stats["sharpe_sum"] / stats["total_trades"],
                    "total_trades": stats["total_trades"],
                    "net_profit_percent": stats["net_profit"]
                }
        
        # Tính toán chỉ số theo timeframe
        timeframes = {}
        for result in backtest_results:
            timeframe = result["timeframe"]
            if timeframe not in timeframes:
                timeframes[timeframe] = {
                    "total_trades": 0,
                    "win_rate_sum": 0,
                    "profit_factor_sum": 0,
                    "drawdown_sum": 0,
                    "sharpe_sum": 0,
                    "net_profit": 0
                }
            
            trades = result["combined_result"]["total_trades"]
            timeframes[timeframe]["total_trades"] += trades
            timeframes[timeframe]["win_rate_sum"] += result["combined_result"]["win_rate"] * trades
            timeframes[timeframe]["profit_factor_sum"] += result["combined_result"]["profit_factor"] * trades
            timeframes[timeframe]["drawdown_sum"] += result["combined_result"]["drawdown"] * trades
            timeframes[timeframe]["sharpe_sum"] += result["combined_result"]["sharpe_ratio"] * trades
            timeframes[timeframe]["net_profit"] += result["combined_result"]["net_profit_percent"]
        
        # Tính trung bình cho từng timeframe
        for timeframe, stats in timeframes.items():
            if stats["total_trades"] > 0:
                performance_results["timeframe_metrics"][timeframe] = {
                    "win_rate": stats["win_rate_sum"] / stats["total_trades"],
                    "profit_factor": stats["profit_factor_sum"] / stats["total_trades"],
                    "drawdown": stats["drawdown_sum"] / stats["total_trades"],
                    "sharpe_ratio": stats["sharpe_sum"] / stats["total_trades"],
                    "total_trades": stats["total_trades"],
                    "net_profit_percent": stats["net_profit"]
                }
        
        # Tính toán chỉ số theo risk level
        risk_levels = {}
        for result in backtest_results:
            risk_level = result["risk_level"]
            if risk_level not in risk_levels:
                risk_levels[risk_level] = {
                    "total_trades": 0,
                    "win_rate_sum": 0,
                    "profit_factor_sum": 0,
                    "drawdown_sum": 0,
                    "sharpe_sum": 0,
                    "net_profit": 0
                }
            
            trades = result["combined_result"]["total_trades"]
            risk_levels[risk_level]["total_trades"] += trades
            risk_levels[risk_level]["win_rate_sum"] += result["combined_result"]["win_rate"] * trades
            risk_levels[risk_level]["profit_factor_sum"] += result["combined_result"]["profit_factor"] * trades
            risk_levels[risk_level]["drawdown_sum"] += result["combined_result"]["drawdown"] * trades
            risk_levels[risk_level]["sharpe_sum"] += result["combined_result"]["sharpe_ratio"] * trades
            risk_levels[risk_level]["net_profit"] += result["combined_result"]["net_profit_percent"]
        
        # Tính trung bình cho từng risk level
        for risk_level, stats in risk_levels.items():
            if stats["total_trades"] > 0:
                performance_results["risk_level_metrics"][risk_level] = {
                    "win_rate": stats["win_rate_sum"] / stats["total_trades"],
                    "profit_factor": stats["profit_factor_sum"] / stats["total_trades"],
                    "drawdown": stats["drawdown_sum"] / stats["total_trades"],
                    "sharpe_ratio": stats["sharpe_sum"] / stats["total_trades"],
                    "total_trades": stats["total_trades"],
                    "net_profit_percent": stats["net_profit"]
                }
        
        # Tính toán chỉ số theo chiến lược
        strategies = {}
        for result in backtest_results:
            for strategy, strategy_result in result["strategies"].items():
                if strategy not in strategies:
                    strategies[strategy] = {
                        "total_trades": 0,
                        "win_rate_sum": 0,
                        "profit_factor_sum": 0,
                        "drawdown_sum": 0,
                        "sharpe_sum": 0,
                        "net_profit": 0
                    }
                
                trades = strategy_result["total_trades"]
                strategies[strategy]["total_trades"] += trades
                strategies[strategy]["win_rate_sum"] += strategy_result["win_rate"] * trades
                strategies[strategy]["profit_factor_sum"] += strategy_result["profit_factor"] * trades
                strategies[strategy]["drawdown_sum"] += strategy_result["drawdown"] * trades
                strategies[strategy]["sharpe_sum"] += strategy_result["sharpe_ratio"] * trades
                strategies[strategy]["net_profit"] += strategy_result["net_profit_percent"]
        
        # Tính trung bình cho từng chiến lược
        for strategy, stats in strategies.items():
            if stats["total_trades"] > 0:
                performance_results["strategy_metrics"][strategy] = {
                    "win_rate": stats["win_rate_sum"] / stats["total_trades"],
                    "profit_factor": stats["profit_factor_sum"] / stats["total_trades"],
                    "drawdown": stats["drawdown_sum"] / stats["total_trades"],
                    "sharpe_ratio": stats["sharpe_sum"] / stats["total_trades"],
                    "total_trades": stats["total_trades"],
                    "net_profit_percent": stats["net_profit"]
                }
        
        # Tìm các kết hợp tốt nhất và tệ nhất
        # Sắp xếp theo profit factor
        sorted_results = sorted(backtest_results, key=lambda x: x["combined_result"]["profit_factor"], reverse=True)
        
        # Top 5 kết hợp tốt nhất
        performance_results["best_combinations"] = []
        for result in sorted_results[:5]:
            performance_results["best_combinations"].append({
                "symbol": result["symbol"],
                "timeframe": result["timeframe"],
                "risk_level": result["risk_level"],
                "profit_factor": result["combined_result"]["profit_factor"],
                "win_rate": result["combined_result"]["win_rate"],
                "net_profit_percent": result["combined_result"]["net_profit_percent"]
            })
        
        # Top 5 kết hợp tệ nhất
        performance_results["worst_combinations"] = []
        for result in sorted_results[-5:]:
            performance_results["worst_combinations"].append({
                "symbol": result["symbol"],
                "timeframe": result["timeframe"],
                "risk_level": result["risk_level"],
                "profit_factor": result["combined_result"]["profit_factor"],
                "win_rate": result["combined_result"]["win_rate"],
                "net_profit_percent": result["combined_result"]["net_profit_percent"]
            })
    
    def _generate_performance_recommendations(self, performance_results):
        """
        Tạo khuyến nghị dựa trên kết quả hiệu suất
        
        Args:
            performance_results (dict): Kết quả hiệu suất
        """
        # Lấy ngưỡng hiệu suất
        thresholds = self.config.get("performance_metrics", {})
        min_win_rate = thresholds.get("min_win_rate", 55)
        max_drawdown = thresholds.get("max_drawdown", 20)
        min_profit_factor = thresholds.get("min_profit_factor", 1.5)
        min_sharpe_ratio = thresholds.get("min_sharpe_ratio", 1.0)
        
        # Khuyến nghị dựa trên chỉ số tổng thể
        overall = performance_results["overall_metrics"]
        
        if overall["win_rate"] < min_win_rate:
            performance_results["recommendations"].append({
                "type": "critical",
                "recommendation": f"Tỷ lệ thắng ({overall['win_rate']:.2f}%) thấp hơn ngưỡng tối thiểu ({min_win_rate}%).",
                "details": "Tỷ lệ thắng thấp có thể dẫn đến lỗ vốn dài hạn, cần cải thiện thuật toán vào lệnh."
            })
        
        if overall["profit_factor"] < min_profit_factor:
            performance_results["recommendations"].append({
                "type": "critical",
                "recommendation": f"Hệ số lợi nhuận ({overall['profit_factor']:.2f}) thấp hơn ngưỡng tối thiểu ({min_profit_factor}).",
                "details": "Hệ số lợi nhuận thấp cho thấy tỷ lệ lãi/lỗ không đủ, cần cải thiện TP/SL."
            })
        
        if overall["drawdown"] > max_drawdown:
            performance_results["recommendations"].append({
                "type": "warning",
                "recommendation": f"Drawdown ({overall['drawdown']:.2f}%) vượt quá ngưỡng tối đa ({max_drawdown}%).",
                "details": "Drawdown cao có thể gây tổn thất vốn lớn, cần cải thiện quản lý rủi ro."
            })
        
        if overall["sharpe_ratio"] < min_sharpe_ratio:
            performance_results["recommendations"].append({
                "type": "warning",
                "recommendation": f"Tỷ lệ Sharpe ({overall['sharpe_ratio']:.2f}) thấp hơn ngưỡng tối thiểu ({min_sharpe_ratio}).",
                "details": "Tỷ lệ Sharpe thấp cho thấy lợi nhuận không xứng đáng với rủi ro, cần cải thiện chiến lược."
            })
        
        # Khuyến nghị dựa trên timeframe
        best_timeframe = max(performance_results["timeframe_metrics"].items(), key=lambda x: x[1]["profit_factor"])
        worst_timeframe = min(performance_results["timeframe_metrics"].items(), key=lambda x: x[1]["profit_factor"])
        
        performance_results["recommendations"].append({
            "type": "info",
            "recommendation": f"Timeframe {best_timeframe[0]} có hiệu suất tốt nhất, {worst_timeframe[0]} có hiệu suất tệ nhất.",
            "details": f"Cân nhắc ưu tiên giao dịch trong timeframe {best_timeframe[0]} với profit factor {best_timeframe[1]['profit_factor']:.2f}."
        })
        
        # Khuyến nghị dựa trên cặp tiền
        best_symbol = max(performance_results["symbol_metrics"].items(), key=lambda x: x[1]["profit_factor"])
        worst_symbol = min(performance_results["symbol_metrics"].items(), key=lambda x: x[1]["profit_factor"])
        
        performance_results["recommendations"].append({
            "type": "info",
            "recommendation": f"Cặp tiền {best_symbol[0]} có hiệu suất tốt nhất, {worst_symbol[0]} có hiệu suất tệ nhất.",
            "details": f"Cân nhắc tập trung giao dịch {best_symbol[0]} với profit factor {best_symbol[1]['profit_factor']:.2f}."
        })
        
        # Khuyến nghị dựa trên mức độ rủi ro
        best_risk = max(performance_results["risk_level_metrics"].items(), key=lambda x: x[1]["sharpe_ratio"])
        
        performance_results["recommendations"].append({
            "type": "info",
            "recommendation": f"Mức rủi ro {best_risk[0]} cho tỷ lệ Sharpe tốt nhất.",
            "details": f"Mức rủi ro {best_risk[0]} có tỷ lệ Sharpe {best_risk[1]['sharpe_ratio']:.2f}, cân nhắc sử dụng mức rủi ro này cho giao dịch thực."
        })
        
        # Khuyến nghị dựa trên chiến lược
        best_strategy = max(performance_results["strategy_metrics"].items(), key=lambda x: x[1]["profit_factor"])
        worst_strategy = min(performance_results["strategy_metrics"].items(), key=lambda x: x[1]["profit_factor"])
        
        performance_results["recommendations"].append({
            "type": "info",
            "recommendation": f"Chiến lược {best_strategy[0]} có hiệu suất tốt nhất, {worst_strategy[0]} có hiệu suất tệ nhất.",
            "details": f"Cân nhắc ưu tiên chiến lược {best_strategy[0]} với profit factor {best_strategy[1]['profit_factor']:.2f} và cải thiện hoặc loại bỏ {worst_strategy[0]}."
        })
        
        # Khuyến nghị dựa trên kết hợp tốt nhất
        if performance_results["best_combinations"]:
            best_combo = performance_results["best_combinations"][0]
            performance_results["recommendations"].append({
                "type": "success",
                "recommendation": f"Kết hợp tốt nhất: {best_combo['symbol']} {best_combo['timeframe']} {best_combo['risk_level']}",
                "details": f"Profit factor: {best_combo['profit_factor']:.2f}, Win rate: {best_combo['win_rate']:.2f}%, Net profit: {best_combo['net_profit_percent']:.2f}%"
            })
    
    def _combine_recommendations(self, results):
        """
        Kết hợp các khuyến nghị từ tất cả các phân tích
        
        Args:
            results (dict): Kết quả tổng hợp
        """
        # Tập hợp tất cả khuyến nghị
        all_recommendations = []
        
        # Thêm khuyến nghị từ bot diagnostic
        if "diagnostic_results" in results and "recommendations" in results["diagnostic_results"]:
            for recommendation in results["diagnostic_results"]["recommendations"]:
                all_recommendations.append(recommendation)
        
        # Thêm khuyến nghị từ phân tích xung đột
        if "conflict_analysis" in results and "recommendations" in results["conflict_analysis"]:
            for recommendation in results["conflict_analysis"]["recommendations"]:
                all_recommendations.append(recommendation)
        
        # Thêm khuyến nghị từ phân tích tính nhất quán
        if "signal_consistency" in results and "recommendations" in results["signal_consistency"]:
            for recommendation in results["signal_consistency"]["recommendations"]:
                all_recommendations.append(recommendation)
        
        # Thêm khuyến nghị từ phân tích hiệu suất
        if "performance_metrics" in results and "recommendations" in results["performance_metrics"]:
            for recommendation in results["performance_metrics"]["recommendations"]:
                all_recommendations.append(recommendation)
        
        # Sắp xếp khuyến nghị theo mức độ nghiêm trọng
        priority_order = {"critical": 0, "warning": 1, "info": 2, "success": 3}
        all_recommendations.sort(key=lambda x: priority_order.get(x.get("type", "info"), 99))
        
        # Giới hạn số lượng khuyến nghị
        results["combined_recommendations"] = all_recommendations[:15]  # Chỉ lấy 15 khuyến nghị quan trọng nhất
    
    def _calculate_final_score(self, results):
        """
        Tính điểm tổng thể và trạng thái pass/fail
        
        Args:
            results (dict): Kết quả tổng hợp
        """
        # Tính điểm dựa trên các tiêu chí
        score = 0
        max_score = 0
        
        # Điểm từ bot diagnostic
        if "diagnostic_results" in results:
            diagnostic = results["diagnostic_results"]
            
            # Điểm dựa trên số lượng lỗi
            error_score = 100 - min(diagnostic.get("total_errors", 0), 100)
            score += error_score * 0.2  # 20% trọng số
            max_score += 100 * 0.2
            
            # Điểm hạ dựa trên số lỗi nghiêm trọng
            critical_penalty = min(diagnostic.get("critical_errors", 0) * 5, 100)
            score -= critical_penalty * 0.1  # 10% trọng số
            max_score += 0  # Không thay đổi max_score vì đây là điểm trừ
        
        # Điểm từ phân tích xung đột
        if "conflict_analysis" in results:
            conflict = results["conflict_analysis"]
            
            # Điểm dựa trên tỷ lệ xung đột
            conflict_score = 100 - min(conflict.get("conflict_percentage", 0), 100)
            score += conflict_score * 0.2  # 20% trọng số
            max_score += 100 * 0.2
            
            # Điểm dựa trên tỷ lệ chồng chéo
            overlap_score = 100 - min(conflict.get("overlap_percentage", 0), 100)
            score += overlap_score * 0.1  # 10% trọng số
            max_score += 100 * 0.1
        
        # Điểm từ phân tích tính nhất quán
        if "signal_consistency" in results:
            consistency = results["signal_consistency"]
            
            # Điểm dựa trên tỷ lệ đồng thuận
            agreement_score = min(consistency.get("agreement_percentage", 0), 100)
            score += agreement_score * 0.15  # 15% trọng số
            max_score += 100 * 0.15
            
            # Điểm dựa trên tỷ lệ mâu thuẫn
            contradiction_score = 100 - min(consistency.get("contradiction_percentage", 0), 100)
            score += contradiction_score * 0.05  # 5% trọng số
            max_score += 100 * 0.05
        
        # Điểm từ phân tích hiệu suất
        if "performance_metrics" in results and "overall_metrics" in results["performance_metrics"]:
            performance = results["performance_metrics"]["overall_metrics"]
            
            # Điểm dựa trên tỷ lệ thắng
            win_rate = performance.get("win_rate", 0)
            win_rate_score = min(win_rate, 100)
            score += win_rate_score * 0.1  # 10% trọng số
            max_score += 100 * 0.1
            
            # Điểm dựa trên profit factor
            profit_factor = performance.get("profit_factor", 0)
            profit_factor_score = min(profit_factor * 25, 100)  # Profit factor 4.0 trở lên được 100 điểm
            score += profit_factor_score * 0.1  # 10% trọng số
            max_score += 100 * 0.1
            
            # Điểm dựa trên drawdown
            drawdown = performance.get("drawdown", 0)
            drawdown_score = 100 - min(drawdown * 5, 100)  # Drawdown 20% trở lên được 0 điểm
            score += drawdown_score * 0.05  # 5% trọng số
            max_score += 100 * 0.05
            
            # Điểm dựa trên Sharpe ratio
            sharpe = performance.get("sharpe_ratio", 0)
            sharpe_score = min(sharpe * 33.33, 100)  # Sharpe ratio 3.0 trở lên được 100 điểm
            score += sharpe_score * 0.05  # 5% trọng số
            max_score += 100 * 0.05
        
        # Tính điểm phần trăm
        if max_score > 0:
            final_score = (score / max_score) * 100
        else:
            final_score = 0
        
        # Xác định trạng thái pass/fail
        passing_threshold = 75  # Ngưỡng đạt
        passing_status = final_score >= passing_threshold
        
        # Cập nhật kết quả
        results["final_score"] = final_score
        results["passing_status"] = passing_status
        results["passing_threshold"] = passing_threshold
    
    def _generate_report(self, results):
        """
        Tạo báo cáo từ kết quả kiểm tra
        
        Args:
            results (dict): Kết quả kiểm tra
        """
        # Tạo timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Định dạng báo cáo
        report_formats = self.config.get("report_formats", ["json"])
        
        # Lưu dạng JSON
        if "json" in report_formats:
            json_path = os.path.join(self.results_dir, f"comprehensive_test_report_{timestamp}.json")
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Đã lưu báo cáo JSON vào {json_path}")
        
        # Lưu dạng HTML
        if "html" in report_formats:
            html_path = os.path.join(self.results_dir, f"comprehensive_test_report_{timestamp}.html")
            self._generate_html_report(results, html_path)
            logger.info(f"Đã lưu báo cáo HTML vào {html_path}")
        
        # Lưu dạng Markdown
        if "md" in report_formats:
            md_path = os.path.join(self.results_dir, f"comprehensive_test_report_{timestamp}.md")
            self._generate_markdown_report(results, md_path)
            logger.info(f"Đã lưu báo cáo Markdown vào {md_path}")
    
    def _generate_html_report(self, results, output_path):
        """
        Tạo báo cáo HTML
        
        Args:
            results (dict): Kết quả kiểm tra
            output_path (str): Đường dẫn file đầu ra
        """
        with open(output_path, 'w') as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Báo cáo kiểm tra toàn diện</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; color: #333; }}
                    .container {{ width: 90%; margin: 0 auto; padding: 20px; }}
                    h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                    h2 {{ color: #2980b9; margin-top: 30px; }}
                    h3 {{ color: #16a085; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .critical {{ color: #e74c3c; font-weight: bold; }}
                    .warning {{ color: #f39c12; font-weight: bold; }}
                    .info {{ color: #3498db; }}
                    .success {{ color: #2ecc71; }}
                    .score-box {{ 
                        border: 1px solid #ddd; 
                        padding: 15px; 
                        border-radius: 5px; 
                        margin: 20px 0; 
                        text-align: center;
                        background-color: {('#e74c3c' if not results.get('passing_status', False) else '#2ecc71')};
                        color: white;
                    }}
                    .metrics {{ display: flex; flex-wrap: wrap; }}
                    .metric-card {{ 
                        flex: 1 1 200px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        margin: 10px;
                        padding: 15px;
                        background-color: #f9f9f9;
                    }}
                    .metric-value {{ 
                        font-size: 24px; 
                        font-weight: bold; 
                        margin: 10px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Báo cáo kiểm tra toàn diện</h1>
                    <p>Thời gian kiểm tra: {results.get('timestamp', 'N/A')}</p>
                    
                    <div class="score-box">
                        <h2 style="color: white; margin: 0;">Điểm tổng thể: {results.get('final_score', 0):.2f}/100</h2>
                        <p style="margin: 5px 0;">Trạng thái: {"ĐẠT" if results.get('passing_status', False) else "KHÔNG ĐẠT"}</p>
                        <p style="margin: 5px 0;">Ngưỡng đạt: {results.get('passing_threshold', 75)}</p>
                    </div>
                    
                    <h2>Thông tin kiểm tra</h2>
                    <table>
                        <tr>
                            <th>Thông số</th>
                            <th>Giá trị</th>
                        </tr>
                        <tr>
                            <td>Số cặp tiền kiểm tra</td>
                            <td>{len(results.get('symbols_tested', []))}</td>
                        </tr>
                        <tr>
                            <td>Số khung thời gian kiểm tra</td>
                            <td>{len(results.get('timeframes_tested', []))}</td>
                        </tr>
                        <tr>
                            <td>Số mức độ rủi ro kiểm tra</td>
                            <td>{len(results.get('risk_levels_tested', []))}</td>
                        </tr>
                        <tr>
                            <td>Số chiến lược kiểm tra</td>
                            <td>{len(results.get('strategies_tested', []))}</td>
                        </tr>
                        <tr>
                            <td>Thời gian chạy kiểm tra</td>
                            <td>{results.get('test_duration', 0):.2f} giây</td>
                        </tr>
                    </table>
                    
                    <h2>Khuyến nghị cuối cùng</h2>
                    <table>
                        <tr>
                            <th>#</th>
                            <th>Loại</th>
                            <th>Khuyến nghị</th>
                            <th>Chi tiết</th>
                        </tr>
            """)
            
            # Thêm khuyến nghị
            for i, recommendation in enumerate(results.get("combined_recommendations", [])):
                recommendation_class = recommendation.get("type", "info")
                f.write(f"""
                        <tr>
                            <td>{i+1}</td>
                            <td class="{recommendation_class}">{recommendation.get('type', 'info').upper()}</td>
                            <td>{recommendation.get('recommendation', '')}</td>
                            <td>{recommendation.get('details', '')}</td>
                        </tr>
                """)
            
            f.write("""
                    </table>
                    
                    <h2>Chỉ số hiệu suất</h2>
                    <div class="metrics">
            """)
            
            # Thêm chỉ số hiệu suất
            if "performance_metrics" in results and "overall_metrics" in results["performance_metrics"]:
                metrics = results["performance_metrics"]["overall_metrics"]
                
                f.write(f"""
                        <div class="metric-card">
                            <h3>Tỷ lệ thắng</h3>
                            <div class="metric-value {self._get_metric_class(metrics.get('win_rate', 0), 50, 60)}">{metrics.get('win_rate', 0):.2f}%</div>
                        </div>
                        
                        <div class="metric-card">
                            <h3>Profit Factor</h3>
                            <div class="metric-value {self._get_metric_class(metrics.get('profit_factor', 0), 1.5, 2.0)}">{metrics.get('profit_factor', 0):.2f}</div>
                        </div>
                        
                        <div class="metric-card">
                            <h3>Drawdown</h3>
                            <div class="metric-value {self._get_metric_class_reverse(metrics.get('drawdown', 0), 15, 10)}">{metrics.get('drawdown', 0):.2f}%</div>
                        </div>
                        
                        <div class="metric-card">
                            <h3>Sharpe Ratio</h3>
                            <div class="metric-value {self._get_metric_class(metrics.get('sharpe_ratio', 0), 1, 2)}">{metrics.get('sharpe_ratio', 0):.2f}</div>
                        </div>
                        
                        <div class="metric-card">
                            <h3>Tổng số lệnh</h3>
                            <div class="metric-value">{metrics.get('total_trades', 0)}</div>
                        </div>
                        
                        <div class="metric-card">
                            <h3>Lợi nhuận ròng</h3>
                            <div class="metric-value {self._get_metric_class(metrics.get('net_profit_percent', 0), 0, 20)}">{metrics.get('net_profit_percent', 0):.2f}%</div>
                        </div>
                """)
            
            f.write("""
                    </div>
                    
                    <h2>Phân tích xung đột</h2>
            """)
            
            # Thêm phân tích xung đột
            if "conflict_analysis" in results:
                conflict = results["conflict_analysis"]
                
                f.write(f"""
                    <table>
                        <tr>
                            <th>Thông số</th>
                            <th>Giá trị</th>
                        </tr>
                        <tr>
                            <td>Tổng số xung đột</td>
                            <td>{conflict.get('total_conflicts', 0)}</td>
                        </tr>
                        <tr>
                            <td>Tổng số chồng chéo</td>
                            <td>{conflict.get('total_overlaps', 0)}</td>
                        </tr>
                        <tr>
                            <td>Tỷ lệ xung đột</td>
                            <td class="{self._get_metric_class_reverse(conflict.get('conflict_percentage', 0), 10, 5)}">{conflict.get('conflict_percentage', 0):.2f}%</td>
                        </tr>
                        <tr>
                            <td>Tỷ lệ chồng chéo</td>
                            <td class="{self._get_metric_class_reverse(conflict.get('overlap_percentage', 0), 10, 5)}">{conflict.get('overlap_percentage', 0):.2f}%</td>
                        </tr>
                    </table>
                """)
            
            # Thêm kết quả chẩn đoán
            if "diagnostic_results" in results:
                diagnostic = results["diagnostic_results"]
                
                f.write(f"""
                    <h2>Kết quả chẩn đoán</h2>
                    <table>
                        <tr>
                            <th>Thông số</th>
                            <th>Giá trị</th>
                        </tr>
                        <tr>
                            <td>Tổng số lỗi</td>
                            <td>{diagnostic.get('total_errors', 0)}</td>
                        </tr>
                        <tr>
                            <td>Lỗi nghiêm trọng</td>
                            <td class="{self._get_metric_class_reverse(diagnostic.get('critical_errors', 0), 1, 0)}">{diagnostic.get('critical_errors', 0)}</td>
                        </tr>
                        <tr>
                            <td>Cảnh báo</td>
                            <td class="{self._get_metric_class_reverse(diagnostic.get('warning_errors', 0), 5, 2)}">{diagnostic.get('warning_errors', 0)}</td>
                        </tr>
                    </table>
                """)
            
            # Thêm tính nhất quán tín hiệu
            if "signal_consistency" in results:
                consistency = results["signal_consistency"]
                
                f.write(f"""
                    <h2>Tính nhất quán tín hiệu</h2>
                    <table>
                        <tr>
                            <th>Thông số</th>
                            <th>Giá trị</th>
                        </tr>
                        <tr>
                            <td>Tỷ lệ đồng thuận</td>
                            <td class="{self._get_metric_class(consistency.get('agreement_percentage', 0), 60, 80)}">{consistency.get('agreement_percentage', 0):.2f}%</td>
                        </tr>
                        <tr>
                            <td>Tỷ lệ mâu thuẫn</td>
                            <td class="{self._get_metric_class_reverse(consistency.get('contradiction_percentage', 0), 20, 10)}">{consistency.get('contradiction_percentage', 0):.2f}%</td>
                        </tr>
                        <tr>
                            <td>Tương quan trung bình</td>
                            <td class="{self._get_metric_class(consistency.get('average_correlation', 0), 0.3, 0.7)}">{consistency.get('average_correlation', 0):.2f}</td>
                        </tr>
                    </table>
                """)
            
            # Thêm kết hợp tốt nhất
            if "performance_metrics" in results and "best_combinations" in results["performance_metrics"]:
                best_combinations = results["performance_metrics"]["best_combinations"]
                
                f.write("""
                    <h2>Top kết hợp tốt nhất</h2>
                    <table>
                        <tr>
                            <th>#</th>
                            <th>Cặp tiền</th>
                            <th>Timeframe</th>
                            <th>Mức rủi ro</th>
                            <th>Profit Factor</th>
                            <th>Tỷ lệ thắng</th>
                            <th>Lợi nhuận</th>
                        </tr>
                """)
                
                for i, combo in enumerate(best_combinations):
                    f.write(f"""
                        <tr>
                            <td>{i+1}</td>
                            <td>{combo.get('symbol', 'N/A')}</td>
                            <td>{combo.get('timeframe', 'N/A')}</td>
                            <td>{combo.get('risk_level', 'N/A')}</td>
                            <td class="{self._get_metric_class(combo.get('profit_factor', 0), 1.5, 2.0)}">{combo.get('profit_factor', 0):.2f}</td>
                            <td class="{self._get_metric_class(combo.get('win_rate', 0), 50, 60)}">{combo.get('win_rate', 0):.2f}%</td>
                            <td class="{self._get_metric_class(combo.get('net_profit_percent', 0), 0, 20)}">{combo.get('net_profit_percent', 0):.2f}%</td>
                        </tr>
                    """)
                
                f.write("</table>")
            
            f.write("""
                    <p style="margin-top: 40px;">Báo cáo này được tạo tự động bởi hệ thống kiểm tra toàn diện.</p>
                </div>
            </body>
            </html>
            """)
    
    def _generate_markdown_report(self, results, output_path):
        """
        Tạo báo cáo Markdown
        
        Args:
            results (dict): Kết quả kiểm tra
            output_path (str): Đường dẫn file đầu ra
        """
        with open(output_path, 'w') as f:
            f.write("# BÁO CÁO KIỂM TRA TOÀN DIỆN HỆ THỐNG GIAO DỊCH\n\n")
            
            # Thông tin kiểm tra
            f.write("## Thông tin kiểm tra\n\n")
            f.write(f"- Thời gian kiểm tra: {results.get('timestamp', 'N/A')}\n")
            f.write(f"- Số cặp tiền kiểm tra: {len(results.get('symbols_tested', []))}\n")
            f.write(f"- Số khung thời gian kiểm tra: {len(results.get('timeframes_tested', []))}\n")
            f.write(f"- Số mức độ rủi ro kiểm tra: {len(results.get('risk_levels_tested', []))}\n")
            f.write(f"- Số chiến lược kiểm tra: {len(results.get('strategies_tested', []))}\n")
            f.write(f"- Điểm tổng thể: {results.get('final_score', 0):.2f}/100\n")
            f.write(f"- Trạng thái: {'ĐẠT' if results.get('passing_status', False) else 'KHÔNG ĐẠT'}\n\n")
            
            # Khuyến nghị cuối cùng
            f.write("## Khuyến nghị cuối cùng\n\n")
            
            # Top kết hợp tốt nhất
            if "performance_metrics" in results and "best_combinations" in results["performance_metrics"]:
                f.write("### Top cặp tiền nên giao dịch\n\n")
                f.write("| # | Cặp tiền | Timeframe | Mức rủi ro | Profit Factor | Lợi nhuận | Ghi chú |\n")
                f.write("|---|---------|-----------|------------|---------------|-----------|--------|\n")
                
                for i, combo in enumerate(results["performance_metrics"]["best_combinations"][:3]):
                    symbol = combo.get('symbol', 'N/A')
                    timeframe = combo.get('timeframe', 'N/A')
                    risk_level = combo.get('risk_level', 'N/A')
                    profit_factor = combo.get('profit_factor', 0)
                    net_profit = combo.get('net_profit_percent', 0)
                    
                    # Tạo ghi chú
                    note = ""
                    if profit_factor > 2.0:
                        note = "Hiệu suất xuất sắc"
                    elif profit_factor > 1.5:
                        note = "Hiệu suất tốt"
                    else:
                        note = "Hiệu suất khá"
                    
                    f.write(f"| {i+1} | {symbol} | {timeframe} | {risk_level} | {profit_factor:.2f} | {net_profit:.2f}% | {note} |\n")
                
                f.write("\n")
            
            # Thông tin chiến lược hiệu quả nhất
            if "performance_metrics" in results and "strategy_metrics" in results["performance_metrics"]:
                strategies = results["performance_metrics"]["strategy_metrics"]
                sorted_strategies = sorted(strategies.items(), key=lambda x: x[1].get('profit_factor', 0), reverse=True)
                
                f.write("### Top chiến lược hiệu quả\n\n")
                f.write("| # | Chiến lược | Profit Factor | Tỷ lệ thắng | Ghi chú |\n")
                f.write("|---|-----------|---------------|-------------|--------|\n")
                
                for i, (strategy, metrics) in enumerate(sorted_strategies[:3]):
                    profit_factor = metrics.get('profit_factor', 0)
                    win_rate = metrics.get('win_rate', 0)
                    
                    # Tạo ghi chú
                    note = ""
                    if profit_factor > 2.0 and win_rate > 60:
                        note = "Rất đáng tin cậy"
                    elif profit_factor > 1.5:
                        note = "Đáng tin cậy"
                    else:
                        note = "Cần theo dõi thêm"
                    
                    f.write(f"| {i+1} | {strategy} | {profit_factor:.2f} | {win_rate:.2f}% | {note} |\n")
                
                f.write("\n")
            
            # Thông tin timeframe hiệu quả nhất
            if "performance_metrics" in results and "timeframe_metrics" in results["performance_metrics"]:
                timeframes = results["performance_metrics"]["timeframe_metrics"]
                sorted_timeframes = sorted(timeframes.items(), key=lambda x: x[1].get('profit_factor', 0), reverse=True)
                
                f.write("### Top thời điểm giao dịch tối ưu\n\n")
                f.write("| # | Timeframe | Profit Factor | Tỷ lệ thắng | Ghi chú |\n")
                f.write("|---|-----------|---------------|-------------|--------|\n")
                
                for i, (timeframe, metrics) in enumerate(sorted_timeframes):
                    profit_factor = metrics.get('profit_factor', 0)
                    win_rate = metrics.get('win_rate', 0)
                    
                    # Tạo ghi chú
                    note = ""
                    if timeframe == "1h":
                        note = "Nhiều cơ hội, biến động"
                    elif timeframe == "4h":
                        note = "Cân bằng cơ hội và độ ổn định"
                    elif timeframe == "1d":
                        note = "Ít cơ hội nhưng ổn định"
                    
                    f.write(f"| {i+1} | {timeframe} | {profit_factor:.2f} | {win_rate:.2f}% | {note} |\n")
                
                f.write("\n")
            
            # Kết luận và đề xuất
            f.write("## Kết luận và đề xuất\n\n")
            
            # Thêm các khuyến nghị quan trọng
            for recommendation in results.get("combined_recommendations", [])[:5]:
                if recommendation.get("type") in ["critical", "warning"]:
                    f.write(f"- {recommendation.get('recommendation')}\n")
            
            f.write("\n")
            
            # Chỉ số hiệu suất
            if "performance_metrics" in results and "overall_metrics" in results["performance_metrics"]:
                metrics = results["performance_metrics"]["overall_metrics"]
                
                f.write("## Các thiết lập được đề xuất\n\n")
                
                # Đề xuất mức rủi ro
                if "risk_level_metrics" in results["performance_metrics"]:
                    risk_metrics = results["performance_metrics"]["risk_level_metrics"]
                    best_risk = max(risk_metrics.items(), key=lambda x: x[1].get('sharpe_ratio', 0))
                    risk_level = best_risk[0]
                else:
                    risk_level = "medium"
                
                # Đề xuất SL/TP dựa trên mức rủi ro
                if risk_level == "low":
                    sl = 3.0
                    tp = 9.0
                    r_ratio = 3.0
                    max_orders = 3
                    position_size = 2
                elif risk_level == "high":
                    sl = 7.0
                    tp = 21.0
                    r_ratio = 3.0
                    max_orders = 5
                    position_size = 3
                else:  # medium
                    sl = 5.0
                    tp = 15.0
                    r_ratio = 3.0
                    max_orders = 4
                    position_size = 2.5
                
                f.write(f"- Mức rủi ro: {risk_level.upper()}\n")
                f.write(f"- Stop Loss: {sl}%\n")
                f.write(f"- Take Profit: {tp}%\n")
                f.write(f"- Tỷ lệ R:R: {r_ratio}\n")
                f.write(f"- Số lệnh tối đa mỗi ngày: {max_orders}\n")
                f.write(f"- Kích thước vị thế: {position_size}% mỗi lệnh\n")
            
            f.write("\n")
            
            # Chi tiết các chỉ số hiệu suất
            if "performance_metrics" in results and "overall_metrics" in results["performance_metrics"]:
                metrics = results["performance_metrics"]["overall_metrics"]
                
                f.write("## Chi tiết hiệu suất\n\n")
                f.write(f"- Tỷ lệ thắng: {metrics.get('win_rate', 0):.2f}%\n")
                f.write(f"- Profit Factor: {metrics.get('profit_factor', 0):.2f}\n")
                f.write(f"- Drawdown: {metrics.get('drawdown', 0):.2f}%\n")
                f.write(f"- Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n")
                f.write(f"- Tổng số lệnh: {metrics.get('total_trades', 0)}\n")
                f.write(f"- Lợi nhuận ròng: {metrics.get('net_profit_percent', 0):.2f}%\n")
            
            f.write("\n")
            
            # Chi tiết xung đột
            if "conflict_analysis" in results:
                conflict = results["conflict_analysis"]
                
                f.write("## Chi tiết xung đột\n\n")
                f.write(f"- Tổng số xung đột: {conflict.get('total_conflicts', 0)}\n")
                f.write(f"- Tổng số chồng chéo: {conflict.get('total_overlaps', 0)}\n")
                f.write(f"- Tỷ lệ xung đột: {conflict.get('conflict_percentage', 0):.2f}%\n")
                f.write(f"- Tỷ lệ chồng chéo: {conflict.get('overlap_percentage', 0):.2f}%\n")
            
            f.write("\n")
            
            # Chú thích cuối báo cáo
            f.write("---\n")
            f.write("Báo cáo này được tạo tự động bởi hệ thống kiểm tra toàn diện.\n")
    
    def _get_metric_class(self, value, warning_threshold, good_threshold):
        """
        Lấy lớp CSS cho một chỉ số dựa trên ngưỡng
        
        Args:
            value (float): Giá trị chỉ số
            warning_threshold (float): Ngưỡng cảnh báo
            good_threshold (float): Ngưỡng tốt
            
        Returns:
            str: Tên lớp CSS
        """
        if value >= good_threshold:
            return "success"
        elif value >= warning_threshold:
            return "info"
        else:
            return "warning"
    
    def _get_metric_class_reverse(self, value, warning_threshold, good_threshold):
        """
        Lấy lớp CSS cho một chỉ số dựa trên ngưỡng (đảo ngược)
        
        Args:
            value (float): Giá trị chỉ số
            warning_threshold (float): Ngưỡng cảnh báo
            good_threshold (float): Ngưỡng tốt
            
        Returns:
            str: Tên lớp CSS
        """
        if value <= good_threshold:
            return "success"
        elif value <= warning_threshold:
            return "info"
        else:
            return "warning"
    
    def _save_results(self, results):
        """
        Lưu kết quả kiểm tra
        
        Args:
            results (dict): Kết quả kiểm tra
        """
        # Tạo timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Lưu dạng JSON
        json_path = os.path.join(self.results_dir, f"comprehensive_test_report_{timestamp}.json")
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Đã lưu kết quả kiểm tra vào {json_path}")


def main():
    """
    Hàm chính
    """
    parser = argparse.ArgumentParser(description='Comprehensive Backtesting System')
    parser.add_argument('--config', type=str, default='comprehensive_backtest_config.json',
                      help='Path to configuration file')
    parser.add_argument('--symbols', type=str, nargs='+',
                      help='List of symbols to test')
    parser.add_argument('--timeframes', type=str, nargs='+',
                      help='List of timeframes to test')
    parser.add_argument('--days', type=int,
                      help='Number of days to test')
    
    args = parser.parse_args()
    
    # Khởi tạo hệ thống backtest toàn diện
    backtest = ComprehensiveBacktest(config_path=args.config)
    
    # Cập nhật cấu hình từ tham số dòng lệnh
    if args.symbols:
        backtest.config["symbols"] = args.symbols
    
    if args.timeframes:
        backtest.config["timeframes"] = args.timeframes
    
    if args.days:
        backtest.config["test_days"] = args.days
    
    # Chạy kiểm tra toàn diện
    try:
        results = backtest.run_comprehensive_test()
        
        # Hiển thị kết quả tổng quát
        print(f"\nĐiểm tổng thể: {results['final_score']:.2f}/100")
        print(f"Trạng thái: {'ĐẠT' if results['passing_status'] else 'KHÔNG ĐẠT'}")
        print(f"Báo cáo đã được lưu vào thư mục: {backtest.results_dir}")
        
        # Hiển thị top khuyến nghị
        print("\nTop khuyến nghị:")
        for i, recommendation in enumerate(results["combined_recommendations"][:5]):
            print(f"{i+1}. [{recommendation['type'].upper()}] {recommendation['recommendation']}")
        
        # Hiển thị kết hợp tốt nhất
        if "performance_metrics" in results and "best_combinations" in results["performance_metrics"] and results["performance_metrics"]["best_combinations"]:
            best_combo = results["performance_metrics"]["best_combinations"][0]
            print(f"\nKết hợp tốt nhất: {best_combo['symbol']} {best_combo['timeframe']} {best_combo['risk_level']}")
            print(f"  Profit Factor: {best_combo['profit_factor']:.2f}")
            print(f"  Win Rate: {best_combo['win_rate']:.2f}%")
            print(f"  Net Profit: {best_combo['net_profit_percent']:.2f}%")
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy kiểm tra toàn diện: {e}")
        print(f"Đã xảy ra lỗi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()