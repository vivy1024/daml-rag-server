# -*- coding: utf-8 -*-
"""
SkillManager v2

管理所有 Skill 的注册、加载、查询，并生成 LLM function calling 所需的 prompt 和 schema。
"""

import logging
from typing import Dict, List, Optional

from .definition import SkillDefinition
from .loader import SkillLoader

logger = logging.getLogger(__name__)


class SkillNotFoundError(Exception):
    """Skill 未找到异常"""
    pass


class SkillManager:
    """Skill 管理器 v2

    负责 Skill 的注册、加载、查询，以及生成 LLM Skill 选择所需的
    prompt 和 function calling schema。
    """

    def __init__(self) -> None:
        self._skills: Dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        """注册单个 Skill

        Args:
            skill: SkillDefinition 实例
        """
        if skill.id in self._skills:
            logger.warning(f"Skill [{skill.id}] 已存在，将被覆盖")
        self._skills[skill.id] = skill
        logger.debug(f"已注册 Skill: {skill.id} ({skill.name})")

    def load_all(self, directory: str) -> int:
        """从目录加载所有 Skill YAML 并注册

        Args:
            directory: Skill YAML 文件目录

        Returns:
            成功加载的 Skill 数量
        """
        skills = SkillLoader.load_directory(directory)
        for skill in skills:
            self.register(skill)
        logger.info(f"SkillManager 已加载 {len(skills)} 个 Skill")
        return len(skills)

    def get(self, skill_id: str) -> SkillDefinition:
        """获取指定 Skill

        Args:
            skill_id: Skill ID

        Returns:
            SkillDefinition 实例

        Raises:
            SkillNotFoundError: Skill 不存在
        """
        if skill_id not in self._skills:
            raise SkillNotFoundError(f"Skill 不存在: {skill_id}")
        return self._skills[skill_id]

    def list_skills(self) -> List[SkillDefinition]:
        """列出所有已注册的 Skill

        Returns:
            SkillDefinition 列表
        """
        return list(self._skills.values())

    def get_selection_prompt(self) -> str:
        """生成 Skill 选择 prompt（供 LLM function calling 用）

        Returns:
            包含所有 Skill 信息的选择 prompt 文本
        """
        lines = [
            "你是玉珍健身 AI 教练的任务路由器。",
            "根据用户消息选择最合适的 Skill。",
            "如果用户只是简单问候或闲聊，使用 direct_reply 直接回答。",
            "",
            "可用 Skill 列表：",
            "",
        ]

        for skill in self._skills.values():
            lines.append(f"- **{skill.id}**: {skill.name}")
            lines.append(f"  描述: {skill.description}")
            if skill.triggers:
                triggers_str = "、".join(skill.triggers[:5])
                lines.append(f"  适用场景: {triggers_str}")
            lines.append("")

        return "\n".join(lines)

    def get_function_schema(self) -> dict:
        """生成 select_skill 的 OpenAI function calling schema

        Returns:
            符合 OpenAI function calling 格式的 schema 字典
        """
        skill_ids = list(self._skills.keys())

        return {
            "type": "function",
            "function": {
                "name": "select_skill",
                "description": (
                    "根据用户意图选择最合适的 Skill 来处理请求。"
                    "如果是简单问候或闲聊，使用 direct_reply 参数直接回答。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "enum": skill_ids,
                            "description": "选择的 Skill ID",
                        },
                        "reason": {
                            "type": "string",
                            "description": "选择该 Skill 的原因（简短说明）",
                        },
                        "direct_reply": {
                            "type": "string",
                            "description": (
                                "如果不需要调用 Skill（如简单问候），"
                                "直接在此字段返回回答内容"
                            ),
                        },
                    },
                    "required": [],
                },
            },
        }

    @property
    def skill_count(self) -> int:
        """已注册的 Skill 数量"""
        return len(self._skills)
