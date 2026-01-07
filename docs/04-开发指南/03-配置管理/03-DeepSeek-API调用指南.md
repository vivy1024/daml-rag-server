# DeepSeek API 调用开发指南

**版本**: v1.0.0  
**创建日期**: 2025-12-18  
**更新日期**: 2025-12-18  
**状态**: ✅ 已完成

---

## 📋 概述

本文档详细说明如何正确调用 DeepSeek API，包括请求格式、参数规范、错误处理和最佳实践。

### 官方文档

- **API文档**: https://api-docs.deepseek.com/zh-cn/
- **模型列表**: https://api-docs.deepseek.com/zh-cn/quick_start/pricing
- **错误码**: https://api-docs.deepseek.com/zh-cn/api/error_codes

---

## 🔑 API 基础信息

### 端点地址

```
POST https://api.deepseek.com/v1/chat/completions
```

### 认证方式

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

### 支持的模型

| 模型名称 | 说明 | 上下文长度 | 价格 |
|---------|------|-----------|------|
| `deepseek-chat` | 最新对话模型 | 64K | ¥1/M tokens (输入), ¥2/M tokens (输出) |
| `deepseek-coder` | 代码专用模型 | 16K | ¥1/M tokens (输入), ¥2/M tokens (输出) |

---

## 📝 请求格式规范

### 标准请求示例

```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业的健身教练"
    },
    {
      "role": "user",
      "content": "帮我制定一个增肌训练计划"
    }
  ],
  "max_tokens": 2000,
  "temperature": 0.7,
  "top_p": 0.95,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stop": null,
  "stream": false
}
```

### 必需参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `model` | string | 模型名称 | `"deepseek-chat"` |
| `messages` | array | 对话消息列表 | 见下文 |

### 可选参数

| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| `max_tokens` | integer | 4096 | 1-4096 | 最大生成token数 |
| `temperature` | float | 1.0 | 0.0-2.0 | 采样温度 |
| `top_p` | float | 1.0 | 0.0-1.0 | 核采样概率 |
| `frequency_penalty` | float | 0.0 | -2.0-2.0 | 频率惩罚 |
| `presence_penalty` | float | 0.0 | -2.0-2.0 | 存在惩罚 |
| `stop` | string/array | null | - | 停止序列 |
| `stream` | boolean | false | - | 是否流式输出 |
| `logprobs` | boolean | false | - | 是否返回log概率 |
| `top_logprobs` | integer | null | 0-20 | 返回top-k log概率 |

---

## 💬 Messages 格式规范

### 消息角色

DeepSeek API 支持以下角色：

| 角色 | 说明 | 使用场景 |
|------|------|---------|
| `system` | 系统消息 | 设置AI助手的行为和角色 |
| `user` | 用户消息 | 用户的输入和问题 |
| `assistant` | 助手消息 | AI的回复（用于多轮对话） |

### 消息结构

```python
{
    "role": "system" | "user" | "assistant",
    "content": "消息内容"
}
```

### ⚠️ 重要规则

1. **messages 必须是数组**: 即使只有一条消息，也必须用数组包裹
2. **role 必须是有效值**: 只能是 `system`, `user`, `assistant` 之一
3. **content 不能为空**: 每条消息的 content 必须有内容
4. **顺序要求**: 通常以 system 开头，然后是 user/assistant 交替

### 正确示例

```python
# ✅ 正确：单条消息
messages = [
    {"role": "user", "content": "你好"}
]

# ✅ 正确：多轮对话
messages = [
    {"role": "system", "content": "你是一个健身教练"},
    {"role": "user", "content": "如何增肌？"},
    {"role": "assistant", "content": "增肌需要..."},
    {"role": "user", "content": "具体怎么做？"}
]
```

### 错误示例

