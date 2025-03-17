#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
from tabulate import tabulate

def print_risk_configs():
    """In ra thông tin chi tiết về các cấu hình rủi ro"""
    try:
        # Đọc file cấu hình rủi ro
        with open('account_risk_config.json', 'r') as f:
            config = json.load(f)
        
        # Lấy thông tin về các mức rủi ro
        risk_levels = config.get('risk_levels', {})
        
        # Tạo bảng so sánh
        comparison_data = []
        
        for level, settings in risk_levels.items():
            # Thêm vào dữ liệu so sánh
            comparison_data.append({
                'Risk Level': level,
                'Description': settings.get('risk_level_description', ''),
                'Risk Per Trade (%)': settings.get('risk_per_trade', 0),
                'Max Leverage': settings.get('max_leverage', 0),
                'Max Positions': settings.get('max_open_positions', 0),
                'Base Stop Loss (%)': settings.get('base_stop_loss_pct', 0),
                'Base Take Profit (%)': settings.get('base_take_profit_pct', 0),
                'Position Size (%)': settings.get('base_position_size_pct', 0)
            })
        
        # Sắp xếp theo mức rủi ro
        risk_order = ['very_low', 'low', 'medium', 'high', 'very_high']
        comparison_data.sort(key=lambda x: risk_order.index(x['Risk Level']) if x['Risk Level'] in risk_order else 999)
        
        # In bảng so sánh
        print("\n===== CẤU HÌNH QUẢN LÝ RỦI RO =====\n")
        print(tabulate(comparison_data, headers='keys', tablefmt='grid', floatfmt=".2f", showindex=False))
        
        # In thông tin ATR
        print("\n===== CẤU HÌNH ATR =====\n")
        atr_settings = config.get('atr_settings', {})
        print(f"Chu kỳ ATR: {atr_settings.get('atr_period', 14)}")
        
        # Bảng ATR Multiplier
        print("\nATR Multiplier theo mức rủi ro:")
        atr_mult = atr_settings.get('atr_multiplier', {})
        for level, mult in atr_mult.items():
            print(f"  - {level}: x{mult}")
            
        # Bảng Take Profit Multiplier
        print("\nTake Profit Multiplier theo mức rủi ro:")
        tp_mult = atr_settings.get('take_profit_atr_multiplier', {})
        for level, mult in tp_mult.items():
            print(f"  - {level}: x{mult}")
        
        # Stop Loss Min/Max
        print("\nStop Loss Min (%):")
        sl_min = atr_settings.get('min_atr_stop_loss_pct', {})
        for level, val in sl_min.items():
            print(f"  - {level}: {val}%")
            
        print("\nStop Loss Max (%):")
        sl_max = atr_settings.get('max_atr_stop_loss_pct', {})
        for level, val in sl_max.items():
            print(f"  - {level}: {val}%")
        
        # In thông tin điều chỉnh theo biến động
        print("\n===== ĐIỀU CHỈNH THEO BIẾN ĐỘNG (VOLATILITY ADJUSTMENTS) =====\n")
        
        # Ngưỡng biến động
        print("Ngưỡng phân loại biến động:")
        vol_adj = config.get('volatility_adjustment', {})
        print(f"  - Thấp: < {vol_adj.get('low_volatility_threshold', 0)}%")
        print(f"  - Trung bình: < {vol_adj.get('medium_volatility_threshold', 0)}%")
        print(f"  - Cao: < {vol_adj.get('high_volatility_threshold', 0)}%")
        print(f"  - Cực cao: >= {vol_adj.get('extreme_volatility_threshold', 0)}%")
        
        # Điều chỉnh kích thước vị thế
        print("\nĐiều chỉnh kích thước vị thế theo biến động:")
        pos_adj = vol_adj.get('position_size_adjustments', {})
        for vol_level, adjustment in pos_adj.items():
            print(f"  - {vol_level}: x{adjustment}")
            
        # Điều chỉnh stop loss
        print("\nĐiều chỉnh stop loss theo biến động:")
        sl_adj = vol_adj.get('stop_loss_adjustments', {})
        for vol_level, adjustment in sl_adj.items():
            print(f"  - {vol_level}: x{adjustment}")
            
        # Điều chỉnh đòn bẩy
        print("\nĐiều chỉnh đòn bẩy theo biến động:")
        lev_adj = vol_adj.get('leverage_adjustments', {})
        for vol_level, adjustment in lev_adj.items():
            print(f"  - {vol_level}: x{adjustment}")
        
        return True
        
    except Exception as e:
        print(f"Lỗi khi đọc cấu hình rủi ro: {str(e)}")
        return False

if __name__ == "__main__":
    print_risk_configs()