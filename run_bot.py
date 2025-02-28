"""
Khởi chạy bot giao dịch sử dụng hệ thống giao dịch nâng cao
"""

import os
import sys
import argparse
import logging
import time
import json
from datetime import datetime
import pandas as pd
import numpy as np

from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.market_regime_detector import MarketRegimeDetector
from app.advanced_ml_optimizer import AdvancedMLOptimizer
from app.advanced_ml_strategy import AdvancedMLStrategy

from multi_timeframe_analyzer import MultiTimeframeAnalyzer
from composite_indicator import CompositeIndicator
from liquidity_analyzer import LiquidityAnalyzer
from advanced_trading_system import AdvancedTradingSystem
import visualization as vis

# Thiết lập logger
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.FileHandler("trading_bot.log"),
                       logging.StreamHandler()
                   ])
logger = logging.getLogger('trading_bot')

def check_api_keys():
    """Kiểm tra API keys có tồn tại không"""
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        logger.warning("Khóa API Binance chưa được cấu hình.")
        logger.warning("Bot sẽ chạy ở chế độ giả lập.")
        return False
    
    return True

def save_config(config, file_path="config.json"):
    """Lưu cấu hình vào file"""
    with open(file_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"Đã lưu cấu hình vào {file_path}")

def load_config(file_path="config.json"):
    """Tải cấu hình từ file"""
    if not os.path.exists(file_path):
        logger.warning(f"Không tìm thấy file cấu hình {file_path}")
        return None
    
    with open(file_path, 'r') as f:
        config = json.load(f)
    
    logger.info(f"Đã tải cấu hình từ {file_path}")
    return config

