"""
Regime Performance Analyzer - Phân tích hiệu suất hệ thống giao dịch theo chế độ thị trường

Module này cung cấp các công cụ để phân tích hiệu suất giao dịch tách biệt 
theo từng chế độ thị trường khác nhau, giúp tối ưu hóa chiến lược giao dịch
cho từng chế độ cụ thể.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional, Union, Any
from collections import defaultdict
import math

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('regime_performance_analyzer')

# Import enhanced market regime detector
from enhanced_market_regime_detector import EnhancedMarketRegimeDetector

class RegimePerformanceAnalyzer:
    """
    Phân tích hiệu suất giao dịch theo từng chế độ thị trường
    và tạo báo cáo chi tiết.
    """
    
    def __init__(self, data_storage_path='data/regime_performance'):
        """
        Khởi tạo trình phân tích hiệu suất theo chế độ thị trường.
        
        Args:
            data_storage_path (str): Đường dẫn để lưu trữ dữ liệu phân tích
        """
        self.data_storage_path = data_storage_path
        self.regime_detector = EnhancedMarketRegimeDetector()
        self.performance_data = {}
        self.regime_performance = {}
        self.trade_history = []
        
        # Tạo thư mục lưu trữ nếu chưa tồn tại
        os.makedirs(data_storage_path, exist_ok=True)
        
        # Tải dữ liệu hiệu suất nếu có
        self._load_performance_data()
    
    def analyze_trades_by_regime(self, trades_df: pd.DataFrame, 
                               market_data_df: pd.DataFrame,
                               calculate_regime: bool = True) -> Dict[str, Any]:
        """
        Phân tích hiệu suất giao dịch theo chế độ thị trường.
        
        Args:
            trades_df (pd.DataFrame): DataFrame chứa lịch sử giao dịch với các cột:
                - entry_time: Thời gian vào lệnh
                - exit_time: Thời gian ra lệnh
                - symbol: Cặp tiền giao dịch
                - direction: Hướng giao dịch (1 = Long, -1 = Short)
                - entry_price: Giá vào lệnh
                - exit_price: Giá ra lệnh
                - profit_pct: Lợi nhuận theo phần trăm
                - profit_amount: Lợi nhuận theo số tiền
            market_data_df (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            calculate_regime (bool): Nếu True, tính toán chế độ thị trường từ dữ liệu
                                   Nếu False, sử dụng cột 'regime' trong trades_df
        
        Returns:
            Dict: Thông tin hiệu suất theo chế độ thị trường
        """
        try:
            if trades_df.empty:
                logger.warning("Không có dữ liệu giao dịch để phân tích")
                return {}
            
            # Sao chép dữ liệu để tránh cảnh báo SettingWithCopyWarning
            trades = trades_df.copy()
            
            # Nếu cần tính toán chế độ thị trường
            if calculate_regime and 'regime' not in trades.columns:
                logger.info("Tính toán chế độ thị trường cho từng giao dịch...")
                
                # Tạo cột chế độ thị trường
                trades['regime'] = None
                trades['regime_confidence'] = 0.0
                
                # Duyệt qua từng giao dịch
                for idx, trade in trades.iterrows():
                    # Lấy thời gian vào lệnh
                    entry_time = pd.to_datetime(trade['entry_time'])
                    
                    # Lấy dữ liệu thị trường tại thời điểm vào lệnh
                    market_data_before_entry = market_data_df[market_data_df.index <= entry_time]
                    
                    if len(market_data_before_entry) >= 50:  # Đủ dữ liệu để phát hiện chế độ
                        # Phát hiện chế độ thị trường
                        regime_result = self.regime_detector.detect_regime(market_data_before_entry)
                        trades.at[idx, 'regime'] = regime_result['regime']
                        trades.at[idx, 'regime_confidence'] = regime_result['confidence']
                    else:
                        trades.at[idx, 'regime'] = 'unknown'
                        trades.at[idx, 'regime_confidence'] = 0.0
            
            # Thêm cột win/loss
            if 'win' not in trades.columns:
                trades['win'] = trades['profit_pct'] > 0
            
            # Phân nhóm theo chế độ thị trường
            regime_groups = trades.groupby('regime')
            
            # Tạo thống kê hiệu suất cho mỗi chế độ
            regime_performance = {}
            for regime, group in regime_groups:
                # Bỏ qua nếu không có đủ dữ liệu
                if len(group) < 5:
                    logger.warning(f"Không đủ dữ liệu cho chế độ {regime}, cần ít nhất 5 giao dịch")
                    continue
                
                win_trades = group[group['win']]
                lose_trades = group[~group['win']]
                
                # Tính toán các thống kê
                total_trades = len(group)
                win_trades_count = len(win_trades)
                win_rate = win_trades_count / total_trades if total_trades > 0 else 0
                
                # Lợi nhuận trung bình
                avg_profit = group['profit_pct'].mean()
                avg_win = win_trades['profit_pct'].mean() if len(win_trades) > 0 else 0
                avg_loss = lose_trades['profit_pct'].mean() if len(lose_trades) > 0 else 0
                
                # Profit factor
                total_win = win_trades['profit_pct'].sum() if len(win_trades) > 0 else 0
                total_loss = abs(lose_trades['profit_pct'].sum()) if len(lose_trades) > 0 else 0
                profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
                
                # Thời gian giữ lệnh trung bình
                if 'exit_time' in group.columns and 'entry_time' in group.columns:
                    group['hold_time'] = (pd.to_datetime(group['exit_time']) - pd.to_datetime(group['entry_time'])).dt.total_seconds() / 3600.0
                    avg_hold_time = group['hold_time'].mean()
                else:
                    avg_hold_time = None
                
                # Drawdown các lệnh
                cumulative_returns = (1 + group['profit_pct'] / 100).cumprod()
                peak = cumulative_returns.expanding().max()
                drawdown = (cumulative_returns / peak - 1) * 100
                max_drawdown = abs(drawdown.min())
                
                # Tính Sharpe ratio (đơn giản hóa)
                returns_array = group['profit_pct'].values
                avg_return = np.mean(returns_array)
                std_return = np.std(returns_array) if len(returns_array) > 1 else 1e-9
                sharpe_ratio = avg_return / std_return if std_return > 0 else 0
                
                # Phân tích theo hướng giao dịch
                if 'direction' in group.columns:
                    long_trades = group[group['direction'] == 1]
                    short_trades = group[group['direction'] == -1]
                    
                    long_win_rate = len(long_trades[long_trades['win']]) / len(long_trades) if len(long_trades) > 0 else 0
                    short_win_rate = len(short_trades[short_trades['win']]) / len(short_trades) if len(short_trades) > 0 else 0
                    
                    direction_analysis = {
                        'long_trades': len(long_trades),
                        'short_trades': len(short_trades),
                        'long_win_rate': long_win_rate,
                        'short_win_rate': short_win_rate,
                        'long_avg_profit': long_trades['profit_pct'].mean() if len(long_trades) > 0 else 0,
                        'short_avg_profit': short_trades['profit_pct'].mean() if len(short_trades) > 0 else 0
                    }
                else:
                    direction_analysis = None
                
                # Chi tiết về chế độ hiện tại
                regime_desc = self.regime_detector._get_regime_description(regime)
                
                # Lưu thống kê
                regime_performance[regime] = {
                    'total_trades': total_trades,
                    'win_trades': win_trades_count,
                    'lose_trades': total_trades - win_trades_count,
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'profit_factor': profit_factor,
                    'max_drawdown': max_drawdown,
                    'sharpe_ratio': sharpe_ratio,
                    'avg_hold_time': avg_hold_time,
                    'direction_analysis': direction_analysis,
                    'regime_description': regime_desc
                }
            
            # Tính toán thống kê tổng thể
            total_trades = len(trades)
            total_win_trades = len(trades[trades['win']])
            overall_win_rate = total_win_trades / total_trades if total_trades > 0 else 0
            overall_avg_profit = trades['profit_pct'].mean()
            
            # Profit factor tổng thể
            total_win_amount = trades[trades['win']]['profit_pct'].sum()
            total_loss_amount = abs(trades[~trades['win']]['profit_pct'].sum())
            overall_profit_factor = total_win_amount / total_loss_amount if total_loss_amount > 0 else float('inf')
            
            # Kết quả nếu tiếp tục chọn lọc theo chế độ tốt nhất
            best_regimes = sorted(regime_performance.items(), 
                                key=lambda x: x[1]['win_rate'] * x[1]['profit_factor'],
                                reverse=True)
            
            # Lưu kết quả phân tích
            self.regime_performance = regime_performance
            
            # Lưu lịch sử giao dịch
            self.trade_history = trades.to_dict('records')
            
            # Tạo báo cáo đầy đủ
            result = {
                'overall': {
                    'total_trades': total_trades,
                    'win_rate': overall_win_rate,
                    'avg_profit': overall_avg_profit,
                    'profit_factor': overall_profit_factor
                },
                'regime_performance': regime_performance,
                'best_regimes': [r[0] for r in best_regimes[:3]],
                'trades_count_by_regime': dict(trades['regime'].value_counts()),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Lưu kết quả phân tích
            self._save_performance_data(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích hiệu suất theo chế độ thị trường: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def generate_performance_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo hiệu suất theo chế độ thị trường.
        
        Args:
            output_path (str, optional): Đường dẫn lưu báo cáo. Mặc định là thư mục dữ liệu.
        
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        try:
            if not self.regime_performance:
                logger.warning("Không có dữ liệu hiệu suất để tạo báo cáo")
                return ""
            
            if output_path is None:
                output_path = os.path.join(self.data_storage_path, 'regime_performance_report.html')
            
            # Tạo DataFrame từ dữ liệu hiệu suất
            performance_records = []
            for regime, data in self.regime_performance.items():
                record = {
                    'Chế độ thị trường': regime,
                    'Số lệnh': data['total_trades'],
                    'Tỷ lệ thắng': f"{data['win_rate']:.2%}",
                    'Lợi nhuận TB': f"{data['avg_profit']:.2f}%",
                    'Profit Factor': f"{data['profit_factor']:.2f}",
                    'Drawdown tối đa': f"{data['max_drawdown']:.2f}%",
                    'Sharpe Ratio': f"{data['sharpe_ratio']:.2f}",
                    'Mô tả': data['regime_description']['vi']
                }
                performance_records.append(record)
            
            performance_df = pd.DataFrame(performance_records)
            
            # Tạo báo cáo HTML
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Báo cáo hiệu suất theo chế độ thị trường</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1, h2 { color: #2c3e50; }
                    table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                    .chart-container { margin: 20px 0; }
                    .section { margin: 30px 0; }
                    .highlight { background-color: #e6f7ff; }
                </style>
            </head>
            <body>
                <h1>Báo cáo hiệu suất theo chế độ thị trường</h1>
                <div class="section">
                    <h2>Tổng quan hiệu suất theo chế độ</h2>
                    {table_html}
                </div>
                <div class="section">
                    <h2>Phân tích chế độ thị trường tốt nhất</h2>
                    <p>Dựa trên phân tích hiệu suất, các chế độ thị trường có hiệu quả cao nhất là:</p>
                    <ol>
                        {best_regimes}
                    </ol>
                </div>
                <div class="section">
                    <h2>Đề xuất chiến lược tối ưu</h2>
                    <ul>
                        {strategy_recommendations}
                    </ul>
                </div>
                <div class="section">
                    <p>Báo cáo được tạo lúc: {timestamp}</p>
                </div>
            </body>
            </html>
            """.format(
                table_html=performance_df.to_html(index=False),
                best_regimes="".join([f"<li><strong>{regime}</strong>: {self.regime_performance[regime]['regime_description']['vi']}<br>Tỷ lệ thắng: {self.regime_performance[regime]['win_rate']:.2%}, Profit Factor: {self.regime_performance[regime]['profit_factor']:.2f}</li>" 
                                  for regime in self.get_best_regimes(3)]),
                strategy_recommendations="".join([f"<li>Cho chế độ <strong>{regime}</strong>: Sử dụng chiến lược {self.regime_detector.REGIME_STRATEGIES.get(regime, ['combined'])[0]}, với tỷ lệ rủi ro tối ưu {self._get_optimal_risk_for_regime(regime):.1f}%</li>" 
                                            for regime in self.get_best_regimes(3)]),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # Lưu báo cáo
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Đã tạo báo cáo hiệu suất theo chế độ thị trường tại: {output_path}")
            
            # Tạo biểu đồ và lưu
            self._generate_performance_charts()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo hiệu suất: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return ""
    
    def _generate_performance_charts(self):
        """Tạo các biểu đồ hiệu suất theo chế độ thị trường."""
        try:
            # Nếu không có dữ liệu, thoát
            if not self.regime_performance:
                return
            
            # Tạo DataFrame cho biểu đồ
            chart_data = []
            for regime, data in self.regime_performance.items():
                chart_data.append({
                    'regime': regime,
                    'win_rate': data['win_rate'] * 100,  # Chuyển thành phần trăm
                    'avg_profit': data['avg_profit'],
                    'profit_factor': min(data['profit_factor'], 10),  # Giới hạn để biểu đồ dễ nhìn
                    'sharpe_ratio': data['sharpe_ratio'],
                    'max_drawdown': data['max_drawdown'],
                    'total_trades': data['total_trades']
                })
            
            chart_df = pd.DataFrame(chart_data)
            
            # 1. Biểu đồ tỷ lệ thắng theo chế độ
            plt.figure(figsize=(12, 8))
            plt.subplot(2, 2, 1)
            bars = plt.bar(chart_df['regime'], chart_df['win_rate'], color='skyblue')
            plt.title('Tỷ lệ thắng theo chế độ thị trường')
            plt.xlabel('Chế độ thị trường')
            plt.ylabel('Tỷ lệ thắng (%)')
            plt.xticks(rotation=45)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Thêm nhãn phần trăm lên mỗi cột
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom')
            
            # 2. Biểu đồ lợi nhuận trung bình theo chế độ
            plt.subplot(2, 2, 2)
            bars = plt.bar(chart_df['regime'], chart_df['avg_profit'], color='lightgreen')
            plt.title('Lợi nhuận trung bình theo chế độ thị trường')
            plt.xlabel('Chế độ thị trường')
            plt.ylabel('Lợi nhuận trung bình (%)')
            plt.xticks(rotation=45)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Thêm nhãn phần trăm lên mỗi cột
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}%', ha='center', va='bottom')
            
            # 3. Biểu đồ Profit Factor theo chế độ
            plt.subplot(2, 2, 3)
            bars = plt.bar(chart_df['regime'], chart_df['profit_factor'], color='salmon')
            plt.title('Profit Factor theo chế độ thị trường')
            plt.xlabel('Chế độ thị trường')
            plt.ylabel('Profit Factor')
            plt.xticks(rotation=45)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Thêm nhãn lên mỗi cột
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}', ha='center', va='bottom')
            
            # 4. Biểu đồ so sánh Sharpe Ratio và Drawdown
            plt.subplot(2, 2, 4)
            x = range(len(chart_df))
            width = 0.35
            
            plt.bar(x, chart_df['sharpe_ratio'], width, label='Sharpe Ratio', color='purple', alpha=0.7)
            plt.bar([i + width for i in x], chart_df['max_drawdown'], width, label='Max Drawdown (%)', color='red', alpha=0.7)
            
            plt.xlabel('Chế độ thị trường')
            plt.ylabel('Giá trị')
            plt.title('So sánh Sharpe Ratio và Drawdown tối đa')
            plt.xticks([i + width/2 for i in x], chart_df['regime'], rotation=45)
            plt.legend()
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            
            # Lưu biểu đồ
            chart_path = os.path.join(self.data_storage_path, 'regime_performance_charts.png')
            plt.savefig(chart_path)
            plt.close()
            
            # Biểu đồ phân phối lệnh theo chế độ
            plt.figure(figsize=(10, 6))
            plt.pie(chart_df['total_trades'], labels=chart_df['regime'], autopct='%1.1f%%',
                  startangle=90, shadow=True)
            plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            plt.title('Phân phối lệnh theo chế độ thị trường')
            
            # Lưu biểu đồ
            chart_path = os.path.join(self.data_storage_path, 'regime_trades_distribution.png')
            plt.savefig(chart_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ hiệu suất theo chế độ thị trường tại: {self.data_storage_path}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ hiệu suất: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_best_regimes(self, top_n: int = 3) -> List[str]:
        """
        Lấy danh sách các chế độ thị trường có hiệu suất tốt nhất.
        
        Args:
            top_n (int): Số lượng chế độ thị trường tốt nhất cần lấy
            
        Returns:
            List[str]: Danh sách chế độ thị trường tốt nhất
        """
        if not self.regime_performance:
            return []
        
        # Sắp xếp theo điểm số (win_rate * profit_factor)
        sorted_regimes = sorted(self.regime_performance.items(), 
                              key=lambda x: x[1]['win_rate'] * x[1]['profit_factor'],
                              reverse=True)
        
        return [r[0] for r in sorted_regimes[:top_n]]
    
    def _get_optimal_risk_for_regime(self, regime: str) -> float:
        """
        Đề xuất mức rủi ro tối ưu cho một chế độ thị trường.
        
        Args:
            regime (str): Chế độ thị trường
            
        Returns:
            float: Mức rủi ro tối ưu (%)
        """
        # Đề xuất mức rủi ro dựa trên đặc điểm của chế độ
        risk_mapping = {
            'trending_bullish': 3.0,
            'trending_bearish': 2.5,
            'ranging_narrow': 2.0,
            'ranging_wide': 2.5,
            'volatile_breakout': 3.5,
            'quiet_accumulation': 1.5,
            'neutral': 2.0
        }
        
        # Sử dụng thông tin từ dữ liệu hiệu suất để điều chỉnh
        if regime in self.regime_performance:
            perf = self.regime_performance[regime]
            
            # Điều chỉnh dựa trên win rate và drawdown
            base_risk = risk_mapping.get(regime, 2.0)
            win_rate_factor = perf['win_rate'] / 0.6  # Chuẩn hóa với tỷ lệ thắng cơ sở 60%
            drawdown_factor = 0.15 / (perf['max_drawdown'] / 100) if perf['max_drawdown'] > 0 else 1.5
            
            # Giới hạn các hệ số điều chỉnh
            win_rate_factor = max(0.7, min(1.3, win_rate_factor))
            drawdown_factor = max(0.7, min(1.3, drawdown_factor))
            
            adjusted_risk = base_risk * win_rate_factor * drawdown_factor
            
            # Giới hạn mức rủi ro trong khoảng hợp lý
            return max(1.0, min(5.0, adjusted_risk))
        
        return risk_mapping.get(regime, 2.0)
    
    def _save_performance_data(self, data: Dict) -> None:
        """Lưu dữ liệu hiệu suất vào file."""
        try:
            # Lưu dữ liệu hiệu suất
            with open(os.path.join(self.data_storage_path, 'regime_performance.json'), 'w') as f:
                json.dump(data, f, indent=2)
                
            # Lưu lịch sử giao dịch
            with open(os.path.join(self.data_storage_path, 'trade_history.json'), 'w') as f:
                json.dump(self.trade_history, f, indent=2)
                
            logger.info(f"Đã lưu dữ liệu hiệu suất theo chế độ thị trường tại: {self.data_storage_path}")
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu hiệu suất: {str(e)}")
    
    def _load_performance_data(self) -> None:
        """Tải dữ liệu hiệu suất từ file."""
        try:
            # Tải dữ liệu hiệu suất
            performance_file = os.path.join(self.data_storage_path, 'regime_performance.json')
            if os.path.exists(performance_file):
                with open(performance_file, 'r') as f:
                    self.performance_data = json.load(f)
                    
                # Lấy thông tin hiệu suất theo chế độ
                if 'regime_performance' in self.performance_data:
                    self.regime_performance = self.performance_data['regime_performance']
            
            # Tải lịch sử giao dịch
            trade_history_file = os.path.join(self.data_storage_path, 'trade_history.json')
            if os.path.exists(trade_history_file):
                with open(trade_history_file, 'r') as f:
                    self.trade_history = json.load(f)
                    
            logger.info(f"Đã tải dữ liệu hiệu suất theo chế độ thị trường từ: {self.data_storage_path}")
                    
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu hiệu suất: {str(e)}")


if __name__ == "__main__":
    # Ví dụ sử dụng
    analyzer = RegimePerformanceAnalyzer()
    
    # Tạo dữ liệu mẫu
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Giả lập dữ liệu giao dịch
    num_trades = 200
    np.random.seed(42)
    
    # Tạo các chế độ thị trường khác nhau
    regimes = ['trending_bullish', 'trending_bearish', 'ranging_narrow', 
              'ranging_wide', 'volatile_breakout', 'quiet_accumulation']
    
    # Thiết lập tỷ lệ thắng và lợi nhuận khác nhau cho từng chế độ
    regime_params = {
        'trending_bullish': {'win_rate': 0.75, 'avg_profit': 2.5, 'avg_loss': -1.5},
        'trending_bearish': {'win_rate': 0.70, 'avg_profit': 2.2, 'avg_loss': -1.6},
        'ranging_narrow': {'win_rate': 0.65, 'avg_profit': 1.8, 'avg_loss': -1.4},
        'ranging_wide': {'win_rate': 0.60, 'avg_profit': 2.0, 'avg_loss': -1.8},
        'volatile_breakout': {'win_rate': 0.55, 'avg_profit': 3.5, 'avg_loss': -2.5},
        'quiet_accumulation': {'win_rate': 0.60, 'avg_profit': 1.5, 'avg_loss': -1.2}
    }
    
    trades_data = []
    for i in range(num_trades):
        # Chọn ngẫu nhiên chế độ thị trường
        regime = np.random.choice(regimes)
        params = regime_params[regime]
        
        # Xác định thắng thua dựa trên tỷ lệ thắng
        is_win = np.random.random() < params['win_rate']
        
        # Tính lợi nhuận
        if is_win:
            profit_pct = params['avg_profit'] + np.random.normal(0, 0.5)
        else:
            profit_pct = params['avg_loss'] + np.random.normal(0, 0.3)
        
        # Thời gian vào lệnh và ra lệnh
        entry_time = datetime.now() - timedelta(days=np.random.randint(1, 90))
        hold_hours = np.random.randint(1, 48)
        exit_time = entry_time + timedelta(hours=hold_hours)
        
        # Hướng giao dịch
        direction = np.random.choice([1, -1])
        
        trades_data.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'symbol': 'BTCUSDT',
            'direction': direction,
            'entry_price': 50000 + np.random.normal(0, 1000),
            'exit_price': 50000 + np.random.normal(0, 1000),
            'profit_pct': profit_pct,
            'profit_amount': profit_pct * 10,  # Giả sử vốn 1000$, đòn bẩy 1:1
            'regime': regime,
            'win': is_win
        })
    
    trades_df = pd.DataFrame(trades_data)
    
    # Tạo dữ liệu thị trường giả lập
    dates = [datetime.now() - timedelta(days=i) for i in range(100, 0, -1)]
    market_data = {
        'open': [50000 + np.random.normal(0, 500) for _ in range(100)],
        'high': [50000 + np.random.normal(0, 700) for _ in range(100)],
        'low': [50000 + np.random.normal(0, 700) for _ in range(100)],
        'close': [50000 + np.random.normal(0, 500) for _ in range(100)],
        'volume': [1000 * (1 + np.random.random()) for _ in range(100)]
    }
    market_df = pd.DataFrame(market_data, index=dates)
    
    # Phân tích hiệu suất
    result = analyzer.analyze_trades_by_regime(trades_df, market_df, calculate_regime=False)
    
    # In kết quả
    for regime, perf in result.get('regime_performance', {}).items():
        print(f"Chế độ: {regime}")
        print(f"  Tỷ lệ thắng: {perf['win_rate']:.2%}")
        print(f"  Lợi nhuận TB: {perf['avg_profit']:.2f}%")
        print(f"  Profit Factor: {perf['profit_factor']:.2f}")
        print("")
    
    # Tạo báo cáo
    report_path = analyzer.generate_performance_report()
    print(f"Đã tạo báo cáo tại: {report_path}")