#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tự động thiết lập stop loss và take profit cho các vị thế đang mở

Script này kiểm tra các vị thế đang mở và tự động thiết lập stop loss (SL) và
take profit (TP) cho các vị thế chưa có, đặc biệt là ETH và các cặp tiền khác.
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auto_setup_sltp')

# Thêm thư mục gốc vào sys.path để import các module
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from binance_api import BinanceAPI
from profit_manager import ProfitManager
from data_cache import DataCache

def setup_sltp_for_positions(api_key: str = None, api_secret: str = None, testnet: bool = True, force_check: bool = False):
    """
    Thiết lập SL/TP cho các vị thế đang mở
    
    Args:
        api_key (str, optional): API key Binance
        api_secret (str, optional): API secret Binance
        testnet (bool): Sử dụng testnet hay không
        force_check (bool): Buộc kiểm tra lại tất cả các vị thế dù đã có SL/TP
    """
    try:
        # Khởi tạo các đối tượng cần thiết
        binance_api = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=testnet)
        data_cache = DataCache()
        
        # Tải cấu hình profit manager
        try:
            with open('configs/profit_manager_config.json', 'r') as f:
                profit_config = json.load(f)
        except Exception as e:
            logger.warning(f"Không thể tải cấu hình profit manager: {str(e)}")
            profit_config = {}
            
        # Khởi tạo profit manager
        profit_manager = ProfitManager(config=profit_config, data_cache=data_cache)
        
        # Lấy danh sách vị thế đang mở
        positions = binance_api.futures_get_position()
        
        # Lấy tất cả lệnh đang mở để kiểm tra cả lệnh chờ ETH
        all_open_orders = binance_api.get_open_orders()  # Không truyền symbol để lấy tất cả các lệnh
        logger.info(f"Đang có {len(all_open_orders)} lệnh đang mở/chờ")
        
        # Kiểm tra lệnh ETH đang chờ
        check_pending_eth_orders(binance_api, all_open_orders)
        
        if not positions:
            logger.info("Không có vị thế nào đang mở")
            return
            
        logger.info(f"Đã tìm thấy {len(positions)} vị thế đang mở")
        
        # Kiểm tra và thiết lập SL/TP cho từng vị thế
        for position in positions:
            symbol = position.get('symbol')
            side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
            entry_price = float(position.get('entryPrice', 0))
            leverage = int(position.get('leverage', 1))
            
            # Bỏ qua các vị thế có lượng = 0
            position_amt = float(position.get('positionAmt', 0))
            if abs(position_amt) <= 0:
                continue
                
            logger.info(f"Kiểm tra vị thế {symbol} {side}: Entry price={entry_price}")
            
            # Kiểm tra nếu đã có SL/TP
            existing_orders = binance_api.get_open_orders(symbol)
            has_sl = any(order.get('type') == 'STOP_MARKET' for order in existing_orders)
            has_tp = any(order.get('type') == 'TAKE_PROFIT_MARKET' for order in existing_orders)
            
            # Lấy giá hiện tại
            current_price = float(binance_api.get_symbol_ticker(symbol).get('price', 0))
            
            # Lấy giá trị ATR nếu có
            try:
                atr_value = get_atr_value(binance_api, symbol, '1h')
            except Exception as e:
                logger.warning(f"Không thể lấy giá trị ATR cho {symbol}: {str(e)}")
                atr_value = None
            
            # Thiết lập SL nếu chưa có
            if not has_sl:
                sl_price = calculate_stop_loss(entry_price, current_price, side, atr_value, profit_config)
                if sl_price > 0:
                    try:
                        result = binance_api.futures_set_stop_loss(symbol, side, sl_price)
                        if 'error' in result:
                            logger.error(f"Lỗi khi đặt SL cho {symbol}: {result.get('error')}")
                        else:
                            logger.info(f"Đã đặt SL cho {symbol} {side} tại giá {sl_price}")
                    except Exception as e:
                        logger.error(f"Lỗi khi đặt SL cho {symbol}: {str(e)}")
                else:
                    logger.warning(f"Không thể tính giá SL hợp lệ cho {symbol}")
            else:
                logger.info(f"Vị thế {symbol} đã có SL")
            
            # Thiết lập TP nếu chưa có
            if not has_tp:
                tp_price = calculate_take_profit(entry_price, current_price, side, atr_value, profit_config, symbol, leverage)
                if tp_price > 0:
                    try:
                        result = binance_api.futures_set_take_profit(symbol, side, tp_price)
                        if 'error' in result:
                            logger.error(f"Lỗi khi đặt TP cho {symbol}: {result.get('error')}")
                        else:
                            logger.info(f"Đã đặt TP cho {symbol} {side} tại giá {tp_price}")
                    except Exception as e:
                        logger.error(f"Lỗi khi đặt TP cho {symbol}: {str(e)}")
                else:
                    logger.warning(f"Không thể tính giá TP hợp lệ cho {symbol}")
            else:
                logger.info(f"Vị thế {symbol} đã có TP")
        
        logger.info("Đã kiểm tra và thiết lập SL/TP cho tất cả vị thế")
        
    except Exception as e:
        logger.error(f"Lỗi trong quá trình thiết lập SL/TP: {str(e)}")

