#!/usr/bin/env python3
"""
Cấu hình rủi ro vừa phải cho bot giao dịch tài khoản nhỏ (100 USD)

File này chứa các cài đặt với mức chấp nhận rủi ro vừa phải (mất 20-30% vốn)
để cân bằng giữa cơ hội giao dịch và bảo toàn vốn.
"""

# === 1. Cấu hình rủi ro cơ bản ===
INITIAL_BALANCE = 100.0               # Số dư ban đầu (USD)
MAX_ACCOUNT_RISK = 25.0               # Rủi ro tối đa cho tài khoản (%, 0-100)
MAX_DRAWDOWN = 30.0                   # Drawdown tối đa chấp nhận được (%, 0-100)
MAX_POSITIONS = 2                     # Số vị thế đồng thời tối đa (giảm so với high risk)

# === 2. Cấu hình đòn bẩy ===
MAX_LEVERAGE = 15                     # Đòn bẩy tối đa (giảm so với high risk)
OPTIMAL_LEVERAGE = 12                 # Đòn bẩy khuyến nghị (cân bằng rủi ro-lợi nhuận)

# === 3. Cấu hình rủi ro mỗi giao dịch ===
RISK_PER_TRADE = 3.0                  # Rủi ro mỗi giao dịch tính theo % tài khoản
                                      # 3% của 100 USD = 3 USD rủi ro mỗi lệnh
                                      
PYRAMIDING_ALLOWED = False            # Không cho phép mở nhiều vị thế cùng chiều

# === 4. Cấu hình chống thanh lý (Liquidation) ===
MIN_DISTANCE_TO_LIQUIDATION = 25.0    # Khoảng cách tối thiểu từ entry đến thanh lý (%)
                                      # Tăng lên 25% (từ 15% của high risk) để an toàn hơn

# === 5. Cấu hình bộ lọc biến động ===
VOLATILITY_THRESHOLD = 1.0            # Ngưỡng biến động tối thiểu để vào lệnh (%)
                                      # Tăng lên 1.0% (từ 0.8% của high risk) để giảm số lệnh

# === 6. Cấu hình chỉ báo RSI ===
RSI_LOWER = 30                        # Ngưỡng quá bán (mặc định: 30)
RSI_UPPER = 70                        # Ngưỡng quá mua (mặc định: 70)
                                      # Thắt chặt lại khoảng để vào ít lệnh hơn nhưng chính xác hơn

# === 7. Cấu hình Risk-Reward ===
MIN_RISK_REWARD = 1.5                 # Tỷ lệ R:R tối thiểu
                                      # Tăng lên 1.5 (từ 1.2) để đảm bảo lợi nhuận kỳ vọng tốt hơn

# === 8. Cấu hình Take Profit và Stop Loss ===
SCALPING_STOP_LOSS = 0.8              # Stop loss cho scalping (% dưới/trên giá entry)
SCALPING_TAKE_PROFIT = 1.6            # Take profit cho scalping (% trên/dưới giá entry)

TREND_STOP_LOSS = 1.2                 # Stop loss cho giao dịch xu hướng (%)
TREND_TAKE_PROFIT = 2.4               # Take profit cho giao dịch xu hướng (%)

# === 9. Cấu hình Trailing Stop ===
USE_TRAILING_STOP = True              # Sử dụng trailing stop
TRAILING_ACTIVATION = 0.8             # Kích hoạt trailing khi lợi nhuận đạt % này
TRAILING_CALLBACK = 0.3               # % lùi lại từ giá cao/thấp nhất

# === 10. Cấu hình margin ===
MAX_MARGIN_USAGE = 60.0               # Tỷ lệ sử dụng margin tối đa (% số dư)
                                      # Giảm xuống 60% (từ 80% của high risk) để đảm bảo an toàn hơn

def get_summary():
    """Trả về tóm tắt cấu hình rủi ro vừa phải"""
    max_position_size = INITIAL_BALANCE * (MAX_MARGIN_USAGE / 100) * OPTIMAL_LEVERAGE
    max_risk_amount = INITIAL_BALANCE * (RISK_PER_TRADE / 100)
    
    return f"""
    === TÓM TẮT CẤU HÌNH RỦI RO VỪA PHẢI ===
    
    Số dư ban đầu: ${INITIAL_BALANCE:.2f}
    Rủi ro tối đa: {MAX_ACCOUNT_RISK:.1f}% (${INITIAL_BALANCE * MAX_ACCOUNT_RISK / 100:.2f})
    Rủi ro mỗi giao dịch: {RISK_PER_TRADE:.1f}% (${max_risk_amount:.2f})
    
    Đòn bẩy tối đa: x{MAX_LEVERAGE}
    Đòn bẩy khuyến nghị: x{OPTIMAL_LEVERAGE}
    
    Kích thước vị thế tối đa: ${max_position_size:.2f}
    Số vị thế đồng thời: {MAX_POSITIONS}
    
    Khoảng cách an toàn đến thanh lý: {MIN_DISTANCE_TO_LIQUIDATION:.1f}%
    Sử dụng margin tối đa: {MAX_MARGIN_USAGE:.1f}%
    
    Với cấu hình này, bạn có thể mất tối đa ${INITIAL_BALANCE * MAX_ACCOUNT_RISK / 100:.2f},
    nhưng cũng có tiềm năng lợi nhuận khả quan với rủi ro được kiểm soát.
    """

if __name__ == "__main__":
    print(get_summary())