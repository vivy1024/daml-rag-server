# 数据导入向量化 📥

**任务目标**: 营养数据、食物数据的导入和向量化

**脚本数量**: 6个

## 📋 核心脚本

### 导入脚本
- `batch_import_nutrition.py` - 批量导入营养数据
- `optimized_nutrition_import.py` - 优化营养导入

### 向量化脚本
- `vectorize_food_nutrition.py` - 向量化食物营养
- `vectorize_nutrition_knowledge.py` - 向量化营养知识
- `docker_vectorize_foods.py` - Docker环境食物向量化

### 文档
- `README.md` - 数据导入说明文档

## 🚀 运行方式

```bash
# 批量导入营养数据
docker exec fitness_daml_rag python scripts/数据导入向量化/batch_import_nutrition.py

# Docker环境食物向量化
docker exec fitness_daml_rag python scripts/数据导入向量化/docker_vectorize_foods.py
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