def run_simulation(config):
    """
    Chạy bot ở chế độ giả lập
    
    Args:
        config (dict): Cấu hình cho bot
    """
    logger.info("=== Khởi chạy bot ở chế độ giả lập ===")
    
    # Trích xuất cấu hình
    symbol = config.get('symbol', 'BTCUSDT')
    timeframe = config.get('timeframe', '1h')
    initial_balance = config.get('initial_balance', 10000.0)
    risk_percentage = config.get('risk_percentage', 1.0)
    check_interval = config.get('check_interval', 60)  # giây
    run_duration = config.get('run_duration', 3600)    # giây
    
    # Khởi tạo các thành phần
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Khởi tạo hệ thống giao dịch nâng cao
    trading_system = AdvancedTradingSystem(
        binance_api=binance_api,
        data_processor=data_processor,
        initial_balance=initial_balance,
        risk_percentage=risk_percentage,
        timeframes=[timeframe, '4h', '1d'] if timeframe not in ['4h', '1d'] else [timeframe, '1d']
    )
    
    # Lấy dữ liệu lịch sử
    historical_data = data_processor.get_historical_data(symbol, timeframe, lookback_days=30)
    if historical_data is None or len(historical_data) < 10:
        logger.error(f"Không thể lấy dữ liệu lịch sử cho {symbol}")
        return None
    
    logger.info(f"Đã tải {len(historical_data)} mẫu dữ liệu lịch sử")
    
    # Khởi tạo thời gian bắt đầu
    start_time = time.time()
    iteration = 0
    
    # Vòng lặp chính
    try:
        while time.time() - start_time < run_duration:
            iteration += 1
            logger.info(f"=== Vòng lặp {iteration} ===")
            
            # Phân tích thị trường
            analysis = trading_system.analyze_market(symbol, timeframe)
            
            if analysis:
                logger.info(f"Giá hiện tại: {analysis['current_price']:.2f}")
                
                # Hiển thị tín hiệu
                if 'signal' in analysis:
                    signal = analysis['signal']
                    confidence = analysis.get('confidence', 0)
                    logger.info(f"Tín hiệu: {signal} với độ tin cậy {confidence:.1f}%")
                else:
                    logger.info("Không có tín hiệu rõ ràng")
                
                # Hiển thị giai đoạn thị trường
                if 'market_regime' in analysis and analysis['market_regime']:
                    regime = analysis['market_regime'].get('regime')
                    logger.info(f"Giai đoạn thị trường: {regime}")
                
                # Hiển thị tóm tắt
                if 'summary' in analysis:
                    logger.info(f"Tóm tắt: {analysis['summary']}")
                
                # Kiểm tra xem có nên thực hiện giao dịch không
                if signal in ['BUY', 'SELL'] and confidence >= 70:
                    logger.info(f"Tín hiệu mạnh: {signal} với độ tin cậy {confidence:.1f}%")
                    
                    # Lấy thông tin quản lý rủi ro
                    risk_params = analysis.get('risk_management', {})
                    
                    # Thực hiện giao dịch
                    trade_id = trading_system.execute_trade(
                        symbol=symbol,
                        side=signal,
                        position_size=risk_params.get('position_size_pct', risk_percentage),
                        entry_price=analysis['current_price'],
                        leverage=config.get('leverage', 1),
                        risk_params=risk_params
                    )
                    
                    if trade_id:
                        logger.info(f"Đã thực hiện giao dịch {signal} {symbol}, ID: {trade_id}")
                    else:
                        logger.error(f"Không thể thực hiện giao dịch {signal} {symbol}")
            else:
                logger.error(f"Không thể phân tích thị trường cho {symbol}")
            
            # Cập nhật các vị thế đang mở
            current_price = binance_api.get_symbol_price(symbol)
            if current_price:
                closed_positions = trading_system.update_positions({symbol: current_price})
                
                if closed_positions:
                    logger.info(f"Đã đóng {len(closed_positions)} vị thế")
                    
                    # Hiển thị thông tin hiệu suất
                    performance = trading_system.get_performance_summary()
                    logger.info(f"Số dư hiện tại: ${performance['current_balance']:.2f}")
                    logger.info(f"Tổng lợi nhuận: {performance['profit_percent']:.2f}%")
                    logger.info(f"Tỷ lệ thắng: {performance['win_rate']:.2f}%")
            
            # In các vị thế đang mở
            active_positions = trading_system.get_active_positions()
            if active_positions:
                logger.info(f"Có {len(active_positions)} vị thế đang mở:")
                for pos in active_positions:
                    logger.info(f"  {pos['side']} {pos['symbol']} @ {pos['entry_price']:.2f}, "
                             f"TP: {pos['take_profit_price']:.2f}, SL: {pos['stop_loss_price']:.2f}")
            else:
                logger.info("Không có vị thế đang mở")
            
            # Chờ đến lần kiểm tra tiếp theo
            logger.info(f"Đang chờ {check_interval} giây đến lần kiểm tra tiếp theo...")
            time.sleep(check_interval)
    
    except KeyboardInterrupt:
        logger.info("Người dùng đã dừng bot")
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {e}", exc_info=True)
    finally:
        # Lưu trạng thái hệ thống
        trading_system.save_state("trading_state.json")
        
        # Hiển thị các vị thế đã đóng
        closed_positions = trading_system.get_closed_positions()
        if closed_positions:
            logger.info(f"Các vị thế đã đóng ({len(closed_positions)}):")
            for i, pos in enumerate(closed_positions[:5]):  # Chỉ hiển thị 5 vị thế gần nhất
                logger.info(f"  {i+1}. {pos['side']} {pos['symbol']} @ {pos['entry_price']:.2f} -> {pos['exit_price']:.2f}, "
                         f"PnL: {pos['pnl_percent']:.2f}%, Lý do: {pos['exit_reason']}")
        
        # Hiển thị hiệu suất tổng thể
        performance = trading_system.get_performance_summary()
        logger.info(f"=== Hiệu suất tổng thể ===")
        logger.info(f"Số dư cuối cùng: ${performance['current_balance']:.2f}")
        logger.info(f"Tổng lợi nhuận: {performance['profit_percent']:.2f}%")
        logger.info(f"Tỷ lệ thắng: {performance['win_rate']:.2f}%")
        logger.info(f"Hệ số lợi nhuận: {performance['profit_factor']:.2f}")
        logger.info(f"Drawdown tối đa: {performance['max_drawdown']:.2f}%")
        logger.info(f"Tổng số giao dịch: {performance['total_trades']}")
        
        # Tạo các biểu đồ để minh họa kết quả
        create_visualization(trading_system, symbol, timeframe, historical_data)
        
        return performance

