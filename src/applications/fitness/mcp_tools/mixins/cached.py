# -*- coding: utf-8 -*-
"""
CachedToolMixin - 缓存集成Mixin

提供缓存读写辅助方法，工具可通过 get_cached/set_cached 快速接入缓存层。

Task 44 - Phase 7 Batch 4
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CACHE_MISS = object()


class CachedToolMixin:
    """
    缓存集成Mixin

    依赖 self.cache_manager（由BaseMCPTool.__init__注入）。
    当 cache_manager 为 None 时，所有操作静默跳过。
    """

    def get_cached(self, key: str) -> Any:
        """
        从缓存读取值。

        Returns:
            缓存值，未命中时返回 None。
        """
        if not getattr(self, "cache_manager", None):
            return None
        try:
            return self.cache_manager.get(key)
        except Exception as e:
            logger.debug(f"缓存读取失败(key={key}): {e}")
            return None

    def set_cached(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """写入缓存，返回是否成功。"""
        if not getattr(self, "cache_manager", None):
            return False
        try:
            if ttl is not None:
                self.cache_manager.set(key, value, ttl=ttl)
            else:
                self.cache_manager.set(key, value)
            return True
        except Exception as e:
            logger.debug(f"缓存写入失败(key={key}): {e}")
            return False

    def invalidate_cached(self, key: str) -> bool:
        """删除缓存键。"""
        if not getattr(self, "cache_manager", None):
            return False
        try:
            self.cache_manager.delete(key)
            return True
        except Exception as e:
            logger.debug(f"缓存删除失败(key={key}): {e}")
            return False
