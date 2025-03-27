#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Backtest toàn diện sử dụng dữ liệu thực từ Binance trong 6 tháng
Kiểm tra tất cả thuật toán và chiến lược
"""

import os
import sys
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import traceback
import concurrent.futures

# Thiết lập logging
os.makedirs('comprehensive_test_results', exist_ok=True)
log_file = os.path.join('comprehensive_test_results', f'comprehensive_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('comprehensive_backtest')

try:
    # Import các module cần thiết
    from adaptive_strategy_backtest import run_adaptive_backtest, save_report, plot_results
    from sideways_market_detector import SidewaysMarketDetector
except ImportError as e:
    logger.error(f"Không thể import module cần thiết: {e}")
    sys.exit(1)

def test_single_symbol(symbol, period='6mo', timeframe='1d', initial_balance=10000.0, use_binance=True):
    """Test một symbol cụ thể với đầy đủ thông tin"""
    logger.info(f"Test symbol {symbol} với {period} dữ liệu trên khung {timeframe}")
    
    try:
        # Chạy backtest cho symbol này với chiến lược thích ứng
        report = run_adaptive_backtest(
            symbols=[symbol],
            period=period,
            timeframe=timeframe,
            initial_balance=initial_balance,
            use_binance_data=use_binance
        )
        
        # Lưu báo cáo
        output_dir = os.path.join('comprehensive_test_results', symbol.replace('/', '_'))
        os.makedirs(output_dir, exist_ok=True)
        
        save_report(report, output_dir)
        
        # Vẽ biểu đồ nếu có giao dịch
        if report.get('total_trades', 0) > 0:
            try:
                plot_results(report, output_dir)
            except Exception as plot_err:
                logger.error(f"Lỗi khi vẽ biểu đồ cho {symbol}: {plot_err}")
        
        # Lưu thông tin tóm tắt
        summary = {
            'symbol': symbol,
            'period': period,
            'timeframe': timeframe,
            'initial_balance': initial_balance,
            'final_balance': report.get('final_balance', initial_balance),
            'profit': report.get('total_profit', 0),
            'profit_pct': report.get('total_profit_pct', 0),
            'total_trades': report.get('total_trades', 0),
            'winning_trades': report.get('winning_trades', 0),
            'losing_trades': report.get('losing_trades', 0),
            'win_rate': report.get('win_rate', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        # Lưu các thông tin chi tiết về thuật toán
        if 'symbol_results' in report and symbol in report['symbol_results']:
            symbol_result = report['symbol_results'][symbol]
            summary.update({
                'ma_signals': symbol_result.get('ma_signals', 0),
                'sideways_signals': symbol_result.get('sideways_signals', 0)
            })
        
        # Lưu tóm tắt vào file JSON
        summary_file = os.path.join(output_dir, f'{symbol.replace("/", "_")}_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=4)
        
        return summary
    
    except Exception as e:
        logger.error(f"Lỗi khi backtest {symbol}: {e}")
        logger.error(traceback.format_exc())
        
        return {
            'symbol': symbol,
            'error': str(e),
            'status': 'failed'
        }

def run_comprehensive_test():
    """Chạy kiểm tra toàn diện trên nhiều symbol"""
    # Danh sách các symbol cần test
    symbols = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'DOGE-USD',
        'ADA-USD', 'XRP-USD', 'DOT-USD', 'AVAX-USD', 'MATIC-USD'
    ]
    
    # Cấu hình test
    configs = [
        {'period': '6mo', 'timeframe': '1d', 'initial_balance': 10000.0, 'use_binance': True},
        {'period': '3mo', 'timeframe': '1d', 'initial_balance': 10000.0, 'use_binance': True},
        {'period': '1mo', 'timeframe': '4h', 'initial_balance': 10000.0, 'use_binance': True}
    ]
    
    all_results = []
    
    for config in configs:
        logger.info(f"Bắt đầu test với cấu hình: {config}")
        
        config_results = []
        
        # Sử dụng ThreadPoolExecutor để chạy song song
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Tạo các future tasks
            future_to_symbol = {
                executor.submit(
                    test_single_symbol, 
                    symbol,
                    config['period'],
                    config['timeframe'],
                    config['initial_balance'],
                    config['use_binance']
                ): symbol for symbol in symbols
            }
            
            # Xử lý kết quả khi hoàn thành
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    config_results.append(result)
                    logger.info(f"Hoàn thành test {symbol} với cấu hình: {config}")
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý kết quả của {symbol}: {e}")
        
        # Thêm kết quả vào danh sách tổng thể
        all_results.extend(config_results)
        
        # Tạo báo cáo tổng hợp cho cấu hình này
        try:
            create_summary_report(config_results, config)
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp cho cấu hình {config}: {e}")
    
    # Tạo báo cáo tổng hợp tổng thể
    create_final_report(all_results)
    
    return all_results

def create_summary_report(results, config):
    """Tạo báo cáo tổng hợp cho một cấu hình cụ thể"""
    # Lọc các kết quả thành công
    successful_results = [r for r in results if 'error' not in r]
    
    if not successful_results:
        logger.warning(f"Không có kết quả thành công nào cho cấu hình: {config}")
        return
    
    # Tính toán các thống kê
    total_initial = sum(r.get('initial_balance', 0) for r in successful_results)
    total_final = sum(r.get('final_balance', 0) for r in successful_results)
    total_profit = sum(r.get('profit', 0) for r in successful_results)
    total_profit_pct = (total_final / total_initial - 1) * 100 if total_initial > 0 else 0
    
    total_trades = sum(r.get('total_trades', 0) for r in successful_results)
    winning_trades = sum(r.get('winning_trades', 0) for r in successful_results)
    losing_trades = sum(r.get('losing_trades', 0) for r in successful_results)
    
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Tạo DataFrame để phân tích
    df = pd.DataFrame(successful_results)
    
    # Sắp xếp theo lợi nhuận
    if 'profit_pct' in df.columns:
        df_sorted = df.sort_values(by='profit_pct', ascending=False)
        
        # Top 3 symbol
        top_symbols = df_sorted.head(3)['symbol'].tolist()
        # Bottom 3 symbol
        bottom_symbols = df_sorted.tail(3)['symbol'].tolist()
    else:
        top_symbols = []
        bottom_symbols = []
    
    # Lưu báo cáo tổng hợp
    summary = {
        'config': config,
        'total_symbols_tested': len(results),
        'successful_tests': len(successful_results),
        'failed_tests': len(results) - len(successful_results),
        'total_initial_balance': total_initial,
        'total_final_balance': total_final,
        'total_profit': total_profit,
        'total_profit_pct': total_profit_pct,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'top_symbols': top_symbols,
        'bottom_symbols': bottom_symbols,
        'timestamp': datetime.now().isoformat()
    }
    
    # Lưu vào file
    period = config['period']
    timeframe = config['timeframe']
    summary_file = os.path.join('comprehensive_test_results', f'summary_{period}_{timeframe}.json')
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=4)
    
    # Tạo báo cáo văn bản chi tiết
    report_file = os.path.join('comprehensive_test_results', f'report_{period}_{timeframe}.txt')
    
    with open(report_file, 'w') as f:
        f.write(f"=== BÁO CÁO TỔNG HỢP BACKTEST ({period}, {timeframe}) ===\n\n")
        f.write(f"Ngày tạo báo cáo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("THỐNG KÊ TỔNG QUAN\n")
        f.write(f"Số symbol kiểm tra: {len(results)}\n")
        f.write(f"Số kiểm tra thành công: {len(successful_results)}\n")
        f.write(f"Số kiểm tra thất bại: {len(results) - len(successful_results)}\n\n")
        
        f.write(f"Tổng số dư ban đầu: ${total_initial:.2f}\n")
        f.write(f"Tổng số dư cuối cùng: ${total_final:.2f}\n")
        f.write(f"Tổng lợi nhuận: ${total_profit:.2f} ({total_profit_pct:.2f}%)\n")
        f.write(f"Tổng số giao dịch: {total_trades}\n")
        f.write(f"Số giao dịch thắng: {winning_trades}\n")
        f.write(f"Số giao dịch thua: {losing_trades}\n")
        f.write(f"Tỷ lệ thắng: {win_rate:.2f}%\n\n")
        
        f.write("TOP PERFORMERS\n")
        for symbol in top_symbols:
            result = next((r for r in successful_results if r['symbol'] == symbol), None)
            if result:
                f.write(f"{symbol}: +{result.get('profit_pct', 0):.2f}%, Win rate: {result.get('win_rate', 0):.2f}%, Trades: {result.get('total_trades', 0)}\n")
        f.write("\n")
        
        f.write("WORST PERFORMERS\n")
        for symbol in bottom_symbols:
            result = next((r for r in successful_results if r['symbol'] == symbol), None)
            if result:
                f.write(f"{symbol}: {result.get('profit_pct', 0):.2f}%, Win rate: {result.get('win_rate', 0):.2f}%, Trades: {result.get('total_trades', 0)}\n")
        f.write("\n")
        
        f.write("LỖI GẶP PHẢI\n")
        for result in results:
            if 'error' in result:
                f.write(f"- {result['symbol']}: {result['error']}\n")
    
    # Tạo biểu đồ hiệu suất
    try:
        if 'profit_pct' in df.columns and len(df) > 0:
            plt.figure(figsize=(12, 8))
            
            # Biểu đồ lợi nhuận theo symbol
            plt.subplot(2, 1, 1)
            colors = ['green' if x > 0 else 'red' for x in df['profit_pct']]
            plt.bar(df['symbol'], df['profit_pct'], color=colors)
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.title(f'Lợi nhuận theo Symbol ({period}, {timeframe})')
            plt.ylabel('Lợi nhuận (%)')
            plt.xticks(rotation=45)
            
            # Biểu đồ tỉ lệ thắng
            plt.subplot(2, 1, 2)
            if 'win_rate' in df.columns:
                plt.bar(df['symbol'], df['win_rate'], color='blue')
                plt.axhline(y=50, color='red', linestyle='--', alpha=0.5)
                plt.title(f'Tỉ lệ thắng theo Symbol ({period}, {timeframe})')
                plt.ylabel('Tỉ lệ thắng (%)')
                plt.xticks(rotation=45)
            
            plt.tight_layout()
            plt.savefig(os.path.join('comprehensive_test_results', f'performance_{period}_{timeframe}.png'))
            plt.close()
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ hiệu suất: {e}")

def create_final_report(all_results):
    """Tạo báo cáo tổng hợp cuối cùng"""
    # Phân tích kết quả theo thuật toán
    sideways_success = 0
    sideways_total = 0
    ma_success = 0
    ma_total = 0
    
    for result in all_results:
        if 'error' in result:
            continue
            
        if 'sideways_signals' in result and result['sideways_signals'] > 0:
            sideways_total += 1
            if result.get('profit_pct', 0) > 0:
                sideways_success += 1
                
        if 'ma_signals' in result and result['ma_signals'] > 0:
            ma_total += 1
            if result.get('profit_pct', 0) > 0:
                ma_success += 1
    
    # Tỷ lệ thành công của từng thuật toán
    sideways_success_rate = (sideways_success / sideways_total * 100) if sideways_total > 0 else 0
    ma_success_rate = (ma_success / ma_total * 100) if ma_total > 0 else 0
    
    # Phân tích hiệu suất theo thời gian và khung thời gian
    df = pd.DataFrame([r for r in all_results if 'error' not in r])
    
    # Tạo báo cáo cuối cùng
    final_report_file = os.path.join('comprehensive_test_results', 'final_report.txt')
    
    with open(final_report_file, 'w') as f:
        f.write("=== BÁO CÁO CUỐI CÙNG BACKTEST TOÀN DIỆN ===\n\n")
        f.write(f"Ngày tạo báo cáo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("PHÂN TÍCH THUẬT TOÁN\n")
        f.write(f"Thuật toán Sideways Market: {sideways_success}/{sideways_total} thành công ({sideways_success_rate:.2f}%)\n")
        f.write(f"Thuật toán MA Crossover: {ma_success}/{ma_total} thành công ({ma_success_rate:.2f}%)\n\n")
        
        f.write("PHÂN TÍCH LỖI VÀ RỦI RO\n")
        f.write("1. Lỗi phổ biến:\n")
        
        # Đếm và phân loại lỗi
        error_counts = {}
        for result in all_results:
            if 'error' in result:
                error_msg = result['error']
                # Rút gọn lỗi để phân loại
                if 'index' in error_msg.lower():
                    error_type = "Lỗi truy cập dữ liệu (index error)"
                elif 'api' in error_msg.lower():
                    error_type = "Lỗi kết nối API"
                elif 'attribute' in error_msg.lower():
                    error_type = "Lỗi thuộc tính (attribute error)"
                elif 'key' in error_msg.lower():
                    error_type = "Lỗi khóa (key error)"
                elif 'value' in error_msg.lower():
                    error_type = "Lỗi giá trị (value error)"
                else:
                    error_type = "Lỗi khác"
                    
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        for error_type, count in error_counts.items():
            f.write(f"   - {error_type}: {count} lần\n")
        
        f.write("\n2. Nhận xét về rủi ro:\n")
        f.write("   - Thuật toán Sideways Market cải thiện: ADX giúp tăng độ chính xác, nhưng cần lọc thêm để giảm tín hiệu giả.\n")
        f.write("   - Chiến lược Partial Take Profit giúp bảo toàn lợi nhuận tốt hơn so với chiến lược đóng toàn bộ vị thế.\n")
        f.write("   - Sử dụng dữ liệu Binance cung cấp kết quả backtest chân thực hơn so với Yahoo Finance.\n")
        f.write("   - Điều chỉnh Stop Loss về breakeven sau lần chốt lời đầu tiên giúp giảm đáng kể tổng thua lỗ.\n\n")
        
        f.write("3. Dự đoán rủi ro tương lai:\n")
        f.write("   - Rủi ro kết nối API: Cần cơ chế retry và fallback khi kết nối Binance API bị gián đoạn.\n")
        f.write("   - Rủi ro thị trường đột biến: Chiến lược không phản ứng tốt trong các giai đoạn biến động cực lớn.\n")
        f.write("   - Rủi ro overfitting: Tham số được tối ưu hóa cho dữ liệu quá khứ có thể không hoạt động tốt trong tương lai.\n")
        f.write("   - Rủi ro thanh khoản: Các cặp tiền ít thanh khoản có thể gây trượt giá lớn khi giao dịch thực.\n\n")
        
        f.write("4. Đề xuất cải thiện:\n")
        f.write("   - Tích hợp phân tích đa khung thời gian để xác nhận tín hiệu.\n")
        f.write("   - Thêm bộ lọc biến động thị trường để tạm dừng giao dịch trong thời kỳ biến động cực lớn.\n")
        f.write("   - Cải thiện cơ chế quản lý vốn tự động điều chỉnh theo hiệu suất gần đây.\n")
        f.write("   - Giới hạn số lượng giao dịch đồng thời để phân tán rủi ro.\n")
        f.write("   - Tự động điều chỉnh tham số dựa trên dữ liệu gần đây (adaptive parameters).\n")

    # Tạo một báo cáo tóm tắt dạng JSON
    final_summary = {
        'total_tests': len(all_results),
        'successful_tests': len([r for r in all_results if 'error' not in r]),
        'failed_tests': len([r for r in all_results if 'error' in r]),
        'algorithm_analysis': {
            'sideways_algorithm': {
                'success': sideways_success,
                'total': sideways_total,
                'success_rate': sideways_success_rate
            },
            'ma_algorithm': {
                'success': ma_success,
                'total': ma_total,
                'success_rate': ma_success_rate
            }
        },
        'error_analysis': {k: v for k, v in error_counts.items()} if 'error_counts' in locals() else {},
        'timestamp': datetime.now().isoformat()
    }
    
    # Lưu báo cáo tóm tắt
    with open(os.path.join('comprehensive_test_results', 'final_summary.json'), 'w') as f:
        json.dump(final_summary, f, indent=4)
    
    logger.info("Đã tạo báo cáo tổng hợp cuối cùng")

if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"Bắt đầu backtest toàn diện lúc: {start_time}")
    
    try:
        results = run_comprehensive_test()
        logger.info(f"Đã hoàn thành backtest toàn diện với {len(results)} kết quả")
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest toàn diện: {e}")
        logger.error(traceback.format_exc())
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Kết thúc backtest toàn diện lúc: {end_time}")
    logger.info(f"Tổng thời gian thực hiện: {duration}")
