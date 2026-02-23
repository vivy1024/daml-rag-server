# -*- coding: utf-8 -*-
"""
Token 预算管理器

统一管理所有上下文组件的 token 预算。
当总 token 超过预算时，按优先级压缩低优先级组件。

组件优先级（从高到低，高优先级不可压缩）：
1. persona_prefix — 固定，不可压缩
2. task_instruction — 模板指令，基本固定
3. rendering_constraint — 固定
4. current_message — 用户当前消息，不可压缩
5. user_profile — 可压缩（截断）
6. user_memory — 可减少条数
7. few_shot_examples — 可减少条数
8. web_search — 可减少条数
9. mcp_tools_result — 可截断
10. conversation_history — 主要压缩对象

版本: v1.0.0
日期: 2026-02-20
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 中文平均每 token 字符数（校准值，更接近 Claude/DeepSeek 实际 tokenization）
AVG_CHARS_PER_TOKEN = 1.8


def estimate_tokens(text: str) -> int:
    """估算文本 token 数（字符数 / 2.5）"""
    if not text:
        return 0
    return int(len(text) / AVG_CHARS_PER_TOKEN)


@dataclass
class BudgetAllocation:
    """单个组件的预算分配结果"""
    name: str
    original_tokens: int
    allocated_tokens: int
    text: str  # 压缩后的文本
    compressed: bool = False


@dataclass
class BudgetResult:
    """预算分配总结果"""
    total_tokens: int
    budget: int
    over_budget: bool
    allocations: Dict[str, BudgetAllocation] = field(default_factory=dict)

    def get_text(self, name: str) -> str:
        """获取组件压缩后的文本"""
        alloc = self.allocations.get(name)
        return alloc.text if alloc else ""


class TokenBudgetManager:
    """
    统一管理所有上下文组件的 token 预算。

    总预算 8000 tokens，各组件有默认分配上限。
    超预算时按 COMPRESSION_PRIORITY 顺序压缩。
    """

    DEFAULT_BUDGET = 12000

    # 各组件默认 token 上限
    COMPONENT_LIMITS = {
        "persona_prefix": 400,
        "task_instruction": 1500,
        "rendering_constraint": 200,
        "current_message": 200,
        "user_profile": 300,
        "user_memory": 400,
        "few_shot_examples": 500,
        "web_search": 500,
        "mcp_tools_result": 3000,
        "conversation_history": 4000,
    }

    # 不可压缩的组件
    INCOMPRESSIBLE = {"persona_prefix", "task_instruction", "rendering_constraint", "current_message"}

    # 压缩优先级（先压低优先级的）
    COMPRESSION_PRIORITY = [
        "conversation_history",
        "mcp_tools_result",
        "few_shot_examples",
        "web_search",
        "user_memory",
        "user_profile",
    ]

    def __init__(self, total_budget: Optional[int] = None):
        self.total_budget = total_budget or self.DEFAULT_BUDGET

    def allocate(self, components: Dict[str, str]) -> BudgetResult:
        """
        输入各组件的原始文本，输出压缩后的分配方案。

        Args:
            components: {组件名: 原始文本}，如 {"persona_prefix": "...", "user_memory": "..."}

        Returns:
            BudgetResult 包含每个组件的分配结果
        """
        # 1. 计算各组件原始 token 数
        allocations: Dict[str, BudgetAllocation] = {}
        total = 0

        for name, text in components.items():
            tokens = estimate_tokens(text)
            # 先按组件上限裁剪（即使未超总预算，单组件也不应超限）
            limit = self.COMPONENT_LIMITS.get(name, 500)
            if tokens > limit and name not in self.INCOMPRESSIBLE:
                text = self._truncate_text(text, limit)
                tokens = limit

            allocations[name] = BudgetAllocation(
                name=name,
                original_tokens=estimate_tokens(components[name]),
                allocated_tokens=tokens,
                text=text,
            )
            total += tokens

        # 2. 如果未超预算，直接返回
        if total <= self.total_budget:
            return BudgetResult(
                total_tokens=total,
                budget=self.total_budget,
                over_budget=False,
                allocations=allocations,
            )

        # 3. 超预算 → 按优先级压缩
        logger.info(f"🔧 Token预算超限: {total}/{self.total_budget}，开始压缩")
        overflow = total - self.total_budget

        for comp_name in self.COMPRESSION_PRIORITY:
            if overflow <= 0:
                break
            alloc = allocations.get(comp_name)
            if not alloc or alloc.allocated_tokens == 0:
                continue

            # 计算该组件最少保留的 token 数
            min_keep = self._min_keep(comp_name)
            can_free = alloc.allocated_tokens - min_keep
            if can_free <= 0:
                continue

            freed = min(can_free, overflow)
            new_tokens = alloc.allocated_tokens - freed

            alloc.text = self._truncate_text(alloc.text, new_tokens)
            alloc.allocated_tokens = new_tokens
            alloc.compressed = True
            overflow -= freed

            logger.info(
                f"  压缩 {comp_name}: {alloc.original_tokens} → {new_tokens} tokens "
                f"(释放 {freed})"
            )

        new_total = sum(a.allocated_tokens for a in allocations.values())
        return BudgetResult(
            total_tokens=new_total,
            budget=self.total_budget,
            over_budget=new_total > self.total_budget,
            allocations=allocations,
        )

    def _min_keep(self, comp_name: str) -> int:
        """各组件压缩后的最低保留 token 数"""
        minimums = {
            "conversation_history": 200,   # 至少保留最近 1-2 轮
            "mcp_tools_result": 100,       # 至少保留摘要
            "few_shot_examples": 0,        # 可完全移除
            "web_search": 0,               # 可完全移除
            "user_memory": 80,             # 至少保留 1 条
            "user_profile": 50,            # 至少保留基本信息
        }
        return minimums.get(comp_name, 0)

    @staticmethod
    def _truncate_text(text: str, target_tokens: int) -> str:
        """按目标 token 数截断文本"""
        if target_tokens <= 0:
            return ""
        target_chars = int(target_tokens * AVG_CHARS_PER_TOKEN)
        if len(text) <= target_chars:
            return text
        # 尝试在换行符处截断，保持结构完整
        truncated = text[:target_chars]
        last_newline = truncated.rfind("\n")
        if last_newline > target_chars * 0.7:
            truncated = truncated[:last_newline]
        return truncated + "\n[...已截断]"
