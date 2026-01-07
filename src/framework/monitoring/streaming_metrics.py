# -*- coding: utf-8 -*-
"""
流式会话监控指标 - Streaming Session Metrics

提供Prometheus指标和StreamingMonitor类用于监控流式会话的性能。

核心指标：
1. streaming_session_ttfb_seconds: 首字节响应时间（TTFB）
2. streaming_session_duration_seconds: 会话持续时间
3. streaming_session_tokens_per_second: 令牌生成速率
4. streaming_session_success_total: 成功会话计数
5. streaming_session_failure_total: 失败会话计数

StreamingMonitor类：
- 线程安全的活跃连接数跟踪
- 会话指标记录和存储
- 统计数据聚合
- 最近会话查询

版本: v1.1.0
日期: 2025-12-27
"""

import logging
import threading
import time
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)


# ========== Prometheus指标定义 ==========

# TTFB直方图（首字节响应时间）
streaming_ttfb = Histogram(
    'streaming_session_ttfb_seconds',
    'Time to first byte for streaming sessions',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
)

# 会话持续时间直方图
streaming_duration = Histogram(
    'streaming_session_duration_seconds',
    'Total duration of streaming sessions',
    buckets=[1, 5, 10, 30, 60, 120, 180, 300]
)

# 令牌生成速率直方图
streaming_tokens_per_second = Histogram(
    'streaming_session_tokens_per_second',
    'Tokens generated per second in streaming sessions',
    buckets=[1, 5, 10, 20, 50, 100, 200]
)

# 成功计数器
streaming_success = Counter(
    'streaming_session_success_total',
    'Total successful streaming sessions'
)

# 失败计数器
streaming_failure = Counter(
    'streaming_session_failure_total',
    'Total failed streaming sessions'
)

# 活跃连接数Gauge
streaming_active_connections = Gauge(
    'streaming_active_connections',
    'Current number of active streaming connections'
)


# ========== 数据类定义 ==========

@dataclass
class StreamingSessionMetrics:
    """
    流式会话指标数据类
    
    记录单个流式会话的完整性能指标。
    """
    session_id: str
    user_id: str
    start_time: float
    first_byte_time: Optional[float] = None
    end_time: Optional[float] = None
    total_tokens: int = 0
    success: bool = False
    error_message: Optional[str] = None
    
    @property
    def ttfb(self) -> Optional[float]:
        """
        Time To First Byte（秒）
        
        Returns:
            Optional[float]: TTFB时间，如果未记录首字节时间则返回None
        """
        if self.first_byte_time:
            return self.first_byte_time - self.start_time
        return None
    
    @property
    def duration(self) -> Optional[float]:
        """
        总持续时间（秒）
        
        Returns:
            Optional[float]: 会话持续时间，如果未完成则返回None
        """
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def tokens_per_second(self) -> float:
        """
        令牌生成速率（tokens/秒）
        
        Returns:
            float: 令牌生成速率，如果持续时间为0则返回0
        """
        if self.duration and self.duration > 0:
            return self.total_tokens / self.duration
        return 0.0


# ========== 辅助函数 ==========

def record_streaming_metrics(metrics: StreamingSessionMetrics):
    """
    记录流式会话指标到Prometheus
    
    Args:
        metrics: 流式会话指标数据
    """
    try:
        # 记录TTFB
        if metrics.ttfb is not None:
            streaming_ttfb.observe(metrics.ttfb)
            logger.debug(f"📊 记录TTFB: {metrics.ttfb:.2f}s, session={metrics.session_id[:8]}...")
        
        # 记录持续时间
        if metrics.duration is not None:
            streaming_duration.observe(metrics.duration)
            logger.debug(f"📊 记录持续时间: {metrics.duration:.2f}s, session={metrics.session_id[:8]}...")
        
        # 记录令牌速率
        if metrics.tokens_per_second > 0:
            streaming_tokens_per_second.observe(metrics.tokens_per_second)
            logger.debug(f"📊 记录令牌速率: {metrics.tokens_per_second:.1f} tokens/s, session={metrics.session_id[:8]}...")
        
        # 记录成功/失败
        if metrics.success:
            streaming_success.inc()
            logger.debug(f"✅ 记录成功会话: session={metrics.session_id[:8]}...")
        else:
            streaming_failure.inc()
            logger.debug(f"❌ 记录失败会话: session={metrics.session_id[:8]}..., error={metrics.error_message}")
            
    except Exception as e:
        # 静默失败，不影响主业务
        logger.warning(f"⚠️ Prometheus指标记录失败: {e}, session={metrics.session_id[:8]}...")


