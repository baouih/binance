#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Improved Win Rate Adapter - Bộ điều hợp cải thiện tỷ lệ thắng

Module này tích hợp bộ lọc tín hiệu nâng cao và điều chỉnh SL/TP động 
để cải thiện tỷ lệ thắng cho chiến lược giao dịch rủi ro cao.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
from enhanced_signal_filter import EnhancedSignalFilter

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('improved_win_rate.log')
    ]
)

logger = logging.getLogger('improved_win_rate')

class ImprovedWinRateAdapter:
    """
    Adapter để tích hợp các cải tiến win rate vào hệ thống giao dịch
    """
    
    def __init__(self, signal_filter=None, config_path='configs/improved_win_rate_config.json'):
        """
        Khởi tạo adapter
        
        Args:
            signal_filter: Bộ lọc tín hiệu (nếu không cung cấp, sẽ tạo mới)
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self.load_or_create_config()
        
        # Khởi tạo bộ lọc tín hiệu
        self.signal_filter = signal_filter if signal_filter else EnhancedSignalFilter()
        
        # Theo dõi hiệu suất
        self.performance_tracker = {
            "total_signals": 0,
            "filtered_signals": 0,
            "accepted_signals": 0,
            "rejected_signals": 0,
            "trades": [],
            "win_rate_before": 0.0,
            "win_rate_after": 0.0
        }
        
        logger.info("Khởi tạo ImprovedWinRateAdapter")
    
    def load_or_create_config(self) -> Dict[str, Any]:
        """
        Tải hoặc tạo cấu hình mặc định
        
        Returns:
            Dict[str, Any]: Cấu hình
        """
        default_config = {
            "enabled": True,
            "adaptive_sl_tp": {
                "enabled": True,
                "sl_adjustment": {
                    "trending": 1.0,
                    "ranging": 0.9,
                    "volatile": 0.85
                },
                "tp_adjustment": {
                    "trending": 1.05,
                    "ranging": 0.95,
                    "volatile": 0.9
                }
            },
            "preferred_timeframes": ["1d", "4h"],
            "entry_timing": {
                "enabled": True,
                "retry_count": 3,
                "max_wait_time": 30,  # phút
                "improvement_threshold": 0.2  # %
            },
            "performance_tracking": {
                "enabled": True,
                "record_all_trades": True
            }
        }
        
        # Tạo thư mục configs nếu chưa tồn tại
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Kiểm tra nếu file cấu hình tồn tại
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info("Đã tải cấu hình từ %s", self.config_path)
                return config
            except Exception as e:
                logger.error("Lỗi khi tải cấu hình: %s. Sử dụng cấu hình mặc định.", str(e))
                return default_config
        else:
            # Tạo file cấu hình mặc định
            try:
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info("Đã tạo cấu hình mặc định tại %s", self.config_path)
                return default_config
            except Exception as e:
                logger.error("Lỗi khi tạo cấu hình mặc định: %s", str(e))
                return default_config
    
    def process_signal(self, signal_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Xử lý tín hiệu giao dịch qua bộ lọc và điều chỉnh tham số
        
        Args:
            signal_data (Dict[str, Any]): Dữ liệu tín hiệu
        
        Returns:
            Tuple[bool, Dict[str, Any]]:
                - should_trade (bool): True nếu nên giao dịch
                - adjusted_params (Dict[str, Any]): Tham số đã được điều chỉnh
        """
        if not self.config["enabled"]:
            return True, signal_data  # Không áp dụng cải tiến
        
        # Theo dõi hiệu suất
        self.performance_tracker["total_signals"] += 1
        
        # 1. Lọc tín hiệu
        accepted, score, filter_details = self.signal_filter.filter_signal(signal_data)
        
        # Cập nhật thống kê
        if accepted:
            self.performance_tracker["accepted_signals"] += 1
        else:
            self.performance_tracker["rejected_signals"] += 1
        
        # Không giao dịch nếu tín hiệu bị từ chối
        if not accepted:
            logger.info(
                "Tín hiệu %s %s bị từ chối (score: %.2f)",
                signal_data.get("direction", "UNKNOWN"),
                signal_data.get("symbol", "UNKNOWN"),
                score
            )
            return False, signal_data
        
        # 2. Điều chỉnh SL/TP
        adjusted_params = signal_data.copy()
        if self.config["adaptive_sl_tp"]["enabled"] and "sl_tp_adjustments" in filter_details:
            adjusted_params = self._adjust_sl_tp(adjusted_params, filter_details["sl_tp_adjustments"])
        
        # 3. Điều chỉnh timing nếu cấu hình
        if self.config["entry_timing"]["enabled"]:
            adjusted_params["entry_timing"] = {
                "retry_count": self.config["entry_timing"]["retry_count"],
                "max_wait_time": self.config["entry_timing"]["max_wait_time"],
                "improvement_threshold": self.config["entry_timing"]["improvement_threshold"]
            }
        
        # Ghi log
        logger.info(
            "Tín hiệu %s %s được chấp nhận (score: %.2f)",
            adjusted_params.get("direction", "UNKNOWN"),
            adjusted_params.get("symbol", "UNKNOWN"),
            score
        )
        
        return True, adjusted_params
    
    def _adjust_sl_tp(self, signal_data: Dict[str, Any], sl_tp_adjustments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Điều chỉnh SL/TP dựa trên các thông số tối ưu
        
        Args:
            signal_data (Dict[str, Any]): Dữ liệu tín hiệu
            sl_tp_adjustments (Dict[str, Any]): Thông số điều chỉnh
        
        Returns:
            Dict[str, Any]: Dữ liệu tín hiệu đã điều chỉnh
        """
        adjusted_data = signal_data.copy()
        
        regime_type = sl_tp_adjustments.get("regime_type", "ranging")
        sl_atr_mult = sl_tp_adjustments.get("sl_atr_mult", 2.0)
        tp_atr_mult = sl_tp_adjustments.get("tp_atr_mult", 3.5)
        
        # Điều chỉnh thêm từ cấu hình adapter
        sl_adjustment_factor = self.config["adaptive_sl_tp"]["sl_adjustment"].get(regime_type, 1.0)
        tp_adjustment_factor = self.config["adaptive_sl_tp"]["tp_adjustment"].get(regime_type, 1.0)
        
        # Áp dụng điều chỉnh
        adjusted_data["sl_atr_multiplier"] = sl_atr_mult * sl_adjustment_factor
        adjusted_data["tp_atr_multiplier"] = tp_atr_mult * tp_adjustment_factor
        
        # Ghi log
        logger.info(
            "Điều chỉnh SL/TP cho %s %s: SL_ATR=%.2f, TP_ATR=%.2f (Chế độ: %s)",
            adjusted_data.get("direction", "UNKNOWN"),
            adjusted_data.get("symbol", "UNKNOWN"),
            adjusted_data["sl_atr_multiplier"],
            adjusted_data["tp_atr_multiplier"],
            regime_type
        )
        
        return adjusted_data
    
    def update_trade_result(self, trade_result: Dict[str, Any]) -> None:
        """
        Cập nhật kết quả giao dịch để theo dõi hiệu suất
        
        Args:
            trade_result (Dict[str, Any]): Kết quả giao dịch
        """
        if not self.config["performance_tracking"]["enabled"]:
            return
        
        # Lưu giao dịch nếu cấu hình
        if self.config["performance_tracking"]["record_all_trades"]:
            self.performance_tracker["trades"].append(trade_result)
        
        # Tính toán win rate mới
        total_trades = len(self.performance_tracker["trades"])
        if total_trades > 0:
            winning_trades = sum(1 for trade in self.performance_tracker["trades"] if trade.get("is_win", False))
            self.performance_tracker["win_rate_after"] = (winning_trades / total_trades) * 100.0
        
        # Ghi log
        logger.info(
            "Cập nhật kết quả giao dịch: %s %s, Kết quả: %s, PnL: %.2f, Win Rate: %.2f%%",
            trade_result.get("direction", "UNKNOWN"),
            trade_result.get("symbol", "UNKNOWN"),
            "THẮNG" if trade_result.get("is_win", False) else "THUA",
            trade_result.get("pnl", 0.0),
            self.performance_tracker["win_rate_after"]
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê hiệu suất
        
        Returns:
            Dict[str, Any]: Thống kê hiệu suất
        """
        stats = self.performance_tracker.copy()
        
        # Tính tỷ lệ lọc
        if stats["total_signals"] > 0:
            stats["filter_rate"] = (stats["rejected_signals"] / stats["total_signals"]) * 100.0
        else:
            stats["filter_rate"] = 0.0
        
        return stats
    
    def recommend_improvements(self) -> Dict[str, Any]:
        """
        Đề xuất cải tiến dựa trên dữ liệu hiệu suất
        
        Returns:
            Dict[str, Any]: Các đề xuất cải tiến
        """
        stats = self.get_performance_stats()
        recommendations = {
            "filter_threshold": None,
            "sl_tp_adjustments": None,
            "timeframe_focus": None
        }
        
        # Phân tích dữ liệu giao dịch nếu có đủ
        if len(stats["trades"]) >= 30:
            # 1. Đề xuất điều chỉnh ngưỡng lọc
            if stats["win_rate_after"] < 55.0:
                recommendations["filter_threshold"] = min(0.80, self.signal_filter.config["score_threshold"] + 0.05)
            elif stats["filter_rate"] > 60.0:
                recommendations["filter_threshold"] = max(0.60, self.signal_filter.config["score_threshold"] - 0.05)
            
            # 2. Phân tích hiệu suất theo timeframe
            timeframe_performance = {}
            for trade in stats["trades"]:
                tf = trade.get("timeframe", "unknown")
                if tf not in timeframe_performance:
                    timeframe_performance[tf] = {"wins": 0, "losses": 0}
                
                if trade.get("is_win", False):
                    timeframe_performance[tf]["wins"] += 1
                else:
                    timeframe_performance[tf]["losses"] += 1
            
            # Tính win rate cho mỗi timeframe
            for tf, data in timeframe_performance.items():
                total = data["wins"] + data["losses"]
                if total > 0:
                    data["win_rate"] = (data["wins"] / total) * 100.0
                else:
                    data["win_rate"] = 0.0
            
            # Đề xuất tập trung vào các timeframe hiệu quả nhất
            sorted_timeframes = sorted(
                timeframe_performance.items(),
                key=lambda x: x[1]["win_rate"],
                reverse=True
            )
            
            if sorted_timeframes:
                recommendations["timeframe_focus"] = [tf for tf, _ in sorted_timeframes[:2]]
        
        return recommendations

def test_improved_win_rate():
    """
    Hàm kiểm tra bộ điều hợp cải thiện tỷ lệ thắng
    """
    adapter = ImprovedWinRateAdapter()
    
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
    
    print("=== KIỂM TRA CẢI THIỆN TỶ LỆ THẮNG ===\n")
    
    # Kiểm tra từng tín hiệu
    for i, signal in enumerate(test_signals):
        print(f"Tín hiệu #{i+1}: {signal['direction']} {signal['symbol']} ({signal['timeframe']})")
        should_trade, adjusted_params = adapter.process_signal(signal)
        
        print(f"  Kết quả: {'NÊN GIAO DỊCH' if should_trade else 'BỎ QUA'}")
        
        if should_trade:
            print("  Tham số điều chỉnh:")
            if "sl_atr_multiplier" in adjusted_params:
                print(f"  - SL ATR: {adjusted_params['sl_atr_multiplier']:.2f}")
            if "tp_atr_multiplier" in adjusted_params:
                print(f"  - TP ATR: {adjusted_params['tp_atr_multiplier']:.2f}")
            if "entry_timing" in adjusted_params:
                print(f"  - Retry Count: {adjusted_params['entry_timing']['retry_count']}")
        
        print("")
    
    # Mô phỏng kết quả giao dịch
    print("Mô phỏng kết quả giao dịch:")
    
    # Trade 1: Thắng
    adapter.update_trade_result({
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
    adapter.update_trade_result({
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
    stats = adapter.get_performance_stats()
    print("\nThống kê hiệu suất:")
    print(f"Tổng số tín hiệu: {stats['total_signals']}")
    print(f"Tín hiệu được chấp nhận: {stats['accepted_signals']}")
    print(f"Tín hiệu bị từ chối: {stats['rejected_signals']}")
    print(f"Tỷ lệ lọc: {stats.get('filter_rate', 0):.1f}%")
    print(f"Win rate: {stats['win_rate_after']:.1f}%")

if __name__ == "__main__":
    test_improved_win_rate()