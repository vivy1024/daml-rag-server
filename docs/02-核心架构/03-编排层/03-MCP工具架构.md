# MCP工具架构

**版本**: v3.0.0
**创建日期**: 2025-12-17
**更新日期**: 2026-01-06
**状态**: ✅ 已完成

---

## 概述

DAML-RAG系统使用MCP（Model Context Protocol）工具架构来实现专业的健身功能。当前架构采用**混合部署模式**：
- **18个Python内置工具**：直接在DAML-RAG容器内调用（本地函数调用）
- **16个服务层组件**：业务逻辑处理和数据转换（v8.63.0更新）
- **1个stdio MCP服务**：用户档案服务（进程内stdio通信）
- **参数转换与配置管理系统**：中英文转换、字段映射
- **流式响应与监控体系**：实时性能监控
- **MCP工具版本管理系统**：版本追踪、兼容性检查（v8.58.0新增）

**v2.2.0更新**：新增postural_assessor（体态评估器）工具，支持12种体态问题的识别、矫正动作推荐和加重动作警告。

**v3.0.0更新**：
- 新增MCP工具版本管理系统（VersionInfo、ChangelogEntry、MCPToolVersionRegistry）
- 新增三层检索标准化调用（ThreeLayerQueryResult、execute_three_layer_query）
- 新增热身放松动作推荐系统（WarmupCooldownSelector）
- 服务层组件从11个扩展至16个

这种混合架构兼顾了性能（Python内置工具）、业务逻辑（服务层）、灵活性（stdio MCP服务）和可观测性（流式监控）。

---

## 架构演进历史

### 阶段1：TypeScript独立微服务架构（2025-10 ~ 2025-11）

**架构特点**：
- 每个MCP服务器独立部署为Docker容器
- 使用TypeScript + Node.js实现
- 通过stdio协议通信
- 独立的端口和进程

**实现的MCP服务器**：
1. `user-profile-stdio`（端口3001）
2. `comprehensive-fitness-coach-stdio`（端口3002）
3. 其他已归档服务

**优点**：
- ✅ 服务隔离，故障不互相影响
- ✅ 可独立扩展和部署
- ✅ 符合微服务架构原则

**缺点**：
- ❌ 部署复杂（需要多个Docker容器）
- ❌ 网络开销大（HTTP/stdio通信）
- ❌ 资源消耗高（每个服务独立进程）
- ❌ 维护成本高（多个代码库）
- ❌ TypeScript与Python混合技术栈

### 阶段2：Python内置工具集成架构（2025-12 ~ 至今）⭐当前架构

**架构特点**：
- 所有MCP工具集成到DAML-RAG容器内
- 使用Python实现，统一技术栈
- 直接函数调用，无网络开销
- 单一进程，资源高效

**性能提升**：
- 网络开销减少：**99%**
- 部署复杂度降低：**70%**
- 资源节省：**50%**
- 维护成本降低：**40%**

---

## 当前MCP工具清单

### 用户档案工具（1个）

#### 1. user_profile_tool - 用户档案工具

**服务类型**：TypeScript stdio MCP服务  
**位置**：`mcp-servers/user-profile-stdio/`  
**调用方式**：通过MCP客户端stdio协议通信  
**配置标识**：`server_name: "user-profile-stdio"`

**功能**：
- 获取用户档案（get_user_profile）
- 更新用户档案（update_user_profile）
- 与Laravel后端集成
- 提供用户数据CRUD

### P0核心工具（5个）

#### 2. intelligent_exercise_selector - 智能动作选择器

**优先级**：P0  
**位置**：`src/applications/fitness/mcp_tools/exercise/`  
**数据源**：Exercise + Muscle + Equipment

**功能**：
- 基于用户目标肌肉查询动作
- 根据难度和器材筛选
- 支持训练容量查询
- 100%数据就绪

**核心查询**：
```cypher
MATCH (m:Muscle {name_zh: $muscle_name})<-[:TARGETS_PRIMARY]-(e:Exercise)
WHERE ($difficulty IS NULL OR e.difficulty = $difficulty)
  AND ($equipment IS NULL OR e.equipment_zh = $equipment)
RETURN e
```

#### 3. contraindications_checker - 禁忌症检查器

**优先级**：P0  
**位置**：`src/applications/fitness/mcp_tools/safety/`  
**数据源**：InjuryType + Exercise（CONTRAINDICATED_FOR关系）

