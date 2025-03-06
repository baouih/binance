#!/usr/bin/env python3
"""
Script kiểm tra điều kiện vào lệnh trên nhiều cặp tiền với tích hợp đa khung thời gian

Script này thực hiện:
1. Phân tích cặp tiền trên nhiều khung thời gian
2. Tích hợp kết quả phân tích
3. Kiểm tra chi tiết điều kiện vào lệnh và lý do không vào lệnh
4. So sánh quyết định giữa phân tích đơn khung và đa khung
"""

import os
import json
import logging
import argparse
from typing import Dict, List
from tabulate import tabulate
import sys
# Thêm đường dẫn của thư mục gốc vào sys.path
sys.path.append('.')
from market_analysis_system import MarketAnalysisSystem
from multi_timeframe_integration import MultiTimeframeIntegration

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_trading_conditions")

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Kiểm tra điều kiện vào lệnh')
    parser.add_argument('--symbols', type=str, nargs='+', default=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'], help='Danh sách các cặp tiền cần kiểm tra')
    parser.add_argument('--save-report', action='store_true', help='Lưu báo cáo phân tích')
    return parser.parse_args()

def check_trading_decision(symbol: str, market_analyzer: MarketAnalysisSystem, integrator: MultiTimeframeIntegration) -> Dict:
    """
    Kiểm tra quyết định giao dịch cho một cặp tiền
    
    Args:
        symbol (str): Mã cặp tiền
        market_analyzer (MarketAnalysisSystem): Đối tượng phân tích thị trường
        integrator (MultiTimeframeIntegration): Đối tượng tích hợp đa khung
        
    Returns:
        Dict: Kết quả quyết định giao dịch
    """
    try:
        # Phân tích trên từng khung thời gian
        timeframes = ["5m", "15m", "1h", "4h", "1d"]
        timeframe_analyses = {}
        single_timeframe_decisions = {}
        
        # Khung thời gian chính
        primary_tf = market_analyzer.config.get("primary_timeframe", "1h")
        
        logger.info(f"Đang phân tích và kiểm tra điều kiện giao dịch cho {symbol}")
        
        for tf in timeframes:
            # Phân tích
            analysis = market_analyzer.analyze_symbol(symbol, tf)
            timeframe_analyses[tf] = analysis
            
            # Xác định hướng từ phân tích
            direction = None
            if analysis["recommendation"] in ["strong_buy", "buy"]:
                direction = "long"
            elif analysis["recommendation"] in ["strong_sell", "sell"]:
                direction = "short"
            
            # Kiểm tra điều kiện giao dịch
            if direction:
                can_trade, reasons = market_analyzer.check_trading_conditions(symbol, tf, direction)
                
                # Lưu quyết định
                single_timeframe_decisions[tf] = {
                    "direction": direction,
                    "can_trade": can_trade,
                    "reasons": reasons,
                    "score": analysis["score"],
                    "recommendation": analysis["recommendation"]
                }
            else:
                # Khuyến nghị trung tính
                single_timeframe_decisions[tf] = {
                    "direction": "neutral",
                    "can_trade": False,
                    "reasons": [{
                        "category": "technical_indicators",
                        "reason": "Khuyến nghị trung tính",
                        "importance": "medium"
                    }],
                    "score": analysis["score"],
                    "recommendation": analysis["recommendation"]
                }
        
        # Tích hợp phân tích đa khung thời gian
        integrated_result = integrator.integrate_timeframes(symbol, timeframe_analyses)
        
        # Xác định hướng từ phân tích tích hợp
        integrated_direction = None
        if integrated_result["recommendation"] in ["strong_buy", "buy"]:
            integrated_direction = "long"
        elif integrated_result["recommendation"] in ["strong_sell", "sell"]:
            integrated_direction = "short"
        
        # Kiểm tra điều kiện giao dịch từ kết quả tích hợp
        integrated_decision = {}
        
        if integrated_direction:
            # Truyền kết quả tích hợp vào phân tích khung chính để kiểm tra điều kiện
            timeframe_analyses[primary_tf]["score"] = integrated_result["integrated_score"]
            timeframe_analyses[primary_tf]["recommendation"] = integrated_result["recommendation"]
            timeframe_analyses[primary_tf]["entry_exit_points"] = integrated_result["entry_exit_points"]
            
            # Kiểm tra với thông tin tích hợp
            can_trade, reasons = market_analyzer.check_trading_conditions(symbol, primary_tf, integrated_direction)
            
            integrated_decision = {
                "direction": integrated_direction,
                "can_trade": can_trade,
                "reasons": reasons,
                "score": integrated_result["integrated_score"],
                "recommendation": integrated_result["recommendation"]
            }
        else:
            # Khuyến nghị trung tính
            integrated_decision = {
                "direction": "neutral",
                "can_trade": False,
                "reasons": [{
                    "category": "technical_indicators",
                    "reason": "Khuyến nghị tích hợp trung tính",
                    "importance": "medium"
                }],
                "score": integrated_result["integrated_score"],
                "recommendation": integrated_result["recommendation"]
            }
        
        # Tổng hợp kết quả
        return {
            "symbol": symbol,
            "timestamp": timeframe_analyses[primary_tf].get("timestamp", ""),
            "single_timeframe_decisions": single_timeframe_decisions,
            "integrated_decision": integrated_decision,
            "integrated_result": integrated_result
        }
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra quyết định giao dịch cho {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "error": str(e)
        }

def save_test_report(symbol: str, test_result: Dict) -> str:
    """
    Lưu báo cáo kiểm tra
    
    Args:
        symbol (str): Mã cặp tiền
        test_result (Dict): Kết quả kiểm tra
        
    Returns:
        str: Đường dẫn đến báo cáo
    """
    try:
        # Tạo thư mục
        report_dir = "reports/entry_condition_tests"
        os.makedirs(report_dir, exist_ok=True)
        
        # Tạo báo cáo
        report_path = f"{report_dir}/{symbol}_trading_conditions_test.json"
        
        # Lưu báo cáo
        with open(report_path, 'w') as f:
            json.dump(test_result, f, indent=4)
        
        logger.info(f"Đã lưu báo cáo kiểm tra điều kiện vào lệnh tại {report_path}")
        return report_path
    
    except Exception as e:
        logger.error(f"Lỗi khi lưu báo cáo: {str(e)}")
        return ""

def display_test_result(test_result: Dict) -> None:
    """
    Hiển thị kết quả kiểm tra điều kiện giao dịch
    
    Args:
        test_result (Dict): Kết quả kiểm tra
    """
    if "error" in test_result:
        print(f"\nLỖI: {test_result['error']}\n")
        return
    
    symbol = test_result["symbol"]
    integrated_decision = test_result["integrated_decision"]
    single_tf_decisions = test_result["single_timeframe_decisions"]
    
    print("\n" + "=" * 80)
    print(f"KẾT QUẢ KIỂM TRA ĐIỀU KIỆN VÀO LỆNH CHO {symbol}".center(80))
    print("=" * 80 + "\n")
    
    # Hiển thị quyết định từng khung
    print("I. QUYẾT ĐỊNH THEO TỪNG KHUNG THỜI GIAN")
    print("-" * 80)
    
    table_data = []
    for tf, decision in single_tf_decisions.items():
        direction = decision["direction"].upper()
        can_trade = "CÓ" if decision["can_trade"] else "KHÔNG"
        score = decision["score"]
        
        # Màu sắc (chỉ hoạt động trong terminal hỗ trợ)
        if direction == "LONG":
            direction = f"\033[32m{direction}\033[0m"  # Xanh lá
        elif direction == "SHORT":
            direction = f"\033[31m{direction}\033[0m"  # Đỏ
        else:
            direction = f"\033[33m{direction}\033[0m"  # Vàng
            
        if can_trade == "CÓ":
            can_trade = f"\033[32m{can_trade}\033[0m"  # Xanh lá
        else:
            can_trade = f"\033[31m{can_trade}\033[0m"  # Đỏ
            
        table_data.append([tf, direction, score, can_trade])
    
    print(tabulate(table_data, headers=["Khung", "Hướng", "Điểm", "Vào lệnh"], tablefmt="grid"))
    
    # Hiển thị lý do không vào lệnh
    for tf, decision in single_tf_decisions.items():
        if not decision["can_trade"] and decision["reasons"]:
            print(f"\nLý do không vào lệnh trên khung {tf}:")
            for i, reason in enumerate(decision["reasons"], 1):
                importance = reason["importance"]
                importance_color = "\033[33m"  # Vàng cho medium
                if importance == "high":
                    importance_color = "\033[31m"  # Đỏ cho high
                elif importance == "low":
                    importance_color = "\033[32m"  # Xanh lá cho low
                
                print(f"  {i}. {reason['reason']} ({importance_color}{importance}\033[0m])")
    
    # Hiển thị quyết định tích hợp
    print("\nII. QUYẾT ĐỊNH TÍCH HỢP ĐA KHUNG")
    print("-" * 80)
    
    direction = integrated_decision["direction"].upper()
    can_trade = "CÓ" if integrated_decision["can_trade"] else "KHÔNG"
    score = integrated_decision["score"]
    
    # Màu sắc
    if direction == "LONG":
        direction = f"\033[32m{direction}\033[0m"  # Xanh lá
    elif direction == "SHORT":
        direction = f"\033[31m{direction}\033[0m"  # Đỏ
    else:
        direction = f"\033[33m{direction}\033[0m"  # Vàng
        
    if can_trade == "CÓ":
        can_trade = f"\033[32m{can_trade}\033[0m"  # Xanh lá
    else:
        can_trade = f"\033[31m{can_trade}\033[0m"  # Đỏ
    
    print(f"Hướng: {direction}")
    print(f"Điểm tích hợp: {score}/100")
    print(f"Vào lệnh: {can_trade}")
    
    # Hiển thị lý do không vào lệnh tích hợp
    if not integrated_decision["can_trade"] and integrated_decision["reasons"]:
        print("\nLý do không vào lệnh (tích hợp đa khung):")
        for i, reason in enumerate(integrated_decision["reasons"], 1):
            importance = reason["importance"]
            importance_color = "\033[33m"  # Vàng cho medium
            if importance == "high":
                importance_color = "\033[31m"  # Đỏ cho high
            elif importance == "low":
                importance_color = "\033[32m"  # Xanh lá cho low
            
            print(f"  {i}. {reason['reason']} ({importance_color}{importance}\033[0m])")
    
    # Hiển thị xung đột giữa các khung thời gian
    if test_result["integrated_result"]["conflict_info"]["has_conflict"]:
        print("\nIII. XUNG ĐỘT GIỮA CÁC KHUNG THỜI GIAN")
        print("-" * 80)
        
        for conflict in test_result["integrated_result"]["conflict_info"]["conflicts"]:
            print(f"  • {conflict['timeframe1']} ({conflict['rec1'].upper()}, {conflict['score1']}) vs " +
                  f"{conflict['timeframe2']} ({conflict['rec2'].upper()}, {conflict['score2']})")
        
        print(f"\nPhương pháp giải quyết xung đột: {test_result['integrated_result']['conflict_info']['resolution_method']}")
    
    # Hiển thị thông tin điểm vào/ra nếu có thể giao dịch
    if integrated_decision["can_trade"]:
        print("\nIV. THÔNG TIN ĐIỂM VÀO/RA")
        print("-" * 80)
        
        direction = integrated_decision["direction"]
        entry_points = test_result["integrated_result"]["entry_exit_points"][direction]["entry_points"]
        tp_points = test_result["integrated_result"]["entry_exit_points"][direction]["exit_points"]["take_profit"]
        sl_points = test_result["integrated_result"]["entry_exit_points"][direction]["exit_points"]["stop_loss"]
        reasoning = test_result["integrated_result"]["entry_exit_points"][direction]["reasoning"]
        
        print(f"Điểm vào: {', '.join([str(p) for p in entry_points])}")
        print(f"Take profit: {', '.join([str(p) for p in tp_points])}")
        print(f"Stop loss: {', '.join([str(p) for p in sl_points])}")
        print("\nLý do:")
        for i, reason in enumerate(reasoning, 1):
            print(f"  {i}. {reason}")
    
    print("\n" + "=" * 80 + "\n")

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    symbols = args.symbols
    save_report = args.save_report
    
    # Khởi tạo các đối tượng
    market_analyzer = MarketAnalysisSystem()
    integrator = MultiTimeframeIntegration()
    
    for symbol in symbols:
        # Kiểm tra điều kiện giao dịch
        test_result = check_trading_decision(symbol, market_analyzer, integrator)
        
        # Hiển thị kết quả
        display_test_result(test_result)
        
        # Lưu báo cáo nếu cần
        if save_report:
            save_test_report(symbol, test_result)

if __name__ == "__main__":
    main()
