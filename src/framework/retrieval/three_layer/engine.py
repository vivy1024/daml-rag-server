# -*- coding: utf-8 -*-
"""
企业级三层检索引擎 - 主引擎类

基于GraphRAG v3简洁架构,增强Neo4j直接连接能力,实现真正的三层检索。

版本: v2.1.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import LayerExecutionResult, ThreeLayerResult
from .neo4j_manager import Neo4jConnectionManager
from .layer1_vector import Layer1VectorMixin
from .layer2_graph import Layer2GraphMixin
from .layer3_rules import Layer3RulesMixin
from .result_merger import ResultMergerMixin
from .fallback import FallbackMixin

from ...config.app_config import get_config
from ..timeout_manager import TimeoutManager, get_timeout_manager

logger = logging.getLogger(__name__)


class TrueThreeLayerEngine(
    ResultMergerMixin,
    Layer1VectorMixin,
    Layer2GraphMixin,
    FallbackMixin,
    Layer3RulesMixin,
):
    """
    企业级三层检索引擎

    核心特性:
    1. Layer 1: Qdrant向量检索 (通过GraphRAG API)
    2. Layer 2: Neo4j图谱推理 (直接连接 + API备份)
    3. Layer 3: 业务规则验证 (Python逻辑)

    设计亮点:
    - 连接池管理
    - 优雅降级
    - 并行执行
    - 完善监控
    """

    def __init__(
        self,
        graphrag_api_port: str = "8001",
        neo4j_uri: str = None,
        neo4j_user: str = None,
        neo4j_password: str = None,
        enable_neo4j_direct: bool = True,
        enable_parallel_execution: bool = False,
        connection_pool_manager=None,
        timeout_manager: Optional[TimeoutManager] = None,
        domain_adapter=None
    ):
        """初始化三层检索引擎"""
        config = get_config()
        # API配置
        self.graphrag_api_port = str(graphrag_api_port or config.api.port)
        self.graphrag_api_base = f"http://localhost:{self.graphrag_api_port}/api/graphrag"
        self._internal_api_token = config.internal.api_token

        # Neo4j配置
        self.neo4j_uri = neo4j_uri or config.database.neo4j.uri
        self.neo4j_user = neo4j_user or config.database.neo4j.user
        self.neo4j_password = neo4j_password or config.database.neo4j.password

        # 功能开关
        self.enable_neo4j_direct = enable_neo4j_direct
        self.enable_parallel_execution = enable_parallel_execution

        self.connection_pool_manager = connection_pool_manager
        self.timeout_manager = timeout_manager or get_timeout_manager()
        self.domain_adapter = domain_adapter

        # Neo4j连接管理器
        self.neo4j_manager: Optional[Neo4jConnectionManager] = None
        self.neo4j_available = False

        # 性能统计
        self.stats = {
            "total_queries": 0,
            "layer1_success": 0,
            "layer2_neo4j_direct": 0,
            "layer2_api_fallback": 0,
            "layer3_success": 0,
            "total_errors": 0,
            "timeout_count": 0
        }

        logger.info(f"三层检索引擎已创建 - GraphRAG API: {self.graphrag_api_base}")
        logger.info(f"  → 超时配置: Layer1={self.timeout_manager.get_timeout_ms('layer1_timeout_ms')}ms, "
                   f"Layer2={self.timeout_manager.get_timeout_ms('layer2_timeout_ms')}ms, "
                   f"Layer3={self.timeout_manager.get_timeout_ms('layer3_timeout_ms')}ms")
        if self.domain_adapter:
            logger.info(f"  → 领域适配器: {self.domain_adapter.get_name()}")

        if self.enable_neo4j_direct:
            self._initialize_neo4j_connection()

    def _initialize_neo4j_connection(self):
        """初始化Neo4j直连"""
        try:
            self.neo4j_manager = Neo4jConnectionManager(
                uri=self.neo4j_uri,
                user=self.neo4j_user,
                password=self.neo4j_password
            )

            if self.neo4j_manager.connect():
                self.neo4j_available = True
                logger.info("✅ Neo4j直连已启用")
            else:
                logger.warning("⚠️ Neo4j直连失败,将使用API降级")
                self.neo4j_available = False

        except Exception as e:
            logger.error(f"❌ Neo4j连接管理器初始化失败: {e}")
            self.neo4j_available = False

    async def execute_three_layer_query(
        self,
        query: str,
        domain: str = None,
        user_id: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        safety_check: bool = True,
        layer1_multiplier: int = 5
    ) -> ThreeLayerResult:
        """执行完整的三层检索"""
        start_time = datetime.now()
        self.stats["total_queries"] += 1

        if domain is None and self.domain_adapter:
            domain = self.domain_adapter.get_name()
        elif domain is None:
            domain = "general"

        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🔍 开始三层检索: {query}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        try:
            # Layer 1: 向量语义检索
            layer1_result = await self._execute_layer1_vector_search(
                query=query,
                domain=domain,
                top_k=top_k * layer1_multiplier,
                filters=filters,
                user_id=user_id
            )

            # Layer 1降级方案
            if not layer1_result.success or not layer1_result.results:
                logger.warning("⚠️ Layer 1失败，启动降级方案")

                logger.info("  → 降级方案1：尝试Layer 2图谱检索（无向量结果）")
                layer2_result = await self._execute_layer2_graph_reasoning_fallback(
                    query=query,
                    domain=domain,
                    top_k=top_k * 2,
                    user_id=user_id
                )

                if layer2_result.success and layer2_result.results:
                    logger.info(f"  ✓ Layer 2降级成功: {len(layer2_result.results)}个图谱结果")
                    candidates_for_layer3 = layer2_result.results
                else:
                    logger.warning("  ⚠️ Layer 2也失败，启动降级方案2：规则匹配")
                    rule_based_result = await self._execute_rule_based_fallback(
                        query=query,
                        user_profile=user_profile,
                        top_k=top_k * 2
                    )

                    if rule_based_result.success and rule_based_result.results:
                        logger.info(f"  ✓ 规则匹配成功: {len(rule_based_result.results)}个结果")
                        candidates_for_layer3 = rule_based_result.results
                        layer2_result = rule_based_result
                    else:
                        logger.error("  ✗ 所有降级方案均失败，返回空结果")
                        return self._build_final_result(
                            query=query,
                            domain=domain,
                            layer1=layer1_result,
                            layer2=layer2_result,
                            layer3=self._empty_layer_result("Layer3-Rules"),
                            start_time=start_time
                        )

                layer3_result = await self._execute_layer3_business_rules(
                    query=query,
                    candidates=candidates_for_layer3,
                    user_profile=user_profile,
                    top_k=top_k,
                    safety_check=safety_check
                )

                final_result = self._build_final_result(
                    query=query,
                    domain=domain,
                    layer1=layer1_result,
                    layer2=layer2_result,
                    layer3=layer3_result,
                    start_time=start_time
                )

                logger.info(f"✅ 降级检索完成: {len(final_result.final_results)}个结果, 耗时{final_result.total_execution_time_ms:.0f}ms")
                return final_result

            # Layer 2: 图谱关系推理
            knowledge_context = await self._fetch_knowledge_context(query)

            if layer1_result.metadata.get("is_low_quality", False):
                logger.info("  → Layer1质量偏低，Layer2增加召回倍数")
                layer2_top_k = top_k * 3
            else:
                layer2_top_k = top_k * 2

            layer2_result = await self._execute_layer2_graph_reasoning(
                query=query,
                domain=domain,
                vector_results=layer1_result.results,
                top_k=layer2_top_k,
                user_id=user_id,
                filters=filters
            )

            if layer2_result.success and layer2_result.results:
                candidates_for_layer3 = layer2_result.results
            else:
                logger.warning("Layer 2未返回结果,使用Layer 1结果")
                candidates_for_layer3 = layer1_result.results[:top_k * 2]

            # Layer 3: 业务规则验证
            layer3_result = await self._execute_layer3_business_rules(
                query=query,
                candidates=candidates_for_layer3,
                user_profile=user_profile,
                top_k=top_k,
                safety_check=safety_check
            )

            final_result = self._build_final_result(
                query=query,
                domain=domain,
                layer1=layer1_result,
                layer2=layer2_result,
                layer3=layer3_result,
                start_time=start_time,
                knowledge_context=knowledge_context
            )

            logger.info(f"✅ 三层检索完成: {len(final_result.final_results)}个结果, 耗时{final_result.total_execution_time_ms:.0f}ms")

            return final_result

        except Exception as e:
            logger.error(f"❌ 三层检索失败: {e}", exc_info=True)
            self.stats["total_errors"] += 1

            return ThreeLayerResult(
                query=query,
                domain=domain,
                final_results=[],
                layer_1_result=self._empty_layer_result("Layer1-Vector", error=str(e)),
                layer_2_result=self._empty_layer_result("Layer2-Graph"),
                layer_3_result=self._empty_layer_result("Layer3-Rules"),
                total_confidence=0.0,
                total_execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                reasoning=f"检索过程出错: {str(e)}",
                metadata={"error": str(e)}
            )

    async def execute_three_layer_search(
        self,
        query: str,
        domain: str = None,
        user_id: str = None,
        context: Dict[str, Any] = None
    ):
        """Framework层适配器方法"""
        if domain is None and self.domain_adapter:
            domain = self.domain_adapter.get_name()
        elif domain is None:
            domain = "general"

        user_profile = context.get("user_profile") if context else None
        filters = context.get("filters") if context else None
        top_k = context.get("top_k", 10) if context else 10
        safety_check = context.get("safety_check", True) if context else True

        return await self.execute_three_layer_query(
            query=query,
            domain=domain,
            user_id=user_id,
            user_profile=user_profile,
            filters=filters,
            top_k=top_k,
            safety_check=safety_check
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        stats = self.stats.copy()

        if stats["total_queries"] > 0:
            stats["success_rate"] = (stats["layer3_success"] / stats["total_queries"]) * 100
            stats["neo4j_direct_rate"] = (stats["layer2_neo4j_direct"] / stats["total_queries"]) * 100
            stats["api_fallback_rate"] = (stats["layer2_api_fallback"] / stats["total_queries"]) * 100
        else:
            stats["success_rate"] = 0
            stats["neo4j_direct_rate"] = 0
            stats["api_fallback_rate"] = 0

        stats["neo4j_available"] = self.neo4j_available

        return stats

    def close(self):
        """关闭引擎和所有连接"""
        if self.neo4j_manager:
            self.neo4j_manager.close()
        logger.info("三层检索引擎已关闭")
