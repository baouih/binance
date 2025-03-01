#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo báo cáo sử dụng thuật toán từ dữ liệu test

Script này phân tích dữ liệu từ các báo cáo test bot và tạo báo cáo chi tiết
về việc vận dụng thuật toán, chiến lược và chỉ báo trong các tình huống thị trường
khác nhau.
"""

import os
import json
import logging
import argparse
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlgorithmUsageAnalyzer:
    """Lớp phân tích việc sử dụng thuật toán"""
    
    def __init__(self, report_path=None, output_dir='reports'):
        """
        Khởi tạo analyzer
        
        Args:
            report_path (str): Đường dẫn đến file báo cáo JSON
            output_dir (str): Thư mục lưu báo cáo
        """
        self.report_path = report_path
        self.output_dir = output_dir
        self.report_data = None
        
        # Đảm bảo thư mục output tồn tại
        os.makedirs(output_dir, exist_ok=True)
    
    def load_report(self):
        """Tải dữ liệu báo cáo"""
        if not self.report_path or not os.path.exists(self.report_path):
            logger.error(f"File báo cáo không tồn tại: {self.report_path}")
            return False
        
        try:
            with open(self.report_path, 'r', encoding='utf-8') as f:
                self.report_data = json.load(f)
            
            logger.info(f"Đã tải báo cáo: {self.report_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải báo cáo: {str(e)}")
            return False
    
    def _analyze_algorithm_usage_by_regime(self):
        """Phân tích việc sử dụng thuật toán theo chế độ thị trường"""
        if not self.report_data:
            logger.error("Chưa có dữ liệu báo cáo để phân tích")
            return None
        
        results = {}
        
        try:
            algorithm_usage = self.report_data.get("algorithm_usage", {})
            for symbol, usage_data in algorithm_usage.items():
                regimes = usage_data.get("regime_detection_counts", {})
                strategies = usage_data.get("strategy_usage_counts", {})
                indicators = usage_data.get("indicators_usage", {})
                
                detailed_reports = self.report_data.get("detailed_reports", {}).get(symbol, {})
                decisions = detailed_reports.get("decisions", [])
                
                # Phân tích sử dụng chiến lược và chỉ báo theo chế độ thị trường
                regime_analysis = {}
                
                for regime in regimes.keys():
                    regime_analysis[regime] = {
                        "strategy_usage": {},
                        "indicator_usage": {},
                        "decision_counts": {
                            "BUY": 0,
                            "SELL": 0,
                            "HOLD": 0
                        },
                        "decision_records": []
                    }
                
                # Phân loại quyết định theo chế độ thị trường
                for decision in decisions:
                    regime = decision.get("regime")
                    if not regime or regime not in regime_analysis:
                        continue
                    
                    # Đếm loại quyết định
                    signal = decision.get("signal")
                    action = signal.get("action") if isinstance(signal, dict) and "action" in signal else "UNKNOWN"
                    
                    if action in regime_analysis[regime]["decision_counts"]:
                        regime_analysis[regime]["decision_counts"][action] += 1
                    else:
                        regime_analysis[regime]["decision_counts"][action] = 1
                    
                    # Theo dõi chiến lược được sử dụng trong quyết định
                    strategies_used = decision.get("strategies_used", {})
                    for strategy_name, strategy_info in strategies_used.items():
                        if strategy_name not in regime_analysis[regime]["strategy_usage"]:
                            regime_analysis[regime]["strategy_usage"][strategy_name] = 0
                        
                        # Tăng đếm nếu chiến lược đã đưa ra tín hiệu
                        if "signal" in strategy_info and strategy_info["signal"] != 0:
                            regime_analysis[regime]["strategy_usage"][strategy_name] += 1
                    
                    # Theo dõi chỉ báo được sử dụng
                    indicators_used = decision.get("indicators", {})
                    for indicator_name, value in indicators_used.items():
                        if indicator_name not in regime_analysis[regime]["indicator_usage"]:
                            regime_analysis[regime]["indicator_usage"][indicator_name] = 0
                        
                        if value is not None:
                            regime_analysis[regime]["indicator_usage"][indicator_name] += 1
                    
                    # Lưu lại quyết định
                    regime_analysis[regime]["decision_records"].append(decision)
                
                results[symbol] = regime_analysis
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích sử dụng thuật toán theo chế độ thị trường: {str(e)}")
        
        return results
    
    def _create_algorithm_usage_charts(self, algorithm_usage_by_regime):
        """Tạo biểu đồ sử dụng thuật toán"""
        if not algorithm_usage_by_regime:
            logger.error("Không có dữ liệu để tạo biểu đồ")
            return {}
        
        chart_paths = {}
        
        try:
            for symbol, regime_data in algorithm_usage_by_regime.items():
                chart_paths[symbol] = {}
                
                # Biểu đồ phân bố chế độ thị trường
                regime_counts = {regime: len(data["decision_records"]) for regime, data in regime_data.items()}
                
                if regime_counts:
                    plt.figure(figsize=(10, 6))
                    plt.bar(regime_counts.keys(), regime_counts.values())
                    plt.title(f"Phân bố chế độ thị trường - {symbol}")
                    plt.xlabel("Chế độ thị trường")
                    plt.ylabel("Số lần xuất hiện")
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    regime_chart_path = os.path.join(self.output_dir, f"{symbol}_regime_distribution.png")
                    plt.savefig(regime_chart_path)
                    plt.close()
                    
                    chart_paths[symbol]["regime_distribution"] = regime_chart_path
                
                # Biểu đồ sử dụng chiến lược theo chế độ thị trường
                for regime, data in regime_data.items():
                    strategy_usage = data["strategy_usage"]
                    
                    if strategy_usage:
                        plt.figure(figsize=(10, 6))
                        plt.bar(strategy_usage.keys(), strategy_usage.values())
                        plt.title(f"Sử dụng chiến lược trong chế độ {regime} - {symbol}")
                        plt.xlabel("Chiến lược")
                        plt.ylabel("Số lần sử dụng")
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        
                        strategy_chart_path = os.path.join(self.output_dir, f"{symbol}_{regime}_strategy_usage.png")
                        plt.savefig(strategy_chart_path)
                        plt.close()
                        
                        if "strategy_usage" not in chart_paths[symbol]:
                            chart_paths[symbol]["strategy_usage"] = {}
                        
                        chart_paths[symbol]["strategy_usage"][regime] = strategy_chart_path
                    
                    # Biểu đồ quyết định theo chế độ thị trường
                    decision_counts = data["decision_counts"]
                    
                    if decision_counts:
                        plt.figure(figsize=(8, 8))
                        plt.pie(decision_counts.values(), labels=decision_counts.keys(), autopct='%1.1f%%')
                        plt.title(f"Phân bố quyết định trong chế độ {regime} - {symbol}")
                        plt.axis('equal')
                        
                        decision_chart_path = os.path.join(self.output_dir, f"{symbol}_{regime}_decisions.png")
                        plt.savefig(decision_chart_path)
                        plt.close()
                        
                        if "decision_counts" not in chart_paths[symbol]:
                            chart_paths[symbol]["decision_counts"] = {}
                        
                        chart_paths[symbol]["decision_counts"][regime] = decision_chart_path
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ: {str(e)}")
        
        return chart_paths
    
    def _analyze_bbands_in_quiet_market(self, algorithm_usage_by_regime):
        """Phân tích hiệu quả chiến lược BBands trong thị trường yên tĩnh"""
        if not algorithm_usage_by_regime:
            logger.error("Không có dữ liệu để phân tích")
            return None
        
        results = {}
        
        for symbol, regime_data in algorithm_usage_by_regime.items():
            if "quiet" not in regime_data:
                results[symbol] = {
                    "has_quiet_market": False,
                    "bbands_usage": 0,
                    "bbands_effectiveness": None,
                    "analysis": "Không có dữ liệu về thị trường yên tĩnh"
                }
                continue
            
            quiet_data = regime_data["quiet"]
            
            # Kiểm tra sử dụng BBands
            bbands_usage = quiet_data["strategy_usage"].get("BollingerBands", 0)
            
            # Kiểm tra hiệu quả
            decisions = quiet_data["decision_records"]
            bbands_signals = 0
            correct_signals = 0
            
            for decision in decisions:
                strategies_used = decision.get("strategies_used", {})
                if "BollingerBands" in strategies_used:
                    bbands_info = strategies_used["BollingerBands"]
                    bbands_signal = bbands_info.get("signal", 0)
                    
                    if bbands_signal != 0:
                        bbands_signals += 1
                        
                        # TODO: Đánh giá tín hiệu đúng/sai dựa trên giá tiếp theo
                        # (cần dữ liệu lịch sử giá để đánh giá)
            
            if bbands_signals > 0:
                effectiveness = correct_signals / bbands_signals
            else:
                effectiveness = None
            
            results[symbol] = {
                "has_quiet_market": True,
                "bbands_usage": bbands_usage,
                "bbands_signals": bbands_signals,
                "bbands_effectiveness": effectiveness,
                "decision_counts": quiet_data["decision_counts"],
                "analysis": self._get_bbands_analysis(bbands_usage, bbands_signals, effectiveness)
            }
        
        return results
    
    def _get_bbands_analysis(self, usage, signals, effectiveness):
        """Tạo phân tích văn bản về hiệu quả BBands"""
        if usage == 0:
            return "Không có bằng chứng về việc sử dụng chiến lược BBands trong thị trường yên tĩnh"
        
        if signals == 0:
            return "Chiến lược BBands được sử dụng nhưng không sinh ra tín hiệu giao dịch"
        
        if effectiveness is None:
            return f"Chiến lược BBands sinh ra {signals} tín hiệu giao dịch nhưng chưa thể đánh giá hiệu quả"
        
        if effectiveness >= 0.7:
            return f"Chiến lược BBands hoạt động HIỆU QUẢ CAO trong thị trường yên tĩnh với {signals} tín hiệu"
        elif effectiveness >= 0.5:
            return f"Chiến lược BBands hoạt động HIỆU QUẢ TRUNG BÌNH trong thị trường yên tĩnh với {signals} tín hiệu"
        else:
            return f"Chiến lược BBands hoạt động KÉMM HIỆU QUẢ trong thị trường yên tĩnh với {signals} tín hiệu"
    
    def analyze_and_create_report(self):
        """Phân tích và tạo báo cáo sử dụng thuật toán"""
        if not self.report_data:
            if not self.load_report():
                return False
        
        # Phân tích sử dụng thuật toán theo chế độ thị trường
        algorithm_usage_by_regime = self._analyze_algorithm_usage_by_regime()
        
        # Tạo biểu đồ
        chart_paths = self._create_algorithm_usage_charts(algorithm_usage_by_regime)
        
        # Phân tích BBands trong thị trường yên tĩnh
        bbands_analysis = self._analyze_bbands_in_quiet_market(algorithm_usage_by_regime)
        
        # Tạo báo cáo HTML
        html_report = self._create_html_report(algorithm_usage_by_regime, chart_paths, bbands_analysis)
        
        # Tạo báo cáo văn bản
        text_report = self._create_text_report(algorithm_usage_by_regime, bbands_analysis)
        
        # Lưu báo cáo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        html_report_path = os.path.join(self.output_dir, f"algorithm_usage_report_{timestamp}.html")
        with open(html_report_path, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        text_report_path = os.path.join(self.output_dir, f"algorithm_usage_report_{timestamp}.txt")
        with open(text_report_path, 'w', encoding='utf-8') as f:
            f.write(text_report)
        
        logger.info(f"Đã tạo báo cáo HTML: {html_report_path}")
        logger.info(f"Đã tạo báo cáo văn bản: {text_report_path}")
        
        return {
            "html_report": html_report_path,
            "text_report": text_report_path
        }
    
    def _create_html_report(self, algorithm_usage_by_regime, chart_paths, bbands_analysis):
        """Tạo báo cáo HTML"""
        html = []
        html.append('<!DOCTYPE html>')
        html.append('<html lang="en">')
        html.append('<head>')
        html.append('    <meta charset="UTF-8">')
        html.append('    <meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html.append('    <title>Báo cáo phân tích sử dụng thuật toán</title>')
        html.append('    <style>')
        html.append('        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }')
        html.append('        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }')
        html.append('        h2 { color: #2980b9; margin-top: 30px; }')
        html.append('        h3 { color: #3498db; }')
        html.append('        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }')
        html.append('        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }')
        html.append('        th { background-color: #f2f2f2; }')
        html.append('        tr:nth-child(even) { background-color: #f9f9f9; }')
        html.append('        .chart { margin: 20px 0; max-width: 100%; }')
        html.append('        .success { color: green; }')
        html.append('        .warning { color: orange; }')
        html.append('        .danger { color: red; }')
        html.append('        .container { max-width: 1200px; margin: 0 auto; }')
        html.append('    </style>')
        html.append('</head>')
        html.append('<body>')
        html.append('    <div class="container">')
        html.append('        <h1>Báo cáo phân tích sử dụng thuật toán</h1>')
        html.append(f'        <p>Thời gian tạo báo cáo: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')
        
        # Báo cáo tổng quan
        html.append('        <h2>Tổng quan</h2>')
        html.append('        <p>Báo cáo này phân tích việc vận dụng thuật toán, chiến lược và chỉ báo trong các tình huống thị trường khác nhau.</p>')
        
        # Phân tích theo cặp tiền
        for symbol in algorithm_usage_by_regime.keys():
            html.append(f'        <h2>Phân tích cho {symbol}</h2>')
            
            # Biểu đồ phân bố chế độ thị trường
            if symbol in chart_paths and "regime_distribution" in chart_paths[symbol]:
                html.append('        <h3>Phân bố chế độ thị trường</h3>')
                html.append(f'        <img class="chart" src="{os.path.basename(chart_paths[symbol]["regime_distribution"])}" alt="Phân bố chế độ thị trường">')
            
            # Phân tích theo chế độ thị trường
            for regime, data in algorithm_usage_by_regime[symbol].items():
                html.append(f'        <h3>Chế độ thị trường: {regime}</h3>')
                
                # Thống kê quyết định
                html.append('        <h4>Phân bố quyết định</h4>')
                html.append('        <table>')
                html.append('            <tr><th>Loại quyết định</th><th>Số lượng</th></tr>')
                
                for decision, count in data["decision_counts"].items():
                    html.append(f'            <tr><td>{decision}</td><td>{count}</td></tr>')
                
                html.append('        </table>')
                
                # Biểu đồ quyết định
                if (symbol in chart_paths and "decision_counts" in chart_paths[symbol] and 
                    regime in chart_paths[symbol]["decision_counts"]):
                    html.append(f'        <img class="chart" src="{os.path.basename(chart_paths[symbol]["decision_counts"][regime])}" alt="Phân bố quyết định">')
                
                # Thống kê sử dụng chiến lược
                html.append('        <h4>Sử dụng chiến lược</h4>')
                html.append('        <table>')
                html.append('            <tr><th>Chiến lược</th><th>Số lần sử dụng</th></tr>')
                
                for strategy, count in data["strategy_usage"].items():
                    html.append(f'            <tr><td>{strategy}</td><td>{count}</td></tr>')
                
                html.append('        </table>')
                
                # Biểu đồ sử dụng chiến lược
                if (symbol in chart_paths and "strategy_usage" in chart_paths[symbol] and 
                    regime in chart_paths[symbol]["strategy_usage"]):
                    html.append(f'        <img class="chart" src="{os.path.basename(chart_paths[symbol]["strategy_usage"][regime])}" alt="Sử dụng chiến lược">')
                
                # Thống kê sử dụng chỉ báo
                html.append('        <h4>Sử dụng chỉ báo kỹ thuật</h4>')
                html.append('        <table>')
                html.append('            <tr><th>Chỉ báo</th><th>Số lần sử dụng</th></tr>')
                
                for indicator, count in data["indicator_usage"].items():
                    html.append(f'            <tr><td>{indicator}</td><td>{count}</td></tr>')
                
                html.append('        </table>')
            
            # Phân tích BBands trong thị trường yên tĩnh
            if symbol in bbands_analysis:
                html.append('        <h3>Hiệu quả của chiến lược BBands trong thị trường yên tĩnh</h3>')
                
                bb_data = bbands_analysis[symbol]
                
                if not bb_data["has_quiet_market"]:
                    html.append('        <p class="warning">Không có dữ liệu về thị trường yên tĩnh</p>')
                else:
                    html.append('        <table>')
                    html.append('            <tr><th>Thông số</th><th>Giá trị</th></tr>')
                    html.append(f'            <tr><td>Số lần sử dụng BBands</td><td>{bb_data["bbands_usage"]}</td></tr>')
                    html.append(f'            <tr><td>Số tín hiệu BBands</td><td>{bb_data["bbands_signals"]}</td></tr>')
                    
                    if bb_data["bbands_effectiveness"] is not None:
                        html.append(f'            <tr><td>Hiệu quả</td><td>{bb_data["bbands_effectiveness"]:.2%}</td></tr>')
                    else:
                        html.append('            <tr><td>Hiệu quả</td><td>Chưa đánh giá được</td></tr>')
                    
                    html.append('        </table>')
                    
                    # Hiển thị phân tích
                    css_class = "success" if bb_data["bbands_usage"] > 0 else "warning"
                    html.append(f'        <p class="{css_class}">{bb_data["analysis"]}</p>')
        
        # Kết luận và kiến nghị
        html.append('        <h2>Kết luận và kiến nghị</h2>')
        
        # TODO: Tự động tạo kết luận dựa trên phân tích
        html.append('        <p>Dựa trên phân tích sử dụng thuật toán, có thể đưa ra các kết luận và kiến nghị sau:</p>')
        html.append('        <ul>')
        
        # Kiểm tra sử dụng BBands trong thị trường yên tĩnh
        has_bbands_quiet_issues = any(
            data["has_quiet_market"] and data["bbands_usage"] == 0
            for data in bbands_analysis.values()
        )
        
        if has_bbands_quiet_issues:
            html.append('            <li class="warning">Cần tăng cường sử dụng chiến lược BBands trong thị trường yên tĩnh</li>')
        else:
            html.append('            <li class="success">Chiến lược BBands đã được vận dụng hiệu quả trong thị trường yên tĩnh</li>')
        
        # TODO: Thêm các kết luận khác dựa trên phân tích
        
        html.append('        </ul>')
        
        html.append('    </div>')
        html.append('</body>')
        html.append('</html>')
        
        return '\n'.join(html)
    
    def _create_text_report(self, algorithm_usage_by_regime, bbands_analysis):
        """Tạo báo cáo văn bản"""
        report = []
        report.append("="*80)
        report.append("BÁO CÁO PHÂN TÍCH SỬ DỤNG THUẬT TOÁN")
        report.append("="*80)
        report.append(f"Thời gian tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Báo cáo tổng quan
        report.append("TỔNG QUAN")
        report.append("-"*40)
        report.append("Báo cáo này phân tích việc vận dụng thuật toán, chiến lược và chỉ báo")
        report.append("trong các tình huống thị trường khác nhau.")
        report.append("")
        
        # Phân tích theo cặp tiền
        for symbol in algorithm_usage_by_regime.keys():
            report.append(f"PHÂN TÍCH CHO {symbol}")
            report.append("="*40)
            
            # Phân tích theo chế độ thị trường
            for regime, data in algorithm_usage_by_regime[symbol].items():
                report.append(f"Chế độ thị trường: {regime}")
                report.append("-"*30)
                
                # Thống kê quyết định
                report.append("Phân bố quyết định:")
                for decision, count in data["decision_counts"].items():
                    report.append(f"  - {decision}: {count}")
                
                report.append("")
                
                # Thống kê sử dụng chiến lược
                report.append("Sử dụng chiến lược:")
                for strategy, count in sorted(data["strategy_usage"].items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  - {strategy}: {count}")
                
                report.append("")
                
                # Thống kê sử dụng chỉ báo
                report.append("Sử dụng chỉ báo kỹ thuật:")
                for indicator, count in sorted(data["indicator_usage"].items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  - {indicator}: {count}")
                
                report.append("")
            
            # Phân tích BBands trong thị trường yên tĩnh
            if symbol in bbands_analysis:
                report.append("Hiệu quả của chiến lược BBands trong thị trường yên tĩnh")
                report.append("-"*30)
                
                bb_data = bbands_analysis[symbol]
                
                if not bb_data["has_quiet_market"]:
                    report.append("Không có dữ liệu về thị trường yên tĩnh")
                else:
                    report.append(f"Số lần sử dụng BBands: {bb_data['bbands_usage']}")
                    report.append(f"Số tín hiệu BBands: {bb_data['bbands_signals']}")
                    
                    if bb_data["bbands_effectiveness"] is not None:
                        report.append(f"Hiệu quả: {bb_data['bbands_effectiveness']:.2%}")
                    else:
                        report.append("Hiệu quả: Chưa đánh giá được")
                    
                    report.append("")
                    report.append(bb_data["analysis"])
                
                report.append("")
        
        # Kết luận và kiến nghị
        report.append("KẾT LUẬN VÀ KIẾN NGHỊ")
        report.append("="*40)
        
        # Kiểm tra sử dụng BBands trong thị trường yên tĩnh
        has_bbands_quiet_issues = any(
            data["has_quiet_market"] and data["bbands_usage"] == 0
            for data in bbands_analysis.values()
        )
        
        if has_bbands_quiet_issues:
            report.append("! Cần tăng cường sử dụng chiến lược BBands trong thị trường yên tĩnh")
        else:
            report.append("✓ Chiến lược BBands đã được vận dụng hiệu quả trong thị trường yên tĩnh")
        
        # TODO: Thêm các kết luận khác dựa trên phân tích
        
        return "\n".join(report)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Phân tích sử dụng thuật toán từ báo cáo test')
    parser.add_argument('--report', required=True, help='Đường dẫn đến file báo cáo JSON')
    parser.add_argument('--output', default='reports', help='Thư mục lưu báo cáo kết quả')
    
    args = parser.parse_args()
    
    analyzer = AlgorithmUsageAnalyzer(report_path=args.report, output_dir=args.output)
    analyzer.analyze_and_create_report()