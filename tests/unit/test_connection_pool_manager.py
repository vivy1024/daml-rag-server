"""
连接池管理器单元测试

测试连接池管理器的核心功能：
- 连接的获取和释放
- 连接池耗尽时的等待机制
- 健康检查和连接恢复
- 动态调整连接池大小

版本: v1.0.0
创建日期: 2025-12-21
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.framework.storage.connection_pool_manager import (
    ConnectionPoolManager,
    PoolConfig,
    MySQLConnectionPool,
    Neo4jConnectionPool,
    HTTPConnectionPool
)


class TestPoolConfig:
    """测试连接池配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = PoolConfig()
        assert config.min_size == 10
        assert config.max_size == 50
        assert config.max_idle_time == 60
        assert config.max_lifetime == 3600
        assert config.acquire_timeout == 2
        assert config.health_check_interval == 30
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = PoolConfig(
            min_size=5,
            max_size=20,
            max_idle_time=30,
            acquire_timeout=5
        )
        assert config.min_size == 5
        assert config.max_size == 20
        assert config.max_idle_time == 30
        assert config.acquire_timeout == 5


class TestMySQLConnectionPool:
    """测试MySQL连接池"""
    
    @pytest_asyncio.fixture
    async def mysql_pool(self):
        """创建MySQL连接池fixture"""
        config = PoolConfig(min_size=2, max_size=5, acquire_timeout=1)
        db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }
        pool = MySQLConnectionPool(config, db_config)
        
        # Mock aiomysql.create_pool
        with patch('src.framework.storage.connection_pool_manager.aiomysql.create_pool') as mock_create:
            mock_pool = AsyncMock()
            mock_pool.size = 2
            mock_pool.freesize = 2
            
            # 创建一个async函数来返回mock_pool
            async def create_pool_mock(*args, **kwargs):
                return mock_pool
            
            mock_create.side_effect = create_pool_mock
            
            await pool.initialize()
            yield pool
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_initialize(self, mysql_pool):
        """测试初始化"""
        assert mysql_pool.pool is not None
        assert mysql_pool._health_check_task is not None
    
    @pytest.mark.asyncio
    async def test_acquire_connection(self, mysql_pool):
        """测试获取连接"""
        # Mock connection
        mock_conn = AsyncMock()
        mysql_pool.pool.acquire = AsyncMock(return_value=mock_conn)
        mysql_pool.pool.release = Mock()
        
        async with mysql_pool.acquire() as conn:
            assert conn == mock_conn
        
        # 验证连接被释放
        mysql_pool.pool.release.assert_called_once_with(mock_conn)
    
    @pytest.mark.asyncio
    async def test_acquire_timeout(self, mysql_pool):
        """测试获取连接超时"""
        # Mock acquire to timeout
        async def slow_acquire():
            await asyncio.sleep(10)
            return AsyncMock()
        
        mysql_pool.pool.acquire = slow_acquire
        
        with pytest.raises(asyncio.TimeoutError):
            async with mysql_pool.acquire() as conn:
                pass
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mysql_pool):
        """测试健康检查成功"""
        # Mock connection and cursor
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(1,))
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock()
        
        mock_conn = AsyncMock()
        mock_conn.cursor = Mock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()
        
        mysql_pool.pool.acquire = AsyncMock(return_value=mock_conn)
        mysql_pool.pool.release = Mock()
        
        result = await mysql_pool.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mysql_pool):
        """测试健康检查失败"""
        # Mock acquire to raise exception
        mysql_pool.pool.acquire = AsyncMock(side_effect=Exception("Connection failed"))
        
        result = await mysql_pool.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_adjust_pool_size(self, mysql_pool):
        """测试动态调整连接池大小"""
        await mysql_pool.adjust_pool_size(10)
        assert mysql_pool.config.max_size == 10
    
    @pytest.mark.asyncio
    async def test_adjust_pool_size_below_min(self, mysql_pool):
        """测试调整连接池大小低于最小值"""
        original_max = mysql_pool.config.max_size
        await mysql_pool.adjust_pool_size(1)  # 低于min_size=2
        assert mysql_pool.config.max_size == original_max  # 不应该改变
    
    def test_get_stats(self, mysql_pool):
        """测试获取统计信息"""
        stats = mysql_pool.get_stats()
        assert 'size' in stats
        assert 'free' in stats
        assert 'min_size' in stats
        assert 'max_size' in stats


