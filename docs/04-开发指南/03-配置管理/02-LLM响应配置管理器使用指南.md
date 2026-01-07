# LLM响应配置管理器使用指南

**版本**: v1.0.0  
**创建日期**: 2025-12-17  
**更新日期**: 2025-12-17  
**状态**: ✅ 已完成

---

## 📋 概述

LLM响应配置管理器（`LLMResponseConfigManager`）是一个基于YAML配置文件的配置管理系统，用于管理不同DAG模板的LLM响应行为。

**核心功能**：
- 从YAML文件加载配置
- 根据模板ID获取配置
- 动态构建提示词
- 支持配置热加载
- 完善的错误处理

---

## 🚀 快速开始

### 基本使用

```python
from src.framework.config import LLMResponseConfigManager

# 1. 初始化配置管理器
manager = LLMResponseConfigManager()

# 2. 获取配置
config = manager.get_config("greeting")
print(f"max_tokens: {config.max_tokens}")
print(f"temperature: {config.temperature}")

# 3. 构建提示词
prompt = manager.build_prompt(
    "greeting",
    query="你好",
    response_hint="简短友好，1-2句话"
)

# 4. 使用配置调用LLM
response = await call_llm(
    prompt=prompt,
    max_tokens=config.max_tokens,
    temperature=config.temperature
)
```

---

## 📦 核心API

### LLMResponseConfig

**数据类**，定义单个模板的LLM响应配置。

**字段**：
- `max_tokens` (int): 最大生成token数（50-20000）
- `temperature` (float): 温度参数（0.0-1.0）
- `response_style` (str): 响应风格（concise/detailed/comprehensive等）
- `tone` (str): 语气（friendly/professional/cautious等）
- `length_constraint` (str): 长度约束描述
- `prompt_template` (str): 提示词模板（支持占位符）

**方法**：
- `from_dict(data: dict)`: 从字典创建配置对象
- `to_dict()`: 转换为字典

### LLMResponseConfigManager

**管理器类**，负责加载和管理所有模板配置。

#### 初始化

```python
# 使用默认配置文件路径
manager = LLMResponseConfigManager()

# 使用自定义配置文件路径
manager = LLMResponseConfigManager(config_path="path/to/config.yaml")
```

#### 获取配置

```python
# 获取指定模板的配置
config = manager.get_config("greeting")

# 如果模板不存在，返回默认配置
config = manager.get_config("unknown_template")  # 返回default配置
```

#### 构建提示词

```python
# 使用模板构建提示词
prompt = manager.build_prompt(
    template_id="greeting",
    query="你好",
    response_hint="简短友好"
)

# 支持的占位符
prompt = manager.build_prompt(
    template_id="complete_training_plan",
    query="制定增肌计划",
    user_profile=json.dumps(user_profile),
    response_hint="详细专业",
    mcp_tools_count=5,
    retrieval_count=10
)
```

#### 其他方法

```python
# 重新加载配置（热加载）
manager.reload()

# 获取所有模板ID
template_ids = manager.get_all_template_ids()

# 检查模板是否存在
exists = manager.has_config("greeting")
```

---

## 📝 配置文件格式

**位置**: `daml-rag-server/config/llm_response_config.yaml`

**结构**：
```yaml
templates:
  greeting:
    max_tokens: 100
    temperature: 0.8
    response_style: "concise"
    tone: "friendly"
    length_constraint: "1-2句话"
    prompt_template: |
      你是玉珍健身的AI助手。用户向你问好，请简短友好地回应。
      
      用户查询: {query}
      
      响应要求: {response_hint}
      
      请直接回应，不要提供训练建议或其他内容。

default:
  max_tokens: 2000
  temperature: 0.7
  response_style: "balanced"
  tone: "professional"
  length_constraint: "适中"
  prompt_template: |
    你是玉珍健身专业教练，擅长基于真实数据进行深度分析和个性化指导。
    
    用户查询: {query}
    
    用户档案: {user_profile}
    
    请提供专业的分析和建议。
```

---

## 🎯 提示词占位符

