#!/usr/bin/env python3
"""
修复剩余的文档问题
主要处理文档编号不匹配和路径错误
"""

import os
import re
from pathlib import Path
from typing import Dict


def fix_remaining_issues():
    """修复剩余问题"""
    docs_root = Path('daml-rag-server/docs')
    
    # 1. 修复最后一个格式问题
    fix_last_metadata_issue(docs_root)
    
    # 2. 修复工作流程步骤文档的编号问题
    fix_workflow_step_numbers(docs_root)
    
    # 3. 删除或注释掉指向不存在文档的链接
    fix_broken_links(docs_root)
    
    print("\n✅ 所有修复完成！")


def fix_last_metadata_issue(docs_root: Path):
    """修复最后一个元数据问题"""
    print("📝 修复最后一个元数据问题...")
    
    file_path = docs_root / '04-开发指南/04-最佳实践/07-Grafana性能问题排查指南.md'
    
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        
        # 在第一个标题后添加元数据
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('# '):
                metadata = [
                    '',
                    '**版本**: v1.0.0',
                    '**创建日期**: 2025-12-22',
                    '**状态**: ✅ 已完成',
                    '',
                    '---',
                    ''
                ]
                lines = lines[:i+1] + metadata + lines[i+1:]
                break
        
        file_path.write_text('\n'.join(lines), encoding='utf-8')
        print(f"  ✅ 修复: {file_path.name}")


def fix_workflow_step_numbers(docs_root: Path):
    """修复工作流程步骤文档的编号问题"""
    print("\n🔢 修复工作流程步骤编号...")
    
    # 步骤文档的正确编号映射
    step_mappings = {
        '02-步骤1-用户档案预加载.md': '01-步骤1-用户档案预加载.md',
        '03-步骤2-会话记录存储.md': '02-步骤2-会话记录存储.md',
        '04-步骤3-会员权限检查.md': '03-步骤3-会员权限检查.md',
        '05-步骤4-BGE复杂度分类.md': '04-步骤4-BGE复杂度分类.md',
        '06-步骤5-智能模型选择.md': '05-步骤5-智能模型选择.md',
        '07-步骤6-FewShot检索.md': '06-步骤6-FewShot检索.md',
        '08-步骤6.5-LLM选择DAG方案.md': '07-步骤6.5-LLM选择DAG方案.md',
        '09-步骤7-DAG编排器.md': '08-步骤7-DAG编排器.md',
        '10-步骤8-三层检索.md': '09-步骤8-三层检索.md',
        '11-步骤9-工具结果汇总.md': '10-步骤9-工具结果汇总.md',
        '12-步骤10-LLM深度分析.md': '11-步骤10-LLM深度分析.md',
        '13-步骤11-交互记录.md': '12-步骤11-交互记录.md',
    }
    
    # 批量替换所有文档中的引用
    for md_file in docs_root.rglob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
            original_content = content
            
            for old_name, new_name in step_mappings.items():
                content = content.replace(f'](./{old_name})', f'](./{new_name})')
                content = content.replace(f'](../{old_name})', f'](../{new_name})')
            
            if content != original_content:
                md_file.write_text(content, encoding='utf-8')
                print(f"  ✅ 更新引用: {md_file.relative_to(docs_root)}")
        
        except Exception as e:
            pass


def fix_broken_links(docs_root: Path):
    """修复断链 - 注释掉指向不存在文档的链接"""
    print("\n🔗 处理断链...")
    
    # 已知不存在的文档列表
    non_existent_docs = [
        '系统架构.md',
        '技术栈.md',
        '设计模式.md',
        '目录结构.md',
        '完整工作流程.md',
        'DAML-RAG框架架构.md',
        '25-MCP工具系统参考.md',
        '15-企业级三层检索引擎参考.md',
        '26-DAG模板系统参考.md',
        '29-三段式编排器参考.md',
        '知识图谱快速导入指南.md',
        '监控告警.md',
        '故障排查.md',
        '安全最佳实践.md',
        '健康检查API.md',
        '12-性能优化配置使用指南.md',
        '13-工作流性能优化完整指南.md',
        '05-流式输出监控指南.md',
        '33-LLM提示词优化方案.md',
        '08-损伤禁忌与康复路径设计指南.md',
        '45-训练知识导入指南.md',
        '12.1-步骤10-提示词构建与LLM参数配置.md',
    ]
    
    count = 0
    for md_file in docs_root.rglob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
            original_content = content
            
            # 注释掉指向不存在文档的链接
            for doc_name in non_existent_docs:
                # 匹配链接模式
                pattern = rf'\[([^\]]+)\]\(([^)]*{re.escape(doc_name)})\)'
                matches = re.findall(pattern, content)
                
                for link_text, link_path in matches:
                    old_link = f'[{link_text}]({link_path})'
                    new_link = f'<!-- [{link_text}]({link_path}) (文档不存在) -->'
                    content = content.replace(old_link, new_link)
            
            if content != original_content:
                md_file.write_text(content, encoding='utf-8')
                count += 1
        
        except Exception as e:
            pass
    
    print(f"  ✅ 处理了 {count} 个文件的断链")


if __name__ == '__main__':
    fix_remaining_issues()
