# Hướng Dẫn Quản Lý Rủi Ro

## Giới thiệu
Hệ thống quản lý rủi ro là một trong những thành phần quan trọng nhất của bot giao dịch. Nó giúp bảo vệ vốn của bạn và tối ưu hóa lợi nhuận dựa trên mức độ chấp nhận rủi ro của bạn.

## Các Mức Độ Rủi Ro

Hệ thống hỗ trợ 4 mức độ rủi ro chính:

### 1. Bảo Thủ (10%)
- **Mô tả**: Chiến lược rủi ro thấp nhất, ưu tiên bảo toàn vốn
- **Đặc điểm**:
  - Vị thế tối đa: 2
  - Kích thước vị thế: 1% số dư tài khoản
  - Stop Loss: 1%
  - Take Profit: 2%
  - Leverage: 1x
  - Độ biến động tối đa cho phép: Thấp
- **Phù hợp với**: Người mới bắt đầu, nhà đầu tư thận trọng

### 2. Vừa Phải (15%)
- **Mô tả**: Chiến lược cân bằng giữa rủi ro và lợi nhuận
- **Đặc điểm**:
  - Vị thế tối đa: 3
  - Kích thước vị thế: 2% số dư tài khoản
  - Stop Loss: 1.5%
  - Take Profit: 3%
  - Leverage: 2x
  - Độ biến động tối đa cho phép: Trung bình
- **Phù hợp với**: Trader có kinh nghiệm cơ bản

### 3. Tích Cực (20%)
- **Mô tả**: Chiến lược ưu tiên tăng trưởng nhanh với rủi ro cao hơn
- **Đặc điểm**:
  - Vị thế tối đa: 4
  - Kích thước vị thế: 3% số dư tài khoản
  - Stop Loss: 2%
  - Take Profit: 4%
  - Leverage: 3x
  - Độ biến động tối đa cho phép: Cao
- **Phù hợp với**: Trader có kinh nghiệm

### 4. Mạo Hiểm (30%)
- **Mô tả**: Chiến lược rủi ro cao nhất, ưu tiên tuyệt đối cho tăng trưởng nhanh
- **Đặc điểm**:
  - Vị thế tối đa: 5
  - Kích thước vị thế: 5% số dư tài khoản
  - Stop Loss: 3%
  - Take Profit: 6%
  - Leverage: 5x
  - Độ biến động tối đa cho phép: Rất cao
- **Phù hợp với**: Trader chuyên nghiệp

## Cách Thay Đổi Mức Độ Rủi Ro

### Thông qua Giao Diện Web
1. Truy cập trang quản lý: http://localhost:5000
2. Chọn tab "Cài Đặt"
3. Trong phần "Quản Lý Rủi Ro", chọn mức độ rủi ro mong muốn
4. Nhấn "Áp Dụng"

### Thông qua Giao Diện Desktop
1. Mở ứng dụng desktop
2. Chọn tab "Cài Đặt"
3. Trong phần "Quản Lý Rủi Ro", chọn mức độ rủi ro mong muốn
4. Nhấn "Áp Dụng"

### Thông qua Dòng Lệnh
```bash
python risk_level_manager.py --set-risk-level 20
```

## Tùy Chỉnh Mức Độ Rủi Ro

Bạn có thể tùy chỉnh các tham số rủi ro:

### Thông qua File Cấu Hình
1. Mở file cấu hình: `risk_configs/risk_level_XX.json`
2. Chỉnh sửa các tham số theo ý muốn
3. Lưu file và khởi động lại hệ thống

### Thông qua API
```python
from risk_level_manager import RiskLevelManager

# Khởi tạo quản lý rủi ro
risk_manager = RiskLevelManager()

# Tạo cấu hình rủi ro tùy chỉnh
custom_config = {
    "position_size_percent": 2.5,
    "stop_loss_percent": 2.0,
    "take_profit_percent": 4.0,
    "leverage": 2,
    "max_open_positions": 3,
    "max_daily_trades": 10,
    "risk_multipliers": {
        "stop_loss_multiplier": 1.5,
        "take_profit_multiplier": 1.5
    }
}

# Tạo mức rủi ro tùy chỉnh
risk_manager.create_custom_risk_level("my_custom", custom_config)

# Áp dụng mức rủi ro tùy chỉnh
risk_manager.apply_risk_config("my_custom")
```

## Kiểm Tra Hiệu Quả Rủi Ro

Để đánh giá hiệu quả của cấu hình rủi ro:

1. Chạy backtest với mức rủi ro hiện tại:
```bash
python backtest.py --risk-level 20 --period 3m
```

2. So sánh kết quả giữa các mức rủi ro:
```bash
python compare_risk_levels.py --levels 10,15,20,30 --period 6m
```

## Lời Khuyên
- Người mới nên bắt đầu với mức rủi ro Bảo Thủ (10%)
- Đánh giá lại chiến lược rủi ro định kỳ, 2-4 tuần một lần
- Thay đổi mức rủi ro dần dần, không nên nhảy từ 10% lên 30%
- Luôn chạy backtest trước khi áp dụng mức rủi ro mới