def calculate_stop_loss(entry_price: float, current_price: float, side: str, atr_value: Optional[float], 
                      config: Dict) -> float:
    """
    Tính toán giá stop loss
    
    Args:
        entry_price (float): Giá vào lệnh
        current_price (float): Giá hiện tại
        side (str): Phía vị thế ('LONG' hoặc 'SHORT')
        atr_value (float, optional): Giá trị ATR
        config (Dict): Cấu hình profit manager
        
    Returns:
        float: Giá stop loss
    """
    # Thiết lập giới hạn % tối đa cho SL
    max_sl_percent = 5.0  # Tối đa 5% từ giá entry
    
    # Tính toán SL phù hợp
    if side == 'LONG':
        # Sử dụng % cố định
        sl_percent = 2.0  # Mặc định 2%
        sl_percent_adjusted = min(sl_percent, max_sl_percent)
        sl_price = entry_price * (1 - sl_percent_adjusted / 100)
        
        # Giới hạn SL không quá xa giá hiện tại
        min_sl_price = current_price * 0.9  # Không thấp hơn 90% giá hiện tại
        sl_price = max(sl_price, min_sl_price)
    else:
        # Sử dụng % cố định
        sl_percent = 2.0  # Mặc định 2%
        sl_percent_adjusted = min(sl_percent, max_sl_percent)
        sl_price = entry_price * (1 + sl_percent_adjusted / 100)
        
        # Giới hạn SL không quá xa giá hiện tại
        max_sl_price = current_price * 1.1  # Không cao hơn 110% giá hiện tại
        sl_price = min(sl_price, max_sl_price)
    
    # Đảm bảo SL không quá gần giá hiện tại
    min_distance = current_price * 0.005  # Ít nhất 0.5% từ giá hiện tại
    if side == 'LONG' and sl_price > current_price - min_distance:
        sl_price = current_price - min_distance
    elif side == 'SHORT' and sl_price < current_price + min_distance:
        sl_price = current_price + min_distance
        
    # Làm tròn giá
    sl_price = round(sl_price, 4)
    
    logger.info(f"Tính toán SL: Entry={entry_price}, Current={current_price}, Side={side}, SL={sl_price}")
    
    return sl_price

