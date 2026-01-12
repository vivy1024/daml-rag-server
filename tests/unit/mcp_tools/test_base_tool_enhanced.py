"""
BaseMCPTool增强版测试

测试内容：
1. 版本管理功能 - Requirements 12.1-12.5
2. 三层检索标准化调用 - Requirements 17.1-17.6

版本: 1.0.0
日期: 2026-01-06
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, List
from pydantic import BaseModel

from src.applications.fitness.mcp_tools.base_tool import (
    BaseMCPTool,
    ToolMetadata,
    VersionInfo,
    ChangelogEntry,
    ThreeLayerQueryResult,
    MCPToolVersionRegistry,
    get_version_registry
)


# =============================================================================
# 测试用的具体工具实现
# =============================================================================

class TestInput(BaseModel):
    """测试输入Schema"""
    query: str
    top_k: int = 10


class TestOutput(BaseModel):
    """测试输出Schema"""
    success: bool
    results: List[Dict[str, Any]]


class TestMCPTool(BaseMCPTool):
    """测试用MCP工具"""
    
    # 设置版本信息
    _version = VersionInfo(1, 2, 3)
    _changelog = [
        ChangelogEntry(
            version="1.2.3",
            date="2026-01-06",
            changes=["测试变更1", "测试变更2"],
            breaking_changes=[]
        ),
        ChangelogEntry(
            version="1.0.0",
            date="2025-12-01",
            changes=["初始版本"],
            breaking_changes=[]
        )
    ]
    
    def get_name(self) -> str:
        return "test_tool"
    
    def get_description(self) -> str:
        return "测试工具"
    
    def get_category(self) -> str:
        return "utility"
    
    def get_input_schema(self):
        return TestInput
    
    def get_output_schema(self):
        return TestOutput
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "tool_name": self.get_name(),
            "data": {"results": []},
            "metadata": {}
        }


# =============================================================================
# 版本管理测试 - Requirements 12.1-12.5
# =============================================================================

class TestVersionManagement:
    """版本管理功能测试"""
    
    def test_version_info_creation(self):
        """测试VersionInfo创建"""
        version = VersionInfo(1, 2, 3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert str(version) == "1.2.3"
    
    def test_version_info_from_string(self):
        """测试从字符串解析版本号"""
        version = VersionInfo.from_string("2.1.0")
        assert version.major == 2
        assert version.minor == 1
        assert version.patch == 0
    
    def test_version_info_invalid_string(self):
        """测试无效版本字符串"""
        with pytest.raises(ValueError):
            VersionInfo.from_string("1.2")
        with pytest.raises(ValueError):
            VersionInfo.from_string("invalid")
    
    def test_version_comparison(self):
        """测试版本比较"""
        v1 = VersionInfo(1, 0, 0)
        v2 = VersionInfo(1, 1, 0)
        v3 = VersionInfo(2, 0, 0)
        
        assert v1 < v2
        assert v2 < v3
        assert v1 == VersionInfo(1, 0, 0)
    
    def test_version_compatibility(self):
        """测试版本兼容性 - Requirements 12.5"""
        v1 = VersionInfo(1, 0, 0)
        v2 = VersionInfo(1, 5, 0)
        v3 = VersionInfo(2, 0, 0)
        
        # 同一主版本内兼容
        assert v1.is_compatible_with(v2)
        assert v2.is_compatible_with(v1)
        
        # 不同主版本不兼容
        assert not v1.is_compatible_with(v3)
        assert not v3.is_compatible_with(v1)
    
    def test_tool_version(self):
        """测试工具版本号 - Requirements 12.1"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        assert tool.get_version() == "1.2.3"
        assert tool.get_version_info() == VersionInfo(1, 2, 3)
    
    def test_tool_changelog(self):
        """测试工具变更日志 - Requirements 12.2"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        changelog = tool.get_changelog()
        assert len(changelog) == 2
        assert changelog[0]["version"] == "1.2.3"
        assert "测试变更1" in changelog[0]["changes"]
    
    def test_tool_latest_changelog(self):
        """测试获取最新变更日志"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        latest = tool.get_latest_changelog()
        assert latest is not None
        assert latest["version"] == "1.2.3"
    
    def test_tool_compatibility_check(self):
        """测试工具版本兼容性检查 - Requirements 12.5"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        # 同一主版本兼容
        assert tool.is_compatible_with_version("1.0.0")
        assert tool.is_compatible_with_version("1.5.0")
        
        # 不同主版本不兼容
        assert not tool.is_compatible_with_version("2.0.0")
        assert not tool.is_compatible_with_version("0.9.0")
    
    def test_metadata_includes_version(self):
        """测试元数据包含版本信息"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        metadata = tool.get_metadata()
        assert metadata.version == "1.2.3"
        assert len(metadata.changelog) == 2


