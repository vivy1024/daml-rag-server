# 04-LLM层

**版本**: v1.1.0  
**创建日期**: 2025-12-22  
**更新日期**: 2026-01-06  
**状态**: ✅ 已实现

---

## 📋 模块说明

本模块包含DAML-RAG框架的LLM层架构文档,负责LLM决策、模型选择和响应生成。

LLM层是整个系统的"大脑",通过智能决策和分析实现:
- **智能模型选择**: 根据查询复杂度和Few-Shot数量选择合适的模型(教师/学生)
- **Few-Shot检索**: 从历史对话中检索高质量示例,实现推理时上下文学习
- **LLM决策**: 在步骤6.5选择合适的DAG方案
- **LLM综合**: 在步骤10基于真实数据进行专业分析和建议
- **响应优化**: 根据场景动态调整提示词和参数

---

## 🆕 v1.1.0更新：服务器环境优化

### API池轮询

支持最多10个DeepSeek API Key轮询，提高可用性：

```bash
# 环境变量配置
DEEPSEEK_API_KEY=sk-main-key
DEEPSEEK_API_KEY_2=sk-backup-2
...
DEEPSEEK_API_KEY_10=sk-backup-10

USE_API_POOL=true  # 启用API池轮询
```

**核心组件**: `src/framework/clients/api_pool_manager.py`

### 禁用双模型选择

服务器环境无Anthropic Claude，可禁用双模型选择：

```bash
DUAL_MODEL_ENABLED=false  # 禁用双模型选择
OLLAMA_ENABLED=false      # 禁用Anthropic Claude降级
```

**影响**:
- 步骤4：快速跳过BGE复杂度分类
- 步骤5：直接选择DeepSeek（teacher）
- 降级策略：DeepSeek(API池) → Template

---

## 📚 文档列表

### 核心架构文档

1. **01-智能模型选择架构.md** (待创建)
   - 模型选择器的设计理念
   - 复杂度分类算法(BGE向量相似度)
   - 教师模型vs学生模型的选择策略
   - 灰色地带的Few-Shot辅助决策
   - **v1.1.0**: 双模型选择禁用机制

2. **02-Few-Shot检索架构.md** (待创建)
   - Few-Shot检索的设计理念
   - 推理时上下文学习(In-Context Learning)
   - 质量评分机制(rating, training_effect)
   - Qdrant向量检索实现

3. **03-LLM模板架构.md** (已创建)
   - LLM决策模板设计(步骤6.5)
   - LLM分析模板设计(步骤10)
   - 模板配置方式和扩展机制
   - 动态提示词构建

4. **04-LLM响应优化架构.md** (待创建)
   - 响应优化的设计理念
   - 动态参数配置(max_tokens, temperature)
   - 场景复杂度分类
   - 提示词风格调整

5. **05-API池轮询架构.md** (待创建)
   - API池管理器设计
   - 多Key轮询策略
   - 健康状态追踪和冷却机制
   - 降级策略

---

## 🔗 相关模块

- **01-系统架构**: 了解LLM层在整体系统中的位置
- **02-数据层**: 了解Few-Shot数据存储在Qdrant中
- **03-编排层**: 了解LLM如何与编排器交互
- **04-开发指南/03-配置管理**: 查看LLM配置的使用方法
- **04-开发指南/51-训练案例库与Few-Shot融合指南**: 查看Few-Shot的使用方法

---

## 🎯 快速导航

- 想了解模型如何选择? → 阅读 `01-智能模型选择架构.md` (待创建)
- 想了解Few-Shot如何工作? → 阅读 `02-Few-Shot检索架构.md` (待创建)
- 想了解LLM模板如何设计? → 阅读 `03-LLM模板架构.md`
- 想了解响应如何优化? → 阅读 `04-LLM响应优化架构.md` (待创建)
- 想了解API池轮询? → 阅读 `05-API池轮询架构.md` (待创建)

---

## 📝 核心代码文件

| 文件 | 说明 |
|------|------|
| `src/framework/clients/llm_client.py` | LLM客户端，支持DeepSeek/Anthropic Claude/Moonshot |
| `src/framework/clients/llm_fallback_manager.py` | LLM降级管理器 |
| `src/framework/clients/api_pool_manager.py` | API池轮询管理器（v8.75.0新增） |
| `src/framework/models/adaptive_model_selector.py` | 自适应模型选择器 |
| `src/framework/models/query_complexity_classifier.py` | 查询复杂度分类器 |
| `src/applications/fitness/llm_decision_engine.py` | LLM决策引擎（步骤6.5） |
| `src/applications/fitness/llm_analysis_engine.py` | LLM分析引擎（步骤10） |

---

**维护者**: 薛小川  
**最后更新**: 2026-01-06