def calculate_take_profit(entry_price: float, current_price: float, side: str, atr_value: Optional[float], 
                       config: Dict, symbol: str, leverage: int) -> float:
    """
    Tính toán giá take profit
    
    Args:
        entry_price (float): Giá vào lệnh
        current_price (float): Giá hiện tại
        side (str): Phía vị thế ('LONG' hoặc 'SHORT')
        atr_value (float, optional): Giá trị ATR
        config (Dict): Cấu hình profit manager
        symbol (str): Mã cặp tiền
        leverage (int): Đòn bẩy
        
    Returns:
        float: Giá take profit
    """
    # Lấy target profit từ cấu hình
    target_profit = config.get('target_profit', {}).get('profit_target', 2.0)
    
    # Kiểm tra cấu hình cho tài khoản nhỏ
    small_account_settings = config.get('small_account_settings', {})
    if small_account_settings.get('enabled', False) and small_account_settings.get('lower_profit_targets', False):
        if symbol == 'BTCUSDT':
            target_profit = small_account_settings.get('btc_profit_target', 1.5)
        elif symbol == 'ETHUSDT':
            target_profit = small_account_settings.get('eth_profit_target', 2.0)
        else:
            target_profit = small_account_settings.get('altcoin_profit_target', 3.0)
    
    # Điều chỉnh target dựa trên đòn bẩy
    effective_target = target_profit / leverage if leverage > 1 else target_profit
    
    # Thiết lập giới hạn % tối đa cho TP
    max_tp_percent = 10.0  # Tối đa 10% từ giá entry
    
    # Tính toán TP phù hợp
    if side == 'LONG':
        # Sử dụng % mục tiêu
        tp_percent = effective_target  # Từ cấu hình
        tp_percent_adjusted = min(tp_percent, max_tp_percent)
        tp_price = entry_price * (1 + tp_percent_adjusted / 100)
        
        # Giới hạn TP không quá xa giá hiện tại
        max_tp_price = current_price * 1.15  # Không cao hơn 115% giá hiện tại
        tp_price = min(tp_price, max_tp_price)
    else:
        # Sử dụng % mục tiêu
        tp_percent = effective_target  # Từ cấu hình
        tp_percent_adjusted = min(tp_percent, max_tp_percent)
        tp_price = entry_price * (1 - tp_percent_adjusted / 100)
        
        # Giới hạn TP không quá xa giá hiện tại
        min_tp_price = current_price * 0.85  # Không thấp hơn 85% giá hiện tại
        tp_price = max(tp_price, min_tp_price)
    
    # Đảm bảo TP không quá gần giá hiện tại
    min_distance = current_price * 0.01  # Ít nhất 1% từ giá hiện tại
    if side == 'LONG' and tp_price < current_price + min_distance:
        tp_price = current_price + min_distance
    elif side == 'SHORT' and tp_price > current_price - min_distance:
        tp_price = current_price - min_distance
        
    # Làm tròn giá
    tp_price = round(tp_price, 4)
    
    logger.info(f"Tính toán TP: Entry={entry_price}, Current={current_price}, Side={side}, Symbol={symbol}, TP={tp_price}")
    
    return tp_price

def get_atr_value(binance_api: BinanceAPI, symbol: str, timeframe: str = '1h', period: int = 14) -> Optional[float]:
    """
    Tính giá trị ATR (Average True Range)
    
    Args:
        binance_api (BinanceAPI): Đối tượng API Binance
        symbol (str): Mã cặp tiền
        timeframe (str): Khung thời gian
        period (int): Số chu kỳ ATR
        
    Returns:
        Optional[float]: Giá trị ATR hoặc None nếu không tính được
    """
    try:
        # Lấy dữ liệu k-line
        klines = binance_api.get_klines(symbol, timeframe, limit=period+1)
        
        if not klines or len(klines) < period:
            return None
            
        # Chuyển đổi dữ liệu
        highs = [float(kline[2]) for kline in klines]
        lows = [float(kline[3]) for kline in klines]
        closes = [float(kline[4]) for kline in klines]
        
        # Tính True Range
        tr_values = []
        for i in range(1, len(closes)):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i-1]
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            tr = max(tr1, tr2, tr3)
            tr_values.append(tr)
        
        # Tính ATR
        atr = sum(tr_values) / len(tr_values)
        return atr
        
    except Exception as e:
        logger.error(f"Lỗi khi tính ATR cho {symbol}: {str(e)}")
        return None

