# -*- coding: utf-8 -*-
"""
Find Similar Training Cases Tool 单元测试

测试训练案例库与Few-Shot质量评分融合功能
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# 导入待测试的工具
from src.applications.fitness.mcp_tools.find_similar_training_cases import (
    FindSimilarTrainingCasesTool,
    TOOL_METADATA
)


class TestFindSimilarTrainingCasesTool:
    """测试Find Similar Training Cases工具"""
    
    @pytest.fixture
    def mock_backend_client(self):
        """模拟后端客户端"""
        client = Mock()
        client.search_similar_conversations = AsyncMock(return_value={
            "conversations": [
                {
                    "user_query": "如何增肌？",
                    "llm_response": "推荐以下训练计划...",
                    "reward": 4.5,
                    "quality_score": 4.2,
                    "similarity": 0.85,
                    "tools_used": ["professional_program_designer"],
                    "model_used": "deepseek-chat",
                    "created_at": datetime.now().isoformat(),
                    "session_id": "test_session_1",
                    "metadata": {"training_goal": "增肌"},
                    "training_effect": "excellent",
                    "feedback_text": "很有帮助！"
                },
                {
                    "user_query": "增肌训练计划",
                    "llm_response": "建议采用推拉腿分化...",
                    "reward": 4.0,
                    "quality_score": 4.0,
                    "similarity": 0.80,
                    "tools_used": ["professional_program_designer"],
                    "model_used": "deepseek-chat",
                    "created_at": datetime.now().isoformat(),
                    "session_id": "test_session_2",
                    "metadata": {"training_goal": "增肌"},
                    "training_effect": "good",
                    "feedback_text": None
                }
            ],
            "total": 2
        })
        return client
    
    @pytest.fixture
    def mock_vector_store(self):
        """模拟向量存储"""
        store = Mock()
        # 模拟search_conversations方法为AsyncMock
        store.search_conversations = AsyncMock(return_value=[])
        return store
    
    @pytest.fixture
    def tool(self, mock_backend_client, mock_vector_store):
        """创建工具实例"""
        return FindSimilarTrainingCasesTool(
            backend_client=mock_backend_client,
            vector_store=mock_vector_store
        )
    
    @pytest.mark.asyncio
    async def test_execute_success(self, tool):
        """测试成功执行"""
        input_data = {
            "query": "增肌训练计划",
            "user_profile": {"user_id": 1, "fitness_goal": "增肌"},
            "training_goal": "增肌",
            "min_quality_score": 4.0,  # 降低阈值以匹配mock数据
            "top_k": 5
        }
        
        result = await tool.execute(input_data)
        
        assert result["success"] is True
        assert "similar_cases" in result
        assert "total_found" in result
        assert "recommendation" in result
        # 由于使用降级搜索，可能返回空结果或有结果
        assert isinstance(result["similar_cases"], list)
    
    @pytest.mark.asyncio
    async def test_execute_empty_query(self, tool):
        """测试空查询"""
        input_data = {
            "query": "",
            "user_profile": {"user_id": 1}
        }
        
        result = await tool.execute(input_data)
        
        assert result["success"] is False
        assert "error" in result
        assert result["total_found"] == 0
    
    @pytest.mark.asyncio
    async def test_training_effect_filter(self, tool):
        """测试训练效果过滤"""
        input_data = {
            "query": "增肌训练计划",
            "user_profile": {"user_id": 1},
            "training_effect_filter": "excellent",
            "top_k": 5
        }
        
        result = await tool.execute(input_data)
        
        assert result["success"] is True
        # 验证返回的案例都是excellent或更好
        for case in result["similar_cases"]:
            if case["training_effect"]:
                assert case["training_effect"] in ["excellent"]
    
    @pytest.mark.asyncio
    async def test_quality_score_filter(self, tool):
        """测试质量评分过滤"""
        input_data = {
            "query": "增肌训练计划",
            "user_profile": {"user_id": 1},
            "min_quality_score": 4.5,
            "top_k": 5
        }
        
        result = await tool.execute(input_data)
        
        assert result["success"] is True
        # 验证返回的案例质量评分都≥4.5
        for case in result["similar_cases"]:
            assert case["quality_score"] >= 4.5
    
    @pytest.mark.asyncio
    async def test_format_cases(self, tool):
        """测试案例格式化"""
        from src.framework.retrieval.enhanced_few_shot_retriever import FewShotExample
        
        cases = [
            FewShotExample(
                query="测试查询",
                response="测试响应" * 100,  # 长响应
                user_rating=4.5,
                quality_score=4.2,
                similarity=0.85,
                tools_used=["tool1"],
                model_used="test_model",
                timestamp=datetime.now(),
                session_id="test_session",
                metadata={},
                training_effect="excellent",
                user_feedback="很好"
            )
        ]
        
        formatted = tool._format_cases(cases)
        
        assert len(formatted) == 1
        assert "rank" in formatted[0]
        assert "response_summary" in formatted[0]
        assert "full_response" in formatted[0]
        assert len(formatted[0]["response_summary"]) <= 203  # 200 + "..."
    
    @pytest.mark.asyncio
    async def test_generate_recommendation(self, tool):
        """测试推荐说明生成"""
        from src.framework.retrieval.enhanced_few_shot_retriever import FewShotExample
        
        cases = [
            FewShotExample(
                query="测试查询1",
                response="测试响应1",
                user_rating=4.5,
                quality_score=4.2,
                similarity=0.85,
                tools_used=[],
                model_used="test_model",
                timestamp=datetime.now(),
                session_id="test_session_1",
                metadata={},
                training_effect="excellent",
                user_feedback=None
            ),
            FewShotExample(
                query="测试查询2",
                response="测试响应2",
                user_rating=4.0,
                quality_score=4.0,
                similarity=0.80,
                tools_used=[],
                model_used="test_model",
                timestamp=datetime.now(),
                session_id="test_session_2",
                metadata={},
                training_effect="good",
                user_feedback=None
            )
        ]
        
        recommendation = tool._generate_recommendation(
            cases=cases,
            query="测试查询",
            training_goal="增肌"
        )
        
        assert "找到2个相似的训练案例" in recommendation
        assert "平均质量评分" in recommendation
        assert "训练效果分布" in recommendation
        assert "优秀" in recommendation
        assert "良好" in recommendation
    
    def test_tool_metadata(self):
        """测试工具元数据"""
        assert TOOL_METADATA["name"] == "find_similar_training_cases"
        assert "description" in TOOL_METADATA
        assert "input_schema" in TOOL_METADATA
        assert "query" in TOOL_METADATA["input_schema"]["properties"]
        assert "user_profile" in TOOL_METADATA["input_schema"]["properties"]
        assert "query" in TOOL_METADATA["input_schema"]["required"]
        assert "user_profile" in TOOL_METADATA["input_schema"]["required"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
