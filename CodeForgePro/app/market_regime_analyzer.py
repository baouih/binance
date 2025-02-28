"""
Market Regime Analyzer for identifying and tracking different market phases
"""
import logging
from datetime import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class MarketRegimeAnalyzer:
    def __init__(self):
        """Initialize market regime analyzer"""
        self.regimes = {
            'trending_up': {
                'strategies': [],
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'last_updated': None
            },
            'trending_down': {
                'strategies': [],
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'last_updated': None
            },
            'ranging': {
                'strategies': [],
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'last_updated': None
            },
            'volatile': {
                'strategies': [],
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'last_updated': None
            }
        }

        # Thresholds for regime detection (Ngưỡng phát hiện giai đoạn)
        self.TREND_STRENGTH_THRESHOLD = 0.015  # Ngưỡng xác định xu hướng (giảm từ 0.02)
        self.VOLATILITY_THRESHOLD = 0.02  # Ngưỡng biến động (tăng từ 0.015)
        self.RANGE_DEVIATION_THRESHOLD = 0.01  # Ngưỡng dao động sideway
        self.MIN_REGIME_DURATION = 5  # Số nến tối thiểu để xác nhận giai đoạn
        self.VOLUME_IMPACT_THRESHOLD = 1.5  # Ngưỡng tác động khối lượng (mới thêm)

        # Performance tracking
        self.current_regime = None
        self.regime_start_time = None
        self.performance_history = []

    def detect_regime(self, data: pd.DataFrame) -> str:
        """
        Phát hiện giai đoạn thị trường hiện tại dựa trên các chỉ báo kỹ thuật
        """
        try:
            if len(data) < 20:
                logger.warning("Không đủ dữ liệu để phân tích giai đoạn")
                return 'unknown'

            # Calculate key metrics (Tính toán các chỉ số quan trọng)
            returns = data['close'].pct_change()
            sma20 = data['close'].rolling(20).mean()
            volatility = returns.rolling(20).std()

            # Trend metrics (Các chỉ số xu hướng)
            trend_strength = abs(sma20.pct_change(20).iloc[-1])
            price_direction = sma20.pct_change(10).iloc[-1]

            # Volatility metrics (Các chỉ số biến động)
            current_volatility = volatility.iloc[-1]
            avg_volatility = volatility.mean()

            # Volume impact (Tác động khối lượng - mới thêm)
            volume_sma = data['volume'].rolling(20).mean()
            volume_impact = data['volume'].iloc[-1] / volume_sma.iloc[-1]

            # Range metrics (Các chỉ số sideway)
            price_range = (data['high'] - data['low']) / data['close']
            is_ranging = price_range.rolling(20).mean().iloc[-1] < self.RANGE_DEVIATION_THRESHOLD

            logger.info("\n=== Phân tích giai đoạn thị trường ===")
            logger.info(f"Độ mạnh xu hướng: {trend_strength:.4f}")
            logger.info(f"Hướng giá: {price_direction:.4f}")
            logger.info(f"Biến động hiện tại: {current_volatility:.4f}")
            logger.info(f"Biến động trung bình: {avg_volatility:.4f}")
            logger.info(f"Biên độ giá: {price_range.iloc[-1]:.4f}")
            logger.info(f"Tác động khối lượng: {volume_impact:.2f}x")

            # Record all conditions for regime change validation
            conditions = {
                'trending_up': {
                    'trend_strength': trend_strength > self.TREND_STRENGTH_THRESHOLD,
                    'volume_impact': volume_impact > self.VOLUME_IMPACT_THRESHOLD,
                    'price_direction': price_direction > 0,
                    'status': False
                },
                'trending_down': {
                    'trend_strength': trend_strength > self.TREND_STRENGTH_THRESHOLD,
                    'volume_impact': volume_impact > self.VOLUME_IMPACT_THRESHOLD,
                    'price_direction': price_direction < 0,
                    'status': False
                },
                'volatile': {
                    'volatility': current_volatility > (avg_volatility * self.VOLATILITY_THRESHOLD),
                    'volume_impact': volume_impact > self.VOLUME_IMPACT_THRESHOLD,
                    'status': False
                },
                'ranging': {
                    'range_deviation': is_ranging,
                    'trend_strength': trend_strength < self.TREND_STRENGTH_THRESHOLD,
                    'status': False
                }
            }

            # Log detailed condition analysis
            logger.info("\nĐiều kiện giai đoạn thị trường:")
            for regime, condition in conditions.items():
                logger.info(f"\n{regime}:")
                for key, value in condition.items():
                    if key != 'status':
                        logger.info(f"- {key}: {value}")

            # Determine regime (Xác định giai đoạn)
            if trend_strength > self.TREND_STRENGTH_THRESHOLD and volume_impact > self.VOLUME_IMPACT_THRESHOLD:
                if price_direction > 0:
                    regime = 'trending_up'
                    conditions['trending_up']['status'] = True
                    logger.info("✓ Phát hiện giai đoạn TĂNG")
                else:
                    regime = 'trending_down'
                    conditions['trending_down']['status'] = True
                    logger.info("✓ Phát hiện giai đoạn GIẢM")
            elif current_volatility > (avg_volatility * self.VOLATILITY_THRESHOLD):
                regime = 'volatile'
                conditions['volatile']['status'] = True
                logger.info("✓ Phát hiện giai đoạn BIẾN ĐỘNG MẠNH")
            elif is_ranging:
                regime = 'ranging'
                conditions['ranging']['status'] = True
                logger.info("✓ Phát hiện giai đoạn SIDEWAY")
            else:
                regime = 'unknown'
                logger.info("✗ Chưa xác định được giai đoạn rõ ràng")

            # Update regime if changed (Cập nhật nếu giai đoạn thay đổi)
            if regime != self.current_regime:
                self._handle_regime_change(regime)

            return regime

        except Exception as e:
            logger.error(f"Lỗi khi phát hiện giai đoạn thị trường: {e}")
            logger.exception("Chi tiết lỗi:")
            return 'unknown'

    def update_regime_performance(self, trades: List[Dict]) -> None:
        """
        Cập nhật hiệu suất của chiến lược trong giai đoạn hiện tại
        """
        if not self.current_regime or not trades:
            return

        # Calculate performance metrics (Tính toán các chỉ số hiệu suất)
        wins = sum(1 for t in trades if t['pnl'] > 0)
        losses = sum(1 for t in trades if t['pnl'] < 0)

        if wins + losses == 0:
            return

        win_rate = wins / (wins + losses)
        avg_win = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if wins > 0 else 0
        avg_loss = abs(np.mean([t['pnl'] for t in trades if t['pnl'] < 0])) if losses > 0 else 0
        profit_factor = avg_win / avg_loss if avg_loss > 0 else float('inf')

        # Update regime stats (Cập nhật thống kê giai đoạn)
        self.regimes[self.current_regime]['win_rate'] = win_rate
        self.regimes[self.current_regime]['profit_factor'] = profit_factor
        self.regimes[self.current_regime]['last_updated'] = datetime.now()

        # Log performance (Ghi log hiệu suất)
        logger.info(f"\n=== Hiệu suất giai đoạn {self.current_regime} ===")
        logger.info(f"Tỷ lệ thắng: {win_rate:.2%}")
        logger.info(f"Hệ số lợi nhuận: {profit_factor:.2f}")
        logger.info(f"Lợi nhuận TB: {avg_win:.2%}")
        logger.info(f"Thua lỗ TB: {avg_loss:.2%}")

        # Log strategy recommendations
        recommended = self.get_recommended_strategy()
        if recommended:
            logger.info("\nChiến lược được đề xuất:")
            logger.info(f"Tên: {recommended['name']}")
            logger.info(f"Tỷ lệ thắng: {recommended['win_rate']:.2%}")
            logger.info(f"Các tham số:")
            for param, value in recommended['parameters'].items():
                logger.info(f"- {param}: {value}")

    def get_recommended_strategy(self) -> Optional[Dict]:
        """
        Đề xuất chiến lược phù hợp với giai đoạn hiện tại
        """
        if not self.current_regime:
            return None

        strategies = self.regimes[self.current_regime]['strategies']
        if not strategies:
            return None

        # Sort by win rate and profit factor (Sắp xếp theo tỷ lệ thắng và hệ số lợi nhuận)
        sorted_strategies = sorted(
            strategies,
            key=lambda x: (x['win_rate'], x['profit_factor']),
            reverse=True
        )

        selected = sorted_strategies[0] if sorted_strategies else None
        if selected:
            logger.info(f"\nĐã chọn chiến lược tốt nhất cho giai đoạn {self.current_regime}:")
            logger.info(f"Tên: {selected['name']}")
            logger.info(f"Tỷ lệ thắng: {selected['win_rate']:.2%}")
            logger.info(f"Hệ số lợi nhuận: {selected['profit_factor']:.2f}")

        return selected

    def _handle_regime_change(self, new_regime: str) -> None:
        """
        Xử lý khi thị trường chuyển giai đoạn
        """
        if self.current_regime:
            duration = (datetime.now() - self.regime_start_time).days
            logger.info(f"\nKết thúc giai đoạn {self.current_regime} sau {duration} ngày")

            # Store regime performance (Lưu hiệu suất giai đoạn)
            self.performance_history.append({
                'regime': self.current_regime,
                'start_time': self.regime_start_time,
                'end_time': datetime.now(),
                'duration': duration,
                'win_rate': self.regimes[self.current_regime]['win_rate'],
                'profit_factor': self.regimes[self.current_regime]['profit_factor']
            })

            # Log historical performance
            logger.info("\nLịch sử hiệu suất các giai đoạn:")
            for perf in self.performance_history[-5:]:  # Show last 5 regimes
                logger.info(f"\nGiai đoạn: {perf['regime']}")
                logger.info(f"Thời gian: {perf['duration']} ngày")
                logger.info(f"Tỷ lệ thắng: {perf['win_rate']:.2%}")
                logger.info(f"Hệ số lợi nhuận: {perf['profit_factor']:.2f}")

        self.current_regime = new_regime
        self.regime_start_time = datetime.now()
        logger.info(f"\nBắt đầu giai đoạn mới: {new_regime}")
        logger.info("Đang tìm chiến lược phù hợp...")

    def save_successful_strategy(self, strategy: Dict) -> None:
        """
        Lưu chiến lược thành công cho giai đoạn hiện tại
        """
        if not self.current_regime:
            return

        strategy['timestamp'] = datetime.now()
        self.regimes[self.current_regime]['strategies'].append(strategy)
        logger.info(f"\nĐã lưu chiến lược thành công cho giai đoạn {self.current_regime}:")
        logger.info(f"Tên: {strategy['name']}")
        logger.info(f"Tỷ lệ thắng: {strategy['win_rate']:.2%}")
        logger.info(f"Hệ số lợi nhuận: {strategy['profit_factor']:.2f}")
        logger.info("Các tham số:")
        for param, value in strategy['parameters'].items():
            logger.info(f"- {param}: {value}")