#!/usr/bin/env python3
"""
Script kiểm tra tích hợp đa khung thời gian

Script này kết hợp MarketAnalysisSystem và MultiTimeframeIntegration để kiểm tra việc
tích hợp phân tích từ nhiều khung thời gian khác nhau, nhằm giải quyết vấn đề
các khuyến nghị mâu thuẫn.
"""

import os
import json
import logging
import argparse
from typing import Dict, List
from market_analysis_system import MarketAnalysisSystem
from multi_timeframe_integration import MultiTimeframeIntegration

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("integration_test")

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Kiểm tra tích hợp đa khung thời gian')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã cặp tiền để phân tích')
    parser.add_argument('--save-report', action='store_true', help='Lưu báo cáo phân tích')
    return parser.parse_args()

def run_integrated_analysis(symbol: str, save_report: bool = False) -> Dict:
    """
    Chạy phân tích tích hợp đa khung thời gian
    
    Args:
        symbol (str): Mã cặp tiền
        save_report (bool): Có lưu báo cáo không
        
    Returns:
        Dict: Kết quả phân tích tích hợp
    """
    try:
        # Khởi tạo các đối tượng
        market_analyzer = MarketAnalysisSystem()
        integrator = MultiTimeframeIntegration()
        
        logger.info(f"Bắt đầu phân tích tích hợp đa khung thời gian cho {symbol}")
        
        # Phân tích trên từng khung thời gian
        timeframes = ["5m", "15m", "1h", "4h", "1d"]
        timeframe_analyses = {}
        
        for tf in timeframes:
            logger.info(f"Đang phân tích {symbol} trên khung {tf}...")
            analysis = market_analyzer.analyze_symbol(symbol, tf)
            timeframe_analyses[tf] = analysis
            logger.info(f"Đã phân tích {symbol} trên khung {tf}, điểm: {analysis['score']}, khuyến nghị: {analysis['recommendation']}")
        
        # Tích hợp phân tích
        logger.info(f"Tích hợp kết quả phân tích từ {len(timeframe_analyses)} khung thời gian...")
        integrated_result = integrator.integrate_timeframes(symbol, timeframe_analyses)
        
        # Thống kê kết quả
        logger.info(f"Đã hoàn thành phân tích tích hợp, điểm tích hợp: {integrated_result['integrated_score']}, khuyến nghị: {integrated_result['recommendation']}")
        
        # Kiểm tra xung đột
        if integrated_result['conflict_info']['has_conflict']:
            logger.warning(f"Phát hiện {len(integrated_result['conflict_info']['conflicts'])} xung đột giữa các khung thời gian")
        
        # Lưu báo cáo nếu cần
        if save_report:
            save_integrated_report(symbol, integrated_result, timeframe_analyses)
        
        return integrated_result
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy phân tích tích hợp: {str(e)}")
        return {
            "symbol": symbol,
            "error": str(e),
            "integrated_score": 50,
            "recommendation": "neutral"
        }

def save_integrated_report(symbol: str, integrated_result: Dict, timeframe_analyses: Dict) -> str:
    """
    Lưu báo cáo phân tích tích hợp
    
    Args:
        symbol (str): Mã cặp tiền
        integrated_result (Dict): Kết quả phân tích tích hợp
        timeframe_analyses (Dict): Phân tích theo từng khung thời gian
        
    Returns:
        str: Đường dẫn đến báo cáo
    """
    try:
        # Tạo thư mục
        report_dir = "reports/integrated_analysis"
        os.makedirs(report_dir, exist_ok=True)
        
        # Tạo báo cáo
        report_path = f"{report_dir}/{symbol}_integrated_analysis.json"
        
        # Chuẩn bị dữ liệu báo cáo
        report_data = {
            "symbol": symbol,
            "timestamp": integrated_result.get("timestamp", ""),
            "integrated_result": integrated_result,
            "individual_timeframe_analyses": timeframe_analyses
        }
        
        # Lưu báo cáo
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=4)
        
        logger.info(f"Đã lưu báo cáo phân tích tích hợp tại {report_path}")
        return report_path
    
    except Exception as e:
        logger.error(f"Lỗi khi lưu báo cáo: {str(e)}")
        return ""

