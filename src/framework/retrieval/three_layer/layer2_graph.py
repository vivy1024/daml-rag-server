# -*- coding: utf-8 -*-
"""
三层检索引擎 - Layer 2 图谱关系推理
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp

from .models import LayerExecutionResult

logger = logging.getLogger(__name__)


class Layer2GraphMixin:
    """Layer 2: 图谱关系推理 Mixin"""

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
        """通过Neo4j直连查询图谱（使用连接池）

        框架层领域无关：Cypher模板从领域适配器获取
        """
        start_time = datetime.now()

        try:
            # 从查询中提取关键词
            keywords = self._extract_muscle_keywords(query)
            graph_results = []

            # 从filters中提取过滤条件
            filter_values = None
            if filters:
                filter_values = filters.get("available_equipment", [])

            # 从领域适配器获取Cypher模板（框架层领域无关）
            if not self.domain_adapter:
                logger.warning("  ⚠️ 未配置领域适配器，无法执行Neo4j查询")
                return self._empty_layer_result("Layer2-Graph", error="未配置领域适配器")

            cypher_templates = self.domain_adapter.get_cypher_templates()
            result_mapping = self.domain_adapter.get_cypher_result_mapping()

            # 选择合适的Cypher模板
            if filter_values:
                cypher_template = cypher_templates.get("entity_search_with_filter")
            else:
                cypher_template = cypher_templates.get("entity_search")

            if not cypher_template:
                logger.warning("  ⚠️ 领域适配器未提供Cypher模板")
                return self._empty_layer_result("Layer2-Graph", error="未提供Cypher模板")

            # 优先使用连接池管理器
            if self.connection_pool_manager and self.connection_pool_manager.neo4j_pool:
                logger.debug("  → 使用Neo4j连接池")
                async with self.connection_pool_manager.get_neo4j_session() as session:
                    for keyword in keywords[:3]:  # 限制关键词数量
                        if filter_values:
                            result = await session.run(
                                cypher_template,
                                keyword=keyword,
                                filter_values=filter_values,
                                limit=top_k
                            )
                        else:
                            result = await session.run(
                                cypher_template,
                                keyword=keyword,
                                limit=top_k
                            )

                        async for record in result:
                            item = {"source": "neo4j_pool", "score": 0.8}
                            for cypher_field, output_field in result_mapping.items():
                                value = record.get(cypher_field)
                                if cypher_field in ["mev", "mav", "mrv"]:
                                    if "training_volume" not in item:
                                        item["training_volume"] = {}
                                    item["training_volume"][cypher_field] = value
                                else:
                                    item[output_field] = value if value is not None else ""
                            graph_results.append(item)

            # 降级：使用传统Neo4jConnectionManager
            elif keywords and self.neo4j_manager:
                logger.debug("  → 使用传统Neo4j连接管理器")
                with self.neo4j_manager.get_session() as session:
                    for keyword in keywords[:3]:  # 限制关键词数量
                        if filter_values:
                            result = session.run(
                                cypher_template,
                                keyword=keyword,
                                filter_values=filter_values,
                                limit=top_k
                            )
                        else:
                            result = session.run(
                                cypher_template,
                                keyword=keyword,
                                limit=top_k
                            )

                        for record in result:
                            item = {"source": "neo4j_direct", "score": 0.8}
                            for cypher_field, output_field in result_mapping.items():
                                value = record.get(cypher_field)
                                if cypher_field in ["mev", "mav", "mrv"]:
                                    if "training_volume" not in item:
                                        item["training_volume"] = {}
                                    item["training_volume"][cypher_field] = value
                                else:
                                    item[output_field] = value if value is not None else ""
                            graph_results.append(item)

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
                    "keywords": keywords,
                    "filter_applied": bool(filter_values)
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
        """Neo4j直连降级查询（无向量结果）

        框架层领域无关：Cypher模板从领域适配器获取
        """
        start_time = datetime.now()

        try:
            keywords = self._extract_muscle_keywords(query)
            graph_results = []

            # 从领域适配器获取Cypher模板（框架层领域无关）
            if not self.domain_adapter:
                logger.warning("  ⚠️ 未配置领域适配器，无法执行Neo4j降级查询")
                return self._empty_layer_result("Layer2-Graph-Fallback", error="未配置领域适配器")

            cypher_templates = self.domain_adapter.get_cypher_templates()
            result_mapping = self.domain_adapter.get_cypher_result_mapping()
            cypher_template = cypher_templates.get("entity_search")

            if not cypher_template:
                logger.warning("  ⚠️ 领域适配器未提供Cypher模板")
                return self._empty_layer_result("Layer2-Graph-Fallback", error="未提供Cypher模板")

            if keywords and self.neo4j_manager:
                with self.neo4j_manager.get_session() as session:
                    for keyword in keywords[:3]:  # 限制关键词数量
                        result = session.run(
                            cypher_template,
                            keyword=keyword,
                            limit=top_k
                        )

                        for record in result:
                            item = {"source": "neo4j_direct_fallback", "score": 0.7}
                            for cypher_field, output_field in result_mapping.items():
                                value = record.get(cypher_field)
                                if cypher_field in ["mev", "mav", "mrv"]:
                                    if "training_volume" not in item:
                                        item["training_volume"] = {}
                                    item["training_volume"][cypher_field] = value
                                else:
                                    item[output_field] = value if value is not None else ""
                            graph_results.append(item)

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
                    "keywords": keywords
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
            _headers = {}
            if self._internal_api_token:
                _headers["X-Internal-Token"] = self._internal_api_token
            async with aiohttp.ClientSession(headers=_headers) as session:
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
                                "exercise_id": payload.get("exercise_id", ""),
                                "id": payload.get("exercise_id", ""),
                                "exercise_name_zh": payload.get("name_zh", ""),
                                "exercise_name_en": payload.get("name_en", ""),
                                "name_zh": payload.get("name_zh", ""),
                                "name_en": payload.get("name_en", ""),
                                "difficulty": payload.get("difficulty", ""),
                                "equipment": payload.get("equipment_zh", ""),
                                "equipment_zh": payload.get("equipment_zh", ""),
                                "target_muscle": payload.get("primary_muscle_zh", ""),
                                "primary_muscle_zh": payload.get("primary_muscle_zh", ""),
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
            _headers = {}
            if self._internal_api_token:
                _headers["X-Internal-Token"] = self._internal_api_token
            async with aiohttp.ClientSession(headers=_headers) as session:
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
                                "exercise_id": payload.get("exercise_id", ""),
                                "id": payload.get("exercise_id", ""),
                                "exercise_name_zh": payload.get("name_zh", ""),
                                "exercise_name_en": payload.get("name_en", ""),
                                "name_zh": payload.get("name_zh", ""),
                                "name_en": payload.get("name_en", ""),
                                "difficulty": payload.get("difficulty", ""),
                                "equipment": payload.get("equipment_zh", ""),
                                "equipment_zh": payload.get("equipment_zh", ""),
                                "target_muscle": payload.get("primary_muscle_zh", ""),
                                "primary_muscle_zh": payload.get("primary_muscle_zh", ""),
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

    def _query_neo4j_contraindications_sync(
        self,
        exercise_name: str,
        user_conditions: list
    ) -> list:
        """
        同步查询Neo4j中动作的禁忌症关系（CONTRAINDICATED_FOR）

        通过exercise名称模糊匹配，返回与用户健康状况相关的禁忌信息。
        此方法为同步方法，需要通过asyncio.to_thread()在async上下文中调用。
        """
        if not self.neo4j_available or not self.neo4j_manager:
            return []

        try:
            query = """
            MATCH (e:Exercise)-[r:CONTRAINDICATED_FOR]->(injury:InjuryType)
            WHERE e.name_zh CONTAINS $exercise_name
               OR e.name CONTAINS $exercise_name
            RETURN
              injury.name_zh AS injury_name_zh,
              injury.name_en AS injury_name_en,
              injury.category_zh AS category_zh,
              r.severity AS severity,
              r.risk_level AS risk_level,
              r.reason AS reason,
              r.severity_score AS severity_score,
              injury.affected_body_parts AS body_parts
            ORDER BY r.severity_score DESC
            """

            with self.neo4j_manager.get_session() as session:
                result = session.run(query, {"exercise_name": exercise_name})
                records = [record.data() for record in result]

            if not records:
                return []

            # 过滤出与用户健康状况匹配的禁忌
            matched = []
            user_conditions_lower = [str(c).lower() for c in user_conditions if c]

            for record in records:
                if record.get("injury_name_zh") is None:
                    continue

                injury_name = (record.get("injury_name_zh") or "").lower()
                injury_name_en = (record.get("injury_name_en") or "").lower()
                category = (record.get("category_zh") or "").lower()
                body_parts = record.get("body_parts") or []
                if isinstance(body_parts, str):
                    body_parts = [body_parts]
                body_parts_lower = [bp.lower() for bp in body_parts]

                for cond in user_conditions_lower:
                    if not cond:
                        continue
                    if (cond in injury_name or injury_name in cond or
                        cond in injury_name_en or injury_name_en in cond or
                        cond in category or category in cond or
                        any(cond in bp or bp in cond for bp in body_parts_lower)):
                        matched.append(record)
                        break

            return matched

        except Exception as e:
            logger.warning(f"Neo4j禁忌症查询失败（降级到payload方式）: {e}")
            return []

    def _extract_muscle_keywords(self, query: str) -> List[str]:
        """
        从查询中提取关键词

        框架层领域无关（Requirements 6.1, 6.2）：
        - 关键词映射从领域适配器获取
        - 如果没有适配器，返回空列表
        """
        if not self.domain_adapter:
            logger.debug("未配置领域适配器，无法提取关键词")
            return []

        keyword_mapping = self.domain_adapter.get_keyword_mapping()

        keywords = []
        query_lower = query.lower()

        for key, synonyms in keyword_mapping.items():
            if key in query or any(s.lower() in query_lower for s in synonyms):
                keywords.extend(synonyms)

        return list(set(keywords))  # 去重
