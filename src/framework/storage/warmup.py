# -*- coding: utf-8 -*-
"""
Warmup Manager - 预加载管理器

合并progressive_warmup和smart_preloader的功能，提供统一的预加载管理

核心功能：
1. 系统启动时预加载常用数据
2. 后台异步预加载
3. 可配置的预加载策略
4. 预加载统计和监控

版本: v1.0.0
日期: 2026-01-10
作者: 薛小川
"""

import logging
import asyncio
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WarmupConfig:
    """预加载配置"""
    enabled: bool = True  # 是否启用
    batch_size: int = 100  # 批量大小
    max_concurrent: int = 5  # 最大并发数
    timeout: int = 30  # 超时时间（秒）
    
    # 预加载用户ID列表（可选）
    user_ids: List[int] = field(default_factory=list)


@dataclass
class WarmupStatistics:
    """预加载统计信息"""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    
    # 用户档案预加载统计
    profiles_total: int = 0
    profiles_success: int = 0
    profiles_failed: int = 0
    
    # 会员信息预加载统计
    memberships_total: int = 0
    memberships_success: int = 0
    memberships_failed: int = 0
    
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
            "profiles": {
                "total": self.profiles_total,
                "success": self.profiles_success,
                "failed": self.profiles_failed,
                "success_rate": self.profiles_success / self.profiles_total if self.profiles_total > 0 else 0.0
            },
            "memberships": {
                "total": self.memberships_total,
                "success": self.memberships_success,
                "failed": self.memberships_failed,
                "success_rate": self.memberships_success / self.memberships_total if self.memberships_total > 0 else 0.0
            }
        }


