# MCP工具使用指南

**版本**: v1.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

本指南说明如何使用DAML-RAG系统中的17个MCP工具（16个Python内置工具 + 1个stdio MCP服务）。这些工具提供专业的健身功能，包括动作选择、训练计划设计、营养规划、安全评估等。

### 核心原则

- ✅ **通过DAG编排器调用**：不直接调用工具，而是通过DAG模板系统
- ✅ **自动依赖管理**：DAG编排器自动处理工具间的依赖关系
- ✅ **并行执行优化**：自动识别可并行任务，提升执行效率
- ✅ **缓存机制**：自动缓存可重复使用的结果
- ✅ **错误处理**：完善的错误处理和降级策略

---

## 工具调用方法

### 方法1：通过API调用（推荐）

**适用场景**：前端应用、外部系统集成

```javascript
// 流式调用（推荐）
const eventSource = new EventSource('/api/chat/stream', {
  method: 'POST',
  body: JSON.stringify({
    query: '推荐几个胸部动作',
    user_id: 'user_123'
  })
});

// 监听进度事件
eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  console.log(`步骤${data.step}: ${data.step_name}`);
});

// 监听内容事件
eventSource.addEventListener('content', (event) => {
  const data = JSON.parse(event.data);
  appendContent(data.content);
});

// 监听完成事件
eventSource.addEventListener('done', (event) => {
  const data = JSON.parse(event.data);
  console.log('完成！');
  eventSource.close();
});
```

```javascript
// 非流式调用
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: '推荐几个胸部动作',
    user_id: 'user_123'
  })
});

const result = await response.json();
console.log(result.response);
```

### 方法2：通过Python代码调用

**适用场景**：后端开发、测试、调试

```python
from src.applications.fitness.workflow_executor import WorkflowExecutor
from src.applications.fitness.dag_template_system import DAGTemplateManager

# 初始化
workflow_executor = WorkflowExecutor()
template_manager = DAGTemplateManager()

# 执行工作流程
result = await workflow_executor.execute_workflow(
    query="推荐几个胸部动作",
    user_id="user_123",
    session_id="session_456"
)

print(result["response"])
```

### 方法3：直接调用单个工具（仅用于测试）

**适用场景**：单元测试、工具调试

```python
from src.applications.fitness.mcp_tools.registry import MCPToolRegistry
from src.applications.fitness.mcp_tools import initialize_all_tools

# 初始化工具注册表
registry = MCPToolRegistry()
initialize_all_tools(
    registry,
    neo4j_client=neo4j_client,
    qdrant_client=qdrant_client,
    three_layer_engine=three_layer_engine
)

# 调用单个工具
result = await registry.call_tool(
    tool_name="intelligent_exercise_selector",
    input_data={
        "target_muscle": "胸大肌",
        "difficulty": "intermediate",
        "equipment": "哑铃"
    }
)

print(result)
```

---

## 工具分类和使用场景

### Exercise工具（动作相关）

#### 1. intelligent_exercise_selector - 智能动作选择器

**使用场景**：
- 根据目标肌肉查询动作
- 根据难度和器材筛选动作
- 查询训练容量

**输入参数**：
```python
{
  "target_muscle": "胸大肌",      # 必需：目标肌肉
  "difficulty": "intermediate",   # 可选：难度（beginner/intermediate/advanced）
  "equipment": "哑铃",            # 可选：器材
  "limit": 10                     # 可选：返回数量限制
}
```

**输出示例**：
```json
{
  "success": true,
  "exercises": [
    {
      "name": "哑铃卧推",
      "difficulty": "intermediate",
      "equipment": "哑铃",
      "primary_muscles": ["胸大肌"],
      "secondary_muscles": ["三角肌前束", "肱三头肌"]
    }
  ],
  "total_count": 8
}
```

**使用示例**：
```python
# 查询胸部动作
result = await registry.call_tool(
    "intelligent_exercise_selector",
    {
        "target_muscle": "胸大肌",
        "difficulty": "intermediate",
        "equipment": "哑铃"
    }
)
```

