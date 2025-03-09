"""
Regime Test - Kiểm tra hiệu quả của trình phát hiện chế độ thị trường mới

Script này dùng để kiểm tra trình phát hiện chế độ thị trường mới (enhanced_market_regime_detector.py)
và phân tích hiệu suất theo chế độ thị trường (regime_performance_analyzer.py).
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Union, Any

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('regime_test')

# Import các module liên quan
from enhanced_market_regime_detector import EnhancedMarketRegimeDetector
from regime_performance_analyzer import RegimePerformanceAnalyzer

# Import thư viện dữ liệu Binance nếu cần
try:
    from app.data_loader import DataLoader
    has_data_loader = True
except ImportError:
    logger.warning("Không thể import DataLoader, sẽ sử dụng dữ liệu mẫu")
    has_data_loader = False

def load_market_data(symbol: str = 'BTCUSDT', timeframe: str = '1h', 
                    days: int = 90) -> pd.DataFrame:
    """
    Tải dữ liệu thị trường từ Binance hoặc tạo dữ liệu mẫu.
    
    Args:
        symbol (str): Cặp tiền tệ
        timeframe (str): Khung thời gian
        days (int): Số ngày dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu thị trường
    """
    if has_data_loader:
        try:
            # Sử dụng DataLoader để tải dữ liệu thực
            data_loader = DataLoader()
            df = data_loader.load_historical_data(symbol, timeframe, days)
            logger.info(f"Đã tải dữ liệu thực từ Binance cho {symbol} {timeframe}, {len(df)} nến")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu thực: {str(e)}")
            logger.info("Chuyển sang sử dụng dữ liệu mẫu")
    
    # Tạo dữ liệu mẫu nếu không tải được dữ liệu thực
    logger.info("Tạo dữ liệu thị trường mẫu")
    
    # Số lượng nến (24 giờ * số ngày)
    num_candles = 24 * days if timeframe == '1h' else days
    
    # Tạo mốc thời gian
    end_time = datetime.now()
    dates = [end_time - timedelta(hours=i) for i in range(num_candles, 0, -1)]
    
    # Tạo giá mẫu (giả lập xu hướng và biến động)
    np.random.seed(42)  # Để kết quả nhất quán
    
    # Giá ban đầu
    base_price = 50000  # Giá BTC
    
    # Tạo mẫu nhiễu ngẫu nhiên
    noise = np.random.normal(0, 1, num_candles)
    
    # Tạo xu hướng (trend)
    trend = np.zeros(num_candles)
    
    # Tạo các chu kỳ thị trường
    # 1. Trending bullish (0-20%)
    trend[:int(num_candles*0.2)] = np.linspace(0, 5000, int(num_candles*0.2))
    
    # 2. Ranging wide (20-35%)
    range_wide_idx = slice(int(num_candles*0.2), int(num_candles*0.35))
    trend[range_wide_idx] = 5000 + np.random.uniform(-500, 500, len(trend[range_wide_idx]))
    
    # 3. Trending bearish (35-50%)
    trend[int(num_candles*0.35):int(num_candles*0.5)] = np.linspace(5000, 2000, int(num_candles*0.15))
    
    # 4. Volatile breakout (50-60%)
    volatile_idx = slice(int(num_candles*0.5), int(num_candles*0.6))
    trend[volatile_idx] = 2000 + np.concatenate([
        np.random.uniform(-1000, 1000, len(trend[volatile_idx])//2),
        np.random.uniform(1000, 3000, len(trend[volatile_idx])//2)
    ])
    
    # 5. Quiet accumulation (60-75%)
    quiet_idx = slice(int(num_candles*0.6), int(num_candles*0.75))
    trend[quiet_idx] = 4000 + np.random.uniform(-200, 200, len(trend[quiet_idx]))
    
    # 6. Ranging narrow (75-90%)
    range_narrow_idx = slice(int(num_candles*0.75), int(num_candles*0.9))
    trend[range_narrow_idx] = 4000 + np.random.uniform(-350, 350, len(trend[range_narrow_idx]))
    
    # 7. Trending bullish (90-100%)
    trend[int(num_candles*0.9):] = np.linspace(4000, 6000, num_candles - int(num_candles*0.9))
    
    # Kết hợp xu hướng và nhiễu
    close_prices = base_price + trend + noise * 100
    
    # Tạo biến động giữa nến (open, high, low)
    volatility = np.abs(np.random.normal(0, 1, num_candles)) * 100 + 50
    
    # Tạo volume với mô hình tương quan với giá
    volume_base = 1000
    volume = np.zeros(num_candles)
    
    for i in range(num_candles):
        if i > 0:
            # Tăng volume khi giá thay đổi mạnh
            price_change = abs(close_prices[i] - close_prices[i-1])
            volume_change = price_change / 100  # Tăng volume theo biến động giá
            volume[i] = volume_base * (1 + volume_change + np.random.random() * 0.5)
        else:
            volume[i] = volume_base
    
    # Tạo DataFrame
    market_data = pd.DataFrame({
        'open': [close_prices[i-1] if i > 0 else close_prices[i] - volatility[i] for i in range(num_candles)],
        'high': [max(close_prices[i], close_prices[i-1] if i > 0 else close_prices[i]) + volatility[i] for i in range(num_candles)],
        'low': [min(close_prices[i], close_prices[i-1] if i > 0 else close_prices[i]) - volatility[i] for i in range(num_candles)],
        'close': close_prices,
        'volume': volume
    }, index=dates)
    
    # Thêm các chỉ báo cần thiết
    # 1. SMA & EMA
    market_data['SMA20'] = market_data['close'].rolling(window=20).mean()
    market_data['EMA20'] = market_data['close'].ewm(span=20, adjust=False).mean()
    
    # 2. Bollinger Bands
    market_data['BB_Middle'] = market_data['SMA20']
    market_data['BB_Std'] = market_data['close'].rolling(window=20).std()
    market_data['BB_Upper'] = market_data['BB_Middle'] + 2 * market_data['BB_Std']
    market_data['BB_Lower'] = market_data['BB_Middle'] - 2 * market_data['BB_Std']
    market_data['BB_Width'] = (market_data['BB_Upper'] - market_data['BB_Lower']) / market_data['BB_Middle']
    
    # 3. RSI
    delta = market_data['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    market_data['RSI'] = 100 - (100 / (1 + rs))
    
    # 4. Simulate ADX (Direction Movement Index)
    market_data['ATR'] = volatility  # Simplified ATR
    market_data['ADX'] = np.zeros(len(market_data))
    
    # Thêm ADX tính toán đơn giản
    for i in range(30, len(market_data)):
        # ADX cao cho chế độ trending, thấp cho ranging
        if i < int(num_candles*0.2) or i > int(num_candles*0.9) or (i > int(num_candles*0.35) and i < int(num_candles*0.5)):
            market_data.loc[market_data.index[i], 'ADX'] = np.random.uniform(25, 45)  # Trending
        elif (i > int(num_candles*0.6) and i < int(num_candles*0.9)):
            market_data.loc[market_data.index[i], 'ADX'] = np.random.uniform(5, 15)  # Ranging narrow / Quiet
        else:
            market_data.loc[market_data.index[i], 'ADX'] = np.random.uniform(15, 25)  # Ranging wide / Mixed
    
    # 5. Các chỉ báo khác cần thiết
    market_data['Price_Volatility'] = market_data['close'].pct_change().rolling(window=14).std()
    market_data['Trend_Strength'] = (market_data['close'] - market_data['close'].shift(20)) / market_data['close'].shift(20)
    market_data['Volume_Ratio'] = market_data['volume'] / market_data['volume'].rolling(window=20).mean()
    market_data['Volume_Trend'] = market_data['volume'].diff(5) / market_data['volume'].shift(5)
    market_data['MA20'] = market_data['SMA20']  # Duplicate for compatibility
    market_data['ATR_Ratio'] = market_data['ATR'] / market_data['ATR'].rolling(window=14).mean()
    
    # Lấy một phần của dữ liệu dựa trên tham số days
    logger.info(f"Đã tạo dữ liệu mẫu: {len(market_data)} nến")
    
    # Loại bỏ hàng có giá trị NaN
    return market_data.dropna()

def generate_simulated_trades(market_data: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo các giao dịch mô phỏng dựa trên dữ liệu thị trường.
    
    Args:
        market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
        
    Returns:
        pd.DataFrame: DataFrame chứa lịch sử giao dịch mô phỏng
    """
    logger.info("Tạo dữ liệu giao dịch mô phỏng")
    
    # Phát hiện chế độ thị trường cho dữ liệu
    detector = EnhancedMarketRegimeDetector()
    
    # Danh sách lưu trữ giao dịch
    trades = []
    
    # Số lượng giao dịch mô phỏng
    num_trades = min(200, len(market_data) // 5)
    
    # Tạo giao dịch mô phỏng
    for i in range(num_trades):
        # Chọn một thời điểm ngẫu nhiên từ dữ liệu
        idx = np.random.randint(50, len(market_data) - 30)
        
        # Phát hiện chế độ thị trường tại thời điểm đó
        current_data = market_data.iloc[:idx].copy()
        regime_result = detector.detect_regime(current_data)
        regime = regime_result['regime']
        
        # Thiết lập thông số dựa trên chế độ thị trường
        regime_params = {
            'trending_bullish': {'win_rate': 0.75, 'avg_profit': 2.5, 'avg_loss': -1.5, 'hold_time': (6, 48), 'direction': 1},
            'trending_bearish': {'win_rate': 0.70, 'avg_profit': 2.2, 'avg_loss': -1.6, 'hold_time': (6, 48), 'direction': -1},
            'ranging_narrow': {'win_rate': 0.65, 'avg_profit': 1.8, 'avg_loss': -1.4, 'hold_time': (4, 24), 'direction': 0},
            'ranging_wide': {'win_rate': 0.60, 'avg_profit': 2.0, 'avg_loss': -1.8, 'hold_time': (4, 36), 'direction': 0},
            'volatile_breakout': {'win_rate': 0.55, 'avg_profit': 3.5, 'avg_loss': -2.5, 'hold_time': (2, 12), 'direction': 0},
            'quiet_accumulation': {'win_rate': 0.60, 'avg_profit': 1.5, 'avg_loss': -1.2, 'hold_time': (12, 72), 'direction': 0},
            'neutral': {'win_rate': 0.50, 'avg_profit': 1.0, 'avg_loss': -1.0, 'hold_time': (6, 24), 'direction': 0}
        }
        
        params = regime_params.get(regime, regime_params['neutral'])
        
        # Xác định hướng giao dịch
        if params['direction'] == 0:
            direction = np.random.choice([1, -1])
        else:
            direction = params['direction']
        
        # Xác định thắng/thua dựa trên tỷ lệ thắng
        is_win = np.random.random() < params['win_rate']
        
        # Tính lợi nhuận
        if is_win:
            profit_pct = params['avg_profit'] + np.random.normal(0, 0.5)
        else:
            profit_pct = params['avg_loss'] + np.random.normal(0, 0.3)
        
        # Thời gian giữ lệnh
        hold_hours = np.random.randint(params['hold_time'][0], params['hold_time'][1])
        
        # Thời gian vào lệnh
        entry_time = market_data.index[idx]
        
        # Thời gian ra lệnh
        exit_idx = min(idx + hold_hours, len(market_data) - 1)
        exit_time = market_data.index[exit_idx]
        
        # Giá vào lệnh và ra lệnh
        entry_price = market_data.iloc[idx]['close']
        exit_price = market_data.iloc[exit_idx]['close']
        
        # Tính lợi nhuận theo số tiền (giả sử vốn 1000$)
        profit_amount = profit_pct * 10
        
        # Thêm vào danh sách giao dịch
        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'symbol': 'BTCUSDT',
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit_pct': profit_pct,
            'profit_amount': profit_amount,
            'regime': regime,
            'regime_confidence': regime_result['confidence'],
            'win': is_win
        })
    
    # Tạo DataFrame từ danh sách giao dịch
    trades_df = pd.DataFrame(trades)
    
    logger.info(f"Đã tạo {len(trades_df)} giao dịch mô phỏng")
    
    return trades_df

