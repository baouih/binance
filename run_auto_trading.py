#!/usr/bin/env python3
"""
Script tự động chạy và training bot giao dịch
"""
import os
import time
import json
import logging
import random
import threading
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_trading.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auto_trading")

# Thiết lập dữ liệu giả cho giao dịch
class SimulatedTrading:
    def __init__(self):
        self.balance = 10000.0
        self.positions = []
        self.trade_history = []
        self.current_prices = {
            "BTCUSDT": 83000 + random.uniform(-2000, 2000),
            "ETHUSDT": 2300 + random.uniform(-100, 100),
            "BNBUSDT": 380 + random.uniform(-20, 20),
            "SOLUSDT": 140 + random.uniform(-10, 10),
            "DOGEUSDT": 0.12 + random.uniform(-0.01, 0.01)
        }
        self.load_state()
        logger.info(f"Khởi tạo tài khoản với số dư: ${self.balance:.2f}")
        
    def load_state(self):
        """Tải trạng thái giao dịch từ file (nếu có)"""
        try:
            if os.path.exists("trading_state.json"):
                with open("trading_state.json", "r") as f:
                    state = json.load(f)
                    self.balance = state.get("balance", self.balance)
                    self.positions = state.get("positions", [])
                    self.trade_history = state.get("trade_history", [])
                    logger.info("Đã tải trạng thái giao dịch từ file")
        except Exception as e:
            logger.error(f"Lỗi khi tải trạng thái: {e}")
    
    def save_state(self):
        """Lưu trạng thái giao dịch vào file"""
        try:
            state = {
                "balance": self.balance,
                "positions": self.positions,
                "trade_history": self.trade_history
            }
            with open("trading_state.json", "w") as f:
                json.dump(state, f, indent=4)
            logger.info("Đã lưu trạng thái giao dịch")
        except Exception as e:
            logger.error(f"Lỗi khi lưu trạng thái: {e}")
    
    def update_prices(self):
        """Cập nhật giá thị trường"""
        for symbol in self.current_prices:
            # Tạo biến động giá ngẫu nhiên với xu hướng nhẹ
            price_change_pct = random.uniform(-0.5, 0.5) / 100  # biến động 0.5%
            self.current_prices[symbol] *= (1 + price_change_pct)
        
        # Cập nhật giá các vị thế và tính P&L
        for position in self.positions:
            current_price = self.current_prices[position["symbol"]]
            position["current_price"] = current_price
            
            if position["type"] == "LONG":
                profit = (current_price - position["entry_price"]) * position["quantity"]
                profit_pct = (current_price / position["entry_price"] - 1) * 100
            else:  # SHORT
                profit = (position["entry_price"] - current_price) * position["quantity"]
                profit_pct = (position["entry_price"] / current_price - 1) * 100
            
            position["pnl"] = profit
            position["pnl_pct"] = profit_pct
    
    def generate_signal(self, symbol):
        """Tạo tín hiệu giao dịch"""
        # Tỷ lệ xuất hiện tín hiệu thấp
        if random.random() < 0.1:  # 10% cơ hội có tín hiệu
            signal = random.choice(["BUY", "SELL"])
            price = self.current_prices[symbol]
            confidence = random.randint(60, 95)
            
            logger.info(f"Tín hiệu: {signal} {symbol} @ ${price:.2f} (độ tin cậy: {confidence}%)")
            return {
                "symbol": symbol,
                "signal": signal,
                "price": price,
                "confidence": confidence,
                "time": datetime.now().strftime("%H:%M:%S")
            }
        return None
    
    def execute_trade(self, signal):
        """Thực hiện giao dịch dựa trên tín hiệu"""
        symbol = signal["symbol"]
        signal_type = signal["signal"]
        price = signal["price"]
        
        # Kiểm tra xem đã có vị thế cho symbol này chưa
        for position in self.positions:
            if position["symbol"] == symbol:
                logger.info(f"Đã có vị thế cho {symbol}, bỏ qua tín hiệu")
                return None
        
        # Tính kích thước vị thế (1% tài khoản)
        position_value = self.balance * 0.01
        quantity = position_value / price
        
        # Tạo ID giao dịch
        trade_id = f"{symbol}_{len(self.trade_history) + 1}"
        
        # Tạo vị thế mới
        position = {
            "id": trade_id,
            "symbol": symbol,
            "type": signal_type,
            "entry_price": price,
            "current_price": price,
            "quantity": quantity,
            "entry_time": datetime.now().isoformat(),
            "pnl": 0.0,
            "pnl_pct": 0.0
        }
        
        self.positions.append(position)
        logger.info(f"Đã tạo vị thế {signal_type} cho {symbol} @ ${price:.2f}, số lượng: {quantity:.6f}")
        
        return position
    
    def check_positions(self):
        """Kiểm tra các vị thế và tự động đóng vị thế khi đạt điều kiện"""
        positions_to_close = []
        
        for position in self.positions:
            # Kiểm tra take profit (5%) hoặc stop loss (2%)
            if position["pnl_pct"] >= 5.0 or position["pnl_pct"] <= -2.0:
                positions_to_close.append(position)
        
        # Đóng các vị thế đủ điều kiện
        for position in positions_to_close:
            self.close_position(position)
    
    def close_position(self, position):
        """Đóng vị thế"""
        # Cập nhật số dư
        self.balance += position["pnl"]
        
        # Thêm vào lịch sử giao dịch
        trade_record = position.copy()
        trade_record["exit_time"] = datetime.now().isoformat()
        trade_record["exit_price"] = position["current_price"]
        
        if position["pnl"] > 0:
            reason = "Take Profit"
        else:
            reason = "Stop Loss"
        
        trade_record["exit_reason"] = reason
        self.trade_history.append(trade_record)
        
        # Xóa khỏi danh sách vị thế
        self.positions.remove(position)
        
        logger.info(f"Đã đóng vị thế {position['type']} {position['symbol']} @ ${position['current_price']:.2f}, P&L: ${position['pnl']:.2f} ({position['pnl_pct']:.2f}%)")
        logger.info(f"Số dư hiện tại: ${self.balance:.2f}")

    def train_model(self):
        """Giả lập quá trình huấn luyện mô hình ML"""
        logger.info("Bắt đầu huấn luyện mô hình...")
        
        # Giả lập thời gian huấn luyện
        training_time = random.randint(30, 120)
        time.sleep(2)  # Thực tế sẽ mất nhiều thời gian hơn
        
        accuracy = random.uniform(65, 85)
        f1_score = random.uniform(0.6, 0.8)
        
        logger.info(f"Đã hoàn tất huấn luyện mô hình (giả lập thời gian: {training_time}s)")
        logger.info(f"Độ chính xác: {accuracy:.2f}%, F1-score: {f1_score:.2f}")
        
        return {
            "accuracy": accuracy,
            "f1_score": f1_score,
            "training_time": training_time
        }

