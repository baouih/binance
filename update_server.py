#!/usr/bin/env python3
"""
Update Server - Máy chủ cập nhật cho Crypto Trading Bot

Script này tạo ra một máy chủ web đơn giản để phục vụ các cập nhật cho Crypto Trading Bot.
Nó cho phép các client kiểm tra và tải các bản cập nhật mới nhất.
"""

import os
import sys
import json
import time
import zipfile
import hashlib
import logging
import argparse
import datetime
import shutil
import glob
from typing import Dict, List, Optional, Any, Tuple

from flask import Flask, request, jsonify, send_file

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("update_server.log"),
        logging.StreamHandler()
    ]
)

# Cấu hình mặc định
DEFAULT_CONFIG = {
    "port": 5001,
    "host": "0.0.0.0",
    "auth_token": "your_auth_token_here",
    "update_dir": "updates",
    "versions_file": "versions.json",
    "client_logs_dir": "client_logs",
    "authorized_clients": []
}

# Đối tượng Flask app
app = Flask(__name__)

# Cấu hình
config = {}

def load_config(config_path: str) -> Dict:
    """
    Tải cấu hình từ file
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        
    Returns:
        Dict: Cấu hình
    """
    global config
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                
                # Cập nhật các key mặc định nếu thiếu
                for key, value in DEFAULT_CONFIG.items():
                    if key not in loaded_config:
                        loaded_config[key] = value
                
                config = loaded_config
                logging.info(f"Đã tải cấu hình từ {config_path}")
                return config
        except Exception as e:
            logging.error(f"Lỗi khi tải cấu hình: {str(e)}")
    
    # Sử dụng cấu hình mặc định
    config = DEFAULT_CONFIG.copy()
    
    # Lưu cấu hình mặc định
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        logging.info(f"Đã tạo cấu hình mặc định tại {config_path}")
    except Exception as e:
        logging.error(f"Lỗi khi tạo cấu hình mặc định: {str(e)}")
    
    return config

def save_config(config_path: str) -> bool:
    """
    Lưu cấu hình vào file
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
        
    Returns:
        bool: True nếu lưu thành công, False nếu thất bại
    """
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        logging.info(f"Đã lưu cấu hình vào {config_path}")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi lưu cấu hình: {str(e)}")
        return False