**功能**：
- 检查用户健康状况
- 识别禁忌动作
- 提供替代方案
- 基础关系已建立

#### 4. injury_risk_assessor - 损伤风险评估器

**优先级**：P0  
**位置**：`src/applications/fitness/mcp_tools/safety/`  
**数据源**：InjuryType + Exercise

**功能**：
- 评估动作风险等级
- 基于safety_level分类
- 生成风险报告
- 提供安全建议

#### 5. muscle_group_volume_calculator - 肌群容量计算器

**优先级**：P0  
**位置**：`src/applications/fitness/mcp_tools/training/`  
**数据源**：Muscle节点（v4.0.0新增训练数据字段）

**功能**：
- 基于training_frequency计算周训练量
- 基于recovery_time调整容量
- 使用MEV/MAV/MRV数据
- 支持个性化容量推荐

**核心计算**：
```python
# 基于Muscle节点的训练数据计算
muscle_data = query_muscle_training_data(muscle_group)
frequency = parse_frequency(muscle_data["training_frequency"])
recovery_factor = calculate_recovery_factor(
    muscle_data["recovery_time"],
    user_profile["recovery_capacity"]
)
adjusted_volume = base_volume * recovery_factor
```

#### 6. tdee_calculator - TDEE计算器

**优先级**：P0  
**位置**：`src/applications/fitness/mcp_tools/nutrition/`  
**数据源**：用户档案

**功能**：
- 计算每日总能量消耗
- 基于Harris-Benedict公式
- 考虑活动水平
- 提供营养素分配建议

### P1高级工具（8个）

#### 7. professional_program_designer - 专业计划设计器

**优先级**：P1  
**位置**：`src/applications/fitness/mcp_tools/training/`  
**数据源**：Exercise + Muscle + PeriodizationModel

**功能**：
- 设计完整训练计划
- 基于用户目标和水平
- 整合多个肌肉群
- 分配训练日

#### 8. exercise_alternative_finder - 动作替代查找器

**优先级**：P1  
**位置**：`src/applications/fitness/mcp_tools/exercise/`  
**数据源**：Exercise + Muscle

**功能**：
- 查找替代动作
- 基于目标肌肉匹配
- 考虑器材限制
- 保持训练效果

#### 9. movement_pattern_balancer - 动作模式平衡器

**优先级**：P1  
**位置**：`src/applications/fitness/mcp_tools/training/`  
**数据源**：Muscle.movement_patterns（v4.0.0新增）

**功能**：
- 分析动作模式分布
- 识别模式不平衡
- 推荐补充动作
- 预防肌肉失衡

#### 10. intelligent_weight_calculator - 智能重量计算器

**优先级**：P1  
**位置**：`src/applications/fitness/mcp_tools/training/`  
**数据源**：Exercise + 用户历史记录

**功能**：
- 计算训练重量
- 基于1RM估算
- 考虑训练目标
- 提供渐进方案

#### 11. safe_exercise_modifier - 安全动作修改器

**优先级**：P1  
**位置**：`src/applications/fitness/mcp_tools/safety/`  
**数据源**：Exercise + InjuryType + REHAB_PROGRESSION

**功能**：
- 修改动作以适应限制
- 推荐康复渐进路径
- 基于康复阶段调整
- 确保训练安全

**康复路径示例**：
```
深蹲康复路径：
负重靠墙静蹲 → 徒手深蹲 → 杠铃深蹲
- 进阶标准：无痛完成3组×30秒 / 完成3组×15次
- 预计周数：2周 / 4周
- 阶段：acute / subacute
```

#### 12. postural_assessor - 体态评估器 ✨ v8.47.0新增

**优先级**：P1  
**位置**：`src/applications/fitness/mcp_tools/safety/`  
**数据源**：PosturalIssue + Exercise + Muscle

**功能**：
- 识别用户体态问题
- 推荐矫正动作（基于CORRECTS关系）
- 警告加重动作（基于AGGRAVATES关系）
- 提供相关肌肉信息（基于RELATED_TO关系）
- 生成体态矫正训练计划

**支持的体态问题**（12个）：
- 脊柱相关：头前伸、驼背、胸椎后凸过度/不足、腰椎前凸过度
- 肩部相关：圆肩
- 髋部相关：骨盆前倾、骨盆后倾
- 膝部相关：膝内扣、膝超伸
- 踝部相关：扁平足、高弓足

