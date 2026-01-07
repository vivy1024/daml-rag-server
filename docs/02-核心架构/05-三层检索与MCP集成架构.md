# 三层检索引擎与MCP工具集成架构

**版本**: v2.0.0  
**日期**: 2026-01-06  
**状态**: ✅ 已完成  

---

## 📋 概述

本文档详细说明DAML-RAG系统中**三层检索引擎**与**MCP工具**的集成架构，解释它们如何协同工作以提供智能健身推荐。

**v2.0.0更新**：
- Layer3规则引擎扩展至11条规则
- 新增动态上下文构建器（DynamicContextBuilder）
- 新增用户档案约束提取（Layer3Constraints）
- 向量模型从BGE-M3更换为GTE-Large-zh
- Layer1召回倍数从3倍提升至5倍
- 新增质量评估机制（min_confidence=0.70）

---

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAML-RAG 11步工作流程                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  【阶段1：LLM决策】步骤1-6.5                                       │
│  ├─ 步骤6.5: LLM选择DAG方案                                       │
│  └─ 输出: DAG模板ID + 工具列表                                    │
│                                                                   │
│  【阶段2：程序执行】步骤7-9  ⬅️ 本文档重点                         │
│  ├─ 步骤7: DAG编排器执行工具                                      │
│  │   ├─ 调用MCP工具（如intelligent_exercise_selector）           │
│  │   └─ MCP工具内部调用三层检索引擎                               │
│  ├─ 步骤8: 三层检索引擎执行                                       │
│  │   ├─ Layer1: Qdrant向量检索                                   │
│  │   ├─ Layer2: Neo4j图谱推理                                    │
│  │   └─ Layer3: Python业务规则                                   │
│  └─ 步骤9: 工具结果汇总                                           │
│                                                                   │
│  【阶段3：LLM综合】步骤10-11                                       │
│  └─ 步骤10: LLM基于真实数据进行专业分析                           │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🔧 核心组件关系

### 1. 三层检索引擎（TrueThreeLayerEngine）

**文件位置**: `src/framework/retrieval/true_three_layer_engine.py`

**核心职责**:
- 提供统一的检索接口
- 管理三层检索流程
- 处理降级和容错
- 提供性能监控

**关键方法**:
```python
class TrueThreeLayerEngine:
    async def execute_three_layer_query(
        self,
        query: str,                          # 查询文本
        domain: str = "fitness_exercises",   # 检索领域
        user_id: Optional[str] = None,       # 用户ID
        user_profile: Optional[Dict] = None, # 用户档案
        filters: Optional[Dict] = None,      # 过滤条件
        top_k: int = 10,                     # 返回数量
        safety_check: bool = True            # 安全检查
    ) -> ThreeLayerResult:
        """执行完整的三层检索"""
```

### 2. MCP工具基类（BaseMCPTool）

**文件位置**: `src/applications/fitness/mcp_tools/base_tool.py`

**核心职责**:
- 定义MCP工具标准接口
- 注入三层检索引擎依赖
- 提供通用工具方法
- 管理工具元数据

**依赖注入**:
```python
class BaseMCPTool:
    def __init__(
        self,
        neo4j_client,           # Neo4j客户端
        qdrant_client,          # Qdrant客户端
        three_layer_engine,     # ⭐ 三层检索引擎（核心依赖）
        user_profile_client,    # 用户档案客户端
        logger=None
    ):
        self.neo4j_client = neo4j_client
        self.qdrant_client = qdrant_client
        self.three_layer_engine = three_layer_engine  # ⭐ 注入
        self.user_profile_client = user_profile_client
        self.logger = logger or logging.getLogger(__name__)
```

### 3. 具体MCP工具（如IntelligentExerciseSelector）

**文件位置**: `src/applications/fitness/mcp_tools/exercise/intelligent_exercise_selector.py`

**核心职责**:
- 实现特定业务逻辑
- 调用三层检索引擎
- 处理检索结果
- 计算评分和排序

