"""
引用更新器

负责查找和更新文档间的引用链接
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Reference:
    """文档引用"""
    source_file: str      # 引用所在文件
    line_number: int      # 行号
    original_ref: str     # 原始引用
    target_file: str      # 目标文件
    ref_type: str         # 引用类型：markdown_link/relative_path


@dataclass
class BrokenReference:
    """断链引用"""
    source_file: str
    line_number: int
    reference: str
    reason: str


class ReferenceUpdater:
    """引用更新器"""
    
    def __init__(self, base_path: str):
        """
        初始化引用更新器
        
        Args:
            base_path: 基础路径（如 daml-rag-server/docs）
        """
        self.base_path = Path(base_path)
        
        # Markdown链接正则：[text](path)
        self.md_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        # 相对路径正则：../xxx/yyy.md 或 ./xxx.md
        self.rel_path_pattern = re.compile(r'(?:\.\.?/[\w\-/]+\.md)')
        
    def find_references(self, doc_path: str) -> List[Reference]:
        """
        查找文档中的所有引用
        
        Args:
            doc_path: 文档路径
            
        Returns:
            引用列表
        """
        doc_path = Path(doc_path)
        references = []
        
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️  无法读取文档 {doc_path}: {e}")
            return references
            
        for line_num, line in enumerate(lines, 1):
            # 查找Markdown链接
            for match in self.md_link_pattern.finditer(line):
                text, path = match.groups()
                # 只处理相对路径和.md文件
                if path.endswith('.md') and not path.startswith('http'):
                    references.append(Reference(
                        source_file=str(doc_path),
                        line_number=line_num,
                        original_ref=match.group(0),
                        target_file=path,
                        ref_type='markdown_link'
                    ))
                    
        return references
        
    def update_reference(self, doc_path: str, old_ref: str, new_ref: str) -> bool:
        """
        更新单个引用
        
        Args:
            doc_path: 文档路径
            old_ref: 旧引用
            new_ref: 新引用
            
        Returns:
            是否成功
        """
        doc_path = Path(doc_path)
        
        try:
            content = doc_path.read_text(encoding='utf-8')
            
            # 替换引用
            updated_content = content.replace(old_ref, new_ref)
            
            if content != updated_content:
                doc_path.write_text(updated_content, encoding='utf-8')
                print(f"✅ 更新引用: {doc_path}")
                print(f"   {old_ref} -> {new_ref}")
                return True
            else:
                print(f"⚠️  未找到引用: {old_ref} in {doc_path}")
                return False
                
        except Exception as e:
            print(f"❌ 更新失败: {e}")
            return False
            
    def batch_update(self, doc_path: str, ref_map: Dict[str, str]) -> int:
        """
        批量更新引用
        
        Args:
            doc_path: 文档路径
            ref_map: 引用映射 {旧引用: 新引用}
            
        Returns:
            更新数量
        """
        doc_path = Path(doc_path)
        
        try:
            content = doc_path.read_text(encoding='utf-8')
            original_content = content
            
            # 批量替换
            for old_ref, new_ref in ref_map.items():
                content = content.replace(old_ref, new_ref)
                
            # 如果有变化，写回文件
            if content != original_content:
                doc_path.write_text(content, encoding='utf-8')
                count = sum(1 for old_ref in ref_map if old_ref in original_content)
                print(f"✅ 批量更新 {count} 个引用: {doc_path}")
                return count
            else:
                return 0
                
        except Exception as e:
            print(f"❌ 批量更新失败: {e}")
            return 0
            
    def validate_references(self, scan_dir: str = None) -> List[BrokenReference]:
        """
        验证所有引用有效性
        
        Args:
            scan_dir: 扫描目录，默认为base_path
            
        Returns:
            断链引用列表
        """
        if scan_dir is None:
            scan_dir = self.base_path
        else:
            scan_dir = Path(scan_dir)
            
        broken_refs = []
        
        # 扫描所有.md文件
        for doc_path in scan_dir.rglob("*.md"):
            if not doc_path.is_file():
                continue
                
            references = self.find_references(str(doc_path))
            
            for ref in references:
                # 解析目标路径
                target_path = self._resolve_path(doc_path, ref.target_file)
                
                # 检查目标文件是否存在
                if not target_path.exists():
                    broken_refs.append(BrokenReference(
                        source_file=str(doc_path),
                        line_number=ref.line_number,
                        reference=ref.target_file,
                        reason=f"目标文件不存在: {target_path}"
                    ))
                    
        return broken_refs
        
    def _resolve_path(self, source_file: Path, relative_path: str) -> Path:
        """
        解析相对路径为绝对路径
        
        Args:
            source_file: 源文件路径
            relative_path: 相对路径
            
        Returns:
            绝对路径
        """
        # 从源文件所在目录开始解析
        source_dir = source_file.parent
        target_path = (source_dir / relative_path).resolve()
        return target_path
        
    def generate_ref_map(self, moves: List[Tuple[str, str]]) -> Dict[str, Dict[str, str]]:
        """
        根据文件移动生成引用映射
        
        Args:
            moves: 移动列表 [(源路径, 目标路径), ...]
            
        Returns:
            引用映射 {文档路径: {旧引用: 新引用}}
        """
        ref_map = {}
        
        # 为每个移动操作生成引用更新
        for old_path, new_path in moves:
            old_path = Path(old_path)
            new_path = Path(new_path)
            
            # 扫描所有文档，查找对该文件的引用
            for doc_path in self.base_path.rglob("*.md"):
                if not doc_path.is_file():
                    continue
                    
                references = self.find_references(str(doc_path))
                
                for ref in references:
                    # 解析引用的目标路径
                    target_path = self._resolve_path(doc_path, ref.target_file)
                    
                    # 如果引用指向被移动的文件
                    if target_path.resolve() == old_path.resolve():
                        # 计算新的相对路径
                        new_rel_path = self._calculate_relative_path(doc_path, new_path)
                        
                        # 添加到映射
                        if str(doc_path) not in ref_map:
                            ref_map[str(doc_path)] = {}
                        ref_map[str(doc_path)][ref.target_file] = new_rel_path
                        
        return ref_map
        
    def _calculate_relative_path(self, from_file: Path, to_file: Path) -> str:
        """
        计算相对路径
        
        Args:
            from_file: 源文件
            to_file: 目标文件
            
        Returns:
            相对路径字符串
        """
        try:
            rel_path = os.path.relpath(to_file, from_file.parent)
            # 统一使用正斜杠
            rel_path = rel_path.replace('\\', '/')
            return rel_path
        except Exception:
            # 如果无法计算相对路径，返回绝对路径
            return str(to_file)


import os
