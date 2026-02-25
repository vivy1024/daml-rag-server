# -*- coding: utf-8 -*-
"""
UsageReporter - 异步用量上报客户端

DAML-RAG完成AI查询后，异步向PHP后端上报用量。
失败时写入内存重试队列（最多3次，指数退避）。

Requirements: 4.3, 4.4
版本: v1.0.0
日期: 2026-02-12
"""

import asyncio
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class UsageReportTask:
    """用量上报任务"""
    user_id: int
    mode: str
    session_id: str
    timestamp: str
    execution_time_ms: int = 0
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[float] = None


class UsageReporter:
    """
    异步用量上报，带重试队列

    上报失败时写入内存队列，后台任务定时重试。
    重试耗尽后写入 fallback JSONL 日志，防止数据丢失。
    """

    FALLBACK_LOG = "/app/logs/credit_fallback.jsonl"

    def __init__(
        self,
        backend_url: str,
        internal_token: str = "",
        timeout: float = 5.0,
        max_queue_size: int = 1000,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.internal_token = internal_token
        self.timeout = timeout
        self.max_queue_size = max_queue_size
        self._retry_queue: deque[UsageReportTask] = deque(maxlen=max_queue_size)

    async def report_usage(
        self,
        user_id: int,
        mode: str,
        session_id: str,
        execution_time_ms: int = 0,
    ) -> bool:
        """
        上报用量到PHP后端
        
        Args:
            user_id: 用户ID
            mode: 查询模式 (dag|agent)
            session_id: 会话ID
            execution_time_ms: 执行时间（毫秒）
            
        Returns:
            是否上报成功
        """
        task = UsageReportTask(
            user_id=user_id,
            mode=mode,
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            execution_time_ms=execution_time_ms,
        )
        return await self._send_report(task)

    async def _send_report(self, task: UsageReportTask) -> bool:
        """发送上报请求"""
        url = f"{self.backend_url}/api/internal/usage/report"
        payload = {
            "user_id": task.user_id,
            "mode": task.mode,
            "session_id": task.session_id,
            "timestamp": task.timestamp,
            "execution_time_ms": task.execution_time_ms,
        }
        headers = {}
        if self.internal_token:
            headers["X-Internal-Token"] = self.internal_token

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code == 200:
                logger.info(
                    f"用量上报成功: user_id={task.user_id}, mode={task.mode}"
                )
                return True
            else:
                logger.warning(
                    f"用量上报失败(HTTP {resp.status_code}): "
                    f"user_id={task.user_id}, body={resp.text[:200]}"
                )
                self._enqueue_retry(task)
                return False

        except Exception as e:
            logger.warning(
                f"用量上报异常: user_id={task.user_id}, error={e}"
            )
            self._enqueue_retry(task)
            return False

    def _enqueue_retry(self, task: UsageReportTask) -> None:
        """将失败任务加入重试队列"""
        if task.retry_count >= task.max_retries:
            logger.error(
                f"用量上报重试次数已达上限，写入fallback日志: "
                f"user_id={task.user_id}, session_id={task.session_id}"
            )
            self._write_fallback(task)
            return

        task.retry_count += 1
        # 指数退避: 2^retry_count 秒
        delay = 2 ** task.retry_count
        task.next_retry_at = time.time() + delay

        self._retry_queue.append(task)
        logger.info(
            f"用量上报已加入重试队列: user_id={task.user_id}, "
            f"retry={task.retry_count}/{task.max_retries}, "
            f"next_retry_in={delay}s"
        )

    def _write_fallback(self, task: UsageReportTask) -> None:
        """重试耗尽后写入 fallback JSONL 日志（最后防线）"""
        record = {
            "user_id": task.user_id,
            "mode": task.mode,
            "session_id": task.session_id,
            "timestamp": task.timestamp,
            "execution_time_ms": task.execution_time_ms,
            "failed_at": datetime.utcnow().isoformat() + "Z",
            "retry_count": task.retry_count,
        }
        try:
            os.makedirs(os.path.dirname(self.FALLBACK_LOG), exist_ok=True)
            with open(self.FALLBACK_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            logger.warning(
                f"用量上报已写入fallback日志: user_id={task.user_id}, "
                f"session_id={task.session_id}"
            )
        except Exception as e:
            logger.critical(
                f"fallback日志写入失败(数据可能丢失): "
                f"user_id={task.user_id}, session_id={task.session_id}, "
                f"error={e}"
            )

    async def retry_failed(self) -> int:
        """
        重试失败的上报任务
        
        Returns:
            成功重试的数量
        """
        now = time.time()
        success_count = 0
        remaining: list[UsageReportTask] = []

        while self._retry_queue:
            task = self._retry_queue.popleft()
            if task.next_retry_at and task.next_retry_at > now:
                remaining.append(task)
                continue

            ok = await self._send_report(task)
            if ok:
                success_count += 1

        # 把还没到重试时间的任务放回队列
        for task in remaining:
            self._retry_queue.append(task)

        if success_count > 0:
            logger.info(f"重试成功: {success_count}个任务")

        return success_count

    @property
    def pending_count(self) -> int:
        """重试队列中的待处理任务数"""
        return len(self._retry_queue)

    def get_pending_tasks(self) -> list[UsageReportTask]:
        """获取重试队列中的所有任务（只读）"""
        return list(self._retry_queue)


__all__ = ["UsageReporter", "UsageReportTask"]