```python
# ❌ 错误：不是数组
messages = {"role": "user", "content": "你好"}

# ❌ 错误：role 拼写错误
messages = [{"role": "users", "content": "你好"}]

# ❌ 错误：content 为空
messages = [{"role": "user", "content": ""}]

# ❌ 错误：缺少 role 或 content
messages = [{"role": "user"}]
messages = [{"content": "你好"}]
```

---

## 🔧 Python 调用示例

### 基础调用

```python
import httpx
import asyncio

async def call_deepseek(query: str, max_tokens: int = 2000, temperature: float = 0.7):
    """调用 DeepSeek API"""
    
    # 构建请求
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": query}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    # 发送请求
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        # 检查响应
        response.raise_for_status()
        result = response.json()
        
        # 提取回答
        answer = result["choices"][0]["message"]["content"]
        return answer
```

### 带系统提示的调用

```python
async def call_deepseek_with_system(
    query: str,
    system_prompt: str,
    max_tokens: int = 2000,
    temperature: float = 0.7
):
    """带系统提示的 DeepSeek 调用"""
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
```

### 多轮对话调用

```python
async def call_deepseek_multi_turn(
    conversation_history: list,
    new_query: str,
    max_tokens: int = 2000,
    temperature: float = 0.7
):
    """多轮对话调用"""
    
    # 添加新的用户消息
    messages = conversation_history + [
        {"role": "user", "content": new_query}
    ]
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        
        # 更新对话历史
        messages.append({"role": "assistant", "content": answer})
        
        return answer, messages
```

---

## ⚠️ 常见错误和解决方案

### 错误 400: Bad Request

**原因**：请求格式不正确

**常见情况**：

1. **messages 不是数组**
   ```python
   # ❌ 错误
   "messages": {"role": "user", "content": "你好"}
   
   # ✅ 正确
   "messages": [{"role": "user", "content": "你好"}]
   ```

2. **role 值无效**
   ```python
   # ❌ 错误
   {"role": "users", "content": "你好"}
   
   # ✅ 正确
   {"role": "user", "content": "你好"}
   ```

3. **content 为空或缺失**
   ```python
   # ❌ 错误
   {"role": "user", "content": ""}
   {"role": "user"}
   
   # ✅ 正确
   {"role": "user", "content": "你好"}
   ```

4. **max_tokens 超出范围**
   ```python
   # ❌ 错误
   "max_tokens": 100000  # 超过4096
   
   # ✅ 正确
   "max_tokens": 4096  # 最大值
   ```

### 错误 401: Unauthorized

**原因**：API Key 无效或缺失

**解决方案**：
```python
# 检查 API Key
headers = {
    "Authorization": f"Bearer {API_KEY}",  # 确保有 "Bearer " 前缀
    "Content-Type": "application/json"
}
```

### 错误 429: Too Many Requests

**原因**：请求频率超限

**解决方案**：
```python
import asyncio

# 添加重试逻辑
for attempt in range(3):
    try:
        response = await client.post(...)
        break
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            await asyncio.sleep(2 ** attempt)  # 指数退避
            continue
        raise
```

### 错误 500: Internal Server Error

**原因**：服务器内部错误

**解决方案**：
- 重试请求
- 检查请求是否过大
- 联系 DeepSeek 技术支持

---

## 📊 响应格式

### 标准响应

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "这是AI的回答内容"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

### 提取回答

```python
# 提取回答内容
answer = result["choices"][0]["message"]["content"]

# 提取token使用情况
usage = result["usage"]
prompt_tokens = usage["prompt_tokens"]
completion_tokens = usage["completion_tokens"]
total_tokens = usage["total_tokens"]
```

---

## 🎯 最佳实践

### 1. 参数验证

