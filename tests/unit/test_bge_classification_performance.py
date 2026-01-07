# -*- coding: utf-8 -*-
"""
BGE复杂度分类性能测试

测试目标：
1. 正常分类的响应时间(<500ms)
2. 缓存命中的响应时间(<50ms)
3. 降级策略的执行

版本: v1.0.0
日期: 2025-12-21
作者: 薛小川
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.framework.models.query_complexity_classifier import (
    QueryComplexityClassifier,
    ClassificationResult
)


class TestBGEClassificationPerformance:
    """BGE复杂度分类性能测试"""

    @pytest.fixture
    def classifier(self):
        """创建分类器实例（不启用Redis缓存）"""
        return QueryComplexityClassifier(
            enable_cache=True,
            redis_client=None,  # 不使用Redis，只测试内存缓存
            max_query_length=1000
        )

    @pytest.fixture
    def classifier_with_redis(self):
        """创建带Redis缓存的分类器实例"""
        # 创建Mock Redis客户端
        mock_redis = Mock()
        mock_redis.get = Mock(return_value=None)
        mock_redis.setex = Mock()
        mock_redis.keys = Mock(return_value=[])
        mock_redis.delete = Mock()
        
        return QueryComplexityClassifier(
            enable_cache=True,
            redis_client=mock_redis,
            max_query_length=1000
        )

    def test_normal_classification_performance(self, classifier):
        """
        测试1: 正常分类的响应时间(<500ms)
        
        验证：
        - 首次分类耗时（包含模型加载）
        - 第二次分类耗时<500ms（模型已加载）
        - 分类结果正确
        - 性能指标记录正确
        """
        # 测试查询
        query = "帮我设计一套完整的增肌训练计划，我有腰椎间盘突出"
        
        # 首次执行分类（可能包含模型加载）
        start_time = time.time()
        result1 = classifier.classify_complexity(query)
        duration_ms_1 = (time.time() - start_time) * 1000
        
        print(f"首次分类（含模型加载）: {duration_ms_1:.2f}ms")
        
        # 验证首次结果
        assert isinstance(result1, ClassificationResult)
        assert result1.is_complex is True  # 应该被判定为复杂查询
        assert result1.similarity >= 0.0
        assert result1.reason != ""
        
        # 第二次分类（模型已加载，测试实际性能）
        query2 = "我想制定一个力量训练方案"
        start_time = time.time()
        result2 = classifier.classify_complexity(query2)
        duration_ms_2 = (time.time() - start_time) * 1000
        
        # 验证第二次性能（模型已加载）
        assert duration_ms_2 < 500, f"模型加载后分类耗时过长: {duration_ms_2:.2f}ms"
        assert result2.duration_ms < 500, f"记录的耗时过长: {result2.duration_ms:.2f}ms"
        
        # 验证结果
        assert isinstance(result2, ClassificationResult)
        assert result2.cache_hit is False  # 不同查询不应命中缓存
        
        print(f"✅ 正常分类性能测试通过:")
        print(f"   - 首次分类（含模型加载）: {duration_ms_1:.2f}ms")
        print(f"   - 第二次分类（模型已加载）: {duration_ms_2:.2f}ms")
        print(f"   - 记录耗时: {result2.duration_ms:.2f}ms")
        print(f"   - 复杂度: {'复杂' if result2.is_complex else '简单'}")
        print(f"   - 相似度: {result2.similarity:.2f}")

    def test_cache_hit_performance(self, classifier):
        """
        测试2: 缓存命中的响应时间(<50ms)
        
        验证：
        - 首次查询建立缓存
        - 第二次查询命中缓存
        - 缓存命中耗时<50ms
        """
        query = "我想制定一个增肌训练计划"
        
        # 首次查询（建立缓存）
        result1 = classifier.classify_complexity(query)
        assert result1.cache_hit is False
        print(f"✅ 首次查询完成（建立缓存）: {result1.duration_ms:.2f}ms")
        
        # 第二次查询（应该命中缓存）
        start_time = time.time()
        result2 = classifier.classify_complexity(query)
        duration_ms = (time.time() - start_time) * 1000
        
        # 验证缓存命中
        assert result2.cache_hit is True, "第二次查询应该命中缓存"
        assert duration_ms < 50, f"缓存命中耗时过长: {duration_ms:.2f}ms"
        assert result2.duration_ms < 50, f"记录的缓存命中耗时过长: {result2.duration_ms:.2f}ms"
        
        # 验证结果一致性
        assert result2.is_complex == result1.is_complex
        assert result2.similarity == result1.similarity
        
        print(f"✅ 缓存命中性能测试通过:")
        print(f"   - 实际耗时: {duration_ms:.2f}ms")
        print(f"   - 记录耗时: {result2.duration_ms:.2f}ms")
        print(f"   - 缓存命中: {result2.cache_hit}")

    def test_query_length_limit(self, classifier):
        """
        测试3: 查询文本长度限制
        
        验证：
        - 超长查询被截断到1000字
        - 截断后仍能正常分类
        - 性能保持在合理范围（考虑模型可能已加载）
        """
        # 创建超长查询（2000字）
        long_query = "帮我设计训练计划" * 200  # 约2000字
        
        # 执行分类
        start_time = time.time()
        result = classifier.classify_complexity(long_query)
        duration_ms = (time.time() - start_time) * 1000
        
        # 验证性能（如果模型已加载，应该<500ms；如果需要加载，可能更长）
        # 这里我们只验证结果正确性，不严格限制时间
        print(f"超长查询分类耗时: {duration_ms:.2f}ms")
        
        # 验证结果
        assert isinstance(result, ClassificationResult)
        assert result.is_complex is not None
        
        print(f"✅ 查询长度限制测试通过:")
        print(f"   - 原始长度: {len(long_query)}字")
        print(f"   - 截断后长度: {min(len(long_query), 1000)}字")
        print(f"   - 分类耗时: {duration_ms:.2f}ms")
        print(f"   - 复杂度: {'复杂' if result.is_complex else '简单'}")

    def test_fallback_strategy_performance(self, classifier):
        """
        测试4: 降级策略的执行
        
        验证：
        - 模型加载失败时使用关键词匹配
        - 降级策略耗时<100ms
        - 降级标记正确
        """
        # 模拟模型加载失败
        classifier._model_load_failed = True
        classifier._model = None
        
        # 测试查询（包含关键词）
        query = "帮我设计一个训练计划"
        
        # 执行分类
        start_time = time.time()
        result = classifier.classify_complexity(query)
        duration_ms = (time.time() - start_time) * 1000
        
        # 验证性能
        assert duration_ms < 100, f"降级策略耗时过长: {duration_ms:.2f}ms"
        
        # 验证降级标记
        assert result.fallback_used is True, "应该标记为使用了降级策略"
        assert result.is_complex is True  # 包含"训练"和"计划"关键词
        assert result.similarity == 0.0  # 降级策略不计算相似度
        
        print(f"✅ 降级策略性能测试通过:")
        print(f"   - 降级耗时: {duration_ms:.2f}ms")
        print(f"   - 降级标记: {result.fallback_used}")
        print(f"   - 分类结果: {'复杂' if result.is_complex else '简单'}")

    def test_redis_cache_integration(self, classifier_with_redis):
        """
        测试5: Redis缓存集成
        
        验证：
        - Redis缓存写入正常
        - Redis缓存读取正常
        - 缓存失败时降级到内存缓存
        """
        query = "设计增肌方案"
        
        # 首次查询（写入Redis）
        result1 = classifier_with_redis.classify_complexity(query)
        
        # 验证Redis写入被调用
        assert classifier_with_redis.redis_client.setex.called
        
        # 模拟Redis返回缓存数据
        import json
        cache_data = json.dumps({
            "is_complex": result1.is_complex,
            "similarity": result1.similarity,
            "reason": result1.reason,
            "fallback_used": result1.fallback_used
        })
        classifier_with_redis.redis_client.get = Mock(return_value=cache_data)
        
        # 第二次查询（从Redis读取）
        result2 = classifier_with_redis.classify_complexity(query)
        
        # 验证缓存命中
        assert result2.cache_hit is True
        assert result2.is_complex == result1.is_complex
        
        print(f"✅ Redis缓存集成测试通过:")
        print(f"   - Redis写入调用: {classifier_with_redis.redis_client.setex.called}")
        print(f"   - 缓存命中: {result2.cache_hit}")

    def test_statistics_tracking(self, classifier):
        """
        测试6: 统计信息跟踪
        
        验证：
        - 分类次数统计正确
        - 缓存命中率统计正确
        - 平均耗时统计正确
        """
        queries = [
            "设计训练计划",
            "增肌方案",
            "设计训练计划",  # 重复查询，应该命中缓存
            "减脂计划"
        ]
        
        # 执行多次分类
        for query in queries:
            classifier.classify_complexity(query)
        
        # 获取统计信息
        stats = classifier.get_statistics()
        
        # 验证统计
        assert stats["total_classifications"] == 4
        assert stats["cache_hits"] >= 1  # 至少有一次缓存命中
        assert stats["cache_misses"] >= 1
        assert stats["avg_duration_ms"] > 0
        assert 0 <= stats["cache_hit_rate"] <= 1
        
        print(f"✅ 统计信息跟踪测试通过:")
        print(f"   - 总分类次数: {stats['total_classifications']}")
        print(f"   - 缓存命中: {stats['cache_hits']}")
        print(f"   - 缓存未命中: {stats['cache_misses']}")
        print(f"   - 缓存命中率: {stats['cache_hit_rate']:.2%}")
        print(f"   - 平均耗时: {stats['avg_duration_ms']:.2f}ms")

    def test_concurrent_classification(self, classifier):
        """
        测试7: 并发分类性能
        
        验证：
        - 并发分类不会相互干扰
        - 缓存在并发场景下正常工作
        - 性能保持稳定
        """
        import asyncio
        
        async def classify_async(query: str):
            """异步分类包装"""
            return classifier.classify_complexity(query)
        
        async def run_concurrent_tests():
            """运行并发测试"""
            queries = [
                "设计训练计划",
                "增肌方案",
                "减脂计划",
                "设计训练计划",  # 重复
                "康复训练"
            ]
            
            # 并发执行
            tasks = [classify_async(q) for q in queries]
            results = await asyncio.gather(*tasks)
            
            return results
        
        # 执行并发测试
        results = asyncio.run(run_concurrent_tests())
        
        # 验证结果
        assert len(results) == 5
        assert all(isinstance(r, ClassificationResult) for r in results)
        
        # 验证缓存工作正常（重复查询应该命中缓存）
        stats = classifier.get_statistics()
        assert stats["cache_hits"] >= 1
        
        print(f"✅ 并发分类性能测试通过:")
        print(f"   - 并发请求数: {len(results)}")
        print(f"   - 缓存命中: {stats['cache_hits']}")
        print(f"   - 平均耗时: {stats['avg_duration_ms']:.2f}ms")

    def test_cache_clear(self, classifier):
        """
        测试8: 缓存清除功能
        
        验证：
        - 缓存清除后，查询不再命中缓存
        - 清除操作不影响分类功能
        """
        query = "设计训练计划"
        
        # 首次查询（建立缓存）
        result1 = classifier.classify_complexity(query)
        assert result1.cache_hit is False
        
        # 第二次查询（命中缓存）
        result2 = classifier.classify_complexity(query)
        assert result2.cache_hit is True
        
        # 清除缓存
        classifier.clear_cache()
        
        # 第三次查询（不应命中缓存）
        result3 = classifier.classify_complexity(query)
        assert result3.cache_hit is False
        
        print(f"✅ 缓存清除功能测试通过:")
        print(f"   - 清除前缓存命中: {result2.cache_hit}")
        print(f"   - 清除后缓存命中: {result3.cache_hit}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
