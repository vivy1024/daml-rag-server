"""
MCP 工具: 用户数据 — 从 Laravel 后端获取用户档案和训练记录

通过 BackendClient 调用 Laravel 内部 API。
所有工具都有 fallback_hint，失败时 Agent 可降级。
"""

import logging
from typing import Any, Dict

from ..clients import get_backend_client

logger = logging.getLogger(__name__)


async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """获取用户完整健身档案

    Returns:
        成功: {user_id, basic, goals, health, training, strength}
        失败: {error, fallback_hint}
    """
    client = get_backend_client()
    result = await client.get_user_profile(user_id)

    if result is None:
        return {
            "error": f"无法获取用户 {user_id} 的档案",
            "fallback_hint": "请直接询问用户的身高、体重、年龄、性别、训练目标和伤病情况",
        }

    return result


async def get_training_history(
    user_id: str, days: int = 30, exercise_name: str = None
) -> Dict[str, Any]:
    """获取训练记录

    Returns:
        成功: {records, summary}
        失败: {error, fallback_hint}
    """
    client = get_backend_client()
    result = await client.get_training_records(user_id, days=days, exercise_name=exercise_name)

    if result is None:
        return {
            "error": f"无法获取用户 {user_id} 的训练记录",
            "fallback_hint": "请询问用户最近的训练情况（做了什么动作、用了多少重量、做了几组几次）",
        }

    return result


async def get_progress_data(
    user_id: str, metric: str = "weight", days: int = 90
) -> Dict[str, Any]:
    """获取进度数据

    Returns:
        成功: {metric, data_points, trend}
        失败: {error, fallback_hint}
    """
    client = get_backend_client()
    result = await client.get_progress_data(user_id, metric=metric, days=days)

    if result is None:
        return {
            "error": f"无法获取用户 {user_id} 的进度数据",
            "fallback_hint": "请询问用户当前体重/体脂等数据，以及过去几个月的变化趋势",
        }

    return result


async def save_training_plan(user_id: str, plan_data: Dict[str, Any]) -> Dict[str, Any]:
    """保存 AI 生成的训练计划到用户账户

    Returns:
        成功: {plan_id, message}
        失败: {error, fallback_hint}
    """
    # 基本校验
    if not plan_data:
        return {"error": "计划数据为空", "fallback_hint": "请将计划以文本形式输出给用户"}

    # 大小限制（防止超大 payload）
    plan_str = str(plan_data)
    if len(plan_str) > 50000:
        return {"error": "计划数据过大（>50KB）", "fallback_hint": "请精简计划内容后重试"}

    # 必需字段检查
    if "name" not in plan_data and "goal" not in plan_data:
        return {"error": "计划缺少 name 或 goal 字段", "fallback_hint": "请确保计划包含名称和目标"}

    client = get_backend_client()
    result = await client.save_training_plan(user_id, plan_data)

    if result is None:
        return {
            "error": "训练计划保存失败",
            "fallback_hint": "请将计划以文本形式输出给用户，建议用户手动保存",
        }

    return result
