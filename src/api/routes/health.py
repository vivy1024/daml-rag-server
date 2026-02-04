# -*- coding: utf-8 -*-
"""
Health Route - 系统健康检查接口

提供完整的系统健康状态监控，包括：
- DAML-RAG框架状态
- 三层检索组件状态
- 数据库连接状态
- API接口状态
- 性能指标监控

GET  /api/health - 公开健康检查（仅返回基本状态）
GET  /api/health/components - 组件详细状态（需要管理员认证）
GET  /api/health/metrics - 性能指标（需要管理员认证）

版本：v2.2.0
更新日期：2026-01-18
重构说明：安全加固 - 公开端点仅返回基本状态，详细端点需要认证
安全加固：Requirements 9.1, 9.2, 9.3, 9.4
"""

import logging
import os
import asyncio
import psutil
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional, Union, List

# 导入API模型
from ..models import ApiResponse, HealthResponse

# 导入监控模块
from ...framework.monitoring.structured_logger import get_logger, set_trace_id
from ...framework.monitoring.metrics_collector import get_metrics_collector

logger = logging.getLogger(__name__)
structured_logger = get_logger("health_check")
metrics_collector = get_metrics_collector()

# 安全加固：HTTPBearer认证（auto_error=False允许公开端点不需要认证）
security = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="/health",  # 注意：main.py会添加/api前缀
    tags=["health"]
)


# ============================================================================
# 安全加固：敏感信息过滤函数
# Requirements 9.3: 不暴露数据库连接字符串、API密钥等敏感信息
# ============================================================================

