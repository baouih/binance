import argparse
import json
import logging
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Tắt backend đồ họa

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_backtest')

def load_risk_config():
    """Tải cấu hình rủi ro từ file"""
    try:
        with open('account_risk_config.json', 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Lỗi tải cấu hình: {e}")
        return {
            "risk_levels": {
                "low": {
                    "risk_per_trade": 3.0,
                    "max_leverage": 3,
                    "max_open_positions": 5
                }
            },
            "atr_settings": {
                "atr_period": 14,
                "atr_multiplier": {"low": 1.5},
                "take_profit_atr_multiplier": {"low": 4.0}
            }
        }

def run_backtest(symbols, period="3mo", timeframe="1d", initial_balance=10000.0):
    """Chạy backtest đơn giản"""
    # Tải cấu hình
    risk_config = load_risk_config()
    risk_level = "low"
    risk_params = risk_config["risk_levels"][risk_level]
    
    logger.info(f"=== BẮT ĐẦU BACKTEST ĐƠN GIẢN ===")
    logger.info(f"Số lượng symbols: {len(symbols)}")
    logger.info(f"Khung thời gian: {timeframe}")
    logger.info(f"Khoảng thời gian: {period}")
    logger.info(f"Số dư ban đầu: ${initial_balance}")
    logger.info(f"Mức rủi ro: {risk_level}")
    logger.info(f"Rủi ro/Giao dịch: {risk_params['risk_per_trade']}%")
    logger.info(f"Đòn bẩy: {risk_params['max_leverage']}x")
    
    # Thông tin kết quả
    balance = initial_balance
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    
    # Danh sách giao dịch và kết quả theo symbol
    all_trades = []
    symbol_results = {}
    
    # Chạy backtest cho từng symbol
    for symbol in symbols:
        logger.info(f"\nBắt đầu backtest {symbol}")
        
        # Tải dữ liệu
        try:
            data = yf.download(symbol, period=period, interval=timeframe)
            logger.info(f"Đã tải {len(data)} dòng dữ liệu cho {symbol}")
            
            if len(data) < 20:  # Cần ít nhất 20 dòng dữ liệu
                logger.warning(f"Không đủ dữ liệu cho {symbol}, bỏ qua")
                continue
                
            # Tính RSI
            delta = data['Close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Tính ATR (Average True Range)
            high_low = data['High'] - data['Low']
            high_close = abs(data['High'] - data['Close'].shift())
            low_close = abs(data['Low'] - data['Close'].shift())
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(14).mean()
            
            # Tính biến động
            volatility = atr / data['Close'] * 100
            
            # Tìm tín hiệu giao dịch
            symbol_trades = []
            
            # Kiểm tra các điểm RSI thấp (dưới 30) và tìm điểm phục hồi
            for i in range(15, len(data)-1):
                # Tránh sử dụng .iloc[] với các phép so sánh trực tiếp để tránh lỗi
                current_rsi = rsi.iloc[i]
                prev_rsi = rsi.iloc[i-1]
                current_close = data['Close'].iloc[i]
                prev_close = data['Close'].iloc[i-1]
                
                # Đơn giản hóa - chỉ kiểm tra xu hướng tăng
                if i >= 20:  # Cần ít nhất 20 điểm dữ liệu
                    # Lấy dữ liệu giá đóng cửa của 3 nến gần nhất
                    curr_price = float(data['Close'].iloc[i])
                    prev_price = float(data['Close'].iloc[i-1])
                    prev_prev_price = float(data['Close'].iloc[i-2])
                    
                    # Tính MA20
                    ma20 = float(data['Close'].iloc[i-20:i].mean())
                    
                    # Tín hiệu mua khi có xu hướng tăng rõ ràng và vượt MA20
                    xu_huong_tang = curr_price > prev_price > prev_prev_price
                    vuot_ma20 = prev_price <= ma20 and curr_price > ma20
                    
                    if xu_huong_tang and vuot_ma20:
                        # Tín hiệu mua
                        entry_date = data.index[i]
                        entry_price = current_close
                        
                        # Tính stop loss và take profit dựa trên ATR
                        entry_price_float = float(entry_price.iloc[0]) if hasattr(entry_price, 'iloc') else float(entry_price)
                        
                        current_atr = atr.iloc[i]
                        if not np.isnan(current_atr):
                            # Nếu đầy đủ dữ liệu ATR
                            atr_multiplier = risk_config["atr_settings"]["atr_multiplier"][risk_level]
                            tp_multiplier = risk_config["atr_settings"]["take_profit_atr_multiplier"][risk_level]
                            
                            stop_loss = entry_price_float - (current_atr * atr_multiplier)
                            take_profit = entry_price_float + (current_atr * tp_multiplier)
                        else:
                            # Nếu không có dữ liệu ATR, sử dụng % cố định
                            stop_loss = entry_price_float * 0.95  # 5% stop loss
                            take_profit = entry_price_float * 1.15  # 15% take profit
                        
                        # Tính kích thước vị thế
                        risk_amount = balance * (risk_params['risk_per_trade'] / 100)
                        risk_per_share = entry_price_float - stop_loss
                        position_size = risk_amount / risk_per_share
                        leverage = risk_params['max_leverage']
                        
                        logger.info(f"Tín hiệu LONG cho {symbol} tại {entry_date}, giá ${entry_price_float:.2f}")
                        logger.info(f"Stop Loss: ${stop_loss:.2f}, Take Profit: ${take_profit:.2f}")
                        logger.info(f"Kích thước vị thế: {position_size:.4f}, Đòn bẩy: {leverage}x")
                        
                        # Mô phỏng giao dịch
                        exit_date = None
                        exit_price = None
                        exit_reason = None
                        profit = 0
                        
                        # Kiểm tra kết quả sau khi vào lệnh
                        for j in range(i+1, len(data)):
                            curr_price_j = float(data['Close'].iloc[j])
                            
                            # Kiểm tra stop loss
                            if curr_price_j <= stop_loss:
                                exit_date = data.index[j]
                                exit_price = stop_loss
                                exit_reason = "stop_loss"
                                profit = (exit_price - entry_price_float) * position_size * leverage
                                break
                                
                            # Kiểm tra take profit  
                            if curr_price_j >= take_profit:
                                exit_date = data.index[j]
                                exit_price = take_profit
                                exit_reason = "take_profit"
                                profit = (exit_price - entry_price_float) * position_size * leverage
                                break
                        
                        # Nếu không chạm SL/TP thì tính đến điểm kết thúc backtest
                        if exit_date is None:
                            exit_date = data.index[-1]
                            exit_price_val = float(data['Close'].iloc[-1])
                            exit_reason = "end_of_test"
                            profit = (exit_price_val - entry_price_float) * position_size * leverage
                            exit_price = exit_price_val
                        
                        # Thêm vào danh sách giao dịch
                        # Đảm bảo exit_price là số thực để tránh lỗi khi tính toán
                        if isinstance(exit_price, (int, float)):
                            exit_price_float = float(exit_price)
                        else:
                            try:
                                exit_price_float = float(exit_price)
                            except (ValueError, TypeError):
                                exit_price_float = entry_price_float  # Mặc định trong trường hợp lỗi
                        
                        # Tính phần trăm lợi nhuận an toàn hơn
                        profit_pct = ((exit_price_float / entry_price_float) - 1) * 100 * leverage
                        
                        trade = {
                            "symbol": symbol,
                            "entry_date": entry_date,
                            "entry_price": entry_price_float,
                            "exit_date": exit_date,
                            "exit_price": exit_price_float,
                            "exit_reason": exit_reason,
                            "position_size": position_size,
                            "leverage": leverage,
                            "profit": profit,
                            "profit_pct": profit_pct
                        }
                        
                        symbol_trades.append(trade)
                        all_trades.append(trade)
                        
                        # Cập nhật số dư
                        balance += profit
                        
                        # Thống kê
                        total_trades += 1
                        if profit > 0:
                            winning_trades += 1
                        else:
                            losing_trades += 1
                        
                        logger.info(f"Kết quả: {exit_reason} tại {exit_date}, giá ${exit_price_float:.2f}")
                        logger.info(f"Lợi nhuận: ${profit:.2f} ({trade['profit_pct']:.2f}%)")
                        logger.info(f"Số dư mới: ${balance:.2f}")
                        
                        # Chỉ lấy tín hiệu đầu tiên cho mỗi symbol để đơn giản hóa
                        break
        
            # Lưu kết quả cho symbol
            if len(symbol_trades) > 0:
                symbol_profit = sum(trade["profit"] for trade in symbol_trades)
                symbol_win_rate = sum(1 for trade in symbol_trades if trade["profit"] > 0) / len(symbol_trades) * 100
                
                symbol_results[symbol] = {
                    "trades": len(symbol_trades),
                    "profit": symbol_profit,
                    "win_rate": symbol_win_rate
                }
                
                logger.info(f"Kết quả {symbol}: {len(symbol_trades)} giao dịch, Lợi nhuận: ${symbol_profit:.2f}, Tỷ lệ thắng: {symbol_win_rate:.2f}%")
            else:
                logger.info(f"Không tìm thấy tín hiệu giao dịch cho {symbol}")
                
        except Exception as e:
            logger.error(f"Lỗi khi backtest {symbol}: {e}")
    
    # Tổng kết toàn bộ backtest
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    profit = balance - initial_balance
    profit_pct = (balance / initial_balance - 1) * 100
    
    logger.info(f"\n=== KẾT QUẢ BACKTEST ===")
    logger.info(f"Số lượng giao dịch: {total_trades}")
    logger.info(f"Giao dịch thắng/thua: {winning_trades}/{losing_trades}")
    logger.info(f"Tỷ lệ thắng: {win_rate:.2f}%")
    logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
    logger.info(f"Số dư cuối cùng: ${balance:.2f}")
    logger.info(f"Tổng lợi nhuận: ${profit:.2f} ({profit_pct:.2f}%)")
    
    # Chi tiết từng symbol
    logger.info(f"\n=== CHI TIẾT TỪNG SYMBOL ===")
    for symbol, result in symbol_results.items():
        logger.info(f"{symbol}: {result['trades']} giao dịch, Lợi nhuận: ${result['profit']:.2f}, Tỷ lệ thắng: {result['win_rate']:.2f}%")
    
    return {
        "initial_balance": initial_balance,
        "final_balance": balance,
        "total_profit": profit,
        "total_profit_pct": profit_pct,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "symbol_results": symbol_results,
        "all_trades": all_trades
    }

def main():
    parser = argparse.ArgumentParser(description='Công cụ backtest đơn giản')
    parser.add_argument('--symbols', nargs='+', default=['BTC-USD', 'ETH-USD', 'SOL-USD'],
                        help='Danh sách các symbols cần test (e.g., BTC-USD ETH-USD)')
    parser.add_argument('--period', default='3mo', help='Khoảng thời gian (e.g., 1mo, 3mo, 6mo)')
    parser.add_argument('--timeframe', default='1d', help='Khung thời gian (e.g., 1d, 4h, 1h)')
    parser.add_argument('--balance', type=float, default=10000, help='Số dư ban đầu')
    
    args = parser.parse_args()
    
    run_backtest(
        symbols=args.symbols,
        period=args.period,
        timeframe=args.timeframe,
        initial_balance=args.balance
    )

if __name__ == "__main__":
    main()