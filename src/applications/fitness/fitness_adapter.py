# -*- coding: utf-8 -*-
"""
健身领域适配器 - FitnessAdapter

DAML-RAG框架的健身领域参考实现，展示如何将框架应用到垂直领域。

核心功能：
1. 提供健身领域的Layer3安全规则（11条）
2. 提供健身领域的DAG模板（13个）
3. 提供健身领域的MCP工具（18个）

Requirements: 5.6

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
from typing import Dict, List, Optional, Any

from src.framework.adapters.domain_adapter import (
    DomainAdapter,
    Layer3Rule,
    DAGTemplateDefinition,
    ToolDefinition,
    RuleSeverity,
    RuleCategory,
    register_domain_adapter,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 健身领域Layer3规则定义
# =============================================================================

FITNESS_LAYER3_RULES = [
    # 安全规则（优先级最高）
    Layer3Rule(
        rule_id="joint_load_rule",
        name="关节负荷规则",
        description="排除涉及受伤关节的动作，区分绝对禁忌和相对禁忌",
        category=RuleCategory.SAFETY,
        severity=RuleSeverity.ABSOLUTE,
        condition="user_has_joint_injury",
        action="filter",
        parameters={
            "joint_keywords": {
                "肩": ["肩", "shoulder", "三角肌", "deltoid"],
                "膝": ["膝", "knee", "股四头肌", "quadriceps"],
                "腰": ["腰", "lower back", "竖脊肌", "erector"],
            }
        }
    ),
    Layer3Rule(
        rule_id="postural_correction_rule",
        name="体态矫正规则",
        description="推荐矫正动作并避免加重动作",
        category=RuleCategory.SAFETY,
        severity=RuleSeverity.RELATIVE,
        condition="user_has_postural_issues",
        action="boost",
        parameters={
            "postural_issues": {
                "骨盆前倾": {
                    "corrective_keywords": ["臀桥", "死虫", "平板支撑"],
                    "aggravating_keywords": ["深蹲", "硬拉", "弓步蹲"]
                },
                "圆肩": {
                    "corrective_keywords": ["面拉", "反向飞鸟", "YTWL"],
                    "aggravating_keywords": ["卧推", "俯卧撑", "前平举"]
                },
                "驼背": {
                    "corrective_keywords": ["胸椎伸展", "猫牛式", "眼镜蛇式"],
                    "aggravating_keywords": ["卷腹", "仰卧起坐"]
                }
            }
        }
    ),
    
    # 运动学规则
    Layer3Rule(
        rule_id="kinetic_chain_rule",
        name="动力链规则",
        description="康复场景优先闭链动作",
        category=RuleCategory.KINETIC,
        severity=RuleSeverity.RELATIVE,
        condition="user_in_rehabilitation",
        action="boost",
        parameters={
            "closed_chain_boost": 0.2,
            "open_chain_penalty": 0.0
        }
    ),
    Layer3Rule(
        rule_id="force_balance_rule",
        name="推拉平衡规则",
        description="确保push:pull比例在1:1到2:1之间",
        category=RuleCategory.KINETIC,
        severity=RuleSeverity.CAUTION,
        condition="session_has_imbalance",
        action="boost",
        parameters={
            "target_ratio_min": 1.0,
            "target_ratio_max": 2.0
        }
    ),
    
    # 恢复规则
    Layer3Rule(
        rule_id="recovery_time_rule",
        name="恢复时间规则",
        description="基于肌肉恢复时间推荐",
        category=RuleCategory.RECOVERY,
        severity=RuleSeverity.CAUTION,
        condition="muscle_not_recovered",
        action="warn",
        parameters={
            "recovery_hours": {
                "大肌群": 72,
                "中等肌群": 48,
                "小肌群": 36
            }
        }
    ),
    
    # 领域专业约束
    Layer3Rule(
        rule_id="body_type_constraint",
        name="体型约束",
        description="根据用户体型推荐适合的动作",
        category=RuleCategory.DOMAIN,
        severity=RuleSeverity.RELATIVE,
        condition="user_has_body_type",
        action="boost",
        parameters={
            "ectomorph": {"preferred_mechanics": ["compound"]},
            "mesomorph": {"preferred_mechanics": ["compound", "isolation"]},
            "endomorph": {"preferred_mechanics": ["compound"]}
        }
    ),
    Layer3Rule(
        rule_id="training_frequency_constraint",
        name="训练频率约束",
        description="根据用户训练频率调整推荐",
        category=RuleCategory.DOMAIN,
        severity=RuleSeverity.RELATIVE,
        condition="always",
        action="boost",
        parameters={
            "low_frequency": {"strategy": "full_body", "days": [1, 2]},
            "medium_frequency": {"strategy": "split", "days": [3, 4]},
            "high_frequency": {"strategy": "detailed_split", "days": [5, 6, 7]}
        }
    ),
    Layer3Rule(
        rule_id="session_duration_constraint",
        name="训练时长约束",
        description="确保推荐动作适合用户的训练时长",
        category=RuleCategory.DOMAIN,
        severity=RuleSeverity.RELATIVE,
        condition="always",
        action="filter",
        parameters={
            "short": {"max_exercises": 5, "duration_minutes": 45},
            "medium": {"max_exercises": 8, "duration_minutes": 75},
            "long": {"max_exercises": 12, "duration_minutes": 90}
        }
    ),
    Layer3Rule(
        rule_id="goal_alignment_constraint",
        name="目标对齐约束",
        description="优先推荐与用户目标匹配的动作",
        category=RuleCategory.DOMAIN,
        severity=RuleSeverity.RELATIVE,
        condition="user_has_goal",
        action="boost",
        parameters={
            "muscle_gain": {"preferred_mechanics": ["compound", "isolation"]},
            "fat_loss": {"preferred_mechanics": ["compound"]},
            "strength": {"preferred_mechanics": ["compound"]},
            "rehabilitation": {"preferred_kinetic_chain": ["closed_chain"]}
        }
    ),
    Layer3Rule(
        rule_id="progressive_overload_constraint",
        name="渐进超负荷约束",
        description="根据训练周数调整难度推荐",
        category=RuleCategory.DOMAIN,
        severity=RuleSeverity.RELATIVE,
        condition="always",
        action="filter",
        parameters={
            "novice": {"weeks": [0, 4], "allowed_difficulties": ["beginner", "easy"]},
            "adaptation": {"weeks": [5, 12], "allowed_difficulties": ["beginner", "intermediate"]},
            "mature": {"weeks": [13, 999], "allowed_difficulties": ["beginner", "intermediate", "advanced"]}
        }
    ),
    Layer3Rule(
        rule_id="nutrition_constraint",
        name="营养约束",
        description="根据营养摄入调整高强度动作推荐",
        category=RuleCategory.DOMAIN,
        severity=RuleSeverity.CAUTION,
        condition="user_in_calorie_deficit",
        action="warn",
        parameters={
            "deficit_threshold": 0.8,
            "intensity_limit": "moderate"
        }
    ),
]


# =============================================================================
# 健身领域DAG模板定义
# =============================================================================

FITNESS_DAG_TEMPLATES = {
    "greeting": DAGTemplateDefinition(
        template_id="greeting",
        name="问候闲聊",
        description="友好回应用户的问候和简单闲聊",
        category="quick",
        applicable_intents=["你好", "早上好", "晚上好", "hi", "hello", "嗨", "在吗"],
        required_tools=[],
        optional_tools=[],
        tool_dependencies={},
        parallel_groups=[],
        expected_output={"greeting_response": "简短友好的问候回应"},
        safety_constraints=[],
        estimated_duration_seconds=1.0,
        complexity_level=1,
        response_hint="简短友好，1-2句话，不要提供训练建议"
    ),
    
    "complete_training_plan": DAGTemplateDefinition(
        template_id="complete_training_plan",
        name="完整训练计划",
        description="为用户制定包含动作选择、训练量计算、周期化安排的完整训练计划",
        category="comprehensive",
        applicable_intents=["制定训练计划", "增肌计划", "力量训练计划", "完整训练方案"],
        required_tools=[
            "get_user_profile",
            "contraindications_checker",
            "injury_risk_assessor",
            "intelligent_exercise_selector",
            "muscle_group_volume_calculator",
            "professional_program_designer",
            "intelligent_weight_calculator"
        ],
        optional_tools=[
            "movement_pattern_balancer",
            "periodized_program_designer",
            "training_split_designer"
        ],
        tool_dependencies={
            "get_user_profile": [],
            "contraindications_checker": ["get_user_profile"],
            "injury_risk_assessor": ["get_user_profile"],
            "muscle_group_volume_calculator": ["get_user_profile"],
            "intelligent_exercise_selector": ["contraindications_checker", "injury_risk_assessor"],
            "intelligent_weight_calculator": ["intelligent_exercise_selector"],
            "professional_program_designer": ["intelligent_exercise_selector", "muscle_group_volume_calculator"]
        },
        parallel_groups=[
            ["get_user_profile"],
            ["contraindications_checker", "injury_risk_assessor", "muscle_group_volume_calculator"],
            ["intelligent_exercise_selector"],
            ["intelligent_weight_calculator"],
            ["professional_program_designer"]
        ],
        expected_output={
            "user_profile": "用户档案数据",
            "contraindications": "禁忌动作列表",
            "recommended_exercises": "推荐动作列表",
            "training_program": "完整训练计划"
        },
        safety_constraints=[
            "必须执行contraindications_checker",
            "必须执行injury_risk_assessor",
            "禁忌动作必须从推荐中排除"
        ],
        estimated_duration_seconds=15.0,
        complexity_level=3,
        response_hint="详细专业，提供完整的训练计划，包含动作选择、组数次数、训练量分配"
    ),
    
    "nutrition_planning": DAGTemplateDefinition(
        template_id="nutrition_planning",
        name="营养规划",
        description="基于用户目标和训练计划制定完整的营养方案",
        category="nutrition",
        applicable_intents=["营养计划", "饮食建议", "营养规划", "膳食计划"],
        required_tools=[
            "get_user_profile",
            "tdee_calculator",
            "nutrition_intake_analyzer",
            "meal_plan_designer"
        ],
        optional_tools=["exercise_nutrition_optimization"],
        tool_dependencies={
            "get_user_profile": [],
            "tdee_calculator": ["get_user_profile"],
            "nutrition_intake_analyzer": ["tdee_calculator"],
            "meal_plan_designer": ["tdee_calculator", "nutrition_intake_analyzer"]
        },
        parallel_groups=[
            ["get_user_profile"],
            ["tdee_calculator"],
            ["nutrition_intake_analyzer"],
            ["meal_plan_designer"]
        ],
        expected_output={
            "tdee": "每日总能量消耗",
            "nutrition_analysis": "营养摄入分析",
            "meal_plan": "膳食计划"
        },
        safety_constraints=["必须考虑用户饮食偏好", "必须考虑食物过敏"],
        estimated_duration_seconds=10.0,
        complexity_level=2,
        response_hint="专业详细，提供完整的营养方案，包含TDEE计算、宏量营养素分配"
    ),
    
    "safety_assessment": DAGTemplateDefinition(
        template_id="safety_assessment",
        name="安全评估",
        description="全面评估用户的运动安全性，识别风险和禁忌",
        category="safety",
        applicable_intents=["安全评估", "风险评估", "禁忌检查", "能否训练"],
        required_tools=[
            "get_user_profile",
            "contraindications_checker",
            "injury_risk_assessor"
        ],
        optional_tools=["safe_exercise_modifier", "exercise_alternative_finder"],
        tool_dependencies={
            "get_user_profile": [],
            "contraindications_checker": ["get_user_profile"],
            "injury_risk_assessor": ["get_user_profile"],
            "safe_exercise_modifier": ["injury_risk_assessor"],
            "exercise_alternative_finder": ["contraindications_checker"]
        },
        parallel_groups=[
            ["get_user_profile"],
            ["contraindications_checker", "injury_risk_assessor"],
            ["safe_exercise_modifier", "exercise_alternative_finder"]
        ],
        expected_output={
            "contraindications": "禁忌动作",
            "injury_risks": "损伤风险",
            "safety_report": "安全评估报告"
        },
        safety_constraints=["必须全面检查健康状况", "必须识别所有禁忌症"],
        estimated_duration_seconds=8.0,
        complexity_level=2,
        response_hint="专业严谨，重点说明安全风险和禁忌事项"
    ),
    
    "exercise_optimization": DAGTemplateDefinition(
        template_id="exercise_optimization",
        name="动作优化",
        description="优化训练动作选择，提供替代方案和安全调整",
        category="training",
        applicable_intents=["动作推荐", "动作选择", "动作替代", "换动作"],
        required_tools=[
            "get_user_profile",
            "intelligent_exercise_selector",
            "exercise_alternative_finder"
        ],
        optional_tools=["contraindications_checker", "safe_exercise_modifier"],
        tool_dependencies={
            "get_user_profile": [],
            "contraindications_checker": ["get_user_profile"],
            "intelligent_exercise_selector": ["get_user_profile"],
            "exercise_alternative_finder": ["intelligent_exercise_selector"]
        },
        parallel_groups=[
            ["get_user_profile"],
            ["contraindications_checker"],
            ["intelligent_exercise_selector"],
            ["exercise_alternative_finder"]
        ],
        expected_output={
            "recommended_exercises": "推荐动作",
            "alternatives": "替代动作"
        },
        safety_constraints=["必须考虑用户能力", "必须提供安全替代"],
        estimated_duration_seconds=6.0,
        complexity_level=1,
        response_hint="简洁实用，重点推荐2-3个动作，说明选择理由"
    ),
    
    "quick_consultation": DAGTemplateDefinition(
        template_id="quick_consultation",
        name="快速咨询",
        description="快速回答简单的健身问题",
        category="quick",
        applicable_intents=["简单问题", "快速咨询", "基础问题"],
        required_tools=["get_user_profile"],
        optional_tools=[],
        tool_dependencies={"get_user_profile": []},
        parallel_groups=[["get_user_profile"]],
        expected_output={"quick_answer": "快速回答"},
        safety_constraints=["必须提供准确信息"],
        estimated_duration_seconds=2.0,
        complexity_level=1,
        response_hint="简洁明了，直接回答用户问题"
    ),
    
    "posture_correction": DAGTemplateDefinition(
        template_id="posture_correction",
        name="体态矫正",
        description="评估用户体态问题，推荐矫正动作并制定矫正训练计划",
        category="safety",
        applicable_intents=["体态矫正", "姿势改善", "圆肩驼背", "骨盆前倾"],
        required_tools=[
            "get_user_profile",
            "postural_assessor",
            "contraindications_checker",
            "intelligent_exercise_selector"
        ],
        optional_tools=["movement_pattern_balancer", "professional_program_designer"],
        tool_dependencies={
            "get_user_profile": [],
            "postural_assessor": ["get_user_profile"],
            "contraindications_checker": ["postural_assessor"],
            "intelligent_exercise_selector": ["contraindications_checker"]
        },
        parallel_groups=[
            ["get_user_profile"],
            ["postural_assessor"],
            ["contraindications_checker"],
            ["intelligent_exercise_selector"]
        ],
        expected_output={
            "postural_assessment": "体态评估",
            "corrective_exercises": "矫正动作",
            "correction_plan": "矫正训练计划"
        },
        safety_constraints=["必须识别体态问题", "必须推荐矫正动作"],
        estimated_duration_seconds=10.0,
        complexity_level=2,
        response_hint="专业友好，重点说明体态问题的成因和影响"
    ),
    
    "rehabilitation_training": DAGTemplateDefinition(
        template_id="rehabilitation_training",
        name="康复训练",
        description="为有伤病史的用户制定安全的康复训练计划",
        category="safety",
        applicable_intents=["康复训练", "伤后训练", "康复计划", "恢复训练"],
        required_tools=[
            "get_user_profile",
            "contraindications_checker",
            "injury_risk_assessor",
            "safe_exercise_modifier"
        ],
        optional_tools=["exercise_alternative_finder", "intelligent_exercise_selector"],
        tool_dependencies={
            "get_user_profile": [],
            "contraindications_checker": ["get_user_profile"],
            "injury_risk_assessor": ["get_user_profile"],
            "safe_exercise_modifier": ["injury_risk_assessor"],
            "exercise_alternative_finder": ["contraindications_checker"]
        },
        parallel_groups=[
            ["get_user_profile"],
            ["contraindications_checker", "injury_risk_assessor"],
            ["safe_exercise_modifier"],
            ["exercise_alternative_finder"]
        ],
        expected_output={
            "safety_assessment": "安全评估",
            "safe_exercises": "安全动作",
            "rehabilitation_plan": "康复计划"
        },
        safety_constraints=["必须严格安全评估", "必须避免加重伤病"],
        estimated_duration_seconds=12.0,
        complexity_level=3,
        response_hint="谨慎专业，重点强调安全性和循序渐进"
    ),
    
    "fat_loss_program": DAGTemplateDefinition(
        template_id="fat_loss_program",
        name="减脂专项",
        description="制定以减脂为目标的综合训练和营养方案",
        category="comprehensive",
        applicable_intents=["减脂", "减肥", "降体脂", "减脂计划", "瘦身"],
        required_tools=[
            "get_user_profile",
            "tdee_calculator",
            "intelligent_exercise_selector",
            "muscle_group_volume_calculator",
            "professional_program_designer",
            "meal_plan_designer"
        ],
        optional_tools=["contraindications_checker", "nutrition_intake_analyzer"],
        tool_dependencies={
            "get_user_profile": [],
            "tdee_calculator": ["get_user_profile"],
            "intelligent_exercise_selector": ["get_user_profile"],
            "professional_program_designer": ["intelligent_exercise_selector"],
            "meal_plan_designer": ["tdee_calculator"]
        },
        parallel_groups=[
            ["get_user_profile"],
            ["tdee_calculator", "intelligent_exercise_selector"],
            ["professional_program_designer", "meal_plan_designer"]
        ],
        expected_output={
            "tdee": "每日总能量消耗",
            "training_program": "减脂训练计划",
            "nutrition_plan": "减脂营养计划"
        },
        safety_constraints=["必须设置合理的热量缺口", "必须保持肌肉量"],
        estimated_duration_seconds=15.0,
        complexity_level=3,
        response_hint="系统全面，重点说明减脂的科学原理和策略"
    ),
    
    "strength_program": DAGTemplateDefinition(
        template_id="strength_program",
        name="力量专项",
        description="制定以增强力量为目标的专项训练计划",
        category="training",
        applicable_intents=["增强力量", "力量训练", "提高力量", "大重量训练"],
        required_tools=[
            "get_user_profile",
            "intelligent_exercise_selector",
            "intelligent_weight_calculator",
            "professional_program_designer"
        ],
        optional_tools=["contraindications_checker", "injury_risk_assessor"],
        tool_dependencies={
            "get_user_profile": [],
            "intelligent_exercise_selector": ["get_user_profile"],
            "intelligent_weight_calculator": ["intelligent_exercise_selector"],
            "professional_program_designer": ["intelligent_weight_calculator"]
        },
        parallel_groups=[
            ["get_user_profile"],
            ["intelligent_exercise_selector"],
            ["intelligent_weight_calculator"],
            ["professional_program_designer"]
        ],
        expected_output={
            "recommended_exercises": "推荐动作",
            "weight_recommendations": "重量建议",
            "strength_program": "力量训练计划"
        },
        safety_constraints=["必须评估当前力量水平", "必须循序渐进"],
        estimated_duration_seconds=10.0,
        complexity_level=2,
        response_hint="专业实用，重点说明力量训练的原则和进阶方法"
    ),
}


# =============================================================================
# 健身领域MCP工具定义
# =============================================================================

FITNESS_TOOLS = [
    # 动作类工具
    ToolDefinition(
        name="intelligent_exercise_selector",
        description="智能动作选择器，基于用户档案和目标推荐最适合的训练动作",
        category="exercise",
        priority="P0",
        requires_user_profile=True,
        requires_three_layer=True
    ),
    ToolDefinition(
        name="exercise_alternative_finder",
        description="动作替代查找器，为指定动作找到安全的替代方案",
        category="exercise",
        priority="P1",
        requires_user_profile=True,
        requires_three_layer=True
    ),
    
    # 安全类工具
    ToolDefinition(
        name="contraindications_checker",
        description="禁忌症检查器，检查用户健康状况与动作的禁忌关系",
        category="safety",
        priority="P0",
        requires_user_profile=True,
        requires_three_layer=True
    ),
    ToolDefinition(
        name="injury_risk_assessor",
        description="损伤风险评估器，评估特定动作对用户的潜在损伤风险",
        category="safety",
        priority="P0",
        requires_user_profile=True,
        requires_three_layer=True
    ),
    ToolDefinition(
        name="safe_exercise_modifier",
        description="安全动作修改器，为有伤病的用户提供动作修改建议",
        category="safety",
        priority="P1",
        requires_user_profile=True,
        requires_three_layer=True
    ),
    ToolDefinition(
        name="postural_assessor",
        description="体态评估器，评估用户体态问题并推荐矫正方案",
        category="safety",
        priority="P1",
        requires_user_profile=True,
        requires_three_layer=False
    ),
    
    # 训练类工具
    ToolDefinition(
        name="muscle_group_volume_calculator",
        description="肌群训练量计算器，计算各肌群的最佳训练量",
        category="training",
        priority="P0",
        requires_user_profile=True,
        requires_three_layer=False
    ),
    ToolDefinition(
        name="professional_program_designer",
        description="专业训练计划设计器，设计完整的周期化训练计划",
        category="training",
        priority="P0",
        requires_user_profile=True,
        requires_three_layer=True
    ),
    ToolDefinition(
        name="periodized_program_designer",
        description="周期化计划设计器，设计长期周期化训练方案",
        category="training",
        priority="P1",
        requires_user_profile=True,
        requires_three_layer=False
    ),
    ToolDefinition(
        name="training_split_designer",
        description="训练分化设计器，设计训练分化方案",
        category="training",
        priority="P1",
        requires_user_profile=True,
        requires_three_layer=False
    ),
    ToolDefinition(
        name="intelligent_weight_calculator",
        description="智能重量计算器，计算个性化训练重量",
        category="training",
        priority="P0",
        requires_user_profile=True,
        requires_three_layer=False
    ),
    ToolDefinition(
        name="movement_pattern_balancer",
        description="动作模式平衡器，确保训练计划的动作模式平衡",
        category="training",
        priority="P1",
        requires_user_profile=True,
        requires_three_layer=False
    ),
    ToolDefinition(
        name="record_training_feedback",
        description="训练反馈记录器，记录用户的训练反馈",
        category="training",
        priority="P1",
        requires_user_profile=True,
        requires_three_layer=False
    ),
    
    # 营养类工具
    ToolDefinition(
        name="tdee_calculator",
        description="TDEE计算器，计算每日总能量消耗",
        category="nutrition",
        priority="P0",
        requires_user_profile=True,
        requires_three_layer=False
    ),
    ToolDefinition(
        name="meal_plan_designer",
        description="膳食计划设计器，设计个性化膳食计划",
        category="nutrition",
        priority="P0",
        requires_user_profile=True,
        requires_three_layer=True
    ),
    ToolDefinition(
        name="nutrition_intake_analyzer",
        description="营养摄入分析器，分析用户的营养摄入情况",
        category="nutrition",
        priority="P1",
        requires_user_profile=True,
        requires_three_layer=False
    ),
    ToolDefinition(
        name="exercise_nutrition_optimization",
        description="运动营养优化器，优化训练前后的营养摄入",
        category="nutrition",
        priority="P1",
        requires_user_profile=True,
        requires_three_layer=False
    ),
]


# =============================================================================
# FitnessAdapter 健身领域适配器
# =============================================================================

@register_domain_adapter
class FitnessAdapter(DomainAdapter):
    """
    健身领域适配器
    
    DAML-RAG框架的健身领域参考实现，展示如何将框架应用到垂直领域。
    
    Requirements: 5.6
    
    功能：
    1. 提供健身领域的Layer3安全规则（11条）
    2. 提供健身领域的DAG模板（13个）
    3. 提供健身领域的MCP工具（18个）
    
    使用示例:
    ```python
    from src.applications.fitness.fitness_adapter import FitnessAdapter
    
    adapter = FitnessAdapter()
    await adapter.initialize()
    
    # 获取规则
    rules = adapter.get_layer3_rules()
    
    # 获取模板
    templates = adapter.get_dag_templates()
    
    # 获取工具
    tools = adapter.get_tools()
    ```
    """
    
    def __init__(self):
        """初始化健身领域适配器"""
        super().__init__()
        self._version = "1.0.0"
        logger.info("创建健身领域适配器 FitnessAdapter")
    
    def get_name(self) -> str:
        """返回领域名称"""
        return "fitness"
    
    def get_display_name(self) -> str:
        """返回领域显示名称"""
        return "健身"
    
    def get_description(self) -> str:
        """返回领域描述"""
        return (
            "健身领域适配器，提供智能训练计划制定、营养规划、安全评估等功能。"
            "包含11条Layer3安全规则、13个DAG模板和18个MCP工具。"
        )
    
    def get_version(self) -> str:
        """返回适配器版本"""
        return self._version
    
    def get_layer3_rules(self) -> List[Layer3Rule]:
        """
        返回健身领域的Layer3安全规则
        
        Returns:
            List[Layer3Rule]: 11条健身领域规则
        """
        return FITNESS_LAYER3_RULES.copy()
    
    def get_dag_templates(self) -> Dict[str, DAGTemplateDefinition]:
        """
        返回健身领域的DAG模板
        
        Returns:
            Dict[str, DAGTemplateDefinition]: 13个健身领域模板
        """
        return FITNESS_DAG_TEMPLATES.copy()
    
    def get_tools(self) -> List[ToolDefinition]:
        """
        返回健身领域的MCP工具
        
        Returns:
            List[ToolDefinition]: 18个健身领域工具
        """
        return FITNESS_TOOLS.copy()
    
    async def initialize(self) -> bool:
        """
        初始化健身领域适配器
        
        执行以下初始化步骤：
        1. 验证规则完整性
        2. 验证模板完整性
        3. 验证工具定义
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("=" * 60)
            logger.info("🏋️ 初始化健身领域适配器 FitnessAdapter")
            logger.info("=" * 60)
            
            # 验证规则
            rules = self.get_layer3_rules()
            enabled_rules = [r for r in rules if r.enabled]
            logger.info(f"  📋 Layer3规则: {len(rules)}条 (启用: {len(enabled_rules)}条)")
            
            # 按类别统计规则
            rule_categories = {}
            for rule in rules:
                cat = rule.category.value
                rule_categories[cat] = rule_categories.get(cat, 0) + 1
            for cat, count in rule_categories.items():
                logger.info(f"     - {cat}: {count}条")
            
            # 验证模板
            templates = self.get_dag_templates()
            valid_templates = 0
            for template_id, template in templates.items():
                if template.validate():
                    valid_templates += 1
                else:
                    logger.warning(f"  ⚠️ 模板 {template_id} 验证失败")
            logger.info(f"  📋 DAG模板: {valid_templates}/{len(templates)}个有效")
            
            # 按类别统计模板
            template_categories = {}
            for template in templates.values():
                cat = template.category
                template_categories[cat] = template_categories.get(cat, 0) + 1
            for cat, count in template_categories.items():
                logger.info(f"     - {cat}: {count}个")
            
            # 验证工具
            tools = self.get_tools()
            logger.info(f"  📋 MCP工具: {len(tools)}个")
            
            # 按类别统计工具
            tool_categories = {}
            for tool in tools:
                cat = tool.category
                tool_categories[cat] = tool_categories.get(cat, 0) + 1
            for cat, count in tool_categories.items():
                logger.info(f"     - {cat}: {count}个")
            
            # 按优先级统计工具
            p0_tools = [t for t in tools if t.priority == "P0"]
            p1_tools = [t for t in tools if t.priority == "P1"]
            logger.info(f"     - P0优先级: {len(p0_tools)}个")
            logger.info(f"     - P1优先级: {len(p1_tools)}个")
            
            self._initialized = True
            logger.info("=" * 60)
            logger.info("✅ 健身领域适配器初始化成功")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"❌ 健身领域适配器初始化失败: {e}")
            return False
    
    # =========================================================================
    # 健身领域特定方法
    # =========================================================================
    
    def get_safety_rules(self) -> List[Layer3Rule]:
        """获取安全类规则"""
        return self.get_rules_by_category(RuleCategory.SAFETY)
    
    def get_kinetic_rules(self) -> List[Layer3Rule]:
        """获取运动学规则"""
        return self.get_rules_by_category(RuleCategory.KINETIC)
    
    def get_recovery_rules(self) -> List[Layer3Rule]:
        """获取恢复规则"""
        return self.get_rules_by_category(RuleCategory.RECOVERY)
    
    def get_domain_rules(self) -> List[Layer3Rule]:
        """获取领域专业约束规则"""
        return self.get_rules_by_category(RuleCategory.DOMAIN)
    
    def get_training_templates(self) -> List[DAGTemplateDefinition]:
        """获取训练类模板"""
        return self.get_templates_by_category("training")
    
    def get_nutrition_templates(self) -> List[DAGTemplateDefinition]:
        """获取营养类模板"""
        return self.get_templates_by_category("nutrition")
    
    def get_safety_templates(self) -> List[DAGTemplateDefinition]:
        """获取安全类模板"""
        return self.get_templates_by_category("safety")
    
    def get_comprehensive_templates(self) -> List[DAGTemplateDefinition]:
        """获取综合类模板"""
        return self.get_templates_by_category("comprehensive")
    
    def get_exercise_tools(self) -> List[ToolDefinition]:
        """获取动作类工具"""
        return self.get_tools_by_category("exercise")
    
    def get_safety_tools(self) -> List[ToolDefinition]:
        """获取安全类工具"""
        return self.get_tools_by_category("safety")
    
    def get_training_tools(self) -> List[ToolDefinition]:
        """获取训练类工具"""
        return self.get_tools_by_category("training")
    
    def get_nutrition_tools(self) -> List[ToolDefinition]:
        """获取营养类工具"""
        return self.get_tools_by_category("nutrition")
    
    def get_p0_tools(self) -> List[ToolDefinition]:
        """获取P0优先级工具"""
        return self.get_tools_by_priority("P0")
    
    def get_p1_tools(self) -> List[ToolDefinition]:
        """获取P1优先级工具"""
        return self.get_tools_by_priority("P1")


# =============================================================================
# 便捷函数
# =============================================================================

def get_fitness_adapter() -> FitnessAdapter:
    """
    获取健身领域适配器实例
    
    Returns:
        FitnessAdapter: 健身领域适配器实例
    """
    return FitnessAdapter()


async def initialize_fitness_adapter() -> FitnessAdapter:
    """
    初始化并返回健身领域适配器
    
    Returns:
        FitnessAdapter: 已初始化的健身领域适配器实例
    """
    adapter = FitnessAdapter()
    await adapter.initialize()
    return adapter
