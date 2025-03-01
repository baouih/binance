#!/usr/bin/env python3
"""
CLI Controller for Crypto Trading Bot

Công cụ dòng lệnh đơn giản để điều khiển và giám sát bot giao dịch crypto
không phụ thuộc vào giao diện web socketio.
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from datetime import datetime
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("cli_controller.log")
    ]
)
logger = logging.getLogger(__name__)

# Định nghĩa các màu ANSI để hiển thị màu trong terminal
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

def print_banner():
    """Hiển thị banner của chương trình"""
    banner = f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║  {Colors.YELLOW}████████╗██████╗  █████╗ ██████╗ ██╗███╗   ██╗ ██████╗{Colors.CYAN}         ║
║  {Colors.YELLOW}╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝{Colors.CYAN}         ║
║  {Colors.YELLOW}   ██║   ██████╔╝███████║██║  ██║██║██╔██╗ ██║██║  ███╗{Colors.CYAN}        ║
║  {Colors.YELLOW}   ██║   ██╔══██╗██╔══██║██║  ██║██║██║╚██╗██║██║   ██║{Colors.CYAN}        ║
║  {Colors.YELLOW}   ██║   ██║  ██║██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝{Colors.CYAN}        ║
║  {Colors.YELLOW}   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝{Colors.CYAN}         ║
║                                                                   ║
║               {Colors.GREEN}Binance Crypto Trading Bot CLI Controller{Colors.CYAN}            ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝{Colors.ENDC}
    """
    print(banner)

