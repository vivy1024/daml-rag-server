# Feature Flag使用指南

**版本**: v1.0.0
**创建日期**: 2026-01-10
**状态**: ✅ 已完成

---

## 概述

本文档说明如何使用 `USE_NEW_CACHE` feature flag 在新旧缓存系统之间切换。

---

## 配置说明

### 环境变量

在 `.env` 或 `.env.production` 中配置：

```bash
# 使用新缓存系统（false=旧缓存，true=新缓存）
USE_NEW_CACHE=false
```

### 支持的值

| 值 | 说明 |
|---|---|
| `false` | 使用旧缓存系统（默认） |
| `true` | 使用新缓存系统 |
| `1` | 使用新缓存系统 |
| `yes` | 使用新缓存系统 |

---

## 缓存系统对比

### 旧缓存系统（默认）

| 组件 | 模块 | 说明 |
|------|------|------|
| 用户档案缓存 | `IntelligentUserCache` | 智能用户档案缓存 |
| 会员缓存 | `IntelligentMembershipCache` | 智能会员权限缓存 |
| 预加载器 | `SmartPreloader` | 智能预加载器 |

### 新缓存系统

| 组件 | 模块 | 说明 |
|------|------|------|
| 统一缓存 | `UnifiedCache` | 统一缓存基础 |
| 用户档案缓存 | `UserProfileCache` | 基于UnifiedCache |
| 会员缓存 | `MembershipCache` | 基于UnifiedCache |
| 预加载器 | `WarmupManager` | 统一预加载管理器 |

---

## 切换步骤

### 1. 本地开发环境

```bash
# 1. 修改配置
# 编辑 daml-rag-server/.env
USE_NEW_CACHE=true

# 2. 重启容器
docker-compose restart fitness_daml_rag

# 3. 查看日志确认
docker logs fitness_daml_rag | grep -i cache
```

**预期日志**：
```
✅ UserProfileCache（新缓存）初始化完成
✅ MembershipCache（新缓存）初始化完成
```

### 2. 生产环境（Zeabur）

```bash
# 1. 修改配置
# 编辑 daml-rag-server/.env.production
USE_NEW_CACHE=true

# 2. 提交并推送
git add .env.production
git commit -m "feat(storage): 启用新缓存系统"
git push origin main

# 3. Zeabur自动重新构建部署

# 4. 查看日志确认
# 在Zeabur控制台查看fitness_daml_rag服务日志
```

---

## 验证方法

### 方法1：查看启动日志

```bash
# 本地环境
docker logs fitness_daml_rag | grep -i "cache.*初始化完成"

# 预期输出（旧缓存）：
# ✅ IntelligentUserCache（旧缓存）初始化完成
# ✅ IntelligentMembershipCache（旧缓存）初始化完成

# 预期输出（新缓存）：
# ✅ UserProfileCache（新缓存）初始化完成
# ✅ MembershipCache（新缓存）初始化完成
```

### 方法2：测试预热接口

```bash
# 调用预热接口
curl -X POST http://localhost:8001/v1/user/warmup \
  -H "Content-Type: application/json" \
  -d '{"user_id": "123"}'

# 查看日志
docker logs fitness_daml_rag | tail -20

# 预期日志（旧缓存）：
# ✅ 会员数据预热已启动（旧预加载器）: user_id=123

# 预期日志（新缓存）：
# ✅ 会员数据预热已启动（新预加载器）: user_id=123
```

---

## 回滚方法

如果新缓存出现问题，立即回滚：

```bash
# 1. 修改配置
USE_NEW_CACHE=false

# 2. 重启服务
docker-compose restart fitness_daml_rag

# 3. 验证旧缓存正常工作
docker logs fitness_daml_rag | grep -i "IntelligentUserCache"
```

---

## 注意事项

1. **默认使用旧缓存**：`USE_NEW_CACHE=false` 是默认值，确保向后兼容
2. **重启生效**：修改配置后必须重启容器才能生效
3. **日志确认**：切换后务必查看日志确认使用的是正确的缓存系统
4. **API兼容**：新旧缓存对外API接口完全兼容，PHP后端无需修改

---

## 相关文档

- **存储层重构设计**: `.kiro/specs/storage-layer-cleanup/design.md`
- **实施任务列表**: `.kiro/specs/storage-layer-cleanup/tasks.md`
- **CHANGELOG**: `daml-rag-server/CHANGELOG.md`

---

**维护者**: 薛小川
**版本**: v1.0.0
**创建日期**: 2026-01-10
