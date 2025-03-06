#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os
from datetime import datetime

def load_json_file(file_path):
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi khi đọc file {file_path}: {str(e)}")
        return None

def main():
    print("===== THÔNG TIN CHIẾN LƯỢC GIAO DỊCH =====")
    print(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Kiểm tra file cấu hình bot
    bot_config = load_json_file('bot_config.json')
    if bot_config:
        print("\nCẤU HÌNH BOT:")
        print(f"Tên bot: {bot_config.get('bot_name', 'Không xác định')}")
        print(f"Phiên bản: {bot_config.get('version', 'Không xác định')}")
        
        if 'strategies' in bot_config:
            active_strategies = []
            for strategy_name, strategy_data in bot_config['strategies'].items():
                if strategy_data.get('enabled', False):
                    active_strategies.append(strategy_name)
            print(f"Chiến lược đang hoạt động: {', '.join(active_strategies) if active_strategies else 'Không có'}")
        
        if 'risk_management' in bot_config:
            risk = bot_config.get('risk_management', {})
            print(f"Quản lý rủi ro:")
            print(f"  - Rủi ro tối đa mỗi giao dịch: {risk.get('max_risk_per_trade', 'N/A')}%")
            print(f"  - Rủi ro tối đa tài khoản: {risk.get('max_risk_total', 'N/A')}%")
            print(f"  - Số vị thế tối đa: {risk.get('max_positions', 'N/A')}")
    else:
        print("Không tìm thấy file cấu hình bot_config.json")
    
    # Kiểm tra file tín hiệu
    signals_file = load_json_file('composite_recommendation.json')
    if signals_file:
        print("\nTÍN HIỆU GIAO DỊCH GẦN ĐÂY:")
        
        timestamp = datetime.fromtimestamp(signals_file.get('timestamp', 0))
        print(f"Thời gian tạo: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if 'recommendations' in signals_file:
            recommendations = signals_file['recommendations']
            for symbol, data in recommendations.items():
                signal = data.get('signal', 'NEUTRAL')
                score = data.get('score', 0)
                confidence = data.get('confidence', 0)
                
                # Hiển thị tín hiệu với màu sắc
                signal_colored = signal
                if signal == 'BUY':
                    signal_colored = "\033[32mBUY\033[0m"
                elif signal == 'SELL':
                    signal_colored = "\033[31mSELL\033[0m"
                elif signal == 'STRONG_BUY':
                    signal_colored = "\033[1;32mSTRONG BUY\033[0m"
                elif signal == 'STRONG_SELL':
                    signal_colored = "\033[1;31mSTRONG SELL\033[0m"
                
                print(f"{symbol}: {signal_colored} (Score: {score:.2f}, Confidence: {confidence:.2f})")
    else:
        print("\nKhông tìm thấy file tín hiệu composite_recommendation.json")
    
    # Kiểm tra file trạng thái thị trường
    market_file = load_json_file('market_analysis.json')
    if market_file:
        print("\nPHÂN TÍCH THỊ TRƯỜNG:")
        
        timestamp = datetime.fromtimestamp(market_file.get('timestamp', 0))
        print(f"Thời gian cập nhật: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if 'market_regime' in market_file:
            regime = market_file.get('market_regime', 'Không xác định')
            print(f"Chế độ thị trường: {regime}")
        
        if 'volatility' in market_file:
            volatility = market_file.get('volatility', 0)
            print(f"Biến động: {volatility:.2f}%")
        
        if 'trend_strength' in market_file:
            trend = market_file.get('trend_strength', 0)
            print(f"Độ mạnh xu hướng: {trend:.2f}")
        
        if 'summary' in market_file:
            print(f"Tóm tắt: {market_file.get('summary', 'Không có')}")
    else:
        print("\nKhông tìm thấy file phân tích thị trường market_analysis.json")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
