# daml-rag-server 构建日志

> 内部构建号，不对外发布。产品版本见根仓库 `CHANGELOG.md`。
> 历史版本（v9.88.0 及之前）已归档至 `CHANGELOG-legacy.md`。

---

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
