# -*- coding: utf-8 -*-
"""
Credit Reporter Unit Tests

测试积分消耗上报服务的核心功能。

核心功能测试：
- 积分计算（calculate_credits）
- DAG模式和Agent模式的不同倍率
- 最小消耗1积分
- 向上取整规则
- 异步上报功能
- 错误处理

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5 - DAML-RAG积分上报集成

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2026-02-05
"""

import pytest
import math
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.applications.fitness.services.credit_reporter import (
    CreditReporter,
    get_credit_reporter,
    reset_credit_reporter,
    report_credit_consumption
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def reporter():
    """创建CreditReporter实例"""
    reset_credit_reporter()
    return CreditReporter(
        backend_url="http://test-backend:8000",
        internal_token="test-token-12345",
        enabled=True
    )


@pytest.fixture
def disabled_reporter():
    """创建禁用的CreditReporter实例"""
    return CreditReporter(
        backend_url="http://test-backend:8000",
        internal_token="test-token-12345",
        enabled=False
    )


@pytest.fixture(autouse=True)
def reset_singleton():
    """每个测试后重置单例"""
    yield
    reset_credit_reporter()


# ============================================================================
# Unit Tests - Credit Calculation (Requirements 1.1, 1.2, 1.3, 1.4, 1.5)
# ============================================================================

class TestCreditCalculation:
    """积分计算测试 - Requirements 1.1, 1.2, 1.3, 1.4, 1.5"""
    
    def test_dag_mode_multiplier_1x(self, reporter):
        """DAG模式使用1.0x倍率 - Requirement 1.3"""
        # 1000 tokens * 1.0 / 1000 = 1 credit
        assert reporter.calculate_credits(1000, 'dag') == 1
        # 2000 tokens * 1.0 / 1000 = 2 credits
        assert reporter.calculate_credits(2000, 'dag') == 2
        # 5000 tokens * 1.0 / 1000 = 5 credits
        assert reporter.calculate_credits(5000, 'dag') == 5
    
    def test_agent_mode_multiplier_1_5x(self, reporter):
        """Agent模式使用1.5x倍率 - Requirement 1.2"""
        # 1000 tokens * 1.5 / 1000 = 1.5 -> ceil = 2 credits
        assert reporter.calculate_credits(1000, 'agent') == 2
        # 2000 tokens * 1.5 / 1000 = 3 credits
        assert reporter.calculate_credits(2000, 'agent') == 3
        # 667 tokens * 1.5 / 1000 = 1.0005 -> ceil = 2 credits
        assert reporter.calculate_credits(667, 'agent') == 2
    
    def test_ceiling_rounding(self, reporter):
        """向上取整规则 - Requirement 1.4"""
        # 1001 tokens * 1.0 / 1000 = 1.001 -> ceil = 2 credits
        assert reporter.calculate_credits(1001, 'dag') == 2
        # 1500 tokens * 1.0 / 1000 = 1.5 -> ceil = 2 credits
        assert reporter.calculate_credits(1500, 'dag') == 2
        # 1999 tokens * 1.0 / 1000 = 1.999 -> ceil = 2 credits
        assert reporter.calculate_credits(1999, 'dag') == 2
    
    def test_minimum_consumption_1_credit(self, reporter):
        """最小消耗1积分 - Requirement 1.5"""
        # 0 tokens should still consume 1 credit
        assert reporter.calculate_credits(0, 'dag') == 1
        # 1 token should consume 1 credit
        assert reporter.calculate_credits(1, 'dag') == 1
        # 100 tokens should consume 1 credit
        assert reporter.calculate_credits(100, 'dag') == 1
        # 999 tokens should consume 1 credit
        assert reporter.calculate_credits(999, 'dag') == 1
    
    def test_formula_credits_equals_ceil_tokens_times_multiplier_div_1000(self, reporter):
        """验证公式: credits = ceil(tokens × multiplier / 1000) - Requirement 1.1"""
        test_cases = [
            # (tokens, mode, expected_credits)
            (0, 'dag', 1),       # min 1
            (500, 'dag', 1),     # ceil(0.5) = 1
            (1000, 'dag', 1),    # ceil(1.0) = 1
            (1001, 'dag', 2),    # ceil(1.001) = 2
            (2500, 'dag', 3),    # ceil(2.5) = 3
            (0, 'agent', 1),     # min 1
            (500, 'agent', 1),   # ceil(0.75) = 1
            (667, 'agent', 2),   # ceil(1.0005) = 2
            (1000, 'agent', 2),  # ceil(1.5) = 2
            (2000, 'agent', 3),  # ceil(3.0) = 3
            (3333, 'agent', 5),  # ceil(4.9995) = 5
            (3334, 'agent', 6),  # ceil(5.001) = 6
        ]
        
        for tokens, mode, expected in test_cases:
            result = reporter.calculate_credits(tokens, mode)
            assert result == expected, f"tokens={tokens}, mode={mode}: expected {expected}, got {result}"
    
    def test_large_token_values(self, reporter):
        """大量Token值测试"""
        # 100000 tokens in dag mode = 100 credits
        assert reporter.calculate_credits(100000, 'dag') == 100
        # 100000 tokens in agent mode = ceil(150) = 150 credits
        assert reporter.calculate_credits(100000, 'agent') == 150
        # 1000000 tokens in dag mode = 1000 credits
        assert reporter.calculate_credits(1000000, 'dag') == 1000


class TestCreditCalculationEdgeCases:
    """积分计算边界情况测试"""
    
    def test_boundary_at_1000_tokens(self, reporter):
        """1000 tokens边界测试"""
        # 999 tokens = 1 credit (dag)
        assert reporter.calculate_credits(999, 'dag') == 1
        # 1000 tokens = 1 credit (dag)
        assert reporter.calculate_credits(1000, 'dag') == 1
        # 1001 tokens = 2 credits (dag)
        assert reporter.calculate_credits(1001, 'dag') == 2
    
    def test_boundary_at_667_tokens_agent(self, reporter):
        """Agent模式667 tokens边界测试"""
        # 666 tokens * 1.5 = 999 -> ceil(0.999) = 1 credit
        assert reporter.calculate_credits(666, 'agent') == 1
        # 667 tokens * 1.5 = 1000.5 -> ceil(1.0005) = 2 credits
        assert reporter.calculate_credits(667, 'agent') == 2
    
    def test_unknown_mode_defaults_to_dag(self, reporter):
        """未知模式默认使用DAG倍率"""
        # 未知模式应该使用1.0x倍率
        assert reporter.calculate_credits(1000, 'unknown') == 1
        assert reporter.calculate_credits(1000, '') == 1
        assert reporter.calculate_credits(1000, 'other') == 1


# ============================================================================
# Unit Tests - Async Report Consumption (Requirements 10.1, 10.5)
# ============================================================================

class TestReportConsumption:
    """积分上报测试 - Requirements 10.1, 10.5"""
    
    @pytest.mark.asyncio
    async def test_report_consumption_success(self, reporter):
        """成功上报积分消耗"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 200,
            "msg": "success",
            "data": {"credits_deducted": 3}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await reporter.report_consumption(
                user_id=123,
                tokens=2500,
                mode='dag',
                template_name='exercise_optimization',
                conversation_id='conv_abc123',
                input_tokens=800,
                output_tokens=1700
            )
            
            assert result['success'] is True
            assert result['credits'] == 3  # ceil(2500/1000) = 3
            
            # 验证请求参数
            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert 'json' in call_args.kwargs
            payload = call_args.kwargs['json']
            assert payload['user_id'] == 123
            assert payload['tokens'] == 2500
            assert payload['mode'] == 'dag'
            assert payload['template_name'] == 'exercise_optimization'
    
    @pytest.mark.asyncio
    async def test_report_consumption_disabled(self, disabled_reporter):
        """禁用时跳过上报"""
        result = await disabled_reporter.report_consumption(
            user_id=123,
            tokens=2500,
            mode='dag'
        )
        
        assert result['success'] is True
        assert result['credits'] == 0
        assert result.get('skipped') is True
    
    @pytest.mark.asyncio
    async def test_report_consumption_http_error(self, reporter):
        """HTTP错误处理 - Requirement 10.5"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await reporter.report_consumption(
                user_id=123,
                tokens=2500,
                mode='dag'
            )
            
            assert result['success'] is False
            assert 'error' in result
            assert '500' in result['error']
    
    @pytest.mark.asyncio
    async def test_report_consumption_timeout(self, reporter):
        """超时错误处理 - Requirement 10.5"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.TimeoutException("Connection timeout")
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await reporter.report_consumption(
                user_id=123,
                tokens=2500,
                mode='dag'
            )
            
            assert result['success'] is False
            assert 'error' in result
            assert '超时' in result['error']
    
    @pytest.mark.asyncio
    async def test_report_consumption_request_error(self, reporter):
        """请求错误处理 - Requirement 10.5"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.RequestError("Connection refused")
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await reporter.report_consumption(
                user_id=123,
                tokens=2500,
                mode='dag'
            )
            
            assert result['success'] is False
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_report_consumption_includes_all_fields(self, reporter):
        """上报包含所有必要字段 - Requirements 10.2, 10.3, 10.4"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "data": {}}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            await reporter.report_consumption(
                user_id=123,
                tokens=2500,
                mode='agent',
                template_name='fitness_coach',
                conversation_id='conv_xyz789',
                input_tokens=1000,
                output_tokens=1500
            )
            
            call_args = mock_instance.post.call_args
            payload = call_args.kwargs['json']
            
            # 验证所有必要字段
            assert 'user_id' in payload
            assert 'tokens' in payload
            assert 'credits' in payload
            assert 'mode' in payload
            assert 'template_name' in payload
            assert 'conversation_id' in payload
            assert 'input_tokens' in payload
            assert 'output_tokens' in payload


# ============================================================================
# Unit Tests - Statistics
# ============================================================================

class TestStatistics:
    """统计信息测试"""
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, reporter):
        """统计信息跟踪"""
        # 初始状态
        stats = reporter.get_statistics()
        assert stats['report_count'] == 0
        assert stats['error_count'] == 0
        
        # 模拟成功上报
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "data": {}}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            await reporter.report_consumption(user_id=1, tokens=1000, mode='dag')
            await reporter.report_consumption(user_id=2, tokens=2000, mode='agent')
        
        stats = reporter.get_statistics()
        assert stats['report_count'] == 2
        assert stats['error_count'] == 0
    
    @pytest.mark.asyncio
    async def test_error_count_tracking(self, reporter):
        """错误计数跟踪"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            await reporter.report_consumption(user_id=1, tokens=1000, mode='dag')
            await reporter.report_consumption(user_id=2, tokens=2000, mode='dag')
        
        stats = reporter.get_statistics()
        assert stats['report_count'] == 2
        assert stats['error_count'] == 2
        assert stats['error_rate'] == 1.0


