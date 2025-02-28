#!/usr/bin/env python3
"""
Script giả lập giao dịch đa đồng tiền với báo cáo và điều khiển qua web
"""
import os
import sys
import time
import json
import random
import logging
import threading
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("multi_coin_simulation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("multi_coin_simulation")

# Thông tin cấu hình
TRADING_PAIRS = [
    {"symbol": "BTCUSDT", "enabled": True, "leverage": 3, "take_profit_pct": 2.5, "stop_loss_pct": 1.5},
    {"symbol": "ETHUSDT", "enabled": True, "leverage": 3, "take_profit_pct": 3.0, "stop_loss_pct": 2.0},
    {"symbol": "BNBUSDT", "enabled": False, "leverage": 2, "take_profit_pct": 2.5, "stop_loss_pct": 1.5},
    {"symbol": "SOLUSDT", "enabled": False, "leverage": 2, "take_profit_pct": 3.5, "stop_loss_pct": 2.5},
]

class MultiCoinSimulation:
    def __init__(self):
        # Số dư và thông tin tài khoản
        self.balance = 10000.0
        self.initial_balance = 10000.0
        self.positions = []
        self.trade_history = []
        
        # Giá thị trường
        self.current_prices = {
            "BTCUSDT": 83000 + random.uniform(-2000, 2000),
            "ETHUSDT": 2300 + random.uniform(-100, 100),
            "BNBUSDT": 380 + random.uniform(-20, 20),
            "SOLUSDT": 140 + random.uniform(-10, 10),
            "DOGEUSDT": 0.12 + random.uniform(-0.01, 0.01)
        }
        
        # Tốc độ giả lập (giây)
        self.update_interval = 1
        self.trade_interval = 10
        self.report_interval = 60
        
        # Các metric hiệu suất
        self.performance_metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "average_profit": 0.0,
            "average_loss": 0.0
        }
        
        # Cờ điều khiển
        self.running = True
        self.paused = False
        self.last_price_update = datetime.now()
        self.last_signal_check = datetime.now()
        self.last_report = datetime.now()
        self.last_training = datetime.now() - timedelta(hours=3)  # Huấn luyện trong giờ đầu tiên
        
        # Tải trạng thái nếu có
        self.load_state()
        logger.info(f"Khởi tạo hệ thống với số dư: ${self.balance:.2f}")
        
        # Khởi tạo bảng giá trị composite indicator
        self.composite_scores = {}
        for symbol in self.current_prices:
            self.composite_scores[symbol] = {
                "score": random.uniform(-1.0, 1.0),
                "rsi": random.uniform(30, 70),
                "macd": random.choice([-1, 0, 1]),
                "trend": random.choice(["up", "down", "sideways"]),
                "strength": random.uniform(0, 100),
                "signals": []
            }
    
    def load_state(self):
        """Tải trạng thái giao dịch từ file (nếu có)"""
        try:
            if os.path.exists("trading_state.json"):
                with open("trading_state.json", "r") as f:
                    state = json.load(f)
                    
                    # Chỉ cập nhật các trường liên quan đến hiệu suất và lịch sử
                    self.balance = state.get("current_balance", self.balance)
                    self.trade_history = state.get("closed_positions", [])
                    self.performance_metrics = state.get("performance_metrics", self.performance_metrics)
                    
                    logger.info("Đã tải trạng thái giao dịch từ file")
        except Exception as e:
            logger.error(f"Lỗi khi tải trạng thái: {e}")
    
    def save_state(self):
        """Lưu trạng thái giao dịch"""
        try:
            state = {
                "initial_balance": self.initial_balance,
                "current_balance": self.balance,
                "risk_percentage": 1.0,
                "timeframes": ["1h", "4h", "1d"],
                "use_multi_timeframe": True,
                "use_composite_indicators": True,
                "use_liquidity_analysis": True,
                "use_market_regimes": True,
                "open_positions": self.positions,
                "closed_positions": self.trade_history,
                "performance_metrics": self.performance_metrics,
                "timestamp": datetime.now().isoformat()
            }
            
            with open("trading_state.json", "w") as f:
                json.dump(state, f, indent=2)
                
            logger.info("Đã lưu trạng thái giao dịch")
        except Exception as e:
            logger.error(f"Lỗi khi lưu trạng thái: {e}")
    
    def update_prices(self):
        """Cập nhật giá thị trường theo thời gian thực"""
        # Tạo biến động giá ngẫu nhiên với xu hướng nhẹ
        for symbol in self.current_prices:
            # Tính toán biến động giá
            volatility = 0.1  # 0.1% biến động cơ bản
            
            # Thêm yếu tố xu hướng (30% cơ hội có xu hướng)
            if random.random() < 0.3:
                trend = random.choice([-1, 1]) * random.uniform(0.2, 0.5)  # Xu hướng 0.2-0.5%
            else:
                trend = 0
                
            # Tạo biến động giá ngẫu nhiên
            price_change_pct = (random.uniform(-volatility, volatility) + trend) / 100
            self.current_prices[symbol] *= (1 + price_change_pct)
            
            # Cập nhật composite indicator score
            score_change = random.uniform(-0.05, 0.05)
            self.composite_scores[symbol]["score"] += score_change
            # Giới hạn trong khoảng [-1, 1]
            self.composite_scores[symbol]["score"] = max(-1, min(1, self.composite_scores[symbol]["score"]))
            
            # Cập nhật RSI
            rsi_change = random.uniform(-2, 2)
            self.composite_scores[symbol]["rsi"] += rsi_change
            # Giới hạn trong khoảng [0, 100]
            self.composite_scores[symbol]["rsi"] = max(0, min(100, self.composite_scores[symbol]["rsi"]))
            
            # Cập nhật MACD nếu cần
            if random.random() < 0.1:  # 10% cơ hội thay đổi
                self.composite_scores[symbol]["macd"] = random.choice([-1, 0, 1])
            
            # Cập nhật xu hướng nếu cần
            if random.random() < 0.05:  # 5% cơ hội thay đổi xu hướng
                self.composite_scores[symbol]["trend"] = random.choice(["up", "down", "sideways"])
            
            # Cập nhật sức mạnh tín hiệu
            strength_change = random.uniform(-2, 2)
            self.composite_scores[symbol]["strength"] += strength_change
            # Giới hạn trong khoảng [0, 100]
            self.composite_scores[symbol]["strength"] = max(0, min(100, self.composite_scores[symbol]["strength"]))
        
        # Cập nhật giá các vị thế và tính P&L
        for position in self.positions:
            symbol = position["symbol"]
            current_price = self.current_prices[symbol]
            position["current_price"] = current_price
            
            entry_price = position["entry_price"]
            quantity = position["quantity"]
            leverage = position.get("leverage", 1)
            
            if position["type"] == "BUY":
                profit = (current_price - entry_price) * quantity * leverage
                profit_pct = (current_price / entry_price - 1) * 100 * leverage
            else:  # SELL
                profit = (entry_price - current_price) * quantity * leverage
                profit_pct = (entry_price / current_price - 1) * 100 * leverage
            
            position["pnl"] = profit
            position["pnl_pct"] = profit_pct
            
            # Cập nhật trailing stop nếu được kích hoạt
            if position.get("trailing_stop_activated", False):
                trailing_stop_price = position.get("trailing_stop_price", 0)
                
                if position["type"] == "BUY" and current_price > trailing_stop_price:
                    # Cập nhật trailing stop cho lệnh mua
                    callback_pct = position.get("trailing_stop_callback_pct", 0.5) / 100
                    new_stop_price = current_price * (1 - callback_pct)
                    
                    if new_stop_price > trailing_stop_price:
                        position["trailing_stop_price"] = new_stop_price
                        logger.info(f"Cập nhật trailing stop cho {symbol} BUY: ${new_stop_price:.2f}")
                        
                elif position["type"] == "SELL" and current_price < trailing_stop_price:
                    # Cập nhật trailing stop cho lệnh bán
                    callback_pct = position.get("trailing_stop_callback_pct", 0.5) / 100
                    new_stop_price = current_price * (1 + callback_pct)
                    
                    if new_stop_price < trailing_stop_price:
                        position["trailing_stop_price"] = new_stop_price
                        logger.info(f"Cập nhật trailing stop cho {symbol} SELL: ${new_stop_price:.2f}")
    
    def check_signals(self):
        """Kiểm tra tín hiệu giao dịch cho tất cả cặp tiền được kích hoạt"""
        signals = {}
        
        for pair in TRADING_PAIRS:
            if pair["enabled"]:
                symbol = pair["symbol"]
                signals[symbol] = self.check_signal_for_symbol(symbol)
                
                # Thêm tín hiệu vào danh sách theo dõi
                if signals[symbol]:
                    signal_type = signals[symbol]["type"]
                    confidence = signals[symbol]["confidence"]
                    
                    # Lưu 5 tín hiệu gần nhất
                    self.composite_scores[symbol]["signals"].append({
                        "time": datetime.now().isoformat(),
                        "type": signal_type,
                        "confidence": confidence,
                        "price": self.current_prices[symbol]
                    })
                    
                    # Giữ tối đa 5 tín hiệu gần nhất
                    if len(self.composite_scores[symbol]["signals"]) > 5:
                        self.composite_scores[symbol]["signals"] = self.composite_scores[symbol]["signals"][-5:]
        
        # Kiểm tra và thực hiện giao dịch nếu có tín hiệu
        for symbol, signal in signals.items():
            if signal:
                # Kiểm tra xem đã có vị thế cho symbol này chưa
                if not self.has_position(symbol):
                    pair_config = next((p for p in TRADING_PAIRS if p["symbol"] == symbol), None)
                    if pair_config:
                        self.execute_trade(symbol, signal["type"], pair_config)
    
    def check_signal_for_symbol(self, symbol):
        """Kiểm tra tín hiệu cho một cặp tiền cụ thể"""
        score = self.composite_scores[symbol]["score"]
        rsi = self.composite_scores[symbol]["rsi"]
        macd = self.composite_scores[symbol]["macd"]
        trend = self.composite_scores[symbol]["trend"]
        strength = self.composite_scores[symbol]["strength"]
        
        # Tỷ lệ xuất hiện tín hiệu thấp (5-10%)
        if random.random() < 0.05:
            # Xác định loại tín hiệu dựa trên các chỉ báo
            if score > 0.7 or (rsi < 30 and macd > 0) or (trend == "up" and strength > 70):
                signal_type = "BUY"
                confidence = random.randint(65, 95)
            elif score < -0.7 or (rsi > 70 and macd < 0) or (trend == "down" and strength > 70):
                signal_type = "SELL"
                confidence = random.randint(65, 95)
            else:
                # Tín hiệu ngẫu nhiên nếu không có điều kiện cụ thể
                signal_type = random.choice(["BUY", "SELL"])
                confidence = random.randint(60, 75)  # Độ tin cậy thấp hơn
            
            price = self.current_prices[symbol]
            logger.info(f"Tín hiệu: {signal_type} {symbol} @ ${price:.2f} (độ tin cậy: {confidence}%)")
            
            return {
                "type": signal_type,
                "price": price,
                "confidence": confidence,
                "time": datetime.now().isoformat()
            }
        
        return None
    
    def has_position(self, symbol):
        """Kiểm tra xem đã có vị thế cho symbol chưa"""
        return any(p["symbol"] == symbol for p in self.positions)
    
    def execute_trade(self, symbol, signal_type, config):
        """Thực hiện giao dịch"""
        price = self.current_prices[symbol]
        leverage = config.get("leverage", 1)
        take_profit_pct = config.get("take_profit_pct", 3.0)
        stop_loss_pct = config.get("stop_loss_pct", 1.5)
        trailing_stop_enabled = config.get("trailing_stop_enabled", True)
        trailing_stop_activation_pct = config.get("trailing_stop_activation_pct", 1.0)
        trailing_stop_callback_pct = config.get("trailing_stop_callback_pct", 0.5)
        
        # Tính kích thước vị thế (1% tài khoản)
        risk_pct = 1.0
        position_value = self.balance * (risk_pct / 100)
        quantity = position_value / price
        
        # Tạo ID giao dịch
        trade_id = f"{symbol}_{len(self.trade_history) + 1}"
        
        # Tính toán take profit và stop loss
        if signal_type == "BUY":
            take_profit_price = price * (1 + take_profit_pct / 100)
            stop_loss_price = price * (1 - stop_loss_pct / 100)
            trailing_stop_activation_price = price * (1 + trailing_stop_activation_pct / 100)
            trailing_stop_price = stop_loss_price
        else:  # SELL
            take_profit_price = price * (1 - take_profit_pct / 100)
            stop_loss_price = price * (1 + stop_loss_pct / 100)
            trailing_stop_activation_price = price * (1 - trailing_stop_activation_pct / 100)
            trailing_stop_price = stop_loss_price
        
        # Tạo vị thế mới
        position = {
            "id": trade_id,
            "symbol": symbol,
            "type": signal_type,
            "entry_price": price,
            "current_price": price,
            "quantity": quantity,
            "leverage": leverage,
            "entry_time": datetime.now().isoformat(),
            "take_profit_price": take_profit_price,
            "stop_loss_price": stop_loss_price,
            "trailing_stop_enabled": trailing_stop_enabled,
            "trailing_stop_activated": False,
            "trailing_stop_activation_price": trailing_stop_activation_price,
            "trailing_stop_price": trailing_stop_price,
            "trailing_stop_callback_pct": trailing_stop_callback_pct,
            "pnl": 0.0,
            "pnl_pct": 0.0
        }
        
        self.positions.append(position)
        logger.info(f"Đã mở vị thế {signal_type} cho {symbol} @ ${price:.2f}, số lượng: {quantity:.6f}, đòn bẩy: {leverage}x")
        logger.info(f"  Take profit: ${take_profit_price:.2f}, Stop loss: ${stop_loss_price:.2f}")
        
        return position
    
    def check_positions(self):
        """Kiểm tra các vị thế và tự động đóng vị thế khi đạt điều kiện"""
        positions_to_close = []
        
        for position in self.positions:
            symbol = position["symbol"]
            current_price = position["current_price"]
            signal_type = position["type"]
            
            # Kiểm tra điều kiện đóng vị thế
            reason = None
            
            if signal_type == "BUY":
                # Kiểm tra take profit
                if current_price >= position["take_profit_price"]:
                    reason = "Take Profit"
                
                # Kiểm tra stop loss hoặc trailing stop
                elif position.get("trailing_stop_activated", False):
                    if current_price <= position["trailing_stop_price"]:
                        reason = "Trailing Stop"
                elif current_price <= position["stop_loss_price"]:
                    reason = "Stop Loss"
                
                # Kiểm tra kích hoạt trailing stop
                elif position.get("trailing_stop_enabled", False) and not position.get("trailing_stop_activated", False):
                    if current_price >= position["trailing_stop_activation_price"]:
                        position["trailing_stop_activated"] = True
                        logger.info(f"Đã kích hoạt trailing stop cho {symbol} BUY @ ${current_price:.2f}")
            else:  # SELL
                # Kiểm tra take profit
                if current_price <= position["take_profit_price"]:
                    reason = "Take Profit"
                
                # Kiểm tra stop loss hoặc trailing stop
                elif position.get("trailing_stop_activated", False):
                    if current_price >= position["trailing_stop_price"]:
                        reason = "Trailing Stop"
                elif current_price >= position["stop_loss_price"]:
                    reason = "Stop Loss"
                
                # Kiểm tra kích hoạt trailing stop
                elif position.get("trailing_stop_enabled", False) and not position.get("trailing_stop_activated", False):
                    if current_price <= position["trailing_stop_activation_price"]:
                        position["trailing_stop_activated"] = True
                        logger.info(f"Đã kích hoạt trailing stop cho {symbol} SELL @ ${current_price:.2f}")
            
            # Thêm vào danh sách đóng vị thế nếu có lý do
            if reason:
                position["exit_reason"] = reason
                positions_to_close.append(position)
        
        # Đóng các vị thế
        for position in positions_to_close:
            self.close_position(position)
    
    def close_position(self, position):
        """Đóng vị thế"""
        # Thông tin vị thế
        symbol = position["symbol"]
        signal_type = position["type"]
        entry_price = position["entry_price"]
        current_price = position["current_price"]
        quantity = position["quantity"]
        leverage = position.get("leverage", 1)
        pnl = position["pnl"]
        pnl_pct = position["pnl_pct"]
        reason = position.get("exit_reason", "Manual")
        
        # Cập nhật số dư
        self.balance += pnl
        
        # Thêm vào lịch sử giao dịch
        trade_record = position.copy()
        trade_record["exit_time"] = datetime.now().isoformat()
        trade_record["exit_price"] = current_price
        
        self.trade_history.append(trade_record)
        
        # Xóa khỏi danh sách vị thế
        self.positions.remove(position)
        
        # Cập nhật các chỉ số hiệu suất
        self.performance_metrics["total_trades"] += 1
        
        if pnl > 0:
            self.performance_metrics["winning_trades"] += 1
            self.performance_metrics["total_profit"] += pnl
        else:
            self.performance_metrics["losing_trades"] += 1
            self.performance_metrics["total_loss"] += abs(pnl)
        
        # Tính toán các chỉ số khác
        win_rate = self.performance_metrics["winning_trades"] / self.performance_metrics["total_trades"] * 100 if self.performance_metrics["total_trades"] > 0 else 0
        self.performance_metrics["win_rate"] = win_rate
        
        profit_factor = self.performance_metrics["total_profit"] / self.performance_metrics["total_loss"] if self.performance_metrics["total_loss"] > 0 else 0
        self.performance_metrics["profit_factor"] = profit_factor
        
        # Tính toán drawdown
        current_drawdown = (self.initial_balance - self.balance) / self.initial_balance * 100 if self.balance < self.initial_balance else 0
        if current_drawdown > self.performance_metrics["max_drawdown"]:
            self.performance_metrics["max_drawdown"] = current_drawdown
        
        logger.info(f"Đã đóng vị thế {signal_type} {symbol} @ ${current_price:.2f}, P&L: ${pnl:.2f} ({pnl_pct:.2f}%), Lý do: {reason}")
        logger.info(f"Số dư hiện tại: ${self.balance:.2f}")
    
    def generate_training_data(self):
        """Giả lập quá trình tạo dữ liệu huấn luyện"""
        logger.info("Đang tạo dữ liệu huấn luyện...")
        
        # Giả lập thời gian xử lý
        time.sleep(1)
        
        # Giả lập kết quả
        result = {
            "samples": random.randint(1000, 5000),
            "features": random.randint(10, 30),
            "training_symbols": [p["symbol"] for p in TRADING_PAIRS if p["enabled"]],
            "time_taken": random.uniform(0.5, 2.0)
        }
        
        logger.info(f"Đã tạo {result['samples']} mẫu dữ liệu với {result['features']} đặc trưng")
        return result
    
    def train_model(self):
        """Giả lập quá trình huấn luyện mô hình ML"""
        logger.info("Bắt đầu huấn luyện mô hình...")
        
        # Tạo dữ liệu huấn luyện
        training_data = self.generate_training_data()
        
        # Giả lập thời gian huấn luyện
        training_time = random.uniform(1, 3)
        time.sleep(training_time)
        
        # Giả lập kết quả
        accuracy = random.uniform(65, 85)
        f1_score = random.uniform(0.6, 0.8)
        
        logger.info(f"Đã hoàn tất huấn luyện mô hình (thời gian: {training_time:.1f}s)")
        logger.info(f"Độ chính xác: {accuracy:.2f}%, F1-score: {f1_score:.2f}")
        
        # Cập nhật cho từng cặp giao dịch
        for pair in TRADING_PAIRS:
            if pair["enabled"]:
                symbol = pair["symbol"]
                # Cập nhật composite score ngẫu nhiên
                self.composite_scores[symbol]["score"] = random.uniform(-0.8, 0.8)
        
        return {
            "accuracy": accuracy,
            "f1_score": f1_score,
            "training_time": training_time,
            "training_data": training_data
        }
    
    def generate_daily_report(self):
        """Tạo báo cáo hiệu suất hàng ngày"""
        logger.info("Đang tạo báo cáo hiệu suất...")
        
        try:
            # Chạy module báo cáo
            import subprocess
            subprocess.run(["python", "daily_report.py"])
            logger.info("Đã tạo báo cáo hiệu suất thành công")
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo: {e}")
    
    def run(self):
        """Chạy giả lập giao dịch"""
        logger.info("Bot giao dịch đa đồng tiền đã khởi động")
        
        try:
            while self.running:
                current_time = datetime.now()
                
                # Không thực hiện gì nếu đang tạm dừng
                if self.paused:
                    time.sleep(1)
                    continue
                
                # Cập nhật giá thị trường
                time_elapsed = (current_time - self.last_price_update).total_seconds()
                if time_elapsed >= self.update_interval:
                    self.update_prices()
                    self.check_positions()
                    self.last_price_update = current_time
                
                # Kiểm tra tín hiệu giao dịch
                time_elapsed = (current_time - self.last_signal_check).total_seconds()
                if time_elapsed >= self.trade_interval:
                    self.check_signals()
                    self.last_signal_check = current_time
                
                # Huấn luyện lại mô hình
                time_elapsed = (current_time - self.last_training).total_seconds()
                if time_elapsed >= 4 * 3600:  # 4 giờ
                    logger.info(f"Đã {time_elapsed / 3600:.1f} giờ kể từ lần huấn luyện cuối")
                    training_result = self.train_model()
                    self.last_training = current_time
                
                # Tạo báo cáo định kỳ
                time_elapsed = (current_time - self.last_report).total_seconds()
                if time_elapsed >= self.report_interval:
                    logger.info("Cập nhật trạng thái định kỳ:")
                    logger.info(f"Số dư: ${self.balance:.2f}")
                    logger.info(f"Vị thế đang mở: {len(self.positions)}")
                    logger.info(f"Lịch sử giao dịch: {len(self.trade_history)} giao dịch")
                    
                    # Lưu trạng thái
                    self.save_state()
                    self.last_report = current_time
                    
                    # Tạo báo cáo hàng ngày nếu đủ 24 giờ
                    hours_elapsed = time_elapsed / 3600
                    if hours_elapsed >= 24:
                        self.generate_daily_report()
                
                # Đợi trước khi kiểm tra lại
                time.sleep(0.1)  # 100ms
                
        except KeyboardInterrupt:
            logger.info("Đang dừng bot giao dịch...")
        except Exception as e:
            logger.error(f"Lỗi: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Lưu trạng thái trước khi dừng
            self.save_state()
            logger.info("Bot giao dịch đã dừng")
    
    def stop(self):
        """Dừng bot giao dịch"""
        self.running = False
    
    def pause(self):
        """Tạm dừng bot giao dịch"""
        self.paused = True
        logger.info("Bot giao dịch đã tạm dừng")
    
    def resume(self):
        """Tiếp tục bot giao dịch"""
        self.paused = False
        logger.info("Bot giao dịch đã tiếp tục")

def main():
    """Hàm chính để chạy giả lập"""
    simulation = MultiCoinSimulation()
    
    # Khởi tạo thread riêng cho bot
    bot_thread = threading.Thread(target=simulation.run)
    bot_thread.daemon = True
    bot_thread.start()
    
    try:
        logger.info("Giả lập đang chạy. Nhấn Ctrl+C để dừng.")
        while bot_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Nhận lệnh dừng từ người dùng")
        simulation.stop()
        bot_thread.join(timeout=5)
    
    logger.info("Giả lập đã kết thúc")

if __name__ == "__main__":
    main()