#!/bin/bash
# auto_start_services.sh
#
# Script tự động khởi động các dịch vụ của hệ thống BinanceTrader
# - Khởi động dịch vụ hợp nhất
# - Khởi động các dịch vụ con (Auto SLTP, Trailing Stop, Market Monitor)
# - Kích hoạt bot trading

# Thiết lập màu sắc
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'

# Đường dẫn trạng thái
PID_DIR="."
RESULT_FILE="service_startup_result.log"
START_TIME=$(date +%s)

# Hàm in thông báo
print_message() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
  echo -e "${BLUE}[STEP]${NC} $1"
}

# Hàm kiểm tra dịch vụ đang chạy
check_service_running() {
  local service_name="$1"
  local pid_file="${PID_DIR}/${service_name}.pid"
  
  if [ -f "$pid_file" ]; then
    local pid=$(cat "$pid_file")
    if ps -p "$pid" > /dev/null; then
      print_message "Dịch vụ $service_name đang chạy với PID $pid"
      return 0
    else
      print_warning "PID file tồn tại nhưng process $pid không hoạt động"
      return 1
    fi
  else
    print_warning "Không tìm thấy PID file cho $service_name"
    return 1
  fi
}

# Hàm gửi request HTTP để khởi động dịch vụ
start_service_with_api() {
  local endpoint="$1"
  local action="${2:-start}"
  
  print_step "Gửi request khởi động đến $endpoint với action=$action"
  
  # Gửi request và lưu kết quả
  local result=$(curl -s -X POST "http://localhost:5000$endpoint" \
    -H "Content-Type: application/json" \
    -d "{\"action\":\"$action\"}")
  
  # Kiểm tra kết quả
  if [[ "$result" == *"success\":true"* ]]; then
    print_message "API request thành công: $result"
    return 0
  else
    print_error "API request thất bại: $result"
    return 1
  fi
}

# Hàm khởi động dịch vụ hợp nhất
start_unified_service() {
  print_step "1. Khởi động dịch vụ hợp nhất"
  
  # Kiểm tra service đã chạy chưa
  if check_service_running "unified_trading_service"; then
    print_message "Dịch vụ hợp nhất đã đang chạy!"
    return 0
  fi
  
  # Khởi động thông qua API
  if start_service_with_api "/api/services/unified/start"; then
    print_message "Đã khởi động dịch vụ hợp nhất thành công"
    sleep 2 # Đợi dịch vụ khởi động hoàn tất
    return 0
  else
    print_error "Không thể khởi động dịch vụ hợp nhất qua API, thử khởi động trực tiếp..."
    
    # Khởi động trực tiếp script
    if [ -f "./start_unified_service.sh" ]; then
      chmod +x ./start_unified_service.sh
      ./start_unified_service.sh
      sleep 2
      
      if check_service_running "unified_trading_service"; then
        print_message "Đã khởi động dịch vụ hợp nhất trực tiếp thành công"
        return 0
      else
        print_error "Không thể khởi động dịch vụ hợp nhất trực tiếp"
        return 1
      fi
    else
      print_error "Không tìm thấy script khởi động dịch vụ hợp nhất"
      return 1
    fi
  fi
}

# Hàm khởi động bot trading
start_trading_bot() {
  print_step "2. Khởi động bot trading"
  
  # Khởi động thông qua API
  if start_service_with_api "/api/bot/control/all" "start"; then
    print_message "Đã khởi động bot trading thành công"
    return 0
  else
    print_error "Không thể khởi động bot trading"
    return 1
  fi
}

# Hàm chính để khởi động tất cả các dịch vụ
start_all_services() {
  print_message "===== BẮT ĐẦU KHỞI ĐỘNG CÁC DỊCH VỤ ====="
  echo "Thời gian bắt đầu: $(date '+%Y-%m-%d %H:%M:%S')"
  
  # Reset file kết quả
  echo "Kết quả khởi động dịch vụ: $(date '+%Y-%m-%d %H:%M:%S')" > "$RESULT_FILE"
  
  # 1. Khởi động dịch vụ hợp nhất
  if start_unified_service; then
    echo "Dịch vụ hợp nhất: THÀNH CÔNG" >> "$RESULT_FILE"
  else
    echo "Dịch vụ hợp nhất: THẤT BẠI" >> "$RESULT_FILE"
  fi
  
  # 2. Khởi động bot trading
  if start_trading_bot; then
    echo "Bot trading: THÀNH CÔNG" >> "$RESULT_FILE"
  else
    echo "Bot trading: THẤT BẠI" >> "$RESULT_FILE"
  fi
  
  # Tính thời gian khởi động
  END_TIME=$(date +%s)
  DURATION=$((END_TIME - START_TIME))
  
  print_message "===== HOÀN TẤT KHỞI ĐỘNG DỊCH VỤ ====="
  echo "Tổng thời gian khởi động: ${DURATION}s"
  echo "Tổng thời gian khởi động: ${DURATION}s" >> "$RESULT_FILE"
  echo "Xem kết quả chi tiết tại: $RESULT_FILE"
}

# Hàm xác minh trạng thái hệ thống
verify_system_status() {
  print_step "Xác minh trạng thái hệ thống sau khi khởi động"
  
  # Kiểm tra dịch vụ hợp nhất
  if check_service_running "unified_trading_service"; then
    print_message "✓ Dịch vụ hợp nhất hoạt động bình thường"
  else
    print_error "✗ Dịch vụ hợp nhất không hoạt động"
  fi
  
  # Kiểm tra các dịch vụ con
  for service in "auto_sltp_manager" "position_trailing_stop" "auto_market_notifier"; do
    if check_service_running "$service"; then
      print_message "✓ Dịch vụ $service hoạt động bình thường"
    else
      print_warning "✗ Dịch vụ $service không hoạt động"
    fi
  done
  
  print_message "Xác minh hoàn tất!"
}

# Hàm hiển thị trợ giúp
show_help() {
  echo "Sử dụng: $0 [options]"
  echo "Options:"
  echo "  --help             Hiển thị trợ giúp này"
  echo "  --unified-only     Chỉ khởi động dịch vụ hợp nhất"
  echo "  --bot-only         Chỉ khởi động bot trading"
  echo "  --verify           Chỉ xác minh trạng thái hệ thống"
  echo "  --all              Khởi động tất cả dịch vụ và xác minh trạng thái (mặc định)"
}

# Xử lý tham số dòng lệnh
case "$1" in
  --help)
    show_help
    ;;
  --unified-only)
    start_unified_service
    ;;
  --bot-only)
    start_trading_bot
    ;;
  --verify)
    verify_system_status
    ;;
  --all|"")
    start_all_services
    verify_system_status
    ;;
  *)
    print_error "Tham số không hợp lệ: $1"
    show_help
    exit 1
    ;;
esac

exit 0