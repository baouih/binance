"""
Script tạo dữ liệu mẫu cho backtesting với độ chân thực cao

Script này tạo dữ liệu giá mẫu với đặc tính gần giống dữ liệu thực của BTC, ETH
để phục vụ cho công việc backtest khi không có dữ liệu thực tế.
"""

import os
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def generate_price_series(symbol='BTCUSDT', days=180, interval='1h', volatility=None, 
                         start_price=None, with_tendency=True, with_regime_shifts=True,
                         regime_length_days=30):
    """
    Tạo chuỗi giá mẫu chân thực cho backtest
    
    Args:
        symbol (str): Mã cặp giao dịch
        days (int): Số ngày dữ liệu
        interval (str): Khung thời gian
        volatility (float): Độ biến động
        start_price (float): Giá ban đầu
        with_tendency (bool): Có tạo xu hướng tổng thể không
        with_regime_shifts (bool): Có tạo sự thay đổi chế độ thị trường không
        regime_length_days (int): Độ dài trung bình của một chế độ thị trường (ngày)
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLCV và timestamp
    """
    logger.info(f"Tạo dữ liệu mẫu cho {symbol}, {days} ngày, khung thời gian {interval}")
    
    # Xác định giá ban đầu dựa trên symbol
    if start_price is None:
        if symbol.startswith('BTC'):
            start_price = np.random.uniform(50000, 60000)
        elif symbol.startswith('ETH'):
            start_price = np.random.uniform(3000, 4000)
        else:
            start_price = np.random.uniform(1, 1000)
    
    # Xác định độ biến động dựa trên symbol
    if volatility is None:
        if symbol.startswith('BTC'):
            volatility = 0.015  # 1.5% biến động trung bình
        elif symbol.startswith('ETH'):
            volatility = 0.02   # 2.0% biến động trung bình
        else:
            volatility = 0.03   # 3.0% biến động trung bình
    
    # Tạo dữ liệu timestamp
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Xác định tần suất dựa trên interval
    if interval == '1m':
        freq = 'T'
        periods = days * 24 * 60
    elif interval == '5m':
        freq = '5T'
        periods = days * 24 * 12
    elif interval == '15m':
        freq = '15T'
        periods = days * 24 * 4
    elif interval == '30m':
        freq = '30T'
        periods = days * 24 * 2
    elif interval == '1h':
        freq = 'H'
        periods = days * 24
    elif interval == '4h':
        freq = '4H'
        periods = days * 6
    elif interval == '1d':
        freq = 'D'
        periods = days
    else:
        freq = 'H'  # Default to hourly
        periods = days * 24
    
    # Tạo chuỗi timestamp
    timestamp = pd.date_range(start=start_date, end=end_date, freq=freq)
    timestamp = timestamp[:periods]  # Cắt để đảm bảo đúng số lượng
    
    # Seed cho numpy random để tái tạo được kết quả
    seed = hash(symbol) % 10000
    np.random.seed(seed)
    
    # Tạo xu hướng cơ bản
    if with_tendency:
        # Xu hướng tổng thể (tăng/giảm/sideway)
        tendency_type = np.random.choice(['up', 'down', 'sideway'], p=[0.5, 0.3, 0.2])
        
        if tendency_type == 'up':
            drift = 0.0002  # Xu hướng tăng nhẹ
        elif tendency_type == 'down':
            drift = -0.0001  # Xu hướng giảm nhẹ
        else:
            drift = 0.00005  # Sideway với xu hướng tăng rất nhẹ
    else:
        drift = 0
        
    logger.info(f"Xu hướng tổng thể: {tendency_type if with_tendency else 'không có xu hướng'}")
    
    # Tạo chế độ thị trường
    if with_regime_shifts:
        # Số lượng thay đổi chế độ
        n_regimes = max(1, int(days / regime_length_days))
        
        # Tạo các điểm thay đổi chế độ
        change_points = sorted(np.random.choice(range(1, periods), size=n_regimes-1, replace=False))
        change_points = [0] + change_points + [periods]
        
        # Các loại chế độ thị trường
        regime_types = ['ranging', 'trending_up', 'trending_down', 'volatile']
        
        # Chọn chế độ cho từng khoảng
        regimes = []
        for i in range(n_regimes):
            regime = np.random.choice(regime_types)
            length = change_points[i+1] - change_points[i]
            regimes.append((regime, length))
            
        logger.info(f"Đã tạo {n_regimes} chế độ thị trường: {regimes}")
    
    # Tạo giá đóng cửa
    closes = [start_price]
    
    if with_regime_shifts:
        current_regime_idx = 0
        current_regime = regimes[0][0]
        remaining_length = regimes[0][1]
    
    for i in range(1, periods):
        if with_regime_shifts and remaining_length <= 0:
            current_regime_idx += 1
            if current_regime_idx < len(regimes):
                current_regime = regimes[current_regime_idx][0]
                remaining_length = regimes[current_regime_idx][1]
                logger.info(f"Thay đổi chế độ thị trường tại {timestamp[i]}: {current_regime}")
        
        # Điều chỉnh tham số dựa trên chế độ thị trường
        if with_regime_shifts:
            if current_regime == 'ranging':
                local_volatility = volatility * 0.8
                local_drift = 0
                spike_prob = 0.005
            elif current_regime == 'trending_up':
                local_volatility = volatility * 0.7
                local_drift = 0.0003
                spike_prob = 0.01
            elif current_regime == 'trending_down':
                local_volatility = volatility * 0.7
                local_drift = -0.0002
                spike_prob = 0.01
            elif current_regime == 'volatile':
                local_volatility = volatility * 1.5
                local_drift = 0
                spike_prob = 0.02
            
            remaining_length -= 1
        else:
            local_volatility = volatility
            local_drift = drift
            spike_prob = 0.01
        
        # Biến động ngẫu nhiên
        daily_return = local_drift + local_volatility * np.random.normal()
        
        # Thêm yếu tố mùa vụ
        seasonal = 0.001 * np.sin(i / 30)  # chu kỳ 30 ngày
        
        # Thêm nhiễu ngẫu nhiên
        noise = 0.001 * np.random.normal()
        
        # Tính giá mới
        return_rate = daily_return + seasonal + noise
        
        # Thêm đôi khi có biến động lớn (spike)
        if np.random.random() < spike_prob:
            spike = np.random.choice([-1, 1]) * np.random.uniform(0.01, 0.05)
            return_rate += spike
            logger.info(f"Biến động lớn tại {timestamp[i]}: {spike:.2%}")
        
        # Tính giá mới
        new_close = closes[-1] * (1 + return_rate)
        
        # Đảm bảo giá không âm và không quá thấp
        new_close = max(0.1, new_close)
        
        closes.append(new_close)
    
    # Tạo dataframe
    df = pd.DataFrame(index=timestamp)
    df['close'] = closes
    
    # Tạo open, high, low
    df['open'] = df['close'].shift(1)
    df.loc[df.index[0], 'open'] = closes[0] * (1 - np.random.uniform(0, 0.005))
    
    # Tạo biến động trong ngày (intraday)
    # High là giá cao nhất, thường cao hơn close/open
    # Low là giá thấp nhất, thường thấp hơn close/open
    intraday_volatility = pd.Series(np.random.uniform(0.003, 0.02, size=periods), index=df.index)
    
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + intraday_volatility)
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - intraday_volatility)
    
    # Tạo khối lượng giao dịch
    base_volume = start_price * 10  # Khối lượng cơ bản tỷ lệ với giá
    
    # Khối lượng tương quan với biến động giá
    price_changes = np.abs(df['close'].pct_change().fillna(0))
    volume = base_volume * (1 + 5 * price_changes)
    
    # Thêm nhiễu ngẫu nhiên cho khối lượng
    volume_noise = 1 + 0.3 * np.random.randn(len(df))
    volume_noise = np.maximum(0.5, volume_noise)  # Đảm bảo không âm
    
    df['volume'] = volume * volume_noise
    
    # Đổi tên index
    df.index.name = 'timestamp'
    
    # Đảm bảo không có giá trị NaN
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    # Thêm một số quy luật thị trường
    # 1. Khối lượng thường cao hơn khi giá biến động mạnh
    correlation_factor = 2.0
    df['volume'] = df['volume'] * (1 + correlation_factor * price_changes)
    
    # 2. Sau các phiên tăng/giảm mạnh thường có xu hướng đảo chiều
    strong_moves = (price_changes > np.percentile(price_changes, 90))
    reversal_mask = strong_moves.shift(1).fillna(False)
    
    for i in df.index[reversal_mask]:
        idx = df.index.get_loc(i)
        if idx + 1 < len(df):
            prev_change = df['close'].iloc[idx-1] / df['close'].iloc[idx-2] - 1
            reversal = -np.sign(prev_change) * np.random.uniform(0.002, 0.01)
            df.loc[df.index[idx], 'close'] = df['close'].iloc[idx-1] * (1 + reversal)
            df.loc[df.index[idx], 'high'] = max(df['close'].iloc[idx], df['open'].iloc[idx]) * (1 + 0.005)
            df.loc[df.index[idx], 'low'] = min(df['close'].iloc[idx], df['open'].iloc[idx]) * (1 - 0.005)
    
    # Reset index để timestamp thành cột
    df = df.reset_index()
    
    logger.info(f"Đã tạo xong dữ liệu mẫu: {len(df)} dòng")
    
    return df

