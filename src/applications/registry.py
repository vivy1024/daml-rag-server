"""
DAML-RAG组件注册系统

基于装饰器模式的组件发现和加载机制。
学习LangChain等主流框架的设计模式，支持：
- 组件自动注册
- 依赖注入
- 插件化扩展
- 版本管理

这是DAML-RAG框架生态系统的核心基础设施。

作者: BUILD_BODY Team
版本: v2.0.0
"""

import logging
import inspect
from typing import Dict, List, Any, Optional, Callable, Type, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """组件类型"""
    RETRIEVAL = "retrieval"           # 检索组件
    PROCESSOR = "processor"           # 处理组件
    EVALUATOR = "evaluator"           # 评估组件
    GENERATOR = "generator"           # 生成组件
    VALIDATOR = "validator"           # 验证组件
    WORKFLOW = "workflow"             # 工作流组件
    MODEL = "model"                   # 模型组件
    ADAPTER = "adapter"               # 适配器组件
    SERVICE = "service"               # 服务组件


class ComponentStatus(Enum):
    """组件状态"""
    REGISTERED = "registered"         # 已注册
    ACTIVE = "active"                 # 激活
    INACTIVE = "inactive"             # 未激活
    ERROR = "error"                   # 错误
    DEPRECATED = "deprecated"         # 已弃用


@dataclass
class ComponentInfo:
    """组件信息"""
    name: str
    component_type: ComponentType
    cls: Type
    version: str
    description: str
    author: str
    tags: List[str]
    dependencies: List[str]
    status: ComponentStatus
    registered_at: datetime
    config: Dict[str, Any]
    instance: Optional[Any] = None

    @property
    def full_name(self) -> str:
        """完整名称"""
        return f"{self.component_type.value}.{self.name}"


