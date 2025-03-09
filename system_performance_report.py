#!/usr/bin/env python3
"""
Báo cáo thống kê hiệu suất của hệ thống giao dịch

Script này tạo báo cáo phân tích chi tiết về hiệu suất của bot giao dịch,
bao gồm thống kê lãi/lỗ, tỷ lệ thành công, và đánh giá các chiến lược khác nhau.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import tabulate

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("performance_report.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("performance_report")

# Tạo thư mục báo cáo nếu chưa tồn tại
os.makedirs("reports", exist_ok=True)

class PerformanceAnalyzer:
    """Phân tích hiệu suất hệ thống giao dịch"""
    
    def __init__(self, backtest_files=None, result_dir="backtest_results"):
        """
        Khởi tạo công cụ phân tích hiệu suất
        
        Args:
            backtest_files (List[str], optional): Danh sách các file kết quả backtest
            result_dir (str): Thư mục chứa kết quả backtest
        """
        self.result_dir = result_dir
        
        if backtest_files:
            self.backtest_files = backtest_files
        else:
            # Tìm tất cả file JSON trong thư mục kết quả
            self.backtest_files = []
            for file in os.listdir(result_dir):
                if file.endswith(".json") and "results" in file:
                    self.backtest_files.append(os.path.join(result_dir, file))
                    
        logger.info(f"Tìm thấy {len(self.backtest_files)} file kết quả backtest")
        
        # Tải dữ liệu từ các file
        self.backtest_results = []
        for file_path in self.backtest_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    data['file_path'] = file_path
                    self.backtest_results.append(data)
                logger.info(f"Đã tải dữ liệu từ {file_path}")
            except Exception as e:
                logger.error(f"Lỗi khi tải {file_path}: {e}")
                
    def analyze_all_results(self):
        """
        Phân tích tất cả kết quả backtest đã tải
        
        Returns:
            Dict: Kết quả phân tích tổng hợp
        """
        all_stats = []
        
        for result in self.backtest_results:
            symbol = result.get('symbol', 'UNKNOWN')
            strategy = result.get('strategy', 'UNKNOWN')
            
            trades = result.get('trades', [])
            
            if not trades:
                logger.warning(f"Không có giao dịch trong {result['file_path']}")
                continue
                
            # Tạo DataFrame từ các giao dịch
            try:
                trades_df = pd.DataFrame(trades)
            except Exception as e:
                logger.error(f"Lỗi khi tạo DataFrame: {e}")
                logger.error(f"Cấu trúc giao dịch: {trades[0] if trades else None}")
                continue
                
            # Tính toán thống kê
            try:
                stats = self._calculate_performance_stats(trades_df, symbol, strategy, result)
                all_stats.append(stats)
            except Exception as e:
                logger.error(f"Lỗi khi tính toán thống kê: {e}")
                continue
                
        # Tổng hợp và so sánh các kết quả
        if all_stats:
            stats_df = pd.DataFrame(all_stats)
            
            # Sắp xếp theo profit_pct giảm dần
            stats_df = stats_df.sort_values('profit_pct', ascending=False)
            
            # Lưu kết quả tổng hợp
            report_path = "reports/performance_summary.csv"
            stats_df.to_csv(report_path, index=False)
            logger.info(f"Đã lưu báo cáo tổng hợp vào {report_path}")
            
            # Vẽ biểu đồ so sánh
            self._plot_comparison_charts(stats_df)
            
            return stats_df
        else:
            logger.warning("Không có kết quả phân tích")
            return None
            
    def _calculate_performance_stats(self, trades_df, symbol, strategy, result):
        """
        Tính toán thống kê hiệu suất từ DataFrame giao dịch
        
        Args:
            trades_df (DataFrame): DataFrame chứa các giao dịch
            symbol (str): Mã cặp giao dịch
            strategy (str): Tên chiến lược
            result (Dict): Dữ liệu kết quả gốc
            
        Returns:
            Dict: Thống kê hiệu suất
        """
        # Chuẩn hóa tên cột nếu cần
        if 'pnl' not in trades_df.columns and 'profit' in trades_df.columns:
            trades_df['pnl'] = trades_df['profit']
            
        if 'side' not in trades_df.columns and 'position' in trades_df.columns:
            trades_df['side'] = trades_df['position']
            
        stats = {
            'symbol': symbol,
            'strategy': strategy,
            'file_path': result['file_path']
        }
        
        # Thông tin cơ bản
        stats['total_trades'] = len(trades_df)
        stats['profitable_trades'] = sum(trades_df['pnl'] > 0)
        stats['losing_trades'] = sum(trades_df['pnl'] <= 0)
        
        if stats['total_trades'] > 0:
            stats['win_rate'] = stats['profitable_trades'] / stats['total_trades']
        else:
            stats['win_rate'] = 0
            
        # Thống kê lãi/lỗ
        stats['total_profit'] = trades_df['pnl'].sum()
        
        if 'entry_price' in trades_df.columns and 'quantity' in trades_df.columns:
            total_investment = (trades_df['entry_price'] * trades_df['quantity']).sum()
            if total_investment > 0:
                stats['profit_pct'] = (stats['total_profit'] / total_investment) * 100
            else:
                stats['profit_pct'] = 0
        elif 'initial_balance' in result:
            stats['profit_pct'] = (stats['total_profit'] / result['initial_balance']) * 100
        else:
            stats['profit_pct'] = 0
            
        # Thống kê nâng cao
        if stats['profitable_trades'] > 0:
            profitable_trades = trades_df[trades_df['pnl'] > 0]
            stats['avg_profit'] = profitable_trades['pnl'].mean()
            stats['max_profit'] = profitable_trades['pnl'].max()
        else:
            stats['avg_profit'] = 0
            stats['max_profit'] = 0
            
        if stats['losing_trades'] > 0:
            losing_trades = trades_df[trades_df['pnl'] <= 0]
            stats['avg_loss'] = losing_trades['pnl'].mean()
            stats['max_loss'] = losing_trades['pnl'].min()
        else:
            stats['avg_loss'] = 0
            stats['max_loss'] = 0
            
        # Profit factor (lợi nhuận tích cực / tổn thất tiêu cực)
        total_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        total_loss = abs(trades_df[trades_df['pnl'] <= 0]['pnl'].sum())
        
        if total_loss > 0:
            stats['profit_factor'] = total_profit / total_loss
        else:
            stats['profit_factor'] = float('inf') if total_profit > 0 else 0
            
        # Phân tích theo phía giao dịch
        if 'side' in trades_df.columns:
            buy_trades = trades_df[trades_df['side'].str.upper() == 'BUY']
            sell_trades = trades_df[trades_df['side'].str.upper() == 'SELL']
            
            stats['buy_trades'] = len(buy_trades)
            stats['buy_win_rate'] = sum(buy_trades['pnl'] > 0) / len(buy_trades) if len(buy_trades) > 0 else 0
            stats['buy_profit'] = buy_trades['pnl'].sum()
            
            stats['sell_trades'] = len(sell_trades)
            stats['sell_win_rate'] = sum(sell_trades['pnl'] > 0) / len(sell_trades) if len(sell_trades) > 0 else 0
            stats['sell_profit'] = sell_trades['pnl'].sum()
        
        # Tính toán thời gian nắm giữ
        if 'entry_time' in trades_df.columns and 'exit_time' in trades_df.columns:
            try:
                # Chuyển đổi chuỗi thành datetime nếu cần
                if isinstance(trades_df['entry_time'].iloc[0], str):
                    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
                if isinstance(trades_df['exit_time'].iloc[0], str):
                    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
                
                # Tính toán thời gian nắm giữ (giờ)
                trades_df['holding_time'] = (trades_df['exit_time'] - trades_df['entry_time']).dt.total_seconds() / 3600
                
                stats['avg_holding_time'] = trades_df['holding_time'].mean()
                stats['max_holding_time'] = trades_df['holding_time'].max()
                stats['min_holding_time'] = trades_df['holding_time'].min()
            except Exception as e:
                logger.warning(f"Không thể tính thời gian nắm giữ: {e}")
                
        # Tính drawdown nếu có dữ liệu
        if 'balance_history' in result:
            try:
                balance_history = result['balance_history']
                balances = [entry['balance'] for entry in balance_history]
                
                # Tính drawdown tối đa
                peak = balances[0]
                max_drawdown = 0
                max_drawdown_pct = 0
                
                for balance in balances:
                    if balance > peak:
                        peak = balance
                    drawdown = peak - balance
                    drawdown_pct = drawdown / peak * 100 if peak > 0 else 0
                    
                    if drawdown_pct > max_drawdown_pct:
                        max_drawdown = drawdown
                        max_drawdown_pct = drawdown_pct
                        
                stats['max_drawdown'] = max_drawdown
                stats['max_drawdown_pct'] = max_drawdown_pct
            except Exception as e:
                logger.warning(f"Không thể tính drawdown: {e}")
        
        # Thêm thống kê từ summary nếu có
        if 'summary' in result:
            summary = result['summary']
            for key, value in summary.items():
                if key not in stats:
                    stats[key] = value
                    
        return stats
        
    def _plot_comparison_charts(self, stats_df):
        """
        Vẽ biểu đồ so sánh hiệu suất
        
        Args:
            stats_df (DataFrame): DataFrame chứa thống kê hiệu suất
        """
        try:
            # Tạo thư mục charts nếu chưa tồn tại
            os.makedirs("reports/charts", exist_ok=True)
            
            # 1. Biểu đồ so sánh Profit %
            plt.figure(figsize=(12, 8))
            plt.bar(stats_df['strategy'], stats_df['profit_pct'])
            plt.title('So sánh % Lợi nhuận')
            plt.ylabel('Lợi nhuận (%)')
            plt.xlabel('Chiến lược')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig("reports/charts/profit_comparison.png")
            plt.close()
            
            # 2. Biểu đồ so sánh Win Rate
            plt.figure(figsize=(12, 8))
            plt.bar(stats_df['strategy'], stats_df['win_rate'] * 100)
            plt.title('So sánh Win Rate')
            plt.ylabel('Win Rate (%)')
            plt.xlabel('Chiến lược')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig("reports/charts/winrate_comparison.png")
            plt.close()
            
            # 3. Biểu đồ so sánh Profit Factor
            plt.figure(figsize=(12, 8))
            # Giới hạn profit factor để dễ nhìn
            profit_factors = [min(pf, 10) for pf in stats_df['profit_factor']]
            plt.bar(stats_df['strategy'], profit_factors)
            plt.title('So sánh Profit Factor (cắt ở mức 10)')
            plt.ylabel('Profit Factor')
            plt.xlabel('Chiến lược')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig("reports/charts/profit_factor_comparison.png")
            plt.close()
            
            # 4. Biểu đồ so sánh Drawdown
            if 'max_drawdown_pct' in stats_df.columns:
                plt.figure(figsize=(12, 8))
                plt.bar(stats_df['strategy'], stats_df['max_drawdown_pct'])
                plt.title('So sánh Drawdown tối đa')
                plt.ylabel('Drawdown (%)')
                plt.xlabel('Chiến lược')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                plt.savefig("reports/charts/drawdown_comparison.png")
                plt.close()
                
            logger.info("Đã tạo các biểu đồ so sánh")
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ: {e}")
            
    def analyze_market_regimes(self):
        """
        Phân tích hiệu suất theo chế độ thị trường
        
        Returns:
            Dict: Kết quả phân tích theo chế độ thị trường
        """
        regime_stats = {}
        
        for result in self.backtest_results:
            # Kiểm tra xem có dữ liệu về chế độ thị trường không
            if 'regime_stats' not in result and 'regime_history' not in result:
                continue
                
            trades = result.get('trades', [])
            if not trades:
                continue
                
            # Trích xuất dữ liệu chế độ thị trường
            if 'regime_stats' in result:
                for regime, count in result['regime_stats'].items():
                    if regime not in regime_stats:
                        regime_stats[regime] = {
                            'count': 0,
                            'trades': 0,
                            'profit': 0,
                            'wins': 0,
                            'losses': 0
                        }
                    regime_stats[regime]['count'] += count
            
            # Phân tích giao dịch theo chế độ thị trường
            if 'regime_history' in result:
                regime_history = result['regime_history']
                
                # Tạo ánh xạ thời gian -> chế độ
                time_to_regime = {}
                for entry in regime_history:
                    time_str = entry['time']
                    try:
                        if isinstance(time_str, str):
                            time = pd.to_datetime(time_str)
                        else:
                            time = time_str
                        time_to_regime[time] = entry['regime']
                    except Exception as e:
                        logger.warning(f"Không thể chuyển đổi thời gian: {e}")
                
                # Phân tích mỗi giao dịch
                for trade in trades:
                    entry_time = trade.get('entry_time')
                    
                    # Tìm chế độ thị trường gần nhất
                    if entry_time:
                        try:
                            if isinstance(entry_time, str):
                                entry_time = pd.to_datetime(entry_time)
                                
                            # Tìm thời điểm gần nhất trong time_to_regime
                            closest_time = min(time_to_regime.keys(), 
                                              key=lambda x: abs((x - entry_time).total_seconds()))
                            regime = time_to_regime[closest_time]
                            
                            # Cập nhật thống kê
                            if regime not in regime_stats:
                                regime_stats[regime] = {
                                    'count': 0,
                                    'trades': 0,
                                    'profit': 0,
                                    'wins': 0,
                                    'losses': 0
                                }
                                
                            regime_stats[regime]['trades'] += 1
                            
                            pnl = trade.get('pnl', 0)
                            regime_stats[regime]['profit'] += pnl
                            
                            if pnl > 0:
                                regime_stats[regime]['wins'] += 1
                            else:
                                regime_stats[regime]['losses'] += 1
                        except Exception as e:
                            logger.warning(f"Lỗi khi phân tích giao dịch: {e}")
        
        # Tính toán win rate và profit per trade
        for regime, stats in regime_stats.items():
            if stats['trades'] > 0:
                stats['win_rate'] = stats['wins'] / stats['trades']
                stats['profit_per_trade'] = stats['profit'] / stats['trades']
            else:
                stats['win_rate'] = 0
                stats['profit_per_trade'] = 0
                
        # Tạo báo cáo
        if regime_stats:
            # Chuyển thành DataFrame
            regime_df = pd.DataFrame.from_dict(regime_stats, orient='index')
            
            # Sắp xếp theo profit_per_trade
            regime_df = regime_df.sort_values('profit_per_trade', ascending=False)
            
            # Lưu kết quả
            report_path = "reports/regime_analysis.csv"
            regime_df.to_csv(report_path)
            logger.info(f"Đã lưu phân tích chế độ thị trường vào {report_path}")
            
            # Vẽ biểu đồ
            self._plot_regime_charts(regime_df)
            
            return regime_df
        else:
            logger.warning("Không có dữ liệu về chế độ thị trường")
            return None
            
    def _plot_regime_charts(self, regime_df):
        """
        Vẽ biểu đồ phân tích chế độ thị trường
        
        Args:
            regime_df (DataFrame): DataFrame chứa thống kê theo chế độ thị trường
        """
        try:
            # Tạo thư mục charts nếu chưa tồn tại
            os.makedirs("reports/charts", exist_ok=True)
            
            # 1. Biểu đồ Win Rate theo chế độ thị trường
            plt.figure(figsize=(10, 6))
            plt.bar(regime_df.index, regime_df['win_rate'] * 100)
            plt.title('Win Rate theo chế độ thị trường')
            plt.ylabel('Win Rate (%)')
            plt.xlabel('Chế độ thị trường')
            plt.tight_layout()
            plt.savefig("reports/charts/regime_winrate.png")
            plt.close()
            
            # 2. Biểu đồ Profit per Trade theo chế độ thị trường
            plt.figure(figsize=(10, 6))
            plt.bar(regime_df.index, regime_df['profit_per_trade'])
            plt.title('Lợi nhuận trung bình mỗi giao dịch theo chế độ thị trường')
            plt.ylabel('Lợi nhuận trung bình')
            plt.xlabel('Chế độ thị trường')
            plt.tight_layout()
            plt.savefig("reports/charts/regime_profit.png")
            plt.close()
            
            # 3. Biểu đồ số lượng giao dịch theo chế độ thị trường
            plt.figure(figsize=(10, 6))
            plt.bar(regime_df.index, regime_df['trades'])
            plt.title('Số lượng giao dịch theo chế độ thị trường')
            plt.ylabel('Số lượng giao dịch')
            plt.xlabel('Chế độ thị trường')
            plt.tight_layout()
            plt.savefig("reports/charts/regime_trade_count.png")
            plt.close()
            
            logger.info("Đã tạo các biểu đồ phân tích chế độ thị trường")
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ chế độ thị trường: {e}")
    
    def create_full_report(self):
        """Tạo báo cáo đầy đủ về hiệu suất hệ thống giao dịch"""
        report_lines = [
            "# BÁO CÁO HIỆU SUẤT HỆ THỐNG GIAO DỊCH BITCOIN",
            f"Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. Thống kê tổng quát\n"
        ]
        
        # Phân tích hiệu suất
        stats_df = self.analyze_all_results()
        
        if stats_df is not None:
            # Số liệu tổng quát
            total_trades = stats_df['total_trades'].sum()
            total_profit = stats_df['total_profit'].sum()
            avg_win_rate = stats_df['win_rate'].mean()
            best_strategy = stats_df.iloc[0]['strategy']
            worst_strategy = stats_df.iloc[-1]['strategy']
            
            report_lines.extend([
                f"- Tổng số giao dịch: {total_trades}",
                f"- Tổng lợi nhuận: ${total_profit:.2f}",
                f"- Win Rate trung bình: {avg_win_rate:.2%}",
                f"- Chiến lược tốt nhất: {best_strategy} ({stats_df.iloc[0]['profit_pct']:.2f}%)",
                f"- Chiến lược kém nhất: {worst_strategy} ({stats_df.iloc[-1]['profit_pct']:.2f}%)"
            ])
            
            # Bảng thống kê
            report_lines.append("\n## 2. So sánh chi tiết các chiến lược\n")
            
            # Chọn và định dạng các cột quan trọng
            display_columns = ['strategy', 'total_trades', 'win_rate', 'profit_pct', 
                              'profit_factor', 'avg_profit', 'avg_loss']
            
            if 'max_drawdown_pct' in stats_df.columns:
                display_columns.append('max_drawdown_pct')
                
            display_df = stats_df[display_columns].copy()
            
            # Định dạng các cột
            display_df['win_rate'] = display_df['win_rate'].apply(lambda x: f"{x:.2%}")
            display_df['profit_pct'] = display_df['profit_pct'].apply(lambda x: f"{x:.2f}%")
            display_df['profit_factor'] = display_df['profit_factor'].apply(lambda x: f"{x:.2f}")
            display_df['avg_profit'] = display_df['avg_profit'].apply(lambda x: f"${x:.2f}")
            display_df['avg_loss'] = display_df['avg_loss'].apply(lambda x: f"${x:.2f}")
            
            if 'max_drawdown_pct' in display_df.columns:
                display_df['max_drawdown_pct'] = display_df['max_drawdown_pct'].apply(lambda x: f"{x:.2f}%")
                
            # Đổi tên cột cho dễ đọc
            display_df.columns = ['Chiến lược', 'Số giao dịch', 'Win Rate', 'Lợi nhuận %', 
                                'Profit Factor', 'Lãi TB', 'Lỗ TB']
            
            if 'max_drawdown_pct' in display_df.columns:
                display_df = display_df.rename(columns={'max_drawdown_pct': 'Drawdown tối đa'})
                
            # Chuyển thành bảng Markdown
            table = tabulate.tabulate(display_df, headers='keys', tablefmt='pipe', showindex=False)
            report_lines.append(table)
            
            # Phân tích theo chế độ thị trường
            report_lines.append("\n## 3. Phân tích theo chế độ thị trường\n")
            
            regime_df = self.analyze_market_regimes()
            
            if regime_df is not None:
                # Định dạng các cột
                display_regime = regime_df.copy()
                display_regime['win_rate'] = display_regime['win_rate'].apply(lambda x: f"{x:.2%}")
                display_regime['profit_per_trade'] = display_regime['profit_per_trade'].apply(lambda x: f"${x:.2f}")
                
                # Đổi tên cột cho dễ đọc
                display_regime = display_regime.rename(columns={
                    'count': 'Số lần xuất hiện',
                    'trades': 'Số giao dịch',
                    'profit': 'Tổng lợi nhuận',
                    'wins': 'Giao dịch thắng',
                    'losses': 'Giao dịch thua',
                    'win_rate': 'Win Rate',
                    'profit_per_trade': 'Lợi nhuận/Giao dịch'
                })
                
                # Chuyển thành bảng Markdown
                regime_table = tabulate.tabulate(display_regime, headers='keys', tablefmt='pipe')
                report_lines.append(regime_table)
                
                # Phân tích chi tiết từng chế độ
                best_regime = regime_df['profit_per_trade'].idxmax()
                worst_regime = regime_df['profit_per_trade'].idxmin()
                
                report_lines.extend([
                    f"\n### Phân tích chi tiết các chế độ thị trường",
                    f"\n#### Chế độ thị trường tốt nhất: {best_regime}",
                    f"- Lợi nhuận trung bình: ${regime_df.loc[best_regime, 'profit_per_trade']:.2f}",
                    f"- Win Rate: {regime_df.loc[best_regime, 'win_rate']:.2%}",
                    f"- Số giao dịch: {regime_df.loc[best_regime, 'trades']}",
                    
                    f"\n#### Chế độ thị trường kém nhất: {worst_regime}",
                    f"- Lợi nhuận trung bình: ${regime_df.loc[worst_regime, 'profit_per_trade']:.2f}",
                    f"- Win Rate: {regime_df.loc[worst_regime, 'win_rate']:.2%}",
                    f"- Số giao dịch: {regime_df.loc[worst_regime, 'trades']}"
                ])
            else:
                report_lines.append("Không có dữ liệu về chế độ thị trường")
                
            # Thêm hình ảnh vào báo cáo
            report_lines.extend([
                "\n## 4. Biểu đồ phân tích\n",
                "### So sánh lợi nhuận các chiến lược",
                "![Profit Comparison](charts/profit_comparison.png)\n",
                
                "### So sánh Win Rate của các chiến lược",
                "![WinRate Comparison](charts/winrate_comparison.png)\n",
                
                "### So sánh Profit Factor của các chiến lược",
                "![Profit Factor Comparison](charts/profit_factor_comparison.png)\n"
            ])
            
            if os.path.exists("reports/charts/drawdown_comparison.png"):
                report_lines.extend([
                    "### So sánh Drawdown của các chiến lược",
                    "![Drawdown Comparison](charts/drawdown_comparison.png)\n"
                ])
                
            if os.path.exists("reports/charts/regime_winrate.png"):
                report_lines.extend([
                    "### Win Rate theo chế độ thị trường",
                    "![Regime WinRate](charts/regime_winrate.png)\n",
                    
                    "### Lợi nhuận theo chế độ thị trường",
                    "![Regime Profit](charts/regime_profit.png)\n",
                    
                    "### Số lượng giao dịch theo chế độ thị trường",
                    "![Regime Trade Count](charts/regime_trade_count.png)\n"
                ])
                
            # Thêm phần kết luận
            report_lines.append("\n## 5. Kết luận và Khuyến nghị\n")
            
            # Chiến lược tốt nhất
            best_strategy_stats = stats_df.iloc[0]
            report_lines.extend([
                f"### Chiến lược tốt nhất: {best_strategy}",
                f"- Lợi nhuận: {best_strategy_stats['profit_pct']:.2f}%",
                f"- Win Rate: {best_strategy_stats['win_rate']:.2%}",
                f"- Profit Factor: {best_strategy_stats['profit_factor']:.2f}",
                f"- Số giao dịch: {best_strategy_stats['total_trades']}"
            ])
            
            # Khuyến nghị dựa trên phân tích
            report_lines.append("\n### Khuyến nghị:")
            
            # Thêm khuyến nghị dựa trên kết quả phân tích
            if regime_df is not None:
                best_regime = regime_df['profit_per_trade'].idxmax()
                report_lines.append(f"1. Tập trung giao dịch trong chế độ thị trường {best_regime} để tối đa hóa lợi nhuận")
                
            report_lines.extend([
                f"2. Sử dụng chiến lược {best_strategy} làm chiến lược chính",
                "3. Đánh giá lại và điều chỉnh các tham số để cải thiện hiệu suất",
                "4. Tiếp tục cải thiện quản lý rủi ro để giảm drawdown"
            ])
        else:
            report_lines.append("Không có dữ liệu để phân tích")
            
        # Lưu báo cáo
        report_content = "\n".join(report_lines)
        report_path = "reports/performance_report.md"
        
        with open(report_path, 'w') as f:
            f.write(report_content)
            
        logger.info(f"Đã tạo báo cáo đầy đủ tại {report_path}")
        
        return report_path

def create_performance_report():
    """Tạo báo cáo hiệu suất"""
    analyzer = PerformanceAnalyzer()
    report_path = analyzer.create_full_report()
    
    print(f"Đã tạo báo cáo hiệu suất tại: {report_path}")
    
    # Hiển thị báo cáo tóm tắt
    print("\nTÓM TẮT BÁO CÁO HIỆU SUẤT:")
    
    stats_df = analyzer.analyze_all_results()
    if stats_df is not None:
        # Hiển thị top 3 chiến lược
        top_strategies = stats_df.head(3)
        print("\nTop 3 chiến lược hiệu quả nhất:")
        for i, (_, row) in enumerate(top_strategies.iterrows(), 1):
            print(f"{i}. {row['strategy']} - Lợi nhuận: {row['profit_pct']:.2f}%, Win Rate: {row['win_rate']:.2%}")
            
        # Hiển thị thống kê tổng quát
        print(f"\nTổng số giao dịch: {stats_df['total_trades'].sum()}")
        print(f"Tổng lợi nhuận: ${stats_df['total_profit'].sum():.2f}")
        print(f"Win Rate trung bình: {stats_df['win_rate'].mean():.2%}")
        
        # Hiển thị thống kê chế độ thị trường
        regime_df = analyzer.analyze_market_regimes()
        if regime_df is not None:
            print("\nHiệu suất theo chế độ thị trường:")
            for regime, row in regime_df.iterrows():
                print(f"- {regime}: Win Rate={row['win_rate']:.2%}, P&L/Trade=${row['profit_per_trade']:.2f}")
    else:
        print("Không có dữ liệu để phân tích")
        
    return report_path

if __name__ == "__main__":
    create_performance_report()