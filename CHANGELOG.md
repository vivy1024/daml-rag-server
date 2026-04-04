# daml-rag-server 构建日志

> 内部构建号，不对外发布。产品版本见根仓库 `CHANGELOG.md`。
> 历史版本（v9.88.0 及之前）已归档至 `CHANGELOG-legacy.md`。

---

## #54 (feat) Harness v1 — 确定性执行壳层 8 模块 — 2026-04-05

**REQ-1 路由分流**: `workflow/nodes/step7_execute_dag.py`
  - 在 DAG 执行前后插入 harness 管道钩子（策略→执行→校验→追踪）
  - 完全由 HarnessConfig feature flag 控制，关闭时零行为变更
  - harness 初始化失败自动回退旧路径（静默降级）

**REQ-2 执行策略**: `harness/execution_policy.py` (280行)
  - `ExecutionPolicy.check_pre_template()` fail-closed 安全检查
  - `TemplateRiskLevel` 三级风险分级 (HIGH/MEDIUM/LOW)
  - HIGH 模板在用户有 health_conditions 时强制要求 contraindications_checker + injury_risk_assessor

**REQ-3 上下文包**: `harness/context_packet_builder.py` (330行)
  - 9 层固定槽位上下文组装（system_rules → retrieved_knowledge）
  - 独立 token 预算与自动截断
  - `hard_constraints` 层标记 compressible=False，绝不压缩

**REQ-4 记忆 Schema v2**: `services/user_memory.py` (+90行)
  - `MemoryCategory` 6 类细分: PREFERENCE/HARD_CONSTRAINT/OUTCOME_PATTERN/COACH_DECISION/FAILURE_CASE/SESSION_FACT
  - 置信度评分、来源追踪、TTL 过期机制
  - `recall_constraints()` 专用接口 + v1 兼容映射 `_normalize_category()`

