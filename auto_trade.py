#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import logging
import schedule
from datetime import datetime
from binance_api import BinanceAPI
from adaptive_stop_loss_manager import AdaptiveStopLossManager
from multi_timeframe_volatility_analyzer import MultiTimeframeVolatilityAnalyzer

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_trade.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('auto_trade')

class AutoTrader:
    def __init__(self):
        self.api = BinanceAPI()
        self.stop_loss_manager = AdaptiveStopLossManager()
        self.volatility_analyzer = MultiTimeframeVolatilityAnalyzer()
        
        # Tải cấu hình tài khoản
        with open('account_config.json', 'r') as f:
            self.config = json.load(f)
        
        # Cặp tiền để giao dịch
        self.trade_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
        
        # Đòn bẩy mặc định
        self.default_leverage = 5
        
        # Khung thời gian phân tích
        self.timeframes = ["5m", "1h", "4h"]
        self.tf_weights = {"5m": 0.2, "1h": 0.5, "4h": 0.3}  # Trọng số từng khung thời gian
        
        # Chiến lược giao dịch
        self.strategies = ["trend_following", "rsi_reversal", "bollinger_bounce"]
        
        # Giới hạn vị thế đồng thời
        self.max_positions = 3
    
    def get_account_balance(self):
        """Lấy số dư tài khoản"""
        account_info = self.api.get_futures_account()
        balance = float(account_info.get('totalWalletBalance', 0))
        logger.info(f"Số dư tài khoản hiện tại: {balance} USDT")
        return balance
    
    def get_current_positions(self):
        """Lấy danh sách vị thế hiện tại"""
        positions = []
        positions_info = self.api.get_futures_position_risk()
        
        for position in positions_info:
            amt = float(position.get('positionAmt', 0))
            if amt != 0:  # Vị thế đang mở
                positions.append({
                    'symbol': position['symbol'],
                    'amount': amt,
                    'entryPrice': float(position['entryPrice']),
                    'side': 'BUY' if amt > 0 else 'SELL',
                    'leverage': int(position['leverage'])
                })
        
        logger.info(f"Số vị thế hiện tại: {len(positions)}")
        return positions
    
    def analyze_market(self, symbol):
        """Phân tích thị trường và đưa ra tín hiệu giao dịch"""
        signals = {}
        
        # Lấy giá hiện tại
        ticker = self.api.futures_ticker_price(symbol)
        # Kiểm tra định dạng kết quả trả về
        if isinstance(ticker, list):
            # Nếu là danh sách, tìm ticker phù hợp với symbol
            for t in ticker:
                if t.get('symbol') == symbol:
                    current_price = float(t.get('price', 0))
                    break
            else:
                # Nếu không tìm thấy, lấy từ API thị trường
                market_data = self.api.get_market_data()
                current_price = market_data.get(symbol, 0)
        else:
            # Nếu là dict, lấy giá trực tiếp
            current_price = float(ticker.get('price', 0))
        
        # Phân tích đa khung thời gian
        volatility_result = self.volatility_analyzer.analyze(symbol, self.timeframes)
        
        # Tính điểm tổng hợp dựa trên trọng số từng khung thời gian
        score = 0
        for tf in self.timeframes:
            if tf in volatility_result and 'signal' in volatility_result[tf]:
                if volatility_result[tf]['signal'] == 'BUY':
                    tf_score = 1
                elif volatility_result[tf]['signal'] == 'SELL':
                    tf_score = -1
                else:
                    tf_score = 0
                
                score += tf_score * self.tf_weights[tf]
        
        # Xác định tín hiệu cuối cùng
        if score > 0.3:  # Ngưỡng để xác định tín hiệu BUY
            signal = 'BUY'
            strategy = 'trend_following'
        elif score < -0.3:  # Ngưỡng để xác định tín hiệu SELL
            signal = 'SELL'
            strategy = 'trend_following'
        else:
            signal = 'NEUTRAL'
            strategy = None
        
        return {
            'symbol': symbol,
            'price': current_price,
            'signal': signal,
            'strategy': strategy,
            'score': score,
            'volatility': volatility_result
        }
    
    def execute_trade(self, symbol, side, price, strategy):
        """Thực hiện giao dịch"""
        # Kiểm tra số vị thế hiện tại
        current_positions = self.get_current_positions()
        if len(current_positions) >= self.max_positions:
            logger.info(f"Đã đạt giới hạn vị thế ({self.max_positions}), bỏ qua tín hiệu.")
            return None
        
        # Thiết lập đòn bẩy
        leverage = self.default_leverage
        try:
            self.api.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"Đã thiết lập đòn bẩy {leverage}x cho {symbol}")
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập đòn bẩy: {str(e)}")
            return None
        
        # Tính toán kích thước vị thế
        balance = self.get_account_balance()
        risk_amount = balance * 0.01  # Rủi ro 1% số dư
        position_size = round((risk_amount * leverage) / price, 3)
        
        # Tính toán stop loss và take profit
        sl_tp_info = self.stop_loss_manager.calculate_optimal_stop_loss(
            symbol, side, price, strategy
        )
        
        stop_loss_percent = sl_tp_info['stop_loss']['percent']
        take_profit_percent = sl_tp_info['take_profit']['percent']
        
        stop_loss_price = round(price * (1 - stop_loss_percent/100 if side == 'BUY' else 1 + stop_loss_percent/100), 2)
        take_profit_price = round(price * (1 + take_profit_percent/100 if side == 'BUY' else 1 - take_profit_percent/100), 2)
        
        logger.info(f"Thông số giao dịch {symbol}:")
        logger.info(f"- Đòn bẩy: {leverage}x")
        logger.info(f"- Kích thước vị thế: {position_size} (~{position_size * price} USDT)")
        logger.info(f"- Giá hiện tại: {price} USDT")
        logger.info(f"- Stop Loss: {stop_loss_price} USDT ({stop_loss_percent}%)")
        logger.info(f"- Take Profit: {take_profit_price} USDT ({take_profit_percent}%)")
        
        # Đặt lệnh MARKET
        try:
            order = self.api.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=position_size
            )
            logger.info(f"Đã đặt lệnh MARKET {side} thành công: {json.dumps(order, indent=2)}")
            
            # Đặt Stop Loss
            opposite_side = 'SELL' if side == 'BUY' else 'BUY'
            stop_order = self.api.futures_create_order(
                symbol=symbol,
                side=opposite_side,
                type='STOP_MARKET',
                stopPrice=stop_loss_price,
                closePosition='true'
            )
            logger.info(f"Đã đặt lệnh Stop Loss thành công")
            
            # Đặt Take Profit
            take_profit_order = self.api.futures_create_order(
                symbol=symbol,
                side=opposite_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=take_profit_price,
                closePosition='true'
            )
            logger.info(f"Đã đặt lệnh Take Profit thành công")
            
            return {
                'market_order': order,
                'stop_loss_order': stop_order,
                'take_profit_order': take_profit_order
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh: {str(e)}")
            return None
    
    def run_trading_cycle(self):
        """Chạy một chu kỳ giao dịch"""
        logger.info("Bắt đầu chu kỳ giao dịch mới")
        
        try:
            # Lấy các vị thế hiện tại
            current_positions = self.get_current_positions()
            current_symbols = [p['symbol'] for p in current_positions]
            
            # Phân tích thị trường cho các cặp tiền
            for symbol in self.trade_symbols:
                # Bỏ qua nếu đã có vị thế
                if symbol in current_symbols:
                    logger.info(f"Đã có vị thế cho {symbol}, bỏ qua phân tích")
                    continue
                
                # Phân tích thị trường
                analysis = self.analyze_market(symbol)
                logger.info(f"Kết quả phân tích {symbol}: Tín hiệu={analysis['signal']}, Điểm={analysis['score']:.2f}")
                
                # Nếu có tín hiệu giao dịch, thực hiện
                if analysis['signal'] in ['BUY', 'SELL'] and analysis['strategy']:
                    logger.info(f"Phát hiện tín hiệu {analysis['signal']} cho {symbol}, thực hiện giao dịch")
                    
                    # Thực hiện giao dịch
                    trade_result = self.execute_trade(
                        symbol=symbol,
                        side=analysis['signal'],
                        price=analysis['price'],
                        strategy=analysis['strategy']
                    )
                    
                    if trade_result:
                        logger.info(f"Giao dịch {symbol} {analysis['signal']} thành công")
                    else:
                        logger.warning(f"Giao dịch {symbol} {analysis['signal']} thất bại")
                else:
                    logger.info(f"Không có tín hiệu giao dịch cho {symbol}")
            
            logger.info("Hoàn thành chu kỳ giao dịch")
            
        except Exception as e:
            logger.error(f"Lỗi trong chu kỳ giao dịch: {str(e)}")
    
    def schedule_trading(self):
        """Thiết lập lịch trình giao dịch tự động"""
        # Chạy giao dịch mỗi 1 giờ
        schedule.every(1).hours.do(self.run_trading_cycle)
        
        # Chạy giao dịch ngay lập tức khi bắt đầu
        self.run_trading_cycle()
        
        logger.info("Đã thiết lập lịch trình giao dịch tự động")
        
        # Chạy vô hạn để duy trì lịch trình
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Kiểm tra mỗi phút
            except KeyboardInterrupt:
                logger.info("Thoát khỏi chương trình theo yêu cầu người dùng")
                break
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp chính: {str(e)}")
                time.sleep(60)  # Tiếp tục sau 60 giây nếu có lỗi
    
    def run_once(self):
        """Chạy một lần phân tích và giao dịch"""
        self.run_trading_cycle()
        
if __name__ == "__main__":
    trader = AutoTrader()
    
    if len(sys.argv) > 1 and sys.argv[1] == "schedule":
        # Chạy theo lịch trình tự động
        trader.schedule_trading()
    else:
        # Chạy một lần
        trader.run_once()