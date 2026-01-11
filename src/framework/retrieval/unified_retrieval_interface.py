# -*- coding: utf-8 -*-
"""
统一三层检索接口 - DAML-RAG框架整合核心

解决框架层内多个重复三层检索实现的问题：
1. true_three_layer_engine.py (933行) - 企业级三层检索
2. parallel_three_layer_engine.py (656行) - 并行化三层检索
3. applications/fitness/retrieval/fitness_three_layer.py (1003行) - 健身领域三层检索

设计原则：
1. 统一接口 - 单一入口，支持所有检索模式
2. 模式化 - 支持串行、并行、领域专用等执行模式
3. 可扩展 - 新的检索模式通过插件扩展
4. 向后兼容 - 现有代码平滑迁移

版本: v2.1.0
日期: 2025-12-03
作者: 薛小川 (框架层重构)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


# ============ 枚举定义 ============

class RetrievalMode(Enum):
    """检索执行模式"""
    SEQUENTIAL = "sequential"          # 串行执行 (Layer1 → Layer2 → Layer3)
    PARALLEL = "parallel"             # 并行执行 (Layer1+Layer2 → Layer3)
    DOMAIN_SPECIALIZED = "domain_specialized"  # 领域专用
    ADAPTIVE = "adaptive"             # 自适应选择

class ProcessingLevel(Enum):
    """处理层级"""
    BASIC = "basic"                   # 基础检索
    STANDARD = "standard"             # 标准检索
    ADVANCED = "advanced"             # 高级检索
    ENTERPRISE = "enterprise"         # 企业级检索


# ============ 数据类定义 ============

@dataclass
class RetrievalRequest:
    """统一的检索请求"""
    query: str
    domain: str = "general"  # ✅ 修改：默认值改为通用领域 (Requirements 6.2)
    user_id: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None

    # 检索配置
    mode: RetrievalMode = RetrievalMode.SEQUENTIAL
    level: ProcessingLevel = ProcessingLevel.STANDARD
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = None

    # 功能开关
    enable_caching: bool = False
    enable_safety_check: bool = True
    enable_personalization: bool = True

    # 性能配置
    timeout_seconds: float = 15.0
    enable_early_stopping: bool = False


@dataclass
class LayerResult:
    """单层检索结果"""
    layer_name: str
    success: bool
    results: List[Dict[str, Any]]
    execution_time_ms: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class RetrievalResult:
    """统一检索结果"""
    request: RetrievalRequest
    success: bool
    final_results: List[Dict[str, Any]]

    # 整体指标
    total_execution_time_ms: float
    total_confidence: float
    layers_executed: int

    # 层级结果
    layer_results: Dict[str, LayerResult] = field(default_factory=dict)

    # 元数据
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def final_recommendations(self) -> List[Dict[str, Any]]:
        """兼容性属性"""
        return self.final_results

    @property
    def answer(self) -> str:
        """兼容性属性"""
        return self.reasoning

    @property
    def sources(self) -> List[Dict[str, Any]]:
        """兼容性属性"""
        return self.final_results


# ============ 抽象接口定义 ============

class IRetrievalEngine(ABC):
    """检索引擎接口"""

    @abstractmethod
    async def execute(self, request: RetrievalRequest) -> RetrievalResult:
        """执行检索"""
        pass

    @abstractmethod
    def get_supported_modes(self) -> List[RetrievalMode]:
        """获取支持的执行模式"""
        pass

    @abstractmethod
    def get_supported_levels(self) -> List[ProcessingLevel]:
        """获取支持的处理层级"""
        pass


class IRetrievalStrategy(ABC):
    """检索策略接口"""

    @abstractmethod
    async def execute_retrieval(
        self,
        request: RetrievalRequest,
        **components
    ) -> RetrievalResult:
        """执行具体检索策略"""
        pass

    @abstractmethod
    def get_mode(self) -> RetrievalMode:
        """获取检索模式"""
        pass


# ============ 统一检索引擎 ============

class UnifiedRetrievalEngine(IRetrievalEngine):
    """
    统一检索引擎 - 框架层单一入口

    功能：
    1. 统一请求处理和路由
    2. 策略模式执行不同检索模式
    3. 结果标准化和兼容性处理
    4. 性能监控和错误处理
    """

    def __init__(self):
        self.strategies: Dict[RetrievalMode, IRetrievalStrategy] = {}
        self.components = {}
        self.logger = logging.getLogger(__name__)

        # 性能统计
        self.stats = {
            "total_requests": 0,
            "mode_usage": {mode.value: 0 for mode in RetrievalMode},
            "avg_execution_time": 0.0,
            "success_rate": 0.0
        }

    def register_strategy(
        self,
        strategy: IRetrievalStrategy,
        override: bool = False
    ):
        """注册检索策略"""
        mode = strategy.get_mode()

        if mode in self.strategies and not override:
            raise ValueError(f"策略 {mode.value} 已存在，使用 override=True 覆盖")

        self.strategies[mode] = strategy
        self.logger.info(f"✓ 注册检索策略: {mode.value}")

    def register_component(self, name: str, component: Any):
        """注册检索组件"""
        self.components[name] = component
        self.logger.info(f"✓ 注册检索组件: {name}")

    async def execute(self, request: RetrievalRequest) -> RetrievalResult:
        """执行检索请求"""
        start_time = datetime.now()
        self.stats["total_requests"] += 1

        logger.info(f"🚀 统一检索开始: {request.mode.value}/{request.level.value}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"查询: {request.query}")

        try:
            # 1. 选择策略
            strategy = self._select_strategy(request)
            if not strategy:
                raise ValueError(f"不支持的检索模式: {request.mode}")

            # 2. 预处理请求
            processed_request = await self._preprocess_request(request)

            # 3. 执行检索
            result = await strategy.execute_retrieval(
                processed_request,
                **self.components
            )

            # 4. 后处理结果
            final_result = await self._postprocess_result(result, processed_request)

            # 5. 更新统计
            self._update_stats(final_result, start_time)

            self.logger.info(
                f"✅ 统一检索完成: {len(final_result.final_results)}个结果, "
                f"耗时{final_result.total_execution_time_ms:.0f}ms"
            )

            return final_result

        except Exception as e:
            self.logger.error(f"❌ 统一检索失败: {e}", exc_info=True)

            # 返回错误结果
            return RetrievalResult(
                request=request,
                success=False,
                final_results=[],
                total_execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                total_confidence=0.0,
                layers_executed=0,
                reasoning=f"检索失败: {str(e)}",
                metadata={"error": str(e)}
            )

    def _select_strategy(self, request: RetrievalRequest) -> Optional[IRetrievalStrategy]:
        """选择检索策略"""
        # 直接匹配
        if request.mode in self.strategies:
            return self.strategies[request.mode]

        # 自适应选择
        if request.mode == RetrievalMode.ADAPTIVE:
            return self._select_adaptive_strategy(request)

        return None

    def _select_adaptive_strategy(self, request: RetrievalRequest) -> Optional[IRetrievalStrategy]:
        """自适应策略选择"""
        # 简化规则：根据处理层级选择
        if request.level in [ProcessingLevel.ENTERPRISE, ProcessingLevel.ADVANCED]:
            return self.strategies.get(RetrievalMode.PARALLEL)
        else:
            return self.strategies.get(RetrievalMode.SEQUENTIAL)

    async def _preprocess_request(self, request: RetrievalRequest) -> RetrievalRequest:
        """预处理请求"""
        # 设置默认的context字段
        if request.context is None:
            request.context = {}

        request.context.setdefault("user_profile", request.user_profile)
        request.context.setdefault("filters", request.filters)
        request.context.setdefault("top_k", request.top_k)
        request.context.setdefault("safety_check", request.enable_safety_check)

        return request

    async def _postprocess_result(
        self,
        result: RetrievalResult,
        request: RetrievalRequest
    ) -> RetrievalResult:
        """后处理结果"""
        # 添加统一元数据
        result.metadata.update({
            "engine": "UnifiedRetrievalEngine",
            "request_mode": request.mode.value,
            "request_level": request.level.value,
            "timestamp": datetime.now().isoformat()
        })

        return result

    def _update_stats(self, result: RetrievalResult, start_time: datetime):
        """更新性能统计"""
        execution_time = result.total_execution_time_ms

        # 更新模式使用统计
        mode = result.request.mode.value
        self.stats["mode_usage"][mode] += 1

        # 更新平均执行时间
        total_requests = self.stats["total_requests"]
        current_avg = self.stats["avg_execution_time"]
        self.stats["avg_execution_time"] = (
            (current_avg * (total_requests - 1) + execution_time) / total_requests
        )

        # 更新成功率
        success_count = self.stats.get("success_count", 0)
        if result.success:
            success_count += 1
        self.stats["success_count"] = success_count
        self.stats["success_rate"] = (success_count / total_requests) * 100

    def get_supported_modes(self) -> List[RetrievalMode]:
        """获取支持的执行模式"""
        return list(self.strategies.keys())

    def get_supported_levels(self) -> List[ProcessingLevel]:
        """获取支持的处理层级"""
        return list(ProcessingLevel)

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.stats.copy()


# ============ 检索策略实现 ============

class SequentialStrategy(IRetrievalStrategy):
    """串行检索策略 - Layer1 → Layer2 → Layer3"""

    def __init__(self, base_engine):
        self.base_engine = base_engine

    async def execute_retrieval(
        self,
        request: RetrievalRequest,
        **components
    ) -> RetrievalResult:
        """执行串行检索"""
        start_time = datetime.now()

        # 使用基础引擎执行
        if hasattr(self.base_engine, 'execute_three_layer_query'):
            three_layer_result = await self.base_engine.execute_three_layer_query(
                query=request.query,
                domain=request.domain,
                user_id=request.user_id,
                user_profile=request.user_profile,
                filters=request.filters,
                top_k=request.top_k,
                safety_check=request.enable_safety_check
            )

            # 转换为统一格式
            return self._convert_to_unified_result(
                three_layer_result, request, start_time
            )

        else:
            raise ValueError("base_engine 不支持三层检索")

    def get_mode(self) -> RetrievalMode:
        return RetrievalMode.SEQUENTIAL

    def _convert_to_unified_result(
        self,
        three_layer_result: Any,
        request: RetrievalRequest,
        start_time: datetime
    ) -> RetrievalResult:
        """转换为基础引擎结果为统一格式"""
        # 假设基础引擎返回ThreeLayerResult格式
        return RetrievalResult(
            request=request,
            success=three_layer_result.final_results is not None,
            final_results=three_layer_result.final_results or [],
            layer_results={
                "Layer1": three_layer_result.layer_1_result,
                "Layer2": three_layer_result.layer_2_result,
                "Layer3": three_layer_result.layer_3_result
            },
            total_execution_time_ms=three_layer_result.total_execution_time_ms,
            total_confidence=three_layer_result.total_confidence,
            layers_executed=3,
            reasoning=three_layer_result.reasoning,
            metadata=three_layer_result.metadata or {}
        )


class ParallelStrategy(IRetrievalStrategy):
    """并行检索策略 - Layer1+Layer2 → Layer3"""

    def __init__(self, parallel_engine):
        self.parallel_engine = parallel_engine

    async def execute_retrieval(
        self,
        request: RetrievalRequest,
        **components
    ) -> RetrievalResult:
        """执行并行检索"""
        start_time = datetime.now()

        # 使用并行引擎执行
        if hasattr(self.parallel_engine, 'execute_parallel_three_layer_search'):
            parallel_result = await self.parallel_engine.execute_parallel_three_layer_search(
                query=request.query,
                domain=request.domain,
                user_id=request.user_id,
                user_profile=request.user_profile,
                filters=request.filters,
                top_k=request.top_k,
                safety_check=request.enable_safety_check
            )

            # 转换为统一格式
            return self._convert_to_unified_result(
                parallel_result, request, start_time
            )

        else:
            raise ValueError("parallel_engine 不支持并行三层检索")

    def get_mode(self) -> RetrievalMode:
        return RetrievalMode.PARALLEL

    def _convert_to_unified_result(
        self,
        parallel_result: Any,
        request: RetrievalRequest,
        start_time: datetime
    ) -> RetrievalResult:
        """转换并行引擎结果为统一格式"""
        return RetrievalResult(
            request=request,
            success=parallel_result.final_results is not None,
            final_results=parallel_result.final_results or [],
            layer_results={
                "Layer1": parallel_result.layer_1_result,
                "Layer2": parallel_result.layer_2_result,
                "Layer3": parallel_result.layer_3_result
            },
            total_execution_time_ms=parallel_result.total_execution_time_ms,
            total_confidence=parallel_result.total_confidence,
            layers_executed=3,
            reasoning=parallel_result.reasoning,
            metadata=parallel_result.metadata or {}
        )


class DomainSpecializedStrategy(IRetrievalStrategy):
    """领域专用检索策略"""

    def __init__(self, domain_engines: Dict[str, Any]):
        self.domain_engines = domain_engines

    async def execute_retrieval(
        self,
        request: RetrievalRequest,
        **components
    ) -> RetrievalResult:
        """执行领域专用检索"""
        start_time = datetime.now()

        # 选择领域引擎
        domain_engine = self.domain_engines.get(request.domain)
        if not domain_engine:
            raise ValueError(f"不支持的领域: {request.domain}")

        # 使用领域引擎执行
        if hasattr(domain_engine, 'fitness_search'):  # 健身领域
            fitness_user_profile = self._create_fitness_user_profile(request.user_profile)

            domain_result = await domain_engine.fitness_search(
                query=request.query,
                user_profile=fitness_user_profile,
                top_k=request.top_k
            )

            # 转换为统一格式
            return self._convert_domain_result_to_unified(
                domain_result, request, start_time
            )

        else:
            raise ValueError(f"领域引擎 {request.domain} 不支持专用检索")

    def get_mode(self) -> RetrievalMode:
        return RetrievalMode.DOMAIN_SPECIALIZED

    def _create_fitness_user_profile(self, user_profile: Optional[Dict]):
        """创建健身用户档案"""
        if not user_profile:
            return None

        # 这里应该转换为FitnessUserProfile对象
        # 简化实现
        return type('FitnessUserProfile', (), user_profile)()

    def _convert_domain_result_to_unified(
        self,
        domain_result: Any,
        request: RetrievalRequest,
        start_time: datetime
    ) -> RetrievalResult:
        """转换领域结果为统一格式"""
        return RetrievalResult(
            request=request,
            success=True,
            final_results=domain_result.get('combined_documents', []),
            total_execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            total_confidence=0.8,
            layers_executed=3,
            reasoning=domain_result.get('reasoning', ''),
            metadata={"domain_specialized": True, **domain_result}
        )


# ============ 兼容性适配器 ============

class FrameworkCompatibilityAdapter:
    """
    框架层兼容性适配器

    提供与现有代码的兼容性：
    1. query() 函数兼容
    2. get_graphrag_tool() 兼容
    3. 旧接口平滑迁移
    """

    def __init__(self, unified_engine: UnifiedRetrievalEngine):
        self.unified_engine = unified_engine
        self.logger = logging.getLogger(__name__)

    async def query(
        self,
        query: str,
        domain: str = "general",
        user_id: str = None,
        context: Dict[str, Any] = None
    ):
        """兼容framework层的query接口"""
        request = RetrievalRequest(
            query=query,
            domain=domain,
            user_id=user_id,
            context=context or {},
            mode=RetrievalMode.ADAPTIVE,  # 自适应选择
            level=ProcessingLevel.STANDARD
        )

        result = await self.unified_engine.execute(request)

        # 转换为FrameworkResponse格式
        return self._to_framework_response(result)

    def _to_framework_response(self, result: RetrievalResult):
        """转换为FrameworkResponse格式"""
        from .. import FrameworkResponse

        return FrameworkResponse(
            query=result.request.query,
            results={
                "final_recommendations": result.final_results,
                "three_layer_result": result.metadata
            },
            metadata=result.metadata,
            answer=result.reasoning,
            sources=result.final_results,
            confidence=result.total_confidence,
            retrieval_summary=result.metadata,
            anti_hallucination_result=result.metadata.get("anti_hallucination_result"),
            standardization_result=result.metadata.get("standardization_result")
        )


# ============ 工厂函数 ============

async def create_unified_engine(
    enable_sequential: bool = True,
    enable_parallel: bool = True,
    enable_domain_specialized: bool = True,
    **engine_configs
) -> UnifiedRetrievalEngine:
    """
    创建统一检索引擎

    Args:
        enable_sequential: 启用串行检索
        enable_parallel: 启用并行检索
        enable_domain_specialized: 启用领域专用检索
        **engine_configs: 各引擎的配置参数

    Returns:
        统一检索引擎实例
    """
    engine = UnifiedRetrievalEngine()

    # 注册串行策略
    if enable_sequential:
        from .true_three_layer_engine import TrueThreeLayerEngine
        sequential_engine = TrueThreeLayerEngine(**engine_configs.get("sequential", {}))
        sequential_strategy = SequentialStrategy(sequential_engine)
        engine.register_strategy(sequential_strategy)
        engine.register_component("sequential_engine", sequential_engine)
        logger.info("✓ 串行检索策略已注册")

    # 注：根据v2.3.1架构优化，并行检索已被简化，统一使用GraphRAG接口
    # 不再注册复杂的并行检索策略，保持架构简洁

    # 注：根据v2.3.1重构，领域专用策略已被简化，统一使用GraphRAG接口
    # applications目录已在重构清理中删除，保持架构简洁

    logger.info(f"✅ 统一检索引擎创建完成 - 支持{len(engine.strategies)}种模式")

    return engine


# ============ 全局实例 ============

# 全局统一引擎实例
_unified_engine: Optional[UnifiedRetrievalEngine] = None
_compatibility_adapter: Optional[FrameworkCompatibilityAdapter] = None

async def get_unified_engine() -> UnifiedRetrievalEngine:
    """获取全局统一引擎实例"""
    global _unified_engine
    if _unified_engine is None:
        # 根据v2.3.1架构优化，只启用串行策略，保持简洁
        _unified_engine = await create_unified_engine(
            enable_sequential=True,
            enable_parallel=False,  # 已删除冗余实现
            enable_domain_specialized=False  # applications目录已清理
        )
    return _unified_engine

async def get_compatibility_adapter() -> FrameworkCompatibilityAdapter:
    """获取兼容性适配器实例"""
    global _compatibility_adapter
    if _compatibility_adapter is None:
        unified_engine = await get_unified_engine()
        _compatibility_adapter = FrameworkCompatibilityAdapter(unified_engine)
    return _compatibility_adapter


# ============ 导出 ============

__all__ = [
    # 核心类
    "UnifiedRetrievalEngine",
    "RetrievalRequest",
    "RetrievalResult",
    "LayerResult",

    # 枚举
    "RetrievalMode",
    "ProcessingLevel",

    # 接口
    "IRetrievalEngine",
    "IRetrievalStrategy",

    # 策略
    "SequentialStrategy",
    "ParallelStrategy",
    "DomainSpecializedStrategy",

    # 兼容性
    "FrameworkCompatibilityAdapter",

    # 工厂函数
    "create_unified_engine",
    "get_unified_engine",
    "get_compatibility_adapter"
]