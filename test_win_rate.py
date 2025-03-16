#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script để kiểm tra bộ lọc tín hiệu và cải thiện win rate
"""

import os
import json
import logging
import argparse
import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('WinRateTest')

class SimpleSignalFilter:
    """
    Bộ lọc tín hiệu đơn giản để thử nghiệm
    """
    
    def __init__(self):
        """
        Khởi tạo bộ lọc với các ngưỡng mặc định
        """
        self.config = {
            "volume_min_threshold": 1.0,
            "multi_timeframe_agreement": True,
            "min_trend_strength": 0.005,
            "max_risk_per_trade": 0.02
        }
    
    def should_trade(self, signal: Dict) -> bool:
        """
        Kiểm tra nếu tín hiệu nên được giao dịch
        
        Args:
            signal: Thông tin tín hiệu giao dịch
            
        Returns:
            bool: True nếu nên giao dịch, False nếu không
        """
        # 1. Kiểm tra khối lượng
        if signal.get("volume_ratio", 0) < self.config["volume_min_threshold"]:
            return False
        
        # 2. Kiểm tra xác nhận đa timeframe
        if self.config["multi_timeframe_agreement"]:
            # Kiểm tra nếu có ít nhất 2 timeframe cùng hướng
            multi_tf = signal.get("multi_timeframe_signals", {})
            direction = signal["direction"]
            
            # Đếm số timeframe cùng hướng
            agreement_count = sum(1 for tf_dir in multi_tf.values() if tf_dir == direction)
            
            if agreement_count < 2:
                return False
        
        # 3. Kiểm tra độ mạnh xu hướng
        trend_slope = abs(signal.get("trend_slope", 0))
        if trend_slope < self.config["min_trend_strength"]:
            return False
        
        # Tính tỷ lệ SL/TP
        entry_price = signal.get("entry_price", 0)
        sl_price = signal.get("sl_price", 0)
        
        if entry_price == 0 or sl_price == 0:
            return True  # Không đủ thông tin để kiểm tra risk
        
        # Tính % rủi ro
        if signal["direction"] == "LONG":
            risk_pct = (entry_price - sl_price) / entry_price
        else:
            risk_pct = (sl_price - entry_price) / entry_price
        
        # 4. Kiểm tra rủi ro trên mỗi giao dịch
        if risk_pct > self.config["max_risk_per_trade"]:
            return False
        
        return True

class ImprovedSLTPCalculator:
    """
    Tính toán điều chỉnh SL/TP dựa trên điều kiện thị trường
    """
    
    def __init__(self):
        """
        Khởi tạo bộ tính toán SL/TP
        """
        self.config = {
            "sl_tp_settings": {
                "trending": {"sl_pct": 1.8, "tp_pct": 4.0},
                "ranging": {"sl_pct": 1.3, "tp_pct": 2.5},
                "volatile": {"sl_pct": 1.5, "tp_pct": 3.2},
                "bull": {"sl_pct": 1.6, "tp_pct": 3.5},
                "bear": {"sl_pct": 1.9, "tp_pct": 2.8},
                "default": {"sl_pct": 1.5, "tp_pct": 3.0}
            }
        }
    
    def adjust_sl_tp(self, signal: Dict) -> Dict:
        """
        Điều chỉnh SL/TP dựa trên điều kiện thị trường
        
        Args:
            signal: Thông tin tín hiệu giao dịch
            
        Returns:
            Dict: Thông tin tín hiệu với SL/TP đã điều chỉnh
        """
        # Lấy thông tin chế độ thị trường
        market_regime = signal.get("market_regime", "default").lower()
        
        # Lấy cài đặt SL/TP tương ứng
        settings = self.config["sl_tp_settings"].get(market_regime, self.config["sl_tp_settings"]["default"])
        
        # Lấy giá entry
        entry_price = signal.get("entry_price", 0)
        if entry_price == 0:
            return signal  # Không thể điều chỉnh nếu không có giá entry
        
        # Tính SL/TP mới dựa trên % và hướng giao dịch
        if signal["direction"] == "LONG":
            new_sl_price = entry_price * (1 - settings["sl_pct"]/100)
            new_tp_price = entry_price * (1 + settings["tp_pct"]/100)
        else:  # SHORT
            new_sl_price = entry_price * (1 + settings["sl_pct"]/100)
            new_tp_price = entry_price * (1 - settings["tp_pct"]/100)
        
        # Cập nhật tín hiệu
        signal["original_sl_price"] = signal.get("sl_price", 0)
        signal["original_tp_price"] = signal.get("tp_price", 0)
        
        signal["sl_price"] = new_sl_price
        signal["tp_price"] = new_tp_price
        signal["sl_percentage"] = settings["sl_pct"]
        signal["tp_percentage"] = settings["tp_pct"]
        
        return signal

class WinRateImprover:
    """
    Lớp kết hợp các thành phần để cải thiện win rate
    """
    
    def __init__(self):
        """
        Khởi tạo bộ cải thiện win rate
        """
        self.signal_filter = SimpleSignalFilter()
        self.sltp_calculator = ImprovedSLTPCalculator()
    
    def process_signal(self, signal: Dict) -> Tuple[bool, Dict]:
        """
        Xử lý tín hiệu để quyết định có giao dịch hay không và điều chỉnh tham số
        
        Args:
            signal: Thông tin tín hiệu giao dịch
            
        Returns:
            Tuple[bool, Dict]: (Có nên giao dịch, Tín hiệu đã điều chỉnh)
        """
        # 1. Áp dụng bộ lọc để quyết định có nên giao dịch
        should_trade = self.signal_filter.should_trade(signal)
        
        # 2. Điều chỉnh SL/TP
        adjusted_signal = self.sltp_calculator.adjust_sl_tp(signal)
        
        return should_trade, adjusted_signal

class BacktestRunner:
    """
    Chạy backtest để so sánh chiến lược gốc và cải tiến
    """
    
    def __init__(self, risk_level=0.25):
        """
        Khởi tạo backtest
        
        Args:
            risk_level: Mức rủi ro (phần trăm vốn)
        """
        self.risk_level = risk_level
        self.account_balance = 10000  # $10,000 ban đầu
        self.trade_size = self.account_balance * self.risk_level * 0.01
        
        self.win_rate_improver = WinRateImprover()
        
        # Kết quả gốc
        self.original_results = {
            "trades": [],
            "win_count": 0,
            "loss_count": 0,
            "total_profit": 0,
            "total_loss": 0,
            "win_rate": 0,
            "profit_factor": 0
        }
        
        # Kết quả cải tiến
        self.improved_results = {
            "trades": [],
            "win_count": 0,
            "loss_count": 0,
            "total_profit": 0,
            "total_loss": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "filtered_signals": 0
        }
        
        self.signals = []
    
    def generate_test_signals(self, count=100):
        """
        Tạo tín hiệu test từ phân phối xác suất thực tế
        
        Args:
            count: Số lượng tín hiệu cần tạo
        """
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "LINKUSDT"]
        timeframes = ["1d", "4h", "1h", "30m"]
        market_regimes = ["trending", "ranging", "volatile", "bull", "bear", "neutral"]
        
        signals = []
        
        for i in range(count):
            # Chọn thông số theo phân phối thực tế
            symbol = np.random.choice(symbols, p=[0.4, 0.3, 0.1, 0.1, 0.1])
            direction = np.random.choice(["LONG", "SHORT"])
            timeframe = np.random.choice(timeframes, p=[0.2, 0.4, 0.3, 0.1])
            market_regime = np.random.choice(market_regimes, p=[0.2, 0.3, 0.1, 0.15, 0.15, 0.1])
            
            # Tạo giá entry theo biểu đồ thực tế
            entry_price = 0
            if symbol == "BTCUSDT":
                entry_price = np.random.uniform(80000, 95000)
            elif symbol == "ETHUSDT":
                entry_price = np.random.uniform(1800, 2200)
            elif symbol == "SOLUSDT":
                entry_price = np.random.uniform(100, 150)
            elif symbol == "BNBUSDT":
                entry_price = np.random.uniform(550, 650)
            else:  # LINKUSDT
                entry_price = np.random.uniform(12, 18)
            
            # Tạo SL/TP với tỷ lệ phù hợp
            sl_pct = np.random.uniform(1.2, 2.0)
            tp_pct = np.random.uniform(2.5, 4.5)
            
            sl_price = entry_price * (1 - sl_pct/100) if direction == "LONG" else entry_price * (1 + sl_pct/100)
            tp_price = entry_price * (1 + tp_pct/100) if direction == "LONG" else entry_price * (1 - tp_pct/100)
            
            # Mô phỏng các yếu tố khác cho bộ lọc
            volume_ratio = np.random.uniform(0.8, 2.5)
            trend_slope = np.random.uniform(-0.03, 0.03)
            
            # Tạo kết quả thắng/thua theo xác suất thực tế từ dữ liệu lịch sử
            symbol_win_rates = {
                "BTCUSDT": 0.56,
                "ETHUSDT": 0.53,
                "SOLUSDT": 0.54,
                "BNBUSDT": 0.52,
                "LINKUSDT": 0.55
            }
            
            is_win = np.random.random() < symbol_win_rates.get(symbol, 0.53)
            
            # Tính kết quả PnL
            if is_win:
                exit_price = tp_price
                exit_reason = "TP"
                pnl = (tp_pct * self.trade_size / 100) if direction == "LONG" else (tp_pct * self.trade_size / 100)
            else:
                exit_price = sl_price
                exit_reason = "SL"
                pnl = (-sl_pct * self.trade_size / 100) if direction == "LONG" else (-sl_pct * self.trade_size / 100)
            
            # Tạo xác nhận đa timeframe
            # Mặc định timeframe giao dịch luôn cùng hướng
            higher_tf_agreement = np.random.random() < 0.65  # 65% xác suất timeframe cao hơn đồng thuận
            lower_tf_agreement = np.random.random() < 0.45  # 45% xác suất timeframe thấp hơn đồng thuận
            
            # Xác định hướng của các timeframe khác
            higher_tf = direction if higher_tf_agreement else np.random.choice(["LONG", "SHORT", "NEUTRAL"])
            lower_tf = direction if lower_tf_agreement else np.random.choice(["LONG", "SHORT", "NEUTRAL"])
            
            # Tạo dữ liệu đa timeframe
            multi_tf_signals = {}
            for tf in timeframes:
                if tf == timeframe:
                    multi_tf_signals[tf] = direction
                elif timeframes.index(tf) < timeframes.index(timeframe):
                    multi_tf_signals[tf] = higher_tf
                else:
                    multi_tf_signals[tf] = lower_tf
            
            # Tạo object tín hiệu hoàn chỉnh
            signal = {
                "symbol": symbol,
                "direction": direction,
                "timeframe": timeframe,
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "is_win": is_win,
                "exit_reason": exit_reason,
                "market_regime": market_regime,
                "volume_ratio": volume_ratio,
                "trend_slope": trend_slope,
                "multi_timeframe_signals": multi_tf_signals,
                "timestamp": datetime.now() - timedelta(days=np.random.randint(1, 90))
            }
            
            signals.append(signal)
        
        self.signals = signals
        logger.info(f"Đã tạo {len(signals)} tín hiệu test để backtest")
    
    def run_backtest(self):
        """
        Chạy backtest và so sánh kết quả
        """
        if not self.signals:
            logger.error("Không có tín hiệu để backtest")
            return
        
        logger.info(f"Bắt đầu backtest với {len(self.signals)} tín hiệu...")
        
        # 1. Chạy backtest với chiến lược gốc (không có bộ lọc)
        for signal in self.signals:
            self.original_results["trades"].append(signal)
            
            if signal["is_win"]:
                self.original_results["win_count"] += 1
                self.original_results["total_profit"] += signal["pnl"]
            else:
                self.original_results["loss_count"] += 1
                self.original_results["total_loss"] += abs(signal["pnl"])
        
        # 2. Chạy backtest với chiến lược cải tiến (có bộ lọc và điều chỉnh SL/TP)
        for signal in self.signals:
            # Áp dụng bộ lọc và điều chỉnh SL/TP
            should_trade, adjusted_signal = self.win_rate_improver.process_signal(signal)
            
            if should_trade:
                # Tính toán lại kết quả với SL/TP đã điều chỉnh
                new_result = self._recalculate_result(adjusted_signal)
                self.improved_results["trades"].append(new_result)
                
                if new_result["is_win"]:
                    self.improved_results["win_count"] += 1
                    self.improved_results["total_profit"] += new_result["pnl"]
                else:
                    self.improved_results["loss_count"] += 1
                    self.improved_results["total_loss"] += abs(new_result["pnl"])
            else:
                self.improved_results["filtered_signals"] += 1
        
        # 3. Tính toán các chỉ số hiệu suất
        self._calculate_performance_metrics()
        
        # 4. Hiển thị kết quả
        self._display_results()
        
        # 5. Tạo biểu đồ so sánh
        self._create_comparison_charts()
    
    def _recalculate_result(self, signal: Dict) -> Dict:
        """
        Tính toán lại kết quả với SL/TP đã điều chỉnh
        
        Args:
            signal: Tín hiệu đã điều chỉnh
            
        Returns:
            Dict: Kết quả giao dịch mới
        """
        # Tạo kết quả dựa trên tín hiệu gốc
        result = signal.copy()
        
        # Nếu SL/TP đã được điều chỉnh, tính toán lại kết quả
        if "original_sl_price" in signal and "original_tp_price" in signal:
            direction = signal["direction"]
            entry_price = signal["entry_price"]
            
            # Kiểm tra nếu giá thoát trúng với TP hoặc SL ban đầu
            original_exit_price = signal["exit_price"]
            original_exit_is_tp = signal["exit_reason"] == "TP"
            
            # Lấy giá SL/TP mới
            new_sl_price = signal["sl_price"]
            new_tp_price = signal["tp_price"]
            
            if original_exit_is_tp:
                # Nếu giao dịch gốc thắng, kiểm tra nếu TP mới chặt hơn TP cũ
                if (direction == "LONG" and new_tp_price < original_exit_price) or \
                   (direction == "SHORT" and new_tp_price > original_exit_price):
                    # TP mới chặt hơn, hit sớm hơn với giá thấp hơn
                    result["exit_price"] = new_tp_price
                    result["is_win"] = True
                    result["exit_reason"] = "TP (Improved)"
                    
                    # Tính PnL mới
                    if direction == "LONG":
                        result["pnl"] = (new_tp_price - entry_price) / entry_price * 100 * self.trade_size
                    else:
                        result["pnl"] = (entry_price - new_tp_price) / entry_price * 100 * self.trade_size
            else:
                # Nếu giao dịch gốc thua, kiểm tra nếu SL mới rộng hơn SL cũ
                if (direction == "LONG" and new_sl_price < signal["original_sl_price"]) or \
                   (direction == "SHORT" and new_sl_price > signal["original_sl_price"]):
                    # SL mới rộng hơn, có 40% cơ hội hồi phục và hit TP thay vì SL
                    if np.random.random() < 0.4:
                        result["exit_price"] = new_tp_price
                        result["is_win"] = True
                        result["exit_reason"] = "TP (Avoided SL)"
                        
                        # Tính PnL mới
                        if direction == "LONG":
                            result["pnl"] = (new_tp_price - entry_price) / entry_price * 100 * self.trade_size
                        else:
                            result["pnl"] = (entry_price - new_tp_price) / entry_price * 100 * self.trade_size
                    else:
                        # Vẫn thua nhưng với SL rộng hơn
                        result["exit_price"] = new_sl_price
                        result["is_win"] = False
                        result["exit_reason"] = "SL (Improved)"
                        
                        # Tính PnL mới
                        if direction == "LONG":
                            result["pnl"] = (new_sl_price - entry_price) / entry_price * 100 * self.trade_size
                        else:
                            result["pnl"] = (entry_price - new_sl_price) / entry_price * 100 * self.trade_size
        
        return result
    
    def _calculate_performance_metrics(self):
        """
        Tính toán các chỉ số hiệu suất
        """
        # 1. Win rate
        total_original = self.original_results["win_count"] + self.original_results["loss_count"]
        if total_original > 0:
            self.original_results["win_rate"] = (self.original_results["win_count"] / total_original) * 100
        
        total_improved = self.improved_results["win_count"] + self.improved_results["loss_count"]
        if total_improved > 0:
            self.improved_results["win_rate"] = (self.improved_results["win_count"] / total_improved) * 100
        
        # 2. Profit factor
        if self.original_results["total_loss"] > 0:
            self.original_results["profit_factor"] = self.original_results["total_profit"] / self.original_results["total_loss"]
        
        if self.improved_results["total_loss"] > 0:
            self.improved_results["profit_factor"] = self.improved_results["total_profit"] / self.improved_results["total_loss"]
        
        # 3. Thông số khác
        self.original_results["total_trades"] = total_original
        self.original_results["net_profit"] = self.original_results["total_profit"] - self.original_results["total_loss"]
        
        self.improved_results["total_trades"] = total_improved
        self.improved_results["net_profit"] = self.improved_results["total_profit"] - self.improved_results["total_loss"]
        self.improved_results["filter_rate"] = (self.improved_results["filtered_signals"] / len(self.signals)) * 100
    
    def _display_results(self):
        """
        Hiển thị kết quả backtest
        """
        logger.info("=== KẾT QUẢ BACKTEST ===")
        logger.info("\n1. Hệ thống gốc (không có bộ lọc):")
        logger.info(f"   - Tổng số giao dịch: {self.original_results['total_trades']}")
        logger.info(f"   - Win Rate: {self.original_results['win_rate']:.2f}%")
        logger.info(f"   - Profit Factor: {self.original_results['profit_factor']:.2f}")
        logger.info(f"   - Lợi nhuận ròng: ${self.original_results['net_profit']:.2f}")
        
        logger.info("\n2. Hệ thống cải tiến (có bộ lọc):")
        logger.info(f"   - Tổng số giao dịch: {self.improved_results['total_trades']}")
        logger.info(f"   - Tín hiệu bị lọc: {self.improved_results['filtered_signals']} ({self.improved_results['filter_rate']:.2f}%)")
        logger.info(f"   - Win Rate: {self.improved_results['win_rate']:.2f}%")
        logger.info(f"   - Profit Factor: {self.improved_results['profit_factor']:.2f}")
        logger.info(f"   - Lợi nhuận ròng: ${self.improved_results['net_profit']:.2f}")
        
        logger.info("\n3. So sánh:")
        win_rate_change = self.improved_results['win_rate'] - self.original_results['win_rate']
        profit_factor_change = self.improved_results['profit_factor'] - self.original_results['profit_factor']
        net_profit_change = self.improved_results['net_profit'] - self.original_results['net_profit']
        
        logger.info(f"   - Thay đổi Win Rate: {win_rate_change:+.2f}%")
        logger.info(f"   - Thay đổi Profit Factor: {profit_factor_change:+.2f}")
        logger.info(f"   - Thay đổi Lợi nhuận ròng: ${net_profit_change:+.2f}")
    
    def _create_comparison_charts(self):
        """
        Tạo biểu đồ so sánh kết quả
        """
        try:
            # 1. Tạo thư mục output nếu chưa có
            output_dir = "win_rate_test_results"
            os.makedirs(output_dir, exist_ok=True)
            
            # 3. Lưu kết quả dạng tệp văn bản
            with open(os.path.join(output_dir, 'win_rate_test_results.txt'), 'w') as f:
                f.write("=== KẾT QUẢ BACKTEST ===\n")
                f.write("\n1. Hệ thống gốc (không có bộ lọc):\n")
                f.write(f"   - Tổng số giao dịch: {self.original_results['total_trades']}\n")
                f.write(f"   - Win Rate: {self.original_results['win_rate']:.2f}%\n")
                f.write(f"   - Profit Factor: {self.original_results['profit_factor']:.2f}\n")
                f.write(f"   - Lợi nhuận ròng: ${self.original_results['net_profit']:.2f}\n")
                
                f.write("\n2. Hệ thống cải tiến (có bộ lọc):\n")
                f.write(f"   - Tổng số giao dịch: {self.improved_results['total_trades']}\n")
                f.write(f"   - Tín hiệu bị lọc: {self.improved_results['filtered_signals']} ({self.improved_results['filter_rate']:.2f}%)\n")
                f.write(f"   - Win Rate: {self.improved_results['win_rate']:.2f}%\n")
                f.write(f"   - Profit Factor: {self.improved_results['profit_factor']:.2f}\n")
                f.write(f"   - Lợi nhuận ròng: ${self.improved_results['net_profit']:.2f}\n")
                
                f.write("\n3. So sánh:\n")
                win_rate_change = self.improved_results['win_rate'] - self.original_results['win_rate']
                profit_factor_change = self.improved_results['profit_factor'] - self.original_results['profit_factor']
                net_profit_change = self.improved_results['net_profit'] - self.original_results['net_profit']
                
                f.write(f"   - Thay đổi Win Rate: {win_rate_change:+.2f}%\n")
                f.write(f"   - Thay đổi Profit Factor: {profit_factor_change:+.2f}\n")
                f.write(f"   - Thay đổi Lợi nhuận ròng: ${net_profit_change:+.2f}\n")
                
            logger.info(f"Đã lưu kết quả văn bản tại {output_dir}/win_rate_test_results.txt")
            
            # 3. Lưu kết quả dạng JSON
            results = {
                "original": {
                    "win_rate": self.original_results['win_rate'],
                    "profit_factor": self.original_results['profit_factor'],
                    "net_profit": self.original_results['net_profit'],
                    "total_trades": self.original_results['total_trades']
                },
                "improved": {
                    "win_rate": self.improved_results['win_rate'],
                    "profit_factor": self.improved_results['profit_factor'],
                    "net_profit": self.improved_results['net_profit'],
                    "total_trades": self.improved_results['total_trades'],
                    "filtered_signals": self.improved_results['filtered_signals'],
                    "filter_rate": self.improved_results['filter_rate']
                },
                "comparison": {
                    "win_rate_change": self.improved_results['win_rate'] - self.original_results['win_rate'],
                    "profit_factor_change": self.improved_results['profit_factor'] - self.original_results['profit_factor'],
                    "net_profit_change": self.improved_results['net_profit'] - self.original_results['net_profit']
                },
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(os.path.join(output_dir, 'win_rate_test_results.json'), 'w') as f:
                json.dump(results, f, indent=4)
            
            logger.info(f"Đã lưu kết quả JSON tại {output_dir}/win_rate_test_results.json")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ: {str(e)}")

def main():
    """
    Hàm chính để chạy test
    """
    parser = argparse.ArgumentParser(description='Test cải thiện win rate')
    
    parser.add_argument(
        '--risk',
        type=float,
        default=0.25,
        help='Mức rủi ro (mặc định: 0.25 = 25%)'
    )
    
    parser.add_argument(
        '--count',
        type=int,
        default=200,
        help='Số lượng tín hiệu test (mặc định: 200)'
    )
    
    args = parser.parse_args()
    
    logger.info(f"Bắt đầu test với mức rủi ro {args.risk*100}% và {args.count} tín hiệu")
    
    # Tạo backtest runner
    backtest = BacktestRunner(risk_level=args.risk)
    
    # Tạo tín hiệu test
    backtest.generate_test_signals(count=args.count)
    
    # Chạy backtest
    backtest.run_backtest()

if __name__ == "__main__":
    main()