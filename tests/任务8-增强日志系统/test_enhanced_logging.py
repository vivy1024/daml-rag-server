# -*- coding: utf-8 -*-
"""
增强日志系统测试

测试EnhancedLogger的各项功能。

版本：v1.0.0
创建日期：2025-12-20
"""

import pytest
import time
from src.framework.monitoring.enhanced_logging import EnhancedLogger, SessionLogContext


def test_session_start_logging():
    """测试会话开始日志"""
    logger = EnhancedLogger()
    
    context = logger.log_session_start(
        request_id="test_001",
        user_id="user_123",
        session_id="session_456",
        query="帮我设计一个增肌计划",
        domain="fitness"
    )
    
    assert context.request_id == "test_001"
    assert context.user_id == "user_123"
    assert context.session_id == "session_456"
    assert context.query == "帮我设计一个增肌计划"
    assert context.query_length == len("帮我设计一个增肌计划")
    assert context.domain == "fitness"
    assert context.success is True
    
    # 验证会话已添加到活跃会话列表
    assert "test_001" in logger.active_sessions


def test_step_logging():
    """测试步骤日志"""
    logger = EnhancedLogger()
    
    # 先创建会话
    context = logger.log_session_start(
        request_id="test_002",
        user_id="user_123",
        session_id="session_456",
        query="测试查询",
        domain="fitness"
    )
    
    # 记录步骤开始
    logger.log_step_start(
        request_id="test_002",
        step_number=1,
        step_name="预加载用户档案",
        metadata={"user_id": "user_123"}
    )
    
    # 模拟步骤执行
    time.sleep(0.1)
    
    # 记录步骤完成
    logger.log_step_complete(
        request_id="test_002",
        step_number=1,
        success=True,
        result_summary="用户档案已加载",
        metadata={"profile_loaded": True}
    )
    
    # 验证步骤记录
    assert len(context.steps_executed) == 1
    step = context.steps_executed[0]
    assert step["step_number"] == 1
    assert step["step_name"] == "预加载用户档案"
    assert step["success"] is True
    assert step["result_summary"] == "用户档案已加载"
    assert "duration_ms" in step
    assert step["duration_ms"] >= 100  # 至少100ms


def test_structured_data_detection_logging():
    """测试结构化数据检测日志"""
    logger = EnhancedLogger()
    
    # 先创建会话
    context = logger.log_session_start(
        request_id="test_003",
        user_id="user_123",
        session_id="session_456",
        query="测试查询",
        domain="fitness"
    )
    
    # 记录结构化数据检测
    logger.log_structured_data_detected(
        request_id="test_003",
        data_type="training_plan",
        data_size=1024,
        marker="TRAINING_PLAN",
        extraction_success=True
    )
    
    # 验证结构化数据记录
    assert len(context.structured_data_detected) == 1
    detection = context.structured_data_detected[0]
    assert detection["data_type"] == "training_plan"
    assert detection["data_size"] == 1024
    assert detection["marker"] == "TRAINING_PLAN"
    assert detection["extraction_success"] is True


def test_error_logging():
    """测试错误日志"""
    logger = EnhancedLogger()
    
    # 先创建会话
    context = logger.log_session_start(
        request_id="test_004",
        user_id="user_123",
        session_id="session_456",
        query="测试查询",
        domain="fitness"
    )
    
    # 创建一个测试异常
    try:
        raise ValueError("测试错误")
    except ValueError as e:
        logger.log_error(
            request_id="test_004",
            error=e,
            context_info={"step": "测试步骤"},
            step_number=1
        )
    
    # 验证错误记录
    assert len(context.errors) == 1
    error = context.errors[0]
    assert error["error_type"] == "ValueError"
    assert error["error_message"] == "测试错误"
    assert "error_traceback" in error
    assert error["step_number"] == 1
    assert context.success is False  # 错误发生后success应该变为False


def test_session_complete_logging():
    """测试会话完成日志"""
    logger = EnhancedLogger()
    
    # 先创建会话
    context = logger.log_session_start(
        request_id="test_005",
        user_id="user_123",
        session_id="session_456",
        query="测试查询",
        domain="fitness"
    )
    
    # 模拟会话执行
    time.sleep(0.1)
    
    # 记录会话完成
    logger.log_session_complete(
        request_id="test_005",
        tokens_generated=100,
        content_length=500,
        ttfb_ms=50.0,
        generation_speed=20.0
    )
    
    # 验证会话已从活跃列表中移除
    assert "test_005" not in logger.active_sessions


def test_session_summary():
    """测试会话摘要"""
    logger = EnhancedLogger()
    
    # 创建会话
    context = logger.log_session_start(
        request_id="test_006",
        user_id="user_123",
        session_id="session_456",
        query="测试查询",
        domain="fitness"
    )
    
    # 添加一些步骤
    logger.log_step_start("test_006", 1, "步骤1")
    logger.log_step_complete("test_006", 1, success=True)
    
    # 添加结构化数据
    logger.log_structured_data_detected(
        "test_006", "training_plan", 1024, "TRAINING_PLAN", True
    )
    
    # 获取摘要
    summary = logger.get_session_summary("test_006")
    
    assert summary is not None
    assert summary["request_id"] == "test_006"
    assert summary["user_id"] == "user_123"
    assert summary["steps_executed"] == 1
    assert summary["structured_data_detected"] == 1
    assert summary["errors"] == 0
    assert summary["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
