#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tổng hợp và danh sách tất cả các chiến thuật của hệ thống
"""

import os
import sys
import importlib
import inspect
import pkgutil
import re
from datetime import datetime

def get_all_strategy_files():
    """Lấy danh sách tất cả các file có tên chứa các keyword liên quan đến chiến thuật"""
    strategy_keywords = [
        "strategy", "detector", "analyzer", "predictor", 
        "optimized", "adaptive", "backtester", "divergence"
    ]
    
    all_files = []
    for file in os.listdir('.'):
        if file.endswith('.py'):
            for keyword in strategy_keywords:
                if keyword in file.lower() and file not in all_files:
                    all_files.append(file)
    
    return sorted(all_files)

def extract_docstring(file_path):
    """Trích xuất docstring từ file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tìm docstring
        docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if docstring_match:
            return docstring_match.group(1).strip()
        
        return "Không có mô tả"
    except Exception as e:
        return f"Lỗi khi đọc file: {e}"

def extract_classes(file_path):
    """Trích xuất tên các class từ file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tìm các class definition
        class_matches = re.findall(r'class\s+(\w+)', content)
        return class_matches
    except Exception as e:
        return []

def extract_functions(file_path):
    """Trích xuất tên các function từ file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tìm các function definition (loại bỏ các method trong class)
        function_matches = []
        for match in re.finditer(r'def\s+(\w+)\s*\(', content):
            # Kiểm tra indentation để loại bỏ method
            line_start = content[:match.start()].rfind('\n') + 1
            if line_start == -1:
                line_start = 0
            indentation = match.start() - line_start
            
            if indentation <= 4:  # Hàm top-level
                function_matches.append(match.group(1))
        
        return function_matches
    except Exception as e:
        return []

def categorize_strategy_files():
    """Phân loại các file theo loại chiến thuật"""
    strategies = {
        "Core Strategies": [],
        "Market Analysis": [],
        "Technical Indicators": [],
        "Risk Management": [],
        "Optimizers & Backtesting": [],
        "Machine Learning": [],
        "Utility & Integration": []
    }
    
    files = get_all_strategy_files()
    
    for file in files:
        docstring = extract_docstring(file)
        classes = extract_classes(file)
        functions = extract_functions(file)
        
        file_info = {
            "filename": file,
            "docstring": docstring,
            "classes": classes,
            "functions": functions
        }
        
        # Phân loại
        if "backtest" in file.lower() or "test" in file.lower() or "optimizer" in file.lower():
            strategies["Optimizers & Backtesting"].append(file_info)
        elif "ml" in file.lower() or "machine" in file.lower():
            strategies["Machine Learning"].append(file_info)
        elif "risk" in file.lower() or "account" in file.lower():
            strategies["Risk Management"].append(file_info)
        elif "analyzer" in file.lower() or "detector" in file.lower() or "regime" in file.lower():
            strategies["Market Analysis"].append(file_info)
        elif "integration" in file.lower() or "utility" in file.lower() or "factory" in file.lower():
            strategies["Utility & Integration"].append(file_info)
        elif "rsi" in file.lower() or "divergence" in file.lower() or "volume" in file.lower():
            strategies["Technical Indicators"].append(file_info)
        else:
            strategies["Core Strategies"].append(file_info)
    
    return strategies

def generate_markdown_report(categorized_strategies):
    """Tạo báo cáo markdown"""
    report = f"# Tổng hợp các chiến thuật giao dịch\n\n"
    report += f"*Báo cáo được tạo lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    report += f"## Tổng quan\n\n"
    
    total_strategies = sum(len(files) for files in categorized_strategies.values())
    report += f"Hệ thống có tổng cộng **{total_strategies}** file thuật toán và chiến lược, phân loại như sau:\n\n"
    
    for category, files in categorized_strategies.items():
        report += f"- **{category}**: {len(files)} thuật toán\n"
    
    report += f"\n## Chi tiết từng nhóm\n\n"
    
    for category, files in categorized_strategies.items():
        report += f"### {category}\n\n"
        
        for i, file_info in enumerate(files, 1):
            filename = file_info["filename"]
            docstring = file_info["docstring"]
            classes = file_info["classes"]
            functions = file_info["functions"]
            
            report += f"#### {i}. {filename}\n\n"
            
            # Mô tả
            if docstring and docstring != "Không có mô tả":
                # Chỉ lấy 5 dòng đầu
                short_desc = "\n".join(docstring.split("\n")[:5])
                report += f"{short_desc}...\n\n"
            else:
                report += "Không có mô tả\n\n"
            
            # Các class
            if classes:
                report += f"**Các lớp chính:**\n\n"
                for cls in classes:
                    report += f"- `{cls}`\n"
                report += "\n"
            
            # Các hàm chính
            main_functions = [f for f in functions if not f.startswith("_")]
            if main_functions:
                report += f"**Các hàm chính:**\n\n"
                for func in main_functions[:5]:  # Chỉ hiển thị 5 hàm
                    report += f"- `{func}()`\n"
                
                if len(main_functions) > 5:
                    report += f"- ... và {len(main_functions) - 5} hàm khác\n"
                report += "\n"
        
        report += "\n"
    
    report += "## Tóm tắt các chiến thuật chính\n\n"
    
    # Lấy các chiến thuật core
    core_strategies = categorized_strategies["Core Strategies"]
    for file_info in core_strategies:
        filename = file_info["filename"]
        docstring = file_info["docstring"]
        
        report += f"### {filename}\n\n"
        # Chỉ lấy 3 dòng đầu của docstring
        if docstring and docstring != "Không có mô tả":
            short_desc = "\n".join(docstring.split("\n")[:3])
            report += f"{short_desc}...\n\n"
        else:
            report += "Không có mô tả\n\n"
    
    return report

def main():
    categorized_strategies = categorize_strategy_files()
    report = generate_markdown_report(categorized_strategies)
    
    output_file = 'complete_strategies_summary.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Đã tạo báo cáo tại: {output_file}")
    
    # In tóm tắt
    print("\n=== TÓM TẮT CHIẾN THUẬT ===")
    total_strategies = sum(len(files) for files in categorized_strategies.values())
    print(f"Tổng số thuật toán và chiến lược: {total_strategies}")
    
    for category, files in categorized_strategies.items():
        print(f"{category}: {len(files)} thuật toán")
    
    # In ra các chiến thuật core
    print("\nCác chiến thuật cốt lõi:")
    for file_info in categorized_strategies["Core Strategies"]:
        print(f"- {file_info['filename']}")

if __name__ == "__main__":
    main()
