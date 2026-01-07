# -*- coding: utf-8 -*-
"""GraphRAG统一查询接口

MCO统一GraphRAG入口 - 为所有MCP提供Neo4j+Qdrant访问

功能：
1. 语义向量检索 (Qdrant)
2. 图关系查询 (Neo4j)
3. 混合检索 (Vector Recall + Graph Filter)
4. 增强推理生成 (Phase 3.5)

优势：
- 复用已有基础设施：DAML-RAG已部署的Neo4j(3,654节点) + Qdrant
- 避免重复部署：其他TypeScript MCP无需安装数据库依赖
- 统一入口：所有MCP通过MCP协议调用MCO的GraphRAG
- 多层次推理：图关系 + 专家知识 + 个性化
"""

import logging
from typing import Dict, List, Optional, Literal, TypedDict, Union
from enum import Enum

logger = logging.getLogger(__name__)

# 导入SearchResult类
try:
    from .graph.vector_search_engine import SearchResult
except ImportError:
    # 如果导入失败，定义一个简单的SearchResult类型
    class SearchResult:
        def __init__(self, id, score, payload):
            self.id = id
            self.score = score
            self.payload = payload

# 定义精确的搜索结果类型，避免使用Any
class GraphRAGResult(TypedDict):
    """GraphRAG搜索结果类型定义"""
    exercise_id: Optional[str]
    node_id: Optional[str]
    id: Optional[str]
    name: Optional[str]
    similarity: Optional[float]
    score: Optional[float]
    primary_movers: Optional[List[str]]
    synergists: Optional[List[str]]
    stabilizers: Optional[List[str]]
    antagonists: Optional[List[str]]
    joint_actions: Optional[List[str]]
    activation_level: Optional[float]
    risk_level: Optional[str]
    category: Optional[str]
    equipment: Optional[str]
    difficulty: Optional[str]
    domain: Optional[str]
    payload: Optional[Dict[str, Union[str, float, List[str]]]]



class QueryType(str, Enum):
    """查询类型枚举"""
    SEMANTIC_SEARCH = "semantic_search"  # 纯向量语义搜索
    GRAPH_QUERY = "graph_query"          # 纯Neo4j图查询
    HYBRID = "hybrid"                     # 混合检索（向量召回+图过滤）


class Domain(str, Enum):
    """领域枚举"""
    FITNESS_EXERCISES = "fitness_exercises"  # 健身动作库
    NUTRITION = "nutrition"                  # 营养食物
    REHABILITATION = "rehabilitation"        # 康复训练
    TRAINING = "training"                    # 训练计划
    GENERAL = "general"                      # 通用


