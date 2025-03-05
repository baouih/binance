#!/usr/bin/env python3
"""
Script thiết lập thông báo Telegram cho bot giao dịch

Script này hướng dẫn người dùng thiết lập và kiểm tra thông báo Telegram
để nhận các cập nhật từ bot giao dịch tự động.
"""

import os
import json
import sys
from telegram_notifier import TelegramNotifier

def main():
    """Hàm chính để thiết lập Telegram Bot"""
    print("=== THIẾT LẬP THÔNG BÁO TELEGRAM CHO BOT GIAO DỊCH ===\n")
    
    # Kiểm tra xem đã có cấu hình chưa
    notifier = TelegramNotifier()
    if notifier.token and notifier.chat_id:
        print(f"Đã tìm thấy cấu hình Telegram hiện tại:")
        print(f"- Token: {notifier.token[:5]}...{notifier.token[-5:]}")
        print(f"- Chat ID: {notifier.chat_id}")
        
        # Hỏi người dùng có muốn thay đổi cấu hình không
        change = input("\nBạn có muốn thay đổi cấu hình Telegram này không? (y/n) [n]: ").strip().lower()
        if change != 'y':
            # Kiểm tra kết nối hiện tại
            print("\nĐang kiểm tra kết nối Telegram...\n")
            test_result = notifier.send_notification('info', "🧪 Đây là tin nhắn kiểm tra kết nối từ bot giao dịch")
            
            if test_result.get('ok'):
                print("✅ Kết nối thành công! Bạn sẽ nhận được thông báo khi bot hoạt động.")
            else:
                print(f"❌ Kết nối thất bại: {test_result.get('error', 'Unknown error')}")
                print("Vui lòng thiết lập lại cấu hình Telegram.")
                reset_config = input("Thiết lập lại ngay bây giờ? (y/n) [y]: ").strip().lower()
                if reset_config != 'n':
                    setup_telegram()
            
            return
    
    # Nếu chưa có cấu hình hoặc người dùng muốn thay đổi
    setup_telegram()

def setup_telegram():
    """Hướng dẫn người dùng thiết lập Telegram Bot"""
    print("\n=== HƯỚNG DẪN THIẾT LẬP TELEGRAM BOT ===\n")
    print("Để nhận thông báo về bot giao dịch, bạn cần tạo một Telegram bot và lấy token của nó.")
    print("1. Mở Telegram và tìm kiếm @BotFather")
    print("2. Nhắn tin /newbot cho BotFather")
    print("3. Đặt tên cho bot của bạn")
    print("4. BotFather sẽ tạo bot và cung cấp cho bạn một token")
    print("5. Mở bot vừa tạo và gửi tin nhắn /start")
    
    print("\nBạn đã tạo Telegram bot và có token chưa?")
    ready = input("Nhấn Enter khi đã sẵn sàng, hoặc 'q' để thoát: ").strip().lower()
    if ready == 'q':
        return
    
    # Nhập token
    token = input("\nNhập Telegram Bot token của bạn: ").strip()
    if not token:
        print("Token không hợp lệ. Thoát khỏi thiết lập.")
        return
    
    print("\nBây giờ, chúng ta cần lấy Chat ID của bạn.")
    print("1. Gửi tin nhắn /start cho bot của bạn")
    print("2. Truy cập URL sau (thay token của bạn vào): https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
    print("3. Tìm giá trị \"chat\":{\"id\":XXXXXXXXX} trong kết quả")
    
    # Nhập chat ID
    chat_id = input("\nNhập Chat ID của bạn: ").strip()
    if not chat_id:
        print("Chat ID không hợp lệ. Thoát khỏi thiết lập.")
        return
    
    # Lưu cấu hình
    notifier = TelegramNotifier(token, chat_id)
    notifier.save_config()
    
    # Kiểm tra kết nối
    print("\nĐang kiểm tra kết nối Telegram...\n")
    test_result = notifier.send_notification('info', "🧪 Thiết lập Telegram Bot thành công! Đây là tin nhắn kiểm tra.")
    
    if test_result.get('ok'):
        print("✅ Thiết lập Telegram Bot thành công!")
        print("Từ giờ, bạn sẽ nhận được thông báo về:")
        print("- Trailing Stop được kích hoạt")
        print("- Vị thế đóng")
        print("- Cảnh báo quan trọng từ bot")
    else:
        print(f"❌ Thiết lập thất bại: {test_result.get('error', 'Unknown error')}")
        print("Vui lòng kiểm tra token và chat ID, sau đó thử lại.")

if __name__ == "__main__":
    main()