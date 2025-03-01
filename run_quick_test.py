"""
Script chạy kiểm thử nhanh với dữ liệu đã tải
"""
import os
import sys
import logging
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quick_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("quick_test")

def run_quick_backtest():
    """Chạy backtest nhanh sử dụng dữ liệu đã tải"""
    # Kiểm tra dữ liệu BTC
    btc_data_file = 'test_data/BTCUSDT_1h.csv'
    
    if not os.path.exists(btc_data_file):
        logger.error(f"Không tìm thấy file dữ liệu {btc_data_file}")
        return False
    
    # Đọc dữ liệu
    try:
        df = pd.read_csv(btc_data_file)
        
        # Chuyển đổi timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"Đã tải dữ liệu: {len(df)} candles từ {df.index.min()} đến {df.index.max()}")
        
        # Thêm chỉ báo đơn giản
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['sma50'] = df['close'].rolling(window=50).mean()
        
        # Tạo tín hiệu đơn giản
        df['signal'] = 0
        df.loc[df['sma20'] > df['sma50'], 'signal'] = 1
        df.loc[df['sma20'] < df['sma50'], 'signal'] = -1
        
        # Loại bỏ NaN
        df = df.dropna()
        
        # Tính toán lợi nhuận
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        
        # Tính toán hiệu suất
        cumulative_returns = (1 + df['returns']).cumprod()
        cumulative_strategy_returns = (1 + df['strategy_returns']).cumprod()
        
        # Tạo báo cáo
        os.makedirs('test_results', exist_ok=True)
        os.makedirs('test_charts', exist_ok=True)
        
        # Tạo biểu đồ
        plt.figure(figsize=(12, 8))
        plt.plot(df.index, cumulative_returns, label='Buy and Hold')
        plt.plot(df.index, cumulative_strategy_returns, label='SMA Strategy')
        plt.title('BTC/USDT 1h - SMA Strategy Backtest')
        plt.xlabel('Ngày')
        plt.ylabel('Lợi nhuận tích lũy')
        plt.legend()
        plt.grid(True)
        
        # Lưu biểu đồ
        chart_path = 'test_charts/btc_quick_test.png'
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ: {chart_path}")
        
        # Tính các chỉ số hiệu suất
        total_returns = cumulative_returns.iloc[-1] - 1
        strategy_returns = cumulative_strategy_returns.iloc[-1] - 1
        
        max_drawdown = (cumulative_strategy_returns / cumulative_strategy_returns.cummax() - 1).min()
        
        win_trades = df.loc[df['strategy_returns'] > 0].shape[0]
        lose_trades = df.loc[df['strategy_returns'] < 0].shape[0]
        win_rate = win_trades / (win_trades + lose_trades) if win_trades + lose_trades > 0 else 0
        
        # Tạo báo cáo HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Báo cáo kiểm thử nhanh</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .chart {{ margin: 20px 0; max-width: 100%; }}
            </style>
        </head>
        <body>
            <h1>Báo cáo kiểm thử nhanh</h1>
            <p>Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Tổng quan</h2>
            <table>
                <tr>
                    <th>Cặp giao dịch</th>
                    <td>BTC/USDT</td>
                </tr>
                <tr>
                    <th>Khung thời gian</th>
                    <td>1h</td>
                </tr>
                <tr>
                    <th>Chiến lược</th>
                    <td>SMA Cross (20/50)</td>
                </tr>
                <tr>
                    <th>Thời gian kiểm thử</th>
                    <td>{df.index.min()} - {df.index.max()}</td>
                </tr>
            </table>
            
            <h2>Hiệu suất</h2>
            <table>
                <tr>
                    <th>Lợi nhuận Buy & Hold</th>
                    <td class="{'positive' if total_returns > 0 else 'negative'}">{total_returns:.2%}</td>
                </tr>
                <tr>
                    <th>Lợi nhuận chiến lược</th>
                    <td class="{'positive' if strategy_returns > 0 else 'negative'}">{strategy_returns:.2%}</td>
                </tr>
                <tr>
                    <th>Drawdown tối đa</th>
                    <td class="negative">{max_drawdown:.2%}</td>
                </tr>
                <tr>
                    <th>Tỷ lệ thắng</th>
                    <td>{win_rate:.2%}</td>
                </tr>
                <tr>
                    <th>Số giao dịch thắng</th>
                    <td>{win_trades}</td>
                </tr>
                <tr>
                    <th>Số giao dịch thua</th>
                    <td>{lose_trades}</td>
                </tr>
            </table>
            
            <h2>Biểu đồ</h2>
            <div class="chart">
                <img src="../test_charts/btc_quick_test.png" alt="BTC Backtest Chart" width="800">
            </div>
        </body>
        </html>
        """
        
        # Lưu báo cáo HTML
        report_path = 'test_results/btc_quick_report.html'
        with open(report_path, 'w') as f:
            f.write(html_content)
            
        logger.info(f"Đã tạo báo cáo: {report_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest nhanh: {str(e)}")
        return False

if __name__ == "__main__":
    if run_quick_backtest():
        print("Đã chạy kiểm thử nhanh thành công!")
        print("Báo cáo: test_results/btc_quick_report.html")
        print("Biểu đồ: test_charts/btc_quick_test.png")
    else:
        print("Có lỗi khi chạy kiểm thử nhanh!")