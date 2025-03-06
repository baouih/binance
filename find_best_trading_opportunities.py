#!/usr/bin/env python3
"""
Script quét toàn bộ thị trường để tìm ra TOP cơ hội giao dịch tốt nhất

Script này phân tích tất cả các cặp tiền được cấu hình, xếp hạng và hiển thị:
1. TOP cơ hội long tốt nhất
2. TOP cơ hội short tốt nhất
3. Tóm tắt thị trường toàn cầu
4. Phân tích tương quan giữa các cặp tiền
5. Khuyến nghị cụ thể về khi nào nên đánh coin và khi nào không

Cách sử dụng:
    python find_best_trading_opportunities.py --top 5 --min-score 60 --timeframe 1h
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
logger = logging.getLogger("best_opportunities_finder")

class BestOpportunitiesFinder:
    """Tìm ra cơ hội giao dịch tốt nhất từ toàn bộ thị trường"""
    
    def __init__(self):
        """Khởi tạo finder"""
        self.analyzer = MarketAnalysisSystem()
        # Đảm bảo thư mục tồn tại
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Tạo các thư mục cần thiết"""
        directories = [
            "reports/market_scan",
            "charts/market_scan"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Đã tạo thư mục: {directory}")
    
    def scan_market(self, timeframe: str = None, min_score: int = 50, top_n: int = 5) -> Dict:
        """
        Quét toàn bộ thị trường để tìm ra cơ hội giao dịch tốt nhất
        
        Args:
            timeframe (str, optional): Khung thời gian, mặc định là primary_timeframe
            min_score (int): Điểm tối thiểu để xem xét (0-100)
            top_n (int): Số lượng cơ hội hiển thị
            
        Returns:
            Dict: Kết quả quét thị trường
        """
        if timeframe is None:
            timeframe = self.analyzer.config["primary_timeframe"]
        
        logger.info(f"Bắt đầu quét thị trường trên khung {timeframe} tìm TOP {top_n} cơ hội với điểm >= {min_score}")
        
        # Phân tích thị trường toàn cầu
        global_market = self.analyzer.analyze_global_market()
        
        # Lấy danh sách các cặp tiền cần phân tích
        symbols = self.analyzer.config["symbols_to_analyze"]
        
        # Phân tích từng cặp tiền
        symbols_analysis = {}
        long_opportunities = []
        short_opportunities = []
        no_opportunities = []
        
        for symbol in symbols:
            try:
                # Phân tích cặp tiền
                analysis = self.analyzer.analyze_symbol(symbol, timeframe)
                symbols_analysis[symbol] = analysis
                
                # Tính điểm long/short
                entry_exit = analysis.get("entry_exit_points", {})
                long_score = entry_exit.get("score", {}).get("long", 0)
                short_score = entry_exit.get("score", {}).get("short", 0)
                
                # Kiểm tra với long
                if long_score >= min_score:
                    # Kiểm tra điều kiện giao dịch
                    can_trade, reasons = self.analyzer.check_trading_conditions(symbol, timeframe, "long")
                    
                    if can_trade:
                        # Lấy thông tin entry/exit
                        entry_points = entry_exit.get("long", {}).get("entry_points", [])
                        take_profit = entry_exit.get("long", {}).get("exit_points", {}).get("take_profit", [])
                        stop_loss = entry_exit.get("long", {}).get("exit_points", {}).get("stop_loss", [])
                        reasoning = entry_exit.get("long", {}).get("reasoning", [])
                        
                        if entry_points and take_profit and stop_loss:
                            # Tính R:R
                            risk = analysis["price"]["current"] - stop_loss[0] if stop_loss else 0
                            reward = take_profit[0] - analysis["price"]["current"] if take_profit else 0
                            risk_reward_ratio = reward / risk if risk > 0 else 0
                            
                            # Thêm vào danh sách cơ hội
                            long_opportunities.append({
                                "symbol": symbol,
                                "direction": "long",
                                "score": long_score,
                                "current_price": analysis["price"]["current"],
                                "entry_price": entry_points[0] if entry_points else analysis["price"]["current"],
                                "take_profit": take_profit[0] if take_profit else None,
                                "stop_loss": stop_loss[0] if stop_loss else None,
                                "risk_reward_ratio": risk_reward_ratio,
                                "reasoning": reasoning,
                                "market_regime": analysis.get("market_regime", "unknown")
                            })
                
                # Kiểm tra với short
                if short_score >= min_score:
                    # Kiểm tra điều kiện giao dịch
                    can_trade, reasons = self.analyzer.check_trading_conditions(symbol, timeframe, "short")
                    
                    if can_trade:
                        # Lấy thông tin entry/exit
                        entry_points = entry_exit.get("short", {}).get("entry_points", [])
                        take_profit = entry_exit.get("short", {}).get("exit_points", {}).get("take_profit", [])
                        stop_loss = entry_exit.get("short", {}).get("exit_points", {}).get("stop_loss", [])
                        reasoning = entry_exit.get("short", {}).get("reasoning", [])
                        
                        if entry_points and take_profit and stop_loss:
                            # Tính R:R
                            risk = stop_loss[0] - analysis["price"]["current"] if stop_loss else 0
                            reward = analysis["price"]["current"] - take_profit[0] if take_profit else 0
                            risk_reward_ratio = reward / risk if risk > 0 else 0
                            
                            # Thêm vào danh sách cơ hội
                            short_opportunities.append({
                                "symbol": symbol,
                                "direction": "short",
                                "score": short_score,
                                "current_price": analysis["price"]["current"],
                                "entry_price": entry_points[0] if entry_points else analysis["price"]["current"],
                                "take_profit": take_profit[0] if take_profit else None,
                                "stop_loss": stop_loss[0] if stop_loss else None,
                                "risk_reward_ratio": risk_reward_ratio,
                                "reasoning": reasoning,
                                "market_regime": analysis.get("market_regime", "unknown")
                            })
                
                # Nếu không có cơ hội thỏa mãn, ghi lại lý do
                if long_score < min_score and short_score < min_score:
                    no_opportunities.append({
                        "symbol": symbol,
                        "long_score": long_score,
                        "short_score": short_score,
                        "current_price": analysis["price"]["current"],
                        "market_regime": analysis.get("market_regime", "unknown"),
                        "reason": "Không đủ điểm tối thiểu"
                    })
            except Exception as e:
                logger.error(f"Lỗi khi phân tích {symbol}: {str(e)}")
                no_opportunities.append({
                    "symbol": symbol,
                    "reason": f"Lỗi: {str(e)}"
                })
        
        # Sắp xếp cơ hội
        long_opportunities.sort(key=lambda x: (x["score"], x["risk_reward_ratio"]), reverse=True)
        short_opportunities.sort(key=lambda x: (x["score"], x["risk_reward_ratio"]), reverse=True)
        
        # Lấy TOP N cơ hội
        top_long = long_opportunities[:top_n]
        top_short = short_opportunities[:top_n]
        
        # Tính tương quan
        correlation_matrix = self.analyzer._calculate_symbols_correlation()
        
        # Tổng hợp kết quả
        result = {
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "timeframe": timeframe,
            "global_market": global_market,
            "top_long_opportunities": top_long,
            "top_short_opportunities": top_short,
            "no_opportunities": no_opportunities,
            "correlation_matrix": correlation_matrix,
            "scan_summary": {
                "total_symbols": len(symbols),
                "long_opportunities": len(long_opportunities),
                "short_opportunities": len(short_opportunities),
                "no_opportunities": len(no_opportunities),
                "avg_long_score": sum(opp.get("score", 0) for opp in long_opportunities) / len(long_opportunities) if long_opportunities else 0,
                "avg_short_score": sum(opp.get("score", 0) for opp in short_opportunities) / len(short_opportunities) if short_opportunities else 0,
                "best_long": top_long[0]["symbol"] if top_long else None,
                "best_short": top_short[0]["symbol"] if top_short else None
            }
        }
        
        # Lưu báo cáo
        self._save_report(result)
        
        # Tạo biểu đồ thị trường
        self._create_market_heatmap(result)
        
        logger.info("Hoàn thành quét thị trường")
        return result
    
    def _save_report(self, scan_result: Dict) -> str:
        """
        Lưu báo cáo quét thị trường
        
        Args:
            scan_result (Dict): Kết quả quét thị trường
            
        Returns:
            str: Đường dẫn đến báo cáo
        """
        timeframe = scan_result["timeframe"]
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Tạo tên file
        report_filename = f"reports/market_scan/market_scan_{timeframe}_{timestamp}.json"
        
        # Lưu file JSON
        try:
            with open(report_filename, 'w') as f:
                json.dump(scan_result, f, indent=4)
            
            logger.info(f"Đã lưu báo cáo quét thị trường tại {report_filename}")
            return report_filename
        except Exception as e:
            logger.error(f"Lỗi khi lưu báo cáo quét thị trường: {str(e)}")
            return ""
    
    def _create_market_heatmap(self, scan_result: Dict) -> str:
        """
        Tạo biểu đồ heatmap thị trường
        
        Args:
            scan_result (Dict): Kết quả quét thị trường
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            chart_path = f"charts/market_scan/market_heatmap_{timestamp}.png"
            
            # Lấy dữ liệu cho heatmap
            symbols = []
            scores = []
            
            # Lấy từ cơ hội long
            for opp in scan_result["top_long_opportunities"]:
                symbols.append(f"{opp['symbol']} (L)")
                scores.append(opp["score"])
            
            # Lấy từ cơ hội short
            for opp in scan_result["top_short_opportunities"]:
                symbols.append(f"{opp['symbol']} (S)")
                scores.append(opp["score"])
            
            if not symbols:
                logger.warning("Không có dữ liệu để tạo heatmap")
                return ""
            
            # Tạo biểu đồ
            plt.figure(figsize=(12, 8))
            
            # Tạo heatmap dạng ngang
            y_pos = np.arange(len(symbols))
            colors = ['green' if score >= 80 else 'lightgreen' if score >= 60 
                       else 'orange' if score >= 40 else 'red' for score in scores]
            
            plt.barh(y_pos, scores, color=colors)
            plt.yticks(y_pos, symbols)
            plt.xlabel('Điểm đánh giá (0-100)')
            plt.title('TOP Cơ Hội Giao Dịch')
            
            # Thêm giá trị lên mỗi thanh
            for i, v in enumerate(scores):
                plt.text(v + 1, i, str(v), va='center')
            
            # Lưu biểu đồ
            plt.tight_layout()
            plt.savefig(chart_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ heatmap tại {chart_path}")
            return chart_path
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ heatmap: {str(e)}")
            return ""
    
    def print_scan_summary(self, scan_result: Dict) -> None:
        """
        In tóm tắt kết quả quét thị trường
        
        Args:
            scan_result (Dict): Kết quả quét thị trường
        """
        timestamp = scan_result["timestamp"]
        timeframe = scan_result["timeframe"]
        global_market = scan_result["global_market"]
        top_long = scan_result["top_long_opportunities"]
        top_short = scan_result["top_short_opportunities"]
        summary = scan_result["scan_summary"]
        
        print("\n" + "="*80)
        print(f"QUÉT THỊ TRƯỜNG - {timeframe} - {timestamp}")
        print("="*80)
        
        # Thông tin thị trường toàn cầu
        print(f"\nXu hướng thị trường: {global_market['market_trend'].upper()}")
        print(f"Chế độ thị trường: {global_market['market_regime'].upper()}")
        print(f"Giá Bitcoin: ${global_market['btc_price']:.2f}")
        
        # Tóm tắt kết quả quét
        print("\n" + "-"*80)
        print("TÓM TẮT KẾT QUẢ QUÉT")
        print("-"*80)
        print(f"Tổng số cặp tiền: {summary['total_symbols']}")
        print(f"Cơ hội LONG: {summary['long_opportunities']}")
        print(f"Cơ hội SHORT: {summary['short_opportunities']}")
        print(f"Không có cơ hội: {summary['no_opportunities']}")
        print(f"Điểm LONG trung bình: {summary['avg_long_score']:.2f}")
        print(f"Điểm SHORT trung bình: {summary['avg_short_score']:.2f}")
        print(f"Cặp tiền LONG tốt nhất: {summary['best_long'] or 'Không có'}")
        print(f"Cặp tiền SHORT tốt nhất: {summary['best_short'] or 'Không có'}")
        
        # TOP cơ hội LONG
        if top_long:
            print("\n" + "-"*80)
            print(f"TOP {len(top_long)} CƠ HỘI LONG")
            print("-"*80)
            
            long_data = []
            for opp in top_long:
                risk_reward = f"1:{opp['risk_reward_ratio']:.2f}" if opp['risk_reward_ratio'] > 0 else "N/A"
                reasoning = opp['reasoning'][0] if opp['reasoning'] else "N/A"
                
                long_data.append([
                    opp['symbol'],
                    opp['score'],
                    opp['current_price'],
                    opp['entry_price'],
                    opp['stop_loss'],
                    opp['take_profit'],
                    risk_reward,
                    reasoning[:50] + "..." if len(reasoning) > 50 else reasoning
                ])
            
            print(tabulate(long_data, headers=[
                "Symbol", "Điểm", "Giá hiện tại", "Giá vào", "Stop Loss", 
                "Take Profit", "R:R", "Lý do"
            ], tablefmt="grid"))
        else:
            print("\nKhông có cơ hội LONG thỏa mãn tiêu chí")
        
        # TOP cơ hội SHORT
        if top_short:
            print("\n" + "-"*80)
            print(f"TOP {len(top_short)} CƠ HỘI SHORT")
            print("-"*80)
            
            short_data = []
            for opp in top_short:
                risk_reward = f"1:{opp['risk_reward_ratio']:.2f}" if opp['risk_reward_ratio'] > 0 else "N/A"
                reasoning = opp['reasoning'][0] if opp['reasoning'] else "N/A"
                
                short_data.append([
                    opp['symbol'],
                    opp['score'],
                    opp['current_price'],
                    opp['entry_price'],
                    opp['stop_loss'],
                    opp['take_profit'],
                    risk_reward,
                    reasoning[:50] + "..." if len(reasoning) > 50 else reasoning
                ])
            
            print(tabulate(short_data, headers=[
                "Symbol", "Điểm", "Giá hiện tại", "Giá vào", "Stop Loss", 
                "Take Profit", "R:R", "Lý do"
            ], tablefmt="grid"))
        else:
            print("\nKhông có cơ hội SHORT thỏa mãn tiêu chí")
        
        # Khuyến nghị chung
        print("\n" + "-"*80)
        print("KHUYẾN NGHỊ CHUNG")
        print("-"*80)
        
        if global_market['market_regime'] == "high_volatility":
            print("⚠️ Thị trường đang biến động cao. Khuyến nghị thận trọng, giảm kích thước vị thế và đặt stop loss chặt chẽ.")
        elif global_market['market_regime'] == "trending_up" and top_long:
            print("📈 Thị trường đang trong xu hướng tăng. Khuyến nghị ưu tiên các cơ hội LONG.")
        elif global_market['market_regime'] == "trending_down" and top_short:
            print("📉 Thị trường đang trong xu hướng giảm. Khuyến nghị ưu tiên các cơ hội SHORT.")
        elif global_market['market_regime'] == "ranging":
            print("↔️ Thị trường đang đi ngang. Khuyến nghị giao dịch theo biên độ tại các vùng hỗ trợ/kháng cự rõ ràng.")
        else:
            print("🔍 Không có xu hướng rõ ràng. Khuyến nghị thận trọng và chờ đợi tín hiệu rõ ràng hơn.")
        
        # Gợi ý cụ thể
        if summary['best_long'] and summary['avg_long_score'] > 60:
            print(f"\n✅ Cơ hội LONG tốt nhất hiện tại: {summary['best_long']}")
            best_long = next((o for o in top_long if o['symbol'] == summary['best_long']), None)
            if best_long:
                print(f"   Giá vào: {best_long['entry_price']}")
                print(f"   Stop loss: {best_long['stop_loss']}")
                print(f"   Take profit: {best_long['take_profit']}")
        
        if summary['best_short'] and summary['avg_short_score'] > 60:
            print(f"\n✅ Cơ hội SHORT tốt nhất hiện tại: {summary['best_short']}")
            best_short = next((o for o in top_short if o['symbol'] == summary['best_short']), None)
            if best_short:
                print(f"   Giá vào: {best_short['entry_price']}")
                print(f"   Stop loss: {best_short['stop_loss']}")
                print(f"   Take profit: {best_short['take_profit']}")
        
        # Nếu không có cơ hội tốt
        if (not summary['best_long'] or summary['avg_long_score'] <= 60) and \
           (not summary['best_short'] or summary['avg_short_score'] <= 60):
            print("\n❌ Hiện tại không có cơ hội giao dịch nào đáng kể. Nên đợi điều kiện thị trường tốt hơn.")
        
        print("\n" + "="*80)
        print(f"Báo cáo chi tiết được lưu trong thư mục reports/market_scan/")
        print("="*80 + "\n")

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Tìm cơ hội giao dịch tốt nhất từ quét thị trường")
    parser.add_argument("--timeframe", type=str, default=None, help="Khung thời gian (ví dụ: 1h, 4h, 1d)")
    parser.add_argument("--min-score", type=int, default=60, help="Điểm tối thiểu để xem xét (0-100)")
    parser.add_argument("--top", type=int, default=5, help="Số lượng cơ hội hiển thị")
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    print(f"\nĐang quét thị trường trên khung {args.timeframe or 'mặc định'} tìm TOP {args.top} cơ hội với điểm >= {args.min_score}...")
    
    finder = BestOpportunitiesFinder()
    result = finder.scan_market(args.timeframe, args.min_score, args.top)
    
    # In kết quả
    finder.print_scan_summary(result)

if __name__ == "__main__":
    main()