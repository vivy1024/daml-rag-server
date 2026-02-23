# daml-rag-server 构建日志

> 内部构建号，不对外发布。产品版本见根仓库 `CHANGELOG.md`。
> 历史版本（v9.88.0 及之前）已归档至 `CHANGELOG-legacy.md`。

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
