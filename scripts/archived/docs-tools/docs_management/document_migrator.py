"""
文档迁移器

负责分析文档分类并执行迁移操作
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class DocumentClassification:
    """文档分类结果"""
    category: str  # 分类：architecture/code/guide
    module: str    # 所属模块
    confidence: float  # 置信度


@dataclass
class MigrationPlan:
    """迁移计划"""
    moves: List['MoveOperation']
    
    
@dataclass
class MoveOperation:
    """移动操作"""
    source: str           # 源路径
    destination: str      # 目标路径
    reason: str          # 移动原因
    update_references: bool = True  # 是否更新引用


@dataclass
class MigrationResult:
    """迁移结果"""
    success: bool
    moved_files: List[str]
    failed_files: List[str]
    errors: List[str]


class DocumentMigrator:
    """文档迁移器"""
    
    def __init__(self, base_path: str):
        """
        初始化文档迁移器
        
        Args:
            base_path: 基础路径（如 daml-rag-server/docs）
        """
        self.base_path = Path(base_path)
        
        # 分类关键词
        self.architecture_keywords = [
            '架构', '设计', '理念', 'why', '为什么', '总览',
            '演进', '选型', '技术栈', '工作流程'
        ]
        
        self.code_keywords = [
            '实现', '代码', '步骤', '组件', '执行器',
            '注册表', '模板系统', '核心实现'
        ]
        
        self.guide_keywords = [
            '指南', '使用', '配置', '开发', '最佳实践',
            '完整指南', '管理器', '调用'
        ]
        
    def analyze_document(self, doc_path: str) -> DocumentClassification:
        """
        分析文档应属于哪个分类
        
        Args:
            doc_path: 文档路径
            
        Returns:
            DocumentClassification: 分类结果
        """
        doc_path = Path(doc_path)
        
        # 读取文档内容
        try:
            content = doc_path.read_text(encoding='utf-8')
            title = doc_path.stem
        except Exception as e:
            print(f"⚠️  无法读取文档 {doc_path}: {e}")
            return DocumentClassification(
                category='unknown',
                module='unknown',
                confidence=0.0
            )
            
        # 计算关键词匹配分数
        arch_score = sum(1 for kw in self.architecture_keywords if kw in title or kw in content[:1000])
        code_score = sum(1 for kw in self.code_keywords if kw in title or kw in content[:1000])
        guide_score = sum(1 for kw in self.guide_keywords if kw in title or kw in content[:1000])
        
        # 确定分类
        scores = {
            'architecture': arch_score,
            'code': code_score,
            'guide': guide_score
        }
        
        category = max(scores, key=scores.get)
        max_score = scores[category]
        total_score = sum(scores.values())
        
        confidence = max_score / total_score if total_score > 0 else 0.0
        
        # 根据文件名推断模块
        module = self._infer_module(title, content)
        
        return DocumentClassification(
            category=category,
            module=module,
            confidence=confidence
        )
        
    def _infer_module(self, title: str, content: str) -> str:
        """
        推断文档所属模块
        
        Args:
            title: 文档标题
            content: 文档内容
            
        Returns:
            模块名称
        """
        # 模块关键词映射
        module_keywords = {
            '系统架构': ['系统架构', '工作流程', '技术栈', '框架层'],
            '数据层': ['数据库', 'Neo4j', 'Qdrant', 'MySQL', '用户档案MCP'],
            '编排层': ['编排器', 'DAG', 'MCP工具', 'MCP架构'],
            '监控层': ['监控', '流式输出', 'SSE', '可观测性'],
            '优化层': ['性能优化', '缓存', '并发'],
            'LLM层': ['模型选择', 'Few-Shot', 'LLM模板', 'LLM响应'],
        }
        
        text = title + content[:500]
        
        for module, keywords in module_keywords.items():
            if any(kw in text for kw in keywords):
                return module
                
        return 'unknown'
        
    def move_document(self, src: str, dest: str, update_refs: bool = True) -> bool:
        """
        移动文档并可选更新引用
        
        Args:
            src: 源路径
            dest: 目标路径
            update_refs: 是否更新引用
            
        Returns:
            是否成功
        """
        src_path = Path(src)
        dest_path = Path(dest)
        
        # 检查源文件是否存在
        if not src_path.exists():
            print(f"❌ 源文件不存在: {src_path}")
            return False
            
        # 创建目标目录
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 移动文件
            shutil.move(str(src_path), str(dest_path))
            print(f"✅ 移动文档: {src_path} -> {dest_path}")
            return True
        except Exception as e:
            print(f"❌ 移动失败: {e}")
            return False
            
    def batch_migrate(self, migration_plan: MigrationPlan) -> MigrationResult:
        """
        批量迁移文档
        
        Args:
            migration_plan: 迁移计划
            
        Returns:
            MigrationResult: 迁移结果
        """
        moved_files = []
        failed_files = []
        errors = []
        
        for operation in migration_plan.moves:
            success = self.move_document(
                operation.source,
                operation.destination,
                operation.update_references
            )
            
            if success:
                moved_files.append(operation.source)
            else:
                failed_files.append(operation.source)
                errors.append(f"Failed to move {operation.source}")
                
        return MigrationResult(
            success=len(failed_files) == 0,
            moved_files=moved_files,
            failed_files=failed_files,
            errors=errors
        )
        
    def scan_documents(self, directory: str, pattern: str = "*.md") -> List[str]:
        """
        扫描目录下的所有文档
        
        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            
        Returns:
            文档路径列表
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
            
        docs = []
        for doc_path in dir_path.rglob(pattern):
            if doc_path.is_file():
                docs.append(str(doc_path))
                
        return sorted(docs)
