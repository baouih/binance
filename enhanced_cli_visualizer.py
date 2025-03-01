#!/usr/bin/env python3
"""
Công cụ trực quan hóa nâng cao cho BinanceTrader CLI

Module này tạo biểu đồ và trực quan hóa dữ liệu từ bot trading tiền điện tử.
Nó có thể chạy độc lập hoặc được tích hợp vào cli_controller.py.
"""

import os
import sys
import json
import time
import logging
import argparse
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cli_visualizer.log')
    ]
)
logger = logging.getLogger('cli_visualizer')

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str) -> None:
    """In tiêu đề với định dạng nổi bật"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*50}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(50)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*50}{Colors.ENDC}\n")

def load_trading_state(file_path: str = "trading_state.json") -> Dict:
    """Tải dữ liệu từ file trading_state.json"""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        else:
            logger.error(f"File {file_path} không tồn tại")
            return {}
    except Exception as e:
        logger.error(f"Lỗi khi tải file {file_path}: {e}")
        return {}

def generate_equity_curve(save_path: Optional[str] = None, show: bool = True) -> None:
    """
    Tạo biểu đồ đường cong vốn từ dữ liệu giao dịch
    
    Args:
        save_path: Đường dẫn để lưu biểu đồ (nếu None, chỉ hiển thị)
        show: Có hiển thị biểu đồ hay không
    """
    trading_state = load_trading_state()
    
    if not trading_state:
        print(f"{Colors.RED}Không thể tải dữ liệu giao dịch.{Colors.ENDC}")
        return
    
    closed_positions = trading_state.get("closed_positions", [])
    
    if not closed_positions:
        print(f"{Colors.YELLOW}Không có dữ liệu giao dịch đã đóng.{Colors.ENDC}")
        return
    
    # Sắp xếp các giao dịch theo thời gian
    sorted_positions = sorted(
        closed_positions,
        key=lambda x: datetime.fromisoformat(x.get('exit_time', '2000-01-01 00:00:00')),
    )
    
    # Xây dựng đường cong vốn
    initial_balance = trading_state.get("initial_balance", 10000)
    balance = initial_balance
    equity_curve = [balance]
    dates = [datetime.fromisoformat(sorted_positions[0].get('entry_time', '2000-01-01 00:00:00'))]
    
    for pos in sorted_positions:
        balance += pos.get('pnl', 0)
        equity_curve.append(balance)
        dates.append(datetime.fromisoformat(pos.get('exit_time', '2000-01-01 00:00:00')))
    
    # Tạo biểu đồ
    plt.figure(figsize=(12, 6))
    plt.plot(dates, equity_curve, 'b-', linewidth=2)
    plt.fill_between(dates, initial_balance, equity_curve, where=(np.array(equity_curve) >= initial_balance), 
                     interpolate=True, color='green', alpha=0.3)
    plt.fill_between(dates, initial_balance, equity_curve, where=(np.array(equity_curve) < initial_balance), 
                     interpolate=True, color='red', alpha=0.3)
    
    # Tính toán và vẽ biểu đồ drawdown
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (np.array(equity_curve) - running_max) / running_max * 100
    
    plt.title('Đường cong vốn và Drawdown', fontsize=14)
    plt.xlabel('Thời gian')
    plt.ylabel('Balance ($)', color='b')
    plt.tick_params(axis='y', labelcolor='b')
    plt.grid(True, alpha=0.3)
    
    # Vẽ trục phụ cho drawdown
    ax2 = plt.twinx()
    ax2.fill_between(dates, 0, drawdown, color='red', alpha=0.2)
    ax2.plot(dates, drawdown, 'r--', alpha=0.7)
    ax2.set_ylabel('Drawdown (%)', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.set_ylim(min(drawdown) * 1.1, 5)  # Đảm bảo biểu đồ có không gian đủ
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"{Colors.GREEN}Đã lưu biểu đồ tại {save_path}{Colors.ENDC}")
    
    if show:
        plt.show()
    else:
        plt.close()

def generate_performance_chart(save_path: Optional[str] = None, show: bool = True) -> None:
    """
    Tạo biểu đồ hiệu suất dạng radar chart
    
    Args:
        save_path: Đường dẫn để lưu biểu đồ (nếu None, chỉ hiển thị)
        show: Có hiển thị biểu đồ hay không
    """
    trading_state = load_trading_state()
    
    if not trading_state:
        print(f"{Colors.RED}Không thể tải dữ liệu giao dịch.{Colors.ENDC}")
        return
    
    metrics = trading_state.get("performance_metrics", {})
    
    if not metrics:
        print(f"{Colors.YELLOW}Không có dữ liệu chỉ số hiệu suất.{Colors.ENDC}")
        return
    
    # Metrics sẽ được hiển thị trong radar chart
    categories = ['Win Rate', 'Profit Factor', 'Risk Reward', 'Sharpe Ratio', 'Sortino Ratio']
    metrics_values = [
        min(100, metrics.get('win_rate', 0)) / 100,  # Scale từ 0-100% thành 0-1
        min(5, metrics.get('profit_factor', 0)) / 5,  # Scale từ 0-5 thành 0-1
        min(5, metrics.get('risk_reward_ratio', 0)) / 5,  # Scale từ 0-5 thành 0-1
        min(3, metrics.get('sharpe_ratio', 0)) / 3,  # Scale từ 0-3 thành 0-1
        min(3, metrics.get('sortino_ratio', 0)) / 3,  # Scale từ 0-3 thành 0-1
    ]
    
    # Vẽ radar chart
    angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]  # Đóng đồ thị
    metrics_values += metrics_values[:1]  # Đóng dữ liệu
    
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(polar=True))
    
    # Đặt mức độ
    ax.set_ylim(0, 1)
    plt.xticks(angles[:-1], categories, size=12)
    
    # Vẽ các đường tròn cấp độ
    for level in [0.2, 0.4, 0.6, 0.8, 1.0]:
        ax.plot(angles, [level] * len(angles), '--', color='gray', alpha=0.3)
        if level < 1.0:
            ax.text(np.pi/6, level, f'{level:.1f}', color='gray', ha='center', va='center')
    
    # Vẽ biểu đồ radar
    ax.plot(angles, metrics_values, 'b-', linewidth=2)
    ax.fill(angles, metrics_values, 'b', alpha=0.2)
    
    # Thêm các giá trị thực tế
    for angle, radius, category in zip(angles[:-1], metrics_values[:-1], categories):
        original_value = 0
        if category == 'Win Rate':
            original_value = metrics.get('win_rate', 0)
            value_text = f"{original_value:.1f}%"
        elif category == 'Profit Factor':
            original_value = metrics.get('profit_factor', 0)
            value_text = f"{original_value:.2f}"
        elif category == 'Risk Reward':
            original_value = metrics.get('risk_reward_ratio', 0)
            value_text = f"{original_value:.2f}"
        elif category == 'Sharpe Ratio':
            original_value = metrics.get('sharpe_ratio', 0)
            value_text = f"{original_value:.2f}"
        elif category == 'Sortino Ratio':
            original_value = metrics.get('sortino_ratio', 0)
            value_text = f"{original_value:.2f}"
        else:
            value_text = ""
        
        ax.text(angle, radius + 0.05, value_text, color='blue', ha='center', va='center')
    
    plt.title('Chỉ số hiệu suất', size=15)
    
    # Thêm thông tin bổ sung
    info_text = f"Tổng giao dịch: {metrics.get('total_trades', 0)}\n"
    info_text += f"Win/Loss: {metrics.get('winning_trades', 0)}/{metrics.get('losing_trades', 0)}\n"
    info_text += f"Avg Profit: ${metrics.get('avg_profit', 0):.2f}\n"
    info_text += f"Avg Loss: ${metrics.get('avg_loss', 0):.2f}\n"
    info_text += f"Max Drawdown: {metrics.get('max_drawdown_percent', 0):.2f}%"
    
    plt.figtext(0.02, 0.02, info_text, ha="left", fontsize=12, 
                bbox={"facecolor":"white", "alpha":0.8, "pad":5})
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"{Colors.GREEN}Đã lưu biểu đồ tại {save_path}{Colors.ENDC}")
    
    if show:
        plt.show()
    else:
        plt.close()

def generate_trades_by_symbol(save_path: Optional[str] = None, show: bool = True) -> None:
    """
    Tạo biểu đồ hiệu suất theo từng symbol
    
    Args:
        save_path: Đường dẫn để lưu biểu đồ (nếu None, chỉ hiển thị)
        show: Có hiển thị biểu đồ hay không
    """
    trading_state = load_trading_state()
    
    if not trading_state:
        print(f"{Colors.RED}Không thể tải dữ liệu giao dịch.{Colors.ENDC}")
        return
    
    closed_positions = trading_state.get("closed_positions", [])
    
    if not closed_positions:
        print(f"{Colors.YELLOW}Không có dữ liệu giao dịch đã đóng.{Colors.ENDC}")
        return
    
    # Tính toán thống kê theo symbol
    symbols = {}
    
    for pos in closed_positions:
        symbol = pos.get('symbol', 'Unknown')
        pnl = pos.get('pnl', 0)
        
        if symbol not in symbols:
            symbols[symbol] = {
                'count': 0,
                'profit': 0,
                'win': 0,
                'loss': 0
            }
        
        symbols[symbol]['count'] += 1
        symbols[symbol]['profit'] += pnl
        
        if pnl >= 0:
            symbols[symbol]['win'] += 1
        else:
            symbols[symbol]['loss'] += 1
    
    # Chuẩn bị dữ liệu cho biểu đồ
    symbol_names = list(symbols.keys())
    total_trades = [symbols[s]['count'] for s in symbol_names]
    profits = [symbols[s]['profit'] for s in symbol_names]
    win_rates = [symbols[s]['win'] / symbols[s]['count'] * 100 if symbols[s]['count'] > 0 else 0 
                 for s in symbol_names]
    
    # Sắp xếp theo lợi nhuận
    sorted_indices = np.argsort(profits)[::-1]  # Từ cao xuống thấp
    symbol_names = [symbol_names[i] for i in sorted_indices]
    total_trades = [total_trades[i] for i in sorted_indices]
    profits = [profits[i] for i in sorted_indices]
    win_rates = [win_rates[i] for i in sorted_indices]
    
    # Tạo biểu đồ
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Biểu đồ lợi nhuận theo symbol
    bars = ax1.bar(symbol_names, profits)
    
    # Tô màu các thanh theo lợi nhuận
    for i, bar in enumerate(bars):
        color = 'green' if profits[i] >= 0 else 'red'
        bar.set_color(color)
    
    ax1.set_title('Lợi nhuận theo Symbol')
    ax1.set_xlabel('Symbol')
    ax1.set_ylabel('Lợi nhuận ($)')
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax1.grid(axis='y', alpha=0.3)
    
    # Thêm giá trị trên mỗi thanh
    for i, v in enumerate(profits):
        ax1.text(i, v + np.sign(v) * 5, f'${v:.2f}', 
                ha='center', color='black', fontweight='bold')
    
    # Biểu đồ tỷ lệ thắng và số lượng giao dịch
    ax2.bar(symbol_names, win_rates, alpha=0.7, label='Tỷ lệ thắng (%)')
    
    # Thêm trục phụ cho số lượng giao dịch
    ax3 = ax2.twinx()
    ax3.plot(symbol_names, total_trades, 'ro-', label='Số lượng giao dịch')
    
    # Thêm nhãn
    ax2.set_title('Tỷ lệ thắng và Số lượng giao dịch theo Symbol')
    ax2.set_xlabel('Symbol')
    ax2.set_ylabel('Tỷ lệ thắng (%)')
    ax2.set_ylim(0, 100)
    ax3.set_ylabel('Số lượng giao dịch')
    
    # Thêm grid
    ax2.grid(alpha=0.3)
    
    # Gộp legends
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax3.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    # Thêm giá trị trên mỗi thanh
    for i, v in enumerate(win_rates):
        ax2.text(i, v + 3, f'{v:.1f}%', ha='center')
    for i, v in enumerate(total_trades):
        ax3.text(i, v + 0.5, str(v), ha='center', color='red')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"{Colors.GREEN}Đã lưu biểu đồ tại {save_path}{Colors.ENDC}")
    
    if show:
        plt.show()
    else:
        plt.close()

def generate_dashboard(save_dir: str = 'reports') -> List[str]:
    """
    Tạo bảng điều khiển với tất cả các biểu đồ
    
    Args:
        save_dir: Thư mục để lưu biểu đồ
    
    Returns:
        List[str]: Danh sách các đường dẫn đã lưu
    """
    print_header("Đang tạo báo cáo trực quan...")
    
    # Đảm bảo thư mục tồn tại
    os.makedirs(save_dir, exist_ok=True)
    
    saved_paths = []
    
    # Tạo timestamp cho tên file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Tạo và lưu từng biểu đồ
    try:
        print("Đang tạo biểu đồ đường cong vốn...")
        equity_path = os.path.join(save_dir, f"equity_curve_{timestamp}.png")
        generate_equity_curve(equity_path, False)
        saved_paths.append(equity_path)
        
        print("Đang tạo biểu đồ hiệu suất...")
        performance_path = os.path.join(save_dir, f"performance_{timestamp}.png")
        generate_performance_chart(performance_path, False)
        saved_paths.append(performance_path)
        
        print("Đang tạo biểu đồ phân tích theo symbol...")
        symbol_path = os.path.join(save_dir, f"symbol_analysis_{timestamp}.png")
        generate_trades_by_symbol(symbol_path, False)
        saved_paths.append(symbol_path)
        
        print(f"{Colors.GREEN}Tất cả biểu đồ đã được tạo và lưu trong thư mục {save_dir}{Colors.ENDC}")
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo: {e}")
        print(f"{Colors.RED}Lỗi khi tạo báo cáo: {e}{Colors.ENDC}")
    
    return saved_paths

def generate_detailed_html_report(save_path: str = 'reports/trading_report.html') -> str:
    """
    Tạo báo cáo HTML đầy đủ với các biểu đồ và phân tích
    
    Args:
        save_path: Đường dẫn để lưu báo cáo HTML
    
    Returns:
        str: Đường dẫn đến file báo cáo
    """
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Tạo các biểu đồ và lưu
        report_dir = os.path.dirname(save_path)
        chart_paths = generate_dashboard(report_dir)
        
        # Lấy dữ liệu giao dịch
        trading_state = load_trading_state()
        
        if not trading_state:
            print(f"{Colors.RED}Không thể tải dữ liệu giao dịch.{Colors.ENDC}")
            return ""
        
        # Tạo nội dung HTML
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>BinanceTrader - Báo cáo Giao dịch</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    border-radius: 5px;
                }
                h1, h2, h3 {
                    color: #2c3e50;
                }
                .dashboard {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    margin-bottom: 20px;
                }
                .metric-card {
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 15px;
                    margin-bottom: 15px;
                    flex: 1 0 calc(25% - 20px);
                    min-width: 250px;
                    margin-right: 10px;
                }
                .metric-value {
                    font-size: 24px;
                    font-weight: bold;
                    margin: 10px 0;
                }
                .positive { color: #27ae60; }
                .negative { color: #e74c3c; }
                .neutral { color: #2980b9; }
                .chart-container {
                    margin: 30px 0;
                }
                .chart-container img {
                    width: 100%;
                    max-width: 100%;
                    height: auto;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                th, td {
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                thead {
                    background-color: #f8f9fa;
                }
                tr:hover {
                    background-color: #f5f5f5;
                }
                .trade-win { background-color: rgba(46, 204, 113, 0.1); }
                .trade-loss { background-color: rgba(231, 76, 60, 0.1); }
                .footer {
                    margin-top: 30px;
                    text-align: center;
                    font-size: 12px;
                    color: #888;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>BinanceTrader - Báo cáo Giao dịch</h1>
                <p>Báo cáo được tạo vào: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        """
        
        # Thêm phần tổng quan
        metrics = trading_state.get("performance_metrics", {})
        current_balance = trading_state.get("current_balance", 0)
        initial_balance = 10000  # Giả sử giá trị mặc định
        
        total_profit = current_balance - initial_balance
        profit_percentage = (total_profit / initial_balance) * 100 if initial_balance > 0 else 0
        
        html_content += """
                <h2>Tổng quan hiệu suất</h2>
                <div class="dashboard">
                    <div class="metric-card">
                        <h3>Số dư hiện tại</h3>
                        <div class="metric-value neutral">$""" + f"{current_balance:.2f}" + """</div>
                    </div>
                    <div class="metric-card">
                        <h3>Lợi nhuận</h3>
                        <div class="metric-value """ + ("positive" if total_profit >= 0 else "negative") + """">$""" + f"{total_profit:.2f}" + """ (""" + f"{profit_percentage:.2f}%" + """)</div>
                    </div>
                    <div class="metric-card">
                        <h3>Tỷ lệ thắng</h3>
                        <div class="metric-value neutral">""" + f"{metrics.get('win_rate', 0):.2f}%" + """</div>
                    </div>
                    <div class="metric-card">
                        <h3>Max Drawdown</h3>
                        <div class="metric-value negative">""" + f"{metrics.get('max_drawdown_percent', 0):.2f}%" + """</div>
                    </div>
                </div>
                
                <div class="dashboard">
                    <div class="metric-card">
                        <h3>Tổng số giao dịch</h3>
                        <div class="metric-value neutral">""" + f"{metrics.get('total_trades', 0)}" + """</div>
                    </div>
                    <div class="metric-card">
                        <h3>Profit Factor</h3>
                        <div class="metric-value """ + ("positive" if metrics.get('profit_factor', 0) >= 1.5 else "neutral") + """">""" + f"{metrics.get('profit_factor', 0):.2f}" + """</div>
                    </div>
                    <div class="metric-card">
                        <h3>Sharpe Ratio</h3>
                        <div class="metric-value """ + ("positive" if metrics.get('sharpe_ratio', 0) >= 1 else "neutral") + """">""" + f"{metrics.get('sharpe_ratio', 0):.2f}" + """</div>
                    </div>
                    <div class="metric-card">
                        <h3>Risk/Reward</h3>
                        <div class="metric-value """ + ("positive" if metrics.get('risk_reward_ratio', 0) >= 1.5 else "neutral") + """">""" + f"{metrics.get('risk_reward_ratio', 0):.2f}" + """</div>
                    </div>
                </div>
        """
        
        # Thêm phần biểu đồ
        html_content += """
                <h2>Biểu đồ phân tích</h2>
        """
        
        for path in chart_paths:
            rel_path = os.path.relpath(path, os.path.dirname(save_path))
            title = "Biểu đồ "
            if "equity" in path:
                title += "Đường Cong Vốn & Drawdown"
            elif "performance" in path:
                title += "Chỉ Số Hiệu Suất"
            elif "symbol" in path:
                title += "Phân Tích Theo Symbol"
            
            html_content += f"""
                <div class="chart-container">
                    <h3>{title}</h3>
                    <img src="{rel_path}" alt="{title}">
                </div>
            """
        
        # Thêm phần giao dịch gần đây
        closed_positions = trading_state.get("closed_positions", [])
        
        if closed_positions:
            # Sắp xếp theo thời gian đóng vị thế (gần nhất đầu tiên)
            sorted_positions = sorted(
                closed_positions,
                key=lambda x: x.get('exit_time', ''),
                reverse=True
            )
            
            # Lấy 10 giao dịch gần nhất
            recent_trades = sorted_positions[:10]
            
            html_content += """
                <h2>Giao dịch gần đây</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Loại</th>
                            <th>Giá vào</th>
                            <th>Giá ra</th>
                            <th>Khối lượng</th>
                            <th>Lợi nhuận</th>
                            <th>%</th>
                            <th>Thời gian vào</th>
                            <th>Thời gian ra</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for trade in recent_trades:
                pnl = trade.get('pnl', 0)
                row_class = "trade-win" if pnl >= 0 else "trade-loss"
                
                html_content += f"""
                        <tr class="{row_class}">
                            <td>{trade.get('symbol', 'N/A')}</td>
                            <td>{trade.get('type', 'N/A')}</td>
                            <td>${trade.get('entry_price', 0):.2f}</td>
                            <td>${trade.get('exit_price', 0):.2f}</td>
                            <td>{trade.get('quantity', 0):.4f}</td>
                            <td class="{"positive" if pnl >= 0 else "negative"}">${pnl:.2f}</td>
                            <td class="{"positive" if pnl >= 0 else "negative"}">{trade.get('pnl_percent', 0):.2f}%</td>
                            <td>{trade.get('entry_time', 'N/A')}</td>
                            <td>{trade.get('exit_time', 'N/A')}</td>
                        </tr>
                """
            
            html_content += """
                    </tbody>
                </table>
            """
        
        # Thêm phần vị thế hiện tại
        open_positions = trading_state.get("open_positions", [])
        
        if open_positions:
            html_content += """
                <h2>Vị thế hiện tại</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Loại</th>
                            <th>Giá vào</th>
                            <th>Giá hiện tại</th>
                            <th>Khối lượng</th>
                            <th>Lợi nhuận</th>
                            <th>%</th>
                            <th>Thời gian vào</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for pos in open_positions:
                pnl = pos.get('pnl', 0)
                row_class = "trade-win" if pnl >= 0 else "trade-loss"
                
                html_content += f"""
                        <tr class="{row_class}">
                            <td>{pos.get('symbol', 'N/A')}</td>
                            <td>{pos.get('type', 'N/A')}</td>
                            <td>${pos.get('entry_price', 0):.2f}</td>
                            <td>${pos.get('current_price', 0):.2f}</td>
                            <td>{pos.get('quantity', 0):.4f}</td>
                            <td class="{"positive" if pnl >= 0 else "negative"}">${pnl:.2f}</td>
                            <td class="{"positive" if pnl >= 0 else "negative"}">{pos.get('pnl_percent', 0):.2f}%</td>
                            <td>{pos.get('entry_time', 'N/A')}</td>
                        </tr>
                """
            
            html_content += """
                    </tbody>
                </table>
            """
        
        # Kết thúc file HTML
        html_content += """
                <div class="footer">
                    <p>BinanceTrader Bot - Báo cáo tạo tự động</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Lưu file HTML
        with open(save_path, "w") as f:
            f.write(html_content)
        
        print(f"{Colors.GREEN}Báo cáo HTML đã được tạo và lưu tại {save_path}{Colors.ENDC}")
        return save_path
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo HTML: {e}")
        print(f"{Colors.RED}Lỗi khi tạo báo cáo HTML: {e}{Colors.ENDC}")
        return ""

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Công cụ trực quan hóa cho BinanceTrader')
    
    # Thêm các tùy chọn dòng lệnh
    parser.add_argument('--equity', '-e', action='store_true', help='Tạo biểu đồ đường cong vốn')
    parser.add_argument('--performance', '-p', action='store_true', help='Tạo biểu đồ hiệu suất')
    parser.add_argument('--symbols', '-s', action='store_true', help='Tạo biểu đồ phân tích theo symbol')
    parser.add_argument('--dashboard', '-d', action='store_true', help='Tạo tất cả các biểu đồ')
    parser.add_argument('--report', '-r', action='store_true', help='Tạo báo cáo HTML đầy đủ')
    parser.add_argument('--output', '-o', type=str, help='Thư mục hoặc file đầu ra')
    
    args = parser.parse_args()
    
    # Nếu không có tham số, hiển thị hướng dẫn
    if len(sys.argv) == 1:
        parser.print_help()
        print("\nVí dụ:")
        print(f"  {sys.argv[0]} --equity              # Tạo biểu đồ đường cong vốn")
        print(f"  {sys.argv[0]} --dashboard           # Tạo tất cả các biểu đồ")
        print(f"  {sys.argv[0]} --report -o report.html    # Tạo báo cáo HTML đầy đủ")
        return
    
    if args.equity:
        generate_equity_curve(args.output)
    
    if args.performance:
        generate_performance_chart(args.output)
    
    if args.symbols:
        generate_trades_by_symbol(args.output)
    
    if args.dashboard:
        output_dir = args.output if args.output else 'reports'
        generate_dashboard(output_dir)
    
    if args.report:
        output_file = args.output if args.output else 'reports/trading_report.html'
        generate_detailed_html_report(output_file)

if __name__ == "__main__":
    main()