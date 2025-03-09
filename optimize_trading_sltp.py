#!/usr/bin/env python3
"""
Script tối ưu hóa stop loss và take profit dựa trên phân tích đa khung thời gian

Script này sử dụng phân tích khung thời gian 5m, 1h và 4h để điều chỉnh thông số
stop loss và take profit một cách tự động và linh hoạt, nhằm tránh dừng lệnh quá sớm
khi xu hướng vẫn đúng.

Cách sử dụng:
    python optimize_trading_sltp.py --symbol BTCUSDT --mode analyze
    python optimize_trading_sltp.py --mode backtest --symbol BTCUSDT --days 30
    python optimize_trading_sltp.py --mode monitor
"""

import os
import sys
import json
import logging
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

from binance_api import BinanceAPI
from multi_timeframe_volatility_analyzer import MultiTimeframeVolatilityAnalyzer
from adaptive_stop_loss_manager import AdaptiveStopLossManager
from account_size_based_strategy import AccountSizeStrategy

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("optimize_trading_sltp")

class TradingParameterOptimizer:
    """Tối ưu hóa tham số giao dịch"""
    
    def __init__(self):
        """Khởi tạo tối ưu hóa tham số"""
        self.api = BinanceAPI()
        self.volatility_analyzer = MultiTimeframeVolatilityAnalyzer()
        self.sltp_manager = AdaptiveStopLossManager()
        self.strategy = AccountSizeStrategy()
        
        # Đảm bảo thư mục tồn tại
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Tạo các thư mục cần thiết"""
        directories = [
            "optimization_results",
            "configs",
            "reports",
            "data/positions"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """
        Phân tích một cặp tiền cụ thể
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả phân tích
        """
        # Lấy dữ liệu thị trường
        market_data = {}
        for timeframe in ["5m", "1h", "4h"]:
            try:
                candles = self.api.futures_klines(symbol=symbol, interval=timeframe, limit=100)
                
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                                 'close_time', 'quote_asset_volume', 'trades', 
                                                 'taker_buy_base', 'taker_buy_quote', 'ignore'])
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['open'] = pd.to_numeric(df['open'])
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])
                df['close'] = pd.to_numeric(df['close'])
                df['volume'] = pd.to_numeric(df['volume'])
                
                market_data[timeframe] = df
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu {timeframe} cho {symbol}: {str(e)}")
        
        # Kết quả phân tích biến động
        volatility_result = self.volatility_analyzer.calculate_weighted_volatility(symbol)
        
        # Lấy chiến lược tối ưu
        optimal_strategy, strategy_params = self.strategy.select_optimal_strategy(symbol, timeframe="1h")
        
        # Tính toán stop loss tối ưu
        current_price = float(self.api.futures_ticker_price(symbol=symbol)["price"])
        optimal_sltp = self.sltp_manager.calculate_optimal_stop_loss(
            symbol=symbol,
            side="BUY",  # Giả sử phía BUY cho phân tích
            entry_price=current_price,
            strategy_name=optimal_strategy
        )
        
        # Kết quả phân tích tổng thể
        analysis_result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "current_price": current_price,
            "optimal_strategy": optimal_strategy,
            "strategy_params": strategy_params,
            "volatility_analysis": volatility_result,
            "optimal_sltp": optimal_sltp,
            "market_data_summary": {}
        }
        
        # Tóm tắt dữ liệu thị trường
        for timeframe, df in market_data.items():
            if df is not None and not df.empty:
                high = df['high'].max()
                low = df['low'].min()
                close = df['close'].iloc[-1]
                volume = df['volume'].sum()
                
                price_range = high - low
                price_range_percent = (price_range / low) * 100
                
                analysis_result["market_data_summary"][timeframe] = {
                    "start_time": df['timestamp'].iloc[0].isoformat(),
                    "end_time": df['timestamp'].iloc[-1].isoformat(),
                    "candles": len(df),
                    "high": high,
                    "low": low,
                    "close": close,
                    "price_range": price_range,
                    "price_range_percent": price_range_percent,
                    "volume": volume
                }
        
        # Lưu kết quả phân tích
        self._save_analysis(symbol, analysis_result)
        
        return analysis_result
    
    def _save_analysis(self, symbol: str, analysis: Dict):
        """
        Lưu kết quả phân tích
        
        Args:
            symbol (str): Mã cặp tiền
            analysis (Dict): Kết quả phân tích
        """
        file_path = f"optimization_results/{symbol}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(file_path, 'w') as f:
                json.dump(analysis, f, indent=4)
            logger.info(f"Đã lưu kết quả phân tích cho {symbol} tại {file_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả phân tích: {str(e)}")
    
    def backtest_adaptive_sltp(self, symbol: str, days: int = 30) -> Dict:
        """
        Backtest stop loss thích ứng
        
        Args:
            symbol (str): Mã cặp tiền
            days (int): Số ngày lấy dữ liệu
            
        Returns:
            Dict: Kết quả backtest
        """
        # Lấy dữ liệu
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        try:
            # Lấy dữ liệu khung thời gian 1h
            candles = self.api.futures_klines(
                symbol=symbol, 
                interval="1h",
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000)
            )
            
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                             'close_time', 'quote_asset_volume', 'trades', 
                                             'taker_buy_base', 'taker_buy_quote', 'ignore'])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # Thêm chỉ báo
            df = self._add_indicators(df)
            
            # Mô phỏng giao dịch với stop loss thích ứng
            trades, performance = self._simulate_trades(df, symbol)
            
            # Vẽ biểu đồ
            self._plot_backtest_results(df, trades, symbol)
            
            # Kết quả backtest
            backtest_result = {
                "symbol": symbol,
                "period": f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}",
                "trades": trades,
                "performance": performance
            }
            
            # Lưu kết quả
            file_path = f"optimization_results/{symbol}_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(file_path, 'w') as f:
                json.dump(backtest_result, f, indent=4)
                
            logger.info(f"Đã lưu kết quả backtest cho {symbol} tại {file_path}")
            
            return backtest_result
            
        except Exception as e:
            logger.error(f"Lỗi khi backtest cho {symbol}: {str(e)}")
            return {"error": str(e)}
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm chỉ báo kỹ thuật vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            
        Returns:
            pd.DataFrame: DataFrame đã thêm chỉ báo
        """
        # Thêm EMA
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # Thêm RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).fillna(0)
        loss = -delta.where(delta < 0, 0).fillna(0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Thêm Bollinger Bands
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['stddev'] = df['close'].rolling(window=20).std()
        df['upper_band'] = df['sma20'] + 2 * df['stddev']
        df['lower_band'] = df['sma20'] - 2 * df['stddev']
        
        # Thêm ATR
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        return df
    
    def _simulate_trades(self, df: pd.DataFrame, symbol: str) -> Tuple[List[Dict], Dict]:
        """
        Mô phỏng giao dịch với stop loss thích ứng
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            symbol (str): Mã cặp tiền
            
        Returns:
            Tuple[List[Dict], Dict]: (Danh sách giao dịch, Thông số hiệu suất)
        """
        trades = []
        
        # Thử nghiệm với các loại stop loss khác nhau
        stop_loss_types = {
            "fixed": {"percent": 2.0},  # Stop loss cố định 2%
            "atr_based": {"multiplier": 1.5},  # Stop loss dựa trên ATR
            "adaptive": {"use_volatility": True}  # Stop loss thích ứng
        }
        
        for sl_type, sl_params in stop_loss_types.items():
            # Mô phỏng tín hiệu giao dịch
            in_position = False
            entry_price = 0
            entry_index = 0
            
            for i in range(20, len(df)):
                # Đơn giản hóa, chỉ sử dụng tín hiệu vượt lên trên EMA20
                if not in_position and df['close'].iloc[i] > df['ema20'].iloc[i] and df['close'].iloc[i-1] <= df['ema20'].iloc[i-1]:
                    # Tín hiệu mua
                    in_position = True
                    entry_price = df['close'].iloc[i]
                    entry_index = i
                    entry_date = df['timestamp'].iloc[i]
                    
                    # Tính stop loss dựa trên loại
                    if sl_type == "fixed":
                        stop_loss_percent = sl_params["percent"]
                        stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
                    elif sl_type == "atr_based":
                        multiplier = sl_params["multiplier"]
                        atr = df['atr'].iloc[i]
                        stop_loss_price = entry_price - (atr * multiplier)
                        stop_loss_percent = (entry_price - stop_loss_price) / entry_price * 100
                    else:  # adaptive
                        # Mô phỏng stop loss thích ứng
                        # Tăng stop loss khi volatility thấp
                        atr_percent = df['atr'].iloc[i] / df['close'].iloc[i] * 100
                        
                        if atr_percent < 1.0:
                            stop_loss_percent = 2.5  # Volatility thấp, stop loss lớn hơn
                        elif atr_percent < 2.0:
                            stop_loss_percent = 2.0  # Volatility trung bình
                        else:
                            stop_loss_percent = 1.5  # Volatility cao, stop loss chặt chẽ hơn
                            
                        stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
                        
                    # Ghi nhận trade mới
                    trade = {
                        "type": sl_type,
                        "entry_date": entry_date.strftime("%Y-%m-%d %H:%M"),
                        "entry_price": entry_price,
                        "entry_index": entry_index,
                        "stop_loss_percent": stop_loss_percent,
                        "stop_loss_price": stop_loss_price,
                        "exit_date": None,
                        "exit_price": None,
                        "exit_index": None,
                        "pnl_percent": None,
                        "exit_reason": None
                    }
                
                elif in_position:
                    # Kiểm tra điều kiện thoát
                    current_price = df['close'].iloc[i]
                    
                    # Điều kiện dừng lỗ
                    if current_price <= stop_loss_price:
                        # Thoát vị thế do dừng lỗ
                        exit_price = stop_loss_price
                        exit_date = df['timestamp'].iloc[i]
                        
                        # Tính lợi nhuận
                        pnl_percent = (exit_price - entry_price) / entry_price * 100
                        
                        # Cập nhật thông tin giao dịch
                        trade["exit_date"] = exit_date.strftime("%Y-%m-%d %H:%M")
                        trade["exit_price"] = exit_price
                        trade["exit_index"] = i
                        trade["pnl_percent"] = pnl_percent
                        trade["exit_reason"] = "stop_loss"
                        
                        # Thêm vào danh sách
                        trades.append(trade)
                        
                        # Reset trạng thái
                        in_position = False
                        
                    # Điều kiện chốt lời (ví dụ: khi giá dưới EMA20)
                    elif current_price < df['ema20'].iloc[i] and df['close'].iloc[i-1] >= df['ema20'].iloc[i-1]:
                        # Thoát vị thế do tín hiệu
                        exit_price = current_price
                        exit_date = df['timestamp'].iloc[i]
                        
                        # Tính lợi nhuận
                        pnl_percent = (exit_price - entry_price) / entry_price * 100
                        
                        # Cập nhật thông tin giao dịch
                        trade["exit_date"] = exit_date.strftime("%Y-%m-%d %H:%M")
                        trade["exit_price"] = exit_price
                        trade["exit_index"] = i
                        trade["pnl_percent"] = pnl_percent
                        trade["exit_reason"] = "signal"
                        
                        # Thêm vào danh sách
                        trades.append(trade)
                        
                        # Reset trạng thái
                        in_position = False
        
        # Tính toán hiệu suất
        performance = self._calculate_performance(trades)
        
        return trades, performance
    
    def _calculate_performance(self, trades: List[Dict]) -> Dict:
        """
        Tính toán hiệu suất giao dịch
        
        Args:
            trades (List[Dict]): Danh sách giao dịch
            
        Returns:
            Dict: Thông số hiệu suất
        """
        # Phân nhóm theo loại stop loss
        by_type = {}
        
        for trade in trades:
            sl_type = trade["type"]
            
            if sl_type not in by_type:
                by_type[sl_type] = []
                
            by_type[sl_type].append(trade)
        
        # Tính toán hiệu suất cho từng loại
        performance = {}
        
        for sl_type, type_trades in by_type.items():
            # Tính tổng lợi nhuận
            total_pnl = sum(trade["pnl_percent"] for trade in type_trades)
            
            # Tính số lệnh thắng/thua
            winning_trades = [trade for trade in type_trades if trade["pnl_percent"] > 0]
            losing_trades = [trade for trade in type_trades if trade["pnl_percent"] <= 0]
            
            # Tính tỷ lệ win/loss
            win_rate = len(winning_trades) / len(type_trades) if type_trades else 0
            
            # Phân loại theo lý do thoát
            stop_loss_exits = [trade for trade in type_trades if trade["exit_reason"] == "stop_loss"]
            signal_exits = [trade for trade in type_trades if trade["exit_reason"] == "signal"]
            
            # Tính hiệu suất trung bình
            avg_pnl = total_pnl / len(type_trades) if type_trades else 0
            avg_win = sum(trade["pnl_percent"] for trade in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(trade["pnl_percent"] for trade in losing_trades) / len(losing_trades) if losing_trades else 0
            
            # Lưu kết quả
            performance[sl_type] = {
                "total_trades": len(type_trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": win_rate,
                "stop_loss_exits": len(stop_loss_exits),
                "signal_exits": len(signal_exits),
                "total_pnl_percent": total_pnl,
                "average_pnl_percent": avg_pnl,
                "average_win_percent": avg_win,
                "average_loss_percent": avg_loss
            }
        
        return performance
    
    def _plot_backtest_results(self, df: pd.DataFrame, trades: List[Dict], symbol: str):
        """
        Vẽ biểu đồ kết quả backtest
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            trades (List[Dict]): Danh sách giao dịch
            symbol (str): Mã cặp tiền
        """
        try:
            # Tạo biểu đồ
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1]})
            
            # Vẽ giá
            ax1.plot(df.index, df['close'], label='Close Price', color='blue', alpha=0.6)
            ax1.plot(df.index, df['ema20'], label='EMA20', color='orange')
            
            # Phân nhóm trades theo loại stop loss
            by_type = {}
            for trade in trades:
                sl_type = trade["type"]
                
                if sl_type not in by_type:
                    by_type[sl_type] = []
                    
                by_type[sl_type].append(trade)
            
            # Màu cho từng loại
            colors = {
                "fixed": "red",
                "atr_based": "green",
                "adaptive": "purple"
            }
            
            # Vẽ điểm vào/ra cho từng loại
            for sl_type, type_trades in by_type.items():
                entries_x = [trade["entry_index"] for trade in type_trades]
                entries_y = [trade["entry_price"] for trade in type_trades]
                
                exits_x = [trade["exit_index"] for trade in type_trades if trade["exit_index"] is not None]
                exits_y = [trade["exit_price"] for trade in type_trades if trade["exit_price"] is not None]
                
                # Vẽ điểm vào
                ax1.scatter(entries_x, entries_y, marker='^', color=colors.get(sl_type, "blue"), 
                           s=100, label=f'{sl_type} Entries')
                
                # Vẽ điểm ra
                ax1.scatter(exits_x, exits_y, marker='v', color=colors.get(sl_type, "red"), 
                           s=100, label=f'{sl_type} Exits')
                
                # Vẽ đường nối giữa điểm vào và ra
                for trade in type_trades:
                    if trade["exit_index"] is not None:
                        ax1.plot([trade["entry_index"], trade["exit_index"]], 
                               [trade["entry_price"], trade["exit_price"]], 
                               color=colors.get(sl_type, "gray"), linestyle='--', alpha=0.5)
            
            # Vẽ biểu đồ hiệu suất
            performance = self._calculate_performance(trades)
            
            # Chuẩn bị dữ liệu cho biểu đồ hiệu suất
            labels = list(performance.keys())
            total_pnl = [performance[sl_type]["total_pnl_percent"] for sl_type in labels]
            win_rates = [performance[sl_type]["win_rate"] * 100 for sl_type in labels]
            
            x = np.arange(len(labels))
            width = 0.35
            
            # Vẽ biểu đồ cột
            rects1 = ax2.bar(x - width/2, total_pnl, width, label='Total PnL (%)')
            rects2 = ax2.bar(x + width/2, win_rates, width, label='Win Rate (%)')
            
            # Thêm nhãn
            ax2.set_xlabel('Stop Loss Type')
            ax2.set_ylabel('Percentage')
            ax2.set_title('Performance Comparison')
            ax2.set_xticks(x)
            ax2.set_xticklabels(labels)
            ax2.legend()
            
            # Thêm giá trị lên cột
            def autolabel(rects):
                for rect in rects:
                    height = rect.get_height()
                    ax2.annotate(f'{height:.1f}%',
                                xy=(rect.get_x() + rect.get_width() / 2, height),
                                xytext=(0, 3),
                                textcoords="offset points",
                                ha='center', va='bottom')
            
            autolabel(rects1)
            autolabel(rects2)
            
            # Thêm tiêu đề và chú thích
            ax1.set_title(f'{symbol} Backtest Results')
            ax1.set_ylabel('Price')
            ax1.legend()
            ax1.grid(True)
            
            # Lưu biểu đồ
            plt.tight_layout()
            plt.savefig(f"optimization_results/{symbol}_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.close()
            
            logger.info(f"Đã lưu biểu đồ backtest cho {symbol}")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ: {str(e)}")
    
    def run_monitor(self):
        """Chạy chế độ theo dõi liên tục"""
        try:
            self.sltp_manager.run_monitoring_loop()
        except KeyboardInterrupt:
            logger.info("Đã dừng theo dõi")
        except Exception as e:
            logger.error(f"Lỗi khi chạy chế độ theo dõi: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tối ưu hóa tham số giao dịch")
    parser.add_argument("--mode", type=str, choices=["analyze", "backtest", "monitor"], 
                        required=True, help="Chế độ hoạt động")
    parser.add_argument("--symbol", type=str, help="Mã cặp tiền")
    parser.add_argument("--days", type=int, default=30, help="Số ngày lấy dữ liệu (cho backtest)")
    
    args = parser.parse_args()
    
    optimizer = TradingParameterOptimizer()
    
    if args.mode == "analyze":
        if not args.symbol:
            parser.error("--symbol là bắt buộc khi sử dụng mode=analyze")
        
        # Phân tích cặp tiền
        result = optimizer.analyze_symbol(args.symbol)
        print(json.dumps(result, indent=2))
        
    elif args.mode == "backtest":
        if not args.symbol:
            parser.error("--symbol là bắt buộc khi sử dụng mode=backtest")
        
        # Backtest
        result = optimizer.backtest_adaptive_sltp(args.symbol, args.days)
        print(json.dumps(result, indent=2))
        
    elif args.mode == "monitor":
        # Chạy chế độ theo dõi
        optimizer.run_monitor()