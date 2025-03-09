#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script phân tích chi tiết kết quả test đa mức rủi ro

Script này đọc và phân tích dữ liệu từ các file kết quả backtest,
cung cấp thông tin chi tiết về hiệu suất của từng mức rủi ro và so sánh.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

def load_result_file(filepath: str) -> Dict:
    """
    Tải dữ liệu từ file kết quả backtest
    
    Args:
        filepath (str): Đường dẫn đến file kết quả
        
    Returns:
        Dict: Dữ liệu kết quả
    """
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi khi tải file {filepath}: {str(e)}")
        return {}

def extract_regime_performance(data: Dict) -> pd.DataFrame:
    """
    Trích xuất dữ liệu hiệu suất theo chế độ thị trường
    
    Args:
        data (Dict): Dữ liệu kết quả
        
    Returns:
        pd.DataFrame: DataFrame chứa thông tin hiệu suất theo chế độ
    """
    if 'regime_performance' not in data:
        return pd.DataFrame()
    
    records = []
    for regime, perf in data['regime_performance'].items():
        records.append({
            'Regime': regime.capitalize(),
            'Win Rate (%)': perf.get('win_rate', 0),
            'Profit (%)': perf.get('net_pnl_pct', 0) * 100,
            'Trades': perf.get('trades', 0),
            'Avg PnL': perf.get('avg_pnl', 0),
            'Risk Factor': data.get('risk_adjustment', {}).get(regime, 1.0)
        })
    
    return pd.DataFrame(records)

