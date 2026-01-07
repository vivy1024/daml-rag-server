"""
文档管理工具主入口

提供命令行接口来使用文档管理工具
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.docs_management.directory_manager import DirectoryManager, Module
from scripts.docs_management.document_migrator import DocumentMigrator, MigrationPlan, MoveOperation
from scripts.docs_management.reference_updater import ReferenceUpdater
from scripts.docs_management.readme_generator import ReadmeGenerator, Document


def create_directory_structure(base_path: str):
    """创建模块化目录结构"""
    print("=" * 60)
    print("创建模块化目录结构")
    print("=" * 60)
    
    manager = DirectoryManager(base_path)
    
    # 定义02-核心架构模块
    architecture_modules = [
        Module(
            name="02-核心架构",
            display_name="核心架构",
            description="系统架构设计文档，回答What和Why",
            sub_modules=[
                Module("01-系统架构", "系统架构", "系统总览、工作流程、技术栈选型"),
                Module("02-数据层", "数据层", "Neo4j、Qdrant、MySQL数据结构"),
                Module("03-编排层", "编排层", "DAG编排器、MCP工具架构"),
                Module("04-LLM层", "LLM层", "模型选择、Few-Shot检索、LLM模板"),
                Module("05-监控层", "监控层", "监控系统、流式输出架构"),
                Module("06-优化层", "优化层", "性能优化、缓存系统、并发控制"),
            ]
        )
    ]
    
    # 定义03-代码参考模块
    code_modules = [
        Module(
            name="03-代码参考",
            display_name="代码参考",
            description="代码实现文档，回答How-实现",
            sub_modules=[
                Module("01-工作流程步骤", "工作流程步骤", "步骤1-11的代码实现"),
                Module("02-核心组件", "核心组件", "框架核心、LLM客户端、缓存系统"),
                Module("03-MCP工具实现", "MCP工具实现", "MCP工具注册表和代码实现"),
                Module("04-DAG模板实现", "DAG模板实现", "DAG模板系统和代码实现"),
                Module("05-流式输出", "流式输出", "流式输出代码实现"),
            ]
        )
    ]
    
    # 定义04-开发指南模块
    guide_modules = [
        Module(
            name="04-开发指南",
            display_name="开发指南",
            description="使用指南文档，回答How-使用",
            sub_modules=[
                Module("01-快速上手", "快速上手", "DAG模板、MCP工具、三层检索开发指南"),
                Module("02-工具使用", "工具使用", "DAG模板选择、MCP工具使用、流式输出"),
                Module("03-配置管理", "配置管理", "LLM模板配置、响应配置、性能优化配置"),
                Module("04-最佳实践", "最佳实践", "监控、性能优化、安全性、质量保证"),
            ]
        )
    ]
    
    # 创建所有模块
    all_modules = architecture_modules + code_modules + guide_modules
    manager.create_module_structure(all_modules)
    
    print("\n✅ 目录结构创建完成！")
    

def validate_structure(base_path: str):
    """验证目录结构"""
    print("=" * 60)
    print("验证目录结构")
    print("=" * 60)
    
    manager = DirectoryManager(base_path)
    
    # 定义期望的模块（简化版，仅用于验证）
    expected_modules = [
        Module("02-核心架构", "核心架构", "架构设计", sub_modules=[
            Module("01-系统架构", "系统架构", ""),
            Module("02-数据层", "数据层", ""),
        ]),
        Module("03-代码参考", "代码参考", "代码实现", sub_modules=[
            Module("01-工作流程步骤", "工作流程步骤", ""),
        ]),
    ]
    
    result = manager.validate_structure(expected_modules)
    
    if result.is_valid:
        print("✅ 目录结构验证通过！")
    else:
        print("❌ 目录结构验证失败：")
        if result.missing_dirs:
            print("\n缺失的目录：")
            for d in result.missing_dirs:
                print(f"  - {d}")
        if result.missing_readmes:
            print("\n缺失的README：")
            for r in result.missing_readmes:
                print(f"  - {r}")
        if result.errors:
            print("\n错误：")
            for e in result.errors:
                print(f"  - {e}")
                

def analyze_documents(base_path: str):
    """分析文档分类"""
    print("=" * 60)
    print("分析文档分类")
    print("=" * 60)
    
    migrator = DocumentMigrator(base_path)
    
    # 扫描所有文档
    docs = migrator.scan_documents(base_path)
    
    print(f"\n找到 {len(docs)} 个文档\n")
    
    # 分析每个文档
    for doc in docs[:10]:  # 只显示前10个
        classification = migrator.analyze_document(doc)
        doc_name = Path(doc).name
        print(f"📄 {doc_name}")
        print(f"   分类: {classification.category}")
        print(f"   模块: {classification.module}")
        print(f"   置信度: {classification.confidence:.2f}")
        print()
        

def validate_references(base_path: str):
    """验证引用链接"""
    print("=" * 60)
    print("验证引用链接")
    print("=" * 60)
    
    updater = ReferenceUpdater(base_path)
    
    broken_refs = updater.validate_references()
    
    if not broken_refs:
        print("✅ 所有引用链接有效！")
    else:
        print(f"❌ 发现 {len(broken_refs)} 个断链：\n")
        for ref in broken_refs[:10]:  # 只显示前10个
            print(f"📄 {Path(ref.source_file).name}:{ref.line_number}")
            print(f"   引用: {ref.reference}")
            print(f"   原因: {ref.reason}")
            print()
            

def generate_readme(base_path: str, module_path: str):
    """生成README"""
    print("=" * 60)
    print(f"生成README: {module_path}")
    print("=" * 60)
    
    generator = ReadmeGenerator(base_path)
    
    full_path = Path(base_path) / module_path
    
    # 提取文档
    documents = generator.extract_documents_from_dir(full_path)
    
    print(f"\n找到 {len(documents)} 个文档")
    
    # 生成README
    readme_path = full_path / "README.md"
    generator.create_readme_if_not_exists(
        str(readme_path),
        module_path.split('/')[-1],
        "模块说明"
    )
    

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='文档管理工具')
    parser.add_argument('command', choices=[
        'create', 'validate', 'analyze', 'check-refs', 'gen-readme'
    ], help='命令')
    parser.add_argument('--base-path', default='docs', help='基础路径')
    parser.add_argument('--module', help='模块路径（用于gen-readme）')
    
    args = parser.parse_args()
    
    # 确定基础路径
    base_path = Path(__file__).parent.parent.parent / args.base_path
    
    if args.command == 'create':
        create_directory_structure(str(base_path))
    elif args.command == 'validate':
        validate_structure(str(base_path))
    elif args.command == 'analyze':
        analyze_documents(str(base_path))
    elif args.command == 'check-refs':
        validate_references(str(base_path))
    elif args.command == 'gen-readme':
        if not args.module:
            print("❌ 请指定模块路径：--module <path>")
            return
        generate_readme(str(base_path), args.module)
        

if __name__ == '__main__':
    main()
