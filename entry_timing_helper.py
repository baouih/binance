#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Công cụ hỗ trợ xác định thời điểm vào lệnh tối ưu

Script này giúp xác định thời điểm vào lệnh tối ưu trong ngày hiện tại,
dựa trên kết quả phân tích của optimized_entry_strategy.py.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, time, timedelta
from typing import Dict, List

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('entry_timing.log')
    ]
)

logger = logging.getLogger('entry_timing_helper')

def load_entry_strategy(strategy_file: str = "optimized_entry_strategy.json") -> Dict:
    """
    Đọc chiến lược vào lệnh từ file

    Args:
        strategy_file (str): Đường dẫn đến file chiến lược vào lệnh

    Returns:
        Dict: Dữ liệu chiến lược vào lệnh
    """
    try:
        with open(strategy_file, 'r') as f:
            strategy = json.load(f)
        return strategy
    except Exception as e:
        logger.error(f"Không thể đọc file chiến lược vào lệnh: {e}")
        return None

def get_today_schedule(strategy: Dict) -> Dict:
    """
    Lấy lịch trình vào lệnh cho ngày hôm nay

    Args:
        strategy (Dict): Dữ liệu chiến lược vào lệnh

    Returns:
        Dict: Lịch trình vào lệnh cho ngày hôm nay
    """
    # Lấy ngày trong tuần
    weekday = datetime.now().weekday()  # 0 = Thứ 2, 6 = Chủ nhật
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_name = weekday_names[weekday]
    
    # Lấy lịch trình cho ngày hôm nay
    schedule = strategy.get("weekly_schedule", {}).get(today_name, {})
    
    return {
        "day": today_name,
        "win_rate": schedule.get("win_rate", 0),
        "entries": schedule.get("entries", [])
    }

def get_current_status(today_schedule: Dict) -> List[Dict]:
    """
    Xác định trạng thái hiện tại và thời điểm vào lệnh tiếp theo

    Args:
        today_schedule (Dict): Lịch trình vào lệnh cho ngày hôm nay

    Returns:
        List[Dict]: Danh sách các thời điểm vào lệnh còn lại trong ngày
    """
    # Lấy thời gian hiện tại
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    # Danh sách các thời điểm vào lệnh trong ngày
    entries = today_schedule.get("entries", [])
    
    # Lọc các thời điểm vào lệnh còn lại trong ngày
    upcoming_entries = []
    
    for entry in entries:
        start_hour = entry.get("start_hour", 0)
        start_minute = entry.get("start_minute", 0)
        end_hour = entry.get("end_hour", 0)
        end_minute = entry.get("end_minute", 0)
        
        # Kiểm tra xem thời điểm vào lệnh đã qua chưa
        if start_hour > current_hour or (start_hour == current_hour and start_minute > current_minute):
            # Thời điểm vào lệnh sắp tới
            minutes_until = (start_hour - current_hour) * 60 + (start_minute - current_minute)
            entry["status"] = "upcoming"
            entry["minutes_until"] = minutes_until
            upcoming_entries.append(entry)
        elif end_hour > current_hour or (end_hour == current_hour and end_minute > current_minute):
            # Thời điểm vào lệnh đang diễn ra
            minutes_remaining = (end_hour - current_hour) * 60 + (end_minute - current_minute)
            entry["status"] = "active"
            entry["minutes_remaining"] = minutes_remaining
            upcoming_entries.append(entry)
    
    # Sắp xếp theo thời gian còn lại
    upcoming_entries.sort(key=lambda x: x.get("start_hour", 0) * 60 + x.get("start_minute", 0))
    
    return upcoming_entries

def get_recommended_coins(entry: Dict) -> List[str]:
    """
    Lấy danh sách coin được khuyến nghị cho thời điểm vào lệnh

    Args:
        entry (Dict): Thông tin thời điểm vào lệnh

    Returns:
        List[str]: Danh sách coin được khuyến nghị
    """
    coins = entry.get("coins", [])
    return [coin.get("symbol", "") for coin in coins]

def format_time_until(minutes: int) -> str:
    """
    Định dạng thời gian còn lại

    Args:
        minutes (int): Số phút

    Returns:
        str: Chuỗi thời gian định dạng
    """
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        return f"{hours} giờ {mins} phút"
    else:
        return f"{mins} phút"

