#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy thử nghiệm 3 tháng với 5 mức rủi ro khác nhau cho tất cả cặp tiền

Script này điều phối việc chạy backtest cho tất cả các cặp tiền trên nhiều
khung thời gian và nhiều mức rủi ro khác nhau, đồng thời tạo báo cáo
tổng hợp và các biểu đồ so sánh chi tiết.
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_risk_3month_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('multi_risk_3month_test')

# Tạo các thư mục cần thiết
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)
os.makedirs("backtest_summary", exist_ok=True)
os.makedirs("risk_analysis", exist_ok=True)

# Định nghĩa các mức rủi ro
RISK_LEVELS = [0.5, 1.0, 1.5, 2.0, 3.0]

# Định nghĩa danh sách khung thời gian
TIMEFRAMES = ['1h', '4h']

def load_account_config() -> Dict:
    """
    Tải cấu hình tài khoản
    
    Returns:
        Dict: Cấu hình tài khoản
    """
    try:
        with open('account_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải account_config.json: {str(e)}")
        return {}

def run_backtest(symbol: str, interval: str, risk: float, start_date: str = None, end_date: str = None) -> Tuple[str, str, float, Dict]:
    """
    Chạy backtest cho một cặp tiền với khung thời gian và mức rủi ro cụ thể
    
    Args:
        symbol (str): Mã cặp tiền
        interval (str): Khung thời gian
        risk (float): Mức rủi ro
        start_date (str, optional): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str, optional): Ngày kết thúc (YYYY-MM-DD)
        
    Returns:
        Tuple[str, str, float, Dict]: (symbol, interval, risk, kết quả)
    """
    try:
        logger.info(f"Chạy backtest cho {symbol} {interval} với mức rủi ro {risk}%...")
        
        cmd = [
            "python", "enhanced_backtest.py",
            "--symbol", symbol,
            "--interval", interval,
            "--risk", str(risk),
            "--adaptive_risk"
        ]
        
        if start_date:
            cmd.extend(["--start_date", start_date])
        if end_date:
            cmd.extend(["--end_date", end_date])
            
        # Chạy lệnh
        subprocess.run(cmd, check=True)
        
        # Tạo tên file kết quả
        risk_str = str(risk).replace('.', '_')
        result_file = f"backtest_results/{symbol}_{interval}_risk{risk_str}_results.json"
        
        # Đọc kết quả
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                return symbol, interval, risk, json.load(f)
        
        # Thử file mặc định
        default_file = f"backtest_results/{symbol}_{interval}_adaptive_results.json"
        if os.path.exists(default_file):
            with open(default_file, 'r') as f:
                result = json.load(f)
                # Sao chép với tên mới
                with open(result_file, 'w') as f2:
                    json.dump(result, f2, indent=4)
                return symbol, interval, risk, result
                
        logger.warning(f"Không tìm thấy file kết quả cho {symbol} {interval} rủi ro {risk}%")
        return symbol, interval, risk, {}
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest cho {symbol} {interval} rủi ro {risk}%: {str(e)}")
        return symbol, interval, risk, {}

def run_parallel_backtests(symbols: List[str], interval: str, risks: List[float], 
                         start_date: str = None, end_date: str = None, max_workers: int = 4) -> Dict:
    """
    Chạy backtest song song cho nhiều cặp tiền và mức rủi ro
    
    Args:
        symbols (List[str]): Danh sách cặp tiền
        interval (str): Khung thời gian
        risks (List[float]): Danh sách mức rủi ro
        start_date (str, optional): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str, optional): Ngày kết thúc (YYYY-MM-DD)
        max_workers (int): Số lượng process tối đa
        
    Returns:
        Dict: Kết quả backtest
    """
    results = {}
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        
        # Tạo danh sách các tác vụ
        for symbol in symbols:
            for risk in risks:
                futures.append(
                    executor.submit(run_backtest, symbol, interval, risk, start_date, end_date)
                )
        
        # Theo dõi tiến độ
        total = len(futures)
        completed = 0
        
        for future in as_completed(futures):
            symbol, interval, risk, result = future.result()
            completed += 1
            
            logger.info(f"Tiến độ: {completed}/{total} ({100*completed/total:.1f}%)")
            
            if symbol not in results:
                results[symbol] = {}
            
            if interval not in results[symbol]:
                results[symbol][interval] = {}
                
            results[symbol][interval][risk] = result
            
            if result:
                profit = result.get("profit_percentage", 0)
                win_rate = result.get("win_rate", 0)
                logger.info(f"{symbol} {interval} (Rủi ro {risk}%): Lợi nhuận {profit:.2f}%, Win rate {win_rate:.2f}%")
    
    return results

def create_summary_report(results: Dict, output_file: str = "backtest_summary/multi_risk_summary.json") -> None:
    """
    Tạo báo cáo tổng hợp
    
    Args:
        results (Dict): Kết quả backtest
        output_file (str): Đường dẫn file output
    """
    summary = {
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_symbols": len(results),
        "total_timeframes": len(TIMEFRAMES),
        "total_risk_levels": len(RISK_LEVELS),
        "symbols": {},
        "risk_analysis": {
            "optimal_risk_by_symbol": {},
            "optimal_timeframe_by_symbol": {},
            "risk_distribution": {str(risk): 0 for risk in RISK_LEVELS},
            "risk_performance_correlation": {},
            "best_performers": []
        }
    }
    
    # Xử lý từng cặp tiền
    for symbol, tf_results in results.items():
        # Tìm khung thời gian và mức rủi ro tốt nhất
        best_profit = -float('inf')
        best_risk = None
        best_tf = None
        symbol_summary = {}
        
        for tf, risk_results in tf_results.items():
            tf_best_profit = -float('inf')
            tf_best_risk = None
            
            for risk, result in risk_results.items():
                if not result:
                    continue
                
                profit = result.get("profit_percentage", 0)
                win_rate = result.get("win_rate", 0)
                profit_factor = result.get("profit_factor", 0)
                
                # Lưu tóm tắt
                if tf not in symbol_summary:
                    symbol_summary[tf] = {}
                
                symbol_summary[tf][str(risk)] = {
                    "profit_pct": profit,
                    "win_rate": win_rate,
                    "profit_factor": profit_factor,
                    "total_trades": result.get("total_trades", 0),
                    "max_drawdown": result.get("max_drawdown", 0)
                }
                
                # Cập nhật mức rủi ro tốt nhất cho khung thời gian này
                if profit > tf_best_profit:
                    tf_best_profit = profit
                    tf_best_risk = risk
                
                # Cập nhật mức tốt nhất tổng thể
                if profit > best_profit:
                    best_profit = profit
                    best_risk = risk
                    best_tf = tf
        
            # Cập nhật phân phối mức rủi ro
            if tf_best_risk is not None:
                risk_str = str(tf_best_risk)
                if risk_str in summary["risk_analysis"]["risk_distribution"]:
                    summary["risk_analysis"]["risk_distribution"][risk_str] += 1
        
        # Lưu kết quả cho cặp tiền này
        summary["symbols"][symbol] = symbol_summary
        
        if best_risk is not None:
            summary["risk_analysis"]["optimal_risk_by_symbol"][symbol] = best_risk
        
        if best_tf is not None:
            summary["risk_analysis"]["optimal_timeframe_by_symbol"][symbol] = best_tf
            
        # Thêm vào danh sách hiệu suất tốt nhất
        if best_risk is not None and best_tf is not None:
            best_result = tf_results[best_tf][best_risk]
            if best_result:
                summary["risk_analysis"]["best_performers"].append({
                    "symbol": symbol,
                    "timeframe": best_tf,
                    "risk": best_risk,
                    "profit_pct": best_result.get("profit_percentage", 0),
                    "win_rate": best_result.get("win_rate", 0),
                    "profit_factor": best_result.get("profit_factor", 0)
                })
    
    # Sắp xếp danh sách hiệu suất tốt nhất
    summary["risk_analysis"]["best_performers"].sort(
        key=lambda x: x["profit_pct"], reverse=True
    )
    
    # Lưu báo cáo
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=4)
        
    logger.info(f"Đã lưu báo cáo tổng hợp: {output_file}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Chạy thử nghiệm 3 tháng với nhiều mức rủi ro')
    parser.add_argument('--symbols', nargs='+', help='Danh sách các cặp tiền (mặc định: tất cả)')
    parser.add_argument('--timeframes', nargs='+', help='Danh sách khung thời gian (mặc định: 1h, 4h)')
    parser.add_argument('--start_date', type=str, default='2023-12-01', help='Ngày bắt đầu (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default='2024-03-01', help='Ngày kết thúc (YYYY-MM-DD)')
    parser.add_argument('--max_workers', type=int, default=2, help='Số lượng process tối đa')
    args = parser.parse_args()
    
    # Tải cấu hình
    config = load_account_config()
    all_symbols = config.get('symbols', [])
    
    # Xác định danh sách cặp tiền
    symbols = args.symbols if args.symbols else all_symbols
    
    # Xác định danh sách khung thời gian
    timeframes = args.timeframes if args.timeframes else TIMEFRAMES
    
    logger.info(f"=== BẮT ĐẦU THỬ NGHIỆM ĐA MỨC RỦI RO 3 THÁNG ===")
    logger.info(f"Tổng số cặp tiền: {len(symbols)}")
    logger.info(f"Khung thời gian: {timeframes}")
    logger.info(f"Các mức rủi ro: {RISK_LEVELS}")
    logger.info(f"Thời gian: {args.start_date} đến {args.end_date}")
    
    # Kết quả tổng hợp
    all_results = {}
    
    # Chạy từng khung thời gian
    for interval in timeframes:
        logger.info(f"Chạy thử nghiệm cho khung thời gian {interval}...")
        
        # Chạy backtest song song
        results = run_parallel_backtests(
            symbols=symbols,
            interval=interval,
            risks=RISK_LEVELS,
            start_date=args.start_date,
            end_date=args.end_date,
            max_workers=args.max_workers
        )
        
        # Cập nhật kết quả tổng hợp
        for symbol, risk_results in results.items():
            if symbol not in all_results:
                all_results[symbol] = {}
            
            all_results[symbol][interval] = risk_results
    
    # Tạo báo cáo tổng hợp
    create_summary_report(all_results)
    
    # Chạy script phân tích rủi ro
    logger.info("Chạy phân tích rủi ro tổng hợp...")
    subprocess.run(["python", "risk_analysis_report.py"], check=True)
    
    logger.info(f"=== KẾT THÚC THỬ NGHIỆM ===")

if __name__ == "__main__":
    main()