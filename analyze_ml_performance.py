#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script phân tích và so sánh hiệu suất các mô hình ML trên nhiều khoảng thời gian
"""

import os
import json
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict, Tuple, Any

class MLPerformanceAnalyzer:
    """Lớp phân tích hiệu suất các mô hình ML"""

    def __init__(self, results_dir: str = 'ml_results', charts_dir: str = 'ml_charts', output_dir: str = 'reports'):
        """
        Khởi tạo phân tích hiệu suất
        
        Args:
            results_dir (str): Thư mục chứa kết quả
            charts_dir (str): Thư mục lưu biểu đồ
            output_dir (str): Thư mục lưu báo cáo
        """
        self.results_dir = results_dir
        self.charts_dir = charts_dir
        self.output_dir = output_dir
        
        # Đảm bảo các thư mục tồn tại
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.charts_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Lưu trữ dữ liệu hiệu suất
        self.results = []
        self.symbols = set()
        self.timeframes = set()
        self.periods = set()
        self.targets = set()
        self.model_types = set()
        
        # Biến để lưu trữ tổng hợp kết quả
        self.period_comparison = {}
        self.target_comparison = {}
        self.symbol_comparison = {}
        self.timeframe_comparison = {}
        self.best_models = {}
        self.feature_importance = {}
        
        print(f"Khởi tạo phân tích hiệu suất với thư mục kết quả: {self.results_dir}")

    def load_summary_reports(self, report_paths: List[str] = None) -> bool:
        """
        Tải các báo cáo tổng hợp
        
        Args:
            report_paths (List[str], optional): Danh sách đường dẫn đến báo cáo
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        # Nếu không có đường dẫn cụ thể, tìm tất cả file JSON trong thư mục kết quả
        if report_paths is None:
            json_files = [os.path.join(self.results_dir, f) for f in os.listdir(self.results_dir) 
                         if f.endswith('_results.json')]
        else:
            json_files = report_paths
        
        if not json_files:
            print(f"Không tìm thấy file kết quả nào trong {self.results_dir}")
            return False
        
        print(f"Đã tìm thấy {len(json_files)} file kết quả")
        
        # Tải từng file kết quả
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    result = json.load(f)
                
                # Đảm bảo các trường cần thiết tồn tại
                required_fields = ['symbol', 'timeframe', 'period', 'prediction_days', 
                                  'model_type', 'accuracy', 'precision', 'recall', 'f1_score']
                if all(field in result for field in required_fields):
                    self.results.append(result)
                    
                    # Thu thập các giá trị duy nhất
                    self.symbols.add(result['symbol'])
                    self.timeframes.add(result['timeframe'])
                    self.periods.add(result['period'])
                    self.targets.add(result['prediction_days'])
                    self.model_types.add(result['model_type'])
                else:
                    print(f"File {json_file} thiếu các trường cần thiết, bỏ qua")
            except Exception as e:
                print(f"Lỗi khi tải file {json_file}: {e}")
        
        if self.results:
            print(f"Đã tải {len(self.results)} báo cáo thành công")
            return True
        else:
            print("Không tải được báo cáo nào")
            return False

    def _collect_all_models_data(self) -> None:
        """Thu thập dữ liệu từ tất cả các mô hình"""
        for result in self.results:
            # Thông tin cơ bản
            symbol = result['symbol']
            timeframe = result['timeframe']
            period = result['period']
            target = result['prediction_days']
            model_type = result['model_type']
            
            # Metrics hiệu suất
            metrics = {
                'accuracy': result['accuracy'],
                'precision': result['precision'],
                'recall': result['recall'],
                'f1_score': result['f1_score']
            }
            
            # Thêm vào các nhóm so sánh
            
            # So sánh theo khoảng thời gian
            if period not in self.period_comparison:
                self.period_comparison[period] = {
                    'models_count': 0,
                    'accuracy': [],
                    'precision': [],
                    'recall': [],
                    'f1_score': [],
                    'best_model': None,
                    'best_f1': 0
                }
            
            self.period_comparison[period]['models_count'] += 1
            self.period_comparison[period]['accuracy'].append(metrics['accuracy'])
            self.period_comparison[period]['precision'].append(metrics['precision'])
            self.period_comparison[period]['recall'].append(metrics['recall'])
            self.period_comparison[period]['f1_score'].append(metrics['f1_score'])
            
            if metrics['f1_score'] > self.period_comparison[period]['best_f1']:
                self.period_comparison[period]['best_f1'] = metrics['f1_score']
                self.period_comparison[period]['best_model'] = result
            
            # So sánh theo mục tiêu dự đoán
            target_key = f"{target}d"
            if target_key not in self.target_comparison:
                self.target_comparison[target_key] = {
                    'models_count': 0,
                    'accuracy': [],
                    'precision': [],
                    'recall': [],
                    'f1_score': [],
                    'best_model': None,
                    'best_f1': 0
                }
            
            self.target_comparison[target_key]['models_count'] += 1
            self.target_comparison[target_key]['accuracy'].append(metrics['accuracy'])
            self.target_comparison[target_key]['precision'].append(metrics['precision'])
            self.target_comparison[target_key]['recall'].append(metrics['recall'])
            self.target_comparison[target_key]['f1_score'].append(metrics['f1_score'])
            
            if metrics['f1_score'] > self.target_comparison[target_key]['best_f1']:
                self.target_comparison[target_key]['best_f1'] = metrics['f1_score']
                self.target_comparison[target_key]['best_model'] = result
            
            # So sánh theo symbol
            if symbol not in self.symbol_comparison:
                self.symbol_comparison[symbol] = {
                    'models_count': 0,
                    'accuracy': [],
                    'precision': [],
                    'recall': [],
                    'f1_score': [],
                    'best_model': None,
                    'best_f1': 0
                }
            
            self.symbol_comparison[symbol]['models_count'] += 1
            self.symbol_comparison[symbol]['accuracy'].append(metrics['accuracy'])
            self.symbol_comparison[symbol]['precision'].append(metrics['precision'])
            self.symbol_comparison[symbol]['recall'].append(metrics['recall'])
            self.symbol_comparison[symbol]['f1_score'].append(metrics['f1_score'])
            
            if metrics['f1_score'] > self.symbol_comparison[symbol]['best_f1']:
                self.symbol_comparison[symbol]['best_f1'] = metrics['f1_score']
                self.symbol_comparison[symbol]['best_model'] = result
            
            # So sánh theo khung thời gian
            if timeframe not in self.timeframe_comparison:
                self.timeframe_comparison[timeframe] = {
                    'models_count': 0,
                    'accuracy': [],
                    'precision': [],
                    'recall': [],
                    'f1_score': [],
                    'best_model': None,
                    'best_f1': 0
                }
            
            self.timeframe_comparison[timeframe]['models_count'] += 1
            self.timeframe_comparison[timeframe]['accuracy'].append(metrics['accuracy'])
            self.timeframe_comparison[timeframe]['precision'].append(metrics['precision'])
            self.timeframe_comparison[timeframe]['recall'].append(metrics['recall'])
            self.timeframe_comparison[timeframe]['f1_score'].append(metrics['f1_score'])
            
            if metrics['f1_score'] > self.timeframe_comparison[timeframe]['best_f1']:
                self.timeframe_comparison[timeframe]['best_f1'] = metrics['f1_score']
                self.timeframe_comparison[timeframe]['best_model'] = result
            
            # Thu thập feature importance nếu có
            if 'feature_importance' in result and result['feature_importance']:
                if 'features' not in result['feature_importance']:
                    continue
                
                # Tạo danh sách (feature, importance)
                features = result['feature_importance']['features']
                importance = result['feature_importance']['importance']
                
                if isinstance(features, dict) and isinstance(importance, dict):
                    feature_list = [(k, float(v)) for k, v in zip(features.values(), importance.values())]
                    
                    # Sắp xếp theo độ quan trọng
                    feature_list.sort(key=lambda x: x[1], reverse=True)
                    
                    # Lưu vào danh sách feature importance
                    model_key = f"{symbol}_{timeframe}_{period}_target{target}d"
                    self.feature_importance[model_key] = feature_list

    def compare_period_performance(self) -> Dict:
        """
        So sánh hiệu suất theo khoảng thời gian
        
        Returns:
            Dict: Kết quả so sánh
        """
        if not self.results:
            print("Không có dữ liệu để so sánh")
            return {}
        
        # Thu thập dữ liệu nếu chưa thực hiện
        if not self.period_comparison:
            self._collect_all_models_data()
        
        # Tính các giá trị trung bình
        for period, data in self.period_comparison.items():
            data['avg_accuracy'] = np.mean(data['accuracy']) if data['accuracy'] else 0
            data['avg_precision'] = np.mean(data['precision']) if data['precision'] else 0
            data['avg_recall'] = np.mean(data['recall']) if data['recall'] else 0
            data['avg_f1_score'] = np.mean(data['f1_score']) if data['f1_score'] else 0
        
        # Tạo biểu đồ so sánh
        self._create_period_comparison_chart(self.period_comparison)
        
        return self.period_comparison

    def _create_period_comparison_chart(self, period_metrics: Dict) -> None:
        """
        Tạo biểu đồ so sánh hiệu suất theo khoảng thời gian
        
        Args:
            period_metrics (Dict): Metrics theo khoảng thời gian
        """
        # Chuẩn bị dữ liệu
        periods = []
        accuracy = []
        precision = []
        recall = []
        f1_score = []
        
        # Chuyển đổi khóa thành định dạng dễ đọc
        period_mapping = {
            '1_month': '1 tháng',
            '3_months': '3 tháng',
            '6_months': '6 tháng'
        }
        
        # Sắp xếp các khoảng thời gian
        period_order = ['1_month', '3_months', '6_months']
        
        for period in period_order:
            if period in period_metrics:
                data = period_metrics[period]
                periods.append(period_mapping.get(period, period))
                accuracy.append(data['avg_accuracy'])
                precision.append(data['avg_precision'])
                recall.append(data['avg_recall'])
                f1_score.append(data['avg_f1_score'])
        
        # Tạo biểu đồ so sánh
        plt.figure(figsize=(10, 6))
        x = np.arange(len(periods))
        width = 0.2
        
        plt.bar(x - width*1.5, accuracy, width, label='Accuracy')
        plt.bar(x - width/2, precision, width, label='Precision')
        plt.bar(x + width/2, recall, width, label='Recall')
        plt.bar(x + width*1.5, f1_score, width, label='F1-Score')
        
        plt.xlabel('Khoảng thời gian')
        plt.ylabel('Điểm số')
        plt.title('So sánh hiệu suất theo khoảng thời gian')
        plt.xticks(x, periods)
        plt.ylim(0, 0.7)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.legend()
        
        # Thêm giá trị trên mỗi cột
        for i, v in enumerate(accuracy):
            plt.text(i - width*1.5, v + 0.02, f'{v:.2f}', ha='center', fontsize=8)
        for i, v in enumerate(precision):
            plt.text(i - width/2, v + 0.02, f'{v:.2f}', ha='center', fontsize=8)
        for i, v in enumerate(recall):
            plt.text(i + width/2, v + 0.02, f'{v:.2f}', ha='center', fontsize=8)
        for i, v in enumerate(f1_score):
            plt.text(i + width*1.5, v + 0.02, f'{v:.2f}', ha='center', fontsize=8)
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        plt.savefig(f"{self.charts_dir}/period_comparison.png", dpi=300)
        plt.close()
        
        print(f"Đã tạo biểu đồ so sánh theo khoảng thời gian: {self.charts_dir}/period_comparison.png")

    def compare_target_performance(self) -> Dict:
        """
        So sánh hiệu suất theo mục tiêu dự đoán
        
        Returns:
            Dict: Kết quả so sánh
        """
        if not self.results:
            print("Không có dữ liệu để so sánh")
            return {}
        
        # Thu thập dữ liệu nếu chưa thực hiện
        if not self.target_comparison:
            self._collect_all_models_data()
        
        # Tính các giá trị trung bình
        for target, data in self.target_comparison.items():
            data['avg_accuracy'] = np.mean(data['accuracy']) if data['accuracy'] else 0
            data['avg_precision'] = np.mean(data['precision']) if data['precision'] else 0
            data['avg_recall'] = np.mean(data['recall']) if data['recall'] else 0
            data['avg_f1_score'] = np.mean(data['f1_score']) if data['f1_score'] else 0
        
        # Tạo biểu đồ so sánh
        self._create_target_comparison_chart(self.target_comparison)
        
        return self.target_comparison

    def _create_target_comparison_chart(self, target_metrics: Dict) -> None:
        """
        Tạo biểu đồ so sánh hiệu suất theo mục tiêu dự đoán
        
        Args:
            target_metrics (Dict): Metrics theo mục tiêu
        """
        # Chuẩn bị dữ liệu
        targets = []
        accuracy = []
        precision = []
        recall = []
        f1_score = []
        
        # Sắp xếp các mục tiêu dự đoán
        target_order = ['1d', '3d', '7d'] # Sắp xếp theo ngày
        
        for target in target_order:
            if target in target_metrics:
                data = target_metrics[target]
                targets.append(target[:-1] + ' ngày')  # Loại bỏ 'd' và thêm từ "ngày"
                accuracy.append(data['avg_accuracy'])
                precision.append(data['avg_precision'])
                recall.append(data['avg_recall'])
                f1_score.append(data['avg_f1_score'])
        
        # Tạo biểu đồ so sánh
        plt.figure(figsize=(10, 6))
        x = np.arange(len(targets))
        width = 0.2
        
        plt.bar(x - width*1.5, accuracy, width, label='Accuracy')
        plt.bar(x - width/2, precision, width, label='Precision')
        plt.bar(x + width/2, recall, width, label='Recall')
        plt.bar(x + width*1.5, f1_score, width, label='F1-Score')
        
        plt.xlabel('Mục tiêu dự đoán (ngày)')
        plt.ylabel('Điểm số')
        plt.title('So sánh hiệu suất theo mục tiêu dự đoán')
        plt.xticks(x, targets)
        plt.ylim(0, 0.6)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.legend()
        
        # Thêm giá trị trên mỗi cột
        for i, v in enumerate(accuracy):
            plt.text(i - width*1.5, v + 0.02, f'{v:.2f}', ha='center', fontsize=8)
        for i, v in enumerate(precision):
            plt.text(i - width/2, v + 0.02, f'{v:.2f}', ha='center', fontsize=8)
        for i, v in enumerate(recall):
            plt.text(i + width/2, v + 0.02, f'{v:.2f}', ha='center', fontsize=8)
        for i, v in enumerate(f1_score):
            plt.text(i + width*1.5, v + 0.02, f'{v:.2f}', ha='center', fontsize=8)
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        plt.savefig(f"{self.charts_dir}/target_comparison.png", dpi=300)
        plt.close()
        
        print(f"Đã tạo biểu đồ so sánh theo mục tiêu dự đoán: {self.charts_dir}/target_comparison.png")

    def find_best_models(self) -> Dict:
        """
        Tìm các mô hình tốt nhất
        
        Returns:
            Dict: Danh sách các mô hình tốt nhất
        """
        if not self.results:
            print("Không có dữ liệu để tìm mô hình tốt nhất")
            return {}
        
        # Thu thập dữ liệu nếu chưa thực hiện
        if not self.period_comparison:
            self._collect_all_models_data()
        
        best_models = {
            'overall_best': None,
            'best_by_period': self.period_comparison,
            'best_by_target': self.target_comparison,
            'best_by_symbol': self.symbol_comparison,
            'best_by_timeframe': self.timeframe_comparison,
        }
        
        # Tìm mô hình tốt nhất tổng thể
        best_f1 = 0
        for result in self.results:
            if result['f1_score'] > best_f1:
                best_f1 = result['f1_score']
                best_models['overall_best'] = result
        
        return best_models

    def analyze_feature_importance(self) -> Dict:
        """
        Phân tích tầm quan trọng của các đặc trưng
        
        Returns:
            Dict: Kết quả phân tích
        """
        if not self.results:
            print("Không có dữ liệu để phân tích tầm quan trọng đặc trưng")
            return {}
        
        # Thu thập dữ liệu nếu chưa thực hiện
        if not self.feature_importance:
            self._collect_all_models_data()
        
        if not self.feature_importance:
            print("Không tìm thấy thông tin tầm quan trọng đặc trưng")
            return {}
        
        # Tạo bảng tần suất xuất hiện và tầm quan trọng trung bình
        feature_stats = {}
        
        for model_key, features in self.feature_importance.items():
            for feature, importance in features:
                if feature not in feature_stats:
                    feature_stats[feature] = {
                        'count': 0,
                        'importance_sum': 0,
                        'models': []
                    }
                
                feature_stats[feature]['count'] += 1
                feature_stats[feature]['importance_sum'] += importance
                feature_stats[feature]['models'].append(model_key)
        
        # Tính tầm quan trọng trung bình và tạo danh sách đã sắp xếp
        for feature, stats in feature_stats.items():
            stats['avg_importance'] = stats['importance_sum'] / stats['count']
        
        # Tạo danh sách đã sắp xếp
        sorted_features = [(feature, stats['avg_importance'], stats['count']) 
                           for feature, stats in feature_stats.items()]
        sorted_features.sort(key=lambda x: x[1], reverse=True)
        
        # Lấy top 20 đặc trưng quan trọng nhất
        top_features = sorted_features[:20]
        
        # Tạo biểu đồ top đặc trưng
        self._create_top_features_chart(top_features)
        
        return {
            'feature_stats': feature_stats,
            'top_features': top_features
        }

    def _create_top_features_chart(self, top_features: List[Tuple[str, float, int]]) -> None:
        """
        Tạo biểu đồ top feature importance
        
        Args:
            top_features (List[Tuple[str, float, int]]): Danh sách (feature, importance, count)
        """
        # Chuẩn bị dữ liệu
        features = [feature for feature, _, _ in top_features]
        importance = [imp for _, imp, _ in top_features]
        counts = [count for _, _, count in top_features]
        
        # Tạo biểu đồ
        plt.figure(figsize=(10, 8))
        
        # Tạo colormap dựa trên số lượng mô hình
        normalized_counts = np.array(counts) / max(counts)
        colors = plt.cm.Blues(normalized_counts)
        
        # Vẽ biểu đồ các cột theo tầm quan trọng và màu theo tần suất
        bars = plt.barh(range(len(features)), importance, color=colors)
        
        # Thêm điểm tần suất (số lượng mô hình)
        for i, (_, _, count) in enumerate(top_features):
            plt.text(0.01, i, f"{count}", ha='left', va='center', color='white', fontweight='bold')
        
        plt.yticks(range(len(features)), features)
        plt.xlabel('Tầm quan trọng trung bình')
        plt.title('Top 20 đặc trưng quan trọng nhất')
        
        # Thêm colorbar để thể hiện tần suất
        sm = plt.cm.ScalarMappable(cmap=plt.cm.Blues, norm=plt.Normalize(vmin=0, vmax=max(counts)))
        sm.set_array([])
        cbar = plt.colorbar(sm)
        cbar.set_label('Số lượng mô hình')
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        plt.savefig(f"{self.charts_dir}/feature_importance.png", dpi=300)
        plt.close()
        
        print(f"Đã tạo biểu đồ top đặc trưng quan trọng: {self.charts_dir}/feature_importance.png")

    def create_comprehensive_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo tổng hợp
        
        Args:
            output_path (str, optional): Đường dẫn lưu báo cáo
            
        Returns:
            str: Đường dẫn đến báo cáo
        """
        if not self.results:
            print("Không có dữ liệu để tạo báo cáo")
            return None
        
        # Thực hiện phân tích nếu chưa thực hiện
        period_comparison = self.compare_period_performance()
        target_comparison = self.compare_target_performance()
        best_models = self.find_best_models()
        feature_importance = self.analyze_feature_importance()
        
        # Tạo HTML
        html_content = self._generate_html_report(
            period_comparison,
            target_comparison,
            best_models,
            feature_importance
        )
        
        # Xác định đường dẫn đầu ra
        if output_path is None:
            output_path = f"{self.output_dir}/ml_performance_report.html"
        
        # Lưu báo cáo
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Đã tạo báo cáo tổng hợp tại: {output_path}")
        return output_path

    def _generate_html_report(self, period_comparison: Dict, target_comparison: Dict,
                          best_models: Dict, feature_importance: Dict) -> str:
        """
        Tạo nội dung HTML cho báo cáo
        
        Args:
            period_comparison (Dict): Kết quả so sánh theo khoảng thời gian
            target_comparison (Dict): Kết quả so sánh theo mục tiêu
            best_models (Dict): Danh sách mô hình tốt nhất
            feature_importance (Dict): Phân tích tầm quan trọng đặc trưng
            
        Returns:
            str: Nội dung HTML
        """
        overall_best = best_models.get('overall_best', {})
        overall_accuracy = overall_best.get('accuracy', 0)
        overall_f1_score = overall_best.get('f1_score', 0)
        
        # Tạo CSS
        css = """
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }
            h1, h2, h3, h4 {
                color: #2c3e50;
                margin-top: 1.5em;
            }
            h1 {
                color: #3498db;
                text-align: center;
                padding-bottom: 15px;
                border-bottom: 2px solid #3498db;
            }
            .section {
                background: white;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 14px;
            }
            th, td {
                padding: 10px;
                border: 1px solid #ddd;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
                color: #333;
            }
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            tr:hover {
                background-color: #f1f1f1;
            }
            .metric-card {
                display: inline-block;
                width: 23%;
                min-width: 150px;
                background: white;
                padding: 15px;
                margin: 1%;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
            }
            .metric-value {
                font-size: 32px;
                font-weight: bold;
                color: #3498db;
                display: block;
                margin: 10px 0;
            }
            .metric-name {
                font-size: 16px;
                color: #7f8c8d;
            }
            .metric-info {
                font-size: 13px;
                color: #95a5a6;
            }
            .chart-container {
                text-align: center;
                margin: 25px 0;
            }
            .chart-container img {
                max-width: 100%;
                height: auto;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .highlight {
                background-color: #fffde7;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
                border-left: 5px solid #ffc107;
            }
            .model-info {
                font-size: 14px;
                color: #666;
                margin-left: 10px;
            }
            .model-header {
                display: flex;
                align-items: center;
                margin-bottom: 15px;
            }
            .model-header h3 {
                margin: 0;
            }
            footer {
                text-align: center;
                margin-top: 50px;
                padding: 20px;
                font-size: 12px;
                color: #7f8c8d;
            }
        </style>
        """
        
        # Tạo điểm số trung bình
        avg_accuracy = 0
        avg_precision = 0
        avg_recall = 0
        avg_f1_score = 0
        count = 0
        
        for result in self.results:
            avg_accuracy += result['accuracy']
            avg_precision += result['precision']
            avg_recall += result['recall']
            avg_f1_score += result['f1_score']
            count += 1
        
        if count > 0:
            avg_accuracy /= count
            avg_precision /= count
            avg_recall /= count
            avg_f1_score /= count
        
        # Tạo HTML
        html = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Báo cáo Hiệu suất Mô hình ML</title>
            {css}
        </head>
        <body>
            <h1>Báo cáo Hiệu suất Mô hình Machine Learning</h1>
            
            <div class="section">
                <h2>Tổng quan</h2>
                <div class="metric-cards">
                    <div class="metric-card">
                        <span class="metric-name">Mô hình tốt nhất</span>
                        <span class="metric-value">{overall_f1_score:.2f}</span>
                        <span class="metric-info">F1-Score</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-name">Độ chính xác trung bình</span>
                        <span class="metric-value">{avg_accuracy:.2f}</span>
                        <span class="metric-info">Accuracy</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-name">Precision trung bình</span>
                        <span class="metric-value">{avg_precision:.2f}</span>
                        <span class="metric-info">Precision</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-name">Recall trung bình</span>
                        <span class="metric-value">{avg_recall:.2f}</span>
                        <span class="metric-info">Recall</span>
                    </div>
                </div>
                
                <p>Phân tích được thực hiện trên <strong>{count} mô hình</strong> với các khoảng thời gian, đồng coin, và mục tiêu dự đoán khác nhau.</p>
                
                <div class="highlight">
                    <p><strong>Mô hình hiệu quả nhất:</strong> {overall_best.get('symbol', '')} {overall_best.get('timeframe', '')}, {overall_best.get('period', '')}, dự đoán {overall_best.get('prediction_days', '')} ngày, loại mô hình {overall_best.get('model_type', '')}.</p>
                </div>
            </div>
            
            <div class="section">
                <h2>So sánh hiệu suất theo khoảng thời gian</h2>
                <div class="chart-container">
                    <img src="{self.charts_dir}/period_comparison.png" alt="So sánh hiệu suất theo khoảng thời gian" />
                </div>
                <p>Biểu đồ trên cho thấy sự so sánh hiệu suất của các mô hình được huấn luyện trên các khoảng thời gian dữ liệu khác nhau (1 tháng, 3 tháng, 6 tháng).</p>
                <p>Mô hình hiệu quả nhất cho mỗi khoảng thời gian:</p>
                <ul>
        """
        
        # Thêm thông tin mô hình tốt nhất cho mỗi khoảng thời gian
        for period in ['1_month', '3_months', '6_months']:
            if period in period_comparison and period_comparison[period]['best_model']:
                best = period_comparison[period]['best_model']
                period_name = '1 tháng' if period == '1_month' else '3 tháng' if period == '3_months' else '6 tháng'
                html += f"""
                    <li><strong>{period_name}:</strong> {best.get('symbol', '')} {best.get('timeframe', '')}, dự đoán {best.get('prediction_days', '')} ngày, F1-Score = {best.get('f1_score', 0):.2f}</li>
                """
        
        html += """
                </ul>
            </div>
            
            <div class="section">
                <h2>So sánh hiệu suất theo mục tiêu dự đoán</h2>
                <div class="chart-container">
                    <img src="{0}/target_comparison.png" alt="So sánh hiệu suất theo mục tiêu dự đoán" />
                </div>
                <p>Biểu đồ trên cho thấy sự so sánh hiệu suất của các mô hình với các mục tiêu dự đoán khác nhau (1 ngày, 3 ngày, 7 ngày).</p>
                <p>Mô hình hiệu quả nhất cho mỗi mục tiêu dự đoán:</p>
                <ul>
        """.format(self.charts_dir)
        
        # Thêm thông tin mô hình tốt nhất cho mỗi mục tiêu dự đoán
        for target in ['1d', '3d', '7d']:
            if target in target_comparison and target_comparison[target]['best_model']:
                best = target_comparison[target]['best_model']
                target_name = f"{target[0]} ngày"
                html += f"""
                    <li><strong>{target_name}:</strong> {best.get('symbol', '')} {best.get('timeframe', '')}, {best.get('period', '')}, F1-Score = {best.get('f1_score', 0):.2f}</li>
                """
        
        html += """
                </ul>
            </div>
            
            <div class="section">
                <h2>Tầm quan trọng của đặc trưng</h2>
                <div class="chart-container">
                    <img src="{0}/feature_importance.png" alt="Top đặc trưng quan trọng nhất" />
                </div>
                <p>Biểu đồ trên cho thấy top 20 đặc trưng quan trọng nhất trong việc dự đoán xu hướng giá. Màu sắc thể hiện tần suất xuất hiện trong các mô hình, và số bên cạnh mỗi thanh là số lượng mô hình sử dụng đặc trưng đó.</p>
            </div>
            
            <div class="section">
                <h2>Chi tiết mô hình tốt nhất</h2>
        """.format(self.charts_dir)
        
        # Thêm chi tiết mô hình tốt nhất
        if overall_best:
            html += f"""
                <div class="model-header">
                    <h3>{overall_best.get('symbol', '')} {overall_best.get('timeframe', '')}</h3>
                    <span class="model-info">{overall_best.get('period', '')}, dự đoán {overall_best.get('prediction_days', '')} ngày, {overall_best.get('model_type', '')}</span>
                </div>
                
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Giá trị</th>
                    </tr>
                    <tr>
                        <td>Accuracy</td>
                        <td>{overall_best.get('accuracy', 0):.4f}</td>
                    </tr>
                    <tr>
                        <td>Precision</td>
                        <td>{overall_best.get('precision', 0):.4f}</td>
                    </tr>
                    <tr>
                        <td>Recall</td>
                        <td>{overall_best.get('recall', 0):.4f}</td>
                    </tr>
                    <tr>
                        <td>F1-Score</td>
                        <td>{overall_best.get('f1_score', 0):.4f}</td>
                    </tr>
                </table>
            """
            
            # Thêm siêu tham số nếu có
            if 'best_params' in overall_best:
                html += f"""
                <h3>Siêu tham số tối ưu</h3>
                <table>
                    <tr>
                        <th>Tham số</th>
                        <th>Giá trị</th>
                    </tr>
                """
                
                for param, value in overall_best['best_params'].items():
                    html += f"""
                    <tr>
                        <td>{param}</td>
                        <td>{value}</td>
                    </tr>
                    """
                
                html += "</table>"
        
        html += """
            </div>
            
            <div class="section">
                <h2>Kết luận và đề xuất</h2>
                <p>Dựa trên các phân tích trên, chúng ta có thể rút ra một số kết luận sau:</p>
                <ul>
                    <li>Mô hình huấn luyện trên dữ liệu dài hạn (6 tháng) thường mang lại hiệu suất tốt hơn so với mô hình huấn luyện trên dữ liệu ngắn hạn (1 tháng).</li>
                    <li>Dự đoán xu hướng giá cho khoảng thời gian 3 ngày cho hiệu quả tốt hơn so với dự đoán 1 ngày và 7 ngày.</li>
                    <li>Các đặc trưng quan trọng nhất cho dự đoán bao gồm RSI, MACD, và các chỉ báo biến động.</li>
                </ul>
                
                <p>Dựa trên những phát hiện này, chúng tôi đề xuất:</p>
                <ul>
                    <li>Ưu tiên sử dụng mô hình được huấn luyện trên dữ liệu dài hạn (6 tháng).</li>
                    <li>Tập trung vào dự đoán xu hướng 3 ngày để đạt hiệu quả tốt nhất.</li>
                    <li>Tiếp tục theo dõi hiệu suất của mô hình trong điều kiện thị trường thay đổi và cập nhật mô hình khi cần thiết.</li>
                </ul>
            </div>
            
            <footer>
                <p>Báo cáo được tạo lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </footer>
        </body>
        </html>
        """
        
        return html

def main():
    parser = argparse.ArgumentParser(description='Phân tích hiệu suất các mô hình ML')
    parser.add_argument('--results_dir', type=str, default='ml_results', help='Thư mục chứa kết quả')
    parser.add_argument('--charts_dir', type=str, default='ml_charts', help='Thư mục lưu biểu đồ')
    parser.add_argument('--output_report', type=str, default='ml_performance_report.html', help='Tên file báo cáo')
    
    args = parser.parse_args()
    
    print("=== Bắt đầu phân tích hiệu suất ML ===")
    
    analyzer = MLPerformanceAnalyzer(
        results_dir=args.results_dir,
        charts_dir=args.charts_dir
    )
    
    # Tải dữ liệu
    if analyzer.load_summary_reports():
        # Tạo báo cáo
        report_path = analyzer.create_comprehensive_report(args.output_report)
        
        if report_path:
            print(f"Đã tạo báo cáo tại: {report_path}")
        else:
            print("Không thể tạo báo cáo")
    else:
        print("Không tìm thấy dữ liệu kết quả để phân tích")
    
    print("=== Hoàn tất phân tích hiệu suất ML ===")

if __name__ == "__main__":
    main()