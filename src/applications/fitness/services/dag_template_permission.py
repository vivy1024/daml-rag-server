# -*- coding: utf-8 -*-
"""
DAG模板权限检查服务

基于会员等级检查用户是否有权使用特定的DAG模板。
与前端dag-templates.ts配置保持一致。

版本: v1.0.0
日期: 2026-01-06
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# DAG模板分级定义（MVP阶段 - 按复杂度分级计费）
# 免费版开放全部13个模板，但按复杂度限制使用次数
ALL_TEMPLATES = [
    "greeting", "quick_consultation", "exercise_optimization", 
    "progress_analysis", "safety_assessment", "complete_training_plan", 
    "nutrition_planning", "comprehensive_fitness", "rehabilitation_training", 
    "posture_correction", "plan_adjustment", "fat_loss_program", "strength_program"
]

# 按复杂度分类
SIMPLE_TEMPLATES = ["greeting", "quick_consultation", "exercise_optimization"]  # complexity 1
MEDIUM_TEMPLATES = ["progress_analysis", "safety_assessment", "nutrition_planning", "posture_correction", "plan_adjustment"]  # complexity 2
COMPLEX_TEMPLATES = ["complete_training_plan", "comprehensive_fitness", "rehabilitation_training", "fat_loss_program", "strength_program"]  # complexity 3

DAG_TEMPLATE_TIERS = {
    "free": ALL_TEMPLATES,
    "warmheart": ALL_TEMPLATES,
    "energy": ALL_TEMPLATES
}

# 会员等级层级（用于权限继承）
MEMBERSHIP_HIERARCHY = {
    "free": 0,
    "warmheart": 1,
    "energy": 2
}

# 模板到所需会员等级的映射
TEMPLATE_REQUIRED_TIER: Dict[str, str] = {}
for tier, templates in DAG_TEMPLATE_TIERS.items():
    for template_id in templates:
        TEMPLATE_REQUIRED_TIER[template_id] = tier


@dataclass
class PermissionCheckResult:
    """权限检查结果"""
    allowed: bool
    template_id: str
    user_tier: str
    required_tier: str
    message: str
    fallback_template_id: Optional[str] = None


def get_user_membership_tier(membership_info: Optional[Dict[str, Any]]) -> str:
    """
    从会员信息中提取会员等级
    
    Args:
        membership_info: 会员信息字典
        
    Returns:
        str: 会员等级（free/warmheart/energy）
    """
    if not membership_info:
        return "free"
    
    # 尝试多种字段名
    tier = membership_info.get("tier")
    if not tier:
        tier = membership_info.get("slug")
    if not tier:
        tier = membership_info.get("membership_tier")
    if not tier:
        # 从嵌套的membership对象中获取
        membership = membership_info.get("membership", {})
        tier = membership.get("tier") or membership.get("slug")
    
    # 标准化等级名称
    if tier:
        tier = tier.lower()
        if tier in MEMBERSHIP_HIERARCHY:
            return tier
    
    return "free"


def check_template_permission(
    template_id: str,
    membership_info: Optional[Dict[str, Any]]
) -> PermissionCheckResult:
    """
    检查用户是否有权使用指定的DAG模板
    
    积分体系改造后，所有模板直接返回allowed=true，
    权限控制改为积分消耗机制。
    
    Args:
        template_id: DAG模板ID
        membership_info: 用户会员信息
        
    Returns:
        PermissionCheckResult: 权限检查结果（始终允许）
    """
    user_tier = get_user_membership_tier(membership_info)
    
    # 积分体系：所有模板直接允许访问
    # 权限控制改为积分消耗机制
    return PermissionCheckResult(
        allowed=True,
        template_id=template_id,
        user_tier=user_tier,
        required_tier="free",  # 所有模板对所有用户开放
        message=f"用户({user_tier})有权使用模板({template_id})"
    )


def _find_fallback_template(original_template_id: str, user_tier: str) -> str:
    """
    为无权限的模板找到合适的降级模板
    
    Args:
        original_template_id: 原始模板ID
        user_tier: 用户会员等级
        
    Returns:
        str: 降级模板ID
    """
    # 获取用户可用的所有模板
    available_templates = get_available_templates(user_tier)
    
    # 模板类别映射（用于智能降级）
    template_categories = {
        # 训练相关
        "complete_training_plan": "training",
        "exercise_optimization": "training",
        "progress_analysis": "training",
        "plan_adjustment": "training",
        "strength_program": "training",
        # 营养相关
        "nutrition_planning": "nutrition",
        "fat_loss_program": "nutrition",
        # 安全相关
        "safety_assessment": "safety",
        "rehabilitation_training": "safety",
        "posture_correction": "safety",
        # 综合
        "comprehensive_fitness": "comprehensive",
        # 快速
        "greeting": "quick",
        "quick_consultation": "quick"
    }
    
    original_category = template_categories.get(original_template_id, "quick")
    
    # 按类别优先级选择降级模板
    category_fallbacks = {
        "training": ["exercise_optimization", "progress_analysis", "quick_consultation"],
        "nutrition": ["quick_consultation"],
        "safety": ["safety_assessment", "quick_consultation"],
        "comprehensive": ["exercise_optimization", "safety_assessment", "quick_consultation"],
        "quick": ["quick_consultation", "greeting"]
    }
    
    fallback_candidates = category_fallbacks.get(original_category, ["quick_consultation"])
    
    for candidate in fallback_candidates:
        if candidate in available_templates:
            return candidate
    
    # 最终降级到quick_consultation
    return "quick_consultation"


def get_available_templates(user_tier: str) -> List[str]:
    """
    获取用户可用的所有DAG模板
    
    Args:
        user_tier: 用户会员等级
        
    Returns:
        List[str]: 可用模板ID列表
    """
    # MVP阶段：所有用户都可以使用全部模板
    return ALL_TEMPLATES


def get_template_complexity(template_id: str) -> str:
    """
    获取模板的复杂度级别
    
    Args:
        template_id: 模板ID
        
    Returns:
        str: 复杂度级别 (simple/medium/complex)
    """
    if template_id in SIMPLE_TEMPLATES:
        return "simple"
    elif template_id in MEDIUM_TEMPLATES:
        return "medium"
    elif template_id in COMPLEX_TEMPLATES:
        return "complex"
    else:
        return "complex"  # 未知模板默认为复杂


def get_complexity_limit(user_tier: str, complexity: str) -> int:
    """
    获取用户对特定复杂度模板的每日使用限制
    
    积分体系改造后，不再按复杂度限制使用次数，
    改为统一的积分消耗机制。
    
    Args:
        user_tier: 用户会员等级
        complexity: 复杂度级别
        
    Returns:
        int: 每日使用限制 (-1表示无限制)
    """
    # 积分体系：不再限制使用次数，返回-1表示无限制
    return -1


def get_all_complexity_limits(user_tier: str) -> Dict[str, int]:
    """
    获取用户所有复杂度级别的限制
    
    积分体系改造后，不再按复杂度限制使用次数。
    
    Args:
        user_tier: 用户会员等级
        
    Returns:
        Dict[str, int]: 各复杂度的限制（全部为-1表示无限制）
    """
    # 积分体系：不再限制使用次数
    return {"simple": -1, "medium": -1, "complex": -1}


def get_template_count_by_tier(user_tier: str) -> Tuple[int, int]:
    """
    获取用户可用模板数量和总模板数量
    
    Args:
        user_tier: 用户会员等级
        
    Returns:
        Tuple[int, int]: (可用数量, 总数量)
    """
    available = len(get_available_templates(user_tier))
    total = sum(len(templates) for templates in DAG_TEMPLATE_TIERS.values())
    return available, total


def filter_templates_by_permission(
    templates: List[str],
    membership_info: Optional[Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    """
    按权限过滤模板列表
    
    Args:
        templates: 模板ID列表
        membership_info: 用户会员信息
        
    Returns:
        Tuple[List[str], List[str]]: (可用模板, 不可用模板)
    """
    user_tier = get_user_membership_tier(membership_info)
    available_templates = set(get_available_templates(user_tier))
    
    allowed = []
    denied = []
    
    for template_id in templates:
        if template_id in available_templates:
            allowed.append(template_id)
        else:
            denied.append(template_id)
    
    return allowed, denied


# 导出
__all__ = [
    "DAG_TEMPLATE_TIERS",
    "MEMBERSHIP_HIERARCHY",
    "TEMPLATE_REQUIRED_TIER",
    "SIMPLE_TEMPLATES",
    "MEDIUM_TEMPLATES", 
    "COMPLEX_TEMPLATES",
    "PermissionCheckResult",
    "get_user_membership_tier",
    "check_template_permission",
    "get_available_templates",
    "get_template_complexity",
    "get_complexity_limit",
    "get_all_complexity_limits",
    "get_template_count_by_tier",
    "filter_templates_by_permission",
]
