#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo báo cáo HTML đẹp, dễ đọc từ kết quả phân tích ML
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
from typing import List, Dict, Tuple, Any
import argparse

# Thiết lập để không hiển thị biểu đồ khi chạy trong server
matplotlib.use('Agg')

def create_comparison_charts(report_dir='ml_results', charts_dir='ml_charts'):
    """
    Tạo biểu đồ so sánh hiệu suất các mô hình ML
    
    Args:
        report_dir (str): Thư mục chứa kết quả
        charts_dir (str): Thư mục lưu biểu đồ
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs(charts_dir, exist_ok=True)
    
    # Tìm tất cả file kết quả
    json_files = [os.path.join(report_dir, f) for f in os.listdir(report_dir) 
                 if f.endswith('_results.json')]
    
    if not json_files:
        print(f"Không tìm thấy file kết quả nào trong {report_dir}")
        return []
    
    print(f"Đã tìm thấy {len(json_files)} file kết quả")
    
    # Thu thập dữ liệu
    results = []
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                result = json.load(f)
            results.append(result)
        except Exception as e:
            print(f"Lỗi khi tải file {json_file}: {e}")
    
    if not results:
        print("Không tải được kết quả nào")
        return []
    
    print(f"Đã tải {len(results)} kết quả thành công")
    
    # Tạo DataFrame từ kết quả
    df_results = pd.DataFrame([{
        'symbol': r.get('symbol', ''),
        'timeframe': r.get('timeframe', ''),
        'period': r.get('period', ''),
        'prediction_days': r.get('prediction_days', 0),
        'model_type': r.get('model_type', ''),
        'accuracy': r.get('accuracy', 0),
        'precision': r.get('precision', 0),
        'recall': r.get('recall', 0),
        'f1_score': r.get('f1_score', 0),
        'timestamp': r.get('timestamp', ''),
        'file_path': json_file
    } for r, json_file in zip(results, json_files)])
    
    # 1. So sánh hiệu suất theo khoảng thời gian
    period_stats = df_results.groupby('period').agg({
        'accuracy': 'mean',
        'precision': 'mean',
        'recall': 'mean',
        'f1_score': 'mean',
        'symbol': 'count'
    }).rename(columns={'symbol': 'count'}).reset_index()
    
    # Map period names
    period_mapping = {
        '1_month': '1 tháng',
        '3_months': '3 tháng',
        '6_months': '6 tháng'
    }
    period_stats['period_name'] = period_stats['period'].map(period_mapping)
    
    # Sắp xếp theo thứ tự khoảng thời gian
    period_order = ['1_month', '3_months', '6_months']
    period_stats['sort_order'] = period_stats['period'].apply(lambda x: period_order.index(x) if x in period_order else 999)
    period_stats = period_stats.sort_values('sort_order')
    
    # Tạo biểu đồ
    plt.figure(figsize=(10, 6))
    x = np.arange(len(period_stats))
    width = 0.2
    
    plt.bar(x - width*1.5, period_stats['accuracy'], width, label='Accuracy')
    plt.bar(x - width/2, period_stats['precision'], width, label='Precision')
    plt.bar(x + width/2, period_stats['recall'], width, label='Recall')
    plt.bar(x + width*1.5, period_stats['f1_score'], width, label='F1-Score')
    
    plt.xlabel('Khoảng thời gian')
    plt.ylabel('Điểm số')
    plt.title('So sánh hiệu suất theo khoảng thời gian')
    plt.xticks(x, period_stats['period_name'])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend()
    
    # Lưu biểu đồ
    period_chart_path = f"{charts_dir}/period_comparison.png"
    plt.savefig(period_chart_path, dpi=300)
    plt.close()
    
    print(f"Đã tạo biểu đồ so sánh theo khoảng thời gian: {period_chart_path}")
    
    # 2. So sánh hiệu suất theo mục tiêu dự đoán
    target_stats = df_results.groupby('prediction_days').agg({
        'accuracy': 'mean',
        'precision': 'mean',
        'recall': 'mean',
        'f1_score': 'mean',
        'symbol': 'count'
    }).rename(columns={'symbol': 'count'}).reset_index()
    
    # Tạo biểu đồ
    plt.figure(figsize=(10, 6))
    x = np.arange(len(target_stats))
    width = 0.2
    
    plt.bar(x - width*1.5, target_stats['accuracy'], width, label='Accuracy')
    plt.bar(x - width/2, target_stats['precision'], width, label='Precision')
    plt.bar(x + width/2, target_stats['recall'], width, label='Recall')
    plt.bar(x + width*1.5, target_stats['f1_score'], width, label='F1-Score')
    
    plt.xlabel('Mục tiêu dự đoán (ngày)')
    plt.ylabel('Điểm số')
    plt.title('So sánh hiệu suất theo mục tiêu dự đoán')
    plt.xticks(x, [f"{int(d)} ngày" for d in target_stats['prediction_days']])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend()
    
    # Lưu biểu đồ
    target_chart_path = f"{charts_dir}/target_comparison.png"
    plt.savefig(target_chart_path, dpi=300)
    plt.close()
    
    print(f"Đã tạo biểu đồ so sánh theo mục tiêu dự đoán: {target_chart_path}")
    
    # 3. So sánh hiệu suất theo đồng tiền
    symbol_stats = df_results.groupby('symbol').agg({
        'accuracy': 'mean',
        'precision': 'mean',
        'recall': 'mean',
        'f1_score': 'mean',
        'timeframe': 'count'
    }).rename(columns={'timeframe': 'count'}).reset_index()
    
    # Sắp xếp theo F1-score
    symbol_stats = symbol_stats.sort_values('f1_score', ascending=False)
    
    # Tạo biểu đồ
    plt.figure(figsize=(12, 6))
    x = np.arange(len(symbol_stats))
    width = 0.2
    
    plt.bar(x - width*1.5, symbol_stats['accuracy'], width, label='Accuracy')
    plt.bar(x - width/2, symbol_stats['precision'], width, label='Precision')
    plt.bar(x + width/2, symbol_stats['recall'], width, label='Recall')
    plt.bar(x + width*1.5, symbol_stats['f1_score'], width, label='F1-Score')
    
    plt.xlabel('Mã tiền điện tử')
    plt.ylabel('Điểm số')
    plt.title('So sánh hiệu suất theo đồng tiền')
    plt.xticks(x, symbol_stats['symbol'])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend()
    
    # Lưu biểu đồ
    symbol_chart_path = f"{charts_dir}/symbol_comparison.png"
    plt.savefig(symbol_chart_path, dpi=300)
    plt.close()
    
    print(f"Đã tạo biểu đồ so sánh theo đồng tiền: {symbol_chart_path}")
    
    # 4. So sánh hiệu suất theo khung thời gian
    timeframe_stats = df_results.groupby('timeframe').agg({
        'accuracy': 'mean',
        'precision': 'mean',
        'recall': 'mean',
        'f1_score': 'mean',
        'symbol': 'count'
    }).rename(columns={'symbol': 'count'}).reset_index()
    
    # Sắp xếp theo khung thời gian
    timeframe_order = {'1m': 0, '5m': 1, '15m': 2, '30m': 3, '1h': 4, '4h': 5, '1d': 6, '1w': 7}
    timeframe_stats['sort_order'] = timeframe_stats['timeframe'].apply(lambda x: timeframe_order.get(x, 999))
    timeframe_stats = timeframe_stats.sort_values('sort_order')
    
    # Tạo biểu đồ
    plt.figure(figsize=(10, 6))
    x = np.arange(len(timeframe_stats))
    width = 0.2
    
    plt.bar(x - width*1.5, timeframe_stats['accuracy'], width, label='Accuracy')
    plt.bar(x - width/2, timeframe_stats['precision'], width, label='Precision')
    plt.bar(x + width/2, timeframe_stats['recall'], width, label='Recall')
    plt.bar(x + width*1.5, timeframe_stats['f1_score'], width, label='F1-Score')
    
    plt.xlabel('Khung thời gian')
    plt.ylabel('Điểm số')
    plt.title('So sánh hiệu suất theo khung thời gian')
    plt.xticks(x, timeframe_stats['timeframe'])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend()
    
    # Lưu biểu đồ
    timeframe_chart_path = f"{charts_dir}/timeframe_comparison.png"
    plt.savefig(timeframe_chart_path, dpi=300)
    plt.close()
    
    print(f"Đã tạo biểu đồ so sánh theo khung thời gian: {timeframe_chart_path}")
    
    # 5. So sánh hiệu suất theo loại mô hình
    model_stats = df_results.groupby('model_type').agg({
        'accuracy': 'mean',
        'precision': 'mean',
        'recall': 'mean',
        'f1_score': 'mean',
        'symbol': 'count'
    }).rename(columns={'symbol': 'count'}).reset_index()
    
    # Tạo biểu đồ
    plt.figure(figsize=(10, 6))
    x = np.arange(len(model_stats))
    width = 0.2
    
    plt.bar(x - width*1.5, model_stats['accuracy'], width, label='Accuracy')
    plt.bar(x - width/2, model_stats['precision'], width, label='Precision')
    plt.bar(x + width/2, model_stats['recall'], width, label='Recall')
    plt.bar(x + width*1.5, model_stats['f1_score'], width, label='F1-Score')
    
    plt.xlabel('Loại mô hình')
    plt.ylabel('Điểm số')
    plt.title('So sánh hiệu suất theo loại mô hình')
    plt.xticks(x, model_stats['model_type'])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend()
    
    # Lưu biểu đồ
    model_chart_path = f"{charts_dir}/model_comparison.png"
    plt.savefig(model_chart_path, dpi=300)
    plt.close()
    
    print(f"Đã tạo biểu đồ so sánh theo loại mô hình: {model_chart_path}")
    
    # Thu thập danh sách đường dẫn biểu đồ
    chart_paths = {
        'period_chart': period_chart_path,
        'target_chart': target_chart_path,
        'symbol_chart': symbol_chart_path,
        'timeframe_chart': timeframe_chart_path,
        'model_chart': model_chart_path
    }
    
    # Thu thập thống kê tổng quát
    global_stats = {
        'total_models': len(df_results),
        'avg_accuracy': df_results['accuracy'].mean(),
        'avg_precision': df_results['precision'].mean(),
        'avg_recall': df_results['recall'].mean(),
        'avg_f1_score': df_results['f1_score'].mean(),
        'best_model': df_results.loc[df_results['f1_score'].idxmax()].to_dict(),
        'period_stats': period_stats.to_dict('records'),
        'target_stats': target_stats.to_dict('records'),
        'symbol_stats': symbol_stats.to_dict('records'),
        'timeframe_stats': timeframe_stats.to_dict('records'),
        'model_stats': model_stats.to_dict('records')
    }
    
    return chart_paths, global_stats

def create_html_report(chart_paths, global_stats, output_path='ml_report.html'):
    """
    Tạo báo cáo HTML với các biểu đồ đã tạo
    
    Args:
        chart_paths (dict): Đường dẫn đến các biểu đồ
        global_stats (dict): Thống kê tổng quát
        output_path (str): Đường dẫn lưu báo cáo
    """
    # CSS cho báo cáo
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
        .summary-cards {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            margin: 20px 0;
        }
        .card {
            flex: 1 1 200px;
            background: white;
            padding: 15px;
            margin: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .card-value {
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
            display: block;
            margin: 10px 0;
        }
        .card-label {
            font-size: 14px;
            color: #7f8c8d;
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
        footer {
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            font-size: 12px;
            color: #7f8c8d;
        }
    </style>
    """
    
    # Lấy thông tin từ global_stats
    total_models = global_stats['total_models']
    avg_accuracy = global_stats['avg_accuracy']
    avg_precision = global_stats['avg_precision']
    avg_recall = global_stats['avg_recall']
    avg_f1_score = global_stats['avg_f1_score']
    best_model = global_stats['best_model']
    
    # Tạo HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Báo cáo ML - Trading Bot</title>
        {css}
    </head>
    <body>
        <h1>Báo cáo Machine Learning - Trading Bot</h1>
        
        <div class="section">
            <h2>Tổng quan</h2>
            <div class="summary-cards">
                <div class="card">
                    <span class="card-label">Tổng số mô hình</span>
                    <span class="card-value">{total_models}</span>
                </div>
                <div class="card">
                    <span class="card-label">Độ chính xác trung bình</span>
                    <span class="card-value">{avg_accuracy:.2f}</span>
                </div>
                <div class="card">
                    <span class="card-label">F1-Score trung bình</span>
                    <span class="card-value">{avg_f1_score:.2f}</span>
                </div>
                <div class="card">
                    <span class="card-label">Recall trung bình</span>
                    <span class="card-value">{avg_recall:.2f}</span>
                </div>
            </div>
            
            <div class="highlight">
                <h3>Mô hình tốt nhất</h3>
                <p><strong>Symbol:</strong> {best_model.get('symbol', '')}</p>
                <p><strong>Khung thời gian:</strong> {best_model.get('timeframe', '')}</p>
                <p><strong>Khoảng thời gian:</strong> {best_model.get('period', '')}</p>
                <p><strong>Mục tiêu dự đoán:</strong> {best_model.get('prediction_days', '')} ngày</p>
                <p><strong>Loại mô hình:</strong> {best_model.get('model_type', '')}</p>
                <p><strong>Độ chính xác:</strong> {best_model.get('accuracy', 0):.4f}</p>
                <p><strong>F1-Score:</strong> {best_model.get('f1_score', 0):.4f}</p>
            </div>
        </div>
        
        <div class="section">
            <h2>So sánh theo khoảng thời gian</h2>
            <div class="chart-container">
                <img src="{chart_paths.get('period_chart', '')}" alt="So sánh theo khoảng thời gian">
            </div>
            <p>Biểu đồ này so sánh hiệu suất của các mô hình được huấn luyện trên các khoảng thời gian dữ liệu khác nhau (1 tháng, 3 tháng, 6 tháng).</p>
            <p>Nhận xét:</p>
            <ul>
                <li>Dữ liệu nhiều tháng hơn thường mang lại hiệu suất tốt hơn do có nhiều mẫu huấn luyện hơn.</li>
                <li>Mô hình có thể phát hiện các mẫu lặp lại trong dữ liệu dài hạn.</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>So sánh theo mục tiêu dự đoán</h2>
            <div class="chart-container">
                <img src="{chart_paths.get('target_chart', '')}" alt="So sánh theo mục tiêu dự đoán">
            </div>
            <p>Biểu đồ này so sánh hiệu suất của các mô hình với các mục tiêu dự đoán khác nhau (1 ngày, 3 ngày, 7 ngày).</p>
            <p>Nhận xét:</p>
            <ul>
                <li>Dự đoán thời gian ngắn hạn thường chính xác hơn dự đoán dài hạn.</li>
                <li>Độ tin cậy của mô hình giảm khi thời gian dự đoán tăng.</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>So sánh theo đồng tiền</h2>
            <div class="chart-container">
                <img src="{chart_paths.get('symbol_chart', '')}" alt="So sánh theo đồng tiền">
            </div>
            <p>Biểu đồ này so sánh hiệu suất của các mô hình trên các đồng tiền khác nhau.</p>
            <p>Nhận xét:</p>
            <ul>
                <li>Bitcoin (BTC) và Ethereum (ETH) thường có hiệu suất dự đoán tốt hơn do tính thanh khoản cao và biến động ít hơn.</li>
                <li>Các altcoin có vốn hóa nhỏ thường khó dự đoán hơn do biến động mạnh và bất thường.</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>So sánh theo khung thời gian</h2>
            <div class="chart-container">
                <img src="{chart_paths.get('timeframe_chart', '')}" alt="So sánh theo khung thời gian">
            </div>
            <p>Biểu đồ này so sánh hiệu suất của các mô hình trên các khung thời gian khác nhau (1h, 4h, 1d).</p>
            <p>Nhận xét:</p>
            <ul>
                <li>Khung thời gian lớn hơn (4h, 1d) thường mang lại hiệu suất tốt hơn do ít nhiễu và bắt được xu hướng chính của thị trường.</li>
                <li>Khung thời gian nhỏ (1h, 15m) chứa nhiều biến động ngắn hạn làm nhiễu mô hình.</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>So sánh theo loại mô hình</h2>
            <div class="chart-container">
                <img src="{chart_paths.get('model_chart', '')}" alt="So sánh theo loại mô hình">
            </div>
            <p>Biểu đồ này so sánh hiệu suất của các loại mô hình machine learning khác nhau.</p>
            <p>Nhận xét:</p>
            <ul>
                <li>Mô hình Random Forest thường có hiệu suất tốt trên dữ liệu tài chính do khả năng xử lý nhiễu và đặc trưng phi tuyến tính.</li>
                <li>Gradient Boosting cung cấp độ chính xác cao nhưng có thể dễ bị overfitting khi không được tối ưu hóa cẩn thận.</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>Kết luận và đề xuất</h2>
            <p>Dựa trên phân tích hiệu suất, chúng tôi đề xuất:</p>
            <ol>
                <li><strong>Loại mô hình:</strong> Sử dụng Random Forest hoặc Gradient Boosting tùy thuộc vào đặc tính của đồng tiền.</li>
                <li><strong>Khung thời gian:</strong> Ưu tiên mô hình trên khung 4h hoặc 1d cho giao dịch dài hạn, 1h cho giao dịch trong ngày.</li>
                <li><strong>Khoảng thời gian dữ liệu:</strong> Sử dụng ít nhất 3 tháng dữ liệu để huấn luyện.</li>
                <li><strong>Mục tiêu dự đoán:</strong> Tập trung vào dự đoán 1-3 ngày để đảm bảo độ chính xác.</li>
                <li><strong>Đồng tiền:</strong> Ưu tiên ứng dụng mô hình cho các đồng vốn hóa lớn (BTC, ETH) trước khi mở rộng sang các altcoin.</li>
            </ol>
            <p>Để tiếp tục cải thiện hiệu suất, cần:</p>
            <ul>
                <li>Kết hợp phân tích chỉ báo kỹ thuật với phân tích sentiment từ mạng xã hội.</li>
                <li>Áp dụng phương pháp tinh chỉnh tham số tự động cho mỗi đồng tiền.</li>
                <li>Triển khai chiến lược ensemble kết hợp dự đoán từ nhiều mô hình khác nhau.</li>
            </ul>
        </div>
        
        <footer>
            <p>Báo cáo được tạo lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </body>
    </html>
    """
    
    # Lưu báo cáo HTML
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Đã tạo báo cáo HTML tại: {output_path}")
    return output_path

def main():
    """Hàm chính để tạo báo cáo"""
    parser = argparse.ArgumentParser(description='Tạo báo cáo HTML từ kết quả ML')
    parser.add_argument('--results_dir', type=str, default='ml_results', help='Thư mục chứa kết quả')
    parser.add_argument('--charts_dir', type=str, default='ml_charts', help='Thư mục lưu biểu đồ')
    parser.add_argument('--output', type=str, default='ml_report.html', help='Tên file báo cáo')
    
    args = parser.parse_args()
    
    print("=== Bắt đầu tạo báo cáo HTML ===")
    
    # Tạo biểu đồ so sánh
    chart_paths, global_stats = create_comparison_charts(args.results_dir, args.charts_dir)
    
    if chart_paths:
        # Tạo báo cáo HTML
        report_path = create_html_report(chart_paths, global_stats, args.output)
        print(f"=== Hoàn tất tạo báo cáo HTML: {report_path} ===")
    else:
        print("=== Không thể tạo báo cáo do thiếu dữ liệu ===")

if __name__ == "__main__":
    main()