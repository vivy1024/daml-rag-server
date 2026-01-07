# 实用工具脚本 🛠️

**任务目标**: 保留的实用工具脚本，提供文档管理、问题识别和框架同步功能

**脚本数量**: 3个

## 📋 核心脚本

### 文档管理工具
- `document_scanner.py` - 文档扫描器
  - 扫描docs目录并生成文档清单
  - 检查文档编号、版本、状态等信息
  - 识别临时文件和编号冲突

### 问题识别工具
- `problem_identifier.py` - 问题文档识别器
  - 识别临时文件、编号冲突、过时内容
  - 检查放错位置的文档
  - 生成问题报告

### 框架同步工具
- `sync_framework_to_github.py` - GitHub框架代码同步
  - 将框架层代码同步到GitHub开源项目
  - 支持备份旧代码
  - 验证文件完整性

## 🚀 运行方式

```bash
# 扫描文档并生成清单
docker exec fitness_daml_rag python scripts/document_scanner.py

# 识别问题文档
docker exec fitness_daml_rag python scripts/problem_identifier.py

# 同步框架代码到GitHub
docker exec fitness_daml_rag python scripts/sync_framework_to_github.py
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
