"""
DAML-RAG v3 统一配置

所有配置通过环境变量 + 默认值管理。
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EmbeddingConfig:
    """Embedding 服务配置"""
    provider: str = os.getenv("EMBEDDING_PROVIDER", "openai")
    model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    api_base: str = os.getenv("EMBEDDING_API_BASE", "https://api.openai.com/v1")
    dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
    batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))


@dataclass
class EngineConfig:
    """浪潮引擎配置"""
    # 向量融合权重
    query_weight: float = float(os.getenv("ENGINE_QUERY_WEIGHT", "0.7"))
    spike_weight: float = float(os.getenv("ENGINE_SPIKE_WEIGHT", "0.15"))
    profile_weight: float = float(os.getenv("ENGINE_PROFILE_WEIGHT", "0.15"))

    # 脉冲传播
    spike_depth: int = int(os.getenv("ENGINE_SPIKE_DEPTH", "2"))
    spike_decay: float = float(os.getenv("ENGINE_SPIKE_DECAY", "0.5"))

    # CalibratedFusion
    fusion_alpha: float = float(os.getenv("ENGINE_FUSION_ALPHA", "0.6"))
    fusion_enabled: bool = os.getenv("ENGINE_FUSION_ENABLED", "true").lower() == "true"

    # GraphConvRerank
    gc_alpha: float = float(os.getenv("ENGINE_GC_ALPHA", "0.8"))
    gc_enabled: bool = os.getenv("ENGINE_GC_ENABLED", "true").lower() == "true"

    # 测地线重排
    geodesic_enabled: bool = os.getenv("ENGINE_GEODESIC_ENABLED", "true").lower() == "true"
    svd_diversity_threshold: float = float(os.getenv("ENGINE_SVD_THRESHOLD", "0.3"))

    # EPA
    epa_enabled: bool = os.getenv("ENGINE_EPA_ENABLED", "true").lower() == "true"

    # 残差金字塔
    pyramid_enabled: bool = os.getenv("ENGINE_PYRAMID_ENABLED", "true").lower() == "true"
    pyramid_max_levels: int = int(os.getenv("ENGINE_PYRAMID_LEVELS", "3"))

    # QueryReshaper
    reshaper_enabled: bool = os.getenv("ENGINE_RESHAPER_ENABLED", "true").lower() == "true"
    reshaper_alpha: float = float(os.getenv("ENGINE_RESHAPER_ALPHA", "0.85"))

    # 统计共现（预留，默认关闭）
    cooccurrence_enabled: bool = os.getenv("ENGINE_COOCCURRENCE_ENABLED", "false").lower() == "true"


@dataclass
class DataConfig:
    """数据层配置"""
    data_dir: str = os.getenv("DATA_DIR", "/app/data")
    vectors_dir: str = ""
    graph_dir: str = ""
    anchors_dir: str = ""

    def __post_init__(self):
        self.vectors_dir = os.path.join(self.data_dir, "vectors")
        self.graph_dir = os.path.join(self.data_dir, "graph")
        self.anchors_dir = os.path.join(self.data_dir, "anchors")


@dataclass
class BackendConfig:
    """后端 API 代理配置"""
    base_url: str = os.getenv("BACKEND_BASE_URL", "http://fitness_nginx_v2:8000")
    timeout: float = float(os.getenv("BACKEND_TIMEOUT", "10.0"))


@dataclass
class Config:
    """全局配置"""
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    data: DataConfig = field(default_factory=DataConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)

    # 日志级别
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


# 全局单例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置单例"""
    global _config
    if _config is None:
        _config = Config()
    return _config
