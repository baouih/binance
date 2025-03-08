#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module cập nhật giờ giao dịch tối ưu cho tài khoản nhỏ

Module này phân tích lịch sử giao dịch để xác định khung giờ và ngày trong tuần
có hiệu suất cao nhất, nhằm tối ưu hóa thời gian giao dịch cho tài khoản nhỏ.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from trading_time_optimizer import TradingTimeOptimizer
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimal_trading_hours.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("optimal_hours_updater")

class OptimalTradingHoursUpdater:
    """Lớp cập nhật giờ giao dịch tối ưu dựa trên phân tích lịch sử"""
    
    def __init__(self, account_config_path='account_config.json', trade_history_file=None):
        """
        Khởi tạo cập nhật giờ giao dịch tối ưu
        
        Args:
            account_config_path (str): Đường dẫn đến file cấu hình tài khoản
            trade_history_file (str): Đường dẫn đến file lịch sử giao dịch
        """
        self.api = BinanceAPI(testnet=True)
        self.account_config_path = account_config_path
        self.account_config = self._load_config(account_config_path)
        self.trade_history = self._load_trade_history(trade_history_file)
        self.time_optimizer = None
        
        logger.info(f"Đã khởi tạo OptimalTradingHoursUpdater với {len(self.trade_history)} giao dịch")
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs('optimization_results', exist_ok=True)
    
    def _load_config(self, config_path):
        """Tải cấu hình từ file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Không thể tải cấu hình từ {config_path}: {str(e)}")
            return {}
    
    def _save_config(self, config, config_path=None):
        """Lưu cấu hình vào file"""
        if config_path is None:
            config_path = self.account_config_path
            
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Đã lưu cấu hình vào {config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
            return False
    
    def _load_trade_history(self, filename=None):
        """
        Tải lịch sử giao dịch từ file hoặc API
        
        Args:
            filename (str): Đường dẫn đến file lịch sử giao dịch
            
        Returns:
            List[Dict]: Danh sách các giao dịch
        """
        trades = []
        
        # Nếu có file, tải từ file
        if filename and os.path.exists(filename):
            try:
                df = pd.read_csv(filename)
                trades = df.to_dict('records')
                logger.info(f"Đã tải {len(trades)} giao dịch từ file {filename}")
                return trades
            except Exception as e:
                logger.error(f"Lỗi khi tải file lịch sử giao dịch: {str(e)}")
        
        # Nếu không có file, thử lấy từ API
        try:
            # Lấy lịch sử giao dịch từ API (ví dụ: 3 tháng gần nhất)
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)
            
            # Lấy balance để biết kích thước tài khoản
            balance = 0
            try:
                account_balance = self.api.futures_account_balance()
                for bal in account_balance:
                    if bal.get('asset') == 'USDT':
                        balance = float(bal.get('availableBalance', 0))
                        break
            except Exception as e:
                logger.error(f"Lỗi khi lấy số dư tài khoản: {str(e)}")
            
            # Lấy danh sách cặp phù hợp dựa trên kích thước tài khoản
            suitable_pairs = []
            
            # Xác định cấu hình dựa trên balance
            small_account_configs = self.account_config.get('small_account_configs', {})
            
            # Chuyển đổi các key từ string thành float để so sánh
            sizes = [float(size) for size in small_account_configs.keys()]
            sizes.sort()
            
            selected_size = None
            for size in sizes:
                if balance >= size:
                    selected_size = size
                else:
                    break
                    
            if selected_size is None and sizes:
                # Nếu số dư nhỏ hơn tất cả các mức, chọn mức nhỏ nhất
                selected_size = sizes[0]
            
            if selected_size:
                size_str = str(int(selected_size))
                config = small_account_configs.get(size_str, {})
                suitable_pairs = config.get('suitable_pairs', [])
            
            if not suitable_pairs:
                # Nếu không có, sử dụng danh sách mặc định
                suitable_pairs = self.account_config.get('symbols', [
                    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 
                    'DOGEUSDT', 'XRPUSDT', 'LINKUSDT', 'AVAXUSDT'
                ])
            
            for symbol in suitable_pairs:
                try:
                    api_trades = self.api.futures_account_trades(symbol=symbol, startTime=start_time, endTime=end_time)
                    
                    if api_trades:
                        for trade in api_trades:
                            trades.append({
                                'symbol': trade.get('symbol'),
                                'side': trade.get('side'),
                                'price': float(trade.get('price')),
                                'qty': float(trade.get('qty')),
                                'realized_pnl': float(trade.get('realizedPnl')),
                                'commission': float(trade.get('commission')),
                                'time': datetime.fromtimestamp(trade.get('time') / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            })
                except Exception as e:
                    logger.error(f"Lỗi khi lấy lịch sử giao dịch cho {symbol}: {str(e)}")
            
            logger.info(f"Đã lấy {len(trades)} giao dịch từ API")
            
            # Lưu lại cho lần sau
            if trades:
                df = pd.DataFrame(trades)
                output_file = 'trade_history.csv'
                df.to_csv(output_file, index=False)
                logger.info(f"Đã lưu lịch sử giao dịch vào file {output_file}")
                
            return trades
        except Exception as e:
            logger.error(f"Lỗi khi lấy lịch sử giao dịch từ API: {str(e)}")
            
        # Nếu không có dữ liệu, sử dụng danh sách rỗng
        logger.warning("Không thể lấy lịch sử giao dịch, tiếp tục với danh sách rỗng")
        return []
    
    def analyze_optimal_trading_hours(self):
        """
        Phân tích giờ giao dịch tối ưu
        
        Returns:
            Tuple[List[int], List[int]]: (Danh sách giờ tối ưu, Danh sách ngày tối ưu)
        """
        if not self.trade_history:
            logger.warning("Không có lịch sử giao dịch để phân tích")
            return [], []
            
        # Chuẩn bị dữ liệu giao dịch cho time optimizer
        formatted_trades = []
        
        for trade in self.trade_history:
            try:
                entry_time = trade.get('time')
                if not entry_time:
                    continue
                
                # Chuyển đổi thời gian
                if isinstance(entry_time, str):
                    entry_time = datetime.strptime(entry_time, '%Y-%m-%d %H:%M:%S')
                
                # Xác định số dư tài khoản
                account_size = 500  # Giá trị mặc định
                
                # Tạo trade entry cho time optimizer
                formatted_trade = {
                    'entry_time': entry_time,
                    'pnl_pct': (trade.get('realized_pnl', 0) / account_size) * 100,
                    'symbol': trade.get('symbol'),
                    'side': trade.get('side'),
                    'realized_pnl': trade.get('realized_pnl', 0)
                }
                
                formatted_trades.append(formatted_trade)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý giao dịch cho time optimizer: {str(e)}")
        
        # Khởi tạo time optimizer
        self.time_optimizer = TradingTimeOptimizer(formatted_trades)
        
        # Lấy giờ và ngày tối ưu
        optimal_hours = self.time_optimizer.get_optimal_trading_hours(min_trades=5, min_expectancy=0.05)
        optimal_days = self.time_optimizer.get_optimal_trading_days(min_trades=5, min_expectancy=0.05)
        
        # Lấy xếp hạng
        hour_ranking = self.time_optimizer.get_hour_ranking()
        day_ranking = self.time_optimizer.get_day_ranking()
        
        logger.info(f"Giờ giao dịch tối ưu: {optimal_hours}")
        logger.info(f"Ngày giao dịch tối ưu: {optimal_days}")
        
        # Tạo biểu đồ phân tích giờ
        try:
            if hour_ranking:
                plt.figure(figsize=(12, 7))
                
                hours = [h.get('hour') for h in hour_ranking]
                scores = [h.get('rank_score', 0) for h in hour_ranking]
                win_rates = [h.get('win_rate', 0) * 100 for h in hour_ranking]
                trades_count = [h.get('trades', 0) for h in hour_ranking]
                
                # Chuẩn hóa số lượng giao dịch để hiển thị
                max_trades = max(trades_count) if trades_count else 1
                normalized_trades = [t / max_trades * 50 for t in trades_count]
                
                # Màu sắc cho các điểm dựa trên win rate
                colors = ['red' if wr < 50 else 'green' for wr in win_rates]
                
                plt.scatter(hours, scores, s=normalized_trades, c=colors, alpha=0.7)
                
                # Thêm nhãn cho các điểm
                for i, hour in enumerate(hours):
                    plt.annotate(f"{hour}:00\nWR: {win_rates[i]:.1f}%\nN: {trades_count[i]}", 
                                xy=(hour, scores[i]),
                                xytext=(5, 5),
                                textcoords='offset points',
                                fontsize=8)
                
                plt.xlabel('Giờ trong ngày')
                plt.ylabel('Điểm xếp hạng')
                plt.title('Phân tích hiệu suất theo giờ', fontsize=16, pad=20)
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.xticks(range(0, 24))
                
                # Tô màu nền cho các giờ tối ưu
                for hour in optimal_hours:
                    plt.axvspan(hour - 0.5, hour + 0.5, alpha=0.2, color='green')
                
                plt.tight_layout()
                plt.savefig('optimization_results/optimal_hours_analysis.png')
                logger.info("Đã lưu biểu đồ phân tích giờ tối ưu vào file optimization_results/optimal_hours_analysis.png")
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân tích giờ: {str(e)}")
        
        # Tạo biểu đồ phân tích ngày
        try:
            if day_ranking:
                plt.figure(figsize=(12, 7))
                
                day_names = [d.get('day_name', '') for d in day_ranking]
                day_nums = [d.get('day') for d in day_ranking]
                scores = [d.get('rank_score', 0) for d in day_ranking]
                win_rates = [d.get('win_rate', 0) * 100 for d in day_ranking]
                trades_count = [d.get('trades', 0) for d in day_ranking]
                
                # Chuẩn hóa số lượng giao dịch để hiển thị
                max_trades = max(trades_count) if trades_count else 1
                normalized_trades = [t / max_trades * 100 for t in trades_count]
                
                # Màu sắc cho các điểm dựa trên win rate
                colors = ['red' if wr < 50 else 'green' for wr in win_rates]
                
                plt.bar(day_names, scores, color=colors, alpha=0.7)
                
                # Thêm nhãn
                for i, day in enumerate(day_names):
                    plt.annotate(f"WR: {win_rates[i]:.1f}%\nN: {trades_count[i]}", 
                                xy=(i, scores[i]),
                                xytext=(0, 5),
                                textcoords='offset points',
                                ha='center',
                                fontsize=9)
                
                plt.xlabel('Ngày trong tuần')
                plt.ylabel('Điểm xếp hạng')
                plt.title('Phân tích hiệu suất theo ngày', fontsize=16, pad=20)
                plt.grid(True, linestyle='--', alpha=0.7, axis='y')
                
                # Tô màu nền cho các ngày tối ưu
                for i, day_num in enumerate(day_nums):
                    if day_num in optimal_days:
                        plt.bar(day_names[i], scores[i], color='lightgreen', alpha=0.5)
                
                plt.tight_layout()
                plt.savefig('optimization_results/optimal_days_analysis.png')
                logger.info("Đã lưu biểu đồ phân tích ngày tối ưu vào file optimization_results/optimal_days_analysis.png")
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân tích ngày: {str(e)}")
        
        return optimal_hours, optimal_days
    
    def analyze_symbol_performance_by_hour(self):
        """
        Phân tích hiệu suất của từng cặp tiền theo giờ
        
        Returns:
            Dict: Thông tin hiệu suất theo cặp tiền và giờ
        """
        if not self.trade_history:
            logger.warning("Không có lịch sử giao dịch để phân tích hiệu suất theo cặp tiền")
            return {}
            
        # Nhóm giao dịch theo cặp tiền và giờ
        symbol_hour_stats = {}
        
        for trade in self.trade_history:
            try:
                symbol = trade.get('symbol')
                entry_time = trade.get('time')
                
                if not symbol or not entry_time:
                    continue
                    
                # Chuyển đổi thời gian
                if isinstance(entry_time, str):
                    entry_time = datetime.strptime(entry_time, '%Y-%m-%d %H:%M:%S')
                
                hour = entry_time.hour
                
                if symbol not in symbol_hour_stats:
                    symbol_hour_stats[symbol] = {}
                
                if hour not in symbol_hour_stats[symbol]:
                    symbol_hour_stats[symbol][hour] = {
                        'trades': 0,
                        'win_trades': 0,
                        'loss_trades': 0,
                        'profit': 0,
                        'loss': 0,
                        'win_rate': 0,
                        'profit_factor': 0
                    }
                
                # Cập nhật thống kê
                stats = symbol_hour_stats[symbol][hour]
                pnl = trade.get('realized_pnl', 0)
                
                stats['trades'] += 1
                
                if pnl > 0:
                    stats['win_trades'] += 1
                    stats['profit'] += pnl
                else:
                    stats['loss_trades'] += 1
                    stats['loss'] += abs(pnl)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý giao dịch cho phân tích cặp tiền theo giờ: {str(e)}")
        
        # Tính toán các chỉ số
        for symbol, hours in symbol_hour_stats.items():
            for hour, stats in hours.items():
                if stats['trades'] > 0:
                    stats['win_rate'] = stats['win_trades'] / stats['trades']
                if stats['loss'] > 0:
                    stats['profit_factor'] = stats['profit'] / stats['loss']
                else:
                    stats['profit_factor'] = stats['profit'] if stats['profit'] > 0 else 0
        
        # Tìm giờ tối ưu cho từng cặp tiền
        optimal_hours_by_symbol = {}
        
        for symbol, hours in symbol_hour_stats.items():
            # Lọc các giờ có ít nhất 5 giao dịch và profit factor > 1
            good_hours = [
                hour for hour, stats in hours.items()
                if stats['trades'] >= 5 and stats['profit_factor'] > 1
            ]
            
            optimal_hours_by_symbol[symbol] = good_hours
            
            logger.info(f"Giờ giao dịch tối ưu cho {symbol}: {good_hours}")
        
        # Lưu kết quả
        try:
            with open('optimization_results/optimal_hours_by_symbol.json', 'w') as f:
                json.dump(optimal_hours_by_symbol, f, indent=4)
                
            logger.info("Đã lưu giờ tối ưu theo cặp tiền vào file optimization_results/optimal_hours_by_symbol.json")
        except Exception as e:
            logger.error(f"Lỗi khi lưu giờ tối ưu theo cặp tiền: {str(e)}")
        
        return optimal_hours_by_symbol
    
    def update_account_config(self, optimal_hours, optimal_days):
        """
        Cập nhật cấu hình tài khoản với giờ và ngày giao dịch tối ưu
        
        Args:
            optimal_hours (List[int]): Danh sách giờ tối ưu
            optimal_days (List[int]): Danh sách ngày tối ưu
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if not optimal_hours and not optimal_days:
            logger.warning("Không có giờ hoặc ngày tối ưu để cập nhật cấu hình")
            return False
            
        # Tạo bản sao cấu hình
        config = self.account_config.copy()
        
        # Cập nhật giờ và ngày tối ưu cho từng cấu hình tài khoản nhỏ
        small_account_configs = config.get('small_account_configs', {})
        
        for size, size_config in small_account_configs.items():
            if optimal_hours:
                size_config['optimal_trading_hours'] = optimal_hours
            if optimal_days:
                size_config['optimal_trading_days'] = optimal_days
        
        # Cập nhật cấu hình
        config['small_account_configs'] = small_account_configs
        
        # Cập nhật thời gian sửa đổi
        config['last_updated'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        
        # Lưu cấu hình
        success = self._save_config(config)
        
        if success:
            logger.info(f"Đã cập nhật cấu hình tài khoản với giờ tối ưu: {optimal_hours} và ngày tối ưu: {optimal_days}")
        
        return success
    
    def run(self):
        """Thực hiện đầy đủ quá trình phân tích và cập nhật"""
        logger.info("="*80)
        logger.info("BẮT ĐẦU PHÂN TÍCH VÀ CẬP NHẬT GIỜ GIAO DỊCH TỐI ƯU")
        logger.info("="*80)
        
        # Phân tích giờ giao dịch tối ưu
        logger.info("\nPhân tích giờ giao dịch tối ưu...")
        optimal_hours, optimal_days = self.analyze_optimal_trading_hours()
        
        # Phân tích hiệu suất theo cặp tiền và giờ
        logger.info("\nPhân tích hiệu suất theo cặp tiền và giờ...")
        symbol_hour_stats = self.analyze_symbol_performance_by_hour()
        
        # Cập nhật cấu hình tài khoản
        logger.info("\nCập nhật cấu hình tài khoản...")
        updated = self.update_account_config(optimal_hours, optimal_days)
        
        # Hiển thị kết quả
        logger.info("\n" + "="*80)
        logger.info("KẾT QUẢ PHÂN TÍCH")
        logger.info("="*80)
        
        hour_names = [f"{h}:00" for h in sorted(optimal_hours)]
        day_names = {
            0: "Thứ Hai", 1: "Thứ Ba", 2: "Thứ Tư", 
            3: "Thứ Năm", 4: "Thứ Sáu", 5: "Thứ Bảy", 6: "Chủ Nhật"
        }
        optimal_day_names = [day_names.get(d) for d in sorted(optimal_days)]
        
        logger.info(f"\nGiờ giao dịch tối ưu: {', '.join(hour_names)}")
        logger.info(f"Ngày giao dịch tối ưu: {', '.join(optimal_day_names)}")
        
        if symbol_hour_stats:
            logger.info("\nGiờ tối ưu theo cặp tiền:")
            for symbol, hours in symbol_hour_stats.items():
                hour_names = [f"{h}:00" for h in sorted(hours)]
                if hour_names:
                    logger.info(f"  {symbol}: {', '.join(hour_names)}")
        
        logger.info("\n" + "="*80)
        logger.info("HOÀN THÀNH CẬP NHẬT GIỜ GIAO DỊCH TỐI ƯU")
        logger.info("="*80)
        
        return {
            'optimal_hours': optimal_hours,
            'optimal_days': optimal_days,
            'symbol_hour_stats': symbol_hour_stats,
            'updated': updated
        }

def update_optimal_trading_hours(trade_history_file=None):
    """
    Hàm chính để chạy cập nhật giờ giao dịch tối ưu
    
    Args:
        trade_history_file (str): Đường dẫn đến file lịch sử giao dịch
    """
    updater = OptimalTradingHoursUpdater(trade_history_file=trade_history_file)
    return updater.run()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Cập nhật giờ giao dịch tối ưu')
    parser.add_argument('--history', type=str, help='Đường dẫn đến file lịch sử giao dịch')
    
    args = parser.parse_args()
    
    update_optimal_trading_hours(args.history)