def run_regime_detection_test(market_data: pd.DataFrame) -> Dict:
    """
    Chạy thử nghiệm phát hiện chế độ thị trường.
    
    Args:
        market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
        
    Returns:
        Dict: Kết quả của thử nghiệm
    """
    logger.info("Bắt đầu thử nghiệm phát hiện chế độ thị trường")
    
    # Khởi tạo detector
    detector = EnhancedMarketRegimeDetector()
    
    # Danh sách lưu trữ kết quả
    results = []
    
    # Phát hiện chế độ thị trường tại mỗi thời điểm
    step = max(1, len(market_data) // 100)  # Lấy mẫu để giảm thời gian xử lý
    
    for i in range(50, len(market_data), step):
        # Lấy dữ liệu đến thời điểm hiện tại
        current_data = market_data.iloc[:i].copy()
        
        # Phát hiện chế độ thị trường
        result = detector.detect_regime(current_data)
        
        # Thêm vào danh sách kết quả
        results.append({
            'time': market_data.index[i],
            'regime': result['regime'],
            'confidence': result['confidence'],
            'price': market_data.iloc[i]['close'],
            'adx': market_data.iloc[i]['ADX'],
            'volatility': market_data.iloc[i]['Price_Volatility'],
            'regime_scores': result.get('scores', {})
        })
    
    # Tạo DataFrame từ danh sách kết quả
    results_df = pd.DataFrame(results)
    
    # Thống kê phân phối chế độ
    regime_counts = results_df['regime'].value_counts()
    total_counts = len(results_df)
    
    # In thống kê
    logger.info("Phân phối chế độ thị trường:")
    for regime, count in regime_counts.items():
        percentage = count / total_counts * 100
        logger.info(f"  {regime}: {count} lần ({percentage:.1f}%)")
    
    # Tính độ tin cậy trung bình cho mỗi chế độ
    avg_confidence = results_df.groupby('regime')['confidence'].mean()
    
    logger.info("Độ tin cậy trung bình theo chế độ:")
    for regime, confidence in avg_confidence.items():
        logger.info(f"  {regime}: {confidence:.2f}")
    
    # Tạo biểu đồ phân phối chế độ thị trường theo thời gian
    plt.figure(figsize=(15, 10))
    
    # 1. Biểu đồ giá
    plt.subplot(3, 1, 1)
    plt.plot(results_df['time'], results_df['price'], color='blue')
    plt.title('Giá Bitcoin')
    plt.ylabel('Giá (USD)')
    plt.grid(True, alpha=0.3)
    
    # 2. Biểu đồ chế độ thị trường
    plt.subplot(3, 1, 2)
    
    # Tạo mã màu cho từng chế độ
    regime_colors = {
        'trending_bullish': 'green',
        'trending_bearish': 'red',
        'ranging_narrow': 'gray',
        'ranging_wide': 'orange',
        'volatile_breakout': 'purple',
        'quiet_accumulation': 'blue',
        'neutral': 'black'
    }
    
    # Màu mặc định
    default_color = 'black'
    
    # Tạo mã số cho mỗi chế độ để hiển thị trên biểu đồ
    regime_mapping = {regime: i for i, regime in enumerate(regime_colors.keys())}
    
    # Chuyển đổi chế độ thành mã số
    regime_codes = [regime_mapping.get(r, -1) for r in results_df['regime']]
    
    # Vẽ biểu đồ
    plt.scatter(results_df['time'], regime_codes, 
              c=[regime_colors.get(r, default_color) for r in results_df['regime']], 
              alpha=0.7)
    
    # Thêm nhãn cho trục y
    plt.yticks(list(regime_mapping.values()), list(regime_mapping.keys()))
    plt.title('Phát hiện chế độ thị trường theo thời gian')
    plt.ylabel('Chế độ thị trường')
    plt.grid(True, alpha=0.3)
    
    # 3. Biểu đồ độ tin cậy
    plt.subplot(3, 1, 3)
    plt.plot(results_df['time'], results_df['confidence'], color='orange')
    plt.title('Độ tin cậy phát hiện chế độ thị trường')
    plt.ylabel('Độ tin cậy')
    plt.xlabel('Thời gian')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Lưu biểu đồ
    chart_path = 'regime_detection_test.png'
    plt.savefig(chart_path)
    plt.close()
    
    logger.info(f"Đã lưu biểu đồ phát hiện chế độ thị trường tại: {chart_path}")
    
    # Tạo kết quả thử nghiệm
    test_result = {
        'regime_distribution': regime_counts.to_dict(),
        'avg_confidence': avg_confidence.to_dict(),
        'chart_path': chart_path,
        'test_time': datetime.now().isoformat()
    }
    
    return test_result

def run_performance_analysis_test(market_data: pd.DataFrame, trades_df: pd.DataFrame) -> str:
    """
    Chạy thử nghiệm phân tích hiệu suất theo chế độ thị trường.
    
    Args:
        market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
        trades_df (pd.DataFrame): DataFrame chứa lịch sử giao dịch
        
    Returns:
        str: Đường dẫn đến báo cáo hiệu suất
    """
    logger.info("Bắt đầu thử nghiệm phân tích hiệu suất theo chế độ thị trường")
    
    # Khởi tạo trình phân tích
    analyzer = RegimePerformanceAnalyzer()
    
    # Phân tích hiệu suất
    result = analyzer.analyze_trades_by_regime(trades_df, market_data, calculate_regime=False)
    
    # In kết quả
    for regime, perf in result.get('regime_performance', {}).items():
        logger.info(f"Chế độ: {regime}")
        logger.info(f"  Tỷ lệ thắng: {perf['win_rate']:.2%}")
        logger.info(f"  Lợi nhuận TB: {perf['avg_profit']:.2f}%")
        logger.info(f"  Profit Factor: {perf['profit_factor']:.2f}")
        logger.info(f"  Sharpe Ratio: {perf['sharpe_ratio']:.2f}")
        logger.info("")
    
    # Tạo báo cáo hiệu suất
    report_path = analyzer.generate_performance_report()
    
    logger.info(f"Đã tạo báo cáo hiệu suất tại: {report_path}")
    
    return report_path

def run_full_test():
    """Chạy toàn bộ thử nghiệm"""
    logger.info("=== BẮT ĐẦU THỬ NGHIỆM TOÀN DIỆN ===")
    
    # 1. Tải dữ liệu thị trường
    market_data = load_market_data(days=90)
    
    # 2. Chạy thử nghiệm phát hiện chế độ thị trường
    regime_test_result = run_regime_detection_test(market_data)
    
    # 3. Tạo dữ liệu giao dịch mô phỏng
    trades_df = generate_simulated_trades(market_data)
    
    # 4. Chạy thử nghiệm phân tích hiệu suất
    report_path = run_performance_analysis_test(market_data, trades_df)
    
    logger.info("=== KẾT THÚC THỬ NGHIỆM TOÀN DIỆN ===")
    logger.info(f"Kết quả phát hiện chế độ thị trường: {len(regime_test_result['regime_distribution'])} chế độ phát hiện được")
    logger.info(f"Báo cáo hiệu suất: {report_path}")
    
    return {
        'regime_test_result': regime_test_result,
        'performance_report_path': report_path
    }

if __name__ == "__main__":
    # Chạy thử nghiệm
    run_full_test()