def display_results(symbol: str, integrated_result: Dict) -> None:
    """
    Hiển thị kết quả phân tích tích hợp
    
    Args:
        symbol (str): Mã cặp tiền
        integrated_result (Dict): Kết quả phân tích tích hợp
    """
    print("\n" + "=" * 80)
    print(f"KẾT QUẢ PHÂN TÍCH TÍCH HỢP ĐA KHUNG THỜI GIAN CHO {symbol}".center(80))
    print("=" * 80 + "\n")
    
    # Hiển thị kết quả tích hợp
    recommendation = integrated_result['recommendation'].upper()
    score = integrated_result['integrated_score']
    
    # Màu sắc cho khuyến nghị
    if recommendation in ["BUY", "STRONG_BUY"]:
        colored_rec = f"\033[32m{recommendation}\033[0m"  # Màu xanh lá
    elif recommendation in ["SELL", "STRONG_SELL"]:
        colored_rec = f"\033[31m{recommendation}\033[0m"  # Màu đỏ
    else:
        colored_rec = f"\033[33m{recommendation}\033[0m"  # Màu vàng
    
    print(f"Khuyến nghị tích hợp: {colored_rec}")
    print(f"Điểm tích hợp: {score}/100")
    
    # Hiển thị điểm từng khung thời gian
    print("\nĐiểm theo từng khung thời gian:")
    print("-" * 60)
    print(f"{'Khung':^15}{'Điểm':^10}{'Khuyến nghị':^20}{'Trọng số':^15}")
    print("-" * 60)
    
    for tf, data in integrated_result['timeframe_breakdown'].items():
        rec = data['recommendation'].upper()
        
        # Màu sắc cho khuyến nghị
        if rec in ["BUY", "STRONG_BUY"]:
            colored_tf_rec = f"\033[32m{rec}\033[0m"  # Màu xanh lá
        elif rec in ["SELL", "STRONG_SELL"]:
            colored_tf_rec = f"\033[31m{rec}\033[0m"  # Màu đỏ
        else:
            colored_tf_rec = f"\033[33m{rec}\033[0m"  # Màu vàng
        
        print(f"{tf:^15}{data['score']:^10}{colored_tf_rec:^30}{data['weight']:^15.2f}")
    
    # Kiểm tra xung đột
    if integrated_result['conflict_info']['has_conflict']:
        print("\nXung đột giữa các khung thời gian:")
        print("-" * 80)
        for conflict in integrated_result['conflict_info']['conflicts']:
            print(f"  • {conflict['timeframe1']} ({conflict['rec1'].upper()}, {conflict['score1']}) vs " +
                  f"{conflict['timeframe2']} ({conflict['rec2'].upper()}, {conflict['score2']})")
        
        print(f"\nPhương pháp giải quyết xung đột: {integrated_result['conflict_info']['resolution_method']}")
    
    # Hiển thị điểm vào/ra
    print("\nThông tin giao dịch LONG:")
    print("-" * 80)
    entry_points = integrated_result['entry_exit_points']['long']['entry_points']
    tp_points = integrated_result['entry_exit_points']['long']['exit_points']['take_profit']
    sl_points = integrated_result['entry_exit_points']['long']['exit_points']['stop_loss']
    reasoning = integrated_result['entry_exit_points']['long']['reasoning']
    
    if entry_points:
        print(f"  • Điểm vào: {', '.join([str(p) for p in entry_points])}")
        if tp_points:
            print(f"  • Take profit: {', '.join([str(p) for p in tp_points])}")
        if sl_points:
            print(f"  • Stop loss: {', '.join([str(p) for p in sl_points])}")
        if reasoning:
            print(f"  • Lý do: {', '.join(reasoning)}")
    else:
        print("  Không có điểm vào LONG")
    
    print("\nThông tin giao dịch SHORT:")
    print("-" * 80)
    entry_points = integrated_result['entry_exit_points']['short']['entry_points']
    tp_points = integrated_result['entry_exit_points']['short']['exit_points']['take_profit']
    sl_points = integrated_result['entry_exit_points']['short']['exit_points']['stop_loss']
    reasoning = integrated_result['entry_exit_points']['short']['reasoning']
    
    if entry_points:
        print(f"  • Điểm vào: {', '.join([str(p) for p in entry_points])}")
        if tp_points:
            print(f"  • Take profit: {', '.join([str(p) for p in tp_points])}")
        if sl_points:
            print(f"  • Stop loss: {', '.join([str(p) for p in sl_points])}")
        if reasoning:
            print(f"  • Lý do: {', '.join(reasoning)}")
    else:
        print("  Không có điểm vào SHORT")
    
    print("\n" + "=" * 80)

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    symbol = args.symbol
    save_report = args.save_report
    
    # Chạy phân tích
    integrated_result = run_integrated_analysis(symbol, save_report)
    
    # Hiển thị kết quả
    display_results(symbol, integrated_result)

if __name__ == "__main__":
    main()