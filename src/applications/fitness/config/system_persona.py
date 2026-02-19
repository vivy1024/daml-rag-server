# -*- coding: utf-8 -*-
"""
SystemPersona 风格系统

管理系统人设配置，支持：
- 从 YAML 加载 persona 配置
- 热加载（文件修改时间检测）
- get_persona(persona_id) → SystemPersona
- list_personas() → 给前端/API 用
- 单例模式 + 懒加载缓存

版本: v1.0.0
日期: 2026-02-20
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SystemPersona:
    """系统人设数据类"""
    id: str
    name: str
    icon: str
    description: str
    system_prefix: str
    tone: str
    emoji_style: str  # minimal / frequent / none

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "tone": self.tone,
            "emoji_style": self.emoji_style,
        }


class SystemPersonaManager:
    """
    系统人设管理器

    从 config/system_personas.yaml 加载 persona 配置，
    支持热加载和单例访问。
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            config_path = project_root / "config" / "system_personas.yaml"

        self.config_path = Path(config_path)
        self._personas: Dict[str, SystemPersona] = {}
        self._default_persona_id: str = "coach_professional"
        self._last_modified: Optional[float] = None

        self._load()

    def _load(self):
        """从 YAML 加载配置"""
        if not self.config_path.exists():
            logger.error(f"Persona 配置文件不存在: {self.config_path}")
            self._create_fallback()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            self._default_persona_id = data.get("default_persona", "coach_professional")
            personas_data = data.get("personas", {})

            self._personas.clear()
            for pid, pdata in personas_data.items():
                self._personas[pid] = SystemPersona(
                    id=pid,
                    name=pdata["name"],
                    icon=pdata["icon"],
                    description=pdata["description"],
                    system_prefix=pdata["system_prefix"].strip(),
                    tone=pdata["tone"],
                    emoji_style=pdata["emoji_style"],
                )

            self._last_modified = self.config_path.stat().st_mtime
            logger.info(f"✅ Persona 配置加载完成: {len(self._personas)} 个人设")

        except Exception as e:
            logger.error(f"❌ Persona 配置加载失败: {e}")
            self._create_fallback()

    def _create_fallback(self):
        """创建兜底默认 persona"""
        self._personas["coach_professional"] = SystemPersona(
            id="coach_professional",
            name="专业教练",
            icon="🎓",
            description="严谨专业，引用科学标准",
            system_prefix="你是玉珍健身的专业教练，拥有ACSM和NSCA认证。请提供专业、严谨的健身指导。",
            tone="professional",
            emoji_style="minimal",
        )
        self._default_persona_id = "coach_professional"

    def reload_if_modified(self) -> bool:
        """检查文件是否修改，是则热加载"""
        try:
            if not self.config_path.exists():
                return False
            current_mtime = self.config_path.stat().st_mtime
            if self._last_modified is not None and current_mtime == self._last_modified:
                return False
            logger.info("🔄 检测到 Persona 配置修改，重新加载")
            self._load()
            return True
        except Exception as e:
            logger.error(f"检查 Persona 配置修改失败: {e}")
            return False

    def get_persona(self, persona_id: Optional[str] = None) -> SystemPersona:
        """获取指定 persona，不存在则返回默认"""
        self.reload_if_modified()

        if persona_id and persona_id in self._personas:
            return self._personas[persona_id]

        if persona_id:
            logger.warning(f"Persona '{persona_id}' 不存在，使用默认: {self._default_persona_id}")

        return self._personas.get(self._default_persona_id, list(self._personas.values())[0])

    def list_personas(self) -> List[dict]:
        """返回所有 persona 的摘要信息（给前端/API 用）"""
        self.reload_if_modified()
        return [p.to_dict() for p in self._personas.values()]

    @property
    def default_persona_id(self) -> str:
        return self._default_persona_id


# ═══════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════

_global_persona_manager: Optional[SystemPersonaManager] = None


def get_persona_manager() -> SystemPersonaManager:
    """获取全局 PersonaManager 单例"""
    global _global_persona_manager
    if _global_persona_manager is None:
        _global_persona_manager = SystemPersonaManager()
    return _global_persona_manager
