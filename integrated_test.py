"""
Script kiểm tra kết hợp các tính năng nâng cao mới của bot giao dịch

Script này kết hợp và kiểm thử các module mới đã được phát triển:
- PythagoreanPositionSizer (vị thế dựa trên công thức Pythagoras)
- MonteCarloRiskAnalyzer (phân tích rủi ro Monte Carlo)
- FractalMarketRegimeDetector (phát hiện chế độ thị trường tiên tiến)
- TradingTimeOptimizer (tối ưu hóa thời gian giao dịch)

Các thành phần này có thể được tích hợp vào hệ thống bot chính.
"""

import logging
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

# Import các module mới
from position_sizing_enhanced import PythagoreanPositionSizer, MonteCarloRiskAnalyzer
from fractal_market_regime import FractalMarketRegimeDetector
from trading_time_optimizer import TradingTimeOptimizer

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("integrated_test")

def generate_sample_price_data(days=100):
    """
    Tạo dữ liệu giá mẫu với các chế độ thị trường khác nhau
    
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLCV
    """
    # Tạo index từ ngày hiện tại trở về trước
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_range = pd.date_range(start=start_date, end=end_date, freq='1h')
    
    # Tạo dữ liệu giá
    prices = np.zeros(len(date_range))
    prices[0] = 50000  # Giá ban đầu $50k
    
    # Thêm xu hướng và nhiễu
    for i in range(1, len(prices)):
        # Thay đổi chế độ thị trường
        if i < len(prices) // 4:  # 1/4 đầu: Trending up
            trend = 0.05
            volatility = 0.5
        elif i < len(prices) // 2:  # 1/4 tiếp theo: Ranging
            trend = 0.0
            volatility = 0.3
        elif i < 3 * len(prices) // 4:  # 1/4 tiếp theo: Volatile
            trend = -0.01
            volatility = 1.2
        else:  # 1/4 cuối: Quiet
            trend = 0.01
            volatility = 0.2
            
        # Tạo giá
        price_change = np.random.normal(trend, volatility)
        prices[i] = max(1, prices[i-1] * (1 + price_change / 100))
    
    # Tạo DataFrame
    df = pd.DataFrame(index=date_range)
    df['close'] = prices
    
    # Tạo OHLCV
    df['open'] = df['close'].shift(1)
    df['open'].iloc[0] = df['close'].iloc[0] * 0.99
    
    # High & Low - thêm nhiễu ngẫu nhiên
    random_factors = np.random.uniform(0.001, 0.01, len(df))
    df['high'] = df['close'] * (1 + random_factors)
    df['low'] = df['close'] * (1 - random_factors)
    
    # Thêm volume
    df['volume'] = np.random.uniform(100, 1000, len(df)) * df['close'] / 1000
    
    return df

def generate_sample_trades(prices_df, num_trades=50):
    """
    Tạo lịch sử giao dịch mẫu dựa trên dữ liệu giá
    
    Args:
        prices_df (pd.DataFrame): DataFrame chứa dữ liệu giá
        num_trades (int): Số giao dịch cần tạo
        
    Returns:
        List[Dict]: Danh sách các giao dịch mẫu
    """
    trades = []
    
    # Lấy dữ liệu giá và thời gian
    dates = prices_df.index.tolist()
    closes = prices_df['close'].tolist()
    
    # Sinh ngẫu nhiên các giao dịch
    for i in range(num_trades):
        # Chọn ngẫu nhiên thời gian vào lệnh
        entry_idx = random.randint(0, len(dates) - 2)
        entry_time = dates[entry_idx]
        entry_price = closes[entry_idx]
        
        # Chọn ngẫu nhiên thời gian thoát lệnh (sau thời gian vào lệnh)
        exit_idx = random.randint(entry_idx + 1, min(entry_idx + 48, len(dates) - 1))
        exit_time = dates[exit_idx]
        exit_price = closes[exit_idx]
        
        # Tính P&L
        pnl = exit_price - entry_price
        pnl_pct = pnl / entry_price * 100
        
        # Phần trăm thành công/thất bại ngẫu nhiên nếu cần
        trade = {
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'symbol': 'BTCUSDT',
            'position_size': 1.0
        }
        
        trades.append(trade)
        
    return trades

