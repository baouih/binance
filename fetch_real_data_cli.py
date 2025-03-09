#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command Line Interface cho việc tải dữ liệu thực tế từ Binance

Script này cung cấp một giao diện dòng lệnh tương tác để tải dữ liệu giá từ Binance API.
Người dùng có thể lựa chọn các cặp tiền, khung thời gian và thời gian trong giao diện menu đơn giản.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
try:
    import pandas as pd
    from binance.client import Client
    from tqdm import tqdm
    from dotenv import load_dotenv
except ImportError:
    print("Thiếu các thư viện cần thiết. Đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "python-binance", "tqdm", "python-dotenv"])
    import pandas as pd
    from binance.client import Client
    from tqdm import tqdm
    from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fetch_real_data_cli.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('fetch_real_data_cli')

# Tải biến môi trường
load_dotenv()
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Sử dụng API keys trong account config nếu có
try:
    with open('account_config.json', 'r') as f:
        account_config = json.load(f)
        if not API_KEY and account_config.get('api_key'):
            API_KEY = account_config.get('api_key')
        if not API_SECRET and account_config.get('api_secret'):
            API_SECRET = account_config.get('api_secret')
except (FileNotFoundError, json.JSONDecodeError):
    pass

# Định nghĩa các mục menu
MAIN_MENU = """
===== MENU TẢI DỮ LIỆU BINANCE =====
1. Tải dữ liệu cho một cặp tiền cụ thể
2. Tải dữ liệu cho nhiều cặp tiền
3. Tải dữ liệu từ cấu hình backtest
4. Tải dữ liệu mẫu cho demo
5. Kiểm tra dữ liệu đã tải
6. Thoát
Chọn một tùy chọn (1-6): """

def get_binance_client():
    """Tạo và trả về một client Binance"""
    try:
        client = Client(API_KEY, API_SECRET)
        # Kiểm tra kết nối
        server_time = client.get_server_time()
        logger.info(f"Đã kết nối đến Binance. Server time: {datetime.fromtimestamp(server_time['serverTime']/1000)}")
        return client
    except Exception as e:
        logger.error(f"Lỗi kết nối đến Binance: {str(e)}")
        return None

def get_historical_klines(client, symbol, interval, start_str, end_str=None):
    """Lấy dữ liệu lịch sử từ Binance"""
    try:
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_str,
            end_str=end_str
        )
        return klines
    except Exception as e:
        logger.error(f"Lỗi lấy dữ liệu lịch sử cho {symbol} {interval}: {str(e)}")
        return []

def klines_to_dataframe(klines):
    """Chuyển đổi dữ liệu klines sang DataFrame"""
    columns = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ]
    df = pd.DataFrame(klines, columns=columns)
    
    # Chuyển đổi kiểu dữ liệu
    numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                      'quote_asset_volume', 'number_of_trades',
                      'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
    
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col])
    
    # Chuyển đổi timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    return df

def save_to_csv(df, symbol, interval, output_dir='data'):
    """Lưu DataFrame vào file CSV"""
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = f"{output_dir}/{symbol}_{interval}.csv"
    df.to_csv(file_path, index=False)
    logger.info(f"Đã lưu {len(df)} dòng dữ liệu vào {file_path}")
    return file_path

