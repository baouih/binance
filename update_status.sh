#!/bin/bash
# Script cập nhật trạng thái bot trong file bot_status.json

# Đường dẫn đến file bot_status.json
BOT_STATUS_FILE="bot_status.json"

# Cập nhật thời gian last_update trong bot_status.json
if [ -f "$BOT_STATUS_FILE" ]; then
    # Lấy thời gian hiện tại
    CURRENT_TIME=$(date +"%Y-%m-%d %H:%M:%S")
    
    # Cập nhật last_update trong bot_status.json
    # Sử dụng một file tạm thời để tránh mất dữ liệu
    cat "$BOT_STATUS_FILE" | sed "s/\"last_update\": \"[^\"]*\"/\"last_update\": \"$CURRENT_TIME\"/" > tmp_bot_status.json
    mv tmp_bot_status.json "$BOT_STATUS_FILE"
    
    echo "Đã cập nhật last_update thành $CURRENT_TIME trong $BOT_STATUS_FILE"
else
    echo "Không tìm thấy file $BOT_STATUS_FILE"
fi