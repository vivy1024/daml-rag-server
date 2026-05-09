# -*- coding: utf-8 -*-
"""
集中配置管理模块

使用 Pydantic BaseSettings 统一管理所有环境变量，替代散落在各文件中的 os.getenv 调用。
启动时 fail-fast 校验：必需的密钥/密码缺失时直接抛异常阻止启动。

版本: v1.0.0
日期: 2026-02-21
"""

from typing import Optional

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MySQLConfig(BaseSettings):
    """MySQL 连接配置"""
    model_config = SettingsConfigDict(env_prefix='MYSQL_')

    host: str = 'fitness_mysql'
    port: int = 3306
    user: str = 'root'
    password: str = ''
    database: str = 'fitness_app'

    def to_dict(self) -> dict:
        """转换为 ConnectionPoolManager 需要的 dict 格式"""
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'database': self.database,
        }


class Neo4jConfig(BaseSettings):
    """Neo4j 连接配置"""
    model_config = SettingsConfigDict(env_prefix='NEO4J_')

    uri: str = 'bolt://fitness_neo4j:7687'
    user: str = 'neo4j'
    password: str = ''
    database: str = 'neo4j'

    @model_validator(mode='after')
    def check_password(self):
        if not self.password:
            raise ValueError(
                'NEO4J_PASSWORD 未设置。请在环境变量或 .env 文件中配置。'
            )
        return self

    def to_dict(self) -> dict:
        """转换为 ConnectionPoolManager 需要的 dict 格式"""
        return {
            'uri': self.uri,
            'user': self.user,
            'password': self.password,
        }


class QdrantConfig(BaseSettings):
    """Qdrant 向量数据库配置"""
    model_config = SettingsConfigDict(env_prefix='QDRANT_')

    host: str = 'fitness_qdrant'
    port: int = 6333
    grpc_port: int = 6334
    api_key: Optional[str] = None
    prefer_grpc: bool = True
    https: bool = False
    collection: str = 'default_collection'


class RedisConfig(BaseSettings):
    """Redis 配置"""
    model_config = SettingsConfigDict(env_prefix='REDIS_')

    host: str = 'fitness_redis'
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


class BackendAPIConfig(BaseSettings):
    """Laravel 后端 API 配置"""
    model_config = SettingsConfigDict(env_prefix='BACKEND_')

    api_url: str = 'http://host.docker.internal:8000'
    api_timeout: float = 10.0
    api_max_retries: int = 3
    pool_max_connections: int = 100
    pool_max_keepalive: int = 20
    pool_keepalive_expiry: float = 5.0
    membership_timeout_ms: int = 2000
    user_profile_timeout_ms: int = 5000

    @property
    def base_url(self) -> str:
        return self.api_url


class InternalTokenConfig(BaseSettings):
    """内部服务 Token 配置"""
    model_config = SettingsConfigDict(env_prefix='INTERNAL_')

    api_token: str = ''

    @model_validator(mode='after')
    def check_token(self):
        if not self.api_token:
            raise ValueError(
                'INTERNAL_API_TOKEN 未设置。请在环境变量或 .env 文件中配置。'
            )
        return self


class LLMBaseConfig(BaseSettings):
    """LLM 通用配置"""
    model_config = SettingsConfigDict(env_prefix='LLM_')

    timeout: float = 120.0
    max_tokens: int = 2000
    temperature: float = 0.7
    max_retries: int = 2
    retry_delay: float = 2.0


class DeepSeekConfig(BaseSettings):
    """DeepSeek LLM 配置"""
    model_config = SettingsConfigDict(env_prefix='DEEPSEEK_')

    api_key: str = ''
    base_url: str = 'https://api.deepseek.com/v1'
    model: str = 'deepseek-chat'


class MoonshotConfig(BaseSettings):
    """Moonshot Kimi 配置"""
    model_config = SettingsConfigDict(env_prefix='MOONSHOT_')

    enabled: bool = False
    api_key: str = ''
    base_url: str = 'https://api.moonshot.cn/v1'
    model: str = 'moonshot-v1-8k'


