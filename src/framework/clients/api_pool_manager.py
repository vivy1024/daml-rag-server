# -*- coding: utf-8 -*-
"""
API池轮询管理器

管理多个DeepSeek API Key的轮询调用，提高可用性和稳定性。

功能：
1. 多API Key轮询
2. 失败自动切换
3. 健康状态追踪
4. 负载均衡

版本: v1.0.0
创建日期: 2026-01-06
"""

import os
import logging
import asyncio
import time
import json
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


@dataclass
class APIKeyStatus:
    """API Key状态"""
    key: str
    is_healthy: bool = True
    last_used: float = 0.0
    last_error: Optional[str] = None
    error_count: int = 0
    success_count: int = 0
    cooldown_until: float = 0.0  # 冷却结束时间
    
    @property
    def masked_key(self) -> str:
        """返回脱敏的API Key"""
        if len(self.key) > 8:
            return f"{self.key[:4]}...{self.key[-4:]}"
        return "****"


class APIPoolManager:
    """
    API池轮询管理器
    
    支持多个DeepSeek API Key轮询，提高可用性。
    当一个Key失败时自动切换到下一个。
    """
    
    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        cooldown_seconds: float = 60.0,  # 失败后冷却时间
        max_errors_before_cooldown: int = 2  # 连续失败多少次后进入冷却
    ):
        """
        初始化API池管理器
        
        Args:
            api_keys: API Key列表，如果为None则从环境变量读取
            base_url: API基础URL
            model: 模型名称
            cooldown_seconds: 失败后冷却时间（秒）
            max_errors_before_cooldown: 连续失败多少次后进入冷却
        """
        self.base_url = base_url
        self.model = model
        self.cooldown_seconds = cooldown_seconds
        self.max_errors_before_cooldown = max_errors_before_cooldown
        
        # 从环境变量或参数获取API Keys
        if api_keys:
            self.api_keys = api_keys
        else:
            self.api_keys = self._load_api_keys_from_env()
        
        # 初始化Key状态
        self.key_statuses: List[APIKeyStatus] = [
            APIKeyStatus(key=key) for key in self.api_keys
        ]
        
        # 当前使用的Key索引
        self.current_index = 0
        
        # 统计信息
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "key_switches": 0
        }
        
        logger.info(
            f"API池管理器初始化: "
            f"keys_count={len(self.api_keys)}, "
            f"cooldown={cooldown_seconds}s, "
            f"max_errors={max_errors_before_cooldown}"
        )
    
    def _load_api_keys_from_env(self) -> List[str]:
        """从环境变量加载API Keys"""
        keys = []
        
        # 主Key
        main_key = os.getenv("DEEPSEEK_API_KEY", "")
        if main_key:
            keys.append(main_key)
        
        # 备用Keys（DEEPSEEK_API_KEY_2, DEEPSEEK_API_KEY_3, ... DEEPSEEK_API_KEY_10）
        for i in range(2, 11):  # 支持最多10个Key
            backup_key = os.getenv(f"DEEPSEEK_API_KEY_{i}", "")
            if backup_key:
                keys.append(backup_key)
        
        # 也支持逗号分隔的格式：DEEPSEEK_API_KEYS=key1,key2,key3
        keys_str = os.getenv("DEEPSEEK_API_KEYS", "")
        if keys_str:
            for key in keys_str.split(","):
                key = key.strip()
                if key and key not in keys:
                    keys.append(key)
        
        if not keys:
            logger.warning("未找到任何DeepSeek API Key，请配置DEEPSEEK_API_KEY环境变量")
        else:
            logger.info(f"已加载 {len(keys)} 个DeepSeek API Key")
        
        return keys
    
    def get_available_key(self) -> Optional[APIKeyStatus]:
        """
        获取一个可用的API Key
        
        Returns:
            APIKeyStatus: 可用的Key状态，如果没有可用的返回None
        """
        current_time = time.time()
        
        # 尝试从当前索引开始找一个可用的Key
        for _ in range(len(self.key_statuses)):
            status = self.key_statuses[self.current_index]
            
            # 检查是否在冷却中
            if status.cooldown_until > current_time:
                logger.debug(
                    f"Key {status.masked_key} 在冷却中，"
                    f"剩余 {status.cooldown_until - current_time:.0f}s"
                )
                self._rotate_index()
                continue
            
            # 检查是否健康
            if status.is_healthy:
                return status
            
            # 不健康但冷却结束，重置状态尝试使用
            if not status.is_healthy and status.cooldown_until <= current_time:
                status.is_healthy = True
                status.error_count = 0
                logger.info(f"Key {status.masked_key} 冷却结束，重新启用")
                return status
            
            self._rotate_index()
        
        # 所有Key都不可用，返回第一个（强制使用）
        logger.warning("所有API Key都不可用，强制使用第一个")
        return self.key_statuses[0] if self.key_statuses else None
    
    def _rotate_index(self):
        """轮转到下一个Key"""
        self.current_index = (self.current_index + 1) % len(self.key_statuses)
        self.stats["key_switches"] += 1
    
    def mark_success(self, status: APIKeyStatus):
        """标记Key调用成功"""
        status.success_count += 1
        status.error_count = 0
        status.is_healthy = True
        status.last_used = time.time()
        status.last_error = None
        self.stats["successful_calls"] += 1
        self.stats["total_calls"] += 1
    
    def mark_failure(self, status: APIKeyStatus, error: str):
        """标记Key调用失败"""
        status.error_count += 1
        status.last_error = error
        status.last_used = time.time()
        self.stats["failed_calls"] += 1
        self.stats["total_calls"] += 1
        
        # 连续失败超过阈值，进入冷却
        if status.error_count >= self.max_errors_before_cooldown:
            status.is_healthy = False
            status.cooldown_until = time.time() + self.cooldown_seconds
            logger.warning(
                f"Key {status.masked_key} 连续失败{status.error_count}次，"
                f"进入冷却{self.cooldown_seconds}s"
            )
            self._rotate_index()
    
    async def call_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        timeout: float = 180.0
    ) -> AsyncIterator[str]:
        """
        使用API池进行流式调用
        
        Args:
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度
            timeout: 超时时间
        
        Yields:
            str: 流式文本片段
        """
        # 尝试所有可用的Key
        tried_keys = set()
        last_error = None
        
        while len(tried_keys) < len(self.key_statuses):
            status = self.get_available_key()
            if status is None:
                break
            
            if status.key in tried_keys:
                # 已经尝试过这个Key，跳过
                self._rotate_index()
                continue
            
            tried_keys.add(status.key)
            
            try:
                logger.info(f"使用API Key: {status.masked_key}")
                
                async for chunk in self._call_deepseek_stream(
                    api_key=status.key,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout
                ):
                    yield chunk
                
                # 成功完成
                self.mark_success(status)
                return
            
            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(
                    f"API Key {status.masked_key} 调用失败: {error_msg[:100]}"
                )
                self.mark_failure(status, error_msg)
                
                # 继续尝试下一个Key
                continue
        
        # 所有Key都失败
        error_msg = f"所有API Key都失败（尝试{len(tried_keys)}个）: {str(last_error)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    async def _call_deepseek_stream(
        self,
        api_key: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        timeout: float
    ) -> AsyncIterator[str]:
        """实际的DeepSeek流式调用"""
        timeout_config = httpx.Timeout(
            connect=10.0,
            read=timeout,
            write=10.0,
            pool=5.0
        )
        
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        
                        if data == "[DONE]":
                            return
                        
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"]
                            
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
    
    async def call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        timeout: float = 120.0
    ) -> str:
        """
        使用API池进行非流式调用
        
        Args:
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度
            timeout: 超时时间
        
        Returns:
            str: 完整响应文本
        """
        tried_keys = set()
        last_error = None
        
        while len(tried_keys) < len(self.key_statuses):
            status = self.get_available_key()
            if status is None:
                break
            
            if status.key in tried_keys:
                self._rotate_index()
                continue
            
            tried_keys.add(status.key)
            
            try:
                logger.info(f"使用API Key: {status.masked_key}")
                
                result = await self._call_deepseek(
                    api_key=status.key,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout
                )
                
                self.mark_success(status)
                return result
            
            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(
                    f"API Key {status.masked_key} 调用失败: {error_msg[:100]}"
                )
                self.mark_failure(status, error_msg)
                continue
        
        error_msg = f"所有API Key都失败（尝试{len(tried_keys)}个）: {str(last_error)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    async def _call_deepseek(
        self,
        api_key: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        timeout: float
    ) -> str:
        """实际的DeepSeek非流式调用"""
        timeout_config = httpx.Timeout(
            connect=10.0,
            read=timeout,
            write=10.0,
            pool=5.0
        )
        
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result["choices"][0]["message"]["content"]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "keys_count": len(self.key_statuses),
            "healthy_keys": sum(1 for s in self.key_statuses if s.is_healthy),
            "keys_status": [
                {
                    "key": s.masked_key,
                    "is_healthy": s.is_healthy,
                    "error_count": s.error_count,
                    "success_count": s.success_count,
                    "in_cooldown": s.cooldown_until > time.time()
                }
                for s in self.key_statuses
            ]
        }


# 全局单例
_api_pool_manager: Optional[APIPoolManager] = None


def get_api_pool_manager() -> APIPoolManager:
    """获取API池管理器单例"""
    global _api_pool_manager
    if _api_pool_manager is None:
        _api_pool_manager = APIPoolManager()
    return _api_pool_manager


def reset_api_pool_manager():
    """重置API池管理器（用于测试）"""
    global _api_pool_manager
    _api_pool_manager = None