#### 2. exercise_alternative_finder - 动作替代查找器

**使用场景**：
- 查找替代动作
- 基于目标肌肉匹配
- 考虑器材限制

**输入参数**：
```python
{
  "original_exercise": "杠铃卧推",  # 必需：原动作名称
  "available_equipment": ["哑铃"],  # 可选：可用器材
  "limit": 5                        # 可选：返回数量限制
}
```

**输出示例**：
```json
{
  "success": true,
  "alternatives": [
    {
      "name": "哑铃卧推",
      "similarity_score": 0.95,
      "reason": "目标肌肉相同，动作模式相似"
    }
  ]
}
```

---

### Training工具（训练相关）

#### 3. professional_program_designer - 专业计划设计器

**使用场景**：
- 设计完整训练计划
- 基于用户目标和水平
- 整合多个肌肉群

**输入参数**：
```python
{
  "user_profile": {...},           # 必需：用户档案
  "selected_exercises": [...],     # 必需：选定的动作列表
  "training_goal": "增肌",         # 必需：训练目标
  "duration_weeks": 4              # 可选：计划周期
}
```

**输出示例**：
```json
{
  "success": true,
  "program": {
    "program_name": "4周增肌训练计划",
    "duration_weeks": 4,
    "training_days_per_week": 4,
    "split_type": "upper_lower",
    "weekly_schedule": [...]
  }
}
```

#### 4. muscle_group_volume_calculator - 肌群容量计算器

**使用场景**：
- 计算周训练量
- 基于训练频率调整
- 使用MEV/MAV/MRV数据

**输入参数**：
```python
{
  "muscle_group": "胸大肌",        # 必需：肌肉群
  "training_level": "intermediate", # 必需：训练水平
  "recovery_capacity": "normal"     # 可选：恢复能力
}
```

**输出示例**：
```json
{
  "success": true,
  "volume_recommendation": {
    "muscle_group": "胸大肌",
    "mev": 10,
    "mav": 16,
    "mrv": 22,
    "recommended_sets_per_week": 14
  }
}
```

#### 5. periodized_program_designer - 周期化计划设计器

**使用场景**：
- 设计周期化训练计划
- 分阶段调整强度
- 优化长期进步

**输入参数**：
```python
{
  "training_level": "intermediate",  # 必需：训练水平
  "training_goal": "增肌",           # 必需：训练目标
  "duration_weeks": 12               # 必需：计划周期
}
```

**输出示例**：
```json
{
  "success": true,
  "periodized_program": {
    "phases": [
      {
        "phase_name": "适应期",
        "weeks": 2,
        "intensity": "60-70%",
        "volume": "中等"
      },
      {
        "phase_name": "增长期",
        "weeks": 6,
        "intensity": "70-85%",
        "volume": "高"
      }
    ]
  }
}
```

#### 6. training_split_designer - 训练分化设计器

**使用场景**：
- 设计训练分化方案
- 基于训练频率
- 优化肌肉恢复

**输入参数**：
```python
{
  "training_days_per_week": 4,     # 必需：每周训练天数
  "training_goal": "增肌",         # 必需：训练目标
  "training_level": "intermediate" # 必需：训练水平
}
```

**输出示例**：
```json
{
  "success": true,
  "split_design": {
    "split_type": "upper_lower",
    "schedule": [
      {"day": 1, "focus": "上肢推"},
      {"day": 2, "focus": "下肢"},
      {"day": 3, "focus": "上肢拉"},
      {"day": 4, "focus": "下肢"}
    ]
  }
}
```

---

### Safety工具（安全相关）

#### 7. contraindications_checker - 禁忌症检查器

**使用场景**：
- 检查用户健康状况
- 识别禁忌动作
- 提供替代方案

**输入参数**：
```python
{
  "user_profile": {...},           # 必需：用户档案
  "exercises": ["深蹲", "硬拉"]    # 可选：要检查的动作列表
}
```

