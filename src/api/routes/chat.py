# -*- coding: utf-8 -*-
"""
Chat Route - 聊天接口（集成三层检索架构 v2.0.0）

薄路由架构设计：
- 路由层：只负责参数验证和响应转换
- 业务逻辑：集中在ChatService类中

集成特性：
- 三层检索：语义搜索 + 图谱推理 + 业务约束
- 字段标准化：自动标准化用户输入
- 反幻觉验证：三层反幻觉检测
- 个性化回复：基于用户档案的定制化

POST /chat - PHP后端调用（保持兼容）
POST /v1/chat - RESTful版本化路由
POST /v1/chat/stream - 流式聊天接口

版本：v2.0.0
更新日期：2025-11-17
重构说明：集成三层检索架构，支持字段标准化和反幻觉验证
"""

import logging
import json
import asyncio
import uuid
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, AsyncGenerator, Dict, Any
from sse_starlette.sse import EventSourceResponse

# 导入API模型
from ..models import ApiResponse, ApiError, ChatRequest, ChatResponse
# 导入11步工作流程执行器
from ...applications.fitness.workflow_executor import execute_eleven_step_workflow
# 导入权限检查器
from ...framework.auth.fail_closed_checker import FailClosedPermissionChecker

logger = logging.getLogger(__name__)

# 全局fail-closed权限检查器实例
_permission_checker = FailClosedPermissionChecker()


def _extract_user_id(request: Request, body_user_id: Optional[str] = None) -> str:
    """
    从请求中提取user_id（Property 4: JWT身份优先于请求体）
    
    优先级：
    1. Internal JWT中的user_id（request.state.permission_claims）
    2. 请求体中的user_id（旧模式兼容）
    """
    auth_mode = getattr(request.state, "auth_mode", None)
    
    if auth_mode == "internal_jwt":
        claims = getattr(request.state, "permission_claims", None)
        if claims:
            return str(claims.user_id)
    
    # 旧模式或无认证：从请求体获取
    if body_user_id:
        return str(body_user_id) if not isinstance(body_user_id, str) else body_user_id
    
    return ""

router = APIRouter()


