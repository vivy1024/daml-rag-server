"""
连接池管理器

统一管理MySQL、Neo4j和HTTP连接池，提供连接获取、健康检查和动态调整功能。

版本: v1.0.0
创建日期: 2025-12-21
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
import aiomysql
from neo4j import AsyncGraphDatabase, AsyncSession
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """连接池配置"""
    min_size: int = 10
    max_size: int = 50
    max_idle_time: int = 60  # 最大空闲时间(秒)
    max_lifetime: int = 3600  # 连接最大生命周期(秒)
    acquire_timeout: int = 2  # 获取连接超时(秒)
    health_check_interval: int = 30  # 健康检查间隔(秒)


@dataclass
class ConnectionMetadata:
    """连接元数据"""
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0
    is_healthy: bool = True


class MySQLConnectionPool:
    """MySQL连接池"""
    
    def __init__(self, config: PoolConfig, db_config: Dict[str, Any]):
        self.config = config
        self.db_config = db_config
        self.pool: Optional[aiomysql.Pool] = None
        self._metadata: Dict[int, ConnectionMetadata] = {}
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """初始化连接池"""
        try:
            self.pool = await aiomysql.create_pool(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 3306),
                user=self.db_config.get('user', 'root'),
                password=self.db_config.get('password', ''),
                db=self.db_config.get('database', 'test'),
                minsize=self.config.min_size,
                maxsize=self.config.max_size,
                pool_recycle=self.config.max_lifetime,
                connect_timeout=self.db_config.get('connect_timeout', 5),
                read_timeout=self.db_config.get('read_timeout', 30),
                write_timeout=self.db_config.get('write_timeout', 30),
                autocommit=True
            )
            logger.info(f"MySQL连接池初始化成功: min={self.config.min_size}, max={self.config.max_size}")
            
            # 启动健康检查任务
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
        except Exception as e:
            logger.error(f"MySQL连接池初始化失败: {e}")
            raise
    
    @asynccontextmanager
    async def acquire(self):
        """获取连接（上下文管理器）"""
        if not self.pool:
            raise RuntimeError("连接池未初始化")
        
        conn = None
        try:
            # 使用超时获取连接
            conn = await asyncio.wait_for(
                self.pool.acquire(),
                timeout=self.config.acquire_timeout
            )
            
            # 更新元数据
            conn_id = id(conn)
            async with self._lock:
                if conn_id not in self._metadata:
                    self._metadata[conn_id] = ConnectionMetadata()
                metadata = self._metadata[conn_id]
                metadata.last_used_at = time.time()
                metadata.use_count += 1
            
            yield conn
            
        except asyncio.TimeoutError:
            logger.error(f"获取MySQL连接超时: {self.config.acquire_timeout}秒")
            raise
        except Exception as e:
            logger.error(f"获取MySQL连接失败: {e}")
            raise
        finally:
            if conn:
                self.pool.release(conn)
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with self.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    return result == (1,)
        except Exception as e:
            logger.error(f"MySQL健康检查失败: {e}")
            return False
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                is_healthy = await self.health_check()
                if not is_healthy:
                    logger.warning("MySQL连接池健康检查失败")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查循环异常: {e}")
    
    async def adjust_pool_size(self, new_max_size: int):
        """动态调整连接池大小"""
        if new_max_size < self.config.min_size:
            logger.warning(f"新的最大连接数({new_max_size})小于最小连接数({self.config.min_size})")
            return
        
        self.config.max_size = new_max_size
        logger.info(f"MySQL连接池大小已调整: max={new_max_size}")
        
        # 注意: aiomysql不支持动态调整，需要重新创建连接池
        # 这里只更新配置，实际调整需要重启
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        if not self.pool:
            return {}
        
        return {
            'size': self.pool.size,
            'free': self.pool.freesize,
            'min_size': self.config.min_size,
            'max_size': self.config.max_size,
            'total_connections': len(self._metadata)
        }
    
    async def close(self):
        """关闭连接池"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("MySQL连接池已关闭")


