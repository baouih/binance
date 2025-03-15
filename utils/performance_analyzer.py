import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """
    Lớp phân tích hiệu suất giao dịch
    """
    
    def __init__(self, results_dir='./results'):
        self.results_dir = Path(results_dir)
        if not self.results_dir.exists():
            os.makedirs(self.results_dir)
    
    def calculate_metrics(self, trades, initial_balance=10000):
        """
        Tính toán các chỉ số hiệu suất từ danh sách giao dịch
        
        Args:
            trades (list): Danh sách các giao dịch
            initial_balance (float): Số dư ban đầu
            
        Returns:
            dict: Các chỉ số hiệu suất
        """
        if not trades:
            logger.warning("Không có giao dịch nào để phân tích")
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_loss': 0,
                'profit_loss_pct': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'win_loss_ratio': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'avg_trade': 0,
                'avg_holding_time': 0
            }
        
        # Số lượng giao dịch
        total_trades = len(trades)
        
        # Số lượng giao dịch thắng/thua
        winning_trades = [t for t in trades if t['profit'] > 0]
        losing_trades = [t for t in trades if t['profit'] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        # Tỷ lệ thắng
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
        
        # Tổng lợi nhuận/lỗ
        total_profit = sum([t['profit'] for t in winning_trades])
        total_loss = sum([abs(t['profit']) for t in losing_trades])
        
        profit_loss = total_profit - total_loss
        profit_loss_pct = (profit_loss / initial_balance) * 100
        
        # Profit factor
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Tính equity curve và drawdown
        equity_curve = [initial_balance]
        current_balance = initial_balance
        
        for trade in sorted(trades, key=lambda x: x['entry_time']):
            current_balance += trade['profit']
            equity_curve.append(current_balance)
        
        # Tính max drawdown
        peak = initial_balance
        drawdown = []
        
        for balance in equity_curve:
            if balance > peak:
                peak = balance
            
            dd = (peak - balance) / peak * 100 if peak > 0 else 0
            drawdown.append(dd)
        
        max_drawdown = max(drawdown)
        
        # Tính các chỉ số khác
        avg_win = total_profit / win_count if win_count > 0 else 0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0
        
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
        
        largest_win = max([t['profit'] for t in winning_trades]) if winning_trades else 0
        largest_loss = max([abs(t['profit']) for t in losing_trades]) if losing_trades else 0
        
        avg_trade = profit_loss / total_trades if total_trades > 0 else 0
        
        # Tính thời gian nắm giữ trung bình
        holding_times = []
        for trade in trades:
            if isinstance(trade['entry_time'], datetime) and isinstance(trade['exit_time'], datetime):
                holding_time = (trade['exit_time'] - trade['entry_time']).total_seconds() / 3600  # giờ
                holding_times.append(holding_time)
        
        avg_holding_time = np.mean(holding_times) if holding_times else 0
        
        # Tính Sharpe Ratio (đơn giản hóa)
        returns = [t['profit_pct'] for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'win_loss_ratio': win_loss_ratio,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'avg_trade': avg_trade,
            'avg_holding_time': avg_holding_time,
            'equity_curve': equity_curve
        }
    
    def analyze_by_market_condition(self, trades):
        """
        Phân tích hiệu suất theo điều kiện thị trường
        
        Args:
            trades (list): Danh sách các giao dịch
            
        Returns:
            dict: Kết quả phân tích theo điều kiện thị trường
        """
        # Phân loại giao dịch theo điều kiện thị trường
        trades_by_condition = {}
        
        for trade in trades:
            condition = trade.get('market_condition', 'UNKNOWN')
            if condition not in trades_by_condition:
                trades_by_condition[condition] = []
            
            trades_by_condition[condition].append(trade)
        
        # Tính toán chỉ số cho từng điều kiện
        results = {}
        
        for condition, condition_trades in trades_by_condition.items():
            total = len(condition_trades)
            winning = len([t for t in condition_trades if t['profit'] > 0])
            
            win_rate = (winning / total) * 100 if total > 0 else 0
            avg_profit = np.mean([t['profit_pct'] for t in condition_trades]) if condition_trades else 0
            
            results[condition] = {
                'total_trades': total,
                'winning_trades': winning,
                'win_rate': win_rate,
                'avg_profit_pct': avg_profit
            }
        
        return results
    
    def analyze_by_strategy(self, trades):
        """
        Phân tích hiệu suất theo loại chiến lược
        
        Args:
            trades (list): Danh sách các giao dịch
            
        Returns:
            dict: Kết quả phân tích theo loại chiến lược
        """
        # Phân loại giao dịch theo chiến lược
        trades_by_strategy = {}
        
        for trade in trades:
            strategy = trade.get('strategy', 'UNKNOWN')
            if strategy not in trades_by_strategy:
                trades_by_strategy[strategy] = []
            
            trades_by_strategy[strategy].append(trade)
        
        # Tính toán chỉ số cho từng chiến lược
        results = {}
        
        for strategy, strategy_trades in trades_by_strategy.items():
            total = len(strategy_trades)
            winning = len([t for t in strategy_trades if t['profit'] > 0])
            
            win_rate = (winning / total) * 100 if total > 0 else 0
            avg_profit = np.mean([t['profit_pct'] for t in strategy_trades]) if strategy_trades else 0
            
            results[strategy] = {
                'total_trades': total,
                'winning_trades': winning,
                'win_rate': win_rate,
                'avg_profit_pct': avg_profit
            }
        
        return results
    
    def plot_equity_curve(self, equity_curve, title="Equity Curve", save_path=None):
        """
        Vẽ biểu đồ equity curve
        
        Args:
            equity_curve (list): Danh sách giá trị số dư theo thời gian
            title (str): Tiêu đề biểu đồ
            save_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            matplotlib.figure.Figure: Đối tượng biểu đồ
        """
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve, linewidth=2)
        plt.title(title)
        plt.xlabel('Giao dịch')
        plt.ylabel('Số dư')
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Đã lưu biểu đồ vào {save_path}")
        
        return plt.gcf()
    
    def plot_drawdown_chart(self, equity_curve, initial_balance=10000, title="Drawdown Chart", save_path=None):
        """
        Vẽ biểu đồ drawdown
        
        Args:
            equity_curve (list): Danh sách giá trị số dư theo thời gian
            initial_balance (float): Số dư ban đầu
            title (str): Tiêu đề biểu đồ
            save_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            matplotlib.figure.Figure: Đối tượng biểu đồ
        """
        # Tính drawdown
        peak = initial_balance
        drawdown = []
        
        for balance in equity_curve:
            if balance > peak:
                peak = balance
            
            dd = (peak - balance) / peak * 100 if peak > 0 else 0
            drawdown.append(dd)
        
        plt.figure(figsize=(12, 6))
        plt.plot(drawdown, linewidth=2, color='red')
        plt.title(title)
        plt.xlabel('Giao dịch')
        plt.ylabel('Drawdown (%)')
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Đã lưu biểu đồ vào {save_path}")
        
        return plt.gcf()
    
    def plot_win_loss_distribution(self, trades, title="Win/Loss Distribution", save_path=None):
        """
        Vẽ biểu đồ phân phối lợi nhuận/lỗ
        
        Args:
            trades (list): Danh sách các giao dịch
            title (str): Tiêu đề biểu đồ
            save_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            matplotlib.figure.Figure: Đối tượng biểu đồ
        """
        profits = [t['profit_pct'] for t in trades]
        
        plt.figure(figsize=(12, 6))
        plt.hist(profits, bins=20, alpha=0.7)
        plt.axvline(x=0, color='red', linestyle='--')
        plt.title(title)
        plt.xlabel('Lợi nhuận/Lỗ (%)')
        plt.ylabel('Số lượng giao dịch')
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Đã lưu biểu đồ vào {save_path}")
        
        return plt.gcf()
    
    def plot_market_condition_performance(self, market_condition_results, title="Performance by Market Condition", save_path=None):
        """
        Vẽ biểu đồ hiệu suất theo điều kiện thị trường
        
        Args:
            market_condition_results (dict): Kết quả phân tích theo điều kiện thị trường
            title (str): Tiêu đề biểu đồ
            save_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            matplotlib.figure.Figure: Đối tượng biểu đồ
        """
        conditions = list(market_condition_results.keys())
        win_rates = [market_condition_results[c]['win_rate'] for c in conditions]
        avg_profits = [market_condition_results[c]['avg_profit_pct'] for c in conditions]
        
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 1, 1)
        plt.bar(conditions, win_rates, alpha=0.7, color='blue')
        plt.title('Win Rate (%) by Market Condition')
        plt.ylabel('Win Rate (%)')
        plt.grid(True)
        
        plt.subplot(2, 1, 2)
        plt.bar(conditions, avg_profits, alpha=0.7, color='green')
        plt.title('Average Profit (%) by Market Condition')
        plt.ylabel('Average Profit (%)')
        plt.grid(True)
        
        plt.tight_layout()
        plt.suptitle(title, fontsize=16, y=1.05)
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Đã lưu biểu đồ vào {save_path}")
        
        return plt.gcf()
    
    def plot_strategy_performance(self, strategy_results, title="Performance by Strategy", save_path=None):
        """
        Vẽ biểu đồ hiệu suất theo loại chiến lược
        
        Args:
            strategy_results (dict): Kết quả phân tích theo loại chiến lược
            title (str): Tiêu đề biểu đồ
            save_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            matplotlib.figure.Figure: Đối tượng biểu đồ
        """
        strategies = list(strategy_results.keys())
        win_rates = [strategy_results[s]['win_rate'] for s in strategies]
        avg_profits = [strategy_results[s]['avg_profit_pct'] for s in strategies]
        
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 1, 1)
        plt.bar(strategies, win_rates, alpha=0.7, color='blue')
        plt.title('Win Rate (%) by Strategy')
        plt.ylabel('Win Rate (%)')
        plt.grid(True)
        
        plt.subplot(2, 1, 2)
        plt.bar(strategies, avg_profits, alpha=0.7, color='green')
        plt.title('Average Profit (%) by Strategy')
        plt.ylabel('Average Profit (%)')
        plt.grid(True)
        
        plt.tight_layout()
        plt.suptitle(title, fontsize=16, y=1.05)
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Đã lưu biểu đồ vào {save_path}")
        
        return plt.gcf()
    
    def generate_performance_report(self, metrics, market_condition_results, strategy_results, report_path=None):
        """
        Tạo báo cáo hiệu suất
        
        Args:
            metrics (dict): Các chỉ số hiệu suất
            market_condition_results (dict): Kết quả phân tích theo điều kiện thị trường
            strategy_results (dict): Kết quả phân tích theo loại chiến lược
            report_path (str, optional): Đường dẫn lưu báo cáo
            
        Returns:
            str: Nội dung báo cáo
        """
        report = "# BÁO CÁO HIỆU SUẤT GIAO DỊCH\n\n"
        
        # Thông tin tổng quan
        report += "## THÔNG TIN TỔNG QUAN\n\n"
        report += f"- Tổng số giao dịch: {metrics['total_trades']}\n"
        report += f"- Tỷ lệ thắng: {metrics['win_rate']:.2f}%\n"
        report += f"- Lợi nhuận/Lỗ: {metrics['profit_loss']:.2f} ({metrics['profit_loss_pct']:.2f}%)\n"
        report += f"- Drawdown tối đa: {metrics['max_drawdown']:.2f}%\n"
        report += f"- Profit Factor: {metrics['profit_factor']:.2f}\n"
        report += f"- Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n\n"
        
        # Chi tiết giao dịch
        report += "## CHI TIẾT GIAO DỊCH\n\n"
        report += f"- Thắng trung bình: {metrics['avg_win']:.2f}\n"
        report += f"- Thua trung bình: {metrics['avg_loss']:.2f}\n"
        report += f"- Tỷ lệ thắng/thua: {metrics['win_loss_ratio']:.2f}\n"
        report += f"- Lợi nhuận lớn nhất: {metrics['largest_win']:.2f}\n"
        report += f"- Lỗ lớn nhất: {metrics['largest_loss']:.2f}\n"
        report += f"- Giao dịch trung bình: {metrics['avg_trade']:.2f}\n"
        report += f"- Thời gian nắm giữ trung bình: {metrics['avg_holding_time']:.2f} giờ\n\n"
        
        # Hiệu suất theo điều kiện thị trường
        report += "## HIỆU SUẤT THEO ĐIỀU KIỆN THỊ TRƯỜNG\n\n"
        report += "| Điều kiện | Số lượng | Thắng | Tỷ lệ thắng (%) | Lợi nhuận trung bình (%) |\n"
        report += "|-----------|----------|-------|----------------|---------------------------|\n"
        
        for condition, stats in market_condition_results.items():
            report += f"| {condition} | {stats['total_trades']} | {stats['winning_trades']} | "
            report += f"{stats['win_rate']:.2f} | {stats['avg_profit_pct']:.2f} |\n"
        
        report += "\n"
        
        # Hiệu suất theo chiến lược
        report += "## HIỆU SUẤT THEO CHIẾN LƯỢC\n\n"
        report += "| Chiến lược | Số lượng | Thắng | Tỷ lệ thắng (%) | Lợi nhuận trung bình (%) |\n"
        report += "|------------|----------|-------|----------------|---------------------------|\n"
        
        for strategy, stats in strategy_results.items():
            report += f"| {strategy} | {stats['total_trades']} | {stats['winning_trades']} | "
            report += f"{stats['win_rate']:.2f} | {stats['avg_profit_pct']:.2f} |\n"
        
        report += "\n"
        
        # Nhận xét và đánh giá
        report += "## NHẬN XÉT VÀ ĐÁNH GIÁ\n\n"
        
        if metrics['profit_loss_pct'] > 0:
            report += "- **Lợi nhuận:** Chiến lược đang có lợi nhuận dương. "
            
            if metrics['profit_factor'] > 2:
                report += "Profit factor > 2 cho thấy chiến lược có khả năng sinh lời tốt.\n"
            elif metrics['profit_factor'] > 1:
                report += "Profit factor > 1 nhưng < 2, chiến lược có lãi nhưng chưa thực sự mạnh.\n"
            else:
                report += "Profit factor < 1, cảnh báo rủi ro cao.\n"
        else:
            report += "- **Lợi nhuận:** Chiến lược đang lỗ. Cần xem xét lại các thông số và điều kiện thị trường.\n"
        
        report += f"- **Tỷ lệ thắng:** {metrics['win_rate']:.2f}%. "
        
        if metrics['win_rate'] > 60:
            report += "Tỷ lệ thắng tốt (>60%).\n"
        elif metrics['win_rate'] > 50:
            report += "Tỷ lệ thắng khá (>50%).\n"
        else:
            report += "Tỷ lệ thắng thấp (<50%), cần cải thiện khả năng dự đoán.\n"
        
        report += f"- **Drawdown:** Drawdown tối đa là {metrics['max_drawdown']:.2f}%. "
        
        if metrics['max_drawdown'] < 15:
            report += "Drawdown thấp, quản lý rủi ro tốt.\n"
        elif metrics['max_drawdown'] < 25:
            report += "Drawdown ở mức trung bình.\n"
        else:
            report += "Drawdown cao, cần cải thiện quản lý rủi ro.\n"
        
        # Lưu báo cáo
        if report_path:
            with open(report_path, 'w') as f:
                f.write(report)
            
            logger.info(f"Đã lưu báo cáo vào {report_path}")
        
        return report