---

## 🔄 集成流程详解

### 步骤1：DAG编排器调用MCP工具

```python
# 在DAG编排器中
async def execute_tool(tool_name: str, params: dict):
    """执行MCP工具"""
    
    # 1. 从工具注册表获取工具实例
    tool = tool_registry.get_tool(tool_name)
    
    # 2. 工具实例已经注入了三层检索引擎
    # tool.three_layer_engine = TrueThreeLayerEngine(...)
    
    # 3. 调用工具的execute方法
    result = await tool.execute(params)
    
    return result
```

### 步骤2：MCP工具调用三层检索引擎

```python
# 在IntelligentExerciseSelector中
async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行智能动作选择"""
    
    # 1. 构建查询文本
    query_text = self._build_query_text(input_data, user_profile)
    # 例如: "推荐胸部训练动作，适合中级水平，可用器械：哑铃、杠铃"
    
    # 2. 准备过滤条件
    filters = {
        "available_equipment": input_data["available_equipment"],
        "difficulty_level": input_data["difficulty_level"],
        "rehabilitation_phase": input_data.get("rehabilitation_phase"),
        "force_type": input_data.get("force_type"),
        "postural_issues": input_data.get("postural_issues")
    }
    
    # 3. 调用三层检索引擎 ⭐ 核心调用
    retrieval_result = await self.three_layer_engine.execute_three_layer_query(
        query=query_text,
        domain="fitness_exercises",
        user_id=input_data.get("user_id"),
        user_profile=user_profile,
        filters=filters,
        top_k=20,  # 召回更多候选
        safety_check=True
    )
    
    # 4. 处理检索结果
    recommendations = self._process_results(retrieval_result)
    
    return recommendations
```

### 步骤3：三层检索引擎执行

```python
# 在TrueThreeLayerEngine中
async def execute_three_layer_query(...) -> ThreeLayerResult:
    """执行三层检索"""
    
    # ============ Layer 1: 向量语义检索 ============
    layer1_result = await self._execute_layer1_vector_search(
        query=query,
        domain=domain,
        top_k=top_k * 3,  # 召回更多候选
        filters=filters
    )
    # 调用: GraphRAG API → Qdrant向量数据库
    # 返回: 30个语义相似的动作
    
    # ============ Layer 2: 图谱关系推理 ============
    layer2_result = await self._execute_layer2_graph_reasoning(
        query=query,
        vector_results=layer1_result.results,
        top_k=top_k * 2,
        filters=filters
    )
    # 调用: Neo4j直连（优先）或 GraphRAG API（降级）
    # 查询: TARGETS_PRIMARY/SECONDARY关系、训练数据（MEV/MAV/MRV）
    # 过滤: 器械、难度、动力链、力类型、体态问题
    # 返回: 20个符合条件的动作
    
    # ============ Layer 3: 业务规则验证 ============
    layer3_result = await self._execute_layer3_business_rules(
        candidates=layer2_result.results,
        user_profile=user_profile,
        top_k=top_k,
        safety_check=safety_check
    )
    # 验证: 经验等级、安全性、器械可用性、训练容量
    # 返回: 10个最终推荐动作
    
    # ============ 构建最终结果 ============
    return ThreeLayerResult(
        query=query,
        final_results=layer3_result.results,
        layer_1_result=layer1_result,
        layer_2_result=layer2_result,
        layer_3_result=layer3_result,
        total_confidence=0.85,
        reasoning="三层检索完成: Layer1(30) → Layer2(20) → Layer3(10)"
    )
```

---

## 📊 数据流图

