#!/usr/bin/env python3
"""
Gửi báo cáo qua email

Module này gửi các báo cáo về tín hiệu thị trường, hiệu suất giao dịch và tình trạng hoạt động 
của bot qua email, giúp người dùng theo dõi hoạt động của bot ngay cả khi không có kết nối với Telegram.
"""

import os
import logging
import json
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import Dict, List, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_report")

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
        # Lấy thông tin từ biến môi trường nếu không được cung cấp
        self.smtp_server = smtp_server or os.environ.get("EMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.environ.get("EMAIL_SMTP_PORT", "587"))
        self.email_user = email_user or os.environ.get("EMAIL_USER")
        self.email_password = email_password or os.environ.get("EMAIL_PASSWORD")
        
        # Kiểm tra cấu hình
        if not all([self.smtp_server, self.smtp_port, self.email_user, self.email_password]):
            logger.warning("Email reporter không được cấu hình đầy đủ")
            logger.warning("Đặt EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD trong biến môi trường để kích hoạt")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Email reporter đã được kích hoạt")
    
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
            logger.warning("Email reporter không được kích hoạt")
            return False
        
        try:
            # Tạo tin nhắn
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
                    if not os.path.exists(file_path):
                        logger.warning(f"File đính kèm không tồn tại: {file_path}")
                        continue
                    
                    # Xác định loại MIME dựa vào phần mở rộng
                    filename = os.path.basename(file_path)
                    extension = os.path.splitext(filename)[1].lower()
                    
                    with open(file_path, 'rb') as file:
                        file_data = file.read()
                        
                        if extension in ['.jpg', '.jpeg', '.png', '.gif']:
                            # Đính kèm hình ảnh
                            attachment = MIMEImage(file_data, name=filename)
                        else:
                            # Đính kèm file khác
                            attachment = MIMEApplication(file_data, Name=filename)
                            attachment['Content-Disposition'] = f'attachment; filename="{filename}"'
                        
                        msg.attach(attachment)
            
            # Kết nối và gửi email
            context = ssl.create_default_context()
            
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.email_user, self.email_password)
                    server.sendmail(self.email_user, to_email, msg.as_string())
                
                logger.info(f"Đã gửi email thành công đến {to_email}")
                return True
            
            except Exception as e:
                logger.error(f"Lỗi khi gửi email: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi tạo email: {str(e)}")
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
                logger.warning("Không thể tải dữ liệu giao dịch")
                return False
            
            # Tạo tiêu đề email
            now = datetime.now()
            subject = f"Báo cáo giao dịch hàng ngày - {now.strftime('%d/%m/%Y')}"
            
            # Tạo nội dung HTML
            html_content = self._generate_html_report(state, now)
            
            # Tạo nội dung văn bản thuần
            text_content = self._generate_text_report(state, now)
            
            # Danh sách file đính kèm
            attachments = report_images if report_images else []
            
            # Gửi email
            return self.send_email(subject, to_email, html_content, text_content, attachments)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo hàng ngày: {str(e)}")
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
                with open(file_path, "r") as f:
                    return json.load(f)
            else:
                logger.warning(f"File {file_path} không tồn tại")
                return {}
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu giao dịch: {str(e)}")
            return {}
    
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
        balance = state.get("balance", 0)
        positions = state.get("positions", [])
        trade_history = state.get("trade_history", [])
        
        # Tạo HTML cho vị thế
        positions_html = ""
        for pos in positions:
            profit_class = "text-success" if pos.get("pnl", 0) >= 0 else "text-danger"
            positions_html += f"""
            <tr>
                <td>{pos.get('symbol', 'N/A')}</td>
                <td>{pos.get('type', 'N/A')}</td>
                <td>${pos.get('entry_price', 0):.2f}</td>
                <td>${pos.get('current_price', 0):.2f}</td>
                <td>{pos.get('quantity', 0):.6f}</td>
                <td class="{profit_class}">${pos.get('pnl', 0):.2f} ({pos.get('pnl_pct', 0):.2f}%)</td>
            </tr>
            """
        
        if not positions:
            positions_html = '<tr><td colspan="6" class="text-center">Không có vị thế đang mở</td></tr>'
        
        # Tạo HTML cho lịch sử giao dịch (chỉ 10 giao dịch gần nhất)
        recent_trades = sorted(trade_history, key=lambda x: x.get('exit_time', ''), reverse=True)[:10]
        trades_html = ""
        
        for trade in recent_trades:
            profit_class = "text-success" if trade.get("pnl", 0) >= 0 else "text-danger"
            trades_html += f"""
            <tr>
                <td>{trade.get('symbol', 'N/A')}</td>
                <td>{trade.get('type', 'N/A')}</td>
                <td>${trade.get('entry_price', 0):.2f}</td>
                <td>${trade.get('exit_price', 0):.2f}</td>
                <td>{trade.get('exit_reason', 'N/A')}</td>
                <td class="{profit_class}">${trade.get('pnl', 0):.2f} ({trade.get('pnl_pct', 0):.2f}%)</td>
            </tr>
            """
        
        if not recent_trades:
            trades_html = '<tr><td colspan="6" class="text-center">Không có lịch sử giao dịch</td></tr>'
        
        # Tính hiệu suất
        winning_trades = sum(1 for trade in trade_history if trade.get("pnl", 0) > 0)
        total_trades = len(trade_history)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        realized_pnl = sum(trade.get("pnl", 0) for trade in trade_history)
        unrealized_pnl = sum(pos.get("pnl", 0) for pos in positions)
        
        # Tạo HTML đầy đủ
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
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
                .container {{
                    width: 100%;
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .card {{
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }}
                .card-header {{
                    background-color: #f8f9fa;
                    padding: 10px 15px;
                    border-bottom: 1px solid #ddd;
                    font-weight: bold;
                }}
                .card-body {{
                    padding: 15px;
                }}
                .table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .table th, .table td {{
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                    text-align: left;
                }}
                .table th {{
                    background-color: #f8f9fa;
                }}
                .text-center {{
                    text-align: center;
                }}
                .text-success {{
                    color: #28a745;
                }}
                .text-danger {{
                    color: #dc3545;
                }}
                .summary-box {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                .summary-item {{
                    flex: 1;
                    background-color: #f8f9fa;
                    border-radius: 5px;
                    padding: 15px;
                    text-align: center;
                }}
                .summary-item h3 {{
                    margin-top: 0;
                    margin-bottom: 10px;
                    font-size: 16px;
                    color: #666;
                }}
                .summary-item p {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #777;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Báo cáo giao dịch hàng ngày</h1>
                    <p>{timestamp.strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
                
                <div class="summary-box">
                    <div class="summary-item">
                        <h3>Số dư</h3>
                        <p>${balance:.2f}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Tỷ lệ thắng</h3>
                        <p>{win_rate:.2f}%</p>
                    </div>
                    <div class="summary-item">
                        <h3>P&L đã thực hiện</h3>
                        <p class="{('text-success' if realized_pnl >= 0 else 'text-danger')}">${realized_pnl:.2f}</p>
                    </div>
                    <div class="summary-item">
                        <h3>P&L chưa thực hiện</h3>
                        <p class="{('text-success' if unrealized_pnl >= 0 else 'text-danger')}">${unrealized_pnl:.2f}</p>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">Vị thế đang mở</div>
                    <div class="card-body" style="padding: 0;">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Loại</th>
                                    <th>Giá vào</th>
                                    <th>Giá hiện tại</th>
                                    <th>Số lượng</th>
                                    <th>P&L</th>
                                </tr>
                            </thead>
                            <tbody>
                                {positions_html}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">Giao dịch gần đây</div>
                    <div class="card-body" style="padding: 0;">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Loại</th>
                                    <th>Giá vào</th>
                                    <th>Giá thoát</th>
                                    <th>Lý do thoát</th>
                                    <th>P&L</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trades_html}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Báo cáo này được tạo tự động bởi Bot Trading</p>
                    <p>© {timestamp.year} Bot Trading</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
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
        balance = state.get("balance", 0)
        positions = state.get("positions", [])
        trade_history = state.get("trade_history", [])
        
        # Tính hiệu suất
        winning_trades = sum(1 for trade in trade_history if trade.get("pnl", 0) > 0)
        total_trades = len(trade_history)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        realized_pnl = sum(trade.get("pnl", 0) for trade in trade_history)
        unrealized_pnl = sum(pos.get("pnl", 0) for pos in positions)
        
        # Tạo báo cáo văn bản
        report = f"BÁO CÁO GIAO DỊCH HÀNG NGÀY\n"
        report += f"Thời gian: {timestamp.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        
        # Tổng quan
        report += f"TỔNG QUAN\n"
        report += f"Số dư: ${balance:.2f}\n"
        report += f"Tỷ lệ thắng: {win_rate:.2f}%\n"
        report += f"P&L đã thực hiện: ${realized_pnl:.2f}\n"
        report += f"P&L chưa thực hiện: ${unrealized_pnl:.2f}\n\n"
        
        # Vị thế đang mở
        report += f"VỊ THẾ ĐANG MỞ\n"
        if positions:
            for pos in positions:
                report += f"- {pos.get('symbol', 'N/A')} ({pos.get('type', 'N/A')})\n"
                report += f"  Giá vào: ${pos.get('entry_price', 0):.2f}, Giá hiện tại: ${pos.get('current_price', 0):.2f}\n"
                report += f"  Số lượng: {pos.get('quantity', 0):.6f}\n"
                report += f"  P&L: ${pos.get('pnl', 0):.2f} ({pos.get('pnl_pct', 0):.2f}%)\n"
        else:
            report += "Không có vị thế đang mở\n"
        
        report += "\n"
        
        # Giao dịch gần đây
        report += f"GIAO DỊCH GẦN ĐÂY\n"
        recent_trades = sorted(trade_history, key=lambda x: x.get('exit_time', ''), reverse=True)[:5]
        
        if recent_trades:
            for trade in recent_trades:
                report += f"- {trade.get('symbol', 'N/A')} ({trade.get('type', 'N/A')})\n"
                report += f"  Giá vào: ${trade.get('entry_price', 0):.2f}, Giá thoát: ${trade.get('exit_price', 0):.2f}\n"
                report += f"  Lý do thoát: {trade.get('exit_reason', 'N/A')}\n"
                report += f"  P&L: ${trade.get('pnl', 0):.2f} ({trade.get('pnl_pct', 0):.2f}%)\n"
        else:
            report += "Không có giao dịch gần đây\n"
        
        return report
    
    def send_signal_report(self, to_email: str, signal_report_file: str = None, report_images: List[str] = None) -> bool:
        """
        Gửi báo cáo tín hiệu thị trường qua email.
        
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
            # Tìm file báo cáo mới nhất nếu không được chỉ định
            if not signal_report_file:
                reports_folder = "reports"
                if os.path.exists(reports_folder):
                    signal_reports = [f for f in os.listdir(reports_folder) if f.startswith("signal_report_") and f.endswith(".json")]
                    if signal_reports:
                        signal_report_file = os.path.join(reports_folder, max(signal_reports, key=lambda x: os.path.getmtime(os.path.join(reports_folder, x))))
            
            if not signal_report_file or not os.path.exists(signal_report_file):
                logger.warning("Không tìm thấy file báo cáo tín hiệu")
                return False
            
            # Tải báo cáo tín hiệu
            with open(signal_report_file, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            # Tìm file tóm tắt tương ứng
            summary_file = signal_report_file.replace("signal_report_", "signal_summary_").replace(".json", ".txt")
            
            # Tạo tiêu đề email
            now = datetime.now()
            subject = f"Báo cáo tín hiệu thị trường - {now.strftime('%d/%m/%Y %H:%M')}"
            
            # Tạo nội dung HTML
            html_content = self._generate_html_signal_report(report)
            
            # Tạo nội dung văn bản thuần
            if os.path.exists(summary_file):
                with open(summary_file, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            else:
                text_content = "Xem báo cáo đầy đủ ở phiên bản HTML"
            
            # Danh sách file đính kèm
            attachments = []
            
            # Thêm biểu đồ nếu có
            if "charts" in report:
                chart_paths = report["charts"]
                for chart_name, chart_path in chart_paths.items():
                    if os.path.exists(chart_path):
                        attachments.append(chart_path)
            
            # Thêm các hình ảnh khác nếu có
            if report_images:
                for image_path in report_images:
                    if os.path.exists(image_path) and image_path not in attachments:
                        attachments.append(image_path)
            
            # Gửi email
            return self.send_email(subject, to_email, html_content, text_content, attachments)
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo tín hiệu: {str(e)}")
            return False
    
    def _generate_html_signal_report(self, report: Dict) -> str:
        """
        Tạo báo cáo HTML từ báo cáo tín hiệu.
        
        Args:
            report (Dict): Báo cáo tín hiệu
            
        Returns:
            str: Nội dung HTML
        """
        # Trích xuất dữ liệu từ báo cáo
        analysis = report.get("analysis", {})
        overview = analysis.get("overview", {})
        assets = analysis.get("assets", {})
        timestamp = datetime.fromisoformat(report.get("timestamp", datetime.now().isoformat()))
        
        # Tâm lý thị trường
        sentiment = overview.get("market_sentiment", "neutral")
        sentiment_text = {
            "bullish": "TÍCH CỰC 📈",
            "bearish": "TIÊU CỰC 📉",
            "neutral": "TRUNG TÍNH ↔️"
        }.get(sentiment, "KHÔNG XÁC ĐỊNH")
        
        # Tạo bảng assets
        assets_html = ""
        for symbol, data in assets.items():
            signal = data.get("signal", "neutral").upper()
            confidence = data.get("confidence", 0) * 100
            regime = data.get("market_regime", "unknown")
            trend = data.get("trend", "sideways")
            
            # Màu sắc dựa vào tín hiệu
            signal_class = "text-success" if signal == "BUY" else "text-danger" if signal == "SELL" else ""
            strong_class = " font-weight-bold" if data.get("strong_signal", False) else ""
            
            # Định dạng xu hướng
            trend_text = "tăng" if trend == "uptrend" else "giảm" if trend == "downtrend" else "đi ngang"
            
            # Định dạng chế độ thị trường
            regime_text = {
                "trending_up": "xu hướng tăng",
                "trending_down": "xu hướng giảm",
                "ranging": "sideway",
                "volatile": "biến động mạnh",
                "breakout": "breakout",
                "neutral": "trung tính"
            }.get(regime, regime)
            
            assets_html += f"""
            <tr>
                <td>{symbol}</td>
                <td class="{signal_class}{strong_class}">{signal}</td>
                <td>{confidence:.1f}%</td>
                <td>{regime_text}</td>
                <td>{trend_text}</td>
            </tr>
            """
        
        if not assets:
            assets_html = '<tr><td colspan="5" class="text-center">Không có dữ liệu tài sản</td></tr>'
        
        # Tạo bảng top tài sản
        top_assets_html = ""
        top_assets = overview.get("top_assets", [])
        
        for asset in top_assets:
            symbol = asset.get("symbol", "")
            signal = asset.get("signal", "").upper()
            confidence = asset.get("confidence", 0) * 100
            signal_class = "text-success" if signal == "BUY" else "text-danger" if signal == "SELL" else ""
            
            top_assets_html += f"""
            <tr>
                <td>{symbol}</td>
                <td class="{signal_class}">{signal}</td>
                <td>{confidence:.1f}%</td>
            </tr>
            """
        
        if not top_assets:
            top_assets_html = '<tr><td colspan="3" class="text-center">Không có dữ liệu top tài sản</td></tr>'
        
        # Tạo HTML đầy đủ
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
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
                .container {{
                    width: 100%;
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .card {{
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }}
                .card-header {{
                    background-color: #f8f9fa;
                    padding: 10px 15px;
                    border-bottom: 1px solid #ddd;
                    font-weight: bold;
                }}
                .card-body {{
                    padding: 15px;
                }}
                .table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .table th, .table td {{
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                    text-align: left;
                }}
                .table th {{
                    background-color: #f8f9fa;
                }}
                .text-center {{
                    text-align: center;
                }}
                .text-success {{
                    color: #28a745;
                }}
                .text-danger {{
                    color: #dc3545;
                }}
                .summary-box {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                .summary-item {{
                    flex: 1;
                    background-color: #f8f9fa;
                    border-radius: 5px;
                    padding: 15px;
                    text-align: center;
                }}
                .summary-item h3 {{
                    margin-top: 0;
                    margin-bottom: 10px;
                    font-size: 16px;
                    color: #666;
                }}
                .summary-item p {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #777;
                }}
                .sentiment-box {{
                    text-align: center;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .sentiment-bullish {{
                    background-color: rgba(40, 167, 69, 0.1);
                    color: #28a745;
                }}
                .sentiment-bearish {{
                    background-color: rgba(220, 53, 69, 0.1);
                    color: #dc3545;
                }}
                .sentiment-neutral {{
                    background-color: rgba(108, 117, 125, 0.1);
                    color: #6c757d;
                }}
                .font-weight-bold {{
                    font-weight: bold;
                }}
                .chart-container {{
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .chart-container img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Báo cáo tín hiệu thị trường</h1>
                    <p>{timestamp.strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
                
                <div class="sentiment-box sentiment-{sentiment}">
                    Tâm lý thị trường: {sentiment_text}
                </div>
                
                <div class="summary-box">
                    <div class="summary-item">
                        <h3>Tín hiệu mua</h3>
                        <p class="text-success">{overview.get('buy_signals', 0)}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Tín hiệu bán</h3>
                        <p class="text-danger">{overview.get('sell_signals', 0)}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Trung tính</h3>
                        <p>{overview.get('neutral_signals', 0)}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Tín hiệu mạnh</h3>
                        <p>{overview.get('strong_signals', 0)}</p>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">Top cặp giao dịch</div>
                    <div class="card-body" style="padding: 0;">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Tín hiệu</th>
                                    <th>Độ tin cậy</th>
                                </tr>
                            </thead>
                            <tbody>
                                {top_assets_html}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">Phân tích tất cả các cặp</div>
                    <div class="card-body" style="padding: 0;">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Tín hiệu</th>
                                    <th>Độ tin cậy</th>
                                    <th>Chế độ thị trường</th>
                                    <th>Xu hướng</th>
                                </tr>
                            </thead>
                            <tbody>
                                {assets_html}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Báo cáo này được tạo tự động bởi Bot Trading</p>
                    <p>© {timestamp.year} Bot Trading</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content

def main():
    """Hàm chính"""
    # Lấy thông tin từ biến môi trường
    to_email = os.environ.get("REPORT_EMAIL")
    if not to_email:
        logger.error("Không có địa chỉ email nhận báo cáo (REPORT_EMAIL)")
        return
    
    # Tạo email reporter
    reporter = EmailReporter()
    
    if not reporter.enabled:
        logger.error("Email reporter không được kích hoạt do thiếu cấu hình")
        return
    
    # Tạo các thư mục cần thiết
    os.makedirs("reports", exist_ok=True)
    
    # Gửi báo cáo hàng ngày
    if os.path.exists("trading_state.json"):
        reporter.send_daily_report(to_email)
        logger.info(f"Đã gửi báo cáo hàng ngày đến {to_email}")
    
    # Gửi báo cáo tín hiệu
    reporter.send_signal_report(to_email)
    logger.info(f"Đã gửi báo cáo tín hiệu đến {to_email}")
    
    print(f"Đã gửi báo cáo đến {to_email}")

if __name__ == "__main__":
    main()