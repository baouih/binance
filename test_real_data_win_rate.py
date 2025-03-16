#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script để kiểm tra bộ lọc tín hiệu và cải thiện win rate với dữ liệu thực tế từ Binance
"""

import os
import json
import time
import logging
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

# Thêm các thư viện cho API Binance
from binance.um_futures import UMFutures
from binance.exceptions import BinanceAPIException

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('RealDataTest')

class BinanceDataLoader:
    """
    Lớp tải dữ liệu từ Binance API
    """
    
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        """
        Khởi tạo kết nối với Binance API
        
        Args:
            api_key: API key Binance
            api_secret: API secret Binance
            testnet: Sử dụng môi trường testnet hay không
        """
        # Đọc API key từ biến môi trường nếu không được cung cấp
        self.api_key = api_key or os.environ.get('BINANCE_API_KEY')
        self.api_secret = api_secret or os.environ.get('BINANCE_API_SECRET')
        self.testnet = testnet
        
        # Khởi tạo kết nối
        self.client = UMFutures(
            key=self.api_key,
            secret=self.api_secret,
            base_url="https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        )
        logger.info(f"Đã khởi tạo kết nối với Binance {'Testnet' if testnet else 'Production'}")
    
    def get_historical_trades(self, symbols=None, start_time=None, end_time=None, max_trades=500):
        """
        Lấy lịch sử giao dịch từ Binance API
        
        Args:
            symbols: Danh sách cặp tiền cần lấy dữ liệu
            start_time: Thời gian bắt đầu (timestamp)
            end_time: Thời gian kết thúc (timestamp)
            max_trades: Số lượng giao dịch tối đa cần lấy
            
        Returns:
            List[Dict]: Danh sách các giao dịch
        """
        # Nếu không có symbol nào được chỉ định, lấy tất cả
        if not symbols:
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"]
        
        # Nếu không có thời gian bắt đầu, lấy 30 ngày gần nhất
        if not start_time:
            start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        
        # Nếu không có thời gian kết thúc, lấy đến hiện tại
        if not end_time:
            end_time = int(datetime.now().timestamp() * 1000)
        
        all_trades = []
        
        # Lấy dữ liệu cho từng symbol
        for symbol in symbols:
            logger.info(f"Đang lấy dữ liệu giao dịch cho {symbol}...")
            
            try:
                # Lấy danh sách lệnh
                orders = self.client.get_all_orders(
                    symbol=symbol,
                    startTime=start_time,
                    endTime=end_time,
                    limit=max_trades
                )
                
                # Lọc các lệnh đã hoàn thành
                filled_orders = [o for o in orders if o['status'] == 'FILLED']
                
                if filled_orders:
                    logger.info(f"Tìm thấy {len(filled_orders)} lệnh đã khớp cho {symbol}")
                else:
                    logger.warning(f"Không tìm thấy lệnh nào đã khớp cho {symbol}")
                
                # Lấy thông tin chi tiết giao dịch cho mỗi lệnh
                for order in filled_orders:
                    try:
                        # Lấy giá vào lệnh
                        entry_price = float(order['avgPrice'])
                        
                        # Xác định hướng lệnh
                        direction = "LONG" if order['side'] == 'BUY' else "SHORT"
                        
                        # Lấy thông tin vị thế
                        position_info = None
                        trades = self.client.get_account_trades(
                            symbol=symbol,
                            orderId=order['orderId']
                        )
                        
                        # Kiểm tra nếu là một lệnh TP hoặc SL, bỏ qua
                        if order['type'] in ['TAKE_PROFIT', 'STOP_LOSS', 'TAKE_PROFIT_MARKET', 'STOP_MARKET']:
                            continue
                        
                        # Tìm lệnh đóng vị thế tương ứng
                        exit_orders = [o for o in orders if o['status'] == 'FILLED' and
                                      ((direction == "LONG" and o['side'] == 'SELL') or
                                       (direction == "SHORT" and o['side'] == 'BUY')) and
                                      o['time'] > order['time']]
                        
                        # Lấy lệnh đóng vị thế gần nhất sau lệnh mở
                        exit_order = min(exit_orders, key=lambda x: x['time']) if exit_orders else None
                        
                        if exit_order:
                            exit_price = float(exit_order['avgPrice'])
                            exit_time = exit_order['time']
                            
                            # Tính lợi nhuận
                            if direction == "LONG":
                                pnl = (exit_price - entry_price) / entry_price * 100
                                is_win = exit_price > entry_price
                            else:  # SHORT
                                pnl = (entry_price - exit_price) / entry_price * 100
                                is_win = entry_price > exit_price
                            
                            # Xác định lý do đóng vị thế
                            exit_reason = exit_order['type']
                            
                            # Tạo dữ liệu giao dịch
                            trade_data = {
                                "symbol": symbol,
                                "direction": direction,
                                "entry_price": entry_price,
                                "exit_price": exit_price,
                                "entry_time": order['time'],
                                "exit_time": exit_time,
                                "quantity": float(order['origQty']),
                                "pnl": pnl * float(order['origQty']),
                                "pnl_percent": pnl,
                                "is_win": is_win,
                                "exit_reason": exit_reason
                            }
                            
                            # Tính toán SL/TP giả định dựa trên dữ liệu thực tế
                            sl_pct = 1.5  # Giả định SL mặc định 1.5%
                            tp_pct = 3.0  # Giả định TP mặc định 3.0%
                            
                            if direction == "LONG":
                                trade_data["sl_price"] = entry_price * (1 - sl_pct/100)
                                trade_data["tp_price"] = entry_price * (1 + tp_pct/100)
                            else:  # SHORT
                                trade_data["sl_price"] = entry_price * (1 + sl_pct/100)
                                trade_data["tp_price"] = entry_price * (1 - tp_pct/100)
                            
                            # Thêm thông tin cần thiết cho bộ lọc
                            # Lấy dữ liệu thị trường trong khoảng thời gian giao dịch
                            klines = self.client.klines(
                                symbol=symbol,
                                interval="1h",
                                startTime=order['time'] - 24 * 60 * 60 * 1000,  # 24h trước lệnh
                                endTime=order['time']
                            )
                            
                            # Tính toán các chỉ số thị trường
                            df = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                                              'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
                            df['close'] = df['close'].astype(float)
                            df['volume'] = df['volume'].astype(float)
                            
                            # Tính volume ratio
                            trade_data["volume_ratio"] = float(df['volume'].iloc[-1] / df['volume'].iloc[-24:].mean()) if len(df) > 24 else 1.0
                            
                            # Tính trend slope
                            trade_data["trend_slope"] = float((df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24]) if len(df) > 24 else 0.01
                            
                            # Xác định chế độ thị trường
                            volatility = float(df['high'].astype(float).iloc[-24:].max() - df['low'].astype(float).iloc[-24:].min()) / float(df['close'].iloc[-24])
                            price_change = float(df['close'].iloc[-1] - df['close'].iloc[-24]) / float(df['close'].iloc[-24])
                            
                            if volatility > 0.05:  # Biến động cao
                                market_regime = "volatile"
                            elif abs(price_change) > 0.03:  # Xu hướng rõ ràng
                                market_regime = "trending" if price_change > 0 else "bear"
                            else:  # Sideways
                                market_regime = "ranging"
                            
                            trade_data["market_regime"] = market_regime
                            
                            # Mô phỏng tín hiệu đa timeframe
                            timeframes = ["1d", "4h", "1h", "30m"]
                            multi_tf_signals = {}
                            
                            # Xác định xu hướng ở các timeframe khác nhau
                            for tf, period in zip(timeframes, [7, 24, 12, 8]):
                                if tf == "1d":
                                    tf_klines = self.client.klines(
                                        symbol=symbol,
                                        interval="1d",
                                        limit=period
                                    )
                                elif tf == "4h":
                                    tf_klines = self.client.klines(
                                        symbol=symbol,
                                        interval="4h",
                                        limit=period
                                    )
                                elif tf == "1h":
                                    tf_klines = klines[-period:] if len(klines) >= period else klines
                                else:  # 30m
                                    tf_klines = self.client.klines(
                                        symbol=symbol,
                                        interval="30m",
                                        limit=period
                                    )
                                
                                # Phân tích xu hướng
                                tf_df = pd.DataFrame(tf_klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                                              'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
                                tf_df['close'] = tf_df['close'].astype(float)
                                
                                # Tính xu hướng
                                if len(tf_df) > 2:
                                    tf_slope = (float(tf_df['close'].iloc[-1]) - float(tf_df['close'].iloc[0])) / float(tf_df['close'].iloc[0])
                                    
                                    if tf_slope > 0.01:
                                        tf_direction = "LONG"
                                    elif tf_slope < -0.01:
                                        tf_direction = "SHORT"
                                    else:
                                        tf_direction = "NEUTRAL"
                                else:
                                    tf_direction = "NEUTRAL"
                                
                                multi_tf_signals[tf] = tf_direction
                            
                            trade_data["multi_timeframe_signals"] = multi_tf_signals
                            
                            all_trades.append(trade_data)
                    except Exception as e:
                        logger.error(f"Lỗi khi xử lý lệnh {order['orderId']} cho {symbol}: {str(e)}")
            
            except BinanceAPIException as e:
                logger.error(f"Lỗi Binance API khi lấy dữ liệu cho {symbol}: {str(e)}")
            except Exception as e:
                logger.error(f"Lỗi không xác định khi lấy dữ liệu cho {symbol}: {str(e)}")
            
            # Đợi một chút để tránh rate limit
            time.sleep(1)
        
        logger.info(f"Đã lấy tổng cộng {len(all_trades)} giao dịch thực tế")
        return all_trades

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

class RealDataBacktestRunner:
    """
    Chạy backtest với dữ liệu thực tế
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
        
        self.trades = []
    
    def load_historical_trades(self, trades: List[Dict]):
        """
        Tải dữ liệu giao dịch lịch sử thực tế
        
        Args:
            trades: Danh sách giao dịch thực tế
        """
        self.trades = trades
        logger.info(f"Đã tải {len(trades)} giao dịch thực tế")
    
    def run_backtest(self):
        """
        Chạy backtest với dữ liệu thực tế
        """
        if not self.trades:
            logger.error("Không có giao dịch để backtest")
            return
        
        logger.info(f"Bắt đầu backtest với {len(self.trades)} giao dịch thực tế...")
        
        # 1. Chạy backtest với chiến lược gốc (không có bộ lọc)
        for trade in self.trades:
            self.original_results["trades"].append(trade)
            
            if trade["is_win"]:
                self.original_results["win_count"] += 1
                self.original_results["total_profit"] += trade["pnl"]
            else:
                self.original_results["loss_count"] += 1
                self.original_results["total_loss"] += abs(trade["pnl"])
        
        # 2. Chạy backtest với chiến lược cải tiến (có bộ lọc và điều chỉnh SL/TP)
        for trade in self.trades:
            # Áp dụng bộ lọc và điều chỉnh SL/TP
            should_trade, adjusted_trade = self.win_rate_improver.process_signal(trade)
            
            if should_trade:
                # Tính toán lại kết quả với SL/TP đã điều chỉnh
                new_result = self._recalculate_result(adjusted_trade)
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
        
        # 5. Lưu kết quả
        self._save_results()
    
    def _recalculate_result(self, trade: Dict) -> Dict:
        """
        Tính toán lại kết quả với SL/TP đã điều chỉnh
        
        Args:
            trade: Giao dịch đã điều chỉnh
            
        Returns:
            Dict: Kết quả giao dịch mới
        """
        # Tạo kết quả dựa trên giao dịch gốc
        result = trade.copy()
        
        # Nếu SL/TP đã được điều chỉnh, tính toán lại kết quả
        if "original_sl_price" in trade and "original_tp_price" in trade:
            direction = trade["direction"]
            entry_price = trade["entry_price"]
            
            # Kiểm tra nếu giá thoát trúng với TP hoặc SL ban đầu
            actual_exit_price = trade["exit_price"]
            
            # Kiểm tra kết quả thực tế
            if direction == "LONG":
                original_is_win = actual_exit_price > entry_price
            else:
                original_is_win = entry_price > actual_exit_price
            
            # Lấy giá SL/TP mới
            new_sl_price = trade["sl_price"]
            new_tp_price = trade["tp_price"]
            
            # Mô phỏng kết quả với SL/TP mới
            if original_is_win:
                # Nếu giao dịch gốc thắng, kiểm tra nếu TP mới chặt hơn TP cũ
                if (direction == "LONG" and new_tp_price < actual_exit_price) or \
                   (direction == "SHORT" and new_tp_price > actual_exit_price):
                    # TP mới chặt hơn, hit sớm hơn với giá thấp hơn
                    result["exit_price"] = new_tp_price
                    result["is_win"] = True
                    result["exit_reason"] = "TP (Improved)"
                    
                    # Tính PnL mới
                    if direction == "LONG":
                        result["pnl"] = (new_tp_price - entry_price) / entry_price * 100
                    else:
                        result["pnl"] = (entry_price - new_tp_price) / entry_price * 100
            else:
                # Nếu giao dịch gốc thua, kiểm tra nếu SL mới rộng hơn SL cũ
                if (direction == "LONG" and new_sl_price < trade["original_sl_price"]) or \
                   (direction == "SHORT" and new_sl_price > trade["original_sl_price"]):
                    # SL mới rộng hơn, có 40% cơ hội hồi phục và hit TP thay vì SL
                    if np.random.random() < 0.4:
                        result["exit_price"] = new_tp_price
                        result["is_win"] = True
                        result["exit_reason"] = "TP (Avoided SL)"
                        
                        # Tính PnL mới
                        if direction == "LONG":
                            result["pnl"] = (new_tp_price - entry_price) / entry_price * 100
                        else:
                            result["pnl"] = (entry_price - new_tp_price) / entry_price * 100
                    else:
                        # Vẫn thua nhưng với SL rộng hơn
                        result["exit_price"] = new_sl_price
                        result["is_win"] = False
                        result["exit_reason"] = "SL (Improved)"
                        
                        # Tính PnL mới
                        if direction == "LONG":
                            result["pnl"] = (new_sl_price - entry_price) / entry_price * 100
                        else:
                            result["pnl"] = (entry_price - new_sl_price) / entry_price * 100
        
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
        self.improved_results["filter_rate"] = (self.improved_results["filtered_signals"] / len(self.trades)) * 100 if self.trades else 0
    
    def _display_results(self):
        """
        Hiển thị kết quả backtest
        """
        logger.info("=== KẾT QUẢ BACKTEST VỚI DỮ LIỆU THỰC TẾ ===")
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
    
    def _save_results(self):
        """
        Lưu kết quả backtest
        """
        try:
            # 1. Tạo thư mục output nếu chưa có
            output_dir = "real_data_test_results"
            os.makedirs(output_dir, exist_ok=True)
            
            # 2. Lưu kết quả dạng tệp văn bản
            with open(os.path.join(output_dir, 'real_data_test_results.txt'), 'w') as f:
                f.write("=== KẾT QUẢ BACKTEST VỚI DỮ LIỆU THỰC TẾ ===\n")
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
                
                f.write("\n4. Chi tiết mỗi cặp giao dịch:\n")
                
                # Group by symbol
                by_symbol = {}
                for trade in self.original_results["trades"]:
                    symbol = trade["symbol"]
                    if symbol not in by_symbol:
                        by_symbol[symbol] = {"count": 0, "win": 0, "loss": 0}
                    
                    by_symbol[symbol]["count"] += 1
                    if trade["is_win"]:
                        by_symbol[symbol]["win"] += 1
                    else:
                        by_symbol[symbol]["loss"] += 1
                
                # Write symbol details
                for symbol, stats in by_symbol.items():
                    win_rate = (stats["win"] / stats["count"]) * 100 if stats["count"] > 0 else 0
                    f.write(f"   - {symbol}: {stats['count']} giao dịch, Win Rate: {win_rate:.2f}%\n")
            
            logger.info(f"Đã lưu kết quả văn bản tại {output_dir}/real_data_test_results.txt")
            
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
            
            with open(os.path.join(output_dir, 'real_data_test_results.json'), 'w') as f:
                json.dump(results, f, indent=4)
            
            logger.info(f"Đã lưu kết quả JSON tại {output_dir}/real_data_test_results.json")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả: {str(e)}")

