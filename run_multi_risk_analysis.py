#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script chạy phân tích hiệu suất giao dịch ở nhiều mức rủi ro khác nhau

Script này thực hiện backtest với 5 mức rủi ro khác nhau (0.5%, 1.0%, 1.5%, 2.0%, 3.0%)
và tạo báo cáo so sánh hiệu suất để xác định mức rủi ro tối ưu.
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("multi_risk_analysis")

def setup_directories():
    """Tạo thư mục kết quả nếu chưa tồn tại"""
    directories = [
        "backtest_results/risk_level_comparison",
        "risk_analysis/charts"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Đã tạo thư mục: {directory}")

def run_backtest(symbol: str, interval: str, risk: float, adaptive_risk: bool = True,
               timeout: int = 1800) -> bool:
    """
    Chạy backtest với tham số cụ thể
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        risk (float): Mức rủi ro
        adaptive_risk (bool): Sử dụng rủi ro thích ứng hay không
        timeout (int): Thời gian chờ tối đa (giây)
        
    Returns:
        bool: True nếu thành công, False nếu lỗi
    """
    adaptive_flag = "--adaptive_risk" if adaptive_risk else ""
    command = f"python enhanced_backtest.py --symbol {symbol} --interval {interval} --risk {risk} {adaptive_flag}"
    
    logger.info(f"Đang chạy backtest: {command}")
    
    try:
        # Chạy với timeout
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Đặt timeout
        start_time = time.time()
        while process.poll() is None:
            if time.time() - start_time > timeout:
                process.terminate()
                logger.error(f"Backtest bị hủy do vượt quá thời gian chờ {timeout} giây")
                return False
            time.sleep(1)
        
        # Kiểm tra kết quả
        return_code = process.returncode
        if return_code != 0:
            stderr = process.stderr.read().decode('utf-8')
            logger.error(f"Backtest thất bại với mã lỗi {return_code}: {stderr}")
            return False
            
        logger.info(f"Backtest thành công với mức rủi ro {risk}%")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest: {e}")
        return False

def copy_result_file(risk: float, adaptive: bool = True) -> bool:
    """
    Sao chép file kết quả vào thư mục so sánh
    
    Args:
        risk (float): Mức rủi ro
        adaptive (bool): Rủi ro thích ứng hay không
        
    Returns:
        bool: True nếu thành công, False nếu lỗi
    """
    risk_str = str(risk).replace('.', '_')
    adaptive_str = "adaptive" if adaptive else "static"
    source_file = f"backtest_results/BTCUSDT_1h_{adaptive_str}_results.json"
    dest_file = f"backtest_results/risk_level_comparison/BTCUSDT_1h_risk{risk_str}_{adaptive_str}_results.json"
    
    try:
        if not os.path.exists(source_file):
            logger.error(f"File nguồn không tồn tại: {source_file}")
            return False
            
        import shutil
        shutil.copy2(source_file, dest_file)
        logger.info(f"Đã sao chép kết quả vào: {dest_file}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi sao chép file kết quả: {e}")
        return False

def extract_performance_metrics(risk: float, adaptive: bool = True) -> Dict:
    """
    Trích xuất các chỉ số hiệu suất từ file kết quả
    
    Args:
        risk (float): Mức rủi ro
        adaptive (bool): Rủi ro thích ứng hay không
        
    Returns:
        Dict: Các chỉ số hiệu suất
    """
    risk_str = str(risk).replace('.', '_')
    adaptive_str = "adaptive" if adaptive else "static"
    result_file = f"backtest_results/risk_level_comparison/BTCUSDT_1h_risk{risk_str}_{adaptive_str}_results.json"
    
    try:
        if not os.path.exists(result_file):
            logger.error(f"File kết quả không tồn tại: {result_file}")
            return {}
            
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Trích xuất các chỉ số chính
        metrics = {
            "risk_level": risk,
            "adaptive": adaptive,
            "total_profit": data.get("total_profit_percentage", 0),
            "win_rate": data.get("win_rate", 0) * 100,
            "profit_factor": data.get("profit_factor", 0),
            "max_drawdown": data.get("max_drawdown_percentage", 0),
            "trade_count": data.get("total_trades", 0),
            "avg_profit_per_trade": data.get("average_profit_per_trade", 0),
            "sharpe_ratio": data.get("sharpe_ratio", 0),
            
            # Phân tích theo chế độ thị trường
            "regime_performance": data.get("regime_performance", {})
        }
        
        return metrics
    except Exception as e:
        logger.error(f"Lỗi khi trích xuất chỉ số hiệu suất: {e}")
        return {}

def generate_comparison_report(metrics_list: List[Dict]) -> str:
    """
    Tạo báo cáo so sánh hiệu suất
    
    Args:
        metrics_list (List[Dict]): Danh sách các chỉ số hiệu suất
        
    Returns:
        str: Nội dung báo cáo
    """
    if not metrics_list:
        return "Không có dữ liệu để tạo báo cáo"
    
    # Sắp xếp theo mức rủi ro
    metrics_list.sort(key=lambda x: x.get("risk_level", 0))
    
    # Tạo báo cáo
    report = "# Báo Cáo So Sánh Hiệu Suất Theo Mức Rủi Ro\n\n"
    report += "## Tổng Quan\n\n"
    
    # Bảng tổng quan
    report += "| Mức Rủi Ro | Lợi Nhuận | Win Rate | Profit Factor | Max Drawdown | Giao Dịch | Lợi Nhuận/Giao Dịch |\n"
    report += "|------------|-----------|----------|---------------|--------------|-----------|---------------------|\n"
    
    for metrics in metrics_list:
        risk = metrics.get("risk_level", 0)
        adaptive = "+" if metrics.get("adaptive", False) else "-"
        profit = f"{metrics.get('total_profit', 0):.2f}%"
        win_rate = f"{metrics.get('win_rate', 0):.1f}%"
        pf = f"{metrics.get('profit_factor', 0):.2f}"
        dd = f"{metrics.get('max_drawdown', 0):.2f}%"
        trades = str(metrics.get("trade_count", 0))
        avg_profit = f"{metrics.get('avg_profit_per_trade', 0):.2f} USDT"
        
        report += f"| {risk}% ({adaptive}) | {profit} | {win_rate} | {pf} | {dd} | {trades} | {avg_profit} |\n"
    
    # Phân tích chi tiết
    report += "\n## Phân Tích Chi Tiết\n\n"
    
    for metrics in metrics_list:
        risk = metrics.get("risk_level", 0)
        adaptive = "thích ứng" if metrics.get("adaptive", False) else "cố định"
        
        report += f"### Mức Rủi Ro {risk}% ({adaptive})\n\n"
        
        # Phân tích theo chế độ thị trường
        regime_perf = metrics.get("regime_performance", {})
        if regime_perf:
            report += "#### Hiệu Suất Theo Chế Độ Thị Trường\n\n"
            report += "| Chế Độ | Win Rate | Lợi Nhuận | Giao Dịch |\n"
            report += "|--------|----------|-----------|----------|\n"
            
            for regime, perf in regime_perf.items():
                r_win_rate = f"{perf.get('win_rate', 0) * 100:.1f}%"
                r_profit = f"{perf.get('profit_percentage', 0):.2f}%"
                r_trades = str(perf.get("trade_count", 0))
                
                report += f"| {regime} | {r_win_rate} | {r_profit} | {r_trades} |\n"
        
        report += "\n"
    
    # Kết luận
    report += "## Kết Luận và Đề Xuất\n\n"
    
    # Tìm mức rủi ro có profit factor cao nhất
    best_pf_metrics = max(metrics_list, key=lambda x: x.get("profit_factor", 0))
    best_pf_risk = best_pf_metrics.get("risk_level", 0)
    best_pf_adaptive = "thích ứng" if best_pf_metrics.get("adaptive", False) else "cố định"
    
    # Tìm mức rủi ro có win rate cao nhất
    best_wr_metrics = max(metrics_list, key=lambda x: x.get("win_rate", 0))
    best_wr_risk = best_wr_metrics.get("risk_level", 0)
    best_wr_adaptive = "thích ứng" if best_wr_metrics.get("adaptive", False) else "cố định"
    
    # Tìm mức rủi ro có tổng lợi nhuận cao nhất
    best_profit_metrics = max(metrics_list, key=lambda x: x.get("total_profit", 0))
    best_profit_risk = best_profit_metrics.get("risk_level", 0)
    best_profit_adaptive = "thích ứng" if best_profit_metrics.get("adaptive", False) else "cố định"
    
    report += f"1. **Profit Factor cao nhất**: Mức rủi ro {best_pf_risk}% ({best_pf_adaptive}) với profit factor {best_pf_metrics.get('profit_factor', 0):.2f}\n"
    report += f"2. **Win Rate cao nhất**: Mức rủi ro {best_wr_risk}% ({best_wr_adaptive}) với win rate {best_wr_metrics.get('win_rate', 0):.1f}%\n"
    report += f"3. **Lợi nhuận cao nhất**: Mức rủi ro {best_profit_risk}% ({best_profit_adaptive}) với lợi nhuận {best_profit_metrics.get('total_profit', 0):.2f}%\n\n"
    
    # Đề xuất
    report += "### Đề Xuất\n\n"
    report += "Dựa trên kết quả phân tích, đề xuất cấu hình tối ưu:\n\n"
    
    # Đề xuất mức rủi ro tối ưu
    optimal_metrics = max(metrics_list, key=lambda x: x.get("profit_factor", 0) * 0.5 + x.get("win_rate", 0) / 100 * 0.3 + x.get("total_profit", 0) / 100 * 0.2)
    optimal_risk = optimal_metrics.get("risk_level", 0)
    optimal_adaptive = optimal_metrics.get("adaptive", True)
    
    report += f"- **Mức rủi ro tối ưu**: {optimal_risk}%\n"
    report += f"- **Rủi ro thích ứng**: {'Bật' if optimal_adaptive else 'Tắt'}\n"
    report += f"- **Profit Factor dự kiến**: {optimal_metrics.get('profit_factor', 0):.2f}\n"
    report += f"- **Win Rate dự kiến**: {optimal_metrics.get('win_rate', 0):.1f}%\n"
    report += f"- **Lợi nhuận dự kiến**: {optimal_metrics.get('total_profit', 0):.2f}%\n\n"
    
    # Phân tích lý do
    report += "### Lý Do Đề Xuất\n\n"
    report += f"Mức rủi ro {optimal_risk}% với chế độ rủi ro thích ứng {'bật' if optimal_adaptive else 'tắt'} cung cấp sự cân bằng tốt nhất giữa:\n\n"
    report += "1. Profit factor cao, giảm thiểu rủi ro lỗ vốn\n"
    report += "2. Win rate ổn định, tạo tâm lý tích cực cho nhà giao dịch\n"
    report += "3. Tổng lợi nhuận tốt, đáp ứng mục tiêu tăng trưởng vốn\n"
    
    return report

def generate_comparison_charts(metrics_list: List[Dict]) -> bool:
    """
    Tạo biểu đồ so sánh hiệu suất
    
    Args:
        metrics_list (List[Dict]): Danh sách các chỉ số hiệu suất
        
    Returns:
        bool: True nếu thành công, False nếu lỗi
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        if not metrics_list:
            logger.error("Không có dữ liệu để tạo biểu đồ")
            return False
        
        # Sắp xếp theo mức rủi ro
        metrics_list.sort(key=lambda x: x.get("risk_level", 0))
        
        # Dữ liệu cho biểu đồ
        risk_levels = [f"{m.get('risk_level', 0)}%" for m in metrics_list]
        profits = [m.get("total_profit", 0) for m in metrics_list]
        win_rates = [m.get("win_rate", 0) for m in metrics_list]
        profit_factors = [m.get("profit_factor", 0) for m in metrics_list]
        drawdowns = [abs(m.get("max_drawdown", 0)) for m in metrics_list]
        
        # Biểu đồ 1: So sánh lợi nhuận và win rate
        plt.figure(figsize=(12, 7))
        
        # Trục x chính
        x = np.arange(len(risk_levels))
        width = 0.35
        
        # Trục cho lợi nhuận
        ax1 = plt.subplot(111)
        bars1 = ax1.bar(x - width/2, profits, width, label='Lợi nhuận (%)', color='#2ecc71')
        ax1.set_xlabel('Mức Rủi Ro')
        ax1.set_ylabel('Lợi Nhuận (%)', color='#2ecc71')
        ax1.set_title('So Sánh Lợi Nhuận và Win Rate Theo Mức Rủi Ro')
        ax1.set_xticks(x)
        ax1.set_xticklabels(risk_levels)
        ax1.tick_params(axis='y', labelcolor='#2ecc71')
        
        # Trục cho win rate
        ax2 = ax1.twinx()
        bars2 = ax2.bar(x + width/2, win_rates, width, label='Win Rate (%)', color='#3498db')
        ax2.set_ylabel('Win Rate (%)', color='#3498db')
        ax2.tick_params(axis='y', labelcolor='#3498db')
        
        # Thêm giá trị lên mỗi cột
        for bar in bars1:
            height = bar.get_height()
            ax1.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        for bar in bars2:
            height = bar.get_height()
            ax2.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        # Thêm legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        plt.savefig('risk_analysis/charts/profit_winrate_comparison.png', dpi=300)
        plt.close()
        
        # Biểu đồ 2: So sánh profit factor và drawdown
        plt.figure(figsize=(12, 7))
        
        # Trục x chính
        x = np.arange(len(risk_levels))
        width = 0.35
        
        # Trục cho profit factor
        ax1 = plt.subplot(111)
        bars1 = ax1.bar(x - width/2, profit_factors, width, label='Profit Factor', color='#f39c12')
        ax1.set_xlabel('Mức Rủi Ro')
        ax1.set_ylabel('Profit Factor', color='#f39c12')
        ax1.set_title('So Sánh Profit Factor và Max Drawdown Theo Mức Rủi Ro')
        ax1.set_xticks(x)
        ax1.set_xticklabels(risk_levels)
        ax1.tick_params(axis='y', labelcolor='#f39c12')
        
        # Trục cho drawdown
        ax2 = ax1.twinx()
        bars2 = ax2.bar(x + width/2, drawdowns, width, label='Max Drawdown (%)', color='#e74c3c')
        ax2.set_ylabel('Max Drawdown (%)', color='#e74c3c')
        ax2.tick_params(axis='y', labelcolor='#e74c3c')
        
        # Thêm giá trị lên mỗi cột
        for bar in bars1:
            height = bar.get_height()
            ax1.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        for bar in bars2:
            height = bar.get_height()
            ax2.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        # Thêm legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        plt.savefig('risk_analysis/charts/profitfactor_drawdown_comparison.png', dpi=300)
        plt.close()
        
        logger.info("Đã tạo biểu đồ so sánh thành công")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ so sánh: {e}")
        return False

def run_analysis(symbol: str = "BTCUSDT", interval: str = "1h") -> bool:
    """
    Chạy phân tích đa mức rủi ro
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        
    Returns:
        bool: True nếu thành công, False nếu lỗi
    """
    # Thiết lập thư mục
    setup_directories()
    
    # Danh sách mức rủi ro cần phân tích
    risk_levels = [0.5, 1.0, 1.5, 2.0, 3.0]
    
    # Danh sách kết quả
    metrics_list = []
    
    # Chạy backtest cho từng mức rủi ro
    for risk in risk_levels:
        # Chạy với rủi ro thích ứng (adaptive)
        if run_backtest(symbol, interval, risk, True):
            copy_result_file(risk, True)
            metrics = extract_performance_metrics(risk, True)
            if metrics:
                metrics_list.append(metrics)
        
        # # Chạy với rủi ro cố định (non-adaptive)
        # if run_backtest(symbol, interval, risk, False):
        #     copy_result_file(risk, False)
        #     metrics = extract_performance_metrics(risk, False)
        #     if metrics:
        #         metrics_list.append(metrics)
    
    # Tạo báo cáo
    if metrics_list:
        report = generate_comparison_report(metrics_list)
        
        # Lưu báo cáo
        report_path = "risk_analysis/risk_level_comparison_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Đã lưu báo cáo tại: {report_path}")
        
        # Tạo biểu đồ
        generate_comparison_charts(metrics_list)
        
        return True
    else:
        logger.error("Không có dữ liệu để tạo báo cáo")
        return False

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Phân tích hiệu suất giao dịch ở nhiều mức rủi ro khác nhau')
    parser.add_argument('--symbol', type=str, default="BTCUSDT", help='Mã cặp giao dịch')
    parser.add_argument('--interval', type=str, default="1h", help='Khung thời gian')
    args = parser.parse_args()
    
    success = run_analysis(args.symbol, args.interval)
    
    if success:
        logger.info("Phân tích hiệu suất đa mức rủi ro thành công")
        sys.exit(0)
    else:
        logger.error("Phân tích hiệu suất đa mức rủi ro thất bại")
        sys.exit(1)

if __name__ == "__main__":
    main()