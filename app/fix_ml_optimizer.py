#!/usr/bin/env python3
import re
import os

# Đường dẫn đến tệp tin cần sửa
file_path = '/home/runner/workspace/app/advanced_ml_optimizer.py'

# Đọc nội dung tệp tin
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Tìm các dòng có lỗi và sửa
pattern1 = r'(X_processed = self\._preprocess_features\(X, )(regime)(, is_training=False\))'
replacement1 = r'\1y=None, regime=\2\3'

# Thực hiện thay thế
modified_content = re.sub(pattern1, replacement1, content)

# Lưu lại tệp tin đã sửa
backup_path = file_path + '.bak'
os.rename(file_path, backup_path)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(modified_content)

print(f"Đã sửa xong tệp tin {file_path}. Bản sao lưu tại {backup_path}")