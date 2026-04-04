# -*- coding: utf-8 -*-
"""
分层上下文包构建器 — REQ-3

替代 ContextEngineering.build_context()，将上下文分为 9 层固定槽位，
每层有独立 token 预算和压缩策略。hard_constraints 层绝不压缩。

通过 HarnessConfig.context_packet_enabled feature flag 启用，
旧 ContextEngineering 保留为兼容模式。

版本: v1.0.0
日期: 2026-04-04
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ContextLayer:
    """上下文层"""
    name: str
    content: str = ""
    token_count: int = 0
    token_budget: int = 0
    compressible: bool = True
    was_compressed: bool = False
    source: str = ""  # 数据来源描述


@dataclass
class ContextPacket:
    """分层上下文包"""
    version: str = "1.0"
    layers: Dict[str, ContextLayer] = field(default_factory=dict)
    total_tokens: int = 0
    total_budget: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_layer(self, name: str) -> Optional[ContextLayer]:
        return self.layers.get(name)

    def to_llm_text(self) -> str:
        """拼接为 LLM system prompt 文本（按层顺序）"""
        parts = []
        for layer_name in LAYER_ORDER:
            layer = self.layers.get(layer_name)
            if layer and layer.content.strip():
                parts.append(layer.content)
        return "\n\n".join(parts)

    def token_usage_summary(self) -> Dict[str, Dict[str, int]]:
        """各层 token 使用量摘要"""
        return {
            name: {
                "used": layer.token_count,
                "budget": layer.token_budget,
                "utilization_pct": round(layer.token_count / layer.token_budget * 100)
                if layer.token_budget > 0 else 0,
            }
            for name, layer in self.layers.items()
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "total_tokens": self.total_tokens,
            "total_budget": self.total_budget,
            "layers": {
                name: {
                    "token_count": layer.token_count,
                    "token_budget": layer.token_budget,
                    "compressible": layer.compressible,
                    "was_compressed": layer.was_compressed,
                    "content_length": len(layer.content),
                }
                for name, layer in self.layers.items()
            },
            "metadata": self.metadata,
        }


# ============================================================
# 层配置
# ============================================================

LAYER_CONFIG = {
    "system_rules":        {"budget": 200,  "compressible": False},
    "request_context":     {"budget": 300,  "compressible": False},
    "user_snapshot":       {"budget": 500,  "compressible": True},
    "active_plan":         {"budget": 400,  "compressible": True},
    "adherence_window":    {"budget": 300,  "compressible": True},
    "hard_constraints":    {"budget": 200,  "compressible": False},   # 绝不压缩
    "long_term_memory":    {"budget": 400,  "compressible": True},
    "recent_dialogue":     {"budget": 500,  "compressible": True},
    "retrieved_knowledge": {"budget": 600,  "compressible": True},
}

LAYER_ORDER = [
    "system_rules",
    "request_context",
    "user_snapshot",
    "active_plan",
    "adherence_window",
    "hard_constraints",
    "long_term_memory",
    "recent_dialogue",
    "retrieved_knowledge",
]


# ============================================================
# 构建器
# ============================================================

class ContextPacketBuilder:
    """
    分层上下文包构建器

    每层独立填充，超预算时对 compressible 层自动截断。
    hard_constraints 层绝不压缩、绝不截断。
    """

    def __init__(self, token_counter=None):
        """
        Args:
            token_counter: (str) -> int 的 token 计数函数，
                           None 时按 1 token ≈ 2 中文字符估算
        """
        self._count_tokens = token_counter or self._estimate_tokens

    async def build(
        self,
        user_id: str,
        message: str,
        user_profile: Optional[Dict[str, Any]] = None,
        active_plan: Optional[Dict[str, Any]] = None,
        adherence_data: Optional[Dict[str, Any]] = None,
        hard_constraints: Optional[List[str]] = None,
        long_term_memories: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        retrieved_knowledge: Optional[str] = None,
        system_rules: Optional[str] = None,
    ) -> ContextPacket:
        """
        构建完整上下文包

        Args:
            user_id: 用户ID
            message: 当前用户消息
            user_profile: 用户档案（由 ProfileInjector 格式化）
            active_plan: 当前训练计划摘要
            adherence_data: 训练依从性数据（7d/14d窗口）
            hard_constraints: 硬约束列表（伤病/禁忌，绝不压缩）
            long_term_memories: 长期记忆检索结果
            conversation_history: 最近对话轮次
            retrieved_knowledge: Qdrant/Neo4j 检索知识
            system_rules: 系统规则文本

        Returns:
            ContextPacket
        """
        packet = ContextPacket(
            metadata={"user_id": user_id, "builder": "ContextPacketBuilder/v1.0"},
        )
        total_budget = 0

        # 初始化所有层
        for layer_name in LAYER_ORDER:
            config = LAYER_CONFIG[layer_name]
            packet.layers[layer_name] = ContextLayer(
                name=layer_name,
                token_budget=config["budget"],
                compressible=config["compressible"],
            )
            total_budget += config["budget"]

        packet.total_budget = total_budget

        # ---- 填充各层 ----

        # 1. system_rules
        self._fill_layer(packet, "system_rules",
            content=system_rules or "你是玉珍健身的AI训练教练。基于用户数据和工具分析结果提供专业健身指导。",
            source="hardcoded",
        )

        # 2. request_context
        self._fill_layer(packet, "request_context",
            content=f"## 用户当前请求\n{message}",
            source="current_message",
        )

        # 3. user_snapshot
        if user_profile:
            profile_text = self._format_user_snapshot(user_profile)
            self._fill_layer(packet, "user_snapshot",
                content=profile_text,
                source="user_profile_tool",
            )

        # 4. active_plan
        if active_plan:
            plan_text = self._format_active_plan(active_plan)
            self._fill_layer(packet, "active_plan",
                content=plan_text,
                source="weekly_plan_generator",
            )

        # 5. adherence_window
        if adherence_data:
            adherence_text = self._format_adherence(adherence_data)
            self._fill_layer(packet, "adherence_window",
                content=adherence_text,
                source="training_log_analyzer",
            )

        # 6. hard_constraints — 绝不压缩
        if hard_constraints:
            constraints_text = "## 硬约束（安全红线，绝不违反）\n"
            for c in hard_constraints:
                constraints_text += f"- ⛔ {c}\n"
            self._fill_layer(packet, "hard_constraints",
                content=constraints_text,
                source="memory_v2_hard_constraint",
            )

        # 7. long_term_memory
        if long_term_memories:
            memory_text = "## 用户记忆\n"
            for m in long_term_memories:
                score = m.get("score", 0)
                if score > 0.5:
                    cat = m.get("category", "")
                    memory_text += f"- [{cat}] {m.get('content', '')} (相关度:{score:.2f})\n"
            self._fill_layer(packet, "long_term_memory",
                content=memory_text,
                source="memory_v2_recall",
            )

        # 8. recent_dialogue
        if conversation_history:
            dialogue_text = "## 最近对话\n"
            for msg in conversation_history[-6:]:  # 最多保留6条
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # 截断过长的单条消息
                if len(content) > 300:
                    content = content[:300] + "..."
                dialogue_text += f"**{role}**: {content}\n\n"
            self._fill_layer(packet, "recent_dialogue",
                content=dialogue_text,
                source="conversation_memory",
            )

        # 9. retrieved_knowledge
        if retrieved_knowledge:
            self._fill_layer(packet, "retrieved_knowledge",
                content=f"## 检索知识\n{retrieved_knowledge}",
                source="qdrant_neo4j",
            )

        # 计算总 token
        packet.total_tokens = sum(
            layer.token_count for layer in packet.layers.values()
        )

        logger.info(
            f"🧱 上下文包构建完成: user={user_id}, "
            f"total_tokens={packet.total_tokens}/{packet.total_budget}, "
            f"layers_filled={sum(1 for l in packet.layers.values() if l.content)}/9"
        )

        return packet

    # ============================================================
    # 层填充与压缩
    # ============================================================

    def _fill_layer(
        self,
        packet: ContextPacket,
        layer_name: str,
        content: str,
        source: str = "",
    ):
        """填充单层，超预算时自动截断（compressible 层）"""
        layer = packet.layers[layer_name]
        layer.source = source

        token_count = self._count_tokens(content)

        if token_count <= layer.token_budget:
            # 在预算内
            layer.content = content
            layer.token_count = token_count
        elif layer.compressible:
            # 超预算且可压缩 → 截断
            truncated = self._truncate_to_budget(content, layer.token_budget)
            layer.content = truncated
            layer.token_count = self._count_tokens(truncated)
            layer.was_compressed = True
            logger.debug(
                f"层 {layer_name} 超预算截断: "
                f"{token_count} → {layer.token_count} tokens"
            )
        else:
            # 不可压缩层（hard_constraints 等）→ 不截断，允许超预算
            layer.content = content
            layer.token_count = token_count
            if token_count > layer.token_budget:
                logger.warning(
                    f"⚠️ 不可压缩层 {layer_name} 超预算: "
                    f"{token_count} > {layer.token_budget} tokens"
                )

    def _truncate_to_budget(self, text: str, budget: int) -> str:
        """按 token 预算截断文本"""
        # 估算：1 token ≈ 2 字符（中文），按字符截断
        char_limit = budget * 2
        if len(text) <= char_limit:
            return text
        return text[:char_limit] + "\n...(已截断)"

    # ============================================================
    # 格式化辅助
    # ============================================================

    @staticmethod
    def _format_user_snapshot(profile: Dict[str, Any]) -> str:
        """格式化用户快照"""
        parts = ["## 用户档案"]

        basic_fields = {
            "name": "姓名",
            "age": "年龄",
            "gender": "性别",
            "height": "身高(cm)",
            "weight": "体重(kg)",
            "fitness_goal": "训练目标",
            "experience_level": "经验水平",
            "available_time": "可用时间",
        }

        for key, label in basic_fields.items():
            val = profile.get(key)
            if val:
                parts.append(f"- {label}: {val}")

        equipment = profile.get("available_equipment", [])
        if equipment:
            parts.append(f"- 可用器械: {', '.join(equipment) if isinstance(equipment, list) else equipment}")

        return "\n".join(parts)

    @staticmethod
    def _format_active_plan(plan: Dict[str, Any]) -> str:
        """格式化当前训练计划摘要"""
        parts = ["## 当前训练计划"]
        if plan.get("name"):
            parts.append(f"- 计划名称: {plan['name']}")
        if plan.get("current_week"):
            parts.append(f"- 当前周: 第{plan['current_week']}周")
        if plan.get("split_type"):
            parts.append(f"- 分化方式: {plan['split_type']}")
        if plan.get("days_per_week"):
            parts.append(f"- 训练频率: {plan['days_per_week']}天/周")
        return "\n".join(parts)

    @staticmethod
    def _format_adherence(data: Dict[str, Any]) -> str:
        """格式化训练依从性数据"""
        parts = ["## 训练执行情况"]
        if data.get("completion_rate"):
            parts.append(f"- 完成率: {data['completion_rate']}%")
        if data.get("missed_sessions"):
            parts.append(f"- 漏练次数: {data['missed_sessions']}")
        if data.get("avg_rpe"):
            parts.append(f"- 平均RPE: {data['avg_rpe']}")
        if data.get("trend"):
            parts.append(f"- 趋势: {data['trend']}")
        return "\n".join(parts)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """估算 token 数（1 token ≈ 2 中文字符 或 4 英文字符）"""
        if not text:
            return 0
        # 简单估算：中文字符数/2 + 英文单词数
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        ascii_chars = sum(1 for c in text if c.isascii())
        return (chinese_chars // 2) + (ascii_chars // 4) + 1
