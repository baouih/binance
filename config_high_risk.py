#!/usr/bin/env python3
"""
Cấu hình rủi ro cao cho bot giao dịch tài khoản nhỏ (100 USD)

File này chứa các cài đặt với mức chấp nhận rủi ro cao (mất 30-50% vốn)
để tối đa hóa cơ hội giao dịch và lợi nhuận tiềm năng.
"""

# === 1. Cấu hình rủi ro cơ bản ===
INITIAL_BALANCE = 100.0               # Số dư ban đầu (USD)
MAX_ACCOUNT_RISK = 50.0               # Rủi ro tối đa cho tài khoản (%, 0-100)
MAX_DRAWDOWN = 50.0                   # Drawdown tối đa chấp nhận được (%, 0-100)
MAX_POSITIONS = 3                     # Số vị thế đồng thời tối đa

# === 2. Cấu hình đòn bẩy ===
MAX_LEVERAGE = 20                     # Đòn bẩy tối đa
OPTIMAL_LEVERAGE = 16                 # Đòn bẩy khuyến nghị (cân bằng rủi ro-lợi nhuận)

# === 3. Cấu hình rủi ro mỗi giao dịch ===
RISK_PER_TRADE = 5.0                  # Rủi ro mỗi giao dịch tính theo % tài khoản
                                      # 5% của 100 USD = 5 USD rủi ro mỗi lệnh
                                      
PYRAMIDING_ALLOWED = True             # Cho phép mở nhiều vị thế cùng chiều
PYRAMIDING_MAX_POSITIONS = 2          # Số vị thế tối đa cùng chiều

# === 4. Cấu hình chống thanh lý (Liquidation) ===
MIN_DISTANCE_TO_LIQUIDATION = 15.0    # Khoảng cách tối thiểu từ entry đến thanh lý (%)
                                      # Giảm xuống 15% (từ mặc định 25%) để tăng kích thước vị thế

# === 5. Cấu hình bộ lọc biến động ===
VOLATILITY_THRESHOLD = 0.8            # Ngưỡng biến động tối thiểu để vào lệnh (%)
                                      # Giảm xuống 0.8% (từ mặc định 1.5%) để vào lệnh nhiều hơn

# === 6. Cấu hình chỉ báo RSI ===
RSI_LOWER = 35                        # Ngưỡng quá bán (mặc định: 30)
RSI_UPPER = 65                        # Ngưỡng quá mua (mặc định: 70)
                                      # Mở rộng khoảng để vào lệnh nhiều hơn

# === 7. Cấu hình Risk-Reward ===
MIN_RISK_REWARD = 1.2                 # Tỷ lệ R:R tối thiểu (mặc định: 1.5)
                                      # Giảm xuống 1.2 để tăng số lượng giao dịch

# === 8. Cấu hình Take Profit và Stop Loss ===
SCALPING_STOP_LOSS = 1.0              # Stop loss cho scalping (% dưới/trên giá entry)
SCALPING_TAKE_PROFIT = 2.0            # Take profit cho scalping (% trên/dưới giá entry)

TREND_STOP_LOSS = 1.5                 # Stop loss cho giao dịch xu hướng (%)
TREND_TAKE_PROFIT = 3.0               # Take profit cho giao dịch xu hướng (%)

# === 9. Cấu hình Trailing Stop ===
USE_TRAILING_STOP = True              # Sử dụng trailing stop
TRAILING_ACTIVATION = 1.0             # Kích hoạt trailing khi lợi nhuận đạt % này
TRAILING_CALLBACK = 0.5               # % lùi lại từ giá cao/thấp nhất

# === 10. Cấu hình margin ===
MAX_MARGIN_USAGE = 80.0               # Tỷ lệ sử dụng margin tối đa (% số dư)
                                      # Tăng lên 80% (từ mặc định 50%) để tăng kích thước vị thế

def get_risk_profile(profile="high"):
    """
    Trả về cấu hình rủi ro dựa trên profile
    
    Args:
        profile (str): Cấu hình rủi ro ("low", "medium", "high")
        
    Returns:
        Dict: Cấu hình rủi ro
    """
    if profile == "low":
        return {
            "risk_per_trade": 1.0,
            "max_account_risk": 10.0,
            "max_leverage": 10,
            "min_distance_to_liquidation": 30.0,
            "volatility_threshold": 1.5,
            "min_risk_reward": 2.0,
            "max_margin_usage": 40.0
        }
    elif profile == "medium":
        return {
            "risk_per_trade": 2.0,
            "max_account_risk": 25.0,
            "max_leverage": 15,
            "min_distance_to_liquidation": 20.0,
            "volatility_threshold": 1.2,
            "min_risk_reward": 1.5,
            "max_margin_usage": 60.0
        }
    else:  # "high"
        return {
            "risk_per_trade": 5.0,
            "max_account_risk": 50.0,
            "max_leverage": 20,
            "min_distance_to_liquidation": 15.0,
            "volatility_threshold": 0.8,
            "min_risk_reward": 1.2,
            "max_margin_usage": 80.0
        }

# Tính toán các giá trị phụ thuộc
def calculate_max_position_size(balance=INITIAL_BALANCE, leverage=OPTIMAL_LEVERAGE, margin_usage=MAX_MARGIN_USAGE):
    """
    Tính kích thước vị thế tối đa
    
    Args:
        balance (float): Số dư tài khoản
        leverage (int): Đòn bẩy
        margin_usage (float): % sử dụng margin
        
    Returns:
        float: Kích thước vị thế tối đa (USD)
    """
    return balance * (margin_usage / 100) * leverage

def calculate_max_risk_amount(balance=INITIAL_BALANCE, risk_per_trade=RISK_PER_TRADE):
    """
    Tính số tiền rủi ro tối đa cho mỗi giao dịch
    
    Args:
        balance (float): Số dư tài khoản
        risk_per_trade (float): % rủi ro mỗi giao dịch
        
    Returns:
        float: Số tiền rủi ro tối đa (USD)
    """
    return balance * (risk_per_trade / 100)

def get_summary():
    """Trả về tóm tắt cấu hình rủi ro"""
    max_position_size = calculate_max_position_size()
    max_risk_amount = calculate_max_risk_amount()
    
    return f"""
    === TÓM TẮT CẤU HÌNH RỦI RO CAO ===
    
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
    nhưng cũng có tiềm năng lợi nhuận cao hơn đáng kể.
    """

if __name__ == "__main__":
    print(get_summary())