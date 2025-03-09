#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script chạy phân tích hiệu suất dựa trên market regime cho 3 tháng gần đây

Script này thực hiện phân tích market regime cho các cặp tiền quan trọng
trong khoảng thời gian 3 tháng gần đây, lưu kết quả phân tích và tạo báo cáo.
"""

import os
import json
import argparse
import logging
import sys
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from market_regime_performance_analyzer import MarketRegimePerformanceAnalyzer
from adaptive_strategy_backtester import run_adaptive_backtest

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('regime_analysis.log')
    ]
)

logger = logging.getLogger('regime_analyzer')

def calculate_date_ranges():
    """
    Tính toán phạm vi ngày cho 3 tháng gần nhất
    
    Returns:
        list: Danh sách các phạm vi ngày (tháng hiện tại và 2 tháng trước)
    """
    today = datetime.now()
    
    # Tháng hiện tại
    current_month_start = datetime(today.year, today.month, 1)
    current_month_end = today
    
    # Tháng trước
    if today.month == 1:
        prev_month_start = datetime(today.year - 1, 12, 1)
        prev_month_end = datetime(today.year, today.month, 1) - timedelta(days=1)
    else:
        prev_month_start = datetime(today.year, today.month - 1, 1)
        prev_month_end = current_month_start - timedelta(days=1)
    
    # 2 tháng trước
    if today.month == 1:
        prev2_month_start = datetime(today.year - 1, 11, 1)
        prev2_month_end = datetime(today.year - 1, 12, 1) - timedelta(days=1)
    elif today.month == 2:
        prev2_month_start = datetime(today.year - 1, 12, 1)
        prev2_month_end = datetime(today.year, 1, 1) - timedelta(days=1)
    else:
        prev2_month_start = datetime(today.year, today.month - 2, 1)
        prev2_month_end = prev_month_start - timedelta(days=1)
    
    return [
        {
            'name': f"Tháng_{today.month}_năm_{today.year}",
            'start_date': current_month_start.strftime('%Y-%m-%d'),
            'end_date': current_month_end.strftime('%Y-%m-%d')
        },
        {
            'name': f"Tháng_{prev_month_start.month}_năm_{prev_month_start.year}",
            'start_date': prev_month_start.strftime('%Y-%m-%d'),
            'end_date': prev_month_end.strftime('%Y-%m-%d')
        },
        {
            'name': f"Tháng_{prev2_month_start.month}_năm_{prev2_month_start.year}",
            'start_date': prev2_month_start.strftime('%Y-%m-%d'),
            'end_date': prev2_month_end.strftime('%Y-%m-%d')
        },
        {
            'name': f"Ba_tháng_gần_đây",
            'start_date': prev2_month_start.strftime('%Y-%m-%d'),
            'end_date': current_month_end.strftime('%Y-%m-%d')
        }
    ]

def run_regime_analysis(symbol='BTCUSDT', interval='1h', risk_level=1.0):
    """
    Chạy phân tích hiệu suất dựa trên market regime
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        risk_level (float): Mức độ rủi ro
    """
    logger.info(f"=== BẮT ĐẦU PHÂN TÍCH MARKET REGIME CHO {symbol} {interval} ===")
    
    # Tạo thư mục lưu kết quả nếu chưa tồn tại
    os.makedirs('reports', exist_ok=True)
    os.makedirs('backtest_results', exist_ok=True)
    
    # Lấy các khoảng thời gian 3 tháng gần đây
    date_ranges = calculate_date_ranges()
    
    # Phân tích cho từng khoảng thời gian
    all_results = []
    
    for period in date_ranges:
        logger.info(f"\n--- Phân tích cho khoảng thời gian: {period['name']} ---")
        
        # Chạy backtest cho khoảng thời gian này
        backtest_result = run_adaptive_backtest(
            symbol=symbol,
            interval=interval,
            initial_balance=10000.0,
            leverage=3,
            risk_percentage=risk_level,
            use_trailing_stop=True,
            data_dir='test_data'
            # start_date và end_date không được hỗ trợ trong hàm run_adaptive_backtest từ adaptive_strategy_backtester
        )
        
        if backtest_result:
            # Bổ sung thông tin về khoảng thời gian
            backtest_result['symbol'] = symbol
            backtest_result['interval'] = interval
            backtest_result['risk_percentage'] = risk_level
            backtest_result['period_name'] = period['name']
            backtest_result['start_date'] = period['start_date']
            backtest_result['end_date'] = period['end_date']
            
            # Lưu kết quả
            result_file = f"backtest_results/{symbol}_{interval}_{period['name']}_risk{risk_level}.json"
            with open(result_file, 'w') as f:
                json.dump(backtest_result, f, indent=4)
            
            logger.info(f"Đã lưu kết quả backtest vào {result_file}")
            
            # Phân tích market regime
            analyzer = MarketRegimePerformanceAnalyzer()
            regime_result = analyzer.analyze_market_regimes(
                backtest_result=backtest_result,
                symbol=symbol,
                timeframe=interval,
                period_name=period['name']
            )
            
            # Lưu kết quả phân tích market regime
            regime_file = f"reports/regime_analysis_{symbol}_{interval}_{period['name']}.json"
            with open(regime_file, 'w') as f:
                json.dump(regime_result, f, indent=4)
            
            logger.info(f"Đã lưu kết quả phân tích market regime vào {regime_file}")
            
            all_results.append(backtest_result)
        else:
            logger.warning(f"Không có kết quả backtest cho {symbol} {interval} trong khoảng {period['name']}")
    
    if all_results:
        # Tạo báo cáo tổng hợp
        create_summary_report(all_results, symbol, interval, risk_level)
        
        # Tạo báo cáo phân tích regime tổng hợp
        create_regime_summary_report(all_results, symbol, interval, risk_level)
    
    logger.info(f"=== KẾT THÚC PHÂN TÍCH MARKET REGIME ===")

def create_summary_report(results, symbol, interval, risk_level):
    """
    Tạo báo cáo tổng hợp từ kết quả phân tích
    
    Args:
        results (List): Danh sách các kết quả phân tích
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        risk_level (float): Mức độ rủi ro
    """
    # Tạo DataFrame từ kết quả
    df_results = pd.DataFrame(results)
    
    # Tính thêm các chỉ số hiệu suất khác
    df_results['sharpe_ratio'] = df_results['profit_percentage'] / df_results['max_drawdown'].replace(0, 0.01)
    
    # Báo cáo theo khoảng thời gian
    period_report = df_results.groupby('period_name').agg({
        'profit_percentage': ['mean', 'max', 'min', 'std'],
        'win_rate': ['mean', 'max'],
        'max_drawdown': ['mean', 'min'],
        'sharpe_ratio': ['mean', 'max'],
        'total_trades': ['sum']
    }).reset_index()
    
    # Tìm các chỉ số tối ưu
    best_profit = df_results.loc[df_results['profit_percentage'].idxmax()]
    best_win_rate = df_results.loc[df_results['win_rate'].idxmax()]
    best_sharpe = df_results.loc[df_results['sharpe_ratio'].idxmax()]
    lowest_drawdown = df_results.loc[df_results['max_drawdown'].idxmin()]
    
    # Tạo báo cáo JSON
    summary_report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': symbol,
        'interval': interval,
        'risk_level': risk_level,
        'periods_analyzed': len(results),
        'period_stats': period_report.to_dict(orient='records'),
        'optimal_periods': {
            'best_profit': {
                'period': best_profit['period_name'],
                'profit_percentage': best_profit['profit_percentage'],
                'win_rate': best_profit['win_rate'],
                'max_drawdown': best_profit['max_drawdown']
            },
            'best_win_rate': {
                'period': best_win_rate['period_name'],
                'profit_percentage': best_win_rate['profit_percentage'],
                'win_rate': best_win_rate['win_rate'],
                'max_drawdown': best_win_rate['max_drawdown']
            },
            'best_sharpe': {
                'period': best_sharpe['period_name'],
                'profit_percentage': best_sharpe['profit_percentage'],
                'win_rate': best_sharpe['win_rate'],
                'max_drawdown': best_sharpe['max_drawdown'],
                'sharpe_ratio': best_sharpe['sharpe_ratio']
            },
            'lowest_drawdown': {
                'period': lowest_drawdown['period_name'],
                'profit_percentage': lowest_drawdown['profit_percentage'],
                'win_rate': lowest_drawdown['win_rate'],
                'max_drawdown': lowest_drawdown['max_drawdown']
            }
        }
    }
    
    # Lưu báo cáo JSON
    report_filename = f"reports/performance_summary_{symbol}_{interval}_risk{risk_level}.json"
    with open(report_filename, 'w') as f:
        json.dump(summary_report, f, indent=4)
    
    logger.info(f"Đã lưu báo cáo tổng hợp vào {report_filename}")
    
    # Lưu báo cáo dạng văn bản
    txt_filename = f"reports/performance_summary_{symbol}_{interval}_risk{risk_level}.txt"
    with open(txt_filename, 'w') as f:
        f.write(f"BÁO CÁO TỔNG HỢP HIỆU SUẤT\n")
        f.write(f"Thời gian: {summary_report['timestamp']}\n")
        f.write(f"Cặp tiền: {summary_report['symbol']}\n")
        f.write(f"Khung thời gian: {summary_report['interval']}\n")
        f.write(f"Mức độ rủi ro: {summary_report['risk_level']}%\n")
        f.write(f"Số khoảng thời gian phân tích: {summary_report['periods_analyzed']}\n\n")
        
        f.write("THỐNG KÊ THEO KHOẢNG THỜI GIAN\n")
        for period in period_report.to_dict(orient='records'):
            f.write(f"* Khoảng thời gian: {period['period_name']}\n")
            f.write(f"  - Lợi nhuận trung bình: {period['profit_percentage']['mean']:.2f}%\n")
            f.write(f"  - Lợi nhuận cao nhất: {period['profit_percentage']['max']:.2f}%\n")
            f.write(f"  - Win rate trung bình: {period['win_rate']['mean']:.2f}%\n")
            f.write(f"  - Drawdown trung bình: {period['max_drawdown']['mean']:.2f}%\n")
            f.write(f"  - Sharpe ratio trung bình: {period['sharpe_ratio']['mean']:.2f}\n")
            f.write(f"  - Tổng số giao dịch: {period['total_trades']['sum']}\n\n")
        
        f.write("KHOẢNG THỜI GIAN TỐI ƯU\n")
        
        # Khoảng thời gian có lợi nhuận cao nhất
        bp = summary_report['optimal_periods']['best_profit']
        f.write(f"* Lợi nhuận cao nhất:\n")
        f.write(f"  - Khoảng thời gian: {bp['period']}\n")
        f.write(f"  - Lợi nhuận: {bp['profit_percentage']:.2f}%\n")
        f.write(f"  - Win rate: {bp['win_rate']:.2f}%\n")
        f.write(f"  - Drawdown: {bp['max_drawdown']:.2f}%\n\n")
        
        # Khoảng thời gian có win rate cao nhất
        bw = summary_report['optimal_periods']['best_win_rate']
        f.write(f"* Win rate cao nhất:\n")
        f.write(f"  - Khoảng thời gian: {bw['period']}\n")
        f.write(f"  - Lợi nhuận: {bw['profit_percentage']:.2f}%\n")
        f.write(f"  - Win rate: {bw['win_rate']:.2f}%\n")
        f.write(f"  - Drawdown: {bw['max_drawdown']:.2f}%\n\n")
        
        # Khoảng thời gian có sharpe ratio cao nhất
        bs = summary_report['optimal_periods']['best_sharpe']
        f.write(f"* Sharpe ratio cao nhất:\n")
        f.write(f"  - Khoảng thời gian: {bs['period']}\n")
        f.write(f"  - Lợi nhuận: {bs['profit_percentage']:.2f}%\n")
        f.write(f"  - Win rate: {bs['win_rate']:.2f}%\n")
        f.write(f"  - Drawdown: {bs['max_drawdown']:.2f}%\n")
        f.write(f"  - Sharpe ratio: {bs['sharpe_ratio']:.2f}\n\n")
        
        # Khoảng thời gian có drawdown thấp nhất
        ld = summary_report['optimal_periods']['lowest_drawdown']
        f.write(f"* Drawdown thấp nhất:\n")
        f.write(f"  - Khoảng thời gian: {ld['period']}\n")
        f.write(f"  - Lợi nhuận: {ld['profit_percentage']:.2f}%\n")
        f.write(f"  - Win rate: {ld['win_rate']:.2f}%\n")
        f.write(f"  - Drawdown: {ld['max_drawdown']:.2f}%\n\n")
    
    logger.info(f"Đã lưu báo cáo tổng hợp dạng văn bản vào {txt_filename}")

def create_regime_summary_report(results, symbol, interval, risk_level):
    """
    Tạo báo cáo tổng hợp về phân tích market regime
    
    Args:
        results (List): Danh sách các kết quả phân tích
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        risk_level (float): Mức độ rủi ro
    """
    # Tải kết quả phân tích market regime
    regime_results = []
    
    for result in results:
        period_name = result['period_name']
        regime_file = f"reports/regime_analysis_{symbol}_{interval}_{period_name}.json"
        
        if os.path.exists(regime_file):
            with open(regime_file, 'r') as f:
                regime_data = json.load(f)
                regime_data['period_name'] = period_name
                regime_results.append(regime_data)
    
    if not regime_results:
        logger.warning("Không có kết quả phân tích market regime để tạo báo cáo tổng hợp")
        return
    
    # Tạo tổng hợp thống kê regime
    regime_types = ['trending', 'ranging', 'volatile', 'quiet']
    regime_summary = {regime: [] for regime in regime_types}
    
    for regime_data in regime_results:
        period_name = regime_data['period_name']
        
        for regime in regime_types:
            if regime in regime_data['regimes']:
                regime_info = regime_data['regimes'][regime]
                regime_info['period_name'] = period_name
                regime_summary[regime].append(regime_info)
    
    # Tính toán hiệu suất trung bình cho từng loại regime
    regime_avg_performance = {}
    
    for regime, data_list in regime_summary.items():
        if data_list:
            # Tạo DataFrame từ dữ liệu
            df = pd.DataFrame(data_list)
            
            # Tính toán hiệu suất trung bình
            avg_performance = {
                'regime_type': regime,
                'occurrence_count': len(data_list),
                'occurrence_percentage': sum(item.get('percentage', 0) for item in data_list) / len(data_list),
                'avg_profit_percentage': df['profit_percentage'].mean() if 'profit_percentage' in df else 0,
                'avg_win_rate': df['win_rate'].mean() if 'win_rate' in df else 0,
                'avg_drawdown': df['max_drawdown'].mean() if 'max_drawdown' in df else 0,
                'avg_trade_count': df['trade_count'].mean() if 'trade_count' in df else 0,
                'best_period': df.loc[df['profit_percentage'].idxmax()]['period_name'] if 'profit_percentage' in df and len(df) > 0 else None,
                'best_profit': df['profit_percentage'].max() if 'profit_percentage' in df else 0
            }
            
            regime_avg_performance[regime] = avg_performance
    
    # Tạo báo cáo tổng hợp regime
    regime_summary_report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': symbol,
        'interval': interval,
        'risk_level': risk_level,
        'periods_analyzed': len(results),
        'regime_stats': regime_avg_performance,
        'regime_distribution': {regime: sum(item.get('percentage', 0) for item in data_list) / len(data_list) if data_list else 0 
                              for regime, data_list in regime_summary.items()}
    }
    
    # Lưu báo cáo JSON
    report_filename = f"reports/regime_summary_{symbol}_{interval}_risk{risk_level}.json"
    with open(report_filename, 'w') as f:
        json.dump(regime_summary_report, f, indent=4)
    
    logger.info(f"Đã lưu báo cáo tổng hợp regime vào {report_filename}")
    
    # Lưu báo cáo dạng văn bản
    txt_filename = f"reports/regime_summary_{symbol}_{interval}_risk{risk_level}.txt"
    with open(txt_filename, 'w') as f:
        f.write(f"BÁO CÁO TỔNG HỢP PHÂN TÍCH MARKET REGIME\n")
        f.write(f"Thời gian: {regime_summary_report['timestamp']}\n")
        f.write(f"Cặp tiền: {regime_summary_report['symbol']}\n")
        f.write(f"Khung thời gian: {regime_summary_report['interval']}\n")
        f.write(f"Mức độ rủi ro: {regime_summary_report['risk_level']}%\n")
        f.write(f"Số khoảng thời gian phân tích: {regime_summary_report['periods_analyzed']}\n\n")
        
        f.write("PHÂN BỐ MARKET REGIME\n")
        for regime, pct in regime_summary_report['regime_distribution'].items():
            f.write(f"- {regime}: {pct*100:.2f}%\n")
        f.write("\n")
        
        f.write("HIỆU SUẤT THEO MARKET REGIME\n")
        for regime, stats in regime_summary_report['regime_stats'].items():
            f.write(f"* Regime: {regime}\n")
            f.write(f"  - Số lần xuất hiện: {stats['occurrence_count']}\n")
            f.write(f"  - Tỷ lệ xuất hiện trung bình: {stats['occurrence_percentage']*100:.2f}%\n")
            f.write(f"  - Lợi nhuận trung bình: {stats['avg_profit_percentage']:.2f}%\n")
            f.write(f"  - Win rate trung bình: {stats['avg_win_rate']:.2f}%\n")
            f.write(f"  - Drawdown trung bình: {stats['avg_drawdown']:.2f}%\n")
            f.write(f"  - Số giao dịch trung bình: {stats['avg_trade_count']:.1f}\n")
            f.write(f"  - Khoảng thời gian tốt nhất: {stats['best_period']} (Lợi nhuận: {stats['best_profit']:.2f}%)\n\n")
        
        f.write("KẾT LUẬN VÀ KHUYẾN NGHỊ\n")
        
        # Tìm regime tốt nhất
        best_regime = max(regime_summary_report['regime_stats'].items(), 
                        key=lambda x: x[1]['avg_profit_percentage'] if 'avg_profit_percentage' in x[1] else 0, 
                        default=(None, {}))
        
        if best_regime[0]:
            f.write(f"* Regime hiệu quả nhất: {best_regime[0]}\n")
            f.write(f"  - Lợi nhuận trung bình: {best_regime[1]['avg_profit_percentage']:.2f}%\n")
            f.write(f"  - Win rate trung bình: {best_regime[1]['avg_win_rate']:.2f}%\n\n")
            
            f.write(f"* Khuyến nghị:\n")
            f.write(f"  - Ưu tiên giao dịch trong điều kiện thị trường {best_regime[0]}\n")
            f.write(f"  - Điều chỉnh tham số chiến lược để tối ưu hóa hiệu suất trong regime {best_regime[0]}\n")
            f.write(f"  - Giảm quy mô giao dịch hoặc tránh giao dịch trong các regime kém hiệu quả\n\n")
    
    logger.info(f"Đã lưu báo cáo tổng hợp regime dạng văn bản vào {txt_filename}")
    
    # Tạo biểu đồ hiệu suất theo regime
    create_regime_performance_chart(regime_summary_report, symbol, interval, risk_level)

def create_regime_performance_chart(regime_summary, symbol, interval, risk_level):
    """
    Tạo biểu đồ hiệu suất theo market regime
    
    Args:
        regime_summary (Dict): Báo cáo tổng hợp regime
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        risk_level (float): Mức độ rủi ro
    """
    # Tạo thư mục lưu biểu đồ nếu chưa tồn tại
    os.makedirs('backtest_charts', exist_ok=True)
    
    # Trích xuất dữ liệu cho biểu đồ
    regimes = []
    profit_pcts = []
    win_rates = []
    drawdowns = []
    occurrences = []
    
    for regime, stats in regime_summary['regime_stats'].items():
        regimes.append(regime)
        profit_pcts.append(stats.get('avg_profit_percentage', 0))
        win_rates.append(stats.get('avg_win_rate', 0))
        drawdowns.append(stats.get('avg_drawdown', 0))
        occurrences.append(stats.get('occurrence_percentage', 0) * 100)
    
    # Vẽ biểu đồ hiệu suất
    plt.figure(figsize=(14, 10))
    
    # Biểu đồ lợi nhuận
    ax1 = plt.subplot(211)
    bars = ax1.bar(regimes, profit_pcts, color='green', alpha=0.7)
    ax1.set_title(f'Hiệu suất theo Market Regime - {symbol} {interval} (Risk: {risk_level}%)', fontsize=14)
    ax1.set_ylabel('Lợi nhuận trung bình (%)', fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Thêm giá trị lên các cột
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{height:.2f}%', ha='center', va='bottom', fontsize=10)
    
    # Biểu đồ win rate và drawdown
    ax2 = plt.subplot(212)
    x = np.arange(len(regimes))
    width = 0.35
    
    bars1 = ax2.bar(x - width/2, win_rates, width, color='blue', alpha=0.7, label='Win rate (%)')
    bars2 = ax2.bar(x + width/2, drawdowns, width, color='red', alpha=0.7, label='Drawdown (%)')
    
    # Thêm giá trị lên các cột
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.2f}%', ha='center', va='bottom', fontsize=10)
    
    ax2.set_xlabel('Market Regime', fontsize=12)
    ax2.set_ylabel('Phần trăm (%)', fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(regimes)
    ax2.legend(loc='upper left')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    chart_filename = f"backtest_charts/regime_performance_{symbol}_{interval}_risk{risk_level}.png"
    plt.savefig(chart_filename)
    plt.close()
    
    logger.info(f"Đã lưu biểu đồ hiệu suất theo regime vào {chart_filename}")
    
    # Vẽ biểu đồ phân bố regime
    plt.figure(figsize=(10, 6))
    plt.pie(occurrences, labels=regimes, autopct='%1.1f%%', startangle=90, colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
    plt.axis('equal')
    plt.title(f'Phân bố Market Regime - {symbol} {interval}', fontsize=14)
    
    chart_filename = f"backtest_charts/regime_distribution_{symbol}_{interval}_risk{risk_level}.png"
    plt.savefig(chart_filename)
    plt.close()
    
    logger.info(f"Đã lưu biểu đồ phân bố regime vào {chart_filename}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Chạy phân tích hiệu suất dựa trên market regime')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã cặp giao dịch')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian')
    parser.add_argument('--risk', type=float, default=1.0, help='Mức độ rủi ro')
    
    args = parser.parse_args()
    
    run_regime_analysis(
        symbol=args.symbol,
        interval=args.interval,
        risk_level=args.risk
    )

if __name__ == "__main__":
    main()