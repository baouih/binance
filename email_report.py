#!/usr/bin/env python3
"""
Gửi báo cáo qua email

Module này gửi các báo cáo về tín hiệu thị trường, hiệu suất giao dịch và tình trạng hoạt động 
của bot qua email, giúp người dùng theo dõi hoạt động của bot ngay cả khi không có kết nối với Telegram.
"""

import os
import json
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, List, Union, Optional
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailReporter:
    """Lớp gửi báo cáo qua email"""
    
    def __init__(self, smtp_server: str = None, smtp_port: int = None, 
                email_user: str = None, email_password: str = None):
        """
        Khởi tạo Email Reporter.
        
        Args:
            smtp_server (str, optional): Địa chỉ máy chủ SMTP
            smtp_port (int, optional): Cổng SMTP
            email_user (str, optional): Tên đăng nhập email
            email_password (str, optional): Mật khẩu email
        """
        self.smtp_server = smtp_server or os.environ.get('EMAIL_SMTP_SERVER')
        self.smtp_port = smtp_port or int(os.environ.get('EMAIL_SMTP_PORT', '587'))
        self.email_user = email_user or os.environ.get('EMAIL_USER')
        self.email_password = email_password or os.environ.get('EMAIL_PASSWORD')
        self.enabled = bool(self.smtp_server and self.smtp_port and self.email_user and self.email_password)
        
        if not self.enabled:
            logger.warning("Email không được kích hoạt. Thiếu thông tin kết nối.")
    
    def send_email(self, subject: str, to_email: str, html_content: str = None, 
                 text_content: str = None, attachments: List[str] = None) -> bool:
        """
        Gửi email.
        
        Args:
            subject (str): Tiêu đề email
            to_email (str): Địa chỉ email nhận
            html_content (str, optional): Nội dung HTML
            text_content (str, optional): Nội dung văn bản thuần
            attachments (List[str], optional): Danh sách đường dẫn đến file đính kèm
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            logger.warning("Email không được kích hoạt. Không thể gửi email.")
            return False
        
        if not html_content and not text_content:
            logger.error("Thiếu nội dung email. Cần cung cấp HTML hoặc văn bản thuần.")
            return False
        
        try:
            # Tạo message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = to_email
            
            # Thêm nội dung văn bản thuần
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # Thêm nội dung HTML
            if html_content:
                msg.attach(MIMEText(html_content, 'html'))
            
            # Thêm file đính kèm
            if attachments:
                for file_path in attachments:
                    try:
                        with open(file_path, 'rb') as f:
                            part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                        msg.attach(part)
                    except Exception as e:
                        logger.error(f"Lỗi khi đính kèm file {file_path}: {e}")
            
            # Kết nối SMTP và gửi email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.email_user, self.email_password)
                server.sendmail(self.email_user, to_email, msg.as_string())
            
            logger.info(f"Đã gửi email thành công đến {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi email: {e}")
            return False
    
    def send_daily_report(self, to_email: str, trading_state_file: str = "trading_state.json", 
                        report_images: List[str] = None) -> bool:
        """
        Gửi báo cáo giao dịch hàng ngày qua email.
        
        Args:
            to_email (str): Địa chỉ email nhận
            trading_state_file (str): Đường dẫn đến file trạng thái giao dịch
            report_images (List[str], optional): Danh sách đường dẫn đến hình ảnh báo cáo
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            # Tải dữ liệu giao dịch
            state = self._load_trading_state(trading_state_file)
            if not state:
                logger.error(f"Không thể tải dữ liệu giao dịch từ {trading_state_file}")
                return False
            
            # Lấy thời gian hiện tại
            timestamp = datetime.now()
            
            # Tạo nội dung báo cáo
            html_content = self._generate_html_report(state, timestamp)
            text_content = self._generate_text_report(state, timestamp)
            
            # Tạo tiêu đề email
            subject = f"Báo cáo giao dịch hàng ngày - {timestamp.strftime('%Y-%m-%d')}"
            
            # Gửi email
            return self.send_email(
                subject=subject,
                to_email=to_email,
                html_content=html_content,
                text_content=text_content,
                attachments=report_images
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo hàng ngày: {e}")
            return False
    
    def _load_trading_state(self, file_path: str) -> Dict:
        """
        Tải dữ liệu giao dịch từ file.
        
        Args:
            file_path (str): Đường dẫn đến file
            
        Returns:
            Dict: Dữ liệu giao dịch
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            else:
                # Tạo dữ liệu mẫu nếu không tìm thấy file
                return {
                    "current_balance": 10000.0,
                    "start_balance": 10000.0,
                    "open_positions": [],
                    "trade_history": [],
                    "last_update": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu giao dịch: {e}")
            return None
    
    def _generate_html_report(self, state: Dict, timestamp: datetime) -> str:
        """
        Tạo báo cáo HTML từ dữ liệu giao dịch.
        
        Args:
            state (Dict): Dữ liệu giao dịch
            timestamp (datetime): Thời gian báo cáo
            
        Returns:
            str: Nội dung HTML
        """
        # Lấy dữ liệu từ state
        current_balance = state.get('current_balance', 0)
        start_balance = state.get('start_balance', current_balance)
        open_positions = state.get('open_positions', [])
        trade_history = state.get('trade_history', [])
        
        # Tính toán thống kê
        total_trades = len(trade_history)
        winning_trades = sum(1 for trade in trade_history if trade.get('pnl', 0) > 0)
        losing_trades = sum(1 for trade in trade_history if trade.get('pnl', 0) < 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(trade.get('pnl', 0) for trade in trade_history if trade.get('pnl', 0) > 0)
        total_loss = sum(trade.get('pnl', 0) for trade in trade_history if trade.get('pnl', 0) < 0)
        
        # Lọc giao dịch trong ngày
        today = timestamp.date()
        today_trades = [
            trade for trade in trade_history 
            if datetime.fromisoformat(trade.get('exit_time', timestamp.isoformat())).date() == today
        ]
        
        today_profit = sum(trade.get('pnl', 0) for trade in today_trades if trade.get('pnl', 0) > 0)
        today_loss = sum(trade.get('pnl', 0) for trade in today_trades if trade.get('pnl', 0) < 0)
        today_net = today_profit + today_loss
        
        # Tạo HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Báo cáo giao dịch hàng ngày</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .summary-card {{
                    background-color: #f8f9fa;
                    border-radius: 5px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .metrics {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    margin: 20px 0;
                }}
                .metric {{
                    flex-basis: 48%;
                    background: #fff;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 15px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                .metric-title {{
                    font-size: 14px;
                    color: #7f8c8d;
                    margin-bottom: 5px;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .positive {{
                    color: #27ae60;
                }}
                .negative {{
                    color: #e74c3c;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #7f8c8d;
                    font-size: 12px;
                }}
                .position {{
                    margin-bottom: 20px;
                    padding: 15px;
                    background-color: #fff;
                    border-radius: 5px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                .position-header {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 10px;
                }}
                .position-symbol {{
                    font-weight: bold;
                    font-size: 18px;
                }}
                .position-type {{
                    font-weight: bold;
                }}
                .buy {{
                    color: #27ae60;
                }}
                .sell {{
                    color: #e74c3c;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Báo cáo giao dịch hàng ngày</h1>
                    <p>{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="summary-card">
                    <h2>Tổng quan tài khoản</h2>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-title">Số dư hiện tại</div>
                            <div class="metric-value">${current_balance:.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Lãi/Lỗ tổng</div>
                            <div class="metric-value {('positive' if current_balance > start_balance else 'negative')}">
                                ${current_balance - start_balance:.2f} ({(current_balance / start_balance - 1) * 100:.2f}%)
                            </div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Tỷ lệ thắng</div>
                            <div class="metric-value">{win_rate:.1f}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Tổng giao dịch</div>
                            <div class="metric-value">{total_trades}</div>
                        </div>
                    </div>
                </div>
                
                <div class="summary-card">
                    <h2>Hiệu suất hôm nay</h2>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-title">Lãi/Lỗ ròng</div>
                            <div class="metric-value {('positive' if today_net > 0 else 'negative')}">
                                ${today_net:.2f}
                            </div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Giao dịch hôm nay</div>
                            <div class="metric-value">{len(today_trades)}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Tổng lãi</div>
                            <div class="metric-value positive">${today_profit:.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Tổng lỗ</div>
                            <div class="metric-value negative">${today_loss:.2f}</div>
                        </div>
                    </div>
                </div>
        """
        
        # Thêm vị thế đang mở
        if open_positions:
            html += """
                <div class="summary-card">
                    <h2>Vị thế đang mở</h2>
            """
            
            for position in open_positions:
                symbol = position.get('symbol', '')
                pos_type = position.get('type', '').upper()
                side_class = 'buy' if pos_type == 'LONG' else 'sell'
                side_text = 'LONG' if pos_type == 'LONG' else 'SHORT'
                entry_price = position.get('entry_price', 0)
                current_price = position.get('current_price', 0)
                quantity = position.get('quantity', 0)
                pnl = position.get('pnl', 0)
                pnl_percent = position.get('pnl_percent', 0)
                entry_time = datetime.fromisoformat(position.get('entry_time', timestamp.isoformat()))
                
                html += f"""
                    <div class="position">
                        <div class="position-header">
                            <div class="position-symbol">{symbol}</div>
                            <div class="position-type {side_class}">{side_text}</div>
                        </div>
                        <div>
                            <p><strong>Giá vào:</strong> ${entry_price:.2f} | <strong>Giá hiện tại:</strong> ${current_price:.2f}</p>
                            <p><strong>Số lượng:</strong> {quantity}</p>
                            <p><strong>Thời gian vào:</strong> {entry_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                            <p><strong>Lãi/Lỗ:</strong> <span class="{('positive' if pnl >= 0 else 'negative')}">${pnl:.2f} ({pnl_percent:.2f}%)</span></p>
                        </div>
                    </div>
                """
            
            html += """
                </div>
            """
        else:
            html += """
                <div class="summary-card">
                    <h2>Vị thế đang mở</h2>
                    <p>Không có vị thế đang mở</p>
                </div>
            """
        
        # Thêm lịch sử giao dịch gần đây
        html += """
                <div class="summary-card">
                    <h2>Lịch sử giao dịch gần đây</h2>
        """
        
        if trade_history:
            html += """
                    <table>
                        <thead>
                            <tr>
                                <th>Cặp</th>
                                <th>Loại</th>
                                <th>Vào/Ra</th>
                                <th>Lãi/Lỗ</th>
                                <th>Thời gian</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            # Lấy 10 giao dịch gần nhất
            recent_trades = sorted(
                trade_history, 
                key=lambda x: datetime.fromisoformat(x.get('exit_time', timestamp.isoformat())),
                reverse=True
            )[:10]
            
            for trade in recent_trades:
                symbol = trade.get('symbol', '')
                trade_type = trade.get('type', '').upper()
                side_class = 'buy' if trade_type == 'LONG' else 'sell'
                entry_price = trade.get('entry_price', 0)
                exit_price = trade.get('exit_price', 0)
                pnl = trade.get('pnl', 0)
                exit_time = datetime.fromisoformat(trade.get('exit_time', timestamp.isoformat()))
                
                html += f"""
                            <tr>
                                <td>{symbol}</td>
                                <td class="{side_class}">{trade_type}</td>
                                <td>${entry_price:.2f} / ${exit_price:.2f}</td>
                                <td class="{('positive' if pnl >= 0 else 'negative')}">${pnl:.2f}</td>
                                <td>{exit_time.strftime('%Y-%m-%d %H:%M')}</td>
                            </tr>
                """
            
            html += """
                        </tbody>
                    </table>
            """
        else:
            html += """
                    <p>Chưa có giao dịch nào được thực hiện</p>
            """
        
        html += """
                </div>
                
                <div class="footer">
                    <p>Báo cáo này được tạo tự động bởi Crypto Trading Bot.</p>
                    <p>© 2025 Crypto Trading Bot. Mọi quyền được bảo lưu.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_text_report(self, state: Dict, timestamp: datetime) -> str:
        """
        Tạo báo cáo văn bản thuần từ dữ liệu giao dịch.
        
        Args:
            state (Dict): Dữ liệu giao dịch
            timestamp (datetime): Thời gian báo cáo
            
        Returns:
            str: Nội dung văn bản thuần
        """
        # Lấy dữ liệu từ state
        current_balance = state.get('current_balance', 0)
        start_balance = state.get('start_balance', current_balance)
        open_positions = state.get('open_positions', [])
        trade_history = state.get('trade_history', [])
        
        # Tính toán thống kê
        total_trades = len(trade_history)
        winning_trades = sum(1 for trade in trade_history if trade.get('pnl', 0) > 0)
        losing_trades = sum(1 for trade in trade_history if trade.get('pnl', 0) < 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(trade.get('pnl', 0) for trade in trade_history if trade.get('pnl', 0) > 0)
        total_loss = sum(trade.get('pnl', 0) for trade in trade_history if trade.get('pnl', 0) < 0)
        
        # Lọc giao dịch trong ngày
        today = timestamp.date()
        today_trades = [
            trade for trade in trade_history 
            if datetime.fromisoformat(trade.get('exit_time', timestamp.isoformat())).date() == today
        ]
        
        today_profit = sum(trade.get('pnl', 0) for trade in today_trades if trade.get('pnl', 0) > 0)
        today_loss = sum(trade.get('pnl', 0) for trade in today_trades if trade.get('pnl', 0) < 0)
        today_net = today_profit + today_loss
        
        # Tạo văn bản
        text = f"""
BÁO CÁO GIAO DỊCH HÀNG NGÀY
{timestamp.strftime('%Y-%m-%d %H:%M:%S')}

TỔNG QUAN TÀI KHOẢN
------------------
Số dư hiện tại: ${current_balance:.2f}
Lãi/Lỗ tổng: ${current_balance - start_balance:.2f} ({(current_balance / start_balance - 1) * 100:.2f}%)
Tỷ lệ thắng: {win_rate:.1f}%
Tổng giao dịch: {total_trades}

HIỆU SUẤT HÔM NAY
----------------
Lãi/Lỗ ròng: ${today_net:.2f}
Giao dịch hôm nay: {len(today_trades)}
Tổng lãi: ${today_profit:.2f}
Tổng lỗ: ${today_loss:.2f}
"""
        
        # Thêm vị thế đang mở
        text += """
VỊ THẾ ĐANG MỞ
------------
"""
        
        if open_positions:
            for position in open_positions:
                symbol = position.get('symbol', '')
                pos_type = position.get('type', '').upper()
                entry_price = position.get('entry_price', 0)
                current_price = position.get('current_price', 0)
                quantity = position.get('quantity', 0)
                pnl = position.get('pnl', 0)
                pnl_percent = position.get('pnl_percent', 0)
                entry_time = datetime.fromisoformat(position.get('entry_time', timestamp.isoformat()))
                
                text += f"""
{symbol} {pos_type}
Giá vào: ${entry_price:.2f} | Giá hiện tại: ${current_price:.2f}
Số lượng: {quantity}
Thời gian vào: {entry_time.strftime('%Y-%m-%d %H:%M:%S')}
Lãi/Lỗ: ${pnl:.2f} ({pnl_percent:.2f}%)
"""
        else:
            text += "Không có vị thế đang mở\n"
        
        # Thêm lịch sử giao dịch gần đây
        text += """
LỊCH SỬ GIAO DỊCH GẦN ĐÂY
----------------------
"""
        
        if trade_history:
            # Lấy 10 giao dịch gần nhất
            recent_trades = sorted(
                trade_history, 
                key=lambda x: datetime.fromisoformat(x.get('exit_time', timestamp.isoformat())),
                reverse=True
            )[:10]
            
            for trade in recent_trades:
                symbol = trade.get('symbol', '')
                trade_type = trade.get('type', '').upper()
                entry_price = trade.get('entry_price', 0)
                exit_price = trade.get('exit_price', 0)
                pnl = trade.get('pnl', 0)
                exit_time = datetime.fromisoformat(trade.get('exit_time', timestamp.isoformat()))
                
                text += f"""
{symbol} {trade_type}
Vào/Ra: ${entry_price:.2f} / ${exit_price:.2f}
Lãi/Lỗ: ${pnl:.2f}
Thời gian: {exit_time.strftime('%Y-%m-%d %H:%M')}
"""
        else:
            text += "Chưa có giao dịch nào được thực hiện\n"
        
        text += """

Báo cáo này được tạo tự động bởi Crypto Trading Bot.
© 2025 Crypto Trading Bot. Mọi quyền được bảo lưu.
"""
        
        return text
    
    def send_signal_report(self, to_email: str, signal_report_file: str = None, report_images: List[str] = None) -> bool:
        """
        Gửi báo cáo tín hiệu qua email.
        
        Args:
            to_email (str): Địa chỉ email nhận
            signal_report_file (str, optional): Đường dẫn đến file báo cáo tín hiệu
            report_images (List[str], optional): Danh sách đường dẫn đến hình ảnh báo cáo
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            # Lấy thời gian hiện tại
            timestamp = datetime.now()
            
            # Tạo tiêu đề email
            subject = f"Báo cáo tín hiệu thị trường - {timestamp.strftime('%Y-%m-%d %H:%M')}"
            
            # Tải báo cáo tín hiệu
            if signal_report_file and os.path.exists(signal_report_file):
                with open(signal_report_file, 'r') as f:
                    report = json.load(f)
            else:
                # Báo cáo mẫu nếu không tìm thấy file
                report = {
                    "timestamp": timestamp.isoformat(),
                    "signals": [
                        {
                            "symbol": "BTCUSDT",
                            "timeframe": "1h",
                            "signal": "BUY",
                            "confidence": 75.5,
                            "indicators": {
                                "rsi": 32.5,
                                "macd": "positive crossover",
                                "ema": "uptrend"
                            },
                            "price": 68000.0
                        }
                    ],
                    "market_sentiment": "neutral",
                    "summary": "Thị trường đang có dấu hiệu hồi phục sau khi chạm ngưỡng hỗ trợ"
                }
            
            # Tạo nội dung HTML
            html_content = self._generate_html_signal_report(report)
            
            # Gửi email
            return self.send_email(
                subject=subject,
                to_email=to_email,
                html_content=html_content,
                attachments=report_images
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo tín hiệu: {e}")
            return False
    
    def _generate_html_signal_report(self, report: Dict) -> str:
        """
        Tạo báo cáo HTML từ báo cáo tín hiệu.
        
        Args:
            report (Dict): Báo cáo tín hiệu
            
        Returns:
            str: Nội dung HTML
        """
        try:
            # Lấy dữ liệu từ báo cáo
            timestamp = datetime.fromisoformat(report.get('timestamp', datetime.now().isoformat()))
            signals = report.get('signals', [])
            market_sentiment = report.get('market_sentiment', 'neutral')
            summary = report.get('summary', 'Không có tóm tắt')
            
            # Xác định màu cho sentiment
            sentiment_color = "#3498db"  # neutral
            if market_sentiment == "bullish":
                sentiment_color = "#2ecc71"
            elif market_sentiment == "bearish":
                sentiment_color = "#e74c3c"
            
            # Tạo HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Báo cáo tín hiệu thị trường</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        color: #333;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #2c3e50;
                    }}
                    .container {{
                        max-width: 800px;
                        margin: 0 auto;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .card {{
                        background-color: #f8f9fa;
                        border-radius: 5px;
                        padding: 20px;
                        margin-bottom: 20px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    }}
                    .signal-card {{
                        background-color: #fff;
                        border-radius: 5px;
                        padding: 15px;
                        margin-bottom: 15px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    }}
                    .signal-header {{
                        display: flex;
                        justify-content: space-between;
                        margin-bottom: 10px;
                        border-bottom: 1px solid #eee;
                        padding-bottom: 10px;
                    }}
                    .signal-symbol {{
                        font-weight: bold;
                        font-size: 18px;
                    }}
                    .signal-timeframe {{
                        color: #7f8c8d;
                    }}
                    .signal-type {{
                        font-weight: bold;
                        padding: 5px 10px;
                        border-radius: 3px;
                    }}
                    .buy-signal {{
                        background-color: #e8f8f5;
                        color: #27ae60;
                    }}
                    .sell-signal {{
                        background-color: #fdedec;
                        color: #e74c3c;
                    }}
                    .neutral-signal {{
                        background-color: #f8f9fa;
                        color: #7f8c8d;
                    }}
                    .metrics {{
                        display: flex;
                        flex-wrap: wrap;
                        justify-content: space-between;
                        margin: 20px 0;
                    }}
                    .metric {{
                        flex-basis: 48%;
                        margin-bottom: 15px;
                    }}
                    .metric-title {{
                        font-size: 14px;
                        color: #7f8c8d;
                        margin-bottom: 5px;
                    }}
                    .metric-value {{
                        font-size: 16px;
                        font-weight: bold;
                    }}
                    .indicator-item {{
                        margin-bottom: 8px;
                    }}
                    .confidence-bar {{
                        height: 6px;
                        background-color: #ecf0f1;
                        border-radius: 3px;
                        margin-top: 8px;
                    }}
                    .confidence-value {{
                        height: 100%;
                        border-radius: 3px;
                    }}
                    .high-confidence {{
                        background-color: #27ae60;
                    }}
                    .medium-confidence {{
                        background-color: #f39c12;
                    }}
                    .low-confidence {{
                        background-color: #e74c3c;
                    }}
                    .sentiment-indicator {{
                        padding: 10px;
                        border-radius: 5px;
                        text-align: center;
                        color: white;
                        font-weight: bold;
                        margin-bottom: 15px;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                        color: #7f8c8d;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Báo cáo tín hiệu thị trường</h1>
                        <p>{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    
                    <div class="card">
                        <div class="sentiment-indicator" style="background-color: {sentiment_color};">
                            Tâm lý thị trường: {market_sentiment.upper()}
                        </div>
                        <h3>Tóm tắt thị trường</h3>
                        <p>{summary}</p>
                    </div>
                    
                    <div class="card">
                        <h2>Tín hiệu giao dịch</h2>
            """
            
            if signals:
                for signal in signals:
                    symbol = signal.get('symbol', '')
                    timeframe = signal.get('timeframe', '')
                    signal_type = signal.get('signal', '').upper()
                    confidence = signal.get('confidence', 0)
                    indicators = signal.get('indicators', {})
                    price = signal.get('price', 0)
                    
                    # Xác định màu và lớp cho tín hiệu
                    signal_class = "neutral-signal"
                    if signal_type == "BUY":
                        signal_class = "buy-signal"
                    elif signal_type == "SELL":
                        signal_class = "sell-signal"
                    
                    # Xác định lớp cho độ tin cậy
                    confidence_class = "medium-confidence"
                    if confidence >= 75:
                        confidence_class = "high-confidence"
                    elif confidence < 50:
                        confidence_class = "low-confidence"
                    
                    html += f"""
                        <div class="signal-card">
                            <div class="signal-header">
                                <div>
                                    <div class="signal-symbol">{symbol}</div>
                                    <div class="signal-timeframe">Khung TG: {timeframe}</div>
                                </div>
                                <div class="signal-type {signal_class}">{signal_type}</div>
                            </div>
                            
                            <div class="metrics">
                                <div class="metric">
                                    <div class="metric-title">Giá hiện tại</div>
                                    <div class="metric-value">${price:.2f}</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-title">Độ tin cậy</div>
                                    <div class="metric-value">{confidence:.1f}%</div>
                                    <div class="confidence-bar">
                                        <div class="confidence-value {confidence_class}" style="width: {confidence}%;"></div>
                                    </div>
                                </div>
                            </div>
                            
                            <h4>Chỉ báo</h4>
                    """
                    
                    for indicator, value in indicators.items():
                        html += f"""
                                <div class="indicator-item">
                                    <strong>{indicator.upper()}:</strong> {value}
                                </div>
                        """
                    
                    html += """
                        </div>
                    """
            else:
                html += """
                        <p>Không có tín hiệu giao dịch nào ở thời điểm này.</p>
                """
            
            html += """
                    </div>
                    
                    <div class="footer">
                        <p>Báo cáo này được tạo tự động bởi Crypto Trading Bot.</p>
                        <p>© 2025 Crypto Trading Bot. Mọi quyền được bảo lưu.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo HTML tín hiệu: {e}")
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Báo cáo tín hiệu thị trường</title>
            </head>
            <body>
                <h1>Báo cáo tín hiệu thị trường</h1>
                <p>Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Đã xảy ra lỗi khi tạo báo cáo chi tiết. Vui lòng kiểm tra lại hệ thống.</p>
            </body>
            </html>
            """

def main():
    """Hàm chính"""
    # Lấy thông tin kết nối từ biến môi trường
    smtp_server = os.environ.get('EMAIL_SMTP_SERVER')
    smtp_port = int(os.environ.get('EMAIL_SMTP_PORT', '587'))
    email_user = os.environ.get('EMAIL_USER')
    email_password = os.environ.get('EMAIL_PASSWORD')
    
    if not smtp_server or not email_user or not email_password:
        print("Thiếu thông tin kết nối email. Vui lòng thiết lập biến môi trường EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD")
        return
    
    # Khởi tạo EmailReporter
    reporter = EmailReporter(smtp_server, smtp_port, email_user, email_password)
    
    # Lấy địa chỉ email người nhận từ biến môi trường hoặc đối số
    recipient = os.environ.get('REPORT_EMAIL')
    if not recipient:
        print("Thiếu địa chỉ email người nhận. Vui lòng thiết lập biến môi trường REPORT_EMAIL")
        return
    
    # Gửi email test
    print(f"Gửi email test đến {recipient}...")
    success = reporter.send_email(
        subject="Test Email từ Crypto Trading Bot",
        to_email=recipient,
        html_content="<h1>Test Email</h1><p>Đây là email test từ Crypto Trading Bot.</p>",
        text_content="Test Email\n\nĐây là email test từ Crypto Trading Bot."
    )
    
    print(f"Kết quả: {'Thành công' if success else 'Thất bại'}")
    
    # Gửi báo cáo hàng ngày test
    print(f"Gửi báo cáo hàng ngày test đến {recipient}...")
    success = reporter.send_daily_report(recipient)
    print(f"Kết quả: {'Thành công' if success else 'Thất bại'}")
    
    # Gửi báo cáo tín hiệu test
    print(f"Gửi báo cáo tín hiệu test đến {recipient}...")
    success = reporter.send_signal_report(recipient)
    print(f"Kết quả: {'Thành công' if success else 'Thất bại'}")

if __name__ == "__main__":
    main()