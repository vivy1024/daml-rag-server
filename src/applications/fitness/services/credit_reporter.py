# -*- coding: utf-8 -*-
"""
积分消耗上报服务

负责计算积分消耗并上报到后端API，用于积分体系的Token消耗记录。

版本: v1.0.0
创建日期: 2026-02-05
Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import os
import math
import asyncio
import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class CreditReporter:
    """
    积分消耗上报服务
    
    功能：
    1. 计算Token消耗对应的积分
    2. 异步上报积分消耗到后端API
    3. 支持DAG模式和Agent模式的不同倍率
    4. 错误处理：记录日志但不阻塞响应
    
    积分计算规则：
    - 1积分 = 1000 tokens
    - DAG模式：1.0x 倍率
    - Agent模式：1.5x 倍率
    - 最小消耗：1积分
    - 向上取整
    """
    
    # 积分计算常量
    TOKENS_PER_CREDIT = 1000
    AGENT_MULTIPLIER = 1.5
    DAG_MULTIPLIER = 1.0
    
    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 5.0
    
    def __init__(
        self,
        backend_url: Optional[str] = None,
        internal_token: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        enabled: bool = True
    ):
        """
        初始化积分上报服务
        
        Args:
            backend_url: 后端API基础URL，默认从环境变量BACKEND_API_URL读取
            internal_token: 内部API认证Token，默认从环境变量INTERNAL_API_TOKEN读取
            timeout: HTTP请求超时时间（秒）
            enabled: 是否启用积分上报，默认True
        """
        # 优先使用BACKEND_INTERNAL_URL，回退到BACKEND_API_URL
        self.backend_url = backend_url or os.getenv(
            "BACKEND_INTERNAL_URL", 
            os.getenv("BACKEND_API_URL", "http://host.docker.internal:8000")
        )
        self.internal_token = internal_token or os.getenv("INTERNAL_API_TOKEN", "")
        self.timeout = timeout
        self.enabled = enabled and os.getenv("CREDIT_REPORT_ENABLED", "true").lower() == "true"
        
        # 统计信息
        self._report_count = 0
        self._error_count = 0

        # 幂等性：conversation_id 去重缓存（最多保留1000条）
        self._reported_conversations: set = set()
        self._max_dedup_cache = 1000
        
        if self.enabled:
            logger.info(f"积分上报服务初始化完成: backend_url={self.backend_url}")
        else:
            logger.info("积分上报服务已禁用")
    
    def calculate_credits(self, tokens: int, mode: str) -> int:
        """
        计算积分消耗
        
        根据Token数量和查询模式计算应消耗的积分数。
        
        Args:
            tokens: Token消耗数量
            mode: 查询模式，'dag' 或 'agent'
        
        Returns:
            int: 应消耗的积分数（最小为1）
        
        计算公式：
            credits = ceil(tokens × multiplier / 1000)
            - DAG模式：multiplier = 1.0
            - Agent模式：multiplier = 1.5
        
        Examples:
            >>> reporter = CreditReporter()
            >>> reporter.calculate_credits(500, 'dag')
            1
            >>> reporter.calculate_credits(1000, 'dag')
            1
            >>> reporter.calculate_credits(1001, 'dag')
            2
            >>> reporter.calculate_credits(1000, 'agent')
            2
        """
        # 确定倍率
        multiplier = self.AGENT_MULTIPLIER if mode == 'agent' else self.DAG_MULTIPLIER
        
        # 计算积分（向上取整）
        credits = math.ceil((tokens * multiplier) / self.TOKENS_PER_CREDIT)
        
        # 最小消耗1积分
        return max(1, credits)
    
    async def report_consumption(
        self,
        user_id: int,
        tokens: int,
        mode: str,
        template_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        backend_used: str = "unknown"
    ) -> Dict[str, Any]:
        """
        上报积分消耗到后端

        Args:
            user_id: 用户ID
            tokens: 总Token消耗数量
            mode: 查询模式，'dag' 或 'agent'
            template_name: DAG模板名称（可选）
            conversation_id: 会话ID（可选，用于幂等性去重）
            input_tokens: 输入Token数量
            output_tokens: 输出Token数量
            backend_used: 实际使用的LLM后端（anthropic/deepseek/template）

        Returns:
            dict: 上报结果
        """
        # 检查是否启用
        if not self.enabled:
            logger.debug("积分上报已禁用，跳过上报")
            return {"success": True, "credits": 0, "skipped": True}

        # 幂等性检查：同一 conversation_id 不重复上报
        if conversation_id and conversation_id in self._reported_conversations:
            logger.info(f"积分上报跳过(已上报): conversation_id={conversation_id}")
            return {"success": True, "credits": 0, "deduplicated": True}

        # 计算积分
        credits = self.calculate_credits(tokens, mode)

        # 构建请求数据
        payload = {
            "user_id": user_id,
            "tokens": tokens,
            "credits": credits,
            "mode": mode,
            "template_name": template_name,
            "conversation_id": conversation_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "backend_used": backend_used,
        }

        self._report_count += 1

        # 重试逻辑（3次指数退避）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.backend_url}/api/internal/credits/record",
                        json=payload,
                        headers={
                            "X-Internal-Token": self.internal_token,
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                        timeout=self.timeout
                    )

                    if response.status_code == 200:
                        result = response.json()
                        # 记录已上报的 conversation_id
                        if conversation_id:
                            if len(self._reported_conversations) >= self._max_dedup_cache:
                                self._reported_conversations.clear()
                            self._reported_conversations.add(conversation_id)
                        logger.info(
                            f"积分上报成功: user_id={user_id}, credits={credits}, "
                            f"tokens={tokens}, mode={mode}, backend={backend_used}"
                        )
                        return {
                            "success": True,
                            "credits": credits,
                            "data": result.get("data", {})
                        }
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        if attempt < max_retries - 1:
                            delay = 1.0 * (2 ** attempt)
                            logger.warning(f"积分上报失败(重试{attempt+1}/{max_retries}): {error_msg}")
                            await asyncio.sleep(delay)
                            continue
                        logger.error(f"积分上报最终失败: {error_msg}")
                        self._error_count += 1
                        return {"success": False, "error": error_msg, "credits": credits}

            except (httpx.TimeoutException, httpx.RequestError) as e:
                error_msg = f"{type(e).__name__}: {e}"
                if attempt < max_retries - 1:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(f"积分上报失败(重试{attempt+1}/{max_retries}): {error_msg}")
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"积分上报最终失败: {error_msg}")
                self._error_count += 1
                return {"success": False, "error": error_msg, "credits": credits}

            except Exception as e:
                error_msg = f"未知错误: {e}"
                logger.error(f"积分上报失败: {error_msg}")
                self._error_count += 1
                return {"success": False, "error": error_msg, "credits": credits}

        return {"success": False, "error": "重试耗尽", "credits": credits}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取上报统计信息
        
        Returns:
            dict: 统计信息
                - report_count: 总上报次数
                - error_count: 错误次数
                - error_rate: 错误率
                - enabled: 是否启用
        """
        return {
            "report_count": self._report_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._report_count, 1),
            "enabled": self.enabled,
            "backend_url": self.backend_url,
        }


