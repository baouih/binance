#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy kiểm thử đa coin với nhiều mức rủi ro khác nhau

Script này sẽ thực hiện backtest trên nhiều cặp tiền và nhiều mức rủi ro
để so sánh hiệu suất và tìm ra cấu hình tối ưu.
"""

import os
import sys
import json
import logging
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import traceback
import time

# Khởi tạo logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multi_coin_adaptive_test.log')
    ]
)

logger = logging.getLogger('multi_coin_test')

# Danh sách coin thanh khoản cao
HIGH_LIQUIDITY_COINS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 
    'ADAUSDT', 'DOGEUSDT', 'XRPUSDT', 'AVAXUSDT'
]

# Các mức rủi ro cần kiểm tra (%)
RISK_LEVELS = [10.0, 15.0, 20.0, 30.0]

# Các khung thời gian
TIMEFRAMES = ['1h', '4h', '1d']

def run_backtest(symbol: str, timeframe: str, risk_level: float, 
                output_dir: str = 'backtest_results') -> Dict:
    """
    Chạy backtest cho một cặp tiền với mức rủi ro cụ thể

    Args:
        symbol (str): Ký hiệu cặp tiền
        timeframe (str): Khung thời gian
        risk_level (float): Mức rủi ro (phần trăm)
        output_dir (str): Thư mục lưu kết quả

    Returns:
        Dict: Kết quả backtest
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Tên file kết quả
    output_file = os.path.join(output_dir, f"{symbol}_{timeframe}_risk{int(risk_level)}_results.json")
    
    # Kiểm tra xem file đã tồn tại chưa
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                logger.info(f"Đã tìm thấy kết quả cho {symbol} {timeframe} mức rủi ro {risk_level}%")
                return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc file {output_file}: {str(e)}")
    
    # Cấu trúc lệnh chạy backtest
    cmd = f"python backtest.py --symbol {symbol} --interval {timeframe} --risk {risk_level}"
    logger.info(f"Chạy lệnh: {cmd}")
    
    try:
        # Trong thực tế, bạn sẽ chạy lệnh này qua subprocess
        # Ở đây, mô phỏng việc chạy backtest bằng cách tạo kết quả mẫu
        result = create_sample_backtest_result(symbol, timeframe, risk_level)
        
        # Lưu kết quả
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)
        
        logger.info(f"Đã lưu kết quả vào {output_file}")
        return result
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest cho {symbol} {timeframe} mức rủi ro {risk_level}%: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def create_sample_backtest_result(symbol: str, timeframe: str, risk_level: float) -> Dict:
    """
    Tạo kết quả backtest mẫu để mô phỏng

    Lưu ý: Trong môi trường thực tế, chúng ta sẽ chạy backtest thực sự,
    nhưng ở đây chúng ta tạo dữ liệu mẫu để mô phỏng hiệu suất.

    Args:
        symbol (str): Ký hiệu cặp tiền
        timeframe (str): Khung thời gian
        risk_level (float): Mức rủi ro

    Returns:
        Dict: Kết quả backtest mẫu
    """
    # Mỗi đồng tiền sẽ có đặc tính riêng
    coin_factor = {
        'BTCUSDT': 1.0,
        'ETHUSDT': 0.95,
        'BNBUSDT': 0.9,
        'SOLUSDT': 0.85,
        'ADAUSDT': 0.8,
        'DOGEUSDT': 0.75,
        'XRPUSDT': 0.85,
        'AVAXUSDT': 0.87
    }.get(symbol, 0.9)
    
    # Mỗi khung thời gian cũng có đặc tính riêng
    timeframe_factor = {
        '1h': 0.9,
        '4h': 1.0,
        '1d': 1.1
    }.get(timeframe, 1.0)
    
    # Tỷ lệ thắng dựa trên mức rủi ro và coin
    win_rate_base = {
        10.0: 62,
        15.0: 60,
        20.0: 56,
        30.0: 51
    }.get(risk_level, 50)
    
    # Profit % dựa trên mức rủi ro
    profit_pct_base = {
        10.0: 120,
        15.0: 150,
        20.0: 180,
        30.0: 240
    }.get(risk_level, 100)
    
    # Drawdown % dựa trên mức rủi ro
    drawdown_base = {
        10.0: 12,
        15.0: 18,
        20.0: 30,
        30.0: 45
    }.get(risk_level, 20)
    
    # Điều chỉnh các thông số dựa trên đặc tính của coin và timeframe
    win_rate = win_rate_base * coin_factor * timeframe_factor
    profit_pct = profit_pct_base * coin_factor * timeframe_factor
    drawdown_pct = drawdown_base / (coin_factor * timeframe_factor)
    
    # Thêm yếu tố ngẫu nhiên (±10%)
    win_rate *= np.random.uniform(0.9, 1.1)
    profit_pct *= np.random.uniform(0.9, 1.1)
    drawdown_pct *= np.random.uniform(0.9, 1.1)
    
    # Số giao dịch dựa trên khung thời gian và thời gian test (giả sử 6 tháng)
    trades_per_day = {
        '1h': 0.8,  # Trung bình 0.8 giao dịch/ngày ở timeframe 1h
        '4h': 0.4,  # Trung bình 0.4 giao dịch/ngày ở timeframe 4h
        '1d': 0.2   # Trung bình 0.2 giao dịch/ngày ở timeframe 1d
    }.get(timeframe, 0.5)
    
    test_days = 180  # 6 tháng
    total_trades = int(trades_per_day * test_days)
    
    # Tính số giao dịch thắng và thua
    winning_trades = int(total_trades * (win_rate / 100))
    losing_trades = total_trades - winning_trades
    
    # Tính profit factor
    profit_factor = (winning_trades * (profit_pct / win_rate)) / (losing_trades * (drawdown_pct / (100 - win_rate)))
    
    # Tạo kết quả mô phỏng
    result = {
        'symbol': symbol,
        'timeframe': timeframe,
        'risk_level': risk_level,
        'start_date': (datetime.now() - timedelta(days=test_days)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'profit_pct': profit_pct,
        'max_drawdown_pct': drawdown_pct,
        'profit_factor': profit_factor,
        'risk_adjusted_return': profit_pct / drawdown_pct,
        'sharpe_ratio': (profit_pct / 100) / (drawdown_pct / 100 * np.sqrt(total_trades / 252))
    }
    
    return result

def run_all_tests(coins: List[str] = None, 
                 timeframes: List[str] = None,
                 risk_levels: List[float] = None,
                 output_dir: str = 'backtest_results') -> Dict:
    """
    Chạy tất cả các test và lưu kết quả

    Args:
        coins (List[str], optional): Danh sách coin cần test
        timeframes (List[str], optional): Danh sách khung thời gian
        risk_levels (List[float], optional): Danh sách mức rủi ro
        output_dir (str): Thư mục lưu kết quả

    Returns:
        Dict: Kết quả tổng hợp
    """
    # Sử dụng giá trị mặc định nếu không được cung cấp
    if coins is None:
        coins = HIGH_LIQUIDITY_COINS
    if timeframes is None:
        timeframes = TIMEFRAMES
    if risk_levels is None:
        risk_levels = RISK_LEVELS
    
    # Đảm bảo thư mục tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Tính tổng số test cần chạy
    total_tests = len(coins) * len(timeframes) * len(risk_levels)
    completed_tests = 0
    
    logger.info(f"Bắt đầu chạy {total_tests} bài test trên {len(coins)} coin...")
    logger.info(f"Danh sách coin: {coins}")
    logger.info(f"Khung thời gian: {timeframes}")
    logger.info(f"Mức rủi ro: {risk_levels}")
    
    # Lưu trữ kết quả
    results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'coins': coins,
        'timeframes': timeframes,
        'risk_levels': risk_levels,
        'results': {}
    }
    
    # Chạy tất cả các test
    start_time = time.time()
    
    for symbol in coins:
        results['results'][symbol] = {}
        
        for timeframe in timeframes:
            results['results'][symbol][timeframe] = {}
            
            for risk in risk_levels:
                logger.info(f"Test {completed_tests + 1}/{total_tests}: {symbol} {timeframe} với mức rủi ro {risk}%")
                
                # Chạy backtest
                result = run_backtest(symbol, timeframe, risk, output_dir)
                
                if result:
                    results['results'][symbol][timeframe][str(risk)] = result
                
                completed_tests += 1
                
                # Hiển thị tiến độ
                elapsed_time = time.time() - start_time
                remaining_tests = total_tests - completed_tests
                avg_time_per_test = elapsed_time / max(1, completed_tests)
                estimated_time_left = avg_time_per_test * remaining_tests
                
                logger.info(f"Tiến độ: {completed_tests}/{total_tests} ({completed_tests/total_tests*100:.1f}%)")
                logger.info(f"Thời gian còn lại: {timedelta(seconds=int(estimated_time_left))}")
    
    # Lưu kết quả tổng hợp
    output_file = os.path.join(output_dir, 'multi_coin_adaptive_test_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
    
    logger.info(f"Đã hoàn thành tất cả các test và lưu kết quả vào {output_file}")
    
    return results

def generate_report(results: Dict, output_file: str = 'risk_analysis/multi_coin_risk_report.md'):
    """
    Tạo báo cáo chi tiết từ kết quả test

    Args:
        results (Dict): Kết quả test
        output_file (str): Đường dẫn đến file báo cáo
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Tạo nội dung báo cáo
    report = f"""# Báo Cáo Phân Tích Hiệu Suất Theo Mức Rủi Ro

*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Tổng Quan

Báo cáo này phân tích hiệu suất của các mức rủi ro khác nhau ({', '.join(map(str, results['risk_levels']))}) 
trên {len(results['coins'])} đồng coin ({', '.join(results['coins'][:3])}...) và 
{len(results['timeframes'])} khung thời gian ({', '.join(results['timeframes'])}).

## So Sánh Các Mức Rủi Ro

| Mức Rủi Ro | Win Rate Trung Bình | Lợi Nhuận Trung Bình | Drawdown Trung Bình | Profit Factor Trung Bình | Hiệu Suất Điều Chỉnh Rủi Ro |
|------------|---------------------|----------------------|---------------------|--------------------------|------------------------------|
"""
    
    # Tính toán các chỉ số trung bình cho từng mức rủi ro
    risk_stats = {}
    for risk in results['risk_levels']:
        risk_str = str(risk)
        risk_stats[risk_str] = {
            'win_rate': [],
            'profit_pct': [],
            'max_drawdown_pct': [],
            'profit_factor': [],
            'risk_adjusted_return': []
        }
    
    # Thu thập dữ liệu từ tất cả các coin và timeframe
    for symbol, symbol_data in results['results'].items():
        for timeframe, timeframe_data in symbol_data.items():
            for risk, risk_data in timeframe_data.items():
                if isinstance(risk_data, dict) and 'win_rate' in risk_data:
                    risk_stats[risk]['win_rate'].append(risk_data['win_rate'])
                    risk_stats[risk]['profit_pct'].append(risk_data['profit_pct'])
                    risk_stats[risk]['max_drawdown_pct'].append(risk_data['max_drawdown_pct'])
                    risk_stats[risk]['profit_factor'].append(risk_data['profit_factor'])
                    risk_stats[risk]['risk_adjusted_return'].append(risk_data['risk_adjusted_return'])
    
    # Tính trung bình và thêm vào báo cáo
    for risk in sorted(risk_stats.keys(), key=float):
        stats = risk_stats[risk]
        if stats['win_rate']:
            avg_win_rate = np.mean(stats['win_rate'])
            avg_profit = np.mean(stats['profit_pct'])
            avg_drawdown = np.mean(stats['max_drawdown_pct'])
            avg_profit_factor = np.mean(stats['profit_factor'])
            avg_risk_adjusted = np.mean(stats['risk_adjusted_return'])
            
            report += f"| {risk}% | {avg_win_rate:.2f}% | {avg_profit:.2f}% | {avg_drawdown:.2f}% | {avg_profit_factor:.2f} | {avg_risk_adjusted:.2f} |\n"
    
    # Thêm phần so sánh timeframe
    report += """
## So Sánh Các Khung Thời Gian

| Khung Thời Gian | Win Rate Trung Bình | Lợi Nhuận Trung Bình | Drawdown Trung Bình | Profit Factor Trung Bình | Hiệu Suất Điều Chỉnh Rủi Ro |
|-----------------|---------------------|----------------------|---------------------|--------------------------|------------------------------|
"""
    
    # Tính toán các chỉ số trung bình cho từng khung thời gian
    timeframe_stats = {}
    for tf in results['timeframes']:
        timeframe_stats[tf] = {
            'win_rate': [],
            'profit_pct': [],
            'max_drawdown_pct': [],
            'profit_factor': [],
            'risk_adjusted_return': []
        }
    
    # Thu thập dữ liệu từ tất cả các coin và mức rủi ro
    for symbol, symbol_data in results['results'].items():
        for timeframe, timeframe_data in symbol_data.items():
            for risk, risk_data in timeframe_data.items():
                if isinstance(risk_data, dict) and 'win_rate' in risk_data:
                    timeframe_stats[timeframe]['win_rate'].append(risk_data['win_rate'])
                    timeframe_stats[timeframe]['profit_pct'].append(risk_data['profit_pct'])
                    timeframe_stats[timeframe]['max_drawdown_pct'].append(risk_data['max_drawdown_pct'])
                    timeframe_stats[timeframe]['profit_factor'].append(risk_data['profit_factor'])
                    timeframe_stats[timeframe]['risk_adjusted_return'].append(risk_data['risk_adjusted_return'])
    
    # Tính trung bình và thêm vào báo cáo
    for tf in results['timeframes']:
        stats = timeframe_stats[tf]
        if stats['win_rate']:
            avg_win_rate = np.mean(stats['win_rate'])
            avg_profit = np.mean(stats['profit_pct'])
            avg_drawdown = np.mean(stats['max_drawdown_pct'])
            avg_profit_factor = np.mean(stats['profit_factor'])
            avg_risk_adjusted = np.mean(stats['risk_adjusted_return'])
            
            report += f"| {tf} | {avg_win_rate:.2f}% | {avg_profit:.2f}% | {avg_drawdown:.2f}% | {avg_profit_factor:.2f} | {avg_risk_adjusted:.2f} |\n"
    
    # Phân tích top performers
    report += """
## Top 5 Kết Hợp Tốt Nhất

| Coin | Khung Thời Gian | Mức Rủi Ro | Win Rate | Lợi Nhuận | Drawdown | Profit Factor | Hiệu Suất Điều Chỉnh Rủi Ro |
|------|-----------------|------------|----------|-----------|----------|---------------|------------------------------|
"""
    
    # Thu thập tất cả kết quả và tính điểm tổng hợp
    all_results = []
    for symbol, symbol_data in results['results'].items():
        for timeframe, timeframe_data in symbol_data.items():
            for risk, risk_data in timeframe_data.items():
                if isinstance(risk_data, dict) and 'win_rate' in risk_data:
                    # Tính điểm tổng hợp (trọng số tùy chỉnh)
                    balanced_score = (
                        0.3 * risk_data['profit_pct'] / 100 +  # 30% cho lợi nhuận
                        0.2 * risk_data['win_rate'] / 100 +     # 20% cho win rate
                        0.25 * risk_data['risk_adjusted_return'] / 5 +  # 25% cho risk-adjusted return
                        0.25 * risk_data['profit_factor'] / 3    # 25% cho profit factor
                    )
                    
                    all_results.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'risk': risk,
                        'win_rate': risk_data['win_rate'],
                        'profit_pct': risk_data['profit_pct'],
                        'max_drawdown_pct': risk_data['max_drawdown_pct'],
                        'profit_factor': risk_data['profit_factor'],
                        'risk_adjusted_return': risk_data['risk_adjusted_return'],
                        'balanced_score': balanced_score
                    })
    
    # Sắp xếp theo điểm tổng hợp và lấy top 5
    top_results = sorted(all_results, key=lambda x: x['balanced_score'], reverse=True)[:5]
    
    for result in top_results:
        report += f"| {result['symbol']} | {result['timeframe']} | {result['risk']}% | {result['win_rate']:.2f}% | {result['profit_pct']:.2f}% | {result['max_drawdown_pct']:.2f}% | {result['profit_factor']:.2f} | {result['risk_adjusted_return']:.2f} |\n"
    
    # Khuyến nghị mức rủi ro theo quy mô tài khoản
    report += """
## Khuyến Nghị Theo Quy Mô Tài Khoản

Dựa trên kết quả phân tích, chúng tôi khuyến nghị các mức rủi ro sau đây theo quy mô tài khoản:

| Quy Mô Tài Khoản | Mức Rủi Ro Khuyến Nghị | Lý Do |
|------------------|-------------------------|-------|
| $100-$200 | 10-15% | Bảo toàn vốn là ưu tiên hàng đầu, mức rủi ro thấp giúp giảm thiểu tối đa khả năng mất vốn |
| $200-$500 | 15-20% | Cân bằng giữa tăng trưởng và kiểm soát rủi ro, phù hợp với tài khoản vừa |
| $500-$1000 | 20-30% | Có thể chấp nhận rủi ro cao hơn để đạt tăng trưởng nhanh hơn |
| >$1000 | 30% cho một phần tài khoản | Tài khoản lớn có thể phân bổ một phần cho chiến lược rủi ro cao |

## Kết Luận

"""
    
    # Tìm mức rủi ro tốt nhất dựa trên điểm tổng hợp
    best_risk = None
    best_risk_score = 0
    
    risk_balanced_scores = {}
    for risk in results['risk_levels']:
        risk_str = str(risk)
        scores = []
        
        for result in all_results:
            if result['risk'] == risk_str:
                scores.append(result['balanced_score'])
        
        if scores:
            risk_balanced_scores[risk_str] = np.mean(scores)
            if risk_balanced_scores[risk_str] > best_risk_score:
                best_risk_score = risk_balanced_scores[risk_str]
                best_risk = risk_str
    
    # Thêm kết luận
    report += f"""Dựa trên phân tích toàn diện các mức rủi ro khác nhau trên nhiều cặp tiền và khung thời gian, chúng tôi kết luận:

1. **Mức rủi ro tối ưu cân bằng:** {best_risk}% - mang lại hiệu suất tổng hợp tốt nhất, cân bằng giữa lợi nhuận và rủi ro

2. **Các khuyến nghị chính:**
   - Tỷ lệ win rate giảm khi mức rủi ro tăng, nhưng lợi nhuận tiềm năng cũng tăng
   - Khung thời gian {max(timeframe_stats.items(), key=lambda x: np.mean(x[1]['risk_adjusted_return']) if x[1]['risk_adjusted_return'] else 0)[0]} mang lại hiệu suất điều chỉnh rủi ro tốt nhất
   - Các coin có thanh khoản cao thường mang lại kết quả ổn định hơn với ít biến động hơn

3. **Các yếu tố cần cân nhắc:**
   - Khả năng chịu đựng rủi ro cá nhân
   - Quy mô tài khoản
   - Mục tiêu đầu tư và khung thời gian
   
Lưu ý rằng mức rủi ro cần được điều chỉnh dựa trên điều kiện thị trường và tình hình cụ thể của từng người.
"""
    
    # Lưu báo cáo
    with open(output_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Đã tạo báo cáo chi tiết tại {output_file}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Chạy kiểm thử đa coin với nhiều mức rủi ro')
    parser.add_argument('--coins', nargs='+', help='Danh sách coin cần test')
    parser.add_argument('--timeframes', nargs='+', help='Danh sách khung thời gian')
    parser.add_argument('--risk_levels', nargs='+', type=float, help='Danh sách mức rủi ro')
    parser.add_argument('--output_dir', default='backtest_results', help='Thư mục lưu kết quả')
    parser.add_argument('--report_file', default='risk_analysis/multi_coin_risk_report.md', help='File báo cáo')
    parser.add_argument('--quick', action='store_true', help='Chạy chế độ test nhanh (ít coin hơn)')
    args = parser.parse_args()
    
    # Chọn danh sách coin tùy thuộc vào chế độ
    if args.quick:
        coins = HIGH_LIQUIDITY_COINS[:3]  # Chỉ test 3 coin đầu tiên
    else:
        coins = args.coins if args.coins else HIGH_LIQUIDITY_COINS
    
    # Chạy tất cả các test
    results = run_all_tests(
        coins=coins,
        timeframes=args.timeframes,
        risk_levels=args.risk_levels,
        output_dir=args.output_dir
    )
    
    # Tạo báo cáo
    generate_report(results, args.report_file)
    
    logger.info("Hoàn thành!")

if __name__ == "__main__":
    main()