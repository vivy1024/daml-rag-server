#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新测试文件中的请求格式
"""

import re

def update_test_file():
    file_path = '/app/tests/integration/test_e2e_workflow.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找所有没有domain字段的请求，添加domain字段
    # 匹配模式：json={ ... "user_id": TEST_USER_ID, ... } 但没有 "domain"
    lines = content.split('\n')
    updated_lines = []
    
    for i, line in enumerate(lines):
        updated_lines.append(line)
        # 如果这行包含 "user_id": TEST_USER_ID, 并且下一行不包含 "domain"
        if '"user_id": TEST_USER_ID,' in line:
            # 检查接下来的几行是否已经有domain
            has_domain = False
            for j in range(i+1, min(i+5, len(lines))):
                if '"domain"' in lines[j]:
                    has_domain = True
                    break
            
            if not has_domain:
                # 添加domain字段，保持相同的缩进
                indent = len(line) - len(line.lstrip())
                updated_lines.append(' ' * indent + '"domain": "fitness",')
    
    updated_content = '\n'.join(updated_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print('✅ 测试文件已更新')

if __name__ == '__main__':
    update_test_file()