class TestNeo4jConnectionPool:
    """测试Neo4j连接池"""
    
    @pytest_asyncio.fixture
    async def neo4j_pool(self):
        """创建Neo4j连接池fixture"""
        config = PoolConfig(min_size=2, max_size=5, acquire_timeout=1)
        db_config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'test'
        }
        pool = Neo4jConnectionPool(config, db_config)
        
        # Mock AsyncGraphDatabase.driver
        with patch('src.framework.storage.connection_pool_manager.AsyncGraphDatabase.driver') as mock_driver:
            mock_driver_instance = AsyncMock()
            mock_driver_instance.verify_connectivity = AsyncMock()
            mock_driver.return_value = mock_driver_instance
            
            await pool.initialize()
            yield pool
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_initialize(self, neo4j_pool):
        """测试初始化"""
        assert neo4j_pool.driver is not None
        assert neo4j_pool._health_check_task is not None
    
    @pytest.mark.asyncio
    async def test_acquire_session(self, neo4j_pool):
        """测试获取会话"""
        # Mock session
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        neo4j_pool.driver.session = Mock(return_value=mock_session)
        
        async with neo4j_pool.acquire() as session:
            assert session == mock_session
        
        # 验证会话被关闭
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, neo4j_pool):
        """测试健康检查成功"""
        # Mock session and result
        mock_record = {"num": 1}
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=mock_record)
        
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        
        neo4j_pool.driver.session = Mock(return_value=mock_session)
        
        result = await neo4j_pool.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, neo4j_pool):
        """测试健康检查失败"""
        # Mock session to raise exception
        neo4j_pool.driver.session = Mock(side_effect=Exception("Connection failed"))
        
        result = await neo4j_pool.health_check()
        assert result is False
    
    def test_get_stats(self, neo4j_pool):
        """测试获取统计信息"""
        stats = neo4j_pool.get_stats()
        assert 'max_size' in stats
        assert 'total_sessions' in stats


class TestHTTPConnectionPool:
    """测试HTTP连接池"""
    
    @pytest_asyncio.fixture
    async def http_pool(self):
        """创建HTTP连接池fixture"""
        config = PoolConfig(min_size=5, max_size=20, acquire_timeout=1)
        pool = HTTPConnectionPool(config)
        
        # Mock aiohttp.ClientSession
        with patch('src.framework.storage.connection_pool_manager.aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.closed = False
            mock_session_instance.close = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            await pool.initialize()
            yield pool
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_initialize(self, http_pool):
        """测试初始化"""
        assert http_pool.session is not None
        assert http_pool._health_check_task is not None
    
    @pytest.mark.asyncio
    async def test_acquire_session(self, http_pool):
        """测试获取会话"""
        async with http_pool.acquire() as session:
            assert session == http_pool.session
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, http_pool):
        """测试健康检查成功"""
        http_pool.session.closed = False
        result = await http_pool.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, http_pool):
        """测试健康检查失败"""
        http_pool.session.closed = True
        result = await http_pool.health_check()
        assert result is False
    
    def test_get_stats(self, http_pool):
        """测试获取统计信息"""
        stats = http_pool.get_stats()
        assert 'max_size' in stats
        assert 'total_connections' in stats


