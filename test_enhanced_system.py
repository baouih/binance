#!/usr/bin/env python3
"""
Test Enhanced System - Kiểm thử hệ thống nâng cao với các công cụ mới

Script này dùng để kiểm thử các tính năng mới được thêm vào hệ thống:
- Enhanced Market Regime Detector (6 chế độ thị trường)
- Order Flow Indicators (phân tích dòng lệnh)
- Volume Profile (phân tích cấu trúc khối lượng theo giá)
- Adaptive Risk Allocator (điều chỉnh rủi ro theo chế độ thị trường)

Cách sử dụng:
python test_enhanced_system.py --symbol BTCUSDT --days 30 --report
"""

import os
import sys
import argparse
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional, Union, Tuple

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('enhanced_system_test.log')
    ]
)
logger = logging.getLogger('test_enhanced_system')

# Import các module cần kiểm thử
try:
    from enhanced_market_regime_detector import EnhancedMarketRegimeDetector
    from order_flow_indicators import OrderFlowAnalyzer
    from volume_profile_analyzer import VolumeProfileAnalyzer
    from adaptive_risk_allocator import AdaptiveRiskAllocator
    from regime_performance_analyzer import RegimePerformanceAnalyzer
except ImportError as e:
    logger.error(f"Lỗi khi import module: {str(e)}")
    logger.info("Đảm bảo các module sau đã được cài đặt và có thể truy cập:")
    logger.info("- enhanced_market_regime_detector.py")
    logger.info("- order_flow_indicators.py")
    logger.info("- volume_profile_analyzer.py")
    logger.info("- adaptive_risk_allocator.py")
    logger.info("- regime_performance_analyzer.py")
    sys.exit(1)

def load_market_data(symbol: str, days: int = 30) -> pd.DataFrame:
    """
    Tải dữ liệu thị trường từ file hoặc API.
    
    Args:
        symbol (str): Cặp tiền tệ
        days (int): Số ngày dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu thị trường
    """
    # Kiểm tra xem có file dữ liệu đã lưu không
    data_dir = 'data'
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, f"{symbol}_{days}days.csv")
    
    if os.path.exists(file_path):
        try:
            logger.info(f"Tải dữ liệu từ file: {file_path}")
            df = pd.read_csv(file_path, index_col=0)
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as e:
            logger.warning(f"Lỗi khi đọc file dữ liệu: {str(e)}")
    
    # Nếu không có file hoặc đọc lỗi, tạo dữ liệu mẫu
    logger.info(f"Tạo dữ liệu mẫu cho {symbol}, {days} ngày")
    return _generate_sample_data(symbol, days)

