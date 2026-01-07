# -*- coding: utf-8 -*-
"""
Intelligent User Profile Cache - 智能用户档案缓存系统

基于使用模式和访问频率的智能预加载和缓存策略

核心功能：
1. 智能预加载：基于用户行为模式预测需要的档案
2. 多级缓存：内存 + Redis + 数据库分层存储
3. 缓存策略：LRU + TTL + 访问频率权重
4. 性能监控：缓存命中率、预加载效率
5. 自动刷新：基于变更检测的自动更新
6. 熔断器防护：防止缓存雪崩 (Requirements 4.4)

版本: v2.0.0
日期: 2025-12-29
作者: 薛小川
"""

import logging
import asyncio
import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import OrderedDict, defaultdict
import weakref

# 导入熔断器组件
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenException,
    user_profile_circuit_breaker
)

# 导入热度图组件 (Requirements 5.1)
from .heat_map import HeatMap, get_heat_map

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别枚举"""
    MEMORY = "memory"      # 内存缓存（最快）
    REDIS = "redis"        # Redis缓存（中等）
    DATABASE = "database"  # 数据库（最慢，但最全）


class UserProfileStatus(Enum):
    """用户档案状态枚举"""
    NOT_LOADED = "not_loaded"      # 未加载
    LOADING = "loading"            # 加载中
    LOADED = "loaded"              # 已加载
    STALE = "stale"                # 过期
    ERROR = "error"                # 加载错误


class UserProfileNotFoundError(Exception):
    """用户档案不存在异常 (Requirements 2.6)"""
    def __init__(self, user_id: str, message: str = None):
        self.user_id = user_id
        self.message = message or f"用户档案不存在: {user_id}"
        super().__init__(self.message)


@dataclass
class UserProfileEntry:
    """用户档案缓存条目"""
    user_id: str
    profile_data: Optional[Dict[str, Any]]
    status: UserProfileStatus
    created_at: datetime
    last_accessed: datetime
    last_updated: datetime
    access_count: int = 0
    size_bytes: int = 0
    checksum: str = ""
    ttl_seconds: int = 3600  # 1小时TTL
    preload_priority: float = 0.0  # 预加载优先级

    def mark_accessed(self):
        """标记访问"""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def is_expired(self) -> bool:
        """检查是否过期"""
        return (datetime.now() - self.last_updated).total_seconds() > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "profile_data": self.profile_data,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "access_count": self.access_count,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "ttl_seconds": self.ttl_seconds,
            "preload_priority": self.preload_priority
        }


@dataclass
class PreloadPrediction:
    """预加载预测结果"""
    user_id: str
    probability: float
    reason: str
    estimated_time_s: float
    priority_score: float


@dataclass
class CacheConfig:
    """缓存配置"""
    # 内存缓存配置
    max_memory_entries: int = 1000  # 从200增加到1000 (Requirements 2.4)
    max_memory_size_mb: int = 100   # 相应增加内存限制

    # Redis缓存配置
    redis_ttl_seconds: int = 3600   # 从600增加到3600（1小时）(Requirements 2.5)
    redis_key_prefix: str = "user_profile:"

    # 预加载配置
    preload_enabled: bool = True
    preload_threshold: float = 0.7  # 预加载概率阈值
    max_concurrent_preloads: int = 5
    preload_window_minutes: int = 30  # 预加载时间窗口

    # 刷新配置
    auto_refresh_enabled: bool = True
    refresh_interval_minutes: int = 15
    checksum_validation: bool = True

    # 监控配置
    stats_collection_enabled: bool = True
    performance_logging: bool = True


class IntelligentUserCache:
    """
    智能用户档案缓存系统

    核心特性：
    1. 多级缓存：内存 + Redis + 数据库
    2. 智能预加载：基于用户行为模式预测
    3. 自适应TTL：根据访问频率动态调整
    4. 并发安全：支持高并发访问
    5. 性能监控：详细的缓存性能统计
    6. 熔断器防护：防止缓存雪崩 (Requirements 4.4)
    """

    def __init__(
        self,
        backend_client=None,
        redis_client=None,
        config: Optional[CacheConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        heat_map: Optional[HeatMap] = None
    ):
        """
        初始化智能用户档案缓存

        Args:
            backend_client: 后端客户端
            redis_client: Redis客户端
            config: 缓存配置
            circuit_breaker: 熔断器实例（可选，默认使用全局实例）
            heat_map: 热度图实例（可选，默认使用全局实例）(Requirements 5.1)
        """
        self.backend_client = backend_client
        self.redis_client = redis_client
        self.config = config or CacheConfig()
        
        # 熔断器 (Requirements 4.4)
        self.circuit_breaker = circuit_breaker or user_profile_circuit_breaker
        
        # 热度图 (Requirements 5.1)
        self.heat_map = heat_map or get_heat_map()

        # 内存缓存（使用OrderedDict实现LRU）
        self.memory_cache: OrderedDict[str, UserProfileEntry] = OrderedDict()
        self.current_memory_size_bytes = 0

        # 加载状态跟踪
        self.loading_status: Dict[str, asyncio.Task] = {}

        # 预加载队列
        self.preload_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.preload_workers: List[asyncio.Task] = []

        # 访问模式分析
        self.access_patterns: Dict[str, List[datetime]] = defaultdict(list)

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "database_hits": 0,
            "misses": 0,
            "preload_successes": 0,
            "preload_failures": 0,
            "auto_refreshes": 0,
            "cache_evictions": 0,
            "errors": 0,
            "circuit_breaker_rejections": 0  # 熔断器拒绝计数
        }

        # 性能指标
        self.performance_metrics = {
            "avg_response_time_ms": 0.0,
            "p95_response_time_ms": 0.0,
            "cache_hit_rate": 0.0,
            "preload_efficiency": 0.0
        }

        # 启动预加载工作线程
        if self.config.preload_enabled:
            self._start_preload_workers()

        # 启动自动刷新任务
        if self.config.auto_refresh_enabled:
            asyncio.create_task(self._auto_refresh_loop())

        logger.info(
            f"IntelligentUserCache initialized: "
            f"memory_entries={self.config.max_memory_entries}, "
            f"preload_enabled={self.config.preload_enabled}, "
            f"circuit_breaker={self.circuit_breaker.name}"
        )

    def _start_preload_workers(self):
        """启动预加载工作线程"""
        for i in range(self.config.max_concurrent_preloads):
            worker = asyncio.create_task(self._preload_worker(f"preload_worker_{i}"))
            self.preload_workers.append(worker)

    async def _preload_worker(self, worker_name: str):
        """预加载工作线程"""
        logger.info(f"启动预加载工作线程: {worker_name}")

        while True:
            try:
                # 从队列获取预加载任务
                prediction = await asyncio.wait_for(
                    self.preload_queue.get(),
                    timeout=1.0
                )

                # 执行预加载
                await self._execute_preload(prediction)
                self.preload_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"预加载工作线程错误 {worker_name}: {e}")

    async def _execute_preload(self, prediction: PreloadPrediction):
        """执行预加载"""
        user_id = prediction.user_id

        # 检查是否已经在内存中
        if user_id in self.memory_cache:
            entry = self.memory_cache[user_id]
            if not entry.is_expired():
                return

        try:
            # 异步加载用户档案
            profile_data = await self._load_profile_from_backend(user_id)
            if profile_data:
                await self._store_in_cache(user_id, profile_data, CacheLevel.MEMORY)
                self.stats["preload_successes"] += 1
                logger.debug(f"预加载成功: {user_id}")
            else:
                self.stats["preload_failures"] += 1

        except Exception as e:
            self.stats["preload_failures"] += 1
            logger.error(f"预加载失败 {user_id}: {e}")

    async def get_user_profile(
        self,
        user_id: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户档案（智能缓存策略）

        Args:
            user_id: 用户ID
            force_refresh: 是否强制刷新

        Returns:
            Optional[Dict[str, Any]]: 用户档案数据
        """
        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # 记录访问模式
            self._record_access_pattern(user_id)
            
            # 更新热度图 (Requirements 5.1)
            self.heat_map.update_heat(user_id)

            # 检查是否已经在加载中
            if user_id in self.loading_status and not force_refresh:
                task = self.loading_status[user_id]
                if not task.done():
                    # 等待加载完成
                    profile_data = await task
                    return profile_data

            # 1. 检查内存缓存
            if not force_refresh:
                profile_data = await self._get_from_memory_cache(user_id)
                if profile_data is not None:
                    self.stats["memory_hits"] += 1
                    return profile_data

            # 2. 检查Redis缓存
            if not force_refresh and self.redis_client:
                profile_data = await self._get_from_redis_cache(user_id)
                if profile_data is not None:
                    self.stats["redis_hits"] += 1
                    # 提升到内存缓存
                    await self._store_in_cache(user_id, profile_data, CacheLevel.MEMORY)
                    return profile_data

            # 3. 从数据库加载
            profile_data = await self._load_profile_from_backend(user_id)
            if profile_data is not None:
                self.stats["database_hits"] += 1
                # 存储到所有缓存层级
                await self._store_in_cache(user_id, profile_data, CacheLevel.MEMORY)
                if self.redis_client:
                    await self._store_in_cache(user_id, profile_data, CacheLevel.REDIS)

                # 触发相关用户的预加载
                if self.config.preload_enabled:
                    await self._trigger_related_preloads(user_id)

                return profile_data

            # 未找到用户档案
            self.stats["misses"] += 1
            return None

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"获取用户档案失败 {user_id}: {e}")
            return None

        finally:
            # 更新性能指标
            response_time = (time.time() - start_time) * 1000
            self._update_performance_metrics(response_time)

    async def _get_from_memory_cache(self, user_id: str) -> Optional[Dict[str, Any]]:
        """从内存缓存获取"""
        if user_id not in self.memory_cache:
            return None

        entry = self.memory_cache[user_id]

        # 检查是否过期
        if entry.is_expired():
            # 移除过期条目
            await self._evict_from_memory(user_id, "expired")
            return None

        # 标记访问并移动到末尾（LRU）
        entry.mark_accessed()
        self.memory_cache.move_to_end(user_id)

        return entry.profile_data

    async def _get_from_redis_cache(self, user_id: str) -> Optional[Dict[str, Any]]:
        """从Redis缓存获取"""
        if not self.redis_client:
            return None

        try:
            key = f"{self.config.redis_key_prefix}{user_id}"
            cached_data = await self.redis_client.get(key)

            if cached_data:
                data = json.loads(cached_data)
                # 验证数据完整性
                if self._validate_profile_data(data):
                    return data.get("profile_data")
                else:
                    # 数据损坏，删除缓存
                    await self.redis_client.delete(key)

            return None

        except Exception as e:
            logger.error(f"Redis缓存读取失败 {user_id}: {e}")
            return None

    async def _load_profile_from_backend(self, user_id: str) -> Optional[Dict[str, Any]]:
        """从后端加载用户档案"""
        if not self.backend_client:
            return None

        try:
            # 创建加载任务
            if user_id in self.loading_status:
                task = self.loading_status[user_id]
                if not task.done():
                    return await task

            # 创建新的加载任务
            task = asyncio.create_task(self._do_load_profile(user_id))
            self.loading_status[user_id] = task

            profile_data = await task

            # 清理加载任务
            del self.loading_status[user_id]

            return profile_data

        except Exception as e:
            if user_id in self.loading_status:
                del self.loading_status[user_id]
            logger.error(f"后端加载失败 {user_id}: {e}")
            return None

    async def _do_load_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        执行实际的后端加载（带超时控制和熔断器保护）
        
        核心原则 (Requirements 2.6): 禁止返回降级数据，必须返回真实数据
        熔断器保护 (Requirements 4.4): 使用熔断器防止缓存雪崩
        """
        try:
            # ✅ 优化：使用5秒超时，匹配后端配置 user_profile_timeout_ms = 5000
            timeout_seconds = 5.0  # 5秒超时
            
            async def fetch_profile_with_timeout():
                """异步获取用户档案（带超时）"""
                # 确保backend_client的方法是异步的
                if asyncio.iscoroutinefunction(self.backend_client.get_user_profile):
                    return await asyncio.wait_for(
                        self.backend_client.get_user_profile(int(user_id)),
                        timeout=timeout_seconds
                    )
                else:
                    # 如果是同步方法，使用run_in_executor转换为异步
                    loop = asyncio.get_event_loop()
                    return await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            self.backend_client.get_user_profile,
                            int(user_id)
                        ),
                        timeout=timeout_seconds
                    )
            
            # 使用熔断器包装数据源调用 (Requirements 4.4)
            # ✅ 修复：直接传递异步函数，而不是lambda
            try:
                result = await self.circuit_breaker.call(fetch_profile_with_timeout)
            except CircuitOpenException as e:
                # 熔断器开启，记录并抛出异常
                self.stats["circuit_breaker_rejections"] += 1
                logger.warning(f"🔴 熔断器开启，拒绝用户档案请求: user_id={user_id}")
                raise UserProfileNotFoundError(user_id, f"熔断器开启，请稍后重试: user_id={user_id}")
            
            # 检查结果是否有效
            if result is None:
                # 用户不存在，抛出异常而非返回降级数据
                raise UserProfileNotFoundError(user_id, f"用户档案不存在: user_id={user_id}")
            
            # 检查是否是旧的降级档案（兼容性处理）
            if result.get('_fallback'):
                logger.warning(f"⚠️ 检测到旧的降级档案，拒绝使用: user_id={user_id}")
                raise UserProfileNotFoundError(user_id, f"用户档案数据无效: user_id={user_id}")
            
            return result

        except asyncio.TimeoutError:
            # 超时：抛出异常而非返回降级档案 (Requirements 2.6)
            logger.error(f"❌ 用户档案加载超时（{timeout_seconds}秒）: user_id={user_id}")
            raise UserProfileNotFoundError(user_id, f"用户档案加载超时: user_id={user_id}")
            
        except UserProfileNotFoundError:
            # 重新抛出自定义异常
            raise
            
        except CircuitOpenException:
            # 重新抛出熔断器异常
            raise
            
        except Exception as e:
            logger.error(f"❌ 执行后端加载失败 {user_id}: {e}")
            # 抛出异常而非返回降级档案 (Requirements 2.6)
            raise UserProfileNotFoundError(user_id, f"用户档案加载失败: user_id={user_id}, error={str(e)}")
    
    async def _store_in_cache(
        self,
        user_id: str,
        profile_data: Dict[str, Any],
        cache_level: CacheLevel
    ):
        """存储到指定缓存层级"""
        checksum = self._calculate_checksum(profile_data)
        size_bytes = len(json.dumps(profile_data, ensure_ascii=False).encode('utf-8'))

        entry = UserProfileEntry(
            user_id=user_id,
            profile_data=profile_data,
            status=UserProfileStatus.LOADED,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            last_updated=datetime.now(),
            size_bytes=size_bytes,
            checksum=checksum,
            ttl_seconds=self.config.redis_ttl_seconds if cache_level == CacheLevel.REDIS else 3600
        )

        if cache_level == CacheLevel.MEMORY:
            await self._store_in_memory(user_id, entry)
        elif cache_level == CacheLevel.REDIS and self.redis_client:
            await self._store_in_redis(user_id, entry)

    async def _store_in_memory(self, user_id: str, entry: UserProfileEntry):
        """存储到内存缓存"""
        # 检查内存限制
        while (len(self.memory_cache) >= self.config.max_memory_entries or
               self.current_memory_size_bytes >= self.config.max_memory_size_mb * 1024 * 1024):
            await self._evict_lru()

        # 如果用户已存在，更新大小统计
        if user_id in self.memory_cache:
            old_entry = self.memory_cache[user_id]
            self.current_memory_size_bytes -= old_entry.size_bytes

        # 添加新条目
        self.memory_cache[user_id] = entry
        self.memory_cache.move_to_end(user_id)
        self.current_memory_size_bytes += entry.size_bytes

    async def _store_in_redis(self, user_id: str, entry: UserProfileEntry):
        """存储到Redis缓存"""
        try:
            key = f"{self.config.redis_key_prefix}{user_id}"
            value = json.dumps(entry.to_dict(), ensure_ascii=False, default=str)

            await self.redis_client.setex(
                key,
                entry.ttl_seconds,
                value
            )

        except Exception as e:
            logger.error(f"Redis缓存存储失败 {user_id}: {e}")

    async def _evict_lru(self):
        """清理LRU条目"""
        if not self.memory_cache:
            return

        # 获取最旧的条目
        user_id, entry = self.memory_cache.popitem(last=False)
        self.current_memory_size_bytes -= entry.size_bytes
        self.stats["cache_evictions"] += 1

        logger.debug(f"LRU清理用户档案: {user_id}")

    async def _evict_from_memory(self, user_id: str, reason: str):
        """从内存中移除指定用户"""
        if user_id in self.memory_cache:
            entry = self.memory_cache.pop(user_id)
            self.current_memory_size_bytes -= entry.size_bytes
            logger.debug(f"内存移除用户档案 {user_id}: {reason}")

    def _record_access_pattern(self, user_id: str):
        """记录访问模式"""
        now = datetime.now()
        self.access_patterns[user_id].append(now)

        # 保持最近100次访问记录
        if len(self.access_patterns[user_id]) > 100:
            self.access_patterns[user_id] = self.access_patterns[user_id][-100:]

    async def _trigger_related_preloads(self, current_user_id: str):
        """触发相关用户的预加载"""
        if not self.config.preload_enabled:
            return

        try:
            # 基于访问模式分析相关用户
            predictions = self._predict_related_users(current_user_id)

            for prediction in predictions:
                if prediction.probability >= self.config.preload_threshold:
                    try:
                        # 非阻塞地添加到预加载队列
                        self.preload_queue.put_nowait(prediction)
                    except asyncio.QueueFull:
                        # 队列满，跳过这个预加载
                        break

        except Exception as e:
            logger.error(f"触发预加载失败 {current_user_id}: {e}")

    def _predict_related_users(self, current_user_id: str) -> List[PreloadPrediction]:
        """预测可能需要预加载的相关用户"""
        predictions = []

        # 简单的相关性分析：基于时间窗口内的访问模式
        current_user_access = self.access_patterns[current_user_id]
        if len(current_user_access) < 5:
            return predictions

        # 分析最近30分钟的访问时间
        recent_time = datetime.now() - timedelta(minutes=self.config.preload_window_minutes)
        recent_accesses = [
            access for access in current_user_access
            if access >= recent_time
        ]

        if len(recent_accesses) < 2:
            return predictions

        # 寻找在相似时间访问过的其他用户
        for other_user_id, other_accesses in self.access_patterns.items():
            if other_user_id == current_user_id:
                continue

            # 计算时间重叠度
            overlap_score = self._calculate_temporal_overlap(
                recent_accesses,
                [a for a in other_accesses if a >= recent_time]
            )

            if overlap_score > 0.3:  # 30%以上重叠
                predictions.append(PreloadPrediction(
                    user_id=other_user_id,
                    probability=overlap_score,
                    reason=f"时间模式重叠度: {overlap_score:.2f}",
                    estimated_time_s=1.0,
                    priority_score=overlap_score
                ))

        # 按概率排序
        predictions.sort(key=lambda p: p.probability, reverse=True)
        return predictions[:5]  # 最多返回5个预测

    def _calculate_temporal_overlap(
        self,
        times1: List[datetime],
        times2: List[datetime]
    ) -> float:
        """计算两个时间列表的重叠度"""
        if not times1 or not times2:
            return 0.0

        # 简单的重叠计算：在5分钟窗口内的访问
        window = timedelta(minutes=5)
        overlap_count = 0

        for t1 in times1:
            for t2 in times2:
                if abs((t1 - t2).total_seconds()) <= window.total_seconds():
                    overlap_count += 1
                    break

        return overlap_count / max(len(times1), len(times2))

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """计算数据校验和"""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()

    def _validate_profile_data(self, data: Dict[str, Any]) -> bool:
        """验证用户档案数据完整性"""
        if not isinstance(data, dict):
            return False

        if "profile_data" not in data:
            return False

        if "checksum" not in data:
            return True  # 如果没有校验和，跳过验证

        # 验证校验和
        calculated_checksum = self._calculate_checksum(data["profile_data"])
        return calculated_checksum == data["checksum"]

    def _update_performance_metrics(self, response_time_ms: float):
        """更新性能指标"""
        # 更新平均响应时间
        total_requests = self.stats["total_requests"]
        if total_requests == 1:
            self.performance_metrics["avg_response_time_ms"] = response_time_ms
        else:
            self.performance_metrics["avg_response_time_ms"] = (
                (self.performance_metrics["avg_response_time_ms"] * (total_requests - 1) + response_time_ms) /
                total_requests
            )

        # 更新缓存命中率
        total_hits = (
            self.stats["memory_hits"] +
            self.stats["redis_hits"]
        )
        self.performance_metrics["cache_hit_rate"] = total_hits / total_requests if total_requests > 0 else 0

    async def _auto_refresh_loop(self):
        """自动刷新循环"""
        while True:
            try:
                await asyncio.sleep(self.config.refresh_interval_minutes * 60)
                await self._auto_refresh_stale_entries()

            except Exception as e:
                logger.error(f"自动刷新循环错误: {e}")

    async def _auto_refresh_stale_entries(self):
        """自动刷新过期条目"""
        stale_users = []

        for user_id, entry in self.memory_cache.items():
            if entry.is_expired():
                stale_users.append(user_id)

        if stale_users:
            logger.info(f"开始自动刷新 {len(stale_users)} 个过期用户档案")
            # 并发刷新
            tasks = [
                self.get_user_profile(user_id, force_refresh=True)
                for user_id in stale_users[:10]  # 限制并发数量
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

            self.stats["auto_refreshes"] += len(stale_users)

    def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.stats["total_requests"]

        return {
            **self.stats,
            **self.performance_metrics,
            "memory_cache_entries": len(self.memory_cache),
            "memory_size_mb": self.current_memory_size_bytes / (1024 * 1024),
            "loading_tasks": len(self.loading_status),
            "preload_queue_size": self.preload_queue.qsize(),
            "access_patterns_tracked": len(self.access_patterns),
            "top_users_by_access": self._get_top_users_by_access(),
            "circuit_breaker_status": self.circuit_breaker.get_status(),  # 熔断器状态
            "heat_map_stats": self.heat_map.get_statistics()  # 热度图统计 (Requirements 5.1)
        }

    def _get_top_users_by_access(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取访问次数最多的用户"""
        user_stats = []

        for user_id, entry in self.memory_cache.items():
            user_stats.append({
                "user_id": user_id,
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed.isoformat(),
                "size_bytes": entry.size_bytes
            })

        user_stats.sort(key=lambda x: x["access_count"], reverse=True)
        return user_stats[:limit]

    async def invalidate_user(self, user_id: str):
        """使指定用户的缓存失效"""
        # 从内存中移除
        await self._evict_from_memory(user_id, "manual_invalidation")

        # 从Redis中移除
        if self.redis_client:
            try:
                key = f"{self.config.redis_key_prefix}{user_id}"
                await self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis缓存失效失败 {user_id}: {e}")

        logger.info(f"用户缓存已失效: {user_id}")

    async def shutdown(self):
        """关闭缓存系统"""
        # 停止预加载工作线程
        for worker in self.preload_workers:
            worker.cancel()

        # 等待工作线程结束
        if self.preload_workers:
            await asyncio.gather(*self.preload_workers, return_exceptions=True)

        # 清理内存缓存
        self.memory_cache.clear()
        self.current_memory_size_bytes = 0

        logger.info("智能用户档案缓存系统已关闭")


# 导出
__all__ = [
    "IntelligentUserCache",
    "UserProfileEntry",
    "PreloadPrediction",
    "CacheConfig",
    "CacheLevel",
    "UserProfileStatus",
    "UserProfileNotFoundError",  # 异常类导出
    # 熔断器相关（从circuit_breaker模块重新导出）
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenException",
    # 热度图相关（从heat_map模块重新导出）(Requirements 5.1)
    "HeatMap"
]