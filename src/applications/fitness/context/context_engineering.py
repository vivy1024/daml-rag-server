# -*- coding: utf-8 -*-
"""
上下文工程主模块

参考 LangChain Memory 设计模式，实现多轮对话上下文管理。

核心功能：
1. 对话历史管理（滑动窗口）
2. Token智能压缩
3. 用户档案自动注入
4. 话题切换逻辑

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5

版本: v1.0.0
日期: 2025-12-31
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .conversation_memory import (
    ConversationMemory,
    Message,
    MessageRole,
)
from .token_compressor import (
    TokenCompressor,
    CompressionConfig,
    CompressionStrategy,
)
from .profile_injector import (
    ProfileInjector,
    ProfileInjectionConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class ContextConfig:
    """上下文工程配置"""
    # 历史管理
    max_history: int = 5                 # 最大历史轮数（默认5轮）
    enable_persistence: bool = True      # 是否启用持久化
    
    # Token压缩
    max_tokens: int = 4000               # Token上限
    compression_strategy: CompressionStrategy = CompressionStrategy.HYBRID
    keep_messages: int = 10              # 压缩时保留的消息数
    
    # 档案注入
    inject_profile: bool = True          # 是否注入用户档案
    profile_style: str = "concise"       # 档案格式风格
    
    # 话题管理
    auto_create_topic: bool = True       # 是否自动创建话题
    topic_timeout_minutes: int = 30      # 话题超时时间（分钟）


@dataclass
class ContextResult:
    """上下文构建结果"""
    # 核心上下文
    conversation_history: List[Dict[str, str]]  # LLM格式的对话历史
    user_profile_text: str                       # 格式化的用户档案
    current_message: str                         # 当前用户消息
    
    # 元数据
    topic_id: str                                # 话题ID
    conversation_turn: int                       # 对话轮数
    total_tokens: int                            # 总Token数
    was_compressed: bool                         # 是否进行了压缩
    profile_utilization: float                   # 档案利用率
    
    # 原始数据
    raw_messages: List[Message] = field(default_factory=list)
    user_profile: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "conversation_history": self.conversation_history,
            "user_profile_text": self.user_profile_text,
            "current_message": self.current_message,
            "topic_id": self.topic_id,
            "conversation_turn": self.conversation_turn,
            "total_tokens": self.total_tokens,
            "was_compressed": self.was_compressed,
            "profile_utilization": self.profile_utilization,
        }


class ContextEngineering:
    """
    上下文工程主类
    
    参考 LangChain Memory 设计模式，整合：
    - ConversationMemory: 对话历史管理
    - TokenCompressor: Token智能压缩
    - ProfileInjector: 用户档案注入
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    
    def __init__(
        self,
        config: Optional[ContextConfig] = None,
        backend_client = None,
        llm_client = None,
    ):
        """
        初始化上下文工程
        
        Args:
            config: 上下文配置
            backend_client: 后端客户端（用于持久化）
            llm_client: LLM客户端（用于摘要压缩）
        """
        self.config = config or ContextConfig()
        self.backend_client = backend_client
        self.llm_client = llm_client
        
        # 初始化子组件
        self.memory = ConversationMemory(
            max_history=self.config.max_history,
            backend_client=backend_client,
            enable_persistence=self.config.enable_persistence,
        )
        
        self.compressor = TokenCompressor(
            config=CompressionConfig(
                max_tokens=self.config.max_tokens,
                keep_messages=self.config.keep_messages,
                strategy=self.config.compression_strategy,
            ),
            llm_client=llm_client,
        )
        
        self.profile_injector = ProfileInjector(
            config=ProfileInjectionConfig(
                format_style=self.config.profile_style,
            ),
        )
        
        logger.info(
            f"ContextEngineering initialized: "
            f"max_history={self.config.max_history}, "
            f"max_tokens={self.config.max_tokens}, "
            f"compression={self.config.compression_strategy.value}"
        )
    
    async def build_context(
        self,
        user_id: str,
        message: str,
        topic_id: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> ContextResult:
        """
        构建完整的对话上下文
        
        这是主要的入口方法，整合所有上下文工程功能。
        
        Args:
            user_id: 用户ID
            message: 当前用户消息
            topic_id: 话题ID（可选）
            user_profile: 用户档案（可选）
            
        Returns:
            ContextResult: 构建的上下文结果
            
        Requirements: 8.1, 8.2, 8.3, 8.5
        """
        logger.info(f"构建上下文: user={user_id}, topic={topic_id}")
        
        # 1. 确定话题
        if topic_id is None:
            topic_id = self.memory.get_active_topic_id(user_id)
        
        if topic_id is None and self.config.auto_create_topic:
            topic = await self.memory.create_topic(user_id, f"{user_id}_default")
            topic_id = topic.topic_id
        
        # 2. 获取对话历史
        history_messages = await self.memory.get_history(
            user_id=user_id,
            topic_id=topic_id,
        )
        
        # 3. Token压缩（如果需要）
        was_compressed = False
        if self.compressor.needs_compression(history_messages):
            history_messages = await self.compressor.compress(history_messages)
            was_compressed = True
        
        # 4. 格式化用户档案
        profile_text = ""
        if self.config.inject_profile and user_profile:
            profile_text = self.profile_injector.format_profile_for_context(
                user_profile
            )
        
        # 5. 计算统计信息
        conversation_turn = self.memory.get_conversation_turn(user_id, topic_id)
        total_tokens = self.compressor.count_messages_tokens(history_messages)
        total_tokens += self.compressor.count_tokens(message)
        total_tokens += self.compressor.count_tokens(profile_text)
        
        # 6. 格式化为LLM格式
        conversation_history = self.memory.format_history_for_llm(
            history_messages,
            include_system=True,
        )
        
        # 7. 构建结果
        result = ContextResult(
            conversation_history=conversation_history,
            user_profile_text=profile_text,
            current_message=message,
            topic_id=topic_id or "",
            conversation_turn=conversation_turn,
            total_tokens=total_tokens,
            was_compressed=was_compressed,
            profile_utilization=0.0,  # 稍后计算
            raw_messages=history_messages,
            user_profile=user_profile,
        )
        
        logger.info(
            f"上下文构建完成: "
            f"history={len(history_messages)}条, "
            f"tokens={total_tokens}, "
            f"compressed={was_compressed}"
        )
        
        return result
    
    async def add_turn(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        topic_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加一轮对话到历史
        
        Args:
            user_id: 用户ID
            user_message: 用户消息
            assistant_response: 助手响应
            topic_id: 话题ID
            session_id: 会话ID（用于PHP后端持久化）
            tools_used: 使用的工具列表
            metadata: 元数据
            
        Requirements: 8.3
        """
        # 将session_id添加到metadata中
        full_metadata = metadata.copy() if metadata else {}
        if session_id:
            full_metadata['session_id'] = session_id
        
        # 添加用户消息
        await self.memory.add_user_message(
            user_id=user_id,
            content=user_message,
            topic_id=topic_id,
            metadata=full_metadata,
        )
        
        # 添加助手消息
        await self.memory.add_assistant_message(
            user_id=user_id,
            content=assistant_response,
            topic_id=topic_id,
            tools_used=tools_used,
            metadata=full_metadata,
        )
        
        logger.debug(
            f"添加对话轮次: user={user_id}, "
            f"user_len={len(user_message)}, "
            f"assistant_len={len(assistant_response)}"
        )
    
    async def switch_topic(
        self,
        user_id: str,
        new_topic_id: str,
        title: Optional[str] = None,
    ) -> None:
        """
        切换话题
        
        清空当前上下文，加载新话题历史。
        
        Args:
            user_id: 用户ID
            new_topic_id: 新话题ID
            title: 话题标题
            
        Requirements: 8.4
        """
        old_topic_id = self.memory.get_active_topic_id(user_id)
        
        # 切换到新话题
        await self.memory.switch_topic(
            user_id=user_id,
            topic_id=new_topic_id,
            create_if_not_exists=True,
        )
        
        logger.info(
            f"切换话题: user={user_id}, "
            f"from={old_topic_id} to={new_topic_id}"
        )
    
    async def clear_context(
        self,
        user_id: str,
        topic_id: Optional[str] = None,
    ) -> None:
        """
        清空上下文
        
        Args:
            user_id: 用户ID
            topic_id: 话题ID（可选，默认清空当前话题）
            
        Requirements: 8.4
        """
        await self.memory.clear_topic(user_id, topic_id)
        logger.info(f"清空上下文: user={user_id}, topic={topic_id}")
    
    def calculate_profile_utilization(
        self,
        user_profile: Dict[str, Any],
        response: str,
    ) -> float:
        """
        计算档案利用率
        
        Args:
            user_profile: 用户档案
            response: 系统响应
            
        Returns:
            利用率（0-100%）
        """
        return self.profile_injector.calculate_profile_utilization(
            user_profile, response
        )
    
    def build_llm_messages(
        self,
        context: ContextResult,
        system_prompt: str,
    ) -> List[Dict[str, str]]:
        """
        构建完整的LLM消息列表
        
        Args:
            context: 上下文结果
            system_prompt: 系统提示词
            
        Returns:
            LLM API格式的消息列表
        """
        messages = []
        
        # 1. 系统提示词（包含用户档案）
        full_system_prompt = system_prompt
        if context.user_profile_text:
            full_system_prompt = f"{system_prompt}\n\n{context.user_profile_text}"
        
        messages.append({
            "role": "system",
            "content": full_system_prompt,
        })
        
        # 2. 对话历史
        for msg in context.conversation_history:
            if msg["role"] != "system":  # 跳过历史中的系统消息
                messages.append(msg)
        
        # 3. 当前用户消息
        messages.append({
            "role": "user",
            "content": context.current_message,
        })
        
        return messages
    
    def get_context_stats(
        self,
        user_id: str,
        topic_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取上下文统计信息
        
        Args:
            user_id: 用户ID
            topic_id: 话题ID
            
        Returns:
            统计信息字典
        """
        if topic_id is None:
            topic_id = self.memory.get_active_topic_id(user_id)
        
        return {
            "user_id": user_id,
            "topic_id": topic_id,
            "conversation_turn": self.memory.get_conversation_turn(user_id, topic_id),
            "max_history": self.config.max_history,
            "max_tokens": self.config.max_tokens,
            "compression_strategy": self.config.compression_strategy.value,
        }


# ============ 便捷函数 ============

_default_context_engine: Optional[ContextEngineering] = None


def get_context_engine(
    backend_client = None,
    llm_client = None,
) -> ContextEngineering:
    """
    获取默认的上下文工程实例（单例）
    
    Args:
        backend_client: 后端客户端
        llm_client: LLM客户端
        
    Returns:
        ContextEngineering实例
    """
    global _default_context_engine
    
    if _default_context_engine is None:
        _default_context_engine = ContextEngineering(
            backend_client=backend_client,
            llm_client=llm_client,
        )
    
    return _default_context_engine


async def build_context(
    user_id: str,
    message: str,
    topic_id: Optional[str] = None,
    user_profile: Optional[Dict[str, Any]] = None,
) -> ContextResult:
    """
    构建上下文的便捷函数
    
    Args:
        user_id: 用户ID
        message: 当前消息
        topic_id: 话题ID
        user_profile: 用户档案
        
    Returns:
        ContextResult
    """
    engine = get_context_engine()
    return await engine.build_context(
        user_id=user_id,
        message=message,
        topic_id=topic_id,
        user_profile=user_profile,
    )
