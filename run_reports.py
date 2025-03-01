#!/usr/bin/env python3
"""
Script chạy tất cả các báo cáo và gửi qua Telegram/Email

Script này sẽ chạy tất cả các báo cáo (hàng ngày, tín hiệu, huấn luyện, thị trường)
và gửi chúng qua Telegram và Email (nếu được cấu hình).
"""

import os
import json
import logging
import argparse
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_reports")

def create_directories():
    """Tạo các thư mục cần thiết nếu chưa tồn tại"""
    dirs = ["data", "reports", "reports/charts", "logs", "models"]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

def run_daily_report():
    """Chạy báo cáo hàng ngày"""
    try:
        logger.info("Đang tạo báo cáo hàng ngày...")
        from daily_report import main as generate_daily_report
        generate_daily_report()
        logger.info("Đã tạo báo cáo hàng ngày thành công")
        return True
    except ImportError:
        logger.error("Không thể import module daily_report")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo hàng ngày: {e}")
        return False

def run_signal_report():
    """Chạy báo cáo tín hiệu thị trường"""
    try:
        logger.info("Đang tạo báo cáo tín hiệu thị trường...")
        from signal_report import main as generate_signal_report
        generate_signal_report()
        logger.info("Đã tạo báo cáo tín hiệu thị trường thành công")
        return True
    except ImportError:
        logger.error("Không thể import module signal_report")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo tín hiệu thị trường: {e}")
        return False

def run_training_report():
    """Chạy báo cáo huấn luyện mô hình"""
    try:
        logger.info("Đang tạo báo cáo huấn luyện mô hình...")
        from training_report import main as generate_training_report
        generate_training_report()
        logger.info("Đã tạo báo cáo huấn luyện mô hình thành công")
        return True
    except ImportError:
        logger.error("Không thể import module training_report")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo huấn luyện mô hình: {e}")
        return False

