#!/usr/bin/env python3
"""
框架代码同步脚本

功能：
1. 备份旧代码（可选）
2. 删除旧代码
3. 复制新代码
4. 验证文件完整性

使用方法：
    python scripts/sync_framework_to_github.py [--no-backup]
"""

import os
import sys
import shutil
import filecmp
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'


class SyncResult:
    """同步结果"""
    def __init__(self, success: bool, message: str, details: Dict = None):
        self.success = success
        self.message = message
        self.details = details or {}


class ValidationResult:
    """验证结果"""
    def __init__(self, success: bool, message: str, file_count: int = 0):
        self.success = success
        self.message = message
        self.file_count = file_count


class GitHubSyncManager:
    """GitHub同步管理器"""
    
    def __init__(self, backup: bool = True):
        # 获取项目根目录
        self.project_root = Path(__file__).parent.parent.parent
        
        # 源目录和目标目录
        self.source_dir = self.project_root / "daml-rag-server" / "src" / "framework"
        self.target_dir = self.project_root / "daml-rag-framework" / "framework"
        
        self.backup_enabled = backup
        self.backup_dir = None
        
    def print_info(self, message: str):
        """打印信息"""
        print(f"{Colors.BLUE}[INFO]{Colors.END} {message}")
    
    def print_success(self, message: str):
        """打印成功信息"""
        print(f"{Colors.GREEN}[SUCCESS]{Colors.END} {message}")
    
    def print_warning(self, message: str):
        """打印警告信息"""
        print(f"{Colors.YELLOW}[WARNING]{Colors.END} {message}")
    
    def print_error(self, message: str):
        """打印错误信息"""
        print(f"{Colors.RED}[ERROR]{Colors.END} {message}")
    
    def _get_all_files(self, directory: Path, relative_to: Path = None) -> List[str]:
        """获取目录下所有文件（相对路径）"""
        if relative_to is None:
            relative_to = directory
        
        files = []
        for item in directory.rglob("*"):
            if item.is_file():
                # 排除 __pycache__ 和 .pyc 文件
                if "__pycache__" not in str(item) and not str(item).endswith(".pyc"):
                    relative_path = item.relative_to(relative_to)
                    files.append(str(relative_path))
        
        return sorted(files)
    
    def backup_old_code(self) -> bool:
        """备份旧代码"""
        if not self.backup_enabled:
            self.print_info("跳过备份（--no-backup）")
            return True
        
        if not self.target_dir.exists():
            self.print_info("目标目录不存在，无需备份")
            return True
        
        # 创建备份目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.target_dir.parent / f"framework.backup_{timestamp}"
        
        try:
            self.print_info(f"正在备份旧代码到: {self.backup_dir}")
            shutil.copytree(self.target_dir, self.backup_dir)
            self.print_success(f"备份完成: {self.backup_dir}")
            return True
        except Exception as e:
            self.print_error(f"备份失败: {e}")
            return False
    
    def delete_old_code(self) -> bool:
        """删除旧代码"""
        if not self.target_dir.exists():
            self.print_info("目标目录不存在，无需删除")
            return True
        
        try:
            self.print_info(f"正在删除旧代码: {self.target_dir}")
            shutil.rmtree(self.target_dir)
            self.print_success("旧代码删除完成")
            return True
        except Exception as e:
            self.print_error(f"删除失败: {e}")
            return False
    
    def copy_new_code(self) -> bool:
        """复制新代码"""
        if not self.source_dir.exists():
            self.print_error(f"源目录不存在: {self.source_dir}")
            return False
        
        try:
            self.print_info(f"正在复制新代码: {self.source_dir} -> {self.target_dir}")
            
            # 复制目录，排除 __pycache__
            shutil.copytree(
                self.source_dir,
                self.target_dir,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
            )
            
            self.print_success("新代码复制完成")
            return True
        except Exception as e:
            self.print_error(f"复制失败: {e}")
            return False
    
    def validate_sync(self) -> ValidationResult:
        """验证同步结果"""
        self.print_info("正在验证文件完整性...")
        
        # 获取源文件和目标文件列表
        source_files = self._get_all_files(self.source_dir, self.source_dir)
        target_files = self._get_all_files(self.target_dir, self.target_dir)
        
        # 检查文件数量
        if len(source_files) != len(target_files):
            return ValidationResult(
                success=False,
                message=f"文件数量不一致: 源={len(source_files)}, 目标={len(target_files)}",
                file_count=len(target_files)
            )
        
        # 检查文件列表是否一致
        missing_files = set(source_files) - set(target_files)
        extra_files = set(target_files) - set(source_files)
        
        if missing_files:
            return ValidationResult(
                success=False,
                message=f"缺少文件: {', '.join(list(missing_files)[:5])}...",
                file_count=len(target_files)
            )
        
        if extra_files:
            return ValidationResult(
                success=False,
                message=f"多余文件: {', '.join(list(extra_files)[:5])}...",
                file_count=len(target_files)
            )
        
        # 检查文件内容是否一致
        mismatched_files = []
        for file in source_files:
            source_path = self.source_dir / file
            target_path = self.target_dir / file
            
            if not filecmp.cmp(source_path, target_path, shallow=False):
                mismatched_files.append(file)
        
        if mismatched_files:
            return ValidationResult(
                success=False,
                message=f"文件内容不一致: {', '.join(mismatched_files[:5])}...",
                file_count=len(target_files)
            )
        
        return ValidationResult(
            success=True,
            message="所有文件验证通过",
            file_count=len(target_files)
        )
    
    def sync_framework_code(self) -> SyncResult:
        """同步框架代码到GitHub项目"""
        self.print_info("=" * 60)
        self.print_info("开始同步框架代码到GitHub项目")
        self.print_info("=" * 60)
        
        # 步骤1: 备份旧代码
        if not self.backup_old_code():
            return SyncResult(
                success=False,
                message="备份失败",
                details={"step": "backup"}
            )
        
        # 步骤2: 删除旧代码
        if not self.delete_old_code():
            return SyncResult(
                success=False,
                message="删除旧代码失败",
                details={"step": "delete"}
            )
        
        # 步骤3: 复制新代码
        if not self.copy_new_code():
            return SyncResult(
                success=False,
                message="复制新代码失败",
                details={"step": "copy"}
            )
        
        # 步骤4: 验证文件完整性
        validation = self.validate_sync()
        
        if not validation.success:
            self.print_error(f"验证失败: {validation.message}")
            return SyncResult(
                success=False,
                message=validation.message,
                details={
                    "step": "validation",
                    "file_count": validation.file_count
                }
            )
        
        # 成功
        self.print_success("=" * 60)
        self.print_success("框架代码同步完成！")
        self.print_success(f"同步文件数: {validation.file_count}")
        if self.backup_dir:
            self.print_success(f"备份位置: {self.backup_dir}")
        self.print_success("=" * 60)
        
        return SyncResult(
            success=True,
            message="框架代码同步完成",
            details={
                "file_count": validation.file_count,
                "backup_dir": str(self.backup_dir) if self.backup_dir else None
            }
        )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="同步框架代码到GitHub项目")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="不备份旧代码"
    )
    
    args = parser.parse_args()
    
    # 创建同步管理器
    sync_manager = GitHubSyncManager(backup=not args.no_backup)
    
    # 执行同步
    result = sync_manager.sync_framework_code()
    
    # 返回退出码
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
