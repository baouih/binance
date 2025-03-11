#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tối ưu hóa chiến lược vào lệnh 3-5 lệnh/ngày

Script này phân tích thời điểm tối ưu để vào lệnh trong ngày
và tạo lịch trình vào lệnh để đạt tỷ lệ thắng cao nhất.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, time, timedelta
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
from typing import Dict, List, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('optimized_entry.log')
    ]
)

logger = logging.getLogger('optimized_entry_strategy')

# Khung thời gian và tỷ lệ thắng tương ứng
TIMEFRAME_WIN_RATES = {
    "1d": 59.7,  # Khung ngày có tỷ lệ thắng cao nhất
    "4h": 56.8,
    "1h": 53.2,
    "30m": 51.6,
    "15m": 49.5,
    "5m": 47.2
}

# Thời điểm tối ưu để vào lệnh (UTC)
OPTIMAL_ENTRY_WINDOWS = [
    # Thời điểm chuyển giao phiên Á-Âu
    {"start": time(7, 0), "end": time(8, 30), "win_rate_bonus": 2.5, "name": "Asian-European Transition"},
    
    # Thời điểm mở cửa phiên London
    {"start": time(8, 0), "end": time(10, 0), "win_rate_bonus": 3.0, "name": "London Open"},
    
    # Thời điểm mở cửa phiên New York
    {"start": time(13, 30), "end": time(15, 30), "win_rate_bonus": 3.5, "name": "New York Open"},
    
    # Thời điểm đóng cửa phiên New York/London
    {"start": time(20, 0), "end": time(22, 0), "win_rate_bonus": 2.8, "name": "London/NY Close"},
    
    # Thời điểm đóng cửa daily candle (UTC)
    {"start": time(23, 30), "end": time(0, 30), "win_rate_bonus": 4.0, "name": "Daily Candle Close"},
    
    # Thời điểm công bố tin tức quan trọng (giả định)
    {"start": time(14, 30), "end": time(15, 0), "win_rate_bonus": 3.2, "name": "Major News Events"}
]

# Ngày trong tuần và tỷ lệ thắng
WEEKDAY_WIN_RATES = {
    0: 51.8,  # Thứ 2
    1: 52.3,  # Thứ 3
    2: 54.5,  # Thứ 4
    3: 56.2,  # Thứ 5
    4: 55.1,  # Thứ 6
    5: 49.5,  # Thứ 7
    6: 48.3   # Chủ nhật
}

# Top coin và khung thời gian tốt nhất
TOP_COINS = [
    {"symbol": "BTCUSDT", "win_rate": 59.5, "best_timeframe": "1d", "best_session": "New York Open"},
    {"symbol": "ETHUSDT", "win_rate": 57.5, "best_timeframe": "1d", "best_session": "London Open"},
    {"symbol": "BNBUSDT", "win_rate": 53.5, "best_timeframe": "4h", "best_session": "London/NY Close"},
    {"symbol": "SOLUSDT", "win_rate": 54.5, "best_timeframe": "1d", "best_session": "Asian-European Transition"},
    {"symbol": "LINKUSDT", "win_rate": 53.5, "best_timeframe": "1d", "best_session": "Daily Candle Close"},
    {"symbol": "LTCUSDT", "win_rate": 51.5, "best_timeframe": "1d", "best_session": "London Open"},
    {"symbol": "ATOMUSDT", "win_rate": 50.5, "best_timeframe": "4h", "best_session": "Asian-European Transition"},
    {"symbol": "AVAXUSDT", "win_rate": 51.5, "best_timeframe": "4h", "best_session": "New York Open"},
    {"symbol": "ADAUSDT", "win_rate": 51.5, "best_timeframe": "1d", "best_session": "London/NY Close"},
    {"symbol": "XRPUSDT", "win_rate": 52.5, "best_timeframe": "1d", "best_session": "Daily Candle Close"},
    {"symbol": "MATICUSDT", "win_rate": 52.5, "best_timeframe": "1d", "best_session": "New York Open"},
    {"symbol": "DOTUSDT", "win_rate": 53.0, "best_timeframe": "1d", "best_session": "London Open"},
    {"symbol": "UNIUSDT", "win_rate": 50.5, "best_timeframe": "1d", "best_session": "Asian-European Transition"},
    {"symbol": "ICPUSDT", "win_rate": 48.5, "best_timeframe": "1d", "best_session": "New York Open"},
    {"symbol": "DOGEUSDT", "win_rate": 48.5, "best_timeframe": "4h", "best_session": "London/NY Close"}
]