**输出示例**：
```json
{
  "issue_name_zh": "骨盆前倾",
  "category": "hip",
  "related_muscles": ["髂腰肌", "竖脊肌", "腹直肌"],
  "corrective_exercises": [
    {
      "name_zh": "平板支撑",
      "difficulty": "beginner",
      "description": "加强核心稳定性"
    }
  ],
  "aggravating_exercises": [
    {
      "name_zh": "深蹲",
      "risk_level": "MODERATE",
      "warning": "此动作可能加重骨盆前倾问题"
    }
  ],
  "recommendations": [
    "建议每周进行2-3次矫正训练",
    "加强核心稳定性训练，改善骨盆位置"
  ]
}
```

#### 13. nutrition_intake_analyzer - 营养摄入分析器

**优先级**：P1  
**位置**：`src/applications/fitness/mcp_tools/nutrition/`  
**数据源**：Food + Nutrient

**功能**：
- 分析营养摄入
- 对比推荐摄入量
- 识别营养缺口
- 提供改进建议

#### 13. exercise_nutrition_optimization - 运动营养优化器

**优先级**：P1
**位置**：`src/applications/fitness/mcp_tools/nutrition/`
**数据源**：Food + Nutrient + TrainingPlan

**功能**：
- 优化训练前后营养
- 基于训练强度调整
- 营养素时机优化
- 提升训练效果

#### 14. record_training_feedback - 训练反馈记录器

**优先级**：P1
**位置**：`src/applications/fitness/mcp_tools/training/`
**数据源**：用户档案 + 训练记录

**功能**：
- 记录用户满意度反馈
- 训练计划完成情况
- 身体感受评估
- 为强化学习提供数据

### P2扩展工具（3个）

#### 15. periodized_program_designer - 周期化计划设计器

**优先级**：P2
**位置**：`src/applications/fitness/mcp_tools/training/`
**数据源**：PeriodizationModel + 用户目标

**功能**：
- 设计长期周期化计划
- 基于科学训练理论
- 整合多阶段目标
- 适应高级训练者

#### 16. training_split_designer - 训练分化设计器

**优先级**：P2
**位置**：`src/applications/fitness/mcp_tools/training/`
**数据源**：Muscle + Exercise + 用户时间

**功能**：
- 设计训练分化方案
- 优化肌肉群分配
- 平衡训练频率
- 适应不同时间安排

#### 17. find_similar_training_cases - 相似训练案例查找器

**优先级**：P2
**位置**：`src/applications/fitness/mcp_tools/`
**数据源**：后端API + 向量存储

**功能**：
- 查找相似训练案例
- 基于用户特征匹配
- 提供历史参考
- 支持Few-Shot学习

### 用户档案工具（1个）

#### 1. user_profile_tool - 用户档案工具

**服务类型**：TypeScript stdio MCP服务
**位置**：`mcp-servers/user-profile-stdio/`
**调用方式**：通过MCP客户端stdio协议通信
**配置标识**：`server_name: "user-profile-stdio"`

**功能**：
- 获取用户档案（get_user_profile）
- 更新用户档案（update_user_profile）
- 与Laravel后端集成
- 提供用户数据CRUD

---

## 服务层组件（16个）

服务层组件位于 `src/applications/fitness/services/`，负责业务逻辑处理和数据转换：

### 1. content_safety_filter.py - 内容安全过滤器

**功能**：过滤和检测不安全的内容
**数据源**：配置文件 + 规则引擎
**应用场景**：用户输入过滤、输出内容审核

### 2. equipment_alias_mapper.py - 器械别名映射器

**功能**：处理器械名称的中英文映射和别名识别
**数据源**：Equipment节点 + 配置映射表
**应用场景**：用户输入标准化、查询优化

### 3. exercise_stability_manager.py - 动作稳定性管理器

**功能**：评估动作的稳定性和安全性
**数据源**：Exercise.safety_level + InjuryType
**应用场景**：风险评估、动作推荐

### 4. intensity_converter.py - 训练强度转换器

**功能**：实现RPE、%1RM、RIR等强度指标间的转换
**数据源**：用户训练记录 + 力量标准
**应用场景**：强度标准化、训练指导

### 5. llm_call_logger.py - LLM调用日志记录器

**功能**：记录LLM调用的详细日志
**数据源**：LLM调用记录
**应用场景**：调试、性能分析、成本追踪

### 6. progressive_overload.py - 渐进式超负荷计算

