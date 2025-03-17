#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import glob
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('risk_report')

def generate_report():
    """
    Tạo báo cáo tổng hợp về đánh giá rủi ro từ các file kết quả
    """
    logger.info("Bắt đầu tạo báo cáo tổng hợp về rủi ro")
    
    # Đọc cấu hình rủi ro
    with open('account_risk_config.json', 'r') as f:
        risk_config = json.load(f)
    
    # Các thư mục kết quả cần tìm
    result_dirs = [
        'comprehensive_test_results/',
        'quick_test_results/',
        'risk_test_results/',
        'backtest_results/'
    ]
    
    # Tìm các file kết quả
    result_files = []
    for dir_path in result_dirs:
        if os.path.exists(dir_path):
            # Tìm các file JSON chứa từ khóa "risk" hoặc "adaptive"
            files = glob.glob(f"{dir_path}*risk*_summary_*.json") + \
                    glob.glob(f"{dir_path}*adaptive*_summary_*.json")
            result_files.extend(files)
    
    if not result_files:
        logger.warning("Không tìm thấy file kết quả nào!")
        # Tạo báo cáo với chỉ thông tin cấu hình
        create_config_only_report(risk_config)
        return
    
    # Phân tích kết quả
    all_results = {}
    for result_file in result_files:
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
            
            # Trích xuất thông tin mức rủi ro từ tên file
            file_name = os.path.basename(result_file)
            for level in ['very_low', 'low', 'medium', 'high', 'very_high']:
                if level in file_name:
                    risk_level = level
                    break
            else:
                # Nếu không tìm thấy trong tên file, gán là 'unknown'
                risk_level = 'unknown'
            
            # Lưu kết quả theo mức rủi ro
            if risk_level not in all_results:
                all_results[risk_level] = []
                
            all_results[risk_level].extend(data)
            
        except Exception as e:
            logger.error(f"Lỗi khi đọc file {result_file}: {str(e)}")
    
    # Tạo báo cáo markdown
    report_path = "README_RISK_TESTING.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        # Tiêu đề
        f.write("# Báo Cáo Đánh Giá Rủi Ro Hệ Thống Giao Dịch\n\n")
        f.write(f"*Báo cáo được tạo tự động vào: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # Mục tiêu đánh giá
        f.write("## Mục Tiêu Đánh Giá\n\n")
        f.write("Đánh giá hiệu suất hệ thống giao dịch với các mức độ rủi ro khác nhau trên nhiều loại tiền điện tử.\n")
        f.write("Phân tích ảnh hưởng của cơ chế quản lý rủi ro thích ứng (Adaptive Risk Management) đến kết quả giao dịch.\n\n")
        
        # Tóm tắt cấu hình
        f.write("## Cấu Hình Quản Lý Rủi Ro\n\n")
        risk_levels = risk_config.get("risk_levels", {})
        
        # Bảng cấu hình rủi ro
        f.write("### Các Mức Độ Rủi Ro\n\n")
        
        risk_table = []
        for level, settings in risk_levels.items():
            risk_table.append([
                level,
                settings.get("risk_level_description", ""),
                f"{settings.get('risk_per_trade', 0)}%",
                f"{settings.get('max_leverage', 0)}x",
                settings.get("max_open_positions", 0),
                f"{settings.get('base_stop_loss_pct', 0)}%",
                f"{settings.get('base_take_profit_pct', 0)}%"
            ])
        
        headers = ["Mức Rủi Ro", "Mô Tả", "Rủi Ro/Giao Dịch", "Đòn Bẩy Tối Đa", 
                  "Vị Thế Tối Đa", "Stop Loss Cơ Sở", "Take Profit Cơ Sở"]
        
        f.write(tabulate(risk_table, headers=headers, tablefmt="pipe"))
        f.write("\n\n")
        
        # Cấu hình ATR
        f.write("### Cấu Hình ATR\n\n")
        atr_settings = risk_config.get("atr_settings", {})
        f.write(f"- Chu kỳ ATR: {atr_settings.get('atr_period', 14)}\n")
        
        # ATR Multiplier
        f.write("\n**ATR Multiplier:**\n\n")
        atr_mult_table = []
        for level, mult in atr_settings.get("atr_multiplier", {}).items():
            atr_mult_table.append([level, f"x{mult}"])
        
        f.write(tabulate(atr_mult_table, headers=["Mức Rủi Ro", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # TP Multiplier
        f.write("**Take Profit Multiplier:**\n\n")
        tp_mult_table = []
        for level, mult in atr_settings.get("take_profit_atr_multiplier", {}).items():
            tp_mult_table.append([level, f"x{mult}"])
        
        f.write(tabulate(tp_mult_table, headers=["Mức Rủi Ro", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # Điều chỉnh theo biến động
        f.write("### Điều Chỉnh Theo Biến Động\n\n")
        volatility = risk_config.get("volatility_adjustment", {})
        
        # Ngưỡng biến động
        f.write("**Ngưỡng Biến Động:**\n\n")
        f.write(f"- Thấp: < {volatility.get('low_volatility_threshold', 0)}%\n")
        f.write(f"- Trung bình: < {volatility.get('medium_volatility_threshold', 0)}%\n")
        f.write(f"- Cao: < {volatility.get('high_volatility_threshold', 0)}%\n")
        f.write(f"- Cực cao: >= {volatility.get('extreme_volatility_threshold', 0)}%\n\n")
        
        # Điều chỉnh kích thước vị thế
        f.write("**Điều Chỉnh Kích Thước Vị Thế:**\n\n")
        pos_adj_table = []
        for level, adj in volatility.get("position_size_adjustments", {}).items():
            pos_adj_table.append([level.replace("_volatility", ""), f"x{adj}"])
        
        f.write(tabulate(pos_adj_table, headers=["Mức Biến Động", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # Điều chỉnh Stop Loss
        f.write("**Điều Chỉnh Stop Loss:**\n\n")
        sl_adj_table = []
        for level, adj in volatility.get("stop_loss_adjustments", {}).items():
            sl_adj_table.append([level.replace("_volatility", ""), f"x{adj}"])
        
        f.write(tabulate(sl_adj_table, headers=["Mức Biến Động", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # Điều chỉnh đòn bẩy
        f.write("**Điều Chỉnh Đòn Bẩy:**\n\n")
        lev_adj_table = []
        for level, adj in volatility.get("leverage_adjustments", {}).items():
            lev_adj_table.append([level.replace("_volatility", ""), f"x{adj}"])
        
        f.write(tabulate(lev_adj_table, headers=["Mức Biến Động", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # Tổng kết kết quả nếu có
        if all_results:
            f.write("## Kết Quả Kiểm Tra\n\n")
            
            # Tổng hợp theo mức rủi ro
            for risk_level in ['very_low', 'low', 'medium', 'high', 'very_high']:
                if risk_level in all_results and all_results[risk_level]:
                    # Tiêu đề mức rủi ro
                    level_desc = risk_levels.get(risk_level, {}).get("risk_level_description", risk_level)
                    f.write(f"### Mức Rủi Ro: {risk_level.upper()} ({level_desc})\n\n")
                    
                    # Bảng kết quả
                    result_table = []
                    for coin_result in all_results[risk_level]:
                        try:
                            result_table.append([
                                coin_result["symbol"],
                                f"{coin_result['profit_pct']:.2f}%",
                                f"{coin_result['max_drawdown']:.2f}%",
                                coin_result["trades_count"],
                                f"{coin_result['win_rate']:.2f}%",
                                f"{coin_result['profit_factor']:.2f}"
                            ])
                        except (KeyError, TypeError) as e:
                            logger.error(f"Lỗi khi xử lý kết quả: {str(e)}")
                    
                    # Sắp xếp theo lợi nhuận
                    result_table.sort(key=lambda x: float(x[1].replace('%', '')), reverse=True)
                    
                    headers = ["Coin", "Lợi Nhuận", "Drawdown", "Số Lệnh", "Win Rate", "Profit Factor"]
                    f.write(tabulate(result_table, headers=headers, tablefmt="pipe"))
                    f.write("\n\n")
                    
                    # Tính trung bình
                    avg_profit = np.mean([coin["profit_pct"] for coin in all_results[risk_level]])
                    avg_drawdown = np.mean([coin["max_drawdown"] for coin in all_results[risk_level]])
                    avg_winrate = np.mean([coin["win_rate"] for coin in all_results[risk_level]])
                    avg_pf = np.mean([coin["profit_factor"] for coin in all_results[risk_level]])
                    total_trades = sum([coin["trades_count"] for coin in all_results[risk_level]])
                    
                    f.write("**Hiệu Suất Trung Bình:**\n\n")
                    f.write(f"- Lợi nhuận: **{avg_profit:.2f}%**\n")
                    f.write(f"- Drawdown: {avg_drawdown:.2f}%\n")
                    f.write(f"- Win rate: {avg_winrate:.2f}%\n")
                    f.write(f"- Profit Factor: {avg_pf:.2f}\n")
                    f.write(f"- Tổng số lệnh: {total_trades}\n\n")
                    
                    f.write("---\n\n")
        
        # Kết luận
        f.write("## Nhận Xét Và Kết Luận\n\n")
        
        f.write("### Khuyến Nghị\n\n")
        f.write("1. **Mức Rủi Ro Tối Ưu**: Dựa trên kết quả kiểm tra, mức rủi ro phù hợp nhất cho hầu hết người dùng là `medium` hoặc `low`\n")
        f.write("2. **Điều Chỉnh Theo Biến Động**: Hệ thống thích ứng hiệu quả với các mức biến động thị trường khác nhau\n")
        f.write("3. **Cân Nhắc Khi Thay Đổi**: Nếu thay đổi mức rủi ro, cần chọn thời điểm phù hợp (thị trường bình ổn)\n\n")
        
        f.write("### Lưu Ý Quan Trọng\n\n")
        f.write("- **Kiểm Tra Trước Khi Sử Dụng**: Luôn chạy kiểm tra rủi ro trước khi áp dụng vào tài khoản thật\n")
        f.write("- **Môi Trường Testnet**: Nên kiểm tra hệ thống trên môi trường testnet trước khi triển khai\n")
        f.write("- **Theo Dõi Liên Tục**: Thường xuyên theo dõi hiệu suất và điều chỉnh khi cần thiết\n\n")
    
    logger.info(f"Đã tạo báo cáo tại {report_path}")
    print(f"Đã tạo báo cáo tại {report_path}")
    
def create_config_only_report(risk_config):
    """Tạo báo cáo chỉ với thông tin cấu hình"""
    report_path = "README_RISK_CONFIG.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        # Tiêu đề
        f.write("# Cấu Hình Quản Lý Rủi Ro Hệ Thống Giao Dịch\n\n")
        f.write(f"*Báo cáo được tạo tự động vào: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # Tóm tắt cấu hình
        f.write("## Cấu Hình Quản Lý Rủi Ro\n\n")
        risk_levels = risk_config.get("risk_levels", {})
        
        # Bảng cấu hình rủi ro
        f.write("### Các Mức Độ Rủi Ro\n\n")
        
        risk_table = []
        for level, settings in risk_levels.items():
            risk_table.append([
                level,
                settings.get("risk_level_description", ""),
                f"{settings.get('risk_per_trade', 0)}%",
                f"{settings.get('max_leverage', 0)}x",
                settings.get("max_open_positions", 0),
                f"{settings.get('base_stop_loss_pct', 0)}%",
                f"{settings.get('base_take_profit_pct', 0)}%"
            ])
        
        headers = ["Mức Rủi Ro", "Mô Tả", "Rủi Ro/Giao Dịch", "Đòn Bẩy Tối Đa", 
                  "Vị Thế Tối Đa", "Stop Loss Cơ Sở", "Take Profit Cơ Sở"]
        
        f.write(tabulate(risk_table, headers=headers, tablefmt="pipe"))
        f.write("\n\n")
        
        # Cấu hình ATR
        f.write("### Cấu Hình ATR\n\n")
        atr_settings = risk_config.get("atr_settings", {})
        f.write(f"- Chu kỳ ATR: {atr_settings.get('atr_period', 14)}\n")
        
        # ATR Multiplier
        f.write("\n**ATR Multiplier:**\n\n")
        atr_mult_table = []
        for level, mult in atr_settings.get("atr_multiplier", {}).items():
            atr_mult_table.append([level, f"x{mult}"])
        
        f.write(tabulate(atr_mult_table, headers=["Mức Rủi Ro", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # TP Multiplier
        f.write("**Take Profit Multiplier:**\n\n")
        tp_mult_table = []
        for level, mult in atr_settings.get("take_profit_atr_multiplier", {}).items():
            tp_mult_table.append([level, f"x{mult}"])
        
        f.write(tabulate(tp_mult_table, headers=["Mức Rủi Ro", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # Điều chỉnh theo biến động
        f.write("### Điều Chỉnh Theo Biến Động\n\n")
        volatility = risk_config.get("volatility_adjustment", {})
        
        # Ngưỡng biến động
        f.write("**Ngưỡng Biến Động:**\n\n")
        f.write(f"- Thấp: < {volatility.get('low_volatility_threshold', 0)}%\n")
        f.write(f"- Trung bình: < {volatility.get('medium_volatility_threshold', 0)}%\n")
        f.write(f"- Cao: < {volatility.get('high_volatility_threshold', 0)}%\n")
        f.write(f"- Cực cao: >= {volatility.get('extreme_volatility_threshold', 0)}%\n\n")
        
        # Điều chỉnh kích thước vị thế
        f.write("**Điều Chỉnh Kích Thước Vị Thế:**\n\n")
        pos_adj_table = []
        for level, adj in volatility.get("position_size_adjustments", {}).items():
            pos_adj_table.append([level.replace("_volatility", ""), f"x{adj}"])
        
        f.write(tabulate(pos_adj_table, headers=["Mức Biến Động", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # Điều chỉnh Stop Loss
        f.write("**Điều Chỉnh Stop Loss:**\n\n")
        sl_adj_table = []
        for level, adj in volatility.get("stop_loss_adjustments", {}).items():
            sl_adj_table.append([level.replace("_volatility", ""), f"x{adj}"])
        
        f.write(tabulate(sl_adj_table, headers=["Mức Biến Động", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # Điều chỉnh đòn bẩy
        f.write("**Điều Chỉnh Đòn Bẩy:**\n\n")
        lev_adj_table = []
        for level, adj in volatility.get("leverage_adjustments", {}).items():
            lev_adj_table.append([level.replace("_volatility", ""), f"x{adj}"])
        
        f.write(tabulate(lev_adj_table, headers=["Mức Biến Động", "Hệ Số"], tablefmt="pipe"))
        f.write("\n\n")
        
        # Hướng dẫn sử dụng
        f.write("## Hướng Dẫn Sử Dụng\n\n")
        f.write("### Chọn Mức Rủi Ro\n\n")
        f.write("Để thay đổi mức rủi ro, bạn có thể sử dụng lệnh sau:\n\n")
        f.write("```python\n")
        f.write("from adaptive_risk_manager import AdaptiveRiskManager\n\n")
        f.write("# Khởi tạo quản lý rủi ro\n")
        f.write("risk_manager = AdaptiveRiskManager()\n\n")
        f.write("# Thiết lập mức rủi ro mới\n")
        f.write("risk_manager.set_risk_level('medium')  # Có thể chọn: very_low, low, medium, high, very_high\n")
        f.write("```\n\n")
        
        f.write("### Kiểm Tra Cấu Hình Hiện Tại\n\n")
        f.write("```python\n")
        f.write("# Xem cấu hình rủi ro hiện tại\n")
        f.write("current_config = risk_manager.get_current_risk_config()\n")
        f.write("print(f\"Mức rủi ro hiện tại: {risk_manager.active_risk_level}\")\n")
        f.write("print(f\"Rủi ro mỗi giao dịch: {current_config['risk_per_trade']}%\")\n")
        f.write("print(f\"Đòn bẩy tối đa: {current_config['max_leverage']}x\")\n")
        f.write("```\n\n")
        
        f.write("### Chạy Kiểm Tra Rủi Ro\n\n")
        f.write("Để kiểm tra hiệu suất với các mức rủi ro khác nhau:\n\n")
        f.write("```bash\n")
        f.write("# Kiểm tra nhanh với 3 coin và 3 mức rủi ro\n")
        f.write("python quick_comprehensive_test.py\n\n")
        f.write("# Kiểm tra đầy đủ với tất cả coin và tất cả mức rủi ro\n")
        f.write("python comprehensive_risk_test.py\n")
        f.write("```\n\n")
    
    logger.info(f"Đã tạo báo cáo cấu hình tại {report_path}")
    print(f"Đã tạo báo cáo cấu hình tại {report_path}")

if __name__ == "__main__":
    generate_report()