#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module xử lý lỗi giao dịch tập trung.
Phát hiện, phân loại và ghi log các lỗi giao dịch.
Cung cấp gợi ý khắc phục dựa trên loại lỗi.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Thiết lập logging
logger = logging.getLogger("trade_error_handler")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trade_errors.log"),
        logging.StreamHandler()
    ]
)

# Các mã lỗi Binance API phổ biến và giải thích
BINANCE_ERROR_CODES = {
    "-1000": {
        "message": "Lỗi không xác định",
        "description": "Lỗi không xác định từ máy chủ Binance",
        "solution": "Thử lại sau một lúc hoặc kiểm tra trạng thái API Binance"
    },
    "-1001": {
        "message": "Timeout",
        "description": "Kết nối đến máy chủ Binance bị timeout",
        "solution": "Kiểm tra kết nối mạng và thử lại sau"
    },
    "-1002": {
        "message": "Lỗi xác thực",
        "description": "Không thể xác thực với API Binance",
        "solution": "Kiểm tra lại API key và secret"
    },
    "-1003": {
        "message": "Quá nhiều yêu cầu",
        "description": "Đã vượt quá giới hạn số yêu cầu API",
        "solution": "Giảm tần suất gửi yêu cầu hoặc đợi ít phút rồi thử lại"
    },
    "-1004": {
        "message": "Máy chủ đang bảo trì",
        "description": "Máy chủ Binance đang trong chế độ bảo trì",
        "solution": "Đợi đến khi máy chủ hoạt động trở lại"
    },
    "-1006": {
        "message": "Kết nối không ổn định",
        "description": "Kết nối không ổn định với máy chủ Binance",
        "solution": "Kiểm tra kết nối mạng và thử lại"
    },
    "-1010": {
        "message": "Lỗi thông tin lệnh",
        "description": "Thông tin lệnh không hợp lệ (giá, số lượng, vv.)",
        "solution": "Kiểm tra lại thông tin lệnh và đảm bảo tuân thủ quy tắc của sàn"
    },
    "-1013": {
        "message": "Lỗi xử lý lệnh",
        "description": "Lỗi khi xử lý lệnh",
        "solution": "Kiểm tra lại thông số lệnh và thử lại"
    },
    "-1015": {
        "message": "Quá nhiều lệnh được gửi",
        "description": "Đã vượt quá giới hạn số lệnh cho phép",
        "solution": "Giảm tần suất đặt lệnh hoặc đợi ít phút"
    },
    "-1016": {
        "message": "Dịch vụ không khả dụng",
        "description": "Dịch vụ không khả dụng tạm thời",
        "solution": "Đợi ít phút và thử lại"
    },
    "-1020": {
        "message": "Không được phép",
        "description": "API key không có quyền truy cập chức năng này",
        "solution": "Kiểm tra quyền hạn của API key"
    },
    "-1021": {
        "message": "Timestamp ngoài phạm vi",
        "description": "Timestamp trong yêu cầu nằm ngoài phạm vi cho phép",
        "solution": "Đồng bộ lại thời gian hệ thống"
    },
    "-1022": {
        "message": "Chữ ký không hợp lệ",
        "description": "Chữ ký không hợp lệ trong yêu cầu",
        "solution": "Kiểm tra lại quá trình tạo chữ ký"
    },
    "-1100": {
        "message": "Tham số bắt buộc thiếu",
        "description": "Thiếu một hoặc nhiều tham số bắt buộc",
        "solution": "Kiểm tra lại tất cả tham số bắt buộc"
    },
    "-1101": {
        "message": "Tham số không được hỗ trợ",
        "description": "Một tham số không được hỗ trợ",
        "solution": "Loại bỏ tham số không được hỗ trợ"
    },
    "-1102": {
        "message": "Tham số bắt buộc trống",
        "description": "Một tham số bắt buộc bị trống",
        "solution": "Đảm bảo tất cả tham số bắt buộc có giá trị"
    },
    "-1103": {
        "message": "Loại lệnh không rõ",
        "description": "Loại lệnh không được hỗ trợ",
        "solution": "Sử dụng một trong các loại lệnh được hỗ trợ"
    },
    "-1104": {
        "message": "Độ chính xác không hợp lệ",
        "description": "Số thập phân trong tham số không hợp lệ",
        "solution": "Đảm bảo sử dụng đúng số thập phân cho giá và số lượng"
    },
    "-1105": {
        "message": "Tham số nằm ngoài phạm vi",
        "description": "Một tham số nằm ngoài phạm vi cho phép",
        "solution": "Điều chỉnh giá trị tham số nằm trong phạm vi cho phép"
    },
    "-1106": {
        "message": "Tham số không bắt buộc không được hỗ trợ",
        "description": "Một tham số không bắt buộc không được hỗ trợ",
        "solution": "Loại bỏ tham số không được hỗ trợ"
    },
    "-1111": {
        "message": "Lỗi thông số kỹ thuật",
        "description": "Lỗi trong thông số kỹ thuật",
        "solution": "Kiểm tra lại tất cả thông số kỹ thuật"
    },
    "-1112": {
        "message": "Lệnh không tồn tại",
        "description": "Lệnh không tồn tại",
        "solution": "Kiểm tra lại ID lệnh"
    },
    "-1114": {
        "message": "ID lệnh trùng lặp",
        "description": "ID lệnh đã được sử dụng trước đó",
        "solution": "Sử dụng một ID lệnh khác"
    },
    "-1115": {
        "message": "Lỗi hủy lệnh",
        "description": "Lỗi khi hủy lệnh",
        "solution": "Kiểm tra lại trạng thái lệnh và ID lệnh"
    },
    "-1116": {
        "message": "Lệnh không được phép ở trạng thái hiện tại",
        "description": "Lệnh không được phép ở trạng thái hiện tại",
        "solution": "Kiểm tra trạng thái hiện tại của lệnh trước khi thực hiện hành động"
    },
    "-1117": {
        "message": "Lệnh đã bị hủy",
        "description": "Lệnh đã bị hủy trước đó",
        "solution": "Không cần thực hiện thêm hành động"
    },
    "-1118": {
        "message": "Lệnh đã được thực hiện",
        "description": "Lệnh đã được thực hiện hoàn toàn",
        "solution": "Không cần thực hiện thêm hành động"
    },
    "-1119": {
        "message": "Lệnh đã bị từ chối",
        "description": "Lệnh đã bị từ chối bởi hệ thống",
        "solution": "Kiểm tra thông tin lệnh và thử lại với thông số khác"
    },
    "-1120": {
        "message": "Lệnh đang được huỷ",
        "description": "Lệnh đang trong quá trình huỷ",
        "solution": "Đợi cho quá trình huỷ hoàn tất"
    },
    "-1121": {
        "message": "Giá không hợp lệ",
        "description": "Giá đặt lệnh không hợp lệ",
        "solution": "Kiểm tra lại giá đặt lệnh theo quy tắc của sàn"
    },
    "-1125": {
        "message": "Tài sản không khả dụng",
        "description": "Tài sản giao dịch không khả dụng",
        "solution": "Kiểm tra lại cặp giao dịch"
    },
    "-1127": {
        "message": "Thời gian API hết hạn",
        "description": "Thời gian trong yêu cầu đã hết hạn",
        "solution": "Đảm bảo timestamp nằm trong khoảng thời gian hợp lệ"
    },
    "-1130": {
        "message": "Số dư không đủ",
        "description": "Số dư tài khoản không đủ để thực hiện giao dịch",
        "solution": "Kiểm tra lại số dư và điều chỉnh kích thước vị thế"
    },
    "-2010": {
        "message": "Số dư không đủ",
        "description": "Số dư tài khoản không đủ để thực hiện giao dịch",
        "solution": "Nạp thêm tiền hoặc giảm kích thước vị thế"
    },
    "-2011": {
        "message": "Số lượng không đủ",
        "description": "Số lượng không đủ để thực hiện giao dịch",
        "solution": "Tăng số lượng hoặc kiểm tra lại số lượng tối thiểu"
    },
    "-2013": {
        "message": "Lệnh không tồn tại",
        "description": "Lệnh không tồn tại hoặc đã bị hủy",
        "solution": "Kiểm tra lại ID lệnh"
    },
    "-2014": {
        "message": "API key không tồn tại",
        "description": "API key không tồn tại, đã bị thu hồi hoặc vô hiệu hóa",
        "solution": "Kiểm tra lại hoặc tạo API key mới"
    },
    "-2015": {
        "message": "Lỗi xác thực",
        "description": "Lỗi xác thực với API Binance",
        "solution": "Kiểm tra lại API key và secret"
    },
    "-3000": {
        "message": "Lỗi nghiệp vụ",
        "description": "Lỗi nghiệp vụ trong quá trình xử lý",
        "solution": "Kiểm tra lại thông tin giao dịch và thử lại"
    },
    "-3001": {
        "message": "Lỗi mạng",
        "description": "Lỗi mạng trong quá trình xử lý",
        "solution": "Kiểm tra kết nối mạng và thử lại"
    },
    "-3002": {
        "message": "Lỗi hệ thống",
        "description": "Lỗi hệ thống trong quá trình xử lý",
        "solution": "Thử lại sau hoặc liên hệ hỗ trợ"
    },
    "-3003": {
        "message": "Tham số không hợp lệ",
        "description": "Một hoặc nhiều tham số không hợp lệ",
        "solution": "Kiểm tra lại tất cả tham số"
    },
    "-3004": {
        "message": "Lỗi tài khoản",
        "description": "Lỗi liên quan đến tài khoản",
        "solution": "Kiểm tra trạng thái tài khoản"
    },
    "-3005": {
        "message": "Lỗi thời gian",
        "description": "Lỗi liên quan đến thời gian",
        "solution": "Đồng bộ lại thời gian hệ thống"
    },
    "-3006": {
        "message": "Lỗi xác thực",
        "description": "Lỗi xác thực",
        "solution": "Kiểm tra lại thông tin xác thực"
    },
    "-3007": {
        "message": "Lỗi ủy quyền",
        "description": "Lỗi ủy quyền",
        "solution": "Kiểm tra quyền của tài khoản"
    },
    "-3008": {
        "message": "Lỗi không tìm thấy tài nguyên",
        "description": "Không tìm thấy tài nguyên yêu cầu",
        "solution": "Kiểm tra lại tài nguyên yêu cầu"
    },
    "-3010": {
        "message": "Lỗi tài sản",
        "description": "Lỗi liên quan đến tài sản",
        "solution": "Kiểm tra trạng thái tài sản"
    },
    "-3014": {
        "message": "Lỗi API key",
        "description": "Lỗi liên quan đến API key",
        "solution": "Kiểm tra lại API key"
    },
    "-3015": {
        "message": "Lỗi API secret",
        "description": "Lỗi liên quan đến API secret",
        "solution": "Kiểm tra lại API secret"
    },
    "-3016": {
        "message": "Lỗi chữ ký",
        "description": "Lỗi chữ ký",
        "solution": "Kiểm tra lại quá trình tạo chữ ký"
    },
    "-3017": {
        "message": "Lỗi IP",
        "description": "IP không được phép truy cập",
        "solution": "Kiểm tra lại cài đặt IP cho API key"
    },
    "-3020": {
        "message": "Lỗi bảo trì",
        "description": "Hệ thống đang bảo trì",
        "solution": "Đợi đến khi hệ thống hoạt động trở lại"
    },
    "-3021": {
        "message": "Lỗi timeout",
        "description": "Yêu cầu bị timeout",
        "solution": "Thử lại sau"
    },
    "-4000": {
        "message": "Lỗi tài khoản futures",
        "description": "Lỗi liên quan đến tài khoản futures",
        "solution": "Kiểm tra trạng thái tài khoản futures"
    },
    "-4001": {
        "message": "Lỗi margin",
        "description": "Lỗi liên quan đến margin",
        "solution": "Kiểm tra trạng thái margin"
    },
    "-4002": {
        "message": "Lỗi đòn bẩy",
        "description": "Lỗi liên quan đến đòn bẩy",
        "solution": "Kiểm tra cài đặt đòn bẩy"
    },
    "-4003": {
        "message": "Lỗi vị thế",
        "description": "Lỗi liên quan đến vị thế",
        "solution": "Kiểm tra trạng thái vị thế"
    },
    "-4004": {
        "message": "Lỗi lệnh futures",
        "description": "Lỗi liên quan đến lệnh futures",
        "solution": "Kiểm tra thông tin lệnh futures"
    },
    "-4005": {
        "message": "Lỗi giới hạn vị thế",
        "description": "Đã vượt quá giới hạn vị thế",
        "solution": "Giảm kích thước vị thế hoặc đóng bớt vị thế"
    },
    "-4006": {
        "message": "Lỗi giới hạn lệnh",
        "description": "Đã vượt quá giới hạn lệnh",
        "solution": "Giảm số lượng lệnh hoặc đợi ít phút"
    },
    "-4007": {
        "message": "Lỗi giới hạn đòn bẩy",
        "description": "Đã vượt quá giới hạn đòn bẩy",
        "solution": "Giảm đòn bẩy"
    },
    "-4008": {
        "message": "Lỗi giới hạn số dư",
        "description": "Đã vượt quá giới hạn số dư",
        "solution": "Giảm kích thước vị thế"
    },
    "-4010": {
        "message": "Lỗi tài khoản không tồn tại",
        "description": "Tài khoản futures không tồn tại",
        "solution": "Tạo tài khoản futures"
    },
    "-4011": {
        "message": "Lỗi tài khoản không được kích hoạt",
        "description": "Tài khoản futures chưa được kích hoạt",
        "solution": "Kích hoạt tài khoản futures"
    },
    "-4012": {
        "message": "Lỗi tài khoản bị khóa",
        "description": "Tài khoản futures bị khóa",
        "solution": "Liên hệ hỗ trợ để mở khóa tài khoản"
    },
    "-4013": {
        "message": "Lỗi tài khoản bị vô hiệu hóa",
        "description": "Tài khoản futures bị vô hiệu hóa",
        "solution": "Liên hệ hỗ trợ để kích hoạt lại tài khoản"
    },
    "-4014": {
        "message": "Lỗi tài khoản bị cấm giao dịch",
        "description": "Tài khoản futures bị cấm giao dịch",
        "solution": "Liên hệ hỗ trợ để xóa lệnh cấm"
    },
    "-4015": {
        "message": "Lỗi tài khoản bị thanh lý",
        "description": "Tài khoản futures bị thanh lý",
        "solution": "Nạp thêm tiền vào tài khoản"
    },
    "-4016": {
        "message": "Lỗi tài khoản bị cấm rút tiền",
        "description": "Tài khoản futures bị cấm rút tiền",
        "solution": "Liên hệ hỗ trợ để xóa lệnh cấm"
    },
}


