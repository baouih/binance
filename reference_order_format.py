#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module chứa các mẫu định dạng lệnh giao dịch tham chiếu cho Binance Futures API

Tham khảo từ:
https://binance-docs.github.io/apidocs/futures/en/
"""

# 1. Các loại lệnh phổ biến
MARKET_ORDER = {
    "symbol": "BTCUSDT",
    "side": "BUY",  # hoặc "SELL"
    "type": "MARKET",
    "quantity": 0.001,
    # Các tham số tùy chọn
    "reduceOnly": "false",  # "true" hoặc "false" (chuỗi, không phải boolean)
    "newClientOrderId": "my_order_id",  # ID tùy chỉnh (tùy chọn)
}

LIMIT_ORDER = {
    "symbol": "BTCUSDT",
    "side": "BUY",  # hoặc "SELL"
    "type": "LIMIT",
    "timeInForce": "GTC",  # GTC, IOC, FOK
    "quantity": 0.001,
    "price": 50000,  # Giá limit
    # Các tham số tùy chọn
    "reduceOnly": "false",  # "true" hoặc "false" (chuỗi, không phải boolean)
    "newClientOrderId": "my_limit_order",  # ID tùy chỉnh (tùy chọn)
}

# 2. Các lệnh có điều kiện
STOP_MARKET_ORDER = {
    "symbol": "BTCUSDT",
    "side": "SELL",  # hoặc "BUY"
    "type": "STOP_MARKET",
    "quantity": 0.001,
    "stopPrice": 48000,  # Giá kích hoạt lệnh
    # Các tham số tùy chọn
    "reduceOnly": "true",  # "true" hoặc "false" (chuỗi, không phải boolean)
    "closePosition": "false",  # Đóng toàn bộ vị thế khi kích hoạt
    "workingType": "MARK_PRICE",  # "MARK_PRICE" hoặc "CONTRACT_PRICE"
}

STOP_LIMIT_ORDER = {
    "symbol": "BTCUSDT",
    "side": "SELL",  # hoặc "BUY"
    "type": "STOP",
    "quantity": 0.001,
    "price": 47500,  # Giá limit khi lệnh được kích hoạt
    "stopPrice": 48000,  # Giá kích hoạt lệnh
    "timeInForce": "GTC",  # GTC, IOC, FOK
    # Các tham số tùy chọn
    "reduceOnly": "true",  # "true" hoặc "false" (chuỗi, không phải boolean)
    "workingType": "MARK_PRICE",  # "MARK_PRICE" hoặc "CONTRACT_PRICE"
}

TAKE_PROFIT_MARKET_ORDER = {
    "symbol": "BTCUSDT",
    "side": "SELL",  # hoặc "BUY"
    "type": "TAKE_PROFIT_MARKET",
    "quantity": 0.001,
    "stopPrice": 55000,  # Giá kích hoạt take profit
    # Các tham số tùy chọn
    "reduceOnly": "true",  # "true" hoặc "false" (chuỗi, không phải boolean)
    "closePosition": "false",  # Đóng toàn bộ vị thế khi kích hoạt
    "workingType": "MARK_PRICE",  # "MARK_PRICE" hoặc "CONTRACT_PRICE"
}

TAKE_PROFIT_LIMIT_ORDER = {
    "symbol": "BTCUSDT",
    "side": "SELL",  # hoặc "BUY"
    "type": "TAKE_PROFIT",
    "quantity": 0.001,
    "price": 55500,  # Giá limit khi lệnh được kích hoạt
    "stopPrice": 55000,  # Giá kích hoạt take profit
    "timeInForce": "GTC",  # GTC, IOC, FOK
    # Các tham số tùy chọn
    "reduceOnly": "true",  # "true" hoặc "false" (chuỗi, không phải boolean)
    "workingType": "MARK_PRICE",  # "MARK_PRICE" hoặc "CONTRACT_PRICE"
}

# 3. Lệnh Trailing Stop
TRAILING_STOP_ORDER = {
    "symbol": "BTCUSDT",
    "side": "SELL",  # hoặc "BUY"
    "type": "TRAILING_STOP_MARKET",
    "quantity": 0.001,
    "callbackRate": 1.0,  # Callback rate tính bằng % (0.1 - 5)
    # Các tham số tùy chọn
    "activationPrice": 52000,  # Giá kích hoạt, nếu không chỉ định sẽ dùng giá thị trường hiện tại
    "reduceOnly": "true",  # "true" hoặc "false" (chuỗi, không phải boolean)
    "workingType": "MARK_PRICE",  # "MARK_PRICE" hoặc "CONTRACT_PRICE"
}