#!/usr/bin/env python3
"""
CLI Controller cho BinanceTrader Bot

Module này cung cấp giao diện dòng lệnh (CLI) để điều khiển và giám sát
bot giao dịch tiền điện tử. Giao diện này giúp người dùng dễ dàng quản lý bot
mà không cần sử dụng giao diện web, đặc biệt hữu ích khi có vấn đề về kết nối
hoặc khi cần tương tác từ xa qua SSH.
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cli_controller.log')
    ]
)
logger = logging.getLogger('cli_controller')

# Các màu ANSI để làm đẹp đầu ra
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str) -> None:
    """In tiêu đề với định dạng nổi bật"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*50}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(50)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*50}{Colors.ENDC}\n")

def print_colored(text: str, color: str) -> None:
    """In văn bản với màu đã chọn"""
    print(f"{color}{text}{Colors.ENDC}")

def get_bot_status() -> Dict:
    """Kiểm tra trạng thái của bot và trả về thông tin chi tiết"""
    # Kiểm tra xem bot có đang chạy không
    ps_result = subprocess.run(
        "ps aux | grep 'python multi_coin_bot.py' | grep -v grep",
        shell=True,
        capture_output=True,
        text=True
    )
    
    is_running = len(ps_result.stdout.strip()) > 0
    
    if is_running:
        # Nếu bot đang chạy, lấy thêm thông tin chi tiết
        # Kiểm tra xem file trạng thái có tồn tại không
        if os.path.exists("trading_state.json"):
            try:
                with open("trading_state.json", "r") as f:
                    trading_state = json.load(f)
                
                # Kiểm tra log gần đây
                log_tail = subprocess.run(
                    "tail -n 10 trading_bot.log",
                    shell=True,
                    capture_output=True,
                    text=True
                ).stdout
                
                # Lấy PID của bot
                pid = ps_result.stdout.split()[1] if ps_result.stdout else "N/A"
                
                return {
                    "status": "running",
                    "pid": pid,
                    "uptime": trading_state.get("uptime", "N/A"),
                    "start_time": trading_state.get("start_time", "N/A"),
                    "current_balance": trading_state.get("current_balance", 0),
                    "open_positions": len(trading_state.get("open_positions", [])),
                    "total_trades": len(trading_state.get("closed_positions", [])),
                    "recent_log": log_tail,
                }
            except Exception as e:
                logger.error(f"Lỗi khi đọc trạng thái giao dịch: {e}")
                return {
                    "status": "running",
                    "pid": ps_result.stdout.split()[1] if ps_result.stdout else "N/A",
                    "error": str(e)
                }
        else:
            return {
                "status": "running",
                "pid": ps_result.stdout.split()[1] if ps_result.stdout else "N/A",
                "message": "Bot đang chạy nhưng chưa có thông tin trạng thái"
            }
    else:
        return {
            "status": "stopped",
            "message": "Bot không chạy"
        }

def format_status(status: Dict) -> str:
    """Format trạng thái bot thành văn bản đầu ra"""
    if status["status"] == "running":
        result = [
            f"{Colors.GREEN}●{Colors.ENDC} {Colors.BOLD}Trạng thái:{Colors.ENDC} Đang chạy",
            f"{Colors.BOLD}PID:{Colors.ENDC} {status.get('pid', 'N/A')}",
        ]
        
        # Thêm các thông tin khác nếu có
        for key in ['uptime', 'start_time', 'current_balance']:
            if key in status:
                label = key.replace('_', ' ').title()
                value = status[key]
                if key == 'current_balance':
                    value = f"${value:.2f}" if isinstance(value, (int, float)) else value
                result.append(f"{Colors.BOLD}{label}:{Colors.ENDC} {value}")
        
        if 'open_positions' in status:
            result.append(f"{Colors.BOLD}Vị thế mở:{Colors.ENDC} {status['open_positions']}")
            
        if 'total_trades' in status:
            result.append(f"{Colors.BOLD}Tổng số giao dịch:{Colors.ENDC} {status['total_trades']}")
        
        return "\n".join(result)
    else:
        return f"{Colors.RED}●{Colors.ENDC} {Colors.BOLD}Trạng thái:{Colors.ENDC} Đã dừng\n{status.get('message', '')}"

