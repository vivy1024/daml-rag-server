# -*- coding: utf-8 -*-
"""
Checkpointer 工厂模块

提供 LangGraph 状态持久化能力：
- 生产环境：使用 Redis 作为 checkpoint 存储
- 开发环境：使用 InMemorySaver 作为 fallback
- 支持从环境变量读取 Redis 连接信息

版本：v1.0.0
更新日期：2026-03-15
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CheckpointerConfig:
    """Checkpointer 配置"""
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 1  # 使用 db=1 避免与 session 缓存冲突
    use_memory_fallback: bool = False  # 强制使用内存模式
    key_prefix: str = "langgraph:checkpoint:"
    ttl_seconds: int = 86400 * 7  # 7天过期

    @classmethod
    def from_env(cls) -> "CheckpointerConfig":
        """从环境变量加载配置"""
        return cls(
            redis_host=os.getenv("REDIS_HOST", "redis"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_password=os.getenv("REDIS_PASSWORD", ""),
            redis_db=int(os.getenv("CHECKPOINT_REDIS_DB", "1")),
            use_memory_fallback=os.getenv(
                "CHECKPOINT_USE_MEMORY", "false"
            ).lower() == "true",
            key_prefix=os.getenv(
                "CHECKPOINT_KEY_PREFIX", "langgraph:checkpoint:"
            ),
            ttl_seconds=int(os.getenv("CHECKPOINT_TTL", "604800")),
        )


def get_checkpointer(config: Optional[CheckpointerConfig] = None):
    """
    获取 LangGraph Checkpointer 实例

    降级策略：
    1. 如果配置了 use_memory_fallback=True → 直接返回 InMemorySaver
    2. 尝试创建 Redis checkpointer
    3. Redis 连接失败 → 降级到 InMemorySaver

    Returns:
        BaseCheckpointSaver 实例（RedisSaver 或 InMemorySaver）
    """
    if config is None:
        config = CheckpointerConfig.from_env()

    # 开发模式：强制使用内存
    if config.use_memory_fallback:
        logger.info("Checkpointer: 使用 InMemorySaver（开发模式）")
        return _get_memory_saver()

    # 生产模式：尝试 Redis
    try:
        return _get_redis_saver(config)
    except Exception as e:
        logger.warning(
            "Redis Checkpointer 初始化失败，降级到 InMemorySaver: %s", e
        )
        return _get_memory_saver()


def _get_redis_saver(config: CheckpointerConfig):
    """创建 Redis Checkpointer"""
    from langgraph.checkpoint.redis import RedisSaver

    # 构建 Redis URL
    password_part = f":{config.redis_password}@" if config.redis_password else ""
    redis_url = (
        f"redis://{password_part}{config.redis_host}:"
        f"{config.redis_port}/{config.redis_db}"
    )

    saver = RedisSaver.from_conn_string(redis_url)
    logger.info(
        "Checkpointer: 使用 RedisSaver (host=%s, port=%d, db=%d)",
        config.redis_host, config.redis_port, config.redis_db,
    )
    return saver


def _get_memory_saver():
    """创建内存 Checkpointer（开发/测试用）"""
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()
