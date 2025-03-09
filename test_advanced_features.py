"""
Script test các tính năng nâng cao của hệ thống giao dịch tự động

Script này test các module mới: phân tích đa khung thời gian, chỉ báo tổng hợp,
phân tích thanh khoản và hệ thống giao dịch nâng cao.
"""

import os
import sys
import logging
import time
import json
from datetime import datetime

from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.market_regime_detector import MarketRegimeDetector
from multi_timeframe_analyzer import MultiTimeframeAnalyzer
from composite_indicator import CompositeIndicator
from liquidity_analyzer import LiquidityAnalyzer
from advanced_trading_system import AdvancedTradingSystem

# Thiết lập logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_advanced')

def test_multi_timeframe_analyzer():
    """Test phân tích đa khung thời gian"""
    logger.info("=== Test phân tích đa khung thời gian ===")
    
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    mtf_analyzer = MultiTimeframeAnalyzer(
        binance_api=binance_api,
        data_processor=data_processor,
        timeframes=['15m', '1h', '4h', '1d']
    )
    
    # Test phân tích
    result = mtf_analyzer.consolidate_signals('BTCUSDT', lookback_days=30)
    
    if result:
        logger.info(f"Tín hiệu tổng hợp: {result['signal_description']}")
        logger.info(f"Độ tin cậy: {result['confidence']:.1f}%")
        logger.info(f"Tóm tắt: {result['summary']}")
        
        # Lưu kết quả ra file
        with open('mtf_analysis_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        logger.info("Đã lưu kết quả vào mtf_analysis_result.json")
    else:
        logger.error("Phân tích đa khung thời gian thất bại")
    
    # Test entry points
    entry_points = mtf_analyzer.get_optimal_entry_points('BTCUSDT', lookback_days=30)
    
    if entry_points:
        logger.info(f"Số điểm vào lệnh tối ưu: {len(entry_points.get('entry_points', []))}")
        logger.info(f"Điểm vào lệnh tốt nhất: {entry_points.get('best_entry_points', [])}")
        
        # Lưu kết quả ra file
        with open('mtf_entry_points.json', 'w') as f:
            json.dump(entry_points, f, indent=2)
        logger.info("Đã lưu kết quả vào mtf_entry_points.json")
    else:
        logger.error("Phân tích điểm vào lệnh tối ưu thất bại")

def test_composite_indicator():
    """Test chỉ báo tổng hợp"""
    logger.info("=== Test chỉ báo tổng hợp ===")
    
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Lấy dữ liệu mẫu
    df = data_processor.get_historical_data('BTCUSDT', '1h', lookback_days=30)
    
    if df is None or df.empty:
        logger.error("Không thể lấy dữ liệu")
        return
    
    # Khởi tạo chỉ báo tổng hợp
    ci = CompositeIndicator(
        indicators=['rsi', 'macd', 'ema_cross', 'bbands', 'volume_trend'],
        dynamic_weights=True
    )
    
    # Test tính toán điểm tổng hợp
    result = ci.calculate_composite_score(df)
    
    if result:
        logger.info(f"Điểm tổng hợp: {result['composite_score']:.2f}")
        logger.info(f"Tín hiệu: {result['signal_description']}")
        logger.info(f"Điểm các chỉ báo: {result['individual_scores']}")
        logger.info(f"Điểm có trọng số: {result['weighted_scores']}")
        
        # Lưu kết quả ra file
        with open('composite_indicator_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        logger.info("Đã lưu kết quả vào composite_indicator_result.json")
    else:
        logger.error("Tính toán chỉ báo tổng hợp thất bại")
    
    # Test khuyến nghị giao dịch
    recommendation = ci.get_trading_recommendation(df)
    
    if recommendation:
        logger.info(f"Khuyến nghị: {recommendation['action']}")
        logger.info(f"Chi tiết: {recommendation['action_details']}")
        
        # Lưu kết quả ra file
        with open('composite_recommendation.json', 'w') as f:
            json.dump(recommendation, f, indent=2)
        logger.info("Đã lưu kết quả vào composite_recommendation.json")
    else:
        logger.error("Lấy khuyến nghị giao dịch thất bại")

def test_liquidity_analyzer():
    """Test phân tích thanh khoản"""
    logger.info("=== Test phân tích thanh khoản ===")
    
    binance_api = BinanceAPI(simulation_mode=True)
    liq_analyzer = LiquidityAnalyzer(binance_api=binance_api)
    
    # Test phân tích orderbook
    result = liq_analyzer.analyze_orderbook('BTCUSDT')
    
    if result:
        logger.info(f"Giá hiện tại: {result['current_price']:.2f}")
        logger.info(f"Áp lực thị trường: {result['market_pressure'].upper()}")
        logger.info(f"Tỷ lệ bid/ask: {result['bid_ask_ratio']:.2f}")
        logger.info(f"Số vùng thanh khoản cao: {len(result['high_liquidity_zones'])}")
        
        # Lưu kết quả ra file
        with open('liquidity_analysis.json', 'w') as f:
            json.dump(result, f, indent=2)
        logger.info("Đã lưu kết quả vào liquidity_analysis.json")
    else:
        logger.error("Phân tích thanh khoản thất bại")
    
    # Test phát hiện sự kiện thanh khoản
    events = liq_analyzer.detect_liquidity_events('BTCUSDT')
    
    if events:
        logger.info(f"Số sự kiện thanh khoản: {events['event_count']}")
        if events['event_count'] > 0:
            logger.info(f"Sự kiện mạnh nhất: {events['events'][0]['description']}")
        
        # Lưu kết quả ra file
        with open('liquidity_events.json', 'w') as f:
            json.dump(events, f, indent=2)
        logger.info("Đã lưu kết quả vào liquidity_events.json")
    else:
        logger.error("Phát hiện sự kiện thanh khoản thất bại")
    
    # Test đề xuất vào lệnh/ra lệnh
    recommendations = liq_analyzer.get_entry_exit_recommendations('BTCUSDT')
    
    if recommendations:
        logger.info(f"Áp lực thị trường: {recommendations['market_pressure'].upper()}")
        logger.info(f"Số điểm vào lệnh mua: {len(recommendations.get('buy_entries', []))}")
        logger.info(f"Số điểm vào lệnh bán: {len(recommendations.get('sell_entries', []))}")
        logger.info(f"Số điểm chốt lời: {len(recommendations.get('take_profit_levels', []))}")
        
        # Lưu kết quả ra file
        with open('liquidity_recommendations.json', 'w') as f:
            json.dump(recommendations, f, indent=2)
        logger.info("Đã lưu kết quả vào liquidity_recommendations.json")
    else:
        logger.error("Lấy đề xuất vào lệnh/ra lệnh thất bại")

def test_advanced_trading_system():
    """Test hệ thống giao dịch nâng cao"""
    logger.info("=== Test hệ thống giao dịch nâng cao ===")
    
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Khởi tạo hệ thống giao dịch
    trading_system = AdvancedTradingSystem(
        binance_api=binance_api,
        data_processor=data_processor,
        initial_balance=10000.0,
        risk_percentage=1.0
    )
    
    # Test phân tích thị trường
    analysis = trading_system.analyze_market('BTCUSDT', '1h')
    
    if analysis:
        logger.info(f"Phân tích thị trường:")
        logger.info(f"Giá hiện tại: {analysis['current_price']:.2f}")
        logger.info(f"Tín hiệu: {analysis.get('signal', 'NEUTRAL')}")
        logger.info(f"Độ tin cậy: {analysis.get('confidence', 0):.1f}%")
        logger.info(f"Giai đoạn thị trường: {analysis.get('market_regime', {}).get('regime', 'unknown')}")
        logger.info(f"Tóm tắt: {analysis.get('summary', '')}")
        
        # Lưu kết quả ra file
        with open('market_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2)
        logger.info("Đã lưu kết quả vào market_analysis.json")
    else:
        logger.error("Phân tích thị trường thất bại")
    
    # Test tạo kế hoạch giao dịch
    plan = trading_system.generate_trading_plan('BTCUSDT', '1h')
    
    if plan:
        logger.info(f"Kế hoạch giao dịch:")
        logger.info(f"Hành động chính: {plan['primary_action']}")
        logger.info(f"Số điểm vào lệnh: {len(plan['entry_levels'])}")
        logger.info(f"Số điểm chốt lời: {len(plan['take_profit_levels'])}")
        logger.info(f"Số điểm dừng lỗ: {len(plan['stop_loss_levels'])}")
        logger.info(f"Tỷ lệ rủi ro/phần thưởng: {plan.get('risk_reward_ratio', 0):.2f}")
        logger.info(f"Tóm tắt: {plan.get('summary', '')}")
        
        # Lưu kết quả ra file
        with open('trading_plan.json', 'w') as f:
            json.dump(plan, f, indent=2)
        logger.info("Đã lưu kết quả vào trading_plan.json")
    else:
        logger.error("Tạo kế hoạch giao dịch thất bại")
    
    # Test mô phỏng giao dịch
    logger.info("=== Test mô phỏng giao dịch ===")
    
    # Lấy tín hiệu từ phân tích
    signal = analysis.get('signal')
    
    if signal in ['BUY', 'SELL']:
        # Lấy thông tin quản lý rủi ro
        risk_params = analysis.get('risk_management', {})
        
        # Thực hiện giao dịch
        trade_id = trading_system.execute_trade(
            symbol='BTCUSDT',
            side=signal,
            position_size=1.0,
            entry_price=analysis['current_price'],
            leverage=3,
            risk_params=risk_params
        )
        
        if trade_id:
            logger.info(f"Đã thực hiện giao dịch {signal} BTCUSDT, ID: {trade_id}")
            
            # Lấy danh sách vị thế đang mở
            open_positions = trading_system.get_active_positions()
            logger.info(f"Số vị thế đang mở: {len(open_positions)}")
            
            # Mô phỏng thay đổi giá
            current_price = analysis['current_price']
            price_change = current_price * 0.02  # Giả sử thay đổi 2%
            
            # Giá tăng nếu BUY, giảm nếu SELL (mô phỏng lãi)
            if signal == 'BUY':
                new_price = current_price * 1.02
            else:
                new_price = current_price * 0.98
            
            logger.info(f"Mô phỏng thay đổi giá từ {current_price:.2f} thành {new_price:.2f}")
            
            # Cập nhật vị thế với giá mới
            closed_positions = trading_system.update_positions({'BTCUSDT': new_price})
            
            # Hiển thị kết quả
            performance = trading_system.get_performance_summary()
            logger.info(f"Số dư hiện tại: ${performance['current_balance']:.2f}")
            logger.info(f"PnL: ${performance['current_balance'] - 10000.0:.2f} "
                     f"({(performance['current_balance'] - 10000.0) / 10000.0 * 100:.2f}%)")
            
            # Lưu kết quả ra file
            with open('trading_performance.json', 'w') as f:
                json.dump(performance, f, indent=2)
            logger.info("Đã lưu kết quả vào trading_performance.json")
            
            # Lấy danh sách vị thế đã đóng
            closed_positions = trading_system.get_closed_positions()
            
            with open('closed_positions.json', 'w') as f:
                json.dump(closed_positions, f, indent=2)
            logger.info("Đã lưu danh sách vị thế đã đóng vào closed_positions.json")
        else:
            logger.error(f"Không thể thực hiện giao dịch {signal} BTCUSDT")
    else:
        logger.info(f"Không có tín hiệu giao dịch rõ ràng")

def main():
    """Hàm chính"""
    # Kiểm tra xem có các API key cần thiết không
    if not os.environ.get('BINANCE_API_KEY') or not os.environ.get('BINANCE_API_SECRET'):
        logger.warning("Không tìm thấy BINANCE_API_KEY hoặc BINANCE_API_SECRET trong môi trường.")
        logger.warning("Sẽ sử dụng chế độ mô phỏng với dữ liệu giả lập.")
    
    # Test các module
    try:
        test_multi_timeframe_analyzer()
    except Exception as e:
        logger.error(f"Lỗi khi test phân tích đa khung thời gian: {e}")
    
    try:
        test_composite_indicator()
    except Exception as e:
        logger.error(f"Lỗi khi test chỉ báo tổng hợp: {e}")
    
    try:
        test_liquidity_analyzer()
    except Exception as e:
        logger.error(f"Lỗi khi test phân tích thanh khoản: {e}")
    
    try:
        test_advanced_trading_system()
    except Exception as e:
        logger.error(f"Lỗi khi test hệ thống giao dịch nâng cao: {e}")
    
    logger.info("Hoàn thành test các tính năng nâng cao")

if __name__ == "__main__":
    main()