```
用户请求
   ↓
LLM选择DAG模板（步骤6.5）
   ↓
DAG编排器（步骤7）
   ↓
┌─────────────────────────────────────────────────────────┐
│  MCP工具: intelligent_exercise_selector                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │  1. 构建查询文本                                  │    │
│  │     "推荐胸部训练动作，中级，哑铃+杠铃"           │    │
│  │                                                   │    │
│  │  2. 准备过滤条件                                  │    │
│  │     {equipment: [哑铃, 杠铃], difficulty: 中级}  │    │
│  │                                                   │    │
│  │  3. 调用三层检索引擎 ⬇️                           │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  三层检索引擎: TrueThreeLayerEngine                      │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Layer 1: 向量语义检索（Qdrant）                 │    │
│  │  ├─ GraphRAG API调用                             │    │
│  │  ├─ 语义匹配: "胸部" → 胸大肌相关动作            │    │
│  │  └─ 返回: 30个候选动作                           │    │
│  └─────────────────────────────────────────────────┘    │
│                         ↓                                 │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Layer 2: 图谱关系推理（Neo4j）                  │    │
│  │  ├─ Neo4j直连查询（优先）                        │    │
│  │  ├─ 关系过滤:                                    │    │
│  │  │   - TARGETS_PRIMARY → 胸大肌                  │    │
│  │  │   - REQUIRES → 哑铃/杠铃                      │    │
│  │  │   - SUITABLE_FOR_LEVEL → 中级                 │    │
│  │  │   - HAS_KINETIC_CHAIN → 闭链（康复）          │    │
│  │  │   - USES_FORCE → 推力（力类型）               │    │
│  │  │   - CORRECTS → 圆肩（体态矫正）               │    │
│  │  ├─ 训练数据: MEV/MAV/MRV                        │    │
│  │  └─ 返回: 20个符合条件的动作                     │    │
│  └─────────────────────────────────────────────────┘    │
│                         ↓                                 │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Layer 3: 业务规则验证（Python）                 │    │
│  │  ├─ 规则1: 经验等级匹配                          │    │
│  │  │   用户中级 ✓ 动作中级 ✓                       │    │
│  │  ├─ 规则2: 安全性检查                            │    │
│  │  │   无禁忌症 ✓ 年龄适合 ✓                       │    │
│  │  ├─ 规则3: 器械可用性                            │    │
│  │  │   需要哑铃 ✓ 用户有哑铃 ✓                     │    │
│  │  ├─ 规则4: 训练容量合理性                        │    │
│  │  │   MEV/MAV/MRV数据完整 ✓                      │    │
│  │  └─ 返回: 10个最终推荐动作                       │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  返回: ThreeLayerResult                                  │
│  ├─ final_results: [10个动作]                            │
│  ├─ layer_1_result: 30个候选                             │
│  ├─ layer_2_result: 20个过滤后                           │
│  ├─ layer_3_result: 10个验证后                           │
│  └─ confidence: 0.85                                     │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  MCP工具: intelligent_exercise_selector                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │  4. 处理检索结果                                  │    │
│  │     ├─ 计算适配度评分                            │    │
│  │     ├─ 计算安全评分                              │    │
│  │     ├─ 生成推荐理由                              │    │
│  │     └─ 生成安全提醒                              │    │
│  │                                                   │    │
│  │  5. 返回结构化结果                                │    │
│  │     {                                             │    │
│  │       success: true,                              │    │
│  │       recommendations: [10个动作],                │    │
│  │       reasoning: "基于三层检索...",               │    │
│  │       safety_alerts: ["注意事项..."]              │    │
│  │     }                                             │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                         ↓
DAG编排器汇总结果（步骤9）
   ↓
LLM深度分析（步骤10）
   ↓
返回给用户
```

---

## 🔑 关键设计特性

### 1. 依赖注入模式

**优势**:
- 解耦：MCP工具不直接依赖具体实现
- 可测试：可以注入Mock对象进行单元测试
- 灵活：可以替换不同的检索引擎实现

**实现**:
```python
# 在工具注册时注入
tool_registry.register(
    "intelligent_exercise_selector",
    IntelligentExerciseSelector(
        neo4j_client=neo4j_client,
        qdrant_client=qdrant_client,
        three_layer_engine=three_layer_engine,  # ⭐ 注入
        user_profile_client=user_profile_client
    )
)
```

