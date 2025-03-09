"""
Module tối ưu hóa thời gian giao dịch dựa trên phân tích hiệu suất lịch sử

Module này phân tích hiệu suất giao dịch theo thời gian trong ngày và theo ngày
trong tuần để xác định các khoảng thời gian tối ưu cho giao dịch, giúp tăng
hiệu quả và giảm thiểu rủi ro.
"""

import math
import logging
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any

# Thiết lập logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('trading_time_optimizer')

class TradingTimeOptimizer:
    """Tối ưu hóa thời gian giao dịch dựa trên hiệu suất lịch sử"""
    
    # Tên các ngày trong tuần để hiển thị
    DAY_NAMES = {
        0: "Thứ Hai",
        1: "Thứ Ba",
        2: "Thứ Tư",
        3: "Thứ Năm", 
        4: "Thứ Sáu",
        5: "Thứ Bảy",
        6: "Chủ Nhật"
    }
    
    def __init__(self, trade_history: List[Dict] = None, time_segments: int = 24):
        """
        Khởi tạo Trading Time Optimizer
        
        Args:
            trade_history (List[Dict]): Lịch sử giao dịch
            time_segments (int): Số phân đoạn thời gian trong ngày
        """
        self.trade_history = trade_history or []
        self.time_segments = time_segments
        self.hour_performance = {}
        self.day_performance = {}
        self.update_performance_analysis()
        logger.info(f"Đã khởi tạo TradingTimeOptimizer với {len(self.trade_history)} giao dịch")
    
    def update_performance_analysis(self) -> None:
        """
        Cập nhật phân tích hiệu suất từ lịch sử giao dịch
        """
        # Khởi tạo thống kê theo giờ
        self.hour_performance = {i: {
            'trades': 0, 'win_rate': 0, 'avg_profit': 0, 
            'sharpe': 0, 'expectancy': 0, 'profit_factor': 0,
            'win_trades': 0, 'loss_trades': 0
        } for i in range(self.time_segments)}
        
        # Khởi tạo thống kê theo ngày trong tuần
        self.day_performance = {i: {
            'trades': 0, 'win_rate': 0, 'avg_profit': 0, 
            'sharpe': 0, 'expectancy': 0, 'profit_factor': 0,
            'win_trades': 0, 'loss_trades': 0
        } for i in range(7)}  # 0 = Thứ 2, 6 = Chủ nhật
        
        if not self.trade_history:
            logger.warning("Không có lịch sử giao dịch để phân tích")
            return
        
        logger.info(f"Phân tích {len(self.trade_history)} giao dịch theo thời gian")
        
        # Tính toán thống kê theo giờ
        for trade in self.trade_history:
            # Phân tích theo giờ
            entry_time = trade.get('entry_time')
            if not entry_time:
                continue
            
            # Chuyển đổi sang datetime nếu là string
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.error(f"Không thể parse thời gian: {entry_time}")
                    continue
                
            hour = entry_time.hour
            day = entry_time.weekday()
            pnl = trade.get('pnl_pct', 0)
            
            # Cập nhật thống kê giờ
            hour_stats = self.hour_performance[hour]
            hour_stats['trades'] += 1
            
            if pnl > 0:
                hour_stats['win_trades'] += 1
            else:
                hour_stats['loss_trades'] += 1
                
            if hour_stats['trades'] == 1:
                hour_stats['win_rate'] = 1 if pnl > 0 else 0
                hour_stats['avg_profit'] = pnl
            else:
                hour_stats['win_rate'] = hour_stats['win_trades'] / hour_stats['trades']
                hour_stats['avg_profit'] = (hour_stats['avg_profit'] * (hour_stats['trades'] - 1) + 
                                         pnl) / hour_stats['trades']
            
            # Cập nhật thống kê ngày
            day_stats = self.day_performance[day]
            day_stats['trades'] += 1
            
            if pnl > 0:
                day_stats['win_trades'] += 1
            else:
                day_stats['loss_trades'] += 1
                
            if day_stats['trades'] == 1:
                day_stats['win_rate'] = 1 if pnl > 0 else 0
                day_stats['avg_profit'] = pnl
            else:
                day_stats['win_rate'] = day_stats['win_trades'] / day_stats['trades']
                day_stats['avg_profit'] = (day_stats['avg_profit'] * (day_stats['trades'] - 1) + 
                                        pnl) / day_stats['trades']
        
        # Tính toán metrics nâng cao
        self._calculate_advanced_metrics()
        logger.info("Hoàn tất phân tích hiệu suất theo thời gian")
    
    def _calculate_advanced_metrics(self) -> None:
        """
        Tính toán các metrics nâng cao như Sharpe ratio, Expectancy, và Profit Factor
        """
        # Tính cho từng giờ
        for hour, stats in self.hour_performance.items():
            if stats['trades'] < 5:
                continue
                
            hour_trades = [t.get('pnl_pct', 0) for t in self.trade_history 
                         if self._get_hour(t.get('entry_time')) == hour]
            
            if len(hour_trades) > 1:
                # Tính Sharpe ratio
                mean_return = np.mean(hour_trades)
                std_return = np.std(hour_trades)
                stats['sharpe'] = mean_return / std_return if std_return > 0 else 0
                
                # Tính Expectancy
                win_rate = stats['win_rate']
                win_trades = [pnl for pnl in hour_trades if pnl > 0]
                loss_trades = [abs(pnl) for pnl in hour_trades if pnl < 0]
                
                avg_win = np.mean(win_trades) if win_trades else 0
                avg_loss = np.mean(loss_trades) if loss_trades else 0
                
                if avg_loss > 0:  # Tránh chia cho 0
                    stats['expectancy'] = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_loss
                else:
                    stats['expectancy'] = 0
                
                # Tính Profit Factor
                total_profit = sum(pnl for pnl in hour_trades if pnl > 0)
                total_loss = sum(abs(pnl) for pnl in hour_trades if pnl < 0)
                
                if total_loss > 0:
                    stats['profit_factor'] = total_profit / total_loss
                else:
                    stats['profit_factor'] = total_profit if total_profit > 0 else 0
        
        # Tính cho từng ngày
        for day, stats in self.day_performance.items():
            if stats['trades'] < 5:
                continue
                
            day_trades = [t.get('pnl_pct', 0) for t in self.trade_history 
                        if self._get_weekday(t.get('entry_time')) == day]
            
            if len(day_trades) > 1:
                # Tính Sharpe ratio
                mean_return = np.mean(day_trades)
                std_return = np.std(day_trades)
                stats['sharpe'] = mean_return / std_return if std_return > 0 else 0
                
                # Tính Expectancy
                win_rate = stats['win_rate']
                win_trades = [pnl for pnl in day_trades if pnl > 0]
                loss_trades = [abs(pnl) for pnl in day_trades if pnl < 0]
                
                avg_win = np.mean(win_trades) if win_trades else 0
                avg_loss = np.mean(loss_trades) if loss_trades else 0
                
                if avg_loss > 0:  # Tránh chia cho 0
                    stats['expectancy'] = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_loss
                else:
                    stats['expectancy'] = 0
                
                # Tính Profit Factor
                total_profit = sum(pnl for pnl in day_trades if pnl > 0)
                total_loss = sum(abs(pnl) for pnl in day_trades if pnl < 0)
                
                if total_loss > 0:
                    stats['profit_factor'] = total_profit / total_loss
                else:
                    stats['profit_factor'] = total_profit if total_profit > 0 else 0
    
    def _get_hour(self, entry_time) -> Optional[int]:
        """Helper để lấy giờ từ đối tượng entry_time"""
        if entry_time is None:
            return None
            
        # Chuyển đổi sang datetime nếu là string
        if isinstance(entry_time, str):
            try:
                entry_time = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
                
        return entry_time.hour
    
    def _get_weekday(self, entry_time) -> Optional[int]:
        """Helper để lấy ngày trong tuần từ đối tượng entry_time"""
        if entry_time is None:
            return None
            
        # Chuyển đổi sang datetime nếu là string
        if isinstance(entry_time, str):
            try:
                entry_time = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
                
        return entry_time.weekday()
    
    def get_optimal_trading_hours(self, min_trades: int = 10, min_expectancy: float = 0.1) -> List[int]:
        """
        Lấy các giờ tối ưu cho giao dịch
        
        Args:
            min_trades (int): Số giao dịch tối thiểu để đánh giá
            min_expectancy (float): Mức expectancy tối thiểu
            
        Returns:
            List[int]: Danh sách các giờ tối ưu
        """
        optimal_hours = []
        
        for hour, stats in self.hour_performance.items():
            if (stats['trades'] >= min_trades and 
                stats['expectancy'] >= min_expectancy and
                stats['avg_profit'] > 0):
                optimal_hours.append(hour)
        
        logger.info(f"Tìm thấy {len(optimal_hours)} giờ tối ưu: {optimal_hours}")
        return sorted(optimal_hours)
    
    def get_optimal_trading_days(self, min_trades: int = 10, min_expectancy: float = 0.1) -> List[int]:
        """
        Lấy các ngày tối ưu cho giao dịch
        
        Args:
            min_trades (int): Số giao dịch tối thiểu để đánh giá
            min_expectancy (float): Mức expectancy tối thiểu
            
        Returns:
            List[int]: Danh sách các ngày tối ưu
        """
        optimal_days = []
        
        for day, stats in self.day_performance.items():
            if (stats['trades'] >= min_trades and 
                stats['expectancy'] >= min_expectancy and
                stats['avg_profit'] > 0):
                optimal_days.append(day)
        
        logger.info(f"Tìm thấy {len(optimal_days)} ngày tối ưu: {optimal_days}")
        return sorted(optimal_days)
    
    def should_trade_now(self, current_time: datetime = None) -> Tuple[bool, str]:
        """
        Kiểm tra xem thời điểm hiện tại có nên giao dịch không
        
        Args:
            current_time (datetime): Thời gian hiện tại, mặc định là now()
            
        Returns:
            Tuple[bool, str]: (Có nên giao dịch, Lý do)
        """
        if current_time is None:
            current_time = datetime.now()
        
        hour = current_time.hour
        day = current_time.weekday()
        
        hour_stats = self.hour_performance.get(hour, {})
        day_stats = self.day_performance.get(day, {})
        
        # Kiểm tra đủ dữ liệu
        if hour_stats.get('trades', 0) < 10 or day_stats.get('trades', 0) < 5:
            return True, "Không đủ dữ liệu lịch sử để đánh giá thời gian giao dịch"
        
        # Kiểm tra nếu cả giờ và ngày đều không tốt
        if (hour_stats.get('avg_profit', 0) < 0 and 
            day_stats.get('avg_profit', 0) < 0):
            return False, f"Thời gian không tối ưu: Giờ {hour} và {self.DAY_NAMES[day]} đều có hiệu suất âm"
        
        # Kiểm tra expectancy
        if hour_stats.get('expectancy', 0) < 0 and day_stats.get('expectancy', 0) < 0:
            return False, f"Thời gian không tối ưu: Giờ {hour} và {self.DAY_NAMES[day]} đều có expectancy âm"
        
        # Trường hợp hiệu suất tốt
        if hour_stats.get('avg_profit', 0) > 0.2 or day_stats.get('expectancy', 0) > 0.5:
            return True, f"Thời gian tối ưu: Hiệu suất cao vào giờ {hour} {self.DAY_NAMES[day]}"
        
        # Mặc định
        return True, "Thời gian chấp nhận được cho giao dịch"
    
    def get_hour_ranking(self) -> List[Dict]:
        """
        Xếp hạng các giờ giao dịch dựa trên hiệu suất
        
        Returns:
            List[Dict]: Danh sách các giờ và thông tin, đã được xếp hạng
        """
        hour_info = []
        
        for hour, stats in self.hour_performance.items():
            if stats['trades'] < 5:
                continue
                
            # Tính điểm xếp hạng
            rank_score = (
                stats['expectancy'] * 0.4 + 
                stats['profit_factor'] * 0.3 + 
                stats['sharpe'] * 0.2 + 
                stats['win_rate'] * 0.1
            )
            
            hour_info.append({
                'hour': hour,
                'trades': stats['trades'],
                'win_rate': stats['win_rate'],
                'avg_profit': stats['avg_profit'],
                'expectancy': stats['expectancy'],
                'profit_factor': stats['profit_factor'],
                'sharpe': stats['sharpe'],
                'rank_score': rank_score
            })
        
        # Sắp xếp theo điểm xếp hạng
        return sorted(hour_info, key=lambda x: x['rank_score'], reverse=True)
    
    def get_day_ranking(self) -> List[Dict]:
        """
        Xếp hạng các ngày giao dịch dựa trên hiệu suất
        
        Returns:
            List[Dict]: Danh sách các ngày và thông tin, đã được xếp hạng
        """
        day_info = []
        
        for day, stats in self.day_performance.items():
            if stats['trades'] < 5:
                continue
                
            # Tính điểm xếp hạng
            rank_score = (
                stats['expectancy'] * 0.4 + 
                stats['profit_factor'] * 0.3 + 
                stats['sharpe'] * 0.2 + 
                stats['win_rate'] * 0.1
            )
            
            day_info.append({
                'day': day,
                'day_name': self.DAY_NAMES[day],
                'trades': stats['trades'],
                'win_rate': stats['win_rate'],
                'avg_profit': stats['avg_profit'],
                'expectancy': stats['expectancy'],
                'profit_factor': stats['profit_factor'],
                'sharpe': stats['sharpe'],
                'rank_score': rank_score
            })
        
        # Sắp xếp theo điểm xếp hạng
        return sorted(day_info, key=lambda x: x['rank_score'], reverse=True)
    
    def get_trading_schedule(self) -> Dict:
        """
        Tạo lịch giao dịch tối ưu dựa trên phân tích hiệu suất
        
        Returns:
            Dict: Lịch giao dịch tối ưu
        """
        # Lấy xếp hạng
        hour_ranking = self.get_hour_ranking()
        day_ranking = self.get_day_ranking()
        
        # Lọc ra các khoảng thời gian tốt
        good_hours = [h['hour'] for h in hour_ranking if h['rank_score'] > 0.5]
        good_days = [d['day'] for d in day_ranking if d['rank_score'] > 0.5]
        
        # Lọc ra các khoảng thời gian tránh
        bad_hours = [h['hour'] for h in hour_ranking if h['rank_score'] < 0]
        bad_days = [d['day'] for d in day_ranking if d['rank_score'] < 0]
        
        # Tạo lịch
        schedule = {
            'optimal_hours': good_hours,
            'optimal_days': good_days,
            'avoid_hours': bad_hours,
            'avoid_days': bad_days,
            'best_day': day_ranking[0]['day'] if day_ranking else None,
            'best_hour': hour_ranking[0]['hour'] if hour_ranking else None,
            'worst_day': day_ranking[-1]['day'] if day_ranking else None,
            'worst_hour': hour_ranking[-1]['hour'] if hour_ranking else None
        }
        
        return schedule
    
    def get_risk_adjustment(self, current_time: datetime = None) -> float:
        """
        Lấy hệ số điều chỉnh rủi ro dựa trên thời gian hiện tại
        
        Args:
            current_time (datetime): Thời gian hiện tại, mặc định là now()
            
        Returns:
            float: Hệ số điều chỉnh rủi ro (0-1.5)
        """
        if current_time is None:
            current_time = datetime.now()
            
        hour = current_time.hour
        day = current_time.weekday()
        
        hour_stats = self.hour_performance.get(hour, {})
        day_stats = self.day_performance.get(day, {})
        
        # Mặc định
        if hour_stats.get('trades', 0) < 10 or day_stats.get('trades', 0) < 5:
            return 1.0
            
        # Tính điểm xếp hạng cho thời gian hiện tại
        hour_score = (
            hour_stats.get('expectancy', 0) * 0.4 + 
            hour_stats.get('profit_factor', 1) * 0.3 + 
            hour_stats.get('sharpe', 0) * 0.2 + 
            hour_stats.get('win_rate', 0.5) * 0.1
        )
        
        day_score = (
            day_stats.get('expectancy', 0) * 0.4 + 
            day_stats.get('profit_factor', 1) * 0.3 + 
            day_stats.get('sharpe', 0) * 0.2 + 
            day_stats.get('win_rate', 0.5) * 0.1
        )
        
        # Kết hợp hai điểm số
        combined_score = hour_score * 0.6 + day_score * 0.4
        
        # Chuyển đổi điểm số thành hệ số điều chỉnh rủi ro
        # Giá trị từ 0.5 (rủi ro giảm một nửa) đến 1.5 (rủi ro tăng 50%)
        risk_factor = 0.5 + combined_score
        
        # Giới hạn giá trị
        return max(0.5, min(1.5, risk_factor))
    
    def get_summary_report(self) -> str:
        """
        Tạo báo cáo tóm tắt về hiệu suất theo thời gian
        
        Returns:
            str: Báo cáo dạng văn bản
        """
        hour_ranking = self.get_hour_ranking()
        day_ranking = self.get_day_ranking()
        
        report = "=== BÁO CÁO HIỆU SUẤT THEO THỜI GIAN ===\n\n"
        
        # Top 3 giờ tốt nhất
        report += "TOP 3 GIỜ TỐT NHẤT:\n"
        for i, hour_info in enumerate(hour_ranking[:3]):
            report += f"{i+1}. Giờ {hour_info['hour']}: "
            report += f"Win rate: {hour_info['win_rate']*100:.1f}%, "
            report += f"Lợi nhuận TB: {hour_info['avg_profit']:.2f}%, "
            report += f"Profit factor: {hour_info['profit_factor']:.2f}\n"
        
        # Top 3 ngày tốt nhất
        report += "\nTOP 3 NGÀY TỐT NHẤT:\n"
        for i, day_info in enumerate(day_ranking[:3]):
            report += f"{i+1}. {day_info['day_name']}: "
            report += f"Win rate: {day_info['win_rate']*100:.1f}%, "
            report += f"Lợi nhuận TB: {day_info['avg_profit']:.2f}%, "
            report += f"Profit factor: {day_info['profit_factor']:.2f}\n"
        
        # Các giờ nên tránh
        report += "\nCÁC GIỜ NÊN TRÁNH:\n"
        bad_hours = [h for h in hour_ranking if h['rank_score'] < 0]
        for i, hour_info in enumerate(bad_hours):
            report += f"{i+1}. Giờ {hour_info['hour']}: "
            report += f"Win rate: {hour_info['win_rate']*100:.1f}%, "
            report += f"Lợi nhuận TB: {hour_info['avg_profit']:.2f}%, "
            report += f"Profit factor: {hour_info['profit_factor']:.2f}\n"
        
        # Các ngày nên tránh
        report += "\nCÁC NGÀY NÊN TRÁNH:\n"
        bad_days = [d for d in day_ranking if d['rank_score'] < 0]
        for i, day_info in enumerate(bad_days):
            report += f"{i+1}. {day_info['day_name']}: "
            report += f"Win rate: {day_info['win_rate']*100:.1f}%, "
            report += f"Lợi nhuận TB: {day_info['avg_profit']:.2f}%, "
            report += f"Profit factor: {day_info['profit_factor']:.2f}\n"
        
        # Đề xuất lịch giao dịch
        schedule = self.get_trading_schedule()
        report += "\nĐỀ XUẤT LỊCH GIAO DỊCH:\n"
        
        # Các ngày tốt
        if schedule['optimal_days']:
            report += "Các ngày tốt nhất: "
            day_names = [self.DAY_NAMES[day] for day in schedule['optimal_days']]
            report += ", ".join(day_names) + "\n"
            
        # Các giờ tốt
        if schedule['optimal_hours']:
            report += "Các giờ tốt nhất: "
            report += ", ".join([f"{hour}h" for hour in schedule['optimal_hours']]) + "\n"
            
        # Các ngày nên tránh
        if schedule['avoid_days']:
            report += "Các ngày nên tránh: "
            day_names = [self.DAY_NAMES[day] for day in schedule['avoid_days']]
            report += ", ".join(day_names) + "\n"
            
        # Các giờ nên tránh
        if schedule['avoid_hours']:
            report += "Các giờ nên tránh: "
            report += ", ".join([f"{hour}h" for hour in schedule['avoid_hours']]) + "\n"
        
        return report

