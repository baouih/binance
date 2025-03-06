#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script cập nhật lịch sử giao dịch và vị thế hiện tại

Script này:
1. Lấy thông tin giao dịch gần đây từ Binance API
2. Cập nhật lại file trade_history.json
3. Cập nhật active_positions.json dựa trên vị thế hiện tại
4. Cập nhật bot_status.json để phản ánh trạng thái hiện tại
"""

import json
import logging
import os
from datetime import datetime, timedelta
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trade_history_updater')

def load_json_file(file_path, default=None):
    """Tải dữ liệu từ file JSON"""
    if not os.path.exists(file_path):
        return default if default is not None else {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.warning(f"Không thể đọc file {file_path}, sử dụng giá trị mặc định")
        return default if default is not None else {}

def save_json_file(file_path, data):
    """Lưu dữ liệu vào file JSON"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu file {file_path}: {e}")
        return False

def update_trade_history():
    """Cập nhật lịch sử giao dịch"""
    api = BinanceAPI()
    
    # Lấy lịch sử giao dịch (7 ngày gần nhất để tránh lỗi timestamp)
    start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)
    
    try:
        # Lấy danh sách các cặp tiền từ account_config.json
        account_config = load_json_file('account_config.json')
        symbols = account_config.get('symbols', ["BTCUSDT", "ETHUSDT"])
        
        # Lấy lịch sử giao dịch từ API
        all_trades = []
        
        logger.info("Đang lấy lịch sử giao dịch từ Binance API...")
        for symbol in symbols:
            try:
                # Sử dụng get_all_orders để lấy lịch sử giao dịch
                trades = api.get_all_orders(symbol=symbol, start_time=start_time, end_time=end_time) or []
                filled_trades = [t for t in trades if t.get('status') == 'FILLED']
                logger.info(f"Đã lấy {len(filled_trades)} giao dịch cho {symbol}")
                all_trades.extend(filled_trades)
            except Exception as symbol_error:
                logger.warning(f"Không thể lấy giao dịch cho {symbol}: {symbol_error}")
        
        # Chuyển đổi định dạng và lưu vào trade_history.json
        trade_history = []
        for trade in all_trades:
            try:
                timestamp = datetime.fromtimestamp(trade.get('time', 0) / 1000).isoformat()
                symbol = trade.get('symbol')
                action = trade.get('side', 'UNKNOWN')
                price = float(trade.get('price', 0))
                quantity = float(trade.get('executedQty', 0))
                order_id = trade.get('orderId')
                order_type = trade.get('type', 'UNKNOWN')
                
                trade_entry = {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "action": action,
                    "price": price,
                    "quantity": quantity,
                    "type": order_type,
                    "mode": "testnet",
                    "success": True,
                    "error": None,
                    "order_id": order_id
                }
                trade_history.append(trade_entry)
            except Exception as trade_error:
                logger.warning(f"Lỗi khi xử lý giao dịch: {trade_error}")
        
        # Sắp xếp theo thời gian mới nhất
        trade_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Lưu vào file
        with open('trade_history.json', 'w', encoding='utf-8') as f:
            for trade in trade_history:
                f.write(json.dumps(trade, ensure_ascii=False) + '\n')
        
        logger.info(f"Đã cập nhật {len(trade_history)} giao dịch vào trade_history.json")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật lịch sử giao dịch: {e}")
        return False

def update_active_positions():
    """Cập nhật vị thế đang mở"""
    api = BinanceAPI()
    
    try:
        # Lấy vị thế đang mở từ API
        account_info = api.get_futures_account()
        positions_info = account_info.get('positions', [])
        active_positions = {}
        
        # Lọc ra các vị thế có số lượng khác 0
        for pos in positions_info:
            symbol = pos.get('symbol')
            amount = float(pos.get('positionAmt', 0))
            
            if amount != 0:
                entry_price = float(pos.get('entryPrice', 0))
                leverage = int(pos.get('leverage', 1))
                unrealized_profit = float(pos.get('unrealizedProfit', 0))
                margin_type = pos.get('marginType', 'cross')
                
                direction = "LONG" if amount > 0 else "SHORT"
                
                active_positions[symbol] = {
                    "symbol": symbol,
                    "amount": abs(amount),
                    "direction": direction,
                    "entry_price": entry_price,
                    "leverage": leverage,
                    "unrealized_profit": unrealized_profit,
                    "margin_type": margin_type,
                    "entry_time": datetime.now().isoformat(),
                    "last_update": datetime.now().isoformat()
                }
        
        # Lưu vào file
        save_json_file('active_positions.json', active_positions)
        
        logger.info(f"Đã cập nhật {len(active_positions)} vị thế đang mở vào active_positions.json")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật vị thế đang mở: {e}")
        return False

def update_bot_status():
    """Cập nhật trạng thái bot"""
    api = BinanceAPI()
    
    try:
        # Lấy thông tin tài khoản
        account = api.get_futures_account()
        balance = float(account.get('totalWalletBalance', 0))
        
        # Lấy trạng thái bot hiện tại
        bot_status = load_json_file('bot_status.json')
        
        # Cập nhật thông tin
        active_positions = load_json_file('active_positions.json')
        active_symbols = list(active_positions.keys())
        
        bot_status['balance'] = balance
        bot_status['active_symbols'] = active_symbols
        bot_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        bot_status['running'] = True
        
        # Lấy chế độ thị trường từ phân tích gần nhất
        market_analysis = load_json_file('reports/market_analysis_results.json', [])
        if market_analysis:
            latest_analysis = market_analysis[-1]
            bot_status['market_regime'] = latest_analysis.get('market_regime', 'neutral')
        
        # Lưu vào file
        save_json_file('bot_status.json', bot_status)
        
        logger.info(f"Đã cập nhật bot_status.json với số dư {balance:.2f} USDT")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật trạng thái bot: {e}")
        return False

def main():
    logger.info("Bắt đầu cập nhật lịch sử giao dịch và vị thế hiện tại...")
    
    # Cập nhật lịch sử giao dịch
    update_trade_history()
    
    # Cập nhật vị thế đang mở
    update_active_positions()
    
    # Cập nhật trạng thái bot
    update_bot_status()
    
    logger.info("Đã hoàn thành cập nhật lịch sử giao dịch và vị thế hiện tại")

if __name__ == '__main__':
    main()