### 2. 连接池管理

**优势**:
- 性能：复用连接，减少建立连接开销
- 稳定：连接池自动管理连接生命周期
- 并发：支持多个工具并发访问

**实现**:
```python
# 三层检索引擎优先使用连接池
if self.connection_pool_manager and self.connection_pool_manager.neo4j_pool:
    async with self.connection_pool_manager.get_neo4j_session() as session:
        # 使用连接池中的会话
        result = await session.run(cypher_query, params)
```

### 3. 优雅降级策略

**Layer1降级**:
```
Layer1失败 → Layer2图谱检索 → 规则匹配 → 返回通用推荐
```

**Layer2降级**:
```
Neo4j直连失败 → GraphRAG API → 返回API结果
```

**完整降级链**:
```
三层检索 → 两层检索 → 一层检索 → 规则匹配 → 通用推荐
```

### 4. 重试机制

**Layer1重试**:
- 最多重试3次
- 指数退避：1s, 2s, 4s
- 详细日志记录

**实现**:
```python
for attempt in range(max_retries):
    try:
        if attempt > 0:
            await asyncio.sleep(retry_delay)
        
        result = await query_api()
        return result
    except Exception as e:
        if attempt == max_retries - 1:
            return fallback_result
        retry_delay *= 2  # 指数退避
```

---

## 📈 性能指标

### 数据规模

| 数据源 | 数量 | 说明 |
|--------|------|------|
| Qdrant向量（动作） | 1,790 | fitness_exercises_v2集合，与Neo4j完全同步 |
| Qdrant向量（食物） | 1,851 | food_nutrition_vector集合 |
| Qdrant向量（知识） | 43 | training_knowledge集合 |
| Neo4j节点 | 4,246 | Exercise、Muscle、Food等 |
| Neo4j关系 | 61,507 | 包含CONTRAINDICATED_FOR、INVOLVES_JOINT等 |

### 典型执行时间

| 层级 | 执行时间 | 说明 |
|------|---------|------|
| Layer1 | 50-200ms | Qdrant向量检索（1,790个动作向量） |
| Layer2 | 10-50ms | Neo4j图谱查询（直连） |
| Layer2 | 100-300ms | GraphRAG API（降级） |
| Layer3 | 5-20ms | Python规则验证（11条规则） |
| **总计** | **65-270ms** | **完整三层检索** |

### 并发性能

- **连接池大小**: 50个连接
- **并发工具数**: 10-20个
- **平均响应时间**: < 300ms
- **P95响应时间**: < 500ms

---

## 🛠️ 当前实现的MCP工具

### P0核心工具（使用三层检索）

1. **intelligent_exercise_selector** ⭐
   - 智能动作选择
   - 完整使用三层检索
   - 支持所有过滤条件

2. **contraindications_checker**
   - 禁忌症检查
   - 使用Layer2图谱关系
   - 查询CONTRAINDICATED_FOR关系

3. **injury_risk_assessor**
   - 损伤风险评估
   - 使用Layer2+Layer3
   - 安全性验证

4. **muscle_group_volume_calculator**
   - 肌群训练量计算
   - 使用Layer2训练数据
   - MEV/MAV/MRV查询

### P1建议工具（部分使用）

5. **exercise_alternative_finder**
   - 动作替代查找
   - 使用Layer2 VARIATION_OF关系

6. **movement_pattern_balancer**
   - 动作模式平衡
   - 使用Layer2 USES_FORCE关系

---

## 🔮 Layer3规则引擎详解（v2.0.0扩展至11条）

### 当前实现的规则