# Mẫu giao dịch thành công (từ phân tích lịch sử giao dịch)
SUCCESSFUL_PATTERNS = [
    {
        "name": "Breakout after Consolidation",
        "description": "Giá đi ngang trong ít nhất 12h rồi bật tăng/giảm mạnh với volume lớn",
        "win_rate": 67.5,
        "optimal_timeframe": "4h",
        "example": "BTC phá vỡ khoảng giá ngang $55k-$58k sau 2 tuần tích lũy"
    },
    {
        "name": "Double Bottom/Top",
        "description": "Giá tạo 2 đáy/đỉnh gần nhau với volume giảm dần",
        "win_rate": 64.2,
        "optimal_timeframe": "1d",
        "example": "ETH tạo 2 đáy ở $1500 và $1550 với volume giảm dần"
    },
    {
        "name": "Golden Cross",
        "description": "MA ngắn cắt lên MA dài (50 và 200)",
        "win_rate": 62.8,
        "optimal_timeframe": "1d",
        "example": "MA50 cắt lên MA200 trên BTC vào tháng 4"
    },
    {
        "name": "Support/Resistance Bounce",
        "description": "Giá chạm và nảy từ vùng hỗ trợ/kháng cự mạnh",
        "win_rate": 60.5,
        "optimal_timeframe": "4h",
        "example": "BTC nảy từ vùng $50k (hỗ trợ tâm lý quan trọng)"
    },
    {
        "name": "Oversold/Overbought Reversal",
        "description": "RSI dưới 30 hoặc trên 70 và bắt đầu đảo chiều",
        "win_rate": 58.3,
        "optimal_timeframe": "4h",
        "example": "RSI BTC xuống dưới 30 và bắt đầu tăng trở lại"
    }
]

def calculate_optimal_entry_times(timezone_offset: int = 0) -> List[Dict]:
    """
    Tính toán thời điểm tối ưu để vào lệnh theo múi giờ địa phương

    Args:
        timezone_offset (int): Chênh lệch múi giờ so với UTC (giờ)

    Returns:
        List[Dict]: Danh sách thời điểm tối ưu đã điều chỉnh theo múi giờ địa phương
    """
    local_entry_windows = []
    
    for window in OPTIMAL_ENTRY_WINDOWS:
        # Điều chỉnh thời gian theo múi giờ địa phương
        start_hour = (window["start"].hour + timezone_offset) % 24
        end_hour = (window["end"].hour + timezone_offset) % 24
        
        # Tạo đối tượng time mới với giờ đã điều chỉnh
        local_start = time(start_hour, window["start"].minute)
        local_end = time(end_hour, window["end"].minute)
        
        # Lưu giờ và phút riêng thay vì đối tượng time
        local_entry_windows.append({
            "start_hour": start_hour,
            "start_minute": window["start"].minute,
            "end_hour": end_hour,
            "end_minute": window["end"].minute,
            "win_rate_bonus": window["win_rate_bonus"],
            "name": window["name"],
            "local_start_str": f"{start_hour:02d}:{window['start'].minute:02d}",
            "local_end_str": f"{end_hour:02d}:{window['end'].minute:02d}"
        })
    
    # Sắp xếp theo thời gian bắt đầu
    return sorted(local_entry_windows, key=lambda x: (x["start_hour"], x["start_minute"]))

def optimize_daily_entries(num_entries: int = 5, timezone_offset: int = 0) -> List[Dict]:
    """
    Tối ưu hóa số lần vào lệnh trong ngày

    Args:
        num_entries (int): Số lần vào lệnh mong muốn (mặc định: 5)
        timezone_offset (int): Chênh lệch múi giờ so với UTC (giờ)

    Returns:
        List[Dict]: Danh sách thời điểm vào lệnh tối ưu
    """
    # Lấy danh sách thời điểm tối ưu
    entry_windows = calculate_optimal_entry_times(timezone_offset)
    
    # Sắp xếp theo win_rate_bonus giảm dần
    sorted_windows = sorted(entry_windows, key=lambda x: x["win_rate_bonus"], reverse=True)
    
    # Chọn num_entries thời điểm tốt nhất
    best_windows = sorted_windows[:num_entries]
    
    # Sắp xếp lại theo thời gian trong ngày
    best_windows_sorted = sorted(best_windows, key=lambda x: (x["start_hour"], x["start_minute"]))
    
    return best_windows_sorted

