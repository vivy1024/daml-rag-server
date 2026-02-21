# daml-rag-server 构建日志

> 内部构建号，不对外发布。产品版本见根仓库 `CHANGELOG.md`。
> 历史版本（v9.88.0 及之前）已归档至 `CHANGELOG-legacy.md`。

---

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
- DAML-RAG 框架，含 DAG 编排、Agent 模式、18 个 MCP 工具
- 多模型蓝绿池（Anthropic → DeepSeek → Template）
- 对应产品版本：v1.0.0