class TradeErrorHandler:
    """
    Lớp xử lý lỗi giao dịch
    
    Phân tích, phân loại và ghi log các lỗi giao dịch.
    Cung cấp thông tin và gợi ý khắc phục dựa trên loại lỗi.
    """
    
    def __init__(self, log_file: str = "trade_errors.log", notification_callback=None):
        """
        Khởi tạo handler lỗi giao dịch
        
        Args:
            log_file: Đường dẫn file log
            notification_callback: Callback function để gửi thông báo lỗi
        """
        self.log_file = log_file
        self.notification_callback = notification_callback
        
        # Đảm bảo file log tồn tại
        if not os.path.exists(os.path.dirname(log_file)) and os.path.dirname(log_file):
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Thiết lập handler log
        self.logger = logging.getLogger("trade_error_handler")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Xử lý lỗi giao dịch
        
        Args:
            error: Lỗi cần xử lý
            context: Thông tin ngữ cảnh về lỗi
            
        Returns:
            Dict với thông tin lỗi và gợi ý khắc phục
        """
        # Mặc định thông tin lỗi
        error_info = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error_message": str(error),
            "error_type": type(error).__name__,
            "error_code": "UNKNOWN",
            "description": "Lỗi không xác định",
            "solution": "Kiểm tra log chi tiết và thử lại",
            "context": context or {}
        }
        
        # Phân tích lỗi Binance API
        error_msg = str(error)
        if "APIError(code=" in error_msg:
            try:
                # Trích xuất mã lỗi
                code_start = error_msg.find("APIError(code=") + 13
                code_end = error_msg.find(")", code_start)
                if code_end == -1:
                    code_end = error_msg.find(",", code_start)
                
                if code_end != -1:
                    error_code = error_msg[code_start:code_end]
                    
                    # Tìm thông tin lỗi dựa trên mã
                    if error_code in BINANCE_ERROR_CODES:
                        error_info.update({
                            "error_code": f"BINANCE_{error_code}",
                            "description": BINANCE_ERROR_CODES[error_code]["description"],
                            "solution": BINANCE_ERROR_CODES[error_code]["solution"]
                        })
            except Exception as e:
                self.logger.error(f"Lỗi khi phân tích mã lỗi: {str(e)}")
        
        # Ghi log lỗi
        log_message = (
            f"[{error_info['error_code']}] {error_info['error_type']}: {error_info['error_message']} - "
            f"Mô tả: {error_info['description']} - Giải pháp: {error_info['solution']}"
        )
        
        if "context" in error_info and error_info["context"]:
            context_str = json.dumps(error_info["context"], ensure_ascii=False)
            log_message += f" - Ngữ cảnh: {context_str}"
        
        self.logger.error(log_message)
        
        # Gửi thông báo nếu có callback
        if self.notification_callback:
            try:
                self.notification_callback(error_info)
            except Exception as e:
                self.logger.error(f"Lỗi khi gửi thông báo: {str(e)}")
        
        return error_info
    
    def classify_error(self, error_message: str) -> str:
        """
        Phân loại lỗi dựa trên thông điệp
        
        Args:
            error_message: Thông điệp lỗi
            
        Returns:
            Phân loại lỗi
        """
        error_message = error_message.lower()
        
        if "timeout" in error_message or "connection" in error_message:
            return "NETWORK_ERROR"
        elif "insufficient balance" in error_message or "số dư không đủ" in error_message or "balance" in error_message:
            return "BALANCE_ERROR"
        elif "unauthorized" in error_message or "auth" in error_message or "key" in error_message:
            return "AUTHENTICATION_ERROR"
        elif "limit" in error_message or "rate" in error_message:
            return "RATE_LIMIT_ERROR"
        elif "invalid" in error_message and ("quantity" in error_message or "số lượng" in error_message):
            return "QUANTITY_ERROR"
        elif "invalid" in error_message and ("price" in error_message or "giá" in error_message):
            return "PRICE_ERROR"
        elif "leverage" in error_message or "đòn bẩy" in error_message:
            return "LEVERAGE_ERROR"
        elif "symbol" in error_message or "cặp" in error_message:
            return "SYMBOL_ERROR"
        elif "server" in error_message or "maintenance" in error_message or "bảo trì" in error_message:
            return "SERVER_ERROR"
        elif "order" in error_message and "not found" in error_message:
            return "ORDER_NOT_FOUND_ERROR"
        elif "cannot" in error_message and "position" in error_message:
            return "POSITION_ERROR"
        else:
            return "UNKNOWN_ERROR"
    
    def get_solution_for_error(self, error_code: str) -> str:
        """
        Lấy giải pháp cho mã lỗi
        
        Args:
            error_code: Mã lỗi
            
        Returns:
            Giải pháp gợi ý
        """
        # Trích xuất mã lỗi Binance nếu có
        if error_code.startswith("BINANCE_"):
            binance_code = error_code[8:]  # Bỏ tiền tố "BINANCE_"
            if binance_code in BINANCE_ERROR_CODES:
                return BINANCE_ERROR_CODES[binance_code]["solution"]
        
        # Các lỗi phổ biến khác
        solutions = {
            "NETWORK_ERROR": "Kiểm tra kết nối mạng và thử lại sau",
            "BALANCE_ERROR": "Nạp thêm tiền vào tài khoản hoặc giảm kích thước vị thế",
            "AUTHENTICATION_ERROR": "Kiểm tra lại API key và secret, đảm bảo chúng vẫn hoạt động",
            "RATE_LIMIT_ERROR": "Giảm tần suất gửi yêu cầu hoặc đợi ít phút",
            "QUANTITY_ERROR": "Điều chỉnh số lượng để tuân thủ quy tắc của sàn",
            "PRICE_ERROR": "Điều chỉnh giá để tuân thủ quy tắc của sàn",
            "LEVERAGE_ERROR": "Kiểm tra và điều chỉnh cài đặt đòn bẩy",
            "SYMBOL_ERROR": "Kiểm tra lại cặp giao dịch, đảm bảo nó được hỗ trợ và đúng định dạng",
            "SERVER_ERROR": "Đợi đến khi máy chủ hoạt động trở lại",
            "ORDER_NOT_FOUND_ERROR": "Kiểm tra lại ID lệnh",
            "POSITION_ERROR": "Kiểm tra trạng thái vị thế hiện tại",
            "UNKNOWN_ERROR": "Kiểm tra log chi tiết và thử lại"
        }
        
        return solutions.get(error_code, "Kiểm tra log chi tiết và thử lại")
    
    def log_error_summary(self, time_period: str = "day") -> Dict[str, int]:
        """
        Tạo báo cáo tóm tắt về các lỗi trong một khoảng thời gian
        
        Args:
            time_period: Khoảng thời gian (day, week, month)
            
        Returns:
            Dict với số lỗi theo phân loại
        """
        # Xác định thời điểm bắt đầu dựa trên khoảng thời gian
        now = datetime.now()
        if time_period == "day":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_period == "week":
            start_time = now - timedelta(days=now.weekday())
            start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_period == "month":
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Đọc file log
        errors_count = {}
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    for line in f:
                        try:
                            # Phân tích dòng log
                            parts = line.split(' - ')
                            if len(parts) >= 3:
                                # Trích xuất thời gian và mã lỗi
                                log_time_str = parts[0].strip()
                                log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S,%f')
                                
                                # Chỉ đếm lỗi trong khoảng thời gian
                                if log_time >= start_time:
                                    # Trích xuất mã lỗi
                                    error_code_part = parts[1].strip()
                                    if '[' in error_code_part and ']' in error_code_part:
                                        error_code = error_code_part[error_code_part.find('[')+1:error_code_part.find(']')]
                                        errors_count[error_code] = errors_count.get(error_code, 0) + 1
                        except Exception:
                            continue
        except Exception as e:
            self.logger.error(f"Lỗi khi đọc file log: {str(e)}")
        
        return errors_count


# Singleton instance
_error_handler = None

def get_error_handler() -> TradeErrorHandler:
    """Lấy singleton instance của TradeErrorHandler"""
    global _error_handler
    if _error_handler is None:
        _error_handler = TradeErrorHandler()
    return _error_handler


def handle_trading_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Hàm tiện ích để xử lý lỗi giao dịch
    
    Args:
        error: Lỗi cần xử lý
        context: Thông tin ngữ cảnh về lỗi
        
    Returns:
        Dict với thông tin lỗi và gợi ý khắc phục
    """
    handler = get_error_handler()
    return handler.handle_error(error, context)