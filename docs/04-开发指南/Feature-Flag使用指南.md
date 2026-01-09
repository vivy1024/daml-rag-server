# Feature Flag使用指南

**状态**: ✅ 已完成
**版本**: v1.0.0
**创建日期**: 2026-01-10

---

## 概述

本文档说明如何使用 `USE_NEW_CACHE` feature flag 在新旧缓存系统之间切换。

## Feature Flag配置

### 环境变量

```bash
USE_NEW_CACHE=false  # 使用旧缓存系统（默认）
USE_NEW_CACHE=true   # 使用新缓存系统
```

### 支持的值

| 值 | 说明 | 使用的缓存系统 |
|---|---|---|
| `false` (默认) | 使用旧缓存 | IntelligentUserCache, IntelligentMembershipCache, SmartPreloader |
| `true` | 使用新缓存 | UserProfileCache, MembershipCache, WarmupManager |
| `1` | 使用新缓存 | 同上 |
| `yes` | 使用新缓存 | 同上 |

## 切换方式

### 方式1：修改 .env 文件（推荐）

```bash
# 编辑 daml-rag-server/.env
USE_NEW_CACHE=true

# 重启服务
docker restart fitness_daml_rag
```

### 方式2：Docker Compose环境变量

```yaml
# docker-compose.yml
services:
  fitness_daml_rag:
    environment:
      - USE_NEW_CACHE=true
```

### 方式3：Docker命令行

```bash
docker run -e USE_NEW_CACHE=true ...
```

## 影响范围

### 1. 用户档案缓存

**旧缓存** (`USE_NEW_CACHE=false`):
- 使用 `IntelligentUserCache`
- 位置: `framework/storage/intelligent_user_profile_cache.py`
- 特点: 多层缓存（内存+Redis）、热度追踪

**新缓存** (`USE_NEW_CACHE=true`):
- 使用 `UserProfileCache`
- 位置: `framework/storage/user_profile_cache.py`
- 特点: 基于UnifiedCache、简化逻辑、TTL=5分钟

### 2. 会员缓存

**旧缓存** (`USE_NEW_CACHE=false`):
- 使用 `IntelligentMembershipCache`
- 位置: `framework/storage/intelligent_membership_cache.py`
- 特点: 多层缓存、热度追踪

**新缓存** (`USE_NEW_CACHE=true`):
- 使用 `MembershipCache`
- 位置: `framework/storage/membership_cache.py`
- 特点: 基于UnifiedCache、简化逻辑、TTL=10分钟

### 3. 预加载系统

**旧预加载器** (`USE_NEW_CACHE=false`):
- 使用 `SmartPreloader`
- 位置: `framework/storage/smart_preloader.py`
- 特点: 智能预加载、热度追踪

**新预加载器** (`USE_NEW_CACHE=true`):
- 使用 `WarmupManager`
- 位置: `framework/storage/warmup.py`
- 特点: 统一预加载管理、可配置

## 代码实现

### Singletons模块

```python
# src/applications/fitness/workflow/singletons.py

def _use_new_cache() -> bool:
    """检查是否使用新缓存系统"""
    use_new = os.getenv('USE_NEW_CACHE', 'false').lower() in ('true', '1', 'yes')
    return use_new

def get_user_cache(backend_client=None, redis_client=None):
    """根据flag选择新旧用户缓存"""
    global _user_cache_instance
    if _user_cache_instance is None:
        if _use_new_cache():
            # 使用新缓存
            from ....framework.storage.user_profile_cache import UserProfileCache
            from ....framework.storage.unified_cache import UnifiedCache, CacheConfig
            
            cache_config = CacheConfig()
            unified_cache = UnifiedCache(redis_client=redis_client, config=cache_config)
            _user_cache_instance = UserProfileCache(
                unified_cache=unified_cache,
                backend_client=backend_client
            )
        else:
            # 使用旧缓存（默认）
            from ....framework.storage.intelligent_user_profile_cache import IntelligentUserCache
            _user_cache_instance = IntelligentUserCache(...)
    return _user_cache_instance
```

### API路由

```python
# src/api/routes/user.py

def _use_new_cache() -> bool:
    """检查是否使用新缓存系统"""
    use_new = os.getenv('USE_NEW_CACHE', 'false').lower() in ('true', '1', 'yes')
    return use_new

@router.post("/v1/user/warmup")
async def warmup_user(request: WarmupRequest):
    """根据flag选择新旧预加载器"""
    if _use_new_cache():
        # 使用新预加载器
        from ...framework.storage.warmup import get_warmup_manager
        warmup_manager = get_warmup_manager()
        await warmup_manager.preload_memberships([user_id])
    else:
        # 使用旧预加载器
        from ...framework.storage.smart_preloader import get_smart_preloader
        smart_preloader = get_smart_preloader()
        await smart_preloader.preload_for_step3(user_id)
```

## 验证方法

### 1. 检查环境变量

```bash
docker exec fitness_daml_rag env | grep USE_NEW_CACHE
```

### 2. 运行集成测试

```bash
docker exec fitness_daml_rag python /app/test_cache_integration.py
```

### 3. 查看日志

```bash
# 启用新缓存时，日志中会显示：
# ✅ UserProfileCache（新缓存）初始化完成
# ✅ MembershipCache（新缓存）初始化完成

# 使用旧缓存时，日志中会显示：
# ✅ IntelligentUserCache（旧缓存）初始化完成
# ✅ IntelligentMembershipCache（旧缓存）初始化完成

docker logs fitness_daml_rag | grep "缓存.*初始化完成"
```

## 迁移计划

### Phase 2: 并行运行（当前阶段）

- ✅ 添加feature flag支持
- ✅ 默认使用旧缓存（`USE_NEW_CACHE=false`）
- ⏳ 在测试环境验证新缓存
- ⏳ 性能对比测试

### Phase 3: 切换迁移

- 设置 `USE_NEW_CACHE=true`
- 监控运行状态
- 验证功能正常

### Phase 4: 清理旧代码

- 删除旧缓存模块
- 移除feature flag
- 更新文档

## 注意事项

1. **默认使用旧缓存**: 确保向后兼容，不影响现有功能
2. **API接口不变**: 无论使用新旧缓存，API接口和响应格式保持一致
3. **PHP后端无感知**: PHP后端无需修改代码
4. **可快速回滚**: 如果新缓存出现问题，设置 `USE_NEW_CACHE=false` 即可回滚

## 性能对比

| 指标 | 旧缓存 | 新缓存 | 目标 |
|---|---|---|---|
| 代码大小 | ~113KB | ~60KB | 减少47% |
| 缓存命中率 | >90% | >90% | 保持 |
| 响应时间 | <10ms | <10ms | 保持 |
| 内存使用 | ~100MB | ~80MB | 减少20% |

## 相关文档

- **需求文档**: `.kiro/specs/storage-layer-cleanup/requirements.md`
- **设计文档**: `.kiro/specs/storage-layer-cleanup/design.md`
- **任务列表**: `.kiro/specs/storage-layer-cleanup/tasks.md`

---

**维护者**: 薛小川
**版本**: v1.0.0
**创建日期**: 2026-01-10
