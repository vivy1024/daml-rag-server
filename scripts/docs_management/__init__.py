"""
文档管理工具包

提供文档结构优化所需的核心工具类：
- DirectoryManager: 目录结构管理
- DocumentMigrator: 文档迁移
- ReferenceUpdater: 引用更新
- ReadmeGenerator: README生成
"""

from .directory_manager import DirectoryManager
from .document_migrator import DocumentMigrator
from .reference_updater import ReferenceUpdater
from .readme_generator import ReadmeGenerator

__all__ = [
    'DirectoryManager',
    'DocumentMigrator',
    'ReferenceUpdater',
    'ReadmeGenerator',
]

__version__ = '1.0.0'
