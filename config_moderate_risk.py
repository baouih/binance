#!/usr/bin/env python3
"""
Cấu hình rủi ro vừa phải cho bot giao dịch tài khoản nhỏ (100-500 USD)

File này chứa các cài đặt với mức chấp nhận rủi ro vừa phải (10-15% vốn)
để cân bằng giữa bảo toàn vốn và tận dụng cơ hội giao dịch.
"""

# === 1. Cấu hình rủi ro cơ bản ===
INITIAL_BALANCE = 100.0               # Số dư ban đầu (USD)
MAX_ACCOUNT_RISK = 15.0               # Rủi ro tối đa cho tài khoản (%, 0-15)
MAX_DRAWDOWN = 15.0                   # Drawdown tối đa chấp nhận được (%, 0-15)
MAX_POSITIONS = 3                     # Số vị thế đồng thời tối đa

# === 2. Cấu hình đòn bẩy ===
MAX_LEVERAGE = 12                     # Đòn bẩy tối đa 
OPTIMAL_LEVERAGE = 10                 # Đòn bẩy khuyến nghị (cân bằng rủi ro-lợi nhuận)

# === 3. Cấu hình rủi ro mỗi giao dịch ===
RISK_PER_TRADE = 3.0                  # Rủi ro mỗi giao dịch tính theo % tài khoản
                                      # 3% của 100 USD = 3 USD rủi ro mỗi lệnh
                                      
PYRAMIDING_ALLOWED = True             # Cho phép mở nhiều vị thế cùng chiều
PYRAMIDING_MAX_POSITIONS = 2          # Số vị thế tối đa cùng chiều

# === 4. Cấu hình chống thanh lý (Liquidation) ===
MIN_DISTANCE_TO_LIQUIDATION = 20.0    # Khoảng cách tối thiểu từ entry đến thanh lý (%)
                                      # Mức 20% để có khoảng an toàn tốt hơn

# === 5. Cấu hình bộ lọc biến động ===
VOLATILITY_THRESHOLD = 1.0            # Ngưỡng biến động tối thiểu để vào lệnh (%)
                                      # Mức 1.0% để có tín hiệu chất lượng cao hơn

# === 6. Cấu hình chỉ báo RSI ===
RSI_LOWER = 30                        # Ngưỡng quá bán (mặc định: 30)
RSI_UPPER = 70                        # Ngưỡng quá mua (mặc định: 70)
                                      # Giữ khoảng chuẩn để chỉ bắt tín hiệu mạnh

# === 7. Cấu hình Risk-Reward ===
MIN_RISK_REWARD = 1.5                 # Tỷ lệ R:R tối thiểu
                                      # Mức 1.5 đảm bảo chỉ vào lệnh có tiềm năng cao

# === 8. Cấu hình Take Profit và Stop Loss ===
SCALPING_STOP_LOSS = 0.8              # Stop loss cho scalping (% dưới/trên giá entry)
SCALPING_TAKE_PROFIT = 1.6            # Take profit cho scalping (% trên/dưới giá entry)

TREND_STOP_LOSS = 1.2                 # Stop loss cho giao dịch xu hướng (%)
TREND_TAKE_PROFIT = 2.4               # Take profit cho giao dịch xu hướng (%)

# === 9. Cấu hình Trailing Stop ===
USE_TRAILING_STOP = True              # Sử dụng trailing stop
TRAILING_ACTIVATION = 0.8             # Kích hoạt trailing khi lợi nhuận đạt % này
TRAILING_CALLBACK = 0.4               # % lùi lại từ giá cao/thấp nhất

# === 10. Cấu hình margin ===
MAX_MARGIN_USAGE = 60.0               # Tỷ lệ sử dụng margin tối đa (% số dư)
                                      # Mức 60% để đảm bảo có buffer khi thị trường biến động