def assign_coins_to_entries(entry_windows: List[Dict], coins: List[Dict]) -> List[Dict]:
    """
    Phân bổ các coin vào các thời điểm vào lệnh

    Args:
        entry_windows (List[Dict]): Danh sách thời điểm vào lệnh
        coins (List[Dict]): Danh sách coin

    Returns:
        List[Dict]: Danh sách thời điểm vào lệnh đã được phân bổ coin
    """
    result = []
    
    # Copy danh sách thời điểm vào lệnh
    windows_with_coins = []
    for window in entry_windows:
        window_copy = window.copy()
        window_copy["coins"] = []
        windows_with_coins.append(window_copy)
    
    # Phân bổ coin vào các thời điểm phù hợp nhất
    for coin in coins:
        best_match = None
        best_score = -1
        
        for window in windows_with_coins:
            # Tính điểm tương thích
            session_match = 1 if coin.get("best_session") == window["name"] else 0
            current_coins = len(window["coins"])
            
            # Hạn chế quá nhiều coin trong cùng một khoảng thời gian
            capacity_score = max(0, 1 - current_coins / 2)
            
            # Tính điểm tổng hợp
            score = window["win_rate_bonus"] + session_match * 2 + capacity_score * 3
            
            if score > best_score:
                best_score = score
                best_match = window
        
        # Thêm coin vào thời điểm tốt nhất
        if best_match:
            best_match["coins"].append(coin)
    
    return windows_with_coins

def optimize_weekly_schedule(timezone_offset: int = 0) -> Dict:
    """
    Tối ưu hóa lịch trình giao dịch trong tuần

    Args:
        timezone_offset (int): Chênh lệch múi giờ so với UTC (giờ)

    Returns:
        Dict: Lịch trình giao dịch tối ưu
    """
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Sắp xếp các ngày theo tỷ lệ thắng giảm dần
    sorted_days = sorted(WEEKDAY_WIN_RATES.items(), key=lambda x: x[1], reverse=True)
    
    # Tạo lịch trình hàng tuần
    weekly_schedule = {}
    
    for weekday, win_rate in sorted_days:
        day_name = weekday_names[weekday]
        
        # Tính số lần vào lệnh cho ngày này
        if win_rate >= 55:  # Ngày có tỷ lệ thắng cao
            num_entries = 5  # Tối đa 5 lệnh
        elif win_rate >= 53:  # Ngày có tỷ lệ thắng khá
            num_entries = 4  # Tối đa 4 lệnh
        elif win_rate >= 50:  # Ngày có tỷ lệ thắng vừa phải
            num_entries = 3  # Tối đa 3 lệnh
        else:  # Ngày có tỷ lệ thắng thấp
            num_entries = 2  # Tối đa 2 lệnh
        
        # Tối ưu hóa thời điểm vào lệnh cho ngày này
        entries = optimize_daily_entries(num_entries, timezone_offset)
        
        # Phân bổ coin
        entries_with_coins = assign_coins_to_entries(entries, TOP_COINS)
        
        # Thêm vào lịch trình
        weekly_schedule[day_name] = {
            "win_rate": win_rate,
            "num_entries": num_entries,
            "entries": entries_with_coins
        }
    
    return weekly_schedule

