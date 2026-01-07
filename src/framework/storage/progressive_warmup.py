# -*- coding: utf-8 -*-
"""
Progressive Warmup System - 渐进式预热系统

基于Netflix/Amazon/Google等大厂的缓存策略，实现启动时预热 + 运行时懒加载 + 智能预热的混合模式。

核心功能：
1. 三阶段预热：critical → important → optional
2. 非阻塞启动：预热不阻塞服务启动
3. 配置化预热：支持配置预热用户ID和常用查询
4. 错误容忍：预热失败不影响主服务

版本: v1.0.0
日期: 2025-12-29
作者: 薛小川
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WarmupPhase(Enum):
    """预热阶段枚举"""
    CRITICAL = "critical"      # 关键数据（用户档案、会员权限）
    IMPORTANT = "important"    # 重要数据（常用查询）
    OPTIONAL = "optional"      # 可选数据（热门用户）


@dataclass
class WarmupConfig:
    """预热配置"""
    # 关键用户ID列表（第1阶段预热）- 默认为空，避免预热不存在的用户
    critical_user_ids: List[int] = field(default_factory=list)
    
    # 常用查询列表（第2阶段预热）
    common_queries: List[str] = field(default_factory=lambda: [
        "我想增肌", "怎么减肥", "深蹲怎么做",
        "胸肌训练", "背部训练", "腿部训练",
        "蛋白质摄入", "热量计算", "训练计划", "休息恢复"
    ])
    
    # 热门用户数量（第3阶段预热）
    hot_users_limit: int = 20
    
    # 预热超时时间（秒）
    phase_timeout_seconds: float = 30.0
    
    # 单个预热任务超时（秒）
    task_timeout_seconds: float = 5.0
    
    # 是否启用预热
    enabled: bool = True
    
    # 并发预热数量
    max_concurrent_warmups: int = 5


@dataclass
class WarmupResult:
    """预热结果"""
    phase: WarmupPhase
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    @property
    def total_count(self) -> int:
        return self.success_count + self.failure_count + self.skipped_count
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count


@dataclass
class WarmupStatistics:
    """预热统计信息"""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    phase_results: Dict[str, WarmupResult] = field(default_factory=dict)
    is_running: bool = False
    is_completed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_seconds": self.total_duration_seconds,
            "is_running": self.is_running,
            "is_completed": self.is_completed,
            "phase_results": {
                phase: {
                    "success_count": result.success_count,
                    "failure_count": result.failure_count,
                    "skipped_count": result.skipped_count,
                    "duration_seconds": result.duration_seconds,
                    "success_rate": result.success_rate,
                    "errors": result.errors[:5]  # 只返回前5个错误
                }
                for phase, result in self.phase_results.items()
            }
        }


class ProgressiveWarmup:
    """
    渐进式预热系统
    
    核心特性：
    1. 三阶段预热：critical → important → optional
    2. 非阻塞启动：预热不阻塞服务启动
    3. 错误容忍：预热失败不影响主服务
    4. 性能监控：详细的预热统计信息
    """
    
    def __init__(
        self,
        user_cache=None,
        membership_cache=None,
        few_shot_retriever=None,
        config: Optional[WarmupConfig] = None
    ):
        """
        初始化渐进式预热系统
        
        Args:
            user_cache: 用户档案缓存实例
            membership_cache: 会员权限缓存实例
            few_shot_retriever: Few-Shot检索器实例
            config: 预热配置
        """
        self.user_cache = user_cache
        self.membership_cache = membership_cache
        self.few_shot_retriever = few_shot_retriever
        self.config = config or WarmupConfig()
        
        # 预热统计
        self.statistics = WarmupStatistics()
        
        # 预热任务
        self._warmup_task: Optional[asyncio.Task] = None
        
        # 预热阶段定义
        self._warmup_phases = [
            (WarmupPhase.CRITICAL, self._warm_critical_data),
            (WarmupPhase.IMPORTANT, self._warm_important_data),
            (WarmupPhase.OPTIONAL, self._warm_optional_data)
        ]
        
        logger.info(
            f"ProgressiveWarmup initialized: "
            f"critical_users={len(self.config.critical_user_ids)}, "
            f"common_queries={len(self.config.common_queries)}, "
            f"enabled={self.config.enabled}"
        )
    
    async def progressive_warmup(self) -> WarmupStatistics:
        """
        执行渐进式预热（非阻塞）
        
        Returns:
            WarmupStatistics: 预热统计信息
        """
        if not self.config.enabled:
            logger.info("⏭️ 预热已禁用，跳过预热")
            return self.statistics
        
        if self.statistics.is_running:
            logger.warning("⚠️ 预热已在运行中，跳过重复启动")
            return self.statistics
        
        # 启动非阻塞预热任务
        self._warmup_task = asyncio.create_task(self._execute_warmup())
        
        logger.info("🚀 渐进式预热已启动（非阻塞）")
        return self.statistics
    
    async def _execute_warmup(self):
        """执行预热（内部方法）"""
        self.statistics.is_running = True
        self.statistics.started_at = datetime.now()
        total_start_time = time.time()
        
        try:
            for phase, warmup_func in self._warmup_phases:
                try:
                    result = await asyncio.wait_for(
                        warmup_func(),
                        timeout=self.config.phase_timeout_seconds
                    )
                    self.statistics.phase_results[phase.value] = result
                    
                    logger.info(
                        f"✅ 预热阶段完成: {phase.value}, "
                        f"成功={result.success_count}, "
                        f"失败={result.failure_count}, "
                        f"耗时={result.duration_seconds:.2f}s"
                    )
                    
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ 预热阶段超时: {phase.value}")
                    self.statistics.phase_results[phase.value] = WarmupResult(
                        phase=phase,
                        errors=[f"阶段超时（{self.config.phase_timeout_seconds}s）"]
                    )
                    
                except Exception as e:
                    logger.error(f"❌ 预热阶段失败: {phase.value}, 错误: {e}")
                    self.statistics.phase_results[phase.value] = WarmupResult(
                        phase=phase,
                        errors=[str(e)]
                    )
            
        except Exception as e:
            logger.error(f"❌ 预热执行失败: {e}")
            
        finally:
            self.statistics.is_running = False
            self.statistics.is_completed = True
            self.statistics.completed_at = datetime.now()
            self.statistics.total_duration_seconds = time.time() - total_start_time
            
            logger.info(
                f"🏁 渐进式预热完成: "
                f"总耗时={self.statistics.total_duration_seconds:.2f}s"
            )
    
    async def _warm_critical_data(self) -> WarmupResult:
        """
        预热关键数据（第1阶段）
        - 常用用户档案
        - 常用用户会员权限
        """
        result = WarmupResult(phase=WarmupPhase.CRITICAL)
        start_time = time.time()
        
        # 预热用户档案和会员权限
        tasks = []
        for user_id in self.config.critical_user_ids:
            if self.user_cache:
                tasks.append(self._warmup_user_profile(str(user_id)))
            if self.membership_cache:
                tasks.append(self._warmup_membership(str(user_id)))
        
        if tasks:
            # 使用信号量限制并发
            semaphore = asyncio.Semaphore(self.config.max_concurrent_warmups)
            
            async def limited_task(task):
                async with semaphore:
                    return await task
            
            results = await asyncio.gather(
                *[limited_task(task) for task in tasks],
                return_exceptions=True
            )
            
            for r in results:
                if isinstance(r, Exception):
                    result.failure_count += 1
                    result.errors.append(str(r))
                elif r is True:
                    result.success_count += 1
                else:
                    result.skipped_count += 1
        
        result.duration_seconds = time.time() - start_time
        return result
    
    async def _warm_important_data(self) -> WarmupResult:
        """
        预热重要数据（第2阶段）
        - 常用查询的Few-Shot示例
        """
        result = WarmupResult(phase=WarmupPhase.IMPORTANT)
        start_time = time.time()
        
        if not self.few_shot_retriever:
            logger.debug("⏭️ Few-Shot检索器未配置，跳过重要数据预热")
            result.skipped_count = len(self.config.common_queries)
            result.duration_seconds = time.time() - start_time
            return result
        
        # 预热常用查询
        tasks = []
        for query in self.config.common_queries:
            tasks.append(self._warmup_query(query))
        
        if tasks:
            semaphore = asyncio.Semaphore(self.config.max_concurrent_warmups)
            
            async def limited_task(task):
                async with semaphore:
                    return await task
            
            results = await asyncio.gather(
                *[limited_task(task) for task in tasks],
                return_exceptions=True
            )
            
            for r in results:
                if isinstance(r, Exception):
                    result.failure_count += 1
                    result.errors.append(str(r))
                elif r is True:
                    result.success_count += 1
                else:
                    result.skipped_count += 1
        
        result.duration_seconds = time.time() - start_time
        return result
    
    async def _warm_optional_data(self) -> WarmupResult:
        """
        预热可选数据（第3阶段）
        - 热门用户数据
        """
        result = WarmupResult(phase=WarmupPhase.OPTIONAL)
        start_time = time.time()
        
        # 获取热门用户（从分析数据或缓存统计）
        hot_users = await self._get_hot_users()
        
        if not hot_users:
            logger.debug("⏭️ 无热门用户数据，跳过可选数据预热")
            result.duration_seconds = time.time() - start_time
            return result
        
        # 预热热门用户
        tasks = []
        for user_id in hot_users[:self.config.hot_users_limit]:
            if self.user_cache:
                tasks.append(self._warmup_user_profile(str(user_id)))
        
        if tasks:
            semaphore = asyncio.Semaphore(self.config.max_concurrent_warmups)
            
            async def limited_task(task):
                async with semaphore:
                    return await task
            
            results = await asyncio.gather(
                *[limited_task(task) for task in tasks],
                return_exceptions=True
            )
            
            for r in results:
                if isinstance(r, Exception):
                    result.failure_count += 1
                    result.errors.append(str(r))
                elif r is True:
                    result.success_count += 1
                else:
                    result.skipped_count += 1
        
        result.duration_seconds = time.time() - start_time
        return result
    
    async def _warmup_user_profile(self, user_id: str) -> bool:
        """预热单个用户档案"""
        try:
            await asyncio.wait_for(
                self.user_cache.get_user_profile(user_id),
                timeout=self.config.task_timeout_seconds
            )
            logger.debug(f"✅ 用户档案预热成功: {user_id}")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ 用户档案预热超时: {user_id}")
            return False
        except Exception as e:
            logger.warning(f"⚠️ 用户档案预热失败: {user_id}, 错误: {e}")
            raise
    
    async def _warmup_membership(self, user_id: str) -> bool:
        """预热单个用户会员权限"""
        try:
            await asyncio.wait_for(
                self.membership_cache.get_user_membership(user_id),
                timeout=self.config.task_timeout_seconds
            )
            logger.debug(f"✅ 会员权限预热成功: {user_id}")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ 会员权限预热超时: {user_id}")
            return False
        except Exception as e:
            logger.warning(f"⚠️ 会员权限预热失败: {user_id}, 错误: {e}")
            raise
    
    async def _warmup_query(self, query: str) -> bool:
        """预热单个查询"""
        try:
            await asyncio.wait_for(
                self.few_shot_retriever.retrieve(query),
                timeout=self.config.task_timeout_seconds
            )
            logger.debug(f"✅ 查询预热成功: {query[:20]}...")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ 查询预热超时: {query[:20]}...")
            return False
        except Exception as e:
            logger.warning(f"⚠️ 查询预热失败: {query[:20]}..., 错误: {e}")
            raise
    
    async def _get_hot_users(self) -> List[int]:
        """
        获取热门用户列表
        
        可以从以下来源获取：
        1. 用户缓存的访问统计
        2. 数据库的访问日志
        3. Redis的热度数据
        """
        hot_users = []
        
        # 从用户缓存获取热门用户
        if self.user_cache and hasattr(self.user_cache, 'access_patterns'):
            # 按访问次数排序
            sorted_users = sorted(
                self.user_cache.access_patterns.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            hot_users = [int(user_id) for user_id, _ in sorted_users[:self.config.hot_users_limit]]
        
        return hot_users
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取预热统计信息"""
        return self.statistics.to_dict()
    
    async def wait_for_completion(self, timeout: float = 60.0) -> bool:
        """
        等待预热完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否在超时前完成
        """
        if not self._warmup_task:
            return True
        
        try:
            await asyncio.wait_for(self._warmup_task, timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ 等待预热完成超时（{timeout}s）")
            return False
    
    async def cancel(self):
        """取消预热"""
        if self._warmup_task and not self._warmup_task.done():
            self._warmup_task.cancel()
            try:
                await self._warmup_task
            except asyncio.CancelledError:
                pass
            logger.info("🛑 预热已取消")


# 全局预热实例
_global_warmup: Optional[ProgressiveWarmup] = None


def get_progressive_warmup() -> Optional[ProgressiveWarmup]:
    """获取全局预热实例"""
    return _global_warmup


def set_progressive_warmup(warmup: ProgressiveWarmup):
    """设置全局预热实例"""
    global _global_warmup
    _global_warmup = warmup


async def create_and_start_warmup(
    user_cache=None,
    membership_cache=None,
    few_shot_retriever=None,
    config: Optional[WarmupConfig] = None
) -> ProgressiveWarmup:
    """
    创建并启动预热系统
    
    Args:
        user_cache: 用户档案缓存实例
        membership_cache: 会员权限缓存实例
        few_shot_retriever: Few-Shot检索器实例
        config: 预热配置
        
    Returns:
        ProgressiveWarmup: 预热实例
    """
    warmup = ProgressiveWarmup(
        user_cache=user_cache,
        membership_cache=membership_cache,
        few_shot_retriever=few_shot_retriever,
        config=config
    )
    
    # 设置全局实例
    set_progressive_warmup(warmup)
    
    # 启动非阻塞预热
    await warmup.progressive_warmup()
    
    return warmup


# 导出
__all__ = [
    "ProgressiveWarmup",
    "WarmupConfig",
    "WarmupPhase",
    "WarmupResult",
    "WarmupStatistics",
    "get_progressive_warmup",
    "set_progressive_warmup",
    "create_and_start_warmup"
]