def _generate_sample_data(symbol: str, days: int) -> pd.DataFrame:
    """Tạo dữ liệu mẫu để kiểm thử"""
    hours = 24 * days
    
    # Tạo timestamp
    end_time = datetime.now()
    dates = [end_time - timedelta(hours=i) for i in range(hours, 0, -1)]
    
    # Tạo giá với các mô hình khác nhau
    prices = []
    base_price = 50000 if symbol.startswith('BTC') else 2000  # Giá cơ sở tùy theo token
    
    # Tạo chuỗi giá mô phỏng các chế độ thị trường khác nhau
    for i in range(hours):
        # Chia thành các đoạn khác nhau để mô phỏng các chế độ thị trường
        if i < hours * 0.2:  # 20% đầu: trending bullish
            trend = base_price * 0.1 * (i / (hours * 0.2))  # Tăng 10%
            noise = np.random.normal(0, base_price * 0.005)
            price = base_price + trend + noise
            
        elif i < hours * 0.35:  # 15% tiếp: ranging wide
            mid_price = base_price * 1.1  # Giá sau đoạn tăng
            swing = base_price * 0.03 * np.sin(i * 0.3)  # Dao động ±3%
            noise = np.random.normal(0, base_price * 0.005)
            price = mid_price + swing + noise
            
        elif i < hours * 0.5:  # 15% tiếp: trending bearish
            start_price = base_price * 1.1 + base_price * 0.03  # Giá bắt đầu giảm
            drop = base_price * 0.15 * ((i - hours * 0.35) / (hours * 0.15))  # Giảm 15%
            noise = np.random.normal(0, base_price * 0.008)
            price = start_price - drop + noise
            
        elif i < hours * 0.6:  # 10% tiếp: volatile breakout
            start_price = base_price * 0.95  # Giá sau khi giảm
            # Tạo các cú sốc giá
            if (i - int(hours * 0.5)) % 24 < 4:  # Tạo spike mỗi 24 giờ
                spike = base_price * 0.08 * np.random.choice([-1, 1])  # Spike ±8%
            else:
                spike = 0
            noise = np.random.normal(0, base_price * 0.015)  # Nhiễu lớn hơn
            price = start_price + spike + noise
            
        elif i < hours * 0.75:  # 15% tiếp: quiet accumulation
            mid_price = base_price * 0.95  # Giá ổn định
            swing = base_price * 0.01 * np.sin(i * 0.2)  # Dao động nhỏ ±1%
            noise = np.random.normal(0, base_price * 0.002)  # Nhiễu nhỏ
            price = mid_price + swing + noise
            
        elif i < hours * 0.9:  # 15% tiếp: ranging narrow
            mid_price = base_price * 0.96  # Giá dao động hẹp
            swing = base_price * 0.015 * np.sin(i * 0.4)  # Dao động ±1.5%
            noise = np.random.normal(0, base_price * 0.003)
            price = mid_price + swing + noise
            
        else:  # 10% cuối: trending bullish again
            start_price = base_price * 0.96  # Giá bắt đầu tăng
            gain = base_price * 0.12 * ((i - hours * 0.9) / (hours * 0.1))  # Tăng 12%
            noise = np.random.normal(0, base_price * 0.006)
            price = start_price + gain + noise
        
        prices.append(price)
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'open': [prices[i-1] if i > 0 else prices[i] * 0.999 for i in range(hours)],
        'high': [p * (1 + np.random.uniform(0.001, 0.005)) for p in prices],
        'low': [p * (1 - np.random.uniform(0.001, 0.005)) for p in prices],
        'close': prices,
        'volume': [base_price * 0.5 * (1 + 0.5 * np.random.random()) for _ in range(hours)]
    }, index=dates)
    
    # Thêm các chỉ báo kỹ thuật
    # SMA
    df['SMA20'] = df['close'].rolling(window=20).mean()
    df['SMA50'] = df['close'].rolling(window=50).mean()
    
    # Bollinger Bands
    df['BB_Middle'] = df['SMA20']
    df['BB_Std'] = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
    df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = true_range.rolling(window=14).mean()
    
    # Thêm các chỉ báo cần thiết cho Enhanced Market Regime Detector
    df['ADX'] = 30 * np.random.random(hours)  # Giả lập ADX
    df['Trend_Strength'] = delta.rolling(window=20).mean() / df['close'].rolling(window=20).mean()
    df['Price_Volatility'] = df['close'].pct_change().rolling(window=14).std()
    df['MA20'] = df['SMA20']
    df['ATR_Ratio'] = df['ATR'] / df['ATR'].rolling(window=14).mean()
    df['BB_Width_Ratio'] = df['BB_Width'] / df['BB_Width'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()
    df['Volume_Trend'] = df['volume'].diff(5) / df['volume'].shift(5)
    
    # Lọc bỏ các hàng có NaN
    df = df.dropna()
    
    # Lưu dữ liệu
    data_dir = 'data'
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, f"{symbol}_{days}days.csv")
    df.to_csv(file_path)
    
    logger.info(f"Đã tạo và lưu dữ liệu mẫu tại: {file_path}")
    
    return df