def check_bot_status():
    """Kiểm tra xem bot có đang chạy không và trả về trạng thái"""
    try:
        # Tìm quy trình bot bằng lệnh ps
        result = subprocess.run(
            "ps aux | grep 'python multi_coin_bot.py' | grep -v grep",
            shell=True, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Lấy PID của bot
            pid = result.stdout.strip().split()[1]
            
            # Kiểm tra thời gian uptime
            uptime_result = subprocess.run(
                f"ps -p {pid} -o etime=",
                shell=True,
                capture_output=True,
                text=True
            )
            uptime = uptime_result.stdout.strip()
            
            return {
                "status": "running",
                "pid": pid,
                "uptime": uptime,
                "last_update": datetime.now().strftime("%H:%M:%S")
            }
        else:
            return {
                "status": "stopped",
                "pid": None,
                "uptime": None,
                "last_update": datetime.now().strftime("%H:%M:%S")
            }
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái bot: {e}")
        return {
            "status": "unknown",
            "pid": None,
            "uptime": None,
            "last_update": datetime.now().strftime("%H:%M:%S"),
            "error": str(e)
        }

def start_bot():
    """Khởi động bot"""
    try:
        status = check_bot_status()
        if status["status"] == "running":
            print(f"{Colors.YELLOW}Bot đã đang chạy với PID {status['pid']}{Colors.ENDC}")
            return False
            
        # Khởi động bot trong background
        subprocess.Popen(
            "python multi_coin_bot.py >> trading_bot.log 2>&1 &",
            shell=True
        )
        
        # Kiểm tra xem bot đã khởi động chưa
        time.sleep(2)
        status = check_bot_status()
        if status["status"] == "running":
            print(f"{Colors.GREEN}Bot đã được khởi động thành công với PID {status['pid']}{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.RED}Không thể khởi động bot. Kiểm tra log để biết thêm chi tiết.{Colors.ENDC}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi động bot: {e}")
        print(f"{Colors.RED}Lỗi khi khởi động bot: {e}{Colors.ENDC}")
        return False

def stop_bot():
    """Dừng bot"""
    try:
        status = check_bot_status()
        if status["status"] != "running":
            print(f"{Colors.YELLOW}Bot hiện không chạy{Colors.ENDC}")
            return False
            
        # Dừng bot
        subprocess.run(
            "pkill -f 'python multi_coin_bot.py'",
            shell=True
        )
        
        # Kiểm tra xem bot đã dừng chưa
        time.sleep(2)
        status = check_bot_status()
        if status["status"] == "stopped":
            print(f"{Colors.GREEN}Bot đã được dừng thành công{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.RED}Không thể dừng bot. Thử dừng thủ công với lệnh 'pkill -f python multi_coin_bot.py'{Colors.ENDC}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi dừng bot: {e}")
        print(f"{Colors.RED}Lỗi khi dừng bot: {e}{Colors.ENDC}")
        return False

def restart_bot():
    """Khởi động lại bot"""
    try:
        stop_bot()
        time.sleep(2)
        return start_bot()
    except Exception as e:
        logger.error(f"Lỗi khi khởi động lại bot: {e}")
        print(f"{Colors.RED}Lỗi khi khởi động lại bot: {e}{Colors.ENDC}")
        return False

def load_config():
    """Đọc cấu hình từ file config.json"""
    try:
        if os.path.exists('multi_coin_config.json'):
            with open('multi_coin_config.json', 'r') as f:
                return json.load(f)
        else:
            return None
    except Exception as e:
        logger.error(f"Lỗi khi đọc config: {e}")
        return None

def show_config():
    """Hiển thị cấu hình hiện tại"""
    config = load_config()
    if not config:
        print(f"{Colors.RED}Không thể đọc cấu hình. File multi_coin_config.json không tồn tại hoặc không hợp lệ.{Colors.ENDC}")
        return
    
    # Hiển thị thông tin cặp giao dịch
    pairs_data = []
    for pair in config.get('trading_pairs', []):
        strategies = ", ".join(pair.get('strategies', []))
        timeframes = ", ".join(pair.get('timeframes', []))
        status = f"{Colors.GREEN}Enabled{Colors.ENDC}" if pair.get('enabled', False) else f"{Colors.RED}Disabled{Colors.ENDC}"
        pairs_data.append([
            pair.get('symbol', 'N/A'),
            timeframes,
            strategies,
            status
        ])
    
    print(f"\n{Colors.CYAN}=== Trading Pairs ==={Colors.ENDC}")
    print(tabulate(pairs_data, headers=["Symbol", "Timeframes", "Strategies", "Status"], tablefmt="grid"))
    
    # Hiển thị cấu hình chung
    general_config = [
        ["Risk per trade (%)", config.get('risk_per_trade', 'N/A')],
        ["Default leverage", config.get('default_leverage', 'N/A')],
        ["Position sizing", config.get('position_sizing', 'N/A')],
        ["Default interval", config.get('default_interval', 'N/A')],
        ["Auto trailing stop", "Yes" if config.get('auto_trailing_stop', False) else "No"]
    ]
    
    print(f"\n{Colors.CYAN}=== General Configuration ==={Colors.ENDC}")
    print(tabulate(general_config, tablefmt="grid"))

def view_recent_trades():
    """Hiển thị các giao dịch gần đây từ trading_state.json"""
    try:
        if os.path.exists('trading_state.json'):
            with open('trading_state.json', 'r') as f:
                state = json.load(f)
                
            # Hiển thị vị thế đang mở
            open_positions = state.get('open_positions', [])
            if open_positions:
                positions_data = []
                for pos in open_positions:
                    entry_time = pos.get('entry_time', 'N/A')
                    pnl = pos.get('pnl', 0)
                    pnl_color = Colors.GREEN if pnl >= 0 else Colors.RED
                    pnl_display = f"{pnl_color}{pnl:.2f} ({pos.get('pnl_percent', 0):.2f}%){Colors.ENDC}"
                    
                    positions_data.append([
                        pos.get('symbol', 'N/A'),
                        pos.get('type', 'N/A'),
                        f"{pos.get('entry_price', 0):.2f}",
                        f"{pos.get('current_price', 0):.2f}",
                        pos.get('quantity', 0),
                        pnl_display,
                        entry_time
                    ])
                
                print(f"\n{Colors.CYAN}=== Open Positions ==={Colors.ENDC}")
                print(tabulate(positions_data, 
                              headers=["Symbol", "Type", "Entry", "Current", "Quantity", "PnL", "Entry Time"], 
                              tablefmt="grid"))
            else:
                print(f"\n{Colors.YELLOW}Không có vị thế nào đang mở{Colors.ENDC}")
            
            # Hiển thị giao dịch đã đóng gần đây
            closed_trades = state.get('closed_trades', [])
            if closed_trades:
                # Sắp xếp theo thời gian, lấy 10 giao dịch gần nhất
                sorted_trades = sorted(closed_trades, 
                                      key=lambda x: x.get('exit_time', ''), 
                                      reverse=True)[:10]
                
                trades_data = []
                for trade in sorted_trades:
                    pnl = trade.get('pnl', 0)
                    pnl_color = Colors.GREEN if pnl >= 0 else Colors.RED
                    pnl_display = f"{pnl_color}{pnl:.2f} ({trade.get('pnl_percent', 0):.2f}%){Colors.ENDC}"
                    
                    trades_data.append([
                        trade.get('symbol', 'N/A'),
                        trade.get('type', 'N/A'),
                        f"{trade.get('entry_price', 0):.2f}",
                        f"{trade.get('exit_price', 0):.2f}",
                        trade.get('quantity', 0),
                        pnl_display,
                        trade.get('exit_time', 'N/A')
                    ])
                
                print(f"\n{Colors.CYAN}=== Recent Closed Trades (Last 10) ==={Colors.ENDC}")
                print(tabulate(trades_data, 
                              headers=["Symbol", "Type", "Entry", "Exit", "Quantity", "PnL", "Exit Time"], 
                              tablefmt="grid"))
            else:
                print(f"\n{Colors.YELLOW}Không có giao dịch nào đã đóng{Colors.ENDC}")
            
            # Hiển thị thống kê
            balance = state.get('current_balance', 0)
            initial_balance = state.get('initial_balance', 0)
            total_pnl = balance - initial_balance
            total_pnl_pct = (total_pnl / initial_balance) * 100 if initial_balance else 0
            
            pnl_color = Colors.GREEN if total_pnl >= 0 else Colors.RED
            
            stats_data = [
                ["Initial Balance", f"{initial_balance:.2f}"],
                ["Current Balance", f"{balance:.2f}"],
                ["Total P&L", f"{pnl_color}{total_pnl:.2f} ({total_pnl_pct:.2f}%){Colors.ENDC}"],
                ["Win Rate", f"{state.get('win_rate', 0):.2f}%"],
                ["Total Trades", state.get('total_trades', 0)],
                ["Winning Trades", state.get('winning_trades', 0)],
                ["Losing Trades", state.get('losing_trades', 0)]
            ]
            
            print(f"\n{Colors.CYAN}=== Trading Statistics ==={Colors.ENDC}")
            print(tabulate(stats_data, tablefmt="grid"))
        else:
            print(f"{Colors.YELLOW}Không tìm thấy file trading_state.json. Chưa có dữ liệu giao dịch.{Colors.ENDC}")
    except Exception as e:
        logger.error(f"Lỗi khi đọc dữ liệu giao dịch: {e}")
        print(f"{Colors.RED}Lỗi khi đọc dữ liệu giao dịch: {e}{Colors.ENDC}")

def show_logs(num_lines=50):
    """Hiển thị log gần đây của bot"""
    try:
        if os.path.exists('trading_bot.log'):
            result = subprocess.run(
                f"tail -n {num_lines} trading_bot.log",
                shell=True,
                capture_output=True,
                text=True
            )
            
            log_content = result.stdout.strip()
            if log_content:
                print(f"\n{Colors.CYAN}=== Recent Logs (Last {num_lines} lines) ==={Colors.ENDC}")
                
                # Màu sắc cho các loại log
                colored_log = log_content
                colored_log = colored_log.replace(" ERROR ", f"{Colors.RED} ERROR {Colors.ENDC}")
                colored_log = colored_log.replace(" WARNING ", f"{Colors.YELLOW} WARNING {Colors.ENDC}")
                colored_log = colored_log.replace(" INFO ", f"{Colors.GREEN} INFO {Colors.ENDC}")
                
                print(colored_log)
            else:
                print(f"{Colors.YELLOW}File log rỗng{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}Không tìm thấy file trading_bot.log{Colors.ENDC}")
    except Exception as e:
        logger.error(f"Lỗi khi đọc log: {e}")
        print(f"{Colors.RED}Lỗi khi đọc log: {e}{Colors.ENDC}")

def show_system_status():
    """Hiển thị trạng thái hệ thống"""
    try:
        # Kiểm tra trạng thái bot
        bot_status = check_bot_status()
        
        # Lấy thông tin CPU, memory
        cpu_result = subprocess.run(
            "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'",
            shell=True,
            capture_output=True,
            text=True
        )
        cpu_usage = cpu_result.stdout.strip()
        
        mem_result = subprocess.run(
            "free -m | grep Mem | awk '{print $3,$2,$3*100/$2}'",
            shell=True,
            capture_output=True,
            text=True
        )
        mem_output = mem_result.stdout.strip().split()
        if len(mem_output) >= 3:
            mem_used = mem_output[0]
            mem_total = mem_output[1]
            mem_percent = float(mem_output[2])
        else:
            mem_used = "N/A"
            mem_total = "N/A"
            mem_percent = 0
            
        # Lấy thông tin disk
        disk_result = subprocess.run(
            "df -h . | tail -1 | awk '{print $3,$2,$5}'",
            shell=True,
            capture_output=True,
            text=True
        )
        disk_output = disk_result.stdout.strip().split()
        if len(disk_output) >= 3:
            disk_used = disk_output[0]
            disk_total = disk_output[1]
            disk_percent = disk_output[2]
        else:
            disk_used = "N/A"
            disk_total = "N/A"
            disk_percent = "N/A"
            
        # Định dạng trạng thái bot với màu sắc
        if bot_status["status"] == "running":
            status_str = f"{Colors.GREEN}Running{Colors.ENDC}"
        elif bot_status["status"] == "stopped":
            status_str = f"{Colors.RED}Stopped{Colors.ENDC}"
        else:
            status_str = f"{Colors.YELLOW}Unknown{Colors.ENDC}"
            
        # Dữ liệu hệ thống
        system_data = [
            ["Bot Status", status_str],
            ["Bot PID", bot_status.get("pid", "N/A")],
            ["Bot Uptime", bot_status.get("uptime", "N/A")],
            ["CPU Usage", f"{cpu_usage}%"],
            ["Memory", f"{mem_used}/{mem_total} MB ({mem_percent:.1f}%)"],
            ["Disk", f"{disk_used}/{disk_total} ({disk_percent})"],
            ["System Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        ]
        
        print(f"\n{Colors.CYAN}=== System Status ==={Colors.ENDC}")
        print(tabulate(system_data, tablefmt="grid"))
    except Exception as e:
        logger.error(f"Lỗi khi lấy trạng thái hệ thống: {e}")
        print(f"{Colors.RED}Lỗi khi lấy trạng thái hệ thống: {e}{Colors.ENDC}")

def show_help():
    """Hiển thị trợ giúp"""
    help_text = f"""
{Colors.CYAN}Hướng dẫn sử dụng CLI Controller:{Colors.ENDC}

{Colors.YELLOW}Lệnh:{Colors.ENDC}

  {Colors.GREEN}start{Colors.ENDC}           Khởi động bot
  {Colors.GREEN}stop{Colors.ENDC}            Dừng bot
  {Colors.GREEN}restart{Colors.ENDC}         Khởi động lại bot
  {Colors.GREEN}status{Colors.ENDC}          Hiển thị trạng thái hệ thống
  {Colors.GREEN}config{Colors.ENDC}          Hiển thị cấu hình hiện tại
  {Colors.GREEN}trades{Colors.ENDC}          Hiển thị giao dịch gần đây
  {Colors.GREEN}logs [n]{Colors.ENDC}        Hiển thị n dòng log gần nhất (mặc định: 50)
  {Colors.GREEN}help{Colors.ENDC}            Hiển thị trợ giúp này
  {Colors.GREEN}exit{Colors.ENDC}            Thoát CLI Controller

{Colors.YELLOW}Ví dụ:{Colors.ENDC}

  {Colors.GREEN}logs 100{Colors.ENDC}        Hiển thị 100 dòng log gần nhất
  {Colors.GREEN}status{Colors.ENDC}          Kiểm tra trạng thái hệ thống và bot
    """
    print(help_text)

def process_command(command):
    """Xử lý lệnh từ người dùng"""
    try:
        command = command.strip()
        parts = command.split()
        
        if not parts:
            return
            
        cmd = parts[0].lower()
        
        if cmd == "start":
            start_bot()
        elif cmd == "stop":
            stop_bot()
        elif cmd == "restart":
            restart_bot()
        elif cmd == "status":
            show_system_status()
        elif cmd == "config":
            show_config()
        elif cmd == "trades":
            view_recent_trades()
        elif cmd == "logs":
            num_lines = int(parts[1]) if len(parts) > 1 else 50
            show_logs(num_lines)
        elif cmd == "help":
            show_help()
        elif cmd == "exit" or cmd == "quit":
            print(f"{Colors.YELLOW}Thoát CLI Controller...{Colors.ENDC}")
            sys.exit(0)
        else:
            print(f"{Colors.RED}Lệnh không hợp lệ. Nhập 'help' để xem danh sách lệnh.{Colors.ENDC}")
    except Exception as e:
        logger.error(f"Lỗi khi xử lý lệnh: {e}")
        print(f"{Colors.RED}Lỗi khi xử lý lệnh: {e}{Colors.ENDC}")
        
def interactive_mode():
    """Chạy chế độ tương tác"""
    print_banner()
    show_system_status()
    print(f"\nNhập '{Colors.GREEN}help{Colors.ENDC}' để xem danh sách lệnh. Nhập '{Colors.GREEN}exit{Colors.ENDC}' để thoát.\n")
    
    while True:
        try:
            command = input(f"{Colors.BOLD}crypto-bot>{Colors.ENDC} ")
            process_command(command)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Thoát CLI Controller...{Colors.ENDC}")
            break
        except Exception as e:
            logger.error(f"Lỗi trong chế độ tương tác: {e}")
            print(f"{Colors.RED}Lỗi: {e}{Colors.ENDC}")

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='CLI Controller for Crypto Trading Bot')
    
    # Nhóm các lệnh không sử dụng tham số
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--start', action='store_true', help='Khởi động bot')
    group.add_argument('--stop', action='store_true', help='Dừng bot')
    group.add_argument('--restart', action='store_true', help='Khởi động lại bot')
    group.add_argument('--status', action='store_true', help='Hiển thị trạng thái hệ thống')
    group.add_argument('--config', action='store_true', help='Hiển thị cấu hình hiện tại')
    group.add_argument('--trades', action='store_true', help='Hiển thị giao dịch gần đây')
    
    # Nhóm lệnh với tham số
    parser.add_argument('--logs', type=int, metavar='N', help='Hiển thị N dòng log gần nhất')
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    # Nếu không có tham số, chạy chế độ tương tác
    if len(sys.argv) == 1:
        interactive_mode()
        return
    
    # Xử lý lệnh từ tham số
    if args.start:
        start_bot()
    elif args.stop:
        stop_bot()
    elif args.restart:
        restart_bot()
    elif args.status:
        print_banner()
        show_system_status()
    elif args.config:
        print_banner()
        show_config()
    elif args.trades:
        print_banner()
        view_recent_trades()
    elif args.logs is not None:
        print_banner()
        show_logs(args.logs)
    else:
        interactive_mode()

if __name__ == '__main__':
    main()