class TestConnectionPoolManager:
    """测试连接池管理器"""
    
    @pytest_asyncio.fixture
    async def pool_manager(self):
        """创建连接池管理器fixture"""
        mysql_config = PoolConfig(min_size=2, max_size=5)
        neo4j_config = PoolConfig(min_size=2, max_size=5)
        http_config = PoolConfig(min_size=5, max_size=20)
        
        mysql_db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }
        
        neo4j_db_config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'test'
        }
        
        manager = ConnectionPoolManager(
            mysql_config=mysql_config,
            neo4j_config=neo4j_config,
            http_config=http_config,
            mysql_db_config=mysql_db_config,
            neo4j_db_config=neo4j_db_config
        )
        
        # Mock all pool initializations
        with patch('src.framework.storage.connection_pool_manager.aiomysql.create_pool') as mock_mysql, \
             patch('src.framework.storage.connection_pool_manager.AsyncGraphDatabase.driver') as mock_neo4j, \
             patch('src.framework.storage.connection_pool_manager.aiohttp.ClientSession') as mock_http:
            
            # Mock MySQL pool
            mock_mysql_pool = AsyncMock()
            mock_mysql_pool.size = 2
            mock_mysql_pool.freesize = 2
            
            async def create_mysql_pool(*args, **kwargs):
                return mock_mysql_pool
            
            mock_mysql.side_effect = create_mysql_pool
            
            # Mock Neo4j driver
            mock_neo4j_driver = AsyncMock()
            mock_neo4j_driver.verify_connectivity = AsyncMock()
            mock_neo4j.return_value = mock_neo4j_driver
            
            # Mock HTTP session
            mock_http_session = AsyncMock()
            mock_http_session.closed = False
            mock_http.return_value = mock_http_session
            
            await manager.initialize()
            yield manager
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_initialize(self, pool_manager):
        """测试初始化所有连接池"""
        assert pool_manager._initialized is True
        assert pool_manager.mysql_pool is not None
        assert pool_manager.neo4j_pool is not None
        assert pool_manager.http_pool is not None
    
    @pytest.mark.asyncio
    async def test_get_mysql_connection(self, pool_manager):
        """测试获取MySQL连接"""
        # Mock connection
        mock_conn = AsyncMock()
        pool_manager.mysql_pool.pool.acquire = AsyncMock(return_value=mock_conn)
        pool_manager.mysql_pool.pool.release = Mock()
        
        async with pool_manager.get_mysql_connection() as conn:
            assert conn == mock_conn
    
    @pytest.mark.asyncio
    async def test_get_neo4j_session(self, pool_manager):
        """测试获取Neo4j会话"""
        # Mock session
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        pool_manager.neo4j_pool.driver.session = Mock(return_value=mock_session)
        
        async with pool_manager.get_neo4j_session() as session:
            assert session == mock_session
    
    @pytest.mark.asyncio
    async def test_get_http_session(self, pool_manager):
        """测试获取HTTP会话"""
        async with pool_manager.get_http_session() as session:
            assert session == pool_manager.http_pool.session
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, pool_manager):
        """测试所有连接池的健康检查"""
        # Mock health checks
        pool_manager.mysql_pool.health_check = AsyncMock(return_value=True)
        pool_manager.neo4j_pool.health_check = AsyncMock(return_value=True)
        pool_manager.http_pool.health_check = AsyncMock(return_value=True)
        
        results = await pool_manager.health_check()
        
        assert results['mysql'] is True
        assert results['neo4j'] is True
        assert results['http'] is True
    
    @pytest.mark.asyncio
    async def test_health_check_partial_failure(self, pool_manager):
        """测试部分连接池健康检查失败"""
        # Mock health checks
        pool_manager.mysql_pool.health_check = AsyncMock(return_value=True)
        pool_manager.neo4j_pool.health_check = AsyncMock(return_value=False)
        pool_manager.http_pool.health_check = AsyncMock(return_value=True)
        
        results = await pool_manager.health_check()
        
        assert results['mysql'] is True
        assert results['neo4j'] is False
        assert results['http'] is True
    
    @pytest.mark.asyncio
    async def test_adjust_pool_size_mysql(self, pool_manager):
        """测试调整MySQL连接池大小"""
        await pool_manager.adjust_pool_size('mysql', 10)
        assert pool_manager.mysql_pool.config.max_size == 10
    
    @pytest.mark.asyncio
    async def test_adjust_pool_size_neo4j(self, pool_manager):
        """测试调整Neo4j连接池大小"""
        await pool_manager.adjust_pool_size('neo4j', 15)
        assert pool_manager.neo4j_pool.config.max_size == 15
    
    @pytest.mark.asyncio
    async def test_adjust_pool_size_http(self, pool_manager):
        """测试调整HTTP连接池大小"""
        await pool_manager.adjust_pool_size('http', 30)
        assert pool_manager.http_pool.config.max_size == 30
    
    @pytest.mark.asyncio
    async def test_adjust_pool_size_invalid_name(self, pool_manager):
        """测试调整无效连接池名称"""
        # 不应该抛出异常，只是记录警告
        await pool_manager.adjust_pool_size('invalid', 10)
    
    def test_get_all_stats(self, pool_manager):
        """测试获取所有连接池统计信息"""
        stats = pool_manager.get_all_stats()
        
        assert 'mysql' in stats
        assert 'neo4j' in stats
        assert 'http' in stats
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, pool_manager):
        """测试连接池耗尽时的等待机制"""
        # 设置小的连接池
        pool_manager.mysql_pool.config.max_size = 1
        pool_manager.mysql_pool.config.acquire_timeout = 0.5
        
        # Mock connection
        mock_conn = AsyncMock()
        
        # 第一次获取成功
        pool_manager.mysql_pool.pool.acquire = AsyncMock(return_value=mock_conn)
        pool_manager.mysql_pool.pool.release = Mock()
        
        async with pool_manager.get_mysql_connection() as conn1:
            assert conn1 == mock_conn
            
            # 第二次获取应该超时（因为连接池已满）
            async def slow_acquire():
                await asyncio.sleep(10)
                return AsyncMock()
            
            pool_manager.mysql_pool.pool.acquire = slow_acquire
            
            with pytest.raises(asyncio.TimeoutError):
                async with pool_manager.get_mysql_connection() as conn2:
                    pass
    
    @pytest.mark.asyncio
    async def test_connection_recovery_after_failure(self, pool_manager):
        """测试连接失败后的恢复"""
        # 第一次健康检查失败
        pool_manager.mysql_pool.health_check = AsyncMock(return_value=False)
        result1 = await pool_manager.health_check()
        assert result1['mysql'] is False
        
        # 第二次健康检查成功（模拟恢复）
        pool_manager.mysql_pool.health_check = AsyncMock(return_value=True)
        result2 = await pool_manager.health_check()
        assert result2['mysql'] is True
    
    @pytest.mark.asyncio
    async def test_dynamic_pool_size_adjustment_under_load(self, pool_manager):
        """测试负载下的动态连接池大小调整"""
        # 初始大小
        initial_size = pool_manager.mysql_pool.config.max_size
        
        # 模拟高负载，调整连接池大小
        new_size = initial_size * 2
        await pool_manager.adjust_pool_size('mysql', new_size)
        
        assert pool_manager.mysql_pool.config.max_size == new_size
        
        # 模拟负载降低，减小连接池大小
        reduced_size = initial_size
        await pool_manager.adjust_pool_size('mysql', reduced_size)
        
        assert pool_manager.mysql_pool.config.max_size == reduced_size


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
