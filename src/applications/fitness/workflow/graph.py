# -*- coding: utf-8 -*-
"""
工作流图构建模块

组装 StateGraph，参考 LangGraph 的 StateGraph API。
定义节点、边和条件边，构建完整的工作流图。

版本: v1.0.0
日期: 2025-12-28

主要类:
- WorkflowGraph: 工作流图（参考 LangGraph StateGraph）
"""

import logging
from typing import Dict, Any, Callable, Optional, Tuple, List
from dataclasses import dataclass, field

from .state import WorkflowState, WorkflowStep
from .nodes import (
    node_preload_user_profile,
    node_store_session,
    node_check_membership,
    node_classify_complexity,
    node_select_model,
    node_retrieve_few_shot,
    node_select_dag_template,
    node_execute_dag,
    node_retrieve_context,
    node_aggregate_data,
    node_llm_analysis,
    node_log_interaction,
)
from .edges import (
    route_after_complexity,
    route_after_dag,
    route_on_error,
    should_continue,
    get_next_step,
)

logger = logging.getLogger(__name__)


@dataclass
class NodeConfig:
    """节点配置"""
    name: str
    func: Callable
    step_number: int
    description: str = ""
    is_parallel: bool = False  # 是否可以并行执行
    parallel_group: Optional[str] = None  # 并行组名称


@dataclass
class EdgeConfig:
    """边配置"""
    from_node: str
    to_node: str
    is_conditional: bool = False
    condition_func: Optional[Callable] = None
    condition_mapping: Dict[str, str] = field(default_factory=dict)


