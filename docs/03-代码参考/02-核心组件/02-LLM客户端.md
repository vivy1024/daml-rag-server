# LLM客户端参考

**创建日期**: 2025-12-22

---


**版本**: v1.0.0  
**更新日期**: 2025-12-16  
**状态**: ✅ 已完成  
**文件**: `src/framework/clients/llm_client.py`

---

## 📋 概述

LLM客户端提供统一的大语言模型调用接口，支持多个LLM提供商，具备自动重试、降级响应等企业级特性。

### 支持的LLM提供商

| 提供商 | 角色 | 模型 | 特点 |
|--------|------|------|------|
| **DeepSeek** | Teacher模型 | deepseek-chat | 经济实惠，推理能力强 |
| **Ollama** | Student模型 | qwen3:8b | 本地部署，隐私保护 |
| **Moonshot** | 备用 | moonshot-v1-32k | 长文本处理 |
| **通义千问** | 备用 | qwen-turbo | 国内稳定 |

---

## 🔧 配置说明

### 环境变量配置

```bash
# DeepSeek配置（主要）
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# Ollama配置（本地）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b

# 通用配置
LLM_TIMEOUT=120.0          # 超时时间（秒）
LLM_MAX_TOKENS=2000        # 最大生成token数
LLM_TEMPERATURE=0.7        # 温度参数

# 重试配置（v2.3.9新增）
LLM_MAX_RETRIES=2          # 最大重试次数
LLM_RETRY_DELAY=2.0        # 重试延迟（秒）
```

### 超时配置详解（v2.3.9优化）

```python
timeout_config = httpx.Timeout(
    connect=10.0,   # 连接超时：10秒
    read=120.0,     # 读取超时：120秒（主要优化点）
    write=10.0,     # 写入超时：10秒
    pool=5.0        # 连接池超时：5秒
)
```

**优化历史**:
- v2.3.8及之前：统一60秒超时
- v2.3.9：精细化配置，读取超时提升到120秒

---

## 📖 核心API

### 1. `call_deepseek()` - DeepSeek调用

**功能**: 调用DeepSeek API，支持自动重试和降级响应

```python
async def call_deepseek(
    query: str,
    few_shot_examples: List[Dict[str, Any]],
    tool_results: Dict[str, Any],
    system_prompt: str = "你是一位专业的健身教练...",
    max_tokens: int = LLMConfig.MAX_TOKENS
) -> str
```

**参数**:
- `query`: 用户查询
- `few_shot_examples`: Few-Shot示例列表
- `tool_results`: 工具调用结果
- `system_prompt`: 系统提示词
- `max_tokens`: 最大生成token数

**返回**: AI回答文本

**特性**（v2.3.9）:
- ✅ 自动重试：最多重试2次
- ✅ 指数退避：每次重试延迟递增
- ✅ 降级响应：失败后返回结构化响应
- ✅ 详细日志：记录每次尝试的详细信息

**使用示例**:

```python
from src.framework.clients.llm_client import call_deepseek

# 基础调用
answer = await call_deepseek(
    query="如何练胸肌？",
    few_shot_examples=[],
    tool_results={}
)

# 带Few-Shot和工具结果
answer = await call_deepseek(
    query="推荐适合我的训练计划",
    few_shot_examples=[
        {
            "query": "如何增肌？",
            "response": "增肌需要..."
        }
    ],
    tool_results={
        "user_profile": {"age": 25, "goal": "增肌"},
        "exercises": [...]
    }
)
```

### 2. `call_ollama()` - Ollama调用

**功能**: 调用本地Ollama模型

```python
async def call_ollama(
    query: str,
    few_shot_examples: List[Dict[str, Any]],
    tool_results: Dict[str, Any],
    system_prompt: str = "你是一位专业的健身教练...",
    model: str = LLMConfig.OLLAMA_MODEL
) -> str
```

**使用场景**:
- 本地部署，无需API密钥
- 隐私保护，数据不出本地
- 简单查询，快速响应

### 3. `stream_deepseek()` - 流式调用

**功能**: 流式返回DeepSeek响应

```python
async def stream_deepseek(
    query: str,
    few_shot_examples: List[Dict[str, Any]],
    tool_results: Dict[str, Any],
    system_prompt: str = "你是一位专业的健身教练..."
) -> AsyncIterator[str]
```

**使用示例**:

```python
async for chunk in stream_deepseek(query, [], {}):
    print(chunk, end="", flush=True)
```

### 4. `get_fallback_response()` - 降级响应

**功能**: 生成有意义的降级响应（v2.3.9优化）

```python
def get_fallback_response(
    query: str,
    tool_results: Optional[Dict[str, Any]] = None,
    reason: str = "LLM服务暂时不可用"
) -> str
```

**特点**:
- 基于查询和工具结果生成结构化响应
- 提取关键信息（用户档案、检索结果等）
- 提供实用建议

**降级响应示例**:

```
抱歉，AI分析功能暂时不可用（DeepSeek读取超时）。

📝 您的查询：推荐适合我的训练计划

✅ 已完成以下数据分析：

👤 **用户档案**：
  - 年龄：25岁
  - 目标：增肌
  - 水平：中级

📊 **检索结果**：找到 15 个相关推荐

💡 **建议**：
  - 请稍后重试获取AI分析
  - 或联系客服获取人工指导
  - 您也可以查看上述数据自行分析
```

