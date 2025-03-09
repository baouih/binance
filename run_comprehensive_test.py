#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bài kiểm tra toàn diện cho hệ thống giao dịch
Kiểm tra tất cả các thuật toán với mức rủi ro cao trên nhiều cặp tiền
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('comprehensive_test.log')
    ]
)

logger = logging.getLogger('comprehensive_test')

# Import các module cần thiết
try:
    from high_risk_entry_tester import HighRiskEntryTester
except ImportError:
    logger.error("Không thể import module HighRiskEntryTester. Hãy đảm bảo file high_risk_entry_tester.py tồn tại.")
    sys.exit(1)

try:
    from time_optimized_strategy import TimeOptimizedStrategy
except ImportError:
    logger.error("Không thể import module TimeOptimizedStrategy. Hãy đảm bảo file time_optimized_strategy.py tồn tại.")
    sys.exit(1)

try:
    from time_based_trading_system import TimeBasedTradingSystem
except ImportError:
    logger.error("Không thể import module TimeBasedTradingSystem. Hãy đảm bảo file time_based_trading_system.py tồn tại.")
    sys.exit(1)

# Danh sách các coin phổ biến để kiểm tra
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT", "DOGEUSDT", 
    "ADAUSDT", "XRPUSDT", "DOTUSDT", "AVAXUSDT", "MATICUSDT", "LTCUSDT",
    "ATOMUSDT", "NEARUSDT", "UNIUSDT", "AAVEUSDT", "SANDUSDT", "AXSUSDT"
]

# Các khung thời gian kiểm tra mặc định
DEFAULT_TIMEFRAMES = [
    {"name": "London Open", "start_hour": 15, "start_minute": 0, "end_hour": 17, "end_minute": 0, "direction": "short"},
    {"name": "New York Open", "start_hour": 20, "start_minute": 30, "end_hour": 22, "end_minute": 30, "direction": "short"},
    {"name": "Daily Candle Close", "start_hour": 6, "start_minute": 30, "end_hour": 7, "end_minute": 30, "direction": "long"},
    {"name": "Major News Events", "start_hour": 21, "start_minute": 30, "end_hour": 22, "end_minute": 0, "direction": "short"}
]

