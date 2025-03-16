# TÀI LIỆU THAM KHẢO TÍNH TOÁN RỦI RO & TỐI ƯU HÓA

## A. CÔNG THỨC TÍNH TOÁN

### 1. Tính toán ATR Multipliers cho Rủi Ro Cao

| Market Regime | SL Multiplier | TP Multiplier | Ý nghĩa |
|---------------|--------------|---------------|---------|
| Strong_Bullish | 1.8 | 4.0 | SL gần hơn (ngưỡng thấp), TP xa hơn (xu hướng tăng mạnh) |
| Bullish | 2.0 | 3.5 | SL trung bình, TP xa (xu hướng tăng) |
| Neutral | 1.8 | 3.0 | SL gần hơn, TP trung bình (thị trường đi ngang) |
| Bearish | 2.0 | 3.5 | SL trung bình, TP xa (xu hướng giảm) |
| Strong_Bearish | 1.8 | 4.0 | SL gần hơn (ngưỡng thấp), TP xa hơn (xu hướng giảm mạnh) |

Công thức:
- SL Ratio = (1 - (Entry Price - SL Price) / Entry Price) × 100%
- TP Ratio = (TP Price - Entry Price) / Entry Price × 100%
- R/R Ratio = TP Ratio / SL Ratio

### 2. Phân bổ vốn động theo hiệu suất

**Công thức cơ bản:**
```
Adjustment Factor = 0.2
New Allocation = Current Allocation × (1 + Adjustment)
```

**Công thức chi tiết:**
```
Relative Performance = Coin Performance / Average Performance
Performance Adjustment = (Relative Performance - 1.0) × Adjustment Factor
New Allocation = Current Allocation × (1 + Performance Adjustment)
```

**Ví dụ:**
- BTC Performance: +30%, ETH Performance: +20%, Avg Performance: +25%
- BTC Relative Performance: 30/25 = 1.2
- ETH Relative Performance: 20/25 = 0.8
- BTC Adjustment: (1.2 - 1.0) × 0.2 = +0.04 (+4%)
- ETH Adjustment: (0.8 - 1.0) × 0.2 = -0.04 (-4%)
- Từ 40/30 → 41.6/28.8 (chuẩn hóa sau)

### 3. Hệ số tăng tốc cho Trailing Stop

**Công thức:**
```
Steps Achieved = ((Current Profit - Activation Threshold) / Step Size) + 1
Acceleration Factor = min(Steps Achieved × Acceleration Rate, Maximum Factor)
Trailing Distance = Step Size × (1 - Acceleration Factor)
```

**Ví dụ:**
- Entry: $80,000, Current: $84,000, Profit: 5%
- Activation: 2.5%, Step: 0.5%, Acceleration: 0.02, Max: 0.2
- Steps Achieved: ((5 - 2.5) / 0.5) + 1 = 6
- Acceleration Factor: min(6 × 0.02, 0.2) = 0.12
- Trailing Distance: 0.5% × (1 - 0.12) = 0.44%
- Trailing Stop Price: $84,000 × (1 - 0.0044) = $83,630 (LONG)

## B. BẢNG THAM CHIẾU ĐIỀU CHỈNH

### 1. Điều chỉnh Trailing Stop theo Chế độ Thị trường

| Market Regime | Activation | Step Size | Acceleration Rate | Max Factor |
|---------------|------------|-----------|-------------------|------------|
| Trending | 2.0% | 0.4% | 0.025 | 0.25 |
| Ranging | 3.0% | 0.6% | 0.015 | 0.15 |
| Volatile | 3.5% | 0.7% | 0.01 | 0.1 |
| Quiet | 2.5% | 0.5% | 0.02 | 0.2 |

### 2. Điều chỉnh Position Size theo Thời gian

| Cửa sổ Thời gian | Boost Factor | Chiến lược Ưu tiên |
|------------------|--------------|-------------------|
| London Open (15:00-17:00) | 1.25x | SHORT |
| NY Open (20:30-22:30) | 1.25x | SHORT |
| Daily Close (06:30-07:30) | 1.0x | LONG |
| Thời gian khác | 0.8x | Tùy chế độ |

### 3. Điều chỉnh Drawdown Limit theo Account Size

| Account Size | Warning | Reduce Size | Stop Trading |
|--------------|---------|-------------|--------------|
| < $10,000 | 20% | 25% | 30% |
| $10,000 - $50,000 | 25% | 30% | 35% |
| $50,000 - $100,000 | 30% | 35% | 40% |
| > $100,000 | 35% | 40% | 45% |

