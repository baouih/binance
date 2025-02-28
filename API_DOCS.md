# API Documentation

## RESTful API Endpoints

### Thông tin thị trường

#### GET `/api/market-data`
Lấy dữ liệu thị trường cho một cặp giao dịch cụ thể.

**Tham số:**
- `symbol` (string, không bắt buộc): Cặp giao dịch (mặc định: BTCUSDT)

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "price": 83772.88,
  "change_24h": 1.25,
  "volume_24h": 35461.23,
  "high_24h": 84500.00,
  "low_24h": 82100.00,
  "updated_at": "2025-02-28T16:05:07.472Z"
}
```

#### GET `/api/historical-data`
Lấy dữ liệu lịch sử cho một cặp giao dịch.

**Tham số:**
- `symbol` (string, không bắt buộc): Cặp giao dịch (mặc định: BTCUSDT)
- `interval` (string, không bắt buộc): Khung thời gian (mặc định: 1h)
- `limit` (number, không bắt buộc): Số lượng kết quả (mặc định: 500)

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "data": [
    {
      "time": "2025-02-28T15:00:00Z",
      "open": 83500.00,
      "high": 83800.00,
      "low": 83200.00,
      "close": 83772.88,
      "volume": 1250.45
    },
    // ... additional candles
  ]
}
```

#### GET `/api/indicators`
Lấy chỉ báo kỹ thuật cho một cặp giao dịch.

**Tham số:**
- `symbol` (string, không bắt buộc): Cặp giao dịch (mặc định: BTCUSDT)
- `interval` (string, không bắt buộc): Khung thời gian (mặc định: 1h)

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "indicators": {
    "rsi": 52.45,
    "macd": {
      "macd": 125.45,
      "signal": 110.23,
      "histogram": 15.22
    },
    "ema": {
      "ema9": 83500.00,
      "ema21": 83200.00
    },
    "bollinger_bands": {
      "upper": 84500.00,
      "middle": 83500.00,
      "lower": 82500.00
    },
    "market_regime": "neutral"
  }
}
```

#### GET `/api/sentiment`
Lấy phân tích tâm lý thị trường.

**Tham số:**
- `symbol` (string, không bắt buộc): Cặp giao dịch (mặc định: BTCUSDT)

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "sentiment_score": 62.5,
  "sentiment_category": "bullish",
  "sentiment_trend": "increasing",
  "components": {
    "technical": 65.0,
    "social": 70.0,
    "fear_greed": 55.0
  },
  "updated_at": "2025-02-28T16:05:07.472Z"
}
```

### Quản lý tài khoản

#### GET `/api/account`
Lấy thông tin tài khoản.

**Response:**
```json
{
  "balance": 10000.00,
  "available_balance": 9500.00,
  "margin_used": 500.00,
  "positions_count": 1,
  "unrealized_pnl": 120.50,
  "realized_pnl_24h": 350.75
}
```

#### GET `/api/positions`
Lấy thông tin về các vị thế đang mở.

**Response:**
```json
{
  "positions": [
    {
      "symbol": "BTCUSDT",
      "side": "BUY",
      "entry_price": 83000.00,
      "current_price": 83772.88,
      "quantity": 0.1,
      "leverage": 5,
      "margin": 500.00,
      "pnl": 77.29,
      "pnl_percent": 1.55,
      "liquidation_price": 76500.00,
      "created_at": "2025-02-28T10:30:00Z"
    }
  ]
}
```

#### GET `/api/orders`
Lấy thông tin về các lệnh đang mở.

**Response:**
```json
{
  "orders": [
    {
      "id": "123456789",
      "symbol": "BTCUSDT",
      "side": "SELL",
      "type": "LIMIT",
      "price": 85000.00,
      "quantity": 0.1,
      "filled": 0.0,
      "status": "NEW",
      "created_at": "2025-02-28T14:30:00Z"
    }
  ]
}
```

#### GET `/api/trade-history`
Lấy lịch sử giao dịch.

**Tham số:**
- `limit` (number, không bắt buộc): Số lượng kết quả (mặc định: 50)

**Response:**
```json
{
  "trades": [
    {
      "symbol": "BTCUSDT",
      "side": "BUY",
      "entry_price": 82000.00,
      "exit_price": 83500.00,
      "quantity": 0.1,
      "pnl": 150.00,
      "pnl_percent": 1.83,
      "entry_time": "2025-02-27T10:30:00Z",
      "exit_time": "2025-02-27T18:45:00Z",
      "strategy": "ema_cross",
      "market_regime": "trending_up"
    }
  ]
}
```

### Quản lý giao dịch

#### POST `/api/place-order`
Đặt lệnh giao dịch mới.

**Body:**
```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "quantity": 0.1,
  "leverage": 5
}
```

**Response:**
```json
{
  "order_id": "123456790",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "price": 83772.88,
  "executed_price": 83772.88,
  "quantity": 0.1,
  "status": "FILLED",
  "created_at": "2025-02-28T16:10:15Z"
}
```

#### POST `/api/close-position`
Đóng một vị thế đang mở.

