# -*- coding: utf-8 -*-
"""
增强日志系统

为流式会话提供结构化、详细的日志记录功能。

功能：
- 会话开始/结束日志
- 步骤执行日志（包含耗时）
- 结构化数据检测日志
- 错误日志（包含完整堆栈和上下文）
- 性能指标日志

版本：v1.0.0
创建日期：2025-12-20
"""

import logging
import time
import json
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SessionLogContext:
    """会话日志上下文"""
    request_id: str
    user_id: str
    session_id: str
    query: str
    query_length: int
    domain: str
    start_time: float
    timestamp: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # 性能指标
    ttfb_ms: Optional[float] = None
    total_duration_ms: Optional[float] = None
    tokens_generated: int = 0
    content_length: int = 0
    
    # 步骤执行记录
    steps_executed: List[Dict[str, Any]] = field(default_factory=list)
    
    # 结构化数据检测
    structured_data_detected: List[Dict[str, Any]] = field(default_factory=list)
    
    # 错误记录
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # 成功标志
    success: bool = True


class EnhancedLogger:
    """增强日志记录器"""
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionLogContext] = {}
    
    def log_session_start(
        self,
        request_id: str,
        user_id: str,
        session_id: str,
        query: str,
        domain: str = "fitness"
    ) -> SessionLogContext:
        """
        记录流式会话开始
        
        Args:
            request_id: 请求ID
            user_id: 用户ID
            session_id: 会话ID
            query: 用户查询
            domain: 领域
        
        Returns:
            SessionLogContext: 会话日志上下文
        """
        context = SessionLogContext(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            query=query,
            query_length=len(query),
            domain=domain,
            start_time=time.time()
        )
        
        self.active_sessions[request_id] = context
        
        logger.info(
            f"🚀 [{request_id}] 流式会话开始: "
            f"user_id={user_id}, "
            f"session_id={session_id}, "
            f"query='{query[:100]}{'...' if len(query) > 100 else ''}', "
            f"query_length={len(query)}, "
            f"domain={domain}, "
            f"timestamp={context.timestamp}"
        )
        
        return context
    
    def log_step_start(
        self,
        request_id: str,
        step_number: int,
        step_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录步骤开始
        
        Args:
            request_id: 请求ID
            step_number: 步骤编号
            step_name: 步骤名称
            metadata: 额外元数据
        """
        context = self.active_sessions.get(request_id)
        if not context:
            logger.warning(f"⚠️ [{request_id}] 会话上下文不存在，无法记录步骤开始")
            return
        
        step_info = {
            "step_number": step_number,
            "step_name": step_name,
            "start_time": time.time(),
            "metadata": metadata or {}
        }
        
        context.steps_executed.append(step_info)
        
        logger.info(
            f"[{request_id}] 步骤{step_number}开始: "
            f"{step_name}, "
            f"timestamp={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def log_step_complete(
        self,
        request_id: str,
        step_number: int,
        success: bool = True,
        result_summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录步骤完成
        
        Args:
            request_id: 请求ID
            step_number: 步骤编号
            success: 是否成功
            result_summary: 结果摘要
            metadata: 额外元数据
        """
        context = self.active_sessions.get(request_id)
        if not context:
            logger.warning(f"⚠️ [{request_id}] 会话上下文不存在，无法记录步骤完成")
            return
        
        # 查找对应的步骤记录
        step_info = None
        for step in context.steps_executed:
            if step["step_number"] == step_number and "end_time" not in step:
                step_info = step
                break
        
        if step_info:
            step_info["end_time"] = time.time()
            step_info["duration_ms"] = (step_info["end_time"] - step_info["start_time"]) * 1000
            step_info["success"] = success
            step_info["result_summary"] = result_summary
            if metadata:
                step_info["metadata"].update(metadata)
            
            status_icon = "✅" if success else "❌"
            logger.info(
                f"{status_icon} [{request_id}] 步骤{step_number}完成: "
                f"{step_info['step_name']}, "
                f"耗时={step_info['duration_ms']:.2f}ms, "
                f"success={success}"
                + (f", {result_summary}" if result_summary else "")
            )
        else:
            logger.warning(f"⚠️ [{request_id}] 未找到步骤{step_number}的开始记录")
    
    def log_structured_data_detected(
        self,
        request_id: str,
        data_type: str,
        data_size: int,
        marker: str,
        extraction_success: bool = True
    ):
        """
        记录结构化数据检测
        
        Args:
            request_id: 请求ID
            data_type: 数据类型（training_plan, nutrition_data等）
            data_size: 数据大小（字节）
            marker: 标记类型（TRAINING_PLAN, NUTRITION_DATA等）
            extraction_success: 提取是否成功
        """
        context = self.active_sessions.get(request_id)
        if not context:
            logger.warning(f"⚠️ [{request_id}] 会话上下文不存在，无法记录结构化数据检测")
            return
        
        detection_info = {
            "data_type": data_type,
            "data_size": data_size,
            "marker": marker,
            "extraction_success": extraction_success,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        context.structured_data_detected.append(detection_info)
        
        status_icon = "📦" if extraction_success else "⚠️"
        logger.info(
            f"{status_icon} [{request_id}] 检测到结构化数据: "
            f"type={data_type}, "
            f"marker={marker}, "
            f"size={data_size}字节, "
            f"extraction_success={extraction_success}"
        )
    
    def log_error(
        self,
        request_id: str,
        error: Exception,
        context_info: Optional[Dict[str, Any]] = None,
        step_number: Optional[int] = None
    ):
        """
        记录错误（包含完整堆栈和上下文）
        
        Args:
            request_id: 请求ID
            error: 异常对象
            context_info: 上下文信息
            step_number: 步骤编号（如果在步骤中发生）
        """
        context = self.active_sessions.get(request_id)
        if context:
            context.success = False
        
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_traceback": traceback.format_exc(),
            "context_info": context_info or {},
            "step_number": step_number,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if context:
            context.errors.append(error_info)
        
        logger.error(
            f"❌ [{request_id}] 错误发生: "
            f"error_type={error_info['error_type']}, "
            f"error_message={error_info['error_message']}"
            + (f", step={step_number}" if step_number else "")
            + (f", context={json.dumps(context_info, ensure_ascii=False)}" if context_info else ""),
            exc_info=True
        )
    
    def log_session_complete(
        self,
        request_id: str,
        tokens_generated: int,
        content_length: int,
        ttfb_ms: Optional[float] = None,
        generation_speed: Optional[float] = None
    ):
        """
        记录会话完成
        
        Args:
            request_id: 请求ID
            tokens_generated: 生成的token数
            content_length: 内容长度（字符数）
            ttfb_ms: 首字节响应时间（毫秒）
            generation_speed: 生成速度（tokens/s）
        """
        context = self.active_sessions.get(request_id)
        if not context:
            logger.warning(f"⚠️ [{request_id}] 会话上下文不存在，无法记录会话完成")
            return
        
        context.total_duration_ms = (time.time() - context.start_time) * 1000
        context.tokens_generated = tokens_generated
        context.content_length = content_length
        context.ttfb_ms = ttfb_ms
        
        # 计算生成速度
        if generation_speed is None and context.total_duration_ms > 0:
            generation_speed = tokens_generated / (context.total_duration_ms / 1000)
        
        # 统计步骤信息
        completed_steps = sum(1 for step in context.steps_executed if step.get("success", False))
        failed_steps = sum(1 for step in context.steps_executed if not step.get("success", True))
        total_steps = len(context.steps_executed)
        
        # 计算平均步骤耗时
        step_durations = [step.get("duration_ms", 0) for step in context.steps_executed if "duration_ms" in step]
        avg_step_duration = sum(step_durations) / len(step_durations) if step_durations else 0
        
        status_icon = "🎉" if context.success else "❌"
        logger.info(
            f"{status_icon} [{request_id}] 流式会话完成: "
            f"success={context.success}, "
            f"total_duration={context.total_duration_ms:.0f}ms, "
            f"ttfb={ttfb_ms:.0f}ms, " if ttfb_ms else ""
            f"tokens_generated={tokens_generated}, "
            f"content_length={content_length}字, "
            f"generation_speed={generation_speed:.1f} tokens/s, "
            f"steps_completed={completed_steps}/{total_steps}, "
            f"steps_failed={failed_steps}, "
            f"avg_step_duration={avg_step_duration:.2f}ms, "
            f"structured_data_count={len(context.structured_data_detected)}, "
            f"errors_count={len(context.errors)}"
        )
        
        # 如果有错误，记录错误摘要
        if context.errors:
            logger.error(
                f"❌ [{request_id}] 会话错误摘要: "
                f"total_errors={len(context.errors)}, "
                f"error_types={', '.join(set(e['error_type'] for e in context.errors))}"
            )
        
        # 移除已完成的会话上下文
        del self.active_sessions[request_id]
    
    def get_session_summary(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话摘要
        
        Args:
            request_id: 请求ID
        
        Returns:
            Dict[str, Any]: 会话摘要，如果会话不存在则返回None
        """
        context = self.active_sessions.get(request_id)
        if not context:
            return None
        
        return {
            "request_id": context.request_id,
            "user_id": context.user_id,
            "session_id": context.session_id,
            "query": context.query,
            "query_length": context.query_length,
            "domain": context.domain,
            "start_time": context.timestamp,
            "total_duration_ms": context.total_duration_ms,
            "ttfb_ms": context.ttfb_ms,
            "tokens_generated": context.tokens_generated,
            "content_length": context.content_length,
            "steps_executed": len(context.steps_executed),
            "structured_data_detected": len(context.structured_data_detected),
            "errors": len(context.errors),
            "success": context.success
        }


# 全局增强日志记录器实例
enhanced_logger = EnhancedLogger()


# 导出
__all__ = [
    "EnhancedLogger",
    "SessionLogContext",
    "enhanced_logger"
]
