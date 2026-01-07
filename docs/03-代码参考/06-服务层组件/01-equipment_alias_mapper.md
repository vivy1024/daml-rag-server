# equipment_alias_mapper.py - 器械别名映射器

**文件路径**：`src/applications/fitness/services/equipment_alias_mapper.py`
**状态**：✅ 已完成

---

## 📋 功能概述

器械别名映射器负责统一管理健身器械名称的多种表达方式，实现用户输入的智能识别和标准化转换。这是确保系统准确理解用户意图的关键组件。

---

## 🎯 核心功能

### 1. 别名识别
- 支持中英文别名识别
- 模糊匹配算法
- 智能纠错机制

### 2. 标准化转换
- 统一器械标准名称
- 分类体系映射
- 向后兼容处理

### 3. 扩展支持
- 动态添加新别名
- 上下文相关映射
- 使用频率统计

---

## 📊 数据结构

### 器械分类体系

| 分类 | 标准名称 | 常见别名 |
|------|----------|----------|
| 胸部训练 | 杠铃卧推 | 卧推、杠铃推胸、Chest Press |
| 背部训练 | 引体向上 | 拉单杠、Pull-up、Chin-up |
| 肩部训练 | 哑铃推举 | 肩推、Shoulder Press、Overhead Press |
| 腿部训练 | 深蹲 | 蹲举、Squat、Back Squat |

---

## 🔧 使用示例

```python
# 初始化映射器
mapper = EquipmentAliasMapper()

# 标准化器械名称
standard_name = mapper.map_to_standard("卧推")
# 返回: "杠铃卧推"

# 批量转换
aliases = ["肩推", "Shoulder Press", "overhead press"]
standard_names = mapper.batch_map(aliases)
# 返回: ["哑铃推举", "哑铃推举", "哑铃推举"]
```

---

## 🔗 集成方式

- **MCP工具**：intelligent_exercise_selector
- **服务层**：training_plan_summarizer
- **工作流**：workflow_executor

---

**维护者**: 薛小川
**最后更新**: 2025-12-31
