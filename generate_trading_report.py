#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import argparse
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from tabulate import tabulate
from jinja2 import Template

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("report_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("report_generator")

class TradingReportGenerator:
    def __init__(self, results_dir="backtest_results", summary_dir="backtest_summary"):
        """
        Khởi tạo generator báo cáo
        
        Args:
            results_dir (str): Thư mục chứa kết quả backtest
            summary_dir (str): Thư mục chứa báo cáo tổng hợp
        """
        self.results_dir = results_dir
        self.summary_dir = summary_dir
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs('reports', exist_ok=True)
        
        logger.info(f"Khởi tạo generator báo cáo từ thư mục {results_dir}")
    
    def load_results(self):
        """
        Tải kết quả backtest từ thư mục
        
        Returns:
            dict: Kết quả backtest
        """
        results = {}
        
        try:
            # Lấy danh sách file JSON trong thư mục
            json_files = [f for f in os.listdir(self.results_dir) if f.endswith('.json')]
            
            for filename in json_files:
                filepath = os.path.join(self.results_dir, filename)
                
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                # Phân tích tên file để lấy thông tin
                # Ví dụ: small_account_100_lev20x_20250101_20250401.json
                parts = filename.split('_')
                if len(parts) >= 7:
                    account_size = parts[2]
                    leverage = parts[3].replace('lev', '').replace('x', '')
                    start_date = parts[4]
                    end_date = parts[5].split('.')[0]
                    
                    key = f"{account_size}_{leverage}_{start_date}_{end_date}"
                    results[key] = data
            
            logger.info(f"Đã tải {len(results)} kết quả backtest")
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi tải kết quả backtest: {str(e)}")
            return {}
    
    def load_summary(self):
        """
        Tải báo cáo tổng hợp từ thư mục
        
        Returns:
            dict: Báo cáo tổng hợp
        """
        summary = {}
        
        try:
            # Lấy danh sách file JSON trong thư mục
            json_files = [f for f in os.listdir(self.summary_dir) if f.endswith('.json') and f.startswith('summary_')]
            
            for filename in json_files:
                filepath = os.path.join(self.summary_dir, filename)
                
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                # Phân tích tên file để lấy thông tin
                # Ví dụ: summary_20250101_20250401.json
                parts = filename.split('_')
                if len(parts) >= 3:
                    start_date = parts[1]
                    end_date = parts[2].split('.')[0]
                    
                    key = f"{start_date}_{end_date}"
                    summary[key] = data
            
            logger.info(f"Đã tải {len(summary)} báo cáo tổng hợp")
            return summary
            
        except Exception as e:
            logger.error(f"Lỗi khi tải báo cáo tổng hợp: {str(e)}")
            return {}
    
    def generate_symbol_report(self, results):
        """
        Tạo báo cáo hiệu suất theo symbol
        
        Args:
            results (dict): Kết quả backtest
            
        Returns:
            pd.DataFrame: Báo cáo hiệu suất theo symbol
        """
        symbol_stats = []
        
        for key, data in results.items():
            if 'summary' not in data or 'results' not in data:
                continue
                
            account_size = data['summary']['account_size']
            leverage = data['summary']['leverage']
            start_date = data['summary']['start_date']
            end_date = data['summary']['end_date']
            
            for symbol, result in data['results'].items():
                if 'statistics' not in result:
                    continue
                    
                stats = result['statistics']
                
                symbol_stats.append({
                    'symbol': symbol,
                    'account_size': account_size,
                    'leverage': leverage,
                    'start_date': start_date,
                    'end_date': end_date,
                    'net_profit_pct': stats['net_profit_pct'],
                    'total_trades': stats['total_trades'],
                    'win_rate': stats['win_rate'],
                    'avg_win': stats['avg_win'],
                    'avg_loss': stats['avg_loss'],
                    'profit_factor': stats['profit_factor'],
                    'max_drawdown_pct': stats['max_drawdown_pct'],
                    'avg_holding_time': stats['avg_holding_time']
                })
        
        if not symbol_stats:
            logger.error("Không có dữ liệu để tạo báo cáo hiệu suất theo symbol")
            return None
            
        df = pd.DataFrame(symbol_stats)
        
        # Sắp xếp theo lợi nhuận
        df = df.sort_values('net_profit_pct', ascending=False)
        
        return df
    
    def generate_account_size_report(self, results):
        """
        Tạo báo cáo hiệu suất theo kích thước tài khoản
        
        Args:
            results (dict): Kết quả backtest
            
        Returns:
            pd.DataFrame: Báo cáo hiệu suất theo kích thước tài khoản
        """
        account_stats = []
        
        for key, data in results.items():
            if 'summary' not in data:
                continue
                
            summary = data['summary']
            
            account_stats.append({
                'account_size': summary['account_size'],
                'leverage': summary['leverage'],
                'risk_percentage': summary['risk_percentage'],
                'start_date': summary['start_date'],
                'end_date': summary['end_date'],
                'total_symbols': summary['total_symbols'],
                'total_trades': summary['total_trades'],
                'overall_win_rate': summary['overall_win_rate'],
                'avg_net_profit_pct': summary['avg_net_profit_pct'],
                'total_net_profit_pct': summary['total_net_profit_pct'],
                'avg_max_drawdown_pct': summary['avg_max_drawdown_pct'],
                'avg_profit_factor': summary['avg_profit_factor'],
                'avg_holding_time': summary['avg_holding_time'],
                'best_symbol': summary['best_symbol'],
                'best_profit_pct': summary['best_profit_pct']
            })
        
        if not account_stats:
            logger.error("Không có dữ liệu để tạo báo cáo hiệu suất theo kích thước tài khoản")
            return None
            
        df = pd.DataFrame(account_stats)
        
        # Sắp xếp theo lợi nhuận
        df = df.sort_values('total_net_profit_pct', ascending=False)
        
        return df
    
    def generate_combined_report(self, summary):
        """
        Tạo báo cáo tổng hợp từ nhiều khoảng thời gian
        
        Args:
            summary (dict): Báo cáo tổng hợp
            
        Returns:
            pd.DataFrame: Báo cáo tổng hợp
        """
        combined_stats = []
        
        for key, data in summary.items():
            for account_size, timeframes in data.items():
                for timeframe, summary_data in timeframes.items():
                    if summary_data:
                        combined_stats.append({
                            'account_size': account_size,
                            'timeframe': timeframe,
                            'leverage': summary_data.get('leverage'),
                            'risk_percentage': summary_data.get('risk_percentage'),
                            'start_date': summary_data.get('start_date'),
                            'end_date': summary_data.get('end_date'),
                            'total_symbols': summary_data.get('total_symbols'),
                            'total_trades': summary_data.get('total_trades'),
                            'overall_win_rate': summary_data.get('overall_win_rate'),
                            'avg_net_profit_pct': summary_data.get('avg_net_profit_pct'),
                            'total_net_profit_pct': summary_data.get('total_net_profit_pct'),
                            'avg_max_drawdown_pct': summary_data.get('avg_max_drawdown_pct'),
                            'avg_profit_factor': summary_data.get('avg_profit_factor'),
                            'avg_holding_time': summary_data.get('avg_holding_time'),
                            'best_symbol': summary_data.get('best_symbol'),
                            'best_profit_pct': summary_data.get('best_profit_pct')
                        })
        
        if not combined_stats:
            logger.error("Không có dữ liệu để tạo báo cáo tổng hợp")
            return None
            
        df = pd.DataFrame(combined_stats)
        
        # Sắp xếp theo lợi nhuận
        df = df.sort_values('total_net_profit_pct', ascending=False)
        
        return df
    
    def plot_heatmap(self, df, x_col, y_col, value_col, title, filename):
        """
        Vẽ heatmap
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            x_col (str): Tên cột trục x
            y_col (str): Tên cột trục y
            value_col (str): Tên cột giá trị
            title (str): Tiêu đề
            filename (str): Tên file
        """
        try:
            # Tạo pivot table
            pivot = df.pivot_table(
                index=y_col, 
                columns=x_col, 
                values=value_col, 
                aggfunc='mean'
            )
            
            # Vẽ heatmap
            plt.figure(figsize=(10, 8))
            plt.imshow(pivot, cmap='RdYlGn')
            
            # Thêm giá trị vào heatmap
            for i in range(len(pivot.index)):
                for j in range(len(pivot.columns)):
                    try:
                        value = pivot.iloc[i, j]
                        if not np.isnan(value):
                            plt.text(j, i, f'{value:.2f}', ha='center', va='center', color='black')
                    except:
                        pass
            
            plt.colorbar(label=value_col)
            plt.title(title)
            plt.xlabel(x_col)
            plt.ylabel(y_col)
            plt.xticks(np.arange(len(pivot.columns)), pivot.columns)
            plt.yticks(np.arange(len(pivot.index)), pivot.index)
            plt.tight_layout()
            
            # Lưu biểu đồ
            plt.savefig(os.path.join('reports', filename))
            plt.close()
            
            logger.info(f"Đã lưu heatmap vào file {filename}")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ heatmap: {str(e)}")
    
    def generate_html_report(self, results, summary):
        """
        Tạo báo cáo HTML
        
        Args:
            results (dict): Kết quả backtest
            summary (dict): Báo cáo tổng hợp
        """
        try:
            # Tạo các báo cáo
            symbol_report = self.generate_symbol_report(results)
            account_report = self.generate_account_size_report(results)
            combined_report = self.generate_combined_report(summary)
            
            # Tạo HTML template
            template_str = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Báo cáo giao dịch cho tài khoản nhỏ</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
                    h1, h2, h3 { color: #0066cc; }
                    table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                    tr:hover { background-color: #f5f5f5; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .summary { background-color: #e6f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .profit { color: green; }
                    .loss { color: red; }
                    img { max-width: 100%; height: auto; margin-bottom: 20px; }
                    .date { color: #666; font-size: 0.9em; }
                    .footer { margin-top: 50px; border-top: 1px solid #ddd; padding-top: 10px; color: #666; font-size: 0.8em; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Báo cáo giao dịch cho tài khoản nhỏ</h1>
                    <p class="date">Được tạo lúc: {{ generation_date }}</p>
                    
                    <div class="summary">
                        <h2>Tóm tắt</h2>
                        <p>Báo cáo này phân tích hiệu suất giao dịch cho các tài khoản $100, $200 và $300 với các mức đòn bẩy và rủi ro khác nhau.</p>
                        <p>Tổng số cấu hình được phân tích: {{ total_configs }}</p>
                        <p>Tổng số cặp tiền được phân tích: {{ total_symbols if total_symbols else 'N/A' }}</p>
                        <p>Khoảng thời gian: {{ time_period if time_period else 'N/A' }}</p>
                    </div>
                    
                    <h2>Kết quả theo kích thước tài khoản</h2>
                    <p>Bảng dưới đây so sánh hiệu suất giao dịch của các kích thước tài khoản khác nhau.</p>
                    {{ account_table | safe }}
                    
                    <h2>Top 20 cặp tiền hiệu quả nhất</h2>
                    <p>Bảng dưới đây liệt kê 20 cặp tiền có hiệu suất cao nhất trong kỳ kiểm thử.</p>
                    {{ symbol_table | safe }}
                    
                    <h2>So sánh cấu hình</h2>
                    <p>Bảng dưới đây so sánh hiệu suất của các cấu hình khác nhau (kích thước tài khoản, đòn bẩy, timeframe).</p>
                    {{ combined_table | safe }}
                    
                    <h2>Biểu đồ phân tích</h2>
                    
                    <h3>Heatmap lợi nhuận theo tài khoản và đòn bẩy</h3>
                    <img src="profit_heatmap_account_leverage.png" alt="Heatmap lợi nhuận theo tài khoản và đòn bẩy">
                    
                    <h3>Heatmap tỷ lệ thắng theo tài khoản và đòn bẩy</h3>
                    <img src="winrate_heatmap_account_leverage.png" alt="Heatmap tỷ lệ thắng theo tài khoản và đòn bẩy">
                    
                    <h3>Heatmap profit factor theo tài khoản và đòn bẩy</h3>
                    <img src="profitfactor_heatmap_account_leverage.png" alt="Heatmap profit factor theo tài khoản và đòn bẩy">
                    
                    <div class="footer">
                        <p>Báo cáo này được tạo tự động bởi hệ thống giao dịch cho tài khoản nhỏ.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Tạo HTML từ template
            template = Template(template_str)
            
            # Vẽ heatmap và lưu
            if combined_report is not None:
                # Chuyển đổi kiểu dữ liệu
                combined_report['account_size'] = combined_report['account_size'].astype(str)
                combined_report['leverage'] = combined_report['leverage'].astype(str)
                combined_report['total_net_profit_pct'] = combined_report['total_net_profit_pct'].astype(float)
                combined_report['overall_win_rate'] = combined_report['overall_win_rate'].astype(float) * 100
                combined_report['avg_profit_factor'] = combined_report['avg_profit_factor'].astype(float)
                
                # Vẽ heatmap
                self.plot_heatmap(
                    combined_report, 
                    'leverage', 
                    'account_size', 
                    'total_net_profit_pct', 
                    'Lợi nhuận (%) theo tài khoản và đòn bẩy',
                    'profit_heatmap_account_leverage.png'
                )
                
                self.plot_heatmap(
                    combined_report, 
                    'leverage', 
                    'account_size', 
                    'overall_win_rate', 
                    'Tỷ lệ thắng (%) theo tài khoản và đòn bẩy',
                    'winrate_heatmap_account_leverage.png'
                )
                
                self.plot_heatmap(
                    combined_report, 
                    'leverage', 
                    'account_size', 
                    'avg_profit_factor', 
                    'Profit Factor theo tài khoản và đòn bẩy',
                    'profitfactor_heatmap_account_leverage.png'
                )
            
            # Render HTML
            time_period = None
            if account_report is not None and not account_report.empty:
                start_date = account_report['start_date'].iloc[0]
                end_date = account_report['end_date'].iloc[0]
                time_period = f"{start_date} đến {end_date}"
                
            html = template.render(
                generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                total_configs=len(results) if results else 0,
                total_symbols=len(symbol_report['symbol'].unique()) if symbol_report is not None else None,
                time_period=time_period,
                account_table=account_report.to_html(index=False) if account_report is not None else "Không có dữ liệu",
                symbol_table=symbol_report.head(20).to_html(index=False) if symbol_report is not None else "Không có dữ liệu",
                combined_table=combined_report.to_html(index=False) if combined_report is not None else "Không có dữ liệu"
            )
            
            # Lưu HTML
            with open(os.path.join('reports', 'trading_report.html'), 'w') as f:
                f.write(html)
                
            logger.info("Đã tạo báo cáo HTML")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo HTML: {str(e)}")
    
    def generate_report(self):
        """
        Tạo báo cáo
        """
        logger.info("Bắt đầu tạo báo cáo...")
        
        # Tải kết quả
        results = self.load_results()
        summary = self.load_summary()
        
        # Tạo báo cáo HTML
        self.generate_html_report(results, summary)
        
        logger.info("Hoàn thành tạo báo cáo")

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Tạo báo cáo giao dịch')
    parser.add_argument('--results-dir', type=str, default='backtest_results', help='Thư mục chứa kết quả backtest')
    parser.add_argument('--summary-dir', type=str, default='backtest_summary', help='Thư mục chứa báo cáo tổng hợp')
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    generator = TradingReportGenerator(
        results_dir=args.results_dir,
        summary_dir=args.summary_dir
    )
    
    generator.generate_report()