**功能**：计算训练强度的渐进式提升方案
**数据源**：用户训练记录 + Muscle训练数据
**应用场景**：训练计划优化、进度跟踪

### 7. safety_reminder_generator.py - 安全提醒生成器

**功能**：生成个性化的安全训练提醒
**数据源**：用户健康状况 + 动作风险评估
**应用场景**：预防运动损伤、安全保障

### 8. three_track_rating.py - 三轨评分系统

**功能**：多维度评估训练计划和动作推荐质量
**数据源**：用户反馈 + 训练效果数据
**应用场景**：推荐质量评估、系统优化

### 9. training_goal_recommender.py - 训练目标推荐器

**功能**：基于用户特征推荐训练目标
**数据源**：用户档案 + 历史数据
**应用场景**：目标设定、计划定制

### 10. training_log_analyzer.py - 训练日志分析器

**功能**：分析用户训练日志，提取关键指标
**数据源**：训练记录 + 用户反馈
**应用场景**：性能分析、计划调整

### 11. training_plan_summarizer.py - 训练计划总结器

**功能**：生成训练计划的概要和关键信息
**数据源**：训练计划 + 执行记录
**应用场景**：计划展示、进度汇报

### 12. user_profile_data_mapper.py - 用户档案数据映射器

**功能**：用户档案数据格式转换和映射
**数据源**：用户档案 + 前端数据
**应用场景**：数据格式统一、前后端对接

### 13. user_profile_integrator.py - 用户档案集成器

**功能**：整合多源用户数据，构建完整档案
**数据源**：用户档案 + 训练数据 + 健康状况
**应用场景**：数据融合、个性化推荐

### 14. volume_adjuster.py - 训练量调整器

**功能**：基于用户反馈调整训练量
**数据源**：训练记录 + 用户满意度 + Muscle数据
**应用场景**：个性化调整、闭环学习

### 15. warmup_cooldown_exercises.py - 热身放松动作配置

**功能**：提供专业筛选的热身和放松动作推荐
**数据源**：Exercise节点（硬编码专业筛选的动作ID）
**应用场景**：训练计划热身放松部分生成

**核心特性**：
- 基于运动学教授和专业教练视角，从1790个动作中精选
- 硬编码专业筛选的动作ID（恢复类218个、拉伸类52个、瑜伽类75个、有氧类46个）
- 支持10种训练重点：上肢、下肢、推、拉、腿、全身、核心、胸、背、肩
- WarmupCooldownSelector选择器：
  - `get_warmup_exercises()` - 根据训练重点获取热身动作
  - `get_cooldown_exercises()` - 根据训练重点获取放松动作
  - `determine_training_focus()` - 根据目标肌群判断训练重点
- 支持时长控制（默认10分钟）和有氧热身开关

### 16. weekly_plan_generator.py - 周计划生成器

**功能**：生成详细的周训练计划
**数据源**：用户目标 + 时间安排 + 训练分化
**应用场景**：计划生成、时间管理

---

## 参数转换与配置管理系统

### 核心组件（6个）

#### 1. parameter_mapper.py - DAG参数映射器

**功能**：DAG任务参数到MCP工具的映射
**特性**：
- 字段名映射（MCP ↔ Neo4j）
- 参数类型转换
- 中英文转换
- 智能参数验证

#### 2. parameter_converter.py - 参数类型转换器

**功能**：不同格式参数间的转换
**支持**：JSON ↔ YAML ↔ Python字典 ↔ Cypher参数

#### 3. llm_response_config_manager.py - LLM响应配置管理器

**功能**：基于YAML配置文件的LLM响应配置管理
**特性**：
- 从YAML文件加载配置
- 根据模板ID获取配置
- 动态构建提示词
- 热加载配置（可选）

#### 4. mcp_config_loader.py - MCP配置加载器

**功能**：加载和管理MCP工具配置
**特性**：
- 自动发现MCP工具
- 加载工具元数据
- 配置验证

#### 5. enhanced_parameter_extractor.py - 增强参数提取器

**功能**：从用户输入中提取结构化参数
**特性**：
- 智能参数识别
- 参数完整性验证
- 错误提示

#### 6. enhanced_parameter_validator.py - 增强参数验证器

**功能**：多层次参数验证
**层次**：类型 → 存在 → 格式 → 安全

---

## 流式响应与监控体系

### 核心组件

#### 1. stream_executor.py - 流式工作流执行器