class Neo4jConnectionPool:
    """Neo4j连接池"""
    
    def __init__(self, config: PoolConfig, db_config: Dict[str, Any]):
        self.config = config
        self.db_config = db_config
        self.driver = None
        self._metadata: Dict[int, ConnectionMetadata] = {}
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """初始化连接池"""
        try:
            uri = self.db_config.get('uri', 'bolt://localhost:7687')
            user = self.db_config.get('user', 'neo4j')
            password = self.db_config.get('password', 'password')
            
            self.driver = AsyncGraphDatabase.driver(
                uri,
                auth=(user, password),
                max_connection_pool_size=self.config.max_size,
                connection_acquisition_timeout=self.config.acquire_timeout,
                max_connection_lifetime=self.config.max_lifetime
            )
            
            # 验证连接
            await self.driver.verify_connectivity()
            
            logger.info(f"Neo4j连接池初始化成功: max={self.config.max_size}")
            
            # 启动健康检查任务
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
        except Exception as e:
            logger.error(f"Neo4j连接池初始化失败: {e}")
            raise
    
    @asynccontextmanager
    async def acquire(self) -> AsyncSession:
        """获取会话（上下文管理器）"""
        if not self.driver:
            raise RuntimeError("连接池未初始化")
        
        session = None
        try:
            session = self.driver.session()
            
            # 更新元数据
            session_id = id(session)
            async with self._lock:
                if session_id not in self._metadata:
                    self._metadata[session_id] = ConnectionMetadata()
                metadata = self._metadata[session_id]
                metadata.last_used_at = time.time()
                metadata.use_count += 1
            
            yield session
            
        except Exception as e:
            logger.error(f"获取Neo4j会话失败: {e}")
            raise
        finally:
            if session:
                await session.close()
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with self.acquire() as session:
                result = await session.run("RETURN 1 AS num")
                record = await result.single()
                return record["num"] == 1
        except Exception as e:
            logger.error(f"Neo4j健康检查失败: {e}")
            return False
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                is_healthy = await self.health_check()
                if not is_healthy:
                    logger.warning("Neo4j连接池健康检查失败")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查循环异常: {e}")
    
    async def adjust_pool_size(self, new_max_size: int):
        """动态调整连接池大小"""
        if new_max_size < self.config.min_size:
            logger.warning(f"新的最大连接数({new_max_size})小于最小连接数({self.config.min_size})")
            return
        
        self.config.max_size = new_max_size
        logger.info(f"Neo4j连接池大小已调整: max={new_max_size}")
        
        # 注意: Neo4j driver不支持动态调整，需要重新创建driver
        # 这里只更新配置，实际调整需要重启
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        return {
            'max_size': self.config.max_size,
            'total_sessions': len(self._metadata)
        }
    
    async def close(self):
        """关闭连接池"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j连接池已关闭")


class HTTPConnectionPool:
    """HTTP连接池"""
    
    def __init__(self, config: PoolConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._metadata: Dict[int, ConnectionMetadata] = {}
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """初始化连接池"""
        try:
            connector = aiohttp.TCPConnector(
                limit=self.config.max_size,
                limit_per_host=self.config.max_size // 2,
                ttl_dns_cache=300,
                keepalive_timeout=self.config.max_idle_time
            )
            
            timeout = aiohttp.ClientTimeout(
                total=30,
                connect=self.config.acquire_timeout
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
            
            logger.info(f"HTTP连接池初始化成功: max={self.config.max_size}")
            
            # 启动健康检查任务
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
        except Exception as e:
            logger.error(f"HTTP连接池初始化失败: {e}")
            raise
    
    @asynccontextmanager
    async def acquire(self):
        """获取会话（上下文管理器）"""
        if not self.session:
            raise RuntimeError("连接池未初始化")
        
        # 更新元数据
        session_id = id(self.session)
        async with self._lock:
            if session_id not in self._metadata:
                self._metadata[session_id] = ConnectionMetadata()
            metadata = self._metadata[session_id]
            metadata.last_used_at = time.time()
            metadata.use_count += 1
        
        yield self.session
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.session or self.session.closed:
                return False
            return True
        except Exception as e:
            logger.error(f"HTTP连接池健康检查失败: {e}")
            return False
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                is_healthy = await self.health_check()
                if not is_healthy:
                    logger.warning("HTTP连接池健康检查失败")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查循环异常: {e}")
    
    async def adjust_pool_size(self, new_max_size: int):
        """动态调整连接池大小"""
        if new_max_size < self.config.min_size:
            logger.warning(f"新的最大连接数({new_max_size})小于最小连接数({self.config.min_size})")
            return
        
        self.config.max_size = new_max_size
        logger.info(f"HTTP连接池大小已调整: max={new_max_size}")
        
        # 注意: aiohttp不支持动态调整，需要重新创建session
        # 这里只更新配置，实际调整需要重启
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        if not self.session or not self.session.connector:
            return {}
        
        connector = self.session.connector
        return {
            'max_size': self.config.max_size,
            'total_connections': len(self._metadata),
            'connector_limit': connector.limit
        }
    
    async def close(self):
        """关闭连接池"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
            logger.info("HTTP连接池已关闭")


