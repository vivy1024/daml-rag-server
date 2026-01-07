"""
BaseMCPTool基类 - 增强版

定义所有Python MCP工具的统一接口和通用功能

增强功能：
1. 标准化三层检索调用 - Requirements 17.1-17.6
2. 版本管理 - Requirements 12.1-12.5
3. 统一错误处理
4. 缓存机制集成
5. 性能监控

版本: 2.0.0
日期: 2026-01-06
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel
from dataclasses import dataclass, field
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# 版本管理数据类
# =============================================================================

@dataclass
class VersionInfo:
    """
    工具版本信息
    
    Attributes:
        major: 主版本号（不兼容的API变更）
        minor: 次版本号（向后兼容的功能新增）
        patch: 补丁版本号（向后兼容的问题修复）
    """
    major: int
    minor: int
    patch: int
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, VersionInfo):
            return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
        return False
    
    def __lt__(self, other) -> bool:
        if isinstance(other, VersionInfo):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        return NotImplemented
    
    def is_compatible_with(self, other: 'VersionInfo') -> bool:
        """
        检查版本兼容性（同一主版本内兼容）
        
        Requirements: 12.5
        """
        return self.major == other.major
    
    @classmethod
    def from_string(cls, version_str: str) -> 'VersionInfo':
        """从字符串解析版本号"""
        parts = version_str.split('.')
        if len(parts) != 3:
            raise ValueError(f"无效的版本号格式: {version_str}")
        return cls(
            major=int(parts[0]),
            minor=int(parts[1]),
            patch=int(parts[2])
        )


@dataclass
class ChangelogEntry:
    """
    变更日志条目
    
    Attributes:
        version: 版本号
        date: 变更日期
        changes: 变更列表
        breaking_changes: 破坏性变更列表
    """
    version: str
    date: str
    changes: List[str]
    breaking_changes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "date": self.date,
            "changes": self.changes,
            "breaking_changes": self.breaking_changes
        }


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    category: str  # exercise, training, safety, nutrition, analytics, utility
    complexity: str  # simple, medium, complex
    estimated_duration_ms: float
    requires_user_profile: bool
    dependencies: List[str]
    version: str = "1.0.0"
    changelog: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# 三层检索结果数据类
# =============================================================================

@dataclass
class ThreeLayerQueryResult:
    """
    三层检索查询结果
    
    用于标准化三层检索的返回结果
    """
    success: bool
    results: List[Dict[str, Any]]
    layer_stats: Dict[str, Any]
    execution_time_ms: float
    confidence: float
    reasoning: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "results": self.results,
            "layer_stats": self.layer_stats,
            "execution_time_ms": self.execution_time_ms,
            "confidence": self.confidence,
            "reasoning": self.reasoning
        }


# =============================================================================
# BaseMCPTool基类
# =============================================================================

class BaseMCPTool(ABC):
    """
    MCP工具基类 - 增强版
    
    所有Python MCP工具必须继承此基类并实现抽象方法
    
    设计原则：
    1. 统一接口：所有工具实现相同的execute()方法
    2. 类型安全：使用Pydantic进行输入输出验证
    3. 依赖注入：通过构造函数注入数据库客户端和检索引擎
    4. 性能监控：自动记录执行时间和资源使用
    5. 错误处理：统一的异常类型和错误格式
    6. 三层检索标准化：所有工具通过三层检索引擎查询 - Requirements 17.1-17.6
    7. 版本管理：支持版本号和变更日志 - Requirements 12.1-12.5
    
    新增功能 (v2.0.0):
    - 标准化三层检索调用方法
    - 版本管理属性和方法
    - 缓存机制集成
    - 增强的错误处理
    """
    
    # 默认版本号
    _version: VersionInfo = VersionInfo(1, 0, 0)
    
    # 变更日志
    _changelog: List[ChangelogEntry] = []
    
    def __init__(
        self,
        neo4j_client,
        qdrant_client,
        three_layer_engine,
        cache_manager=None,
        error_handler=None,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化工具
        
        Args:
            neo4j_client: Neo4j客户端实例
            qdrant_client: Qdrant客户端实例
            three_layer_engine: 三层检索引擎实例（必需依赖）- Requirements 17.1
            cache_manager: 缓存管理器（可选）
            error_handler: 错误处理器（可选）
            logger: 日志记录器（可选）
        """
        self.neo4j_client = neo4j_client
        self.qdrant_client = qdrant_client
        self.three_layer_engine = three_layer_engine
        self.cache_manager = cache_manager
        self.error_handler = error_handler
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # 验证三层检索引擎是必需依赖 - Requirements 17.1
        if self.three_layer_engine is None:
            self.logger.warning(
                f"⚠️ 工具 {self.get_name()} 未注入三层检索引擎，"
                "部分功能可能不可用"
            )
    
    # =========================================================================
    # 抽象方法（子类必须实现）
    # =========================================================================
    
    @abstractmethod
    def get_name(self) -> str:
        """返回工具名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """返回工具描述"""
        pass
    
    @abstractmethod
    def get_category(self) -> str:
        """
        返回工具分类
        
        可选值：exercise, training, safety, nutrition, analytics, utility
        """
        pass
    
    @abstractmethod
    def get_input_schema(self) -> type[BaseModel]:
        """返回输入Schema（Pydantic模型类）"""
        pass
    
    @abstractmethod
    def get_output_schema(self) -> type[BaseModel]:
        """返回输出Schema（Pydantic模型类）"""
        pass
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具逻辑
        
        Args:
            input_data: 输入数据（已验证）
        
        Returns:
            标准化输出格式：
            {
                "success": bool,
                "tool_name": str,
                "data": {...},
                "metadata": {
                    "execution_time_ms": float,
                    "timestamp": str,
                    "tool_version": str,
                    ...
                }
            }
        """
        pass
    
    # =========================================================================
    # 版本管理方法 - Requirements 12.1-12.5
    # =========================================================================
    
    def get_version(self) -> str:
        """
        返回工具版本号
        
        格式: "major.minor.patch" (如 "1.2.0")
        
        Requirements: 12.1
        """
        return str(self._version)
    
    def get_version_info(self) -> VersionInfo:
        """返回版本信息对象"""
        return self._version
    
    def get_changelog(self) -> List[Dict[str, Any]]:
        """
        返回变更日志
        
        Requirements: 12.2
        """
        return [entry.to_dict() for entry in self._changelog]
    
    def get_latest_changelog(self) -> Optional[Dict[str, Any]]:
        """返回最新的变更日志条目"""
        if self._changelog:
            return self._changelog[0].to_dict()
        return None
    
    def is_compatible_with_version(self, version_str: str) -> bool:
        """
        检查是否与指定版本兼容
        
        同一主版本内保持向后兼容
        
        Requirements: 12.5
        """
        try:
            other_version = VersionInfo.from_string(version_str)
            return self._version.is_compatible_with(other_version)
        except ValueError:
            return False
    
    @classmethod
    def set_version(cls, major: int, minor: int, patch: int) -> None:
        """设置工具版本（子类使用）"""
        cls._version = VersionInfo(major, minor, patch)
    
    @classmethod
    def add_changelog_entry(
        cls,
        version: str,
        date: str,
        changes: List[str],
        breaking_changes: Optional[List[str]] = None
    ) -> None:
        """添加变更日志条目（子类使用）"""
        entry = ChangelogEntry(
            version=version,
            date=date,
            changes=changes,
            breaking_changes=breaking_changes or []
        )
        cls._changelog.insert(0, entry)  # 最新的在前面
    
    # =========================================================================
    # 三层检索标准化方法 - Requirements 17.1-17.6
    # =========================================================================
    
    async def execute_three_layer_query(
        self,
        query: str,
        user_profile: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        domain: str = "fitness_exercises",
        safety_check: bool = True
    ) -> ThreeLayerQueryResult:
        """
        标准化三层检索调用
        
        所有MCP工具应通过此方法查询动作，而不是直接访问数据库
        
        Requirements: 17.2, 17.3
        
        Args:
            query: 查询文本
            user_profile: 用户档案（用于Layer3规则验证）- Requirements 17.3
            filters: 领域特定过滤条件（用于Layer2图谱推理）- Requirements 17.4
            top_k: 返回结果数
            domain: 检索领域
            safety_check: 是否执行安全检查
        
        Returns:
            ThreeLayerQueryResult: 标准化的检索结果
        """
        start_time = time.time()
        tool_name = self.get_name()
        
        # 检查三层检索引擎是否可用
        if self.three_layer_engine is None:
            self.logger.error(f"❌ 工具 {tool_name} 未注入三层检索引擎")
            return ThreeLayerQueryResult(
                success=False,
                results=[],
                layer_stats={},
                execution_time_ms=0,
                confidence=0,
                reasoning="三层检索引擎未初始化"
            )
        
        try:
            self.logger.info(
                f"🔍 [{tool_name}] 调用三层检索引擎 | "
                f"查询: {query[:50]}... | "
                f"top_k: {top_k}"
            )
            
            # 调用三层检索引擎 - Requirements 17.2
            result = await self.three_layer_engine.execute_three_layer_query(
                query=query,
                domain=domain,
                user_profile=user_profile,  # Requirements 17.3
                filters=filters,  # Requirements 17.4
                top_k=top_k,
                safety_check=safety_check
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # 记录执行结果 - Requirements 17.5
            layer_stats = {
                "layer1": {
                    "success": result.layer_1_result.success,
                    "count": len(result.layer_1_result.results),
                    "confidence": result.layer_1_result.confidence,
                    "execution_time_ms": result.layer_1_result.execution_time_ms
                },
                "layer2": {
                    "success": result.layer_2_result.success,
                    "count": len(result.layer_2_result.results),
                    "confidence": result.layer_2_result.confidence,
                    "execution_time_ms": result.layer_2_result.execution_time_ms
                },
                "layer3": {
                    "success": result.layer_3_result.success,
                    "count": len(result.layer_3_result.results),
                    "confidence": result.layer_3_result.confidence,
                    "execution_time_ms": result.layer_3_result.execution_time_ms
                }
            }
            
            self.logger.info(
                f"✅ [{tool_name}] 三层检索完成 | "
                f"结果数: {len(result.final_results)} | "
                f"置信度: {result.total_confidence:.2f} | "
                f"耗时: {execution_time_ms:.0f}ms"
            )
            
            return ThreeLayerQueryResult(
                success=True,
                results=result.final_results,
                layer_stats=layer_stats,
                execution_time_ms=execution_time_ms,
                confidence=result.total_confidence,
                reasoning=result.reasoning
            )
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # 错误处理 - Requirements 17.6
            self.logger.error(
                f"❌ [{tool_name}] 三层检索失败 | "
                f"错误: {e} | "
                f"耗时: {execution_time_ms:.0f}ms",
                exc_info=True
            )
            
            # 尝试降级处理
            fallback_result = await self._handle_three_layer_failure(
                query=query,
                filters=filters,
                top_k=top_k,
                error=e
            )
            
            return fallback_result
    
    async def _handle_three_layer_failure(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        top_k: int,
        error: Exception
    ) -> ThreeLayerQueryResult:
        """
        三层检索失败时的降级处理
        
        Requirements: 17.6
        """
        tool_name = self.get_name()
        self.logger.warning(
            f"⚠️ [{tool_name}] 启动降级策略 | "
            f"原因: {error}"
        )
        
        # 返回空结果，让调用方决定如何处理
        return ThreeLayerQueryResult(
            success=False,
            results=[],
            layer_stats={
                "error": str(error),
                "fallback_used": True
            },
            execution_time_ms=0,
            confidence=0,
            reasoning=f"三层检索失败: {error}"
        )
    
    # =========================================================================
    # 元数据方法
    # =========================================================================
    
    def get_metadata(self) -> ToolMetadata:
        """返回工具元数据（包含版本信息）"""
        return ToolMetadata(
            name=self.get_name(),
            description=self.get_description(),
            category=self.get_category(),
            complexity=self.get_complexity(),
            estimated_duration_ms=self.get_estimated_duration(),
            requires_user_profile=self.requires_user_profile(),
            dependencies=self.get_dependencies(),
            version=self.get_version(),
            changelog=self.get_changelog()
        )
    
    def get_complexity(self) -> str:
        """
        返回工具复杂度（子类可覆盖）
        
        可选值：simple, medium, complex
        """
        return "medium"
    
    def get_estimated_duration(self) -> float:
        """返回预估执行时间（毫秒，子类可覆盖）"""
        return 1000.0
    
    def requires_user_profile(self) -> bool:
        """是否需要用户档案（子类可覆盖）"""
        return True
    
    def get_dependencies(self) -> List[str]:
        """返回依赖列表（子类可覆盖）"""
        return ["neo4j", "qdrant", "three_layer_engine"]
    
    # =========================================================================
    # 执行包装器
    # =========================================================================
    
    async def execute_with_monitoring(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        带性能监控的执行包装器
        
        自动记录执行时间、捕获异常、标准化输出
        
        Args:
            input_data: 输入数据（未验证）
        
        Returns:
            标准化输出格式（包含性能元数据和版本信息）
        """
        start_time = time.time()
        tool_name = self.get_name()
        tool_version = self.get_version()
        
        try:
            # 验证输入
            input_schema = self.get_input_schema()
            validated_input = input_schema(**input_data)
            
            self.logger.info(f"🔧 开始执行工具: {tool_name} (v{tool_version})")
            
            # 执行工具
            result = await self.execute(validated_input.model_dump())
            
            # 添加元数据
            execution_time_ms = (time.time() - start_time) * 1000
            result.setdefault("metadata", {})
            result["metadata"]["execution_time_ms"] = execution_time_ms
            result["metadata"]["timestamp"] = datetime.now().isoformat()
            result["metadata"]["tool_name"] = tool_name
            result["metadata"]["tool_version"] = tool_version  # Requirements 12.3
            
            self.logger.info(
                f"✅ 工具执行成功: {tool_name} v{tool_version} "
                f"({execution_time_ms:.2f}ms)"
            )
            
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"❌ 工具执行失败: {tool_name} v{tool_version} "
                f"({execution_time_ms:.2f}ms) - {e}",
                exc_info=True
            )
            
            return {
                "success": False,
                "tool_name": tool_name,
                "error": {
                    "code": "TOOL_EXECUTION_ERROR",
                    "message": str(e),
                    "type": type(e).__name__
                },
                "metadata": {
                    "execution_time_ms": execution_time_ms,
                    "timestamp": datetime.now().isoformat(),
                    "tool_version": tool_version
                }
            }


# =============================================================================
# 版本查询API
# =============================================================================

class MCPToolVersionRegistry:
    """
    MCP工具版本注册表
    
    提供版本查询API
    
    Requirements: 12.4
    """
    
    _instance = None
    _tools: Dict[str, BaseMCPTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, tool: BaseMCPTool) -> None:
        """注册工具"""
        self._tools[tool.get_name()] = tool
    
    def get_tool_version(self, tool_name: str) -> Optional[str]:
        """
        获取工具版本
        
        Requirements: 12.4
        """
        tool = self._tools.get(tool_name)
        if tool:
            return tool.get_version()
        return None
    
    def get_all_versions(self) -> Dict[str, str]:
        """
        获取所有工具版本
        
        Requirements: 12.4
        """
        return {
            name: tool.get_version()
            for name, tool in self._tools.items()
        }
    
    def get_tool_changelog(self, tool_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取工具变更日志
        
        Requirements: 12.2
        """
        tool = self._tools.get(tool_name)
        if tool:
            return tool.get_changelog()
        return None
    
    def check_compatibility(
        self,
        tool_name: str,
        required_version: str
    ) -> Tuple[bool, str]:
        """
        检查版本兼容性
        
        Requirements: 12.5
        
        Returns:
            (是否兼容, 说明信息)
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return False, f"工具 {tool_name} 未注册"
        
        current_version = tool.get_version()
        is_compatible = tool.is_compatible_with_version(required_version)
        
        if is_compatible:
            return True, f"版本兼容: 当前 {current_version}, 要求 {required_version}"
        else:
            return False, f"版本不兼容: 当前 {current_version}, 要求 {required_version}"


# 全局版本注册表实例
_version_registry = MCPToolVersionRegistry()


def get_version_registry() -> MCPToolVersionRegistry:
    """获取全局版本注册表"""
    return _version_registry