# === 11. Cấu hình riêng cho mức rủi ro 10% ===
LOW_RISK_CONFIG = {
    "risk_per_trade": 2.0,            # Rủi ro mỗi giao dịch 2%
    "max_account_risk": 10.0,         # Rủi ro tài khoản tối đa 10%
    "max_leverage": 8,                # Đòn bẩy an toàn hơn
    "min_distance_to_liquidation": 25.0, # Khoảng cách an toàn cao hơn
    "volatility_threshold": 1.2,      # Chỉ giao dịch khi biến động đủ lớn
    "min_risk_reward": 1.8,           # Risk-reward cao hơn
    "max_margin_usage": 50.0,         # Sử dụng margin thận trọng
    "trailing_activation": 1.0,       # Kích hoạt trailing muộn hơn
    "max_positions": 2                # Giảm số lượng vị thế đồng thời
}

# === 12. Cấu hình riêng cho mức rủi ro 15% ===
MODERATE_RISK_CONFIG = {
    "risk_per_trade": 3.0,            # Rủi ro mỗi giao dịch 3%
    "max_account_risk": 15.0,         # Rủi ro tài khoản tối đa 15%
    "max_leverage": 12,               # Đòn bẩy cao hơn một chút
    "min_distance_to_liquidation": 20.0, # Khoảng cách an toàn vừa phải
    "volatility_threshold": 1.0,      # Yêu cầu biến động vừa phải
    "min_risk_reward": 1.5,           # Risk-reward cân bằng
    "max_margin_usage": 60.0,         # Sử dụng margin vừa phải
    "trailing_activation": 0.8,       # Kích hoạt trailing sớm hơn
    "max_positions": 3                # Cho phép 3 vị thế đồng thời
}

def get_risk_profile(profile="moderate"):
    """
    Trả về cấu hình rủi ro dựa trên profile
    
    Args:
        profile (str): Cấu hình rủi ro ("low", "moderate")
        
    Returns:
        Dict: Cấu hình rủi ro
    """
    if profile == "low":  # 10%
        return LOW_RISK_CONFIG
    else:  # "moderate" - 15%
        return MODERATE_RISK_CONFIG

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

def get_summary(risk_level="moderate"):
    """
    Trả về tóm tắt cấu hình rủi ro
    
    Args:
        risk_level (str): Mức rủi ro ("low", "moderate")
    """
    config = get_risk_profile(risk_level)
    
    balance = INITIAL_BALANCE
    risk_per_trade = config["risk_per_trade"]
    max_account_risk = config["max_account_risk"]
    max_leverage = config["max_leverage"]
    margin_usage = config["max_margin_usage"]
    max_positions = config["max_positions"]
    min_distance = config["min_distance_to_liquidation"]
    
    max_position_size = balance * (margin_usage / 100) * max_leverage
    max_risk_amount = balance * (risk_per_trade / 100)
    
    return f"""
    === TÓM TẮT CẤU HÌNH RỦI RO {risk_level.upper()} ({max_account_risk}%) ===
    
    Số dư ban đầu: ${balance:.2f}
    Rủi ro tối đa: {max_account_risk:.1f}% (${balance * max_account_risk / 100:.2f})
    Rủi ro mỗi giao dịch: {risk_per_trade:.1f}% (${max_risk_amount:.2f})
    
    Đòn bẩy tối đa: x{max_leverage}
    Đòn bẩy khuyến nghị: x{int(max_leverage * 0.8)}
    
    Kích thước vị thế tối đa: ${max_position_size:.2f}
    Số vị thế đồng thời: {max_positions}
    
    Khoảng cách an toàn đến thanh lý: {min_distance:.1f}%
    Sử dụng margin tối đa: {margin_usage:.1f}%
    
    Với cấu hình này, bạn có thể mất tối đa ${balance * max_account_risk / 100:.2f},
    nhưng vẫn có cơ hội tăng trưởng vốn đáng kể.
    """

if __name__ == "__main__":
    print(get_summary("low"))      # 10%
    print(get_summary("moderate")) # 15%