#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tích hợp cải thiện tỷ lệ thắng vào hệ thống giao dịch

Script này tích hợp bộ lọc tín hiệu nâng cao và các cải tiến win rate
vào hệ thống giao dịch rủi ro cao hiện tại.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Thêm thư mục gốc vào sys.path để import các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import các module cải thiện win rate
from enhanced_signal_filter import EnhancedSignalFilter
from improved_win_rate_adapter import ImprovedWinRateAdapter

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('win_rate_integration.log')
    ]
)

logger = logging.getLogger('win_rate_integration')

def setup_win_rate_improvements(config_path=None):
    """
    Thiết lập và khởi tạo bộ cải thiện win rate
    
    Args:
        config_path (str, optional): Đường dẫn đến file cấu hình
    
    Returns:
        ImprovedWinRateAdapter: Bộ điều hợp cải thiện win rate đã khởi tạo
    """
    logger.info("Thiết lập bộ cải thiện tỷ lệ thắng...")
    
    # Khởi tạo bộ lọc tín hiệu
    filter_config = config_path + '/enhanced_filter_config.json' if config_path else None
    signal_filter = EnhancedSignalFilter(filter_config)
    
    # Khởi tạo bộ điều hợp win rate
    adapter_config = config_path + '/improved_win_rate_config.json' if config_path else None
    win_rate_adapter = ImprovedWinRateAdapter(signal_filter, adapter_config)
    
    logger.info("Đã khởi tạo thành công bộ cải thiện tỷ lệ thắng")
    
    return win_rate_adapter

def apply_to_strategy(strategy_module, win_rate_adapter):
    """
    Áp dụng bộ cải thiện win rate vào module chiến lược
    
    Args:
        strategy_module: Module chiến lược giao dịch
        win_rate_adapter: Bộ điều hợp cải thiện win rate
    
    Returns:
        bool: True nếu áp dụng thành công, False nếu thất bại
    """
    try:
        # Lưu trữ hàm xử lý tín hiệu gốc
        original_process_signal = strategy_module.process_signal
        original_on_trade_closed = getattr(strategy_module, 'on_trade_closed', None)
        
        # Thay thế bằng hàm mới có tích hợp bộ cải thiện win rate
        def enhanced_process_signal(signal_data):
            logger.info(f"Xử lý tín hiệu với bộ cải thiện win rate: {signal_data.get('direction', 'UNKNOWN')} {signal_data.get('symbol', 'UNKNOWN')}")
            
            # Áp dụng bộ lọc và điều chỉnh
            should_trade, adjusted_params = win_rate_adapter.process_signal(signal_data)
            
            if not should_trade:
                logger.info(f"Tín hiệu bị từ chối bởi bộ lọc")
                return None  # Không giao dịch
            
            # Gọi hàm xử lý gốc với tham số đã điều chỉnh
            return original_process_signal(adjusted_params)
        
        # Thay thế hàm xử lý tín hiệu
        strategy_module.process_signal = enhanced_process_signal
        
        # Thay thế hàm xử lý kết quả giao dịch nếu có
        if original_on_trade_closed:
            def enhanced_on_trade_closed(trade_result):
                # Gọi hàm xử lý gốc
                result = original_on_trade_closed(trade_result)
                
                # Cập nhật kết quả vào bộ theo dõi hiệu suất
                win_rate_adapter.update_trade_result(trade_result)
                
                return result
            
            strategy_module.on_trade_closed = enhanced_on_trade_closed
        
        logger.info("Đã tích hợp thành công bộ cải thiện tỷ lệ thắng vào chiến lược giao dịch")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tích hợp bộ cải thiện tỷ lệ thắng: {str(e)}")
        return False

