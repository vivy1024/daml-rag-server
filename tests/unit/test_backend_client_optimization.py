# -*- coding: utf-8 -*-
"""
BackendClient优化功能测试

测试连接池预热、缓存集成和超时配置

版本: v1.0.0
日期: 2025-12-22
作者: 薛小川
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.applications.fitness.clients.backend_client import (
    BackendClient,
    BackendConfig,
    MembershipFeature
)


class TestBackendClientOptimization:
    """测试BackendClient优化功能"""
    
    @pytest.mark.asyncio
    async def test_connection_pool_config(self):
        """测试连接池配置"""
        config = BackendConfig()
        
        # 验证连接池配置存在
        assert hasattr(config, 'pool_max_connections')
        assert hasattr(config, 'pool_max_keepalive')
        assert hasattr(config, 'pool_keepalive_expiry')
        
        # 验证默认值
        assert config.pool_max_connections == 100
        assert config.pool_max_keepalive == 20
        assert config.pool_keepalive_expiry == 5.0
    
    @pytest.mark.asyncio
    async def test_membership_timeout_config(self):
        """测试会员权限超时配置"""
        config = BackendConfig()
        
        # 验证超时配置存在
        assert hasattr(config, 'membership_timeout_ms')
        assert hasattr(config, 'user_profile_timeout_ms')
        
        # 验证默认值（2000ms = 2秒）
        assert config.membership_timeout_ms == 2000
        assert config.user_profile_timeout_ms == 5000
    
    @pytest.mark.asyncio
    async def test_pool_stats_initialization(self):
        """测试连接池状态初始化"""
        client = BackendClient()
        
        # 验证连接池状态存在
        assert hasattr(client, '_pool_stats')
        assert 'total_requests' in client._pool_stats
        assert 'warmup_time_ms' in client._pool_stats
        
        # 验证初始值
        assert client._pool_stats['total_requests'] == 0
        assert client._pool_stats['warmup_time_ms'] == 0.0
    
    @pytest.mark.asyncio
    async def test_get_pool_stats(self):
        """测试获取连接池状态"""
        client = BackendClient()
        
        stats = client.get_pool_stats()
        
        # 验证返回的统计信息
        assert 'total_requests' in stats
        assert 'warmup_time_ms' in stats
        assert 'is_warmed_up' in stats
        assert 'config' in stats
        
        # 验证配置信息
        assert 'max_connections' in stats['config']
        assert 'max_keepalive' in stats['config']
        assert 'keepalive_expiry' in stats['config']
    
    @pytest.mark.asyncio
    async def test_cache_manager_integration(self):
        """测试缓存管理器集成"""
        mock_cache = Mock()
        mock_cache.get_user_profile = AsyncMock(return_value=None)
        mock_cache.set_user_profile = AsyncMock()
        
        client = BackendClient(cache_manager=mock_cache)
        
        # 验证缓存管理器已设置
        assert client.cache_manager is not None
        assert client.cache_manager == mock_cache
    
    @pytest.mark.asyncio
    async def test_fallback_membership(self):
        """测试降级会员权限"""
        client = BackendClient()
        
        fallback = client._get_fallback_membership(123)
        
        # 验证降级数据结构
        assert fallback['user_id'] == 123
        assert fallback['tier'] == 'free'
        assert fallback['status'] == 'active'
        assert fallback['_fallback'] is True
        
        # 验证权限都是False
        assert fallback['permissions']['ai_recommendation'] is False
        assert fallback['permissions']['data_analysis'] is False
        assert fallback['permissions']['coach_service'] is False
    
    @pytest.mark.asyncio
    async def test_log_cache_statistics_without_cache(self):
        """测试无缓存时的统计日志"""
        client = BackendClient()
        
        # 没有缓存管理器时应返回None
        stats = client.log_cache_statistics()
        assert stats is None
    
    @pytest.mark.asyncio
    async def test_log_cache_statistics_with_cache(self):
        """测试有缓存时的统计日志"""
        mock_cache = Mock()
        mock_cache.get_statistics = Mock(return_value={
            'total_requests': 100,
            'total_hits': 80,
            'hit_rate': 80.0,
            'user_profile_hit_rate': 85.0,
            'membership_hit_rate': 75.0,
            'avg_response_time_ms': 15.5
        })
        
        client = BackendClient(cache_manager=mock_cache)
        
        stats = client.log_cache_statistics()
        
        # 验证统计信息
        assert stats is not None
        assert stats['total_requests'] == 100
        assert stats['hit_rate'] == 80.0
        assert stats['user_profile_hit_rate'] == 85.0
        assert stats['membership_hit_rate'] == 75.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