def print_entry_recommendations():
    """
    In ra khuyến nghị vào lệnh cho ngày hôm nay
    """
    # Đọc chiến lược vào lệnh
    strategy = load_entry_strategy()
    if not strategy:
        logger.error("Không thể đọc chiến lược vào lệnh")
        return
    
    # Lấy lịch trình cho ngày hôm nay
    today_schedule = get_today_schedule(strategy)
    
    # Lấy trạng thái hiện tại và thời điểm vào lệnh tiếp theo
    upcoming_entries = get_current_status(today_schedule)
    
    # In ra thông tin
    day_name = today_schedule["day"]
    win_rate = today_schedule["win_rate"]
    
    print("\n===== THỜI ĐIỂM VÀO LỆNH TỐI ƯU HÔM NAY =====")
    print(f"Ngày: {day_name} - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Tỷ lệ thắng của ngày: {win_rate:.1f}%")
    
    if not upcoming_entries:
        print("\nKhông còn thời điểm vào lệnh nào trong ngày hôm nay!")
        print("Hãy chuẩn bị cho ngày mai hoặc xem xét giao dịch ngoài kế hoạch với kích thước lệnh nhỏ hơn.")
        return
    
    # In ra thông tin cụ thể
    print(f"\nSố thời điểm vào lệnh còn lại: {len(upcoming_entries)}")
    
    for i, entry in enumerate(upcoming_entries, 1):
        start_time = entry["local_start_str"]
        end_time = entry["local_end_str"]
        event_name = entry["name"]
        coins = get_recommended_coins(entry)
        win_rate_bonus = entry["win_rate_bonus"]
        total_win_rate = win_rate + win_rate_bonus
        
        print(f"\n{i}. Thời điểm: {start_time}-{end_time} ({event_name})")
        print(f"   Tỷ lệ thắng: {total_win_rate:.1f}%")
        print(f"   Coins khuyến nghị: {', '.join(coins)}")
        
        if entry["status"] == "upcoming":
            print(f"   Thời gian còn lại: {format_time_until(entry['minutes_until'])}")
        else:  # active
            print(f"   Đang diễn ra! Còn lại: {format_time_until(entry['minutes_remaining'])}")
    
    # In ra khuyến nghị
    print("\n===== KHUYẾN NGHỊ CHO GIAO DỊCH HÔM NAY =====")
    if win_rate >= 55:
        print("- Đây là ngày có tỷ lệ thắng cao, nên tận dụng tối đa các cơ hội giao dịch.")
        print("- Có thể sử dụng đến 100% kích thước lệnh đề xuất.")
    elif win_rate >= 52:
        print("- Đây là ngày có tỷ lệ thắng khá, nên chọn lọc các cơ hội giao dịch tốt nhất.")
        print("- Nên giảm kích thước lệnh xuống còn 75-80% so với đề xuất.")
    elif win_rate >= 50:
        print("- Đây là ngày có tỷ lệ thắng trung bình, cần thận trọng khi vào lệnh.")
        print("- Nên giảm kích thước lệnh xuống còn 50% so với đề xuất.")
    else:
        print("- Đây là ngày có tỷ lệ thắng thấp, nên hạn chế giao dịch.")
        print("- Chỉ giao dịch nếu có tín hiệu rất rõ ràng và giảm kích thước lệnh xuống còn 30%.")
    
    print("\n===== NHẮC NHỞ QUAN TRỌNG =====")
    print("1. Luôn đặt Stop Loss và Take Profit ngay khi vào lệnh")
    print("2. Chỉ vào lệnh khi có xác nhận từ mẫu hình kỹ thuật")
    print("3. Theo dõi các tin tức quan trọng trước khi giao dịch")
    print("4. Không vượt quá số lệnh tối đa cho ngày hôm nay")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Công cụ hỗ trợ xác định thời điểm vào lệnh tối ưu')
    parser.add_argument('--strategy', type=str, default='optimized_entry_strategy.json', help='File chiến lược vào lệnh')
    args = parser.parse_args()
    
    # Đọc chiến lược vào lệnh
    if not os.path.exists(args.strategy):
        logger.error(f"Không tìm thấy file chiến lược vào lệnh: {args.strategy}")
        print(f"Không tìm thấy file chiến lược vào lệnh: {args.strategy}")
        print(f"Hãy chạy optimized_entry_strategy.py trước!")
        sys.exit(1)
    
    # In ra khuyến nghị vào lệnh
    print_entry_recommendations()

if __name__ == "__main__":
    main()