**输出示例**：
```json
{
  "success": true,
  "contraindications": [
    {
      "exercise": "颈后深蹲",
      "reason": "颈椎压力过大",
      "severity": "high"
    }
  ],
  "safe_exercises": [...]
}
```

#### 8. injury_risk_assessor - 损伤风险评估器

**使用场景**：
- 评估动作风险等级
- 基于safety_level分类
- 生成风险报告

**输入参数**：
```python
{
  "user_profile": {...},           # 必需：用户档案
  "exercises": ["深蹲", "硬拉"]    # 必需：要评估的动作列表
}
```

**输出示例**：
```json
{
  "success": true,
  "risk_assessment": [
    {
      "exercise": "深蹲",
      "risk_level": "medium",
      "risk_factors": ["膝关节压力", "腰椎负荷"],
      "recommendations": ["确保正确姿势", "循序渐进增加重量"]
    }
  ]
}
```

#### 9. safe_exercise_modifier - 安全动作修改器

**使用场景**：
- 修改动作以适应限制
- 推荐康复渐进路径
- 确保训练安全

**输入参数**：
```python
{
  "exercise": "深蹲",              # 必需：动作名称
  "user_limitations": ["膝盖损伤"], # 必需：用户限制
  "rehabilitation_stage": "subacute" # 可选：康复阶段
}
```

**输出示例**：
```json
{
  "success": true,
  "modified_exercise": {
    "name": "靠墙静蹲",
    "modifications": ["减少膝关节角度", "控制下蹲深度"],
    "progression_path": [
      {"exercise": "靠墙静蹲", "duration": "2周"},
      {"exercise": "徒手深蹲", "duration": "4周"},
      {"exercise": "杠铃深蹲", "duration": "持续"}
    ]
  }
}
```

---

### Nutrition工具（营养相关）

#### 10. tdee_calculator - TDEE计算器

**使用场景**：
- 计算每日总能量消耗
- 基于Harris-Benedict公式
- 考虑活动水平

**输入参数**：
```python
{
  "age": 28,                       # 必需：年龄
  "gender": "male",                # 必需：性别
  "weight_kg": 75,                 # 必需：体重（kg）
  "height_cm": 175,                # 必需：身高（cm）
  "activity_level": "moderate"     # 必需：活动水平
}
```

**输出示例**：
```json
{
  "success": true,
  "tdee": {
    "bmr": 1750,
    "tdee": 2625,
    "activity_multiplier": 1.5,
    "macros": {
      "protein_g": 150,
      "carbs_g": 300,
      "fat_g": 75
    }
  }
}
```

#### 11. nutrition_intake_analyzer - 营养摄入分析器

**使用场景**：
- 分析营养摄入
- 对比推荐摄入量
- 识别营养缺口

**输入参数**：
```python
{
  "current_intake": {              # 必需：当前摄入
    "protein_g": 120,
    "carbs_g": 250,
    "fat_g": 60
  },
  "target_intake": {               # 必需：目标摄入
    "protein_g": 150,
    "carbs_g": 300,
    "fat_g": 75
  }
}
```

**输出示例**：
```json
{
  "success": true,
  "analysis": {
    "protein_gap": -30,
    "carbs_gap": -50,
    "fat_gap": -15,
    "recommendations": [
      "增加蛋白质摄入30g",
      "增加碳水化合物摄入50g"
    ]
  }
}
```

#### 12. meal_plan_designer - 膳食计划设计器

**使用场景**：
- 设计每日膳食计划
- 满足营养需求
- 考虑食物偏好

**输入参数**：
```python
{
  "tdee": 2625,                    # 必需：TDEE
  "training_goal": "增肌",         # 必需：训练目标
  "meals_per_day": 4,              # 可选：每日餐数
  "food_preferences": ["鸡胸肉"]   # 可选：食物偏好
}
```

**输出示例**：
```json
{
  "success": true,
  "meal_plan": {
    "total_calories": 2800,
    "meals": [
      {
        "meal_name": "早餐",
        "foods": [...],
        "calories": 700,
        "protein_g": 40
      }
    ]
  }
}
```

