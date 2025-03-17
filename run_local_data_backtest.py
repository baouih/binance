#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module chạy backtest với dữ liệu lịch sử local

Script này sẽ:
1. Tìm các tập tin dữ liệu lịch sử đã tải 
2. Chạy backtest với dữ liệu local 
3. Xuất báo cáo backtest chi tiết
"""

import os
import sys
import json
import glob
import logging
import argparse
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any, Optional, Union

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('local_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('local_backtest')

def parse_arguments():
    """Xử lý tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Chạy backtest với dữ liệu lịch sử local")
    parser.add_argument("--config", help="Đường dẫn đến tập tin cấu hình", default="comprehensive_backtest_config.json")
    parser.add_argument("--data-dir", help="Thư mục chứa dữ liệu lịch sử", default="data")
    parser.add_argument("--output-dir", help="Thư mục lưu kết quả backtest", default="backtest_results")
    parser.add_argument("--risk-level", help="Mức độ rủi ro (low/medium/high)", default="medium")
    parser.add_argument("--start", help="Ngày bắt đầu (YYYY-MM-DD)", default="2024-02-01")
    parser.add_argument("--end", help="Ngày kết thúc (YYYY-MM-DD)", default="2024-03-15")
    parser.add_argument("--symbols", help="Chỉ chạy backtest với những symbols này (phân tách bằng dấu phẩy)", default="")
    
    return parser.parse_args()

def load_config(config_path='comprehensive_backtest_config.json'):
    """Tải tập tin cấu hình"""
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
            logger.info(f"Đã tải cấu hình từ {config_path}")
            return config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {e}")
        sys.exit(1)

def find_data_files(data_dir, symbols, timeframes):
    """Tìm các tập tin dữ liệu lịch sử theo symbols và timeframes"""
    data_files = {}
    
    for symbol in symbols:
        data_files[symbol] = {}
        
        for timeframe in timeframes:
            # Tìm tất cả các file khớp với pattern
            pattern = os.path.join(data_dir, f"{symbol}_{timeframe}_*.csv")
            files = glob.glob(pattern)
            
            if files:
                # Sắp xếp theo thời gian tạo file (mới nhất trước)
                files.sort(key=os.path.getmtime, reverse=True)
                data_files[symbol][timeframe] = files[0]  # Lấy file mới nhất
                logger.info(f"Đã tìm thấy file dữ liệu cho {symbol} ({timeframe}): {os.path.basename(files[0])}")
            else:
                logger.warning(f"Không tìm thấy file dữ liệu cho {symbol} ({timeframe})")
                data_files[symbol][timeframe] = None
    
    return data_files

def load_historical_data(file_path, start_date=None, end_date=None):
    """Tải dữ liệu lịch sử từ file CSV"""
    if not file_path or not os.path.exists(file_path):
        logger.error(f"File không tồn tại: {file_path}")
        return None
    
    try:
        # Đọc dữ liệu từ CSV
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        # Lọc theo khoảng thời gian
        if start_date:
            df = df[df.index >= start_date]
        
        if end_date:
            df = df[df.index <= end_date]
        
        if df.empty:
            logger.warning(f"Không có dữ liệu trong khoảng thời gian chỉ định cho {file_path}")
            return None
        
        logger.info(f"Đã tải dữ liệu từ {file_path}: {len(df)} dòng")
        return df
    
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu từ {file_path}: {e}")
        return None

def prepare_backtest_data(data_files, start_date, end_date):
    """Chuẩn bị dữ liệu cho backtest"""
    data = {}
    
    for symbol in data_files:
        data[symbol] = {}
        
        for timeframe in data_files[symbol]:
            file_path = data_files[symbol][timeframe]
            
            if file_path:
                df = load_historical_data(file_path, start_date, end_date)
                if df is not None:
                    data[symbol][timeframe] = df
    
    return data