**REQ-5 MCP 三层化**: `mcp_resources/` + `mcp_prompts/`
  - `MCPResourceRegistry`: 9 个 URI 可寻址资源 (fitness://rules/* + fitness://data/*)
  - `MCPPromptRegistry`: 4 个预制模板 (training-plan-synthesis/safety-assessment/nutrition-plan/harness-fallback)

**REQ-6 输出校验**: `harness/output_verifier.py` (310行)
  - 5 维度纯 Python 确定性校验: safety_conflict/equipment_mismatch/duration_exceeded/volume_overload/goal_mismatch
  - safety_conflict 使用关键词交集匹配（中文2字子串拆分）
  - critical 失败阻止输出，warning 放行

**REQ-7 追踪器**: `harness/harness_tracer.py` (160行)
  - 结构化 `HarnessTrace` 记录各阶段耗时、策略判定、工具执行、验证结果

**REQ-8 灰度配置**: `config/runtime.py` (+44行)
  - `HarnessConfig` dataclass: 主开关 + 6 个子开关 (policy/verifier/tracer/memory_v2/context_packet)
  - `is_active_for(template_id, user_id)` 白名单灰度
  - 支持 YAML 配置文件 + 环境变量覆盖

- 容器内全部组件导入 + 烟雾测试通过 (test_harness_smoke.py + test_mcp_three_layer.py)

---

## #53 (feat) Phase 4 长期改进 — OpenTelemetry + pyproject.toml — 2026-03-06

- **OpenTelemetry 基础集成 (REQ-11)**: `framework/monitoring/tracing.py`
  - `init_tracing()` 初始化 TracerProvider + ConsoleSpanExporter
  - `get_tracer()` 工具函数，管线步骤使用 `with get_tracer().start_as_current_span()`
  - `instrument_fastapi()` 自动追踪 FastAPI 请求
  - `api/main.py` 启动时自动初始化，失败不影响服务
- **管线步骤 Span 注入 (REQ-11)**: `stream_executor_pipeline.py`
  - 所有步骤方法包裹 `start_as_current_span`: step_1_2, step_3, step_3_4, step_5, step_6, step_6_5, step_7_8, step_9, step_11
  - 每个 span 记录 request_id 和 user_id
- **依赖管理 (REQ-12)**: 新增 `pyproject.toml` (hatchling build system)
  - `[project.dependencies]` 对齐 requirements.txt
  - `[project.optional-dependencies.dev]` 对齐 requirements-dev.txt
  - Dockerfile 添加 uv 迁移注释（未正式迁移，保留 requirements.txt）
- **代码清理**: `monitoring/__init__.py` 简化、`tests/conftest.py` 精简为 sys.path 设置
- 验证：427 单元测试通过

---

## #52 (test) Phase 3 测试加强 — adapter集成测试 + 检索测试 + Chaos测试 — 2026-03-06

- **fitness_adapter 集成测试 (REQ-8)**: `tests/integration/test_fitness_adapter.py` — 40 用例
  - 基础 API (7) + Layer3 规则 (6) + DAG 模板 (8) + MCP 工具 (7) + 领域数据 (7) + 初始化 (3) + 集成 (2)
- **三层检索引擎单元测试 (REQ-9)**: `tests/unit/framework/test_three_layer_engine.py` — 24 用例
  - Layer1 向量检索 (3) + Layer2 图检索 (3) + Layer3 规则 (7) + 结果融合 (2) + 降级 (2) + 空查询 (1) + 统计 (1) + 关键词 (2)
  - 修复 aiohttp mock: `async with ClientSession` 双层上下文管理器正确 mock
  - 修复 `test_match_fitness_level_advanced_rejects_beginner` 断言（advanced 用户不接受 beginner 难度）
- **Chaos Engineering 测试 (REQ-10)**: `tests/integration/test_chaos_engineering.py` — 8 用例
  - Redis 断连 (2) + Neo4j 超时 (2) + LLM 全故障 (2) + Qdrant 不可用 (2)
  - 修复 aiohttp mock 与三层检索测试一致
- 验证：427 单元测试通过（1 failed 为已知预存问题 test_safety_check_scenario）

---

## #51 (refactor) Phase 2 架构优化 — env集中化 + 步骤条件化 — 2026-03-06

- **环境变量集中化 (REQ-6)**: 100+ 处 `os.getenv` → `get_config()` 迁移
  - api/ 目录: 61 处 (main.py, logging_config, auth_middleware, security, routes/*)
  - framework/ 目录: 33 处 (container, neo4j_client, three_layer/engine, cypher_templates, kg_full 等)
  - applications/ 目录: 6 处 (step4/step5, stream_executor_pipeline, credit_reporter, user_memory)
  - 保留约 30 处（动态 API KEY 池化、ENCRYPTION_KEY 等无法 config 化的场景）
- **三层检索引擎拆分 (REQ-5)**: 确认已在早期迭代完成
  - engine.py (278行) + layer1_vector (170) + layer2_graph (438) + layer3_rules (346) + result_merger (100) + fallback (85) + neo4j_manager (98) + models (33)
  - 主文件 true_three_layer_engine.py 缩减为 39 行别名
- **步骤条件化 (REQ-7)**: DUAL_MODEL_ENABLED=false 时管线跳过步骤 4/5
  - 新增 `_is_dual_model_enabled()` + `_execute_step_3_only()` 方法
  - 步骤 4/5 不再被调用（之前是调用后内部立即返回默认值）
- 验证：403 单元测试通过

---

## #50 (refactor) Phase 1 代码质量治理 — nodes拆分 + stream_executor Mixin + except收窄确认 — 2026-03-05

对应产品版本：v1.6.8

- **nodes.py 拆分** (commit 457cc95): 1641行 → 12个独立步骤文件 + `__init__.py` re-export
  - `workflow/nodes/` 子包：step1~step11 + constants.py
  - 所有相对 import 从 `from .state import` 改为 `from ..state import`
  - 删除旧 `workflow/nodes.py`，所有外部引用兼容
- **stream_executor.py Mixin 拆分** (commit 70c9056): 1518行 → 170行主类 + 3个 Mixin
  - `stream_executor_pipeline.py` (PipelineMixin): execute_stream + 步骤1-9 + 步骤11
  - `stream_executor_llm.py` (LLMStreamMixin): 步骤10 流式LLM生成（316行）
  - `stream_executor_permission.py` (PermissionMixin): 权限检查 + 三轨评分 + 用量计数 + 积分上报
  - MRO: StreamWorkflowExecutor → PipelineMixin → LLMStreamMixin → PermissionMixin → WorkflowExecutor
- **except 收窄**: 确认 clients/ 和 services/ 目录已在 #4 中完成收窄，无 except Exception 残留
- 验证：403 单元测试通过，无回归

---

## #49 (security) 移除 pickle 反序列化 — 消除 RCE 向量 — 2026-03-05

对应产品版本：v1.6.8

- unified_cache.py: 移除 `import pickle` 及所有 pickle 相关代码
  - `_get_from_redis()`: JSON 反序列化失败时返回原始字符串或 None（移除 pickle.loads fallback）
  - `_set_to_redis()`: JSON 序列化添加 `default=str` 兜底（移除 pickle.dumps fallback）
  - 消除 Redis 被攻破时的 RCE（远程代码执行）风险

---

## #48 (fix) 生产日志问题修复 R2 Batch 2 — 2026-03-01

对应产品版本：v1.6.6

- `security.py`: `AuthenticationManager.PUBLIC_PATHS` 补充 `/favicon.ico` 和 `/robots.txt`，修复 SecurityMiddleware 拦截静态资源导致 401
- `container.py`: `LLMFallbackManager` timeout 从硬编码 30s 改为读取 `LLM_TIMEOUT` 环境变量（默认 60s），修复免费模型响应慢时过早超时

---

## #47 (fix) 生产日志问题修复 R2 Batch 1 — 2026-03-01

对应产品版本：v1.6.6

- `credit_client.py`: `check_usage()` endpoint 从 `/api/usage/check`（jwt.auth）改为 `/api/internal/usage/check`（internal.api），修复 401 认证失败
- `postural_assessor.py`: 实现 5 个抽象方法（get_name/get_description/get_category/get_input_schema/get_output_schema），删除旧类属性，修复 MCPToolRegistry 实例化失败
- `llm_decision_engine.py`: exercise_optimization 增加强触发规则（"推荐+动作+肌群"→必选），新增 5 个复合意图示例，quick_consultation 增加排除条件
- `chat_client.py`: 新增 `get_conversation_topic()` 方法，修复 conversation_memory 从后端加载话题时 AttributeError

---

## #46 (fix) 生产环境审计修复 Batch 2 — 2026-02-28

对应产品版本：v1.6.5

- `parameter_mapping_config.yaml`: 补全 `chinese_to_enum` 转换器（9 个类型：training_goal/fitness_level/activity_level/split_type/training_intensity/alternative_reason/modification_purpose/fitness_goal/training_type）
- `model_routing.py`: 可用后端 < 2 时打 WARNING 告警
- `model_routing.py`: 新增 `get_model_pool_status()` 供 health 端点调用
- `health.py`: `/health` 端点增加 `model_pool` 字段（available/total/degraded/backends）
- 配置验证通过：无 ⚠️ 和 ❌

---

## #45 (fix) 生产环境审计修复 Batch 1 — 2026-02-28

对应产品版本：v1.6.5

- `llm_decision_engine.py`: DAGSelectionResult 新增 `method` 字段（"llm"/"fallback"），修复 fallback 路径缺少必填字段导致的运行时崩溃
- `llm_decision_engine.py`: fallback 模板从不存在的 `general_qa` 改为 `quick_consultation`
- `llm_decision_engine.py`: LLM 分类 prompt 补全 4 个缺失模板（posture_correction/plan_adjustment/fat_loss_program/strength_program），从 9 个扩展到 13 个
- `llm_decision_engine.py`: `_keyword_matching()` 标记 `@deprecated`
- `unified_cache.py`: `set()` 方法同时写 L1 进程内缓存，Redis 不可用时 L1 仍生效
- `unified_cache.py`: `delete()`/`invalidate()` 同时清理 L1
- 新增 `tests/unit/services/test_user_memory.py` — 记忆检索冒烟测试（8 个用例）
- 新增 `tests/unit/framework/test_unified_cache_l1.py` — L1 缓存验证（8 个用例）

---

## #44 (fix) 上线前安全加固 — 2026-02-28

对应产品版本：v1.6.4

- `routes/chat.py`: 3处 `str(e)` 异常信息泄露 → 替换为通用错误消息
- `main.py`: 生产环境禁用 `/docs`、`/redoc`、`/openapi.json` 路由
- `main.py`: `DEBUG` 环境变量判断修复（`"false"` 字符串不再误判为 True）
- `main.py`: CORS 白名单生产环境移除 localhost 源
- `connection_pool_manager.py`: MySQL 连接池添加 `connect_timeout`/`read_timeout`/`write_timeout`

---

## #43 (fix) 积分上报降级 + MCP工具部分降级 — 2026-02-27

对应产品版本：v1.5.1

- `credit_reporter.py`: 新增 `_write_fallback()` 方法，重试耗尽后写入本地 JSONL 文件（`/app/logs/credit_fallback.jsonl`）
- `credit_reporter.py`: 返回值增加 `fallback: True` 标识，便于监控降级情况
- `agent/nodes.py`: MCP 工具调用失败时返回空结果而非错误信息，单个工具失败不阻断整体对话

---

## #42 (chore) 测试清理+断言修复 — 1142 passed, 64 skipped, 0 failed — 2026-02-26

对应产品版本：v1.5.0

- 删除 10 个废弃模块测试文件（PerformanceMonitor/ParallelStepExecutor/three_stage_orchestrator/data_supplement/qdrant_importer/layer2_fix）
- 容器安装 hypothesis，解锁 3 个属性测试（+107 个 hypothesis 生成用例）
- `test_volume_adjuster.py`: 断言"连续2周"→"连续2...RPE过高/完成率过低"（兼容"训练周期"措辞）
- `test_training_plan_summarizer.py`: 断言"第1周"→"第1"（兼容"第1训练周期"）

---

## #41 (fix) 全部非e2e测试修复 — 1032 passed, 0 failed — 2026-02-26

对应产品版本：v1.5.0

- `test_monitoring_api_endpoints.py`: 重写适配 v2.2.0 安全加固 API（JWT认证+权限校验）
- `test_llm_fallback_manager.py`: `test_backend_health_check` pop 自动注册的 DeepSeek client
- `test_task_10_1_quick_benchmark.py`: 添加 `@pytest.mark.asyncio` + server reachable skip
- `test_security_features.py`: `test_rate_limit_basic` patch `BYPASS_RATE_LIMIT_FOR_INTERNAL` 环境变量
- `test_task_23_standards.py`: 添加 `@pytest.mark.asyncio`（strict mode 要求）
- `test_internal_jwt_verifier_property.py`: parametrize 中 `time.time()` 改为函数内动态生成，避免 collect→execute 间 JWT 过期
- `tests/performance/conftest.py`: 新增 autouse fixture，默认跳过性能测试（`RUN_PERFORMANCE_TESTS=1` 启用）

---

## #40 (test) JWT验证器属性测试修复 — 无效类型测试用例校正 — 2026-02-26

对应产品版本：v1.5.0

- `test_internal_jwt_verifier_property.py`: 修复 `test_invalid_field_type_raises_claims_missing_error` 两个参数化用例
  - `permissions: "not-an-array"` → `daily_dag_limit: "not-a-number"`（`list()` 对字符串不抛异常，`int()` 对非数字字符串抛 ValueError）
  - `tier: 123` → `daily_agent_limit: "invalid"`（`str()` 对整数不抛异常，`int()` 对非数字字符串抛 ValueError）
- 根因：`PermissionClaims.from_jwt_payload()` 使用 `str()/int()/list()` 防御性强转，原测试用例选择的类型可被正常强转

---

## #39 (refactor) 计算器卡片迁移 — Python服务删除+MCP薄包装+孤立测试清理 — 2026-02-25

对应产品版本：v1.5.0

- 删除 `services/intensity_converter.py` 和 `services/progressive_overload.py`（计算逻辑已迁移到PHP）
- `services/__init__.py` 移除已删除服务的导出
- `mcp_tools/nutrition/tdee_calculator.py`: execute() 改为从 user_profile.nutrition_profile.auto_calculated 读取
- `mcp_tools/training/intelligent_weight_calculator.py`: execute() 改为从 user_profile.strength_data 读取1RM
- 清理孤立测试: 删除 `test_intensity_converter.py`、`test_progressive_overload.py`
- 清理 `test_closed_loop_training_system.py` 中 TestProgressiveOverloadCalculator 类
- 修复 `test_llm_decision_optimization.py` 缺少 @pytest.mark.asyncio 装饰器

---

## #38 (refactor) 提示词-数据对齐 — ProfileInjector字段修复+数据丰富化+模板升级+工具清理 — 2026-02-25

对应产品版本：v1.5.0（无变更）

- P0修复: ProfileInjector health_status 字段名对齐数据库（injuries→injury_history, medical_conditions→chronic_diseases, 新增medications/other_notes）
- P1丰富: ProfileInjectionConfig 新增5个开关（nutrition/strength/ffmi/training_prefs/body_composition），extract_key_profile 提取12+字段
- P1格式: _format_concise/_format_detailed 新增营养/力量/FFMI/体成分/训练偏好输出
- P1模板: 6个prompt template添加「用户数据字段说明」段（nutrition_planning/safety_assessment/progress_analysis/rehabilitation_training/strength_program/fat_loss_program）
- P2工具: 注册PosturalAssessor（第18个工具），清理orchestrator孤儿元数据（chinese_food_analyzer/weight_calculator），标注未使用工具

---

## #37 (fix) AI对话系统全面修复 — 安全+可靠性+健壮性 — 2026-02-25

对应产品版本：v1.5.0

- usage_reporter.py: 积分上报重试耗尽后写入 fallback JSONL 日志（/app/logs/credit_fallback.jsonl）
- chat.py: Prompt Injection 检测异常改为 fail-closed（返回安全降级响应）
- chat.py: Token 计数改进，新增 _estimate_tokens() 区分中英文比率（1.5/4.0 chars/token）
- stream_executor.py: 权限检查异常改为 fail-closed（返回 allowed=False）
- llm_client.py: LLM Fallback 捕获所有 httpx.TimeoutException，ConnectTimeout 快速失败
- nodes.py: MCP 工具部分降级，hybrid 检索路径 try-except 保护
- health.py: /health 端点新增 tools 字段返回18个工具的名称+中文名+数据来源

---

## #36 (feat) 三端枚举统一 — AI 服务枚举修复 + 字段名对齐 — 2026-02-24

对应产品版本：v1.4.0

- types/enums.py: MembershipTier 修复 PAID→WARMHEART, VIP→ENERGY
- concurrency_limiter.py: UserTier 同步修改 + DEFAULT_TIER_CONFIGS
- clients/models.py: UserProfile 字段名 strength_levels→strength_data, health_profile→health_status（from_api_response 含 fallback 兼容）
- 全局替换 10+ 文件中的 health_profile→health_status, strength_levels→strength_data dict key 引用
- 测试文件同步更新，pytest 全量通过（跳过1个已存在的 async 配置问题）
- 12-枚举映射说明.md 更新反映统一后状态

---

## #35 (feat) 统一可观测性仪表盘 — 性能字段上报 — 2026-02-24

对应产品版本：v1.3.0

- credit_reporter: report_consumption() 新增 5 个性能参数（ttfb_ms/duration_ms/tokens_per_sec/fallback_count/error_type）
- stream_executor: 对话完成后采集性能指标传递给 credit_reporter
- executor: 同步执行器同样采集性能指标（ttfb_ms=0）
- pytest: TestPerformanceFields 3 用例通过，总计 25/25 passed

---

## #34 (fix) Agent user_profile 注入 + TDEE 字段兼容 — 2026-02-24

对应产品版本：v1.2.0

- `tool_node` 将 Agent state 中的 `user_profile` 注入到 MCP 工具参数，解决工具内 `_get_user_profile()` 未实现导致档案为空的问题
- `tdee_calculator._merge_user_info` 兼容 `weight`/`height` 和 `weight_kg`/`height_cm` 两种字段名
- 端到端验证通过：Agent → load_skill(nutrition_planning) → tdee_calculator → TDEE=2651卡
- 测试指标：TTFB=36.7s, 总耗时=54.5s, 字符=2545, Agent执行=27.03s, tools=2, cost=0.10, credits=3

## #33 (fix) Agent Function Calling 修复 — 2026-02-24

对应产品版本：v1.2.0

- 增强 Agent fallback system prompt，明确要求调用工具而非直接回答
- 首次 agent_node 调用使用 `tool_choice="required"` 强制触发 FC
- system prompt 注入当前 user_id，解决 DeepSeek-V3 因缺少上下文不触发 FC 的问题
- `chat_with_tools` 新增 `tool_choice` 参数透传
- Agent 测试通过：skills=['nutrition_planning'], tools=1, 14.74s

## #31 (test) 4xx快速失败 + 降级链耗时测试 — 2026-02-23

对应产品版本：v1.2.0

- `tests/unit/framework/test_llm_4xx_no_retry.py`: 12 个单元测试覆盖 4xx/5xx/ValueError 分类 + 400 不重试直接降级
- `tests/integration/test_degradation_chain_timing.py`: 2 个集成测试验证降级链耗时（5xx链≈3s, 4xx链<0.1s, 均 ≤30s）

---

## #30 (fix) TokenBudgetManager 动态预算组件限额缩放 — 2026-02-23

对应产品版本：v1.2.0

- `token_budget_manager.py`: 动态预算时按 `total_budget / DEFAULT_BUDGET` 比例缩放可压缩组件限额
- 修复：128K模型(budget=76800)下 `mcp_tools_result` 限额从硬编码3000→19200，摘要不再被二次截断
- 不可压缩组件（persona_prefix/task_instruction/rendering_constraint/current_message）限额保持不变

---

## #29 (feat) 多模型Token预算适配 — 先选模型再压缩 — 2026-02-23

对应产品版本：v1.2.0

- `multi_model_pool.yaml` / `vision_model_pool.yaml`: 每个模型增加 `context_window` 字段
- `PoolEntry` dataclass 增加 `context_window: int = 32000` 字段
- `stream_executor.py` 步骤10: 蓝绿池模型选择提前到 TokenBudgetManager 之前
- 动态预算: `input_budget = context_window × 0.6`（32K→19200, 128K→76800, 200K→120000）

---

## #28 (fix) 流式对话可靠性修复 — Token预算+降级策略+接口兼容 — 2026-02-23

对应产品版本：v1.2.0

- **tool_result_summarizer 部署生效**：MCP工具结果 132K→6.7K chars（95%压缩），LLM 正常返回增肌计划（TTFB 12.3s）
- **LLM 降级管理器 400 快速失败**：`_is_non_retryable_error()` 扩展为全部 4xx 不重试，避免 3轮×10Key 重试风暴
- **指数退避重试**：重试间隔从线性（1s→2s→3s）改为指数退避（200ms→400ms→800ms→2000ms）
- **API Pool 4xx 透传**：`api_pool_manager.call_stream()` 检测 4xx 立即抛出，不继续轮询其他 Key
- **Warmup 422 修复**：`WarmupRequest.user_id` 添加 `field_validator` 自动 int→str，消除前端 422 错误
- **Token 预算参数校准**：`AVG_CHARS_PER_TOKEN` 2.5→1.8，`DEFAULT_BUDGET` 8000→12000，`mcp_tools_result` 限额 1500→3000
- **死代码服务标记**：6 个未调用 services 添加 `# TODO: 待接入工作流` 注释

---

## #27 (chore) 死代码清理 — _use_new_cache feature flag 退役 — 2026-02-23

对应产品版本：v1.1.0（内部清理，产品版本不动）

- 删除 `singletons.py` 中 `_use_new_cache()` 函数（硬编码 return True）
- 清理 `user.py`/`main.py`/`nodes.py` 中 4 处 feature flag 条件分支，内联 True 分支
- 删除 4 个死脚本：`checkpoint_phase2_verification.py`/`test_cache_integration.py`/`test_new_cache_enabled.py`/根目录 `test_cache_integration.py`
- 删除 3 个 `.bak` 归档文件 + 2 个空脚本
- 修复 `main.py` 重复 logger.info 行
- 验证：860 passed / 6 skipped / 0 failed

---

## #26 (refactor) professional_program_designer.py Mixin 拆分 — 2026-02-23

对应产品版本：v1.1.0（内部重构，产品版本不动）

- 2028 行 → 5 文件 Mixin 拆分（`program_designer/` 子包）
- `models.py`：枚举 + Pydantic schemas（~150 行）
- `volume_mixin.py`：训练量计算 + 周期化 + 减量日（~230 行）
- `program_generator_mixin.py`：周计划生成 + 训练日创建 + 热身/放松（~310 行）
- `program_analysis_mixin.py`：平衡分析 + 安全评估 + 执行建议（~280 行）
- 主文件保留 execute() + 训练周期 + 肌群数据 + 动作选择（~480 行）
- Re-export 所有模型类，API 完全向后兼容

---

## #25 (refactor) backend_client.py Mixin 拆分 — 2026-02-23

对应产品版本：v1.1.0（内部重构，产品版本不动）

- 2240 行 → 7 文件 Mixin 拆分（`clients/` 子包）
- `models.py`：数据模型 + 枚举 + 异常类
- `base_client.py`：BackendConfig + HTTP 核心基础设施
- `user_client.py`：用户档案 API（UserMixin）
- `credit_client.py`：会员权限 + 用量统计 API（CreditMixin）
- `chat_client.py`：对话记录 API（ChatMixin）
- `health_client.py`：健康检查 + 训练数据 API（HealthMixin）
- 修复 `BackendConnectionError` → `BackendAPIError`（原 line 1715 不存在的异常类）
- 验证：860 passed / 6 skipped / 0 failed

---

## #24 (refactor) LLM 客户端迁移到 DI 容器 — 2026-02-23

对应产品版本：v1.1.0（内部重构，产品版本不动）

- `call_with_fallback`/`call_with_fallback_stream` 新增 `primary_backend`/`fallback_backends` 覆盖参数
- 消除 3 个文件中 6 处 `LLMFallbackManager` 直接实例化（llm_decision_engine/nodes/stream_executor）
- 蓝绿池路由通过参数覆盖实现，不再每次请求创建新实例
- 更新 `test_llm_fallback_integration.py` 断言适配 DI 容器模式
- 验证：860 unit + 74 integration passed / 0 failed

---

## #23 (refactor) DI 容器重构 — singletons 全局单例集中管理 — 2026-02-23

对应产品版本：v1.1.0（内部重构，产品版本不动）

- 新增 `src/framework/container.py`：轻量 AppContainer（11 个工厂函数，零新依赖）
- `singletons.py` 从 601 行重构为 ~150 行薄代理层，所有 get_xxx() 委托到容器
- 支持 `override()` 测试注入 + `reset()` 状态清理，替代原有 `reset_all_singletons()`
- 修复 `from ....framework` 相对 import 超出包边界问题（改为绝对 import）
- 验证：104 passed / 0 failed（5 个核心组件测试文件）

---

## #22 (test) 集成测试全量修复 + 训练术语统一 — 2026-02-23

对应产品版本：v1.1.0（测试修复+术语优化，产品版本不动）

**集成测试修复（8 FAILED → 0 FAILED）**：
- `test_llm_fallback_integration.py`: 3个测试重写，适配关键词匹配优先架构（不再mock已废弃的LLM路径）
- `test_prometheus_streaming_metrics.py`: 5个测试添加JWT admin认证（`_verify_admin_token`路由级鉴权）
- `test_weekly_plan_generation_flow.py`: 断言适配新术语"训练周期"
- 4个挂起测试添加skip标记：`test_step_3_4_parallel`（ParallelStepExecutor已删除）、`test_streaming_e2e`/`test_streaming_workflow_功能`（需真实API服务）、`test_connection_pool_integration`单测（需真实DB连接池）

**术语统一**：
- `weekly_plan_generator.py`: 注释/docstring/日志中"周"（训练周期含义）→"训练周期"，避免与"星期"混淆
- `volume_adjuster.py`: 用户通知消息和docstring同步更新

**最终结果**：77 passed / 29 skipped / 0 failed

---

## #21 (fix) HTTPException handler Pydantic v2 兼容修复 — 2026-02-22

- 修复 `main.py:464` http_exception_handler：移除 `model_dump_json(encoder=CustomJSONEncoder)` 不兼容参数
- 根因：Pydantic v2 的 `model_dump_json()` 不支持 `encoder` 参数（v1 语法残留），导致所有 HTTPException（401/403/404）被 general_exception_handler 捕获后返回 500
- 影响范围：所有需要认证的 /api/health/metrics/* 端点、以及任何抛出 HTTPException 的路由
- 验证：/api/health/metrics/prometheus 正确返回 401（无有效JWT时）而非 500
- 对应产品版本：v1.1.0（内部bug修复，产品版本不动）

---

## #20 (fix) contraindications_checker Neo4j API对齐 + 安全扫描基础设施 — 2026-02-22

对应产品版本：v1.1.0（内部bug修复+工具链，产品版本不动）

- `contraindications_checker.py`: 4处 `neo4j_client.query()` → `execute_query()`（Neo4jClient无query方法，端到端验证发现）
- 测试mock同步更新: `mock_neo4j_client.query` → `mock_neo4j_client.execute_query`
- 端到端验证通过: Neo4j真实数据 exercise_id=1063 lower_back_pain severity=moderate 238ms
- 新增安全扫描基础设施: `scripts/security-scan/`（SOUL.md + scan.sh + crontab + 首次报告）
- PHP依赖扫描发现5漏洞: symfony/http-foundation CVE-2025-64500(high) 需升级

## #19 (fix) health_conditions字段名对齐 — 用户健康档案数据链路修复 — 2026-02-22

对应产品版本：v9.88.0（内部bug修复，产品版本不动）

- `_build_health_conditions()`: 读取key从`health_profile`改为`health_status`（对齐后端InternalUserController）
- 字段名对齐: `chronic_conditions`→`chronic_diseases`, 移除不存在的`current_symptoms`, 新增`medications`支持
- `_generate_medical_guidance()`: 同步字段名修复
- 更新5个测试用例mock数据为实际string[]格式（后端传递的是字符串数组，非dict）

## #18 (feat) 意图分类器扩展 — 带伤训练场景覆盖 — 2026-02-22

对应产品版本：v9.88.0（内部优化，产品版本不动）

- INJURY_KEYWORDS 新增20+口语化表达（腰突/膝盖疼/肩膀疼/崴脚/鼠标手等）
- SAFETY_CONTRAINDICATION_PATTERNS 新增4个带伤训练正则模式
- 实体提取后清理尾部标点和助词（的/了/，）
- 测试覆盖: 14个查询中12个正确路由（之前仅6个）

## #17 (fix) 禁忌症系统修复 — Neo4j数据补全+Cypher属性对齐+checker bug修复 — 2026-02-22

对应产品版本：v9.88.0（内部bug修复，产品版本不动）

- Neo4j数据补全: 11个孤立InjuryType补充3,293条CONTRAINDICATED_FOR关系（3,078→6,371）
- Cypher模板修复: SAFETY_CONTRAINDICATIONS移除不存在的description/intensity_limit属性
- INJURY_SYNONYMS同义词映射: 60+条口语→正式医学术语映射
- contraindications_checker.py: 修复6处属性名不匹配（category_zh→category等）
- 39 checker tests passed, 840 total unit tests passed

## #16 (docs) 文档清理 — 删除冗余测试报告 + 更新过时代码引用 — 2026-02-22

对应产品版本：v9.88.0（纯文档清理，产品版本不动）

- 删除 11 个冗余测试报告（07-测试报告/01-06,08,10,11,15,21）
- 更新 5 个代码参考文档中已删除模块的路径标注
  - `05-代码目录结构.md`: membership_controller, parallel_step_executor, strategy_selector, neo4j_field_mapping, content_safety_filter
  - `09-步骤8-三层检索.md`: graphrag_retriever.py
  - `06-三层检索与MCP集成架构.md`: graphrag_retriever.py
  - `03-MCP工具架构.md`: content_safety_filter.py
  - `02-框架层代码文件说明.md`: strategy_selector.py

## #15 (refactor) Agent模块化重构 — 管线步骤7双模式执行 — 2026-02-22

对应产品版本：v9.88.0（内部重构，产品版本不动）

**Agent 恢复为管线步骤7的执行方式（与DAG并列）**
- `agent/` 从 `experimental/` 移回 `src/applications/fitness/agent/`
- `stream_executor.py`: `_execute_steps_7_8()` 拆分为 `_dag` 和 `_agent` 两个方法
  - DAG模式: 固定模板编排MCP工具（默认，所有用户）
  - Agent模式: LangGraph动态决策tool-calling loop（积分体系，所有用户可用）
  - Agent输出 `tool_results` 转换为 `dag_results` 格式，步骤9统一处理
  - Agent失败时降级到检索(node_retrieve_context)
- `chat.py`: 恢复 `strategy` 参数从请求读取（`dag`/`agent`）
- `mode_router.py` v4.1: 积分体系对齐，所有用户可用Agent模式（权限由积分消耗控制）
- `executor.py`: 修复 `framework.skills` import 为绝对路径

**架构**: 步骤1-6(共享) → 步骤7(DAG或Agent) → 步骤8-11(共享)

## #14 (chore) 管线缓存 + 死代码清理 + 依赖精简 — 2026-02-22

对应产品版本：v9.88.0（纯内部优化，产品版本不动）

**3A: 步骤6.5 DAG模板选择缓存**
- `nodes.py` `node_select_dag_template`: 添加 query_hash+user_tier 缓存key，TTL=1h
- `stream_executor.py`: 传入 cache_manager 到步骤6.5
- 预期效果：重复查询跳过LLM调用(1-3s)，响应时间-30%

**3B: 死代码清理 (-4,326行)**
- 删除9个孤岛源文件: neo4j_field_mapping.py, container.py, parallel_step_executor.py, content_safety_filter.py, image_processor.py, llm_call_logger.py, graphrag_retriever.py, query_preprocessor.py, qdrant_helper.py
- 删除8个引用已删除模块的测试文件

**3C: 依赖精简**
- `requirements.txt`: 移除6个未使用包(faiss-cpu, aiosqlite, pypdf, FlagEmbedding, requests, python-dotenv)
- 新增 `requirements-dev.txt`: 分离开发依赖(pytest, pytest-asyncio, black, ruff)

## #13 (refactor) Agent模式移至experimental/ + 检索层精简 — 2026-02-22

对应产品版本：v9.88.0（纯内部重构，产品版本不动）

**Block A: Agent代码清理 (-5,157行)**
- `src/applications/fitness/agent/` 6个核心文件(36,303行)移至 `experimental/agent/`
- `src/framework/orchestration/agent_executor.py`(2,000行) 移至 `experimental/`
- `src/framework/skills/skills_agent_executor.py`(786行) 移至 `experimental/`
- 清理 `chat.py` + `stream_executor.py` Agent路由分支
- 简化 `mode_router.py` 统一返回DAG
- `strategy_selector.py` 移除AGENT枚举和相关逻辑
- `skills/__init__.py` 移除Agent执行器导出
- `is_agent_mode_enabled()` 统一返回False
- 2个Agent测试文件移至 `experimental/`

**Block B: 检索层精简**
- 删除 `HybridSearchEngine.compare_search_methods()` 未使用方法
- 三套引擎保留(各有分工): HybridSearch(DAG管线60%) + GraphRAG(API+降级) + TrueThreeLayer(MCP工具)

**验证**: 654 unit tests passed, 所有import正常

## #12 (fix) 向量检索修复 — hybrid_search 直查 Qdrant 同源数据 — 2026-02-21

- `src/framework/retrieval/hybrid_search.py`：`vector_search()` 重写
  - 移除 HTTP 自调用 GraphRAG API（路径 `/api/v1/graphrag` 404 + 查错 collection）
  - 改为直接查 Qdrant `training_knowledge` collection（与 BM25 同源 4,062 文档）
  - 修复结果解析：从 `payload.chunk_text` 提取文本（原 `r.get('text')` 为空）
  - 移除 `aiohttp` 依赖和 `graphrag_api_base` 参数
- A/B 测试重新验证：
  - Hybrid 关键词命中率：31.7% → 51.7%（新权重）/ 40.0% → 55.0%（旧等权）
  - 纯 BM25 仍领先（65%），符合健身领域关键词匹配特性
  - 向量检索延迟：首次 ~2.3s（模型冷启动），稳定 ~25-40ms
- 对应产品版本：v1.1.0

## #11 (feat) Embedding 模型评估 + 口语噪声清洗预处理器 — 2026-02-21

- 新增 `scripts/eval_embedding_models.py`：Embedding 模型评估框架
  - 10 组健身领域 query-document 相关性对 + 8 组口语噪声测试对
  - GTE-Large-zh 实测：100% 相关性准确率 / margin=0.3115 / 口语sim=0.8501 / 3.4ms
  - BGE-M3 / GTE-Qwen2 容器无外网无法下载，基于公开 benchmark 对比
  - 结论：GTE-Large-zh 当前够用，BGE-M3 迁移 ROI 低优先级不高
- 新增 `src/framework/retrieval/query_preprocessor.py`：口语噪声清洗预处理器
  - 28 个填充词（按长度降序匹配）+ 7 条句式正则模式
  - 纯规则零 LLM 调用，8/8 口语清洗正确 + 2/2 正常查询不破坏
  - 入口函数 `preprocess_query()` 可直接集成到检索管线
- 对应产品版本：v1.1.0

## #10 (feat) Neo4j Cypher 模板扩展 — 2026-02-21

- `src/framework/retrieval/cypher_templates.py`：新增 3 个 Cypher 查询模板
  - TRAINING_FREQUENCY：肌肉训练频率查询（optimal_frequency + recovery_time）
  - EXERCISE_SUBSTITUTION：动作替代查询（共享 PRIMARY+SECONDARY 肌肉匹配，按共享数排序）
  - NUTRITION_MACRO：食物宏量营养素查询（Food→Nutrient 关系，蛋白质/碳水/脂肪/能量）
- 模板总数从 12 → 15，覆盖 15/18 种 StructuredQueryType
- 性能测试：3 个新模板均 < 200ms（29ms / 123.6ms / 8.8ms）
- 测试：406/407 通过（1 个预存会员权限失败非本次引入）
- 对应产品版本：v1.1.0

## #9 (feat) 意图分类器扩展 + A/B 测试 — 2026-02-21

- `src/framework/retrieval/intent_classifier.py`：新增 6 种意图模式
  - SUPPLEMENT_ADVICE：补剂咨询（蛋白粉/肌酸/BCAA 等 20 个关键词）
  - TRAINING_FREQUENCY：训练频率（多久练一次/一周几练/恢复时间）
  - TRAINING_SPLIT：训练分化（推拉腿/PPL/上下肢/N天分化）
  - EXERCISE_SUBSTITUTION：动作替代（替代/替换/代替/没有...怎么练）
  - WARMUP_STRETCHING：热身拉伸（训练前热身/训练后拉伸/激活）
  - NUTRITION_MACRO：营养宏量（蛋白质/碳水/TDEE/热量摄入）
- 修复 `MUSCLE_CAPACITY_PATTERNS` 中 "训练频率" 关键词与新模式冲突
- 修复 `FITNESS_LEVEL_PATTERNS` 实体提取：遍历所有捕获组找有效 level 关键词
- 修复 `m.lastindex` 为 None 时的 TypeError（无捕获组正则安全检查）
- 新增 `scripts/ab_test_retrieval.py`：20 查询 A/B 测试脚本
- 新增 `scripts/test_intent_expansion.py`：42 用例意图分类测试（100% 通过）
- 测试：406/407 通过（1 个预存会员权限失败非本次引入）
- 对应产品版本：v1.1.0

## #8 (feat) Alertmanager 企业微信告警转发 — 2026-02-21

- 新增 `src/api/routes/alertmanager_webhook.py`：Alertmanager → 企业微信 Markdown 消息转发
  - 接收标准 Alertmanager webhook payload，格式化为企业微信 Markdown
  - 按 severity 显示不同颜色（critical/warning=橙色, info=绿色）
  - 环境变量 `WECHAT_WEBHOOK_URL` 配置企业微信机器人地址
  - 未配置时优雅降级为日志记录
- 更新 `prometheus/alertmanager.yml`：Slack → 企业微信 webhook 转发
- 更新 `config/prometheus/alertmanager.yml`：同步企业微信配置
- 路由注册到 api_router（`/webhooks/alertmanager`）
- 对应产品版本：v1.1.0

## #7 (refactor) metrics_collector → prometheus_client 迁移 — 2026-02-21

- `src/api/routes/health.py`：移除自定义 `metrics_collector` 依赖
  - 请求耗时改用 `prometheus_integration.request_duration` 官方 Histogram
  - 错误计数改用 `prometheus_integration.record_error()` 官方 Counter
  - `/metrics` 端点改用 `prometheus_client.REGISTRY.collect()` 获取指标摘要
  - `/metrics/prometheus` 端点移除自定义 `export_prometheus()` 追加，只输出标准格式
- `src/applications/fitness/workflow/singletons.py`：`get_performance_monitor` 兼容层改用 `initialize_prometheus_metrics()`
- `src/framework/monitoring/__init__.py`：`metrics_collector` 导出添加 DEPRECATED 注释
- 对应产品版本：v1.1.0

- `src/framework/retrieval/hybrid_search.py`：新增 `search_knowledge_articles` 方法
  - 懒加载 GTE-Large-zh（1024维）向量模型，复用现有 `get_qdrant_client()`
  - collection 不存在时优雅降级（log warning + 返回空列表）
  - 结果携带 `source_type="knowledge_article"`、`article_id`、`title`、`source_book`、`chapter`
- `src/applications/fitness/workflow/nodes.py`：`node_retrieve_context` 扩展
  - 函数启动时并行发起 knowledge_articles 检索任务（`asyncio.ensure_future`）
  - 所有返回路径（DAG/Neo4j/Hybrid/HybridSearch/降级）均追加 `knowledge_refs` 字段
  - 内部辅助函数 `_get_knowledge_refs()` 统一等待任务结果，失败时返回空列表
- `src/applications/fitness/workflow/nodes.py`：`node_llm_analysis` 扩展
  - 从 `retrieval_results.knowledge_refs` 读取知识库引用
  - 注入格式：`[知识引用] {title} — {source_book} Ch.{chapter}`，用分隔线追加到 system_prompt
- 对应产品版本：v1.1.0

## #5 (refactor) 环境变量集中配置 — 2026-02-21

- 创建 `framework/config/app_config.py`：Pydantic BaseSettings 集中管理所有环境变量
- 9 个配置类：MySQLConfig/Neo4jConfig/QdrantConfig/RedisConfig/BackendAPIConfig/InternalTokenConfig/LLMBaseConfig/DeepSeekConfig/AnthropicConfig/ServiceConfig
- fail-fast 校验：Neo4j 密码 + 内部 API Token 缺失时启动即报错
- 迁移 singletons.py 数据库配置到 get_config() 集中入口
- 15 个单元测试全部通过
- 对应产品版本：v1.1.0

## #4 (fix) 全量裸 except 收窄 — 2026-02-21

- 7 个文件 30+ 处裸 except 收窄为具体异常类型
- main.py(2处)/exercise_stability_manager.py(4处)/fewshot_types.py(3处)/mcp_client_v2.py(1处)
- stream_executor.py(10处)/llm_client.py(7处)/backend_client.py(10处)
- daml-rag-server/src/ 零裸 except 残留
- 对应产品版本：v1.1.0

## #3 (feat) 知识库入库脚本 — 2026-02-21

- 创建 `scripts/import_knowledge.py` 批量入库工具
- 支持 YAML front matter 解析 + Markdown 正文提取
- 三端写入：MySQL（文章+引用）→ Qdrant（GTE-Large-zh 1024维向量）→ Neo4j（KnowledgeArticle 节点）
- 首批 5 篇知识文章入库验证通过（CUDA GPU 加速）
- 支持 --dry-run / --skip-qdrant / --skip-neo4j 参数
- 对应产品版本：v1.1.0

## #2 (fix) 安全加固 + Vision 降级逻辑 — 2026-02-21

- 清除 3 个硬编码凭证回退值（singletons.py/backend_client.py/neo4j_client.py）
- LLMRequest 新增 `has_vision_content()` / `strip_vision_content()` 方法
- LLMFallbackManager 新增 Vision 降级：模型不支持图片时自动剥离 image_url，切换纯文本模式
- 流式模式下 yield 用户可见降级提示
- 对应产品版本：v1.1.0

## #1 (chore) MVP 基线 — 2026-02-21

- 从 legacy v9.88.0 冻结归档后的新起点
- Python FastAPI + LangGraph DAML-RAG 框架，含 11 步 DAG 编排、三层检索、18 个 MCP Skills
- 多模型蓝绿池（Anthropic → DeepSeek → Template）
- 对应产品版本：v1.0.0
