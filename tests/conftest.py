# -*- coding: utf-8 -*-
"""
Pytest 全局配置

目的：
1) 确保项目根目录在 sys.path 中（支持 `import src.*`）
2) 避免将 `src/` 直接加入 sys.path，防止 `applications.*` 触发相对导入层级问题
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_root_on_syspath() -> None:
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


_ensure_project_root_on_syspath()
