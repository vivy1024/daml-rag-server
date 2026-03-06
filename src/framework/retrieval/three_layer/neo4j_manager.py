# -*- coding: utf-8 -*-
"""
三层检索引擎 - Neo4j连接管理器
"""

import logging
from typing import Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Neo4jConnectionManager:
    """
    企业级Neo4j连接管理器

    功能:
    1. 连接池管理
    2. 健康检查
    3. 自动重连
    4. 优雅关闭
    """

    def __init__(
        self,
        uri: str = "bolt://neo4j:7687",
        user: str = "neo4j",
        password: Optional[str] = None,
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
        connection_timeout: float = 30.0
    ):
        """初始化Neo4j连接管理器"""
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.is_connected = False
        self.last_health_check = None

        # 连接池配置
        self.config = {
            "max_connection_lifetime": max_connection_lifetime,
            "max_connection_pool_size": max_connection_pool_size,
            "connection_timeout": connection_timeout
        }

        logger.info(f"Neo4j连接管理器已创建 - URI: {uri}, User: {user}, Password: {'***' if password else 'None'}")

    def connect(self) -> bool:
        """建立Neo4j连接"""
        try:
            from neo4j import GraphDatabase

            # 创建驱动实例
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password) if self.password else None,
                max_connection_lifetime=self.config["max_connection_lifetime"],
                max_connection_pool_size=self.config["max_connection_pool_size"],
                connection_timeout=self.config["connection_timeout"]
            )

            # 验证连接
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                test_value = result.single()["test"]
                if test_value == 1:
                    self.is_connected = True
                    self.last_health_check = datetime.now()
                    logger.info("✅ Neo4j连接成功建立")
                    return True
                else:
                    logger.error("❌ Neo4j连接验证失败")
                    return False

        except ImportError:
            logger.error("❌ Neo4j驱动未安装: pip install neo4j")
            return False
        except Exception as e:
            logger.error(f"❌ Neo4j连接失败: {e}")
            self.is_connected = False
            return False

    @contextmanager
    def get_session(self):
        """获取Neo4j会话 (上下文管理器)"""
        if not self.is_connected or not self.driver:
            raise RuntimeError("Neo4j未连接,请先调用connect()")

        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.driver:
                return False

            with self.driver.session() as session:
                result = session.run("RETURN 1 AS health")
                result.single()
                self.last_health_check = datetime.now()
                return True
        except Exception as e:
            logger.warning(f"Neo4j健康检查失败: {e}")
            self.is_connected = False
            return False

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.is_connected = False
            logger.info("Neo4j连接已关闭")
