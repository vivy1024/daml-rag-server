# -*- coding: utf-8 -*-
"""
BaseMCPTool基类 - v3.0.0 (Mixin架构)

所有Python MCP工具的统一接口。职责已拆分为4个Mixin：
- VersionedToolMixin: 版本管理 (Requirements 12.1-12.5)
- CachedToolMixin: 缓存集成
- MonitoredToolMixin: 性能监控
- ThreeLayerQueryMixin: 三层检索标准化 (Requirements 17.1-17.6)

BaseMCPTool 组合所有Mixin，子类只需继承BaseMCPTool即可获得全部功能。

版本: 3.0.0
日期: 2026-02-19
Task 44 - Phase 7 Batch 4 架构重构
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel
from dataclasses import dataclass, field
import logging

from .mixins.versioned import (
    VersionedToolMixin,
    VersionInfo,
    ChangelogEntry,
)
from .mixins.cached import CachedToolMixin
from .mixins.monitored import MonitoredToolMixin
from .mixins.three_layer_query import (
    ThreeLayerQueryMixin,
    ThreeLayerQueryResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 元数据数据类
# =============================================================================

@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    category: str
    complexity: str
    estimated_duration_ms: float
    requires_user_profile: bool
    dependencies: List[str]
    version: str = "1.0.0"
    changelog: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# BaseMCPTool基类（≤100行核心逻辑）
# =============================================================================

class BaseMCPTool(
    VersionedToolMixin,
    CachedToolMixin,
    MonitoredToolMixin,
    ThreeLayerQueryMixin,
    ABC,
):
    """
    MCP工具基类 - Mixin组合架构

    子类只需实现6个抽象方法：
    get_name, get_description, get_category,
    get_input_schema, get_output_schema, execute
    """

    def __init__(
        self,
        neo4j_client,
        qdrant_client,
        three_layer_engine,
        cache_manager=None,
        error_handler=None,
        logger: Optional[logging.Logger] = None,
    ):
        self.neo4j_client = neo4j_client
        self.qdrant_client = qdrant_client
        self.three_layer_engine = three_layer_engine
        self.cache_manager = cache_manager
        self.error_handler = error_handler
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        if self.three_layer_engine is None:
            self.logger.warning(
                f"⚠️ 工具 {self.get_name()} 未注入三层检索引擎，"
                "部分功能可能不可用"
            )

    # ── 抽象方法 ──────────────────────────────────────────

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass

    @abstractmethod
    def get_category(self) -> str:
        pass

    @abstractmethod
    def get_input_schema(self) -> type[BaseModel]:
        pass

    @abstractmethod
    def get_output_schema(self) -> type[BaseModel]:
        pass

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    # ── 元数据 ────────────────────────────────────────────

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.get_name(),
            description=self.get_description(),
            category=self.get_category(),
            complexity=self.get_complexity(),
            estimated_duration_ms=self.get_estimated_duration(),
            requires_user_profile=self.requires_user_profile(),
            dependencies=self.get_dependencies(),
            version=self.get_version(),
            changelog=self.get_changelog(),
        )

    def get_complexity(self) -> str:
        return "medium"

    def get_estimated_duration(self) -> float:
        return 1000.0

    def requires_user_profile(self) -> bool:
        return True

    def get_dependencies(self) -> List[str]:
        return ["neo4j", "qdrant", "three_layer_engine"]


# =============================================================================
# 版本注册表（保持向后兼容）
# =============================================================================

class MCPToolVersionRegistry:
    """MCP工具版本注册表 (Req 12.4)"""

    _instance = None
    _tools: Dict[str, BaseMCPTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, tool: BaseMCPTool) -> None:
        self._tools[tool.get_name()] = tool

    def get_tool_version(self, tool_name: str) -> Optional[str]:
        tool = self._tools.get(tool_name)
        return tool.get_version() if tool else None

    def get_all_versions(self) -> Dict[str, str]:
        return {name: tool.get_version() for name, tool in self._tools.items()}

    def get_tool_changelog(self, tool_name: str) -> Optional[List[Dict[str, Any]]]:
        tool = self._tools.get(tool_name)
        return tool.get_changelog() if tool else None

    def check_compatibility(
        self, tool_name: str, required_version: str
    ) -> Tuple[bool, str]:
        tool = self._tools.get(tool_name)
        if not tool:
            return False, f"工具 {tool_name} 未注册"
        current = tool.get_version()
        ok = tool.is_compatible_with_version(required_version)
        if ok:
            return True, f"版本兼容: 当前 {current}, 要求 {required_version}"
        return False, f"版本不兼容: 当前 {current}, 要求 {required_version}"


_version_registry = MCPToolVersionRegistry()


def get_version_registry() -> MCPToolVersionRegistry:
    return _version_registry
