# Hệ thống phân tích đa khung thời gian

## Giới thiệu

Tài liệu này mô tả hệ thống phân tích đa khung thời gian mới được phát triển nhằm giải quyết vấn đề khuyến nghị giao dịch mâu thuẫn giữa các khung thời gian khác nhau.

Hệ thống này giúp nhà giao dịch:
1. Phân tích và tích hợp tín hiệu từ nhiều khung thời gian (5m, 15m, 1h, 4h, 1d)
2. Phát hiện và giải quyết các khuyến nghị mâu thuẫn
3. Đưa ra khuyến nghị hợp nhất dựa trên trọng số của từng khung thời gian
4. Tạo báo cáo chi tiết về phân tích đa khung thời gian

## Vấn đề đã giải quyết

Trước đây, hệ thống phân tích từng khung thời gian một cách độc lập, dẫn đến những tình huống như:
- Khung 5m và 15m khuyến nghị SELL
- Khung 1h khuyến nghị BUY
- Khung 4h khuyến nghị NEUTRAL

Điều này gây nhầm lẫn cho người dùng và có thể dẫn đến quyết định giao dịch không tối ưu.

## Giải pháp

1. **Tích hợp đa khung thời gian**:
   - Gán trọng số cho từng khung thời gian (mặc định: 5m: 10%, 15m: 15%, 1h: 40%, 4h: 25%, 1d: 10%)
   - Tính điểm tích hợp dựa trên trung bình có trọng số

2. **Phát hiện xung đột**:
   - Xác định mức độ xung đột đáng kể giữa các khung thời gian
   - Cung cấp thông tin chi tiết về xung đột

3. **Các phương pháp giải quyết xung đột**:
   - Trung bình có trọng số (weighted_average): Tính điểm tích hợp theo trọng số
   - Khung thời gian chính (primary_only): Chỉ sử dụng khung thời gian chính (mặc định: 1h)
   - Biểu quyết đa số (majority_vote): Sử dụng khuyến nghị xuất hiện nhiều nhất

4. **Xác định điểm vào/ra thông minh**:
   - Có thể ưu tiên điểm vào/ra từ khung thời gian chính, hoặc
   - Chọn điểm bảo thủ nhất (ít rủi ro), hoặc
   - Chọn điểm tích cực nhất (nhiều lợi nhuận)

## Cách sử dụng

### Phân tích một cặp tiền

```bash
python integration_test.py --symbol BTCUSDT
```

### Lưu báo cáo phân tích

```bash
python integration_test.py --symbol BTCUSDT --save-report
```

Báo cáo sẽ được lưu tại `reports/integrated_analysis/BTCUSDT_integrated_analysis.json`.

## Cấu hình hệ thống

Bạn có thể tùy chỉnh cấu hình hệ thống tại file `configs/multi_timeframe_config.json`:

```json
{
    "timeframe_weights": {
        "5m": 0.1,
        "15m": 0.15,
        "1h": 0.4,
        "4h": 0.25,
        "1d": 0.1
    },
    "primary_timeframe": "1h",
    "conflict_resolution": "weighted_average",
    "significance_threshold": 20,
    "entry_exit_preferences": {
        "entry_points": "primary_timeframe",
        "take_profit": "most_conservative",
        "stop_loss": "most_conservative"
    },
    "market_regime_influence": {
        "enabled": true,
        "trending_up_boost": 10,
        "trending_down_boost": 10,
        "volatile_discount": 5,
        "ranging_discount": 0
    }
}
```

### Các tùy chọn cấu hình

- **timeframe_weights**: Trọng số cho từng khung thời gian
- **primary_timeframe**: Khung thời gian chính (được ưu tiên khi cần)
- **conflict_resolution**: Phương pháp giải quyết xung đột
  - `weighted_average`: Trung bình có trọng số
  - `primary_only`: Chỉ sử dụng khung thời gian chính
  - `majority_vote`: Biểu quyết đa số
- **significance_threshold**: Ngưỡng chênh lệch điểm đáng kể giữa các khung
- **entry_exit_preferences**: Ưu tiên khi xác định điểm vào/ra
  - `primary_timeframe`: Sử dụng khung thời gian chính
  - `most_conservative`: Chọn điểm bảo thủ nhất
  - `most_aggressive`: Chọn điểm tích cực nhất
- **market_regime_influence**: Ảnh hưởng của chế độ thị trường

## Lợi ích

1. **Giảm thiểu sự mâu thuẫn**: Hệ thống đưa ra một khuyến nghị thống nhất
2. **Phản ánh đa góc nhìn**: Tích hợp thông tin từ nhiều khung thời gian
3. **Rõ ràng hơn cho người dùng**: Dễ dàng hiểu lý do đằng sau mỗi khuyến nghị
4. **Tùy biến linh hoạt**: Người dùng có thể điều chỉnh trọng số và cấu hình theo nhu cầu
5. **Quản lý rủi ro tốt hơn**: Các điểm stop loss và take profit được tối ưu hóa

## Kết luận

Hệ thống phân tích đa khung thời gian mới cung cấp cách tiếp cận toàn diện hơn đối với việc phân tích thị trường, giúp người dùng đưa ra quyết định giao dịch chính xác hơn bằng cách kết hợp thông tin từ nhiều khung thời gian khác nhau.