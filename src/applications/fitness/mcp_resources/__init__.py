# -*- coding: utf-8 -*-
"""
MCP Resources — REQ-5

将静态域知识（安全规则、器械库、体态配置等）暴露为 MCP Resource，
供 Claude 等 LLM 客户端通过 resources/read 端点按需检索。

MCP 三层架构:
  - Tools:     已有 mcp_tools/ 目录（执行动作）
  - Resources: 本目录（静态知识，按 URI 检索）
  - Prompts:   mcp_prompts/ 目录（预制 prompt 模板）

版本: v1.0.0
日期: 2026-04-05
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MCPResource:
    """MCP Resource 定义"""
    uri: str               # 资源 URI, e.g. "fitness://rules/safety"
    name: str              # 显示名称
    description: str       # 资源描述
    mime_type: str = "application/json"
    content: Any = None    # 资源内容（延迟加载）
    _loader: Optional[callable] = field(default=None, repr=False)

    def read(self) -> Any:
        """读取资源内容"""
        if self.content is None and self._loader:
            self.content = self._loader()
        return self.content

    def to_mcp_format(self) -> Dict[str, Any]:
        """转换为 MCP resources/list 响应格式"""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


class MCPResourceRegistry:
    """
    MCP Resource 注册表

    管理所有可用的 MCP Resources，支持：
    - list: 列出所有资源
    - read: 按 URI 读取资源内容
    """

    def __init__(self):
        self._resources: Dict[str, MCPResource] = {}
        self._register_builtin()

    def _register_builtin(self):
        """注册内置健身领域资源"""
        from ..fitness_adapter import FitnessAdapter
        adapter = FitnessAdapter()

        # 安全规则
        self.register(MCPResource(
            uri="fitness://rules/safety",
            name="安全禁忌规则",
            description="体态问题禁忌映射表 — 骨盆前倾/圆肩/驼背等对应的禁忌动作",
            _loader=adapter.get_safety_contraindications,
        ))

        # 关节关键词
        self.register(MCPResource(
            uri="fitness://rules/joint-keywords",
            name="关节关键词映射",
            description="关节名称到相关动作关键词的映射，用于损伤检查",
            _loader=adapter.get_joint_keywords,
        ))

        # 高负荷动作
        self.register(MCPResource(
            uri="fitness://rules/high-load",
            name="高负荷动作关键词",
            description="需要特别安全检查的高负荷动作列表",
            _loader=adapter.get_high_load_keywords,
        ))

        # 肌肉恢复时间
        self.register(MCPResource(
            uri="fitness://data/recovery-hours",
            name="肌肉恢复时间表",
            description="各肌群恢复所需小时数（大肌群72h/中等48h/小肌群36h）",
            _loader=adapter.get_muscle_recovery_hours,
        ))

        # 目标偏好配置
        self.register(MCPResource(
            uri="fitness://data/goal-preferences",
            name="训练目标偏好",
            description="增肌/减脂/力量/耐力/康复的训练参数配置",
            _loader=adapter.get_goal_preferences,
        ))

        # 体型偏好
        self.register(MCPResource(
            uri="fitness://data/body-type-preferences",
            name="体型偏好配置",
            description="外胚/中胚/内胚型的推荐训练策略",
            _loader=adapter.get_body_type_preferences,
        ))

        # 体态问题详细配置
        self.register(MCPResource(
            uri="fitness://data/postural-issues",
            name="体态问题详细配置",
            description="骨盆前倾/后倾/圆肩/头前伸/驼背/脊柱侧弯的完整评估配置",
            _loader=adapter.get_postural_issue_config,
        ))

        # 降级推荐
        self.register(MCPResource(
            uri="fitness://data/fallback-exercises",
            name="降级推荐动作库",
            description="当 AI 工具链失败时的兜底推荐动作",
            _loader=adapter.get_fallback_recommendations,
        ))

        # 肌肉关键词映射
        self.register(MCPResource(
            uri="fitness://data/muscle-keywords",
            name="肌肉关键词映射",
            description="肌肉主关键词到同义词的映射表",
            _loader=adapter.get_keyword_mapping,
        ))

        logger.info(f"📦 MCP Resources 注册完成: {len(self._resources)} 个资源")

    def register(self, resource: MCPResource):
        """注册资源"""
        self._resources[resource.uri] = resource

    def list_resources(self) -> List[Dict[str, Any]]:
        """列出所有资源（MCP resources/list 格式）"""
        return [r.to_mcp_format() for r in self._resources.values()]

    def read_resource(self, uri: str) -> Optional[Any]:
        """
        读取资源内容

        Args:
            uri: 资源 URI

        Returns:
            资源内容，不存在返回 None
        """
        resource = self._resources.get(uri)
        if resource is None:
            logger.warning(f"⚠️ 未知资源 URI: {uri}")
            return None
        return resource.read()

    def get_resource(self, uri: str) -> Optional[MCPResource]:
        """获取资源对象"""
        return self._resources.get(uri)


# 单例
_registry: Optional[MCPResourceRegistry] = None


def get_resource_registry() -> MCPResourceRegistry:
    """获取资源注册表（单例）"""
    global _registry
    if _registry is None:
        _registry = MCPResourceRegistry()
    return _registry