def _filter_sensitive_data(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    过滤敏感信息
    
    安全加固：Requirements 9.3
    过滤数据库连接字符串、API密钥、密码等敏感信息
    
    Args:
        data: 需要过滤的数据（字典、列表或其他类型）
        
    Returns:
        过滤后的数据，敏感字段值替换为 '[REDACTED]'
    """
    # 敏感关键字列表（不区分大小写）
    sensitive_keys = [
        'password', 'secret', 'key', 'token', 
        'credential', 'auth', 'connection_string',
        'api_key', 'apikey', 'private_key', 'privatekey',
        'access_token', 'refresh_token', 'jwt',
        'mysql_password', 'neo4j_password', 'redis_password',
        'qdrant_api_key', 'deepseek_api_key', 'encryption_key'
    ]
    
    def _is_sensitive_key(key: str) -> bool:
        """检查键名是否为敏感键"""
        key_lower = str(key).lower()
        return any(sensitive in key_lower for sensitive in sensitive_keys)
    
    def _filter_value(value: Any) -> Any:
        """递归过滤值"""
        if isinstance(value, dict):
            return {
                k: '[REDACTED]' if _is_sensitive_key(k) else _filter_value(v)
                for k, v in value.items()
            }
        elif isinstance(value, list):
            return [_filter_value(item) for item in value]
        elif isinstance(value, str):
            # 检查字符串值是否包含敏感模式（如连接字符串）
            value_lower = value.lower()
            if any(pattern in value_lower for pattern in ['password=', 'secret=', 'key=', 'token=']):
                return '[REDACTED]'
            return value
        return value
    
    return _filter_value(data)


def _verify_admin_token(credentials: Optional[HTTPAuthorizationCredentials]) -> bool:
    """
    验证管理员Token
    
    安全加固：Requirements 9.2
    详细端点需要管理员认证
    
    Args:
        credentials: HTTP Bearer认证凭证
        
    Returns:
        bool: Token是否有效
    """
    if not credentials:
        return False
    
    token = credentials.credentials
    if not token:
        return False
    
    try:
        # 获取JWT密钥
        jwt_secret = os.getenv('JWT_SECRET', '')
        if not jwt_secret:
            structured_logger.warning(
                "JWT_SECRET未配置",
                component="health_auth",
                security_warning="JWT_SECRET not configured for admin verification"
            )
            return False
        
        # 解码并验证Token
        payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        
        # 检查是否为管理员角色
        role = payload.get('role', '')
        if role == 'admin':
            return True
        
        # 检查用户ID是否为管理员（user_id=1通常是管理员）
        user_id = payload.get('sub') or payload.get('user_id')
        if user_id == 1 or user_id == '1':
            return True
        
        return False
        
    except jwt.ExpiredSignatureError:
        structured_logger.warning(
            "管理员Token已过期",
            component="health_auth"
        )
        return False
    except jwt.InvalidTokenError as e:
        structured_logger.warning(
            "无效的管理员Token",
            component="health_auth",
            error=str(e)[:100]
        )
        return False
    except Exception as e:
        structured_logger.error(
            "Token验证异常",
            component="health_auth",
            error=str(e)[:100]
        )
        return False


@router.get("/")
async def public_health_check():
    """
    公开健康检查端点
    
    安全加固：Requirements 9.1, 9.3
    仅返回基本状态，不暴露敏感信息
    
    Returns:
        dict: 基本健康状态
            - status: healthy, unhealthy, degraded
            - timestamp: 检查时间
    """
    # 注意：健康检查API不记录INFO日志，避免日志膨胀
    # 只在出错时记录ERROR日志
    try:
        start_time = asyncio.get_event_loop().time()

        # 快速检查核心组件状态（不返回详细信息）
        try:
            components = await _check_all_components()
            metrics = await _get_system_metrics()
            overall_status = _calculate_overall_status(components, metrics)
        except Exception:
            overall_status = "degraded"

        processing_time = asyncio.get_event_loop().time() - start_time
        
        # 记录指标（不记录日志）
        try:
            metrics_collector.get_metric("request_duration_seconds").observe(
                processing_time,
                labels={"endpoint": "/health", "method": "GET", "status": "200"}
            )
            metrics_collector.get_metric("requests_total").inc(
                labels={"endpoint": "/health", "method": "GET", "status": "200"}
            )
        except Exception:
            pass  # 指标收集失败不影响健康检查

        # 安全加固：仅返回基本状态和时间戳
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 只记录错误日志
        structured_logger.error(
            "健康检查失败",
            error=str(e),
            component="health_check"
        )
        
        # 记录错误指标
        try:
            metrics_collector.get_metric("errors_total").inc(
                labels={"error_type": "health_check_error", "component": "health_check"}
            )
        except Exception:
            pass
        
        # 安全加固：错误时也只返回基本信息，不暴露错误详情
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat()
        }


@router.get("/detailed", response_model=ApiResponse[HealthResponse])
async def detailed_health_check(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    详细健康检查（需要管理员认证）
    
    安全加固：Requirements 9.2
    检查所有核心组件的状态，返回整体系统健康状况。
    
    Returns:
        ApiResponse[HealthResponse]: 系统健康状态（过滤敏感信息）
            - status: healthy, unhealthy, degraded
            - version: 系统版本
            - components: 各组件状态
            - metrics: 性能指标
            - auth_enabled: 认证是否启用
    """
    # 安全加固：验证管理员Token
    if not _verify_admin_token(credentials):
        raise HTTPException(
            status_code=401, 
            detail="Authentication required - Admin access only"
        )
    
    try:
        start_time = asyncio.get_event_loop().time()

        # 1. 基础信息
        version = "2.2.0"
        timestamp = datetime.now()
        
        # 获取认证启用状态（安全加固：Requirements 6.4）
        auth_enabled = os.getenv('ENABLE_AUTH', 'false').lower() == 'true'

        # 2. 检查各组件状态
        components = await _check_all_components()

        # 3. 获取性能指标
        metrics = await _get_system_metrics()

        # 4. 计算整体状态
        overall_status = _calculate_overall_status(components, metrics)

        # 5. 安全加固：过滤敏感信息
        filtered_components = _filter_sensitive_data(components)
        filtered_metrics = _filter_sensitive_data(metrics)

        # 6. 构建响应
        health_response = HealthResponse(
            status=overall_status,
            version=version,
            timestamp=timestamp,
            components=filtered_components,
            metrics=filtered_metrics,
            auth_enabled=auth_enabled
        )

        processing_time = asyncio.get_event_loop().time() - start_time
        
        # 记录指标
        metrics_collector.get_metric("request_duration_seconds").observe(
            processing_time,
            labels={"endpoint": "/health/detailed", "method": "GET", "status": "200"}
        )
        metrics_collector.get_metric("requests_total").inc(
            labels={"endpoint": "/health/detailed", "method": "GET", "status": "200"}
        )

        return ApiResponse.success(
            data=health_response,
            msg="系统健康检查完成"
        )

    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(
            "详细健康检查失败",
            error=str(e),
            component="health_check"
        )
        
        metrics_collector.get_metric("errors_total").inc(
            labels={"error_type": "health_check_error", "component": "health_check"}
        )
        
        return ApiResponse.error(
            code=500,
            msg="健康检查失败"  # 安全加固：不暴露错误详情
        )


@router.get("/components")
async def components_health(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    组件详细状态检查（需要管理员认证）
    
    安全加固：Requirements 9.2, 9.3
    返回各个组件的详细健康状态信息，过滤敏感数据。

    Returns:
        ApiResponse: 组件状态详情（过滤敏感信息）
    """
    # 安全加固：验证管理员Token
    if not _verify_admin_token(credentials):
        raise HTTPException(
            status_code=401, 
            detail="Authentication required - Admin access only"
        )
    
    try:
        components = await _check_all_components()

        # 添加组件详细信息
        for component_name, component_status in components.items():
            # 为每个组件添加详细信息
            if component_name == "daml_rag_framework":
                component_status.update(await _check_daml_rag_details())
            elif component_name == "three_layer_retrieval":
                component_status.update(await _check_three_layer_details())
            elif component_name == "databases":
                component_status.update(await _check_database_details())

        # 安全加固：过滤敏感信息
        filtered_components = _filter_sensitive_data(components)

        return ApiResponse.success(
            data=filtered_components,
            msg="组件状态检查完成"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"组件状态检查失败: {e}", exc_info=True)
        return ApiResponse.error(
            code=500,
            msg="组件状态检查失败"  # 安全加固：不暴露错误详情
        )


@router.get("/metrics")
async def system_metrics(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    系统性能指标（需要管理员认证）
    
    安全加固：Requirements 9.2, 9.3
    返回详细的性能监控数据，过滤敏感信息。

    Returns:
        ApiResponse: 性能指标数据（过滤敏感信息）
    """
    # 安全加固：验证管理员Token
    if not _verify_admin_token(credentials):
        raise HTTPException(
            status_code=401, 
            detail="Authentication required - Admin access only"
        )
    
    try:
        metrics = await _get_system_metrics()
        
        # 添加收集的指标
        collected_metrics = {}
        for name, metric in metrics_collector.get_all_metrics().items():
            snapshot = metric.get_snapshot()
            if snapshot:
                collected_metrics[name] = {
                    "type": snapshot.metric_type.value,
                    "value": snapshot.value,
                    "timestamp": snapshot.timestamp,
                    "labels": snapshot.labels
                }
        
        metrics["collected_metrics"] = collected_metrics

        # 安全加固：过滤敏感信息
        filtered_metrics = _filter_sensitive_data(metrics)

        return ApiResponse.success(
            data=filtered_metrics,
            msg="性能指标获取完成"
        )

    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(
            "性能指标获取失败",
            error=str(e),
            component="metrics"
        )
        
        return ApiResponse.error(
            code=500,
            msg="性能指标获取失败"  # 安全加固：不暴露错误详情
        )


@router.get("/metrics/prometheus")
async def prometheus_metrics(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Prometheus格式指标（需要管理员认证）
    
    安全加固：Requirements 9.2, 9.3
    返回Prometheus格式的性能指标，包括：
    - 系统基础指标（CPU、内存、请求等）
    - 流式输出指标（TTFB、生成速度、成功率等）

    Returns:
        str: Prometheus格式文本（过滤敏感信息）
    """
    from fastapi.responses import PlainTextResponse
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    # 安全加固：验证管理员Token
    if not _verify_admin_token(credentials):
        raise HTTPException(
            status_code=401, 
            detail="Authentication required - Admin access only"
        )
    
    try:
        # 导出所有Prometheus指标（包括streaming_metrics.py中定义的指标）
        prometheus_bytes = generate_latest()
        prometheus_text = prometheus_bytes.decode('utf-8')
        
        # 同时包含metrics_collector的指标
        try:
            custom_metrics = metrics_collector.export_prometheus()
            prometheus_text += "\n" + custom_metrics
        except Exception as e:
            structured_logger.warning(
                "自定义指标导出失败",
                error=str(e),
                component="metrics"
            )
        
        return PlainTextResponse(
            content=prometheus_text,
            media_type=CONTENT_TYPE_LATEST
        )
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(
            "Prometheus指标导出失败",
            error=str(e),
            component="metrics"
        )
        return PlainTextResponse(
            content="# Error exporting metrics",  # 安全加固：不暴露错误详情
            status_code=500
        )


@router.get("/metrics/streaming")
async def streaming_metrics(
    time_window: int = 3600,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    流式输出监控指标（需要管理员认证）
    
    安全加固：Requirements 9.2, 9.3
    返回流式输出的性能统计数据。

    Args:
        time_window: 时间窗口（秒），默认1小时

    Returns:
        ApiResponse: 流式监控统计数据（过滤敏感信息）
            - total_sessions: 总会话数
            - success_rate: 成功率
            - avg_ttfb_ms: 平均首字节响应时间
            - avg_duration_ms: 平均总耗时
            - avg_tokens_per_second: 平均生成速度
            - error_distribution: 错误分布
    """
    # 安全加固：验证管理员Token
    if not _verify_admin_token(credentials):
        raise HTTPException(
            status_code=401, 
            detail="Authentication required - Admin access only"
        )
    
    try:
        from ...framework.monitoring.streaming_metrics import streaming_monitor
        
        # 获取统计数据
        statistics = streaming_monitor.get_statistics(time_window_seconds=time_window)
        
        # 安全加固：过滤敏感信息
        filtered_statistics = _filter_sensitive_data(statistics)
        
        return ApiResponse.success(
            data=filtered_statistics,
            msg="流式监控指标获取完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(
            "流式监控指标获取失败",
            error=str(e),
            component="streaming_metrics"
        )
        
        return ApiResponse.error(
            code=500,
            msg="流式监控指标获取失败"  # 安全加固：不暴露错误详情
        )


@router.get("/metrics/streaming/recent")
async def recent_streaming_metrics(
    limit: int = 100,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    最近的流式会话记录（需要管理员认证）
    
    安全加固：Requirements 9.2, 9.3
    返回最近的流式会话详细记录，过滤敏感信息。

    Args:
        limit: 返回的最大记录数，默认100

    Returns:
        ApiResponse: 流式会话记录列表（过滤敏感信息）
    """
    # 安全加固：验证管理员Token
    if not _verify_admin_token(credentials):
        raise HTTPException(
            status_code=401, 
            detail="Authentication required - Admin access only"
        )
    
    try:
        from ...framework.monitoring.streaming_metrics import streaming_monitor
        
        # 获取最近的记录
        recent_metrics = streaming_monitor.get_recent_metrics(limit=limit)
        
        # 安全加固：过滤敏感信息
        filtered_metrics = _filter_sensitive_data(recent_metrics)
        
        return ApiResponse.success(
            data={
                "metrics": filtered_metrics,
                "count": len(recent_metrics),
                "limit": limit
            },
            msg=f"获取到{len(recent_metrics)}条流式会话记录"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(
            "获取流式会话记录失败",
            error=str(e),
            component="streaming_metrics"
        )
        
        return ApiResponse.error(
            code=500,
            msg="获取流式会话记录失败"  # 安全加固：不暴露错误详情
        )


async def _check_all_components() -> Dict[str, Any]:
    """检查所有组件状态"""
    components = {}

    # 1. DAML-RAG框架状态
    components["daml_rag_framework"] = await _check_daml_rag_framework()

    # 2. 三层检索组件状态
    components["three_layer_retrieval"] = await _check_three_layer_retrieval()

    # 3. 字段标准化器状态
    components["field_standardizer"] = await _check_field_standardizer()

    # 4. 反幻觉系统状态
    components["anti_hallucination"] = await _check_anti_hallucination()

    # 5. 数据库连接状态
    components["databases"] = await _check_databases()

    # 6. API接口状态
    components["api_endpoints"] = await _check_api_endpoints()

    return components


async def _check_daml_rag_framework() -> Dict[str, Any]:
    """检查DAML-RAG框架状态"""
    try:
        from ...framework.core.simple_framework_initializer import get_framework_initializer

        # 获取框架初始化器实例
        initializer = get_framework_initializer()
        
        if initializer is None:
            return {
                "status": "unhealthy",
                "initialized": False,
                "error": "Framework initializer not available",
                "last_check": datetime.now().isoformat()
            }

        # 检查框架是否已初始化（通过检查components属性）
        # SimpleFrameworkInitializer使用components字典存储已初始化的组件
        initialized = bool(initializer.components)

        if initialized:
            # 获取已初始化的组件信息
            component_names = list(initializer.components.keys())
            
            return {
                "status": "healthy",
                "initialized": True,
                "components": component_names,
                "component_count": len(component_names),
                "last_check": datetime.now().isoformat()
            }
        else:
            return {
                "status": "unhealthy",
                "initialized": False,
                "error": "Framework not initialized",
                "last_check": datetime.now().isoformat()
            }

    except ImportError as e:
        return {
            "status": "unhealthy",
            "initialized": False,
            "error": f"Import error: {str(e)}",
            "last_check": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "initialized": False,
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


async def _check_three_layer_retrieval() -> Dict[str, Any]:
    """检查三层检索组件状态"""
    components = {
        "semantic_search": False,
        "graph_reasoning": False,
        "business_constraints": False,
        "fusion_engine": False,
        "fitness_specific": False
    }

    try:
        # 检查框架初始化器中的组件
        from ...framework.core.simple_framework_initializer import get_framework_initializer
        
        initializer = get_framework_initializer()
        if initializer and initializer.components:
            framework_components = initializer.components
            
            # 检查知识图谱组件（包含向量搜索和图推理）
            if framework_components.get("kg_full"):
                components["semantic_search"] = True
                components["graph_reasoning"] = True
                components["fusion_engine"] = True
            
            # 检查MCP客户端（业务约束通过MCP工具实现）
            if framework_components.get("mcp_client"):
                components["business_constraints"] = True
            
            # 检查健身特定组件（领域适配器）
            if framework_components.get("domain_adapter"):
                components["fitness_specific"] = True

        # 计算整体状态
        healthy_count = sum(1 for v in components.values() if v is True)
        total_count = len(components)
        status = "healthy" if healthy_count == total_count else "degraded" if healthy_count > 0 else "unhealthy"

        return {
            "status": status,
            "components": components,
            "healthy_ratio": f"{healthy_count}/{total_count}",
            "last_check": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "components": components,
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


async def _check_field_standardizer() -> Dict[str, Any]:
    """检查字段标准化器状态"""
    try:
        # v3.0架构中，字段标准化通过知识图谱和MCP工具实现
        from ...framework.core.simple_framework_initializer import get_framework_initializer
        
        initializer = get_framework_initializer()
        if initializer and initializer.components:
            # 知识图谱提供字段标准化能力
            if initializer.components.get("kg_full"):
                return {
                    "status": "healthy",
                    "available": True,
                    "implementation": "knowledge_graph_based",
                    "supported_types": [
                        "exercise",
                        "muscle",
                        "equipment",
                        "food"
                    ],
                    "last_check": datetime.now().isoformat()
                }

        return {
            "status": "degraded",
            "available": False,
            "error": "Knowledge graph not initialized",
            "last_check": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "available": False,
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


async def _check_anti_hallucination() -> Dict[str, Any]:
    """检查反幻觉系统状态"""
    try:
        # v3.0架构中，反幻觉通过DAG模板和Layer3约束实现
        from ...framework.core.simple_framework_initializer import get_framework_initializer
        
        initializer = get_framework_initializer()
        if initializer and initializer.components:
            # 知识图谱和MCP工具提供反幻觉能力
            kg_available = initializer.components.get("kg_full") is not None
            mcp_available = initializer.components.get("mcp_client") is not None
            
            if kg_available and mcp_available:
                return {
                    "status": "healthy",
                    "available": True,
                    "implementation": "dag_template_based",
                    "layers": [
                        "knowledge_graph_validation",
                        "layer3_constraints",
                        "mcp_tool_verification"
                    ],
                    "last_check": datetime.now().isoformat()
                }
            elif kg_available or mcp_available:
                return {
                    "status": "degraded",
                    "available": True,
                    "implementation": "partial",
                    "kg_available": kg_available,
                    "mcp_available": mcp_available,
                    "last_check": datetime.now().isoformat()
                }

        return {
            "status": "degraded",
            "available": False,
            "error": "Framework components not initialized",
            "last_check": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "available": False,
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


async def _check_databases() -> Dict[str, Any]:
    """检查数据库连接状态"""
    databases = {
        "neo4j": "unknown",
        "qdrant": "unknown",
        "mysql": "unknown",
        "redis": "unknown"
    }

    try:
        # Neo4j检查
        try:
            from neo4j import GraphDatabase
            neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
            neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
            neo4j_password = os.getenv('NEO4J_PASSWORD', 'build_body_2024')

            driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password),
                max_connection_lifetime=5
            )
            with driver.session() as session:
                session.run("RETURN 1").single()
            driver.close()
            databases["neo4j"] = "connected"
        except Exception as e:
            databases["neo4j"] = f"error: {str(e)[:50]}"

        # Qdrant检查
        try:
            from qdrant_client import QdrantClient
            qdrant_host = os.getenv('QDRANT_HOST', 'qdrant')
            qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
            qdrant_api_key = os.getenv('QDRANT_API_KEY', '')
            qdrant_https = os.getenv('QDRANT_HTTPS', 'false').lower() == 'true'
            
            # 使用Qdrant客户端检查连接（支持API Key认证，显式禁用HTTPS）
            client = QdrantClient(
                host=qdrant_host,
                port=qdrant_port,
                api_key=qdrant_api_key if qdrant_api_key else None,
                https=qdrant_https,  # 显式设置HTTPS，默认禁用
                timeout=5
            )
            # 获取集合列表来验证连接
            collections = client.get_collections()
            databases["qdrant"] = "connected"
        except Exception as e:
            databases["qdrant"] = f"error: {str(e)[:50]}"

        # MySQL检查
        try:
            import pymysql
            mysql_host = os.getenv('MYSQL_HOST', 'mysql')
            mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
            mysql_user = os.getenv('MYSQL_USER', 'root')
            mysql_password = os.getenv('MYSQL_PASSWORD', 'build_body_2024')
            mysql_db = os.getenv('MYSQL_DATABASE', 'fitness_app')
            
            conn = pymysql.connect(
                host=mysql_host,
                port=mysql_port,
                user=mysql_user,
                password=mysql_password,
                database=mysql_db,
                connect_timeout=5
            )
            conn.ping()
            conn.close()
            databases["mysql"] = "connected"
        except Exception as e:
            databases["mysql"] = f"error: {str(e)[:50]}"

        # Redis检查（安全加固：Requirements 8.3, 8.4）
        try:
            import redis
            redis_host = os.getenv('REDIS_HOST', 'redis')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_password = os.getenv('REDIS_PASSWORD', '')
            
            # 安全加固：记录Redis密码配置状态
            if not redis_password:
                structured_logger.warning(
                    "Redis连接未配置密码",
                    component="redis",
                    host=redis_host,
                    port=redis_port,
                    security_warning="Redis connection without password authentication"
                )
            
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password if redis_password else None,
                socket_timeout=5
            )
            r.ping()
            databases["redis"] = "connected"
        except redis.AuthenticationError as auth_error:
            # 安全加固：认证失败时记录警告日志（Requirements 8.4）
            structured_logger.warning(
                "Redis认证失败",
                component="redis",
                host=redis_host,
                port=redis_port,
                error=str(auth_error)[:100],
                security_warning="Redis authentication failed - check REDIS_PASSWORD configuration"
            )
            databases["redis"] = "auth_error"
        except redis.ConnectionError as conn_error:
            structured_logger.warning(
                "Redis连接失败",
                component="redis",
                host=redis_host,
                port=redis_port,
                error=str(conn_error)[:100]
            )
            databases["redis"] = f"connection_error: {str(conn_error)[:30]}"
        except Exception as e:
            databases["redis"] = f"error: {str(e)[:50]}"

        # 计算数据库整体状态
        connected_count = sum(1 for status in databases.values() if status == "connected")
        total_count = len(databases)
        status = "healthy" if connected_count >= 2 else "degraded" if connected_count > 0 else "unhealthy"

        return {
            "status": status,
            "connections": databases,
            "connected_ratio": f"{connected_count}/{total_count}",
            "last_check": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "connections": databases,
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


async def _check_api_endpoints() -> Dict[str, Any]:
    """检查API接口状态"""
    endpoints = {
        "/api/graphrag/query": "available",
        "/api/v1/chat": "available",
        "/api/feedback/submit": "available",
        "/api/health": "available"
    }

    # 检查各接口是否可访问（简化版）
    # 在实际环境中，可以发送测试请求来验证

    return {
        "status": "healthy",
        "endpoints": endpoints,
        "total_endpoints": len(endpoints),
        "last_check": datetime.now().isoformat()
    }


async def _get_system_metrics() -> Dict[str, Any]:
    """获取系统性能指标"""
    try:
        # 系统资源指标
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Python进程指标
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()

        return {
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "disk_percent": round(disk.percent, 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2)
            },
            "process": {
                "cpu_percent": round(process_cpu, 2),
                "memory_mb": round(process_memory.rss / (1024**2), 2),
                "memory_vms_mb": round(process_memory.vms / (1024**2), 2),
                "num_threads": process.num_threads(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
            },
            "performance": {
                "response_time_avg": "0.85s",  # 模拟数据
                "requests_per_minute": 15,     # 模拟数据
                "error_rate": "2.3%"           # 模拟数据
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.warning(f"获取性能指标失败: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _calculate_overall_status(components: Dict[str, Any], metrics: Dict[str, Any]) -> str:
    """计算整体系统状态"""
    try:
        # 基于组件状态计算
        component_statuses = [comp.get("status", "unhealthy") for comp in components.values()]
        healthy_count = sum(1 for status in component_statuses if status == "healthy")
        total_count = len(component_statuses)

        if healthy_count == total_count:
            component_status = "healthy"
        elif healthy_count >= total_count * 0.7:
            component_status = "degraded"
        else:
            component_status = "unhealthy"

        # 基于系统资源检查
        cpu_percent = metrics.get("system", {}).get("cpu_percent", 0)
        memory_percent = metrics.get("system", {}).get("memory_percent", 0)

        if cpu_percent > 90 or memory_percent > 90:
            resource_status = "unhealthy"
        elif cpu_percent > 70 or memory_percent > 70:
            resource_status = "degraded"
        else:
            resource_status = "healthy"

        # 综合判断
        if component_status == "healthy" and resource_status == "healthy":
            return "healthy"
        elif component_status == "unhealthy" or resource_status == "unhealthy":
            return "unhealthy"
        else:
            return "degraded"

    except Exception:
        return "unknown"


async def _check_daml_rag_details() -> Dict[str, Any]:
    """获取DAML-RAG框架详细信息"""
    try:
        from ...framework.core.simple_framework_initializer import get_framework_initializer
        initializer = get_framework_initializer()
        if initializer and initializer.components:
            return {
                "framework_metrics": {
                    "initialized": True,
                    "component_count": len(initializer.components),
                    "components": list(initializer.components.keys())
                }
            }
        return {"framework_metrics": {"initialized": False}}
    except Exception as e:
        return {"framework_metrics": {"error": str(e)}}


async def _check_three_layer_details() -> Dict[str, Any]:
    """获取三层检索详细信息"""
    try:
        from ...tools.graphrag_query import _get_graphrag_tool
        tool = _get_graphrag_tool()
        stats = tool.get_stats()
        return {"retrieval_stats": stats}
    except Exception:
        return {"retrieval_stats": {}}


async def _check_database_details() -> Dict[str, Any]:
    """获取数据库详细信息"""
    try:
        # 这里可以添加更详细的数据库检查
        return {"database_details": "detailed_check_not_implemented"}
    except Exception:
        return {"database_details": {}}


# 导出路由
__all__ = ['router']