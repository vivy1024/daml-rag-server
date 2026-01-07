# 文档管理工具包

**版本**: v1.0.0  
**创建日期**: 2025-12-21  
**状态**: ✅ 已完成

---

## 📋 概述

文档管理工具包提供了一套完整的工具来支持DAML-RAG文档结构优化项目。包含四个核心组件：

1. **DirectoryManager** - 目录结构管理
2. **DocumentMigrator** - 文档迁移
3. **ReferenceUpdater** - 引用更新
4. **ReadmeGenerator** - README生成

---

## 🚀 快速开始

### 安装依赖

工具包使用Python标准库，无需额外依赖。

### 基本使用

```bash
# 在Docker容器中运行
docker exec fitness_daml_rag python scripts/docs_management/main.py <command>

# 或在项目根目录运行
cd daml-rag-server
python scripts/docs_management/main.py <command>
```

---

## 📚 核心组件

### 1. DirectoryManager（目录管理器）

**功能**：
- 创建模块化目录结构
- 生成模块README
- 验证目录结构完整性

**使用示例**：

```python
from scripts.docs_management.directory_manager import DirectoryManager, Module

# 初始化
manager = DirectoryManager('docs')

# 定义模块
modules = [
    Module(
        name="02-核心架构",
        display_name="核心架构",
        description="系统架构设计文档",
        sub_modules=[
            Module("01-系统架构", "系统架构", "系统总览和工作流程"),
            Module("02-数据层", "数据层", "数据库结构"),
        ]
    )
]

# 创建目录结构
manager.create_module_structure(modules)

# 验证结构
result = manager.validate_structure(modules)
if result.is_valid:
    print("✅ 验证通过")
```

### 2. DocumentMigrator（文档迁移器）

**功能**：
- 分析文档分类（架构/代码/指南）
- 移动文档到正确位置
- 批量迁移文档

**使用示例**：

```python
from scripts.docs_management.document_migrator import DocumentMigrator, MigrationPlan, MoveOperation

# 初始化
migrator = DocumentMigrator('docs')

# 分析文档
classification = migrator.analyze_document('docs/02-核心架构/01-xxx.md')
print(f"分类: {classification.category}")
print(f"模块: {classification.module}")

# 移动单个文档
migrator.move_document(
    'docs/old/file.md',
    'docs/new/file.md',
    update_refs=True
)

# 批量迁移
plan = MigrationPlan(moves=[
    MoveOperation(
        source='docs/old/file1.md',
        destination='docs/new/file1.md',
        reason='重组到正确模块'
    )
])
result = migrator.batch_migrate(plan)
```

### 3. ReferenceUpdater（引用更新器）

**功能**：
- 查找文档中的引用
- 更新引用链接
- 验证引用有效性

**使用示例**：

```python
from scripts.docs_management.reference_updater import ReferenceUpdater

# 初始化
updater = ReferenceUpdater('docs')

# 查找引用
references = updater.find_references('docs/02-核心架构/01-xxx.md')
for ref in references:
    print(f"引用: {ref.target_file}")

# 更新单个引用
updater.update_reference(
    'docs/file.md',
    '../old/path.md',
    '../new/path.md'
)

# 批量更新
ref_map = {
    '../old/path1.md': '../new/path1.md',
    '../old/path2.md': '../new/path2.md',
}
updater.batch_update('docs/file.md', ref_map)

# 验证所有引用
broken_refs = updater.validate_references()
if not broken_refs:
    print("✅ 所有引用有效")
```

### 4. ReadmeGenerator（README生成器）

**功能**：
- 生成模块README
- 生成主README
- 更新README索引

**使用示例**：

```python
from scripts.docs_management.readme_generator import ReadmeGenerator, Document

# 初始化
generator = ReadmeGenerator('docs')

# 生成模块README
documents = [
    Document(
        path='docs/module/file1.md',
        title='文档1',
        description='文档1说明'
    )
]

content = generator.generate_module_readme(
    module_name='系统架构',
    module_description='系统架构设计文档',
    documents=documents
)

# 更新README索引
generator.update_readme_index(
    'docs/module/README.md',
    documents
)

# 从目录提取文档并创建README
generator.create_readme_if_not_exists(
    'docs/module/README.md',
    '系统架构',
    '系统架构设计文档'
)
```