```python
def validate_deepseek_params(messages, max_tokens, temperature):
    """验证 DeepSeek API 参数"""
    
    # 验证 messages
    assert isinstance(messages, list), "messages 必须是数组"
    assert len(messages) > 0, "messages 不能为空"
    
    for msg in messages:
        assert "role" in msg, "消息缺少 role 字段"
        assert "content" in msg, "消息缺少 content 字段"
        assert msg["role"] in ["system", "user", "assistant"], f"无效的 role: {msg['role']}"
        assert len(msg["content"]) > 0, "content 不能为空"
    
    # 验证 max_tokens
    assert 1 <= max_tokens <= 4096, f"max_tokens 必须在 1-4096 之间: {max_tokens}"
    
    # 验证 temperature
    assert 0.0 <= temperature <= 2.0, f"temperature 必须在 0.0-2.0 之间: {temperature}"
```

### 2. 错误处理

```python
async def call_deepseek_with_retry(
    messages: list,
    max_tokens: int = 2000,
    temperature: float = 0.7,
    max_retries: int = 3
):
    """带重试的 DeepSeek 调用"""
    
    for attempt in range(max_retries):
        try:
            # 验证参数
            validate_deepseek_params(messages, max_tokens, temperature)
            
            # 调用 API
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # 400 错误不重试，直接抛出
                logger.error(f"DeepSeek 400 错误: {e.response.text}")
                raise
            elif e.response.status_code == 429:
                # 429 错误重试，指数退避
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            raise
            
        except httpx.ReadTimeout:
            # 超时重试
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            raise
```

### 3. 日志记录

```python
import logging

logger = logging.getLogger(__name__)

async def call_deepseek_with_logging(messages, max_tokens, temperature):
    """带日志的 DeepSeek 调用"""
    
    logger.info(f"调用 DeepSeek API:")
    logger.info(f"  - 消息数: {len(messages)}")
    logger.info(f"  - max_tokens: {max_tokens}")
    logger.info(f"  - temperature: {temperature}")
    
    try:
        result = await call_deepseek(messages, max_tokens, temperature)
        logger.info(f"DeepSeek 调用成功: 响应长度={len(result)}")
        return result
        
    except Exception as e:
        logger.error(f"DeepSeek 调用失败: {e}")
        raise
```

---

## 🔍 调试技巧

### 1. 打印请求内容

```python
import json

# 打印请求 payload
payload = {
    "model": "deepseek-chat",
    "messages": messages,
    "max_tokens": max_tokens,
    "temperature": temperature
}

print("DeepSeek 请求:")
print(json.dumps(payload, indent=2, ensure_ascii=False))
```

### 2. 检查响应内容

```python
# 打印完整响应
print("DeepSeek 响应:")
print(json.dumps(result, indent=2, ensure_ascii=False))

# 检查错误响应
if response.status_code != 200:
    print(f"错误状态码: {response.status_code}")
    print(f"错误内容: {response.text}")
```

### 3. 使用 curl 测试

```bash
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

---

## 📌 项目中的应用

### 当前实现位置

- **LLM客户端**: `daml-rag-server/src/framework/clients/llm_client.py`
- **配置文件**: `daml-rag-server/config/llm_response_config.yaml`

### 需要修复的问题

根据日志分析，当前代码可能存在以下问题：

1. **messages 格式错误**: 可能没有正确构建为数组
2. **参数验证缺失**: 没有验证 max_tokens 范围
3. **错误处理不完善**: 400 错误应该立即停止，不应重试

### 建议的修复方案

参考本文档的最佳实践部分，在 `llm_client.py` 中：

1. 添加参数验证函数
2. 确保 messages 始终是数组格式
3. 改进错误处理逻辑
4. 添加详细的日志记录

---

## 📚 参考资源

- [DeepSeek API 官方文档](https://api-docs.deepseek.com/zh-cn/)
- [DeepSeek 快速开始](https://api-docs.deepseek.com/zh-cn/quick_start/quick_start)
- [DeepSeek 错误码](https://api-docs.deepseek.com/zh-cn/api/error_codes)
- [DeepSeek 定价](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-18  
**版本**: v1.0.0
