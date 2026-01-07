# -*- coding: utf-8 -*-
"""
智能缓存系统测试

测试缓存系统的核心功能：
1. 基本缓存操作（get/put）
2. 基于DAG模板的预加载
3. 缓存一致性验证
4. 缓存统计

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any

# 导入被测试的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework.storage.intelligent_cache_system import (
    IntelligentCacheSystem,
    SmartCacheManager,
    CacheConfig,
    CacheLevel
)


@pytest.fixture
def cache_config():
    """缓存配置"""
    return CacheConfig(
        enable_memory_cache=True,
        enable_redis_cache=False,  # 测试时禁用Redis
        memory_cache_size=100,
        memory_cache_ttl=3600,
        enable_preloading=True,
        preload_threshold=0.7
    )


@pytest.fixture
def cache_system(cache_config):
    """缓存系统实例"""
    return IntelligentCacheSystem(redis_client=None, config=cache_config)


@pytest.fixture
def cache_manager(cache_system):
    """缓存管理器实例"""
    return SmartCacheManager(cache_system)


@pytest.fixture
def mock_dag_template():
    """模拟DAG模板"""
    template = Mock()
    template.template_id = "complete_training_plan"
    template.name = "完整训练计划"
    template.required_tools = [
        "get-user-profile",
        "contraindications-checker",
        "intelligent-exercise-selector"
    ]
    template.optional_tools = [
        "tdee-calculator",
        "rpe-recommender"
    ]
    template.tool_dependencies = {
        "get-user-profile": [],
        "contraindications-checker": ["get-user-profile"],
        "intelligent-exercise-selector": ["contraindications-checker"]
    }
    template.parallel_groups = [
        ["get-user-profile"],
        ["contraindications-checker", "tdee-calculator"],
        ["intelligent-exercise-selector"]
    ]
    return template


@pytest.fixture
def sample_user_profile():
    """示例用户档案"""
    return {
        "user_id": "test_user_123",
        "basic_info": {
            "age": 25,
            "gender": "male",
            "weight": 70,
            "height": 175
        },
        "fitness_config": {
            "fitness_level": "intermediate",
            "training_days_per_week": 4
        },
        "fitness_goals": ["增肌", "力量提升"]
    }


class TestIntelligentCacheSystem:
    """测试智能缓存系统"""

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self, cache_system, sample_user_profile):
        """测试基本缓存操作"""
        tool_name = "get_user_profile"
        params = {"user_id": "test_user_123"}
        user_id = "test_user_123"
        test_data = {"profile": "test_data"}

        # 测试存储
        await cache_system.put(tool_name, params, user_id, test_data)

        # 测试获取
        cached_data = await cache_system.get(tool_name, params, user_id)
        assert cached_data == test_data

        # 验证统计
        stats = cache_system.get_statistics()
        assert stats["stats"]["hits"] == 1
        assert stats["stats"]["misses"] == 0

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_system):
        """测试缓存未命中"""
        tool_name = "nonexistent_tool"
        params = {"param": "value"}
        user_id = "test_user"

        result = await cache_system.get(tool_name, params, user_id)
        assert result is None

        stats = cache_system.get_statistics()
        assert stats["stats"]["misses"] == 1

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, cache_system):
        """测试缓存TTL过期"""
        tool_name = "tdee_calculator"
        params = {"weight": 70, "height": 175}
        user_id = "test_user"
        test_data = {"tdee": 2500}

        # 存储数据（TTL=1秒，用于测试）
        cache_system.tool_specific_configs[tool_name]["ttl"] = 1
        await cache_system.put(tool_name, params, user_id, test_data)

        # 立即获取应该成功
        cached_data = await cache_system.get(tool_name, params, user_id)
        assert cached_data == test_data

        # 等待TTL过期
        await asyncio.sleep(1.1)

        # 再次获取应该失败
        expired_data = await cache_system.get(tool_name, params, user_id)
        assert expired_data is None

    @pytest.mark.asyncio
    async def test_identify_preloadable_tools(self, cache_system, mock_dag_template):
        """测试识别可预加载工具"""
        preloadable = cache_system._identify_preloadable_tools(mock_dag_template)

        # 验证识别结果
        assert isinstance(preloadable, list)
        assert len(preloadable) > 0

        # 验证只包含配置为可预加载的工具
        for tool in preloadable:
            assert tool in cache_system.tool_specific_configs
            assert cache_system.tool_specific_configs[tool].get("preload", False)

    @pytest.mark.asyncio
    async def test_sort_tools_by_priority(self, cache_system, mock_dag_template):
        """测试工具优先级排序"""
        tools = ["intelligent_exercise_selector", "get_user_profile", "tdee_calculator"]
        sorted_tools = cache_system._sort_tools_by_priority(tools, mock_dag_template)

        # 验证get_user_profile应该排在最前面
        assert sorted_tools[0] == "get_user_profile"

    @pytest.mark.asyncio
    async def test_cache_consistency_validation_identical(self, cache_system):
        """测试缓存一致性验证 - 相同结果"""
        tool_name = "tdee_calculator"
        params = {"weight": 70, "height": 175}
        user_id = "test_user"
        test_data = {"tdee": 2500, "bmr": 1800}

        # 存储缓存
        await cache_system.put(tool_name, params, user_id, test_data)

        # 验证一致性（相同数据）
        validation = await cache_system.validate_cache_consistency(
            tool_name, params, user_id, test_data
        )

        assert validation["has_cached"] is True
        assert validation["is_consistent"] is True
        assert validation["drift_detected"] is False
        assert validation["recommendation"] == "use_cached"

    @pytest.mark.asyncio
    async def test_cache_consistency_validation_different(self, cache_system):
        """测试缓存一致性验证 - 不同结果"""
        tool_name = "tdee_calculator"
        params = {"weight": 70, "height": 175}
        user_id = "test_user"
        cached_data = {"tdee": 2500, "bmr": 1800}
        fresh_data = {"tdee": 2600, "bmr": 1900}  # 不同的数据

        # 存储缓存
        await cache_system.put(tool_name, params, user_id, cached_data)

        # 验证一致性（不同数据）
        validation = await cache_system.validate_cache_consistency(
            tool_name, params, user_id, fresh_data
        )

        assert validation["has_cached"] is True
        assert validation["is_consistent"] is False
        assert validation["drift_detected"] is True
        assert len(validation["differences"]) > 0
        assert validation["recommendation"] == "use_fresh_and_update_cache"

    @pytest.mark.asyncio
    async def test_compare_dicts(self, cache_system):
        """测试字典比较"""
        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"a": 1, "b": 2, "c": 3}

        is_consistent, differences = cache_system._compare_dicts(dict1, dict2, "test_tool")
        assert is_consistent is True
        assert len(differences) == 0

        # 测试不同的字典
        dict3 = {"a": 1, "b": 2, "c": 4}
        is_consistent, differences = cache_system._compare_dicts(dict1, dict3, "test_tool")
        assert is_consistent is False
        assert len(differences) > 0

    @pytest.mark.asyncio
    async def test_compare_lists(self, cache_system):
        """测试列表比较"""
        list1 = [1, 2, 3, 4, 5]
        list2 = [1, 2, 3, 4, 5]

        is_consistent, differences = cache_system._compare_lists(list1, list2, "test_tool")
        assert is_consistent is True
        assert len(differences) == 0

        # 测试不同的列表
        list3 = [1, 2, 3, 4, 6]
        is_consistent, differences = cache_system._compare_lists(list1, list3, "test_tool")
        assert is_consistent is False
        assert len(differences) > 0


class TestSmartCacheManager:
    """测试智能缓存管理器"""

    @pytest.mark.asyncio
    async def test_get_tool_result_with_cache(self, cache_manager, sample_user_profile):
        """测试带缓存的工具结果获取"""
        tool_name = "get_user_profile"
        params = {"user_id": "test_user_123"}
        user_id = "test_user_123"
        expected_result = {"profile": "data"}

        # 模拟执行函数
        execute_func = AsyncMock(return_value=expected_result)

        # 第一次调用（缓存未命中）
        result1 = await cache_manager.get_tool_result(
            tool_name, params, user_id, execute_func
        )
        assert result1 == expected_result
        assert execute_func.call_count == 1

        # 第二次调用（缓存命中）
        result2 = await cache_manager.get_tool_result(
            tool_name, params, user_id, execute_func
        )
        assert result2 == expected_result
        assert execute_func.call_count == 1  # 不应该再次调用

    @pytest.mark.asyncio
    async def test_update_user_pattern(self, cache_manager):
        """测试更新用户使用模式"""
        user_id = "test_user"
        tool_name = "intelligent_exercise_selector"

        # 更新模式
        cache_manager.update_user_pattern(user_id, tool_name, usage_count=3)

        # 验证
        pattern = cache_manager.get_user_pattern(user_id)
        assert pattern[tool_name] == 3

        # 再次更新
        cache_manager.update_user_pattern(user_id, tool_name, usage_count=2)
        pattern = cache_manager.get_user_pattern(user_id)
        assert pattern[tool_name] == 5

    @pytest.mark.asyncio
    async def test_validate_and_refresh_cache(self, cache_manager):
        """测试验证并刷新缓存"""
        tool_name = "tdee_calculator"
        params = {"weight": 70, "height": 175}
        user_id = "test_user"
        cached_data = {"tdee": 2500}
        fresh_data = {"tdee": 2600}

        # 先存储缓存
        await cache_manager.cache_system.put(tool_name, params, user_id, cached_data)

        # 验证并刷新
        validation = await cache_manager.validate_and_refresh_cache(
            tool_name, params, user_id, fresh_data
        )

        assert validation["drift_detected"] is True
        assert validation["recommendation"] == "use_fresh_and_update_cache"

    @pytest.mark.asyncio
    async def test_get_cache_statistics(self, cache_manager, sample_user_profile):
        """测试获取缓存统计"""
        # 执行一些操作
        tool_name = "get_user_profile"
        params = {"user_id": "test_user"}
        user_id = "test_user"
        test_data = {"profile": "data"}

        await cache_manager.cache_system.put(tool_name, params, user_id, test_data)
        await cache_manager.cache_system.get(tool_name, params, user_id)

        # 获取统计
        stats = cache_manager.get_cache_statistics()

        assert "stats" in stats
        assert "tool_configs" in stats
        assert "preload_statistics" in stats
        assert stats["stats"]["hits"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
