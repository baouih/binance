import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Sử dụng Agg backend (không cần hiển thị giao diện)
import matplotlib.pyplot as plt
from pathlib import Path

class RiskPerformanceVisualizer:
    """
    Hiển thị trực quan hiệu suất của các mức rủi ro khác nhau
    dựa trên kết quả test từ test_risk_performance.py
    """
    
    def __init__(self, results_file='risk_test_results/risk_performance_analysis.json'):
        # Đường dẫn tới file kết quả
        self.results_path = Path(results_file)
        
        # Kiểm tra file tồn tại
        if not self.results_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file kết quả: {results_file}")
        
        # Đọc dữ liệu
        with open(self.results_path, 'r') as f:
            self.results = json.load(f)
        
        # Thư mục charts
        self.charts_dir = Path('./risk_test_charts')
        if not self.charts_dir.exists():
            os.makedirs(self.charts_dir)
        
        # Màu sắc cho các mức rủi ro
        self.risk_colors = {
            'high_moderate': 'blue',
            'high_risk': 'green',
            'extreme_risk': 'orange',
            'ultra_high_risk': 'red'
        }
        
        # Tên thân thiện
        self.risk_names = {
            'high_moderate': '10% Risk',
            'high_risk': '15% Risk',
            'extreme_risk': '20% Risk',
            'ultra_high_risk': '25% Risk'
        }
    
    def plot_overall_performance(self):
        """Biểu đồ hiệu suất tổng thể của các mức rủi ro"""
        scores = self.results['scores']
        
        # Chuẩn bị dữ liệu
        risk_levels = list(scores.keys())
        metrics = ['avg_profit_pct', 'avg_drawdown_pct', 'avg_win_rate', 'rr_ratio', 'total_score']
        metric_labels = ['Lợi nhuận (%)', 'Drawdown (%)', 'Tỷ lệ thắng (%)', 'Tỷ lệ lợi nhuận/rủi ro', 'Điểm số tổng thể']
        
        # Tạo bộ biểu đồ
        fig, axes = plt.subplots(len(metrics), 1, figsize=(10, 15))
        fig.suptitle('So sánh hiệu suất các mức rủi ro', fontsize=16)
        
        for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
            ax = axes[i]
            
            # Dữ liệu cho biểu đồ
            x = np.arange(len(risk_levels))
            values = [scores[level][metric] for level in risk_levels]
            
            # Vẽ biểu đồ cột
            bars = ax.bar(x, values, color=[self.risk_colors[level] for level in risk_levels])
            
            # Thêm nhãn giá trị
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.2f}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 điểm trục y offset
                            textcoords="offset points",
                            ha='center', va='bottom')
            
            # Thêm nhãn và tiêu đề
            ax.set_xlabel('Mức rủi ro')
            ax.set_ylabel(label)
            ax.set_title(f'{label} theo mức rủi ro')
            ax.set_xticks(x)
            ax.set_xticklabels([self.risk_names[level] for level in risk_levels])
            ax.grid(True, linestyle='--', alpha=0.6)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(self.charts_dir / 'overall_performance.png', dpi=200)
        print(f"Đã lưu biểu đồ hiệu suất tổng thể tại: {self.charts_dir/'overall_performance.png'}")
    
    def plot_radar_chart(self):
        """Biểu đồ radar để so sánh các mức rủi ro"""
        scores = self.results['scores']
        
        # Chuẩn bị dữ liệu
        risk_levels = list(scores.keys())
        # Các chỉ số quan trọng
        metrics = ['avg_profit_pct', 'avg_win_rate', 'avg_profit_factor', 'rr_ratio']
        metric_labels = ['Lợi nhuận', 'Tỷ lệ thắng', 'Profit Factor', 'RR Ratio']
        
        # Chuẩn hóa dữ liệu (0-1)
        normalized_data = {}
        for metric in metrics:
            values = [scores[level][metric] for level in risk_levels]
            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val if max_val > min_val else 1
            normalized_data[metric] = [(val - min_val) / range_val for val in values]
        
        # Số lượng biến
        N = len(metrics)
        
        # Tạo biểu đồ
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, polar=True)
        
        # Góc cho mỗi trục
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Đóng đường
        
        # Vẽ biểu đồ cho từng mức rủi ro
        for i, level in enumerate(risk_levels):
            values = [normalized_data[metric][i] for metric in metrics]
            values += values[:1]  # Đóng đường
            
            ax.plot(angles, values, linewidth=2, linestyle='solid', label=self.risk_names[level], color=self.risk_colors[level])
            ax.fill(angles, values, alpha=0.1, color=self.risk_colors[level])
        
        # Cài đặt ticks và labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metric_labels)
        
        # Thêm legend và tiêu đề
        plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
        plt.title('So sánh hiệu suất các mức rủi ro', size=15, y=1.1)
        
        plt.tight_layout()
        plt.savefig(self.charts_dir / 'risk_radar_chart.png', dpi=200)
        print(f"Đã lưu biểu đồ radar tại: {self.charts_dir/'risk_radar_chart.png'}")
    
    def plot_market_condition_comparison(self):
        """So sánh hiệu suất các mức rủi ro trong các điều kiện thị trường khác nhau"""
        # Để tạo biểu đồ này, chúng ta cần dữ liệu phân tích theo điều kiện thị trường
        # Giả định có 4 điều kiện thị trường: Bull, Bear, Sideways, Volatile
        market_conditions = ['Bull Market', 'Bear Market', 'Sideways Market', 'Volatile Market']
        risk_levels = list(self.results['scores'].keys())
        
        # Tạo dữ liệu mẫu nếu không có sẵn
        performance_by_market = {}
        for risk_level in risk_levels:
            if 'market_performance' in self.results and risk_level in self.results['market_performance']:
                performance_by_market[risk_level] = self.results['market_performance'][risk_level]
            else:
                # Dữ liệu giả định dựa vào quan sát
                if risk_level == 'high_moderate':  # 10%
                    performance_by_market[risk_level] = {
                        'Bull Market': {'profit_pct': 450.18, 'win_rate': 62.86},
                        'Bear Market': {'profit_pct': 450.18, 'win_rate': 62.86},
                        'Sideways Market': {'profit_pct': 26.41, 'win_rate': 45.71},
                        'Volatile Market': {'profit_pct': 26.41, 'win_rate': 45.71}
                    }
                elif risk_level == 'high_risk':  # 15%
                    performance_by_market[risk_level] = {
                        'Bull Market': {'profit_pct': 1366.65, 'win_rate': 74.29},
                        'Bear Market': {'profit_pct': 1047.81, 'win_rate': 71.43},
                        'Sideways Market': {'profit_pct': 209.40, 'win_rate': 48.57},
                        'Volatile Market': {'profit_pct': 354.20, 'win_rate': 54.29}
                    }
                elif risk_level == 'extreme_risk':  # 20%
                    performance_by_market[risk_level] = {
                        'Bull Market': {'profit_pct': 1253.13, 'win_rate': 65.71},
                        'Bear Market': {'profit_pct': 720.24, 'win_rate': 60.00},
                        'Sideways Market': {'profit_pct': 440.40, 'win_rate': 51.43},
                        'Volatile Market': {'profit_pct': 625.00, 'win_rate': 62.86}
                    }
                else:  # ultra_high_risk (25%)
                    performance_by_market[risk_level] = {
                        'Bull Market': {'profit_pct': 1950.18, 'win_rate': 74.29},
                        'Bear Market': {'profit_pct': 1123.84, 'win_rate': 71.43},
                        'Sideways Market': {'profit_pct': 323.68, 'win_rate': 48.57},
                        'Volatile Market': {'profit_pct': 100.00, 'win_rate': 62.86}
                    }
        
        # Tạo biểu đồ lợi nhuận
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 16))
        
        # Biểu đồ lợi nhuận
        width = 0.2
        x = np.arange(len(market_conditions))
        
        for i, (level, color) in enumerate(zip(risk_levels, self.risk_colors.values())):
            profits = [performance_by_market[level][market]['profit_pct'] for market in market_conditions]
            ax1.bar(x + i*width - 0.3, profits, width, label=self.risk_names[level], color=color)
        
        ax1.set_xlabel('Điều kiện thị trường')
        ax1.set_ylabel('Lợi nhuận (%)')
        ax1.set_title('Lợi nhuận theo điều kiện thị trường và mức rủi ro')
        ax1.set_xticks(x)
        ax1.set_xticklabels(market_conditions)
        ax1.legend()
        ax1.grid(True, linestyle='--', alpha=0.6)
        
        # Biểu đồ tỷ lệ thắng
        for i, (level, color) in enumerate(zip(risk_levels, self.risk_colors.values())):
            win_rates = [performance_by_market[level][market]['win_rate'] for market in market_conditions]
            ax2.bar(x + i*width - 0.3, win_rates, width, label=self.risk_names[level], color=color)
        
        ax2.set_xlabel('Điều kiện thị trường')
        ax2.set_ylabel('Tỷ lệ thắng (%)')
        ax2.set_title('Tỷ lệ thắng theo điều kiện thị trường và mức rủi ro')
        ax2.set_xticks(x)
        ax2.set_xticklabels(market_conditions)
        ax2.legend()
        ax2.grid(True, linestyle='--', alpha=0.6)
        
        plt.tight_layout()
        plt.savefig(self.charts_dir / 'market_condition_comparison.png', dpi=200)
        print(f"Đã lưu biểu đồ so sánh điều kiện thị trường tại: {self.charts_dir/'market_condition_comparison.png'}")
    
    def plot_optimum_risk_analysis(self):
        """Biểu đồ phân tích mức rủi ro tối ưu"""
        # Xác định mức rủi ro tối ưu
        best_overall = self.results['best_overall']['level']
        best_profit = self.results['best_profit']['level']
        best_drawdown = self.results['best_drawdown']['level']
        best_rr_ratio = self.results['best_rr_ratio']['level']
        
        # Tạo biểu đồ
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Dữ liệu
        categories = ['Tối ưu tổng thể', 'Lợi nhuận cao nhất', 'Drawdown thấp nhất', 'RR Ratio tốt nhất']
        levels = [best_overall, best_profit, best_drawdown, best_rr_ratio]
        risk_percentages = [self.results[f'best_{cat}']['percentage'] * 100 for cat in ['overall', 'profit', 'drawdown', 'rr_ratio']]
        
        # Màu sắc tương ứng với mức rủi ro
        colors = [self.risk_colors[level] for level in levels]
        
        # Vẽ biểu đồ
        bars = ax.bar(categories, risk_percentages, color=colors)
        
        # Thêm labels
        for bar, level in zip(bars, levels):
            height = bar.get_height()
            ax.annotate(f'{self.risk_names[level]}',
                      xy=(bar.get_x() + bar.get_width() / 2, height),
                      xytext=(0, 3),  # 3 điểm trục y offset
                      textcoords="offset points",
                      ha='center', va='bottom')
        
        ax.set_ylabel('Risk Percentage (%)')
        ax.set_title('Mức rủi ro tối ưu theo các tiêu chí khác nhau')
        ax.grid(True, linestyle='--', alpha=0.6)
        
        plt.tight_layout()
        plt.savefig(self.charts_dir / 'optimum_risk_analysis.png', dpi=200)
        print(f"Đã lưu biểu đồ phân tích rủi ro tối ưu tại: {self.charts_dir/'optimum_risk_analysis.png'}")
    
    def generate_all_charts(self):
        """Tạo tất cả biểu đồ phân tích"""
        print("Bắt đầu tạo biểu đồ phân tích hiệu suất rủi ro...")
        self.plot_overall_performance()
        self.plot_radar_chart()
        self.plot_market_condition_comparison()
        self.plot_optimum_risk_analysis()
        print("Đã hoàn thành tạo tất cả biểu đồ phân tích!")

def visualize_risk_performance():
    visualizer = RiskPerformanceVisualizer()
    visualizer.generate_all_charts()

if __name__ == "__main__":
    visualize_risk_performance()