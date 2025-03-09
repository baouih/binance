#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script phân tích hiệu suất theo chế độ thị trường từ kết quả backtest

Script này tải các kết quả backtest, phân tích hiệu suất theo từng chế độ thị trường,
và tạo các báo cáo và biểu đồ để so sánh hiệu suất.
"""

import os
import json
import glob
import logging
import sys
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('market_regime_analysis.log')
    ]
)

logger = logging.getLogger('market_regime_analyzer')

# Đảm bảo thư mục kết quả tồn tại
os.makedirs("reports/market_regime", exist_ok=True)
os.makedirs("charts/market_regime", exist_ok=True)

class MarketRegimePerformanceAnalyzer:
    """Lớp phân tích hiệu suất theo chế độ thị trường"""
    
    def __init__(self, results_dir='backtest_results'):
        """
        Khởi tạo phân tích
        
        Args:
            results_dir (str): Thư mục chứa kết quả backtest
        """
        self.results_dir = results_dir
        
    def analyze_market_regimes(self, backtest_result=None, symbol=None, timeframe=None, period_name=None):
        """
        Phân tích hiệu suất dựa trên các chế độ thị trường từ kết quả backtest
        
        Args:
            backtest_result (Dict): Kết quả backtest
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            period_name (str): Tên khoảng thời gian
        
        Returns:
            Dict: Kết quả phân tích theo market regime
        """
        logger = logging.getLogger('regime_analyzer')
        
        if not backtest_result:
            logger.warning("Không có kết quả backtest để phân tích")
            return None
        
        # Tạo thư mục reports nếu chưa tồn tại
        os.makedirs("reports", exist_ok=True)
        
        # Phân tích trades theo market regime
        trades = backtest_result.get('trades', [])
        
        if not trades:
            logger.warning("Không có giao dịch trong kết quả backtest")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'period_name': period_name,
                'regimes': {}
            }
        
        # Thống kê theo regime
        regime_stats = {}
        
        for trade in trades:
            regime = trade.get('market_regime', 'unknown')
            
            if regime not in regime_stats:
                regime_stats[regime] = {
                    'trade_count': 0,
                    'win_count': 0,
                    'loss_count': 0,
                    'profit_sum': 0,
                    'loss_sum': 0,
                    'pnl_amount': 0,
                    'max_profit': 0,
                    'max_loss': 0
                }
            
            stats = regime_stats[regime]
            stats['trade_count'] += 1
            pnl = trade.get('pnl_amount', 0)
            stats['pnl_amount'] += pnl
            
            if pnl > 0:
                stats['win_count'] += 1
                stats['profit_sum'] += pnl
                stats['max_profit'] = max(stats['max_profit'], pnl)
            else:
                stats['loss_count'] += 1
                stats['loss_sum'] += pnl
                stats['max_loss'] = min(stats['max_loss'], pnl)
        
        # Tính các chỉ số hiệu suất cho mỗi regime
        regime_performance = {}
        total_trades = len(trades)
        
        for regime, stats in regime_stats.items():
            win_rate = stats['win_count'] / stats['trade_count'] * 100 if stats['trade_count'] > 0 else 0
            profit_factor = abs(stats['profit_sum'] / stats['loss_sum']) if stats['loss_sum'] != 0 else float('inf')
            
            regime_performance[regime] = {
                'trade_count': stats['trade_count'],
                'percentage': stats['trade_count'] / total_trades * 100,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'profit_percentage': (stats['pnl_amount'] / backtest_result.get('initial_balance', 10000)) * 100,
                'avg_profit': stats['profit_sum'] / stats['win_count'] if stats['win_count'] > 0 else 0,
                'avg_loss': stats['loss_sum'] / stats['loss_count'] if stats['loss_count'] > 0 else 0,
                'max_profit': stats['max_profit'],
                'max_loss': stats['max_loss'],
                'pnl_amount': stats['pnl_amount']
            }
        
        # Tính các chỉ số đánh giá regime
        regime_evaluation = {}
        
        for regime, perf in regime_performance.items():
            evaluation_score = (
                perf['win_rate'] * 0.4 + 
                min(perf['profit_factor'] * 10, 50) * 0.3 + 
                perf['profit_percentage'] * 0.3
            )
            
            regime_evaluation[regime] = {
                'score': evaluation_score,
                'recommendation': 'Rất tốt' if evaluation_score > 75 else
                                'Tốt' if evaluation_score > 50 else
                                'Trung bình' if evaluation_score > 25 else
                                'Kém'
            }
        
        # Kết quả phân tích
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'period_name': period_name,
            'total_trades': total_trades,
            'regimes': regime_performance,
            'evaluation': regime_evaluation
        }
        
        # Tạo biểu đồ và lưu kết quả
        self._create_regime_chart(result, f"{symbol}_{timeframe}_{period_name}")
        
        logger.info(f"Đã hoàn thành phân tích market regime cho {symbol} {timeframe} ({period_name})")
        
        return result
        
    def _create_regime_chart(self, analysis, chart_name):
        """Tạo biểu đồ hiệu suất theo regime"""
        if not analysis or 'regimes' not in analysis:
            return
            
        try:
            regimes = list(analysis['regimes'].keys())
            percentages = [analysis['regimes'][r]['percentage'] for r in regimes]
            win_rates = [analysis['regimes'][r]['win_rate'] for r in regimes]
            profit_pcts = [analysis['regimes'][r]['profit_percentage'] for r in regimes]
            
            # Thiết lập biểu đồ
            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
            
            # 1. Biểu đồ tỉ lệ xuất hiện
            ax1.bar(regimes, percentages, color='skyblue')
            ax1.set_title('Tỉ lệ xuất hiện của các Market Regime')
            ax1.set_ylabel('Phần trăm (%)')
            ax1.set_ylim(0, 100)
            
            # 2. Biểu đồ win rate
            ax2.bar(regimes, win_rates, color='lightgreen')
            ax2.set_title('Win Rate theo Market Regime')
            ax2.set_ylabel('Win Rate (%)')
            ax2.set_ylim(0, 100)
            
            # 3. Biểu đồ lợi nhuận
            ax3.bar(regimes, profit_pcts, color='salmon')
            ax3.set_title('Lợi nhuận (%) theo Market Regime')
            ax3.set_ylabel('Lợi nhuận (%)')
            
            plt.tight_layout()
            plt.savefig(f"backtest_charts/regime_analysis_{chart_name}.png")
            plt.close()
        except Exception as e:
            logging.warning(f"Không thể tạo biểu đồ regime: {e}")
        self.results = []
        self.regime_metrics = {}
        self.regime_trades = {}
        self.all_trades = []
        self.regime_names = ['trending', 'ranging', 'volatile', 'quiet']
        
        # Màu sắc cho các chế độ thị trường
        self.regime_colors = {
            'trending': '#2E86C1',  # Xanh dương
            'ranging': '#27AE60',   # Xanh lá
            'volatile': '#E74C3C',  # Đỏ
            'quiet': '#F39C12'      # Cam
        }
    
    def load_results(self, symbol=None, interval=None):
        """
        Tải kết quả backtest
        
        Args:
            symbol (str, optional): Lọc theo cặp tiền
            interval (str, optional): Lọc theo khung thời gian
            
        Returns:
            bool: True nếu tải thành công ít nhất một kết quả
        """
        pattern = os.path.join(self.results_dir, "*.json")
        result_files = glob.glob(pattern)
        
        if not result_files:
            logger.warning(f"Không tìm thấy file kết quả nào trong {self.results_dir}")
            return False
        
        logger.info(f"Tìm thấy {len(result_files)} file kết quả trong {self.results_dir}")
        
        for file_path in result_files:
            try:
                with open(file_path, 'r') as f:
                    result_data = json.load(f)
                
                # Lọc theo symbol và interval nếu có
                if symbol and result_data.get('symbol') != symbol:
                    continue
                    
                if interval and result_data.get('interval') != interval:
                    continue
                
                # Thêm vào danh sách kết quả
                self.results.append(result_data)
                
                # Thu thập tất cả các giao dịch
                if 'trades' in result_data:
                    for trade in result_data['trades']:
                        trade['symbol'] = result_data.get('symbol')
                        trade['interval'] = result_data.get('interval')
                        trade['risk_percentage'] = result_data.get('risk_percentage')
                        trade['analysis_period'] = result_data.get('analysis_period')
                        self.all_trades.append(trade)
                
            except Exception as e:
                logger.error(f"Lỗi khi tải file {file_path}: {str(e)}")
        
        logger.info(f"Đã tải {len(self.results)} kết quả thỏa mãn điều kiện")
        
        if not self.results:
            return False
        
        return True
    
    def analyze_regime_performance(self):
        """
        Phân tích hiệu suất theo chế độ thị trường
        
        Returns:
            Dict: Kết quả phân tích theo chế độ thị trường
        """
        if not self.results:
            logger.warning("Không có kết quả để phân tích")
            return {}
        
        # Khởi tạo metrics cho từng chế độ
        for regime in self.regime_names:
            self.regime_metrics[regime] = {
                'trade_count': 0,
                'win_count': 0,
                'loss_count': 0,
                'profit_sum': 0.0,
                'loss_sum': 0.0,
                'max_profit': 0.0,
                'max_loss': 0.0,
                'avg_holding_time_win': [],
                'avg_holding_time_loss': [],
                'total_trades': []
            }
        
        # Phân tích các giao dịch theo chế độ thị trường
        for trade in self.all_trades:
            regime = trade.get('market_regime', 'unknown')
            if regime not in self.regime_metrics:
                self.regime_metrics[regime] = {
                    'trade_count': 0,
                    'win_count': 0,
                    'loss_count': 0,
                    'profit_sum': 0.0,
                    'loss_sum': 0.0,
                    'max_profit': 0.0,
                    'max_loss': 0.0,
                    'avg_holding_time_win': [],
                    'avg_holding_time_loss': [],
                    'total_trades': []
                }
            
            self.regime_metrics[regime]['trade_count'] += 1
            self.regime_metrics[regime]['total_trades'].append(trade)
            
            profit_pct = trade.get('profit_percentage', 0)
            if profit_pct > 0:
                self.regime_metrics[regime]['win_count'] += 1
                self.regime_metrics[regime]['profit_sum'] += profit_pct
                self.regime_metrics[regime]['max_profit'] = max(self.regime_metrics[regime]['max_profit'], profit_pct)
                
                # Thời gian giữ
                if 'holding_time_hours' in trade:
                    self.regime_metrics[regime]['avg_holding_time_win'].append(trade['holding_time_hours'])
            else:
                self.regime_metrics[regime]['loss_count'] += 1
                self.regime_metrics[regime]['loss_sum'] += abs(profit_pct)
                self.regime_metrics[regime]['max_loss'] = max(self.regime_metrics[regime]['max_loss'], abs(profit_pct))
                
                # Thời gian giữ
                if 'holding_time_hours' in trade:
                    self.regime_metrics[regime]['avg_holding_time_loss'].append(trade['holding_time_hours'])
        
        # Tính toán các metrics tổng hợp
        for regime, metrics in self.regime_metrics.items():
            if metrics['trade_count'] > 0:
                metrics['win_rate'] = metrics['win_count'] / metrics['trade_count'] * 100 if metrics['trade_count'] > 0 else 0
                metrics['profit_factor'] = metrics['profit_sum'] / metrics['loss_sum'] if metrics['loss_sum'] > 0 else float('inf')
                metrics['avg_profit'] = metrics['profit_sum'] / metrics['win_count'] if metrics['win_count'] > 0 else 0
                metrics['avg_loss'] = metrics['loss_sum'] / metrics['loss_count'] if metrics['loss_count'] > 0 else 0
                metrics['expectancy'] = ((metrics['win_rate'] / 100) * metrics['avg_profit']) - ((1 - metrics['win_rate'] / 100) * metrics['avg_loss'])
                
                # Thời gian giữ trung bình
                metrics['avg_holding_time_win'] = sum(metrics['avg_holding_time_win']) / len(metrics['avg_holding_time_win']) if metrics['avg_holding_time_win'] else 0
                metrics['avg_holding_time_loss'] = sum(metrics['avg_holding_time_loss']) / len(metrics['avg_holding_time_loss']) if metrics['avg_holding_time_loss'] else 0
            else:
                metrics['win_rate'] = 0
                metrics['profit_factor'] = 0
                metrics['avg_profit'] = 0
                metrics['avg_loss'] = 0
                metrics['expectancy'] = 0
                metrics['avg_holding_time_win'] = 0
                metrics['avg_holding_time_loss'] = 0
        
        return self.regime_metrics
    
    def create_regime_performance_chart(self):
        """
        Tạo biểu đồ hiệu suất theo chế độ thị trường
        """
        if not self.regime_metrics:
            logger.warning("Không có dữ liệu để tạo biểu đồ")
            return
        
        # Lọc các chế độ có giao dịch
        active_regimes = [regime for regime in self.regime_names if self.regime_metrics.get(regime, {}).get('trade_count', 0) > 0]
        
        if not active_regimes:
            logger.warning("Không có chế độ nào có giao dịch để tạo biểu đồ")
            return
        
        # Chuẩn bị dữ liệu
        trade_counts = [self.regime_metrics[regime]['trade_count'] for regime in active_regimes]
        win_rates = [self.regime_metrics[regime]['win_rate'] for regime in active_regimes]
        expectancies = [self.regime_metrics[regime]['expectancy'] for regime in active_regimes]
        avg_profits = [self.regime_metrics[regime]['avg_profit'] for regime in active_regimes]
        avg_losses = [self.regime_metrics[regime]['avg_loss'] for regime in active_regimes]
        
        # Tạo biểu đồ tổng quan
        plt.figure(figsize=(15, 10))
        
        # Biểu đồ số lượng giao dịch
        plt.subplot(221)
        bars = plt.bar(active_regimes, trade_counts, color=[self.regime_colors.get(regime, '#CCCCCC') for regime in active_regimes])
        
        # Thêm labels lên các cột
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}',
                    ha='center', va='bottom', rotation=0)
        
        plt.title('Số lượng giao dịch theo chế độ thị trường')
        plt.ylabel('Số lượng')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Biểu đồ win rate
        plt.subplot(222)
        bars = plt.bar(active_regimes, win_rates, color=[self.regime_colors.get(regime, '#CCCCCC') for regime in active_regimes])
        
        # Thêm labels lên các cột
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.1f}%',
                    ha='center', va='bottom', rotation=0)
        
        plt.title('Win Rate theo chế độ thị trường')
        plt.ylabel('Win Rate (%)')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Biểu đồ expectancy
        plt.subplot(223)
        bars = plt.bar(active_regimes, expectancies, color=[self.regime_colors.get(regime, '#CCCCCC') for regime in active_regimes])
        
        # Thêm labels lên các cột
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{height:.2f}%',
                    ha='center', va='bottom', rotation=0)
        
        plt.title('Expectancy theo chế độ thị trường')
        plt.ylabel('Expectancy (%)')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Biểu đồ lợi nhuận/thua lỗ trung bình
        plt.subplot(224)
        x = np.arange(len(active_regimes))
        width = 0.35
        
        bar1 = plt.bar(x - width/2, avg_profits, width, label='Lợi nhuận TB', color='green', alpha=0.7)
        bar2 = plt.bar(x + width/2, avg_losses, width, label='Thua lỗ TB', color='red', alpha=0.7)
        
        plt.xlabel('Chế độ thị trường')
        plt.ylabel('Phần trăm (%)')
        plt.title('Lợi nhuận/Thua lỗ trung bình theo chế độ')
        plt.xticks(x, active_regimes)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        plt.savefig('charts/market_regime/regime_performance_overview.png')
        plt.close()
        
        logger.info("Đã lưu biểu đồ tổng quan hiệu suất theo chế độ thị trường")
        
        # Tạo biểu đồ phân phối lợi nhuận
        plt.figure(figsize=(15, 10))
        
        for i, regime in enumerate(active_regimes):
            plt.subplot(2, 2, i+1)
            
            profits = [trade.get('profit_percentage', 0) for trade in self.regime_metrics[regime]['total_trades']]
            
            if profits:
                plt.hist(profits, bins=20, alpha=0.7, color=self.regime_colors.get(regime, '#CCCCCC'))
                plt.axvline(x=0, color='r', linestyle='--')
                plt.title(f'Phân phối lợi nhuận - {regime.capitalize()}')
                plt.xlabel('Lợi nhuận (%)')
                plt.ylabel('Số lượng giao dịch')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
            else:
                plt.text(0.5, 0.5, 'Không có dữ liệu', ha='center', va='center')
                plt.title(f'Phân phối lợi nhuận - {regime.capitalize()}')
        
        plt.tight_layout()
        plt.savefig('charts/market_regime/profit_distribution_by_regime.png')
        plt.close()
        
        logger.info("Đã lưu biểu đồ phân phối lợi nhuận theo chế độ thị trường")
    
    def create_regime_comparison_report(self):
        """
        Tạo báo cáo so sánh hiệu suất giữa các chế độ thị trường
        
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        if not self.regime_metrics:
            logger.warning("Không có dữ liệu để tạo báo cáo")
            return None
        
        # Lọc các chế độ có giao dịch
        active_regimes = [regime for regime in self.regime_names if regime in self.regime_metrics and self.regime_metrics[regime].get('trade_count', 0) > 0]
        
        if not active_regimes:
            logger.warning("Không có chế độ nào có giao dịch để tạo báo cáo")
            return None
        
        # Tạo DataFrame so sánh
        compare_metrics = [
            'trade_count', 'win_rate', 'profit_factor', 'expectancy',
            'avg_profit', 'avg_loss', 'max_profit', 'max_loss',
            'avg_holding_time_win', 'avg_holding_time_loss'
        ]
        
        compare_data = {}
        for metric in compare_metrics:
            compare_data[metric] = [self.regime_metrics[regime].get(metric, 0) for regime in active_regimes]
        
        df_comparison = pd.DataFrame(compare_data, index=active_regimes)
        
        # Tìm chế độ thị trường tốt nhất cho từng metric
        best_regimes = {}
        for metric in compare_metrics:
            if metric in ['avg_loss', 'max_loss']:
                # Đối với losses, giá trị thấp hơn là tốt hơn
                best_idx = df_comparison[metric].idxmin() if not df_comparison[metric].isna().all() else None
            else:
                # Đối với các metric khác, giá trị cao hơn là tốt hơn
                best_idx = df_comparison[metric].idxmax() if not df_comparison[metric].isna().all() else None
            
            best_regimes[metric] = best_idx
        
        # Tạo báo cáo HTML
        html_content = f"""
        <html>
        <head>
            <title>Báo cáo hiệu suất theo chế độ thị trường</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333366; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ text-align: left; padding: 8px; }}
                th {{ background-color: #333366; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .highlight {{ background-color: #ffffcc; font-weight: bold; }}
                .chart-container {{ margin: 20px 0; }}
                .regime-trending {{ color: #2E86C1; }}
                .regime-ranging {{ color: #27AE60; }}
                .regime-volatile {{ color: #E74C3C; }}
                .regime-quiet {{ color: #F39C12; }}
            </style>
        </head>
        <body>
            <h1>Báo cáo hiệu suất theo chế độ thị trường</h1>
            <p><strong>Thời gian tạo:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>1. Bảng so sánh hiệu suất</h2>
            <table border="1">
                <tr>
                    <th>Chỉ số</th>
        """
        
        # Thêm tiêu đề cột
        for regime in active_regimes:
            regime_class = f"regime-{regime}" if regime in self.regime_names else ""
            html_content += f'<th class="{regime_class}">{regime.capitalize()}</th>'
        
        html_content += "</tr>"
        
        # Thêm hàng dữ liệu
        metric_display = {
            'trade_count': 'Số lượng giao dịch',
            'win_rate': 'Win Rate (%)',
            'profit_factor': 'Profit Factor',
            'expectancy': 'Expectancy (%)',
            'avg_profit': 'Lợi nhuận TB (%)',
            'avg_loss': 'Thua lỗ TB (%)',
            'max_profit': 'Lợi nhuận tối đa (%)',
            'max_loss': 'Thua lỗ tối đa (%)',
            'avg_holding_time_win': 'Thời gian giữ TB (thắng)',
            'avg_holding_time_loss': 'Thời gian giữ TB (thua)'
        }
        
        for metric in compare_metrics:
            html_content += f"<tr><td>{metric_display.get(metric, metric)}</td>"
            
            for regime in active_regimes:
                value = self.regime_metrics[regime].get(metric, 0)
                highlight = "highlight" if best_regimes.get(metric) == regime else ""
                
                # Format giá trị
                if metric == 'trade_count':
                    formatted_value = f"{int(value)}"
                elif metric in ['win_rate', 'avg_profit', 'avg_loss', 'max_profit', 'max_loss', 'expectancy']:
                    formatted_value = f"{value:.2f}%"
                elif metric == 'profit_factor':
                    formatted_value = f"{value:.2f}" if value != float('inf') else "∞"
                elif metric in ['avg_holding_time_win', 'avg_holding_time_loss']:
                    formatted_value = f"{value:.1f} giờ"
                else:
                    formatted_value = f"{value}"
                
                html_content += f'<td class="{highlight}">{formatted_value}</td>'
            
            html_content += "</tr>"
        
        html_content += """
            </table>
            
            <h2>2. Chế độ thị trường tốt nhất cho từng loại giao dịch</h2>
            <table border="1">
                <tr>
                    <th>Chỉ số</th>
                    <th>Chế độ tốt nhất</th>
                    <th>Giá trị</th>
                </tr>
        """
        
        for metric, best_regime in best_regimes.items():
            if best_regime is not None:
                value = self.regime_metrics[best_regime].get(metric, 0)
                
                # Format giá trị
                if metric == 'trade_count':
                    formatted_value = f"{int(value)}"
                elif metric in ['win_rate', 'avg_profit', 'avg_loss', 'max_profit', 'max_loss', 'expectancy']:
                    formatted_value = f"{value:.2f}%"
                elif metric == 'profit_factor':
                    formatted_value = f"{value:.2f}" if value != float('inf') else "∞"
                elif metric in ['avg_holding_time_win', 'avg_holding_time_loss']:
                    formatted_value = f"{value:.1f} giờ"
                else:
                    formatted_value = f"{value}"
                
                regime_class = f"regime-{best_regime}" if best_regime in self.regime_names else ""
                
                html_content += f"""
                <tr>
                    <td>{metric_display.get(metric, metric)}</td>
                    <td class="{regime_class}">{best_regime.capitalize()}</td>
                    <td>{formatted_value}</td>
                </tr>
                """
        
        html_content += """
            </table>
            
            <h2>3. Biểu đồ</h2>
            <div class="chart-container">
                <h3>Tổng quan hiệu suất</h3>
                <img src="../charts/market_regime/regime_performance_overview.png" alt="Biểu đồ tổng quan hiệu suất" style="width:100%; max-width:1000px;">
            </div>
            
            <div class="chart-container">
                <h3>Phân phối lợi nhuận</h3>
                <img src="../charts/market_regime/profit_distribution_by_regime.png" alt="Biểu đồ phân phối lợi nhuận" style="width:100%; max-width:1000px;">
            </div>
            
            <h2>4. Kết luận và đề xuất</h2>
            <p>Dựa trên phân tích hiệu suất, chúng ta có thể rút ra các kết luận sau:</p>
            <ul>
        """
        
        # Thêm kết luận tự động
        for regime in active_regimes:
            metrics = self.regime_metrics[regime]
            
            if metrics['trade_count'] >= 5:  # Chỉ đưa ra kết luận nếu có đủ dữ liệu
                html_content += f"<li><strong class=\"regime-{regime}\">{regime.capitalize()}</strong>: "
                
                if metrics['win_rate'] > 60:
                    html_content += f"Win rate cao ({metrics['win_rate']:.1f}%), "
                elif metrics['win_rate'] < 40:
                    html_content += f"Win rate thấp ({metrics['win_rate']:.1f}%), "
                else:
                    html_content += f"Win rate trung bình ({metrics['win_rate']:.1f}%), "
                
                if metrics['profit_factor'] > 2:
                    html_content += f"profit factor tốt ({metrics['profit_factor']:.2f}). "
                elif metrics['profit_factor'] < 1:
                    html_content += f"profit factor kém ({metrics['profit_factor']:.2f}). "
                else:
                    html_content += f"profit factor chấp nhận được ({metrics['profit_factor']:.2f}). "
                
                if metrics['expectancy'] > 0:
                    html_content += f"Kỳ vọng dương ({metrics['expectancy']:.2f}%)."
                else:
                    html_content += f"Kỳ vọng âm ({metrics['expectancy']:.2f}%)."
                
                html_content += "</li>"
        
        # Thêm đề xuất
        html_content += """
            </ul>
            <p><strong>Đề xuất tối ưu hóa:</strong></p>
            <ul>
        """
        
        # Đề xuất tự động
        best_regime = best_regimes.get('expectancy')
        worst_regime = min(active_regimes, key=lambda r: self.regime_metrics[r]['expectancy']) if active_regimes else None
        
        if best_regime:
            html_content += f"""
            <li>Nên tập trung giao dịch trong chế độ <strong class="regime-{best_regime}">{best_regime.capitalize()}</strong> vì có hiệu suất tốt nhất (Expectancy: {self.regime_metrics[best_regime]['expectancy']:.2f}%).</li>
            """
        
        if worst_regime and self.regime_metrics[worst_regime]['expectancy'] < 0:
            html_content += f"""
            <li>Hạn chế giao dịch trong chế độ <strong class="regime-{worst_regime}">{worst_regime.capitalize()}</strong> do có hiệu suất kém (Expectancy: {self.regime_metrics[worst_regime]['expectancy']:.2f}%).</li>
            """
        
        html_content += """
            </ul>
        </body>
        </html>
        """
        
        # Lưu báo cáo
        report_path = "reports/market_regime/performance_comparison.html"
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Đã lưu báo cáo so sánh hiệu suất theo chế độ thị trường vào {report_path}")
        
        return report_path
    
    def analyze_and_create_report(self, symbol=None, interval=None):
        """
        Phân tích và tạo báo cáo tổng hợp
        
        Args:
            symbol (str, optional): Lọc theo cặp tiền
            interval (str, optional): Lọc theo khung thời gian
            
        Returns:
            str: Đường dẫn đến báo cáo hoặc None nếu không có dữ liệu
        """
        # Tải kết quả
        if not self.load_results(symbol, interval):
            logger.warning("Không thể tải kết quả để phân tích")
            return None
        
        # Phân tích hiệu suất
        self.analyze_regime_performance()
        
        # Tạo biểu đồ
        self.create_regime_performance_chart()
        
        # Tạo báo cáo
        report_path = self.create_regime_comparison_report()
        
        return report_path

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phân tích hiệu suất theo chế độ thị trường')
    parser.add_argument('--symbol', type=str, help='Lọc theo cặp tiền')
    parser.add_argument('--interval', type=str, help='Lọc theo khung thời gian')
    parser.add_argument('--results-dir', type=str, default='backtest_results',
                      help='Thư mục chứa kết quả backtest')
    
    args = parser.parse_args()
    
    analyzer = MarketRegimePerformanceAnalyzer(results_dir=args.results_dir)
    report_path = analyzer.analyze_and_create_report(symbol=args.symbol, interval=args.interval)
    
    if report_path:
        logger.info(f"Phân tích hoàn tất. Báo cáo được lưu tại: {report_path}")
    else:
        logger.error("Không thể tạo báo cáo do thiếu dữ liệu")

if __name__ == "__main__":
    main()