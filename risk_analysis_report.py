#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script phân tích chi tiết hiệu suất theo mức rủi ro

Script này phân tích hiệu suất backtest với các mức rủi ro khác nhau,
so sánh lợi nhuận, win rate, drawdown, và các metrics khác.
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
import matplotlib.colors as mcolors
import matplotlib.ticker as mtick

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('risk_analysis.log')
    ]
)

logger = logging.getLogger('risk_analyzer')

# Đảm bảo thư mục kết quả tồn tại
os.makedirs("reports/risk_analysis", exist_ok=True)
os.makedirs("charts/risk_analysis", exist_ok=True)

class RiskAnalysisReport:
    """Lớp phân tích và tạo báo cáo chi tiết về hiệu suất theo mức rủi ro"""
    
    def __init__(self, results_dir='backtest_results'):
        """
        Khởi tạo phân tích
        
        Args:
            results_dir (str): Thư mục chứa kết quả backtest
        """
        self.results_dir = results_dir
        self.results = []
        self.df_results = None
        self.all_trades = []
        self.risk_levels = []
        
        # Màu sắc cho các mức rủi ro
        self.risk_colors = {
            0.5: '#2E86C1',   # Xanh dương
            1.0: '#27AE60',   # Xanh lá
            1.5: '#F39C12',   # Cam
            2.0: '#E74C3C',   # Đỏ
            3.0: '#8E44AD'    # Tím
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
                
                # Thu thập các mức rủi ro độc nhất
                risk = result_data.get('risk_percentage')
                if risk is not None and risk not in self.risk_levels:
                    self.risk_levels.append(risk)
                
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
        
        # Sắp xếp các mức rủi ro
        self.risk_levels.sort()
        
        logger.info(f"Đã tải {len(self.results)} kết quả thỏa mãn điều kiện")
        logger.info(f"Mức rủi ro: {self.risk_levels}")
        
        if not self.results:
            return False
        
        # Tạo DataFrame từ kết quả
        self.df_results = pd.DataFrame(self.results)
        
        # Thêm trường Sharpe Ratio (Profit/Drawdown)
        self.df_results['sharpe_ratio'] = self.df_results['profit_percentage'] / self.df_results['max_drawdown'].replace(0, 0.01)
        
        return True
    
    def create_risk_performance_chart(self):
        """
        Tạo biểu đồ hiệu suất theo mức rủi ro
        """
        if self.df_results is None or self.df_results.empty:
            logger.warning("Không có dữ liệu để tạo biểu đồ")
            return
        
        # Phân tích theo mức rủi ro
        risk_analysis = self.df_results.groupby('risk_percentage').agg({
            'profit_percentage': ['mean', 'std', 'max', 'min'],
            'win_rate': ['mean', 'max', 'min'],
            'max_drawdown': ['mean', 'max', 'min'],
            'sharpe_ratio': ['mean', 'max', 'min'],
            'analysis_period': 'count'
        }).reset_index()
        
        # Đổi tên cột cho dễ truy cập
        risk_analysis.columns = ['risk_percentage', 'profit_mean', 'profit_std', 'profit_max', 'profit_min', 
                              'win_rate_mean', 'win_rate_max', 'win_rate_min',
                              'drawdown_mean', 'drawdown_max', 'drawdown_min',
                              'sharpe_mean', 'sharpe_max', 'sharpe_min',
                              'test_count']
        
        # Tạo biểu đồ tổng quan hiệu suất
        plt.figure(figsize=(12, 10))
        
        # 1. Biểu đồ lợi nhuận trung bình
        ax1 = plt.subplot(221)
        bars = ax1.bar(risk_analysis['risk_percentage'], risk_analysis['profit_mean'], 
                    yerr=risk_analysis['profit_std'], capsize=5, 
                    color=[self.risk_colors.get(r, '#CCCCCC') for r in risk_analysis['risk_percentage']])
        
        # Thêm giá trị lên mỗi cột
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{height:.2f}%',
                   ha='center', va='bottom', rotation=0)
        
        ax1.set_title('Lợi nhuận trung bình theo mức rủi ro')
        ax1.set_xlabel('Mức rủi ro (%)')
        ax1.set_ylabel('Lợi nhuận (%)')
        ax1.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 2. Biểu đồ win rate
        ax2 = plt.subplot(222)
        bars = ax2.bar(risk_analysis['risk_percentage'], risk_analysis['win_rate_mean'],
                     color=[self.risk_colors.get(r, '#CCCCCC') for r in risk_analysis['risk_percentage']])
        
        # Thêm giá trị lên mỗi cột
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{height:.1f}%',
                   ha='center', va='bottom', rotation=0)
        
        ax2.set_title('Win Rate trung bình theo mức rủi ro')
        ax2.set_xlabel('Mức rủi ro (%)')
        ax2.set_ylabel('Win Rate (%)')
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 3. Biểu đồ drawdown
        ax3 = plt.subplot(223)
        bars = ax3.bar(risk_analysis['risk_percentage'], risk_analysis['drawdown_mean'],
                     color=[self.risk_colors.get(r, '#CCCCCC') for r in risk_analysis['risk_percentage']])
        
        # Thêm giá trị lên mỗi cột
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{height:.2f}%',
                   ha='center', va='bottom', rotation=0)
        
        ax3.set_title('Drawdown trung bình theo mức rủi ro')
        ax3.set_xlabel('Mức rủi ro (%)')
        ax3.set_ylabel('Drawdown (%)')
        ax3.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 4. Biểu đồ Sharpe Ratio
        ax4 = plt.subplot(224)
        bars = ax4.bar(risk_analysis['risk_percentage'], risk_analysis['sharpe_mean'],
                     color=[self.risk_colors.get(r, '#CCCCCC') for r in risk_analysis['risk_percentage']])
        
        # Thêm giá trị lên mỗi cột
        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                   f'{height:.2f}',
                   ha='center', va='bottom', rotation=0)
        
        ax4.set_title('Sharpe Ratio trung bình theo mức rủi ro')
        ax4.set_xlabel('Mức rủi ro (%)')
        ax4.set_ylabel('Sharpe Ratio')
        ax4.grid(axis='y', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        plt.savefig('charts/risk_analysis/risk_performance_overview.png')
        plt.close()
        
        logger.info("Đã lưu biểu đồ hiệu suất theo mức rủi ro")
        
        # Tạo biểu đồ so sánh lợi nhuận theo mức rủi ro và khoảng thời gian
        if 'analysis_period' in self.df_results.columns:
            periods = self.df_results['analysis_period'].unique()
            if len(periods) > 1:
                plt.figure(figsize=(15, 8))
                
                # Chuẩn bị dữ liệu
                pivot_data = self.df_results.pivot_table(
                    index='analysis_period', 
                    columns='risk_percentage',
                    values='profit_percentage',
                    aggfunc='mean'
                )
                
                # Vẽ biểu đồ
                ax = pivot_data.plot(kind='bar', figsize=(15, 8), 
                                   color=[self.risk_colors.get(r, '#CCCCCC') for r in pivot_data.columns])
                
                plt.title('Lợi nhuận trung bình theo khoảng thời gian và mức rủi ro')
                plt.xlabel('Khoảng thời gian')
                plt.ylabel('Lợi nhuận (%)')
                plt.legend(title='Mức rủi ro (%)')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                # Thêm giá trị lên mỗi cột
                for container in ax.containers:
                    ax.bar_label(container, fmt='%.1f%%', padding=3)
                
                plt.tight_layout()
                plt.savefig('charts/risk_analysis/risk_profit_by_period.png')
                plt.close()
                
                logger.info("Đã lưu biểu đồ lợi nhuận theo khoảng thời gian và mức rủi ro")
                
                # Tương tự với Win Rate
                plt.figure(figsize=(15, 8))
                
                # Chuẩn bị dữ liệu
                pivot_data = self.df_results.pivot_table(
                    index='analysis_period', 
                    columns='risk_percentage',
                    values='win_rate',
                    aggfunc='mean'
                )
                
                # Vẽ biểu đồ
                ax = pivot_data.plot(kind='bar', figsize=(15, 8), 
                                   color=[self.risk_colors.get(r, '#CCCCCC') for r in pivot_data.columns])
                
                plt.title('Win Rate trung bình theo khoảng thời gian và mức rủi ro')
                plt.xlabel('Khoảng thời gian')
                plt.ylabel('Win Rate (%)')
                plt.legend(title='Mức rủi ro (%)')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                # Thêm giá trị lên mỗi cột
                for container in ax.containers:
                    ax.bar_label(container, fmt='%.1f%%', padding=3)
                
                plt.tight_layout()
                plt.savefig('charts/risk_analysis/risk_winrate_by_period.png')
                plt.close()
                
                logger.info("Đã lưu biểu đồ win rate theo khoảng thời gian và mức rủi ro")
    
    def create_profit_distribution_chart(self):
        """
        Tạo biểu đồ phân phối lợi nhuận theo mức rủi ro
        """
        if not self.all_trades:
            logger.warning("Không có dữ liệu giao dịch để tạo biểu đồ phân phối")
            return
        
        # Tạo DataFrame từ tất cả giao dịch
        df_trades = pd.DataFrame(self.all_trades)
        
        # Nhóm giao dịch theo mức rủi ro
        for risk in self.risk_levels:
            trades_for_risk = df_trades[df_trades['risk_percentage'] == risk]
            
            if not trades_for_risk.empty:
                profits = trades_for_risk['profit_percentage'].values
                
                plt.figure(figsize=(10, 6))
                plt.hist(profits, bins=20, alpha=0.7, color=self.risk_colors.get(risk, '#CCCCCC'))
                plt.axvline(x=0, color='r', linestyle='--')
                plt.title(f'Phân phối lợi nhuận - Mức rủi ro {risk}%')
                plt.xlabel('Lợi nhuận (%)')
                plt.ylabel('Số lượng giao dịch')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                # Thêm thông tin thống kê
                mean_profit = profits.mean()
                median_profit = np.median(profits)
                positive_pct = (profits > 0).mean() * 100
                
                plt.figtext(0.15, 0.85, f'Lợi nhuận TB: {mean_profit:.2f}%', fontsize=10)
                plt.figtext(0.15, 0.82, f'Lợi nhuận trung vị: {median_profit:.2f}%', fontsize=10)
                plt.figtext(0.15, 0.79, f'Tỷ lệ lãi: {positive_pct:.1f}%', fontsize=10)
                
                plt.tight_layout()
                plt.savefig(f'charts/risk_analysis/profit_distribution_risk_{risk}.png')
                plt.close()
                
                logger.info(f"Đã lưu biểu đồ phân phối lợi nhuận cho mức rủi ro {risk}%")
        
        # Tạo biểu đồ violin để so sánh phân phối giữa các mức rủi ro
        plt.figure(figsize=(12, 8))
        
        # Chuẩn bị dữ liệu cho violin plot
        data = []
        labels = []
        
        for risk in self.risk_levels:
            trades_for_risk = df_trades[df_trades['risk_percentage'] == risk]
            if not trades_for_risk.empty:
                data.append(trades_for_risk['profit_percentage'].values)
                labels.append(f"{risk}%")
        
        if data:
            violin_parts = plt.violinplot(data, showmeans=True, showmedians=True)
            
            # Tùy chỉnh màu sắc
            for i, pc in enumerate(violin_parts['bodies']):
                pc.set_facecolor(self.risk_colors.get(self.risk_levels[i], '#CCCCCC'))
                pc.set_alpha(0.7)
            
            # Thêm đường đánh dấu 0
            plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            
            plt.title('So sánh phân phối lợi nhuận theo mức rủi ro')
            plt.ylabel('Lợi nhuận (%)')
            plt.xticks(np.arange(1, len(labels) + 1), labels)
            plt.xlabel('Mức rủi ro')
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig('charts/risk_analysis/profit_distribution_comparison.png')
            plt.close()
            
            logger.info("Đã lưu biểu đồ so sánh phân phối lợi nhuận giữa các mức rủi ro")
    
    def create_risk_optimization_matrix(self):
        """
        Tạo bảng tối ưu hóa mức rủi ro theo các tiêu chí khác nhau
        """
        if self.df_results is None or self.df_results.empty:
            logger.warning("Không có dữ liệu để tạo bảng tối ưu hóa")
            return
        
        # Kiểm tra nếu có dữ liệu theo khoảng thời gian
        if 'analysis_period' in self.df_results.columns:
            periods = self.df_results['analysis_period'].unique()
            
            if len(periods) > 1:
                # Tạo heatmap cho lợi nhuận
                pivot_profit = self.df_results.pivot_table(
                    index='analysis_period', 
                    columns='risk_percentage',
                    values='profit_percentage',
                    aggfunc='mean'
                )
                
                plt.figure(figsize=(10, 6))
                heatmap = plt.pcolor(pivot_profit, cmap='RdYlGn')
                
                plt.colorbar(heatmap, label='Lợi nhuận (%)')
                plt.title('Bảng tối ưu hóa lợi nhuận theo mức rủi ro và khoảng thời gian')
                plt.xlabel('Mức rủi ro (%)')
                plt.ylabel('Khoảng thời gian')
                
                # Thêm giá trị vào từng ô
                for i in range(len(pivot_profit.index)):
                    for j in range(len(pivot_profit.columns)):
                        plt.text(j + 0.5, i + 0.5, f'{pivot_profit.iloc[i, j]:.2f}%',
                              ha='center', va='center', color='black')
                
                plt.xticks(np.arange(0.5, len(pivot_profit.columns)), pivot_profit.columns)
                plt.yticks(np.arange(0.5, len(pivot_profit.index)), pivot_profit.index)
                
                plt.tight_layout()
                plt.savefig('charts/risk_analysis/risk_profit_heatmap.png')
                plt.close()
                
                logger.info("Đã lưu bảng tối ưu hóa lợi nhuận")
                
                # Tạo heatmap cho Sharpe Ratio
                pivot_sharpe = self.df_results.pivot_table(
                    index='analysis_period', 
                    columns='risk_percentage',
                    values='sharpe_ratio',
                    aggfunc='mean'
                )
                
                plt.figure(figsize=(10, 6))
                heatmap = plt.pcolor(pivot_sharpe, cmap='RdYlGn')
                
                plt.colorbar(heatmap, label='Sharpe Ratio')
                plt.title('Bảng tối ưu hóa Sharpe Ratio theo mức rủi ro và khoảng thời gian')
                plt.xlabel('Mức rủi ro (%)')
                plt.ylabel('Khoảng thời gian')
                
                # Thêm giá trị vào từng ô
                for i in range(len(pivot_sharpe.index)):
                    for j in range(len(pivot_sharpe.columns)):
                        plt.text(j + 0.5, i + 0.5, f'{pivot_sharpe.iloc[i, j]:.2f}',
                              ha='center', va='center', color='black')
                
                plt.xticks(np.arange(0.5, len(pivot_sharpe.columns)), pivot_sharpe.columns)
                plt.yticks(np.arange(0.5, len(pivot_sharpe.index)), pivot_sharpe.index)
                
                plt.tight_layout()
                plt.savefig('charts/risk_analysis/risk_sharpe_heatmap.png')
                plt.close()
                
                logger.info("Đã lưu bảng tối ưu hóa Sharpe Ratio")
    
    def create_optimal_risk_report(self):
        """
        Tạo báo cáo về mức rủi ro tối ưu dựa trên phân tích
        
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        if self.df_results is None or self.df_results.empty:
            logger.warning("Không có dữ liệu để tạo báo cáo")
            return None
        
        # Phân tích theo mức rủi ro
        risk_analysis = self.df_results.groupby('risk_percentage').agg({
            'profit_percentage': ['mean', 'std', 'max', 'min'],
            'win_rate': ['mean', 'max', 'min'],
            'max_drawdown': ['mean', 'max', 'min'],
            'sharpe_ratio': ['mean', 'max', 'min'],
            'analysis_period': 'count'
        }).reset_index()
        
        # Đổi tên cột cho dễ truy cập
        risk_analysis.columns = ['risk_percentage', 'profit_mean', 'profit_std', 'profit_max', 'profit_min', 
                              'win_rate_mean', 'win_rate_max', 'win_rate_min',
                              'drawdown_mean', 'drawdown_max', 'drawdown_min',
                              'sharpe_mean', 'sharpe_max', 'sharpe_min',
                              'test_count']
        
        # Tìm mức rủi ro tối ưu dựa trên các tiêu chí khác nhau
        optimal_profit_risk = risk_analysis.loc[risk_analysis['profit_mean'].idxmax()]
        optimal_winrate_risk = risk_analysis.loc[risk_analysis['win_rate_mean'].idxmax()]
        optimal_drawdown_risk = risk_analysis.loc[risk_analysis['drawdown_mean'].idxmin()]
        optimal_sharpe_risk = risk_analysis.loc[risk_analysis['sharpe_mean'].idxmax()]
        
        # Tạo báo cáo HTML
        html_content = f"""
        <html>
        <head>
            <title>Báo cáo phân tích mức rủi ro tối ưu</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333366; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ text-align: left; padding: 8px; }}
                th {{ background-color: #333366; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .highlight {{ background-color: #ffffcc; font-weight: bold; }}
                .chart-container {{ margin: 20px 0; }}
                .risk-0-5 {{ color: #2E86C1; }}
                .risk-1-0 {{ color: #27AE60; }}
                .risk-1-5 {{ color: #F39C12; }}
                .risk-2-0 {{ color: #E74C3C; }}
                .risk-3-0 {{ color: #8E44AD; }}
            </style>
        </head>
        <body>
            <h1>Báo cáo phân tích mức rủi ro tối ưu</h1>
            <p><strong>Thời gian tạo:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>1. Tổng quan hiệu suất theo mức rủi ro</h2>
            <table border="1">
                <tr>
                    <th>Mức rủi ro (%)</th>
                    <th>Lợi nhuận TB (%)</th>
                    <th>Độ lệch chuẩn (%)</th>
                    <th>Win Rate TB (%)</th>
                    <th>Drawdown TB (%)</th>
                    <th>Sharpe Ratio</th>
                    <th>Số test</th>
                </tr>
        """
        
        # Thêm hàng dữ liệu
        for i, row in risk_analysis.iterrows():
            risk_class = f"risk-{row['risk_percentage']}".replace('.', '-')
            
            # Xác định các giá trị tối ưu
            profit_highlight = "highlight" if row['risk_percentage'] == optimal_profit_risk['risk_percentage'] else ""
            winrate_highlight = "highlight" if row['risk_percentage'] == optimal_winrate_risk['risk_percentage'] else ""
            drawdown_highlight = "highlight" if row['risk_percentage'] == optimal_drawdown_risk['risk_percentage'] else ""
            sharpe_highlight = "highlight" if row['risk_percentage'] == optimal_sharpe_risk['risk_percentage'] else ""
            
            html_content += f"""
                <tr>
                    <td class="{risk_class}">{row['risk_percentage']}%</td>
                    <td class="{profit_highlight}">{row['profit_mean']:.2f}% (±{row['profit_std']:.2f}%)</td>
                    <td>{row['profit_std']:.2f}%</td>
                    <td class="{winrate_highlight}">{row['win_rate_mean']:.2f}%</td>
                    <td class="{drawdown_highlight}">{row['drawdown_mean']:.2f}%</td>
                    <td class="{sharpe_highlight}">{row['sharpe_mean']:.2f}</td>
                    <td>{int(row['test_count'])}</td>
                </tr>
            """
        
        html_content += """
            </table>
            
            <h2>2. Mức rủi ro tối ưu theo từng tiêu chí</h2>
            <table border="1">
                <tr>
                    <th>Tiêu chí</th>
                    <th>Mức rủi ro tối ưu</th>
                    <th>Giá trị</th>
                </tr>
        """
        
        # Thông tin mức rủi ro tối ưu theo từng tiêu chí
        opt_profit_class = f"risk-{optimal_profit_risk['risk_percentage']}".replace('.', '-')
        opt_winrate_class = f"risk-{optimal_winrate_risk['risk_percentage']}".replace('.', '-')
        opt_drawdown_class = f"risk-{optimal_drawdown_risk['risk_percentage']}".replace('.', '-')
        opt_sharpe_class = f"risk-{optimal_sharpe_risk['risk_percentage']}".replace('.', '-')
        
        html_content += f"""
                <tr>
                    <td>Lợi nhuận cao nhất</td>
                    <td class="{opt_profit_class}">{optimal_profit_risk['risk_percentage']}%</td>
                    <td>{optimal_profit_risk['profit_mean']:.2f}%</td>
                </tr>
                <tr>
                    <td>Win Rate cao nhất</td>
                    <td class="{opt_winrate_class}">{optimal_winrate_risk['risk_percentage']}%</td>
                    <td>{optimal_winrate_risk['win_rate_mean']:.2f}%</td>
                </tr>
                <tr>
                    <td>Drawdown thấp nhất</td>
                    <td class="{opt_drawdown_class}">{optimal_drawdown_risk['risk_percentage']}%</td>
                    <td>{optimal_drawdown_risk['drawdown_mean']:.2f}%</td>
                </tr>
                <tr>
                    <td>Sharpe Ratio cao nhất</td>
                    <td class="{opt_sharpe_class}">{optimal_sharpe_risk['risk_percentage']}%</td>
                    <td>{optimal_sharpe_risk['sharpe_mean']:.2f}</td>
                </tr>
        """
        
        html_content += """
            </table>
            
            <h2>3. Biểu đồ phân tích</h2>
            <div class="chart-container">
                <h3>Tổng quan hiệu suất theo mức rủi ro</h3>
                <img src="../../charts/risk_analysis/risk_performance_overview.png" alt="Biểu đồ tổng quan hiệu suất" style="width:100%; max-width:1000px;">
            </div>
        """
        
        # Thêm biểu đồ theo khoảng thời gian nếu có
        if 'analysis_period' in self.df_results.columns and len(self.df_results['analysis_period'].unique()) > 1:
            html_content += """
            <div class="chart-container">
                <h3>Lợi nhuận theo khoảng thời gian và mức rủi ro</h3>
                <img src="../../charts/risk_analysis/risk_profit_by_period.png" alt="Biểu đồ lợi nhuận theo khoảng thời gian" style="width:100%; max-width:1000px;">
            </div>
            
            <div class="chart-container">
                <h3>Win Rate theo khoảng thời gian và mức rủi ro</h3>
                <img src="../../charts/risk_analysis/risk_winrate_by_period.png" alt="Biểu đồ win rate theo khoảng thời gian" style="width:100%; max-width:1000px;">
            </div>
            
            <div class="chart-container">
                <h3>Bảng tối ưu hóa lợi nhuận</h3>
                <img src="../../charts/risk_analysis/risk_profit_heatmap.png" alt="Bảng tối ưu hóa lợi nhuận" style="width:100%; max-width:1000px;">
            </div>
            
            <div class="chart-container">
                <h3>Bảng tối ưu hóa Sharpe Ratio</h3>
                <img src="../../charts/risk_analysis/risk_sharpe_heatmap.png" alt="Bảng tối ưu hóa Sharpe Ratio" style="width:100%; max-width:1000px;">
            </div>
            """
        
        # Thêm biểu đồ phân phối lợi nhuận
        if self.all_trades:
            html_content += """
            <div class="chart-container">
                <h3>So sánh phân phối lợi nhuận giữa các mức rủi ro</h3>
                <img src="../../charts/risk_analysis/profit_distribution_comparison.png" alt="Biểu đồ so sánh phân phối lợi nhuận" style="width:100%; max-width:1000px;">
            </div>
            """
            
            for risk in self.risk_levels:
                df_trades = pd.DataFrame(self.all_trades)
                trades_for_risk = df_trades[df_trades['risk_percentage'] == risk]
                
                if not trades_for_risk.empty:
                    html_content += f"""
                    <div class="chart-container">
                        <h3>Phân phối lợi nhuận - Mức rủi ro {risk}%</h3>
                        <img src="../../charts/risk_analysis/profit_distribution_risk_{risk}.png" alt="Biểu đồ phân phối lợi nhuận" style="width:100%; max-width:1000px;">
                    </div>
                    """
        
        # Thêm kết luận và đề xuất
        html_content += """
            <h2>4. Kết luận và đề xuất</h2>
        """
        
        # Tìm mức rủi ro cân bằng dựa trên nhiều tiêu chí
        optimal_risks = [
            optimal_profit_risk['risk_percentage'],
            optimal_winrate_risk['risk_percentage'],
            optimal_sharpe_risk['risk_percentage']
        ]
        
        # Xác định mức rủi ro xuất hiện nhiều nhất trong các tiêu chí
        from collections import Counter
        risk_counter = Counter(optimal_risks)
        most_balanced_risk = risk_counter.most_common(1)[0][0]
        
        balance_risk_class = f"risk-{most_balanced_risk}".replace('.', '-')
        
        html_content += f"""
            <p>Dựa trên phân tích các mức rủi ro khác nhau, chúng ta có thể rút ra các kết luận sau:</p>
            <ul>
                <li>Mức rủi ro tối ưu cho lợi nhuận cao nhất: <strong class="{opt_profit_class}">{optimal_profit_risk['risk_percentage']}%</strong></li>
                <li>Mức rủi ro tối ưu cho win rate cao nhất: <strong class="{opt_winrate_class}">{optimal_winrate_risk['risk_percentage']}%</strong></li>
                <li>Mức rủi ro tối ưu cho drawdown thấp nhất: <strong class="{opt_drawdown_class}">{optimal_drawdown_risk['risk_percentage']}%</strong></li>
                <li>Mức rủi ro tối ưu cho Sharpe ratio cao nhất: <strong class="{opt_sharpe_class}">{optimal_sharpe_risk['risk_percentage']}%</strong></li>
            </ul>
            
            <p><strong>Đề xuất:</strong></p>
            <p>Mức rủi ro cân bằng nhất (xuất hiện nhiều nhất trong các tiêu chí): <strong class="{balance_risk_class}">{most_balanced_risk}%</strong></p>
            <p>Lý do:</p>
            <ul>
        """
        
        # Đưa ra lý do cụ thể
        if most_balanced_risk == optimal_profit_risk['risk_percentage']:
            html_content += f"<li>Mức rủi ro này mang lại lợi nhuận cao nhất ({optimal_profit_risk['profit_mean']:.2f}%)</li>"
        
        if most_balanced_risk == optimal_winrate_risk['risk_percentage']:
            html_content += f"<li>Mức rủi ro này mang lại win rate cao nhất ({optimal_winrate_risk['win_rate_mean']:.2f}%)</li>"
        
        if most_balanced_risk == optimal_sharpe_risk['risk_percentage']:
            html_content += f"<li>Mức rủi ro này mang lại Sharpe ratio tốt nhất ({optimal_sharpe_risk['sharpe_mean']:.2f})</li>"
        
        # Thêm thông tin về sự cân bằng giữa rủi ro và phần thưởng
        most_balanced_idx = risk_analysis[risk_analysis['risk_percentage'] == most_balanced_risk].index[0]
        html_content += f"""
            <li>Mức rủi ro này cung cấp sự cân bằng tốt giữa:
                <ul>
                    <li>Lợi nhuận: {risk_analysis.iloc[most_balanced_idx]['profit_mean']:.2f}%</li>
                    <li>Win rate: {risk_analysis.iloc[most_balanced_idx]['win_rate_mean']:.2f}%</li>
                    <li>Drawdown: {risk_analysis.iloc[most_balanced_idx]['drawdown_mean']:.2f}%</li>
                    <li>Sharpe ratio: {risk_analysis.iloc[most_balanced_idx]['sharpe_mean']:.2f}</li>
                </ul>
            </li>
        """
        
        html_content += """
            </ul>
        </body>
        </html>
        """
        
        # Lưu báo cáo
        report_path = "reports/risk_analysis/optimal_risk_report.html"
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Đã lưu báo cáo mức rủi ro tối ưu vào {report_path}")
        
        return report_path
    
    def analyze_and_create_report(self, symbol=None, interval=None):
        """
        Phân tích và tạo báo cáo tổng hợp về mức rủi ro tối ưu
        
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
        
        # Tạo biểu đồ hiệu suất
        self.create_risk_performance_chart()
        
        # Tạo biểu đồ phân phối lợi nhuận
        self.create_profit_distribution_chart()
        
        # Tạo bảng tối ưu hóa
        self.create_risk_optimization_matrix()
        
        # Tạo báo cáo
        report_path = self.create_optimal_risk_report()
        
        return report_path

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phân tích chi tiết hiệu suất theo mức rủi ro')
    parser.add_argument('--symbol', type=str, help='Lọc theo cặp tiền')
    parser.add_argument('--interval', type=str, help='Lọc theo khung thời gian')
    parser.add_argument('--results-dir', type=str, default='backtest_results',
                      help='Thư mục chứa kết quả backtest')
    
    args = parser.parse_args()
    
    analyzer = RiskAnalysisReport(results_dir=args.results_dir)
    report_path = analyzer.analyze_and_create_report(symbol=args.symbol, interval=args.interval)
    
    if report_path:
        logger.info(f"Phân tích hoàn tất. Báo cáo được lưu tại: {report_path}")
    else:
        logger.error("Không thể tạo báo cáo do thiếu dữ liệu")

if __name__ == "__main__":
    main()