def fetch_single_pair(client, symbol, interval, start_date, end_date, output_dir, retry_count=3):
    """Lấy dữ liệu cho một cặp tiền và khung thời gian cụ thể"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Đang lấy dữ liệu {symbol} {interval} từ {start_date} đến {end_date}...")
    
    for attempt in range(retry_count):
        try:
            klines = get_historical_klines(
                client=client,
                symbol=symbol,
                interval=interval,
                start_str=start_date,
                end_str=end_date
            )
            
            if klines:
                df = klines_to_dataframe(klines)
                file_path = save_to_csv(df, symbol, interval, output_dir)
                
                result = {
                    "file_path": file_path,
                    "candles": len(df),
                    "start_date": df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
                    "end_date": df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                print(f"✅ Đã tải thành công {len(df)} nến cho {symbol} {interval}")
                return result, len(df)
            
            print(f"⚠️ Thử lại lần {attempt+1}/{retry_count}...")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu {symbol} {interval}: {str(e)}")
            print(f"❌ Lỗi: {str(e)}")
            print(f"⚠️ Thử lại lần {attempt+1}/{retry_count}...")
            time.sleep(5)
    
    print(f"❌ Không thể tải dữ liệu cho {symbol} {interval} sau {retry_count} lần thử")
    return None, 0

def select_symbol():
    """Chọn cặp tiền"""
    popular_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
    
    print("\n===== CHỌN CẶP TIỀN =====")
    print("Các cặp phổ biến:")
    for i, symbol in enumerate(popular_symbols, 1):
        print(f"{i}. {symbol}")
    print(f"{len(popular_symbols)+1}. Nhập cặp tiền khác")
    
    choice = int(input(f"Chọn một tùy chọn (1-{len(popular_symbols)+1}): "))
    
    if 1 <= choice <= len(popular_symbols):
        return popular_symbols[choice-1]
    else:
        return input("Nhập mã cặp tiền (ví dụ: BTCUSDT): ").upper()

def select_interval():
    """Chọn khung thời gian"""
    intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    
    print("\n===== CHỌN KHUNG THỜI GIAN =====")
    for i, interval in enumerate(intervals, 1):
        print(f"{i}. {interval}")
    
    choice = int(input(f"Chọn một tùy chọn (1-{len(intervals)}): "))
    
    if 1 <= choice <= len(intervals):
        return intervals[choice-1]
    else:
        return '1h'  # Mặc định

def select_time_range():
    """Chọn khoảng thời gian"""
    now = datetime.now()
    time_ranges = {
        '1 tuần gần đây': (now - timedelta(days=7)).strftime('%Y-%m-%d'),
        '1 tháng gần đây': (now - timedelta(days=30)).strftime('%Y-%m-%d'),
        '3 tháng gần đây': (now - timedelta(days=90)).strftime('%Y-%m-%d'),
        '6 tháng gần đây': (now - timedelta(days=180)).strftime('%Y-%m-%d'),
        '1 năm gần đây': (now - timedelta(days=365)).strftime('%Y-%m-%d'),
        'Tùy chỉnh': 'custom'
    }
    
    print("\n===== CHỌN KHOẢNG THỜI GIAN =====")
    options = list(time_ranges.keys())
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    
    choice = int(input(f"Chọn một tùy chọn (1-{len(options)}): "))
    
    if 1 <= choice <= len(options):
        option = options[choice-1]
        start_date = time_ranges[option]
        
        if start_date == 'custom':
            print("\nNhập thời gian tùy chỉnh (định dạng: YYYY-MM-DD)")
            start_date = input("Thời gian bắt đầu: ")
            end_date = input("Thời gian kết thúc (Enter để sử dụng thời gian hiện tại): ")
            if not end_date:
                end_date = now.strftime('%Y-%m-%d')
        else:
            end_date = now.strftime('%Y-%m-%d')
        
        return start_date, end_date
    else:
        # Mặc định: 1 tháng gần đây
        return (now - timedelta(days=30)).strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')

def select_output_dir():
    """Chọn thư mục đầu ra"""
    default_dirs = ['test_data', 'real_data', 'backtest_data', 'data']
    
    print("\n===== CHỌN THƯ MỤC ĐẦU RA =====")
    for i, dir_name in enumerate(default_dirs, 1):
        print(f"{i}. {dir_name}")
    print(f"{len(default_dirs)+1}. Nhập thư mục khác")
    
    choice = int(input(f"Chọn một tùy chọn (1-{len(default_dirs)+1}): "))
    
    if 1 <= choice <= len(default_dirs):
        return default_dirs[choice-1]
    else:
        return input("Nhập đường dẫn thư mục đầu ra: ")

def load_backtest_config():
    """Tải cấu hình backtest từ file"""
    config_file = 'backtest_master_config.json'
    if not os.path.exists(config_file):
        print(f"❌ Không tìm thấy file cấu hình {config_file}")
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"❌ Lỗi khi đọc file cấu hình: {str(e)}")
        return None

def fetch_data_from_backtest_config():
    """Tải dữ liệu dựa trên cấu hình backtest"""
    config = load_backtest_config()
    if not config:
        return
    
    symbols = config.get('symbols', ['BTCUSDT'])
    timeframes = config.get('timeframes', ['1h'])
    phases = config.get('phases', [])
    
    print("\n===== TẢI DỮ LIỆU TỪ CẤU HÌNH BACKTEST =====")
    print(f"Đã tìm thấy {len(symbols)} cặp tiền và {len(timeframes)} khung thời gian")
    print(f"Cặp tiền: {', '.join(symbols)}")
    print(f"Khung thời gian: {', '.join(timeframes)}")
    print(f"Số giai đoạn: {len(phases)}")
    
    if not phases:
        print("❌ Không tìm thấy thông tin giai đoạn trong cấu hình")
        return
    
    print("\nChọn giai đoạn để tải dữ liệu:")
    for i, phase in enumerate(phases, 1):
        print(f"{i}. {phase.get('name')} ({phase.get('start_date')} đến {phase.get('end_date')})")
    print(f"{len(phases)+1}. Tất cả các giai đoạn")
    
    choice = int(input(f"Chọn một tùy chọn (1-{len(phases)+1}): "))
    
    # Lấy client Binance
    client = get_binance_client()
    if not client:
        print("❌ Không thể kết nối đến Binance API")
        return
    
    # Xử lý lựa chọn
    phases_to_fetch = []
    if 1 <= choice <= len(phases):
        phases_to_fetch = [phases[choice-1]]
    elif choice == len(phases)+1:
        phases_to_fetch = phases
    else:
        print("❌ Lựa chọn không hợp lệ")
        return
    
    # Tải dữ liệu cho từng giai đoạn
    total_files = 0
    total_candles = 0
    
    for phase in phases_to_fetch:
        phase_name = phase.get('name', 'unknown')
        start_date = phase.get('start_date')
        end_date = phase.get('end_date')
        output_dir = f"test_data/{phase_name.lower().replace(' ', '_')}"
        
        print(f"\n===== TẢI DỮ LIỆU CHO GIAI ĐOẠN: {phase_name} =====")
        print(f"Khoảng thời gian: {start_date} đến {end_date}")
        print(f"Lưu vào thư mục: {output_dir}")
        
        # Tạo thư mục nếu chưa tồn tại
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Tổng số cặp cần tải
        total_pairs = len(symbols) * len(timeframes)
        progress_bar = tqdm(total=total_pairs, desc=f"Giai đoạn {phase_name}", unit="pair")
        
        # Tải dữ liệu cho từng cặp
        for symbol in symbols:
            for interval in timeframes:
                result, candles = fetch_single_pair(
                    client=client,
                    symbol=symbol,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir,
                    retry_count=3
                )
                
                if result:
                    total_files += 1
                    total_candles += candles
                
                progress_bar.update(1)
                progress_bar.set_description(f"Giai đoạn {phase_name}: {symbol} {interval}")
                
                # Tránh rate limit
                time.sleep(0.5)
        
        progress_bar.close()
    
    print(f"\n✅ Hoàn tất! Đã tải {total_files} file với tổng cộng {total_candles} nến")

def fetch_data_for_single_pair():
    """Tải dữ liệu cho một cặp tiền cụ thể"""
    # Chọn cặp tiền
    symbol = select_symbol()
    
    # Chọn khung thời gian
    interval = select_interval()
    
    # Chọn khoảng thời gian
    start_date, end_date = select_time_range()
    
    # Chọn thư mục đầu ra
    output_dir = select_output_dir()
    
    # Tóm tắt lựa chọn
    print("\n===== TÓM TẮT LỰA CHỌN =====")
    print(f"Cặp tiền: {symbol}")
    print(f"Khung thời gian: {interval}")
    print(f"Thời gian: {start_date} đến {end_date}")
    print(f"Thư mục đầu ra: {output_dir}")
    
    confirm = input("\nXác nhận tải dữ liệu? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Đã hủy tải dữ liệu")
        return
    
    # Lấy client Binance
    client = get_binance_client()
    if not client:
        print("❌ Không thể kết nối đến Binance API")
        return
    
    # Tải dữ liệu
    fetch_single_pair(
        client=client,
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        retry_count=3
    )

def fetch_data_for_multiple_pairs():
    """Tải dữ liệu cho nhiều cặp tiền"""
    # Danh sách cặp tiền phổ biến
    popular_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
                       'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'LINKUSDT']
    
    print("\n===== CHỌN CẶP TIỀN =====")
    print("Nhập số thứ tự của các cặp tiền, cách nhau bởi dấu cách:")
    for i, symbol in enumerate(popular_symbols, 1):
        print(f"{i}. {symbol}")
    
    selections = input(f"Lựa chọn (ví dụ: 1 2 3) hoặc 'all' để chọn tất cả: ")
    
    if selections.lower() == 'all':
        selected_symbols = popular_symbols
    else:
        try:
            indices = [int(x) - 1 for x in selections.split()]
            selected_symbols = [popular_symbols[i] for i in indices if 0 <= i < len(popular_symbols)]
        except:
            print("❌ Lựa chọn không hợp lệ")
            return
    
    if not selected_symbols:
        print("❌ Không có cặp tiền nào được chọn")
        return
    
    # Chọn khung thời gian
    print("\n===== CHỌN KHUNG THỜI GIAN =====")
    intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d']
    for i, interval in enumerate(intervals, 1):
        print(f"{i}. {interval}")
    
    selections = input(f"Lựa chọn (ví dụ: 6 7 8) hoặc 'common' cho các khung phổ biến: ")
    
    if selections.lower() == 'common':
        selected_intervals = ['15m', '1h', '4h']
    else:
        try:
            indices = [int(x) - 1 for x in selections.split()]
            selected_intervals = [intervals[i] for i in indices if 0 <= i < len(intervals)]
        except:
            print("❌ Lựa chọn không hợp lệ")
            return
    
    if not selected_intervals:
        print("❌ Không có khung thời gian nào được chọn")
        return
    
    # Chọn khoảng thời gian
    start_date, end_date = select_time_range()
    
    # Chọn thư mục đầu ra
    output_dir = select_output_dir()
    
    # Tóm tắt lựa chọn
    print("\n===== TÓM TẮT LỰA CHỌN =====")
    print(f"Cặp tiền ({len(selected_symbols)}): {', '.join(selected_symbols)}")
    print(f"Khung thời gian ({len(selected_intervals)}): {', '.join(selected_intervals)}")
    print(f"Thời gian: {start_date} đến {end_date}")
    print(f"Thư mục đầu ra: {output_dir}")
    
    confirm = input("\nXác nhận tải dữ liệu? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Đã hủy tải dữ liệu")
        return
    
    # Lấy client Binance
    client = get_binance_client()
    if not client:
        print("❌ Không thể kết nối đến Binance API")
        return
    
    # Tải dữ liệu
    total_files = 0
    total_candles = 0
    total_pairs = len(selected_symbols) * len(selected_intervals)
    
    progress_bar = tqdm(total=total_pairs, desc="Tải dữ liệu", unit="pair")
    
    for symbol in selected_symbols:
        for interval in selected_intervals:
            result, candles = fetch_single_pair(
                client=client,
                symbol=symbol,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                output_dir=output_dir,
                retry_count=3
            )
            
            if result:
                total_files += 1
                total_candles += candles
            
            progress_bar.update(1)
            progress_bar.set_description(f"Tải dữ liệu: {symbol} {interval}")
            
            # Tránh rate limit
            time.sleep(0.5)
    
    progress_bar.close()
    print(f"\n✅ Hoàn tất! Đã tải {total_files}/{total_pairs} file với tổng cộng {total_candles} nến")

def fetch_demo_data():
    """Tải dữ liệu mẫu cho demo"""
    # Bộ dữ liệu mẫu
    demo_data = [
        {'symbol': 'BTCUSDT', 'interval': '15m', 'days': 30},
        {'symbol': 'BTCUSDT', 'interval': '1h', 'days': 90},
        {'symbol': 'ETHUSDT', 'interval': '15m', 'days': 30},
        {'symbol': 'ETHUSDT', 'interval': '1h', 'days': 90}
    ]
    
    # Chọn thư mục đầu ra
    output_dir = 'demo_data'
    print(f"\n===== TẢI DỮ LIỆU MẪU CHO DEMO =====")
    print(f"Thư mục đầu ra: {output_dir}")
    print("Sẽ tải 4 bộ dữ liệu mẫu cho BTC và ETH với các khung thời gian 15m và 1h")
    
    confirm = input("\nXác nhận tải dữ liệu mẫu? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Đã hủy tải dữ liệu")
        return
    
    # Lấy client Binance
    client = get_binance_client()
    if not client:
        print("❌ Không thể kết nối đến Binance API")
        return
    
    # Tải dữ liệu mẫu
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    total_files = 0
    total_candles = 0
    
    for item in demo_data:
        symbol = item['symbol']
        interval = item['interval']
        days = item['days']
        
        now = datetime.now()
        start_date = (now - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        print(f"\nĐang tải {symbol} {interval} cho {days} ngày gần đây...")
        result, candles = fetch_single_pair(
            client=client,
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            retry_count=3
        )
        
        if result:
            total_files += 1
            total_candles += candles
        
        # Tránh rate limit
        time.sleep(0.5)
    
    print(f"\n✅ Hoàn tất! Đã tải {total_files}/4 file với tổng cộng {total_candles} nến")

def check_downloaded_data():
    """Kiểm tra dữ liệu đã tải"""
    print("\n===== KIỂM TRA DỮ LIỆU ĐÃ TẢI =====")
    
    # Các thư mục cần kiểm tra
    dirs = ['test_data', 'real_data', 'backtest_data', 'data', 'demo_data']
    
    # Thống kê
    total_files = 0
    total_size = 0
    
    # Tổng hợp
    summary = {}
    
    # Kiểm tra từng thư mục
    for dir_name in dirs:
        if not os.path.exists(dir_name):
            continue
        
        print(f"\nThư mục: {dir_name}")
        
        # Lấy danh sách file CSV
        csv_files = []
        for root, _, files in os.walk(dir_name):
            for file in files:
                if file.endswith('.csv'):
                    file_path = os.path.join(root, file)
                    csv_files.append(file_path)
        
        if not csv_files:
            print("  Không có file CSV nào")
            continue
        
        # Hiển thị danh sách và thống kê
        for file_path in csv_files:
            file_size = os.path.getsize(file_path) / 1024  # KB
            total_size += file_size
            total_files += 1
            
            # Đọc file để đếm số dòng
            try:
                with open(file_path, 'r') as f:
                    lines = sum(1 for _ in f) - 1  # Trừ header
            except:
                lines = 0
            
            # Lấy tên file
            file_name = os.path.basename(file_path)
            
            # Phân tích tên file để lấy symbol và interval
            parts = file_name.split('_')
            if len(parts) >= 2:
                symbol = parts[0]
                interval = parts[1].replace('.csv', '')
                
                # Cập nhật tổng hợp
                if symbol not in summary:
                    summary[symbol] = {}
                if interval not in summary[symbol]:
                    summary[symbol][interval] = []
                
                summary[symbol][interval].append({
                    'file': file_path,
                    'candles': lines,
                    'size_kb': round(file_size, 2)
                })
            
            print(f"  {file_name}: {lines} nến, {round(file_size, 2)} KB")
    
    # Hiển thị tổng hợp
    print("\n===== TỔNG HỢP =====")
    print(f"Tổng số file: {total_files}")
    print(f"Tổng dung lượng: {round(total_size / 1024, 2)} MB")
    
    # Hiển thị chi tiết theo symbol
    print("\n===== CHI TIẾT THEO CẶP TIỀN =====")
    for symbol in sorted(summary.keys()):
        print(f"\n{symbol}:")
        for interval in sorted(summary[symbol].keys()):
            files = summary[symbol][interval]
            total_candles = sum(f['candles'] for f in files)
            print(f"  {interval}: {len(files)} file, {total_candles} nến")

def main():
    """Hàm chính"""
    # Hiển thị header
    print("\n" + "="*50)
    print("  CÔNG CỤ TẢI DỮ LIỆU GIÁ CRYPTO TỪ BINANCE")
    print("  Phiên bản 1.0 - (c) 2025")
    print("="*50)
    
    while True:
        try:
            choice = input(MAIN_MENU)
            
            if choice == '1':
                fetch_data_for_single_pair()
            elif choice == '2':
                fetch_data_for_multiple_pairs()
            elif choice == '3':
                fetch_data_from_backtest_config()
            elif choice == '4':
                fetch_demo_data()
            elif choice == '5':
                check_downloaded_data()
            elif choice == '6':
                print("\nCảm ơn bạn đã sử dụng công cụ tải dữ liệu. Tạm biệt!")
                break
            else:
                print("\n❌ Lựa chọn không hợp lệ. Vui lòng thử lại.")
            
            print("\n" + "-"*50)
        except Exception as e:
            print(f"\n❌ Lỗi không xác định: {str(e)}")
            logger.exception("Lỗi không xác định")

if __name__ == "__main__":
    main()