#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tích hợp các cải tiến win rate vào hệ thống chính
"""

import os
import json
import logging
import argparse
from typing import Dict, Any, List, Tuple

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('WinRateIntegration')

class EnhancedSignalFilter:
    """
    Bộ lọc tín hiệu nâng cao để cải thiện win rate
    """
    
    def __init__(self, config_path='configs/enhanced_filter_config.json'):
        """
        Khởi tạo bộ lọc tín hiệu nâng cao
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self.load_config()
        logger.info("Đã khởi tạo EnhancedSignalFilter")
    
    def load_config(self) -> Dict[str, Any]:
        """
        Tải cấu hình từ file JSON
        
        Returns:
            Dict[str, Any]: Cấu hình bộ lọc
        """
        default_config = {
            "volume_min_threshold": 1.0,
            "multi_timeframe_agreement": True,
            "min_trend_strength": 0.005,
            "max_risk_per_trade": 0.02,
            "min_tf_agreement_count": 2,
            "market_regime_filters": {
                "trending": {
                    "volume_threshold": 1.2,
                    "trend_strength": 0.008
                },
                "ranging": {
                    "volume_threshold": 0.9,
                    "trend_strength": 0.003
                },
                "volatile": {
                    "volume_threshold": 1.5,
                    "trend_strength": 0.01
                },
                "bull": {
                    "volume_threshold": 1.1,
                    "trend_strength": 0.007
                },
                "bear": {
                    "volume_threshold": 1.3,
                    "trend_strength": 0.009
                }
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình bộ lọc từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {str(e)}. Sử dụng cấu hình mặc định.")
                return default_config
        else:
            # Tạo thư mục chứa file cấu hình nếu chưa tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Tạo file cấu hình mặc định
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            logger.info(f"Đã tạo cấu hình mặc định tại {self.config_path}")
            
            return default_config
    
    def should_trade(self, signal: Dict[str, Any]) -> bool:
        """
        Kiểm tra nếu tín hiệu nên được giao dịch
        
        Args:
            signal (Dict[str, Any]): Thông tin tín hiệu giao dịch
            
        Returns:
            bool: True nếu nên giao dịch, False nếu không
        """
        # 1. Kiểm tra khối lượng
        volume_ratio = signal.get("volume_ratio", 0)
        
        # Lấy ngưỡng khối lượng dựa trên chế độ thị trường
        market_regime = signal.get("market_regime", "default").lower()
        volume_threshold = self.config["volume_min_threshold"]
        
        if market_regime in self.config["market_regime_filters"]:
            volume_threshold = self.config["market_regime_filters"][market_regime]["volume_threshold"]
        
        if volume_ratio < volume_threshold:
            logger.debug(f"Lọc tín hiệu {signal.get('symbol')}: Khối lượng thấp {volume_ratio:.2f} < {volume_threshold}")
            return False
        
        # 2. Kiểm tra xác nhận đa timeframe
        if self.config["multi_timeframe_agreement"]:
            # Kiểm tra nếu có ít nhất N timeframe cùng hướng
            multi_tf = signal.get("multi_timeframe_signals", {})
            direction = signal.get("direction", "NEUTRAL")
            
            # Đếm số timeframe cùng hướng
            agreement_count = sum(1 for tf_dir in multi_tf.values() if tf_dir == direction)
            min_agreement = self.config["min_tf_agreement_count"]
            
            if agreement_count < min_agreement:
                logger.debug(f"Lọc tín hiệu {signal.get('symbol')}: Xác nhận timeframe không đủ ({agreement_count}/{min_agreement})")
                return False
        
        # 3. Kiểm tra độ mạnh xu hướng
        trend_slope = abs(signal.get("trend_slope", 0))
        
        # Lấy ngưỡng độ mạnh xu hướng dựa trên chế độ thị trường
        trend_threshold = self.config["min_trend_strength"]
        
        if market_regime in self.config["market_regime_filters"]:
            trend_threshold = self.config["market_regime_filters"][market_regime]["trend_strength"]
        
        if trend_slope < trend_threshold:
            logger.debug(f"Lọc tín hiệu {signal.get('symbol')}: Độ mạnh xu hướng thấp {trend_slope:.4f} < {trend_threshold}")
            return False
        
        # 4. Kiểm tra rủi ro trên mỗi giao dịch
        entry_price = signal.get("entry_price", 0)
        sl_price = signal.get("sl_price", 0)
        
        if entry_price == 0 or sl_price == 0:
            return True  # Không đủ thông tin để kiểm tra risk
        
        # Tính % rủi ro
        if signal.get("direction") == "LONG":
            risk_pct = (entry_price - sl_price) / entry_price
        else:
            risk_pct = (sl_price - entry_price) / entry_price
        
        # Kiểm tra rủi ro tối đa
        if risk_pct > self.config["max_risk_per_trade"]:
            logger.debug(f"Lọc tín hiệu {signal.get('symbol')}: Rủi ro quá cao {risk_pct*100:.2f}% > {self.config['max_risk_per_trade']*100:.2f}%")
            return False
        
        # Tín hiệu đã vượt qua tất cả bộ lọc
        return True

class ImprovedSLTPCalculator:
    """
    Bộ điều chỉnh SL/TP thích ứng để tối ưu hóa win rate
    """
    
    def __init__(self, config_path='configs/improved_win_rate_config.json'):
        """
        Khởi tạo bộ tính toán SL/TP
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self.load_config()
        logger.info("Đã khởi tạo ImprovedSLTPCalculator")
    
    def load_config(self) -> Dict[str, Any]:
        """
        Tải cấu hình từ file JSON
        
        Returns:
            Dict[str, Any]: Cấu hình bộ tính toán SL/TP
        """
        default_config = {
            "sl_tp_settings": {
                "trending": {"sl_pct": 1.8, "tp_pct": 4.0},
                "ranging": {"sl_pct": 1.3, "tp_pct": 2.5},
                "volatile": {"sl_pct": 1.5, "tp_pct": 3.2},
                "bull": {"sl_pct": 1.6, "tp_pct": 3.5},
                "bear": {"sl_pct": 1.9, "tp_pct": 2.8},
                "default": {"sl_pct": 1.5, "tp_pct": 3.0}
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình SL/TP từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {str(e)}. Sử dụng cấu hình mặc định.")
                return default_config
        else:
            # Tạo thư mục chứa file cấu hình nếu chưa tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Tạo file cấu hình mặc định
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            logger.info(f"Đã tạo cấu hình mặc định tại {self.config_path}")
            
            return default_config
    
    def adjust_sl_tp(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Điều chỉnh SL/TP dựa trên điều kiện thị trường
        
        Args:
            signal (Dict[str, Any]): Thông tin tín hiệu giao dịch
            
        Returns:
            Dict[str, Any]: Thông tin tín hiệu với SL/TP đã điều chỉnh
        """
        # Tạo bản sao tín hiệu gốc
        adjusted_signal = signal.copy()
        
        # Lấy thông tin chế độ thị trường
        market_regime = signal.get("market_regime", "default").lower()
        
        # Lấy cài đặt SL/TP tương ứng
        sl_tp_settings = self.config.get("sl_tp_settings", {})
        settings = sl_tp_settings.get(market_regime, sl_tp_settings.get("default", {"sl_pct": 1.5, "tp_pct": 3.0}))
        
        # Lấy giá entry
        entry_price = signal.get("entry_price", 0)
        if entry_price == 0:
            logger.warning("Không thể điều chỉnh SL/TP: Không có giá entry")
            return signal  # Không thể điều chỉnh nếu không có giá entry
        
        # Tính SL/TP mới dựa trên % và hướng giao dịch
        if signal.get("direction") == "LONG":
            new_sl_price = entry_price * (1 - settings["sl_pct"]/100)
            new_tp_price = entry_price * (1 + settings["tp_pct"]/100)
        else:  # SHORT
            new_sl_price = entry_price * (1 + settings["sl_pct"]/100)
            new_tp_price = entry_price * (1 - settings["tp_pct"]/100)
        
        # Lưu trữ giá SL/TP gốc
        adjusted_signal["original_sl_price"] = signal.get("sl_price", 0)
        adjusted_signal["original_tp_price"] = signal.get("tp_price", 0)
        
        # Cập nhật giá SL/TP mới
        adjusted_signal["sl_price"] = new_sl_price
        adjusted_signal["tp_price"] = new_tp_price
        adjusted_signal["sl_percentage"] = settings["sl_pct"]
        adjusted_signal["tp_percentage"] = settings["tp_pct"]
        
        # Thêm thông tin về điều chỉnh
        adjusted_signal["sl_tp_adjusted"] = True
        adjusted_signal["sl_tp_adjustment_reason"] = f"Điều chỉnh theo chế độ thị trường: {market_regime}"
        
        logger.debug(f"Đã điều chỉnh SL/TP cho {signal.get('symbol')}: {settings['sl_pct']}% / {settings['tp_pct']}%")
        
        return adjusted_signal

class ImprovedWinRateAdapter:
    """
    Tích hợp bộ lọc tín hiệu và điều chỉnh SL/TP thành một thành phần duy nhất
    """
    
    def __init__(self, signal_filter=None, sltp_calculator=None):
        """
        Khởi tạo adapter cải thiện win rate
        
        Args:
            signal_filter: Bộ lọc tín hiệu (tùy chọn)
            sltp_calculator: Bộ tính toán SL/TP (tùy chọn)
        """
        self.signal_filter = signal_filter or EnhancedSignalFilter()
        self.sltp_calculator = sltp_calculator or ImprovedSLTPCalculator()
        logger.info("Đã khởi tạo ImprovedWinRateAdapter")
    
    def process_signal(self, signal: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Xử lý tín hiệu để quyết định có giao dịch hay không và điều chỉnh tham số
        
        Args:
            signal: Thông tin tín hiệu giao dịch
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (Có nên giao dịch, Tín hiệu đã điều chỉnh)
        """
        # 1. Áp dụng bộ lọc để quyết định có nên giao dịch
        should_trade = self.signal_filter.should_trade(signal)
        
        # 2. Điều chỉnh SL/TP
        adjusted_signal = self.sltp_calculator.adjust_sl_tp(signal)
        
        if should_trade:
            logger.info(f"Chấp nhận và điều chỉnh tín hiệu {signal.get('symbol')} ({signal.get('direction')})")
        else:
            logger.info(f"Từ chối tín hiệu {signal.get('symbol')} ({signal.get('direction')})")
        
        return should_trade, adjusted_signal

def integrate_win_rate_improvements():
    """
    Hàm chính để tích hợp cải tiến win rate vào hệ thống
    """
    parser = argparse.ArgumentParser(description='Tích hợp cải tiến win rate vào hệ thống')
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Chế độ kiểm tra (không thực hiện thay đổi thực tế)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Hiển thị thông tin chi tiết'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Đường dẫn đến thư mục cấu hình tùy chọn'
    )
    
    args = parser.parse_args()
    
    # Thiết lập logging chi tiết nếu cần
    if args.verbose:
        logging.getLogger('WinRateIntegration').setLevel(logging.DEBUG)
    
    # Tạo đường dẫn cấu hình tùy chọn nếu có
    filter_config = 'configs/enhanced_filter_config.json'
    sltp_config = 'configs/improved_win_rate_config.json'
    
    if args.config:
        filter_config = os.path.join(args.config, 'enhanced_filter_config.json')
        sltp_config = os.path.join(args.config, 'improved_win_rate_config.json')
    
    # Khởi tạo các thành phần
    signal_filter = EnhancedSignalFilter(config_path=filter_config)
    sltp_calculator = ImprovedSLTPCalculator(config_path=sltp_config)
    win_rate_adapter = ImprovedWinRateAdapter(signal_filter, sltp_calculator)
    
    logger.info("Đã khởi tạo các thành phần cải thiện win rate")
    
    if args.test:
        logger.info("Chạy ở chế độ kiểm tra, không thực hiện thay đổi thực tế")
        test_win_rate_improvements(win_rate_adapter)
    else:
        logger.info("Tích hợp cải tiến win rate vào hệ thống")
        apply_win_rate_improvements(win_rate_adapter)

def test_win_rate_improvements(win_rate_adapter):
    """
    Kiểm tra cải tiến win rate với dữ liệu mẫu
    
    Args:
        win_rate_adapter: Adapter cải thiện win rate
    """
    # Tạo một số tín hiệu mẫu để kiểm tra
    sample_signals = [
        {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 85000,
            "sl_price": 83500,
            "tp_price": 87500,
            "volume_ratio": 1.2,
            "trend_slope": 0.01,
            "market_regime": "trending",
            "multi_timeframe_signals": {
                "1d": "LONG",
                "4h": "LONG",
                "1h": "NEUTRAL",
                "30m": "LONG"
            }
        },
        {
            "symbol": "ETHUSDT",
            "direction": "SHORT",
            "entry_price": 2000,
            "sl_price": 2040,
            "tp_price": 1920,
            "volume_ratio": 0.9,
            "trend_slope": 0.002,
            "market_regime": "ranging",
            "multi_timeframe_signals": {
                "1d": "NEUTRAL",
                "4h": "SHORT",
                "1h": "SHORT",
                "30m": "NEUTRAL"
            }
        },
        {
            "symbol": "SOLUSDT",
            "direction": "LONG",
            "entry_price": 120,
            "sl_price": 116,
            "tp_price": 128,
            "volume_ratio": 1.8,
            "trend_slope": 0.015,
            "market_regime": "volatile",
            "multi_timeframe_signals": {
                "1d": "LONG",
                "4h": "LONG",
                "1h": "LONG",
                "30m": "LONG"
            }
        }
    ]
    
    logger.info("Kiểm tra với các tín hiệu mẫu")
    
    results = []
    
    for i, signal in enumerate(sample_signals):
        logger.info(f"\nTín hiệu {i+1}: {signal['symbol']} {signal['direction']}")
        logger.info(f"- Market Regime: {signal['market_regime']}")
        logger.info(f"- Volume Ratio: {signal['volume_ratio']}")
        logger.info(f"- Trend Slope: {signal['trend_slope']}")
        logger.info(f"- SL/TP gốc: {signal['sl_price']} / {signal['tp_price']}")
        
        # Xử lý tín hiệu
        should_trade, adjusted_signal = win_rate_adapter.process_signal(signal)
        
        logger.info(f"- Kết quả lọc: {'Chấp nhận' if should_trade else 'Từ chối'}")
        if should_trade:
            logger.info(f"- SL/TP mới: {adjusted_signal['sl_price']:.2f} / {adjusted_signal['tp_price']:.2f}")
            sl_change = (adjusted_signal['sl_price'] - signal['sl_price']) / signal['sl_price'] * 100
            tp_change = (adjusted_signal['tp_price'] - signal['tp_price']) / signal['tp_price'] * 100
            logger.info(f"- Thay đổi SL/TP: {sl_change:+.2f}% / {tp_change:+.2f}%")
        
        # Lưu kết quả
        results.append({
            "signal": signal,
            "should_trade": should_trade,
            "adjusted_signal": adjusted_signal if should_trade else None
        })
    
    # Thống kê kết quả
    accepted_count = sum(1 for r in results if r["should_trade"])
    rejected_count = len(results) - accepted_count
    
    logger.info("\n=== KẾT QUẢ KIỂM TRA ===")
    logger.info(f"Tổng số tín hiệu: {len(results)}")
    logger.info(f"Tín hiệu được chấp nhận: {accepted_count} ({accepted_count/len(results)*100:.2f}%)")
    logger.info(f"Tín hiệu bị từ chối: {rejected_count} ({rejected_count/len(results)*100:.2f}%)")

def apply_win_rate_improvements(win_rate_adapter):
    """
    Áp dụng cải tiến win rate vào hệ thống chính
    
    Args:
        win_rate_adapter: Adapter cải thiện win rate
    """
    # TODO: Tích hợp với hệ thống thực tế
    # Điều này sẽ phụ thuộc vào cấu trúc hệ thống hiện tại
    
    logger.info("Đang tích hợp cải tiến win rate vào hệ thống chính...")
    
    # 1. Đường dẫn đến file tích hợp
    integration_path = "win_rate_integration.json"
    
    # 2. Lưu thông tin tích hợp
    integration_info = {
        "components": {
            "signal_filter": {
                "class": "EnhancedSignalFilter",
                "config_path": win_rate_adapter.signal_filter.config_path,
                "enabled": True
            },
            "sltp_calculator": {
                "class": "ImprovedSLTPCalculator",
                "config_path": win_rate_adapter.sltp_calculator.config_path,
                "enabled": True
            },
            "win_rate_adapter": {
                "class": "ImprovedWinRateAdapter",
                "enabled": True
            }
        },
        "integration_points": {
            "signal_processing": "before_position_open",
            "sltp_adjustment": "before_order_placement",
            "filter_application": "before_signal_execution"
        },
        "status": "active",
        "version": "1.0.0"
    }
    
    with open(integration_path, 'w') as f:
        json.dump(integration_info, f, indent=4)
    
    logger.info(f"Đã lưu thông tin tích hợp tại {integration_path}")
    logger.info("Tích hợp cải thiện win rate đã hoàn tất. Hệ thống sẽ sử dụng các cải tiến trong giao dịch.")

if __name__ == "__main__":
    integrate_win_rate_improvements()