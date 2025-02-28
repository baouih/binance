#!/usr/bin/env python3
"""
Script để chạy bot giao dịch đa đồng tiền với ML nâng cao

Script này sẽ:
1. Lấy dữ liệu thực từ Binance API cho nhiều cặp giao dịch
2. Huấn luyện và quản lý mô hình ML riêng biệt cho mỗi cặp và chế độ thị trường
3. Chạy bot giao dịch đa đồng tiền với thông báo qua Telegram
"""

import os
import sys
import time
import logging
import json
import threading
import signal
import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Đường dẫn tương đối
sys.path.append(".")
from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.advanced_ml_optimizer import AdvancedMLOptimizer
from app.market_regime_detector import MarketRegimeDetector
from app.advanced_ml_strategy import AdvancedMLStrategy
from telegram_notify import TelegramNotifier, telegram_notifier
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
        logging.FileHandler('multi_coin_trading.log')
    ]
)
logger = logging.getLogger('multi_coin_trading')

class MultiCoinTradingBot:
    """Bot giao dịch đa đồng tiền với quản lý tài khoản và rủi ro tích hợp"""
    
    def __init__(self, config_file="multi_coin_config.json"):
        """
        Khởi tạo bot giao dịch đa đồng tiền
        
        Args:
            config_file (str): Đường dẫn đến file cấu hình
        """
        # Tải cấu hình
        self.config = self._load_config(config_file)
        
        # Cài đặt chung
        self.general_settings = self.config["general_settings"]
        self.risk_settings = self.config["risk_management"]
        self.performance_settings = self.config["performance_monitoring"]
        self.advanced_settings = self.config["advanced_features"]
        
        # Các cặp giao dịch đã kích hoạt
        self.active_pairs = [pair for pair in self.config["trading_pairs"] if pair["enabled"]]
        self.symbols = [pair["symbol"] for pair in self.active_pairs]
        
        # Trạng thái bot
        self.is_running = False
        self.stop_event = threading.Event()
        self.active_positions = {}  # {symbol: position_info}
        self.latest_prices = {}  # {symbol: price}
        self.symbol_data = {}  # {symbol: {data, models, metrics, etc.}}
        
        # Dữ liệu hiệu suất
        self.performance_metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "max_drawdown": 0.0,
            "current_drawdown": 0.0,
            "peak_balance": self.general_settings["initial_balance"],
            "daily_pnl": {},  # {date: pnl}
            "by_symbol": {}   # {symbol: {...metrics...}}
        }
        
        # Thời gian cho tác vụ định kỳ
        self.last_model_save_time = datetime.now()
        self.last_daily_report_time = datetime.now()
        self.last_health_check_time = datetime.now()
        
        # Khởi tạo API Binance
        self.api = BinanceAPI(
            api_key=os.environ.get("BINANCE_API_KEY"),
            api_secret=os.environ.get("BINANCE_API_SECRET"),
            testnet=self.general_settings["use_testnet"]
        )
        
        # Khởi tạo các thành phần hệ thống
        self.data_processor = DataProcessor(self.api)
        self.market_regime_detector = MarketRegimeDetector()
        self.composite_indicator = CompositeIndicator()
        
        # Đường dẫn lưu mô hình
        self.model_path = "models/multi_coin"
        os.makedirs(self.model_path, exist_ok=True)
        
        # Khởi tạo mô hình và dữ liệu cho mỗi cặp
        self._initialize_symbol_data()
        
        # Gửi thông báo Telegram khi khởi động
        if self.general_settings["telegram_notifications"]:
            telegram_notifier.send_startup_notification()
        
        logger.info(f"Bot giao dịch đa đồng tiền đã được khởi tạo với {len(self.active_pairs)} cặp giao dịch")
    
    def _load_config(self, config_file):
        """Tải cấu hình từ file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {config_file}")
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            raise
    
    def _initialize_symbol_data(self):
        """Khởi tạo dữ liệu và mô hình cho mỗi cặp giao dịch"""
        for pair in self.active_pairs:
            symbol = pair["symbol"]
            timeframes = pair["timeframes"]
            primary_timeframe = timeframes[0]  # Sử dụng timeframe đầu tiên làm chính
            
            # Tạo dữ liệu cặp
            self.symbol_data[symbol] = {
                "config": pair,
                "primary_timeframe": primary_timeframe,
                "timeframes": timeframes,
                "ml_optimizer": AdvancedMLOptimizer(
                    base_models=["random_forest", "gradient_boosting"],
                    use_model_per_regime=self.advanced_settings["regime_based_strategies"],
                    feature_selection=True,
                    use_ensemble=True
                ),
                "regime": "neutral",  # Giá trị mặc định ban đầu
                "latest_signals": {},
                "last_training_time": None,
                "trade_history": [],
                "metrics": {
                    "win_rate": 0,
                    "profit_factor": 0,
                    "average_win": 0,
                    "average_loss": 0,
                    "total_trades": 0
                }
            }
            
            # Tìm mô hình có sẵn cho cặp này
            self._load_or_train_model(symbol)
            
            # Khởi tạo thông tin hiệu suất
            self.performance_metrics["by_symbol"][symbol] = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0
            }
            
            logger.info(f"Đã khởi tạo dữ liệu cho {symbol} với {len(timeframes)} khung thời gian")
    
    def _load_or_train_model(self, symbol):
        """Tải mô hình có sẵn hoặc huấn luyện mô hình mới cho một cặp giao dịch"""
        symbol_model_path = f"{self.model_path}/{symbol}"
        os.makedirs(symbol_model_path, exist_ok=True)
        
        # Tìm file mô hình mới nhất cho cặp này
        model_files = []
        for root, dirs, files in os.walk(symbol_model_path):
            for file in files:
                if file.endswith('.pkl'):
                    model_files.append(os.path.join(root, file))
        
        if model_files:
            # Tìm file mô hình mới nhất
            latest_model = max(model_files, key=os.path.getmtime)
            try:
                logger.info(f"Đang nạp mô hình cho {symbol} từ: {latest_model}")
                self.symbol_data[symbol]["ml_optimizer"].load_models(latest_model)
                self.symbol_data[symbol]["last_training_time"] = datetime.fromtimestamp(os.path.getmtime(latest_model))
                logger.info(f"Đã nạp mô hình thành công cho {symbol}")
                return
            except Exception as e:
                logger.error(f"Lỗi khi nạp mô hình cho {symbol}: {str(e)}")
        
        # Nếu không tìm thấy mô hình hoặc lỗi khi nạp, huấn luyện mô hình mới
        self._train_model_for_symbol(symbol)
    
    def _train_model_for_symbol(self, symbol):
        """Huấn luyện mô hình mới cho một cặp giao dịch"""
        logger.info(f"Huấn luyện mô hình mới cho {symbol}")
        
        primary_timeframe = self.symbol_data[symbol]["primary_timeframe"]
        lookback_days = self.general_settings["training_lookback_days"]
        
        # Lấy dữ liệu lịch sử
        df = self.data_processor.get_historical_data(
            symbol=symbol,
            interval=primary_timeframe,
            lookback_days=lookback_days
        )
        
        if df is None or df.empty:
            logger.error(f"Không thể lấy dữ liệu cho {symbol}")
            return
        
        # Phát hiện chế độ thị trường
        regime = self.market_regime_detector.detect_regime(df)
        self.symbol_data[symbol]["regime"] = regime
        
        # Chuẩn bị dữ liệu huấn luyện
        ml_optimizer = self.symbol_data[symbol]["ml_optimizer"]
        X = ml_optimizer.prepare_features_for_prediction(df)
        y = ml_optimizer.prepare_target_for_training(df, lookahead=1, threshold=0.001)
        
        # Đảm bảo X và y có cùng kích thước
        if len(X) != len(y):
            min_len = min(len(X), len(y))
            X = X.iloc[:min_len]
            y = y[:min_len]
            logger.info(f"Điều chỉnh kích thước dữ liệu huấn luyện cho {symbol}: X = {len(X)}, y = {len(y)}")
        
        # Huấn luyện mô hình
        logger.info(f"Huấn luyện mô hình cho {symbol} với {len(X)} mẫu, chế độ thị trường: {regime}")
        ml_optimizer.train_models(X, y, regime=regime)
        
        # Lưu mô hình
        if self.general_settings["save_ml_models"]:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = ml_optimizer.save_models(f"{self.model_path}/{symbol}/model_{timestamp}.pkl")
            logger.info(f"Đã lưu mô hình cho {symbol} vào {model_filename}")
        
        # Cập nhật thời gian huấn luyện
        self.symbol_data[symbol]["last_training_time"] = datetime.now()
    
    def get_trading_signals(self, symbol):
        """
        Lấy tín hiệu giao dịch cho một cặp tiền
        
        Args:
            symbol (str): Cặp giao dịch
            
        Returns:
            dict: Thông tin tín hiệu giao dịch
        """
        # Lấy dữ liệu mới nhất
        primary_timeframe = self.symbol_data[symbol]["primary_timeframe"]
        df = self.data_processor.get_historical_data(
            symbol=symbol,
            interval=primary_timeframe,
            lookback_days=7  # Dữ liệu gần đây để dự đoán
        )
        
        if df is None or df.empty:
            logger.error(f"Không thể lấy dữ liệu cho {symbol}")
            return None
        
        # Phát hiện chế độ thị trường
        market_regime = self.market_regime_detector.detect_regime(df)
        self.symbol_data[symbol]["regime"] = market_regime
        
        # Tính toán chỉ báo tổng hợp
        composite_score = self.composite_indicator.calculate_composite_score(df)
        
        # Chuẩn bị tính năng và dự đoán
        ml_optimizer = self.symbol_data[symbol]["ml_optimizer"]
        X = ml_optimizer.prepare_features_for_prediction(df)
        X_latest = X.iloc[-1:].copy()  # Lấy dòng mới nhất
        
        # Dự đoán với mô hình ML
        y_pred, probas = ml_optimizer.predict(X_latest, regime=market_regime)
        
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
        
        # Lấy cấu hình cặp giao dịch
        pair_config = self.symbol_data[symbol]["config"]
        entry_threshold = pair_config.get("entry_threshold", 0.65)
        
        # Quyết định cuối cùng
        final_signal = "neutral"
        if ml_signal == composite_signal and ml_signal != "neutral":
            final_signal = ml_signal
        elif ml_signal != "neutral" and confidence > entry_threshold:
            final_signal = ml_signal
        
        # Lấy giá hiện tại
        current_price = self.api.get_symbol_price(symbol)
        self.latest_prices[symbol] = current_price
        
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
            "current_price": current_price,
            "individual_scores": composite_score.get("individual_scores", {})
        }
        
        # Lưu tín hiệu mới nhất
        self.symbol_data[symbol]["latest_signals"] = signal_info
        
        logger.info(f"Tín hiệu: {symbol} - {final_signal} (Confidence: {confidence:.2f}, Regime: {market_regime})")
        
        # Gửi thông báo Telegram cho tín hiệu giao dịch quan trọng
        if self.general_settings["telegram_notifications"] and final_signal != "neutral":
            notification_level = self.general_settings["notification_level"]
            if notification_level in ["all", "trades_and_signals", "signals_only"]:
                telegram_notifier.send_trade_signal(signal_info)
        
        return signal_info
    
    def calculate_position_size(self, symbol, signal):
        """
        Tính toán kích thước vị thế dựa trên quản lý rủi ro
        
        Args:
            symbol (str): Cặp giao dịch
            signal (str): Tín hiệu giao dịch
            
        Returns:
            float: Kích thước vị thế (số lượng)
        """
        # Lấy cấu hình cặp giao dịch
        pair_config = self.symbol_data[symbol]["config"]
        risk_percentage = pair_config["risk_percentage"]
        max_position_size = pair_config["max_position_size"]
        
        # Điều chỉnh rủi ro theo chế độ thị trường
        regime = self.symbol_data[symbol]["regime"]
        if self.risk_settings["auto_adjust_position_size"]:
            if regime == "trending_up" or regime == "trending_down":
                risk_percentage *= self.risk_settings["risk_multiplier_trending"]
            elif regime == "ranging":
                risk_percentage *= self.risk_settings["risk_multiplier_ranging"]
            elif regime == "volatile":
                risk_percentage *= self.risk_settings["risk_multiplier_volatile"]
        
        # Lấy số dư tài khoản
        if self.general_settings["use_testnet"]:
            account_info = self.api.get_account_info()
            if account_info and 'availableBalance' in account_info:
                balance = float(account_info['availableBalance'])
            else:
                balance = self.general_settings["initial_balance"]
        else:
            balance = self.general_settings["initial_balance"]
        
        # Kiểm tra mức thua lỗ trong ngày
        today = datetime.now().strftime("%Y-%m-%d")
        daily_loss = self.performance_metrics["daily_pnl"].get(today, 0)
        daily_loss_limit = balance * (self.risk_settings["daily_loss_limit_percentage"] / 100)
        
        if daily_loss < 0 and abs(daily_loss) >= daily_loss_limit:
            logger.warning(f"Đã đạt giới hạn thua lỗ trong ngày: ${abs(daily_loss):.2f} >= ${daily_loss_limit:.2f}")
            return 0
        
        # Tính toán kích thước vị thế dựa trên rủi ro
        risk_amount = balance * (risk_percentage / 100)
        
        # Lấy giá hiện tại
        current_price = self.latest_prices.get(symbol, self.api.get_symbol_price(symbol))
        if current_price is None:
            logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
            return 0
        
        # Tính số lượng có thể mua
        position_size = risk_amount / current_price
        
        # Giới hạn kích thước vị thế
        position_size = min(position_size, max_position_size)
        
        # Làm tròn số lượng
        position_size = round(position_size, 6)  # 6 chữ số thập phân
        
        logger.info(f"Kích thước vị thế cho {symbol}: {position_size} ({risk_percentage}% rủi ro, giá: {current_price})")
        return position_size
    
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
        max_positions = self.general_settings["max_concurrent_positions"]
        if len(self.active_positions) >= max_positions and symbol not in self.active_positions:
            logger.info(f"Đã đạt số lượng vị thế tối đa ({max_positions}), bỏ qua tín hiệu {signal} cho {symbol}")
            return None
        
        # Tính kích thước vị thế nếu không được cung cấp
        if position_size is None:
            position_size = self.calculate_position_size(symbol, signal)
        
        if position_size <= 0:
            logger.error(f"Kích thước vị thế không hợp lệ: {position_size}")
            return None
        
        # Xác định hướng lệnh
        side = "BUY" if signal == "buy" else "SELL"
        
        # Lệnh thực tế hoặc giả lập
        if not self.general_settings["use_testnet"]:
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
                        "order_id": order['orderId'],
                        "take_profit": self.symbol_data[symbol]["config"]["take_profit"],
                        "stop_loss": self.symbol_data[symbol]["config"]["stop_loss"]
                    }
                    logger.info(f"Đã mở vị thế {side} cho {symbol}: {position_size} @ {entry_price}")
                    
                    # Gửi thông báo Telegram
                    if self.general_settings["telegram_notifications"]:
                        notification_level = self.general_settings["notification_level"]
                        if notification_level in ["all", "trades_and_signals", "trades_only"]:
                            telegram_notifier.send_trade_execution(order)
                    
                    return order
                else:
                    logger.error(f"Lỗi khi tạo lệnh: {order}")
                    return None
            except Exception as e:
                logger.error(f"Lỗi khi thực hiện lệnh: {str(e)}")
                return None
        else:
            # Giả lập lệnh
            current_price = self.latest_prices.get(symbol, self.api.get_symbol_price(symbol))
            
            # Lấy cấu hình cặp giao dịch
            pair_config = self.symbol_data[symbol]["config"]
            take_profit = pair_config["take_profit"]
            stop_loss = pair_config["stop_loss"]
            
            self.active_positions[symbol] = {
                "symbol": symbol,
                "side": side,
                "quantity": position_size,
                "entry_price": current_price,
                "entry_time": datetime.now(),
                "order_id": f"sim_{int(time.time())}",
                "take_profit": take_profit,
                "stop_loss": stop_loss
            }
            logger.info(f"[GIẢLẬP] Đã mở vị thế {side} cho {symbol}: {position_size} @ {current_price}")
            
            trade_data = {
                "symbol": symbol,
                "side": side,
                "quantity": position_size,
                "price": current_price,
                "orderId": self.active_positions[symbol]["order_id"],
                "status": "FILLED",
                "simulated": True
            }
            
            # Gửi thông báo Telegram
            if self.general_settings["telegram_notifications"]:
                notification_level = self.general_settings["notification_level"]
                if notification_level in ["all", "trades_and_signals", "trades_only"]:
                    telegram_notifier.send_trade_execution(trade_data)
            
            return trade_data
    
    def check_and_update_positions(self):
        """
        Kiểm tra và cập nhật trạng thái các vị thế hiện tại
        
        Returns:
            list: Danh sách các vị thế đã đóng
        """
        closed_positions = []
        
        for symbol in list(self.active_positions.keys()):
            position = self.active_positions[symbol]
            current_price = self.latest_prices.get(symbol, self.api.get_symbol_price(symbol))
            
            if current_price is None:
                logger.warning(f"Không thể lấy giá hiện tại cho {symbol}, bỏ qua cập nhật vị thế")
                continue
            
            # Tính toán P&L
            entry_price = position["entry_price"]
            quantity = position["quantity"]
            side = position["side"]
            take_profit = position["take_profit"]
            stop_loss = position["stop_loss"]
            
            if side == "BUY":
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
                pnl = (current_price - entry_price) * quantity
            else:  # SELL
                price_change_pct = ((entry_price - current_price) / entry_price) * 100
                pnl = (entry_price - current_price) * quantity
            
            # Kiểm tra điều kiện đóng vị thế
            close_position = False
            exit_reason = None
            
            # Kiểm tra Take Profit
            if price_change_pct >= take_profit:
                close_position = True
                exit_reason = "take_profit"
            
            # Kiểm tra Stop Loss
            elif price_change_pct <= -stop_loss:
                close_position = True
                exit_reason = "stop_loss"
            
            # Đóng vị thế nếu cần
            if close_position:
                logger.info(f"Đóng vị thế {symbol} {side} do {exit_reason}: {price_change_pct:.2f}% ({pnl:.2f} USD)")
                self._close_position(symbol, current_price, exit_reason)
                closed_positions.append(symbol)
        
        return closed_positions
    
    def _close_position(self, symbol, exit_price=None, exit_reason=None):
        """
        Đóng vị thế
        
        Args:
            symbol (str): Cặp giao dịch
            exit_price (float): Giá thoát lệnh, nếu None thì lấy giá hiện tại
            exit_reason (str): Lý do thoát lệnh
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if symbol not in self.active_positions:
            logger.warning(f"Không có vị thế nào để đóng cho {symbol}")
            return False
        
        position = self.active_positions[symbol]
        close_side = "SELL" if position["side"] == "BUY" else "BUY"
        
        # Lấy giá thoát nếu không được cung cấp
        if exit_price is None:
            exit_price = self.latest_prices.get(symbol, self.api.get_symbol_price(symbol))
        
        # Tính toán P&L
        if position["side"] == "BUY":
            pnl = (exit_price - position["entry_price"]) * position["quantity"]
        else:  # SELL
            pnl = (position["entry_price"] - exit_price) * position["quantity"]
        
        # Lệnh thực tế hoặc giả lập
        if not self.general_settings["use_testnet"]:
            try:
                order = self.api.create_order(
                    symbol=symbol,
                    side=close_side,
                    order_type="MARKET",
                    quantity=position["quantity"]
                )
                
                if order and 'orderId' in order:
                    logger.info(f"Đã đóng vị thế {position['side']} cho {symbol}: P&L = ${pnl:.2f}")
                    # Lưu lịch sử giao dịch
                    self._save_trade_history(position, exit_price, pnl, exit_reason)
                    # Xóa vị thế khỏi danh sách vị thế hoạt động
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
            logger.info(f"[GIẢLẬP] Đã đóng vị thế {position['side']} cho {symbol}: P&L = ${pnl:.2f}")
            # Lưu lịch sử giao dịch
            self._save_trade_history(position, exit_price, pnl, exit_reason)
            # Xóa vị thế khỏi danh sách vị thế hoạt động
            del self.active_positions[symbol]
            return True
    
    def _save_trade_history(self, position, exit_price, pnl, exit_reason=None):
        """
        Lưu lịch sử giao dịch và cập nhật thống kê hiệu suất
        
        Args:
            position (dict): Thông tin vị thế
            exit_price (float): Giá thoát
            pnl (float): Lãi/lỗ
            exit_reason (str): Lý do thoát
        """
        symbol = position["symbol"]
        trade_history = []
        history_file = f"trade_history_{symbol}.json"
        
        # Tạo bản ghi giao dịch
        trade_record = {
            "symbol": symbol,
            "side": position["side"],
            "quantity": position["quantity"],
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_percentage": (pnl / (position["entry_price"] * position["quantity"])) * 100,
            "entry_time": position["entry_time"].isoformat(),
            "exit_time": datetime.now().isoformat(),
            "order_id": position["order_id"],
            "exit_reason": exit_reason,
            "market_regime": self.symbol_data[symbol]["regime"]
        }
        
        # Đọc lịch sử hiện có
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    trade_history = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc lịch sử giao dịch: {str(e)}")
        
        # Thêm giao dịch mới
        trade_history.append(trade_record)
        
        # Lưu lịch sử
        try:
            with open(history_file, 'w') as f:
                json.dump(trade_history, f, indent=4)
            logger.info(f"Đã lưu lịch sử giao dịch: {symbol} {position['side']} - PnL: {pnl}")
            
            # Cập nhật thống kê hiệu suất
            self._update_performance_metrics(trade_record)
            
            # Lưu vào lịch sử giao dịch của cặp
            self.symbol_data[symbol]["trade_history"].append(trade_record)
            
            # Gửi thông báo Telegram
            if self.general_settings["telegram_notifications"]:
                notification_level = self.general_settings["notification_level"]
                if notification_level in ["all", "trades_and_signals", "trades_only"]:
                    telegram_notifier.send_position_closed(trade_record)
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử giao dịch: {str(e)}")
    
    def _update_performance_metrics(self, trade_record):
        """
        Cập nhật các chỉ số hiệu suất từ giao dịch đã đóng
        
        Args:
            trade_record (dict): Bản ghi giao dịch
        """
        symbol = trade_record["symbol"]
        pnl = trade_record["pnl"]
        
        # Cập nhật thống kê tổng thể
        self.performance_metrics["total_trades"] += 1
        
        if pnl > 0:
            self.performance_metrics["winning_trades"] += 1
            self.performance_metrics["total_profit"] += pnl
        else:
            self.performance_metrics["losing_trades"] += 1
            self.performance_metrics["total_loss"] += abs(pnl)
        
        # Cập nhật thống kê theo cặp
        symbol_metrics = self.performance_metrics["by_symbol"][symbol]
        symbol_metrics["total_trades"] += 1
        
        if pnl > 0:
            symbol_metrics["winning_trades"] += 1
            symbol_metrics["total_profit"] += pnl
        else:
            symbol_metrics["losing_trades"] += 1
            symbol_metrics["total_loss"] += abs(pnl)
        
        # Tính tỷ lệ thắng
        if symbol_metrics["total_trades"] > 0:
            symbol_metrics["win_rate"] = (symbol_metrics["winning_trades"] / symbol_metrics["total_trades"]) * 100
        
        # Tính hệ số lợi nhuận
        if symbol_metrics["total_loss"] > 0:
            symbol_metrics["profit_factor"] = symbol_metrics["total_profit"] / symbol_metrics["total_loss"]
        else:
            symbol_metrics["profit_factor"] = symbol_metrics["total_profit"] if symbol_metrics["total_profit"] > 0 else 0
        
        # Cập nhật thống kê theo ngày
        exit_date = datetime.fromisoformat(trade_record["exit_time"]).strftime("%Y-%m-%d")
        if exit_date not in self.performance_metrics["daily_pnl"]:
            self.performance_metrics["daily_pnl"][exit_date] = 0
        
        self.performance_metrics["daily_pnl"][exit_date] += pnl
        
        # Tính toán drawdown
        total_pnl = self.performance_metrics["total_profit"] - self.performance_metrics["total_loss"]
        current_balance = self.general_settings["initial_balance"] + total_pnl
        
        if current_balance > self.performance_metrics["peak_balance"]:
            self.performance_metrics["peak_balance"] = current_balance
            self.performance_metrics["current_drawdown"] = 0
        else:
            current_drawdown_pct = ((self.performance_metrics["peak_balance"] - current_balance) / 
                                   self.performance_metrics["peak_balance"]) * 100
            self.performance_metrics["current_drawdown"] = current_drawdown_pct
            
            if current_drawdown_pct > self.performance_metrics["max_drawdown"]:
                self.performance_metrics["max_drawdown"] = current_drawdown_pct
    
    def _check_periodic_tasks(self):
        """Kiểm tra và thực hiện các tác vụ định kỳ"""
        now = datetime.now()
        
        # Huấn luyện lại mô hình nếu cần
        if self.general_settings["continuous_learning"]:
            ml_save_interval = timedelta(hours=self.general_settings["ml_model_save_interval_hours"])
            
            for symbol in self.symbols:
                last_train_time = self.symbol_data[symbol]["last_training_time"]
                if last_train_time is None or (now - last_train_time) > ml_save_interval:
                    logger.info(f"Huấn luyện lại mô hình cho {symbol} theo định kỳ")
                    self._train_model_for_symbol(symbol)
        
        # Kiểm tra thời gian gửi báo cáo hàng ngày
        report_time = self.performance_settings["daily_report_time"]
        report_hour, report_minute = map(int, report_time.split(':'))
        
        if (now.hour == report_hour and now.minute == report_minute and 
            (self.last_daily_report_time.date() != now.date() or 
             (now - self.last_daily_report_time).total_seconds() > 3600)):
            self._send_daily_report()
            self.last_daily_report_time = now
        
        # Kiểm tra sức khỏe hệ thống
        health_interval = timedelta(minutes=self.performance_settings["health_check_interval_minutes"])
        if (now - self.last_health_check_time) > health_interval:
            self._perform_health_check()
            self.last_health_check_time = now
    
    def _send_daily_report(self):
        """
        Tạo và gửi báo cáo hiệu suất hàng ngày
        """
        if not self.general_settings["telegram_notifications"]:
            return
        
        # Tính toán hiệu suất hàng ngày
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        daily_pnl = self.performance_metrics["daily_pnl"].get(today, 0)
        
        # Tính toán tổng số dư và hiệu suất
        total_pnl = self.performance_metrics["total_profit"] - self.performance_metrics["total_loss"]
        current_balance = self.general_settings["initial_balance"] + total_pnl
        
        # Tính toán hiệu suất theo ngày
        daily_pnl_pct = (daily_pnl / current_balance) * 100 if current_balance > 0 else 0
        
        # Lấy thông tin giao dịch trong ngày
        today_trades = []
        for symbol in self.symbols:
            for trade in self.symbol_data[symbol]["trade_history"]:
                exit_time = datetime.fromisoformat(trade["exit_time"])
                if exit_time.strftime("%Y-%m-%d") == today:
                    today_trades.append(trade)
        
        # Tạo báo cáo hiệu suất theo cặp
        symbol_performance = {}
        for symbol in self.symbols:
            symbol_trades = [t for t in today_trades if t["symbol"] == symbol]
            symbol_pnl = sum(t["pnl"] for t in symbol_trades)
            
            if symbol_trades:
                symbol_performance[symbol] = {
                    "trades": len(symbol_trades),
                    "pnl": symbol_pnl
                }
        
        # Dữ liệu báo cáo
        report_data = {
            "balance": current_balance,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "trades": today_trades,
            "symbol_performance": symbol_performance
        }
        
        # Gửi báo cáo qua Telegram
        telegram_notifier.send_daily_report(report_data)
        logger.info(f"Đã gửi báo cáo hiệu suất hàng ngày qua Telegram")
    
    def _perform_health_check(self):
        """
        Kiểm tra sức khỏe hệ thống
        """
        # Kiểm tra kết nối API
        try:
            api_status = self.api.test_connection()
            if not api_status:
                logger.error("Lỗi kết nối Binance API")
                if self.general_settings["telegram_notifications"]:
                    telegram_notifier.send_error_alert("Lỗi kết nối Binance API", "API Connection")
        except Exception as e:
            logger.error(f"Lỗi kiểm tra kết nối API: {str(e)}")
            if self.general_settings["telegram_notifications"]:
                telegram_notifier.send_error_alert(f"Lỗi kiểm tra kết nối API: {str(e)}", "API Connection")
        
        # Kiểm tra drawdown
        if self.performance_metrics["current_drawdown"] > self.risk_settings["max_drawdown_percentage"]:
            message = (f"Cảnh báo: Drawdown hiện tại ({self.performance_metrics['current_drawdown']:.2f}%) "
                      f"đã vượt quá giới hạn ({self.risk_settings['max_drawdown_percentage']}%)")
            logger.warning(message)
            if self.general_settings["telegram_notifications"]:
                telegram_notifier.send_error_alert(message, "Drawdown Alert")
        
        # Kiểm tra API response time
        start_time = time.time()
        try:
            self.api.get_server_time()
            response_time = time.time() - start_time
            if response_time > 2.0:  # Quá 2 giây được coi là chậm
                logger.warning(f"API response time chậm: {response_time:.2f}s")
                if self.general_settings["telegram_notifications"]:
                    telegram_notifier.send_error_alert(f"API response time chậm: {response_time:.2f}s", "Performance Alert")
        except Exception as e:
            logger.error(f"Lỗi kiểm tra API response time: {str(e)}")
        
        logger.info("Đã hoàn thành kiểm tra sức khỏe hệ thống")
    
    def _close_all_positions(self):
        """Đóng tất cả các vị thế đang mở"""
        for symbol in list(self.active_positions.keys()):
            self._close_position(symbol)
        
        logger.info("Đã đóng tất cả các vị thế đang mở")
    
    def _print_status(self):
        """In trạng thái hiện tại của bot"""
        logger.info("-" * 50)
        logger.info(f"Trạng thái bot ({datetime.now().isoformat()})")
        logger.info(f"Số vị thế đang mở: {len(self.active_positions)}")
        
        for symbol, position in self.active_positions.items():
            current_price = self.latest_prices.get(symbol, self.api.get_symbol_price(symbol))
            
            if current_price is None:
                logger.warning(f"Không thể lấy giá hiện tại cho {symbol}")
                continue
            
            # Tính toán P&L
            if position["side"] == "BUY":
                pnl = (current_price - position["entry_price"]) * position["quantity"]
                pnl_pct = ((current_price - position["entry_price"]) / position["entry_price"]) * 100
            else:  # SELL
                pnl = (position["entry_price"] - current_price) * position["quantity"]
                pnl_pct = ((position["entry_price"] - current_price) / position["entry_price"]) * 100
            
            logger.info(f"{symbol}: {position['side']} {position['quantity']} @ {position['entry_price']} "
                       f"(Hiện tại: {current_price}, P&L: ${pnl:.2f}, {pnl_pct:.2f}%)")
        
        # Hiệu suất tổng thể
        total_pnl = self.performance_metrics["total_profit"] - self.performance_metrics["total_loss"]
        current_balance = self.general_settings["initial_balance"] + total_pnl
        
        logger.info(f"Số dư: ${current_balance:.2f} (Ban đầu: ${self.general_settings['initial_balance']:.2f})")
        logger.info(f"Tổng P&L: ${total_pnl:.2f}")
        logger.info(f"Số giao dịch: {self.performance_metrics['total_trades']} "
                   f"(Thắng: {self.performance_metrics['winning_trades']}, "
                   f"Thua: {self.performance_metrics['losing_trades']})")
        
        if self.performance_metrics["total_trades"] > 0:
            win_rate = (self.performance_metrics["winning_trades"] / self.performance_metrics["total_trades"]) * 100
            logger.info(f"Tỷ lệ thắng: {win_rate:.2f}%")
        
        if self.performance_metrics["total_loss"] > 0:
            profit_factor = self.performance_metrics["total_profit"] / self.performance_metrics["total_loss"]
            logger.info(f"Hệ số lợi nhuận: {profit_factor:.2f}")
        
        logger.info(f"Max Drawdown: {self.performance_metrics['max_drawdown']:.2f}%")
        logger.info("-" * 50)
    
    def run(self, check_interval=None):
        """
        Chạy bot giao dịch liên tục
        
        Args:
            check_interval (int): Thời gian giữa các lần kiểm tra (giây)
        """
        if check_interval is None:
            check_interval = self.general_settings["check_interval_seconds"]
        
        logger.info(f"Bắt đầu chạy bot giao dịch đa đồng tiền với {len(self.active_pairs)} cặp")
        
        # Thiết lập bộ xử lý signal để kết thúc gracefully
        def signal_handler(sig, frame):
            logger.info("Nhận tín hiệu kết thúc, đang đóng bot an toàn...")
            self.stop_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.is_running = True
        try:
            while not self.stop_event.is_set():
                # Kiểm tra và thực hiện các tác vụ định kỳ
                self._check_periodic_tasks()
                
                # Kiểm tra và cập nhật các vị thế hiện tại
                self.check_and_update_positions()
                
                # Kiểm tra tín hiệu giao dịch cho mỗi cặp
                for pair in self.active_pairs:
                    symbol = pair["symbol"]
                    
                    # Cập nhật giá mới nhất
                    current_price = self.api.get_symbol_price(symbol)
                    if current_price is not None:
                        self.latest_prices[symbol] = current_price
                    
                    # Lấy tín hiệu giao dịch
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
                
                # Sử dụng event để có thể kết thúc sớm khi cần
                self.stop_event.wait(timeout=check_interval)
        except Exception as e:
            logger.error(f"Lỗi không mong muốn khi chạy bot: {str(e)}")
            if self.general_settings["telegram_notifications"]:
                telegram_notifier.send_error_alert(f"Bot dừng do lỗi: {str(e)}", "Critical Error")
        finally:
            self.is_running = False
            # Đóng tất cả các vị thế khi kết thúc
            self._close_all_positions()
            logger.info("Bot đã dừng, tất cả các vị thế đã được đóng")
            if self.general_settings["telegram_notifications"]:
                telegram_notifier.send_message("Bot giao dịch đã dừng hoạt động an toàn.")

def main():
    """Hàm chính để chạy bot giao dịch đa đồng tiền"""
    parser = argparse.ArgumentParser(description='Bot giao dịch đa đồng tiền với học máy')
    parser.add_argument('--config', type=str, default='multi_coin_config.json',
                        help='Đường dẫn đến file cấu hình')
    parser.add_argument('--interval', type=int, default=None,
                        help='Thời gian giữa các lần kiểm tra (giây)')
    parser.add_argument('--live', action='store_true',
                        help='Chạy trong chế độ thực tế (mặc định là giả lập)')
    
    args = parser.parse_args()
    
    # Tải cấu hình
    config_file = args.config
    
    try:
        # Khởi tạo bot
        bot = MultiCoinTradingBot(config_file=config_file)
        
        # Cập nhật chế độ thực tế nếu được chỉ định
        if args.live:
            bot.general_settings["use_testnet"] = False
            logger.warning("Chạy bot trong chế độ THỰC TẾ! Sẽ thực hiện giao dịch thực.")
        
        # Chạy bot
        bot.run(check_interval=args.interval)
    except KeyboardInterrupt:
        logger.info("Bot đã dừng bởi người dùng.")
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {str(e)}")

if __name__ == "__main__":
    main()