# ============================================================================
# Unit Tests - Singleton Pattern
# ============================================================================

class TestSingletonPattern:
    """单例模式测试"""
    
    def test_get_same_instance(self):
        """获取相同实例"""
        reset_credit_reporter()
        instance1 = get_credit_reporter()
        instance2 = get_credit_reporter()
        assert instance1 is instance2
    
    def test_reset_creates_new_instance(self):
        """重置后创建新实例"""
        instance1 = get_credit_reporter()
        reset_credit_reporter()
        instance2 = get_credit_reporter()
        assert instance1 is not instance2


# ============================================================================
# Unit Tests - Convenience Function
# ============================================================================

class TestConvenienceFunction:
    """便捷函数测试"""
    
    @pytest.mark.asyncio
    async def test_report_credit_consumption_function(self):
        """测试便捷函数"""
        reset_credit_reporter()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "data": {}}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await report_credit_consumption(
                user_id=123,
                tokens=3000,
                mode='dag',
                template_name='test_template'
            )
            
            assert result['success'] is True
            assert result['credits'] == 3


# ============================================================================
# Unit Tests - Configuration
# ============================================================================

class TestConfiguration:
    """配置测试"""
    
    def test_default_configuration(self):
        """默认配置"""
        reporter = CreditReporter()
        assert reporter.TOKENS_PER_CREDIT == 1000
        assert reporter.AGENT_MULTIPLIER == 1.5
        assert reporter.DAG_MULTIPLIER == 1.0
        assert reporter.DEFAULT_TIMEOUT == 5.0
    
    def test_custom_configuration(self):
        """自定义配置"""
        reporter = CreditReporter(
            backend_url="http://custom:9000",
            internal_token="custom-token",
            timeout=10.0,
            enabled=False
        )
        assert reporter.backend_url == "http://custom:9000"
        assert reporter.internal_token == "custom-token"
        assert reporter.timeout == 10.0
        assert reporter.enabled is False