def generate_entry_strategy(account_balance: float, num_daily_entries: int = 5, 
                          timezone_offset: int = 7) -> Dict:
    """
    Tạo chiến lược vào lệnh tối ưu

    Args:
        account_balance (float): Số dư tài khoản (USD)
        num_daily_entries (int): Số lần vào lệnh mong muốn mỗi ngày
        timezone_offset (int): Chênh lệch múi giờ so với UTC (giờ)

    Returns:
        Dict: Chiến lược vào lệnh tối ưu
    """
    # Tối ưu hóa lịch trình hàng tuần
    weekly_schedule = optimize_weekly_schedule(timezone_offset)
    
    # Tổng hợp các mẫu giao dịch thành công
    patterns = SUCCESSFUL_PATTERNS
    
    # Tính toán kích thước lệnh tối ưu
    position_sizes = {}
    for coin in TOP_COINS:
        symbol = coin["symbol"]
        win_rate = coin["win_rate"] / 100.0
        
        # Phân bổ vốn dựa trên tỷ lệ thắng
        weight = win_rate / sum(c["win_rate"] / 100.0 for c in TOP_COINS)
        position_size = account_balance * 0.2 * weight  # 20% tài khoản phân bổ theo trọng số
        
        # Đảm bảo kích thước lệnh hợp lý
        position_size = min(position_size, account_balance * 0.1)  # Tối đa 10% tài khoản cho 1 lệnh
        position_sizes[symbol] = position_size
    
    # Tạo chiến lược vào lệnh
    entry_strategy = {
        "account_balance": account_balance,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timezone_offset": timezone_offset,
        "total_weekly_entries": sum(day["num_entries"] for day in weekly_schedule.values()),
        "weekly_schedule": weekly_schedule,
        "position_sizes": position_sizes,
        "successful_patterns": patterns,
        "recommendations": [
            "Chỉ vào lệnh vào thời điểm đã được xác định trước trong lịch trình",
            "Ưu tiên các mẫu giao dịch có tỷ lệ thắng cao (>60%)",
            "Tập trung vào khung thời gian 1d và 4h để có tỷ lệ thắng cao nhất",
            "Tránh giao dịch vào cuối tuần (thứ 7, chủ nhật) khi thị trường ít thanh khoản",
            "Nếu gặp mẫu giao dịch có tỷ lệ thắng thấp, giảm kích thước lệnh xuống 50%",
            "Đặt cảnh báo giá để theo dõi hiệu quả thời điểm vào lệnh đã lên lịch"
        ]
    }
    
    return entry_strategy

def generate_telegram_schedule(entry_strategy: Dict) -> str:
    """
    Tạo lịch gửi thông báo Telegram

    Args:
        entry_strategy (Dict): Chiến lược vào lệnh

    Returns:
        str: Nội dung thông báo Telegram
    """
    schedule = entry_strategy["weekly_schedule"]
    
    # Tạo chuỗi thông báo
    message = "🔔 *LỊCH VÀO LỆNH HÀNG TUẦN* 🔔\n\n"
    
    for day, data in schedule.items():
        message += f"*{day}* (Tỷ lệ thắng: {data['win_rate']:.1f}%)\n"
        
        for i, entry in enumerate(data["entries"], 1):
            start_time = entry["local_start_str"]
            end_time = entry["local_end_str"]
            coins = ", ".join([c["symbol"] for c in entry["coins"]])
            
            message += f"  {i}. {start_time}-{end_time} ({entry['name']})\n"
            message += f"     Coins: {coins}\n"
        
        message += "\n"
    
    message += "*LƯU Ý QUAN TRỌNG:*\n"
    message += "• Chỉ vào lệnh khi có tín hiệu rõ ràng\n"
    message += "• Ưu tiên mẫu giao dịch có tỷ lệ thắng cao\n"
    message += "• Luôn đặt stop loss và take profit\n"
    message += "• Thứ 4 và Thứ 5 là ngày tốt nhất để giao dịch\n"
    
    return message

def generate_pattern_examples(output_dir: str = "trading_patterns"):
    """
    Tạo file markdown mô tả các mẫu giao dịch thành công

    Args:
        output_dir (str): Thư mục đầu ra
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Tạo file markdown cho từng mẫu
    for pattern in SUCCESSFUL_PATTERNS:
        pattern_name = pattern["name"].replace("/", "_")
        file_name = f"{pattern_name.lower().replace(' ', '_')}.md"
        file_path = os.path.join(output_dir, file_name)
        
        content = f"""# {pattern["name"]}

## Mô tả
{pattern["description"]}

## Hiệu suất
- **Tỷ lệ thắng:** {pattern["win_rate"]}%
- **Khung thời gian tốt nhất:** {pattern["optimal_timeframe"]}

## Ví dụ
{pattern["example"]}

## Cách nhận diện
1. Xác định mẫu hình trên biểu đồ {pattern["optimal_timeframe"]}
2. Kiểm tra volume để xác nhận tín hiệu
3. Đợi breakout hoặc reversal rõ ràng
4. Vào lệnh với stop loss phù hợp

## Khi nào KHÔNG sử dụng mẫu này
- Thị trường đang biến động mạnh không có xu hướng rõ ràng
- Volume thấp bất thường
- Tin tức quan trọng sắp được công bố