def test_trading_time_optimizer():
    """Hàm test cho module"""
    # Tạo dữ liệu test
    np.random.seed(42)
    
    # Tạo lịch sử giao dịch mẫu
    trade_history = []
    
    # Giờ và ngày với hiệu suất khác nhau
    good_hours = [9, 10, 14, 15, 16]  # Giờ tốt
    bad_hours = [0, 1, 2, 12, 13]     # Giờ xấu
    
    good_days = [1, 3, 4]  # Thứ 3, Thứ 5, Thứ 6
    bad_days = [0, 6]      # Thứ 2, Chủ nhật
    
    # Tạo 200 giao dịch ngẫu nhiên
    start_date = datetime(2023, 1, 1)
    
    for i in range(200):
        # Tạo thời gian ngẫu nhiên
        days_offset = np.random.randint(0, 180)
        hour = np.random.randint(0, 24)
        minute = np.random.randint(0, 60)
        
        trade_time = start_date + timedelta(days=days_offset, hours=hour, minutes=minute)
        
        # Gán hiệu suất dựa trên giờ và ngày
        base_pnl = np.random.normal(0, 1.5)
        
        # Giờ tốt có xu hướng dương
        if hour in good_hours:
            pnl = base_pnl + 1.0
        # Giờ xấu có xu hướng âm
        elif hour in bad_hours:
            pnl = base_pnl - 1.0
        else:
            pnl = base_pnl
            
        # Ngày tốt có xu hướng dương
        if trade_time.weekday() in good_days:
            pnl += 0.5
        # Ngày xấu có xu hướng âm
        elif trade_time.weekday() in bad_days:
            pnl -= 0.5
            
        # Thêm một chút nhiễu
        pnl += np.random.normal(0, 0.5)
        
        # Tạo giao dịch
        trade = {
            'entry_time': trade_time,
            'exit_time': trade_time + timedelta(hours=2),
            'pnl': pnl * 100,  # Đổi sang USD
            'pnl_pct': pnl,    # Phần trăm
            'symbol': 'BTCUSDT',
            'position_size': 1.0
        }
        
        trade_history.append(trade)
    
    # Khởi tạo optimizer
    optimizer = TradingTimeOptimizer(trade_history)
    
    # Test các chức năng
    print("=== Test Trading Time Optimizer ===")
    
    # Lấy giờ tối ưu
    optimal_hours = optimizer.get_optimal_trading_hours()
    print(f"Các giờ tối ưu: {optimal_hours}")
    
    # Lấy ngày tối ưu
    optimal_days = optimizer.get_optimal_trading_days()
    print(f"Các ngày tối ưu: {[TradingTimeOptimizer.DAY_NAMES[d] for d in optimal_days]}")
    
    # Kiểm tra thời gian hiện tại
    now = datetime.now()
    should_trade, reason = optimizer.should_trade_now(now)
    print(f"Nên giao dịch ngay bây giờ: {should_trade}, Lý do: {reason}")
    
    # Lấy xếp hạng giờ
    hour_ranking = optimizer.get_hour_ranking()
    print("\nXếp hạng giờ giao dịch (top 5):")
    for i, hour_info in enumerate(hour_ranking[:5]):
        print(f"{i+1}. Giờ {hour_info['hour']}: Score={hour_info['rank_score']:.2f}, "
              f"Win rate={hour_info['win_rate']*100:.1f}%, Expectancy={hour_info['expectancy']:.2f}")
    
    # Lấy xếp hạng ngày
    day_ranking = optimizer.get_day_ranking()
    print("\nXếp hạng ngày giao dịch:")
    for i, day_info in enumerate(day_ranking):
        print(f"{i+1}. {day_info['day_name']}: Score={day_info['rank_score']:.2f}, "
              f"Win rate={day_info['win_rate']*100:.1f}%, Expectancy={day_info['expectancy']:.2f}")
    
    # Lấy lịch giao dịch
    schedule = optimizer.get_trading_schedule()
    print("\nLịch giao dịch tối ưu:")
    print(f"Các giờ tốt nhất: {schedule['optimal_hours']}")
    print(f"Các ngày tốt nhất: {[TradingTimeOptimizer.DAY_NAMES[d] for d in schedule['optimal_days']]}")
    print(f"Các giờ nên tránh: {schedule['avoid_hours']}")
    print(f"Các ngày nên tránh: {[TradingTimeOptimizer.DAY_NAMES[d] for d in schedule['avoid_days']]}")
    
    # In báo cáo
    print("\n" + optimizer.get_summary_report())
    
    # Kiểm tra điều chỉnh rủi ro
    test_times = [
        datetime(2023, 7, 10, 10, 0),  # Thứ 2, giờ tốt
        datetime(2023, 7, 10, 0, 0),   # Thứ 2, giờ xấu
        datetime(2023, 7, 11, 10, 0),  # Thứ 3, giờ tốt
        datetime(2023, 7, 16, 0, 0),   # Chủ nhật, giờ xấu
    ]
    
    print("\nĐiều chỉnh rủi ro theo thời gian:")
    for test_time in test_times:
        risk_factor = optimizer.get_risk_adjustment(test_time)
        print(f"{test_time.strftime('%A %H:%M')}: {risk_factor:.2f}")

if __name__ == "__main__":
    test_trading_time_optimizer()