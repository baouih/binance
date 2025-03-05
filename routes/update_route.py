"""
Blueprint cho các route quản lý cập nhật

Module này cung cấp các endpoints API và trang web cho việc quản lý cập nhật hệ thống, 
bao gồm tải lên, cài đặt, và quay lại các bản cập nhật cũ.
"""

import os
import json
import time
import logging
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

from update_manager import UpdateManager

logger = logging.getLogger('update_route')

update_bp = Blueprint('update', __name__, url_prefix='/update')
manager = UpdateManager()

# Đảm bảo các thư mục tồn tại
os.makedirs("update_packages", exist_ok=True)
os.makedirs("backups", exist_ok=True)

@update_bp.route('/', methods=['GET'])
def update_home():
    """Trang chủ quản lý cập nhật"""
    return render_template('updates.html',
                           current_version=manager.get_current_version(),
                           available_updates=manager.get_available_updates(),
                           update_history=manager.get_update_history(),
                           backups=manager.get_available_backups())

@update_bp.route('/create', methods=['GET', 'POST'])
def create_update():
    """Trang tạo gói cập nhật mới"""
    if request.method == 'POST':
        try:
            version = request.form.get('version')
            description = request.form.get('description', '')
            
            # Kiểm tra phiên bản
            if not version:
                flash('Phiên bản không được để trống!', 'error')
                return redirect(url_for('update.create_update'))
            
            # Lấy danh sách file từ form
            files = request.form.getlist('files')
            
            # Tạo gói cập nhật
            update_path = manager.create_update_package(
                version=version,
                files=files if files else None,
                description=description
            )
            
            if update_path:
                flash(f'Đã tạo gói cập nhật phiên bản {version} thành công!', 'success')
                return redirect(url_for('update.update_home'))
            else:
                flash('Không thể tạo gói cập nhật!', 'error')
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo gói cập nhật: {str(e)}")
            flash(f'Lỗi: {str(e)}', 'error')
    
    # Chuẩn bị danh sách file có thể chọn
    available_files = []
    # Các file Python trong thư mục gốc
    for file in os.listdir('.'):
        if file.endswith('.py') and not file.startswith('__'):
            available_files.append(file)
    
    # Các thư mục quan trọng
    important_dirs = ['app', 'routes', 'models', 'templates', 'static']
    for dir_name in important_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            available_files.append(f"{dir_name}/*")
    
    return render_template('create_update.html',
                           current_version=manager.get_current_version(),
                           available_files=available_files)

@update_bp.route('/upload', methods=['POST'])
def upload_update():
    """API để tải lên gói cập nhật"""
    if 'update_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'Không tìm thấy file cập nhật'})
    
    update_file = request.files['update_file']
    if update_file.filename == '':
        return jsonify({'status': 'error', 'message': 'Không có file nào được chọn'})
    
    if update_file and update_file.filename.endswith('.zip'):
        filename = secure_filename(update_file.filename)
        
        # Thêm timestamp để tránh trùng tên
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if '_v' in filename:
            # Giữ nguyên phần phiên bản
            base_name, version = filename.rsplit('_v', 1)
            filename = f"{base_name}_{timestamp}_v{version}"
        else:
            # Thêm timestamp vào tên
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{timestamp}{ext}"
        
        file_path = os.path.join('update_packages', filename)
        update_file.save(file_path)
        
        return jsonify({
            'status': 'success',
            'message': 'Đã tải lên gói cập nhật thành công',
            'filename': filename,
            'path': file_path
        })
    
    return jsonify({'status': 'error', 'message': 'File không hợp lệ'})

@update_bp.route('/create_backup', methods=['POST'])
def create_backup():
    """API để tạo bản sao lưu mới"""
    try:
        # Tạo tên file sao lưu với timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"manual_backup_{timestamp}"
        
        # Tạo bản sao lưu
        backup_path = manager.create_backup(backup_name)
        
        if backup_path:
            return jsonify({
                'status': 'success',
                'message': 'Đã tạo bản sao lưu thành công',
                'backup_path': backup_path,
                'filename': os.path.basename(backup_path)
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Không thể tạo bản sao lưu'
            })
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo bản sao lưu: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi tạo bản sao lưu: {str(e)}'
        })

