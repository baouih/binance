#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module kiểm tra tính hợp lệ của API credentials
"""

import os
import json
import logging
import time
import traceback
import requests

# Xử lý vấn đề import để tránh lỗi
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
except ImportError:
    # Tạo lớp giả khi không import được
    class Client:
        def __init__(self, *args, **kwargs):
            pass
    
    class BinanceAPIException(Exception):
        pass

# Cấu hình logging
logger = logging.getLogger("api_validator")

def validate_binance_credentials(api_key=None, api_secret=None, testnet=True):
    """
    Kiểm tra tính hợp lệ của Binance API credentials
    
    :param api_key: Binance API key
    :param api_secret: Binance API secret
    :param testnet: Sử dụng testnet hay không
    :return: Dict kết quả kiểm tra
    """
    # Sử dụng biến môi trường nếu không có đầu vào
    api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY")
    api_secret = api_secret or os.environ.get("BINANCE_TESTNET_API_SECRET")
    
    # Kiểm tra xem có API key và secret không
    if not api_key or not api_secret:
        return {
            "status": "error",
            "is_valid": False,
            "message": "Thiếu API key hoặc secret",
            "details": "Cần cung cấp cả API key và secret để kiểm tra"
        }
    
    try:
        # Tạo client và kiểm tra kết nối
        client = Client(api_key=api_key, api_secret=api_secret, testnet=testnet)
        
        # Thử lấy thông tin tài khoản
        account_info = client.get_account() if not testnet else client.get_account(recvWindow=5000)
        
        return {
            "status": "success",
            "is_valid": True,
            "message": "API credentials hợp lệ",
            "account_info": {
                "can_trade": account_info.get("canTrade", False),
                "permissions": account_info.get("permissions", []),
                "balance_count": len(account_info.get("balances", [])),
                "account_type": "testnet" if testnet else "live"
            }
        }
    except BinanceAPIException as e:
        error_code = getattr(e, "code", "unknown")
        error_message = str(e)
        
        if error_code == -2015 or "Invalid API-key" in error_message:
            return {
                "status": "error",
                "is_valid": False,
                "message": "API key không hợp lệ",
                "details": error_message,
                "error_code": error_code
            }
        elif error_code == -2014 or "API-key format invalid" in error_message:
            return {
                "status": "error",
                "is_valid": False,
                "message": "Định dạng API key không hợp lệ",
                "details": error_message,
                "error_code": error_code
            }
        else:
            return {
                "status": "error",
                "is_valid": False,
                "message": f"Lỗi Binance API: {error_message}",
                "details": error_message,
                "error_code": error_code
            }
    except Exception as e:
        return {
            "status": "error",
            "is_valid": False,
            "message": f"Lỗi không xác định: {str(e)}",
            "details": traceback.format_exc()
        }

def validate_telegram_credentials(token=None, chat_id=None):
    """
    Kiểm tra tính hợp lệ của Telegram bot credentials
    
    :param token: Telegram bot token
    :param chat_id: Telegram chat ID
    :return: Dict kết quả kiểm tra
    """
    # Sử dụng biến môi trường nếu không có đầu vào
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    
    # Kiểm tra xem có token và chat_id không
    if not token:
        return {
            "status": "error",
            "is_valid": False,
            "message": "Thiếu Telegram bot token",
            "details": "Cần cung cấp Telegram bot token để kiểm tra"
        }
    
    if not chat_id:
        return {
            "status": "error",
            "is_valid": False,
            "message": "Thiếu Telegram chat ID",
            "details": "Cần cung cấp Telegram chat ID để kiểm tra"
        }
    
    try:
        # Thử gửi tin nhắn để kiểm tra
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        # Tạo nội dung tin nhắn kiểm tra
        test_message = f"✅ Kiểm tra kết nối bot thành công! [{time.strftime('%H:%M:%S')}]"
        
        # Gửi request
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": test_message
            },
            timeout=10
        )
        
        # Kiểm tra kết quả
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "is_valid": True,
                "message": "Telegram credentials hợp lệ",
                "details": {
                    "message_id": data.get("result", {}).get("message_id"),
                    "bot_name": data.get("result", {}).get("from", {}).get("username"),
                    "chat_type": data.get("result", {}).get("chat", {}).get("type")
                }
            }
        else:
            error_data = response.json()
            error_code = error_data.get("error_code")
            error_description = error_data.get("description", "Unknown error")
            
            # Xử lý các lỗi phổ biến
            if error_code == 401:
                return {
                    "status": "error",
                    "is_valid": False,
                    "message": "Bot token không hợp lệ",
                    "details": error_description,
                    "error_code": error_code
                }
            elif error_code == 400 and "chat not found" in error_description.lower():
                return {
                    "status": "error",
                    "is_valid": False,
                    "message": "Chat ID không hợp lệ",
                    "details": error_description,
                    "error_code": error_code
                }
            else:
                return {
                    "status": "error",
                    "is_valid": False,
                    "message": f"Lỗi Telegram API: {error_description}",
                    "details": error_description,
                    "error_code": error_code
                }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "is_valid": False,
            "message": "Timeout khi kết nối tới Telegram API",
            "details": "Kiểm tra kết nối mạng hoặc thử lại sau"
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "is_valid": False,
            "message": f"Lỗi kết nối: {str(e)}",
            "details": traceback.format_exc()
        }
    except Exception as e:
        return {
            "status": "error",
            "is_valid": False,
            "message": f"Lỗi không xác định: {str(e)}",
            "details": traceback.format_exc()
        }

def validate_api_credentials():
    """
    Kiểm tra tất cả các API credentials và trả về kết quả
    
    :return: Dict kết quả kiểm tra
    """
    results = {}
    
    # Kiểm tra Binance testnet
    binance_testnet_result = validate_binance_credentials(testnet=True)
    results["binance_testnet"] = binance_testnet_result
    
    # Kiểm tra Telegram
    telegram_result = validate_telegram_credentials()
    results["telegram"] = telegram_result
    
    # Tổng hợp kết quả
    all_valid = all(result.get("is_valid", False) for result in results.values())
    
    return {
        "status": "success" if all_valid else "warning",
        "all_valid": all_valid,
        "results": results
    }

# Hàm để thử nghiệm module
def test_api_validator():
    """Hàm kiểm tra chức năng của API validator"""
    # Cấu hình logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("=== Kiểm tra API credentials ===")
    
    # Kiểm tra Binance testnet
    print("\n--- Kiểm tra Binance testnet credentials ---")
    binance_testnet_result = validate_binance_credentials(testnet=True)
    print(f"Trạng thái: {binance_testnet_result['status']}")
    print(f"Hợp lệ: {binance_testnet_result['is_valid']}")
    print(f"Thông báo: {binance_testnet_result['message']}")
    
    if binance_testnet_result["is_valid"]:
        print("Thông tin tài khoản:")
        for key, value in binance_testnet_result["account_info"].items():
            print(f"  - {key}: {value}")
    
    # Kiểm tra Telegram
    print("\n--- Kiểm tra Telegram credentials ---")
    telegram_result = validate_telegram_credentials()
    print(f"Trạng thái: {telegram_result['status']}")
    print(f"Hợp lệ: {telegram_result['is_valid']}")
    print(f"Thông báo: {telegram_result['message']}")
    
    if telegram_result["is_valid"]:
        print("Chi tiết:")
        for key, value in telegram_result["details"].items():
            print(f"  - {key}: {value}")
    
    # Tổng hợp kết quả
    print("\n--- Tổng hợp kết quả ---")
    all_results = validate_api_credentials()
    print(f"Tất cả hợp lệ: {all_results['all_valid']}")

if __name__ == "__main__":
    test_api_validator()