class ComprehensiveTest:
    """
    Kiểm tra toàn diện hệ thống giao dịch
    """
    
    def __init__(
        self,
        symbols=None,
        days=30,
        risk_level="high",
        output_dir="comprehensive_test_results"
    ):
        """
        Khởi tạo bài kiểm tra toàn diện
        
        Args:
            symbols (list, optional): Danh sách các cặp tiền cần kiểm tra. Mặc định là None (tất cả các cặp tiền phổ biến).
            days (int, optional): Số ngày dữ liệu để kiểm tra. Mặc định là 30.
            risk_level (str, optional): Mức độ rủi ro (low, balanced, high). Mặc định là "high".
            output_dir (str, optional): Thư mục lưu kết quả. Mặc định là "comprehensive_test_results".
        """
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.days = days
        self.risk_level = risk_level
        self.output_dir = output_dir
        
        # Tạo thư mục đầu ra nếu chưa tồn tại
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Khởi tạo các tester và chiến lược
        self.entry_tester = HighRiskEntryTester(
            config_path="configs/high_risk_entry_config.json",
            strategy_config_path="configs/time_optimized_strategy_config.json"
        )
        
        self.time_strategy = TimeOptimizedStrategy(
            config_path="configs/time_optimized_strategy_config.json"
        )
        
        # Điều chỉnh cấu hình theo mức độ rủi ro
        self._configure_risk_level()
        
        # Kết quả kiểm tra
        self.test_results = {}
        
        logger.info(f"Đã khởi tạo ComprehensiveTest với {len(self.symbols)} cặp tiền, mức độ rủi ro {self.risk_level.upper()}")
    
    def _configure_risk_level(self):
        """
        Điều chỉnh cấu hình theo mức độ rủi ro
        """
        if self.risk_level == "low":
            # Mức độ rủi ro thấp
            self.entry_tester.config["test_settings"]["risk_reward_ratio"] = 2.0
            self.entry_tester.config["test_settings"]["stop_loss_percent"] = 5.0
            self.entry_tester.config["test_settings"]["take_profit_percent"] = 10.0
            self.entry_tester._save_config()
            
            logger.info("Đã cấu hình mức độ rủi ro THẤP (R:R=2.0, SL=5%, TP=10%)")
        elif self.risk_level == "balanced":
            # Mức độ rủi ro cân bằng
            self.entry_tester.config["test_settings"]["risk_reward_ratio"] = 2.5
            self.entry_tester.config["test_settings"]["stop_loss_percent"] = 6.0
            self.entry_tester.config["test_settings"]["take_profit_percent"] = 15.0
            self.entry_tester._save_config()
            
            logger.info("Đã cấu hình mức độ rủi ro CÂN BẰNG (R:R=2.5, SL=6%, TP=15%)")
        else:
            # Mức độ rủi ro cao (mặc định)
            self.entry_tester.config["test_settings"]["risk_reward_ratio"] = 3.0
            self.entry_tester.config["test_settings"]["stop_loss_percent"] = 7.0
            self.entry_tester.config["test_settings"]["take_profit_percent"] = 21.0
            self.entry_tester._save_config()
            
            logger.info("Đã cấu hình mức độ rủi ro CAO (R:R=3.0, SL=7%, TP=21%)")
    
    def download_market_data(self):
        """
        Tải dữ liệu thị trường từ Binance
        """
        logger.info("Đang tải dữ liệu thị trường từ Binance...")
        
        for symbol in self.symbols:
            try:
                # Tải dữ liệu 1h cho mỗi cặp tiền
                self.entry_tester.load_test_data(symbol, "1h", self.days)
                logger.info(f"Đã tải dữ liệu {symbol} (1h, {self.days} ngày)")
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu {symbol}: {str(e)}")
    
    def run_entry_tests(self):
        """
        Chạy kiểm tra các điểm vào lệnh
        """
        logger.info("Đang chạy kiểm tra các điểm vào lệnh rủi ro cao...")
        
        # Cập nhật danh sách các cặp tiền trong entry_tester
        self.entry_tester.test_symbols = self.symbols
        self.entry_tester._save_config()
        
        # Chạy kiểm tra
        self.entry_tester.run_tests()
        
        # Lưu kết quả
        self.test_results["entry_tests"] = self.entry_tester.test_results
        
        # Tạo tóm tắt
        entry_summary = self.entry_tester.generate_summary()
        self.test_results["entry_summary"] = entry_summary
        
        # In tóm tắt
        self.entry_tester.print_summary()
    
    def run_time_window_analysis(self):
        """
        Chạy phân tích cửa sổ thời gian tối ưu
        """
        logger.info("Đang phân tích các cửa sổ thời gian tối ưu...")
        
        # Lấy tất cả các thời điểm tối ưu từ chiến lược
        optimal_times = self.time_strategy.get_all_optimal_times()
        
        # Lấy ngày tốt nhất trong tuần
        best_days = self.time_strategy.get_best_trading_days()
        
        # Tạo khuyến nghị giao dịch dựa trên thời gian
        time_recommendations = []
        
        for time_info in optimal_times:
            if time_info["win_rate"] >= 70.0:
                time_recommendations.append({
                    "session": time_info["name"],
                    "time": f"{time_info['start_time']} - {time_info['end_time']}",
                    "win_rate": time_info["win_rate"],
                    "direction": time_info["direction"],
                    "symbols": time_info["symbols"],
                    "confidence": "Cao" if time_info["win_rate"] >= 85.0 else "Trung bình"
                })
        
        # Sắp xếp theo tỷ lệ thắng giảm dần
        time_recommendations.sort(key=lambda x: x["win_rate"], reverse=True)
        
        # Lưu kết quả
        self.test_results["time_analysis"] = {
            "optimal_times": optimal_times,
            "best_days": best_days,
            "recommendations": time_recommendations
        }
        
        # In kết quả
        print("\n===== PHÂN TÍCH CỬA SỔ THỜI GIAN TỐI ƯU =====")
        
        print("\nTop thời điểm giao dịch có tỷ lệ thắng cao:")
        for i, rec in enumerate(time_recommendations, 1):
            print(f"{i}. {rec['session']} ({rec['time']}) - {rec['win_rate']:.1f}% - {rec['direction'].upper()}")
            print(f"   Coin khuyến nghị: {', '.join(rec['symbols']) if rec['symbols'] else 'Không có khuyến nghị cụ thể'}")
            print(f"   Độ tin cậy: {rec['confidence']}")
            print()
        
        print("\nCác ngày giao dịch tốt nhất:")
        for day in best_days[:3]:
            print(f"- {day['name']} - Tỷ lệ thắng: {day['win_rate']:.1f}% - Số lệnh tối đa: {day['max_trades']}")
    
    def run_combined_strategy_test(self):
        """
        Kiểm tra chiến lược kết hợp giữa thời gian tối ưu và điểm vào rủi ro cao
        """
        logger.info("Đang kiểm tra chiến lược kết hợp...")
        
        # Lấy các kết quả từ high_risk_entry_tester
        entry_summary = self.test_results.get("entry_summary", {})
        
        # Lấy các khung thời gian tối ưu từ time_optimized_strategy
        optimal_times = self.time_strategy.get_all_optimal_times()
        
        # Lọc ra các cặp tiền hiệu quả nhất
        best_symbols = {}
        for symbol, symbol_data in entry_summary.get("by_symbol", {}).items():
            if symbol_data["total_trades"] >= 3 and symbol_data["win_rate"] >= 60.0:
                best_symbols[symbol] = symbol_data["win_rate"]
        
        # Sắp xếp theo tỷ lệ thắng giảm dần
        best_symbols = {k: v for k, v in sorted(best_symbols.items(), key=lambda item: item[1], reverse=True)}
        
        # Tạo các khuyến nghị kết hợp
        combined_recommendations = []
        
        for time_info in optimal_times:
            if time_info["win_rate"] < 70.0:
                continue
            
            for symbol, win_rate in best_symbols.items():
                # Kiểm tra xem symbol có trong danh sách khuyến nghị của thời gian này không
                is_recommended = symbol in time_info["symbols"] if time_info["symbols"] else False
                
                # Tính điểm tin cậy kết hợp
                combined_score = (time_info["win_rate"] + win_rate) / 2
                
                if combined_score >= 70.0 or is_recommended:
                    combined_recommendations.append({
                        "symbol": symbol,
                        "session": time_info["name"],
                        "time": f"{time_info['start_time']} - {time_info['end_time']}",
                        "direction": time_info["direction"],
                        "combined_score": combined_score,
                        "time_win_rate": time_info["win_rate"],
                        "symbol_win_rate": win_rate,
                        "is_recommended": is_recommended
                    })
        
        # Sắp xếp theo điểm kết hợp giảm dần
        combined_recommendations.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # Lưu kết quả
        self.test_results["combined_strategy"] = {
            "best_symbols": best_symbols,
            "recommendations": combined_recommendations
        }
        
        # In kết quả
        print("\n===== KHUYẾN NGHỊ CHIẾN LƯỢC KẾT HỢP =====")
        
        print("\nTop khuyến nghị giao dịch kết hợp thời gian và cặp tiền:")
        for i, rec in enumerate(combined_recommendations[:10], 1):
            print(f"{i}. {rec['symbol']} - {rec['session']} ({rec['time']}) - {rec['direction'].upper()}")
            print(f"   Điểm kết hợp: {rec['combined_score']:.1f}% (Thời gian: {rec['time_win_rate']:.1f}%, Cặp tiền: {rec['symbol_win_rate']:.1f}%)")
            print(f"   {'✓ Nằm trong danh sách khuyến nghị' if rec['is_recommended'] else '✗ Không nằm trong danh sách khuyến nghị'}")
            print()
        
        print("\nTop cặp tiền hiệu quả nhất:")
        for i, (symbol, win_rate) in enumerate(list(best_symbols.items())[:5], 1):
            print(f"{i}. {symbol} - Tỷ lệ thắng: {win_rate:.1f}%")
    
    def generate_final_report(self):
        """
        Tạo báo cáo cuối cùng
        """
        logger.info("Đang tạo báo cáo cuối cùng...")
        
        # Lấy tóm tắt từ các bài kiểm tra
        entry_summary = self.test_results.get("entry_summary", {})
        time_analysis = self.test_results.get("time_analysis", {})
        combined_strategy = self.test_results.get("combined_strategy", {})
        
        # Tạo báo cáo tổng hợp
        report = {
            "test_summary": {
                "symbols_tested": self.symbols,
                "risk_level": self.risk_level,
                "days_tested": self.days,
                "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "entry_test_results": entry_summary,
            "time_window_analysis": time_analysis,
            "combined_strategy_results": combined_strategy,
            "final_recommendations": self._generate_final_recommendations()
        }
        
        # Lưu báo cáo vào file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_dir, f"comprehensive_test_report_{timestamp}.json")
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Đã lưu báo cáo vào {report_file}")
            print(f"\nĐã lưu báo cáo đầy đủ vào {report_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu báo cáo: {str(e)}")
        
        # Tạo file markdown để dễ đọc
        md_file = os.path.join(self.output_dir, f"comprehensive_test_report_{timestamp}.md")
        
        try:
            with open(md_file, 'w') as f:
                f.write("# BÁO CÁO KIỂM TRA TOÀN DIỆN HỆ THỐNG GIAO DỊCH\n\n")
                
                f.write(f"## Thông tin kiểm tra\n\n")
                f.write(f"- Thời gian kiểm tra: {report['test_summary']['test_time']}\n")
                f.write(f"- Số cặp tiền kiểm tra: {len(report['test_summary']['symbols_tested'])}\n")
                f.write(f"- Mức độ rủi ro: {report['test_summary']['risk_level'].upper()}\n")
                f.write(f"- Số ngày dữ liệu: {report['test_summary']['days_tested']}\n\n")
                
                f.write("## Khuyến nghị cuối cùng\n\n")
                final_recs = report["final_recommendations"]
                
                f.write("### Top cặp tiền nên giao dịch\n\n")
                f.write("| # | Cặp tiền | Tỷ lệ thắng | Ghi chú |\n")
                f.write("|---|---------|-------------|--------|\n")
                for i, rec in enumerate(final_recs.get("best_symbols", [])[:5], 1):
                    f.write(f"| {i} | {rec['symbol']} | {rec['win_rate']:.1f}% | {rec.get('note', '')} |\n")
                
                f.write("\n### Top thời điểm giao dịch tối ưu\n\n")
                f.write("| # | Phiên | Thời gian | Tỷ lệ thắng | Hướng |\n")
                f.write("|---|-------|-----------|-------------|-------|\n")
                for i, rec in enumerate(final_recs.get("best_times", [])[:5], 1):
                    f.write(f"| {i} | {rec['session']} | {rec['time']} | {rec['win_rate']:.1f}% | {rec['direction'].upper()} |\n")
                
                f.write("\n### Top chiến lược kết hợp\n\n")
                f.write("| # | Cặp tiền | Phiên | Hướng | Điểm kết hợp |\n")
                f.write("|---|---------|-------|-------|-------------|\n")
                for i, rec in enumerate(final_recs.get("best_combinations", [])[:10], 1):
                    f.write(f"| {i} | {rec['symbol']} | {rec['session']} | {rec['direction'].upper()} | {rec['score']:.1f}% |\n")
                
                f.write("\n## Kết luận và đề xuất\n\n")
                for conclusion in final_recs.get("conclusions", []):
                    f.write(f"- {conclusion}\n")
                
                f.write("\n## Các thiết lập được đề xuất\n\n")
                for setting in final_recs.get("suggested_settings", []):
                    f.write(f"- {setting}\n")
            
            logger.info(f"Đã lưu báo cáo markdown vào {md_file}")
            print(f"Đã lưu báo cáo markdown vào {md_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu báo cáo markdown: {str(e)}")
        
        # In tóm tắt cuối cùng
        self._print_final_summary(report["final_recommendations"])
        
        return report
    
    def _generate_final_recommendations(self):
        """
        Tạo các khuyến nghị cuối cùng dựa trên tất cả các kết quả kiểm tra
        
        Returns:
            dict: Các khuyến nghị cuối cùng
        """
        # Lấy dữ liệu từ các bài kiểm tra
        entry_summary = self.test_results.get("entry_summary", {})
        time_analysis = self.test_results.get("time_analysis", {})
        combined_strategy = self.test_results.get("combined_strategy", {})
        
        # Tạo danh sách các cặp tiền tốt nhất
        best_symbols = []
        for symbol, win_rate in combined_strategy.get("best_symbols", {}).items():
            symbol_info = {
                "symbol": symbol,
                "win_rate": win_rate,
                "note": ""
            }
            
            if win_rate >= 80.0:
                symbol_info["note"] = "Hiệu suất rất cao"
            elif win_rate >= 70.0:
                symbol_info["note"] = "Hiệu suất tốt"
            elif win_rate >= 60.0:
                symbol_info["note"] = "Hiệu suất khá"
            
            best_symbols.append(symbol_info)
        
        # Sắp xếp theo tỷ lệ thắng giảm dần
        best_symbols.sort(key=lambda x: x["win_rate"], reverse=True)
        
        # Tạo danh sách các thời điểm tốt nhất
        best_times = []
        for time_info in time_analysis.get("recommendations", []):
            best_times.append({
                "session": time_info["session"],
                "time": time_info["time"],
                "win_rate": time_info["win_rate"],
                "direction": time_info["direction"]
            })
        
        # Tạo danh sách các kết hợp tốt nhất
        best_combinations = []
        for combo in combined_strategy.get("recommendations", []):
            if combo["combined_score"] >= 70.0:
                best_combinations.append({
                    "symbol": combo["symbol"],
                    "session": combo["session"],
                    "time": combo["time"],
                    "direction": combo["direction"],
                    "score": combo["combined_score"],
                    "is_recommended": combo["is_recommended"]
                })
        
        # Tạo các kết luận dựa trên kết quả kiểm tra
        conclusions = []
        
        # Kết luận về thời gian
        if best_times and best_times[0]["win_rate"] >= 90.0:
            conclusions.append(f"Phiên {best_times[0]['session']} có hiệu suất xuất sắc với tỷ lệ thắng {best_times[0]['win_rate']:.1f}%, nên ưu tiên giao dịch trong khung thời gian này.")
        
        if best_times and all(t["direction"] == "short" for t in best_times[:3]):
            conclusions.append("Các phiên có hiệu suất cao nhất đều khuyến nghị lệnh SHORT, nên ưu tiên hướng này khi giao dịch.")
        
        # Kết luận về cặp tiền
        if best_symbols and best_symbols[0]["win_rate"] >= 70.0:
            conclusions.append(f"Cặp tiền {best_symbols[0]['symbol']} có hiệu suất cao nhất với tỷ lệ thắng {best_symbols[0]['win_rate']:.1f}%, nên ưu tiên giao dịch cặp này.")
        
        # Kết luận về chiến lược kết hợp
        if best_combinations:
            top_combo = best_combinations[0]
            conclusions.append(f"Chiến lược kết hợp tốt nhất là giao dịch {top_combo['symbol']} trong phiên {top_combo['session']} theo hướng {top_combo['direction'].upper()}, với điểm kết hợp {top_combo['score']:.1f}%.")
        
        # Tạo các thiết lập được đề xuất
        suggested_settings = [
            f"Mức rủi ro: {self.risk_level.upper()}",
            f"Stop Loss: {self.entry_tester.config['test_settings']['stop_loss_percent']}%",
            f"Take Profit: {self.entry_tester.config['test_settings']['take_profit_percent']}%",
            f"Tỷ lệ R:R: {self.entry_tester.config['test_settings']['risk_reward_ratio']}"
        ]
        
        # Thêm khuyến nghị về số lệnh tối đa mỗi ngày
        best_day_info = time_analysis.get("best_days", [{}])[0]
        if best_day_info:
            suggested_settings.append(f"Số lệnh tối đa mỗi ngày: {best_day_info.get('max_trades', 3)}")
        
        # Kích thước vị thế
        if self.risk_level == "high":
            suggested_settings.append("Kích thước vị thế: 3% mỗi lệnh")
        elif self.risk_level == "balanced":
            suggested_settings.append("Kích thước vị thế: 2% mỗi lệnh")
        else:
            suggested_settings.append("Kích thước vị thế: 1% mỗi lệnh")
        
        return {
            "best_symbols": best_symbols,
            "best_times": best_times,
            "best_combinations": best_combinations,
            "conclusions": conclusions,
            "suggested_settings": suggested_settings
        }
    
    def _print_final_summary(self, recommendations):
        """
        In tóm tắt cuối cùng
        
        Args:
            recommendations (dict): Các khuyến nghị cuối cùng
        """
        print("\n" + "="*50)
        print("TỔNG KẾT KIỂM TRA TOÀN DIỆN HỆ THỐNG GIAO DỊCH")
        print("="*50 + "\n")
        
        print(f"Mức độ rủi ro: {self.risk_level.upper()}")
        print(f"Số cặp tiền kiểm tra: {len(self.symbols)}")
        print(f"Số ngày dữ liệu: {self.days}\n")
        
        print("TOP 3 CẶP TIỀN TỐT NHẤT:")
        for i, symbol in enumerate(recommendations["best_symbols"][:3], 1):
            print(f"{i}. {symbol['symbol']} - Tỷ lệ thắng: {symbol['win_rate']:.1f}% - {symbol['note']}")
        
        print("\nTOP 3 THỜI ĐIỂM GIAO DỊCH TỐI ƯU:")
        for i, time_info in enumerate(recommendations["best_times"][:3], 1):
            print(f"{i}. {time_info['session']} ({time_info['time']}) - {time_info['win_rate']:.1f}% - {time_info['direction'].upper()}")
        
        print("\nTOP 5 CHIẾN LƯỢC KẾT HỢP ĐƯỢC KHUYẾN NGHỊ:")
        for i, combo in enumerate(recommendations["best_combinations"][:5], 1):
            print(f"{i}. {combo['symbol']} - {combo['session']} - {combo['direction'].upper()} ({combo['score']:.1f}%)")
        
        print("\nKẾT LUẬN VÀ ĐỀ XUẤT:")
        for conclusion in recommendations["conclusions"]:
            print(f"- {conclusion}")
        
        print("\nTHIẾT LẬP ĐƯỢC KHUYẾN NGHỊ:")
        for setting in recommendations["suggested_settings"]:
            print(f"- {setting}")
        
        print("\n" + "="*50)
        print("KẾT THÚC BÁO CÁO KIỂM TRA TOÀN DIỆN")
        print("="*50)
    
    def run_all_tests(self):
        """
        Chạy tất cả các bài kiểm tra
        """
        # Tải dữ liệu thị trường
        self.download_market_data()
        
        # Chạy kiểm tra các điểm vào lệnh
        self.run_entry_tests()
        
        # Chạy phân tích cửa sổ thời gian tối ưu
        self.run_time_window_analysis()
        
        # Chạy kiểm tra chiến lược kết hợp
        self.run_combined_strategy_test()
        
        # Tạo báo cáo cuối cùng
        self.generate_final_report()
        
        logger.info("Đã hoàn thành tất cả các bài kiểm tra!")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Kiểm tra toàn diện hệ thống giao dịch')
    parser.add_argument('--symbols', type=str, help='Danh sách các cặp tiền cần kiểm tra, phân cách bởi dấu phẩy')
    parser.add_argument('--days', type=int, default=30, help='Số ngày dữ liệu để kiểm tra')
    parser.add_argument('--risk', type=str, choices=['low', 'balanced', 'high'], default='high', help='Mức độ rủi ro (low, balanced, high)')
    parser.add_argument('--output', type=str, default='comprehensive_test_results', help='Thư mục lưu kết quả')
    args = parser.parse_args()
    
    # Xử lý danh sách cặp tiền
    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    
    # Khởi tạo và chạy bài kiểm tra
    tester = ComprehensiveTest(
        symbols=symbols,
        days=args.days,
        risk_level=args.risk,
        output_dir=args.output
    )
    
    # Chạy tất cả các bài kiểm tra
    tester.run_all_tests()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã dừng kiểm tra!")
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {str(e)}", exc_info=True)
        sys.exit(1)