def run_backtest(data, config, risk_level, output_dir):
    """Chạy backtest với dữ liệu đã chuẩn bị"""
    try:
        from comprehensive_backtest import ComprehensiveBacktester
        
        # Kiểm tra xem thư mục đầu ra tồn tại chưa
        os.makedirs(output_dir, exist_ok=True)
        
        # Chuyển đổi risk_level thành cấu hình risk
        risk_config = {
            "low": {"risk_percentage": 1.0, "max_positions": 3},
            "medium": {"risk_percentage": 2.0, "max_positions": 5},
            "high": {"risk_percentage": 5.0, "max_positions": 7}
        }
        
        # Lấy cấu hình risk tương ứng
        risk = risk_config.get(risk_level, risk_config["medium"])
        
        # Khởi tạo backtest
        logger.info(f"Khởi tạo backtest với mức độ rủi ro: {risk_level} "
                   f"(risk_percentage={risk['risk_percentage']}%, "
                   f"max_positions={risk['max_positions']})")
        
        results = {}
        
        # Chạy backtest cho từng symbol
        for symbol in data:
            if not data[symbol]:
                logger.warning(f"Không có dữ liệu cho {symbol}, bỏ qua")
                continue
            
            # Kiểm tra xem có đủ dữ liệu cho tất cả timeframes
            has_all_timeframes = all(tf in data[symbol] for tf in config["timeframes"])
            
            if not has_all_timeframes:
                logger.warning(f"Thiếu dữ liệu cho một số timeframes của {symbol}, bỏ qua")
                continue
            
            logger.info(f"Chạy backtest cho {symbol}...")
            
            # Khởi tạo backtest cho symbol này
            backtest_config = {
                "symbol": symbol,
                "timeframes": config["timeframes"],
                "risk_percentage": risk["risk_percentage"],
                "max_positions": risk["max_positions"],
                "initial_balance": 10000.0,
                "leverage": 10,
                "strategies": config["strategies"],
                "use_market_regime": True,
                "use_trailing_stop": True
            }
            
            # Tạo backtest instance
            backtester = ComprehensiveBacktester(backtest_config)
            
            # Chạy backtest với dữ liệu đã chuẩn bị
            symbol_result = backtester.run_with_data(data[symbol])
            
            if symbol_result:
                results[symbol] = symbol_result
                
                # Lưu kết quả backtest
                result_file = os.path.join(output_dir, f"{symbol}_{risk_level}_risk_backtest.json")
                with open(result_file, 'w') as f:
                    json.dump(symbol_result, f, indent=4)
                
                logger.info(f"Đã lưu kết quả backtest cho {symbol} vào {result_file}")
                
                # Tạo báo cáo chi tiết
                report_file = os.path.join(output_dir, f"{symbol}_{risk_level}_risk_backtest_report.txt")
                create_backtest_report(symbol, symbol_result, report_file, risk_level)
            else:
                logger.error(f"Không có kết quả backtest cho {symbol}")
        
        return results
    
    except ImportError as e:
        logger.error(f"Lỗi import module: {e}")
        return None
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest: {e}", exc_info=True)
        return None

def create_backtest_report(symbol, result, report_file, risk_level):
    """Tạo báo cáo chi tiết từ kết quả backtest"""
    try:
        with open(report_file, 'w') as f:
            f.write(f"===== BÁO CÁO BACKTEST {symbol} - CHIẾN LƯỢC RỦI RO {risk_level.upper()} =====\n\n")
            f.write(f"Ngày thực hiện: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Symbol: {symbol}\n")
            
            # Thông tin cấu hình
            if "config" in result:
                f.write(f"Số ngày backtest: {result.get('test_days', 'N/A')}\n")
                f.write(f"Khung thời gian: {result['config'].get('timeframe', 'multiple')}\n")
                f.write(f"Rủi ro mỗi lệnh: {result['config'].get('risk_percentage', 'N/A')}%\n")
                f.write(f"Đòn bẩy: {result['config'].get('leverage', 'N/A')}x\n")
            
            f.write("\n")
            
            # Thông tin kết quả
            f.write(f"Số dư ban đầu: {result.get('initial_balance', 'N/A')} USDT\n")
            f.write(f"Số dư cuối: {result.get('final_balance', 'N/A')} USDT\n")
            
            profit = result.get('final_balance', 0) - result.get('initial_balance', 0)
            profit_pct = profit / result.get('initial_balance', 1) * 100
            
            f.write(f"Lợi nhuận: {profit:.2f} USDT ({profit_pct:.2f}%)\n")
            f.write(f"Drawdown tối đa: {result.get('max_drawdown_pct', 'N/A')}%\n")
            
            total_trades = result.get('total_trades', 0)
            win_trades = result.get('winning_trades', 0)
            lose_trades = result.get('losing_trades', 0)
            
            f.write(f"Số lệnh: {total_trades}\n")
            
            if total_trades > 0:
                win_rate = win_trades / total_trades * 100
                f.write(f"Tỷ lệ thắng: {win_rate:.2f}%\n")
                
                avg_win = result.get('avg_win_pct', 0)
                avg_loss = result.get('avg_loss_pct', 0)
                
                f.write(f"Trung bình lãi mỗi lệnh thắng: {avg_win:.2f}%\n")
                f.write(f"Trung bình lỗ mỗi lệnh thua: {avg_loss:.2f}%\n")
                
                if lose_trades > 0:
                    profit_factor = abs(win_trades * avg_win / (lose_trades * avg_loss)) if lose_trades * avg_loss != 0 else float('inf')
                    f.write(f"Profit Factor: {profit_factor:.2f}\n")
            
            f.write("\nDANH SÁCH GIAO DỊCH:\n")
            
            # Chi tiết giao dịch
            if "trades" in result:
                for i, trade in enumerate(result["trades"]):
                    entry_time = trade.get('entry_time', 'N/A')
                    exit_time = trade.get('exit_time', 'N/A')
                    entry_price = trade.get('entry_price', 0)
                    exit_price = trade.get('exit_price', 0)
                    pnl_pct = trade.get('pnl_pct', 0)
                    
                    direction = "LONG" if trade.get('direction', '').lower() == 'long' else "SHORT"
                    result_text = "THẮNG" if pnl_pct > 0 else "THUA"
                    
                    f.write(f"{i+1}. {direction} {entry_time} -> {exit_time}, "
                           f"Giá vào: {entry_price:.2f}, Giá ra: {exit_price:.2f}, "
                           f"P/L: {pnl_pct:.2f}%, Kết quả: {result_text}\n")
        
        logger.info(f"Đã tạo báo cáo chi tiết: {report_file}")
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo: {e}")

