# -*- coding: utf-8 -*-
"""
MonitoredToolMixin - 性能监控Mixin

提供 execute_with_monitoring() 包装器，自动记录执行时间、
捕获异常、注入版本元数据。

Task 44 - Phase 7 Batch 4
"""

import logging
import time
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MonitoredToolMixin:
    """
    性能监控Mixin

    依赖 self.get_name(), self.get_version(), self.get_input_schema(),
    self.execute() — 均由 BaseMCPTool 提供。
    """

    async def execute_with_monitoring(
        self, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        带性能监控的执行包装器。

        自动完成：输入验证 → 计时 → 执行 → 元数据注入 → 异常标准化。
        """
        start_time = time.time()
        tool_name = self.get_name()
        tool_version = self.get_version()

        try:
            input_schema = self.get_input_schema()
            validated_input = input_schema(**input_data)

            _logger = getattr(self, "logger", logger)
            _logger.info(f"🔧 开始执行工具: {tool_name} (v{tool_version})")

            result = await self.execute(validated_input.model_dump())

            execution_time_ms = (time.time() - start_time) * 1000
            result.setdefault("metadata", {})
            result["metadata"]["execution_time_ms"] = execution_time_ms
            result["metadata"]["timestamp"] = datetime.now().isoformat()
            result["metadata"]["tool_name"] = tool_name
            result["metadata"]["tool_version"] = tool_version

            _logger.info(
                f"✅ 工具执行成功: {tool_name} v{tool_version} "
                f"({execution_time_ms:.2f}ms)"
            )
            return result

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            _logger = getattr(self, "logger", logger)
            _logger.error(
                f"❌ 工具执行失败: {tool_name} v{tool_version} "
                f"({execution_time_ms:.2f}ms) - {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "tool_name": tool_name,
                "error": {
                    "code": "TOOL_EXECUTION_ERROR",
                    "message": str(e),
                    "type": type(e).__name__,
                },
                "metadata": {
                    "execution_time_ms": execution_time_ms,
                    "timestamp": datetime.now().isoformat(),
                    "tool_version": tool_version,
                },
            }