def check_pending_eth_orders(binance_api: BinanceAPI, all_orders: List[Dict]) -> None:
    """
    Kiểm tra các lệnh ETH đang chờ xử lý
    
    Args:
        binance_api (BinanceAPI): Đối tượng API Binance
        all_orders (List[Dict]): Tất cả các lệnh đang mở
    """
    # Lọc ra các lệnh ETH
    eth_orders = [order for order in all_orders if order.get('symbol') == 'ETHUSDT']
    
    if not eth_orders:
        logger.info("Không có lệnh ETH nào đang chờ xử lý")
        return
    
    logger.info(f"Đang có {len(eth_orders)} lệnh ETH đang chờ xử lý")
    
    # Kiểm tra từng lệnh
    for order in eth_orders:
        order_id = order.get('orderId')
        order_type = order.get('type')
        side = order.get('side')
        price = float(order.get('price', 0))
        
        logger.info(f"Lệnh ETH #{order_id}: Loại={order_type}, Phía={side}, Giá={price}")
        
        # Lấy giá hiện tại
        current_price = float(binance_api.get_symbol_ticker('ETHUSDT').get('price', 0))
        
        # Kiểm tra tính hợp lệ của lệnh
        if order_type == 'LIMIT':
            price_diff_percent = abs(price - current_price) / current_price * 100
            if price_diff_percent > 5:
                logger.warning(f"Lệnh ETH #{order_id} có giá ({price}) chênh lệch {price_diff_percent:.2f}% so với giá hiện tại ({current_price})")
            else:
                logger.info(f"Lệnh ETH #{order_id} có giá hợp lý ({price_diff_percent:.2f}% chênh lệch)")
            
            # Kiểm tra nếu lệnh này đã có SL/TP được chuẩn bị
            client_order_id = order.get('clientOrderId', '')
            has_sl_tp_preparation = client_order_id.startswith('auto') or 'sltp' in client_order_id.lower()
            
            if not has_sl_tp_preparation:
                logger.warning(f"Lệnh ETH #{order_id} không có chuẩn bị SL/TP tự động")
                
                # Ghi lại lệnh vào file để theo dõi
                _log_manual_order('ETHUSDT', order)