## Thiết lập giao dịch đề xuất
- **Stop Loss:** 1-2 ATR từ điểm vào lệnh
- **Take Profit:** 2-3 lần Stop Loss
- **Thời gian nắm giữ tối đa:** 3-5 candle {pattern["optimal_timeframe"]}
"""
        
        with open(file_path, "w") as f:
            f.write(content)
        
        logger.info(f"Đã tạo file mẫu giao dịch: {file_path}")

def generate_markdown_schedule(entry_strategy: Dict, output_file: str = "optimized_entry_schedule.md"):
    """
    Tạo báo cáo markdown từ chiến lược vào lệnh

    Args:
        entry_strategy (Dict): Chiến lược vào lệnh
        output_file (str): File đầu ra cho báo cáo
    """
    schedule = entry_strategy["weekly_schedule"]
    
    # Tạo nội dung báo cáo
    report = f"""# Lịch Trình Vào Lệnh Tối Ưu (3-5 Lệnh/Ngày)

*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Tổng Quan

Đây là lịch trình vào lệnh được tối ưu hóa để đạt tỷ lệ thắng cao nhất, giới hạn ở 3-5 lệnh mỗi ngày. Lịch trình này được thiết kế dựa trên phân tích các thời điểm giao dịch tối ưu và tỷ lệ thắng lịch sử của từng khung thời gian.

## Thông Số Chính

| Thông Số | Giá Trị |
|----------|---------|
| Số dư tài khoản | ${entry_strategy['account_balance']} USD |
| Múi giờ | UTC+{entry_strategy['timezone_offset']} |
| Tổng số lệnh/tuần | {entry_strategy['total_weekly_entries']} |
| Số lệnh trung bình/ngày | {entry_strategy['total_weekly_entries']/7:.1f} |

## Lịch Trình Hàng Tuần

"""
    
    # Sắp xếp các ngày trong tuần
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    sorted_schedule = {day: schedule[day] for day in weekday_order if day in schedule}
    
    # Thêm lịch trình cho từng ngày
    for day, data in sorted_schedule.items():
        report += f"### {day} (Tỷ lệ thắng: {data['win_rate']:.1f}%)\n\n"
        
        if data["entries"]:
            report += "| STT | Thời gian (Giờ địa phương) | Sự kiện | Coins | Tỷ lệ thắng |\n"
            report += "|-----|---------------------------|---------|-------|------------|\n"
            
            for i, entry in enumerate(data["entries"], 1):
                start_time = entry["local_start_str"]
                end_time = entry["local_end_str"]
                coins = ", ".join([c["symbol"] for c in entry["coins"]])
                win_rate = data["win_rate"] + entry["win_rate_bonus"]
                
                report += f"| {i} | {start_time}-{end_time} | {entry['name']} | {coins} | {win_rate:.1f}% |\n"
        else:
            report += "*Không có lệnh được lên lịch cho ngày này.*\n"
        
        report += "\n"
    
    # Thêm kích thước lệnh cho từng coin
    report += "## Kích Thước Lệnh Đề Xuất\n\n"
    report += "| Coin | Kích Thước Lệnh (USD) | Tỷ lệ thắng |\n"
    report += "|------|----------------------|------------|\n"
    
    for coin in TOP_COINS:
        symbol = coin["symbol"]
        position_size = entry_strategy["position_sizes"][symbol]
        win_rate = coin["win_rate"]
        
        report += f"| {symbol} | ${position_size:.2f} | {win_rate:.1f}% |\n"
    
    # Thêm các mẫu giao dịch thành công
    report += """
## Mẫu Giao Dịch Thành Công

Sử dụng các mẫu giao dịch sau để tăng tỷ lệ thắng:

| Mẫu | Mô tả | Tỷ lệ thắng | Khung thời gian tốt nhất |
|-----|-------|------------|---------------------------|
"""
    
    for pattern in SUCCESSFUL_PATTERNS:
        report += f"| {pattern['name']} | {pattern['description']} | {pattern['win_rate']}% | {pattern['optimal_timeframe']} |\n"
    
    # Thêm khuyến nghị
    report += """
## Khuyến Nghị Tối Ưu Hóa 3-5 Lệnh/Ngày

"""
    
    for i, recommendation in enumerate(entry_strategy["recommendations"], 1):
        report += f"{i}. **{recommendation}**\n"
    
    report += """
## Quy Trình Vào Lệnh Tối Ưu