def monitor_performance(win_rate_adapter, interval=100):
    """
    Thiết lập giám sát hiệu suất định kỳ
    
    Args:
        win_rate_adapter: Bộ điều hợp cải thiện win rate
        interval (int): Số lệnh giữa các lần kiểm tra
    
    Returns:
        callable: Hàm kiểm tra hiệu suất
    """
    trade_counter = 0
    
    def check_performance():
        nonlocal trade_counter
        trade_counter += 1
        
        # Kiểm tra hiệu suất sau mỗi 'interval' lệnh
        if trade_counter >= interval:
            stats = win_rate_adapter.get_performance_stats()
            recommendations = win_rate_adapter.recommend_improvements()
            
            logger.info("=== BÁO CÁO HIỆU SUẤT ===")
            logger.info(f"Tổng số tín hiệu: {stats['total_signals']}")
            logger.info(f"Tín hiệu được chấp nhận: {stats['accepted_signals']}")
            logger.info(f"Tín hiệu bị từ chối: {stats['rejected_signals']}")
            logger.info(f"Tỷ lệ lọc: {stats.get('filter_rate', 0):.1f}%")
            logger.info(f"Win rate: {stats['win_rate_after']:.1f}%")
            
            if recommendations['filter_threshold']:
                logger.info(f"Đề xuất: Điều chỉnh ngưỡng lọc thành {recommendations['filter_threshold']:.2f}")
            
            if recommendations['timeframe_focus']:
                logger.info(f"Đề xuất: Tập trung vào timeframes {', '.join(recommendations['timeframe_focus'])}")
            
            # Reset bộ đếm
            trade_counter = 0
    
    return check_performance

def parse_arguments():
    """
    Phân tích tham số dòng lệnh
    
    Returns:
        argparse.Namespace: Tham số dòng lệnh
    """
    parser = argparse.ArgumentParser(description='Tích hợp cải thiện tỷ lệ thắng vào hệ thống giao dịch')
    
    parser.add_argument(
        '--strategy-path',
        type=str,
        help='Đường dẫn đến module chiến lược giao dịch cần tích hợp'
    )
    
    parser.add_argument(
        '--config-path',
        type=str,
        default='configs',
        help='Đường dẫn đến thư mục cấu hình'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Chạy kiểm tra mà không tích hợp vào hệ thống'
    )
    
    return parser.parse_args()

def main():
    """
    Hàm chính để tích hợp cải thiện win rate
    """
    # Phân tích tham số dòng lệnh
    args = parse_arguments()
    
    # Khởi tạo bộ cải thiện win rate
    win_rate_adapter = setup_win_rate_improvements(args.config_path)
    
    if args.test:
        # Chế độ kiểm tra - chạy một số tín hiệu mẫu
        test_improved_win_rate(win_rate_adapter)
    else:
        # Chế độ tích hợp - nhập module chiến lược và áp dụng cải tiến
        if not args.strategy_path:
            logger.error("Thiếu đường dẫn đến module chiến lược giao dịch. Sử dụng --strategy-path")
            return
        
        try:
            # Nhập module chiến lược
            sys.path.append(os.path.dirname(args.strategy_path))
            strategy_name = os.path.basename(args.strategy_path).replace('.py', '')
            strategy_module = __import__(strategy_name)
            
            # Áp dụng cải tiến
            success = apply_to_strategy(strategy_module, win_rate_adapter)
            
            if success:
                # Thiết lập giám sát hiệu suất
                check_performance = monitor_performance(win_rate_adapter)
                
                # Lưu hàm kiểm tra hiệu suất vào module chiến lược
                strategy_module.check_win_rate_performance = check_performance
                
                logger.info(f"Đã tích hợp thành công bộ cải thiện win rate vào {strategy_name}")
            else:
                logger.error(f"Không thể tích hợp bộ cải thiện win rate vào {strategy_name}")
        
        except ImportError as e:
            logger.error(f"Không thể nhập module chiến lược: {str(e)}")
        except Exception as e:
            logger.error(f"Lỗi khi tích hợp: {str(e)}")

