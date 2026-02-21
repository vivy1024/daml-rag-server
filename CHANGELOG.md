# daml-rag-server 构建日志

> 内部构建号，不对外发布。产品版本见根仓库 `CHANGELOG.md`。
> 历史版本（v9.88.0 及之前）已归档至 `CHANGELOG-legacy.md`。

---

## #2 (fix) 安全加固 + Vision 降级逻辑 — 2026-02-21

- 清除 3 个硬编码凭证回退值（singletons.py/backend_client.py/neo4j_client.py）
- LLMRequest 新增 `has_vision_content()` / `strip_vision_content()` 方法
- LLMFallbackManager 新增 Vision 降级：模型不支持图片时自动剥离 image_url，切换纯文本模式
- 流式模式下 yield 用户可见降级提示
- 对应产品版本：v1.0.0

## #1 (chore) MVP 基线 — 2026-02-21

- 从 legacy v9.88.0 冻结归档后的新起点
- DAML-RAG 框架，含 DAG 编排、Agent 模式、18 个 MCP 工具
- 多模型蓝绿池（Anthropic → DeepSeek → Template）
- 对应产品版本：v1.0.0
