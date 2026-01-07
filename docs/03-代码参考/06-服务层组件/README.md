# 06-服务层组件

**版本**: v1.0.0
**创建日期**: 2025-12-31
**状态**: ✅ 已完成

---

## 📋 概述

服务层是应用层的业务逻辑核心，封装了健身领域的专业业务逻辑，为MCP工具和工作流提供高质量的服务支持。服务层包含16个核心组件，覆盖训练计划、安全评估、数据分析等全业务流程。

---

## 📚 组件列表

### 1. [equipment_alias_mapper.py](./01-equipment_alias_mapper.md)
- **功能**：器械别名映射器
- **位置**：`src/applications/fitness/services/equipment_alias_mapper.py`
- **说明**：统一管理器械名称的多种表达方式，实现智能识别和转换

### 2. [exercise_stability_manager.py](./02-exercise_stability_manager.md)
- **功能**：动作稳定性管理器
- **位置**：`src/applications/fitness/services/exercise_stability_manager.py`
- **说明**：评估动作的稳定性等级，提供动作改良建议

### 3. [progressive_overload.py](./03-progressive_overload.md)
- **功能**：渐进式超负荷计算
- **位置**：`src/applications/fitness/services/progressive_overload.py`
- **说明**：科学计算训练强度的渐进式增长计划

### 4. [safety_reminder_generator.py](./04-safety_reminder_generator.md)
- **功能**：安全提醒生成器
- **位置**：`src/applications/fitness/services/safety_reminder_generator.py`
- **说明**：基于用户状态和动作特点生成个性化安全提醒

### 5. [training_goal_recommender.py](./05-training_goal_recommender.md)
- **功能**：训练目标推荐器
- **位置**：`src/applications/fitness/services/training_goal_recommender.py`
- **说明**：根据用户档案和历史数据推荐合适的训练目标

### 6. [training_log_analyzer.py](./06-training_log_analyzer.md)
- **功能**：训练日志分析器
- **位置**：`src/applications/fitness/services/training_log_analyzer.py`
- **说明**：深度分析训练记录，识别训练模式和趋势

### 7. [training_plan_summarizer.py](./07-training_plan_summarizer.md)
- **功能**：训练计划总结器
- **位置**：`src/applications/fitness/services/training_plan_summarizer.py`
- **说明**：对复杂训练计划进行智能总结和提炼

### 8. [user_profile_integrator.py](./08-user_profile_integrator.md)
- **功能**：用户档案集成器
- **位置**：`src/applications/fitness/services/user_profile_integrator.py`
- **说明**：整合多源用户数据，构建完整用户画像

### 9. [volume_adjuster.py](./09-volume_adjuster.md)
- **功能**：训练量调整器
- **位置**：`src/applications/fitness/services/volume_adjuster.py`
- **说明**：根据恢复状态和目标动态调整训练量

### 10. [weekly_plan_generator.py](./10-weekly_plan_generator.md)
- **功能**：周计划生成器
- **位置**：`src/applications/fitness/services/weekly_plan_generator.py`
- **说明**：生成完整的周训练计划，包括动作、组数、次数等

---

## 🔗 服务层架构

```
应用层 (applications/fitness/)
├── mcp_tools/          # MCP工具 (17个)
├── services/           # 服务层 (16个组件) ⭐
├── workflow/           # 工作流系统 (7个文件)
├── dag/                # DAG编排 (6个文件)
└── parameters/         # 参数系统 (6个组件)
```

## 🎯 服务层特点

1. **业务聚焦**：专门针对健身领域设计
2. **松耦合**：服务间依赖最小化，可独立使用
3. **高性能**：内置缓存和优化机制
4. **可扩展**：易于添加新的业务逻辑
5. **可测试**：完整单元测试覆盖

---

**维护者**: 薛小川
**最后更新**: 2025-12-31