class WarmupManager:
    """
    预加载管理器
    
    合并progressive_warmup和smart_preloader的功能
    """
    
    def __init__(
        self,
        config: Optional[WarmupConfig] = None,
        user_profile_cache=None,
        membership_cache=None
    ):
        """
        初始化
        
        Args:
            config: 预加载配置
            user_profile_cache: 用户档案缓存实例
            membership_cache: 会员缓存实例
        """
        self.config = config or WarmupConfig()
        self.user_profile_cache = user_profile_cache
        self.membership_cache = membership_cache
        self.statistics = WarmupStatistics()
        self._warmup_task = None
        
        logger.info(f"WarmupManager initialized with config: enabled={self.config.enabled}")
    
    async def start(self):
        """
        启动预加载
        
        行为：
        1. 检查配置是否启用
        2. 在后台线程预加载数据
        3. 记录预加载进度
        """
        try:
            # 检查是否启用
            if not self.config.enabled:
                logger.info("Warmup is disabled, skipping")
                return
            
            # 检查是否已经在运行
            if self.statistics.is_running:
                logger.warning("Warmup is already running")
                return
            
            # 标记开始
            self.statistics.is_running = True
            self.statistics.started_at = datetime.now()
            
            logger.info("Starting warmup in background")
            
            # 在后台启动预加载任务
            self._warmup_task = asyncio.create_task(self._run_warmup())
            
        except Exception as e:
            logger.error(f"Error starting warmup: {e}")
            self.statistics.is_running = False
    
    async def preload_user_profiles(self, user_ids: List[int]):
        """
        预加载用户档案
        
        Args:
            user_ids: 用户ID列表
        """
        try:
            if not user_ids:
                logger.debug("No user IDs to preload")
                return
            
            if self.user_profile_cache is None:
                logger.warning("User profile cache is None, skipping preload")
                return
            
            logger.info(f"Preloading {len(user_ids)} user profiles")
            
            # 更新统计
            self.statistics.profiles_total = len(user_ids)
            
            # 分批预加载
            for i in range(0, len(user_ids), self.config.batch_size):
                batch = user_ids[i:i + self.config.batch_size]
                
                # 并发预加载
                tasks = [self._preload_single_profile(user_id) for user_id in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 统计结果
                for result in results:
                    if isinstance(result, Exception):
                        self.statistics.profiles_failed += 1
                    elif result:
                        self.statistics.profiles_success += 1
                    else:
                        self.statistics.profiles_failed += 1
            
            logger.info(
                f"User profiles preload completed: "
                f"{self.statistics.profiles_success}/{self.statistics.profiles_total} succeeded"
            )
            
        except Exception as e:
            logger.error(f"Error preloading user profiles: {e}")
    
    async def preload_memberships(self, user_ids: List[int]):
        """
        预加载会员信息
        
        Args:
            user_ids: 用户ID列表
        """
        try:
            if not user_ids:
                logger.debug("No user IDs to preload")
                return
            
            if self.membership_cache is None:
                logger.warning("Membership cache is None, skipping preload")
                return
            
            logger.info(f"Preloading {len(user_ids)} memberships")
            
            # 更新统计
            self.statistics.memberships_total = len(user_ids)
            
            # 分批预加载
            for i in range(0, len(user_ids), self.config.batch_size):
                batch = user_ids[i:i + self.config.batch_size]
                
                # 并发预加载
                tasks = [self._preload_single_membership(user_id) for user_id in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 统计结果
                for result in results:
                    if isinstance(result, Exception):
                        self.statistics.memberships_failed += 1
                    elif result:
                        self.statistics.memberships_success += 1
                    else:
                        self.statistics.memberships_failed += 1
            
            logger.info(
                f"Memberships preload completed: "
                f"{self.statistics.memberships_success}/{self.statistics.memberships_total} succeeded"
            )
            
        except Exception as e:
            logger.error(f"Error preloading memberships: {e}")
    
    def get_statistics(self) -> WarmupStatistics:
        """获取预加载统计信息"""
        return self.statistics
    
    async def wait_for_completion(self, timeout: Optional[float] = None):
        """
        等待预加载完成
        
        Args:
            timeout: 超时时间（秒），None表示无限等待
        """
        if self._warmup_task is None:
            return
        
        try:
            if timeout:
                await asyncio.wait_for(self._warmup_task, timeout=timeout)
            else:
                await self._warmup_task
        except asyncio.TimeoutError:
            logger.warning(f"Warmup did not complete within {timeout}s")
        except Exception as e:
            logger.error(f"Error waiting for warmup completion: {e}")
    
    # ==================== 私有方法 ====================
    
    async def _run_warmup(self):
        """运行预加载任务"""
        try:
            start_time = time.time()
            
            # 获取要预加载的用户ID列表
            user_ids = self.config.user_ids
            
            if not user_ids:
                logger.info("No user IDs configured for warmup")
                return
            
            # 预加载用户档案
            await self.preload_user_profiles(user_ids)
            
            # 预加载会员信息
            await self.preload_memberships(user_ids)
            
            # 标记完成
            self.statistics.completed_at = datetime.now()
            self.statistics.total_duration_seconds = time.time() - start_time
            self.statistics.is_running = False
            self.statistics.is_completed = True
            
            logger.info(
                f"Warmup completed in {self.statistics.total_duration_seconds:.2f}s: "
                f"profiles={self.statistics.profiles_success}/{self.statistics.profiles_total}, "
                f"memberships={self.statistics.memberships_success}/{self.statistics.memberships_total}"
            )
            
        except Exception as e:
            logger.error(f"Error running warmup: {e}")
            self.statistics.is_running = False
    
    async def _preload_single_profile(self, user_id: int) -> bool:
        """
        预加载单个用户档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        try:
            # 设置超时
            profile = await asyncio.wait_for(
                self.user_profile_cache.get_profile(user_id),
                timeout=self.config.timeout
            )
            
            if profile is not None:
                logger.debug(f"Preloaded user profile for user_id={user_id}")
                return True
            else:
                logger.debug(f"User profile not found for user_id={user_id}")
                return False
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout preloading user profile for user_id={user_id}")
            return False
        except Exception as e:
            logger.error(f"Error preloading user profile for user_id={user_id}: {e}")
            return False
    
    async def _preload_single_membership(self, user_id: int) -> bool:
        """
        预加载单个会员信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        try:
            # 设置超时
            membership = await asyncio.wait_for(
                self.membership_cache.get_membership(user_id),
                timeout=self.config.timeout
            )
            
            if membership is not None:
                logger.debug(f"Preloaded membership for user_id={user_id}")
                return True
            else:
                logger.debug(f"Membership not found for user_id={user_id}")
                return False
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout preloading membership for user_id={user_id}")
            return False
        except Exception as e:
            logger.error(f"Error preloading membership for user_id={user_id}: {e}")
            return False


# ==================== 全局实例 ====================

# 全局预加载管理器实例（延迟初始化）
_warmup_manager: Optional[WarmupManager] = None


def get_warmup_manager() -> Optional[WarmupManager]:
    """获取全局预加载管理器实例"""
    return _warmup_manager


def set_warmup_manager(manager: WarmupManager):
    """设置全局预加载管理器实例"""
    global _warmup_manager
    _warmup_manager = manager