**Body:**
```json
{
  "symbol": "BTCUSDT"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Position closed successfully",
  "details": {
    "symbol": "BTCUSDT",
    "exit_price": 83772.88,
    "pnl": 77.29,
    "pnl_percent": 1.55,
    "closed_at": "2025-02-28T16:11:20Z"
  }
}
```

### Quản lý bot

#### POST `/api/start-bot`
Bắt đầu chạy bot giao dịch tự động.

**Body:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "strategy": "advanced_ml",
  "risk_percentage": 1.0,
  "leverage": 5
}
```

**Response:**
```json
{
  "success": true,
  "bot_id": "ml_bot_123",
  "message": "Bot started successfully",
  "details": {
    "symbol": "BTCUSDT",
    "interval": "1h",
    "strategy": "advanced_ml",
    "risk_percentage": 1.0,
    "leverage": 5,
    "started_at": "2025-02-28T16:15:00Z"
  }
}
```

#### POST `/api/stop-bot`
Dừng bot giao dịch tự động.

**Body:**
```json
{
  "bot_id": "ml_bot_123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Bot stopped successfully",
  "details": {
    "bot_id": "ml_bot_123",
    "running_time": "2h 30m",
    "trades_executed": 3,
    "net_pnl": 120.50,
    "stopped_at": "2025-02-28T18:45:00Z"
  }
}
```

#### GET `/api/bot-status`
Lấy trạng thái hiện tại của bot giao dịch.

**Response:**
```json
{
  "bots": [
    {
      "bot_id": "ml_bot_123",
      "symbol": "BTCUSDT",
      "interval": "1h",
      "strategy": "advanced_ml",
      "status": "running",
      "started_at": "2025-02-28T16:15:00Z",
      "last_trade": "2025-02-28T18:30:00Z",
      "trades_executed": 3,
      "net_pnl": 120.50,
      "current_market_regime": "trending_up"
    }
  ]
}
```

### Backtesting

#### POST `/api/run-backtest`
Chạy backtest với cấu hình được chỉ định.

**Body:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "strategy": "advanced_ml",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-02-28T00:00:00Z",
  "initial_balance": 10000.0,
  "leverage": 5
}
```

**Response:**
```json
{
  "success": true,
  "backtest_id": "backtest_123",
  "results": {
    "total_trades": 42,
    "win_rate": 65.2,
    "profit_factor": 2.3,
    "net_profit": 3250.75,
    "net_profit_percent": 32.5,
    "max_drawdown": 850.25,
    "max_drawdown_percent": 8.5,
    "sharpe_ratio": 1.8,
    "sortino_ratio": 2.5,
    "market_regime_performance": {
      "trending_up": {
        "trades": 18,
        "win_rate": 77.8,
        "net_profit": 2150.50
      },
      "trending_down": {
        "trades": 12,
        "win_rate": 58.3,
        "net_profit": 950.25
      },
      "ranging": {
        "trades": 8,
        "win_rate": 50.0,
        "net_profit": 150.00
      },
      "volatile": {
        "trades": 4,
        "win_rate": 50.0,
        "net_profit": 0.00
      }
    }
  }
}
```

## WebSocket API

Kết nối WebSocket: `ws://localhost:5000/socket.io/`

### Kết nối

```javascript
const socket = io.connect('http://localhost:5000');

socket.on('connect', () => {
  console.log('Connected to server');
});

socket.on('disconnect', () => {
  console.log('Disconnected from server');
});
```

### Các sự kiện

#### `price_update`
Nhận cập nhật giá mới nhất.

```javascript
socket.on('price_update', (data) => {
  console.log('Price update:', data);
  // data: { symbol: 'BTCUSDT', price: 83772.88, timestamp: '2025-02-28T16:05:07.472Z' }
});
```

#### `sentiment_update`
Nhận cập nhật về tâm lý thị trường.

```javascript
socket.on('sentiment_update', (data) => {
  console.log('Sentiment update:', data);
  // data: { symbol: 'BTCUSDT', score: 62.5, category: 'bullish' }
});
```

#### `account_update`
Nhận cập nhật về tài khoản và vị thế.

```javascript
socket.on('account_update', (data) => {
  console.log('Account update:', data);
  // data: { balance: 10000.00, positions: [...], orders: [...] }
});
```

#### `trade_executed`
Nhận thông báo khi có giao dịch mới được thực hiện.

```javascript
socket.on('trade_executed', (data) => {
  console.log('Trade executed:', data);
  // data: { symbol: 'BTCUSDT', side: 'BUY', price: 83772.88, ... }
});
```

#### `bot_status_update`
Nhận cập nhật về trạng thái bot.

```javascript
socket.on('bot_status_update', (data) => {
  console.log('Bot status update:', data);
  // data: { bot_id: 'ml_bot_123', status: 'running', ... }
});
```

#### `market_regime_change`
Nhận thông báo khi chế độ thị trường thay đổi.

```javascript
socket.on('market_regime_change', (data) => {
  console.log('Market regime change:', data);
  // data: { symbol: 'BTCUSDT', old_regime: 'neutral', new_regime: 'trending_up' }
});
```