def create_visualization(trading_system, symbol, timeframe, historical_data):
    """
    Tạo các biểu đồ để minh họa kết quả
    
    Args:
        trading_system (AdvancedTradingSystem): Hệ thống giao dịch
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        historical_data (pd.DataFrame): Dữ liệu lịch sử
    """
    logger.info("Đang tạo các biểu đồ...")
    
    # Tạo thư mục để lưu biểu đồ
    os.makedirs('charts', exist_ok=True)
    
    # Lấy các vị thế đã đóng
    closed_positions = trading_system.get_closed_positions()
    
    # Tạo biểu đồ giá và các giao dịch
    vis.plot_price_with_indicators(
        historical_data,
        indicators=['ema9', 'ema21', 'rsi', 'macd'],
        trades=closed_positions,
        title=f"{symbol} - {timeframe} Chart with Trades",
        save_path=f"charts/{symbol}_{timeframe}_chart.png"
    )
    
    # Tạo biểu đồ equity curve
    performance = trading_system.get_performance_summary()
    if 'equity_curve' in performance:
        vis.plot_equity_curve(
            performance['equity_curve'],
            trades=closed_positions,
            title=f"{symbol} - Equity Curve",
            save_path=f"charts/{symbol}_equity_curve.png"
        )
    
    # Tạo biểu đồ drawdown
    if 'equity_curve' in performance:
        vis.plot_drawdown_curve(
            performance['equity_curve'],
            title=f"{symbol} - Drawdown Analysis",
            save_path=f"charts/{symbol}_drawdown.png"
        )
    
    # Tạo biểu đồ phân phối giao dịch
    if closed_positions:
        vis.plot_trade_distribution(
            closed_positions,
            title=f"{symbol} - Trade Distribution",
            save_path=f"charts/{symbol}_trade_distribution.png"
        )
    
    logger.info("Đã tạo các biểu đồ trong thư mục 'charts'")

def run_live(config):
    """
    Chạy bot ở chế độ thực
    
    Args:
        config (dict): Cấu hình cho bot
    """
    logger.info("=== Khởi chạy bot ở chế độ thực ===")
    
    # Kiểm tra API keys
    has_api_keys = check_api_keys()
    if not has_api_keys:
        logger.error("Cần phải có API keys để chạy ở chế độ thực")
        return None
    
    # Thực hiện tương tự như chế độ giả lập nhưng với simulation_mode=False
    config_copy = config.copy()
    config_copy['simulation_mode'] = False
    
    return run_simulation(config_copy)