def run_market_report(symbols=None):
    """
    Chạy báo cáo phân tích thị trường
    
    Args:
        symbols (list): Danh sách các cặp giao dịch cần phân tích
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT"]
    
    try:
        logger.info("Đang tạo báo cáo phân tích thị trường...")
        from market_report import main as generate_market_report
        
        # Gọi hàm main với tham số symbols
        generate_market_report(symbols)
        
        logger.info("Đã tạo báo cáo phân tích thị trường thành công")
        return True
    except ImportError:
        logger.error("Không thể import module market_report")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo phân tích thị trường: {e}")
        return False

def send_email_reports(recipient=None, report_types=None):
    """
    Gửi báo cáo qua email
    
    Args:
        recipient (str): Địa chỉ email nhận
        report_types (list): Danh sách các loại báo cáo cần gửi
    """
    if report_types is None:
        report_types = ["daily", "signal", "market"]
    
    if recipient is None:
        # Lấy từ biến môi trường
        recipient = os.environ.get("REPORT_EMAIL")
        if not recipient:
            logger.error("Không có địa chỉ email nhận. Vui lòng đặt REPORT_EMAIL hoặc cung cấp qua tham số")
            return False
    
    try:
        logger.info(f"Đang gửi báo cáo qua email đến {recipient}...")
        from email_report import EmailReporter
        
        reporter = EmailReporter()
        
        if not reporter.enabled:
            logger.error("EmailReporter không được kích hoạt. Kiểm tra cấu hình SMTP")
            return False
        
        success = True
        
        # Gửi báo cáo hàng ngày
        if "daily" in report_types:
            if reporter.send_daily_report(recipient):
                logger.info("Đã gửi báo cáo hàng ngày qua email")
            else:
                logger.error("Lỗi khi gửi báo cáo hàng ngày qua email")
                success = False
        
        # Gửi báo cáo tín hiệu
        if "signal" in report_types:
            if reporter.send_signal_report(recipient):
                logger.info("Đã gửi báo cáo tín hiệu qua email")
            else:
                logger.error("Lỗi khi gửi báo cáo tín hiệu qua email")
                success = False
        
        # Gửi báo cáo thị trường (chưa có phương thức cụ thể trong EmailReporter)
        if "market" in report_types and hasattr(reporter, "send_market_report"):
            if reporter.send_market_report(recipient):
                logger.info("Đã gửi báo cáo thị trường qua email")
            else:
                logger.error("Lỗi khi gửi báo cáo thị trường qua email")
                success = False
        
        # Gửi báo cáo huấn luyện (chưa có phương thức cụ thể trong EmailReporter)
        if "training" in report_types and hasattr(reporter, "send_training_report"):
            if reporter.send_training_report(recipient):
                logger.info("Đã gửi báo cáo huấn luyện qua email")
            else:
                logger.error("Lỗi khi gửi báo cáo huấn luyện qua email")
                success = False
        
        return success
    
    except ImportError:
        logger.error("Không thể import module email_report")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi gửi báo cáo qua email: {e}")
        return False

def send_telegram_reports(report_types=None):
    """
    Gửi báo cáo qua Telegram
    
    Args:
        report_types (list): Danh sách các loại báo cáo cần gửi
    """
    if report_types is None:
        report_types = ["daily", "signal", "market"]
    
    try:
        logger.info("Đang gửi báo cáo qua Telegram...")
        
        # Import TelegramNotifier
        try:
            from telegram_notify import telegram_notifier
            
            if not telegram_notifier or not telegram_notifier.enabled:
                logger.error("TelegramNotifier không được kích hoạt. Kiểm tra cấu hình token và chat_id")
                return False
        except ImportError:
            logger.error("Không thể import telegram_notifier")
            return False
        
        success = True
        
        # Gửi báo cáo hàng ngày qua Telegram
        if "daily" in report_types:
            try:
                # Tải trạng thái giao dịch
                with open("trading_state.json", "r") as f:
                    state = json.load(f)
                
                # Tính hiệu suất
                balance = state.get("balance", 0)
                positions = state.get("positions", [])
                trade_history = state.get("trade_history", [])
                
                winning_trades = sum(1 for trade in trade_history if trade.get("pnl", 0) > 0)
                total_trades = len(trade_history)
                win_rate = (winning_trades / total_trades) if total_trades > 0 else 0
                
                # Tạo dữ liệu báo cáo
                performance_data = {
                    "current_balance": balance,
                    "daily_pnl": sum(trade.get("pnl", 0) for trade in trade_history if 
                                   datetime.fromisoformat(trade.get("exit_time", datetime.now().isoformat())).date() == datetime.now().date()),
                    "daily_trades": sum(1 for trade in trade_history if 
                                      datetime.fromisoformat(trade.get("exit_time", datetime.now().isoformat())).date() == datetime.now().date()),
                    "win_rate": win_rate,
                    "open_positions": positions
                }
                
                # Gửi báo cáo
                if telegram_notifier.send_daily_report(performance_data):
                    logger.info("Đã gửi báo cáo hàng ngày qua Telegram")
                else:
                    logger.error("Lỗi khi gửi báo cáo hàng ngày qua Telegram")
                    success = False
            
            except Exception as e:
                logger.error(f"Lỗi khi gửi báo cáo hàng ngày qua Telegram: {e}")
                success = False
        
        # Gửi báo cáo tín hiệu qua Telegram
        if "signal" in report_types:
            try:
                from signal_report import SignalReporter
                reporter = SignalReporter()
                report = reporter.generate_signal_report()
                
                if report:
                    if reporter.send_telegram_notification(report):
                        logger.info("Đã gửi báo cáo tín hiệu qua Telegram")
                    else:
                        logger.error("Lỗi khi gửi báo cáo tín hiệu qua Telegram")
                        success = False
                else:
                    logger.error("Không thể tạo báo cáo tín hiệu")
                    success = False
            
            except ImportError:
                logger.error("Không thể import SignalReporter")
                success = False
            except Exception as e:
                logger.error(f"Lỗi khi gửi báo cáo tín hiệu qua Telegram: {e}")
                success = False
        
        # Gửi báo cáo thị trường qua Telegram
        if "market" in report_types:
            try:
                from market_report import MarketReporter
                reporter = MarketReporter()
                
                # Mặc định phân tích BTC và ETH
                symbols = ["BTCUSDT", "ETHUSDT"]
                
                for symbol in symbols:
                    report = reporter.generate_market_report(symbol)
                    if report:
                        if reporter.send_telegram_notification(report):
                            logger.info(f"Đã gửi báo cáo thị trường {symbol} qua Telegram")
                        else:
                            logger.error(f"Lỗi khi gửi báo cáo thị trường {symbol} qua Telegram")
                            success = False
                    else:
                        logger.error(f"Không thể tạo báo cáo thị trường cho {symbol}")
                        success = False
            
            except ImportError:
                logger.error("Không thể import MarketReporter")
                success = False
            except Exception as e:
                logger.error(f"Lỗi khi gửi báo cáo thị trường qua Telegram: {e}")
                success = False
        
        # Gửi báo cáo huấn luyện qua Telegram
        if "training" in report_types:
            try:
                from training_report import TrainingReporter
                reporter = TrainingReporter()
                report = reporter.generate_training_report()
                
                if report:
                    if reporter.send_telegram_notification(report):
                        logger.info("Đã gửi báo cáo huấn luyện qua Telegram")
                    else:
                        logger.error("Lỗi khi gửi báo cáo huấn luyện qua Telegram")
                        success = False
                else:
                    logger.error("Không thể tạo báo cáo huấn luyện")
                    success = False
            
            except ImportError:
                logger.error("Không thể import TrainingReporter")
                success = False
            except Exception as e:
                logger.error(f"Lỗi khi gửi báo cáo huấn luyện qua Telegram: {e}")
                success = False
        
        return success
    
    except Exception as e:
        logger.error(f"Lỗi khi gửi báo cáo qua Telegram: {e}")
        return False

def main():
    """Hàm chính"""
    # Tạo ArgumentParser
    parser = argparse.ArgumentParser(description='Chạy và gửi báo cáo hệ thống giao dịch')
    
    # Thêm các tham số
    parser.add_argument('--daily', action='store_true', help='Tạo báo cáo hàng ngày')
    parser.add_argument('--signal', action='store_true', help='Tạo báo cáo tín hiệu')
    parser.add_argument('--market', action='store_true', help='Tạo báo cáo thị trường')
    parser.add_argument('--training', action='store_true', help='Tạo báo cáo huấn luyện')
    parser.add_argument('--all', action='store_true', help='Tạo tất cả các báo cáo')
    parser.add_argument('--email', type=str, help='Gửi báo cáo qua email (nhập địa chỉ email)')
    parser.add_argument('--telegram', action='store_true', help='Gửi báo cáo qua Telegram')
    parser.add_argument('--symbols', type=str, nargs='+', default=['BTCUSDT', 'ETHUSDT'],
                       help='Danh sách các cặp giao dịch cần phân tích (cho báo cáo thị trường)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Tạo thư mục cần thiết
    create_directories()
    
    # Danh sách các loại báo cáo sẽ tạo
    report_types = []
    
    # Xác định các loại báo cáo cần tạo
    if args.all:
        args.daily = args.signal = args.market = args.training = True
    
    # Tạo báo cáo hàng ngày
    if args.daily:
        report_types.append("daily")
        if run_daily_report():
            logger.info("Đã tạo báo cáo hàng ngày")
    
    # Tạo báo cáo tín hiệu
    if args.signal:
        report_types.append("signal")
        if run_signal_report():
            logger.info("Đã tạo báo cáo tín hiệu")
    
    # Tạo báo cáo thị trường
    if args.market:
        report_types.append("market")
        if run_market_report(args.symbols):
            logger.info(f"Đã tạo báo cáo thị trường cho {', '.join(args.symbols)}")
    
    # Tạo báo cáo huấn luyện
    if args.training:
        report_types.append("training")
        if run_training_report():
            logger.info("Đã tạo báo cáo huấn luyện")
    
    # Gửi báo cáo qua email nếu được yêu cầu
    if args.email:
        if send_email_reports(args.email, report_types):
            logger.info(f"Đã gửi báo cáo qua email đến {args.email}")
    
    # Gửi báo cáo qua Telegram nếu được yêu cầu
    if args.telegram:
        if send_telegram_reports(report_types):
            logger.info("Đã gửi báo cáo qua Telegram")

if __name__ == "__main__":
    main()