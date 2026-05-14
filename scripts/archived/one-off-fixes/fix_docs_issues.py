#!/usr/bin/env python3
"""
文档问题修复脚本
自动修复文档格式问题和引用链接问题
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime


class DocsFixer:
    """文档修复器"""
    
    def __init__(self, docs_root: str):
        self.docs_root = Path(docs_root)
        self.fixed_count = {
            'metadata': 0,
            'links': 0,
            'total_files': 0
        }
        
        # 文档路径映射（旧路径 -> 新路径）
        self.path_mappings = self._build_path_mappings()
    
    def _build_path_mappings(self) -> Dict[str, str]:
        """构建文档路径映射表"""
        mappings = {
            # 02-核心架构的映射
            '../02-核心架构/03-完整工作流程.md': '../../02-核心架构/01-系统架构/02-完整工作流程.md',
            '../02-核心架构/02-系统架构总览.md': '../../02-核心架构/01-系统架构/01-系统架构总览.md',
            '../02-核心架构/04-数据库结构.md': '../../02-核心架构/02-数据层/01-数据库结构总览.md',
            '../02-核心架构/05-MCP工具架构.md': '../../02-核心架构/03-编排层/03-MCP工具架构.md',
            '../02-核心架构/11-Neo4j数据库结构.md': '../../02-核心架构/02-数据层/02-Neo4j数据库结构.md',
            
            # 03-代码参考的映射
            '../03-代码参考/12-步骤10-LLM深度分析.md': '../../03-代码参考/01-工作流程步骤/11-步骤10-LLM深度分析.md',
            '../03-代码参考/09-步骤7-DAG编排器.md': '../../03-代码参考/01-工作流程步骤/08-步骤7-DAG编排器.md',
            '../03-代码参考/10-步骤8-三层检索.md': '../../03-代码参考/01-工作流程步骤/09-步骤8-三层检索.md',
            
            # 04-开发指南的映射
            './12-性能优化配置使用指南.md': '../03-配置管理/04-性能优化配置使用指南.md',
            './11-性能优化完整指南.md': './02-性能优化完整指南.md',
            './04-监控和可观测性完整指南.md': './01-监控和可观测性完整指南.md',
            
            # 删除或移动的文档
            '../04-开发指南/12-性能优化配置使用指南.md': None,  # 已移动
            '../04-开发指南/13-工作流性能优化完整指南.md': None,  # 已删除
            '../04-开发指南/05-流式输出监控指南.md': None,  # 已删除
        }
        return mappings
    
    def fix_all(self):
        """修复所有问题"""
        print("=" * 80)
        print("开始修复文档问题")
        print("=" * 80)
        print()
        
        # 1. 修复文档格式
        print("📝 步骤1：修复文档格式问题...")
        self.fix_metadata()
        print()
        
        # 2. 修复引用链接
        print("🔗 步骤2：修复引用链接...")
        self.fix_references()
        print()
        
        # 3. 生成报告
        self.generate_report()
    
    def fix_metadata(self):
        """修复文档元数据"""
        for md_file in self.docs_root.rglob('*.md'):
            if md_file.name == 'README.md':
                continue
            
            try:
                content = md_file.read_text(encoding='utf-8')
                original_content = content
                
                # 检查是否缺少元数据
                has_version = bool(re.search(r'\*\*版本\*\*:\s*v?\d+\.\d+\.\d+', content[:500]))
                has_date = bool(re.search(r'\*\*创建日期\*\*:\s*\d{4}-\d{2}-\d{2}', content[:500]))
                has_status = bool(re.search(r'\*\*状态\*\*:\s*(✅|📋|🚧|🎉|🔄)', content[:500]))
                
                if not (has_version and has_date and has_status):
                    # 添加缺失的元数据
                    content = self._add_metadata(content, has_version, has_date, has_status)
                    
                    if content != original_content:
                        md_file.write_text(content, encoding='utf-8')
                        self.fixed_count['metadata'] += 1
                        relative_path = md_file.relative_to(self.docs_root)
                        print(f"  ✅ 修复元数据: {relative_path}")
            
            except Exception as e:
                print(f"  ❌ 处理失败: {md_file.name} - {e}")
    
    def _add_metadata(self, content: str, has_version: bool, has_date: bool, has_status: bool) -> str:
        """添加缺失的元数据"""
        lines = content.split('\n')
        
        # 找到第一个标题
        title_idx = -1
        for i, line in enumerate(lines):
            if line.startswith('# '):
                title_idx = i
                break
        
        if title_idx == -1:
            return content
        
        # 构建元数据
        metadata_lines = []
        if not has_version:
            metadata_lines.append('**版本**: v1.0.0')
        if not has_date:
            metadata_lines.append(f'**创建日期**: {datetime.now().strftime("%Y-%m-%d")}')
        if not has_status:
            metadata_lines.append('**状态**: ✅ 已完成')
        
        # 插入元数据
        if metadata_lines:
            # 在标题后插入
            insert_lines = [''] + metadata_lines + ['', '---', '']
            lines = lines[:title_idx+1] + insert_lines + lines[title_idx+1:]
        
        return '\n'.join(lines)
    
    def fix_references(self):
        """修复引用链接"""
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        for md_file in self.docs_root.rglob('*.md'):
            try:
                content = md_file.read_text(encoding='utf-8')
                original_content = content
                
                # 查找所有链接
                links = link_pattern.findall(content)
                
                for link_text, link_path in links:
                    # 跳过外部链接和锚点
                    if link_path.startswith(('http://', 'https://', '#')):
                        continue
                    
                    # 跳过模板变量
                    if '{{' in link_path or '}}' in link_path:
                        continue
                    
                    # 检查链接是否有效
                    target_path = (md_file.parent / link_path).resolve()
                    
                    if not target_path.exists():
                        # 尝试从映射表中查找新路径
                        new_path = self._find_new_path(link_path, md_file)
                        
                        if new_path:
                            # 替换链接
                            old_link = f'[{link_text}]({link_path})'
                            new_link = f'[{link_text}]({new_path})'
                            content = content.replace(old_link, new_link)
                            self.fixed_count['links'] += 1
                
                if content != original_content:
                    md_file.write_text(content, encoding='utf-8')
                    self.fixed_count['total_files'] += 1
                    relative_path = md_file.relative_to(self.docs_root)
                    print(f"  ✅ 修复链接: {relative_path}")
            
            except Exception as e:
                print(f"  ❌ 处理失败: {md_file.name} - {e}")
    
    def _find_new_path(self, old_path: str, current_file: Path) -> str:
        """查找新的文档路径"""
        # 1. 检查映射表
        if old_path in self.path_mappings:
            new_path = self.path_mappings[old_path]
            if new_path is None:
                return ''  # 文档已删除
            return new_path
        
        # 2. 尝试智能查找
        # 提取文件名
        filename = Path(old_path).name
        
        # 在docs目录中搜索同名文件
        for found_file in self.docs_root.rglob(filename):
            if found_file.is_file():
                # 计算相对路径
                try:
                    rel_path = os.path.relpath(found_file, current_file.parent)
                    return rel_path.replace('\\', '/')
                except:
                    pass
        
        return ''
    
    def generate_report(self):
        """生成修复报告"""
        print("=" * 80)
        print("修复完成报告")
        print("=" * 80)
        print(f"修复元数据的文档数: {self.fixed_count['metadata']}")
        print(f"修复的链接数: {self.fixed_count['links']}")
        print(f"修改的文件总数: {self.fixed_count['total_files']}")
        print()
        
        if self.fixed_count['metadata'] > 0 or self.fixed_count['links'] > 0:
            print("✅ 修复成功！建议重新运行验证脚本确认。")
        else:
            print("ℹ️  没有发现需要修复的问题。")


def main():
    """主函数"""
    script_dir = Path(__file__).parent
    docs_root = script_dir.parent / 'docs'
    
    if not docs_root.exists():
        print(f"❌ 错误: 找不到docs目录: {docs_root}")
        return 1
    
    fixer = DocsFixer(str(docs_root))
    fixer.fix_all()
    
    return 0


if __name__ == '__main__':
    exit(main())