def test_enhanced_market_regime_detector(df: pd.DataFrame, symbol: str) -> Dict:
    """Kiểm thử Enhanced Market Regime Detector"""
    logger.info("=== Kiểm thử Enhanced Market Regime Detector ===")
    
    detector = EnhancedMarketRegimeDetector()
    
    # Danh sách lưu trữ kết quả
    regime_history = []
    
    # Duyệt qua từng điểm dữ liệu (nhảy cách để tăng tốc độ)
    step = max(1, len(df) // 100)
    
    for i in range(50, len(df), step):
        # Cắt dữ liệu đến điểm hiện tại
        current_df = df.iloc[:i].copy()
        
        # Phát hiện chế độ thị trường
        result = detector.detect_regime(current_df)
        
        # Lưu kết quả
        regime_history.append({
            'time': df.index[i-1],
            'regime': result['regime'],
            'confidence': result['confidence'],
            'price': df.iloc[i-1]['close']
        })
    
    # Tạo DataFrame từ kết quả
    results_df = pd.DataFrame(regime_history)
    
    # Thống kê
    regime_counts = results_df['regime'].value_counts()
    logger.info("Phân bố chế độ thị trường:")
    for regime, count in regime_counts.items():
        pct = count / len(results_df) * 100
        logger.info(f"  {regime}: {count} lần ({pct:.1f}%)")
    
    # Tính độ tin cậy trung bình
    avg_confidence = results_df.groupby('regime')['confidence'].mean()
    logger.info("Độ tin cậy trung bình:")
    for regime, conf in avg_confidence.items():
        logger.info(f"  {regime}: {conf:.2f}")
    
    # Tạo biểu đồ
    _plot_regime_detection_results(results_df, symbol)
    
    # Trả về kết quả
    return {
        'regime_counts': regime_counts.to_dict(),
        'avg_confidence': avg_confidence.to_dict(),
        'regime_history': regime_history
    }

def test_order_flow_analyzer(df: pd.DataFrame, symbol: str) -> Dict:
    """Kiểm thử Order Flow Analyzer"""
    logger.info("=== Kiểm thử Order Flow Analyzer ===")
    
    analyzer = OrderFlowAnalyzer()
    
    # Mô phỏng dữ liệu order flow từ dữ liệu nến
    logger.info("Mô phỏng dữ liệu order flow từ dữ liệu nến...")
    analyzer.simulate_from_candle_data(symbol, df)
    
    # Lấy tín hiệu order flow
    signals = analyzer.get_order_flow_signals(symbol, df)
    
    logger.info(f"Tín hiệu Order Flow cho {symbol}:")
    logger.info(f"  Buy Signal: {signals['signals']['buy_signal']}")
    logger.info(f"  Sell Signal: {signals['signals']['sell_signal']}")
    logger.info(f"  Neutral: {signals['signals']['neutral']}")
    logger.info(f"  Signal Strength: {signals['signals']['strength']:.2f}")
    
    # Lấy các mức hỗ trợ/kháng cự
    support_levels = signals['key_levels']['support']
    resistance_levels = signals['key_levels']['resistance']
    
    if support_levels:
        logger.info(f"Các mức hỗ trợ: {', '.join([f'{level:.2f}' for level in support_levels])}")
    
    if resistance_levels:
        logger.info(f"Các mức kháng cự: {', '.join([f'{level:.2f}' for level in resistance_levels])}")
    
    # Lấy thông tin thanh khoản
    liquidity_ratio = signals['liquidity']['ratio']
    logger.info(f"Tỷ lệ thanh khoản (trên/dưới): {liquidity_ratio:.2f}")
    
    # Lấy delta tích lũy và chênh lệch lệnh
    cumulative_delta = analyzer.get_cumulative_delta(symbol)
    order_imbalance = analyzer.get_order_imbalance(symbol)
    
    logger.info(f"Delta tích lũy: {cumulative_delta:.2f}")
    logger.info(f"Chênh lệch lệnh: {order_imbalance:.2f}")
    
    # Trả về kết quả
    return {
        'signals': signals['signals'],
        'key_levels': signals['key_levels'],
        'liquidity': signals['liquidity'],
        'cumulative_delta': cumulative_delta,
        'order_imbalance': order_imbalance
    }

def test_volume_profile_analyzer(df: pd.DataFrame, symbol: str) -> Dict:
    """Kiểm thử Volume Profile Analyzer"""
    logger.info("=== Kiểm thử Volume Profile Analyzer ===")
    
    analyzer = VolumeProfileAnalyzer()
    
    # Tính toán volume profile
    profile_result = analyzer.calculate_volume_profile(df, symbol, 'session')
    
    if profile_result:
        logger.info(f"Point of Control (POC): {profile_result['poc']:.2f}")
        logger.info(f"Value Area High: {profile_result['value_area']['high']:.2f}")
        logger.info(f"Value Area Low: {profile_result['value_area']['low']:.2f}")
    
    # Phân tích vùng giao dịch
    range_analysis = analyzer.analyze_trading_range(df, symbol)
    
    if range_analysis:
        logger.info(f"Giá hiện tại: {range_analysis['current_price']:.2f}")
        logger.info(f"Vị trí: {range_analysis['position']}")
        
        if range_analysis['breakout_potential']['up']:
            logger.info("Có khả năng bứt phá lên")
        if range_analysis['breakout_potential']['down']:
            logger.info("Có khả năng bứt phá xuống")
    
    # Xác định vùng hỗ trợ/kháng cự
    sr_levels = analyzer.identify_support_resistance(df, symbol)
    
    if sr_levels:
        if 'support_levels' in sr_levels and sr_levels['support_levels']:
            logger.info("Vùng hỗ trợ:")
            for level in sr_levels['support_levels']:
                logger.info(f"  {level:.2f}")
        
        if 'resistance_levels' in sr_levels and sr_levels['resistance_levels']:
            logger.info("Vùng kháng cự:")
            for level in sr_levels['resistance_levels']:
                logger.info(f"  {level:.2f}")
    
    # Tạo biểu đồ
    chart_path = analyzer.visualize_volume_profile(symbol)
    logger.info(f"Đã tạo biểu đồ volume profile tại: {chart_path}")
    
    # Trả về kết quả
    return {
        'profile': profile_result,
        'range_analysis': range_analysis,
        'sr_levels': sr_levels,
        'chart_path': chart_path
    }

def test_adaptive_risk_allocator(df: pd.DataFrame, symbol: str) -> Dict:
    """Kiểm thử Adaptive Risk Allocator"""
    logger.info("=== Kiểm thử Adaptive Risk Allocator ===")
    
    risk_allocator = AdaptiveRiskAllocator(base_risk=2.5)
    
    # Danh sách lưu trữ kết quả
    risk_history = []
    
    # Duyệt qua từng điểm dữ liệu (nhảy cách để tăng tốc độ)
    step = max(1, len(df) // 50)
    
    for i in range(50, len(df), step):
        # Cắt dữ liệu đến điểm hiện tại
        current_df = df.iloc[:i].copy()
        
        # Mô phỏng thống kê tài khoản
        account_stats = {
            'win_streak': np.random.randint(0, 5),
            'lose_streak': np.random.randint(0, 3),
            'current_drawdown': np.random.uniform(0, 15)
        }
        
        # Tính toán mức rủi ro thích ứng
        result = risk_allocator.calculate_adaptive_risk(current_df, account_stats)
        
        # Lưu kết quả
        risk_history.append({
            'time': df.index[i-1],
            'regime': result['regime'],
            'base_risk': result['base_risk'],
            'base_regime_risk': result['base_regime_risk'],
            'adaptive_risk': result['adaptive_risk'],
            'price': df.iloc[i-1]['close']
        })
    
    # Tạo DataFrame từ kết quả
    results_df = pd.DataFrame(risk_history)
    
    # Thống kê mức rủi ro theo chế độ
    risk_by_regime = results_df.groupby('regime')[['base_regime_risk', 'adaptive_risk']].mean()
    logger.info("Mức rủi ro trung bình theo chế độ:")
    for regime, row in risk_by_regime.iterrows():
        logger.info(f"  {regime}: Cơ sở={row['base_regime_risk']:.2f}%, Thích ứng={row['adaptive_risk']:.2f}%")
    
    # Lấy đề xuất rủi ro cho các mức khác nhau
    for level in ['conservative', 'balanced', 'aggressive']:
        suggestion = risk_allocator.get_risk_suggestion(symbol, level)
        logger.info(f"Đề xuất cho mức {level}: {suggestion['suggested_risk_percentage']:.2f}%")
        logger.info(f"  {suggestion['suggestion_reason']}")
    
    # Tạo biểu đồ
    _plot_adaptive_risk_results(results_df, symbol)
    
    # Trả về kết quả
    return {
        'risk_by_regime': risk_by_regime.to_dict(),
        'risk_history': risk_history,
        'suggestions': {
            'conservative': risk_allocator.get_risk_suggestion(symbol, 'conservative'),
            'balanced': risk_allocator.get_risk_suggestion(symbol, 'balanced'),
            'aggressive': risk_allocator.get_risk_suggestion(symbol, 'aggressive')
        }
    }

def test_regime_performance_analyzer(df: pd.DataFrame, symbol: str) -> Dict:
    """Kiểm thử Regime Performance Analyzer"""
    logger.info("=== Kiểm thử Regime Performance Analyzer ===")
    
    detector = EnhancedMarketRegimeDetector()
    
    # Tạo dữ liệu giao dịch mô phỏng
    trades = _generate_sample_trades(df, symbol, detector)
    trades_df = pd.DataFrame(trades)
    
    # Tạo analyzer
    analyzer = RegimePerformanceAnalyzer()
    
    # Phân tích hiệu suất
    result = analyzer.analyze_trades_by_regime(trades_df, df, calculate_regime=False)
    
    if result:
        logger.info("Hiệu suất tổng thể:")
        logger.info(f"  Tổng số lệnh: {result['overall']['total_trades']}")
        logger.info(f"  Tỷ lệ thắng: {result['overall']['win_rate']:.2%}")
        logger.info(f"  Lợi nhuận TB: {result['overall']['avg_profit']:.2f}%")
        logger.info(f"  Profit Factor: {result['overall']['profit_factor']:.2f}")
        
        logger.info("Hiệu suất theo chế độ thị trường:")
        for regime, perf in result['regime_performance'].items():
            logger.info(f"  {regime}:")
            logger.info(f"    Tỷ lệ thắng: {perf['win_rate']:.2%}")
            logger.info(f"    Lợi nhuận TB: {perf['avg_profit']:.2f}%")
            logger.info(f"    Profit Factor: {perf['profit_factor']:.2f}")
        
        logger.info(f"Chế độ thị trường tốt nhất: {', '.join(result['best_regimes'])}")
    
    # Tạo báo cáo
    report_path = analyzer.generate_performance_report()
    logger.info(f"Đã tạo báo cáo phân tích hiệu suất tại: {report_path}")
    
    # Trả về kết quả
    return {
        'overall': result.get('overall', {}),
        'regime_performance': result.get('regime_performance', {}),
        'best_regimes': result.get('best_regimes', []),
        'report_path': report_path
    }

def _generate_sample_trades(df: pd.DataFrame, symbol: str, detector: EnhancedMarketRegimeDetector) -> List[Dict]:
    """Tạo dữ liệu giao dịch mô phỏng dựa trên chế độ thị trường"""
    trades = []
    
    # Tỷ lệ thắng và lợi nhuận theo chế độ
    regime_params = {
        'trending_bullish': {'win_rate': 0.75, 'avg_profit': 2.5, 'avg_loss': -1.5, 'hold_time': (6, 48), 'direction': 1},
        'trending_bearish': {'win_rate': 0.70, 'avg_profit': 2.2, 'avg_loss': -1.6, 'hold_time': (6, 48), 'direction': -1},
        'ranging_narrow': {'win_rate': 0.65, 'avg_profit': 1.8, 'avg_loss': -1.4, 'hold_time': (4, 24), 'direction': 0},
        'ranging_wide': {'win_rate': 0.60, 'avg_profit': 2.0, 'avg_loss': -1.8, 'hold_time': (4, 36), 'direction': 0},
        'volatile_breakout': {'win_rate': 0.55, 'avg_profit': 3.5, 'avg_loss': -2.5, 'hold_time': (2, 12), 'direction': 0},
        'quiet_accumulation': {'win_rate': 0.60, 'avg_profit': 1.5, 'avg_loss': -1.2, 'hold_time': (12, 72), 'direction': 0},
        'neutral': {'win_rate': 0.50, 'avg_profit': 1.0, 'avg_loss': -1.0, 'hold_time': (6, 24), 'direction': 0}
    }
    
    # Số lượng giao dịch mô phỏng
    num_trades = min(200, len(df) // 5)
    
    # Duyệt qua để xác định chế độ thị trường
    regimes = []
    step = max(1, len(df) // 100)
    
    for i in range(50, len(df), step):
        current_df = df.iloc[:i].copy()
        result = detector.detect_regime(current_df)
        regimes.append({
            'index': i,
            'regime': result['regime'],
            'confidence': result['confidence']
        })
    
    # Tạo giao dịch mô phỏng
    for i in range(num_trades):
        # Chọn một thời điểm ngẫu nhiên và lấy chế độ tương ứng
        regime_data = np.random.choice(regimes)
        idx = regime_data['index']
        regime = regime_data['regime']
        
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
        entry_time = df.index[idx]
        
        # Thời gian ra lệnh
        exit_idx = min(idx + hold_hours, len(df) - 1)
        exit_time = df.index[exit_idx]
        
        # Giá vào lệnh và ra lệnh
        entry_price = df.iloc[idx]['close']
        exit_price = df.iloc[exit_idx]['close']
        
        # Tính lợi nhuận theo số tiền (giả sử vốn 1000$)
        profit_amount = profit_pct * 10
        
        # Thêm vào danh sách giao dịch
        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit_pct': profit_pct,
            'profit_amount': profit_amount,
            'regime': regime,
            'regime_confidence': regime_data['confidence'],
            'win': is_win
        })
    
    return trades

def _plot_regime_detection_results(results_df: pd.DataFrame, symbol: str) -> None:
    """Tạo biểu đồ kết quả phát hiện chế độ thị trường"""
    plt.figure(figsize=(15, 10))
    
    # 1. Biểu đồ giá
    plt.subplot(3, 1, 1)
    plt.plot(results_df['time'], results_df['price'], color='blue')
    plt.title(f'Giá {symbol}')
    plt.ylabel('Giá (USD)')
    plt.grid(True, alpha=0.3)
    
    # 2. Biểu đồ chế độ thị trường
    plt.subplot(3, 1, 2)
    
    # Tạo màu cho từng chế độ
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
    regimes = list(regime_colors.keys())
    regime_mapping = {regime: i for i, regime in enumerate(regimes)}
    
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
    plt.savefig(f'{symbol}_regime_detection.png')
    plt.close()

def _plot_adaptive_risk_results(results_df: pd.DataFrame, symbol: str) -> None:
    """Tạo biểu đồ kết quả điều chỉnh rủi ro thích ứng"""
    plt.figure(figsize=(15, 10))
    
    # 1. Biểu đồ giá
    plt.subplot(3, 1, 1)
    plt.plot(results_df['time'], results_df['price'], color='blue')
    plt.title(f'Giá {symbol}')
    plt.ylabel('Giá (USD)')
    plt.grid(True, alpha=0.3)
    
    # 2. Biểu đồ chế độ thị trường
    plt.subplot(3, 1, 2)
    
    # Tạo màu cho từng chế độ
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
    regimes = list(regime_colors.keys())
    regime_mapping = {regime: i for i, regime in enumerate(regimes)}
    
    # Chuyển đổi chế độ thành mã số
    regime_codes = [regime_mapping.get(r, -1) for r in results_df['regime']]
    
    # Vẽ biểu đồ
    plt.scatter(results_df['time'], regime_codes, 
              c=[regime_colors.get(r, default_color) for r in results_df['regime']], 
              alpha=0.7)
    
    # Thêm nhãn cho trục y
    plt.yticks(list(regime_mapping.values()), list(regime_mapping.keys()))
    plt.title('Chế độ thị trường')
    plt.ylabel('Chế độ thị trường')
    plt.grid(True, alpha=0.3)
    
    # 3. Biểu đồ mức rủi ro
    plt.subplot(3, 1, 3)
    plt.plot(results_df['time'], results_df['base_regime_risk'], color='blue', label='Rủi ro cơ sở')
    plt.plot(results_df['time'], results_df['adaptive_risk'], color='red', label='Rủi ro thích ứng')
    plt.title('Mức rủi ro thích ứng theo chế độ thị trường')
    plt.ylabel('Mức rủi ro (%)')
    plt.xlabel('Thời gian')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Lưu biểu đồ
    plt.savefig(f'{symbol}_adaptive_risk.png')
    plt.close()

def generate_summary_report(test_results: Dict, symbol: str, days: int) -> None:
    """Tạo báo cáo tổng hợp kết quả kiểm thử"""
    report_path = f"{symbol}_enhanced_system_report.html"
    
    # Tạo nội dung báo cáo
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Báo cáo kiểm thử hệ thống nâng cao - {symbol}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            .section {{ margin: 30px 0; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .chart {{ max-width: 100%; height: auto; margin: 20px 0; }}
            .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>Báo cáo kiểm thử hệ thống nâng cao</h1>
        <div class="summary">
            <p><strong>Symbol:</strong> {symbol}</p>
            <p><strong>Thời gian kiểm thử:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Số ngày dữ liệu:</strong> {days}</p>
        </div>
        
        <div class="section">
            <h2>1. Enhanced Market Regime Detector</h2>
            <p>Kết quả phát hiện chế độ thị trường với 6 chế độ mới.</p>
            
            <h3>Phân bố chế độ thị trường:</h3>
            <table>
                <tr>
                    <th>Chế độ</th>
                    <th>Số lần</th>
                    <th>Phần trăm</th>
                    <th>Độ tin cậy TB</th>
                </tr>
    """
    
    # Thêm phân bố chế độ thị trường
    regime_counts = test_results.get('regime_detection', {}).get('regime_counts', {})
    avg_confidence = test_results.get('regime_detection', {}).get('avg_confidence', {})
    total_counts = sum(regime_counts.values()) if regime_counts else 0
    
    for regime, count in regime_counts.items():
        percentage = count / total_counts * 100 if total_counts > 0 else 0
        confidence = avg_confidence.get(regime, 0)
        html_content += f"""
                <tr>
                    <td>{regime}</td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                    <td>{confidence:.2f}</td>
                </tr>
        """
    
    html_content += f"""
            </table>
            
            <h3>Biểu đồ phát hiện chế độ:</h3>
            <img src="{symbol}_regime_detection.png" class="chart" alt="Biểu đồ phát hiện chế độ thị trường">
        </div>
        
        <div class="section">
            <h2>2. Order Flow Analyzer</h2>
            <p>Kết quả phân tích dòng lệnh và áp lực mua/bán.</p>
            
            <h3>Tín hiệu:</h3>
            <ul>
    """
    
    # Thêm thông tin order flow
    order_flow = test_results.get('order_flow', {})
    signals = order_flow.get('signals', {})
    
    html_content += f"""
                <li><strong>Buy Signal:</strong> {signals.get('buy_signal', False)}</li>
                <li><strong>Sell Signal:</strong> {signals.get('sell_signal', False)}</li>
                <li><strong>Neutral:</strong> {signals.get('neutral', True)}</li>
                <li><strong>Signal Strength:</strong> {signals.get('strength', 0):.2f}</li>
                <li><strong>Delta tích lũy:</strong> {order_flow.get('cumulative_delta', 0):.2f}</li>
                <li><strong>Chênh lệch lệnh:</strong> {order_flow.get('order_imbalance', 0):.2f}</li>
            </ul>
            
            <h3>Các mức giá quan trọng:</h3>
            <ul>
    """
    
    # Thêm các mức giá quan trọng
    key_levels = order_flow.get('key_levels', {})
    support_levels = key_levels.get('support', [])
    resistance_levels = key_levels.get('resistance', [])
    
    if support_levels:
        html_content += f"""
                <li><strong>Hỗ trợ:</strong> {', '.join([f'{level:.2f}' for level in support_levels])}</li>
        """
    
    if resistance_levels:
        html_content += f"""
                <li><strong>Kháng cự:</strong> {', '.join([f'{level:.2f}' for level in resistance_levels])}</li>
        """
    
    html_content += f"""
            </ul>
        </div>
        
        <div class="section">
            <h2>3. Volume Profile Analyzer</h2>
            <p>Kết quả phân tích cấu trúc khối lượng theo giá.</p>
    """
    
    # Thêm thông tin volume profile
    volume_profile = test_results.get('volume_profile', {})
    profile = volume_profile.get('profile', {})
    range_analysis = volume_profile.get('range_analysis', {})
    
    if profile:
        html_content += f"""
            <h3>Volume Profile:</h3>
            <ul>
                <li><strong>Point of Control (POC):</strong> {profile.get('poc', 0):.2f}</li>
                <li><strong>Value Area High:</strong> {profile.get('value_area', {}).get('high', 0):.2f}</li>
                <li><strong>Value Area Low:</strong> {profile.get('value_area', {}).get('low', 0):.2f}</li>
            </ul>
        """
    
    if range_analysis:
        html_content += f"""
            <h3>Phân tích vùng giao dịch:</h3>
            <ul>
                <li><strong>Giá hiện tại:</strong> {range_analysis.get('current_price', 0):.2f}</li>
                <li><strong>Vị trí:</strong> {range_analysis.get('position', 'unknown')}</li>
                <li><strong>Khả năng bứt phá lên:</strong> {range_analysis.get('breakout_potential', {}).get('up', False)}</li>
                <li><strong>Khả năng bứt phá xuống:</strong> {range_analysis.get('breakout_potential', {}).get('down', False)}</li>
            </ul>
            
            <h3>Biểu đồ Volume Profile:</h3>
            <img src="{volume_profile.get('chart_path', '')}" class="chart" alt="Volume Profile">
        """
    
    html_content += f"""
        </div>
        
        <div class="section">
            <h2>4. Adaptive Risk Allocator</h2>
            <p>Kết quả điều chỉnh mức rủi ro theo chế độ thị trường.</p>
            
            <h3>Mức rủi ro theo chế độ:</h3>
            <table>
                <tr>
                    <th>Chế độ</th>
                    <th>Mức rủi ro cơ sở (%)</th>
                    <th>Mức rủi ro thích ứng (%)</th>
                </tr>
    """
    
    # Thêm mức rủi ro theo chế độ
    risk_by_regime = test_results.get('adaptive_risk', {}).get('risk_by_regime', {})
    
    for regime, risks in risk_by_regime.items():
        base_risk = risks.get('base_regime_risk', 0)
        adaptive_risk = risks.get('adaptive_risk', 0)
        html_content += f"""
                <tr>
                    <td>{regime}</td>
                    <td>{base_risk:.2f}%</td>
                    <td>{adaptive_risk:.2f}%</td>
                </tr>
        """
    
    html_content += f"""
            </table>
            
            <h3>Đề xuất mức rủi ro:</h3>
            <ul>
    """
    
    # Thêm đề xuất mức rủi ro
    suggestions = test_results.get('adaptive_risk', {}).get('suggestions', {})
    
    for level, suggestion in suggestions.items():
        html_content += f"""
                <li><strong>{level.capitalize()}:</strong> {suggestion.get('suggested_risk_percentage', 0):.2f}%</li>
        """
    
    html_content += f"""
            </ul>
            
            <h3>Biểu đồ mức rủi ro thích ứng:</h3>
            <img src="{symbol}_adaptive_risk.png" class="chart" alt="Biểu đồ mức rủi ro thích ứng">
        </div>
        
        <div class="section">
            <h2>5. Regime Performance Analyzer</h2>
            <p>Phân tích hiệu suất giao dịch theo chế độ thị trường.</p>
            
            <h3>Hiệu suất tổng thể:</h3>
            <ul>
    """
    
    # Thêm hiệu suất tổng thể
    overall = test_results.get('regime_performance', {}).get('overall', {})
    
    html_content += f"""
                <li><strong>Tổng số lệnh:</strong> {overall.get('total_trades', 0)}</li>
                <li><strong>Tỷ lệ thắng:</strong> {overall.get('win_rate', 0):.2%}</li>
                <li><strong>Lợi nhuận TB:</strong> {overall.get('avg_profit', 0):.2f}%</li>
                <li><strong>Profit Factor:</strong> {overall.get('profit_factor', 0):.2f}</li>
            </ul>
            
            <h3>Hiệu suất theo chế độ:</h3>
            <table>
                <tr>
                    <th>Chế độ</th>
                    <th>Số lệnh</th>
                    <th>Tỷ lệ thắng</th>
                    <th>Lợi nhuận TB</th>
                    <th>Profit Factor</th>
                </tr>
    """
    
    # Thêm hiệu suất theo chế độ
    regime_performance = test_results.get('regime_performance', {}).get('regime_performance', {})
    
    for regime, perf in regime_performance.items():
        html_content += f"""
                <tr>
                    <td>{regime}</td>
                    <td>{perf.get('total_trades', 0)}</td>
                    <td>{perf.get('win_rate', 0):.2%}</td>
                    <td>{perf.get('avg_profit', 0):.2f}%</td>
                    <td>{perf.get('profit_factor', 0):.2f}</td>
                </tr>
        """
    
    html_content += f"""
            </table>
            
            <h3>Chế độ thị trường tốt nhất:</h3>
            <p>{', '.join(test_results.get('regime_performance', {}).get('best_regimes', []))}</p>
        </div>
        
        <div class="section">
            <p>Báo cáo được tạo lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    
    # Lưu báo cáo
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Đã tạo báo cáo tổng hợp tại: {report_path}")

def main():
    # Phân tích tham số dòng lệnh
    parser = argparse.ArgumentParser(description='Kiểm thử hệ thống nâng cao')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp tiền tệ (mặc định: BTCUSDT)')
    parser.add_argument('--days', type=int, default=30, help='Số ngày dữ liệu (mặc định: 30)')
    parser.add_argument('--report', action='store_true', help='Tạo báo cáo tổng hợp')
    
    args = parser.parse_args()
    
    logger.info(f"Bắt đầu kiểm thử hệ thống nâng cao cho {args.symbol}, {args.days} ngày")
    
    # Tải dữ liệu thị trường
    df = load_market_data(args.symbol, args.days)
    
    # Lưu kết quả kiểm thử
    test_results = {}
    
    # Kiểm thử Enhanced Market Regime Detector
    test_results['regime_detection'] = test_enhanced_market_regime_detector(df, args.symbol)
    
    # Kiểm thử Order Flow Analyzer
    test_results['order_flow'] = test_order_flow_analyzer(df, args.symbol)
    
    # Kiểm thử Volume Profile Analyzer
    test_results['volume_profile'] = test_volume_profile_analyzer(df, args.symbol)
    
    # Kiểm thử Adaptive Risk Allocator
    test_results['adaptive_risk'] = test_adaptive_risk_allocator(df, args.symbol)
    
    # Kiểm thử Regime Performance Analyzer
    test_results['regime_performance'] = test_regime_performance_analyzer(df, args.symbol)
    
    # Tạo báo cáo tổng hợp nếu yêu cầu
    if args.report:
        generate_summary_report(test_results, args.symbol, args.days)
    
    logger.info("Kiểm thử hoàn tất!")

if __name__ == "__main__":
    main()