# Neo4j数据库操作 🗄️

**任务目标**: Neo4j数据库的查询、验证、修复、补充

**脚本数量**: 17个

## 📋 核心脚本

### 验证脚本
- `verify_neo4j_structure.py` - 验证数据库结构
- `verify_neo4j_correct.py` - 验证数据正确性
- `check_all_relationships.py` - 检查所有关系
- `check_all_exercise_fields.py` - 检查所有字段

### 修复脚本
- `fix_neo4j_relationships.py` - 修复关系
- `create_contraindicated_relations_enhanced.py` - 创建禁忌症关系
- `create_missing_relationships.py` - 创建缺失关系
- `restore_muscle_nodes.py` - 恢复肌肉节点

### 查询脚本
- `query_exercise_data.py` - 查询动作数据
- `query_exercise_relationships.py` - 查询动作关系
- `find_exercises_with_targets.py` - 查找有目标的动作

### 导入脚本
- `import_exercises_to_neo4j.py` - 导入动作到Neo4j

### 分析脚本
- `analyze_injury_data.py` - 分析损伤数据
- `analyze_relationships.py` - 分析关系
- `check_contraindicated_for.py` - 检查禁忌症关系
- `check_neo4j_fields.py` - 检查Neo4j字段
- `get_valid_exercise_ids.py` - 获取有效动作ID

## 🚀 运行方式

```bash
# 验证数据库结构
docker exec fitness_daml_rag python scripts/Neo4j数据库操作/verify_neo4j_structure.py

# 检查所有关系
docker exec fitness_daml_rag python scripts/Neo4j数据库操作/check_all_relationships.py

# 导入动作数据
docker exec fitness_daml_rag python scripts/Neo4j数据库操作/import_exercises_to_neo4j.py
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
