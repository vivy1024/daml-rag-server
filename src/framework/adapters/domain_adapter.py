# -*- coding: utf-8 -*-
"""
领域适配器抽象接口

定义DAML-RAG框架的领域适配器接口，支持将框架应用到不同垂直领域。

核心功能：
1. get_name() - 返回领域名称
2. get_layer3_rules() - 返回领域安全规则列表
3. get_dag_templates() - 返回领域DAG模板字典
4. get_tools() - 返回领域MCP工具列表

Requirements: 5.1-5.4

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# 数据类定义
# =============================================================================

class RuleSeverity(Enum):
    """规则严重程度"""
    ABSOLUTE = "absolute"      # 绝对禁忌，必须排除
    RELATIVE = "relative"      # 相对禁忌，降低优先级
    CAUTION = "caution"        # 注意事项，添加警告
    BOOST = "boost"            # 加分规则，提高优先级


class RuleCategory(Enum):
    """规则类别"""
    SAFETY = "safety"              # 安全规则
    KINETIC = "kinetic"            # 运动学规则
    RECOVERY = "recovery"          # 恢复规则
    DOMAIN = "domain"              # 领域专业约束
    CUSTOM = "custom"              # 自定义规则


@dataclass
class Layer3Rule:
    """
    Layer3规则定义
    
    用于定义领域特定的安全和业务规则
    
    Attributes:
        rule_id: 规则唯一标识
        name: 规则名称
        description: 规则描述
        category: 规则类别
        severity: 规则严重程度
        condition: 规则触发条件（Python表达式或函数名）
        action: 规则动作（filter/boost/warn）
        parameters: 规则参数
        enabled: 是否启用
    """
    rule_id: str
    name: str
    description: str
    category: RuleCategory
    severity: RuleSeverity
    condition: str  # 条件表达式或函数名
    action: str     # filter | boost | warn | modify
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "condition": self.condition,
            "action": self.action,
            "parameters": self.parameters,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Layer3Rule':
        """从字典创建"""
        return cls(
            rule_id=data["rule_id"],
            name=data["name"],
            description=data["description"],
            category=RuleCategory(data.get("category", "custom")),
            severity=RuleSeverity(data.get("severity", "relative")),
            condition=data["condition"],
            action=data["action"],
            parameters=data.get("parameters", {}),
            enabled=data.get("enabled", True)
        )


@dataclass
class DAGTemplateDefinition:
    """
    DAG模板定义
    
    用于定义领域特定的工作流模板
    
    Attributes:
        template_id: 模板唯一标识
        name: 模板名称
        description: 模板描述
        category: 模板类别
        applicable_intents: 适用意图列表
        required_tools: 必需工具列表
        optional_tools: 可选工具列表
        tool_dependencies: 工具依赖关系
        parallel_groups: 并行执行组
        expected_output: 预期输出
        safety_constraints: 安全约束
        estimated_duration_seconds: 预估执行时间
        complexity_level: 复杂度级别（1-3）
        response_hint: LLM响应提示
    """
    template_id: str
    name: str
    description: str
    category: str
    applicable_intents: List[str]
    required_tools: List[str]
    optional_tools: List[str] = field(default_factory=list)
    tool_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    parallel_groups: List[List[str]] = field(default_factory=list)
    expected_output: Dict[str, str] = field(default_factory=dict)
    safety_constraints: List[str] = field(default_factory=list)
    estimated_duration_seconds: float = 10.0
    complexity_level: int = 1
    response_hint: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "applicable_intents": self.applicable_intents,
            "required_tools": self.required_tools,
            "optional_tools": self.optional_tools,
            "tool_dependencies": self.tool_dependencies,
            "parallel_groups": self.parallel_groups,
            "expected_output": self.expected_output,
            "safety_constraints": self.safety_constraints,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "complexity_level": self.complexity_level,
            "response_hint": self.response_hint
        }
    
    def validate(self) -> bool:
        """验证模板完整性"""
        # 检查必需字段
        if not self.template_id or not self.name:
            logger.error(f"模板缺少必需字段: template_id或name")
            return False
        
        # 检查工具列表（greeting类模板允许为空）
        if not self.required_tools and "greeting" not in self.template_id:
            logger.warning(f"模板 {self.template_id} 没有必需工具")
        
        # 检查依赖关系中的工具是否在工具列表中
        all_tools = set(self.required_tools + self.optional_tools)
        for tool, deps in self.tool_dependencies.items():
            if tool not in all_tools:
                logger.error(f"模板 {self.template_id} 依赖关系中的工具 {tool} 不在工具列表中")
                return False
            for dep in deps:
                if dep not in all_tools:
                    logger.error(f"模板 {self.template_id} 工具 {tool} 的依赖 {dep} 不在工具列表中")
                    return False
        
        return True


@dataclass
class ToolDefinition:
    """
    MCP工具定义
    
    用于定义领域特定的MCP工具
    
    Attributes:
        name: 工具名称
        description: 工具描述
        category: 工具类别
        priority: 优先级（P0/P1/P2）
        input_schema: 输入Schema类
        output_schema: 输出Schema类
        implementation_class: 实现类
        requires_user_profile: 是否需要用户档案
        requires_three_layer: 是否需要三层检索
    """
    name: str
    description: str
    category: str
    priority: str = "P1"
    input_schema: Optional[Type] = None
    output_schema: Optional[Type] = None
    implementation_class: Optional[Type] = None
    requires_user_profile: bool = True
    requires_three_layer: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "requires_user_profile": self.requires_user_profile,
            "requires_three_layer": self.requires_three_layer
        }


@dataclass
class DomainConfig:
    """
    领域配置
    
    包含领域的所有配置信息
    """
    name: str
    display_name: str
    description: str
    version: str
    rules_count: int = 0
    templates_count: int = 0
    tools_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "rules_count": self.rules_count,
            "templates_count": self.templates_count,
            "tools_count": self.tools_count,
            "metadata": self.metadata
        }


# =============================================================================
# 领域适配器抽象基类
# =============================================================================

class DomainAdapter(ABC):
    """
    领域适配器抽象基类
    
    所有垂直领域的适配器必须继承此类并实现抽象方法。
    
    Requirements:
    - 5.1: get_name() 返回领域名称
    - 5.2: get_layer3_rules() 返回领域安全规则列表
    - 5.3: get_dag_templates() 返回领域DAG模板字典
    - 5.4: get_tools() 返回领域MCP工具列表
    
    使用示例:
    ```python
    class FitnessAdapter(DomainAdapter):
        def get_name(self) -> str:
            return "fitness"
        
        def get_layer3_rules(self) -> List[Layer3Rule]:
            return [
                Layer3Rule(
                    rule_id="joint_load_rule",
                    name="关节负荷规则",
                    ...
                )
            ]
        
        def get_dag_templates(self) -> Dict[str, DAGTemplateDefinition]:
            return {
                "complete_training_plan": DAGTemplateDefinition(...)
            }
        
        def get_tools(self) -> List[ToolDefinition]:
            return [
                ToolDefinition(
                    name="intelligent_exercise_selector",
                    ...
                )
            ]
    ```
    """
    
    def __init__(self):
        """初始化领域适配器"""
        self._initialized = False
        self._rules_cache: Optional[List[Layer3Rule]] = None
        self._templates_cache: Optional[Dict[str, DAGTemplateDefinition]] = None
        self._tools_cache: Optional[List[ToolDefinition]] = None
        
        logger.info(f"创建领域适配器: {self.__class__.__name__}")
    
    # =========================================================================
    # 抽象方法（子类必须实现）- Requirements 5.1-5.4
    # =========================================================================
    
    @abstractmethod
    def get_name(self) -> str:
        """
        返回领域名称
        
        Requirements: 5.1
        
        Returns:
            str: 领域名称（如 'fitness', 'medical', 'legal'）
        """
        pass
    
    @abstractmethod
    def get_display_name(self) -> str:
        """
        返回领域显示名称
        
        Returns:
            str: 领域显示名称（如 '健身', '医疗', '法律'）
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        返回领域描述
        
        Returns:
            str: 领域描述
        """
        pass
    
    @abstractmethod
    def get_layer3_rules(self) -> List[Layer3Rule]:
        """
        返回领域安全规则列表
        
        Requirements: 5.2
        
        Returns:
            List[Layer3Rule]: Layer3规则列表
        """
        pass
    
    @abstractmethod
    def get_dag_templates(self) -> Dict[str, DAGTemplateDefinition]:
        """
        返回领域DAG模板字典
        
        Requirements: 5.3
        
        Returns:
            Dict[str, DAGTemplateDefinition]: 模板ID -> 模板定义
        """
        pass
    
    @abstractmethod
    def get_tools(self) -> List[ToolDefinition]:
        """
        返回领域MCP工具列表
        
        Requirements: 5.4
        
        Returns:
            List[ToolDefinition]: 工具定义列表
        """
        pass
    
    @abstractmethod
    def get_fallback_recommendations(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        返回降级推荐数据
        
        当Layer1和Layer2都失败时，使用此数据进行规则匹配降级。
        
        Requirements: 6.1, 6.2 (框架层领域无关)
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: 关键词 -> 推荐项列表
            
        示例:
        ```python
        {
            "关键词1": [
                {"name": "项目1", "difficulty": "beginner", ...},
                {"name": "项目2", "difficulty": "intermediate", ...},
            ],
            "关键词2": [...],
        }
        ```
        """
        pass
    
    @abstractmethod
    def get_keyword_mapping(self) -> Dict[str, List[str]]:
        """
        返回关键词映射表
        
        用于从查询中提取领域相关关键词。
        
        Requirements: 6.1, 6.2 (框架层领域无关)
        
        Returns:
            Dict[str, List[str]]: 主关键词 -> 同义词列表
            
        示例:
        ```python
        {
            "主题1": ["同义词1", "同义词2", "英文名"],
            "主题2": ["同义词3", "同义词4"],
        }
        ```
        """
        pass
    
    @abstractmethod
    def get_safety_contraindications(self) -> Dict[str, List[str]]:
        """
        返回安全禁忌映射
        
        用于安全检查时过滤不适合的项目。
        
        Requirements: 6.1, 6.2 (框架层领域无关)
        
        Returns:
            Dict[str, List[str]]: 用户状况 -> 禁忌项目列表
            
        示例:
        ```python
        {
            "状况1": ["禁忌项1", "禁忌项2"],
            "状况2": ["禁忌项3", "禁忌项4"],
        }
        ```
        """
        pass
    
    @abstractmethod
    def get_joint_keywords(self) -> Dict[str, List[str]]:
        """
        返回关节/部位关键词映射
        
        用于关节损伤检查时匹配相关项目。
        
        Requirements: 6.1, 6.2 (框架层领域无关)
        
        Returns:
            Dict[str, List[str]]: 部位名称 -> 关键词列表
            
        示例:
        ```python
        {
            "部位1": ["关键词1", "关键词2"],
            "部位2": ["关键词3", "关键词4"],
        }
        ```
        """
        pass
    
    @abstractmethod
    def get_default_fallback_items(self) -> List[Dict[str, Any]]:
        """
        返回默认降级项目
        
        当没有匹配到任何关键词时返回的通用项目。
        
        Requirements: 6.1, 6.2 (框架层领域无关)
        
        Returns:
            List[Dict[str, Any]]: 默认项目列表
        """
        pass
    
    # =========================================================================
    # 可选方法（子类可覆盖）
    # =========================================================================
    
    def get_version(self) -> str:
        """
        返回适配器版本
        
        Returns:
            str: 版本号（如 '1.0.0'）
        """
        return "1.0.0"
    
    def get_config(self) -> DomainConfig:
        """
        返回领域配置
        
        Returns:
            DomainConfig: 领域配置对象
        """
        return DomainConfig(
            name=self.get_name(),
            display_name=self.get_display_name(),
            description=self.get_description(),
            version=self.get_version(),
            rules_count=len(self.get_layer3_rules()),
            templates_count=len(self.get_dag_templates()),
            tools_count=len(self.get_tools())
        )
    
    async def initialize(self) -> bool:
        """
        初始化适配器
        
        子类可覆盖此方法以执行初始化逻辑
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 验证规则
            rules = self.get_layer3_rules()
            logger.info(f"  加载 {len(rules)} 条Layer3规则")
            
            # 验证模板
            templates = self.get_dag_templates()
            valid_templates = 0
            for template_id, template in templates.items():
                if template.validate():
                    valid_templates += 1
                else:
                    logger.warning(f"  模板 {template_id} 验证失败")
            logger.info(f"  加载 {valid_templates}/{len(templates)} 个DAG模板")
            
            # 验证工具
            tools = self.get_tools()
            logger.info(f"  加载 {len(tools)} 个MCP工具")
            
            self._initialized = True
            logger.info(f"✅ 领域适配器 {self.get_name()} 初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 领域适配器 {self.get_name()} 初始化失败: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """检查适配器是否已初始化"""
        return self._initialized
    
    # =========================================================================
    # 便捷方法
    # =========================================================================
    
    def get_rule_by_id(self, rule_id: str) -> Optional[Layer3Rule]:
        """
        根据ID获取规则
        
        Args:
            rule_id: 规则ID
        
        Returns:
            Layer3Rule或None
        """
        for rule in self.get_layer3_rules():
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def get_enabled_rules(self) -> List[Layer3Rule]:
        """
        获取所有启用的规则
        
        Returns:
            List[Layer3Rule]: 启用的规则列表
        """
        return [rule for rule in self.get_layer3_rules() if rule.enabled]
    
    def get_rules_by_category(self, category: RuleCategory) -> List[Layer3Rule]:
        """
        根据类别获取规则
        
        Args:
            category: 规则类别
        
        Returns:
            List[Layer3Rule]: 该类别的规则列表
        """
        return [rule for rule in self.get_layer3_rules() if rule.category == category]
    
    def get_template_by_id(self, template_id: str) -> Optional[DAGTemplateDefinition]:
        """
        根据ID获取模板
        
        Args:
            template_id: 模板ID
        
        Returns:
            DAGTemplateDefinition或None
        """
        return self.get_dag_templates().get(template_id)
    
    def get_templates_by_category(self, category: str) -> List[DAGTemplateDefinition]:
        """
        根据类别获取模板
        
        Args:
            category: 模板类别
        
        Returns:
            List[DAGTemplateDefinition]: 该类别的模板列表
        """
        return [
            template for template in self.get_dag_templates().values()
            if template.category == category
        ]
    
    def match_template_by_intent(self, intent: str) -> Optional[DAGTemplateDefinition]:
        """
        根据意图匹配模板
        
        Args:
            intent: 用户意图
        
        Returns:
            DAGTemplateDefinition或None
        """
        intent_lower = intent.lower()
        for template in self.get_dag_templates().values():
            for applicable_intent in template.applicable_intents:
                if applicable_intent.lower() in intent_lower or intent_lower in applicable_intent.lower():
                    return template
        return None
    
    def get_tool_by_name(self, name: str) -> Optional[ToolDefinition]:
        """
        根据名称获取工具
        
        Args:
            name: 工具名称
        
        Returns:
            ToolDefinition或None
        """
        for tool in self.get_tools():
            if tool.name == name:
                return tool
        return None
    
    def get_tools_by_category(self, category: str) -> List[ToolDefinition]:
        """
        根据类别获取工具
        
        Args:
            category: 工具类别
        
        Returns:
            List[ToolDefinition]: 该类别的工具列表
        """
        return [tool for tool in self.get_tools() if tool.category == category]
    
    def get_tools_by_priority(self, priority: str) -> List[ToolDefinition]:
        """
        根据优先级获取工具
        
        Args:
            priority: 优先级（P0/P1/P2）
        
        Returns:
            List[ToolDefinition]: 该优先级的工具列表
        """
        return [tool for tool in self.get_tools() if tool.priority == priority]
    
    # =========================================================================
    # 健康检查
    # =========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict[str, Any]: 健康状态信息
        """
        return {
            "domain": self.get_name(),
            "display_name": self.get_display_name(),
            "version": self.get_version(),
            "initialized": self._initialized,
            "rules_count": len(self.get_layer3_rules()),
            "enabled_rules_count": len(self.get_enabled_rules()),
            "templates_count": len(self.get_dag_templates()),
            "tools_count": len(self.get_tools()),
            "status": "healthy" if self._initialized else "not_initialized"
        }