# 单例实例
_credit_reporter: Optional[CreditReporter] = None


def get_credit_reporter() -> CreditReporter:
    """
    获取积分上报服务单例
    
    Returns:
        CreditReporter: 积分上报服务实例
    """
    global _credit_reporter
    if _credit_reporter is None:
        _credit_reporter = CreditReporter()
    return _credit_reporter


def reset_credit_reporter() -> None:
    """
    重置积分上报服务单例（主要用于测试）
    """
    global _credit_reporter
    _credit_reporter = None


# 便捷函数
async def report_credit_consumption(
    user_id: int,
    tokens: int,
    mode: str,
    template_name: Optional[str] = None,
    conversation_id: Optional[str] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    backend_used: str = "unknown"
) -> Dict[str, Any]:
    """
    便捷函数：上报积分消耗

    Args:
        user_id: 用户ID
        tokens: 总Token消耗数量
        mode: 查询模式，'dag' 或 'agent'
        template_name: DAG模板名称（可选）
        conversation_id: 会话ID（可选）
        input_tokens: 输入Token数量（可选）
        output_tokens: 输出Token数量（可选）
        backend_used: 实际使用的LLM后端（可选）

    Returns:
        dict: 上报结果
    """
    reporter = get_credit_reporter()
    return await reporter.report_consumption(
        user_id=user_id,
        tokens=tokens,
        mode=mode,
        template_name=template_name,
        conversation_id=conversation_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        backend_used=backend_used,
    )
