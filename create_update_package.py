#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo gói cập nhật cho máy chủ

Script này tạo gói cập nhật để phát hành cho người dùng, bao gồm các file
được chỉ định hoặc toàn bộ hệ thống. Gói cập nhật được tạo ra có thể được
tải lên máy chủ Replit để người dùng tải xuống.
"""

import os
import sys
import glob
import json
import hashlib
import zipfile
import argparse
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import UpdateManager từ update_manager.py
from update_manager import UpdateManager


def create_update(version: str, description: str = "", changes: List[str] = None, 
                  files: List[str] = None, output_dir: str = None):
    """
    Tạo gói cập nhật với phiên bản và danh sách file chỉ định
    
    Args:
        version (str): Phiên bản của gói cập nhật (vd: "1.0.1")
        description (str): Mô tả về bản cập nhật
        changes (List[str]): Danh sách các thay đổi
        files (List[str]): Danh sách đường dẫn file cần đưa vào gói
        output_dir (str): Thư mục đầu ra cho gói cập nhật
    """
    # Khởi tạo UpdateManager
    update_manager = UpdateManager()
    
    # Thay đổi thư mục đầu ra nếu cần
    if output_dir:
        update_manager.config["update_packages_dir"] = output_dir
        update_manager._save_config()
    
    # Tạo gói cập nhật
    package_path = update_manager.create_update_package(
        version=version,
        files=files,
        description=description,
        changes=changes
    )
    
    if package_path:
        print(f"✅ Đã tạo gói cập nhật thành công: {package_path}")
        return package_path
    else:
        print(f"❌ Không thể tạo gói cập nhật")
        return None


def select_files_interactively() -> List[str]:
    """
    Chọn các file cần đưa vào gói cập nhật theo cách tương tác
    
    Returns:
        List[str]: Danh sách đường dẫn file được chọn
    """
    selected_files = []
    
    # Lấy danh sách các file trong thư mục hiện tại và các thư mục con
    all_files = []
    for root, _, files in os.walk("."):
        for file in files:
            if not file.startswith(".") and not file.endswith(".pyc") and "backup_" not in file and "update_package_" not in file:
                file_path = os.path.join(root, file)[2:]  # remove ./ from path
                all_files.append(file_path)
    
    # Hiển thị menu chọn file
    print("\n=== Chọn các file cần đưa vào gói cập nhật ===")
    print("0. Bao gồm tất cả các file")
    
    # Nhóm các file theo thư mục
    file_groups = {}
    for file_path in all_files:
        directory = os.path.dirname(file_path) or "root"
        if directory not in file_groups:
            file_groups[directory] = []
        file_groups[directory].append(file_path)
    
    # Hiển thị danh sách thư mục
    directories = sorted(file_groups.keys())
    for i, directory in enumerate(directories, 1):
        print(f"{i}. Thư mục: {directory} ({len(file_groups[directory])} files)")
    
    # Hỏi người dùng chọn thư mục
    while True:
        choice = input("\nChọn thư mục (0 cho tất cả, -1 để kết thúc): ")
        
        try:
            choice = int(choice)
            
            if choice == 0:
                # Chọn tất cả các file
                return None
            
            elif choice == -1:
                # Kết thúc chọn
                break
            
            elif 1 <= choice <= len(directories):
                directory = directories[choice - 1]
                files_in_dir = file_groups[directory]
                
                # Hiển thị danh sách file trong thư mục
                print(f"\nCác file trong thư mục {directory}:")
                for i, file_path in enumerate(files_in_dir, 1):
                    print(f"{i}. {file_path}")
                
                # Hỏi người dùng chọn file
                subchoice = input("\nChọn file (0 cho tất cả trong thư mục này, -1 để quay lại): ")
                
                try:
                    subchoice = int(subchoice)
                    
                    if subchoice == 0:
                        # Chọn tất cả các file trong thư mục
                        selected_files.extend(files_in_dir)
                        print(f"Đã chọn {len(files_in_dir)} files từ thư mục {directory}")
                    
                    elif subchoice == -1:
                        # Quay lại menu chọn thư mục
                        continue
                    
                    elif 1 <= subchoice <= len(files_in_dir):
                        # Chọn một file cụ thể
                        selected_file = files_in_dir[subchoice - 1]
                        if selected_file not in selected_files:
                            selected_files.append(selected_file)
                            print(f"Đã chọn: {selected_file}")
                        else:
                            print(f"File {selected_file} đã được chọn trước đó")
                    
                    else:
                        print("Lựa chọn không hợp lệ")
                
                except ValueError:
                    print("Vui lòng nhập một số nguyên")
            
            else:
                print("Lựa chọn không hợp lệ")
        
        except ValueError:
            print("Vui lòng nhập một số nguyên")
    
    return selected_files if selected_files else None


def main():
    """Hàm chính của script"""
    parser = argparse.ArgumentParser(description="Tạo gói cập nhật cho người dùng")
    
    parser.add_argument("--version", type=str, help="Phiên bản của gói cập nhật (vd: 1.0.1)")
    parser.add_argument("--description", type=str, default="", help="Mô tả về bản cập nhật")
    parser.add_argument("--changes", type=str, nargs="+", help="Danh sách các thay đổi")
    parser.add_argument("--files", type=str, nargs="+", help="Danh sách đường dẫn file cần đưa vào gói")
    parser.add_argument("--output-dir", type=str, help="Thư mục đầu ra cho gói cập nhật")
    parser.add_argument("--interactive", action="store_true", help="Chọn các file theo cách tương tác")
    
    args = parser.parse_args()
    
    # Kiểm tra phiên bản
    if not args.version:
        # Đọc phiên bản hiện tại và tăng lên
        update_manager = UpdateManager()
        current_version = update_manager.config.get("version", "1.0.0")
        
        # Tăng phiên bản
        version_parts = current_version.split(".")
        version_parts[-1] = str(int(version_parts[-1]) + 1)
        suggested_version = ".".join(version_parts)
        
        # Hỏi người dùng
        version = input(f"Nhập phiên bản (mặc định: {suggested_version}): ")
        if not version:
            version = suggested_version
    else:
        version = args.version
    
    # Kiểm tra mô tả
    if not args.description:
        description = input("Nhập mô tả về bản cập nhật: ")
    else:
        description = args.description
    
    # Kiểm tra danh sách thay đổi
    if not args.changes:
        changes_str = input("Nhập danh sách thay đổi (mỗi dòng là một thay đổi, nhấn Enter hai lần để kết thúc):\n")
        changes = []
        
        while changes_str:
            changes.append(changes_str)
            changes_str = input()
    else:
        changes = args.changes
    
    # Kiểm tra danh sách file
    if args.interactive:
        files = select_files_interactively()
    elif not args.files:
        include_all = input("Bạn muốn bao gồm tất cả các file? (y/n): ")
        if include_all.lower() == 'y':
            files = None
        else:
            files = select_files_interactively()
    else:
        files = args.files
    
    # Tạo gói cập nhật
    create_update(
        version=version,
        description=description,
        changes=changes,
        files=files,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()