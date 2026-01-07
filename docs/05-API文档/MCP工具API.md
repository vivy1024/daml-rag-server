# DAML-RAG框架MCP工具系统参考

**创建日期**: 2025-12-22

---


**版本**: v5.0.0
**更新日期**: 2025-12-03
**状态**: ✅ 生产就绪

---

## 📋 概述

DAML-RAG框架包含**13个专业健身MCP工具**，作为内部组件提供智能健身服务。这些工具通过MCPOrchestrator进行编排，不直接对外暴露HTTP接口。

`✶ Insight ─────────────────────────────────────`
DAML-RAG的MCP工具设计遵循"专业领域深度"原则。每个工具都针对健身领域的特定需求设计，从动作选择到营养优化，从周期化设计到损伤预防，形成完整的健身指导生态系统。这些工具不是通用API，而是专业级健身服务组件。
`─────────────────────────────────────────────────`

---

## 🔧 MCP工具调用方式

### ⚠️ 重要说明

**❌ 错误方式**: 通过HTTP端点直接调用MCP工具
```bash
# 这样调用是错误的，不存在这些HTTP端点
curl -X POST http://localhost:8001/api/mcp/tools/intelligent_exercise_selector
```

**✅ 正确方式**: 通过MCPOrchestrator内部编排调用
```python
from fitness_orchestrator import FitnessOrchestrator

orchestrator = FitnessOrchestrator()
result = await orchestrator.call_tool("IntelligentExerciseSelectorV2", params)
```

---

## 🏋️ 13个专业健身MCP工具

### 1. IntelligentExerciseSelectorV2
- **文件**: `intelligent_exercise_selector_v2.py`
- **功能**: 智能动作选择器
- **用途**: 根据用户目标、器械条件、健身水平选择最适合的训练动作
- **核心算法**: 多维度评分系统 + 约束满足

### 2. ExerciseNutritionOptimizerV2
- **文件**: `exercise_nutrition_optimization_v2.py`
- **功能**: 训练营养优化器
- **用途**: 为特定训练动作和目标提供营养搭配建议
- **核心算法**: 营养素匹配 + 能量需求计算

### 3. PeriodizedProgramDesignerV2
- **文件**: `periodized_program_designer_v2.py`
- **功能**: 周期化计划设计器
- **用途**: 设计科学的训练周期化方案（线性/波浪/分块等）
- **核心算法**: 周期化模型 + 超量恢复原理

### 4. InjuryPreventionAnalyzer
- **文件**: `injury_prevention_analyzer.py`
- **功能**: 损伤预防分析器
- **用途**: 分析训练动作的损伤风险并提供预防建议
- **核心算法**: 生物力学分析 + 风险评估模型

### 5. WorkoutIntensityCalculator
- **文件**: `workout_intensity_calculator.py`
- **功能**: 训练强度计算器
- **用途**: 计算训练强度、RPE、心率区间等强度指标
- **核心算法**: 强度理论 + 个性化系数

### 6. RecoveryTimeEstimator
- **文件**: `recovery_time_estimator.py`
- **功能**: 恢复时间估算器
- **用途**: 估算训练后所需的恢复时间
- **核心算法**: 恢复模型 + 个体差异因子

### 7. ExerciseTechniqueCoach
- **文件**: `exercise_technique_coach.py`
- **功能**: 动作技术教练
- **用途**: 提供动作技术指导和纠正建议
- **核心算法**: 运动生物力学 + 技术评分系统

### 8. NutritionTimingOptimizer
- **文件**: `nutrition_timing_optimizer.py`
- **功能**: 营养时机优化器
- **用途**: 优化训练前后的营养摄入时机
- **核心算法**: 代谢节律 + 营养吸收动力学

### 9. SupplementSelector
- **文件**: `supplement_selector.py`
- **功能**: 补剂选择器
- **用途**: 根据训练目标和需求推荐合适的营养补剂
- **核心算法**: 循证医学 + 个体化匹配

### 10. ProgressTracker
- **文件**: `progress_tracker.py`
- **功能**: 进度跟踪器
- **用途**: 跟踪训练进度并提供调整建议
- **核心算法**: 进度建模 + 目标达成分析

### 11. GoalAdjustmentAdvisor
- **文件**: `goal_adjustment_advisor.py`
- **功能**: 目标调整建议器
- **用途**: 根据实际进展调整训练目标
- **核心算法**: 目标理论 + 适应性调整

### 12. PersonalizedWarmupCreator
- **文件**: `personalized_warmup_creator.py`
- **功能**: 个性化热身创建器
- **用途**: 创建针对特定训练的个性化热身方案
- **核心算法**: 运动生理学 + 热身效应研究