def get_open_positions() -> List[Dict]:
    """Lấy danh sách các vị thế mở hiện tại"""
    try:
        if os.path.exists("trading_state.json"):
            with open("trading_state.json", "r") as f:
                trading_state = json.load(f)
                return trading_state.get("open_positions", [])
        return []
    except Exception as e:
        logger.error(f"Lỗi khi đọc vị thế mở: {e}")
        return []

def get_recent_trades(limit: int = 10) -> List[Dict]:
    """Lấy các giao dịch gần đây"""
    try:
        if os.path.exists("trading_state.json"):
            with open("trading_state.json", "r") as f:
                trading_state = json.load(f)
                closed_positions = trading_state.get("closed_positions", [])
                
                # Sắp xếp theo thời gian đóng vị thế (gần nhất đầu tiên)
                sorted_positions = sorted(
                    closed_positions,
                    key=lambda x: x.get('exit_time', ''),
                    reverse=True
                )
                
                return sorted_positions[:limit]
        return []
    except Exception as e:
        logger.error(f"Lỗi khi đọc giao dịch gần đây: {e}")
        return []

def display_positions(positions: List[Dict], title: str = "Vị thế hiện tại") -> None:
    """Hiển thị danh sách vị thế dưới dạng bảng"""
    if not positions:
        print_colored("Không có vị thế nào.", Colors.YELLOW)
        return
    
    # Chuyển đổi dữ liệu vào DataFrame để dễ dàng hiển thị
    df_data = []
    for pos in positions:
        df_data.append({
            'ID': pos.get('id', 'N/A')[:8],
            'Symbol': pos.get('symbol', 'N/A'),
            'Type': pos.get('type', 'N/A'),
            'Entry': f"${pos.get('entry_price', 0):.2f}",
            'Current': f"${pos.get('current_price', 0):.2f}" 
                     if 'current_price' in pos else f"${pos.get('exit_price', 0):.2f}",
            'Qty': f"{pos.get('quantity', 0):.4f}",
            'P&L': f"${pos.get('pnl', 0):.2f}",
            'P&L %': f"{pos.get('pnl_percent', 0):.2f}%",
            'Time': pos.get('entry_time', 'N/A')[:16] 
                  if 'entry_time' in pos else pos.get('exit_time', 'N/A')[:16]
        })
    
    df = pd.DataFrame(df_data)
    print_header(title)
    print(tabulate(df, headers='keys', tablefmt='pretty', showindex=False))
    print()

def display_performance_metrics() -> None:
    """Hiển thị các chỉ số hiệu suất của bot"""
    try:
        if os.path.exists("trading_state.json"):
            with open("trading_state.json", "r") as f:
                trading_state = json.load(f)
                
                # Lấy các chỉ số từ trạng thái giao dịch
                metrics = trading_state.get("performance_metrics", {})
                
                if not metrics:
                    print_colored("Chưa có dữ liệu hiệu suất.", Colors.YELLOW)
                    return
                
                print_header("Chỉ số hiệu suất")
                
                # Format các chỉ số thành bảng
                data = []
                for key, value in metrics.items():
                    # Format các trường phổ biến
                    formatted_key = key.replace('_', ' ').title()
                    
                    if isinstance(value, float):
                        # Format phần trăm và tiền
                        if 'percent' in key or 'rate' in key:
                            formatted_value = f"{value:.2f}%"
                        elif 'ratio' in key:
                            formatted_value = f"{value:.3f}"
                        else:
                            formatted_value = f"${value:.2f}" if value > 100 else f"{value:.2f}"
                    else:
                        formatted_value = str(value)
                    
                    data.append([formatted_key, formatted_value])
                
                # Chia các chỉ số thành 2 cột để hiển thị tốt hơn
                mid_point = len(data) // 2 + len(data) % 2
                left_col = data[:mid_point]
                right_col = data[mid_point:]
                
                # Đảm bảo 2 cột bằng nhau bằng cách thêm hàng trống vào cột phải
                while len(right_col) < len(left_col):
                    right_col.append(["", ""])
                
                # Gộp hai cột
                table_data = []
                for i in range(len(left_col)):
                    row = left_col[i] + right_col[i] if i < len(right_col) else left_col[i] + ["", ""]
                    table_data.append(row)
                
                # In bảng
                print(tabulate(table_data, tablefmt='pretty'))
                print()
                
        else:
            print_colored("Không tìm thấy file trạng thái giao dịch.", Colors.YELLOW)
    except Exception as e:
        logger.error(f"Lỗi khi đọc chỉ số hiệu suất: {e}")
        print_colored(f"Lỗi: {e}", Colors.RED)

