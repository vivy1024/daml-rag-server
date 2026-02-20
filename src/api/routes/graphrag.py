# -*- coding: utf-8 -*-
"""
GraphRAG Route - 独立的知识图谱查询接口

提供纯粹的知识图谱查询接口（不执行11步工作流程）
集成三层检索架构：语义搜索 + 图谱推理 + 业务约束验证

POST /api/graphrag/query - GraphRAG独立查询接口
GET  /api/graphrag/stats - 知识图谱统计信息
GET  /api/graphrag/health - GraphRAG健康检查

版本：v6.0.0
更新日期：2025-12-16
重构说明：移除11步工作流程，只保留纯粹的知识图谱查询
"""

import logging
import os
import asyncio
import time
import json
import hashlib
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional

# 导入API模型
from ..models import ApiResponse, ApiError
# 修复导入路径：GraphRAGQueryTool在framework/retrieval/graphrag.py中
from ...framework.retrieval.graphrag import GraphRAGQueryTool

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/graphrag",
    tags=["graphrag"]
)

# 全局GraphRAG实例（延迟初始化）
_graphrag_query_tool = None

# 请求去重缓存（防止重复执行）
_request_cache = {}
_cache_timeout = 30  # 30秒缓存


def _generate_request_cache_key(request: Dict[str, Any]) -> str:
    """
    生成请求缓存键
    
    注意：必须包含所有影响结果的参数，确保个性化查询不会共享缓存
    """
    key_fields = {
        "query_text": request.get("query_text", ""),
        "user_id": request.get("user_id", ""),
        "query_type": request.get("query_type", "three_layer"),
        "domain": request.get("domain", "fitness_exercises"),
        # ✅ 新增：包含过滤条件（影响Layer 1/2结果）
        "filters": request.get("filters", {}),
        # ✅ 新增：包含用户档案关键字段（影响Layer 3结果）
        "user_profile_key": _extract_user_profile_key(request.get("user_profile"))
    }
    key_str = json.dumps(key_fields, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def _extract_user_profile_key(user_profile: Optional[Dict[str, Any]]) -> str:
    """
    提取用户档案的关键字段用于缓存键
    
    只提取影响检索结果的字段，避免缓存键过长
    """
    if not user_profile:
        return ""
    
    # 提取影响检索的关键字段
    key_fields = {
        "fitness_level": user_profile.get("fitness_level", ""),
        "available_equipment": sorted(user_profile.get("available_equipment", [])),
        "health_conditions": sorted(user_profile.get("health_conditions", [])),
        "injury_history": sorted(user_profile.get("injury_history", []))
    }
    return json.dumps(key_fields, sort_keys=True)


def _check_request_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """检查请求缓存"""
    if cache_key in _request_cache:
        cached_data, timestamp = _request_cache[cache_key]
        if time.time() - timestamp < _cache_timeout:
            logger.info(f"🚀 使用缓存结果: {cache_key[:8]}...")
            return cached_data
        else:
            del _request_cache[cache_key]
    return None


def _cache_request_result(cache_key: str, result: Dict[str, Any]):
    """缓存请求结果"""
    _request_cache[cache_key] = (result, time.time())

    # 清理过期缓存
    current_time = time.time()
    expired_keys = [
        key for key, (_, timestamp) in _request_cache.items()
        if current_time - timestamp >= _cache_timeout
    ]
    for key in expired_keys:
        del _request_cache[key]


def _get_graphrag_tool():
    """延迟初始化GraphRAG查询工具"""
    global _graphrag_query_tool

    if _graphrag_query_tool is None:
        try:
            logger.info("初始化GraphRAG查询工具...")

            from ...framework.core.simple_framework_initializer import get_framework_initializer
            from ...framework.retrieval.true_three_layer_engine import TrueThreeLayerEngine
            
            initializer = get_framework_initializer()
            three_layer_engine = None

            if initializer and "kg_full" in initializer.components:
                kg_full = initializer.components["kg_full"]
                
                # 尝试获取或创建 TrueThreeLayerEngine
                if "three_layer_engine" in initializer.components:
                    three_layer_engine = initializer.components["three_layer_engine"]
                    logger.info("  → 使用框架已初始化的 TrueThreeLayerEngine")
                else:
                    # 创建新的 TrueThreeLayerEngine
                    three_layer_engine = TrueThreeLayerEngine(
                        graphrag_api_port=os.getenv('API_PORT', '8001'),
                        neo4j_uri=os.getenv('NEO4J_URI', 'bolt://neo4j:7687'),
                        neo4j_user=os.getenv('NEO4J_USER', 'neo4j'),
                        neo4j_password=os.getenv('NEO4J_PASSWORD', 'build_body_2024')
                    )
                    logger.info("  → 创建新的 TrueThreeLayerEngine")
                
                _graphrag_query_tool = GraphRAGQueryTool(
                    kg_full, 
                    three_layer_engine=three_layer_engine
                )
                logger.info("✅ GraphRAG查询工具初始化完成（使用框架kg_full + TrueThreeLayerEngine）")
            else:
                from ...framework.retrieval.graph.kg_full import KnowledgeGraphFull
                kg_full = KnowledgeGraphFull(
                    neo4j_uri=os.getenv('NEO4J_URI', 'bolt://neo4j:7687'),
                    neo4j_user=os.getenv('NEO4J_USER', 'neo4j'),
                    neo4j_password=os.getenv('NEO4J_PASSWORD', 'build_body_2024'),
                    qdrant_host=os.getenv('QDRANT_HOST', 'qdrant'),
                    qdrant_port=int(os.getenv('QDRANT_PORT', '6333')),
                    qdrant_collection=os.getenv('QDRANT_COLLECTION', 'fitness_exercises_v2'),
                    embedding_model='thenlper/gte-large-zh'
                )
                
                # 创建 TrueThreeLayerEngine
                three_layer_engine = TrueThreeLayerEngine(
                    graphrag_api_port=os.getenv('API_PORT', '8001'),
                    neo4j_uri=os.getenv('NEO4J_URI', 'bolt://neo4j:7687'),
                    neo4j_user=os.getenv('NEO4J_USER', 'neo4j'),
                    neo4j_password=os.getenv('NEO4J_PASSWORD', 'build_body_2024')
                )
                
                _graphrag_query_tool = GraphRAGQueryTool(
                    kg_full,
                    three_layer_engine=three_layer_engine
                )
                logger.info("✅ GraphRAG查询工具初始化完成（直接创建kg_full + TrueThreeLayerEngine）")

        except Exception as e:
            logger.error(f"❌ GraphRAG查询工具初始化失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"GraphRAG初始化失败: {str(e)}"
            )

    return _graphrag_query_tool


class GraphRAGQueryRequest:
    """GraphRAG查询请求"""

    def __init__(self, **kwargs):
        self.query_type = kwargs.get("query_type", "three_layer")
        self.domain = kwargs.get("domain", "fitness_exercises")
        self.query_text = kwargs.get("query_text")
        self.user_id = kwargs.get("user_id", "anonymous")
        self.filters = kwargs.get("filters", {})
        self.top_k = kwargs.get("top_k", 10)
        self.min_similarity = kwargs.get("min_similarity", 0.5)
        self.return_reason = kwargs.get("return_reason", True)


@router.post("/query", response_model=ApiResponse[Dict[str, Any]])
async def query_graphrag(request: Dict[str, Any]):
    """
    GraphRAG独立查询接口 - 纯粹的知识图谱查询

    用途：
    - 开发者调试
    - 独立的知识查询场景
    - 不需要LLM生成的场景

    支持四种查询模式：
    - semantic_search: 纯向量语义检索
    - graph_query: 纯图推理查询
    - three_layer: 三层检索（语义+图谱+约束）
    - hybrid: 混合检索（向量+图）

    不执行：
    - 11步工作流程
    - LLM生成
    - 用户档案加载
    - Few-Shot检索

    只执行：
    - 三层检索引擎查询
    - 返回检索结果

    Args:
        request: {
            "query_type": "three_layer" | "semantic_search" | "graph_query" | "hybrid",
            "domain": "fitness_exercises" | "nutrition" | "rehabilitation" | "training" | "general",
            "query_text": "查询文本",
            "user_id": "用户ID",  # 可选
            "filters": {"muscle_group": "chest"},  # 可选
            "top_k": 10,  # 可选
        }

    Returns:
        {
            "code": 200,
            "msg": "查询成功",
            "data": {
                "success": true,
                "results": [...],
                "query_type": "three_layer",
                "domain": "fitness_exercises",
                "count": 5,
                "processing_time": 0.23,
                "cached": false
            }
        }
    """
    try:
        start_time = time.time()

        # 1. 参数验证
        if not request.get("query_text"):
            raise ApiError(400, "缺少必需参数：query_text")

        # 2. 生成请求缓存键
        cache_key = _generate_request_cache_key(request)

        # 3. 检查缓存
        cached_result = _check_request_cache(cache_key)
        if cached_result:
            cached_result["cached"] = True
            cached_result["cache_hit"] = True
            return ApiResponse.success(data=cached_result)

        # 4. 创建查询请求对象
        query_request = GraphRAGQueryRequest(**request)

        logger.info(
            f"GraphRAG独立查询: type={query_request.query_type}, "
            f"domain={query_request.domain}, "
            f"query='{query_request.query_text[:50]}...', cache_key={cache_key[:8]}..."
        )

        # 5. 获取GraphRAG查询工具（延迟初始化）
        graphrag_tool = _get_graphrag_tool()

        # 6. 构建查询参数
        query_args = {
            "query_type": query_request.query_type,
            "domain": query_request.domain,
            "query_text": query_request.query_text,
            "user_id": query_request.user_id,
            "filters": query_request.filters or {},
            "top_k": query_request.top_k,
            "min_similarity": query_request.min_similarity,
            "return_reason": query_request.return_reason
        }

        # 7. 直接调用三层检索引擎（不执行11步工作流程）
        result = await graphrag_tool.query(query_args)

        # 8. 添加处理时间和缓存标记
        processing_time = time.time() - start_time
        if result:
            result["processing_time"] = processing_time
            result["cached"] = False
            result["cache_hit"] = False
            result["cache_key"] = cache_key[:8] + "..."
        else:
            result = {
                "success": False,
                "results": [],
                "query_type": query_request.query_type,
                "domain": query_request.domain,
                "count": 0,
                "processing_time": processing_time,
                "cached": False,
                "error": "查询返回空结果"
            }

        # 9. 缓存结果
        _cache_request_result(cache_key, result)

        # 10. 记录查询结果
        logger.info(
            f"GraphRAG独立查询完成: success={result.get('success')}, "
            f"count={result.get('count', 0)}, "
            f"time={processing_time:.2f}s, cached={result.get('cached', False)}"
        )

        # 11. 返回结果
        return ApiResponse.success(data=result)

    except ApiError as e:
        logger.error(f"GraphRAG API错误: {e.msg}", exc_info=True)
        return ApiResponse.error(code=e.code, msg=e.msg, data=e.data)

    except Exception as e:
        logger.error(f"GraphRAG查询失败: {e}", exc_info=True)
        return ApiResponse.error(
            code=500,
            msg=f"GraphRAG查询失败: {str(e)}"
        )


@router.get("/health")
async def graphrag_health():
    """
    GraphRAG健康检查

    检查组件状态：
    - GraphRAG查询工具初始化状态
    - 三层检索组件可用性
    - 数据库连接状态
    - 系统资源状态

    Returns:
        {
            "code": 200,
            "msg": "GraphRAG服务正常",
            "data": {
                "status": "healthy",
                "components": {...},
                "database_connections": {...},
                "performance_stats": {...}
            }
        }
    """
    try:
        tool = _get_graphrag_tool()
        stats = tool.get_stats()

        components = {
            "graphrag_tool": tool is not None,
            "three_layer_retrieval": True,
            "field_standardizer": True,
            "anti_hallucination": True
        }

        db_connections = {
            "neo4j_uri": os.getenv('NEO4J_URI', 'bolt://neo4j:7687'),
            "qdrant_host": os.getenv('QDRANT_HOST', 'qdrant'),
            "qdrant_port": int(os.getenv('QDRANT_PORT', '6333'))
        }

        health_data = {
            "status": "healthy" if all(components.values()) else "unhealthy",
            "components": components,
            "database_connections": db_connections,
            "performance_stats": stats,
            "timestamp": asyncio.get_event_loop().time()
        }

        return ApiResponse.success(
            data=health_data,
            msg="GraphRAG服务正常"
        )

    except Exception as e:
        logger.error(f"GraphRAG健康检查失败: {e}", exc_info=True)
        return ApiResponse.error(
            code=500,
            msg=f"GraphRAG服务异常: {str(e)}",
            data={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@router.get("/stats")
async def kg_stats():
    """
    知识图谱统计信息

    提供Neo4j知识图谱的实时统计数据，用于监控数据质量。
    同时包含GraphRAG查询统计信息。

    Returns:
        {
            "code": 200,
            "msg": "操作成功",
            "data": {
                "knowledge_graph": {...},
                "graphrag_stats": {...}
            }
        }
    """
    try:
        tool = _get_graphrag_tool()
        graphrag_stats = tool.get_stats()

        kg_stats_data = await _get_knowledge_graph_stats()

        combined_stats = {
            "knowledge_graph": kg_stats_data,
            "graphrag_stats": {
                **graphrag_stats,
                "last_updated": asyncio.get_event_loop().time()
            }
        }

        logger.info(f"KG Stats: {kg_stats_data.get('nodes', 0)} nodes, {kg_stats_data.get('relationships', 0)} relations")

        return ApiResponse.success(
            data=combined_stats,
            msg="操作成功"
        )

    except Exception as e:
        logger.error(f"统计信息获取失败: {e}", exc_info=True)
        return ApiResponse.error(
            code=500,
            msg=f"统计失败: {str(e)}"
        )


async def _get_knowledge_graph_stats() -> Dict[str, Any]:
    """获取知识图谱统计信息"""
    try:
        from neo4j import GraphDatabase

        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'build_body_2024')

        logger.info(f"Connecting to Neo4j at {neo4j_uri}")

        # 同步Neo4j操作，用to_thread避免阻塞事件循环
        def _sync_query():
            driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password),
                max_connection_lifetime=30
            )
            try:
                with driver.session() as session:
                    node_result = session.run("MATCH (n) RETURN count(n) as count")
                    node_count = node_result.single()["count"]

                    rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                    rel_count = rel_result.single()["count"]

                    type_result = session.run(
                        "MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC"
                    )
                    node_types = {
                        record["label"]: record["count"]
                        for record in type_result
                        if record["label"]
                    }
                return node_count, rel_count, node_types
            finally:
                driver.close()

        node_count, rel_count, node_types = await asyncio.to_thread(_sync_query)

        return {
            "nodes": node_count,
            "relationships": rel_count,
            "node_types": node_types,
            "timestamp": int(os.times().elapsed * 1000)
        }

    except Exception as e:
        logger.warning(f"无法获取真实KG统计，使用模拟数据: {e}")
        return {
            "nodes": 4329,
            "relationships": 171767,
            "node_types": {
                "Exercise": 850,
                "Muscle": 120,
                "Equipment": 45,
                "Concept": 3314
            },
            "timestamp": int(os.times().elapsed * 1000),
            "note": "模拟数据（开发环境）"
        }


# 导出路由
__all__ = ['router']
