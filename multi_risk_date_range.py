#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script chạy backtest với nhiều mức độ rủi ro trên các khoảng thời gian khác nhau

Script này chạy backtest với nhiều mức độ rủi ro (từ 0.5% đến 3.0%) trên các 
khoảng thời gian khác nhau, lưu kết quả, và tạo báo cáo tổng hợp.
"""

import os
import json
import argparse
import logging
import sys
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from enhanced_backtest import run_adaptive_backtest

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('multi_risk_date_range.log')
    ]
)

logger = logging.getLogger('multi_risk')

# Đảm bảo thư mục kết quả tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)
os.makedirs("reports", exist_ok=True)

def run_multi_risk_test(symbol: str, interval: str, use_all_symbols: bool = False):
    """
    Chạy test với nhiều mức độ rủi ro trên các khoảng thời gian khác nhau
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        use_all_symbols (bool): Có sử dụng tất cả các cặp tiền không
    """
    logger.info(f"=== BẮT ĐẦU CHẠY BACKTEST VỚI NHIỀU MỨC ĐỘ RỦI RO ===")
    logger.info(f"Symbol: {symbol}, Interval: {interval}")
    
    # Danh sách các mức độ rủi ro cần kiểm tra
    risk_levels = [0.5, 1.0, 1.5, 2.0, 3.0]
    
    # Các khoảng thời gian kiểm thử - dựa trên dữ liệu thực tế 3 tháng gần đây
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    
    # Tháng hiện tại
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year
    
    # Tháng trước đó nữa
    if current_month == 1:
        prev2_month = 11
        prev2_year = current_year - 1
    elif current_month == 2:
        prev2_month = 12
        prev2_year = current_year - 1
    else:
        prev2_month = current_month - 2
        prev2_year = current_year
    
    test_periods = [
        # Tháng hiện tại
        {
            'name': f'Tháng_{current_month}_năm_{current_year}',
            'start_date': f'{current_year}-{current_month:02d}-01',
            'end_date': today.strftime('%Y-%m-%d')
        },
        # Tháng trước
        {
            'name': f'Tháng_{prev_month}_năm_{prev_year}',
            'start_date': f'{prev_year}-{prev_month:02d}-01',
            'end_date': f'{prev_year}-{prev_month:02d}-28' if prev_month != 2 else f'{prev_year}-{prev_month:02d}-{29 if (prev_year % 4 == 0 and prev_year % 100 != 0) or (prev_year % 400 == 0) else 28}'
        },
        # Tháng trước nữa
        {
            'name': f'Tháng_{prev2_month}_năm_{prev2_year}',
            'start_date': f'{prev2_year}-{prev2_month:02d}-01',
            'end_date': f'{prev2_year}-{prev2_month:02d}-28' if prev2_month != 2 else f'{prev2_year}-{prev2_month:02d}-{29 if (prev2_year % 4 == 0 and prev2_year % 100 != 0) or (prev2_year % 400 == 0) else 28}'
        },
        # Ba tháng đầy đủ
        {
            'name': f'Ba_tháng_gần_đây',
            'start_date': f'{prev2_year}-{prev2_month:02d}-01',
            'end_date': today.strftime('%Y-%m-%d')
        }
    ]
    
    # Danh sách các cặp tiền nếu chạy chế độ đa cặp
    symbols = [symbol]
    if use_all_symbols:
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    
    # Theo dõi tất cả các kết quả để phân tích
    all_results = []
    
    # Chạy test cho tất cả tổ hợp (khoảng thời gian, mức rủi ro, cặp tiền)
    for period in test_periods:
        logger.info(f"\n========== KHOẢNG THỜI GIAN: {period['name']} ==========")
        logger.info(f"Phạm vi: {period['start_date']} đến {period['end_date']}")
        
        for sym in symbols:
            logger.info(f"\n----- CẶP TIỀN: {sym} -----")
            
            period_results = []
            for risk in risk_levels:
                logger.info(f"Chạy với mức rủi ro: {risk}%")
                
                # Tên file kết quả
                result_filename = f"{sym}_{interval}_{period['name']}_risk{risk}.json"
                
                # Chạy backtest
                backtest_result = run_adaptive_backtest(
                    symbol=sym,
                    interval=interval,
                    initial_balance=10000.0,
                    leverage=3,
                    risk_percentage=risk,
                    stop_loss_pct=7.0,
                    take_profit_pct=15.0,
                    use_adaptive_risk=True,
                    data_dir='test_data',
                    start_date=period['start_date'],
                    end_date=period['end_date']
                )
                
                # Lưu biểu đồ riêng sau khi có kết quả
                if backtest_result:
                    chart_filename = f"backtest_charts/{sym}_{interval}_{period['name']}_risk{risk}.png"
                    # Lưu ý: Có thể lưu biểu đồ nếu cần
                
                # Bổ sung thông tin thêm
                if backtest_result:
                    backtest_result['symbol'] = sym
                    backtest_result['interval'] = interval
                    backtest_result['risk_percentage'] = risk
                    backtest_result['start_date'] = period['start_date']
                    backtest_result['end_date'] = period['end_date']
                    backtest_result['analysis_period'] = period['name']
                    
                    # Lưu kết quả ra file
                    result_path = os.path.join('backtest_results', result_filename)
                    with open(result_path, 'w') as f:
                        json.dump(backtest_result, f, indent=4)
                    
                    logger.info(f"Đã lưu kết quả vào {result_path}")
                    period_results.append(backtest_result)
                    all_results.append(backtest_result)
                else:
                    logger.warning(f"Không có kết quả cho {sym} với rủi ro {risk}% trong khoảng {period['name']}")
            
            # Vẽ biểu đồ so sánh các mức rủi ro cho cặp tiền và khoảng thời gian này
            if period_results:
                create_risk_comparison_chart(period_results, period['name'], sym, interval)
    
    # Tạo báo cáo tổng hợp
    if all_results:
        create_summary_report(all_results, symbol, interval, use_all_symbols)
        
    logger.info("=== KẾT THÚC CHẠY BACKTEST VỚI NHIỀU MỨC ĐỘ RỦI RO ===")

def create_risk_comparison_chart(results, period_name, symbol, interval):
    """
    Tạo biểu đồ so sánh hiệu suất giữa các mức độ rủi ro
    
    Args:
        results (list): Danh sách kết quả
        period_name (str): Tên khoảng thời gian
        symbol (str): Mã cặp tiền
        interval (str): Khung thời gian
    """
    if not results:
        return
    
    # Sắp xếp kết quả theo mức độ rủi ro
    results.sort(key=lambda x: x.get('risk_percentage', 0))
    
    # Trích xuất dữ liệu cho biểu đồ
    risk_levels = [r.get('risk_percentage', 0) for r in results]
    profit_pcts = [r.get('profit_percentage', 0) for r in results]
    win_rates = [r.get('win_rate', 0) for r in results]
    drawdowns = [r.get('max_drawdown', 0) for r in results]
    
    # Vẽ biểu đồ
    plt.figure(figsize=(12, 8))
    
    # Biểu đồ lợi nhuận
    ax1 = plt.subplot(211)
    ax1.plot(risk_levels, profit_pcts, 'go-', linewidth=2, label='Lợi nhuận (%)')
    ax1.set_title(f'So sánh hiệu suất theo mức độ rủi ro - {symbol} {interval} - {period_name}')
    ax1.set_ylabel('Lợi nhuận (%)')
    ax1.legend(loc='upper left')
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Biểu đồ win rate và drawdown
    ax2 = plt.subplot(212, sharex=ax1)
    ax2.plot(risk_levels, win_rates, 'bo-', linewidth=2, label='Win rate (%)')
    ax2.plot(risk_levels, drawdowns, 'ro-', linewidth=2, label='Drawdown (%)')
    ax2.set_xlabel('Mức độ rủi ro (%)')
    ax2.set_ylabel('Phần trăm (%)')
    ax2.legend(loc='upper left')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    chart_filename = f"backtest_charts/risk_comparison_{symbol}_{interval}_{period_name}.png"
    plt.savefig(chart_filename)
    plt.close()
    
    logger.info(f"Đã lưu biểu đồ so sánh vào {chart_filename}")

def create_summary_report(results, symbol, interval, use_all_symbols):
    """
    Tạo báo cáo tổng hợp từ tất cả các kết quả test
    
    Args:
        results (list): Danh sách kết quả
        symbol (str): Mã cặp tiền chính
        interval (str): Khung thời gian
        use_all_symbols (bool): Có sử dụng tất cả các cặp tiền không
    """
    # Tạo DataFrame từ kết quả
    df_results = pd.DataFrame(results)
    
    # Thêm trường Sharpe Ratio (Profit/Drawdown)
    df_results['sharpe_ratio'] = df_results['profit_percentage'] / df_results['max_drawdown'].replace(0, 0.01)
    
    # Báo cáo theo khoảng thời gian
    period_report = df_results.groupby('analysis_period').agg({
        'profit_percentage': ['mean', 'max', 'min', 'std'],
        'win_rate': ['mean', 'max'],
        'max_drawdown': ['mean', 'min'],
        'sharpe_ratio': ['mean', 'max'],
        'risk_percentage': lambda x: list(x.unique())
    }).reset_index()
    
    # Báo cáo theo mức độ rủi ro
    risk_report = df_results.groupby('risk_percentage').agg({
        'profit_percentage': ['mean', 'max', 'min', 'std'],
        'win_rate': ['mean', 'max'],
        'max_drawdown': ['mean', 'min'],
        'sharpe_ratio': ['mean', 'max'],
        'analysis_period': lambda x: list(x.unique())
    }).reset_index()
    
    # Tìm tổ hợp tối ưu
    best_profit = df_results.loc[df_results['profit_percentage'].idxmax()]
    best_win_rate = df_results.loc[df_results['win_rate'].idxmax()]
    best_sharpe = df_results.loc[df_results['sharpe_ratio'].idxmax()]
    lowest_drawdown = df_results.loc[df_results['max_drawdown'].idxmin()]
    
    # Tạo báo cáo JSON
    summary_report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': symbol if not use_all_symbols else 'multiple',
        'interval': interval,
        'total_tests': len(results),
        'period_stats': period_report.to_dict(orient='records'),
        'risk_stats': risk_report.to_dict(orient='records'),
        'optimal_combinations': {
            'best_profit': {
                'period': best_profit['analysis_period'],
                'risk': best_profit['risk_percentage'],
                'profit_percentage': best_profit['profit_percentage'],
                'win_rate': best_profit['win_rate'],
                'max_drawdown': best_profit['max_drawdown']
            },
            'best_win_rate': {
                'period': best_win_rate['analysis_period'],
                'risk': best_win_rate['risk_percentage'],
                'profit_percentage': best_win_rate['profit_percentage'],
                'win_rate': best_win_rate['win_rate'],
                'max_drawdown': best_win_rate['max_drawdown']
            },
            'best_sharpe': {
                'period': best_sharpe['analysis_period'],
                'risk': best_sharpe['risk_percentage'],
                'profit_percentage': best_sharpe['profit_percentage'],
                'win_rate': best_sharpe['win_rate'],
                'max_drawdown': best_sharpe['max_drawdown'],
                'sharpe_ratio': best_sharpe['sharpe_ratio']
            },
            'lowest_drawdown': {
                'period': lowest_drawdown['analysis_period'],
                'risk': lowest_drawdown['risk_percentage'],
                'profit_percentage': lowest_drawdown['profit_percentage'],
                'win_rate': lowest_drawdown['win_rate'],
                'max_drawdown': lowest_drawdown['max_drawdown']
            }
        }
    }
    
    # Lưu báo cáo JSON
    report_filename = f"reports/multi_risk_summary_{symbol}_{interval}.json"
    with open(report_filename, 'w') as f:
        json.dump(summary_report, f, indent=4)
    
    logger.info(f"Đã lưu báo cáo tổng hợp vào {report_filename}")
    
    # Lưu báo cáo dạng văn bản dễ đọc
    txt_filename = f"reports/multi_risk_summary_{symbol}_{interval}.txt"
    with open(txt_filename, 'w') as f:
        f.write(f"BÁO CÁO TỔNG HỢP PHÂN TÍCH NHIỀU MỨC ĐỘ RỦI RO\n")
        f.write(f"Thời gian: {summary_report['timestamp']}\n")
        f.write(f"Cặp tiền: {summary_report['symbol']}\n")
        f.write(f"Khung thời gian: {summary_report['interval']}\n")
        f.write(f"Tổng số test: {summary_report['total_tests']}\n\n")
        
        f.write("THỐNG KÊ THEO KHOẢNG THỜI GIAN\n")
        for period in period_report.to_dict(orient='records'):
            f.write(f"* Khoảng thời gian: {period['analysis_period']}\n")
            f.write(f"  - Lợi nhuận trung bình: {period['profit_percentage']['mean']:.2f}% (±{period['profit_percentage']['std']:.2f}%)\n")
            f.write(f"  - Lợi nhuận cao nhất: {period['profit_percentage']['max']:.2f}%\n")
            f.write(f"  - Win rate trung bình: {period['win_rate']['mean']:.2f}%\n")
            f.write(f"  - Drawdown trung bình: {period['max_drawdown']['mean']:.2f}%\n")
            f.write(f"  - Sharpe ratio trung bình: {period['sharpe_ratio']['mean']:.2f}\n\n")
        
        f.write("THỐNG KÊ THEO MỨC ĐỘ RỦI RO\n")
        for risk in risk_report.to_dict(orient='records'):
            f.write(f"* Mức độ rủi ro: {risk['risk_percentage']:.1f}%\n")
            f.write(f"  - Lợi nhuận trung bình: {risk['profit_percentage']['mean']:.2f}% (±{risk['profit_percentage']['std']:.2f}%)\n")
            f.write(f"  - Lợi nhuận cao nhất: {risk['profit_percentage']['max']:.2f}%\n")
            f.write(f"  - Win rate trung bình: {risk['win_rate']['mean']:.2f}%\n")
            f.write(f"  - Drawdown trung bình: {risk['max_drawdown']['mean']:.2f}%\n")
            f.write(f"  - Sharpe ratio trung bình: {risk['sharpe_ratio']['mean']:.2f}\n\n")
        
        f.write("TỔ HỢP TỐI ƯU\n")
        
        # Tổ hợp có lợi nhuận cao nhất
        bp = summary_report['optimal_combinations']['best_profit']
        f.write(f"* Lợi nhuận cao nhất:\n")
        f.write(f"  - Khoảng thời gian: {bp['period']}\n")
        f.write(f"  - Mức độ rủi ro: {bp['risk']:.1f}%\n")
        f.write(f"  - Lợi nhuận: {bp['profit_percentage']:.2f}%\n")
        f.write(f"  - Win rate: {bp['win_rate']:.2f}%\n")
        f.write(f"  - Drawdown: {bp['max_drawdown']:.2f}%\n\n")
        
        # Tổ hợp có win rate cao nhất
        bw = summary_report['optimal_combinations']['best_win_rate']
        f.write(f"* Win rate cao nhất:\n")
        f.write(f"  - Khoảng thời gian: {bw['period']}\n")
        f.write(f"  - Mức độ rủi ro: {bw['risk']:.1f}%\n")
        f.write(f"  - Lợi nhuận: {bw['profit_percentage']:.2f}%\n")
        f.write(f"  - Win rate: {bw['win_rate']:.2f}%\n")
        f.write(f"  - Drawdown: {bw['max_drawdown']:.2f}%\n\n")
        
        # Tổ hợp có sharpe ratio cao nhất
        bs = summary_report['optimal_combinations']['best_sharpe']
        f.write(f"* Sharpe ratio cao nhất:\n")
        f.write(f"  - Khoảng thời gian: {bs['period']}\n")
        f.write(f"  - Mức độ rủi ro: {bs['risk']:.1f}%\n")
        f.write(f"  - Lợi nhuận: {bs['profit_percentage']:.2f}%\n")
        f.write(f"  - Win rate: {bs['win_rate']:.2f}%\n")
        f.write(f"  - Drawdown: {bs['max_drawdown']:.2f}%\n")
        f.write(f"  - Sharpe ratio: {bs['sharpe_ratio']:.2f}\n\n")
        
        # Tổ hợp có drawdown thấp nhất
        ld = summary_report['optimal_combinations']['lowest_drawdown']
        f.write(f"* Drawdown thấp nhất:\n")
        f.write(f"  - Khoảng thời gian: {ld['period']}\n")
        f.write(f"  - Mức độ rủi ro: {ld['risk']:.1f}%\n")
        f.write(f"  - Lợi nhuận: {ld['profit_percentage']:.2f}%\n")
        f.write(f"  - Win rate: {ld['win_rate']:.2f}%\n")
        f.write(f"  - Drawdown: {ld['max_drawdown']:.2f}%\n\n")
    
    logger.info(f"Đã lưu báo cáo tổng hợp dạng văn bản vào {txt_filename}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Chạy backtest với nhiều mức độ rủi ro')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Mã cặp giao dịch')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian')
    parser.add_argument('--all-symbols', action='store_true', help='Sử dụng tất cả các cặp tiền có sẵn')
    
    args = parser.parse_args()
    
    run_multi_risk_test(
        symbol=args.symbol,
        interval=args.interval,
        use_all_symbols=args.all_symbols
    )

if __name__ == "__main__":
    main()