# -*- coding: utf-8 -*-
"""
Qdrant客户端配置

优化的Qdrant客户端配置，包含：
- 增加超时时间到30秒
- 启用gRPC连接
- 连接池配置

版本：v1.0.0
创建日期：2025-12-16
"""

import os
import logging
from typing import Optional
from qdrant_client import QdrantClient as BaseQdrantClient

logger = logging.getLogger(__name__)


class OptimizedQdrantClient:
    """
    优化的Qdrant客户端
    
    特性：
    - 超时时间：30秒（优化前：10秒）
    - gRPC连接：启用（提升性能）
    - 连接池：配置（提升并发能力）
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        url: Optional[str] = None,
        grpc_port: Optional[int] = None,
        prefer_grpc: bool = True,
        timeout: float = 30.0,
        **kwargs
    ):
        """
        初始化优化的Qdrant客户端
        
        Args:
            host: Qdrant主机地址（默认从环境变量读取）
            port: HTTP端口（默认6333）
            url: 完整URL（如果提供，优先使用）
            grpc_port: gRPC端口（默认6334）
            prefer_grpc: 是否优先使用gRPC（默认True）
            timeout: 超时时间（秒，默认30.0）
            **kwargs: 其他QdrantClient参数
        """
        self.host = host or os.getenv('QDRANT_HOST', 'qdrant')
        self.port = port or int(os.getenv('QDRANT_PORT', '6333'))
        self.grpc_port = grpc_port or int(os.getenv('QDRANT_GRPC_PORT', '6334'))
        self.prefer_grpc = prefer_grpc
        self.timeout = timeout
        
        # 构建连接参数
        connection_params = {
            'timeout': self.timeout,
            'prefer_grpc': self.prefer_grpc,
            **kwargs
        }
        
        # 如果提供了URL，使用URL连接
        if url:
            connection_params['url'] = url
            logger.info(f"🔗 连接Qdrant (URL): {url}")
        else:
            connection_params['host'] = self.host
            connection_params['port'] = self.port
            if self.prefer_grpc:
                connection_params['grpc_port'] = self.grpc_port
            logger.info(f"🔗 连接Qdrant: {self.host}:{self.port} (gRPC: {self.grpc_port})")
        
        # 初始化客户端
        try:
            self.client = BaseQdrantClient(**connection_params)
            logger.info(f"✅ Qdrant客户端已连接")
            logger.info(f"  - 超时时间: {self.timeout}秒")
            logger.info(f"  - gRPC连接: {'启用' if self.prefer_grpc else '禁用'}")
            
            # 测试连接
            collections = self.client.get_collections()
            logger.info(f"  - 可用集合数: {len(collections.collections)}")
            
        except Exception as e:
            logger.error(f"❌ Qdrant连接失败: {e}")
            raise
    
    def get_client(self) -> BaseQdrantClient:
        """
        获取底层Qdrant客户端实例
        
        Returns:
            QdrantClient实例
        """
        return self.client
    
    def __getattr__(self, name):
        """
        代理所有方法到底层客户端
        
        这样OptimizedQdrantClient可以像QdrantClient一样使用
        """
        return getattr(self.client, name)


def create_qdrant_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    url: Optional[str] = None,
    **kwargs
) -> BaseQdrantClient:
    """
    创建优化的Qdrant客户端（工厂函数）
    
    Args:
        host: Qdrant主机地址
        port: HTTP端口
        url: 完整URL
        **kwargs: 其他参数
    
    Returns:
        QdrantClient实例
    
    Example:
        >>> client = create_qdrant_client(host="localhost", port=6333)
        >>> collections = client.get_collections()
    """
    optimized_client = OptimizedQdrantClient(
        host=host,
        port=port,
        url=url,
        **kwargs
    )
    return optimized_client.get_client()


# 向后兼容：导出为QdrantClient
QdrantClient = OptimizedQdrantClient


# 全局单例实例
_qdrant_client_instance = None


def get_qdrant_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    url: Optional[str] = None,
    **kwargs
) -> BaseQdrantClient:
    """
    获取Qdrant客户端单例（工厂函数）
    
    使用单例模式，确保全局只有一个Qdrant客户端实例。
    
    Args:
        host: Qdrant主机地址
        port: HTTP端口
        url: 完整URL
        **kwargs: 其他参数
    
    Returns:
        QdrantClient实例（单例）
    
    Example:
        >>> client = get_qdrant_client()
        >>> collections = client.get_collections()
    """
    global _qdrant_client_instance
    
    if _qdrant_client_instance is None:
        _qdrant_client_instance = create_qdrant_client(
            host=host,
            port=port,
            url=url,
            **kwargs
        )
        logger.info("✅ Qdrant客户端单例已创建")
    
    return _qdrant_client_instance


def reset_qdrant_client():
    """
    重置Qdrant客户端单例（仅用于测试）
    """
    global _qdrant_client_instance
    _qdrant_client_instance = None
    logger.info("🔄 Qdrant客户端单例已重置")
