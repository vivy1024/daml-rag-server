# CacheManager使用指南

**版本**: v1.0.0  
**更新日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

CacheManager 是一个统一的缓存管理接口，用于在 DAG 编排器中管理用户档案和会员权限的缓存。它基于 `IntelligentUserCache` 和 `IntelligentMembershipCache` 提供简化的 API。

## 核心特性

1. **统一接口**：简化缓存操作，提供一致的 API
2. **多级缓存**：内存 + Redis + 后端 API 三级缓存
3. **智能统计**：实时跟踪缓存命中率和响应时间
4. **降级支持**：自动处理降级数据
5. **灵活配置**：支持自定义 TTL 和缓存策略

## 快速开始

### 1. 初始化 CacheManager

```python
from src.framework.orchestration import CacheManager
from src.framework.storage import IntelligentUserCache, IntelligentMembershipCache

# 创建底层缓存实例
user_cache = IntelligentUserCache(
    backend_client=backend_client,
    redis_client=redis_client
)

membership_cache = IntelligentMembershipCache(
    backend_client=backend_client,
    redis_client=redis_client
)

# 创建 CacheManager
cache_manager = CacheManager(
    user_cache=user_cache,
    membership_cache=membership_cache,
    user_profile_ttl=300,  # 5分钟
    membership_ttl=600     # 10分钟
)
```

### 2. 获取用户档案

```python
# 从缓存获取用户档案
user_profile = await cache_manager.get_user_profile(user_id="123")

if user_profile:
    print(f"用户年龄: {user_profile['basic_info']['age']}")
    print(f"健身目标: {user_profile['fitness_goals']['primary_goal']}")
    
    # 检查是否是降级数据
    if user_profile.get('_fallback'):
        print("⚠️ 使用降级用户档案")
else:
    print("❌ 未找到用户档案")
```

### 3. 获取会员权限

```python
# 从缓存获取会员权限
membership = await cache_manager.get_membership_permissions(user_id="123")

if membership:
    print(f"会员等级: {membership['tier']}")
    print(f"每日查询限制: {membership['permissions']['max_queries_per_day']}")
    
    # 检查是否是降级数据
    if membership.get('_fallback'):
        print("⚠️ 使用降级会员权限（默认免费用户）")
else:
    print("❌ 未找到会员权限")
```

### 4. 强制刷新缓存

```python
# 强制从后端API重新加载
user_profile = await cache_manager.get_user_profile(
    user_id="123",
    force_refresh=True
)
```

### 5. 使缓存失效

```python
# 使用户档案缓存失效
await cache_manager.invalidate_user_profile(user_id="123")

# 使会员权限缓存失效
await cache_manager.invalidate_membership(user_id="123")

# 使所有缓存失效
await cache_manager.invalidate_all(user_id="123")
```

### 6. 获取缓存统计

```python
# 获取缓存统计信息
stats = cache_manager.get_statistics()

print(f"总请求数: {stats['total_requests']}")
print(f"总命中率: {stats['hit_rate']}%")
print(f"用户档案命中率: {stats['user_profile_hit_rate']}%")
print(f"会员权限命中率: {stats['membership_hit_rate']}%")
print(f"平均响应时间: {stats['avg_response_time_ms']}ms")
```

## 在 DAG 编排器中使用

### 集成到 EnhancedDAGOrchestrator

```python
class EnhancedDAGOrchestrator:
    def __init__(self, ...):
        # 初始化缓存管理器
        self.cache_manager = CacheManager(
            user_cache=self.user_cache,
            membership_cache=self.membership_cache
        )
    
    async def execute_dag(self, user_id: str, query: str):
        # 1. 预加载用户档案（使用缓存）
        user_profile = await self.cache_manager.get_user_profile(user_id)
        
        # 2. 检查会员权限（使用缓存）
        membership = await self.cache_manager.get_membership_permissions(user_id)
        
        # 3. 执行 DAG 任务
        # ...
        
        # 4. 记录缓存统计
        stats = self.cache_manager.get_statistics()
        logger.info(f"缓存命中率: {stats['hit_rate']}%")
```

## 缓存策略

### TTL 配置

| 缓存类型 | 默认 TTL | 说明 |
|---------|---------|------|
| 用户档案 | 300秒（5分钟） | 用户基本信息、健身目标等 |
| 会员权限 | 600秒（10分钟） | 会员等级、权限配置等 |
| 降级数据 | 60秒（1分钟） | 降级数据使用更短的 TTL |

### 缓存层级

```
请求 → 内存缓存（L1）→ Redis缓存（L2）→ 后端API（L3）
         ↓ 命中           ↓ 命中           ↓ 命中
       立即返回         回填L1          回填L1+L2
```

## 降级策略

### 用户档案降级

当后端 API 超时或失败时，返回默认用户档案：

```python
{
    'user_id': user_id,
    'basic_info': {
        'age': 25,
        'gender': 'unknown',
        'height': 170,
        'weight': 65
    },
    'fitness_goals': {
        'primary_goal': 'general_fitness'
    },
    '_fallback': True  # 标记为降级数据
}
```

### 会员权限降级

当后端 API 超时或失败时，返回默认免费用户权限：

```python
{
    'user_id': user_id,
    'tier': 'free',
    'status': 'active',
    'permissions': {
        'max_queries_per_day': 10,
        'can_use_advanced_features': False
    },
    '_fallback': True  # 标记为降级数据
}
```

## 性能优化

### 1. 预加载用户档案

```python
# 在用户登录时预加载
await cache_manager.get_user_profile(user_id)
await cache_manager.get_membership_permissions(user_id)
```

### 2. 批量预加载

```python
# 预加载多个用户
user_ids = ["123", "456", "789"]
tasks = [
    cache_manager.get_user_profile(uid)
    for uid in user_ids
]
await asyncio.gather(*tasks)
```

### 3. 监控缓存命中率

```python
# 定期检查缓存命中率
stats = cache_manager.get_statistics()
if stats['hit_rate'] < 70:
    logger.warning(f"缓存命中率过低: {stats['hit_rate']}%")
```

## 日志记录

CacheManager 提供详细的日志记录：

```
✅ 用户档案缓存命中: user_id=123
❌ 用户档案缓存未命中: user_id=456
⚠️ 使用降级用户档案: user_id=789
💾 缓存用户档案: user_id=123, ttl=300s
```

## 错误处理

```python
try:
    user_profile = await cache_manager.get_user_profile(user_id)
    if user_profile is None:
        # 处理未找到的情况
        logger.warning(f"用户档案未找到: {user_id}")
        return default_profile
    
    if user_profile.get('_fallback'):
        # 处理降级数据
        logger.warning(f"使用降级用户档案: {user_id}")
        # 可以选择重试或使用降级数据
    
except Exception as e:
    logger.error(f"获取用户档案失败: {e}")
    return default_profile
```

## 最佳实践

1. **始终检查降级标记**：检查 `_fallback` 字段来判断是否是降级数据
2. **合理设置 TTL**：根据数据更新频率调整 TTL
3. **监控缓存命中率**：定期检查缓存性能
4. **及时失效缓存**：当数据更新时，及时使缓存失效
5. **使用预加载**：在用户登录时预加载常用数据

## 相关文档

- [IntelligentUserCache 实现](../02-数据层/06-智能用户档案缓存.md)
- [IntelligentMembershipCache 实现](../02-数据层/07-智能会员权限缓存.md)
- [DAG 编排器实现](./01-DAG编排器实现.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