def start_bot() -> bool:
    """Khởi động bot"""
    status = get_bot_status()
    
    if status["status"] == "running":
        print_colored("Bot đã đang chạy!", Colors.YELLOW)
        return False
    
    try:
        print_colored("Đang khởi động bot...", Colors.BLUE)
        subprocess.Popen(
            "python multi_coin_bot.py",
            shell=True,
            stdin=None,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Đợi một chút và kiểm tra xem bot đã khởi động thành công hay chưa
        time.sleep(3)
        new_status = get_bot_status()
        
        if new_status["status"] == "running":
            print_colored("Bot đã khởi động thành công!", Colors.GREEN)
            return True
        else:
            print_colored("Không thể khởi động bot. Vui lòng kiểm tra logs.", Colors.RED)
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi động bot: {e}")
        print_colored(f"Lỗi: {e}", Colors.RED)
        return False

def stop_bot() -> bool:
    """Dừng bot"""
    status = get_bot_status()
    
    if status["status"] == "stopped":
        print_colored("Bot đã dừng rồi!", Colors.YELLOW)
        return False
    
    try:
        pid = status.get("pid", None)
        if pid:
            print_colored(f"Đang dừng bot (PID: {pid})...", Colors.BLUE)
            subprocess.run(f"kill {pid}", shell=True)
            
            # Đợi một chút và kiểm tra xem bot đã dừng thành công hay chưa
            time.sleep(3)
            new_status = get_bot_status()
            
            if new_status["status"] == "stopped":
                print_colored("Bot đã dừng thành công!", Colors.GREEN)
                return True
            else:
                print_colored("Không thể dừng bot. Đang thử dừng mạnh...", Colors.YELLOW)
                subprocess.run(f"kill -9 {pid}", shell=True)
                time.sleep(1)
                
                if get_bot_status()["status"] == "stopped":
                    print_colored("Bot đã dừng thành công (buộc dừng)!", Colors.GREEN)
                    return True
                else:
                    print_colored("Không thể dừng bot. Vui lòng kiểm tra manually.", Colors.RED)
                    return False
        else:
            print_colored("Không thể xác định PID của bot.", Colors.RED)
            return False
    except Exception as e:
        logger.error(f"Lỗi khi dừng bot: {e}")
        print_colored(f"Lỗi: {e}", Colors.RED)
        return False

def restart_bot() -> bool:
    """Khởi động lại bot"""
    print_colored("Đang khởi động lại bot...", Colors.BLUE)
    
    # Dừng bot nếu đang chạy
    if get_bot_status()["status"] == "running":
        if not stop_bot():
            print_colored("Không thể dừng bot, hủy khởi động lại.", Colors.RED)
            return False
    
    # Đợi một chút
    time.sleep(2)
    
    # Khởi động lại bot
    return start_bot()

def view_logs(lines: int = 20) -> None:
    """Xem log gần đây của bot"""
    print_header(f"Log gần đây (last {lines} lines)")
    
    if os.path.exists("trading_bot.log"):
        log_tail = subprocess.run(
            f"tail -n {lines} trading_bot.log",
            shell=True,
            capture_output=True,
            text=True
        ).stdout
        
        print(log_tail)
    else:
        print_colored("Không tìm thấy file log.", Colors.YELLOW)

def display_real_time_monitor(refresh_interval: int = 5) -> None:
    """Hiển thị màn hình giám sát thời gian thực"""
    try:
        print_colored("Đang bắt đầu chế độ giám sát. Nhấn Ctrl+C để thoát.", Colors.BLUE)
        
        # Đặt signal handler để bắt Ctrl+C
        def signal_handler(sig, frame):
            print_colored("\nĐã thoát chế độ giám sát.", Colors.BLUE)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        while True:
            # Xóa màn hình
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Lấy thông tin hiện tại
            status = get_bot_status()
            positions = get_open_positions()
            
            # Hiển thị thông tin
            print_header("BinanceTrader Bot - Màn hình giám sát")
            print(format_status(status))
            print()
            
            if positions:
                display_positions(positions)
            else:
                print_colored("Không có vị thế mở nào.", Colors.YELLOW)
                print()
            
            # Hiển thị thời gian cập nhật tiếp theo
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"Cập nhật vào: {current_time} | Cập nhật tiếp theo sau {refresh_interval} giây")
            print(f"Nhấn {Colors.BOLD}Ctrl+C{Colors.ENDC} để thoát")
            
            # Đợi đến lần cập nhật tiếp theo
            time.sleep(refresh_interval)
    except KeyboardInterrupt:
        print_colored("\nĐã thoát chế độ giám sát.", Colors.BLUE)
    except Exception as e:
        logger.error(f"Lỗi trong chế độ giám sát: {e}")
        print_colored(f"Lỗi: {e}", Colors.RED)

