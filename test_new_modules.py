"""
Test New Modules - Kiểm tra các module mới đã triển khai

Script này sẽ kiểm tra các module mới đã triển khai:
1. Order Flow Indicators
2. Volume Profile Analyzer 
3. Adaptive Exit Strategy
4. Partial Take Profit Manager

Mỗi module sẽ được kiểm tra với dữ liệu mẫu tạo ra và hiển thị kết quả.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Any

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_new_modules.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('test_new_modules')

# Import các module đã triển khai
from order_flow_indicators import OrderFlowAnalyzer
from volume_profile_analyzer_extended import VolumeProfileAnalyzer
from adaptive_exit_strategy import AdaptiveExitStrategy
from partial_take_profit_manager import PartialTakeProfitManager

# Tạo thư mục lưu kết quả test
os.makedirs("test_results", exist_ok=True)


def create_sample_data(periods: int = 100, volatility: float = 0.02) -> pd.DataFrame:
    """
    Tạo dữ liệu mẫu cho việc kiểm tra.
    
    Args:
        periods (int): Số lượng chu kỳ
        volatility (float): Độ biến động
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLCV
    """
    # Tạo thời gian
    dates = [datetime.now() - timedelta(hours=i) for i in range(periods, 0, -1)]
    
    # Tạo giá theo mô hình random walk
    np.random.seed(42)  # Đảm bảo kết quả có thể tái tạo
    returns = np.random.normal(0, volatility, periods)
    
    # Tạo các vùng thị trường khác nhau
    # 0-25: Xu hướng tăng
    # 25-40: Tích lũy hẹp
    # 40-60: Tích lũy rộng
    # 60-80: Biến động mạnh
    # 80-100: Xu hướng giảm
    
    returns[0:25] = np.abs(returns[0:25]) * 1.2  # Xu hướng tăng
    returns[25:40] = returns[25:40] * 0.3  # Tích lũy hẹp
    returns[40:60] = returns[40:60] * 0.8  # Tích lũy rộng
    returns[60:80] = returns[60:80] * 2.0  # Biến động mạnh
    returns[80:100] = -np.abs(returns[80:100]) * 1.1  # Xu hướng giảm
    
    # Tạo giá
    price = 50000  # Giá ban đầu
    prices = [price]
    
    for ret in returns:
        price *= (1 + ret)
        prices.append(price)
    
    close_prices = prices[1:]  # Bỏ giá đầu tiên
    
    # Tạo OHLC từ giá đóng cửa
    open_prices = [close_prices[0]] + close_prices[:-1]
    high_prices = [c + abs(o-c) * np.random.uniform(1.0, 1.5) for o, c in zip(open_prices, close_prices)]
    low_prices = [c - abs(o-c) * np.random.uniform(1.0, 1.5) for o, c in zip(open_prices, close_prices)]
    
    # Tạo khối lượng - tăng cao ở vùng xu hướng và biến động
    volumes = np.random.normal(1000, 200, periods)
    volumes[0:25] *= 1.5  # Khối lượng cao ở xu hướng tăng
    volumes[60:80] *= 2.0  # Khối lượng cao ở vùng biến động
    volumes[80:100] *= 1.3  # Khối lượng cao ở xu hướng giảm
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=dates)
    
    # Thêm một số chỉ báo cơ bản để giả lập dữ liệu đầy đủ
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
    
    # Bollinger Bands
    df['SMA20'] = df['close'].rolling(window=20).mean()
    std20 = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA20'] + (std20 * 2)
    df['BB_Lower'] = df['SMA20'] - (std20 * 2)
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['SMA20']
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = true_ranges.rolling(14).mean()
    
    # Thêm chỉ báo cho biến động
    df['Price_Volatility'] = df['close'].pct_change().rolling(window=20).std() * np.sqrt(20)
    
    # Đảm bảo không có giá trị NaN
    df = df.fillna(method='bfill').fillna(method='ffill')
    
    return df


def test_order_flow_indicators(df: pd.DataFrame) -> None:
    """
    Kiểm tra Order Flow Indicators.
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV
    """
    logger.info("Kiểm tra Order Flow Indicators...")
    
    try:
        # Khởi tạo Order Flow Analyzer
        order_flow = OrderFlowAnalyzer()
        
        # Mô phỏng dữ liệu order flow từ dữ liệu nến
        order_flow.simulate_from_candle_data("BTCUSDT", df)
        
        # Lấy dữ liệu mô phỏng làm enhanced_df
        enhanced_df = df.copy()
        
        # Kiểm tra các chỉ báo đã được thêm
        new_columns = set(enhanced_df.columns) - set(df.columns)
        logger.info(f"Đã thêm {len(new_columns)} chỉ báo mới: {new_columns}")
        
        # Lấy tín hiệu giao dịch
        signals = order_flow.get_order_flow_signals("BTCUSDT")
        
        logger.info(f"Order Flow Bias: {signals.get('signals', {}).get('buy_signal', False)}")
        logger.info(f"Buy Signal: {signals.get('signals', {}).get('buy_signal', False)}")
        logger.info(f"Sell Signal: {signals.get('signals', {}).get('sell_signal', False)}")
        
        # Tạo biểu đồ
        chart_path = order_flow.visualize_delta_flow("BTCUSDT")
        logger.info(f"Đã tạo biểu đồ tại: {chart_path}")
        
        print("\n==== ORDER FLOW INDICATORS ====")
        print(f"- Đã thêm {len(new_columns)} chỉ báo mới")
        print(f"- Order Flow Buy Signal: {signals.get('signals', {}).get('buy_signal', False)}")
        print(f"- Order Flow Sell Signal: {signals.get('signals', {}).get('sell_signal', False)}")
        print(f"- Chart: {chart_path}")
        print("===============================\n")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Order Flow Indicators: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_volume_profile_analyzer(df: pd.DataFrame) -> None:
    """
    Kiểm tra Volume Profile Analyzer.
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV
    """
    logger.info("Kiểm tra Volume Profile Analyzer...")
    
    try:
        # Khởi tạo Volume Profile Analyzer
        vp_analyzer = VolumeProfileAnalyzer()
        
        # Tính Volume Profile
        profile = vp_analyzer.calculate_volume_profile(df, "BTCUSDT", "session")
        
        logger.info(f"POC: {profile.get('poc')}")
        logger.info(f"Value Area: {profile.get('value_area')}")
        logger.info(f"Secondary POCs: {profile.get('volume_nodes', [])}")
        
        # Tìm vùng hỗ trợ/kháng cự
        sr_zones = vp_analyzer.identify_support_resistance(df, "BTCUSDT")
        
        support_count = len(sr_zones.get('support_levels', []))
        resistance_count = len(sr_zones.get('resistance_levels', []))
        
        logger.info(f"Support Zones: {support_count}")
        logger.info(f"Resistance Zones: {resistance_count}")
        
        # Phân tích mẫu hình Volume
        patterns = vp_analyzer.analyze_trading_range(df, "BTCUSDT")
        
        pattern_count = len(patterns.get('patterns', []))
        logger.info(f"Volume Patterns: {pattern_count}")
        
        # Tạo biểu đồ
        chart_path = vp_analyzer.visualize_volume_profile(df, lookback_periods=50)
        logger.info(f"Đã tạo biểu đồ Volume Profile tại: {chart_path}")
        
        # Tính VWAP
        vwap_zones = vp_analyzer.identify_vwap_zones(df, period='day')
        logger.info(f"VWAP: {vwap_zones.get('vwap')}")
        
        # Tạo biểu đồ VWAP
        vwap_chart = vp_analyzer.visualize_vwap_zones(df)
        logger.info(f"Đã tạo biểu đồ VWAP tại: {vwap_chart}")
        
        print("\n==== VOLUME PROFILE ANALYZER ====")
        print(f"- POC: {profile.get('poc'):.2f}")
        print(f"- Value Area: {profile.get('value_area')}")
        print(f"- Support Zones: {support_count}")
        print(f"- Resistance Zones: {resistance_count}")
        print(f"- Volume Patterns: {pattern_count}")
        print(f"- VWAP: {vwap_zones.get('vwap'):.2f}")
        print(f"- Chart: {chart_path}")
        print("=================================\n")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Volume Profile Analyzer: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_adaptive_exit_strategy(df: pd.DataFrame) -> None:
    """
    Kiểm tra Adaptive Exit Strategy.
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV
    """
    logger.info("Kiểm tra Adaptive Exit Strategy...")
    
    try:
        # Khởi tạo Adaptive Exit Strategy
        exit_strategy = AdaptiveExitStrategy()
        
        # Tạo dữ liệu vị thế mẫu
        current_price = df['close'].iloc[-1]
        position_data = {
            'position_type': 'long',
            'entry_price': current_price * 0.95,  # Giả sử vào lệnh ở giá thấp hơn 5%
            'current_price': current_price,
            'unrealized_pnl_pct': 5.0,
            'entry_time': (datetime.now() - timedelta(hours=10)).isoformat(),
            'holding_time': 10,  # Giờ
            'prev_pnl_pct': 3.0
        }
        
        # Xác định chiến lược thoát lệnh
        strategy = exit_strategy.determine_exit_strategy(df, position_data)
        
        logger.info(f"Chế độ thị trường: {strategy.get('regime')}")
        logger.info(f"Chiến lược active: {strategy.get('active_strategies')}")
        
        # In điểm của các chiến lược
        strategy_scores = strategy.get('strategy_scores', {})
        for strategy_name, score in strategy_scores.items():
            logger.info(f"- {strategy_name}: {score:.2f}")
        
        # Tính toán các điểm thoát
        exit_points = exit_strategy.calculate_exit_points(df, position_data, strategy)
        
        # Hiển thị các điểm thoát
        stop_loss = exit_points.get('stop_loss')
        take_profit = exit_points.get('take_profit')
        trailing_stop = exit_points.get('trailing_stop')
        
        if stop_loss:
            logger.info(f"Stop Loss: {stop_loss['price']:.2f} ({stop_loss['source']})")
        
        if take_profit:
            logger.info(f"Take Profit: {take_profit['price']:.2f} ({take_profit['source']})")
        
        if trailing_stop:
            logger.info(f"Trailing Stop: {trailing_stop['price']:.2f}")
        
        partial_tps = exit_points.get('partial_take_profits', [])
        logger.info(f"Partial Take Profits: {len(partial_tps)}")
        
        # Lấy tín hiệu thoát lệnh
        exit_signal = exit_strategy.get_exit_signal(df, position_data)
        
        logger.info(f"Exit Signal: {exit_signal['exit_signal']}")
        if exit_signal['exit_signal']:
            logger.info(f"Exit Type: {exit_signal['exit_type']}")
            logger.info(f"Exit Price: {exit_signal['exit_price']}")
            logger.info(f"Exit Reason: {exit_signal['exit_reason']}")
        
        # Tạo biểu đồ
        chart_path = exit_strategy.visualize_exit_points(df, position_data, exit_points)
        logger.info(f"Đã tạo biểu đồ các điểm thoát lệnh tại: {chart_path}")
        
        print("\n==== ADAPTIVE EXIT STRATEGY ====")
        print(f"- Chế độ thị trường: {strategy.get('regime')}")
        print(f"- Chiến lược active: {strategy.get('active_strategies')}")
        
        if stop_loss:
            print(f"- Stop Loss: {stop_loss['price']:.2f} ({stop_loss['source']})")
        
        if take_profit:
            print(f"- Take Profit: {take_profit['price']:.2f} ({take_profit['source']})")
        
        if trailing_stop:
            print(f"- Trailing Stop: {trailing_stop['price']:.2f}")
        
        print(f"- Partial Take Profits: {len(partial_tps)}")
        print(f"- Exit Signal: {exit_signal['exit_signal']}")
        if exit_signal['exit_signal']:
            print(f"- Exit Type: {exit_signal['exit_type']}")
            print(f"- Exit Price: {exit_signal['exit_price']}")
            print(f"- Exit Reason: {exit_signal['exit_reason']}")
        print(f"- Chart: {chart_path}")
        print("================================\n")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Adaptive Exit Strategy: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_partial_take_profit_manager(df: pd.DataFrame) -> None:
    """
    Kiểm tra Partial Take Profit Manager.
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV
    """
    logger.info("Kiểm tra Partial Take Profit Manager...")
    
    try:
        # Khởi tạo Partial Take Profit Manager
        tp_manager = PartialTakeProfitManager()
        
        # Tạo dữ liệu vị thế mẫu
        current_price = df['close'].iloc[-1]
        position_data = {
            'symbol': 'BTCUSDT',
            'position_id': 'test_position',
            'position_type': 'long',
            'entry_price': current_price * 0.95,  # Giả sử vào lệnh ở giá thấp hơn 5%
            'current_price': current_price,
            'position_size': 0.1
        }
        
        # Thiết lập các mức chốt lời
        tp_result = tp_manager.set_tp_levels(df, position_data)
        
        # Hiển thị các mức chốt lời
        tp_levels = tp_result.get('tp_levels', [])
        logger.info(f"Số mức chốt lời: {len(tp_levels)}")
        
        for level in tp_levels:
            logger.info(f"Mức {level['level']}: {level['price']:.2f} ({level['quantity_percent']:.0f}%)")
        
        # Kiểm tra tín hiệu chốt lời
        # Giả sử giá tăng đến mức chốt lời đầu tiên
        if tp_levels:
            test_price = tp_levels[0]['price']
            tp_signal = tp_manager.check_tp_signals(position_data['symbol'], position_data['position_id'], test_price)
            
            logger.info(f"TP Signal at price {test_price:.2f}: {tp_signal['tp_signal']}")
            
            if tp_signal['tp_signal']:
                logger.info(f"TP Level: {tp_signal['level']}")
                logger.info(f"TP Quantity: {tp_signal['quantity']}")
                
                # Thực hiện chốt lời
                execution_data = {
                    'level': tp_signal['level'],
                    'price': tp_signal['price'],
                    'quantity': tp_signal['quantity']
                }
                
                execute_result = tp_manager.execute_partial_tp(position_data['symbol'], position_data['position_id'], execution_data)
                
                logger.info(f"Execute TP Result: {execute_result['success']}")
                if execute_result['success']:
                    logger.info(f"Adjusted Stop: {execute_result.get('adjusted_stop')}")
                    logger.info(f"Remaining Levels: {execute_result['remaining_levels']}")
                
                # Lấy trạng thái sau khi thực hiện
                status = tp_manager.get_position_tp_status(position_data['symbol'], position_data['position_id'])
                
                logger.info(f"Executed Percent: {status.get('executed_percent', 0):.1f}%")
                logger.info(f"Remaining Quantity: {status.get('remaining_quantity', 0):.6f}")
        
        # Tạo biểu đồ
        chart_path = tp_manager.visualize_tp_levels(position_data['symbol'], position_data['position_id'], df)
        logger.info(f"Đã tạo biểu đồ các mức chốt lời tại: {chart_path}")
        
        # Reset vị thế
        tp_manager.reset_position_tp(position_data['symbol'], position_data['position_id'])
        
        print("\n==== PARTIAL TAKE PROFIT MANAGER ====")
        print(f"- Số mức chốt lời: {len(tp_levels)}")
        
        for level in tp_levels:
            print(f"- Mức {level['level']}: {level['price']:.2f} ({level['quantity_percent']:.0f}%)")
        
        if tp_levels:
            print(f"- TP Signal at price {test_price:.2f}: {tp_signal['tp_signal']}")
            
            if tp_signal['tp_signal']:
                print(f"- TP Level: {tp_signal['level']}")
                print(f"- TP Quantity: {tp_signal['quantity']}")
                print(f"- Execute TP Result: {execute_result['success']}")
                
                if execute_result['success']:
                    print(f"- Adjusted Stop: {execute_result.get('adjusted_stop')}")
                    print(f"- Remaining Levels: {execute_result['remaining_levels']}")
                    print(f"- Executed Percent: {status.get('executed_percent', 0):.1f}%")
                    print(f"- Remaining Quantity: {status.get('remaining_quantity', 0):.6f}")
        
        print(f"- Chart: {chart_path}")
        print("======================================\n")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Partial Take Profit Manager: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    print("\n=============================================")
    print("KIỂM TRA CÁC MODULE MỚI ĐÃ TRIỂN KHAI")
    print("=============================================\n")
    
    # Tạo dữ liệu mẫu
    print("Đang tạo dữ liệu mẫu...")
    df = create_sample_data(periods=100, volatility=0.02)
    print(f"Đã tạo dữ liệu mẫu với {len(df)} chu kỳ")
    
    # Hiển thị thông tin dữ liệu
    print(f"Giá bắt đầu: {df['close'].iloc[0]:.2f}")
    print(f"Giá kết thúc: {df['close'].iloc[-1]:.2f}")
    print(f"Khối lượng trung bình: {df['volume'].mean():.2f}")
    print(f"Biến động trung bình: {df['Price_Volatility'].mean():.4f}")
    print("\n")
    
    # Lưu dữ liệu mẫu
    df.to_csv("test_results/sample_data.csv")
    
    # Tạo biểu đồ dữ liệu mẫu
    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['close'], color='blue')
    plt.title('Sample Data - Price')
    plt.grid(True, alpha=0.3)
    
    plt.subplot(2, 1, 2)
    plt.bar(df.index, df['volume'], color='green', alpha=0.6)
    plt.title('Sample Data - Volume')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("test_results/sample_data.png")
    plt.close()
    
    # Chạy các bài test
    test_results = {}
    
    # 1. Test Order Flow Indicators
    test_results['order_flow'] = test_order_flow_indicators(df)
    
    # 2. Test Volume Profile Analyzer
    test_results['volume_profile'] = test_volume_profile_analyzer(df)
    
    # 3. Test Adaptive Exit Strategy
    test_results['exit_strategy'] = test_adaptive_exit_strategy(df)
    
    # 4. Test Partial Take Profit Manager
    test_results['tp_manager'] = test_partial_take_profit_manager(df)
    
    # Tổng hợp kết quả
    print("\n=============================================")
    print("TÓM TẮT KẾT QUẢ KIỂM TRA")
    print("=============================================")
    
    all_success = True
    
    for module, success in test_results.items():
        status = "✅ THÀNH CÔNG" if success else "❌ THẤT BẠI"
        print(f"{module}: {status}")
        
        if not success:
            all_success = False
    
    print("\nKẾT LUẬN:")
    if all_success:
        print("✅ Tất cả các module hoạt động tốt!")
        print("Hệ thống đã sẵn sàng để chạy với dữ liệu thực tế.")
    else:
        print("❌ Một số module gặp lỗi, vui lòng kiểm tra log để biết chi tiết.")
        print("Cần sửa lỗi trước khi chạy với dữ liệu thực tế.")
    
    print("\nLưu ý: Biểu đồ và kết quả kiểm tra đã được lưu trong thư mục 'test_results'")
    print("Log chi tiết đã được lưu trong file 'test_new_modules.log'")
    print("=============================================\n")


if __name__ == "__main__":
    main()