@update_bp.route('/apply/<filename>', methods=['POST'])
def apply_update(filename):
    """API để áp dụng gói cập nhật"""
    try:
        # Kiểm tra file tồn tại
        update_path = os.path.join('update_packages', filename)
        if not os.path.exists(update_path):
            return jsonify({
                'status': 'error',
                'message': f'Không tìm thấy gói cập nhật: {filename}'
            })
        
        # Tạo bản sao lưu trước khi cập nhật
        backup_path = manager.create_backup(f"before_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if not backup_path:
            return jsonify({
                'status': 'error',
                'message': 'Không thể tạo bản sao lưu trước khi cập nhật'
            })
        
        # Áp dụng cập nhật
        result = manager.apply_update(update_path, auto_backup=False)  # Đã tạo backup ở trên
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f'Đã cập nhật thành công lên phiên bản {manager.get_current_version()}',
                'version': manager.get_current_version(),
                'backup_path': backup_path
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Không thể áp dụng gói cập nhật'
            })
    
    except Exception as e:
        logger.error(f"Lỗi khi áp dụng cập nhật: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi áp dụng cập nhật: {str(e)}'
        })

@update_bp.route('/rollback/<filename>', methods=['POST'])
def rollback_update(filename):
    """API để quay lại phiên bản cũ từ bản sao lưu"""
    try:
        # Kiểm tra file tồn tại
        backup_path = os.path.join('backups', filename)
        if not os.path.exists(backup_path):
            return jsonify({
                'status': 'error',
                'message': f'Không tìm thấy bản sao lưu: {filename}'
            })
        
        # Tạo bản sao lưu của phiên bản hiện tại trước khi rollback
        current_backup = manager.create_backup(f"before_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if not current_backup:
            return jsonify({
                'status': 'warning',
                'message': 'Không thể tạo bản sao lưu của phiên bản hiện tại trước khi rollback, nhưng vẫn tiếp tục'
            })
        
        # Quay lại phiên bản cũ
        result = manager.rollback(backup_path)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f'Đã quay lại phiên bản {manager.get_current_version()} thành công',
                'version': manager.get_current_version()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Không thể quay lại phiên bản cũ'
            })
    
    except Exception as e:
        logger.error(f"Lỗi khi quay lại phiên bản cũ: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi quay lại phiên bản cũ: {str(e)}'
        })

@update_bp.route('/download/update/<filename>', methods=['GET'])
def download_update(filename):
    """API để tải xuống gói cập nhật"""
    try:
        file_path = os.path.join('update_packages', filename)
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': f'Không tìm thấy gói cập nhật: {filename}'
            })
        
        return send_file(file_path, as_attachment=True)
    
    except Exception as e:
        logger.error(f"Lỗi khi tải xuống gói cập nhật: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi tải xuống gói cập nhật: {str(e)}'
        })

@update_bp.route('/download/backup/<filename>', methods=['GET'])
def download_backup(filename):
    """API để tải xuống bản sao lưu"""
    try:
        file_path = os.path.join('backups', filename)
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': f'Không tìm thấy bản sao lưu: {filename}'
            })
        
        return send_file(file_path, as_attachment=True)
    
    except Exception as e:
        logger.error(f"Lỗi khi tải xuống bản sao lưu: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi tải xuống bản sao lưu: {str(e)}'
        })

@update_bp.route('/delete/update/<filename>', methods=['POST'])
def delete_update(filename):
    """API để xóa gói cập nhật"""
    try:
        file_path = os.path.join('update_packages', filename)
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': f'Không tìm thấy gói cập nhật: {filename}'
            })
        
        os.remove(file_path)
        
        return jsonify({
            'status': 'success',
            'message': f'Đã xóa gói cập nhật {filename}'
        })
    
    except Exception as e:
        logger.error(f"Lỗi khi xóa gói cập nhật: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi xóa gói cập nhật: {str(e)}'
        })

@update_bp.route('/delete/backup/<filename>', methods=['POST'])
def delete_backup(filename):
    """API để xóa bản sao lưu"""
    try:
        file_path = os.path.join('backups', filename)
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': f'Không tìm thấy bản sao lưu: {filename}'
            })
        
        os.remove(file_path)
        
        return jsonify({
            'status': 'success',
            'message': f'Đã xóa bản sao lưu {filename}'
        })
    
    except Exception as e:
        logger.error(f"Lỗi khi xóa bản sao lưu: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi xóa bản sao lưu: {str(e)}'
        })

def register_blueprint(app):
    """Đăng ký blueprint với ứng dụng Flask"""
    app.register_blueprint(update_bp)
    logger.info("Đã đăng ký blueprint update_route")