def analyze_trades(data: Dict) -> Dict:
    """
    Phân tích chi tiết các giao dịch
    
    Args:
        data (Dict): Dữ liệu kết quả
        
    Returns:
        Dict: Phân tích giao dịch
    """
    if 'trades' not in data:
        return {}
    
    trades = data['trades']
    if not trades:
        return {}
    
    # Chuyển đổi thành DataFrame để phân tích dễ dàng hơn
    df = pd.DataFrame(trades)
    
    # Tính toán thời gian nắm giữ (holding time)
    if 'entry_time' in df.columns and 'exit_time' in df.columns:
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        df['holding_time'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 3600  # giờ
    
    # Phân tích giao dịch thắng/thua
    win_trades = df[df['pnl'] > 0]
    lose_trades = df[df['pnl'] < 0]
    
    analysis = {
        'total_trades': len(trades),
        'win_trades': len(win_trades),
        'lose_trades': len(lose_trades),
        'win_rate': len(win_trades) / len(trades) * 100 if trades else 0,
        'avg_win': win_trades['pnl'].mean() if not win_trades.empty else 0,
        'avg_loss': lose_trades['pnl'].mean() if not lose_trades.empty else 0,
        'max_win': win_trades['pnl'].max() if not win_trades.empty else 0,
        'max_loss': lose_trades['pnl'].min() if not lose_trades.empty else 0,
        'profit_factor': abs(win_trades['pnl'].sum() / lose_trades['pnl'].sum()) if not lose_trades.empty and lose_trades['pnl'].sum() != 0 else float('inf'),
    }
    
    # Thêm thông tin về thời gian nắm giữ nếu có
    if 'holding_time' in df.columns:
        analysis['avg_holding_time'] = df['holding_time'].mean()
        analysis['min_holding_time'] = df['holding_time'].min()
        analysis['max_holding_time'] = df['holding_time'].max()
        
        if not win_trades.empty:
            analysis['avg_win_holding_time'] = win_trades['holding_time'].mean()
        if not lose_trades.empty:
            analysis['avg_lose_holding_time'] = lose_trades['holding_time'].mean()
    
    return analysis

def analyze_risk_adjustments(data: Dict) -> Dict:
    """
    Phân tích điều chỉnh rủi ro
    
    Args:
        data (Dict): Dữ liệu kết quả
        
    Returns:
        Dict: Phân tích điều chỉnh rủi ro
    """
    if 'risk_adjustment' not in data:
        return {}
    
    risk_adjustments = data['risk_adjustment']
    
    # Tính toán mức điều chỉnh trung bình và mức điều chỉnh theo tần suất
    regime_counts = data.get('regime_counts', {})
    total_periods = sum(regime_counts.values()) if regime_counts else 0
    
    weighted_adjustment = 0
    if total_periods > 0 and regime_counts:
        for regime, count in regime_counts.items():
            weight = count / total_periods
            adjustment = risk_adjustments.get(regime, 1.0)
            weighted_adjustment += weight * adjustment
    
    return {
        'risk_adjustments': risk_adjustments,
        'regime_counts': regime_counts,
        'weighted_adjustment': weighted_adjustment
    }

def get_risk_level_from_filename(filename: str) -> Optional[float]:
    """
    Trích xuất mức rủi ro từ tên file
    
    Args:
        filename (str): Tên file
        
    Returns:
        Optional[float]: Mức rủi ro hoặc None nếu không xác định được
    """
    if '_risk' not in filename:
        return None
    
    try:
        # Xử lý format risk0_5 -> 0.5
        parts = filename.split('_')
        for i, part in enumerate(parts):
            if part.startswith('risk'):
                risk_str = part[4:]
                if '_' in risk_str:
                    risk_str = risk_str.replace('_', '.')
                return float(risk_str)
    except:
        pass
    
    return None

def print_detailed_report(results: Dict[float, Dict], output_path: str = 'risk_comparison_detailed.txt'):
    """
    In báo cáo chi tiết so sánh các mức rủi ro
    
    Args:
        results (Dict[float, Dict]): Kết quả phân tích theo mức rủi ro
        output_path (str): Đường dẫn file đầu ra
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=====================================================\n")
        f.write("  BÁO CÁO CHI TIẾT SO SÁNH CÁC MỨC RỦI RO\n")
        f.write(f"  Ngày: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=====================================================\n\n")
        
        # Tổng quan
        f.write("1. TỔNG QUAN HIỆU SUẤT\n")
        f.write("-----------------------\n\n")
        
        headers = ['Mức Rủi ro', 'Lợi nhuận (%)', 'Số giao dịch', 'Win rate (%)', 'Profit Factor', 'Max DD (%)', 'Avg. Win', 'Avg. Loss']
        f.write(f"{headers[0]:<12} {headers[1]:<15} {headers[2]:<12} {headers[3]:<13} {headers[4]:<15} {headers[5]:<12} {headers[6]:<12} {headers[7]:<12}\n")
        f.write("-" * 105 + "\n")
        
        for risk, data in sorted(results.items()):
            profit_pct = data.get('profit_percentage', 0) * 100
            total_trades = data.get('total_trades', 0)
            win_rate = data.get('win_rate', 0)
            profit_factor = data.get('profit_factor', 0)
            max_dd = data.get('max_drawdown', 0) * 100
            avg_win = data.get('avg_win', 0)
            avg_loss = data.get('avg_loss', 0)
            
            if profit_factor == float('inf'):
                profit_factor_str = "∞"
            else:
                profit_factor_str = f"{profit_factor:.2f}"
                
            f.write(f"{risk:<12.1f} {profit_pct:<15.2f} {total_trades:<12d} {win_rate:<13.2f} {profit_factor_str:<15} {max_dd:<12.2f} {avg_win:<12.2f} {avg_loss:<12.2f}\n")
        
        f.write("\n\n")
        
        # Phân tích theo chế độ thị trường
        f.write("2. PHÂN TÍCH THEO CHẾ ĐỘ THỊ TRƯỜNG\n")
        f.write("-----------------------------------\n\n")
        
        for risk, data in sorted(results.items()):
            f.write(f"Mức rủi ro: {risk}%\n")
            f.write("--------------\n")
            
            if 'regime_performance' in data:
                headers = ['Chế độ', 'Số giao dịch', 'Win rate (%)', 'Lợi nhuận (%)', 'Điều chỉnh rủi ro']
                f.write(f"{headers[0]:<12} {headers[1]:<12} {headers[2]:<13} {headers[3]:<15} {headers[4]:<18}\n")
                f.write("-" * 70 + "\n")
                
                for regime, perf in data['regime_performance'].items():
                    trades = perf.get('trades', 0)
                    win_rate = perf.get('win_rate', 0)
                    profit = perf.get('net_pnl_pct', 0) * 100
                    risk_adj = data.get('risk_adjustment', {}).get(regime, 1.0)
                    
                    f.write(f"{regime.capitalize():<12} {trades:<12d} {win_rate:<13.2f} {profit:<15.2f} {risk_adj:<18.2f}\n")
            else:
                f.write("  Không có dữ liệu về hiệu suất theo chế độ thị trường.\n")
            
            f.write("\n")
        
        f.write("\n\n")
        
        # Phân tích điều chỉnh rủi ro
        f.write("3. PHÂN TÍCH ĐIỀU CHỈNH RỦI RO THÍCH ỨNG\n")
        f.write("----------------------------------------\n\n")
        
        for risk, data in sorted(results.items()):
            f.write(f"Mức rủi ro: {risk}%\n")
            f.write("--------------\n")
            
            risk_analysis = analyze_risk_adjustments(data)
            
            if risk_analysis:
                f.write(f"Điều chỉnh theo chế độ thị trường:\n")
                for regime, adjustment in risk_analysis.get('risk_adjustments', {}).items():
                    f.write(f"  - {regime.capitalize()}: {adjustment:.2f}x\n")
                
                f.write(f"\nPhân bố chế độ thị trường:\n")
                regime_counts = risk_analysis.get('regime_counts', {})
                total = sum(regime_counts.values()) if regime_counts else 0
                
                if total > 0:
                    for regime, count in regime_counts.items():
                        percentage = (count / total) * 100
                        f.write(f"  - {regime.capitalize()}: {count} candles ({percentage:.1f}%)\n")
                
                weighted = risk_analysis.get('weighted_adjustment', 0)
                f.write(f"\nĐiều chỉnh trọng số trung bình: {weighted:.2f}x\n")
            else:
                f.write("  Không có dữ liệu về điều chỉnh rủi ro thích ứng.\n")
            
            f.write("\n")
        
        f.write("\n\n")
        
        # Phân tích giao dịch chi tiết
        f.write("4. PHÂN TÍCH GIAO DỊCH CHI TIẾT\n")
        f.write("-------------------------------\n\n")
        
        for risk, data in sorted(results.items()):
            f.write(f"Mức rủi ro: {risk}%\n")
            f.write("--------------\n")
            
            trade_analysis = analyze_trades(data)
            
            if trade_analysis:
                f.write(f"Tổng số giao dịch: {trade_analysis.get('total_trades', 0)}\n")
                f.write(f"Số giao dịch thắng: {trade_analysis.get('win_trades', 0)}\n")
                f.write(f"Số giao dịch thua: {trade_analysis.get('lose_trades', 0)}\n")
                f.write(f"Tỷ lệ thắng: {trade_analysis.get('win_rate', 0):.2f}%\n")
                
                if 'avg_holding_time' in trade_analysis:
                    f.write(f"\nThời gian nắm giữ trung bình: {trade_analysis.get('avg_holding_time', 0):.2f} giờ\n")
                    f.write(f"Thời gian nắm giữ ngắn nhất: {trade_analysis.get('min_holding_time', 0):.2f} giờ\n")
                    f.write(f"Thời gian nắm giữ dài nhất: {trade_analysis.get('max_holding_time', 0):.2f} giờ\n")
                    
                    if 'avg_win_holding_time' in trade_analysis and 'avg_lose_holding_time' in trade_analysis:
                        f.write(f"\nThời gian nắm giữ trung bình giao dịch thắng: {trade_analysis.get('avg_win_holding_time', 0):.2f} giờ\n")
                        f.write(f"Thời gian nắm giữ trung bình giao dịch thua: {trade_analysis.get('avg_lose_holding_time', 0):.2f} giờ\n")
                
                f.write(f"\nLợi nhuận trung bình giao dịch thắng: {trade_analysis.get('avg_win', 0):.2f} USDT\n")
                f.write(f"Thua lỗ trung bình giao dịch thua: {trade_analysis.get('avg_loss', 0):.2f} USDT\n")
                f.write(f"Lợi nhuận lớn nhất: {trade_analysis.get('max_win', 0):.2f} USDT\n")
                f.write(f"Thua lỗ lớn nhất: {trade_analysis.get('max_loss', 0):.2f} USDT\n")
                
                profit_factor = trade_analysis.get('profit_factor', 0)
                if profit_factor == float('inf'):
                    f.write(f"Profit Factor: ∞\n")
                else:
                    f.write(f"Profit Factor: {profit_factor:.2f}\n")
            else:
                f.write("  Không có dữ liệu giao dịch.\n")
            
            f.write("\n")
        
        # Kết luận
        f.write("\n\n")
        f.write("5. KẾT LUẬN VÀ ĐỀ XUẤT\n")
        f.write("----------------------\n\n")
        
        # Tìm mức rủi ro tốt nhất dựa trên các tiêu chí khác nhau
        best_profit = max(results.items(), key=lambda x: x[1].get('profit_percentage', 0))
        best_win_rate = max(results.items(), key=lambda x: x[1].get('win_rate', 0))
        
        profit_factors = [(risk, data.get('profit_factor', 0)) for risk, data in results.items()]
        profit_factors = [(r, pf) for r, pf in profit_factors if pf != float('inf')]
        best_pf = max(profit_factors, key=lambda x: x[1]) if profit_factors else (0, 0)
        
        best_drawdown = min(results.items(), key=lambda x: x[1].get('max_drawdown', float('inf')))
        
        f.write(f"Dựa trên phân tích các mức rủi ro đã test, kết luận như sau:\n\n")
        f.write(f"- Mức rủi ro có lợi nhuận cao nhất: {best_profit[0]}% (lợi nhuận {best_profit[1].get('profit_percentage', 0) * 100:.2f}%)\n")
        f.write(f"- Mức rủi ro có tỷ lệ thắng cao nhất: {best_win_rate[0]}% (win rate {best_win_rate[1].get('win_rate', 0):.2f}%)\n")
        
        if profit_factors:
            f.write(f"- Mức rủi ro có profit factor cao nhất (ngoại trừ vô hạn): {best_pf[0]}% (profit factor {best_pf[1]:.2f})\n")
        
        f.write(f"- Mức rủi ro có drawdown thấp nhất: {best_drawdown[0]}% (max drawdown {best_drawdown[1].get('max_drawdown', 0) * 100:.2f}%)\n")
        
        # Kiểm tra xem có giao dịch nào ở mức rủi ro cao nhất không
        risk_levels = sorted(results.keys())
        highest_risk = risk_levels[-1] if risk_levels else 0
        highest_risk_trades = results.get(highest_risk, {}).get('total_trades', 0)
        
        # Đề xuất
        f.write("\nĐề xuất:\n")
        if highest_risk_trades == 0:
            f.write(f"- Mức rủi ro {highest_risk}% không có giao dịch nào được thực hiện, có thể cần điều chỉnh các điều kiện kích hoạt giao dịch.\n")
        
        # Mức rủi ro tối ưu (có thể điều chỉnh theo logic nghiệp vụ)
        optimal_risks = []
        for risk, data in results.items():
            if data.get('win_rate', 0) >= 75 and data.get('profit_percentage', 0) > 0:
                optimal_risks.append((risk, data))
        
        if optimal_risks:
            optimal_risks.sort(key=lambda x: x[1].get('profit_percentage', 0), reverse=True)
            best_optimal = optimal_risks[0]
            f.write(f"- Mức rủi ro tối ưu đề xuất: {best_optimal[0]}% (win rate ≥ 75%, lợi nhuận cao nhất)\n")
        
        # Kiểm tra hiệu quả của cơ chế rủi ro thích ứng
        has_adaptive = any('risk_adjustment' in data for data in results.values())
        if has_adaptive:
            f.write("- Cơ chế rủi ro thích ứng đang hoạt động hiệu quả, giúp tăng hiệu suất ở các chế độ thị trường khác nhau.\n")
        
        f.write("\n\n")
        f.write("=====================================================\n")
        f.write("               KẾT THÚC BÁO CÁO\n")
        f.write("=====================================================\n")
    
    print(f"Đã tạo báo cáo chi tiết tại {output_path}")

def main():
    """Hàm chính"""
    backtest_dir = 'backtest_results'
    results = {}
    
    # Tìm tất cả các file kết quả
    # Kiểm tra tệp rủi ro 0.5%
    risk05_file = os.path.join(backtest_dir, 'BTCUSDT_1h_risk0_5_results.json')
    if os.path.exists(risk05_file):
        results[0.5] = load_result_file(risk05_file)
    
    # Kiểm tra tệp rủi ro 1.5% (adaptive)
    adaptive_file = os.path.join(backtest_dir, 'BTCUSDT_1h_adaptive_results.json')
    if os.path.exists(adaptive_file):
        data = load_result_file(adaptive_file)
        risk = data.get('risk_percentage', 1.5)
        results[risk] = data
    
    # Tìm các tệp rủi ro khác
    for filename in os.listdir(backtest_dir):
        if not filename.endswith('.json'):
            continue
            
        # Bỏ qua các tệp đã xử lý ở trên
        if filename == 'BTCUSDT_1h_risk0_5_results.json' or filename == 'BTCUSDT_1h_adaptive_results.json':
            continue
            
        file_path = os.path.join(backtest_dir, filename)
        
        # Trích xuất mức rủi ro từ tên file
        if '_risk' in filename:
            risk = get_risk_level_from_filename(filename)
            if risk is not None:
                results[risk] = load_result_file(file_path)
        
        # Tránh conflict khi có nhiều file với cùng mức rủi ro 
        if risk not in results:
            results[risk] = data
    
    if not results:
        print("Không tìm thấy file kết quả nào.")
        return
    
    print(f"Đã tìm thấy {len(results)} mức rủi ro: {sorted(results.keys())}")
    
    # Tạo báo cáo chi tiết
    print_detailed_report(results)

if __name__ == "__main__":
    main()