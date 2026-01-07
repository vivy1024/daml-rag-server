"""
目录结构管理器

负责创建和管理模块化目录结构
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Module:
    """模块定义"""
    name: str                    # 模块名称（如"01-系统架构"）
    display_name: str            # 显示名称（如"系统架构"）
    description: str             # 模块说明
    parent: Optional[str] = None # 父模块路径
    sub_modules: List['Module'] = None  # 子模块列表
    
    def __post_init__(self):
        if self.sub_modules is None:
            self.sub_modules = []


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    missing_dirs: List[str]
    missing_readmes: List[str]
    errors: List[str]


class DirectoryManager:
    """目录结构管理器"""
    
    def __init__(self, base_path: str):
        """
        初始化目录管理器
        
        Args:
            base_path: 基础路径（如 daml-rag-server/docs）
        """
        self.base_path = Path(base_path)
        
    def create_module_structure(self, modules: List[Module]) -> None:
        """
        创建模块化目录结构
        
        Args:
            modules: 模块列表
        """
        for module in modules:
            self._create_module_dir(module)
            
    def _create_module_dir(self, module: Module, parent_path: Optional[Path] = None) -> None:
        """
        递归创建模块目录
        
        Args:
            module: 模块定义
            parent_path: 父目录路径
        """
        # 确定模块路径
        if parent_path:
            module_path = parent_path / module.name
        else:
            module_path = self.base_path / module.name
            
        # 创建目录
        module_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {module_path}")
        
        # 创建README
        self.create_module_readme(module_path, module)
        
        # 递归创建子模块
        for sub_module in module.sub_modules:
            self._create_module_dir(sub_module, module_path)
            
    def create_module_readme(self, module_path: Path, module: Module) -> None:
        """
        创建模块README文件
        
        Args:
            module_path: 模块路径
            module: 模块信息
        """
        readme_path = module_path / "README.md"
        
        # 如果README已存在，不覆盖
        if readme_path.exists():
            print(f"⚠️  README已存在，跳过: {readme_path}")
            return
            
        content = f"""# {module.display_name}

{module.description}

## 文档列表

（待补充）

## 相关链接

- [返回上级目录](../README.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-21
"""
        
        readme_path.write_text(content, encoding='utf-8')
        print(f"✅ 创建README: {readme_path}")
        
    def validate_structure(self, expected_modules: List[Module]) -> ValidationResult:
        """
        验证目录结构完整性
        
        Args:
            expected_modules: 期望的模块列表
            
        Returns:
            ValidationResult: 验证结果
        """
        missing_dirs = []
        missing_readmes = []
        errors = []
        
        def check_module(module: Module, parent_path: Optional[Path] = None):
            # 确定模块路径
            if parent_path:
                module_path = parent_path / module.name
            else:
                module_path = self.base_path / module.name
                
            # 检查目录是否存在
            if not module_path.exists():
                missing_dirs.append(str(module_path))
            elif not module_path.is_dir():
                errors.append(f"{module_path} 不是目录")
            else:
                # 检查README是否存在
                readme_path = module_path / "README.md"
                if not readme_path.exists():
                    missing_readmes.append(str(readme_path))
                    
            # 递归检查子模块
            for sub_module in module.sub_modules:
                check_module(sub_module, module_path)
                
        # 检查所有模块
        for module in expected_modules:
            check_module(module)
            
        is_valid = len(missing_dirs) == 0 and len(missing_readmes) == 0 and len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            missing_dirs=missing_dirs,
            missing_readmes=missing_readmes,
            errors=errors
        )
        
    def list_all_dirs(self) -> List[str]:
        """
        列出所有子目录
        
        Returns:
            目录路径列表
        """
        dirs = []
        for root, dirnames, _ in os.walk(self.base_path):
            for dirname in dirnames:
                dir_path = Path(root) / dirname
                dirs.append(str(dir_path.relative_to(self.base_path)))
        return sorted(dirs)