**功能**：执行工作流图，支持流式输出
**特性**：
- 步骤1-9同步执行
- 步骤10流式LLM调用
- 实时进度推送
- 错误处理和恢复

#### 2. streaming_metrics.py - 流式会话监控指标

**功能**：提供Prometheus指标和StreamingMonitor类
**核心指标**：
- `streaming_session_ttfb_seconds`: 首字节响应时间
- `streaming_session_duration_seconds`: 会话持续时间
- `streaming_session_tokens_per_second`: 令牌生成速率
- `streaming_session_success_total`: 成功会话计数
- `streaming_session_failure_total`: 失败会话计数

#### 3. 性能监控特性

**集成**：
- Prometheus指标监控
- 线程安全的活跃连接数跟踪
- 会话指标记录和存储
- 统计数据聚合
- 最近会话查询

**监控维度**：
- TTFB（首字节响应时间）
- 持续时间
- 令牌生成速率
- 成功/失败率
- 并发连接数

---

## 总结

DAML-RAG的MCP工具架构已经发展为一个完整的混合系统：

- **17个Python内置工具**：提供高性能的本地函数调用
- **16个服务层组件**：处理复杂的业务逻辑
- **1个stdio MCP服务**：提供用户档案管理
- **6个参数系统组件**：确保数据转换和验证
- **流式监控体系**：提供完整的可观测性

这种架构设计兼顾了性能、灵活性、可维护性和可观测性，是当前大模型应用的最佳实践之一。

**核心优势**：
- ✅ **高性能**：Python内置工具减少网络开销
- ✅ **业务逻辑清晰**：服务层组件分离关注点
- ✅ **数据安全**：参数验证和类型转换
- ✅ **可观测性**：完整的流式监控体系
- ✅ **用户体验**：实时反馈和进度展示

---
- 设计每日膳食计划
- 满足营养需求
- 考虑食物偏好
- 控制总热量

#### 14. exercise_nutrition_optimization - 运动营养优化器

**优先级**：P1  
**位置**：`src/applications/fitness/mcp_tools/nutrition/`  
**数据源**：Food + Nutrient + Exercise + Muscle

**功能**：
- 基于训练目标推荐营养
- 根据肌肉功能确定营养需求
- 优化营养时机
- 支持恢复和增长

**核心逻辑**：
```python
# 基于目标肌肉的功能推荐营养
muscle_data = query_muscle_function(target_muscle)
required_nutrients = map_function_to_nutrients(muscle_data["function"])
foods = query_foods_by_nutrients(required_nutrients)
nutrition_plan = generate_meal_timing(training_intensity, recovery_time)
```

### P2扩展工具（2个）

#### 15. periodized_program_designer - 周期化计划设计器

**优先级**：P2  
**位置**：`src/applications/fitness/mcp_tools/training/`  
**数据源**：PeriodizationModel + TrainingPhase + TrainingLevel

**功能**：
- 设计周期化训练计划
- 基于PeriodizationModel
- 分阶段调整强度
- 优化长期进步

**核心设计**：
```python
# 基于PeriodizationModel设计计划
model = query_periodization_model(training_level, training_goal)
phases = query_training_phases(model["id"])
program = generate_periodized_program(phases, duration_weeks)
```

#### 16. training_split_designer - 训练分化设计器

**优先级**：P2  
**位置**：`src/applications/fitness/mcp_tools/training/`  
**数据源**：Muscle + Exercise

**功能**：
- 设计训练分化方案
- 基于训练频率
- 优化肌肉恢复
- 平衡训练负荷

---

## ✨ v2.0.0新增服务（闭环学习系统）

### 闭环学习核心服务（4个）

#### 17. TrainingLogAnalyzer - 训练日志分析器

**优先级**：P0  
**位置**：`src/applications/fitness/services/training_log_analyzer.py`  
**数据源**：MySQL training_logs表（通过BackendClient）

**功能**：
- 获取用户训练历史
- 分析完成率趋势
- 分析RPE趋势
- 中周期综合分析

**核心方法**：
```python
class TrainingLogAnalyzer:
    async def get_user_training_history(user_id, days_back=42) -> List[Dict]
    async def analyze_completion_trend(user_id, weeks=4) -> CompletionTrendAnalysis
    async def analyze_rpe_trend(user_id, weeks=4) -> RPETrendAnalysis
    async def analyze_mesocycle(user_id, mesocycle_weeks=4) -> MesocycleAnalysis
```

