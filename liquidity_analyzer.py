"""
Module phân tích thanh khoản (Liquidity Analysis)

Module này cung cấp các công cụ để phân tích thanh khoản trên thị trường,
xác định các vùng tập trung lệnh chờ và vùng tập trung thanh khoản cao/thấp.
"""

import numpy as np
import pandas as pd
import logging
import time
from typing import Dict, List, Tuple, Optional, Union
from app.binance_api import BinanceAPI

# Thiết lập logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('liquidity_analyzer')

class LiquidityAnalyzer:
    """
    Lớp phân tích thanh khoản thị trường để xác định các vùng lệnh chờ tích tụ
    và các vùng có tiềm năng 'liquidity grab'.
    """
    
    def __init__(self, binance_api: BinanceAPI = None, cache_timeout: int = 30):
        """
        Khởi tạo bộ phân tích thanh khoản.
        
        Args:
            binance_api (BinanceAPI): Đối tượng API Binance để lấy dữ liệu
            cache_timeout (int): Thời gian hết hạn của bộ nhớ cache (giây)
        """
        self.binance_api = binance_api
        self.cache_timeout = cache_timeout
        self.cache = {}
        
        logger.info("Khởi tạo Bộ phân tích thanh khoản")
    
    def get_orderbook(self, symbol: str, limit: int = 500) -> Dict:
        """
        Lấy dữ liệu order book từ Binance.
        
        Args:
            symbol (str): Mã cặp giao dịch
            limit (int): Số lượng lệnh lớn nhất cho mỗi phía (mua/bán)
            
        Returns:
            Dict: Dữ liệu order book
        """
        cache_key = f"{symbol}_orderbook_{limit}"
        
        # Kiểm tra cache
        if cache_key in self.cache:
            # Kiểm tra xem dữ liệu có cần cập nhật không
            cached_time, orderbook = self.cache[cache_key]
            current_time = time.time()
            
            # Nếu dữ liệu được cập nhật trong vòng cache_timeout giây qua
            if current_time - cached_time < self.cache_timeout:
                return orderbook
        
        # Nếu không có trong cache hoặc cần cập nhật, lấy dữ liệu mới
        if self.binance_api:
            orderbook = self.binance_api.get_order_book(symbol, limit)
            
            # Lưu vào cache
            self.cache[cache_key] = (time.time(), orderbook)
            
            return orderbook
        else:
            logger.error("Không thể lấy dữ liệu orderbook vì thiếu binance_api")
            return None
    
    def analyze_orderbook(self, symbol: str, num_levels: int = 50, 
                          price_range_pct: float = 2.0) -> Dict:
        """
        Phân tích orderbook để xác định các vùng tập trung thanh khoản.
        
        Args:
            symbol (str): Mã cặp giao dịch
            num_levels (int): Số lượng level giá để tổng hợp
            price_range_pct (float): Phạm vi giá xung quanh giá hiện tại để phân tích (%)
            
        Returns:
            Dict: Kết quả phân tích orderbook
        """
        # Lấy orderbook
        orderbook = self.get_orderbook(symbol, limit=500)
        if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
            logger.error(f"Không thể lấy orderbook cho {symbol}")
            return None
        
        # Chuyển đổi thành DataFrame
        bids_df = pd.DataFrame(orderbook['bids'], columns=['price', 'quantity'])
        asks_df = pd.DataFrame(orderbook['asks'], columns=['price', 'quantity'])
        
        # Chuyển đổi kiểu dữ liệu
        bids_df['price'] = bids_df['price'].astype(float)
        bids_df['quantity'] = bids_df['quantity'].astype(float)
        asks_df['price'] = asks_df['price'].astype(float)
        asks_df['quantity'] = asks_df['quantity'].astype(float)
        
        # Tính toán giá trị USD tại mỗi mức giá
        bids_df['value'] = bids_df['price'] * bids_df['quantity']
        asks_df['value'] = asks_df['price'] * asks_df['quantity']
        
        # Lấy giá hiện tại (giá trung bình giữa bid cao nhất và ask thấp nhất)
        current_price = (bids_df['price'].iloc[0] + asks_df['price'].iloc[0]) / 2
        
        # Tính giới hạn phạm vi giá để phân tích
        lower_bound = current_price * (1 - price_range_pct / 100)
        upper_bound = current_price * (1 + price_range_pct / 100)
        
        # Lọc dữ liệu trong phạm vi giá
        bids_df = bids_df[(bids_df['price'] >= lower_bound) & (bids_df['price'] <= current_price)]
        asks_df = asks_df[(asks_df['price'] <= upper_bound) & (asks_df['price'] >= current_price)]
        
        # Phân vùng giá thành các level
        price_step = (upper_bound - lower_bound) / num_levels
        
        # Tạo các bin (khoảng giá)
        bins = [lower_bound + i * price_step for i in range(num_levels + 1)]
        
        # Phân loại bid và ask vào các bin
        bids_df['price_level'] = pd.cut(bids_df['price'], bins=bins, labels=False)
        asks_df['price_level'] = pd.cut(asks_df['price'], bins=bins, labels=False)
        
        # Tính tổng khối lượng và giá trị trong mỗi bin
        bid_levels = bids_df.groupby('price_level').agg({
            'quantity': 'sum',
            'value': 'sum',
            'price': 'mean'
        }).reset_index()
        
        ask_levels = asks_df.groupby('price_level').agg({
            'quantity': 'sum',
            'value': 'sum',
            'price': 'mean'
        }).reset_index()
        
        # Tính các vùng thanh khoản cao
        # Xác định ngưỡng để coi là vùng thanh khoản cao
        if not bid_levels.empty:
            bid_value_threshold = bid_levels['value'].mean() + bid_levels['value'].std()
            high_liquidity_bids = bid_levels[bid_levels['value'] >= bid_value_threshold]
        else:
            high_liquidity_bids = pd.DataFrame()
        
        if not ask_levels.empty:
            ask_value_threshold = ask_levels['value'].mean() + ask_levels['value'].std()
            high_liquidity_asks = ask_levels[ask_levels['value'] >= ask_value_threshold]
        else:
            high_liquidity_asks = pd.DataFrame()
        
        # Xác định các vùng thanh khoản cao
        high_liquidity_zones = []
        
        for _, row in high_liquidity_bids.iterrows():
            zone = {
                'price': row['price'],
                'value': row['value'],
                'quantity': row['quantity'],
                'type': 'bid',
                'strength': self._calculate_liquidity_strength(row['value'], bid_levels['value']),
                'price_range': [row['price'] - price_step/2, row['price'] + price_step/2]
            }
            high_liquidity_zones.append(zone)
        
        for _, row in high_liquidity_asks.iterrows():
            zone = {
                'price': row['price'],
                'value': row['value'],
                'quantity': row['quantity'],
                'type': 'ask',
                'strength': self._calculate_liquidity_strength(row['value'], ask_levels['value']),
                'price_range': [row['price'] - price_step/2, row['price'] + price_step/2]
            }
            high_liquidity_zones.append(zone)
        
        # Sắp xếp các vùng theo độ mạnh
        high_liquidity_zones = sorted(high_liquidity_zones, key=lambda x: x['strength'], reverse=True)
        
        # Tính toán chênh lệch giữa bid và ask (spread)
        if not bids_df.empty and not asks_df.empty:
            best_bid = bids_df['price'].iloc[0]
            best_ask = asks_df['price'].iloc[0]
            spread = best_ask - best_bid
            spread_pct = (spread / current_price) * 100
        else:
            best_bid = best_ask = spread = spread_pct = None
        
        # Tính tỷ lệ bid/ask để xác định áp lực mua/bán
        total_bid_value = bids_df['value'].sum() if not bids_df.empty else 0
        total_ask_value = asks_df['value'].sum() if not asks_df.empty else 0
        
        # Tránh chia cho 0
        bid_ask_ratio = total_bid_value / total_ask_value if total_ask_value > 0 else float('inf')
        
        # Xác định hướng áp lực thị trường
        if bid_ask_ratio > 1.2:
            market_pressure = "buy"  # Áp lực mua
        elif bid_ask_ratio < 0.8:
            market_pressure = "sell"  # Áp lực bán
        else:
            market_pressure = "neutral"  # Cân bằng
        
        # Tìm các vùng "liquidity grab" tiềm năng
        # Đây là các vùng có thanh khoản cao, nơi giá có thể đảo chiều sau khi chạm vào
        liquidity_grab_zones = self._identify_liquidity_grab_zones(
            high_liquidity_zones, current_price
        )
        
        # Tạo kết quả
        result = {
            'current_price': current_price,
            'best_bid': best_bid,
            'best_ask': best_ask,
            'spread': spread,
            'spread_pct': spread_pct,
            'bid_ask_ratio': bid_ask_ratio,
            'market_pressure': market_pressure,
            'high_liquidity_zones': high_liquidity_zones,
            'liquidity_grab_zones': liquidity_grab_zones,
            'total_bid_value': total_bid_value,
            'total_ask_value': total_ask_value
        }
        
        # Ghi log thông tin chính
        logger.info(f"Phân tích thanh khoản {symbol}: Giá = {current_price:.2f}, "
                  f"Áp lực thị trường = {market_pressure.upper()}, "
                  f"Tỷ lệ bid/ask = {bid_ask_ratio:.2f}")
        
        logger.info(f"Số vùng thanh khoản cao: {len(high_liquidity_zones)}, "
                  f"Số vùng liquidity grab: {len(liquidity_grab_zones)}")
        
        return result
    
    def _calculate_liquidity_strength(self, value: float, all_values: pd.Series) -> float:
        """
        Tính toán độ mạnh của một vùng thanh khoản dựa trên giá trị tương đối.
        
        Args:
            value (float): Giá trị của vùng thanh khoản
            all_values (pd.Series): Tất cả các giá trị để so sánh
            
        Returns:
            float: Độ mạnh của vùng thanh khoản (0-100)
        """
        max_value = all_values.max()
        
        if max_value == 0:
            return 0
        
        # Chuẩn hóa về khoảng 0-100
        return min(100, (value / max_value) * 100)
    
    def _identify_liquidity_grab_zones(self, high_liquidity_zones: List[Dict], 
                                      current_price: float) -> List[Dict]:
        """
        Xác định các vùng "liquidity grab" tiềm năng.
        
        Args:
            high_liquidity_zones (List[Dict]): Các vùng thanh khoản cao
            current_price (float): Giá hiện tại
            
        Returns:
            List[Dict]: Các vùng "liquidity grab" tiềm năng
        """
        liquidity_grab_zones = []
        
        for zone in high_liquidity_zones:
            # Vùng bid có thanh khoản cao dưới giá hiện tại là vùng hỗ trợ tiềm năng
            if zone['type'] == 'bid' and zone['price'] < current_price:
                # Càng xa giá hiện tại càng yếu
                distance_factor = 1 - min(1, (current_price - zone['price']) / current_price * 10)
                grab_strength = zone['strength'] * distance_factor
                
                if grab_strength > 50:  # Chỉ lấy các vùng có độ mạnh trên 50
                    grab_zone = zone.copy()
                    grab_zone['grab_type'] = 'support'
                    grab_zone['grab_strength'] = grab_strength
                    grab_zone['distance_pct'] = ((current_price - zone['price']) / current_price) * 100
                    liquidity_grab_zones.append(grab_zone)
            
            # Vùng ask có thanh khoản cao trên giá hiện tại là vùng kháng cự tiềm năng
            elif zone['type'] == 'ask' and zone['price'] > current_price:
                # Càng xa giá hiện tại càng yếu
                distance_factor = 1 - min(1, (zone['price'] - current_price) / current_price * 10)
                grab_strength = zone['strength'] * distance_factor
                
                if grab_strength > 50:  # Chỉ lấy các vùng có độ mạnh trên 50
                    grab_zone = zone.copy()
                    grab_zone['grab_type'] = 'resistance'
                    grab_zone['grab_strength'] = grab_strength
                    grab_zone['distance_pct'] = ((zone['price'] - current_price) / current_price) * 100
                    liquidity_grab_zones.append(grab_zone)
        
        # Sắp xếp theo độ mạnh
        liquidity_grab_zones = sorted(liquidity_grab_zones, key=lambda x: x['grab_strength'], reverse=True)
        
        return liquidity_grab_zones
    
    def get_entry_exit_recommendations(self, symbol: str, trade_type: str = 'both',
                                      max_recommendations: int = 3) -> Dict:
        """
        Đưa ra đề xuất điểm vào lệnh và thoát lệnh dựa trên phân tích thanh khoản.
        
        Args:
            symbol (str): Mã cặp giao dịch
            trade_type (str): Loại giao dịch ('buy', 'sell', 'both')
            max_recommendations (int): Số lượng đề xuất tối đa cho mỗi loại
            
        Returns:
            Dict: Đề xuất điểm vào lệnh và thoát lệnh
        """
        # Phân tích thanh khoản
        liquidity_analysis = self.analyze_orderbook(symbol)
        if not liquidity_analysis:
            logger.error(f"Không thể phân tích thanh khoản cho {symbol}")
            return None
        
        current_price = liquidity_analysis['current_price']
        high_liquidity_zones = liquidity_analysis['high_liquidity_zones']
        liquidity_grab_zones = liquidity_analysis['liquidity_grab_zones']
        
        # Tạo đề xuất
        recommendations = {
            'current_price': current_price,
            'market_pressure': liquidity_analysis['market_pressure'],
            'buy_entries': [],
            'sell_entries': [],
            'take_profit_levels': [],
            'stop_loss_levels': []
        }
        
        # Đề xuất điểm vào lệnh
        if trade_type in ['buy', 'both']:
            # Điểm vào mua: vùng hỗ trợ có thanh khoản cao
            buy_zones = [zone for zone in liquidity_grab_zones 
                        if zone['grab_type'] == 'support' and zone['price'] < current_price]
            
            # Sắp xếp theo độ mạnh và lấy tối đa max_recommendations
            buy_zones = sorted(buy_zones, key=lambda x: x['grab_strength'], reverse=True)[:max_recommendations]
            
            for zone in buy_zones:
                entry = {
                    'price': zone['price'],
                    'strength': zone['grab_strength'],
                    'distance_pct': zone['distance_pct'],
                    'description': f"Vùng hỗ trợ mạnh {zone['price']:.2f} (cách {zone['distance_pct']:.2f}%)"
                }
                recommendations['buy_entries'].append(entry)
        
        if trade_type in ['sell', 'both']:
            # Điểm vào bán: vùng kháng cự có thanh khoản cao
            sell_zones = [zone for zone in liquidity_grab_zones 
                         if zone['grab_type'] == 'resistance' and zone['price'] > current_price]
            
            # Sắp xếp theo độ mạnh và lấy tối đa max_recommendations
            sell_zones = sorted(sell_zones, key=lambda x: x['grab_strength'], reverse=True)[:max_recommendations]
            
            for zone in sell_zones:
                entry = {
                    'price': zone['price'],
                    'strength': zone['grab_strength'],
                    'distance_pct': zone['distance_pct'],
                    'description': f"Vùng kháng cự mạnh {zone['price']:.2f} (cách {zone['distance_pct']:.2f}%)"
                }
                recommendations['sell_entries'].append(entry)
        
        # Đề xuất điểm chốt lời và dừng lỗ dựa trên các vùng thanh khoản cao
        for zone in high_liquidity_zones:
            if zone['type'] == 'ask' and zone['price'] > current_price:
                # Vùng ask trên giá hiện tại: tiềm năng điểm chốt lời cho vị thế mua
                tp = {
                    'price': zone['price'],
                    'strength': zone['strength'],
                    'distance_pct': ((zone['price'] - current_price) / current_price) * 100,
                    'position_type': 'buy',
                    'description': f"TP cho vị thế MUA tại {zone['price']:.2f} (cách {((zone['price'] - current_price) / current_price) * 100:.2f}%)"
                }
                recommendations['take_profit_levels'].append(tp)
            
            elif zone['type'] == 'bid' and zone['price'] < current_price:
                # Vùng bid dưới giá hiện tại: tiềm năng điểm chốt lời cho vị thế bán
                tp = {
                    'price': zone['price'],
                    'strength': zone['strength'],
                    'distance_pct': ((current_price - zone['price']) / current_price) * 100,
                    'position_type': 'sell',
                    'description': f"TP cho vị thế BÁN tại {zone['price']:.2f} (cách {((current_price - zone['price']) / current_price) * 100:.2f}%)"
                }
                recommendations['take_profit_levels'].append(tp)
        
        # Sắp xếp các điểm TP và SL theo độ mạnh
        recommendations['take_profit_levels'] = sorted(
            recommendations['take_profit_levels'], 
            key=lambda x: x['strength'], 
            reverse=True
        )[:max_recommendations]
        
        # Đề xuất các mức dừng lỗ - tìm vùng có thanh khoản thấp
        if trade_type in ['buy', 'both'] and recommendations['buy_entries']:
            # Điểm dừng lỗ cho vị thế mua
            for entry in recommendations['buy_entries']:
                # Đặt SL dưới mức hỗ trợ 0.5-1%
                sl_price = entry['price'] * 0.995  # 0.5% dưới điểm vào
                sl = {
                    'price': sl_price,
                    'position_type': 'buy',
                    'entry_price': entry['price'],
                    'distance_pct': ((entry['price'] - sl_price) / entry['price']) * 100,
                    'description': f"SL cho vị thế MUA tại {sl_price:.2f} (cách điểm vào {((entry['price'] - sl_price) / entry['price']) * 100:.2f}%)"
                }
                recommendations['stop_loss_levels'].append(sl)
        
        if trade_type in ['sell', 'both'] and recommendations['sell_entries']:
            # Điểm dừng lỗ cho vị thế bán
            for entry in recommendations['sell_entries']:
                # Đặt SL trên mức kháng cự 0.5-1%
                sl_price = entry['price'] * 1.005  # 0.5% trên điểm vào
                sl = {
                    'price': sl_price,
                    'position_type': 'sell',
                    'entry_price': entry['price'],
                    'distance_pct': ((sl_price - entry['price']) / entry['price']) * 100,
                    'description': f"SL cho vị thế BÁN tại {sl_price:.2f} (cách điểm vào {((sl_price - entry['price']) / entry['price']) * 100:.2f}%)"
                }
                recommendations['stop_loss_levels'].append(sl)
        
        # Tính risk-reward ratio cho mỗi cặp entry-TP
        if trade_type in ['buy', 'both'] and recommendations['buy_entries'] and recommendations['take_profit_levels']:
            for entry in recommendations['buy_entries']:
                # Tìm một TP phù hợp (TP cho vị thế mua)
                suitable_tps = [tp for tp in recommendations['take_profit_levels'] 
                              if tp['position_type'] == 'buy' and tp['price'] > entry['price']]
                
                if suitable_tps:
                    tp = suitable_tps[0]  # Lấy TP mạnh nhất
                    
                    # Tìm SL tương ứng
                    suitable_sls = [sl for sl in recommendations['stop_loss_levels'] 
                                   if sl['position_type'] == 'buy' and sl['entry_price'] == entry['price']]
                    
                    if suitable_sls:
                        sl = suitable_sls[0]
                        
                        # Tính RR ratio
                        reward = tp['price'] - entry['price']
                        risk = entry['price'] - sl['price']
                        
                        if risk > 0:
                            rr_ratio = reward / risk
                            entry['rr_ratio'] = rr_ratio
                            entry['tp_price'] = tp['price']
                            entry['sl_price'] = sl['price']
                            entry['trade_quality'] = self._calculate_trade_quality(rr_ratio, entry['strength'])
        
        if trade_type in ['sell', 'both'] and recommendations['sell_entries'] and recommendations['take_profit_levels']:
            for entry in recommendations['sell_entries']:
                # Tìm một TP phù hợp (TP cho vị thế bán)
                suitable_tps = [tp for tp in recommendations['take_profit_levels'] 
                              if tp['position_type'] == 'sell' and tp['price'] < entry['price']]
                
                if suitable_tps:
                    tp = suitable_tps[0]  # Lấy TP mạnh nhất
                    
                    # Tìm SL tương ứng
                    suitable_sls = [sl for sl in recommendations['stop_loss_levels'] 
                                   if sl['position_type'] == 'sell' and sl['entry_price'] == entry['price']]
                    
                    if suitable_sls:
                        sl = suitable_sls[0]
                        
                        # Tính RR ratio
                        reward = entry['price'] - tp['price']
                        risk = sl['price'] - entry['price']
                        
                        if risk > 0:
                            rr_ratio = reward / risk
                            entry['rr_ratio'] = rr_ratio
                            entry['tp_price'] = tp['price']
                            entry['sl_price'] = sl['price']
                            entry['trade_quality'] = self._calculate_trade_quality(rr_ratio, entry['strength'])
        
        # Sắp xếp các đề xuất theo chất lượng giao dịch (nếu có)
        if trade_type in ['buy', 'both'] and recommendations['buy_entries']:
            recommendations['buy_entries'] = sorted(
                [entry for entry in recommendations['buy_entries'] if 'trade_quality' in entry],
                key=lambda x: x['trade_quality'],
                reverse=True
            )
        
        if trade_type in ['sell', 'both'] and recommendations['sell_entries']:
            recommendations['sell_entries'] = sorted(
                [entry for entry in recommendations['sell_entries'] if 'trade_quality' in entry],
                key=lambda x: x['trade_quality'],
                reverse=True
            )
        
        # Thêm đề xuất tổng hợp
        if recommendations['market_pressure'] == 'buy':
            recommendations['summary'] = "Áp lực mua mạnh. Xem xét mở vị thế MUA tại các điểm hỗ trợ."
        elif recommendations['market_pressure'] == 'sell':
            recommendations['summary'] = "Áp lực bán mạnh. Xem xét mở vị thế BÁN tại các điểm kháng cự."
        else:
            recommendations['summary'] = "Thị trường cân bằng. Theo dõi và chờ đợi tín hiệu rõ ràng hơn."
        
        # Ghi log đề xuất
        log_msg = f"Phân tích thanh khoản {symbol}: {recommendations['summary']}"
        if recommendations['buy_entries']:
            entry = recommendations['buy_entries'][0]
            log_msg += f" MUA tốt nhất: {entry['price']:.2f}"
            if 'rr_ratio' in entry:
                log_msg += f" (RR: {entry['rr_ratio']:.2f})"
        if recommendations['sell_entries']:
            entry = recommendations['sell_entries'][0]
            log_msg += f" BÁN tốt nhất: {entry['price']:.2f}"
            if 'rr_ratio' in entry:
                log_msg += f" (RR: {entry['rr_ratio']:.2f})"
        
        logger.info(log_msg)
        
        return recommendations
    
    def _calculate_trade_quality(self, rr_ratio: float, liquidity_strength: float) -> float:
        """
        Tính toán chất lượng của một giao dịch tiềm năng.
        
        Args:
            rr_ratio (float): Tỷ lệ risk-reward
            liquidity_strength (float): Độ mạnh của vùng thanh khoản
            
        Returns:
            float: Điểm chất lượng giao dịch (0-100)
        """
        # Trọng số
        rr_weight = 0.7  # 70% dựa trên RR ratio
        strength_weight = 0.3  # 30% dựa trên độ mạnh vùng thanh khoản
        
        # Tính điểm RR (giới hạn tại 3)
        rr_score = min(100, rr_ratio * 33.33)
        
        # Tính điểm tổng hợp
        quality = (rr_score * rr_weight) + (liquidity_strength * strength_weight)
        
        return quality
    
    def detect_liquidity_events(self, symbol: str, event_threshold: float = 1.5) -> Dict:
        """
        Phát hiện các sự kiện thanh khoản đáng chú ý, như tích tụ lệnh đột biến.
        
        Args:
            symbol (str): Mã cặp giao dịch
            event_threshold (float): Ngưỡng để phát hiện sự kiện thanh khoản đột biến
            
        Returns:
            Dict: Các sự kiện thanh khoản đột biến
        """
        # Phân tích orderbook
        orderbook_analysis = self.analyze_orderbook(symbol)
        if not orderbook_analysis:
            return None
        
        high_liquidity_zones = orderbook_analysis['high_liquidity_zones']
        current_price = orderbook_analysis['current_price']
        
        # Tìm các vùng có thanh khoản đột biến
        # Vùng có strength > 80 được coi là đột biến
        liquidity_events = []
        
        for zone in high_liquidity_zones:
            if zone['strength'] > 80:
                distance_pct = abs(zone['price'] - current_price) / current_price * 100
                
                event = {
                    'price': zone['price'],
                    'type': zone['type'],
                    'strength': zone['strength'],
                    'distance_pct': distance_pct,
                    'value': zone['value']
                }
                
                # Phân loại sự kiện
                if zone['type'] == 'bid':
                    if distance_pct < 1.0:
                        event['event_type'] = 'strong_support_close'
                        event['description'] = f"Hỗ trợ mạnh gần giá hiện tại ({zone['price']:.2f})"
                    else:
                        event['event_type'] = 'strong_support_distant'
                        event['description'] = f"Hỗ trợ mạnh cách xa ({zone['price']:.2f}, {distance_pct:.2f}%)"
                else:  # ask
                    if distance_pct < 1.0:
                        event['event_type'] = 'strong_resistance_close'
                        event['description'] = f"Kháng cự mạnh gần giá hiện tại ({zone['price']:.2f})"
                    else:
                        event['event_type'] = 'strong_resistance_distant'
                        event['description'] = f"Kháng cự mạnh cách xa ({zone['price']:.2f}, {distance_pct:.2f}%)"
                
                # Thêm thông tin về khả năng liquidity grab
                if zone['type'] == 'bid' and distance_pct < 3.0:
                    event['potential_action'] = "Giá có thể giảm để lấy thanh khoản, sau đó tăng"
                elif zone['type'] == 'ask' and distance_pct < 3.0:
                    event['potential_action'] = "Giá có thể tăng để lấy thanh khoản, sau đó giảm"
                
                liquidity_events.append(event)
        
        # Tính toán chênh lệch bất thường trong bid/ask
        bid_ask_ratio = orderbook_analysis['bid_ask_ratio']
        
        if bid_ask_ratio > event_threshold:
            # Áp lực mua mạnh bất thường
            event = {
                'event_type': 'buying_pressure',
                'strength': min(100, bid_ask_ratio * 20),  # Chuẩn hóa về thang 0-100
                'description': f"Áp lực mua cực mạnh (tỷ lệ bid/ask: {bid_ask_ratio:.2f})",
                'potential_action': "Giá có thể tăng trong ngắn hạn"
            }
            liquidity_events.append(event)
        
        elif bid_ask_ratio < 1 / event_threshold:
            # Áp lực bán mạnh bất thường
            event = {
                'event_type': 'selling_pressure',
                'strength': min(100, (1 / bid_ask_ratio) * 20),  # Chuẩn hóa về thang 0-100
                'description': f"Áp lực bán cực mạnh (tỷ lệ bid/ask: {bid_ask_ratio:.2f})",
                'potential_action': "Giá có thể giảm trong ngắn hạn"
            }
            liquidity_events.append(event)
        
        # Sắp xếp các sự kiện theo độ mạnh
        liquidity_events = sorted(liquidity_events, key=lambda x: x['strength'], reverse=True)
        
        result = {
            'current_price': current_price,
            'events': liquidity_events,
            'event_count': len(liquidity_events),
            'bid_ask_ratio': bid_ask_ratio
        }
        
        # Thêm cảnh báo nếu có
        if liquidity_events:
            result['warning'] = liquidity_events[0]['description']
            
            # Ghi log cảnh báo
            logger.warning(f"Phát hiện sự kiện thanh khoản: {result['warning']}")
        
        return result