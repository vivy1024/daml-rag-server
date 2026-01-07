# -*- coding: utf-8 -*-
"""
QueryComplexityClassifier - 查询复杂度分类器（v5.0性能优化版）

基于BGE向量模型的语义相似度分类

v5.0 性能优化版：
- 查询文本长度限制（1000字）
- BGE分类结果缓存（Redis + 内存）
- 规则引擎降级策略
- 优化BGE模型加载和推理

核心算法：
1. BGE-M3向量模型：1024维中文语义向量
2. 余弦相似度：衡量查询与复杂示例的语义距离
3. 智能降级：向量失败时使用关键词兜底
4. 结果缓存：避免重复计算

性能目标：
- 正常分类：<500ms
- 缓存命中：<50ms
- 降级策略：<100ms

版本: v5.0.0 (性能优化版)
日期: 2025-12-21
作者: 薛小川
"""

import logging
import hashlib
import time
import numpy as np
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """分类结果"""
    is_complex: bool
    similarity: float
    reason: str
    cache_hit: bool = False
    duration_ms: float = 0.0
    fallback_used: bool = False


class QueryComplexityClassifier:
    """
    查询复杂度分类器（性能优化版）

    核心算法：BGE向量模型 + 余弦相似度 + 结果缓存

    工作流程：
    1. 查询文本长度限制（1000字）
    2. 检查缓存（内存 + Redis）
    3. 懒加载BGE模型（首次调用）
    4. 编码查询为向量
    5. 计算与复杂查询库的相似度
    6. 根据阈值分类
    7. 缓存结果
    8. 返回结果和理由

    性能优化：
    - 查询文本截断：避免超长文本影响性能
    - 双层缓存：内存缓存（L1）+ Redis缓存（L2）
    - 规则引擎降级：模型失败时使用关键词匹配
    - 向量库预计算：复杂查询向量提前计算

    设计原则：
    - 懒加载：首次使用时才加载模型
    - 缓存：复杂查询向量库预计算 + 分类结果缓存
    - 降级：模型加载失败时使用硬编码关键词
    - 监控：完整日志和统计信息

    Example:
        >>> classifier = QueryComplexityClassifier()
        >>> result = classifier.classify_complexity(
        ...     "帮我设计一套增肌训练计划，我有腰椎间盘突出"
        ... )
        >>> print(f"复杂度: {result.is_complex}, 相似度: {result.similarity:.2f}")
        >>> print(f"缓存命中: {result.cache_hit}, 耗时: {result.duration_ms:.2f}ms")
    """

    def __init__(
        self,
        complex_query_examples: Optional[List[str]] = None,
        similarity_threshold: float = 0.7,
        moderate_threshold: float = 0.5,
        use_fallback_keywords: bool = True,
        model_name: str = "BAAI/bge-m3",
        max_query_length: int = 1000,
        enable_cache: bool = True,
        cache_ttl: int = 1800,  # 30分钟
        redis_client: Optional[Any] = None
    ):
        """
        初始化分类器

        Args:
            complex_query_examples: 复杂查询示例列表（用于构建向量库）
            similarity_threshold: 高相似度阈值（>= 则判定为复杂）
            moderate_threshold: 低相似度阈值（< 则判定为简单）
            use_fallback_keywords: 是否使用硬编码关键词作为兜底
            model_name: BGE模型名称（默认 BAAI/bge-m3，1024维）
            max_query_length: 最大查询文本长度（默认1000字）
            enable_cache: 是否启用缓存
            cache_ttl: 缓存过期时间（秒）
            redis_client: Redis客户端（可选）
        """
        self.similarity_threshold = similarity_threshold
        self.moderate_threshold = moderate_threshold
        self.use_fallback_keywords = use_fallback_keywords
        self.model_name = model_name
        self.max_query_length = max_query_length
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.redis_client = redis_client

        # 使用全局模型缓存管理器（不再在__init__中加载模型）
        from .model_cache_manager import ModelCacheManager
        self.model_cache = ModelCacheManager.get_instance()
        self._model_load_failed = False

        # 复杂查询向量库（懒计算）
        self.complex_query_examples = complex_query_examples or self._get_default_examples()
        self._complex_query_vectors = None

        # 硬编码关键词（兜底策略）
        self.complex_keywords = [
            '计划', '训练', '方案', '设计', '康复', '个性化',
            '增肌', '减脂', '力量', '周期', '损伤', '营养',
            'plan', 'training', 'program', 'design', 'personalized'
        ]

        # 内存缓存（L1）
        self._memory_cache: Dict[str, ClassificationResult] = {}
        self._memory_cache_max_size = 1000

        # 统计信息
        self._stats = {
            "total_classifications": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "fallback_used": 0,
            "total_duration_ms": 0.0,
            "avg_duration_ms": 0.0
        }

        logger.info(
            f"[QueryComplexityClassifier] 初始化完成: "
            f"model={model_name}, "
            f"threshold={similarity_threshold}, "
            f"max_length={max_query_length}, "
            f"cache_enabled={enable_cache}, "
            f"examples={len(self.complex_query_examples)}"
        )

    def _get_default_examples(self) -> List[str]:
        """
        获取默认的复杂查询示例库

        Returns:
            List[str]: 复杂查询示例列表
        """
        return [
            # 训练计划类（高复杂度）
            "帮我设计一套增肌训练计划，我有腰椎间盘突出，需要避免压迫脊柱的动作",
            "三个月减脂10公斤，需要详细的营养和训练方案，包括每周训练安排和饮食计划",
            "制定一个适合新手的全身力量训练计划，一周训练3天，每次60分钟",

            # 康复方案类（高复杂度）
            "肩关节损伤后如何恢复训练？需要具体的康复动作和训练强度建议",
            "膝盖受伤康复期间，如何继续进行力量训练而不影响恢复？",
            "腰椎间盘突出患者的康复训练方案，包括禁忌动作和安全替代方案",

            # 营养设计类（高复杂度）
            "设计一份增肌期的详细营养计划，包括每日热量分配和食物选择",
            "如何制定减脂期的饮食方案？需要考虑蛋白质摄入和热量赤字",
            "素食人群的增肌营养方案，如何保证蛋白质摄入充足？",

            # 综合咨询类（高复杂度）
            "全面的健身指导，包括训练、营养、补剂、休息等各方面建议",
            "从零开始健身，需要完整的指导方案，包括目标设定、计划制定、动作学习",

            # 周期化训练类（高复杂度）
            "如何进行周期化训练？需要详细的分期计划和强度安排",
            "力量周期训练的设计原则和实施方案",

            # 特殊人群类（高复杂度）
            "中老年人的力量训练方案，需要注意哪些事项？",
            "孕期和产后的安全训练计划，如何恢复核心力量？"
        ]

    def _load_model(self):
        """
        从全局缓存获取BGE模型

        如果模型加载失败，标记失败状态，后续使用硬编码关键词兜底
        """
        if self._model_load_failed:
            return  # 之前加载失败过，不再尝试

        try:
            # 从全局缓存获取模型
            self._model = self.model_cache.get_bge_model(self.model_name)
            
            if self._model is None:
                logger.warning(
                    "[QueryComplexityClassifier] ⚠️ BGE模型加载失败，将使用硬编码关键词兜底策略"
                )
                self._model_load_failed = True
                return

            # 预计算复杂查询向量库
            self._precompute_complex_vectors()

        except Exception as e:
            logger.warning(
                f"[QueryComplexityClassifier] ⚠️ BGE模型加载失败: {e}，将使用硬编码关键词兜底策略"
            )
            self._model_load_failed = True
            self._model = None

    def _precompute_complex_vectors(self):
        """
        预计算复杂查询向量库

        将所有复杂查询示例编码为向量，缓存起来，避免重复计算
        """
        if self._model is None or self._complex_query_vectors is not None:
            return

        try:
            logger.info(
                f"[QueryComplexityClassifier] 预计算复杂查询向量库（{len(self.complex_query_examples)} 条）..."
            )
            self._complex_query_vectors = self._model.encode(
                self.complex_query_examples,
                convert_to_numpy=True,
                normalize_embeddings=True  # L2归一化，便于余弦相似度计算
            )
            logger.info("[QueryComplexityClassifier] ✅ 复杂查询向量库预计算完成")

        except Exception as e:
            logger.error(f"[QueryComplexityClassifier] ❌ 复杂查询向量库预计算失败: {e}")
            self._complex_query_vectors = None

    def classify_complexity(
        self,
        query: str
    ) -> ClassificationResult:
        """
        分类查询复杂度（性能优化版）

        Args:
            query: 用户查询

        Returns:
            ClassificationResult: 分类结果（包含性能指标）

        Example:
            >>> result = classifier.classify_complexity(
            ...     "设计增肌训练计划"
            ... )
            >>> print(f"复杂: {result.is_complex}, 耗时: {result.duration_ms:.2f}ms")
        """
        start_time = time.time()
        self._stats["total_classifications"] += 1

        # 步骤1: 查询文本长度限制（1000字）
        original_query = query
        if len(query) > self.max_query_length:
            query = query[:self.max_query_length]
            logger.info(
                f"[QueryComplexityClassifier] ⚠️ 查询文本过长，截断到{self.max_query_length}字 "
                f"(原长度: {len(original_query)}字)"
            )

        # 步骤2: 检查缓存
        if self.enable_cache:
            cached_result = self._get_from_cache(query)
            if cached_result:
                duration_ms = (time.time() - start_time) * 1000
                cached_result.duration_ms = duration_ms
                self._stats["cache_hits"] += 1
                self._stats["total_duration_ms"] += duration_ms
                self._update_avg_duration()
                logger.info(
                    f"[QueryComplexityClassifier] ✅ 缓存命中 "
                    f"(耗时: {duration_ms:.2f}ms)"
                )
                return cached_result

        self._stats["cache_misses"] += 1

        # 步骤3: 尝试使用BGE模型
        if not self._model_load_failed:
            self._load_model()

        # 步骤4: 如果模型可用，使用向量相似度
        if self._model is not None and self._complex_query_vectors is not None:
            result = self._classify_by_vector(query)
        # 步骤5: 降级到硬编码关键词
        elif self.use_fallback_keywords:
            result = self._classify_by_keywords(query)
            result.fallback_used = True
            self._stats["fallback_used"] += 1
        # 步骤6: 无法分类，默认为复杂（保守策略）
        else:
            logger.warning("[QueryComplexityClassifier] ⚠️ 无法分类查询复杂度，默认使用教师模型")
            result = ClassificationResult(
                is_complex=True,
                similarity=0.0,
                reason="无法分类，默认使用教师模型（保守策略）",
                fallback_used=True
            )
            self._stats["fallback_used"] += 1

        # 步骤7: 计算耗时
        duration_ms = (time.time() - start_time) * 1000
        result.duration_ms = duration_ms
        self._stats["total_duration_ms"] += duration_ms
        self._update_avg_duration()

        # 步骤8: 缓存结果
        if self.enable_cache:
            self._save_to_cache(query, result)

        logger.info(
            f"[QueryComplexityClassifier] ✅ 分类完成 "
            f"(复杂度: {'复杂' if result.is_complex else '简单'}, "
            f"相似度: {result.similarity:.2f}, "
            f"耗时: {duration_ms:.2f}ms, "
            f"降级: {result.fallback_used})"
        )

        return result

    def _get_cache_key(self, query: str) -> str:
        """
        生成缓存键

        Args:
            query: 查询文本

        Returns:
            str: 缓存键（MD5哈希）
        """
        # 使用MD5哈希生成缓存键
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        return f"bge_classification:{query_hash}"

    def _get_from_cache(self, query: str) -> Optional[ClassificationResult]:
        """
        从缓存获取分类结果

        Args:
            query: 查询文本

        Returns:
            Optional[ClassificationResult]: 缓存的分类结果，如果未命中返回None
        """
        cache_key = self._get_cache_key(query)

        # 步骤1: 检查内存缓存（L1）
        if cache_key in self._memory_cache:
            result = self._memory_cache[cache_key]
            result.cache_hit = True
            logger.debug(f"[QueryComplexityClassifier] L1缓存命中: {cache_key}")
            return result

        # 步骤2: 检查Redis缓存（L2）
        if self.redis_client:
            try:
                import json
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    result = ClassificationResult(
                        is_complex=data["is_complex"],
                        similarity=data["similarity"],
                        reason=data["reason"],
                        cache_hit=True,
                        fallback_used=data.get("fallback_used", False)
                    )
                    # 回填到内存缓存
                    self._memory_cache[cache_key] = result
                    logger.debug(f"[QueryComplexityClassifier] L2缓存命中: {cache_key}")
                    return result
            except Exception as e:
                logger.warning(f"[QueryComplexityClassifier] Redis缓存读取失败: {e}")

        return None

    def _save_to_cache(self, query: str, result: ClassificationResult):
        """
        保存分类结果到缓存

        Args:
            query: 查询文本
            result: 分类结果
        """
        cache_key = self._get_cache_key(query)

        # 步骤1: 保存到内存缓存（L1）
        # 如果缓存已满，删除最旧的条目（简单LRU）
        if len(self._memory_cache) >= self._memory_cache_max_size:
            # 删除第一个条目（最旧）
            first_key = next(iter(self._memory_cache))
            del self._memory_cache[first_key]

        self._memory_cache[cache_key] = result
        logger.debug(f"[QueryComplexityClassifier] 保存到L1缓存: {cache_key}")

        # 步骤2: 保存到Redis缓存（L2）
        if self.redis_client:
            try:
                import json
                cache_data = {
                    "is_complex": result.is_complex,
                    "similarity": result.similarity,
                    "reason": result.reason,
                    "fallback_used": result.fallback_used
                }
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(cache_data)
                )
                logger.debug(f"[QueryComplexityClassifier] 保存到L2缓存: {cache_key}")
            except Exception as e:
                logger.warning(f"[QueryComplexityClassifier] Redis缓存写入失败: {e}")

    def _update_avg_duration(self):
        """更新平均耗时统计"""
        total = self._stats["total_classifications"]
        if total > 0:
            self._stats["avg_duration_ms"] = self._stats["total_duration_ms"] / total

    def _classify_by_vector(
        self,
        query: str
    ) -> ClassificationResult:
        """
        基于向量相似度分类

        Args:
            query: 用户查询

        Returns:
            ClassificationResult: 分类结果
        """
        try:
            # 编码查询
            query_vector = self._model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True
            )[0]

            # 计算与复杂查询库的相似度（已归一化，直接点积即为余弦相似度）
            similarities = np.dot(self._complex_query_vectors, query_vector)
            max_similarity = float(np.max(similarities))
            max_idx = int(np.argmax(similarities))

            # 根据阈值分类
            if max_similarity >= self.similarity_threshold:
                reason = (
                    f"与复杂查询示例高度相似（相似度={max_similarity:.2f}）: "
                    f"'{self.complex_query_examples[max_idx][:30]}...'"
                )
                logger.info(f"[QueryComplexityClassifier] ✅ [BGE分类] 复杂查询（相似度={max_similarity:.2f}）")
                return ClassificationResult(
                    is_complex=True,
                    similarity=max_similarity,
                    reason=reason
                )

            elif max_similarity < self.moderate_threshold:
                reason = f"与复杂查询示例相似度低（{max_similarity:.2f}）"
                logger.info(f"[QueryComplexityClassifier] ✅ [BGE分类] 简单查询（相似度={max_similarity:.2f}）")
                return ClassificationResult(
                    is_complex=False,
                    similarity=max_similarity,
                    reason=reason
                )

            else:
                # 中等相似度，需要其他因素判断
                reason = (
                    f"中等复杂度（相似度={max_similarity:.2f}），"
                    "建议结合Few-Shot判断"
                )
                logger.info(
                    f"[QueryComplexityClassifier] ⚠️ [BGE分类] 中等复杂度（相似度={max_similarity:.2f}），"
                    "需要额外判断"
                )
                # 中等复杂度时，偏向保守，使用教师模型
                return ClassificationResult(
                    is_complex=True,
                    similarity=max_similarity,
                    reason=reason
                )

        except Exception as e:
            logger.error(f"[QueryComplexityClassifier] ❌ BGE向量分类失败: {e}，降级到关键词匹配")
            return self._classify_by_keywords(query)

    def _classify_by_keywords(
        self,
        query: str
    ) -> ClassificationResult:
        """
        基于硬编码关键词分类（兜底策略）

        Args:
            query: 用户查询

        Returns:
            ClassificationResult: 分类结果
        """
        query_lower = query.lower()

        for keyword in self.complex_keywords:
            if keyword in query_lower:
                reason = f"匹配复杂查询关键词: '{keyword}'"
                logger.info(f"[QueryComplexityClassifier] ✅ [关键词兜底] 复杂查询（关键词='{keyword}'）")
                return ClassificationResult(
                    is_complex=True,
                    similarity=0.0,
                    reason=reason,
                    fallback_used=True
                )

        reason = "未匹配任何复杂查询关键词"
        logger.info("[QueryComplexityClassifier] ✅ [关键词兜底] 简单查询")
        return ClassificationResult(
            is_complex=False,
            similarity=0.0,
            reason=reason,
            fallback_used=True
        )

    def add_complex_example(self, example: str):
        """
        添加复杂查询示例到向量库

        Args:
            example: 复杂查询示例

        Note:
            添加后需要重新预计算向量库
        """
        if example not in self.complex_query_examples:
            self.complex_query_examples.append(example)
            logger.info(f"[QueryComplexityClassifier] 新增复杂查询示例: {example[:50]}...")

            # 重新预计算向量库
            if self._model is not None:
                self._complex_query_vectors = None
                self._precompute_complex_vectors()

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取分类器统计信息（包含性能指标）

        Returns:
            Dict[str, Any]: 统计信息
        """
        cache_hit_rate = 0.0
        if self._stats["total_classifications"] > 0:
            cache_hit_rate = self._stats["cache_hits"] / self._stats["total_classifications"]

        fallback_rate = 0.0
        if self._stats["total_classifications"] > 0:
            fallback_rate = self._stats["fallback_used"] / self._stats["total_classifications"]

        return {
            # 模型信息
            "model_loaded": self._model is not None,
            "model_name": self.model_name if self._model else "N/A",
            "complex_examples_count": len(self.complex_query_examples),
            "similarity_threshold": self.similarity_threshold,
            "moderate_threshold": self.moderate_threshold,
            "use_fallback": self.use_fallback_keywords,
            "vector_cache_ready": self._complex_query_vectors is not None,
            
            # 性能配置
            "max_query_length": self.max_query_length,
            "cache_enabled": self.enable_cache,
            "cache_ttl": self.cache_ttl,
            "memory_cache_size": len(self._memory_cache),
            "memory_cache_max_size": self._memory_cache_max_size,
            
            # 性能统计
            "total_classifications": self._stats["total_classifications"],
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"],
            "cache_hit_rate": cache_hit_rate,
            "fallback_used": self._stats["fallback_used"],
            "fallback_rate": fallback_rate,
            "avg_duration_ms": self._stats["avg_duration_ms"],
            "total_duration_ms": self._stats["total_duration_ms"]
        }

    def clear_cache(self):
        """清除所有缓存"""
        self._memory_cache.clear()
        logger.info("[QueryComplexityClassifier] 内存缓存已清除")
        
        if self.redis_client:
            try:
                # 清除所有BGE分类缓存
                pattern = "bge_classification:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"[QueryComplexityClassifier] Redis缓存已清除（{len(keys)}个键）")
            except Exception as e:
                logger.warning(f"[QueryComplexityClassifier] Redis缓存清除失败: {e}")