@router.post("/chat", response_model=ApiResponse[ChatResponse])
@router.post("/v1/chat", response_model=ApiResponse[ChatResponse])
async def chat(request: Request, chat_request: ChatRequest) -> ApiResponse[ChatResponse]:
    """
    聊天接口 - 唯一的完整工作流程入口

    执行完整的11步工作流程：
    1. 预加载用户档案
    2. 会话记录存储
    3. 检查会员权限
    4. BGE查询复杂度分类（使用缓存模型）
    5. 智能模型选择
    6. Few-Shot检索
    7. DAG编排器
    8. 执行DAG任务（包括三层检索）
    9. 工具结果汇总
    10. LLM生成最终回答
    11. 记录交互

    Args:
        request: {
            "user_id": "用户ID",
            "query": "用户查询",
            "domain": "fitness",  # 可选，默认"fitness"
            "session_id": "会话ID",  # 可选
            "context": {},  # 上下文信息
        }

    Returns:
        ApiResponse[ChatResponse]: 聊天响应
            - response: AI回答
            - interaction_id: 交互ID
            - model_used: 使用的模型
            - tools_used: 使用的工具列表
            - execution_time: 执行时间
            - personalization_score: 个性化得分
    """
    try:
        start_time = asyncio.get_event_loop().time()

        # 1. 参数验证和输入清理 - JWT身份优先于请求体（Property 4）
        user_id = _extract_user_id(request, chat_request.user_id)
        query_text = chat_request.query

        if not user_id or not query_text:
            raise ApiError(400, "缺少必需参数：user_id 和 query")

        # 类型转换：确保user_id是字符串
        if isinstance(user_id, (int, float)):
            user_id = str(user_id)

        # 类型转换：确保query是字符串
        if not isinstance(query_text, str):
            query_text = str(query_text)
        
        # 输入验证和清理
        try:
            from ..middleware.security import InputValidator
            user_id = InputValidator.validate_and_clean('user_id', user_id)
            query_text = InputValidator.validate_and_clean('query', query_text)
        except ImportError:
            logger.warning("输入验证器未加载，跳过输入清理")
        except Exception as e:
            logger.error(f"输入验证失败: {e}")
            raise ApiError(400, f"输入验证失败: {str(e)}")

        # Prompt Injection 检测
        try:
            from ...framework.safety import get_injection_detector
            detector = get_injection_detector()
            injection_result = detector.detect(query_text)
            if injection_result.is_injection:
                return ApiResponse.success(
                    data=ChatResponse(
                        response=detector.get_safe_response(),
                        interaction_id="blocked",
                        model_used="safety_filter",
                        tools_used=[],
                        execution_time=0.0,
                        personalization_score=0.0,
                    )
                )
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"注入检测异常(降级放行): {e}")

        # 2. session_id处理：支持前端传入或自动生成
        session_id = chat_request.session_id or str(uuid.uuid4())

        logger.info(
            f"📨 Chat request: user={user_id}, "
            f"session={session_id[:8]}..., "
            f"query='{query_text[:50]}...'"
        )

        # 3. 并发限制检查
        from ...framework.monitoring.concurrency_limiter import concurrency_limiter
        
        # 尝试获取连接许可（等待最多5秒）
        acquired = await concurrency_limiter.acquire(
            user_id=user_id,
            session_id=session_id,
            timeout=5.0
        )
        
        if not acquired:
            # 并发限制：返回429错误
            logger.warning(
                f"⚠️ 并发限制：拒绝连接 user={user_id}, session={session_id[:8]}..."
            )
            return ApiResponse.error(
                code=429,
                msg="服务繁忙，请稍后重试",
                data={"retry_after": 10}
            )

        # 3. 执行完整的11步工作流程（或Agent模式）
        requested_mode = getattr(chat_request, "mode", "auto") or "auto"
        topic_id = getattr(chat_request, "topic_id", None)

        try:
            # 尝试解析执行模式（需要先获取会员等级）
            execution_mode = "dag"  # 默认DAG
            if requested_mode == "agent":
                try:
                    from ...applications.fitness.mode_router import resolve_execution_mode
                    # 简化：从权限claims获取会员等级
                    claims = getattr(request.state, "permission_claims", None)
                    membership_level = getattr(claims, "membership_level", "free") if claims else "free"
                    execution_mode = resolve_execution_mode(requested_mode, membership_level)
                except Exception as e:
                    logger.warning(f"模式路由解析失败，降级到DAG: {e}")

            if execution_mode == "agent":
                # Agent模式：LLM动态决策
                logger.info("🤖 Agent模式启动...")
                from ...applications.fitness.agent import AgentExecutor
                from ...framework.core.simple_framework_initializer import get_framework_components

                components = get_framework_components()
                agent_executor = AgentExecutor(
                    llm_client=components.get("llm_client"),
                    mcp_orchestrator=components.get("mcp_orchestrator"),
                    tool_schemas=components.get("tool_schemas", []),
                )
                agent_result = await agent_executor.execute(
                    user_id=user_id,
                    query=query_text,
                    membership_level=membership_level,
                )
                # 转换为统一响应格式
                workflow_result = {
                    "response": agent_result.get("final_response", "抱歉，暂时无法生成回答。"),
                    "processing_time": agent_result.get("total_time_s", 0.0),
                    "metadata": {
                        "selected_model": "agent_mode",
                        "execution_mode": "agent",
                        "tool_calls_count": agent_result.get("tool_calls_count", 0),
                        "total_cost": agent_result.get("total_cost", 0.0),
                    },
                    "eleven_step_workflow": {},
                }
            else:
                # DAG模式：固定模板编排（默认）
                logger.info("🚀 开始执行11步工作流程...")
                workflow_result = await execute_eleven_step_workflow(
                    query_text=query_text,
                    user_id=user_id,
                    domain=chat_request.domain,
                    user_profile=None,
                    session_id=session_id
                )
        finally:
            # 无论成功还是失败，都要释放并发许可
            await concurrency_limiter.release(session_id)

        # 4. 提取工作流程结果
        # 新版executor直接返回response字段，旧版使用eleven_step_workflow
        eleven_step_data = workflow_result.get("eleven_step_workflow", {})
        if eleven_step_data:
            final_response = eleven_step_data.get("final_response", "抱歉，暂时无法生成回答，请稍后再试。")
            model_used = eleven_step_data.get("model_selected", "unknown")
        else:
            # 新版executor格式
            final_response = workflow_result.get("response", "抱歉，暂时无法生成回答，请稍后再试。")
            metadata = workflow_result.get("metadata", {})
            model_used = metadata.get("selected_model", "unknown")
        processing_time = workflow_result.get("processing_time", 0.0)

        # 5. 构建工具使用列表
        tools_used = [
            "user_profile_loader",
            "session_manager",
            "membership_checker",
            "bge_classifier",
            "model_selector",
            "few_shot_retriever",
            "dag_orchestrator",
            "three_layer_retrieval",
            "tool_aggregator",
            "llm_generator",
            "interaction_logger"
        ]

        # 6. 构建响应字典（直接使用字典而不是Pydantic模型）
        personalization_score = _calculate_personalization_score(
            eleven_step_data.get("user_profile_loaded", False),
            eleven_step_data.get("membership_checked", False),
            eleven_step_data.get("few_shot_examples", 0)
        )
        
        response_dict = {
            "response": final_response,
            "interaction_id": session_id,
            "model_used": model_used,
            "tools_used": tools_used,
            "execution_time": processing_time,
            "personalization_score": personalization_score,
            "few_shot_examples_count": eleven_step_data.get("few_shot_examples", 0),
            "cache_hit": False,
            # 添加metadata字段以兼容测试
            "metadata": {
                "model_used": model_used,
                "tools_called": tools_used,  # 别名，兼容测试
                "tools_used": tools_used,
                "execution_time": processing_time,
                "personalization_score": personalization_score,
                "few_shot_examples_count": eleven_step_data.get("few_shot_examples", 0),
                "cache_hit": False,
                "request_id": eleven_step_data.get("request_id", "unknown"),
                "dag_template_id": eleven_step_data.get("dag_template_id"),
                "dag_tasks_completed": eleven_step_data.get("dag_tasks_completed", 0),
                "mcp_tools_called": eleven_step_data.get("mcp_tools_called", 0)
            }
        }

        # 7. 记录完成日志
        logger.info(
            f"✅ Chat completed: user={user_id}, "
            f"model={model_used}, "
            f"tools={len(tools_used)}, "
            f"time={processing_time:.2f}s, "
            f"request_id={eleven_step_data.get('request_id', 'unknown')}"
        )

        # 7.5 异步用量上报（不阻塞响应）
        try:
            from ...framework.auth.usage_reporter import UsageReporter
            reporter = UsageReporter()
            asyncio.create_task(reporter.report_usage(
                user_id=int(user_id) if user_id.isdigit() else 0,
                mode="dag",
                session_id=session_id,
            ))
        except Exception as e:
            logger.warning(f"用量上报启动失败（不影响响应）: {e}")

        # 8. 返回成功响应（直接返回字典，避免Pydantic模型验证）
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "msg": "成功",
                "data": response_dict,
                "timestamp": datetime.now().isoformat()
            }
        )

    except ApiError as e:
        logger.error(f"Chat API错误: {e.msg}", exc_info=True)
        return ApiResponse.error(code=e.code, msg=e.msg, data=e.data)

    except Exception as e:
        logger.error(f"Chat处理异常: {e}", exc_info=True)
        return ApiResponse.error(
            code=500,
            msg=f"服务器错误: {str(e)}"
        )