def save_sample_data(df, symbol, interval, output_dir='sample_data'):
    """
    Lưu dữ liệu mẫu vào file csv
    
    Args:
        df (pd.DataFrame): DataFrame dữ liệu
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        output_dir (str): Thư mục đầu ra
        
    Returns:
        str: Đường dẫn đến file đã lưu
    """
    # Tạo thư mục nếu chưa tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Tạo tên file
    filename = f"{output_dir}/{symbol}_{interval}_sample.csv"
    
    # Lưu file
    df.to_csv(filename, index=False)
    
    logger.info(f"Đã lưu dữ liệu mẫu vào file: {filename}")
    
    return filename

def generate_multiple_symbols(symbols=['BTCUSDT', 'ETHUSDT'], intervals=['1h', '4h', '1d'], 
                            days=180, output_dir='sample_data'):
    """
    Tạo dữ liệu mẫu cho nhiều cặp tiền và khung thời gian
    
    Args:
        symbols (List[str]): Danh sách các cặp giao dịch
        intervals (List[str]): Danh sách khung thời gian
        days (int): Số ngày dữ liệu
        output_dir (str): Thư mục đầu ra
        
    Returns:
        Dict: Đường dẫn đến các file đã lưu
    """
    results = {}
    
    for symbol in symbols:
        symbol_results = {}
        
        for interval in intervals:
            # Tạo dữ liệu
            df = generate_price_series(symbol=symbol, days=days, interval=interval)
            
            # Lưu file
            filepath = save_sample_data(df, symbol, interval, output_dir)
            
            symbol_results[interval] = filepath
        
        results[symbol] = symbol_results
    
    # Lưu metadata
    metadata = {
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'days': days,
        'symbols': symbols,
        'intervals': intervals,
        'files': results
    }
    
    metadata_file = f"{output_dir}/metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=4)
    
    logger.info(f"Đã tạo xong dữ liệu mẫu cho {len(symbols)} symbol, {len(intervals)} interval")
    
    return results

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tạo dữ liệu mẫu cho backtest')
    parser.add_argument('--symbols', nargs='+', default=['BTCUSDT', 'ETHUSDT'], 
                       help='Các cặp giao dịch cần tạo dữ liệu')
    parser.add_argument('--intervals', nargs='+', default=['1h', '4h', '1d'], 
                       help='Các khung thời gian cần tạo dữ liệu')
    parser.add_argument('--days', type=int, default=180, 
                       help='Số ngày dữ liệu')
    parser.add_argument('--output', type=str, default='sample_data', 
                       help='Thư mục đầu ra')
    
    args = parser.parse_args()
    
    logger.info(f"Bắt đầu tạo dữ liệu mẫu với tham số: {args}")
    
    generate_multiple_symbols(
        symbols=args.symbols,
        intervals=args.intervals,
        days=args.days,
        output_dir=args.output
    )
    
    logger.info("Hoàn thành tạo dữ liệu mẫu")

if __name__ == "__main__":
    main()