def load_versions() -> Dict:
    """
    Tải thông tin các phiên bản từ file
    
    Returns:
        Dict: Thông tin các phiên bản
    """
    versions_file = config["versions_file"]
    
    if os.path.exists(versions_file):
        try:
            with open(versions_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Lỗi khi tải thông tin phiên bản: {str(e)}")
    
    # Tạo file versions mới nếu không tồn tại
    empty_versions = {
        "latest_version": "1.0.0",
        "versions": {
            "1.0.0": {
                "release_date": datetime.datetime.now().isoformat(),
                "description": "Phiên bản ban đầu",
                "file": "bot_v1.0.0.zip",
                "checksum": "",
                "min_version_to_upgrade": "0.0.0",
                "changes": ["Phiên bản ban đầu"]
            }
        }
    }
    
    try:
        with open(versions_file, 'w') as f:
            json.dump(empty_versions, f, indent=4)
        
        logging.info(f"Đã tạo file thông tin phiên bản mặc định tại {versions_file}")
    except Exception as e:
        logging.error(f"Lỗi khi tạo file thông tin phiên bản mặc định: {str(e)}")
    
    return empty_versions

def save_versions(versions: Dict) -> bool:
    """
    Lưu thông tin các phiên bản vào file
    
    Args:
        versions (Dict): Thông tin các phiên bản
        
    Returns:
        bool: True nếu lưu thành công, False nếu thất bại
    """
    versions_file = config["versions_file"]
    
    try:
        with open(versions_file, 'w') as f:
            json.dump(versions, f, indent=4)
        
        logging.info(f"Đã lưu thông tin phiên bản vào {versions_file}")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi lưu thông tin phiên bản: {str(e)}")
        return False

def authenticate_request() -> Tuple[bool, str]:
    """
    Xác thực yêu cầu từ client
    
    Returns:
        Tuple[bool, str]: (Thành công hay không, Thông báo lỗi nếu có)
    """
    # Lấy dữ liệu từ request
    data = request.get_json(silent=True)
    if not data:
        return False, "Không có dữ liệu JSON hợp lệ"
    
    # Kiểm tra token xác thực
    auth_token = data.get("auth_token")
    if not auth_token or auth_token != config["auth_token"]:
        return False, "Token xác thực không hợp lệ"
    
    # Kiểm tra client_id
    client_id = data.get("client_id")
    if not client_id:
        return False, "Thiếu client_id"
    
    # Kiểm tra danh sách khách hàng được ủy quyền
    authorized_clients = config.get("authorized_clients", [])
    if authorized_clients and client_id not in authorized_clients:
        # Nếu danh sách không rỗng và client_id không có trong danh sách
        return False, "Client không được ủy quyền"
    
    return True, ""

def log_client_request(data: Dict) -> None:
    """
    Ghi log yêu cầu từ client
    
    Args:
        data (Dict): Dữ liệu từ client
    """
    # Tạo thư mục logs cho client nếu chưa tồn tại
    client_logs_dir = config["client_logs_dir"]
    os.makedirs(client_logs_dir, exist_ok=True)
    
    # Lấy thông tin client
    client_id = data.get("client_id", "unknown")
    timestamp = datetime.datetime.now().isoformat()
    command = data.get("command", "unknown")
    
    # Tạo tên file log
    log_file = os.path.join(client_logs_dir, f"{client_id}.log")
    
    # Ghi log
    try:
        with open(log_file, 'a') as f:
            # Sao chép dữ liệu và xóa thông tin nhạy cảm
            log_data = data.copy()
            if "auth_token" in log_data:
                log_data["auth_token"] = "********"
            
            f.write(f"{timestamp} - Command: {command}\n")
            f.write(f"{json.dumps(log_data, indent=2)}\n")
            f.write("-" * 50 + "\n")
    except Exception as e:
        logging.error(f"Lỗi khi ghi log client: {str(e)}")

def calculate_file_checksum(file_path: str) -> str:
    """
    Tính checksum MD5 của file
    
    Args:
        file_path (str): Đường dẫn đến file
        
    Returns:
        str: Checksum MD5
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def compare_versions(version1: str, version2: str) -> int:
    """
    So sánh hai phiên bản
    
    Args:
        version1 (str): Phiên bản thứ nhất
        version2 (str): Phiên bản thứ hai
        
    Returns:
        int: -1 nếu version1 < version2, 0 nếu version1 = version2, 1 nếu version1 > version2
    """
    def parse_version(version: str) -> List[int]:
        return [int(x) for x in version.split('.')]
    
    v1_parts = parse_version(version1)
    v2_parts = parse_version(version2)
    
    for i in range(max(len(v1_parts), len(v2_parts))):
        v1 = v1_parts[i] if i < len(v1_parts) else 0
        v2 = v2_parts[i] if i < len(v2_parts) else 0
        
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
    
    return 0

@app.route('/api/updates', methods=['POST'])
def handle_update_request():
    """Xử lý yêu cầu cập nhật từ client"""
    # Xác thực yêu cầu
    auth_success, auth_message = authenticate_request()
    if not auth_success:
        return jsonify({"status": "error", "message": auth_message}), 401
    
    # Lấy dữ liệu từ request
    data = request.get_json()
    
    # Ghi log yêu cầu
    log_client_request(data)
    
    # Lấy lệnh từ client
    command = data.get("command", "check_update")
    
    if command == "check_update":
        return handle_check_update(data)
    elif command == "download_update":
        return handle_download_update(data)
    else:
        return jsonify({"status": "error", "message": f"Lệnh không hỗ trợ: {command}"}), 400

def handle_check_update(data: Dict) -> Tuple[Dict, int]:
    """
    Xử lý yêu cầu kiểm tra cập nhật
    
    Args:
        data (Dict): Dữ liệu từ client
        
    Returns:
        Tuple[Dict, int]: (Phản hồi JSON, Mã trạng thái HTTP)
    """
    # Lấy thông tin phiên bản hiện tại của client
    current_version = data.get("current_version", "0.0.0")
    
    # Tải thông tin các phiên bản
    versions = load_versions()
    
    # Lấy phiên bản mới nhất
    latest_version = versions["latest_version"]
    
    # So sánh phiên bản
    if compare_versions(current_version, latest_version) < 0:
        # Cần cập nhật
        update_info = versions["versions"][latest_version].copy()
        
        # Thêm thông tin phiên bản mới
        update_info["new_version"] = latest_version
        
        # Đường dẫn đến file cập nhật
        update_file = os.path.join(config["update_dir"], update_info["file"])
        
        # Kiểm tra xem file tồn tại không
        if not os.path.exists(update_file):
            return jsonify({
                "status": "error",
                "message": f"File cập nhật không tồn tại: {update_info['file']}"
            }), 500
        
        # Cập nhật URL tải xuống
        update_info["download_url"] = f"/api/updates/download/{latest_version}"
        
        # Trả về thông tin cập nhật
        return jsonify({
            "status": "success",
            "update_available": True,
            "update_info": update_info
        }), 200
    else:
        # Không cần cập nhật
        return jsonify({
            "status": "success",
            "update_available": False,
            "message": "Bạn đang sử dụng phiên bản mới nhất"
        }), 200

@app.route('/api/updates/download/<version>', methods=['GET'])
def download_update(version: str):
    """
    Tải xuống bản cập nhật
    
    Args:
        version (str): Phiên bản cần tải xuống
    """
    # Tải thông tin các phiên bản
    versions = load_versions()
    
    # Kiểm tra phiên bản có tồn tại không
    if version not in versions["versions"]:
        return jsonify({
            "status": "error",
            "message": f"Phiên bản không tồn tại: {version}"
        }), 404
    
    # Lấy thông tin file cập nhật
    update_file = os.path.join(config["update_dir"], versions["versions"][version]["file"])
    
    # Kiểm tra xem file tồn tại không
    if not os.path.exists(update_file):
        return jsonify({
            "status": "error",
            "message": f"File cập nhật không tồn tại: {update_file}"
        }), 404
    
    # Gửi file cho client
    try:
        return send_file(
            update_file,
            as_attachment=True,
            download_name=os.path.basename(update_file)
        )
    except Exception as e:
        logging.error(f"Lỗi khi gửi file cập nhật: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Lỗi khi gửi file cập nhật: {str(e)}"
        }), 500

def handle_download_update(data: Dict) -> Tuple[Dict, int]:
    """
    Xử lý yêu cầu tải cập nhật
    
    Args:
        data (Dict): Dữ liệu từ client
        
    Returns:
        Tuple[Dict, int]: (Phản hồi JSON, Mã trạng thái HTTP)
    """
    # Trong trường hợp này, client sẽ sử dụng trực tiếp endpoint /api/updates/download/<version>
    # Hàm này chỉ để xử lý các yêu cầu bổ sung nếu cần
    return jsonify({
        "status": "success",
        "message": "Sử dụng endpoint /api/updates/download/<version> để tải cập nhật"
    }), 200

def create_update_package(version: str, source_dir: str, description: str, changes: List[str]) -> bool:
    """
    Tạo gói cập nhật mới
    
    Args:
        version (str): Phiên bản mới
        source_dir (str): Thư mục chứa mã nguồn
        description (str): Mô tả cập nhật
        changes (List[str]): Danh sách các thay đổi
        
    Returns:
        bool: True nếu tạo thành công, False nếu thất bại
    """
    try:
        # Tải thông tin các phiên bản
        versions = load_versions()
        
        # Kiểm tra xem phiên bản đã tồn tại chưa
        if version in versions["versions"]:
            logging.warning(f"Phiên bản {version} đã tồn tại, sẽ được ghi đè")
        
        # Đảm bảo thư mục updates tồn tại
        os.makedirs(config["update_dir"], exist_ok=True)
        
        # Tên file zip
        zip_file = os.path.join(config["update_dir"], f"bot_v{version}.zip")
        
        # Tạo file zip
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Thêm tất cả các file từ source_dir
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    # Đường dẫn đầy đủ trong thư mục nguồn
                    source_path = os.path.join(root, file)
                    
                    # Bỏ qua các file không cần thiết
                    if any(source_path.endswith(ext) for ext in [".log", ".bak", ".zip", ".pyc"]):
                        continue
                    if ".git" in source_path or "__pycache__" in source_path:
                        continue
                    if os.path.basename(source_path) == "auto_update_config.json":
                        continue
                    
                    # Đường dẫn tương đối so với thư mục nguồn
                    rel_path = os.path.relpath(source_path, source_dir)
                    
                    # Thêm vào zip
                    zipf.write(source_path, rel_path)
        
        # Tính checksum
        checksum = calculate_file_checksum(zip_file)
        
        # Lấy phiên bản nhỏ nhất có thể cập nhật lên phiên bản mới
        min_version = "0.0.0"  # Mặc định là có thể cập nhật từ bất kỳ phiên bản nào
        
        # Cập nhật thông tin phiên bản
        versions["versions"][version] = {
            "release_date": datetime.datetime.now().isoformat(),
            "description": description,
            "file": os.path.basename(zip_file),
            "checksum": checksum,
            "min_version_to_upgrade": min_version,
            "changes": changes
        }
        
        # Cập nhật phiên bản mới nhất
        if compare_versions(version, versions["latest_version"]) > 0:
            versions["latest_version"] = version
        
        # Lưu thông tin phiên bản
        save_versions(versions)
        
        logging.info(f"Đã tạo gói cập nhật v{version}: {zip_file}")
        return True
    
    except Exception as e:
        logging.error(f"Lỗi khi tạo gói cập nhật: {str(e)}")
        return False

def list_updates() -> None:
    """Liệt kê tất cả các bản cập nhật có sẵn"""
    # Tải thông tin các phiên bản
    versions = load_versions()
    
    print(f"\nPhiên bản mới nhất: {versions['latest_version']}")
    print("\nDanh sách các phiên bản có sẵn:")
    print("-" * 80)
    
    for version, info in sorted(versions["versions"].items(), key=lambda x: x[0]):
        is_latest = " (Mới nhất)" if version == versions["latest_version"] else ""
        print(f"Phiên bản: {version}{is_latest}")
        print(f"Ngày phát hành: {info['release_date']}")
        print(f"Mô tả: {info['description']}")
        print(f"File: {info['file']}")
        print(f"Checksum: {info['checksum']}")
        
        print("Thay đổi:")
        for change in info["changes"]:
            print(f"  - {change}")
        
        print("-" * 80)

def init_server(config_path: str) -> None:
    """
    Khởi tạo máy chủ cập nhật
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
    """
    # Tải cấu hình
    load_config(config_path)
    
    # Đảm bảo các thư mục cần thiết tồn tại
    os.makedirs(config["update_dir"], exist_ok=True)
    os.makedirs(config["client_logs_dir"], exist_ok=True)
    
    # Tải thông tin các phiên bản
    load_versions()
    
    print(f"\nMáy chủ cập nhật đã sẵn sàng!")
    print(f"Đang chạy trên http://{config['host']}:{config['port']}")
    print(f"Thư mục cập nhật: {config['update_dir']}")
    print(f"Thư mục logs client: {config['client_logs_dir']}")
    print(f"Token xác thực: {config['auth_token']}")
    print(f"\nSử dụng Ctrl+C để dừng máy chủ")

def main():
    """Hàm chính của script"""
    parser = argparse.ArgumentParser(description="Update Server - Máy chủ cập nhật cho Crypto Trading Bot")
    parser.add_argument("--config", type=str, default="update_server_config.json", help="Đường dẫn đến file cấu hình")
    parser.add_argument("--init", action="store_true", help="Khởi tạo máy chủ cập nhật")
    parser.add_argument("--create-update", action="store_true", help="Tạo gói cập nhật mới")
    parser.add_argument("--version", type=str, help="Phiên bản mới (khi tạo gói cập nhật)")
    parser.add_argument("--source", type=str, help="Thư mục chứa mã nguồn (khi tạo gói cập nhật)")
    parser.add_argument("--description", type=str, help="Mô tả cập nhật (khi tạo gói cập nhật)")
    parser.add_argument("--changes", type=str, help="Danh sách các thay đổi, phân tách bằng dấu phẩy (khi tạo gói cập nhật)")
    parser.add_argument("--list", action="store_true", help="Liệt kê tất cả các bản cập nhật có sẵn")
    
    args = parser.parse_args()
    
    # Tải cấu hình
    load_config(args.config)
    
    if args.init:
        init_server(args.config)
        
        # Chạy máy chủ Flask
        app.run(host=config["host"], port=config["port"])
    elif args.create_update:
        if not args.version:
            print("Lỗi: Thiếu tham số --version")
            return
        
        if not args.source:
            print("Lỗi: Thiếu tham số --source")
            return
        
        description = args.description or f"Cập nhật phiên bản {args.version}"
        changes = args.changes.split(",") if args.changes else [f"Cập nhật phiên bản {args.version}"]
        
        if create_update_package(args.version, args.source, description, changes):
            print(f"Đã tạo gói cập nhật v{args.version} thành công")
        else:
            print(f"Tạo gói cập nhật v{args.version} thất bại")
    elif args.list:
        list_updates()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()