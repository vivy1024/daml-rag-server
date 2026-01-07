# -*- coding: utf-8 -*-
"""
Token智能压缩模块

参考 LangChain SummarizationMiddleware 设计，
实现对话历史的智能压缩。

Requirements: 8.2

版本: v1.0.0
日期: 2025-12-31
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from .conversation_memory import Message, MessageRole

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    """压缩策略枚举"""
    TRIM_OLDEST = "trim_oldest"      # 裁剪最旧的消息
    TRIM_MIDDLE = "trim_middle"      # 保留首尾，裁剪中间
    SUMMARIZE = "summarize"          # 使用LLM摘要
    HYBRID = "hybrid"                # 混合策略（保留最近N条+历史摘要）


@dataclass
class CompressionConfig:
    """压缩配置"""
    max_tokens: int = 4000           # Token上限
    keep_messages: int = 10          # 保留最近消息数
    keep_first: bool = True          # 是否保留第一条消息
    strategy: CompressionStrategy = CompressionStrategy.HYBRID
    summary_max_tokens: int = 500    # 摘要最大Token数
    
    # Token计数配置
    avg_chars_per_token: float = 2.5  # 中文平均每Token字符数


class TokenCompressor:
    """
    Token智能压缩器
    
    参考 LangChain SummarizationMiddleware 设计：
    - 支持多种压缩策略
    - 支持Token计数
    - 支持LLM摘要
    
    Requirements: 8.2
    """
    
    def __init__(
        self,
        config: Optional[CompressionConfig] = None,
        llm_client = None,
        token_counter: Optional[Callable[[str], int]] = None,
    ):
        """
        初始化Token压缩器
        
        Args:
            config: 压缩配置
            llm_client: LLM客户端（用于摘要）
            token_counter: 自定义Token计数函数
        """
        self.config = config or CompressionConfig()
        self.llm_client = llm_client
        self._token_counter = token_counter
        
        logger.info(
            f"TokenCompressor initialized: "
            f"max_tokens={self.config.max_tokens}, "
            f"strategy={self.config.strategy.value}"
        )
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数量
        
        Args:
            text: 文本内容
            
        Returns:
            Token数量
        """
        if self._token_counter:
            return self._token_counter(text)
        
        # 默认使用字符数估算（中文约2.5字符/token）
        return int(len(text) / self.config.avg_chars_per_token)
    
    def count_messages_tokens(self, messages: List[Message]) -> int:
        """
        计算消息列表的总Token数
        
        Args:
            messages: 消息列表
            
        Returns:
            总Token数
        """
        total = 0
        for msg in messages:
            # 消息内容
            total += self.count_tokens(msg.content)
            # 角色标记（约4 tokens）
            total += 4
        return total
    
    def needs_compression(self, messages: List[Message]) -> bool:
        """
        判断是否需要压缩
        
        Args:
            messages: 消息列表
            
        Returns:
            是否需要压缩
        """
        current_tokens = self.count_messages_tokens(messages)
        return current_tokens > self.config.max_tokens
    
    async def compress(
        self,
        messages: List[Message],
        force: bool = False,
    ) -> List[Message]:
        """
        压缩消息历史
        
        Args:
            messages: 原始消息列表
            force: 是否强制压缩
            
        Returns:
            压缩后的消息列表
            
        Requirements: 8.2
        """
        if not messages:
            return messages
        
        # 检查是否需要压缩
        if not force and not self.needs_compression(messages):
            return messages
        
        current_tokens = self.count_messages_tokens(messages)
        logger.info(
            f"开始压缩: {len(messages)}条消息, "
            f"{current_tokens} tokens -> {self.config.max_tokens} tokens"
        )
        
        # 根据策略选择压缩方法
        if self.config.strategy == CompressionStrategy.TRIM_OLDEST:
            result = self._trim_oldest(messages)
        elif self.config.strategy == CompressionStrategy.TRIM_MIDDLE:
            result = self._trim_middle(messages)
        elif self.config.strategy == CompressionStrategy.SUMMARIZE:
            result = await self._summarize(messages)
        else:  # HYBRID
            result = await self._hybrid_compress(messages)
        
        result_tokens = self.count_messages_tokens(result)
        logger.info(
            f"压缩完成: {len(messages)}条 -> {len(result)}条, "
            f"{current_tokens} tokens -> {result_tokens} tokens"
        )
        
        return result
    
    def _trim_oldest(self, messages: List[Message]) -> List[Message]:
        """
        裁剪最旧的消息
        
        保留最近的消息，直到Token数量符合限制
        """
        if not messages:
            return messages
        
        result = []
        current_tokens = 0
        
        # 如果需要保留第一条消息
        first_message = None
        if self.config.keep_first and messages:
            first_message = messages[0]
            current_tokens += self.count_tokens(first_message.content) + 4
        
        # 从后往前添加消息
        for msg in reversed(messages[1:] if first_message else messages):
            msg_tokens = self.count_tokens(msg.content) + 4
            if current_tokens + msg_tokens <= self.config.max_tokens:
                result.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        # 添加第一条消息
        if first_message:
            result.insert(0, first_message)
        
        return result
    
    def _trim_middle(self, messages: List[Message]) -> List[Message]:
        """
        保留首尾，裁剪中间
        
        保留第一条消息和最近N条消息
        """
        if len(messages) <= self.config.keep_messages + 1:
            return messages
        
        result = []
        
        # 保留第一条
        if self.config.keep_first and messages:
            result.append(messages[0])
        
        # 添加省略标记
        omitted_count = len(messages) - self.config.keep_messages - 1
        if omitted_count > 0:
            result.append(Message(
                role=MessageRole.SYSTEM,
                content=f"[已省略 {omitted_count} 条历史消息]",
                metadata={"is_placeholder": True},
            ))
        
        # 保留最近N条
        result.extend(messages[-self.config.keep_messages:])
        
        return result
    
    async def _summarize(self, messages: List[Message]) -> List[Message]:
        """
        使用LLM摘要压缩
        
        将所有历史消息摘要为一条系统消息
        """
        if not self.llm_client:
            logger.warning("LLM客户端未配置，降级到trim_oldest策略")
            return self._trim_oldest(messages)
        
        try:
            # 构建摘要提示
            history_text = self._format_messages_for_summary(messages)
            
            summary_prompt = f"""请将以下对话历史压缩为简洁的摘要，保留关键信息：

{history_text}

请用一段话总结对话的主要内容和关键信息："""
            
            # 调用LLM生成摘要
            summary = await self.llm_client.generate(
                prompt=summary_prompt,
                max_tokens=self.config.summary_max_tokens,
            )
            
            # 创建摘要消息
            summary_message = Message(
                role=MessageRole.SYSTEM,
                content=f"[对话历史摘要]\n{summary}",
                metadata={
                    "is_summary": True,
                    "original_count": len(messages),
                },
            )
            
            return [summary_message]
            
        except Exception as e:
            logger.error(f"LLM摘要失败: {e}")
            return self._trim_oldest(messages)
    
    async def _hybrid_compress(self, messages: List[Message]) -> List[Message]:
        """
        混合压缩策略
        
        参考 LangChain ConversationSummaryBufferMemory：
        - 保留最近N条消息完整
        - 将更早的历史摘要为一条消息
        
        Requirements: 8.2
        """
        if len(messages) <= self.config.keep_messages:
            return messages
        
        # 分割消息
        recent_messages = messages[-self.config.keep_messages:]
        older_messages = messages[:-self.config.keep_messages]
        
        # 检查最近消息是否已经超限
        recent_tokens = self.count_messages_tokens(recent_messages)
        if recent_tokens > self.config.max_tokens:
            # 最近消息已超限，直接裁剪
            return self._trim_oldest(recent_messages)
        
        # 计算可用于摘要的Token数
        available_for_summary = self.config.max_tokens - recent_tokens - 100  # 预留100 tokens
        
        if available_for_summary <= 0 or not older_messages:
            return recent_messages
        
        # 生成历史摘要
        if self.llm_client:
            try:
                summary = await self._generate_summary(
                    older_messages,
                    max_tokens=min(available_for_summary, self.config.summary_max_tokens)
                )
                
                summary_message = Message(
                    role=MessageRole.SYSTEM,
                    content=f"[历史对话摘要]\n{summary}",
                    metadata={
                        "is_summary": True,
                        "original_count": len(older_messages),
                    },
                )
                
                return [summary_message] + recent_messages
                
            except Exception as e:
                logger.warning(f"生成摘要失败: {e}")
        
        # 降级：添加简单的省略标记
        placeholder = Message(
            role=MessageRole.SYSTEM,
            content=f"[已省略 {len(older_messages)} 条早期对话]",
            metadata={"is_placeholder": True},
        )
        
        return [placeholder] + recent_messages
    
    async def _generate_summary(
        self,
        messages: List[Message],
        max_tokens: int = 500,
    ) -> str:
        """
        生成消息摘要
        
        Args:
            messages: 要摘要的消息
            max_tokens: 摘要最大Token数
            
        Returns:
            摘要文本
        """
        history_text = self._format_messages_for_summary(messages)
        
        summary_prompt = f"""请将以下对话历史压缩为简洁的摘要，保留关键信息（用户的问题、系统的建议、重要的数据）：

{history_text}

摘要（不超过{max_tokens}字）："""
        
        summary = await self.llm_client.generate(
            prompt=summary_prompt,
            max_tokens=max_tokens,
        )
        
        return summary.strip()
    
    def _format_messages_for_summary(self, messages: List[Message]) -> str:
        """格式化消息用于摘要"""
        lines = []
        for msg in messages:
            role_name = {
                MessageRole.USER: "用户",
                MessageRole.ASSISTANT: "助手",
                MessageRole.SYSTEM: "系统",
            }.get(msg.role, "未知")
            
            # 截断过长的内容
            content = msg.content
            if len(content) > 500:
                content = content[:500] + "..."
            
            lines.append(f"{role_name}: {content}")
        
        return "\n".join(lines)
    
    def estimate_compression_ratio(self, messages: List[Message]) -> float:
        """
        估算压缩比
        
        Args:
            messages: 消息列表
            
        Returns:
            压缩比（0-1，越小压缩越多）
        """
        current_tokens = self.count_messages_tokens(messages)
        if current_tokens <= self.config.max_tokens:
            return 1.0
        return self.config.max_tokens / current_tokens
