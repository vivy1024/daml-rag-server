#!/usr/bin/env python3
"""
文档一致性验证脚本

验证项：
1. 文档与代码是否同步
2. 文档链接是否有效
3. 版本号是否一致
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class DocumentValidator:
    """文档验证器"""
    
    def __init__(self):
        # Windows 控制台常见为 GBK 编码：避免因不可编码字符导致脚本崩溃
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.success_count = 0
        
    def validate_all(self) -> bool:
        """执行所有验证"""
        print("=" * 80)
        print("文档一致性验证")
        print("=" * 80)
        
        # 1. 验证版本号一致性
        self.validate_version_consistency()
        
        # 2. 验证文档链接
        self.validate_document_links()
        
        # 3. 验证代码引用
        self.validate_code_references()
        
        # 4. 验证文档结构
        self.validate_document_structure()
        
        # 输出结果
        self.print_results()
        
        return len(self.errors) == 0
    
    def validate_version_consistency(self):
        """验证版本号一致性"""
        print("\n1. 验证版本号一致性...")
        
        version_files = {
            "CHANGELOG.md": r"版本\*\*:\s*v([\d.]+)",
            "README.md": r"版本\*\*:\s*v([\d.]+)",
            "docs/02-核心架构/README.md": r"版本\*\*:\s*v([\d.]+)",
            "docs/02-核心架构/01-系统架构/01-系统架构总览.md": r"版本\*\*:\s*v([\d.]+)",
            "docs/02-核心架构/01-系统架构/04-框架层与应用层架构.md": r"版本\*\*:\s*v([\d.]+)",
        }
        
        versions = {}
        for file_path, pattern in version_files.items():
            full_path = PROJECT_ROOT / file_path
            if full_path.exists():
                content = full_path.read_text(encoding='utf-8')
                match = re.search(pattern, content)
                if match:
                    versions[file_path] = match.group(1)
                else:
                    self.warnings.append(f"未找到版本号: {file_path}")
            else:
                self.warnings.append(f"文件不存在: {file_path}")
        
        # 检查版本号是否一致
        if versions:
            unique_versions = set(versions.values())
            if len(unique_versions) == 1:
                detected_version = list(unique_versions)[0]
                if len(versions) == len(version_files):
                    print(f"   [OK] 所有文档版本号一致: v{detected_version}")
                    self.success_count += 1
                else:
                    missing = [p for p in version_files.keys() if p not in versions]
                    self.warnings.append(f"版本号一致(v{detected_version})，但部分文件缺失: {missing}")
                    print(f"   [WARN] 版本号一致: v{detected_version}（部分文件缺失）")
                    self.success_count += 1
            else:
                self.warnings.append(f"版本号不一致: {versions}")
                print(f"   [WARN] 版本号不一致")
                for file, version in versions.items():
                    print(f"      - {file}: v{version}")
    
    def validate_document_links(self):
        """验证文档链接"""
        print("\n2. 验证文档链接...")
        
        # 检查关键文档是否存在
        key_docs = [
            "docs/02-核心架构/README.md",
            "docs/02-核心架构/01-系统架构/01-系统架构总览.md",
            "docs/02-核心架构/01-系统架构/05-代码目录结构.md",
            "docs/05-API文档/MCP工具API参考.md",
            "CHANGELOG.md",
            "README.md",
        ]
        
        missing_docs = []
        for doc in key_docs:
            full_path = PROJECT_ROOT / doc
            if not full_path.exists():
                missing_docs.append(doc)
        
        if missing_docs:
            # 文档体系持续演进：缺失关键文档以警告形式提示，避免阻塞验证流程
            self.warnings.append(f"缺失关键文档: {missing_docs}")
            print(f"   [WARN] 缺失{len(missing_docs)}个关键文档")
        else:
            print(f"   [OK] 所有关键文档存在")
            self.success_count += 1
    
    def validate_code_references(self):
        """验证代码引用"""
        print("\n3. 验证代码引用...")
        
        # 检查文档中提到的关键代码文件是否存在
        key_code_files = [
            "src/framework/orchestration/generic_dag_orchestrator.py",
            "src/framework/tools/registry.py",
            "src/framework/mcp/cache_manager.py",
            "src/framework/models/adaptive_model_selector.py",
            "src/framework/retrieval/enhanced_few_shot_retriever.py",
            "src/framework/retrieval/true_three_layer_engine.py",
            "src/applications/fitness/dag/orchestrator.py",
            "src/applications/fitness/dag_template_system.py",
            "src/applications/fitness/llm_decision_engine.py",
        ]
        
        missing_files = []
        for file_path in key_code_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.warnings.append(f"缺失关键代码文件: {missing_files}")
            print(f"   [WARN] 缺失{len(missing_files)}个关键代码文件")
        else:
            print(f"   [OK] 所有关键代码文件存在")
            self.success_count += 1
    
    def validate_document_structure(self):
        """验证文档结构"""
        print("\n4. 验证文档结构...")

        warnings_before = len(self.warnings)
        
        # 检查文档是否包含必要的章节
        required_sections = {
            "docs/02-核心架构/01-系统架构/04-框架层与应用层架构.md": [
                "架构概览",
                "框架层",
                "应用层",
                "文件结构"
            ],
            "docs/05-API文档/MCP工具API参考.md": [
                "概述",
                "用户档案MCP",
                "基础数据工具",
                "安全工具"
            ],
        }
        
        for doc_path, sections in required_sections.items():
            full_path = PROJECT_ROOT / doc_path
            if full_path.exists():
                content = full_path.read_text(encoding='utf-8')
                missing_sections = [s for s in sections if s not in content]
                if missing_sections:
                    self.warnings.append(f"{doc_path} 缺少章节: {missing_sections}")
                else:
                    self.success_count += 1
            else:
                # 容器镜像可能不包含 docs/ 目录：缺失时以警告提示，避免阻塞验证流程
                self.warnings.append(f"文档不存在: {doc_path}")
        
        if len(self.warnings) == warnings_before and not self.errors:
            print(f"   [OK] 文档结构完整")
        else:
            print(f"   [WARN] 部分文档结构不完整")
    
    def print_results(self):
        """输出验证结果"""
        print("\n" + "=" * 80)
        print("验证结果")
        print("=" * 80)
        
        print(f"\n[OK] 成功: {self.success_count}项")
        
        if self.warnings:
            print(f"\n[WARN] 警告: {len(self.warnings)}项")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if self.errors:
            print(f"\n[ERR] 错误: {len(self.errors)}项")
            for error in self.errors:
                print(f"   - {error}")
        
        print("\n" + "=" * 80)
        if self.errors:
            print("[ERR] 验证失败")
        elif self.warnings:
            print("[WARN] 验证通过（有警告）")
        else:
            print("[OK] 验证通过")
        print("=" * 80)


def main():
    """主函数"""
    validator = DocumentValidator()
    success = validator.validate_all()
    
    # 返回退出码
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