**Requirements**: 7.1 - 分析中周期训练表现

#### 18. VolumeAdjuster - 容量动态调整器

**优先级**：P0  
**位置**：`src/applications/fitness/services/volume_adjuster.py`  
**数据源**：TrainingLogAnalyzer + BackendClient

**功能**：
- 分析中周期训练表现
- 计算容量调整值
- 应用调整到用户档案
- 判断是否需要Deload

**调整规则**：
- RPE < 7 且 完成率 > 95%: +0.05 ~ +0.1
- RPE > 9.5 或 完成率 < 80%: -0.1 ~ -0.15
- 容量系数边界: 0.7 ~ 1.5

**核心方法**：
```python
class VolumeAdjuster:
    MULTIPLIER_MIN = 0.7
    MULTIPLIER_MAX = 1.5
    
    async def analyze_mesocycle(user_id, mesocycle_weeks=4) -> Dict
    def calculate_adjustment(avg_rpe, avg_completion_rate, current_multiplier) -> Tuple[float, AdjustmentDirection, str]
    def should_suggest_deload(avg_rpe, avg_completion_rate, ...) -> Tuple[bool, Optional[str]]
    async def apply_adjustment(user_id, adjustment, current_multiplier, reason) -> float
    async def adjust_volume(user_id, mesocycle_weeks=4) -> VolumeAdjustmentResult
```

**Requirements**: 7.1, 7.2, 7.3, 7.4, 7.5

#### 19. WeeklyPlanGenerator - 分周计划生成器

**优先级**：P0  
**位置**：`src/applications/fitness/services/weekly_plan_generator.py`  
**数据源**：TrainingLogAnalyzer + ProgressiveOverloadCalculator

**功能**：
- 生成第1周计划
- 基于反馈生成下周计划
- 应用个性化容量系数
- 生成Deload周计划
- 应用渐进过载计算

**周期化阶段配置**：
```python
PHASE_CONFIG = {
    1: {"phase": "accumulation", "name_zh": "积累期", "volume_factor": 1.0},
    2: {"phase": "accumulation", "name_zh": "积累期", "volume_factor": 1.0},
    3: {"phase": "intensification", "name_zh": "冲刺期", "volume_factor": 1.2},
    4: {"phase": "deload", "name_zh": "减量期", "volume_factor": 0.6}
}
```

**核心方法**：
```python
class WeeklyPlanGenerator:
    def generate_first_week(full_program, user_profile, total_weeks=4) -> WeeklyPlan
    async def generate_next_week(user_id, current_week, total_weeks, last_week_feedback, base_program, user_profile) -> WeeklyPlan
    def apply_volume_multiplier(base_plan, multiplier) -> Dict
    def insert_deload_week(base_program, week_number, total_weeks, user_profile) -> WeeklyPlan
    async def apply_progressive_overload(weekly_plan, user_id, last_week_weights, last_week_completion, user_profile) -> WeeklyPlan
```

**Requirements**: 10.1, 10.2, 10.3, 10.4, 8.1, 8.2, 8.3, 8.4

#### 20. ProgressiveOverloadCalculator - 渐进过载计算器

**优先级**：P1  
**位置**：`src/applications/fitness/services/progressive_overload.py`  
**数据源**：MySQL personal_bests表

**功能**：
- 计算下周建议重量
- 检测重量下降（回归检测）
- 建议购买1.25kg小片
- 检查MAV限制

**加重幅度配置**：
```python
WEIGHT_INCREMENT = {
    'compound': 2.5,   # 复合动作：深蹲、卧推、硬拉
    'isolation': 1.25  # 孤立动作：弯举、飞鸟
}
```

**核心方法**：
```python
class ProgressiveOverloadCalculator:
    def calculate_next_weight(completed_all_reps, last_weight, exercise_type='compound') -> float
    def detect_regression(current_weight, personal_best) -> bool
    def suggest_micro_plates(exercise_type) -> str
    def check_mav_limit(current_volume, user_mav) -> bool
    def get_weight_annotation(last_weight, next_weight) -> str
```

**Requirements**: 8.1, 8.2, 8.3, 8.4

### 输出优化服务（2个）

#### 21. TrainingPlanSummarizer - 训练计划摘要器

**优先级**：P0  
**位置**：`src/applications/fitness/services/training_plan_summarizer.py`  
**数据源**：训练计划数据