### 13. ProfessionalFitnessWorkflow
- **文件**: `professional_fitness_workflow.py`
- **功能**: 专业健身工作流
- **用途**: 协调多个工具完成复杂的健身咨询任务
- **核心算法**: 工作流编排 + 多工具协同

---

## 🔧 BaseMCPTool架构

所有MCP工具都继承自`BaseMCPTool`基类：

```python
class BaseMCPTool:
    """MCP工具基类"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.validate_config()

    async def execute(self, **kwargs) -> dict:
        """工具执行入口"""
        raise NotImplementedError

    def validate_input(self, **kwargs) -> bool:
        """输入验证"""
        return True

    def get_tool_info(self) -> dict:
        """获取工具信息"""
        return {
            "name": self.__class__.__name__,
            "description": self.__doc__,
            "version": getattr(self, "VERSION", "1.0.0")
        }
```

---

## 🔄 工具编排系统

### MCPOrchestrator

MCPOrchestrator负责任务分解、工具选择和结果整合：

```python
class MCPOrchestrator:
    """MCP工具编排器"""

    async def process_user_query(self, query: str, user_profile: dict) -> dict:
        """处理用户查询"""
        # 1. 任务分解
        subtasks = await self.decompose_task(query)

        # 2. 工具选择
        tools = await self.select_tools(subtasks, user_profile)

        # 3. 并行执行
        results = await asyncio.gather(*[
            self.execute_tool(tool, params)
            for tool, params in tools
        ])

        # 4. 结果整合
        return await self.integrate_results(results)
```

### 工具协作模式

1. **顺序执行**: 先分析后推荐
2. **并行执行**: 多角度分析
3. **条件执行**: 根据中间结果决定后续工具
4. **迭代优化**: 多轮优化改进

---

## 📊 实际使用场景

### 场景1: 完整健身咨询

```python
# 通过chat_service间接调用MCP工具
response = await chat_service.process_message(
    message="帮我制定一个12周的增肌计划",
    user_id="user-123"
)

# 内部流程：
# 1. IntelligentExerciseSelectorV2 - 选择合适动作
# 2. PeriodizedProgramDesignerV2 - 设计周期化方案
# 3. WorkoutIntensityCalculator - 计算训练强度
# 4. NutritionTimingOptimizer - 优化营养时机
# 5. RecoveryTimeEstimator - 估算恢复时间
```

### 场景2: 损伤风险评估

```python
response = await chat_service.process_message(
    message="深蹲对膝盖有损伤风险吗？",
    user_id="user-456"
)

# 内部流程：
# 1. InjuryPreventionAnalyzer - 损伤风险分析
# 2. ExerciseTechniqueCoach - 技术指导
# 3. PersonalizedWarmupCreator - 热身建议
```

---

## 🚀 如何访问MCP工具

### 通过聊天接口

所有MCP工具都可以通过 `/chat` 接口间接访问：

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "推荐几个适合新手的胸部训练动作",
    "user_id": "user-123"
  }'
```

### 通过GraphRAG接口

MCP工具的分析结果也会影响GraphRAG的推理过程：

```bash
curl -X POST http://localhost:8001/api/graphrag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "安全有效的深蹲技术要点",
    "domain": "fitness_exercises"
  }'
```

---

## 🔗 相关文档

- <!-- [MCP工具系统参考](../03-代码参考/25-MCP工具系统参考.md) (文档不存在) --> - 详细技术实现
- [健身编排器参考](../03-代码参考/13-FitnessOrchestrator健身编排器参考.md) - 编排逻辑
- <!-- [GraphRAG三层检索](../03-代码参考/15-企业级三层检索引擎参考.md) (文档不存在) --> - 检索架构
- [API使用指南](./API参考文档.md) - HTTP API接口

---

## 📝 开发指南

### 添加新MCP工具

1. **继承基类**:
```python
class CustomFitnessTool(BaseMCPTool):
    VERSION = "1.0.0"

    async def execute(self, **kwargs) -> dict:
        # 实现工具逻辑
        return {"result": "success"}
```

2. **注册工具**:
```python
# 在 mcp_tool_registry.py 中注册
registry.register_tool("CustomFitnessTool", CustomFitnessTool)
```

3. **更新编排器**:
```python
# 在 fitness_orchestrator.py 中添加工具调用逻辑
```

---

**维护者**: 薛小川
**最后更新**: 2025-12-03
**版本**: v5.0.0
**工具数量**: 13个
**访问方式**: 通过/chat和/api/graphrag/query间接访问

---

**重要提醒**:
- ✅ MCP工具是内部组件，不对外暴露HTTP接口
- ✅ 通过MCPOrchestrator进行统一编排
- ✅ 所有工具都继承自BaseMCPTool
- ✅ 工具间支持复杂的协作模式
- ✅ 通过聊天接口间接访问所有工具功能