## C. BẢNG SO SÁNH RỦI RO TIMEFRAME

### 1. Khung thời gian 1D

| Risk Level | Win Rate | Avg Profit (%) | Avg Loss (%) | Profit Factor | Kelly % |
|------------|----------|----------------|--------------|---------------|---------|
| 10% | 62.5% | 6.4% | 3.2% | 3.12 | 30.8% |
| 15% | 61.7% | 9.3% | 4.5% | 2.52 | 27.7% |
| 20% | 61.0% | 12.1% | 6.1% | 2.41 | 26.0% |
| 25% | 60.2% | 14.8% | 7.8% | 2.28 | 24.0% |
| 30% | 59.5% | 17.6% | 9.3% | 2.23 | 23.2% |

### 2. Khung thời gian 4H

| Risk Level | Win Rate | Avg Profit (%) | Avg Loss (%) | Profit Factor | Kelly % |
|------------|----------|----------------|--------------|---------------|---------|
| 10% | 60.5% | 4.2% | 2.3% | 2.98 | 28.4% |
| 15% | 59.7% | 6.1% | 3.4% | 2.46 | 25.0% |
| 20% | 59.0% | 8.0% | 4.5% | 2.36 | 23.6% |
| 25% | 58.2% | 9.8% | 5.6% | 2.21 | 21.7% |
| 30% | 57.5% | 11.7% | 6.8% | 2.09 | 19.9% |

### 3. Khung thời gian 1H

| Risk Level | Win Rate | Avg Profit (%) | Avg Loss (%) | Profit Factor | Kelly % |
|------------|----------|----------------|--------------|---------------|---------|
| 10% | 58.5% | 2.8% | 1.7% | 2.67 | 24.8% |
| 15% | 57.7% | 4.2% | 2.6% | 2.29 | 21.0% |
| 20% | 57.0% | 5.5% | 3.4% | 2.11 | 18.9% |
| 25% | 56.2% | 6.7% | 4.3% | 1.95 | 16.8% |
| 30% | 55.5% | 8.0% | 5.2% | 1.85 | 15.1% |

## D. SƠ ĐỒ QUYẾT ĐỊNH

### 1. Chọn Mức Rủi ro

```
IF (Account.Size >= $50,000 AND Trader.Experience == "Advanced") THEN
    Risk.Level = 30%
ELSE IF (Account.Size >= $25,000 AND Trader.Experience == "Intermediate") THEN
    Risk.Level = 25%
ELSE IF (Account.Experience == "Beginner") THEN
    Risk.Level = 15%
ELSE
    Risk.Level = 20%
END
```

### 2. Kích hoạt Trailing Stop

```
IF (Position.ProfitPercent >= TrailingStop.ActivationThreshold) THEN
    IF (Position.HasTrailingStop == FALSE) THEN
        Position.TrailingStopPrice = CalculateTrailingStop()
        Position.HasTrailingStop = TRUE
    ELSE
        IF (Position.Direction == "LONG" AND NewTrailingStop > Position.TrailingStopPrice) THEN
            Position.TrailingStopPrice = NewTrailingStop
        ELSE IF (Position.Direction == "SHORT" AND NewTrailingStop < Position.TrailingStopPrice) THEN
            Position.TrailingStopPrice = NewTrailingStop
        END
    END
END
```

### 3. Đánh giá Đóng Vị thế

```
FOR EACH Position IN ActivePositions
    CurrentPrice = GetCurrentPrice(Position.Symbol)
    
    IF (Position.HasTrailingStop == TRUE) THEN
        IF (Position.Direction == "LONG" AND CurrentPrice <= Position.TrailingStopPrice) THEN
            ClosePosition(Position.ID, "Trailing Stop")
        ELSE IF (Position.Direction == "SHORT" AND CurrentPrice >= Position.TrailingStopPrice) THEN
            ClosePosition(Position.ID, "Trailing Stop")
        END
    ELSE
        IF (Position.Direction == "LONG") THEN
            IF (CurrentPrice <= Position.StopLoss) THEN
                ClosePosition(Position.ID, "Stop Loss")
            ELSE IF (CurrentPrice >= Position.TakeProfit) THEN
                ClosePosition(Position.ID, "Take Profit")
            END
        ELSE
            IF (CurrentPrice >= Position.StopLoss) THEN
                ClosePosition(Position.ID, "Stop Loss")
            ELSE IF (CurrentPrice <= Position.TakeProfit) THEN
                ClosePosition(Position.ID, "Take Profit")
            END
        END
    END
END
```