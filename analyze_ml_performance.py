"""
Script phân tích và so sánh hiệu suất các mô hình ML trên nhiều khoảng thời gian
"""
import os
import sys
import json
import argparse
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ml_analysis")

class MLPerformanceAnalyzer:
    """Lớp phân tích hiệu suất các mô hình ML"""
    
    def __init__(self, results_dir: str = 'ml_results', charts_dir: str = 'ml_charts'):
        """
        Khởi tạo phân tích hiệu suất
        
        Args:
            results_dir (str): Thư mục chứa kết quả
            charts_dir (str): Thư mục lưu biểu đồ
        """
        self.results_dir = results_dir
        self.charts_dir = charts_dir
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(charts_dir, exist_ok=True)
        
        # Lưu trữ dữ liệu
        self.summary_reports = {}
        self.all_models_data = []
        self.coins = set()
        self.timeframes = set()
        self.periods = set()
        self.target_days = set()
        
    def load_summary_reports(self, report_paths: List[str] = None) -> bool:
        """
        Tải các báo cáo tổng hợp
        
        Args:
            report_paths (List[str], optional): Danh sách đường dẫn đến báo cáo
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            if not report_paths:
                # Tìm tất cả file ml_summary_report.json trong thư mục
                report_paths = []
                for root, dirs, files in os.walk(self.results_dir):
                    for file in files:
                        if file.endswith('_summary_report.json'):
                            report_paths.append(os.path.join(root, file))
            
            if not report_paths:
                logger.warning(f"Không tìm thấy báo cáo tổng hợp nào trong {self.results_dir}")
                return False
                
            logger.info(f"Tìm thấy {len(report_paths)} báo cáo tổng hợp")
            
            # Tải từng báo cáo
            for path in report_paths:
                try:
                    with open(path, 'r') as f:
                        report = json.load(f)
                        
                    # Lấy timestamp làm key
                    timestamp = report.get('timestamp', os.path.basename(path))
                    self.summary_reports[timestamp] = report
                    
                    # Thu thập thông tin
                    self.coins.update(report.get('coins', []))
                    self.timeframes.update(report.get('timeframes', []))
                    self.periods.update(report.get('periods', []))
                    self.target_days.update(report.get('target_days', []))
                    
                    logger.info(f"Đã tải báo cáo: {path}")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tải báo cáo {path}: {str(e)}")
            
            # Kiểm tra xem đã tải được báo cáo nào chưa
            if not self.summary_reports:
                logger.warning("Không tải được báo cáo tổng hợp nào")
                return False
                
            # Thu thập thông tin tất cả các mô hình
            self._collect_all_models_data()
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tải báo cáo tổng hợp: {str(e)}")
            return False
    
    def _collect_all_models_data(self) -> None:
        """Thu thập dữ liệu từ tất cả các mô hình"""
        for timestamp, report in self.summary_reports.items():
            # Tìm các file kết quả mô hình cụ thể
            model_results_files = []
            for root, dirs, files in os.walk(self.results_dir):
                for file in files:
                    if file.endswith('_results.json') and not file.endswith('_summary_report.json'):
                        model_results_files.append(os.path.join(root, file))
            
            # Tải dữ liệu từng mô hình
            for path in model_results_files:
                try:
                    with open(path, 'r') as f:
                        model_data = json.load(f)
                        
                    # Thêm timestamp report
                    model_data['report_timestamp'] = timestamp
                    
                    # Thêm vào danh sách
                    self.all_models_data.append(model_data)
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tải dữ liệu mô hình {path}: {str(e)}")
    
    def compare_period_performance(self) -> Dict:
        """
        So sánh hiệu suất theo khoảng thời gian
        
        Returns:
            Dict: Kết quả so sánh
        """
        if not self.summary_reports:
            logger.warning("Chưa tải báo cáo tổng hợp")
            return {}
            
        # Chuẩn bị dữ liệu
        period_metrics = {}
        
        for timestamp, report in self.summary_reports.items():
            # Lấy thông tin hiệu suất theo khoảng thời gian
            period_performance = report.get('performance_by_period', {})
            
            # Thêm vào cấu trúc dữ liệu
            for period, metrics in period_performance.items():
                if period not in period_metrics:
                    period_metrics[period] = []
                    
                # Thêm metrics và timestamp
                metrics_with_time = metrics.copy()
                metrics_with_time['timestamp'] = timestamp
                period_metrics[period].append(metrics_with_time)
        
        # Tạo biểu đồ so sánh
        self._create_period_comparison_chart(period_metrics)
        
        # Tính trung bình các metrics cho từng khoảng thời gian
        average_metrics = {}
        for period, metrics_list in period_metrics.items():
            average_metrics[period] = {
                'accuracy': np.mean([m['accuracy'] for m in metrics_list]),
                'precision': np.mean([m['precision'] for m in metrics_list]),
                'recall': np.mean([m['recall'] for m in metrics_list]),
                'f1': np.mean([m['f1'] for m in metrics_list]),
                'n_reports': len(metrics_list)
            }
        
        return {
            'period_metrics': period_metrics,
            'average_metrics': average_metrics
        }
    
    def _create_period_comparison_chart(self, period_metrics: Dict) -> None:
        """
        Tạo biểu đồ so sánh hiệu suất theo khoảng thời gian
        
        Args:
            period_metrics (Dict): Metrics theo khoảng thời gian
        """
        # Kiểm tra dữ liệu
        if not period_metrics:
            logger.warning("Không có đủ dữ liệu để tạo biểu đồ")
            return
            
        # Tạo biểu đồ F1-score
        plt.figure(figsize=(12, 6))
        
        periods = list(period_metrics.keys())
        periods.sort()  # Sắp xếp các khoảng thời gian
        
        x = np.arange(len(periods))
        width = 0.2
        
        # Lấy giá trị trung bình
        accuracy_values = [np.mean([m['accuracy'] for m in period_metrics[p]]) for p in periods]
        precision_values = [np.mean([m['precision'] for m in period_metrics[p]]) for p in periods]
        recall_values = [np.mean([m['recall'] for m in period_metrics[p]]) for p in periods]
        f1_values = [np.mean([m['f1'] for m in period_metrics[p]]) for p in periods]
        
        # Vẽ biểu đồ
        plt.bar(x - width*1.5, accuracy_values, width, label='Accuracy')
        plt.bar(x - width/2, precision_values, width, label='Precision')
        plt.bar(x + width/2, recall_values, width, label='Recall')
        plt.bar(x + width*1.5, f1_values, width, label='F1-Score')
        
        plt.xlabel('Khoảng thời gian')
        plt.ylabel('Điểm số')
        plt.title('So sánh hiệu suất theo khoảng thời gian')
        plt.xticks(x, periods)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Lưu biểu đồ
        plt.tight_layout()
        chart_path = os.path.join(self.charts_dir, 'period_comparison.png')
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ so sánh khoảng thời gian: {chart_path}")
    
    def compare_target_performance(self) -> Dict:
        """
        So sánh hiệu suất theo mục tiêu dự đoán
        
        Returns:
            Dict: Kết quả so sánh
        """
        if not self.summary_reports:
            logger.warning("Chưa tải báo cáo tổng hợp")
            return {}
            
        # Chuẩn bị dữ liệu
        target_metrics = {}
        
        for timestamp, report in self.summary_reports.items():
            # Lấy thông tin hiệu suất theo mục tiêu
            target_performance = report.get('performance_by_target', {})
            
            # Thêm vào cấu trúc dữ liệu
            for target, metrics in target_performance.items():
                if target not in target_metrics:
                    target_metrics[target] = []
                    
                # Thêm metrics và timestamp
                metrics_with_time = metrics.copy()
                metrics_with_time['timestamp'] = timestamp
                target_metrics[target].append(metrics_with_time)
        
        # Tạo biểu đồ so sánh
        self._create_target_comparison_chart(target_metrics)
        
        # Tính trung bình các metrics cho từng mục tiêu
        average_metrics = {}
        for target, metrics_list in target_metrics.items():
            average_metrics[target] = {
                'accuracy': np.mean([m['accuracy'] for m in metrics_list]),
                'precision': np.mean([m['precision'] for m in metrics_list]),
                'recall': np.mean([m['recall'] for m in metrics_list]),
                'f1': np.mean([m['f1'] for m in metrics_list]),
                'n_reports': len(metrics_list)
            }
        
        return {
            'target_metrics': target_metrics,
            'average_metrics': average_metrics
        }
    
    def _create_target_comparison_chart(self, target_metrics: Dict) -> None:
        """
        Tạo biểu đồ so sánh hiệu suất theo mục tiêu dự đoán
        
        Args:
            target_metrics (Dict): Metrics theo mục tiêu
        """
        # Kiểm tra dữ liệu
        if not target_metrics:
            logger.warning("Không có đủ dữ liệu để tạo biểu đồ")
            return
            
        # Tạo biểu đồ F1-score
        plt.figure(figsize=(12, 6))
        
        targets = list(target_metrics.keys())
        targets.sort()  # Sắp xếp các mục tiêu
        
        x = np.arange(len(targets))
        width = 0.2
        
        # Lấy giá trị trung bình
        accuracy_values = [np.mean([m['accuracy'] for m in target_metrics[t]]) for t in targets]
        precision_values = [np.mean([m['precision'] for m in target_metrics[t]]) for t in targets]
        recall_values = [np.mean([m['recall'] for m in target_metrics[t]]) for t in targets]
        f1_values = [np.mean([m['f1'] for m in target_metrics[t]]) for t in targets]
        
        # Vẽ biểu đồ
        plt.bar(x - width*1.5, accuracy_values, width, label='Accuracy')
        plt.bar(x - width/2, precision_values, width, label='Precision')
        plt.bar(x + width/2, recall_values, width, label='Recall')
        plt.bar(x + width*1.5, f1_values, width, label='F1-Score')
        
        plt.xlabel('Mục tiêu dự đoán (ngày)')
        plt.ylabel('Điểm số')
        plt.title('So sánh hiệu suất theo mục tiêu dự đoán')
        plt.xticks(x, targets)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Lưu biểu đồ
        plt.tight_layout()
        chart_path = os.path.join(self.charts_dir, 'target_comparison.png')
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ so sánh mục tiêu: {chart_path}")
    
    def find_best_models(self) -> Dict:
        """
        Tìm các mô hình tốt nhất
        
        Returns:
            Dict: Danh sách các mô hình tốt nhất
        """
        if not self.all_models_data:
            logger.warning("Chưa tải dữ liệu mô hình")
            return {}
            
        # Chuẩn bị dữ liệu
        best_models = {
            'by_coin': {},
            'by_period': {},
            'by_target': {},
            'overall': {
                'accuracy': {'model': None, 'value': 0},
                'precision': {'model': None, 'value': 0},
                'recall': {'model': None, 'value': 0},
                'f1': {'model': None, 'value': 0}
            }
        }
        
        # Duyệt qua từng mô hình
        for model in self.all_models_data:
            coin = model.get('coin')
            period = model.get('period')
            target_days = model.get('target_days')
            model_key = model.get('model_key')
            
            # Lấy metrics
            if 'cross_validation' in model:
                # Lấy kết quả cross-validation
                metrics = {
                    'accuracy': model['cross_validation']['average']['accuracy'],
                    'precision': model['cross_validation']['average']['precision'],
                    'recall': model['cross_validation']['average']['recall'],
                    'f1': model['cross_validation']['average']['f1']
                }
            elif 'metrics' in model:
                # Lấy kết quả thông thường
                metrics = model['metrics']
            else:
                # Không có metrics
                continue
            
            # Kiểm tra và cập nhật best models by coin
            if coin not in best_models['by_coin']:
                best_models['by_coin'][coin] = {
                    'f1': {'model': None, 'value': 0}
                }
                
            if metrics['f1'] > best_models['by_coin'][coin]['f1']['value']:
                best_models['by_coin'][coin]['f1'] = {
                    'model': model_key,
                    'value': metrics['f1'],
                    'metrics': metrics,
                    'period': period,
                    'target_days': target_days
                }
            
            # Kiểm tra và cập nhật best models by period
            if period not in best_models['by_period']:
                best_models['by_period'][period] = {
                    'f1': {'model': None, 'value': 0}
                }
                
            if metrics['f1'] > best_models['by_period'][period]['f1']['value']:
                best_models['by_period'][period]['f1'] = {
                    'model': model_key,
                    'value': metrics['f1'],
                    'metrics': metrics,
                    'coin': coin,
                    'target_days': target_days
                }
            
            # Kiểm tra và cập nhật best models by target
            if target_days not in best_models['by_target']:
                best_models['by_target'][target_days] = {
                    'f1': {'model': None, 'value': 0}
                }
                
            if metrics['f1'] > best_models['by_target'][target_days]['f1']['value']:
                best_models['by_target'][target_days]['f1'] = {
                    'model': model_key,
                    'value': metrics['f1'],
                    'metrics': metrics,
                    'coin': coin,
                    'period': period
                }
            
            # Kiểm tra và cập nhật best models overall
            for metric in ['accuracy', 'precision', 'recall', 'f1']:
                if metrics[metric] > best_models['overall'][metric]['value']:
                    best_models['overall'][metric] = {
                        'model': model_key,
                        'value': metrics[metric],
                        'metrics': metrics,
                        'coin': coin,
                        'period': period,
                        'target_days': target_days
                    }
        
        return best_models
    
    def analyze_feature_importance(self) -> Dict:
        """
        Phân tích tầm quan trọng của các đặc trưng
        
        Returns:
            Dict: Kết quả phân tích
        """
        if not self.all_models_data:
            logger.warning("Chưa tải dữ liệu mô hình")
            return {}
            
        # Chuẩn bị dữ liệu
        all_features = {}
        feature_ranks = {}
        
        # Duyệt qua từng mô hình
        for model in self.all_models_data:
            # Kiểm tra feature importance
            if 'feature_importance' not in model:
                continue
                
            # Lấy feature importance
            importance_data = model['feature_importance']
            
            # Thêm vào danh sách
            for item in importance_data:
                feature = item['feature']
                importance = item['importance']
                
                if feature not in all_features:
                    all_features[feature] = []
                    feature_ranks[feature] = []
                    
                all_features[feature].append(importance)
                
            # Tính rank của feature importance
            sorted_features = sorted(importance_data, key=lambda x: x['importance'], reverse=True)
            for i, item in enumerate(sorted_features):
                feature = item['feature']
                feature_ranks[feature].append(i + 1)  # Thứ hạng bắt đầu từ 1
        
        # Tính trung bình importance và rank
        average_importance = {}
        average_rank = {}
        
        for feature, values in all_features.items():
            average_importance[feature] = np.mean(values)
            
        for feature, ranks in feature_ranks.items():
            average_rank[feature] = np.mean(ranks)
        
        # Sắp xếp theo importance
        sorted_features = sorted(average_importance.items(), key=lambda x: x[1], reverse=True)
        
        # Tạo biểu đồ top 15 feature
        self._create_top_features_chart(sorted_features[:15])
        
        return {
            'average_importance': dict(sorted_features),
            'average_rank': average_rank,
            'feature_count': {feature: len(values) for feature, values in all_features.items()}
        }
    
    def _create_top_features_chart(self, top_features: List[Tuple[str, float]]) -> None:
        """
        Tạo biểu đồ top feature importance
        
        Args:
            top_features (List[Tuple[str, float]]): Danh sách (feature, importance)
        """
        # Kiểm tra dữ liệu
        if not top_features:
            logger.warning("Không có đủ dữ liệu để tạo biểu đồ")
            return
            
        # Tạo biểu đồ
        plt.figure(figsize=(10, 8))
        
        features = [f[0] for f in top_features]
        importance = [f[1] for f in top_features]
        
        # Đảo ngược thứ tự để hiển thị từ trên xuống
        features.reverse()
        importance.reverse()
        
        # Vẽ biểu đồ
        plt.barh(features, importance)
        plt.xlabel('Tầm quan trọng')
        plt.title('Top 15 Feature Importance')
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        
        # Lưu biểu đồ
        plt.tight_layout()
        chart_path = os.path.join(self.charts_dir, 'top_features.png')
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ top features: {chart_path}")
    
    def create_comprehensive_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo tổng hợp
        
        Args:
            output_path (str, optional): Đường dẫn lưu báo cáo
            
        Returns:
            str: Đường dẫn đến báo cáo
        """
        # Phân tích dữ liệu
        period_comparison = self.compare_period_performance()
        target_comparison = self.compare_target_performance()
        best_models = self.find_best_models()
        feature_importance = self.analyze_feature_importance()
        
        # Tạo báo cáo HTML
        html = self._generate_html_report(
            period_comparison,
            target_comparison,
            best_models,
            feature_importance
        )
        
        # Xác định đường dẫn lưu
        if not output_path:
            output_path = os.path.join(self.results_dir, 'ml_performance_analysis.html')
            
        # Lưu báo cáo
        with open(output_path, 'w') as f:
            f.write(html)
            
        logger.info(f"Đã tạo báo cáo tổng hợp: {output_path}")
        
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
        # Bắt đầu HTML
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Phân tích hiệu suất ML - Dự đoán xu hướng</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1, h2, h3 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 20px; }
                .positive { color: green; }
                .negative { color: red; }
                .chart { margin: 20px 0; max-width: 100%; }
                .tabs { display: flex; margin-bottom: 10px; }
                .tab { padding: 8px 16px; background-color: #f2f2f2; cursor: pointer; border: 1px solid #ddd; border-bottom: none; }
                .tab.active { background-color: #fff; border-bottom: 1px solid #fff; }
                .tab-content { display: none; border: 1px solid #ddd; padding: 15px; }
                .tab-content.active { display: block; }
            </style>
            <script>
                function openTab(evt, tabName) {
                    var i, tabcontent, tablinks;
                    tabcontent = document.getElementsByClassName("tab-content");
                    for (i = 0; i < tabcontent.length; i++) {
                        tabcontent[i].className = tabcontent[i].className.replace(" active", "");
                    }
                    tablinks = document.getElementsByClassName("tab");
                    for (i = 0; i < tablinks.length; i++) {
                        tablinks[i].className = tablinks[i].className.replace(" active", "");
                    }
                    document.getElementById(tabName).className += " active";
                    evt.currentTarget.className += " active";
                }
            </script>
        </head>
        <body>
            <h1>Phân tích hiệu suất ML - Dự đoán xu hướng</h1>
            <p>Thời gian: """ + datetime.now().isoformat() + """</p>
            
            <div class="card">
                <h2>Tổng quan</h2>
                <p>Báo cáo này phân tích hiệu suất của các mô hình ML trên nhiều khoảng thời gian và mục tiêu dự đoán khác nhau.</p>
                <table>
                    <tr>
                        <th>Tổng số coins</th>
                        <td>""" + str(len(self.coins)) + """</td>
                    </tr>
                    <tr>
                        <th>Coins</th>
                        <td>""" + ", ".join(self.coins) + """</td>
                    </tr>
                    <tr>
                        <th>Khung thời gian</th>
                        <td>""" + ", ".join(self.timeframes) + """</td>
                    </tr>
                    <tr>
                        <th>Khoảng thời gian</th>
                        <td>""" + ", ".join(self.periods) + """</td>
                    </tr>
                    <tr>
                        <th>Mục tiêu dự đoán (ngày)</th>
                        <td>""" + ", ".join(str(d) for d in self.target_days) + """</td>
                    </tr>
                </table>
            </div>
            
            <div class="tabs">
                <button class="tab active" onclick="openTab(event, 'periodTab')">So sánh khoảng thời gian</button>
                <button class="tab" onclick="openTab(event, 'targetTab')">So sánh mục tiêu dự đoán</button>
                <button class="tab" onclick="openTab(event, 'bestModelsTab')">Mô hình tốt nhất</button>
                <button class="tab" onclick="openTab(event, 'featureTab')">Feature Importance</button>
            </div>
            
            <div id="periodTab" class="tab-content active">
                <h2>So sánh hiệu suất theo khoảng thời gian</h2>
                <img src="../ml_charts/period_comparison.png" class="chart" alt="So sánh khoảng thời gian">
                <h3>Hiệu suất trung bình theo khoảng thời gian</h3>
                <table>
                    <tr>
                        <th>Khoảng thời gian</th>
                        <th>Accuracy</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1-Score</th>
                        <th>Số lượng báo cáo</th>
                    </tr>
        """
        
        # Thêm so sánh khoảng thời gian
        for period, metrics in period_comparison.get('average_metrics', {}).items():
            html += f"""
                    <tr>
                        <td>{period}</td>
                        <td>{metrics['accuracy']:.4f}</td>
                        <td>{metrics['precision']:.4f}</td>
                        <td>{metrics['recall']:.4f}</td>
                        <td>{metrics['f1']:.4f}</td>
                        <td>{metrics['n_reports']}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
            
            <div id="targetTab" class="tab-content">
                <h2>So sánh hiệu suất theo mục tiêu dự đoán</h2>
                <img src="../ml_charts/target_comparison.png" class="chart" alt="So sánh mục tiêu dự đoán">
                <h3>Hiệu suất trung bình theo mục tiêu dự đoán</h3>
                <table>
                    <tr>
                        <th>Mục tiêu (ngày)</th>
                        <th>Accuracy</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1-Score</th>
                        <th>Số lượng báo cáo</th>
                    </tr>
        """
        
        # Thêm so sánh mục tiêu
        for target, metrics in target_comparison.get('average_metrics', {}).items():
            html += f"""
                    <tr>
                        <td>{target}</td>
                        <td>{metrics['accuracy']:.4f}</td>
                        <td>{metrics['precision']:.4f}</td>
                        <td>{metrics['recall']:.4f}</td>
                        <td>{metrics['f1']:.4f}</td>
                        <td>{metrics['n_reports']}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
            
            <div id="bestModelsTab" class="tab-content">
                <h2>Mô hình tốt nhất</h2>
                
                <h3>Mô hình tốt nhất tổng thể</h3>
                <table>
                    <tr>
                        <th>Chỉ số</th>
                        <th>Mô hình</th>
                        <th>Giá trị</th>
                        <th>Coin</th>
                        <th>Khoảng thời gian</th>
                        <th>Mục tiêu (ngày)</th>
                    </tr>
        """
        
        # Thêm mô hình tốt nhất tổng thể
        for metric, data in best_models.get('overall', {}).items():
            html += f"""
                    <tr>
                        <td>{metric.capitalize()}</td>
                        <td>{data.get('model', '')}</td>
                        <td>{data.get('value', 0):.4f}</td>
                        <td>{data.get('coin', '')}</td>
                        <td>{data.get('period', '')}</td>
                        <td>{data.get('target_days', '')}</td>
                    </tr>
            """
            
        html += """
                </table>
                
                <h3>Mô hình tốt nhất theo coin (F1-Score)</h3>
                <table>
                    <tr>
                        <th>Coin</th>
                        <th>Mô hình tốt nhất</th>
                        <th>F1-Score</th>
                        <th>Khoảng thời gian</th>
                        <th>Mục tiêu (ngày)</th>
                    </tr>
        """
        
        # Thêm mô hình tốt nhất theo coin
        for coin, data in best_models.get('by_coin', {}).items():
            f1_data = data.get('f1', {})
            html += f"""
                    <tr>
                        <td>{coin}</td>
                        <td>{f1_data.get('model', '')}</td>
                        <td>{f1_data.get('value', 0):.4f}</td>
                        <td>{f1_data.get('period', '')}</td>
                        <td>{f1_data.get('target_days', '')}</td>
                    </tr>
            """
            
        html += """
                </table>
                
                <h3>Mô hình tốt nhất theo khoảng thời gian (F1-Score)</h3>
                <table>
                    <tr>
                        <th>Khoảng thời gian</th>
                        <th>Mô hình tốt nhất</th>
                        <th>F1-Score</th>
                        <th>Coin</th>
                        <th>Mục tiêu (ngày)</th>
                    </tr>
        """
        
        # Thêm mô hình tốt nhất theo khoảng thời gian
        for period, data in best_models.get('by_period', {}).items():
            f1_data = data.get('f1', {})
            html += f"""
                    <tr>
                        <td>{period}</td>
                        <td>{f1_data.get('model', '')}</td>
                        <td>{f1_data.get('value', 0):.4f}</td>
                        <td>{f1_data.get('coin', '')}</td>
                        <td>{f1_data.get('target_days', '')}</td>
                    </tr>
            """
            
        html += """
                </table>
                
                <h3>Mô hình tốt nhất theo mục tiêu dự đoán (F1-Score)</h3>
                <table>
                    <tr>
                        <th>Mục tiêu (ngày)</th>
                        <th>Mô hình tốt nhất</th>
                        <th>F1-Score</th>
                        <th>Coin</th>
                        <th>Khoảng thời gian</th>
                    </tr>
        """
        
        # Thêm mô hình tốt nhất theo mục tiêu
        for target, data in best_models.get('by_target', {}).items():
            f1_data = data.get('f1', {})
            html += f"""
                    <tr>
                        <td>{target}</td>
                        <td>{f1_data.get('model', '')}</td>
                        <td>{f1_data.get('value', 0):.4f}</td>
                        <td>{f1_data.get('coin', '')}</td>
                        <td>{f1_data.get('period', '')}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
            
            <div id="featureTab" class="tab-content">
                <h2>Feature Importance</h2>
                <img src="../ml_charts/top_features.png" class="chart" alt="Top Feature Importance">
                
                <h3>Top 20 Features</h3>
                <table>
                    <tr>
                        <th>Feature</th>
                        <th>Importance trung bình</th>
                        <th>Số lượng mô hình</th>
                    </tr>
        """
        
        # Thêm feature importance
        features = list(feature_importance.get('average_importance', {}).items())
        features.sort(key=lambda x: x[1], reverse=True)
        
        for i, (feature, importance) in enumerate(features[:20]):
            count = feature_importance.get('feature_count', {}).get(feature, 0)
            html += f"""
                    <tr>
                        <td>{feature}</td>
                        <td>{importance:.6f}</td>
                        <td>{count}</td>
                    </tr>
            """
            
        html += """
                </table>
            </div>
            
            <div class="card">
                <h2>Kết luận</h2>
                <p>Dựa trên phân tích hiệu suất các mô hình ML, chúng ta có thể đưa ra các khuyến nghị sau:</p>
                <ul>
        """
        
        # Thêm kết luận
        # 1. Khoảng thời gian nào hiệu quả nhất
        if period_comparison.get('average_metrics'):
            best_period = max(period_comparison['average_metrics'].items(), key=lambda x: x[1]['f1'])
            html += f"""
                    <li>Khoảng thời gian <strong>{best_period[0]}</strong> cho hiệu suất dự đoán tốt nhất với F1-score trung bình {best_period[1]['f1']:.4f}</li>
            """
            
        # 2. Mục tiêu dự đoán nào hiệu quả nhất
        if target_comparison.get('average_metrics'):
            best_target = max(target_comparison['average_metrics'].items(), key=lambda x: x[1]['f1'])
            html += f"""
                    <li>Mục tiêu dự đoán <strong>{best_target[0]} ngày</strong> cho hiệu suất dự đoán tốt nhất với F1-score trung bình {best_target[1]['f1']:.4f}</li>
            """
            
        # 3. Coin nào hiệu quả nhất
        if best_models.get('by_coin'):
            best_coin = max(best_models['by_coin'].items(), key=lambda x: x[1]['f1']['value'])
            html += f"""
                    <li>Coin <strong>{best_coin[0]}</strong> có hiệu suất dự đoán tốt nhất với F1-score {best_coin[1]['f1']['value']:.4f} từ mô hình {best_coin[1]['f1']['model']}</li>
            """
            
        # 4. Top features quan trọng nhất
        if feature_importance.get('average_importance'):
            top_features = list(feature_importance['average_importance'].items())
            top_features.sort(key=lambda x: x[1], reverse=True)
            top_features = top_features[:5]
            
            feature_names = ", ".join([f"<strong>{f[0]}</strong>" for f in top_features])
            html += f"""
                    <li>Các đặc trưng quan trọng nhất cho dự đoán là: {feature_names}</li>
            """
            
        html += """
                </ul>
                
                <p>Khuyến nghị:</p>
                <ul>
        """
        
        # Thêm khuyến nghị
        # 1. Mô hình tốt nhất để sử dụng
        if best_models.get('overall', {}).get('f1', {}).get('model'):
            best_model = best_models['overall']['f1']
            html += f"""
                    <li>Sử dụng mô hình <strong>{best_model['model']}</strong> cho dự đoán xu hướng với F1-score {best_model['value']:.4f}</li>
            """
            
        # 2. Khoảng thời gian để huấn luyện
        if period_comparison.get('average_metrics'):
            best_period = max(period_comparison['average_metrics'].items(), key=lambda x: x[1]['f1'])
            html += f"""
                    <li>Tập trung huấn luyện mô hình trên khoảng thời gian <strong>{best_period[0]}</strong> để có hiệu suất tốt nhất</li>
            """
            
        # 3. Mục tiêu dự đoán phù hợp
        if target_comparison.get('average_metrics'):
            best_target = max(target_comparison['average_metrics'].items(), key=lambda x: x[1]['f1'])
            html += f"""
                    <li>Tập trung vào dự đoán xu hướng <strong>{best_target[0]} ngày</strong> để có độ chính xác cao nhất</li>
            """
            
        html += """
                </ul>
            </div>
        </body>
        </html>
        """
        
        return html

def main():
    """Hàm chính"""
    # Tạo parser cho đối số dòng lệnh
    parser = argparse.ArgumentParser(description='Phân tích hiệu suất ML và tạo báo cáo tổng hợp')
    parser.add_argument('--input', default='ml_results', help='Thư mục chứa kết quả ML')
    parser.add_argument('--output', default=None, help='Đường dẫn lưu báo cáo tổng hợp')
    parser.add_argument('--charts-dir', default='ml_charts', help='Thư mục lưu biểu đồ')
    
    # Parse đối số
    args = parser.parse_args()
    
    try:
        # Khởi tạo analyzer
        analyzer = MLPerformanceAnalyzer(
            results_dir=args.input,
            charts_dir=args.charts_dir
        )
        
        # Tải báo cáo tổng hợp
        if analyzer.load_summary_reports():
            # Tạo báo cáo phân tích
            output_path = analyzer.create_comprehensive_report(args.output)
            print(f"Đã tạo báo cáo phân tích: {output_path}")
        else:
            print(f"Không tìm thấy báo cáo tổng hợp trong {args.input}")
            
    except Exception as e:
        logger.error(f"Lỗi: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()