# =============================================================================
# 版本注册表测试 - Requirements 12.4
# =============================================================================

class TestVersionRegistry:
    """版本注册表测试"""
    
    def test_registry_singleton(self):
        """测试注册表单例"""
        registry1 = get_version_registry()
        registry2 = get_version_registry()
        assert registry1 is registry2
    
    def test_register_and_get_version(self):
        """测试注册和获取版本 - Requirements 12.4"""
        registry = MCPToolVersionRegistry()
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        registry.register(tool)
        
        version = registry.get_tool_version("test_tool")
        assert version == "1.2.3"
    
    def test_get_all_versions(self):
        """测试获取所有版本 - Requirements 12.4"""
        registry = MCPToolVersionRegistry()
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        registry.register(tool)
        
        all_versions = registry.get_all_versions()
        assert "test_tool" in all_versions
        assert all_versions["test_tool"] == "1.2.3"
    
    def test_get_tool_changelog(self):
        """测试获取工具变更日志 - Requirements 12.2"""
        registry = MCPToolVersionRegistry()
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        registry.register(tool)
        
        changelog = registry.get_tool_changelog("test_tool")
        assert changelog is not None
        assert len(changelog) == 2
    
    def test_check_compatibility(self):
        """测试兼容性检查 - Requirements 12.5"""
        registry = MCPToolVersionRegistry()
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        registry.register(tool)
        
        # 兼容
        is_compatible, message = registry.check_compatibility("test_tool", "1.0.0")
        assert is_compatible
        assert "兼容" in message
        
        # 不兼容
        is_compatible, message = registry.check_compatibility("test_tool", "2.0.0")
        assert not is_compatible
        assert "不兼容" in message
        
        # 工具不存在
        is_compatible, message = registry.check_compatibility("nonexistent", "1.0.0")
        assert not is_compatible
        assert "未注册" in message


# =============================================================================
# 三层检索标准化测试 - Requirements 17.1-17.6
# =============================================================================

