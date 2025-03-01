"""
Script chạy học máy đơn giản để dự đoán xu hướng BTC
"""
import os
import sys
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_quick.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ml_quick")

def run_ml_prediction():
    """Chạy dự đoán xu hướng sử dụng ML"""
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
        
        # Thêm chỉ báo
        df['sma5'] = df['close'].rolling(window=5).mean()
        df['sma10'] = df['close'].rolling(window=10).mean()
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['sma50'] = df['close'].rolling(window=50).mean()
        
        df['ema5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema10'] = df['close'].ewm(span=10, adjust=False).mean()
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        
        # Tính RSI 14
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Tính biến động
        df['close_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        df['price_range'] = (df['high'] - df['low']) / df['close']
        
        # Tính tỷ lệ giá/SMA
        df['close_sma20_ratio'] = df['close'] / df['sma20']
        df['close_sma50_ratio'] = df['close'] / df['sma50']
        
        # Tạo mục tiêu: xu hướng 24h sau (1: tăng, 0: giảm)
        df['target'] = (df['close'].shift(-24) > df['close']).astype(int)
        
        # Loại bỏ NaN
        df = df.dropna()
        
        # Tạo đặc trưng
        features = [
            'sma5', 'sma10', 'sma20', 'sma50', 
            'ema5', 'ema10', 'ema20',
            'rsi', 'close_change', 'volume_change', 'price_range',
            'close_sma20_ratio', 'close_sma50_ratio'
        ]
        
        X = df[features].values
        y = df['target'].values
        
        # Chia dữ liệu thành tập huấn luyện và tập kiểm thử
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        # Chuẩn hóa dữ liệu
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Huấn luyện mô hình
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train_scaled, y_train)
        
        # Dự đoán
        y_pred = model.predict(X_test_scaled)
        
        # Đánh giá
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred)
        conf_matrix = confusion_matrix(y_test, y_pred)
        
        logger.info(f"Accuracy: {accuracy:.4f}")
        logger.info(f"Classification Report:\n{report}")
        
        # Tạo biểu đồ
        plt.figure(figsize=(12, 8))
        
        # Vẽ đường giá
        plt.subplot(2, 1, 1)
        plt.plot(df.index[-len(y_test):], df['close'].values[-len(y_test):], label='Giá BTC')
        plt.title('BTC/USDT 1h - Dự đoán xu hướng ML')
        plt.xlabel('Ngày')
        plt.ylabel('Giá')
        plt.legend()
        plt.grid(True)
        
        # Vẽ dự đoán
        plt.subplot(2, 1, 2)
        plt.plot(df.index[-len(y_test):], y_test, 'b-', label='Xu hướng thực tế')
        plt.plot(df.index[-len(y_test):], y_pred, 'r--', label='Xu hướng dự đoán')
        plt.xlabel('Ngày')
        plt.ylabel('Xu hướng (1: tăng, 0: giảm)')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        chart_path = 'test_charts/btc_ml_prediction.png'
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ dự đoán: {chart_path}")
        
        # Tính tầm quan trọng của đặc trưng
        feature_importance = pd.DataFrame({
            'feature': features,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Vẽ biểu đồ importance
        plt.figure(figsize=(10, 6))
        plt.barh(feature_importance['feature'], feature_importance['importance'])
        plt.title('Tầm quan trọng của các đặc trưng')
        plt.xlabel('Mức độ quan trọng')
        plt.tight_layout()
        
        # Lưu biểu đồ
        importance_path = 'test_charts/btc_feature_importance.png'
        plt.savefig(importance_path)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ tầm quan trọng: {importance_path}")
        
        # Lưu mô hình
        import joblib
        os.makedirs('models', exist_ok=True)
        model_path = 'models/btc_trend_prediction.joblib'
        scaler_path = 'models/btc_scaler.joblib'
        
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)
        
        logger.info(f"Đã lưu mô hình: {model_path}")
        
        # Dự đoán xu hướng cho 24h tới
        latest_data = df.iloc[-1:][features].values
        latest_scaled = scaler.transform(latest_data)
        prediction = model.predict(latest_scaled)[0]
        probability = model.predict_proba(latest_scaled)[0]
        
        logger.info(f"Dự đoán xu hướng 24h tới: {'Tăng' if prediction == 1 else 'Giảm'}")
        logger.info(f"Xác suất Tăng: {probability[1]:.4f}, Xác suất Giảm: {probability[0]:.4f}")
        
        # Tạo báo cáo HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Báo cáo dự đoán xu hướng</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .chart {{ margin: 20px 0; max-width: 100%; }}
                pre {{ background-color: #f5f5f5; padding: 10px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1>Báo cáo dự đoán xu hướng BTC</h1>
            <p>Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Tổng quan mô hình</h2>
            <table>
                <tr>
                    <th>Độ chính xác (Accuracy)</th>
                    <td>{accuracy:.2%}</td>
                </tr>
                <tr>
                    <th>Mô hình</th>
                    <td>Random Forest (100 cây)</td>
                </tr>
                <tr>
                    <th>Số lượng đặc trưng</th>
                    <td>{len(features)}</td>
                </tr>
            </table>
            
            <h2>Chi tiết đánh giá</h2>
            <pre>{report}</pre>
            
            <h2>Dự đoán gần nhất</h2>
            <table>
                <tr>
                    <th>Ngày giờ</th>
                    <td>{df.index[-1]}</td>
                </tr>
                <tr>
                    <th>Giá hiện tại</th>
                    <td>${df['close'].iloc[-1]:.2f}</td>
                </tr>
                <tr>
                    <th>Dự đoán 24h tới</th>
                    <td class="{'positive' if prediction == 1 else 'negative'}">{'Tăng' if prediction == 1 else 'Giảm'}</td>
                </tr>
                <tr>
                    <th>Xác suất tăng</th>
                    <td>{probability[1]:.2%}</td>
                </tr>
                <tr>
                    <th>Xác suất giảm</th>
                    <td>{probability[0]:.2%}</td>
                </tr>
            </table>
            
            <h2>Đặc trưng quan trọng nhất</h2>
            <table>
                <tr>
                    <th>Đặc trưng</th>
                    <th>Mức độ quan trọng</th>
                </tr>
                {''.join([f"<tr><td>{row['feature']}</td><td>{row['importance']:.4f}</td></tr>" for _, row in feature_importance.head(5).iterrows()])}
            </table>
            
            <h2>Biểu đồ dự đoán</h2>
            <div class="chart">
                <img src="../test_charts/btc_ml_prediction.png" alt="BTC Prediction Chart" width="800">
            </div>
            
            <h2>Tầm quan trọng của đặc trưng</h2>
            <div class="chart">
                <img src="../test_charts/btc_feature_importance.png" alt="Feature Importance Chart" width="800">
            </div>
        </body>
        </html>
        """
        
        # Lưu báo cáo HTML
        report_path = 'test_results/btc_ml_report.html'
        with open(report_path, 'w') as f:
            f.write(html_content)
            
        logger.info(f"Đã tạo báo cáo ML: {report_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy dự đoán ML: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    if run_ml_prediction():
        print("Đã chạy dự đoán ML thành công!")
        print("Báo cáo: test_results/btc_ml_report.html")
        print("Biểu đồ dự đoán: test_charts/btc_ml_prediction.png")
        print("Biểu đồ tầm quan trọng: test_charts/btc_feature_importance.png")
    else:
        print("Có lỗi khi chạy dự đoán ML!")