# ============================================================================
# Unit Tests - Performance Fields (unified-observability-dashboard)
# ============================================================================

class TestPerformanceFields:
    """性能字段上报测试 - unified-observability-dashboard"""

    @pytest.mark.asyncio
    async def test_report_includes_performance_fields(self, reporter):
        """上报包含性能监控字段（ttfb_ms, duration_ms, tokens_per_sec, fallback_count, error_type）"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "data": {}}

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            await reporter.report_consumption(
                user_id=123,
                tokens=2500,
                mode='dag',
                template_name='exercise_optimization',
                conversation_id='conv_perf_001',
                input_tokens=800,
                output_tokens=1700,
                ttfb_ms=350,
                duration_ms=2800,
                tokens_per_sec=42.5,
                fallback_count=1,
                error_type=None
            )

            call_args = mock_instance.post.call_args
            payload = call_args.kwargs['json']

            assert payload['ttfb_ms'] == 350
            assert payload['duration_ms'] == 2800
            assert payload['tokens_per_sec'] == 42.5
            assert payload['fallback_count'] == 1
            assert payload.get('error_type') is None

    @pytest.mark.asyncio
    async def test_report_with_error_type(self, reporter):
        """上报包含错误类型"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "data": {}}

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            await reporter.report_consumption(
                user_id=456,
                tokens=1000,
                mode='agent',
                ttfb_ms=0,
                duration_ms=5000,
                tokens_per_sec=0,
                fallback_count=2,
                error_type='rate_limit'
            )

            call_args = mock_instance.post.call_args
            payload = call_args.kwargs['json']

            assert payload['error_type'] == 'rate_limit'
            assert payload['fallback_count'] == 2

    @pytest.mark.asyncio
    async def test_report_performance_fields_default_none(self, reporter):
        """性能字段默认为None时不影响上报"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "data": {}}

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await reporter.report_consumption(
                user_id=789,
                tokens=1500,
                mode='dag'
            )

            assert result['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
