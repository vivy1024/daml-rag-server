# -*- coding: utf-8 -*-
"""
对话记忆管理模块

参考 LangChain ConversationBufferWindowMemory 设计，
实现滑动窗口式的对话历史管理。
支持 Redis 持久化（redis.asyncio），不可用时降级到纯内存。

Requirements: 8.1, 8.3

版本: v2.0.0
日期: 2026-02-17
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """
    对话消息数据类
    
    参考 LangChain BaseMessage 设计
    """
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 可选字段
    message_id: Optional[str] = None
    tools_used: Optional[List[str]] = None
    token_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "message_id": self.message_id,
            "tools_used": self.tools_used,
            "token_count": self.token_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
            message_id=data.get("message_id"),
            tools_used=data.get("tools_used"),
            token_count=data.get("token_count"),
        )
    
    def to_llm_format(self) -> Dict[str, str]:
        """转换为LLM API格式"""
        return {
            "role": self.role.value,
            "content": self.content,
        }


@dataclass
class ConversationTopic:
    """
    对话话题数据类
    
    用于管理话题切换和历史分组
    """
    topic_id: str
    title: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    
    def add_message(self, message: Message) -> None:
        """添加消息到话题"""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, n: int) -> List[Message]:
        """获取最近N条消息"""
        return self.messages[-n:] if n > 0 else []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "topic_id": self.topic_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
            "is_active": self.is_active,
        }


class ConversationMemory:
    """
    对话记忆管理器

    参考 LangChain ConversationBufferWindowMemory 设计：
    - 支持滑动窗口（最近N轮）
    - 支持话题分组
    - 支持 Redis 持久化（redis.asyncio）
    - Redis 不可用时降级到纯内存

    Redis Key 设计：
    - conv:{user_id}:{topic_id}:messages  (List) - 消息列表
    - conv:{user_id}:active_topic         (String) - 当前活跃话题
    - conv:{user_id}:topics               (Hash) - 话题元数据

    Requirements: 8.1, 8.3
    """

    DEFAULT_TTL = 86400  # 24小时

    def __init__(
        self,
        max_history: int = 5,
        backend_client=None,
        enable_persistence: bool = True,
        redis_client=None,
        redis_ttl: int = DEFAULT_TTL,
    ):
        """
        初始化对话记忆管理器

        Args:
            max_history: 最大历史轮数（默认5轮，即10条消息）
            backend_client: 后端客户端（用于持久化到MySQL）
            enable_persistence: 是否启用持久化
            redis_client: redis.asyncio 客户端（可选）
            redis_ttl: Redis Key TTL，默认86400秒
        """
        self.max_history = max_history
        self.backend_client = backend_client
        self.enable_persistence = enable_persistence
        self.redis_client = redis_client
        self.redis_ttl = redis_ttl

        # 内存缓存：user_id -> topic_id -> ConversationTopic
        self._memory_store: Dict[str, Dict[str, ConversationTopic]] = {}

        # 当前活跃话题：user_id -> topic_id
        self._active_topics: Dict[str, str] = {}

        logger.info(
            f"ConversationMemory initialized: "
            f"max_history={max_history}, persistence={enable_persistence}, "
            f"redis={'enabled' if redis_client else 'disabled'}"
        )
    
    async def get_history(
        self,
        user_id: str,
        topic_id: Optional[str] = None,
        n_messages: Optional[int] = None,
    ) -> List[Message]:
        """
        获取对话历史（Redis → 内存 → 后端）

        Args:
            user_id: 用户ID
            topic_id: 话题ID（可选，默认使用当前活跃话题）
            n_messages: 返回消息数量（可选，默认使用max_history*2）

        Returns:
            消息列表

        Requirements: 8.1
        """
        # 确定话题ID
        if topic_id is None:
            topic_id = self._active_topics.get(user_id)
            # 尝试从 Redis 恢复活跃话题
            if topic_id is None:
                topic_id = await self._redis_get_active_topic(user_id)
                if topic_id:
                    self._active_topics[user_id] = topic_id

        if topic_id is None:
            logger.debug(f"用户 {user_id} 没有活跃话题")
            return []

        # 计算返回数量
        if n_messages is None:
            n_messages = self.max_history * 2

        # 1. 尝试从 Redis 获取
        messages = await self._redis_get_messages(user_id, topic_id, n_messages)
        if messages:
            return messages

        # 2. 尝试从内存获取
        topic = self._get_topic_from_memory(user_id, topic_id)
        if topic:
            return topic.get_recent_messages(n_messages)

        # 3. 尝试从后端加载
        if self.enable_persistence and self.backend_client:
            topic = await self._load_topic_from_backend(user_id, topic_id)
            if topic:
                # 回填 Redis
                await self._redis_backfill_topic(user_id, topic)
                return topic.get_recent_messages(n_messages)

        return []
    
    async def add_message(
        self,
        user_id: str,
        message: Message,
        topic_id: Optional[str] = None,
    ) -> None:
        """
        添加消息到对话历史（同时写 Redis + 内存）

        Args:
            user_id: 用户ID
            message: 消息对象
            topic_id: 话题ID（可选）

        Requirements: 8.3
        """
        # 确定话题ID
        if topic_id is None:
            topic_id = self._active_topics.get(user_id)

        # 如果没有活跃话题，创建新话题
        if topic_id is None:
            topic_id = self._generate_topic_id(user_id)
            await self.create_topic(user_id, topic_id)

        # 获取或创建话题（内存）
        topic = self._get_topic_from_memory(user_id, topic_id)
        if topic is None:
            topic = ConversationTopic(topic_id=topic_id)
            self._store_topic_in_memory(user_id, topic)

        # 添加消息到内存
        topic.add_message(message)

        # 写入 Redis
        await self._redis_push_message(user_id, topic_id, message)

        # 持久化到后端
        if self.enable_persistence and self.backend_client:
            await self._persist_message(user_id, topic_id, message)

        logger.debug(
            f"添加消息: user={user_id}, topic={topic_id}, "
            f"role={message.role.value}, len={len(message.content)}"
        )
    
    async def add_user_message(
        self,
        user_id: str,
        content: str,
        topic_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        添加用户消息（便捷方法）
        
        Args:
            user_id: 用户ID
            content: 消息内容
            topic_id: 话题ID
            metadata: 元数据
            
        Returns:
            创建的消息对象
        """
        message = Message(
            role=MessageRole.USER,
            content=content,
            metadata=metadata or {},
        )
        await self.add_message(user_id, message, topic_id)
        return message
    
    async def add_assistant_message(
        self,
        user_id: str,
        content: str,
        topic_id: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        添加助手消息（便捷方法）
        
        Args:
            user_id: 用户ID
            content: 消息内容
            topic_id: 话题ID
            tools_used: 使用的工具列表
            metadata: 元数据
            
        Returns:
            创建的消息对象
        """
        message = Message(
            role=MessageRole.ASSISTANT,
            content=content,
            tools_used=tools_used,
            metadata=metadata or {},
        )
        await self.add_message(user_id, message, topic_id)
        return message
    
    async def create_topic(
        self,
        user_id: str,
        topic_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationTopic:
        """
        创建新话题

        Args:
            user_id: 用户ID
            topic_id: 话题ID
            title: 话题标题
            metadata: 元数据

        Returns:
            创建的话题对象
        """
        topic = ConversationTopic(
            topic_id=topic_id,
            title=title,
            metadata=metadata or {},
        )

        # 存储到内存
        self._store_topic_in_memory(user_id, topic)

        # 设置为活跃话题
        self._active_topics[user_id] = topic_id

        # 写入 Redis
        await self._redis_set_active_topic(user_id, topic_id)
        await self._redis_save_topic_meta(user_id, topic)

        # 持久化到后端
        if self.enable_persistence and self.backend_client:
            await self._persist_topic(user_id, topic)

        logger.info(f"创建新话题: user={user_id}, topic={topic_id}")
        return topic
    
    async def switch_topic(
        self,
        user_id: str,
        topic_id: str,
        create_if_not_exists: bool = True,
    ) -> Optional[ConversationTopic]:
        """
        切换话题

        Args:
            user_id: 用户ID
            topic_id: 目标话题ID
            create_if_not_exists: 如果不存在是否创建

        Returns:
            切换后的话题对象

        Requirements: 8.4
        """
        # 尝试获取话题
        topic = self._get_topic_from_memory(user_id, topic_id)

        # 如果内存没有，尝试从 Redis 加载
        if topic is None:
            topic = await self._redis_load_topic(user_id, topic_id)

        # 如果 Redis 也没有，尝试从后端加载
        if topic is None and self.enable_persistence and self.backend_client:
            topic = await self._load_topic_from_backend(user_id, topic_id)

        # 如果不存在且允许创建
        if topic is None and create_if_not_exists:
            topic = await self.create_topic(user_id, topic_id)

        if topic is not None:
            # 更新活跃话题
            old_topic_id = self._active_topics.get(user_id)
            self._active_topics[user_id] = topic_id
            await self._redis_set_active_topic(user_id, topic_id)

            logger.info(
                f"切换话题: user={user_id}, "
                f"from={old_topic_id} to={topic_id}"
            )

        return topic
    
    async def clear_topic(
        self,
        user_id: str,
        topic_id: Optional[str] = None,
    ) -> None:
        """
        清空话题历史

        Args:
            user_id: 用户ID
            topic_id: 话题ID（可选，默认清空当前活跃话题）

        Requirements: 8.4
        """
        if topic_id is None:
            topic_id = self._active_topics.get(user_id)

        if topic_id is None:
            return

        # 从内存清除
        if user_id in self._memory_store:
            if topic_id in self._memory_store[user_id]:
                self._memory_store[user_id][topic_id].messages.clear()

        # 从 Redis 清除
        await self._redis_delete_topic(user_id, topic_id)

        # 从后端清除
        if self.enable_persistence and self.backend_client:
            await self._clear_topic_from_backend(user_id, topic_id)

        logger.info(f"清空话题: user={user_id}, topic={topic_id}")
    
    def get_active_topic_id(self, user_id: str) -> Optional[str]:
        """获取用户当前活跃话题ID"""
        return self._active_topics.get(user_id)
    
    def get_conversation_turn(self, user_id: str, topic_id: Optional[str] = None) -> int:
        """
        获取当前对话轮数
        
        Args:
            user_id: 用户ID
            topic_id: 话题ID
            
        Returns:
            对话轮数（用户消息数量）
        """
        if topic_id is None:
            topic_id = self._active_topics.get(user_id)
        
        if topic_id is None:
            return 0
        
        topic = self._get_topic_from_memory(user_id, topic_id)
        if topic is None:
            return 0
        
        # 计算用户消息数量
        return sum(1 for m in topic.messages if m.role == MessageRole.USER)
    
    def format_history_for_llm(
        self,
        messages: List[Message],
        include_system: bool = False,
    ) -> List[Dict[str, str]]:
        """
        将消息历史格式化为LLM API格式
        
        Args:
            messages: 消息列表
            include_system: 是否包含系统消息
            
        Returns:
            LLM API格式的消息列表
        """
        result = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM and not include_system:
                continue
            result.append(msg.to_llm_format())
        return result
    
    # ============ 私有方法 ============
    
    def _get_topic_from_memory(
        self,
        user_id: str,
        topic_id: str,
    ) -> Optional[ConversationTopic]:
        """从内存获取话题"""
        if user_id not in self._memory_store:
            return None
        return self._memory_store[user_id].get(topic_id)
    
    def _store_topic_in_memory(
        self,
        user_id: str,
        topic: ConversationTopic,
    ) -> None:
        """存储话题到内存"""
        if user_id not in self._memory_store:
            self._memory_store[user_id] = {}
        self._memory_store[user_id][topic.topic_id] = topic
    
    def _generate_topic_id(self, user_id: str) -> str:
        """生成话题ID"""
        import uuid
        return f"{user_id}_{uuid.uuid4().hex[:8]}"
    
    async def _load_topic_from_backend(
        self,
        user_id: str,
        topic_id: str,
    ) -> Optional[ConversationTopic]:
        """从后端加载话题"""
        if not self.backend_client:
            return None
        
        try:
            data = await self.backend_client.get_conversation_topic(
                user_id=user_id,
                topic_id=topic_id,
            )
            if data:
                topic = ConversationTopic(
                    topic_id=data.get("topic_id", topic_id),
                    title=data.get("title"),
                    messages=[
                        Message.from_dict(m) for m in data.get("messages", [])
                    ],
                    metadata=data.get("metadata", {}),
                )
                self._store_topic_in_memory(user_id, topic)
                return topic
        except Exception as e:
            logger.warning(f"从后端加载话题失败: {e}")
        
        return None
    
    async def _persist_message(
        self,
        user_id: str,
        topic_id: str,
        message: Message,
    ) -> None:
        """持久化消息到后端"""
        if not self.backend_client:
            return
        
        try:
            await self.backend_client.save_conversation_message(
                user_id=str(user_id),
                topic_id=str(topic_id),  # 确保topic_id是字符串
                message=message.to_dict(),
            )
        except Exception as e:
            logger.warning(f"持久化消息失败: {e}")
    
    async def _persist_topic(
        self,
        user_id: str,
        topic: ConversationTopic,
    ) -> None:
        """持久化话题到后端"""
        if not self.backend_client:
            return
        
        try:
            await self.backend_client.save_conversation_topic(
                user_id=user_id,
                topic=topic.to_dict(),
            )
        except Exception as e:
            logger.warning(f"持久化话题失败: {e}")
    
    async def _clear_topic_from_backend(
        self,
        user_id: str,
        topic_id: str,
    ) -> None:
        """从后端清除话题"""
        if not self.backend_client:
            return

        try:
            await self.backend_client.clear_conversation_topic(
                user_id=user_id,
                topic_id=topic_id,
            )
        except Exception as e:
            logger.warning(f"从后端清除话题失败: {e}")

    # ============ Redis 私有方法 ============

    def _redis_key_messages(self, user_id: str, topic_id: str) -> str:
        return f"conv:{user_id}:{topic_id}:messages"

    def _redis_key_active_topic(self, user_id: str) -> str:
        return f"conv:{user_id}:active_topic"

    def _redis_key_topics(self, user_id: str) -> str:
        return f"conv:{user_id}:topics"

    async def _redis_available(self) -> bool:
        """检查 Redis 是否可用"""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.ping()
            return True
        except Exception:
            return False

    async def _redis_push_message(
        self, user_id: str, topic_id: str, message: Message
    ) -> None:
        """将消息 RPUSH 到 Redis List"""
        if not await self._redis_available():
            return
        try:
            key = self._redis_key_messages(user_id, topic_id)
            data = json.dumps(message.to_dict(), ensure_ascii=False)
            await self.redis_client.rpush(key, data)
            # 保留最近 max_history*2 条，裁剪旧消息
            await self.redis_client.ltrim(key, -(self.max_history * 2), -1)
            await self.redis_client.expire(key, self.redis_ttl)
        except Exception as e:
            logger.warning(f"Redis push message 失败（降级到内存）: {e}")

    async def _redis_get_messages(
        self, user_id: str, topic_id: str, n: int
    ) -> List[Message]:
        """从 Redis List 读取最近 n 条消息"""
        if not await self._redis_available():
            return []
        try:
            key = self._redis_key_messages(user_id, topic_id)
            raw_list = await self.redis_client.lrange(key, -n, -1)
            if not raw_list:
                return []
            messages = []
            for raw in raw_list:
                data = json.loads(raw)
                messages.append(Message.from_dict(data))
            return messages
        except Exception as e:
            logger.warning(f"Redis get messages 失败（降级到内存）: {e}")
            return []

    async def _redis_set_active_topic(self, user_id: str, topic_id: str) -> None:
        """设置用户活跃话题"""
        if not await self._redis_available():
            return
        try:
            key = self._redis_key_active_topic(user_id)
            await self.redis_client.set(key, topic_id, ex=self.redis_ttl)
        except Exception as e:
            logger.warning(f"Redis set active topic 失败: {e}")

    async def _redis_get_active_topic(self, user_id: str) -> Optional[str]:
        """获取用户活跃话题"""
        if not await self._redis_available():
            return None
        try:
            key = self._redis_key_active_topic(user_id)
            val = await self.redis_client.get(key)
            return val.decode() if isinstance(val, bytes) else val
        except Exception as e:
            logger.warning(f"Redis get active topic 失败: {e}")
            return None

    async def _redis_save_topic_meta(
        self, user_id: str, topic: ConversationTopic
    ) -> None:
        """保存话题元数据到 Redis Hash"""
        if not await self._redis_available():
            return
        try:
            key = self._redis_key_topics(user_id)
            meta = json.dumps({
                "topic_id": topic.topic_id,
                "title": topic.title,
                "created_at": topic.created_at.isoformat(),
                "updated_at": topic.updated_at.isoformat(),
                "is_active": topic.is_active,
                "metadata": topic.metadata,
            }, ensure_ascii=False)
            await self.redis_client.hset(key, topic.topic_id, meta)
            await self.redis_client.expire(key, self.redis_ttl)
        except Exception as e:
            logger.warning(f"Redis save topic meta 失败: {e}")

    async def _redis_load_topic(
        self, user_id: str, topic_id: str
    ) -> Optional[ConversationTopic]:
        """从 Redis 加载话题（元数据 + 消息）"""
        if not await self._redis_available():
            return None
        try:
            # 读取元数据
            topics_key = self._redis_key_topics(user_id)
            raw_meta = await self.redis_client.hget(topics_key, topic_id)
            if not raw_meta:
                return None
            meta = json.loads(raw_meta)

            # 读取消息
            messages = await self._redis_get_messages(
                user_id, topic_id, self.max_history * 2
            )

            topic = ConversationTopic(
                topic_id=meta.get("topic_id", topic_id),
                title=meta.get("title"),
                created_at=datetime.fromisoformat(meta["created_at"]),
                updated_at=datetime.fromisoformat(meta["updated_at"]),
                messages=messages,
                metadata=meta.get("metadata", {}),
                is_active=meta.get("is_active", True),
            )
            # 同步到内存
            self._store_topic_in_memory(user_id, topic)
            return topic
        except Exception as e:
            logger.warning(f"Redis load topic 失败: {e}")
            return None

    async def _redis_delete_topic(self, user_id: str, topic_id: str) -> None:
        """从 Redis 删除话题数据"""
        if not await self._redis_available():
            return
        try:
            msg_key = self._redis_key_messages(user_id, topic_id)
            topics_key = self._redis_key_topics(user_id)
            await self.redis_client.delete(msg_key)
            await self.redis_client.hdel(topics_key, topic_id)
        except Exception as e:
            logger.warning(f"Redis delete topic 失败: {e}")

    async def _redis_backfill_topic(
        self, user_id: str, topic: ConversationTopic
    ) -> None:
        """将后端加载的话题回填到 Redis"""
        if not await self._redis_available():
            return
        try:
            await self._redis_save_topic_meta(user_id, topic)
            key = self._redis_key_messages(user_id, topic.topic_id)
            for msg in topic.messages[-(self.max_history * 2):]:
                data = json.dumps(msg.to_dict(), ensure_ascii=False)
                await self.redis_client.rpush(key, data)
            await self.redis_client.expire(key, self.redis_ttl)
        except Exception as e:
            logger.warning(f"Redis backfill topic 失败: {e}")

    async def get_user_topics(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有话题列表（Redis → 内存）"""
        # 尝试 Redis
        if await self._redis_available():
            try:
                key = self._redis_key_topics(user_id)
                raw_all = await self.redis_client.hgetall(key)
                if raw_all:
                    topics = []
                    for _, raw_meta in raw_all.items():
                        meta = json.loads(raw_meta)
                        topics.append(meta)
                    return sorted(topics, key=lambda t: t.get("updated_at", ""), reverse=True)
            except Exception as e:
                logger.warning(f"Redis get user topics 失败: {e}")

        # 降级到内存
        if user_id in self._memory_store:
            return [t.to_dict() for t in self._memory_store[user_id].values()]
        return []
