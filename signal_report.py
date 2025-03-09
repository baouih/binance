#!/usr/bin/env python3
"""
Tạo báo cáo tín hiệu thị trường

Module này tạo báo cáo chi tiết về các tín hiệu thị trường, nhận định và phân tích
từ những dữ liệu giao dịch, giúp người dùng nắm bắt được diễn biến thị trường và
đưa ra quyết định giao dịch tốt hơn.
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import matplotlib.pyplot as plt

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("signal_report")

# Import telegram notifier
from telegram_notify import telegram_notifier

class SignalReporter:
    """Lớp tạo báo cáo tín hiệu thị trường"""
    
    def __init__(self, data_folder="./data", report_folder="./reports", state_file="trading_state.json"):
        """
        Khởi tạo Signal Reporter.
        
        Args:
            data_folder (str): Thư mục chứa dữ liệu thị trường
            report_folder (str): Thư mục lưu báo cáo
            state_file (str): File trạng thái giao dịch
        """
        self.data_folder = data_folder
        self.report_folder = report_folder
        self.state_file = state_file
        
        # Tạo thư mục nếu chưa tồn tại
        for folder in [data_folder, report_folder]:
            os.makedirs(folder, exist_ok=True)
    
    def load_trading_state(self) -> Dict:
        """
        Tải trạng thái giao dịch.
        
        Returns:
            Dict: Trạng thái giao dịch
        """
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    return json.load(f)
            else:
                logger.warning(f"File {self.state_file} không tồn tại")
                return {}
        except Exception as e:
            logger.error(f"Lỗi khi tải trạng thái giao dịch: {e}")
            return {}
    
    def load_market_data(self, symbol: str, timeframe: str) -> Dict:
        """
        Tải dữ liệu thị trường cho một cặp giao dịch.
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            
        Returns:
            Dict: Dữ liệu thị trường
        """
        try:
            # Cấu trúc tên file: symbol_timeframe_data.json
            file_path = os.path.join(self.data_folder, f"{symbol}_{timeframe}_data.json")
            
            if not os.path.exists(file_path):
                logger.warning(f"Không tìm thấy dữ liệu cho {symbol} ({timeframe})")
                return {}
            
            with open(file_path, "r") as f:
                data = json.load(f)
            
            return data
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu thị trường {symbol} ({timeframe}): {e}")
            return {}
    
    def load_signal_data(self, symbol: str = None) -> Dict:
        """
        Tải dữ liệu tín hiệu gần đây.
        
        Args:
            symbol (str, optional): Mã cặp giao dịch, nếu None thì tải cho tất cả các cặp
            
        Returns:
            Dict: Dữ liệu tín hiệu
        """
        try:
            # Nếu có symbol cụ thể
            if symbol:
                file_path = os.path.join(self.data_folder, f"{symbol}_signals.json")
                if not os.path.exists(file_path):
                    return {}
                
                with open(file_path, "r") as f:
                    return json.load(f)
            
            # Nếu tải tất cả tín hiệu
            signal_files = [f for f in os.listdir(self.data_folder) if f.endswith("_signals.json")]
            
            all_signals = {}
            for file in signal_files:
                symbol = file.split("_")[0]
                file_path = os.path.join(self.data_folder, file)
                
                with open(file_path, "r") as f:
                    all_signals[symbol] = json.load(f)
            
            return all_signals
        
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu tín hiệu: {e}")
            return {}
    
    def analyze_signals(self, signals: Dict) -> Dict:
        """
        Phân tích tín hiệu và đưa ra nhận định.
        
        Args:
            signals (Dict): Dữ liệu tín hiệu
            
        Returns:
            Dict: Kết quả phân tích
        """
        if not signals:
            return {}
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "overview": {
                "buy_signals": 0,
                "sell_signals": 0,
                "neutral_signals": 0,
                "strong_signals": 0,
                "weak_signals": 0,
                "market_sentiment": "neutral",
                "top_assets": []
            },
            "assets": {}
        }
        
        # Đếm loại tín hiệu
        buy_count = 0
        sell_count = 0
        neutral_count = 0
        
        # Theo dõi tín hiệu mạnh
        strong_signals = []
        
        # Xử lý từng cặp
        for symbol, data in signals.items():
            # Bỏ qua nếu không có dữ liệu
            if not data or not isinstance(data, dict):
                continue
            
            # Lấy tín hiệu mới nhất
            latest_signal = data.get("latest_signal", {})
            historical_signals = data.get("historical", [])
            
            # Phân tích tín hiệu
            signal_type = latest_signal.get("signal", "neutral").lower()
            confidence = latest_signal.get("confidence", 0)
            regime = latest_signal.get("market_regime", "unknown")
            
            # Đếm loại tín hiệu
            if signal_type == "buy":
                buy_count += 1
                if confidence >= 0.7:
                    strong_signals.append({"symbol": symbol, "type": "buy", "confidence": confidence})
            elif signal_type == "sell":
                sell_count += 1
                if confidence >= 0.7:
                    strong_signals.append({"symbol": symbol, "type": "sell", "confidence": confidence})
            else:
                neutral_count += 1
            
            # Phân tích xu hướng dựa trên tín hiệu lịch sử
            trend = "sideways"
            if len(historical_signals) >= 3:
                recent_signals = historical_signals[-3:]
                buy_signals = sum(1 for s in recent_signals if s.get("signal") == "buy")
                sell_signals = sum(1 for s in recent_signals if s.get("signal") == "sell")
                
                if buy_signals >= 2:
                    trend = "uptrend"
                elif sell_signals >= 2:
                    trend = "downtrend"
            
            # Thêm thông tin vào assets
            analysis["assets"][symbol] = {
                "signal": signal_type,
                "confidence": confidence,
                "market_regime": regime,
                "trend": trend,
                "timestamp": latest_signal.get("timestamp", ""),
                "strong_signal": confidence >= 0.7,
                "indicators": latest_signal.get("individual_scores", {})
            }
        
        # Cập nhật overview
        analysis["overview"]["buy_signals"] = buy_count
        analysis["overview"]["sell_signals"] = sell_count
        analysis["overview"]["neutral_signals"] = neutral_count
        analysis["overview"]["strong_signals"] = len(strong_signals)
        
        # Xác định tâm lý thị trường tổng quan
        if buy_count > sell_count and buy_count > neutral_count:
            analysis["overview"]["market_sentiment"] = "bullish"
        elif sell_count > buy_count and sell_count > neutral_count:
            analysis["overview"]["market_sentiment"] = "bearish"
        else:
            analysis["overview"]["market_sentiment"] = "neutral"
        
        # Xếp hạng tài sản theo độ tin cậy
        asset_ranking = []
        for symbol, data in analysis["assets"].items():
            if data["signal"] != "neutral":
                direction = 1 if data["signal"] == "buy" else -1
                asset_ranking.append({
                    "symbol": symbol,
                    "signal": data["signal"],
                    "score": direction * data["confidence"],
                    "confidence": data["confidence"]
                })
        
        # Sắp xếp theo điểm số (mua cao nhất, bán thấp nhất)
        asset_ranking.sort(key=lambda x: x["score"], reverse=True)
        
        # Lấy top 5 tài sản
        analysis["overview"]["top_assets"] = asset_ranking[:5] if asset_ranking else []
        
        return analysis
    
    def generate_signal_summary(self, analysis: Dict) -> str:
        """
        Tạo tóm tắt phân tích tín hiệu bằng văn bản.
        
        Args:
            analysis (Dict): Kết quả phân tích tín hiệu
            
        Returns:
            str: Tóm tắt phân tích
        """
        if not analysis:
            return "Không có dữ liệu phân tích"
        
        # Lấy thông tin tổng quan
        overview = analysis.get("overview", {})
        assets = analysis.get("assets", {})
        
        # Tạo tóm tắt
        summary = f"### TÓM TẮT THỊ TRƯỜNG {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        
        # Tâm lý thị trường
        sentiment = overview.get("market_sentiment", "neutral")
        if sentiment == "bullish":
            summary += "**Tâm lý thị trường: TÍCH CỰC** 📈\n"
        elif sentiment == "bearish":
            summary += "**Tâm lý thị trường: TIÊU CỰC** 📉\n"
        else:
            summary += "**Tâm lý thị trường: TRUNG TÍNH** ↔️\n"
        
        # Tóm tắt tín hiệu
        summary += f"- Tín hiệu mua: {overview.get('buy_signals', 0)}\n"
        summary += f"- Tín hiệu bán: {overview.get('sell_signals', 0)}\n"
        summary += f"- Trung tính: {overview.get('neutral_signals', 0)}\n"
        summary += f"- Tín hiệu mạnh: {overview.get('strong_signals', 0)}\n\n"
        
        # Top tài sản
        top_assets = overview.get("top_assets", [])
        if top_assets:
            summary += "**TOP CẶP GIAO DỊCH:**\n"
            for idx, asset in enumerate(top_assets):
                symbol = asset.get("symbol", "")
                signal = asset.get("signal", "").upper()
                confidence = asset.get("confidence", 0) * 100
                emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪️"
                summary += f"{idx+1}. {emoji} **{symbol}**: {signal} (Độ tin cậy: {confidence:.1f}%)\n"
        
        # Thêm cặp có tín hiệu mạnh
        summary += "\n**CHI TIẾT TÍN HIỆU MẠNH:**\n"
        strong_signals_found = False
        
        for symbol, data in assets.items():
            if data.get("strong_signal", False):
                signal = data.get("signal", "").upper()
                confidence = data.get("confidence", 0) * 100
                regime = data.get("market_regime", "unknown")
                trend = data.get("trend", "sideways")
                
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
                
                emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪️"
                summary += f"{emoji} **{symbol}**: {signal} (Độ tin cậy: {confidence:.1f}%)\n"
                summary += f"   - Chế độ thị trường: {regime_text}\n"
                summary += f"   - Xu hướng gần đây: {trend_text}\n"
                
                strong_signals_found = True
        
        if not strong_signals_found:
            summary += "Không có tín hiệu mạnh nào được phát hiện\n"
        
        # Kết luận
        summary += "\n### NHẬN ĐỊNH TỔNG THỂ\n"
        if sentiment == "bullish":
            summary += "Thị trường đang có xu hướng tích cực. Hầu hết các tài sản đều đang có tín hiệu mua, "
            summary += "đây có thể là thời điểm tốt để xem xét mở vị thế mua cho các tài sản có tín hiệu mạnh.\n"
        elif sentiment == "bearish":
            summary += "Thị trường đang có xu hướng tiêu cực. Đa số các tài sản đều đang có tín hiệu bán, "
            summary += "nên cân nhắc đóng các vị thế mua hiện tại và có thể xem xét mở vị thế bán.\n"
        else:
            summary += "Thị trường đang trong trạng thái trung tính, không có xu hướng rõ ràng. "
            summary += "Nên hạn chế giao dịch và chờ đợi tín hiệu rõ ràng hơn.\n"
        
        return summary
    
    def create_signal_charts(self, signals: Dict, output_folder="./reports/charts"):
        """
        Tạo biểu đồ trực quan từ tín hiệu.
        
        Args:
            signals (Dict): Dữ liệu tín hiệu
            output_folder (str): Thư mục lưu biểu đồ
        """
        # Tạo thư mục đầu ra nếu chưa tồn tại
        os.makedirs(output_folder, exist_ok=True)
        
        # Tạo biểu đồ phân bố tín hiệu
        self._create_signal_distribution_chart(signals, output_folder)
        
        # Tạo biểu đồ độ tin cậy
        self._create_confidence_chart(signals, output_folder)
    
    def _create_signal_distribution_chart(self, signals: Dict, output_folder):
        """
        Tạo biểu đồ phân bố tín hiệu.
        
        Args:
            signals (Dict): Dữ liệu tín hiệu
            output_folder (str): Thư mục lưu biểu đồ
        """
        # Đếm các loại tín hiệu
        buy_count = 0
        sell_count = 0
        neutral_count = 0
        
        for symbol, data in signals.items():
            latest_signal = data.get("latest_signal", {}).get("signal", "neutral").lower()
            
            if latest_signal == "buy":
                buy_count += 1
            elif latest_signal == "sell":
                sell_count += 1
            else:
                neutral_count += 1
        
        # Vẽ biểu đồ
        plt.figure(figsize=(10, 6))
        
        labels = ['Mua', 'Bán', 'Trung tính']
        counts = [buy_count, sell_count, neutral_count]
        colors = ['green', 'red', 'gray']
        
        plt.bar(labels, counts, color=colors)
        
        for i, count in enumerate(counts):
            plt.text(i, count + 0.1, str(count), ha='center')
        
        plt.title('Phân bố tín hiệu giao dịch')
        plt.ylabel('Số lượng tín hiệu')
        plt.grid(axis='y', alpha=0.3)
        
        # Lưu biểu đồ
        plt.savefig(os.path.join(output_folder, "signal_distribution.png"))
        plt.close()
    
    def _create_confidence_chart(self, signals: Dict, output_folder):
        """
        Tạo biểu đồ độ tin cậy của tín hiệu.
        
        Args:
            signals (Dict): Dữ liệu tín hiệu
            output_folder (str): Thư mục lưu biểu đồ
        """
        # Thu thập dữ liệu
        symbols = []
        confidences = []
        signal_types = []
        
        for symbol, data in signals.items():
            latest_signal = data.get("latest_signal", {})
            signal_type = latest_signal.get("signal", "neutral").lower()
            confidence = latest_signal.get("confidence", 0)
            
            # Chỉ hiển thị các tín hiệu không trung tính
            if signal_type != "neutral":
                symbols.append(symbol)
                confidences.append(confidence)
                signal_types.append(signal_type)
        
        # Vẽ biểu đồ nếu có dữ liệu
        if symbols:
            plt.figure(figsize=(12, 8))
            
            # Tạo màu dựa vào loại tín hiệu
            colors = ['green' if s == 'buy' else 'red' for s in signal_types]
            
            # Sắp xếp theo độ tin cậy
            sorted_indices = sorted(range(len(confidences)), key=lambda i: confidences[i], reverse=True)
            sorted_symbols = [symbols[i] for i in sorted_indices]
            sorted_confidences = [confidences[i] for i in sorted_indices]
            sorted_colors = [colors[i] for i in sorted_indices]
            
            # Giới hạn số lượng hiển thị
            max_display = 15
            if len(sorted_symbols) > max_display:
                sorted_symbols = sorted_symbols[:max_display]
                sorted_confidences = sorted_confidences[:max_display]
                sorted_colors = sorted_colors[:max_display]
            
            # Vẽ biểu đồ
            bars = plt.barh(sorted_symbols, sorted_confidences, color=sorted_colors)
            
            # Thêm nhãn giá trị
            for bar in bars:
                width = bar.get_width()
                plt.text(width + 0.01, bar.get_y() + bar.get_height()/2, f'{width:.2f}', 
                         va='center', fontsize=9)
            
            plt.title('Độ tin cậy của tín hiệu giao dịch')
            plt.xlabel('Độ tin cậy')
            plt.xlim(0, 1.1)
            plt.grid(axis='x', alpha=0.3)
            
            # Thêm chú thích
            buy_patch = plt.Rectangle((0, 0), 1, 1, fc="green")
            sell_patch = plt.Rectangle((0, 0), 1, 1, fc="red")
            plt.legend([buy_patch, sell_patch], ["Mua", "Bán"])
            
            # Lưu biểu đồ
            plt.tight_layout()
            plt.savefig(os.path.join(output_folder, "signal_confidence.png"))
            plt.close()
    
    def generate_signal_report(self) -> Dict:
        """
        Tạo báo cáo tín hiệu đầy đủ.
        
        Returns:
            Dict: Báo cáo tín hiệu
        """
        logger.info("Đang tạo báo cáo tín hiệu thị trường")
        
        # Tải dữ liệu tín hiệu
        all_signals = self.load_signal_data()
        
        if not all_signals:
            logger.warning("Không có dữ liệu tín hiệu để tạo báo cáo")
            return {}
        
        # Phân tích tín hiệu
        analysis = self.analyze_signals(all_signals)
        
        # Tạo tóm tắt văn bản
        summary = self.generate_signal_summary(analysis)
        
        # Tạo biểu đồ
        charts_folder = os.path.join(self.report_folder, "charts")
        self.create_signal_charts(all_signals, charts_folder)
        
        # Tạo báo cáo đầy đủ
        report = {
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "summary": summary,
            "charts": {
                "distribution": os.path.join(charts_folder, "signal_distribution.png"),
                "confidence": os.path.join(charts_folder, "signal_confidence.png")
            }
        }
        
        return report
    
    def save_report(self, report: Dict, file_name=None) -> str:
        """
        Lưu báo cáo tín hiệu vào file.
        
        Args:
            report (Dict): Báo cáo tín hiệu
            file_name (str, optional): Tên file báo cáo, nếu None thì tạo tự động
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        if not report:
            return ""
        
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"signal_report_{timestamp}.json"
        
        file_path = os.path.join(self.report_folder, file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            # Lưu tóm tắt văn bản
            summary_file = os.path.join(self.report_folder, f"signal_summary_{timestamp}.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(report.get("summary", ""))
            
            logger.info(f"Đã lưu báo cáo tín hiệu vào: {file_path}")
            logger.info(f"Đã lưu tóm tắt tín hiệu vào: {summary_file}")
            
            return file_path
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu báo cáo tín hiệu: {e}")
            return ""
    
    def send_telegram_notification(self, report: Dict) -> bool:
        """
        Gửi báo cáo tín hiệu qua Telegram.
        
        Args:
            report (Dict): Báo cáo tín hiệu
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not telegram_notifier.enabled:
            logger.warning("Telegram notifier không được kích hoạt")
            return False
        
        try:
            # Lấy thông tin phân tích
            analysis = report.get("analysis", {})
            overview = analysis.get("overview", {})
            
            # Định dạng tin nhắn
            message = f"<b>📊 BÁO CÁO TÍN HIỆU THỊ TRƯỜNG</b>\n\n"
            
            # Tâm lý thị trường
            sentiment = overview.get("market_sentiment", "neutral")
            if sentiment == "bullish":
                message += f"<b>Tâm lý thị trường:</b> 📈 TÍCH CỰC\n"
            elif sentiment == "bearish":
                message += f"<b>Tâm lý thị trường:</b> 📉 TIÊU CỰC\n"
            else:
                message += f"<b>Tâm lý thị trường:</b> ↔️ TRUNG TÍNH\n"
            
            message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Tóm tắt tín hiệu
            message += f"<b>TỔNG QUAN:</b>\n"
            message += f"🟢 Tín hiệu mua: {overview.get('buy_signals', 0)}\n"
            message += f"🔴 Tín hiệu bán: {overview.get('sell_signals', 0)}\n"
            message += f"⚪️ Trung tính: {overview.get('neutral_signals', 0)}\n"
            message += f"💪 Tín hiệu mạnh: {overview.get('strong_signals', 0)}\n\n"
            
            # Top tài sản
            top_assets = overview.get("top_assets", [])
            if top_assets:
                message += f"<b>TOP CẶP GIAO DỊCH:</b>\n"
                for idx, asset in enumerate(top_assets[:5]):  # Chỉ hiển thị top 5
                    symbol = asset.get("symbol", "")
                    signal = asset.get("signal", "").upper()
                    confidence = asset.get("confidence", 0) * 100
                    emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪️"
                    message += f"{idx+1}. {emoji} <b>{symbol}</b>: {signal} ({confidence:.1f}%)\n"
            
            # Gửi tin nhắn
            sent = telegram_notifier.send_message(message)
            
            # Đường dẫn đến biểu đồ
            distribution_chart = report.get("charts", {}).get("distribution")
            confidence_chart = report.get("charts", {}).get("confidence")
            
            # TODO: Nếu muốn gửi ảnh qua Telegram, cần phát triển thêm chức năng gửi ảnh
            
            return sent
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo tín hiệu qua Telegram: {e}")
            return False

def main():
    """Hàm chính để tạo báo cáo tín hiệu"""
    # Tạo thư mục dữ liệu nếu chưa tồn tại
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    reporter = SignalReporter()
    report = reporter.generate_signal_report()
    
    if report:
        # Lưu báo cáo
        reporter.save_report(report)
        
        # Gửi thông báo qua Telegram
        reporter.send_telegram_notification(report)
        
        print("Báo cáo tín hiệu thị trường đã được tạo và gửi đi")
    else:
        print("Không thể tạo báo cáo do thiếu dữ liệu")

if __name__ == "__main__":
    main()