def run_trading_bot():
    """Chạy bot giao dịch giả lập"""
    bot = SimulatedTrading()
    
    # Thiết lập thời gian huấn luyện lần cuối
    last_training_time = datetime.now() - timedelta(hours=4)  # Huấn luyện ngay từ đầu
    
    try:
        logger.info("Bot giao dịch đã khởi động")
        
        while True:
            # Cập nhật giá
            bot.update_prices()
            
            # Kiểm tra và đóng vị thế nếu cần
            bot.check_positions()
            
            # Tạo tín hiệu giao dịch cho các cặp tiền
            symbols = list(bot.current_prices.keys())
            for symbol in symbols:
                signal = bot.generate_signal(symbol)
                if signal:
                    bot.execute_trade(signal)
            
            # Kiểm tra xem có cần huấn luyện lại mô hình không
            current_time = datetime.now()
            hours_since_last_training = (current_time - last_training_time).total_seconds() / 3600
            
            if hours_since_last_training >= 4:  # Huấn luyện mỗi 4 giờ
                logger.info(f"Đã {hours_since_last_training:.1f} giờ kể từ lần huấn luyện cuối")
                training_result = bot.train_model()
                last_training_time = current_time
            
            # Lưu trạng thái
            bot.save_state()
            
            # Đợi trước khi kiểm tra lại
            time.sleep(5)  # 5 giây mỗi chu kỳ
            
    except KeyboardInterrupt:
        logger.info("Đang dừng bot giao dịch...")
    except Exception as e:
        logger.error(f"Lỗi: {e}")
    finally:
        bot.save_state()
        logger.info("Bot giao dịch đã dừng")

if __name__ == "__main__":
    run_trading_bot()
