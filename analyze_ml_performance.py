#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script phân tích và so sánh hiệu suất các mô hình ML trên nhiều khoảng thời gian

Script này đọc và phân tích kết quả của các mô hình ML đã huấn luyện trên các
khoảng thời gian khác nhau, tạo biểu đồ so sánh và báo cáo tổng hợp.
"""

import os
import json
import glob
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any
from datetime import datetime

# Thiết lập cho matplotlib
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.family'] = 'DejaVu Sans'

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
        os.makedirs(output_dir, exist_ok=True)
        
        # Dữ liệu kết quả
        self.results = []
        self.summary = {}
        
        # Các biến phân tích
        self.symbols = set()
        self.timeframes = set()
        self.periods = set()
        self.prediction_days = set()
        self.model_types = set()
        
    def load_summary_reports(self, report_paths: List[str] = None) -> bool:
        """
        Tải các báo cáo tổng hợp
        
        Args:
            report_paths (List[str], optional): Danh sách đường dẫn đến báo cáo
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            # Nếu không có danh sách cụ thể, tìm tất cả file JSON trong thư mục kết quả
            if report_paths is None:
                report_paths = glob.glob(os.path.join(self.results_dir, '*_results.json'))
            
            if not report_paths:
                print(f"Không tìm thấy báo cáo nào trong {self.results_dir}")
                return False
            
            # Tải từng báo cáo
            for path in report_paths:
                try:
                    with open(path, 'r') as f:
                        result = json.load(f)
                        
                    # Thu thập thông tin
                    self.symbols.add(result.get('symbol', 'unknown'))
                    self.timeframes.add(result.get('timeframe', 'unknown'))
                    self.periods.add(result.get('period', 'unknown'))
                    self.prediction_days.add(result.get('prediction_days', 0))
                    self.model_types.add(result.get('model_type', 'unknown'))
                    
                    # Thêm vào danh sách kết quả
                    self.results.append(result)
                except Exception as e:
                    print(f"Không thể tải báo cáo {path}: {e}")
            
            print(f"Đã tải {len(self.results)} báo cáo")
            return True
        except Exception as e:
            print(f"Lỗi khi tải các báo cáo: {e}")
            return False
    
    def _collect_all_models_data(self) -> None:
        """Thu thập dữ liệu từ tất cả các mô hình"""
        if not self.results:
            print("Không có kết quả nào để phân tích")
            return
            
        # Khởi tạo cấu trúc dữ liệu
        self.summary = {
            'by_period': {},
            'by_symbol': {},
            'by_timeframe': {},
            'by_prediction_days': {},
            'by_model_type': {},
            'best_models': []
        }
        
        # Thu thập dữ liệu theo từng nhóm
        for result in self.results:
            # Lấy thông tin cơ bản
            symbol = result.get('symbol', 'unknown')
            timeframe = result.get('timeframe', 'unknown')
            period = result.get('period', 'unknown')
            prediction_days = result.get('prediction_days', 0)
            model_type = result.get('model_type', 'unknown')
            
            # Lấy metrics
            accuracy = result.get('accuracy', 0)
            precision = result.get('precision', 0)
            recall = result.get('recall', 0)
            f1_score = result.get('f1_score', 0)
            
            # Nhóm theo khoảng thời gian
            if period not in self.summary['by_period']:
                self.summary['by_period'][period] = {'count': 0, 'accuracy': [], 'precision': [], 'recall': [], 'f1_score': []}
            self.summary['by_period'][period]['count'] += 1
            self.summary['by_period'][period]['accuracy'].append(accuracy)
            self.summary['by_period'][period]['precision'].append(precision)
            self.summary['by_period'][period]['recall'].append(recall)
            self.summary['by_period'][period]['f1_score'].append(f1_score)
            
            # Nhóm theo đồng tiền
            if symbol not in self.summary['by_symbol']:
                self.summary['by_symbol'][symbol] = {'count': 0, 'accuracy': [], 'precision': [], 'recall': [], 'f1_score': []}
            self.summary['by_symbol'][symbol]['count'] += 1
            self.summary['by_symbol'][symbol]['accuracy'].append(accuracy)
            self.summary['by_symbol'][symbol]['precision'].append(precision)
            self.summary['by_symbol'][symbol]['recall'].append(recall)
            self.summary['by_symbol'][symbol]['f1_score'].append(f1_score)
            
            # Nhóm theo khung thời gian
            if timeframe not in self.summary['by_timeframe']:
                self.summary['by_timeframe'][timeframe] = {'count': 0, 'accuracy': [], 'precision': [], 'recall': [], 'f1_score': []}
            self.summary['by_timeframe'][timeframe]['count'] += 1
            self.summary['by_timeframe'][timeframe]['accuracy'].append(accuracy)
            self.summary['by_timeframe'][timeframe]['precision'].append(precision)
            self.summary['by_timeframe'][timeframe]['recall'].append(recall)
            self.summary['by_timeframe'][timeframe]['f1_score'].append(f1_score)
            
            # Nhóm theo ngày dự đoán
            if prediction_days not in self.summary['by_prediction_days']:
                self.summary['by_prediction_days'][prediction_days] = {'count': 0, 'accuracy': [], 'precision': [], 'recall': [], 'f1_score': []}
            self.summary['by_prediction_days'][prediction_days]['count'] += 1
            self.summary['by_prediction_days'][prediction_days]['accuracy'].append(accuracy)
            self.summary['by_prediction_days'][prediction_days]['precision'].append(precision)
            self.summary['by_prediction_days'][prediction_days]['recall'].append(recall)
            self.summary['by_prediction_days'][prediction_days]['f1_score'].append(f1_score)
            
            # Nhóm theo loại mô hình
            if model_type not in self.summary['by_model_type']:
                self.summary['by_model_type'][model_type] = {'count': 0, 'accuracy': [], 'precision': [], 'recall': [], 'f1_score': []}
            self.summary['by_model_type'][model_type]['count'] += 1
            self.summary['by_model_type'][model_type]['accuracy'].append(accuracy)
            self.summary['by_model_type'][model_type]['precision'].append(precision)
            self.summary['by_model_type'][model_type]['recall'].append(recall)
            self.summary['by_model_type'][model_type]['f1_score'].append(f1_score)
            
            # Thêm vào danh sách best models
            self.summary['best_models'].append({
                'symbol': symbol,
                'timeframe': timeframe,
                'period': period,
                'prediction_days': prediction_days,
                'model_type': model_type,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score
            })
        
        # Sắp xếp best models theo f1_score
        self.summary['best_models'].sort(key=lambda x: x['f1_score'], reverse=True)
        
        # Tính toán trung bình cho từng nhóm
        for category in ['by_period', 'by_symbol', 'by_timeframe', 'by_prediction_days', 'by_model_type']:
            for key in self.summary[category]:
                self.summary[category][key]['avg_accuracy'] = np.mean(self.summary[category][key]['accuracy'])
                self.summary[category][key]['avg_precision'] = np.mean(self.summary[category][key]['precision'])
                self.summary[category][key]['avg_recall'] = np.mean(self.summary[category][key]['recall'])
                self.summary[category][key]['avg_f1_score'] = np.mean(self.summary[category][key]['f1_score'])
                
                self.summary[category][key]['std_accuracy'] = np.std(self.summary[category][key]['accuracy'])
                self.summary[category][key]['std_precision'] = np.std(self.summary[category][key]['precision'])
                self.summary[category][key]['std_recall'] = np.std(self.summary[category][key]['recall'])
                self.summary[category][key]['std_f1_score'] = np.std(self.summary[category][key]['f1_score'])
    
    def compare_period_performance(self) -> Dict:
        """
        So sánh hiệu suất theo khoảng thời gian
        
        Returns:
            Dict: Kết quả so sánh
        """
        if not self.results:
            return {}
            
        # Thu thập dữ liệu nếu chưa có
        if not self.summary:
            self._collect_all_models_data()
            
        # Tạo biểu đồ so sánh
        self._create_period_comparison_chart(self.summary['by_period'])
        
        # Trả về kết quả dạng DataFrame
        periods = []
        avg_accuracy = []
        avg_precision = []
        avg_recall = []
        avg_f1_score = []
        
        for period in sorted(self.summary['by_period'].keys()):
            periods.append(period)
            avg_accuracy.append(self.summary['by_period'][period]['avg_accuracy'])
            avg_precision.append(self.summary['by_period'][period]['avg_precision'])
            avg_recall.append(self.summary['by_period'][period]['avg_recall'])
            avg_f1_score.append(self.summary['by_period'][period]['avg_f1_score'])
            
        df = pd.DataFrame({
            'Period': periods,
            'Accuracy': avg_accuracy,
            'Precision': avg_precision,
            'Recall': avg_recall,
            'F1-Score': avg_f1_score
        })
        
        # Ghi kết quả ra file CSV
        output_path = os.path.join(self.output_dir, 'period_performance_comparison.csv')
        df.to_csv(output_path, index=False)
        
        return self.summary['by_period']
    
    def _create_period_comparison_chart(self, period_metrics: Dict) -> None:
        """
        Tạo biểu đồ so sánh hiệu suất theo khoảng thời gian
        
        Args:
            period_metrics (Dict): Metrics theo khoảng thời gian
        """
        plt.figure(figsize=(12, 8))
        
        # Chuẩn bị dữ liệu
        periods = sorted(period_metrics.keys())
        accuracies = [period_metrics[p]['avg_accuracy'] for p in periods]
        precisions = [period_metrics[p]['avg_precision'] for p in periods]
        recalls = [period_metrics[p]['avg_recall'] for p in periods]
        f1_scores = [period_metrics[p]['avg_f1_score'] for p in periods]
        
        # Vẽ biểu đồ
        bar_width = 0.2
        index = np.arange(len(periods))
        
        plt.bar(index, accuracies, bar_width, label='Accuracy', color='#5DA5DA')
        plt.bar(index + bar_width, precisions, bar_width, label='Precision', color='#FAA43A')
        plt.bar(index + 2*bar_width, recalls, bar_width, label='Recall', color='#60BD68')
        plt.bar(index + 3*bar_width, f1_scores, bar_width, label='F1-Score', color='#F17CB0')
        
        plt.xlabel('Khoảng thời gian dữ liệu')
        plt.ylabel('Giá trị trung bình')
        plt.title('So sánh hiệu suất theo khoảng thời gian dữ liệu')
        plt.xticks(index + 1.5*bar_width, periods)
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Thêm nhãn giá trị
        for i, v in enumerate(accuracies):
            plt.text(i - 0.05, v + 0.02, f'{v:.2f}', rotation=0, ha='center')
        for i, v in enumerate(f1_scores):
            plt.text(i + 3*bar_width - 0.05, v + 0.02, f'{v:.2f}', rotation=0, ha='center')
        
        # Lưu biểu đồ
        output_path = os.path.join(self.charts_dir, 'period_performance_comparison.png')
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        print(f"Đã lưu biểu đồ so sánh hiệu suất theo khoảng thời gian tại: {output_path}")
    
    def compare_target_performance(self) -> Dict:
        """
        So sánh hiệu suất theo mục tiêu dự đoán
        
        Returns:
            Dict: Kết quả so sánh
        """
        if not self.results:
            return {}
            
        # Thu thập dữ liệu nếu chưa có
        if not self.summary:
            self._collect_all_models_data()
            
        # Tạo biểu đồ so sánh
        self._create_target_comparison_chart(self.summary['by_prediction_days'])
        
        # Trả về kết quả dạng DataFrame
        days = []
        avg_accuracy = []
        avg_precision = []
        avg_recall = []
        avg_f1_score = []
        
        for day in sorted(self.summary['by_prediction_days'].keys()):
            days.append(day)
            avg_accuracy.append(self.summary['by_prediction_days'][day]['avg_accuracy'])
            avg_precision.append(self.summary['by_prediction_days'][day]['avg_precision'])
            avg_recall.append(self.summary['by_prediction_days'][day]['avg_recall'])
            avg_f1_score.append(self.summary['by_prediction_days'][day]['avg_f1_score'])
            
        df = pd.DataFrame({
            'Prediction Days': days,
            'Accuracy': avg_accuracy,
            'Precision': avg_precision,
            'Recall': avg_recall,
            'F1-Score': avg_f1_score
        })
        
        # Ghi kết quả ra file CSV
        output_path = os.path.join(self.output_dir, 'target_performance_comparison.csv')
        df.to_csv(output_path, index=False)
        
        return self.summary['by_prediction_days']
    
    def _create_target_comparison_chart(self, target_metrics: Dict) -> None:
        """
        Tạo biểu đồ so sánh hiệu suất theo mục tiêu dự đoán
        
        Args:
            target_metrics (Dict): Metrics theo mục tiêu
        """
        plt.figure(figsize=(12, 8))
        
        # Chuẩn bị dữ liệu
        days = sorted(target_metrics.keys())
        accuracies = [target_metrics[d]['avg_accuracy'] for d in days]
        precisions = [target_metrics[d]['avg_precision'] for d in days]
        recalls = [target_metrics[d]['avg_recall'] for d in days]
        f1_scores = [target_metrics[d]['avg_f1_score'] for d in days]
        
        # Vẽ biểu đồ
        bar_width = 0.2
        index = np.arange(len(days))
        
        plt.bar(index, accuracies, bar_width, label='Accuracy', color='#5DA5DA')
        plt.bar(index + bar_width, precisions, bar_width, label='Precision', color='#FAA43A')
        plt.bar(index + 2*bar_width, recalls, bar_width, label='Recall', color='#60BD68')
        plt.bar(index + 3*bar_width, f1_scores, bar_width, label='F1-Score', color='#F17CB0')
        
        plt.xlabel('Số ngày dự đoán')
        plt.ylabel('Giá trị trung bình')
        plt.title('So sánh hiệu suất theo số ngày dự đoán')
        plt.xticks(index + 1.5*bar_width, days)
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Thêm nhãn giá trị
        for i, v in enumerate(accuracies):
            plt.text(i - 0.05, v + 0.02, f'{v:.2f}', rotation=0, ha='center')
        for i, v in enumerate(f1_scores):
            plt.text(i + 3*bar_width - 0.05, v + 0.02, f'{v:.2f}', rotation=0, ha='center')
        
        # Lưu biểu đồ
        output_path = os.path.join(self.charts_dir, 'target_performance_comparison.png')
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        print(f"Đã lưu biểu đồ so sánh hiệu suất theo số ngày dự đoán tại: {output_path}")
    
    def find_best_models(self) -> Dict:
        """
        Tìm các mô hình tốt nhất
        
        Returns:
            Dict: Danh sách các mô hình tốt nhất
        """
        if not self.results:
            return {}
            
        # Thu thập dữ liệu nếu chưa có
        if not self.summary:
            self._collect_all_models_data()
            
        best_models = self.summary['best_models'][:10]  # Top 10
        
        # Tạo biểu đồ so sánh
        plt.figure(figsize=(14, 8))
        
        # Chuẩn bị dữ liệu
        labels = [f"{m['symbol']} {m['timeframe']} ({m['period']}, {m['prediction_days']}d, {m['model_type']})" for m in best_models]
        accuracies = [m['accuracy'] for m in best_models]
        f1_scores = [m['f1_score'] for m in best_models]
        
        # Vẽ biểu đồ
        bar_width = 0.35
        index = np.arange(len(labels))
        
        plt.bar(index, accuracies, bar_width, label='Accuracy', color='#5DA5DA')
        plt.bar(index + bar_width, f1_scores, bar_width, label='F1-Score', color='#F17CB0')
        
        plt.xlabel('Mô hình')
        plt.ylabel('Điểm số')
        plt.title('Top 10 mô hình tốt nhất')
        plt.xticks(index + bar_width/2, labels, rotation=45, ha='right')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Thêm nhãn giá trị
        for i, v in enumerate(accuracies):
            plt.text(i - 0.05, v + 0.01, f'{v:.2f}', rotation=0, ha='center')
        for i, v in enumerate(f1_scores):
            plt.text(i + bar_width - 0.05, v + 0.01, f'{v:.2f}', rotation=0, ha='center')
        
        # Lưu biểu đồ
        output_path = os.path.join(self.charts_dir, 'best_models.png')
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        print(f"Đã lưu biểu đồ top 10 mô hình tốt nhất tại: {output_path}")
        
        # Ghi kết quả ra file CSV
        df = pd.DataFrame(best_models)
        output_path = os.path.join(self.output_dir, 'best_models.csv')
        df.to_csv(output_path, index=False)
        
        return {'best_models': best_models}
    
    def analyze_feature_importance(self) -> Dict:
        """
        Phân tích tầm quan trọng của các đặc trưng
        
        Returns:
            Dict: Kết quả phân tích
        """
        if not self.results:
            return {}
        
        # Thu thập đặc trưng quan trọng từ các mô hình
        feature_count = {}
        
        for result in self.results:
            if 'feature_importance' in result and result['feature_importance'] and 'features' in result['feature_importance']:
                features = result['feature_importance']['features']
                importance = result['feature_importance']['importance']
                
                for feature_idx, feature_name in features.items():
                    if feature_name not in feature_count:
                        feature_count[feature_name] = {'count': 0, 'importance': 0.0}
                    
                    feature_count[feature_name]['count'] += 1
                    feature_count[feature_name]['importance'] += float(importance.get(feature_idx, 0.0))
        
        # Tính trung bình importance
        for feature in feature_count:
            feature_count[feature]['avg_importance'] = feature_count[feature]['importance'] / feature_count[feature]['count']
        
        # Lấy top N đặc trưng quan trọng nhất
        top_features = sorted([(feature, data['avg_importance'], data['count']) 
                            for feature, data in feature_count.items()], 
                           key=lambda x: x[1], reverse=True)[:20]
        
        # Tạo biểu đồ
        self._create_top_features_chart(top_features)
        
        # Trả về kết quả
        result = {
            'feature_importance': {
                feature: {
                    'avg_importance': data['avg_importance'],
                    'count': data['count']
                } for feature, data in feature_count.items()
            },
            'top_features': top_features
        }
        
        # Ghi ra file CSV
        df = pd.DataFrame([(f, d['avg_importance'], d['count']) for f, d in feature_count.items()],
                        columns=['Feature', 'Average Importance', 'Count'])
        df = df.sort_values('Average Importance', ascending=False)
        
        output_path = os.path.join(self.output_dir, 'feature_importance.csv')
        df.to_csv(output_path, index=False)
        
        return result
    
    def _create_top_features_chart(self, top_features: List[Tuple[str, float, int]]) -> None:
        """
        Tạo biểu đồ top feature importance
        
        Args:
            top_features (List[Tuple[str, float, int]]): Danh sách (feature, importance, count)
        """
        plt.figure(figsize=(12, 10))
        
        # Chuẩn bị dữ liệu
        features = [f[0] for f in top_features]
        importances = [f[1] for f in top_features]
        counts = [f[2] for f in top_features]
        
        # Vẽ biểu đồ chính (importances)
        y_pos = np.arange(len(features))
        plt.barh(y_pos, importances, align='center', color='#5DA5DA', alpha=0.8)
        
        # Thêm số lần xuất hiện
        for i, (imp, cnt) in enumerate(zip(importances, counts)):
            plt.text(imp + 0.01, i, f"({cnt})", va='center')
        
        plt.yticks(y_pos, features)
        plt.xlabel('Độ quan trọng trung bình')
        plt.title('Top 20 đặc trưng quan trọng nhất')
        plt.grid(True, linestyle='--', alpha=0.7, axis='x')
        
        # Lưu biểu đồ
        output_path = os.path.join(self.charts_dir, 'top_features.png')
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        print(f"Đã lưu biểu đồ top đặc trưng quan trọng tại: {output_path}")
    
    def create_comprehensive_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo tổng hợp
        
        Args:
            output_path (str, optional): Đường dẫn lưu báo cáo
            
        Returns:
            str: Đường dẫn đến báo cáo
        """
        if not self.results:
            return "Không có kết quả để tạo báo cáo"
            
        # Thu thập dữ liệu nếu chưa có
        if not self.summary:
            self._collect_all_models_data()
            
        # Phân tích dữ liệu
        period_comparison = self.compare_period_performance()
        target_comparison = self.compare_target_performance()
        best_models = self.find_best_models()
        feature_importance = self.analyze_feature_importance()
        
        # Tạo báo cáo HTML
        if output_path is None:
            output_path = os.path.join(self.output_dir, 'ml_performance_report.html')
            
        html_content = self._generate_html_report(
            period_comparison,
            target_comparison,
            best_models,
            feature_importance
        )
        
        # Lưu báo cáo
        with open(output_path, 'w') as f:
            f.write(html_content)
            
        print(f"Đã lưu báo cáo tổng hợp tại: {output_path}")
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
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Báo cáo hiệu suất ML</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 20px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                .chart-container {{
                    margin: 20px 0;
                    text-align: center;
                }}
                .chart-container img {{
                    max-width: 100%;
                    height: auto;
                    border: 1px solid #ddd;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }}
                .section {{
                    margin-bottom: 30px;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 20px;
                }}
                .highlight {{
                    background-color: #ffffcc;
                    padding: 2px 5px;
                    border-radius: 3px;
                }}
            </style>
        </head>
        <body>
            <h1>Báo cáo hiệu suất Machine Learning</h1>
            <p>Thời gian báo cáo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Tổng số mô hình phân tích: {len(self.results)}</p>
            
            <div class="section">
                <h2>Thông tin tổng quan</h2>
                <p>Danh sách các đồng tiền: {', '.join(sorted(self.symbols))}</p>
                <p>Danh sách các khung thời gian: {', '.join(sorted(self.timeframes))}</p>
                <p>Danh sách các khoảng thời gian dữ liệu: {', '.join(sorted(self.periods))}</p>
                <p>Danh sách các ngày dự đoán: {', '.join(map(str, sorted(self.prediction_days)))}</p>
                <p>Danh sách các loại mô hình: {', '.join(sorted(self.model_types))}</p>
            </div>
            
            <div class="section">
                <h2>So sánh hiệu suất theo khoảng thời gian dữ liệu</h2>
                <div class="chart-container">
                    <img src="../ml_charts/period_performance_comparison.png" alt="So sánh hiệu suất theo khoảng thời gian">
                </div>
                <table>
                    <tr>
                        <th>Khoảng thời gian</th>
                        <th>Số mô hình</th>
                        <th>Accuracy (trung bình)</th>
                        <th>Precision (trung bình)</th>
                        <th>Recall (trung bình)</th>
                        <th>F1-Score (trung bình)</th>
                    </tr>
        """
        
        # Thêm dữ liệu so sánh khoảng thời gian
        for period in sorted(period_comparison.keys()):
            html += f"""
                    <tr>
                        <td>{period}</td>
                        <td>{period_comparison[period]['count']}</td>
                        <td>{period_comparison[period]['avg_accuracy']:.4f}</td>
                        <td>{period_comparison[period]['avg_precision']:.4f}</td>
                        <td>{period_comparison[period]['avg_recall']:.4f}</td>
                        <td>{period_comparison[period]['avg_f1_score']:.4f}</td>
                    </tr>
            """
        
        html += """
                </table>
                <p><strong>Nhận xét:</strong> Khoảng thời gian dữ liệu ảnh hưởng đáng kể đến hiệu suất của mô hình. 
                Dữ liệu dài hơn có thể cung cấp nhiều mẫu học tập hơn nhưng cũng có thể chứa nhiều biến động thị trường hơn.</p>
            </div>
            
            <div class="section">
                <h2>So sánh hiệu suất theo số ngày dự đoán</h2>
                <div class="chart-container">
                    <img src="../ml_charts/target_performance_comparison.png" alt="So sánh hiệu suất theo số ngày dự đoán">
                </div>
                <table>
                    <tr>
                        <th>Số ngày dự đoán</th>
                        <th>Số mô hình</th>
                        <th>Accuracy (trung bình)</th>
                        <th>Precision (trung bình)</th>
                        <th>Recall (trung bình)</th>
                        <th>F1-Score (trung bình)</th>
                    </tr>
        """
        
        # Thêm dữ liệu so sánh mục tiêu
        for days in sorted(target_comparison.keys()):
            html += f"""
                    <tr>
                        <td>{days}</td>
                        <td>{target_comparison[days]['count']}</td>
                        <td>{target_comparison[days]['avg_accuracy']:.4f}</td>
                        <td>{target_comparison[days]['avg_precision']:.4f}</td>
                        <td>{target_comparison[days]['avg_recall']:.4f}</td>
                        <td>{target_comparison[days]['avg_f1_score']:.4f}</td>
                    </tr>
            """
        
        html += """
                </table>
                <p><strong>Nhận xét:</strong> Số ngày dự đoán có ảnh hưởng rõ rệt đến độ chính xác của mô hình.
                Dự đoán ngắn hạn thường chính xác hơn dự đoán dài hạn do tính bất định của thị trường tăng lên theo thời gian.</p>
            </div>
            
            <div class="section">
                <h2>Top 10 mô hình tốt nhất</h2>
                <div class="chart-container">
                    <img src="../ml_charts/best_models.png" alt="Top 10 mô hình tốt nhất">
                </div>
                <table>
                    <tr>
                        <th>Đồng tiền</th>
                        <th>Timeframe</th>
                        <th>Khoảng thời gian</th>
                        <th>Số ngày dự đoán</th>
                        <th>Loại mô hình</th>
                        <th>Accuracy</th>
                        <th>F1-Score</th>
                    </tr>
        """
        
        # Thêm dữ liệu top models
        for model in best_models.get('best_models', [])[:10]:
            html += f"""
                    <tr>
                        <td>{model['symbol']}</td>
                        <td>{model['timeframe']}</td>
                        <td>{model['period']}</td>
                        <td>{model['prediction_days']}</td>
                        <td>{model['model_type']}</td>
                        <td>{model['accuracy']:.4f}</td>
                        <td>{model['f1_score']:.4f}</td>
                    </tr>
            """
        
        html += """
                </table>
                <p><strong>Nhận xét:</strong> Các mô hình tốt nhất thường sử dụng kết hợp khung thời gian, khoảng thời gian dữ liệu và 
                số ngày dự đoán phù hợp với đặc điểm của đồng tiền cụ thể.</p>
            </div>
            
            <div class="section">
                <h2>Các đặc trưng quan trọng nhất</h2>
                <div class="chart-container">
                    <img src="../ml_charts/top_features.png" alt="Các đặc trưng quan trọng nhất">
                </div>
                <p><strong>Nhận xét:</strong> Các đặc trưng kỹ thuật quan trọng nhất trong dự đoán thường liên quan đến 
                các chỉ báo xu hướng và biến động. Những đặc trưng này xuất hiện nhất quán trên nhiều mô hình.</p>
            </div>
            
            <div class="section">
                <h2>Kết luận và khuyến nghị</h2>
                <p>
                    Qua phân tích hiệu suất của các mô hình ML, một số kết luận và khuyến nghị được đưa ra:
                </p>
                <ul>
                    <li>Khoảng thời gian dữ liệu tối ưu: <span class="highlight">{max(period_comparison.keys(), key=lambda p: period_comparison[p]['avg_f1_score'])}</span></li>
                    <li>Số ngày dự đoán tối ưu: <span class="highlight">{max(target_comparison.keys(), key=lambda d: target_comparison[d]['avg_f1_score'])}</span></li>
                    <li>Loại mô hình hiệu quả nhất: <span class="highlight">{max(self.summary['by_model_type'].keys(), key=lambda m: self.summary['by_model_type'][m]['avg_f1_score'])}</span></li>
                </ul>
                <p>
                    Các yếu tố ảnh hưởng đến hiệu suất dự đoán:
                </p>
                <ul>
                    <li>Độ biến động của thị trường ảnh hưởng lớn đến khả năng dự đoán</li>
                    <li>Dự đoán ngắn hạn (1 ngày) thường có độ chính xác cao hơn dự đoán dài hạn</li>
                    <li>Các chỉ báo kỹ thuật quan trọng nhất bao gồm: {', '.join([f[0] for f in feature_importance.get('top_features', [])[:5]])}</li>
                </ul>
            </div>
            
            <div>
                <p>© {datetime.now().year} BinanceTrader Bot - Báo cáo được tạo tự động</p>
            </div>
        </body>
        </html>
        """
        
        return html

def main():
    parser = argparse.ArgumentParser(description='Phân tích hiệu suất ML')
    parser.add_argument('--results_dir', type=str, default='ml_results', help='Thư mục chứa kết quả')
    parser.add_argument('--charts_dir', type=str, default='ml_charts', help='Thư mục lưu biểu đồ')
    parser.add_argument('--output_report', type=str, default=None, help='Đường dẫn đến file báo cáo đầu ra')
    
    args = parser.parse_args()
    
    # Tạo thư mục charts nếu chưa tồn tại
    os.makedirs(args.charts_dir, exist_ok=True)
    
    # Khởi tạo analyzer
    analyzer = MLPerformanceAnalyzer(
        results_dir=args.results_dir,
        charts_dir=args.charts_dir
    )
    
    # Tải các báo cáo
    if not analyzer.load_summary_reports():
        print("Không tìm thấy báo cáo. Hãy chạy run_period_ml_backtest.py trước.")
        return
    
    # Tạo báo cáo tổng hợp
    report_path = analyzer.create_comprehensive_report(args.output_report)
    
    print(f"Phân tích hoàn thành! Báo cáo được lưu tại: {report_path}")

if __name__ == "__main__":
    main()