#### 13. exercise_nutrition_optimization - 运动营养优化器

**使用场景**：
- 基于训练目标推荐营养
- 优化营养时机
- 支持恢复和增长

**输入参数**：
```python
{
  "training_intensity": "high",    # 必需：训练强度
  "target_muscle": "胸大肌",       # 必需：目标肌肉
  "recovery_time": "48小时"        # 必需：恢复时间
}
```

**输出示例**：
```json
{
  "success": true,
  "nutrition_optimization": {
    "pre_workout": {
      "timing": "训练前1-2小时",
      "foods": ["香蕉", "燕麦"],
      "calories": 300
    },
    "post_workout": {
      "timing": "训练后30分钟内",
      "foods": ["蛋白粉", "白米饭"],
      "calories": 400
    }
  }
}
```

---

### Learning工具（学习相关）

#### 14. record_training_feedback - 训练反馈记录器

**使用场景**：
- 记录训练反馈
- 存储到向量库
- 用于Few-Shot学习

**输入参数**：
```python
{
  "user_id": "user_123",           # 必需：用户ID
  "query": "推荐胸部动作",         # 必需：原始查询
  "response": "...",               # 必需：系统响应
  "feedback": "positive"           # 必需：反馈（positive/negative）
}
```

**输出示例**：
```json
{
  "success": true,
  "feedback_id": "feedback_456",
  "stored_in_vector_db": true
}
```

#### 15. find_similar_training_cases - 相似案例查找器

**使用场景**：
- 查找相似训练案例
- 用于Few-Shot学习
- 提供参考案例

**输入参数**：
```python
{
  "query": "推荐胸部动作",         # 必需：查询文本
  "limit": 5                       # 可选：返回数量限制
}
```

**输出示例**：
```json
{
  "success": true,
  "similar_cases": [
    {
      "query": "推荐胸部训练动作",
      "response": "...",
      "similarity_score": 0.92
    }
  ]
}
```

---

### User Profile工具（用户档案）

#### 16. get_user_profile - 获取用户档案

**使用场景**：
- 获取用户基本信息
- 获取健身配置
- 获取健康状况

**输入参数**：
```python
{
  "user_id": "user_123"            # 必需：用户ID
}
```

**输出示例**：
```json
{
  "success": true,
  "user_profile": {
    "user_id": "user_123",
    "age": 28,
    "gender": "male",
    "weight_kg": 75,
    "height_cm": 175,
    "fitness_level": "intermediate",
    "training_days_per_week": 4,
    "fitness_goals": ["增肌", "力量提升"],
    "available_equipment": ["哑铃", "杠铃"],
    "health_conditions": [],
    "injury_history": []
  }
}
```

#### 17. update_user_profile - 更新用户档案

**使用场景**：
- 更新用户信息
- 更新健身配置
- 更新健康状况

**输入参数**：
```python
{
  "user_id": "user_123",           # 必需：用户ID
  "updates": {                     # 必需：更新内容
    "weight_kg": 76,
    "fitness_goals": ["增肌", "力量提升", "减脂"]
  }
}
```

**输出示例**：
```json
{
  "success": true,
  "updated_fields": ["weight_kg", "fitness_goals"],
  "user_profile": {...}
}
```

---

## 扩展新工具的步骤

### 步骤1：创建工具文件

在对应目录下创建Python文件：

