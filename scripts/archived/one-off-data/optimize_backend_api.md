# 🔧 Laravel后端API性能优化指南

## 问题分析

DAML-RAG的会员权限检查需要调用Laravel后端API，但响应时间超过2000ms，导致性能瓶颈。

## 优化方案

### 方案1: 数据库查询优化

```php
<?php
// app/Http/Controllers/UserMembershipController.php

class UserMembershipController extends Controller
{
    /**
     * 获取用户会员权限 - 优化版本
     */
    public function getUserMembership($userId)
    {
        $startTime = microtime(true);

        // ✅ 1. 使用缓存
        $cacheKey = "user_membership_{$userId}";
        $membership = Cache::remember($cacheKey, 3600, function () use ($userId) {
            return $this->queryMembership($userId);
        });

        $executionTime = (microtime(true) - $startTime) * 1000;

        return response()->json([
            'success' => true,
            'data' => $membership,
            'execution_time_ms' => round($executionTime, 2),
            'cache_hit' => Cache::has($cacheKey)
        ]);
    }

    /**
     * 优化的会员权限查询
     */
    private function queryMembership($userId)
    {
        // ✅ 2. 使用索引优化查询
        return DB::table('users')
            ->select([
                'users.id',
                'users.name',
                'memberships.tier',
                'memberships.status',
                'memberships.started_at',
                'memberships.expired_at',
                'memberships.permissions'
            ])
            ->join('memberships', 'users.id', '=', 'memberships.user_id')
            ->where('users.id', $userId)
            ->where('memberships.status', 'active')
            ->first();
    }
}
```

### 方案2: 数据库索引优化

```sql
-- 添加复合索引
ALTER TABLE memberships ADD INDEX idx_user_status (user_id, status);
ALTER TABLE memberships ADD INDEX idx_user_tier (user_id, tier);

-- 添加覆盖索引（包含所有查询字段）
ALTER TABLE memberships ADD INDEX idx_user_status_cover (
    user_id, status, tier, started_at, expired_at, permissions
);
```

### 方案3: Redis缓存层

```php
<?php
// config/cache.php 中配置Redis
'redis' => [
    'client' => 'predis',
    'default' => [
        'host' => env('REDIS_HOST', '127.0.0.1'),
        'password' => env('REDIS_PASSWORD', null),
        'port' => env('REDIS_PORT', 6379),
        'database' => 0,
    ],
],
```

### 方案4: API响应优化

```php
<?php
// app/Http/Middleware/OptimizeApiResponse.php

class OptimizeApiResponse
{
    public function handle($request, Closure $next)
    {
        $response = $next($request);

        // ✅ 1. 启用Gzip压缩
        $response->headers->set('Content-Encoding', 'gzip');

        // ✅ 2. 设置缓存头
        $response->headers->set('Cache-Control', 'public, max-age=3600');

        // ✅ 3. 优化JSON响应
        $response->setEncodingOptions(JSON_UNESCAPED_UNICODE);

        return $response;
    }
}
```

### 方案5: 批量预加载

```php
<?php
// 批量获取多个用户的会员权限
public function getBatchMembership(Request $request)
{
    $userIds = $request->input('user_ids', []);

    // ✅ 批量查询（避免N+1问题）
    $memberships = DB::table('users')
        ->select([
            'users.id',
            'memberships.tier',
            'memberships.status'
        ])
        ->join('memberships', 'users.id', '=', 'memberships.user_id')
        ->whereIn('users.id', $userIds)
        ->where('memberships.status', 'active')
        ->pluck('memberships', 'users.id');

    return response()->json([
        'success' => true,
        'data' => $memberships
    ]);
}
```

## 测试验证

```bash
# 测试API响应时间
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/api/membership/1

# curl-format.txt内容：
echo '
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
'
```

## 预期效果

| 优化项 | 优化前 | 优化后 | 提升 |
|--------|--------|--------|------|
| 数据库查询 | 800ms | 50ms | ⬇️ 94% |
| API响应时间 | 2000ms | 200ms | ⬇️ 90% |
| 缓存命中率 | 0% | 95% | ⬆️ 95% |

## 监控建议

```php
// 在Laravel中添加性能监控
Log::channel('performance')->info('Membership API', [
    'user_id' => $userId,
    'execution_time_ms' => $executionTime,
    'cache_hit' => $cacheHit,
    'memory_usage' => memory_get_usage(true)
]);
```
