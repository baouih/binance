#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Đánh giá hiệu suất mô hình ML trong hệ thống giao dịch
"""

import os
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import joblib
from typing import Dict, List, Any, Optional, Tuple, Union
import glob

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ml_evaluation')

class MLEvaluator:
    """
    Lớp đánh giá hiệu suất mô hình ML cho giao dịch tiền điện tử
    Phân tích hiệu quả dự đoán, các tín hiệu giao dịch và hiệu suất giao dịch
    """
    
    def __init__(self):
        """Khởi tạo MLEvaluator"""
        self.ml_models_dir = 'ml_models'
        self.ml_results_dir = 'ml_results'
        self.ml_charts_dir = 'ml_charts'
        
        # Đảm bảo các thư mục tồn tại
        os.makedirs(self.ml_results_dir, exist_ok=True)
        os.makedirs(self.ml_charts_dir, exist_ok=True)
        
        # Đọc báo cáo hiệu suất hiện có nếu có
        self.performance_summary = self._load_summary_report()
        
        logger.info(f"Đã khởi tạo MLEvaluator, tìm thấy {self._count_models()} mô hình trong {self.ml_models_dir}")
    
    def _count_models(self) -> int:
        """Đếm số lượng mô hình ML trong thư mục ml_models"""
        count = 0
        for ext in ['*.joblib', '*.pkl']:
            count += len(glob.glob(os.path.join(self.ml_models_dir, ext)))
        
        # Loại bỏ các file scaler
        scaler_count = len(glob.glob(os.path.join(self.ml_models_dir, '*scaler*')))
        
        return count - scaler_count
    
    def _load_summary_report(self) -> Dict:
        """Tải báo cáo tóm tắt hiệu suất nếu có"""
        summary_path = os.path.join(self.ml_results_dir, 'ml_summary_report.json')
        
        if os.path.exists(summary_path):
            try:
                with open(summary_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Lỗi khi tải báo cáo tóm tắt: {str(e)}")
        
        # Tạo báo cáo mới nếu không tìm thấy
        return {
            'timestamp': datetime.now().isoformat(),
            'total_models': 0,
            'coins': [],
            'timeframes': [],
            'periods': [],
            'target_days': [],
            'performance_by_coin': {},
            'performance_by_period': {},
            'performance_by_target': {},
            'best_models': {
                'accuracy': {'model': '', 'value': 0},
                'precision': {'model': '', 'value': 0},
                'recall': {'model': '', 'value': 0},
                'f1': {'model': '', 'value': 0}
            }
        }
    
    def _extract_model_metadata(self, model_path: str) -> Optional[Dict]:
        """Trích xuất metadata từ tên tệp mô hình"""
        try:
            base_name = os.path.basename(model_path)
            
            # Bỏ qua các file không phải mô hình
            if 'scaler' in base_name or 'features' in base_name:
                return None
                
            # Định dạng chuẩn: SYMBOL_TIMEFRAME_PERIOD_TARGET_model.joblib
            # Ví dụ: BTCUSDT_1h_1m_target1d_model.joblib
            
            # Loại bỏ phần đuôi tệp
            name_parts = base_name.replace('_model.joblib', '').split('_')
            
            if len(name_parts) < 4:
                logger.warning(f"Không thể phân tích metadata từ {base_name}")
                return None
            
            symbol = name_parts[0]
            timeframe = name_parts[1]
            
            # Xác định thời kỳ dữ liệu
            period = None
            for part in name_parts:
                if part.endswith('m'):
                    period = part
                    break
            
            # Xác định mục tiêu dự đoán
            target_days = None
            for part in name_parts:
                if 'target' in part:
                    # Trích số ngày từ chuỗi như "target1d"
                    target_days = int(part.replace('target', '').replace('d', ''))
                    break
            
            if not (symbol and timeframe and period and target_days):
                logger.warning(f"Thiếu thông tin metadata từ {base_name}")
                return None
            
            return {
                'model_path': model_path,
                'base_name': base_name,
                'symbol': symbol,
                'timeframe': timeframe,
                'period': period,
                'target_days': target_days,
                'model_id': f"{symbol}_{timeframe}_{period}_target{target_days}d"
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất metadata từ {model_path}: {str(e)}")
            return None
    
    def evaluate_all_models(self) -> Dict:
        """Đánh giá hiệu suất của tất cả các mô hình ML"""
        logger.info("Bắt đầu đánh giá tất cả các mô hình ML...")
        
        # Tìm tất cả các tệp mô hình
        model_files = []
        for ext in ['*.joblib', '*.pkl']:
            model_files.extend(glob.glob(os.path.join(self.ml_models_dir, '*_model' + ext.replace('*', ''))))
        
        if not model_files:
            logger.warning(f"Không tìm thấy mô hình ML nào trong {self.ml_models_dir}")
            return {}
        
        logger.info(f"Tìm thấy {len(model_files)} tệp mô hình")
        
        # Thu thập thông tin về các mô hình
        models_metadata = []
        coins = set()
        timeframes = set()
        periods = set()
        target_days_set = set()
        
        for model_path in model_files:
            metadata = self._extract_model_metadata(model_path)
            
            if metadata:
                models_metadata.append(metadata)
                coins.add(metadata['symbol'])
                timeframes.add(metadata['timeframe'])
                periods.add(metadata['period'])
                target_days_set.add(metadata['target_days'])
        
        # Cập nhật thông tin tổng quan
        self.performance_summary['timestamp'] = datetime.now().isoformat()
        self.performance_summary['total_models'] = len(models_metadata)
        self.performance_summary['coins'] = list(coins)
        self.performance_summary['timeframes'] = list(timeframes)
        self.performance_summary['periods'] = list(periods)
        self.performance_summary['target_days'] = list(target_days_set)
        
        # Đọc hiệu suất của từng mô hình
        for metadata in models_metadata:
            model_id = metadata['model_id']
            performance_file = os.path.join(self.ml_results_dir, f"{model_id}_performance.json")
            
            if os.path.exists(performance_file):
                try:
                    with open(performance_file, 'r') as f:
                        perf_data = json.load(f)
                        
                    # Cập nhật thống kê hiệu suất
                    self._update_performance_stats(metadata, perf_data)
                    
                except Exception as e:
                    logger.error(f"Lỗi khi đọc dữ liệu hiệu suất cho {model_id}: {str(e)}")
        
        # Lưu báo cáo tóm tắt
        summary_path = os.path.join(self.ml_results_dir, 'ml_summary_report.json')
        with open(summary_path, 'w') as f:
            json.dump(self.performance_summary, f, indent=2)
        
        # Tạo báo cáo HTML
        self._generate_html_report()
        
        # Vẽ biểu đồ hiệu suất
        self._plot_performance_charts()
        
        logger.info(f"Đã hoàn thành đánh giá mô hình ML. Xem báo cáo tại {self.ml_results_dir}/ml_summary_report.html")
        
        return self.performance_summary
    
    def _update_performance_stats(self, metadata: Dict, perf_data: Dict) -> None:
        """Cập nhật thống kê hiệu suất dựa trên dữ liệu từ một mô hình"""
        symbol = metadata['symbol']
        period = metadata['period']
        target_days = str(metadata['target_days'])
        model_id = metadata['model_id']
        
        # Số liệu cần thu thập
        metrics = ['accuracy', 'precision', 'recall', 'f1']
        
        # Kiểm tra xem dữ liệu hiệu suất có chứa các số liệu này không
        if not all(metric in perf_data for metric in metrics):
            logger.warning(f"Dữ liệu hiệu suất cho {model_id} thiếu các số liệu bắt buộc")
            return
        
        # Cập nhật hiệu suất theo coin
        if symbol not in self.performance_summary['performance_by_coin']:
            self.performance_summary['performance_by_coin'][symbol] = {
                'accuracy': 0,
                'precision': 0,
                'recall': 0,
                'f1': 0,
                'n_models': 0
            }
        
        # Cập nhật hiệu suất theo thời kỳ
        if period not in self.performance_summary['performance_by_period']:
            self.performance_summary['performance_by_period'][period] = {
                'accuracy': 0,
                'precision': 0,
                'recall': 0,
                'f1': 0,
                'n_models': 0
            }
        
        # Cập nhật hiệu suất theo mục tiêu dự đoán
        if target_days not in self.performance_summary['performance_by_target']:
            self.performance_summary['performance_by_target'][target_days] = {
                'accuracy': 0,
                'precision': 0,
                'recall': 0,
                'f1': 0,
                'n_models': 0
            }
        
        # Tính toán tổng hiệu suất
        for metric in metrics:
            current_coin_sum = self.performance_summary['performance_by_coin'][symbol][metric] * self.performance_summary['performance_by_coin'][symbol]['n_models']
            current_period_sum = self.performance_summary['performance_by_period'][period][metric] * self.performance_summary['performance_by_period'][period]['n_models']
            current_target_sum = self.performance_summary['performance_by_target'][target_days][metric] * self.performance_summary['performance_by_target'][target_days]['n_models']
            
            # Cập nhật tổng
            current_coin_sum += perf_data[metric]
            current_period_sum += perf_data[metric]
            current_target_sum += perf_data[metric]
            
            # Tăng số lượng mô hình
            self.performance_summary['performance_by_coin'][symbol]['n_models'] += 1
            self.performance_summary['performance_by_period'][period]['n_models'] += 1
            self.performance_summary['performance_by_target'][target_days]['n_models'] += 1
            
            # Cập nhật trung bình
            self.performance_summary['performance_by_coin'][symbol][metric] = current_coin_sum / self.performance_summary['performance_by_coin'][symbol]['n_models']
            self.performance_summary['performance_by_period'][period][metric] = current_period_sum / self.performance_summary['performance_by_period'][period]['n_models']
            self.performance_summary['performance_by_target'][target_days][metric] = current_target_sum / self.performance_summary['performance_by_target'][target_days]['n_models']
        
        # Cập nhật mô hình tốt nhất cho từng số liệu
        for metric in metrics:
            if perf_data[metric] > self.performance_summary['best_models'][metric]['value']:
                self.performance_summary['best_models'][metric]['value'] = perf_data[metric]
                self.performance_summary['best_models'][metric]['model'] = model_id
    
    def _generate_html_report(self) -> None:
        """Tạo báo cáo HTML từ dữ liệu hiệu suất tóm tắt"""
        try:
            html_path = os.path.join(self.ml_results_dir, 'ml_summary_report.html')
            
            # Định dạng HTML cơ bản
            html = '''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Báo Cáo Hiệu Suất Mô Hình ML</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 0;
                        padding: 20px;
                        color: #333;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                    }
                    h1, h2, h3 {
                        color: #2c3e50;
                    }
                    .summary {
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 20px;
                    }
                    th, td {
                        padding: 12px 15px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }
                    th {
                        background-color: #4CAF50;
                        color: white;
                    }
                    tr:hover {
                        background-color: #f5f5f5;
                    }
                    .tab-content {
                        display: none;
                        padding: 20px;
                        border: 1px solid #ddd;
                        border-radius: 0 0 5px 5px;
                    }
                    .tabs {
                        display: flex;
                        border-bottom: 1px solid #ddd;
                    }
                    .tab {
                        padding: 10px 15px;
                        cursor: pointer;
                        background-color: #f1f1f1;
                        border: 1px solid #ddd;
                        border-bottom: none;
                        border-radius: 5px 5px 0 0;
                        margin-right: 5px;
                    }
                    .tab:hover {
                        background-color: #ddd;
                    }
                    .active-tab {
                        background-color: white;
                        border-bottom: 1px solid white;
                    }
                    .chart-container {
                        margin: 20px 0;
                    }
                    .metric {
                        font-weight: bold;
                        color: #2980b9;
                    }
                    .highlight {
                        background-color: #fff3cd;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Báo Cáo Hiệu Suất Mô Hình ML</h1>
                    <div class="summary">
                        <h2>Tóm Tắt</h2>
                        <p>Thời gian: {timestamp}</p>
                        <p>Tổng số mô hình: {total_models}</p>
                        <p>Coins: {coins}</p>
                        <p>Khung thời gian: {timeframes}</p>
                        <p>Khoảng thời gian huấn luyện: {periods}</p>
                        <p>Mục tiêu dự đoán (ngày): {target_days}</p>
                    </div>
                    
                    <h2>Hiệu Suất Tốt Nhất</h2>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Mô hình</th>
                            <th>Giá trị</th>
                        </tr>
            '''.format(
                timestamp=self.performance_summary['timestamp'],
                total_models=self.performance_summary['total_models'],
                coins=', '.join(self.performance_summary['coins']),
                timeframes=', '.join(self.performance_summary['timeframes']),
                periods=', '.join(self.performance_summary['periods']),
                target_days=', '.join(map(str, self.performance_summary['target_days']))
            )
            
            # Thêm thông tin về mô hình tốt nhất
            for metric, data in self.performance_summary['best_models'].items():
                html += '''
                        <tr>
                            <td>{metric}</td>
                            <td>{model}</td>
                            <td>{value:.4f}</td>
                        </tr>
                '''.format(metric=metric.upper(), model=data['model'], value=data['value'])
            
            html += '''
                    </table>
                    
                    <h2>Hiệu Suất Theo Phân Loại</h2>
                    
                    <div class="tabs">
                        <div class="tab active-tab" onclick="openTab('coinTab')">Theo Coin</div>
                        <div class="tab" onclick="openTab('periodTab')">Theo Khoảng Thời Gian</div>
                        <div class="tab" onclick="openTab('targetTab')">Theo Mục Tiêu</div>
                        <div class="tab" onclick="openTab('allModels')">Tất cả mô hình</div>
                    </div>
                    
                    <div id="coinTab" class="tab-content" style="display: block;">
                        <h2>Theo Coin</h2>
                        <table>
                            <tr>
                                <th>Coin</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Số mô hình</th>
                            </tr>
            '''
            
            # Thêm thông tin hiệu suất theo coin
            for coin, data in self.performance_summary['performance_by_coin'].items():
                html += '''
                            <tr>
                                <td>{coin}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>{n_models}</td>
                            </tr>
                '''.format(
                    coin=coin,
                    accuracy=data['accuracy'],
                    precision=data['precision'],
                    recall=data['recall'],
                    f1=data['f1'],
                    n_models=data['n_models']
                )
            
            html += '''
                        </table>
                    </div>
                    
                    <div id="periodTab" class="tab-content">
                        <h2>Theo Khoảng Thời Gian</h2>
                        <table>
                            <tr>
                                <th>Khoảng thời gian</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Số mô hình</th>
                            </tr>
            '''
            
            # Thêm thông tin hiệu suất theo khoảng thời gian
            for period, data in self.performance_summary['performance_by_period'].items():
                html += '''
                            <tr>
                                <td>{period}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>{n_models}</td>
                            </tr>
                '''.format(
                    period=period,
                    accuracy=data['accuracy'],
                    precision=data['precision'],
                    recall=data['recall'],
                    f1=data['f1'],
                    n_models=data['n_models']
                )
            
            html += '''
                        </table>
                    </div>
                    
                    <div id="targetTab" class="tab-content">
                        <h2>Theo Mục Tiêu Dự Đoán</h2>
                        <table>
                            <tr>
                                <th>Mục tiêu (ngày)</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Số mô hình</th>
                            </tr>
            '''
            
            # Thêm thông tin hiệu suất theo mục tiêu dự đoán
            for target, data in self.performance_summary['performance_by_target'].items():
                html += '''
                            <tr>
                                <td>{target}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>{n_models}</td>
                            </tr>
                '''.format(
                    target=target,
                    accuracy=data['accuracy'],
                    precision=data['precision'],
                    recall=data['recall'],
                    f1=data['f1'],
                    n_models=data['n_models']
                )
            
            html += '''
                        </table>
                    </div>
                    
                    <div id="allModels" class="tab-content">
                        <h2>Tất cả mô hình</h2>
                        <table>
                            <tr>
                                <th>Mô hình</th>
                                <th>Coin</th>
                                <th>Timeframe</th>
                                <th>Khoảng thời gian</th>
                                <th>Mục tiêu (ngày)</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Biểu đồ</th>
                            </tr>
            '''
            
            # Để có thêm thông tin chi tiết về từng mô hình, cần quét lại các tệp hiệu suất
            model_files = []
            for ext in ['*.joblib', '*.pkl']:
                model_files.extend(glob.glob(os.path.join(self.ml_models_dir, '*_model' + ext.replace('*', ''))))
            
            for model_path in model_files:
                metadata = self._extract_model_metadata(model_path)
                
                if metadata:
                    model_id = metadata['model_id']
                    performance_file = os.path.join(self.ml_results_dir, f"{model_id}_performance.json")
                    
                    if os.path.exists(performance_file):
                        try:
                            with open(performance_file, 'r') as f:
                                perf_data = json.load(f)
                            
                            html += '''
                                <tr>
                                    <td>{model_id}</td>
                                    <td>{symbol}</td>
                                    <td>{timeframe}</td>
                                    <td>{period}</td>
                                    <td>{target_days}</td>
                                    <td>{accuracy:.4f}</td>
                                    <td>{precision:.4f}</td>
                                    <td>{recall:.4f}</td>
                                    <td>{f1:.4f}</td>
                                    <td><a href="../ml_charts/{model_id}_confusion_matrix.png" target="_blank">confusion_matrix</a><br><a href="../ml_charts/{model_id}_predictions.png" target="_blank">predictions</a></td>
                                </tr>
                            '''.format(
                                model_id=model_id,
                                symbol=metadata['symbol'],
                                timeframe=metadata['timeframe'],
                                period=metadata['period'],
                                target_days=metadata['target_days'],
                                accuracy=perf_data.get('accuracy', 0),
                                precision=perf_data.get('precision', 0),
                                recall=perf_data.get('recall', 0),
                                f1=perf_data.get('f1', 0)
                            )
                            
                        except Exception as e:
                            logger.error(f"Lỗi khi đọc dữ liệu hiệu suất cho {model_id}: {str(e)}")
            
            html += '''
                        </table>
                    </div>
                    
                    <div class="chart-container">
                        <h2>Biểu Đồ Hiệu Suất</h2>
                        <p>Xem các biểu đồ hiệu suất chi tiết trong thư mục ml_charts.</p>
                    </div>
                    
                    <script>
                        function openTab(tabName) {
                            // Ẩn tất cả các tab content
                            var tabContents = document.getElementsByClassName("tab-content");
                            for (var i = 0; i < tabContents.length; i++) {
                                tabContents[i].style.display = "none";
                            }
                            
                            // Loại bỏ class active-tab khỏi tất cả các tab
                            var tabs = document.getElementsByClassName("tab");
                            for (var i = 0; i < tabs.length; i++) {
                                tabs[i].className = tabs[i].className.replace(" active-tab", "");
                            }
                            
                            // Hiển thị tab hiện tại và thêm class active-tab
                            document.getElementById(tabName).style.display = "block";
                            event.currentTarget.className += " active-tab";
                        }
                    </script>
                </div>
            </body>
            </html>
            '''
            
            with open(html_path, 'w') as f:
                f.write(html)
                
            logger.info(f"Đã tạo báo cáo HTML: {html_path}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo HTML: {str(e)}")
    
    def _plot_performance_charts(self) -> None:
        """Vẽ biểu đồ hiệu suất tổng quan"""
        try:
            # Biểu đồ hiệu suất theo coin
            if self.performance_summary['performance_by_coin']:
                plt.figure(figsize=(12, 6))
                
                coins = list(self.performance_summary['performance_by_coin'].keys())
                metrics = ['accuracy', 'precision', 'recall', 'f1']
                
                x = np.arange(len(coins))
                width = 0.2
                
                for i, metric in enumerate(metrics):
                    values = [self.performance_summary['performance_by_coin'][coin][metric] for coin in coins]
                    plt.bar(x + i*width, values, width, label=metric.capitalize())
                
                plt.xlabel('Coins')
                plt.ylabel('Score')
                plt.title('Hiệu suất theo Coin')
                plt.xticks(x + width * 1.5, coins)
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                # Lưu biểu đồ
                plt.savefig(os.path.join(self.ml_charts_dir, 'performance_by_coin.png'), dpi=300, bbox_inches='tight')
                plt.close()
            
            # Biểu đồ hiệu suất theo khoảng thời gian
            if self.performance_summary['performance_by_period']:
                plt.figure(figsize=(12, 6))
                
                periods = list(self.performance_summary['performance_by_period'].keys())
                metrics = ['accuracy', 'precision', 'recall', 'f1']
                
                x = np.arange(len(periods))
                width = 0.2
                
                for i, metric in enumerate(metrics):
                    values = [self.performance_summary['performance_by_period'][period][metric] for period in periods]
                    plt.bar(x + i*width, values, width, label=metric.capitalize())
                
                plt.xlabel('Khoảng thời gian')
                plt.ylabel('Score')
                plt.title('Hiệu suất theo Khoảng thời gian')
                plt.xticks(x + width * 1.5, periods)
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                # Lưu biểu đồ
                plt.savefig(os.path.join(self.ml_charts_dir, 'performance_by_period.png'), dpi=300, bbox_inches='tight')
                plt.close()
            
            # Biểu đồ hiệu suất theo mục tiêu dự đoán
            if self.performance_summary['performance_by_target']:
                plt.figure(figsize=(12, 6))
                
                targets = list(self.performance_summary['performance_by_target'].keys())
                metrics = ['accuracy', 'precision', 'recall', 'f1']
                
                x = np.arange(len(targets))
                width = 0.2
                
                for i, metric in enumerate(metrics):
                    values = [self.performance_summary['performance_by_target'][target][metric] for target in targets]
                    plt.bar(x + i*width, values, width, label=metric.capitalize())
                
                plt.xlabel('Mục tiêu dự đoán (ngày)')
                plt.ylabel('Score')
                plt.title('Hiệu suất theo Mục tiêu dự đoán')
                plt.xticks(x + width * 1.5, targets)
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                # Lưu biểu đồ
                plt.savefig(os.path.join(self.ml_charts_dir, 'performance_by_target.png'), dpi=300, bbox_inches='tight')
                plt.close()
            
            # Biểu đồ mô hình tốt nhất
            plt.figure(figsize=(12, 6))
            
            metrics = list(self.performance_summary['best_models'].keys())
            values = [self.performance_summary['best_models'][metric]['value'] for metric in metrics]
            models = [self.performance_summary['best_models'][metric]['model'] for metric in metrics]
            
            plt.bar(metrics, values, color='skyblue')
            plt.xlabel('Metric')
            plt.ylabel('Score')
            plt.title('Điểm số cao nhất theo Metric')
            plt.ylim(0, 1)
            
            # Thêm nhãn giá trị và tên mô hình
            for i, v in enumerate(values):
                plt.text(i, v + 0.02, f"{v:.3f}\n{models[i]}", ha='center', fontsize=8)
            
            plt.grid(True, alpha=0.3)
            
            # Lưu biểu đồ
            plt.savefig(os.path.join(self.ml_charts_dir, 'best_models.png'), dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info("Đã tạo các biểu đồ hiệu suất")
            
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ hiệu suất: {str(e)}")
    
    def create_performance_analysis_report(self) -> None:
        """Tạo báo cáo phân tích hiệu suất chi tiết"""
        try:
            # Đánh giá tất cả các mô hình
            self.evaluate_all_models()
            
            # Tạo báo cáo HTML chi tiết
            html_path = os.path.join(self.ml_results_dir, 'ml_performance_analysis.html')
            
            # Đọc dữ liệu hiệu suất
            with open(os.path.join(self.ml_results_dir, 'ml_summary_report.json'), 'r') as f:
                summary = json.load(f)
            
            # Định dạng HTML
            html = '''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <title>Phân tích hiệu suất ML - Dự đoán xu hướng thị trường</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 0;
                        padding: 20px;
                        color: #333;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                    }
                    h1, h2, h3 {
                        color: #2c3e50;
                    }
                    .section {
                        margin-bottom: 30px;
                        padding: 20px;
                        border-radius: 5px;
                        background-color: #f9f9f9;
                    }
                    .highlight {
                        background-color: #f1c40f;
                        padding: 2px 5px;
                        border-radius: 3px;
                    }
                    .chart {
                        margin: 20px 0;
                        text-align: center;
                    }
                    .chart img {
                        max-width: 100%;
                        height: auto;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                    }
                    th, td {
                        padding: 10px;
                        border: 1px solid #ddd;
                        text-align: left;
                    }
                    th {
                        background-color: #4CAF50;
                        color: white;
                    }
                    tr:nth-child(even) {
                        background-color: #f2f2f2;
                    }
                    .conclusion {
                        background-color: #e8f4f8;
                        padding: 15px;
                        border-left: 5px solid #3498db;
                        margin-top: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Phân tích hiệu suất mô hình ML cho dự đoán xu hướng thị trường tiền điện tử</h1>
                    <p>Thời gian phân tích: {timestamp}</p>
                    
                    <div class="section">
                        <h2>Tổng quan</h2>
                        <p>Báo cáo này phân tích hiệu suất của {total_models} mô hình học máy được huấn luyện cho các cặp tiền {coins} với các khung thời gian khác nhau. Các mô hình này được sử dụng để dự đoán xu hướng giá trong tương lai (1-3 ngày) dựa trên dữ liệu lịch sử.</p>
                        
                        <div class="chart">
                            <h3>Biểu đồ mô hình tốt nhất theo số liệu</h3>
                            <img src="../ml_charts/best_models.png" alt="Biểu đồ mô hình tốt nhất">
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Phân tích theo Coin</h2>
                        <p>So sánh hiệu suất dự đoán cho các cặp tiền khác nhau.</p>
                        
                        <table>
                            <tr>
                                <th>Coin</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Số mô hình</th>
                            </tr>
            '''
            
            # Thêm thông tin hiệu suất theo coin
            for coin, data in summary['performance_by_coin'].items():
                html += '''
                            <tr>
                                <td>{coin}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>{n_models}</td>
                            </tr>
                '''.format(
                    coin=coin,
                    accuracy=data['accuracy'],
                    precision=data['precision'],
                    recall=data['recall'],
                    f1=data['f1'],
                    n_models=data['n_models']
                )
            
            html += '''
                        </table>
                        
                        <div class="chart">
                            <h3>Hiệu suất theo Coin</h3>
                            <img src="../ml_charts/performance_by_coin.png" alt="Hiệu suất theo Coin">
                        </div>
                        
                        <div class="conclusion">
                            <h3>Nhận xét</h3>
            '''
            
            # Tìm coin có hiệu suất tốt nhất
            best_coin = max(summary['performance_by_coin'].items(), key=lambda x: x[1]['f1'])
            worst_coin = min(summary['performance_by_coin'].items(), key=lambda x: x[1]['f1'])
            
            html += f'''
                            <p>Coin <span class="highlight">{best_coin[0]}</span> có hiệu suất dự đoán tốt nhất với F1-score {best_coin[1]['f1']:.4f}, trong khi {worst_coin[0]} có hiệu suất thấp nhất với F1-score {worst_coin[1]['f1']:.4f}.</p>
                            <p>Điều này cho thấy việc dự đoán xu hướng cho các coin khác nhau có độ khó khác nhau, phụ thuộc vào đặc tính biến động và thanh khoản của mỗi coin.</p>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Phân tích theo khoảng thời gian dữ liệu huấn luyện</h2>
                        <p>So sánh hiệu suất dự đoán dựa trên lượng dữ liệu lịch sử được sử dụng để huấn luyện mô hình.</p>
                        
                        <table>
                            <tr>
                                <th>Khoảng thời gian</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Số mô hình</th>
                            </tr>
            '''
            
            # Thêm thông tin hiệu suất theo khoảng thời gian
            for period, data in summary['performance_by_period'].items():
                html += '''
                            <tr>
                                <td>{period}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>{n_models}</td>
                            </tr>
                '''.format(
                    period=period,
                    accuracy=data['accuracy'],
                    precision=data['precision'],
                    recall=data['recall'],
                    f1=data['f1'],
                    n_models=data['n_models']
                )
            
            html += '''
                        </table>
                        
                        <div class="chart">
                            <h3>Hiệu suất theo khoảng thời gian dữ liệu</h3>
                            <img src="../ml_charts/performance_by_period.png" alt="Hiệu suất theo khoảng thời gian">
                        </div>
                        
                        <div class="conclusion">
                            <h3>Nhận xét</h3>
            '''
            
            # Tìm khoảng thời gian có hiệu suất tốt nhất
            if summary['performance_by_period']:
                best_period = max(summary['performance_by_period'].items(), key=lambda x: x[1]['f1'])
                
                html += f'''
                                <p>Mô hình được huấn luyện trên dữ liệu <span class="highlight">{best_period[0]}</span> có hiệu suất tốt nhất với F1-score {best_period[1]['f1']:.4f}.</p>
                                <p>Điều này cho thấy tầm quan trọng của việc chọn khoảng thời gian dữ liệu phù hợp để huấn luyện mô hình dự đoán.</p>
                '''
            
            html += '''
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Phân tích theo mục tiêu dự đoán</h2>
                        <p>So sánh hiệu suất dự đoán dựa trên khoảng thời gian dự đoán (1 ngày, 3 ngày, v.v.)</p>
                        
                        <table>
                            <tr>
                                <th>Mục tiêu (ngày)</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>F1</th>
                                <th>Số mô hình</th>
                            </tr>
            '''
            
            # Thêm thông tin hiệu suất theo mục tiêu dự đoán
            for target, data in summary['performance_by_target'].items():
                html += '''
                            <tr>
                                <td>{target}</td>
                                <td>{accuracy:.4f}</td>
                                <td>{precision:.4f}</td>
                                <td>{recall:.4f}</td>
                                <td>{f1:.4f}</td>
                                <td>{n_models}</td>
                            </tr>
                '''.format(
                    target=target,
                    accuracy=data['accuracy'],
                    precision=data['precision'],
                    recall=data['recall'],
                    f1=data['f1'],
                    n_models=data['n_models']
                )
            
            html += '''
                        </table>
                        
                        <div class="chart">
                            <h3>Hiệu suất theo mục tiêu dự đoán</h3>
                            <img src="../ml_charts/performance_by_target.png" alt="Hiệu suất theo mục tiêu dự đoán">
                        </div>
                        
                        <div class="conclusion">
                            <h3>Nhận xét</h3>
            '''
            
            # Tìm mục tiêu có hiệu suất tốt nhất
            if summary['performance_by_target']:
                targets = list(summary['performance_by_target'].keys())
                if len(targets) > 1:
                    short_target = min(targets, key=int)
                    long_target = max(targets, key=int)
                    
                    short_f1 = summary['performance_by_target'][short_target]['f1']
                    long_f1 = summary['performance_by_target'][long_target]['f1']
                    
                    html += f'''
                                <p>Dự đoán <span class="highlight">{short_target} ngày</span> có F1-score {short_f1:.4f}, trong khi dự đoán {long_target} ngày có F1-score {long_f1:.4f}.</p>
                    '''
                    
                    if short_f1 > long_f1:
                        html += '''
                                <p>Mô hình có hiệu suất tốt hơn khi dự đoán ngắn hạn, điều này phù hợp với trực giác rằng dự đoán ngắn hạn thường chính xác hơn dự đoán dài hạn do tính bất định của thị trường tăng lên theo thời gian.</p>
                        '''
                    else:
                        html += '''
                                <p>Thú vị là mô hình có hiệu suất tốt hơn khi dự đoán dài hạn, có thể do các mẫu xu hướng dài hạn rõ ràng hơn trong dữ liệu.</p>
                        '''
            
            html += '''
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Kết luận và Đề xuất</h2>
                        <p>Dựa trên phân tích hiệu suất mô hình, có một số nhận xét và đề xuất quan trọng:</p>
                        
                        <ol>
                            <li>Mô hình <strong>{best_model}</strong> có hiệu suất tổng thể tốt nhất với F1-score {best_f1:.4f}.</li>
                            <li>Các mô hình dự đoán cho {best_coin[0]} có xu hướng chính xác hơn so với các coin khác.</li>
                            <li>Nên sử dụng mô hình được huấn luyện trên dữ liệu phù hợp với điều kiện thị trường hiện tại.</li>
                            <li>Tín hiệu mua/bán nên được lọc và kết hợp với các chiến lược khác để tăng độ tin cậy.</li>
                            <li>Cập nhật và huấn luyện lại mô hình định kỳ để thích ứng với thay đổi của thị trường.</li>
                        </ol>
                        
                        <div class="conclusion">
                            <p>Hiệu suất tổng thể của các mô hình ML cho thấy tiềm năng trong việc dự đoán xu hướng thị trường tiền điện tử. Tuy nhiên, không nên chỉ dựa vào các dự đoán này mà cần kết hợp với phân tích kỹ thuật, phân tích cơ bản và quản lý rủi ro hiệu quả để đạt kết quả tốt nhất.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            '''.format(
                timestamp=summary['timestamp'],
                total_models=summary['total_models'],
                coins=', '.join(summary['coins']),
                best_model=summary['best_models']['f1']['model'],
                best_f1=summary['best_models']['f1']['value']
            )
            
            with open(html_path, 'w') as f:
                f.write(html)
                
            logger.info(f"Đã tạo báo cáo phân tích hiệu suất: {html_path}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo phân tích hiệu suất: {str(e)}")

def main():
    """Chạy đánh giá mô hình ML"""
    logger.info("=== Bắt đầu đánh giá mô hình ML ===")
    
    evaluator = MLEvaluator()
    
    # Đánh giá tất cả các mô hình
    summary = evaluator.evaluate_all_models()
    
    # Tạo báo cáo phân tích hiệu suất
    evaluator.create_performance_analysis_report()
    
    logger.info("=== Đã hoàn thành đánh giá mô hình ML ===")
    
    return summary

if __name__ == "__main__":
    main()