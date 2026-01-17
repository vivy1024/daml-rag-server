# Neo4j生产环境脚本说明

**版本**: v1.0.0
**更新日期**: 2026-01-17
**维护者**: 薛小川

---

## 📋 当前保留的有效脚本

### 1. 数据迁移

#### `migrate_neo4j_fixed_v2.py` ⭐ 主要迁移脚本
**用途**: 将本地Neo4j数据完整迁移到生产环境

**功能特性**:
- 使用正确的节点唯一键（Exercise.id、Muscle.name_en等）
- 支持复合键（TrainingParams使用goal+level）
- 使用Neo4j 5.x新API（elementId替代id）
- 100%迁移成功率（4250节点 + 61854关系）

**使用方法**:
```bash
# 强制清空生产环境并迁移
docker exec fitness_daml_rag python scripts/migrate_neo4j_fixed_v2.py --force
```

**注意事项**:
- 使用`--force`参数会清空生产环境现有数据
- 迁移前会显示初始状态和最终状态对比
- 自动建立ID映射确保关系正确

---

### 2. 数据清空

#### `clear_neo4j_production_batch.py` ⭐ 推荐使用
**用途**: 分批清空生产环境Neo4j数据（避免内存溢出）

**功能特性**:
- 每批删除1000个节点
- 自动处理关系（DETACH DELETE）
- 避免内存溢出错误（生产环境限制358.4 MiB）
- 显示详细进度

**使用方法**:
```bash
docker exec fitness_daml_rag python scripts/clear_neo4j_production_batch.py
```

**适用场景**:
- 生产环境有大量数据需要清空
- 遇到内存溢出错误时
- 需要重新迁移数据前

---

### 3. 诊断工具

#### `diagnose_neo4j_migration.py`
**用途**: 诊断Neo4j迁移问题，检查节点唯一键

**功能特性**:
- 检查所有节点类型的唯一键配置
- 识别缺少唯一键的节点
- 显示有效/无效节点统计
- 提供修复建议

**使用方法**:
```bash
docker exec fitness_daml_rag python scripts/diagnose_neo4j_migration.py
```

**输出示例**:
```
⚠️  Exercise (唯一键: exercise_id)
  总数: 1790
  有效: 0
  无效: 1790
  
✅ Food: 1880 个（全部有效）
```

---

### 4. 数据验证

#### `verify_neo4j_production.py`
**用途**: 验证本地和生产环境Neo4j数据一致性

**功能特性**:
- 对比本地和生产环境节点/关系数量
- 按节点类型和关系类型统计
- 验证核心数据（Exercise、Muscle等）
- 显示示例节点

**使用方法**:
```bash
docker exec fitness_daml_rag python scripts/verify_neo4j_production.py
```

**验证内容**:
- 节点类型统计（23种类型）
- 关系类型统计（20种类型）
- 核心数据验证（Exercise: 1790, Muscle: 40）

---

## 🗂️ 已归档的脚本

以下脚本已移动到 `archived/neo4j_migration_old/`：

### 过时的迁移脚本
- `migrate_neo4j_complete.py` - 早期版本
- `migrate_neo4j_final.py` - 早期版本
- `migrate_neo4j_fixed.py` - v1版本（已被v2替代）
- `migrate_neo4j_production_fixed.py` - 临时版本
- `migrate_neo4j_relations.py` - 只迁移关系
- `migrate_neo4j_remaining.py` - 增量迁移
- `migrate_neo4j_to_production.py` - 初始版本

### 过时的清空脚本
- `clear_neo4j_production.py` - 需要交互确认
- `clear_neo4j_production_force.py` - 会遇到内存溢出

### 过时的诊断脚本
- `diagnose_neo4j_diff.py` - 早期诊断工具
- `check_neo4j_diff.py` - 重复功能

---

## 📊 节点唯一键配置

当前使用的唯一键配置（在`migrate_neo4j_fixed_v2.py`中）：

```python
NODE_UNIQUE_KEYS = {
    'Exercise': 'id',              # 不是exercise_id
    'Muscle': 'name_en',           # 不是muscle_id
    'Equipment': 'name',           # 不是equipment_id
    'Food': 'food_code',
    'Nutrient': 'name',
    'StrengthStandard': 'id',      # 不是name
    'ACSMStandard': 'id',
    'NSCAStandard': 'id',
    'TrainingParams': ['goal', 'level'],  # 复合键
    'TrainingGoal': 'name',
    # ... 其他节点类型
}
```

---

## 🔧 常见问题

### Q1: 迁移失败，关系成功率低于100%
**A**: 运行诊断脚本检查唯一键配置：
```bash
docker exec fitness_daml_rag python scripts/diagnose_neo4j_migration.py
```

### Q2: 清空生产环境时遇到内存溢出
**A**: 使用分批清空脚本：
```bash
docker exec fitness_daml_rag python scripts/clear_neo4j_production_batch.py
```

### Q3: 如何验证迁移是否成功
**A**: 运行验证脚本对比数据：
```bash
docker exec fitness_daml_rag python scripts/verify_neo4j_production.py
```

### Q4: 生产环境连接信息
```
URI: bolt://182.92.78.183:32372
用户: neo4j
密码: build_body_2024
Browser: https://neo4j.yuzhen-fitness.cn
```

---

## 📝 迁移历史

### v1.0.0 (2026-01-17)
- ✅ 完成生产环境数据迁移
- ✅ 节点：4250/4250 (100%)
- ✅ 关系：61854/61854 (100%)
- ✅ 解决内存溢出问题
- ✅ 修正节点唯一键配置

---

**相关文档**:
- `daml-rag-server/CHANGELOG.md` (v9.44.0)
- `CHANGELOG.md` (v3.27.0)
- `.kiro/steering/zeabur-production.md`
