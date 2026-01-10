# -*- coding: utf-8 -*-
"""
企业级三层检索引擎 - DAML-RAG框架核心组件

基于GraphRAG v3简洁架构,增强Neo4j直接连接能力,实现真正的三层检索。

三层架构:
- Layer 1: 向量语义检索 (Qdrant via GraphRAG API)
- Layer 2: 图谱关系推理 (Neo4j Direct Connection with Fallback)
- Layer 3: 专业规则约束 (Business Rules Engine)

设计原则:
1. 连接池管理 - 企业级Neo4j连接管理
2. 优雅降级 - Neo4j失败时自动降级到API
3. 清晰分层 - 每层职责明确,互不耦合
4. 完善监控 - 详细日志和性能指标
5. 统一超时 - 全局超时配置管理 (Requirements 3.6)

版本: v2.1.0
日期: 2026-01-11
作者: 薛小川
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import contextmanager
import aiohttp

# 导入超时管理器
from .timeout_manager import TimeoutManager, get_timeout_manager

logger = logging.getLogger(__name__)


# ============ 数据类定义 ============

@dataclass
class LayerExecutionResult:
    """单层检索执行结果"""
    layer_name: str
    success: bool
    results: List[Dict[str, Any]]
    execution_time_ms: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ThreeLayerResult:
    """三层检索最终结果"""
    query: str
    domain: str
    final_results: List[Dict[str, Any]]
    layer_1_result: LayerExecutionResult
    layer_2_result: LayerExecutionResult
    layer_3_result: LayerExecutionResult
    total_confidence: float
    total_execution_time_ms: float
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def final_recommendations(self) -> List[Dict[str, Any]]:
        """Framework层兼容性属性"""
        return self.final_results


# ============ Neo4j连接管理器 ============

class Neo4jConnectionManager:
    """
    企业级Neo4j连接管理器

    功能:
    1. 连接池管理
    2. 健康检查
    3. 自动重连
    4. 优雅关闭
    """

    def __init__(
        self,
        uri: str = "bolt://neo4j:7687",
        user: str = "neo4j",
        password: Optional[str] = None,
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
        connection_timeout: float = 30.0
    ):
        """初始化Neo4j连接管理器"""
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.is_connected = False
        self.last_health_check = None

        # 连接池配置
        self.config = {
            "max_connection_lifetime": max_connection_lifetime,
            "max_connection_pool_size": max_connection_pool_size,
            "connection_timeout": connection_timeout
        }

        logger.info(f"Neo4j连接管理器已创建 - URI: {uri}, User: {user}, Password: {'***' if password else 'None'}")

    def connect(self) -> bool:
        """建立Neo4j连接"""
        try:
            from neo4j import GraphDatabase

            # 创建驱动实例
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password) if self.password else None,
                max_connection_lifetime=self.config["max_connection_lifetime"],
                max_connection_pool_size=self.config["max_connection_pool_size"],
                connection_timeout=self.config["connection_timeout"]
            )

            # 验证连接
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                test_value = result.single()["test"]
                if test_value == 1:
                    self.is_connected = True
                    self.last_health_check = datetime.now()
                    logger.info("✅ Neo4j连接成功建立")
                    return True
                else:
                    logger.error("❌ Neo4j连接验证失败")
                    return False

        except ImportError:
            logger.error("❌ Neo4j驱动未安装: pip install neo4j")
            return False
        except Exception as e:
            logger.error(f"❌ Neo4j连接失败: {e}")
            self.is_connected = False
            return False

    @contextmanager
    def get_session(self):
        """获取Neo4j会话 (上下文管理器)"""
        if not self.is_connected or not self.driver:
            raise RuntimeError("Neo4j未连接,请先调用connect()")

        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.driver:
                return False

            with self.driver.session() as session:
                result = session.run("RETURN 1 AS health")
                result.single()
                self.last_health_check = datetime.now()
                return True
        except Exception as e:
            logger.warning(f"Neo4j健康检查失败: {e}")
            self.is_connected = False
            return False

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.is_connected = False
            logger.info("Neo4j连接已关闭")


# ============ 三层检索引擎 ============

class TrueThreeLayerEngine:
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
        enable_parallel_execution: bool = False,  # Layer 1和2不能并行,因为2依赖1
        connection_pool_manager=None,  # ✅ 连接池管理器
        timeout_manager: Optional[TimeoutManager] = None  # ✅ 新增：超时管理器
    ):
        """初始化三层检索引擎"""
        # API配置
        self.graphrag_api_port = graphrag_api_port or os.getenv('API_PORT', '8001')
        self.graphrag_api_base = f"http://localhost:{self.graphrag_api_port}/api/graphrag"

        # Neo4j配置
        self.neo4j_uri = neo4j_uri or os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        self.neo4j_user = neo4j_user or os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = neo4j_password or os.getenv('NEO4J_PASSWORD')  # 无密码认证

        # 功能开关
        self.enable_neo4j_direct = enable_neo4j_direct
        self.enable_parallel_execution = enable_parallel_execution
        
        # ✅ 连接池管理器
        self.connection_pool_manager = connection_pool_manager
        
        # ✅ 超时管理器（Requirements 3.6）
        self.timeout_manager = timeout_manager or get_timeout_manager()

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
            "timeout_count": 0  # ✅ 新增：超时计数
        }

        logger.info(f"三层检索引擎已创建 - GraphRAG API: {self.graphrag_api_base}")
        logger.info(f"  → 超时配置: Layer1={self.timeout_manager.get_timeout_ms('layer1_timeout_ms')}ms, "
                   f"Layer2={self.timeout_manager.get_timeout_ms('layer2_timeout_ms')}ms, "
                   f"Layer3={self.timeout_manager.get_timeout_ms('layer3_timeout_ms')}ms")

        # 初始化Neo4j连接
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

            # 尝试连接
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
        domain: str = "fitness_exercises",
        user_id: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        safety_check: bool = True,
        layer1_multiplier: int = 5  # ✅ 新增：Layer1召回倍数（默认5倍）
    ) -> ThreeLayerResult:
        """
        执行完整的三层检索

        Args:
            query: 用户查询文本
            domain: 检索领域
            user_id: 用户ID
            user_profile: 用户档案
            filters: 过滤条件
            top_k: 返回结果数
            safety_check: 是否执行安全检查
            layer1_multiplier: Layer1召回倍数（默认5倍，即top_k=10时召回50个）

        Returns:
            ThreeLayerResult: 三层检索结果
        """
        start_time = datetime.now()
        self.stats["total_queries"] += 1

        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🔍 开始三层检索: {query}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        try:
            # ============ Layer 1: 向量语义检索 ============
            layer1_result = await self._execute_layer1_vector_search(
                query=query,
                domain=domain,
                top_k=top_k * layer1_multiplier,  # ✅ 使用可配置的召回倍数（从3倍提升到5倍）
                filters=filters,
                user_id=user_id
            )

            # ============ Layer 1降级方案 ============
            if not layer1_result.success or not layer1_result.results:
                logger.warning("⚠️ Layer 1失败，启动降级方案")
                
                # 降级方案1：直接使用Layer 2图谱检索
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
                    # 降级方案2：使用规则匹配
                    logger.warning("  ⚠️ Layer 2也失败，启动降级方案2：规则匹配")
                    rule_based_result = await self._execute_rule_based_fallback(
                        query=query,
                        user_profile=user_profile,
                        top_k=top_k * 2
                    )
                    
                    if rule_based_result.success and rule_based_result.results:
                        logger.info(f"  ✓ 规则匹配成功: {len(rule_based_result.results)}个结果")
                        candidates_for_layer3 = rule_based_result.results
                        # 将规则匹配结果作为Layer2结果
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
                
                # 执行Layer 3业务规则验证
                layer3_result = await self._execute_layer3_business_rules(
                    query=query,
                    candidates=candidates_for_layer3,
                    user_profile=user_profile,
                    top_k=top_k,
                    safety_check=safety_check
                )
                
                # 构建最终结果
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

            # ============ Layer 2: 图谱关系推理 ============
            # ✅ 根据Layer1质量动态调整Layer2召回倍数
            if layer1_result.metadata.get("is_low_quality", False):
                logger.info("  → Layer1质量偏低，Layer2增加召回倍数")
                layer2_top_k = top_k * 3  # 从 top_k * 2 提升到 top_k * 3
            else:
                layer2_top_k = top_k * 2  # 正常倍数
            
            layer2_result = await self._execute_layer2_graph_reasoning(
                query=query,
                domain=domain,
                vector_results=layer1_result.results,
                top_k=layer2_top_k,  # ✅ 动态调整
                user_id=user_id,
                filters=filters
            )

            # 选择使用哪层的结果进入Layer 3
            if layer2_result.success and layer2_result.results:
                candidates_for_layer3 = layer2_result.results
            else:
                logger.warning("Layer 2未返回结果,使用Layer 1结果")
                candidates_for_layer3 = layer1_result.results[:top_k * 2]

            # ============ Layer 3: 业务规则验证 ============
            layer3_result = await self._execute_layer3_business_rules(
                query=query,
                candidates=candidates_for_layer3,
                user_profile=user_profile,
                top_k=top_k,
                safety_check=safety_check
            )

            # ============ 构建最终结果 ============
            final_result = self._build_final_result(
                query=query,
                domain=domain,
                layer1=layer1_result,
                layer2=layer2_result,
                layer3=layer3_result,
                start_time=start_time
            )

            logger.info(f"✅ 三层检索完成: {len(final_result.final_results)}个结果, 耗时{final_result.total_execution_time_ms:.0f}ms")

            return final_result

        except Exception as e:
            logger.error(f"❌ 三层检索失败: {e}", exc_info=True)
            self.stats["total_errors"] += 1

            # 返回错误结果
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
        domain: str = "fitness",
        user_id: str = None,
        context: Dict[str, Any] = None
    ):
        """
        Framework层适配器方法

        将framework层的调用转换为内部的execute_three_layer_query调用
        保持向后兼容性
        """
        # 提取参数
        user_profile = context.get("user_profile") if context else None
        filters = context.get("filters") if context else None
        top_k = context.get("top_k", 10) if context else 10
        safety_check = context.get("safety_check", True) if context else True

        # 调用原始方法
        return await self.execute_three_layer_query(
            query=query,
            domain=domain,
            user_id=user_id,
            user_profile=user_profile,
            filters=filters,
            top_k=top_k,
            safety_check=safety_check
        )

    async def _execute_layer1_vector_search(
        self,
        query: str,
        domain: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        user_id: Optional[str] = None,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        min_confidence: float = 0.70  # ✅ 最低置信度阈值
    ) -> LayerExecutionResult:
        """
        Layer 1: 向量语义检索 (Qdrant via GraphRAG API)
        
        特性：
        - 重试机制：最多重试3次
        - 指数退避：1s, 2s, 4s
        - 详细日志：记录每次重试
        - ✅ 质量评估：标记低质量结果（置信度 < min_confidence）
        - ✅ 统一超时：使用TimeoutManager配置 (Requirements 3.6)
        """
        start_time = datetime.now()
        logger.info("→ Layer 1: 向量语义检索 (Qdrant)")
        
        # ✅ 从超时管理器获取配置
        layer1_timeout = self.timeout_manager.get_timeout("layer1_timeout_ms", 5000)
        http_timeout = self.timeout_manager.get_timeout("http_total_timeout_ms", 60000)
        
        retry_delay = initial_retry_delay
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"  ⟳ 重试 {attempt}/{max_retries-1}，等待{retry_delay:.1f}秒...")
                    await asyncio.sleep(retry_delay)
                
                # ✅ 使用超时管理器配置的超时时间
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.graphrag_api_base}/query",
                        json={
                            "query_text": query,
                            "domain": domain,
                            "query_type": "semantic_search",
                            "top_k": top_k,
                            "filters": filters or {},
                            "return_reason": False,
                            "user_id": user_id or "anonymous"
                        },
                        timeout=aiohttp.ClientTimeout(total=min(layer1_timeout, http_timeout))
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = data.get("data", {}).get("results", [])

                            # 计算置信度
                            if results:
                                avg_score = sum(r.get("score", 0) for r in results) / len(results)
                                confidence = min(avg_score, 1.0)
                                
                                # ✅ 质量评估
                                is_low_quality = confidence < min_confidence
                                
                                if is_low_quality:
                                    logger.warning(f"  ⚠️ Layer1质量偏低（置信度{confidence:.2f} < {min_confidence}）")
                            else:
                                confidence = 0.0
                                is_low_quality = True

                            execution_time = (datetime.now() - start_time).total_seconds() * 1000
                            self.stats["layer1_success"] += 1

                            if attempt > 0:
                                logger.info(f"  ✓ Layer 1重试成功（第{attempt+1}次尝试）: {len(results)}个向量结果, 置信度{confidence:.2f}")
                            else:
                                logger.info(f"  ✓ Layer 1完成: {len(results)}个向量结果, 置信度{confidence:.2f}")

                            return LayerExecutionResult(
                                layer_name="Layer1-Vector",
                                success=True,
                                results=results,
                                execution_time_ms=execution_time,
                                confidence=confidence,
                                metadata={
                                    "source": "qdrant_via_api",
                                    "count": len(results),
                                    "avg_score": confidence,
                                    "retry_count": attempt,
                                    "is_low_quality": is_low_quality  # ✅ 新增标记
                                }
                            )
                        else:
                            last_error = f"GraphRAG API返回错误: {response.status}"
                            logger.warning(f"  ⚠️ 尝试{attempt+1}/{max_retries}失败: {last_error}")
                            
                            # 如果是最后一次尝试，返回错误
                            if attempt == max_retries - 1:
                                logger.error(f"  ✗ Layer 1最终失败: {last_error}")
                                return self._empty_layer_result("Layer1-Vector", error=last_error)
                            
                            # 指数退避
                            retry_delay *= 2

            except asyncio.TimeoutError:
                last_error = f"Layer 1超时 (配置: {layer1_timeout}s)"
                logger.warning(f"  ⚠️ 尝试{attempt+1}/{max_retries}超时")
                self.stats["timeout_count"] += 1  # ✅ 记录超时
                
                if attempt == max_retries - 1:
                    logger.error(f"  ✗ Layer 1最终失败: {last_error}")
                    return self._empty_layer_result("Layer1-Vector", error=last_error)
                
                # 指数退避
                retry_delay *= 2
                
            except Exception as e:
                last_error = f"Layer 1异常: {e}"
                logger.warning(f"  ⚠️ 尝试{attempt+1}/{max_retries}异常: {e}")
                
                if attempt == max_retries - 1:
                    logger.error(f"  ✗ Layer 1最终失败: {last_error}")
                    return self._empty_layer_result("Layer1-Vector", error=last_error)
                
                # 指数退避
                retry_delay *= 2
        
        # 理论上不会到达这里，但为了安全起见
        logger.error(f"  ✗ Layer 1失败: 所有重试均失败")
        return self._empty_layer_result("Layer1-Vector", error=last_error or "所有重试均失败")

    async def _execute_layer2_graph_reasoning(
        self,
        query: str,
        domain: str,
        vector_results: List[Dict[str, Any]],
        top_k: int,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> LayerExecutionResult:
        """
        Layer 2: 图谱关系推理 (Neo4j Direct + API Fallback)
        """
        start_time = datetime.now()
        logger.info("→ Layer 2: 图谱关系推理 (Neo4j)")

        # 策略1: 尝试Neo4j直连
        if self.neo4j_available and self.neo4j_manager:
            neo4j_result = await self._query_neo4j_direct(query, vector_results, top_k, filters)
            if neo4j_result.success:
                self.stats["layer2_neo4j_direct"] += 1
                return neo4j_result
            else:
                logger.warning("  ⚠️ Neo4j直连失败,降级到API")

        # 策略2: 降级到GraphRAG API
        api_result = await self._query_neo4j_via_api(query, domain, vector_results, top_k, user_id)
        if api_result.success:
            self.stats["layer2_api_fallback"] += 1

        return api_result

    async def _query_neo4j_direct(
        self,
        query: str,
        vector_results: List[Dict[str, Any]],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> LayerExecutionResult:
        """通过Neo4j直连查询图谱（使用连接池）"""
        start_time = datetime.now()

        try:
            # 从查询中提取肌肉关键词
            muscle_keywords = self._extract_muscle_keywords(query)
            graph_results = []
            
            # 从filters中提取器械过滤条件
            available_equipment = None
            if filters:
                available_equipment = filters.get("available_equipment", [])

            # ✅ 优先使用连接池管理器
            if self.connection_pool_manager and self.connection_pool_manager.neo4j_pool:
                logger.debug("  → 使用Neo4j连接池")
                async with self.connection_pool_manager.get_neo4j_session() as session:
                    for muscle in muscle_keywords[:3]:  # 限制关键词数量
                        # 构建Cypher查询（根据是否有器械过滤条件）
                        if available_equipment:
                            cypher_query = """
                            MATCH (m:Muscle)
                            WHERE m.name_zh CONTAINS $muscle
                               OR m.name_en CONTAINS $muscle
                               OR m.name CONTAINS $muscle
                            MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m)
                            WHERE ANY(equip IN e.equipment_zh WHERE equip IN $equipment)
                            RETURN
                                e.name_zh AS exercise_zh,
                                e.name AS exercise_en,
                                e.difficulty AS difficulty,
                                e.equipment_zh AS equipment,
                                m.name_zh AS muscle_name,
                                type(r) AS relationship_type,
                                m.mev AS mev,
                                m.mav AS mav,
                                m.mrv AS mrv
                            LIMIT $limit
                            """
                            
                            result = await session.run(
                                cypher_query,
                                muscle=muscle,
                                equipment=available_equipment,
                                limit=top_k
                            )
                        else:
                            cypher_query = """
                            MATCH (m:Muscle)
                            WHERE m.name_zh CONTAINS $muscle
                               OR m.name_en CONTAINS $muscle
                               OR m.name CONTAINS $muscle
                            MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m)
                            RETURN
                                e.name_zh AS exercise_zh,
                                e.name AS exercise_en,
                                e.difficulty AS difficulty,
                                e.equipment_zh AS equipment,
                                m.name_zh AS muscle_name,
                                type(r) AS relationship_type,
                                m.mev AS mev,
                                m.mav AS mav,
                                m.mrv AS mrv
                            LIMIT $limit
                            """

                            result = await session.run(
                                cypher_query,
                                muscle=muscle,
                                limit=top_k
                            )

                        async for record in result:
                            graph_results.append({
                                "exercise_name_zh": record.get("exercise_zh", ""),
                                "exercise_name_en": record.get("exercise_en", ""),
                                "difficulty": record.get("difficulty", ""),
                                "equipment": record.get("equipment", ""),
                                "target_muscle": record.get("muscle_name", ""),
                                "relationship_type": record.get("relationship_type", ""),
                                "training_volume": {
                                    "mev": record.get("mev"),
                                    "mav": record.get("mav"),
                                    "mrv": record.get("mrv")
                                },
                                "source": "neo4j_pool",
                                "score": 0.8  # Neo4j图查询默认高分
                            })
            
            # ✅ 降级：使用传统Neo4jConnectionManager
            elif muscle_keywords and self.neo4j_manager:
                logger.debug("  → 使用传统Neo4j连接管理器")
                with self.neo4j_manager.get_session() as session:
                    for muscle in muscle_keywords[:3]:  # 限制关键词数量
                        # 构建Cypher查询（根据是否有器械过滤条件）
                        if available_equipment:
                            cypher_query = """
                            MATCH (m:Muscle)
                            WHERE m.name_zh CONTAINS $muscle
                               OR m.name_en CONTAINS $muscle
                               OR m.name CONTAINS $muscle
                            MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m)
                            WHERE ANY(equip IN e.equipment_zh WHERE equip IN $equipment)
                            RETURN
                                e.name_zh AS exercise_zh,
                                e.name AS exercise_en,
                                e.difficulty AS difficulty,
                                e.equipment_zh AS equipment,
                                m.name_zh AS muscle_name,
                                type(r) AS relationship_type,
                                m.mev AS mev,
                                m.mav AS mav,
                                m.mrv AS mrv
                            LIMIT $limit
                            """
                            
                            result = session.run(
                                cypher_query,
                                muscle=muscle,
                                equipment=available_equipment,
                                limit=top_k
                            )
                        else:
                            cypher_query = """
                            MATCH (m:Muscle)
                            WHERE m.name_zh CONTAINS $muscle
                               OR m.name_en CONTAINS $muscle
                               OR m.name CONTAINS $muscle
                            MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m)
                            RETURN
                                e.name_zh AS exercise_zh,
                                e.name AS exercise_en,
                                e.difficulty AS difficulty,
                                e.equipment_zh AS equipment,
                                m.name_zh AS muscle_name,
                                type(r) AS relationship_type,
                                m.mev AS mev,
                                m.mav AS mav,
                                m.mrv AS mrv
                            LIMIT $limit
                            """

                            result = session.run(
                                cypher_query,
                                muscle=muscle,
                                limit=top_k
                            )

                        for record in result:
                            graph_results.append({
                                "exercise_name_zh": record.get("exercise_zh", ""),
                                "exercise_name_en": record.get("exercise_en", ""),
                                "difficulty": record.get("difficulty", ""),
                                "equipment": record.get("equipment", ""),
                                "target_muscle": record.get("muscle_name", ""),
                                "relationship_type": record.get("relationship_type", ""),
                                "training_volume": {
                                    "mev": record.get("mev"),
                                    "mav": record.get("mav"),
                                    "mrv": record.get("mrv")
                                },
                                "source": "neo4j_direct",
                                "score": 0.8  # Neo4j图查询默认高分
                            })

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            confidence = 0.9 if graph_results else 0.0

            logger.info(f"  ✓ Neo4j直连完成: {len(graph_results)}个图谱结果")

            return LayerExecutionResult(
                layer_name="Layer2-Graph",
                success=bool(graph_results),
                results=graph_results,
                execution_time_ms=execution_time,
                confidence=confidence,
                metadata={
                    "source": "neo4j_pool" if self.connection_pool_manager else "neo4j_direct",
                    "count": len(graph_results),
                    "muscle_keywords": muscle_keywords,
                    "equipment_filtered": bool(available_equipment)
                }
            )

        except Exception as e:
            logger.error(f"  ✗ Neo4j直连查询失败: {e}")
            return self._empty_layer_result("Layer2-Graph", error=str(e))

    async def _execute_layer2_graph_reasoning_fallback(
        self,
        query: str,
        domain: str,
        top_k: int,
        user_id: Optional[str] = None
    ) -> LayerExecutionResult:
        """
        Layer 2降级方案：无向量结果时的图谱检索
        
        策略：
        1. 从查询中提取关键词
        2. 直接查询Neo4j图谱
        3. 如果Neo4j失败，使用API
        """
        start_time = datetime.now()
        logger.info("→ Layer 2降级: 无向量结果的图谱检索")
        
        # 策略1: 尝试Neo4j直连
        if self.neo4j_available and self.neo4j_manager:
            neo4j_result = await self._query_neo4j_direct_fallback(query, top_k)
            if neo4j_result.success:
                self.stats["layer2_neo4j_direct"] += 1
                return neo4j_result
            else:
                logger.warning("  ⚠️ Neo4j直连失败,降级到API")
        
        # 策略2: 降级到GraphRAG API
        api_result = await self._query_neo4j_via_api_fallback(query, domain, top_k, user_id)
        if api_result.success:
            self.stats["layer2_api_fallback"] += 1
        
        return api_result
    
    async def _query_neo4j_direct_fallback(
        self,
        query: str,
        top_k: int
    ) -> LayerExecutionResult:
        """Neo4j直连降级查询（无向量结果）"""
        start_time = datetime.now()
        
        try:
            # 从查询中提取肌肉关键词
            muscle_keywords = self._extract_muscle_keywords(query)
            graph_results = []
            
            if muscle_keywords and self.neo4j_manager:
                with self.neo4j_manager.get_session() as session:
                    for muscle in muscle_keywords[:3]:  # 限制关键词数量
                        cypher_query = """
                        MATCH (m:Muscle)
                        WHERE m.name_zh CONTAINS $muscle
                           OR m.name_en CONTAINS $muscle
                           OR m.name CONTAINS $muscle
                        MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m)
                        RETURN
                            e.name_zh AS exercise_zh,
                            e.name AS exercise_en,
                            e.difficulty AS difficulty,
                            e.equipment_zh AS equipment,
                            m.name_zh AS muscle_name,
                            type(r) AS relationship_type,
                            m.mev AS mev,
                            m.mav AS mav,
                            m.mrv AS mrv
                        LIMIT $limit
                        """
                        
                        result = session.run(
                            cypher_query,
                            muscle=muscle,
                            limit=top_k
                        )
                        
                        for record in result:
                            graph_results.append({
                                "exercise_name_zh": record.get("exercise_zh", ""),
                                "exercise_name_en": record.get("exercise_en", ""),
                                "difficulty": record.get("difficulty", ""),
                                "equipment": record.get("equipment", ""),
                                "target_muscle": record.get("muscle_name", ""),
                                "relationship_type": record.get("relationship_type", ""),
                                "training_volume": {
                                    "mev": record.get("mev"),
                                    "mav": record.get("mav"),
                                    "mrv": record.get("mrv")
                                },
                                "source": "neo4j_direct_fallback",
                                "score": 0.7  # 降级查询给予中等分数
                            })
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            confidence = 0.7 if graph_results else 0.0
            
            logger.info(f"  ✓ Neo4j降级查询完成: {len(graph_results)}个图谱结果")
            
            return LayerExecutionResult(
                layer_name="Layer2-Graph-Fallback",
                success=bool(graph_results),
                results=graph_results,
                execution_time_ms=execution_time,
                confidence=confidence,
                metadata={
                    "source": "neo4j_direct_fallback",
                    "count": len(graph_results),
                    "muscle_keywords": muscle_keywords
                }
            )
        
        except Exception as e:
            logger.error(f"  ✗ Neo4j降级查询失败: {e}")
            return self._empty_layer_result("Layer2-Graph-Fallback", error=str(e))
    
    async def _query_neo4j_via_api_fallback(
        self,
        query: str,
        domain: str,
        top_k: int,
        user_id: Optional[str] = None
    ) -> LayerExecutionResult:
        """通过GraphRAG API降级查询（无向量结果）"""
        start_time = datetime.now()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.graphrag_api_base}/query",
                    json={
                        "query_text": query,
                        "domain": domain,
                        "query_type": "hybrid",  # 混合查询包含图谱
                        "top_k": top_k,
                        "return_reason": True,
                        "user_id": user_id or "anonymous"
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        raw_results = data.get("data", {}).get("results", [])
                        
                        # 转换API返回的嵌套结构为扁平结构
                        results = []
                        for item in raw_results:
                            payload = item.get("payload", {})
                            results.append({
                                "exercise_id": payload.get("exercise_id", ""),  # 添加exercise_id
                                "id": payload.get("exercise_id", ""),  # 兼容性字段
                                "exercise_name_zh": payload.get("name_zh", ""),
                                "exercise_name_en": payload.get("name_en", ""),
                                "name_zh": payload.get("name_zh", ""),  # 兼容性字段
                                "name_en": payload.get("name_en", ""),  # 兼容性字段
                                "difficulty": payload.get("difficulty", ""),
                                "equipment": payload.get("equipment_zh", ""),
                                "equipment_zh": payload.get("equipment_zh", ""),  # 兼容性字段
                                "target_muscle": payload.get("primary_muscle_zh", ""),
                                "primary_muscle_zh": payload.get("primary_muscle_zh", ""),  # 兼容性字段
                                "score": item.get("score", 0.0),
                                "source": "api_fallback"
                            })
                        
                        execution_time = (datetime.now() - start_time).total_seconds() * 1000
                        confidence = 0.6 if results else 0.0
                        
                        logger.info(f"  ✓ API降级查询完成: {len(results)}个结果")
                        
                        return LayerExecutionResult(
                            layer_name="Layer2-Graph-Fallback",
                            success=bool(results),
                            results=results,
                            execution_time_ms=execution_time,
                            confidence=confidence,
                            metadata={
                                "source": "api_fallback",
                                "count": len(results)
                            }
                        )
                    else:
                        error_msg = f"API返回错误: {response.status}"
                        logger.error(f"  ✗ {error_msg}")
                        return self._empty_layer_result("Layer2-Graph-Fallback", error=error_msg)
        
        except Exception as e:
            error_msg = f"API降级查询失败: {e}"
            logger.error(f"  ✗ {error_msg}")
            return self._empty_layer_result("Layer2-Graph-Fallback", error=error_msg)
    
    async def _execute_rule_based_fallback(
        self,
        query: str,
        user_profile: Optional[Dict[str, Any]],
        top_k: int
    ) -> LayerExecutionResult:
        """
        规则匹配降级方案：当Layer1和Layer2都失败时使用
        
        策略：
        1. 基于关键词匹配推荐通用动作
        2. 基于用户档案推荐适合的难度
        3. 返回安全的基础动作
        """
        start_time = datetime.now()
        logger.info("→ 规则匹配降级: 基于关键词的通用推荐")
        
        try:
            # 定义通用推荐规则
            rule_based_recommendations = {
                "胸": [
                    {"exercise_name_zh": "俯卧撑", "difficulty": "beginner", "equipment": "徒手", "target_muscle": "胸大肌"},
                    {"exercise_name_zh": "哑铃卧推", "difficulty": "intermediate", "equipment": "哑铃", "target_muscle": "胸大肌"},
                    {"exercise_name_zh": "杠铃卧推", "difficulty": "intermediate", "equipment": "杠铃", "target_muscle": "胸大肌"},
                ],
                "背": [
                    {"exercise_name_zh": "引体向上", "difficulty": "intermediate", "equipment": "单杠", "target_muscle": "背阔肌"},
                    {"exercise_name_zh": "哑铃划船", "difficulty": "beginner", "equipment": "哑铃", "target_muscle": "背阔肌"},
                    {"exercise_name_zh": "杠铃划船", "difficulty": "intermediate", "equipment": "杠铃", "target_muscle": "背阔肌"},
                ],
                "腿": [
                    {"exercise_name_zh": "深蹲", "difficulty": "beginner", "equipment": "徒手", "target_muscle": "股四头肌"},
                    {"exercise_name_zh": "杠铃深蹲", "difficulty": "intermediate", "equipment": "杠铃", "target_muscle": "股四头肌"},
                    {"exercise_name_zh": "腿举", "difficulty": "beginner", "equipment": "器械", "target_muscle": "股四头肌"},
                ],
                "肩": [
                    {"exercise_name_zh": "哑铃推举", "difficulty": "beginner", "equipment": "哑铃", "target_muscle": "三角肌"},
                    {"exercise_name_zh": "侧平举", "difficulty": "beginner", "equipment": "哑铃", "target_muscle": "三角肌"},
                    {"exercise_name_zh": "杠铃推举", "difficulty": "intermediate", "equipment": "杠铃", "target_muscle": "三角肌"},
                ],
                "臂": [
                    {"exercise_name_zh": "哑铃弯举", "difficulty": "beginner", "equipment": "哑铃", "target_muscle": "肱二头肌"},
                    {"exercise_name_zh": "三头臂屈伸", "difficulty": "beginner", "equipment": "徒手", "target_muscle": "肱三头肌"},
                    {"exercise_name_zh": "杠铃弯举", "difficulty": "intermediate", "equipment": "杠铃", "target_muscle": "肱二头肌"},
                ],
                "腹": [
                    {"exercise_name_zh": "卷腹", "difficulty": "beginner", "equipment": "徒手", "target_muscle": "腹直肌"},
                    {"exercise_name_zh": "平板支撑", "difficulty": "beginner", "equipment": "徒手", "target_muscle": "核心"},
                    {"exercise_name_zh": "仰卧举腿", "difficulty": "intermediate", "equipment": "徒手", "target_muscle": "腹直肌"},
                ],
            }
            
            # 从查询中提取关键词
            query_lower = query.lower()
            matched_results = []
            
            for keyword, exercises in rule_based_recommendations.items():
                if keyword in query:
                    # 根据用户档案过滤难度
                    user_level = user_profile.get("fitness_level", "intermediate") if user_profile else "intermediate"
                    
                    for exercise in exercises:
                        # 简单的难度匹配
                        if user_level == "beginner" and exercise["difficulty"] in ["beginner"]:
                            matched_results.append({
                                **exercise,
                                "source": "rule_based_fallback",
                                "score": 0.5,
                                "rule_matched": keyword
                            })
                        elif user_level == "intermediate" and exercise["difficulty"] in ["beginner", "intermediate"]:
                            matched_results.append({
                                **exercise,
                                "source": "rule_based_fallback",
                                "score": 0.5,
                                "rule_matched": keyword
                            })
                        elif user_level == "advanced":
                            matched_results.append({
                                **exercise,
                                "source": "rule_based_fallback",
                                "score": 0.5,
                                "rule_matched": keyword
                            })
            
            # 如果没有匹配到关键词，返回通用的基础动作
            if not matched_results:
                logger.info("  → 未匹配到关键词，返回通用基础动作")
                matched_results = [
                    {"exercise_name_zh": "俯卧撑", "difficulty": "beginner", "equipment": "徒手", "target_muscle": "胸大肌", "source": "rule_based_fallback", "score": 0.4},
                    {"exercise_name_zh": "深蹲", "difficulty": "beginner", "equipment": "徒手", "target_muscle": "股四头肌", "source": "rule_based_fallback", "score": 0.4},
                    {"exercise_name_zh": "平板支撑", "difficulty": "beginner", "equipment": "徒手", "target_muscle": "核心", "source": "rule_based_fallback", "score": 0.4},
                ]
            
            # 限制返回数量
            matched_results = matched_results[:top_k]
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            confidence = 0.5 if matched_results else 0.0
            
            logger.info(f"  ✓ 规则匹配完成: {len(matched_results)}个通用推荐")
            
            return LayerExecutionResult(
                layer_name="Layer2-RuleBased-Fallback",
                success=bool(matched_results),
                results=matched_results,
                execution_time_ms=execution_time,
                confidence=confidence,
                metadata={
                    "source": "rule_based_fallback",
                    "count": len(matched_results),
                    "fallback_reason": "Layer1和Layer2均失败"
                }
            )
        
        except Exception as e:
            logger.error(f"  ✗ 规则匹配失败: {e}")
            return self._empty_layer_result("Layer2-RuleBased-Fallback", error=str(e))

    async def _query_neo4j_via_api(
        self,
        query: str,
        domain: str,
        vector_results: List[Dict[str, Any]],
        top_k: int,
        user_id: Optional[str] = None
    ) -> LayerExecutionResult:
        """通过GraphRAG API查询图谱(降级方案)"""
        start_time = datetime.now()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.graphrag_api_base}/query",
                    json={
                        "query_text": query,
                        "domain": domain,
                        "query_type": "hybrid",  # 混合查询包含图谱
                        "top_k": top_k,
                        "return_reason": True,
                        "user_id": user_id or "anonymous"
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        raw_results = data.get("data", {}).get("results", [])
                        
                        # 转换API返回的嵌套结构为扁平结构
                        results = []
                        for item in raw_results:
                            payload = item.get("payload", {})
                            results.append({
                                "exercise_id": payload.get("exercise_id", ""),  # 添加exercise_id
                                "id": payload.get("exercise_id", ""),  # 兼容性字段
                                "exercise_name_zh": payload.get("name_zh", ""),
                                "exercise_name_en": payload.get("name_en", ""),
                                "name_zh": payload.get("name_zh", ""),  # 兼容性字段
                                "name_en": payload.get("name_en", ""),  # 兼容性字段
                                "difficulty": payload.get("difficulty", ""),
                                "equipment": payload.get("equipment_zh", ""),
                                "equipment_zh": payload.get("equipment_zh", ""),  # 兼容性字段
                                "target_muscle": payload.get("primary_muscle_zh", ""),
                                "primary_muscle_zh": payload.get("primary_muscle_zh", ""),  # 兼容性字段
                                "score": item.get("score", 0.0),
                                "source": "api_fallback"
                            })

                        execution_time = (datetime.now() - start_time).total_seconds() * 1000
                        confidence = 0.7 if results else 0.0

                        logger.info(f"  ✓ API降级完成: {len(results)}个结果")

                        return LayerExecutionResult(
                            layer_name="Layer2-Graph",
                            success=bool(results),
                            results=results,
                            execution_time_ms=execution_time,
                            confidence=confidence,
                            metadata={
                                "source": "api_fallback",
                                "count": len(results)
                            }
                        )
                    else:
                        error_msg = f"API返回错误: {response.status}"
                        logger.error(f"  ✗ {error_msg}")
                        return self._empty_layer_result("Layer2-Graph", error=error_msg)

        except Exception as e:
            error_msg = f"API查询失败: {e}"
            logger.error(f"  ✗ {error_msg}")
            return self._empty_layer_result("Layer2-Graph", error=error_msg)

    async def _execute_layer3_business_rules(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]],
        top_k: int,
        safety_check: bool,
        session_context: Optional[Dict[str, Any]] = None,
        recent_training: Optional[List[Dict[str, Any]]] = None,
        use_enhanced_rules: bool = True
    ) -> LayerExecutionResult:
        """
        Layer 3: 业务规则验证（增强版）

        基础规则:
        1. 用户档案匹配 (经验等级)
        2. 安全性检查 (禁忌症)
        3. 器械可用性
        4. 训练容量合理性
        
        增强规则 (Requirements 11.1-11.6, 18.1-18.6):
        5. kinetic_chain_rule（动力链规则）
        6. force_balance_rule（推拉平衡规则）
        7. joint_load_rule（关节负荷规则）
        8. recovery_time_rule（恢复时间规则）
        9. postural_correction_rule（体态矫正规则）
        10. body_type_constraint（体型约束）
        11. training_frequency_constraint（训练频率约束）
        12. session_duration_constraint（训练时长约束）
        13. goal_alignment_constraint（目标对齐约束）
        14. progressive_overload_constraint（渐进超负荷约束）
        15. nutrition_constraint（营养约束）
        """
        start_time = datetime.now()
        logger.info("→ Layer 3: 业务规则验证")

        try:
            user_profile = user_profile or {}
            session_context = session_context or {}
            recent_training = recent_training or []
            
            # ============ 基础规则过滤 ============
            validated_results = []
            
            for candidate in candidates:
                # 规则1: 经验等级匹配
                if not self._match_fitness_level(candidate, user_profile):
                    continue

                # 规则2: 安全性检查
                if safety_check:
                    if not self._validate_safety(candidate, user_profile):
                        continue

                # 规则3: 器械可用性
                if not self._check_equipment_availability(candidate, user_profile):
                    continue

                # 规则4: 训练容量合理性
                volume_score = self._assess_training_volume(candidate, user_profile)

                # 添加规则评分
                candidate["rule_validation_score"] = volume_score
                candidate["validation_passed"] = True

                validated_results.append(candidate)
            
            # ============ 增强规则处理 ============
            enhanced_metadata = {}
            
            if use_enhanced_rules and validated_results:
                try:
                    from .layer3_rule_engine import Layer3RuleEngine
                    
                    # 初始化增强规则引擎
                    rule_engine = Layer3RuleEngine(neo4j_client=self.neo4j_manager)
                    
                    # 应用增强规则
                    validated_results, execution_log = await rule_engine.apply_all_rules(
                        candidates=validated_results,
                        user_profile=user_profile,
                        query=query,
                        session_context=session_context,
                        recent_training=recent_training,
                        top_k=top_k * 2  # 给后续处理留余量
                    )
                    
                    # 记录增强规则执行结果
                    enhanced_metadata = {
                        "enhanced_rules_applied": True,
                        "rules_count": len(execution_log.rules_applied),
                        "rules_details": [
                            {
                                "name": r.rule_name,
                                "applied": r.applied,
                                "before": r.candidates_before,
                                "after": r.candidates_after,
                                "time_ms": r.execution_time_ms
                            }
                            for r in execution_log.rules_applied
                        ]
                    }
                    
                    logger.info(f"  → 增强规则完成: {len(execution_log.rules_applied)}条规则")
                    
                except ImportError as e:
                    logger.warning(f"  ⚠️ 增强规则引擎未加载: {e}")
                    enhanced_metadata = {"enhanced_rules_applied": False, "reason": str(e)}
                except Exception as e:
                    logger.error(f"  ⚠️ 增强规则执行失败: {e}")
                    enhanced_metadata = {"enhanced_rules_applied": False, "error": str(e)}
            
            # 限制返回数量
            final_results = validated_results[:top_k]
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            confidence = 0.95 if final_results else 0.0

            self.stats["layer3_success"] += 1
            logger.info(f"  ✓ Layer 3完成: {len(final_results)}/{len(candidates)}个通过规则验证")

            return LayerExecutionResult(
                layer_name="Layer3-Rules",
                success=bool(final_results),
                results=final_results,
                execution_time_ms=execution_time,
                confidence=confidence,
                metadata={
                    "validated_count": len(final_results),
                    "total_candidates": len(candidates),
                    "pass_rate": len(final_results) / len(candidates) if candidates else 0,
                    **enhanced_metadata
                }
            )

        except Exception as e:
            logger.error(f"  ✗ Layer 3失败: {e}")
            return self._empty_layer_result("Layer3-Rules", error=str(e))

    # ============ 业务规则方法 ============

    def _match_fitness_level(
        self,
        exercise: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> bool:
        """匹配健身经验等级"""
        if not user_profile:
            return True

        user_level = user_profile.get("fitness_level", "intermediate").lower()
        # 使用统一字段名：difficulty_zh / difficulty_en
        exercise_difficulty = (exercise.get("difficulty_zh") or exercise.get("difficulty_en") or "intermediate").lower()

        # 等级映射（支持中英文）
        level_hierarchy = {
            "beginner": ["beginner", "easy", "novice", "新手", "初级", "简单"],
            "intermediate": ["beginner", "intermediate", "moderate", "novice", "新手", "中级", "中等", "初级"],
            "advanced": ["intermediate", "advanced", "hard", "elite", "中级", "高级", "困难", "精英"]
        }

        allowed_difficulties = level_hierarchy.get(user_level, ["intermediate", "中级"])
        return any(diff in exercise_difficulty for diff in allowed_difficulties)

    def _validate_safety(
        self,
        exercise: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> bool:
        """
        增强版安全性验证 (Requirements 4.3, 4.6)
        
        检查项目：
        1. 禁忌症匹配（绝对禁忌/相对禁忌/谨慎使用）
        2. 年龄限制
        3. 健康状况检查（慢性病、损伤史）
        4. 关节损伤检查
        5. 体态问题检查
        """
        if not user_profile:
            return True

        exercise_name = exercise.get("exercise_name_zh", "Unknown")
        
        # ============ 1. 禁忌症检查（支持severity级别）============
        contraindications = exercise.get("contraindications", [])
        user_conditions = user_profile.get("medical_conditions", [])
        
        # 获取健康档案
        health_profile = user_profile.get("health_profile", {})
        
        # 整合所有健康状况
        all_conditions = set(user_conditions)
        
        # 添加慢性病
        chronic_conditions = health_profile.get("chronic_conditions", [])
        for condition in chronic_conditions:
            if isinstance(condition, dict):
                all_conditions.add(condition.get("name", ""))
            else:
                all_conditions.add(str(condition))
        
        # 添加当前症状
        current_symptoms = health_profile.get("current_symptoms", [])
        for symptom in current_symptoms:
            all_conditions.add(str(symptom))
        
        # 检查禁忌症匹配
        for condition in all_conditions:
            if not condition:
                continue
            # 精确匹配
            if condition in contraindications:
                logger.debug(f"安全过滤: {exercise_name} - 禁忌症 {condition}")
                return False
            # 模糊匹配（部分包含）
            for contra in contraindications:
                if isinstance(contra, str) and (condition in contra or contra in condition):
                    logger.debug(f"安全过滤: {exercise_name} - 禁忌症匹配 {condition} ~ {contra}")
                    return False

        # ============ 2. 年龄限制检查 ============
        basic_info = user_profile.get("basic_info", {})
        user_age = basic_info.get("age") or user_profile.get("age", 30)
        
        difficulty = (exercise.get("difficulty_zh") or exercise.get("difficulty_en") or "").lower()
        
        # 高龄用户限制
        if user_age > 60:
            if "advanced" in difficulty or "elite" in difficulty or "高级" in difficulty or "精英" in difficulty:
                logger.debug(f"安全过滤: {exercise_name} - 高龄(>{user_age})不适合高难度")
                return False
        
        # 青少年用户限制（<16岁）
        if user_age < 16:
            # 限制大重量复合动作
            high_load_keywords = ["硬拉", "深蹲", "卧推", "推举", "deadlift", "squat", "bench press"]
            if any(kw in exercise_name.lower() for kw in high_load_keywords):
                if "advanced" in difficulty or "高级" in difficulty:
                    logger.debug(f"安全过滤: {exercise_name} - 青少年(<16)不适合高负荷动作")
                    return False

        # ============ 3. 关节损伤检查 ============
        injuries = health_profile.get("injuries", [])
        injury_history = health_profile.get("injury_history", [])
        
        # 整合所有损伤信息
        injured_parts = set()
        for injury in injuries + injury_history:
            if isinstance(injury, dict):
                body_part = injury.get("body_part", "")
                injury_type = injury.get("type", "")
                if body_part:
                    injured_parts.add(body_part.lower())
                if injury_type:
                    injured_parts.add(injury_type.lower())
            elif isinstance(injury, str):
                injured_parts.add(injury.lower())
        
        if injured_parts:
            # 获取动作涉及的关节/部位
            involved_joints = exercise.get("involved_joints", [])
            target_muscle = (exercise.get("primary_muscle_zh") or exercise.get("target_muscle") or "").lower()
            
            # 关节关键词映射
            joint_keywords = {
                "肩": ["肩", "shoulder", "三角肌", "deltoid"],
                "膝": ["膝", "knee", "股四头肌", "quadriceps"],
                "腰": ["腰", "lower back", "竖脊肌", "erector"],
                "颈": ["颈", "neck", "斜方肌上部"],
                "肘": ["肘", "elbow", "肱二头肌", "肱三头肌"],
                "腕": ["腕", "wrist", "前臂"],
                "踝": ["踝", "ankle", "小腿"],
                "髋": ["髋", "hip", "臀", "glute"],
            }
            
            for injured_part in injured_parts:
                # 检查是否涉及受伤部位
                for joint_name, keywords in joint_keywords.items():
                    if any(kw in injured_part for kw in keywords):
                        # 检查动作是否涉及该关节
                        exercise_text = f"{exercise_name} {target_muscle} {' '.join(involved_joints)}".lower()
                        if any(kw in exercise_text for kw in keywords):
                            logger.debug(f"安全过滤: {exercise_name} - 涉及受伤部位 {injured_part}")
                            return False

        # ============ 4. 体态问题检查 ============
        postural_issues = health_profile.get("postural_issues", [])
        
        # 体态问题与禁忌动作映射
        postural_contraindications = {
            "骨盆前倾": ["深蹲", "硬拉", "弓步蹲", "腿举"],
            "骨盆后倾": ["卷腹", "仰卧起坐", "悬垂举腿"],
            "圆肩": ["卧推", "俯卧撑", "前平举", "上斜卧推"],
            "头前伸": ["耸肩", "颈后推举", "直立划船"],
            "驼背": ["卷腹", "仰卧起坐", "俯身划船"],
            "脊柱侧弯": ["大重量深蹲", "大重量硬拉", "单侧负重"],
        }
        
        for issue in postural_issues:
            issue_name = issue if isinstance(issue, str) else issue.get("name", "")
            if issue_name in postural_contraindications:
                contra_exercises = postural_contraindications[issue_name]
                if any(contra in exercise_name for contra in contra_exercises):
                    # 不完全禁止，但在高难度时过滤
                    if "advanced" in difficulty or "高级" in difficulty:
                        logger.debug(f"安全过滤: {exercise_name} - 体态问题 {issue_name} 不适合高难度")
                        return False

        # ============ 5. 特殊健康状况检查 ============
        # 心血管疾病
        cardiovascular_conditions = ["高血压", "心脏病", "心律不齐", "冠心病", "hypertension", "heart disease"]
        has_cardiovascular = any(
            any(cv in str(cond).lower() for cv in cardiovascular_conditions)
            for cond in all_conditions
        )
        
        if has_cardiovascular:
            # 限制高强度动作
            high_intensity_keywords = ["爆发", "冲刺", "跳跃", "波比跳", "burpee", "sprint", "plyometric"]
            if any(kw in exercise_name.lower() for kw in high_intensity_keywords):
                logger.debug(f"安全过滤: {exercise_name} - 心血管疾病不适合高强度动作")
                return False
        
        # 骨质疏松
        osteoporosis_conditions = ["骨质疏松", "osteoporosis"]
        has_osteoporosis = any(
            any(op in str(cond).lower() for op in osteoporosis_conditions)
            for cond in all_conditions
        )
        
        if has_osteoporosis:
            # 限制高冲击动作
            high_impact_keywords = ["跳跃", "跑步", "跳绳", "波比跳", "jump", "running", "plyometric"]
            if any(kw in exercise_name.lower() for kw in high_impact_keywords):
                logger.debug(f"安全过滤: {exercise_name} - 骨质疏松不适合高冲击动作")
                return False

        return True

    def _check_equipment_availability(
        self,
        exercise: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> bool:
        """检查器械可用性"""
        if not user_profile:
            return True

        available_equipment = user_profile.get("available_equipment", [])
        if not available_equipment:
            return True  # 未指定器械限制

        # 获取动作所需器械（可能是字符串或列表）
        required_equipment = exercise.get("equipment", "")
        if not required_equipment:
            return True  # 无器械要求（自重训练）

        # 统一转换为列表处理
        if isinstance(required_equipment, str):
            required_equipment_list = [required_equipment]
        elif isinstance(required_equipment, list):
            required_equipment_list = required_equipment
        else:
            return True  # 未知类型，默认通过

        # 检查是否有任意一个所需器械在可用列表中
        if "全部" in available_equipment:
            return True  # 用户拥有全部器械

        # 检查是否有交集（任意一个所需器械可用即可）
        for req_equip in required_equipment_list:
            if req_equip in available_equipment:
                return True  # 找到可用器械

        # 没有任何可用器械
        logger.debug(f"器械过滤: {exercise.get('exercise_name_zh')} - 需要 {required_equipment_list}，可用 {available_equipment}")
        return False

    def _assess_training_volume(
        self,
        exercise: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> float:
        """评估训练容量合理性"""
        volume_data = exercise.get("training_volume", {})
        if not volume_data:
            return 0.8  # 无训练容量数据,给默认分

        mev = volume_data.get("mev", 0)
        mav = volume_data.get("mav", 0)
        mrv = volume_data.get("mrv", 0)

        # 基于MEV/MAV/MRV评分
        if mev and mav and mrv:
            # 完整数据,高分
            return 1.0
        elif mev or mav:
            # 部分数据,中分
            return 0.9
        else:
            # 无数据,低分
            return 0.7

    def _extract_muscle_keywords(self, query: str) -> List[str]:
        """从查询中提取肌肉关键词"""
        muscle_mapping = {
            "胸": ["胸大肌", "胸部", "Chest", "Pectoralis"],
            "背": ["背阔肌", "背部", "Back", "Latissimus"],
            "肩": ["三角肌", "肩部", "Shoulder", "Deltoid"],
            "臂": ["肱二头肌", "肱三头肌", "手臂", "Biceps", "Triceps"],
            "腿": ["股四头肌", "腘绳肌", "腿部", "Quadriceps", "Hamstrings"],
            "臀": ["臀大肌", "臀部", "Glutes"],
            "腹": ["腹直肌", "腹肌", "腹部", "Abs", "Rectus Abdominis"],
            "核心": ["核心", "Core"]
        }

        keywords = []
        query_lower = query.lower()

        for key, muscles in muscle_mapping.items():
            if key in query or any(m.lower() in query_lower for m in muscles):
                keywords.extend(muscles)

        return list(set(keywords))  # 去重

    # ============ 辅助方法 ============

    def _empty_layer_result(
        self,
        layer_name: str,
        error: Optional[str] = None
    ) -> LayerExecutionResult:
        """创建空的层级结果"""
        return LayerExecutionResult(
            layer_name=layer_name,
            success=False,
            results=[],
            execution_time_ms=0.0,
            confidence=0.0,
            metadata={},
            error=error
        )

    def _build_final_result(
        self,
        query: str,
        domain: str,
        layer1: LayerExecutionResult,
        layer2: LayerExecutionResult,
        layer3: LayerExecutionResult,
        start_time: datetime
    ) -> ThreeLayerResult:
        """构建最终结果"""
        # 确定最终结果来源
        if layer3.success and layer3.results:
            final_results = layer3.results
            reasoning = f"三层检索完成: Layer1({len(layer1.results)}) → Layer2({len(layer2.results)}) → Layer3({len(layer3.results)}) 最终推荐"
        elif layer2.success and layer2.results:
            final_results = layer2.results[:10]
            reasoning = f"部分检索: Layer1({len(layer1.results)}) → Layer2({len(layer2.results)}) 图谱推荐"
        elif layer1.success and layer1.results:
            final_results = layer1.results[:10]
            reasoning = f"基础检索: Layer1({len(layer1.results)}) 向量推荐"
        else:
            final_results = []
            reasoning = "检索失败: 未找到任何结果"

        # 计算总置信度
        layer_confidences = [
            layer1.confidence * 0.3,
            layer2.confidence * 0.4,
            layer3.confidence * 0.3
        ]
        total_confidence = sum(layer_confidences)

        # 计算总耗时
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        return ThreeLayerResult(
            query=query,
            domain=domain,
            final_results=final_results,
            layer_1_result=layer1,
            layer_2_result=layer2,
            layer_3_result=layer3,
            total_confidence=total_confidence,
            total_execution_time_ms=total_time,
            reasoning=reasoning,
            metadata={
                "neo4j_direct_used": layer2.metadata.get("source") == "neo4j_direct",
                "layer_execution_times": {
                    "layer1": layer1.execution_time_ms,
                    "layer2": layer2.execution_time_ms,
                    "layer3": layer3.execution_time_ms
                },
                "stats": self.get_stats()
            }
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


# ============ 模块导出 ============

__all__ = [
    "TrueThreeLayerEngine",
    "ThreeLayerResult",
    "LayerExecutionResult",
    "Neo4jConnectionManager"
]