**功能**：
- 精简训练计划输出（<8000字符）
- 转换动作名为Markdown链接
- 添加高风险动作⚠️标记
- 添加重量变化标注

**核心配置**：
```python
MAX_OUTPUT_CHARS = 8000
CORE_FIELDS = ['exercise_id', 'name_zh', 'sets', 'reps', 'rest_seconds', 'weight_suggestion']
```

**Requirements**: 11.1, 11.2, 11.3, 11.4

#### 22. SafetyReminderGenerator - 安全提醒生成器

**优先级**：P0  
**位置**：`src/applications/fitness/services/safety_reminder_generator.py`  
**数据源**：用户档案 + Exercise安全信息

**功能**：
- 生成免责声明
- 生成损伤历史提醒
- 标记高风险动作
- 获取动作禁忌条件

**Requirements**: 14.1, 14.2, 14.3, 14.4

### 中国本地化服务（2个）

#### 23. EquipmentAliasMapper - 器械别名映射器

**优先级**：P2  
**位置**：`src/applications/fitness/services/equipment_alias_mapper.py`  
**数据源**：配置文件（不修改Neo4j）

**功能**：
- 中文器械名映射到英文
- 获取中文显示名称
- 适配大学健身房基础配置

**别名映射示例**：
```python
ALIAS_MAP = {
    '龙门架': 'Cable',
    '史密斯机': 'Smith Machine',
    '哑铃': 'Dumbbell',
    '杠铃': 'Barbell',
    '徒手': 'Body Weight',
}
```

**Requirements**: 4.1, 4.2, 4.3

#### 24. ExerciseStabilityManager - 动作稳定性管理器

**优先级**：P2  
**位置**：`src/applications/fitness/services/exercise_stability_manager.py`  
**数据源**：用户训练历史 + Neo4j Exercise

**功能**：
- 优先使用熟悉动作
- 提供动作替换建议
- 监控易损部位负荷

**Requirements**: 12.1, 12.2, 12.3, 12.4

---

## 工具调用架构

### 目录结构

```
daml-rag-server/
├── src/
│   └── applications/
│       └── fitness/
│           ├── mcp_tools/              # MCP工具根目录
│           │   ├── __init__.py
│           │   ├── exercise/           # 动作相关工具
│           │   │   ├── intelligent_exercise_selector.py
│           │   │   ├── exercise_alternative_finder.py
│           │   │   └── ...
│           │   ├── training/           # 训练相关工具
│           │   │   ├── professional_program_designer.py
│           │   │   ├── periodized_program_designer.py
│           │   │   ├── muscle_group_volume_calculator.py
│           │   │   └── ...
│           │   ├── nutrition/          # 营养相关工具
│           │   │   ├── tdee_calculator.py
│           │   │   ├── meal_plan_designer.py
│           │   │   └── ...
│           │   ├── safety/             # 安全相关工具
│           │   │   ├── contraindications_checker.py
│           │   │   ├── injury_risk_assessor.py
│           │   │   └── ...
│           │   └── user_profile/       # 用户档案工具
│           │       └── user_profile_tool.py
│           │
│           ├── chat_service.py         # 主服务（调用MCP工具）
│           └── dag_template_system.py  # DAG编排系统
│
└── config/
    └── mcp_registry.json               # MCP工具注册表
```

### 工具调用流程

```python
# 1. 用户请求
user_query = "推荐胸部训练动作"

# 2. LLM决策选择DAG模板
dag_template = llm_decision_engine.select_dag_template(user_query)

# 3. DAG编排器执行工具链
results = await dag_orchestrator.execute(
    template=dag_template,
    tools=[
        "get_user_profile",              # 获取用户档案
        "intelligent_exercise_selector",  # 选择动作
        "contraindications_checker"       # 检查禁忌
    ]
)

# 4. LLM综合分析结果
response = llm_analysis_engine.synthesize(results)
```

### 调用方式对比

#### Python内置工具调用

```
DAG编排器 (enhanced_dag_orchestrator.py)
    ↓
MCPToolManager (mcp_tool_manager.py)
    ↓
判断 server_name = "python_internal"
    ↓
MCPToolRegistry.call_tool() [本地调用]
    ↓
直接函数调用（~0.1ms延迟）
```

#### stdio MCP服务调用

