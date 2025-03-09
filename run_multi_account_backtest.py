#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import argparse
import json
from datetime import datetime, timedelta
from tabulate import tabulate
import pandas as pd
import matplotlib.pyplot as plt
from backtest_small_account_strategy import SmallAccountBacktester

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("multi_account_backtest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("multi_account_backtest")

class MultiAccountBacktester:
    def __init__(self, account_sizes=None, start_date=None, end_date=None, timeframes=None):
        """
        Khởi tạo backtester cho nhiều kích thước tài khoản và timeframe
        
        Args:
            account_sizes (list): Danh sách kích thước tài khoản ($)
            start_date (str): Ngày bắt đầu (YYYY-MM-DD)
            end_date (str): Ngày kết thúc (YYYY-MM-DD)
            timeframes (list): Danh sách khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)
        """
        # Thiết lập thời gian
        self.end_date = datetime.now() if end_date is None else datetime.strptime(end_date, '%Y-%m-%d')
        if start_date is None:
            self.start_date = self.end_date - timedelta(days=90)  # Mặc định 3 tháng
        else:
            self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        # Thiết lập kích thước tài khoản
        self.account_sizes = [100, 200, 300] if account_sizes is None else account_sizes
        
        # Thiết lập timeframe
        self.timeframes = ['1h'] if timeframes is None else timeframes
        
        # Kết quả
        self.results = {}
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs('backtest_results', exist_ok=True)
        os.makedirs('backtest_charts', exist_ok=True)
        os.makedirs('backtest_summary', exist_ok=True)
        
        logger.info(f"Khởi tạo multi account backtester từ {self.start_date.strftime('%Y-%m-%d')} đến {self.end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Các kích thước tài khoản: {self.account_sizes}")
        logger.info(f"Các khung thời gian: {self.timeframes}")
    
    def run_backtest(self):
        """
        Chạy backtest cho tất cả các kích thước tài khoản và timeframe
        """
        logger.info(f"Bắt đầu backtest cho {len(self.account_sizes) * len(self.timeframes)} cấu hình...")
        
        # Chạy backtest cho từng cấu hình
        for account_size in self.account_sizes:
            self.results[account_size] = {}
            
            for timeframe in self.timeframes:
                logger.info(f"\n" + "="*80)
                logger.info(f"BACKTEST CHO TÀI KHOẢN ${account_size}, TIMEFRAME {timeframe}")
                logger.info("="*80)
                
                # Tạo backtester
                backtester = SmallAccountBacktester(
                    start_date=self.start_date.strftime('%Y-%m-%d'),
                    end_date=self.end_date.strftime('%Y-%m-%d'),
                    account_size=account_size,
                    timeframe=timeframe
                )
                
                # Chạy backtest
                backtester.run()
                
                # Lưu kết quả
                self.results[account_size][timeframe] = backtester.summary
        
        # Tạo báo cáo tổng hợp
        self.create_summary_report()
        
        logger.info(f"Hoàn thành backtest cho tất cả cấu hình")
        
    def create_summary_report(self):
        """
        Tạo báo cáo tổng hợp
        """
        logger.info("\n" + "="*80)
        logger.info("BÁO CÁO TỔNG HỢP")
        logger.info("="*80)
        
        # Tạo bảng so sánh
        comparison = []
        
        for account_size in self.account_sizes:
            for timeframe in self.timeframes:
                summary = self.results.get(account_size, {}).get(timeframe)
                
                if summary:
                    comparison.append({
                        'Tài khoản': f"${account_size}",
                        'Timeframe': timeframe,
                        'Đòn bẩy': f"{summary.get('leverage')}x",
                        'Rủi ro': f"{summary.get('risk_percentage')}%",
                        'Tổng giao dịch': summary.get('total_trades'),
                        'Tỷ lệ thắng': f"{summary.get('overall_win_rate', 0) * 100:.2f}%",
                        'Lợi nhuận': f"{summary.get('total_net_profit_pct', 0):.2f}%",
                        'Drawdown': f"{summary.get('avg_max_drawdown_pct', 0):.2f}%",
                        'Profit Factor': f"{summary.get('avg_profit_factor', 0):.2f}",
                        'Cặp tốt nhất': f"{summary.get('best_symbol')} ({summary.get('best_profit_pct', 0):.2f}%)",
                        'Cặp tệ nhất': f"{summary.get('worst_symbol')} ({summary.get('worst_profit_pct', 0):.2f}%)"
                    })
        
        # In bảng so sánh
        logger.info("\nSO SÁNH CÁC CẤU HÌNH")
        logger.info(tabulate(comparison, headers='keys', tablefmt='grid'))
        
        # Tạo DataFrame
        df_comparison = pd.DataFrame(comparison)
        
        # Lưu vào file CSV
        csv_filename = f"backtest_summary/comparison_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.csv"
        df_comparison.to_csv(csv_filename, index=False)
        
        logger.info(f"Đã lưu báo cáo so sánh vào file {csv_filename}")
        
        # Vẽ biểu đồ so sánh
        try:
            # 1. So sánh lợi nhuận
            plt.figure(figsize=(12, 8))
            
            df_plot = df_comparison.copy()
            df_plot['Lợi nhuận'] = df_plot['Lợi nhuận'].str.rstrip('%').astype(float)
            
            # Nhóm theo tài khoản và timeframe
            pivot = df_plot.pivot_table(
                index='Tài khoản', 
                columns='Timeframe', 
                values='Lợi nhuận', 
                aggfunc='mean'
            )
            
            pivot.plot(kind='bar', ax=plt.gca())
            plt.title(f'So sánh lợi nhuận (%) theo tài khoản và timeframe')
            plt.xlabel('Tài khoản')
            plt.ylabel('Lợi nhuận (%)')
            plt.grid(True, alpha=0.3)
            plt.legend(title='Timeframe')
            plt.tight_layout()
            
            # Lưu biểu đồ
            profit_chart_filename = f"backtest_summary/profit_comparison_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.png"
            plt.savefig(profit_chart_filename)
            plt.close()
            
            logger.info(f"Đã lưu biểu đồ so sánh lợi nhuận vào file {profit_chart_filename}")
            
            # 2. So sánh tỷ lệ thắng
            plt.figure(figsize=(12, 8))
            
            df_plot['Tỷ lệ thắng'] = df_plot['Tỷ lệ thắng'].str.rstrip('%').astype(float)
            
            # Nhóm theo tài khoản và timeframe
            pivot = df_plot.pivot_table(
                index='Tài khoản', 
                columns='Timeframe', 
                values='Tỷ lệ thắng', 
                aggfunc='mean'
            )
            
            pivot.plot(kind='bar', ax=plt.gca())
            plt.axhline(y=50, color='r', linestyle='--', label='50%')
            plt.title(f'So sánh tỷ lệ thắng (%) theo tài khoản và timeframe')
            plt.xlabel('Tài khoản')
            plt.ylabel('Tỷ lệ thắng (%)')
            plt.grid(True, alpha=0.3)
            plt.legend(title='Timeframe')
            plt.tight_layout()
            
            # Lưu biểu đồ
            winrate_chart_filename = f"backtest_summary/winrate_comparison_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.png"
            plt.savefig(winrate_chart_filename)
            plt.close()
            
            logger.info(f"Đã lưu biểu đồ so sánh tỷ lệ thắng vào file {winrate_chart_filename}")
            
            # 3. So sánh profit factor
            plt.figure(figsize=(12, 8))
            
            df_plot['Profit Factor'] = df_plot['Profit Factor'].str.rstrip('').astype(float)
            
            # Nhóm theo tài khoản và timeframe
            pivot = df_plot.pivot_table(
                index='Tài khoản', 
                columns='Timeframe', 
                values='Profit Factor', 
                aggfunc='mean'
            )
            
            pivot.plot(kind='bar', ax=plt.gca())
            plt.axhline(y=1, color='r', linestyle='--', label='1.0')
            plt.title(f'So sánh Profit Factor theo tài khoản và timeframe')
            plt.xlabel('Tài khoản')
            plt.ylabel('Profit Factor')
            plt.grid(True, alpha=0.3)
            plt.legend(title='Timeframe')
            plt.tight_layout()
            
            # Lưu biểu đồ
            pf_chart_filename = f"backtest_summary/profit_factor_comparison_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.png"
            plt.savefig(pf_chart_filename)
            plt.close()
            
            logger.info(f"Đã lưu biểu đồ so sánh Profit Factor vào file {pf_chart_filename}")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ so sánh: {str(e)}")
        
        # Tạo báo cáo JSON
        try:
            json_filename = f"backtest_summary/summary_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.json"
            
            with open(json_filename, 'w') as f:
                json.dump(self.results, f, indent=4)
                
            logger.info(f"Đã lưu báo cáo tổng hợp vào file {json_filename}")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu báo cáo JSON: {str(e)}")

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Backtest cho nhiều kích thước tài khoản')
    parser.add_argument('--account-sizes', type=int, nargs='+', default=[100, 200, 300], help='Danh sách kích thước tài khoản ($)')
    parser.add_argument('--start-date', type=str, help='Ngày bắt đầu (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='Ngày kết thúc (YYYY-MM-DD)')
    parser.add_argument('--timeframes', type=str, nargs='+', default=['1h'], help='Danh sách khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)')
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    backtester = MultiAccountBacktester(
        account_sizes=args.account_sizes,
        start_date=args.start_date,
        end_date=args.end_date,
        timeframes=args.timeframes
    )
    
    backtester.run_backtest()