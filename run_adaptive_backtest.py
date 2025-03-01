#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script thực thi backtest với hệ thống thích ứng thông minh

Script này thực hiện backtest với hệ thống giao dịch thích ứng theo chế độ thị trường
và tự động chọn chiến lược tối ưu dựa trên điều kiện hiện tại.
"""

import os
import sys
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import argparse

# Import hệ thống thích ứng
from market_regime_ml_optimized import (
    MarketRegimeDetector,
    StrategySelector,
    AdaptiveTrader,
    load_data,
    find_data_files
)

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quick_backtest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Thư mục dữ liệu và kết quả
DATA_DIR = 'test_data'
RESULT_DIR = 'backtest_results'
CHART_DIR = 'backtest_charts'

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

def create_sample_data(symbol='BTCUSDT', interval='1h', days=180, filename=None):
    """
    Tạo dữ liệu mẫu chân thực
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        days (int): Số ngày dữ liệu
        filename (str): Tên file lưu dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu
    """
    from datetime import datetime, timedelta
    
    if filename is None:
        filename = f"{DATA_DIR}/{symbol}_{interval}_sample.csv"
    
    # Kiểm tra xem file đã tồn tại chưa
    if os.path.exists(filename):
        logger.info(f"Đã tìm thấy dữ liệu mẫu tại {filename}")
        return pd.read_csv(filename)
    
    # Tạo dữ liệu mẫu
    logger.info(f"Tạo dữ liệu mẫu cho {symbol} {interval}...")
    
    # Tham số ban đầu
    initial_price = 40000.0  # BTC giá ban đầu
    rows = days * 24 if interval == '1h' else days  # số dòng dữ liệu
    
    # Dữ liệu thời gian
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = [start_date + timedelta(hours=i) if interval == '1h' else start_date + timedelta(days=i) 
             for i in range(rows)]
    
    # Tạo giá ngẫu nhiên với xu hướng
    price = initial_price
    prices = []
    volumes = []
    
    # Tạo các giai đoạn thị trường khác nhau
    phases = [
        {'type': 'ranging', 'length': rows // 6, 'volatility': 0.01, 'trend': 0.0},
        {'type': 'trending_up', 'length': rows // 6, 'volatility': 0.015, 'trend': 0.003},
        {'type': 'volatile', 'length': rows // 12, 'volatility': 0.03, 'trend': -0.001},
        {'type': 'trending_down', 'length': rows // 6, 'volatility': 0.015, 'trend': -0.003},
        {'type': 'ranging', 'length': rows // 6, 'volatility': 0.01, 'trend': 0.0},
        {'type': 'trending_up', 'length': rows // 6, 'volatility': 0.015, 'trend': 0.003},
        {'type': 'quiet', 'length': rows // 12, 'volatility': 0.005, 'trend': 0.0},
    ]
    
    # Tạo dữ liệu cho từng giai đoạn
    current_idx = 0
    for phase in phases:
        phase_end = min(current_idx + phase['length'], rows)
        
        while current_idx < phase_end:
            # Thêm xu hướng và biến động
            price = price * (1 + phase['trend'] + np.random.normal(0, phase['volatility']))
            prices.append(price)
            
            # Tạo khối lượng tương ứng
            if phase['type'] == 'volatile':
                volume = np.random.gamma(2.0, 1000) * 5  # Khối lượng cao trong giai đoạn biến động
            elif phase['type'] == 'trending_up' or phase['type'] == 'trending_down':
                volume = np.random.gamma(2.0, 1000) * 3  # Khối lượng trung bình trong xu hướng
            else:
                volume = np.random.gamma(2.0, 1000)  # Khối lượng thấp trong giai đoạn yên tĩnh
            
            volumes.append(volume)
            current_idx += 1
    
    # Tạo dữ liệu OHLCV
    data = []
    
    for i in range(len(prices)):
        # Tạo giá trong nến
        if i > 0:
            open_price = prices[i-1]  # Mở cửa bằng giá đóng cửa trước đó
        else:
            open_price = prices[i] * (1 - np.random.random() * 0.01)  # Ngẫu nhiên cho nến đầu tiên
            
        close_price = prices[i]
        
        # Xác định nến tăng hay giảm
        if close_price > open_price:
            high_price = open_price * (1 + np.random.random() * 0.015)  # Thêm tối đa 1.5%
            high_price = max(high_price, close_price)
            low_price = open_price * (1 - np.random.random() * 0.005)  # Giảm tối đa 0.5%
            low_price = min(low_price, close_price)
        else:
            high_price = open_price * (1 + np.random.random() * 0.005)  # Thêm tối đa 0.5%
            high_price = max(high_price, close_price)
            low_price = open_price * (1 - np.random.random() * 0.015)  # Giảm tối đa 1.5%
            low_price = min(low_price, close_price)
        
        # Thêm dòng dữ liệu
        data.append({
            'timestamp': dates[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volumes[i]
        })
    
    # Tạo DataFrame
    df = pd.DataFrame(data)
    
    # Lưu dữ liệu
    df.to_csv(filename, index=False)
    logger.info(f"Đã tạo và lưu dữ liệu mẫu tại {filename}")
    
    return df

def run_backtest(symbol='BTCUSDT', interval='1h', 
                initial_balance=10000.0, leverage=5,
                use_sample_data=True, max_days=90):
    """
    Chạy backtest với hệ thống thích ứng
    
    Args:
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        use_sample_data (bool): Sử dụng dữ liệu mẫu hay dữ liệu thật
        max_days (int): Số ngày tối đa nếu tạo dữ liệu mẫu
        
    Returns:
        Dict: Kết quả backtest
    """
    # Tìm hoặc tạo dữ liệu
    data_file = None
    if use_sample_data:
        # Tạo dữ liệu mẫu
        df = create_sample_data(symbol, interval, max_days)
    else:
        # Tìm dữ liệu thực
        data_files = find_data_files(DATA_DIR, f"{symbol}_{interval}*.csv")
        
        if data_files:
            data_file = data_files[0]
            logger.info(f"Sử dụng dữ liệu từ {data_file}")
            df = load_data(data_file)
        else:
            logger.warning(f"Không tìm thấy dữ liệu thực cho {symbol} {interval}, chuyển sang dữ liệu mẫu")
            df = create_sample_data(symbol, interval, max_days)
    
    if df is None or len(df) < 100:
        logger.error("Không đủ dữ liệu để backtest")
        return None
    
    # Khởi tạo bộ phát hiện chế độ thị trường
    detector = MarketRegimeDetector(use_ml=False)
    
    # Khởi tạo bộ chọn chiến lược
    selector = StrategySelector()
    
    # Khởi tạo hệ thống giao dịch thích ứng
    trader = AdaptiveTrader(detector, selector)
    
    # Chạy backtest
    result = trader.backtest(df, initial_balance=initial_balance, leverage=leverage)
    
    # Tạo tên kết quả
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_file = f"{RESULT_DIR}/adaptive_backtest_{symbol}_{interval}_{timestamp}.json"
    
    # Đảm bảo thư mục tồn tại
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    # Lưu kết quả
    with open(result_file, 'w') as f:
        # Xử lý các đối tượng datetime và numpy types
        serializable_result = {}
        
        # Xử lý từng phần tử để đảm bảo có thể serializable
        for key, value in result.items():
            if key == 'trades':
                serializable_result[key] = []
                for trade in value:
                    serializable_trade = {}
                    for trade_key, trade_value in trade.items():
                        # Xử lý datetime
                        if hasattr(trade_value, 'strftime'):
                            serializable_trade[trade_key] = trade_value.strftime('%Y-%m-%d %H:%M:%S')
                        # Xử lý numpy types
                        elif isinstance(trade_value, (np.integer, np.floating)):
                            serializable_trade[trade_key] = float(trade_value)
                        else:
                            serializable_trade[trade_key] = trade_value
                    serializable_result[key].append(serializable_trade)
            elif key == 'equity_curve':
                serializable_result[key] = [float(x) if isinstance(x, (np.integer, np.floating)) else x for x in value]
            elif key == 'dates':
                serializable_result[key] = [d.strftime('%Y-%m-%d %H:%M:%S') if hasattr(d, 'strftime') else str(d) for d in value]
            elif key == 'regime_changes':
                serializable_result[key] = []
                for change in value:
                    serializable_change = {}
                    for change_key, change_value in change.items():
                        if hasattr(change_value, 'strftime'):
                            serializable_change[change_key] = change_value.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(change_value, (np.integer, np.floating)):
                            serializable_change[change_key] = float(change_value)
                        else:
                            serializable_change[change_key] = change_value
                    serializable_result[key].append(serializable_change)
            elif key == 'regime_performance' or key == 'metrics' or key == 'regime_distribution':
                # Xử lý dictionaries nested
                serializable_result[key] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        serializable_result[key][sub_key] = {}
                        for sub_sub_key, sub_sub_value in sub_value.items():
                            if isinstance(sub_sub_value, (np.integer, np.floating)):
                                serializable_result[key][sub_key][sub_sub_key] = float(sub_sub_value)
                            else:
                                serializable_result[key][sub_key][sub_sub_key] = sub_sub_value
                    elif isinstance(sub_value, (np.integer, np.floating)):
                        serializable_result[key][sub_key] = float(sub_value)
                    else:
                        serializable_result[key][sub_key] = sub_value
            elif isinstance(value, (np.integer, np.floating)):
                # Xử lý numpy types
                serializable_result[key] = float(value)
            else:
                # Loại dữ liệu khác
                serializable_result[key] = value
        
        json.dump(serializable_result, f, indent=4)
    
    logger.info(f"Đã lưu kết quả backtest tại: {result_file}")
    
    # Lưu trades vào CSV
    if result['trades']:
        csv_file = result_file.replace('.json', '_trades.csv')
        pd.DataFrame(serializable_result['trades']).to_csv(csv_file, index=False)
        logger.info(f"Đã lưu chi tiết giao dịch tại: {csv_file}")
    
    # Tạo báo cáo tổng hợp
    create_summary_report(result, f"{CHART_DIR}/adaptive_summary_{symbol}_{interval}_{timestamp}")
    
    return result

def create_summary_report(result, base_filename):
    """
    Tạo báo cáo tổng hợp từ kết quả backtest
    
    Args:
        result (Dict): Kết quả backtest
        base_filename (str): Tên file cơ sở cho báo cáo
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs(os.path.dirname(base_filename), exist_ok=True)
    
    # 1. Tạo biểu đồ đường cong vốn
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(result['equity_curve'])), result['equity_curve'], label='Portfolio Value')
    
    # Thêm đánh dấu về giai đoạn thị trường
    regime_colors = {
        'trending_up': 'green',
        'trending_down': 'red',
        'ranging': 'orange',
        'volatile': 'purple',
        'quiet': 'gray'
    }
    
    # Xác định các vị trí của thay đổi chế độ
    for i, change in enumerate(result['regime_changes']):
        idx = result['dates'].index(change['timestamp']) if isinstance(change['timestamp'], str) else 0
        plt.axvline(x=idx, color=regime_colors.get(change['new_regime'], 'black'), linestyle='--', alpha=0.5)
        
        # Thêm nhãn
        if i % 2 == 0:  # Chỉ hiển thị một nửa nhãn để tránh quá tải
            plt.text(idx, result['equity_curve'][idx], 
                   change['new_regime'], 
                   rotation=90, color=regime_colors.get(change['new_regime'], 'black'), alpha=0.7)
    
    # Hoàn thiện biểu đồ
    plt.title('Equity Curve with Market Regimes')
    plt.xlabel('Time')
    plt.ylabel('Portfolio Value')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Lưu biểu đồ
    equity_chart = f"{base_filename}_equity.png"
    plt.savefig(equity_chart)
    plt.close()
    
    # 2. Tạo biểu đồ tròn về phân phối chế độ thị trường
    plt.figure(figsize=(8, 8))
    
    # Vẽ biểu đồ tròn
    regimes = []
    values = []
    colors = []
    
    for regime, pct in result['regime_distribution'].items():
        if pct > 0:
            regimes.append(regime)
            values.append(pct)
            colors.append(regime_colors.get(regime, 'gray'))
    
    plt.pie(values, labels=regimes, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.title('Market Regime Distribution')
    
    # Lưu biểu đồ
    pie_chart = f"{base_filename}_regimes_pie.png"
    plt.savefig(pie_chart)
    plt.close()
    
    # 3. Tạo biểu đồ hiệu suất theo chế độ thị trường
    plt.figure(figsize=(10, 6))
    
    # Chuẩn bị dữ liệu
    win_rates = []
    trade_counts = []
    regimes = []
    colors = []
    
    for regime, perf in result['regime_performance'].items():
        regimes.append(regime)
        win_rates.append(perf['win_rate'] * 100)
        trade_counts.append(perf['total_trades'])
        colors.append(regime_colors.get(regime, 'gray'))
    
    # Vẽ biểu đồ cột
    bars = plt.bar(regimes, win_rates, color=colors)
    
    # Thêm số lượng giao dịch
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1, 
               f'n={trade_counts[i]}', 
               ha='center', va='bottom')
    
    # Hoàn thiện biểu đồ
    plt.title('Win Rate by Market Regime')
    plt.xlabel('Market Regime')
    plt.ylabel('Win Rate (%)')
    plt.grid(axis='y', alpha=0.3)
    plt.ylim(0, 100)
    
    # Lưu biểu đồ
    regime_chart = f"{base_filename}_win_rates.png"
    plt.savefig(regime_chart)
    plt.close()
    
    # 4. Tạo biểu đồ thống kê chiến lược
    plt.figure(figsize=(10, 6))
    
    # Chuẩn bị dữ liệu
    strategies = []
    usage_counts = []
    
    for strat_name, count in result['strategy_uses'].items():
        if count > 0:
            strategies.append(strat_name)
            usage_counts.append(count)
    
    # Vẽ biểu đồ cột
    plt.bar(strategies, usage_counts)
    
    # Hoàn thiện biểu đồ
    plt.title('Strategy Usage')
    plt.xlabel('Strategy')
    plt.ylabel('Usage Count')
    plt.grid(axis='y', alpha=0.3)
    
    # Lưu biểu đồ
    strat_chart = f"{base_filename}_strategies.png"
    plt.savefig(strat_chart)
    plt.close()
    
    # 5. Tạo báo cáo HTML tổng hợp
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Adaptive Trading System Backtest Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            .metrics {{ display: flex; flex-wrap: wrap; margin-bottom: 20px; }}
            .metric-box {{ 
                background-color: #f5f5f5; 
                border-radius: 5px; 
                padding: 15px; 
                margin: 10px; 
                min-width: 200px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metric-title {{ font-weight: bold; margin-bottom: 5px; color: #555; }}
            .metric-value {{ font-size: 24px; }}
            .positive {{ color: green; }}
            .negative {{ color: red; }}
            .chart-container {{ margin: 20px 0; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1>Adaptive Trading System Backtest Results</h1>
        <p>Timeframe: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="metrics">
            <div class="metric-box">
                <div class="metric-title">Initial Balance</div>
                <div class="metric-value">${result['initial_balance']:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Final Balance</div>
                <div class="metric-value">${result['final_balance']:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Total ROI</div>
                <div class="metric-value {'positive' if result['metrics']['total_roi'] >= 0 else 'negative'}">{result['metrics']['total_roi']:.2f}%</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Win Rate</div>
                <div class="metric-value">{result['metrics']['win_rate']*100:.2f}%</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Total Trades</div>
                <div class="metric-value">{result['metrics']['total_trades']}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Max Drawdown</div>
                <div class="metric-value negative">{result['metrics']['max_drawdown']:.2f}%</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Profit Factor</div>
                <div class="metric-value">{result['metrics']['profit_factor']:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Sharpe Ratio</div>
                <div class="metric-value">{result['metrics']['sharpe_ratio']:.2f}</div>
            </div>
        </div>
        
        <h2>Equity Curve</h2>
        <div class="chart-container">
            <img src="{os.path.basename(equity_chart)}" alt="Equity Curve" style="width:100%">
        </div>
        
        <h2>Market Regime Distribution</h2>
        <div class="chart-container">
            <img src="{os.path.basename(pie_chart)}" alt="Market Regime Distribution" style="width:100%">
        </div>
        
        <h2>Performance by Market Regime</h2>
        <div class="chart-container">
            <img src="{os.path.basename(regime_chart)}" alt="Win Rate by Market Regime" style="width:100%">
        </div>
        
        <h2>Strategy Usage</h2>
        <div class="chart-container">
            <img src="{os.path.basename(strat_chart)}" alt="Strategy Usage" style="width:100%">
        </div>
        
        <h2>Regime Performance Details</h2>
        <table>
            <tr>
                <th>Regime</th>
                <th>Win Rate</th>
                <th>Trades</th>
                <th>Total PnL</th>
                <th>Avg PnL</th>
            </tr>
    """
    
    for regime, perf in result['regime_performance'].items():
        html_content += f"""
            <tr>
                <td>{regime}</td>
                <td>{perf['win_rate']*100:.2f}%</td>
                <td>{perf['total_trades']}</td>
                <td class="{'positive' if perf['total_pnl'] >= 0 else 'negative'}">${perf['total_pnl']:.2f}</td>
                <td class="{'positive' if perf['avg_pnl'] >= 0 else 'negative'}">${perf['avg_pnl']:.2f}</td>
            </tr>
        """
    
    html_content += """
        </table>
        
        <h2>Recent Trades</h2>
        <table>
            <tr>
                <th>Entry Date</th>
                <th>Exit Date</th>
                <th>Side</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>PnL</th>
                <th>ROI</th>
                <th>Regime</th>
                <th>Exit Reason</th>
            </tr>
    """
    
    # Thêm 20 giao dịch gần nhất
    for trade in result['trades'][-20:]:
        html_content += f"""
            <tr>
                <td>{trade['entry_date']}</td>
                <td>{trade['exit_date']}</td>
                <td>{trade['side']}</td>
                <td>${trade['entry_price']:.2f}</td>
                <td>${trade['exit_price']:.2f}</td>
                <td class="{'positive' if trade['pnl'] >= 0 else 'negative'}">${trade['pnl']:.2f}</td>
                <td class="{'positive' if trade['roi'] >= 0 else 'negative'}">{trade['roi']:.2f}%</td>
                <td>{trade['regime']}</td>
                <td>{trade['exit_reason']}</td>
            </tr>
        """
    
    html_content += """
        </table>
    </body>
    </html>
    """
    
    # Lưu báo cáo HTML
    html_file = f"{base_filename}_report.html"
    with open(html_file, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Đã tạo báo cáo tổng hợp tại: {html_file}")
    
    return html_file

def main():
    """Hàm chính để thực thi script"""
    # Phân tích tham số dòng lệnh
    parser = argparse.ArgumentParser(description='Chạy backtest với hệ thống giao dịch thích ứng')
    parser.add_argument('--symbol', type=str, default='BTCUSDT',
                      help='Cặp giao dịch (mặc định: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h',
                      help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--balance', type=float, default=10000.0,
                      help='Số dư ban đầu (mặc định: 10000.0)')
    parser.add_argument('--leverage', type=int, default=5,
                      help='Đòn bẩy (mặc định: 5)')
    parser.add_argument('--use-sample-data', action='store_true',
                      help='Sử dụng dữ liệu mẫu thay vì dữ liệu thực')
    parser.add_argument('--days', type=int, default=90,
                      help='Số ngày dữ liệu mẫu (mặc định: 90)')
    
    args = parser.parse_args()
    
    # Chạy backtest
    result = run_backtest(
        symbol=args.symbol,
        interval=args.interval,
        initial_balance=args.balance,
        leverage=args.leverage,
        use_sample_data=args.use_sample_data,
        max_days=args.days
    )
    
    if result:
        # In kết quả tóm tắt
        logger.info("===== KẾT QUẢ BACKTEST =====")
        logger.info(f"Số dư ban đầu: ${result['initial_balance']:.2f}")
        logger.info(f"Số dư cuối: ${result['final_balance']:.2f}")
        logger.info(f"ROI: {result['metrics']['total_roi']:.2f}%")
        logger.info(f"Tổng số giao dịch: {result['metrics']['total_trades']}")
        logger.info(f"Tỷ lệ thắng: {result['metrics']['win_rate']*100:.2f}%")
        logger.info(f"Drawdown tối đa: {result['metrics']['max_drawdown']:.2f}%")
        logger.info(f"Profit factor: {result['metrics']['profit_factor']:.2f}")
        logger.info(f"Sharpe ratio: {result['metrics']['sharpe_ratio']:.2f}")
        
        # Hiệu suất theo chế độ thị trường
        logger.info("\n==== HIỆU SUẤT THEO CHẾ ĐỘ THỊ TRƯỜNG ====")
        for regime, perf in result['regime_performance'].items():
            logger.info(f"{regime}: Win rate {perf['win_rate']*100:.2f}%, {perf['total_trades']} giao dịch")
        
        # Phân phối chế độ thị trường
        logger.info("\n==== PHÂN PHỐI CHẾ ĐỘ THỊ TRƯỜNG ====")
        for regime, pct in result['regime_distribution'].items():
            logger.info(f"{regime}: {pct:.1f}%")

if __name__ == "__main__":
    main()