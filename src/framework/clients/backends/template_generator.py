# -*- coding: utf-8 -*-
"""
TemplateResponseGenerator - 模板降级响应生成器

当所有LLM后端都不可用时，生成结构化的模板响应。

Task 45 - Phase 7 Batch 4
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TemplateResponseGenerator:
    """模板化响应生成器（最终降级）"""

    def generate(self, query: str, context: Dict[str, Any]) -> str:
        """
        生成模板化响应。

        Args:
            query: 用户查询
            context: 上下文（tool_results, error等）
        """
        tool_results = context.get("tool_results", {})
        error = context.get("error", "LLM服务暂时不可用")

        logger.info(
            f"生成模板化响应: query_length={len(query)}, "
            f"tool_results_count={len(tool_results)}"
        )

        parts = [
            f"抱歉，AI分析功能暂时不可用（{error}）。",
            "",
            f"📝 您的查询：{query}",
            "",
        ]

        if tool_results:
            parts.append("✅ 已完成以下数据分析：")
            parts.append("")

            if "step1_user_profile" in tool_results:
                profile = tool_results["step1_user_profile"]
                if profile and isinstance(profile, dict):
                    parts.append("👤 **用户档案**：")
                    if "age" in profile:
                        parts.append(f"  - 年龄：{profile['age']}岁")
                    if "primary_goal" in profile:
                        parts.append(f"  - 目标：{profile['primary_goal']}")
                    if "fitness_level" in profile:
                        parts.append(f"  - 水平：{profile['fitness_level']}")
                    parts.append("")

            if "step4_complexity" in tool_results:
                complexity = tool_results["step4_complexity"]
                if complexity and isinstance(complexity, dict):
                    is_complex = complexity.get("is_complex", False)
                    parts.append(
                        f"🔍 **查询分析**：{'复杂' if is_complex else '简单'}查询"
                    )
                    parts.append("")

            if "step8_retrieval_results" in tool_results:
                retrieval = tool_results["step8_retrieval_results"]
                if retrieval and isinstance(retrieval, dict):
                    count = retrieval.get("count", 0)
                    parts.append(f"📊 **检索结果**：找到 {count} 个相关推荐")
                    parts.append("")

        parts.extend([
            "💡 **建议**：",
            "  - 请稍后重试获取AI分析",
            "  - 或联系客服获取人工指导",
            "  - 您也可以查看上述数据自行分析",
            "",
            "感谢您的理解！",
        ])

        return "\n".join(parts)