---

## 🔄 重试机制（v2.3.9新增）

### 重试策略

```python
# 重试逻辑
for attempt in range(LLMConfig.MAX_RETRIES + 1):
    try:
        if attempt > 0:
            logger.info(f"DeepSeek重试 {attempt}/{LLMConfig.MAX_RETRIES}...")
            await asyncio.sleep(LLMConfig.RETRY_DELAY * attempt)  # 指数退避
        
        # 调用API
        response = await client.post(...)
        return response
        
    except httpx.ReadTimeout as e:
        # 仅对ReadTimeout重试
        if attempt >= LLMConfig.MAX_RETRIES:
            break
        continue
        
    except httpx.HTTPError as e:
        # HTTP错误不重试（如401、403）
        break
```

### 重试场景

| 错误类型 | 是否重试 | 原因 |
|---------|---------|------|
| `ReadTimeout` | ✅ 是 | 网络波动，重试可能成功 |
| `HTTPError` (401/403) | ❌ 否 | 认证问题，重试无意义 |
| `HTTPError` (500) | ❌ 否 | 服务器错误，立即降级 |
| 其他异常 | ❌ 否 | 未知错误，立即降级 |

### 指数退避

```
第1次尝试：立即执行
第2次尝试：延迟 2秒（RETRY_DELAY * 1）
第3次尝试：延迟 4秒（RETRY_DELAY * 2）
```

---

## 📊 日志记录

### 成功日志

```
DeepSeek调用成功 (尝试1): tokens=1234, length=567
```

### 超时日志

```
DeepSeek读取超时 (尝试1/3): 
  - 超时设置: 120.0秒
  - 查询长度: 123
  - 工具结果数: 5
```

### 降级日志

```
使用降级响应: DeepSeek调用失败（已重试2次）: ReadTimeout
```

---

## 🎯 最佳实践

### 1. 超时配置

```python
# ✅ 推荐：根据查询复杂度调整
simple_query = await call_deepseek(query, [], {})  # 使用默认120秒

# ❌ 避免：过短的超时
# LLM_TIMEOUT=30  # 太短，容易超时
```

### 2. Few-Shot示例

```python
# ✅ 推荐：提供相关示例
few_shot_examples = [
    {
        "query": "如何练胸肌？",
        "response": "胸肌训练推荐：1. 卧推 2. 俯卧撑..."
    }
]

# ❌ 避免：过多示例（影响性能）
# few_shot_examples = [...]  # 超过5个
```

### 3. 工具结果格式化

```python
# ✅ 推荐：结构化数据
tool_results = {
    "user_profile": {"age": 25, "goal": "增肌"},
    "exercises": [
        {"name": "卧推", "difficulty": "中级"}
    ]
}

# ❌ 避免：过大的数据
# tool_results = {"exercises": [...]}  # 超过100条
```

### 4. 错误处理

```python
# ✅ 推荐：信任降级响应
answer = await call_deepseek(query, [], {})
# 无需try-catch，函数内部已处理

# ❌ 避免：外部捕获异常
# try:
#     answer = await call_deepseek(...)
# except Exception:
#     # 不需要，函数已返回降级响应
```

---

## 🔍 故障排查

### 问题1：超时频繁

**症状**: 经常出现ReadTimeout错误

**排查**:
1. 检查网络连接：`ping api.deepseek.com`
2. 检查超时配置：`echo $LLM_TIMEOUT`
3. 查看日志：查询长度、工具结果数

**解决**:
```bash
# 增加超时时间
export LLM_TIMEOUT=180.0

# 或减少输入数据量
tool_results = {...}  # 精简数据
```

### 问题2：降级响应频繁

**症状**: 经常返回降级响应

**排查**:
1. 检查API密钥：`echo $DEEPSEEK_API_KEY`
2. 检查API额度：登录DeepSeek控制台
3. 查看错误日志：具体失败原因

**解决**:
```bash
# 检查API密钥
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
     https://api.deepseek.com/v1/models

# 切换到Ollama
export OLLAMA_BASE_URL=http://localhost:11434
```

### 问题3：重试次数不够

**症状**: 2次重试后仍失败

**排查**:
1. 查看重试日志：每次尝试的详细信息
2. 检查网络稳定性：是否频繁波动

**解决**:
```bash
# 增加重试次数
export LLM_MAX_RETRIES=3

# 增加重试延迟
export LLM_RETRY_DELAY=3.0
```

---

## 📈 性能优化

### 优化历史

| 版本 | 优化内容 | 效果 |
|------|---------|------|
| v2.3.8 | 统一60秒超时 | 基础功能 |
| v2.3.9 | 120秒超时 + 重试 | 成功率提升30% |

### 性能指标

```
平均响应时间：3-8秒
超时率：<5%（v2.3.9）
降级率：<2%
重试成功率：>60%
```

---

## 🔗 相关文档

- <!-- [完整工作流程](../../02-核心架构/01-系统架构/02-完整工作流程.md) (文档不存在) --> - 步骤10使用LLM客户端
- [LLM决策引擎参考](./27-LLM决策引擎参考.md) - 步骤6.5使用LLM客户端
- [LLM综合分析引擎参考](./28-LLM综合分析引擎参考.md) - 步骤10使用LLM客户端

---

**维护者**: BUILD_BODY Team  
**最后更新**: 2025-12-16