# ========== StreamingMonitor类 ==========

@dataclass
class StreamingSessionRecord:
    """
    流式会话记录数据类
    
    用于存储单个流式会话的完整记录。
    """
    user_id: str
    session_id: str
    request_id: str
    timestamp: float
    ttfb_ms: Optional[float] = None
    total_duration_ms: Optional[float] = None
    tokens_generated: int = 0
    content_length: int = 0
    structured_data_count: int = 0
    success: bool = True
    error_type: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "ttfb_ms": self.ttfb_ms,
            "total_duration_ms": self.total_duration_ms,
            "tokens_generated": self.tokens_generated,
            "content_length": self.content_length,
            "structured_data_count": self.structured_data_count,
            "success": self.success,
            "error_type": self.error_type,
            "retry_count": self.retry_count
        }


class StreamingMonitor:
    """
    流式会话监控器
    
    提供线程安全的流式会话监控功能，包括：
    - 活跃连接数跟踪
    - 会话指标记录
    - 统计数据聚合
    - 最近会话查询
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
    """
    
    def __init__(self, max_sessions: int = 1000):
        """
        初始化流式监控器
        
        Args:
            max_sessions: 最大存储的会话记录数，默认1000
        """
        self._active_connections: int = 0
        self._lock: threading.Lock = threading.Lock()
        self._sessions: List[StreamingSessionRecord] = []
        self._max_sessions: int = max_sessions
        logger.info(f"📊 StreamingMonitor初始化完成，最大会话记录数: {max_sessions}")
    
    def increment_active_connections(self) -> int:
        """
        增加活跃连接数
        
        线程安全地增加活跃连接计数器。
        
        Returns:
            int: 增加后的当前连接数
            
        Requirements: 1.1, 1.7
        """
        with self._lock:
            self._active_connections += 1
            current = self._active_connections
        
        # 更新Prometheus Gauge
        streaming_active_connections.set(current)
        logger.debug(f"📈 活跃连接数增加: {current}")
        return current
    
    def decrement_active_connections(self) -> int:
        """
        减少活跃连接数
        
        线程安全地减少活跃连接计数器，确保不会变为负数。
        
        Returns:
            int: 减少后的当前连接数
            
        Requirements: 1.2, 1.7
        """
        with self._lock:
            if self._active_connections > 0:
                self._active_connections -= 1
            current = self._active_connections
        
        # 更新Prometheus Gauge
        streaming_active_connections.set(current)
        logger.debug(f"📉 活跃连接数减少: {current}")
        return current
    
    @property
    def active_connections(self) -> int:
        """
        获取当前活跃连接数
        
        Returns:
            int: 当前活跃连接数
        """
        with self._lock:
            return self._active_connections
    
    def record_streaming_session(
        self,
        user_id: str,
        session_id: str,
        request_id: str = "",
        ttfb_ms: Optional[float] = None,
        total_duration_ms: Optional[float] = None,
        tokens_generated: int = 0,
        content_length: int = 0,
        structured_data_count: int = 0,
        success: bool = True,
        error_type: Optional[str] = None,
        retry_count: int = 0
    ) -> None:
        """
        记录流式会话指标
        
        记录单个流式会话的完整性能指标，同时更新Prometheus指标。
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            request_id: 请求ID
            ttfb_ms: 首字节响应时间（毫秒）
            total_duration_ms: 总持续时间（毫秒）
            tokens_generated: 生成的令牌数
            content_length: 内容长度
            structured_data_count: 结构化数据数量
            success: 是否成功
            error_type: 错误类型（如果失败）
            retry_count: 重试次数
            
        Requirements: 1.3, 1.7
        """
        try:
            # 创建会话记录
            record = StreamingSessionRecord(
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                timestamp=time.time(),
                ttfb_ms=ttfb_ms,
                total_duration_ms=total_duration_ms,
                tokens_generated=tokens_generated,
                content_length=content_length,
                structured_data_count=structured_data_count,
                success=success,
                error_type=error_type,
                retry_count=retry_count
            )
            
            # 线程安全地添加记录
            with self._lock:
                self._sessions.append(record)
                # 如果超过最大数量，移除最旧的记录
                if len(self._sessions) > self._max_sessions:
                    self._sessions = self._sessions[-self._max_sessions:]
            
            # 更新Prometheus指标
            if ttfb_ms is not None:
                streaming_ttfb.observe(ttfb_ms / 1000.0)  # 转换为秒
            
            if total_duration_ms is not None:
                streaming_duration.observe(total_duration_ms / 1000.0)  # 转换为秒
            
            if total_duration_ms and total_duration_ms > 0 and tokens_generated > 0:
                tokens_per_sec = tokens_generated / (total_duration_ms / 1000.0)
                streaming_tokens_per_second.observe(tokens_per_sec)
            
            if success:
                streaming_success.inc()
            else:
                streaming_failure.inc()
            
            logger.debug(
                f"📊 记录流式会话: session={session_id[:8] if session_id else 'N/A'}..., "
                f"success={success}, ttfb={ttfb_ms}ms, duration={total_duration_ms}ms"
            )
            
        except Exception as e:
            # 静默失败，不影响主业务
            logger.warning(f"⚠️ 记录流式会话失败: {e}")
    
    def get_statistics(self, time_window_seconds: int = 3600) -> Dict[str, Any]:
        """
        获取指定时间窗口内的统计数据
        
        Args:
            time_window_seconds: 时间窗口（秒），默认1小时
            
        Returns:
            Dict[str, Any]: 统计数据字典，包含：
                - total_sessions: 总会话数
                - successful_sessions: 成功会话数
                - failed_sessions: 失败会话数
                - success_rate: 成功率
                - avg_ttfb_ms: 平均TTFB（毫秒）
                - avg_duration_ms: 平均持续时间（毫秒）
                - avg_tokens_per_second: 平均令牌生成速率
                - active_connections: 当前活跃连接数
                - p50_ttfb_ms: TTFB P50
                - p95_ttfb_ms: TTFB P95
                - p99_ttfb_ms: TTFB P99
                - error_distribution: 错误分布
                
        Requirements: 1.4, 1.7
        """
        try:
            current_time = time.time()
            cutoff_time = current_time - time_window_seconds
            
            with self._lock:
                # 过滤时间窗口内的会话
                recent_sessions = [
                    s for s in self._sessions 
                    if s.timestamp >= cutoff_time
                ]
            
            if not recent_sessions:
                return {
                    "total_sessions": 0,
                    "successful_sessions": 0,
                    "failed_sessions": 0,
                    "success_rate": 0.0,
                    "avg_ttfb_ms": 0.0,
                    "avg_duration_ms": 0.0,
                    "avg_tokens_per_second": 0.0,
                    "active_connections": self.active_connections,
                    "p50_ttfb_ms": 0.0,
                    "p95_ttfb_ms": 0.0,
                    "p99_ttfb_ms": 0.0,
                    "error_distribution": {},
                    "time_window_seconds": time_window_seconds
                }
            
            # 计算统计数据
            total = len(recent_sessions)
            successful = sum(1 for s in recent_sessions if s.success)
            failed = total - successful
            
            # TTFB统计
            ttfb_values = [s.ttfb_ms for s in recent_sessions if s.ttfb_ms is not None]
            avg_ttfb = sum(ttfb_values) / len(ttfb_values) if ttfb_values else 0.0
            
            # 持续时间统计
            duration_values = [s.total_duration_ms for s in recent_sessions if s.total_duration_ms is not None]
            avg_duration = sum(duration_values) / len(duration_values) if duration_values else 0.0
            
            # 令牌速率统计
            tokens_per_sec_values = []
            for s in recent_sessions:
                if s.total_duration_ms and s.total_duration_ms > 0 and s.tokens_generated > 0:
                    tokens_per_sec_values.append(s.tokens_generated / (s.total_duration_ms / 1000.0))
            avg_tokens_per_sec = sum(tokens_per_sec_values) / len(tokens_per_sec_values) if tokens_per_sec_values else 0.0
            
            # 百分位数计算
            p50_ttfb, p95_ttfb, p99_ttfb = self._calculate_percentiles(ttfb_values)
            
            # 错误分布
            error_distribution: Dict[str, int] = {}
            for s in recent_sessions:
                if not s.success and s.error_type:
                    error_distribution[s.error_type] = error_distribution.get(s.error_type, 0) + 1
            
            return {
                "total_sessions": total,
                "successful_sessions": successful,
                "failed_sessions": failed,
                "success_rate": successful / total if total > 0 else 0.0,
                "avg_ttfb_ms": round(avg_ttfb, 2),
                "avg_duration_ms": round(avg_duration, 2),
                "avg_tokens_per_second": round(avg_tokens_per_sec, 2),
                "active_connections": self.active_connections,
                "p50_ttfb_ms": round(p50_ttfb, 2),
                "p95_ttfb_ms": round(p95_ttfb, 2),
                "p99_ttfb_ms": round(p99_ttfb, 2),
                "error_distribution": error_distribution,
                "time_window_seconds": time_window_seconds
            }
            
        except Exception as e:
            logger.warning(f"⚠️ 获取统计数据失败: {e}")
            return {
                "total_sessions": 0,
                "successful_sessions": 0,
                "failed_sessions": 0,
                "success_rate": 0.0,
                "avg_ttfb_ms": 0.0,
                "avg_duration_ms": 0.0,
                "avg_tokens_per_second": 0.0,
                "active_connections": self.active_connections,
                "p50_ttfb_ms": 0.0,
                "p95_ttfb_ms": 0.0,
                "p99_ttfb_ms": 0.0,
                "error_distribution": {},
                "time_window_seconds": time_window_seconds,
                "error": str(e)
            }
    
    def _calculate_percentiles(self, values: List[float]) -> tuple:
        """
        计算百分位数
        
        Args:
            values: 数值列表
            
        Returns:
            tuple: (p50, p95, p99)
        """
        if not values:
            return (0.0, 0.0, 0.0)
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        def percentile(p: float) -> float:
            idx = int(p * n)
            if idx >= n:
                idx = n - 1
            return sorted_values[idx]
        
        return (percentile(0.5), percentile(0.95), percentile(0.99))
    
    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取最近的会话指标
        
        Args:
            limit: 返回的最大记录数，默认100
            
        Returns:
            List[Dict[str, Any]]: 最近的会话记录列表
            
        Requirements: 1.5, 1.7
        """
        try:
            with self._lock:
                # 获取最近的记录（按时间倒序）
                recent = sorted(
                    self._sessions,
                    key=lambda x: x.timestamp,
                    reverse=True
                )[:limit]
            
            return [record.to_dict() for record in recent]
            
        except Exception as e:
            logger.warning(f"⚠️ 获取最近指标失败: {e}")
            return []
    
    # ========== 流式执行器兼容方法 ==========
    
    def record_ttfb(self, ttfb_ms: float) -> None:
        """
        记录首字节响应时间（TTFB）
        
        供流式执行器调用，记录单次TTFB到Prometheus。
        
        Args:
            ttfb_ms: 首字节响应时间（毫秒）
        """
        try:
            streaming_ttfb.observe(ttfb_ms / 1000.0)  # 转换为秒
            logger.debug(f"📊 记录TTFB: {ttfb_ms:.2f}ms")
        except Exception as e:
            logger.warning(f"⚠️ 记录TTFB失败: {e}")
    
    def record_stream_complete(
        self,
        duration_ms: float,
        tokens: int,
        content_length: int
    ) -> None:
        """
        记录流式会话完成
        
        供流式执行器调用，记录成功完成的流式会话。
        
        Args:
            duration_ms: 总持续时间（毫秒）
            tokens: 生成的令牌数
            content_length: 内容长度
        """
        try:
            # 记录持续时间
            streaming_duration.observe(duration_ms / 1000.0)  # 转换为秒
            
            # 记录令牌速率
            if duration_ms > 0 and tokens > 0:
                tokens_per_sec = tokens / (duration_ms / 1000.0)
                streaming_tokens_per_second.observe(tokens_per_sec)
            
            # 记录成功
            streaming_success.inc()
            
            logger.debug(
                f"📊 记录流式完成: duration={duration_ms:.2f}ms, "
                f"tokens={tokens}, content_length={content_length}"
            )
        except Exception as e:
            logger.warning(f"⚠️ 记录流式完成失败: {e}")
    
    def record_stream_error(self, error: str) -> None:
        """
        记录流式会话错误
        
        供流式执行器调用，记录失败的流式会话。
        
        Args:
            error: 错误信息
        """
        try:
            streaming_failure.inc()
            logger.debug(f"📊 记录流式错误: {error}")
        except Exception as e:
            logger.warning(f"⚠️ 记录流式错误失败: {e}")


# ========== 全局单例 ==========

# 创建全局StreamingMonitor单例
streaming_monitor = StreamingMonitor()


# 导出
__all__ = [
    "streaming_ttfb",
    "streaming_duration",
    "streaming_tokens_per_second",
    "streaming_success",
    "streaming_failure",
    "streaming_active_connections",
    "StreamingSessionMetrics",
    "StreamingSessionRecord",
    "StreamingMonitor",
    "record_streaming_metrics",
    "streaming_monitor"
]