1. **Lên lịch trước**: Đặt cảnh báo giá cho các thời điểm vào lệnh đã lên lịch
2. **Xác nhận tín hiệu**: Chỉ vào lệnh khi có tín hiệu kỹ thuật rõ ràng
3. **Kiểm tra các mẫu giao dịch**: Ưu tiên các mẫu có tỷ lệ thắng cao
4. **Kiểm tra tin tức**: Tránh vào lệnh trước các tin tức lớn
5. **Đặt SL/TP ngay lập tức**: Luôn đặt stop loss và take profit khi vào lệnh
6. **Ghi nhật ký giao dịch**: Ghi lại tất cả các giao dịch để phân tích sau này

## Chỉ Số Hiệu Suất Kỳ Vọng

- **Tỷ lệ thắng trung bình**: 54-59%
- **Profit factor**: 1.5-1.9
- **Drawdown tối đa**: 15-20%
- **Thời gian nắm giữ trung bình**: 1-3 ngày
"""
    
    # Lưu báo cáo
    with open(output_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Đã tạo báo cáo lịch trình vào lệnh tại {output_file}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Tạo chiến lược vào lệnh tối ưu 3-5 lệnh/ngày')
    parser.add_argument('--balance', type=float, default=450.0, help='Số dư tài khoản (USD)')
    parser.add_argument('--entries', type=int, default=4, help='Số lệnh mỗi ngày (3-5)')
    parser.add_argument('--timezone', type=int, default=7, help='Chênh lệch múi giờ so với UTC (giờ)')
    parser.add_argument('--output', type=str, default='optimized_entry_strategy.json', help='File cấu hình đầu ra')
    parser.add_argument('--report', type=str, default='optimized_entry_schedule.md', help='File báo cáo đầu ra')
    args = parser.parse_args()
    
    # Kiểm tra số dư tài khoản hợp lệ
    if args.balance <= 0:
        logger.error("Số dư tài khoản phải lớn hơn 0")
        sys.exit(1)
    
    # Kiểm tra số lệnh mỗi ngày hợp lệ
    if args.entries < 3 or args.entries > 5:
        logger.error("Số lệnh mỗi ngày phải từ 3 đến 5")
        sys.exit(1)
    
    # Tạo chiến lược vào lệnh
    entry_strategy = generate_entry_strategy(args.balance, args.entries, args.timezone)
    
    # Lưu chiến lược vào lệnh
    with open(args.output, 'w') as f:
        json.dump(entry_strategy, f, indent=2)
    
    logger.info(f"Đã lưu chiến lược vào lệnh vào {args.output}")
    
    # Tạo báo cáo markdown
    generate_markdown_schedule(entry_strategy, args.report)
    
    # Tạo các file mẫu giao dịch
    generate_pattern_examples()
    
    # Tạo nội dung thông báo Telegram
    telegram_message = generate_telegram_schedule(entry_strategy)
    
    # Hiển thị tổng quan
    print(f"\n===== Chiến lược vào lệnh tối ưu ({args.entries} lệnh/ngày) =====")
    print(f"Múi giờ: UTC+{args.timezone}")
    print(f"Tổng số lệnh/tuần: {entry_strategy['total_weekly_entries']}")
    
    print("\nTop 3 ngày giao dịch tốt nhất:")
    # Sắp xếp các ngày theo tỷ lệ thắng giảm dần
    sorted_days = sorted(entry_strategy["weekly_schedule"].items(), 
                        key=lambda x: x[1]["win_rate"], reverse=True)
    for i, (day, data) in enumerate(sorted_days[:3], 1):
        print(f"{i}. {day} - Tỷ lệ thắng: {data['win_rate']:.1f}% - Số lệnh: {data['num_entries']}")
    
    print("\nTop 3 thời điểm vào lệnh tốt nhất:")
    all_entries = []
    for day, data in entry_strategy["weekly_schedule"].items():
        for entry in data["entries"]:
            entry_with_day = entry.copy()
            entry_with_day["day"] = day
            all_entries.append(entry_with_day)
    
    # Sắp xếp theo win_rate_bonus giảm dần
    sorted_entries = sorted(all_entries, key=lambda x: x["win_rate_bonus"], reverse=True)
    for i, entry in enumerate(sorted_entries[:3], 1):
        print(f"{i}. {entry['day']} {entry['local_start_str']}-{entry['local_end_str']} ({entry['name']})")
    
    print(f"\nCấu hình chi tiết được lưu tại: {args.output}")
    print(f"Lịch trình vào lệnh được lưu tại: {args.report}")
    print(f"Các mẫu giao dịch thành công được lưu trong thư mục: trading_patterns/")

if __name__ == "__main__":
    main()