def _log_manual_order(symbol: str, order_data: Dict) -> None:
    """
    Ghi lại thông tin lệnh vào file để theo dõi
    
    Args:
        symbol (str): Mã cặp tiền
        order_data (Dict): Dữ liệu lệnh
    """
    try:
        manual_orders_file = 'manual_orders.json'
        manual_orders = []
        
        # Đọc file nếu đã tồn tại
        if os.path.exists(manual_orders_file):
            try:
                with open(manual_orders_file, 'r') as f:
                    manual_orders = json.load(f)
            except:
                manual_orders = []
        
        # Thêm thông tin thời gian
        order_data['logged_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        order_data['symbol'] = symbol
        
        # Thêm lệnh mới
        manual_orders.append(order_data)
        
        # Ghi file
        with open(manual_orders_file, 'w') as f:
            json.dump(manual_orders, f, indent=4)
            
        logger.info(f"Đã ghi lại lệnh thủ công {symbol} vào file {manual_orders_file}")
    except Exception as e:
        logger.error(f"Lỗi khi ghi lệnh thủ công: {str(e)}")

def track_manual_positions(binance_api: BinanceAPI) -> None:
    """
    Theo dõi và quản lý các vị thế được mở thủ công
    
    Args:
        binance_api (BinanceAPI): Đối tượng API Binance
    """
    try:
        # Lấy danh sách vị thế đang mở
        positions = binance_api.futures_get_position()
        
        # Lọc ra các vị thế có lượng > 0
        active_positions = [p for p in positions if abs(float(p.get('positionAmt', 0))) > 0]
        
        if not active_positions:
            logger.info("Không có vị thế nào đang mở")
            return
        
        # Đọc file lịch sử lệnh thủ công nếu có
        manual_orders_file = 'manual_orders.json'
        manual_orders = []
        
        if os.path.exists(manual_orders_file):
            try:
                with open(manual_orders_file, 'r') as f:
                    manual_orders = json.load(f)
            except:
                manual_orders = []
        
        # Tạo danh sách các cặp tiền đã được ghi lại là lệnh thủ công
        manual_symbols = set(order.get('symbol') for order in manual_orders)
        
        # Kiểm tra các vị thế đang mở có SL/TP chưa
        for position in active_positions:
            symbol = position.get('symbol')
            position_amt = float(position.get('positionAmt', 0))
            side = 'LONG' if position_amt > 0 else 'SHORT'
            
            # Bỏ qua các vị thế không có lượng
            if abs(position_amt) <= 0:
                continue
            
            # Kiểm tra nếu cặp tiền này đã được ghi nhận là lệnh thủ công
            is_manual = symbol in manual_symbols
            
            if is_manual:
                logger.info(f"Vị thế {symbol} {side} được ghi nhận là lệnh thủ công")
            
            # Kiểm tra SL/TP
            existing_orders = binance_api.get_open_orders(symbol)
            has_sl = any(order.get('type') == 'STOP_MARKET' for order in existing_orders)
            has_tp = any(order.get('type') == 'TAKE_PROFIT_MARKET' for order in existing_orders)
            
            # Nếu chưa có SL hoặc TP, thiết lập
            if not has_sl or not has_tp:
                logger.warning(f"Vị thế {symbol} {side} chưa có đầy đủ SL/TP")
                
                # Lấy giá hiện tại
                current_price = float(binance_api.get_symbol_ticker(symbol).get('price', 0))
                
                # Lấy giá trị ATR nếu có
                try:
                    atr_value = get_atr_value(binance_api, symbol, '1h')
                except Exception as e:
                    logger.warning(f"Không thể lấy giá trị ATR cho {symbol}: {str(e)}")
                    atr_value = None
                
                # Tải cấu hình profit manager
                try:
                    with open('configs/profit_manager_config.json', 'r') as f:
                        profit_config = json.load(f)
                except Exception as e:
                    logger.warning(f"Không thể tải cấu hình profit manager: {str(e)}")
                    profit_config = {}
                
                entry_price = float(position.get('entryPrice', 0))
                leverage = int(position.get('leverage', 1))
                
                # Thiết lập SL nếu chưa có
                if not has_sl:
                    sl_price = calculate_stop_loss(entry_price, current_price, side, atr_value, profit_config)
                    if sl_price > 0:
                        try:
                            result = binance_api.futures_set_stop_loss(symbol, side, sl_price)
                            logger.info(f"Đã đặt SL cho vị thế thủ công {symbol} {side} tại giá {sl_price}")
                        except Exception as e:
                            logger.error(f"Lỗi khi đặt SL cho {symbol}: {str(e)}")
                
                # Thiết lập TP nếu chưa có
                if not has_tp:
                    tp_price = calculate_take_profit(entry_price, current_price, side, atr_value, profit_config, symbol, leverage)
                    if tp_price > 0:
                        try:
                            result = binance_api.futures_set_take_profit(symbol, side, tp_price)
                            logger.info(f"Đã đặt TP cho vị thế thủ công {symbol} {side} tại giá {tp_price}")
                        except Exception as e:
                            logger.error(f"Lỗi khi đặt TP cho {symbol}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Lỗi khi theo dõi vị thế thủ công: {str(e)}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Tự động thiết lập SL/TP cho các vị thế đang mở')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng testnet')
    parser.add_argument('--force', action='store_true', help='Buộc kiểm tra lại tất cả các vị thế')
    parser.add_argument('--track-manual', action='store_true', help='Theo dõi và thiết lập SL/TP cho các vị thế thủ công')
    args = parser.parse_args()
    
    binance_api = BinanceAPI(testnet=args.testnet)
    
    if args.track_manual:
        logger.info("Theo dõi và thiết lập SL/TP cho các vị thế thủ công")
        track_manual_positions(binance_api)
    else:
        logger.info("Thiết lập SL/TP cho các vị thế đang mở")
        setup_sltp_for_positions(testnet=args.testnet, force_check=args.force)

if __name__ == "__main__":
    main()