class ComponentRegistry:
    """
    组件注册系统

    学习LangChain的组件管理理念，提供：
    - 装饰器注册机制
    - 组件生命周期管理
    - 依赖注入系统
    - 版本兼容性检查
    """

    def __init__(self):
        """初始化组件注册系统"""
        self.logger = logging.getLogger(__name__)
        self.components: Dict[str, ComponentInfo] = {}
        self.type_index: Dict[ComponentType, List[str]] = {
            comp_type: [] for comp_type in ComponentType
        }
        self.tag_index: Dict[str, List[str]] = {}
        self.active_instances: Dict[str, Any] = {}

    def register(
        self,
        name: str,
        component_type: ComponentType,
        version: str = "1.0.0",
        description: str = "",
        author: str = "",
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Callable:
        """
        组件注册装饰器

        使用方式：
        @component_registry.register("fitness_retriever", ComponentType.RETRIEVAL)
        class FitnessRetriever:
            pass

        Args:
            name: 组件名称
            component_type: 组件类型
            version: 组件版本
            description: 组件描述
            author: 作者
            tags: 标签
            dependencies: 依赖组件
            config: 配置参数
        """
        def decorator(cls: Type) -> Type:
            # 创建组件信息
            component_info = ComponentInfo(
                name=name,
                component_type=component_type,
                cls=cls,
                version=version,
                description=description or cls.__doc__ or "",
                author=author or "Unknown",
                tags=tags or [],
                dependencies=dependencies or [],
                status=ComponentStatus.REGISTERED,
                registered_at=datetime.now(),
                config=config or {}
            )

            # 检查依赖
            self._validate_dependencies(component_info)

            # 注册组件
            full_name = component_info.full_name
            self.components[full_name] = component_info
            self.type_index[component_type].append(full_name)

            # 建立标签索引
            for tag in component_info.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = []
                self.tag_index[tag].append(full_name)

            self.logger.info(f"组件已注册: {full_name} v{version}")
            return cls

        return decorator

    def _validate_dependencies(self, component_info: ComponentInfo):
        """验证组件依赖"""
        for dependency in component_info.dependencies:
            if dependency not in self.components:
                self.logger.warning(f"组件 {component_info.full_name} 依赖的组件 {dependency} 未注册")

    def get_component(self, name: str, component_type: Optional[ComponentType] = None) -> Optional[ComponentInfo]:
        """获取组件信息"""
        if component_type:
            full_name = f"{component_type.value}.{name}"
        else:
            full_name = name

        return self.components.get(full_name)

    def get_components_by_type(self, component_type: ComponentType) -> List[ComponentInfo]:
        """按类型获取组件"""
        component_names = self.type_index.get(component_type, [])
        return [self.components[name] for name in component_names if name in self.components]

    def get_components_by_tag(self, tag: str) -> List[ComponentInfo]:
        """按标签获取组件"""
        component_names = self.tag_index.get(tag, [])
        return [self.components[name] for name in component_names if name in self.components]

    def search_components(self, query: str) -> List[ComponentInfo]:
        """搜索组件"""
        query_lower = query.lower()
        results = []

        for component_info in self.components.values():
            # 搜索名称
            if query_lower in component_info.name.lower():
                results.append(component_info)
                continue

            # 搜索描述
            if query_lower in component_info.description.lower():
                results.append(component_info)
                continue

            # 搜索标签
            if any(query_lower in tag.lower() for tag in component_info.tags):
                results.append(component_info)
                continue

        return results

    async def create_instance(
        self,
        name: str,
        component_type: Optional[ComponentType] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        创建组件实例

        Args:
            name: 组件名称
            component_type: 组件类型
            config: 配置参数
            **kwargs: 其他参数

        Returns:
            组件实例
        """
        component_info = self.get_component(name, component_type)
        if not component_info:
            raise ValueError(f"组件未找到: {name}")

        # 合并配置
        final_config = {**component_info.config, **(config or {}), **kwargs}

        try:
            # 创建实例
            instance = component_info.cls(**final_config)

            # 更新组件信息
            component_info.instance = instance
            component_info.status = ComponentStatus.ACTIVE

            # 缓存活跃实例
            self.active_instances[component_info.full_name] = instance

            self.logger.info(f"组件实例已创建: {component_info.full_name}")
            return instance

        except Exception as e:
            component_info.status = ComponentStatus.ERROR
            self.logger.error(f"创建组件实例失败: {component_info.full_name}, 错误: {str(e)}")
            raise

    async def get_instance(
        self,
        name: str,
        component_type: Optional[ComponentType] = None,
        create_if_missing: bool = True,
        **kwargs
    ) -> Any:
        """
        获取组件实例

        Args:
            name: 组件名称
            component_type: 组件类型
            create_if_missing: 如果实例不存在是否创建
            **kwargs: 创建参数

        Returns:
            组件实例
        """
        full_name = f"{component_type.value}.{name}" if component_type else name

        # 检查缓存
        if full_name in self.active_instances:
            return self.active_instances[full_name]

        # 创建新实例
        if create_if_missing:
            return await self.create_instance(name, component_type, **kwargs)

        return None

    def list_components(
        self,
        component_type: Optional[ComponentType] = None,
        status: Optional[ComponentStatus] = None,
        tag: Optional[str] = None
    ) -> List[ComponentInfo]:
        """
        列出组件

        Args:
            component_type: 按类型过滤
            status: 按状态过滤
            tag: 按标签过滤

        Returns:
            组件列表
        """
        components = list(self.components.values())

        if component_type:
            components = [c for c in components if c.component_type == component_type]

        if status:
            components = [c for c in components if c.status == status]

        if tag:
            components = [c for c in components if tag in c.tags]

        return components

    def get_registry_stats(self) -> Dict[str, Any]:
        """获取注册系统统计"""
        type_counts = {
            comp_type.value: len(self.type_index.get(comp_type, []))
            for comp_type in ComponentType
        }

        status_counts = {}
        for component in self.components.values():
            status = component.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_components": len(self.components),
            "active_instances": len(self.active_instances),
            "type_distribution": type_counts,
            "status_distribution": status_counts,
            "total_tags": len(self.tag_index)
        }

    def unregister(self, name: str, component_type: Optional[ComponentType] = None):
        """取消注册组件"""
        full_name = f"{component_type.value}.{name}" if component_type else name

        if full_name not in self.components:
            raise ValueError(f"组件未找到: {full_name}")

        component_info = self.components[full_name]

        # 清理实例
        if full_name in self.active_instances:
            instance = self.active_instances[full_name]
            if hasattr(instance, 'cleanup'):
                try:
                    if inspect.iscoroutinefunction(instance.cleanup):
                        import asyncio
                        asyncio.create_task(instance.cleanup())
                    else:
                        instance.cleanup()
                except Exception as e:
                    self.logger.warning(f"组件清理失败: {full_name}, 错误: {str(e)}")

            del self.active_instances[full_name]

        # 从索引中移除
        self.type_index[component_info.component_type].remove(full_name)
        for tag in component_info.tags:
            if tag in self.tag_index and full_name in self.tag_index[tag]:
                self.tag_index[tag].remove(full_name)

        # 删除组件
        del self.components[full_name]

        self.logger.info(f"组件已取消注册: {full_name}")

    def update_component_status(self, name: str, status: ComponentStatus, component_type: Optional[ComponentType] = None):
        """更新组件状态"""
        component_info = self.get_component(name, component_type)
        if component_info:
            component_info.status = status
            self.logger.info(f"组件状态已更新: {component_info.full_name} -> {status.value}")


# 全局组件注册实例
component_registry = ComponentRegistry()


# 便捷装饰器
def retriever(name: str, **kwargs):
    """检索组件注册装饰器"""
    return component_registry.register(name, ComponentType.RETRIEVAL, **kwargs)


def processor(name: str, **kwargs):
    """处理组件注册装饰器"""
    return component_registry.register(name, ComponentType.PROCESSOR, **kwargs)


def evaluator(name: str, **kwargs):
    """评估组件注册装饰器"""
    return component_registry.register(name, ComponentType.EVALUATOR, **kwargs)


def workflow(name: str, **kwargs):
    """工作流组件注册装饰器"""
    return component_registry.register(name, ComponentType.WORKFLOW, **kwargs)


def model(name: str, **kwargs):
    """模型组件注册装饰器"""
    return component_registry.register(name, ComponentType.MODEL, **kwargs)


def service(name: str, **kwargs):
    """服务组件注册装饰器"""
    return component_registry.register(name, ComponentType.SERVICE, **kwargs)


def adapter(name: str, **kwargs):
    """适配器组件注册装饰器"""
    return component_registry.register(name, ComponentType.ADAPTER, **kwargs)