class GraphRAGQueryTool:
    """
    GraphRAG统一查询工具

    复用DAML-RAG已有组件：
    - KnowledgeGraphFull (kg_full.py)
    - Neo4jManager (neo4j_manager.py)
    - VectorSearchEngine (vector_search_engine.py)
    """
    
    def __init__(self, kg_full):
        """
        初始化GraphRAG查询工具

        Args:
            kg_full: KnowledgeGraphFull实例（已在DAML-RAG中初始化）
        """
        self.kg = kg_full
        self.neo4j = kg_full.neo4j if hasattr(kg_full, 'neo4j') else None
        self.vector_search = kg_full.vector_search if hasattr(kg_full, 'vector_search') else None

        logger.info("✅ GraphRAG查询工具已初始化 (复用已有Neo4j+Qdrant)")

        # 统计信息
        self.stats = {
            "total_queries": 0,
            "semantic_queries": 0,
            "graph_queries": 0,
            "hybrid_queries": 0
        }
    
    async def query(self, input: dict) -> dict:
        """
        统一GraphRAG查询接口 - 支持真正的三层检索架构

        Args:
            input: {
                "query_type": "semantic_search" | "graph_query" | "hybrid" | "three_layer",
                "domain": "fitness_exercises" | "nutrition" | "rehabilitation" | "general",
                "query_text": str,                    # 查询文本
                "filters": Optional[Dict],            # 过滤条件
                "top_k": int = 10,                    # 返回结果数量
                "min_similarity": float = 0.5,        # 最小相似度（仅向量检索）
                "return_reason": bool = True,         # 是否返回推荐理由
                "user_profile": Optional[Dict] = None,# 用户档案（个性化推理）
                "reason_types": Optional[List] = None,# 推理类型
                "optimize_tokens": bool = True,       # 是否优化token消耗
                "max_results": int = 5,               # 优化后最多返回几个结果
                "max_reason_length": int = 200        # 推理最大字符数
            }

        Returns:
            {
                "results": List[Dict],        # 查询结果
                "query_type": str,            # 使用的查询类型
                "domain": str,                # 查询领域
                "count": int,                 # 结果数量
                "reasoning": Optional[Dict],  # 推理结果
                "three_layer_result": Optional[Dict]  # 三层检索详细信息
            }
        """
        try:
            self.stats["total_queries"] += 1

            # 1. 解析参数
            query_type = input.get("query_type", QueryType.SEMANTIC_SEARCH)
            domain = input.get("domain", Domain.GENERAL)
            query_text = input["query_text"]
            filters = input.get("filters", {})
            top_k = input.get("top_k", 10)
            min_similarity = input.get("min_similarity", 0.5)
            return_reason = input.get("return_reason", True)
            user_profile = input.get("user_profile")
            reason_types = input.get("reason_types")
            optimize_tokens = input.get("optimize_tokens", True)
            max_results = input.get("max_results", 5)
            max_reason_length = input.get("max_reason_length", 200)

            logger.info(
                f"GraphRAG查询: type={query_type}, domain={domain}, "
                f"query='{query_text[:50]}...'"
            )

            # 2. 根据查询类型执行不同逻辑
            results = []
            three_layer_info = None

            if query_type == "three_layer":
                # === 真正的三层检索架构 ===
                # Layer 1: 向量语义检索 (召回候选集)
                layer1_results = await self._semantic_search(
                    query_text, domain, top_k * 3, min_similarity, filters
                )
                logger.info(f"✓ Layer 1完成: {len(layer1_results)}个向量结果")

                # Layer 2: 图谱关系推理 (精确筛选)
                layer2_results = await self._graph_reasoning(
                    query_text, domain, layer1_results, top_k * 2
                )
                logger.info(f"✓ Layer 2完成: {len(layer2_results)}个图谱结果")

                # 选择进入Layer 3的候选
                if layer2_results:
                    candidates_for_layer3 = layer2_results
                    layer2_source = "图谱推理"
                else:
                    logger.warning("Layer 2未返回结果，使用Layer 1结果")
                    candidates_for_layer3 = layer1_results[:top_k * 2]
                    layer2_source = "向量降级"

                # Layer 3: 业务规则验证 (安全/器械/容量检查)
                layer3_results = await self._business_rules_validation(
                    query_text, candidates_for_layer3, user_profile, top_k
                )
                logger.info(f"✓ Layer 3完成: {len(layer3_results)}个通过规则验证")

                # 构建最终结果
                results = layer3_results if layer3_results else (layer2_results or layer1_results)

                # 构建三层检索信息
                three_layer_info = {
                    "layers_executed": 3,
                    "layer1": {
                        "name": "Layer 1: 向量语义检索",
                        "source": "Qdrant",
                        "count": len(layer1_results),
                        "confidence": 0.8
                    },
                    "layer2": {
                        "name": "Layer 2: 图谱关系推理",
                        "source": "Neo4j" if layer2_results else "向量降级",
                        "count": len(layer2_results),
                        "note": layer2_source
                    },
                    "layer3": {
                        "name": "Layer 3: 业务规则验证",
                        "source": "规则引擎",
                        "count": len(layer3_results),
                        "rules_applied": ["fitness_level", "safety", "equipment", "volume"]
                    },
                    "pipeline": f"向量({len(layer1_results)}) → 图谱({len(layer2_results)}) → 规则({len(layer3_results)}) → 最终({len(results)})"
                }

                self.stats["semantic_queries"] += 1

            elif query_type == QueryType.SEMANTIC_SEARCH:
                results = await self._semantic_search(
                    query_text, domain, top_k, min_similarity, filters
                )
                self.stats["semantic_queries"] += 1

            elif query_type == QueryType.GRAPH_QUERY:
                results = await self._graph_query(
                    query_text, domain, filters, top_k
                )
                self.stats["graph_queries"] += 1

            elif query_type == QueryType.HYBRID:
                results = await self._hybrid_query(
                    query_text, domain, top_k, min_similarity, filters
                )
                self.stats["hybrid_queries"] += 1

            else:
                raise ValueError(f"不支持的查询类型: {query_type}")

            
            # 3. 生成推荐理由（简化版本）
            reasoning = None
            if return_reason and results:
                count = len(results)
                domain_name = {"fitness": "健身", "nutrition": "营养", "general": "通用"}.get(domain, domain)
                reasoning = f"在{domain_name}领域找到{count}个相关结果。"
            else:
                # 安全地提取payload，处理不同的结果格式
                results_dicts = []
                for r in results or []:
                    if hasattr(r, 'payload'):
                        results_dicts.append(r.payload)
                    elif isinstance(r, dict):
                        if 'payload' in r:
                            results_dicts.append(r['payload'])
                        else:
                            # 如果没有payload字段，使用整个结果字典
                            results_dicts.append(r)
                    else:
                        # 其他情况，使用整个结果
                        results_dicts.append(r)
                reasoning = {"combined_reason": self._generate_reasoning(
                    results_dicts, query_type, domain, query_text
                    )}

            # 4. 构建返回结果
            response = {
                "results": results,
                "query_type": query_type,
                "domain": domain,
                "count": len(results),
                "reasoning": reasoning
            }

            # 如果是三层检索，添加详细信息
            if three_layer_info:
                response["three_layer_result"] = three_layer_info

            logger.info(f"✅ GraphRAG查询完成: 返回{response['count']}个结果")
            return response

        except Exception as e:
            logger.error(f"❌ GraphRAG查询失败: {e}", exc_info=True)
            raise
    
    async def _semantic_search(
        self, 
        query_text: str, 
        domain: str,
        top_k: int,
        min_similarity: float,
        filters: Dict
    ) -> List[Dict]:
        """
        纯向量语义搜索 (Qdrant)
        
        使用场景：模糊查询、语义相似匹配
        """
        if not self.vector_search:
            logger.warning("VectorSearchEngine未初始化，返回空结果")
            return []
        
        try:
            # 向量化查询文本
            query_vector = self.vector_search.encode(query_text)
            
            # 构建过滤条件（✅ 传递query_text用于智能过滤）
            qdrant_filters = self._build_qdrant_filters(domain, filters, query_text)
            
            # 向量检索
            results = self.vector_search.search(
                query_vector=query_vector,
                top_k=top_k,
                min_similarity=min_similarity,
                filters=qdrant_filters
            )
            
            logger.debug(f"向量检索完成: {len(results)}个结果")
            return results
            
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    async def _graph_query(
        self,
        query_text: str,
        domain: str,
        filters: Dict,
        top_k: int
    ) -> List[Dict]:
        """
        纯Neo4j图查询
        
        使用场景：关系推理、多跳查询、精确筛选
        
        注意：直接执行用户提供的Cypher查询（query_text）
        """
        if not self.neo4j:
            logger.warning("Neo4jManager未初始化，返回空结果")
            return []
        
        try:
            # 直接使用用户提供的Cypher查询
            # 不再调用_build_cypher_query，因为用户已经提供了完整的Cypher
            cypher_query = query_text
            
            # 执行Neo4j查询（注意：execute_query是同步方法，不需要await）
            results = self.neo4j.execute_query(cypher_query)
            
            logger.debug(f"图查询完成: {len(results)}个结果")
            return results
            
        except Exception as e:
            logger.error(f"图查询失败: {e}")
            return []
    
    async def _hybrid_query(
        self,
        query_text: str,
        domain: str,
        top_k: int,
        min_similarity: float,
        filters: Dict
    ) -> List[Dict]:
        """
        混合检索：向量召回 + 图过滤
        
        使用场景：既需要语义匹配又需要关系约束
        
        工作流程：
        1. 向量召回 top_k*2 个候选（召回率）
        2. Neo4j图过滤（精确率）
        3. 综合排序，返回 top_k
        """
        if not self.vector_search or not self.neo4j:
            logger.warning("GraphRAG组件未完全初始化，降级为向量检索")
            return await self._semantic_search(
                query_text, domain, top_k, min_similarity, filters
            )
        
        try:
            # Step 1: 向量召回（扩大候选集）
            query_vector = self.vector_search.encode(query_text)
            qdrant_filters = self._build_qdrant_filters(domain, filters)
            
            candidates = self.vector_search.search(
                query_vector=query_vector,
                top_k=top_k * 2,  # 召回2倍候选
                min_similarity=min_similarity * 0.8,  # 降低阈值
                filters=qdrant_filters
            )
            
            if not candidates:
                logger.info("向量召回为空，返回空结果")
                return []
            
            # Step 2: 提取候选节点ID
            candidate_ids = []
            for c in candidates:
                if isinstance(c, SearchResult):
                    node_id = c.payload.get("node_id") if c.payload else None
                elif isinstance(c, dict):
                    node_id = c.get("node_id")
                else:
                    node_id = None
                id_val = node_id or (c.payload.get("id") if isinstance(c, SearchResult) and c.payload else (c.get("id") if isinstance(c, dict) else getattr(c, "id", None)))
                if id_val:
                    candidate_ids.append(id_val)

            if not candidate_ids:
                logger.warning("候选节点无有效ID，返回向量结果")
                return candidates[:top_k]

            # Step 3: Neo4j图过滤
            cypher_filter = self._build_graph_filter_query(
                candidate_ids, domain, filters
            )

            graph_results = await self.neo4j.execute_query(cypher_filter)
            graph_id_set = {r.get("id") or r.get("node_id") for r in graph_results}

            # Step 4: 保留通过图过滤的候选
            filtered = []
            for c in candidates:
                if isinstance(c, SearchResult):
                    node_id = c.payload.get("node_id") if c.payload else None
                elif isinstance(c, dict):
                    node_id = c.get("node_id")
                else:
                    node_id = None
                id_val = node_id or (c.payload.get("id") if isinstance(c, SearchResult) and c.payload else (c.get("id") if isinstance(c, dict) else getattr(c, "id", None)))
                if id_val in graph_id_set:
                    filtered.append(c)
            
            # Step 5: 如果过滤后结果太少，补充向量结果
            if len(filtered) < top_k // 2:
                logger.info(f"图过滤结果太少({len(filtered)})，补充向量结果")
                # 保留向量检索的前top_k个（即使未通过图过滤）
                filtered = candidates[:top_k]
            
            # Step 6: 限制返回数量
            final_results = filtered[:top_k]
            
            logger.info(
                f"混合检索完成: 候选{len(candidates)} → "
                f"图过滤{len(filtered)} → 返回{len(final_results)}"
            )
            
            return final_results
            
        except Exception as e:
            logger.error(f"混合检索失败: {e}，降级为向量检索")
            return await self._semantic_search(
                query_text, domain, top_k, min_similarity, filters
            )

    async def _graph_reasoning(
        self,
        query_text: str,
        domain: str,
        vector_results: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """
        Layer 2: 图谱关系推理 (Neo4j)

        基于向量检索结果，进行图关系精确筛选和多跳推理
        """
        if not self.neo4j:
            logger.warning("Neo4j未初始化，跳过图推理")
            return []

        try:
            # 提取候选节点ID
            # 注意：Qdrant payload中使用exercise_id，Neo4j中使用id（都是整数）
            candidate_ids = []
            failed_extractions = []
            
            for i, r in enumerate(vector_results):
                id_val = None
                extraction_source = None
                
                # 尝试多种方式提取ID
                if isinstance(r, SearchResult):
                    if r.payload:
                        # 优先使用exercise_id（Qdrant标准字段）
                        if "exercise_id" in r.payload:
                            id_val = r.payload["exercise_id"]
                            extraction_source = "payload.exercise_id"
                        # 然后尝试id字段
                        elif "id" in r.payload:
                            id_val = r.payload["id"]
                            extraction_source = "payload.id"
                        # 最后尝试node_id
                        elif "node_id" in r.payload:
                            id_val = r.payload["node_id"]
                            extraction_source = "payload.node_id"
                    
                    # 如果payload中没有，尝试使用SearchResult的id
                    if id_val is None:
                        id_val = r.id
                        extraction_source = "SearchResult.id"
                        
                elif isinstance(r, dict):
                    # 字典格式，按优先级提取
                    if "exercise_id" in r:
                        id_val = r["exercise_id"]
                        extraction_source = "dict.exercise_id"
                    elif "id" in r:
                        id_val = r["id"]
                        extraction_source = "dict.id"
                    elif "node_id" in r:
                        id_val = r["node_id"]
                        extraction_source = "dict.node_id"
                else:
                    # 其他对象类型，尝试属性访问
                    id_val = getattr(r, "exercise_id", None) or getattr(r, "id", None)
                    extraction_source = "attribute"
                
                # 转换为整数并添加到候选列表
                if id_val is not None:
                    try:
                        int_id = int(id_val)
                        candidate_ids.append(int_id)
                        logger.debug(f"  ✓ 提取ID #{i+1}: {int_id} (来源: {extraction_source})")
                    except (ValueError, TypeError) as e:
                        failed_extractions.append({
                            "index": i,
                            "value": id_val,
                            "type": type(id_val).__name__,
                            "source": extraction_source,
                            "error": str(e)
                        })
                        logger.warning(f"  ✗ 无法转换ID为整数 #{i+1}: {id_val} (类型: {type(id_val).__name__}, 来源: {extraction_source})")
                else:
                    failed_extractions.append({
                        "index": i,
                        "value": None,
                        "type": type(r).__name__,
                        "source": "未找到ID字段",
                        "error": "ID字段不存在"
                    })
                    logger.warning(f"  ✗ 未找到ID字段 #{i+1} (结果类型: {type(r).__name__})")

            # 记录提取统计
            logger.info(f"→ ID提取完成: 成功{len(candidate_ids)}/{len(vector_results)}, 失败{len(failed_extractions)}")
            
            if failed_extractions:
                logger.warning(f"→ ID提取失败详情: {failed_extractions[:3]}...")  # 只显示前3个
            
            if not candidate_ids:
                logger.warning("❌ 向量结果无有效ID，跳过图推理")
                return []
            
            logger.info(f"→ 提取到{len(candidate_ids)}个候选ID: {candidate_ids[:5]}...")

            # 提取肌肉关键词（健身领域）
            muscle_keywords = self._extract_muscle_keywords(query_text)
            logger.info(f"→ 提取到{len(muscle_keywords)}个肌肉关键词: {muscle_keywords[:3]}...")
            
            graph_results = []

            # 构建Cypher查询
            cypher_query = self._build_three_layer_cypher_query(
                candidate_ids, muscle_keywords, domain, top_k
            )
            logger.debug(f"→ Cypher查询: {cypher_query[:200]}...")

            # 执行图查询（需要传递参数）
            query_params = {
                "candidate_ids": candidate_ids,
                "muscle_keywords": muscle_keywords,
                "limit": top_k
            }
            logger.info(f"→ 执行Neo4j图查询 (候选ID数: {len(candidate_ids)}, 肌肉关键词数: {len(muscle_keywords)})")
            
            try:
                results = self.neo4j.execute_query(cypher_query, query_params)
                logger.info(f"→ Neo4j返回{len(results)}条记录")
            except Exception as neo4j_error:
                logger.error(f"❌ Neo4j查询失败: {neo4j_error}", exc_info=True)
                logger.error(f"   查询参数: candidate_ids={candidate_ids[:5]}..., muscle_keywords={muscle_keywords[:3]}...")
                return []

            # 转换为统一格式
            for i, record in enumerate(results):
                try:
                    graph_result = {
                        "id": record.get("id"),
                        "name_zh": record.get("name_zh", ""),
                        "name_en": record.get("name_en", ""),
                        "equipment": record.get("equipment", ""),
                        "difficulty": record.get("difficulty", ""),
                        "target_muscle": record.get("target_muscle", ""),
                        "relationship_type": record.get("relationship_type", ""),
                        "training_volume": {
                            "mev": record.get("mev"),
                            "mav": record.get("mav"),
                            "mrv": record.get("mrv")
                        },
                        "source": "neo4j_graph_reasoning",
                        "score": 0.9  # 图查询结果默认高分
                    }
                    graph_results.append(graph_result)
                    logger.debug(f"  ✓ 转换记录 #{i+1}: ID={graph_result['id']}, 名称={graph_result['name_zh']}")
                except Exception as convert_error:
                    logger.warning(f"  ✗ 转换记录 #{i+1} 失败: {convert_error}, 记录内容: {record}")
                    continue

            logger.info(f"✓ Layer 2图谱推理完成: {len(graph_results)}个结果")
            return graph_results

        except Exception as e:
            logger.error(f"❌ Layer 2图谱推理失败: {e}", exc_info=True)
            return []

    async def _business_rules_validation(
        self,
        query_text: str,
        candidates: List[Union[Dict, SearchResult]],
        user_profile: Optional[Dict],
        top_k: int
    ) -> List[Union[Dict, SearchResult]]:
        """
        Layer 3: 业务规则验证

        应用安全、器械、训练容量等业务规则进行最终筛选
        """
        validated_results = []
        user_profile = user_profile or {}

        logger.info(f"→ Layer 3: 业务规则验证 (候选: {len(candidates)})")
        logger.info(f"→ 用户档案: fitness_level={user_profile.get('fitness_level')}, equipment={user_profile.get('available_equipment')}, health={user_profile.get('health_conditions')}")

        for i, candidate in enumerate(candidates):
            try:
                # 将SearchResult转换为Dict格式以支持.get()方法
                candidate_dict = self._normalize_candidate(candidate)
                
                exercise_name = candidate_dict.get('name_zh') or candidate_dict.get('name', '未知')
                logger.debug(f"→ 验证候选 {i+1}/{len(candidates)}: {exercise_name}")
                logger.debug(f"  - 字段: equipment={candidate_dict.get('equipment')}, difficulty={candidate_dict.get('difficulty')}")

                # 规则1: 经验等级匹配
                if not self._match_fitness_level(candidate_dict, user_profile):
                    logger.debug(f"  ✗ 规则1失败: 经验等级不匹配")
                    continue

                # 规则2: 安全性检查
                if not self._validate_safety(candidate_dict, user_profile):
                    logger.debug(f"  ✗ 规则2失败: 安全性检查未通过")
                    continue

                # 规则3: 器械可用性
                if not self._check_equipment_availability(candidate_dict, user_profile):
                    logger.debug(f"  ✗ 规则3失败: 器械不可用")
                    continue

                # 规则4: 训练容量评估
                volume_score = self._assess_training_volume(candidate_dict, user_profile)
                logger.debug(f"  ✓ 所有规则通过, 容量评分: {volume_score}")

                # 添加规则评分
                candidate_dict["rule_validation_score"] = volume_score
                candidate_dict["validation_passed"] = True
                candidate_dict["three_layer_validated"] = True

                validated_results.append(candidate)

                if len(validated_results) >= top_k:
                    break

            except Exception as e:
                logger.warning(f"规则验证异常: {e}", exc_info=True)
                continue

        logger.info(f"✓ Layer 3完成: {len(validated_results)}/{len(candidates)}通过验证")
        return validated_results

    def _normalize_candidate(self, candidate: Union[Dict, SearchResult]) -> Dict:
        """
        将SearchResult对象转换为Dict格式以支持.get()方法
        同时统一字段名（Qdrant使用_zh后缀，业务规则不使用）

        Args:
            candidate: 可能是Dict或SearchResult对象

        Returns:
            Dict格式的候选对象，字段名已统一
        """
        result = {}
        
        # 提取原始数据
        if isinstance(candidate, dict):
            result = candidate.copy()
        elif isinstance(candidate, SearchResult):
            result = candidate.payload.copy() if candidate.payload else {}
            result["id"] = result.get("id") or result.get("exercise_id") or candidate.id
            result["score"] = candidate.score
        else:
            # 未知类型，尝试转换为Dict
            try:
                result = dict(candidate)
            except Exception:
                logger.warning(f"无法转换候选对象为Dict: {type(candidate)}")
                return {}
        
        # 统一字段名：将_zh后缀的字段映射到无后缀版本
        # Qdrant: equipment_zh, name_zh, primary_muscle_zh
        # 业务规则: equipment, name, primary_muscle
        field_mappings = {
            "equipment_zh": "equipment",
            "name_zh": "name",
            "primary_muscle_zh": "primary_muscle"
        }
        
        for qdrant_field, standard_field in field_mappings.items():
            if qdrant_field in result and standard_field not in result:
                result[standard_field] = result[qdrant_field]
        
        return result

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

    def _build_three_layer_cypher_query(
        self,
        candidate_ids: List[str],
        muscle_keywords: List[str],
        domain: str,
        top_k: int
    ) -> str:
        """为三层检索构建Cypher查询"""
        # 基础查询 - 限制候选ID
        cypher = """
        MATCH (e:Exercise)
        WHERE e.id IN $candidate_ids
        """

        # 如果有肌肉关键词，添加关系查询
        if muscle_keywords:
            cypher += """
        MATCH (e)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m:Muscle)
        WHERE ANY(muscle IN $muscle_keywords
                  WHERE m.name_zh CONTAINS muscle
                     OR m.name_en CONTAINS muscle
                     OR m.name CONTAINS muscle)
        """

        cypher += """
        RETURN
            e.id AS id,
            e.name_zh AS name_zh,
            e.name_en AS name_en,
            e.equipment AS equipment,
            e.difficulty AS difficulty,
            m.name_zh AS target_muscle,
            type(r) AS relationship_type,
            m.mev AS mev,
            m.mav AS mav,
            m.mrv AS mrv
        ORDER BY
            CASE WHEN m.mev IS NOT NULL THEN 1 ELSE 0 END DESC,
            CASE WHEN type(r) = 'TARGETS_PRIMARY' THEN 1 ELSE 0 END DESC
        LIMIT $limit
        """

        return cypher

    def _match_fitness_level(self, exercise: Dict, user_profile: Dict) -> bool:
        """匹配健身经验等级"""
        if not user_profile:
            return True

        user_level = user_profile.get("fitness_level", "intermediate").lower()
        # 使用统一字段名：difficulty_zh / difficulty_en
        exercise_difficulty = (exercise.get("difficulty_zh") or exercise.get("difficulty_en") or "intermediate").lower()

        # 等级映射
        level_hierarchy = {
            "beginner": ["beginner", "easy", "novice", "初学者", "简单"],
            "intermediate": ["beginner", "intermediate", "moderate", "novice", "初学者", "中级", "中等"],
            "advanced": ["intermediate", "advanced", "hard", "elite", "中级", "高级", "困难"]
        }

        allowed_difficulties = level_hierarchy.get(user_level, ["intermediate"])
        result = any(diff in exercise_difficulty for diff in allowed_difficulties)
        
        if not result:
            logger.debug(f"    经验等级不匹配: user={user_level}, exercise={exercise_difficulty}, allowed={allowed_difficulties}")
        
        return result

    def _validate_safety(self, exercise: Dict, user_profile: Dict) -> bool:
        """安全性验证"""
        if not user_profile:
            return True

        # 检查禁忌症
        contraindications = exercise.get("contraindications", [])
        user_conditions = user_profile.get("medical_conditions", [])

        for condition in user_conditions:
            if condition in contraindications:
                logger.debug(f"安全过滤: {exercise.get('name_zh')} - 禁忌症 {condition}")
                return False

        # 年龄限制
        user_age = user_profile.get("age", 30)
        if user_age > 60:
            # 使用统一字段名：difficulty_zh / difficulty_en
            difficulty = (exercise.get("difficulty_zh") or exercise.get("difficulty_en") or "").lower()
            if "advanced" in difficulty or "elite" in difficulty or "高级" in difficulty:
                logger.debug(f"安全过滤: {exercise.get('name_zh')} - 高龄不适合高难度")
                return False

        return True

    def _check_equipment_availability(self, exercise: Dict, user_profile: Dict) -> bool:
        """检查器械可用性"""
        if not user_profile:
            return True

        available_equipment = user_profile.get("available_equipment", [])
        if not available_equipment:
            return True  # 未指定器械限制

        required_equipment = exercise.get("equipment", "")
        
        # 处理None值：Neo4j中equipment字段可能是字符串"None"或Python None
        if not required_equipment or required_equipment == "None" or required_equipment is None:
            return True  # 无器械要求，通过验证

        # 检查器械是否可用
        if required_equipment not in available_equipment and "全部" not in available_equipment:
            logger.debug(f"    器械不可用: 需要={required_equipment}, 可用={available_equipment}")
            return False

        return True

    def _assess_training_volume(self, exercise: Dict, user_profile: Dict) -> float:
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

    def _build_qdrant_filters(self, domain: str, filters: Dict, query_text: str = "") -> Optional[Dict]:
        """构建Qdrant过滤条件
        
        注意：Qdrant集合的payload结构与Neo4j不完全一致
        - fitness_exercises_v2: 没有label字段，使用collection名称区分
        - 不应该添加label过滤，会导致0结果
        
        Qdrant payload字段（fitness_exercises_v2）：
        - exercise_id, name_zh, name_en, primary_muscle_zh, equipment_zh, difficulty, search_text
        
        difficulty值映射（中文）：
        - beginner/新手 → "新手"
        - intermediate/中级 → "中级"  
        - advanced/高级 → "高级"
        
        智能过滤：
        - 查询包含"训练"/"力量"时，自动排除瑜伽、拉伸类动作
        
        返回格式：
        - 普通字段: {"field": "value"}
        - 排除字段: {"_exclude_field": ["value1", "value2"]}  # 特殊标记，由VectorSearchEngine处理
        """
        if not filters:
            filters = {}
            
        qdrant_filters = {}
        
        # 字段名映射：业务字段 → Qdrant payload字段
        field_mapping = {
            "muscle_group": "primary_muscle_zh",
            "difficulty_level": "difficulty",
            "available_equipment": "equipment_zh",
            # 以下字段不在Qdrant payload中，跳过
            "injury_history": None,
            "label": None,  # Qdrant没有label字段
        }
        
        # difficulty值映射：英文 → 中文
        difficulty_mapping = {
            "beginner": "新手",
            "intermediate": "中级",
            "advanced": "高级",
            "expert": "专家",
            # 中文值保持不变
            "新手": "新手",
            "中级": "中级",
            "高级": "高级",
            "专家": "专家",
        }
        
        # ✅ 智能过滤：根据查询文本自动添加过滤条件
        strength_keywords = ["训练", "力量", "增肌", "肌肉", "卧推", "深蹲", "硬拉", "推举", "胸部", "背部", "腿部", "肩部"]
        if any(keyword in query_text for keyword in strength_keywords):
            # 排除瑜伽、拉伸、泡沫轴等非力量训练动作
            exclude_equipment = ["瑜伽", "拉伸", "泡沫轴", "按摩球"]
            # 使用特殊标记，由VectorSearchEngine的_build_filter方法处理
            qdrant_filters["_exclude_equipment_zh"] = exclude_equipment
            logger.debug(f"智能过滤：排除非力量训练器械 {exclude_equipment}")
        
        for key, value in filters.items():
            # 跳过空值
            if value is None or value == "" or value == []:
                continue
                
            # 字段名映射
            mapped_key = field_mapping.get(key, key)
            
            # 跳过不支持的字段
            if mapped_key is None:
                logger.debug(f"跳过不支持的过滤字段: {key}")
                continue
            
            # difficulty值转换
            if mapped_key == "difficulty" and isinstance(value, str):
                mapped_value = difficulty_mapping.get(value.lower(), value)
                qdrant_filters[mapped_key] = mapped_value
                logger.debug(f"difficulty值转换: {value} → {mapped_value}")
            else:
                qdrant_filters[mapped_key] = value
        
        # 如果没有有效的过滤条件，返回None（不过滤，返回所有结果）
        if not qdrant_filters:
            logger.debug("无有效过滤条件，将返回所有向量结果")
            return None
            
        logger.debug(f"Qdrant过滤条件: {qdrant_filters}")
        return qdrant_filters
    
    def _build_cypher_query(
        self, 
        domain: str, 
        filters: Dict,
        top_k: int
    ) -> str:
        """
        构建Cypher查询
        
        根据domain和filters动态生成Cypher
        """
        # 基础查询模板
        cypher = "MATCH (n)"
        
        # 添加领域标签过滤
        if domain == Domain.FITNESS_EXERCISES:
            cypher = "MATCH (n:Exercise)"
        elif domain == Domain.NUTRITION:
            cypher = "MATCH (n:Food)"
        elif domain == Domain.REHABILITATION:
            cypher = "MATCH (n:RehabAction)"
        
        # 添加属性过滤
        where_clauses = []
        if filters:
            for key, value in filters.items():
                if isinstance(value, str):
                    where_clauses.append(f"n.{key} = '{value}'")
                elif isinstance(value, (int, float)):
                    where_clauses.append(f"n.{key} = {value}")
        
        if where_clauses:
            cypher += " WHERE " + " AND ".join(where_clauses)
        
        # 返回节点
        cypher += f" RETURN n LIMIT {top_k}"
        
        return cypher
    
    def _build_graph_filter_query(
        self,
        candidate_ids: List[str],
        domain: str,
        filters: Dict
    ) -> str:
        """
        构建图过滤查询
        
        对候选节点进行图关系约束
        """
        # 构建ID列表
        id_list = "', '".join(str(id) for id in candidate_ids)
        
        # 基础查询：匹配候选节点
        cypher = f"MATCH (n) WHERE n.id IN ['{id_list}']"
        
        # 添加关系约束（如果有）
        if filters.get("requires_relationship"):
            rel_type = filters["requires_relationship"]
            cypher += f" MATCH (n)-[:{rel_type}]->(m)"
        
        # 返回节点ID
        cypher += " RETURN n.id AS id, n"
        
        return cypher
    
    def _generate_reasoning(
        self,
        results: List[Dict],
        query_type: str,
        domain: str,
        query_text: str
    ) -> str:
        """
        生成推荐理由
        
        帮助LLM理解为什么返回这些结果
        """
        if not results:
            return f"未找到与'{query_text}'相关的{domain}领域结果，建议扩大查询范围或调整关键词。"
        
        count = len(results)
        
        # 根据查询类型生成理由
        if query_type == QueryType.SEMANTIC_SEARCH:
            # 处理不同的结果格式（对象或字典）
            scores = []
            for r in results:
                if hasattr(r, 'score'):
                    scores.append(r.score)
                elif isinstance(r, dict):
                    # 处理标准向量搜索结果
                    if 'score' in r:
                        scores.append(r['score'])
                    elif 'similarity' in r:
                        scores.append(r['similarity'])
                    # 处理训练知识数据（没有分数字段）
                    elif r.get('type') == 'training_knowledge':
                        # 训练知识没有相似度分数，使用默认值
                        scores.append(0.7)  # 默认中等相关性
                    # 处理其他类型的数据
                    else:
                        logger.debug(f"数据类型无分数字段，使用默认值: {r.get('type', 'unknown')}")
                        scores.append(0.5)  # 保守默认值
                else:
                    logger.debug(f"未知结果格式，使用默认分数: {type(r)}")
                    scores.append(0.5)

            avg_similarity = sum(scores) / len(scores) if scores else 0.0
            reason = (
                f"通过语义向量检索，在{domain}领域找到{count}个相关结果，"
                f"平均相似度{avg_similarity:.2f}。这些结果与'{query_text}'语义最接近。"
            )
        
        elif query_type == QueryType.GRAPH_QUERY:
            reason = (
                f"通过知识图谱关系推理，在{domain}领域精确匹配到{count}个结果。"
                f"这些结果满足指定的关系约束和属性条件。"
            )
        
        elif query_type == QueryType.HYBRID:
            reason = (
                f"通过混合检索（向量语义+图关系），在{domain}领域找到{count}个最佳结果。"
                f"这些结果既语义相关，又满足知识图谱的关系约束，推荐度最高。"
            )
        
        else:
            reason = f"在{domain}领域找到{count}个结果。"
        
        return reason

    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = {
            **self.stats,
            "semantic_rate": (
                f"{self.stats['semantic_queries'] / self.stats['total_queries'] * 100:.1f}%"
                if self.stats['total_queries'] > 0 else "0.0%"
            ),
            "graph_rate": (
                f"{self.stats['graph_queries'] / self.stats['total_queries'] * 100:.1f}%"
                if self.stats['total_queries'] > 0 else "0.0%"
            ),
            "hybrid_rate": (
                f"{self.stats['hybrid_queries'] / self.stats['total_queries'] * 100:.1f}%"
                if self.stats['total_queries'] > 0 else "0.0%"
            )
        }

        # BGE-M3增强器在v2.3.0架构简化中已移除
        # 保留标识以保持API兼容性
        stats["bge_m3_enabled"] = False

        return stats

