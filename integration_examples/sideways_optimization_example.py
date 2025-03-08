#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ví dụ tích hợp SidewaysMarketOptimizer với EnhancedTrailingStopManager

File này minh họa cách tích hợp các module tối ưu hóa sideways 
với hệ thống giao dịch hiện có để cải thiện hiệu suất.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json

# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import các module
from sideways_market_optimizer import SidewaysMarketOptimizer
from enhanced_trailing_stop_manager import EnhancedTrailingStopManager

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/integration_example.log')
    ]
)

logger = logging.getLogger('integration_example')

class OptimizedTradingSystem:
    """
    Hệ thống giao dịch tích hợp tối ưu hóa cho thị trường sideway
    """
    
    def __init__(self, api_client=None):
        """
        Khởi tạo hệ thống giao dịch
        
        Args:
            api_client: Client API để thực hiện các thao tác thị trường
        """
        self.api_client = api_client
        
        # Khởi tạo các module tối ưu hóa
        self.sideways_optimizer = SidewaysMarketOptimizer()
        self.trailing_manager = EnhancedTrailingStopManager(api_client=api_client)
        
        # Cài đặt cấu hình giao dịch
        self.base_position_size = 1.0  # Kích thước vị thế cơ sở
        self.tracked_positions = {}  # Theo dõi các vị thế đang mở
        
        # Đảm bảo thư mục logs tồn tại
        os.makedirs('logs', exist_ok=True)
        os.makedirs('charts/integration', exist_ok=True)
        
        logger.info("Đã khởi tạo OptimizedTradingSystem")
    
    def analyze_market_condition(self, symbol: str, df: pd.DataFrame) -> dict:
        """
        Phân tích điều kiện thị trường và đưa ra điều chỉnh
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            
        Returns:
            dict: Kết quả phân tích và điều chỉnh
        """
        # Phát hiện thị trường sideway
        is_sideway = self.sideways_optimizer.detect_sideways_market(df)
        
        # Lấy các điều chỉnh chiến lược
        strategy_adjustments = self.sideways_optimizer.adjust_strategy_for_sideways(self.base_position_size)
        
        # Tạo báo cáo phân tích
        if is_sideway:
            # Tạo biểu đồ phân tích
            chart_path = self.sideways_optimizer.visualize_sideways_detection(
                df, symbol, custom_path='charts/integration'
            )
            
            # Lấy điều chỉnh TP/SL
            tp_sl_adjustments = self.sideways_optimizer.optimize_takeprofit_stoploss(df)
            
            # Tạo báo cáo
            report = {
                "symbol": symbol,
                "is_sideway": is_sideway,
                "sideway_score": self.sideways_optimizer.sideways_score,
                "position_size": strategy_adjustments['position_size'],
                "use_mean_reversion": strategy_adjustments['use_mean_reversion'],
                "tp_adjustment": tp_sl_adjustments['tp_adjustment'],
                "sl_adjustment": tp_sl_adjustments['sl_adjustment'],
                "chart_path": chart_path,
                "breakout_prediction": self.sideways_optimizer.predict_breakout_direction(df),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Phát hiện thị trường sideway cho {symbol} với score {self.sideways_optimizer.sideways_score:.2f}")
        else:
            report = {
                "symbol": symbol,
                "is_sideway": False,
                "sideway_score": self.sideways_optimizer.sideways_score,
                "position_size": self.base_position_size,
                "use_mean_reversion": False,
                "tp_adjustment": 1.0,
                "sl_adjustment": 1.0,
                "chart_path": "",
                "breakout_prediction": "unknown",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Thị trường {symbol} KHÔNG ở trạng thái sideway (score: {self.sideways_optimizer.sideways_score:.2f})")
        
        return report
    
    def generate_trading_signals(self, symbol: str, df: pd.DataFrame, market_analysis: dict) -> pd.DataFrame:
        """
        Tạo tín hiệu giao dịch dựa trên phân tích thị trường
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            df (pd.DataFrame): DataFrame với dữ liệu OHLC
            market_analysis (dict): Kết quả phân tích thị trường
            
        Returns:
            pd.DataFrame: DataFrame với tín hiệu giao dịch
        """
        # Sao chép dữ liệu để không làm thay đổi dữ liệu gốc
        signals_df = df.copy()
        
        # Tạo các cột tín hiệu mặc định
        signals_df['buy_signal'] = False
        signals_df['sell_signal'] = False
        
        # Nếu là thị trường sideway và sử dụng mean reversion
        if market_analysis['is_sideway'] and market_analysis['use_mean_reversion']:
            logger.info(f"Sử dụng chiến lược mean reversion cho {symbol}")
            # Sử dụng chiến lược mean reversion
            signals_df = self.sideways_optimizer.generate_mean_reversion_signals(df)
        else:
            # Sử dụng chiến lược thông thường (ví dụ: trend following)
            # Đây chỉ là ví dụ đơn giản, cần thay thế bằng chiến lược thực tế
            signals_df['sma_short'] = signals_df['close'].rolling(window=10).mean()
            signals_df['sma_long'] = signals_df['close'].rolling(window=50).mean()
            
            # Tín hiệu mua: SMA ngắn cắt lên trên SMA dài
            signals_df['buy_signal'] = (signals_df['sma_short'] > signals_df['sma_long']) & \
                                      (signals_df['sma_short'].shift(1) <= signals_df['sma_long'].shift(1))
            
            # Tín hiệu bán: SMA ngắn cắt xuống dưới SMA dài
            signals_df['sell_signal'] = (signals_df['sma_short'] < signals_df['sma_long']) & \
                                       (signals_df['sma_short'].shift(1) >= signals_df['sma_long'].shift(1))
        
        return signals_df
    
    def execute_trade(self, symbol: str, signal_type: str, price: float, 
                     market_analysis: dict) -> str:
        """
        Thực hiện giao dịch dựa trên tín hiệu
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            signal_type (str): Loại tín hiệu ('buy' hoặc 'sell')
            price (float): Giá hiện tại
            market_analysis (dict): Kết quả phân tích thị trường
            
        Returns:
            str: ID theo dõi nếu thành công, chuỗi rỗng nếu thất bại
        """
        if not self.api_client:
            logger.warning(f"Không có API client để thực hiện giao dịch {symbol}")
            return ""
        
        try:
            # Tính kích thước vị thế dựa trên phân tích thị trường
            position_size = market_analysis['position_size']
            
            # Tính stop loss và take profit
            base_sl_percent = 0.05  # 5%
            base_tp_percent = 0.15  # 15%
            
            # Điều chỉnh theo market_analysis
            sl_percent = base_sl_percent * market_analysis['sl_adjustment']
            tp_percent = base_tp_percent * market_analysis['tp_adjustment']
            
            if signal_type == 'buy':
                direction = 'long'
                stop_loss_price = price * (1 - sl_percent)
                take_profit_price = price * (1 + tp_percent)
                
                # Đặt lệnh mua
                order_result = self.api_client.create_order(
                    symbol=symbol,
                    side='BUY',
                    type='MARKET',
                    quantity=position_size
                )
                
                order_id = order_result.get('orderId', 'unknown')
                
            elif signal_type == 'sell':
                direction = 'short'
                stop_loss_price = price * (1 + sl_percent)
                take_profit_price = price * (1 - tp_percent)
                
                # Đặt lệnh bán
                order_result = self.api_client.create_order(
                    symbol=symbol,
                    side='SELL',
                    type='MARKET',
                    quantity=position_size
                )
                
                order_id = order_result.get('orderId', 'unknown')
            else:
                logger.warning(f"Loại tín hiệu không hợp lệ: {signal_type}")
                return ""
            
            # Đăng ký với trailing stop manager
            tracking_id = self.trailing_manager.register_position(
                symbol=symbol,
                order_id=str(order_id),
                entry_price=price,
                position_size=position_size,
                direction=direction,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price
            )
            
            # Lưu vào tracked_positions
            self.tracked_positions[tracking_id] = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': price,
                'position_size': position_size,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'is_sideway': market_analysis['is_sideway'],
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Đã thực hiện giao dịch {signal_type} {symbol} với kích thước {position_size} tại {price}")
            logger.info(f"Stop Loss: {stop_loss_price}, Take Profit: {take_profit_price}")
            
            return tracking_id
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện giao dịch {symbol}: {str(e)}")
            return ""
    
    def update_market_prices(self, symbol: str, current_price: float) -> None:
        """
        Cập nhật giá mới và xử lý trailing stop
        
        Args:
            symbol (str): Ký hiệu tiền tệ
            current_price (float): Giá hiện tại
        """
        # Cập nhật giá trong trailing manager
        self.trailing_manager.update_price(symbol, current_price)
        
        # Lấy danh sách vị thế hiện tại
        active_positions = self.trailing_manager.get_active_positions()
        
        # Cập nhật tracked_positions để loại bỏ các vị thế đã đóng
        closed_positions = []
        for tracking_id in list(self.tracked_positions.keys()):
            if tracking_id not in active_positions:
                closed_positions.append(tracking_id)
                logger.info(f"Đã đóng vị thế {tracking_id}")
                
                # Lấy thông tin vị thế đã đóng
                position_info = self.tracked_positions.pop(tracking_id)
                
                # Lưu thông tin giao dịch nếu cần
                self._save_trade_history(tracking_id, position_info, current_price)
        
        # Ghi log các vị thế đã đóng
        if closed_positions:
            logger.info(f"Đã đóng {len(closed_positions)} vị thế: {', '.join(closed_positions)}")
            
            # Cập nhật hiệu suất
            self._update_performance_stats()
    
    def _save_trade_history(self, tracking_id: str, position_info: dict, close_price: float) -> None:
        """
        Lưu lịch sử giao dịch
        
        Args:
            tracking_id (str): ID theo dõi
            position_info (dict): Thông tin vị thế
            close_price (float): Giá đóng vị thế
        """
        # Tính lợi nhuận
        direction = position_info['direction']
        entry_price = position_info['entry_price']
        
        if direction == 'long':
            profit_percent = (close_price - entry_price) / entry_price * 100
        else:  # short
            profit_percent = (entry_price - close_price) / entry_price * 100
        
        # Chuẩn bị dữ liệu giao dịch
        trade_data = {
            'tracking_id': tracking_id,
            'symbol': position_info['symbol'],
            'direction': direction,
            'entry_price': entry_price,
            'close_price': close_price,
            'position_size': position_info['position_size'],
            'profit_percent': profit_percent,
            'is_sideway': position_info.get('is_sideway', False),
            'entry_time': position_info.get('timestamp', ''),
            'close_time': datetime.now().isoformat()
        }
        
        # Đảm bảo thư mục tồn tại
        os.makedirs('logs/trades', exist_ok=True)
        
        # Lưu vào file
        file_path = os.path.join(
            'logs/trades', 
            f"trade_{position_info['symbol']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(file_path, 'w') as f:
            json.dump(trade_data, f, indent=4)
        
        logger.info(f"Đã lưu thông tin giao dịch {tracking_id} vào {file_path}")
        logger.info(f"Lợi nhuận: {profit_percent:.2f}%")
    
    def _update_performance_stats(self) -> None:
        """
        Cập nhật thống kê hiệu suất
        """
        # Lấy thống kê từ trailing stop manager
        trailing_stats = self.trailing_manager.get_performance_stats()
        
        # Đường dẫn thư mục lưu lịch sử giao dịch
        trades_dir = 'logs/trades'
        
        if not os.path.exists(trades_dir):
            return
        
        # Lấy danh sách file trong thư mục
        trade_files = [f for f in os.listdir(trades_dir) if f.endswith('.json')]
        
        # Thống kê
        trades_data = []
        sideway_trades = []
        normal_trades = []
        
        # Đọc từng file
        for file_name in trade_files:
            file_path = os.path.join(trades_dir, file_name)
            
            try:
                with open(file_path, 'r') as f:
                    trade_data = json.load(f)
                
                trades_data.append(trade_data)
                
                # Phân loại giao dịch
                if trade_data.get('is_sideway', False):
                    sideway_trades.append(trade_data)
                else:
                    normal_trades.append(trade_data)
                    
            except Exception as e:
                logger.error(f"Lỗi khi đọc file {file_path}: {str(e)}")
        
        # Tính thống kê
        if trades_data:
            # Tổng số giao dịch
            total_trades = len(trades_data)
            
            # Tỷ lệ thắng/thua
            winning_trades = sum(1 for trade in trades_data if trade.get('profit_percent', 0) > 0)
            win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
            
            # Lợi nhuận trung bình
            avg_profit = sum(trade.get('profit_percent', 0) for trade in trades_data) / total_trades if total_trades > 0 else 0
            
            # Thống kê riêng cho giao dịch sideway
            sideway_win_rate = 0
            sideway_avg_profit = 0
            
            if sideway_trades:
                sideway_winning = sum(1 for trade in sideway_trades if trade.get('profit_percent', 0) > 0)
                sideway_win_rate = sideway_winning / len(sideway_trades) * 100
                sideway_avg_profit = sum(trade.get('profit_percent', 0) for trade in sideway_trades) / len(sideway_trades)
            
            # Thống kê riêng cho giao dịch bình thường
            normal_win_rate = 0
            normal_avg_profit = 0
            
            if normal_trades:
                normal_winning = sum(1 for trade in normal_trades if trade.get('profit_percent', 0) > 0)
                normal_win_rate = normal_winning / len(normal_trades) * 100
                normal_avg_profit = sum(trade.get('profit_percent', 0) for trade in normal_trades) / len(normal_trades)
            
            # Ghi log thống kê
            logger.info(f"===== Thống kê hiệu suất =====")
            logger.info(f"Tổng số giao dịch: {total_trades}")
            logger.info(f"Tỷ lệ thắng: {win_rate:.2f}%")
            logger.info(f"Lợi nhuận trung bình: {avg_profit:.2f}%")
            logger.info(f"Sideway - Tỷ lệ thắng: {sideway_win_rate:.2f}%")
            logger.info(f"Sideway - Lợi nhuận TB: {sideway_avg_profit:.2f}%")
            logger.info(f"Normal - Tỷ lệ thắng: {normal_win_rate:.2f}%")
            logger.info(f"Normal - Lợi nhuận TB: {normal_avg_profit:.2f}%")
            logger.info(f"Trailing stats - Thành công: {trailing_stats['successful_trails']}")
            logger.info(f"Trailing stats - Profit saved: {trailing_stats['profit_saved']:.2f}%")

# Hàm mô phỏng để demo
def run_simulation():
    """
    Chạy mô phỏng để demo tích hợp
    """
    # Tạo mock API client
    class MockAPIClient:
        def create_order(self, **kwargs):
            print(f"Mock API: Tạo lệnh với tham số {kwargs}")
            return {"orderId": "123456", "status": "SUCCESS", **kwargs}
            
        def get_klines(self, **kwargs):
            # Tạo dữ liệu giả
            import random
            import time
            
            now = time.time() * 1000  # ms
            klines = []
            
            base_price = 50000  # Giá cơ sở
            
            for i in range(kwargs.get('limit', 100)):
                # [timestamp, open, high, low, close, volume, ...]
                timestamp = now - (kwargs.get('limit', 100) - i) * 60 * 60 * 1000  # 1h interval
                close = base_price + random.uniform(-1000, 1000)
                klines.append([
                    timestamp,
                    close - random.uniform(-100, 100),  # open
                    close + random.uniform(0, 200),  # high
                    close - random.uniform(0, 200),  # low
                    close,  # close
                    random.uniform(100, 1000)  # volume
                ])
            
            return klines
    
    # Tạo dữ liệu mẫu cho thị trường sideway và bình thường
    def generate_sample_data(market_type="normal"):
        """Tạo dữ liệu mẫu"""
        np.random.seed(42)  # Để kết quả có tính lặp lại
        
        # Tạo dữ liệu cơ sở
        n_samples = 200
        dates = pd.date_range(start='2023-01-01', periods=n_samples, freq='1H')
        
        if market_type == "sideways":
            # Tạo giá sideway (biến động thấp quanh giá trung bình)
            base_price = 1000
            volatility = 0.005  # 0.5%
            prices = np.random.normal(0, volatility, n_samples).cumsum() + base_price
            
            # Tạo vùng sideway rõ ràng
            prices = np.clip(prices, base_price * 0.98, base_price * 1.02)
        else:
            # Tạo giá có xu hướng
            base_price = 1000
            drift = 0.001  # 0.1% mỗi giai đoạn
            volatility = 0.01  # 1%
            random_walk = np.random.normal(drift, volatility, n_samples).cumsum()
            prices = base_price * (1 + random_walk)
        
        # Tạo DataFrame
        df = pd.DataFrame({
            'open': prices * 0.999,
            'high': prices * 1.002,
            'low': prices * 0.998,
            'close': prices,
            'volume': np.random.randint(1000, 10000, n_samples)
        }, index=dates)
        
        return df
    
    # Tạo dữ liệu mẫu
    sideways_data = generate_sample_data("sideways")
    normal_data = generate_sample_data("normal")
    
    # Khởi tạo hệ thống với mock API
    trading_system = OptimizedTradingSystem(api_client=MockAPIClient())
    
    # Demo với thị trường sideway
    print("\n===== Demo với thị trường SIDEWAY =====")
    
    # Phân tích thị trường
    analysis = trading_system.analyze_market_condition("ADAUSDT", sideways_data)
    print(f"Phân tích thị trường: {'SIDEWAY' if analysis['is_sideway'] else 'NORMAL'}")
    print(f"Sideways score: {analysis['sideway_score']:.2f}")
    print(f"Kích thước vị thế: {analysis['position_size']}")
    print(f"Sử dụng mean reversion: {analysis['use_mean_reversion']}")
    print(f"Điều chỉnh TP: {analysis['tp_adjustment']:.2f}x")
    print(f"Điều chỉnh SL: {analysis['sl_adjustment']:.2f}x")
    
    # Tạo tín hiệu
    signals = trading_system.generate_trading_signals("ADAUSDT", sideways_data, analysis)
    buy_signals = signals[signals['buy_signal'] == True]
    sell_signals = signals[signals['sell_signal'] == True]
    
    print(f"Số tín hiệu mua: {len(buy_signals)}")
    print(f"Số tín hiệu bán: {len(sell_signals)}")
    
    # Mô phỏng giao dịch
    if len(buy_signals) > 0:
        print("\nMô phỏng giao dịch mua:")
        signal_row = buy_signals.iloc[0]
        current_price = signal_row['close']
        
        tracking_id = trading_system.execute_trade("ADAUSDT", "buy", current_price, analysis)
        print(f"Đã mở vị thế với ID: {tracking_id}")
        
        # Mô phỏng cập nhật giá
        print("\nMô phỏng cập nhật giá:")
        for i in range(5):
            # Giá dao động nhẹ
            price = current_price * (1 + np.random.uniform(-0.01, 0.01))
            print(f"Cập nhật giá: {price:.2f}")
            trading_system.update_market_prices("ADAUSDT", price)
    
    # Demo với thị trường bình thường
    print("\n===== Demo với thị trường NORMAL =====")
    
    # Phân tích thị trường
    analysis = trading_system.analyze_market_condition("BTCUSDT", normal_data)
    print(f"Phân tích thị trường: {'SIDEWAY' if analysis['is_sideway'] else 'NORMAL'}")
    print(f"Sideways score: {analysis['sideway_score']:.2f}")
    print(f"Kích thước vị thế: {analysis['position_size']}")
    print(f"Sử dụng mean reversion: {analysis['use_mean_reversion']}")
    print(f"Điều chỉnh TP: {analysis['tp_adjustment']:.2f}x")
    print(f"Điều chỉnh SL: {analysis['sl_adjustment']:.2f}x")
    
    # Tạo tín hiệu
    signals = trading_system.generate_trading_signals("BTCUSDT", normal_data, analysis)
    buy_signals = signals[signals['buy_signal'] == True]
    sell_signals = signals[signals['sell_signal'] == True]
    
    print(f"Số tín hiệu mua: {len(buy_signals)}")
    print(f"Số tín hiệu bán: {len(sell_signals)}")
    
    # Mô phỏng giao dịch
    if len(buy_signals) > 0:
        print("\nMô phỏng giao dịch mua:")
        signal_row = buy_signals.iloc[0]
        current_price = signal_row['close']
        
        tracking_id = trading_system.execute_trade("BTCUSDT", "buy", current_price, analysis)
        print(f"Đã mở vị thế với ID: {tracking_id}")
        
        # Mô phỏng cập nhật giá
        print("\nMô phỏng cập nhật giá:")
        for i in range(5):
            # Giá tăng mạnh hơn
            price = current_price * (1 + 0.01 * (i+1))
            print(f"Cập nhật giá: {price:.2f}")
            trading_system.update_market_prices("BTCUSDT", price)

if __name__ == "__main__":
    # Chạy demo
    print("Bắt đầu chạy demo tích hợp SidewaysMarketOptimizer và EnhancedTrailingStopManager")
    
    try:
        run_simulation()
        print("\nHoàn thành demo!")
    except Exception as e:
        print(f"Lỗi khi chạy demo: {str(e)}")