class ConnectionPoolManager:
    """
    连接池管理器
    
    统一管理MySQL、Neo4j和HTTP连接池，提供连接获取、健康检查和动态调整功能。
    """
    
    def __init__(
        self,
        mysql_config: Optional[PoolConfig] = None,
        neo4j_config: Optional[PoolConfig] = None,
        http_config: Optional[PoolConfig] = None,
        mysql_db_config: Optional[Dict[str, Any]] = None,
        neo4j_db_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化连接池管理器
        
        Args:
            mysql_config: MySQL连接池配置
            neo4j_config: Neo4j连接池配置
            http_config: HTTP连接池配置
            mysql_db_config: MySQL数据库配置
            neo4j_db_config: Neo4j数据库配置
        """
        self.mysql_pool: Optional[MySQLConnectionPool] = None
        self.neo4j_pool: Optional[Neo4jConnectionPool] = None
        self.http_pool: Optional[HTTPConnectionPool] = None
        
        # 创建连接池实例
        if mysql_config and mysql_db_config:
            self.mysql_pool = MySQLConnectionPool(mysql_config, mysql_db_config)
        
        if neo4j_config and neo4j_db_config:
            self.neo4j_pool = Neo4jConnectionPool(neo4j_config, neo4j_db_config)
        
        if http_config:
            self.http_pool = HTTPConnectionPool(http_config)
        
        self._initialized = False
        logger.info("连接池管理器已创建")
    
    async def initialize(self):
        """初始化所有连接池"""
        if self._initialized:
            logger.warning("连接池管理器已初始化")
            return
        
        try:
            # 并行初始化所有连接池
            tasks = []
            
            if self.mysql_pool:
                tasks.append(self.mysql_pool.initialize())
            
            if self.neo4j_pool:
                tasks.append(self.neo4j_pool.initialize())
            
            if self.http_pool:
                tasks.append(self.http_pool.initialize())
            
            if tasks:
                await asyncio.gather(*tasks)
            
            self._initialized = True
            logger.info("连接池管理器初始化成功")
            
        except Exception as e:
            logger.error(f"连接池管理器初始化失败: {e}")
            raise
    
    @asynccontextmanager
    async def get_mysql_connection(self):
        """获取MySQL连接"""
        if not self.mysql_pool:
            raise RuntimeError("MySQL连接池未配置")
        
        async with self.mysql_pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def get_neo4j_session(self):
        """获取Neo4j会话"""
        if not self.neo4j_pool:
            raise RuntimeError("Neo4j连接池未配置")
        
        async with self.neo4j_pool.acquire() as session:
            yield session
    
    @asynccontextmanager
    async def get_http_session(self):
        """获取HTTP会话"""
        if not self.http_pool:
            raise RuntimeError("HTTP连接池未配置")
        
        async with self.http_pool.acquire() as session:
            yield session
    
    async def health_check(self) -> Dict[str, bool]:
        """
        健康检查所有连接池
        
        Returns:
            各连接池的健康状态
        """
        results = {}
        
        if self.mysql_pool:
            results['mysql'] = await self.mysql_pool.health_check()
        
        if self.neo4j_pool:
            results['neo4j'] = await self.neo4j_pool.health_check()
        
        if self.http_pool:
            results['http'] = await self.http_pool.health_check()
        
        return results
    
    async def adjust_pool_size(self, pool_name: str, new_size: int):
        """
        动态调整连接池大小
        
        Args:
            pool_name: 连接池名称 ('mysql', 'neo4j', 'http')
            new_size: 新的最大连接数
        """
        if pool_name == 'mysql' and self.mysql_pool:
            await self.mysql_pool.adjust_pool_size(new_size)
        elif pool_name == 'neo4j' and self.neo4j_pool:
            await self.neo4j_pool.adjust_pool_size(new_size)
        elif pool_name == 'http' and self.http_pool:
            await self.http_pool.adjust_pool_size(new_size)
        else:
            logger.warning(f"未知的连接池名称: {pool_name}")
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有连接池的统计信息"""
        stats = {}
        
        if self.mysql_pool:
            stats['mysql'] = self.mysql_pool.get_stats()
        
        if self.neo4j_pool:
            stats['neo4j'] = self.neo4j_pool.get_stats()
        
        if self.http_pool:
            stats['http'] = self.http_pool.get_stats()
        
        return stats
    
    async def close(self):
        """关闭所有连接池"""
        tasks = []
        
        if self.mysql_pool:
            tasks.append(self.mysql_pool.close())
        
        if self.neo4j_pool:
            tasks.append(self.neo4j_pool.close())
        
        if self.http_pool:
            tasks.append(self.http_pool.close())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self._initialized = False
        logger.info("连接池管理器已关闭")