---

## 🔧 命令行工具

### 创建目录结构

```bash
docker exec fitness_daml_rag python scripts/docs_management/main.py create
```

创建完整的模块化目录结构，包括：
- 02-核心架构（6个子模块）
- 03-代码参考（5个子模块）
- 04-开发指南（4个子模块）

### 验证目录结构

```bash
docker exec fitness_daml_rag python scripts/docs_management/main.py validate
```

验证目录结构是否完整，检查：
- 所有必需目录是否存在
- 每个目录是否有README.md

### 分析文档分类

```bash
docker exec fitness_daml_rag python scripts/docs_management/main.py analyze
```

分析现有文档的分类，输出：
- 文档应属于的分类（架构/代码/指南）
- 文档应属于的模块
- 分类置信度

### 验证引用链接

```bash
docker exec fitness_daml_rag python scripts/docs_management/main.py check-refs
```

验证所有文档中的引用链接是否有效，报告断链。

### 生成README

```bash
docker exec fitness_daml_rag python scripts/docs_management/main.py gen-readme --module "02-核心架构/01-系统架构"
```

为指定模块生成README文件。

---

## 📖 工作流程示例

### 完整的文档重组流程

```python
from scripts.docs_management import *

# 1. 创建目录结构
manager = DirectoryManager('docs')
modules = [...]  # 定义模块
manager.create_module_structure(modules)

# 2. 分析现有文档
migrator = DocumentMigrator('docs')
docs = migrator.scan_documents('docs')
for doc in docs:
    classification = migrator.analyze_document(doc)
    # 根据分类决定迁移目标

# 3. 执行迁移
plan = MigrationPlan(moves=[...])
result = migrator.batch_migrate(plan)

# 4. 更新引用
updater = ReferenceUpdater('docs')
moves = [(old, new) for old, new in ...]
ref_map = updater.generate_ref_map(moves)
for doc_path, refs in ref_map.items():
    updater.batch_update(doc_path, refs)

# 5. 生成README
generator = ReadmeGenerator('docs')
for module_path in [...]:
    generator.create_readme_if_not_exists(
        f'docs/{module_path}/README.md',
        module_name,
        module_description
    )

# 6. 验证
broken_refs = updater.validate_references()
validation = manager.validate_structure(modules)
```

---

## ⚠️ 注意事项

1. **备份数据**：在执行大规模迁移前，务必备份文档
2. **Docker环境**：所有操作应在Docker容器内执行
3. **Git提交**：完成迁移后及时提交到Git
4. **引用更新**：移动文档后务必更新引用链接
5. **验证检查**：每个阶段完成后都要验证

---

## 🐛 故障排除

### 问题1：找不到模块

```
ModuleNotFoundError: No module named 'scripts.docs_management'
```

**解决方案**：确保在项目根目录运行，或使用Docker命令。

### 问题2：编码错误

```
UnicodeDecodeError: 'utf-8' codec can't decode
```

**解决方案**：确保所有文档使用UTF-8编码。

### 问题3：权限错误

```
PermissionError: [Errno 13] Permission denied
```

**解决方案**：在Docker容器内运行，或检查文件权限。

---

## 📝 开发指南

### 扩展工具

要添加新功能，可以：

1. 在对应的类中添加新方法
2. 更新`__init__.py`导出新功能
3. 在`main.py`中添加命令行接口
4. 更新本README文档

### 测试

```bash
# 运行单元测试（待实现）
docker exec fitness_daml_rag pytest scripts/docs_management/tests/
```

---

## 🔗 相关文档

- [需求文档](../../.kiro/specs/daml-rag-docs-optimization/requirements.md)
- [设计文档](../../.kiro/specs/daml-rag-docs-optimization/design.md)
- [任务列表](../../.kiro/specs/daml-rag-docs-optimization/tasks.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-21
