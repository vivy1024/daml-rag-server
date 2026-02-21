# -*- coding: utf-8 -*-
"""
config.py 单元测试

验证 Pydantic BaseSettings 配置加载、fail-fast 校验、to_dict 转换。
"""

import os
import pytest
from unittest.mock import patch


class TestMySQLConfig:
    """MySQL 配置测试"""

    def test_default_values(self):
        """默认值应为 Docker 容器内地址"""
        from src.framework.config import MySQLConfig
        with patch.dict(os.environ, {}, clear=True):
            config = MySQLConfig()
            assert config.host == 'fitness_mysql'
            assert config.port == 3306
            assert config.user == 'root'
            assert config.database == 'fitness_app'

    def test_env_override(self):
        """环境变量应覆盖默认值"""
        from src.framework.config import MySQLConfig
        env = {
            'MYSQL_HOST': 'custom-host',
            'MYSQL_PORT': '3307',
            'MYSQL_USER': 'admin',
            'MYSQL_PASSWORD': 'secret',
            'MYSQL_DATABASE': 'testdb',
        }
        with patch.dict(os.environ, env, clear=True):
            config = MySQLConfig()
            assert config.host == 'custom-host'
            assert config.port == 3307
            assert config.password == 'secret'

    def test_to_dict(self):
        """to_dict 应返回 ConnectionPoolManager 兼容格式"""
        from src.framework.config import MySQLConfig
        with patch.dict(os.environ, {'MYSQL_PASSWORD': 'pw'}, clear=True):
            config = MySQLConfig()
            d = config.to_dict()
            assert set(d.keys()) == {'host', 'port', 'user', 'password', 'database'}
            assert isinstance(d['port'], int)


class TestNeo4jConfig:
    """Neo4j 配置测试"""

    def test_fail_fast_no_password(self):
        """NEO4J_PASSWORD 未设置时应抛出 ValidationError"""
        from src.framework.config import Neo4jConfig
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception, match='NEO4J_PASSWORD'):
                Neo4jConfig()

    def test_with_password(self):
        """设置密码后应正常创建"""
        from src.framework.config import Neo4jConfig
        with patch.dict(os.environ, {'NEO4J_PASSWORD': 'test123'}, clear=True):
            config = Neo4jConfig()
            assert config.password == 'test123'
            assert config.uri == 'bolt://fitness_neo4j:7687'

    def test_to_dict(self):
        """to_dict 应包含 uri/user/password"""
        from src.framework.config import Neo4jConfig
        with patch.dict(os.environ, {'NEO4J_PASSWORD': 'pw'}, clear=True):
            d = Neo4jConfig().to_dict()
            assert 'uri' in d
            assert 'user' in d
            assert 'password' in d


class TestQdrantConfig:
    """Qdrant 配置测试"""

    def test_defaults(self):
        from src.framework.config import QdrantConfig
        with patch.dict(os.environ, {}, clear=True):
            config = QdrantConfig()
            assert config.host == 'fitness_qdrant'
            assert config.port == 6333
            assert config.grpc_port == 6334
            assert config.prefer_grpc is True
            assert config.https is False
            assert config.api_key is None


class TestInternalTokenConfig:
    """内部 Token 配置测试"""

    def test_fail_fast_no_token(self):
        """INTERNAL_API_TOKEN 未设置时应抛出 ValidationError"""
        from src.framework.config import InternalTokenConfig
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception, match='INTERNAL_API_TOKEN'):
                InternalTokenConfig()

    def test_with_token(self):
        from src.framework.config import InternalTokenConfig
        with patch.dict(os.environ, {'INTERNAL_API_TOKEN': 'abc123'}, clear=True):
            config = InternalTokenConfig()
            assert config.api_token == 'abc123'


class TestBackendAPIConfig:
    """后端 API 配置测试"""

    def test_defaults(self):
        from src.framework.config import BackendAPIConfig
        with patch.dict(os.environ, {}, clear=True):
            config = BackendAPIConfig()
            assert config.api_url == 'http://host.docker.internal:8000'
            assert config.api_timeout == 10.0
            assert config.base_url == 'http://host.docker.internal:8000'

    def test_env_override(self):
        from src.framework.config import BackendAPIConfig
        with patch.dict(os.environ, {'BACKEND_API_URL': 'http://nginx:8000'}, clear=True):
            config = BackendAPIConfig()
            assert config.base_url == 'http://nginx:8000'


class TestServiceConfig:
    """服务配置测试"""

    def test_defaults(self):
        from src.framework.config import ServiceConfig
        with patch.dict(os.environ, {}, clear=True):
            config = ServiceConfig()
            assert config.log_level == 'WARNING'
            assert config.use_api_pool is True
            assert config.dual_model_enabled is False

    def test_bool_parsing(self):
        """布尔值应正确解析 true/false 字符串"""
        from src.framework.config import ServiceConfig
        with patch.dict(os.environ, {
            'DUAL_MODEL_ENABLED': 'true',
            'USE_API_POOL': 'false',
        }, clear=True):
            config = ServiceConfig()
            assert config.dual_model_enabled is True
            assert config.use_api_pool is False


class TestGetConfig:
    """全局配置单例测试"""

    def test_singleton(self):
        """get_config 应返回同一实例"""
        from src.framework.config import get_config, reset_config
        reset_config()
        env = {
            'NEO4J_PASSWORD': 'test',
            'INTERNAL_API_TOKEN': 'token',
        }
        with patch.dict(os.environ, env):
            c1 = get_config()
            c2 = get_config()
            assert c1 is c2

    def test_reset(self):
        """reset_config 后应创建新实例"""
        from src.framework.config import get_config, reset_config
        env = {
            'NEO4J_PASSWORD': 'test',
            'INTERNAL_API_TOKEN': 'token',
        }
        with patch.dict(os.environ, env):
            c1 = get_config()
            reset_config()
            c2 = get_config()
            assert c1 is not c2
