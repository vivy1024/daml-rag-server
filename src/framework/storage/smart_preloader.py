# -*- coding: utf-8 -*-
"""
Smart Preloader - 智能预热器

实现步骤1预热步骤3的智能预热策略，在用户档案加载完成后，
异步预热会员权限数据，确保步骤3执行时数据已在缓存中。

核心功能：
1. 步骤1预热步骤3：用户档案加载后异步预热会员数据
2. 非阻塞预热：不影响主工作流执行
3. 预热效果追踪：统计预热命中率
4. 自适应预热：基于用户热度进行预热

版本: v1.0.0
日期: 2025-12-29
作者: 薛小川

Requirements:
- 3.1: WHEN step 1 completes, THE DAML_RAG_System SHALL async preload membership data for step 3
- 3.2: THE async preload SHALL NOT block the main workflow execution
- 3.3: WHEN step 3 executes, THE Membership_Cache SHALL find data already in cache
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PreloadStatus(Enum):
    """预热状态枚举"""
    PENDING = "pending"      # 等待预热
    IN_PROGRESS = "in_progress"  # 预热中
    SUCCESS = "success"      # 预热成功
    FAILED = "failed"        # 预热失败
    SKIPPED = "skipped"      # 跳过预热


@dataclass
class PreloadTask:
    """预热任务"""
    user_id: str
    task_type: str  # "membership", "user_profile", etc.
    status: PreloadStatus = PreloadStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    
    def mark_completed(self, success: bool, error: Optional[str] = None):
        """标记任务完成"""
        self.completed_at = datetime.now()
        self.duration_ms = (self.completed_at - self.created_at).total_seconds() * 1000
        self.status = PreloadStatus.SUCCESS if success else PreloadStatus.FAILED
        self.error = error


@dataclass
class SmartPreloaderConfig:
    """智能预热器配置"""
    # 是否启用智能预热
    enabled: bool = True
    
    # 预热超时时间（秒）
    preload_timeout_seconds: float = 5.0
    
    # 最大并发预热数量
    max_concurrent_preloads: int = 10
    
    # 是否启用自适应预热
    adaptive_preload_enabled: bool = True
    
    # 热度阈值（前20%用户）
    hot_user_threshold: float = 0.8
    
    # 高频查询阈值
    hot_query_threshold: int = 100
    
    # 自适应预热间隔（秒）
    adaptive_preload_interval_seconds: float = 300.0  # 5分钟


@dataclass
class SmartPreloaderStatistics:
    """智能预热器统计信息"""
    total_preloads: int = 0
    successful_preloads: int = 0
    failed_preloads: int = 0
    skipped_preloads: int = 0
    cache_hits_after_preload: int = 0  # 预热后缓存命中次数
    avg_preload_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_preloads": self.total_preloads,
            "successful_preloads": self.successful_preloads,
            "failed_preloads": self.failed_preloads,
            "skipped_preloads": self.skipped_preloads,
            "cache_hits_after_preload": self.cache_hits_after_preload,
            "avg_preload_time_ms": self.avg_preload_time_ms,
            "preload_success_rate": (
                self.successful_preloads / self.total_preloads 
                if self.total_preloads > 0 else 0.0
            ),
            "preload_effectiveness": (
                self.cache_hits_after_preload / self.successful_preloads
                if self.successful_preloads > 0 else 0.0
            )
        }


class SmartPreloader:
    """
    智能预热器
    
    核心特性：
    1. 步骤1预热步骤3：用户档案加载后异步预热会员数据 (Requirements 3.1)
    2. 非阻塞预热：不影响主工作流执行 (Requirements 3.2)
    3. 预热效果追踪：统计预热命中率
    4. 自适应预热：基于用户热度进行预热
    """
    
    def __init__(
        self,
        membership_cache=None,
        user_cache=None,
        config: Optional[SmartPreloaderConfig] = None
    ):
        """
        初始化智能预热器
        
        Args:
            membership_cache: 会员权限缓存实例
            user_cache: 用户档案缓存实例
            config: 预热器配置
        """
        self.membership_cache = membership_cache
        self.user_cache = user_cache
        self.config = config or SmartPreloaderConfig()
        
        # 统计信息
        self.statistics = SmartPreloaderStatistics()
        
        # 正在进行的预热任务
        self._pending_tasks: Dict[str, PreloadTask] = {}
        
        # 已预热的用户ID集合（用于追踪预热效果）
        self._preloaded_users: Set[str] = set()
        
        # 并发控制信号量
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_preloads)
        
        # 自适应预热任务
        self._adaptive_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"SmartPreloader initialized: "
            f"enabled={self.config.enabled}, "
            f"timeout={self.config.preload_timeout_seconds}s, "
            f"max_concurrent={self.config.max_concurrent_preloads}"
        )
    
    async def preload_for_step3(self, user_id: str) -> bool:
        """
        步骤1完成后，异步预热步骤3需要的会员数据 (Requirements 3.1, 3.2)
        
        此方法在node_preload_user_profile完成后调用，
        异步预热会员权限数据，确保步骤3执行时数据已在缓存中。
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功启动预热任务（不等待完成）
        """
        if not self.config.enabled:
            logger.debug(f"⏭️ 智能预热已禁用，跳过: user_id={user_id}")
            return False
        
        if not self.membership_cache:
            logger.warning(f"⚠️ 会员缓存未配置，跳过预热: user_id={user_id}")
            return False
        
        if not user_id:
            logger.debug(f"⏭️ 无用户ID，跳过预热")
            return False
        
        # 检查是否已在预热中
        task_key = f"membership:{user_id}"
        if task_key in self._pending_tasks:
            task = self._pending_tasks[task_key]
            if task.status == PreloadStatus.IN_PROGRESS:
                logger.debug(f"⏭️ 会员数据预热已在进行中: user_id={user_id}")
                return True
        
        # 创建预热任务
        task = PreloadTask(
            user_id=user_id,
            task_type="membership",
            status=PreloadStatus.PENDING
        )
        self._pending_tasks[task_key] = task
        
        # 启动非阻塞预热任务 (Requirements 3.2)
        asyncio.create_task(self._execute_membership_preload(user_id, task))
        
        logger.debug(f"🚀 启动会员数据预热: user_id={user_id}")
        return True
    
    async def _execute_membership_preload(self, user_id: str, task: PreloadTask):
        """
        执行会员数据预热（内部方法）
        
        Args:
            user_id: 用户ID
            task: 预热任务
        """
        task.status = PreloadStatus.IN_PROGRESS
        self.statistics.total_preloads += 1
        
        try:
            async with self._semaphore:
                # 带超时的预热
                await asyncio.wait_for(
                    self.membership_cache.get_user_membership(user_id),
                    timeout=self.config.preload_timeout_seconds
                )
            
            # 预热成功
            task.mark_completed(success=True)
            self.statistics.successful_preloads += 1
            self._preloaded_users.add(user_id)
            
            # 更新平均预热时间
            self._update_avg_preload_time(task.duration_ms)
            
            logger.debug(
                f"✅ 会员数据预热成功: user_id={user_id}, "
                f"耗时={task.duration_ms:.2f}ms"
            )
            
        except asyncio.TimeoutError:
            task.mark_completed(success=False, error="预热超时")
            self.statistics.failed_preloads += 1
            logger.warning(
                f"⚠️ 会员数据预热超时: user_id={user_id}, "
                f"timeout={self.config.preload_timeout_seconds}s"
            )
            
        except Exception as e:
            task.mark_completed(success=False, error=str(e))
            self.statistics.failed_preloads += 1
            logger.warning(f"⚠️ 会员数据预热失败: user_id={user_id}, error={e}")
        
        finally:
            # 清理已完成的任务
            task_key = f"membership:{user_id}"
            if task_key in self._pending_tasks:
                del self._pending_tasks[task_key]
    
    def record_cache_hit(self, user_id: str):
        """
        记录缓存命中（用于追踪预热效果）
        
        当步骤3从缓存获取会员数据时调用此方法，
        用于统计预热的有效性。
        
        Args:
            user_id: 用户ID
        """
        if user_id in self._preloaded_users:
            self.statistics.cache_hits_after_preload += 1
            logger.debug(f"📊 预热缓存命中: user_id={user_id}")
    
    async def adaptive_preload(self):
        """
        自适应预热 - 基于用户热度进行预热 (Requirements 5.2, 5.3)
        
        预热高热度用户和高频查询的数据
        """
        if not self.config.adaptive_preload_enabled:
            logger.debug("⏭️ 自适应预热已禁用")
            return
        
        logger.info("🔄 开始自适应预热...")
        
        try:
            # 1. 预热高热度用户
            hot_users = await self._get_hot_users()
            for user_id in hot_users:
                await self.preload_for_step3(user_id)
            
            logger.info(f"✅ 自适应预热完成: 预热了 {len(hot_users)} 个热门用户")
            
        except Exception as e:
            logger.error(f"❌ 自适应预热失败: {e}")
    
    async def _get_hot_users(self) -> List[str]:
        """
        获取热门用户列表
        
        Returns:
            List[str]: 热门用户ID列表
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
            
            # 取前20%
            top_count = max(1, int(len(sorted_users) * (1 - self.config.hot_user_threshold)))
            hot_users = [user_id for user_id, _ in sorted_users[:top_count]]
        
        return hot_users
    
    async def start_adaptive_preload_loop(self):
        """
        启动自适应预热循环
        
        每隔一定时间执行一次自适应预热
        """
        if not self.config.adaptive_preload_enabled:
            logger.info("⏭️ 自适应预热已禁用，不启动循环")
            return
        
        async def _loop():
            while True:
                try:
                    await asyncio.sleep(self.config.adaptive_preload_interval_seconds)
                    await self.adaptive_preload()
                except asyncio.CancelledError:
                    logger.info("🛑 自适应预热循环已取消")
                    break
                except Exception as e:
                    logger.error(f"❌ 自适应预热循环异常: {e}")
        
        self._adaptive_task = asyncio.create_task(_loop())
        logger.info(
            f"🚀 自适应预热循环已启动: "
            f"间隔={self.config.adaptive_preload_interval_seconds}s"
        )
    
    async def stop_adaptive_preload_loop(self):
        """停止自适应预热循环"""
        if self._adaptive_task and not self._adaptive_task.done():
            self._adaptive_task.cancel()
            try:
                await self._adaptive_task
            except asyncio.CancelledError:
                pass
            logger.info("🛑 自适应预热循环已停止")
    
    def _update_avg_preload_time(self, duration_ms: float):
        """更新平均预热时间"""
        total = self.statistics.successful_preloads
        if total == 1:
            self.statistics.avg_preload_time_ms = duration_ms
        else:
            self.statistics.avg_preload_time_ms = (
                (self.statistics.avg_preload_time_ms * (total - 1) + duration_ms) / total
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取预热统计信息"""
        return {
            **self.statistics.to_dict(),
            "pending_tasks": len(self._pending_tasks),
            "preloaded_users_count": len(self._preloaded_users),
            "config": {
                "enabled": self.config.enabled,
                "timeout_seconds": self.config.preload_timeout_seconds,
                "max_concurrent": self.config.max_concurrent_preloads,
                "adaptive_enabled": self.config.adaptive_preload_enabled
            }
        }
    
    def is_user_preloaded(self, user_id: str) -> bool:
        """
        检查用户是否已预热
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否已预热
        """
        return user_id in self._preloaded_users
    
    async def shutdown(self):
        """关闭智能预热器"""
        # 停止自适应预热循环
        await self.stop_adaptive_preload_loop()
        
        # 清理状态
        self._pending_tasks.clear()
        self._preloaded_users.clear()
        
        logger.info("✅ 智能预热器已关闭")


# 全局智能预热器实例
_global_smart_preloader: Optional[SmartPreloader] = None


def get_smart_preloader() -> Optional[SmartPreloader]:
    """获取全局智能预热器实例"""
    return _global_smart_preloader


def set_smart_preloader(preloader: SmartPreloader):
    """设置全局智能预热器实例"""
    global _global_smart_preloader
    _global_smart_preloader = preloader


async def create_smart_preloader(
    membership_cache=None,
    user_cache=None,
    config: Optional[SmartPreloaderConfig] = None,
    start_adaptive_loop: bool = False
) -> SmartPreloader:
    """
    创建智能预热器
    
    Args:
        membership_cache: 会员权限缓存实例
        user_cache: 用户档案缓存实例
        config: 预热器配置
        start_adaptive_loop: 是否启动自适应预热循环
        
    Returns:
        SmartPreloader: 智能预热器实例
    """
    preloader = SmartPreloader(
        membership_cache=membership_cache,
        user_cache=user_cache,
        config=config
    )
    
    # 设置全局实例
    set_smart_preloader(preloader)
    
    # 启动自适应预热循环（如果需要）
    if start_adaptive_loop:
        await preloader.start_adaptive_preload_loop()
    
    return preloader


# 导出
__all__ = [
    "SmartPreloader",
    "SmartPreloaderConfig",
    "SmartPreloaderStatistics",
    "PreloadTask",
    "PreloadStatus",
    "get_smart_preloader",
    "set_smart_preloader",
    "create_smart_preloader"
]
