#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def main():
    try:
        # Kiểm tra file bot_status.json
        with open('bot_status.json', 'r') as f:
            bot_status = json.load(f)
            
        # Kiểm tra file account_config.json
        with open('account_config.json', 'r') as f:
            account_config = json.load(f)
        
        # Kiểm tra các file cấu hình liên quan
        config_files = {
            'Bot config': 'bot_config.json',
            'Algorithm config': 'configs/algorithm_config.json',
            'Advanced AI config': 'configs/advanced_ai_config.json'
        }
        
        configs = {}
        for name, file_path in config_files.items():
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    configs[name] = json.load(f)
            else:
                configs[name] = 'Not found'
        
        # In báo cáo tình trạng
        print("=" * 70)
        print("BÁO CÁO TÌNH TRẠNG BOT GIAO DỊCH")
        print("=" * 70)
        
        print("THÔNG TIN CHUNG:")
        print(f"Phiên bản: {bot_status.get('version', 'N/A')}")
        print(f"Trạng thái: {'Đang hoạt động' if bot_status.get('running', False) else 'Đã dừng'}")
        print(f"Loại tài khoản: {bot_status.get('account_type', 'N/A')}")
        print(f"Môi trường: {bot_status.get('mode', 'N/A')}")
        print(f"Chế độ chiến lược: {bot_status.get('strategy_mode', 'N/A')}")
        print(f"Thời gian bắt đầu: {bot_status.get('start_time', 'N/A')}")
        print(f"Cập nhật gần nhất: {bot_status.get('last_update', 'N/A')}")
        print(f"Hành động gần nhất: {bot_status.get('last_action', 'N/A')}")
        
        print("\nCHIẾN LƯỢC ĐANG HOẠT ĐỘNG:")
        active_strategies = bot_status.get('active_strategies', [])
        if active_strategies:
            for strategy in active_strategies:
                print(f"- {strategy}")
        else:
            print("Không có chiến lược nào đang hoạt động")
        
        print("\nCẤU HÌNH TÀI KHOẢN:")
        print(f"API Mode: {account_config.get('api_mode', 'N/A')}")
        print(f"Đòn bẩy: {account_config.get('leverage', 'N/A')}x")
        print(f"Rủi ro/Giao dịch: {account_config.get('risk_per_trade', 'N/A')}%")
        print(f"Loại tài khoản: {account_config.get('account_type', 'N/A')}")
        
        print("\nCẶP GIAO DỊCH:")
        for symbol in account_config.get('symbols', []):
            print(f"- {symbol}")
        
        print("\nKHUNG THỜI GIAN:")
        for timeframe in account_config.get('timeframes', []):
            print(f"- {timeframe}")
        
        if 'Advanced AI config' in configs and configs['Advanced AI config'] != 'Not found':
            advanced_ai = configs['Advanced AI config']
            print("\nCẤU HÌNH AI NÂNG CAO:")
            print(f"Epsilon: {advanced_ai.get('epsilon', 'N/A')}")
            print(f"Batch size: {advanced_ai.get('batch_size', 'N/A')}")
            print(f"Learning rate: {advanced_ai.get('learning_rate', 'N/A')}")
            print(f"Discount factor: {advanced_ai.get('discount_factor', 'N/A')}")
            print(f"Memory size: {advanced_ai.get('memory_size', 'N/A')}")

    except Exception as e:
        print(f"Lỗi khi đọc cấu hình: {e}")

if __name__ == '__main__':
    main()