def run_backtest(config):
    """
    Chạy backtest
    
    Args:
        config (dict): Cấu hình cho bot
    """
    logger.info("=== Chạy backtest ===")
    
    # Trích xuất cấu hình
    symbol = config.get('symbol', 'BTCUSDT')
    timeframe = config.get('timeframe', '1h')
    initial_balance = config.get('initial_balance', 10000.0)
    risk_percentage = config.get('risk_percentage', 1.0)
    days = config.get('backtest_days', 30)
    
    # Khởi tạo các thành phần
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Lấy dữ liệu lịch sử
    df = data_processor.get_historical_data(symbol, timeframe, lookback_days=days)
    if df is None or len(df) < 10:
        logger.error(f"Không thể lấy dữ liệu lịch sử cho {symbol}")
        return None
    
    logger.info(f"Đã tải {len(df)} mẫu dữ liệu lịch sử")
    
    # Khởi tạo hệ thống giao dịch nâng cao
    trading_system = AdvancedTradingSystem(
        binance_api=binance_api,
        data_processor=data_processor,
        initial_balance=initial_balance,
        risk_percentage=risk_percentage,
        timeframes=[timeframe, '4h', '1d'] if timeframe not in ['4h', '1d'] else [timeframe, '1d']
    )
    
    # Chạy backtest
    balance = initial_balance
    position = None
    trades = []
    equity_curve = [balance]
    
    for i in range(30, len(df)):  # Bắt đầu từ bar thứ 30 để có đủ dữ liệu lịch sử
        # Lấy phân tích thị trường tại thời điểm hiện tại
        current_df = df.iloc[:i+1].copy()
        
        # Gán dữ liệu hiện tại vào data_processor để phân tích
        data_processor._latest_data = {f"{symbol}_{timeframe}": current_df}
        
        # Phân tích thị trường
        analysis = trading_system.analyze_market(symbol, timeframe)
        
        current_price = df['close'].iloc[i]
        current_signal = 0
        
        if analysis and 'signal' in analysis:
            if analysis['signal'] == 'BUY':
                current_signal = 1
            elif analysis['signal'] == 'SELL':
                current_signal = -1
        
        # Nếu không có vị thế và có tín hiệu
        if position is None and current_signal != 0:
            # Tạo vị thế mới
            side = "BUY" if current_signal == 1 else "SELL"
            
            # Lấy các tham số quản lý rủi ro từ phân tích
            risk_params = analysis.get('risk_management', {})
            position_size = risk_params.get('position_size_pct', 1.0)
            
            # Tính số lượng dựa trên kích thước vị thế
            position_value = balance * (position_size / 100)
            quantity = position_value / current_price
            
            position = {
                'side': side,
                'entry_price': current_price,
                'quantity': quantity,
                'entry_time': df.index[i],
                'take_profit_pct': risk_params.get('take_profit_pct', 2.0),
                'stop_loss_pct': risk_params.get('stop_loss_pct', 1.0),
                'trailing_stop': risk_params.get('trailing_stop', False),
                'highest_price': current_price if side == "BUY" else None,
                'lowest_price': current_price if side == "SELL" else None
            }
            
            # Tính giá chốt lời và cắt lỗ
            if side == "BUY":
                position['take_profit_price'] = current_price * (1 + position['take_profit_pct'] / 100)
                position['stop_loss_price'] = current_price * (1 - position['stop_loss_pct'] / 100)
            else:
                position['take_profit_price'] = current_price * (1 - position['take_profit_pct'] / 100)
                position['stop_loss_price'] = current_price * (1 + position['stop_loss_pct'] / 100)
            
            logger.info(f"Mở vị thế {side} tại {current_price:.2f} ({df.index[i]})")
        
        # Nếu có vị thế, cập nhật và kiểm tra các điều kiện đóng vị thế
        elif position is not None:
            # Cập nhật giá cao nhất/thấp nhất
            if position['side'] == "BUY":
                position['highest_price'] = max(position['highest_price'], current_price)
            else:
                position['lowest_price'] = min(position['lowest_price'], current_price)
            
            # Kiểm tra trailing stop
            trailing_stop_hit = False
            if position['trailing_stop'] and 'trailing_stop_price' in position:
                if (position['side'] == "BUY" and current_price < position['trailing_stop_price']) or \
                   (position['side'] == "SELL" and current_price > position['trailing_stop_price']):
                    trailing_stop_hit = True
            
            # Cập nhật trailing stop nếu cần
            if position['trailing_stop'] and position['side'] == "BUY" and position['highest_price'] > position['entry_price'] * 1.01:
                # Kích hoạt trailing stop khi giá tăng 1%
                trailing_callback = position['stop_loss_pct'] * 0.5
                position['trailing_stop_price'] = position['highest_price'] * (1 - trailing_callback / 100)
            
            elif position['trailing_stop'] and position['side'] == "SELL" and position['lowest_price'] < position['entry_price'] * 0.99:
                # Kích hoạt trailing stop khi giá giảm 1%
                trailing_callback = position['stop_loss_pct'] * 0.5
                position['trailing_stop_price'] = position['lowest_price'] * (1 + trailing_callback / 100)
            
            # Kiểm tra các điều kiện đóng vị thế
            close_position = False
            exit_reason = None
            
            if trailing_stop_hit:
                close_position = True
                exit_reason = "Trailing Stop"
            elif (position['side'] == "BUY" and current_price >= position['take_profit_price']) or \
                 (position['side'] == "SELL" and current_price <= position['take_profit_price']):
                close_position = True
                exit_reason = "Take Profit"
            elif (position['side'] == "BUY" and current_price <= position['stop_loss_price']) or \
                 (position['side'] == "SELL" and current_price >= position['stop_loss_price']):
                close_position = True
                exit_reason = "Stop Loss"
            elif (position['side'] == "BUY" and current_signal == -1) or \
                 (position['side'] == "SELL" and current_signal == 1):
                close_position = True
                exit_reason = "Signal Reversed"
            
            # Đóng vị thế
            if close_position:
                # Tính lãi/lỗ
                if position['side'] == "BUY":
                    pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
                else:
                    pnl = (position['entry_price'] - current_price) / position['entry_price'] * 100
                
                balance = balance * (1 + pnl / 100)
                
                # Lưu thông tin giao dịch
                trade = position.copy()
                trade['exit_price'] = current_price
                trade['exit_time'] = df.index[i]
                trade['exit_reason'] = exit_reason
                trade['pnl'] = pnl
                trade['exit_index'] = i
                trades.append(trade)
                
                logger.info(f"Đóng vị thế tại {current_price:.2f} ({df.index[i]}), Lý do: {exit_reason}, PnL: {pnl:.2f}%")
                
                # Reset vị thế
                position = None
        
        # Cập nhật equity curve
        if position is None:
            equity_curve.append(balance)
        else:
            # Tính lãi/lỗ chưa thực hiện
            if position['side'] == "BUY":
                unrealized_pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
            else:
                unrealized_pnl = (position['entry_price'] - current_price) / position['entry_price'] * 100
            
            equity_curve.append(balance * (1 + unrealized_pnl / 100))
    
    # Đóng vị thế nếu còn mở ở cuối backtest
    if position is not None:
        current_price = df['close'].iloc[-1]
        
        # Tính lãi/lỗ
        if position['side'] == "BUY":
            pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
        else:
            pnl = (position['entry_price'] - current_price) / position['entry_price'] * 100
        
        balance = balance * (1 + pnl / 100)
        
        # Lưu thông tin giao dịch
        trade = position.copy()
        trade['exit_price'] = current_price
        trade['exit_time'] = df.index[-1]
        trade['exit_reason'] = "End of Backtest"
        trade['pnl'] = pnl
        trade['exit_index'] = len(df) - 1
        trades.append(trade)
        
        logger.info(f"Đóng vị thế cuối cùng tại {current_price:.2f}, PnL: {pnl:.2f}%")
        
        # Cập nhật equity curve
        equity_curve[-1] = balance
    
    # Tính toán các chỉ số hiệu suất
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]
    
    win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
    total_profit = sum([t['pnl'] for t in winning_trades]) if winning_trades else 0
    total_loss = sum([t['pnl'] for t in losing_trades]) if losing_trades else 0
    
    profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
    
    # Tính drawdown
    max_equity = equity_curve[0]
    max_drawdown = 0
    
    for equity in equity_curve:
        max_equity = max(max_equity, equity)
        drawdown = (max_equity - equity) / max_equity * 100
        max_drawdown = max(max_drawdown, drawdown)
    
    # Kết quả
    performance = {
        'initial_balance': initial_balance,
        'final_balance': balance,
        'total_return': (balance - initial_balance) / initial_balance * 100,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'total_trades': len(trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'equity_curve': equity_curve
    }
    
    # In kết quả
    logger.info("=== Kết quả Backtest ===")
    logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
    logger.info(f"Số dư cuối cùng: ${balance:.2f}")
    logger.info(f"Tổng lợi nhuận: {performance['total_return']:.2f}%")
    logger.info(f"Tỷ lệ thắng: {win_rate:.2f}%")
    logger.info(f"Hệ số lợi nhuận: {profit_factor:.2f}")
    logger.info(f"Drawdown tối đa: {max_drawdown:.2f}%")
    logger.info(f"Tổng số giao dịch: {len(trades)}")
    
    # Tạo biểu đồ
    os.makedirs('backtest_charts', exist_ok=True)
    
    # Vẽ biểu đồ giá và các giao dịch
    vis.plot_price_with_indicators(
        df,
        indicators=['ema9', 'ema21', 'rsi', 'macd'],
        trades=trades,
        title=f"{symbol} - {timeframe} Backtest Chart",
        save_path=f"backtest_charts/{symbol}_{timeframe}_backtest_chart.png"
    )
    
    # Vẽ biểu đồ equity curve
    vis.plot_equity_curve(
        equity_curve,
        trades=trades,
        title=f"{symbol} - Backtest Equity Curve",
        save_path=f"backtest_charts/{symbol}_{timeframe}_backtest_equity.png"
    )
    
    # Vẽ biểu đồ drawdown
    vis.plot_drawdown_curve(
        equity_curve,
        title=f"{symbol} - Backtest Drawdown Analysis",
        save_path=f"backtest_charts/{symbol}_{timeframe}_backtest_drawdown.png"
    )
    
    # Vẽ biểu đồ phân phối giao dịch
    vis.plot_trade_distribution(
        trades,
        title=f"{symbol} - Backtest Trade Distribution",
        save_path=f"backtest_charts/{symbol}_{timeframe}_backtest_distribution.png"
    )
    
    logger.info("Đã tạo các biểu đồ phân tích trong thư mục 'backtest_charts'")
    
    # Lưu kết quả
    backtest_results = {
        'symbol': symbol,
        'timeframe': timeframe,
        'initial_balance': initial_balance,
        'risk_percentage': risk_percentage,
        'days': days,
        'performance': performance,
        'trades': []
    }
    
    # Chuyển đổi datetime thành string để lưu vào JSON
    for trade in trades:
        trade_copy = trade.copy()
        # Kiểm tra xem giá trị có phải là datetime không
        if hasattr(trade_copy['entry_time'], 'strftime'):
            trade_copy['entry_time'] = trade_copy['entry_time'].strftime('%Y-%m-%d %H:%M:%S')
        if hasattr(trade_copy['exit_time'], 'strftime'):
            trade_copy['exit_time'] = trade_copy['exit_time'].strftime('%Y-%m-%d %H:%M:%S')
        backtest_results['trades'].append(trade_copy)
    
    with open(f"backtest_results_{symbol}_{timeframe}.json", 'w') as f:
        json.dump(backtest_results, f, indent=2)
    
    logger.info(f"Đã lưu kết quả backtest vào backtest_results_{symbol}_{timeframe}.json")
    
    return performance

def create_default_config():
    """Tạo cấu hình mặc định"""
    config = {
        'symbol': 'BTCUSDT',
        'timeframe': '1h',
        'initial_balance': 10000.0,
        'risk_percentage': 1.0,
        'leverage': 1,
        'check_interval': 60,      # giây
        'run_duration': 3600,      # giây
        'backtest_days': 30,
        'simulation_mode': True    # Mặc định chạy ở chế độ giả lập
    }
    
    return config

def parse_arguments():
    """Phân tích đối số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Bot giao dịch tiên tiến')
    
    parser.add_argument('--mode', type=str, choices=['sim', 'live', 'backtest'], 
                       default='sim', help='Chế độ chạy (sim, live, backtest)')
    
    parser.add_argument('--symbol', type=str, default='BTCUSDT', 
                       help='Mã cặp giao dịch (mặc định: BTCUSDT)')
    
    parser.add_argument('--timeframe', type=str, default='1h', 
                       help='Khung thời gian (mặc định: 1h)')
    
    parser.add_argument('--balance', type=float, default=10000.0, 
                       help='Số dư ban đầu (mặc định: 10000.0)')
    
    parser.add_argument('--risk', type=float, default=1.0, 
                       help='Phần trăm rủi ro (mặc định: 1.0)')
    
    parser.add_argument('--leverage', type=int, default=1, 
                       help='Đòn bẩy (mặc định: 1)')
    
    parser.add_argument('--interval', type=int, default=60, 
                       help='Khoảng thời gian kiểm tra (giây) (mặc định: 60)')
    
    parser.add_argument('--duration', type=int, default=3600, 
                       help='Thời gian chạy (giây) (mặc định: 3600)')
    
    parser.add_argument('--days', type=int, default=30, 
                       help='Số ngày dữ liệu lịch sử cho backtest (mặc định: 30)')
    
    parser.add_argument('--config', type=str, default='config.json', 
                       help='Đường dẫn đến file cấu hình (mặc định: config.json)')
    
    parser.add_argument('--save-config', action='store_true', 
                       help='Lưu cấu hình vào file')
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    # Phân tích đối số dòng lệnh
    args = parse_arguments()
    
    # Tạo cấu hình mặc định
    config = create_default_config()
    
    # Tải cấu hình từ file (nếu có)
    config_file = args.config
    loaded_config = load_config(config_file)
    
    if loaded_config:
        config.update(loaded_config)
    
    # Cập nhật cấu hình từ đối số dòng lệnh
    config['symbol'] = args.symbol
    config['timeframe'] = args.timeframe
    config['initial_balance'] = args.balance
    config['risk_percentage'] = args.risk
    config['leverage'] = args.leverage
    config['check_interval'] = args.interval
    config['run_duration'] = args.duration
    config['backtest_days'] = args.days
    
    # Lưu cấu hình (nếu được yêu cầu)
    if args.save_config:
        save_config(config, config_file)
    
    # Chạy bot theo chế độ được chỉ định
    if args.mode == 'sim':
        run_simulation(config)
    elif args.mode == 'live':
        run_live(config)
    elif args.mode == 'backtest':
        run_backtest(config)
    else:
        logger.error(f"Chế độ không hợp lệ: {args.mode}")

if __name__ == "__main__":
    main()