配置文件中的提示词模板支持以下占位符：

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{query}` | 用户查询文本 | "制定增肌计划" |
| `{user_profile}` | 用户档案（JSON字符串） | '{"age": 25, "goal": "增肌"}' |
| `{response_hint}` | 响应提示 | "简短友好，1-2句话" |
| `{mcp_tools_count}` | MCP工具调用数量 | 5 |
| `{retrieval_count}` | 检索结果数量 | 10 |

**使用示例**：
```python
prompt = manager.build_prompt(
    "complete_training_plan",
    query="制定增肌计划",
    user_profile='{"age": 25}',
    response_hint="详细专业",
    mcp_tools_count=5,
    retrieval_count=10
)
```

---

## ⚠️ 错误处理

### 配置文件不存在

如果配置文件不存在，管理器会自动使用内置的默认配置：
- greeting配置
- quick_consultation配置
- default配置

```python
# 配置文件不存在时
manager = LLMResponseConfigManager(config_path="/nonexistent/path.yaml")
# ⚠️ 日志: "配置文件不存在，使用默认配置"
# ✅ 仍然可以正常使用
```

### YAML格式错误

如果YAML格式错误，管理器会回退到内置默认配置：

```python
# YAML格式错误时
manager = LLMResponseConfigManager(config_path="invalid.yaml")
# ⚠️ 日志: "YAML格式错误，使用默认配置"
# ✅ 仍然可以正常使用
```

### 模板不存在

如果请求的模板不存在，返回默认配置：

```python
config = manager.get_config("unknown_template")
# ⚠️ 日志: "模板配置不存在: unknown_template，使用默认配置"
# ✅ 返回default配置
```

### 参数验证

如果参数超出范围，抛出ValueError：

```python
# max_tokens超出范围
config = LLMResponseConfig(
    max_tokens=30000,  # 超过20000
    temperature=0.7,
    # ...
)
# ❌ ValueError: max_tokens必须在50-20000之间

# temperature超出范围
config = LLMResponseConfig(
    max_tokens=1000,
    temperature=1.5,  # 超过1.0
    # ...
)
# ❌ ValueError: temperature必须在0.0-1.0之间
```

---

## 🧪 测试

### 运行单元测试

```bash
# 在Docker容器内运行
docker exec fitness_daml_rag pytest tests/unit/test_llm_response_config_manager.py -v
```

### 运行演示脚本

```bash
# 在Docker容器内运行
docker exec fitness_daml_rag python scripts/demo_config_manager.py
```

---

## 📊 已配置的模板

当前配置文件包含9个模板：

| 模板ID | max_tokens | temperature | 说明 |
|--------|-----------|-------------|------|
| greeting | 100 | 0.8 | 问候闲聊 |
| quick_consultation | 800 | 0.6 | 快速咨询 |
| exercise_optimization | 3000 | 0.6 | 动作优化 |
| safety_assessment | 4000 | 0.5 | 安全评估 |
| complete_training_plan | 12000 | 0.7 | 完整训练计划 |
| nutrition_planning | 8000 | 0.6 | 营养规划 |
| comprehensive_fitness | 15000 | 0.7 | 综合健身方案 |
| progress_analysis | 4000 | 0.6 | 进展分析 |
| rehabilitation_training | 8000 | 0.5 | 康复训练 |

---

## 🔧 集成到工作流程

### 在workflow_executor.py中使用

```python
from src.framework.config import LLMResponseConfigManager

# 初始化（在类初始化时）
self.config_manager = LLMResponseConfigManager()

# 在步骤10中使用
async def execute_step_10(self, template_id, query, user_profile, ...):
    # 1. 获取配置
    config = self.config_manager.get_config(template_id)
    
    # 2. 构建提示词
    prompt = self.config_manager.build_prompt(
        template_id,
        query=query,
        user_profile=json.dumps(user_profile),
        response_hint=template.response_hint,
        mcp_tools_count=len(mcp_tools_called),
        retrieval_count=len(retrieval_results)
    )
    
    # 3. 调用LLM
    response = await call_llm(
        prompt=prompt,
        max_tokens=config.max_tokens,
        temperature=config.temperature
    )
    
    return response
```

---

## 📚 相关文档

- <!-- [步骤10-提示词构建与LLM参数配置](../03-代码参考/12.1-步骤10-提示词构建与LLM参数配置.md) (文档不存在) --> - 代码实现参考
- [步骤10-LLM响应优化使用指南](../35-步骤10-LLM响应优化使用指南.md) - 整体使用指南
- <!-- [LLM提示词优化方案](./33-LLM提示词优化方案.md) (文档不存在) --> - 完整优化方案

---

**维护者**: 薛小川  
**最后更新**: 2025-12-17
