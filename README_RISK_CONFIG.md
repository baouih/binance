# Cấu Hình Quản Lý Rủi Ro Hệ Thống Giao Dịch

*Báo cáo được tạo tự động vào: 2025-03-17 05:51:43*

## Cấu Hình Quản Lý Rủi Ro

### Các Mức Độ Rủi Ro

| Mức Rủi Ro   | Mô Tả                                    | Rủi Ro/Giao Dịch   | Đòn Bẩy Tối Đa   |   Vị Thế Tối Đa | Stop Loss Cơ Sở   | Take Profit Cơ Sở   |
|:-------------|:-----------------------------------------|:-------------------|:-----------------|----------------:|:------------------|:--------------------|
| very_low     | Rất thấp, ưu tiên an toàn vốn            | 2.25%              | 2x               |               4 | 2.0%              | 6.0%                |
| low          | Thấp, ưu tiên bảo toàn vốn               | 3.0%               | 3x               |               5 | 2.5%              | 7.5%                |
| medium       | Trung bình, cân bằng rủi ro và lợi nhuận | 3.33%              | 3x               |               6 | 3.0%              | 9.0%                |
| high         | Cao, ưu tiên lợi nhuận                   | 3.6%               | 5x               |               7 | 3.5%              | 10.5%               |
| very_high    | Rất cao, tối đa hóa lợi nhuận            | 3.75%              | 10x              |               8 | 4.0%              | 12.0%               |

### Cấu Hình ATR

- Chu kỳ ATR: 14

**ATR Multiplier:**

| Mức Rủi Ro   | Hệ Số   |
|:-------------|:--------|
| very_low     | x1.2    |
| low          | x1.5    |
| medium       | x2.0    |
| high         | x2.5    |
| very_high    | x3.0    |

**Take Profit Multiplier:**

| Mức Rủi Ro   | Hệ Số   |
|:-------------|:--------|
| very_low     | x3.0    |
| low          | x4.0    |
| medium       | x6.0    |
| high         | x7.5    |
| very_high    | x9.0    |

### Điều Chỉnh Theo Biến Động

**Ngưỡng Biến Động:**

- Thấp: < 1.5%
- Trung bình: < 3.0%
- Cao: < 5.0%
- Cực cao: >= 7.0%

**Điều Chỉnh Kích Thước Vị Thế:**

| Mức Biến Động   | Hệ Số   |
|:----------------|:--------|
| very_low        | x1.2    |
| low             | x1.1    |
| medium          | x1.0    |
| high            | x0.7    |
| extreme         | x0.5    |

**Điều Chỉnh Stop Loss:**

| Mức Biến Động   | Hệ Số   |
|:----------------|:--------|
| very_low        | x0.9    |
| low             | x1.0    |
| medium          | x1.1    |
| high            | x1.3    |
| extreme         | x1.5    |

**Điều Chỉnh Đòn Bẩy:**

| Mức Biến Động   | Hệ Số   |
|:----------------|:--------|
| very_low        | x1.2    |
| low             | x1.1    |
| medium          | x1.0    |
| high            | x0.7    |
| extreme         | x0.5    |

## Hướng Dẫn Sử Dụng

### Chọn Mức Rủi Ro

Để thay đổi mức rủi ro, bạn có thể sử dụng lệnh sau:

```python
from adaptive_risk_manager import AdaptiveRiskManager

# Khởi tạo quản lý rủi ro
risk_manager = AdaptiveRiskManager()

# Thiết lập mức rủi ro mới
risk_manager.set_risk_level('medium')  # Có thể chọn: very_low, low, medium, high, very_high
```

### Kiểm Tra Cấu Hình Hiện Tại

```python
# Xem cấu hình rủi ro hiện tại
current_config = risk_manager.get_current_risk_config()
print(f"Mức rủi ro hiện tại: {risk_manager.active_risk_level}")
print(f"Rủi ro mỗi giao dịch: {current_config['risk_per_trade']}%")
print(f"Đòn bẩy tối đa: {current_config['max_leverage']}x")
```

### Chạy Kiểm Tra Rủi Ro

Để kiểm tra hiệu suất với các mức rủi ro khác nhau:

```bash
# Kiểm tra nhanh với 3 coin và 3 mức rủi ro
python quick_comprehensive_test.py

# Kiểm tra đầy đủ với tất cả coin và tất cả mức rủi ro
python comprehensive_risk_test.py
```

