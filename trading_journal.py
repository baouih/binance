#!/usr/bin/env python3
"""
Hệ thống nhật ký giao dịch tích hợp với phân tích thị trường

Script này giúp người dùng:
1. Lưu trữ và theo dõi các giao dịch
2. Phân tích kết quả giao dịch để cải thiện chiến lược
3. So sánh quyết định của người dùng với khuyến nghị của hệ thống
4. Tìm hiểu lý do thành công/thất bại và cải thiện điểm vào lệnh

Cách sử dụng:
    # Để ghi nhật một giao dịch mới
    python trading_journal.py add --symbol BTCUSDT --direction long --entry 40000 --exit 42000 --volume 0.1 --notes "Giao dịch dựa trên đột phá kháng cự"
    
    # Để xem phân tích các giao dịch
    python trading_journal.py analyze --period 30
    
    # Để so sánh với gợi ý của hệ thống
    python trading_journal.py compare --symbol BTCUSDT
"""

import os
import sys
import json
import argparse
import logging
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any, Union
from market_analysis_system import MarketAnalysisSystem
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("trading_journal")

# Đường dẫn file
JOURNAL_FILE = "reports/trading_journal/journal.json"

class TradingJournal:
    """Nhật ký giao dịch tích hợp với phân tích thị trường"""
    
    def __init__(self):
        """Khởi tạo nhật ký giao dịch"""
        self.analyzer = MarketAnalysisSystem()
        self.trades = self._load_trades()
        # Đảm bảo thư mục tồn tại
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Tạo các thư mục cần thiết"""
        directories = [
            "reports/trading_journal",
            "charts/trading_journal"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Đã tạo thư mục: {directory}")
    
    def _load_trades(self) -> List[Dict]:
        """
        Tải danh sách giao dịch từ file
        
        Returns:
            List[Dict]: Danh sách giao dịch
        """
        if os.path.exists(JOURNAL_FILE):
            try:
                with open(JOURNAL_FILE, 'r') as f:
                    trades = json.load(f)
                logger.info(f"Đã tải {len(trades)} giao dịch từ {JOURNAL_FILE}")
                return trades
            except Exception as e:
                logger.error(f"Lỗi khi tải giao dịch: {str(e)}")
        
        return []
    
    def _save_trades(self) -> bool:
        """
        Lưu danh sách giao dịch vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)
            
            with open(JOURNAL_FILE, 'w') as f:
                json.dump(self.trades, f, indent=4)
            
            logger.info(f"Đã lưu {len(self.trades)} giao dịch vào {JOURNAL_FILE}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu giao dịch: {str(e)}")
            return False
    
    def add_trade(self, trade_data: Dict) -> bool:
        """
        Thêm một giao dịch mới
        
        Args:
            trade_data (Dict): Thông tin giao dịch
            
        Returns:
            bool: True nếu thêm thành công, False nếu thất bại
        """
        try:
            # Thêm ID giao dịch
            if 'trade_id' not in trade_data:
                timestamp = int(datetime.datetime.now().timestamp())
                symbol = trade_data.get('symbol', 'UNKNOWN')
                trade_data['trade_id'] = f"{timestamp}-{symbol}"
            
            # Đảm bảo có timestamp
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Tính toán lợi nhuận
            entry_price = float(trade_data.get('entry_price', 0))
            exit_price = float(trade_data.get('exit_price', 0))
            volume = float(trade_data.get('volume', 0))
            direction = trade_data.get('direction', 'long')
            
            if entry_price > 0 and exit_price > 0 and volume > 0:
                if direction.lower() == 'long':
                    profit_pct = (exit_price - entry_price) / entry_price * 100
                    profit_amount = (exit_price - entry_price) * volume
                else:  # short
                    profit_pct = (entry_price - exit_price) / entry_price * 100
                    profit_amount = (entry_price - exit_price) * volume
                
                trade_data['profit_pct'] = profit_pct
                trade_data['profit_amount'] = profit_amount
                trade_data['result'] = 'win' if profit_pct > 0 else 'loss'
            
            # Thêm thông tin thị trường
            if 'market_conditions' not in trade_data:
                try:
                    market_analysis = self.analyzer.analyze_global_market()
                    symbol_analysis = self.analyzer.analyze_symbol(trade_data['symbol'])
                    
                    trade_data['market_conditions'] = {
                        'global_trend': market_analysis.get('market_trend'),
                        'global_regime': market_analysis.get('market_regime'),
                        'symbol_regime': symbol_analysis.get('market_regime'),
                        'symbol_score': symbol_analysis.get('score')
                    }
                except Exception as e:
                    logger.warning(f"Không thể thêm thông tin thị trường: {str(e)}")
            
            # Phân tích quyết định
            if entry_price > 0 and direction:
                try:
                    can_trade, reasons = self.analyzer.check_trading_conditions(
                        trade_data['symbol'], 
                        trade_data.get('timeframe', '1h'), 
                        direction
                    )
                    
                    trade_data['system_recommendation'] = {
                        'would_trade': can_trade,
                        'reasons': reasons
                    }
                except Exception as e:
                    logger.warning(f"Không thể phân tích quyết định: {str(e)}")
            
            # Thêm vào danh sách
            self.trades.append(trade_data)
            
            # Lưu vào file
            self._save_trades()
            
            logger.info(f"Đã thêm giao dịch mới cho {trade_data.get('symbol')} với ID {trade_data.get('trade_id')}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm giao dịch: {str(e)}")
            return False
    
    def analyze_trades(self, period_days: int = 30) -> Dict:
        """
        Phân tích các giao dịch trong khoảng thời gian
        
        Args:
            period_days (int): Số ngày gần đây để phân tích
            
        Returns:
            Dict: Kết quả phân tích
        """
        try:
            # Lọc giao dịch trong khoảng thời gian
            current_time = datetime.datetime.now()
            start_date = current_time - datetime.timedelta(days=period_days)
            
            filtered_trades = []
            for trade in self.trades:
                try:
                    trade_time = datetime.datetime.strptime(trade.get('timestamp', '1970-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S')
                    if trade_time >= start_date:
                        filtered_trades.append(trade)
                except Exception:
                    # Bỏ qua các giao dịch có định dạng thời gian không đúng
                    pass
            
            if not filtered_trades:
                logger.warning(f"Không có giao dịch nào trong {period_days} ngày qua")
                return {
                    "period_days": period_days,
                    "total_trades": 0,
                    "error": "Không có giao dịch nào trong khoảng thời gian"
                }
            
            # Tính toán các chỉ số
            total_trades = len(filtered_trades)
            winning_trades = [t for t in filtered_trades if t.get('result') == 'win']
            losing_trades = [t for t in filtered_trades if t.get('result') == 'loss']
            
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            
            win_rate = win_count / total_trades if total_trades > 0 else 0
            
            total_profit = sum(t.get('profit_amount', 0) for t in filtered_trades)
            avg_profit = total_profit / total_trades if total_trades > 0 else 0
            
            avg_win = sum(t.get('profit_amount', 0) for t in winning_trades) / win_count if win_count > 0 else 0
            avg_loss = sum(t.get('profit_amount', 0) for t in losing_trades) / loss_count if loss_count > 0 else 0
            
            profit_factor = abs(sum(t.get('profit_amount', 0) for t in winning_trades) / 
                             sum(t.get('profit_amount', 0) for t in losing_trades)) if sum(t.get('profit_amount', 0) for t in losing_trades) != 0 else float('inf')
            
            # Phân tích theo symbol
            symbols_analysis = {}
            for trade in filtered_trades:
                symbol = trade.get('symbol')
                if symbol not in symbols_analysis:
                    symbols_analysis[symbol] = {
                        'count': 0,
                        'wins': 0,
                        'losses': 0,
                        'profit': 0
                    }
                
                symbols_analysis[symbol]['count'] += 1
                if trade.get('result') == 'win':
                    symbols_analysis[symbol]['wins'] += 1
                else:
                    symbols_analysis[symbol]['losses'] += 1
                
                symbols_analysis[symbol]['profit'] += trade.get('profit_amount', 0)
            
            # Phân tích theo hướng giao dịch
            direction_analysis = {
                'long': {
                    'count': 0,
                    'wins': 0,
                    'losses': 0,
                    'profit': 0
                },
                'short': {
                    'count': 0,
                    'wins': 0,
                    'losses': 0,
                    'profit': 0
                }
            }
            
            for trade in filtered_trades:
                direction = trade.get('direction', 'long').lower()
                if direction not in direction_analysis:
                    direction = 'long'  # Mặc định
                
                direction_analysis[direction]['count'] += 1
                if trade.get('result') == 'win':
                    direction_analysis[direction]['wins'] += 1
                else:
                    direction_analysis[direction]['losses'] += 1
                
                direction_analysis[direction]['profit'] += trade.get('profit_amount', 0)
            
            # Phân tích theo điều kiện thị trường
            market_analysis = {
                'trending_up': {
                    'count': 0,
                    'wins': 0,
                    'profit': 0
                },
                'trending_down': {
                    'count': 0,
                    'wins': 0,
                    'profit': 0
                },
                'ranging': {
                    'count': 0,
                    'wins': 0,
                    'profit': 0
                },
                'high_volatility': {
                    'count': 0,
                    'wins': 0,
                    'profit': 0
                },
                'low_volatility': {
                    'count': 0,
                    'wins': 0,
                    'profit': 0
                },
                'unknown': {
                    'count': 0,
                    'wins': 0,
                    'profit': 0
                }
            }
            
            for trade in filtered_trades:
                market_regime = trade.get('market_conditions', {}).get('global_regime', 'unknown')
                if market_regime not in market_analysis:
                    market_regime = 'unknown'
                
                market_analysis[market_regime]['count'] += 1
                if trade.get('result') == 'win':
                    market_analysis[market_regime]['wins'] += 1
                
                market_analysis[market_regime]['profit'] += trade.get('profit_amount', 0)
            
            # So sánh người dùng vs hệ thống
            system_comparison = {
                'agreed_and_won': 0,
                'agreed_and_lost': 0,
                'disagreed_and_won': 0,
                'disagreed_and_lost': 0
            }
            
            for trade in filtered_trades:
                would_trade = trade.get('system_recommendation', {}).get('would_trade', False)
                is_win = trade.get('result') == 'win'
                
                if would_trade and is_win:
                    system_comparison['agreed_and_won'] += 1
                elif would_trade and not is_win:
                    system_comparison['agreed_and_lost'] += 1
                elif not would_trade and is_win:
                    system_comparison['disagreed_and_won'] += 1
                elif not would_trade and not is_win:
                    system_comparison['disagreed_and_lost'] += 1
            
            # Tổng hợp kết quả
            result = {
                "period_days": period_days,
                "total_trades": total_trades,
                "win_count": win_count,
                "loss_count": loss_count,
                "win_rate": win_rate,
                "total_profit": total_profit,
                "avg_profit": avg_profit,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "symbols_analysis": symbols_analysis,
                "direction_analysis": direction_analysis,
                "market_analysis": market_analysis,
                "system_comparison": system_comparison,
                "recent_trades": filtered_trades[-10:]  # 10 giao dịch gần nhất
            }
            
            # Tạo biểu đồ phân tích
            self._create_performance_charts(result)
            
            logger.info(f"Đã phân tích {total_trades} giao dịch trong {period_days} ngày qua")
            return result
        except Exception as e:
            logger.error(f"Lỗi khi phân tích giao dịch: {str(e)}")
            return {
                "period_days": period_days,
                "total_trades": 0,
                "error": str(e)
            }
    
    def compare_with_system(self, symbol: str, timeframe: str = None) -> Dict:
        """
        So sánh các giao dịch của người dùng với khuyến nghị của hệ thống
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str, optional): Khung thời gian
            
        Returns:
            Dict: Kết quả so sánh
        """
        if timeframe is None:
            timeframe = self.analyzer.config["primary_timeframe"]
        
        logger.info(f"So sánh giao dịch của người dùng với hệ thống cho {symbol} trên {timeframe}")
        
        try:
            # Lọc giao dịch của symbol
            symbol_trades = [t for t in self.trades if t.get('symbol') == symbol]
            
            if not symbol_trades:
                logger.warning(f"Không có giao dịch nào cho {symbol}")
                return {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": "Không có giao dịch nào cho symbol này"
                }
            
            # Phân tích hiện tại của hệ thống
            current_analysis = self.analyzer.analyze_symbol(symbol, timeframe)
            
            # Kiểm tra điều kiện giao dịch hiện tại
            can_trade_long, long_reasons = self.analyzer.check_trading_conditions(symbol, timeframe, "long")
            can_trade_short, short_reasons = self.analyzer.check_trading_conditions(symbol, timeframe, "short")
            
            # Phân tích theo kết quả
            winning_trades = [t for t in symbol_trades if t.get('result') == 'win']
            losing_trades = [t for t in symbol_trades if t.get('result') == 'loss']
            
            # Phân tích theo hướng
            long_trades = [t for t in symbol_trades if t.get('direction') == 'long']
            short_trades = [t for t in symbol_trades if t.get('direction') == 'short']
            
            # Phân tích theo sự đồng thuận với hệ thống
            agreed_trades = [t for t in symbol_trades if t.get('system_recommendation', {}).get('would_trade', False)]
            disagreed_trades = [t for t in symbol_trades if not t.get('system_recommendation', {}).get('would_trade', False)]
            
            # Các giao dịch chống lại khuyến nghị nhưng thắng
            successful_disagreements = [t for t in disagreed_trades if t.get('result') == 'win']
            
            # Tìm lý do phổ biến nhất dẫn đến thắng/thua
            winning_notes = [t.get('notes', '') for t in winning_trades]
            losing_notes = [t.get('notes', '') for t in losing_trades]
            
            # Tổng hợp kết quả
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "total_trades": len(symbol_trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "long_trades": len(long_trades),
                "short_trades": len(short_trades),
                "agreed_with_system": len(agreed_trades),
                "disagreed_with_system": len(disagreed_trades),
                "successful_disagreements": len(successful_disagreements),
                "win_rate": len(winning_trades) / len(symbol_trades) if symbol_trades else 0,
                "long_win_rate": len([t for t in long_trades if t.get('result') == 'win']) / len(long_trades) if long_trades else 0,
                "short_win_rate": len([t for t in short_trades if t.get('result') == 'win']) / len(short_trades) if short_trades else 0,
                "agreed_win_rate": len([t for t in agreed_trades if t.get('result') == 'win']) / len(agreed_trades) if agreed_trades else 0,
                "disagreed_win_rate": len([t for t in disagreed_trades if t.get('result') == 'win']) / len(disagreed_trades) if disagreed_trades else 0,
                "current_analysis": {
                    "score": current_analysis.get("score"),
                    "recommendation": current_analysis.get("recommendation"),
                    "can_trade_long": can_trade_long,
                    "can_trade_short": can_trade_short,
                    "long_reasons": long_reasons,
                    "short_reasons": short_reasons
                },
                "recent_trades": symbol_trades[-5:],  # 5 giao dịch gần nhất
                "winning_notes": winning_notes,
                "losing_notes": losing_notes
            }
            
            logger.info(f"Đã so sánh {len(symbol_trades)} giao dịch của người dùng với hệ thống cho {symbol}")
            return result
        except Exception as e:
            logger.error(f"Lỗi khi so sánh giao dịch với hệ thống: {str(e)}")
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "error": str(e)
            }
    
    def _create_performance_charts(self, analysis_result: Dict) -> bool:
        """
        Tạo biểu đồ phân tích hiệu suất
        
        Args:
            analysis_result (Dict): Kết quả phân tích
            
        Returns:
            bool: True nếu tạo thành công, False nếu thất bại
        """
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Biểu đồ tỷ lệ thắng/thua
            plt.figure(figsize=(12, 8))
            plt.subplot(2, 2, 1)
            plt.pie([analysis_result['win_count'], analysis_result['loss_count']], 
                   labels=['Thắng', 'Thua'], 
                   autopct='%1.1f%%',
                   colors=['green', 'red'])
            plt.title('Tỷ lệ thắng/thua')
            
            # Biểu đồ theo symbol
            plt.subplot(2, 2, 2)
            symbols = list(analysis_result['symbols_analysis'].keys())
            profits = [analysis_result['symbols_analysis'][s]['profit'] for s in symbols]
            colors = ['green' if p > 0 else 'red' for p in profits]
            
            plt.bar(symbols, profits, color=colors)
            plt.title('Lợi nhuận theo Symbol')
            plt.xticks(rotation=45)
            
            # Biểu đồ theo hướng giao dịch
            plt.subplot(2, 2, 3)
            directions = list(analysis_result['direction_analysis'].keys())
            direction_counts = [analysis_result['direction_analysis'][d]['count'] for d in directions]
            direction_wins = [analysis_result['direction_analysis'][d]['wins'] for d in directions]
            
            x = np.arange(len(directions))
            width = 0.35
            
            plt.bar(x - width/2, direction_counts, width, label='Tổng số')
            plt.bar(x + width/2, direction_wins, width, label='Thắng')
            plt.xticks(x, directions)
            plt.legend()
            plt.title('Giao dịch theo hướng')
            
            # Biểu đồ theo chế độ thị trường
            plt.subplot(2, 2, 4)
            regimes = list(analysis_result['market_analysis'].keys())
            regime_profits = [analysis_result['market_analysis'][r]['profit'] for r in regimes]
            regime_colors = ['green' if p > 0 else 'red' for p in regime_profits]
            
            plt.bar(regimes, regime_profits, color=regime_colors)
            plt.title('Lợi nhuận theo chế độ thị trường')
            plt.xticks(rotation=45)
            
            # Lưu biểu đồ
            plt.tight_layout()
            chart_path = f"charts/trading_journal/performance_{timestamp}.png"
            plt.savefig(chart_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ phân tích hiệu suất tại {chart_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân tích hiệu suất: {str(e)}")
            return False
    
    def print_analysis_summary(self, analysis_result: Dict) -> None:
        """
        In tóm tắt phân tích ra console
        
        Args:
            analysis_result (Dict): Kết quả phân tích
        """
        if 'error' in analysis_result:
            print(f"\nLỗi: {analysis_result['error']}")
            return
        
        print("\n" + "="*80)
        print(f"TÓM TẮT HIỆU SUẤT GIAO DỊCH ({analysis_result['period_days']} NGÀY QUA)")
        print("="*80)
        
        print(f"\nTổng số giao dịch: {analysis_result['total_trades']}")
        print(f"Số giao dịch thắng: {analysis_result['win_count']}")
        print(f"Số giao dịch thua: {analysis_result['loss_count']}")
        print(f"Tỷ lệ thắng: {analysis_result['win_rate']*100:.2f}%")
        print(f"Tổng lợi nhuận: {analysis_result['total_profit']:.2f}")
        print(f"Lợi nhuận trung bình: {analysis_result['avg_profit']:.2f}")
        print(f"Lợi nhuận thắng trung bình: {analysis_result['avg_win']:.2f}")
        print(f"Lỗ thua trung bình: {analysis_result['avg_loss']:.2f}")
        print(f"Hệ số lợi nhuận: {analysis_result['profit_factor']:.2f}")
        
        # Phân tích theo symbol
        print("\n" + "-"*80)
        print("PHÂN TÍCH THEO SYMBOL")
        print("-"*80)
        
        symbols_data = []
        for symbol, data in analysis_result['symbols_analysis'].items():
            win_rate = data['wins'] / data['count'] if data['count'] > 0 else 0
            symbols_data.append([
                symbol,
                data['count'],
                data['wins'],
                data['losses'],
                f"{win_rate*100:.2f}%",
                data['profit']
            ])
        
        # Sắp xếp theo profit giảm dần
        symbols_data.sort(key=lambda x: x[5], reverse=True)
        
        print(tabulate(symbols_data, headers=[
            "Symbol", "Số lượng", "Thắng", "Thua", "Tỷ lệ thắng", "Lợi nhuận"
        ], tablefmt="grid"))
        
        # Phân tích theo hướng giao dịch
        print("\n" + "-"*80)
        print("PHÂN TÍCH THEO HƯỚNG GIAO DỊCH")
        print("-"*80)
        
        direction_data = []
        for direction, data in analysis_result['direction_analysis'].items():
            win_rate = data['wins'] / data['count'] if data['count'] > 0 else 0
            direction_data.append([
                direction.upper(),
                data['count'],
                data['wins'],
                data['losses'],
                f"{win_rate*100:.2f}%",
                data['profit']
            ])
        
        print(tabulate(direction_data, headers=[
            "Hướng", "Số lượng", "Thắng", "Thua", "Tỷ lệ thắng", "Lợi nhuận"
        ], tablefmt="grid"))
        
        # Phân tích theo chế độ thị trường
        print("\n" + "-"*80)
        print("PHÂN TÍCH THEO CHẾ ĐỘ THỊ TRƯỜNG")
        print("-"*80)
        
        market_data = []
        for regime, data in analysis_result['market_analysis'].items():
            if data['count'] > 0:  # Chỉ hiện những chế độ có giao dịch
                win_rate = data['wins'] / data['count'] if data['count'] > 0 else 0
                market_data.append([
                    regime,
                    data['count'],
                    data['wins'],
                    data['count'] - data['wins'],
                    f"{win_rate*100:.2f}%",
                    data['profit']
                ])
        
        # Sắp xếp theo win rate giảm dần
        market_data.sort(key=lambda x: float(x[4].rstrip('%')), reverse=True)
        
        print(tabulate(market_data, headers=[
            "Chế độ thị trường", "Số lượng", "Thắng", "Thua", "Tỷ lệ thắng", "Lợi nhuận"
        ], tablefmt="grid"))
        
        # So sánh với hệ thống
        print("\n" + "-"*80)
        print("SO SÁNH VỚI HỆ THỐNG")
        print("-"*80)
        
        system_data = [
            ["Đồng thuận và thắng", analysis_result['system_comparison']['agreed_and_won']],
            ["Đồng thuận và thua", analysis_result['system_comparison']['agreed_and_lost']],
            ["Không đồng thuận và thắng", analysis_result['system_comparison']['disagreed_and_won']],
            ["Không đồng thuận và thua", analysis_result['system_comparison']['disagreed_and_lost']]
        ]
        
        print(tabulate(system_data, headers=[
            "Trường hợp", "Số lượng"
        ], tablefmt="grid"))
        
        # Giao dịch gần đây
        print("\n" + "-"*80)
        print("CÁC GIAO DỊCH GẦN ĐÂY")
        print("-"*80)
        
        recent_data = []
        for trade in analysis_result['recent_trades']:
            recent_data.append([
                trade.get('timestamp', ''),
                trade.get('symbol', ''),
                trade.get('direction', '').upper(),
                trade.get('entry_price', 0),
                trade.get('exit_price', 0),
                f"{trade.get('profit_pct', 0):.2f}%",
                trade.get('result', '').upper(),
                'Có' if trade.get('system_recommendation', {}).get('would_trade', False) else 'Không'
            ])
        
        print(tabulate(recent_data, headers=[
            "Thời gian", "Symbol", "Hướng", "Giá vào", "Giá ra", "Lợi nhuận", "Kết quả", "Hệ thống đồng ý"
        ], tablefmt="grid"))
        
        print("\n" + "="*80)
        print("GỢI Ý CẢI THIỆN")
        print("="*80)
        
        # Tìm các symbol hiệu quả nhất
        best_symbols = sorted(
            [(s, d) for s, d in analysis_result['symbols_analysis'].items() if d['count'] >= 3],
            key=lambda x: x[1]['wins'] / x[1]['count'] if x[1]['count'] > 0 else 0,
            reverse=True
        )[:3]
        
        if best_symbols:
            print("\nCác cặp tiền hiệu quả nhất:")
            for symbol, data in best_symbols:
                win_rate = data['wins'] / data['count'] if data['count'] > 0 else 0
                print(f"  - {symbol}: Tỷ lệ thắng {win_rate*100:.2f}%, Lợi nhuận {data['profit']:.2f}")
        
        # Tìm chế độ thị trường hiệu quả nhất
        best_regimes = sorted(
            [(r, d) for r, d in analysis_result['market_analysis'].items() if d['count'] >= 3],
            key=lambda x: x[1]['wins'] / x[1]['count'] if x[1]['count'] > 0 else 0,
            reverse=True
        )[:2]
        
        if best_regimes:
            print("\nCác chế độ thị trường hiệu quả nhất:")
            for regime, data in best_regimes:
                win_rate = data['wins'] / data['count'] if data['count'] > 0 else 0
                print(f"  - {regime}: Tỷ lệ thắng {win_rate*100:.2f}%, Lợi nhuận {data['profit']:.2f}")
        
        # Gợi ý cải thiện
        agreed_rate = (analysis_result['system_comparison']['agreed_and_won'] + 
                     analysis_result['system_comparison']['agreed_and_lost']) / analysis_result['total_trades'] if analysis_result['total_trades'] > 0 else 0
        
        agreed_win_rate = (analysis_result['system_comparison']['agreed_and_won'] / 
                         (analysis_result['system_comparison']['agreed_and_won'] + 
                         analysis_result['system_comparison']['agreed_and_lost'])) if (analysis_result['system_comparison']['agreed_and_won'] + 
                                                                            analysis_result['system_comparison']['agreed_and_lost']) > 0 else 0
        
        disagreed_win_rate = (analysis_result['system_comparison']['disagreed_and_won'] / 
                            (analysis_result['system_comparison']['disagreed_and_won'] + 
                            analysis_result['system_comparison']['disagreed_and_lost'])) if (analysis_result['system_comparison']['disagreed_and_won'] + 
                                                                                analysis_result['system_comparison']['disagreed_and_lost']) > 0 else 0
        
        print("\nGợi ý cải thiện:")
        if agreed_win_rate > disagreed_win_rate:
            print("  - Nên tuân thủ nhiều hơn với khuyến nghị của hệ thống")
            print(f"    (Tỷ lệ thắng khi đồng thuận: {agreed_win_rate*100:.2f}% vs. khi không đồng thuận: {disagreed_win_rate*100:.2f}%)")
        else:
            print("  - Bạn dường như có insight tốt hơn hệ thống, cần xem xét cải thiện hệ thống")
            print(f"    (Tỷ lệ thắng khi không đồng thuận: {disagreed_win_rate*100:.2f}% vs. khi đồng thuận: {agreed_win_rate*100:.2f}%)")
        
        # Xác định hướng giao dịch tốt hơn
        long_data = analysis_result['direction_analysis']['long']
        short_data = analysis_result['direction_analysis']['short']
        
        long_win_rate = long_data['wins'] / long_data['count'] if long_data['count'] > 0 else 0
        short_win_rate = short_data['wins'] / short_data['count'] if short_data['count'] > 0 else 0
        
        if long_win_rate > short_win_rate and long_data['count'] >= 3 and short_data['count'] >= 3:
            print(f"  - Bạn có vẻ giỏi hơn trong giao dịch LONG (Tỷ lệ thắng: {long_win_rate*100:.2f}% vs. SHORT: {short_win_rate*100:.2f}%)")
        elif short_win_rate > long_win_rate and long_data['count'] >= 3 and short_data['count'] >= 3:
            print(f"  - Bạn có vẻ giỏi hơn trong giao dịch SHORT (Tỷ lệ thắng: {short_win_rate*100:.2f}% vs. LONG: {long_win_rate*100:.2f}%)")
        
        print("\n" + "="*80)
        print(f"Biểu đồ phân tích hiệu suất được lưu trong thư mục charts/trading_journal/")
        print("="*80 + "\n")
    
    def print_comparison_summary(self, comparison_result: Dict) -> None:
        """
        In tóm tắt so sánh ra console
        
        Args:
            comparison_result (Dict): Kết quả so sánh
        """
        if 'error' in comparison_result:
            print(f"\nLỗi: {comparison_result['error']}")
            return
        
        symbol = comparison_result['symbol']
        timeframe = comparison_result['timeframe']
        
        print("\n" + "="*80)
        print(f"SO SÁNH GIAO DỊCH NGƯỜI DÙNG vs. HỆ THỐNG: {symbol} - {timeframe}")
        print("="*80)
        
        # Thông tin chung
        print(f"\nTổng số giao dịch: {comparison_result['total_trades']}")
        print(f"Số giao dịch thắng: {comparison_result['winning_trades']}")
        print(f"Số giao dịch thua: {comparison_result['losing_trades']}")
        print(f"Tỷ lệ thắng: {comparison_result['win_rate']*100:.2f}%")
        
        # Phân tích theo hướng
        print("\n" + "-"*80)
        print("PHÂN TÍCH THEO HƯỚNG GIAO DỊCH")
        print("-"*80)
        print(f"Số giao dịch LONG: {comparison_result['long_trades']}")
        print(f"Số giao dịch SHORT: {comparison_result['short_trades']}")
        print(f"Tỷ lệ thắng LONG: {comparison_result['long_win_rate']*100:.2f}%")
        print(f"Tỷ lệ thắng SHORT: {comparison_result['short_win_rate']*100:.2f}%")
        
        # So sánh với hệ thống
        print("\n" + "-"*80)
        print("SO SÁNH VỚI HỆ THỐNG")
        print("-"*80)
        print(f"Số giao dịch đồng thuận với hệ thống: {comparison_result['agreed_with_system']}")
        print(f"Số giao dịch không đồng thuận với hệ thống: {comparison_result['disagreed_with_system']}")
        print(f"Tỷ lệ thắng khi đồng thuận: {comparison_result['agreed_win_rate']*100:.2f}%")
        print(f"Tỷ lệ thắng khi không đồng thuận: {comparison_result['disagreed_win_rate']*100:.2f}%")
        print(f"Số giao dịch thắng khi không đồng thuận: {comparison_result['successful_disagreements']}")
        
        # Phân tích hiện tại của hệ thống
        print("\n" + "-"*80)
        print("PHÂN TÍCH HIỆN TẠI CỦA HỆ THỐNG")
        print("-"*80)
        current = comparison_result['current_analysis']
        print(f"Điểm hiện tại: {current['score']}/100")
        print(f"Khuyến nghị: {current['recommendation'].upper()}")
        print(f"Có thể giao dịch LONG: {'Có' if current['can_trade_long'] else 'Không'}")
        print(f"Có thể giao dịch SHORT: {'Có' if current['can_trade_short'] else 'Không'}")
        
        # Các lý do không giao dịch LONG
        if not current['can_trade_long'] and current['long_reasons']:
            print("\nLý do không giao dịch LONG:")
            for i, reason in enumerate(current['long_reasons'], 1):
                print(f"  {i}. {reason.get('reason', '')}")
        
        # Các lý do không giao dịch SHORT
        if not current['can_trade_short'] and current['short_reasons']:
            print("\nLý do không giao dịch SHORT:")
            for i, reason in enumerate(current['short_reasons'], 1):
                print(f"  {i}. {reason.get('reason', '')}")
        
        # Giao dịch gần đây
        print("\n" + "-"*80)
        print("CÁC GIAO DỊCH GẦN ĐÂY")
        print("-"*80)
        
        recent_data = []
        for trade in comparison_result['recent_trades']:
            recent_data.append([
                trade.get('timestamp', ''),
                trade.get('direction', '').upper(),
                trade.get('entry_price', 0),
                trade.get('exit_price', 0),
                f"{trade.get('profit_pct', 0):.2f}%",
                trade.get('result', '').upper(),
                'Có' if trade.get('system_recommendation', {}).get('would_trade', False) else 'Không',
                trade.get('notes', '')[:30] + ('...' if len(trade.get('notes', '')) > 30 else '')
            ])
        
        print(tabulate(recent_data, headers=[
            "Thời gian", "Hướng", "Giá vào", "Giá ra", "Lợi nhuận", "Kết quả", 
            "Hệ thống đồng ý", "Ghi chú"
        ], tablefmt="grid"))
        
        # Ghi chú giao dịch thắng
        if comparison_result['winning_notes']:
            print("\n" + "-"*80)
            print("GHI CHÚ GIAO DỊCH THẮNG")
            print("-"*80)
            for i, note in enumerate(comparison_result['winning_notes'][:5], 1):
                if note:
                    print(f"{i}. {note}")
        
        # Gọi ý
        print("\n" + "="*80)
        print("GỢI Ý CẢI THIỆN")
        print("="*80)
        
        if comparison_result['agreed_win_rate'] > comparison_result['disagreed_win_rate']:
            print("  - Bạn nên tuân thủ nhiều hơn với khuyến nghị của hệ thống")
            print(f"    (Tỷ lệ thắng khi đồng thuận: {comparison_result['agreed_win_rate']*100:.2f}% vs. khi không đồng thuận: {comparison_result['disagreed_win_rate']*100:.2f}%)")
        else:
            print("  - Bạn có insight tốt cho cặp tiền này, hãy ghi lại các yếu tố quyết định")
            print(f"    (Tỷ lệ thắng khi không đồng thuận: {comparison_result['disagreed_win_rate']*100:.2f}% vs. khi đồng thuận: {comparison_result['agreed_win_rate']*100:.2f}%)")
        
        if comparison_result['long_win_rate'] > comparison_result['short_win_rate'] and comparison_result['long_trades'] >= 3 and comparison_result['short_trades'] >= 3:
            print(f"  - Bạn có vẻ giỏi hơn trong giao dịch LONG cho {symbol}")
            print(f"    (Tỷ lệ thắng LONG: {comparison_result['long_win_rate']*100:.2f}% vs. SHORT: {comparison_result['short_win_rate']*100:.2f}%)")
        elif comparison_result['short_win_rate'] > comparison_result['long_win_rate'] and comparison_result['long_trades'] >= 3 and comparison_result['short_trades'] >= 3:
            print(f"  - Bạn có vẻ giỏi hơn trong giao dịch SHORT cho {symbol}")
            print(f"    (Tỷ lệ thắng SHORT: {comparison_result['short_win_rate']*100:.2f}% vs. LONG: {comparison_result['long_win_rate']*100:.2f}%)")
        
        print("\n" + "="*80)

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Nhật ký giao dịch")
    subparsers = parser.add_subparsers(dest='command', help='Lệnh')
    
    # Thêm giao dịch
    add_parser = subparsers.add_parser('add', help='Thêm giao dịch mới')
    add_parser.add_argument('--symbol', type=str, required=True, help='Mã cặp tiền (VD: BTCUSDT)')
    add_parser.add_argument('--direction', type=str, required=True, choices=['long', 'short'], help='Hướng giao dịch')
    add_parser.add_argument('--entry', type=float, required=True, help='Giá vào')
    add_parser.add_argument('--exit', type=float, required=True, help='Giá ra')
    add_parser.add_argument('--volume', type=float, required=True, help='Khối lượng giao dịch')
    add_parser.add_argument('--timeframe', type=str, default='1h', help='Khung thời gian (VD: 1h, 4h, 1d)')
    add_parser.add_argument('--notes', type=str, default='', help='Ghi chú về giao dịch')
    
    # Phân tích giao dịch
    analyze_parser = subparsers.add_parser('analyze', help='Phân tích giao dịch')
    analyze_parser.add_argument('--period', type=int, default=30, help='Khoảng thời gian phân tích (ngày)')
    
    # So sánh với hệ thống
    compare_parser = subparsers.add_parser('compare', help='So sánh với khuyến nghị của hệ thống')
    compare_parser.add_argument('--symbol', type=str, required=True, help='Mã cặp tiền (VD: BTCUSDT)')
    compare_parser.add_argument('--timeframe', type=str, default=None, help='Khung thời gian (VD: 1h, 4h, 1d)')
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    journal = TradingJournal()
    
    if args.command == 'add':
        print(f"\nĐang thêm giao dịch mới cho {args.symbol}...")
        
        trade_data = {
            'symbol': args.symbol,
            'direction': args.direction,
            'entry_price': args.entry,
            'exit_price': args.exit,
            'volume': args.volume,
            'timeframe': args.timeframe,
            'notes': args.notes
        }
        
        if journal.add_trade(trade_data):
            print(f"Đã thêm giao dịch {args.direction} {args.symbol} thành công!")
        else:
            print("Lỗi khi thêm giao dịch!")
    
    elif args.command == 'analyze':
        print(f"\nĐang phân tích giao dịch trong {args.period} ngày qua...")
        
        result = journal.analyze_trades(args.period)
        journal.print_analysis_summary(result)
    
    elif args.command == 'compare':
        print(f"\nĐang so sánh giao dịch của bạn với hệ thống cho {args.symbol}...")
        
        result = journal.compare_with_system(args.symbol, args.timeframe)
        journal.print_comparison_summary(result)
    
    else:
        print("\nLệnh không hợp lệ. Sử dụng --help để xem hướng dẫn.")

if __name__ == "__main__":
    main()