#!/usr/bin/env python3
"""
Script để chạy bot giao dịch trong chế độ thực tế

Script này sẽ:
1. Lấy dữ liệu thực từ Binance API
2. Huấn luyện mô hình với dữ liệu thực tế mới nhất
3. Chạy bot giao dịch theo thời gian thực
"""

import os
import sys
import time
import logging
import json
from datetime import datetime
import pandas as pd
import numpy as np

# Đường dẫn tương đối
sys.path.append(".")
from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.advanced_ml_optimizer import AdvancedMLOptimizer
from app.market_regime_detector import MarketRegimeDetector
from app.advanced_ml_strategy import AdvancedMLStrategy
try:
    from app.composite_indicator import CompositeIndicator
except ImportError:
    # Sử dụng phiên bản từ thư mục gốc nếu không tìm thấy trong app/
    from composite_indicator import CompositeIndicator

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_bot_live.log')
    ]
)
logger = logging.getLogger('live_trading')

class LiveTradingBot:
    """Bot giao dịch trực tiếp sử dụng API Binance và mô hình ML đã huấn luyện"""
    
    def __init__(self, 
                 symbols=['BTCUSDT'], 
                 timeframes=['1h'],
                 initial_balance=1000.0,
                 risk_percentage=1.0,
                 max_positions=1,
                 train_lookback_days=30,
                 live_mode=False):
        """
        Khởi tạo bot giao dịch trực tiếp
        
        Args:
            symbols (list): Danh sách cặp giao dịch
            timeframes (list): Danh sách khung thời gian
            initial_balance (float): Số dư ban đầu
            risk_percentage (float): Phần trăm rủi ro trên mỗi giao dịch
            max_positions (int): Số vị thế tối đa cùng lúc
            train_lookback_days (int): Số ngày dữ liệu lịch sử để huấn luyện
            live_mode (bool): Chế độ giao dịch thực hay giả lập
        """
        self.symbols = symbols
        self.timeframes = timeframes
        self.primary_timeframe = timeframes[0]  # Sử dụng timeframe đầu tiên làm chính
        self.initial_balance = initial_balance
        self.risk_percentage = risk_percentage
        self.max_positions = max_positions
        self.train_lookback_days = train_lookback_days
        self.live_mode = live_mode
        self.active_positions = {}  # {symbol: position_info}
        
        # Khởi tạo API Binance
        self.api = BinanceAPI(
            api_key=os.environ.get("BINANCE_API_KEY"),
            api_secret=os.environ.get("BINANCE_API_SECRET"),
            testnet=not live_mode  # Sử dụng testnet nếu không phải chế độ live
        )
        
        # Khởi tạo bộ xử lý dữ liệu
        self.data_processor = DataProcessor(self.api)
        
        # Khởi tạo các bộ phân tích
        self.market_regime_detector = MarketRegimeDetector()
        self.composite_indicator = CompositeIndicator()
        
        # Khởi tạo bộ tối ưu hóa ML
        self.ml_optimizer = AdvancedMLOptimizer(
            base_models=["random_forest", "gradient_boosting"],
            use_model_per_regime=True,
            feature_selection=True,
            use_ensemble=True
        )
        
        # Đường dẫn lưu mô hình
        self.model_path = "models"
        os.makedirs(self.model_path, exist_ok=True)
        
        # Phát hiện mô hình có sẵn
        self._initialize_models()
        
        logger.info(f"Khởi tạo bot giao dịch: {symbols}, timeframes={timeframes}, live_mode={live_mode}")
    
    def _initialize_models(self):
        """Nạp mô hình có sẵn hoặc huấn luyện mô hình mới"""
        model_files = []
        for root, dirs, files in os.walk(self.model_path):
            for file in files:
                if file.endswith('.pkl'):
                    model_files.append(os.path.join(root, file))
        
        if model_files:
            # Tìm file mô hình mới nhất
            latest_model = max(model_files, key=os.path.getmtime)
            try:
                logger.info(f"Đang nạp mô hình từ: {latest_model}")
                self.ml_optimizer.load_models(latest_model)
                logger.info(f"Đã nạp mô hình thành công với {len(self.ml_optimizer.models)} mô hình")
                return
            except Exception as e:
                logger.error(f"Lỗi khi nạp mô hình: {str(e)}")
        
        logger.info("Không tìm thấy mô hình hoặc lỗi khi nạp. Sẽ huấn luyện mô hình mới.")
        self._train_new_models()
    
    def _train_new_models(self):
        """Huấn luyện mô hình mới với dữ liệu mới nhất"""
        for symbol in self.symbols:
            logger.info(f"Đang lấy dữ liệu huấn luyện cho {symbol} trong {self.train_lookback_days} ngày")
            df = self.data_processor.get_historical_data(
                symbol=symbol,
                interval=self.primary_timeframe,
                lookback_days=self.train_lookback_days
            )
            
            if df is None or df.empty:
                logger.error(f"Không thể lấy dữ liệu cho {symbol}")
                continue
            
            # Chuẩn bị dữ liệu
            X = self.ml_optimizer.prepare_features_for_prediction(df)
            y = self.ml_optimizer.prepare_target_for_training(df, lookahead=1, threshold=0.001)
            
            # Đảm bảo X và y có cùng kích thước
            if len(X) != len(y):
                min_len = min(len(X), len(y))
                X = X.iloc[:min_len]
                y = y[:min_len]
                logger.info(f"Điều chỉnh kích thước: X = {len(X)}, y = {len(y)}")
            
            logger.info(f"Huấn luyện mô hình cho {symbol} với {len(X)} mẫu, phân phối lớp: {np.unique(y, return_counts=True)}")
            
            # Phát hiện chế độ thị trường
            market_regime = self.market_regime_detector.detect_regime(df)
            
            # Huấn luyện mô hình
            self.ml_optimizer.train_models(X, y, regime=market_regime)
            
            # Lưu mô hình
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = self.ml_optimizer.save_models(f"{self.model_path}/ml_models_{timestamp}.pkl")
            logger.info(f"Đã lưu mô hình vào {model_filename}")
    
    def get_trading_signals(self, symbol):
        """
        Lấy tín hiệu giao dịch cho một cặp tiền
        
        Args:
            symbol (str): Cặp giao dịch
            
        Returns:
            dict: Thông tin tín hiệu giao dịch
        """
        # Lấy dữ liệu mới nhất
        df = self.data_processor.get_historical_data(
            symbol=symbol,
            interval=self.primary_timeframe,
            lookback_days=7  # Dữ liệu gần đây để dự đoán
        )
        
        if df is None or df.empty:
            logger.error(f"Không thể lấy dữ liệu cho {symbol}")
            return None
        
        # Phát hiện chế độ thị trường
        market_regime = self.market_regime_detector.detect_regime(df)
        
        # Tính toán chỉ báo tổng hợp
        composite_score = self.composite_indicator.calculate_composite_score(df)
        
        # Chuẩn bị tính năng và dự đoán
        X = self.ml_optimizer.prepare_features_for_prediction(df)
        X_latest = X.iloc[-1:].copy()  # Lấy dòng mới nhất
        
        # Dự đoán với mô hình ML
        y_pred, probas = self.ml_optimizer.predict(X_latest, regime=market_regime)
        
        # Thông tin dự đoán
        ml_signal = "neutral"
        confidence = 0.5
        
        if y_pred is not None and len(y_pred) > 0:
            if y_pred[0] == 1:
                ml_signal = "buy"
                confidence = probas[0][2] if probas is not None and probas.shape[1] > 2 else 0.7
            elif y_pred[0] == -1:
                ml_signal = "sell"
                confidence = probas[0][0] if probas is not None and probas.shape[1] > 0 else 0.7
            else:
                ml_signal = "neutral"
                confidence = probas[0][1] if probas is not None and probas.shape[1] > 1 else 0.7
        
        # Kết hợp tín hiệu
        composite_signal = "neutral"
        if composite_score['score'] > 0.5:
            composite_signal = "buy"
        elif composite_score['score'] < -0.5:
            composite_signal = "sell"
        
        # Quyết định cuối cùng
        final_signal = "neutral"
        if ml_signal == composite_signal and ml_signal != "neutral":
            final_signal = ml_signal
        elif ml_signal != "neutral" and confidence > 0.75:
            final_signal = ml_signal
        
        # Lấy giá hiện tại
        current_price = self.api.get_symbol_price(symbol)
        
        # Tín hiệu trả về
        signal_info = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "market_regime": market_regime,
            "ml_signal": ml_signal,
            "ml_confidence": float(confidence),
            "composite_signal": composite_signal,
            "composite_score": composite_score['score'],
            "final_signal": final_signal,
            "current_price": current_price
        }
        
        logger.info(f"Tín hiệu: {symbol} - {final_signal} (Confidence: {confidence:.2f}, Regime: {market_regime})")
        return signal_info
    
    def calculate_position_size(self, symbol, risk_percentage=None):
        """
        Tính toán kích thước vị thế dựa trên quản lý rủi ro
        
        Args:
            symbol (str): Cặp giao dịch
            risk_percentage (float): Phần trăm rủi ro, nếu None thì dùng giá trị mặc định
        
        Returns:
            float: Kích thước vị thế (số lượng)
        """
        if risk_percentage is None:
            risk_percentage = self.risk_percentage
        
        # Lấy số dư tài khoản
        if self.live_mode:
            account_info = self.api.get_account_info()
            if account_info and 'availableBalance' in account_info:
                balance = float(account_info['availableBalance'])
            else:
                balance = self.initial_balance
        else:
            balance = self.initial_balance
        
        # Tính toán kích thước vị thế dựa trên rủi ro
        risk_amount = balance * (risk_percentage / 100)
        
        # Lấy giá hiện tại
        current_price = self.api.get_symbol_price(symbol)
        if current_price is None:
            logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
            return 0
        
        # Tính số tiền có thể sử dụng (với đòn bẩy 1x)
        usable_amount = risk_amount * 10  # 10x đòn bẩy ảo
        
        # Tính số lượng có thể mua
        quantity = usable_amount / current_price
        
        # Làm tròn số lượng
        quantity = round(quantity, 6)  # 6 chữ số thập phân
        
        logger.info(f"Kích thước vị thế cho {symbol}: {quantity} ({risk_percentage}% rủi ro, giá: {current_price})")
        return quantity
    
    def execute_trade(self, symbol, signal, position_size=None):
        """
        Thực hiện lệnh giao dịch
        
        Args:
            symbol (str): Cặp giao dịch
            signal (str): Tín hiệu ('buy', 'sell', 'neutral')
            position_size (float): Kích thước vị thế, nếu None thì tự tính
            
        Returns:
            dict: Thông tin lệnh
        """
        if signal == "neutral":
            logger.info(f"Không có tín hiệu giao dịch cho {symbol}")
            return None
        
        # Kiểm tra nếu đã có vị thế
        if symbol in self.active_positions:
            current_position = self.active_positions[symbol]
            # Nếu tín hiệu trùng với vị thế hiện tại, không làm gì
            if (signal == "buy" and current_position["side"] == "BUY") or \
               (signal == "sell" and current_position["side"] == "SELL"):
                logger.info(f"Đã có vị thế {current_position['side']} cho {symbol}, bỏ qua tín hiệu {signal}")
                return None
            
            # Đóng vị thế hiện tại nếu tín hiệu ngược lại
            logger.info(f"Đóng vị thế {current_position['side']} cho {symbol} do có tín hiệu ngược lại: {signal}")
            self._close_position(symbol)
        
        # Kiểm tra số lượng vị thế hiện tại
        if len(self.active_positions) >= self.max_positions and symbol not in self.active_positions:
            logger.info(f"Đã đạt số lượng vị thế tối đa ({self.max_positions}), bỏ qua tín hiệu {signal} cho {symbol}")
            return None
        
        # Tính kích thước vị thế nếu không được cung cấp
        if position_size is None:
            position_size = self.calculate_position_size(symbol)
        
        if position_size <= 0:
            logger.error(f"Kích thước vị thế không hợp lệ: {position_size}")
            return None
        
        # Xác định hướng lệnh
        side = "BUY" if signal == "buy" else "SELL"
        
        # Lệnh thực tế hoặc giả lập
        if self.live_mode:
            try:
                order = self.api.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=position_size
                )
                
                # Lưu thông tin vị thế
                if order and 'orderId' in order:
                    entry_price = float(order.get('price', self.api.get_symbol_price(symbol)))
                    self.active_positions[symbol] = {
                        "symbol": symbol,
                        "side": side,
                        "quantity": position_size,
                        "entry_price": entry_price,
                        "entry_time": datetime.now(),
                        "order_id": order['orderId']
                    }
                    logger.info(f"Đã mở vị thế {side} cho {symbol}: {position_size} @ {entry_price}")
                    return order
                else:
                    logger.error(f"Lỗi khi tạo lệnh: {order}")
                    return None
            except Exception as e:
                logger.error(f"Lỗi khi thực hiện lệnh: {str(e)}")
                return None
        else:
            # Giả lập lệnh
            current_price = self.api.get_symbol_price(symbol)
            self.active_positions[symbol] = {
                "symbol": symbol,
                "side": side,
                "quantity": position_size,
                "entry_price": current_price,
                "entry_time": datetime.now(),
                "order_id": f"sim_{int(time.time())}"
            }
            logger.info(f"[GIẢLẬP] Đã mở vị thế {side} cho {symbol}: {position_size} @ {current_price}")
            
            return {
                "symbol": symbol,
                "side": side,
                "quantity": position_size,
                "price": current_price,
                "orderId": self.active_positions[symbol]["order_id"],
                "status": "FILLED",
                "simulated": True
            }
    
    def _close_position(self, symbol):
        """
        Đóng vị thế
        
        Args:
            symbol (str): Cặp giao dịch
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if symbol not in self.active_positions:
            logger.warning(f"Không có vị thế nào để đóng cho {symbol}")
            return False
        
        position = self.active_positions[symbol]
        close_side = "SELL" if position["side"] == "BUY" else "BUY"
        
        if self.live_mode:
            try:
                order = self.api.create_order(
                    symbol=symbol,
                    side=close_side,
                    order_type="MARKET",
                    quantity=position["quantity"]
                )
                
                if order and 'orderId' in order:
                    exit_price = float(order.get('price', self.api.get_symbol_price(symbol)))
                    
                    # Tính P&L
                    if position["side"] == "BUY":
                        pnl = (exit_price - position["entry_price"]) * position["quantity"]
                    else:
                        pnl = (position["entry_price"] - exit_price) * position["quantity"]
                    
                    # Log kết quả
                    logger.info(f"Đã đóng vị thế {position['side']} cho {symbol}: {position['quantity']} @ {exit_price}, P&L: {pnl:.2f}")
                    
                    # Lưu lịch sử giao dịch
                    self._save_trade_history(position, exit_price, pnl)
                    
                    # Xóa khỏi vị thế đang mở
                    del self.active_positions[symbol]
                    return True
                else:
                    logger.error(f"Lỗi khi đóng vị thế: {order}")
                    return False
            except Exception as e:
                logger.error(f"Lỗi khi đóng vị thế: {str(e)}")
                return False
        else:
            # Giả lập đóng vị thế
            current_price = self.api.get_symbol_price(symbol)
            
            # Tính P&L
            if position["side"] == "BUY":
                pnl = (current_price - position["entry_price"]) * position["quantity"]
            else:
                pnl = (position["entry_price"] - current_price) * position["quantity"]
            
            # Log kết quả
            logger.info(f"[GIẢLẬP] Đã đóng vị thế {position['side']} cho {symbol}: {position['quantity']} @ {current_price}, P&L: {pnl:.2f}")
            
            # Lưu lịch sử giao dịch
            self._save_trade_history(position, current_price, pnl)
            
            # Xóa khỏi vị thế đang mở
            del self.active_positions[symbol]
            return True
    
    def _save_trade_history(self, position, exit_price, pnl):
        """Lưu lịch sử giao dịch vào file"""
        trade_history_file = "trade_history.json"
        
        # Tạo dữ liệu giao dịch
        trade_data = {
            "symbol": position["symbol"],
            "side": position["side"],
            "quantity": position["quantity"],
            "entry_price": position["entry_price"],
            "entry_time": position["entry_time"].isoformat(),
            "exit_price": exit_price,
            "exit_time": datetime.now().isoformat(),
            "pnl": pnl,
            "order_id": position["order_id"]
        }
        
        # Nạp lịch sử giao dịch hiện tại
        trades = []
        if os.path.exists(trade_history_file):
            try:
                with open(trade_history_file, 'r') as f:
                    trades = json.load(f)
            except Exception as e:
                logger.error(f"Lỗi khi đọc file lịch sử giao dịch: {str(e)}")
        
        # Thêm giao dịch mới
        trades.append(trade_data)
        
        # Lưu lại
        try:
            with open(trade_history_file, 'w') as f:
                json.dump(trades, f, indent=2)
            logger.info(f"Đã lưu giao dịch vào lịch sử: {trade_data['symbol']} {trade_data['side']} P&L: {trade_data['pnl']:.2f}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu file lịch sử giao dịch: {str(e)}")
    
    def check_and_update_positions(self):
        """Kiểm tra và cập nhật trạng thái các vị thế hiện tại"""
        for symbol, position in list(self.active_positions.items()):
            # Lấy giá hiện tại
            current_price = self.api.get_symbol_price(symbol)
            if current_price is None:
                logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
                continue
            
            # Tính P&L tạm thời
            if position["side"] == "BUY":
                unrealized_pnl = (current_price - position["entry_price"]) * position["quantity"]
            else:
                unrealized_pnl = (position["entry_price"] - current_price) * position["quantity"]
            
            # Kiểm tra điều kiện chốt lời / cắt lỗ đơn giản
            entry_price = position["entry_price"]
            take_profit_pct = 5.0  # 5% chốt lời
            stop_loss_pct = -2.0   # 2% cắt lỗ
            
            pnl_pct = (unrealized_pnl / (entry_price * position["quantity"])) * 100
            
            if pnl_pct >= take_profit_pct:
                logger.info(f"Đạt mục tiêu chốt lời {take_profit_pct}% cho {symbol}, đóng vị thế")
                self._close_position(symbol)
            elif pnl_pct <= stop_loss_pct:
                logger.info(f"Đạt ngưỡng cắt lỗ {stop_loss_pct}% cho {symbol}, đóng vị thế")
                self._close_position(symbol)
            else:
                logger.info(f"Vị thế {symbol} {position['side']}: P&L tạm thời = {unrealized_pnl:.2f} ({pnl_pct:.2f}%)")
    
    def run(self, check_interval=300):
        """
        Chạy bot giao dịch liên tục
        
        Args:
            check_interval (int): Thời gian giữa các lần kiểm tra (giây)
        """
        logger.info(f"Bắt đầu chạy bot giao dịch {'LIVE' if self.live_mode else 'SIMULATION'}")
        
        try:
            while True:
                # Kiểm tra và cập nhật các vị thế hiện tại
                self.check_and_update_positions()
                
                # Kiểm tra tín hiệu giao dịch cho mỗi cặp
                for symbol in self.symbols:
                    signal_info = self.get_trading_signals(symbol)
                    
                    if signal_info is None:
                        continue
                    
                    # Thực hiện giao dịch nếu có tín hiệu
                    if signal_info['final_signal'] != 'neutral':
                        self.execute_trade(symbol, signal_info['final_signal'])
                
                # Hiển thị trạng thái hiện tại
                self._print_status()
                
                # Chờ đến lần kiểm tra tiếp theo
                logger.info(f"Đang chờ {check_interval} giây đến lần kiểm tra tiếp theo...")
                time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("Bot đã bị dừng bởi người dùng")
        except Exception as e:
            logger.error(f"Lỗi không mong muốn: {str(e)}")
        finally:
            # Đóng tất cả các vị thế khi kết thúc
            self._close_all_positions()
            logger.info("Bot đã dừng, tất cả các vị thế đã được đóng")
    
    def _print_status(self):
        """In trạng thái hiện tại của bot"""
        logger.info("-" * 50)
        logger.info(f"Trạng thái bot ({datetime.now().isoformat()})")
        logger.info(f"Số vị thế đang mở: {len(self.active_positions)}")
        
        for symbol, position in self.active_positions.items():
            current_price = self.api.get_symbol_price(symbol)
            
            if current_price is None:
                logger.warning(f"Không thể lấy giá hiện tại cho {symbol}")
                continue
            
            # Tính P&L tạm thời
            if position["side"] == "BUY":
                unrealized_pnl = (current_price - position["entry_price"]) * position["quantity"]
            else:
                unrealized_pnl = (position["entry_price"] - current_price) * position["quantity"]
            
            pnl_pct = (unrealized_pnl / (position["entry_price"] * position["quantity"])) * 100
            
            logger.info(f"  {symbol} {position['side']}: {position['quantity']} @ {position['entry_price']} (Giá hiện tại: {current_price})")
            logger.info(f"    P&L tạm thời: {unrealized_pnl:.2f} ({pnl_pct:.2f}%)")
            logger.info(f"    Thời gian mở: {position['entry_time'].isoformat()}")
        
        logger.info("-" * 50)
    
    def _close_all_positions(self):
        """Đóng tất cả các vị thế"""
        for symbol in list(self.active_positions.keys()):
            logger.info(f"Đóng vị thế {symbol} khi kết thúc bot")
            self._close_position(symbol)

def main():
    """Hàm chính để chạy bot giao dịch"""
    # Cấu hình bot
    bot = LiveTradingBot(
        symbols=['BTCUSDT'],  # Các cặp giao dịch
        timeframes=['1h'],    # Khung thời gian
        initial_balance=1000.0,  # Số dư ban đầu (USD)
        risk_percentage=1.0,     # % rủi ro trên mỗi giao dịch
        max_positions=1,         # Số vị thế tối đa đồng thời
        train_lookback_days=30,  # Số ngày dữ liệu huấn luyện
        live_mode=False          # Chế độ giả lập (False) hoặc thực tế (True)
    )
    
    # Chạy huấn luyện mô hình với dữ liệu mới nhất
    bot._train_new_models()
    
    # Chạy bot với chu kỳ kiểm tra 5 phút (300 giây)
    bot.run(check_interval=300)

if __name__ == "__main__":
    main()