#!/usr/bin/env python3
"""
批量修复中文字体显示问题
为所有图表文本添加中文字体属性
"""

import re

def fix_chinese_font_in_file():
    """修复results_analysis.py中的中文字体问题"""
    
    file_path = 'simpower/results_analysis.py'
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义需要修改的函数调用模式
    patterns = [
        # set_title 函数
        (r"(\.set_title\([^)]*?\bfontweight='bold')", r"\1, **get_chinese_font_prop()"),
        (r"(\.set_title\([^)]*?['\"])", r"\1, **get_chinese_font_prop()"),
        
        # set_xlabel 和 set_ylabel 函数
        (r"(\.set_xlabel\([^)]*?['\"][^)]*?)", r"\1, **get_chinese_font_prop()"),
        (r"(\.set_ylabel\([^)]*?['\"][^)]*?)", r"\1, **get_chinese_font_prop()"),
        
        # fig.suptitle (已经修改过的不重复修改)
        # 其他可能的文本设置
        (r"(ax\w*\.text\([^)]*?['\"][^)]*?)", r"\1, **get_chinese_font_prop()"),
    ]
    
    original_content = content
    
    for pattern, replacement in patterns:
        # 只替换还没有添加中文字体属性的
        content = re.sub(pattern + r"(?!\s*,\s*\*\*get_chinese_font_prop\(\))", 
                        replacement + ")", content)
    
    print(f"🔧 修复中文字体显示...")
    
    # 检查修改
    changes = 0
    for line_num, (orig_line, new_line) in enumerate(zip(original_content.split('\n'), content.split('\n')), 1):
        if orig_line != new_line:
            print(f"Line {line_num}: {orig_line.strip()[:50]}... -> {new_line.strip()[:50]}...")
            changes += 1
    
    if changes > 0:
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已修改 {changes} 处，保存到 {file_path}")
    else:
        print("✅ 无需修改")

if __name__ == "__main__":
    fix_chinese_font_in_file()