| 规则名称 | 类型 | 说明 | 状态 |
|---------|------|------|------|
| `kinetic_chain_rule` | 运动学 | 康复场景优先闭链动作 | ✅ v8.57.0 |
| `force_balance_rule` | 运动学 | 确保push:pull比例1:1到2:1 | ✅ v8.57.0 |
| `joint_load_rule` | 安全 | 排除涉及受伤关节的动作 | ✅ v8.57.0 |
| `recovery_time_rule` | 恢复 | 基于肌肉恢复时间推荐 | ✅ v8.57.0 |
| `postural_correction_rule` | 安全 | 推荐矫正动作，警告加重动作 | ✅ v8.57.0 |
| `body_type_constraint` | 用户档案 | 根据体型推荐动作 | ✅ v8.57.0 |
| `training_frequency_constraint` | 用户档案 | 训练频率约束 | ✅ v8.57.0 |
| `session_duration_constraint` | 用户档案 | 训练时长约束 | ✅ v8.57.0 |
| `goal_alignment_constraint` | 领域 | 目标对齐约束 | ✅ v8.57.0 |
| `progressive_overload_constraint` | 领域 | 渐进超负荷约束 | ✅ v8.57.0 |
| `nutrition_constraint` | 领域 | 营养约束 | ✅ v8.57.0 |

### Layer3Constraints数据类

```python
@dataclass
class Layer3Constraints:
    """用户档案约束提取结果"""
    # 基础信息
    age: int
    gender: str
    body_type: str
    fitness_level: str
    
    # 训练配置
    training_days_per_week: int
    session_duration_minutes: int
    available_equipment: List[str]
    
    # 健康状况
    injuries: List[str]
    medical_conditions: List[str]
    postural_issues: List[str]
    
    # 训练目标
    primary_goal: str
    target_muscles: List[str]
    
    # 计算属性
    body_type_preference: str  # 体型偏好
    goal_preference: str       # 目标偏好
    training_phase: str        # 训练阶段
    nutrition_status: str      # 营养状态
    frequency_strategy: str    # 频率策略
```

---

## 🔮 后续优化方向（已完成）

### ✅ 1. Layer3规则扩展（v8.57.0已完成）

**新增规则**:
- ✅ `kinetic_chain_rule`: 动力链规则（康复优先闭链）
- ✅ `force_balance_rule`: 推拉平衡规则（1:1到2:1）
- ✅ `joint_load_rule`: 关节负荷规则（排除受伤关节）
- ✅ `recovery_time_rule`: 恢复时间规则（基于肌肉恢复）
- ✅ `postural_correction_rule`: 体态矫正规则（推荐矫正动作）

### ✅ 2. 动态上下文构建（v8.57.0已完成）

**类似GraphRAG的LocalContextBuilder**:
- ✅ 实体-关系上下文构建
- ✅ 多跳推理支持（1-hop, 2-hop）
- ✅ 相关性评分计算（语义+实体+关系权重）
- ✅ 支持查询类型（local, hybrid, global）

### ✅ 3. 用户档案完整覆盖（v8.57.0已完成）

**确保所有字段被Layer3利用**:
- ✅ `basic_info`: age, height, weight, gender, body_type
- ✅ `fitness_config`: fitness_level, training_days_per_week
- ✅ `fitness_goals`: primary_goal, target_weight
- ✅ `health_profile`: injuries, medical_conditions, postural_issues
- ✅ `training_system`: personal_volume_multiplier, personal_recovery_factor
- ✅ `nutrition_profile`: daily_calories, protein_g

---

## 📝 总结

### 核心优势

1. **分层清晰**: 三层各司其职，互不耦合
2. **依赖注入**: MCP工具通过注入使用检索引擎
3. **优雅降级**: 多级降级策略保证可用性
4. **性能优异**: 连接池+缓存+并行优化
5. **易于扩展**: 新增MCP工具只需注入引擎

### 设计原则

- ✅ **单一职责**: 每层只做一件事
- ✅ **依赖倒置**: 依赖抽象而非具体实现
- ✅ **开闭原则**: 对扩展开放，对修改关闭
- ✅ **里氏替换**: 可以替换不同的检索引擎
- ✅ **接口隔离**: MCP工具只依赖需要的接口

---

**维护者**: Kiro AI  
**最后更新**: 2026-01-06  
**版本**: v2.0.0