def test_integrated_features():
    """
    Kiểm thử tích hợp các tính năng mới
    """
    logger.info("Bắt đầu kiểm thử tích hợp các tính năng nâng cao")
    
    # 1. Tạo dữ liệu mẫu
    logger.info("Tạo dữ liệu mẫu...")
    price_df = generate_sample_price_data(days=180)
    trades = generate_sample_trades(price_df, num_trades=100)
    
    # 2. Khởi tạo các thành phần
    logger.info("Khởi tạo các thành phần...")
    
    # Position Sizing với Pythagoras
    pythag_sizer = PythagoreanPositionSizer(
        trade_history=trades,
        account_balance=10000.0,
        risk_percentage=1.0
    )
    
    # Monte Carlo Risk Analyzer
    mc_analyzer = MonteCarloRiskAnalyzer(
        trade_history=trades,
        default_risk=1.0
    )
    
    # Fractal Market Regime Detector
    regime_detector = FractalMarketRegimeDetector(
        lookback_periods=100
    )
    
    # Trading Time Optimizer
    time_optimizer = TradingTimeOptimizer(
        trade_history=trades,
        time_segments=24
    )
    
    # 3. Kiểm thử phát hiện chế độ thị trường
    logger.info("Kiểm thử phát hiện chế độ thị trường...")
    
    # Lấy dữ liệu gần đây nhất
    recent_data = price_df.iloc[-100:]
    
    # Phát hiện chế độ thị trường
    regime_result = regime_detector.detect_regime(recent_data)
    logger.info(f"Chế độ thị trường hiện tại: {regime_result['regime']} (Độ tin cậy: {regime_result['confidence']:.2f})")
    
    # Lấy chiến lược phù hợp
    suitable_strategies = regime_detector.get_suitable_strategies()
    logger.info(f"Chiến lược phù hợp: {suitable_strategies}")
    
    # Lấy điều chỉnh rủi ro
    risk_adjustment = regime_detector.get_risk_adjustment()
    logger.info(f"Điều chỉnh rủi ro: {risk_adjustment:.2f}")
    
    # 4. Kiểm thử phân tích Monte Carlo
    logger.info("Kiểm thử phân tích Monte Carlo...")
    suggested_risk = mc_analyzer.analyze(
        confidence_level=0.95,
        simulations=1000,
        sequence_length=20
    )
    logger.info(f"Đề xuất % rủi ro từ Monte Carlo: {suggested_risk:.2f}%")
    
    # Lấy phân phối drawdown
    drawdown_dist = mc_analyzer.get_drawdown_distribution(simulations=1000)
    logger.info(f"Phân phối drawdown (percentiles): {drawdown_dist['percentiles']}")
    
    # 5. Kiểm thử tối ưu hóa thời gian giao dịch
    logger.info("Kiểm thử tối ưu hóa thời gian giao dịch...")
    
    # Lấy các giờ tối ưu
    optimal_hours = time_optimizer.get_optimal_trading_hours()
    logger.info(f"Các giờ tối ưu cho giao dịch: {optimal_hours}")
    
    # Lấy các ngày tối ưu
    optimal_days = time_optimizer.get_optimal_trading_days()
    day_names = [time_optimizer.DAY_NAMES[day] for day in optimal_days]
    logger.info(f"Các ngày tối ưu cho giao dịch: {day_names}")
    
    # Kiểm tra thời gian hiện tại
    now = datetime.now()
    should_trade, reason = time_optimizer.should_trade_now(now)
    logger.info(f"Nên giao dịch bây giờ: {should_trade}, Lý do: {reason}")
    
    # 6. Kiểm thử PythagoreanPositionSizer
    logger.info("Kiểm thử PythagoreanPositionSizer...")
    
    # Tính toán kích thước vị thế
    current_price = price_df['close'].iloc[-1]
    entry_price = current_price
    stop_loss_price = current_price * 0.98  # 2% dưới giá hiện tại
    
    position_size = pythag_sizer.calculate_position_size(
        current_price=current_price,
        account_balance=10000.0,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price
    )
    
    logger.info(f"Kích thước vị thế Pythagoras: {position_size:.2f}")
    
    # 7. Tích hợp tất cả các thành phần
    logger.info("Tích hợp tất cả các thành phần...")
    
    # a) Phát hiện chế độ thị trường
    regime = regime_detector.detect_regime(recent_data)['regime']
    
    # b) Xác định nên giao dịch theo thời gian không
    should_trade, _ = time_optimizer.should_trade_now()
    
    # c) Nếu nên giao dịch, tính toán % rủi ro dựa trên Monte Carlo
    if should_trade:
        # % rủi ro từ Monte Carlo
        mc_risk = mc_analyzer.analyze(confidence_level=0.95)
        
        # Điều chỉnh theo chế độ thị trường
        regime_adjusted_risk = regime_detector.get_risk_adjustment()
        
        # Điều chỉnh theo thời gian
        time_adjusted_risk = time_optimizer.get_risk_adjustment(now)
        
        # Kết hợp các điều chỉnh
        final_risk_percentage = mc_risk * regime_adjusted_risk * time_adjusted_risk
        
        # Giới hạn % rủi ro
        final_risk_percentage = max(0.1, min(final_risk_percentage, 3.0))
        
        logger.info(f"% rủi ro tích hợp: {final_risk_percentage:.2f}%")
        
        # d) Tính toán kích thước vị thế
        pythag_sizer.max_risk_percentage = final_risk_percentage
        
        adjusted_position_size = pythag_sizer.calculate_position_size(
            current_price=current_price,
            account_balance=10000.0,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price
        )
        
        logger.info(f"Kích thước vị thế tích hợp: {adjusted_position_size:.2f}")
    else:
        logger.info("Không nên giao dịch lúc này theo phân tích thời gian")
    
    # Vẽ biểu đồ kết quả
    try:
        # Vẽ biểu đồ giá và chế độ thị trường
        plt.figure(figsize=(14, 10))
        
        # Biểu đồ giá
        plt.subplot(2, 1, 1)
        plt.plot(price_df.index, price_df['close'])
        plt.title('Giá BTC/USD và Chế độ thị trường')
        plt.ylabel('Giá ($)')
        plt.grid(True)
        
        # Biểu đồ phân phối drawdown
        plt.subplot(2, 1, 2)
        if 'drawdowns' in drawdown_dist and len(drawdown_dist['drawdowns']) > 0:
            plt.hist(drawdown_dist['drawdowns'], bins=30, alpha=0.7)
            plt.axvline(drawdown_dist['percentiles']['95%'], color='r', linestyle='--', label='95% VaR')
            plt.title('Phân phối Drawdown từ Monte Carlo')
            plt.xlabel('Drawdown (%)')
            plt.ylabel('Tần suất')
            plt.legend()
            plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('integrated_test_results.png')
        logger.info("Đã lưu biểu đồ kết quả vào 'integrated_test_results.png'")
        
    except Exception as e:
        logger.error(f"Không thể vẽ biểu đồ: {e}")
    
    # Tạo báo cáo tóm tắt
    logger.info("\n" + "="*50)
    logger.info("BÁO CÁO TÓM TẮT TÍCH HỢP")
    logger.info("="*50)
    logger.info(f"1. Chế độ thị trường: {regime}")
    logger.info(f"2. Đề xuất % rủi ro từ Monte Carlo: {suggested_risk:.2f}%")
    logger.info(f"3. Các giờ tối ưu cho giao dịch: {optimal_hours}")
    logger.info(f"4. Các ngày tối ưu cho giao dịch: {day_names}")
    logger.info(f"5. Kích thước vị thế cơ bản: {position_size:.2f}")
    logger.info("="*50)
    
    return {
        "regime": regime,
        "suggested_risk": suggested_risk,
        "optimal_hours": optimal_hours,
        "optimal_days": day_names,
        "position_size": position_size,
        "should_trade": should_trade
    }

if __name__ == "__main__":
    results = test_integrated_features()
    print("\nKết quả kiểm thử tích hợp:")
    for key, value in results.items():
        print(f"- {key}: {value}")