"""
conftest.py — 共享 fixtures

提供 DataStore / WaveEngine / SafetyEngine 的单例 fixture，
避免每个测试重复加载数据（~1s）。
"""

import sys
import pytest
import pytest_asyncio
import numpy as np

sys.path.insert(0, "/app")

from src_v2.config import get_config
from src_v2.data.loader import DataStore
from src_v2.engine.wave_engine import WaveEngine
from src_v2.rules.safety_engine import SafetyEngine


# === 全局单例（session 级别，只加载一次） ===

_data_store = None
_wave_engine = None
_safety_engine = None


@pytest_asyncio.fixture(scope="session")
async def data_store():
    """加载数据层（session 级别缓存）"""
    global _data_store
    if _data_store is None:
        cfg = get_config()
        _data_store = DataStore(config=cfg.data)
        await _data_store.load()
    return _data_store


@pytest.fixture(scope="session")
def config():
    """全局配置"""
    return get_config()


@pytest_asyncio.fixture(scope="session")
async def wave_engine(data_store):
    """浪潮引擎实例"""
    global _wave_engine
    if _wave_engine is None:
        cfg = get_config()
        _wave_engine = WaveEngine(data_store=data_store, config=cfg.engine)
    return _wave_engine


@pytest_asyncio.fixture(scope="session")
async def safety_engine(data_store):
    """安全引擎实例"""
    global _safety_engine
    if _safety_engine is None:
        _safety_engine = SafetyEngine(
            graph_store=data_store.graph,
            metadata_store=data_store.metadata,
        )
    return _safety_engine


@pytest.fixture
def random_query_vec():
    """随机查询向量（用于管线测试，不依赖 Embedding 模型）"""
    vec = np.random.randn(1024).astype(np.float32)
    return vec / np.linalg.norm(vec)