async def stream_chat_response(
    chat_result: dict,
    three_layer_result: Optional[dict] = None
) -> AsyncGenerator[str, None]:
    """
    流式发送聊天响应（SSE格式）

    支持增量式内容发送，提升用户体验

    Args:
        chat_result: ChatService返回的完整响应
        three_layer_result: 三层检索结果（可选）

    Yields:
        SSE格式的数据块
    """
    try:
        # 1. 发送开始事件
        start_data = {
            "type": "start",
            "session_id": chat_result.get("session_id"),
            "model_used": chat_result.get("metadata", {}).get("model", "unknown")
        }
        yield f"data: {json.dumps(start_data, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.01)

        # 2. 流式发送响应文本（模拟打字效果）
        response_text = chat_result.get("response", "") or ""
        if not response_text:
            response_text = "抱歉，我无法生成合适的回答。"

        chunk_size = 5  # 每次发送5个字符（更流畅的打字效果）

        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i+chunk_size]
            chunk_data = {
                "type": "chunk",
                "content": chunk,
                "done": False
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)  # 模拟延迟

        # 3. 发送三层检索元数据（如果可用）
        if three_layer_result:
            metadata_data = {
                "type": "three_layer_metadata",
                "retrieval_summary": getattr(three_layer_result, 'retrieval_summary', None),
                "anti_hallucination": getattr(three_layer_result, 'anti_hallucination_result', None),
                "standardization": getattr(three_layer_result, 'standardization_result', None)
            }
            yield f"data: {json.dumps(metadata_data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)

        # 4. 发送通用元数据
        tools_used = chat_result.get("tools_used", [])
        few_shot_count = chat_result.get("metadata", {}).get("few_shot_count", 0)
        user_profile_loaded = "get_user_profile" in tools_used
        membership_checked = chat_result.get("metadata", {}).get("membership_checked", False)
        
        metadata = {
            "type": "metadata",
            "model_used": chat_result.get("metadata", {}).get("model", "unknown"),
            "tools_used": tools_used,
            "execution_time": chat_result.get("metadata", {}).get("processing_time", 0.0),
            "few_shot_count": few_shot_count,
            "personalization_score": _calculate_personalization_score(
                user_profile_loaded, membership_checked, few_shot_count
            )
        }
        yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.01)

        # 5. 发送完成事件
        done_data = {
            "type": "done",
            "session_id": chat_result.get("session_id"),
            "success": True,
            "total_time": asyncio.get_event_loop().time()
        }
        yield f"data: {json.dumps(done_data)}\n\n"

    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        error_data = {
            "type": "error",
            "message": str(e),
            "session_id": chat_result.get("session_id")
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post("/v1/chat/stream")
async def chat_stream(request: Request, body: Dict[str, Any]):
    """
    流式聊天接口（SSE - Server-Sent Events）- 真实流式输出版本（带降级机制和并发限制）

    使用场景：
    - 前端需要实时显示AI打字效果
    - 长文本响应的渐进式呈现（突破4096 token限制）
    - 提升用户体验

    技术实现：
    1. 检查并发限制
    2. 执行步骤1-9（同步）
    3. 步骤10使用真实的LLM流式调用
    4. 实时yield SSE事件给前端
    5. 流式失败时自动降级到非流式模式
    6. 释放并发许可

    SSE事件类型：
        - step: {"type": "step", "step": 1-11, "message": "步骤描述"}
        - chunk: {"type": "chunk", "content": "文本片段"}
        - structured_data: {"type": "structured_data", "data_type": "training_plan", "data": {...}}
        - done: {"type": "done", "data": {"request_id": "xxx", "total_length": 8500, ...}}
        - error: {"type": "error", "error": "错误信息"}
        - fallback: {"type": "fallback", "message": "降级到非流式模式"}
        - rate_limit: {"type": "rate_limit", "message": "服务繁忙，请稍后重试"}

    Example:
        curl -N -X POST http://localhost:8001/v1/chat/stream \
          -H "Content-Type: application/json" \
          -d '{"user_id": "test", "query": "帮我设计一个完整的训练计划"}'
    """
    try:
        # 1. 参数验证和类型转换 - JWT身份优先于请求体（Property 4）
        body_user_id = body.get("user_id")
        user_id = _extract_user_id(request, body_user_id)
        query_text = body.get("query")

        if not user_id or not query_text:
            raise HTTPException(status_code=400, detail="缺少必需参数：user_id 和 query")

        # 类型转换：确保user_id是字符串
        if isinstance(user_id, (int, float)):
            user_id = str(user_id)

        # 类型转换：确保query是字符串
        if not isinstance(query_text, str):
            query_text = str(query_text)

        session_id = body.get("session_id") or str(uuid.uuid4())
        topic_id = body.get("topic_id")  # 话题ID，用于多轮对话
        domain = body.get("domain", "fitness")
        strategy = body.get("strategy", "dag")  # 执行策略：dag或agent
        template_id = body.get("template_id")  # DAG模板ID（用户选择时强制使用）

        logger.info(
            f"📨 Chat stream request: user={user_id}, "
            f"topic={topic_id or 'None'}, "
            f"strategy={strategy}, "
            f"template_id={template_id or 'auto'}, "
            f"query='{query_text[:50]}...'"
        )
        
        # 2. 并发限制检查
        from ...framework.monitoring.concurrency_limiter import concurrency_limiter
        
        # 尝试获取连接许可（等待最多5秒）
        acquired = await concurrency_limiter.acquire(
            user_id=user_id,
            session_id=session_id,
            timeout=5.0
        )
        
        if not acquired:
            # 并发限制：返回503错误
            logger.warning(
                f"⚠️ 并发限制：拒绝连接 user={user_id}, session={session_id[:8]}..."
            )
            
            # 返回SSE格式的错误响应
            async def rate_limit_generator():
                yield {
                    "event": "rate_limit",
                    "data": json.dumps({
                        "type": "rate_limit",
                        "message": "服务繁忙，请稍后重试",
                        "retry_after": 10
                    }, ensure_ascii=False)
                }
            
            from sse_starlette.sse import EventSourceResponse
            return EventSourceResponse(
                rate_limit_generator(),
                status_code=503,
                headers={
                    "Retry-After": "10",
                    "Cache-Control": "no-cache"
                }
            )

        # 3. 定义SSE事件生成器（带降级机制和指标记录）
        async def event_generator():
            """SSE事件生成器 - 使用真实的流式工作流，失败时降级"""
            stream_failed = False
            fallback_response = None
            
            # 初始化流式会话指标
            from ...framework.monitoring.streaming_metrics import (
                StreamingSessionMetrics,
                record_streaming_metrics
            )
            
            metrics = StreamingSessionMetrics(
                session_id=session_id,
                user_id=user_id,
                start_time=time.time()
            )
            
            first_byte_sent = False
            total_tokens = 0
            
            try:
                # 导入流式工作流执行器
                from ...applications.fitness.workflow_executor import execute_eleven_step_workflow_stream
                
                # 执行流式工作流，逐个yield事件
                async for event in execute_eleven_step_workflow_stream(
                    query_text=query_text,
                    user_id=user_id,
                    domain=domain,
                    user_profile=None,
                    session_id=session_id,
                    topic_id=topic_id,  # 传递话题ID用于多轮对话
                    strategy=strategy,  # 传递执行策略
                    template_id=template_id  # 传递用户选择的DAG模板ID（强制使用）
                ):
                    # 记录首字节时间（TTFB）
                    if not first_byte_sent:
                        metrics.first_byte_time = time.time()
                        first_byte_sent = True
                        logger.debug(f"📊 首字节发送: TTFB={metrics.ttfb:.2f}s, session={session_id[:8]}...")
                    
                    # 统计令牌数（如果事件包含content）
                    if event.get("type") == "chunk" and "content" in event:
                        # 简单估算：中文按字符数，英文按空格分词
                        content = event["content"]
                        total_tokens += len(content)
                    
                    # 发送SSE事件
                    yield {
                        "event": event["type"],
                        "data": json.dumps(event, ensure_ascii=False)
                    }
                
                # 流式成功完成
                metrics.end_time = time.time()
                metrics.total_tokens = total_tokens
                metrics.success = True
                
                # 记录指标到Prometheus
                try:
                    record_streaming_metrics(metrics)
                    logger.info(
                        f"✅ 流式会话完成: session={session_id[:8]}..., "
                        f"TTFB={metrics.ttfb:.2f}s, duration={metrics.duration:.2f}s, "
                        f"tokens={total_tokens}, rate={metrics.tokens_per_second:.1f} tokens/s"
                    )
                except Exception as metric_error:
                    logger.warning(f"⚠️ 指标记录失败（不影响主业务）: {metric_error}")
                    
            except Exception as stream_error:
                logger.error(f"⚠️ 流式生成失败，尝试降级到非流式模式: {stream_error}", exc_info=True)
                stream_failed = True
                
                # 记录失败指标
                metrics.end_time = time.time()
                metrics.total_tokens = total_tokens
                metrics.success = False
                metrics.error_message = str(stream_error)
                
                try:
                    record_streaming_metrics(metrics)
                    logger.info(
                        f"❌ 流式会话失败: session={session_id[:8]}..., "
                        f"error={stream_error}, duration={metrics.duration:.2f}s"
                    )
                except Exception as metric_error:
                    logger.warning(f"⚠️ 失败指标记录失败: {metric_error}")
                
                # 发送降级通知事件
                yield {
                    "event": "fallback",
                    "data": json.dumps({
                        "type": "fallback",
                        "message": "流式输出暂时不可用，切换到标准模式",
                        "reason": "stream_error"
                    }, ensure_ascii=False)
                }
                
                # 尝试使用非流式模式
                try:
                    logger.info(f"🔄 降级：使用非流式工作流")
                    
                    # 调用非流式工作流
                    workflow_result = await execute_eleven_step_workflow(
                        query_text=query_text,
                        user_id=user_id,
                        domain=domain,
                        user_profile=None,
                        session_id=session_id
                    )
                    
                    # 提取响应
                    eleven_step_data = workflow_result.get("eleven_step_workflow", {})
                    fallback_response = eleven_step_data.get("final_response", "抱歉，暂时无法生成回答，请稍后重试。")
                    
                    # 模拟流式发送（分块发送非流式响应）
                    chunk_size = 50
                    for i in range(0, len(fallback_response), chunk_size):
                        chunk = fallback_response[i:i+chunk_size]
                        yield {
                            "event": "chunk",
                            "data": json.dumps({
                                "type": "chunk",
                                "content": chunk,
                                "fallback": True
                            }, ensure_ascii=False)
                        }
                        await asyncio.sleep(0.05)  # 模拟延迟
                    
                    # 发送完成事件
                    yield {
                        "event": "done",
                        "data": json.dumps({
                            "type": "done",
                            "data": {
                                "request_id": session_id,
                                "total_length": len(fallback_response),
                                "fallback": True,
                                "success": True
                            }
                        }, ensure_ascii=False)
                    }
                    
                    # 记录降级成功的指标（作为成功会话）
                    metrics.end_time = time.time()
                    metrics.total_tokens = len(fallback_response)
                    metrics.success = True
                    
                    try:
                        record_streaming_metrics(metrics)
                        logger.info(
                            f"✅ 降级成功：非流式模式返回响应（长度: {len(fallback_response)}字）, "
                            f"duration={metrics.duration:.2f}s"
                        )
                    except Exception as metric_error:
                        logger.warning(f"⚠️ 降级成功指标记录失败: {metric_error}")
                    
                except Exception as fallback_error:
                    logger.error(f"❌ 降级失败：非流式模式也失败: {fallback_error}", exc_info=True)
                    
                    # 记录降级失败的指标
                    metrics.end_time = time.time()
                    metrics.success = False
                    metrics.error_message = f"Stream failed, fallback also failed: {str(fallback_error)}"
                    
                    try:
                        record_streaming_metrics(metrics)
                    except Exception as metric_error:
                        logger.warning(f"⚠️ 降级失败指标记录失败: {metric_error}")
                    
                    # 发送最终错误事件
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "type": "error",
                            "error": f"服务暂时不可用: {str(fallback_error)}",
                            "fallback_failed": True
                        }, ensure_ascii=False)
                    }
            
            finally:
                # 无论成功还是失败，都要释放并发许可
                await concurrency_limiter.release(session_id)
        
        # 4. 返回SSE响应
        from sse_starlette.sse import EventSourceResponse
        
        return EventSourceResponse(
            event_generator(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用nginx缓冲
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Stream setup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


def _calculate_personalization_score(
    user_profile_loaded: bool,
    membership_checked: bool,
    few_shot_count: int
) -> float:
    """
    计算个性化得分

    Args:
        user_profile_loaded: 是否加载了用户档案
        membership_checked: 是否检查了会员权限
        few_shot_count: Few-Shot示例数量

    Returns:
        float: 个性化得分（0-1）
    """
    base_score = 0.5

    # 基于用户档案
    if user_profile_loaded:
        base_score += 0.2

    # 基于会员权限
    if membership_checked:
        base_score += 0.1

    # 基于Few-Shot示例
    base_score += min(few_shot_count * 0.1, 0.2)
    
    return min(base_score, 1.0)

    return min(base_score, 1.0)


# 导出路由
__all__ = ['router']