class QwenConfig(BaseSettings):
    """通义千问配置"""
    model_config = SettingsConfigDict(env_prefix='QWEN_')

    enabled: bool = False
    api_key: str = ''
    base_url: str = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    model: str = 'qwen-turbo'


class SiliconFlowConfig(BaseSettings):
    """SiliconFlow 配置"""
    model_config = SettingsConfigDict(env_prefix='SILICONFLOW_')

    enabled: bool = False
    api_key: str = ''
    base_url: str = 'https://api.siliconflow.cn/v1'
    model: str = 'Qwen/Qwen2.5-7B-Instruct'


class GLMConfig(BaseSettings):
    """智谱 GLM 配置"""
    model_config = SettingsConfigDict(env_prefix='GLM_')

    enabled: bool = False
    api_key: str = ''
    base_url: str = 'https://open.bigmodel.cn/api/paas/v4'
    model: str = 'glm-4-flash'


class APIConfig(BaseSettings):
    """API 服务配置"""
    model_config = SettingsConfigDict(env_prefix='')

    environment: str = 'development'
    host: str = '0.0.0.0'
    port: int = Field(default=8001, validation_alias=AliasChoices('API_PORT', 'PORT'))
    cors_extra_origins: str = ''
    enable_rate_limit: bool = True
    enable_auth: bool = True
    enable_input_validation: bool = True
    internal_jwt_secret: str = ''
    internal_jwt_issuer: str = 'fitness-backend'
    legacy_auth_enabled: bool = False
    debug: bool = False


class FrameworkConfig(BaseSettings):
    """框架配置"""
    model_config = SettingsConfigDict(env_prefix='')

    metadata_db_path: str = '/tmp/metadata.db'
    mcp_config_path: str = '/app/config/mcp_registry.json'
    mcp_metadata_db_path: str = '/tmp/mcp_metadata.db'
    embedding_model: str = 'BAAI/bge-small-zh-v1.5'


class ServiceConfig(BaseSettings):
    """服务运行配置"""
    model_config = SettingsConfigDict(env_prefix='')

    log_level: str = 'WARNING'
    enable_request_logging: bool = False
    enable_file_logging: bool = True
    use_new_cache: bool = True
    use_api_pool: bool = True
    dual_model_enabled: bool = False


class DatabaseConfig:
    """数据库配置聚合（MySQL + Neo4j + Qdrant + Redis）"""

    def __init__(self):
        self.mysql = MySQLConfig()
        self.neo4j = Neo4jConfig()
        self.qdrant = QdrantConfig()
        self.redis = RedisConfig()


class LLMProviderConfig:
    """LLM 配置聚合（DeepSeek + Moonshot + Qwen + SiliconFlow + GLM + 通用参数）"""

    def __init__(self):
        self.base = LLMBaseConfig()
        self.deepseek = DeepSeekConfig()
        self.moonshot = MoonshotConfig()
        self.qwen = QwenConfig()
        self.siliconflow = SiliconFlowConfig()
        self.glm = GLMConfig()


class AppConfig:
    """
    应用全局配置（单例）

    使用方式::

        from src.framework.config import get_config
        config = get_config()
        config.database.mysql.host  # -> 'fitness_mysql'
        config.database.neo4j.to_dict()  # -> {'uri': ..., 'user': ..., 'password': ...}
    """

    def __init__(self):
        self.database = DatabaseConfig()
        self.llm = LLMProviderConfig()
        self.backend = BackendAPIConfig()
        self.internal = InternalTokenConfig()
        self.service = ServiceConfig()
        self.api = APIConfig()
        self.framework = FrameworkConfig()


# ============ 单例 ============

_config_instance: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置单例（首次调用时初始化并执行 fail-fast 校验）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance


def reset_config() -> None:
    """重置配置单例（仅用于测试）"""
    global _config_instance
    _config_instance = None
