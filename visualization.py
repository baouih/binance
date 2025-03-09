"""
Module để hiển thị kết quả phân tích và giao dịch một cách trực quan

Module này cung cấp các hàm để tạo các biểu đồ trực quan cho dữ liệu giá,
các chỉ báo kỹ thuật, kết quả phân tích, và hiệu suất giao dịch.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

# Thiết lập style cho matplotlib
plt.style.use('dark_background')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3

def ensure_directory(path):
    """Đảm bảo thư mục tồn tại"""
    os.makedirs(path, exist_ok=True)

def plot_price_with_indicators(df: pd.DataFrame, indicators: List[str] = None, 
                             trades: List[Dict] = None, title: str = "Price Chart", 
                             save_path: Optional[str] = None):
    """
    Vẽ biểu đồ giá kèm các chỉ báo và giao dịch
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
        indicators (List[str]): Danh sách các chỉ báo cần vẽ
        trades (List[Dict]): Danh sách các giao dịch
        title (str): Tiêu đề của biểu đồ
        save_path (str): Đường dẫn để lưu biểu đồ (nếu None, sẽ hiển thị)
    """
    if indicators is None:
        indicators = []
    
    # Tạo subplots
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle(title, fontsize=16)
    
    # Plot giá
    axes[0].plot(df.index, df['close'], label='Close Price')
    
    # Plot các chỉ báo trên biểu đồ giá
    for indicator in indicators:
        if indicator in df.columns:
            if indicator in ['ema9', 'ema21', 'sma50', 'sma200']:
                axes[0].plot(df.index, df[indicator], label=indicator.upper())
    
    # Plot các giao dịch
    if trades:
        buy_times = []
        buy_prices = []
        sell_times = []
        sell_prices = []
        
        for trade in trades:
            entry_time = trade['entry_time']
            if isinstance(entry_time, str):
                entry_time = datetime.strptime(entry_time, '%Y-%m-%d %H:%M:%S')
            
            exit_time = trade['exit_time']
            if isinstance(exit_time, str):
                exit_time = datetime.strptime(exit_time, '%Y-%m-%d %H:%M:%S')
            
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            
            if trade['side'] == 'BUY':
                buy_times.append(entry_time)
                buy_prices.append(entry_price)
                
                # Vẽ đường kết nối từ điểm vào đến điểm ra
                axes[0].plot([entry_time, exit_time], [entry_price, exit_price], 
                           color='green' if exit_price > entry_price else 'red', 
                           linestyle='--', alpha=0.7)
            else:  # 'SELL'
                sell_times.append(entry_time)
                sell_prices.append(entry_price)
                
                # Vẽ đường kết nối từ điểm vào đến điểm ra
                axes[0].plot([entry_time, exit_time], [entry_price, exit_price], 
                           color='green' if exit_price < entry_price else 'red', 
                           linestyle='--', alpha=0.7)
        
        # Plot các điểm vào lệnh
        if buy_times:
            axes[0].scatter(buy_times, buy_prices, color='lime', marker='^', s=100, label='Buy')
        if sell_times:
            axes[0].scatter(sell_times, sell_prices, color='red', marker='v', s=100, label='Sell')
    
    # Plot RSI hoặc MACD ở phần dưới
    if 'rsi' in df.columns and 'rsi' in indicators:
        axes[1].plot(df.index, df['rsi'], label='RSI', color='purple')
        axes[1].axhline(y=70, color='red', linestyle='--', alpha=0.5)
        axes[1].axhline(y=30, color='green', linestyle='--', alpha=0.5)
        axes[1].set_ylabel('RSI')
        axes[1].set_ylim(0, 100)
    elif all(x in df.columns for x in ['macd', 'macd_signal']) and 'macd' in indicators:
        axes[1].plot(df.index, df['macd'], label='MACD', color='blue')
        axes[1].plot(df.index, df['macd_signal'], label='Signal', color='red')
        
        # Plot MACD histogram
        if 'macd_hist' in df.columns:
            for i in range(len(df) - 1):
                color = 'green' if df['macd_hist'].iloc[i] > 0 else 'red'
                axes[1].bar(df.index[i], df['macd_hist'].iloc[i], color=color, width=0.7)
        
        axes[1].set_ylabel('MACD')
    
    # Định dạng trục x
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    # Thêm legend
    axes[0].legend(loc='upper left')
    axes[1].legend(loc='upper left')
    
    # Điều chỉnh layout
    plt.tight_layout()
    
    # Lưu hoặc hiển thị
    if save_path:
        ensure_directory(os.path.dirname(save_path))
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

def plot_equity_curve(equity_curve: Union[List[float], np.ndarray], 
                    trades: List[Dict] = None, 
                    title: str = "Equity Curve", 
                    save_path: Optional[str] = None):
    """
    Vẽ biểu đồ equity curve và các điểm giao dịch
    
    Args:
        equity_curve (List[float]): Danh sách giá trị equity curve
        trades (List[Dict]): Danh sách các giao dịch
        title (str): Tiêu đề của biểu đồ
        save_path (str): Đường dẫn để lưu biểu đồ (nếu None, sẽ hiển thị)
    """
    plt.figure(figsize=(12, 6))
    
    # Plot equity curve
    plt.plot(equity_curve, label='Equity', color='cyan')
    
    # Plot các điểm giao dịch
    if trades:
        trade_indices = []
        pnl_values = []
        colors = []
        
        # Tính chỉ số trong equity curve của các giao dịch
        current_index = 0
        for trade in trades:
            pnl = trade.get('pnl', 0)
            pnl_values.append(pnl)
            
            # Ước tính chỉ số trong equity curve
            if 'exit_index' in trade:
                trade_indices.append(trade['exit_index'])
            else:
                # Nếu không có chỉ số rõ ràng, cách đều các điểm
                current_index += len(equity_curve) // (len(trades) + 1)
                trade_indices.append(current_index)
            
            colors.append('green' if pnl > 0 else 'red')
        
        # Plot các điểm giao dịch
        for i, (idx, pnl) in enumerate(zip(trade_indices, pnl_values)):
            if idx < len(equity_curve):
                plt.scatter(idx, equity_curve[idx], color=colors[i], s=100, 
                         alpha=0.7, edgecolors='white')
                
                # Thêm nhãn PnL
                plt.annotate(f"{pnl:.2f}%", 
                           (idx, equity_curve[idx]), 
                           textcoords="offset points", 
                           xytext=(0, 10), 
                           ha='center')
    
    # Tính và plot drawdown
    max_equity = np.maximum.accumulate(equity_curve)
    drawdown = (max_equity - equity_curve) / max_equity * 100
    max_dd = np.max(drawdown)
    
    # Thêm thông tin hiệu suất
    if len(equity_curve) > 1:
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100
        plt.title(f"{title} - Return: {total_return:.2f}%, Max Drawdown: {max_dd:.2f}%")
    else:
        plt.title(title)
    
    plt.xlabel('Bars')
    plt.ylabel('Equity ($)')
    plt.grid(True, alpha=0.3)
    
    # Lưu hoặc hiển thị
    if save_path:
        ensure_directory(os.path.dirname(save_path))
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

def plot_drawdown_curve(equity_curve: Union[List[float], np.ndarray], 
                       title: str = "Drawdown Analysis", 
                       save_path: Optional[str] = None):
    """
    Vẽ biểu đồ phân tích drawdown
    
    Args:
        equity_curve (List[float]): Danh sách giá trị equity curve
        title (str): Tiêu đề của biểu đồ
        save_path (str): Đường dẫn để lưu biểu đồ (nếu None, sẽ hiển thị)
    """
    plt.figure(figsize=(12, 6))
    
    # Tính drawdown
    max_equity = np.maximum.accumulate(equity_curve)
    drawdown = (max_equity - equity_curve) / max_equity * 100
    max_dd = np.max(drawdown)
    max_dd_idx = np.argmax(drawdown)
    
    # Plot drawdown
    plt.plot(drawdown, color='red', label=f'Drawdown (Max: {max_dd:.2f}%)')
    plt.axhline(y=max_dd, color='orange', linestyle='--', alpha=0.7)
    
    # Đánh dấu điểm drawdown lớn nhất
    plt.scatter(max_dd_idx, max_dd, color='yellow', s=100, zorder=5)
    plt.annotate(f"Max DD: {max_dd:.2f}%", 
               (max_dd_idx, max_dd), 
               textcoords="offset points", 
               xytext=(0, -20), 
               ha='center',
               color='yellow',
               fontweight='bold')
    
    # Thêm các mức đánh dấu
    plt.axhline(y=5, color='yellow', linestyle='--', alpha=0.5, label='5% DD')
    plt.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='10% DD')
    plt.axhline(y=20, color='red', linestyle='--', alpha=0.5, label='20% DD')
    
    plt.title(title)
    plt.xlabel('Bars')
    plt.ylabel('Drawdown (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Lưu hoặc hiển thị
    if save_path:
        ensure_directory(os.path.dirname(save_path))
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

def plot_trade_distribution(trades: List[Dict], 
                          title: str = "Trade Distribution Analysis", 
                          save_path: Optional[str] = None):
    """
    Vẽ biểu đồ phân tích phân phối giao dịch
    
    Args:
        trades (List[Dict]): Danh sách các giao dịch
        title (str): Tiêu đề của biểu đồ
        save_path (str): Đường dẫn để lưu biểu đồ (nếu None, sẽ hiển thị)
    """
    if not trades:
        return
    
    plt.figure(figsize=(14, 10))
    
    # Tạo 2x2 subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(title, fontsize=16)
    
    # Trích xuất dữ liệu
    pnl_values = [trade.get('pnl', 0) for trade in trades]
    win_trades = [pnl for pnl in pnl_values if pnl > 0]
    loss_trades = [pnl for pnl in pnl_values if pnl <= 0]
    
    # 1. Histogram phân phối PnL
    axes[0, 0].hist(pnl_values, bins=20, alpha=0.7, color='cyan')
    axes[0, 0].axvline(x=0, color='white', linestyle='--', alpha=0.7)
    axes[0, 0].set_title('PnL Distribution')
    axes[0, 0].set_xlabel('PnL (%)')
    axes[0, 0].set_ylabel('Frequency')
    
    # 2. Pie chart Win/Loss ratio
    win_count = len(win_trades)
    loss_count = len(loss_trades)
    total_count = win_count + loss_count
    
    if total_count > 0:
        win_rate = win_count / total_count * 100
        loss_rate = loss_count / total_count * 100
        
        axes[0, 1].pie([win_rate, loss_rate], 
                     labels=[f'Win ({win_rate:.1f}%)', f'Loss ({loss_rate:.1f}%)'], 
                     colors=['green', 'red'], 
                     autopct='%1.1f%%', 
                     startangle=90, 
                     wedgeprops={'alpha': 0.7})
        axes[0, 1].set_title('Win/Loss Ratio')
    
    # 3. Bar chart Avg Win vs Avg Loss
    avg_win = np.mean(win_trades) if win_trades else 0
    avg_loss = np.mean(loss_trades) if loss_trades else 0
    
    axes[1, 0].bar(['Avg Win', 'Avg Loss'], [avg_win, avg_loss], 
                 color=['green', 'red'], alpha=0.7)
    axes[1, 0].axhline(y=0, color='white', linestyle='-', alpha=0.3)
    axes[1, 0].set_title('Average Win vs Loss')
    axes[1, 0].set_ylabel('PnL (%)')
    
    for i, v in enumerate([avg_win, avg_loss]):
        axes[1, 0].text(i, v + (1 if v > 0 else -1), 
                      f"{v:.2f}%", 
                      ha='center', 
                      fontweight='bold',
                      color='white')
    
    # 4. Scatter plot diễn biến theo thời gian
    if 'exit_time' in trades[0]:
        # Trích xuất thời gian kết thúc giao dịch
        exit_times = []
        for trade in trades:
            exit_time = trade.get('exit_time')
            if isinstance(exit_time, str):
                exit_time = datetime.strptime(exit_time, '%Y-%m-%d %H:%M:%S')
            exit_times.append(exit_time)
        
        # Sắp xếp giao dịch theo thời gian
        sorted_indices = np.argsort(exit_times)
        sorted_pnl = [pnl_values[i] for i in sorted_indices]
        
        # Plot diễn biến theo thời gian
        colors = ['green' if pnl > 0 else 'red' for pnl in sorted_pnl]
        axes[1, 1].scatter(range(len(sorted_pnl)), sorted_pnl, 
                         c=colors, alpha=0.7, s=50)
        axes[1, 1].plot(range(len(sorted_pnl)), sorted_pnl, 
                      color='white', alpha=0.3)
        axes[1, 1].axhline(y=0, color='white', linestyle='-', alpha=0.3)
        axes[1, 1].set_title('PnL Evolution Over Time')
        axes[1, 1].set_xlabel('Trade Number')
        axes[1, 1].set_ylabel('PnL (%)')
    
    plt.tight_layout()
    fig.subplots_adjust(top=0.9)
    
    # Lưu hoặc hiển thị
    if save_path:
        ensure_directory(os.path.dirname(save_path))
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

def plot_comparative_analysis(results: Dict[str, Dict], 
                            metrics: List[str] = None, 
                            title: str = "Strategy Comparison", 
                            save_path: Optional[str] = None):
    """
    Vẽ biểu đồ so sánh các chiến lược
    
    Args:
        results (Dict[str, Dict]): Dictionary chứa kết quả của các chiến lược
        metrics (List[str]): Danh sách các metrics cần so sánh
        title (str): Tiêu đề của biểu đồ
        save_path (str): Đường dẫn để lưu biểu đồ (nếu None, sẽ hiển thị)
    """
    if metrics is None:
        metrics = ['total_return', 'win_rate', 'profit_factor', 'max_drawdown']
    
    strategies = list(results.keys())
    num_metrics = len(metrics)
    
    plt.figure(figsize=(14, 10))
    
    # Tạo subplots cho từng metric
    fig, axes = plt.subplots(num_metrics, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16)
    
    for i, metric in enumerate(metrics):
        metric_values = []
        for strategy, result in results.items():
            perf = result.get('performance', {})
            metric_values.append(perf.get(metric, 0))
        
        # Plot bar chart cho metric
        colors = plt.cm.viridis(np.linspace(0, 1, len(strategies)))
        bars = axes[i].bar(strategies, metric_values, color=colors, alpha=0.7)
        
        # Format thích hợp cho từng loại metric
        format_suffix = '%' if metric in ['total_return', 'win_rate', 'max_drawdown'] else ''
        
        # Thêm giá trị trên mỗi bar
        for bar, value in zip(bars, metric_values):
            axes[i].text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                      f"{value:.2f}{format_suffix}", 
                      ha='center', va='bottom', 
                      fontweight='bold')
        
        # Set title và labels
        metric_name = ' '.join(word.capitalize() for word in metric.split('_'))
        axes[i].set_title(f"{metric_name}")
        axes[i].set_ylabel(metric_name)
        
        # Format trục y
        if metric in ['total_return', 'win_rate', 'max_drawdown']:
            # Format as percentages
            axes[i].yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.0f}%'.format(y)))
    
    plt.tight_layout()
    fig.subplots_adjust(top=0.9)
    
    # Lưu hoặc hiển thị
    if save_path:
        ensure_directory(os.path.dirname(save_path))
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

def plot_market_regimes(df: pd.DataFrame, 
                      title: str = "Market Regime Analysis", 
                      save_path: Optional[str] = None):
    """
    Vẽ biểu đồ phân tích chế độ thị trường
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu giá và chế độ thị trường
        title (str): Tiêu đề của biểu đồ
        save_path (str): Đường dẫn để lưu biểu đồ (nếu None, sẽ hiển thị)
    """
    if 'regime' not in df.columns:
        return
    
    # Tạo subplots
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle(title, fontsize=16)
    
    # Plot giá
    axes[0].plot(df.index, df['close'], label='Close Price')
    
    # Đánh dấu các chế độ thị trường khác nhau
    regimes = df['regime'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(regimes)))
    regime_color_map = dict(zip(regimes, colors))
    
    # Thêm vùng phủ cho từng chế độ
    current_regime = df['regime'].iloc[0]
    regime_start = df.index[0]
    
    for i in range(1, len(df)):
        if df['regime'].iloc[i] != current_regime or i == len(df) - 1:
            # Vẽ vùng phủ từ regime_start đến i
            if i == len(df) - 1 and df['regime'].iloc[i] == current_regime:
                end_idx = i
            else:
                end_idx = i - 1
            
            axes[0].axvspan(regime_start, df.index[end_idx], 
                         alpha=0.2, 
                         color=regime_color_map[current_regime])
            
            # Cập nhật chế độ hiện tại và thời điểm bắt đầu
            current_regime = df['regime'].iloc[i]
            regime_start = df.index[i]
    
    # Plot biểu đồ cột thể hiện chế độ thị trường
    # Chuyển đổi regime thành mã số
    regime_to_code = {regime: i for i, regime in enumerate(regimes)}
    regime_codes = [regime_to_code[r] for r in df['regime']]
    
    # Plot biểu đồ cột
    for i, regime in enumerate(regimes):
        mask = df['regime'] == regime
        if np.any(mask):
            axes[1].scatter(df.index[mask], [i] * np.sum(mask), 
                         color=regime_color_map[regime], 
                         marker='s', s=100, 
                         label=regime)
    
    # Thêm legend
    axes[0].legend(loc='upper left')
    axes[1].legend(loc='upper left')
    
    # Định dạng trục y của biểu đồ chế độ
    axes[1].set_yticks(range(len(regimes)))
    axes[1].set_yticklabels(regimes)
    axes[1].set_ylabel('Market Regime')
    
    # Định dạng trục x
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    
    # Lưu hoặc hiển thị
    if save_path:
        ensure_directory(os.path.dirname(save_path))
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

def plot_heatmap_analysis(trades: List[Dict], 
                        feature_x: str, feature_y: str, 
                        title: str = "Trade Success Heatmap", 
                        save_path: Optional[str] = None):
    """
    Vẽ biểu đồ phân tích heatmap theo hai đặc tính
    
    Args:
        trades (List[Dict]): Danh sách các giao dịch
        feature_x (str): Tên đặc tính trên trục x
        feature_y (str): Tên đặc tính trên trục y
        title (str): Tiêu đề của biểu đồ
        save_path (str): Đường dẫn để lưu biểu đồ (nếu None, sẽ hiển thị)
    """
    if not trades or not all(feature_x in trade and feature_y in trade for trade in trades):
        return
    
    plt.figure(figsize=(10, 8))
    
    # Trích xuất giá trị đặc tính và kết quả giao dịch
    x_values = [trade[feature_x] for trade in trades]
    y_values = [trade[feature_y] for trade in trades]
    pnl_values = [trade.get('pnl', 0) for trade in trades]
    
    # Tạo lưới cho heatmap
    x_bins = np.linspace(min(x_values), max(x_values), 10)
    y_bins = np.linspace(min(y_values), max(y_values), 10)
    
    # Đếm số giao dịch thành công trong mỗi ô
    heatmap = np.zeros((len(y_bins)-1, len(x_bins)-1))
    counts = np.zeros((len(y_bins)-1, len(x_bins)-1))
    
    for x, y, pnl in zip(x_values, y_values, pnl_values):
        x_idx = np.digitize(x, x_bins) - 1
        y_idx = np.digitize(y, y_bins) - 1
        
        if 0 <= x_idx < len(x_bins)-1 and 0 <= y_idx < len(y_bins)-1:
            heatmap[y_idx, x_idx] += pnl
            counts[y_idx, x_idx] += 1
    
    # Tính trung bình PnL trong mỗi ô
    with np.errstate(divide='ignore', invalid='ignore'):
        avg_pnl = np.divide(heatmap, counts)
        avg_pnl = np.nan_to_num(avg_pnl)
    
    # Vẽ heatmap
    plt.imshow(avg_pnl, aspect='auto', cmap='RdYlGn', 
             extent=[min(x_values), max(x_values), min(y_values), max(y_values)])
    
    plt.colorbar(label='Avg PnL (%)')
    plt.title(title)
    plt.xlabel(feature_x)
    plt.ylabel(feature_y)
    
    # Lưu hoặc hiển thị
    if save_path:
        ensure_directory(os.path.dirname(save_path))
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

def create_dashboard(results_dir: str, output_dir: str = "dashboard"):
    """
    Tạo dashboard tổng hợp từ các kết quả
    
    Args:
        results_dir (str): Thư mục chứa kết quả
        output_dir (str): Thư mục đầu ra cho dashboard
    """
    ensure_directory(output_dir)
    
    # Tìm tất cả các file kết quả
    result_files = []
    for root, _, files in os.walk(results_dir):
        for file in files:
            if file.endswith('.json') and 'results' in file:
                result_files.append(os.path.join(root, file))
    
    # Tạo các biểu đồ cho từng file kết quả
    for result_file in result_files:
        strategy_name = os.path.basename(result_file).replace('_results.json', '')
        
        with open(result_file, 'r') as f:
            result = json.load(f)
        
        # Tạo biểu đồ equity curve
        if 'equity_curve' in result:
            plot_equity_curve(
                result['equity_curve'],
                trades=result.get('trades', []),
                title=f"{strategy_name} - Equity Curve",
                save_path=f"{output_dir}/{strategy_name}_equity.png"
            )
        
        # Tạo biểu đồ drawdown
        if 'equity_curve' in result:
            plot_drawdown_curve(
                result['equity_curve'],
                title=f"{strategy_name} - Drawdown Analysis",
                save_path=f"{output_dir}/{strategy_name}_drawdown.png"
            )
        
        # Tạo biểu đồ phân phối giao dịch
        if 'trades' in result and result['trades']:
            plot_trade_distribution(
                result['trades'],
                title=f"{strategy_name} - Trade Distribution",
                save_path=f"{output_dir}/{strategy_name}_distribution.png"
            )
    
    # Tạo biểu đồ so sánh các chiến lược
    all_results = {}
    for result_file in result_files:
        strategy_name = os.path.basename(result_file).replace('_results.json', '')
        
        with open(result_file, 'r') as f:
            result = json.load(f)
        
        all_results[strategy_name] = result
    
    # So sánh các chiến lược
    if len(all_results) > 1:
        plot_comparative_analysis(
            all_results,
            title="Strategy Comparison",
            save_path=f"{output_dir}/strategy_comparison.png"
        )
    
    # Tạo file HTML dashboard
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Trading Strategy Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #1e1e1e;
                color: white;
            }}
            h1, h2, h3 {{
                color: #61dafb;
            }}
            .dashboard {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
            }}
            .dashboard-item {{
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                width: calc(50% - 40px);
                margin-bottom: 20px;
            }}
            .dashboard-item-full {{
                width: calc(100% - 40px);
            }}
            img {{
                max-width: 100%;
                height: auto;
                border-radius: 4px;
            }}
            .strategy-section {{
                margin-bottom: 40px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #444;
                padding: 8px 12px;
                text-align: left;
            }}
            th {{
                background-color: #333;
            }}
            tr:nth-child(even) {{
                background-color: #2a2a2a;
            }}
            .good {{
                color: #4caf50;
            }}
            .bad {{
                color: #f44336;
            }}
        </style>
    </head>
    <body>
        <h1>Trading Strategy Dashboard</h1>
        
        <div class="dashboard-item dashboard-item-full">
            <h2>Strategy Comparison</h2>
            <img src="strategy_comparison.png" alt="Strategy Comparison">
        </div>
        
        <div class="dashboard">
    """
    
    # Thêm phần cho từng chiến lược
    for strategy_name in all_results:
        result = all_results[strategy_name]
        performance = result.get('performance', {})
        
        # Format các metrics
        total_return = performance.get('total_return', 0)
        win_rate = performance.get('win_rate', 0)
        profit_factor = performance.get('profit_factor', 0)
        max_drawdown = performance.get('max_drawdown', 0)
        total_trades = performance.get('total_trades', 0)
        
        html_content += f"""
        <div class="strategy-section dashboard-item-full">
            <h2>{strategy_name}</h2>
            
            <div class="dashboard">
                <div class="dashboard-item">
                    <h3>Performance Metrics</h3>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                        <tr>
                            <td>Total Return</td>
                            <td class="{'good' if total_return > 0 else 'bad'}">{total_return:.2f}%</td>
                        </tr>
                        <tr>
                            <td>Win Rate</td>
                            <td class="{'good' if win_rate > 50 else 'bad'}">{win_rate:.2f}%</td>
                        </tr>
                        <tr>
                            <td>Profit Factor</td>
                            <td class="{'good' if profit_factor > 1 else 'bad'}">{profit_factor:.2f}</td>
                        </tr>
                        <tr>
                            <td>Max Drawdown</td>
                            <td class="{'good' if max_drawdown < 10 else 'bad'}">{max_drawdown:.2f}%</td>
                        </tr>
                        <tr>
                            <td>Total Trades</td>
                            <td>{total_trades}</td>
                        </tr>
                    </table>
                </div>
                
                <div class="dashboard-item">
                    <h3>Equity Curve</h3>
                    <img src="{strategy_name}_equity.png" alt="Equity Curve">
                </div>
                
                <div class="dashboard-item">
                    <h3>Drawdown Analysis</h3>
                    <img src="{strategy_name}_drawdown.png" alt="Drawdown Analysis">
                </div>
                
                <div class="dashboard-item">
                    <h3>Trade Distribution</h3>
                    <img src="{strategy_name}_distribution.png" alt="Trade Distribution">
                </div>
            </div>
        </div>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    # Lưu file HTML
    with open(f"{output_dir}/index.html", 'w') as f:
        f.write(html_content)
    
    print(f"Dashboard created at {output_dir}/index.html")

def main():
    """Hàm chính để test module"""
    # Tạo dữ liệu mẫu
    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Tạo dữ liệu giá giả lập
    np.random.seed(42)
    n = 100
    dates = [datetime.now() - timedelta(days=n-i) for i in range(n)]
    close = 100 + np.cumsum(np.random.normal(0, 1, n))
    high = close + np.random.uniform(0, 2, n)
    low = close - np.random.uniform(0, 2, n)
    
    df = pd.DataFrame({
        'open': close - np.random.uniform(-1, 1, n),
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.uniform(1000, 5000, n)
    }, index=dates)
    
    # Thêm chỉ báo
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    df['rsi'] = 50 + np.random.normal(0, 10, n)  # Giả lập RSI
    df['rsi'] = df['rsi'].clip(0, 100)
    
    # Thêm chế độ thị trường
    regimes = ['trending_up', 'trending_down', 'ranging', 'volatile', 'breakout']
    df['regime'] = [regimes[i % len(regimes)] for i in range(n)]
    
    # Tạo giao dịch mẫu
    trades = []
    for i in range(10):
        entry_idx = np.random.randint(0, n - 10)
        exit_idx = entry_idx + np.random.randint(3, 10)
        
        side = 'BUY' if np.random.rand() > 0.5 else 'SELL'
        entry_price = df['close'].iloc[entry_idx]
        exit_price = df['close'].iloc[exit_idx]
        
        if side == 'BUY':
            pnl = (exit_price - entry_price) / entry_price * 100
        else:
            pnl = (entry_price - exit_price) / entry_price * 100
        
        trades.append({
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'entry_time': df.index[entry_idx],
            'exit_time': df.index[exit_idx],
            'pnl': pnl,
            'exit_reason': np.random.choice(['Take Profit', 'Stop Loss', 'Signal Reversed'])
        })
    
    # Tạo equity curve mẫu
    initial_balance = 10000
    equity_curve = [initial_balance]
    for i in range(1, n):
        change = np.random.normal(0.05, 0.2)  # mean positive return
        equity_curve.append(equity_curve[-1] * (1 + change / 100))
    
    # Test các hàm vẽ biểu đồ
    ensure_directory('test_charts')
    
    plot_price_with_indicators(df, indicators=['ema9', 'ema21', 'rsi'], trades=trades, 
                            title="Test Price Chart", save_path="test_charts/price_chart.png")
    
    plot_equity_curve(equity_curve, trades=trades, 
                    title="Test Equity Curve", save_path="test_charts/equity_curve.png")
    
    plot_drawdown_curve(equity_curve, 
                      title="Test Drawdown Analysis", save_path="test_charts/drawdown.png")
    
    plot_trade_distribution(trades, 
                         title="Test Trade Distribution", save_path="test_charts/distribution.png")
    
    plot_market_regimes(df, 
                     title="Test Market Regime Analysis", save_path="test_charts/regimes.png")
    
    print("Biểu đồ test đã được lưu trong thư mục 'test_charts'")

if __name__ == "__main__":
    main()