class TestThreeLayerStandardization:
    """三层检索标准化测试"""
    
    @pytest.fixture
    def mock_three_layer_engine(self):
        """创建模拟的三层检索引擎"""
        engine = AsyncMock()
        
        # 模拟Layer结果
        layer1_result = Mock()
        layer1_result.success = True
        layer1_result.results = [{"id": 1, "name": "test1"}]
        layer1_result.confidence = 0.9
        layer1_result.execution_time_ms = 100
        
        layer2_result = Mock()
        layer2_result.success = True
        layer2_result.results = [{"id": 1, "name": "test1"}]
        layer2_result.confidence = 0.85
        layer2_result.execution_time_ms = 150
        
        layer3_result = Mock()
        layer3_result.success = True
        layer3_result.results = [{"id": 1, "name": "test1"}]
        layer3_result.confidence = 0.95
        layer3_result.execution_time_ms = 50
        
        # 模拟完整结果
        result = Mock()
        result.final_results = [{"id": 1, "name": "test1"}]
        result.layer_1_result = layer1_result
        result.layer_2_result = layer2_result
        result.layer_3_result = layer3_result
        result.total_confidence = 0.9
        result.reasoning = "测试推理"
        
        engine.execute_three_layer_query = AsyncMock(return_value=result)
        
        return engine
    
    @pytest.mark.asyncio
    async def test_execute_three_layer_query_success(self, mock_three_layer_engine):
        """测试三层检索成功调用 - Requirements 17.2"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=mock_three_layer_engine
        )
        
        result = await tool.execute_three_layer_query(
            query="测试查询",
            user_profile={"fitness_level": "intermediate"},
            filters={"muscle_group": "胸"},
            top_k=10
        )
        
        assert result.success
        assert len(result.results) == 1
        assert result.confidence == 0.9
        assert "layer1" in result.layer_stats
        assert "layer2" in result.layer_stats
        assert "layer3" in result.layer_stats
    
    @pytest.mark.asyncio
    async def test_execute_three_layer_query_with_user_profile(self, mock_three_layer_engine):
        """测试三层检索传递用户档案 - Requirements 17.3"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=mock_three_layer_engine
        )
        
        user_profile = {
            "fitness_level": "intermediate",
            "injuries": ["膝盖"],
            "available_equipment": ["哑铃", "杠铃"]
        }
        
        await tool.execute_three_layer_query(
            query="测试查询",
            user_profile=user_profile,
            top_k=10
        )
        
        # 验证用户档案被传递
        mock_three_layer_engine.execute_three_layer_query.assert_called_once()
        call_args = mock_three_layer_engine.execute_three_layer_query.call_args
        assert call_args.kwargs["user_profile"] == user_profile
    
    @pytest.mark.asyncio
    async def test_execute_three_layer_query_with_filters(self, mock_three_layer_engine):
        """测试三层检索传递过滤条件 - Requirements 17.4"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=mock_three_layer_engine
        )
        
        filters = {
            "muscle_group": "胸",
            "difficulty_level": "intermediate",
            "force_type": "push"
        }
        
        await tool.execute_three_layer_query(
            query="测试查询",
            filters=filters,
            top_k=10
        )
        
        # 验证过滤条件被传递
        mock_three_layer_engine.execute_three_layer_query.assert_called_once()
        call_args = mock_three_layer_engine.execute_three_layer_query.call_args
        assert call_args.kwargs["filters"] == filters
    
    @pytest.mark.asyncio
    async def test_execute_three_layer_query_logs_stats(self, mock_three_layer_engine):
        """测试三层检索记录统计信息 - Requirements 17.5"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=mock_three_layer_engine
        )
        
        result = await tool.execute_three_layer_query(
            query="测试查询",
            top_k=10
        )
        
        # 验证统计信息
        assert "layer1" in result.layer_stats
        assert result.layer_stats["layer1"]["success"] == True
        assert result.layer_stats["layer1"]["count"] == 1
        assert result.layer_stats["layer1"]["confidence"] == 0.9
        
        assert "layer2" in result.layer_stats
        assert "layer3" in result.layer_stats
    
    @pytest.mark.asyncio
    async def test_execute_three_layer_query_no_engine(self):
        """测试三层检索引擎未注入时的处理 - Requirements 17.6"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None  # 未注入
        )
        
        result = await tool.execute_three_layer_query(
            query="测试查询",
            top_k=10
        )
        
        assert not result.success
        assert "未初始化" in result.reasoning
    
    @pytest.mark.asyncio
    async def test_execute_three_layer_query_failure_handling(self):
        """测试三层检索失败处理 - Requirements 17.6"""
        # 创建会抛出异常的引擎
        engine = AsyncMock()
        engine.execute_three_layer_query = AsyncMock(
            side_effect=Exception("模拟错误")
        )
        
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=engine
        )
        
        result = await tool.execute_three_layer_query(
            query="测试查询",
            top_k=10
        )
        
        assert not result.success
        assert "fallback_used" in result.layer_stats
        assert result.layer_stats["fallback_used"] == True


# =============================================================================
# 执行监控测试
# =============================================================================

class TestExecutionMonitoring:
    """执行监控测试"""
    
    @pytest.mark.asyncio
    async def test_execute_with_monitoring_includes_version(self):
        """测试执行结果包含版本信息 - Requirements 12.3"""
        tool = TestMCPTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        result = await tool.execute_with_monitoring({
            "query": "测试",
            "top_k": 10
        })
        
        assert result["metadata"]["tool_version"] == "1.2.3"
        assert result["metadata"]["tool_name"] == "test_tool"
    
    @pytest.mark.asyncio
    async def test_execute_with_monitoring_error_includes_version(self):
        """测试错误结果也包含版本信息"""
        class FailingTool(TestMCPTool):
            async def execute(self, input_data):
                raise ValueError("测试错误")
        
        tool = FailingTool(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        result = await tool.execute_with_monitoring({
            "query": "测试",
            "top_k": 10
        })
        
        assert not result["success"]
        assert result["metadata"]["tool_version"] == "1.2.3"


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