# =============================================================================
# 领域适配器注册表
# =============================================================================

class DomainAdapterRegistry:
    """
    领域适配器注册表
    
    管理所有已注册的领域适配器
    
    Requirements: 5.5
    """
    
    _instance = None
    _adapters: Dict[str, Type[DomainAdapter]] = {}
    _instances: Dict[str, DomainAdapter] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, adapter_class: Type[DomainAdapter]) -> None:
        """
        注册适配器类
        
        Args:
            adapter_class: 适配器类
        """
        # 创建临时实例获取名称
        temp_instance = adapter_class()
        domain_name = temp_instance.get_name()
        
        cls._adapters[domain_name] = adapter_class
        logger.info(f"注册领域适配器: {domain_name} -> {adapter_class.__name__}")
    
    @classmethod
    def get(cls, domain: str) -> Optional[Type[DomainAdapter]]:
        """
        获取适配器类（简写方法）
        
        Args:
            domain: 领域名称
        
        Returns:
            适配器类或None
        """
        return cls._adapters.get(domain)
    
    @classmethod
    def get_adapter_class(cls, domain: str) -> Optional[Type[DomainAdapter]]:
        """
        获取适配器类
        
        Args:
            domain: 领域名称
        
        Returns:
            适配器类或None
        """
        return cls._adapters.get(domain)
    
    @classmethod
    async def get_adapter(cls, domain: str) -> Optional[DomainAdapter]:
        """
        获取适配器实例（单例）
        
        Args:
            domain: 领域名称
        
        Returns:
            适配器实例或None
        """
        if domain not in cls._instances:
            adapter_class = cls.get_adapter_class(domain)
            if adapter_class:
                adapter = adapter_class()
                await adapter.initialize()
                cls._instances[domain] = adapter
                return adapter
            return None
        return cls._instances[domain]
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """
        列出所有已注册的适配器名称
        
        Returns:
            适配器名称列表
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def list_domains(cls) -> List[str]:
        """
        列出所有已注册的领域
        
        Returns:
            领域名称列表
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def get_all_adapters(cls) -> Dict[str, DomainAdapter]:
        """
        获取所有已实例化的适配器
        
        Returns:
            领域名称 -> 适配器实例
        """
        return cls._instances.copy()
    
    @classmethod
    def clear(cls) -> None:
        """清除所有注册（用于测试）"""
        cls._adapters.clear()
        cls._instances.clear()


# 全局注册表实例
_domain_registry = DomainAdapterRegistry()


def get_domain_registry() -> DomainAdapterRegistry:
    """获取全局领域注册表"""
    return _domain_registry


def register_domain_adapter(adapter_class: Type[DomainAdapter]) -> Type[DomainAdapter]:
    """
    装饰器：注册领域适配器
    
    使用示例:
    ```python
    @register_domain_adapter
    class FitnessAdapter(DomainAdapter):
        ...
    ```
    """
    _domain_registry.register(adapter_class)
    return adapter_class