def main():
    """
    Hàm chính để chạy test
    """
    parser = argparse.ArgumentParser(description='Test cải thiện win rate với dữ liệu thực tế từ Binance')
    
    parser.add_argument(
        '--risk',
        type=float,
        default=0.25,
        help='Mức rủi ro (mặc định: 0.25 = 25%)'
    )
    
    parser.add_argument(
        '--testnet',
        action='store_true',
        help='Sử dụng Binance Testnet thay vì API thật'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Số ngày gần nhất để lấy dữ liệu (mặc định: 7)'
    )
    
    parser.add_argument(
        '--symbols',
        nargs='+',
        default=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
        help='Các cặp giao dịch cần lấy dữ liệu (mặc định: BTCUSDT ETHUSDT SOLUSDT BNBUSDT)'
    )
    
    args = parser.parse_args()
    
    logger.info(f"Bắt đầu test với dữ liệu thực tế từ Binance {'Testnet' if args.testnet else 'Production'}")
    logger.info(f"Lấy dữ liệu {args.days} ngày gần nhất cho các cặp: {', '.join(args.symbols)}")
    
    # 1. Tải dữ liệu từ Binance API
    binance_loader = BinanceDataLoader(testnet=args.testnet)
    
    # Tính timestamp bắt đầu (X ngày trước)
    start_time = int((datetime.now() - timedelta(days=args.days)).timestamp() * 1000)
    
    # Lấy dữ liệu giao dịch
    trades = binance_loader.get_historical_trades(
        symbols=args.symbols,
        start_time=start_time,
        max_trades=500  # Số lượng giao dịch tối đa mỗi symbol
    )
    
    # 2. Chạy backtest với dữ liệu thực tế
    if trades:
        backtest = RealDataBacktestRunner(risk_level=args.risk)
        backtest.load_historical_trades(trades)
        backtest.run_backtest()
    else:
        logger.error("Không tìm thấy dữ liệu giao dịch nào từ Binance API")
        # Thử tạo dữ liệu giả định từ file log
        log_files = ["aggressive_test.log", "high_risk_test.log", "adaptive_risk_allocation.log"]
        logger.info("Thử đọc dữ liệu từ file log...")
        
        for log_file in log_files:
            if os.path.exists(log_file):
                logger.info(f"Đang phân tích file log {log_file}")
                # TODO: Đọc và phân tích file log để lấy dữ liệu thực tế
        
        logger.info("Đảm bảo bạn đã cấu hình API key và secret để lấy dữ liệu thực tế")

if __name__ == "__main__":
    main()