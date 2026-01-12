"""
MCP框架模块

提供MCP工具的核心功能：
- 统一错误处理
- 缓存管理
- 工具注册
- 版本管理 - Requirements 12.1-12.5
"""

from .error_handler import (
    MCPToolError,
    MCPErrorCode,
    MCPErrorHandler,
    create_mcp_error,
    wrap_mcp_error
)

from .cache_manager import (
    CacheManager,
    CacheEntry,
    CacheStatistics,
    get_cache_manager,
    cached
)

__all__ = [
    # 错误处理
    "MCPToolError",
    "MCPErrorCode",
    "MCPErrorHandler",
    "create_mcp_error",
    "wrap_mcp_error",
    # 缓存管理
    "CacheManager",
    "CacheEntry",
    "CacheStatistics",
    "get_cache_manager",
    "cached",
]
