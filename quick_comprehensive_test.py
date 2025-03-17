#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime, timedelta
from pathlib import Path
from tabulate import tabulate
from concurrent.futures import ThreadPoolExecutor, as_completed

# Nhập các module cần thiết
from adaptive_risk_manager import AdaptiveRiskManager
from multi_coin_backtest import MultiCoinBacktester

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('quick_comprehensive_test')

class QuickComprehensiveRiskTester:
    """
    Kiểm tra nhanh với một số cặp tiền điện tử và mức độ rủi ro
    """
    def __init__(self):
        """Khởi tạo trình kiểm tra rủi ro nhanh"""
        self.risk_manager = AdaptiveRiskManager()
        
        # Thư mục kết quả
        self.results_dir = 'quick_test_results/'
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Các mức rủi ro cần kiểm tra (chọn 3 mức)
        self.risk_levels = ['low', 'medium', 'high']
        
        # Danh sách các cặp tiền (chọn 3 cặp tiền chính)
        self.coins = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT'
        ]
        
        # Thời gian backtest
        self.backtest_days = 30  # 1 tháng
        
    def run_all_risk_levels(self):
        """Chạy backtest cho tất cả các mức rủi ro đã chọn"""
        results_by_risk = {}
        
        # Chạy backtest cho từng mức rủi ro
        for risk_level in self.risk_levels:
            logger.info(f"===== BẮT ĐẦU KIỂM TRA NHANH MỨC RỦI RO: {risk_level.upper()} =====")
            
            # Thiết lập mức rủi ro cho risk manager
            self.risk_manager.set_risk_level(risk_level)
            
            # Khởi tạo backtester mới với mức rủi ro hiện tại
            backtester = MultiCoinBacktester(
                coins=self.coins,
                backtest_days=self.backtest_days,
                results_dir=self.results_dir
            )
            
            # Chạy backtest và lấy kết quả
            results = backtester.run()
            
            # Lưu kết quả
            results_by_risk[risk_level] = results
            
            # Để không làm quá tải API
            time.sleep(2)
        
        # Tính hiệu suất tổng hợp và tạo báo cáo so sánh
        self.generate_comparison_report(results_by_risk)
    
    def generate_comparison_report(self, results_by_risk):
        """Tạo báo cáo so sánh các mức rủi ro"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Tạo DataFrame cho báo cáo so sánh
        comparison_data = []
        
        for risk_level, results in results_by_risk.items():
            # Tính hiệu suất trung bình
            avg_profit = np.mean([item['profit_pct'] for item in results])
            avg_drawdown = np.mean([item['max_drawdown'] for item in results])
            avg_win_rate = np.mean([item['win_rate'] for item in results])
            avg_profit_factor = np.mean([item['profit_factor'] for item in results])
            total_trades = sum([item['trades_count'] for item in results])
            
            # Lấy thông tin rủi ro
            risk_config = self.risk_manager.config['risk_levels'].get(risk_level, {})
            risk_per_trade = risk_config.get('risk_per_trade', 0)
            max_leverage = risk_config.get('max_leverage', 0)
            max_positions = risk_config.get('max_open_positions', 0)
            risk_description = risk_config.get('risk_level_description', '')
            
            # Thêm vào dữ liệu so sánh
            comparison_data.append({
                'Risk Level': risk_level,
                'Description': risk_description,
                'Profit (%)': avg_profit,
                'Max Drawdown (%)': avg_drawdown,
                'Win Rate (%)': avg_win_rate,
                'Profit Factor': avg_profit_factor,
                'Total Trades': total_trades,
                'Risk Per Trade (%)': risk_per_trade,
                'Max Leverage': max_leverage,
                'Max Positions': max_positions
            })
        
        # Sắp xếp theo lợi nhuận (từ cao đến thấp)
        comparison_data.sort(key=lambda x: x['Profit (%)'], reverse=True)
        
        # Tạo DataFrame
        df_comparison = pd.DataFrame(comparison_data)
        
        # Lưu báo cáo so sánh
        report_file = f"{self.results_dir}quick_risk_comparison_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write("===== SO SÁNH NHANH HIỆU SUẤT CÁC MỨC ĐỘ RỦI RO =====\n\n")
            f.write(f"Thời gian backtest: {self.backtest_days} ngày gần nhất\n")
            f.write(f"Các cặp tiền kiểm tra: {', '.join(self.coins)}\n\n")
            
            # In bảng so sánh
            f.write(tabulate(df_comparison, headers='keys', tablefmt='grid', 
                            floatfmt=".2f", showindex=False))
            
            # Phân tích chi tiết từng mức rủi ro
            f.write("\n\n===== PHÂN TÍCH CHI TIẾT TỪNG CẶP TIỀN THEO MỨC RỦI RO =====\n")
            
            for risk_level in self.risk_levels:
                results = results_by_risk[risk_level]
                
                # Sắp xếp kết quả từng coin theo lợi nhuận
                results.sort(key=lambda x: x['profit_pct'], reverse=True)
                
                f.write(f"\n----- MỨC RỦI RO: {risk_level.upper()} -----\n")
                f.write("XẾP HẠNG HIỆU SUẤT COINS:\n")
                
                for i, item in enumerate(results):
                    f.write(f"{i+1}. {item['symbol']}: {item['profit_pct']:.2f}%, DD: {item['max_drawdown']:.2f}%, ")
                    f.write(f"Số lệnh: {item['trades_count']}, Win rate: {item['win_rate']:.2f}%, PF: {item['profit_factor']:.2f}\n")
        
        logger.info(f"Đã tạo báo cáo so sánh nhanh tại {report_file}")
        
        # Tạo biểu đồ so sánh
        self.create_comparison_charts(df_comparison, timestamp)
        
        # In kết quả
        print("\n===== KẾT QUẢ KIỂM TRA NHANH CÁC MỨC RỦI RO =====")
        print(tabulate(df_comparison, headers='keys', tablefmt='grid', floatfmt=".2f", showindex=False))
        print(f"\nXem báo cáo chi tiết tại: {report_file}")
    
    def create_comparison_charts(self, df_comparison, timestamp):
        """
        Tạo biểu đồ so sánh hiệu suất giữa các mức rủi ro
        
        Args:
            df_comparison: DataFrame chứa dữ liệu so sánh
            timestamp: Dấu thời gian cho tên file
        """
        try:
            plt.figure(figsize=(16, 12))
            gs = gridspec.GridSpec(2, 2)
            
            # Biểu đồ 1: So sánh Lợi nhuận %
            ax1 = plt.subplot(gs[0, 0])
            bars = ax1.bar(df_comparison['Risk Level'], df_comparison['Profit (%)'], color='green')
            ax1.set_title('Lợi nhuận theo mức rủi ro (%)')
            ax1.set_ylabel('Lợi nhuận (%)')
            ax1.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Thêm giá trị trên các cột
            for bar in bars:
                height = bar.get_height()
                if height < 0:
                    color = 'red'
                    y_pos = height - 3
                else:
                    color = 'black'
                    y_pos = height + 0.5
                ax1.text(bar.get_x() + bar.get_width()/2., y_pos,
                        f'{height:.2f}%', ha='center', color=color, fontweight='bold')
            
            # Biểu đồ 2: So sánh Drawdown %
            ax2 = plt.subplot(gs[0, 1])
            bars = ax2.bar(df_comparison['Risk Level'], df_comparison['Max Drawdown (%)'], color='red')
            ax2.set_title('Drawdown tối đa theo mức rủi ro (%)')
            ax2.set_ylabel('Drawdown (%)')
            ax2.grid(axis='y', linestyle='--', alpha=0.7)
            
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{height:.2f}%', ha='center', fontweight='bold')
            
            # Biểu đồ 3: So sánh Win Rate %
            ax3 = plt.subplot(gs[1, 0])
            bars = ax3.bar(df_comparison['Risk Level'], df_comparison['Win Rate (%)'], color='blue')
            ax3.set_title('Tỷ lệ thắng theo mức rủi ro (%)')
            ax3.set_ylabel('Win Rate (%)')
            ax3.grid(axis='y', linestyle='--', alpha=0.7)
            
            for bar in bars:
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{height:.2f}%', ha='center', fontweight='bold')
            
            # Biểu đồ 4: So sánh Profit Factor
            ax4 = plt.subplot(gs[1, 1])
            bars = ax4.bar(df_comparison['Risk Level'], df_comparison['Profit Factor'], color='purple')
            ax4.set_title('Profit Factor theo mức rủi ro')
            ax4.set_ylabel('Profit Factor')
            ax4.grid(axis='y', linestyle='--', alpha=0.7)
            
            for bar in bars:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{height:.2f}', ha='center', fontweight='bold')
            
            plt.tight_layout()
            
            # Lưu biểu đồ
            chart_file = f"{self.results_dir}quick_risk_comparison_chart_{timestamp}.png"
            plt.savefig(chart_file, dpi=200)
            
            logger.info(f"Đã tạo biểu đồ so sánh tại {chart_file}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ so sánh: {str(e)}")

if __name__ == "__main__":
    tester = QuickComprehensiveRiskTester()
    tester.run_all_risk_levels()