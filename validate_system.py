#!/usr/bin/env python3
"""
Script kiểm tra và xác thực các thành phần chính của hệ thống bot giao dịch

Script này thực hiện kiểm tra chi tiết:
1. Xác nhận các module chính hoạt động đúng
2. Kiểm tra tích hợp giữa các thành phần
3. Xác thực chức năng của bot với dữ liệu thực tế
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system_validation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("system_validation")

# Import các module cần xác thực
try:
    # Import các thành phần chính
    from position_sizing_enhanced import PythagoreanPositionSizer, MonteCarloRiskAnalyzer
    from fractal_market_regime import FractalMarketRegimeDetector
    from trading_time_optimizer import TradingTimeOptimizer
    
    # Module khác nếu cần
    
    logger.info("✅ Import tất cả module thành công")
except ImportError as e:
    logger.error(f"❌ Lỗi import module: {e}")
    sys.exit(1)

def generate_test_data(days=30, samples_per_day=24):
    """Tạo dữ liệu thử nghiệm cho quá trình xác thực"""
    logger.info(f"Tạo dữ liệu thử nghiệm: {days} ngày với {samples_per_day} mẫu mỗi ngày")
    
    # Tạo index thời gian
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, periods=days * samples_per_day)
    
    # Tạo DataFrame
    df = pd.DataFrame(index=dates)
    
    # Tạo giá
    price = 50000
    prices = []
    for i in range(len(dates)):
        # Thêm nhiễu ngẫu nhiên với xu hướng nhẹ
        price_change = np.random.normal(0.01, 0.5)  # Trung bình tăng 0.01%, độ lệch chuẩn 0.5%
        price *= (1 + price_change / 100)
        prices.append(price)
    
    df['close'] = prices
    
    # Tạo giá mở, cao, thấp
    df['open'] = df['close'].shift(1)
    df.loc[df.index[0], 'open'] = df['close'].iloc[0] * 0.999
    
    # Tạo giá cao/thấp
    df['high'] = df['close'] * (1 + np.random.uniform(0.001, 0.01, len(df)))
    df['low'] = df['close'] * (1 - np.random.uniform(0.001, 0.01, len(df)))
    
    # Tạo khối lượng
    df['volume'] = np.random.uniform(100, 1000, len(df))
    
    # Tính các chỉ báo kỹ thuật
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    # Bollinger Bands
    df['sma20'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma20'] + (std * 2)
    df['lower_band'] = df['sma20'] - (std * 2)
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(window=14).mean()
    
    logger.info(f"✅ Đã tạo {len(df)} mẫu dữ liệu thử nghiệm")
    return df

def generate_sample_trades(df, num_trades=50):
    """Tạo lịch sử giao dịch mẫu"""
    logger.info(f"Tạo {num_trades} giao dịch mẫu")
    
    trades = []
    
    # Chọn ngẫu nhiên các điểm thời gian từ DataFrame
    indices = np.random.choice(range(len(df) - 24), num_trades, replace=False)
    
    for i, idx in enumerate(indices):
        # Giá vào lệnh
        entry_time = df.index[idx]
        entry_price = df['close'].iloc[idx]
        
        # Giá thoát lệnh (mô phỏng 1-24 giờ sau)
        exit_idx = idx + np.random.randint(1, 24)
        if exit_idx >= len(df):
            exit_idx = len(df) - 1
            
        exit_time = df.index[exit_idx]
        exit_price = df['close'].iloc[exit_idx]
        
        # Phía giao dịch
        side = "buy" if np.random.random() > 0.5 else "sell"
        
        # Tính P&L
        if side == "buy":
            pnl = exit_price - entry_price
        else:
            pnl = entry_price - exit_price
            
        # Tính % P&L
        pnl_pct = pnl / entry_price * 100
        
        # Tạo giao dịch
        trade = {
            "id": i,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "exit_time": exit_time,
            "exit_price": exit_price,
            "side": side,
            "size": np.random.uniform(0.1, 1.0),
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "symbol": "BTCUSDT"
        }
        
        trades.append(trade)
    
    logger.info(f"✅ Đã tạo {len(trades)} giao dịch mẫu")
    return trades

def test_pythagorean_position_sizer(trades, balance=10000.0):
    """Kiểm tra chức năng của Pythagorean Position Sizer"""
    logger.info("=== Bắt đầu kiểm tra Pythagorean Position Sizer ===")
    
    try:
        # Khởi tạo Position Sizer
        sizer = PythagoreanPositionSizer(
            trade_history=trades,
            account_balance=balance,
            risk_percentage=1.0
        )
        
        # Lấy win rate và profit factor
        win_rate = sizer.calculate_win_rate()
        profit_factor = sizer.calculate_profit_factor()
        
        logger.info(f"Win rate: {win_rate:.2f}")
        logger.info(f"Profit factor: {profit_factor:.2f}")
        
        # Kiểm tra tính toán kích thước vị thế
        current_price = 50000.0
        entry_price = 50000.0
        stop_loss_price = 49000.0  # 2% stop loss
        
        position_size = sizer.calculate_position_size(
            current_price=current_price,
            account_balance=balance,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price
        )
        
        logger.info(f"Kích thước vị thế (balance ${balance:.2f}, risk 1%): {position_size:.6f}")
        
        # Kiểm tra với các giá trị win rate và profit factor khác nhau
        test_values = [
            (0.3, 0.5),  # Tình huống xấu
            (0.5, 1.0),  # Break-even
            (0.7, 2.0),  # Tình huống tốt
            (0.9, 5.0)   # Tình huống rất tốt
        ]
        
        for wr, pf in test_values:
            # Tạo một đối tượng sizer mới với các giá trị cụ thể
            test_trades = trades.copy()
            # Thêm giao dịch giả để có win rate và profit factor mong muốn
            num_trades = len(test_trades)
            if num_trades > 0:
                # Giả lập win_rate và profit_factor
                test_sizer = PythagoreanPositionSizer(
                    trade_history=test_trades,
                    account_balance=balance,
                    risk_percentage=1.0
                )
                # Ghi đè phương thức tính toán để trả về giá trị cố định
                test_sizer.calculate_win_rate = lambda: wr
                test_sizer.calculate_profit_factor = lambda: pf
                
                # Tính kích thước vị thế
                test_size = test_sizer.calculate_position_size(
                    current_price=current_price,
                    account_balance=balance,
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price
                )
                logger.info(f"Win rate={wr:.1f}, profit_factor={pf:.1f}: size={test_size:.2f}")
        
        logger.info("✅ Kiểm tra Pythagorean Position Sizer thành công")
        return True
    except Exception as e:
        logger.error(f"❌ Lỗi kiểm tra Pythagorean Position Sizer: {e}")
        return False

def test_monte_carlo_analyzer(trades):
    """Kiểm tra chức năng của Monte Carlo Risk Analyzer"""
    logger.info("=== Bắt đầu kiểm tra Monte Carlo Risk Analyzer ===")
    
    try:
        # Khởi tạo analyzer
        analyzer = MonteCarloRiskAnalyzer(
            trade_history=trades,
            default_risk=1.0
        )
        
        # Chạy phân tích Monte Carlo
        suggested_risk = analyzer.analyze(
            confidence_level=0.95,
            simulations=1000,
            sequence_length=20
        )
        
        logger.info(f"Mức rủi ro đề xuất (tin cậy 95%): {suggested_risk:.2f}%")
        
        # Lấy phân phối drawdown
        drawdown_dist = analyzer.get_drawdown_distribution(simulations=1000)
        
        if 'percentiles' in drawdown_dist:
            for level, value in drawdown_dist['percentiles'].items():
                logger.info(f"Drawdown ở mức {level}: {value:.2f}%")
        
        # Lấy các mức rủi ro ở các mức tin cậy khác nhau
        risk_levels = analyzer.get_risk_levels()
        
        for level, risk in risk_levels.items():
            logger.info(f"Rủi ro ở mức tin cậy {level}: {risk:.2f}%")
        
        logger.info("✅ Kiểm tra Monte Carlo Risk Analyzer thành công")
        return True
    except Exception as e:
        logger.error(f"❌ Lỗi kiểm tra Monte Carlo Risk Analyzer: {e}")
        return False

def test_fractal_market_regime_detector(df):
    """Kiểm tra chức năng của Fractal Market Regime Detector"""
    logger.info("=== Bắt đầu kiểm tra Fractal Market Regime Detector ===")
    
    try:
        # Khởi tạo detector
        detector = FractalMarketRegimeDetector(lookback_periods=50)
        
        # Kiểm tra từng chế độ thị trường
        market_regimes = []
        
        # Chỉ kiểm tra mỗi 10 mẫu để tăng tốc độ
        for i in range(50, len(df), 10):
            # Lấy dữ liệu gần đây
            recent_data = df.iloc[:i].copy()
            
            # Phát hiện chế độ thị trường
            regime_result = detector.detect_regime(recent_data)
            
            regime = regime_result['regime']
            confidence = regime_result['confidence']
            
            market_regimes.append({
                'time': df.index[i-1],
                'regime': regime,
                'confidence': confidence
            })
            
            logger.info(f"Thời điểm {df.index[i-1]}: {regime} (Độ tin cậy: {confidence:.2f})")
        
        # Kiểm tra các chế độ thị trường đã phát hiện
        regime_counts = {}
        for entry in market_regimes:
            regime = entry['regime']
            if regime in regime_counts:
                regime_counts[regime] += 1
            else:
                regime_counts[regime] = 1
        
        logger.info("Phân bố chế độ thị trường:")
        for regime, count in regime_counts.items():
            logger.info(f"- {regime}: {count} lần ({count / len(market_regimes) * 100:.1f}%)")
        
        # Kiểm tra chiến lược phù hợp
        for regime in set(entry['regime'] for entry in market_regimes):
            # Giả lập thiết lập chế độ thị trường
            detector.current_regime = regime
            
            # Lấy chiến lược phù hợp
            strategies = detector.get_suitable_strategies()
            
            logger.info(f"Chiến lược cho chế độ {regime}:")
            for strategy, weight in strategies.items():
                logger.info(f"- {strategy}: {weight:.1f}")
            
            # Lấy điều chỉnh rủi ro
            risk_adjustment = detector.get_risk_adjustment()
            logger.info(f"Điều chỉnh rủi ro cho chế độ {regime}: {risk_adjustment:.2f}")
        
        logger.info("✅ Kiểm tra Fractal Market Regime Detector thành công")
        return True
    except Exception as e:
        logger.error(f"❌ Lỗi kiểm tra Fractal Market Regime Detector: {e}")
        return False

def test_trading_time_optimizer(trades):
    """Kiểm tra chức năng của Trading Time Optimizer"""
    logger.info("=== Bắt đầu kiểm tra Trading Time Optimizer ===")
    
    try:
        # Khởi tạo optimizer
        optimizer = TradingTimeOptimizer(
            trade_history=trades,
            time_segments=24
        )
        
        # Cập nhật phân tích hiệu suất
        optimizer.update_performance_analysis()
        
        # Lấy các giờ tối ưu
        optimal_hours = optimizer.get_optimal_trading_hours()
        
        logger.info("Các giờ tối ưu:")
        for hour in optimal_hours:
            logger.info(f"- {hour}:00")
        
        # Lấy các ngày tối ưu
        optimal_days = optimizer.get_optimal_trading_days()
        day_names = [optimizer.DAY_NAMES[day] for day in optimal_days]
        
        logger.info("Các ngày tối ưu:")
        for day in day_names:
            logger.info(f"- {day}")
        
        # Kiểm tra xem có nên giao dịch vào thời điểm hiện tại không
        now = datetime.now()
        should_trade, reason = optimizer.should_trade_now(now)
        
        logger.info(f"Nên giao dịch hiện tại: {should_trade}, Lý do: {reason}")
        
        # Kiểm tra các thời điểm khác nhau trong ngày
        for hour in range(0, 24, 4):
            test_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            should_trade, reason = optimizer.should_trade_now(test_time)
            logger.info(f"Giờ {hour}:00: Nên giao dịch: {should_trade}, Lý do: {reason}")
        
        # Lấy điều chỉnh rủi ro theo thời gian
        risk_adjustment = optimizer.get_risk_adjustment(now)
        logger.info(f"Điều chỉnh rủi ro tại thời điểm hiện tại: {risk_adjustment:.2f}")
        
        logger.info("✅ Kiểm tra Trading Time Optimizer thành công")
        return True
    except Exception as e:
        logger.error(f"❌ Lỗi kiểm tra Trading Time Optimizer: {e}")
        return False

def test_integration():
    """Kiểm tra tích hợp của tất cả các thành phần"""
    logger.info("=== Bắt đầu kiểm tra tích hợp các thành phần ===")
    
    try:
        # Tạo dữ liệu thử nghiệm
        df = generate_test_data(days=30)
        trades = generate_sample_trades(df, num_trades=50)
        
        # Khởi tạo các thành phần
        regime_detector = FractalMarketRegimeDetector(lookback_periods=50)
        pythag_sizer = PythagoreanPositionSizer(
            trade_history=trades,
            account_balance=10000.0, 
            risk_percentage=1.0
        )
        mc_analyzer = MonteCarloRiskAnalyzer(
            trade_history=trades,
            default_risk=1.0
        )
        time_optimizer = TradingTimeOptimizer(
            trade_history=trades,
            time_segments=24
        )
        
        # Mô phỏng quá trình giao dịch
        logger.info("Mô phỏng quá trình giao dịch tích hợp:")
        
        # Giả lập điểm vào lệnh
        recent_data = df.iloc[-100:].copy()
        current_price = df['close'].iloc[-1]
        current_time = df.index[-1]
        
        # 1. Phát hiện chế độ thị trường
        regime_result = regime_detector.detect_regime(recent_data)
        regime = regime_result['regime']
        confidence = regime_result['confidence']
        
        logger.info(f"Chế độ thị trường: {regime} (Độ tin cậy: {confidence:.2f})")
        
        # 2. Kiểm tra thời gian giao dịch
        time_optimizer.update_performance_analysis()
        should_trade, reason = time_optimizer.should_trade_now(current_time)
        
        logger.info(f"Nên giao dịch thời điểm hiện tại: {should_trade}, Lý do: {reason}")
        
        # 3. Tính toán mức rủi ro từ Monte Carlo
        suggested_risk = mc_analyzer.analyze(
            confidence_level=0.95,
            simulations=1000,
            sequence_length=20
        )
        
        logger.info(f"Mức rủi ro đề xuất từ Monte Carlo: {suggested_risk:.2f}%")
        
        # 4. Điều chỉnh rủi ro theo các thành phần
        regime_adjustment = regime_detector.get_risk_adjustment()
        time_adjustment = time_optimizer.get_risk_adjustment(current_time)
        
        final_risk = suggested_risk * regime_adjustment * time_adjustment
        final_risk = max(0.1, min(final_risk, 3.0))  # Giới hạn 0.1% - 3.0%
        
        logger.info(f"Điều chỉnh rủi ro theo chế độ thị trường: {regime_adjustment:.2f}")
        logger.info(f"Điều chỉnh rủi ro theo thời gian: {time_adjustment:.2f}")
        logger.info(f"Mức rủi ro cuối cùng: {final_risk:.2f}%")
        
        # 5. Tính toán kích thước vị thế
        pythag_sizer.max_risk_percentage = final_risk
        
        # Giả lập stop loss (2% dưới giá hiện tại)
        stop_loss_price = current_price * 0.98
        
        position_size = pythag_sizer.calculate_position_size(
            current_price=current_price,
            account_balance=10000.0,
            entry_price=current_price,
            stop_loss_price=stop_loss_price
        )
        
        logger.info(f"Kích thước vị thế cuối cùng: {position_size:.6f}")
        
        logger.info("✅ Kiểm tra tích hợp các thành phần thành công")
        return True
    except Exception as e:
        logger.error(f"❌ Lỗi kiểm tra tích hợp: {e}")
        return False

def validate_system():
    """Chạy tất cả các bài kiểm tra xác thực"""
    logger.info("=== BẮT ĐẦU XÁC THỰC HỆ THỐNG ===")
    
    # Tạo dữ liệu thử nghiệm
    df = generate_test_data(days=30)
    trades = generate_sample_trades(df, num_trades=50)
    
    # Chạy các bài kiểm tra
    position_sizer_test = test_pythagorean_position_sizer(trades)
    monte_carlo_test = test_monte_carlo_analyzer(trades)
    regime_detector_test = test_fractal_market_regime_detector(df)
    time_optimizer_test = test_trading_time_optimizer(trades)
    integration_test = test_integration()
    
    # Tổng hợp kết quả
    logger.info("\n=== KẾT QUẢ XÁC THỰC HỆ THỐNG ===")
    logger.info(f"Pythagorean Position Sizer: {'✅ PASSED' if position_sizer_test else '❌ FAILED'}")
    logger.info(f"Monte Carlo Risk Analyzer: {'✅ PASSED' if monte_carlo_test else '❌ FAILED'}")
    logger.info(f"Fractal Market Regime Detector: {'✅ PASSED' if regime_detector_test else '❌ FAILED'}")
    logger.info(f"Trading Time Optimizer: {'✅ PASSED' if time_optimizer_test else '❌ FAILED'}")
    logger.info(f"Tích hợp các thành phần: {'✅ PASSED' if integration_test else '❌ FAILED'}")
    
    all_passed = all([position_sizer_test, monte_carlo_test, regime_detector_test, time_optimizer_test, integration_test])
    logger.info(f"\nKết quả chung: {'✅ TẤT CẢ CÁC KIỂM TRA ĐỀU THÀNH CÔNG' if all_passed else '❌ MỘT SỐ KIỂM TRA THẤT BẠI'}")
    
    return all_passed

if __name__ == "__main__":
    success = validate_system()
    sys.exit(0 if success else 1)