class WorkflowGraph:
    """
    工作流图（参考 LangGraph StateGraph）
    
    管理节点、边和条件边，提供图的构建和遍历功能。
    """
    
    # 特殊节点名称
    START = "START"
    END = "END"
    
    def __init__(self):
        """初始化工作流图"""
        self.nodes: Dict[str, NodeConfig] = {}
        self.edges: Dict[str, str] = {}  # from_node -> to_node
        self.conditional_edges: Dict[str, Tuple[Callable, Dict[str, str]]] = {}
        self.parallel_groups: Dict[str, List[str]] = {}  # group_name -> [node_names]
        
        # 构建默认图
        self._build_default_graph()
    
    def _build_default_graph(self):
        """构建默认的11步工作流图"""
        # ========== 添加节点 ==========
        
        # 步骤1-2：可并行执行
        self.add_node(
            "preload_user_profile",
            node_preload_user_profile,
            step_number=1,
            description="预加载用户档案",
            is_parallel=True,
            parallel_group="init"
        )
        self.add_node(
            "store_session",
            node_store_session,
            step_number=2,
            description="会话记录存储",
            is_parallel=True,
            parallel_group="init"
        )
        
        # 步骤3-4：可并行执行
        self.add_node(
            "check_membership",
            node_check_membership,
            step_number=3,
            description="检查会员权限",
            is_parallel=True,
            parallel_group="context"
        )
        self.add_node(
            "classify_complexity",
            node_classify_complexity,
            step_number=4,
            description="BGE复杂度分类",
            is_parallel=True,
            parallel_group="context"
        )
        
        # 步骤5：智能模型选择
        self.add_node(
            "select_model",
            node_select_model,
            step_number=5,
            description="智能模型选择"
        )
        
        # 步骤6：Few-Shot检索
        self.add_node(
            "retrieve_few_shot",
            node_retrieve_few_shot,
            step_number=6,
            description="Few-Shot检索"
        )
        
        # 步骤6.5：LLM选择DAG模板
        self.add_node(
            "select_dag_template",
            node_select_dag_template,
            step_number=7,  # 内部编号为7
            description="LLM选择DAG模板"
        )
        
        # 步骤7：DAG编排执行
        self.add_node(
            "execute_dag",
            node_execute_dag,
            step_number=8,  # 内部编号为8
            description="DAG编排执行"
        )
        
        # 步骤8：三层检索
        self.add_node(
            "retrieve_context",
            node_retrieve_context,
            step_number=9,  # 内部编号为9
            description="三层检索"
        )
        
        # 步骤9：工具结果汇总
        self.add_node(
            "aggregate_data",
            node_aggregate_data,
            step_number=10,  # 内部编号为10
            description="工具结果汇总"
        )
        
        # 步骤10：LLM生成回答
        self.add_node(
            "llm_analysis",
            node_llm_analysis,
            step_number=11,  # 内部编号为11
            description="LLM生成回答"
        )
        
        # 步骤11：记录交互
        self.add_node(
            "log_interaction",
            node_log_interaction,
            step_number=12,  # 内部编号为12
            description="记录交互"
        )
        
        # ========== 添加边 ==========
        
        # 起始边
        self.add_edge(self.START, "preload_user_profile")
        
        # 步骤1-2 -> 步骤3-4（并行组之间的边）
        self.add_edge("preload_user_profile", "check_membership")
        self.add_edge("store_session", "check_membership")
        
        # 步骤3-4 -> 步骤5
        self.add_edge("check_membership", "select_model")
        self.add_edge("classify_complexity", "select_model")
        
        # 步骤5 -> 步骤6
        self.add_edge("select_model", "retrieve_few_shot")
        
        # 步骤6 -> 步骤6.5
        self.add_edge("retrieve_few_shot", "select_dag_template")
        
        # 步骤6.5 -> 步骤7
        self.add_edge("select_dag_template", "execute_dag")
        
        # 步骤7 -> 步骤8（条件边）
        self.add_conditional_edge(
            "execute_dag",
            route_after_dag,
            {
                "aggregate_data": "aggregate_data",
                "fallback_search": "retrieve_context",
                "llm_analysis": "llm_analysis"
            }
        )
        
        # 步骤8 -> 步骤9
        self.add_edge("retrieve_context", "aggregate_data")
        
        # 步骤9 -> 步骤10
        self.add_edge("aggregate_data", "llm_analysis")
        
        # 步骤10 -> 步骤11
        self.add_edge("llm_analysis", "log_interaction")
        
        # 步骤11 -> 结束
        self.add_edge("log_interaction", self.END)
        
        logger.info(f"✅ 工作流图构建完成: {len(self.nodes)}个节点, {len(self.edges)}条边, {len(self.conditional_edges)}条条件边")
    
    def add_node(
        self,
        name: str,
        func: Callable,
        step_number: int,
        description: str = "",
        is_parallel: bool = False,
        parallel_group: Optional[str] = None
    ):
        """
        添加节点
        
        Args:
            name: 节点名称
            func: 节点函数
            step_number: 步骤编号
            description: 节点描述
            is_parallel: 是否可以并行执行
            parallel_group: 并行组名称
        """
        self.nodes[name] = NodeConfig(
            name=name,
            func=func,
            step_number=step_number,
            description=description,
            is_parallel=is_parallel,
            parallel_group=parallel_group
        )
        
        # 添加到并行组
        if parallel_group:
            if parallel_group not in self.parallel_groups:
                self.parallel_groups[parallel_group] = []
            self.parallel_groups[parallel_group].append(name)
    
    def add_edge(self, from_node: str, to_node: str):
        """
        添加普通边
        
        Args:
            from_node: 起始节点
            to_node: 目标节点
        """
        self.edges[from_node] = to_node
    
    def add_conditional_edge(
        self,
        from_node: str,
        condition: Callable,
        mapping: Dict[str, str]
    ):
        """
        添加条件边
        
        Args:
            from_node: 起始节点
            condition: 条件函数，接收状态返回路由键
            mapping: 路由键到目标节点的映射
        """
        self.conditional_edges[from_node] = (condition, mapping)
    
    def get_node(self, name: str) -> Optional[NodeConfig]:
        """获取节点配置"""
        return self.nodes.get(name)
    
    def get_node_func(self, name: str) -> Optional[Callable]:
        """获取节点函数"""
        node = self.nodes.get(name)
        return node.func if node else None
    
    def get_next_node(self, current: str, state: WorkflowState) -> str:
        """
        获取下一个节点
        
        Args:
            current: 当前节点名称
            state: 当前工作流状态
            
        Returns:
            下一个节点名称
        """
        # 检查条件边
        if current in self.conditional_edges:
            condition, mapping = self.conditional_edges[current]
            result = condition(state)
            next_node = mapping.get(result, self.END)
            logger.debug(f"条件路由: {current} -> {result} -> {next_node}")
            return next_node
        
        # 检查普通边
        next_node = self.edges.get(current, self.END)
        logger.debug(f"普通路由: {current} -> {next_node}")
        return next_node
    
    def get_parallel_group(self, group_name: str) -> List[str]:
        """获取并行组中的节点列表"""
        return self.parallel_groups.get(group_name, [])
    
    def get_all_nodes(self) -> List[str]:
        """获取所有节点名称"""
        return list(self.nodes.keys())
    
    def get_node_order(self) -> List[str]:
        """
        获取节点执行顺序（按步骤编号排序）
        
        Returns:
            按顺序排列的节点名称列表
        """
        sorted_nodes = sorted(
            self.nodes.items(),
            key=lambda x: x[1].step_number
        )
        return [name for name, _ in sorted_nodes]
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证图的完整性
        
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 检查所有边的目标节点是否存在
        for from_node, to_node in self.edges.items():
            if to_node != self.END and to_node not in self.nodes:
                errors.append(f"边 {from_node} -> {to_node}: 目标节点不存在")
        
        # 检查条件边的目标节点是否存在
        for from_node, (_, mapping) in self.conditional_edges.items():
            for route_key, to_node in mapping.items():
                if to_node != self.END and to_node not in self.nodes:
                    errors.append(f"条件边 {from_node} -> {route_key} -> {to_node}: 目标节点不存在")
        
        # 检查是否有孤立节点（没有入边）
        nodes_with_incoming = set()
        for to_node in self.edges.values():
            nodes_with_incoming.add(to_node)
        for _, mapping in self.conditional_edges.values():
            for to_node in mapping.values():
                nodes_with_incoming.add(to_node)
        
        for node_name in self.nodes:
            if node_name not in nodes_with_incoming and node_name != "preload_user_profile":
                # 第一个节点可以没有入边
                errors.append(f"节点 {node_name}: 没有入边（孤立节点）")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将图转换为字典格式（用于序列化）
        
        Returns:
            图的字典表示
        """
        return {
            "nodes": {
                name: {
                    "step_number": config.step_number,
                    "description": config.description,
                    "is_parallel": config.is_parallel,
                    "parallel_group": config.parallel_group
                }
                for name, config in self.nodes.items()
            },
            "edges": self.edges,
            "conditional_edges": {
                from_node: {
                    "mapping": mapping
                }
                for from_node, (_, mapping) in self.conditional_edges.items()
            },
            "parallel_groups": self.parallel_groups
        }
    
    def __repr__(self) -> str:
        return f"WorkflowGraph(nodes={len(self.nodes)}, edges={len(self.edges)}, conditional_edges={len(self.conditional_edges)})"


# ============ 全局图实例 ============

_default_graph: Optional[WorkflowGraph] = None


def get_default_graph() -> WorkflowGraph:
    """获取默认工作流图（单例）"""
    global _default_graph
    if _default_graph is None:
        _default_graph = WorkflowGraph()
    return _default_graph


def create_custom_graph() -> WorkflowGraph:
    """创建自定义工作流图（非单例）"""
    return WorkflowGraph()


# ============ 导出 ============

__all__ = [
    "WorkflowGraph",
    "NodeConfig",
    "EdgeConfig",
    "get_default_graph",
    "create_custom_graph",
]
