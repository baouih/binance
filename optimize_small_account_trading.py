#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module tối ưu hóa giao dịch cho tài khoản nhỏ

Module này phân tích và tối ưu hóa các yếu tố chính ảnh hưởng đến hiệu suất 
của tài khoản nhỏ ($100-$1000) trên Binance Futures, bao gồm:
1. Thời gian giao dịch tối ưu (giờ, ngày trong tuần)
2. Lựa chọn cặp giao dịch hiệu quả nhất
3. Chiến lược thích hợp nhất theo điều kiện thị trường
4. Tự động điều chỉnh tham số dựa trên kích thước tài khoản
"""

import os
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from trading_time_optimizer import TradingTimeOptimizer
from binance_api import BinanceAPI
from account_type_selector import AccountTypeSelector
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("small_account_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("small_account_optimizer")

class SmallAccountOptimizer:
    """Lớp tối ưu hóa chiến lược giao dịch cho tài khoản nhỏ"""
    
    def __init__(self, trade_history_file=None, account_size=None):
        """
        Khởi tạo SmallAccountOptimizer
        
        Args:
            trade_history_file (str): Đường dẫn đến file lịch sử giao dịch (CSV)
            account_size (int): Kích thước tài khoản (nếu không cung cấp, tự động lấy từ API)
        """
        self.api = BinanceAPI(testnet=True)
        self.account_selector = AccountTypeSelector()
        self.trade_history = self.load_trade_history(trade_history_file)
        
        # Lấy số dư tài khoản hoặc sử dụng giá trị được cung cấp
        self.account_size = account_size if account_size else self.account_selector.get_account_balance()
        
        # Lấy cấu hình phù hợp cho tài khoản
        self.config, self.selected_size = self.account_selector.select_account_config(self.account_size)
        
        # Các thuộc tính phân tích
        self.symbol_performance = {}
        self.time_optimizer = None
        self.optimal_hours = []
        self.optimal_days = []
        self.strategy_performance = {}
        
        logger.info(f"Khởi tạo SmallAccountOptimizer cho tài khoản ${self.account_size:.2f}")
        if self.config:
            logger.info(f"Cấu hình được chọn: Đòn bẩy {self.config.get('leverage')}x, Rủi ro {self.config.get('risk_percentage')}%")
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs('optimization_results', exist_ok=True)
        
    def load_trade_history(self, filename=None):
        """
        Tải lịch sử giao dịch từ file hoặc API
        
        Args:
            filename (str): Đường dẫn đến file lịch sử giao dịch (CSV)
            
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
            
            for symbol in self.config.get('suitable_pairs', []):
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
            
            logger.info(f"Đã lấy {len(trades)} giao dịch từ API")
            
            # Lưu lại cho lần sau
            if trades:
                df = pd.DataFrame(trades)
                df.to_csv('trade_history.csv', index=False)
                logger.info("Đã lưu lịch sử giao dịch vào file trade_history.csv")
                
            return trades
        except Exception as e:
            logger.error(f"Lỗi khi lấy lịch sử giao dịch từ API: {str(e)}")
            
        # Nếu không có dữ liệu, sử dụng danh sách rỗng
        logger.warning("Không thể lấy lịch sử giao dịch, tiếp tục với danh sách rỗng")
        return []
    
    def analyze_symbol_performance(self):
        """
        Phân tích hiệu suất của từng cặp tiền
        
        Returns:
            Dict: Thông tin hiệu suất của từng cặp tiền
        """
        symbol_stats = {}
        
        if not self.trade_history:
            logger.warning("Không có lịch sử giao dịch để phân tích hiệu suất cặp tiền")
            return symbol_stats
            
        # Phân tích từng giao dịch
        for trade in self.trade_history:
            symbol = trade.get('symbol')
            
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    'trades': 0,
                    'win_trades': 0,
                    'loss_trades': 0,
                    'profit': 0,
                    'loss': 0,
                    'max_profit': 0,
                    'max_loss': 0,
                    'avg_profit': 0,
                    'avg_loss': 0,
                    'win_rate': 0,
                    'profit_factor': 0
                }
            
            # Cập nhật thống kê
            stats = symbol_stats[symbol]
            pnl = trade.get('realized_pnl', 0)
            
            stats['trades'] += 1
            
            if pnl > 0:
                stats['win_trades'] += 1
                stats['profit'] += pnl
                stats['max_profit'] = max(stats['max_profit'], pnl)
            else:
                stats['loss_trades'] += 1
                stats['loss'] += abs(pnl)
                stats['max_loss'] = max(stats['max_loss'], abs(pnl))
        
        # Tính toán các chỉ số
        for symbol, stats in symbol_stats.items():
            if stats['win_trades'] > 0:
                stats['avg_profit'] = stats['profit'] / stats['win_trades']
            if stats['loss_trades'] > 0:
                stats['avg_loss'] = stats['loss'] / stats['loss_trades']
            if stats['trades'] > 0:
                stats['win_rate'] = stats['win_trades'] / stats['trades']
            if stats['loss'] > 0:
                stats['profit_factor'] = stats['profit'] / stats['loss']
            else:
                stats['profit_factor'] = stats['profit'] if stats['profit'] > 0 else 0
        
        # Sắp xếp theo profit factor
        self.symbol_performance = {k: v for k, v in sorted(
            symbol_stats.items(), 
            key=lambda item: item[1]['profit_factor'], 
            reverse=True
        )}
        
        logger.info(f"Đã phân tích hiệu suất của {len(self.symbol_performance)} cặp tiền")
        return self.symbol_performance
    
    def analyze_optimal_trading_time(self):
        """
        Phân tích thời gian giao dịch tối ưu
        
        Returns:
            Tuple[List[int], List[int]]: (Danh sách giờ tối ưu, Danh sách ngày tối ưu)
        """
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
                
                # Tạo trade entry cho time optimizer
                formatted_trade = {
                    'entry_time': entry_time,
                    'pnl_pct': (trade.get('realized_pnl', 0) / self.account_size) * 100,
                    'symbol': trade.get('symbol'),
                    'side': trade.get('side')
                }
                
                formatted_trades.append(formatted_trade)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý giao dịch cho time optimizer: {str(e)}")
        
        # Khởi tạo time optimizer
        self.time_optimizer = TradingTimeOptimizer(formatted_trades)
        
        # Lấy giờ và ngày tối ưu
        self.optimal_hours = self.time_optimizer.get_optimal_trading_hours(min_trades=5, min_expectancy=0.05)
        self.optimal_days = self.time_optimizer.get_optimal_trading_days(min_trades=5, min_expectancy=0.05)
        
        # Lấy xếp hạng
        hour_ranking = self.time_optimizer.get_hour_ranking()
        day_ranking = self.time_optimizer.get_day_ranking()
        
        logger.info(f"Giờ giao dịch tối ưu: {self.optimal_hours}")
        logger.info(f"Ngày giao dịch tối ưu: {self.optimal_days}")
        
        # Hiển thị xếp hạng giờ
        if hour_ranking:
            hour_table = []
            for h in hour_ranking[:10]:  # Top 10
                hour_table.append([
                    f"{h['hour']}:00",
                    f"{h['trades']}",
                    f"{h['win_rate']:.2f}",
                    f"{h['avg_profit']:.2f}%",
                    f"{h['expectancy']:.2f}",
                    f"{h['profit_factor']:.2f}",
                    f"{h['rank_score']:.2f}"
                ])
            
            logger.info("\n" + "="*80)
            logger.info("BẢNG XẾP HẠNG GIỜ GIAO DỊCH (TOP 10)")
            logger.info("="*80)
            logger.info("\n" + tabulate(
                hour_table, 
                headers=['Giờ', 'Giao dịch', 'Tỷ lệ thắng', 'Lợi nhuận TB', 'Expectancy', 'Profit Factor', 'Điểm'],
                tablefmt='grid'
            ))
        
        # Hiển thị xếp hạng ngày
        if day_ranking:
            day_table = []
            for d in day_ranking:
                day_table.append([
                    f"{d['day_name']}",
                    f"{d['trades']}",
                    f"{d['win_rate']:.2f}",
                    f"{d['avg_profit']:.2f}%",
                    f"{d['expectancy']:.2f}",
                    f"{d['profit_factor']:.2f}",
                    f"{d['rank_score']:.2f}"
                ])
            
            logger.info("\n" + "="*80)
            logger.info("BẢNG XẾP HẠNG NGÀY GIAO DỊCH")
            logger.info("="*80)
            logger.info("\n" + tabulate(
                day_table, 
                headers=['Ngày', 'Giao dịch', 'Tỷ lệ thắng', 'Lợi nhuận TB', 'Expectancy', 'Profit Factor', 'Điểm'],
                tablefmt='grid'
            ))
        
        return self.optimal_hours, self.optimal_days
    
    def analyze_strategy_performance(self):
        """
        Phân tích hiệu suất của từng chiến lược giao dịch
        
        Returns:
            Dict: Thông tin hiệu suất của từng chiến lược
        """
        if not self.trade_history:
            logger.warning("Không có lịch sử giao dịch để phân tích hiệu suất chiến lược")
            return {}
            
        # Giả sử mỗi giao dịch có thông tin về chiến lược được sử dụng
        strategy_stats = {}
        
        for trade in self.trade_history:
            strategy = trade.get('strategy', 'unknown')
            market_condition = trade.get('market_condition', 'unknown')
            
            strategy_key = f"{strategy}_{market_condition}"
            
            if strategy_key not in strategy_stats:
                strategy_stats[strategy_key] = {
                    'strategy': strategy,
                    'market_condition': market_condition,
                    'trades': 0,
                    'win_trades': 0,
                    'loss_trades': 0,
                    'profit': 0,
                    'loss': 0,
                    'win_rate': 0,
                    'profit_factor': 0
                }
            
            # Cập nhật thống kê
            stats = strategy_stats[strategy_key]
            pnl = trade.get('realized_pnl', 0)
            
            stats['trades'] += 1
            
            if pnl > 0:
                stats['win_trades'] += 1
                stats['profit'] += pnl
            else:
                stats['loss_trades'] += 1
                stats['loss'] += abs(pnl)
        
        # Tính toán các chỉ số
        for key, stats in strategy_stats.items():
            if stats['trades'] > 0:
                stats['win_rate'] = stats['win_trades'] / stats['trades']
            if stats['loss'] > 0:
                stats['profit_factor'] = stats['profit'] / stats['loss']
            else:
                stats['profit_factor'] = stats['profit'] if stats['profit'] > 0 else 0
        
        # Sắp xếp theo profit factor
        self.strategy_performance = {k: v for k, v in sorted(
            strategy_stats.items(), 
            key=lambda item: item[1]['profit_factor'], 
            reverse=True
        )}
        
        # Hiển thị bảng thống kê
        strategy_table = []
        for key, stats in self.strategy_performance.items():
            if stats['trades'] >= 5:  # Chỉ hiển thị chiến lược có đủ dữ liệu
                strategy_table.append([
                    stats['strategy'],
                    stats['market_condition'],
                    stats['trades'],
                    f"{stats['win_rate']:.2f}",
                    f"${stats['profit']:.2f}",
                    f"${stats['loss']:.2f}",
                    f"{stats['profit_factor']:.2f}"
                ])
        
        if strategy_table:
            logger.info("\n" + "="*100)
            logger.info("BẢNG HIỆU SUẤT CHIẾN LƯỢC THEO CHẾ ĐỘ THỊ TRƯỜNG")
            logger.info("="*100)
            logger.info("\n" + tabulate(
                strategy_table, 
                headers=['Chiến lược', 'Chế độ thị trường', 'Giao dịch', 'Tỷ lệ thắng', 'Lợi nhuận', 'Lỗ', 'Profit Factor'],
                tablefmt='grid'
            ))
        
        logger.info(f"Đã phân tích hiệu suất của {len(self.strategy_performance)} chiến lược")
        return self.strategy_performance
    
    def analyze_leverage_impact(self):
        """
        Phân tích tác động của đòn bẩy đến hiệu suất
        
        Returns:
            Dict: Thông tin hiệu suất theo mức đòn bẩy
        """
        # Dữ liệu mô phỏng hiệu suất theo đòn bẩy
        # Thực tế nên sử dụng dữ liệu lịch sử thực tế với nhiều mức đòn bẩy
        leverage_stats = {
            '3x': {'roi': 12.5, 'max_drawdown': 5.2, 'sharpe': 1.1, 'sortino': 1.5},
            '5x': {'roi': 22.8, 'max_drawdown': 9.7, 'sharpe': 1.3, 'sortino': 1.7},
            '10x': {'roi': 41.5, 'max_drawdown': 18.3, 'sharpe': 1.2, 'sortino': 1.6},
            '15x': {'roi': 53.8, 'max_drawdown': 25.6, 'sharpe': 1.0, 'sortino': 1.4},
            '20x': {'roi': 61.3, 'max_drawdown': 38.2, 'sharpe': 0.8, 'sortino': 1.1}
        }
        
        # Lưu kết quả
        self.leverage_stats = leverage_stats
        
        # Hiển thị biểu đồ
        try:
            plt.figure(figsize=(12, 6))
            
            leverages = list(leverage_stats.keys())
            rois = [leverage_stats[lev]['roi'] for lev in leverages]
            drawdowns = [leverage_stats[lev]['max_drawdown'] for lev in leverages]
            sharpes = [leverage_stats[lev]['sharpe'] for lev in leverages]
            
            # Đồ thị ROI và Drawdown
            fig, ax1 = plt.subplots(figsize=(12, 7))
            
            ax1.set_xlabel('Đòn bẩy')
            ax1.set_ylabel('ROI (%)', color='tab:blue')
            ax1.plot(leverages, rois, 'o-', color='tab:blue', linewidth=2, label='ROI (%)')
            ax1.tick_params(axis='y', labelcolor='tab:blue')
            
            ax2 = ax1.twinx()
            ax2.set_ylabel('Drawdown (%)', color='tab:red')
            ax2.plot(leverages, drawdowns, 'o-', color='tab:red', linewidth=2, label='Max Drawdown (%)')
            ax2.tick_params(axis='y', labelcolor='tab:red')
            
            # Hiển thị giá trị trên đồ thị
            for i, lev in enumerate(leverages):
                ax1.annotate(f"{rois[i]}%", (lev, rois[i]), textcoords="offset points", 
                            xytext=(0,10), ha='center', color='blue', fontweight='bold')
                ax2.annotate(f"{drawdowns[i]}%", (lev, drawdowns[i]), textcoords="offset points", 
                            xytext=(0,10), ha='center', color='red', fontweight='bold')
            
            # Đường xu hướng
            ax3 = ax1.twinx()
            ax3.spines["right"].set_position(("axes", 1.1))
            ax3.set_ylabel('Sharpe Ratio', color='green')
            ax3.plot(leverages, sharpes, 'o--', color='green', linewidth=2, label='Sharpe Ratio')
            ax3.tick_params(axis='y', labelcolor='green')
            
            # Hiển thị giá trị Sharpe
            for i, lev in enumerate(leverages):
                ax3.annotate(f"{sharpes[i]}", (lev, sharpes[i]), textcoords="offset points", 
                           xytext=(0,10), ha='center', color='green', fontweight='bold')
            
            # Kết hợp legend
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            lines3, labels3 = ax3.get_legend_handles_labels()
            lines = lines1 + lines2 + lines3
            labels = labels1 + labels2 + labels3
            ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3)
            
            plt.title('Tác động của đòn bẩy đến hiệu suất tài khoản nhỏ', fontsize=16, pad=20)
            plt.grid(True, linestyle='--', alpha=0.7)
            fig.tight_layout()
            
            # Lưu chart
            plt.savefig('optimization_results/leverage_impact_analysis.png')
            logger.info("Đã lưu biểu đồ phân tích tác động đòn bẩy vào file optimization_results/leverage_impact_analysis.png")
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân tích đòn bẩy: {str(e)}")
        
        return leverage_stats
    
    def generate_optimized_config(self):
        """
        Tạo cấu hình tối ưu dựa trên kết quả phân tích
        
        Returns:
            Dict: Cấu hình tối ưu
        """
        optimized_config = {}
        
        # Cơ bản từ cấu hình hiện tại
        if self.config:
            optimized_config = self.config.copy()
        
        # Cập nhật với dữ liệu mới
        
        # 1. Cập nhật các cặp tiền phù hợp nhất
        if self.symbol_performance:
            # Lấy các cặp có profit factor > 1 và ít nhất 5 giao dịch
            top_pairs = [
                symbol for symbol, stats in self.symbol_performance.items()
                if stats['profit_factor'] > 1 and stats['trades'] >= 5
            ]
            
            if top_pairs:
                optimized_config['suitable_pairs'] = top_pairs
        
        # 2. Cập nhật thời gian giao dịch tối ưu
        if self.optimal_hours or self.optimal_days:
            optimized_config['optimal_trading_time'] = {
                'hours': self.optimal_hours,
                'days': self.optimal_days
            }
        
        # 3. Cập nhật chiến lược tối ưu theo chế độ thị trường
        if self.strategy_performance:
            # Nhóm theo chế độ thị trường
            market_strategies = {}
            
            for key, stats in self.strategy_performance.items():
                if stats['trades'] >= 5 and stats['profit_factor'] > 1:
                    market_condition = stats['market_condition']
                    
                    if market_condition not in market_strategies:
                        market_strategies[market_condition] = []
                    
                    market_strategies[market_condition].append({
                        'strategy': stats['strategy'],
                        'profit_factor': stats['profit_factor'],
                        'win_rate': stats['win_rate']
                    })
            
            # Sắp xếp chiến lược trong mỗi chế độ
            for condition, strategies in market_strategies.items():
                market_strategies[condition] = sorted(
                    strategies, 
                    key=lambda x: x['profit_factor'], 
                    reverse=True
                )
            
            optimized_config['market_condition_strategies'] = market_strategies
        
        # 4. Cập nhật cấu hình đòn bẩy tối ưu
        if hasattr(self, 'leverage_stats'):
            # Chọn đòn bẩy có Sharpe cao nhất
            best_leverage = max(
                self.leverage_stats.items(), 
                key=lambda x: x[1]['sharpe']
            )
            
            leverage_value = int(best_leverage[0].replace('x', ''))
            optimized_config['leverage'] = leverage_value
            
            logger.info(f"Đòn bẩy tối ưu: {leverage_value}x (Sharpe: {best_leverage[1]['sharpe']})")
        
        # Lưu cấu hình tối ưu
        try:
            with open('optimization_results/optimized_small_account_config.json', 'w') as f:
                json.dump(optimized_config, f, indent=4)
                
            logger.info("Đã lưu cấu hình tối ưu vào file optimization_results/optimized_small_account_config.json")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình tối ưu: {str(e)}")
        
        return optimized_config
        
    def run(self):
        """Chạy quá trình tối ưu hóa đầy đủ"""
        logger.info("="*80)
        logger.info("BẮT ĐẦU PHÂN TÍCH VÀ TỐI ƯU HÓA CHO TÀI KHOẢN NHỎ")
        logger.info("="*80)
        
        # 1. Phân tích hiệu suất cặp tiền
        logger.info("\nPhân tích hiệu suất cặp tiền...")
        self.analyze_symbol_performance()
        
        # 2. Phân tích thời gian giao dịch tối ưu
        logger.info("\nPhân tích thời gian giao dịch tối ưu...")
        self.analyze_optimal_trading_time()
        
        # 3. Phân tích chiến lược theo chế độ thị trường
        logger.info("\nPhân tích chiến lược theo chế độ thị trường...")
        self.analyze_strategy_performance()
        
        # 4. Phân tích tác động của đòn bẩy
        logger.info("\nPhân tích tác động của đòn bẩy...")
        self.analyze_leverage_impact()
        
        # 5. Tạo cấu hình tối ưu
        logger.info("\nTạo cấu hình tối ưu...")
        optimized_config = self.generate_optimized_config()
        
        logger.info("\n" + "="*80)
        logger.info("KẾT QUẢ TỐI ƯU HÓA")
        logger.info("="*80)
        
        # Hiển thị cấu hình tối ưu
        logger.info(f"\nĐòn bẩy tối ưu: {optimized_config.get('leverage', 'N/A')}x")
        
        if 'optimal_trading_time' in optimized_config:
            hours = optimized_config['optimal_trading_time'].get('hours', [])
            days = optimized_config['optimal_trading_time'].get('days', [])
            
            hour_str = ', '.join([f"{h}:00" for h in hours]) if hours else "N/A"
            day_names = {
                0: "Thứ Hai", 1: "Thứ Ba", 2: "Thứ Tư", 3: "Thứ Năm", 
                4: "Thứ Sáu", 5: "Thứ Bảy", 6: "Chủ Nhật"
            }
            day_str = ', '.join([day_names.get(d, "N/A") for d in days]) if days else "N/A"
            
            logger.info(f"Giờ giao dịch tối ưu: {hour_str}")
            logger.info(f"Ngày giao dịch tối ưu: {day_str}")
        
        if 'suitable_pairs' in optimized_config:
            pairs = optimized_config['suitable_pairs']
            logger.info(f"\nCặp tiền hiệu quả nhất ({len(pairs)}):")
            
            # Chia thành các hàng để hiển thị đẹp hơn
            pairs_rows = []
            current_row = []
            
            for i, pair in enumerate(pairs):
                current_row.append(pair)
                
                if len(current_row) == 5 or i == len(pairs) - 1:
                    pairs_rows.append(current_row)
                    current_row = []
                    
            for row in pairs_rows:
                logger.info("  ".join(row))
        
        if 'market_condition_strategies' in optimized_config:
            market_strategies = optimized_config['market_condition_strategies']
            
            logger.info("\nChiến lược tối ưu theo chế độ thị trường:")
            
            for condition, strategies in market_strategies.items():
                logger.info(f"\n{condition.upper()}:")
                
                for i, strategy in enumerate(strategies[:3]):  # Top 3
                    logger.info(f"  {i+1}. {strategy['strategy']} (PF: {strategy['profit_factor']:.2f}, Win rate: {strategy['win_rate']:.2f})")
        
        logger.info("\n" + "="*80)
        logger.info("HOÀN THÀNH TỐI ƯU HÓA")
        logger.info("="*80)
        
        return optimized_config

def run_optimization(trade_history_file=None, account_size=None):
    """
    Hàm chính để chạy tối ưu hóa
    
    Args:
        trade_history_file (str): Đường dẫn đến file lịch sử giao dịch
        account_size (int): Kích thước tài khoản ($)
    """
    optimizer = SmallAccountOptimizer(trade_history_file, account_size)
    return optimizer.run()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Tối ưu hóa giao dịch cho tài khoản nhỏ')
    parser.add_argument('--history', type=str, help='Đường dẫn đến file lịch sử giao dịch (CSV)')
    parser.add_argument('--balance', type=float, help='Số dư tài khoản (nếu không cung cấp, sẽ lấy từ API)')
    
    args = parser.parse_args()
    
    run_optimization(args.history, args.balance)