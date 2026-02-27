# 实用工具测试 🛠️

**任务目标**: 调试和临时测试工具

**测试文件数量**: 4个

## 📋 测试文件

### 调试工具
- `debug_greeting_api.py` - 问候API调试
- `test_layer2_fix.py` - Layer2修复测试
- `test_layer2_id_extraction.py` - Layer2 ID提取测试

### 数据导入测试
- `test_qdrant_importer.py` - Qdrant导入器测试

## 🚀 运行方式

```bash
# 运行特定调试测试
docker exec fitness_daml_rag pytest tests/实用工具测试/debug_greeting_api.py -v

# 运行Qdrant导入测试
docker exec fitness_daml_rag pytest tests/实用工具测试/test_qdrant_importer.py -v
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
