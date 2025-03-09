#!/bin/bash

# Script để cài đặt hệ thống SL/TP Telegram và tất cả các phụ thuộc
# V1.0 - 2025-03-09

LOG_FILE="setup_sltp_system.log"
DATE_FORMAT="+%Y-%m-%d %H:%M:%S"

# Hàm ghi log
log_message() {
    local message="$1"
    local timestamp=$(date "$DATE_FORMAT")
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

echo "===================================================="
echo "  THIẾT LẬP HỆ THỐNG QUẢN LÝ SL/TP TELEGRAM TÍCH HỢP  "
echo "===================================================="
echo ""

log_message "Bắt đầu quá trình thiết lập hệ thống..."

# Kiểm tra Python
log_message "Kiểm tra phiên bản Python..."
python --version
if [ $? -ne 0 ]; then
    log_message "CẢNH BÁO: Không tìm thấy Python, vui lòng cài đặt Python 3.6+ trước khi tiếp tục"
    echo "CẢNH BÁO: Không tìm thấy Python, vui lòng cài đặt Python 3.6+ trước khi tiếp tục"
    exit 1
fi

# Kiểm tra và cài đặt các gói Python cần thiết
log_message "Kiểm tra và cài đặt các gói Python cần thiết..."
echo "Đang cài đặt các gói Python cần thiết..."

python -m pip install --upgrade pip
pip install python-binance requests python-telegram-bot schedule python-dotenv setproctitle

# Kiểm tra thư mục cấu hình
log_message "Kiểm tra thư mục cấu hình..."
if [ ! -d "configs" ]; then
    log_message "Tạo thư mục configs..."
    mkdir -p configs
fi

# Kiểm tra cấu hình Telegram
log_message "Kiểm tra cấu hình Telegram..."
if [ ! -f "configs/telegram_config.json" ]; then
    log_message "Chưa có file cấu hình Telegram, tạo file mẫu..."
    cat > configs/telegram_config.json << 'EOL'
{
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "chat_id": "YOUR_CHAT_ID_HERE",
    "default_message_level": "ALL",
    "send_error_messages": true,
    "send_warning_messages": true,
    "send_info_messages": true,
    "send_debug_messages": false,
    "telegram_enabled": true,
    "custom_templates": {
        "position_update": "🔄 *Cập nhật vị thế {symbol}*\n📊 Giá: {price}\n📈 P/L: {pnl}%\n⚠️ SL: {sl}\n🎯 TP: {tp}"
    }
}
EOL
    echo "Đã tạo file cấu hình Telegram mẫu tại configs/telegram_config.json"
    echo "Vui lòng cập nhật token Bot và Chat ID trước khi sử dụng!"
else
    log_message "Đã tìm thấy file cấu hình Telegram"
fi

# Kiểm tra cấu hình SL/TP
log_message "Kiểm tra cấu hình SL/TP..."
if [ ! -f "configs/sltp_config.json" ]; then
    log_message "Chưa có file cấu hình SL/TP, tạo file mẫu..."
    cat > configs/sltp_config.json << 'EOL'
{
    "default_sl_percentage": 2.0,
    "default_tp_percentage": 3.0,
    "adaptive_mode": true,
    "update_interval": 60,
    "trailing_stop_enabled": true,
    "trailing_stop_activation_percentage": 1.0,
    "trailing_stop_callback_percentage": 0.5,
    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT", "MATICUSDT", "DOGEUSDT", "LTCUSDT", "LINKUSDT", "XRPUSDT", "ETCUSDT", "TRXUSDT"],
    "notifications": {
        "position_opened": true,
        "position_closed": true,
        "sl_tp_updated": true,
        "trailing_stop_activated": true,
        "error_notifications": true
    }
}
EOL
    echo "Đã tạo file cấu hình SL/TP mẫu tại configs/sltp_config.json"
else
    log_message "Đã tìm thấy file cấu hình SL/TP"
fi

# Đảm bảo các scripts có quyền thực thi
log_message "Đảm bảo các scripts có quyền thực thi..."
chmod +x auto_start_sltp_telegram.sh
chmod +x sltp_system_monitor.sh
chmod +x auto_setup_cron_restart.sh
chmod +x sltp_watchdog.sh 2>/dev/null || true

echo ""
echo "===================================================="
echo "  THIẾT LẬP HOÀN TẤT  "
echo "===================================================="
echo ""
echo "Các bước tiếp theo:"
echo "1. Cập nhật Telegram Bot Token và Chat ID trong configs/telegram_config.json"
echo "2. Kiểm tra và điều chỉnh cấu hình SL/TP trong configs/sltp_config.json"
echo "3. Khởi động hệ thống bằng lệnh: ./auto_start_sltp_telegram.sh"
echo "4. Thiết lập khởi động lại tự động bằng lệnh: ./auto_setup_cron_restart.sh"
echo ""
echo "Log file: $LOG_FILE"
echo "===================================================="

log_message "Thiết lập hoàn tất"
exit 0