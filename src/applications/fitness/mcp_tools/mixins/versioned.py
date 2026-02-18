# -*- coding: utf-8 -*-
"""
VersionedToolMixin - 版本管理Mixin

提供工具版本号、变更日志、兼容性检查等功能。
从BaseMCPTool v2.0.0中提取，对应Requirements 12.1-12.5。

Task 44 - Phase 7 Batch 4
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class VersionInfo:
    """工具版本信息"""
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
        """同一主版本内兼容 (Req 12.5)"""
        return self.major == other.major

    @classmethod
    def from_string(cls, version_str: str) -> 'VersionInfo':
        parts = version_str.split('.')
        if len(parts) != 3:
            raise ValueError(f"无效的版本号格式: {version_str}")
        return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))


@dataclass
class ChangelogEntry:
    """变更日志条目"""
    version: str
    date: str
    changes: List[str]
    breaking_changes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "date": self.date,
            "changes": self.changes,
            "breaking_changes": self.breaking_changes,
        }


class VersionedToolMixin:
    """
    版本管理Mixin

    为MCP工具提供语义化版本号和变更日志功能。
    子类通过 set_version() / add_changelog_entry() 声明版本。
    """

    _version: VersionInfo = VersionInfo(1, 0, 0)
    _changelog: List[ChangelogEntry] = []

    def get_version(self) -> str:
        """返回版本号字符串 (Req 12.1)"""
        return str(self._version)

    def get_version_info(self) -> VersionInfo:
        return self._version

    def get_changelog(self) -> List[Dict[str, Any]]:
        """返回变更日志 (Req 12.2)"""
        return [entry.to_dict() for entry in self._changelog]

    def get_latest_changelog(self) -> Optional[Dict[str, Any]]:
        if self._changelog:
            return self._changelog[0].to_dict()
        return None

    def is_compatible_with_version(self, version_str: str) -> bool:
        """检查版本兼容性 (Req 12.5)"""
        try:
            other = VersionInfo.from_string(version_str)
            return self._version.is_compatible_with(other)
        except ValueError:
            return False

    @classmethod
    def set_version(cls, major: int, minor: int, patch: int) -> None:
        cls._version = VersionInfo(major, minor, patch)

    @classmethod
    def add_changelog_entry(
        cls,
        version: str,
        date: str,
        changes: List[str],
        breaking_changes: Optional[List[str]] = None,
    ) -> None:
        entry = ChangelogEntry(
            version=version,
            date=date,
            changes=changes,
            breaking_changes=breaking_changes or [],
        )
        cls._changelog.insert(0, entry)
