#!/usr/bin/env python3
"""
文档扫描器 - 扫描docs目录并生成文档清单
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DocumentInfo:
    """文档信息"""
    path: str
    filename: str
    number: Optional[int]
    title: str
    category: str
    version: Optional[str]
    created_date: Optional[str]
    updated_date: Optional[str]
    status: Optional[str]
    is_temporary: bool
    is_numbered: bool
    has_version_info: bool


class DocumentScanner:
    """文档扫描器"""
    
    def __init__(self, docs_root: str):
        self.docs_root = Path(docs_root)
        self.documents: List[DocumentInfo] = []
        
    def scan(self) -> List[DocumentInfo]:
        """扫描所有文档"""
        print(f"📂 扫描目录: {self.docs_root}")
        
        # 递归扫描所有.md文件
        for md_file in self.docs_root.rglob("*.md"):
            if md_file.name == "README.md":
                continue  # 跳过README文件
                
            doc_info = self._extract_document_info(md_file)
            self.documents.append(doc_info)
            
        print(f"✅ 扫描完成，共找到 {len(self.documents)} 个文档")
        return self.documents
    
    def _extract_document_info(self, file_path: Path) -> DocumentInfo:
        """提取文档信息"""
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️  读取文件失败: {file_path} - {e}")
            content = ""
        
        # 提取文件名和编号
        filename = file_path.name
        number = self._extract_number(filename)
        
        # 提取标题
        title = self._extract_title(content, filename)
        
        # 确定分类
        category = self._determine_category(file_path)
        
        # 提取版本信息
        version = self._extract_version(content)
        created_date = self._extract_created_date(content)
        updated_date = self._extract_updated_date(content)
        status = self._extract_status(content)
        
        # 判断是否临时文件
        is_temporary = self._is_temporary_file(filename, content)
        
        # 判断是否有编号
        is_numbered = number is not None
        
        # 判断是否有版本信息
        has_version_info = version is not None or created_date is not None
        
        return DocumentInfo(
            path=str(file_path.relative_to(self.docs_root.parent)),
            filename=filename,
            number=number,
            title=title,
            category=category,
            version=version,
            created_date=created_date,
            updated_date=updated_date,
            status=status,
            is_temporary=is_temporary,
            is_numbered=is_numbered,
            has_version_info=has_version_info
        )
    
    def _extract_number(self, filename: str) -> Optional[int]:
        """提取文档编号"""
        match = re.match(r'^(\d+)-', filename)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_title(self, content: str, filename: str) -> str:
        """提取文档标题"""
        # 尝试从内容中提取第一个一级标题
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # 如果没有标题，使用文件名（去掉编号和.md）
        title = re.sub(r'^\d+-', '', filename)
        title = title.replace('.md', '')
        return title
    
    def _determine_category(self, file_path: Path) -> str:
        """确定文档分类"""
        parts = file_path.parts
        for part in parts:
            if part.startswith('01-'):
                return '快速开始'
            elif part.startswith('02-'):
                return '核心架构'
            elif part.startswith('03-'):
                return '代码参考'
            elif part.startswith('04-'):
                return '开发指南'
            elif part.startswith('05-'):
                return 'API文档'
            elif part.startswith('06-'):
                return '部署运维'
        return '未分类'
    
    def _extract_version(self, content: str) -> Optional[str]:
        """提取版本号"""
        patterns = [
            r'\*\*版本\*\*:\s*v?([\d.]+)',
            r'版本:\s*v?([\d.]+)',
            r'Version:\s*v?([\d.]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return f"v{match.group(1)}"
        return None
    
    def _extract_created_date(self, content: str) -> Optional[str]:
        """提取创建日期"""
        patterns = [
            r'\*\*创建日期\*\*:\s*(\d{4}-\d{2}-\d{2})',
            r'创建日期:\s*(\d{4}-\d{2}-\d{2})',
            r'Created:\s*(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_updated_date(self, content: str) -> Optional[str]:
        """提取更新日期"""
        patterns = [
            r'\*\*更新日期\*\*:\s*(\d{4}-\d{2}-\d{2})',
            r'更新日期:\s*(\d{4}-\d{2}-\d{2})',
            r'Updated:\s*(\d{4}-\d{2}-\d{2})',
            r'最后更新:\s*(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_status(self, content: str) -> Optional[str]:
        """提取状态标记"""
        patterns = [
            r'\*\*状态\*\*:\s*([✅📋🚧🎉🔄📦].+?)(?:\n|$)',
            r'状态:\s*([✅📋🚧🎉🔄📦].+?)(?:\n|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
        return None
    
    def _is_temporary_file(self, filename: str, content: str) -> bool:
        """判断是否临时文件"""
        # 无编号的文件可能是临时文件
        if not re.match(r'^\d+', filename):
            # 但有些特殊文件不是临时文件
            special_files = [
                'README.md',
                'CHANGELOG.md',
                'API_USAGE.md',
                'Docker部署.md',
            ]
            if filename in special_files:
                return False
            return True
        
        # 检查是否包含临时性关键词
        temp_keywords = [
            '工作流程日志',
            '计划生成结果',
            '完成报告',
            '实施总结',
            '修复说明',
        ]
        for keyword in temp_keywords:
            if keyword in filename or keyword in content[:500]:
                return True
        
        return False
    
    def save_to_json(self, output_file: str):
        """保存到JSON文件"""
        data = {
            'scan_time': datetime.now().isoformat(),
            'total_documents': len(self.documents),
            'documents': [asdict(doc) for doc in self.documents]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 文档清单已保存到: {output_file}")
    
    def print_summary(self):
        """打印统计摘要"""
        print("\n" + "="*60)
        print("📊 文档扫描统计")
        print("="*60)
        
        # 按分类统计
        category_counts = {}
        for doc in self.documents:
            category_counts[doc.category] = category_counts.get(doc.category, 0) + 1
        
        print("\n📁 按分类统计:")
        for category, count in sorted(category_counts.items()):
            print(f"  {category}: {count}个")
        
        # 编号统计
        numbered = sum(1 for doc in self.documents if doc.is_numbered)
        unnumbered = len(self.documents) - numbered
        print(f"\n🔢 编号统计:")
        print(f"  有编号: {numbered}个")
        print(f"  无编号: {unnumbered}个")
        
        # 版本信息统计
        with_version = sum(1 for doc in self.documents if doc.has_version_info)
        without_version = len(self.documents) - with_version
        print(f"\n📌 版本信息统计:")
        print(f"  有版本信息: {with_version}个")
        print(f"  无版本信息: {without_version}个")
        
        # 临时文件统计
        temp_files = sum(1 for doc in self.documents if doc.is_temporary)
        print(f"\n⚠️  临时文件: {temp_files}个")
        
        if temp_files > 0:
            print("\n临时文件列表:")
            for doc in self.documents:
                if doc.is_temporary:
                    print(f"  - {doc.filename}")
        
        print("\n" + "="*60)


def main():
    """主函数"""
    # 确定docs目录路径
    script_dir = Path(__file__).parent
    docs_root = script_dir.parent / "docs"
    
    if not docs_root.exists():
        print(f"❌ 文档目录不存在: {docs_root}")
        return
    
    # 创建扫描器并扫描
    scanner = DocumentScanner(str(docs_root))
    scanner.scan()
    
    # 保存结果
    output_file = script_dir / "document_inventory.json"
    scanner.save_to_json(str(output_file))
    
    # 打印统计
    scanner.print_summary()


if __name__ == "__main__":
    main()