def test_improved_win_rate(win_rate_adapter):
    """
    Kiểm tra bộ cải thiện win rate
    
    Args:
        win_rate_adapter: Bộ điều hợp cải thiện win rate
    """
    logger.info("=== KIỂM TRA CẢI THIỆN WIN RATE ===")
    
    # Dữ liệu mẫu
    test_signals = [
        {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "timeframe": "4h",
            "timestamp": datetime.now(),
            "market_regime": "BULL",
            "volume_ratio": 1.5,
            "trend_slope": 0.02,
            "multi_timeframe_signals": {
                "1d": "LONG",
                "4h": "LONG",
                "1h": "NEUTRAL",
                "30m": "SHORT"
            }
        },
        {
            "symbol": "ETHUSDT",
            "direction": "SHORT",
            "timeframe": "1h",
            "timestamp": datetime.now(),
            "market_regime": "CHOPPY",
            "volume_ratio": 0.9,
            "trend_slope": -0.005,
            "multi_timeframe_signals": {
                "1d": "NEUTRAL",
                "4h": "SHORT",
                "1h": "SHORT",
                "30m": "SHORT"
            }
        },
        {
            "symbol": "SOLUSDT",
            "direction": "LONG",
            "timeframe": "1d",
            "timestamp": datetime.now(),
            "market_regime": "STRONG_BULL",
            "volume_ratio": 2.1,
            "trend_slope": 0.03,
            "multi_timeframe_signals": {
                "1d": "LONG",
                "4h": "LONG",
                "1h": "LONG",
                "30m": "LONG"
            }
        }
    ]
    
    # Kiểm tra từng tín hiệu
    for i, signal in enumerate(test_signals):
        logger.info(f"Tín hiệu #{i+1}: {signal['direction']} {signal['symbol']} ({signal['timeframe']})")
        should_trade, adjusted_params = win_rate_adapter.process_signal(signal)
        
        logger.info(f"  Kết quả: {'NÊN GIAO DỊCH' if should_trade else 'BỎ QUA'}")
        
        if should_trade:
            logger.info("  Tham số điều chỉnh:")
            if "sl_atr_multiplier" in adjusted_params:
                logger.info(f"  - SL ATR: {adjusted_params['sl_atr_multiplier']:.2f}")
            if "tp_atr_multiplier" in adjusted_params:
                logger.info(f"  - TP ATR: {adjusted_params['tp_atr_multiplier']:.2f}")
            if "entry_timing" in adjusted_params:
                logger.info(f"  - Retry Count: {adjusted_params['entry_timing']['retry_count']}")
    
    # Mô phỏng kết quả giao dịch
    logger.info("Mô phỏng kết quả giao dịch:")
    
    # Trade 1: Thắng
    win_rate_adapter.update_trade_result({
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "timeframe": "4h",
        "entry_price": 50000,
        "exit_price": 52000,
        "is_win": True,
        "pnl": 400,
        "pnl_percent": 4.0,
        "exit_reason": "TP"
    })
    
    # Trade 2: Thua
    win_rate_adapter.update_trade_result({
        "symbol": "SOLUSDT",
        "direction": "LONG",
        "timeframe": "1d",
        "entry_price": 100,
        "exit_price": 94,
        "is_win": False,
        "pnl": -60,
        "pnl_percent": -6.0,
        "exit_reason": "SL"
    })
    
    # Hiển thị thống kê
    stats = win_rate_adapter.get_performance_stats()
    logger.info("Thống kê hiệu suất:")
    logger.info(f"Tổng số tín hiệu: {stats['total_signals']}")
    logger.info(f"Tín hiệu được chấp nhận: {stats['accepted_signals']}")
    logger.info(f"Tín hiệu bị từ chối: {stats['rejected_signals']}")
    logger.info(f"Tỷ lệ lọc: {stats.get('filter_rate', 0):.1f}%")
    logger.info(f"Win rate: {stats['win_rate_after']:.1f}%")

if __name__ == "__main__":
    main()