def main():
    """Hàm chính"""
    # Xử lý tham số
    args = parse_arguments()
    
    # Tải cấu hình
    config = load_config(args.config)
    
    # Lấy danh sách symbols và timeframes
    all_symbols = config.get('symbols', [])
    timeframes = config.get('timeframes', [])
    
    # Nếu có chỉ định symbols cụ thể
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
        # Chỉ giữ lại các symbols hợp lệ
        symbols = [s for s in symbols if s in all_symbols]
        logger.info(f"Chỉ chạy backtest cho các symbols được chỉ định: {', '.join(symbols)}")
    else:
        symbols = all_symbols
    
    if not symbols:
        logger.error("Không tìm thấy danh sách symbols trong cấu hình. Dừng.")
        return 1
    
    if not timeframes:
        logger.error("Không tìm thấy danh sách timeframes trong cấu hình. Dừng.")
        return 1
    
    logger.info(f"Chuẩn bị chạy backtest cho {len(symbols)} symbols và {len(timeframes)} timeframes")
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Timeframes: {', '.join(timeframes)}")
    logger.info(f"Khoảng thời gian: {args.start} đến {args.end}")
    logger.info(f"Mức độ rủi ro: {args.risk_level}")
    
    # Tìm các tập tin dữ liệu lịch sử
    data_files = find_data_files(args.data_dir, symbols, timeframes)
    
    # Kiểm tra xem có đủ dữ liệu hay không
    missing_data = []
    for symbol in data_files:
        for timeframe in data_files[symbol]:
            if not data_files[symbol][timeframe]:
                missing_data.append(f"{symbol}_{timeframe}")
    
    if missing_data:
        logger.warning(f"Thiếu dữ liệu cho: {', '.join(missing_data)}")
        logger.info("Tiếp tục backtest với dữ liệu đã có")
    
    # Chuẩn bị dữ liệu cho backtest
    data = prepare_backtest_data(data_files, args.start, args.end)
    
    # Chạy backtest
    results = run_backtest(data, config, args.risk_level, args.output_dir)
    
    if not results:
        logger.error("Không có kết quả backtest.")
        return 1
    
    # Tổng kết
    logger.info("=== KẾT QUẢ BACKTEST ===")
    logger.info(f"Đã chạy backtest cho {len(results)} symbols")
    logger.info(f"Kết quả đã được lưu vào thư mục: {args.output_dir}")
    
    # Tạo báo cáo tổng hợp
    summary_file = os.path.join(args.output_dir, f"backtest_summary_{args.risk_level}.json")
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=4)
    
    logger.info(f"Đã lưu báo cáo tổng hợp vào {summary_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())