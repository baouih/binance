#!/usr/bin/env python3
"""
Tạo báo cáo hàng ngày về hiệu suất giao dịch
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("daily_report")

def load_trading_state():
    """Tải dữ liệu giao dịch từ file"""
    try:
        if os.path.exists("trading_state.json"):
            with open("trading_state.json", "r") as f:
                state = json.load(f)
                return state
        else:
            logger.error("File trading_state.json không tồn tại")
            return None
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu giao dịch: {e}")
        return None

def generate_performance_summary(state):
    """Tạo tóm tắt hiệu suất"""
    if not state:
        return "Không có dữ liệu giao dịch"
    
    balance = state.get("balance", 0)
    positions = state.get("positions", [])
    trade_history = state.get("trade_history", [])
    
    # Tính tổng P&L hiện tại
    current_pnl = sum(position.get("pnl", 0) for position in positions)
    
    # Tính P&L đã thực hiện
    realized_pnl = 0
    for trade in trade_history:
        if "pnl" in trade:
            realized_pnl += trade["pnl"]
    
    # Tính tổng P&L
    total_pnl = current_pnl + realized_pnl
    
    # Tỷ lệ thắng/thua
    winning_trades = sum(1 for trade in trade_history if trade.get("pnl", 0) > 0)
    total_trades = len(trade_history)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Tính P&L trung bình mỗi giao dịch
    avg_pnl = realized_pnl / total_trades if total_trades > 0 else 0
    
    # Giao dịch lớn nhất
    if trade_history:
        best_trade = max(trade_history, key=lambda x: x.get("pnl", 0)) if trade_history else None
        worst_trade = min(trade_history, key=lambda x: x.get("pnl", 0)) if trade_history else None
    else:
        best_trade = worst_trade = None
    
    # Tạo báo cáo
    report = {
        "timestamp": datetime.now().isoformat(),
        "balance": balance,
        "active_positions": len(positions),
        "total_trades_closed": total_trades,
        "win_rate": win_rate,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": current_pnl,
        "total_pnl": total_pnl,
        "avg_trade_pnl": avg_pnl,
        "best_trade": best_trade,
        "worst_trade": worst_trade
    }
    
    return report

def create_performance_chart(state):
    """Tạo biểu đồ hiệu suất"""
    if not state or "trade_history" not in state or not state["trade_history"]:
        logger.warning("Không đủ dữ liệu để tạo biểu đồ")
        return
    
    trade_history = state["trade_history"]
    
    # Tạo DataFrame từ lịch sử giao dịch
    df = pd.DataFrame(trade_history)
    
    # Chuyển đổi chuỗi thời gian thành đối tượng datetime
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    
    # Sắp xếp theo thời gian
    df = df.sort_values("exit_time")
    
    # Tính P&L tích lũy
    df["cumulative_pnl"] = df["pnl"].cumsum()
    
    # Tính số dư tăng dần (bắt đầu từ 10000)
    initial_balance = 10000
    df["balance"] = initial_balance + df["cumulative_pnl"]
    
    # Vẽ biểu đồ
    plt.figure(figsize=(10, 6))
    
    # Vẽ số dư
    plt.plot(df["exit_time"], df["balance"], marker='o', linestyle='-', linewidth=2, label='Số dư')
    
    # Vẽ P&L tích lũy
    plt.plot(df["exit_time"], df["cumulative_pnl"], marker='x', linestyle='--', linewidth=1, label='P&L tích lũy')
    
    # Thêm đường cơ sở
    plt.axhline(y=initial_balance, color='r', linestyle=':', label='Số dư ban đầu')
    
    plt.title('Biểu đồ hiệu suất giao dịch')
    plt.xlabel('Thời gian')
    plt.ylabel('Giá trị tài khoản (USDT)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Xoay nhãn trục x để dễ đọc
    plt.xticks(rotation=45)
    
    # Tự động điều chỉnh khoảng cách
    plt.tight_layout()
    
    # Lưu biểu đồ
    plt.savefig('trading_performance.png')
    logger.info("Đã tạo biểu đồ hiệu suất")

def generate_html_report(report, state):
    """Tạo báo cáo HTML"""
    if not report:
        return "<h1>Không có dữ liệu báo cáo</h1>"
    
    positions = state.get("positions", [])
    trade_history = state.get("trade_history", [])
    
    # Định dạng timestamp
    report_time = datetime.fromisoformat(report["timestamp"])
    formatted_time = report_time.strftime("%d/%m/%Y %H:%M:%S")
    
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
    
    # Tạo HTML cho lịch sử giao dịch (chỉ 5 giao dịch gần nhất)
    recent_trades = sorted(trade_history, key=lambda x: x.get('exit_time', ''), reverse=True)[:5]
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
    
    # Tạo HTML cho best/worst trade
    best_trade_html = ""
    worst_trade_html = ""
    
    if report.get("best_trade"):
        best = report["best_trade"]
        best_trade_html = f"""
        <div class="col-md-6">
            <div class="card border-success mb-3">
                <div class="card-header bg-success text-white">Giao dịch tốt nhất</div>
                <div class="card-body">
                    <h5 class="card-title">{best.get('symbol', 'N/A')} {best.get('type', 'N/A')}</h5>
                    <p class="card-text">
                        Giá vào: ${best.get('entry_price', 0):.2f}<br>
                        Giá ra: ${best.get('exit_price', 0):.2f}<br>
                        P&L: $<span class="text-success">{best.get('pnl', 0):.2f}</span> ({best.get('pnl_pct', 0):.2f}%)<br>
                        Lý do thoát: {best.get('exit_reason', 'N/A')}
                    </p>
                </div>
            </div>
        </div>
        """
    
    if report.get("worst_trade"):
        worst = report["worst_trade"]
        worst_trade_html = f"""
        <div class="col-md-6">
            <div class="card border-danger mb-3">
                <div class="card-header bg-danger text-white">Giao dịch tệ nhất</div>
                <div class="card-body">
                    <h5 class="card-title">{worst.get('symbol', 'N/A')} {worst.get('type', 'N/A')}</h5>
                    <p class="card-text">
                        Giá vào: ${worst.get('entry_price', 0):.2f}<br>
                        Giá ra: ${worst.get('exit_price', 0):.2f}<br>
                        P&L: $<span class="text-danger">{worst.get('pnl', 0):.2f}</span> ({worst.get('pnl_pct', 0):.2f}%)<br>
                        Lý do thoát: {worst.get('exit_reason', 'N/A')}
                    </p>
                </div>
            </div>
        </div>
        """
    
    # Tạo HTML đầy đủ
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Báo cáo giao dịch hàng ngày</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            body {{
                padding: 20px;
            }}
            .performance-chart {{
                width: 100%;
                max-width: 800px;
                margin: 0 auto;
            }}
        </style>
    </head>
    <body data-bs-theme="dark">
        <div class="container">
            <h1 class="text-center mb-4">Báo cáo giao dịch bot tự động</h1>
            <p class="text-center text-muted">Thời gian báo cáo: {formatted_time}</p>
            
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">Tổng quan tài khoản</div>
                        <div class="card-body">
                            <h2 class="card-title">${report.get('balance', 0):.2f}</h2>
                            <p class="card-text">
                                P&L đã thực hiện: $<span class="{('text-success' if report.get('realized_pnl', 0) >= 0 else 'text-danger')}">{report.get('realized_pnl', 0):.2f}</span><br>
                                P&L chưa thực hiện: $<span class="{('text-success' if report.get('unrealized_pnl', 0) >= 0 else 'text-danger')}">{report.get('unrealized_pnl', 0):.2f}</span><br>
                                Tổng P&L: $<span class="{('text-success' if report.get('total_pnl', 0) >= 0 else 'text-danger')}">{report.get('total_pnl', 0):.2f}</span>
                            </p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">Hiệu suất giao dịch</div>
                        <div class="card-body">
                            <h4 class="card-title">Tỷ lệ thắng: {report.get('win_rate', 0):.2f}%</h4>
                            <p class="card-text">
                                Tổng giao dịch đã đóng: {report.get('total_trades_closed', 0)}<br>
                                P&L trung bình/giao dịch: ${report.get('avg_trade_pnl', 0):.2f}<br>
                                Vị thế đang mở: {report.get('active_positions', 0)}
                            </p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">Trạng thái Bot</div>
                        <div class="card-body">
                            <h4 class="card-title text-success">Đang chạy</h4>
                            <p class="card-text">
                                Bot đang hoạt động và huấn luyện<br>
                                Chu kỳ huấn luyện: 4 giờ<br>
                                Báo cáo tiếp theo: 24 giờ
                            </p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">Biểu đồ hiệu suất</div>
                        <div class="card-body text-center">
                            <img src="trading_performance.png" class="performance-chart img-fluid" alt="Biểu đồ hiệu suất">
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                {best_trade_html}
                {worst_trade_html}
            </div>
            
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">Vị thế đang mở</div>
                        <div class="card-body p-0">
                            <div class="table-responsive">
                                <table class="table table-hover mb-0">
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
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">Giao dịch gần đây</div>
                        <div class="card-body p-0">
                            <div class="table-responsive">
                                <table class="table table-hover mb-0">
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
                    </div>
                </div>
            </div>
            
            <div class="text-center text-muted mt-4">
                <p>Báo cáo này được tạo tự động bởi Bot Trading</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def save_html_report(html_content, file_path="trading_report.html"):
    """Lưu báo cáo HTML vào file"""
    try:
        with open(file_path, "w") as f:
            f.write(html_content)
        logger.info(f"Đã lưu báo cáo HTML vào {file_path}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu báo cáo HTML: {e}")

def main():
    """Hàm chính để tạo báo cáo"""
    logger.info("Bắt đầu tạo báo cáo hàng ngày")
    
    # Tải dữ liệu giao dịch
    state = load_trading_state()
    if not state:
        logger.error("Không thể tạo báo cáo do không có dữ liệu giao dịch")
        return
    
    # Tạo biểu đồ hiệu suất
    create_performance_chart(state)
    
    # Tạo tóm tắt hiệu suất
    report = generate_performance_summary(state)
    
    # Tạo báo cáo HTML
    html_content = generate_html_report(report, state)
    
    # Lưu báo cáo HTML
    save_html_report(html_content)
    
    logger.info("Hoàn tất tạo báo cáo hàng ngày")

if __name__ == "__main__":
    main()