# -*- coding: utf-8 -*-
"""
DAG重试处理器 - DAG编排层组件

提供工具执行的重试机制，支持超时配置、指数退避和降级策略。

核心功能：
1. 超时配置
2. 指数退避重试
3. 降级工具调用
4. 重试统计

版本: v1.0.0
日期: 2026-01-05
作者: BUILD_BODY Team
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 指数退避
    LINEAR_BACKOFF = "linear_backoff"            # 线性退避
    FIXED_DELAY = "fixed_delay"                  # 固定延迟
    IMMEDIATE = "immediate"                      # 立即重试


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 2                        # 最大重试次数
    timeout_seconds: float = 5.0                # 超时时间（秒）
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0                     # 基础延迟（秒）
    max_delay: float = 10.0                     # 最大延迟（秒）
    fallback_tool: Optional[str] = None         # 降级工具名称
    retry_on_timeout: bool = True               # 超时时是否重试
    retry_on_error: bool = True                 # 错误时是否重试
    
    def __post_init__(self):
        """验证配置"""
        if self.max_retries < 0:
            raise ValueError("max_retries 必须 >= 0")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds 必须 > 0")
        if self.base_delay < 0:
            raise ValueError("base_delay 必须 >= 0")


@dataclass
class RetryResult:
    """重试结果"""
    success: bool = False
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0
    total_time: float = 0.0
    used_fallback: bool = False
    retry_history: List[Dict[str, Any]] = field(default_factory=list)


class DAGRetryHandler:
    """
    DAG重试处理器
    
    提供工具执行的重试机制，支持：
    - 超时配置
    - 指数退避重试
    - 降级工具调用
    - 重试统计
    """
    
    # 默认配置
    DEFAULT_TIMEOUT = 5.0  # 秒
    DEFAULT_MAX_RETRIES = 2
    DEFAULT_BACKOFF_BASE = 1.0  # 秒
    
    def __init__(self):
        """初始化重试处理器"""
        self.retry_statistics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_retries": 0,
            "timeout_count": 0,
            "fallback_count": 0
        }
        logger.info("✅ DAG重试处理器初始化完成")
    
    async def execute_with_retry(
        self,
        tool_func: Callable,
        tool_name: str,
        params: Dict[str, Any],
        config: Optional[RetryConfig] = None
    ) -> RetryResult:
        """
        带重试的工具执行
        
        Args:
            tool_func: 工具执行函数
            tool_name: 工具名称
            params: 工具参数
            config: 重试配置（可选）
        
        Returns:
            RetryResult: 执行结果
        """
        # 使用默认配置
        if config is None:
            config = RetryConfig()
        
        start_time = time.time()
        self.retry_statistics["total_executions"] += 1
        
        retry_result = RetryResult()
        
        # 执行重试循环
        for attempt in range(config.max_retries + 1):
            try:
                logger.debug(
                    f"🔄 执行工具: {tool_name} | "
                    f"尝试: {attempt + 1}/{config.max_retries + 1} | "
                    f"超时: {config.timeout_seconds}s"
                )
                
                # 执行工具（带超时）
                result = await asyncio.wait_for(
                    tool_func(tool_name, params),
                    timeout=config.timeout_seconds
                )
                
                # 成功
                retry_result.success = True
                retry_result.result = result
                retry_result.attempts = attempt + 1
                retry_result.total_time = time.time() - start_time
                
                self.retry_statistics["successful_executions"] += 1
                if attempt > 0:
                    self.retry_statistics["total_retries"] += attempt
                
                logger.info(
                    f"✅ 工具执行成功: {tool_name} | "
                    f"尝试次数: {attempt + 1} | "
                    f"耗时: {retry_result.total_time:.2f}s"
                )
                
                return retry_result
                
            except asyncio.TimeoutError:
                # 超时
                self.retry_statistics["timeout_count"] += 1
                
                retry_result.retry_history.append({
                    "attempt": attempt + 1,
                    "error_type": "timeout",
                    "error_message": f"执行超时（{config.timeout_seconds}s）",
                    "timestamp": time.time()
                })
                
                logger.warning(
                    f"⏱️ 工具执行超时: {tool_name} | "
                    f"尝试: {attempt + 1}/{config.max_retries + 1} | "
                    f"超时: {config.timeout_seconds}s"
                )
                
                # 判断是否继续重试
                if attempt < config.max_retries and config.retry_on_timeout:
                    wait_time = self._calculate_backoff(attempt, config)
                    logger.info(f"⏳ 等待 {wait_time:.1f}s 后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # 达到最大重试次数或不允许重试
                    break
                    
            except Exception as e:
                # 其他错误
                retry_result.retry_history.append({
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": time.time()
                })
                
                logger.warning(
                    f"❌ 工具执行失败: {tool_name} | "
                    f"尝试: {attempt + 1}/{config.max_retries + 1} | "
                    f"错误: {e}"
                )
                
                # 判断是否继续重试
                if attempt < config.max_retries and config.retry_on_error:
                    wait_time = self._calculate_backoff(attempt, config)
                    logger.info(f"⏳ 等待 {wait_time:.1f}s 后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # 达到最大重试次数或不允许重试
                    retry_result.error = str(e)
                    break
        
        # 所有重试都失败，尝试降级
        if config.fallback_tool:
            logger.info(f"🔄 尝试降级工具: {config.fallback_tool}")
            fallback_result = await self._execute_fallback(
                tool_func,
                config.fallback_tool,
                params,
                config
            )
            
            if fallback_result.success:
                retry_result.success = True
                retry_result.result = fallback_result.result
                retry_result.used_fallback = True
                retry_result.attempts += fallback_result.attempts
                retry_result.total_time = time.time() - start_time
                
                self.retry_statistics["fallback_count"] += 1
                self.retry_statistics["successful_executions"] += 1
                
                logger.info(f"✅ 降级工具执行成功: {config.fallback_tool}")
                return retry_result
        
        # 最终失败
        retry_result.success = False
        retry_result.attempts = config.max_retries + 1
        retry_result.total_time = time.time() - start_time
        
        self.retry_statistics["failed_executions"] += 1
        self.retry_statistics["total_retries"] += config.max_retries
        
        logger.error(
            f"❌ 工具执行最终失败: {tool_name} | "
            f"尝试次数: {retry_result.attempts} | "
            f"耗时: {retry_result.total_time:.2f}s"
        )
        
        return retry_result
    
    async def _execute_fallback(
        self,
        tool_func: Callable,
        fallback_tool: str,
        params: Dict[str, Any],
        config: RetryConfig
    ) -> RetryResult:
        """
        执行降级工具
        
        Args:
            tool_func: 工具执行函数
            fallback_tool: 降级工具名称
            params: 工具参数
            config: 重试配置
        
        Returns:
            RetryResult: 执行结果
        """
        try:
            logger.debug(f"🔄 执行降级工具: {fallback_tool}")
            
            result = await asyncio.wait_for(
                tool_func(fallback_tool, params),
                timeout=config.timeout_seconds
            )
            
            return RetryResult(
                success=True,
                result=result,
                attempts=1,
                total_time=0.0,  # 由外层计算
                used_fallback=True
            )
            
        except Exception as e:
            logger.error(f"❌ 降级工具执行失败: {fallback_tool}, 错误: {e}")
            return RetryResult(
                success=False,
                error=str(e),
                attempts=1,
                used_fallback=True
            )
    
    def _calculate_backoff(self, attempt: int, config: RetryConfig) -> float:
        """
        计算退避时间
        
        Args:
            attempt: 当前尝试次数（从0开始）
            config: 重试配置
        
        Returns:
            float: 等待时间（秒）
        """
        if config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            # 指数退避: base_delay * (2 ** attempt)
            delay = config.base_delay * (2 ** attempt)
        
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            # 线性退避: base_delay * (attempt + 1)
            delay = config.base_delay * (attempt + 1)
        
        elif config.strategy == RetryStrategy.FIXED_DELAY:
            # 固定延迟
            delay = config.base_delay
        
        elif config.strategy == RetryStrategy.IMMEDIATE:
            # 立即重试
            delay = 0.0
        
        else:
            # 默认指数退避
            delay = config.base_delay * (2 ** attempt)
        
        # 限制最大延迟
        return min(delay, config.max_delay)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取重试统计信息
        
        Returns:
            Dict: 统计信息
        """
        total = self.retry_statistics["total_executions"]
        
        return {
            **self.retry_statistics,
            "success_rate": (
                self.retry_statistics["successful_executions"] / total
                if total > 0 else 0.0
            ),
            "average_retries": (
                self.retry_statistics["total_retries"] / total
                if total > 0 else 0.0
            ),
            "timeout_rate": (
                self.retry_statistics["timeout_count"] / total
                if total > 0 else 0.0
            ),
            "fallback_rate": (
                self.retry_statistics["fallback_count"] / total
                if total > 0 else 0.0
            )
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.retry_statistics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_retries": 0,
            "timeout_count": 0,
            "fallback_count": 0
        }
        logger.info("✅ 重试统计信息已重置")


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建重试处理器
    handler = DAGRetryHandler()
    
    # 模拟工具函数
    async def mock_tool_func(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """模拟工具执行"""
        # 模拟随机失败
        import random
        if random.random() < 0.5:
            raise Exception("模拟错误")
        
        return {
            "tool": tool_name,
            "status": "success",
            "data": params
        }
    
    # 测试用例1: 基本重试
    async def test_basic_retry():
        print("\n=== 测试1: 基本重试 ===")
        
        config = RetryConfig(
            max_retries=2,
            timeout_seconds=2.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
        
        result = await handler.execute_with_retry(
            mock_tool_func,
            "test_tool",
            {"param1": "value1"},
            config
        )
        
        print(f"成功: {result.success}")
        print(f"尝试次数: {result.attempts}")
        print(f"总耗时: {result.total_time:.2f}s")
        print(f"重试历史: {len(result.retry_history)}条")
    
    # 测试用例2: 降级工具
    async def test_fallback():
        print("\n=== 测试2: 降级工具 ===")
        
        async def always_fail_tool(tool_name: str, params: Dict[str, Any]):
            raise Exception("总是失败")
        
        async def fallback_tool(tool_name: str, params: Dict[str, Any]):
            return {"tool": tool_name, "status": "fallback_success"}
        
        # 使用混合函数
        async def mixed_tool(tool_name: str, params: Dict[str, Any]):
            if tool_name == "fallback_tool":
                return await fallback_tool(tool_name, params)
            else:
                return await always_fail_tool(tool_name, params)
        
        config = RetryConfig(
            max_retries=1,
            timeout_seconds=2.0,
            fallback_tool="fallback_tool"
        )
        
        result = await handler.execute_with_retry(
            mixed_tool,
            "main_tool",
            {"param1": "value1"},
            config
        )
        
        print(f"成功: {result.success}")
        print(f"使用降级: {result.used_fallback}")
        print(f"结果: {result.result}")
    
    # 运行测试
    async def main():
        await test_basic_retry()
        await test_fallback()
        
        # 查看统计
        print("\n=== 重试统计 ===")
        stats = handler.get_statistics()
        for key, value in stats.items():
            print(f"{key}: {value}")
    
    # 执行
    asyncio.run(main())
