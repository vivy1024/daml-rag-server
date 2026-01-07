# -*- coding: utf-8 -*-
"""
Heat Map - 用户热度图系统

追踪用户访问频率和时间，用于自适应预热决策

核心功能：
1. 用户热度追踪：基于访问频率和时间衰减
2. 查询频率追踪：记录常用查询
3. 热门用户识别：获取top 20%热门用户
4. 热门查询识别：获取频率>100的查询
5. 自适应预热支持：为预热系统提供数据

版本: v1.0.0
日期: 2025-12-29
作者: 薛小川

Requirements:
- 5.1: THE Heat_Map SHALL track user access frequency and recency
- 5.2: THE DAML_RAG_System SHALL preload data for hot users (top 20% by heat score)
- 5.3: THE DAML_RAG_System SHALL preload data for hot queries (frequency > 100)
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import json

logger = logging.getLogger(__name__)


@dataclass
class HeatEntry:
    """热度条目"""
    heat_score: float = 0.0
    access_count: int = 0
    last_access_time: datetime = field(default_factory=datetime.now)
    first_access_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "heat_score": self.heat_score,
            "access_count": self.access_count,
            "last_access_time": self.last_access_time.isoformat(),
            "first_access_time": self.first_access_time.isoformat()
        }


@dataclass
class QueryEntry:
    """查询条目"""
    query: str
    frequency: int = 0
    last_access_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "frequency": self.frequency,
            "last_access_time": self.last_access_time.isoformat()
        }


@dataclass
class HeatMapConfig:
    """热度图配置"""
    # 热度衰减配置
    decay_factor: float = 0.95  # 热度衰减因子
    decay_interval_seconds: int = 300  # 衰减间隔（5分钟）
    
    # 热门用户配置
    hot_user_threshold: float = 0.8  # 热门用户阈值（top 20%）
    min_heat_score: float = 1.0  # 最小热度分数
    
    # 热门查询配置
    hot_query_threshold: int = 100  # 热门查询频率阈值
    
    # 清理配置
    max_users: int = 10000  # 最大追踪用户数
    max_queries: int = 5000  # 最大追踪查询数
    cleanup_interval_seconds: int = 3600  # 清理间隔（1小时）
    stale_threshold_hours: int = 24  # 过期阈值（24小时）


class HeatMap:
    """
    用户热度图 - 追踪访问频率和时间
    
    核心特性：
    1. 热度追踪：基于访问频率和时间衰减计算热度分数
    2. 查询频率：追踪查询使用频率
    3. 热门识别：识别热门用户和查询
    4. 自动衰减：定期衰减热度分数
    5. 自动清理：清理过期数据
    
    Requirements:
    - 5.1: track user access frequency and recency
    - 5.2: preload data for hot users (top 20%)
    - 5.3: preload data for hot queries (frequency > 100)
    """
    
    def __init__(self, config: Optional[HeatMapConfig] = None):
        """
        初始化热度图
        
        Args:
            config: 热度图配置
        """
        self.config = config or HeatMapConfig()
        
        # 用户热度数据 {user_id: HeatEntry}
        self.user_heat: Dict[str, HeatEntry] = {}
        
        # 查询频率数据 {query_hash: QueryEntry}
        self.query_frequency: Dict[str, QueryEntry] = {}
        
        # 线程安全锁
        self._user_lock = threading.RLock()
        self._query_lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            "total_user_updates": 0,
            "total_query_updates": 0,
            "decay_cycles": 0,
            "cleanup_cycles": 0,
            "users_cleaned": 0,
            "queries_cleaned": 0
        }
        
        # 后台任务
        self._decay_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            f"HeatMap initialized: "
            f"decay_factor={self.config.decay_factor}, "
            f"hot_user_threshold={self.config.hot_user_threshold}, "
            f"hot_query_threshold={self.config.hot_query_threshold}"
        )
    
    async def start(self):
        """启动后台任务"""
        if self._running:
            return
        
        self._running = True
        
        # 启动衰减任务
        self._decay_task = asyncio.create_task(self._decay_loop())
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("HeatMap background tasks started")
    
    async def stop(self):
        """停止后台任务"""
        self._running = False
        
        if self._decay_task:
            self._decay_task.cancel()
            try:
                await self._decay_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("HeatMap background tasks stopped")
    
    def update_heat(self, user_id: str, increment: float = 1.0):
        """
        更新用户热度 (Requirements 5.1)
        
        热度计算公式：
        new_heat = old_heat * decay_factor + increment
        
        Args:
            user_id: 用户ID
            increment: 热度增量（默认1.0）
        """
        with self._user_lock:
            now = datetime.now()
            
            if user_id in self.user_heat:
                entry = self.user_heat[user_id]
                # 更新热度分数
                entry.heat_score = entry.heat_score * self.config.decay_factor + increment
                entry.access_count += 1
                entry.last_access_time = now
            else:
                # 创建新条目
                self.user_heat[user_id] = HeatEntry(
                    heat_score=increment,
                    access_count=1,
                    last_access_time=now,
                    first_access_time=now
                )
            
            self.stats["total_user_updates"] += 1
            
            # 检查是否需要清理
            if len(self.user_heat) > self.config.max_users:
                self._cleanup_cold_users()
    
    def update_query_frequency(self, query: str):
        """
        更新查询频率 (Requirements 5.3)
        
        Args:
            query: 查询字符串
        """
        # 使用查询的哈希作为键（避免长查询占用过多内存）
        query_hash = self._hash_query(query)
        
        with self._query_lock:
            now = datetime.now()
            
            if query_hash in self.query_frequency:
                entry = self.query_frequency[query_hash]
                entry.frequency += 1
                entry.last_access_time = now
            else:
                self.query_frequency[query_hash] = QueryEntry(
                    query=query[:200],  # 限制查询长度
                    frequency=1,
                    last_access_time=now
                )
            
            self.stats["total_query_updates"] += 1
            
            # 检查是否需要清理
            if len(self.query_frequency) > self.config.max_queries:
                self._cleanup_cold_queries()
    
    def get_heat_score(self, user_id: str) -> float:
        """
        获取用户热度分数
        
        Args:
            user_id: 用户ID
            
        Returns:
            float: 热度分数（0.0表示未追踪）
        """
        with self._user_lock:
            if user_id in self.user_heat:
                return self.user_heat[user_id].heat_score
            return 0.0
    
    def get_hot_users(self, threshold: Optional[float] = None) -> List[str]:
        """
        获取热门用户（top 20%）(Requirements 5.2)
        
        Args:
            threshold: 热度阈值（默认使用配置的hot_user_threshold）
            
        Returns:
            List[str]: 热门用户ID列表
        """
        threshold = threshold or self.config.hot_user_threshold
        
        with self._user_lock:
            if not self.user_heat:
                return []
            
            # 按热度分数排序
            sorted_users = sorted(
                self.user_heat.items(),
                key=lambda x: x[1].heat_score,
                reverse=True
            )
            
            # 过滤最小热度分数
            sorted_users = [
                (user_id, entry) for user_id, entry in sorted_users
                if entry.heat_score >= self.config.min_heat_score
            ]
            
            if not sorted_users:
                return []
            
            # 计算top 20%的数量
            top_count = max(1, int(len(sorted_users) * (1 - threshold)))
            
            # 返回热门用户ID
            hot_users = [user_id for user_id, _ in sorted_users[:top_count]]
            
            logger.debug(
                f"Hot users: {len(hot_users)}/{len(sorted_users)} "
                f"(threshold={threshold})"
            )
            
            return hot_users
    
    def get_hot_queries(self, threshold: Optional[int] = None) -> List[str]:
        """
        获取热门查询（frequency > 100）(Requirements 5.3)
        
        Args:
            threshold: 频率阈值（默认使用配置的hot_query_threshold）
            
        Returns:
            List[str]: 热门查询列表
        """
        threshold = threshold or self.config.hot_query_threshold
        
        with self._query_lock:
            if not self.query_frequency:
                return []
            
            # 过滤频率超过阈值的查询
            hot_queries = [
                entry.query
                for entry in self.query_frequency.values()
                if entry.frequency > threshold
            ]
            
            # 按频率排序
            hot_queries_with_freq = [
                (entry.query, entry.frequency)
                for entry in self.query_frequency.values()
                if entry.frequency > threshold
            ]
            hot_queries_with_freq.sort(key=lambda x: x[1], reverse=True)
            
            hot_queries = [query for query, _ in hot_queries_with_freq]
            
            logger.debug(
                f"Hot queries: {len(hot_queries)} "
                f"(threshold={threshold})"
            )
            
            return hot_queries
    
    def get_query_frequency(self, query: str) -> int:
        """
        获取查询频率
        
        Args:
            query: 查询字符串
            
        Returns:
            int: 查询频率（0表示未追踪）
        """
        query_hash = self._hash_query(query)
        
        with self._query_lock:
            if query_hash in self.query_frequency:
                return self.query_frequency[query_hash].frequency
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取热度图统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self._user_lock:
            user_count = len(self.user_heat)
            if self.user_heat:
                avg_heat = sum(e.heat_score for e in self.user_heat.values()) / user_count
                max_heat = max(e.heat_score for e in self.user_heat.values())
            else:
                avg_heat = 0.0
                max_heat = 0.0
        
        with self._query_lock:
            query_count = len(self.query_frequency)
            if self.query_frequency:
                avg_freq = sum(e.frequency for e in self.query_frequency.values()) / query_count
                max_freq = max(e.frequency for e in self.query_frequency.values())
            else:
                avg_freq = 0.0
                max_freq = 0
        
        return {
            **self.stats,
            "tracked_users": user_count,
            "tracked_queries": query_count,
            "avg_heat_score": round(avg_heat, 2),
            "max_heat_score": round(max_heat, 2),
            "avg_query_frequency": round(avg_freq, 2),
            "max_query_frequency": max_freq,
            "hot_users_count": len(self.get_hot_users()),
            "hot_queries_count": len(self.get_hot_queries()),
            "config": {
                "decay_factor": self.config.decay_factor,
                "hot_user_threshold": self.config.hot_user_threshold,
                "hot_query_threshold": self.config.hot_query_threshold
            }
        }
    
    def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热度最高的用户
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[Dict[str, Any]]: 用户热度信息列表
        """
        with self._user_lock:
            sorted_users = sorted(
                self.user_heat.items(),
                key=lambda x: x[1].heat_score,
                reverse=True
            )[:limit]
            
            return [
                {
                    "user_id": user_id,
                    **entry.to_dict()
                }
                for user_id, entry in sorted_users
            ]
    
    def get_top_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取频率最高的查询
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[Dict[str, Any]]: 查询频率信息列表
        """
        with self._query_lock:
            sorted_queries = sorted(
                self.query_frequency.values(),
                key=lambda x: x.frequency,
                reverse=True
            )[:limit]
            
            return [entry.to_dict() for entry in sorted_queries]
    
    async def _decay_loop(self):
        """热度衰减循环"""
        while self._running:
            try:
                await asyncio.sleep(self.config.decay_interval_seconds)
                self._apply_decay()
                self.stats["decay_cycles"] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heat decay error: {e}")
    
    def _apply_decay(self):
        """应用热度衰减"""
        with self._user_lock:
            for entry in self.user_heat.values():
                entry.heat_score *= self.config.decay_factor
        
        logger.debug(f"Applied heat decay to {len(self.user_heat)} users")
    
    async def _cleanup_loop(self):
        """清理循环"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                self._cleanup_stale_data()
                self.stats["cleanup_cycles"] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    def _cleanup_stale_data(self):
        """清理过期数据"""
        stale_threshold = datetime.now() - timedelta(hours=self.config.stale_threshold_hours)
        
        # 清理过期用户
        with self._user_lock:
            stale_users = [
                user_id for user_id, entry in self.user_heat.items()
                if entry.last_access_time < stale_threshold
            ]
            for user_id in stale_users:
                del self.user_heat[user_id]
            self.stats["users_cleaned"] += len(stale_users)
        
        # 清理过期查询
        with self._query_lock:
            stale_queries = [
                query_hash for query_hash, entry in self.query_frequency.items()
                if entry.last_access_time < stale_threshold
            ]
            for query_hash in stale_queries:
                del self.query_frequency[query_hash]
            self.stats["queries_cleaned"] += len(stale_queries)
        
        if stale_users or stale_queries:
            logger.info(
                f"Cleaned stale data: {len(stale_users)} users, "
                f"{len(stale_queries)} queries"
            )
    
    def _cleanup_cold_users(self):
        """清理冷门用户（当超过最大数量时）"""
        with self._user_lock:
            if len(self.user_heat) <= self.config.max_users:
                return
            
            # 按热度排序，删除最冷的用户
            sorted_users = sorted(
                self.user_heat.items(),
                key=lambda x: x[1].heat_score
            )
            
            # 删除最冷的10%
            remove_count = len(sorted_users) // 10
            for user_id, _ in sorted_users[:remove_count]:
                del self.user_heat[user_id]
            
            self.stats["users_cleaned"] += remove_count
            logger.debug(f"Cleaned {remove_count} cold users")
    
    def _cleanup_cold_queries(self):
        """清理冷门查询（当超过最大数量时）"""
        with self._query_lock:
            if len(self.query_frequency) <= self.config.max_queries:
                return
            
            # 按频率排序，删除最冷的查询
            sorted_queries = sorted(
                self.query_frequency.items(),
                key=lambda x: x[1].frequency
            )
            
            # 删除最冷的10%
            remove_count = len(sorted_queries) // 10
            for query_hash, _ in sorted_queries[:remove_count]:
                del self.query_frequency[query_hash]
            
            self.stats["queries_cleaned"] += remove_count
            logger.debug(f"Cleaned {remove_count} cold queries")
    
    def _hash_query(self, query: str) -> str:
        """
        计算查询哈希
        
        Args:
            query: 查询字符串
            
        Returns:
            str: 查询哈希
        """
        import hashlib
        # 标准化查询（去除多余空格，转小写）
        normalized = ' '.join(query.lower().split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:16]
    
    def clear(self):
        """清空所有数据"""
        with self._user_lock:
            self.user_heat.clear()
        
        with self._query_lock:
            self.query_frequency.clear()
        
        logger.info("HeatMap cleared")


# 全局热度图实例
_global_heat_map: Optional[HeatMap] = None


def get_heat_map() -> HeatMap:
    """
    获取全局热度图实例
    
    Returns:
        HeatMap: 热度图实例
    """
    global _global_heat_map
    if _global_heat_map is None:
        _global_heat_map = HeatMap()
    return _global_heat_map


def set_heat_map(heat_map: HeatMap):
    """
    设置全局热度图实例
    
    Args:
        heat_map: 热度图实例
    """
    global _global_heat_map
    _global_heat_map = heat_map


# 导出
__all__ = [
    "HeatMap",
    "HeatMapConfig",
    "HeatEntry",
    "QueryEntry",
    "get_heat_map",
    "set_heat_map"
]