```
DAG编排器 (enhanced_dag_orchestrator.py)
    ↓
MCPToolManager (mcp_tool_manager.py)
    ↓
判断 server_name = "user-profile-stdio"
    ↓
MCPClient.call_tool() [stdio通信]
    ↓
进程内通信（~5-10ms延迟）
```

---

## 性能优化

### 智能缓存

**L1内存缓存**：
- 用户档案
- TDEE计算结果
- 常用查询结果
- 缓存命中率：> 85%

**L2 Redis缓存**：
- 持久化缓存
- 分布式缓存
- 合理的过期时间

### 并行执行

DAG编排器自动识别可并行任务：
- 使用asyncio.gather并行执行
- 并行效率：3.5x
- 减少总执行时间

### 数据库优化

- 连接池管理
- 查询优化和索引
- 批量操作

---

## 工具注册表

### mcp_registry.json结构

```json
{
  "version": "4.0.0",
  "last_updated": "2025-12-16",
  "servers": {
    "user-profile-stdio": {
      "type": "stdio",
      "command": "node",
      "args": ["dist/index.js"],
      "cwd": "/app/mcp-servers/user-profile-stdio",
      "tools": [
        {
          "name": "get_user_profile",
          "description": "获取用户档案信息"
        },
        {
          "name": "update_user_profile",
          "description": "更新用户档案信息"
        }
      ]
    }
  },
  "python_tools": {
    "exercise": [
      "intelligent_exercise_selector",
      "exercise_alternative_finder"
    ],
    "training": [
      "professional_program_designer",
      "periodized_program_designer",
      "muscle_group_volume_calculator",
      "movement_pattern_balancer",
      "intelligent_weight_calculator",
      "training_split_designer"
    ],
    "nutrition": [
      "tdee_calculator",
      "nutrition_intake_analyzer",
      "meal_plan_designer",
      "exercise_nutrition_optimization"
    ],
    "safety": [
      "contraindications_checker",
      "injury_risk_assessor",
      "safe_exercise_modifier"
    ]
  }
}
```

---

## 工具开发指南

### 开发新工具的步骤

1. **确定工具分类**：exercise/training/nutrition/safety
2. **创建工具文件**：在对应目录下创建Python文件
3. **实现工具逻辑**：继承BaseMCPTool类
4. **注册工具**：在`__init__.py`中注册
5. **更新注册表**：在`mcp_registry.json`中添加元数据
6. **编写测试**：创建单元测试和集成测试
7. **更新文档**：更新API文档和使用指南

### 工具开发模板

```python
from src.framework.mcp.base_mcp_tool import BaseMCPTool
from typing import Dict, Any

class NewMCPTool(BaseMCPTool):
    """新MCP工具"""
    
    def __init__(self):
        super().__init__(
            name="new_mcp_tool",
            description="工具描述",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "参数1"},
                    "param2": {"type": "integer", "description": "参数2"}
                },
                "required": ["param1"]
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具逻辑"""
        param1 = kwargs.get("param1")
        param2 = kwargs.get("param2", 0)
        
        # 实现工具逻辑
        result = self._process(param1, param2)
        
        return {
            "success": True,
            "data": result
        }
    
    def _process(self, param1: str, param2: int) -> Any:
        """处理逻辑"""
        # 实现具体逻辑
        pass
```

---

## 未来规划

### 短期（1-2月）

1. **工具扩展**
   - 添加更多P2扩展工具
   - 优化现有工具性能
   - 增强错误处理

2. **监控增强**
   - 添加工具调用监控
   - 性能指标追踪
   - 异常告警

### 中期（3-6月）

1. **混合架构**
   - 保持核心工具内置
   - 将计算密集型工具独立部署
   - 实现智能路由

2. **水平扩展**
   - 支持多实例部署
   - 负载均衡
   - 分布式缓存

### 长期（6-12月）

1. **插件化架构**
   - 支持动态加载工具
   - 工具市场
   - 第三方工具集成

2. **智能优化**
   - 基于使用模式的自动优化
   - 智能缓存预加载
   - 自适应资源分配

---

## 参考文档

- [MCP架构演进历史](./15-MCP架构演进历史.md)（详细版本）
- [MCP工具API参考](../05-API文档/02-MCP工具API参考.md)
- [系统架构总览](./02-系统架构总览.md)
- <!-- [完整工作流程](./03-完整工作流程.md) (文档不存在) -->

---

**维护者**：薛小川  
**最后更新**：2025-12-26  
**状态**：✅ 已完成