def set_environment_variable(key: str, value: str) -> bool:
    """Thiết lập biến môi trường trong file .env"""
    try:
        env_file = ".env"
        
        # Đọc file .env hiện tại
        env_vars = {}
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        var_name, var_value = line.split('=', 1)
                        env_vars[var_name] = var_value
        
        # Cập nhật biến
        env_vars[key] = value
        
        # Ghi lại file
        with open(env_file, "w") as f:
            for var_name, var_value in env_vars.items():
                f.write(f"{var_name}={var_value}\n")
        
        print_colored(f"Đã thiết lập {key}={value}", Colors.GREEN)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập biến môi trường: {e}")
        print_colored(f"Lỗi: {e}", Colors.RED)
        return False

def toggle_auto_start(enable: bool) -> bool:
    """Bật/tắt tự động khởi động bot"""
    return set_environment_variable("AUTO_START_BOT", "true" if enable else "false")

def toggle_auto_restart(enable: bool) -> bool:
    """Bật/tắt tự động khởi động lại bot khi bị crash"""
    return set_environment_variable("AUTO_RESTART_BOT", "true" if enable else "false")

def run_backtest() -> bool:
    """Chạy backtest"""
    print_colored("Đang chạy backtest...", Colors.BLUE)
    
    try:
        # Chạy script backtest và hiển thị output
        process = subprocess.Popen(
            "python quick_backtest.py",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Hiển thị output theo thời gian thực
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
        
        # Đợi quy trình hoàn thành
        return_code = process.wait()
        
        if return_code == 0:
            print_colored("Backtest đã hoàn thành thành công!", Colors.GREEN)
            return True
        else:
            print_colored(f"Backtest thất bại với mã lỗi {return_code}.", Colors.RED)
            return False
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest: {e}")
        print_colored(f"Lỗi: {e}", Colors.RED)
        return False

def interactive_menu() -> None:
    """Hiển thị menu tương tác"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("BinanceTrader Bot - Menu điều khiển")
        
        # Hiển thị trạng thái bot
        status = get_bot_status()
        print(format_status(status))
        print()
        
        # Hiển thị menu
        print(f"{Colors.BOLD}MENU CÁC LỆNH:{Colors.ENDC}")
        print(f" {Colors.CYAN}1.{Colors.ENDC} Xem vị thế hiện tại")
        print(f" {Colors.CYAN}2.{Colors.ENDC} Xem giao dịch gần đây")
        print(f" {Colors.CYAN}3.{Colors.ENDC} Xem chỉ số hiệu suất")
        print(f" {Colors.CYAN}4.{Colors.ENDC} Xem logs")
        print(f" {Colors.CYAN}5.{Colors.ENDC} Màn hình giám sát thời gian thực")
        print()
        print(f" {Colors.GREEN}s.{Colors.ENDC} Khởi động bot" if status["status"] == "stopped" else f" {Colors.RED}s.{Colors.ENDC} Dừng bot")
        print(f" {Colors.YELLOW}r.{Colors.ENDC} Khởi động lại bot")
        print()
        print(f" {Colors.BLUE}b.{Colors.ENDC} Chạy backtest")
        print(f" {Colors.BLUE}c.{Colors.ENDC} Cấu hình bot")
        print()
        print(f" {Colors.RED}q.{Colors.ENDC} Thoát")
        
        # Nhận lựa chọn từ người dùng
        choice = input("\nNhập lựa chọn của bạn: ").strip().lower()
        
        if choice == '1':
            positions = get_open_positions()
            display_positions(positions)
            input("Nhấn Enter để tiếp tục...")
        elif choice == '2':
            trades = get_recent_trades()
            display_positions(trades, "Giao dịch gần đây")
            input("Nhấn Enter để tiếp tục...")
        elif choice == '3':
            display_performance_metrics()
            input("Nhấn Enter để tiếp tục...")
        elif choice == '4':
            lines = input("Số dòng log muốn hiển thị (mặc định 20): ").strip()
            lines = int(lines) if lines.isdigit() else 20
            view_logs(lines)
            input("Nhấn Enter để tiếp tục...")
        elif choice == '5':
            interval = input("Tần suất làm mới (giây, mặc định 5): ").strip()
            interval = int(interval) if interval.isdigit() else 5
            display_real_time_monitor(interval)
        elif choice == 's':
            if status["status"] == "stopped":
                start_bot()
            else:
                stop_bot()
            input("Nhấn Enter để tiếp tục...")
        elif choice == 'r':
            restart_bot()
            input("Nhấn Enter để tiếp tục...")
        elif choice == 'b':
            run_backtest()
            input("Nhấn Enter để tiếp tục...")
        elif choice == 'c':
            config_menu()
        elif choice == 'q':
            print_colored("Thoát chương trình. Tạm biệt!", Colors.BLUE)
            break
        else:
            print_colored("Lựa chọn không hợp lệ!", Colors.RED)
            time.sleep(1)

def config_menu() -> None:
    """Hiển thị menu cấu hình"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("BinanceTrader Bot - Menu cấu hình")
        
        # Đọc trạng thái tự động bật/tắt từ file .env
        auto_start = "true" == os.environ.get("AUTO_START_BOT", "false").lower()
        auto_restart = "true" == os.environ.get("AUTO_RESTART_BOT", "false").lower()
        
        # Hiển thị trạng thái hiện tại
        print(f"{Colors.BOLD}Cấu hình hiện tại:{Colors.ENDC}")
        print(f" Tự động khởi động: {'Bật' if auto_start else 'Tắt'}")
        print(f" Tự động khởi động lại: {'Bật' if auto_restart else 'Tắt'}")
        print()
        
        # Hiển thị menu
        print(f"{Colors.BOLD}Tùy chọn:{Colors.ENDC}")
        print(f" {Colors.CYAN}1.{Colors.ENDC} {'Tắt' if auto_start else 'Bật'} tự động khởi động")
        print(f" {Colors.CYAN}2.{Colors.ENDC} {'Tắt' if auto_restart else 'Bật'} tự động khởi động lại")
        print(f" {Colors.CYAN}3.{Colors.ENDC} Cấu hình API key")
        print(f" {Colors.CYAN}4.{Colors.ENDC} Cấu hình thông báo Telegram")
        print()
        print(f" {Colors.RED}b.{Colors.ENDC} Quay lại")
        
        # Nhận lựa chọn từ người dùng
        choice = input("\nNhập lựa chọn của bạn: ").strip().lower()
        
        if choice == '1':
            toggle_auto_start(not auto_start)
            input("Nhấn Enter để tiếp tục...")
        elif choice == '2':
            toggle_auto_restart(not auto_restart)
            input("Nhấn Enter để tiếp tục...")
        elif choice == '3':
            api_key = input("Nhập Binance API Key: ").strip()
            if api_key:
                set_environment_variable("BINANCE_API_KEY", api_key)
            
            api_secret = input("Nhập Binance API Secret: ").strip()
            if api_secret:
                set_environment_variable("BINANCE_API_SECRET", api_secret)
            
            input("Nhấn Enter để tiếp tục...")
        elif choice == '4':
            bot_token = input("Nhập Telegram Bot Token: ").strip()
            if bot_token:
                set_environment_variable("TELEGRAM_BOT_TOKEN", bot_token)
            
            chat_id = input("Nhập Telegram Chat ID: ").strip()
            if chat_id:
                set_environment_variable("TELEGRAM_CHAT_ID", chat_id)
            
            input("Nhấn Enter để tiếp tục...")
        elif choice == 'b':
            break
        else:
            print_colored("Lựa chọn không hợp lệ!", Colors.RED)
            time.sleep(1)

def main() -> None:
    """Hàm chính của ứng dụng"""
    # Tạo parser để xử lý tham số dòng lệnh
    parser = argparse.ArgumentParser(description='CLI Controller cho BinanceTrader Bot')
    
    # Thêm các tùy chọn dòng lệnh
    parser.add_argument('--status', '-s', action='store_true', help='Hiển thị trạng thái bot')
    parser.add_argument('--positions', '-p', action='store_true', help='Hiển thị vị thế hiện tại')
    parser.add_argument('--trades', '-t', action='store_true', help='Hiển thị giao dịch gần đây')
    parser.add_argument('--logs', '-l', type=int, metavar='N', nargs='?', const=20, help='Hiển thị N dòng log gần đây')
    parser.add_argument('--start', action='store_true', help='Khởi động bot')
    parser.add_argument('--stop', action='store_true', help='Dừng bot')
    parser.add_argument('--restart', action='store_true', help='Khởi động lại bot')
    parser.add_argument('--monitor', '-m', type=int, metavar='INTERVAL', nargs='?', const=5, help='Giám sát bot theo thời gian thực')
    parser.add_argument('--backtest', '-b', action='store_true', help='Chạy backtest')
    
    # Parse tham số
    args = parser.parse_args()
    
    # Nếu không có tham số nào, hiển thị menu tương tác
    if len(sys.argv) == 1:
        interactive_menu()
        return
    
    # Xử lý các tham số dòng lệnh
    if args.status:
        status = get_bot_status()
        print(format_status(status))
    
    if args.positions:
        positions = get_open_positions()
        display_positions(positions)
    
    if args.trades:
        trades = get_recent_trades()
        display_positions(trades, "Giao dịch gần đây")
    
    if args.logs is not None:
        view_logs(args.logs)
    
    if args.start:
        start_bot()
    
    if args.stop:
        stop_bot()
    
    if args.restart:
        restart_bot()
    
    if args.monitor is not None:
        display_real_time_monitor(args.monitor)
    
    if args.backtest:
        run_backtest()

if __name__ == "__main__":
    main()