```python
# src/applications/fitness/mcp_tools/training/new_tool.py

from src.applications.fitness.mcp_tools.base_tool import BaseMCPTool
from pydantic import BaseModel
from typing import Dict, Any

class NewToolInput(BaseModel):
    """输入Schema"""
    param1: str
    param2: int = 0

class NewToolOutput(BaseModel):
    """输出Schema"""
    success: bool
    result: Dict[str, Any]

class NewTool(BaseMCPTool):
    """新工具"""
    
    def get_name(self) -> str:
        return "new_tool"
    
    def get_description(self) -> str:
        return "新工具的描述"
    
    def get_category(self) -> str:
        return "training"
    
    def get_input_schema(self) -> type[BaseModel]:
        return NewToolInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return NewToolOutput
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具逻辑"""
        param1 = input_data["param1"]
        param2 = input_data.get("param2", 0)
        
        # 实现工具逻辑
        result = self._process(param1, param2)
        
        return {
            "success": True,
            "result": result
        }
    
    def _process(self, param1: str, param2: int) -> Dict[str, Any]:
        """处理逻辑"""
        # 实现具体逻辑
        return {"data": "processed"}
```

### 步骤2：注册工具

在`__init__.py`中注册：

```python
# src/applications/fitness/mcp_tools/__init__.py

from .training.new_tool import NewTool

def initialize_all_tools(registry, ...):
    # ... 其他工具
    registry.register_tool(NewTool(neo4j_client, qdrant_client, three_layer_engine))
```

### 步骤3：更新注册表

在`mcp_registry.json`中添加元数据：

```json
{
  "python_tools": {
    "training": [
      "professional_program_designer",
      "new_tool"
    ]
  }
}
```

### 步骤4：编写测试

创建单元测试：

```python
# tests/unit/mcp_tools/test_new_tool.py

import pytest
from src.applications.fitness.mcp_tools.training.new_tool import NewTool

@pytest.mark.asyncio
async def test_new_tool():
    tool = NewTool(neo4j_client, qdrant_client, three_layer_engine)
    
    result = await tool.execute({
        "param1": "test",
        "param2": 10
    })
    
    assert result["success"] == True
    assert "result" in result
```

### 步骤5：更新文档

更新相关文档：
- `02-核心架构/03-编排层/03-MCP工具架构.md`
- `03-代码参考/03-MCP工具实现/`
- `04-开发指南/02-工具使用/02-MCP工具使用指南.md`（本文档）

---

## 工具配置

### 配置文件位置

```
daml-rag-server/
├── config/
│   ├── mcp_registry.json          # MCP工具注册表
│   └── performance_optimization.yaml  # 性能优化配置
```

### 性能配置

```yaml
# config/performance_optimization.yaml

mcp_tools:
  # 缓存配置
  cache:
    enabled: true
    ttl_seconds: 3600
    max_size: 1000
  
  # 超时配置
  timeout:
    default_seconds: 30
    by_tool:
      professional_program_designer: 60
      periodized_program_designer: 45
  
  # 并行配置
  parallel:
    max_concurrent_tools: 5
    enable_parallel_execution: true
```

---

## 最佳实践建议

### 1. 工具调用

✅ **通过DAG编排器**：不直接调用工具，使用DAG模板系统  
✅ **提供完整参数**：确保必需参数都提供  
✅ **处理错误**：检查返回的success字段  
✅ **使用缓存**：利用系统的缓存机制

### 2. 错误处理

✅ **检查success字段**：所有工具都返回success字段  
✅ **读取error信息**：失败时查看error字段  
✅ **重试机制**：网络错误时可以重试  
✅ **降级策略**：关键工具失败时使用降级方案

### 3. 性能优化

✅ **批量调用**：尽可能批量调用工具  
✅ **并行执行**：利用DAG编排器的并行能力  
✅ **缓存结果**：缓存可重复使用的结果  
✅ **监控性能**：监控工具执行时间

### 4. 安全性

✅ **验证输入**：使用Pydantic Schema验证输入  
✅ **检查权限**：确保用户有权限调用工具  
✅ **限流控制**：避免过度调用  
✅ **日志记录**：记录所有工具调用

---

## 相关文档

- **MCP工具架构**: `../../02-核心架构/03-编排层/03-MCP工具架构.md`
- **MCP工具代码实现**: `../../03-代码参考/03-MCP工具实现/`
- **MCP工具开发指南**: `../01-快速上手/02-MCP工具开发指南.md`
- **DAG模板选择指南**: `01-DAG模板选择指南.md`

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
