# -*- coding: utf-8 -*-
"""
Skill YAML 加载器

从 YAML 文件加载 SkillDefinition，支持单文件和目录批量加载。
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .definition import SkillDefinition

logger = logging.getLogger(__name__)

# SkillDefinition 必填字段
REQUIRED_FIELDS = {"id", "name", "description"}


class SkillLoadError(Exception):
    """Skill 加载异常"""
    pass


class SkillLoader:
    """Skill YAML 加载器

    从 YAML 文件加载 SkillDefinition 实例。
    支持单文件加载和目录批量加载。
    """

    @staticmethod
    def load_file(file_path: str) -> SkillDefinition:
        """从单个 YAML 文件加载 SkillDefinition

        Args:
            file_path: YAML 文件路径

        Returns:
            SkillDefinition 实例

        Raises:
            SkillLoadError: 文件不存在、格式错误或缺少必填字段
        """
        path = Path(file_path)
        if not path.exists():
            raise SkillLoadError(f"Skill 文件不存在: {file_path}")
        if not path.suffix in (".yaml", ".yml"):
            raise SkillLoadError(f"不支持的文件格式: {path.suffix}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise SkillLoadError(f"YAML 解析失败 [{file_path}]: {e}")

        if not isinstance(data, dict):
            raise SkillLoadError(f"YAML 内容必须是字典格式: {file_path}")

        # 验证必填字段
        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise SkillLoadError(
                f"Skill [{file_path}] 缺少必填字段: {', '.join(sorted(missing))}"
            )

        return SkillLoader._dict_to_definition(data)

    @staticmethod
    def load_directory(directory: str) -> List[SkillDefinition]:
        """从目录批量加载所有 Skill YAML 文件

        Args:
            directory: 包含 YAML 文件的目录路径

        Returns:
            SkillDefinition 列表

        Raises:
            SkillLoadError: 目录不存在
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise SkillLoadError(f"Skill 目录不存在: {directory}")
        if not dir_path.is_dir():
            raise SkillLoadError(f"路径不是目录: {directory}")

        skills: List[SkillDefinition] = []
        yaml_files = sorted(
            list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.yml"))
        )

        if not yaml_files:
            logger.warning(f"目录中没有 YAML 文件: {directory}")
            return skills

        for yaml_file in yaml_files:
            try:
                skill = SkillLoader.load_file(str(yaml_file))
                skills.append(skill)
                logger.debug(f"已加载 Skill: {skill.id} ({skill.name})")
            except SkillLoadError as e:
                logger.error(f"加载 Skill 失败: {e}")
                # 单个文件失败不阻断整体加载
                continue

        logger.info(f"从 {directory} 加载了 {len(skills)} 个 Skill")
        return skills

    @staticmethod
    def _dict_to_definition(data: Dict) -> SkillDefinition:
        """将字典转换为 SkillDefinition

        Args:
            data: 从 YAML 解析的字典

        Returns:
            SkillDefinition 实例
        """
        return SkillDefinition(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            triggers=data.get("triggers", []),
            required_tools=data.get("required_tools", []),
            optional_tools=data.get("optional_tools", []),
            safety_preconditions=data.get("safety_preconditions", {}),
            output_standard=data.get("output_standard", ""),
            example_output=data.get("example_output", ""),
            degradation=data.get("degradation", ""),
            harness_checkpoints=data.get("harness_checkpoints", {}),
        )
